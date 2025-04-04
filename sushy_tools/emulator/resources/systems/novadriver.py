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

import base64
from concurrent import futures
import math
import os
import time
from urllib import parse as urlparse

from sushy_tools.emulator import memoize
from sushy_tools.emulator.resources.systems.base import AbstractSystemsDriver
from sushy_tools import error

try:
    import openstack

except ImportError:
    openstack = None


is_loaded = bool(openstack)

FUTURES = {}


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
        cls._executor = futures.ThreadPoolExecutor(max_workers=4)

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

        raise error.NotFound(msg)

    @memoize.memoize(permanent_cache=PERMANENT_CACHE)
    def _get_flavor(self, identity):
        instance = self._get_instance(identity)
        return self._cc.get_flavor(instance.flavor.original_name)

    @memoize.memoize(permanent_cache=PERMANENT_CACHE)
    def _get_image_info(self, identity):
        if not identity:
            return
        return self._cc.image.find_image(identity)

    @memoize.memoize(permanent_cache=PERMANENT_CACHE)
    def _get_volume_info(self, identity):
        if not identity:
            return
        return self._cc.volume.get_volume(identity)

    def _get_instance_image_id(self, instance):
        # instance.image.id is always None for boot from volume instance
        image_id = instance.image.get('id')

        if image_id is None and len(instance.attached_volumes) > 0:
            vol = self._get_volume_info(instance.attached_volumes[0].id)
            image_id = vol.volume_image_metadata.get('image_id')

        return image_id

    def _get_server_metadata(self, identity):
        return self._cc.compute.get_server_metadata(identity).to_dict()

    def _set_server_metadata(self, identity, metadata):
        self._cc.compute.set_server_metadata(identity, metadata)

    @property
    def _futures(self):
        return FUTURES

    @property
    def connection(self):
        """Return openstack connection

        :returns: Connection object
        """
        return self._cc

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
        delayed_media_eject = instance.metadata.get('sushy-tools-delay-eject')

        if delayed_media_eject:
            self._logger.debug(
                'Create task to rebuild with blank-image for %(identity)s' %
                {'identity': identity})
            # Not running async here, as long as the blank image used is small
            # this should finish in ~20 seconds.
            self._submit_future(
                False, self._rebuild_with_blank_image, identity)
            self._remove_delayed_eject_metadata(identity)

        if instance.task_state is not None:
            # SYS518 is used here to trick openstack/sushy to do retries.
            # iDRAC uses SYS518 when a previous task is still running.
            msg = ('SYS518: Cloud instance is busy, task_state: %s'
                   % instance.task_state)
            raise error.FishyError(msg, 503)

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
            raise error.BadRequest(
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

            raise error.BadRequest(msg)

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

        hw_firmware_type = None
        if instance.image.get('id') is not None:
            image = self._get_image_info(instance.image['id'])
            hw_firmware_type = getattr(image, 'hw_firmware_type', None)
        elif len(instance.attached_volumes) > 0:
            vol = self._get_volume_info(instance.attached_volumes[0].id)
            hw_firmware_type = vol.volume_image_metadata.get(
                'hw_firmware_type')

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

        raise error.NotSupportedError(msg)

    def get_secure_boot(self, identity):
        """Get computer system secure boot state for UEFI boot mode.

        :returns: boolean of the current secure boot state

        :raises: `FishyError` if the state can't be fetched
        """
        if self.get_boot_mode(identity) == 'Legacy':
            msg = 'Legacy boot mode does not support secure boot'
            raise error.NotSupportedError(msg)

        instance = self._get_instance(identity)

        os_secure_boot = None
        if instance.image.get('id') is not None:
            image = self._get_image_info(instance.image['id'])
            os_secure_boot = getattr(image, 'os_secure_boot', None)
        elif len(instance.attached_volumes) > 0:
            vol = self._get_volume_info(instance.attached_volumes[0].id)
            os_secure_boot = vol.volume_image_metadata.get('os_secure_boot')

        return os_secure_boot == 'required'

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
        instance = self._get_instance(identity)
        image_id = self._get_instance_image_id(instance)

        return image_id, False, True

    def set_boot_image(self, identity, device, boot_image=None,
                       write_protected=True):
        """Set backend VM boot image

        :param identity: node name or ID
        :param device: device type (from
            `sushy_tools.emulator.constants`)
        :param boot_image: ID of the image, or `None` to switch to
            boot from volume
        :param write_protected: expose media as read-only or writable

        :raises: `error.FishyError` if boot device can't be set
        """
        instance = self._get_instance(identity)
        instance_image = self._get_instance_image_id(instance)

        if instance_image == boot_image:
            msg = ('Image %(identity)s already has image %(boot_image)s. '
                   'Skipping rebuild.' % {'identity': identity,
                                          'boot_image': boot_image})
            self._logger.debug(msg)

        elif boot_image is None:
            if self._config.get('SUSHY_EMULATOR_OS_VMEDIA_DELAY_EJECT', True):
                self._logger.debug(
                    'Set instance metadata for vmedia eject on next power '
                    'action for %(identity)s' % {'identity': identity})
                server_metadata = {'sushy-tools-delay-eject': 'true'}
                self._cc.set_server_metadata(identity, server_metadata)
            else:
                self._logger.debug(
                    'Create task to rebuild with blank-image for '
                    '%(identity)s' % {'identity': identity})
                # Not running async here, as long as the blank image used is
                # small this should finish in ~20 seconds.
                self._submit_future(
                    False, self._rebuild_with_blank_image, identity)

        else:
            if self._config.get('SUSHY_EMULATOR_OS_VMEDIA_DELAY_EJECT', True):
                # Make sure sushy-tools-delay-eject is cleared when media is
                # inserted. Avoid race in case media is ejected and then
                # inserted without a power action.
                self._remove_delayed_eject_metadata(identity)

            self._logger.debug(
                'Creating task to finish import and rebuild for %(identity)s' %
                {'identity': identity})
            self._submit_future(
                True, self._rebuild_with_imported_image, identity, boot_image)

    def insert_image(self, identity, image_url, local_file_path=None):
        self._logger.debug(
            'Creating task to insert image for %(identity)s' %
            {'identity': identity})
        return self._submit_future(
            False, self._insert_image, identity, image_url, local_file_path)

    def _insert_image(self, identity, image_url, local_file_path=None):
        parsed_url = urlparse.urlparse(image_url)
        local_file = os.path.basename(parsed_url.path)
        unique = base64.urlsafe_b64encode(os.urandom(6)).decode('utf-8')
        boot_mode = self.get_boot_mode(identity)

        image_attrs = {
            'name': '%s %s' % (local_file, unique),
            'disk_format': 'raw',
            'container_format': 'bare',
            'visibility': 'private'
        }
        server_metadata = {'sushy-tools-image-url': image_url}

        if boot_mode == 'UEFI':
            self._logger.debug('Setting UEFI image properties for '
                               '%(identity)s' % {'identity': identity})
            image_attrs['properties'] = {
                'hw_firmware_type': 'uefi',
                'hw_machine_type': 'q35'
            }

        if local_file_path:
            image_attrs['filename'] = local_file_path
            server_metadata['sushy-tools-image-local-file'] = local_file_path

        image = None
        try:
            # Create image, and begin importing. Waiting for import to
            # complete will be part of a long-running operation
            image = self._cc.image.create_image(**image_attrs)
            server_metadata['sushy-tools-import-image'] = image.id
            if local_file_path:
                self._logger.debug(
                    'Uploading image file %(file)s from source %(url)s '
                    'for %(identity)s' % {'identity': identity,
                                          'file': local_file_path,
                                          'url': image_url})
            else:
                self._logger.debug(
                    'Importing image %(url)s for %(identity)s' %
                    {'identity': identity, 'url': image_url})
                self._cc.image.import_image(image, method='web-download',
                                            uri=image_url)

            self._cc.set_server_metadata(identity, server_metadata)

        except Exception as ex:
            msg = 'Failed insert image from URL %s: %s' % (image_url, ex)
            self._logger.exception(msg)
            image_id = image.id if image else None
            self._attempt_delete_image_local_file(
                image_id, local_file_path, identity,
                'sushy-tools-import-image',
                'sushy-tools-image-local-file')
            if not isinstance(ex, error.FishyError):
                ex = error.FishyError(msg)
            raise ex

        return image.id, image.name

    def eject_image(self, identity):
        self._logger.debug(
            'Creating task to eject image for %(identity)s' %
            {'identity': identity})
        self._submit_future(False, self._eject_image, identity)

    def _eject_image(self, identity):
        image_url = None
        try:
            server = self._cc.compute.get_server(identity)
            image_id = server.metadata.get('sushy-tools-import-image')
            image_url = server.metadata.get('sushy-tools-image-url')

            # sushy-tools-import-image not set in metadata, nothing to do
            if image_id is None:
                return

            image = self._cc.image.find_image(image_id)

            if image is None:
                msg = ('Failed ejecting image %s. Image not found in image '
                       'service.' % image_url)
                raise error.FishyError(msg)

            self._attempt_delete_image_local_file(
                image.id, None, identity,
                'sushy-tools-import-image', 'sushy-tools-image-url')
        except Exception as ex:
            msg = 'Failed eject image from URL %s: %s' % (image_url, ex)
            self._logger.exception(msg)
            if not isinstance(ex, error.FishyError):
                ex = error.FishyError(msg)
            raise ex

    def _attempt_delete_image_local_file(self, image, local_file, identity,
                                         *metadata_keys):
        if image:
            try:
                self._logger.debug('Deleting image %(image)s' %
                                   {'image': image})
                self._cc.delete_image(image)
            except Exception:
                pass
        if local_file:
            try:
                self._logger.debug('Deleting local file %(local_file)s' %
                                   {'local_file': local_file})
                self._delete_local_file(local_file)
            except Exception:
                pass
        if identity and metadata_keys:
            try:
                self._cc.delete_server_metadata(identity, metadata_keys)
            except Exception:
                pass

    def _submit_future(self, run_async, fn, identity, *args, **kwargs):
        future = self._futures.get(identity, None)
        if future is not None:
            if future.running():
                raise error.Conflict(
                    'An insert or eject operation is already in progress for '
                    '%(identity)s' % {'identity': identity})

            ex = future.exception()
            del self._futures[identity]
            if ex is not None:
                # A previous operation failed, and the server may be in an
                # unknown state. Raise the previous error as an error for
                # this operation.
                raise ex

        future = self._executor.submit(fn, identity, *args, **kwargs)
        self._futures[identity] = future
        if run_async:
            return
        ex = future.exception()
        if ex is not None:
            raise ex
        return future.result()

    def _rebuild_with_imported_image(self, identity, image_id):
        image_url = None
        image = None
        image_local_file = None

        try:
            image = self._cc.image.get_image(image_id)
            server = self._cc.compute.get_server(identity)
            image_url = server.metadata.get('sushy-tools-image-url')
            image_local_file = server.metadata.get(
                'sushy-tools-image-local-file')

            # Wait for image to be imported
            while image.status in ('queued', 'importing'):
                time.sleep(1)
                image = self._cc.image.get_image(image)

            if image.status != 'active':
                raise error.FishyError('Image import ended with status %s' %
                                       image.status)

            self._logger.debug(
                'Rebuilding %(identity)s with image %(image)s' %
                {'identity': identity, 'image': image.id})
            server = self._cc.compute.rebuild_server(identity, image.id)
            while server.status == 'REBUILD':
                server = self._cc.compute.get_server(identity)
                time.sleep(1)
            if server.status not in ('ACTIVE', 'SHUTOFF'):
                raise error.FishyError('Server rebuild attempt resulted in '
                                       'status %s' % server.status)
            self._logger.debug(
                'Rebuild %(identity)s complete' % {'identity': identity})

        except Exception as ex:
            msg = 'Failed insert image from URL %s: %s' % (image_url, ex)
            self._logger.exception(msg)
            self._attempt_delete_image_local_file(
                image.id, image_local_file, identity,
                'sushy-tools-import-image', 'sushy-tools-image-local-file')
            if not isinstance(ex, error.FishyError):
                ex = error.FishyError(msg)
            raise ex
        finally:
            self._attempt_delete_image_local_file(
                None, image_local_file, identity,
                'sushy-tools-image-local-file')

    def _rebuild_with_blank_image(self, identity):
        image_url = None
        try:
            server = self._cc.compute.get_server(identity)
            image_url = server.metadata.get('sushy-tools-image-url')
            blank_image = self._config.get(
                'SUSHY_EMULATOR_OS_VMEDIA_BLANK_IMAGE',
                'sushy-tools-blank-image')
            image = self._cc.image.find_image(blank_image)

            if image is None:
                msg = ('Failed ejecting image %s, vmedia blank image: %s not '
                       'found.' % (image_url, blank_image))
                raise error.FishyError(msg)

            self._logger.debug(
                'Rebuilding %(identity)s with image %(image)s' %
                {'identity': identity, 'image': image.id})
            server = self._cc.compute.rebuild_server(identity, image.id)

            while server.status == 'REBUILD':
                server = self._cc.compute.get_server(identity)
                time.sleep(1)
            if server.status not in ('ACTIVE', 'SHUTOFF'):
                raise error.FishyError('Server rebuild attempt resulted in '
                                       'status %s' % server.status)
            self._logger.debug(
                'Rebuild %(identity)s complete' % {'identity': identity})

        except Exception as ex:
            msg = 'Failed ejecting image %s: %s' % (image_url, ex)
            self._logger.exception(msg)
            if not isinstance(ex, error.FishyError):
                ex = error.FishyError(msg)
            raise ex

    @staticmethod
    def _delete_local_file(local_file):
        try:
            os.remove(local_file)
        except (FileNotFoundError, TypeError):
            pass

    def _remove_delayed_eject_metadata(self, identity):
        try:
            self._cc.delete_server_metadata(identity,
                                            ['sushy-tools-delay-eject'])
        except Exception:
            pass
