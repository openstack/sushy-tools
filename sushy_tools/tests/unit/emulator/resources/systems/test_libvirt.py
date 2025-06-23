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
import uuid
import xml.etree.ElementTree as ET

import libvirt
from oslotest import base

from sushy_tools.emulator.resources.systems.libvirtdriver import LibvirtDriver
from sushy_tools import error


class LibvirtDriverTestCase(base.BaseTestCase):

    name = 'QEmu-fedora-i686'
    uuid = 'c7a5fdbd-cdaf-9455-926a-d65c16db1809'

    def setUp(self):
        test_driver_class = LibvirtDriver.initialize(
            {}, mock.MagicMock())
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
        conn_mock.listAllDomains.return_value = [domain]
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

        domain_mock.destroy.assert_called_once_with()
        domain_mock.create.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_power_state_nmi(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.isActive.return_value = True

        self.test_driver.set_power_state(self.uuid, 'Nmi')

        domain_mock.injectNMI.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_power_cycle(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_boot_os.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state') as gps_mock:
            with mock.patch.object(
                    self.test_driver, 'set_power_state') as sps_mock:
                gps_mock.return_value = 'Off'
                self.test_driver.set_boot_device(self.uuid, 'Cd')

        self.assertFalse(gps_mock.called)
        self.assertFalse(sps_mock.called)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_boot_device_os(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_boot_os.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        boot_device = self.test_driver.get_boot_device(self.uuid)

        self.assertEqual('Cd', boot_device)

    @mock.patch('libvirt.open', autospec=True)
    def test_set_boot_device_os(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_boot_os.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_device(self.uuid, 'Hdd')

        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    def test_set_boot_device_ignored(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_boot_os.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.test_driver.SUSHY_EMULATOR_IGNORE_BOOT_DEVICE = True

        self.test_driver.set_boot_device(self.uuid, 'Hdd')

        conn_mock.defineXML.assert_called_once_with(mock.ANY)
        tree = ET.fromstring(conn_mock.defineXML.call_args[0][0])
        self.assertEqual(1, len(tree.findall('.//boot')))
        os_element = tree.find('os')
        boot_element = os_element.find('boot')
        self.assertEqual('fd', boot_element.get('dev'))

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_boot_device_disk(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_boot_disk.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        boot_device = self.test_driver.get_boot_device(self.uuid)

        self.assertEqual('Cd', boot_device)

    @mock.patch('libvirt.open', autospec=True)
    def test_set_boot_device_disk(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_boot_disk.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_device(self.uuid, 'Hdd')

        conn_mock.defineXML.assert_called_once_with(mock.ANY)

        expected = '<disk type="file" device="disk">\n      <source ' \
                   'file="/home/user/fedora.img" />\n      <target ' \
                   'dev="hda" />\n    <boot order="1" /></disk>\n'

        self.assertIn(expected, conn_mock.defineXML.call_args[0][0])

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_boot_device_network(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_boot_network.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        boot_device = self.test_driver.get_boot_device(self.uuid)

        self.assertEqual('Pxe', boot_device)

    @mock.patch('libvirt.open', autospec=True)
    def test_set_boot_device_network(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_boot_network.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_device(self.uuid, 'Pxe')

        conn_mock.defineXML.assert_called_once_with(mock.ANY)

        expected = '<interface type="direct">\n      <mac address=' \
                   '"52:54:00:da:ac:54" />\n      <source dev="tap-' \
                   'node-2i1" mode="vepa" />\n      <model type="vir' \
                   'tio" />\n      <address type="pci" domain="0x0000" ' \
                   'bus="0x01" slot="0x01" function="0x0" />\n    ' \
                   '<boot order="1" /></interface>'

        self.assertIn(expected, conn_mock.defineXML.call_args[0][0])

    @mock.patch('libvirt.open', autospec=True)
    def test_set_boot_device_network_from_hd(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_to_boot_pxe.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_device(self.uuid, 'Pxe')

        conn_mock.defineXML.assert_called_once_with(mock.ANY)

        newtree = ET.fromstring(conn_mock.defineXML.call_args[0][0])
        # check that os section does not have boot defined.
        # We find all os sections if any. Then count about of boot sections.
        # And the final summ should be 0
        os_boot_amount = sum(
            [len(ossec.findall('boot')) for ossec in newtree.findall('os')])
        self.assertEqual(0, os_boot_amount)

        # check that Network device has order=1
        interface_orders = [
            theint.find('boot').get('order')
            for theint in newtree.find('devices').findall('interface')]
        self.assertIn('1', interface_orders)

        # Check that we have at least one hd device set after a network device
        diskdrives_order_sum = len([
            thedrive.find('boot').get('order')
            for thedrive in newtree.find('devices').findall('disk')])
        self.assertEqual(2, diskdrives_order_sum)

        # Check overall config to match expected fixture
        expected = '<domain type="qemu">\n  <name>QEmu-fedora-i686</name>\n '\
            ' <uuid>c7a5fdbd-cdaf-9455-926a-d65c16db1809</uuid>\n  '\
            '<memory>219200</memory>\n  '\
            '<currentMemory>219200</currentMemory>\n  <vcpu>2</vcpu>\n  '\
            '<os>\n    <type arch="x86_64" machine="pc">hvm</type>\n    '\
            '<loader type="rom" />\n  </os>\n  <devices>\n    '\
            '<emulator>/usr/bin/qemu-system-x86_64</emulator>\n    '\
            '<disk type="file" device="cdrom">\n      '\
            '<source file="/home/user/boot.iso" />\n      '\
            '<target dev="hdc" />\n      <readonly />\n    '\
            '<boot order="3" /></disk>\n    '\
            '<disk type="file" device="disk">\n      '\
            '<source file="/home/user/fedora.img" />\n      '\
            '<target dev="hda" />\n    <boot order="2" /></disk>\n    '\
            '<interface type="network">\n      '\
            '<source network="default" />\n      '\
            '<mac address="52:54:00:da:ac:54" />\n      '\
            '<model type="virtio" />\n      <address type="pci" '\
            'domain="0x0000" bus="0x01" slot="0x01" function="0x0" />\n    '\
            '<boot order="1" /></interface>\n    '\
            '<graphics type="vnc" port="-1" />\n  </devices>\n</domain>'
        self.assertIn(expected, conn_mock.defineXML.call_args[0][0])

    def test__is_firmware_autoselection_disabled(self):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            domain = f.read()

        tree = ET.fromstring(domain)

        fw_auto = self.test_driver._is_firmware_autoselection(tree)

        self.assertEqual(False, fw_auto)

    def test__is_firmware_autoselection_enabled(self):
        with open(('sushy_tools/tests/unit/emulator/'
                   'domain-q35_fw_auto_uefi.xml'), 'r') as f:
            domain = f.read()

        tree = ET.fromstring(domain)

        fw_auto = self.test_driver._is_firmware_autoselection(tree)

        self.assertEqual(True, fw_auto)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_boot_mode_legacy(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertEqual('Legacy', boot_mode)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_boot_mode_uefi(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35_uefi.xml',
                  'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertEqual('UEFI', boot_mode)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_boot_mode_fw_auto_uefi(self, libvirt_mock):
        with open(('sushy_tools/tests/unit/emulator/'
                   'domain-q35_fw_auto_uefi.xml'), 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        boot_mode = self.test_driver.get_boot_mode(self.uuid)

        self.assertEqual('UEFI', boot_mode)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_mode(self.uuid, 'UEFI')

        conn_mock = libvirt_rw_mock.return_value
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_auto_fw_uefi(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_fw_auto.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_mode(self.uuid, 'UEFI')

        conn_mock = libvirt_rw_mock.return_value
        xml_document = conn_mock.defineXML.call_args[0][0]
        tree = ET.fromstring(xml_document)
        os_element = tree.find('os')
        self.assertEqual('efi', os_element.get('firmware'))
        secure_boot = os_element.findall(
            './firmware/feature[@name="secure-boot"]')
        self.assertEqual('secure-boot', secure_boot[0].get('name'))
        self.assertEqual('no', secure_boot[0].get('enabled'))
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_auto_fw_legacy(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain-q35_fw_auto_uefi.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_mode(self.uuid, 'Legacy')

        conn_mock = libvirt_rw_mock.return_value
        xml_document = conn_mock.defineXML.call_args[0][0]
        tree = ET.fromstring(xml_document)
        os_element = tree.find('os')
        self.assertEqual('bios', os_element.get('firmware'))
        # There should be no secure-boot feature element
        secure_boot = os_element.findall(
            './firmware/feature[@name="secure-boot"]')
        self.assertEqual([], secure_boot)
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_legacy(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35_uefi.xml',
                  'r') as f:
            data = f.read()

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_mode(self.uuid, 'Legacy')

        conn_mock = libvirt_rw_mock.return_value
        xml_document = conn_mock.defineXML.call_args[0][0]
        tree = ET.fromstring(xml_document)
        os_element = tree.find('os')
        loader_element = os_element.find('loader')
        self.assertIsNone(loader_element.text)
        self.assertNotIn('readonly', loader_element.attrib)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_no_os(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        tree = ET.fromstring(data)
        os_element = tree.find('os')
        tree.remove(os_element)

        data = ET.tostring(tree)

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.assertRaises(
                error.FishyError, self.test_driver.set_boot_mode,
                self.uuid, 'Uefi')

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_many_loaders(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        tree = ET.fromstring(data)
        os_element = tree.find('os')
        ET.SubElement(os_element, 'loader')

        data = ET.tostring(tree)

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.assertRaises(
                error.FishyError, self.test_driver.set_boot_mode,
                self.uuid, 'Uefi')

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_many_os(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        tree = ET.fromstring(data)
        ET.SubElement(tree, 'os')
        ET.SubElement(tree, 'os')

        data = ET.tostring(tree)

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.assertRaises(
                error.FishyError, self.test_driver.set_boot_mode,
                self.uuid, 'Uefi')

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_boot_image(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        image_info = self.test_driver.get_boot_image(self.uuid, 'Cd')

        expected = '/home/user/boot.iso', False, False

        self.assertEqual(expected, image_info)

    @mock.patch('sushy_tools.emulator.resources.systems.libvirtdriver'
                '.os.stat', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.systems.libvirtdriver'
                '.open')
    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_image(self, libvirt_mock, libvirt_rw_mock,
                            open_mock, stat_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        pool_mock = conn_mock.storagePoolLookupByName.return_value

        with open('sushy_tools/tests/unit/emulator/pool.xml', 'r') as f:
            data = f.read()

        pool_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            with mock.patch.object(
                    self.test_driver, 'get_boot_device', return_value=None):

                self.test_driver.set_boot_image(
                    self.uuid, 'Cd', '/tmp/image.iso')

        conn_mock = libvirt_rw_mock.return_value
        pool_mock.listAllVolumes.assert_called_once_with()
        stat_mock.assert_called_once_with('/tmp/image.iso')
        pool_mock.createXML.assert_called_once_with(mock.ANY)

        volume_mock = pool_mock.createXML.return_value
        volume_mock.upload.assert_called_once_with(mock.ANY, 0, mock.ANY)

        expected_disk = ('<disk type="file" device="cdrom">'
                         '<target dev="hdc" bus="ide" />'
                         '<address type="drive" controller="0"'
                         ' bus="0" target="0" unit="0" />')
        self.assertEqual(1, conn_mock.defineXML.call_count)
        self.assertIn(expected_disk, conn_mock.defineXML.call_args[0][0])

    @mock.patch('sushy_tools.emulator.resources.systems.libvirtdriver'
                '.os.stat', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.systems.libvirtdriver'
                '.open')
    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_image_q35(self, libvirt_mock, libvirt_rw_mock,
                                open_mock, stat_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        pool_mock = conn_mock.storagePoolLookupByName.return_value

        with open('sushy_tools/tests/unit/emulator/pool.xml', 'r') as f:
            data = f.read()

        pool_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            with mock.patch.object(
                    self.test_driver, 'get_boot_device', return_value=None):

                self.test_driver.set_boot_image(
                    self.uuid, 'Cd', '/tmp/image.iso')

        conn_mock = libvirt_rw_mock.return_value
        pool_mock.listAllVolumes.assert_called_once_with()
        stat_mock.assert_called_once_with('/tmp/image.iso')
        pool_mock.createXML.assert_called_once_with(mock.ANY)

        volume_mock = pool_mock.createXML.return_value
        volume_mock.upload.assert_called_once_with(mock.ANY, 0, mock.ANY)

        expected_disk = ('<disk device="cdrom" type="file">'
                         '<target bus="sata" dev="sdx" />'
                         '<address bus="0" controller="0" '
                         'target="0" type="drive" unit="0" />')

        expected_disk = ('<disk type="file" device="cdrom">'
                         '<target dev="sdx" bus="sata" />'
                         '<address type="drive" controller="0"'
                         ' bus="0" target="0" unit="0" />')
        self.assertEqual(1, conn_mock.defineXML.call_count)
        self.assertIn(expected_disk, conn_mock.defineXML.call_args[0][0])

    @mock.patch('sushy_tools.emulator.resources.systems.libvirtdriver'
                '.os.stat', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.systems.libvirtdriver'
                '.open')
    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_image_sata(self, libvirt_mock, libvirt_rw_mock,
                                 open_mock, stat_mock):
        with open('sushy_tools/tests/unit/emulator/domain-sata.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        pool_mock = conn_mock.storagePoolLookupByName.return_value

        with open('sushy_tools/tests/unit/emulator/pool.xml', 'r') as f:
            data = f.read()

        pool_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            with mock.patch.object(
                    self.test_driver, 'get_boot_device', return_value=None):

                self.test_driver.set_boot_image(
                    self.uuid, 'Cd', '/tmp/image.iso')

        conn_mock = libvirt_rw_mock.return_value
        pool_mock.listAllVolumes.assert_called_once_with()
        stat_mock.assert_called_once_with('/tmp/image.iso')
        pool_mock.createXML.assert_called_once_with(mock.ANY)

        volume_mock = pool_mock.createXML.return_value
        volume_mock.upload.assert_called_once_with(mock.ANY, 0, mock.ANY)

        expected_disk = ('<disk type="file" device="cdrom">'
                         '<target dev="sdx" bus="sata" />'
                         '<address type="drive" controller="0"'
                         ' bus="0" target="0" unit="1" />')
        self.assertEqual(1, conn_mock.defineXML.call_count)
        self.assertIn(expected_disk, conn_mock.defineXML.call_args[0][0])

    @mock.patch('sushy_tools.emulator.resources.systems.libvirtdriver'
                '.os.stat', autospec=True)
    @mock.patch('sushy_tools.emulator.resources.systems.libvirtdriver'
                '.open')
    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_image_scsi(self, libvirt_mock, libvirt_rw_mock,
                                 open_mock, stat_mock):
        with open('sushy_tools/tests/unit/emulator/domain-scsi.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        pool_mock = conn_mock.storagePoolLookupByName.return_value

        with open('sushy_tools/tests/unit/emulator/pool.xml', 'r') as f:
            data = f.read()

        pool_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            with mock.patch.object(
                    self.test_driver, 'get_boot_device', return_value=None):

                self.test_driver.set_boot_image(
                    self.uuid, 'Cd', '/tmp/image.iso')

        conn_mock = libvirt_rw_mock.return_value
        pool_mock.listAllVolumes.assert_called_once_with()
        stat_mock.assert_called_once_with('/tmp/image.iso')
        pool_mock.createXML.assert_called_once_with(mock.ANY)

        volume_mock = pool_mock.createXML.return_value
        volume_mock.upload.assert_called_once_with(mock.ANY, 0, mock.ANY)

        expected_disk = ('<disk type="file" device="cdrom">'
                         '<target dev="sdx" bus="scsi" />'
                         '<address type="drive" controller="0"'
                         ' bus="0" target="0" unit="1" />')

        self.assertEqual(1, conn_mock.defineXML.call_count)
        self.assertIn(expected_disk, conn_mock.defineXML.call_args[0][0])

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    @mock.patch(
        'sushy_tools.emulator.resources.systems.libvirtdriver.LibvirtDriver'
        '.get_power_state', new=mock.MagicMock(return_value='Off'))
    @mock.patch(
        'sushy_tools.emulator.resources.systems.libvirtdriver.LibvirtDriver'
        '.get_boot_device', return_value='Cd')
    @mock.patch(
        'sushy_tools.emulator.resources.systems.libvirtdriver.LibvirtDriver'
        '.set_boot_device')
    @mock.patch(
        'sushy_tools.emulator.resources.systems.libvirtdriver.LibvirtDriver'
        '._add_boot_image', new=mock.MagicMock())
    @mock.patch(
        'sushy_tools.emulator.resources.systems.libvirtdriver.LibvirtDriver'
        '._remove_boot_images', new=mock.MagicMock())
    def test_set_boot_image_restore_boot_device(
            self, sbd_mock, gbd_mock, libvirt_mock, libvirt_rw_mock):

        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_rw_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.test_driver.set_boot_image(
            self.uuid, 'Cd', '/tmp/image.iso')

        gbd_mock.assert_called_once_with(self.uuid)
        sbd_mock.assert_called_once_with(self.uuid, 'Cd')

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
                          "L2Cache": "10x256 KB",
                          "NumCores": "10",
                          "NicBoot1": "NetworkBoot",
                          "QuietBoot": "true",
                          "ProcTurboMode": "Disabled",
                          "SecureBootStatus": "Enabled",
                          "SerialNumber": "QPX12345",
                          "SysPassword": ""},
                         bios_attributes)
        conn_mock.defineXML.assert_not_called()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_bios(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_bios(
                self.uuid, {"BootMode": "Uefi",
                            "ProcTurboMode": "Enabled"})

        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    def test_reset_bios(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
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
                          "L2Cache": "10x256 KB",
                          "NumCores": "10",
                          "NicBoot1": "NetworkBoot",
                          "QuietBoot": "true",
                          "ProcTurboMode": "Disabled",
                          "SecureBootStatus": "Enabled",
                          "SerialNumber": "QPX12345",
                          "SysPassword": ""},
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

    def test__process_bios_attributes_update_non_string(self):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()
        result = self.test_driver._process_bios_attributes(
            domain_xml,
            {"NumCores": 11},
            True)
        self.assertTrue(result.attributes_written)
        self.assertEqual({"NumCores": "11"},
                         result.bios_attributes)
        self._assert_bios_xml(result.tree)

    def _assert_bios_xml(self, tree):
        ns = {'sushy': 'http://openstack.org/xmlns/libvirt/sushy'}
        self.assertIsNotNone(tree.find('metadata')
                             .find('sushy:bios', ns)
                             .find('sushy:attributes', ns))

    def _assert_versions_xml(self, tree):
        ns = {'sushy': 'http://openstack.org/xmlns/libvirt/sushy'}
        self.assertIsNotNone(tree.find('metadata')
                             .find('sushy:bios', ns)
                             .find('sushy:versions', ns))

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

    @mock.patch('libvirt.open', autospec=True)
    def test_get_versions(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        firmware_versions = self.test_driver.get_versions(self.uuid)
        self.assertEqual(LibvirtDriver.DEFAULT_FIRMWARE_VERSIONS,
                         firmware_versions)
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    def test_get_versions_existing(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_versions.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        versions = self.test_driver.get_versions(self.uuid)
        self.assertEqual({"BiosVersion": "1.0.0"},
                         versions)
        conn_mock.defineXML.assert_not_called()

    @mock.patch('libvirt.open', autospec=True)
    def test_set_versions(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_versions.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_versions(
                self.uuid, {"BiosVersion": "1.1.0"})

        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    def test_reset_versions(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_versions.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.reset_versions(self.uuid)

        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    def test__process_versions_attributes_get_default(self):
        with open('sushy_tools/tests/unit/emulator/domain.xml') as f:
            domain_xml = f.read()

        result = self.test_driver._process_versions_attributes(domain_xml)
        self.assertTrue(result.attributes_written)
        self.assertEqual(LibvirtDriver.DEFAULT_FIRMWARE_VERSIONS,
                         result.firmware_versions)
        self._assert_versions_xml(result.tree)

    def test__process_versions_attributes_get_default_metadata_exists(self):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_metadata.xml') as f:
            domain_xml = f.read()

        result = self.test_driver._process_versions_attributes(domain_xml)
        self.assertTrue(result.attributes_written)
        self.assertEqual(LibvirtDriver.DEFAULT_FIRMWARE_VERSIONS,
                         result.firmware_versions)
        self._assert_versions_xml(result.tree)

    def test__process_versions_attributes_get_existing(self):
        with open('sushy_tools/tests/unit/emulator/domain_versions.xml') as f:
            domain_xml = f.read()

        result = self.test_driver._process_versions_attributes(domain_xml)
        self.assertFalse(result.attributes_written)
        self.assertEqual({"BiosVersion": "1.0.0"},
                         result.firmware_versions)
        self._assert_versions_xml(result.tree)

    def test__process_versions_attributes_update(self):
        with open('sushy_tools/tests/unit/emulator/domain_versions.xml') as f:
            domain_xml = f.read()
        result = self.test_driver._process_versions_attributes(
            domain_xml,
            {"BiosVersion": "2.0.0"},
            True)
        self.assertTrue(result.attributes_written)
        self.assertEqual({"BiosVersion": "2.0.0"},
                         result.firmware_versions)
        self._assert_versions_xml(result.tree)

    def test__process_versions_attributes_update_non_string(self):
        with open('sushy_tools/tests/unit/emulator/domain_versions.xml') as f:
            domain_xml = f.read()
        result = self.test_driver._process_versions_attributes(
            domain_xml,
            {"BiosVersion": 42},
            True)
        self.assertTrue(result.attributes_written)
        self.assertEqual({"BiosVersion": "42"},
                         result.firmware_versions)
        self._assert_versions_xml(result.tree)

    @mock.patch('libvirt.open', autospec=True)
    def test__process_versions_error(self, libvirt_mock):
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
                          {"BiosVersion" "1.0.0"})

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
                          {'id': '52:54:00:12:31:dd',
                           'mac': '52:54:00:12:31:dd'},
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

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_processors(self, libvirt_mock):
        with open(
                'sushy_tools/tests/unit/emulator/domain_processors.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml
        domain_mock.maxVcpus.return_value = 2

        processors = self.test_driver.get_processors(self.uuid)
        self.assertEqual([{'cores': '2',
                           'id': 'CPU0',
                           'model': 'core2duo',
                           'socket': 'CPU 0',
                           'threads': '1',
                           'vendor': 'Intel'},
                          {'cores': '2',
                           'id': 'CPU1',
                           'model': 'core2duo',
                           'socket': 'CPU 1',
                           'threads': '1',
                           'vendor': 'Intel'}],
                         sorted(processors, key=lambda k: k['id']))

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_processors_notopology(self, libvirt_mock):
        with open(
                'sushy_tools/tests/unit/emulator/'
                'domain_processors_notopology.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = domain_xml
        domain_mock.maxVcpus.return_value = 2

        processors = self.test_driver.get_processors(self.uuid)
        self.assertEqual([{'cores': '1',
                           'id': 'CPU0',
                           'model': 'N/A',
                           'socket': 'CPU 0',
                           'threads': '1',
                           'vendor': 'N/A'},
                          {'cores': '1',
                           'id': 'CPU1',
                           'model': 'N/A',
                           'socket': 'CPU 1',
                           'threads': '1',
                           'vendor': 'N/A'}],
                         sorted(processors, key=lambda k: k['id']))

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_simple_storage_collection(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain_simple_storage.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        dom_mock = conn_mock.lookupByUUID.return_value
        dom_mock.XMLDesc.return_value = data
        vol_mock = conn_mock.storageVolLookupByPath.return_value
        vol_mock.name.side_effect = ['testVM1.img', 'testVol1.img', 'sdb1']
        vol_mock.info.side_effect = [['testVM1.img', 100000],
                                     ['testVol1.img', 200000],
                                     ['sdb1', 150000]]
        pool_mock = conn_mock.storagePoolLookupByName.return_value
        pvol_mock = pool_mock.storageVolLookupByName.return_value
        pvol_mock.name.return_value = 'blk-pool0-vol0'
        pvol_mock.info.return_value = ['volType', 300000]

        simple_storage_response = (self.test_driver
                                   .get_simple_storage_collection(self.uuid))

        simple_storage_expected = {
            'virtio': {
                'Id': 'virtio',
                'Name': 'virtio',
                'DeviceList': [
                    {
                        'Name': 'testVM1.img',
                        'CapacityBytes': 100000
                    },
                    {
                        'Name': 'sdb1',
                        'CapacityBytes': 150000
                    }
                ]
            },
            'ide': {
                'Id': 'ide',
                'Name': 'ide',
                'DeviceList': [
                    {
                        'Name': 'testVol1.img',
                        'CapacityBytes': 200000
                    },
                    {
                        'Name': 'blk-pool0-vol0',
                        'CapacityBytes': 300000
                    }
                ]
            }
        }

        self.assertEqual(simple_storage_response, simple_storage_expected)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_simple_storage_collection_empty(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        dom_mock = conn_mock.lookupByUUID.return_value
        dom_mock.XMLDesc.return_value = domain_xml
        vol_mock = conn_mock.storageVolLookupByPath.return_value
        vol_mock.name.side_effect = ['testVM1.img', 'testVol1.img', 'sdb1']
        vol_mock.info.side_effect = [['testType1', 100000],
                                     ['testType2', 200000],
                                     ['testType1', 150000]]
        pool_mock = conn_mock.storagePoolLookupByName.return_value
        pvol_mock = pool_mock.storageVolLookupByName.return_value
        pvol_mock.name.return_value = 'blk-pool0-vol0'
        pvol_mock.info.return_value = ['volType', 300000]

        simple_storage_response = (self.test_driver
                                   .get_simple_storage_collection(self.uuid))

        self.assertEqual({}, simple_storage_response)

    @mock.patch('libvirt.open', autospec=True)
    def test_find_or_create_storage_volume(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        vol_data = {
            "libvirtVolName": "123456",
            "Id": "1",
            "Name": "Sample Vol",
            "CapacityBytes": 12345,
            "VolumeType": "Mirrored"
        }

        pool_mock = conn_mock.storagePoolLookupByName.return_value
        with open('sushy_tools/tests/unit/emulator/pool.xml', 'r') as f:
            data = f.read()
        pool_mock.storageVolLookupByName.side_effect = libvirt.libvirtError(
            'Storage volume not found')
        pool_mock.XMLDesc.return_value = data

        self.test_driver.find_or_create_storage_volume(vol_data)
        pool_mock.createXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_secure_boot_off(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35_uefi.xml',
                  'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.assertFalse(self.test_driver.get_secure_boot(self.uuid))

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_secure_boot_fw_auto_off(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain-q35_fw_auto_uefi.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.assertFalse(self.test_driver.get_secure_boot(self.uuid))

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_secure_boot_on(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35_uefi_secure.xml',
                  'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.assertTrue(self.test_driver.get_secure_boot(self.uuid))

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_secure_boot_fw_auto_on(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain-q35_fw_auto_uefi_secure.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.assertTrue(self.test_driver.get_secure_boot(self.uuid))

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_get_secure_boot_not_uefi(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.assertRaises(error.NotSupportedError,
                          self.test_driver.get_secure_boot, self.uuid)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_secure_boot_on(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35_uefi.xml',
                  'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.test_driver.set_secure_boot(self.uuid, True)

        conn_mock = libvirt_rw_mock.return_value
        xml_document = conn_mock.defineXML.call_args[0][0]
        tree = ET.fromstring(xml_document)
        os_element = tree.find('os')
        loader_element = os_element.find('loader')
        nvram_element = os_element.find('nvram')
        self.assertEqual('yes', loader_element.get('secure'))
        self.assertEqual('/usr/share/OVMF/OVMF_CODE.secboot.fd',
                         loader_element.text)
        self.assertEqual('/usr/share/OVMF/OVMF_VARS.secboot.fd',
                         nvram_element.get('template'))
        self.assertEqual('/var/lib/libvirt/nvram/%s_VARS.secboot.fd' %
                         self.name, nvram_element.text)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_secure_boot_off(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35_uefi_secure.xml',
                  'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.test_driver.set_secure_boot(self.uuid, False)

        conn_mock = libvirt_rw_mock.return_value
        xml_document = conn_mock.defineXML.call_args[0][0]
        tree = ET.fromstring(xml_document)
        os_element = tree.find('os')
        loader_element = os_element.find('loader')
        nvram_element = os_element.find('nvram')
        self.assertEqual('no', loader_element.get('secure'))
        self.assertEqual('/usr/share/OVMF/OVMF_CODE.secboot.fd',
                         loader_element.text)
        self.assertEqual('/usr/share/OVMF/OVMF_VARS.fd',
                         nvram_element.get('template'))
        self.assertEqual('/var/lib/libvirt/nvram/%s_VARS.nosecboot.fd' %
                         self.name, nvram_element.text)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_secure_boot_not_uefi(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.assertRaises(error.NotSupportedError,
                          self.test_driver.set_secure_boot, self.uuid, True)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_get_http_boot_uri(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain-q35.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data
        self.assertIsNone(self.test_driver.get_http_boot_uri(None))
        uri = 'http://host.path/meow'
        self.test_driver.set_http_boot_uri(uri)
        self.assertEqual(uri, self.test_driver.get_http_boot_uri(None))

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_secure_boot_on_auto_fw(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain-q35_fw_auto_uefi.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.test_driver.set_secure_boot(self.uuid, True)

        conn_mock = libvirt_rw_mock.return_value
        xml_document = conn_mock.defineXML.call_args[0][0]
        tree = ET.fromstring(xml_document)
        os_element = tree.find('os')
        self.assertEqual('efi', os_element.get('firmware'))
        secure_boot = os_element.findall(
            './firmware/feature[@name="secure-boot"]')
        self.assertEqual('secure-boot', secure_boot[0].get('name'))
        self.assertEqual('yes', secure_boot[0].get('enabled'))
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_secure_boot_off_auto_fw(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/'
                  'domain-q35_fw_auto_uefi_secure.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        self.test_driver.set_secure_boot(self.uuid, False)

        conn_mock = libvirt_rw_mock.return_value
        xml_document = conn_mock.defineXML.call_args[0][0]
        tree = ET.fromstring(xml_document)
        os_element = tree.find('os')
        self.assertEqual('efi', os_element.get('firmware'))
        secure_boot = os_element.findall(
            './firmware/feature[@name="secure-boot"]')
        self.assertEqual('secure-boot', secure_boot[0].get('name'))
        self.assertEqual('no', secure_boot[0].get('enabled'))
        conn_mock.defineXML.assert_called_once_with(mock.ANY)
