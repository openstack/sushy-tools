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


update_service = flask.Blueprint(
    'UpdateService', __name__,
    url_prefix='/redfish/v1/UpdateService/')


@update_service.route('', methods=['GET'])
@api_utils.returns_json
def update_service_resource():
    api_utils.debug('Serving update service resources')

    return flask.render_template(
        'update_service.json'
    )


@update_service.route('/Actions/UpdateService.SimpleUpdate',
                      methods=['POST'])
@api_utils.returns_json
def update_service_simple_update():
    image_uri = flask.request.json.get('ImageURI')
    targets = flask.request.json.get('Targets')
    api_utils.debug('Received Targets: "%s"', targets)
    if not image_uri or not targets:
        message = "Missing ImageURI and/or Targets."
        return flask.render_template('error.json', message=message), 400

    for target in targets:
        # NOTE(janders) since we only support BIOS let's ignore Manager targets
        if "Manager" in target:
            message = "Manager is not currently a supported Target."
            return flask.render_template('error.json', message=message), 400

        identity = target.rsplit('/', 1)[-1]
        # NOTE(janders) iterate over the array? narrow down which one is needed
        # first? I suppose the former since we may want to update multiple
        api_utils.debug('Fetching BIOS information for System "%s"',
                        target)
        try:
            versions = flask.current_app.systems.get_versions(identity)

        except error.NotSupportedError as ex:
            api_utils.warning(
                'System failed to fetch BIOS information with exception %s',
                ex)
            message = "Failed fetching BIOS information"
            return flask.render_template('error.json', message=message), 500

        bios_version = versions.get('BiosVersion')

        api_utils.debug('Current BIOS version for System "%s" is "%s" ,'
                        'attempting upgrade.',
                        target, bios_version)

        bios_version = bios_version.split('.')
        bios_version[1] = str(int(bios_version[1]) + 1)
        bios_version = '.'.join(bios_version)
        firmware_versions = {"BiosVersion": bios_version}

        try:
            flask.current_app.systems.set_versions(identity, firmware_versions)
        except error.NotSupportedError as ex:
            api_utils.warning('System failed to update bios with exception %s',
                              ex)
            message = "Failed updating BIOS version"
            return flask.render_template('error.json', message=message), 500

        api_utils.info(
            'Emulated BIOS upgrade has been successful for '
            'System %s, new version is "%s".', target, bios_version)
    return '', 204, {'Location': '/redfish/v1/TaskService/Tasks/42'}
