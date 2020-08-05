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


def patch_resource(name):
    def decorator(func):
        return mock.patch.object(main.Application, name,
                                 new_callable=mock.PropertyMock)(func)
    return decorator


class EmulatorTestCase(base.BaseTestCase):

    name = 'QEmu-fedora-i686'
    uuid = 'c7a5fdbd-cdaf-9455-926a-d65c16db1809'

    def setUp(self):
        self.app = main.app.test_client()

        super(EmulatorTestCase, self).setUp()


class CommonTestCase(EmulatorTestCase):

    @patch_resource('systems')
    def test_error(self, systems_mock):
        systems_mock.return_value.get_power_state.side_effect = Exception(
            'Fish is dead')
        response = self.app.get('/redfish/v1/Systems/' + self.uuid)

        self.assertEqual(500, response.status_code)

    def test_root_resource(self):
        response = self.app.get('/redfish/v1/')
        self.assertEqual(200, response.status_code)
        self.assertEqual('RedvirtService', response.json['Id'])


class ChassisTestCase(EmulatorTestCase):

    @patch_resource('chassis')
    def test_chassis_collection_resource(self, chassis_mock):
        chassis_mock.return_value.chassis = ['chassis0', 'chassis1']
        response = self.app.get('/redfish/v1/Chassis')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id': '/redfish/v1/Chassis/chassis0'},
                         response.json['Members'][0])
        self.assertEqual({'@odata.id': '/redfish/v1/Chassis/chassis1'},
                         response.json['Members'][1])

    @patch_resource('indicators')
    @patch_resource('systems')
    @patch_resource('managers')
    @patch_resource('chassis')
    def test_chassis_resource_get(self, chassis_mock, managers_mock,
                                  systems_mock, indicators_mock):
        chassis_mock = chassis_mock.return_value
        chassis_mock.chassis = ['xxxx-yyyy-zzzz']
        chassis_mock.uuid.return_value = 'xxxx-yyyy-zzzz'
        chassis_mock.name.return_value = 'name'
        managers_mock.return_value.managers = ['man1']
        systems_mock.return_value.systems = ['sys1']
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'

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

    @patch_resource('systems')
    @patch_resource('chassis')
    def test_chassis_thermal(self, chassis_mock, systems_mock):
        chassis_mock = chassis_mock.return_value
        chassis_mock.chassis = [self.uuid]
        chassis_mock.uuid.return_value = self.uuid
        systems_mock.return_value.systems = ['sys1']

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

    @patch_resource('indicators')
    @patch_resource('chassis')
    def test_chassis_indicator_set_ok(self, chassis_mock, indicators_mock):
        chassis_mock.return_value.uuid.return_value = self.uuid

        data = {'IndicatorLED': 'Off'}
        response = self.app.patch('/redfish/v1/Chassis/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(204, response.status_code)
        set_indicator_state = indicators_mock.return_value.set_indicator_state
        set_indicator_state.assert_called_once_with(self.uuid, 'Off')

    @patch_resource('indicators')
    @patch_resource('chassis')
    def test_chassis_indicator_set_fail(self, chassis_mock, indicators_mock):
        set_indicator_state = indicators_mock.return_value.set_indicator_state
        set_indicator_state.side_effect = error.FishyError
        data = {'IndicatorLED': 'Blah'}
        response = self.app.patch('/redfish/v1/Chassis/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(500, response.status_code)


class ManagersTestCase(EmulatorTestCase):

    @patch_resource('managers')
    def test_manager_collection_resource(self, managers_mock):
        type(managers_mock.return_value).managers = mock.PropertyMock(
            return_value=['bmc0', 'bmc1'])
        response = self.app.get('/redfish/v1/Managers')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id': '/redfish/v1/Managers/bmc0'},
                         response.json['Members'][0])
        self.assertEqual({'@odata.id': '/redfish/v1/Managers/bmc1'},
                         response.json['Members'][1])

    @patch_resource('managers')
    def test_manager_resource_get(self, managers_mock):
        managers_mock = managers_mock.return_value
        managers_mock.managers = ['xxxx-yyyy-zzzz']
        managers_mock.get_manager.return_value = {
            'UUID': 'xxxx-yyyy-zzzz',
            'Name': 'name',
            'Id': 'xxxx-yyyy-zzzz',
        }
        managers_mock.get_managed_systems.return_value = ['xxx']
        managers_mock.get_managed_chassis.return_value = ['chassis0']

        response = self.app.get('/redfish/v1/Managers/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual('xxxx-yyyy-zzzz', response.json['Id'])
        self.assertEqual('xxxx-yyyy-zzzz', response.json['UUID'])
        self.assertIsNone(response.json['ServiceEntryPointUUID'])
        self.assertEqual([{'@odata.id': '/redfish/v1/Systems/xxx'}],
                         response.json['Links']['ManagerForServers'])
        self.assertEqual([{'@odata.id': '/redfish/v1/Chassis/chassis0'}],
                         response.json['Links']['ManagerForChassis'])


class SystemsTestCase(EmulatorTestCase):

    @patch_resource('systems')
    def test_system_collection_resource(self, systems_mock):
        type(systems_mock.return_value).systems = mock.PropertyMock(
            return_value=['host0', 'host1'])
        response = self.app.get('/redfish/v1/Systems')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id': '/redfish/v1/Systems/host0'},
                         response.json['Members'][0])
        self.assertEqual({'@odata.id': '/redfish/v1/Systems/host1'},
                         response.json['Members'][1])

    @patch_resource('indicators')
    @patch_resource('chassis')
    @patch_resource('managers')
    @patch_resource('systems')
    def test_system_resource_get(self, systems_mock, managers_mock,
                                 chassis_mock, indicators_mock):
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_total_memory.return_value = 1
        systems_mock.get_total_cpus.return_value = 2
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.return_value = 'Legacy'
        managers_mock.return_value.get_managers_for_system.return_value = [
            'aaaa-bbbb-cccc']
        chassis_mock.return_value.chassis = ['chassis0']
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'

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

    @patch_resource('systems')
    def test_system_resource_patch(self, systems_mock):
        data = {'Boot': {'BootSourceOverrideTarget': 'Cd'}}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(204, response.status_code)
        set_boot_device = systems_mock.return_value.set_boot_device
        set_boot_device.assert_called_once_with('xxxx-yyyy-zzzz', 'Cd')

    @patch_resource('systems')
    def test_system_reset_action(self, systems_mock):
        set_power_state = systems_mock.return_value.set_power_state
        for reset_type in ('On', 'ForceOn', 'ForceOff', 'GracefulShutdown',
                           'GracefulRestart', 'ForceRestart', 'Nmi'):
            set_power_state.reset_mock()
            data = {'ResetType': reset_type}
            response = self.app.post(
                '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/'
                'ComputerSystem.Reset',
                json=data)
            self.assertEqual(204, response.status_code)
            set_power_state.assert_called_once_with('xxxx-yyyy-zzzz',
                                                    reset_type)

    @patch_resource('indicators')
    @patch_resource('systems')
    def test_system_indicator_set_ok(self, systems_mock, indicators_mock):
        systems_mock.return_value.uuid.return_value = self.uuid

        data = {'IndicatorLED': 'Off'}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(204, response.status_code)
        set_indicator_state = indicators_mock.return_value.set_indicator_state
        set_indicator_state.assert_called_once_with(self.uuid, 'Off')

    @patch_resource('indicators')
    @patch_resource('systems')
    def test_system_indicator_set_fail(self, systems_mock, indicators_mock):
        set_indicator_state = indicators_mock.return_value.set_indicator_state
        set_indicator_state.side_effect = error.FishyError
        data = {'IndicatorLED': 'Blah'}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(500, response.status_code)


class InstanceDeniedTestCase(EmulatorTestCase):

    @mock.patch.dict(main.app.config, {}, clear=True)
    def test_instance_denied_allow_all(self):
        self.assertFalse(main.instance_denied(identity='x'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {}})
    def test_instance_denied_disallow_all(self):
        self.assertTrue(main.instance_denied(identity='a'))

    def test_instance_denied_undefined_option(self):
        with mock.patch.dict(main.app.config):
            main.app.config.pop('SUSHY_EMULATOR_ALLOWED_INSTANCES', None)
            self.assertFalse(main.instance_denied(identity='a'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {'a'}})
    def test_instance_denied_allow_some(self):
        self.assertFalse(main.instance_denied(identity='a'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {'a'}})
    def test_instance_denied_disallow_some(self):
        self.assertTrue(main.instance_denied(identity='b'))


@patch_resource('systems')
class BiosTestCase(EmulatorTestCase):

    def test_get_bios(self, systems_mock):
        systems_mock.return_value.get_bios.return_value = {
            "attribute 1": "value 1",
            "attribute 2": "value 2"
        }
        response = self.app.get('/redfish/v1/Systems/' + self.uuid + '/BIOS')

        self.assertEqual(200, response.status_code)
        self.assertEqual('BIOS', response.json['Id'])
        self.assertEqual({"attribute 1": "value 1",
                          "attribute 2": "value 2"},
                         response.json['Attributes'])

    def test_get_bios_existing(self, systems_mock):
        systems_mock.return_value.get_bios.return_value = {
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

    def test_bios_settings_patch(self, systems_mock):
        data = {'Attributes': {'key': 'value'}}
        response = self.app.patch(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS/Settings',
            json=data)
        self.assertEqual(204, response.status_code)
        systems_mock.return_value.set_bios.assert_called_once_with(
            'xxxx-yyyy-zzzz', {'key': 'value'})

    def test_set_bios(self, systems_mock):
        data = {'Attributes': {'key': 'value'}}
        response = self.app.patch(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS/Settings',
            json=data)

        self.assertEqual(204, response.status_code)
        systems_mock.return_value.set_bios.assert_called_once_with(
            'xxxx-yyyy-zzzz', data['Attributes'])

    def test_reset_bios(self, systems_mock):
        response = self.app.post('/redfish/v1/Systems/%s/BIOS/Actions/'
                                 'Bios.ResetBios' % self.uuid)
        self.assertEqual(204, response.status_code)
        systems_mock.return_value.reset_bios.assert_called_once_with(self.uuid)


@patch_resource('systems')
class EthernetInterfacesTestCase(EmulatorTestCase):

    def test_ethernet_interfaces_collection(self, systems_mock):
        systems_mock.return_value.get_nics.return_value = [
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

    def test_ethernet_interfaces_collection_empty(self, systems_mock):
        systems_mock.return_value.get_nics.return_value = []
        response = self.app.get('redfish/v1/Systems/%s/EthernetInterfaces'
                                % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('Ethernet Interface Collection',
                         response.json['Name'])
        self.assertEqual(0, response.json['Members@odata.count'])
        self.assertEqual([], response.json['Members'])

    def test_ethernet_interface(self, systems_mock):
        systems_mock.return_value.get_nics.return_value = [
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

    def test_ethernet_interface_not_found(self, systems_mock):
        systems_mock.return_value.get_nics.return_value = [
            {'id': 'nic1', 'mac': '52:54:00:4e:5d:37'},
            {'id': 'nic2', 'mac': '00:11:22:33:44:55'}
        ]
        response = self.app.get('/redfish/v1/Systems/%s/EthernetInterfaces/'
                                'nic3' % self.uuid)

        self.assertEqual(404, response.status_code)


@patch_resource('vmedia')
@patch_resource('managers')
class VirtualMediaTestCase(EmulatorTestCase):

    def test_virtual_media_collection(self, managers_mock, vmedia_mock):
        managers_mock = managers_mock.return_value
        managers_mock.managers = [self.uuid]
        managers_mock.get_manager.return_value = {'UUID': self.uuid}
        vmedia_mock.return_value.devices = ['CD', 'Floppy']

        response = self.app.get(
            'redfish/v1/Managers/%s/VirtualMedia' % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('Virtual Media Services', response.json['Name'])
        self.assertEqual(2, response.json['Members@odata.count'])
        self.assertEqual(
            ['/redfish/v1/Managers/%s/VirtualMedia/CD' % self.uuid,
             '/redfish/v1/Managers/%s/VirtualMedia/Floppy' % self.uuid],
            [m['@odata.id'] for m in response.json['Members']])

    def test_virtual_media_collection_empty(self, managers_mock, vmedia_mock):
        vmedia_mock.return_value.get_devices.return_value = []

        response = self.app.get(
            'redfish/v1/Managers/' + self.uuid + '/VirtualMedia')

        self.assertEqual(200, response.status_code)
        self.assertEqual('Virtual Media Services', response.json['Name'])
        self.assertEqual(0, response.json['Members@odata.count'])
        self.assertEqual([], response.json['Members'])

    def test_virtual_media(self, managers_mock, vmedia_mock):
        vmedia_mock = vmedia_mock.return_value
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

    def test_virtual_media_not_found(self, managers_mock, vmedia_mock):
        vmedia_mock.return_value.get_device_name.side_effect = error.FishyError

        response = self.app.get(
            '/redfish/v1/Managers/%s/VirtualMedia/DVD-ROM' % self.uuid)

        self.assertEqual(404, response.status_code)

    def test_virtual_media_insert(self, managers_mock, vmedia_mock):
        response = self.app.post(
            '/redfish/v1/Managers/%s/VirtualMedia/CD/Actions/'
            'VirtualMedia.InsertMedia' % self.uuid,
            json={"Image": "http://fish.iso"})

        self.assertEqual(204, response.status_code)

        vmedia_mock.return_value.insert_image.called_once_with(
            'CD', 'http://fish.iso', True, False)

    def test_virtual_media_eject(self, managers_mock, vmedia_mock):
        response = self.app.post(
            '/redfish/v1/Managers/%s/VirtualMedia/CD/Actions/'
            'VirtualMedia.EjectMedia' % self.uuid,
            json={})

        self.assertEqual(204, response.status_code)

        vmedia_mock.return_value.eject_image.called_once_with('CD')


@patch_resource('systems')
class StorageTestCase(EmulatorTestCase):

    def test_simple_storage_collection(self, systems_mock):
        systems_mock = systems_mock.return_value
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

    def test_simple_storage_collection_empty(self, systems_mock):
        systems_mock = systems_mock.return_value
        systems_mock.get_simple_storage_collection.return_value = []
        response = self.app.get('redfish/v1/Systems/%s/SimpleStorage'
                                % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('Simple Storage Collection',
                         response.json['Name'])
        self.assertEqual(0, response.json['Members@odata.count'])
        self.assertEqual([], response.json['Members'])

    def test_simple_storage(self, systems_mock):
        systems_mock = systems_mock.return_value
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

    def test_simple_storage_not_found(self, systems_mock):
        systems_mock = systems_mock.return_value
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

    @patch_resource('storage')
    def test_storage_collection_resource(self, storage_mock, systems_mock):
        storage_mock.return_value.get_storage_col.return_value = [
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

    @patch_resource('storage')
    def test_storage_resource_get(self, storage_mock, systems_mock):
        storage_mock.return_value.get_storage_col.return_value = [
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

    @patch_resource('drives')
    def test_drive_resource_get(self, drives_mock, systems_mock):
        drives_mock.return_value.get_drives.return_value = [
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

    @patch_resource('volumes')
    def test_volume_collection_get(self, volumes_mock, systems_mock):
        volumes_mock.return_value.get_volumes_col.return_value = [
            {
                "libvirtPoolName": "sushyPool",
                "libvirtVolName": "testVol",
                "Id": "1",
                "Name": "Sample Volume 1",
                "VolumeType": "Mirrored",
                "CapacityBytes": 23748
            }
        ]
        systems_mock = systems_mock.return_value
        systems_mock.find_or_create_storage_volume.return_value = "1"
        response = self.app.get('/redfish/v1/Systems/vmc-node/Storage/1/'
                                'Volumes')

        self.assertEqual(200, response.status_code)
        self.assertEqual({'@odata.id':
                          '/redfish/v1/Systems/vmc-node/Storage/1/Volumes/1'},
                         response.json['Members'][0])

    @patch_resource('volumes')
    def test_create_volume_post(self, volumes_mock, systems_mock):
        systems_mock = systems_mock.return_value
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

    @patch_resource('volumes')
    def test_volume_resource_get(self, volumes_mock, systems_mock):
        volumes_mock.return_value.get_volumes_col.return_value = [
            {
                "libvirtPoolName": "sushyPool",
                "libvirtVolName": "testVol",
                "Id": "1",
                "Name": "Sample Volume 1",
                "VolumeType": "Mirrored",
                "CapacityBytes": 23748
            }
        ]
        systems_mock = systems_mock.return_value
        systems_mock.find_or_create_storage_volume.return_value = "1"
        response = self.app.get('/redfish/v1/Systems/vbmc-node/Storage/1/'
                                'Volumes/1')

        self.assertEqual(200, response.status_code)
        self.assertEqual('1', response.json['Id'])
        self.assertEqual('Sample Volume 1', response.json['Name'])
        self.assertEqual('Mirrored', response.json['VolumeType'])
        self.assertEqual(23748, response.json['CapacityBytes'])
