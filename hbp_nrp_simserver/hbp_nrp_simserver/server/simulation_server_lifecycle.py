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
This module contains the simulation server implementation of the simulation lifecycle
"""

import logging
import threading
from typing import Callable, Optional

import hbp_nrp_commons.simulation_lifecycle as simulation_lifecycle

import hbp_nrp_simserver.server as simserver
from .simulation_server import SimulationServer
from .nrp_script_runner import NRPScriptRunner

__author__ = 'NRP software team, Georg Hinkel'


logger = logging.getLogger(__name__)


class SimulationServerLifecycle(simulation_lifecycle.SimulationLifecycle):
    """
    Implements the simulation server lifecycle of a simulation
    """

    # Simulation server should propagate to backend only state change towards these states.
    # In fact, Simulation server can't initiate any other state changes.
    propagated_destinations = ['completed', 'failed']

    def __init__(self,
                 sim_server: SimulationServer,
                 except_hook: Callable = None):

        super().__init__(simserver.TOPIC_LIFECYCLE(sim_server.simulation_id),
                         propagated_destinations=SimulationServerLifecycle.propagated_destinations,
                         mqtt_client_id="nrp_simulation_server")

        self.__server: SimulationServer = sim_server
        self.__nrp_script_runner: Optional[NRPScriptRunner] = sim_server.nrp_script_runner

        if self.__nrp_script_runner is None:
            raise ValueError("Can't create a SimulationServerLifecycle, nrp_script_runner is None")

        self.__except_hook = except_hook or logger.exception
        self.__done_event: threading.Event = threading.Event()

    @property
    def done_event(self):
        """
        Gets the event that represents when the simulation is done

        :return: An event that will be set as soon as the lifecycle is done
        """
        return self.__done_event

    def shutdown(self, shutdown_event):
        """
        Shuts down this instance of the simulation lifecycle

        :param shutdown_event: The event that caused the shutdown
        """
        # gets called by super().__shut_down_on_final_state when reaching one of the final STATES
        try:
            self.__nrp_script_runner.shutdown()
        finally:
            super().shutdown(shutdown_event)
            self.__done_event.set()  # let SimulationServer.run terminate

    def initialize(self, _state_change):
        """
        Initializes the simulation

        :param _state_change: The state change that caused the simulation to initialize
        """
        if not self.__nrp_script_runner.is_initialized:
            try:
                self.__nrp_script_runner.initialize()
            finally:
                self._clear_synchronization_topic()  # consume the intialization event, clear the topic

    def start(self, _state_change):
        """
        Starts the simulation

        :param _state_change: The state change that caused the simulation to start
        """
        try:
            # start the script and ask to call self.completed() once the execution is completed
            self.__nrp_script_runner.start(completed_callback=self.completed)
        except Exception as e:
            self.__except_hook(e)
            raise

    def stop(self, _state_change):
        """
        Stops the simulation and releases required resources

        :param _state_change: The state change that caused the simulation to stop
        """
        try:
            # stop is a final state, super().__propagate_state_change will call self.shutdown
            self.__nrp_script_runner.stop()
        # pylint: disable=broad-except
        except Exception as e:
            self.__except_hook(e)
            raise

    def fail(self, state_change):
        """
        Reacts on failures in the simulation

        :param state_change: The state change according to the failure
        """
        # delegate to stop(), simple method call.
        # No state transition triggered
        try:
            self.stop(state_change)
        finally:
            self.__server.publish_state_update()

    def pause(self, _state_change):
        """
        Pauses the simulation

        :param _state_change: The state change that caused the pause request
        """
        try:
            self.__nrp_script_runner.pause()
        except Exception as e:
            self.__except_hook(e)
            raise

    def reset(self, _state_change):
        """
        Resets the simulation

        :param _state_change:
        :return:
        """
        pass
