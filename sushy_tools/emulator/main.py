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

import argparse
import functools
import os
import ssl

import flask

from sushy_tools.emulator.drivers import libvirtdriver


app = flask.Flask(__name__)
# Turn off strict_slashes on all routes
app.url_map.strict_slashes = False

driver = None


def init_virt_driver(decorated_func):
    @functools.wraps(decorated_func)
    def decorator(*args, **kwargs):
        global driver

        if driver is None:

            driver = libvirtdriver.LibvirtDriver(
                os.environ.get('SUSHY_EMULATOR_LIBVIRT_URL')
            )

        return decorated_func(*args, **kwargs)

    return decorator


def returns_json(decorated_func):
    @functools.wraps(decorated_func)
    def decorator(*args, **kwargs):
        response = decorated_func(*args, **kwargs)
        if isinstance(response, flask.Response):
            return flask.Response(response, content_type='application/json')
        else:
            return response

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

    return flask.render_template(
        'system_collection.json', system_count=len(systems),
        systems=systems)


@app.route('/redfish/v1/Systems/<identity>', methods=['GET', 'PATCH'])
@init_virt_driver
@returns_json
def system_resource(identity):
    if flask.request.method == 'GET':
        return flask.render_template(
            'system.json', identity=identity,
            uuid=driver.uuid(identity),
            power_state=driver.get_power_state(identity),
            total_memory_gb=driver.get_total_memory(identity),
            total_cpus=driver.get_total_cpus(identity),
            boot_source_target=driver.get_boot_device(identity)
        )

    elif flask.request.method == 'PATCH':
        boot = flask.request.json.get('Boot')
        if not boot:
            return 'PATCH only works for the Boot element', 400

        target = boot.get('BootSourceOverrideTarget')
        if not target:
            return 'Missing the BootSourceOverrideTarget element', 400

        # NOTE(lucasagomes): In libvirt we always set the boot
        # device frequency to "continuous" so, we are ignoring the
        # BootSourceOverrideEnabled element here

        # TODO(lucasagomes): We should allow changing the boot mode from
        # BIOS to UEFI (and vice-versa)

        driver.set_boot_device(identity, target)

        return '', 204


@app.route('/redfish/v1/Systems/<identity>/Actions/ComputerSystem.Reset',
           methods=['POST'])
@init_virt_driver
@returns_json
def system_reset_action(identity):
    reset_type = flask.request.json.get('ResetType')

    driver.set_power_state(identity, reset_type)

    return '', 204


def parse_args():
    parser = argparse.ArgumentParser('sushy-emulator')
    parser.add_argument('-p', '--port',
                        type=int,
                        default=8000,
                        help='The port to bind the server to')
    parser.add_argument('-u', '--libvirt-uri',
                        type=str,
                        default='',
                        help='The libvirt URI. Can also be set via '
                             'environment variable '
                             '$SUSHY_EMULATOR_LIBVIRT_URL')
    parser.add_argument('-c', '--ssl-certificate',
                        type=str,
                        help='SSL certificate to use for HTTPS')
    parser.add_argument('-k', '--ssl-key',
                        type=str,
                        help='SSL key to use for HTTPS')
    return parser.parse_args()


def main():
    global driver

    args = parse_args()

    driver = libvirtdriver.LibvirtDriver(args.libvirt_uri)

    ssl_context = None
    if args.ssl_certificate and args.ssl_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(args.ssl_certificate, args.ssl_key)

    app.run(host='', port=args.port, ssl_context=ssl_context)


if __name__ == '__main__':
    main()
