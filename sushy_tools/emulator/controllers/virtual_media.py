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

import flask

from sushy_tools.emulator import api_utils
from sushy_tools import error


virtual_media = flask.Blueprint(
    'VirtualMedia', __name__,
    url_prefix='/redfish/v1/Systems/<identity>/VirtualMedia')


@virtual_media.route('', methods=['GET'])
@api_utils.returns_json
def virtual_media_collection_resource(identity):
    api_utils.debug('Serving virtual media resources for system "%s"',
                    identity)

    return flask.render_template(
        'virtual_media_collection.json',
        identity=identity,
        uuid=flask.current_app.systems.uuid(identity),
        devices=flask.current_app.vmedia.devices
    )


@virtual_media.route('/<device>', methods=['GET'])
@api_utils.returns_json
def virtual_media_resource(identity, device):
    device_name = flask.current_app.vmedia.get_device_name(
        identity, device)

    media_types = flask.current_app.vmedia.get_device_media_types(
        identity, device)

    device_info = flask.current_app.vmedia.get_device_image_info(
        identity, device)

    api_utils.debug('Serving virtual media %s at system "%s"',
                    device, identity)

    return flask.render_template(
        'virtual_media.json',
        identity=identity,
        device=device,
        name=device_name,
        media_types=media_types,
        image_url=device_info.image_url,
        image_name=device_info.image_name,
        inserted=device_info.inserted,
        write_protected=device_info.write_protected,
        username=device_info.username,
        password=device_info.password,
        verify_certificate=device_info.verify,
    )


@virtual_media.route('/<device>', methods=['PATCH'])
@api_utils.returns_json
def virtual_media_patch(identity, device):
    flask.current_app.systems.uuid(identity)
    if not flask.request.json:
        raise error.BadRequest("Empty or malformed patch")

    api_utils.debug('Updating virtual media %s at system "%s"',
                    device, identity)

    verify = flask.request.json.get('VerifyCertificate')
    if verify is not None:
        if not isinstance(verify, bool):
            raise error.BadRequest("VerifyCertificate must be a boolean")

        flask.current_app.vmedia.update_device_info(
            identity, device, verify=verify)
        return '', 204
    else:
        raise error.BadRequest("Empty or malformed patch")


@virtual_media.route('/<device>/Certificates', methods=['GET'])
@api_utils.returns_json
def virtual_media_certificates(identity, device):
    flask.current_app.systems.uuid(identity)
    location = \
        f'/redfish/v1/Systems/{identity}/VirtualMedia/{device}/Certificates'
    certificates = flask.current_app.vmedia.list_certificates(identity, device)
    return flask.render_template(
        'certificate_collection.json',
        location=location,
        certificates=[cert.id for cert in certificates],
    )


@virtual_media.route('/<device>/Certificates', methods=['POST'])
@api_utils.returns_json
def virtual_media_add_certificate(identity, device):
    flask.current_app.systems.uuid(identity)
    if not flask.request.json:
        raise error.BadRequest("Empty or malformed certificate")

    try:
        cert_string = flask.request.json['CertificateString']
        cert_type = flask.request.json['CertificateType']
    except KeyError as exc:
        raise error.BadRequest(f"Missing required parameter {exc}")

    if cert_type != 'PEM':
        raise error.BadRequest(
            f"Only PEM certificates are supported, got {cert_type}")

    api_utils.debug('Adding certificate for virtual media %s at '
                    'system "%s"', device, identity)

    cert = flask.current_app.vmedia.add_certificate(
        identity, device, cert_string, cert_type)

    location = (
        f'/redfish/v1/Systems/{identity}/VirtualMedia/{device}'
        f'/Certificates/{cert.id}'
    )
    return '', 204, {'Location': location}


@virtual_media.route('/<device>/Certificates/<cert_id>', methods=['GET'])
@api_utils.returns_json
def virtual_media_get_certificate(identity, device, cert_id):
    flask.current_app.systems.uuid(identity)
    location = (
        f'/redfish/v1/Systems/{identity}/VirtualMedia/{device}'
        f'/Certificates/{cert_id}'
    )
    certificates = flask.current_app.vmedia.list_certificates(identity, device)
    try:
        cert = next(c for c in certificates if c.id == cert_id)
    except StopIteration:
        raise error.NotFound()

    return flask.render_template(
        'certificate.json',
        location=location,
        cert_id=cert.id,
        cert_string=cert.string,
        cert_type=cert.type_,
    )


@virtual_media.route('/<device>/Certificates/<cert_id>', methods=['DELETE'])
@api_utils.returns_json
def virtual_media_delete_certificate(identity, device, cert_id):
    flask.current_app.systems.uuid(identity)
    api_utils.debug('Removing certificate %s for virtual media %s at '
                    'system "%s"', cert_id, device, identity)
    flask.current_app.vmedia.delete_certificate(identity, device, cert_id)
    return '', 204


@virtual_media.route('/<device>/Actions/VirtualMedia.InsertMedia',
                     methods=['POST'])
@api_utils.returns_json
def virtual_media_insert(identity, device):
    image = flask.request.json.get('Image')
    inserted = flask.request.json.get('Inserted', True)
    write_protected = flask.request.json.get('WriteProtected', True)
    username = flask.request.json.get('UserName', '')
    password = flask.request.json.get('Password', '')

    if (not username and password) or (username and not password):
        message = "UserName and Password must be passed together"
        return flask.render_template('error.json', message=message), 400

    system = flask.current_app.systems.uuid(identity)

    image_path = flask.current_app.vmedia.insert_image(
        identity, device, image, inserted, write_protected,
        username=username, password=password)

    try:
        flask.current_app.systems.set_boot_image(
            system, device, boot_image=image_path,
            write_protected=write_protected)

    except error.NotSupportedError as ex:
        api_utils.warning(
            'System %s failed to set boot image %s on device %s: '
            '%s', system, image_path, device, ex)
    else:
        api_utils.info(
            'Virtual media placed into device %(dev)s for '
            'system %(sys)s. Image %(img)s inserted %(ins)s',
            {'dev': device, 'sys': identity,
             'img': image or '<empty>', 'ins': inserted})

    return '', 204


@virtual_media.route('/<device>/Actions/VirtualMedia.EjectMedia',
                     methods=['POST'])
@api_utils.returns_json
def virtual_media_eject(identity, device):
    flask.current_app.vmedia.eject_image(identity, device)

    try:
        flask.current_app.systems.set_boot_image(identity, device)

    except error.NotSupportedError as ex:
        api_utils.warning(
            'System %s failed to remove boot image from device %s: '
            '%s', identity, device, ex)
    else:
        api_utils.info(
            'Virtual media ejected from device %s system %s',
            device, identity)

    return '', 204
