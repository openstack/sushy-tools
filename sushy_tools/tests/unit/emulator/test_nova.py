# Copyright 2018 Red Hat, Inc.
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

import os

from oslotest import base
from six.moves import mock

from sushy_tools.emulator import main


@mock.patch.object(os, 'environ', dict(OS_CLOUD='fake-cloud', **os.environ))
@mock.patch.object(main, 'driver', None)  # This enables Nova driver
class EmulatorTestCase(base.BaseTestCase):

    def setUp(self):
        self.app = main.app.test_client()
        super(EmulatorTestCase, self).setUp()

    @mock.patch('openstack.connect', autospec=True)
    def test_root_resource(self, nova_mock):
        response = self.app.get('/redfish/v1/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json)

    @mock.patch('openstack.connect', autospec=True)
    def test_collection_resource(self, nova_mock):
        server0 = mock.Mock(id='host0')
        server1 = mock.Mock(id='host1')
        nova_mock.return_value.list_servers.return_value = [server0, server1]

        response = self.app.get('/redfish/v1/Systems')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['Members'][0],
                         {'@odata.id': '/redfish/v1/Systems/host0'})
        self.assertEqual(response.json['Members'][1],
                         {'@odata.id': '/redfish/v1/Systems/host1'})

    @mock.patch('openstack.connect', autospec=True)
    def test_system_resource_get(self, nova_mock):
        server = mock.Mock(id='zzzz-yyyy-xxxx',
                           power_state=1,
                           image={'id': 'xxxx-zzzz-yyyy'})
        nova_mock.return_value.get_server.return_value = server

        flavor = mock.Mock(ram=1024, vcpus=2)
        nova_mock.return_value.get_flavor.return_value = flavor

        image = mock.Mock(hw_firmware_type='bios')
        nova_mock.return_value.glance.find_image.return_value = image

        response = self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['Id'], 'xxxx-yyyy-zzzz')
        self.assertEqual(response.json['UUID'], 'zzzz-yyyy-xxxx')
        self.assertEqual(response.json['PowerState'], 'On')
        self.assertEqual(
            response.json['MemorySummary']['TotalSystemMemoryGiB'], 1)
        self.assertEqual(response.json['ProcessorSummary']['Count'], 2)
        self.assertEqual(
            response.json['Boot']['BootSourceOverrideTarget'], 'Pxe')
        self.assertEqual(
            response.json['Boot']['BootSourceOverrideMode'], 'Legacy')

    @mock.patch('openstack.connect', autospec=True)
    def test_system_resource_patch(self, nova_mock):
        data = {'Boot': {'BootSourceOverrideTarget': 'Cd'}}
        response = self.app.patch('/redfish/v1/Systems/xxxx-yyyy-zzzz',
                                  json=data)
        self.assertEqual(response.status_code, 204)
        server = nova_mock.return_value
        server.compute.set_server_metadata.called_once_with(
            {'libvirt:pxe-first': ''})

    @mock.patch('openstack.connect', autospec=True)
    def test_system_reset_action_on(self, nova_mock):
        server = mock.Mock(power_state=1)
        nova_mock.return_value.get_server.return_value = server

        data = {'ResetType': 'On'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(response.status_code, 204)
        server.compute.start_server.called_once()

    @mock.patch('openstack.connect', autospec=True)
    def test_system_reset_action_forceon(self, nova_mock):
        server = mock.Mock(power_state=1)
        nova_mock.return_value.get_server.return_value = server

        data = {'ResetType': 'ForceOn'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(response.status_code, 204)
        server.compute.start_server.called_once()

    @mock.patch('openstack.connect', autospec=True)
    def test_system_reset_action_forceoff(self, nova_mock):
        server = mock.Mock(power_state=1)
        nova_mock.return_value.get_server.return_value = server

        data = {'ResetType': 'ForceOff'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(response.status_code, 204)
        server.compute.stop_server.called_once()

    @mock.patch('openstack.connect', autospec=True)
    def test_system_reset_action_shutdown(self, nova_mock):
        server = mock.Mock(power_state=1)
        nova_mock.return_value.get_server.return_value = server

        data = {'ResetType': 'GracefulShutdown'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(response.status_code, 204)
        server.compute.stop_server.called_once()

    @mock.patch('openstack.connect', autospec=True)
    def test_system_reset_action_restart(self, nova_mock):
        server = mock.Mock(power_state=1)
        nova_mock.return_value.get_server.return_value = server

        data = {'ResetType': 'GracefulRestart'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(response.status_code, 204)
        server.compute.reboot_server.called_once()

    @mock.patch('openstack.connect', autospec=True)
    def test_system_reset_action_forcerestart(self, nova_mock):
        server = mock.Mock(power_state=1)
        nova_mock.return_value.get_server.return_value = server

        data = {'ResetType': 'ForceRestart'}
        response = self.app.post(
            '/redfish/v1/Systems/xxxx-yyyy-zzzz/Actions/ComputerSystem.Reset',
            json=data)
        self.assertEqual(response.status_code, 204)
        server.compute.reboot_server.called_once()
