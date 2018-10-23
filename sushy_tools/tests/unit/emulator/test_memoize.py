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

from oslotest import base

from sushy_tools.emulator.drivers import memoize


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
