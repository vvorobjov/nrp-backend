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
This module implements a MQTT Notifier interface for status/error messages.
"""

import contextlib
import json
import logging
from typing import Optional

import paho.mqtt.client as mqtt

from . import TOPIC_STATUS, TOPIC_ERROR

logger = logging.getLogger(__name__)

DEFAULT_MQTT_CLIENT_ID = "mqtt_notifier"
DEFAULT_MQTT_HOST = "localhost"
DEFAULT_MQTT_PORT = 1883


class MQTTNotifier:
    """
    This class encapsulates publishing of state/errors/task status to the frontend/clients.
    """
    def __init__(self,
                 sim_id: int,
                 broker_hostname: str = DEFAULT_MQTT_HOST, broker_port: int = DEFAULT_MQTT_PORT,
                 client_id: str = DEFAULT_MQTT_CLIENT_ID):

        self.sim_id = sim_id
        self.mqtt_broker_hostname = broker_hostname
        self.mqtt_broker_port = broker_port
        self.mqtt_client_id = client_id

        self.status_topic = TOPIC_STATUS(self.sim_id)
        self.error_topic = TOPIC_ERROR(self.sim_id)

        # task specific bookkeeping
        self.__current_task: Optional[str] = None
        self.__current_subtask_count = 0
        self.__current_subtask_index = 0

        # NOTE MQTTv5 reqires clean_start=True parameter to connect
        # instead of clean_session=True here
        self.__mqtt_client: Optional[mqtt.Client] = mqtt.Client(self.mqtt_client_id,
                                                                clean_session=True)

        self.__mqtt_client.on_connect = self.__on_connect
        self.__mqtt_client.connect(host=self.mqtt_broker_hostname, port=self.mqtt_broker_port)
        self.__mqtt_client.loop_start()  # start message processing thread

        logger.info("MQTT notifier initialized. Simulation ID: '%s'", self.sim_id)

    def __on_connect(self, _client, _userdata, _flags, _rc):
        logger.debug("Connected to MQTT broker at %s:%d with 'id' %s. Simulation ID: '%s'",
                     self.mqtt_broker_hostname, self.mqtt_broker_port, self.mqtt_client_id, self.sim_id)

    def shutdown(self):
        """
        Shutdown all publishers, notification will no longer function after called.
        """
        logger.info('Shutting down MQTT notifier')
        self.__mqtt_client.loop_stop()
        self.__mqtt_client.disconnect()
        self.__mqtt_client = None

    def publish_status(self, msg):
        """
        Publishes a state message

        :param msg: A string of formatted JSON to publish.
        """
        if self.__mqtt_client is None:
            logger.error('Attempting to publish state after shutdown!')
            return

        self.__mqtt_client.publish(self.status_topic,
                                   msg)

    def publish_error(self, error_msg):
        """
        Publishes an error message

        :param error_msg: A string of formatted JSON to publish.
        """
        if self.__mqtt_client is None:
            logger.error('Attempting to publish error after shutdown!')
            return
        

        logger.debug("Publishing an Error: '%s'", error_msg)

        self.__mqtt_client.publish(self.error_topic,
                                   error_msg)

    # TASK NOTIFIER
    def start_task(self, task_name, subtask_name, number_of_subtasks, block_ui=False):
        """
        Sends a status notification that a task starts on the MQTT status topic.
        This method will save the task name and the task size in class members so that
        it could be reused in subsequent call to the update_task method.

        :param: task_name: Title of the task (example: initializing experiment).
        :param: subtask_name: Title of the first subtask. Could be empty
                (example: 'loading...').
        :param: number_of_subtasks: Number of expected subsequent calls to
                update_current_task(_, True, _).
        :param: block_ui: Indicate that the client should block any user interaction.
        """
        if self.__current_task is not None:
            logger.warning(
                "Previous task was not closed properly, closing it now.")
            self.finish_task()

        self.__current_task = task_name
        self.__current_subtask_count = number_of_subtasks

        message = {'progress': {'task': task_name,
                                'subtask': subtask_name,
                                'number_of_subtasks': number_of_subtasks,
                                'subtask_index': self.__current_subtask_index,
                                'block_ui': block_ui}}
        self.publish_status(json.dumps(message))

    def update_task(self, new_subtask_name, update_progress, block_ui=False):
        """
        Sends a status notification that the current task is updated with a new subtask.

        :param: subtask_name: Title of the first subtask. Could be empty
                (example: 'Loading Foo...').
        :param: update_progress: Boolean indicating if the index of the current subtask
                should be updated (usually yes).
        :param: block_ui: Indicate that the client should block any user interaction.
        """
        if self.__current_task is None:
            logger.warning("Can't update a non existing task.")
            return
        if update_progress:
            self.__current_subtask_index += 1
        message = {'progress': {'task': self.__current_task,
                                'subtask': new_subtask_name,
                                'number_of_subtasks': self.__current_subtask_count,
                                'subtask_index': self.__current_subtask_index,
                                'block_ui': block_ui}}
        self.publish_status(json.dumps(message))

    def finish_task(self):
        """
        Sends a status notification that the current task is finished.
        """
        if self.__current_task is None:
            logger.warning("Can't finish a non existing task.")
            return

        message = {'progress': {'task': self.__current_task,
                                'done': True}}
        self.publish_status(json.dumps(message))

        self.__current_subtask_count = 0
        self.__current_subtask_index = 0
        self.__current_task = None

    @contextlib.contextmanager
    def task_notifier(self, task_name, subtask_name=None):
        """
        Task notifier context manager

        :param task_name:
        :param subtask_name:
        """

        self.start_task(task_name, subtask_name if subtask_name else "", number_of_subtasks=0, block_ui=True)
        try:
            yield
        finally:
            self.finish_task()
