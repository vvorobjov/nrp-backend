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
This module contains the REST implementation for the control of the simulation state
"""

__author__ = 'NRP software team, Georg Hinkel'

from flask import request
from flask_restful import Resource, marshal_with, fields
from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle

from . import ErrorMessages
from . import docstring_parameter
from .. import NRPServicesClientErrorException
from .. import NRPServicesStateException, NRPServicesWrongUserException
from ..simulation_control import get_simulation
from ..user_authentication import UserAuthentication


# pylint: disable=R0201


class SimulationState(Resource):
    """
    The resource to control the state of the simulation.

    Allowed state values are defined in
    'hbp_nrp_commons.sim_lifecycle.SimulationLifecycle.STATES'
    """

    class _State:
        """
        State of a simulation. Allowed values are:
        'hbp_nrp_commons.sim_lifecycle.SimulationLifecycle.STATES'

        Only used for marshaling responses with flask_restful.marshal_with
        """

        resource_fields = {
            'state': fields.String()
        }
        required = ['state']
        required_request_fields = ["state"]

    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401_VIEW,
                         ErrorMessages.STATE_RETRIEVED_200)
    @marshal_with(_State.resource_fields)
    def get(self, sim_id):
        """
        Gets the state of the simulation with the specified simulation id.
        Possible values are simulation_lifecycle.SimulationLifecycle.STATES.

        :param sim_id: The simulation id

        :> json string state: The state of the simulation

        :status 404: {0}
        :status 401: {1}
        :status 200: {2}
        """

        try:
            simulation = get_simulation(sim_id)
        except ValueError:
            raise NRPServicesClientErrorException(
                ErrorMessages.SIMULATION_NOT_FOUND_404, error_code=404)

        if not UserAuthentication.can_view(simulation):
            raise NRPServicesWrongUserException(
                message=ErrorMessages.SIMULATION_PERMISSION_401_VIEW)

        # NOTE "state" attribute of "simulation" gets returned thanks to marshal_with
        return simulation, 200

    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401,
                         ErrorMessages.INVALID_STATE_TRANSITION_400,
                         ErrorMessages.STATE_APPLIED_200)
    @marshal_with(_State.resource_fields)
    def put(self, sim_id: str):
        """
        Sets the simulation with the given name into a new state. Allowed values are:
        created, initialized, started, paused, stopped

        :param sim_id: The simulation id

        :< json string state: The state of the simulation to set

        :> json string state: The state of the simulation

        :status 404: {0}
        :status 401: {1}
        :status 400: {2}
        :status 200: {3}
        """
        try:
            simulation = get_simulation(sim_id)
        except ValueError:
            raise NRPServicesClientErrorException(
                ErrorMessages.SIMULATION_NOT_FOUND_404, error_code=404)

        if not UserAuthentication.can_modify(simulation):
            raise NRPServicesWrongUserException(
                ErrorMessages.SIMULATION_PERMISSION_401)

        if SimulationLifecycle.is_final_state(simulation.state):
            raise NRPServicesStateException(
                f"{ErrorMessages.INVALID_STATE_TRANSITION_400} (The simulation requested is finalized)"
            )

        body = request.get_json(force=True)

        if missing_fields := [f for f in self._State.required_request_fields
                              if f not in body]:
            raise NRPServicesClientErrorException(f'{" ".join(missing_fields)} not given.')

        requested_state = body['state']

        # validate state request
        if not SimulationLifecycle.is_state(requested_state):
            raise NRPServicesStateException(f"Invalid state requested: ({requested_state})")

        try:
            simulation.state = requested_state
        except ValueError:
            raise NRPServicesStateException(
                f"{ErrorMessages.INVALID_STATE_TRANSITION_400} ('{simulation.state}' -> '{requested_state}')"
            )

        return simulation, 200
