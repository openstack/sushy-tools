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
import ssl

import flask

from sushy_tools.emulator.clouds import libvirtdriver
from sushy_tools.error import FishyError


app = flask.Flask(__name__)
# Turn off strict_slashes on all routes
app.url_map.strict_slashes = False

lvCloudDriver = None


@app.route('/redfish/v1/')
def root_resource():
    return flask.render_template('root.json')


@app.route('/redfish/v1/Systems')
def system_collection_resource():
    domains = lvCloudDriver.domains

    return flask.render_template(
        'system_collection.json', system_count=len(domains),
        systems=domains)


@app.route('/redfish/v1/Systems/<identity>', methods=['GET', 'PATCH'])
def system_resource(identity):
    if flask.request.method == 'GET':

        return flask.render_template(
            'system.json', identity=identity,
            uuid=lvCloudDriver.uuid(identity),
            power_state=lvCloudDriver.power_state(identity),
            total_memory_gb=lvCloudDriver.total_memory(identity),
            total_cpus=lvCloudDriver.total_cpus(identity),
            boot_source_target=lvCloudDriver.boot_device(identity))

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

        try:
            lvCloudDriver.boot_device(identity, target)

        except FishyError:
            flask.abort(500)

        return '', 204


@app.route('/redfish/v1/Systems/<identity>/Actions/ComputerSystem.Reset',
           methods=['POST'])
def system_reset_action(identity):
    reset_type = flask.request.json.get('ResetType')

    try:
        lvCloudDriver.power_state(identity, reset_type)

    except FishyError:
        flask.abort(500)

    return '', 204


def parse_args():
    parser = argparse.ArgumentParser('sushy-emulator')
    parser.add_argument('-p', '--port',
                        type=int,
                        default=8000,
                        help='The port to bind the server to')
    parser.add_argument('-u', '--libvirt-uri',
                        type=str,
                        default='qemu:///system',
                        help='The libvirt URI')
    parser.add_argument('-c', '--ssl-certificate',
                        type=str,
                        help='SSL certificate to use for HTTPS')
    parser.add_argument('-k', '--ssl-key',
                        type=str,
                        help='SSL key to use for HTTPS')
    return parser.parse_args()


def main():
    global lvCloudDriver

    args = parse_args()

    lvCloudDriver = libvirtdriver.LibvirtCloudDriver(args.libvirt_uri)

    ssl_context = None
    if args.ssl_certificate and args.ssl_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(args.ssl_certificate, args.ssl_key)

    app.run(host='', port=args.port, ssl_context=ssl_context)


if __name__ == '__main__':
    main()
