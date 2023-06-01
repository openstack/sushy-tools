
Using Redfish emulators
=======================

The sushy-tools package includes two emulators - static and dynamic.

Static emulator could be used to serve Redfish mocks in form of static
JSON documents. Dynamic emulator relies upon `libvirt`, `OpenStack` or
`Ironic` virtualization backend to mimic nodes behind a Redfish BMC.

.. toctree::
  :maxdepth: 2

  static-emulator
  dynamic-emulator
