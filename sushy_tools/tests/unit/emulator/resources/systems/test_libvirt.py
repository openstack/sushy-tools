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

import sys
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

        domain_mock.reset.assert_called_once_with()

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

        expected = '<disk device="disk" type="file">\n      <source ' \
                   'file="/home/user/fedora.img" />\n      <target ' \
                   'dev="hda" />\n    <boot order="1" /></disk>\n'

        # NOTE(rpittau): starting from Python 3.8 the tostring() function
        # preserves the attribute order specified by the user.
        if sys.version_info[1] >= 8:
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
                   'tio" />\n      <address bus="0x01" domain="0x' \
                   '0000" function="0x0" slot="0x01" type="pci" />\n    ' \
                   '<boot order="1" /></interface>'

        # NOTE(rpittau): starting from Python 3.8 the tostring() function
        # preserves the attribute order specified by the user.
        if sys.version_info[1] >= 8:
            expected = '<interface type="direct">\n      <mac address=' \
                       '"52:54:00:da:ac:54" />\n      <source dev="tap-' \
                       'node-2i1" mode="vepa" />\n      <model type="vir' \
                       'tio" />\n      <address type="pci" domain="0x0000" ' \
                       'bus="0x01" slot="0x01" function="0x0" />\n    ' \
                       '<boot order="1" /></interface>'

        self.assertIn(expected, conn_mock.defineXML.call_args[0][0])

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

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_mode(self.uuid, 'UEFI')

        conn_mock = libvirt_rw_mock.return_value
        conn_mock.defineXML.assert_called_once_with(mock.ANY)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_known_loader(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_mode(self.uuid, 'UEFI')

        conn_mock = libvirt_rw_mock.return_value
        xml_document = conn_mock.defineXML.call_args[0][0]
        tree = ET.fromstring(xml_document)
        os_element = tree.find('os')
        loader_element = os_element.find('loader')
        self.assertEqual(
            'pflash', loader_element.get('type'))
        self.assertEqual(
            '/usr/share/OVMF/OVMF_CODE.fd',
            loader_element.text)

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_unknown_loader_path(
            self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.dict(
                self.test_driver.KNOWN_BOOT_LOADERS, {}, clear=True):
            with mock.patch.object(
                    self.test_driver, 'get_power_state', return_value='Off'):
                self.assertRaises(
                    error.FishyError, self.test_driver.set_boot_mode,
                    self.uuid, 'Uefi')

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_no_os(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        tree = ET.fromstring(data)
        os_element = tree.find('os')
        tree.remove(os_element)

        data = ET.tostring(tree)

        conn_mock = libvirt_mock.return_value
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

        conn_mock = libvirt_mock.return_value
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

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.assertRaises(
                error.FishyError, self.test_driver.set_boot_mode,
                self.uuid, 'Uefi')

    @mock.patch('libvirt.open', autospec=True)
    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_set_boot_mode_no_type(self, libvirt_mock, libvirt_rw_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()

        tree = ET.fromstring(data)
        os_element = tree.find('os')
        type_element = os_element.find('type')
        os_element.remove(type_element)

        data = ET.tostring(tree)

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByUUID.return_value
        domain_mock.XMLDesc.return_value = data

        with mock.patch.object(
                self.test_driver, 'get_power_state', return_value='Off'):
            self.test_driver.set_boot_mode(self.uuid, 'UEFI')

        conn_mock = libvirt_rw_mock.return_value
        xml_document = conn_mock.defineXML.call_args[0][0]
        tree = ET.fromstring(xml_document)
        os_element = tree.find('os')
        # NOTE(etingof): should enforce default loader
        self.assertIsNone(os_element.find('loader'))

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

        expected_disk = ('<disk device="cdrom" type="file">'
                         '<target bus="ide" dev="hdc" />'
                         '<address bus="0" controller="0" '
                         'target="0" type="drive" unit="0" />')

        # NOTE(rpittau): starting from Python 3.8 the tostring() function
        # preserves the attribute order specified by the user.
        if sys.version_info[1] >= 8:
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
                         '<target bus="sata" dev="sdc" />'
                         '<address bus="0" controller="0" '
                         'target="0" type="drive" unit="0" />')

        # NOTE(rpittau): starting from Python 3.8 the tostring() function
        # preserves the attribute order specified by the user.
        if sys.version_info[1] >= 8:
            expected_disk = ('<disk type="file" device="cdrom">'
                             '<target dev="sdc" bus="sata" />'
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

        expected_disk = ('<disk device="cdrom" type="file">'
                         '<target bus="sata" dev="sdc" />'
                         '<address bus="0" controller="0" '
                         'target="0" type="drive" unit="1" />')

        # NOTE(rpittau): starting from Python 3.8 the tostring() function
        # preserves the attribute order specified by the user.
        if sys.version_info[1] >= 8:
            expected_disk = ('<disk type="file" device="cdrom">'
                             '<target dev="sdc" bus="sata" />'
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

        expected_disk = ('<disk device="cdrom" type="file">'
                         '<target bus="scsi" dev="sdc" />'
                         '<address bus="0" controller="0" '
                         'target="0" type="drive" unit="1" />')

        # NOTE(rpittau): starting from Python 3.8 the tostring() function
        # preserves the attribute order specified by the user.
        if sys.version_info[1] >= 8:
            expected_disk = ('<disk type="file" device="cdrom">'
                             '<target dev="sdc" bus="scsi" />'
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
