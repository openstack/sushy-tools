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

import xml.etree.ElementTree as ET

from sushy_tools.emulator.clouds.base import AbstractCloudDriver
from sushy_tools.error import FishyError

import libvirt


class LibvirtCloudDriver(AbstractCloudDriver):
    """Libvirt cloud driver"""

    BOOT_DEVICE_MAP = {
        'Pxe': 'network',
        'Hdd': 'hd',
        'Cd': 'cdrom',
    }

    BOOT_DEVICE_MAP_REV = {v: k for k, v in BOOT_DEVICE_MAP.items()}

    def __init__(self, uri, readonly=False):

        try:
            self._conn = (libvirt.openReadOnly(uri)
                          if readonly else libvirt.open(uri))

        except libvirt.libvirtError as e:
            msg = ('Error when connecting to the libvirt URI "%(uri)s": '
                   '%(error)s' % {'uri': self.uri, 'error': e})

            raise FishyError(msg)

    @property
    def domains(self):
        """Return available domains

        :returns: list of domain names.
        """
        return self._conn.listDefinedDomains()

    def uuid(self, identity):
        """Get domain UUID

        :returns: domain UUID
        """
        domain = self._conn.lookupByName(identity)

        return domain.UUIDString()

    def power_state(self, identity, state=None):
        """Get/Set domain power state

        :returns: `True` if power is UP and `False` otherwise
        """
        domain = self._conn.lookupByName(identity)

        if not state:
            return 'On' if domain.isActive() else 'Off'

        try:
            if state in ('On', 'ForceOn'):
                if not domain.isActive():
                    domain.create()
            elif state == 'ForceOff':
                if domain.isActive():
                    domain.destroy()
            elif state == 'GracefulShutdown':
                if domain.isActive():
                    domain.shutdown()
            elif state == 'GracefulRestart':
                if domain.isActive():
                    domain.reboot()
            elif state == 'ForceRestart':
                if domain.isActive():
                    domain.reset()
            elif state == 'Nmi':
                if domain.isActive():
                    domain.injectNMI()

        except libvirt.libvirtError as e:
            msg = ('Error changing power state at libvirt URI "%(uri)s": '
                   '%(error)s' % {'uri': self.uri, 'error': e})

            raise FishyError(msg)

        return ''

    def boot_device(self, identity, boot_source=None):
        """Get/Set domain boot device name

        :returns: boot device name as `str`
        """
        domain = self._conn.lookupByName(identity)

        tree = ET.fromstring(domain.XMLDesc())

        if boot_source:
            try:
                target = self.BOOT_DEVICE_MAP[boot_source]

            except KeyError:
                msg = ('Unknown power state requested: '
                       '%(boot_source)s' % {'boot_source': boot_source})

                raise FishyError(msg)

            for os_element in tree.findall('os'):
                # Remove all "boot" elements
                for boot_element in os_element.findall('boot'):
                    os_element.remove(boot_element)

                # Add a new boot element with the request boot device
                boot_element = ET.SubElement(os_element, 'boot')
                boot_element.set('dev', target)

            self._conn.defineXML(ET.tostring(tree).decode('utf-8'))

        else:
            boot_source_target = None
            boot_element = tree.find('.//boot')
            if boot_element is not None:
                boot_source_target = (
                    self.BOOT_DEVICE_MAP_REV.get(boot_element.get('dev'))
                )

            return boot_source_target

    def boot_mode(self, identity, boot_source=None):
        """Get/Set domain boot mode - BIOS vs UEFI

        :returns: boot mode
        """

    def total_memory(self, identity):
        """Get domain total memory

        :returns: available RAM in GB as `int`
        """
        domain = self._conn.lookupByName(identity)

        return int(domain.maxMemory() / 1024 / 1024)

    def total_cpus(self, identity):
        """Get domain total count of available CPUs

        :returns: available CPU count as `int`
        """
        domain = self._conn.lookupByName(identity)

        tree = ET.fromstring(domain.XMLDesc())

        total_cpus = 0

        if domain.isActive():
            total_cpus = domain.maxVcpus()

        else:
            # If we can't get it from maxVcpus() try to find it by
            # inspecting the domain XML
            if total_cpus <= 0:
                vcpu_element = tree.find('.//vcpu')
                if vcpu_element is not None:
                    total_cpus = int(vcpu_element.text)

        return total_cpus
