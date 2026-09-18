Sllurp example guide
====================

Start with the `Quick Start <../QUICKSTART.md>`_ if Sllurp is not installed yet.
The runnable examples live in `examples/ <../examples/README.md>`_ and are
intended to be small enough to copy into an application and adapt.

Example map
-----------

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Goal
     - Example
   * - First Python inventory
     - `basic_inventory.py <../examples/basic_inventory.py>`_
   * - Timed tag deduplication
     - `dedup_inventory.py <../examples/dedup_inventory.py>`_
   * - RF telemetry / antenna observations
     - `rf_telemetry.py <../examples/rf_telemetry.py>`_
   * - Live runtime configuration
     - `runtime_config.py <../examples/runtime_config.py>`_
   * - Generic HTTP/HTTPS management
     - `reader_management_generic.py <../examples/reader_management_generic.py>`_
   * - Zebra RM / IoT management
     - `zebra_management.py <../examples/zebra_management.py>`_
   * - Impinj R700/R720 management
     - `impinj_management.py <../examples/impinj_management.py>`_
   * - Honeywell/Intermec DCWS
     - `intermec_management.py <../examples/intermec_management.py>`_
   * - TLS, access, logging, multi-reader
     - `CLI recipes <../examples/cli-recipes.md>`_
   * - FastAPI / WebSocket integration
     - `FastAPI demo <../examples/fastapi/README.md>`_

Choosing the right example
--------------------------

Use ``basic_inventory.py`` when learning the Python callback API. Use the CLI
for quick reader checks, one-off inventory, logging, tag-memory access, and TLS
smoke tests. The CLI examples are easier to diagnose before embedding a reader
connection inside a service.

Use ``rf_telemetry.py`` when the application needs per-antenna RSSI, channel,
timestamps, or Zebra phase observations. Raw telemetry normally leaves timed
deduplication disabled so repeated RF samples are preserved.

Use ``runtime_config.py`` when settings must change while a client is running.
It demonstrates ``apply_config()`` and ``get_config_state()`` rather than direct
mutation of a live configuration object.

Use the management examples only for the reader's documented management
interface. LLRP inventory and vendor HTTP/HTTPS/SOAP administration are separate
protocols.

Safety notes
------------

* Test tag-memory writes with disposable/test tags first.
* Keep TLS certificate verification enabled in normal deployments and configure
  the correct CA/hostname.
* Reader network, region, LLRP-service, firmware, reboot, and power changes can
  interrupt access. Read the vendor documentation before applying them.
* Never hard-code production passwords in example-derived source. Use a secret
  store, environment/config injection, or an interactive prompt as appropriate.

Validation
----------

The repository CI compiles Python under ``examples/`` along with the package
and runs the normal static/security gates. The FastAPI example also gets a
clean dependency/import smoke test on supported Python endpoints. Hardware-
dependent behavior still requires the target reader/model/firmware because
examples cannot emulate a reader's vendor API or RF environment.
