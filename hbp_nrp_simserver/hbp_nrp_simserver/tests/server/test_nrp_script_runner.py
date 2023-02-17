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
NRPScriptRunner unit test
"""

import unittest
from unittest import mock

import hbp_nrp_simserver.server as sim_server
from hbp_nrp_commons.tests import utilities_test
from hbp_nrp_simserver.server.nrp_script_runner import NRPScriptRunner


class TestNRPScriptRunner(unittest.TestCase):
    base_path = "hbp_nrp_simserver.server.nrp_script_runner"

    def setUp(self):
        # nrp_core_wrapper
        patcher_nrp_core_wrapper = mock.patch(f"{self.base_path}.nrp_core_wrapper")
        self.nrp_core_wrapper_mock = patcher_nrp_core_wrapper.start().NrpCoreWrapper
        self.addCleanup(patcher_nrp_core_wrapper.stop)

        # exp_conf
        patcher_exp_conf = mock.patch(f"{self.base_path}.exp_conf")
        self.exp_conf = patcher_exp_conf.start()
        self.addCleanup(patcher_exp_conf.stop)

        # logger
        patcher_logger = mock.patch(f"{self.base_path}.logger")
        self.logger_mock = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)

        # os
        patcher_os = mock.patch(f"{self.base_path}.os")
        self.os_mock = patcher_os.start()
        self.addCleanup(patcher_os.stop)

        # open
        patcher_open = mock.patch(f"{self.base_path}.open")
        self.open_mock = patcher_open.start()
        self.addCleanup(patcher_open.stop)

        # exec
        self.patcher_exec = mock.patch(f"{self.base_path}.exec")
        self.exec_mock = self.patcher_exec.start()
        self.addCleanup(self.patcher_exec.stop)

        # ast
        patcher_ast = mock.patch(f"{self.base_path}.ast")
        self.ast_parse_mock = patcher_ast.start().parse
        self.addCleanup(patcher_ast.stop)

        # threading.Thread 
        patcher_threading = mock.patch(f"{self.base_path}.threading")
        threading_mock = patcher_threading.start()
        self.thread_mock = threading_mock.Thread
        self.event_mock = threading_mock.Event
        self.addCleanup(patcher_threading.stop)

        # NRPScriptRunner
        patcher_script_runner = mock.patch(f"{self.base_path}.NRPScriptRunner")
        self.script_runner_mock = patcher_script_runner.start()
        self.addCleanup(patcher_script_runner.stop)

        self.sim_settings = sim_server.SimulationSettings(sim_id="42",
                                                          sim_dir="/tmp/sim_dir",
                                                          exp_config_file="simulation_conf.json",
                                                          main_script_file="main_script.py")

        self.publish_error = mock.MagicMock()
        self.exp_config = mock.sentinel.exp_config

        # NRPScriptRunner._set_up_script_logger
        patcher_set_up_script_logger = mock.patch.object(NRPScriptRunner, "_set_up_script_logger")
        self.set_up_script_logger_mock = patcher_set_up_script_logger.start()
        self.addCleanup(patcher_set_up_script_logger.stop)

        self.nrp_script_runner = NRPScriptRunner(self.sim_settings,
                                                 exp_config=self.exp_config,
                                                 publish_error=self.publish_error)

        self.property_patchers, self.property_mocks = utilities_test.mock_properties(
            NRPScriptRunner, self.addCleanup)

    # __init__
    def test_init(self):
        self.set_up_script_logger_mock.assert_called()

        self.assertEqual(self.nrp_script_runner.sim_settings, self.sim_settings)
        self.assertEqual(self.nrp_script_runner.exp_config, self.exp_config)
        self.assertEqual(self.nrp_script_runner.script_path, self.sim_settings.main_script_file)
        self.assertEqual(self.nrp_script_runner.sim_id, self.sim_settings.sim_id)
        self.assertEqual(self.event_mock.call_count, 2)

    # initialize
    def test_initialize_ioerror(self):
        self.open_mock.side_effect = IOError

        with self.assertRaises(IOError):
            self.nrp_script_runner.initialize()

        self.publish_error.assert_called()

    def test_initialize_syntax_error(self):
        self.ast_parse_mock.side_effect = SyntaxError

        with self.assertRaises(SyntaxError):
            self.nrp_script_runner.initialize()

        self.publish_error.assert_called()

    def test_initialize_wrapper_exception(self):
        self.nrp_core_wrapper_mock.return_value._initialize.side_effect = Exception

        with self.assertRaises(Exception):
            self.nrp_script_runner.initialize()

        self.nrp_core_wrapper_mock.assert_called()
        self.publish_error.assert_called()

    # start
    def test_start_not_initialized(self):
        self.property_mocks["is_initialized"].return_value = False

        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__exec_started_event") as started_event_mock:
            self.nrp_script_runner.start()

            started_event_mock.set.assert_not_called()

    def test_start_exec_thread_none(self):
        self.property_mocks["is_initialized"].return_value = True

        # with mock.patch.object(self.nrp_script_runner, "_NRPScriptRunner__exec_thread") as exec_thread_mock:
        #    exec_thread_mock.is_alive.return_value = False
        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__exec_started_event") as started_event_mock:
            self.nrp_script_runner.start()

            started_event_mock.set.assert_called()
            self.thread_mock.return_value.start.assert_called()

    def test_start_exec_thread_not_alive(self):
        self.property_mocks["is_initialized"].return_value = True

        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__exec_started_event") as started_event_mock:
            with mock.patch.object(self.nrp_script_runner,
                                   "_NRPScriptRunner__exec_thread") as exec_thread_mock:
                exec_thread_mock.is_alive.return_value = False

                self.nrp_script_runner.start()

                started_event_mock.set.assert_called()
                # __exec_thread has been reassigned in start() is not exec_thread_mock
                self.thread_mock.return_value.start.assert_called()

    # pause
    def test_pause(self):
        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__exec_started_event") as started_event_mock:
            self.nrp_script_runner.pause()
            started_event_mock.clear.assert_called()

    # stop
    def test_stop_ok(self):
        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__exec_stopped_event") as stopped_event_mock:
            with mock.patch.object(self.nrp_script_runner,
                                   "_NRPScriptRunner__exec_thread") as exec_thread_mock:
                exec_thread_mock.is_alive.return_value = False

                self.nrp_script_runner.stop()

                stopped_event_mock.set.assert_called()
                exec_thread_mock.join.assert_called_with(
                    sim_server.nrp_script_runner.MAX_STOP_TIMEOUT)

    def test_stop_no_join(self):
        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__exec_stopped_event") as stopped_event_mock:
            with mock.patch.object(self.nrp_script_runner,
                                   "_NRPScriptRunner__exec_thread") as exec_thread_mock:
                exec_thread_mock.is_alive.return_value = True

                self.nrp_script_runner.stop()

                stopped_event_mock.set.assert_called()
                exec_thread_mock.join.assert_called_with(
                    sim_server.nrp_script_runner.MAX_STOP_TIMEOUT)
                # should log the fail
                self.logger_mock.warning.assert_called()

    # shutdown
    def test_shutdown_not_initialized(self):
        self.property_mocks["is_initialized"].return_value = False

        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__nrp_core_wrapped") as nrp_core_wrapped_mock:
            self.nrp_script_runner.shutdown()

            nrp_core_wrapped_mock._shutdown.assert_not_called()

    def test_shutdown_initialized(self):
        self.property_mocks["is_initialized"].return_value = True

        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__nrp_core_wrapped") as nrp_core_wrapped_mock:
            self.nrp_script_runner.shutdown()

            nrp_core_wrapped_mock._shutdown.assert_called()

        # should not be initialized after shutdown
        # stop the property mock and call the real one
        self.property_patchers["is_initialized"].stop()
        self.assertFalse(self.nrp_script_runner.is_initialized)

    def test_shutdown_exception(self):
        self.property_mocks["is_initialized"].return_value = True

        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__nrp_core_wrapped") as nrp_core_wrapped_mock:
            nrp_core_wrapped_mock._shutdown.side_effect = Exception

            with self.assertRaises(Exception):
                self.nrp_script_runner.shutdown()

            nrp_core_wrapped_mock._shutdown.assert_called()
            # should log the fail
            self.logger_mock.warning.assert_called()

    # execute_script
    def test_execute_script(self):
        complete_callback_mock = mock.MagicMock()
        self.nrp_script_runner.script_source = mock.sentinel.script_source
        with mock.patch.object(self.nrp_script_runner,
                               "_NRPScriptRunner__nrp_core_wrapped") as nrp_core_wrapped_mock:
            with mock.patch.object(self.nrp_script_runner, "_hide_modules") as hide_mod_cm_mock:
                self.nrp_script_runner._NRPScriptRunner__execute_script(complete_callback_mock)

                # should use _hide_modules context manager
                hide_mod_cm_mock.return_value.__enter__.assert_called()
                # should exec self.script_source and pass a global env
                self.exec_mock.assert_called_with(mock.sentinel.script_source, mock.ANY)
                # should add mapping nrp -> nrp_core_wrapped to the global env
                script_global_env = self.exec_mock.call_args.args[1]
                self.assertEqual(script_global_env["nrp"], nrp_core_wrapped_mock)

                # should call complete_callback 
                complete_callback_mock.assert_called()

    def test_execute_script_errors(self):
        for error_class in (AttributeError, NameError, SyntaxError):
            with self.subTest(error_class=error_class):
                complete_callback_mock = mock.MagicMock()

                self.exec_mock.side_effect = error_class

                with mock.patch.object(self.nrp_script_runner, "_hide_modules"):
                    self.nrp_script_runner._NRPScriptRunner__execute_script(complete_callback_mock)

                    # should publish the error message
                    self.assertIn(f"{error_class.__name__}",
                                  self.publish_error.call_args.kwargs["msg"])
                    self.publish_error.assert_called_with(msg=mock.ANY,
                                                          error_type="Compile",
                                                          line_number=mock.ANY,
                                                          line_text=mock.ANY)
                    # should call complete_callback 
                    complete_callback_mock.assert_called()

    def test_execute_nrp_stop_exception(self):
        complete_callback_mock = mock.MagicMock()

        self.exec_mock.side_effect = sim_server.nrp_core_wrapper.NRPStopExecution

        with mock.patch.object(self.nrp_script_runner, "_hide_modules"):
            self.nrp_script_runner._NRPScriptRunner__execute_script(complete_callback_mock)

            # should log the event
            self.logger_mock.info.assert_called()

            # should call complete_callback 
            complete_callback_mock.assert_called()

    def test_execute_nrp_sim_timeout_exception(self):
        complete_callback_mock = mock.MagicMock()

        self.exec_mock.side_effect = sim_server.nrp_core_wrapper.NRPSimulationTimeout

        with mock.patch.object(self.nrp_script_runner, "_hide_modules"):
            self.nrp_script_runner._NRPScriptRunner__execute_script(complete_callback_mock)

            # should log the event
            self.logger_mock.info.assert_called()

            # should publish the error message
            self.publish_error.assert_called_with(msg=mock.ANY,
                                                  error_type="SimTimeout")

            # should call complete_callback 
            complete_callback_mock.assert_called()

    def test_execute_nrp_exception(self):
        complete_callback_mock = mock.MagicMock()

        self.exec_mock.side_effect = Exception

        with mock.patch.object(self.nrp_script_runner, "_hide_modules"):
            self.nrp_script_runner._NRPScriptRunner__execute_script(complete_callback_mock)

            # should log the event
            self.logger_mock.exception.assert_called()

            # should publish the error message
            self.publish_error.assert_called_with(msg=mock.ANY,
                                                  error_type="Runtime")

            # should call complete_callback 
            complete_callback_mock.assert_called()

    # _hide_modules
    def test_hide_modules(self):
        with mock.patch(f"{self.base_path}.sys") as sys_mock:
            mods_to_hide = ["foo", "bar", "not_imported_module_to_hide"]

            sys_mock.modules = {"foo": mock.MagicMock("foo_module"),
                                "bar": mock.MagicMock("bar_module"),
                                "do_not_hide": mock.MagicMock("do_not_hide_module")}

            with self.nrp_script_runner._hide_modules(mods_to_hide):
                self.assertNotIn("foo", sys_mock.modules)
                self.assertNotIn("bar", sys_mock.modules)
                self.assertNotIn("not_imported_module_to_hide", sys_mock.modules)
                self.assertIn("do_not_hide", sys_mock.modules)

            # restore modules
            self.assertIn("foo", sys_mock.modules)
            self.assertIn("bar", sys_mock.modules)
            self.assertIn("do_not_hide", sys_mock.modules)
            self.assertNotIn("not_imported_module_to_hide", sys_mock.modules)

    def test_hide_modules_empty_list(self):
        with mock.patch(f"{self.base_path}.sys") as sys_mock:
            orig_modules = {"foo": mock.MagicMock("foo_module")}
            sys_mock.modules = dict(orig_modules)

            with self.nrp_script_runner._hide_modules([]):
                self.assertDictEqual(orig_modules, sys_mock.modules)

            self.assertDictEqual(orig_modules, sys_mock.modules)

    def test_hide_modules_exception(self):
        with self.assertRaises(ValueError):
            with self.nrp_script_runner._hide_modules([]):
                raise ValueError


if __name__ == '__main__':
    unittest.main()
