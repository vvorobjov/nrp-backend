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

import json
from types import SimpleNamespace
from typing import List

type_class = SimpleNamespace


def parse(exp_config_file_path: str) -> type_class:
    with open(exp_config_file_path) as exp_config_file:
        try:
            # TODO validate json using schema
            return json.load(exp_config_file, object_hook=lambda d: type_class(**d))
        except json.JSONDecodeError as d_error:
            raise ValueError(f"Could not parse experiment configuration"
                             f" {exp_config_file_path}: {d_error}")


def validate(exp_config: type_class) -> type_class:
    """
    validate and set default for exp_config
    # TODO USE json schema
    """
    # must have SimulationTimeout otherwise set default
    if not hasattr(exp_config, "SimulationTimeout"):
        setattr(exp_config, "SimulationTimeout", 0)
    # must have SimulationTimestep otherwise set default
    elif not hasattr(exp_config, "SimulationTimestep"):
        setattr(exp_config, "SimulationTimestep", 0.01)

    # must have EngineConfigs otherwise raise
    elif not hasattr(exp_config, "EngineConfigs"):
        raise ValueError("No EngineConfigs in experiment configuration")

    # must have datatransfer_grpc_engine otherwise raise
    try:
        idx = engine_index(exp_config, "datatransfer_grpc_engine")
        data_engine_conf = getattr(exp_config, "EngineConfigs")[idx]
    except ValueError:
        raise ValueError("No datatransfer_grpc_engine in experiment configuration")
    # must have datatransfer_grpc_engine.MQTTBroker otherwise set default
    if not hasattr(data_engine_conf, "MQTTBroker"):
        setattr(data_engine_conf, "MQTTBroker", "localhost:1883")

    return exp_config


def engine_index(exp_config: type_class, engine_type: str) -> int:
    # find engine_type index in conf.EngineConfigs list
    return [getattr(ec, "EngineType")
            for ec in getattr(exp_config, "EngineConfigs")].index(engine_type)


def mqtt_broker_host_port(exp_config: type_class) -> List[str]:
    data_engine_index = engine_index(exp_config,
                                     "datatransfer_grpc_engine")
    data_engine_conf = getattr(exp_config, "EngineConfigs")[data_engine_index]

    return getattr(data_engine_conf, "MQTTBroker").split(":")
