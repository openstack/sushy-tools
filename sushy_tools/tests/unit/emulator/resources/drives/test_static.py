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

from oslotest import base
from six.moves import mock

from sushy_tools.emulator.resources.drives.staticdriver import StaticDriver


class StaticDriverTestCase(base.BaseTestCase):
    SYSTEM_UUID = "da69abcc-dae0-4913-9a7b-d344043097c0"
    STORAGE_ID = "1"
    DRIVE_COL = [
        {
            "Id": "32ADF365C6C1B7BD",
            "Name": "Drive Sample",
            "CapacityBytes": 899527000000,
            "Protocol": "SAS"
        },
        {
            "Id": "58CFF987G8J2V9KL",
            "Name": "Drive2",
            "CapacityBytes": 12345670000,
            "Protocol": "SATA"
        }
    ]

    CONFIG = {
        'SUSHY_EMULATOR_DRIVES': {
            (SYSTEM_UUID, STORAGE_ID): DRIVE_COL
        }
    }

    def test_get_drives(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()
        drv_col = test_driver.get_drives(self.SYSTEM_UUID, self.STORAGE_ID)
        self.assertEqual(self.DRIVE_COL, drv_col)

    def test_get_all_drives(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()
        drives = test_driver.get_all_drives()
        self.assertEqual({('da69abcc-dae0-4913-9a7b-d344043097c0', '1',
                           '32ADF365C6C1B7BD'),
                          ('da69abcc-dae0-4913-9a7b-d344043097c0', '1',
                           '58CFF987G8J2V9KL')}, set(drives))
