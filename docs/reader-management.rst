Reader management and tag deduplication
=======================================

Sllurp's core protocol is LLRP. LLRP is standardized across compatible RFID
readers, while administrative web-management APIs are vendor-specific. Sllurp
therefore keeps LLRP inventory control separate from HTTP/HTTPS reader
management and exposes vendor adapters only for documented management surfaces.

Tag report deduplication
------------------------

A reader can report the same EPC repeatedly across multiple ``RO_ACCESS_REPORT``
messages. ``TagReportDeduplicator`` optionally suppresses repeated application
callbacks for a configurable time window without changing the reader's RF or
inventory behavior.

.. code:: python

    from sllurp.dedup import TagReportDeduplicator

    def on_unique_tags(reader, tags):
        for tag in tags:
            print(tag)

    dedup = TagReportDeduplicator(
        on_unique_tags,
        window_seconds=1.0,
        include_antenna=False,
    )
    reader.add_tag_report_callback(dedup)

By default the EPC is the identity. Set ``include_antenna=True`` when the same
EPC seen on different antennas should be treated as separate observations.
Pass a custom ``key=`` callable for application-specific identity rules.

This is intentionally distinct from LLRP's reader-side tag accumulation and
``TagSeenCount``. Hardware and firmware may aggregate sightings inside a single
report; this helper suppresses duplicate reports seen by the application across
time.

Generic HTTP/HTTPS transport
----------------------------

``HTTPReaderManager`` remains available when an application needs to call an
endpoint that is not covered by a vendor adapter.

.. code:: python

    from sllurp.reader_management import HTTPReaderManager

    manager = HTTPReaderManager(
        "https://reader.example",
        username="admin",
        password="secret",
    )
    settings = manager.get_settings("/vendor/settings")

The transport supports HTTP and HTTPS, GET plus PATCH/PUT/POST requests, HTTP
Basic and bearer authentication, custom headers, CA bundles, client
certificates, and normalized errors.

Unified vendor adapters
-----------------------

Use ``create_reader_manager`` when the vendor and model are known. The returned
object exposes ``supports(operation)`` so applications can branch on actual
reader capabilities instead of assuming every RFID reader has the same web API.

.. code:: python

    from sllurp.reader_adapters import create_reader_manager

    reader = create_reader_manager(
        "zebra",
        "FX9600",
        "https://192.0.2.10",
        username="admin",
        password="reader-password",
    )

    print(reader.identity())
    print(reader.get_status())

    if reader.supports("network"):
        network = reader.get_network()
        print(network)

Readers without a documented HTTP management contract return an
``LLRPOnlyReaderManager``. Calling an unsupported management operation raises
``ReaderManagementUnsupported`` rather than guessing a web endpoint.

Zebra fixed readers
-------------------

``ZebraReaderManager`` implements Zebra's local REST ``/cloud`` management
surface. With web-console credentials it automatically calls
``/cloud/localRestLogin`` using Basic authentication, extracts the returned
token, and uses bearer authentication for subsequent requests. A caller that
already has a token can pass ``bearer_token=`` instead.

.. code:: python

    from sllurp.reader_adapters import ZebraReaderManager

    reader = ZebraReaderManager(
        "https://fx9600.example",
        model="FX9600",
        username="admin",
        password="reader-password",
    )

    status = reader.get_status()
    config = reader.get_settings()
    reader.update_settings({"GPIO-LED": {"GPIDebounce": {"1": 50}}})

    reader.set_mode({"mode": "INVENTORY"})
    reader.start_inventory()
    reader.stop_inventory()

The adapter includes high-level methods for:

* reader version/identity and health status
* reader configuration GET/PUT
* network GET/PUT and reboot
* operating mode plus inventory start/stop
* reader capabilities, current region, supported regions and standards
* GPI status, GPO state and application LED control
* timezone and NTP configuration
* logging configuration, log retrieval and deletion
* reader name and description
* user application list/install/start/stop/uninstall/autostart/pass-through
* installed certificate listing, install/refresh and certificate deletion
* OS/firmware update and firmware revert
* authenticated raw requests for newer vendor routes

Zebra's IoT Connector documentation describes the local REST surface for
FX7500, FX9600 and ATR7000. Zebra publishes a separate FXR90 REST API and its
current fixed-reader SDK exposes corresponding FXR90 management operations.
Firmware capabilities still vary, so use ``supports`` and handle
``ReaderManagementError`` for routes unavailable on a particular image.

Network changes and firmware updates can disconnect the management session.
Applications should treat those calls as disruptive and reconnect using the new
network or firmware state.

Impinj R700/R720
----------------

``ImpinjR700ReaderManager`` covers the R700-series REST interface using HTTP
Basic authentication.

.. code:: python

    from sllurp.reader_adapters import ImpinjR700ReaderManager

    reader = ImpinjR700ReaderManager(
        "https://r700.example",
        model="R700",
        username="root",
        password="reader-password",
    )

    print(reader.get_status())
    presets = reader.list_inventory_presets()
    reader.start_inventory("default")
    reader.stop_inventory()

The adapter includes status/identity, MQTT settings, supported profiles,
inventory-preset schema/list/get/update/delete, preset start/stop, and raw
authenticated requests. Impinj documents the R700/R720 family as providing an
OpenAPI-compatible REST configuration API; the R700 status endpoint is
``/api/v1/status``.

Legacy Impinj and Motorola readers
----------------------------------

Known Sllurp-compatible legacy readers such as Speedway R220/R420, xPortal and
Motorola MC9190-Z remain supported through LLRP. Sllurp does not invent an
HTTP/HTTPS administration contract for them. Their web consoles, RShell tools,
and vendor utilities are different interfaces and are not interchangeable with
the R700 or Zebra REST APIs.

This distinction is intentional:

* RFID inventory/RF behavior belongs in LLRP when the reader supports LLRP.
* Administrative HTTP/HTTPS operations use a vendor adapter when the vendor
  publishes a stable management API.
* A non-LLRP reader remains outside Sllurp's core protocol scope.

Capability matrix
-----------------

============================  =====  ===============================  ==============================
Reader family                 LLRP   HTTP/HTTPS adapter               Main management coverage
============================  =====  ===============================  ==============================
Zebra FX7500 / FX9600         yes    ``ZebraReaderManager``           broad ``/cloud`` management
Zebra FXR90 family            yes    ``ZebraReaderManager``           firmware-dependent REST
Zebra ATR7000                  yes*   ``ZebraReaderManager``           broad ``/cloud`` management
Impinj R700 / R720             yes    ``ImpinjR700ReaderManager``      REST status/profiles/MQTT
Impinj Speedway / xPortal      yes    ``LLRPOnlyReaderManager``        LLRP; no guessed REST API
Motorola MC9190-Z              yes    ``LLRPOnlyReaderManager``        LLRP; no guessed REST API
============================  =====  ===============================  ==============================

``*`` ATR7000 is included because Zebra's IoT Connector REST documentation
lists it; it is not one of the historical Sllurp compatibility-test targets.

TLS
---

Certificate verification is enabled by default. Private reader certificates can
be trusted with ``ca_file=``; mTLS is available with ``cert_file=`` and
``key_file=``. ``verify_tls=False`` is available for controlled legacy/test
environments but should not be the production default.

Vendor references
-----------------

* Zebra fixed-reader API index:
  https://techdocs.zebra.com/dcs/rfid/
* Zebra IoT Connector Local REST API:
  https://zebradevs.github.io/rfid-ziotc-docs/_static/api/redoc-static.html
* Zebra local REST login/setup:
  https://zebradevs.github.io/rfid-ziotc-docs/setupziotc/index.html
* Zebra FXR90 REST API:
  https://techdocs.zebra.com/dcs/rfid/fxr90-rest/
* Impinj R700/R720 datasheet:
  https://support.impinj.com/hc/article_attachments/31243539924371
