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

from oslotest import base
from six.moves import mock

from sushy_tools.emulator import main


@mock.patch.object(main, 'DRIVER')  # This enables libvirt driver
class EmulatorTestCase(base.BaseTestCase):

    name = 'QEmu-fedora-i686'
    uuid = 'c7a5fdbd-cdaf-9455-926a-d65c16db1809'

    def setUp(self):
        main.DRIVER = None
        self.app = main.app.test_client()

        super(EmulatorTestCase, self).setUp()

    def test_error(self, driver_mock):
        driver_mock.return_value.get_power_state.side_effect = (
            Exception('Fish is dead'))
        response = self.app.get('/redfish/v1/Systems/' + self.uuid)

        self.assertEqual(500, response.status_code)

    def test_root_resource(self, driver_mock):
        response = self.app.get('/redfish/v1/')
        self.assertEqual(200, response.status_code)
        self.assertEqual('RedvirtService', response.json['Id'])

    def test_collection_resource(self, driver_mock):
        type(driver_mock.return_value).systems = mock.PropertyMock(
            return_value=['host0', 'host1'])
        response = self.app.get('/redfish/v1/Systems')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id': '/redfish/v1/Systems/host0'},
                         response.json['Members'][0])
        self.assertEqual({'@odata.id': '/redfish/v1/Systems/host1'},
                         response.json['Members'][1])

    def test_system_resource_get(self, driver_mock):
        driver_mock.return_value.uuid.return_value = 'zzzz-yyyy-xxxx'
        driver_mock.return_value.get_power_state.return_value = 'On'
        driver_mock.return_value.get_total_memory.return_value = 1
        driver_mock.return_value.get_total_cpus.return_value = 2
        driver_mock.return_value.get_boot_device.return_value = 'Cd'
        driver_mock.return_value.get_boot_mode.return_value = 'Legacy'

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertEqual('xxxx-yyyy-zzzz', response.json['Id'])
        self.assertEqual('zzzz-yyyy-xxxx', response.json['UUID'])
        self.assertEqual('On', response.json['PowerState'])
        self.assertEqual(
            1, response.json['MemorySummary']['TotalSystemMemoryGiB'])
        self.assertEqual(2, response.json['ProcessorSummary']['Count'])
        self.assertEqual(
            'Cd', response.json['Boot']['BootSourceOverrideTarget'])
        self.assertEqual(
            'Legacy', response.json['Boot']['BootSourceOverrideMode'])

    def test_system_resource_patch(self, driver_mock):
        data = {'Boot': {'BootSourceOverrideTarget': 'Cd'}}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(204, response.status_code)
        set_boot_device = driver_mock.return_value.set_boot_device
        set_boot_device.assert_called_once_with('xxxx-yyyy-zzzz', 'Cd')

    def test_system_reset_action_on(self, driver_mock):
        data = {'ResetType': 'On'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = driver_mock.return_value.set_power_state
        set_power_state.assert_called_once_with('xxxx-yyyy-zzzz', 'On')

    def test_system_reset_action_forceon(self, driver_mock):
        data = {'ResetType': 'ForceOn'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = driver_mock.return_value.set_power_state
        set_power_state.assert_called_once_with('xxxx-yyyy-zzzz', 'ForceOn')

    def test_system_reset_action_forceoff(self, driver_mock):
        data = {'ResetType': 'ForceOff'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = driver_mock.return_value.set_power_state
        set_power_state.assert_called_once_with('xxxx-yyyy-zzzz', 'ForceOff')

    def test_system_reset_action_shutdown(self, driver_mock):
        data = {'ResetType': 'GracefulShutdown'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = driver_mock.return_value.set_power_state
        set_power_state.assert_called_once_with(
            'xxxx-yyyy-zzzz', 'GracefulShutdown')

    def test_system_reset_action_restart(self, driver_mock):
        data = {'ResetType': 'GracefulRestart'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = driver_mock.return_value.set_power_state
        set_power_state.assert_called_once_with(
            'xxxx-yyyy-zzzz', 'GracefulRestart')

    def test_system_reset_action_forcerestart(self, driver_mock):
        data = {'ResetType': 'ForceRestart'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = driver_mock.return_value.set_power_state
        set_power_state.assert_called_once_with(
            'xxxx-yyyy-zzzz', 'ForceRestart')

    def test_system_reset_action_nmi(self, driver_mock):
        data = {'ResetType': 'Nmi'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = driver_mock.return_value.set_power_state
        set_power_state.assert_called_once_with('xxxx-yyyy-zzzz', 'Nmi')

    @mock.patch.dict(main.app.config, {}, clear=True)
    def test_instance_denied_allow_all(self, driver_mock):
        self.assertFalse(main.instance_denied(identity='x'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {}})
    def test_instance_denied_disallow_all(self, driver_mock):
        self.assertTrue(main.instance_denied(identity='a'))

    def test_instance_denied_undefined_option(self, driver_mock):
        with mock.patch.dict(main.app.config):
            main.app.config.pop('SUSHY_EMULATOR_ALLOWED_INSTANCES', None)
            self.assertFalse(main.instance_denied(identity='a'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {'a'}})
    def test_instance_denied_allow_some(self, driver_mock):
        self.assertFalse(main.instance_denied(identity='a'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {'a'}})
    def test_instance_denied_disallow_some(self, driver_mock):
        self.assertTrue(main.instance_denied(identity='b'))

    def test_get_bios(self, driver_mock):
        driver_mock.return_value.get_bios.return_value = {
            "attribute 1": "value 1",
            "attribute 2": "value 2"}
        response = self.app.get('/redfish/v1/Systems/' + self.uuid + '/BIOS')

        self.assertEqual(200, response.status_code)
        self.assertEqual('BIOS', response.json['Id'])
        self.assertEqual({"attribute 1": "value 1",
                          "attribute 2": "value 2"},
                         response.json['Attributes'])

    def test_get_bios_existing(self, driver_mock):
        driver_mock.return_value.get_bios.return_value = {
            "attribute 1": "value 1", "attribute 2": "value 2"}
        response = self.app.get(
            '/redfish/v1/Systems/' + self.uuid + '/BIOS/Settings')

        self.assertEqual(200, response.status_code)
        self.assertEqual('Settings', response.json['Id'])
        self.assertEqual({"attribute 1": "value 1",
                          "attribute 2": "value 2"},
                         response.json['Attributes'])

    def test_bios_settings_patch(self, driver_mock):
        data = {'Attributes': {'key': 'value'}}
        response = self.app.patch(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS/Settings',
            json=data)
        self.assertEqual(204, response.status_code)
        driver_mock.return_value.set_bios.assert_called_once_with(
            'xxxx-yyyy-zzzz', {'key': 'value'})

    def test_set_bios(self, driver_mock):
        data = {'Attributes': {'key': 'value'}}
        response = self.app.patch(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS/Settings',
            json=data)

        self.assertEqual(204, response.status_code)
        driver_mock.return_value.set_bios.assert_called_once_with(
            'xxxx-yyyy-zzzz', data['Attributes'])

    def test_reset_bios(self, driver_mock):
        response = self.app.post('/redfish/v1/Systems/' + self.uuid +
                                 '/BIOS/Actions/Bios.ResetBios')
        self.assertEqual(204, response.status_code)
        driver_mock.return_value.reset_bios.assert_called_once_with(self.uuid)

    def test_ethernet_interfaces_collection(self, driver_mock):
        driver_mock.return_value.get_nics.return_value = [
            {'id': 'nic1', 'mac': '52:54:00:4e:5d:37'},
            {'id': 'nic2', 'mac': '00:11:22:33:44:55'}]
        response = self.app.get('redfish/v1/Systems/' + self.uuid +
                                '/EthernetInterfaces')

        self.assertEqual(200, response.status_code)
        self.assertEqual('Ethernet Interface Collection',
                         response.json['Name'])
        self.assertEqual(2, response.json['Members@odata.count'])
        self.assertEqual(['/redfish/v1/Systems/' + self.uuid +
                          '/EthernetInterfaces/nic1',
                          '/redfish/v1/Systems/' + self.uuid +
                          '/EthernetInterfaces/nic2'],
                         [m['@odata.id'] for m in response.json['Members']])

    def test_ethernet_interfaces_collection_empty(self, driver_mock):
        driver_mock.return_value.get_nics.return_value = []
        response = self.app.get('redfish/v1/Systems/' + self.uuid +
                                '/EthernetInterfaces')

        self.assertEqual(200, response.status_code)
        self.assertEqual('Ethernet Interface Collection',
                         response.json['Name'])
        self.assertEqual(0, response.json['Members@odata.count'])
        self.assertEqual([], response.json['Members'])

    def test_ethernet_interface(self, driver_mock):
        driver_mock.return_value.get_nics.return_value = [
            {'id': 'nic1', 'mac': '52:54:00:4e:5d:37'},
            {'id': 'nic2', 'mac': '00:11:22:33:44:55'}]
        response = self.app.get('/redfish/v1/Systems/' + self.uuid +
                                '/EthernetInterfaces/nic2')

        self.assertEqual(200, response.status_code)
        self.assertEqual('nic2', response.json['Id'])
        self.assertEqual('VNIC nic2', response.json['Name'])
        self.assertEqual('00:11:22:33:44:55',
                         response.json['PermanentMACAddress'])
        self.assertEqual('00:11:22:33:44:55',
                         response.json['MACAddress'])
        self.assertEqual('/redfish/v1/Systems/' + self.uuid +
                         '/EthernetInterfaces/nic2',
                         response.json['@odata.id'])

    def test_ethernet_interface_not_found(self, driver_mock):
        driver_mock.return_value.get_nics.return_value = [
            {'id': 'nic1', 'mac': '52:54:00:4e:5d:37'},
            {'id': 'nic2', 'mac': '00:11:22:33:44:55'}]
        response = self.app.get('/redfish/v1/Systems/' + self.uuid +
                                '/EthernetInterfaces/nic3')

        self.assertEqual(404, response.status_code)
