Sllurp documentation
====================

Quick Start
-----------

New users should begin with the `Quick Start <../QUICKSTART.md>`_. It covers
Windows, Ubuntu/Debian, Fedora/RHEL/Rocky/AlmaLinux, Arch/Manjaro, openSUSE,
macOS, installation, first inventory, Secure LLRP, deduplication, tag access,
logging, reader management, runtime configuration, RF telemetry, and
troubleshooting.

Install the feature set documented in this repository directly from ``main``::

    python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"

The ``sllurp`` package on PyPI is the upstream distribution. It is useful when
you intentionally want the upstream release, but it is not an equivalent
installation path for fork-specific features documented here.

Verify which command build is installed::

    sllurp --version

Runnable examples
-----------------

Use the `Example guide <examples.rst>`_ for small programs covering Python
inventory, timed deduplication, RF telemetry, live runtime configuration,
generic HTTP/HTTPS management, Zebra management, Impinj R700/R720 management,
Honeywell/Intermec DCWS, CLI/TLS recipes, and web-framework integration.

The source files are indexed directly in `examples/README.md <../examples/README.md>`_.

Feature guide
-------------

===============================  ================================================
Topic                            Documentation
===============================  ================================================
First install and first read     `Quick Start <../QUICKSTART.md>`_
Runnable examples                `examples.rst <examples.rst>`_
Reader compatibility             `readers.rst <readers.rst>`_
Secure LLRP / TLS                `secure_llrp.rst <secure_llrp.rst>`_
Reader management + dedup        `reader-management.rst <reader-management.rst>`_
Impinj R700/R720 management      `impinj-management.rst <impinj-management.rst>`_
Honeywell / Intermec DCWS        `intermec-management.rst <intermec-management.rst>`_
RF telemetry / antenna identity  `rf-telemetry.rst <rf-telemetry.rst>`_
Dynamic runtime configuration    `runtime-state.rst <runtime-state.rst>`_
===============================  ================================================

Command-line map
----------------

``sllurp --version``
    Print the installed Sllurp version and exit.

``sllurp inventory``
    Inventory tags, select antennas, power, session, Tari, mode, frequencies,
    reconnect behavior, timed deduplication, Impinj extensions, and Secure LLRP.

``sllurp access``
    Read or write tag memory using LLRP AccessSpecs.

``sllurp log``
    Stream tag observations to a file or stdout.

``sllurp reset``
    Return a reader to a clean LLRP state after an interrupted/debug session.

Use the installed command's help as the authoritative option list::

    sllurp --version
    sllurp --help
    sllurp inventory --help
    sllurp access --help
    sllurp log --help
    sllurp reset --help

Protocol boundaries
-------------------

Sllurp's core reader-control protocol is LLRP. Plain LLRP normally uses TCP
5084 and Secure LLRP normally uses TCP 5085. Vendor HTTP/HTTPS/SOAP reader
management is separate from LLRP inventory and is only used through documented
vendor management APIs.
