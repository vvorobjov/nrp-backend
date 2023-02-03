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
Unit tests for the error handlers
"""

__author__ = 'NRP software team, Georg Hinkel'

import json
import unittest
from unittest import mock
from hbp_nrp_backend.rest_server.tests import RestTest
from hbp_nrp_backend import NRPServicesGeneralException, NRPServicesClientErrorException
from hbp_nrp_backend.simulation_control import simulations, Simulation


class TestErrorHandlers(RestTest):

    def setUp(self):
        del simulations[:]

        # patch BackendSimulationLifecycle in simulation
        self.patcher_backend_lifecycle = mock.patch(
            "hbp_nrp_backend.simulation_control.simulation.BackendSimulationLifecycle")
        self.mock_backend_lifecycle = self.patcher_backend_lifecycle.start()

        simulations.append(Simulation(
            0, 'experiment1', 'default-owner', state='paused'))

    def tearDown(self) -> None:
        self.patcher_backend_lifecycle.stop()

    def test_general_500_error(self):
        simulations[0]._Simulation__lifecycle = mock.MagicMock()
        simulations[0]._Simulation__lifecycle.accept_command = \
            mock.Mock(side_effect=Exception("I am a general Exception"))

        response = self.client.put(
            '/simulation/0/state', data='{"state": "started"}')

        self.assertEqual(response.status_code, 500)
        response_object = json.loads(response.data)
        self.assertEqual("General error", response_object['type'])

    def test_nrp_services_general_exception(self):
        simulations[0]._Simulation__lifecycle = mock.MagicMock()
        simulations[0]._Simulation__lifecycle.accept_command = \
            mock.Mock(side_effect=NRPServicesGeneralException(
                "I am a NRPServicesGeneralException message",
                "I am a NRPServicesGeneralException type",
                data="I am NRPServicesGeneralException data"))

        response = self.client.put(
            '/simulation/0/state', data='{"state": "started"}')

        self.assertEqual(response.status_code, 500)
        response_object = json.loads(response.data)
        self.assertEqual(
            "I am a NRPServicesGeneralException message", response_object['message'])
        self.assertEqual(
            "I am a NRPServicesGeneralException type", response_object['type'])
        self.assertEqual("I am NRPServicesGeneralException data",
                         response_object['data'])

    def test_nrp_services_client_error(self):
        simulations[0]._Simulation__lifecycle = mock.MagicMock()
        simulations[0]._Simulation__lifecycle.accept_command = \
            mock.Mock(side_effect=NRPServicesClientErrorException(
                "I am a NRPServicesClientErrorException message"))

        response = self.client.put(
            '/simulation/0/state', data='{"state": "started"}')

        self.assertEqual(response.status_code, 400)
        response_object = json.loads(response.data)
        self.assertEqual(
            "I am a NRPServicesClientErrorException message", response_object['message'])
        self.assertEqual("Client error", response_object['type'])


if __name__ == '__main__':
    unittest.main()
