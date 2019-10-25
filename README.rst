=========================
Redfish development tools
=========================

This is a set of simple simulation tools aiming at supporting the
development and testing of the Redfish protocol implementations and,
in particular, Sushy library (https://docs.openstack.org/sushy/).

The package ships two simulators - static Redfish responder and
virtual Redfish BMC that is backed by libvirt or OpenStack cloud.

The static Redfish responder is a simple REST API server which
responds the same things to client queries. It is effectively
read-only.

The virtual Redfish BMC resembles the real Redfish-controlled bare-metal
machine to some extent. Some client queries are translated to commands that
actually control VM instances simulating bare metal hardware. However some
of the Redfish commands just return static content never touching the
virtualization backend and, for that matter, virtual Redfish BMC is similar
to the static Redfish responser.

* Free software: Apache license
* Documentation: https://docs.openstack.org/sushy-tools
* Source: http://opendev.org/openstack/sushy-tools
* Bugs: https://storyboard.openstack.org/#!/project/openstack/sushy-tools
