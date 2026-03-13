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

        # Replace PersistentDict with plain dict for tests (avoid SQLite)
        if hasattr(test_driver_class, '_volume_vmedia_images'):
            test_driver_class._volume_vmedia_images = {}
        if hasattr(test_driver_class, '_volume_vmedia_attrs'):
            test_driver_class._volume_vmedia_attrs = {}
        if hasattr(test_driver_class, '_volume_vmedia_delay_eject'):
            test_driver_class._volume_vmedia_delay_eject = {}

        super(NovaDriverTestCase, self).setUp()

    def tearDown(self):
        self.nova_patcher.stop()
        # Clear in-memory dicts to prevent state pollution between tests
        if hasattr(OpenStackDriver, '_volume_vmedia_images'):
            OpenStackDriver._volume_vmedia_images = {}
        if hasattr(OpenStackDriver, '_volume_vmedia_attrs'):
            OpenStackDriver._volume_vmedia_attrs = {}
        if hasattr(OpenStackDriver, '_volume_vmedia_delay_eject'):
            OpenStackDriver._volume_vmedia_delay_eject = {}
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
        server = mock.Mock(id=self.uuid, power_state=0, task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'On')
        compute = self.nova_mock.return_value.compute
        compute.start_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_set_power_state_forceon(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=0, task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'ForceOn')
        compute = self.nova_mock.return_value.compute
        compute.start_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_set_power_state_forceoff(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'ForceOff')
        compute = self.nova_mock.return_value.compute
        compute.stop_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_set_power_state_gracefulshutdown(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'GracefulShutdown')
        compute = self.nova_mock.return_value.compute
        compute.stop_server.assert_called_once_with(self.uuid)

    @mock.patch('time.sleep')
    def test_set_power_state_gracefulrestart(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        self.test_driver.set_power_state(self.uuid, 'GracefulRestart')
        compute = self.nova_mock.return_value.compute
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='SOFT')

    @mock.patch('time.sleep')
    def test_set_power_state_forcerestart(self, mock_sleep):
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None)
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
            id=self.uuid, power_state=1, task_state='rebuilding')
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
        server = mock.Mock(id=self.uuid, power_state=1, task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Set delay-eject flag in PersistentDict
        self.test_driver._volume_vmedia_delay_eject[self.uuid] = True

        # Should raise 503 after triggering rebuild
        e = self.assertRaises(
            error.FishyError, self.test_driver.set_power_state,
            self.uuid, 'ForceOff')
        self.assertIn('SYS518: Cloud instance rebuilding', str(e))

        # Rebuild should have been triggered
        mock_rebuild_blank.assert_called_once_with(self.test_driver, self.uuid)

        # Delay-eject flag should be cleared from PersistentDict
        self.assertNotIn(self.uuid,
                         self.test_driver._volume_vmedia_delay_eject)

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

        # Mock get_server to return a server with matching ID
        mock_server = mock.Mock(id=self.uuid)
        self._cc.get_server.return_value = mock_server

        image_id, image_name = self.test_driver.insert_image(
            self.uuid, 'http://fish.it/red.iso')

        self._cc.image.create_image.assert_called_once_with(
            name='red.iso 0hIwh_vN', disk_format='iso',
            container_format='bare', visibility='private')

        self._cc.image.import_image.assert_called_once_with(
            queued_image, method='web-download', uri='http://fish.it/red.iso')

        # Verify PersistentDict was updated
        self.assertEqual('aaa-bbb',
                         self.test_driver._volume_vmedia_images[self.uuid])
        self.assertEqual({'image_url': 'http://fish.it/red.iso'},
                         self.test_driver._volume_vmedia_attrs[self.uuid])

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

        # Mock get_server to return a server with matching ID
        mock_server = mock.Mock(id=self.uuid)
        self._cc.get_server.return_value = mock_server

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

        # Verify PersistentDict was updated
        self.assertEqual('aaa-bbb',
                         self.test_driver._volume_vmedia_images[self.uuid])
        expected_attrs = {
            'image_url': 'http://fish.it/red.iso',
            'local_file_path': '/alphabet/soup/red.iso'
        }
        self.assertEqual(expected_attrs,
                         self.test_driver._volume_vmedia_attrs[self.uuid])

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
        mock_server = mock.Mock(id=self.uuid)
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-import-image': 'ccc-ddd'
        }
        mock_image = mock.Mock(id='ccc-ddd')

        self._cc.get_server.return_value = mock_server
        self._cc.image.find_image.return_value = mock_image

        # Set up PersistentDict with image ID
        self.test_driver._volume_vmedia_images[self.uuid] = 'ccc-ddd'
        self.test_driver._volume_vmedia_attrs[self.uuid] = {
            'image_url': 'http://fish.it/red.iso'
        }

        self.test_driver.eject_image(self.uuid)

        self._cc.get_server.assert_called_once_with(self.uuid)
        self._cc.image.find_image.assert_called_once_with('ccc-ddd')
        self._cc.delete_image.assert_called_once_with('ccc-ddd')

    def test_eject_image_error_detach(self):
        mock_server = mock.Mock(id=self.uuid)
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-import-image': 'ccc-ddd'
        }

        self._cc.get_server.return_value = mock_server
        self._cc.image.find_image.return_value = None

        # Set up PersistentDict with image ID
        self.test_driver._volume_vmedia_images[self.uuid] = 'ccc-ddd'
        self.test_driver._volume_vmedia_attrs[self.uuid] = {
            'image_url': 'http://fish.it/red.iso'
        }

        e = self.assertRaises(
            error.FishyError, self.test_driver.eject_image,
            self.uuid)
        self.assertEqual(
            'Failed ejecting image http://fish.it/red.iso. '
            'Image not found in image service.', str(e))

        # self._cc.delete_image.assert_not_called()

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_imported_image(self, mock_sleep):
        mock_server = mock.Mock(id=self.uuid)
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso'
        }
        self._cc.get_server.return_value = mock_server

        # Set up PersistentDict
        self.test_driver._volume_vmedia_images[self.uuid] = 'aaa-bbb'
        self.test_driver._volume_vmedia_attrs[self.uuid] = {
            'image_url': 'http://fish.it/red.iso'
        }

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
        mock_server = mock.Mock(id=self.uuid)
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
        }
        self._cc.get_server.return_value = mock_server

        # Set up PersistentDict
        self.test_driver._volume_vmedia_images[self.uuid] = 'aaa-bbb'
        self.test_driver._volume_vmedia_attrs[self.uuid] = {
            'image_url': 'http://fish.it/red.iso'
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
        mock_server = mock.Mock(id=self.uuid)
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
        }
        self._cc.get_server.return_value = mock_server

        # Set up PersistentDict
        self.test_driver._volume_vmedia_images[self.uuid] = 'aaa-bbb'
        self.test_driver._volume_vmedia_attrs[self.uuid] = {
            'image_url': 'http://fish.it/red.iso'
        }

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
            task_state=None, status='ACTIVE')
        self.nova_mock.return_value.get_server.return_value = server
        compute = self.nova_mock.return_value.compute

        # Track fetch calls to simulate state transition
        fetch_count = [0]

        def fetch_side_effect(compute_arg):
            fetch_count[0] += 1
            # After unrescue completes, vm_state becomes ACTIVE
            # and instance is stopped (power_state=0)
            if fetch_count[0] >= 2:
                server.vm_state = 'ACTIVE'
                server.power_state = 0  # Stopped initially
            # After start_server is called, power_state becomes ON
            if compute.start_server.called:
                server.power_state = 1

        server.fetch.side_effect = fetch_side_effect

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


@mock.patch.dict(OpenStackDriver.PERMANENT_CACHE)
class NovaDriverRescueVMediaTestCase(base.BaseTestCase):
    """Tests for Nova driver rescue-based virtual media functionality"""

    uuid = 'c7a5fdbd-cdaf-9455-926a-d65c16db1809'

    def setUp(self):
        super().setUp()
        self.nova_patcher = mock.patch('openstack.connect', autospec=True)
        self.nova_mock = self.nova_patcher.start()
        self._cc = self.nova_mock.return_value

    def tearDown(self):
        self.nova_patcher.stop()
        # Clear in-memory dicts to prevent state pollution between tests
        if hasattr(OpenStackDriver, '_rescue_boot_modes'):
            OpenStackDriver._rescue_boot_modes = {}
        if hasattr(OpenStackDriver, '_rescue_vmedia_images'):
            OpenStackDriver._rescue_vmedia_images = {}
        if hasattr(OpenStackDriver, '_rescue_vmedia_attrs'):
            OpenStackDriver._rescue_vmedia_attrs = {}
        # Reset class-level state
        OpenStackDriver._rescue_vmedia_enabled = False
        OpenStackDriver._rescue_enabled = False
        super().tearDown()

    def _create_driver(self, rescue_vmedia_enabled=True):
        """Helper to create driver with rescue vmedia enabled"""
        config = {
            'SUSHY_EMULATOR_OS_VMEDIA_USE_RESCUE': rescue_vmedia_enabled,
            'SUSHY_EMULATOR_OS_VMEDIA_RESCUE_DEVICE': 'cdrom',
            'SUSHY_EMULATOR_OS_VMEDIA_RESCUE_BUS': 'scsi'
        }

        test_driver_class = OpenStackDriver.initialize(
            config, mock.MagicMock(), 'fake-cloud')

        # Replace PersistentDict with plain dict for tests (avoid SQLite)
        if rescue_vmedia_enabled:
            if hasattr(test_driver_class, '_rescue_boot_modes'):
                test_driver_class._rescue_boot_modes = {}
            if hasattr(test_driver_class, '_rescue_vmedia_images'):
                test_driver_class._rescue_vmedia_images = {}
            if hasattr(test_driver_class, '_rescue_vmedia_attrs'):
                test_driver_class._rescue_vmedia_attrs = {}

        test_driver = test_driver_class()
        test_driver._futures.clear()

        return test_driver

    @mock.patch('sushy_tools.emulator.resources.systems.'
                'novadriver.memoize.PersistentDict')
    def test_make_persistent_safe_handles_race_condition(
            self, mock_persistent_dict_class):
        """Test _make_persistent_safe handles concurrent init"""
        import sqlite3

        # Create a mock PersistentDict instance
        mock_dict = mock.Mock()

        # Simulate OperationalError on make_permanent (race condition)
        mock_dict.make_permanent.side_effect = sqlite3.OperationalError(
            'database is locked')

        # Create a mock logger
        mock_logger = mock.MagicMock()

        # Call _make_persistent_safe
        OpenStackDriver._make_persistent_safe(
            mock_dict, '/var/lib/sushy', 'test_storage', mock_logger)

        # Verify make_permanent was called
        mock_dict.make_permanent.assert_called_once_with(
            '/var/lib/sushy', 'test_storage')

        # Verify warning was logged with correct arguments
        mock_logger.warning.assert_called_once_with(
            'PersistentDict initialization warning for %s: %s. '
            'This is normal in multi-worker environments.',
            'test_storage',
            mock.ANY
        )

    @mock.patch('sushy_tools.emulator.resources.systems.'
                'novadriver.memoize.PersistentDict')
    def test_init_rescue_persistent_storage_partial_failure(
            self, mock_persistent_dict_class):
        """Test init continues if some make_permanent calls fail"""
        import sqlite3

        # Create mock PersistentDict instances
        mock_boot_modes = mock.Mock()
        mock_vmedia_images = mock.Mock()
        mock_vmedia_attrs = mock.Mock()

        # First dict succeeds, second fails, third succeeds
        mock_boot_modes.make_permanent.return_value = None
        mock_vmedia_images.make_permanent.side_effect = (
            sqlite3.OperationalError('database is locked'))
        mock_vmedia_attrs.make_permanent.return_value = None

        # Return different mocks for each instantiation
        mock_persistent_dict_class.side_effect = [
            mock_boot_modes, mock_vmedia_images, mock_vmedia_attrs]

        config = {
            'SUSHY_EMULATOR_OS_RESCUE_PXE_BOOT': True,
            'SUSHY_EMULATOR_OS_VMEDIA_USE_RESCUE': True,
            'SUSHY_EMULATOR_STATE_DIR': '/var/lib/sushy',
            'SUSHY_EMULATOR_OS_VMEDIA_RESCUE_DEVICE': 'cdrom',
            'SUSHY_EMULATOR_OS_VMEDIA_RESCUE_BUS': 'sata'
        }
        mock_logger = mock.MagicMock()

        # Initialize - should not raise exception
        OpenStackDriver.initialize(config, mock_logger, 'fake-cloud')

        # Verify all three PersistentDicts were created
        self.assertEqual(3, mock_persistent_dict_class.call_count)

        # Verify all three make_permanent calls were attempted
        mock_boot_modes.make_permanent.assert_called_once()
        mock_vmedia_images.make_permanent.assert_called_once()
        mock_vmedia_attrs.make_permanent.assert_called_once()

        # Verify warning was logged for the failed one
        warning_calls = [
            call for call in mock_logger.warning.call_args_list
            if 'rescue_vmedia_images' in str(call)]
        self.assertEqual(1, len(warning_calls))

    @mock.patch('time.sleep')
    def test_set_boot_device_cd_sets_persistent_storage(self, mock_sleep):
        """Test setting boot device to CD stores in PersistentDict"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        compute = self.nova_mock.return_value.compute

        # Verify rescue vmedia is enabled
        self.assertTrue(test_driver._rescue_vmedia_enabled)

        # Set boot device to CD
        test_driver.set_boot_device(self.uuid, 'Cd')

        # Should store in PersistentDict
        self.assertEqual('cdrom',
                         test_driver._rescue_boot_modes.get(self.uuid))

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
    def test_get_boot_device_cd_from_persistent_storage(self, mock_sleep):
        """Test get_boot_device returns CD from PersistentDict"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='RESCUED')
        self.nova_mock.return_value.get_server.return_value = server

        # Set boot mode in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'

        boot_device = test_driver.get_boot_device(self.uuid)

        self.assertEqual('Cd', boot_device)

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

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_stores_in_persistent_dict(self, mock_b64e):
        """Test insert_image stores image ID in PersistentDict"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(id='vmedia-image-id', name='test.iso',
                          status='active')
        self._cc.image.create_image.return_value = image
        self._cc.image.get_image.return_value = image

        # Mock get_boot_mode to return UEFI
        with mock.patch.object(test_driver, 'get_boot_mode',
                               return_value='UEFI'):
            # Insert image
            test_driver._insert_image(self.uuid, 'http://example.com/test.iso')

        # Should store image ID in PersistentDict
        self.assertEqual('vmedia-image-id',
                         test_driver._rescue_vmedia_images.get(self.uuid))

        # Should store vmedia attributes
        vmedia_attrs = test_driver._rescue_vmedia_attrs.get(self.uuid)
        self.assertIsNotNone(vmedia_attrs)
        self.assertEqual('http://example.com/test.iso',
                         vmedia_attrs.get('image_url'))

        # Should call import_image with web-download
        self._cc.image.import_image.assert_called_once()

        # Should create image with rescue properties
        create_call = self._cc.image.create_image.call_args
        self.assertIn('properties', create_call.kwargs)
        props = create_call.kwargs['properties']
        self.assertEqual('cdrom', props.get('hw_rescue_device'))
        self.assertEqual('scsi', props.get('hw_rescue_bus'))
        self.assertEqual('uefi', props.get('hw_firmware_type'))

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_with_local_file(self, mock_b64e):
        """Test insert_image with local file path"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(id='vmedia-image-id', name='test.iso',
                          status='active')
        self._cc.image.create_image.return_value = image
        self._cc.image.get_image.return_value = image

        # Mock get_boot_mode to return Legacy
        with mock.patch.object(test_driver, 'get_boot_mode',
                               return_value='Legacy'):
            # Insert image with local file
            test_driver._insert_image(
                self.uuid, 'http://example.com/test.iso',
                local_file_path='/tmp/test.iso')

        # Should store image ID and local file path
        vmedia_attrs = test_driver._rescue_vmedia_attrs.get(self.uuid)
        self.assertEqual('/tmp/test.iso', vmedia_attrs.get('local_file_path'))

        # Should create image with filename
        create_call = self._cc.image.create_image.call_args
        self.assertEqual('/tmp/test.iso', create_call.kwargs.get('filename'))

        # Should NOT call import_image (local file upload)
        self._cc.image.import_image.assert_not_called()

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_with_cd_boot_triggers_rescue(
            self, mock_sleep, mock_check_wait):
        """Test power on with CD boot mode uses rescue with vmedia image"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode and image ID in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock image status check
        image = mock.Mock(id='vmedia-image-id', status='active')
        self._cc.image.get_image.return_value = image

        # Mock _check_and_wait_for_task_state:
        # First call (in set_power_state): ready
        # Second call (in _rescue_with_vmedia_image): not ready (triggers 503)
        mock_check_wait.side_effect = [(True, server), (False, server)]

        # Power on should trigger rescue, wait, then 503 if not ready
        e = self.assertRaises(
            error.FishyError,
            test_driver.set_power_state, self.uuid, 'ForceOn')

        self.assertEqual(503, e.code)
        self.assertIn('entering rescue mode', str(e))
        compute.rescue_server.assert_called_once_with(
            self.uuid, image_ref='vmedia-image-id')
        # Called twice: once in set_power_state, once in
        # _rescue_with_vmedia_image
        self.assertEqual(2, mock_check_wait.call_count)

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_with_image_still_importing_raises_503(
            self, mock_sleep, mock_check_wait):
        """Test power on while image still importing raises 503"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Set boot mode and image ID in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock image status check - still importing
        image = mock.Mock(id='vmedia-image-id', status='importing')
        self._cc.image.get_image.return_value = image

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Power on should raise 503 due to image still importing
        e = self.assertRaises(
            error.FishyError,
            test_driver.set_power_state, self.uuid, 'ForceOn')

        self.assertEqual(503, e.code)
        self.assertIn('still importing', str(e))

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_with_image_queued_raises_503(
            self, mock_sleep, mock_check_wait):
        """Test power on while image queued raises 503"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Set boot mode and image ID in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock image status check - queued
        image = mock.Mock(id='vmedia-image-id', status='queued')
        self._cc.image.get_image.return_value = image

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Power on should raise 503 due to image queued
        e = self.assertRaises(
            error.FishyError,
            test_driver.set_power_state, self.uuid, 'ForceOn')

        self.assertEqual(503, e.code)
        self.assertIn('still importing', str(e))

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_with_image_failed_raises_500(
            self, mock_sleep, mock_check_wait):
        """Test power on with failed image import raises 500"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Set boot mode and image ID in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock image status check - failed
        image = mock.Mock(id='vmedia-image-id', status='killed')
        self._cc.image.get_image.return_value = image

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Power on should raise 500 due to image import failed
        e = self.assertRaises(
            error.FishyError,
            test_driver.set_power_state, self.uuid, 'ForceOn')

        self.assertEqual(500, e.code)
        self.assertIn('import failed', str(e))

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_without_image_raises_error(
            self, mock_sleep, mock_check_wait):
        """Test power on with CD boot but no image inserted raises error"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Set boot mode but NO image ID in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Power on should raise error due to no image inserted
        e = self.assertRaises(
            error.FishyError,
            test_driver.set_power_state, self.uuid, 'ForceOn')

        self.assertIn('No virtual media image inserted', str(e))

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
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock _check_and_wait_for_task_state to always indicate ready
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
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Restart
        test_driver.set_power_state(self.uuid, 'ForceRestart')

        # Should only reboot, not unrescue or re-rescue
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='HARD')
        compute.unrescue_server.assert_not_called()
        compute.rescue_server.assert_not_called()

    def test_eject_image_clears_persistent_dict(self):
        """Test eject_image clears PersistentDict entries"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='RESCUED', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Set up vmedia state
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'
        test_driver._rescue_vmedia_attrs[self.uuid] = {
            'image_url': 'http://example.com/test.iso'
        }

        # Mock image find
        image = mock.Mock(id='vmedia-image-id')
        self._cc.image.find_image.return_value = image

        # Eject image
        test_driver._eject_image(self.uuid)

        # Should delete image from Glance
        self._cc.delete_image.assert_called_once_with('vmedia-image-id')

        # Should clear PersistentDict entries
        self.assertIsNone(test_driver._rescue_vmedia_images.get(self.uuid))
        self.assertIsNone(test_driver._rescue_vmedia_attrs.get(self.uuid))

    def test_eject_image_with_no_image_is_noop(self):
        """Test eject_image when no image inserted is a no-op"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # No image in PersistentDict

        # Eject image should be a no-op
        test_driver._eject_image(self.uuid)

        # Should NOT call delete_image
        self._cc.delete_image.assert_not_called()

    @mock.patch('base64.urlsafe_b64encode')
    def test_eject_image_with_local_file_deletes_file(self, mock_b64e):
        """Test eject_image with local file deletes the file"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Set up vmedia state with local file
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'
        test_driver._rescue_vmedia_attrs[self.uuid] = {
            'image_url': 'http://example.com/test.iso',
            'local_file_path': '/tmp/test.iso'
        }

        # Mock image find
        image = mock.Mock(id='vmedia-image-id')
        self._cc.image.find_image.return_value = image

        # Mock _delete_local_file
        with mock.patch.object(test_driver,
                               '_delete_local_file') as mock_delete:
            # Eject image
            test_driver._eject_image(self.uuid)

            # Should delete local file
            mock_delete.assert_called_once_with('/tmp/test.iso')

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_already_in_rescue_with_cd_boot(
            self, mock_sleep, mock_check_wait):
        """Test power on when already in rescue with CD boot is a no-op"""
        test_driver = self._create_driver()

        # Instance is already in rescue mode and powered on
        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode to CD (rescue)
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

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

        # Instance starts in rescue mode but stopped
        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='RESCUED',
            task_state=None, status='ACTIVE')
        self.nova_mock.return_value.get_server.return_value = server
        compute = self.nova_mock.return_value.compute

        # Track fetch calls to simulate state transition
        fetch_count = [0]

        def fetch_side_effect(compute_arg):
            fetch_count[0] += 1
            # After unrescue completes, vm_state becomes ACTIVE
            # and instance is stopped (power_state=0)
            if fetch_count[0] >= 2:
                server.vm_state = 'ACTIVE'
                server.power_state = 0  # Stopped initially
            # After start_server is called, power_state becomes ON
            if compute.start_server.called:
                server.power_state = 1

        server.fetch.side_effect = fetch_side_effect

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

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_interaction_between_pxe_and_cd_boot_modes(
            self, mock_sleep, mock_check_wait):
        """Test switching between PXE and CD boot modes

        Verify that setting boot device to CD after PXE (or vice versa)
        properly updates the boot mode and triggers the correct rescue
        operation.
        """
        # This test requires both rescue PXE and rescue vmedia enabled
        config = {
            'SUSHY_EMULATOR_OS_RESCUE_PXE_BOOT': True,
            'SUSHY_EMULATOR_OS_RESCUE_PXE_IMAGE_BIOS': 'ipxe-bios',
            'SUSHY_EMULATOR_OS_RESCUE_PXE_IMAGE_UEFI': 'ipxe-uefi',
            'SUSHY_EMULATOR_OS_VMEDIA_USE_RESCUE': True,
            'SUSHY_EMULATOR_OS_VMEDIA_RESCUE_DEVICE': 'cdrom',
            'SUSHY_EMULATOR_OS_VMEDIA_RESCUE_BUS': 'scsi'
        }

        test_driver_class = OpenStackDriver.initialize(
            config, mock.MagicMock(), 'fake-cloud')

        # Replace PersistentDict with plain dict for tests
        test_driver_class._rescue_boot_modes = {}
        test_driver_class._rescue_vmedia_images = {}
        test_driver_class._rescue_vmedia_attrs = {}

        test_driver = test_driver_class()
        test_driver._futures.clear()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Set boot device to PXE
        test_driver.set_boot_device(self.uuid, 'Pxe')
        self.assertEqual('pxe', test_driver._rescue_boot_modes[self.uuid])

        # Switch to CD boot
        test_driver.set_boot_device(self.uuid, 'Cd')
        self.assertEqual('cdrom', test_driver._rescue_boot_modes[self.uuid])

        # Switch back to PXE
        test_driver.set_boot_device(self.uuid, 'Pxe')
        self.assertEqual('pxe', test_driver._rescue_boot_modes[self.uuid])

        # Switch to disk
        test_driver.set_boot_device(self.uuid, 'Hdd')
        self.assertEqual('disk', test_driver._rescue_boot_modes[self.uuid])

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_failure_cleanup(self, mock_b64e):
        """Test insert_image cleans up on failure"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(id='vmedia-image-id', name='test.iso')
        self._cc.image.create_image.return_value = image

        # Mock import_image to raise exception
        self._cc.image.import_image.side_effect = Exception('Import failed')

        # Mock get_boot_mode
        with mock.patch.object(test_driver, 'get_boot_mode',
                               return_value='UEFI'):
            # Insert image should raise error
            self.assertRaises(
                error.FishyError,
                test_driver._insert_image,
                self.uuid, 'http://example.com/test.iso')

        # Should clean up image
        self._cc.delete_image.assert_called_once_with('vmedia-image-id')

        # Should NOT store in PersistentDict
        self.assertIsNone(test_driver._rescue_vmedia_images.get(self.uuid))

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_with_cd_boot_success(self, mock_sleep, mock_check_wait):
        """Test successful power on with CD boot completes rescue"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'}, status='ACTIVE')
        self.nova_mock.return_value.get_server.return_value = server
        compute = self.nova_mock.return_value.compute

        # Simulate power state change after rescue: OFF -> ON
        fetch_count = [0]

        def fetch_side_effect(*args):
            fetch_count[0] += 1
            # After rescue_server is called, instance powers on
            if compute.rescue_server.called:
                server.power_state = 1
                server.vm_state = 'RESCUED'

        server.fetch.side_effect = fetch_side_effect

        # Set boot mode and image ID in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock image status check
        image = mock.Mock(id='vmedia-image-id', status='active')
        self._cc.image.get_image.return_value = image

        # Mock _check_and_wait_for_task_state to indicate ready both times
        mock_check_wait.return_value = (True, server)

        # Power on should trigger rescue and succeed
        test_driver.set_power_state(self.uuid, 'ForceOn')

        # Should call rescue_server with correct image
        compute.rescue_server.assert_called_once_with(
            self.uuid, image_ref='vmedia-image-id')
        # Called three times: once in set_power_state, once in
        # _rescue_with_vmedia_image, once in _wait_for_power_state_stable
        self.assertEqual(3, mock_check_wait.call_count)

    def test_eject_image_sets_boot_mode_to_disk(self):
        """Test eject_image sets boot mode back to disk"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='RESCUED', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Set up vmedia state with CD boot mode
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'
        test_driver._rescue_vmedia_attrs[self.uuid] = {
            'image_url': 'http://example.com/test.iso'
        }

        # Mock image find
        image = mock.Mock(id='vmedia-image-id')
        self._cc.image.find_image.return_value = image

        # Eject image
        test_driver._eject_image(self.uuid)

        # Boot mode should be set back to disk
        self.assertEqual('disk', test_driver._rescue_boot_modes[self.uuid])

    def test_eject_image_while_in_rescue_does_not_unrescue(self):
        """Test eject_image while in RESCUED state doesn't trigger unrescue

        Ejecting media should only clear state and set boot mode to disk.
        The instance remains in RESCUED state until next power cycle.
        """
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='RESCUED', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        compute = self.nova_mock.return_value.compute

        # Set up vmedia state
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'
        test_driver._rescue_vmedia_attrs[self.uuid] = {
            'image_url': 'http://example.com/test.iso'
        }

        # Mock image find
        image = mock.Mock(id='vmedia-image-id')
        self._cc.image.find_image.return_value = image

        # Eject image
        test_driver._eject_image(self.uuid)

        # Should NOT call unrescue_server
        compute.unrescue_server.assert_not_called()

        # Boot mode should be set to disk
        self.assertEqual('disk', test_driver._rescue_boot_modes[self.uuid])

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_restart_with_cd_boot_from_stopped_is_noop(
            self, mock_sleep, mock_check_wait):
        """Test restart with CD boot from stopped state is a no-op

        Restart operations only work when power_state=1 (powered on).
        If instance is stopped (power_state=0), restart is a no-op.
        """
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode and image ID in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock image status check
        image = mock.Mock(id='vmedia-image-id', status='active')
        self._cc.image.get_image.return_value = image

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Restart from stopped should be a no-op
        test_driver.set_power_state(self.uuid, 'ForceRestart')

        # Should NOT call rescue_server or reboot_server (not powered on)
        compute.rescue_server.assert_not_called()
        compute.reboot_server.assert_not_called()

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_graceful_shutdown_in_rescue_unrescues_then_stops(
            self, mock_sleep, mock_check_wait):
        """Test graceful shutdown while in rescue mode unrescues then stops"""
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
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock _check_and_wait_for_task_state to always indicate ready
        mock_check_wait.return_value = (True, server)

        # Graceful shutdown
        test_driver.set_power_state(self.uuid, 'GracefulShutdown')

        # Should unrescue first, then stop
        compute.unrescue_server.assert_called_once_with(self.uuid)
        compute.stop_server.assert_called_once_with(self.uuid)

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_graceful_restart_in_rescue_preserves_rescue(
            self, mock_sleep, mock_check_wait):
        """Test graceful restart while in rescue preserves RESCUED state"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Graceful restart
        test_driver.set_power_state(self.uuid, 'GracefulRestart')

        # Should only reboot, not unrescue or re-rescue
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='SOFT')
        compute.unrescue_server.assert_not_called()
        compute.rescue_server.assert_not_called()

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_does_not_set_boot_mode(self, mock_b64e):
        """Test insert_image does not automatically set boot mode

        Boot mode must be set explicitly via set_boot_device('Cd').
        Insert_image only uploads the ISO and stores the image ID.
        """
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(id='vmedia-image-id', name='test.iso',
                          status='active')
        self._cc.image.create_image.return_value = image
        self._cc.image.get_image.return_value = image

        # Mock get_boot_mode to return UEFI
        with mock.patch.object(test_driver, 'get_boot_mode',
                               return_value='UEFI'):
            # Insert image
            test_driver._insert_image(self.uuid, 'http://example.com/test.iso')

        # Boot mode should NOT be automatically set by insert_image
        # It must be set explicitly via set_boot_device
        self.assertIsNone(test_driver._rescue_boot_modes.get(self.uuid))

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_with_legacy_boot_mode(self, mock_b64e):
        """Test insert_image with Legacy boot mode (BIOS)"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(id='vmedia-image-id', name='test.iso',
                          status='active')
        self._cc.image.create_image.return_value = image
        self._cc.image.get_image.return_value = image

        # Mock get_boot_mode to return Legacy (BIOS)
        with mock.patch.object(test_driver, 'get_boot_mode',
                               return_value='Legacy'):
            # Insert image
            test_driver._insert_image(self.uuid, 'http://example.com/test.iso')

        # Should create image without hw_firmware_type property
        create_call = self._cc.image.create_image.call_args
        self.assertIn('properties', create_call.kwargs)
        props = create_call.kwargs['properties']
        self.assertEqual('cdrom', props.get('hw_rescue_device'))
        self.assertEqual('scsi', props.get('hw_rescue_bus'))
        # Should NOT have hw_firmware_type for Legacy boot
        self.assertNotIn('hw_firmware_type', props)

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_with_none_boot_mode(self, mock_b64e):
        """Test insert_image with None boot mode (no image/volume)"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(id='vmedia-image-id', name='test.iso',
                          status='active')
        self._cc.image.create_image.return_value = image
        self._cc.image.get_image.return_value = image

        # Mock get_boot_mode to return None
        with mock.patch.object(test_driver, 'get_boot_mode',
                               return_value=None):
            # Insert image
            test_driver._insert_image(self.uuid, 'http://example.com/test.iso')

        # Should create image without hw_firmware_type property
        create_call = self._cc.image.create_image.call_args
        self.assertIn('properties', create_call.kwargs)
        props = create_call.kwargs['properties']
        self.assertEqual('cdrom', props.get('hw_rescue_device'))
        self.assertEqual('scsi', props.get('hw_rescue_bus'))
        # Should NOT have hw_firmware_type for None boot mode
        self.assertNotIn('hw_firmware_type', props)

    def test_eject_image_when_image_not_found_in_glance(self):
        """Test eject_image when image is not found in Glance"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Set up vmedia state
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'
        test_driver._rescue_vmedia_attrs[self.uuid] = {
            'image_url': 'http://example.com/test.iso'
        }

        # Mock image find to return None (image not found)
        self._cc.image.find_image.return_value = None

        # Eject image should raise error
        e = self.assertRaises(
            error.FishyError,
            test_driver._eject_image,
            self.uuid)

        self.assertIn('Image not found in image service', str(e))

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_when_already_on_is_noop(
            self, mock_sleep, mock_check_wait):
        """Test power on when already powered on is a no-op

        If instance is already powered on (power_state=1), power on
        operation should be a no-op regardless of vm_state.
        """
        test_driver = self._create_driver()

        # Instance is powered on in ACTIVE state
        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='ACTIVE',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode to CD
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock image status check
        image = mock.Mock(id='vmedia-image-id', status='active')
        self._cc.image.get_image.return_value = image

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Power on should be a no-op (already powered on)
        test_driver.set_power_state(self.uuid, 'ForceOn')

        # Should NOT call rescue_server or start_server
        compute.rescue_server.assert_not_called()
        compute.start_server.assert_not_called()

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_with_cd_boot_when_busy_raises_503(
            self, mock_sleep, mock_check_wait):
        """Test power on with CD boot when instance is busy raises 503"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state='spawning', image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Set boot mode and image ID in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock _check_and_wait_for_task_state to indicate not ready
        mock_check_wait.return_value = (False, server)

        # Power on should raise 503 due to busy state
        e = self.assertRaises(
            error.FishyError,
            test_driver.set_power_state, self.uuid, 'ForceOn')

        self.assertEqual(503, e.code)
        self.assertIn('SYS518', str(e))

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_off_from_rescue_when_unrescue_not_ready_raises_503(
            self, mock_sleep, mock_check_wait):
        """Test power off from rescue when unrescue not ready raises 503"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock _check_and_wait_for_task_state:
        # First call (in set_power_state): ready
        # Second call (in _unrescue_before_power_operation): not ready
        mock_check_wait.side_effect = [(True, server), (False, server)]

        # Power off should raise 503 when unrescue not ready
        e = self.assertRaises(
            error.FishyError,
            test_driver.set_power_state, self.uuid, 'ForceOff')

        self.assertEqual(503, e.code)
        self.assertIn('SYS518', str(e))
        # Should call unrescue_server
        compute.unrescue_server.assert_called_once_with(self.uuid)
        # Should NOT call stop_server since unrescue not ready
        compute.stop_server.assert_not_called()

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_future_already_running(self, mock_b64e):
        """Test insert_image when a future is already running raises error"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        # Set up a running future
        mock_future = mock.Mock()
        mock_future.running.return_value = True
        test_driver._futures[self.uuid] = mock_future

        # Insert image should raise error
        e = self.assertRaises(
            error.FishyError,
            test_driver.insert_image,
            self.uuid, 'http://example.com/test.iso')

        self.assertIn('already in progress', str(e))

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_previous_future_failed(self, mock_b64e):
        """Test insert_image when previous future failed raises that error"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        # Set up a failed future
        mock_future = mock.Mock()
        mock_future.running.return_value = False
        previous_error = error.FishyError('Previous operation failed')
        mock_future.exception.return_value = previous_error
        test_driver._futures[self.uuid] = mock_future

        # Insert image should raise the previous error
        e = self.assertRaises(
            error.FishyError,
            test_driver.insert_image,
            self.uuid, 'http://example.com/test.iso')

        self.assertEqual('Previous operation failed', str(e))

    def test_eject_image_future_already_running(self):
        """Test eject_image when a future is already running raises error"""
        test_driver = self._create_driver()

        # Set up a running future
        mock_future = mock.Mock()
        mock_future.running.return_value = True
        test_driver._futures[self.uuid] = mock_future

        # Eject image should raise error
        e = self.assertRaises(
            error.FishyError,
            test_driver.eject_image,
            self.uuid)

        self.assertIn('already in progress', str(e))

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_with_cd_boot_from_rescued_with_different_image(
            self, mock_sleep, mock_check_wait):
        """Test power on when already in rescue but with different image

        This scenario shouldn't happen in normal operation, but we should
        verify the behavior is correct.
        """
        test_driver = self._create_driver()

        # Instance is already in rescue mode
        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None
        compute = self.nova_mock.return_value.compute

        # Set boot mode to CD with a vmedia image
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Power on should be a no-op (already in rescue and powered on)
        test_driver.set_power_state(self.uuid, 'ForceOn')

        # Should NOT call rescue_server or start_server
        compute.rescue_server.assert_not_called()
        compute.start_server.assert_not_called()

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_restart_from_active_with_cd_boot_triggers_rescue_and_reboot(
            self, mock_sleep, mock_check_wait):
        """Test restart from ACTIVE with CD boot triggers rescue then reboot"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='ACTIVE',
            task_state=None, image={'id': 'image-id'}, status='ACTIVE')
        self.nova_mock.return_value.get_server.return_value = server
        compute = self.nova_mock.return_value.compute

        # Simulate state changes: rescue powers on, reboot maintains power on
        def fetch_side_effect(*args):
            # After rescue_server is called, instance stays powered on
            if compute.rescue_server.called:
                server.power_state = 1
                server.vm_state = 'RESCUED'

        server.fetch.side_effect = fetch_side_effect

        # Set boot mode to CD
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock image status check
        image = mock.Mock(id='vmedia-image-id', status='active')
        self._cc.image.get_image.return_value = image

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Restart should rescue then reboot
        test_driver.set_power_state(self.uuid, 'ForceRestart')

        # Should call rescue_server first (transition ACTIVE -> RESCUED)
        compute.rescue_server.assert_called_once_with(
            self.uuid, image_ref='vmedia-image-id')
        # Should call reboot_server to complete restart
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='HARD')

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_restart_from_rescued_with_disk_boot_unrescues_and_reboots(
            self, mock_sleep, mock_check_wait):
        """Test restart from RESCUED with disk boot unrescues and reboots"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Track fetch calls to simulate state transition
        fetch_count = [0]

        def fetch_side_effect(compute):
            fetch_count[0] += 1
            # After unrescue, vm_state becomes ACTIVE
            if fetch_count[0] >= 2:
                server.vm_state = 'ACTIVE'

        server.fetch.side_effect = fetch_side_effect
        compute = self.nova_mock.return_value.compute

        # Set boot mode to disk
        test_driver._rescue_boot_modes[self.uuid] = 'disk'

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Restart should unrescue, then reboot
        test_driver.set_power_state(self.uuid, 'ForceRestart')

        # Should call unrescue_server first
        compute.unrescue_server.assert_called_once_with(self.uuid)
        # Should call reboot_server (not stop/start)
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='HARD')
        # Should NOT call stop_server or start_server
        compute.stop_server.assert_not_called()
        compute.start_server.assert_not_called()

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_with_qcow2_format(self, mock_b64e):
        """Test insert_image with QCOW2 format image"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(id='vmedia-image-id', name='test.qcow2',
                          status='active')
        self._cc.image.create_image.return_value = image
        self._cc.image.get_image.return_value = image

        # Mock get_boot_mode to return UEFI
        with mock.patch.object(test_driver, 'get_boot_mode',
                               return_value='UEFI'):
            # Insert image with qcow2 format
            test_driver._insert_image(
                self.uuid, 'http://example.com/test.qcow2')

        # Should create image with qcow2 disk format
        create_call = self._cc.image.create_image.call_args
        self.assertEqual('qcow2', create_call.kwargs.get('disk_format'))

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_get_power_state_in_rescue_with_vmedia(self, mock_sleep,
                                                   mock_check_wait):
        """Test get_power_state works correctly when in rescue with vmedia"""
        test_driver = self._create_driver()

        # Instance is in rescue mode and powered on
        server = mock.Mock(
            id=self.uuid, power_state=1, vm_state='RESCUED',
            task_state=None)
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Set boot mode to CD
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Get power state
        power_state = test_driver.get_power_state(self.uuid)

        # Should return 'On' based on power_state=1
        self.assertEqual('On', power_state)

    @mock.patch.object(OpenStackDriver, '_check_and_wait_for_task_state')
    @mock.patch('time.sleep')
    def test_power_on_with_cd_boot_and_error_image_status(
            self, mock_sleep, mock_check_wait):
        """Test power on with CD boot when image status is error"""
        test_driver = self._create_driver()

        server = mock.Mock(
            id=self.uuid, power_state=0, vm_state='STOPPED',
            task_state=None, image={'id': 'image-id'})
        self.nova_mock.return_value.get_server.return_value = server
        server.fetch.return_value = None

        # Set boot mode and image ID in PersistentDict
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'

        # Mock image status check - error status
        image = mock.Mock(id='vmedia-image-id', status='error')
        self._cc.image.get_image.return_value = image

        # Mock _check_and_wait_for_task_state to indicate ready
        mock_check_wait.return_value = (True, server)

        # Power on should raise 500 due to image error
        e = self.assertRaises(
            error.FishyError,
            test_driver.set_power_state, self.uuid, 'ForceOn')

        self.assertEqual(500, e.code)
        self.assertIn('import failed', str(e))
        self.assertIn('error', str(e))

    @mock.patch('base64.urlsafe_b64encode')
    def test_insert_image_with_local_file_cleanup_on_failure(self,
                                                             mock_b64e):
        """Test insert_image with local file cleans up file on failure"""
        test_driver = self._create_driver()
        mock_b64e.return_value = b'unique'

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(id='vmedia-image-id', name='test.iso')
        self._cc.image.create_image.return_value = image

        # Mock create_image to raise exception (simulate upload failure)
        self._cc.image.create_image.side_effect = Exception('Upload failed')

        # Mock get_boot_mode and _delete_local_file
        with mock.patch.object(test_driver, 'get_boot_mode',
                               return_value='UEFI'):
            with mock.patch.object(test_driver,
                                   '_delete_local_file') as mock_delete:
                # Insert image with local file should raise error
                self.assertRaises(
                    error.FishyError,
                    test_driver._insert_image,
                    self.uuid, 'http://example.com/test.iso',
                    local_file_path='/tmp/test.iso')

                # Should attempt to delete local file on cleanup
                mock_delete.assert_called_once_with('/tmp/test.iso')

    def test_eject_image_clears_boot_mode_to_disk(self):
        """Test eject_image sets boot mode to disk after clearing vmedia"""
        test_driver = self._create_driver()

        server = mock.Mock(id=self.uuid, vm_state='ACTIVE', task_state=None)
        self.nova_mock.return_value.get_server.return_value = server

        # Set up vmedia state with CD boot mode
        test_driver._rescue_boot_modes[self.uuid] = 'cdrom'
        test_driver._rescue_vmedia_images[self.uuid] = 'vmedia-image-id'
        test_driver._rescue_vmedia_attrs[self.uuid] = {
            'image_url': 'http://example.com/test.iso'
        }

        # Mock image find
        image = mock.Mock(id='vmedia-image-id')
        self._cc.image.find_image.return_value = image

        # Eject image
        test_driver._eject_image(self.uuid)

        # Boot mode should be set to disk
        self.assertEqual('disk', test_driver._rescue_boot_modes[self.uuid])

        # PersistentDict should be cleared
        self.assertIsNone(test_driver._rescue_vmedia_images.get(self.uuid))
        self.assertIsNone(test_driver._rescue_vmedia_attrs.get(self.uuid))
