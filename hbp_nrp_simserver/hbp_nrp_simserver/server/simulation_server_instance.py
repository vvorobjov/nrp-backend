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

# pylint: disable=redefined-builtin

import logging
import os
import signal
import subprocess
import threading
from typing import Optional, Tuple, IO, Union

import hbp_nrp_commons.simulation_lifecycle as simulation_lifecycle
import hbp_nrp_simserver.server as sim_server

from hbp_nrp_commons import get_python_interpreter

__author__ = 'NRP software team, Ugo Albanese, Sebastian Krach, Georg Hinkel'

# hbp_nrp_backend as name prefix so to use its logger
logger = logging.getLogger(f"hbp_nrp_backend.{__name__.split('.')[-1]}")

python_interpreter = get_python_interpreter()


class SimulationServerInstance:
    """
    The class that encapsulates the execution of simulation script in a simulation server
    and manages its execution in a separate process
    """

    # NOTE SimulationServer child process stopping timeout in secs
    # it should give the SimulationServer to perform the
    # (possibly) lenghty shutdown process before sending to it a SIGTERM
    MAX_STOP_TIMEOUT: float = 30.

    def __init__(self,
                 lifecycle: simulation_lifecycle.SimulationLifecycle,
                 sim_id: int,  # NOTE change here when new sim_id type
                 sim_dir: str,
                 main_script_path: str,
                 exp_config_path: str):
        """
        Creates a new un-initialized SimulationServerInstance

        :param lifecycle: The lifecycle that will control this SimulationServerInstance
        :param sim_id: the simulation id
        :param sim_dir: absolute path to the simulation directory
        :param main_script_path: path to the python source of main simulation script.
        :param exp_config_path: path to the experiment configuration file.

        """
        self.sim_id = sim_id
        self.sim_dir = sim_dir

        self._lifecycle = lifecycle
        self.main_script_path = main_script_path
        self.exp_config_path = exp_config_path

        self.__sim_process: subprocess.Popen = None
        self.__sim_process_monitoring_thread: Optional[threading.Thread] = None
        self.__sim_process_logfile: Optional[IO] = None

        # set when the __sim_process is being terminated
        self.__terminating_process_event: threading.Event = threading.Event()

    @property
    def is_running(self) -> bool:
        """
        Returns whether the simulation process is running or not

        :return: True if the simulation process is running, False otherwise.
        """
        return (self.__sim_process is not None) and (self.__sim_process.poll() is None)

    def initialize(self) -> None:
        """
        Initialize the simulation server:

        Run simulation_server.py in a subprocess, spawning a thread monitoring its execution.
        The stdout of the child process is redirected to a file named simulation_{self.sim_id}.log
        """
        if self.is_running:
            raise Exception("Simulation is already initialized.")

        # TODO what to do with simulation server logs?
        # currently, it's uploaded to user storage on shutdown.
        # If anything goes wrong while uploading it, they are deleted when the simulation directory
        # gets cleaned. Should we log it in the backend's logs too?
        logfile_path = os.path.join(self.sim_dir, f"simulation_{self.sim_id}.log")

        self.__sim_process_logfile = open(logfile_path, "x")

        logger.debug("Starting simulation process. Simulation ID '%s'", self.sim_id)

        # NOTE simulation server executable script
        sim_server_path = os.path.join(os.path.dirname(__file__), "simulation_server.py")

        args = [python_interpreter, sim_server_path,
                "--dir", str(self.sim_dir),
                "--id", str(self.sim_id),
                "--script", str(self.main_script_path),
                "--config", self.exp_config_path]

        # TODO any other extra simulation configuration
        args += ["--verbose"] if logger.getEffectiveLevel() == logging.DEBUG else []

        env_sim = os.environ.copy()
        # TODO: do we need resources folder?
        # resource_path = f"{os.path.join(self.sim_dir, 'resources')}:"
        # env_sim['PATH'] = resource_path + env_sim['PATH']
        # env_sim['PYTHONPATH'] = resource_path + env_sim['PYTHONPATH']

        self.__sim_process = subprocess.Popen(
            args,
            stdout=self.__sim_process_logfile, stderr=subprocess.STDOUT,
            close_fds=True,  # close inherited file descriptors
            env=env_sim
        )

        self.__sim_process_monitoring_thread = threading.Thread(target=self._monitor_sim_process,
                                                                daemon=True,
                                                                name="SimulationServerProcessMonitor")
        self.__sim_process_monitoring_thread.start()

        logger.debug("Simulation server process started. "
                     "Simulation ID: '%s'", self.sim_id)

    def shutdown(self) -> None:
        """
        Shuts down this simulation
        """
        try:
            self._blocking_termination()
        finally:
            self.__sim_process = None

    def _monitor_sim_process(self) -> None:
        """
        Monitor simulation process for termination and perform cleanup.
        """

        def is_signal_sent_by_us(recv_signal: Union[signal.Signals, int]):
            # signals used by us for process management
            sent_by_us: Tuple[signal.Signals] = (signal.SIGTERM, signal.SIGKILL)

            return self.__terminating_process_event.is_set() and (recv_signal in sent_by_us)

        # blocks until process termination
        return_code: int = self.__sim_process.wait()

        # terminated by a signal not sent by us in wait_terminate (i.e. SIGTERM, SIGKILL)
        # signals are returned by wait as negative integers, ignore the ones sent by us
        received_alien_signal = (return_code < 0 and
                                 not is_signal_sent_by_us(abs(return_code)))

        # terminated with an exit code.
        # positive integers can be ServerProcessExitCodes or some other exit code
        if exited_with_server_error := (return_code > 0):
            return_code_name = sim_server.ServerProcessExitCodes(return_code).name
        else:
            return_code_name = str(return_code)

        try:
            if received_alien_signal or exited_with_server_error:
                # simulation server process has failed, request transition to failed.
                # lifecycle will call self.shutdown()

                if not self.__terminating_process_event.is_set():
                    # NOTE 
                    # failed should never be called if the sim process has been stopped by us!
                    # It will cause a deadlock (unless there is a timeout on the join)
                    # since the lifecycle will never complete 
                    # the stopped transition while trying to join this thread
                    # and thus will be stuck trying to call failed.
                    self._lifecycle.failed()
        finally:
            logger.debug("Simulation Server has exited with code: '%s'. Simulation ID: '%s'",
                         return_code_name, self.sim_id)
            # clean up sim process
            self.__sim_process_logfile.close()

    def _blocking_termination(self, timeout: float = MAX_STOP_TIMEOUT) -> None:
        """
        Perform termination and block until the simulation server process has finished.

        Termination protocol is:
        - termination request -> send SIGTERM
        - kill the process -> send SIGKILL

        After any request the simulation process is waited on for timeout seconds
        before escalating.

        :param: timeout: Maximum waiting time in seconds
        """
        if not self.is_running:
            logger.debug("Shutting down an already terminated simulation. "
                         "Simulation ID: '%s'", self.sim_id)
            return

        if self.__sim_process_monitoring_thread.is_alive():
            logger.debug("Simulation process still alive - Sending SIGTERM. "
                         "Simulation ID: '%s'", self.sim_id)
            try:
                self.__sim_process.terminate()
                self.__sim_process_monitoring_thread.join(timeout)  # NOTE Waiting point

                if self.__sim_process_monitoring_thread.is_alive():
                    logger.debug("Killing the simulation process - Sending SIGKILL. "
                                 "Some child processes could still be running."
                                 "Simulation ID: '%s'", self.sim_id)
                    self.__sim_process.kill()
                    self.__sim_process_monitoring_thread.join(timeout)  # NOTE Waiting point
            except ProcessLookupError:
                logger.debug("Simulation process not found while sending signal - Ignore."
                             "Simulation ID: '%s'", self.sim_id)
