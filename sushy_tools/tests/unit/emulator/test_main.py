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

from sushy_tools.emulator import main
from sushy_tools import error


@mock.patch('sushy_tools.emulator.main.Resources')
class EmulatorTestCase(base.BaseTestCase):

    name = 'QEmu-fedora-i686'
    uuid = 'c7a5fdbd-cdaf-9455-926a-d65c16db1809'

    def setUp(self):
        self.app = main.app.test_client()

        super(EmulatorTestCase, self).setUp()

    def test_error(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_power_state.side_effect = Exception('Fish is dead')
        response = self.app.get('/redfish/v1/Systems/' + self.uuid)

        self.assertEqual(500, response.status_code)

    def test_root_resource(self, resources_mock):
        response = self.app.get('/redfish/v1/')
        self.assertEqual(200, response.status_code)
        self.assertEqual('RedvirtService', response.json['Id'])

    def test_chassis_collection_resource(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        chassis_mock = resources_mock.chassis
        chassis_mock.chassis = ['chassis0', 'chassis1']
        response = self.app.get('/redfish/v1/Chassis')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id': '/redfish/v1/Chassis/chassis0'},
                         response.json['Members'][0])
        self.assertEqual({'@odata.id': '/redfish/v1/Chassis/chassis1'},
                         response.json['Members'][1])

    def test_chassis_resource_get(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        chassis_mock = resources_mock.chassis
        chassis_mock.chassis = ['xxxx-yyyy-zzzz']
        chassis_mock.uuid.return_value = 'xxxx-yyyy-zzzz'
        chassis_mock.name.return_value = 'name'
        managers_mock = resources_mock.managers
        managers_mock.managers = ['man1']
        systems_mock = resources_mock.systems
        systems_mock.systems = ['sys1']
        indicators_mock = resources_mock.indicators
        indicators_mock.get_indicator_state.return_value = 'Off'

        response = self.app.get('/redfish/v1/Chassis/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertEqual('xxxx-yyyy-zzzz', response.json['Id'])
        self.assertEqual('xxxx-yyyy-zzzz', response.json['UUID'])
        self.assertEqual('Off', response.json['IndicatorLED'])
        self.assertEqual(
            {'@odata.id': '/redfish/v1/Chassis/xxxx-yyyy-zzzz/Thermal'},
            response.json['Thermal'])
        self.assertEqual([{'@odata.id': '/redfish/v1/Systems/sys1'}],
                         response.json['Links']['ComputerSystems'])
        self.assertEqual([{'@odata.id': '/redfish/v1/Managers/man1'}],
                         response.json['Links']['ManagedBy'])
        self.assertEqual([{'@odata.id': '/redfish/v1/Managers/man1'}],
                         response.json['Links']['ManagersInChassis'])

    def test_chassis_thermal(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        chassis_mock = resources_mock.chassis
        chassis_mock.chassis = [self.uuid]
        chassis_mock.uuid.return_value = self.uuid
        systems_mock = resources_mock.systems
        systems_mock.systems = ['sys1']

        response = self.app.get('/redfish/v1/Chassis/xxxx-yyyy-zzzz/Thermal')

        self.assertEqual(200, response.status_code)
        self.assertEqual('Thermal', response.json['Id'])
        self.assertEqual(
            '/redfish/v1/Chassis/xxxx-yyyy-zzzz/Thermal#/Temperatures/0',
            response.json['Temperatures'][0]['@odata.id'])
        self.assertEqual(
            {'@odata.id': '/redfish/v1/Systems/sys1/Processors/CPU'},
            response.json['Temperatures'][0]['RelatedItem'][0])
        self.assertEqual(
            '/redfish/v1/Chassis/xxxx-yyyy-zzzz/Thermal#/Fans/0',
            response.json['Fans'][0]['@odata.id'])
        self.assertEqual(
            {'@odata.id': '/redfish/v1/Chassis/xxxx-yyyy-zzzz'},
            response.json['Fans'][0]['RelatedItem'][0])

    def test_chassis_indicator_set_ok(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        indicators_mock = resources_mock.indicators
        chassis_mock = resources_mock.chassis
        chassis_mock.uuid.return_value = self.uuid

        data = {'IndicatorLED': 'Off'}
        response = self.app.patch('/redfish/v1/Chassis/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(204, response.status_code)
        set_indicator_state = indicators_mock.set_indicator_state
        set_indicator_state.assert_called_once_with(self.uuid, 'Off')

    def test_chassis_indicator_set_fail(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        indicators_mock = resources_mock.indicators
        set_indicator_state = indicators_mock.set_indicator_state
        set_indicator_state.side_effect = error.FishyError
        data = {'IndicatorLED': 'Blah'}
        response = self.app.patch('/redfish/v1/Chassis/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(500, response.status_code)

    def test_manager_collection_resource(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        managers_mock = resources_mock.managers
        type(managers_mock).managers = mock.PropertyMock(
            return_value=['bmc0', 'bmc1'])
        response = self.app.get('/redfish/v1/Managers')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id': '/redfish/v1/Managers/bmc0'},
                         response.json['Members'][0])
        self.assertEqual({'@odata.id': '/redfish/v1/Managers/bmc1'},
                         response.json['Members'][1])

    def test_manager_resource_get(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.systems = ['xxx']
        managers_mock = resources_mock.managers
        managers_mock.managers = ['xxxx-yyyy-zzzz']
        managers_mock.uuid.return_value = 'xxxx-yyyy-zzzz'
        managers_mock.name.return_value = 'name'
        chassis_mock = resources_mock.chassis
        chassis_mock.chassis = ['chassis0']

        response = self.app.get('/redfish/v1/Managers/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertEqual('xxxx-yyyy-zzzz', response.json['Id'])
        self.assertEqual('xxxx-yyyy-zzzz', response.json['UUID'])
        self.assertEqual('xxxx-yyyy-zzzz',
                         response.json['ServiceEntryPointUUID'])
        self.assertEqual([{'@odata.id': '/redfish/v1/Systems/xxx'}],
                         response.json['Links']['ManagerForServers'])
        self.assertEqual([{'@odata.id': '/redfish/v1/Chassis/chassis0'}],
                         response.json['Links']['ManagerForChassis'])

    def test_system_collection_resource(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems

        type(systems_mock).systems = mock.PropertyMock(
            return_value=['host0', 'host1'])
        response = self.app.get('/redfish/v1/Systems')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id': '/redfish/v1/Systems/host0'},
                         response.json['Members'][0])
        self.assertEqual({'@odata.id': '/redfish/v1/Systems/host1'},
                         response.json['Members'][1])

    def test_system_resource_get(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_total_memory.return_value = 1
        systems_mock.get_total_cpus.return_value = 2
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.return_value = 'Legacy'
        managers_mock = resources_mock.managers
        managers_mock.managers = ['aaaa-bbbb-cccc']
        chassis_mock = resources_mock.chassis
        chassis_mock.chassis = ['chassis0']
        indicators_mock = resources_mock.indicators
        indicators_mock.get_indicator_state.return_value = 'Off'

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertEqual('xxxx-yyyy-zzzz', response.json['Id'])
        self.assertEqual('zzzz-yyyy-xxxx', response.json['UUID'])
        self.assertEqual('On', response.json['PowerState'])
        self.assertEqual('Off', response.json['IndicatorLED'])
        self.assertEqual(
            1, response.json['MemorySummary']['TotalSystemMemoryGiB'])
        self.assertEqual(2, response.json['ProcessorSummary']['Count'])
        self.assertEqual(
            'Cd', response.json['Boot']['BootSourceOverrideTarget'])
        self.assertEqual(
            'Legacy', response.json['Boot']['BootSourceOverrideMode'])
        self.assertEqual(
            [{'@odata.id': '/redfish/v1/Managers/aaaa-bbbb-cccc'}],
            response.json['Links']['ManagedBy'])
        self.assertEqual(
            [{'@odata.id': '/redfish/v1/Chassis/chassis0'}],
            response.json['Links']['Chassis'])

    def test_system_resource_patch(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'Boot': {'BootSourceOverrideTarget': 'Cd'}}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(204, response.status_code)
        set_boot_device = systems_mock.set_boot_device
        set_boot_device.assert_called_once_with('xxxx-yyyy-zzzz', 'Cd')

    def test_system_reset_action_on(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'ResetType': 'On'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = systems_mock.set_power_state
        set_power_state.assert_called_once_with('xxxx-yyyy-zzzz', 'On')

    def test_system_reset_action_forceon(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'ResetType': 'ForceOn'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = systems_mock.set_power_state
        set_power_state.assert_called_once_with('xxxx-yyyy-zzzz', 'ForceOn')

    def test_system_reset_action_forceoff(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'ResetType': 'ForceOff'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = systems_mock.set_power_state
        set_power_state.assert_called_once_with('xxxx-yyyy-zzzz', 'ForceOff')

    def test_system_reset_action_shutdown(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'ResetType': 'GracefulShutdown'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = systems_mock.set_power_state
        set_power_state.assert_called_once_with(
            'xxxx-yyyy-zzzz', 'GracefulShutdown')

    def test_system_reset_action_restart(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'ResetType': 'GracefulRestart'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = systems_mock.set_power_state
        set_power_state.assert_called_once_with(
            'xxxx-yyyy-zzzz', 'GracefulRestart')

    def test_system_reset_action_forcerestart(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'ResetType': 'ForceRestart'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = systems_mock.set_power_state
        set_power_state.assert_called_once_with(
            'xxxx-yyyy-zzzz', 'ForceRestart')

    def test_system_reset_action_nmi(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'ResetType': 'Nmi'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(204, response.status_code)
        set_power_state = systems_mock.set_power_state
        set_power_state.assert_called_once_with('xxxx-yyyy-zzzz', 'Nmi')

    def test_system_indicator_set_ok(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        indicators_mock = resources_mock.indicators
        systems_mock = resources_mock.systems
        systems_mock.uuid.return_value = self.uuid

        data = {'IndicatorLED': 'Off'}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(204, response.status_code)
        set_indicator_state = indicators_mock.set_indicator_state
        set_indicator_state.assert_called_once_with(self.uuid, 'Off')

    def test_system_indicator_set_fail(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        indicators_mock = resources_mock.indicators
        set_indicator_state = indicators_mock.set_indicator_state
        set_indicator_state.side_effect = error.FishyError
        data = {'IndicatorLED': 'Blah'}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(500, response.status_code)

    @mock.patch.dict(main.app.config, {}, clear=True)
    def test_instance_denied_allow_all(self, resources_mock):
        self.assertFalse(main.instance_denied(identity='x'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {}})
    def test_instance_denied_disallow_all(self, resources_mock):
        self.assertTrue(main.instance_denied(identity='a'))

    def test_instance_denied_undefined_option(self, resources_mock):
        with mock.patch.dict(main.app.config):
            main.app.config.pop('SUSHY_EMULATOR_ALLOWED_INSTANCES', None)
            self.assertFalse(main.instance_denied(identity='a'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {'a'}})
    def test_instance_denied_allow_some(self, resources_mock):
        self.assertFalse(main.instance_denied(identity='a'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {'a'}})
    def test_instance_denied_disallow_some(self, resources_mock):
        self.assertTrue(main.instance_denied(identity='b'))

    def test_get_bios(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_bios.return_value = {
            "attribute 1": "value 1",
            "attribute 2": "value 2"
        }
        response = self.app.get('/redfish/v1/Systems/' + self.uuid + '/BIOS')

        self.assertEqual(200, response.status_code)
        self.assertEqual('BIOS', response.json['Id'])
        self.assertEqual({"attribute 1": "value 1",
                          "attribute 2": "value 2"},
                         response.json['Attributes'])

    def test_get_bios_existing(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_bios.return_value = {
            "attribute 1": "value 1",
            "attribute 2": "value 2"
        }
        response = self.app.get(
            '/redfish/v1/Systems/' + self.uuid + '/BIOS/Settings')

        self.assertEqual(200, response.status_code)
        self.assertEqual('Settings', response.json['Id'])
        self.assertEqual(
            {"attribute 1": "value 1",
             "attribute 2": "value 2"},
            response.json['Attributes'])

    def test_bios_settings_patch(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'Attributes': {'key': 'value'}}
        self.app.driver = systems_mock
        response = self.app.patch(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS/Settings',
            json=data)
        self.assertEqual(204, response.status_code)
        systems_mock.set_bios.assert_called_once_with(
            'xxxx-yyyy-zzzz', {'key': 'value'})

    def test_set_bios(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        data = {'Attributes': {'key': 'value'}}
        self.app.driver = systems_mock
        response = self.app.patch(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS/Settings',
            json=data)

        self.assertEqual(204, response.status_code)
        systems_mock.set_bios.assert_called_once_with(
            'xxxx-yyyy-zzzz', data['Attributes'])

    def test_reset_bios(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        self.app.driver = systems_mock
        response = self.app.post('/redfish/v1/Systems/%s/BIOS/Actions/'
                                 'Bios.ResetBios' % self.uuid)
        self.assertEqual(204, response.status_code)
        systems_mock.reset_bios.assert_called_once_with(self.uuid)

    def test_ethernet_interfaces_collection(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_nics.return_value = [
            {'id': 'nic1', 'mac': '52:54:00:4e:5d:37'},
            {'id': 'nic2', 'mac': '00:11:22:33:44:55'}]
        response = self.app.get('redfish/v1/Systems/%s/EthernetInterfaces'
                                % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('Ethernet Interface Collection',
                         response.json['Name'])
        self.assertEqual(2, response.json['Members@odata.count'])
        self.assertEqual(['/redfish/v1/Systems/%s/EthernetInterfaces/nic1'
                          % self.uuid,
                          '/redfish/v1/Systems/%s/EthernetInterfaces/nic2'
                          % self.uuid],
                         [m['@odata.id'] for m in response.json['Members']])

    def test_ethernet_interfaces_collection_empty(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_nics.return_value = []
        response = self.app.get('redfish/v1/Systems/%s/EthernetInterfaces'
                                % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('Ethernet Interface Collection',
                         response.json['Name'])
        self.assertEqual(0, response.json['Members@odata.count'])
        self.assertEqual([], response.json['Members'])

    def test_ethernet_interface(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_nics.return_value = [
            {'id': 'nic1', 'mac': '52:54:00:4e:5d:37'},
            {'id': 'nic2', 'mac': '00:11:22:33:44:55'}]
        response = self.app.get('/redfish/v1/Systems/%s/EthernetInterfaces/'
                                'nic2' % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('nic2', response.json['Id'])
        self.assertEqual('VNIC nic2', response.json['Name'])
        self.assertEqual('00:11:22:33:44:55',
                         response.json['PermanentMACAddress'])
        self.assertEqual('00:11:22:33:44:55',
                         response.json['MACAddress'])
        self.assertEqual('/redfish/v1/Systems/%s/EthernetInterfaces/nic2'
                         % self.uuid,
                         response.json['@odata.id'])

    def test_ethernet_interface_not_found(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_nics.return_value = [
            {'id': 'nic1', 'mac': '52:54:00:4e:5d:37'},
            {'id': 'nic2', 'mac': '00:11:22:33:44:55'}
        ]
        response = self.app.get('/redfish/v1/Systems/%s/EthernetInterfaces/'
                                'nic3' % self.uuid)

        self.assertEqual(404, response.status_code)

    def test_virtual_media_collection(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        managers_mock = resources_mock.managers
        managers_mock.managers = [self.uuid]
        managers_mock.uuid.return_value = self.uuid
        vmedia_mock = resources_mock.vmedia
        vmedia_mock.devices = ['CD', 'Floppy']

        response = self.app.get(
            'redfish/v1/Managers/%s/VirtualMedia' % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('Virtual Media Services', response.json['Name'])
        self.assertEqual(2, response.json['Members@odata.count'])
        self.assertEqual(
            ['/redfish/v1/Managers/%s/VirtualMedia/CD' % self.uuid,
             '/redfish/v1/Managers/%s/VirtualMedia/Floppy' % self.uuid],
            [m['@odata.id'] for m in response.json['Members']])

    def test_virtual_media_collection_empty(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        vmedia_mock = resources_mock.vmedia
        vmedia_mock.get_devices.return_value = []

        response = self.app.get(
            'redfish/v1/Managers/' + self.uuid + '/VirtualMedia')

        self.assertEqual(200, response.status_code)
        self.assertEqual('Virtual Media Services', response.json['Name'])
        self.assertEqual(0, response.json['Members@odata.count'])
        self.assertEqual([], response.json['Members'])

    def test_virtual_media(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        vmedia_mock = resources_mock.vmedia

        vmedia_mock.get_device_name.return_value = 'CD'
        vmedia_mock.get_device_media_types.return_value = [
            'CD', 'DVD']
        vmedia_mock.get_device_image_info.return_value = [
            'image-of-a-fish', 'fishy.iso', True, True]

        response = self.app.get(
            '/redfish/v1/Managers/%s/VirtualMedia/CD' % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('CD', response.json['Id'])
        self.assertEqual(['CD', 'DVD'], response.json['MediaTypes'])
        self.assertEqual('fishy.iso', response.json['Image'])
        self.assertEqual('image-of-a-fish', response.json['ImageName'])
        self.assertTrue(response.json['Inserted'])
        self.assertTrue(response.json['WriteProtected'])

    def test_virtual_media_not_found(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        vmedia_mock = resources_mock.vmedia
        vmedia_mock.get_device_name.side_effect = error.FishyError

        response = self.app.get(
            '/redfish/v1/Managers/%s/VirtualMedia/DVD-ROM' % self.uuid)

        self.assertEqual(404, response.status_code)

    def test_virtual_media_insert(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        vmedia_mock = resources_mock.vmedia

        response = self.app.post(
            '/redfish/v1/Managers/%s/VirtualMedia/CD/Actions/'
            'VirtualMedia.InsertMedia' % self.uuid,
            json={"Image": "http://fish.iso"})

        self.assertEqual(204, response.status_code)

        vmedia_mock.insert_image.called_once_with(
            'CD', 'http://fish.iso', True, False)

    def test_virtual_media_eject(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        vmedia_mock = resources_mock.vmedia

        response = self.app.post(
            '/redfish/v1/Managers/%s/VirtualMedia/CD/Actions/'
            'VirtualMedia.EjectMedia' % self.uuid,
            json={})

        self.assertEqual(204, response.status_code)

        vmedia_mock.eject_image.called_once_with('CD')

    def test_simple_storage_collection(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_simple_storage_collection.return_value = {
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
        response = self.app.get('redfish/v1/Systems/%s/SimpleStorage'
                                % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('Simple Storage Collection',
                         response.json['Name'])
        self.assertEqual(2, response.json['Members@odata.count'])
        self.assertEqual({'/redfish/v1/Systems/%s/SimpleStorage/virtio'
                          % self.uuid,
                          '/redfish/v1/Systems/%s/SimpleStorage/ide'
                          % self.uuid},
                         {m['@odata.id'] for m in response.json['Members']})

    def test_simple_storage_collection_empty(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_simple_storage_collection.return_value = []
        response = self.app.get('redfish/v1/Systems/%s/SimpleStorage'
                                % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('Simple Storage Collection',
                         response.json['Name'])
        self.assertEqual(0, response.json['Members@odata.count'])
        self.assertEqual([], response.json['Members'])

    def test_simple_storage(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_simple_storage_collection.return_value = {
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
        response = self.app.get('/redfish/v1/Systems/%s/SimpleStorage/virtio'
                                % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('virtio', response.json['Id'])
        self.assertEqual('virtio Controller', response.json['Name'])
        self.assertEqual('testVM1.img', response.json['Devices'][0]['Name'])
        self.assertEqual(100000, response.json['Devices'][0]['CapacityBytes'])
        self.assertEqual('sdb1', response.json['Devices'][1]['Name'])
        self.assertEqual(150000, response.json['Devices'][1]['CapacityBytes'])
        self.assertEqual('/redfish/v1/Systems/%s/SimpleStorage/virtio'
                         % self.uuid,
                         response.json['@odata.id'])

    def test_simple_storage_not_found(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.get_simple_storage_collection.return_value = {
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
        response = self.app.get('/redfish/v1/Systems/%s/SimpleStorage/scsi'
                                % self.uuid)

        self.assertEqual(404, response.status_code)

    def test_storage_collection_resource(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        resources_mock.storage.get_storage_col.return_value = [
            {
                "Id": "1",
                "Name": "Local Storage Controller",
                "StorageControllers": [
                    {
                        "MemberId": "0",
                        "Name": "Contoso Integrated RAID",
                        "SpeedGbps": 12
                    }
                ]
            }
        ]
        response = self.app.get('redfish/v1/Systems/vbmc-node/Storage')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id':
                          '/redfish/v1/Systems/vbmc-node/Storage/1'},
                         response.json['Members'][0])

    def test_storage_resource_get(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        resources_mock.storage.get_storage_col.return_value = [
            {
                "Id": "1",
                "Name": "Local Storage Controller",
                "StorageControllers": [
                    {
                        "MemberId": "0",
                        "Name": "Contoso Integrated RAID",
                        "SpeedGbps": 12
                    }
                ]
            }
        ]
        response = self.app.get('/redfish/v1/Systems/vbmc-node/Storage/1')

        self.assertEqual(200, response.status_code)
        self.assertEqual('1', response.json['Id'])
        self.assertEqual('Local Storage Controller', response.json['Name'])
        stg_ctl = response.json['StorageControllers'][0]
        self.assertEqual("0", stg_ctl['MemberId'])
        self.assertEqual("Contoso Integrated RAID", stg_ctl['Name'])
        self.assertEqual(12, stg_ctl['SpeedGbps'])

    def test_drive_resource_get(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        resources_mock.drives.get_drives.return_value = [
            {
                "Id": "32ADF365C6C1B7BD",
                "Name": "Drive Sample",
                "CapacityBytes": 899527000000,
                "Protocol": "SAS"
            }
        ]
        response = self.app.get('/redfish/v1/Systems/vbmc-node/Storage/1'
                                '/Drives/32ADF365C6C1B7BD')

        self.assertEqual(200, response.status_code)
        self.assertEqual('32ADF365C6C1B7BD', response.json['Id'])
        self.assertEqual('Drive Sample', response.json['Name'])
        self.assertEqual(899527000000, response.json['CapacityBytes'])
        self.assertEqual('SAS', response.json['Protocol'])

    def test_volume_collection_get(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        resources_mock.volumes.get_volumes_col.return_value = [
            {
                "libvirtPoolName": "sushyPool",
                "libvirtVolName": "testVol",
                "Id": "1",
                "Name": "Sample Volume 1",
                "VolumeType": "Mirrored",
                "CapacityBytes": 23748
            }
        ]
        resources_mock.systems.find_or_create_storage_volume.return_value = "1"
        response = self.app.get('/redfish/v1/Systems/vmc-node/Storage/1/'
                                'Volumes')

        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id':
                          '/redfish/v1/Systems/vmc-node/Storage/1/Volumes/1'},
                         response.json['Members'][0])

    def test_create_volume_post(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        systems_mock = resources_mock.systems
        systems_mock.find_or_create_storage_volume.return_value = "13087010612"
        data = {
            "Name": "Sample Volume 3",
            "VolumeType": "NonRedundant",
            "CapacityBytes": 23456
        }
        response = self.app.post('/redfish/v1/Systems/vmc-node/Storage/1/'
                                 'Volumes', json=data)

        self.assertEqual(201, response.status_code)
        self.assertEqual('http://localhost/redfish/v1/Systems/vmc-node/'
                         'Storage/1/Volumes/13087010612',
                         response.headers['Location'])

    def test_volume_resource_get(self, resources_mock):
        resources_mock = resources_mock.return_value.__enter__.return_value
        resources_mock.volumes.get_volumes_col.return_value = [
            {
                "libvirtPoolName": "sushyPool",
                "libvirtVolName": "testVol",
                "Id": "1",
                "Name": "Sample Volume 1",
                "VolumeType": "Mirrored",
                "CapacityBytes": 23748
            }
        ]
        resources_mock.systems.find_or_create_storage_volume.return_value = "1"
        response = self.app.get('/redfish/v1/Systems/vbmc-node/Storage/1/'
                                'Volumes/1')

        self.assertEqual(200, response.status_code)
        self.assertEqual('1', response.json['Id'])
        self.assertEqual('Sample Volume 1', response.json['Name'])
        self.assertEqual('Mirrored', response.json['VolumeType'])
        self.assertEqual(23748, response.json['CapacityBytes'])
