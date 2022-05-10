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

import copy
import random
import time

from sushy_tools.emulator import memoize
from sushy_tools.emulator.resources.systems.base import AbstractSystemsDriver
from sushy_tools import error


DEFAULT_UUID = '27946b59-9e44-4fa7-8e91-f3527a1ef094'


class FakeDriver(AbstractSystemsDriver):
    """Fake driver"""

    @classmethod
    def initialize(cls, config, logger):
        config.setdefault('SUSHY_EMULATOR_FAKE_SYSTEMS', [
            {
                'uuid': DEFAULT_UUID,
                'name': 'fake',
                'power_state': 'Off',
            }
        ])
        cls._config = config
        cls._logger = logger
        return cls

    def __init__(self):
        super().__init__()
        self._systems = memoize.PersistentDict()
        if hasattr(self._systems, 'make_permanent'):
            self._systems.make_permanent(
                self._config.get('SUSHY_EMULATOR_STATE_DIR'), 'fakedriver')

        for system in self._config['SUSHY_EMULATOR_FAKE_SYSTEMS']:
            # Be careful to reduce racing with other processes
            if system['uuid'] not in self._systems:
                self._systems[system['uuid']] = copy.deepcopy(system)

        self._by_name = {
            system['name']: uuid
            for uuid, system in self._systems.items()
        }

    def _update_if_needed(self, system):
        pending_power = system.get('pending_power')
        if pending_power and time.time() >= pending_power['apply_time']:
            self._update(system,
                         power_state=pending_power['power_state'],
                         pending_power=None)

        return system

    def _get(self, identity):
        try:
            result = self._systems[identity]
        except KeyError:
            try:
                uuid = self._by_name[identity]
            except KeyError:
                raise error.NotFound(f'Fake system {identity} was not found')
            else:
                raise error.AliasAccessError(uuid)

        # NOTE(dtantsur): since the state change can only be observed after
        # a _get() call, we can cheat a bit and update it on reading.
        return self._update_if_needed(result)

    def _update(self, system, **changes):
        if isinstance(system, str):
            system = self._get(system)
        system.update(changes)
        self._systems[system['uuid']] = system

    @property
    def driver(self):
        return '<fake>'

    @property
    def systems(self):
        return list(self._systems)

    def uuid(self, identity):
        try:
            return self._get(identity)['uuid']
        except error.AliasAccessError as exc:
            return str(exc)

    def name(self, identity):
        try:
            return self._get(identity)['name']
        except error.AliasAccessError:
            return identity

    def get_power_state(self, identity):
        return self._get(identity)['power_state']

    def set_power_state(self, identity, state):
        # hardware actions are not immediate
        apply_time = int(time.time()) + random.randint(1, 11)

        system = self._get(identity)

        if 'On' in state:
            pending_state = 'On'
        elif state in ('ForceOff', 'GracefulShutdown'):
            pending_state = 'Off'
        elif 'Restart' in state:
            system['power_state'] = 'Off'
            pending_state = 'On'
        else:
            raise error.NotSupportedError(
                f'Power state {state} is not supported')

        if system['power_state'] != pending_state:
            self._update(system, pending_power={
                'power_state': pending_state,
                'apply_time': apply_time,
            })

    def get_boot_device(self, identity):
        return self._get(identity).get('boot_device', 'Hdd')

    def set_boot_device(self, identity, boot_source):
        self._update(identity, boot_device=boot_source)

    def get_boot_mode(self, identity):
        return self._get(identity).get('boot_mode', 'UEFI')

    def set_boot_mode(self, identity, boot_mode):
        self._update(identity, boot_mode=boot_mode)

    def get_boot_image(self, identity, device):
        devinfo = self._get(identity).get('boot_image') or {}
        return devinfo.get(device) or (None, False, False)

    def set_boot_image(self, identity, device, boot_image=None,
                       write_protected=True):
        system = self._get(identity)
        devinfo = system.get('boot_image') or {}
        devinfo[device] = (boot_image, write_protected, bool(boot_image))
        self._update(system, boot_image=devinfo)
