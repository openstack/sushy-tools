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

import math

from sushy_tools.emulator import memoize
from sushy_tools.emulator.resources.systems.base import AbstractSystemsDriver
from sushy_tools import error

try:
    import openstack

except ImportError:
    openstack = None


is_loaded = bool(openstack)


class OpenStackDriver(AbstractSystemsDriver):
    """OpenStack driver"""

    NOVA_POWER_STATE_ON = 1

    BOOT_DEVICE_MAP = {
        'Pxe': 'network',
        'Hdd': 'hd',
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

        cls._cc = openstack.connect(cloud=os_cloud)

        return cls

    @memoize.memoize()
    def _get_instance(self, identity):
        instance = self._cc.get_server(identity)
        if instance:
            if identity != instance.id:
                raise error.AliasAccessError(instance.id)

            return instance

        msg = ('Error finding instance by UUID "%(identity)s" at OS '
               'cloud %(os_cloud)s"' % {'identity': identity,
                                        'os_cloud': self._os_cloud})

        self._logger.debug(msg)

        raise error.FishyError(msg)

    @memoize.memoize(permanent_cache=PERMANENT_CACHE)
    def _get_flavor(self, identity):
        instance = self._get_instance(identity)
        return self._cc.get_flavor(instance.flavor.id)

    @memoize.memoize(permanent_cache=PERMANENT_CACHE)
    def _get_image_info(self, identity):
        return self._cc.image.find_image(identity)

    def _get_server_metadata(self, identity):
        return self._cc.compute.get_server_metadata(identity).to_dict()

    def _set_server_metadata(self, identity, metadata):
        self._cc.compute.set_server_metadata(identity, metadata)

    @property
    def driver(self):
        """Return human-friendly driver description

        :returns: driver description as `str`
        """
        return '<OpenStack compute>'

    @property
    def systems(self):
        """Return available computer systems

        :returns: list of UUIDs representing the systems
        """
        return [server.id for server in self._cc.list_servers()]

    def uuid(self, identity):
        """Get computer system UUID by name

        :param identity: OpenStack instance name or ID

        :returns: computer system UUID
        """
        instance = self._get_instance(identity)
        return instance.id

    def name(self, identity):
        """Get computer system name by name

        :param identity: OpenStack instance name or ID

        :returns: computer system name
        """
        instance = self._get_instance(identity)
        return instance.name

    def get_power_state(self, identity):
        """Get computer system power state

        :param identity: OpenStack instance name or ID

        :returns: *On* or *Off*`str` or `None`
            if power state can't be determined
        """
        try:
            instance = self._get_instance(identity)

        except error.FishyError:
            return

        if instance.power_state == self.NOVA_POWER_STATE_ON:
            return 'On'

        return 'Off'

    def set_power_state(self, identity, state):
        """Set computer system power state

        :param identity: OpenStack instance name or ID
        :param state: string literal requesting power state transition.
            Valid values  are: *On*, *ForceOn*, *ForceOff*, *GracefulShutdown*,
            *GracefulRestart*, *ForceRestart*, *Nmi*.

        :raises: `error.FishyError` if power state can't be set

        """
        instance = self._get_instance(identity)

        if state in ('On', 'ForceOn'):
            if instance.power_state != self.NOVA_POWER_STATE_ON:
                self._cc.compute.start_server(instance.id)

        elif state == 'ForceOff':
            if instance.power_state == self.NOVA_POWER_STATE_ON:
                self._cc.compute.stop_server(instance.id)

        elif state == 'GracefulShutdown':
            if instance.power_state == self.NOVA_POWER_STATE_ON:
                self._cc.compute.stop_server(instance.id)

        elif state == 'GracefulRestart':
            if instance.power_state == self.NOVA_POWER_STATE_ON:
                self._cc.compute.reboot_server(
                    instance.id, reboot_type='SOFT'
                )

        elif state == 'ForceRestart':
            if instance.power_state == self.NOVA_POWER_STATE_ON:
                self._cc.compute.reboot_server(
                    instance.id, reboot_type='HARD'
                )

        # NOTE(etingof) can't support `state == "Nmi"` as
        # openstacksdk does not seem to support that
        else:
            raise error.FishyError(
                'Unknown ResetType "%(state)s"' % {'state': state})

    def get_boot_device(self, identity):
        """Get computer system boot device name

        :param identity: OpenStack instance name or ID

        :returns: boot device name as `str` or `None` if device name
            can't be determined. Valid values are: *Pxe*, *Hdd*, *Cd*.
        """
        try:
            instance = self._get_instance(identity)

        except error.FishyError:
            return

        metadata = self._get_server_metadata(instance.id)

        # NOTE(etingof): the following probably only works with
        # libvirt-backed compute nodes

        if metadata.get('libvirt:pxe-first'):
            return self.BOOT_DEVICE_MAP_REV['network']

        else:
            return self.BOOT_DEVICE_MAP_REV['hd']

    def set_boot_device(self, identity, boot_source):
        """Set computer system boot device name

        :param identity: OpenStack instance name or ID
        :param boot_source: string literal requesting boot device
            change on the system. Valid values are: *Pxe*, *Hdd*, *Cd*.

        :raises: `error.FishyError` if boot device can't be set
        """
        instance = self._get_instance(identity)

        try:
            target = self.BOOT_DEVICE_MAP[boot_source]

        except KeyError:
            msg = ('Unknown power state requested: '
                   '%(boot_source)s' % {'boot_source': boot_source})

            raise error.FishyError(msg)

        # NOTE(etingof): the following probably only works with
        # libvirt-backed compute nodes
        self._cc.compute.set_server_metadata(
            instance.id, **{'libvirt:pxe-first': '1'
                            if target == 'network' else ''}
        )

    def get_boot_mode(self, identity):
        """Get computer system boot mode.

        :returns: either *UEFI* or *Legacy* as `str` or `None` if
            current boot mode can't be determined
        """
        instance = self._get_instance(identity)

        image = self._get_image_info(instance.image['id'])

        hw_firmware_type = getattr(image, 'hw_firmware_type', None)

        return self.BOOT_MODE_MAP_REV.get(hw_firmware_type)

    def set_boot_mode(self, identity, boot_mode):
        """Set computer system boot mode.

        :param boot_mode: string literal requesting boot mode
            change on the system. Valid values are: *UEFI*, *Legacy*.

        :raises: `error.FishyError` if boot mode can't be set
        """
        # just to make sure passed identity exists
        self._get_instance(identity)

        msg = ('The cloud driver %(driver)s does not allow changing boot '
               'mode through Redfish' % {'driver': self.driver})

        raise error.FishyError(msg)

    def get_total_memory(self, identity):
        """Get computer system total memory

        :param identity: OpenStack instance name or ID

        :returns: available RAM in GiB as `int` or `None` if total memory
            count can't be determined
        """
        try:
            flavor = self._get_flavor(identity)

        except error.FishyError:
            return

        return int(math.ceil(flavor.ram / 1024.))

    def get_total_cpus(self, identity):
        """Get computer system total count of available CPUs

        :param identity: OpenStack instance name or ID

        :returns: available CPU count as `int` or `None`
            if total memory count can't be determined
        """
        try:
            flavor = self._get_flavor(identity)

        except error.FishyError:
            return

        return flavor.vcpus

    def get_bios(self, identity):
        """Not supported as Openstack SDK does not expose API for BIOS"""
        raise error.FishyError(
            'Operation not supported by the virtualization driver')

    def set_bios(self, identity, attributes):
        """Not supported as Openstack SDK does not expose API for BIOS"""
        raise error.FishyError(
            'Operation not supported by the virtualization driver')

    def reset_bios(self, identity):
        """Not supported as Openstack SDK does not expose API for BIOS"""
        raise error.FishyError(
            'Operation not supported by the virtualization driver')

    def get_nics(self, identity):
        """Get server's network interfaces

        Use MAC address as network interface's id

        :param identity: OpenStack instance name or ID

        :returns: list of dictionaries with NIC attributes (id and mac)
        """
        instance = self._get_instance(identity)
        macs = set()
        if not instance.addresses:
            return macs

        for addresses in instance.addresses.values():
            for adr in addresses:
                try:
                    macs.add(adr['OS-EXT-IPS-MAC:mac_addr'])
                except KeyError:
                    self._logger.warning(
                        'Could not find MAC address in %s', adr)
        return [{'id': mac, 'mac': mac}
                for mac in macs]

    def get_boot_image(self, identity, device):
        """Get backend VM boot image info

        :param identity: node name or ID
        :param device: device type (from
            `sushy_tools.emulator.constants`)
        :returns: a `tuple` of (boot_image, write_protected, inserted)
        :raises: `error.FishyError` if boot device can't be accessed
        """
        raise error.NotSupportedError('Not implemented')

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
        raise error.NotSupportedError('Not implemented')

    def get_simple_storage_collection(self, identity):
        raise error.NotSupportedError('Not implemented')

    def find_or_create_storage_volume(self, data):
        """Find/create volume based on existence in the virtualization backend

        :param data: data about the volume in dict form with values for `Id`,
                     `Name`, `CapacityBytes`, `VolumeType`, `libvirtPoolName`
                     and `libvirtVolName`

        :returns: Id of the volume if successfully found/created else None
        """
        raise error.NotSupportedError('Not implemented')
