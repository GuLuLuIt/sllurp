=================================================================
Sllurp — production-focused Python LLRP client for RFID readers
=================================================================

.. image:: https://img.shields.io/badge/python-3.13--3.14-blue.svg
   :target: https://www.python.org/
   :alt: Python 3.13 and 3.14

.. image:: https://github.com/GuLuLuIt/sllurp/actions/workflows/test.yml/badge.svg?branch=main
   :target: https://github.com/GuLuLuIt/sllurp/actions/workflows/test.yml
   :alt: Tests

.. image:: https://img.shields.io/badge/license-GPL--3.0--only-blue.svg
   :target: LICENSE.txt
   :alt: GPL-3.0-only

Sllurp is a pure-Python client and library for **LLRP-based RFID readers** with
secure LLRP/TLS, timed tag deduplication, reader-management adapters, runtime
configuration, RF telemetry, vendor extensions, and multi-reader support.

Quick Start
-----------

**Start here:** `QUICKSTART.md <QUICKSTART.md>`_

The full Quick Start covers Windows, Ubuntu/Debian, Fedora/RHEL/Rocky/AlmaLinux,
Arch/Manjaro, openSUSE, macOS, virtual environments, installation, first
inventory, TLS, deduplication, tag access, logging, management APIs, runtime
configuration, RF telemetry, and troubleshooting.

Install the feature set documented in this repository::

    python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"

Verify the installed command::

    sllurp --version

The ``sllurp`` package on PyPI is the upstream distribution, not this fork.
Use ``pip install sllurp`` only when you intentionally want the upstream
release. For the features documented on this page, use the GitHub install
above.

First inventory::

    sllurp inventory 192.168.1.50

Use every reader-reported antenna for 10 seconds::

    sllurp inventory -a 0 -t 10 192.168.1.50

Inventory multiple readers::

    sllurp inventory -a 0 192.168.1.50 192.168.1.51

Run ``sllurp --help`` and ``sllurp inventory --help`` for the installed
version's command options.

Features
--------

==============================  ==================================================
Capability                      What you get
==============================  ==================================================
Standard LLRP                   Inventory, AccessSpecs, logging, reset, reconnect
Secure LLRP / TLS               Verified TLS, custom CA, mTLS, SNI, port 5085
Timed tag deduplication         Auto/hardware/memory backends with bounded behavior
Reader management               Generic HTTP/HTTPS plus vendor-aware adapters
Zebra management                RM XML and IoT Connector local REST where supported
Impinj management               R700/R720 documented REST management
Honeywell / Intermec            IF1/IF2/IF61 WSDL-driven DCWS/SOAP management
Runtime configuration           Transactional ``apply_config()`` and state views
RF telemetry                    Per-antenna RSSI/channel/timestamps + Zebra phase
Reader capability registry      Model/family-aware behavior instead of hard-coding
Impinj LLRP extensions          Search mode, reports, fixed-frequency controls
Multi-reader CLI                Inventory more than one reader from one command
==============================  ==================================================

Examples
--------

The `examples index <examples/README.md>`_ contains runnable, focused examples
for the main features instead of forcing users to extract snippets from long
documentation pages.

* `Basic Python inventory <examples/basic_inventory.py>`_
* `Timed deduplication <examples/dedup_inventory.py>`_
* `RF telemetry <examples/rf_telemetry.py>`_
* `Live runtime configuration <examples/runtime_config.py>`_
* `Generic HTTP/HTTPS management <examples/reader_management_generic.py>`_
* `Zebra management <examples/zebra_management.py>`_
* `Impinj R700/R720 management <examples/impinj_management.py>`_
* `Honeywell/Intermec DCWS <examples/intermec_management.py>`_
* `CLI recipes for TLS, tag access, logging, multi-reader, and Impinj extensions <examples/cli-recipes.md>`_
* `FastAPI/WebSocket demo <examples/fastapi/README.md>`_

Common examples
---------------

Timed deduplication::

    sllurp inventory --dedup-seconds 2 --dedup-backend auto -a 0 192.168.1.50

Secure LLRP with a private CA::

    sllurp inventory --tls --tls-ca-file reader-ca.pem reader.example.com

Impinj dual-target search mode::

    sllurp inventory --impinj-search-mode 2 192.168.1.50

Impinj phase/RSSI/Doppler reporting::

    sllurp inventory --impinj-reports -a 0 192.168.1.50

Stream tag observations::

    sllurp log -a 0 -o tags.csv 192.168.1.50

Read tag memory::

    sllurp access --read-words 2 --count 1 192.168.1.50

If a debugging session leaves a reader in an unexpected LLRP state::

    sllurp reset 192.168.1.50

For complete examples and platform-specific setup, use the
`Quick Start <QUICKSTART.md>`_.

Secure LLRP / TLS
-----------------

Plain LLRP normally uses TCP 5084. ``--tls`` uses encrypted LLRP and defaults
to TCP 5085 unless ``--port`` is supplied explicitly. Certificate verification
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
``--tls-server-hostname``. ``--tls-no-verify`` is intended for controlled test
environments, not normal production use.

See `docs/secure_llrp.rst <docs/secure_llrp.rst>`_.

Reader management
-----------------

LLRP controls RFID inventory. Reader web administration is a separate surface.
Sllurp provides:

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

``rf_telemetry_mode`` is opt-in for applications that need per-antenna radio
observations rather than only radio-wide tag identity. ``standard`` requests
portable LLRP telemetry; ``zebra`` adds supported Zebra/Motorola phase and
physical-port telemetry.

.. code:: python

    from sllurp.llrp import LLRPReaderConfig

    config = LLRPReaderConfig({
        "antennas": [1, 2],
        "rf_telemetry_mode": "zebra",
        "dedup_seconds": None,
    })

See `docs/rf-telemetry.rst <docs/rf-telemetry.rst>`_.

Dynamic runtime configuration
-----------------------------

``LLRPReaderClient.apply_config()`` classifies changes before mutating reader
state. Use ``get_config_state()`` to inspect desired, generated, applied, and
reader-reported state.

See `docs/runtime-state.rst <docs/runtime-state.rst>`_.

Reader compatibility
--------------------

Sllurp is not tied to one reader vendor. The compatibility registry includes
families from Zebra/Motorola, Impinj, Honeywell/Intermec, ThingMagic/JADAK, and
Alien where standard LLRP support is documented or known. Vendor-specific
capabilities remain model/firmware dependent.

See `docs/readers.rst <docs/readers.rst>`_.

Documentation
-------------

* `Quick Start <QUICKSTART.md>`_ — installation and first use
* `Documentation index <docs/index.rst>`_ — feature and CLI map
* `Example guide <docs/examples.rst>`_ — runnable examples by feature
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

For verbose protocol diagnostics::

    sllurp --debug inventory 192.168.1.50

Write diagnostics to a file::

    sllurp --debug --logfile sllurp.log inventory 192.168.1.50

See the `Quick Start troubleshooting section <QUICKSTART.md>`_ for the full
checklist.

Development
-----------

Clone and install in editable mode with the complete developer toolset::

    git clone https://github.com/GuLuLuIt/sllurp.git
    cd sllurp
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[dev]"
    pytest -W error

Python 3.13 and 3.14 are the supported Python versions for this fork. CI runs
the full suite on both versions; Windows and macOS also run the full suite on
Python 3.14. See `CONTRIBUTING.md <CONTRIBUTING.md>`_ for the full local quality
gate and hardware/interoperability contribution guidance.

Project maintenance
-------------------

* `Changelog <CHANGELOG.md>`_ — unreleased changes and release history
* `Contributing <CONTRIBUTING.md>`_ — development and pull-request guidance
* `Security policy <SECURITY.md>`_ — vulnerability reporting and sensitive data
* `Support <SUPPORT.md>`_ — what to include in bug and hardware reports
* `Release process <RELEASING.md>`_ — versioning, build validation, and publishing safeguards
* `Notice <NOTICE.md>`_ — fork lineage and attribution

License and lineage
-------------------

Repository-level metadata follows upstream and identifies ``GPL-3.0-only``.
See ``LICENSE.txt`` for the canonical repository license text and ``NOTICE.md``
for attribution plus the inherited file-level license-notice caveat. This
repository is a modified fork of
`the upstream sllurp project <https://github.com/sllurp/sllurp>`_.

Support and bug reports
-----------------------

Start with `SUPPORT.md <SUPPORT.md>`_. When GitHub Issues are enabled for this
fork, use the structured bug/feature templates. Security vulnerabilities should
follow `SECURITY.md <SECURITY.md>`_ instead of being disclosed publicly.
