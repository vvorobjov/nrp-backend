# -*- coding: utf-8 -*-
# Failing test about non ascii character? -> The line above (encoding) has to be the first of the file.

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
Code for testing all classes in hbp_nrp_backend.rest_server.__SimulationControl
"""
__author__ = 'NRP software team'

import unittest
from unittest import mock
import json
from hbp_nrp_backend.simulation_control import simulations, Simulation
from hbp_nrp_backend.rest_server import ErrorMessages

from hbp_nrp_backend.rest_server.tests import RestTest


class TestSimulationControl(RestTest):
    """
    Class for testing hbp_nrp_backend.rest_server.__SimulationControl
    """
    SIM_ID: int = 0
    INITIAL_STATE = 'paused'

    def setUp(self):

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

        simulations.append(Simulation(self.SIM_ID, 'some_experiment_id', 'default-owner',
                                      state=self.INITIAL_STATE))

    def tearDown(self):
        del simulations[:]

    def test_ok(self):
        resp = self.client.get(f'/simulation/{self.SIM_ID}')

        response_object = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(response_object.keys(),
                         Simulation.resource_fields.keys())

    @mock.patch("hbp_nrp_backend.rest_server.__SimulationControl.get_simulation")
    def test_sim_not_found(self, get_simulation_mock):

        get_simulation_mock.side_effect = ValueError()

        resp = self.client.get(f'/simulation/{self.SIM_ID}')

        response_object = json.loads(resp.data)

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(ErrorMessages.SIMULATION_NOT_FOUND_404,
                         response_object['message'])
        self.assertEqual("Client error", response_object['type'])

    def test_user_cannot_view(self):
        self.mock_can_view.return_value = False

        resp = self.client.get(f'/simulation/{self.SIM_ID}')

        response_obj = json.loads(resp.data)

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(
            ErrorMessages.SIMULATION_PERMISSION_401_VIEW, response_obj["message"])


if __name__ == '__main__':
    unittest.main()
