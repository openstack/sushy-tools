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

import os
import signal
import tempfile
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

    def set_feature_set(self, new_feature_set):
        main.app.config['SUSHY_EMULATOR_FEATURE_SET'] = new_feature_set
        self.addCleanup(
            lambda: main.app.config.pop('SUSHY_EMULATOR_FEATURE_SET', None)
        )


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

    def test_root_resource_only_vmedia(self):
        self.set_feature_set("vmedia")
        response = self.app.get('/redfish/v1/')
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {'Id', 'Name', 'RedfishVersion', 'UUID', 'Systems', 'Managers'},
            {x for x in response.json if not x.startswith('@')})

    def test_root_resource_minimum(self):
        self.set_feature_set("minimum")
        response = self.app.get('/redfish/v1/')
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {'Id', 'Name', 'RedfishVersion', 'UUID', 'Systems'},
            {x for x in response.json if not x.startswith('@')})


TEST_PASSWD = \
    b"admin:$2y$05$mYl8KMwM94l4LR/sw1teIeA6P2u8gfX16e8wvT7NmGgAM5r9jgLl."


class AuthenticatedTestCase(base.BaseTestCase):

    def setUp(self):
        super().setUp()
        self.auth_file = tempfile.NamedTemporaryFile()
        self.auth_file.write(TEST_PASSWD)
        self.auth_file.flush()
        self.addCleanup(self.auth_file.close)
        app = main.Application()
        app.configure(
            extra_config={'SUSHY_EMULATOR_AUTH_FILE': self.auth_file.name})
        self.app = app.test_client()

    def test_root_resource(self):
        response = self.app.get('/redfish/v1/')
        # 404 because this application does not have any routes
        self.assertEqual(404, response.status_code, response.data)

    def test_authenticated_resource(self):
        response = self.app.get('/redfish/v1/Systems/',
                                auth=('admin', 'password'))
        self.assertEqual(404, response.status_code, response.data)

    def test_authentication_failed(self):
        response = self.app.get('/redfish/v1/Systems/')
        self.assertEqual(401, response.status_code, response.data)


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
        managers_mock.get_datetime.return_value = {
            "DateTime": "2025-06-02T12:00:00+00:00",
            "DateTimeLocalOffset": "+00:00"}

        response = self.app.get('/redfish/v1/Managers/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual('xxxx-yyyy-zzzz', response.json['Id'])
        self.assertEqual('xxxx-yyyy-zzzz', response.json['UUID'])
        self.assertIsNone(response.json['ServiceEntryPointUUID'])
        self.assertEqual([{'@odata.id': '/redfish/v1/Systems/xxx'}],
                         response.json['Links']['ManagerForServers'])
        self.assertEqual([{'@odata.id': '/redfish/v1/Chassis/chassis0'}],
                         response.json['Links']['ManagerForChassis'])
        self.assertEqual({'@odata.id': '/redfish/v1/Systems/xxx/VirtualMedia'},
                         response.json['VirtualMedia'])

    @patch_resource('managers')
    def test_manager_resource_patch_valid_json(self, managers_mock):
        managers_mock = managers_mock.return_value
        managers_mock.set_datetime.return_value = None

        payload = {
            "DateTime": "2025-07-14T11:30:00+00:00",
            "DateTimeLocalOffset": "+00:00"}

        response = self.app.patch(
            '/redfish/v1/Managers/xxxx-yyyy-zzzz',
            json=payload)

        self.assertEqual(204, response.status_code)

    @patch_resource('managers')
    def test_manager_resource_patch_invalid_json(self, managers_mock):
        managers_mock = managers_mock.return_value
        managers_mock.set_datetime.return_value = None

        response = self.app.patch(
            '/redfish/v1/Managers/xxxx-yyyy-zzzz',
            data='not-json',
            content_type='application/json')

        self.assertEqual(400, response.status_code)

    @patch_resource('managers')
    def test_manager_resource_get_reduced_feature_set(self, managers_mock):
        self.set_feature_set("vmedia")
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
        self.assertNotIn('ServiceEntryPointUUID', response.json)
        self.assertEqual([{'@odata.id': '/redfish/v1/Systems/xxx'}],
                         response.json['Links']['ManagerForServers'])
        self.assertNotIn('Chassis', response.json['Links'])
        self.assertEqual({'@odata.id': '/redfish/v1/Systems/xxx/VirtualMedia'},
                         response.json['VirtualMedia'])


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

    @patch_resource('storage')
    @patch_resource('indicators')
    @patch_resource('chassis')
    @patch_resource('managers')
    @patch_resource('systems')
    def test_system_resource_get(self, systems_mock, managers_mock,
                                 chassis_mock, indicators_mock, storage_mock):
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
        self.assertEqual(
            {'@odata.id': '/redfish/v1/Systems/xxxx-yyyy-zzzz/VirtualMedia'},
            response.json['VirtualMedia'])

    @patch_resource('indicators')
    @patch_resource('chassis')
    @patch_resource('managers')
    @patch_resource('systems')
    def test_system_resource_get_reduced_feature_set(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock):
        self.set_feature_set("vmedia")
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.return_value = 'Legacy'
        managers_mock.return_value.get_managers_for_system.return_value = [
            'aaaa-bbbb-cccc']

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertEqual('xxxx-yyyy-zzzz', response.json['Id'])
        self.assertEqual('zzzz-yyyy-xxxx', response.json['UUID'])
        self.assertEqual('On', response.json['PowerState'])
        self.assertNotIn('IndicatorLED', response.json)
        self.assertNotIn('MemorySummary', response.json)
        self.assertNotIn('ProcessorSummary', response.json)
        self.assertNotIn('BiosVersion', response.json)
        self.assertNotIn('Bios', response.json)
        self.assertEqual(
            'Cd', response.json['Boot']['BootSourceOverrideTarget'])
        self.assertEqual(
            'Legacy', response.json['Boot']['BootSourceOverrideMode'])
        self.assertEqual(
            [{'@odata.id': '/redfish/v1/Managers/aaaa-bbbb-cccc'}],
            response.json['Links']['ManagedBy'])
        self.assertNotIn('Chassis', response.json['Links'])
        self.assertEqual(
            {'@odata.id': '/redfish/v1/Systems/xxxx-yyyy-zzzz/VirtualMedia'},
            response.json['VirtualMedia'])

    @patch_resource('indicators')
    @patch_resource('chassis')
    @patch_resource('managers')
    @patch_resource('systems')
    def test_system_resource_get_minimum_feature_set(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock):
        self.set_feature_set("minimum")
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.return_value = 'Legacy'
        managers_mock.return_value.get_managers_for_system.return_value = [
            'aaaa-bbbb-cccc']

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertEqual('xxxx-yyyy-zzzz', response.json['Id'])
        self.assertEqual('zzzz-yyyy-xxxx', response.json['UUID'])
        self.assertEqual('On', response.json['PowerState'])
        self.assertNotIn('IndicatorLED', response.json)
        self.assertNotIn('MemorySummary', response.json)
        self.assertNotIn('ProcessorSummary', response.json)
        self.assertNotIn('BiosVersion', response.json)
        self.assertNotIn('Bios', response.json)
        self.assertEqual(
            'Cd', response.json['Boot']['BootSourceOverrideTarget'])
        self.assertEqual(
            'Legacy', response.json['Boot']['BootSourceOverrideMode'])
        self.assertNotIn('ManagedBy', response.json['Links'])
        self.assertNotIn('Chassis', response.json['Links'])
        self.assertNotIn('VirtualMedia', response.json)

    @patch_resource('systems')
    def test_system_resource_patch(self, systems_mock):
        data = {'Boot': {'BootSourceOverrideTarget': 'Cd'}}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(204, response.status_code)
        set_boot_device = systems_mock.return_value.set_boot_device
        set_boot_device.assert_called_once_with('xxxx-yyyy-zzzz', 'Cd')

    @patch_resource('vmedia')
    @patch_resource('systems')
    def test_system_boot_http_uri(self, systems_mock, vmedia_mock):
        data = {'Boot': {'BootSourceOverrideMode': 'UEFI',
                         'BootSourceOverrideTarget': 'UefiHttp',
                         'HttpBootUri': 'http://test.url/boot.iso'}}
        insert_image = vmedia_mock.return_value.insert_image
        insert_image.return_value = '/path/to/file.iso'
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(204, response.status_code)
        insert_image.assert_called_once_with('xxxx-yyyy-zzzz', 'Cd',
                                             'http://test.url/boot.iso')
        set_boot_device = systems_mock.return_value.set_boot_device
        set_boot_image = systems_mock.return_value.set_boot_image
        set_boot_mode = systems_mock.return_value.set_boot_mode
        set_http_boot_uri = systems_mock.return_value.set_http_boot_uri
        set_boot_device.assert_called_once_with('xxxx-yyyy-zzzz', 'Cd')
        set_boot_image.assert_called_once_with(
            mock.ANY,
            'Cd',
            boot_image='/path/to/file.iso',
            write_protected=True)
        set_boot_mode.assert_called_once_with('xxxx-yyyy-zzzz', 'UEFI')
        set_http_boot_uri.assert_called_once_with('http://test.url/boot.iso')

    @patch_resource('systems')
    def test_system_reset_action_ok(self, systems_mock):
        set_power_state = systems_mock.return_value.set_power_state
        for reset_type in ('On', 'ForceOn', 'GracefulRestart', 'ForceRestart',
                           'Nmi'):
            set_power_state.reset_mock()
            data = {'ResetType': reset_type}
            response = self.app.post(
                '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/'
                'ComputerSystem.Reset',
                json=data)
            self.assertEqual(204, response.status_code)
            set_power_state.assert_called_once_with('xxxx-yyyy-zzzz',
                                                    reset_type)

    @patch_resource('systems')
    def test_system_reset_action_fail(self, systems_mock):
        self.app.application.config['SUSHY_EMULATOR_DISABLE_POWER_OFF'] = True
        print(self.app.application.config)

        for reset_type in ('ForceOff', 'GracefulShutdown'):
            data = {'ResetType': reset_type}
            response = self.app.post(
                '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/'
                'ComputerSystem.Reset',
                json=data)
            self.assertEqual(400, response.status_code)

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

    @patch_resource('indicators')
    @patch_resource('systems')
    def test_system_indicator_reduced_feature_set(self, systems_mock,
                                                  indicators_mock):
        self.set_feature_set("vmedia")
        systems_mock.return_value.uuid.return_value = self.uuid

        data = {'IndicatorLED': 'Off'}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(400, response.status_code)


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


@patch_resource('storage')
@patch_resource('indicators')
@patch_resource('chassis')
@patch_resource('managers')
@patch_resource('systems')
class ConditionalResourceAdvertisingTestCase(EmulatorTestCase):
    """Test that resources are only advertised when driver supports them"""

    def setUp(self):
        super(ConditionalResourceAdvertisingTestCase, self).setUp()
        self.set_feature_set("full")

    def test_bios_advertised_when_supported(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock,
            storage_mock):
        """Test BIOS is advertised when driver supports it"""
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.side_effect = error.NotSupportedError
        systems_mock.get_bios.return_value = {'attr1': 'value1'}
        systems_mock.get_processors.side_effect = error.NotSupportedError
        systems_mock.get_simple_storage_collection.side_effect = (
            error.NotSupportedError)
        systems_mock.get_total_memory.side_effect = error.NotSupportedError
        systems_mock.get_total_cpus.side_effect = error.NotSupportedError
        systems_mock.get_versions.side_effect = error.NotSupportedError
        managers_mock.return_value.get_managers_for_system.return_value = []
        chassis_mock.return_value.chassis = []
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertIn('Bios', response.json)
        self.assertEqual(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS',
            response.json['Bios']['@odata.id'])

    def test_bios_not_advertised_when_not_supported(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock,
            storage_mock):
        """Test BIOS is NOT advertised when driver doesn't support it"""
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.side_effect = error.NotSupportedError
        systems_mock.get_bios.side_effect = error.NotSupportedError
        systems_mock.get_processors.side_effect = error.NotSupportedError
        systems_mock.get_simple_storage_collection.side_effect = (
            error.NotSupportedError)
        systems_mock.get_total_memory.side_effect = error.NotSupportedError
        systems_mock.get_total_cpus.side_effect = error.NotSupportedError
        systems_mock.get_versions.side_effect = error.NotSupportedError
        managers_mock.return_value.get_managers_for_system.return_value = []
        chassis_mock.return_value.chassis = []
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertNotIn('Bios', response.json)

    def test_processors_advertised_when_supported(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock,
            storage_mock):
        """Test Processors is advertised when driver supports it"""
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.side_effect = error.NotSupportedError
        systems_mock.get_processors.return_value = [{'id': 'CPU'}]
        systems_mock.get_bios.side_effect = error.NotSupportedError
        systems_mock.get_simple_storage_collection.side_effect = (
            error.NotSupportedError)
        systems_mock.get_total_memory.side_effect = error.NotSupportedError
        systems_mock.get_total_cpus.side_effect = error.NotSupportedError
        systems_mock.get_versions.side_effect = error.NotSupportedError
        managers_mock.return_value.get_managers_for_system.return_value = []
        chassis_mock.return_value.chassis = []
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertIn('Processors', response.json)
        self.assertEqual(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Processors',
            response.json['Processors']['@odata.id'])

    def test_processors_not_advertised_when_not_supported(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock,
            storage_mock):
        """Test Processors is NOT advertised when driver doesn't support it"""
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.side_effect = error.NotSupportedError
        systems_mock.get_processors.side_effect = error.NotSupportedError
        systems_mock.get_bios.side_effect = error.NotSupportedError
        systems_mock.get_simple_storage_collection.side_effect = (
            error.NotSupportedError)
        systems_mock.get_total_memory.side_effect = error.NotSupportedError
        systems_mock.get_total_cpus.side_effect = error.NotSupportedError
        systems_mock.get_versions.side_effect = error.NotSupportedError
        managers_mock.return_value.get_managers_for_system.return_value = []
        chassis_mock.return_value.chassis = []
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertNotIn('Processors', response.json)

    def test_simple_storage_advertised_when_supported(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock,
            storage_mock):
        """Test SimpleStorage is advertised when driver supports it"""
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.side_effect = error.NotSupportedError
        systems_mock.get_simple_storage_collection.return_value = (
            {'virtio': {}})
        systems_mock.get_bios.side_effect = error.NotSupportedError
        systems_mock.get_processors.side_effect = error.NotSupportedError
        systems_mock.get_total_memory.side_effect = error.NotSupportedError
        systems_mock.get_total_cpus.side_effect = error.NotSupportedError
        systems_mock.get_versions.side_effect = error.NotSupportedError
        managers_mock.return_value.get_managers_for_system.return_value = []
        chassis_mock.return_value.chassis = []
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertIn('SimpleStorage', response.json)
        self.assertEqual(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/SimpleStorage',
            response.json['SimpleStorage']['@odata.id'])

    def test_simple_storage_not_advertised_when_not_supported(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock,
            storage_mock):
        """Test SimpleStorage NOT advertised when driver doesn't support"""
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.side_effect = error.NotSupportedError
        systems_mock.get_simple_storage_collection.side_effect = (
            error.NotSupportedError)
        systems_mock.get_bios.side_effect = error.NotSupportedError
        systems_mock.get_processors.side_effect = error.NotSupportedError
        systems_mock.get_total_memory.side_effect = error.NotSupportedError
        systems_mock.get_total_cpus.side_effect = error.NotSupportedError
        systems_mock.get_versions.side_effect = error.NotSupportedError
        managers_mock.return_value.get_managers_for_system.return_value = []
        chassis_mock.return_value.chassis = []
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertNotIn('SimpleStorage', response.json)

    def test_storage_advertised_when_supported(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock,
            storage_mock):
        """Test Storage advertised when driver supports it"""
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.side_effect = error.NotSupportedError
        systems_mock.get_simple_storage_collection.side_effect = (
            error.NotSupportedError)
        systems_mock.get_bios.side_effect = error.NotSupportedError
        systems_mock.get_processors.side_effect = error.NotSupportedError
        systems_mock.get_total_memory.side_effect = error.NotSupportedError
        systems_mock.get_total_cpus.side_effect = error.NotSupportedError
        systems_mock.get_versions.side_effect = error.NotSupportedError
        managers_mock.return_value.get_managers_for_system.return_value = []
        chassis_mock.return_value.chassis = []
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'
        storage_mock.return_value.get_storage_col.return_value = ["demo"]

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Storage',
            response.json['Storage']['@odata.id'])

    def test_storage_not_advertised_when_not_supported(
            self, systems_mock, managers_mock, chassis_mock, indicators_mock,
            storage_mock):
        """Test Storage NOT advertised when driver doesn't support"""
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.side_effect = error.NotSupportedError
        systems_mock.get_simple_storage_collection.side_effect = (
            error.NotSupportedError)
        systems_mock.get_bios.side_effect = error.NotSupportedError
        systems_mock.get_processors.side_effect = error.NotSupportedError
        systems_mock.get_total_memory.side_effect = error.NotSupportedError
        systems_mock.get_total_cpus.side_effect = error.NotSupportedError
        systems_mock.get_versions.side_effect = error.NotSupportedError
        managers_mock.return_value.get_managers_for_system.return_value = []
        chassis_mock.return_value.chassis = []
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'
        storage_mock.return_value.get_storage_col.side_effect = \
            error.NotSupportedError

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(200, response.status_code)
        self.assertNotIn('Storage', response.json)


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


@patch_resource('systems')
class SecureBootTestCase(EmulatorTestCase):

    def test_secure_boot_get(self, systems_mock):
        systems_mock = systems_mock.return_value
        systems_mock.get_secure_boot.return_value = True
        response = self.app.get('redfish/v1/Systems/%s/SecureBoot' % self.uuid)

        self.assertEqual(200, response.status_code)
        self.assertEqual('UEFI Secure Boot',
                         response.json['Name'])
        self.assertTrue(response.json['SecureBootEnable'])

        systems_mock.get_secure_boot.return_value = False
        response = self.app.get('redfish/v1/Systems/%s/SecureBoot' % self.uuid)
        self.assertFalse(response.json['SecureBootEnable'])

    def test_secure_boot_patch_on(self, systems_mock):
        systems_mock = systems_mock.return_value
        data = {'SecureBootEnable': True}
        response = self.app.patch('redfish/v1/Systems/%s/SecureBoot'
                                  % self.uuid, json=data)
        self.assertEqual(204, response.status_code)
        systems_mock.set_secure_boot.assert_called_once_with(self.uuid, True)

    def test_secure_boot_patch_off(self, systems_mock):
        systems_mock = systems_mock.return_value
        data = {'SecureBootEnable': False}
        response = self.app.patch('redfish/v1/Systems/%s/SecureBoot'
                                  % self.uuid, json=data)
        self.assertEqual(204, response.status_code)
        systems_mock.set_secure_boot.assert_called_once_with(self.uuid, False)


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
        self.assertIn('/redfish/v1/Systems/vmc-node/'
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


class RegistryTestCase(EmulatorTestCase):

    def test_registry_file_collection(self):
        response = self.app.get('/redfish/v1/Registries')
        self.assertEqual(200, response.status_code)
        self.assertEqual('/redfish/v1/Registries', response.json['@odata.id'])
        self.assertEqual(
            {'@odata.id': '/redfish/v1/Registries/Messages'},
            response.json['Members'][0])
        self.assertEqual(
            {'@odata.id':
                '/redfish/v1/Registries/BiosAttributeRegistry.v1_0_0'},
            response.json['Members'][1])

    def test_bios_attribute_registry_file(self):
        response = self.app.get(
            '/redfish/v1/Registries/BiosAttributeRegistry.v1_0_0')
        self.assertEqual(200, response.status_code)
        self.assertEqual('/redfish/v1/Registries/BiosAttributeRegistry.v1_0_0',
                         response.json['@odata.id'])
        self.assertEqual(
            {'Language': 'en',
             'Uri': '/redfish/v1/Systems/Bios/BiosRegistry'},
            response.json['Location'][0])

    def test_message_registry_file(self):
        response = self.app.get(
            '/redfish/v1/Registries/Messages')
        self.assertEqual(200, response.status_code)
        self.assertEqual('/redfish/v1/Registries/Messages',
                         response.json['@odata.id'])
        self.assertEqual({'Language': 'En',
                          'Uri': '/redfish/v1/Registries/Messages/Registry'},
                         response.json['Location'][0])

    def test_bios_registry(self):
        response = self.app.get(
            '/redfish/v1/Systems/Bios/BiosRegistry')
        self.assertEqual(200, response.status_code)
        self.assertEqual('/redfish/v1/Systems/Bios/BiosRegistry',
                         response.json['@odata.id'])
        self.assertEqual('BIOS Attribute Registry',
                         response.json['Name'])
        self.assertEqual('BiosAttributeRegistryP89.v1_0_0',
                         response.json['Id'])
        entries = response.json['RegistryEntries']
        self.assertEqual(len(entries['Attributes']), 10)
        self.assertEqual({'AttributeName': 'ProcTurboMode',
                          'CurrentValue': None,
                          'DisplayName': 'Turbo Boost',
                          'HelpText': 'Governs the Turbo Boost Technology. '
                          'This feature allows the processor cores to be '
                          'automatically clocked up in frequency beyond the '
                          'advertised processor speed.',
                          'Hidden': False,
                          'Immutable': False,
                          'ReadOnly': False,
                          'Type': 'Enumeration',
                          'Value': [{'ValueDisplayName': 'Enabled',
                                     'ValueName': 'Enabled'},
                                    {'ValueDisplayName': 'Disabled',
                                     'ValueName': 'Disabled'}],
                          'WarningText': None,
                          'WriteOnly': False},
                         entries['Attributes'][0])

    def test_message_registry(self):
        response = self.app.get('/redfish/v1/Registries/Messages/Registry')
        self.assertEqual(200, response.status_code)
        self.assertEqual('/redfish/v1/Registries/Messages/Registry',
                         response.json['@odata.id'])
        self.assertEqual('Message Registry', response.json['Name'])
        self.assertEqual('1.1.1', response.json['Id'])
        messages = response.json['Messages']
        self.assertEqual({"Description": "The command was successful.",
                          "Message": "The command was successful",
                          "Severity": "Informational",
                          "NumberOfArgs": 0,
                          "Resolution": "No response action is required."},
                         messages['BIOS001'])


class TaskServiceTestCase(EmulatorTestCase):

    def test_task_service(self):
        response = self.app.get('/redfish/v1/TaskService')
        self.assertEqual(200, response.status_code)
        self.assertEqual('/redfish/v1/TaskService',
                         response.json['@odata.id'])
        self.assertEqual('Tasks Service', response.json['Name'])
        self.assertEqual(True, response.json['ServiceEnabled'])

    def test_task_service_task(self):
        response = self.app.get('/redfish/v1/TaskService/Tasks/42')
        self.assertEqual(200, response.status_code)
        self.assertEqual('/redfish/v1/TaskService/Tasks/42',
                         response.json['@odata.id'])
        self.assertEqual('Task 42', response.json['Name'])
        self.assertEqual('Completed', response.json['TaskState'])


class ZombieCleanupTestCase(base.BaseTestCase):
    """Test case for zombie process cleanup functionality"""

    def setUp(self):
        super().setUp()
        # Store original signal handler to restore later
        self.original_sigchld_handler = signal.signal(
            signal.SIGCHLD, signal.SIG_DFL)

    def tearDown(self):
        # Restore original signal handler
        signal.signal(signal.SIGCHLD, self.original_sigchld_handler)
        super().tearDown()

    @mock.patch('os.waitpid')
    def test_cleanup_zombies_single_child(self, mock_waitpid):
        """Test that cleanup_zombies reaps a single zombie child"""
        # Mock waitpid to return a single child that has exited
        # First call returns child, second returns no more children
        mock_waitpid.side_effect = [(12345, 0), (0, 0)]

        with mock.patch.object(main.app, 'logger') as mock_logger:
            main.cleanup_zombies(signal.SIGCHLD, None)

        # Verify waitpid was called with correct parameters
        expected_calls = [
            mock.call(-1, os.WNOHANG),
            mock.call(-1, os.WNOHANG)
        ]
        mock_waitpid.assert_has_calls(expected_calls)

        # Verify the logging statement was called with correct message
        # Note: In real usage, logging might fail due to reentrancy
        mock_logger.debug.assert_called_once_with(
            "Reaped zombie process %d with status %d", 12345, 0)

    @mock.patch('os.waitpid')
    def test_cleanup_zombies_multiple_children(self, mock_waitpid):
        """Test that cleanup_zombies reaps multiple zombie children"""
        # Mock waitpid to return multiple children
        mock_waitpid.side_effect = [
            (12345, 0),    # First child
            (12346, 256),  # Second child (exit code 1)
            (0, 0)         # No more children
        ]

        with mock.patch.object(main.app, 'logger') as mock_logger:
            main.cleanup_zombies(signal.SIGCHLD, None)

        # Verify waitpid was called three times
        self.assertEqual(mock_waitpid.call_count, 3)

        # Verify both logging statements were called
        expected_calls = [
            mock.call("Reaped zombie process %d with status %d", 12345, 0),
            mock.call("Reaped zombie process %d with status %d", 12346, 256)
        ]
        mock_logger.debug.assert_has_calls(expected_calls)

    @mock.patch('os.waitpid')
    def test_cleanup_zombies_no_children(self, mock_waitpid):
        """Test that cleanup_zombies handles no zombie children gracefully"""
        # Mock waitpid to return no children
        mock_waitpid.return_value = (0, 0)

        with mock.patch.object(main.app, 'logger') as mock_logger:
            main.cleanup_zombies(signal.SIGCHLD, None)

        # Verify waitpid was called once
        mock_waitpid.assert_called_once_with(-1, os.WNOHANG)

        # Verify no logging statements were made
        mock_logger.debug.assert_not_called()

    @mock.patch('os.waitpid')
    def test_cleanup_zombies_oserror_handling(self, mock_waitpid):
        """Test that cleanup_zombies handles OSError gracefully"""
        # Mock waitpid to raise OSError (no more children)
        mock_waitpid.side_effect = OSError("No child processes")

        with mock.patch.object(main.app, 'logger') as mock_logger:
            main.cleanup_zombies(signal.SIGCHLD, None)

        # Verify waitpid was called once
        mock_waitpid.assert_called_once_with(-1, os.WNOHANG)

        # Verify no logging statements were made
        mock_logger.debug.assert_not_called()

    @mock.patch('signal.signal')
    def test_signal_handler_installation(self, mock_signal):
        """Test that the SIGCHLD signal handler is properly installed"""
        # Create a mock args object with all necessary attributes
        mock_args = mock.Mock()
        mock_args.ssl_certificate = None
        mock_args.ssl_key = None

        # Mock the signal.signal call to verify it's called correctly
        with mock.patch('sushy_tools.emulator.main.parse_args') as mock_parse:
            mock_parse.return_value = mock_args

            # Mock app configuration to avoid actual Flask app setup
            with mock.patch('sushy_tools.emulator.main.app') as mock_app:
                mock_app.configure = mock.Mock()
                mock_app.config = {}
                mock_app.run = mock.Mock()

                # Call main function
                main.main()

        # Verify signal.signal was called with SIGCHLD and cleanup function
        mock_signal.assert_called_with(signal.SIGCHLD, main.cleanup_zombies)

    @mock.patch('os.waitpid')
    def test_cleanup_zombies_with_different_exit_statuses(self, mock_waitpid):
        """Test that cleanup_zombies handles different exit statuses"""
        # Mock waitpid to return children with different exit statuses
        mock_waitpid.side_effect = [
            (12345, 0),      # Normal exit
            (12346, 256),    # Exit code 1 (256 = 1 << 8)
            (12347, 512),    # Exit code 2 (512 = 2 << 8)
            (0, 0)           # No more children
        ]

        with mock.patch.object(main.app, 'logger') as mock_logger:
            main.cleanup_zombies(signal.SIGCHLD, None)

        # Verify all three children were reaped
        expected_calls = [
            mock.call("Reaped zombie process %d with status %d", 12345, 0),
            mock.call("Reaped zombie process %d with status %d", 12346, 256),
            mock.call("Reaped zombie process %d with status %d", 12347, 512)
        ]
        mock_logger.debug.assert_has_calls(expected_calls)

    @mock.patch('os.waitpid')
    def test_cleanup_zombies_logging_failure_handled(self, mock_waitpid):
        """Test that cleanup_zombies handles logging failures gracefully"""
        # Mock waitpid to return a child
        mock_waitpid.side_effect = [(12345, 0), (0, 0)]

        with mock.patch.object(main.app, 'logger') as mock_logger:
            # Make logging raise an exception (simulating reentrancy issue)
            mock_logger.debug.side_effect = RuntimeError("Logging reentrancy")

            # This should not raise an exception
            main.cleanup_zombies(signal.SIGCHLD, None)

        # Verify waitpid was still called correctly
        expected_calls = [
            mock.call(-1, os.WNOHANG),
            mock.call(-1, os.WNOHANG)
        ]
        mock_waitpid.assert_has_calls(expected_calls)

        # Verify logging was attempted
        mock_logger.debug.assert_called_once_with(
            "Reaped zombie process %d with status %d", 12345, 0)
