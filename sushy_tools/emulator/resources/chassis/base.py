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


class AbstractChassisDriver(base.DriverBase, metaclass=abc.ABCMeta):
    """Base class backing Redfish Chassis"""

    @classmethod
    def initialize(cls, config, logger, *args, **kwargs):
        cls._config = config
        cls._logger = logger
        return cls

    @abc.abstractproperty
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """

    @abc.abstractproperty
    def chassis(self):
        """Return available Redfish chassis

        :returns: list of UUIDs representing the chassis
        """

    @abc.abstractmethod
    def uuid(self, identity):
        """Get Redfish chassis UUID

        The universal unique identifier (UUID) for this chassis. Can be used
        in place of chassis name if there are duplicates.

        If driver backend does not support non-unique chassis identity,
        this method may just return the `identity`.

        :returns: Redfish chassis UUID
        """

    @abc.abstractmethod
    def name(self, identity):
        """Get Redfish chassis name by UUID

        The universal unique identifier (UUID) for this Redfish chassis.
        Can be used in place of chassis name if there are duplicates.

        If driver backend does not support chassis names, this method may
        just return the `identity`.

        :returns: Redfish chassis name
        """
