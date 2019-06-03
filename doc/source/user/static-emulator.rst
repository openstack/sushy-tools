
Static Redfish BMC
==================

The static Redfish responder is a simple REST API server which serves
static contents down to the Redfish client. The tool emulates the
simple read-only BMC.

The user is expected to supply the Redfish-compliant contents perhaps
downloaded from the `DMTF <https://www.dmtf.org/>`_ web site. For
example,
`this .zip archive <https://www.dmtf.org/sites/default/files/standards/documents/DSP2043_1.0.0.zip>`_
includes Redfish content mocks for Redfish 1.0.0.

.. code-block:: bash

   curl -o DSP2043_1.0.0.zip \
        https://www.dmtf.org/sites/default/files/standards/documents/DSP2043_1.0.0.zip
   unzip -d mockups DSP2043_1.0.0.zip
   sushy-static -m mockups/public-rackmount

Once you have the static emulator running, you can use it as it was a
read-only bare-metal controller listening at *localhost:8000* (by default):

.. code-block:: bash

   curl http://localhost:8000/redfish/v1/Systems/
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

