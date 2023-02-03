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
Wrapper around the storage API
"""
import fnmatch
import logging
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, List

import requests
from hbp_nrp_commons.workspace.settings import Settings
from hbp_nrp_commons.workspace.sim_util import SimUtil

__author__ = 'NRP software team, Manos Angelidis'

logger = logging.getLogger(__name__)


class StorageClient:
    """
    Wrapper around the storage server API. Users of this class should first
    call the authentication function to retrieve a token, before making the
    requests to the storage server
    """

    __instance = None
    _sim_dir = None

    def __new__(cls):
        """
        Overridden new for the singleton implementation

        :return: Singleton instance
        """

        if StorageClient.__instance is None:
            StorageClient.__instance = object.__new__(cls)

        return StorageClient.__instance

    def __init__(self):
        """
        Creates the storage client
        """
        self.__proxy_url = Settings.storage_uri

        # folders in resources we want to filter
        self.__filtered_resources = []

    def set_sim_dir(self, sim_dir):
        """
        Sets the sim_dir for this client

        :param sim_dir: Simulation directory
        """

        self._sim_dir = sim_dir

    def get_user(self, token):
        """
        Retrieves the user id for the specified authentication token

        :param token: the authentication token
        :return: the user id
        :raises: ValueError Could not verify auth token
        :raises: ConnectionError
        """

        try:
            res = requests.get(
                f'{self.__proxy_url}/identity/me',
                headers={'Authorization': f'Bearer {token}'}
            )
            if 200 <= res.status_code < 300:
                return res.json()
            else:
                raise ValueError(
                    f'Could not verify auth token, status code {str(res.status_code)}')
        except requests.exceptions.ConnectionError as err:
            logger.exception(err)
            raise ConnectionError from err

    def can_access_experiment(self, token: str, context_id, experiment_id):
        """
        Verifies if an authenticated user can access an experiment

        :param token: The authentication token
        :param context_id: Optional context idenfifier
        :param experiment_id: The  experiment id
        :return: Whether the user can access the experiment
        """
        return self.list_experiments(token, context_id, name=experiment_id) is not None

    def list_experiments(self, token: str, context_id, get_all=False, name=None):
        """
        Lists the experiments the user has access to depending on his token.

        :param token: a valid token to be used for the request
        :param context_id: the context_id if we are using collab storage
        :param get_all: a parameter to return all the available experiments,
                        not only the ones available to a specific user
        :param name: if we want to get a specific folder i.e. the robots
        :return: an array of all the available to the user experiments
        """
        query_args = {}
        if name:
            query_args['filter'] = urllib.parse.quote_plus(name)
        if get_all:
            query_args['all'] = str(get_all).lower()

        try:
            res = requests.get(
                '{proxy_url}/storage/experiments?{params}'.format(
                    proxy_url=self.__proxy_url,
                    params=urllib.parse.urlencode(query_args)),
                headers={'Authorization': f'Bearer {token}',
                         'context-id': context_id}
            )

            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    f'Failed to communicate with the storage server,'
                    f' status code {str(res.status_code)}')
            return res.json()
        except requests.exceptions.ConnectionError as err:
            logger.exception(err)
            raise ConnectionError from err

    def get_file(self, token: str, experiment: str, filename: str, by_name: bool = False) -> bytes:
        """
        Gets the content of a file under an experiment based on the filename and on the filetype

        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param filename: the name of the file to return
        :return: if successful, the content of the file as a binary string
        """
        try:
            request_url = f'{self.__proxy_url}/storage/{experiment}/{filename}' \
                          f'?byname={str(by_name).lower()}'

            res = requests.get(request_url,
                               headers={'Authorization': f'Bearer {token}'})

            # TODO what about missing files? i.e. 204
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception('Failed to communicate with the storage server, status code {}'
                                .format(res.status_code))

            return res.content

        except requests.exceptions.ConnectionError as err:
            logger.exception(err)
            raise ConnectionError from err

    def delete_file(self, token: str, experiment: str, filename) -> str:
        """
        Deletes a file under an experiment based on the
        experiment name and the filename. Needs the user token

        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param filename: the name of the file to delete
        :return: if successful, the name of the deleted file
        """
        try:
            request_url = '{proxy_url}/storage/{path}'.format(
                proxy_url=self.__proxy_url,
                path=urllib.parse.quote(os.path.join(
                    experiment, filename), safe='')
            )

            res = requests.delete(
                request_url,
                headers={'Authorization': f'Bearer {token}'}
            )

            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    f'Failed to communicate with the storage server, status code {str(res.status_code)}')

            return filename
        except requests.exceptions.ConnectionError as err:
            logger.exception(err)
            raise ConnectionError from err

    def create_or_update(self, token: str, experiment: str, filename,
                         content, content_type: str, append: bool = False):
        """
        Creates or updates a file under an experiment

        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param filename: the name of the file to update/create
        :param content: the content of the file
        :param content_type: the content type of the file i.e. text/plain or
                             application/octet-stream
        :param append: append to file or create new file
        """
        try:
            append_query = "?append=true" if append else ""
            request_url = f'{self.__proxy_url}/storage/{experiment}/{filename}{append_query}'

            res = requests.post(request_url,
                                headers={'content-type': content_type,
                                         'Authorization': f'Bearer {token}'},
                                data=content)

            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(f'Failed to communicate with the storage server,'
                                f' status code {str(res.status_code)}')

            return res.status_code
        except requests.exceptions.ConnectionError as err:
            logger.exception(err)
            raise ConnectionError from err

    def create_folder(self, token: str, experiment: str, name: str):
        """
        Creates a folder under an experiment. If the folder exists we reuse it

        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param name: the name of the folder to create
        """
        try:
            request_url = '{proxy_url}/storage/{experiment}/{name}?type=folder'.format(
                proxy_url=self.__proxy_url,
                experiment=experiment,
                name=name
            )

            res = requests.post(
                request_url,
                headers={'Authorization': f'Bearer {token}'}
            )

            if res.status_code == 400:
                logger.info('The folder with the name %s already exists in the storage, reusing',
                            name)
                return 200

            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(f'Failed to communicate with the storage server,'
                                f' status code {str(res.status_code)}')

            return res.json()
        except requests.exceptions.ConnectionError as err:
            logger.exception(err)
            raise ConnectionError from err

    def create_and_extract_zip(self, token: str, experiment: str, name: str, content):
        """
        Creates and extracts a zip under an experiment.

        .. TODO:: add a REST endpoint in the storage to allow the transfer of multiple files.
        For instance we might add a create_files(files_list) in StorageClient.
        Internally, the files might be zipped on the client and unzipped on the server.

        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param name: the name of the zip
        :param content: the content of the file
        """
        try:
            request_url = '{proxy_url}/storage/{experiment}/{name}?type=zip'.format(
                proxy_url=self.__proxy_url,
                experiment=experiment,
                name=name)

            res = requests.post(request_url,
                                headers={
                                    'content-type': 'application/octet-stream',
                                    'Authorization': f'Bearer {token}'},
                                data=content)

            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(f'Failed to communicate with the storage server,'
                                f' status code {str(res.status_code)}')
            return res.status_code
        except requests.exceptions.ConnectionError as err:
            logger.exception(err)
            raise ConnectionError from err

    def get_files_list(self, token: str, experiment: str, folder: bool = False):
        """
        Lists all the files under an experiment based on the
        experiment name and the user token

        :param token: a valid token to be used for the request
        :param experiment: the name of the experiment
        :param folder: A boolean variable indicating whether folders should included in the result.

        :return: if successful, the files under the experiment
        """
        try:

            res = requests.get(
                f'{self.__proxy_url}/storage/{experiment}',  # request url
                headers={'Authorization': f'Bearer {token}'})

            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(
                    f'Failed to communicate with the storage server,'
                    f' status code {str(res.status_code)}')
                # folder variable is added because copy_resources_folder needs
                # to list the folders too

            # TODO explicit file extensions exclusion list
            return [entry for entry in res.json()
                    if (entry['type'] == 'file' or folder) and
                    not self.check_file_extension(entry['name'], ['.swp'])]

        except requests.exceptions.ConnectionError as err:
            logger.exception(err)
            raise ConnectionError from err

    def clone_file(self, token: str, filename: str, experiment: str) -> Optional[str]:
        """
        Clones a file according to a given filename to a simulation folder.
        The caller then has the responsibility of managing this folder.

        :param filename: The filename of the file to clone
        :param token: The token of the request
        :param experiment: The experiment which contains the file
        :return: The local path of the cloned file,
        """
        for folder_entry in self.get_files_list(token, experiment):
            if filename in folder_entry['name']:
                clone_destination: str = os.path.join(self._sim_dir, filename)
                with open(clone_destination, "wb") as f:
                    f.write(self.get_file(
                        token, experiment, filename, by_name=True))
                break
        else:
            return None  # filename not found

        return clone_destination

    def copy_file_content(self, token: str, src_folder, dest_folder, filename):
        """
        copy the content of file located in the Storage into the proper tmp folder

        :param token: The token of the request
        :param src_folder: folder location where it will be copy from
        :param dest_folder: folder location where it will be copy to
        :param filename: name of the file to be copied.
        """
        with open(os.path.join(src_folder, filename), "wb") as f:
            f.write(self.get_file(token, dest_folder, filename, by_name=True))

    # pylint: disable=no-self-use
    @staticmethod
    def check_file_extension(filename: str, extensions: List[str]) -> bool:
        """
        checks if a file is of a certain extension

        :param filename: the file name
        :param extensions: the extensions list to check
        """
        _, ext = os.path.splitext(filename)
        return ext.lower() in extensions

    def copy_folder_content_to_tmp(self, token: str, folder):
        """
        Copy the content of the folder located in storage/experiment into sim_dir folder

        :param token: The token of the request
        :param folder: the folder in the storage folder to copy in tmp folder,
                       it has included the uuid of the experiment
        """
        folder['fullpath'] = folder['name']
        child_folders = [folder]

        while child_folders:
            current_folder = child_folders.pop()
            folder_path = current_folder['fullpath']
            folder_uuid = urllib.parse.quote_plus(current_folder['uuid'])

            for entry_to_copy in self.get_files_list(token, folder_uuid, folder=True):
                entry_name, entry_type = entry_to_copy['name'], entry_to_copy['type']

                if entry_type == 'folder':
                    if entry_name not in self.__filtered_resources:
                        entry_to_copy['fullpath'] = os.path.join(
                            folder_path, entry_name)
                        child_folders.append(entry_to_copy)

                elif entry_type == 'file':
                    folder_tmp_path = str(
                        os.path.join(self._sim_dir, folder_path))

                    SimUtil.makedirs(folder_tmp_path)

                    self.copy_file_content(
                        token,
                        folder_tmp_path,
                        folder_uuid,
                        entry_name
                    )

    # pylint: disable=broad-except
    def clone_all_experiment_files(self,
                                   token: str,
                                   experiment: str,
                                   destination_dir: Optional[str] = None,
                                   exclude: Optional[List[str]] = None):
        """
        Clones all the experiment files to a simulation folder.
        The caller has then the responsibility of managing this folder.

        :param token: The token of the request
        :param experiment: The experiment to clone
        :param destination_dir: the directory in which to clone the files,
            if None or an empty string is provided, clones into a temporary folder
        :param exclude: a list of folders of files not to clone (folder names ends with '/')
        :return: A dictionary containing the paths to the experiment files
        """

        self._sim_dir = destination_dir if destination_dir else tempfile.mkdtemp(
            prefix='nrp.')
        # TODO Resources self.__resources_path = os.path.join(self._sim_dir, "resources")

        exclude_rules = exclude if exclude is not None else []

        # local helper functions

        def match_exclusion(name: str, exclusion_list: List[str]):
            return any((fnmatch.fnmatch(name, exc_rule) for exc_rule in exclusion_list))

        def is_directory(rule: str):
            return rule.endswith('/')

        # files exclude rules should be matched against the file name and its os.path.dirname
        exclude_file_rules = [r for r in exclude_rules
                              if not is_directory(r)]
        exclude_file_rules += [os.path.dirname(r) for r in exclude_rules
                               if not is_directory(r)]

        exclude_dirs_rules = [os.path.dirname(r) for r in exclude_rules
                              if is_directory(r)]

        for entry_to_clone in self.get_files_list(token, experiment, folder=True):

            entry_type, entry_name = entry_to_clone['type'], entry_to_clone['name']

            if entry_type == 'folder' and not match_exclusion(entry_name, exclude_dirs_rules):
                self.copy_folder_content_to_tmp(token, entry_to_clone)

            elif entry_type == 'file' and not match_exclusion(entry_name, exclude_file_rules):
                dest_file_path = os.path.join(destination_dir, entry_name)

                with open(dest_file_path, "wb") as file_clone:
                    file_contents = self.get_file(token, experiment, entry_name,
                                                  by_name=True)
                    file_clone.write(file_contents)

        return destination_dir

    def get_folder_uuid_by_name(self, token, context_id, folder_name):
        """
        Returns the uuid of a folder provided its name

        :param token: a valid token to be used for the request
        :param context_id: the context_id of the collab
        :param folder_name: the name of the folder
        :return: if found, the uuid of the named folder
        """
        folders = self.list_experiments(
            token, context_id, get_all=True, name=folder_name)

        for folder in (f for f in folders if f["name"] == folder_name):
            return folder["uuid"]

    # Unused, but useful when these features will be restored
    #
    # TODO Resources
    # def copy_resources_folder(self, token, experiment):
    #     """
    #     Copy the resources folder located in storage/experiment into simulation folder
    #
    #     :param token: The token of the request
    #     :param experiment: The experiment which contains the resource folder
    #     """
    #     try:
    #         for folder_entry in self.get_files_list(token, experiment, True):
    #             if folder_entry['name'] == 'resources' and folder_entry['type'] == 'folder':
    #                 if os.path.exists(self.__resources_path):
    #                     SimUtil.clear_dir(self.__resources_path)
    #                 self.copy_folder_content_to_tmp(token, folder_entry)
    #     except Exception:  # pylint: disable=broad-except
    #         logger.exception(
    #             'An error happened trying to copy resources to tmp ')
    #         raise
    #

    # HELPER FUNCTIONS
