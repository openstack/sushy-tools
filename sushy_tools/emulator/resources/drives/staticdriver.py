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

from sushy_tools.emulator.resources.base import DriverBase
from sushy_tools import error


class StaticDriver(DriverBase):
    """Redfish storage drives backed by configuration file"""

    @classmethod
    def initialize(cls, config, logger, *args, **kwargs):
        cls._config = config
        cls._logger = logger

        cls._drives = cls._config.get('SUSHY_EMULATOR_DRIVES', {})

        return cls

    @property
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """
        return '<static-drives>'

    def get_drives(self, identity, storage_id):
        try:
            uu_identity = str(uuid.UUID(identity))

            return self._drives[(uu_identity, storage_id)]

        except (ValueError, KeyError):
            msg = ('Error finding drive for System UUID "%s" and Storage ID '
                   '"%s"', identity, storage_id)

            self._logger.debug(msg)

            raise error.FishyError(msg)

    def get_all_drives(self):
        """Return all drives represented as tuples in the following format:

        (System_UUID, Storage_ID, Drive_ID)

        :returns: list of tuples representing the drives
        """
        return [k + (d['Id'],) for k in self._drives
                for d in self._drives[k]]
