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

from sushy_tools.emulator.resources.managers.base import AbstractManagersDriver
from sushy_tools import error


class StaticDriver(AbstractManagersDriver):
    """Redfish manager backed by configuration file"""

    def __init__(self):

        managers = self._config.get('SUSHY_EMULATOR_MANAGERS')
        if not managers:
            # Default Manager
            managers = [
                {
                    u'Id': u'BMC',
                    u'Name': u'Manager',
                    u'ServiceEntryPointUUID': u'92384634-2938-2342-'
                                              u'8820-489239905423',
                    u'UUID': u'58893887-8974-2487-2389-841168418919',
                }
            ]

        self._managers_by_id = {
            x['Id']: x for x in managers
        }
        self._managers_by_uuid = {
            x['UUID']: x for x in managers if 'UUID' in x
        }
        self._managers_by_name = {
            x['Name']: x for x in managers if 'Name' in x
        }

        if len(self._managers_by_uuid) != len(managers):
            raise error.FishyError(
                'Conflicting UUIDs in static managers configuration')

    def _get_manager(self, identity):
        try:
            uu_identity = str(uuid.UUID(identity))

            return self._managers_by_uuid[uu_identity]

        except (ValueError, KeyError):

            try:
                uu_identity = self._managers_by_name[identity]['UUID']

            except KeyError:

                try:
                    uu_identity = self._managers_by_id[identity]['UUID']

                except KeyError:
                    msg = ('Error finding manager by UUID/Name/Id '
                           '"%(identity)s"' % {'identity': identity})

                    self._logger.debug(msg)

                    raise error.FishyError(msg)

        raise error.AliasAccessError(uu_identity)

    @property
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """
        return '<static-managers>'

    @property
    def managers(self):
        """Return available Redfish managers

        :returns: list of UUIDs representing the managers
        """
        return sorted(self._managers_by_uuid)

    def uuid(self, identity):
        """Get Redfish manager UUID

        The universal unique identifier (UUID) for this system. Can be used
        in place of manager name if there are duplicates.

        If driver backend does not support non-unique manager identity,
        this method may just return the `identity`.

        :returns: Redfish manager UUID
        """
        manager = self._get_manager(identity)
        return manager.get('UUID')

    def name(self, identity):
        """Get Redfish manager name by UUID

        The universal unique identifier (UUID) for this Redfish manager.
        Can be used in place of manager name if there are duplicates.

        If driver backend does not support manager names, this method may
        just return the `identity`.

        :returns: Redfish manager name
        """
        manager = self._get_manager(identity)
        return manager.get('Name')
