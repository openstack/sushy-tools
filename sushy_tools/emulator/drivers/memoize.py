# Copyright 2018 Red Hat, Inc.
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
from functools import wraps


def memoize(permanent_cache=None):
    """Cache the return value of the decorated method.

    :param permanent_cache: a `dict` like object to use as a cache.
        If not given, the `._cache` attribute would be added to
        the object of the decorated method pointing to a newly
        created `dict`.
    :return: decorated function
    """

    def decorator(method):

        @wraps(method)
        def wrapped(self, *args, **kwargs):
            if permanent_cache is None:
                try:
                    cache = self._cache

                except AttributeError:
                    cache = self._cache = {}

            else:
                cache = permanent_cache

            method_cache = cache.setdefault(method, {})

            key = frozenset(args), frozenset(kwargs)

            try:
                return method_cache[key]

            except KeyError:
                rv = method(self, *args, **kwargs)
                method_cache[key] = rv
                return rv

        return wrapped

    return decorator
