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

__author__ = 'NRP software team'

import typing
from unittest import mock


def _get_properties(klass: typing.Type) -> typing.List[str]:
    """Returns a list of property names belonging to klass"""
    return [p for p in dir(klass) if issubclass(property, getattr(klass, p).__class__)]


def mock_properties(klass: typing.Type, addCleanup: typing.Optional[typing.Callable] = None):
    """
    Mocks the properties of a class returning a pair of dictionaries (patchers, mocks) indexed by the property name
    If addCleanup is provided, for each property, patcher.stop is added to the clean up list.
    :return: A pair of dictionaries (patchers, mocks) indexed by the property name
    """
    property_patchers: typing.Dict[str, typing.Any] = {}
    property_mocks: typing.Dict[str, mock.PropertyMock] = {}

    for p in _get_properties(klass):
        patcher = mock.patch.object(klass, p, new_callable=mock.PropertyMock)
        property_patchers[p] = patcher
        property_mocks[p] = patcher.start()
        if addCleanup:
            addCleanup(patcher.stop)

    return property_patchers, property_mocks
