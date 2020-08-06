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

from sushy_tools.emulator.resources import base
from sushy_tools import error


class FakeDriver(base.DriverBase):
    """Redfish manager that copied systems."""

    def __init__(self, config, logger, systems, chassis):
        super().__init__(config, logger)
        self._systems = systems
        self._chassis = chassis

    def get_manager(self, identity):
        """Get a manager by its identity

        :returns: Redfish manager UUID.
        """
        try:
            system_uuid = self._systems.uuid(identity)
            system_name = self._systems.name(identity)
        except error.AliasAccessError:
            raise
        except error.FishyError:
            msg = 'Manager with UUID %s was not found' % identity
            self._logger.error(msg)
            raise error.FishyError(msg)
        else:
            result = {'Id': system_uuid,
                      'UUID': system_uuid,
                      'Name': '%s-Manager' % system_name}
            self._logger.debug('Found manager %(mgr)s by UUID %(id)s',
                               {'mgr': result, 'id': identity})
            return result

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
        return sorted(self._systems.systems)

    def get_managed_systems(self, manager):
        """Get systems managed by this manager.

        :param manager: Redfish manager object.
        :returns: List of Redfish system UUIDs.
        """
        return [manager['UUID']]

    def get_managed_chassis(self, manager):
        """Get chassis managed by this manager.

        :param manager: Redfish manager object.
        :returns: List of Redfish chassis UUIDs.
        """
        if manager['UUID'] == self.managers[0]:
            return self._chassis.chassis
        else:
            return []

    def get_managers_for_system(self, ident):
        """Get managers that manage the given system.

        :param ident: System UUID.
        :returns: list of UUIDs representing the managers
        """
        return [self._systems.uuid(ident)]
