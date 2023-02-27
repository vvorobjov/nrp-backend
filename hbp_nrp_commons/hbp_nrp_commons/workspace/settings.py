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
This module represents the configuration of a running simulation
"""
import logging
import os

__author__ = 'NRP software team, Hossain Mahmud'

logger = logging.getLogger(__name__)


class _Settings:
    """
    Settings that are common on the backend process or machine
    This class is a Singleton (per process)
    """

    __instance = None

    DEFAULT_MQTT_BROKER_HOST = "localhost"
    DEFAULT_MQTT_BROKER_PORT = 1883

    DEFAULT_STORAGE_HOST = "localhost"
    DEFAULT_STORAGE_PORT = 9000

    env_vars_name = {'ROOT_DIR': 'HBP',  # NRP home directory
                     'SIMULATION_DIR': 'NRP_SIMULATION_DIR',  # NRP simulation directory (in /tmp)
                     'MQTT_BROKER': "NRP_MQTT_BROKER_ADDRESS",
                     'STORAGE_ADDRESS': 'STORAGE_ADDRESS',
                     'STORAGE_PORT': 'STORAGE_PORT'}

    def __new__(cls):
        """
        Overridden new for the singleton implementation

        :return: Singleton instance
        """

        if _Settings.__instance is None:
            _Settings.__instance = object.__new__(cls)
        return _Settings.__instance

    def __init__(self):
        """
        Declare all the config and system variables
        """

        try:
            self.nrp_home = os.environ[self.env_vars_name['ROOT_DIR']]
        except KeyError:
            raise Exception(
                f"Please export NRP home directory as '{self.env_vars_name['ROOT_DIR']}' environment variable")

        try:
            self.sim_dir_symlink = os.environ[self.env_vars_name['SIMULATION_DIR']]
        except KeyError:
            raise Exception(
                "Simulation directory symlink location is not specified in NRP_SIMULATION_DIR")

        # The address of the MQTT broker, defaults to localhost:1883
        try:
            host, port = os.environ.get(self.env_vars_name['MQTT_BROKER']).split(":")
            self.mqtt_broker_host = host
            self.mqtt_broker_port = int(port)
            # user has specified a valid address
            self.is_mqtt_broker_default: bool = False
        except (ValueError, AttributeError):
            # user has specified an invalid address, use default
            self.mqtt_broker_host: str = _Settings.DEFAULT_MQTT_BROKER_HOST
            self.mqtt_broker_port: int = _Settings.DEFAULT_MQTT_BROKER_PORT
            self.is_mqtt_broker_default: bool = True

        # TODO do as for MQTT (i.e. address = host:port), rename to NRP_STORAGE_ADDRESS
        storage_address = os.environ.get(self.env_vars_name['STORAGE_ADDRESS'],
                                         self.DEFAULT_STORAGE_HOST)
        storage_port = os.environ.get(self.env_vars_name['STORAGE_PORT'], self.DEFAULT_STORAGE_PORT)
        self.storage_uri = f'http://{storage_address}:{storage_port}/storage'

        self.MAX_SIMULATION_TIMEOUT = 24 * 60 * 60  # 1 day in seconds


# Instantiate the singleton
Settings = _Settings()
