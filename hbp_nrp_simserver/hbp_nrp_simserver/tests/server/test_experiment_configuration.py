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
Unit tests for hbp_nrp_simserver.server.experiment_configuration.validate
"""

__author__ = 'NRP software team, Ugo Albanese'

import unittest
from types import SimpleNamespace

import hbp_nrp_simserver.server.experiment_configuration as exp_conf


def _data_engine():
    return SimpleNamespace(EngineType="datatransfer_grpc_engine")


class TestExperimentConfigurationValidate(unittest.TestCase):

    def test_sets_all_defaults_when_missing(self):
        conf = SimpleNamespace(EngineConfigs=[_data_engine()])

        exp_conf.validate(conf)

        self.assertEqual(conf.SimulationTimeout, 0)
        self.assertEqual(conf.SimulationTimestep, 0.01)
        self.assertEqual(conf.EngineConfigs[0].MQTTBroker, "localhost:1883")

    def test_timestep_default_set_even_when_timeout_present(self):
        # Regression: the old if/elif chain skipped the SimulationTimestep
        # default (and the EngineConfigs check) whenever SimulationTimeout
        # was already present.
        conf = SimpleNamespace(SimulationTimeout=5, EngineConfigs=[_data_engine()])

        exp_conf.validate(conf)

        self.assertEqual(conf.SimulationTimeout, 5)
        self.assertEqual(conf.SimulationTimestep, 0.01)

    def test_missing_engine_configs_raises_even_when_timeout_present(self):
        # Regression: with if/elif this check was unreachable once
        # SimulationTimeout existed, so validation silently passed.
        conf = SimpleNamespace(SimulationTimeout=5)

        with self.assertRaises(ValueError):
            exp_conf.validate(conf)

    def test_missing_data_transfer_engine_raises(self):
        conf = SimpleNamespace(EngineConfigs=[SimpleNamespace(EngineType="some_other_engine")])

        with self.assertRaises(ValueError):
            exp_conf.validate(conf)

    def test_existing_mqtt_broker_is_preserved(self):
        engine = SimpleNamespace(EngineType="datatransfer_grpc_engine",
                                 MQTTBroker="broker.example:9999")
        conf = SimpleNamespace(EngineConfigs=[engine])

        exp_conf.validate(conf)

        self.assertEqual(conf.EngineConfigs[0].MQTTBroker, "broker.example:9999")


if __name__ == '__main__':
    unittest.main()
