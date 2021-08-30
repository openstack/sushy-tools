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

import functools

import flask


def debug(*args, **kwargs):
    flask.current_app.logger.debug(*args, **kwargs)


def info(*args, **kwargs):
    flask.current_app.logger.info(*args, **kwargs)


def warning(*args, **kwargs):
    flask.current_app.logger.warning(*args, **kwargs)


def error(*args, **kwargs):
    flask.current_app.logger.error(*args, **kwargs)


def instance_denied(**kwargs):
    deny = True

    try:
        deny = (kwargs['identity'] not in
                flask.current_app.config['SUSHY_EMULATOR_ALLOWED_INSTANCES'])

    except KeyError:
        deny = False

    finally:
        if deny:
            warning('Instance %s access denied', kwargs.get('identity'))

        return deny


def ensure_instance_access(decorated_func):
    @functools.wraps(decorated_func)
    def decorator(*args, **kwargs):
        if instance_denied(**kwargs):
            raise error.NotFound()

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
