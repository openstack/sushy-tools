.. _installation:

Installation
============

The sushy-tools Python package can be downloaded and installed with *pip*:

.. code-block:: bash

   $ pip install sushy-tools

Or, if you have virtualenvwrapper installed:

.. code-block:: bash

   $ mkvirtualenv sushy-tools
   $ pip install sushy-tools

The *Virtual Redfish BMC* tool relies upon one or more hypervisors to mimic
bare metal nodes. Depending on the virtualization backend you are planning
to use, certain third-party dependencies should also be installed.

The dependencies for the virtualization backends that should be installed
for the corresponding drivers to become operational are:

* `libvirt-python` for the libvirt driver
* `openstacksdk` for the nova driver

.. note::

   The dependencies for at least one virtualization backend should be
   satisfied to have *Virtual Redfish BMC* emulator operational.
