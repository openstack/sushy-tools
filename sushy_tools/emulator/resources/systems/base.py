# Copyright 2018 Red Hat, Inc.
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


class AbstractSystemsDriver(metaclass=abc.ABCMeta):
    """Base class for all virtualization drivers"""

    @classmethod
    def initialize(cls, config, logger, *args, **kwargs):
        """Initialize class attribute."""
        cls._config = config
        cls._logger = logger

    @property
    @abc.abstractmethod
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """

    @property
    @abc.abstractmethod
    def systems(self):
        """Return available computer systems

        :returns: list of UUIDs representing the systems
        """

    @abc.abstractmethod
    def uuid(self, identity):
        """Get computer system UUID

        The universal unique identifier (UUID) for this system. Can be used
        in place of system name if there are duplicates.

        If virtualization backend does not support non-unique system identity,
        this method may just return the `identity`.

        :returns: computer system UUID
        """

    @abc.abstractmethod
    def name(self, identity):
        """Get computer system name by UUID

        The universal unique identifier (UUID) for this system. Can be used
        in place of system name if there are duplicates.

        If virtualization backend does not support system names
        this method may just return the `identity`.

        :returns: computer system name
        """

    @abc.abstractmethod
    def get_power_state(self, identity):
        """Get computer system power state

        :returns: current power state as *On* or *Off* `str` or `None`
            if power state can't be determined
        """

    @abc.abstractmethod
    def set_power_state(self, identity, state):
        """Set computer system power state

        :param state: string literal requesting power state transition.
            Valid values  are: *On*, *ForceOn*, *ForceOff*, *GracefulShutdown*,
            *GracefulRestart*, *ForceRestart*, *Nmi*.

        :raises: `FishyError` if power state can't be set
        """

    @abc.abstractmethod
    def get_boot_device(self, identity):
        """Get computer system boot device name

        :returns: boot device name as `str` or `None` if device name
            can't be determined
        """

    @abc.abstractmethod
    def set_boot_device(self, identity, boot_source):
        """Set computer system boot device name

        :param boot_source: string literal requesting boot device change on the
            system. Valid values are: *Pxe*, *Hdd*, *Cd*.

        :raises: `FishyError` if boot device can't be set
        """

    def get_boot_mode(self, identity):
        """Get computer system boot mode.

        :returns: either *UEFI* or *Legacy* as `str` or `None` if
            current boot mode can't be determined
        """

    def set_boot_mode(self, identity, boot_mode):
        """Set computer system boot mode.

        :param boot_mode: string literal requesting boot mode
            change on the system. Valid values are: *UEFI*, *Legacy*.

        :raises: `FishyError` if boot mode can't be set
        """

    @abc.abstractmethod
    def get_total_memory(self, identity):
        """Get computer system total memory

        :returns: available RAM in GiB as `int` or `None` if total memory
            count can't be determined
        """

    @abc.abstractmethod
    def get_total_cpus(self, identity):
        """Get computer system total count of available CPUs

        :returns: available CPU count as `int` or `None` if CPU count
            can't be determined
        """

    @abc.abstractmethod
    def get_bios(self, identity):
        """Get BIOS attributes for the system

        :returns: key-value pairs of BIOS attributes

        :raises: `FishyError` if BIOS attributes cannot be processed
        """

    @abc.abstractmethod
    def set_bios(self, identity, attributes):
        """Update BIOS attributes

        :param attributes: key-value pairs of attributes to update

        :raises: `FishyError` if BIOS attributes cannot be processed
        """

    @abc.abstractmethod
    def reset_bios(self, identity):
        """Reset BIOS attributes to default

        :raises: `FishyError` if BIOS attributes cannot be processed
        """

    @abc.abstractmethod
    def get_nics(self, identity):
        """Get list of NICs and their attributes

        :returns: list of dictionaries of NICs and their attributes
        """

    @abc.abstractmethod
    def get_boot_image(self, identity, device):
        """Get backend VM boot image info

        :param identity: node name or ID
        :param device: device type (from
            `sushy_tools.emulator.constants`)
        :returns: a `tuple` of (boot_image, write_protected, inserted)
        :raises: `error.FishyError` if boot device can't be accessed
        """

    @abc.abstractmethod
    def set_boot_image(self, identity, device, boot_image=None,
                       write_protected=True):
        """Set backend VM boot image

        :param identity: node name or ID
        :param device: device type (from
            `sushy_tools.emulator.constants`)
        :param boot_image: path to the image file or `None` to remove
            configured image entirely
        :param write_protected: expose media as read-only or writable

        :raises: `error.FishyError` if boot device can't be set
        """

    @abc.abstractmethod
    def get_simple_storage_collection(self, identity):
        """Get a dict of Simple Storage Controllers and their devices

        :returns: dict of Simple Storage Controllers and their atributes
        """

    def find_or_create_storage_volume(self, data):
        """Find/create volume based on existence in the virtualization backend

        :param data: data about the volume in dict form with values for `Id`,
                     `Name`, `CapacityBytes`, `VolumeType`, `libvirtPoolName`
                     and `libvirtVolName`

        :returns: Id of the volume if successfully found/created else None
        """
