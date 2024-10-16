=========================
Redfish development tools
=========================

This is a set of simple simulation tools aimed at supporting the development and
testing of the Redfish protocol implementations and, in particular, the Sushy
library (https://docs.openstack.org/sushy/). It is not designed for use outside
of development and testing environments. Please do not run sushy-tools in a
production environment of any kind.

The package ships two simulators - the static Redfish responder and the virtual
Redfish BMC (which is backed by libvirt or OpenStack cloud).

The static Redfish responder is a simple REST API server which responds with the
same things to client queries. It is effectively read-only.

The virtual Redfish BMC resembles the real Redfish-controlled bare metal machine
to some extent. Some client queries are translated to commands that actually
control VM instances simulating bare metal hardware. However, some of the
Redfish commands just return static content, never touching the virtualization
backend and in this regard, the virtual Redfish BMC is similar to the static
Redfish responder.

* Free software: Apache license
* Documentation: https://docs.openstack.org/sushy-tools
* Source: http://opendev.org/openstack/sushy-tools
* Bugs: https://storyboard.openstack.org/#!/project/openstack/sushy-tools
