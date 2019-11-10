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
import uuid

from oslotest import base
from six.moves import mock

from sushy_tools.emulator.resources.managers.staticdriver import StaticDriver
from sushy_tools import error


class StaticDriverTestCase(base.BaseTestCase):

    def setUp(self):
        self.managers = [
            {
                "Id": "BMC",
                "Name": "The manager",
                "UUID": "58893887-8974-2487-2389-841168418919",
                "ServiceEntryPointUUID": "92384634-2938-2342-8820-489239905423"
            }
        ]

        self.identity = self.managers[0]['Id']
        self.uuid = self.managers[0]['UUID']
        self.name = self.managers[0]['Name']

        test_driver = StaticDriver.initialize(
            {'SUSHY_EMULATOR_MANAGERS': self.managers},
            mock.MagicMock())

        self.test_driver = test_driver()

        super(StaticDriverTestCase, self).setUp()

    def test__get_manager_by_id(self):
        self.assertRaises(
            error.AliasAccessError, self.test_driver._get_manager,
            self.identity)

    def test__get_manager_by_name(self):
        self.assertRaises(
            error.AliasAccessError, self.test_driver._get_manager, self.name)

    def test__get_manager_by_uuid(self):
        domain_id = uuid.UUID(self.uuid)
        manager = self.test_driver._get_manager(str(domain_id))
        self.assertEqual(
            self.managers[0], manager)

    def test_uuid_ok(self):
        self.assertEqual(self.uuid, self.test_driver.uuid(self.uuid))

    def test_uuid_fail(self):
        self.assertRaises(error.FishyError, self.test_driver.uuid, 'xxx')

    def test_name_ok(self):
        self.assertRaises(error.AliasAccessError,
                          self.test_driver.name, self.name)

    def test_name_fail(self):
        self.assertRaises(error.FishyError, self.test_driver.name, 'xxx')

    def test_managers(self):
        managers = self.test_driver.managers
        self.assertEqual([self.uuid], managers)
