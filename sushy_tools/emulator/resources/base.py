# Copyright 2019 Red Hat, Inc.
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


class DriverBase(object):
    """Common base for emulated Redfish resource drivers"""

    @classmethod
    def initialize(cls, config, logger, *args, **kwargs):
        """Initialize class attributes

        Since drivers may need to cache thing short-term. The emulator
        instantiates the driver every time it serves a client query.

        Driver objects can cache whenever it makes sense for the duration
        of a single session. It is guaranteed that the driver object will
        never be reused for any other session.

        The `initialize` method is provided to set up the driver in a way
        that would affect all the subsequent sessions.

        :params config: system configuration dict
        :params logger: system logger object
        :params *args: driver-specific parameters
        :params **kwargs: driver-specific parameters
        :returns: initialized driver class
        """
        return cls
