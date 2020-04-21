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

import uuid

from sushy_tools.emulator import memoize
from sushy_tools.emulator.resources.base import DriverBase


class StaticDriver(DriverBase):
    """Redfish Volumes emulated in libvirt backed by the config file

    Maintains the libvirt volumes in memory.
    """
    @classmethod
    def initialize(cls, config, logger, *args, **kwargs):
        cls._config = config
        cls._logger = logger

        cls._volumes = memoize.PersistentDict()

        if hasattr(cls._volumes, 'make_permanent'):
            cls._volumes.make_permanent(
                cls._config.get('SUSHY_EMULATOR_STATE_DIR'), 'volumes')

        cls._volumes.update(
            cls._config.get('SUSHY_EMULATOR_VOLUMES', {}))

        return cls

    @property
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """
        return '<static-volumes>'

    def get_volumes_col(self, identity, storage_id):
        try:
            uu_identity = str(uuid.UUID(identity))

            return self._volumes[(uu_identity, storage_id)]

        except (KeyError, ValueError):
            msg = ('Error finding volume collection by System UUID %s '
                   'and Storage ID %s' % (uu_identity, storage_id))
            self._logger.debug(msg)

    def add_volume(self, uu_identity, storage_id, vol):
        if not self._volumes[(uu_identity, storage_id)]:
            self._volumes[(uu_identity, storage_id)] = []

        vol_col = self._volumes[(uu_identity, storage_id)]
        vol_col.append(vol)
        self._volumes.update({(uu_identity, storage_id): vol_col})

    def delete_volume(self, uu_identity, storage_id, vol):
        try:
            vol_col = self._volumes[(uu_identity, storage_id)]
        except KeyError:
            msg = ('Error finding volume collection by System UUID %s '
                   'and Storage ID %s' % (uu_identity, storage_id))
            self._logger.debug(msg)
        else:
            vol_col.remove(vol)
            self._volumes.update({(uu_identity, storage_id): vol_col})
