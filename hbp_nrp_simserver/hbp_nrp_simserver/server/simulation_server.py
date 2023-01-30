# pylint: disable=too-many-lines
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
This module implements the Simulation server application.
It is managed by a SimulationServeInstance.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from typing import List, Optional

import hbp_nrp_commons.timer as timer
import hbp_nrp_simserver.server as simserver
import hbp_nrp_simserver.server.experiment_configuration as exp_conf_utils
import hbp_nrp_simserver.server.simulation_server_lifecycle as simserver_lifecycle
from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle
from hbp_nrp_simserver.server.mqtt_notificator import MQTTNotificator
from hbp_nrp_simserver.server.nrp_script_runner import NRPScriptRunner

from hbp_nrp_commons import set_up_logger

# Warning: We do not use __name__  here, since it translates to "__main__"
logger = logging.getLogger('hbp_nrp_simserver')


def __except_hook(ex_type, value, ex_traceback):
    """
    Logs the unhandled exception

    :param ex_type: The exception type
    :param value: The exception value
    :param ex_traceback: The traceback
    """
    logger.critical("Unhandled exception of type %s: %s", ex_type, value)
    logger.exception(ex_traceback)


class SimulationServer:

    STATUS_UPDATE_INTERVAL = 1.0

    def __init__(self, sim_settings: simserver.SimulationSettings):
        """
        Create the simulation server

        :param sim_settings: The simulation settings
        """

        self.simulation_settings = sim_settings

        # set during initialization
        self.exp_config: Optional[exp_conf_utils.type_class] = None
        self._notificator: Optional[MQTTNotificator] = None
        self.__lifecycle: Optional[simserver_lifecycle.SimulationServerLifecycle] = None
        self.exit_state: str = None
        self.__nrp_script_runner: Optional[NRPScriptRunner] = None

        self.__status_update_timer = timer.Timer(SimulationServer.STATUS_UPDATE_INTERVAL,
                                                 self.publish_state_update,
                                                 name="SimServerStatusUpdateTimer")

    @property
    def nrp_script_runner(self) -> Optional[NRPScriptRunner]:
        """
        Gets the nrp_script_runner used by the server
        """
        return self.__nrp_script_runner

    @property
    def lifecycle(self):
        """
        Gets the lifecycle instance representing the current SimulationServer
        """
        return self.__lifecycle

    @property
    def simulation_id(self) -> str:
        """
        Gets the simulation ID, as configured in sim_settings, that is serviced.
        """
        return self.simulation_settings.sim_id

    @property
    def simulation_time(self) -> float:
        """
        :return: the simulation time if initialized, 0 otherwise
        """
        return self.__nrp_script_runner.simulation_time if self.is_initialized else 0.

    @property
    def real_time(self) -> float:
        """
        :return: the wall-clock time of the simulation if initialized, 0 otherwise
        """
        return self.__nrp_script_runner.real_time if self.is_initialized else 0.

    @property
    def simulation_time_remaining(self) -> float:
        """
        :return: the simulation time left until the timeout if initialized, 0 otherwise
        """
        return self.__nrp_script_runner.simulation_time_remaining \
            if self.is_initialized else 0.

    @property
    def is_initialized(self) -> bool:
        return (self._notificator is not None) and \
            (self.__nrp_script_runner is not None) and \
            (self.__lifecycle is not None)

    def initialize(self, except_hook=None):
        """
        Initialize the simulation server:
        - parse and validate the experiment configuration file
        - create the MQTT notificator
        - create NRPScriptRunner
        - create SimulationServerLifecycle
        - start the status update timer

        If anything goes wrong, the relative exception will be re-raised

        :param except_hook: A handler method for critical exceptions
        """
        # the exception will be caught and logged by the caller
        self.exp_config = exp_conf_utils.validate(
            exp_conf_utils.parse(self.simulation_settings.exp_config_file))

        # find MQTT broker address in config
        broker_address, broker_port = exp_conf_utils.mqtt_broker_address_port(
            self.exp_config)

        logger.debug("Setting up simulation Notificator")
        self._notificator = MQTTNotificator(self.simulation_id,
                                            broker_hostname=broker_address,
                                            broker_port=int(broker_port))

        try:
            logger.debug("Setting up a NRPScriptRunner")
            self.__nrp_script_runner = NRPScriptRunner(self.simulation_settings,
                                                       self.exp_config,
                                                       self.publish_error)

            logger.debug("Creating the simulation server lifecycle")
            self.__lifecycle = simserver_lifecycle.SimulationServerLifecycle(
                self, except_hook)
        except Exception:
            self._notificator.shutdown()
            raise

        self.__status_update_timer.start()

    def _create_state_message(self):
        """
        Creates a status message

        :return: A dictionary with status information
        """
        return {'realTime': self.real_time,
                'simulationTime': self.simulation_time,
                'state': self.__lifecycle.state,
                'simulationTimeLeft': self.simulation_time_remaining
                }

    def publish_state_update(self):
        """
        Publish the simulation state and stats
        """
        try:
            if not self.is_initialized:
                logger.debug(
                    "Trying to publish state even though no simulation is active."
                    " Simulation ID '%s'", self.simulation_id)
                return

            json_message = json.dumps(self._create_state_message())

            # logger.debug("Sending status message: %s."
            #             " Simulation ID '%s'", json_message, self.simulation_id)

            self._notificator.publish_status(json_message)

        # pylint: disable=broad-except
        except Exception as e:
            logger.exception(e)

    def shutdown(self):

        if not self.is_initialized:
            logger.debug("Server un initialized. Can't shutdown. "
                             "Simulation ID '%s'", self.simulation_id)
            return

        try:
            with self._notificator.task_notifier("Shutting down Simulation"):
                try:
                    if self.__lifecycle.is_failed() or self.__lifecycle.is_stopped():
                        logger.debug(
                            "Lifecycle state is already in a final state."
                            " Simulation ID '%s'", self.simulation_id)
                    else:
                        # request and wait simulation stop
                        # __lifecycle will initiate NRPScriptRunner shutdown
                        logger.debug("Requesting lifecycle to stop. "
                                     "Simulation ID '%s'", self.simulation_id)
                        self.__lifecycle.stopped()
                except Exception as e:
                    logger.error("Exception while requesting lifecycle to stop. "
                                 "Simulation ID '%s'", self.simulation_id)
                    logger.exception(e)
                else:
                    logger.debug("Waiting for lifecycle to stop. "
                                 "Simulation ID '%s'", self.simulation_id)

                    # TODO timeout and handle it
                    self.__lifecycle.done_event.wait(10.)  # NOTE Waiting point

                    logger.debug("Lifecycle has stopped. "
                                 "Simulation ID '%s'", self.simulation_id)
                finally:
                    self.exit_state = self.__lifecycle.state
                    self.__lifecycle = None
                    self.__nrp_script_runner = None

            # shutdown MQTTNotificator
            try:
                self._notificator.shutdown()
            except Exception as e:
                logger.error("The MQTT notificator could not be shut down. Simulation ID '%s'",
                             self.simulation_id)
                logger.exception(e)
            finally:
                self._notificator = None

        finally:
            self.__status_update_timer.cancel_all()

    def run(self):
        """
        This method blocks the caller until the simulation is finished
        """
        self.__lifecycle.done_event.wait()  # NOTE Waiting point

        self.publish_state_update()  # broadcast last status update before exiting
        time.sleep(1.0)
        logger.info(
            "Simulation Server main loop completed. Simulation ID '%s'", self.simulation_id)

    def publish_error(self,
                      msg: str, error_type: str,
                      line_number: int = -1, offset: int = -1, line_text: str = ""):
        """
        Sends an error message to clients (e.g. frontend)

        :param msg: The error message
        :param error_type: The error type, e.g. "Runtime"
        :param line_number: The line number where the error occurred
        :param offset: The offset
        :param line_text: The text of the line causing the error
        """
        json_str = json.dumps({"sim_id": self.simulation_id,
                               "msg": msg,
                               "error_type": error_type,
                               "fileName": self.simulation_settings.main_script_file,
                               "line_number": line_number, "offset": offset,
                               "line_text": line_text})

        if self._notificator:
            self._notificator.publish_error(json_str)
        else:
            logger.warning("Publishing an Error but a Notifier is unavailable."
                           " Simulation ID:' %s': '%s'", self.simulation_id, json_str)


def main():  # pragma: no cover

    sys.excepthook = __except_hook

    parser = argparse.ArgumentParser()

    parser.add_argument("-d", "--dir", dest="sim_dir",
                        help="The path to simulation directory. Required",
                        required=True)
    parser.add_argument("-s", "--script", dest="sim_script",
                        help="The filename of script to run. Required",
                        required=True)
    parser.add_argument("-c", "--config", dest="exp_config",
                        required=True,
                        help="The filename of the experiment configuration file. Required")
    parser.add_argument('-i', '--id', dest='sim_id',
                        required=True,
                        help="The simulation ID. Required")
    parser.add_argument('--logfile', dest='logfile',
                        help='specify the state machine logfile')
    parser.add_argument("--verbose", dest="verbose_logs", help="Increase output verbosity",
                        default=False,
                        action="store_true")

    args = parser.parse_args()

    # Initialize root logger, any logger in this process will inherit the settings
    set_up_logger(name=None, logfile_name=args.logfile,
                  level=logging.DEBUG if args.verbose_logs else logging.INFO)

    # Change working directory to experiment directory
    logger.info("Path is %s. Simulation ID '%s'", args.sim_dir, args.sim_id)
    os.chdir(args.sim_dir)

    sim_settings = simserver.SimulationSettings(sim_id=args.sim_id,
                                                sim_dir=args.sim_dir,
                                                exp_config_file=args.exp_config,
                                                main_script_file=args.sim_script)

    sim_server = SimulationServer(sim_settings)

    # pylint: disable=broad-except
    try:

        sim_server.initialize(except_hook=None)  # TODO except_hook ??
    except Exception as e:
        logger.error(
            "Simulation initialization failed. Simulation ID '%s'", sim_settings.sim_id)
        logger.exception(e)
        return simserver.ServerProcessExitCodes.INITIALIZATION_ERROR.value

    # Simulation server is now initialized

    # Event that signals when to terminate, gets set when:
    # - SIGTERM received
    # - after simserver.run has completed
    do_terminate_event = threading.Event()

    def sig_handler(sig, _frame):
        print(f"Received '{sig}'. set do_terminate_event!. Simulation ID '{sim_settings.sim_id}'")
        do_terminate_event.set()

    # SimulationServerInstance uses SIGTERM to send shutdown requests
    # keep signal handler as simple as possible.
    # delegate actual work to terminator_thread
    # Shut down gracefully with SIGINT too.
    termination_signals = [signal.SIGINT, signal.SIGTERM]

    for signum in termination_signals:
        signal.signal(signum, handler=sig_handler)

    # unblock termination_signals
    signal.pthread_sigmask(signal.SIG_UNBLOCK, termination_signals)

    # use a separate thread to handle requests since simserver.run() is blocking
    thread_return_value: List[simserver.ServerProcessExitCodes] = []
    terminator_thread = threading.Thread(target=_handle_shutdown,
                                         name="SimServerShutdownHandler",
                                         args=(sim_server,
                                               do_terminate_event,
                                               thread_return_value))
    terminator_thread.start()

    try:
        sim_server.run()  # Blocking call
    except Exception as e:
        logger.error(
            "Exception during simulation. Simulation ID '%s'", sim_settings.sim_id)
        logger.exception(e)
    finally:
        # sim_server.run() completed, let's shutdown
        do_terminate_event.set()
        terminator_thread.join()  # TODO timeout? how long? # NOTE Waiting point

    return (thread_return_value[0]
            if thread_return_value else simserver.ServerProcessExitCodes.NO_ERROR
            ).value


def _handle_shutdown(sim_server: SimulationServer,
                     terminate_event: threading.Event,
                     return_value: List[simserver.ServerProcessExitCodes]) -> None:
    """
    A thread that takes care of shutting down the simulation server
    The process starts when terminate_event gets set by
    the SIGTERM handler or after SimulationServer.run() termination.

    IF an error occurred while the simulation was running appends
    simserver.ServerProcessExitCodes.RUNNING_ERROR to return_value.
    If an error occurs during shutdown SHUTDOWN_ERROR is appended,
    otherwise NO_ERROR.
    """
    exit_codes = simserver.ServerProcessExitCodes
    sim_id = sim_server.simulation_settings.sim_id

    if not sim_server.is_initialized:
        logger.warning(
            "Shutdown. Simulation server not initialized. Simulation ID '%s'", sim_id)
    else:
        # wait on closed signal handler or SimulationServer.run() termination
        terminate_event.wait()  # NOTE Waiting point

        logger.info("Shutdown. Initiating. Simulation ID '%s'", sim_id)
        try:
            # request the simulation server to shut down
            sim_server.shutdown()
        except Exception as e:
            logger.error(
                "Shutdown. An error occurred. Simulation ID '%s'", sim_id)
            logger.exception(e)
            return_value.append(exit_codes.SHUTDOWN_ERROR)
            return

        logger.info("Shutdown. Completed. Simulation ID '%s'", sim_id)

    if SimulationLifecycle.is_error_state(sim_server.exit_state):
        return_value.append(exit_codes.RUNNING_ERROR)
        return

    # happy path
    return_value.append(exit_codes.NO_ERROR)
    return


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
