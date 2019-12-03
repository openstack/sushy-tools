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


class PersistentDictTestCase(base.BaseTestCase):

    @mock.patch.object(memoize, 'sqlite3', autospec=True)
    def test_make_permanent(self, mock_sqlite3):
        pd = memoize.PersistentDict()

        pd.make_permanent('/', 'file')

        mock_sqlite3.connect.assert_called_with('/file.sqlite')

    @mock.patch.object(memoize, 'pickle', autospec=True)
    def test_encode(self, mock_pickle):
        pd = memoize.PersistentDict()

        pd.encode({1: '2'})

        mock_pickle.dumps.assert_called_once_with({1: '2'})

    @mock.patch.object(memoize, 'pickle', autospec=True)
    def test_decode(self, mock_pickle):
        pd = memoize.PersistentDict()

        pd.decode('blob')

        mock_pickle.loads.assert_called_once_with('blob')

    @mock.patch.object(memoize, 'pickle', autospec=True)
    @mock.patch.object(memoize, 'sqlite3', autospec=True)
    def test___getitem__(self, mock_sqlite3, mock_pickle):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_pickle.dumps.return_value = 'pickled-key'
        mock_connection = mock_sqlite3.connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchone.return_value = ['pickled-value']

        pd[1]

        mock_cursor.execute.assert_called_with(
            'select value from cache where key=?', ('pickled-key',))
        mock_pickle.loads.assert_called_once_with('pickled-value')

    @mock.patch.object(memoize, 'pickle', autospec=True)
    @mock.patch.object(memoize, 'sqlite3', autospec=True)
    def test___setitem__(self, mock_sqlite3, mock_pickle):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_pickle.dumps.side_effect = [
            'pickled-key', 'pickled-value']

        mock_connection = mock_sqlite3.connect.return_value
        mock_cursor = mock_connection.cursor.return_value

        pd[1] = 2

        mock_cursor.execute.assert_called_with(
            'insert or replace into cache values (?, ?)',
            ('pickled-key', 'pickled-value'))

    @mock.patch.object(memoize, 'pickle', autospec=True)
    @mock.patch.object(memoize, 'sqlite3', autospec=True)
    def test___delitem__(self, mock_sqlite3, mock_pickle):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_pickle.dumps.return_value = 'pickled-key'
        mock_connection = mock_sqlite3.connect.return_value
        mock_cursor = mock_connection.cursor.return_value

        del pd[1]

        mock_cursor.execute.assert_called_with(
            'delete from cache where key=?', ('pickled-key',))

    @mock.patch.object(memoize, 'pickle', autospec=True)
    @mock.patch.object(memoize, 'sqlite3', autospec=True)
    def test___iter__(self, mock_sqlite3, mock_pickle):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_pickle.dumps.return_value = 'pickled-key'
        mock_connection = mock_sqlite3.connect.return_value
        mock_cursor = mock_connection.cursor.return_value
        mock_cursor.fetchall.return_value = [['pickled-key']]

        for x in pd:
            x += x

        mock_cursor.execute.assert_called_with('select key from cache')
        mock_pickle.loads.assert_called_once_with('pickled-key')

    @mock.patch.object(memoize, 'pickle', autospec=True)
    @mock.patch.object(memoize, 'sqlite3', autospec=True)
    def test___len__(self, mock_sqlite3, mock_pickle):
        pd = memoize.PersistentDict()
        pd.make_permanent('/', 'file')

        mock_connection = mock_sqlite3.connect.return_value
        mock_cursor = mock_connection.cursor.return_value

        expected = 1

        mock_cursor.fetchone.return_value = [expected]

        self.assertEqual(expected, len(pd))

        mock_cursor.execute.assert_called_with('select count(*) from cache')
