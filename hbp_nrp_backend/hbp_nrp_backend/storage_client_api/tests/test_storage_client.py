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
Storage client unit test
"""
from builtins import object
import inspect
import unittest
import shutil
import os
import requests
import json
from unittest.mock import patch, mock_open
from hbp_nrp_backend.storage_client_api.storage_client import StorageClient

# Used to mock all the http requests by providing a response and a
# status code


class MockResponse(object):

    def __init__(self, json_data, status_code, text=None, content=None, raw=None):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text
        self.content = content
        self.raw = raw

    def json(self):
        return self.json_data

# Functions that return fake responses based on the mock response class

# GET USER HTTP RESPONSES


def mocked_get_user_ok(*args, **kwargs):
    return MockResponse({"id": "fake_id"}, 200)


def mocked_request_not_ok(*args, **kwargs):
    return MockResponse(None, 404)

# GET EXPERIMENT HTTP RESPONSES


def mocked_get_experiments_ok(*args, **kwargs):
    response = [
        {
            "uuid": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
            "name": "New Experiment_3",
            "parent": "89857775-6215-4d53-94ee-fb6c18b9e2f8"
        },
        {
            "uuid": "b246cc8e-d844-4826-ae5b-d2c023b893d8",
            "name": "New Experiment_2",
            "parent": "89857775-6215-4d53-94ee-fb6c18b9e2f8"
        }
    ]
    return MockResponse(response, 200)


create_experiment_response = {
    "uuid": "8cb4fbea-f3cf-4ade-ad46-a570a1ab3b15",
    "entity_type": "folder",
    "name": "experiment",
    "description": "",
    "parent": "89857775-6215-4d53-94ee-fb6c18b9e2f8",
    "created_by": "302416",
    "created_on": "2017-09-12T08:15:39.471269Z",
    "modified_by": "302416",
    "modified_on": "2017-09-12T08:15:39.471353Z"
}

# CREATE EXPERIMENT HTTP RESPONSES


def mocked_create_experiment_ok(*args, **kwargs):
    return MockResponse(create_experiment_response, 200, "8cb4fbea-f3cf-4ade-ad46-a570a1ab3b15")


def mocked_create_experiment_exists(*args, **kwargs):
    return MockResponse(create_experiment_response, 200, "Experiment already exists")

# DELETE FILE HTTP RESPONSES


def mocked_delete_experiment_ok(*args, **kwargs):
    return MockResponse("Success", 200)

# CREATE OR UPDATE HTTP RESPONSES


def mocked_create_or_update_ok(*args, **kwargs):
    return MockResponse({
        "uuid": "8b4b993a-1324-4dbd-bbc1-91c85a996792"
    }, 200)

# CREATE FOLDER HTTP RESPONSES


def mocked_create_folder_ok(*args, **kwargs):
    return MockResponse({
        "uuid": "5b1a2363-1529-40cd-a8b7-94bfd6dea23d",
        "entity_type": "folder",
        "name": "fakeFolder",
        "description": "",
        "parent": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
        "created_by": "302416",
        "created_on": "2017-09-12T16:46:07.506604Z",
        "modified_by": "302416",
        "modified_on": "2017-09-12T16:46:07.506664Z"
    }, 200)

# EXTRACT ZIP HTTP RESPONSES


def mocked_create_and_extract_zip_ok(*args, **kwargs):
    return MockResponse([
        'undefined',
        'undefined',
        'undefined'
    ], 200)


# LIST FILES HTTP RESPONSES


def mocked_get_files_list_ok(*args, **kwargs):
    return MockResponse([{
        "uuid": "07b35b8f-67cd-4e94-8bec-5ede8049590d",
        "name": "env_editor.autosaved",
        "parent": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
        "contentType": "text/plain",
        "type": "file",
        "modifiedOn": "2017-08-31T13:56:34.306090Z"
    },
        {
            "uuid": "6a63d03e-6dad-4793-80d7-8e32a83ddd14",
            "name": "simple_move_robot.py",
            "parent": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
            "contentType": "application/hbp-neurorobotics.tfs+python",
            "type": "file",
            "modifiedOn": "2017-08-30T12:32:47.842214Z"
    },
        {
            "uuid": "6a63d03e-6dad-4793-80d7-8e32a83ddd13",
            "name": "resources",
            "parent": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
            "contentType": "application/hbp-neurorobotics.tfs+python",
            "type": "folder",
            "modifiedOn": "2017-08-30T12:32:47.842214Z"
    }], 200)


class TestStorageClient(unittest.TestCase):

    def setUp(self):
        self.experiments_directory = os.path.join(
            os.path.dirname(inspect.getfile(
                self.__class__)), 'experiment_files'
        )
        self.temporary_directory_to_clean = []

    def tearDown(self):
        for d in self.temporary_directory_to_clean:
            if d.startswith('/tmp'):
                shutil.rmtree(d)
        self.temporary_directory_to_clean = []

    # GET USER
    @patch('requests.get')
    def test_get_user_successfully(self, mocked_get):
        mocked_get.side_effect = mocked_get_user_ok
        client = StorageClient()
        res = client.get_user("faketoken")
        self.assertEqual(res, {"id": "fake_id"})

    @patch('requests.get')
    def test_get_user_not_ok(self, mocked_get):
        mocked_get.side_effect = mocked_request_not_ok

        client = StorageClient()
        with self.assertRaises(Exception) as context:
            client.get_user("wrong token")

        self.assertTrue(
            'Could not verify auth token, status code 404' in context.exception.args)

    @patch('requests.get')
    def test_get_user_connection_error(self, mocked_get):
        expected_exception_cls = ConnectionError
        mocked_get.side_effect = requests.exceptions.ConnectionError

        client = StorageClient()

        with self.assertRaises(expected_exception_cls):
            client.get_user("wrong token")

    # LIST EXPERIMENTS

    @patch('requests.get')
    def test_get_experiments_successfully(self, mocked_get):
        mocked_get.side_effect = mocked_get_experiments_ok

        client = StorageClient()

        res = client.list_experiments("fakeToken", 'ctx')

        self.assertEqual(res[0]['name'], "New Experiment_3")
        self.assertEqual(
            res[1]['uuid'], "b246cc8e-d844-4826-ae5b-d2c023b893d8")

    @patch('requests.get')
    def test_get_experiments_failed(self, mocked_get):
        mocked_get.side_effect = mocked_request_not_ok

        client = StorageClient()
        with self.assertRaises(Exception) as context:
            client.list_experiments("fakeToken", 'ctx')

        self.assertTrue(
            'Failed to communicate with the storage server, status code 404' in context.exception.args)

    @patch('requests.get')
    def test_get_experiment_connection_error(self, mocked_get):
        expected_exception_cls = ConnectionError
        mocked_get.side_effect = requests.exceptions.ConnectionError

        client = StorageClient()

        with self.assertRaises(expected_exception_cls):
            client.list_experiments("fakeToken", 'ctx')

    # GET FILE
    @patch('requests.get')
    def test_get_file_by_name_successfully(self, mocked_get):
        client = StorageClient()

        def get_fake_experiment_file(token, headers):
            with open(os.path.join(self.experiments_directory, "simulation_config.json"), 'rb') as conf_file:
                exp_file_contents = conf_file.read()
                return MockResponse(None, 200, content=exp_file_contents)

        mocked_get.side_effect = get_fake_experiment_file
        file = client.get_file(
            "fakeToken", "fakeExperiment", "simulation_config.json", by_name=True)

        parsed_conf = json.loads(file)
        self.assertEqual(parsed_conf["SimulationName"], "tf_exchange")

    @patch('requests.get')
    def test_get_zip_by_name_successfully(self, mocked_get):
        client = StorageClient()

        class Object(object):
            pass

        def get_fake_zip_file(token, headers):
            empty_binary_string = b''
            return MockResponse(None, 200, None, content=empty_binary_string)

        mocked_get.side_effect = get_fake_zip_file
        res = client.get_file(
            "fakeToken", "fakeExperiment", "fake.zip", by_name=True)
        self.assertIsInstance(res, bytes)

    @patch('requests.get')
    def test_get_file_name_successfully(self, mocked_get):
        client = StorageClient()

        def get_fake_experiment_file(token, headers):
            with open(os.path.join(self.experiments_directory, "simulation_config.json"), 'rb') as conf_file:
                exp_file_contents = conf_file.read()
                return MockResponse(None, 200, content=exp_file_contents)

        mocked_get.side_effect = get_fake_experiment_file
        file = client.get_file(
            "fakeToken", "fakeExperiment", "simulation_config.json")
        parsed_conf = json.loads(file)

        self.assertEqual(parsed_conf["SimulationTimeout"], 1)

    @patch('requests.get', side_effect=mocked_request_not_ok)
    def test_get_file_fail(self, mocked_put):
        client = StorageClient()
        with self.assertRaises(Exception) as context:
            client.get_file(
                "fakeToken", "fakeExperiment", "simulation_config.json")

        self.assertTrue(
            'Failed to communicate with the storage server, status code 404' in context.exception.args)

    @patch('requests.get')
    def test_get_file_connection_error(self, mocked_put):
        client = StorageClient()
        mocked_put.side_effect = requests.exceptions.ConnectionError
        with self.assertRaises(ConnectionError):
            client.get_file(
                "fakeToken", "fakeExperiment", "simulation_config.json")

    # DELETE FILE
    @patch('requests.delete', side_effect=mocked_delete_experiment_ok)
    def test_delete_file_successfully(self, mocked_delete):
        client = StorageClient()
        res = client.delete_file(
            "fakeToken", "fakeExperiment", "simulation_config.json")
        self.assertEqual(res, "simulation_config.json")

    @patch('requests.delete', side_effect=mocked_request_not_ok)
    def test_delete_file_failed(self, mocked_delete):
        client = StorageClient()
        with self.assertRaises(Exception) as context:
            client.delete_file(
                "fakeToken", "fakeExperiment", "simulation_config.json")

        self.assertTrue(
            'Failed to communicate with the storage server, status code 404' in context.exception.args)

    @patch('requests.delete')
    def test_delete_file_connection_error(self, mocked_put):
        client = StorageClient()
        mocked_put.side_effect = requests.exceptions.ConnectionError
        with self.assertRaises(ConnectionError):
            client.delete_file(
                "fakeToken", "fakeExperiment", "simulation_config.json")

    # CREATE OR UPDATE
    @patch('requests.post', side_effect=mocked_create_or_update_ok)
    def test_create_or_update_successfully(self, mocked_post):
        client = StorageClient()
        res = client.create_or_update(
            "fakeToken",
            "fakeExperiment",
            "simulation_config.json",
            "FakeContent",
            "text/plain")
        self.assertEqual(res, 200)

    @patch('requests.post', side_effect=mocked_request_not_ok)
    def test_create_or_update_failed(self, mocked_post):
        client = StorageClient()
        with self.assertRaises(Exception) as context:
            client.create_or_update(
                "fakeToken",
                "fakeExperiment",
                "simulation_config.json",
                "FakeContent",
                "text/plain")

        self.assertTrue(
            'Failed to communicate with the storage server, status code 404' in context.exception.args)

    @patch('requests.post')
    def test_create_or_update_connection_error(self, mocked_post):
        client = StorageClient()
        mocked_post.side_effect = requests.exceptions.ConnectionError
        with self.assertRaises(ConnectionError):
            client.create_or_update(
                "fakeToken",
                "fakeExperiment",
                "simulation_config.json",
                "FakeContent",
                "text/plain")

    # CREATE FOLDER
    @patch('requests.post', side_effect=mocked_create_folder_ok)
    def test_create_folder_successfully(self, mocked_post):
        client = StorageClient()
        res = client.create_folder(
            "fakeToken",
            "fakeExperiment",
            "fakeName")
        self.assertEqual(res['uuid'], '5b1a2363-1529-40cd-a8b7-94bfd6dea23d')
        self.assertEqual(res['name'], 'fakeFolder')

    @patch('requests.post', side_effect=mocked_request_not_ok)
    def test_create_folder_failed(self, mocked_post):
        client = StorageClient()
        with self.assertRaises(Exception) as context:
            res = client.create_folder(
                "fakeToken",
                "fakeExperiment",
                "fakeName")

        self.assertTrue(
            'Failed to communicate with the storage server, status code 404' in context.exception.args)

    @patch('requests.post')
    def test_create_folder_connection_error(self, mocked_post):
        client = StorageClient()
        mocked_post.side_effect = requests.exceptions.ConnectionError
        with self.assertRaises(ConnectionError):
            client.create_folder(
                "fakeToken",
                "fakeExperiment",
                "fakeName")

    # EXTRACT ZIP
    @patch('requests.post', side_effect=mocked_create_and_extract_zip_ok)
    def test_create_and_extract_zip_successfully(self, mocked_post):
        client = StorageClient()
        res = client.create_and_extract_zip(
            "fakeToken",
            "fakeExperiment",
            "fakeFile.zip",
            "FakeContent")
        self.assertEqual(res, 200)

    @patch('requests.post', side_effect=mocked_request_not_ok)
    def test_create_and_extract_zip_failed(self, mocked_post):
        client = StorageClient()
        with self.assertRaises(Exception) as context:
            client.create_and_extract_zip(
                "fakeToken",
                "fakeExperiment",
                "fakeFile.zip",
                "FakeContent")
        self.assertTrue(
            'Failed to communicate with the storage server, status code 404' in context.exception.args)

    @patch('requests.post')
    def test_create_and_extract_zip_connection_error(self, mocked_post):
        client = StorageClient()
        mocked_post.side_effect = requests.exceptions.ConnectionError
        with self.assertRaises(ConnectionError):
            client.create_and_extract_zip(
                "fakeToken",
                "fakeExperiment",
                "fakeFile.zip",
                "FakeContent")

    # LIST FILES

    @patch('requests.get', side_effect=mocked_get_files_list_ok)
    def test_get_files_list_successfully(self, mocked_post):
        client = StorageClient()
        res = client.get_files_list(
            "fakeToken",
            "fakeExperiment")
        self.assertEqual(
            res[0]['uuid'], '07b35b8f-67cd-4e94-8bec-5ede8049590d')
        self.assertEqual(res[1]['name'], 'simple_move_robot.py')

    @patch('requests.get', side_effect=mocked_request_not_ok)
    def test_get_files_list_failed(self, mocked_post):
        client = StorageClient()
        with self.assertRaises(Exception) as context:
            client.get_files_list(
                "fakeToken",
                "fakeExperiment")

        self.assertTrue(
            'Failed to communicate with the storage server, status code 404' in context.exception.args)

    @patch('requests.get')
    def test_get_files_list_connection_error(self, mocked_post):
        client = StorageClient()
        mocked_post.side_effect = requests.exceptions.ConnectionError
        with self.assertRaises(ConnectionError):
            client.get_files_list(
                "fakeToken",
                "fakeExperiment")

    # CLONE FILE
    @patch('hbp_nrp_backend.storage_client_api.storage_client.StorageClient.get_files_list')
    def test_clone_does_not_exist(self, mocked_list):
        client = StorageClient()
        mocked_list.return_value = [{
            "uuid": "07b35b8f-67cd-4e94-8bec-5ede8049590d",
            "name": "env_editor.autosaved",
            "parent": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
            "contentType": "text/plain",
            "type": "file",
            "modifiedOn": "2017-08-31T13:56:34.306090Z"
        },
            {
                "uuid": "6a63d03e-6dad-4793-80d7-8e32a83ddd14",
                "name": "simple_move_robot.py",
                "parent": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
                "contentType": "application/hbp-neurorobotics.tfs+python",
                "type": "file",
                "modifiedOn": "2017-08-30T12:32:47.842214Z"
        }]
        res = client.clone_file("fakeToken",
                                "fakeFile",
                                "fakeExperiment")
        self.assertEqual(res, None)

    # CLONE ALL EXPERIMENT FILES
    @patch('hbp_nrp_backend.storage_client_api.storage_client.StorageClient.get_files_list')
    @patch('hbp_nrp_backend.storage_client_api.storage_client.StorageClient.get_file')
    def test_clone_all_experiment_files(self, mocked_get, mocked_list):
        mocked_get.side_effect = None

        experiment_name = "fakeExperiment"

        env_editor_name = "env_editor.autosaved"
        exp_conf_name = 'simulation_config.json'
        simple_robot_name = 'simple_move_robot.py'

        tfs_dir_name = 'transfer_functions'
        tfs_dir_uuid = "6a63d03e-6dad-4793-80d7-8e32a83aaa66"

        mock_experiment_dir_list = [
            {
                "uuid": "07b35b8f-67cd-4e94-8bec-5ede8049590d",
                "name": env_editor_name,
                "parent": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
                "contentType": "text/plain",
                "type": "file",
                "modifiedOn": "2017-08-31T13:56:34.306090Z"
            },
            {
                "uuid": "6a63d03e-6dad-4793-80d7-8e32a83eee78",
                "name": exp_conf_name,
                "parent": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
                "contentType": "text/plain",
                "type": "file",
                "modifiedOn": "2017-08-30T11:23:47.842214Z"
            },
            {
                "uuid": tfs_dir_uuid,
                "name": tfs_dir_name,
                "parent": "3ce08569-bdb7-49ee-a751-5640f4b879d4",
                "contentType": "application/hbp-neurorobotics.tfs+python",
                "type": "folder",
                "modifiedOn": "2017-08-30T12:32:47.842214Z"
            }
        ]

        # transfer_functions/simple_move_robot.py
        mock_tfs_dir_list = [{
            "uuid": "6a63d03e-6dad-4793-80d7-8e32a83ddd14",
            "name": simple_robot_name,
            "parent": "6a63d03e-6dad-4793-80d7-8e32a83aaa66",
            "contentType": "application/hbp-neurorobotics.tfs+python",
            "type": "file",
            "modifiedOn": "2017-08-30T12:32:47.842214Z"
        }
        ]

        def mocked_list_fun(_token, experiment, folder):
            if experiment == experiment_name:
                return mock_experiment_dir_list
            elif experiment == tfs_dir_uuid:
                return mock_tfs_dir_list
            return []

        mocked_list.side_effect = mocked_list_fun

        client = StorageClient()

        with patch("builtins.open", mock_open(read_data="data")) as mocked_open, \
                patch('hbp_nrp_backend.storage_client_api.storage_client.SimUtil') as mocked_sim_util:
            sim_dir = '/some/path/over/the/rainbow'
            client.clone_all_experiment_files(
                "fakeToken", experiment_name, destination_dir=sim_dir)

            mocked_open.assert_any_call(
                os.path.join(sim_dir, env_editor_name), 'wb')
            mocked_open.assert_any_call(
                os.path.join(sim_dir, exp_conf_name), 'wb')
            mocked_open.assert_any_call(os.path.join(
                sim_dir, tfs_dir_name, simple_robot_name), 'wb')

    @patch('hbp_nrp_backend.storage_client_api.storage_client.StorageClient.list_experiments')
    def test_get_folder_uuid_by_name_ok(self, mocked_get):
        mocked_get.return_value = [{"name": 'Experiment_0', "uuid": "Experiment_0_uuid"}, {
            "name": 'Experiment_1', "uuid": "Experiment_1_uuid"}]
        client = StorageClient()
        uuid = client.get_folder_uuid_by_name(
            'fakeToken', 'fake_context_id', 'Experiment_0')
        self.assertEqual(uuid, 'Experiment_0_uuid')
        mocked_get.assert_called_with(
            'fakeToken', 'fake_context_id', name='Experiment_0', get_all=True)

    def test_check_file_extension(self):
        example1 = [{u'uiid': u'/test_folder/simulation_config.json', u'name': u'simulation_config.json'},
                    {u'uiid': u'/test_folder/.simulation_config.json.swp', u'name': u'.simulation_config.json.swp'}]
        client = StorageClient()

        for i, ext in enumerate(['.json', '.swp']):
            self.assertTrue(client.check_file_extension(
                example1[i]['name'], [ext]))

        for i, ext in enumerate(['.swp', '.txt']):
            self.assertFalse(client.check_file_extension(
                example1[i]['name'], [ext]))


if __name__ == '__main__':
    unittest.main()
