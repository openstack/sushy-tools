#!/usr/bin/env python
#
# Copyright 2017 Red Hat, Inc.
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
class AbstractCloudDriver(object):
    """Base class for all cloud drivers"""

    @abc.abstractproperty
    def domains(self):
        """Return available domains

        :returns: list of domain names.
        """

    @abc.abstractmethod
    def uuid(self, identity):
        """Get domain UUID

        :returns: domain UUID
        """

    @abc.abstractmethod
    def power_state(self, domain, state=None):
        """Get/Set domain power state

        :returns: `True` if power is UP and `False` otherwise
        """

    @abc.abstractmethod
    def boot_device(self, domain, boot_source=None):
        """Get/Set domain boot device name

        :returns: boot device name as `str`
        """

    @abc.abstractmethod
    def boot_mode(self, domain, boot_source=None):
        """Get/Set domain boot mode - BIOS vs UEFI

        :returns: boot mode
        """

    @abc.abstractmethod
    def total_memory(self, domain):
        """Get domain total memory

        :returns: available RAM in GB as `int`
        """

    @abc.abstractmethod
    def total_cpus(self, domain):
        """Get domain total count of available CPUs

        :returns: available CPU count as `int`
        """
