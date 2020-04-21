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

from sushy_tools.emulator.resources.storage.staticdriver import StaticDriver


class StaticDriverTestCase(base.BaseTestCase):
    UUID = "da69abcc-dae0-4913-9a7b-d344043097c0"
    STORAGE_COL = [
        {
            "Id": "1",
            "Name": "Local Storage Controller",
            "StorageControllers": [
                {
                    "MemberId": "0",
                    "Name": "Contoso Integrated RAID",
                    "SpeedGbps": 12
                }
            ]
        }
    ]

    CONFIG = {
        'SUSHY_EMULATOR_STORAGE': {
            UUID: STORAGE_COL
        }
    }

    def test_get_storage_col(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()
        stg_col = test_driver.get_storage_col(self.UUID)
        self.assertEqual(self.STORAGE_COL, stg_col)

    def test_get_all_storage(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()
        stg = test_driver.get_all_storage()
        self.assertEqual([(self.UUID, '1')], stg)
