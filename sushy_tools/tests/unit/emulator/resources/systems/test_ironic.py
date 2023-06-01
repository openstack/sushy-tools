# Copyright 2023 Red Hat, Inc.
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

from sushy_tools.emulator.resources.systems.ironicdriver import IronicDriver
from sushy_tools import error


@mock.patch.dict(IronicDriver.PERMANENT_CACHE)
class IronicDriverTestCase(base.BaseTestCase):
    uuid = 'c7a5fdbd-cdaf-9455-926a-d65c16db1809'

    def setUp(self):
        self.ironic_patcher = mock.patch('openstack.connect', autospec=True)
        self.ironic_mock = self.ironic_patcher.start()

        self.node_mock = mock.Mock(id=self.uuid)
        self.ironic_mock.return_value.baremetal.get_node.return_value = \
            self.node_mock

        # _cc is initialized on the class (not any single object) so it needs
        # to be cleared between tests
        if hasattr(IronicDriver, "_cc"):
            del IronicDriver._cc

        test_driver_class = IronicDriver.initialize(
            {}, mock.MagicMock(), 'fake-cloud')
        self.test_driver = test_driver_class()

        super(IronicDriverTestCase, self).setUp()

    def tearDown(self):
        self.ironic_patcher.stop()
        super(IronicDriverTestCase, self).tearDown()

    def test_uuid(self):
        uuid = self.test_driver.uuid(self.uuid)
        self.assertEqual(self.uuid, uuid)

    def test_systems(self):
        node0 = mock.Mock(id='host0')
        node1 = mock.Mock(id='host1')
        self.ironic_mock.return_value.baremetal.nodes.return_value = [
            node0, node1]
        systems = self.test_driver.systems

        self.assertEqual(['host0', 'host1'], systems)

    def test_get_power_state_on(self):
        self.node_mock.power_state = 'power on'

        power_state = self.test_driver.get_power_state(self.uuid)

        self.assertEqual('On', power_state)

    def test_get_power_state_off(self):
        self.node_mock.power_state = 'power off'

        power_state = self.test_driver.get_power_state(self.uuid)

        self.assertEqual('Off', power_state)

    def test_set_power_state_on(self):
        self.node_mock.power_state = 'power off'
        self.test_driver.set_power_state(self.uuid, 'On')
        snps = self.ironic_mock.return_value.baremetal.set_node_power_state
        snps.assert_called_once_with(self.uuid, 'power on')

    def test_set_power_state_forceon(self):
        self.node_mock.power_state = 'power off'
        self.test_driver.set_power_state(self.uuid, 'ForceOn')
        snps = self.ironic_mock.return_value.baremetal.set_node_power_state
        snps.assert_called_once_with(self.uuid, 'power on')

    def test_set_power_state_forceoff(self):
        self.node_mock.power_state = 'power on'
        self.test_driver.set_power_state(self.uuid, 'ForceOff')
        snps = self.ironic_mock.return_value.baremetal.set_node_power_state
        snps.assert_called_once_with(self.uuid, 'power off')

    def test_set_power_state_gracefulshutdown(self):
        self.node_mock.power_state = 'power on'
        self.test_driver.set_power_state(self.uuid, 'GracefulShutdown')
        snps = self.ironic_mock.return_value.baremetal.set_node_power_state
        snps.assert_called_once_with(self.uuid, 'soft power off')

    def test_set_power_state_gracefulrestart(self):
        self.node_mock.power_state = 'power on'
        self.test_driver.set_power_state(self.uuid, 'GracefulRestart')
        snps = self.ironic_mock.return_value.baremetal.set_node_power_state
        snps.assert_called_once_with(self.uuid, 'soft rebooting')

    def test_set_power_state_forcerestart(self):
        self.node_mock.power_state = 'power on'
        self.test_driver.set_power_state(self.uuid, 'ForceRestart')
        snps = self.ironic_mock.return_value.baremetal.set_node_power_state
        snps.assert_called_once_with(self.uuid, 'rebooting')

    def test_get_boot_device(self):
        self.node_mock.get_boot_device.return_value.get.return_value = "pxe"

        boot_device = self.test_driver.get_boot_device(self.uuid)

        self.assertEqual('Pxe', boot_device)

    def test_set_boot_device(self):
        self.test_driver.set_boot_device(self.uuid, 'Pxe')
        self.ironic_mock.return_value.baremetal.set_node_boot_device.\
            assert_called_once_with(self.uuid, "pxe")

    def test_get_boot_mode(self):
        self.node_mock.boot_mode = 'bios'

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertEqual('Legacy', boot_mode)

    def test_set_boot_mode(self):
        self.assertRaises(
            error.FishyError, self.test_driver.set_boot_mode,
            self.uuid, 'Legacy')

    def test_get_total_memory(self):
        self.node_mock.properties = {'memory_mb': '4096'}

        memory = self.test_driver.get_total_memory(self.uuid)

        self.assertEqual(4, memory)

    def test_get_total_cpus(self):
        self.node_mock.properties = {'cpus': '2'}

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
        self.ironic_mock.return_value.baremetal.ports.return_value = \
            [{"node_uuid": self.uuid, "address": "fa:16:3e:22:18:31"},
             {"node_uuid": "dummy", "address": "dummy"}]

        nics = self.test_driver.get_nics(self.uuid)

        self.assertEqual([{'id': 'fa:16:3e:22:18:31',
                           'mac': 'fa:16:3e:22:18:31'}],
                         sorted(nics, key=lambda k: k['id']))

    def test_get_nics_empty(self):
        self.node_mock.addresses = None
        self.ironic_mock.return_value.baremetal.ports.return_value = []
        nics = self.test_driver.get_nics(self.uuid)
        self.assertEqual([], nics)

    def test_get_simple_storage_collection(self):
        self.assertRaises(
            error.FishyError,
            self.test_driver.get_simple_storage_collection, self.uuid)

    def test_get_secure_boot_off(self):
        self.node_mock.is_secure_boot = False
        self.assertFalse(self.test_driver.get_secure_boot(self.uuid))

    def test_get_secure_boot_on(self):
        self.node_mock.is_secure_boot = True
        self.assertTrue(self.test_driver.get_secure_boot(self.uuid))

    def test_set_secure_boot(self):
        self.assertRaises(
            error.NotSupportedError, self.test_driver.set_secure_boot,
            self.uuid, True)
