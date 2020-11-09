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
