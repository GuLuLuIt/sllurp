Report cadence and inventory lifetime
=====================================

LLRP models report delivery and inventory lifetime as separate controls:

* ``ROReportSpec`` controls when a reader emits an ``RO_ACCESS_REPORT``.
* ``AISpecStopTrigger`` controls when the inventory AISpec ends. Ending an
  AISpec can interrupt and restart RF inventory when the ROSpec repeats.

Continuous N-tag reporting
--------------------------

Use ``ro_report_every_n_tags`` to request a report after a specific number of
tag observations while leaving the AISpec lifetime unchanged::

    from sllurp.llrp import LLRPReaderConfig

    config = LLRPReaderConfig({
        "ro_report_every_n_tags": 1,
    })

The value must be an integer from 1 through 65535. With the value above,
Sllurp generates the following relevant structure::

    AISpecStopTrigger:
        AISpecStopTriggerType: Null
        DurationTriggerValue: 0
    ROReportSpec:
        ROReportTrigger: Upon_N_Tags_Or_End_Of_AISpec
        N: 1

The equivalent inventory command is::

    sllurp inventory --ro-report-every-n-tags 1 READER_HOST

Legacy AISpec-stop behavior
---------------------------

``report_every_n_tags`` and ``report_timeout_ms`` retain their historical
behavior for compatibility. Despite the legacy name, they configure a tag
observation ``AISpecStopTrigger``. For example::

    config = LLRPReaderConfig({
        "report_every_n_tags": 1000,
        "report_timeout_ms": 1000,
    })

produces the following relevant structure::

    AISpecStopTrigger:
        AISpecStopTriggerType: Tag observation
        TagObservationTrigger:
            TriggerType: UponNTags
            NumberOfTags: 1000
            Timeout: 1000
    ROReportSpec:
        ROReportTrigger: Upon_N_Tags_Or_End_Of_AISpec
        N: 0

This ends the AISpec after 1000 observations or 1000 milliseconds, causing
accumulated observations to be reported at the inventory boundary. The legacy
CLI form is ``--report-every-n-tags`` (or ``-n``) and has the same AISpec-stop
semantics.

The controls can be combined. For example,
``ro_report_every_n_tags=10`` and ``report_every_n_tags=1000`` requests reports
every 10 observations before the AISpec eventually ends at 1000 observations.
Neither setting overrides the other.

Time-based continuous reporting
-------------------------------

Sllurp does not translate ``report_timeout_ms`` into continuous timed report
delivery. It remains an AISpec-stop timeout. The additional time-based
``ROReportTrigger`` names found in the protocol table are not selected by this
API because they are not portable across all supported LLRP versions and
readers. Use an authoritative version- or vendor-specific capability before
requesting non-standard timed report behavior.

Reader-side timed deduplication also controls ``ROReportSpec`` on supported
Zebra/Motorola readers. When explicit N-tag report cadence is requested,
``dedup_backend="auto"`` falls back to memory and
``dedup_backend="hardware"`` is rejected rather than overwriting the requested
report cadence.
