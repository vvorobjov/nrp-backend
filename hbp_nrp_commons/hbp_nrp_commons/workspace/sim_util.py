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
This module implements Utility functions used by backend
"""
import os
import errno
import shutil
import logging
import tempfile
from typing import List, Optional

from hbp_nrp_backend import NRPServicesGeneralException
from .settings import Settings

__author__ = 'NRP software team, Hossain Mahmud'

logger = logging.getLogger(__name__)


class SimUtil:
    """
    Utility methods for a simulation
    """

    @staticmethod
    def makedirs(directory: str) -> None:
        """
        Creates [nested] directory if not exists

        :raises: all errors except directory exists
        """
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                logger.exception('An error happened trying to create %s', directory)
                raise

    @staticmethod
    def mkdir(directory: str) -> None:
        """
        Creates [nested] directory if not exists

        :raises: all errors except directory exists
        """
        SimUtil.makedirs(directory)

    @staticmethod
    def rmdir(directory: str) -> None:
        """
        Removes [nested] directory if not exists

        :raises: all errors except directory exists
        """

        shutil.rmtree(os.path.realpath(directory))

    @staticmethod
    def clear_dir(directory: str) -> None:
        """
        Deletes contents of a directory
        """

        shutil.rmtree(os.path.realpath(directory))
        SimUtil.makedirs(directory)

    @staticmethod
    def init_simulation_dir(sim_id: str) -> str:
        """
        Creates a temporary directory and links it to Settings.sim_dir_symlink

        :params sim_id: simulation ID of the simulation we're going to create a temp dir for
                        we embed the sim_id into simulation temp dir so the
                        delete_simulation_dir deletes correctly

        :returns sim_dir: the full path of the address of temp dir for the simulation
        """
        sim_prefix = f'nrp.{str(sim_id)}.' # be sure that sim_id is a str

        sim_dir = tempfile.mkdtemp(prefix=sim_prefix)

        sim_dir_symlink = Settings.sim_dir_symlink
        try:
            if os.path.exists(sim_dir_symlink):
                # clean up dirty sim_dir (possibly from some prior crashed simulation)
                shutil.rmtree(os.path.realpath(sim_dir_symlink))
                os.unlink(sim_dir_symlink)

            os.symlink(sim_dir, sim_dir_symlink)
        except (IOError, OSError) as err:
            raise NRPServicesGeneralException(
                "Could not create symlink to temp simulation folder. {err}".format(err=err),
                error_type="Server Error")

        return sim_dir

    @staticmethod
    def delete_simulation_dir(sim_dir=None):
        """
        Removes simulation directory
        Check that you are deleting the right folder by checking the sim_id
        """
        try:
            if os.path.exists(Settings.sim_dir_symlink):
                current_sim_id = SimUtil.extract_sim_id(os.path.realpath(Settings.sim_dir_symlink))
                input_sim_id = SimUtil.extract_sim_id(sim_dir)
                if (current_sim_id == input_sim_id) or (sim_dir is None):
                    shutil.rmtree(os.path.realpath(Settings.sim_dir_symlink))
                    os.unlink(Settings.sim_dir_symlink)
        except (IOError, OSError) as error:
            raise NRPServicesGeneralException(
                "Could not access symlink to temp simulation folder. {err}".format(err=error),
                error_type="Server Error")

    @staticmethod
    def extract_sim_id(sim_dir: str) -> Optional[int]:
        """
        :param sim_dir: the address of temp folder
        :return: returns the sim_id embedded in sim_dir.
        """
        try:
            base_name = os.path.basename(sim_dir)
            _, sim_id, _ = base_name.split(".", 2)
            return sim_id
        except ValueError:
            return None

    @staticmethod
    def find_file_in_paths(file_rel_path: str, path_list: List[str]) -> Optional[str]:
        """
        :return: returns the absolute path of the first file found in path_list.
                 if not found, returns and empty string.
        """

        for file_path in (p for p in path_list if os.path.isfile(os.path.join(p, file_rel_path))):
            return os.path.join(file_path, file_rel_path)

        return None
