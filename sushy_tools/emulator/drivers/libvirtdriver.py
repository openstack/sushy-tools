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

import xml.etree.ElementTree as ET

from sushy_tools.emulator.drivers.base import AbstractDriver
from sushy_tools.error import FishyError

import libvirt


class libvirt_open(object):

    def __init__(self, uri, readonly=False):
        self._uri = uri
        self._readonly = readonly

    def __enter__(self):
        try:
            self._conn = (libvirt.openReadOnly(self._uri)
                          if self._readonly else
                          libvirt.open(self._uri))

            return self._conn

        except libvirt.libvirtError as e:
            msg = ('Error when connecting to the libvirt URI "%(uri)s": '
                   '%(error)s' % {'uri': self._uri, 'error': e})
            raise FishyError(msg)

    def __exit__(self, type, value, traceback):
        self._conn.close()


class LibvirtDriver(AbstractDriver):
    """Libvirt driver"""

    BOOT_DEVICE_MAP = {
        'Pxe': 'network',
        'Hdd': 'hd',
        'Cd': 'cdrom',
    }

    BOOT_DEVICE_MAP_REV = {v: k for k, v in BOOT_DEVICE_MAP.items()}

    LIBVIRT_URI = 'qemu:///system'

    def __init__(self, uri=None):
        self._uri = uri or self.LIBVIRT_URI

    @property
    def driver(self):
        """Return human-friendly driver information

        :returns: driver information as string
        """
        return '<libvirt>'

    @property
    def systems(self):
        """Return available computer systems

        :returns: list of computer systems names.
        """
        with libvirt_open(self._uri, readonly=True) as conn:
            return conn.listDefinedDomains()

    def uuid(self, identity):
        """Get computer system UUID

        The universal unique identifier (UUID) for this system. Can be used
        in place of system name if there are duplicates.

        :returns: computer system UUID
        """
        with libvirt_open(self._uri, readonly=True) as conn:
            domain = conn.lookupByName(identity)
            return domain.UUIDString()

    def get_power_state(self, identity):
        """Get computer system power state

        :returns: current power state as *On* or *Off* `str` or `None`
            if power state can't be determined
        """
        with libvirt_open(self._uri, readonly=True) as conn:

            domain = conn.lookupByName(identity)
            return 'On' if domain.isActive() else 'Off'

    def set_power_state(self, identity, state):
        """Set computer system power state

        :param state: string literal requesting power state transition.
            If not specified, current system power state is returned.
            Valid values  are: *On*, *ForceOn*, *ForceOff*, *GracefulShutdown*,
            *GracefulRestart*, *ForceRestart*, *Nmi*.

        :raises: `FishyError` if power state can't be set
        """
        with libvirt_open(self._uri) as conn:

            domain = conn.lookupByName(identity)

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
                       '%(error)s' % {'uri': self._uri, 'error': e})

                raise FishyError(msg)

    def get_boot_device(self, identity):
        """Get computer system boot device name

        :returns: boot device name as `str` or `None` if device name
            can't be determined
        """
        with libvirt_open(self._uri, readonly=True) as conn:

            domain = conn.lookupByName(identity)

            tree = ET.fromstring(domain.XMLDesc())

            boot_element = tree.find('.//boot')
            if boot_element is not None:
                boot_source_target = (
                    self.BOOT_DEVICE_MAP_REV.get(boot_element.get('dev'))
                )

                return boot_source_target

    def set_boot_device(self, identity, boot_source):
        """Get/Set computer system boot device name

        :param boot_source: optional string literal requesting boot device
            change on the system. If not specified, current boot device is
            returned. Valid values are: *Pxe*, *Hdd*, *Cd*.

        :raises: `FishyError` if boot device can't be set
        """
        with libvirt_open(self._uri) as conn:

            domain = conn.lookupByName(identity)

            tree = ET.fromstring(domain.XMLDesc())

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

            try:
                conn.defineXML(ET.tostring(tree).decode('utf-8'))

            except libvirt.libvirtError as e:
                msg = ('Error changing boot device at libvirt URI "%(uri)s": '
                       '%(error)s' % {'uri': self._uri, 'error': e})

                raise FishyError(msg)

    def get_total_memory(self, identity):
        """Get computer system total memory

        :returns: available RAM in GiB as `int` or `None` if total memory
            count can't be determined
        """
        with libvirt_open(self._uri, readonly=True) as conn:
            domain = conn.lookupByName(identity)
            return int(domain.maxMemory() / 1024 / 1024)

    def get_total_cpus(self, identity):
        """Get computer system total count of available CPUs

        :returns: available CPU count as `int` or `None` if CPU count
            can't be determined
        """
        with libvirt_open(self._uri, readonly=True) as conn:

            domain = conn.lookupByName(identity)

            tree = ET.fromstring(domain.XMLDesc())

            total_cpus = 0

            if domain.isActive():
                total_cpus = domain.maxVcpus()

            # If we can't get it from maxVcpus() try to find it by
            # inspecting the domain XML
            if total_cpus <= 0:
                vcpu_element = tree.find('.//vcpu')
                if vcpu_element is not None:
                    total_cpus = int(vcpu_element.text)

            return total_cpus or None
