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
Unit tests for the sim config model
"""

import unittest
import os
from unittest.mock import patch, MagicMock

from hbp_nrp_commons.workspace.sim_util import SimUtil

__author__ = 'NRP software team, Hossain Mahmud'

_base_path = 'hbp_nrp_commons.workspace.sim_util'


@patch(f'{_base_path}.logging', new=MagicMock())
class TestSimConfig(unittest.TestCase):
    def setUp(self):
        # mock os
        os_patcher = patch(f'{_base_path}.os')
        self.os_mock = os_patcher.start()
        self.addCleanup(os_patcher.stop)
        # restore os.path.join and os.path.dirname
        self.os_mock.path.join = os.path.join
        self.os_mock.path.dirname = os.path.dirname

        # Settings
        settings_patcher = patch(f'{_base_path}.Settings')
        self.settings_mock = settings_patcher.start()
        self.addCleanup(settings_patcher.stop)

        # shutil
        shutil_patcher = patch(f'{_base_path}.shutil')
        self.shutil_mock = shutil_patcher.start()
        self.addCleanup(shutil_patcher.stop)

        # tempfile
        tempfile_patcher = patch(f'{_base_path}.tempfile')
        self.tempfile_mock = tempfile_patcher.start()
        self.addCleanup(tempfile_patcher.stop)

    def tearDown(self):
        pass

    def test_makedirs(self):
        SimUtil.makedirs('dir/name')
        self.os_mock.makedirs.assert_called_once_with('dir/name')

        self.os_mock.makedirs.side_effect = Exception
        self.assertRaises(Exception, SimUtil.makedirs, 'dir/name')

    def test_clear_dir(self):
        self.os_mock.path.realpath.return_value = '/actual/path'
        SimUtil.clear_dir('/dir/to/clear')
        self.os_mock.path.realpath.assert_called_once_with('/dir/to/clear')
        self.shutil_mock.rmtree.assert_called_once_with('/actual/path')
        self.os_mock.makedirs.assert_called_once_with('/dir/to/clear')

    def test_find_file_in_paths_ok(self):
        self.os_mock.path.isfile.return_value = True
        path = SimUtil.find_file_in_paths('test.txt', ['path1'])
        self.assertEqual(path, 'path1/test.txt')

    def test_init_simulation_dir(self):
        SimUtil.init_simulation_dir(1)
        self.tempfile_mock.mkdtemp.assert_called_once()
        self.os_mock.symlink.assert_called_once()

    def test_delete_simulation_dir(self):
        self.os_mock.path.exists.return_value = True
        SimUtil.delete_simulation_dir()
        self.shutil_mock.rmtree.assert_called_once()
        self.os_mock.unlink.assert_called_once()


if __name__ == '__main__':
    unittest.main()
