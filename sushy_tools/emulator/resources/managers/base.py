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

import abc

from sushy_tools.emulator import base


class AbstractManagersDriver(base.DriverBase, metaclass=abc.ABCMeta):
    """Base class backing Redfish Managers"""

    @classmethod
    def initialize(cls, config, logger, *args, **kwargs):
        cls._config = config
        cls._logger = logger
        return cls

    @property
    @abc.abstractmethod
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """

    @abc.abstractmethod
    def get_manager(self, identity):
        """Get a manager by its identity

        :returns: Redfish manager object.
        """

    @property
    @abc.abstractmethod
    def managers(self):
        """Return available Redfish managers

        :returns: list of UUIDs representing the managers
        """

    @abc.abstractmethod
    def get_managed_systems(self, manager, systems_driver):
        """Get systems managed by this manager.

        :param manager: Redfish manager object.
        :param systems_driver: A systems driver.
        :returns: List of Redfish system UUIDs.
        """

    @abc.abstractmethod
    def get_managed_chassis(self, manager, chassis_driver):
        """Get chassis managed by this manager.

        :param manager: Redfish manager object.
        :param chassis_driver: A chassis driver.
        :returns: List of Redfish chassis UUIDs.
        """

    @abc.abstractmethod
    def get_managers_for_system(self, ident):
        """Get managers that manage the given system.

        :param ident: System UUID.
        :returns: list of UUIDs representing the managers
        """
