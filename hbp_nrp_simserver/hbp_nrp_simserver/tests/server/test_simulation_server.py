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
SimulationServer unit test
"""

import types
import typing
import unittest
from unittest import mock

import hbp_nrp_simserver.server as sim_server
from hbp_nrp_simserver.server.simulation_server import SimulationServer


def get_properties(klass: typing.Type) -> typing.List[str]:
    """Returns a list of property names belonging to klass"""
    return [p for p in dir(klass) if issubclass(property, getattr(klass, p).__class__)]


class TestSimulationServer(unittest.TestCase):
    base_path = "hbp_nrp_simserver.server.simulation_server"

    def setUp(self):
        # threading.Thread 
        patcher_threading = mock.patch(f"{self.base_path}.threading")
        threading_mock = patcher_threading.start()
        self.thread_mock = threading_mock.Thread
        self.event_mock = threading_mock.Event
        self.addCleanup(patcher_threading.stop)

        # timer.Timer
        patcher_timer = mock.patch(f"{self.base_path}.timer")
        self.timer_mock = patcher_timer.start().Timer
        self.addCleanup(patcher_timer.stop)

        # simserver_lifecycle
        patcher_lifecycle = mock.patch(f"{self.base_path}.simserver_lifecycle")
        self.lifecycle_mock = patcher_lifecycle.start().SimulationServerLifecycle
        self.addCleanup(patcher_lifecycle.stop)

        # exp_conf_utils
        patcher_exp_conf_utils = mock.patch(f"{self.base_path}.exp_conf_utils")
        self.exp_conf_utils_mock = patcher_exp_conf_utils.start()
        self.addCleanup(patcher_exp_conf_utils.stop)

        # Settings
        patcher_settings = mock.patch(f"{self.base_path}.Settings")
        self.settings_mock = patcher_settings.start()
        self.settings_mock.is_mqtt_broker_default = False
        self.addCleanup(patcher_settings.stop)

        # SimulationLifecycle
        patcher_simulation_lifecycle = mock.patch(f"{self.base_path}.SimulationLifecycle")
        self.simulation_lifecycle_mock = patcher_simulation_lifecycle.start()
        self.addCleanup(patcher_simulation_lifecycle.stop)

        # simserver
        patcher_simserver = mock.patch(f"{self.base_path}.simserver")
        self.simserver_mock = patcher_simserver.start()
        self.addCleanup(patcher_simserver.stop)

        # logger
        patcher_logger = mock.patch(f"{self.base_path}.logger")
        self.logger_mock = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)

        # signal
        patcher_signal = mock.patch(f"{self.base_path}.signal")
        self.signal_mock = patcher_signal.start()
        self.addCleanup(patcher_signal.stop)

        # os
        patcher_os = mock.patch(f"{self.base_path}.os")
        self.os_mock = patcher_os.start()
        self.addCleanup(patcher_os.stop)

        # MQTTNotificator
        patcher_notificator = mock.patch(f"{self.base_path}.MQTTNotificator")
        self.notificator_mock = patcher_notificator.start()
        self.addCleanup(patcher_notificator.stop)

        # NRPScriptRunner
        patcher_script_runner = mock.patch(f"{self.base_path}.NRPScriptRunner")
        self.script_runner_mock = patcher_script_runner.start()
        self.addCleanup(patcher_script_runner.stop)

        sim_settings = sim_server.SimulationSettings(sim_id="42",
                                                     sim_dir="/tmp/sim_dir",
                                                     exp_config_file="simulation_conf.json",
                                                     main_script_file="main_script.py")

        self.sim_server = SimulationServer(sim_settings)

        # mock SimulationServer properties
        self.property_patchers: typing.Dict[str, mock._patch[mock._Mock]] = {}
        self.property_mocks: typing.Dict[str, mock.PropertyMock] = {}

        for prop in get_properties(SimulationServer):
            patcher = mock.patch.object(SimulationServer, prop,
                                        new_callable=mock.PropertyMock)
            self.property_patchers[prop] = patcher
            self.property_mocks[prop] = patcher.start()
            self.addCleanup(patcher.stop)

    # __init__
    def test_init(self):
        self.timer_mock.assert_called_with(SimulationServer.STATUS_UPDATE_INTERVAL,
                                           mock.ANY,
                                           name=mock.ANY)

    # publish_state
    def test_publish_state_update_not_initialized(self):
        self.property_mocks["is_initialized"].return_value = False
        self.sim_server.publish_state_update()
        self.notificator_mock.return_value.publish_status.assert_not_called()

    def test_publish_state_update_exception(self):
        self.property_mocks["is_initialized"].return_value = True
        with mock.patch.object(self.sim_server, "_create_state_message", side_effect=Exception):
            self.sim_server.publish_state_update()
            self.logger_mock.exception.assert_called()

    def test_publish_state_update(self):
        self.property_mocks["is_initialized"].return_value = True
        with mock.patch.object(self.sim_server, "_notificator") as _notificator_mock:
            with mock.patch.object(self.sim_server, "_create_state_message"):
                with mock.patch(f"{self.base_path}.json") as json_mock:
                    json_mock.dumps.return_value = mock.sentinel.json_msg

                    self.sim_server.publish_state_update()
                    _notificator_mock.publish_status.assert_called_with(mock.sentinel.json_msg)

    # initialize
    def test_initialize(self):
        self.settings_mock.is_mqtt_broker_default = True
        self.exp_conf_utils_mock.mqtt_broker_host_port.return_value = ("localhost", 1883)

        self.sim_server.initialize(mock.sentinel.except_hook)

        self.exp_conf_utils_mock.mqtt_broker_host_port.assert_called_with(
            self.exp_conf_utils_mock.validate.return_value)
        self.notificator_mock.assert_called_once()
        self.script_runner_mock.assert_called_once()
        self.lifecycle_mock.assert_called_with(self.sim_server, mock.sentinel.except_hook)
        self.timer_mock.return_value.start.assert_called()

    def test_initialize_exp_conf_validate_exception(self):
        # exp_conf_utils_mock.validate raises 
        self.exp_conf_utils_mock.validate.side_effect = ValueError

        with self.assertRaises(ValueError):
            self.sim_server.initialize()
            # should propagate the exception 

    def test_initialize_nrp_script_runner_exception(self):
        # NRPScriptRunner raises 
        self.script_runner_mock.side_effect = Exception

        with self.assertRaises(Exception):
            self.sim_server.initialize()
            self.notificator_mock.return_value.shutdown.assert_called()

    def test_initialize_lifecycle_exception(self):
        # SimulationServerLifecycle raises 
        self.lifecycle_mock.side_effect = Exception

        with self.assertRaises(Exception):
            self.sim_server.initialize()
            self.notificator_mock.return_value.shutdown.assert_called()

    # shutdown
    def test_shutdown_not_initialized(self):
        self.property_mocks["is_initialized"].return_value = False
        self.sim_server.shutdown()
        self.lifecycle_mock.done_event.wait.assert_not_called()

    def test_shutdown_failed_state(self):
        self.sim_server.initialize()
        self.property_mocks["is_initialized"].return_value = True

        self.lifecycle_mock.return_value.state = mock.sentinel.failed
        self.lifecycle_mock.return_value.is_failed.return_value = True

        self.sim_server.shutdown()

        self.lifecycle_mock.return_value.done_event.wait.assert_called()
        self.assertIs(self.sim_server.exit_state, mock.sentinel.failed)
        self.notificator_mock.return_value.shutdown.assert_called()

        # should not be initialized
        self.property_patchers["is_initialized"].stop()
        self.assertFalse(self.sim_server.is_initialized)

        # should cancel the status update timer
        self.timer_mock.return_value.cancel_all.assert_called()

    def test_shutdown_running_state(self):
        self.sim_server.initialize()
        self.property_mocks["is_initialized"].return_value = True

        self.lifecycle_mock.return_value.is_failed.return_value = False
        self.lifecycle_mock.return_value.is_stopped.return_value = False

        self.lifecycle_mock.return_value.state = mock.sentinel.stopped

        self.sim_server.shutdown()

        # should stop the lifecycle
        self.lifecycle_mock.return_value.stopped.assert_called()

        self.lifecycle_mock.return_value.done_event.wait.assert_called()
        self.assertIs(self.sim_server.exit_state, mock.sentinel.stopped)
        self.notificator_mock.return_value.shutdown.assert_called()

        # should not be initialized
        self.property_patchers["is_initialized"].stop()
        self.assertFalse(self.sim_server.is_initialized)

        # should cancel the status update timer
        self.timer_mock.return_value.cancel_all.assert_called()

    def test_shutdown_stop_exception(self):
        self.sim_server.initialize()
        self.property_mocks["is_initialized"].return_value = True

        self.lifecycle_mock.return_value.is_failed.return_value = False
        self.lifecycle_mock.return_value.is_stopped.return_value = False

        self.lifecycle_mock.return_value.stopped.side_effect = Exception

        self.sim_server.shutdown()

        # should log the exception
        self.logger_mock.error.assert_called()
        self.logger_mock.exception.assert_called()

        # should not call wait
        self.lifecycle_mock.return_value.done_event.wait.assert_not_called()

        self.notificator_mock.return_value.shutdown.assert_called()

        # should not be initialized
        self.property_patchers["is_initialized"].stop()
        self.assertFalse(self.sim_server.is_initialized)

        # should cancel the status update timer
        self.timer_mock.return_value.cancel_all.assert_called()

    def test_shutdown_notificator_exception(self):
        self.sim_server.initialize()
        self.property_mocks["is_initialized"].return_value = True

        self.notificator_mock.return_value.shutdown.side_effect = Exception

        with self.assertRaises(Exception) as ex_cm:
            self.sim_server.shutdown()
            # should log the exception
            self.logger_mock.error.assert_called()
            self.logger_mock.exception.assert_called_with(ex_cm.exception)

        # should not be initialized
        self.property_patchers["is_initialized"].stop()
        self.assertFalse(self.sim_server.is_initialized)

        # should cancel the status update timer
        self.timer_mock.return_value.cancel_all.assert_called()

    # handle shutdown
    def test_handle_shutdown_not_initialized(self):
        self.property_mocks["is_initialized"].return_value = False
        self.simulation_lifecycle_mock.is_error_state.return_value = False

        self.simserver_mock.ServerProcessExitCodes.NO_ERROR = mock.sentinel.NO_ERROR

        return_list = []
        sim_server.simulation_server._handle_shutdown(self.sim_server,
                                                      self.event_mock.return_value,
                                                      return_list)
        self.assertEqual(return_list[-1], mock.sentinel.NO_ERROR)

    def test_handle_shutdown_not_initialized_error_state(self):
        self.property_mocks["is_initialized"].return_value = False
        self.simulation_lifecycle_mock.is_error_state.return_value = True

        self.simserver_mock.ServerProcessExitCodes.RUNNING_ERROR = mock.sentinel.RUNNING_ERROR

        return_list = []
        sim_server.simulation_server._handle_shutdown(self.sim_server,
                                                      self.event_mock.return_value,
                                                      return_list)

        self.assertEqual(return_list[-1], mock.sentinel.RUNNING_ERROR)

    def test_handle_shutdown(self):
        self.property_mocks["is_initialized"].return_value = True
        self.simulation_lifecycle_mock.is_error_state.return_value = False
        self.simserver_mock.ServerProcessExitCodes.NO_ERROR = mock.sentinel.NO_ERROR

        return_list = []
        with mock.patch.object(self.sim_server, "shutdown") as shutdown_mock:
            sim_server.simulation_server._handle_shutdown(self.sim_server,
                                                          self.event_mock.return_value,
                                                          return_list)

            self.event_mock.return_value.wait.assert_called()
            shutdown_mock.assert_called()

        self.assertEqual(return_list[-1], mock.sentinel.NO_ERROR)

    def test_handle_shutdown_error_state(self):
        self.property_mocks["is_initialized"].return_value = True
        self.simulation_lifecycle_mock.is_error_state.return_value = True
        self.simserver_mock.ServerProcessExitCodes.RUNNING_ERROR = mock.sentinel.RUNNING_ERROR

        return_list = []
        with mock.patch.object(self.sim_server, "shutdown") as shutdown_mock:
            sim_server.simulation_server._handle_shutdown(self.sim_server,
                                                          self.event_mock.return_value,
                                                          return_list)

            self.event_mock.return_value.wait.assert_called()
            shutdown_mock.assert_called()

        self.assertEqual(return_list[-1], mock.sentinel.RUNNING_ERROR)

    def test_handle_shutdown_exception(self):
        self.property_mocks["is_initialized"].return_value = True
        self.simserver_mock.ServerProcessExitCodes.SHUTDOWN_ERROR = mock.sentinel.SHUTDOWN_ERROR

        return_list = []

        with mock.patch.object(self.sim_server, "shutdown", side_effect=Exception) as shutdown_mock:
            with self.assertRaises(Exception) as ex_cm:
                sim_server.simulation_server._handle_shutdown(self.sim_server,
                                                              self.event_mock.return_value,
                                                              return_list)
                # should log the exception
                self.logger_mock.error.assert_called()
                self.logger_mock.exception.assert_called_with(ex_cm.exception)

            self.event_mock.return_value.wait.assert_called()

            shutdown_mock.assert_called()
            self.assertEqual(return_list[-1], mock.sentinel.SHUTDOWN_ERROR)

    # main
    @mock.patch(f"{base_path}.argparse.ArgumentParser")
    @mock.patch(f"{base_path}.SimulationServer")
    def test_main(self, sim_server_mock, arg_parser_mock):

        terminate_event = self.event_mock.return_value
        sim_settings = types.SimpleNamespace(sim_id="42",
                                             sim_dir="/tmp/sim_dir",
                                             exp_config="simulation_conf.json",
                                             sim_script="main_script.py",
                                             logfile="log_file.log",
                                             verbose_logs=True)

        arg_parser_mock.return_value.parse_args.return_value = sim_settings

        ret_value = sim_server.simulation_server.main()

        # must change dir to sim_dir
        self.os_mock.chdir.assert_called_with(sim_settings.sim_dir)

        # must initialize sim server
        sim_server_mock.return_value.initialize.assert_called()

        # must set up signal handling for termination
        termination_signals = [self.signal_mock.SIGINT, self.signal_mock.SIGTERM]
        for signum in termination_signals:
            self.signal_mock.signal.called_with(signum, mock.ANY)

        # must unblock SIGTERM and SIGINT
        self.signal_mock.pthread_sigmask.assert_called_with(self.signal_mock.SIG_UNBLOCK,
                                                            termination_signals)

        # must start SimServerShutdownHandler thread
        self.thread_mock.assert_any_call(target=sim_server.simulation_server._handle_shutdown,
                                         name=mock.ANY,
                                         args=(sim_server_mock.return_value,
                                               terminate_event,
                                               mock.ANY))
        self.thread_mock.return_value.start.assert_called()

        sim_server_mock.return_value.run.assert_called()

        # should signal and wait termination thread
        terminate_event.set.assert_called()
        self.thread_mock.return_value.join.assert_called()

        self.assertEqual(ret_value, self.simserver_mock.ServerProcessExitCodes.NO_ERROR.value)

    @mock.patch(f"{base_path}.argparse.ArgumentParser")
    @mock.patch(f"{base_path}.SimulationServer")
    def test_main_initialize_exception(self, sim_server_mock, arg_parser_mock):

        sim_settings = types.SimpleNamespace(sim_id="42",
                                             sim_dir="/tmp/sim_dir",
                                             exp_config="simulation_conf.json",
                                             sim_script="main_script.py",
                                             logfile="log_file.log",
                                             verbose_logs=True)

        arg_parser_mock.return_value.parse_args.return_value = sim_settings

        sim_server_mock.return_value.initialize.side_effect = Exception

        ret_value = sim_server.simulation_server.main()

        # should log the exception
        self.logger_mock.error.assert_called()
        self.logger_mock.exception.assert_called()

        # should return INITIALIZATION_ERROR
        self.assertEqual(ret_value,
                         self.simserver_mock.ServerProcessExitCodes.INITIALIZATION_ERROR.value)

    @mock.patch(f"{base_path}.argparse.ArgumentParser")
    @mock.patch(f"{base_path}.SimulationServer")
    def test_main_run_exception(self, sim_server_mock, arg_parser_mock):

        terminate_event = self.event_mock.return_value

        sim_settings = types.SimpleNamespace(sim_id="42",
                                             sim_dir="/tmp/sim_dir",
                                             exp_config="simulation_conf.json",
                                             sim_script="main_script.py",
                                             logfile="log_file.log",
                                             verbose_logs=True)

        arg_parser_mock.return_value.parse_args.return_value = sim_settings

        sim_server_mock.return_value.run.side_effect = Exception

        ret_value = sim_server.simulation_server.main()

        # should log the exception
        self.logger_mock.error.assert_called()
        self.logger_mock.exception.assert_called()

        # should signal and wait termination thread
        terminate_event.set.assert_called()
        self.thread_mock.return_value.join.assert_called()

        # should return NO_ERROR
        self.assertEqual(ret_value, self.simserver_mock.ServerProcessExitCodes.NO_ERROR.value)

    @mock.patch(f"{base_path}.argparse.ArgumentParser")
    @mock.patch(f"{base_path}.SimulationServer")
    def test_main_thread_return_value(self, sim_server_mock, arg_parser_mock):

        sim_settings = types.SimpleNamespace(sim_id="42",
                                             sim_dir="/tmp/sim_dir",
                                             exp_config="simulation_conf.json",
                                             sim_script="main_script.py",
                                             logfile="log_file.log",
                                             verbose_logs=True)

        arg_parser_mock.return_value.parse_args.return_value = sim_settings

        sim_server_mock.return_value.run.side_effect = Exception

        # set thread return value mock
        error_value = types.SimpleNamespace(value=mock.sentinel.error_value)
        self.thread_mock.return_value.join.side_effect = lambda: \
        self.thread_mock.call_args.kwargs["args"][2].append(error_value)

        ret_value = sim_server.simulation_server.main()

        self.assertEqual(ret_value, mock.sentinel.error_value)


if __name__ == '__main__':
    unittest.main()
