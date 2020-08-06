# Copyright 2019 Red Hat, Inc.
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

from sushy_tools.emulator.resources.indicators import StaticDriver
from sushy_tools import error


class StaticDriverTestCase(base.BaseTestCase):

    UUID = "58893887-8974-2487-2389-841168418919"
    STATE = "Off"

    CONFIG = {
        'SUSHY_EMULATOR_INDICATOR_LEDS': {
            UUID: STATE
        }
    }

    def setUp(self):
        super().setUp()
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value={}, autospec=True):
            self.test_driver = StaticDriver(self.CONFIG, mock.MagicMock())

    def test_indicators(self):
        indicators = self.test_driver.indicators
        self.assertEqual([self.UUID], indicators)

    def test_get_indicator_state(self):
        state = self.test_driver.get_indicator_state(self.UUID)
        self.assertEqual('Off', state)

    def test_set_indicator_state_ok(self):
        self.test_driver.set_indicator_state(self.UUID, 'Lit')
        state = self.test_driver.get_indicator_state(self.UUID)
        self.assertEqual('Lit', state)

    def test_set_indicator_state_fail(self):
        self.assertRaises(
            error.FishyError,
            self.test_driver.set_indicator_state,
            self.UUID, 'Blah')
