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
This is package contains the Simulation server.
It runs user-defined python scripts that uses on nrp_core.client.NRPCore.

A simulation server can be managed by an instance of SimulationServerInstance and once initialized, it sends
on MQTT topics, informations about its status (/status) and,
on error, a message describing such error (/runtime_error).

The runtime state of the server is controlled via an instance of SimulationLifecycle that reacts to 
state changes initiated by the user via the REST API exposed by hbp_nrp_backend.
Besides those, state changes initiated by the Simulation server are the ones dependent on the simulation being run, i.e.
'completed' and 'failed'.

"""

__author__ = 'NRP software team, Ugo Albanese'

from dataclasses import dataclass
from enum import IntEnum, unique

import pytz

timezone = pytz.timezone('Europe/Zurich')

# import nrp_core python client class client
from nrp_core.client import NrpCore as NrpCoreClientClass  # nrp-core python client

MQTT_TOPIC_PREFIX = 'nrp_simulation'

# TODO use protobuf as message format instead of JSON
# The MQTT topic on which the server will publish, every second,
# the status of the 'sim_id' simulation.
# The Message is a JSON object specified in SimulationServer._create_state_message:
TOPIC_STATUS = lambda sim_id: f'{MQTT_TOPIC_PREFIX}/{sim_id}/status'

# The MQTT topic used to synchronize the simulation lifecycles of the 'sim_id' simulation .
# Used in hbp_nrp_commons.sim_lifecycle.SimulationLifecycle and subclasses
# in the method __propagate_state_changes.
# The Message is a JSON object specified in SimulationLifecycle.__propagate_state_changes
TOPIC_LIFECYCLE = lambda sim_id: f'{MQTT_TOPIC_PREFIX}/{sim_id}/lifecycle'

# The MQTT topic on which the server will publish any runtime error caused
# by the 'sim_id' simulation.
# The Message is a JSON object specified in simulation_server.SimulationServer.publish_error
TOPIC_ERROR = lambda sim_id: f'{MQTT_TOPIC_PREFIX}/{sim_id}/runtime_error'


@dataclass
class SimulationSettings:
    """
    sim_id: the ID of the simulation
    sim_dir: the directory containing the simulation files
    exp_config_file: the experiment configuration file name (e.g. experiment_configuration.json)
    main_script_file: the simulation's main script file name (e.g. main_script.py)
    """
    sim_id: str
    sim_dir: str
    exp_config_file: str
    main_script_file: str


@unique
class ServerProcessExitCodes(IntEnum):
    """
    Exit error codes for simulation_server.py
    """
    NO_ERROR = 0
    INITIALIZATION_ERROR = 1
    SHUTDOWN_ERROR = 2
    RUNNING_ERROR = 3

