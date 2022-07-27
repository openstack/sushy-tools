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

import re

import flask

from sushy_tools.emulator import api_utils
from sushy_tools import error


certificate_service = flask.Blueprint(
    'CertificateService', __name__,
    url_prefix='/redfish/v1/CertificateService')


_VMEDIA_URI_PATTERN = re.compile(
    '/redfish/v1/Managers/([^/]+)/VirtualMedia/([^/]+)/Certificates/([^/]+)/?$'
)


@certificate_service.route('', methods=['GET'])
@api_utils.returns_json
def certificate_service_resource():
    api_utils.debug('Serving certificate service')
    return flask.render_template('certificate_service.json')


@certificate_service.route('/CertificateLocations', methods=['GET'])
@api_utils.returns_json
def certificate_service_locations():
    api_utils.debug('Serving certificate locations')
    locations = []
    for mgr in flask.current_app.managers.managers:
        for dev in flask.current_app.vmedia.devices:
            try:
                certs = flask.current_app.vmedia.list_certificates(mgr, dev)
            except error.NotFound:
                api_utils.debug('No certificates for manager %s, virtual '
                                'media device %s', mgr, dev)
                continue

            for cert in certs:
                locations.append(
                    f'/redfish/v1/Managers/{mgr}/VirtualMedia/{dev}'
                    f'/Certificates/{cert.id}'
                )

    return flask.render_template('certificate_locations.json',
                                 certificates=locations)


@certificate_service.route('/Actions/CertificateService.ReplaceCertificate',
                           methods=['POST'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def certificate_service_replace_certificate():
    if not flask.request.json:
        raise error.BadRequest("Empty or malformed certificate")

    try:
        cert_string = flask.request.json['CertificateString']
        cert_type = flask.request.json['CertificateType']
        cert_uri = flask.request.json['CertificateUri']
    except KeyError as exc:
        raise error.BadRequest(f"Missing required parameter {exc}")

    match = _VMEDIA_URI_PATTERN.search(cert_uri)
    if not match:
        raise error.NotFound(
            f"Certificates at URI {cert_uri} are not supported")

    if cert_type != 'PEM':
        raise error.BadRequest(
            f"Only PEM certificates are supported, got {cert_type}")

    manager_id, device, cert_id = match.groups()

    flask.current_app.managers.get_manager(manager_id)
    flask.current_app.vmedia.replace_certificate(
        manager_id, device, cert_id, cert_string, cert_type)

    return '', 204
