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

import builtins
from unittest import mock

from oslotest import base

from sushy_tools.emulator.resources import vmedia
from sushy_tools import error


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

    def setUp(self):
        super().setUp()
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            self.test_driver = vmedia.StaticDriver(self.CONFIG,
                                                   mock.MagicMock())

    def test_devices(self):
        devices = self.test_driver.devices
        self.assertEqual(['Cd', 'Floppy'], sorted(devices))

    def test_get_device_name(self):
        device_name = self.test_driver.get_device_name(
            self.UUID, 'Cd')
        self.assertEqual('Virtual CD', device_name)

    def test_get_device_media_types(self):
        media_types = self.test_driver.get_device_media_types(
            self.UUID, 'Cd')
        self.assertEqual(['CD', 'DVD'], media_types)

    def test_get_device_image_info(self):
        dev_info = self.test_driver.get_device_image_info(
            self.UUID, 'Cd')
        expected = ('', '', False, False, '', '', False)
        self.assertEqual(expected, dev_info)

    def test_update_device_info(self):
        dev_info = self.test_driver.get_device_image_info(self.UUID, 'Cd')
        self.assertFalse(dev_info.verify)

        self.test_driver.update_device_info(self.UUID, 'Cd', verify=True)
        dev_info = self.test_driver.get_device_image_info(self.UUID, 'Cd')
        self.assertTrue(dev_info.verify)

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(builtins, 'open', autospec=True)
    @mock.patch.object(vmedia.os, 'rename', autospec=True)
    @mock.patch.object(vmedia, 'tempfile', autospec=True)
    @mock.patch.object(vmedia, 'requests', autospec=True)
    def test_insert_image(self, mock_requests, mock_tempfile, mock_rename,
                          mock_open, mock_get_device):
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
        mock_rsp.status_code = 200

        local_file = self.test_driver.insert_image(
            self.UUID, 'Cd', 'http://fish.it/red.iso', inserted=True,
            write_protected=False)

        self.assertEqual('/alphabet/soup/fish.iso', local_file)
        mock_requests.get.assert_called_once_with(
            'http://fish.it/red.iso', stream=True, verify=False, auth=None)
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/fish.iso')

        self.assertEqual('http://fish.it/red.iso', device_info['Image'])
        self.assertEqual('fish.iso', device_info['ImageName'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])
        self.assertEqual('', device_info['UserName'])
        self.assertEqual('', device_info['Password'])
        self.assertEqual(local_file, device_info['_local_file'])

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(builtins, 'open', autospec=True)
    @mock.patch.object(vmedia.os, 'rename', autospec=True)
    @mock.patch.object(vmedia, 'tempfile', autospec=True)
    @mock.patch.object(vmedia, 'requests', autospec=True)
    def test_insert_image_auth(self, mock_requests, mock_tempfile, mock_rename,
                               mock_open, mock_get_device):
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
        mock_rsp.status_code = 200

        local_file = self.test_driver.insert_image(
            self.UUID, 'Cd', 'http://fish.it/red.iso', inserted=True,
            write_protected=False, username='Admin', password='Secret')

        self.assertEqual('/alphabet/soup/fish.iso', local_file)
        mock_requests.get.assert_called_once_with(
            'http://fish.it/red.iso', stream=True, verify=False,
            auth=('Admin', 'Secret'))
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/fish.iso')

        self.assertEqual('http://fish.it/red.iso', device_info['Image'])
        self.assertEqual('fish.iso', device_info['ImageName'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])
        self.assertEqual('Admin', device_info['UserName'])
        self.assertEqual('Secret', device_info['Password'])
        self.assertEqual(local_file, device_info['_local_file'])

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(builtins, 'open', autospec=True)
    @mock.patch.object(vmedia.os, 'rename', autospec=True)
    @mock.patch.object(vmedia, 'tempfile', autospec=True)
    @mock.patch.object(vmedia, 'requests', autospec=True)
    def test_insert_image_no_local_file(self, mock_requests, mock_tempfile,
                                        mock_rename, mock_open,
                                        mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        mock_tempfile.mkdtemp.return_value = '/alphabet/soup'
        mock_tempfile.gettempdir.return_value = '/tmp'
        mock_tmp_file = (mock_tempfile.NamedTemporaryFile
                         .return_value.__enter__.return_value)
        mock_tmp_file.name = 'alphabet.soup'
        mock_rsp = mock_requests.get.return_value.__enter__.return_value
        mock_rsp.headers = {}
        mock_rsp.status_code = 200

        local_file = self.test_driver.insert_image(
            self.UUID, 'Cd', 'http://fish.it/red.iso', inserted=True,
            write_protected=False)

        self.assertEqual('/alphabet/soup/red.iso', local_file)
        mock_requests.get.assert_called_once_with(
            'http://fish.it/red.iso', stream=True, verify=False, auth=None)
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/red.iso')

        self.assertEqual('http://fish.it/red.iso', device_info['Image'])
        self.assertEqual('red.iso', device_info['ImageName'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(builtins, 'open', autospec=True)
    @mock.patch.object(vmedia.os, 'rename', autospec=True)
    @mock.patch.object(vmedia, 'tempfile', autospec=True)
    @mock.patch.object(vmedia, 'requests', autospec=True)
    def test_insert_image_full_url_v6(self, mock_requests, mock_tempfile,
                                      mock_rename, mock_open,
                                      mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        mock_tempfile.mkdtemp.return_value = '/alphabet/soup'
        mock_tempfile.gettempdir.return_value = '/tmp'
        mock_tmp_file = (mock_tempfile.NamedTemporaryFile
                         .return_value.__enter__.return_value)
        mock_tmp_file.name = 'alphabet.soup'
        mock_rsp = mock_requests.get.return_value.__enter__.return_value
        mock_rsp.headers = {}
        mock_rsp.status_code = 200

        full_url = 'http://[::2]:80/redfish/boot-abc?filename=tmp.iso'
        local_file = self.test_driver.insert_image(
            self.UUID, 'Cd', full_url,
            inserted=True, write_protected=False)

        self.assertEqual('/alphabet/soup/boot-abc', local_file)
        mock_requests.get.assert_called_once_with(full_url, stream=True,
                                                  verify=False, auth=None)
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/boot-abc')

        self.assertEqual(full_url, device_info['Image'])
        self.assertEqual('boot-abc', device_info['ImageName'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(builtins, 'open', autospec=True)
    @mock.patch.object(vmedia.os, 'rename', autospec=True)
    @mock.patch.object(vmedia, 'tempfile', autospec=True)
    @mock.patch.object(vmedia, 'requests', autospec=True)
    def test_insert_image_verify_ssl(self, mock_requests, mock_tempfile,
                                     mock_rename, mock_open,
                                     mock_get_device):
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
        mock_rsp.status_code = 200

        ssl_conf_key = 'SUSHY_EMULATOR_VMEDIA_VERIFY_SSL'
        default_ssl_verify = self.test_driver._config.get(ssl_conf_key)
        try:
            self.test_driver._config[ssl_conf_key] = True
            local_file = self.test_driver.insert_image(
                self.UUID, 'Cd', 'https://fish.it/red.iso', inserted=True,
                write_protected=False)
        finally:
            self.test_driver._config[ssl_conf_key] = default_ssl_verify

        self.assertEqual('/alphabet/soup/fish.iso', local_file)
        mock_requests.get.assert_called_once_with(
            'https://fish.it/red.iso', stream=True, auth=None, verify=True)
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/fish.iso')

        self.assertEqual('https://fish.it/red.iso', device_info['Image'])
        self.assertEqual('fish.iso', device_info['ImageName'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])
        self.assertEqual(local_file, device_info['_local_file'])

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(builtins, 'open', autospec=True)
    @mock.patch.object(vmedia.os, 'rename', autospec=True)
    @mock.patch.object(vmedia, 'tempfile', autospec=True)
    @mock.patch.object(vmedia, 'requests', autospec=True)
    def test_insert_image_verify_ssl_changed(self, mock_requests,
                                             mock_tempfile,
                                             mock_rename, mock_open,
                                             mock_get_device):
        device_info = {'Verify': True}
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
        mock_rsp.status_code = 200

        local_file = self.test_driver.insert_image(
            self.UUID, 'Cd', 'https://fish.it/red.iso', inserted=True,
            write_protected=False)

        self.assertEqual('/alphabet/soup/fish.iso', local_file)
        mock_requests.get.assert_called_once_with(
            'https://fish.it/red.iso', stream=True, auth=None, verify=True)
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/fish.iso')

        self.assertEqual('https://fish.it/red.iso', device_info['Image'])
        self.assertEqual('fish.iso', device_info['ImageName'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])
        self.assertEqual(local_file, device_info['_local_file'])

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(builtins, 'open', autospec=True)
    @mock.patch.object(vmedia.os, 'rename', autospec=True)
    @mock.patch.object(vmedia, 'tempfile', autospec=True)
    @mock.patch.object(vmedia, 'requests', autospec=True)
    def test_insert_image_verify_ssl_custom(self, mock_requests,
                                            mock_tempfile,
                                            mock_rename, mock_open,
                                            mock_get_device):
        device_info = {'Verify': True,
                       'Certificate': {'String': 'abcd'}}
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
        mock_rsp.status_code = 200

        local_file = self.test_driver.insert_image(
            self.UUID, 'Cd', 'https://fish.it/red.iso', inserted=True,
            write_protected=False)

        self.assertEqual('/alphabet/soup/fish.iso', local_file)
        mock_requests.get.assert_called_once_with(
            'https://fish.it/red.iso', stream=True,
            verify=mock_tempfile.NamedTemporaryFile.return_value.name,
            auth=None)
        mock_open.assert_called_once_with(mock.ANY, 'wb')
        mock_rename.assert_called_once_with(
            'alphabet.soup', '/alphabet/soup/fish.iso')

        self.assertEqual('https://fish.it/red.iso', device_info['Image'])
        self.assertEqual('fish.iso', device_info['ImageName'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])
        self.assertEqual(local_file, device_info['_local_file'])

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(builtins, 'open', autospec=True)
    @mock.patch.object(vmedia.os, 'rename', autospec=True)
    @mock.patch.object(vmedia, 'tempfile', autospec=True)
    @mock.patch.object(vmedia, 'requests', autospec=True)
    def test_insert_image_fail(self, mock_requests, mock_tempfile, mock_rename,
                               mock_open, mock_get_device):
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
        mock_rsp.status_code = 401

        self.assertRaises(error.FishyError,
                          self.test_driver.insert_image,
                          self.UUID, 'Cd', 'http://fish.it/red.iso',
                          inserted=True, write_protected=False)
        mock_requests.get.assert_called_once_with(
            'http://fish.it/red.iso', stream=True, auth=None, verify=False)
        mock_open.assert_not_called()
        self.assertEqual({}, device_info)

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(vmedia.os, 'unlink', autospec=True)
    def test_eject_image(self, mock_unlink, mock_get_device):
        device_info = {
            '_local_file': '/tmp/fish.iso'
        }
        mock_get_device.return_value = device_info

        self.test_driver.eject_image(self.UUID, 'Cd')

        self.assertEqual('', device_info['Image'])
        self.assertEqual('', device_info['ImageName'])
        self.assertFalse(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])

        mock_unlink.assert_called_once_with('/tmp/fish.iso')

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_list_certificates(self, mock_get_device):
        mock_get_device.return_value = {
            'Certificate': {'Type': 'PEM', 'String': 'abcd'},
        }
        result = self.test_driver.list_certificates(self.UUID, 'Cd')
        self.assertEqual([vmedia.Certificate('Default', 'abcd', 'PEM')],
                         result)

    def test_list_certificates_empty(self):
        result = self.test_driver.list_certificates(self.UUID, 'Cd')
        self.assertEqual([], result)

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_add_certificate(self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        result = self.test_driver.add_certificate(self.UUID, 'Cd',
                                                  'abcd', 'PEM')
        self.assertEqual(vmedia.Certificate('Default', 'abcd', 'PEM'), result)
        self.assertEqual({'Certificate': {'Type': 'PEM', 'String': 'abcd'}},
                         device_info)

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_add_certificate_exists(self, mock_get_device):
        device_info = {
            'Certificate': {'Type': 'PEM', 'String': 'abcd'},
        }
        mock_get_device.return_value = device_info

        self.assertRaises(error.FishyError,
                          self.test_driver.add_certificate,
                          self.UUID, 'Cd', 'defg', 'PEM')

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_replace_certificate(self, mock_get_device):
        device_info = {
            'Certificate': {'Type': 'PEM', 'String': 'abcd'},
        }
        mock_get_device.return_value = device_info

        result = self.test_driver.replace_certificate(self.UUID, 'Cd',
                                                      'Default', 'defg', 'PEM')
        self.assertEqual(vmedia.Certificate('Default', 'defg', 'PEM'), result)
        self.assertEqual({'Certificate': {'Type': 'PEM', 'String': 'defg'}},
                         device_info)

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_replace_certificate_wrong_id(self, mock_get_device):
        device_info = {
            'Certificate': {'Type': 'PEM', 'String': 'abcd'},
        }
        mock_get_device.return_value = device_info

        self.assertRaises(error.NotFound,
                          self.test_driver.replace_certificate,
                          self.UUID, 'Cd', 'Other', 'defg', 'PEM')

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_replace_certificate_not_found(self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        self.assertRaises(error.NotFound,
                          self.test_driver.replace_certificate,
                          self.UUID, 'Cd', 'Default', 'defg', 'PEM')

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_delete_certificate(self, mock_get_device):
        device_info = {
            'Certificate': {'Type': 'PEM', 'String': 'abcd'},
        }
        mock_get_device.return_value = device_info

        self.test_driver.delete_certificate(self.UUID, 'Cd', 'Default')
        self.assertEqual({}, device_info)

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_delete_certificate_not_found(self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        self.assertRaises(error.NotFound,
                          self.test_driver.delete_certificate,
                          self.UUID, 'Cd', 'Default')

    @mock.patch.object(builtins, 'open', autospec=True)
    @mock.patch.object(vmedia.os, 'rename', autospec=True)
    @mock.patch.object(vmedia, 'tempfile', autospec=True)
    @mock.patch.object(vmedia, 'requests', autospec=True)
    def test__get_image(self, mock_requests, mock_tempfile, mock_rename,
                        mock_open):
        mock_tempfile.mkdtemp.return_value = '/alphabet/soup'
        mock_tmp_file = (mock_tempfile.NamedTemporaryFile
                         .return_value.__enter__.return_value)
        mock_tmp_file.name = 'alphabet.soup'
        mock_rsp = mock_requests.get.return_value.__enter__.return_value
        mock_rsp.headers = {
            'content-disposition': 'attachment; filename="fish.iso"'
        }
        mock_rsp.status_code = 200

        self.assertEqual(
            ('fish.iso', '/alphabet/soup/fish.iso'),
            self.test_driver._get_image(
                'http://fish.it/fish.iso', None, False, None))


class OpenstackDriverTestCase(base.BaseTestCase):

    UUID = 'ZZZ-YYY-XXX'

    def setUp(self):
        super().setUp()
        self.novadriver = mock.Mock()
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            self.test_driver = vmedia.OpenstackDriver(
                {}, mock.MagicMock(), self.novadriver)

    @mock.patch.object(vmedia.OpenstackDriver, '_get_device', autospec=True)
    def test_insert_image(self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        self.novadriver.insert_image.return_value = ('aaa-bbb', 'red.iso')

        image_id = self.test_driver.insert_image(
            self.UUID, 'Cd', 'http://fish.it/red.iso', inserted=True,
            write_protected=False)

        self.novadriver.insert_image.assert_called_once_with(
            self.UUID, 'http://fish.it/red.iso', None)
        self.assertEqual('aaa-bbb', image_id)

        self.assertEqual('http://fish.it/red.iso', device_info['Image'])
        self.assertEqual('red.iso', device_info['ImageName'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])

    @mock.patch.object(vmedia.OpenstackDriver, '_get_image', autospec=True)
    @mock.patch.object(vmedia.OpenstackDriver, '_get_device', autospec=True)
    def test_insert_image_file_upload(self, mock_get_device, mock_get_image):
        device_info = {}
        mock_get_device.return_value = device_info
        mock_get_image.return_value = ('red.iso', '/fish.it/red.iso')
        file_upload_key = 'SUSHY_EMULATOR_OS_VMEDIA_IMAGE_FILE_UPLOAD'
        self.test_driver._config[file_upload_key] = True

        self.novadriver.insert_image.return_value = ('aaa-bbb', 'red.iso')

        image_id = self.test_driver.insert_image(
            self.UUID, 'Cd', 'http://fish.it/red.iso', inserted=True,
            write_protected=False)

        self.novadriver.insert_image.assert_called_once_with(
            self.UUID, 'http://fish.it/red.iso', '/fish.it/red.iso')
        self.assertEqual('aaa-bbb', image_id)

        self.assertEqual('http://fish.it/red.iso', device_info['Image'])
        self.assertEqual('red.iso', device_info['ImageName'])
        self.assertTrue(device_info['Inserted'])
        self.assertFalse(device_info['WriteProtected'])

    @mock.patch.object(vmedia.OpenstackDriver, '_get_device', autospec=True)
    def test_insert_image_auth(self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        self.assertRaises(
            error.NotSupportedError, self.test_driver.insert_image,
            self.UUID, 'Cd', 'http://fish.it/red.iso', inserted=True,
            write_protected=False, username='Admin', password='Secret')

    @mock.patch.object(vmedia.OpenstackDriver, '_get_device', autospec=True)
    def test_insert_image_verify_ssl(self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        ssl_conf_key = 'SUSHY_EMULATOR_VMEDIA_VERIFY_SSL'
        self.test_driver._config[ssl_conf_key] = True
        self.assertRaises(
            error.NotSupportedError, self.test_driver.insert_image,
            self.UUID, 'Cd', 'https://fish.it/red.iso', inserted=True,
            write_protected=False)

    @mock.patch.object(vmedia.OpenstackDriver, '_get_device', autospec=True)
    def test_insert_image_fail(self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info
        self.novadriver.insert_image.side_effect = error.FishyError('ouch')

        e = self.assertRaises(
            error.FishyError, self.test_driver.insert_image,
            self.UUID, 'Cd', 'http://fish.it/red.iso', inserted=True,
            write_protected=False)
        self.assertEqual('ouch', str(e))

    @mock.patch.object(vmedia.OpenstackDriver, '_get_device', autospec=True)
    def test_eject_image(self, mock_get_device):

        device_info = {
            'Image': 'http://fish.it/red.iso',
            'Inserted': True
        }
        mock_get_device.return_value = device_info

        self.test_driver.eject_image(self.UUID, 'Cd')

        self.assertFalse(device_info['Inserted'])
        self.assertEqual('', device_info['Image'])
        self.assertEqual('', device_info['ImageName'])

    @mock.patch.object(vmedia.OpenstackDriver, '_get_device', autospec=True)
    def test_eject_image_error(self, mock_get_device):
        device_info = {
            'Image': 'http://fish.it/red.iso',
            'Inserted': True
        }
        mock_get_device.return_value = device_info
        self.novadriver.eject_image.side_effect = error.FishyError('ouch')

        e = self.assertRaises(
            error.FishyError, self.test_driver.eject_image,
            self.UUID, 'Cd')
        self.assertEqual('ouch', str(e))
        self.assertTrue(device_info['Inserted'])


class IpFamilyValidationTestCase(base.BaseTestCase):
    """Test IP family validation for virtual media."""

    UUID = 'ZZZ-YYY-XXX'

    CONFIG = {
        'SUSHY_EMULATOR_VMEDIA_DEVICES': {
            "Cd": {
                "Name": "Virtual CD",
                "MediaTypes": [
                    "CD",
                    "DVD"
                ]
            }
        }
    }

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_insert_image_ip_family_validation_ipv4_required_ipv6_provided(
            self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        # Create driver with IPv4 restriction
        config = self.CONFIG.copy()
        config['SUSHY_EMULATOR_VIRTUAL_MEDIA_IP_FAMILY'] = '4'
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            driver = vmedia.StaticDriver(config, mock.MagicMock())

        # IPv6 URL should raise error when IPv4 is required
        self.assertRaises(error.BadRequest,
                          driver.insert_image,
                          self.UUID, 'Cd', 'http://[::1]/image.iso')

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    def test_insert_image_ip_family_validation_ipv6_required_ipv4_provided(
            self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        # Create driver with IPv6 restriction
        config = self.CONFIG.copy()
        config['SUSHY_EMULATOR_VIRTUAL_MEDIA_IP_FAMILY'] = '6'
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            driver = vmedia.StaticDriver(config, mock.MagicMock())

        # IPv4 URL should raise error when IPv6 is required
        self.assertRaises(error.BadRequest,
                          driver.insert_image,
                          self.UUID, 'Cd', 'http://192.168.1.1/image.iso')

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(vmedia.StaticDriver, '_get_image', autospec=True)
    def test_insert_image_ip_family_validation_hostname_allowed(
            self, mock_get_image, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info
        mock_get_image.return_value = ('image.iso', '/tmp/image.iso')

        # Create driver with IPv4 restriction
        config = self.CONFIG.copy()
        config['SUSHY_EMULATOR_VIRTUAL_MEDIA_IP_FAMILY'] = '4'
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            driver = vmedia.StaticDriver(config, mock.MagicMock())

        # Hostname should be allowed regardless of IP family restriction
        result = driver.insert_image(self.UUID, 'Cd',
                                     'http://example.com/image.iso')
        self.assertEqual('/tmp/image.iso', result)

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(vmedia.StaticDriver, '_get_image', autospec=True)
    def test_insert_image_ip_family_validation_ipv4_allowed(
            self, mock_get_image, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info
        mock_get_image.return_value = ('image.iso', '/tmp/image.iso')

        # Create driver with IPv4 restriction
        config = self.CONFIG.copy()
        config['SUSHY_EMULATOR_VIRTUAL_MEDIA_IP_FAMILY'] = '4'
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            driver = vmedia.StaticDriver(config, mock.MagicMock())

        # IPv4 address should be allowed when IPv4 is required
        result = driver.insert_image(self.UUID, 'Cd',
                                     'http://192.168.1.1/image.iso')
        self.assertEqual('/tmp/image.iso', result)

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(vmedia.StaticDriver, '_get_image', autospec=True)
    def test_insert_image_ip_family_validation_ipv6_allowed(
            self, mock_get_image, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info
        mock_get_image.return_value = ('image.iso', '/tmp/image.iso')

        # Create driver with IPv6 restriction
        config = self.CONFIG.copy()
        config['SUSHY_EMULATOR_VIRTUAL_MEDIA_IP_FAMILY'] = '6'
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            driver = vmedia.StaticDriver(config, mock.MagicMock())

        # IPv6 address should be allowed when IPv6 is required
        result = driver.insert_image(self.UUID, 'Cd',
                                     'http://[::1]/image.iso')
        self.assertEqual('/tmp/image.iso', result)

    @mock.patch.object(vmedia.StaticDriver, '_get_device', autospec=True)
    @mock.patch.object(vmedia.StaticDriver, '_get_image', autospec=True)
    def test_insert_image_ip_family_validation_disabled(
            self, mock_get_image, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info
        mock_get_image.return_value = ('image.iso', '/tmp/image.iso')

        # Create driver without IP family restriction
        config = self.CONFIG.copy()
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            driver = vmedia.StaticDriver(config, mock.MagicMock())

        # Both IPv4 and IPv6 should be allowed when no restriction is set
        result = driver.insert_image(self.UUID, 'Cd',
                                     'http://192.168.1.1/image.iso')
        self.assertEqual('/tmp/image.iso', result)

        result = driver.insert_image(self.UUID, 'Cd',
                                     'http://[::1]/image.iso')
        self.assertEqual('/tmp/image.iso', result)

    @mock.patch.object(vmedia.OpenstackDriver, '_get_device', autospec=True)
    def test_openstack_driver_ip_family_validation_ipv4_required_ipv6(
            self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        # Create driver with IPv4 restriction
        config = {'SUSHY_EMULATOR_VIRTUAL_MEDIA_IP_FAMILY': '4'}
        novadriver = mock.Mock()
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            driver = vmedia.OpenstackDriver(config, mock.MagicMock(),
                                            novadriver)

        # IPv6 URL should raise error when IPv4 is required
        self.assertRaises(error.BadRequest,
                          driver.insert_image,
                          self.UUID, 'Cd', 'http://[::1]/image.iso')

    @mock.patch.object(vmedia.OpenstackDriver, '_get_device', autospec=True)
    def test_openstack_driver_ip_family_validation_ipv6_required_ipv4(
            self, mock_get_device):
        device_info = {}
        mock_get_device.return_value = device_info

        # Create driver with IPv6 restriction
        config = {'SUSHY_EMULATOR_VIRTUAL_MEDIA_IP_FAMILY': '6'}
        novadriver = mock.Mock()
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            driver = vmedia.OpenstackDriver(config, mock.MagicMock(),
                                            novadriver)

        # IPv4 URL should raise error when IPv6 is required
        self.assertRaises(error.BadRequest,
                          driver.insert_image,
                          self.UUID, 'Cd', 'http://192.168.1.1/image.iso')
