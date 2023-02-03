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
Unit tests for the simulation setup
"""

__author__ = 'NRP software team, GeorgHinkel'


import unittest
import json
import datetime
import time
from hbp_nrp_backend.rest_server import ErrorMessages
from hbp_nrp_backend.rest_server.__SimulationService import SimulationService
import unittest
import threading
from unittest import mock
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server.tests import RestTest
from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle


class TestSimulationService(RestTest):
    SIM_ID: int = 0

    def setUp(self):
        self.response = []
        self.now = datetime.datetime.now()

        # patch state property of simulation.Simulation
        # can't use PropertyMock since we need to control __set__ and __get__ independently
        self.patcher_state = mock.patch(
            'hbp_nrp_backend.simulation_control.simulation.Simulation.state', new_callable=mock.PropertyMock)
        self.mock_state = self.patcher_state.start()
        # self.mock_state.__get__ = mock.MagicMock()
        # self.mock_state.__set__ = mock.MagicMock()
        self.addCleanup(self.patcher_state.stop)

        # patch BackendSimulationLifecycle in simulation
        self.patcher_backend_lifecycle = mock.patch(
            "hbp_nrp_backend.simulation_control.simulation.BackendSimulationLifecycle")
        self.mock_backend_lifecycle = self.patcher_backend_lifecycle.start()
        self.addCleanup(self.patcher_backend_lifecycle.stop)

        self.patcher_comm_lock = mock.patch(
            'hbp_nrp_backend.rest_server.__SimulationService.SimulationService.comm_lock', wraps=threading.Lock())
        self.mock_comm_lock = self.patcher_comm_lock.start()
        self.mock_comm_lock.__enter__ = mock.MagicMock()
        self.mock_comm_lock.__exit__ = mock.MagicMock()
        self.addCleanup(self.patcher_comm_lock.stop)

    def tearDown(self):
        del simulations[:]

    # GET
    def test_get_simulation_ok(self):  # , _mock_state_property):

        def sim_field_to_attribute(field_name):
            # Mapping between response fields and Simulation attributes is defined in Simulation.resource_fields
            return Simulation.resource_fields[field_name].attribute

        # create a simulation
        simulations.append(Simulation(
            sim_id=0, experiment_id='some_experiment_id', owner='default-owner', state="paused"))
        self.mock_state.return_value = "paused"

        self._get_service()
        response_object = json.loads(self.response.data)

        # comm_lock should have been used as context manager
        self.assertTrue(self.mock_comm_lock.__enter__.called)
        self.assertTrue(self.mock_comm_lock.__exit__.called)
        self.assertEqual(self.response.status_code, 200)

        # for any simulation test response fields
        for i, sim in enumerate(simulations):
            # should contain any required field
            self.assertEqual(response_object[i].keys(
            ), Simulation.resource_fields.keys())

            for required_response_field in Simulation.required:
                # the field in the response should match the simulation attribute
                self.assertEqual(response_object[i][required_response_field],
                                 getattr(sim, sim_field_to_attribute(required_response_field)))

    def _get_service(self):
        self.response = self.client.get('/simulation')

    # POST
    def _postService(self):
        self.response = self.client.post('/simulation',
                                         data=json.dumps({"experimentID": "my_cloned_experiment"}))

    def test_post_missing_field(self):
        self.patcher_comm_lock.stop()
        resp = self.client.post(
            '/simulation', data=json.dumps({"WRONG_FIELD": "WRONG_VALUE"}))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(len(simulations), 0)

    def test_post_another_sim_running(self):
        self.patcher_comm_lock.stop()

        # for any running state
        for running_state in SimulationLifecycle.RUNNING_STATES:
            sim_id = 0

            # add a running simulation
            sim = Simulation(sim_id=sim_id, experiment_id='some_experiment_id', owner='default-owner',
                             state=running_state)

            simulations.append(sim)
            sim.state.return_value = running_state

            resp = self.client.post(
                '/simulation', data=json.dumps({"experimentID": "my_cloned_experiment"}))
            response_obj = json.loads(resp.data)

            self.assertEqual(resp.status_code, 409)
            self.assertIn(
                ErrorMessages.SIMULATION_ANOTHER_RUNNING_409, response_obj["message"])

            del simulations[sim_id]

    @mock.patch('hbp_nrp_backend.simulation_control.simulation.datetime')
    def test_simulation_service_post(self, mocked_date_time):
        mocked_date_time.datetime.now = mock.MagicMock(return_value=self.now)

        self.mock_state.return_value = "paused"

        self.response = self.client.post('/simulation',
                                         data=json.dumps({"experimentID": "my_cloned_experiment"}))

        # comm_lock should have been used as context manager
        self.assertTrue(self.mock_comm_lock.__enter__.called)
        self.assertTrue(self.mock_comm_lock.__exit__.called)

        self.assertEqual(self.response.status_code, 201)
        self.assertEqual(self.response.headers['Location'], '/simulation/0')

        expected_response_data = {
            'state': "paused",
            'simulationID': 0,
            'experimentConfiguration': Simulation.DEFAULT_EXP_CONF,
            'mainScript': Simulation.DEFAULT_MAIN_SCRIPT,
            'creationDate': self.now.isoformat(),
            'owner': 'default-owner',
            'experimentID': "my_cloned_experiment",
            'ctxId': None
        }

        self.assertDictEqual(
            json.loads(self.response.data.strip().decode()),
            expected_response_data)

    def test_simulation_service_wrong_method(self):
        rqdata = {
            "experimentID": "my_cloned_experiment",
        }
        response = self.client.put('/simulation', data=json.dumps(rqdata))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(len(simulations), 0)


if __name__ == '__main__':
    unittest.main()
