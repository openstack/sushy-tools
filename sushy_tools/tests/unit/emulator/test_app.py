#!/usr/bin/env python
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

import json

from oslotest import base
from six.moves import mock

from sushy_tools.emulator import main


class EmulatorTestCase(base.BaseTestCase):

    def setUp(self):
        self.app = main.app.test_client()

        super(EmulatorTestCase, self).setUp()

    @mock.patch('flask.render_template', autospec=True)
    def test_root_resource(self, render_mock):
        self.app.get('/redfish/v1/')
        render_mock.assert_called_once_with('root.json')

    @mock.patch('libvirt.openReadOnly', autospec=True)
    @mock.patch('flask.render_template', autospec=True)
    def test_collection_resource(self, render_mock, libvirt_mock):
        conn_mock = libvirt_mock.return_value
        conn_mock.listDefinedDomains.return_value = ['host0', 'host1']

        self.app.get('/redfish/v1/Systems')
        render_mock.assert_called_once_with('system_collection.json',
                                            system_count=2,
                                            systems=['host0', 'host1'])

    @mock.patch('libvirt.openReadOnly', autospec=True)
    @mock.patch('flask.render_template', autospec=True)
    def test_system_resource_get(self, render_mock, libvirt_mock):
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

        self.app.get('/redfish/v1/Systems/xxxx-yyyy-zzzz')

        render_mock.assert_called_once_with(
            'system.json', identity='xxxx-yyyy-zzzz', uuid='zzzz-yyyy-xxxx',
            power_state='On', total_memory_gb=1, total_cpus=2,
            boot_source_target='Cd', boot_source_mode='Legacy')

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
