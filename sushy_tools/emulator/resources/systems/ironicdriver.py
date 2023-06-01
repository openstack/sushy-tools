# Copyright 2023 Red Hat, Inc.
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

import math

from sushy_tools.emulator import memoize
from sushy_tools.emulator.resources.systems.base import AbstractSystemsDriver
from sushy_tools import error

try:
    import openstack

except ImportError:
    openstack = None


is_loaded = bool(openstack)


class IronicDriver(AbstractSystemsDriver):
    """Ironic driver"""

    IRONIC_POWER_ON = "power on"
    IRONIC_POWER_OFF = "power off"
    IRONIC_POWER_OFF_SOFT = "soft power off"
    IRONIC_POWER_REBOOT = "rebooting"
    IRONIC_POWER_REBOOT_SOFT = "soft rebooting"

    BOOT_DEVICE_MAP = {
        'Pxe': 'pxe',
        'Hdd': 'disk',
        'Cd': 'cdrom',
    }

    BOOT_DEVICE_MAP_REV = {v: k for k, v in BOOT_DEVICE_MAP.items()}

    BOOT_MODE_MAP = {
        'Legacy': 'bios',
        'UEFI': 'uefi',
    }

    BOOT_MODE_MAP_REV = {v: k for k, v in BOOT_MODE_MAP.items()}

    PERMANENT_CACHE = {}

    @classmethod
    def initialize(cls, config, logger, os_cloud, *args, **kwargs):
        cls._config = config
        cls._logger = logger
        cls._os_cloud = os_cloud

        if not hasattr(cls, "_cc"):
            cls._cc = openstack.connect(cloud=cls._os_cloud)

        return cls

    @memoize.memoize()
    def _get_node(self, identity):
        try:
            node = self._cc.baremetal.get_node(identity)
            return node
        except openstack.exceptions.ResourceNotFound:
            pass

        msg = ('Error finding node by UUID "%(identity)s" at ironic '
               'cloud %(os_cloud)s"' % {'identity': identity,
                                        'os_cloud': self._os_cloud})

        self._logger.debug(msg)

        raise error.NotFound(msg)

    @memoize.memoize(permanent_cache=PERMANENT_CACHE)
    def _get_properties(self, identity):
        node = self._get_node(identity)
        return node.properties

    @memoize.memoize(permanent_cache=PERMANENT_CACHE)
    def _get_driver_internal_info(self, identity):
        return self._get_node(identity).driver_internal_info

    @property
    def driver(self):
        """Return human-friendly driver description

        :returns: driver description as `str`
        """
        return '<OpenStack baremetal>'

    @property
    def systems(self):
        """Return available computer systems

        :returns: list of UUIDs representing the systems
        """
        return [node.id for node in self._cc.baremetal.nodes(fields=["uuid"])]

    def uuid(self, identity):
        """Get computer system UUID by name

        :param identity: OpenStack node name or ID

        :returns: computer system UUID
        """
        node = self._get_node(identity)
        return node.id

    def name(self, identity):
        """Get computer system name by name

        :param identity: OpenStack node name or ID

        :returns: computer system name
        """
        node = self._get_node(identity)
        return node.name

    def get_power_state(self, identity):
        """Get computer system power state

        :param identity: OpenStack node name or ID

        :returns: *On* or *Off*`str` or `None`
            if power state can't be determined
        """
        try:
            node = self._get_node(identity)

        except error.FishyError:
            return

        if node.power_state == self.IRONIC_POWER_ON:
            return 'On'

        return 'Off'

    def set_power_state(self, identity, state):
        """Set computer system power state

        :param identity: OpenStack node name or ID
        :param state: string literal requesting power state transition.
            Valid values  are: *On*, *ForceOn*, *ForceOff*, *GracefulShutdown*,
            *GracefulRestart*, *ForceRestart*, *Nmi*.

        :raises: `error.FishyError` if power state can't be set

        """
        node = self._get_node(identity)

        if state in ('On', 'ForceOn'):
            self._cc.baremetal.set_node_power_state(
                node.id, self.IRONIC_POWER_ON)

        elif state == 'ForceOff':
            self._cc.baremetal.set_node_power_state(
                node.id, self.IRONIC_POWER_OFF)

        elif state == 'GracefulShutdown':
            self._cc.baremetal.set_node_power_state(
                node.id, self.IRONIC_POWER_OFF_SOFT)

        elif state == 'GracefulRestart':
            if node.power_state == self.IRONIC_POWER_ON:
                self._cc.baremetal.set_node_power_state(
                    node.id, self.IRONIC_POWER_REBOOT_SOFT)

        elif state == 'ForceRestart':
            if node.power_state == self.IRONIC_POWER_ON:
                self._cc.baremetal.set_node_power_state(
                    node.id, self.IRONIC_POWER_REBOOT)

        # NOTE(etingof) can't support `state == "Nmi"` as
        # openstacksdk does not seem to support that
        else:
            raise error.BadRequest(
                'Unknown ResetType "%(state)s"' % {'state': state})

    def get_boot_device(self, identity):
        """Get computer system boot device name

        :param identity: OpenStack node name or ID

        :returns: boot device name as `str` or `None` if device name
            can't be determined. Valid values are: *Pxe*, *Hdd*, *Cd*.
        """
        try:
            node = self._get_node(identity)

        except error.FishyError:
            return

        bdevice = node.get_boot_device(self._cc.baremetal).get("boot_device")
        return self.BOOT_DEVICE_MAP_REV.get(bdevice)

    def set_boot_device(self, identity, boot_source):
        """Set computer system boot device name

        :param identity: OpenStack node name or ID
        :param boot_source: string literal requesting boot device
            change on the system. Valid values are: *Pxe*, *Hdd*, *Cd*.

        :raises: `error.FishyError` if boot device can't be set
        """

        try:
            target = self.BOOT_DEVICE_MAP[boot_source]

        except KeyError:
            msg = ('Unknown power state requested: '
                   '%(boot_source)s' % {'boot_source': boot_source})

            raise error.BadRequest(msg)

        self._cc.baremetal.set_node_boot_device(identity, target)

    def get_boot_mode(self, identity):
        """Get computer system boot mode.

        :returns: either *UEFI* or *Legacy* as `str` or `None` if
            current boot mode can't be determined
        """

        node = self._get_node(identity)
        return self.BOOT_MODE_MAP_REV.get(node.boot_mode)

    def set_boot_mode(self, identity, boot_mode):
        """Set computer system boot mode.

        :param boot_mode: string literal requesting boot mode
            change on the system. Valid values are: *UEFI*, *Legacy*.

        :raises: `error.FishyError` if boot mode can't be set
        """
        # just to make sure passed identity exists
        self._get_node(identity)
        msg = ('The cloud driver %(driver)s does not allow changing boot '
               'mode through Redfish' % {'driver': self.driver})
        raise error.NotSupportedError(msg)

    def get_secure_boot(self, identity):
        """Get computer system secure boot state for UEFI boot mode.

        :returns: boolean of the current secure boot state

        :raises: `FishyError` if the state can't be fetched
        """
        node = self._get_node(identity)
        return node.is_secure_boot or False

    def set_secure_boot(self, identity, secure):
        """Set computer system secure boot state for UEFI boot mode.

        :param secure: boolean requesting the secure boot state

        :raises: `FishyError` if the can't be set
        """
        msg = ('The cloud driver %(driver)s does not support changing secure '
               'boot mode through Redfish' % {'driver': self.driver})
        raise error.NotSupportedError(msg)

    def get_total_memory(self, identity):
        """Get computer system total memory

        :param identity: OpenStack node name or ID

        :returns: available RAM in GiB as `int`
        """
        try:
            properties = self._get_properties(identity)

        except error.FishyError:
            return

        memory_mb = properties.get("memory_mb")
        if memory_mb is None:
            return None
        return int(math.ceil(int(memory_mb) / 1024))

    def get_total_cpus(self, identity):
        """Get computer system total count of available CPUs

        :param identity: OpenStack node name or ID

        :returns: available CPU count as `int`
        """
        try:
            properties = self._get_properties(identity)

        except error.FishyError:
            return

        cpus = properties.get("cpus")
        if cpus is None:
            return None
        return int(cpus)

    def get_nics(self, identity):
        """Get node's network interfaces

        Use MAC address as network interface's id

        :param identity: OpenStack node name or ID

        :returns: list of dictionaries with NIC attributes (id and mac)
        """

        self._get_node(identity)

        macs = set()
        for port in self._cc.baremetal.ports(fields=["address", "node_uuid"]):
            if port["node_uuid"] == identity:
                macs.add(port["address"])

        return [{'id': mac, 'mac': mac}
                for mac in macs]
