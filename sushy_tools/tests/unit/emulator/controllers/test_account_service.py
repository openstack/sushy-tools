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
import tempfile

from oslotest import base

from sushy_tools.emulator import auth_basic
from sushy_tools.emulator.controllers import account_service as acctctl
from sushy_tools.emulator import main
from sushy_tools import error
from sushy_tools.tests.unit.emulator import test_main


class AuthFileTestCase(test_main.EmulatorTestCase):
    """Tests against the global application with an auth file configured"""

    def setUp(self):
        super().setUp()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(test_main.TEST_PASSWD.decode('utf-8'))
            self.auth_file = f.name
        self.addCleanup(os.remove, self.auth_file)

        main.app.config['SUSHY_EMULATOR_AUTH_FILE'] = self.auth_file
        self.addCleanup(main.app.config.pop,
                        'SUSHY_EMULATOR_AUTH_FILE', None)
        # the accounts driver is memoized, make sure it is re-created
        main.app._cache = {}
        self.addCleanup(setattr, main.app, '_cache', {})


class AccountServiceTestCase(AuthFileTestCase):

    def setUp(self):
        super().setUp()
        main.app.config['SUSHY_EMULATOR_ACCOUNT_EDITING'] = True
        self.addCleanup(main.app.config.pop,
                        'SUSHY_EMULATOR_ACCOUNT_EDITING', None)

    def test_root_resource(self):
        response = self.app.get('/redfish/v1/')
        self.assertEqual(200, response.status_code)
        self.assertEqual('/redfish/v1/AccountService',
                         response.json['AccountService']['@odata.id'])

    def test_account_service_resource(self):
        response = self.app.get('/redfish/v1/AccountService')
        self.assertEqual(200, response.status_code)
        self.assertEqual('AccountService', response.json['Id'])
        self.assertTrue(response.json['ServiceEnabled'])
        self.assertEqual('/redfish/v1/AccountService/Accounts',
                         response.json['Accounts']['@odata.id'])

    def test_account_collection(self):
        response = self.app.get('/redfish/v1/AccountService/Accounts')
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json['Members@odata.count'])
        self.assertEqual(
            [{'@odata.id': '/redfish/v1/AccountService/Accounts/admin'}],
            response.json['Members'])

    def test_account_resource(self):
        response = self.app.get('/redfish/v1/AccountService/Accounts/admin')
        self.assertEqual(200, response.status_code)
        self.assertEqual('admin', response.json['Id'])
        self.assertEqual('admin', response.json['UserName'])
        self.assertEqual('Administrator', response.json['RoleId'])
        self.assertTrue(response.json['Enabled'])
        self.assertIsNone(response.json['Password'])

    def test_account_not_found(self):
        response = self.app.get('/redfish/v1/AccountService/Accounts/nosuch')
        self.assertEqual(404, response.status_code)

    def test_add_account(self):
        response = self.app.post(
            '/redfish/v1/AccountService/Accounts',
            json={'UserName': 'bob', 'Password': 'myPassword',
                  'RoleId': 'Operator'})
        self.assertEqual(201, response.status_code)
        self.assertEqual('/redfish/v1/AccountService/Accounts/bob',
                         response.headers['Location'])

        response = self.app.get('/redfish/v1/AccountService/Accounts')
        self.assertEqual(2, response.json['Members@odata.count'])

        response = self.app.get('/redfish/v1/AccountService/Accounts/bob')
        self.assertEqual(200, response.status_code)
        self.assertEqual('bob', response.json['UserName'])
        # password must be null per standard
        self.assertIsNone(response.json['Password'])

        # the new user can authenticate against the auth user file
        self.assertEqual(
            {'HTTP_X_USER': 'bob', 'HTTP_X_USER_NAME': 'bob'},
            auth_basic.authenticate(self.auth_file, 'bob', b'myPassword'))

    def test_add_account_duplicate(self):
        response = self.app.post(
            '/redfish/v1/AccountService/Accounts',
            json={'UserName': 'admin', 'Password': 'myPassword'})
        self.assertEqual(400, response.status_code)

    def test_add_account_missing_fields(self):
        response = self.app.post(
            '/redfish/v1/AccountService/Accounts',
            json={'UserName': 'bob'})
        self.assertEqual(400, response.status_code)

    def test_add_account_invalid_username(self):
        for username in ('', 'bo:b', 'bo/b', 'bo b', 'ünïcode', 'bo\nb'):
            response = self.app.post(
                '/redfish/v1/AccountService/Accounts',
                json={'UserName': username, 'Password': 'myPassword'})
            self.assertEqual(400, response.status_code, username)

    def test_delete_account(self):
        response = self.app.post(
            '/redfish/v1/AccountService/Accounts',
            json={'UserName': 'bob', 'Password': 'myPassword'})
        self.assertEqual(201, response.status_code)

        response = self.app.delete('/redfish/v1/AccountService/Accounts/bob')
        self.assertEqual(204, response.status_code)

        response = self.app.get('/redfish/v1/AccountService/Accounts')
        self.assertEqual(1, response.json['Members@odata.count'])

        # the user cannot authenticate anymore
        self.assertRaises(error.Unauthorized,
                          auth_basic.authenticate,
                          self.auth_file, 'bob', b'myPassword')

    def test_delete_builtin_account(self):
        response = self.app.delete(
            '/redfish/v1/AccountService/Accounts/admin')
        self.assertEqual(400, response.status_code)

    def test_delete_account_not_found(self):
        response = self.app.delete(
            '/redfish/v1/AccountService/Accounts/nosuch')
        self.assertEqual(404, response.status_code)

    def test_change_password(self):
        response = self.app.patch(
            '/redfish/v1/AccountService/Accounts/admin',
            json={'Password': 'newPassword'})
        self.assertEqual(204, response.status_code)

        self.assertEqual(
            {'HTTP_X_USER': 'admin', 'HTTP_X_USER_NAME': 'admin'},
            auth_basic.authenticate(self.auth_file, 'admin', b'newPassword'))
        self.assertRaises(error.Unauthorized,
                          auth_basic.authenticate,
                          self.auth_file, 'admin', b'password')

    def test_change_password_missing(self):
        response = self.app.patch(
            '/redfish/v1/AccountService/Accounts/admin', json={})
        self.assertEqual(400, response.status_code)

    def test_change_password_too_long(self):
        response = self.app.patch(
            '/redfish/v1/AccountService/Accounts/admin',
            json={'Password': 'x' * 73})
        self.assertEqual(400, response.status_code)

    def test_change_password_not_found(self):
        response = self.app.patch(
            '/redfish/v1/AccountService/Accounts/nosuch',
            json={'Password': 'newPassword'})
        self.assertEqual(404, response.status_code)


class ReadOnlyAccountServiceTestCase(AuthFileTestCase):
    """Account editing not enabled: read-only access"""

    def test_reads_allowed(self):
        response = self.app.get('/redfish/v1/AccountService')
        self.assertEqual(200, response.status_code)

        response = self.app.get('/redfish/v1/AccountService/Accounts')
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.json['Members@odata.count'])

        response = self.app.get('/redfish/v1/AccountService/Accounts/admin')
        self.assertEqual(200, response.status_code)
        self.assertEqual('admin', response.json['UserName'])

    def test_add_account_not_allowed(self):
        response = self.app.post(
            '/redfish/v1/AccountService/Accounts',
            json={'UserName': 'bob', 'Password': 'myPassword'})
        self.assertEqual(405, response.status_code)

        # even with a malformed payload, not a validation error
        response = self.app.post(
            '/redfish/v1/AccountService/Accounts',
            json={'UserName': 'bob'})
        self.assertEqual(405, response.status_code)

        # the account was not created
        self.assertRaises(error.Unauthorized,
                          auth_basic.authenticate,
                          self.auth_file, 'bob', b'myPassword')

    def test_change_password_not_allowed(self):
        response = self.app.patch(
            '/redfish/v1/AccountService/Accounts/admin',
            json={'Password': 'newPassword'})
        self.assertEqual(405, response.status_code)

        # the password was not changed
        self.assertEqual(
            {'HTTP_X_USER': 'admin', 'HTTP_X_USER_NAME': 'admin'},
            auth_basic.authenticate(self.auth_file, 'admin', b'password'))

    def test_delete_account_not_allowed(self):
        response = self.app.delete(
            '/redfish/v1/AccountService/Accounts/admin')
        self.assertEqual(405, response.status_code)

        response = self.app.get('/redfish/v1/AccountService/Accounts')
        self.assertEqual(1, response.json['Members@odata.count'])


class AccountServiceNotConfiguredTestCase(test_main.EmulatorTestCase):

    def test_account_service_not_available(self):
        response = self.app.get('/redfish/v1/AccountService')
        self.assertEqual(404, response.status_code)

    def test_accounts_not_available(self):
        for method in ('get', 'post'):
            response = getattr(self.app, method)(
                '/redfish/v1/AccountService/Accounts',
                json={'UserName': 'bob', 'Password': 'myPassword'})
            self.assertEqual(404, response.status_code)

        response = self.app.patch(
            '/redfish/v1/AccountService/Accounts/bob',
            json={'Password': 'myPassword'})
        self.assertEqual(404, response.status_code)

        response = self.app.delete(
            '/redfish/v1/AccountService/Accounts/bob')
        self.assertEqual(404, response.status_code)

    def test_root_resource_no_account_service(self):
        response = self.app.get('/redfish/v1/')
        self.assertEqual(200, response.status_code)
        self.assertNotIn('AccountService', response.json)


class AuthenticatedAccountServiceTestCase(base.BaseTestCase):
    """End-to-end tests through the HTTP basic auth middleware"""

    editing = True

    def setUp(self):
        super().setUp()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(test_main.TEST_PASSWD.decode('utf-8'))
            self.auth_file = f.name
        self.addCleanup(os.remove, self.auth_file)

        extra_config = {'SUSHY_EMULATOR_AUTH_FILE': self.auth_file}
        if self.editing:
            extra_config['SUSHY_EMULATOR_ACCOUNT_EDITING'] = True

        self.app = main.Application()
        self.app.register_blueprint(acctctl.account_service)
        self.app.configure(extra_config=extra_config)
        self.app = self.app.test_client()

    def test_add_account_and_authenticate(self):
        response = self.app.get('/redfish/v1/AccountService/Accounts/admin')
        self.assertEqual(401, response.status_code)

        response = self.app.post(
            '/redfish/v1/AccountService/Accounts',
            auth=('admin', 'password'),
            json={'UserName': 'bob', 'Password': 'myPassword'})
        self.assertEqual(201, response.status_code, response.data)

        # the newly created user can authenticate via HTTP basic auth
        response = self.app.get('/redfish/v1/AccountService/Accounts/bob',
                                auth=('bob', 'myPassword'))
        self.assertEqual(200, response.status_code)
        self.assertEqual('bob', response.json['UserName'])


class ReadOnlyAuthenticatedAccountServiceTestCase(
        AuthenticatedAccountServiceTestCase):

    editing = False

    def test_add_account_and_authenticate(self):
        # the same request as with editing enabled, now rejected
        response = self.app.post(
            '/redfish/v1/AccountService/Accounts',
            auth=('admin', 'password'),
            json={'UserName': 'bob', 'Password': 'myPassword'})
        self.assertEqual(405, response.status_code, response.data)

        # the account was not created and cannot authenticate
        response = self.app.get('/redfish/v1/AccountService/Accounts/bob',
                                auth=('bob', 'myPassword'))
        self.assertEqual(401, response.status_code)

        # the admin credentials still work
        response = self.app.get('/redfish/v1/AccountService/Accounts/admin',
                                auth=('admin', 'password'))
        self.assertEqual(200, response.status_code)

    def test_mutation_not_allowed(self):
        # even with a malformed payload, not a validation error
        response = self.app.post(
            '/redfish/v1/AccountService/Accounts',
            auth=('admin', 'password'),
            json={'UserName': 'bob'})
        self.assertEqual(405, response.status_code)
