
Using Redfish emulators
=======================

The sushy-tools package includes two emulators - static and dynamic.

Static emulator could be used to serve Redfish mocks in form of static
JSON documents. Dynamic emulator relies upon either `libvirt` or `OpenStack`
virtualization backend to mimic baremetal nodes behind Redfish BMC.

.. toctree::
  :maxdepth: 2

  static-emulator
  dynamic-emulator
