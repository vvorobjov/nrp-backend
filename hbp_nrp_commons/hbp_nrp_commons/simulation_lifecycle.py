# ---LICENSE-BEGIN - DO NOT CHANGE OR MOVE THIS HEADER
# This file is part of the Neurorobotics Platform software
# Copyright (C) 2014,2015,2016,2017 Human Brain Project
# https://www.humanbrainproject.eu
#
# The Human Brain Project is a European Commission funded project
# in the frame of the Horizon2020 FET Flagship plan.
# http://ec.europa.eu/programmes/horizon2020/en/h2020-section/fet-flagships
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# ---LICENSE-END
"""
This package defines the simulation lifecycle such as used in the NRP
"""

import os
import json
import logging
import time
from typing import Optional, List

from hbp_nrp_commons.workspace.settings import Settings
from transitions import MachineError
from transitions.extensions import LockedMachine as Machine
import paho.mqtt.client as mqtt

__author__ = 'NRP software team, Georg Hinkel, Ugo Albanese'

logger = logging.getLogger(__name__)

# NOTE
# transition package logging is quite verbose, add one level to the parent one:
# i.e. parent_level + 10
logging.getLogger("transitions").setLevel(logger.getEffectiveLevel() + 10)

class SimulationLifecycle:
    """
    Defines the lifecycle of a simulation.

    The Simulation is created in the 'created' initial state; the 'initialized' trigger makes it transition to 'paused'.
    The 'started' trigger makes it move to started, 
    then 'completed' to 'completed' and finally, 'stopped' to the 'stopped' final state.
    From any running state, the 'failed' trigger will result in the final 'failed' state.

    After a transition, state changes may be propagated on the 'synchronization_topic'
    to other instances of SimulationLifecycle.
    """

    STATES: List[str] = [
        'created',
        'paused',  # Simulation resources have been initialized and waiting to start
        'started',  # Simulation is advancing
        'completed',  # Simulation has completed, waiting to be stopped
        'stopped',  # Simulation has been stopped, resources have been released.
        'failed']  # Simulation has failed, resources have been released.

    INITIAL_STATE: str = 'created'

    FINAL_STATES: List[str] = ['stopped', 'failed']

    RUNNING_STATES: List[str] = ['created', 'paused', 'started', 'completed']

    ERROR_STATES: List[str] = ['failed']

    TRIGGERS: List[str] = ['initialized', 'paused', 'started', 'completed', 'stopped', 'failed']

    @staticmethod
    def is_state(state: str) -> bool:
        return state in SimulationLifecycle.STATES

    @staticmethod
    def is_final_state(state: str) -> bool:
        return state in SimulationLifecycle.FINAL_STATES

    @staticmethod
    def is_error_state(state: str) -> bool:
        return state in SimulationLifecycle.ERROR_STATES

    @staticmethod
    def is_initial_state(state: str) -> bool:
        return state == SimulationLifecycle.INITIAL_STATE

    def __after_state_change_callback(self, state_change):
        """
            Callback to be executed after any state change.
            According to transitions' docs,
            it will be executed after 'transition.after' callbacks
            https://github.com/pytransitions/transitions#callback-execution-order
        """
        self.__propagate_state_change(state_change)

        self.__shut_down_on_final_state(state_change)

    def __shut_down_on_final_state(self, state_change):
        """
        Shuts self down if the destination state is one of FINAL_STATES.

        """
        source_state = state_change.transition.source
        dest_state = state_change.transition.dest

        if not SimulationLifecycle.is_final_state(dest_state):
            logger.debug("Not a final state. Don't shutdown.")
            return

        if source_state != dest_state:  # not a self transition
            time.sleep(1)
            logger.debug("Final state '%s' reached. Shutdown.", dest_state)
            self.shutdown(state_change)

    def __propagate_state_change(self, state_change):
        """
        Propagates the state change to other simulation lifecycle implementations.

        :param state_change: The event that caused the state change
            From this, the trigger that caused the event is available as state_change.event.name
            The source state of the transition is state_change.transition.source
            The target state of the transition is state_change.transition.dest
        """
        source_state = state_change.transition.source
        dest_state = state_change.transition.dest

        if 'silent' not in state_change.kwargs or not state_change.kwargs['silent']:
            # Publish the state change message.

            logger.debug("Propagating simulation lifecycle state change from '%s' to '%s'",
                         source_state, dest_state)
            # For the transition out of the initial state (i.e. initialized), setting
            # the retain flag is crucial since it allows to create the two lifecycles asynchronously.
            # In fact, the Backend lifecycle transitions to initialized before the creation of
            # the simulation server lifecycle.
            # It's not a problem, since, upon connection to the broker, 
            # the retained initialization message will be delivered to simulation server lifecycle
            # allowing it to transition correctly
            should_retain = self.is_initial_state(source_state)

            self.__mqtt_client.publish(topic=self.synchronization_topic,
                                       payload=json.dumps({"source_node": self.mqtt_client_id,
                                                           "source_state": source_state,
                                                           "event": state_change.event.name,
                                                           "target_state": dest_state}),
                                       retain=should_retain)

    def __synchronized_lifecycle_changed(self, _client, _userdata, message):
        """
        Gets called when the lifecycle of the simulation changed in another MQTT node:
        i.e. it's the state change MQTT message received callback
        
        :param message: received message.
                        message.payload is a JSON with format:
                        string source_node   # The mqtt node from which the simulation lifecycle
                                               change was initiated
                        string source_state  # The source state of the lifecycle
                        string event         # The event that caused the state change
                        string target_state  # The target state name
        """
        if not (decoded_msg := str(message.payload.decode("utf-8", "ignore"))):
            # ignore empty messages
            return

        try:
            state_change = json.loads(decoded_msg)
        except json.JSONDecodeError:
            logger.debug("[%s] Received malformed lifecycle synchronization message. Ignoring",
                         self.mqtt_client_id)
            return

        source_state = state_change["source_state"]

        try:
            # don't recevive message from myself
            if self.mqtt_client_id == state_change["source_node"]:  # receiver same as sender
                return

            logger.debug("[%s] Received lifecycle synchronization message: %s",
                         self.mqtt_client_id, state_change)

            if self.state != source_state:
                logger.warning("The local simulation lifecycle and the remote version "
                               "have diverged.")
                logger.warning("Moving to selected source state now")
                self.__machine.set_state(source_state)

            # pylint: disable=broad-except
            try:
                self.__machine.events[state_change["event"]].trigger(silent=True)
            except Exception as e:
                self.__machine.set_state(state_change["target_state"])
                logger.exception(
                    "Error while synchronizing the lifecycle: %s", str(e))
                self.failed()
        except Exception as e2:
            logger.exception(
                "Error failing the simulation (this should never happen): %s", str(e2))

    def __on_connect(self, client, _userdata: dict, _flags, _rc):
        logger.debug("Connected to MQTT broker with id '%s'", self.mqtt_client_id)

        # clear the topic from stale retained msgs if required
        self._clear_synchronization_topic()

        client.subscribe(self.synchronization_topic)
        logger.debug("Subscribed to %s MQTT topic", self.synchronization_topic)

    def _clear_synchronization_topic(self):
        """
        Clear the synchronization_topic from retained messages if clear_synchronization_topic is True
        """
        if self.clear_synchronization_topic:
            self.__mqtt_client.publish(topic=self.synchronization_topic,
                                       payload="",
                                       retain=True)

    def __init__(self,
                 synchronization_topic: str,
                 initial_state: str = INITIAL_STATE,
                 propagated_destinations: Optional[List[str]] = STATES,
                 mqtt_client_id: Optional[str] = None,
                 mqtt_broker_host: str = Settings.mqtt_broker_host,
                 mqtt_broker_port: int = Settings.mqtt_broker_port,
                 clear_synchronization_topic=False):
        """
        Creates a new synchronization lifecycle for the given topic

        :param synchronization_topic: The topic name used to synchronize the simulation lifecycles
        :param initial_state: The initial state of the lifecycle
        :param propagated_destinations: States for which change events should be propagated to other lifecycles
        :param mqtt_client_id: the MQTT Client ID of this lifecycle
        :param mqtt_broker_host: the host where to find the MQTT broker
        :param mqtt_broker_port: the port, on mqtt_broker_host, at which the MQTT broker is available
        :param clear_synchronization_topic: Whether to clean on connect the synchronization topic of retained messages

        """

        propagated_destinations = propagated_destinations \
            if propagated_destinations is not None else SimulationLifecycle.STATES
        
        # states for which change events should NOT be propagated to other lifecycles
        self._silent_destinations = frozenset(self.STATES) - frozenset(propagated_destinations)

        self.synchronization_topic = synchronization_topic
        self.clear_synchronization_topic = clear_synchronization_topic

        # Transitions adds some members based on the STATES and transitions
        # We assign them dummy values here to avoid pylint warnings
        self.state = initial_state
        self.failed = lambda: None

        # create StateMachine and setup transitions
        self.__machine = Machine(model=self,
                                 states=SimulationLifecycle.STATES,
                                 initial=initial_state,
                                 after_state_change=self.__after_state_change_callback,
                                 send_event=True)

        self._add_transition(trigger='initialized',
                             source='created', dest='paused',
                             before='initialize')
        self._add_transition(trigger='started',
                             source='paused', dest='started',
                             before='start')
        self._add_transition(trigger='paused',
                             source='started', dest='paused',
                             before='pause')
        self._add_transition(trigger='completed',
                             source='started', dest='completed')
        self._add_transition(trigger='stopped',
                             source=SimulationLifecycle.RUNNING_STATES, dest='stopped',
                             before='stop')
        self._add_transition(trigger='failed',
                             source=['paused', 'started', 'completed'], dest='failed',
                             after='fail')
        self._add_transition(trigger='failed',
                             source='created', dest='failed',
                             before='stop')
        # TODO reset support

        # mqtt
        self.mqtt_client_id = mqtt_client_id
        self.mqtt_broker_host = mqtt_broker_host
        self.mqtt_broker_port = mqtt_broker_port

        # NOTE MQTTv5 requires clean_start=True parameter to connect
        # instead of clean_session=True here
        self.__mqtt_client: Optional[mqtt.Client] = mqtt.Client(self.mqtt_client_id,
                                                         clean_session=True)

        self.__mqtt_client.on_connect = self.__on_connect
        self.__mqtt_client.message_callback_add(self.synchronization_topic,
                                                self.__synchronized_lifecycle_changed)

        logger.debug("Connecting to the MQTT broker at %s:%s", str(self.mqtt_broker_host),
                     str(self.mqtt_broker_port))
        self.__mqtt_client.connect(host=self.mqtt_broker_host, port=self.mqtt_broker_port)
        self.__mqtt_client.loop_start()  # start message processing thread

    def _add_transition(self, trigger,
                        source, dest,
                        before: Optional[str] = None,
                        after: Optional[str] = None):
        """
        Registers a new transition in the simulation lifecycle

        :param trigger: The trigger that should be used to activate the transition
        :param source: The source state, either as state name or list of STATES
        :param dest: The destination state name
        :param before: The method that should be run before the transition is applied and propagated
        :param after: The method that should be run after the transition has been applied
            successfully, yet still before state propagation
        """
        if (dest != source) and (dest not in source):
            # add idempotent self transitions to avoid raising MachineError
            # in case of duplicated request of transitions
            self.__machine.add_transition(trigger=trigger,
                                          source=dest, dest=dest,
                                          before='set_silent')
        elif trigger in self.__machine.events:
            event = self.__machine.events[trigger]
            if dest in event.transitions:
                del event.transitions[dest]

        before_list = [before] if before is not None else []

        if dest in self._silent_destinations:
            before_list += ['set_silent']

        self.__machine.add_transition(trigger=trigger,
                                      source=source, dest=dest,
                                      before=before_list, after=after)

    def accept_command(self, command):
        """
        Accepts the given command for the simulation lifecycle.

        Any error during the execution of the command,
        results in a state transition to failed so to perform a cleanup.

        :param command: the command that should be activated
        :raise: Propagate any exception coming from the execution of the command
        :raise: ValueError: command is not valid for the current state
        """
        # pylint: disable=broad-except
        try:
            self.__machine.events[command].trigger()
        except MachineError as m_e:
            raise ValueError from m_e
        except Exception as ex:
            logger.error("Error trying to execute command '%s'", command)
            logger.exception(ex)

            try:
                self.failed()
            except Exception as ex2:
                logger.error(
                    "Error trying to perform cleanup operation for command '%s'", command)
                logger.exception(ex2)
                raise ex2

            raise ex

    @staticmethod
    def set_silent(state_change):
        """
        Specifies that the given state change should not be propagated to other synchronized
        lifecycles

        :param state_change: The state change that should not be propagated
        """
        state_change.kwargs['silent'] = True

    def shutdown(self, _shutdown_event):
        """
        Shuts down this simulation lifecycle instance

        :param _shutdown_event: The event that caused the shutdown
        """
        if self.__mqtt_client is None:
            logger.debug("Double shutdown of %s lifecycle", self.mqtt_client_id)
            return

        # clear retained msg if required
        self._clear_synchronization_topic()

        self.__mqtt_client.unsubscribe(self.synchronization_topic)
        self.__mqtt_client.loop_stop()
        self.__mqtt_client.disconnect()
        self.__mqtt_client = None

    # These methods will be overridden in the derived classes, thus we need to exclude them
    # from pylint
    def initialize(self, state_change):
        """
        Gets called when the simulation should be initialized.

        :param state_change: The state change that caused the simulation to initialize.
        """
        raise NotImplementedError(
            "This state transition needs to be implemented in a concrete lifecycle")

    def start(self, state_change):
        """
        Gets called when the simulation needs to be started.

        :param state_change: The state change that caused the simulation to start.
        """
        raise NotImplementedError(
            "This state transition needs to be implemented in a concrete lifecycle")

    def pause(self, state_change):
        """
        Gets called when the simulation needs to be paused.

        :param state_change: The state change that caused the simulation to pause.
        """
        raise NotImplementedError(
            "This state transition needs to be implemented in a concrete lifecycle")

    def stop(self, state_change):
        """
        Gets called when the simulation needs to be stopped; it releases any simulation resource.

        :param state_change: The state change that caused the simulation to stop
        """
        raise NotImplementedError(
            "This state transition needs to be implemented in a concrete lifecycle")

    def fail(self, state_change):
        """
        Gets called when the simulation fails.

        :param state_change: The state change that caused the simulation to fail.
        """
        raise NotImplementedError(
            "This state transition needs to be implemented in a concrete lifecycle")

    # TODO reset support
    # def reset(self, state_change):
    #     """
    #     Gets called when the simulation is reset.
    #     :param state_change: The state change that caused the simulation to reset.
    #     """
    #     raise NotImplementedError(
    #         "This state transition needs to be implemented in a concrete lifecycle")
