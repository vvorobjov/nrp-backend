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
This module contains an implementation to run a certain function repeatedly until a timeout is
reached
"""

from threading import Thread, Event
import logging

__author__ = 'NRP software team'

from typing import Callable

logger = logging.getLogger(__name__)


# from http://stackoverflow.com/questions/12435211/
# python-threading-timer-repeat-function-every-n-seconds
class Timer(Thread):
    """
    Timer that runs a function each 'interval' seconds
    similar to threading.Thread
    """

    def __init__(self, interval: int, callback: Callable[..., None], **kwargs):
        """
        Construct the timer.

        :param interval: the time interval in seconds
        :param callback: the function to be called
        """
        
        Thread.__init__(self,
                        **kwargs)
        
        self.setDaemon(kwargs.get("daemon", True))
        self.interval = interval
        self.callback = callback

        self.stopped = Event()
        self.stopped.clear()

    def run(self) -> None:
        """
        Exec the function and restart the timer.
        """
        while not self.stopped.wait(self.interval):
            self.callback()

    def cancel_all(self) -> None:
        """
        Cancel the timer.
        """
        self.stopped.set()
