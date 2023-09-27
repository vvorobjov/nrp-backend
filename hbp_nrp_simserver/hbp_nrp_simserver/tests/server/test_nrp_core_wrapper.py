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
NrpCoreWrapper unit test
"""

import unittest
from unittest import mock

import hbp_nrp_simserver.server as sim_server
import time
from hbp_nrp_commons.tests.utilities_test import mock_properties
from hbp_nrp_simserver.server.nrp_core_wrapper import NrpCoreWrapper, NRPStopExecution, \
    NRPSimulationTimeout


class TestNrpCoreWrapper(unittest.TestCase):
    base_path = "hbp_nrp_simserver.server.nrp_core_wrapper"

    def setUp(self):
        # exp_conf_utils
        patcher_exp_conf_utils = mock.patch(f"{self.base_path}.exp_conf_utils")
        self.exp_conf_utils = patcher_exp_conf_utils.start()
        self.exp_conf_utils.engine_index.return_value = 3
        self.addCleanup(patcher_exp_conf_utils.stop)

        # now_ns
        self.patcher_now_ns = mock.patch(f"{self.base_path}.now_ns", wraps=time.time_ns)
        self.now_ns_mock = self.patcher_now_ns.start()
        self.addCleanup(self.patcher_now_ns.stop)

        # Settings
        settings_patcher = mock.patch(f'{self.base_path}.Settings')
        self.settings_mock = settings_patcher.start()
        self.settings_mock.is_mqtt_broker_default = False
        self.settings_mock.mqtt_broker_host = "localhost_mock"
        self.settings_mock.mqtt_broker_port = "4242"
        self.settings_mock.mqtt_topics_prefix = ""
        self.addCleanup(settings_patcher.stop)

        # logger
        patcher_logger = mock.patch(f"{self.base_path}.logger")
        self.logger_mock = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)

        self.sim_settings = sim_server.SimulationSettings(sim_id="42",
                                                          sim_dir="/tmp/sim_dir",
                                                          exp_config_file="simulation_conf.json",
                                                          main_script_file="main_script.py")

        self.paused_event_mock = mock.MagicMock()
        self.stopped_event_mock = mock.MagicMock()
        self.nrp_core_class_mock = mock.MagicMock(__name__="NrpCoreMock")
        self.exp_config_file = "simulation_conf.json"

        self.exp_config_mock = mock.MagicMock(SimulationTimeout=1., SimulationTimestep=0.01)

        self.nrp_core_wrapper = NrpCoreWrapper(self.nrp_core_class_mock,
                                               sim_id="42",
                                               exp_config_file=self.exp_config_file,
                                               exp_config=self.exp_config_mock,
                                               paused_event=self.paused_event_mock,
                                               stopped_event=self.stopped_event_mock)

        # mock NrpCoreWrapper properties
        self.property_patchers, self.property_mocks = mock_properties(NrpCoreWrapper,
                                                                      addCleanup=self.addCleanup)

    # __init__
    def test_init(self):
        engine_param_override_arg = "-o"
        engine_configs_arg = "EngineConfigs"
        sim_id = "3"
        field_sep = "."
        args_to_override_dict = {"simulationID": '"42"',
                                 "MQTTBroker": f'"{self.settings_mock.mqtt_broker_host}:{self.settings_mock.mqtt_broker_port}"',
                                 "MQTTPrefix": f'"{self.settings_mock.mqtt_topics_prefix}"'}
        
        args_to_override_mappings = [f"{k}={v}" for k, v in args_to_override_dict.items()]

        #e.g. -o EngineConfigs.3.simulationID=42 -o EngineConfigs.3.MQTTBroker=localhost_mock:4242 -o EngineConfigs.3.MQTTPrefix='
        args_to_override_str = " ".join([f"{engine_param_override_arg} {field_sep.join([engine_configs_arg, sim_id, args_to_override_mapping])}" 
                                         for args_to_override_mapping in args_to_override_mappings])

        self.nrp_core_class_mock.assert_called_with(NrpCoreWrapper.NRP_CORE_DEFAULT_ADDRESS_PORT,
                                                    config_file=self.exp_config_file,
                                                    args=args_to_override_str)

    def test_init_topics_prefix(self):

        self.settings_mock.mqtt_topics_prefix = "mqtt_prefix"

        self.nrp_core_wrapper = NrpCoreWrapper(self.nrp_core_class_mock,
                                               sim_id="42",
                                               exp_config_file=self.exp_config_file,
                                               exp_config=self.exp_config_mock,
                                               paused_event=self.paused_event_mock,
                                               stopped_event=self.stopped_event_mock)

        mqtt_prefix_arg = '-o EngineConfigs.3.MQTTPrefix="mqtt_prefix"'
        self.assertIn(mqtt_prefix_arg, self.nrp_core_class_mock.call_args.kwargs["args"])

    def test_init_topics_empty_prefix(self):

        self.settings_mock.mqtt_topics_prefix = ""

        self.nrp_core_wrapper = NrpCoreWrapper(self.nrp_core_class_mock,
                                               sim_id="42",
                                               exp_config_file=self.exp_config_file,
                                               exp_config=self.exp_config_mock,
                                               paused_event=self.paused_event_mock,
                                               stopped_event=self.stopped_event_mock)

        mqtt_prefix_arg = '-o EngineConfigs.3.MQTTPrefix='
        self.assertIn(mqtt_prefix_arg, self.nrp_core_class_mock.call_args.kwargs["args"])

    # stop, reset, shutdown, initialize
    def test_not_implemented(self):
        for method_tested in ["stop", "reset", "shutdown", "initialize"]:
            with self.subTest(method=method_tested):
                with self.assertRaises(NotImplementedError) as ex_cm:
                    getattr(self.nrp_core_wrapper, method_tested)()

                self.assertEqual(ex_cm.exception.args[0], f"{method_tested}() is not available")

    def test_delegate_methods(self):
        for method_tested, target_command in zip(["_initialize", "_shutdown"],
                                                 ["initialize", "shutdown"]):
            with self.subTest(method=method_tested):
                getattr(self.nrp_core_wrapper, method_tested)()
                getattr(self.nrp_core_class_mock.return_value, target_command).assert_called()

    # run_loop
    def test_run_loop_stop(self):
        self.stopped_event_mock.is_set.return_value = True

        with self.assertRaises(NRPStopExecution):
            self.nrp_core_wrapper.run_loop()

        self.paused_event_mock.wait.assert_called()

    def test_run_loop_timeout(self):
        self.property_patchers["max_timesteps"].stop()

        self.stopped_event_mock.is_set.return_value = False

        # request more timesteps than are left
        too_many_steps = self.nrp_core_wrapper.max_timesteps + 1

        with self.assertRaises(NRPSimulationTimeout):
            self.nrp_core_wrapper.run_loop(num_iterations=too_many_steps)

        self.paused_event_mock.wait.assert_called()

    def test_run_loop_exception(self):
        for p in ["real_time"]:
            self.property_patchers[p].stop()

        self.stopped_event_mock.is_set.return_value = False

        self.nrp_core_class_mock.return_value.run_loop.side_effect = Exception

        with self.assertRaises(Exception):
            self.nrp_core_wrapper.run_loop()

        # should not be running
        self.assertFalse(self.nrp_core_wrapper.is_running)
        self.assertGreater(self.nrp_core_wrapper.real_time, 0.)

    def test_run_loop(self):
        for p in ["simulation_time", "simulation_time_remaining", "real_time"]:
            self.property_patchers[p].stop()

        self.stopped_event_mock.is_set.return_value = False
        sim_time_remaining_before = self.nrp_core_wrapper.simulation_time_remaining

        self.nrp_core_class_mock.return_value.run_loop.return_value = mock.sentinel.loop_result

        # test subject
        loop_result = self.nrp_core_wrapper.run_loop()

        sim_time_remaining_after = self.nrp_core_wrapper.simulation_time_remaining

        # should delegate to NrpCore
        self.nrp_core_class_mock.return_value.run_loop.assert_called()

        # should handle paused and stopped events
        self.paused_event_mock.wait.assert_called()
        self.stopped_event_mock.is_set.assert_called()

        # should not be running
        self.assertFalse(self.nrp_core_wrapper.is_running)

        # should take care of sim timekeeping
        timeout = self.exp_config_mock.SimulationTimeout
        timestep = self.exp_config_mock.SimulationTimestep

        self.assertAlmostEquals(self.nrp_core_wrapper.simulation_time,
                                timeout * timestep)
        self.assertGreater(self.nrp_core_wrapper.real_time, 0.)

        self.assertAlmostEquals(sim_time_remaining_before - sim_time_remaining_after, timestep)

        # should return what delegate has returned
        self.assertEqual(mock.sentinel.loop_result, loop_result)


if __name__ == '__main__':
    unittest.main()
