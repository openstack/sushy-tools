
============
Contributing
============

.. include:: ../../../CONTRIBUTING.rst


Cloning the sushy-tools repository
++++++++++++++++++++++++++++++++++

If you haven't already, sushy-tools source code should be pulled directly
from git.

.. code-block:: bash

    # from the directory where you want the source code to reside
    git clone https://opendev.org/openstack/sushy-tools


Running the emulators locally
+++++++++++++++++++++++++++++

Activate the virtual environment and run the emulator of your choice. For
instance, to run the dynamic emulator:

.. code-block:: bash

    tox -e venv -- sushy-emulator

For more information on running the emulators, refer to the user docs for the
:doc:`dynamic-emulator <../user/dynamic-emulator>` and the :doc:`static-
emulator <../user/static-emulator>`.