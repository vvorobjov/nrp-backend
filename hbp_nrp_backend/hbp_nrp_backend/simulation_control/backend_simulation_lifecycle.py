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
This module contains the implementation of the backend simulation lifecycle
"""
# avoid circular import when using typing annotations PEP563
# use "import module.submodule as subm" and subm.Class
from __future__ import annotations

import glob
import itertools
import logging
import os
import tempfile
from typing import Optional

import hbp_nrp_backend.simulation_control.simulation as sim
import hbp_nrp_backend.storage_client_api.storage_client as storage_client
import hbp_nrp_backend.user_authentication as user_auth
import hbp_nrp_simserver.server as simserver
from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle
from hbp_nrp_commons.workspace.sim_util import SimUtil
from hbp_nrp_simserver.server.simulation_server_instance import SimulationServerInstance

from hbp_nrp_backend import NRPServicesGeneralException
from hbp_nrp_commons import zip_util

__author__ = 'NRP software team, Georg Hinkel, Ugo Albanese'

logger = logging.getLogger(__name__)


class BackendSimulationLifecycle(SimulationLifecycle):
    """
    This class implements the backend simulation lifecycle
    """

    # Backend should only state change towards these states.
    # In fact, Backend can't make a simulation fail.
    propagated_destinations = SimulationLifecycle.RUNNING_STATES  # anything but final states

    def __init__(self,
                 simulation: sim.Simulation,
                 initial_state: str = SimulationLifecycle.INITIAL_STATE):
        """
        Creates a new backend simulation lifecycle

        :param simulation: The simulation for which the simulation lifecycle is created
        """
        super(self).__init__(
            simserver.TOPIC_LIFECYCLE(simulation.sim_id),
            initial_state=initial_state,
            mqtt_client_id="nrp_backend",
            propagated_destinations=BackendSimulationLifecycle.propagated_destinations,
            clear_synchronization_topic=True)

        self.__simulation: sim.Simulation = simulation
        self._sim_dir: Optional[str] = None  # sim_dir created by initialize method
        self.__experiment_path: Optional[str] = None
        self.__storage_client: storage_client.StorageClient = storage_client.StorageClient()

    @property
    def simulation(self) -> sim.Simulation:
        """
        :return: the simulation controlled by this lifecycle
        """
        return self.__simulation

    @property
    def experiment_path(self):
        """
        Gets the experiment_path

        :return: The experiment_path
        """
        return self.__experiment_path

    @experiment_path.setter
    def experiment_path(self, value):
        """
        Sets the experiment_path

        """
        self.__experiment_path = value

    @property
    def sim_dir(self):
        """
        Gets the simulation root folder

        :return: The _sim_dir
        """
        return self._sim_dir

    def initialize(self, _state_change) -> None:
        """
        Initializes the simulation

        :param _state_change: The state change that caused the simulation to be initialized
        """
        sim = self.simulation
        self._sim_dir = SimUtil.init_simulation_dir(str(sim.sim_id))

        try:
            if not sim.private:
                raise NRPServicesGeneralException("Only private experiments are supported",
                                                  error_type="User Error", error_code=500)

            # file or directories (i.e. ending with "/")
            # in the experiment folder to ignore in cloning
            exclude_list = ["*.log", "*.log.zip", "logs/", '__pycache__/']

            # clone the experiment files in local temporary directory
            self.__storage_client.clone_all_experiment_files(
                token=user_auth.UserAuthentication.get_header_token(),
                experiment=sim.experiment_id,
                destination_dir=self._sim_dir,
                exclude=exclude_list
            )

            self.__experiment_path = os.path.join(self._sim_dir,
                                                  sim.experiment_configuration)

            sim.simulation_server = SimulationServerInstance(
                self,
                sim.sim_id,
                self._sim_dir,
                sim.main_script,
                sim.experiment_configuration)

            sim.simulation_server.initialize()

            logger.info("Simulation initialized. Simulation ID: '%s'", str(sim.sim_id))
        # pylint: disable=broad-except
        except Exception as ex:
            raise NRPServicesGeneralException(
                f'Error starting the simulation. ("{repr(ex)}") An exception has occurred',
                error_type="Server Error",
                data=ex) from ex

    def start(self, _state_change):
        """
        Starts the simulation

        :param _state_change: The state change that led to starting the simulation
        """
        # Nothing to do here, the starting process will be carried out
        # by SimulationServerLifecycle
        pass

    def stop(self, _state_change):
        """
        Stops the simulation:
        - uploads logs to storage
        - cleans the simulation directory up
        """
        sim_id_str: str = str(self.simulation.sim_id)

        if self.simulation.simulation_server is None:
            logger.debug("Simulation Server uninitialized, can't stop it."
                         "Simulation ID: '%s'", sim_id_str)
            return

        try:
            # NOTE
            # shutdown can't rely on simulation server's lifecycle for shutting down the simulation;
            # we must synchronously call simulation_server.shutdown(),
            # so that we are sure that the files to be persisted in the storage are available
            # in the simulation directory.
            self.simulation.simulation_server.shutdown()

            # uploads logs to storage
            try:
                # NOTE
                # save here any simulation-related file we are interested in persisting into
                # the user storage 
                self._save_log_to_user_storage()
            except Exception:
                logger.debug("Logs upload to storage failed. Simulation ID: '%s'", sim_id_str)
                # NOTE TODO what to do of simulation data in the case of a failed storage upload?
                raise
            else:
                logger.debug("Uploaded logs to storage. Simulation ID: '%s'", sim_id_str)
        finally:
            # Clean up simulation directory
            SimUtil.delete_simulation_dir(self._sim_dir)
            logger.debug("Deleted simulation dir '%s'. Simulation ID: '%s'", str(self._sim_dir),
                         sim_id_str)

        logger.info("Stopping completed. Simulation ID: '%s'", sim_id_str)

    def pause(self, _state_change):
        """
        Pauses the simulation

        :param _state_change: The state change that paused the simulation
        """
        # Nothing to do here, the pausing process will be carried out
        # by SimulationServerLifecycle
        pass

    def fail(self, state_change):
        """
        Fails the simulation

        :param state_change: The state change which resulted in failing the simulation
        """
        try:
            # delegating the cleanup to stop, no state transition is involved
            self.stop(state_change)
        finally:
            logger.info("Simulation has Failed. Simulation ID: '%s'", str(self.simulation.sim_id))

    def reset(self, _state_change):
        """
        Resets the simulation

        :param _state_change: The state change that led to resetting the simulation
        """
        logger.info("Simulation reset NOT IMPLEMENTED. Simulation ID: '%s'",
                    str(self.simulation.sim_id))

    def _save_log_to_user_storage(self):
        """
        Save logs to user storage

        """
        sim_id_str: str = str(self.simulation.sim_id)

        logs_globs = ("*.log", ".*.log")
        logs_file_lists = [glob.glob(os.path.join(self._sim_dir, gl)) for gl in
                           logs_globs]  # list of lists

        if not any(logs_file_lists):  # empty logs_file_lists
            logger.debug("No logs to save on storage. Simulation ID: '%s'",
                         sim_id_str)
            return

        logs_filename = f"simulation_{sim_id_str}.log.zip"

        temp_dest = os.path.join(tempfile.gettempdir(), logs_filename)

        zip_util.create_from_filelist(itertools.chain(*logs_file_lists),
                                      temp_dest,
                                      preserve_path=False)  # flat file hierarchy

        # upload zip to user storage
        try:
            with open(temp_dest, 'rb') as zipped_logs:
                self.__storage_client.create_or_update(
                    self.simulation.token,
                    self.simulation.experiment_id,
                    logs_filename,
                    zipped_logs.read(),
                    "application/octet-stream")
        finally:
            os.remove(temp_dest)
