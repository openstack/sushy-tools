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

from sushy_tools.emulator import base
from sushy_tools import error


class StaticDriver(base.DriverBase):
    """Redfish chassis backed by configuration file"""

    def __init__(self, config, logger):
        super().__init__(config, logger)

        chassis = self._config.get('SUSHY_EMULATOR_CHASSIS')
        if not chassis:
            # Default chassis
            chassis = [
                {
                    u'Id': u'SheetMetalChassis',
                    u'Name': u'Chassis',
                    u'UUID': u'15693887-7984-9484-3272-842188918912',
                }
            ]

        self._chassis_by_id = {
            x['Id']: x for x in chassis
        }
        self._chassis_by_uuid = {
            x['UUID']: x for x in chassis if 'UUID' in x
        }
        self._chassis_by_name = {
            x['Name']: x for x in chassis if 'Name' in x
        }

        if len(self._chassis_by_uuid) != len(chassis):
            raise error.FishyError(
                'Conflicting UUIDs in static chassis configuration')

    def _get_chassis(self, identity):
        try:
            uu_identity = str(uuid.UUID(identity))

            return self._chassis_by_uuid[uu_identity]

        except (ValueError, KeyError):
            try:
                uu_identity = self._chassis_by_name[identity]['UUID']

            except KeyError:

                try:
                    uu_identity = self._chassis_by_id[identity]['UUID']

                except KeyError:
                    msg = ('Error finding chassis by UUID/Name/Id '
                           '"%(identity)s"' % {'identity': identity})

                    self._logger.debug(msg)

                    raise error.FishyError(msg)

        raise error.AliasAccessError(uu_identity)

    @property
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """
        return '<static-chassis>'

    @property
    def chassis(self):
        """Return available Redfish chassis

        :returns: list of UUIDs representing the chassis
        """
        return sorted(self._chassis_by_uuid)

    def uuid(self, identity):
        """Get Redfish chassis UUID

        The universal unique identifier (UUID) for this system. Can be used
        in place of chassis name if there are duplicates.

        If driver backend does not support non-unique chassis identity,
        this method may just return the `identity`.

        :returns: Redfish chassis UUID
        """
        chassis = self._get_chassis(identity)
        return chassis.get('UUID')

    def name(self, identity):
        """Get Redfish chassis name by UUID

        The universal unique identifier (UUID) for this Redfish chassis.
        Can be used in place of chassis name if there are duplicates.

        If driver backend does not support chassis names, this method may
        just return the `identity`.

        :returns: Redfish chassis name
        """
        chassis = self._get_chassis(identity)
        return chassis.get('Name')
