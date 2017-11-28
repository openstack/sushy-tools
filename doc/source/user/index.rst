
Using Redfish simulators
========================

The sushy-tools package includes two simulators - static Redfish responder
and cloud-backed Redfish proxy.

Static Redfish BMC
------------------

The static Redfish responder is a simple REST API server which serves
static contents down to the Redfish client. The tool emulates the
simple read-only BMC.

The user is expected to supply the Redfish-compliant contents perhaps
downloaded from the `DMTF <https://www.dmtf.org/>`_ web site. For
example,
`this .zip archive <https://www.dmtf.org/sites/default/files/standards/documents/DSP2043_1.0.0.zip>`_
includes Redfish content mocks for Redfish 1.0.0.

.. code-block:: bash

   $ curl -o DSP2043_1.0.0.zip \
        https://www.dmtf.org/sites/default/files/standards/documents/DSP2043_1.0.0.zip
   $ unzip -d mockups DSP2043_1.0.0.zip
   $ sushy-static -m mockups/public-rackmount

Once you have the static simulator running, you can use it as it was a
read-only bare-metal controller listening at *localhost:8000* (by default):

.. code-block:: bash

   $ curl http://localhost:8000/redfish/v1/Systems/
   {
       "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
       "Name": "Computer System Collection",
       "Members@odata.count": 1,
       "Members": [
           {
               "@odata.id": "/redfish/v1/Systems/437XR1138R2"
           }
       ],
       "@odata.context": "/redfish/v1/$metadata#Systems",
       "@odata.id": "/redfish/v1/Systems",
       "@Redfish.Copyright": "Copyright 2014-2016 Distributed Management Task Force, Inc. (DMTF). For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright."
   }

You can mock different Redfish versions as well as different bare-metal
machines by providing appropriate Redfish contents.

Virtual Redfish BMC
-------------------

The virtual Redfish BMC is functionally similar to the
`Virtual BMC <https://github.com/openstack/virtualbmc>`_ tool except that the
frontend protocol is Redfish rather than IPMI. The Redfish commands coming
from the client get executed against the virtualization backend. That lets
you control virtual machine instances over Redfish.

The libvirt backend
+++++++++++++++++++

First thing you need is to set up some libvirt-managed virtual machines
(AKA domains) to manipulate.

.. code-block:: bash

   # virt-install \
      --name vbm-node \
      --ram 1024 \
      --disk path=/var/kvm/images/fedora26.img,size=30 \
      --vcpus 2 \
      --os-type linux \
      --os-variant fedora25 \
      --graphics none \
      --location 'https://dl.fedoraproject.org/pub/fedora/linux/releases/26/Server/x86_64/os/'

Next you can fire up the Redfish virtual BMC which will listen at
*localhost:8000* (by default):

.. code-block:: bash

   $ sushy-emulator
    * Running on http://localhost:8000/ (Press CTRL+C to quit)

Now you should be able to see your libvirt domain among the Redfish
*Systems*:

.. code-block:: bash

   $ curl http://localhost:8000/redfish/v1/Systems/
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

You should be able to flip its power state via the Redfish call:

.. code-block:: bash

   $ curl -d '{"ResetType":"On"}' \
       -H "Content-Type: application/json" -X POST \
        http://localhost:8000/redfish/v1/Systems/vbmc-node/Actions/ComputerSystem.Reset

   $ curl -d '{"ResetType":"ForceOff"}' \
       -H "Content-Type: application/json" -X POST \
        http://localhost:8000/redfish/v1/Systems/vbmc-node/Actions/ComputerSystem.Reset

You can have as many domains as you need. The domains can be concurrently
managed over Redfish and some other tool like
`Virtual BMC <https://github.com/openstack/virtualbmc>`_.

The OpenStack backend
+++++++++++++++++++++

You can use an OpenStack cloud instances to simulate Redfish-managed
baremetal machines. This setup is known under the name of
`OpenStack Virtial Baremetal <http://openstack-virtual-baremetal.readthedocs.io/en/latest/>`_.
We will largely re-use its OpenStack infrastructure and configuration
instructions. After all, what we are trying to do here is to set up the
Redfish simulator alongside the
`openstackvbmc <https://docs.openstack.org/tripleo-docs/latest/install/environments/virtualbmc.html>`_
tool which is used for exactly the same purpose at OVB with the only
difference that it works over the *IPMI* protocol as opposed to *Redfish*.

The easiest way is probably to set up your OpenStack Virtial Baremetal cloud
by following
`its instructions <http://openstack-virtual-baremetal.readthedocs.io/en/latest/>`_.

Once your OVB cloud operational, you log into the *BMC* instance and
:ref:`set up sushy-tools <installation>` there.

Next you can invoke the Redfish virtual BMC pointing it to your OVB cloud:

.. code-block:: bash

   $ sushy-emulator --os-cloud rdo-cloud
    * Running on http://localhost:8000/ (Press CTRL+C to quit)

By this point you should be able to see your OpenStack instances among the
Redfish *Systems*:

.. code-block:: bash

   $ curl http://localhost:8000/redfish/v1/Systems/
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

And flip its power state via the Redfish call:

.. code-block:: bash

   $ curl -d '{"ResetType":"On"}' \
       -H "Content-Type: application/json" -X POST \
        http://localhost:8000/redfish/v1/Systems/vbmc-node/Actions/ComputerSystem.Reset

   $ curl -d '{"ResetType":"ForceOff"}' \
       -H "Content-Type: application/json" -X POST \
        http://localhost:8000/redfish/v1/Systems/vbmc-node/Actions/ComputerSystem.Reset

You can have as many OpenStack instances as you need. The instances can be
concurrently managed over Redfish and functionally similar tools like
`Virtual BMC <https://github.com/openstack/virtualbmc>`_.
