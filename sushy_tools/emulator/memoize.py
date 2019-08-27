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

try:
    from collections import abc as collections

except ImportError:
    import collections

import contextlib
from functools import wraps
import os
import pickle
import sqlite3
import tempfile

# Python 3.8
MutableMapping = getattr(collections, 'abc', collections).MutableMapping


def memoize(permanent_cache=None):
    """Cache the return value of the decorated method.

    :param permanent_cache: a `dict` like object to use as a cache.
        If not given, the `._cache` attribute would be added to
        the object of the decorated method pointing to a newly
        created `dict`.
    :return: decorated function
    """

    def decorator(method):

        @wraps(method)
        def wrapped(self, *args, **kwargs):
            if permanent_cache is None:
                try:
                    cache = self._cache

                except AttributeError:
                    cache = self._cache = {}

            else:
                cache = permanent_cache

            method_cache = cache.setdefault(method, {})

            key = frozenset(args), frozenset(kwargs)

            try:
                return method_cache[key]

            except KeyError:
                rv = method(self, *args, **kwargs)
                method_cache[key] = rv
                return rv

        return wrapped

    return decorator


class PersistentDict(MutableMapping):
    DBPATH = os.path.join(tempfile.gettempdir(), 'sushy-emulator')

    _dbpath = None

    def make_permanent(self, dbpath, dbfile):
        dbpath = dbpath or self.DBPATH
        if not os.path.exists(dbpath):
            os.makedirs(dbpath)

        self._dbpath = os.path.join(dbpath, dbfile) + '.sqlite'

        with self.connection() as cursor:
            cursor.execute(
                'create table if not exists cache '
                '(key blob primary key not null, value blob not null)'
            )

        self.update(dict(self))

    @staticmethod
    def encode(obj):
        return pickle.dumps(obj)

    @staticmethod
    def decode(blob):
        return pickle.loads(blob)

    @contextlib.contextmanager
    def connection(self):
        if not self._dbpath:
            raise TypeError('Dict is not yet persistent')

        connection = sqlite3.connect(self._dbpath)

        try:
            yield connection.cursor()

            connection.commit()

        finally:
            connection.close()

    def __getitem__(self, key):
        key = self.encode(key)

        with self.connection() as cursor:
            cursor.execute(
                'select value from cache where key=?',
                (key,)
            )
            value = cursor.fetchone()

        if value is None:
            raise KeyError(key)

        return self.decode(value[0])

    def __setitem__(self, key, value):
        key = self.encode(key)
        value = self.encode(value)

        with self.connection() as cursor:
            cursor.execute(
                'insert or replace into cache values (?, ?)',
                (key, value)
            )

    def __delitem__(self, key):
        key = self.encode(key)

        with self.connection() as cursor:
            cursor.execute(
                'select count(*) from cache where key=?',
                (key,)
            )

            if cursor.fetchone()[0] == 0:
                raise KeyError(key)

            cursor.execute(
                'delete from cache where key=?',
                (key,)
            )

    def __iter__(self):
        with self.connection() as cursor:
            cursor.execute(
                'select key from cache'
            )
            records = cursor.fetchall()

        for r in records:
            yield self.decode(r[0])

    def __len__(self):
        with self.connection() as cursor:
            cursor.execute(
                'select count(*) from cache'
            )
            count = cursor.fetchone()[0]
            return count
