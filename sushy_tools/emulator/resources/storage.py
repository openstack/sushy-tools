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

from sushy_tools.emulator.resources import base
from sushy_tools import error


class StaticDriver(base.DriverBase):
    """Redfish storage backed by configuration file"""

    def __init__(self, config, logger):
        super().__init__(config, logger)
        self._storage = self._config.get('SUSHY_EMULATOR_STORAGE', {})

    @property
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """
        return '<static-storage>'

    def get_storage_col(self, identity):
        try:
            uu_identity = str(uuid.UUID(identity))

            return self._storage[uu_identity]

        except KeyError:
            msg = ('Error finding storage collection by UUID '
                   '"%(identity)s"' % {'identity': identity})

            self._logger.debug(msg)

            raise error.FishyError(msg)

    def get_all_storage(self):
        """Returns all storage instances represented as tuples in the format:

        (System_ID, Storage_ID)

        :returns: list of tuples representing the storage instances
        """
        return [(k, st["Id"]) for k in self._storage
                for st in self._storage[k]]
