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
SimulationServerInstance unit test
"""

import os
import signal
import threading
import unittest
from unittest import mock

import hbp_nrp_simserver.server as sim_server
from hbp_nrp_simserver.server.simulation_server_instance import SimulationServerInstance


class TestSimulationServerInstance(unittest.TestCase):
    base_path = "hbp_nrp_simserver.server.simulation_server_instance"

    def setUp(self):
        # python_interpreter()
        patcher_python_interpreter = mock.patch(f"{self.base_path}.python_interpreter",
                                                new="python")
        patcher_python_interpreter.start()
        self.addCleanup(patcher_python_interpreter.stop)

        # subprocess.Popen
        patcher_subprocess = mock.patch(f"{self.base_path}.subprocess")
        self.subprocess_mock = patcher_subprocess.start()
        self.popen_mock: mock.MagicMock = self.subprocess_mock.Popen
        self.addCleanup(patcher_subprocess.stop)

        # threading.Thread 
        patcher_threading = mock.patch(f"{self.base_path}.threading")
        threading_mock = patcher_threading.start()
        self.thread_mock = threading_mock.Thread
        self.event_mock = threading_mock.Event
        self.addCleanup(patcher_threading.stop)

        # open
        patcher_open = mock.patch(f"{self.base_path}.open")
        self.open_mock = patcher_open.start()
        self.addCleanup(patcher_open.stop)

        self.lifecycle_mock = mock.MagicMock()

        self.ssi = SimulationServerInstance(lifecycle=self.lifecycle_mock,
                                            sim_id=42,
                                            sim_dir="/tmp/sim_dir",
                                            main_script_path="main_script.py",
                                            exp_config_path="simulation_conf.json")

        # SimulationServerInstance.is_running
        patcher_is_running = mock.patch.object(SimulationServerInstance, "is_running",
                                               new_callable=mock.PropertyMock, return_value=False)
        self.is_running_mock = patcher_is_running.start()
        self.addCleanup(patcher_is_running.stop)

    def test_double_initialize(self):
        self.is_running_mock.return_value = True
        with self.assertRaises(Exception):
            self.assertFalse(self.ssi.is_running)

    def test_initialize(self):
        with mock.patch(f"{self.base_path}.os") as mock_os:
            mock_os.path.dirname.return_value = ""
            mock_os.environ = {"VAR": "foo"}
            mock_os.path.join.side_effect = os.path.join

            self.open_mock.return_value = mock.sentinel.open
            self.subprocess_mock.STDOUT = mock.sentinel.STDOUT

            self.ssi.initialize()

            self.open_mock.assert_called_with('/tmp/sim_dir/simulation_42.log', 'x')

            args = ["python", "simulation_server.py",
                    "--dir", "/tmp/sim_dir",
                    "--id", "42",
                    "--script", "main_script.py",
                    "--config", "simulation_conf.json"]
            self.popen_mock.assert_called_with(args,
                                               stdout=mock.sentinel.open,
                                               stderr=mock.sentinel.STDOUT,
                                               close_fds=True, env=mock_os.environ)

            self.assertTrue(self.thread_mock.called)
            self.assertTrue(self.thread_mock.return_value.start.called)

    def _monitor_thread_test(self, fail_cause, event_is_set):
        wait_event = threading.Event()

        def wait_process(return_value):
            wait_event.wait()
            return return_value

        with mock.patch(f"{self.base_path}.os"):
            self.ssi.initialize()
            self.is_running_mock.return_value = True
            self.event_mock.return_value.is_set.return_value = event_is_set  # __terminating_process_event
            self.popen_mock.return_value.wait.side_effect = lambda: wait_process(fail_cause)

            monitor_thread = threading.Thread(target=self.ssi._monitor_sim_process)
            monitor_thread.start()
            wait_event.set()
            monitor_thread.join()

    def test_monitor_thread_ok(self):
        self._monitor_thread_test(fail_cause=-signal.SIGTERM,
                                  event_is_set=True)  # Popen.wait returns negative values for signals

        self.assertFalse(self.lifecycle_mock.failed.called)  # DO NOT CALL failed()
        self.assertTrue(self.open_mock.return_value.close.called)

    def test_monitor_thread_server_init_error(self):
        self._monitor_thread_test(fail_cause=sim_server.ServerProcessExitCodes.INITIALIZATION_ERROR,
                                  event_is_set=False)

        self.assertTrue(self.lifecycle_mock.failed.called)  # DO CALL failed()
        self.assertTrue(self.open_mock.return_value.close.called)

    def test_shutdown_not_initialized(self):
        with mock.patch.object(self.ssi, "_blocking_termination") as bt_mock:
            self.ssi.shutdown()

            bt_mock.assert_not_called()

    def test_termination_not_initialized(self):
        sim_process = self.popen_mock.return_value

        self.is_running_mock.return_value = False

        self.ssi._blocking_termination()

        self.assertFalse(sim_process.terminate.called)

    def test_termination_monitor_thread_not_alive(self):
        sim_process = self.popen_mock.return_value
        monitor_thread = self.thread_mock.return_value

        self.ssi.initialize()
        self.is_running_mock.return_value = True

        monitor_thread.is_alive.return_value = False

        self.ssi._blocking_termination()

        self.assertFalse(sim_process.terminate.called)

    def test_termination_term(self):
        sim_process = self.popen_mock.return_value
        monitor_thread = self.thread_mock.return_value

        self.ssi.initialize()
        self.is_running_mock.return_value = True

        monitor_thread.is_alive.return_value = True
        monitor_thread.join.side_effect = lambda _timeout: setattr(monitor_thread.is_alive,
                                                                   "return_value", False)
        self.ssi._blocking_termination()

        self.assertFalse(sim_process.kill.called)
        self.assertEqual(monitor_thread.join.call_count, 1)

    def test_termination_kill(self):
        sim_process = self.popen_mock.return_value
        monitor_thread = self.thread_mock.return_value

        self.ssi.initialize()
        self.is_running_mock.return_value = True

        monitor_thread.is_alive.return_value = True
        monitor_thread.join.side_effect = lambda _timeout: setattr(monitor_thread.is_alive,
                                                                   "return_value", True)
        self.ssi._blocking_termination()

        self.assertTrue(sim_process.terminate.called)
        self.assertTrue(sim_process.kill.called)
        self.assertEqual(monitor_thread.join.call_count, 2)


if __name__ == '__main__':
    unittest.main()
