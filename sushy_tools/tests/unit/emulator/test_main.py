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

from oslotest import base
from six.moves import mock

from sushy_tools.emulator import main


@mock.patch('sushy_tools.emulator.main.driver', autospec=True)
class EmulatorTestCase(base.BaseTestCase):

    def setUp(self):
        main.driver = None
        self.app = main.app.test_client()

        super(EmulatorTestCase, self).setUp()

    def test_bios(self, driver_mock):
        driver_mock.get_bios.return_value = {"attribute 1": "value 1",
                                             "attribute 2": "value 2"}
        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS')

        self.assertEqual('200 OK', response.status)
        self.assertEqual('BIOS', response.json['Id'])
        self.assertEqual({"attribute 1": "value 1",
                          "attribute 2": "value 2"},
                         response.json['Attributes'])

    def test_bios_settings(self, driver_mock):
        driver_mock.get_bios.return_value = {"attribute 1": "value 1",
                                             "attribute 2": "value 2"}
        response = self.app.get(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS/Settings')

        self.assertEqual('200 OK', response.status)
        self.assertEqual('Settings', response.json['Id'])
        self.assertEqual({"attribute 1": "value 1",
                          "attribute 2": "value 2"},
                         response.json['Attributes'])

    def test_bios_settings_patch(self, driver_mock):
        self.app.driver = driver_mock
        response = self.app.patch(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/BIOS/Settings',
            data=json.dumps({'Attributes': {'key': 'value'}}),
            content_type='application/json')

        self.assertEqual('204 NO CONTENT', response.status)
        driver_mock.set_bios.assert_called_once_with('xxxx-yyyy-zzzz',
                                                     {'key': 'value'})

    def test_reset_bios(self, driver_mock):
        self.app.driver = driver_mock
        response = self.app.post('/redfish/v1/Systems/xxxx-yyyy-zzzz/'
                                 'BIOS/Actions/Bios.ResetBios')

        self.assertEqual('204 NO CONTENT', response.status)
        driver_mock.reset_bios.assert_called_once_with('xxxx-yyyy-zzzz')
