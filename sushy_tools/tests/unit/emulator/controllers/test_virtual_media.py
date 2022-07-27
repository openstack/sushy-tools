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
class VirtualMediaTestCase(test_main.EmulatorTestCase):

    def test_virtual_media_collection(self, managers_mock, vmedia_mock):
        managers_mock = managers_mock.return_value
        managers_mock.managers = [self.uuid]
        managers_mock.get_manager.return_value = {'UUID': self.uuid}
        vmedia_mock.return_value.devices = ['CD', 'Floppy']

        response = self.app.get(
            '/redfish/v1/Managers/%s/VirtualMedia' % self.uuid)

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
        vmedia_mock.get_device_image_info.return_value = vmedia.DeviceInfo(
            'image-of-a-fish', 'fishy.iso', True, True, '', '', False)

        response = self.app.get(
            '/redfish/v1/Managers/%s/VirtualMedia/CD' % self.uuid)

        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual('CD', response.json['Id'])
        self.assertEqual(['CD', 'DVD'], response.json['MediaTypes'])
        self.assertEqual('fishy.iso', response.json['Image'])
        self.assertEqual('image-of-a-fish', response.json['ImageName'])
        self.assertTrue(response.json['Inserted'])
        self.assertTrue(response.json['WriteProtected'])
        self.assertEqual('', response.json['UserName'])
        self.assertEqual('', response.json['Password'])
        self.assertFalse(response.json['VerifyCertificate'])
        self.assertEqual(
            '/redfish/v1/Managers/%s/VirtualMedia/CD/Certificates' % self.uuid,
            response.json['Certificates']['@odata.id'])

    def test_virtual_media_with_auth(self, managers_mock, vmedia_mock):
        vmedia_mock = vmedia_mock.return_value
        vmedia_mock.get_device_name.return_value = 'CD'
        vmedia_mock.get_device_media_types.return_value = [
            'CD', 'DVD']
        vmedia_mock.get_device_image_info.return_value = vmedia.DeviceInfo(
            'image-of-a-fish', 'fishy.iso', True, True, 'Admin', 'Secret',
            False)

        response = self.app.get(
            '/redfish/v1/Managers/%s/VirtualMedia/CD' % self.uuid)

        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual('CD', response.json['Id'])
        self.assertEqual(['CD', 'DVD'], response.json['MediaTypes'])
        self.assertEqual('fishy.iso', response.json['Image'])
        self.assertEqual('image-of-a-fish', response.json['ImageName'])
        self.assertTrue(response.json['Inserted'])
        self.assertTrue(response.json['WriteProtected'])
        self.assertEqual('Admin', response.json['UserName'])
        self.assertEqual('******', response.json['Password'])
        self.assertFalse(response.json['VerifyCertificate'])

    def test_virtual_media_not_found(self, managers_mock, vmedia_mock):
        vmedia_mock.return_value.get_device_name.side_effect = error.NotFound

        response = self.app.get(
            '/redfish/v1/Managers/%s/VirtualMedia/DVD-ROM' % self.uuid)

        self.assertEqual(404, response.status_code)

    def test_virtual_media_update(self, managers_mock, vmedia_mock):
        response = self.app.patch(
            '/redfish/v1/Managers/%s/VirtualMedia/CD' % self.uuid,
            json={'VerifyCertificate': True})

        self.assertEqual(204, response.status_code)
        vmedia_mock = vmedia_mock.return_value
        vmedia_mock.update_device_info.assert_called_once_with(
            self.uuid, 'CD', verify=True)

    def test_virtual_media_update_not_found(self, managers_mock, vmedia_mock):
        vmedia_mock = vmedia_mock.return_value
        vmedia_mock.update_device_info.side_effect = error.NotFound

        response = self.app.patch(
            '/redfish/v1/Managers/%s/VirtualMedia/DVD-ROM' % self.uuid,
            json={'VerifyCertificate': True})

        self.assertEqual(404, response.status_code)

    def test_virtual_media_update_invalid(self, managers_mock, vmedia_mock):
        response = self.app.patch(
            '/redfish/v1/Managers/%s/VirtualMedia/CD' % self.uuid,
            json={'VerifyCertificate': 'banana'})

        self.assertEqual(400, response.status_code)

    def test_virtual_media_update_empty(self, managers_mock, vmedia_mock):
        response = self.app.patch(
            '/redfish/v1/Managers/%s/VirtualMedia/CD' % self.uuid)

        self.assertEqual(400, response.status_code)

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

    def test_virtual_media_certificates(self, managers_mock, vmedia_mock):
        vmedia_mock.return_value.list_certificates.return_value = [
            vmedia.Certificate('1', 'PEM', 'abcd'),
            vmedia.Certificate('2', 'PEM', 'dcba'),
        ]
        response = self.app.get(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates')

        self.assertEqual(200, response.status_code, response.json)
        self.assertEqual(2, response.json['Members@odata.count'])
        for index, member in enumerate(response.json['Members']):
            self.assertTrue(member['@odata.id'].endswith(
                f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD'
                f'/Certificates/{index+1}'), member['@odata.id'])
        self.assertEqual(['PEM'],
                         response.json['@Redfish.SupportedCertificates'])

    def test_virtual_media_certificates_manager_not_found(self, managers_mock,
                                                          vmedia_mock):
        managers_mock.return_value.get_manager.side_effect = error.NotFound
        response = self.app.get(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates')

        self.assertEqual(404, response.status_code, response.json)

    def test_virtual_media_add_certificate(self, managers_mock, vmedia_mock):
        vmedia_mock.return_value.add_certificate.return_value = \
            vmedia.Certificate('9', 'abcd', 'PEM')

        response = self.app.post(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates',
            json={'CertificateString': 'abcd', 'CertificateType': 'PEM'})

        self.assertEqual(204, response.status_code, response.data)
        self.assertIn(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates/9',
            response.headers['Location'])

    def test_virtual_media_add_certificate_no_string(self, managers_mock,
                                                     vmedia_mock):
        response = self.app.post(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates',
            json={'CertificateType': 'PEM'})

        self.assertEqual(400, response.status_code, response.data)

    def test_virtual_media_add_certificate_bad_type(self, managers_mock,
                                                    vmedia_mock):
        response = self.app.post(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates',
            json={'CertificateString': 'abcd', 'CertificateType': 'non-PEM'})

        self.assertEqual(400, response.status_code, response.data)

    def test_virtual_media_get_certificate(self, managers_mock, vmedia_mock):
        vmedia_mock.return_value.list_certificates.return_value = [
            vmedia.Certificate('1', 'abcd', 'PEM'),
            vmedia.Certificate('2', 'dcba', 'PEM'),
        ]
        response = self.app.get(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates/2')

        self.assertEqual(200, response.status_code, response.json)
        self.assertIn('Id', response.json)
        self.assertEqual('2', response.json['Id'])
        self.assertEqual('dcba', response.json['CertificateString'])
        self.assertEqual('PEM', response.json['CertificateType'])

    def test_virtual_media_get_certificate_manager_not_found(self,
                                                             managers_mock,
                                                             vmedia_mock):
        managers_mock.return_value.get_manager.side_effect = error.NotFound
        response = self.app.get(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates/2')

        self.assertEqual(404, response.status_code, response.json)

    def test_virtual_media_delete_certificate(self, managers_mock,
                                              vmedia_mock):
        response = self.app.delete(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates/2')

        self.assertEqual(204, response.status_code, response.data)
        vmedia_mock.return_value.delete_certificate.assert_called_once_with(
            self.uuid, 'CD', '2')

    def test_virtual_media_delete_certificate_manager_not_found(self,
                                                                managers_mock,
                                                                vmedia_mock):
        managers_mock.return_value.get_manager.side_effect = error.NotFound
        response = self.app.delete(
            f'/redfish/v1/Managers/{self.uuid}/VirtualMedia/CD/Certificates/2')

        self.assertEqual(404, response.status_code, response.json)
        vmedia_mock.return_value.delete_certificate.assert_not_called()
