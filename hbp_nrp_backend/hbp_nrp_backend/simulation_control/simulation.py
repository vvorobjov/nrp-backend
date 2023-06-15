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
This module contains the simulation class
"""
# avoid circular import when using typing annotations PEP563
# use "import module.submodule as subm" and subm.Class
from __future__ import annotations

__author__ = 'NRP software team, Georg Hinkel'

import datetime
import logging
from typing import Optional
from flask_restful import fields

from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle
import hbp_nrp_simserver.server.simulation_server_instance as simserver

from . import timezone
from . import sim_id_type
from .backend_simulation_lifecycle import BackendSimulationLifecycle
from hbp_nrp_commons.workspace.settings import Settings

logger = logging.getLogger(__name__)


class Simulation:
    """
    The class modelling simulations
    """

    DEFAULT_EXP_CONF: str = "simulation_config.json" # same as in nrpStorageServer
    DEFAULT_MAIN_SCRIPT: str = "main_script.py"
    DEFAULT_STATE: str = 'created'
    DEFAULT_PRIVATE: bool = True

    # pylint: disable=too-many-arguments
    def __init__(self,
                 sim_id: sim_id_type,
                 experiment_id: str,
                 owner: str,
                 experiment_configuration: str = DEFAULT_EXP_CONF,
                 main_script: str = DEFAULT_MAIN_SCRIPT,
                 state: str = DEFAULT_STATE,
                 private: bool = DEFAULT_PRIVATE,
                 ctx_id: str = None,
                 token: Optional[str] = None):
        """
        Creates a new simulation

        :param sim_id: The simulation id
        :param experiment_id: The experiment ID of the experiment to be run
        :param owner: The name of the user owning the simulation
        :param experiment_configuration: (optional) The path to the experiment configuration file
        :param main_script: (optional) The path to the main_script_path file
        :param state: (optional) The initial state ('created' by default)
        :param private: (optional) A flag for private simulations (True by default)
        :param ctx_id: (optional) the request context id (collab)
        :param token: (optional) the request token
        """

        # NOTE
        # Add more fields for any other simulation-related info that the frontend might need.
        # (e.g. URLs of backend-created resources/services)
        # Add them to resource_fields too

        self.__owner = owner

        self.__sim_id = sim_id
        self.__experiment_id = experiment_id
        self.__experiment_configuration = experiment_configuration
        self.__main_script = main_script

        self.__creation_datetime: datetime.datetime = datetime.datetime.now(tz=timezone)
        self.__private = private
        self.__token = token
        self.__ctx_id = ctx_id
        
        # use mqtt_topics_prefix specified in workspace.Settings via Env Var.
        #
        # NOTE Currently, it's the same for every simulation of this backend.
        # It could be changed, in case the need arises: just use the value passed as argument.
        self.__mqtt_topics_prefix = Settings.mqtt_topics_prefix

        # simulation_server created during initialization in Lifecycle
        self.__simulation_server_instance: Optional[simserver.SimulationServerInstance] = None

        self.__lifecycle: SimulationLifecycle = BackendSimulationLifecycle(self, state)

    @property
    def simulation_server(self) -> simserver.SimulationServerInstance:
        """
        :return: The simulation server instance. Might be None if Simulation hasn't been initialized
        """
        return self.__simulation_server_instance

    @simulation_server.setter
    def simulation_server(self, new_value: simserver.SimulationServerInstance) -> None:
        """
        Sets the simulation server instance
        """
        self.__simulation_server_instance = new_value

    @property
    def main_script(self) -> str:
        """
        :return: The simulation main script
        """
        return self.__main_script

    @property
    def token(self) -> Optional[str]:
        """
        :return: the authorization token
        """
        return self.__token

    @token.setter
    def token(self, new_value: Optional[str]) -> None:
        """
        Sets the  token
        :param new_value: The new token
        """
        self.__token = new_value
    
    @property
    def ctx_id(self) -> Optional[str]:
        """
        :return: the context ID of the simulation (collab)
        """
        return self.__ctx_id

    @property
    def sim_id(self) -> str:
        """
        Gets the simulation ID
        """
        return self.__sim_id

    @property
    def owner(self) -> str:
        """
        The owner of this simulation

        :return: The owner name
        """
        return self.__owner

    @property
    def creation_datetime(self) -> datetime.datetime:
        """
        The creation datetime of this simulation

        :return: The creation datetime
        """
        return self.__creation_datetime

    @property
    def creation_date(self) -> str:
        """
        The creation date of this simulation

        :return: The creation date
        """
        return self.__creation_datetime.isoformat()

    @property
    def experiment_id(self) -> str:
        """
        :return: The experiment ID used to create the experiment
        """
        return self.__experiment_id

    @property
    def experiment_configuration(self) -> str:
        """
        The name of the experiment configuration file of the simulation

        :return: The name of the experiment configuration file of the simulation
        """
        return self.__experiment_configuration

    @property
    def private(self) -> bool:
        """
        Defines whether the simulation is based on a private experiment

        :return: A boolean defining whether the sim is private
        """
        return self.__private

    @property
    def lifecycle(self) -> SimulationLifecycle:
        """
        Gets the lifecycle of this simulation

        :return: The lifecycle instance
        """
        return self.__lifecycle

    @property
    def state(self) -> str:
        """
        Gets the state of the simulation

        :return: The state of the simulation as a string
        """
        return self.__lifecycle.state

    @state.setter
    def state(self, new_state: str) -> None:
        """
        Sets the simulation in a new state

        :param new_state: The new state
        """
        self.__lifecycle.accept_command(new_state)

    @property
    def mqtt_topics_prefix(self) -> str:
        """
        Gets the prefix to any MQTT topic name of this simulation

        :return: the prefix to any MQTT topic name of this simulation
        """
        return self.__mqtt_topics_prefix


    # for use with marshal or marshal_with
    resource_fields = {
        'state': fields.String(attribute='state'),
        'simulationID': fields.Integer(attribute='sim_id'),  # NOTE change in case of new sim_id type
        'experimentConfiguration': fields.String(attribute='experiment_configuration'),
        'mainScript': fields.String(attribute='main_script'),
        'owner': fields.String(attribute='owner'),
        'creationDate': fields.String(attribute=lambda x: x.creation_date),
        'experimentID': fields.String(attribute='experiment_id'),
        'ctxId': fields.String(attribute='ctx_id'),
        'MQTTPrefix': fields.String(attribute='mqtt_topics_prefix'),
    }

    required = ['state',
                'experimentConfiguration',
                'owner',
                'experimentID']

    required_request_fields = ["experimentID"]

