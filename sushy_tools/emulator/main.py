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
import json
import os
import signal
import ssl
import sys

import flask
from werkzeug import exceptions as wz_exc

from sushy_tools.emulator import api_utils
from sushy_tools.emulator import auth_basic
from sushy_tools.emulator.controllers import certificate_service as certctl
from sushy_tools.emulator.controllers import update_service as usctl
from sushy_tools.emulator.controllers import virtual_media as vmctl
from sushy_tools.emulator import memoize
from sushy_tools.emulator.resources import chassis as chsdriver
from sushy_tools.emulator.resources import drives as drvdriver
from sushy_tools.emulator.resources import indicators as inddriver
from sushy_tools.emulator.resources import managers as mgrdriver
from sushy_tools.emulator.resources import storage as stgdriver
from sushy_tools.emulator.resources.systems import fakedriver
from sushy_tools.emulator.resources.systems import ironicdriver
from sushy_tools.emulator.resources.systems import libvirtdriver
from sushy_tools.emulator.resources.systems import novadriver
from sushy_tools.emulator.resources import vmedia as vmddriver
from sushy_tools.emulator.resources import volumes as voldriver
from sushy_tools import error


def _render_error(message):
    return {
        "error": {
            "code": "Base.1.0.GeneralError",
            "message": message,
            "@Message.ExtendedInfo": [
                {
                    "@odata.type": ("/redfish/v1/$metadata"
                                    "#Message.1.0.0.Message"),
                    "MessageId": "Base.1.0.GeneralError"
                }
            ]
        }
    }


class RedfishAuthMiddleware(auth_basic.BasicAuthMiddleware):

    _EXCLUDE_PATHS = frozenset(['', 'redfish', 'redfish/v1'])

    def __call__(self, env, start_response):
        path = env.get('PATH_INFO', '')
        if path.strip('/') in self._EXCLUDE_PATHS:
            return self.app(env, start_response)
        else:
            return super().__call__(env, start_response)

    def format_exception(self, e):
        response = super().format_exception(e)
        response.json_body = _render_error(str(e))
        return response


class Application(flask.Flask):

    def __init__(self):
        super().__init__(__name__)
        # Turn off strict_slashes on all routes
        self.url_map.strict_slashes = False
        # This is needed for WSGI since it cannot process argv
        self.configure(config_file=os.environ.get('SUSHY_EMULATOR_CONFIG'))

    def configure(self, config_file=None, extra_config=None):
        if config_file:
            self.config.from_pyfile(os.path.abspath(config_file))
        if extra_config:
            self.config.update(extra_config)

        auth_file = self.config.get("SUSHY_EMULATOR_AUTH_FILE")
        if auth_file and not isinstance(self.wsgi_app, RedfishAuthMiddleware):
            self.wsgi_app = RedfishAuthMiddleware(self.wsgi_app, auth_file)

        feature_set = self.config.get('SUSHY_EMULATOR_FEATURE_SET', 'full')
        if feature_set not in ('full', 'vmedia', 'minimum'):
            raise RuntimeError(f"Invalid feature set {self.feature_set}")

    @property
    def feature_set(self):
        return self.config.get('SUSHY_EMULATOR_FEATURE_SET', 'full')

    def render_template(self, template_name, /, **params):
        params.setdefault('feature_set', self.feature_set)
        return flask.render_template(template_name, **params)

    @property
    @memoize.memoize()
    def systems(self):
        fake = self.config.get('SUSHY_EMULATOR_FAKE_DRIVER')
        os_cloud = self.config.get('SUSHY_EMULATOR_OS_CLOUD')
        ironic_cloud = self.config.get('SUSHY_EMULATOR_IRONIC_CLOUD')

        if fake:
            result = fakedriver.FakeDriver.initialize(
                self.config, self.logger)()

        elif os_cloud:
            if not novadriver.is_loaded:
                self.logger.error('Nova driver not loaded')
                sys.exit(1)

            result = novadriver.OpenStackDriver.initialize(
                self.config, self.logger, os_cloud)()

        elif ironic_cloud:
            if not ironicdriver.is_loaded:
                self.logger.error('Ironic driver not loaded')
                sys.exit(1)

            result = ironicdriver.IronicDriver.initialize(
                self.config, self.logger, ironic_cloud)()

        else:
            if not libvirtdriver.is_loaded:
                self.logger.error('libvirt driver not loaded')
                sys.exit(1)

            libvirt_uri = self.config.get('SUSHY_EMULATOR_LIBVIRT_URI', '')

            result = libvirtdriver.LibvirtDriver.initialize(
                self.config, self.logger, libvirt_uri)()

        self.logger.debug('Initialized system resource backed by %s driver',
                          result)
        return result

    @property
    @memoize.memoize()
    def managers(self):
        return mgrdriver.FakeDriver(self.config, self.logger,
                                    self.systems, self.chassis)

    @property
    @memoize.memoize()
    def chassis(self):
        return chsdriver.StaticDriver(self.config, self.logger)

    @property
    @memoize.memoize()
    def indicators(self):
        return inddriver.StaticDriver(self.config, self.logger)

    @property
    @memoize.memoize()
    def vmedia(self):
        os_cloud = self.config.get('SUSHY_EMULATOR_OS_CLOUD')
        if os_cloud:
            return vmddriver.OpenstackDriver(self.config, self.logger,
                                             self.systems)
        return vmddriver.StaticDriver(self.config, self.logger)

    @property
    @memoize.memoize()
    def storage(self):
        return stgdriver.StaticDriver(self.config, self.logger)

    @property
    @memoize.memoize()
    def drives(self):
        return drvdriver.StaticDriver(self.config, self.logger)

    @property
    @memoize.memoize()
    def volumes(self):
        return voldriver.StaticDriver(self.config, self.logger)


app = Application()
app.register_blueprint(certctl.certificate_service)
app.register_blueprint(vmctl.virtual_media)
app.register_blueprint(usctl.update_service)


@app.errorhandler(Exception)
@api_utils.returns_json
def all_exception_handler(message):
    if isinstance(message, error.AliasAccessError):
        url = flask.url_for(flask.request.endpoint, identity=message.args[0])
        return flask.redirect(url, code=307, Response=flask.Response)

    code = getattr(message, 'code', 500)
    if (isinstance(message, error.FishyError)
            or isinstance(message, wz_exc.HTTPException)):
        app.logger.debug(
            'Request failed with %s: %s', message.__class__.__name__, message)
    else:
        app.logger.exception(
            'Unexpected %s: %s', message.__class__.__name__, message)

    return flask.render_template('error.json', message=message), code


@app.route('/redfish/v1/')
@api_utils.returns_json
def root_resource():
    return app.render_template('root.json')


@app.route('/redfish/v1/Chassis')
@api_utils.returns_json
def chassis_collection_resource():
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Chassis")

    app.logger.debug('Serving chassis list')

    return app.render_template(
        'chassis_collection.json',
        manager_count=len(app.chassis.chassis),
        chassis=app.chassis.chassis)


@app.route('/redfish/v1/Chassis/<identity>', methods=['GET', 'PATCH'])
@api_utils.returns_json
def chassis_resource(identity):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Chassis")

    chassis = app.chassis

    uuid = chassis.uuid(identity)

    if flask.request.method == 'GET':

        app.logger.debug('Serving resources for chassis "%s"', identity)

        # the first chassis gets all resources
        if uuid == chassis.chassis[0]:
            systems = app.systems.systems
            managers = app.managers.managers
            storage = app.storage.get_all_storage()
            drives = app.drives.get_all_drives()

        else:
            systems = []
            managers = []
            storage = []
            drives = []

        return app.render_template(
            'chassis.json',
            identity=identity,
            name=chassis.name(identity),
            uuid=uuid,
            contained_by=None,
            contained_systems=systems,
            contained_managers=managers,
            contained_chassis=[],
            managers=managers[:1],
            indicator_led=app.indicators.get_indicator_state(uuid),
            storage=storage,
            drives=drives
        )

    elif flask.request.method == 'PATCH':
        indicator_led_state = flask.request.json.get('IndicatorLED')
        if not indicator_led_state:
            return 'PATCH only works for IndicatorLED element', 400

        app.indicators.set_indicator_state(uuid, indicator_led_state)

        app.logger.info('Set indicator LED to "%s" for chassis "%s"',
                        indicator_led_state, identity)

        return '', 204


@app.route('/redfish/v1/Chassis/<identity>/Thermal', methods=['GET'])
@api_utils.returns_json
def thermal_resource(identity):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Chassis")

    chassis = app.chassis

    uuid = chassis.uuid(identity)

    app.logger.debug(
        'Serving thermal resources for chassis "%s"', identity)

    # the first chassis gets all resources
    if uuid == chassis.chassis[0]:
        systems = app.systems.systems

    else:
        systems = []

    return app.render_template(
        'thermal.json',
        chassis=identity,
        systems=systems
    )


@app.route('/redfish/v1/Managers')
@api_utils.returns_json
def manager_collection_resource():
    if app.feature_set == "minimum":
        raise error.FeatureNotAvailable("Managers")

    app.logger.debug('Serving managers list')

    return app.render_template(
        'manager_collection.json',
        manager_count=len(app.managers.managers),
        managers=app.managers.managers)


def jsonify(obj_type, obj_version, obj):
    obj.update({
        "@odata.type": "#{0}.{1}.{0}".format(obj_type, obj_version),
        "@odata.context": "/redfish/v1/$metadata#{0}.{0}".format(obj_type),
        "@Redfish.Copyright": ("Copyright 2014-2017 Distributed Management "
                               "Task Force, Inc. (DMTF). For the full DMTF "
                               "copyright policy, see http://www.dmtf.org/"
                               "about/policies/copyright.")
    })
    return flask.jsonify(obj)


@app.route('/redfish/v1/Managers/<identity>', methods=['GET', 'PATCH'])
@api_utils.returns_json
def manager_resource(identity):
    if app.feature_set == "minimum":
        raise error.FeatureNotAvailable("Managers")

    manager = app.managers.get_manager(identity)
    systems = app.managers.get_managed_systems(manager)
    chassis = app.managers.get_managed_chassis(manager)

    uuid = manager['UUID']

    if flask.request.method == "GET":
        app.logger.debug('Serving resources for manager "%s"', identity)

        result = {
            "Id": manager['Id'],
            "Name": manager.get('Name'),
            "UUID": uuid,
            "ManagerType": "BMC",
            "VirtualMedia": {
                "@odata.id": "/redfish/v1/Systems/%s/VirtualMedia" % systems[0]
                },
            "Links": {
                "ManagerForServers": [
                    {
                        "@odata.id": "/redfish/v1/Systems/%s" % system
                        }
                    for system in systems
                    ],
                "ManagerForChassis": [
                    {
                        "@odata.id": "/redfish/v1/Chassis/%s" % ch
                        }
                    for ch in chassis if app.feature_set == "full"
                    ]
                },
            "@odata.id": "/redfish/v1/Managers/%s" % uuid,
            }

        if app.feature_set == "full":
            dt_info = app.managers.get_datetime()
            result.update({
                "ServiceEntryPointUUID": manager.get('ServiceEntryPointUUID'),
                "Description": "Contoso BMC",
                "Model": "Joo Janta 200",
                "DateTime": dt_info.get(
                    "DateTime",
                    datetime.now().strftime('%Y-%m-%dT%H:%M:%S+00:00')),
                "DateTimeLocalOffset": dt_info.get(
                    "DateTimeLocalOffset", "+00:00"),
                "Status": {
                    "State": "Enabled",
                    "Health": "OK"
                    },
                "PowerState": "On",
                "FirmwareVersion": "1.00",
                })
        return jsonify('Manager', 'v1_3_1', result)

    elif flask.request.method == "PATCH":
        if app.feature_set != "full":
            raise error.MethodNotAllowed("PATCH not supported in minimum mode")
        try:
            data = flask.request.get_json()
        except wz_exc.BadRequest:
            app.logger.error(
                "PATCH method missing in /Managers/%s due to invalid JSON",
                identity
            )
            raise error.BadRequest("Request must be a valid JSON")

        new_datetime = data.get("DateTime")
        new_offset = data.get("DateTimeLocalOffset")

        app.managers.set_datetime(new_datetime, new_offset)

        app.logger.debug("Updated DateTime for manager %s", identity)

        return '', 204


@app.route('/redfish/v1/Systems')
@api_utils.returns_json
def system_collection_resource():
    systems = [system for system in app.systems.systems
               if not api_utils.instance_denied(identity=system)]

    app.logger.debug('Serving systems list')

    return app.render_template(
        'system_collection.json', system_count=len(systems), systems=systems)


@app.route('/redfish/v1/Systems/<identity>', methods=['GET', 'PATCH'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def system_resource(identity):
    uuid = app.systems.uuid(identity)
    try:
        versions = app.systems.get_versions(identity)
    except error.NotSupportedError:
        app.logger.debug('Fetching BIOS version information not supported '
                         'for system "%s"', identity)
        versions = {}

    bios_version = versions.get('BiosVersion')

    if flask.request.method == 'GET':

        app.logger.debug('Serving resources for system "%s"', identity)

        def try_get(call):
            try:
                return call(identity)
            except error.NotSupportedError:
                return None

        storage_supported = False
        if app.feature_set == 'full':
            try:
                stor = app.storage.get_storage_col(uuid)
                storage_supported = bool(stor)
            except error.FishyError:
                pass

        return app.render_template(
            'system.json',
            identity=identity,
            name=app.systems.name(identity),
            uuid=app.systems.uuid(identity),
            power_state=app.systems.get_power_state(identity),
            total_memory_gb=try_get(app.systems.get_total_memory),
            bios_version=bios_version,
            bios_supported=try_get(app.systems.get_bios),
            processors_supported=try_get(app.systems.get_processors),
            storage_supported=storage_supported,
            simple_storage_supported=try_get(
                app.systems.get_simple_storage_collection),
            total_cpus=try_get(app.systems.get_total_cpus),
            boot_source_target=app.systems.get_boot_device(identity),
            boot_source_mode=try_get(app.systems.get_boot_mode),
            uefi_mode=(try_get(app.systems.get_boot_mode) == 'UEFI'),
            managers=app.managers.get_managers_for_system(identity),
            chassis=app.chassis.chassis[:1],
            indicator_led=app.indicators.get_indicator_state(
                app.systems.uuid(identity)),
            http_boot_uri=try_get(app.systems.get_http_boot_uri)
        )

    elif flask.request.method == 'PATCH':
        boot = flask.request.json.get('Boot')
        indicator_led_state = flask.request.json.get('IndicatorLED')
        if not boot and not indicator_led_state:
            return ('PATCH only works for Boot and '
                    'IndicatorLED elements'), 400
        if indicator_led_state and app.feature_set != "full":
            raise error.FeatureNotAvailable("IndicatorLED", code=400)

        if boot:
            target = boot.get('BootSourceOverrideTarget')
            mode = boot.get('BootSourceOverrideMode')
            http_uri = boot.get('HttpBootUri')

            if http_uri and target == 'UefiHttp':

                try:
                    # Download the image
                    image_path = app.vmedia.insert_image(
                        identity, 'Cd', http_uri)
                except Exception as e:
                    app.logger.error('Unable to insert image for HttpBootUri '
                                     'request processing. Error: %s', e)
                    return 'Failed to download and attach HttpBootUri.', 400
                try:
                    # Mount it as an ISO
                    app.systems.set_boot_image(
                        uuid,
                        'Cd', boot_image=image_path,
                        write_protected=True)
                    # Set it for our emulator's API surface to return it
                    # if queried.
                except Exception as e:
                    app.logger.error('Unable to attach HttpBootUri for boot '
                                     'operation. Error: %s', e)
                    return (('Failed to set the supplied media as the next '
                             'bootdevice.'), 400)
                try:
                    app.systems.set_http_boot_uri(http_uri)
                except Exception as e:
                    app.logger.error('Unable to record HttpBootUri for boot '
                                     'operation. Error: %s', e)
                    return 'Failed to save HttpBootUri field value.', 400
                # Explicitly set to CD as in this case we will boot a an iso
                # image provided, not precisely the same, but BMC facilitated
                # HTTPBoot is a little different and the overall functionality
                # test is more important.
                target = 'Cd'

            if target == 'UefiHttp' and not http_uri:
                # Reset to Pxe, in our case, since we can't force override
                # the network boot to a specific URL. This is sort of a hack
                # but testing functionality overall is a bit more important.
                target = 'Pxe'

            if target:
                # NOTE(lucasagomes): In libvirt we always set the boot
                # device frequency to "continuous" so, we are ignoring the
                # BootSourceOverrideEnabled element here

                app.systems.set_boot_device(identity, target)

                app.logger.info('Set boot device to "%s" for system "%s"',
                                target, identity)

            if mode:
                app.systems.set_boot_mode(identity, mode)

                app.logger.info('Set boot mode to "%s" for system "%s"',
                                mode, identity)

            if not target and not mode and not http_uri:
                return ('Missing the BootSourceOverrideTarget and/or '
                        'BootSourceOverrideMode and/or HttpBootUri '
                        'element', 400)

        if indicator_led_state:
            app.indicators.set_indicator_state(
                uuid, indicator_led_state)

            app.logger.info('Set indicator LED to "%s" for system "%s"',
                            indicator_led_state, identity)

        return '', 204


@app.route('/redfish/v1/Systems/<identity>/EthernetInterfaces',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def ethernet_interfaces_collection(identity):
    if app.feature_set == "minimum":
        raise error.FeatureNotAvailable("EthernetInterfaces")

    nics = app.systems.get_nics(identity)

    return app.render_template(
        'ethernet_interfaces_collection.json', identity=identity,
        nics=nics)


@app.route('/redfish/v1/Systems/<identity>/EthernetInterfaces/<nic_id>',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def ethernet_interface(identity, nic_id):
    if app.feature_set == "minimum":
        raise error.FeatureNotAvailable("EthernetInterfaces")

    nics = app.systems.get_nics(identity)

    for nic in nics:
        if nic['id'] == nic_id:
            return app.render_template(
                'ethernet_interface.json', identity=identity, nic=nic)

    raise error.NotFound()


@app.route('/redfish/v1/Systems/<identity>/Processors',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def processors_collection(identity):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Processors")

    processors = app.systems.get_processors(identity)

    return app.render_template(
        'processors_collection.json', identity=identity,
        processors=processors)


@app.route('/redfish/v1/Systems/<identity>/Processors/<processor_id>',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def processor(identity, processor_id):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Processors")

    processors = app.systems.get_processors(identity)

    for proc in processors:
        if proc['id'] == processor_id:
            return app.render_template(
                'processor.json', identity=identity, processor=proc)

    raise error.NotFound()


@app.route('/redfish/v1/Systems/<identity>/Actions/ComputerSystem.Reset',
           methods=['POST'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def system_reset_action(identity):
    reset_type = flask.request.json.get('ResetType')
    if app.config.get('SUSHY_EMULATOR_DISABLE_POWER_OFF') is True and \
            reset_type in ('ForceOff', 'GracefulShutdown'):
        raise error.BadRequest('Can not request power off transition. It is '
                               'disabled via the '
                               'SUSHY_EMULATOR_DISABLE_POWER_OFF configuration'
                               'option.')

    app.systems.set_power_state(identity, reset_type)

    app.logger.info('System "%s" power state set to "%s"',
                    identity, reset_type)

    return '', 204


@app.route('/redfish/v1/Systems/<identity>/BIOS', methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def bios(identity):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("BIOS")

    bios = app.systems.get_bios(identity)

    app.logger.debug('Serving BIOS for system "%s"', identity)

    return app.render_template(
        'bios.json',
        identity=identity,
        bios_current_attributes=json.dumps(bios, sort_keys=True, indent=6))


@app.route('/redfish/v1/Systems/<identity>/BIOS/Settings',
           methods=['GET', 'PATCH'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def bios_settings(identity):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("BIOS")

    if flask.request.method == 'GET':
        bios = app.systems.get_bios(identity)

        app.logger.debug('Serving BIOS Settings for system "%s"', identity)

        return app.render_template(
            'bios_settings.json',
            identity=identity,
            bios_pending_attributes=json.dumps(bios, sort_keys=True, indent=6))

    elif flask.request.method == 'PATCH':
        attributes = flask.request.json.get('Attributes')

        app.systems.set_bios(identity, attributes)

        app.logger.info('System "%s" BIOS attributes "%s" updated',
                        identity, attributes)
        return '', 204


@app.route('/redfish/v1/Systems/<identity>/BIOS/Actions/Bios.ResetBios',
           methods=['POST'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def system_reset_bios(identity):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("BIOS")

    app.systems.reset_bios(identity)

    app.logger.info('BIOS for system "%s" reset', identity)

    return '', 204


@app.route('/redfish/v1/Systems/<identity>/SecureBoot',
           methods=['GET', 'PATCH'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def secure_boot(identity):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("SecureBoot")

    if flask.request.method == 'GET':
        secure = app.systems.get_secure_boot(identity)

        app.logger.debug('Serving secure boot for system "%s"', identity)

        return app.render_template(
            'secure_boot.json',
            identity=identity,
            secure_boot_enable=secure,
            secure_boot_current_boot=secure and 'Enabled' or 'Disabled')

    elif flask.request.method == 'PATCH':
        secure = flask.request.json.get('SecureBootEnable')

        app.systems.set_secure_boot(identity, secure)

        app.logger.info('System "%s" secure boot updated to "%s"',
                        identity, secure)
        return '', 204


@app.route('/redfish/v1/Systems/<identity>/SimpleStorage',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def simple_storage_collection(identity):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("SimpleStorage")

    simple_storage_controllers = (
        app.systems.get_simple_storage_collection(identity))

    return app.render_template(
        'simple_storage_collection.json', identity=identity,
        simple_storage_controllers=simple_storage_controllers)


@app.route('/redfish/v1/Systems/<identity>/SimpleStorage/<simple_storage_id>',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def simple_storage(identity, simple_storage_id):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("SimpleStorage")

    simple_storage_controllers = (
        app.systems.get_simple_storage_collection(identity))
    try:
        storage_controller = simple_storage_controllers[simple_storage_id]
    except KeyError:
        app.logger.debug('"%s" Simple Storage resource was not found')
        raise error.NotFound()
    return app.render_template('simple_storage.json', identity=identity,
                               simple_storage=storage_controller)


@app.route('/redfish/v1/Systems/<identity>/Storage',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def storage_collection(identity):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Storage")

    uuid = app.systems.uuid(identity)

    storage_col = app.storage.get_storage_col(uuid)

    return app.render_template(
        'storage_collection.json', identity=identity,
        storage_col=storage_col)


@app.route('/redfish/v1/Systems/<identity>/Storage/<storage_id>',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def storage(identity, storage_id):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Storage")

    uuid = app.systems.uuid(identity)
    storage_col = app.storage.get_storage_col(uuid)

    for stg in storage_col:
        if stg['Id'] == storage_id:
            return app.render_template(
                'storage.json', identity=identity, storage=stg)

    raise error.NotFound()


@app.route('/redfish/v1/Systems/<identity>/Storage/<stg_id>/Drives/<drv_id>',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def drive_resource(identity, stg_id, drv_id):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Storage")

    uuid = app.systems.uuid(identity)
    drives = app.drives.get_drives(uuid, stg_id)

    for drv in drives:
        if drv['Id'] == drv_id:
            return app.render_template(
                'drive.json', identity=identity, storage_id=stg_id, drive=drv)

    raise error.NotFound()


@app.route('/redfish/v1/Systems/<identity>/Storage/<storage_id>/Volumes',
           methods=['GET', 'POST'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def volumes_collection(identity, storage_id):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Storage")

    uuid = app.systems.uuid(identity)

    if flask.request.method == 'GET':

        vol_col = app.volumes.get_volumes_col(uuid, storage_id)

        vol_ids = []
        for vol in vol_col:
            vol_id = app.systems.find_or_create_storage_volume(vol)
            if not vol_id:
                app.volumes.delete_volume(uuid, storage_id, vol)
            else:
                vol_ids.append(vol_id)

        return app.render_template(
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
        new_id = app.systems.find_or_create_storage_volume(data)
        if new_id:
            app.volumes.add_volume(uuid, storage_id, data)
            app.logger.debug('New storage volume created with ID "%s"',
                             new_id)
            vol_url = ("/redfish/v1/Systems/%s/Storage/%s/"
                       "Volumes/%s" % (identity, storage_id, new_id))
            return flask.Response(status=201,
                                  headers={'Location': vol_url})


@app.route('/redfish/v1/Systems/<identity>/Storage/<stg_id>/Volumes/<vol_id>',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def volume(identity, stg_id, vol_id):
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Storage")

    uuid = app.systems.uuid(identity)
    vol_col = app.volumes.get_volumes_col(uuid, stg_id)

    for vol in vol_col:
        if vol['Id'] == vol_id:
            vol_id = app.systems.find_or_create_storage_volume(vol)
            if not vol_id:
                app.volumes.delete_volume(uuid, stg_id, vol)
            else:
                return app.render_template(
                    'volume.json', identity=identity, storage_id=stg_id,
                    volume=vol)

    raise error.NotFound()


@app.route('/redfish/v1/Registries')
@api_utils.returns_json
def registry_file_collection():
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Registries")

    app.logger.debug('Serving registry file collection')

    return app.render_template(
        'registry_file_collection.json')


@app.route('/redfish/v1/Registries/BiosAttributeRegistry.v1_0_0')
@api_utils.returns_json
def bios_attribute_registry_file():
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Registries")

    app.logger.debug('Serving BIOS attribute registry file')

    return app.render_template(
        'bios_attribute_registry_file.json')


@app.route('/redfish/v1/Registries/Messages')
@api_utils.returns_json
def message_registry_file():
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Registries")

    app.logger.debug('Serving message registry file')

    return app.render_template(
        'message_registry_file.json')


@app.route('/redfish/v1/Systems/Bios/BiosRegistry')
@api_utils.returns_json
def bios_registry():
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Registries")

    app.logger.debug('Serving BIOS registry')

    return app.render_template('bios_registry.json')


@app.route('/redfish/v1/Registries/Messages/Registry')
@api_utils.returns_json
def message_registry():
    if app.feature_set != "full":
        raise error.FeatureNotAvailable("Registries")

    app.logger.debug('Serving message registry')

    return app.render_template('message_registry.json')


@app.route('/redfish/v1/TaskService',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def simple_task_service():
    return app.render_template('task_service.json')


@app.route('/redfish/v1/TaskService/Tasks/42',
           methods=['GET'])
@api_utils.ensure_instance_access
@api_utils.returns_json
def simple_task():
    return app.render_template('task.json')


def cleanup_zombies(signum, frame):
    """Signal handler for SIGCHLD that reaps all terminated children."""
    while True:
        # os.waitpid(-1, os.WNOHANG) checks all children (-1)
        # without blocking (os.WNOHANG)
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except OSError:
            # No more children to wait for
            break

        if pid == 0:
            # No children have exited yet
            break

        # Log the reaped zombie process safely to avoid reentrancy issues
        try:
            app.logger.debug(
                "Reaped zombie process %d with status %d", pid, status)
        except RuntimeError:
            # If logging fails due to reentrancy, silently continue
            # The important part is that we reaped the zombie process
            pass


def parse_args():
    parser = argparse.ArgumentParser('sushy-emulator')
    parser.add_argument('--config',
                        type=str,
                        help='Config file path. Can also be set via '
                             'environment variable SUSHY_EMULATOR_CONFIG.')
    parser.add_argument('--debug', action='store_true',
                        help='Enables debug mode when running sushy-emulator.')
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
    parser.add_argument('--feature-set',
                        type=str, choices=['full', 'vmedia', 'minimum'],
                        help='Feature set to provide. Can also be set'
                        'via config variable SUSHY_EMULATOR_FEATURE_SET.')
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
    backend_group.add_argument('--fake', action='store_true',
                               help='Use the fake driver. Can also be set '
                                    'via environment variable '
                                    'SUSHY_EMULATOR_FAKE_DRIVER.')
    backend_group.add_argument('--ironic-cloud',
                               type=str,
                               help='Ironic cloud name. Can also be set via '
                                    'via config variable '
                                    'SUSHY_EMULATOR_IRONIC_CLOUD.')

    return parser.parse_args()


def main():

    args = parse_args()

    # Install the SIGCHLD handler to clean up zombie processes
    signal.signal(signal.SIGCHLD, cleanup_zombies)

    app.debug = args.debug

    app.configure(config_file=args.config)

    if args.os_cloud:
        app.config['SUSHY_EMULATOR_OS_CLOUD'] = args.os_cloud

    if args.libvirt_uri:
        app.config['SUSHY_EMULATOR_LIBVIRT_URI'] = args.libvirt_uri

    if args.ironic_cloud:
        app.config['SUSHY_EMULATOR_IRONIC_CLOUD'] = args.ironic_cloud

    if args.fake:
        app.config['SUSHY_EMULATOR_FAKE_DRIVER'] = True

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

    if args.feature_set:
        app.config['SUSHY_EMULATOR_FEATURE_SET'] = args.feature_set

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
