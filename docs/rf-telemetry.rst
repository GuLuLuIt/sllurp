RF telemetry mode
=================

Purpose
-------

RF telemetry mode is an opt-in inventory mode for applications that need
per-antenna radio observations for later motion, direction, displacement,
or localization analysis. Sllurp acquires and normalizes the observations;
it does not calculate position or movement vectors.

The default remains ``off`` so existing applications keep their current
reporting and deduplication behavior.

Modes
-----

``off``
    Existing behavior. RF telemetry-specific fields are not forced on.

``standard``
    Enables standard LLRP fields useful for RF analysis on any supported LLRP
    reader: ROSpec ID, Antenna ID, channel index, peak RSSI, first-seen
    timestamp, last-seen timestamp, and tag-seen count.

``zebra``
    Includes everything in ``standard`` and also requests Zebra/Motorola
    physical-port configuration and tag RF phase. ``MotoTagPhase`` is decoded
    to degrees. This mode is intended for Zebra fixed readers that implement
    those custom LLRP parameters, including the FX9600 and FXR90 family where
    supported by firmware.

Quick start
-----------

.. code:: python

    from sllurp.llrp import LLRPReaderConfig

    config = LLRPReaderConfig({
        "antennas": [1, 2],
        "rf_telemetry_mode": "zebra",
        # Leave None for raw repeated RF observations.
        "dedup_seconds": None,
    })

Data flow
---------

::

    +----------------------+
    | Supported LLRP       |
    | reader               |
    +----------+-----------+
               |
               | EPC, antenna, channel, RSSI,
               | timestamps, phase where supported
               v
    +----------+-----------+
    | Sllurp               |
    | acquisition layer    |
    |                      |
    | - decode LLRP        |
    | - preserve antenna   |
    | - normalize fields   |
    | - optional dedup     |
    +----------+-----------+
               |
               | normalized RF observations
               v
    +----------+-----------+
    | application /        |
    | future RF library    |
    |                      |
    | - vectors            |
    | - direction          |
    | - displacement       |
    | - localization       |
    +----------------------+

Sllurp deliberately stops at the normalized-observation boundary. Vector,
triangulation, filtering, and multi-reader fusion belong in a separate module
or library.

Per-antenna identity
--------------------

Normal inventory can treat an EPC as one radio-wide identity. RF telemetry
mode preserves the antenna dimension so the same EPC may produce distinct
observations from multiple ports::

    EPC 3008...  Antenna 1  RSSI -46  Phase  42 deg
    EPC 3008...  Antenna 2  RSSI -53  Phase 101 deg
            |          |
            +----------+---- same tag, two RF observations

This is important for fixed multi-element antennas and for comparing
observations across ports.

Deduplication
-------------

Raw phase/motion work normally uses ``dedup_seconds=None`` because repeated
observations are the signal being analyzed.

If timed deduplication is explicitly enabled while RF telemetry mode is on,
Sllurp uses the in-memory deduplicator and keys identities by
``(EPC, AntennaID)`` for every supported reader. A sighting from antenna 1
therefore does not suppress the same EPC from antenna 2. This behavior is
reader-vendor independent; Zebra-specific mode only adds Zebra telemetry
fields.

::

    RF telemetry off              RF telemetry on

    EPC X / ant 1 ----+            EPC X / ant 1 ---> keep
                      +--> one      EPC X / ant 2 ---> keep
    EPC X / ant 2 ----+            identities differ by antenna

Reader-wide hardware timed dedup is intentionally not selected in RF telemetry
mode because a reader-wide unique-tag policy can collapse the cross-antenna
observations this mode is designed to preserve. Requesting
``dedup_backend="hardware"`` together with RF telemetry mode is rejected; use
``memory`` or disable timed dedup.

Memory behavior
---------------

Software dedup stores one entry per active identity for the configured window.
In RF telemetry mode the identity includes Antenna ID for all supported
readers, so memory usage can increase when the same EPC is observed on many
ports. Use ``dedup_max_entries`` as a hard bound and prefer raw/no-dedup
telemetry for short analysis sessions when repeated phase samples are required.

Fields preserved for analysis
-----------------------------

Standard RF telemetry requests:

* EPC / EPCData
* Antenna ID
* channel index
* peak RSSI
* first-seen timestamp
* last-seen timestamp
* tag-seen count
* ROSpec ID

Zebra RF telemetry additionally requests:

* ``MotoTagPhase`` in degrees
* antenna physical-port configuration

Other reader/vendor extensions can be added later without changing the
boundary: Sllurp should expose measurements, while higher-level RF math remains
outside this package.

FXR90 family
------------

Sllurp treats FXR90 model strings as one capability-driven family rather than
hard-coding antenna counts. Four-port, integrated-antenna/external-port, and
eight-port variants therefore use the same RF telemetry mode; actual antenna
availability remains reader-reported.
