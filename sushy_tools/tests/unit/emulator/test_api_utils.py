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

from sushy_tools.emulator import api_utils
from sushy_tools.emulator import main
from sushy_tools.tests.unit.emulator import test_main


class InstanceDeniedTestCase(test_main.EmulatorTestCase):

    def setUp(self):
        super().setUp()
        ctx = main.app.app_context().__enter__()
        self.addCleanup(lambda: ctx.__exit__(None, None, None))

    @mock.patch.dict(main.app.config, {}, clear=True)
    def test_instance_denied_allow_all(self):
        self.assertFalse(api_utils.instance_denied(identity='x'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {}})
    def test_instance_denied_disallow_all(self):
        self.assertTrue(api_utils.instance_denied(identity='a'))

    def test_instance_denied_undefined_option(self):
        with mock.patch.dict(main.app.config):
            main.app.config.pop('SUSHY_EMULATOR_ALLOWED_INSTANCES', None)
            self.assertFalse(api_utils.instance_denied(identity='a'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {'a'}})
    def test_instance_denied_allow_some(self):
        self.assertFalse(api_utils.instance_denied(identity='a'))

    @mock.patch.dict(
        main.app.config, {'SUSHY_EMULATOR_ALLOWED_INSTANCES': {'a'}})
    def test_instance_denied_disallow_some(self):
        self.assertTrue(api_utils.instance_denied(identity='b'))
