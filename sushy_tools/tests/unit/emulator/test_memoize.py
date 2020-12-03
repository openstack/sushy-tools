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

import pickle
import sqlite3
from unittest import mock

from oslotest import base

from sushy_tools.emulator import memoize


class MemoizeTestCase(base.BaseTestCase):

    def test_local_cache(self):

        class Driver(object):
            call_count = 0

            @memoize.memoize()
            def fun(self, *args, **kwargs):
                self.call_count += 1
                return args, kwargs

        driver = Driver()

        result = driver.fun(1, x=2)
        self.assertEqual(((1,), {'x': 2}), result)

        result = driver.fun(1, x=2)
        self.assertEqual(((1,), {'x': 2}), result)

        # Due to memoization, expect just one call
        self.assertEqual(1, driver.call_count)

        driver = Driver()

        result = driver.fun(1, x=2)
        self.assertEqual(((1,), {'x': 2}), result)

        # Due to volatile cache, expect one more call
        self.assertEqual(1, driver.call_count)

    def test_external_cache(self):

        permanent_cache = {}

        class Driver(object):
            call_count = 0

            @memoize.memoize(permanent_cache=permanent_cache)
            def fun(self, *args, **kwargs):
                self.call_count += 1
                return args, kwargs

        driver = Driver()

        result = driver.fun(1, x=2)
        self.assertEqual(((1,), {'x': 2}), result)

        result = driver.fun(1, x=2)
        self.assertEqual(((1,), {'x': 2}), result)

        # Due to memoization, expect just one call
        self.assertEqual(1, driver.call_count)

        driver = Driver()

        result = driver.fun(1, x=2)
        self.assertEqual(((1,), {'x': 2}), result)

        # Due to permanent cache, expect no more calls
        self.assertEqual(0, driver.call_count)


@mock.patch.object(sqlite3, 'connect', autospec=True)
class PersistentDictTestCase(base.BaseTestCase):

    def test_make_permanent(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')
        mock_sqlite3.assert_called_once_with('/file.sqlite')

    def test_encode(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        value = pd.encode({1: '2'})
        self.assertEqual(pickle.dumps({1: '2'}), value)

    def test_decode(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        value = pd.decode(pickle.dumps({1: '2'}))
        self.assertEqual({1: '2'}, value)

    def test___getitem__(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_conn = mock_sqlite3.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.reset_mock()
        mock_cursor.fetchone.return_value = [pickle.dumps('pickled-value')]

        result = pd[1]
        self.assertEqual('pickled-value', result)

        mock_cursor.execute.assert_called_with(
            'select value from cache where key=?', (pickle.dumps(1),))

    def test___getitem__retries(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_conn = mock_sqlite3.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.reset_mock()
        mock_cursor.execute.side_effect = [
            sqlite3.OperationalError,
            None
        ]
        mock_cursor.fetchone.return_value = [pickle.dumps('pickled-value')]

        result = pd[1]
        self.assertEqual('pickled-value', result)

        mock_cursor.execute.assert_called_with(
            'select value from cache where key=?', (pickle.dumps(1),))
        self.assertEqual(2, mock_cursor.execute.call_count)

    def test___setitem__(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_conn = mock_sqlite3.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.reset_mock()

        pd[1] = 2

        mock_cursor.execute.assert_called_once_with(
            'insert or replace into cache values (?, ?)',
            (pickle.dumps(1), pickle.dumps(2)))

    def test___setitem__retries(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_conn = mock_sqlite3.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.reset_mock()
        mock_cursor.execute.side_effect = [
            sqlite3.OperationalError,
            None
        ]

        pd[1] = 2

        mock_cursor.execute.assert_called_with(
            'insert or replace into cache values (?, ?)',
            (pickle.dumps(1), pickle.dumps(2)))
        self.assertEqual(2, mock_cursor.execute.call_count)

    def test___delitem__(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_conn = mock_sqlite3.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.reset_mock()

        del pd[1]

        mock_cursor.execute.assert_called_once_with(
            'delete from cache where key=?', (pickle.dumps(1),))

    def test___delitem__fails(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_conn = mock_sqlite3.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.reset_mock()
        mock_cursor.rowcount = 0

        def _del():
            del pd[1]

        self.assertRaises(KeyError, _del)

        mock_cursor.execute.assert_called_once_with(
            'delete from cache where key=?', (pickle.dumps(1),))

    def test___iter__(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_conn = mock_sqlite3.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.reset_mock()
        mock_cursor.fetchall.return_value = [[pickle.dumps('pickled-key')]]

        self.assertEqual(['pickled-key'], list(iter(pd)))

        mock_cursor.execute.assert_called_once_with('select key from cache')

    def test___len__(self, mock_sqlite3):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_conn = mock_sqlite3.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.execute.reset_mock()
        mock_cursor.fetchone.return_value = [42]

        self.assertEqual(42, len(pd))

        mock_cursor.execute.assert_called_once_with(
            'select count(*) from cache')
