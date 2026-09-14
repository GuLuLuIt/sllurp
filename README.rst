=================================================================
Sllurp — production-focused Python LLRP client for RFID readers
=================================================================

.. image:: https://img.shields.io/pypi/v/sllurp.svg
   :target: https://pypi.org/project/sllurp/
   :alt: PyPI

.. image:: https://img.shields.io/pypi/pyversions/sllurp.svg
   :target: https://pypi.org/project/sllurp/
   :alt: Python versions

.. image:: https://github.com/GuLuLuIt/sllurp/actions/workflows/test.yml/badge.svg?branch=main
   :target: https://github.com/GuLuLuIt/sllurp/actions/workflows/test.yml
   :alt: Tests

.. image:: https://img.shields.io/badge/license-GPL--3.0-blue.svg
   :target: LICENSE.txt
   :alt: GPL-3.0

Sllurp is a pure-Python client and library for **LLRP-based RFID readers**.
This fork keeps the original vendor-neutral LLRP core and adds production-focused
features for secure transport, reader administration, deduplication, runtime
configuration, and RF telemetry.

**New here?** Start with the `Quick Start <QUICKSTART.md>`_.  It covers Windows,
Ubuntu/Debian, Fedora/RHEL-family distributions, Arch/Manjaro, openSUSE, macOS,
first inventory, Secure LLRP, tag access, deduplication, management APIs, and
RF telemetry.

==============================  ==================================================
Capability                      What you get
==============================  ==================================================
Standard LLRP                   Inventory, AccessSpecs, logging, reset, reconnect
Secure LLRP / TLS               Verified TLS, custom CA, mTLS, SNI, port 5085
Timed tag deduplication         Auto/hardware/memory backends with bounded behavior
Reader management              Generic HTTP/HTTPS plus vendor-aware adapters
Zebra management                RM XML and IoT Connector local REST where supported
Impinj management               R700/R720 documented REST management
Honeywell / Intermec            IF1/IF2/IF61 WSDL-driven DCWS/SOAP management
Runtime configuration           Transactional ``apply_config()`` and state views
RF telemetry                    Per-antenna RSSI/channel/timestamps + Zebra phase
Reader capability registry      Model/family-aware behavior instead of hard-coding
Impinj LLRP extensions          Search mode, reports, fixed-frequency controls
Multi-reader CLI                Inventory more than one reader from one command
==============================  ==================================================

Install the full feature set
----------------------------

The package published on PyPI may lag this fork.  To use the features documented
in this repository, install directly from this fork's ``main`` branch.

Windows PowerShell::

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"

Ubuntu / Debian / Linux Mint / Raspberry Pi OS::

    sudo apt update
    sudo apt install -y python3 python3-venv python3-pip git
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"

For Fedora/RHEL/Rocky/AlmaLinux, Arch/Manjaro, openSUSE, macOS, Windows Command
Prompt, editable source installs, and troubleshooting, see the
`complete Quick Start <QUICKSTART.md>`_.

The currently published package can still be installed with::

    python -m pip install sllurp

First RFID inventory
--------------------

Replace the address with your reader::

    sllurp inventory 192.168.1.50

Use every antenna reported by the reader and stop after 10 seconds::

    sllurp inventory -a 0 -t 10 192.168.1.50

Inventory multiple readers::

    sllurp inventory -a 0 192.168.1.50 192.168.1.51

If an interrupted debugging session leaves a reader in an unexpected LLRP
state::

    sllurp reset 192.168.1.50

Run ``sllurp --help`` and ``sllurp inventory --help`` for the complete command
options available in the installed version.

Common feature examples
-----------------------

Timed deduplication::

    sllurp inventory --dedup-seconds 2 --dedup-backend auto -a 0 192.168.1.50

Secure LLRP with a private CA::

    sllurp inventory --tls --tls-ca-file reader-ca.pem reader.example.com

Impinj dual-target search mode::

    sllurp inventory --impinj-search-mode 2 192.168.1.50

Impinj extended phase/RSSI/Doppler reporting::

    sllurp inventory --impinj-reports -a 0 192.168.1.50

Stream tag observations to CSV::

    sllurp log -a 0 -o tags.csv 192.168.1.50

Read tag memory::

    sllurp access --read-words 2 --count 1 192.168.1.50

See the `Quick Start <QUICKSTART.md>`_ for complete examples and safety notes.

Secure LLRP / TLS
-----------------

Plain LLRP normally uses TCP 5084.  ``--tls`` uses encrypted LLRP and defaults
to TCP 5085 unless ``--port`` is supplied explicitly.  Certificate verification
is enabled by default.

Private CA::

    sllurp inventory --tls --tls-ca-file reader-ca.pem reader.example.com

Mutual TLS::

    sllurp inventory \
        --tls \
        --tls-ca-file reader-ca.pem \
        --tls-client-cert client.pem \
        --tls-client-key client.key \
        reader.example.com

When connecting by IP to a certificate issued to a DNS name, use
``--tls-server-hostname``.  ``--tls-no-verify`` exists for controlled testing,
but should not be the normal production setup.

See `docs/secure_llrp.rst <docs/secure_llrp.rst>`_.

Reader management
-----------------

LLRP controls RFID inventory.  Reader web administration is a separate surface.
This fork provides:

* generic HTTP/HTTPS management with Basic/Bearer authentication, verified TLS,
  custom CAs, client certificates, same-origin protection, and normalized errors;
* Zebra Reader Management XML support for documented fixed-reader families;
* Zebra IoT Connector local REST support where the model/firmware exposes it;
* Impinj R700/R720 documented ``/api/v1`` management;
* Honeywell/Intermec IF1/IF2/IF61 WSDL-driven DCWS/SOAP management.

Example generic transport:

.. code:: python

    from sllurp.reader_management import HTTPReaderManager

    manager = HTTPReaderManager(
        "https://reader.example",
        username="admin",
        password="secret",
    )
    settings = manager.get_settings("/api/settings")

See `docs/reader-management.rst <docs/reader-management.rst>`_,
`docs/impinj-management.rst <docs/impinj-management.rst>`_, and
`docs/intermec-management.rst <docs/intermec-management.rst>`_.

RF telemetry
------------

``rf_telemetry_mode`` is an opt-in mode for applications that need per-antenna
radio observations instead of only radio-wide tag identity.

``standard`` requests portable LLRP telemetry such as antenna, channel, RSSI,
timestamps, tag-seen count, and ROSpec ID.  ``zebra`` adds supported
Zebra/Motorola phase and physical-port telemetry.

.. code:: python

    from sllurp.llrp import LLRPReaderConfig

    config = LLRPReaderConfig({
        "antennas": [1, 2],
        "rf_telemetry_mode": "zebra",
        "dedup_seconds": None,
    })

Sllurp acquires and normalizes measurements; localization/vector math remains a
higher-level application concern.  See
`docs/rf-telemetry.rst <docs/rf-telemetry.rst>`_.

Dynamic runtime configuration
-----------------------------

``LLRPReaderClient.apply_config()`` classifies changes before mutating reader
state.  Client-only changes can apply locally, ROSpec changes can perform a
controlled replacement, reader configuration changes are serialized, and
transport/session changes that require reconnect are rejected while connected
rather than being half-applied.

Use ``get_config_state()`` to inspect desired, generated, applied, and
reader-reported state.  See
`docs/runtime-state.rst <docs/runtime-state.rst>`_.

Reader compatibility
--------------------

Sllurp is deliberately not tied to one reader vendor.  The compatibility
registry includes families from Zebra/Motorola, Impinj, Honeywell/Intermec,
ThingMagic/JADAK, and Alien where standard LLRP support is documented or known.
Vendor-specific capabilities remain model/firmware dependent.

See the full matrix in `docs/readers.rst <docs/readers.rst>`_.

Documentation
-------------

* `Quick Start <QUICKSTART.md>`_ — install and use every major feature
* `Documentation index <docs/index.rst>`_ — feature map and CLI map
* `Reader compatibility <docs/readers.rst>`_
* `Secure LLRP <docs/secure_llrp.rst>`_
* `Reader management and deduplication <docs/reader-management.rst>`_
* `Impinj management <docs/impinj-management.rst>`_
* `Honeywell / Intermec management <docs/intermec-management.rst>`_
* `RF telemetry <docs/rf-telemetry.rst>`_
* `Runtime state and dynamic configuration <docs/runtime-state.rst>`_

Minimal Python API
------------------

.. code:: python

    from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig, LLRP_DEFAULT_PORT

    def on_tags(reader, tag_reports):
        for tag in tag_reports:
            print(tag)

    config = LLRPReaderConfig({"antennas": [0]})
    reader = LLRPReaderClient("192.168.1.50", LLRP_DEFAULT_PORT, config)
    reader.add_tag_report_callback(on_tags)
    reader.connect()

    try:
        reader.join(None)
    finally:
        reader.disconnect()

Troubleshooting
---------------

Connection failures usually come down to reader addressing, VLAN/firewall
rules, LLRP being disabled, or the wrong plain/secure port.  For verbose
protocol diagnostics::

    sllurp --debug inventory 192.168.1.50

Write diagnostics to a file::

    sllurp --debug --logfile sllurp.log inventory 192.168.1.50

For certificate errors, prefer supplying the correct CA rather than disabling
verification.  The `Quick Start troubleshooting section <QUICKSTART.md>`_
contains a fuller checklist.

Development
-----------

Clone this fork and install it in editable mode::

    git clone https://github.com/GuLuLuIt/sllurp.git
    cd sllurp
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[test]"
    pytest -q

Python 3.10 through 3.14 are supported by the current project metadata.

License and lineage
-------------------

Sllurp is distributed under GPL-3.0.  See ``LICENSE.txt``.

The project began as a fork of LLRPyC and has received contributions from Ben
Ransford, Florent Viard, Bogdan-Marius Pradatu, Jonas Gröger, Qifan Lu, and many
other contributors.  This repository is an enhanced fork of the original
`sllurp/sllurp <https://github.com/sllurp/sllurp>`_ project.

Issues
------

When reporting a bug, include the reader model, firmware version, whether the
connection is plain LLRP or TLS, the command/configuration used, and DEBUG logs
with secrets removed.