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
This module defines a job that runs in the background and looks for expired simulations
"""


import datetime
import time
import logging

from hbp_nrp_backend.simulation_control import simulations, timezone
from hbp_nrp_commons.workspace.settings import Settings
from hbp_nrp_commons.simulation_lifecycle import SimulationLifecycle

__author__ = 'NRP software team, Georg Hinkel'

logger = logging.getLogger(__name__)


def clean_simulations():  # pragma: no cover
    """
    Wakes up every five minutes and stops expired simulations

    This function is not unit-tested as it contains an endless loop
    """
    _last_stopped = 0
    while True:
        time.sleep(300)
        _last_stopped = remove_old_simulations(_last_stopped)


def remove_old_simulations(_last_stopped):
    """
    Stops expired simulations
    """
    logger.info("Start cleanup")
    current_time = datetime.datetime.now(timezone)
    # NOTE change when refactoring simulations ID types
    for sim_id, sim in enumerate(simulations, start=_last_stopped):
        kill_time_reached = sim.kill_datetime is not None and sim.kill_datetime < current_time
        max_sim_time_reached = (
            sim.creation_datetime +
            datetime.timedelta(seconds=Settings.MAX_SIMULATION_TIMEOUT) < current_time)

        if kill_time_reached or max_sim_time_reached:
            if sim.state not in SimulationLifecycle.FINAL_STATES:
                logger.info("Stopping expired simulation %s", str(sim.sim_id))
                sim.state = 'stopped'
            _last_stopped = sim_id
    return _last_stopped
