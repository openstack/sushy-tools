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

import logging
import math

from sushy_tools.emulator.drivers.base import AbstractDriver
from sushy_tools.error import FishyError

import openstack


logger = logging.getLogger(__name__)


class OpenStackDriver(AbstractDriver):
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
        'Uefi': 'uefi',
    }

    BOOT_MODE_MAP_REV = {v: k for k, v in BOOT_MODE_MAP.items()}

    def __init__(self, os_cloud, readonly=False):
        self._cc = openstack.connect(cloud=os_cloud)
        self._os_cloud = os_cloud

    def _get_instance(self, identity):
        server = self._cc.get_server(identity)
        if server:
            return server

        msg = ('Error finding instance by UUID "%(identity)s" at OS '
               'cloud %(os_cloud)s"' % {'identity': identity,
                                        'os_cloud': self._os_cloud})
        raise FishyError(msg)

    def _get_flavor(self, identity):
        instance = self._get_instance(identity)
        flavor = self._cc.get_flavor(instance.flavor.id)
        return flavor

    @property
    def driver(self):
        """Return human-friendly driver description

        :returns: driver description as `str`
        """
        return '<OpenStack compute>'

    @property
    def systems(self):
        """Return available computer systems

        :returns: list of computer systems names.
        """
        return [server.id for server in self._cc.list_servers()]

    def uuid(self, identity):
        """Get computer system UUID by name

        :returns: computer system UUID
        """
        instance = self._get_instance(identity)
        return instance.id

    def get_power_state(self, identity):
        """Get computer system power state

        :returns: *On* or *Off*`str` or `None`
            if power state can't be determined
        """
        instance = self._get_instance(identity)

        if instance.power_state == self.NOVA_POWER_STATE_ON:
            return 'On'

        return 'Off'

    def set_power_state(self, identity, state):
        """Set computer system power state

        :param state: optional string literal requesting power state
            transition If not specified, current system power state is
            returned. Valid values  are: *On*, *ForceOn*, *ForceOff*,
            *GracefulShutdown*, *GracefulRestart*, *ForceRestart*, *Nmi*.

        :raises: `FishyError` if power state can't be set

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
            raise FishyError('Unknown ResetType '
                             '"%(state)s"' % {'state': state})

    def get_boot_device(self, identity):
        """Get computer system boot device name

        :param boot_source: optional string literal requesting boot device
            change on the system. If not specified, current boot device is
            returned. Valid values are: *Pxe*, *Hdd*, *Cd*.

        :returns: boot device name as `str` or `None` if device name
            can't be determined
        """
        instance = self._get_instance(identity)

        metadata = self._cc.compute.get_server_metadata(instance.id).to_dict()

        # NOTE(etingof): the following probably only works with
        # libvirt-backed compute nodes

        if metadata.get('libvirt:pxe-first'):
            return self.BOOT_DEVICE_MAP_REV['network']

        else:
            return self.BOOT_DEVICE_MAP_REV['hd']

    def set_boot_device(self, identity, boot_source):
        """Set computer system boot device name

        :param boot_source: optional string literal requesting boot device
            change on the system. If not specified, current boot device is
            returned. Valid values are: *Pxe*, *Hdd*, *Cd*.

        :raises: `FishyError` if boot device can't be set
        """
        instance = self._get_instance(identity)

        try:
            target = self.BOOT_DEVICE_MAP[boot_source]

        except KeyError:
            msg = ('Unknown power state requested: '
                   '%(boot_source)s' % {'boot_source': boot_source})

            raise FishyError(msg)

        # NOTE(etingof): the following probably only works with
        # libvirt-backed compute nodes

        self._cc.compute.set_server_metadata(
            instance.id, {'libvirt:pxe-first': '1'
                          if target == 'network' else ''}
        )

    def get_boot_mode(self, identity):
        """Get computer system boot mode.

        :returns: either *Uefi* or *Legacy* as `str` or `None` if
            current boot mode can't be determined
        """
        instance = self._get_instance(identity)

        image = self._nc.glance.find_image(instance.image['id'])

        hw_firmware_type = getattr(image, 'hw_firmware_type', None)

        return self.BOOT_MODE_MAP_REV.get(hw_firmware_type)

    def set_boot_mode(self, identity, boot_mode):
        """Set computer system boot mode.

        :param boot_mode: optional string literal requesting boot mode
            change on the system. If not specified, current boot mode is
            returned. Valid values are: *Uefi*, *Legacy*.

        :raises: `FishyError` if boot mode can't be set
        """
        # just to make sure passed identity exists
        self._get_instance(identity)

        msg = ('The cloud driver %(driver)s does not allow changing boot '
               'mode through Redfish' % {'driver': self.driver})

        raise FishyError(msg)

    def get_total_memory(self, identity):
        """Get computer system total memory

        :returns: available RAM in GiB as `int` or `None` if total memory
            count can't be determined
        """
        flavor = self._get_flavor(identity)

        return int(math.ceil(flavor.ram // 1024))

    def get_total_cpus(self, identity):
        """Get computer system total count of available CPUs

        :returns: available CPU count as `int` or `None`
            if total memory count can't be determined
        """
        flavor = self._get_flavor(identity)

        return flavor.vcpus
