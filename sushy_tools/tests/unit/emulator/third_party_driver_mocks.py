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

"""This module detects whether third-party libraries, utilized by third-party
drivers, are present on the system. If they are not, it mocks them and tinkers
with sys.modules so that the drivers can be loaded by unit tests, and the unit
tests can continue to test the functionality of those drivers without the
respective external libraries' actually being present.

Any external library required by a third-party driver should be mocked here.
Current list of mocked libraries:

- python-libvirt
- python-openstacksdk
"""

import sys

import mock
import six

from sushy_tools.tests.unit.emulator import third_party_driver_mock_specs \
    as mock_specs

try:
    import libvirt

except ImportError:
    libvirt = None

try:
    import openstack

except ImportError:
    openstack = None


if not libvirt:
    libvirt = mock.MagicMock(spec_set=mock_specs.LIBVIRT_SPEC)
    sys.modules['libvirt'] = libvirt
    libvirt.libvirtError = type(
        'libvirtError', (Exception,), {})

if 'sushy_tools.emulator.drivers.libvirtdriver' in sys.modules:
    six.moves.reload_module(
        sys.modules['sushy_tools.emulator.drivers.libvirtdriver'])


if not openstack:
    openstack = mock.MagicMock(spec_set=mock_specs.OPENSTACKSDK_SPEC)
    sys.modules['openstack'] = openstack

if 'sushy_tools.emulator.drivers.novadriver' in sys.modules:
    six.moves.reload_module(
        sys.modules['sushy_tools.emulator.drivers.novadriver'])
