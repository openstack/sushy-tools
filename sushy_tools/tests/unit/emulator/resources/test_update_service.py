# Copyright 2019 Red Hat, Inc.
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

from sushy_tools.tests.unit.emulator import test_main


class UpdateServiceTestCase(test_main.EmulatorTestCase):

    def test_update_service_get(self):
        actions = {
            "#UpdateService.SimpleUpdate": {
                "TransferProtocol@Redfish.AllowableValues": [
                    "HTTP",
                    "HTTPS"
                ],
                "target": "/redfish/v1/UpdateService/Actions/"
                          "UpdateService.SimpleUpdate"
            }
        }

        firmwareinventory = {
            "@odata.id": "/redfish/v1/UpdateService/FirmwareInventory"
        }

        softwareinventory = {
            "@odata.id": "/redfish/v1/UpdateService/SoftwareInventory"
        }

        resp = self.app.get('/redfish/v1/UpdateService')
        self.assertEqual(200, resp.status_code)

        self.assertEqual('/redfish/v1/$metadata#UpdateService.UpdateService',
                         resp.json['@odata.context'])
        self.assertEqual('/redfish/v1/UpdateService', resp.json['@odata.id'])
        self.assertEqual('#UpdateService.v1_11_0.UpdateService',
                         resp.json['@odata.type'])
        self.assertEqual(actions, resp.json['Actions'])
        self.assertEqual('Represents the properties for the Update Service',
                         resp.json['Description'])
        self.assertEqual(firmwareinventory, resp.json['FirmwareInventory'])
        self.assertEqual('/redfish/v1/UpdateService/FirmwareInventory',
                         resp.json['HttpPushUri'])
        self.assertEqual('UpdateService', resp.json['Id'])
        self.assertIsNone(resp.json['MaxImageSizeBytes'])
        self.assertEqual('Update Service', resp.json['Name'])
        self.assertTrue(resp.json['ServiceEnabled'])
        self.assertEqual(softwareinventory, resp.json['SoftwareInventory'])

    @test_main.patch_resource('storage')
    @test_main.patch_resource('indicators')
    @test_main.patch_resource('chassis')
    @test_main.patch_resource('managers')
    @test_main.patch_resource('systems')
    def test_update_service_simpleupdate(self, systems_mock, managers_mock,
                                         chassis_mock, indicators_mock,
                                         storage_mock):
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        systems_mock.get_power_state.return_value = 'On'
        systems_mock.get_total_memory.return_value = 1
        systems_mock.get_total_cpus.return_value = 2
        systems_mock.get_boot_device.return_value = 'Cd'
        systems_mock.get_boot_mode.return_value = 'Legacy'
        systems_mock.get_versions().get.return_value = '1.0.0'
        get_versions = systems_mock.get_versions
        managers_mock.return_value.get_managers_for_system.return_value = [
            'aaaa-bbbb-cccc']
        chassis_mock.return_value.chassis = ['chassis0']
        indicators_mock.return_value.get_indicator_state.return_value = 'Off'

        resp = self.app.get('/redfish/v1/Systems/zzzz-yyyy-xxxx')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('zzzz-yyyy-xxxx', resp.json['Id'])
        self.assertEqual('1.0.0', resp.json['BiosVersion'])
        get_versions.assert_called()

        args = {
            'ImageURI': 'http://10.6.48.48:8080/ilo5278.bin',
            'TransferProtocol': 'HTTP',
            'Targets': ['/redfish/v1/Systems/'
                        'zzzz-yyyy-xxxx']
        }
        set_versions = systems_mock.set_versions
        response = self.app.post('/redfish/v1/UpdateService/Actions/'
                                 'UpdateService.SimpleUpdate', json=args)
        self.assertEqual(204, response.status_code)
        set_versions.assert_called_once_with('zzzz-yyyy-xxxx',
                                             {'BiosVersion': '1.1.0'})

    def test_update_service_invalid_params(self):
        args = {
            'NonexistentURI': 'asdf://nowhere.com',
        }

        response = self.app.post('/redfish/v1/UpdateService/Actions/'
                                 'UpdateService.SimpleUpdate', json=args)
        self.assertEqual('Base.1.0.GeneralError',
                         response.json['error']['code'])
        self.assertEqual('Missing ImageURI and/or Targets.',
                         response.json['error']['message'])

    @test_main.patch_resource('systems')
    def test_update_service_simpleupdate_manager(self, systems_mock):
        systems_mock = systems_mock.return_value
        systems_mock.uuid.return_value = 'zzzz-yyyy-xxxx'
        args = {
            'ImageURI': 'http://10.6.48.48:8080/ilo5278.bin',
            'TransferProtocol': 'HTTP',
            'Targets': ['/redfish/v1/Managers/'
                        'zzzz-yyyy-xxxx']
        }
        set_versions = systems_mock.set_versions
        response = self.app.post('/redfish/v1/UpdateService/Actions/'
                                 'UpdateService.SimpleUpdate', json=args)
        self.assertEqual(400, response.status_code)
        self.assertEqual('Manager is not currently a supported Target.',
                         response.json['error']['message'])
        set_versions.assert_not_called()
