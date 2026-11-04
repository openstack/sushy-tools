# Copyright 2026 Red Hat, Inc.
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

import contextlib
import os
import re
import tempfile
import threading

import bcrypt

from sushy_tools.emulator import auth_basic
from sushy_tools.emulator.resources import base
from sushy_tools import error


# bcrypt only makes use of the first 72 bytes of a password
MAX_PASSWORD_LENGTH = 72

# Same cost as the htpasswd default, keeps authentication fast since
# the basic auth middleware verifies the password on every request
_BCRYPT_ROUNDS = 5

# Characters that are safe in user names for both the auth user file
# format and URIs
_USERNAME_RE = re.compile(r'^[A-Za-z0-9._@-]+$')


class StaticDriver(base.DriverBase):
    """Account service simulator backed by an Apache-style user auth file

    Accounts are listed from the authentication file used by the HTTP
    basic auth middleware. If the SUSHY_EMULATOR_ACCOUNT_EDITING
    configuration option is enabled, accounts can also be created,
    deleted and given new passwords through the AccountService, and the
    changes are written to the file so that the new users can
    authenticate against the emulator just like on a real BMC.

    The user name doubles as the account identity, which keeps the
    identities stable no matter how the file is edited. The first user
    in the file is treated as the built-in account that cannot be
    removed (its password can still be changed).

    Mutations are serialized with a lock, which is enough for the
    threaded development server. Multi-process WSGI deployments sharing
    one auth user file would need file locking.
    """

    _lock = threading.Lock()

    def __init__(self, config, logger, auth_file):
        super().__init__(config, logger)
        self._auth_file = auth_file

    @property
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """
        return '<static-accounts>'

    def check_editing_allowed(self):
        """Raise an error unless account editing is enabled

        :raises: `error.MethodNotAllowed` if the
            SUSHY_EMULATOR_ACCOUNT_EDITING option is not enabled
        """
        if not self._config.get('SUSHY_EMULATOR_ACCOUNT_EDITING'):
            raise error.MethodNotAllowed(
                'Account management is not enabled '
                '(SUSHY_EMULATOR_ACCOUNT_EDITING)')

    def _read_entries(self):
        """Read user entries from the auth user file

        Lines without a colon are ignored, like in the basic auth
        middleware.

        :returns: a list of (username, bcrypt digest) tuples in file order
        :raises: `error.FishyError` if the file cannot be read or parsed
        """
        try:
            with open(self._auth_file) as f:
                entries = []
                for line in f:
                    entry = line.strip()
                    if entry and ':' in entry:
                        entries.append(auth_basic.parse_entry(entry))
                return entries
        except OSError as exc:
            raise error.FishyError(f'Problem reading the auth user file: '
                                   f'{exc}')

    def _write_entries(self, entries):
        """Write user entries back to the auth user file

        The file is replaced atomically, preserving its location (also
        through symlinks), its permissions and the order of the entries.

        :raises: `error.FishyError` if the file cannot be written
        """
        target = os.path.realpath(self._auth_file)
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                    'w', dir=os.path.dirname(target) or '.',
                    delete=False) as f:
                tmp_file = f.name
                for username, digest in entries:
                    f.write(f'{username}:{digest.decode("utf-8")}\n')
            os.chmod(tmp_file, os.stat(target).st_mode & 0o777)
            os.replace(tmp_file, target)
            tmp_file = None
        except OSError as exc:
            raise error.FishyError(f'Problem writing the auth user file: '
                                   f'{exc}')
        finally:
            if tmp_file is not None:
                with contextlib.suppress(OSError):
                    os.remove(tmp_file)

    @staticmethod
    def _find_entry(username, entries):
        """Find a user entry by user name

        :param username: user name to find
        :param entries: a list of (username, digest) tuples
        :raises: `error.NotFound` if there is no such user
        """
        for entry in entries:
            if entry[0] == username:
                return entry

        raise error.NotFound(f'No account with ID {username}')

    @property
    def accounts(self):
        """Return available user accounts

        :returns: a list of dicts with `Id` and `UserName` keys
        """
        return [{'Id': username, 'UserName': username}
                for username, digest in self._read_entries()]

    def get_account(self, identity):
        """Get a user account by its identity

        :param identity: account identity, which is the user name
        :returns: a dict with `Id` and `UserName` keys
        :raises: `error.NotFound` if no account matches the identity
        """
        username, digest = self._find_entry(identity, self._read_entries())
        return {'Id': username, 'UserName': username}

    def add_account(self, username, password):
        """Create a new user account

        :param username: user name for the new account
        :param password: password for the new account
        :returns: identity of the new account, which is the user name
        :raises: `error.MethodNotAllowed` if account editing is disabled
        :raises: `error.BadRequest` on invalid or duplicate user name
        """
        self.check_editing_allowed()

        if not isinstance(username, str) or not _USERNAME_RE.match(username):
            raise error.BadRequest(f'Invalid user name {username!r}')

        digest = self._hash_password(password)

        with self._lock:
            entries = self._read_entries()
            if any(entry[0] == username for entry in entries):
                raise error.BadRequest(f'User {username} already exists')
            entries.append((username, digest))
            self._write_entries(entries)

        return username

    def delete_account(self, identity):
        """Delete a user account

        The built-in account (the first user in the auth user file)
        cannot be deleted.

        :param identity: account identity, which is the user name
        :raises: `error.MethodNotAllowed` if account editing is disabled
        :raises: `error.NotFound` if no account matches the identity
        :raises: `error.BadRequest` for the built-in account
        """
        self.check_editing_allowed()

        with self._lock:
            entries = self._read_entries()
            self._find_entry(identity, entries)

            if identity == entries[0][0]:
                raise error.BadRequest('The built-in user account '
                                       'cannot be deleted')

            entries = [entry for entry in entries if entry[0] != identity]
            self._write_entries(entries)

    def set_password(self, identity, password):
        """Change the password of a user account

        :param identity: account identity, which is the user name
        :param password: new password for the account
        :raises: `error.MethodNotAllowed` if account editing is disabled
        :raises: `error.NotFound` if no account matches the identity
        """
        self.check_editing_allowed()

        digest = self._hash_password(password)

        with self._lock:
            entries = self._read_entries()
            self._find_entry(identity, entries)
            entries = [(name, digest if name == identity else old_digest)
                       for name, old_digest in entries]
            self._write_entries(entries)

    @staticmethod
    def _hash_password(password):
        """Digest a password with bcrypt

        :param password: password as a string
        :returns: bcrypt digest as bytes
        :raises: `error.BadRequest` on an invalid password
        """
        if not isinstance(password, str) or not password:
            raise error.BadRequest('Password must be a non-empty string')

        try:
            encoded = password.encode('utf-8')
        except UnicodeEncodeError:
            raise error.BadRequest('Password is not valid UTF-8')

        if len(encoded) > MAX_PASSWORD_LENGTH:
            raise error.BadRequest(
                f'Password cannot be longer than {MAX_PASSWORD_LENGTH} bytes')

        return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
