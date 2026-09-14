RF telemetry mode
=================

Start here
----------

Install and verify a normal inventory first using the
`Quick Start <../QUICKSTART.md>`_::

    sllurp inventory -a 0 READER_HOST

Then enable telemetry in Python with ``rf_telemetry_mode="standard"`` for
portable LLRP fields or ``"zebra"`` for supported Zebra/Motorola phase and
physical-port extensions.  The full docs map is in `docs/index.rst <index.rst>`_.

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

Single versus dual/multi-antenna hardware
-----------------------------------------

The need for per-antenna identity depends on the RF topology, not only on the
reader model.

A single connected antenna has only one antenna path. Timed or unique-tag
reporting can still collapse repeated reads of the same EPC over time, but
there is no cross-port observation to lose. In that case antenna-aware memory
deduplication adds little beyond preserving the antenna identifier for
consistency.

A dual-element panel or a reader with two or more active antenna ports has
multiple RF paths. If reporting or deduplication is radio-wide, the same EPC
seen on two paths can be reduced to one observation. RF telemetry mode exists
to preserve those separate observations.

From Sllurp's point of view these two physical layouts are equivalent when the
reader reports distinct ``AntennaID`` values::

    One dual-element panel             Two separate single-port antennas

    +----------------------+           +-----------+     +-----------+
    | element A | element B|           | antenna A |     | antenna B |
    +-----+-----------+----+           +-----+-----+     +-----+-----+
          |           |                      |                 |
        port 1      port 2                 port 1            port 2
          \           /                      \                 /
           +---------+                        +---------------+
                |                                    |
                +---------- RFID reader -------------+

In both cases the desired software identity is ``(EPC, AntennaID)`` whenever
software-memory deduplication is enabled.

Hardware examples
~~~~~~~~~~~~~~~~~

The following examples illustrate topology. They do not imply that all reader
firmware exposes the same vendor-specific telemetry fields.

* **Zebra AN440** -- a dual-element panel with two RF connectors in one
  enclosure. When its two elements are connected to two reader antenna ports,
  the same EPC can legitimately be observed on both paths. This is the clearest
  example of where cross-port collapse loses useful information.
* **Zebra AN510** -- a single-connector panel antenna. One AN510 on one reader
  port has no cross-port ambiguity. Two AN510 antennas connected to two reader
  ports do have two independent RF paths, so per-antenna identity becomes
  useful again.
* **Impinj Speedway R220** -- provides two reader antenna ports. Two attached
  single-port antennas therefore behave, from Sllurp's point of view, like two
  independently reported antenna paths. The Speedway R420 extends the same
  principle to four ports.
* **Impinj xPortal** -- uses integrated internal antennas rather than exposed
  external antenna connectors. Where the reader reports distinct antenna IDs,
  Sllurp preserves those paths the same way as external ports.
* **Honeywell/Intermec IF2** -- supports up to four electronically switched
  antennas. With two or more active antennas, the same ``(EPC, AntennaID)``
  rule applies when software-memory deduplication is used.
* **Zebra FX9600 and FXR90 family** -- multi-port fixed readers can use either
  a dual-element panel such as the AN440 or multiple separate single-port
  antennas. The topology determines whether cross-port preservation matters.

The important distinction is therefore:

::

    single antenna path
        repeated EPC over time may be deduplicated
        no second antenna observation exists to preserve

    two or more antenna paths
        repeated EPC over time may be deduplicated
        AND the same EPC may be seen on multiple paths
        RF telemetry mode preserves each antenna/path observation

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
