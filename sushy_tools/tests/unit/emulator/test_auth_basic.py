# Copyright 2020 Red Hat, Inc.
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

import base64
import json
import os
import tempfile
from unittest import mock

from sushy_tools.emulator import auth_basic
from sushy_tools import error
from sushy_tools.tests.unit import base


class TestAuthBasic(base.TestCase):

    def write_auth_file(self, data=None):
        if not data:
            data = '\n'
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(data)
            self.addCleanup(os.remove, f.name)
            return f.name

    def test_middleware_authenticate(self):
        auth_file = self.write_auth_file(
            'myName:$2y$05$lE3eGtyj41jZwrzS87KTqe6.'
            'JETVCWBkc32C63UP2aYrGoYOEpbJm\n\n\n')
        app = mock.Mock()
        start_response = mock.Mock()
        middleware = auth_basic.BasicAuthMiddleware(app, auth_file)
        env = {
            'HTTP_AUTHORIZATION': 'Basic bXlOYW1lOm15UGFzc3dvcmQ='
        }

        result = middleware(env, start_response)
        self.assertEqual(app.return_value, result)
        start_response.assert_not_called()

    def test_middleware_unauthenticated(self):
        auth_file = self.write_auth_file(
            'myName:$2y$05$lE3eGtyj41jZwrzS87KTqe6.'
            'JETVCWBkc32C63UP2aYrGoYOEpbJm\n\n\n')
        app = mock.Mock()
        start_response = mock.Mock()
        middleware = auth_basic.BasicAuthMiddleware(app, auth_file)
        env = {'REQUEST_METHOD': 'GET'}

        body = middleware(env, start_response)
        decoded = json.loads(body[0].decode())
        self.assertEqual({'error': {'message': 'Authorization required',
                                    'code': 401}}, decoded)

        start_response.assert_called_once_with(
            '401 Unauthorized',
            [('WWW-Authenticate', 'Basic realm="Baremetal API"'),
             ('Content-Type', 'application/json'),
             ('Content-Length', str(len(body[0])))]
        )
        app.assert_not_called()

    def test_authenticate(self):
        auth_file = self.write_auth_file(
            'foo:bar\nmyName:$2y$05$lE3eGtyj41jZwrzS87KTqe6.'
            'JETVCWBkc32C63UP2aYrGoYOEpbJm\n\n\n')

        # test basic auth
        self.assertEqual(
            {'HTTP_X_USER': 'myName', 'HTTP_X_USER_NAME': 'myName'},
            auth_basic.authenticate(
                auth_file, 'myName', b'myPassword')
        )

        # test failed auth
        e = self.assertRaises(error.ConfigInvalid,
                              auth_basic.authenticate,
                              auth_file, 'foo', b'bar')
        self.assertEqual('Invalid configuration file. Only bcrypt digested '
                         'passwords are supported for foo', str(e))

        # test problem reading user data file
        auth_file = auth_file + '.missing'
        e = self.assertRaises(error.ConfigInvalid,
                              auth_basic.authenticate,
                              auth_file, 'myName',
                              b'myPassword')
        self.assertEqual('Invalid configuration file. Problem reading '
                         'auth user file', str(e))

    def test_auth_entry(self):
        entry_pass = ('myName:$2y$05$lE3eGtyj41jZwrzS87KTqe6.'
                      'JETVCWBkc32C63UP2aYrGoYOEpbJm')
        entry_pass_2a = ('myName:$2a$10$I9Fi3DM1sbxQP0560MK9'
                         'tec1dUdytBtIqXfDCyTNfDUabtGvQjW1S')
        entry_pass_2b = ('myName:$2b$12$dWLBxT6aMxpVTfUNAyOu'
                         'IusHXewu8m6Hrsxw4/e95WGBelFn0oOMW')
        entry_fail = 'foo:bar'

        # success
        self.assertEqual(
            {'HTTP_X_USER': 'myName', 'HTTP_X_USER_NAME': 'myName'},
            auth_basic.auth_entry(
                entry_pass, b'myPassword')
        )

        # success with a bcrypt implementations other than htpasswd
        self.assertEqual(
            {'HTTP_X_USER': 'myName', 'HTTP_X_USER_NAME': 'myName'},
            auth_basic.auth_entry(
                entry_pass_2a, b'myPassword')
        )
        self.assertEqual(
            {'HTTP_X_USER': 'myName', 'HTTP_X_USER_NAME': 'myName'},
            auth_basic.auth_entry(
                entry_pass_2b, b'myPassword')
        )

        # failed, unknown digest format
        e = self.assertRaises(error.ConfigInvalid,
                              auth_basic.auth_entry, entry_fail, b'bar')
        self.assertEqual('Invalid configuration file. Only bcrypt digested '
                         'passwords are supported for foo', str(e))

        # failed, incorrect password
        e = self.assertRaises(error.Unauthorized,
                              auth_basic.auth_entry, entry_pass, b'bar')
        self.assertEqual('Incorrect username or password', str(e))

    def test_validate_auth_file(self):
        auth_file = self.write_auth_file(
            'myName:$2y$05$lE3eGtyj41jZwrzS87KTqe6.'
            'JETVCWBkc32C63UP2aYrGoYOEpbJm\n\n\n')
        # success, valid config
        auth_basic.validate_auth_file(auth_file)

        # failed, missing auth file
        auth_file = auth_file + '.missing'
        self.assertRaises(error.ConfigInvalid,
                          auth_basic.validate_auth_file, auth_file)

        # failed, invalid entry
        auth_file = self.write_auth_file(
            'foo:bar\nmyName:$2y$05$lE3eGtyj41jZwrzS87KTqe6.'
            'JETVCWBkc32C63UP2aYrGoYOEpbJm\n\n\n')
        self.assertRaises(error.ConfigInvalid,
                          auth_basic.validate_auth_file, auth_file)

    def test_parse_token(self):

        # success with bytes
        token = base64.b64encode(b'myName:myPassword')
        self.assertEqual(
            ('myName', b'myPassword'),
            auth_basic.parse_token(token)
        )

        # success with string
        token = str(token, encoding='utf-8')
        self.assertEqual(
            ('myName', b'myPassword'),
            auth_basic.parse_token(token)
        )

        # failed, invalid base64
        e = self.assertRaises(error.BadRequest,
                              auth_basic.parse_token, token[:-1])
        self.assertEqual('Could not decode authorization token', str(e))

        # failed, no colon in token
        token = str(base64.b64encode(b'myNamemyPassword'), encoding='utf-8')
        e = self.assertRaises(error.BadRequest,
                              auth_basic.parse_token, token[:-1])
        self.assertEqual('Could not decode authorization token', str(e))

    def test_parse_header(self):
        auth_value = 'Basic bXlOYW1lOm15UGFzc3dvcmQ='

        # success
        self.assertEqual(
            'bXlOYW1lOm15UGFzc3dvcmQ=',
            auth_basic.parse_header({
                'HTTP_AUTHORIZATION': auth_value
            })
        )

        # failed, missing Authorization header
        e = self.assertRaises(error.Unauthorized,
                              auth_basic.parse_header,
                              {})
        self.assertEqual('Authorization required', str(e))

        # failed missing token
        e = self.assertRaises(error.BadRequest,
                              auth_basic.parse_header,
                              {'HTTP_AUTHORIZATION': 'Basic'})
        self.assertEqual('Could not parse Authorization header', str(e))

        # failed, type other than Basic
        digest_value = 'Digest username="myName" nonce="foobar"'
        e = self.assertRaises(error.BadRequest,
                              auth_basic.parse_header,
                              {'HTTP_AUTHORIZATION': digest_value})
        self.assertEqual('Unsupported authorization type "Digest"', str(e))

    def test_unauthorized(self):
        e = self.assertRaises(error.Unauthorized,
                              auth_basic.unauthorized, 'ouch')
        self.assertEqual('ouch', str(e))
        self.assertEqual({
            'WWW-Authenticate': 'Basic realm="Baremetal API"'
        }, e.headers)
