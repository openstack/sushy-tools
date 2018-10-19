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
import functools
import json
import os
import ssl
import sys

from sushy_tools.emulator.drivers import libvirtdriver
from sushy_tools.emulator.drivers import novadriver

import flask


app = flask.Flask(__name__)
# Turn off strict_slashes on all routes
app.url_map.strict_slashes = False

driver = None


def init_virt_driver(decorated_func):
    @functools.wraps(decorated_func)
    def decorator(*args, **kwargs):
        global driver

        if driver is None:

            if 'OS_CLOUD' in os.environ:
                if not novadriver.is_loaded:
                    app.logger.error('Nova driver not loaded')
                    sys.exit(1)

                driver = novadriver.OpenStackDriver(os.environ['OS_CLOUD'])

            else:
                if not libvirtdriver.is_loaded:
                    app.logger.error('libvirt driver not loaded')
                    sys.exit(1)

                driver = libvirtdriver.LibvirtDriver(
                    os.environ.get('SUSHY_EMULATOR_LIBVIRT_URL')
                )

                app.logger.debug('Running with %s', driver.driver)

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
    return flask.render_template('error.json', message=message)


@app.route('/redfish/v1/')
@init_virt_driver
@returns_json
def root_resource():
    return flask.render_template('root.json')


@app.route('/redfish/v1/Systems')
@init_virt_driver
@returns_json
def system_collection_resource():
    systems = driver.systems

    app.logger.debug('Serving systems list')

    return flask.render_template(
        'system_collection.json', system_count=len(systems),
        systems=systems)


@app.route('/redfish/v1/Systems/<identity>', methods=['GET', 'PATCH'])
@init_virt_driver
@returns_json
def system_resource(identity):
    if flask.request.method == 'GET':

        app.logger.debug('Serving resources for system "%s"', identity)

        return flask.render_template(
            'system.json', identity=identity,
            uuid=driver.uuid(identity),
            power_state=driver.get_power_state(identity),
            total_memory_gb=driver.get_total_memory(identity),
            total_cpus=driver.get_total_cpus(identity),
            boot_source_target=driver.get_boot_device(identity),
            boot_source_mode=driver.get_boot_mode(identity)
        )

    elif flask.request.method == 'PATCH':
        boot = flask.request.json.get('Boot')
        if not boot:
            return 'PATCH only works for the Boot element', 400

        target = boot.get('BootSourceOverrideTarget')

        if target:
            # NOTE(lucasagomes): In libvirt we always set the boot
            # device frequency to "continuous" so, we are ignoring the
            # BootSourceOverrideEnabled element here

            driver.set_boot_device(identity, target)

            app.logger.info('Set boot device to "%s" for system "%s"',
                            target, identity)

        mode = boot.get('BootSourceOverrideMode')

        if mode:
            driver.set_boot_mode(identity, mode)

            app.logger.info('Set boot mode to "%s" for system "%s"',
                            mode, identity)

        if not target and not mode:
            return ('Missing the BootSourceOverrideTarget and/or '
                    'BootSourceOverrideMode element', 400)

        return '', 204


@app.route('/redfish/v1/Systems/<identity>/EthernetInterfaces',
           methods=['GET'])
@init_virt_driver
@returns_json
def ethernet_interfaces_collection(identity):
    nics = driver.get_nics(identity)
    return flask.render_template(
        'ethernet_interfaces_collection.json', identity=identity,
        nics=nics)


@app.route('/redfish/v1/Systems/<identity>/EthernetInterfaces/<nic_id>',
           methods=['GET'])
@init_virt_driver
@returns_json
def ethernet_interface(identity, nic_id):
    nics = driver.get_nics(identity)
    for nic in nics:
        if nic['id'] == nic_id:
            return flask.render_template(
                'ethernet_interface.json', identity=identity, nic=nic)

    return 'Not found', 404


@app.route('/redfish/v1/Systems/<identity>/Actions/ComputerSystem.Reset',
           methods=['POST'])
@init_virt_driver
@returns_json
def system_reset_action(identity):
    reset_type = flask.request.json.get('ResetType')

    driver.set_power_state(identity, reset_type)

    app.logger.info('System "%s" power state set to "%s"',
                    identity, reset_type)

    return '', 204


@app.route('/redfish/v1/Systems/<identity>/BIOS', methods=['GET'])
@init_virt_driver
@returns_json
def bios(identity):
    bios = driver.get_bios(identity)

    app.logger.debug('Serving BIOS for system "%s"', identity)

    return flask.render_template(
        'bios.json',
        identity=identity,
        bios_current_attributes=json.dumps(bios, sort_keys=True, indent=6))


@app.route('/redfish/v1/Systems/<identity>/BIOS/Settings',
           methods=['GET', 'PATCH'])
@init_virt_driver
@returns_json
def bios_settings(identity):

    if flask.request.method == 'GET':
        bios = driver.get_bios(identity)

        app.logger.debug('Serving BIOS Settings for system "%s"', identity)

        return flask.render_template(
            'bios_settings.json',
            identity=identity,
            bios_pending_attributes=json.dumps(bios, sort_keys=True, indent=6))

    elif flask.request.method == 'PATCH':
        attributes = flask.request.json.get('Attributes')

        driver.set_bios(identity, attributes)
        app.logger.info('System "%s" BIOS attributes "%s" updated',
                        identity, attributes)
        return '', 204


@app.route('/redfish/v1/Systems/<identity>/BIOS/Actions/Bios.ResetBios',
           methods=['POST'])
@init_virt_driver
@returns_json
def system_reset_bios(identity):

    driver.reset_bios(identity)
    app.logger.info('BIOS for system "%s" reset', identity)
    return '', 204


def parse_args():
    parser = argparse.ArgumentParser('sushy-emulator')
    parser.add_argument('-i', '--interface',
                        type=str,
                        default='',
                        help='Local interface to listen at')
    parser.add_argument('-p', '--port',
                        type=int,
                        default=8000,
                        help='The port to bind the server to')
    parser.add_argument('--ssl-certificate',
                        type=str,
                        help='SSL certificate to use for HTTPS')
    parser.add_argument('--ssl-key',
                        type=str,
                        help='SSL key to use for HTTPS')

    backend_group = parser.add_mutually_exclusive_group()
    backend_group.add_argument('--os-cloud',
                               type=str,
                               help='OpenStack cloud name. Can also be set '
                                    'via environment variable '
                                    '$OS_CLOUD')
    backend_group.add_argument('--libvirt-uri',
                               type=str,
                               default='',
                               help='The libvirt URI. Can also be set via '
                                    'environment variable '
                                    '$SUSHY_EMULATOR_LIBVIRT_URL. '
                                    'Default is qemu:///system')

    return parser.parse_args()


def main():
    global driver

    args = parse_args()

    if args.os_cloud:
        if not novadriver.is_loaded:
            app.logger.error('Nova driver not loaded')
            return 1

        driver = novadriver.OpenStackDriver(args.os_cloud)

    else:
        if not libvirtdriver.is_loaded:
            app.logger.error('libvirt driver not loaded')
            return 1

        driver = libvirtdriver.LibvirtDriver(args.libvirt_uri)

    app.logger.debug('Running with %s', driver.driver)

    ssl_context = None
    if args.ssl_certificate and args.ssl_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(args.ssl_certificate, args.ssl_key)

    app.run(host=args.interface, port=args.port, ssl_context=ssl_context)

    return 0


if __name__ == '__main__':
    sys.exit(main())
