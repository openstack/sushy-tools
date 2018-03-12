
Configuring simulators
======================

Running simulators in background
--------------------------------

The simulators run as interactive processes attached to the
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

If you want to run simulators with different configuration, for example,
``sushy-static`` simulator with different mockup files, then create a new
systemd unit file.

You can also use ``gunicorn`` to run ``sushy-emulator``, for example::

  ExecStart=/usr/bin/gunicorn sushy_tools.emulator.main:app
