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
This module tests the backend implementation of the simulation lifecycle
"""

from unittest.mock import patch, MagicMock, mock_open, PropertyMock
import unittest
import os
from hbp_nrp_backend.simulation_control.backend_simulation_lifecycle import BackendSimulationLifecycle
from hbp_nrp_backend import NRPServicesGeneralException
 

PATH = os.path.split(__file__)[0]

__author__ = 'NRP software team'

_base_path = 'hbp_nrp_backend.simulation_control.backend_simulation_lifecycle'


@patch("builtins.open", mock_open(read_data='somedata'))
@patch(f'{_base_path}.user_auth.UserAuthentication', new=MagicMock())
class TestBackendSimulationLifecycle(unittest.TestCase):

    def setUp(self):
        self.simulation = MagicMock()
        # PropertyMock must be assigned to type(self.simulation)
        # see https://docs.python.org/3/library/unittest.mock.html#unittest.mock.PropertyMock
        t = type(self.simulation)
        t.sim_id= PropertyMock(return_value=42)
        t.experiment_conf = PropertyMock(return_value="simulation_config.json")
        t.experiment_id = PropertyMock(return_value="some_exp_id"),
        t.main_script = PropertyMock(return_value="main_script.py"),
        t.private = PropertyMock(return_value=True)
        t.mqtt_topics_prefix = PropertyMock(return_value="")

        # mock SimulationServerInstance
        self.patcher_simserver_instance = patch(f'{_base_path}.SimulationServerInstance')
        self.simserver_instance_mock = self.patcher_simserver_instance.start()
        self.addCleanup(self.patcher_simserver_instance.stop)

        # mock storage_client.StorageClient
        self.patcher_storage = patch(f'{_base_path}.storage_client.StorageClient')
        self.storage_mock = self.patcher_storage.start()
        self.addCleanup(self.patcher_storage.stop)

        # mock zip_util
        self.patcher_zip_util = patch(f'{_base_path}.zip_util')
        self.zip_util_mock = self.patcher_zip_util.start()
        self.addCleanup(self.patcher_zip_util.stop)
        self.zip_util_mock.extract_all.return_value = None

        # mock zip_util
        self.patcher_sim_util = patch(f'{_base_path}.SimUtil')
        self.sim_util_mock = self.patcher_sim_util.start()
        self.addCleanup(self.patcher_sim_util.stop)

        # mock os
        self.patcher_os = patch(f'{_base_path}.os')
        self.os_mock = self.patcher_os.start()
        self.addCleanup(self.patcher_os.stop)
        self.os_mock.path.join.return_value = "/some/tmp/dir/"
        self.os_mock.path.exists.return_value = True
        self.os_mock.makedirs.return_value = None

        # create a BackendSimulationLifecycle
        with patch("hbp_nrp_commons.simulation_lifecycle.mqtt"):
            self.lifecycle = BackendSimulationLifecycle(self.simulation)

        self.lifecycle.experiment_path = PATH
        self.assertEqual(None, self.lifecycle.sim_dir)

    # initialize
    def test_backend_initialize_non_storage(self):
        returned_simulation_server = MagicMock()
        type(self.simulation).simulation_server = PropertyMock(return_value=returned_simulation_server)

        self.lifecycle.initialize(MagicMock())

        # Assert Simulation server has been called
        self.assertTrue(self.simserver_instance_mock.called)
        self.assertTrue(returned_simulation_server.initialize.called)

        self.assertIsNotNone(self.lifecycle.experiment_path)

    def test_backend_initialize_storage_fail(self):

        self.storage_mock.return_value.clone_all_experiment_files.side_effect = Exception

        with self.assertRaises(NRPServicesGeneralException) as cm:
            self.lifecycle.initialize(MagicMock())

            raised_ex = cm.exception
            self.assertEqual(raised_ex.error_type, "Server Error")
            self.assertIsNotNone(raised_ex.data)

    def test_backend_sim_server_instance_initialize_fail(self):

        self.simserver_instance_mock.return_value.initialize.side_effect = Exception

        with self.assertRaises(NRPServicesGeneralException) as cm:
            self.lifecycle.initialize(MagicMock())

            raised_ex = cm.exception
            self.assertEqual(raised_ex.error_type, "Server Error")
            self.assertIsNotNone(raised_ex.data)

    # start()
    def test_backend_start(self):
        # The method does nothing currently, so we have nothing to test
        self.lifecycle.start(MagicMock())

    # stop()
    def test_backend_stop_uninitialized(self):
        type(self.simulation).simulation_server = PropertyMock(return_value=None)

        self.lifecycle.stop(MagicMock())
        self.assertFalse(self.sim_util_mock.delete_simulation_dir.called)

    @patch(f"{_base_path}.glob")
    def test_backend_stop(self, glob_mock):
        glob_mock.glob.return_value = ["file.log"]
        
        returned_simulation_server = MagicMock()
        type(self.simulation).simulation_server = PropertyMock(return_value=returned_simulation_server)

        self.lifecycle.stop(MagicMock())

        self.assertTrue(returned_simulation_server.shutdown.called)

        # _save_log_to_user_storage
        self.assertTrue(self.zip_util_mock.create_from_filelist.called)
        self.assertTrue(self.storage_mock.return_value.create_or_update.called)
        
        # finally
        self.assertTrue(self.sim_util_mock.delete_simulation_dir.called)

    def test_backend_stop_shutdown_fail(self):
        # should clean sim_dir up even when shutdown fails

        type(self.simulation).simulation_server = PropertyMock(side_effect=Exception)

        with self.assertRaises(Exception):
            self.lifecycle.stop(MagicMock())
            self.assertTrue(self.sim_util_mock.delete_simulation_dir.called)
    
    def test_backend_stop_logs_update_fail(self):
        # should clean sim_dir up even when file updates fails
        # TODO What to do on top of that?

        with patch.object(BackendSimulationLifecycle, "_save_log_to_user_storage", side_effect = Exception):
            with self.assertRaises(Exception):
                self.lifecycle.stop(MagicMock())
                self.assertTrue(self.sim_util_mock.delete_simulation_dir.called)
        
    # pause()
    def test_backend_pause(self):
        # The method does nothing currently, so we have nothing to test
        self.lifecycle.pause(MagicMock())

    def test_backend_fail(self):
        event = MagicMock()

        with patch.object(BackendSimulationLifecycle, "stop") as stop_mock:
            self.lifecycle.fail(event)
            stop_mock.assert_called_once_with(event)


if __name__ == "__main__":
    unittest.main()
