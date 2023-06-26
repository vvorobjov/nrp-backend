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
Unit tests for the simulation lifecycle
"""

from unittest import mock
from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle
from hbp_nrp_commons.workspace.settings import Settings
import unittest
import json

__author__ = 'NRP software team, Ugo Albanese, Georg Hinkel'


class MockLifecycle(SimulationLifecycle):

    def __init__(self, synchronization_topic="simulationLifecycle", mqtt_client_id="unittests", **kwargs):
        super().__init__(synchronization_topic, mqtt_client_id=mqtt_client_id, **kwargs)
        self.last_state_change = None
        self.last_transition = None

    def start(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "start"

    def initialize(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "initialize"

    def fail(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "fail"

    def pause(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "pause"

    def stop(self, state_change):
        self.last_state_change = state_change
        self.last_transition = "stop"

class TestLifecycle(unittest.TestCase):
    def setUp(self):
        # mqtt
        patcher_mqtt_client = mock.patch("hbp_nrp_commons.simulation_lifecycle.mqtt.Client")
        self.mqtt_client_mock = patcher_mqtt_client.start()
        self.publish_mock = self.mqtt_client_mock.return_value.publish
        self.addCleanup(patcher_mqtt_client.stop)

        # time
        patcher_time = mock.patch("hbp_nrp_commons.simulation_lifecycle.time")
        self.time_mock = patcher_time.start()
        self.addCleanup(patcher_time.stop)

    def make_transition_message(self, origin, source_state, transition, target_state):
        return json.dumps({"source_node": origin,
                           "source_state": source_state,
                           "event": transition,
                           "target_state": target_state})

    def receive_state_change(self, origin, source_state, transition, target_state):

        msg: str = self.make_transition_message(origin, source_state, transition, target_state)

        # self.__mqtt_client.message_callback_add(synchronization_topic, self.__synchronized_lifecycle_changed)
        _topic, msg_callback = self.mqtt_client_mock.return_value.message_callback_add.call_args[0]

        # __synchronized_lifecycle_changed(self, _client, _userdata, message)
        msg_callback(mock.ANY, mock.ANY, message=mock.MagicMock(payload=msg.encode()))

    def assert_publisher_called_with(self, topic, payload, retain=False):
        self.publish_mock.assert_has_calls([ mock.call( topic=topic, payload=payload, retain=retain) ])

    def test_prefixed_synchronization_topic(self):
        mqtt_topics_prefix = "prefix"
        synchronization_topic = "simulationLifecycle_topic"
        mqtt_client_id="my_id",
        lifecycle = MockLifecycle(synchronization_topic=synchronization_topic,
                                  mqtt_client_id=mqtt_client_id,
                                  mqtt_topics_prefix = "prefix")
    
        self.assertTrue(lifecycle.synchronization_topic.startswith(mqtt_topics_prefix))
        self.assertTrue(lifecycle.mqtt_client_id.startswith(mqtt_topics_prefix))


    def test_init_mqtt(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic",
                                  mqtt_client_id="my_id")

        # properly create client()
        self.mqtt_client_mock.assert_has_calls([mock.call("my_id", clean_session=True)])

        # set on_connect callback
        self.assertEqual(self.mqtt_client_mock.return_value.on_connect,
                         lifecycle._SimulationLifecycle__on_connect)

        # set on_mesage callback
        self.assertEqual(self.mqtt_client_mock.return_value.message_callback_add.call_args,
                         mock.call("simulationLifecycle_topic",
                                   lifecycle._SimulationLifecycle__synchronized_lifecycle_changed))
        # properly call connect()
        self.assertEqual(self.mqtt_client_mock.return_value.connect.call_args,
                         mock.call(host=Settings.DEFAULT_MQTT_BROKER_HOST,
                                   port=Settings.DEFAULT_MQTT_BROKER_PORT))
        # call loop_start()
        self.assertTrue(self.mqtt_client_mock.return_value.loop_start.called)

    def test_created_simulation_must_be_initialized(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic")

        self.assertRaises(ValueError, lifecycle.accept_command, "started")
        self.assertRaises(ValueError, lifecycle.accept_command, "paused")

        self.assertIsNone(lifecycle.last_state_change)
        lifecycle.accept_command("initialized")
        self.assertEqual("initialize", lifecycle.last_transition)
        self.assertEqual("created", lifecycle.last_state_change.transition.source)
        self.assertEqual("paused", lifecycle.last_state_change.transition.dest)
        self.assertEqual("initialized", lifecycle.last_state_change.event.name)
        self.assertEqual("paused", lifecycle.state)

    def test_accept_command_fail(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic")

        trigger_callbacks = {"started": mock.MagicMock()}
        trigger_callbacks["started"].trigger.side_effect = Exception

        with mock.patch.dict(lifecycle._SimulationLifecycle__machine.events, trigger_callbacks):
            # call stop() on failing accept_command
            with mock.patch.object(lifecycle, "stop") as stop_mock:
                self.assertRaises(Exception, lifecycle.accept_command, "started")
                self.assertTrue(stop_mock.called)
                # shutdown lifecycle
                self.assert_shutdown(lifecycle)

    def test_lifecycle_normal_workflow(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic")

        # Start by initializing a simulation
        lifecycle.accept_command("initialized")
        self.assertEqual("paused", lifecycle.state)
        self.assertEqual("initialize", lifecycle.last_transition)
        self.assertEqual(1, self.publish_mock.call_count)
        # Then, we start the simulation
        lifecycle.accept_command("started")
        self.assertEqual("started", lifecycle.state)
        self.assertEqual("start", lifecycle.last_transition)
        self.assertEqual(2, self.publish_mock.call_count)
        # Pause the simulation
        lifecycle.accept_command("paused")
        self.assertEqual("paused", lifecycle.state)
        self.assertEqual("pause", lifecycle.last_transition)
        self.assertEqual(3, self.publish_mock.call_count)
        # Resume it
        lifecycle.accept_command("started")
        self.assertEqual("started", lifecycle.state)
        self.assertEqual("start", lifecycle.last_transition)
        self.assertEqual(4, self.publish_mock.call_count)
        # Finally, we are done
        lifecycle.accept_command("stopped")
        self.assertEqual("stopped", lifecycle.state)
        self.assertEqual("stop", lifecycle.last_transition)
        self.assertEqual(5, self.publish_mock.call_count)
        # shutdown lifecycle
        self.assert_shutdown(lifecycle)

    def test_lifecycle_normal_workflow_synchronized(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic", mqtt_client_id="unittests")
        
        other_lifecycle_id = "backend"

        # Start by initializing a simulation
        self.receive_state_change(origin=other_lifecycle_id, source_state="created", transition="initialized", target_state="paused")
        self.assertEqual("paused", lifecycle.state)
        self.assertEqual("initialize", lifecycle.last_transition)
        self.assertEqual(0, self.publish_mock.call_count) # do not propagate received transitions

        # Then, we start the simulation
        self.receive_state_change(other_lifecycle_id, "paused", "started", "started")
        self.assertEqual("started", lifecycle.state)
        self.assertEqual("start", lifecycle.last_transition)
        self.assertEqual(0, self.publish_mock.call_count)
        # Pause the simulation
        self.receive_state_change(other_lifecycle_id, "started", "paused", "paused")
        self.assertEqual("paused", lifecycle.state)
        self.assertEqual("pause", lifecycle.last_transition)
        self.assertEqual(0, self.publish_mock.call_count)
        # Resume it
        self.receive_state_change(other_lifecycle_id, "paused", "started", "started")
        self.assertEqual("started", lifecycle.state)
        self.assertEqual("start", lifecycle.last_transition)
        self.assertEqual(0, self.publish_mock.call_count)
        # Finally, we are done
        self.receive_state_change(other_lifecycle_id, "started", "stopped", "stopped")
        self.assertEqual("stopped", lifecycle.state)
        self.assertEqual("stop", lifecycle.last_transition)
        self.assertEqual(0, self.publish_mock.call_count)
        # shutdown lifecycle
        self.assert_shutdown(lifecycle)

    def test_lifecycle_error_during_initialize(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic",
                                  mqtt_client_id="backend",
                                  clear_synchronization_topic=True)
        
        with mock.patch.object(lifecycle, "initialize", side_effect=Exception):
                self.assertRaises(Exception, lifecycle.accept_command, "initialized")
        
        self.assertEqual("failed", lifecycle.state)
        # We need to tell others that the simulation crashed
        msg = self.make_transition_message(lifecycle.mqtt_client_id, "created", "failed", "failed")
        self.assert_publisher_called_with(lifecycle.synchronization_topic, msg, retain=True)
        # clear_synchronization_topic on shutdown
        self.assert_publisher_called_with(lifecycle.synchronization_topic, "", retain=True)

    def test_lifecycle_error_synchronizing_initialization(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic",
                                  mqtt_client_id="unittests")

        with mock.patch.object(lifecycle, "initialize", side_effect=Exception):
            self.receive_state_change("backend", "created", "initialized", "paused")

        self.assertEqual("failed", lifecycle.state)
        msg = self.make_transition_message(lifecycle.mqtt_client_id, "paused", "failed", "failed")
        self.assert_publisher_called_with(lifecycle.synchronization_topic, msg)

    def test_lifecycle_error_in_simulation_server_while_running(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic",
                                  mqtt_client_id="unittests")

        # Again, we initialize the simulation
        lifecycle.accept_command("initialized")
        self.assertEqual("initialize", lifecycle.last_transition)
        self.assertEqual(1, self.publish_mock.call_count)
        # We start it
        lifecycle.accept_command("started")
        self.assertEqual("start", lifecycle.last_transition)
        self.assertEqual(2, self.publish_mock.call_count)
        # From the simulation server, we get feedback that the simulation has failed
        self.receive_state_change("simulation", "started", "failed", "failed")
        self.assertEqual("fail", lifecycle.last_transition)
        self.assertEqual(2, self.publish_mock.call_count)
        # We still know that an error happened
        self.assertEqual("failed", lifecycle.state)

    def test_lifecycle_error_while_running(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic",
                                  mqtt_client_id="backend",
                                  clear_synchronization_topic=True)

        # Start by initializing a simulation
        lifecycle.accept_command("initialized")
        self.assertEqual("paused", lifecycle.state)
        self.assertEqual("initialize", lifecycle.last_transition)
        self.assertEqual(1, self.publish_mock.call_count)
        # Then, we start the simulation
        lifecycle.accept_command("started")
        self.assertEqual("started", lifecycle.state)
        self.assertEqual("start", lifecycle.last_transition)
        self.assertEqual(2, self.publish_mock.call_count)
        # From the simulation server, we get feedback that the simulation has failed

        with mock.patch.object(lifecycle, "fail", wraps=lifecycle.fail) as fail_mock:
            self.receive_state_change("sim_server", "started", "failed", "failed")
            self.assertEqual("fail", lifecycle.last_transition)
            self.assertTrue(fail_mock.called)
            self.assert_shutdown(lifecycle)
            # clear_synchronization_topic on shutdown
            self.assert_publisher_called_with(lifecycle.synchronization_topic, "", retain=True)

    def test_propagated_destinations(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic",
                                  mqtt_client_id="unittests",
                                  propagated_destinations=["paused"])
            
        # Start by initializing a simulation
        lifecycle.accept_command("initialized")
        self.assertEqual("paused", lifecycle.state)
        self.assertEqual("initialize", lifecycle.last_transition)
        self.assertEqual(1, self.publish_mock.call_count) # 2?
        pub_call_count_after_one_transition = self.publish_mock.call_count
        # paused should be propagated
        self.assertEqual(1, self.publish_mock.call_count)
        msg = self.make_transition_message(lifecycle.mqtt_client_id, SimulationLifecycle.INITIAL_STATE, "initialized", "paused")
        self.assert_publisher_called_with(lifecycle.synchronization_topic, msg, retain=True) # retain since source is an INITIAL_STATE

        # Then, we start the simulation
        lifecycle.accept_command("started")
        self.assertEqual("started", lifecycle.state)
        self.assertEqual("start", lifecycle.last_transition)
        # started should NOT be propagated
        self.assertEqual(pub_call_count_after_one_transition, self.publish_mock.call_count)

        # Then, we stop the simulation
        lifecycle.accept_command("stopped")
        self.assertEqual("stopped", lifecycle.state)
        self.assertEqual("stop", lifecycle.last_transition)
        # stopped should NOT be propagated
        self.assertEqual(pub_call_count_after_one_transition, self.publish_mock.call_count)

    def test_shutdown(self):
        lifecycle = MockLifecycle(synchronization_topic="simulationLifecycle_topic",
                                  mqtt_client_id="unittests",
                                  clear_synchronization_topic=True)
        lifecycle.shutdown(None)
        self.assert_shutdown(lifecycle, clear_synchronization_topic=True)

    def assert_shutdown(self, lifecycle, clear_synchronization_topic=False):
        mqtt_client = self.mqtt_client_mock.return_value

        if clear_synchronization_topic:
            self.assert_publisher_called_with(lifecycle.synchronization_topic,
                                            payload="",
                                            retain=lifecycle.clear_synchronization_topic)

        mqtt_client.unsubscribe.called_with(lifecycle.synchronization_topic)
        self.assertTrue(mqtt_client.loop_stop.called)
        self.assertTrue(mqtt_client.disconnect.called)

    def test_invalid_lifecycle(self):
        invalid = SimulationLifecycle('foo')
        self.assertRaises(Exception, invalid.accept_command, 'bar')
        self.assertRaises(Exception, invalid.initialize, 'bar')
        self.assertRaises(Exception, invalid.start, 'bar')
        self.assertRaises(Exception, invalid.pause, 'bar')
        self.assertRaises(Exception, invalid.stop, 'bar')
        self.assertRaises(Exception, invalid.fail, 'bar')

    def test_connect_mqtt(self):
        clear_topic = True
        topic="simulationLifecycle_topic"
        
        _lifecycle = MockLifecycle(synchronization_topic=topic,
                            mqtt_client_id="unittests",
                            clear_synchronization_topic=clear_topic)

        mqtt_client=self.mqtt_client_mock.return_value
        mqtt_client.on_connect(mqtt_client, {}, mock.ANY, mock.ANY)
        self.assert_publisher_called_with(topic=topic, payload="", retain=clear_topic)
        self.assertTrue(mqtt_client.subscribe.called)

if __name__ == '__main__':
    unittest.main()
