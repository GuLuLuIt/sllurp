Zebra IoT Connector Local REST
==============================

``sllurp.zebra_iot.ZebraIoTConnector`` provides a small client for Zebra's
documented IoT Connector Local REST interface. This is separate from LLRP:
LLRP controls RFID reader operations, while the Local REST interface exposes
reader management and control endpoints over HTTP/HTTPS.

Authentication
--------------

Readers with Local REST authentication enabled use HTTP Basic authentication
for ``GET /cloud/localRestLogin``. The returned JWT is then supplied as a
Bearer token for subsequent ``/cloud`` requests.

Example::

    from sllurp.zebra_iot import ZebraIoTConnector

    reader = ZebraIoTConnector(
        "https://reader.example",
        username="admin",
        password="change-me",
    )

    print(reader.get_version())
    print(reader.get_status())
    print(reader.get_capabilities())
    print(reader.get_hostname())

    reader.set_hostname("warehouse-reader")
    reader.start()
    reader.stop()

A previously obtained JWT can be supplied with ``token=...`` instead of a
username and password.

Supported helpers
-----------------

The client currently wraps these documented endpoints:

* ``GET /cloud/version``
* ``GET /cloud/status``
* ``GET /cloud/readerCapabilities``
* ``GET`` and ``PUT /cloud/hostname``
* ``GET`` and ``PUT /cloud/config``
* ``PUT /cloud/start``
* ``PUT /cloud/stop``

Use ``request()`` for other documented Local REST endpoints. Endpoint
availability varies by reader model and firmware.

Reference
---------

Zebra IoT Connector Local REST API documentation:
https://zebradevs.github.io/rfid-ziotc-docs/_static/api/redoc-static.html
