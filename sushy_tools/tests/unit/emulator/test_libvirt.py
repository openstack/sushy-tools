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

import json
import libvirt

from oslotest import base
from six.moves import mock

from sushy_tools.emulator.drivers.libvirtdriver import LibvirtDriver
from sushy_tools.emulator import main
from sushy_tools.error import FishyError


class EmulatorTestCase(base.BaseTestCase):

    def setUp(self):
        self.app = main.app.test_client()

        # This enables libvirt driver
        main.driver = None
        self.test_driver = LibvirtDriver()
        super(EmulatorTestCase, self).setUp()

    def test_root_resource(self):
        response = self.app.get('/redfish/v1/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(True, bool(response.json))

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_collection_resource(self, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        conn_mock.listDefinedDomains.return_value = ['host0', 'host1']

        response = self.app.get('/redfish/v1/Systems')
        self.assertEqual(response.status_code, 200)
        hosts = ['/redfish/v1/Systems/%s' % x.values()
                 for x in response.json['Members']]
        self.assertEqual(hosts, hosts)

    @mock.patch('libvirt.openReadOnly', autospec=True)
    def test_system_resource_get(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()
        domain_mock = mock.Mock()
        domain_mock.XMLDesc.return_value = data
        domain_mock.isActive.return_value = True
        domain_mock.maxMemory.return_value = 1024 * 1024
        domain_mock.UUIDString.return_value = 'zzzz-yyyy-xxxx'
        domain_mock.maxVcpus.return_value = 2

        conn_mock = libvirt_mock.return_value
        conn_mock.lookupByName.return_value = domain_mock

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['Id'], 'xxxx-yyyy-zzzz')
        self.assertEqual(response.json['UUID'], 'zzzz-yyyy-xxxx')
        self.assertEqual(response.json['PowerState'], 'On')
        self.assertEqual(
            response.json['MemorySummary']['TotalSystemMemoryGiB'], 1)
        self.assertEqual(response.json['ProcessorSummary']['Count'], 2)
        self.assertEqual(
            response.json['Boot']['BootSourceOverrideTarget'], 'Cd')
        self.assertEqual(
            response.json['Boot']['BootSourceOverrideMode'], 'Legacy')

    @mock.patch('libvirt.open', autospec=True)
    def test_system_resource_patch(self, libvirt_mock):

        with open('sushy_tools/tests/unit/emulator/domain.xml', 'r') as f:
            data = f.read()
        domain_mock = mock.Mock()
        domain_mock.XMLDesc.return_value = data

        conn_mock = libvirt_mock.return_value
        conn_mock.lookupByName.return_value = domain_mock
        conn_mock.defineXML = mock.Mock()
        data0 = json.dumps({'Boot': {'BootSourceOverrideTarget': 'Cd'}})
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  data=data0, content_type='application/json')
        self.assertEqual(response.status, '204 NO CONTENT')

    @mock.patch('libvirt.open', autospec=True)
    def test_system_reset_action_on(self, libvirt_mock):
        domain_mock = mock.Mock()
        domain_mock.isActive.return_value = True

        conn_mock = libvirt_mock.return_value
        conn_mock.lookupByName.return_value = domain_mock

        data = json.dumps({'ResetType': 'On'})
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            data=data, content_type='application/json')
        self.assertEqual(response.status, '204 NO CONTENT')
        domain_mock.create.assert_not_called()

    @mock.patch('libvirt.open', autospec=True)
    def test_system_reset_action_forceon(self, libvirt_mock):
        domain_mock = mock.Mock()
        domain_mock.isActive.return_value = True

        conn_mock = libvirt_mock.return_value
        conn_mock.lookupByName.return_value = domain_mock
        data = json.dumps({'ResetType': 'ForceOn'})
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            data=data, content_type='application/json')
        self.assertEqual(response.status, '204 NO CONTENT')
        domain_mock.create.assert_not_called()

    @mock.patch('libvirt.open', autospec=True)
    def test_system_reset_action_forceoff(self, libvirt_mock):
        domain_mock = mock.Mock()
        domain_mock.isActive.return_value = True

        conn_mock = libvirt_mock.return_value
        conn_mock.lookupByName.return_value = domain_mock
        data = json.dumps({'ResetType': 'ForceOff'})
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            data=data, content_type='application/json')
        self.assertEqual(response.status, '204 NO CONTENT')
        domain_mock.destroy.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_system_reset_action_shutdown(self, libvirt_mock):
        domain_mock = mock.Mock()
        domain_mock.isActive.return_value = True

        conn_mock = libvirt_mock.return_value
        conn_mock.lookupByName.return_value = domain_mock
        data = json.dumps({'ResetType': 'GracefulShutdown'})
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            data=data, content_type='application/json')
        self.assertEqual(response.status, '204 NO CONTENT')
        domain_mock.shutdown.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_system_reset_action_restart(self, libvirt_mock):
        domain_mock = mock.Mock()
        domain_mock.isActive.return_value = True

        conn_mock = libvirt_mock.return_value
        conn_mock.lookupByName.return_value = domain_mock
        data = json.dumps({'ResetType': 'GracefulRestart'})
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            data=data, content_type='application/json')
        self.assertEqual(response.status, '204 NO CONTENT')
        domain_mock.reboot.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_system_reset_action_forcerestart(self, libvirt_mock):
        domain_mock = mock.Mock()
        domain_mock.isActive.return_value = True

        conn_mock = libvirt_mock.return_value
        conn_mock.lookupByName.return_value = domain_mock
        data = json.dumps({'ResetType': 'ForceRestart'})
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            data=data, content_type='application/json')
        self.assertEqual(response.status, '204 NO CONTENT')
        domain_mock.reset.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_system_reset_action_nmi(self, libvirt_mock):
        domain_mock = mock.Mock()
        domain_mock.isActive.return_value = True

        conn_mock = libvirt_mock.return_value
        conn_mock.lookupByName.return_value = domain_mock
        data = json.dumps({'ResetType': 'Nmi'})
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            data=data, content_type='application/json')
        self.assertEqual(response.status, '204 NO CONTENT')
        domain_mock.injectNMI.assert_called_once_with()

    @mock.patch('libvirt.open', autospec=True)
    def test_get_bios(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByName.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        bios_attributes = self.test_driver.get_bios('xxx-yyy-zzz')
        self.assertEqual(LibvirtDriver.DEFAULT_BIOS_ATTRIBUTES,
                         bios_attributes)
        self.assertEqual(1, conn_mock.defineXML.call_count)

    @mock.patch('libvirt.open', autospec=True)
    def test_get_bios_existing(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByName.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        bios_attributes = self.test_driver.get_bios('xxx-yyy-zzz')
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
        domain_mock = conn_mock.lookupByName.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        self.test_driver.set_bios('xxx-yyy-zzz',
                                  {"BootMode": "Uefi",
                                   "ProcTurboMode": "Enabled"})
        self.assertEqual(1, conn_mock.defineXML.call_count)

    @mock.patch('libvirt.open', autospec=True)
    def test_reset_bios(self, libvirt_mock):
        with open('sushy_tools/tests/unit/emulator/domain_bios.xml') as f:
            domain_xml = f.read()

        conn_mock = libvirt_mock.return_value
        domain_mock = conn_mock.lookupByName.return_value
        domain_mock.XMLDesc.return_value = domain_xml

        self.test_driver.reset_bios('xxx-yyy-zzz')
        self.assertEqual(1, conn_mock.defineXML.call_count)

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
        domain_mock = conn_mock.lookupByName.return_value
        domain_mock.XMLDesc.return_value = domain_xml
        conn_mock.defineXML.side_effect = libvirt.libvirtError(
            'because I can')

        self.assertRaises(FishyError,
                          self.test_driver._process_bios,
                          'xxx-yyy-zzz',
                          {"BootMode": "Uefi",
                           "ProcTurboMode": "Enabled"})
