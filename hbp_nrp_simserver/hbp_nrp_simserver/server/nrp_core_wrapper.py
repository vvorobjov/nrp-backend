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
A Wrapper for NrpCore clients instances making it amenable to be controlled interactively.
It adds cooperative execution via thread synchronization and checks on simulation timeouts
"""

import logging
import threading
from time import time_ns as now_ns
from typing import List, Optional, Type

from hbp_nrp_commons.workspace.settings import Settings
import hbp_nrp_simserver.server.experiment_configuration as exp_conf_utils

import hbp_nrp_simserver.server as simserver

logger = logging.getLogger(__name__)


class NrpCoreWrapper:

    NRP_CORE_DEFAULT_ADDRESS_PORT = 'localhost:5345'  # TODO from some configuration instead?

    def __init__(self,
                 nrp_core_class: Type[simserver.NrpCoreClientClass],
                 sim_id: str,
                 exp_config_file: str,
                 exp_config: exp_conf_utils.type_class,  # experiment-related params
                 paused_event: threading.Event,
                 stopped_event: threading.Event):

        self.sim_id = sim_id
        self.__exp_config_file = exp_config_file
        self.__paused_event = paused_event
        self.__stopped_event = stopped_event

        # exp_config is assumed to be valid
        self.__timeout_s: float = float(exp_config.SimulationTimeout)
        self.__timestep_s: float = float(exp_config.SimulationTimestep)

        # keep internal simulation time in timestep units
        self.__max_timesteps: int = int(self.__timeout_s / self.__timestep_s)
        self.__timesteps_count: int = 0

        # Track real time as follows
        # right before nrp_core.client run_loop is run, start_time is set to the current clock time.
        # When it's completed, elapsed_time is incremented by (stop_time - start_time).
        # Thus, the real time is:
        # - elapsed_time when paused
        # - elapsed_time + (now - start_time) when running
        # time unit is ns since we use time.time_ns()
        self.__start_time: int = 0  # nsecs
        self.__elapsed_time: int = 0  # nsecs

        self.is_running: bool = False

        # datatransfer_engine's needs sim_id to use in topics' naming.
        # We pass "sim_id" overriding its "simulationID" parameter in its configuration
        # But we need to find the position of its configuration in the exp_config.EngineConfigs list
        data_engine_index: int = exp_conf_utils.engine_index(exp_config,
                                                             "datatransfer_grpc_engine")

        conf_overrides: List[str] = [""]  # empty string to ease string joining with str.join()
        conf_overrides.append(f"EngineConfigs.{data_engine_index}.simulationID={sim_id}")

        # We override the MQTTBroker address if specified in workspace.Settings via Env Vars
        if not Settings.is_mqtt_broker_default:
            mqtt_address_str = f"{Settings.mqtt_broker_host}:{Settings.mqtt_broker_port}"
            conf_overrides.append(f"EngineConfigs.{data_engine_index}.MQTTBroker={mqtt_address_str}")

        conf_overrides_str = ' -o '.join(conf_overrides).strip()

        nrp_core_args = [conf_overrides_str]  # NOTE append nrp_core args e.g. "--cloglevel=trace"
        nrp_core_args_str = " ".join(nrp_core_args)

        # Configurations Assumptions:
        # - address is 'localhost:5345'
        # - current directory is the experiment directory
        logger.debug("Instantiating nrp-core client: "
                     "%s(%s, config_file=%s, args=%s) ",
                     nrp_core_class.__name__,
                     self.NRP_CORE_DEFAULT_ADDRESS_PORT,
                     self.__exp_config_file, nrp_core_args_str)

        self.__nrp_core_client_instance = nrp_core_class(self.NRP_CORE_DEFAULT_ADDRESS_PORT,
                                                         config_file=self.__exp_config_file,
                                                         args=nrp_core_args_str)

    def _initialize(self):
        self.__nrp_core_client_instance.initialize()

    def _shutdown(self):
        self.__nrp_core_client_instance.shutdown()

    @property
    def max_timesteps(self) -> int:
        """
        return: configured timeout / configured timestep as int
        """
        return self.__max_timesteps

    @property
    def simulation_time(self) -> float:
        """"
        :return: the simulation time in seconds as a float
        """
        return float(self.__timesteps_count * self.__timestep_s)  # in secs

    @property
    def simulation_time_remaining(self) -> float:
        """"
        :return: the simulation time remaining until the configured timeout in seconds as a float
        """
        return float((self.__max_timesteps - self.__timesteps_count) * self.__timestep_s)  # in secs

    @property
    def real_time(self) -> float:
        """"
        :return: The wall-clock elapsed execution time in secs as a float
        """
        time_delta = (now_ns() - self.__start_time) if self.is_running else 0.
        return float((self.__elapsed_time + time_delta) * 1e-9)

    def run_loop(self, num_iterations: int = 1, json_data: Optional[str] = None) -> Optional[dict]:
        """
        Ask to advance the simulation of num_iterations timesteps.

        In the case such number of iterations will result in the timeout being reached,
        an NRPSimulationTimeout exception will be raised; the simulation won't be advanced.

        See nrp_core.client.NrpCore.run_loop for further details.

        :raises: NRPSimulationTimeout if running for num_iterations will exceed the configured
                 simulation timeout (i.e. curr_timestep + num_iterations > max_timestep)
        :raises

        :return: same as NrpCore.run_loop, i.e any JSON data passed in the response or None
        """

        logger.debug("run_loop: waiting on paused event. Simulation ID '%s'", self.sim_id)
        # set by NRPScriptRunner.pause() and cleared by NRPScriptRunner.start()
        self.__paused_event.wait() # NOTE Waiting
        logger.debug("run_loop: wait on paused event over. Simulation ID '%s'", self.sim_id)

        # check if we have been asked to stop
        if self.__stopped_event.is_set():
            logger.debug("run_loop: Stop event is set! raise NRPStopExecution. "
                         "Simulation ID '%s'", self.sim_id)
            raise NRPStopExecution()

        # Check simulation timeout boundary
        # if __max_timesteps is not a multiple of num_iterations,
        # the last (self.__max_timesteps % num_iterations) timesteps won't be executed.
        # The other behaviour will require a change in the method signature.
        # In fact, since it will be possible to run fewer timesteps than required,
        # the user will have to know how many have been actually run.
        # e.g.
        # loops_actually_run = run_loop(requested_loops)
        # 0 <= loops_actually_run <= requested_loops
        if (self.__timesteps_count + num_iterations) > self.__max_timesteps:
            raise NRPSimulationTimeout("The number of iteration requested will exceed the timeout")

        self.__start_time = now_ns()
        self.is_running = True

        try:
            # delegate run_loop to wrapped NrpCore instance
            # NOTE This is subject to changes in NrpCore's API
            loop_result: Optional[dict] = self.__nrp_core_client_instance.run_loop(num_iterations,
                                                                                   json_data)
        finally:
            # in case of run_loop raising an exception,
            # we don't know how many iterations have been completed, don't count them.
            # the simulation can't go on anyway
            self.__elapsed_time += now_ns() - self.__start_time
            self.is_running = False

        # time keeping. Ideally, NrpCore should take care of it
        self.__timesteps_count += num_iterations

        logger.debug("run_loop: loop completed. Simulation ID '%s'", self.sim_id)

        return loop_result

    def stop(self):
        raise NotImplementedError("stop() is not available")

    def reset(self):
        raise NotImplementedError("reset() is not available")

    def shutdown(self):
        raise NotImplementedError("shutdown() is not available")

    def initialize(self):
        raise NotImplementedError("initialize() is not available")


class NRPStopExecution(Exception):
    """
    Raised by NrpCoreWrapped.run_loop when called in a stopped state
    """
    pass


class NRPSimulationTimeout(Exception):
    """
    Raised by NrpCoreWrapped.run_loop when as simulation timeout has been reached
    """
    pass
