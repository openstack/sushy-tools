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


account_service = flask.Blueprint(
    'AccountService', __name__,
    url_prefix='/redfish/v1/AccountService')


def _get_accounts():
    accounts = flask.current_app.accounts
    if accounts is None:
        raise error.FeatureNotAvailable(
            'AccountService (no SUSHY_EMULATOR_AUTH_FILE configured)')
    return accounts


@account_service.route('', methods=['GET'])
@api_utils.returns_json
def account_service_resource():
    _get_accounts()

    api_utils.debug('Serving account service')

    return flask.render_template('account_service.json')


@account_service.route('/Accounts', methods=['GET', 'POST'])
@api_utils.returns_json
def account_collection_resource():
    accounts = _get_accounts()

    if flask.request.method == 'GET':
        api_utils.debug('Serving accounts list')

        return flask.render_template(
            'account_collection.json', accounts=accounts.accounts)

    # creating an account requires editing to be enabled
    accounts.check_editing_allowed()

    data = flask.request.json or {}
    username = data.get('UserName')
    password = data.get('Password')

    if not username or not password:
        raise error.BadRequest(
            'Both UserName and Password are required to create an account')

    # NOTE: RoleId is accepted but ignored: the emulator does not
    # distinguish between user roles.
    account_id = accounts.add_account(username, password)

    api_utils.info('Created user account "%s" with ID %s',
                   username, account_id)

    return flask.Response(
        status=201,
        headers={'Location': f'/redfish/v1/AccountService/Accounts/'
                             f'{account_id}'})


@account_service.route('/Accounts/<identity>', methods=['GET', 'PATCH',
                                                        'DELETE'])
@api_utils.returns_json
def account_resource(identity):
    accounts = _get_accounts()

    if flask.request.method == 'GET':
        api_utils.debug('Serving user account "%s"', identity)

        return flask.render_template(
            'account.json', account=accounts.get_account(identity))

    # changing or deleting an account requires editing to be enabled
    accounts.check_editing_allowed()

    if flask.request.method == 'PATCH':
        password = (flask.request.json or {}).get('Password')
        if not password:
            raise error.BadRequest('PATCH only works for the Password '
                                   'element')

        accounts.set_password(identity, password)

        api_utils.info('Changed password for user account "%s"', identity)

        return '', 204

    elif flask.request.method == 'DELETE':
        accounts.delete_account(identity)

        api_utils.info('Deleted user account "%s"', identity)

        return '', 204
