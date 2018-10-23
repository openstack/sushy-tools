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
import six


@six.add_metaclass(abc.ABCMeta)
class AbstractDriver(object):
    """Base class for all virtualization drivers"""

    @classmethod
    def initialize(cls, **kwargs):
        """Initialize class attributes

        Since drivers may need to cache thing short-term. The emulator
        instantiates the driver every time it serves a client query.

        Driver objects can cache whenever it makes sense for the duration
        of a single session. It is guaranteed that the driver object will
        never be reused for any other session.

        The `initialize` method is provided to set up the driver in a way
        that would affect all the subsequent sessions.

        :params **kwargs: driver-specific parameters
        :returns: initialized driver class
        """
        return cls

    @abc.abstractproperty
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as `str`
        """

    @abc.abstractproperty
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
            If not specified, current system power state is returned.
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
            system. If not specified, current boot device is returned.
            Valid values are: *Pxe*, *Hdd*, *Cd*.

        :raises: `FishyError` if boot device can't be set
        """

    def get_boot_mode(self, identity):
        """Get computer system boot mode.

        :returns: either *Uefi* or *Legacy* as `str` or `None` if
            current boot mode can't be determined
        """

    def set_boot_mode(self, identity, boot_mode):
        """Set computer system boot mode.

        :param boot_mode: optional string literal requesting boot mode
            change on the system. If not specified, current boot mode is
            returned. Valid values are: *Uefi*, *Legacy*.

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
