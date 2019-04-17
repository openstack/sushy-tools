
Virtual Redfish BMC
===================

The Virtual Redfish BMC is functionally similar to the
`Virtual BMC <https://opendev.org/openstack/virtualbmc>`_ tool
except that the frontend protocol is Redfish rather than IPMI. The Redfish
commands coming from the client are handled by one or more resource-specific
drivers.

Systems resource
----------------

For *Systems* resource, emulator maintains two drivers relying on
a virtualization backend to emulate bare metal machines by means of
virtual machines.

The following sections will explain how to configure and use
each of these drivers.

Systems resource driver: libvirt
++++++++++++++++++++++++++++++++

First thing you need is to set up some libvirt-managed virtual machines
(AKA domains) to manipulate. The following command will create a new
virtual machine i.e. libvirt domain `vbmc-node`:

.. code-block:: bash

   tmpfile=$(mktemp /tmp/sushy-domain.XXXXXX)
   virt-install \
      --name vbmc-node \
      --ram 1024 \
      --disk size=1 \
      --vcpus 2 \
      --os-type linux \
      --os-variant fedora28 \
      --graphics vnc \
      --print-xml > $tmpfile
   virsh define --file $tmpfile
   rm $tmpfile

Next you can fire up the Redfish virtual BMC which will listen at
*localhost:8000* (by default):

.. code-block:: bash

   sushy-emulator
    * Running on http://localhost:8000/ (Press CTRL+C to quit)

Now you should be able to see your libvirt domain among the Redfish
*Systems*:

.. code-block:: bash

   curl http://localhost:8000/redfish/v1/Systems/
   {
       "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
       "Name": "Computer System Collection",
       "Members@odata.count": 1,
       "Members": [

               {
                   "@odata.id": "/redfish/v1/Systems/vbmc-node"
               }

       ],
       "@odata.context": "/redfish/v1/$metadata#ComputerSystemCollection.ComputerSystemCollection",
       "@odata.id": "/redfish/v1/Systems",
       "@Redfish.Copyright": "Copyright 2014-2016 Distributed Management Task Force, Inc. (DMTF). For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright."
   }

You should be able to flip its power state via the Redfish call:

.. code-block:: bash

   curl -d '{"ResetType":"On"}' \
       -H "Content-Type: application/json" -X POST \
        http://localhost:8000/redfish/v1/Systems/vbmc-node/Actions/ComputerSystem.Reset

   curl -d '{"ResetType":"ForceOff"}' \
       -H "Content-Type: application/json" -X POST \
        http://localhost:8000/redfish/v1/Systems/vbmc-node/Actions/ComputerSystem.Reset

You can have as many domains as you need. The domains can be concurrently
managed over Redfish and some other tool like *Virtual BMC*.

UEFI boot
~~~~~~~~~

By default, `legacy` or `BIOS` mode is used to boot the instance. However,
libvirt domain can be configured to boot via UEFI firmware. This process
requires additional preparation on the host side.

On the host you need to have OVMF firmware binaries installed. Fedora users
could pull them as `edk2-ovmf` RPM. On Ubuntu, `apt-get install ovmf` should
do the job.

Then you need to create a VM by running `virt-install` with the `--boot uefi`
option:

Example:

.. code-block:: bash

   tmpfile=$(mktemp /tmp/sushy-domain.XXXXXX)
   virt-install \
      --name vbmc-node \
      --ram 1024 \
      --boot uefi \
      --disk size=1 \
      --vcpus 2 \
      --os-type linux \
      --os-variant fedora28 \
      --graphics vnc \
      --print-xml > $tmpfile
   virsh define --file $tmpfile
   rm $tmpfile

This will create a new `libvirt` domain with path to OVMF images properly
configured. Let's take a note on the path to the blob:

.. code-block:: bash

    $ virsh dumpxml vbmc-node | grep loader
    <loader readonly='yes' type='pflash'>/usr/share/edk2/ovmf/OVMF_CODE.fd</loader>

Because now we need to add this path to emulator's configuration matching
VM architecture we are running. Make a copy of stock configuration file
and edit it accordingly:

.. code-block:: bash

    $ cat sushy-tools/doc/source/admin/emulator.conf
    ...
    SUSHY_EMULATOR_BOOT_LOADER_MAP = {
        'Uefi': {
            'x86_64': '/usr/share/edk2/ovmf/OVMF_CODE.fd',
            ...
    }
    ...

Now you can run `sushy-emulator` with the updated configuration file:

.. code-block:: bash

    sushy-emulator --config emulator.conf

.. note::

   The images you will serve to your VMs need to be UEFI-bootable.

Systems resource driver: OpenStack
++++++++++++++++++++++++++++++++++

You can use an OpenStack cloud instances to simulate Redfish-managed
baremetal machines. This setup is known under the name of
`OpenStack Virtual Baremetal <http://openstack-virtual-baremetal.readthedocs.io/en/latest/>`_.
We will largely re-use its OpenStack infrastructure and configuration
instructions. After all, what we are trying to do here is to set up the
Redfish emulator alongside the
`openstackbmc <https://github.com/cybertron/openstack-virtual-baremetal/blob/master/openstack_virtual_baremetal/openstackbmc.py>`_
tool which is used for exactly the same purpose at OVB with the only
difference that it works over the *IPMI* protocol as opposed to *Redfish*.

The easiest way is probably to set up your OpenStack Virtual Baremetal cloud
by following
`its instructions <http://openstack-virtual-baremetal.readthedocs.io/en/latest/>`_.

Once your OVB cloud operational, you log into the *BMC* instance and
:ref:`set up sushy-tools <installation>` there.

Next you can invoke the Redfish virtual BMC pointing it to your OVB cloud:

.. code-block:: bash

   sushy-emulator --os-cloud rdo-cloud
    * Running on http://localhost:8000/ (Press CTRL+C to quit)

By this point you should be able to see your OpenStack instances among the
Redfish *Systems*:

.. code-block:: bash

   curl http://localhost:8000/redfish/v1/Systems/
   {
       "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
       "Name": "Computer System Collection",
       "Members@odata.count": 1,
       "Members": [

               {
                   "@odata.id": "/redfish/v1/Systems/vbmc-node"
               }

       ],
       "@odata.context": "/redfish/v1/$metadata#ComputerSystemCollection.ComputerSystemCollection",
       "@odata.id": "/redfish/v1/Systems",
       "@Redfish.Copyright": "Copyright 2014-2016 Distributed Management Task Force, Inc. (DMTF). For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright."
   }

And flip its power state via the Redfish call:

.. code-block:: bash

   curl -d '{"ResetType":"On"}' \
       -H "Content-Type: application/json" -X POST \
        http://localhost:8000/redfish/v1/Systems/vbmc-node/Actions/ComputerSystem.Reset

   curl -d '{"ResetType":"ForceOff"}' \
       -H "Content-Type: application/json" -X POST \
        http://localhost:8000/redfish/v1/Systems/vbmc-node/Actions/ComputerSystem.Reset

You can have as many OpenStack instances as you need. The instances can be
concurrently managed over Redfish and functionally similar tools.

Managers resource
-----------------

For emulating *Managers* resource, the user can statically configure
one or more imaginary Managers. The first configured manager will
pretend to manage all *Systems*, *Chassis* and potentially other
resources.

.. code-block:: python

    SUSHY_EMULATOR_MANAGERS = [
        {
            "Id": "BMC",
            "Name": "Manager",
            "ServiceEntryPointUUID": "92384634-2938-2342-8820-489239905423",
            "UUID": "58893887-8974-2487-2389-841168418919"
        }
    ]

By default a single manager with be configured automatically.

Managers will be revealed when querying the *Managers* resource
directly, as well as other resources they manage or have some
other relations.

.. code-block:: bash

    curl http://localhost:8000/redfish/v1/Managers
    {
        "@odata.type": "#ManagerCollection.ManagerCollection",
        "Name": "Manager Collection",
        "Members@odata.count": 1,
        "Members": [

              {
                  "@odata.id": "/redfish/v1/Managers/58893887-8974-2487-2389-841168418919"
              }

        ],
        "@odata.context": "/redfish/v1/$metadata#ManagerCollection.ManagerCollection",
        "@odata.id": "/redfish/v1/Managers",
        "@Redfish.Copyright": "Copyright 2014-2017 Distributed Management Task Force, Inc. (DMTF). For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright."

Chassis resource
----------------

For emulating *Chassis* resource, the user can statically configure
one or more imaginary chassis. All existing resources (e.g. *Systems*,
*Managers*) will pretend to reside in the first chassis.

.. code-block:: python

    SUSHY_EMULATOR_CHASSIS = [
        {
            "Id": "Chassis",
            "Name": "Chassis",
            "UUID": "48295861-2522-3561-6729-621118518810"
        }
    ]

By default a single chassis with be configured automatically.

Chassis will be revealed when querying the *Chassis* resource
directly, as well as other resources they manage or have some
other relations.

.. code-block:: bash

    curl http://localhost:8000/redfish/v1/Chassis
    {
        "@odata.type": "#ChassisCollection.ChassisCollection",
        "Name": "Chassis Collection",
        "Members@odata.count": 1,
        "Members": [
              {
                  "@odata.id": "/redfish/v1/Chassis/48295861-2522-3561-6729-621118518810"
              }
        ],
        "@odata.context": "/redfish/v1/$metadata#ChassisCollection.ChassisCollection",
        "@odata.id": "/redfish/v1/Chassis",
        "@Redfish.Copyright": "Copyright 2014-2017 Distributed Management Task Force, Inc. (DMTF). For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright."
