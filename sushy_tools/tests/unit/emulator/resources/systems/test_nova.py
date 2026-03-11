# Copyright 2018 Red Hat, Inc.
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
import base64
import time
from unittest import mock

from munch import Munch
from oslotest import base

from sushy_tools.emulator.resources.systems.novadriver import OpenStackDriver
from sushy_tools import error


@mock.patch.dict(OpenStackDriver.PERMANENT_CACHE)
class NovaDriverTestCase(base.BaseTestCase):

    name = 'QEmu-fedora-i686'
    uuid = 'c7a5fdbd-cdaf-9455-926a-d65c16db1809'

    def setUp(self):
        self.nova_patcher = mock.patch('openstack.connect', autospec=True)
        self.nova_mock = self.nova_patcher.start()
        self._cc = self.nova_mock.return_value

        test_driver_class = OpenStackDriver.initialize(
            {}, mock.MagicMock(), 'fake-cloud')
        self.test_driver = test_driver_class()
        self.test_driver._futures.clear()

        super(NovaDriverTestCase, self).setUp()

    def tearDown(self):
        self.nova_patcher.stop()
        super(NovaDriverTestCase, self).tearDown()

    def test_uuid(self):
        server = mock.Mock(id=self.uuid)
        self.nova_mock.return_value.get_server.return_value = server
        uuid = self.test_driver.uuid(self.uuid)
        self.assertEqual(self.uuid, uuid)

    def test_systems(self):
        server0 = mock.Mock(id='host0')
        server1 = mock.Mock(id='host1')
        self.nova_mock.return_value.list_servers.return_value = [
            server0, server1]
        systems = self.test_driver.systems

        self.assertEqual(['host0', 'host1'], systems)

    def test_get_power_state_on(self,):
        server = mock.Mock(id=self.uuid,
                           power_state=1)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        power_state = self.test_driver.get_power_state(self.uuid)

        self.assertEqual('On', power_state)

    def test_get_power_state_off(self):
        server = mock.Mock(id=self.uuid,
                           power_state=0)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        power_state = self.test_driver.get_power_state(self.uuid)

        self.assertEqual('Off', power_state)

    @mock.patch('time.sleep')
    def test_set_power_state_on(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=0, task_state=None,
                           metadata={})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'On')
        compute = self.nova_mock.return_value.compute
        compute.start_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_set_power_state_forceon(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=0, task_state=None,
                           metadata={})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'ForceOn')
        compute = self.nova_mock.return_value.compute
        compute.start_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_set_power_state_forceoff(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None,
                           metadata={})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'ForceOff')
        compute = self.nova_mock.return_value.compute
        compute.stop_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_set_power_state_gracefulshutdown(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None,
                           metadata={})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'GracefulShutdown')
        compute = self.nova_mock.return_value.compute
        compute.stop_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_set_power_state_gracefulrestart(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None,
                           metadata={})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'GracefulRestart')
        compute = self.nova_mock.return_value.compute
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='SOFT')

    @mock.patch('time.sleep')
    def test_set_power_state_forcerestart(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None,
                           metadata={})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(
            self.uuid, 'ForceRestart')
        compute = self.nova_mock.return_value.compute
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='HARD')

    @mock.patch('time.sleep')
    def test_set_power_state_raises_SYS518(self, mock_sleep):
        server_busy = mock.Mock(
            id=self.uuid, power_state=1, task_state='rebuilding',
            metadata={})
        self.nova_mock.return_value.get_server.return_value = server_busy
        server_busy.fetch.return_value = None
        e = self.assertRaises(
            error.FishyError, self.test_driver.set_power_state,
            self.uuid, 'SOFT')
        self.assertEqual(
            'SYS518: Cloud instance is busy, task_state: rebuilding',
            str(e))

    @mock.patch('time.sleep')
    @mock.patch.object(OpenStackDriver, "_rebuild_with_blank_image",
                       autospec=True)
    def test_set_power_state_delayed_eject(self, mock_rebuild_blank,
                                           mock_sleep):
        """Test that 503 is always raised after triggering rebuild"""
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None,
                           metadata={'sushy-tools-delay-eject': 'true'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Should raise 503 after triggering rebuild
        e = self.assertRaises(
            error.FishyError, self.test_driver.set_power_state,
            self.uuid, 'ForceOff')
        self.assertIn('SYS518: Cloud instance rebuilding', str(e))

        # Rebuild should have been triggered
        mock_rebuild_blank.assert_called_once_with(self.test_driver, self.uuid)
        self._cc.delete_server_metadata.assert_called_once_with(
            self.uuid, ['sushy-tools-delay-eject'])

        # Power state change should NOT have been attempted
        compute = self.nova_mock.return_value.compute
        compute.stop_server.assert_not_called()

    @mock.patch('time.sleep')
    @mock.patch.object(OpenStackDriver, "_rebuild_with_blank_image",
                       autospec=True)
    def test_set_power_state_delayed_eject_busy(self, mock_rebuild_blank,
                                                mock_sleep):
        """Test that rebuild is not attempted when instance is busy"""
        server = mock.Mock(id=self.uuid, power_state=4,
                           task_state='powering-off',
                           metadata={'sushy-tools-delay-eject': 'true'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Should raise 503 before attempting rebuild due to powering-off state
        e = self.assertRaises(
            error.FishyError, self.test_driver.set_power_state,
            self.uuid, 'On')
        self.assertIn('SYS518: Cloud instance is busy', str(e))
        self.assertIn('powering-off', str(e))

        # Rebuild should NOT have been attempted
        mock_rebuild_blank.assert_not_called()

    def test_get_boot_device(self):
        server = mock.Mock(id=self.uuid)
        self.nova_mock.return_value.get_server.return_value = server

        boot_device = self.test_driver.get_boot_device(self.uuid)

        self.assertEqual('Pxe', boot_device)
        get_server_metadata = (
            self.nova_mock.return_value.compute.get_server_metadata)
        get_server_metadata.assert_called_once_with(server.id)

    def test_set_boot_device(self):
        server = mock.Mock(id=self.uuid)
        self.nova_mock.return_value.get_server.return_value = server

        compute = self.nova_mock.return_value.compute
        set_server_metadata = compute.set_server_metadata

        self.test_driver.set_boot_device(self.uuid, 'Pxe')

        set_server_metadata.assert_called_once_with(
            self.uuid, **{'libvirt:pxe-first': '1'}
        )

    def test_get_boot_mode(self):
        server = mock.Mock(id=self.uuid, image=dict(id=self.uuid))
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(properties={'hw_firmware_type': 'bios'})

        self.nova_mock.return_value.image.find_image.return_value = image

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertEqual('Legacy', boot_mode)

    def test_get_boot_mode_no_image(self):
        server = mock.Mock(id=self.uuid, image=dict(id=self.uuid))
        self.nova_mock.return_value.get_server.return_value = server

        self.nova_mock.return_value.image.find_image.return_value = None

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertIsNone(boot_mode)

    def test_get_boot_mode_volume_boot(self):
        volumes_attached = [mock.Mock(id='fake-vol-id')]
        server = mock.Mock(id=self.uuid, image=dict(id=None),
                           attached_volumes=volumes_attached)
        vol_metadata = {'hw_firmware_type': 'uefi'}
        volume = mock.Mock(id='fake-vol-id',
                           volume_image_metadata=vol_metadata)
        self.nova_mock.return_value.get_server.return_value = server
        self.nova_mock.return_value.volume.get_volume.return_value = volume

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertEqual('UEFI', boot_mode)

    def test_set_boot_mode(self):
        self.assertRaises(
            error.FishyError, self.test_driver.set_boot_mode,
            self.uuid, 'Legacy')

    def test_get_total_memory(self):
        server = mock.Mock(id=self.uuid)
        self.nova_mock.return_value.get_server.return_value = server

        flavor = mock.Mock(ram=1024)
        self.nova_mock.return_value.get_flavor.return_value = flavor

        memory = self.test_driver.get_total_memory(self.uuid)

        self.assertEqual(1, memory)

    def test_get_total_cpus(self):
        server = mock.Mock(id=self.uuid)
        self.nova_mock.return_value.get_server.return_value = server

        flavor = mock.Mock(vcpus=2)
        self.nova_mock.return_value.get_flavor.return_value = flavor

        cpus = self.test_driver.get_total_cpus(self.uuid)

        self.assertEqual(2, cpus)

    def test_get_bios(self):
        self.assertRaises(
            error.FishyError, self.test_driver.get_bios, self.uuid)

    def test_set_bios(self):
        self.assertRaises(
            error.FishyError,
            self.test_driver.set_bios,
            self.uuid,
            {'attribute 1': 'value 1'})

    def test_reset_bios(self):
        self.assertRaises(
            error.FishyError, self.test_driver.reset_bios, self.uuid)

    def test_get_nics(self):
        addresses = Munch(
            {u'public': [
                Munch({u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:46:e3:ac',
                       u'version': 6,
                       u'addr': u'2001:db8::7',
                       u'OS-EXT-IPS:type': u'fixed'}),
                Munch({u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:46:e3:ac',
                       u'version': 4,
                       u'addr': u'172.24.4.4',
                       u'OS-EXT-IPS:type': u'fixed'})],
             u'private': [
                Munch({u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:22:18:31',
                       u'version': 6,
                       u'addr': u'fdc2:e509:41b8:0:f816:3eff:fe22:1831',
                       u'OS-EXT-IPS:type': u'fixed'}),
                Munch({u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:22:18:31',
                       u'version': 4,
                       u'addr': u'10.0.0.10',
                       u'OS-EXT-IPS:type': u'fixed'})]})

        server = mock.Mock(id=self.uuid, addresses=addresses)
        self.nova_mock.return_value.get_server.return_value = server

        nics = self.test_driver.get_nics(self.uuid)

        self.assertEqual([{'id': 'fa:16:3e:22:18:31',
                           'mac': 'fa:16:3e:22:18:31'},
                          {'id': 'fa:16:3e:46:e3:ac',
                           'mac': 'fa:16:3e:46:e3:ac'}],
                         sorted(nics, key=lambda k: k['id']))

    def test_get_nics_empty(self):
        server = mock.Mock(id=self.uuid, addresses=None)
        self.nova_mock.return_value.get_server.return_value = server
        nics = self.test_driver.get_nics(self.uuid)
        self.assertEqual(set(), nics)

    def test_get_nics_error(self):
        addresses = Munch(
            {u'public': [
                Munch({u'version': 6,
                       u'addr': u'2001:db8::7'}),
                Munch({u'version': 4,
                       u'addr': u'172.24.4.4'})],
             u'private': [
                Munch({u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:22:18:31',
                       u'version': 6,
                       u'addr': u'fdc2:e509:41b8:0:f816:3eff:fe22:1831',
                       u'OS-EXT-IPS:type': u'fixed'}),
                Munch({u'OS-EXT-IPS-MAC:mac_addr': u'fa:16:3e:22:18:31',
                       u'version': 4,
                       u'addr': u'10.0.0.10',
                       u'OS-EXT-IPS:type': u'fixed'})]})

        server = mock.Mock(id=self.uuid, addresses=addresses)
        self.nova_mock.return_value.get_server.return_value = server
        nics = self.test_driver.get_nics(self.uuid)
        self.assertEqual([{'id': 'fa:16:3e:22:18:31',
                           'mac': 'fa:16:3e:22:18:31'}], nics)

    def test_get_simple_storage_collection(self):
        self.assertRaises(
            error.FishyError,
            self.test_driver.get_simple_storage_collection, self.uuid)

    def test_get_secure_boot_off(self):
        server = mock.Mock(id=self.uuid, image=dict(id=self.uuid))
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(properties={'hw_firmware_type': 'uefi'})

        self.nova_mock.return_value.image.find_image.return_value = image

        self.assertFalse(self.test_driver.get_secure_boot(self.uuid))

    def test_get_secure_boot_on(self):
        server = mock.Mock(id=self.uuid, image=dict(id=self.uuid))
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(properties={'hw_firmware_type': 'uefi',
                                      'os_secure_boot': 'required'})

        self.nova_mock.return_value.image.find_image.return_value = image

        self.assertTrue(self.test_driver.get_secure_boot(self.uuid))

    def test_get_secure_boot_off_volume_boot(self):
        volumes_attached = [mock.Mock(id='fake-vol-id')]
        server = mock.Mock(id=self.uuid, image=dict(id=None),
                           attached_volumes=volumes_attached)
        self.nova_mock.return_value.get_server.return_value = server
        vol_metadata = {'hw_firmware_type': 'uefi'}
        volume = mock.Mock(id='fake-vol-id',
                           volume_image_metadata=vol_metadata)

        image = mock.Mock()

        self.nova_mock.return_value.image.find_image.return_value = image
        self.nova_mock.return_value.volume.get_volume.return_value = volume

        self.assertFalse(self.test_driver.get_secure_boot(self.uuid))

    def test_get_secure_boot_on_volume_boot(self):
        volumes_attached = [mock.Mock(id='fake-vol-id')]
        server = mock.Mock(id=self.uuid, image=dict(id=None),
                           attached_volumes=volumes_attached)
        self.nova_mock.return_value.get_server.return_value = server
        vol_metadata = {'os_secure_boot': 'required'}
        volume = mock.Mock(id='fake-vol-id',
                           volume_image_metadata=vol_metadata)

        image = mock.Mock()

        self.nova_mock.return_value.image.find_image.return_value = image
        self.nova_mock.return_value.volume.get_volume.return_value = volume

        self.assertTrue(self.test_driver.get_secure_boot(self.uuid))

    def test_set_secure_boot(self):
        self.assertRaises(
            error.NotSupportedError, self.test_driver.set_secure_boot,
            self.uuid, True)

    def test_set_get_http_boot_uri(self):
        self.assertRaises(error.NotSupportedError,
                          self.test_driver.get_http_boot_uri,
                          None)
        self.assertRaises(error.NotSupportedError,
                          self.test_driver.set_http_boot_uri,
                          None)

    @mock.patch.object(OpenStackDriver, 'get_boot_mode', autospec=True)
    @mock.patch.object(base64, 'urlsafe_b64encode', autospec=True)
    def test_insert_image(self, mock_b64e, mock_get_boot_mode):
        mock_get_boot_mode.return_value = None
        mock_b64e.return_value = b'0hIwh_vN'
        queued_image = mock.Mock(id='aaa-bbb')
        self._cc.image.create_image.return_value = queued_image

        image_id, image_name = self.test_driver.insert_image(
            self.uuid, 'http://fish.it/red.iso')

        self._cc.image.create_image.assert_called_once_with(
            name='red.iso 0hIwh_vN', disk_format='iso',
            container_format='bare', visibility='private')

        self._cc.image.import_image.assert_called_once_with(
            queued_image, method='web-download', uri='http://fish.it/red.iso')
        self._cc.set_server_metadata.assert_called_once_with(
            self.uuid,
            {'sushy-tools-image-url': 'http://fish.it/red.iso',
             'sushy-tools-import-image': 'aaa-bbb'})

        self.assertEqual('aaa-bbb', image_id)

    @mock.patch('builtins.open', autospec=True)
    @mock.patch.object(OpenStackDriver, 'get_boot_mode', autospec=True)
    @mock.patch.object(base64, 'urlsafe_b64encode', autospec=True)
    def test_insert_image_file_upload(self, mock_b64e, mock_get_boot_mode,
                                      mock_open):
        mock_get_boot_mode.return_value = None
        mock_b64e.return_value = b'0hIwh_vN'
        queued_image = mock.Mock(id='aaa-bbb')

        self._cc.image.create_image.return_value = queued_image

        # Mock file reading for ISO detection
        mock_file = mock.MagicMock()
        mock_file.read.side_effect = [
            b'\x00\x00\x00\x00',  # First 4 bytes (not QCOW2)
            b'CD001'  # ISO signature at offset 32769
        ]
        mock_file.seek.return_value = None
        mock_open.return_value.__enter__.return_value = mock_file

        image_id, image_name = self.test_driver.insert_image(
            self.uuid, 'http://fish.it/red.iso', '/alphabet/soup/red.iso')

        self._cc.image.create_image.assert_called_once_with(
            name='red.iso 0hIwh_vN', disk_format='iso',
            container_format='bare', visibility='private',
            filename='/alphabet/soup/red.iso')
        self._cc.image.import_image.assert_not_called()
        self._cc.set_server_metadata.assert_called_once_with(
            self.uuid,
            {'sushy-tools-image-url': 'http://fish.it/red.iso',
             'sushy-tools-image-local-file': '/alphabet/soup/red.iso',
             'sushy-tools-import-image': 'aaa-bbb'})

        self.assertEqual('aaa-bbb', image_id)

    @mock.patch('builtins.open', autospec=True)
    def test_get_disk_format_from_content(self, mock_open):
        """Test disk format detection from file content"""
        # Test ISO format
        mock_file = mock.MagicMock()
        mock_file.read.side_effect = [
            b'\x00\x00\x00\x00',  # First 4 bytes (not QCOW2)
            b'CD001'  # ISO signature at offset 32769
        ]
        mock_file.seek.return_value = None
        mock_open.return_value.__enter__.return_value = mock_file

        result = self.test_driver._get_disk_format_from_content(
            '/path/to/test.iso')
        self.assertEqual('iso', result)
        mock_file.seek.assert_called_once_with(32769)

        # Test QCOW2 format
        mock_file = mock.MagicMock()
        mock_file.read.return_value = b'QFI\xfb'
        mock_open.return_value.__enter__.return_value = mock_file

        result = self.test_driver._get_disk_format_from_content(
            '/path/to/test.qcow2')
        self.assertEqual('qcow2', result)

        # Test raw format (no recognized signature)
        mock_file = mock.MagicMock()
        mock_file.read.side_effect = [
            b'\x00\x00\x00\x00',  # First 4 bytes (not QCOW2)
            b'\x00\x00\x00\x00\x00'  # Not ISO signature
        ]
        mock_open.return_value.__enter__.return_value = mock_file

        result = self.test_driver._get_disk_format_from_content(
            '/path/to/test.img')
        self.assertEqual('raw', result)

        # Test error fallback
        mock_open.side_effect = IOError('File not found')

        result = self.test_driver._get_disk_format_from_content(
            '/path/to/missing.img')
        self.assertEqual('raw', result)

    def test_get_disk_format_from_filename(self):
        """Test disk format inference from filename extensions"""
        # ISO format
        self.assertEqual('iso',
                         self.test_driver._get_disk_format_from_filename(
                             'boot.iso'))
        self.assertEqual('iso',
                         self.test_driver._get_disk_format_from_filename(
                             'BOOT.ISO'))
        # QCOW2 format
        self.assertEqual('qcow2',
                         self.test_driver._get_disk_format_from_filename(
                             'image.qcow2'))
        self.assertEqual('qcow2',
                         self.test_driver._get_disk_format_from_filename(
                             'image.qcow'))
        # Raw format (default for unknown extensions)
        self.assertEqual('raw',
                         self.test_driver._get_disk_format_from_filename(
                             'disk.img'))
        self.assertEqual('raw',
                         self.test_driver._get_disk_format_from_filename(
                             'disk.raw'))
        self.assertEqual('raw',
                         self.test_driver._get_disk_format_from_filename(
                             'unknown'))

    @mock.patch('builtins.open', autospec=True)
    def test_get_disk_format_from_local_file(self, mock_open):
        """Test _get_disk_format from local file uses content detection"""
        mock_file = mock.MagicMock()
        mock_file.read.side_effect = [
            b'\x00\x00\x00\x00',  # First 4 bytes (not QCOW2)
            b'CD001'  # ISO signature at offset 32769
        ]
        mock_open.return_value.__enter__.return_value = mock_file

        result = self.test_driver._get_disk_format(
            'boot.iso', '/local/path/boot.iso')

        self.assertEqual('iso', result)

    def test_get_disk_format_without_local_file(self):
        """Test _get_disk_format without local file uses filename inference"""
        result = self.test_driver._get_disk_format('image.qcow2', None)

        self.assertEqual('qcow2', result)

    @mock.patch('builtins.open', autospec=True)
    def test_get_disk_format_with_override(self, mock_open):
        """Test _get_disk_format respects configuration override"""
        # Configure override to 'raw'
        self.test_driver._config[
            'SUSHY_EMULATOR_OS_VMEDIA_DISK_FORMAT_OVERRIDE'] = 'raw'

        # Test with local file that would be detected as ISO
        mock_file = mock.MagicMock()
        mock_file.read.side_effect = [
            b'\x00\x00\x00\x00',  # First 4 bytes (not QCOW2)
            b'CD001'  # ISO signature at offset 32769
        ]
        mock_open.return_value.__enter__.return_value = mock_file

        result = self.test_driver._get_disk_format(
            'boot.iso', '/local/path/boot.iso')
        self.assertEqual('raw', result)

        # Test with filename that would be detected as qcow2
        result = self.test_driver._get_disk_format('image.qcow2', None)
        self.assertEqual('raw', result)

        # Clean up
        del self.test_driver._config[
            'SUSHY_EMULATOR_OS_VMEDIA_DISK_FORMAT_OVERRIDE']

    @mock.patch.object(OpenStackDriver, 'get_boot_mode', autospec=True)
    def test_insert_image_fail(self, mock_get_boot_mode):
        mock_get_boot_mode.return_value = None
        self._cc.image.create_image.return_value = mock.Mock(id='aaa-bbb')

        self._cc.image.create_image.side_effect = Exception('ouch')

        e = self.assertRaises(
            error.FishyError, self.test_driver.insert_image,
            self.uuid, 'http://fish.it/red.iso')
        self.assertEqual(
            'Failed insert image from URL http://fish.it/red.iso: ouch',
            str(e))

    @mock.patch.object(OpenStackDriver, 'get_boot_mode', autospec=True)
    def test_insert_image_future_running(self, mock_get_boot_mode):
        mock_get_boot_mode.return_value = None
        mock_future = mock.Mock()
        mock_future.running.return_value = True
        self.test_driver._futures[self.uuid] = mock_future
        e = self.assertRaises(
            error.FishyError, self.test_driver.insert_image,
            self.uuid, 'http://fish.it/red.iso')
        self.assertEqual(
            'An insert or eject operation is already in progress for '
            'c7a5fdbd-cdaf-9455-926a-d65c16db1809', str(e))

    @mock.patch.object(OpenStackDriver, 'get_boot_mode', autospec=True)
    def test_insert_image_future_exception(self, mock_get_boot_mode):
        mock_get_boot_mode.return_value = None
        mock_future = mock.Mock()
        mock_future.running.return_value = False
        mock_future.exception.return_value = error.FishyError('ouch')
        self.test_driver._futures[self.uuid] = mock_future
        e = self.assertRaises(
            error.FishyError, self.test_driver.insert_image,
            self.uuid, 'http://fish.it/red.iso')
        self.assertEqual('ouch', str(e))

    def test_eject_image(self):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-import-image': 'ccc-ddd'
        }
        mock_image = mock.Mock(id='ccc-ddd')

        self._cc.compute.get_server.return_value = mock_server
        self._cc.image.find_image.return_value = mock_image

        self.test_driver.eject_image(self.uuid)

        self._cc.compute.get_server.assert_called_once_with(self.uuid)
        self._cc.image.find_image.assert_called_once_with('ccc-ddd')
        self._cc.delete_image.assert_called_once_with('ccc-ddd')

    def test_eject_image_error_detach(self):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-import-image': 'ccc-ddd'
        }

        self._cc.compute.get_server.return_value = mock_server
        self._cc.image.find_image.return_value = None

        e = self.assertRaises(
            error.FishyError, self.test_driver.eject_image,
            self.uuid)
        self.assertEqual(
            'Failed ejecting image http://fish.it/red.iso. '
            'Image not found in image service.', str(e))

        # self._cc.delete_image.assert_not_called()

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_imported_image(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso'
        }
        self._cc.compute.get_server.return_value = mock_server
        queued_image = mock.Mock(id='aaa-bbb', status='queued')
        self._cc.image.get_image.side_effect = [
            queued_image,
            mock.Mock(id='aaa-bbb', status='importing'),
            mock.Mock(id='aaa-bbb', status='active'),
        ]
        self._cc.compute.rebuild_server.return_value = mock.Mock(
            status='REBUILD')
        self._cc.compute.get_server.side_effect = [
            mock.Mock(status='REBUILD'),
            mock.Mock(status='ACTIVE'),
        ]

        self.test_driver._rebuild_with_imported_image(
            self.uuid, 'aaa-bbb')

        self._cc.compute.rebuild_server.assert_called_once_with(
            self.uuid, 'aaa-bbb')

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_imported_imaged_error_image(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
        }
        self._cc.image.get_image.side_effect = [
            mock.Mock(id='aaa-bbb', status='queued'),
            mock.Mock(id='aaa-bbb', status='importing'),
            mock.Mock(id='aaa-bbb', status='error'),
        ]
        e = self.assertRaises(
            error.FishyError, self.test_driver._rebuild_with_imported_image,
            self.uuid, 'aaa-bbb')
        self.assertEqual('Image import ended with status error', str(e))

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_imported_image_error_rebuild(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
        }
        self._cc.compute.get_server.return_value = mock_server
        self._cc.image.get_image.side_effect = [
            mock.Mock(id='aaa-bbb', status='queued'),
            mock.Mock(id='aaa-bbb', status='importing'),
            mock.Mock(id='aaa-bbb', status='active'),
        ]
        self._cc.compute.rebuild_server.return_value = mock.Mock(
            status='REBUILD')
        self._cc.compute.get_server.side_effect = [
            mock.Mock(status='REBUILD'),
            mock.Mock(status='ERROR'),
        ]
        e = self.assertRaises(
            error.FishyError, self.test_driver._rebuild_with_imported_image,
            self.uuid, 'aaa-bbb')
        self.assertEqual(
            'Server rebuild attempt resulted in status ERROR', str(e))

    @mock.patch('time.sleep')
    def test_check_and_wait_task_state_immediately_ready(self, mock_sleep):
        """Test when instance is immediately ready (task_state=None)"""
        server = mock.Mock(id=self.uuid, task_state=None)
        # fetch() updates instance in-place, doesn't change task_state
        server.fetch.return_value = None

        is_ready, result_instance = (
            self.test_driver._check_and_wait_for_task_state(server))

        self.assertTrue(is_ready)
        self.assertEqual(server, result_instance)
        # Should sleep for initial_wait (2s) + stability_wait (4s)
        self.assertEqual(2, mock_sleep.call_count)
        mock_sleep.assert_any_call(2)  # initial_wait
        mock_sleep.assert_any_call(4)  # stability_wait
        # fetch() called twice: initial check + stability check
        self.assertEqual(2, server.fetch.call_count)

    @mock.patch('time.sleep')
    def test_check_and_wait_task_state_becomes_ready(self, mock_sleep):
        """Test when instance becomes ready after polling"""
        server = mock.Mock(id=self.uuid, task_state='rebuilding')

        # fetch() updates: initial->busy, busy->ready, ready (stability)
        fetch_states = ['rebuilding', None, None]
        fetch_call_count = [0]

        def update_task_state(compute):
            server.task_state = fetch_states[fetch_call_count[0]]
            fetch_call_count[0] += 1

        server.fetch.side_effect = update_task_state

        is_ready, result_instance = (
            self.test_driver._check_and_wait_for_task_state(server))

        self.assertTrue(is_ready)
        self.assertEqual(server, result_instance)
        # Sleeps: 2s (initial check->busy), 4s (backoff->ready), 4s (stability)
        self.assertEqual(3, mock_sleep.call_count)

    @mock.patch('time.sleep')
    def test_check_and_wait_task_state_timeout(self, mock_sleep):
        """Test when instance stays busy and times out"""
        server = mock.Mock(id=self.uuid, task_state='rebuilding')
        # fetch() keeps task_state as 'rebuilding'
        server.fetch.return_value = None

        is_ready, result_instance = (
            self.test_driver._check_and_wait_for_task_state(
                server, max_wait=3))

        self.assertFalse(is_ready)
        self.assertEqual(server, result_instance)
        # Should have tried to poll multiple times within max_wait
        self.assertGreater(mock_sleep.call_count, 0)

    @mock.patch('time.sleep')
    def test_check_and_wait_task_state_stability_check_fails(self,
                                                             mock_sleep):
        """Test when stability check detects a state change"""
        server = mock.Mock(id=self.uuid, task_state=None)

        # fetch() updates: initial->busy, busy->busy, busy->ready, ready
        fetch_states = ['powering-off', 'powering-off', None, None]
        fetch_call_count = [0]

        def update_task_state(compute):
            server.task_state = fetch_states[fetch_call_count[0]]
            fetch_call_count[0] += 1

        server.fetch.side_effect = update_task_state

        is_ready, result_instance = (
            self.test_driver._check_and_wait_for_task_state(server))

        self.assertTrue(is_ready)
        self.assertEqual(server, result_instance)
        # Should have multiple sleeps due to stability check retry
        self.assertGreater(mock_sleep.call_count, 2)

    @mock.patch('time.sleep')
    def test_check_and_wait_task_state_exponential_backoff(self, mock_sleep):
        """Test exponential backoff behavior"""
        server = mock.Mock(id=self.uuid, task_state='rebuilding')

        # fetch() updates: initial->busy, busy->ready, ready (stability)
        fetch_states = ['rebuilding', None, None]
        fetch_call_count = [0]

        def update_task_state(compute):
            server.task_state = fetch_states[fetch_call_count[0]]
            fetch_call_count[0] += 1

        server.fetch.side_effect = update_task_state

        is_ready, result_instance = (
            self.test_driver._check_and_wait_for_task_state(server))

        self.assertTrue(is_ready)
        # Check that exponential backoff was used
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        # Should see: 2s (initial), 4s (backoff->ready), 4s (stability)
        self.assertEqual(3, len(calls))
        self.assertEqual(2, calls[0])  # initial_wait
        self.assertEqual(4, calls[1])  # exponential (2*2)
        self.assertEqual(4, calls[2])  # stability_wait


@mock.patch.dict(OpenStackDriver.PERMANENT_CACHE)
class NovaDriverRescuePXETestCase(base.BaseTestCase):
    """Tests for Nova driver rescue PXE boot functionality"""

    uuid = 'c7a5fdbd-cdaf-9455-926a-d65c16db1809'

    def setUp(self):
        super().setUp()
        self.nova_patcher = mock.patch('openstack.connect', autospec=True)
        self.nova_mock = self.nova_patcher.start()
        self._cc = self.nova_mock.return_value

    def tearDown(self):
        self.nova_patcher.stop()
        # Clear in-memory dict to prevent state pollution between tests
        if hasattr(OpenStackDriver, '_rescue_boot_modes'):
            OpenStackDriver._rescue_boot_modes = {}
        # Reset class-level state
        OpenStackDriver._rescue_pxe_enabled = False
        super().tearDown()

    def _create_driver(self, rescue_pxe_enabled=True):
        """Helper to create driver with rescue PXE boot enabled"""
        config = {
            'SUSHY_EMULATOR_OS_RESCUE_PXE_BOOT': rescue_pxe_enabled,
            'SUSHY_EMULATOR_OS_RESCUE_PXE_IMAGE_BIOS': 'ipxe-bios',
            'SUSHY_EMULATOR_OS_RESCUE_PXE_IMAGE_UEFI': 'ipxe-uefi'
        }

        test_driver_class = OpenStackDriver.initialize(
            config, mock.MagicMock(), 'fake-cloud')

        # Replace PersistentDict with plain dict for tests (avoid SQLite)
        if (rescue_pxe_enabled
                and hasattr(test_driver_class, '_rescue_boot_modes')):
            test_driver_class._rescue_boot_modes = {}

        test_driver = test_driver_class()
        test_driver._futures.clear()

        return test_driver

    @mock.patch('time.sleep')
    def test_set_boot_device_pxe_sets_persistent_storage(self, mock_sleep):
        """Test setting boot device to PXE stores in PersistentDict"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        compute = self.nova_mock.return_value.compute

        # Verify rescue PXE is enabled
        self.assertTrue(test_driver._rescue_pxe_enabled)

        # Set boot device to PXE
        test_driver.set_boot_device(self.uuid, 'Pxe')

        # Should store in PersistentDict
        self.assertEqual('pxe', test_driver._rescue_boot_modes.get(self.uuid))

        # Should NOT set metadata (rescue mode uses PersistentDict)
        compute.set_server_metadata.assert_not_called()

        # Should NOT trigger immediate rescue
        compute.rescue_server.assert_not_called()

    @mock.patch('time.sleep')
    def test_set_boot_device_disk_sets_persistent_storage(self, mock_sleep):
        """Test setting boot device to disk stores in PersistentDict"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='RESCUED', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        compute = self.nova_mock.return_value.compute

        # Set boot device to Hdd
        test_driver.set_boot_device(self.uuid, 'Hdd')

        # Should store in PersistentDict
        self.assertEqual('disk', test_driver._rescue_boot_modes[self.uuid])

        # Should NOT set metadata (rescue mode uses PersistentDict)
        compute.set_server_metadata.assert_not_called()

        # Should NOT trigger immediate unrescue
        compute.unrescue_server.assert_not_called()

    @mock.patch('time.sleep')
    def test_get_boot_device_pxe_from_persistent_storage(self, mock_sleep):
        """Test get_boot_device returns PXE from PersistentDict"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='RESCUED')
        self.nova_mock.return_value.get_server.return_value = server

        # Set boot mode in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'pxe'

        boot_device = test_driver.get_boot_device(self.uuid)

        self.assertEqual('Pxe', boot_device)

    @mock.patch('time.sleep')
    def test_get_boot_device_disk_from_persistent_storage(self, mock_sleep):
        """Test get_boot_device returns Hdd from PersistentDict"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE')
        self.nova_mock.return_value.get_server.return_value = server

        # Set boot mode in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'disk'

        boot_device = test_driver.get_boot_device(self.uuid)

        self.assertEqual('Hdd', boot_device)

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_with_pxe_triggers_rescue(self, mock_sleep,
                                               mock_check_wait):
        """Test power on with PXE boot mode uses rescue"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'pxe'

        # Mock boot mode check and rescue image
        image = mock.Mock(hw_firmware_type='uefi')
        self.nova_mock.return_value.image.find_image.side_effect = [
            image,  # boot mode check
            mock.Mock(id='ipxe-uefi-id')  # rescue image
        ]

        # Mock _check_and_wait_for_task_state:
        # First call (in set_power_state): ready
        # Second call (in _rescue_with_pxe_image): not ready (triggers 503)
        mock_check_wait.side_effect = [(True, server), (False, server)]

        # Power on should trigger rescue, wait, then 503 if not ready
        e = self.assertRaises(
            error.FishyError,
            test_driver.set_power_state, self.uuid, 'ForceOn')

        self.assertEqual(503, e.code)
        self.assertIn('entering rescue mode', str(e))
        compute.rescue_server.assert_called_once_with(
            self.uuid, image_ref='ipxe-uefi-id')
        # Called twice: once in set_power_state, once in _rescue_with_pxe_image
        self.assertEqual(2, mock_check_wait.call_count)

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_off_in_rescue_unrescues_then_stops(
            self, mock_sleep, mock_check_wait):
        """Test power off while in rescue mode unrescues then stops"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Track fetch calls to simulate state transition
        fetch_count = [0]

        def fetch_side_effect(compute):
            fetch_count[0] += 1
            # After second fetch (after unrescue), vm_state changes to ACTIVE
            if fetch_count[0] >= 2:
                server.vm_state = 'ACTIVE'

        server.fetch.side_effect = fetch_side_effect
        compute = self.nova_mock.return_value.compute

        # Set boot mode in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'pxe'

        # Mock _check_and_wait_for_task_state to always indicate ready
        # Called twice: once in set_power_state, once in
        # _unrescue_before_power_operation
        mock_check_wait.return_value = (True, server)

        # Power off
        test_driver.set_power_state(self.uuid, 'ForceOff')

        # Should unrescue first, then stop
        compute.unrescue_server.assert_called_once_with(self.uuid)
        compute.stop_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_restart_in_rescue_preserves_rescue(self, mock_sleep):
        """Test restart while in rescue preserves RESCUED state"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'pxe'

        # Restart
        test_driver.set_power_state(self.uuid, 'ForceRestart')

        # Should only reboot, not unrescue or re-rescue
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='HARD')
        compute.unrescue_server.assert_not_called()
        compute.rescue_server.assert_not_called()

    @mock.patch('time.sleep')
    def test_power_on_when_already_active_noop(self, mock_sleep):
        """Test power on when instance is already active is a no-op"""
        test_driver = self._create_driver()

        # Instance is already powered on with vm_state=ACTIVE
        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='ACTIVE',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode to disk
        test_driver._rescue_boot_modes[self.uuid] = 'disk'

        # Power on should be a no-op (not call start_server)
        test_driver.set_power_state(self.uuid, 'On')

        # Should NOT call start_server since already active
        compute.start_server.assert_not_called()

    @mock.patch('time.sleep')
    def test_power_on_in_rescue_when_already_active_noop(self, mock_sleep):
        """Test power on when in rescue mode and already active is a no-op"""
        test_driver = self._create_driver()

        # Instance is in rescue mode and already powered on
        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode to PXE (rescue)
        test_driver._rescue_boot_modes[self.uuid] = 'pxe'

        # Power on should be a no-op (not call start_server or rescue)
        test_driver.set_power_state(self.uuid, 'ForceOn')

        # Should NOT call start_server or rescue_server since already active
        compute.start_server.assert_not_called()
        compute.rescue_server.assert_not_called()

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_after_unrescue_when_stopped(
            self, mock_sleep, mock_check_wait):
        """Test power on after unrescue when instance is stopped

        After unrescue, if the instance is stopped (power_state=0),
        we should call start_server to power it on.
        """
        test_driver = self._create_driver()

        # Instance starts in rescue mode
        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='RESCUED',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Track fetch calls to simulate state transition
        fetch_count = [0]

        def fetch_side_effect(compute):
            fetch_count[0] += 1
            # After unrescue completes, vm_state becomes ACTIVE
            # and instance is stopped (power_state=0)
            if fetch_count[0] >= 2:
                server.vm_state = 'ACTIVE'
                server.power_state = 0  # Stopped

        server.fetch.side_effect = fetch_side_effect
        compute = self.nova_mock.return_value.compute

        # Set boot mode to disk (will trigger unrescue)
        test_driver._rescue_boot_modes[self.uuid] = 'disk'

        # Mock _check_and_wait_for_task_state to always indicate ready
        mock_check_wait.return_value = (True, server)

        # Power on should unrescue and then call start_server
        test_driver.set_power_state(self.uuid, 'On')

        # Should unrescue first
        compute.unrescue_server.assert_called_once_with(self.uuid)
        # Should call start_server since power_state=0
        compute.start_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_power_on_when_already_running_is_noop(self, mock_sleep):
        """Test power on when already running is a no-op

        If the instance is already running (power_state=1), we should not
        attempt any power operations at all, regardless of vm_state.
        """
        test_driver = self._create_driver()

        # Instance is already running
        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='ACTIVE',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode to disk
        test_driver._rescue_boot_modes[self.uuid] = 'disk'

        # Power on should be a no-op since already running
        test_driver.set_power_state(self.uuid, 'On')

        # Should NOT call start_server since power_state=1 (already running)
        compute.start_server.assert_not_called()
        # Should NOT call unrescue since not needed
        compute.unrescue_server.assert_not_called()

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_off_waits_for_state_stable(
            self, mock_sleep, mock_check_wait):
        """Test power off waits for power state to stabilize

        This verifies the slow BMC behavior - waiting for Nova state to
        fully settle before responding to avoid race conditions.
        """
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='ACTIVE',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Simulate power state transition during stabilization
        fetch_count = [0]

        def fetch_side_effect(compute):
            fetch_count[0] += 1
            # After stop_server, power_state changes from 1 to 0
            if fetch_count[0] >= 2:
                server.power_state = 0

        server.fetch.side_effect = fetch_side_effect
        compute = self.nova_mock.return_value.compute

        # Set boot mode to disk
        test_driver._rescue_boot_modes[self.uuid] = 'disk'

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Power off should call stop_server and wait for state to stabilize
        test_driver.set_power_state(self.uuid, 'ForceOff')

        # Should call stop_server
        compute.stop_server.assert_called_once_with(self.uuid)
        # Should wait (verify sleep was called for stabilization)
        self.assertTrue(mock_sleep.called)
        # Should fetch state multiple times (initial + stability checks)
        self.assertGreaterEqual(server.fetch.call_count, 2)

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_off_in_rescue_waits_for_state_stable(
            self, mock_sleep, mock_check_wait):
        """Test power off in rescue mode waits for state to stabilize

        Verifies that after unrescue + stop, we wait for stabilization.
        """
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Simulate state transitions: RESCUED -> ACTIVE (unrescue) -> off
        fetch_count = [0]

        def fetch_side_effect(compute):
            fetch_count[0] += 1
            # After unrescue
            if fetch_count[0] >= 2:
                server.vm_state = 'ACTIVE'
            # After stop_server
            if fetch_count[0] >= 3:
                server.power_state = 0

        server.fetch.side_effect = fetch_side_effect
        compute = self.nova_mock.return_value.compute

        # Set boot mode to disk
        test_driver._rescue_boot_modes[self.uuid] = 'disk'

        # Mock _check_and_wait_for_task_state to indicate ready
        # Called multiple times: initial check, unrescue wait, stop wait
        mock_check_wait.return_value = (True, server)

        # Power off should unrescue, stop, and wait for stabilization
        test_driver.set_power_state(self.uuid, 'GracefulShutdown')

        # Should unrescue first
        compute.unrescue_server.assert_called_once_with(self.uuid)
        # Should call stop_server
        compute.stop_server.assert_called_once_with(self.uuid)
        # Should wait (verify sleep was called)
        self.assertTrue(mock_sleep.called)
        # Should fetch state multiple times
        self.assertGreaterEqual(server.fetch.call_count, 3)

    def test_power_operations_on_error_instance_raise_error(self):
        """Test any power operation fails when instance is in ERROR state

        When Nova instance is in ERROR state, all power operations should
        fail with a clear error message, not just power on.
        """
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='ERROR',
            task_state=None, status='ERROR')
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Test various power operations all fail with ERROR state
        for power_state in ['On', 'ForceOn', 'ForceOff',
                            'GracefulShutdown', 'ForceRestart',
                            'GracefulRestart']:
            err = self.assertRaises(
                error.FishyError,
                test_driver.set_power_state,
                self.uuid, power_state)

            # Verify error message mentions ERROR state
            self.assertIn('ERROR state', str(err))
            # Verify HTTP 500 error code
            self.assertEqual(500, err.code)
