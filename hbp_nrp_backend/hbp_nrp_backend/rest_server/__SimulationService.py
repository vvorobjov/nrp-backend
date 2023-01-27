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
This module contains the REST services to create simulations
"""


__author__ = 'NRP software team, GeorgHinkel, Ugo Albanese'


import logging
import threading

from flask import request
from flask_restful import Resource, marshal_with
from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle

from . import ErrorMessages, docstring_parameter
from . import SimulationControl
from . import api
from .. import NRPServicesClientErrorException
from ..simulation_control import simulations, Simulation, sim_id_type
from ..user_authentication import UserAuthentication

# pylint: disable=R0201

logger = logging.getLogger(__name__)


class SimulationService(Resource):
    """
    The service to create simulations
    """

    comm_lock = threading.Lock()

    @docstring_parameter(ErrorMessages.SIMULATION_ANOTHER_RUNNING_409,
                         ErrorMessages.SIMULATION_CREATED_201)
    @marshal_with(Simulation.resource_fields)
    def post(self):
        # pylint: disable=R0914
        """
        Creates a new simulation in the specified state.

        :< json string experimentID: The experiment ID of the experiment
        :< json string experimentConfiguration: The file describing the experiment configuration
        :< json string mainScript: The main script of the experiment
        :< json string state: The initial state of the simulation (default: "initialized")
        :< json string owner: The simulation owner (ebrains username or 'hbp-default')
        :< json string ctxId: The context id of the collab if we are running a collab based simulation

        :> json string state: The initial state of the simulation (default: "initialized")
        :> json integer simulationID: The id of the simulation (needed for further REST calls)
        :< json string experimentConfiguration: The file describing the experiment configuration
        :< json string mainScript: The main script of the experiment
        :> json string owner: The simulation owner (ebrains username or 'hbp-default')
        :> json string creationDate: Date of creation of this simulation
        :> json string experimentID: The experiment ID of the experiment

        :status 409: {0}
        :status 201: {1}
        """
        # Use context manager to lock access to simulations while a new simulation is created
        with SimulationService.comm_lock:
            body = request.get_json(force=True)

            # check request fields
            if missing_fields := [f for f in Simulation.required_request_fields if f not in body]:
                raise NRPServicesClientErrorException(f'{" ".missing_fields.join()} not given.')

            # check if another sim is running (i.e. any sim not in a final state)
            if [s for s in simulations if not SimulationLifecycle.is_final_state(s.state)]:
                raise NRPServicesClientErrorException(
                    ErrorMessages.SIMULATION_ANOTHER_RUNNING_409, error_code=409)

            # TODO better simulation IDs
            # sim_id: uuid.UUID = uuid.uuid4() # then simulations must be a dict
            sim_id: sim_id_type = len(simulations)

        sim_experiment_id = body.get('experimentID', None)
        sim_experiment_configuration = body.get('experimentConfiguration',
                                                Simulation.DEFAULT_EXP_CONF)
        sim_main_script = body.get('mainScript', Simulation.DEFAULT_MAIN_SCRIPT)
        sim_state = body.get('state', Simulation.DEFAULT_STATE)
        sim_owner = UserAuthentication.get_user()
        ctx_id = body.get('ctxId', None)
        token = UserAuthentication.get_header_token() # TODO TEST

        sim = Simulation(sim_id,
                         sim_experiment_id,
                         sim_owner,
                         experiment_configuration=sim_experiment_configuration,
                         main_script=sim_main_script,
                         state=sim_state,
                         ctx_id=ctx_id,
                         token=token)
        simulations.append(sim)

        sim.state = "initialized"  # move to initialize state

        # 'Location' is the URL at which the newly created resource is available
        return sim, 201, {'Location': api.url_for(SimulationControl, sim_id=sim_id)} 

    @docstring_parameter(ErrorMessages.SIMULATIONS_RETRIEVED_200)
    @marshal_with(Simulation.resource_fields)
    def get(self):
        """
        Gets the list of simulations on this server.

        :status 200: {0}
        """
        # Acquire lock before getting simulation
        with SimulationService.comm_lock:
            return simulations, 200
