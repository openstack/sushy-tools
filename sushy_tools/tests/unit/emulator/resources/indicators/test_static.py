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

from sushy_tools.emulator.resources.indicators.staticdriver import StaticDriver
from sushy_tools import error


@mock.patch('sushy_tools.emulator.resources.indicators'
            '.staticdriver.memoize.PersistentDict', new=dict)
class StaticDriverTestCase(base.BaseTestCase):

    UUID = "58893887-8974-2487-2389-841168418919"
    STATE = "Off"

    CONFIG = {
        'SUSHY_EMULATOR_INDICATOR_LEDS': {
            UUID: STATE
        }
    }

    def test_indicators(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()
        indicators = test_driver.indicators
        self.assertEqual([self.UUID], indicators)

    def test_get_indicator_state(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()
        state = test_driver.get_indicator_state(self.UUID)
        self.assertEqual('Off', state)

    def test_set_indicator_state_ok(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()
        test_driver.set_indicator_state(self.UUID, 'Lit')
        state = test_driver.get_indicator_state(self.UUID)
        self.assertEqual('Lit', state)

    def test_set_indicator_state_fail(self):
        test_driver = StaticDriver.initialize(
            self.CONFIG, mock.MagicMock())()

        self.assertRaises(
            error.FishyError,
            test_driver.set_indicator_state,
            self.UUID, 'Blah')
