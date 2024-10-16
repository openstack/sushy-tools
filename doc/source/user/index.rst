
Using Redfish emulators
=======================

The sushy-tools package includes two emulators - static and dynamic.

The static emulator can be used to serve Redfish mocks in the form of static
JSON documents. The dynamic emulator relies upon the `libvirt`, `OpenStack` or
`Ironic` virtualization backends to mimic nodes behind a Redfish BMC.

.. toctree::
  :maxdepth: 2

  static-emulator
  dynamic-emulator
