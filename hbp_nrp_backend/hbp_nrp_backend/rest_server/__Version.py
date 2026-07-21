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
import json

from flask import current_app
from flask.views import MethodView
from flask_smorest import Blueprint

from . import ErrorMessages, docstring_parameter
from .RestSyncMiddleware import RestSyncMiddleware

COMPONENTS_PACKAGES_NAMES = ['hbp_nrp_backend', 'hbp_nrp_simserver']
COMPONENTS_PACKAGES = {c_p_name: importlib.import_module(c_p_name)
                       for c_p_name in COMPONENTS_PACKAGES_NAMES}

VERSIONS = {name: getattr(module, "__version__")
            for name, module in COMPONENTS_PACKAGES.items()}

blp = Blueprint('version', __name__,
                description='Retrieve NRP component versions')


@blp.route('/version')
class Version(MethodView):
    """
    Implements the REST service providing the user with the versions
    of all NRP python COMPONENTS_PACKAGES_NAMES.
    """
    @RestSyncMiddleware.threadsafe
    @docstring_parameter(ErrorMessages.VERSIONS_RETRIEVED_200)
    def get(self):
        """
        Returns the versions of all NRP python component packages.

        :> json string hbp_nrp_backend: version
        :> json string hbp_nrp_simserver: version

        :status 200: {0}
        """
        # Serialize VERSIONS explicitly (rather than via @blp.response/jsonify)
        # to preserve the exact, insertion-ordered JSON body relied on by the
        # /version healthcheck and clients.
        return current_app.response_class(json.dumps(VERSIONS),
                                          status=200,
                                          mimetype='application/json')
