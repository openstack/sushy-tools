
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


Simple Storage resource
~~~~~~~~~~~~~~~~~~~~~~~

For emulating the *Simple Storage* resource, some additional preparation is
required on the host side.

First, you need to create, build and start a libvirt storage pool using virsh:

.. code-block:: bash

    virsh pool-define-as testPool dir - - - - "/testPool"
    virsh pool-build testPool
    virsh pool-start testPool
    virsh pool-autostart testPool

Next, create a storage volume in the above created storage pool:

.. code-block:: bash

    virsh vol-create-as testPool testVol 1G

Next, attach the created volume to the virtual machine/domain:

.. code-block:: bash

    virsh attach-disk vbmc-node /testPool/testVol sda

Now, query the *Simple Storage* resource collection for the `vbmc-node` domain
in a closely similar format (with 'ide' and 'scsi', here, referring to the two
Redfish Simple Storage Controllers available for this domain):

.. code-block:: bash

    curl http://localhost:8000/redfish/v1/vbmc-node/SimpleStorage
    {
        "@odata.type": "#SimpleStorageCollection.SimpleStorageCollection",
        "Name": "Simple Storage Collection",
        "Members@odata.count": 2,
        "Members": [

                    {
                        "@odata.id": "/redfish/v1/Systems/vbmc-node/SimpleStorage/ide"
                    },

                    {
                        "@odata.id": "/redfish/v1/Systems/vbmc-node/SimpleStorage/scsi"
                    }

        ],
        "Oem": {},
        "@odata.context": "/redfish/v1/$metadata#SimpleStorageCollection.SimpleStorageCollection",
        "@odata.id": "/redfish/v1/Systems/vbmc-node/SimpleStorage"
    }


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

Settable boot image
~~~~~~~~~~~~~~~~~~~

The `libvirt` system emulation backend supports setting custom boot images,
so that libvirt domains (representing bare metal nodes) can boot from user
images.

This feature enables system boot from virtual media device.

The limitations:

* Only ISO images are supported

See *VirtualMedia* resource section for more information on how to perform
virtual media boot.

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

*Managers* are emulated based on systems: each *System* has a *Manager* with
the same UUID. The first (alphabetically) manager will pretend to manage all
*Chassis* and potentially other resources.

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
*Managers*, *Drives*) will pretend to reside in the first chassis.

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

Indicator resource
------------------

*IndicatorLED* resource is emulated as a persistent emulator database
record, observable and manageable by a Redfish client.

By default, *Chassis* and *Systems* resources have emulated *IndicatorLED*
sub-resource attached and *Lit*.

Non-default initial indicator state can optionally be configured
on a per-resource basis:

.. code-block:: python

    SUSHY_EMULATOR_INDICATOR_LEDS = {
        "48295861-2522-3561-6729-621118518810": "Blinking"
    }

Indicator LEDs will be revealed when querying any resource having
*IndicatorLED*:

.. code-block:: bash

    $ curl http://localhost:8000/redfish/v1/Chassis/48295861-2522-3561-6729-621118518810
    {
        "@odata.type": "#Chassis.v1_5_0.Chassis",
        "Id": "48295861-2522-3561-6729-621118518810",
        "Name": "Chassis",
        "UUID": "48295861-2522-3561-6729-621118518810",
        ...
        "IndicatorLED": "Lit",
        ...
    }

Redfish client can turn *IndicatorLED* into a different state:

.. code-block:: bash

   curl -d '{"IndicatorLED": "Blinking"}' \
       -H "Content-Type: application/json" -X PATCH \
        http://localhost:8000/redfish/v1/Chassis/48295861-2522-3561-6729-621118518810

Virtual media resource
----------------------

Virtual Media resource is emulated as a persistent emulator database
record, observable and manageable by a Redfish client.

By default, *VirtualMedia* resource includes two emulated removable
devices: *Cd* and *Floppy*. Each *Manager* resource gets its own collection
of virtual media devices as a *VirtualMedia* sub-resource.

If currently used *Systems* resource emulation driver supports setting
boot image, *VirtualMedia* resource will apply inserted image onto
all the systems being managed by this manager. Setting system boot source
to *Cd* and boot mode to *Uefi* will cause the system to boot from
virtual media image.

User can change virtual media devices and their properties through
emulator configuration:

.. code-block:: python

    SUSHY_EMULATOR_VMEDIA_DEVICES = {
        "Cd": {
            "Name": "Virtual CD",
            "MediaTypes": [
                "CD",
                "DVD"
            ]
        },
        "Floppy": {
            "Name": "Virtual Removable Media",
            "MediaTypes": [
                "Floppy",
                "USBStick"
            ]
        }
    }

Virtual Media resource will be revealed when querying Manager resource:

.. code-block:: bash

    curl -L http://localhost:8000/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia
    {
        "@odata.type": "#VirtualMediaCollection.VirtualMediaCollection",
        "Name": "Virtual Media Services",
        "Description": "Redfish-BMC Virtual Media Service Settings",
        "Members@odata.count": 2,
        "Members": [

            {
                "@odata.id": "/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia/Cd"
            },

            {
                "@odata.id": "/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia/Floppy"
            }

        ],
        "@odata.context": "/redfish/v1/$metadata#VirtualMediaCollection.VirtualMediaCollection",
        "@odata.id": "/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia",
        "@Redfish.Copyright": "Copyright 2014-2017 Distributed Management Task Force, Inc. (DMTF). For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright."
    }

Redfish client can insert a HTTP-based image into the virtual device:

.. code-block:: bash

   curl -d '{"Image":"http://localhost.localdomain/mini.iso",\
             "Inserted": true}' \
        -H "Content-Type: application/json" \
        -X POST \
        http://localhost:8000/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia

.. note::

   All systems being managed by this manager and booting from their
   corresponding removable media device (e.g. cdrom or fd) will boot the
   image inserted into manager's virtual media device.

.. warning::

   System boot from virtual media only works if *System* resource emulation
   driver supports setting boot image.

Redfish client can eject image from virtual media device:

.. code-block:: bash

   curl -d '{}' \
        -H "Content-Type: application/json" \
        -X POST \
        http://localhost:8000/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia

Virtual media boot
++++++++++++++++++

To boot a system from a virtual media device the client first needs to figure
out which manager is responsible for the system of interest:

.. code-block:: bash

    $ curl http://localhost:8000/redfish/v1/Systems/281c2fc3-dd34-439a-9f0f-63df45e2c998
    {
    ...
    "Links": {
        "Chassis": [
        ],
        "ManagedBy": [
            {
                "@odata.id": "/redfish/v1/Managers/58893887-8974-2487-2389-841168418919"
            }
        ]
    },
    ...

Exploring the Redfish API links, the client can learn the virtual media devices
being offered:

.. code-block:: bash

    $ curl http://localhost:8000/redfish/v1/Managers/58893887-894-2487-2389-841168418919/VirtualMedia
    ...
    "Members": [
    {
        "@odata.id": "/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia/Cd"
    },
    ...

Knowing virtual media device name, the client can check out its present state:

.. code-block:: bash

    $ curl http://localhost:8000/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia/Cd
    {
        ...
        "Name": "Virtual CD",
        "MediaTypes": [
            "CD",
            "DVD"
        ],
        "Image": "",
        "ImageName": "",
        "ConnectedVia": "URI",
        "Inserted": false,
        "WriteProtected": false,
        ...

Assuming `http://localhost/var/tmp/mini.iso` URL points to a bootable UEFI or
hybrid ISO, the following Redfish REST API call will insert the image into the
virtual CD drive:

.. code-block:: bash

    $ curl -d \
        '{"Image":"http:://localhost/var/tmp/mini.iso", "Inserted": true}' \
         -H "Content-Type: application/json" \
         -X POST \
         http://localhost:8000/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia

Querying again, the emulator should have it in the drive:

.. code-block:: bash

    $ curl http://localhost:8000/redfish/v1/Managers/58893887-8974-2487-2389-841168418919/VirtualMedia/Cd
    {
        ...
        "Name": "Virtual CD",
        "MediaTypes": [
            "CD",
            "DVD"
        ],
        "Image": "http://localhost/var/tmp/mini.iso",
        "ImageName": "mini.iso",
        "ConnectedVia": "URI",
        "Inserted": true,
        "WriteProtected": true,
        ...

Next, the node needs to be configured to boot from its local CD drive
over UEFI:

.. code-block:: bash

   $ curl -X PATCH -H 'Content-Type: application/json' \
       -d '{
         "Boot": {
             "BootSourceOverrideTarget": "Cd",
             "BootSourceOverrideMode": "Uefi",
             "BootSourceOverrideEnabled": "Continuous"
         }
       }' \
       http://localhost:8000/redfish/v1/Systems/281c2fc3-dd34-439a-9f0f-63df45e2c998

By this point the system will boot off the virtual CD drive when powering it on:

.. code-block:: bash

   curl -d '{"ResetType":"On"}' \
       -H "Content-Type: application/json" -X POST \
        http://localhost:8000/redfish/v1/Systems/281c2fc3-dd34-439a-9f0f-63df45e2c998/Actions/ComputerSystem.Reset

.. note::

   ISO files to boot from must be UEFI-bootable, libvirtd should be running on the same
   machine with sushy-emulator.

Storage resource
----------------

For emulating *Storage* resource for a System of choice, the
user can statically configure one or more imaginary storage
instances along with the corresponding storage controllers which
are also imaginary.

The IDs of the imaginary drives associated to a *Storage* resource
can be provided as a list under *Drives*.

The *Storage* instances are keyed by the UUIDs of the System they
belong to.

.. code-block:: python

    SUSHY_EMULATOR_STORAGE = {
        "da69abcc-dae0-4913-9a7b-d344043097c0": [
            {
                "Id": "1",
                "Name": "Local Storage Controller",
                "StorageControllers": [
                    {
                        "MemberId": "0",
                        "Name": "Contoso Integrated RAID",
                        "SpeedGbps": 12
                    }
                ],
                "Drives": [
                    "32ADF365C6C1B7BD"
                ]
            }
        ]
    }

The Storage resources can be revealed by querying Storage resource
for the corresponding System directly.

.. code-block:: bash

    curl http://localhost:8000/redfish/v1/Systems/da69abcc-dae0-4913-9a7b-d344043097c0/Storage
    {
        "@odata.type": "#StorageCollection.StorageCollection",
        "Name": "Storage Collection",
        "Members@odata.count": 1,
        "Members": [
            {
                "@odata.id": "/redfish/v1/Systems/da69abcc-dae0-4913-9a7b-d344043097c0/Storage/1"
            }
        ],
        "Oem": {},
        "@odata.context": "/redfish/v1/$metadata#StorageCollection.StorageCollection",
        "@odata.id": "/redfish/v1/Systems/da69abcc-dae0-4913-9a7b-d344043097c0/Storage"
    }

Drive resource
++++++++++++++

For emulating the *Drive* resource, the user can statically configure
one or more drives.

The *Drive* instances are keyed in a composite manner using
(System_UUID, Storage_ID) where System_UUID is the UUID of the System
and Storage_ID is the ID of the Storage resource to which that particular
drive belongs.

.. code-block:: python

    SUSHY_EMULATOR_DRIVES = {
        ("da69abcc-dae0-4913-9a7b-d344043097c0", "1"): [
            {
                "Id": "32ADF365C6C1B7BD",
                "Name": "Drive Sample",
                "CapacityBytes": 899527000000,
                "Protocol": "SAS"
            }
        ]
    }

The *Drive* resource can be revealed by querying it via the System and the
Storage resource it belongs to.

.. code-block:: bash

    curl http://localhost:8000/redfish/v1/Systems/da69abcc-dae0-4913-9a7b-d344043097c0/Storage/1/Drives/32ADF365C6C1B7BD
    {
        ...
        "Id": "32ADF365C6C1B7BD",
        "Name": "Drive Sample",
        "Model": "C123",
        "Revision": "100A",
        "CapacityBytes": 899527000000,
        "FailurePredicted": false,
        "Protocol": "SAS",
        "MediaType": "HDD",
        "Manufacturer": "Contoso",
        "SerialNumber": "1234570",
        ...
    }

Storage Volume resource
+++++++++++++++++++++++

The *Volume* resource is emulated as a persistent emulator database
record, backed by the libvirt virtualization backend of the dynamic
Redfish emulator.

Only the volumes specified in the config file or created via a POST request
are allowed to be emulated upon by the emulator and appear as libvirt volumes
in the libvirt virtualization backend. Volumes other than these can neither be
listed nor deleted.

To allow libvirt volumes to be emulated upon, they need to be specified
in the configuration file in the following format (keyed compositely by
the System UUID and the Storage ID):

.. code-block:: python

    SUSHY_EMULATOR_VOLUMES = {
        ('da69abcc-dae0-4913-9a7b-d344043097c0', '1'): [
            {
                "libvirtPoolName": "sushyPool",
                "libvirtVolName": "testVol",
                "Id": "1",
                "Name": "Sample Volume 1",
                "VolumeType": "Mirrored",
                "CapacityBytes": 23748
            },
            {
                "libvirtPoolName": "sushyPool",
                "libvirtVolName": "testVol1",
                "Id": "2",
                "Name": "Sample Volume 2",
                "VolumeType": "StripedWithParity",
                "CapacityBytes": 48395
            }
        ]
    }

The Volume resources can be revealed by querying Volumes resource
for the corresponding System and the Storage.

.. code-block:: bash

    curl http://localhost:8000/redfish/v1/Systems/da69abcc-dae0-4913-9a7b-d344043097c0/Storage/1/Volumes
    {
        "@odata.type": "#VolumeCollection.VolumeCollection",
        "Name": "Storage Volume Collection",
        "Members@odata.count": 2,
        "Members": [
            {
                "@odata.id": "/redfish/v1/Systems/da69abcc-dae0-4913-9a7b-d344043097c0/Storage/1/Volumes/1"
            },
            {
                "@odata.id": "/redfish/v1/Systems/da69abcc-dae0-4913-9a7b-d344043097c0/Storage/1/Volumes/2"
            }
        ],
        "@odata.context": "/redfish/v1/$metadata#VolumeCollection.VolumeCollection",
        "@odata.id": "/redfish/v1/Systems/da69abcc-dae0-4913-9a7b-d344043097c0/Storage/1/Volumes",
    }

A new volume can also be created in the libvirt backend via a POST request
on a Volume Collection:

.. code-block:: bash

    curl -d '{"Name": "SampleVol",\
             "VolumeType": "Mirrored",\
             "CapacityBytes": 74859}' \
        -H "Content-Type: application/json" \
        -X POST \
        http://localhost:8000/redfish/v1/Systems/da69abcc-dae0-4913-9a7b-d344043097c0/Storage/1/Volumes
