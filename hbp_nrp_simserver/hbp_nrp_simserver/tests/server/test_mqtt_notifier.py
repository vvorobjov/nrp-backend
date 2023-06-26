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
MQTTNotifier unit test
"""
import json
import unittest
from unittest import mock

from hbp_nrp_simserver.server.mqtt_notifier import MQTTNotifier



class TestMQTTNotifier(unittest.TestCase):

    def setUp(self):
        # mqtt
        patcher_mqtt_client = mock.patch('hbp_nrp_simserver.server.mqtt_notifier.mqtt.Client')
        self.mqtt_client_class_mock = patcher_mqtt_client.start()
        self.mqtt_client_mock = self.mqtt_client_class_mock.return_value
        self.mqtt_client_publish_mock = self.mqtt_client_mock.publish
        self.addCleanup(patcher_mqtt_client.stop)

        # patcher_settings = mock.patch('hbp_nrp_simserver.server.mqtt_notifier.Settings')
        # self.patcher_settings_class_mock = patcher_settings.start()

        DEFAULT_MQTT_BROKER_HOST ="home"
        DEFAULT_MQTT_BROKER_PORT = 42

        new_defaults = (DEFAULT_MQTT_BROKER_HOST, DEFAULT_MQTT_BROKER_PORT, "","mqtt_notifier")

        # self.addCleanup(patcher_settings.stop)

        self.sim_id = 0
        with mock.patch.object(MQTTNotifier.__init__, '__defaults__', new_defaults):
            self.__mqtt_notifier: MQTTNotifier = MQTTNotifier(sim_id=self.sim_id)

    def test_mqtt_node_init(self):
        self.mqtt_client_class_mock.assert_called_with(MQTTNotifier.DEFAULT_MQTT_CLIENT_ID,
                                                       clean_session=True)
        
        self.mqtt_client_mock.connect.assert_called_with(host="home",
                                                         port=42)
        self.mqtt_client_mock.loop_start.assert_called()

    def test_init_topics_prefix(self):
        prefix = "a_prefix"
        mqtt_notifier = MQTTNotifier(sim_id=self.sim_id, topics_prefix=prefix)

        for attribute in ["status_topic", "status_topic", "mqtt_client_id"]:
            self.assertTrue(getattr(mqtt_notifier, attribute).startswith(prefix))

        # empty prefix
        prefix = ""
        mqtt_notifier = MQTTNotifier(sim_id=self.sim_id, topics_prefix=prefix)

        for attribute in ["status_topic", "status_topic", "mqtt_client_id"]:
            self.assertFalse(getattr(mqtt_notifier, attribute).startswith("/"))


    def test_shutdown(self):
        self.__mqtt_notifier.shutdown()
        self.mqtt_client_mock.loop_stop.assert_called()
        self.mqtt_client_mock.disconnect.assert_called()
        # no publishing after shutdown
        self.assertFalse(self.mqtt_client_publish_mock.called)

    def test_publish(self):
        self.__mqtt_notifier.publish_status('foo')
        self.mqtt_client_publish_mock.assert_called_once_with(self.__mqtt_notifier.status_topic,
                                                              'foo')

        self.mqtt_client_publish_mock.reset_mock()
        self.__mqtt_notifier.publish_error('bar')
        self.mqtt_client_mock.publish.assert_called_once_with(self.__mqtt_notifier.error_topic,
                                                              'bar')
    
    def test_task(self):
        self.__mqtt_notifier.start_task('task', 'subtask', 1, False)
        self.assertEqual(self.mqtt_client_publish_mock.call_count, 1)
        self.__mqtt_notifier.update_task('new_subtask', True, False)
        self.assertEqual(self.mqtt_client_publish_mock.call_count, 2)
        self.__mqtt_notifier.finish_task()
        self.assertEqual(self.mqtt_client_publish_mock.call_count, 3)

    def test_start_task(self):
        task_name = 'test_name'
        subtask_name = 'test_subtaskname'
        number_of_subtasks = 1
        block_ui = False
        self.__mqtt_notifier.start_task(task_name, subtask_name, number_of_subtasks, block_ui)
        self.assertEqual(1, self.mqtt_client_publish_mock.call_count)
        message = {'progress': {'task': task_name,
                                'subtask': subtask_name,
                                'number_of_subtasks': number_of_subtasks,
                                'subtask_index': 0,
                                'block_ui': block_ui}}
        self.mqtt_client_publish_mock.assert_called_with(self.__mqtt_notifier.status_topic,
                                                         json.dumps(message))

        with mock.patch.object(self.__mqtt_notifier, 'finish_task') as mock_finish:
            self.__mqtt_notifier.start_task(task_name, subtask_name, number_of_subtasks,
                                               block_ui)
            mock_finish.assert_called_once()

    def test_task_notifier(self):
        with mock.patch.object(self.__mqtt_notifier, 'start_task') as mock_start, \
                mock.patch.object(self.__mqtt_notifier, 'finish_task') as mock_finish:
            with self.__mqtt_notifier.task_notifier('foo', 'bar'):
                mock_start.assert_called_once_with('foo', 'bar', number_of_subtasks=0,
                                                   block_ui=True)

            mock_finish.assert_called_once()


if __name__ == "__main__":
    unittest.main()
