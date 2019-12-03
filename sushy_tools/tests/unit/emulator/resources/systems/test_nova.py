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

        test_driver_class = OpenStackDriver.initialize(
            {}, mock.MagicMock(), 'fake-cloud')
        self.test_driver = test_driver_class()

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
