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

from sushy_tools.emulator.resources.vmedia.staticdriver import StaticDriver


@mock.patch('sushy_tools.emulator.memoize.PersistentDict', new=dict)
class StaticDriverTestCase(base.BaseTestCase):

    UUID = 'ZZZ-YYY-XXX'

    CONFIG = {
        'SUSHY_EMULATOR_VMEDIA_DEVICES': {
            "Cd": {
                "Name": "Virtual CD",
                "MediaTypes": [
                    "CD",
                    "DVD"
                ]
            },
            "Floppy": {
                "Name": "Virtual Removable Media",
                "MediaTypes": [
                    "Floppy",
                    "USBStick"
                ]
            }
        }
    }

    def test_devices(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()

        devices = test_driver.devices
        self.assertEqual(['Cd', 'Floppy'], sorted(devices))

    def test_get_device_name(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()

        device_name = test_driver.get_device_name(
            self.UUID, 'Cd')
        self.assertEqual('Virtual CD', device_name)

    def test_get_device_media_types(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()

        media_types = test_driver.get_device_media_types(
            self.UUID, 'Cd')
        self.assertEqual(['CD', 'DVD'], media_types)

    def test_get_device_image_info(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()

        dev_info = test_driver.get_device_image_info(
            self.UUID, 'Cd')
        expected = ('', '', False, False)
        self.assertEqual(expected, dev_info)

    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.StaticDriver._get_device',
                autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.open')
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.os.rename', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.tempfile', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.requests', autospec=True)
    def test_insert_image(self, mock_requests, mock_tempfile, mock_rename,
                          mock_open, mock_get_device):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()

        device_info = {}
        mock_get_device.return_value = device_info

        mock_tempfile.mkdtemp.return_value = '/alphabet/soup'
        mock_tempfile.gettempdir.return_value = '/tmp'
        mock_tmp_file = (mock_tempfile.NamedTemporaryFile
                         .return_value.__enter__.return_value)
        mock_tmp_file.name = 'alphabet.soup'
        mock_rsp = mock_requests.get.return_value.__enter__.return_value
        mock_rsp.headers = {
            'content-disposition': 'attachment; filename="fish.iso"'
        }

        local_file = test_driver.insert_image(
            self.UUID, 'Cd', 'http://fish.it/red.iso', inserted=True,
            write_protected=False)

        self.assertEqual('/alphabet/soup/fish.iso', local_file)
        mock_requests.get.assert_called_once_with(
            'http://fish.it/red.iso', stream=True)
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/fish.iso')

        self.assertEqual('fish.iso', device_info['Image'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])

    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.StaticDriver._get_device',
                autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.open')
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.os.rename', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.tempfile', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.requests', autospec=True)
    def test_insert_image_no_local_file(self, mock_requests, mock_tempfile,
                                        mock_rename, mock_open,
                                        mock_get_device):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()

        device_info = {}
        mock_get_device.return_value = device_info

        mock_tempfile.mkdtemp.return_value = '/alphabet/soup'
        mock_tempfile.gettempdir.return_value = '/tmp'
        mock_tmp_file = (mock_tempfile.NamedTemporaryFile
                         .return_value.__enter__.return_value)
        mock_tmp_file.name = 'alphabet.soup'
        mock_rsp = mock_requests.get.return_value.__enter__.return_value
        mock_rsp.headers = {}

        local_file = test_driver.insert_image(
            self.UUID, 'Cd', 'http://fish.it/red.iso', inserted=True,
            write_protected=False)

        self.assertEqual('/alphabet/soup/red.iso', local_file)
        mock_requests.get.assert_called_once_with(
            'http://fish.it/red.iso', stream=True)
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/red.iso')

        self.assertEqual('red.iso', device_info['Image'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])

    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.StaticDriver._get_device',
                autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.open')
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.os.rename', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.tempfile', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.requests', autospec=True)
    def test_insert_image_full_url_v6(self, mock_requests, mock_tempfile,
                                      mock_rename, mock_open,
                                      mock_get_device):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()

        device_info = {}
        mock_get_device.return_value = device_info

        mock_tempfile.mkdtemp.return_value = '/alphabet/soup'
        mock_tempfile.gettempdir.return_value = '/tmp'
        mock_tmp_file = (mock_tempfile.NamedTemporaryFile
                         .return_value.__enter__.return_value)
        mock_tmp_file.name = 'alphabet.soup'
        mock_rsp = mock_requests.get.return_value.__enter__.return_value
        mock_rsp.headers = {}

        full_url = 'http://[::2]:80/redfish/boot-abc?filename=tmp.iso'
        local_file = test_driver.insert_image(
            self.UUID, 'Cd', full_url,
            inserted=True, write_protected=False)

        self.assertEqual('/alphabet/soup/boot-abc', local_file)
        mock_requests.get.assert_called_once_with(full_url, stream=True)
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/boot-abc')

        self.assertEqual('boot-abc', device_info['Image'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])

    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.StaticDriver._get_device',
                autospec=True)
    @mock.patch('sushy_tools.emulator.resources.vmedia'
                '.staticdriver.os.unlink', autospec=True)
    def test_eject_image(self, mock_unlink, mock_get_device):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()

        device_info = {
            '_local_file': '/tmp/fish.iso'
        }
        mock_get_device.return_value = device_info

        test_driver.eject_image(self.UUID, 'Cd')

        self.assertEqual('', device_info['Image'])
        self.assertEqual('', device_info['ImageName'])
        self.assertFalse(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])

        mock_unlink.assert_called_once_with('/tmp/fish.iso')
