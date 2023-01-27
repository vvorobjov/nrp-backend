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
This module provides helper functions to handle zip
"""
__author__ = 'NRP software team, Hossain Mahmud'

import os
import zipfile
import logging
from typing import Union, IO, Iterable, Optional

logger = logging.getLogger(__name__)

# pylint: disable=inconsistent-return-statements
def extract_all(zip_target: Union[str, os.PathLike, IO[bytes]],
                extract_to: Union[str, os.PathLike],
                overwrite: bool = False,
                preserve_path: bool =True) -> None:  # pragma: no cover
    """
    Extract a zip in the given location

    :param zip_target: absolute path of the zip file or BytesIO object
    :param extract_to: absolute path to the folder where to unzip
    :param overwrite: boolean to indicate whether to overwrite the existing contents
    :param preserve_path: preserve the archived file paths, flatten them otherwise
    :return:
    """
    with zipfile.ZipFile(zip_target) as zf:
        if not overwrite:
            for f in zf.namelist():
                if os.path.exists(os.path.join(extract_to, f)):
                    logger.info("Aborting extraction. %s exists.", f)
                    return None
        try:
            if not os.path.exists(extract_to):
                os.makedirs(extract_to)

            if preserve_path:
                zf.extractall(extract_to)
            else:
                for zip_info in zf.infolist():
                    if zip_info.filename[-1] == '/':
                        continue  # skip directories
                    zip_info.filename = os.path.basename(zip_info.filename)
                    zf.extract(zip_info, extract_to)
                # for f in zf.namelist():
                #     f_name = os.path.basename(f)
                #     if f_name:
                #         with open(os.path.join(extract_to, f_name), 'w') as file_to_write:
                #             file_to_write.write(zf.read(f))
        except IOError as ex:
            logger.info("Extraction failed due to %s", str(ex))

def create_from_path(path: Union[str, os.PathLike],
                     dest_zip_file: Union[str, os.PathLike]) -> None:
    """
    Create a zip from a path

    :param path: path to be compressed
    :param dest_zip_file: file name and path to the zip archive
    """
    with zipfile.ZipFile(dest_zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(path):
            for f in files:
                zf.write(filename=os.path.join(root, f),
                         arcname=os.path.relpath(os.path.join(root, f),
                                                 start=os.path.join(path, '..')))

def create_from_filelist(file_list: Iterable[Union[str, os.PathLike]],
                         dest_zip_file: Union[str, os.PathLike],
                         preserve_path : bool = True) -> None:
    """
    Create a zip from file_list.

    :param file_list: the list of files to be compressed
    :param dest_zip_file: file name and path to the zip archive
    :param preserve_path: the file paths will be preseverd in the archive.
    """
    if file_list:
        with zipfile.ZipFile(dest_zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in file_list:
                zf.write(filename=file,
                         arcname=os.path.basename(file) if not preserve_path else None)

def get_rootname(zip_abs_path: Union[str, os.PathLike, IO[bytes]]) -> Optional[str]: # pragma: no cover
    """
    Gets the root folder name inside a zip
    Note: for some zip, namelist doesn't contain the folders as entries
    Possibly dependent upon how the zip was bundled, hence the extra check

    :return: root folder name inside a zip or None if not found
    """

    with zipfile.ZipFile(zip_abs_path) as r_zip:
        first_item = r_zip.namelist()[0]
        if first_item.endswith('/'):
            return first_item
        elif '/' in first_item:
            return first_item.split('/')[0]
        else:
            return None
