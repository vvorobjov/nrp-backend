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
Tests the simulation state service
"""
import json
import unittest
from unittest import mock
from flask import Response
from hbp_nrp_backend.rest_server import ErrorMessages
from hbp_nrp_backend.rest_server.tests import RestTest
from hbp_nrp_backend.simulation_control import simulations, Simulation
__author__ = "NRP Team, Ugo Albanese"


class TestSimulationStateService(RestTest):
    """
    Class for testing hbp_nrp_backend.rest_server.__SimulationState.
    """
    SIM_ID: int = 0
    INITIAL_STATE = 'paused'

    def setUp(self):
        # patch Simulation.state property
        # can't use PropertyMock since we need to control __set__ and __get__ independently
        self.patcher_state = mock.patch(
            'hbp_nrp_backend.simulation_control.simulation.Simulation.state')
        self.mock_state = self.patcher_state.start()
        self.mock_state.__get__ = mock.MagicMock(
            return_value=self.INITIAL_STATE)
        self.mock_state.__set__ = mock.MagicMock()
        self.addCleanup(self.patcher_state.stop)
        # patch BackendSimulationLifecycle in simulation
        self.patcher_backend_lifecycle = mock.patch(
            "hbp_nrp_backend.simulation_control.simulation.BackendSimulationLifecycle")
        self.mock_backend_lifecycle = self.patcher_backend_lifecycle.start()
        self.addCleanup(self.patcher_backend_lifecycle.stop)
        self.patcher_can_view = mock.patch(
            'hbp_nrp_backend.user_authentication.UserAuthentication.can_view')
        self.mock_can_view = self.patcher_can_view.start()
        self.mock_can_view.return_value = True
        self.addCleanup(self.patcher_can_view.stop)
        self.patcher_can_modify = mock.patch(
            'hbp_nrp_backend.user_authentication.UserAuthentication.can_modify')
        self.mock_can_modify = self.patcher_can_modify.start()
        self.mock_can_modify.return_value = True
        self.addCleanup(self.patcher_can_modify.stop)
        self.patcher_is_state = mock.patch(
            'hbp_nrp_commons.simulation_lifecycle.SimulationLifecycle.is_state')
        self.mock_is_state = self.patcher_is_state.start()
        self.mock_is_state.return_value = True
        self.addCleanup(self.patcher_is_state.stop)
        self.patcher_is_final_state = mock.patch(
            'hbp_nrp_commons.simulation_lifecycle.SimulationLifecycle.is_final_state')
        self.mock_is_final_state = self.patcher_is_final_state.start()
        self.mock_is_final_state.return_value = False
        self.addCleanup(self.patcher_is_final_state.stop)
        simulations.append(Simulation(self.SIM_ID, 'some_experiment_id', 'default-owner',
                                      state=self.INITIAL_STATE))

    def tearDown(self):
        del simulations[:]
    # GET

    def test_get_state(self):
        self.mock_state.__get__.return_value = "foobar"
        response = self.client.get(f'/simulation/{self.SIM_ID}/state')
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({"state": "foobar"}, json.loads(response.data))

    def test_get_sim_not_found(self):
        NON_EXISTENT_SIM_ID = 42
        resp = self.client.get(f'/simulation/{NON_EXISTENT_SIM_ID}/state')
        response_object = json.loads(resp.data)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         response_object['message'])
        self.assertEqual("Client error", response_object['type'])

    def test_get_user_cannot_view(self):
        self.mock_can_view.return_value = False
        resp = self.client.get(f'/simulation/{self.SIM_ID}/state')
        response_obj = json.loads(resp.data)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(
            ErrorMessages.SIMULATION_PERMISSION_401_VIEW, response_obj["message"])
    # PUT

    def test_put_state_ok(self):
        self.mock_state.__get__.return_value = "foo"
        response = self.client.put(
            f'/simulation/{self.SIM_ID}/state', data='{"state": "bar"}')
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 200)

    def test_put_sim_not_found(self):
        NON_EXISTENT_SIM_ID = 42
        resp = self.client.put(
            f'/simulation/{NON_EXISTENT_SIM_ID}/state', data='{"state": "bar"}')
        response_object = json.loads(resp.data)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         response_object['message'])
        self.assertEqual("Client error", response_object['type'])

    def test_get_user_cannot_modify(self):
        self.mock_can_modify.return_value = False
        resp = self.client.put(
            f'/simulation/{self.SIM_ID}/state', data='{"state": "bar"}')
        response_obj = json.loads(resp.data)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(ErrorMessages.SIMULATION_PERMISSION_401,
                         response_obj["message"])

    def test_put_fail_is_final_state(self):
        self.mock_is_final_state.return_value = True
        resp = self.client.put(
            f'/simulation/{self.SIM_ID}/state', data='{"state": "bar"}')
        response_obj = json.loads(resp.data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn(ErrorMessages.INVALID_STATE_TRANSITION_400,
                      response_obj["message"])

    def test_put_fail_not_is_state(self):
        self.mock_is_state.return_value = False
        resp = self.client.put(
            f'/simulation/{self.SIM_ID}/state', data='{"state": "bar"}')
        response_obj = json.loads(resp.data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid state requested", response_obj["message"])

    def test_put_missing_field(self):
        resp = self.client.put(f'/simulation/{self.SIM_ID}/state',
                               data='{"WRONG_FIELD": "bar"}')
        self.assertEqual(resp.status_code, 400)

    def test_put_invalid_transition(self):
        self.mock_state.__set__.side_effect = ValueError
        resp = self.client.put(
            f'/simulation/{self.SIM_ID}/state', data='{"state": "bar"}')
        response_obj = json.loads(resp.data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn(ErrorMessages.INVALID_STATE_TRANSITION_400,
                      response_obj["message"])


if __name__ == '__main__':
    unittest.main()
