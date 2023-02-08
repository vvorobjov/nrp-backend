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
Unit tests for the sim config model
"""

import unittest
import os
from unittest.mock import patch, MagicMock

# NOTE: top level import won't work here as os is NOT MOCKED at the point
from hbp_nrp_commons.workspace.settings import _Settings

__author__ = 'NRP software team, Hossain Mahmud'

_base_path = 'hbp_nrp_commons.workspace.settings'


@patch(f'{_base_path}.logging', new=MagicMock())
class TestSimConfig(unittest.TestCase):
    def setUp(self):
        # mock os
        os_patcher = patch(f'{_base_path}.os')
        self.os_mock = os_patcher.start()
        self.addCleanup(os_patcher.stop)
        # restore os.path.join and os.path.dirname
        self.os_mock.path.join = os.path.join
        self.os_mock.path.dirname = os.path.dirname
        
        self.os_mock.environ = {
            'HOME': '/home/dir',
            'HBP': '/hbp/dir',
            'NRP_SIMULATION_DIR': '/sim/dir',
            'NRP_MQTT_BROKER_ADDRESS' : "mqtt:6000",
            "STORAGE_ADDRESS": "localhost",
            "STORAGE_PORT": 99
        }

        #Clear the Singleton instance (if exists), and force a new copy
        _Settings._Settings__instance = None

    def tearDown(self):
        pass

    def test_init_Settings(self):
        settings = _Settings()
        self.assertEqual(settings.nrp_home, '/hbp/dir')
        self.assertEqual(settings.sim_dir_symlink, '/sim/dir')

        self.assertEqual(settings.mqtt_broker_host, 'mqtt')
        self.assertEqual(settings.mqtt_broker_port, 6000)
        self.assertFalse(settings.is_mqtt_broker_default)

        self.assertEqual("http://localhost:99/storage", settings.storage_uri)
    
    def test_default_mqtt_broker(self):
        del self.os_mock.environ["NRP_MQTT_BROKER_ADDRESS"]

        settings = _Settings()
        self.assertEqual(settings.mqtt_broker_host, _Settings.DEFAULT_MQTT_BROKER_HOST)
        self.assertEqual(settings.mqtt_broker_port, _Settings.DEFAULT_MQTT_BROKER_PORT)
        self.assertTrue(settings.is_mqtt_broker_default)

    def test_malformed_mqtt_broker(self):
        for v in [None, "", "host:host:90", "host:host"]:
            self.os_mock.environ["NRP_MQTT_BROKER_ADDRESS"] = v

            settings = _Settings()
            
            self.assertEqual(settings.mqtt_broker_host, _Settings.DEFAULT_MQTT_BROKER_HOST)
            self.assertEqual(settings.mqtt_broker_port, _Settings.DEFAULT_MQTT_BROKER_PORT)
            self.assertTrue(settings.is_mqtt_broker_default)

            #Clear the Singleton instance (if exists), and force a new copy
            _Settings._Settings__instance = None

if __name__ == '__main__':
    unittest.main()
