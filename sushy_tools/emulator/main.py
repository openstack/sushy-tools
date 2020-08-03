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

import argparse
from datetime import datetime
import functools
import json
import os
import ssl
import sys

import flask

from sushy_tools.emulator.resources.chassis import staticdriver as chsdriver
from sushy_tools.emulator.resources.drives import staticdriver as drvdriver
from sushy_tools.emulator.resources.indicators import staticdriver as inddriver
from sushy_tools.emulator.resources.managers import staticdriver as mgrdriver
from sushy_tools.emulator.resources.storage import staticdriver as stgdriver
from sushy_tools.emulator.resources.systems import libvirtdriver
from sushy_tools.emulator.resources.systems import novadriver
from sushy_tools.emulator.resources.vmedia import staticdriver as vmddriver
from sushy_tools.emulator.resources.volumes import staticdriver as voldriver
from sushy_tools import error
from sushy_tools.error import FishyError


class Application(flask.Flask):

    def __init__(self):
        super().__init__(__name__)
        # Turn off strict_slashes on all routes
        self.url_map.strict_slashes = False
        config_file = os.environ.get('SUSHY_EMULATOR_CONFIG')
        if config_file:
            self.config.from_pyfile(config_file)


app = Application()


class Resources(object):

    SYSTEMS = None
    MANAGERS = None
    CHASSIS = None
    INDICATORS = None
    VMEDIA = None
    STORAGE = None
    DRIVES = None
    VOLUMES = None

    def __new__(cls, *args, **kwargs):

        if not cls.SYSTEMS:

            os_cloud = app.config.get('SUSHY_EMULATOR_OS_CLOUD')

            if os_cloud:
                if not novadriver.is_loaded:
                    app.logger.error('Nova driver not loaded')
                    sys.exit(1)

                cls.SYSTEMS = novadriver.OpenStackDriver.initialize(
                    app.config, app.logger, os_cloud)

            else:
                if not libvirtdriver.is_loaded:
                    app.logger.error('libvirt driver not loaded')
                    sys.exit(1)

                libvirt_uri = app.config.get('SUSHY_EMULATOR_LIBVIRT_URI', '')

                cls.SYSTEMS = libvirtdriver.LibvirtDriver.initialize(
                    app.config, app.logger, libvirt_uri)

            app.logger.debug(
                'Initialized system resource backed by %s '
                'driver', cls.SYSTEMS().driver)

        if cls.MANAGERS is None:
            cls.MANAGERS = mgrdriver.StaticDriver.initialize(
                app.config, app.logger)

            app.logger.debug(
                'Initialized manager resource backed by %s '
                'driver', cls.MANAGERS().driver)

        if cls.CHASSIS is None:
            cls.CHASSIS = chsdriver.StaticDriver.initialize(
                app.config, app.logger)

            app.logger.debug(
                'Initialized chassis resource backed by %s '
                'driver', cls.CHASSIS().driver)

        if cls.INDICATORS is None:
            cls.INDICATORS = inddriver.StaticDriver.initialize(
                app.config, app.logger)

            app.logger.debug(
                'Initialized indicators resource backed by %s '
                'driver', cls.INDICATORS().driver)

        if cls.VMEDIA is None:
            cls.VMEDIA = vmddriver.StaticDriver.initialize(
                app.config, app.logger)

            app.logger.debug(
                'Initialized virtual media resource backed by %s '
                'driver', cls.VMEDIA().driver)

        if cls.STORAGE is None:
            cls.STORAGE = stgdriver.StaticDriver.initialize(
                app.config, app.logger)

            app.logger.debug(
                'Initialized storage resource backed by %s '
                'driver', cls.STORAGE().driver)

        if cls.DRIVES is None:
            cls.DRIVES = drvdriver.StaticDriver.initialize(
                app.config, app.logger)

            app.logger.debug(
                'Initialized drive resource backed by %s '
                'driver', cls.DRIVES().driver)

        if cls.VOLUMES is None:
            cls.VOLUMES = voldriver.StaticDriver.initialize(
                app.config, app.logger)

            app.logger.debug(
                'Initialized volumes resource backed by %s '
                'driver', cls.VOLUMES().driver)

        return super(Resources, cls).__new__(cls, *args, **kwargs)

    def __enter__(self):
        self.systems = self.SYSTEMS()
        self.managers = self.MANAGERS()
        self.chassis = self.CHASSIS()
        self.indicators = self.INDICATORS()
        self.vmedia = self.VMEDIA()
        self.storage = self.STORAGE()
        self.drives = self.DRIVES()
        self.volumes = self.VOLUMES()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.systems
        del self.managers
        del self.chassis
        del self.indicators
        del self.vmedia
        del self.storage
        del self.drives
        del self.volumes


def instance_denied(**kwargs):
    deny = True

    try:
        deny = (kwargs['identity'] not in
                app.config['SUSHY_EMULATOR_ALLOWED_INSTANCES'])

    except KeyError:
        deny = False

    finally:
        if deny:
            app.logger.warning('Instance %s access denied',
                               kwargs.get('identity'))

        return deny


def ensure_instance_access(decorated_func):
    @functools.wraps(decorated_func)
    def decorator(*args, **kwargs):
        if instance_denied(**kwargs):
            raise FishyError('Error finding instance')

        return decorated_func(*args, **kwargs)

    return decorator


def returns_json(decorated_func):
    @functools.wraps(decorated_func)
    def decorator(*args, **kwargs):
        response = decorated_func(*args, **kwargs)
        if isinstance(response, flask.Response):
            return response
        if isinstance(response, tuple):
            contents, status = response
        else:
            contents, status = response, 200
        return flask.Response(response=contents, status=status,
                              content_type='application/json')

    return decorator


@app.errorhandler(Exception)
@returns_json
def all_exception_handler(message):
    if isinstance(message, error.AliasAccessError):
        url = flask.url_for(flask.request.endpoint, identity=message.args[0])
        return flask.redirect(url, code=307, Response=flask.Response)
    return flask.render_template('error.json', message=message), 500


@app.route('/redfish/v1/')
@returns_json
def root_resource():
    return flask.render_template('root.json')


@app.route('/redfish/v1/Chassis')
@returns_json
def chassis_collection_resource():
    with Resources() as resources:

        app.logger.debug('Serving chassis list')

        return flask.render_template(
            'chassis_collection.json',
            manager_count=len(resources.chassis.chassis),
            chassis=resources.chassis.chassis)


@app.route('/redfish/v1/Chassis/<identity>', methods=['GET', 'PATCH'])
@returns_json
def chassis_resource(identity):
    with Resources() as resources:

        chassis = resources.chassis

        uuid = chassis.uuid(identity)

        if flask.request.method == 'GET':

            app.logger.debug('Serving resources for chassis "%s"', identity)

            # the first chassis gets all resources
            if uuid == chassis.chassis[0]:
                systems = resources.systems.systems
                managers = resources.managers.managers
                storage = resources.storage.get_all_storage()
                drives = resources.drives.get_all_drives()

            else:
                systems = []
                managers = []
                storage = []
                drives = []

            return flask.render_template(
                'chassis.json',
                identity=identity,
                name=chassis.name(identity),
                uuid=uuid,
                contained_by=None,
                contained_systems=systems,
                contained_managers=managers,
                contained_chassis=[],
                managers=managers[:1],
                indicator_led=resources.indicators.get_indicator_state(
                    uuid),
                storage=storage,
                drives=drives
            )

        elif flask.request.method == 'PATCH':
            indicator_led_state = flask.request.json.get('IndicatorLED')
            if not indicator_led_state:
                return 'PATCH only works for IndicatorLED element', 400

            resources.indicators.set_indicator_state(
                uuid, indicator_led_state)

            app.logger.info('Set indicator LED to "%s" for chassis "%s"',
                            indicator_led_state, identity)

            return '', 204


@app.route('/redfish/v1/Chassis/<identity>/Thermal', methods=['GET'])
@returns_json
def thermal_resource(identity):
    with Resources() as resources:

        chassis = resources.chassis

        uuid = chassis.uuid(identity)

        if flask.request.method != 'GET':
            return

        app.logger.debug(
            'Serving thermal resources for chassis "%s"', identity)

        # the first chassis gets all resources
        if uuid == chassis.chassis[0]:
            systems = resources.systems.systems

        else:
            systems = []

        return flask.render_template(
            'thermal.json',
            chassis=identity,
            systems=systems
        )


@app.route('/redfish/v1/Managers')
@returns_json
def manager_collection_resource():
    with Resources() as resources:

        app.logger.debug('Serving managers list')

        return flask.render_template(
            'manager_collection.json',
            manager_count=len(resources.managers.managers),
            managers=resources.managers.managers)


@app.route('/redfish/v1/Managers/<identity>', methods=['GET'])
@returns_json
def manager_resource(identity):
    if flask.request.method == 'GET':

        with Resources() as resources:

            app.logger.debug('Serving resources for manager "%s"', identity)

            managers = resources.managers

            uuid = managers.uuid(identity)

            # the first manager gets all resources
            if uuid == managers.managers[0]:
                systems = resources.systems.systems
                chassis = resources.chassis.chassis

            else:
                systems = []
                chassis = []

            return flask.render_template(
                'manager.json',
                dateTime=datetime.now().strftime('%Y-%M-%dT%H:%M:%S+00:00'),
                identity=identity,
                name=resources.managers.name(identity),
                uuid=uuid,
                serviceEntryPointUUID=resources.managers.uuid(identity),
                systems=systems,
                chassis=chassis
            )


@app.route('/redfish/v1/Managers/<identity>/VirtualMedia', methods=['GET'])
@returns_json
def virtual_media_collection_resource(identity):
    if flask.request.method == 'GET':

        with Resources() as resources:

            app.logger.debug('Serving virtual media resources for '
                             'manager "%s"', identity)

            return flask.render_template(
                'virtual_media_collection.json',
                identity=identity,
                uuid=resources.managers.uuid(identity),
                devices=resources.vmedia.devices
            )


@app.route('/redfish/v1/Managers/<identity>/VirtualMedia/<device>',
           methods=['GET'])
@returns_json
def virtual_media_resource(identity, device):
    if flask.request.method == 'GET':

        with Resources() as resources:

            try:
                device_name = resources.vmedia.get_device_name(
                    identity, device)

                media_types = resources.vmedia.get_device_media_types(
                    identity, device)

                (image_name, image_url, inserted,
                 write_protected) = resources.vmedia.get_device_image_info(
                    identity, device)

            except error.FishyError as ex:
                app.logger.warning(
                    'Virtual media %s at manager %s error: '
                    '%s', device, identity, ex)
                return 'Not found', 404

        app.logger.debug('Serving virtual media %s at '
                         'manager "%s"', device, identity)

        return flask.render_template(
            'virtual_media.json',
            identity=identity,
            device=device,
            name=device_name,
            media_types=media_types,
            image_url=image_url,
            image_name=image_name,
            inserted=inserted,
            write_protected=write_protected
        )


@app.route('/redfish/v1/Managers/<identity>/VirtualMedia/<device>'
           '/Actions/VirtualMedia.InsertMedia',
           methods=['POST'])
@returns_json
def virtual_media_insert(identity, device):
    image = flask.request.json.get('Image')
    inserted = flask.request.json.get('Inserted', True)
    write_protected = flask.request.json.get('WriteProtected', False)

    with Resources() as resources:

        image_path = resources.vmedia.insert_image(
            identity, device, image, inserted, write_protected)

        for system in resources.systems.systems:
            try:
                resources.systems.set_boot_image(
                    system, device, boot_image=image_path,
                    write_protected=write_protected)

            except error.NotSupportedError as ex:
                app.logger.warning(
                    'System %s failed to set boot image %s on device %s: '
                    '%s', system, image_path, device, ex)

    app.logger.info(
        'Virtual media placed into device %s manager %s image %s '
        'inserted %s', device, identity, image or '<empty>', inserted)

    return '', 204


@app.route('/redfish/v1/Managers/<identity>/VirtualMedia/<device>'
           '/Actions/VirtualMedia.EjectMedia',
           methods=['POST'])
@returns_json
def virtual_media_eject(identity, device):
    with Resources() as resources:
        resources.vmedia.eject_image(identity, device)

        for system in resources.systems.systems:
            try:
                resources.systems.set_boot_image(system, device)

            except error.NotSupportedError as ex:
                app.logger.warning(
                    'System %s failed to remove boot image from device %s: '
                    '%s', system, device, ex)

    app.logger.info(
        'Virtual media ejected from device %s manager %s '
        'image ', device, identity)

    return '', 204


@app.route('/redfish/v1/Systems')
@returns_json
def system_collection_resource():
    with Resources() as resources:
        systems = [system for system in resources.systems.systems
                   if not instance_denied(identity=system)]

    app.logger.debug('Serving systems list')

    return flask.render_template(
        'system_collection.json', system_count=len(systems), systems=systems)


@app.route('/redfish/v1/Systems/<identity>', methods=['GET', 'PATCH'])
@ensure_instance_access
@returns_json
def system_resource(identity):

    with Resources() as resources:

        if flask.request.method == 'GET':

            app.logger.debug('Serving resources for system "%s"', identity)

            return flask.render_template(
                'system.json',
                identity=identity,
                name=resources.systems.name(identity),
                uuid=resources.systems.uuid(identity),
                power_state=resources.systems.get_power_state(identity),
                total_memory_gb=resources.systems.get_total_memory(identity),
                total_cpus=resources.systems.get_total_cpus(identity),
                boot_source_target=resources.systems.get_boot_device(identity),
                boot_source_mode=resources.systems.get_boot_mode(identity),
                managers=resources.managers.managers[:1],
                chassis=resources.chassis.chassis[:1],
                indicator_led=resources.indicators.get_indicator_state(
                    resources.systems.uuid(identity))
            )

        elif flask.request.method == 'PATCH':
            boot = flask.request.json.get('Boot')
            indicator_led_state = flask.request.json.get('IndicatorLED')
            if not boot and not indicator_led_state:
                return ('PATCH only works for Boot and '
                        'IndicatorLED elements'), 400

            if boot:
                target = boot.get('BootSourceOverrideTarget')

                if target:
                    # NOTE(lucasagomes): In libvirt we always set the boot
                    # device frequency to "continuous" so, we are ignoring the
                    # BootSourceOverrideEnabled element here

                    resources.systems.set_boot_device(identity, target)

                    app.logger.info('Set boot device to "%s" for system "%s"',
                                    target, identity)

                mode = boot.get('BootSourceOverrideMode')

                if mode:
                    resources.systems.set_boot_mode(identity, mode)

                    app.logger.info('Set boot mode to "%s" for system "%s"',
                                    mode, identity)

                if not target and not mode:
                    return ('Missing the BootSourceOverrideTarget and/or '
                            'BootSourceOverrideMode element', 400)

            if indicator_led_state:
                resources.indicators.set_indicator_state(
                    resources.systems.uuid(identity), indicator_led_state)

                app.logger.info('Set indicator LED to "%s" for system "%s"',
                                indicator_led_state, identity)

            return '', 204


@app.route('/redfish/v1/Systems/<identity>/EthernetInterfaces',
           methods=['GET'])
@ensure_instance_access
@returns_json
def ethernet_interfaces_collection(identity):
    with Resources() as resources:
        nics = resources.systems.get_nics(identity)

        return flask.render_template(
            'ethernet_interfaces_collection.json', identity=identity,
            nics=nics)


@app.route('/redfish/v1/Systems/<identity>/EthernetInterfaces/<nic_id>',
           methods=['GET'])
@ensure_instance_access
@returns_json
def ethernet_interface(identity, nic_id):
    with Resources() as resources:
        nics = resources.systems.get_nics(identity)

    for nic in nics:
        if nic['id'] == nic_id:
            return flask.render_template(
                'ethernet_interface.json', identity=identity, nic=nic)

    return 'Not found', 404


@app.route('/redfish/v1/Systems/<identity>/Actions/ComputerSystem.Reset',
           methods=['POST'])
@ensure_instance_access
@returns_json
def system_reset_action(identity):
    reset_type = flask.request.json.get('ResetType')

    with Resources() as resources:
        resources.systems.set_power_state(identity, reset_type)

    app.logger.info('System "%s" power state set to "%s"',
                    identity, reset_type)

    return '', 204


@app.route('/redfish/v1/Systems/<identity>/BIOS', methods=['GET'])
@ensure_instance_access
@returns_json
def bios(identity):
    with Resources() as resources:
        bios = resources.systems.get_bios(identity)

    app.logger.debug('Serving BIOS for system "%s"', identity)

    return flask.render_template(
        'bios.json',
        identity=identity,
        bios_current_attributes=json.dumps(bios, sort_keys=True, indent=6))


@app.route('/redfish/v1/Systems/<identity>/BIOS/Settings',
           methods=['GET', 'PATCH'])
@ensure_instance_access
@returns_json
def bios_settings(identity):

    if flask.request.method == 'GET':
        with Resources() as resources:
            bios = resources.systems.get_bios(identity)

        app.logger.debug('Serving BIOS Settings for system "%s"', identity)

        return flask.render_template(
            'bios_settings.json',
            identity=identity,
            bios_pending_attributes=json.dumps(bios, sort_keys=True, indent=6))

    elif flask.request.method == 'PATCH':
        attributes = flask.request.json.get('Attributes')

        with Resources() as resources:
            resources.systems.set_bios(identity, attributes)

        app.logger.info('System "%s" BIOS attributes "%s" updated',
                        identity, attributes)
        return '', 204


@app.route('/redfish/v1/Systems/<identity>/BIOS/Actions/Bios.ResetBios',
           methods=['POST'])
@ensure_instance_access
@returns_json
def system_reset_bios(identity):
    with Resources() as resources:
        resources.systems.reset_bios(identity)

    app.logger.info('BIOS for system "%s" reset', identity)

    return '', 204


@app.route('/redfish/v1/Systems/<identity>/SimpleStorage',
           methods=['GET'])
@ensure_instance_access
@returns_json
def simple_storage_collection(identity):
    with Resources() as resources:
        simple_storage_controllers = (
            resources.systems.get_simple_storage_collection(identity))

        return flask.render_template(
            'simple_storage_collection.json', identity=identity,
            simple_storage_controllers=simple_storage_controllers)


@app.route('/redfish/v1/Systems/<identity>/SimpleStorage/<simple_storage_id>',
           methods=['GET'])
@ensure_instance_access
@returns_json
def simple_storage(identity, simple_storage_id):
    with Resources() as resources:
        simple_storage_controllers = (
            resources.systems.get_simple_storage_collection(identity))
        try:
            storage_controller = simple_storage_controllers[simple_storage_id]
        except KeyError:
            app.logger.debug('"%s" Simple Storage resource was not found')
            return 'Not found', 404
        return flask.render_template('simple_storage.json', identity=identity,
                                     simple_storage=storage_controller)


@app.route('/redfish/v1/Systems/<identity>/Storage',
           methods=['GET'])
@ensure_instance_access
@returns_json
def storage_collection(identity):
    with Resources() as resources:
        uuid = resources.systems.uuid(identity)

        storage_col = resources.storage.get_storage_col(uuid)

        return flask.render_template(
            'storage_collection.json', identity=identity,
            storage_col=storage_col)


@app.route('/redfish/v1/Systems/<identity>/Storage/<storage_id>',
           methods=['GET'])
@ensure_instance_access
@returns_json
def storage(identity, storage_id):
    with Resources() as resources:
        uuid = resources.systems.uuid(identity)
        storage_col = resources.storage.get_storage_col(uuid)

    for stg in storage_col:
        if stg['Id'] == storage_id:
            return flask.render_template(
                'storage.json', identity=identity, storage=stg)

    return 'Not found', 404


@app.route('/redfish/v1/Systems/<identity>/Storage/<stg_id>/Drives/<drv_id>',
           methods=['GET'])
@ensure_instance_access
@returns_json
def drive_resource(identity, stg_id, drv_id):
    with Resources() as resources:
        uuid = resources.systems.uuid(identity)
        drives = resources.drives.get_drives(uuid, stg_id)

    for drv in drives:
        if drv['Id'] == drv_id:
            return flask.render_template(
                'drive.json', identity=identity, storage_id=stg_id, drive=drv)

    return 'Not found', 404


@app.route('/redfish/v1/Systems/<identity>/Storage/<storage_id>/Volumes',
           methods=['GET', 'POST'])
@ensure_instance_access
@returns_json
def volumes_collection(identity, storage_id):
    with Resources() as resources:

        uuid = resources.systems.uuid(identity)

        if flask.request.method == 'GET':

            vol_col = resources.volumes.get_volumes_col(uuid, storage_id)

            vol_ids = []
            for vol in vol_col:
                vol_id = resources.systems.find_or_create_storage_volume(vol)
                if not vol_id:
                    resources.volumes.delete_volume(uuid, storage_id, vol)
                else:
                    vol_ids.append(vol_id)

            return flask.render_template(
                'volume_collection.json', identity=identity,
                storage_id=storage_id, volume_col=vol_ids)

        elif flask.request.method == 'POST':
            data = {
                "Name": flask.request.json.get('Name'),
                "VolumeType": flask.request.json.get('VolumeType'),
                "CapacityBytes": flask.request.json.get('CapacityBytes'),
                "Id": str(os.getpid()) + datetime.now().strftime("%H%M%S")
            }
            data['libvirtVolName'] = data['Id']
            new_id = resources.systems.find_or_create_storage_volume(data)
            if new_id:
                resources.volumes.add_volume(uuid, storage_id, data)
                app.logger.debug('New storage volume created with ID "%s"',
                                 new_id)
                vol_url = ("/redfish/v1/Systems/%s/Storage/%s/"
                           "Volumes/%s" % (identity, storage_id, new_id))
                return flask.Response(status=201,
                                      headers={'Location': vol_url})


@app.route('/redfish/v1/Systems/<identity>/Storage/<stg_id>/Volumes/<vol_id>',
           methods=['GET'])
@ensure_instance_access
@returns_json
def volume(identity, stg_id, vol_id):
    with Resources() as resources:
        uuid = resources.systems.uuid(identity)
        vol_col = resources.volumes.get_volumes_col(uuid, stg_id)

        for vol in vol_col:
            if vol['Id'] == vol_id:
                vol_id = resources.systems.find_or_create_storage_volume(vol)
                if not vol_id:
                    resources.volumes.delete_volume(uuid, stg_id, vol)
                else:
                    return flask.render_template(
                        'volume.json', identity=identity, storage_id=stg_id,
                        volume=vol)

    return 'Not Found', 404


def parse_args():
    parser = argparse.ArgumentParser('sushy-emulator')
    parser.add_argument('--config',
                        type=str,
                        help='Config file path. Can also be set via '
                             'environment variable SUSHY_EMULATOR_CONFIG.')
    parser.add_argument('-i', '--interface',
                        type=str,
                        help='IP address of the local interface to listen '
                             'at. Can also be set via config variable '
                             'SUSHY_EMULATOR_LISTEN_IP. Default is all '
                             'local interfaces.')
    parser.add_argument('-p', '--port',
                        type=int,
                        help='TCP port to bind the server to.  Can also be '
                             'set via config variable '
                             'SUSHY_EMULATOR_LISTEN_PORT. Default is 8000.')
    parser.add_argument('--ssl-certificate',
                        type=str,
                        help='SSL certificate to use for HTTPS. Can also be '
                        'set via config variable SUSHY_EMULATOR_SSL_CERT.')
    parser.add_argument('--ssl-key',
                        type=str,
                        help='SSL key to use for HTTPS. Can also be set'
                        'via config variable SUSHY_EMULATOR_SSL_KEY.')
    backend_group = parser.add_mutually_exclusive_group()
    backend_group.add_argument('--os-cloud',
                               type=str,
                               help='OpenStack cloud name. Can also be set '
                                    'via environment variable OS_CLOUD or '
                                    'config variable SUSHY_EMULATOR_OS_CLOUD.'
                               )
    backend_group.add_argument('--libvirt-uri',
                               type=str,
                               help='The libvirt URI. Can also be set via '
                                    'environment variable '
                                    'SUSHY_EMULATOR_LIBVIRT_URI. '
                                    'Default is qemu:///system')

    return parser.parse_args()


def main():

    args = parse_args()

    if args.config:
        app.config.from_pyfile(args.config)

    if args.os_cloud:
        app.config['SUSHY_EMULATOR_OS_CLOUD'] = args.os_cloud

    if args.libvirt_uri:
        app.config['SUSHY_EMULATOR_LIBVIRT_URI'] = args.libvirt_uri

    else:
        for envvar in ('SUSHY_EMULATOR_LIBVIRT_URL',  # backward compatibility
                       'SUSHY_EMULATOR_LIBVIRT_URI'):
            envvar = os.environ.get(envvar)
            if envvar:
                app.config['SUSHY_EMULATOR_LIBVIRT_URI'] = envvar

    if args.interface:
        app.config['SUSHY_EMULATOR_LISTEN_IP'] = args.interface

    if args.port:
        app.config['SUSHY_EMULATOR_LISTEN_PORT'] = args.port

    if args.ssl_certificate:
        app.config['SUSHY_EMULATOR_SSL_CERT'] = args.ssl_certificate

    if args.ssl_key:
        app.config['SUSHY_EMULATOR_SSL_KEY'] = args.ssl_key

    ssl_context = None
    ssl_certificate = app.config.get('SUSHY_EMULATOR_SSL_CERT')
    ssl_key = app.config.get('SUSHY_EMULATOR_SSL_KEY')

    if ssl_certificate and ssl_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(ssl_certificate, ssl_key)

    app.run(host=app.config.get('SUSHY_EMULATOR_LISTEN_IP'),
            port=app.config.get('SUSHY_EMULATOR_LISTEN_PORT', 8000),
            ssl_context=ssl_context)

    return 0


if __name__ == '__main__':
    sys.exit(main())
