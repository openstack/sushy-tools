
Configuring emulators
=====================

Running emulators in background
-------------------------------

The emulators run as interactive processes attached to the
terminal by default. You can create a systemd service to run the
emulators in background.
For each emulator create a systemd unit file and
update full path to ``sushy-static`` or ``sushy-emulator`` binary and
adjust arguments as necessary, for example::

  [Unit]
  Description=Sushy Libvirt emulator
  After=syslog.target

  [Service]
  Type=simple
  ExecStart=/<full-path>/sushy-emulator --port 8000 --libvirt-uri "qemu:///system"
  StandardOutput=syslog
  StandardError=syslog

If you want to run emulators with different configuration, for example,
``sushy-static`` emulator with different mockup files, then create a new
systemd unit file.

You can also use ``gunicorn`` to run ``sushy-emulator``, for example::

  ExecStart=/usr/bin/gunicorn sushy_tools.emulator.main:app

Using configuration file
------------------------

Besides command-line options, `sushy-emulator` can be configured via a
configuration file. The tool uses Flask application
`configuration infrastructure <http://flask.pocoo.org/docs/config/>`_,
emulator-specific configuration options are prefixed with **SUSHY_EMULATOR_**
to make sure they won't collide with Flask's own configuration options.

The configuration file itself can be specified through the
`SUSHY_EMULATOR_CONFIG` environment variable.

The full list of supported options and their meanings could be found in
the sample configuration file:

.. literalinclude:: emulator.conf
