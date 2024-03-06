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

        power_state = self.test_driver.get_power_state(self.uuid)

        self.assertEqual('On', power_state)

    def test_get_power_state_off(self):
        server = mock.Mock(id=self.uuid,
                           power_state=0)
        self.nova_mock.return_value.get_server.return_value = server

        power_state = self.test_driver.get_power_state(self.uuid)

        self.assertEqual('Off', power_state)

    def test_set_power_state_on(self):
        server = mock.Mock(id=self.uuid, power_state=0)
        self.nova_mock.return_value.get_server.return_value = server
        self.test_driver.set_power_state(self.uuid, 'On')
        compute = self.nova_mock.return_value.compute
        compute.start_server.assert_called_once_with(self.uuid)

    def test_set_power_state_forceon(self):
        server = mock.Mock(id=self.uuid, power_state=0)
        self.nova_mock.return_value.get_server.return_value = server
        self.test_driver.set_power_state(self.uuid, 'ForceOn')
        compute = self.nova_mock.return_value.compute
        compute.start_server.assert_called_once_with(self.uuid)

    def test_set_power_state_forceoff(self):
        server = mock.Mock(id=self.uuid, power_state=1)
        self.nova_mock.return_value.get_server.return_value = server
        self.test_driver.set_power_state(self.uuid, 'ForceOff')
        compute = self.nova_mock.return_value.compute
        compute.stop_server.assert_called_once_with(self.uuid)

    def test_set_power_state_gracefulshutdown(self):
        server = mock.Mock(id=self.uuid, power_state=1)
        self.nova_mock.return_value.get_server.return_value = server
        self.test_driver.set_power_state(self.uuid, 'GracefulShutdown')
        compute = self.nova_mock.return_value.compute
        compute.stop_server.assert_called_once_with(self.uuid)

    def test_set_power_state_gracefulrestart(self):
        server = mock.Mock(id=self.uuid, power_state=1)
        self.nova_mock.return_value.get_server.return_value = server
        self.test_driver.set_power_state(self.uuid, 'GracefulRestart')
        compute = self.nova_mock.return_value.compute
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='SOFT')

    def test_set_power_state_forcerestart(self):
        server = mock.Mock(id=self.uuid, power_state=1)
        self.nova_mock.return_value.get_server.return_value = server
        self.test_driver.set_power_state(
            self.uuid, 'ForceRestart')
        compute = self.nova_mock.return_value.compute
        compute.reboot_server.assert_called_once_with(
            self.uuid, reboot_type='HARD')

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

        image = mock.Mock(hw_firmware_type='bios')

        self.nova_mock.return_value.image.find_image.return_value = image

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertEqual('Legacy', boot_mode)

    def test_get_boot_mode_no_image(self):
        server = mock.Mock(id=self.uuid, image=dict(id=self.uuid))
        self.nova_mock.return_value.get_server.return_value = server

        self.nova_mock.return_value.image.find_image.return_value = None

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertIsNone(boot_mode)

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

        image = mock.Mock()

        self.nova_mock.return_value.image.find_image.return_value = image

        self.assertFalse(self.test_driver.get_secure_boot(self.uuid))

    def test_get_secure_boot_on(self):
        server = mock.Mock(id=self.uuid, image=dict(id=self.uuid))
        self.nova_mock.return_value.get_server.return_value = server

        image = mock.Mock(os_secure_boot='required')

        self.nova_mock.return_value.image.find_image.return_value = image

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

    @mock.patch.object(base64, 'urlsafe_b64encode', autospec=True)
    def test_insert_image(self, mock_b64e):
        mock_b64e.return_value = b'0hIwh_vN'
        mock_server = mock.Mock()
        mock_server.flavor.disk = 20
        mock_server.name = 'node01'
        queued_image = mock.Mock(id='aaa-bbb')
        self._cc.image.create_image.return_value = queued_image
        self._cc.compute.get_server.return_value = mock_server
        self._cc.block_storage.create_volume.return_value = mock.Mock(
            id='ccc-ddd')

        image_id, image_name = self.test_driver.insert_image(
            self.uuid, 'http://fish.it/red.iso')

        self._cc.image.create_image.assert_called_once_with(
            name='red.iso 0hIwh_vN', disk_format='raw',
            container_format='bare', visibility='private')
        self._cc.compute.get_server.assert_called_once_with(self.uuid)
        self._cc.block_storage.create_volume.assert_called_once_with(
            size=20, name='node01')
        self._cc.image.import_image.assert_called_once_with(
            queued_image, method='web-download', uri='http://fish.it/red.iso')

        self.assertEqual('aaa-bbb', image_id)

    def test_insert_image_fail(self):
        mock_server = mock.Mock()
        mock_server.flavor.disk = 20
        mock_server.name = 'node01'
        self._cc.image.create_image.return_value = mock.Mock(id='aaa-bbb')
        self._cc.compute.get_server.return_value = mock_server
        self._cc.block_storage.create_volume.return_value = mock.Mock(
            id='ccc-ddd')

        self._cc.image.create_image.side_effect = Exception('ouch')

        e = self.assertRaises(
            error.FishyError, self.test_driver.insert_image,
            self.uuid, 'http://fish.it/red.iso')
        self.assertEqual(
            'Failed insert image from URL http://fish.it/red.iso: ouch',
            str(e))

    def test_insert_image_future_running(self):

        mock_future = mock.Mock()
        mock_future.running.return_value = True
        self.test_driver._futures[self.uuid] = mock_future
        e = self.assertRaises(
            error.FishyError, self.test_driver.insert_image,
            self.uuid, 'http://fish.it/red.iso')
        self.assertEqual(
            'An insert or eject operation is already in progress for '
            'c7a5fdbd-cdaf-9455-926a-d65c16db1809', str(e))

    def test_insert_image_future_exception(self):

        mock_future = mock.Mock()
        mock_future.running.return_value = False
        mock_future.exception.return_value = error.FishyError('ouch')
        self.test_driver._futures[self.uuid] = mock_future
        e = self.assertRaises(
            error.FishyError, self.test_driver.insert_image,
            self.uuid, 'http://fish.it/red.iso')
        self.assertEqual('ouch', str(e))

    @mock.patch.object(time, 'sleep', autospec=True)
    def test_eject_image(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-volume': 'ccc-ddd'
        }
        self._cc.compute.get_server.return_value = mock_server

        available_volume = mock.Mock()
        available_volume.id = 'ccc-ddd'
        available_volume.status = 'available'
        available_volume.name = self.uuid
        in_use_volume = mock.Mock(id='ccc-ddd', status='in-use')
        self._cc.block_storage.get_volume.side_effect = [
            in_use_volume,
            mock.Mock(id='ccc-ddd', status='queued'),
            mock.Mock(id='ccc-ddd', status='detaching'),
            available_volume,
            mock.Mock(id='ccc-ddd', status='uploading'),
            available_volume
        ]
        self._cc.block_storage.upload_volume_to_image.return_value = {
            'image_id': 'aaa-bbb'}

        self.test_driver.eject_image(self.uuid)

        self._cc.compute.delete_volume_attachment(self.uuid, in_use_volume)
        self._cc.block_storage.upload_volume_to_image.assert_called_once_with(
            volume=available_volume, image_name=self.uuid, disk_format='raw',
            container_format='bare', visibility='private')

    @mock.patch.object(time, 'sleep', autospec=True)
    def test_eject_image_error_detach(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-volume': 'ccc-ddd'
        }
        self._cc.compute.get_server.return_value = mock_server
        self._cc.block_storage.get_volume.side_effect = [
            mock.Mock(id='ccc-ddd', status='in-use'),
            mock.Mock(id='ccc-ddd', status='queued'),
            mock.Mock(id='ccc-ddd', status='detaching'),
            mock.Mock(id='ccc-ddd', status='error'),
        ]

        e = self.assertRaises(
            error.FishyError, self.test_driver.eject_image,
            self.uuid)
        self.assertEqual('Volume detachment resulted in status error', str(e))

        self._cc.delete_image.assert_not_called()
        self._cc.block_storage.delete_volume.assert_not_called()

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_imported_image(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-volume': 'ccc-ddd'
        }
        self._cc.compute.get_server.return_value = mock_server
        queued_image = mock.Mock(id='aaa-bbb', status='queued')
        self._cc.image.get_image.side_effect = [
            queued_image,
            mock.Mock(id='aaa-bbb', status='importing'),
            mock.Mock(id='aaa-bbb', status='active'),
        ]
        available_volume = mock.Mock(id='ccc-ddd', status='available')
        self._cc.block_storage.get_volume.side_effect = [
            mock.Mock(id='ccc-ddd', status='creating'),
            available_volume,
            mock.Mock(id='ccc-ddd', status='reserved'),
            mock.Mock(id='ccc-ddd', status='attaching'),
            mock.Mock(id='ccc-ddd', status='in-use')
        ]
        self._cc.compute.rebuild_server.return_value = mock.Mock(
            status='REBUILD')
        self._cc.compute.get_server.side_effect = [
            mock.Mock(status='REBUILD'),
            mock.Mock(status='ACTIVE'),
        ]

        self.test_driver._rebuild_with_imported_image(
            self.uuid, 'aaa-bbb')

        self._cc.compute.create_volume_attachment.assert_called_once_with(
            self.uuid, available_volume, delete_on_termination=True)
        self._cc.compute.rebuild_server.assert_called_once_with(
            self.uuid, 'aaa-bbb')
        self._cc.delete_image.assert_called_once_with('aaa-bbb')
        self._cc.block_storage.delete_volume.assert_not_called()

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_imported_imaged_error_image(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-volume': 'ccc-ddd'
        }
        self._cc.block_storage.get_volume.side_effect = [
            mock.Mock(id='ccc-ddd', status='creating'),
            mock.Mock(id='ccc-ddd', status='available'),
            mock.Mock(id='ccc-ddd', status='reserved'),
            mock.Mock(id='ccc-ddd', status='attaching'),
            mock.Mock(id='ccc-ddd', status='in-use')
        ]
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
    def test__rebuild_with_imported_image_error_volume(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-volume': 'ccc-ddd'
        }
        self._cc.compute.get_server.return_value = mock_server
        self._cc.image.get_image.side_effect = [
            mock.Mock(id='aaa-bbb', status='queued'),
            mock.Mock(id='aaa-bbb', status='importing'),
            mock.Mock(id='aaa-bbb', status='active'),
        ]
        self._cc.block_storage.get_volume.side_effect = [
            mock.Mock(id='ccc-ddd', status='creating'),
            mock.Mock(id='ccc-ddd', status='reserved'),
            mock.Mock(id='ccc-ddd', status='error')
        ]
        e = self.assertRaises(
            error.FishyError, self.test_driver._rebuild_with_imported_image,
            self.uuid, 'aaa-bbb')
        self.assertEqual('Volume creation resulted in status reserved', str(e))

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_imported_image_error_rebuild(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-volume': 'ccc-ddd'
        }
        self._cc.compute.get_server.return_value = mock_server
        self._cc.image.get_image.side_effect = [
            mock.Mock(id='aaa-bbb', status='queued'),
            mock.Mock(id='aaa-bbb', status='importing'),
            mock.Mock(id='aaa-bbb', status='active'),
        ]
        self._cc.block_storage.get_volume.side_effect = [
            mock.Mock(id='ccc-ddd', status='creating'),
            mock.Mock(id='ccc-ddd', status='available'),
            mock.Mock(id='ccc-ddd', status='reserved'),
            mock.Mock(id='ccc-ddd', status='attaching'),
            mock.Mock(id='ccc-ddd', status='in-use')
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

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_volume_image(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-volume': 'ccc-ddd',
            'sushy-tools-volume-image': 'aaa-bbb'
        }
        mock_server.status = 'ACTIVE'
        self._cc.image.get_image.side_effect = [
            mock.Mock(id='aaa-bbb', status='queued'),
            mock.Mock(id='aaa-bbb', status='uploading'),
            mock.Mock(id='aaa-bbb', status='saving'),
            mock.Mock(id='aaa-bbb', status='active'),
        ]
        self._cc.compute.rebuild_server.return_value = mock.Mock(
            status='REBUILD')
        self._cc.compute.get_server.side_effect = [
            mock_server,
            mock.Mock(status='REBUILD'),
            mock.Mock(status='ACTIVE'),
        ]
        self._cc.block_storage.get_volume.side_effect = [
            mock.Mock(id='ccc-ddd', status='uploading'),
            mock.Mock(id='ccc-ddd', status='available')
        ]

        self.test_driver._rebuild_with_volume_image(
            self.uuid)

        self._cc.compute.rebuild_server.assert_called_once_with(
            self.uuid, 'aaa-bbb')
        self._cc.delete_image.assert_called_once_with('aaa-bbb')
        self._cc.block_storage.delete_volume.assert_called_once_with('ccc-ddd')

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_volume_image_error_upload(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-volume': 'ccc-ddd',
            'sushy-tools-volume-image': 'aaa-bbb'
        }
        mock_server.status = 'ACTIVE'
        self._cc.compute.get_server.return_value = mock_server
        self._cc.image.get_image.side_effect = [
            mock.Mock(id='aaa-bbb', status='queued'),
            mock.Mock(id='aaa-bbb', status='uploading'),
            mock.Mock(id='aaa-bbb', status='saving'),
            mock.Mock(id='aaa-bbb', status='error'),
        ]

        e = self.assertRaises(
            error.FishyError, self.test_driver._rebuild_with_volume_image,
            self.uuid)
        self.assertEqual('Image import ended with status error', str(e))

        self._cc.compute.rebuild_server.assert_not_called()
        self._cc.delete_image.assert_called_once_with('aaa-bbb')
        self._cc.block_storage.delete_volume.assert_called_once_with('ccc-ddd')

    @mock.patch.object(time, 'sleep', autospec=True)
    def test__rebuild_with_volume_image_error_rebuild(self, mock_sleep):
        mock_server = mock.Mock()
        mock_server.name = 'node01'
        mock_server.metadata = {
            'sushy-tools-image-url': 'http://fish.it/red.iso',
            'sushy-tools-volume': 'ccc-ddd',
            'sushy-tools-volume-image': 'aaa-bbb'
        }
        mock_server.status = 'ACTIVE'
        self._cc.image.get_image.side_effect = [
            mock.Mock(id='aaa-bbb', status='queued'),
            mock.Mock(id='aaa-bbb', status='uploading'),
            mock.Mock(id='aaa-bbb', status='saving'),
            mock.Mock(id='aaa-bbb', status='active'),
        ]
        self._cc.block_storage.upload_volume_to_image.return_value = {
            'image_id': 'aaa-bbb'}
        self._cc.compute.rebuild_server.return_value = mock.Mock(
            status='REBUILD')
        self._cc.compute.get_server.side_effect = [
            mock_server,
            mock.Mock(status='REBUILD'),
            mock.Mock(status='ERROR'),
        ]

        e = self.assertRaises(
            error.FishyError, self.test_driver._rebuild_with_volume_image,
            self.uuid)
        self.assertEqual(
            'Server rebuild attempt resulted in status ERROR', str(e))

        self._cc.compute.rebuild_server.assert_called_once_with(
            self.uuid, 'aaa-bbb')
        self._cc.delete_image.assert_called_once_with('aaa-bbb')
        self._cc.block_storage.delete_volume.assert_called_once_with('ccc-ddd')
