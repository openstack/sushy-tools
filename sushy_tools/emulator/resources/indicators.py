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

from sushy_tools.emulator import memoize
from sushy_tools.emulator.resources import base
from sushy_tools import error


class StaticDriver(base.DriverBase):
    """Redfish indicator LED simulator

    Maintain indicators states in memory. Does not light up
    anything.
    """

    def __init__(self, config, logger):
        super().__init__(config, logger)
        self._indicators = memoize.PersistentDict()
        if hasattr(self._indicators, 'make_permanent'):
            self._indicators.make_permanent(
                self._config.get('SUSHY_EMULATOR_STATE_DIR'), 'indicators')
        self._indicators.update(
            self._config.get('SUSHY_EMULATOR_INDICATOR_LEDS', {}))

    @property
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """
        return '<static-indicators>'

    @property
    def indicators(self):
        """Return available Redfish indicators

        :returns: list of UUIDs representing the indicators
        """
        return list(self._indicators)

    def get_indicator_state(self, identity):
        """Get indicator state

        :param identity: indicator identity

        :returns: indicator state as one of *Lit*, *Blinking*,
                *Off*
        """
        if identity not in self._indicators:
            self._indicators[identity] = 'Lit'

        return self._indicators[identity]

    def set_indicator_state(self, identity, state):
        """Set indicator state

        :param identity: indicator identity
        :param state: indicator state as one of *Lit*, *Blinking*, *Off*

        :raises: `error.FishyError` if desired state can't be set
        """
        if state not in ('Lit', 'Off', 'Blinking'):
            raise error.FishyError(
                'Unknown indicator state %s, ID %s' % (state, identity))

        self._indicators[identity] = state
