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

import time
from unittest import mock

from oslotest import base

from sushy_tools.emulator.resources.systems import fakedriver
from sushy_tools import error


UUID = fakedriver.DEFAULT_UUID


class FakeDriverTestCase(base.BaseTestCase):

    def setUp(self):
        super().setUp()
        test_driver_class = fakedriver.FakeDriver.initialize(
            {}, mock.MagicMock())
        self.cache = {}
        with mock.patch('sushy_tools.emulator.memoize.PersistentDict',
                        return_value=self.cache, autospec=True):
            self.test_driver = test_driver_class()

    def test_systems(self):
        self.assertEqual([UUID], self.test_driver.systems)
        self.assertEqual('fake', self.test_driver.name(UUID))
        self.assertEqual(UUID, self.test_driver.uuid('fake'))
        self.assertEqual(UUID, self.test_driver.uuid(UUID))
        self.assertEqual('fake', self.test_driver.name('fake'))
        self.assertRaises(error.NotFound, self.test_driver.uuid, 'foo')
        self.assertRaises(error.NotFound, self.test_driver.name, 'foo')

    @mock.patch('random.randint', autospec=True, return_value=0)
    def test_power_state(self, mock_rand):
        self.assertEqual('Off', self.test_driver.get_power_state(UUID))
        self.test_driver.set_power_state(UUID, 'On')
        self.assertEqual('On', self.test_driver.get_power_state(UUID))
        self.test_driver.set_power_state(UUID, 'ForceOff')
        self.assertEqual('Off', self.test_driver.get_power_state(UUID))

    @mock.patch('random.randint', autospec=True, return_value=1000)
    def test_power_state_delay(self, mock_rand):
        self.assertEqual('Off', self.test_driver.get_power_state(UUID))
        self.test_driver.set_power_state(UUID, 'On')
        self.assertEqual('Off', self.test_driver.get_power_state(UUID))

        new_time = time.time() + 2000
        with mock.patch.object(time, 'time', autospec=True,
                               return_value=new_time):
            self.assertEqual('On', self.test_driver.get_power_state(UUID))

    @mock.patch('random.randint', autospec=True, return_value=1000)
    def test_reboot_delay(self, mock_rand):
        self.cache[UUID]['power_state'] = 'On'

        self.assertEqual('On', self.test_driver.get_power_state(UUID))
        self.test_driver.set_power_state(UUID, 'ForceRestart')
        self.assertEqual('Off', self.test_driver.get_power_state(UUID))

        new_time = time.time() + 2000
        with mock.patch.object(time, 'time', autospec=True,
                               return_value=new_time):
            self.assertEqual('On', self.test_driver.get_power_state(UUID))

    def test_boot_mode(self):
        self.assertEqual('UEFI', self.test_driver.get_boot_mode(UUID))
        self.test_driver.set_boot_mode(UUID, 'legacy')
        self.assertEqual('legacy', self.test_driver.get_boot_mode(UUID))

    def test_boot_device(self):
        self.assertEqual('Hdd', self.test_driver.get_boot_device(UUID))
        self.test_driver.set_boot_device(UUID, 'Cd')
        self.assertEqual('Cd', self.test_driver.get_boot_device(UUID))

    def test_boot_image(self):
        self.assertEqual((None, False, False),
                         self.test_driver.get_boot_image(UUID, 'Cd'))
        self.test_driver.set_boot_image(UUID, 'Cd', 'http://example')
        self.assertEqual(('http://example', True, True),
                         self.test_driver.get_boot_image(UUID, 'Cd'))
        self.assertEqual((None, False, False),
                         self.test_driver.get_boot_image(UUID, 'Hdd'))
