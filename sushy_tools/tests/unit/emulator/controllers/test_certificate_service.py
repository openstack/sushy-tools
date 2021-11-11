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

from sushy_tools.emulator.resources import vmedia
from sushy_tools import error
from sushy_tools.tests.unit.emulator import test_main


@test_main.patch_resource('vmedia')
@test_main.patch_resource('managers')
class CertificateServiceTestCase(test_main.EmulatorTestCase):

    def test_root(self, managers_mock, vmedia_mock):
        response = self.app.get('redfish/v1/CertificateService')

        self.assertEqual(200, response.status_code)
        self.assertIn('#CertificateService.ReplaceCertificate',
                      response.json['Actions'])

    def test_replace_ok(self, managers_mock, vmedia_mock):
        response = self.app.post(
            'redfish/v1/CertificateService/Actions/'
            'CertificateService.ReplaceCertificate',
            json={'CertificateString': 'abcd',
                  'CertificateType': 'PEM',
                  'CertificateUri': ('https://host/redfish/v1/Managers/1234'
                                     '/VirtualMedia/CD/Certificates/1')})

        self.assertEqual(204, response.status_code)
        managers_mock.return_value.get_manager.assert_called_once_with('1234')
        vmedia_mock.return_value.replace_certificate.assert_called_once_with(
            '1234', 'CD', '1', 'abcd', 'PEM')

    def test_replace_manager_not_found(self, managers_mock, vmedia_mock):
        managers_mock.return_value.get_manager.side_effect = error.NotFound

        response = self.app.post(
            'redfish/v1/CertificateService/Actions/'
            'CertificateService.ReplaceCertificate',
            json={'CertificateString': 'abcd',
                  'CertificateType': 'PEM',
                  'CertificateUri': ('https://host/redfish/v1/Managers/1234'
                                     '/VirtualMedia/CD/Certificates/1')})

        self.assertEqual(404, response.status_code)
        managers_mock.return_value.get_manager.assert_called_once_with('1234')
        vmedia_mock.return_value.replace_certificate.assert_not_called()

    def test_replace_wrong_uri(self, managers_mock, vmedia_mock):
        response = self.app.post(
            'redfish/v1/CertificateService/Actions/'
            'CertificateService.ReplaceCertificate',
            json={'CertificateString': 'abcd',
                  'CertificateType': 'PEM',
                  'CertificateUri': ('https://host/redfish/v1/Managers/1234'
                                     '/NetworkProtocol/HTTPS/Certificates/1')})

        self.assertEqual(404, response.status_code)
        managers_mock.return_value.get_manager.assert_not_called()
        vmedia_mock.return_value.replace_certificate.assert_not_called()

    def test_replace_missing_string(self, managers_mock, vmedia_mock):
        response = self.app.post(
            'redfish/v1/CertificateService/Actions/'
            'CertificateService.ReplaceCertificate',
            json={'CertificateType': 'PEM',
                  'CertificateUri': ('https://host/redfish/v1/Managers/1234'
                                     '/VirtualMedia/CD/Certificates/1')})

        self.assertEqual(400, response.status_code)
        managers_mock.return_value.get_manager.assert_not_called()
        vmedia_mock.return_value.replace_certificate.assert_not_called()

    def test_replace_wrong_type(self, managers_mock, vmedia_mock):
        response = self.app.post(
            'redfish/v1/CertificateService/Actions/'
            'CertificateService.ReplaceCertificate',
            json={'CertificateString': 'abcd',
                  'CertificateType': 'non-PEM',
                  'CertificateUri': ('https://host/redfish/v1/Managers/1234'
                                     '/VirtualMedia/CD/Certificates/1')})

        self.assertEqual(400, response.status_code)
        managers_mock.return_value.get_manager.assert_not_called()
        vmedia_mock.return_value.replace_certificate.assert_not_called()

    def test_replace_missing_uri(self, managers_mock, vmedia_mock):
        response = self.app.post(
            'redfish/v1/CertificateService/Actions/'
            'CertificateService.ReplaceCertificate',
            json={'CertificateString': 'abcd',
                  'CertificateType': 'PEM'})

        self.assertEqual(400, response.status_code)
        managers_mock.return_value.get_manager.assert_not_called()
        vmedia_mock.return_value.replace_certificate.assert_not_called()

    def test_locations(self, managers_mock, vmedia_mock):
        managers_mock.return_value.managers = ["1", "2"]
        vmedia_mock.return_value.devices = ["CD", "DVD"]
        vmedia_mock.return_value.list_certificates.side_effect = [
            error.NotFound(),
            [vmedia.Certificate("cert1", "abcd", "PEM")],
            [vmedia.Certificate("cert2", "abcd", "PEM")],
            error.NotFound(),
        ]
        response = self.app.get(
            'redfish/v1/CertificateService/CertificateLocations')

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            ['/redfish/v1/Managers/1/VirtualMedia/DVD/Certificates/cert1',
             '/redfish/v1/Managers/2/VirtualMedia/CD/Certificates/cert2'],
            [item['@odata.id']
             for item in response.json['Links']['Certificates']])
