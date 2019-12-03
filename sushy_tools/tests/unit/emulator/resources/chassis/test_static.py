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
import uuid

from oslotest import base

from sushy_tools.emulator.resources.chassis.staticdriver import StaticDriver
from sushy_tools import error


class StaticDriverTestCase(base.BaseTestCase):

    def setUp(self):
        self.chassis = [
            {
                "Id": "Chassis",
                "Name": "Tinfoil Chassis",
                "UUID": "48295861-2522-3561-6729-621118518810",
                "Contains": ['48295861-2522-3561-6729-621118518810'],
                "ContainedBy": 'ZZZ-YYY-XXX'
            }
        ]

        self.identity = self.chassis[0]['Id']
        self.uuid = self.chassis[0]['UUID']
        self.name = self.chassis[0]['Name']

        self.sys_name = 'server01'
        self.sys_uuid = self.uuid.replace('8', '1')

        self.mgr_name = 'manager01'
        self.mgr_uuid = self.uuid.replace('8', '2')

        test_driver = StaticDriver.initialize(
            {'SUSHY_EMULATOR_CHASSIS': self.chassis},
            mock.MagicMock())

        self.test_driver = test_driver()

        systems_mock = mock.MagicMock()
        systems_mock.name.return_value = self.sys_name
        systems_mock.uuid.return_value = self.sys_uuid
        systems_mock.systems = [self.sys_name]

        self.test_driver.systems = systems_mock

        managers_mock = mock.MagicMock()
        managers_mock.name.return_value = self.mgr_name
        managers_mock.uuid.return_value = self.mgr_uuid
        managers_mock.managers = [self.mgr_name]

        self.test_driver.managers = managers_mock

        super(StaticDriverTestCase, self).setUp()

    def test__get_chassis_by_id(self):
        self.assertRaises(
            error.AliasAccessError, self.test_driver._get_chassis,
            self.identity)

    def test__get_chassis_by_name(self):
        self.assertRaises(
            error.AliasAccessError, self.test_driver._get_chassis, self.name)

    def test__get_chassis_by_uuid(self):
        chassis_uuid = uuid.UUID(self.uuid)
        chassis = self.test_driver._get_chassis(str(chassis_uuid))
        self.assertEqual(
            self.chassis[0], chassis)

    def test_uuid_ok(self):
        self.assertEqual(self.uuid, self.test_driver.uuid(self.uuid))

    def test_uuid_fail(self):
        self.assertRaises(error.FishyError, self.test_driver.uuid, 'xxx')

    def test_name_ok(self):
        self.assertRaises(error.AliasAccessError,
                          self.test_driver.name, self.name)

    def test_name_fail(self):
        self.assertRaises(error.FishyError, self.test_driver.name, 'xxx')

    def test_chassis(self):
        chassis = self.test_driver.chassis
        self.assertEqual([self.uuid], chassis)
