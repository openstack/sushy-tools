# Copyright 2019 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

from oslotest import base

from sushy_tools.emulator.resources import managers
from sushy_tools import error


class FakeDriverTestCase(base.BaseTestCase):

    def setUp(self):
        super(FakeDriverTestCase, self).setUp()
        self.identity = 'xxx'
        self.systems = mock.Mock(systems=[self.identity])
        self.systems.uuid.return_value = 'xxx'
        self.systems.name.return_value = 'name'
        self.manager = {'UUID': self.identity,
                        'Id': self.identity,
                        'Name': 'name-Manager'}
        self.chassis = mock.Mock(chassis=[])
        self.test_driver = managers.FakeDriver({}, mock.Mock(),
                                               self.systems, self.chassis)

        self.datetime_value = "2025-06-11T12:00:00+00:00"
        self.datetimelocaloffset_value = "+00:00"

    def test_get_manager_not_found(self):
        self.systems.uuid.side_effect = error.FishyError('boom')
        self.assertRaises(
            error.FishyError, self.test_driver.get_manager, 'foo')

    def test_get_manager_by_uuid(self):
        manager = self.test_driver.get_manager('xxx')
        self.assertEqual(self.manager, manager)

    def test_managers(self):
        result = self.test_driver.managers
        self.assertEqual([self.identity], result)

    def test_managed_systems(self):
        self.assertEqual(
            ['xxx'], self.test_driver.get_managed_systems(self.manager))

    def test_set_datetime(self):
        self.test_driver.set_datetime(self.datetime_value,
                                      self.datetimelocaloffset_value)
        self.assertEqual(self.test_driver._datetime, self.datetime_value)
        self.assertEqual(self.test_driver._datetimelocaloffset,
                         self.datetimelocaloffset_value)

    def test_get_datetime_returns_expected_dict(self):
        self.test_driver.set_datetime(self.datetime_value,
                                      self.datetimelocaloffset_value)
        result = self.test_driver.get_datetime()
        expected = {
            "DateTime": self.datetime_value,
            "DateTimeLocalOffset": self.datetimelocaloffset_value
        }
        self.assertEqual(result, expected)

    def test_get_datetime_returns_empty_dict_when_not_set(self):
        result = self.test_driver.get_datetime()
        self.assertEqual(result, {})
