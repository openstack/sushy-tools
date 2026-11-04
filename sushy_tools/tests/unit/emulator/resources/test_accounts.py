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

import logging
import os
import tempfile
import threading

import bcrypt
from oslotest import base

from sushy_tools.emulator import auth_basic
from sushy_tools.emulator.resources import accounts
from sushy_tools import error


LOG = logging.getLogger(__name__)

EDITING_CONFIG = {'SUSHY_EMULATOR_ACCOUNT_EDITING': True}


class StaticDriverTestCase(base.BaseTestCase):

    def setUp(self):
        super().setUp()

        # the built-in account first, another account after it
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            self.auth_file = f.name
            f.write('admin:$2y$05$mYl8KMwM94l4LR/sw1teIeA6P2u8gfX16e8w'
                    'vT7NmGgAM5r9jgLl.\n')
            f.write('other:%s\n' % bcrypt.hashpw(
                b'otherPassword', bcrypt.gensalt(rounds=4)).decode())
        self.addCleanup(os.remove, self.auth_file)

        self.test_driver = accounts.StaticDriver(
            EDITING_CONFIG, LOG, self.auth_file)
        self.readonly_driver = accounts.StaticDriver({}, LOG, self.auth_file)

    def _read_lines(self):
        with open(self.auth_file) as f:
            return f.read().splitlines()

    def test_accounts(self):
        self.assertEqual(
            [{'Id': 'admin', 'UserName': 'admin'},
             {'Id': 'other', 'UserName': 'other'}],
            self.test_driver.accounts)

    def test_accounts_ignores_malformed_lines(self):
        with open(self.auth_file, 'a') as f:
            f.write('not-a-valid-line\n')

        self.assertEqual(['admin', 'other'],
                         [account['Id']
                          for account in self.test_driver.accounts])

    def test_get_account(self):
        self.assertEqual({'Id': 'other', 'UserName': 'other'},
                         self.test_driver.get_account('other'))

    def test_get_account_not_found(self):
        self.assertRaises(error.NotFound,
                          self.test_driver.get_account, 'nosuch')

    def test_editing_disabled(self):
        # accounts can still be listed and read...
        self.assertEqual(
            [{'Id': 'admin', 'UserName': 'admin'},
             {'Id': 'other', 'UserName': 'other'}],
            self.readonly_driver.accounts)
        self.assertEqual({'Id': 'admin', 'UserName': 'admin'},
                         self.readonly_driver.get_account('admin'))

        # ...but not modified in any way
        self.assertRaises(error.MethodNotAllowed,
                          self.readonly_driver.add_account,
                          'bob', 'bobPassword')
        self.assertRaises(error.MethodNotAllowed,
                          self.readonly_driver.delete_account, 'other')
        self.assertRaises(error.MethodNotAllowed,
                          self.readonly_driver.set_password,
                          'admin', 'newPassword')

        # and the auth user file is left untouched
        self.assertEqual(2, len(self._read_lines()))

    def test_add_account(self):
        self.assertEqual('bob',
                         self.test_driver.add_account('bob', 'bobPassword'))

        # the new account is appended, other entries are untouched
        lines = self._read_lines()
        self.assertEqual(3, len(lines))
        self.assertTrue(lines[0].startswith('admin:'))
        self.assertTrue(lines[1].startswith('other:'))
        username, digest = auth_basic.parse_entry(lines[2])
        self.assertEqual('bob', username)
        self.assertTrue(bcrypt.checkpw(b'bobPassword', digest))

    def test_add_account_duplicate(self):
        self.assertRaises(error.BadRequest, self.test_driver.add_account,
                          'admin', 'newPassword')

    def test_add_account_invalid_username(self):
        for username in ('', 'bo:b', 'bo/b', 'bo b', 'bo\nb', 'ünïcode',
                         None, 42):
            self.assertRaises(error.BadRequest, self.test_driver.add_account,
                              username, 'newPassword')

    def test_add_account_invalid_password(self):
        for password in ('', None, 42, 'x' * 73, '\ud800'):
            self.assertRaises(error.BadRequest, self.test_driver.add_account,
                              'bob', password)

    def test_add_account_multibyte_password(self):
        # 72 bytes is the limit even for multi-byte characters
        self.assertRaises(error.BadRequest, self.test_driver.add_account,
                          'bob', 'é' * 37)
        self.assertEqual('bob', self.test_driver.add_account('bob', 'é' * 36))

    def test_delete_account(self):
        self.test_driver.delete_account('other')

        lines = self._read_lines()
        self.assertEqual(1, len(lines))
        self.assertTrue(lines[0].startswith('admin:'))

    def test_delete_builtin_account(self):
        self.assertRaises(error.BadRequest, self.test_driver.delete_account,
                          'admin')

    def test_delete_account_not_found(self):
        self.assertRaises(error.NotFound, self.test_driver.delete_account,
                          'nosuch')

    def test_set_password(self):
        self.test_driver.set_password('other', 'newPassword')

        lines = self._read_lines()
        self.assertEqual(2, len(lines))
        self.assertTrue(lines[0].startswith('admin:'))
        username, digest = auth_basic.parse_entry(lines[1])
        self.assertEqual('other', username)
        self.assertTrue(bcrypt.checkpw(b'newPassword', digest))
        self.assertFalse(bcrypt.checkpw(b'otherPassword', digest))

    def test_set_password_not_found(self):
        self.assertRaises(error.NotFound, self.test_driver.set_password,
                          'nosuch', 'newPassword')

    def test_write_preserves_permissions_and_symlinks(self):
        os.chmod(self.auth_file, 0o644)
        with tempfile.TemporaryDirectory() as tmpdir:
            link = os.path.join(tmpdir, 'auth-file')
            os.symlink(os.path.realpath(self.auth_file), link)
            driver = accounts.StaticDriver(EDITING_CONFIG, LOG, link)

            driver.add_account('bob', 'bobPassword')

            self.assertTrue(os.path.islink(link))
            self.assertEqual(0o644, os.stat(link).st_mode & 0o777)
            with open(link) as f:
                lines = f.read().splitlines()
            self.assertEqual(3, len(lines))
            # no temporary files are left behind
            self.assertEqual(['auth-file'], os.listdir(tmpdir))

    def test_write_error(self):
        driver = accounts.StaticDriver(
            EDITING_CONFIG, LOG, '/nosuch-directory/nosuch-file')
        self.assertRaises(error.FishyError, driver.add_account,
                          'bob', 'bobPassword')

    def test_concurrent_add_accounts(self):
        errors = []

        def add(username):
            try:
                self.test_driver.add_account(username, username + 'Password')
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=add, args=(f'user{i}',))
                   for i in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual([], errors)
        # all accounts are stored, the built-in one stays first
        ids = [account['Id'] for account in self.test_driver.accounts]
        self.assertEqual('admin', ids[0])
        self.assertEqual({'admin', 'other', 'user0', 'user1', 'user2',
                          'user3', 'user4'}, set(ids))
