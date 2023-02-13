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
SimulationServerLifecycle unit test
"""

import unittest
from unittest import mock
from unittest.mock import patch, MagicMock

from hbp_nrp_simserver.server import TOPIC_LIFECYCLE

from hbp_nrp_simserver.server.simulation_server_lifecycle import SimulationServerLifecycle



class TestSimulationServerLifecycle(unittest.TestCase):

    base_path = "hbp_nrp_simserver.server.simulation_server_lifecycle"

    def setUp(self):

        # Patch hbp_nrp_commons.simulation_lifecycle deps
        # mqtt 
        patcher_mqtt_client = patch("hbp_nrp_commons.simulation_lifecycle.mqtt.Client")
        self.mqtt_client_mock = patcher_mqtt_client.start()
        self.publish_mock = self.mqtt_client_mock.return_value.publish
        self.addCleanup(patcher_mqtt_client.stop)

        # time
        patcher_time = patch("hbp_nrp_commons.simulation_lifecycle.time")
        self.time_mock = patcher_time.start()
        self.addCleanup(patcher_time.stop)

        # Patch simulation_server_lifecycle
        # threading.Event
        patcher_threading_event = patch(f"{self.base_path}.threading.Event")
        self.threading_event_mock = patcher_threading_event.start()
        self.addCleanup(patcher_threading_event.stop)

        self.sim_server_mock = MagicMock(simulation_id=42)
        self.ssl = SimulationServerLifecycle(self.sim_server_mock)

    def test_init_invalid_args(self):
        # sim_server is None
        with self.assertRaises(ValueError):
            SimulationServerLifecycle(sim_server=None)

        # sim_server.nrp_script_runner is None
        with self.assertRaises(ValueError):
            SimulationServerLifecycle(MagicMock(nrp_script_runner=None))

    def test_init(self):
        self.assertIn(self.ssl.synchronization_topic, TOPIC_LIFECYCLE(self.sim_server_mock.simulation_id))
        self.assertEqual(self.ssl.mqtt_client_id, self.ssl.DEFAULT_MQTT_CLIENT_ID)
        self.assertEqual(self.ssl.propagated_destinations, SimulationServerLifecycle.propagated_destinations)

    def test_start(self):
        self.ssl.start(mock.sentinel.event)

        self.sim_server_mock.nrp_script_runner.start.assert_called_with(completed_callback=self.ssl.completed)

    def test_start_exception(self):

        self.sim_server_mock.nrp_script_runner.start.side_effect = Exception

        except_hook = MagicMock()

        ssl = SimulationServerLifecycle(self.sim_server_mock, except_hook)

        with self.assertRaises(Exception) as cm:
            ssl.start(mock.sentinel.event)
            except_hook.assert_called_with(cm.exception)

    def test_stop(self):
        self.ssl.stop(mock.sentinel.event)

        self.sim_server_mock.nrp_script_runner.stop.assert_called()

    def test_stop_exception(self):
        self.sim_server_mock.nrp_script_runner.stop.side_effect = Exception
        except_hook = MagicMock()

        ssl = SimulationServerLifecycle(self.sim_server_mock, except_hook)

        with self.assertRaises(Exception) as cm:
            ssl.stop(mock.sentinel.event)
            except_hook.assert_called_with(cm.exception)

    def test_pause(self):
        self.ssl.pause(mock.sentinel.event)

        self.sim_server_mock.nrp_script_runner.pause.assert_called()

    def test_pause_exception(self):
        self.sim_server_mock.nrp_script_runner.pause.side_effect = Exception
        except_hook = MagicMock()

        ssl = SimulationServerLifecycle(self.sim_server_mock, except_hook)

        with self.assertRaises(Exception) as cm:
            ssl.pause(mock.sentinel.event)
            except_hook.assert_called_with(cm.exception)

    def test_fail(self):
        with patch.object(self.ssl, "stop") as stop_mock:
            some_event = mock.sentinel.event
            self.ssl.fail(some_event)
            stop_mock.assert_called_with(some_event)
            self.sim_server_mock.publish_state_update.assert_called()

    def test_fail_exception(self):
        with patch.object(self.ssl, "stop", side_effect=Exception):

            with self.assertRaises(Exception):
                self.ssl.fail(mock.sentinel.event)
                self.sim_server_mock.publish_state_update.assert_called()

    def test_initialize(self):
        self.sim_server_mock.nrp_script_runner.is_initialized = False

        with patch.object(self.ssl, "_clear_synchronization_topic") as cst_mock:
            self.ssl.initialize(mock.sentinel.event)
            self.sim_server_mock.nrp_script_runner.initialize.assert_called()
            cst_mock.assert_called()

    def test_initialize_exception(self):
        self.sim_server_mock.nrp_script_runner.is_initialized = False
        self.sim_server_mock.nrp_script_runner.initialize.side_effect = Exception

        with patch.object(self.ssl, "_clear_synchronization_topic") as cst_mock:
            with self.assertRaises(Exception) as cm:
                self.ssl.initialize(mock.sentinel.event)
                cst_mock.assert_called()

    def test_already_initialized(self):
        self.sim_server_mock.nrp_script_runner.is_initialized = True

        with patch.object(self.ssl, "_clear_synchronization_topic") as cst_mock:
            self.ssl.initialize(mock.sentinel.event)
            self.sim_server_mock.nrp_script_runner.initialize.assert_not_called()
            cst_mock.assert_not_called()

    def test_shutdown(self):

        ssl = SimulationServerLifecycle(self.sim_server_mock)

        with patch(f"{self.base_path}.super") as super_mock:
            ssl.shutdown(mock.sentinel.event)

            # call shutdown
            self.sim_server_mock.nrp_script_runner.shutdown.assert_called()
            # done_event.set()
            self.threading_event_mock.return_value.set.assert_called()
            # call super().shutdown
            super_mock.return_value.shutdown.assert_called_with(mock.sentinel.event)



if __name__ == '__main__':
    unittest.main()
