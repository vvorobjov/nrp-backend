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
This module contains the REST implementation for the simulation control
"""
__author__ = 'NRP software team, GeorgHinkel'

from flask_restful import Resource, abort, marshal_with

from hbp_nrp_backend.rest_server import ErrorMessages, docstring_parameter
from hbp_nrp_backend.simulation_control import Simulation, get_simulation
from hbp_nrp_backend.user_authentication import UserAuthentication

from hbp_nrp_backend import NRPServicesWrongUserException, NRPServicesClientErrorException


# pylint: disable=no-self-use

class SimulationControl(Resource):
    """
    The resource to get a simulation
    """
    @docstring_parameter(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         ErrorMessages.SIMULATION_PERMISSION_401_VIEW,
                         ErrorMessages.SIMULATION_RETRIEVED_200)
    @marshal_with(Simulation.resource_fields)
    def get(self, sim_id):
        """
        Gets the simulation with the specified simulation id

        :param sim_id: The simulation ID

        :> json string state: The current state of the simulation
        :> json integer simulationID: The id of the simulation (needed for further REST calls)
        :> json string environmentConfiguration: Path and name of the environment configuration file
        :> json string owner: The simulation owner (Ebrains user id or 'hbp-default')
        :> json string creationDate: Date of creation of this simulation
        :> json string experimentID: The experiment ID if the experiment is using the storage

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
            raise NRPServicesWrongUserException(message=ErrorMessages.SIMULATION_PERMISSION_401_VIEW)

        return simulation, 200
