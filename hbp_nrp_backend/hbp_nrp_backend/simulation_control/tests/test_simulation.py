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
Test file for testing hbp_nrp_backend.simulation_control.Simulation
"""

__author__ = 'NRP software team'

import unittest
from unittest import mock
from hbp_nrp_backend.simulation_control import Simulation

class TestSimulation(unittest.TestCase):

    def setUp(self):
        self.patcher_state = mock.patch('hbp_nrp_backend.simulation_control.simulation.Simulation.state', new_callable=mock.PropertyMock)
        self.mock_state = self.patcher_state.start()
        self.addCleanup(self.patcher_state.stop)

        # patch BackendSimulationLifecycle in simulation
        self.patcher_backend_lifecycle = mock.patch(
            "hbp_nrp_backend.simulation_control.simulation.BackendSimulationLifecycle")
        self.mock_backend_lifecycle = self.patcher_backend_lifecycle.start()
        self.addCleanup(self.patcher_backend_lifecycle.stop)


    def test_new_simulation(self):
        sim = Simulation(sim_id=0, experiment_id='some_exp_id', owner='some_owner')

        self.assertIsNotNone(sim.lifecycle)
        self.assertIsNotNone(sim.creation_datetime)
        self.assertEqual(sim.experiment_configuration, Simulation.DEFAULT_EXP_CONF)
        self.assertEqual(sim.main_script, Simulation.DEFAULT_MAIN_SCRIPT)
        self.assertEqual(sim.private, Simulation.DEFAULT_PRIVATE)

        self.mock_backend_lifecycle.assert_called_with(sim, Simulation.DEFAULT_STATE)

    
    def test_state(self):
        self.patcher_state.stop()

        # a unique value to be tested later for identity
        state_created = mock.sentinel.state_created
        
        # self.mock_backend_lifecycle.return_value is the BackendSimulationLifecycle instance created
        # by Simulation's __init__
        self.mock_backend_lifecycle.return_value = mock.MagicMock(state=state_created)

        sim = Simulation(sim_id=0, experiment_id='some_exp_id', owner='some_owner', state=state_created)

        # get state
        state_got = sim.state
        self.assertIs(state_got, state_created)

        # set state
        sim.state = "initialized"

        self.mock_backend_lifecycle.return_value.accept_command.assert_called_with("initialized")


    

if __name__ == '__main__':
    unittest.main()
