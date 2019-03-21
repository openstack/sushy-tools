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
import uuid

import libvirt
from oslotest import base
from six.moves import mock

from sushy_tools.emulator.drivers.libvirtdriver import LibvirtDriver
from sushy_tools import error


class LibvirtDriverTestCase(base.BaseTestCase):

    name = 'QEmu-fedora-i686'
    uuid = 'c7a5fdbd-cdaf-9455-926a-d65c16db1809'

    def setUp(self):
        test_driver_class = LibvirtDriver.initialize({})
        self.test_driver = test_driver_class()
        super(LibvirtDriverTestCase, self).setUp()

    @mock.patch('libvirt.open', autospec=True)
    def test__get_domain_by_name(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        lookupByUUID_mock = conn_mock.lookupByUUID
        domain_mock = lookupByUUID_mock.return_value
        domain_mock.UUIDString.return_value = self.uuid
        self.assertRaises(
            error.AliasAccessError, self.test_driver._get_domain, self.name)

    @mock.patch('libvirt.open', autospec=True)
    def test__get_domain_by_uuid(self, libvirt_mock):
        domain_id = uuid.UUID(self.uuid)

        conn_mock = libvirt_mock.return_value
        lookupByUUID_mock = conn_mock.lookupByUUID
        self.test_driver._get_domain(str(domain_id))
        lookupByUUID_mock.assert_called_once_with(domain_id.bytes)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_uuid(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByName.return_value
        domain_mock.UUIDString.return_value = self.uuid
        self.assertRaises(error.AliasAccessError,
                          self.test_driver.uuid, 'name')

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_systems(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain = mock.MagicMock()
        domain.UUIDString.return_value = self.uuid
        conn_mock.listDefinedDomains.return_value = [domain]
        uuidstring_mock = conn_mock.lookupByName.return_value.UUIDString
        uuidstring_mock.return_value = self.uuid
        systems = self.test_driver.systems
        self.assertEqual([self.uuid], systems)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_power_state_on(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.UUIDString.return_value = self.uuid

        domain_mock.isActive.return_value = True
        domain_mock.maxMemory.return_value = 1024 * 1024
        domain_mock.maxVcpus.return_value = 2

        power_state = self.test_driver.get_power_state(self.uuid)

        self.assertEqual('On', power_state)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_power_state_off(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = False

        power_state = self.test_driver.get_power_state(self.uuid)

        self.assertEqual('Off', power_state)

    @mock.patch('libvirt.open', autospec=True)
    def test_set_power_state_on(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = False

        self.test_driver.set_power_state(self.uuid, 'On')

        domain_mock.create.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_power_state_forceon(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = False

        self.test_driver.set_power_state(self.uuid, 'ForceOn')

        domain_mock.create.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_power_state_forceoff(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = True

        self.test_driver.set_power_state(self.uuid, 'ForceOff')

        domain_mock.destroy.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_power_state_gracefulshutdown(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = True

        self.test_driver.set_power_state(self.uuid, 'GracefulShutdown')

        domain_mock.shutdown.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_power_state_gracefulrestart(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = True

        self.test_driver.set_power_state(self.uuid, 'GracefulRestart')

        domain_mock.reboot.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_power_state_forcerestart(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = True

        self.test_driver.set_power_state(self.uuid, 'ForceRestart')

        domain_mock.reset.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_power_state_nmi(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = True

        self.test_driver.set_power_state(self.uuid, 'Nmi')

        domain_mock.injectNMI.assert_called_once_with()

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_boot_device(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        boot_device = self.test_driver.get_boot_device(self.uuid)

        self.assertEqual('Cd', boot_device)

    @mock.patch('libvirt.open', autospec=True)
    def test_set_boot_device(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.test_driver.set_boot_device(self.uuid, 'Hdd')

        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_boot_mode(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertEqual('Legacy', boot_mode)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.test_driver.set_boot_mode(self.uuid, 'Uefi')

        conn_mock = libvirt_rw_mock.return_value
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_unknown_path(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.dict(
                self.test_driver.KNOWN_BOOT_LOADERS, {}, clear=True):
            self.assertRaises(
                error.FishyError, self.test_driver.set_boot_mode,
                self.uuid, 'Uefi')

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_total_memory(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.maxMemory.return_value = 1024 * 1024

        memory = self.test_driver.get_total_memory(self.uuid)

        self.assertEqual(1, memory)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_total_cpus(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = True
        domain_mock.XMLDesc.return_value = b'<empty/>'
        domain_mock.maxVcpus.return_value = 2

        cpus = self.test_driver.get_total_cpus(self.uuid)

        self.assertEqual(2, cpus)

    @mock.patch('libvirt.open', autospec=True)
    def test_get_bios(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        bios_attributes = self.test_driver.get_bios(self.uuid)
        self.assertEqual(LibvirtDriver.DEFAULT_BIOS_ATTRIBUTES,
                         bios_attributes)
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    def test_get_bios_existing(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        bios_attributes = self.test_driver.get_bios(self.uuid)
        self.assertEqual({"BootMode": "Bios",
                          "EmbeddedSata": "Raid",
                          "NicBoot1": "NetworkBoot",
                          "ProcTurboMode": "Disabled"},
                         bios_attributes)
        conn_mock.defineXML.assert_not_called()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_bios(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        self.test_driver.set_bios(self.uuid,
                                  {"BootMode": "Uefi",
                                   "ProcTurboMode": "Enabled"})
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    def test_reset_bios(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        self.test_driver.reset_bios(self.uuid)
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    def test__process_bios_attributes_get_default(self):
        with open('sushy_tools/tests/unit/emulator/domain.xml') as f:
            domain_xml = f.read()

        result = self.test_driver._process_bios_attributes(domain_xml)
        self.assertTrue(result.attributes_written)
        self.assertEqual(LibvirtDriver.DEFAULT_BIOS_ATTRIBUTES,
                         result.bios_attributes)
        self._assert_bios_xml(result.tree)

    def test__process_bios_attributes_get_default_metadata_exists(self):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_metadata.xml') as f:
            domain_xml = f.read()

        result = self.test_driver._process_bios_attributes(domain_xml)
        self.assertTrue(result.attributes_written)
        self.assertEqual(LibvirtDriver.DEFAULT_BIOS_ATTRIBUTES,
                         result.bios_attributes)
        self._assert_bios_xml(result.tree)

    def test__process_bios_attributes_get_existing(self):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()

        result = self.test_driver._process_bios_attributes(domain_xml)
        self.assertFalse(result.attributes_written)
        self.assertEqual({"BootMode": "Bios",
                          "EmbeddedSata": "Raid",
                          "NicBoot1": "NetworkBoot",
                          "ProcTurboMode": "Disabled"},
                         result.bios_attributes)
        self._assert_bios_xml(result.tree)

    def test__process_bios_attributes_update(self):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()
        result = self.test_driver._process_bios_attributes(
            domain_xml,
            {"BootMode": "Uefi",
             "ProcTurboMode": "Enabled"},
            True)
        self.assertTrue(result.attributes_written)
        self.assertEqual({"BootMode": "Uefi",
                         "ProcTurboMode": "Enabled"},
                         result.bios_attributes)
        self._assert_bios_xml(result.tree)

    def _assert_bios_xml(self, tree):
        ns = {'sushy': 'http://openstack.org/xmlns/libvirt/sushy'}
        self.assertIsNotNone(tree.find('metadata')
                             .find('sushy:bios', ns)
                             .find('sushy:attributes', ns))

    @mock.patch('libvirt.open', autospec=True)
    def test__process_bios_error(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml
        conn_mock.defineXML.side_effect = libvirt.libvirtError(
            'because I can')

        self.assertRaises(error.FishyError,
                          self.test_driver._process_bios,
                          'xxx-yyy-zzz',
                          {"BootMode": "Uefi",
                           "ProcTurboMode": "Enabled"})

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_nics(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_nics.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        nics = self.test_driver.get_nics(self.uuid)
        self.assertEqual([{'id': '00:11:22:33:44:55',
                           'mac': '00:11:22:33:44:55'},
                          {'id': '52:54:00:4e:5d:37',
                           'mac': '52:54:00:4e:5d:37'}],
                         sorted(nics, key=lambda k: k['id']))

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_nics_empty(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        nics = self.test_driver.get_nics(self.uuid)
        self.assertEqual([], nics)
