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

from sushy_tools.emulator.resources.volumes import StaticDriver


@mock.patch('sushy_tools.emulator.resources.volumes.memoize.PersistentDict',
            new=dict)
class StaticDriverTestCase(base.BaseTestCase):

    SYSTEM_UUID = "da69abcc-dae0-4913-9a7b-d344043097c0"
    STORAGE_ID = "1"
    VOLUMES_COL = [
        {
            "libvirtPoolName": "sushyPool",
            "libvirtVolName": "testVol",
            "Id": "1",
            "Name": "Sample Volume 1",
            "VolumeType": "Mirrored",
            "CapacityBytes": 23748
        },
        {
            "libvirtPoolName": "sushyPool",
            "libvirtVolName": "testVol1",
            "Id": "2",
            "Name": "Sample Volume 2",
            "VolumeType": "StripedWithParity",
            "CapacityBytes": 48395
        }
    ]

    CONFIG = {
        'SUSHY_EMULATOR_VOLUMES': {
            (SYSTEM_UUID, STORAGE_ID): VOLUMES_COL
        }
    }

    def setUp(self):
        super().setUp()
        self.test_driver = StaticDriver(self.CONFIG, mock.MagicMock())

    def test_get_volumes_col(self):
        vol_col = self.test_driver.get_volumes_col(self.SYSTEM_UUID,
                                                   self.STORAGE_ID)
        self.assertEqual(self.VOLUMES_COL, vol_col)

    def test_add_volume(self):
        vol = {
            "libvirtPoolName": "sushyPool",
            "libvirtVolName": "testVol2",
            "Id": "3",
            "Name": "Sample Volume 3",
            "VolumeType": "Mirrored",
            "CapacityBytes": 76584
        }
        self.test_driver.add_volume(self.SYSTEM_UUID, self.STORAGE_ID, vol)
        vol_col = self.test_driver.get_volumes_col(self.SYSTEM_UUID,
                                                   self.STORAGE_ID)
        self.assertTrue(vol in vol_col)

    def test_delete_volume(self):
        vol = {
            "libvirtPoolName": "sushyPool",
            "libvirtVolName": "testVol",
            "Id": "1",
            "Name": "Sample Volume 1",
            "VolumeType": "Mirrored",
            "CapacityBytes": 23748
        }
        self.test_driver.delete_volume(self.SYSTEM_UUID, self.STORAGE_ID, vol)
        vol_col = self.test_driver.get_volumes_col(self.SYSTEM_UUID,
                                                   self.STORAGE_ID)
        self.assertFalse(vol in vol_col)
