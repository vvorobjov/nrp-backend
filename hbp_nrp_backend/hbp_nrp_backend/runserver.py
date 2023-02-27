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
Runs the REST server
"""

import os

__author__ = 'NRP software team, Georg Hinkel, Ugo Albanese'

import logging
import sys
import argparse
# from threading import Thread
from hbp_nrp_backend.rest_server import app
# from hbp_nrp_backend.rest_server.cleanup import clean_simulations
from hbp_nrp_backend.rest_server.RestSyncMiddleware import RestSyncMiddleware
from hbp_nrp_commons import get_python_interpreter, set_up_logger


DEFAULT_PORT = 5000
DEFAULT_HOST = '0.0.0.0'


# Warning: We do not use __name__  here, since it translates to "__main__"
# when this file is ran directly (such as python runserver.py)
logger = logging.getLogger('hbp_nrp_backend')


def __process_args():  # pragma: no cover
    """
    Processes the arguments to the server.
    """
    nrp_debug_env_var = os.environ.get("NRP_DEBUG", default="")

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', dest='port',
                        help="'specify the application server's port'")
    # TODO support for user specified debugger server address and port
    parser.add_argument('--debug', dest='debug',
                        help="debug with IDE specified in the NRP_DEBUG env var (pycharm, vscode)"
                             " listening on 0.0.0.0:9991",
                        default=False,
                        action="store_true")
    parser.add_argument('--logfile', dest='logfile',
                        help="specify the logfile for the nrp-backend")
    parser.add_argument("--verbose",  dest="verbose_logs", help="Increase output verbosity",
                        default=False,
                        action="store_true")

    args = parser.parse_args()

    # debugging support with VScode and PyCharm
    if args.debug and nrp_debug_env_var:
        debug_address, debug_port = ("0.0.0.0", 9991)

        if nrp_debug_env_var == "pycharm":
            # pylint: disable=import-error
            import pydevd_pycharm
            # blocks execution until client is attached
            print("Pycharm debugging server active, waiting for client...")
            pydevd_pycharm.settrace(debug_address,
                                    port=debug_port,
                                    stdoutToServer=True,
                                    stderrToServer=True)
        elif nrp_debug_env_var == "vscode":
            # pylint: disable=import-error
            import debugpy
            debugpy.configure(python=get_python_interpreter())
            debugpy.listen((debug_address, debug_port))
            print("VSCode debugging server active, waiting for client...")
            debugpy.wait_for_client()  # blocks execution until client is attached
        else:
            print(
                f'Unsupported IDE "{nrp_debug_env_var}" for debugging: Ignoring argument')

    return args


# Detect uwsgi, and initialize multithreading support
if __name__.find("uwsgi_file") == 0:  # pragma: no cover
    app.wsgi_app = RestSyncMiddleware(app.wsgi_app, app)
    _args = __process_args()

    # Initialize root logger, any logger in this process will inherit the settings
    set_up_logger(
        name=None, level=logging.DEBUG if _args.verbose_logs else logging.INFO)
    logger.warning("Application started with uWSGI or any other framework. logging "
                   "to console by default!")


# This is executed in local install mode without uwsgi
if __name__ == '__main__':  # pragma: no cover

    # TODO restore cleanup support
    # root_logger.info("Starting cleanup thread")
    # cleanup_thread = Thread(target=clean_simulations, name="SimulationCleanup")
    # cleanup_thread.setDaemon(True)
    # cleanup_thread.start()s

    app.wsgi_app = RestSyncMiddleware(app.wsgi_app, app)

    _args = __process_args()
    # Initialize root logger, any logger in this process will inherit the settings
    set_up_logger(name=None, logfile_name=_args.logfile,
                  level=logging.DEBUG if _args.verbose_logs else logging.INFO)

    port = DEFAULT_PORT

    try:
        port = int(_args.port)
    except (TypeError, ValueError) as _:
        logger.warning(
            "Could not parse port, will use default port: %s", str(DEFAULT_PORT))

    logger.info("Starting the REST backend server now ...")
    app.run(port=port, host=DEFAULT_HOST, threaded=True)
    logger.info("REST backend server terminated.")
