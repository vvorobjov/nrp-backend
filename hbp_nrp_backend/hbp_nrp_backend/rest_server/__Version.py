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
This module contains the REST implementation
for retrieving the versions of all NRP python component packages.
"""

__author__ = 'NRP software team'

import importlib

from flask_restful import Resource

from . import ErrorMessages, docstring_parameter
from .RestSyncMiddleware import RestSyncMiddleware

# pylint: disable=R0201
COMPONENTS_PACKAGES_NAMES = ['hbp_nrp_backend', 'hbp_nrp_simserver']
for c_p in COMPONENTS_PACKAGES_NAMES:
    importlib.import_module(c_p)


class Version(Resource):
    """
    Implements the REST service providing the user with the versions
    of all NRP python COMPONENTS_PACKAGES_NAMES.
    """
    @RestSyncMiddleware.threadsafe
    @docstring_parameter(ErrorMessages.VERSIONS_RETRIEVED_200)
    def get(self):
        """
        Returns the versions of all NRP python component packages.

        :> json string hbp_nrp_backend:
        :> json string hbp_nrp_simserver:

        :status 200: {0}
        """

        # pylint: disable=eval-used
        return {name: getattr(name, "__version__") for name in COMPONENTS_PACKAGES_NAMES}, 200
