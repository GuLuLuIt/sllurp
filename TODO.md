# TODO

This is the engineering roadmap after the core correctness pass on `fix/core-state-bugs-2026-09-11`.

The immediate correctness hazards found in `BUGS.md` have been fixed or fenced. Items below are larger capabilities/refactors that should stay incremental and test-driven.

```text
small focused change
       |
       v
state-machine/unit tests
       |
       v
CI: Python 3.10 -> 3.14 + coverage + wheel smoke
       |
       v
hardware interoperability validation
       |
       v
merge
```

## Completed in the core bug pass

- [x] Normalize legacy `Channelist` before validating frequency configuration.
- [x] Make generic `update_config()` safe by allowing replacement only while fully disconnected.
- [x] Validate proposed config before committing generic replacement.
- [x] Invalidate stale ROSpec/reported-state caches after disconnected config replacement.
- [x] Rebuild software dedup state consistently on reader config replacement.
- [x] Preserve explicit LLRP ports and update implicit default port when TLS mode changes.
- [x] Use stable callback snapshots so add/remove during dispatch cannot corrupt the current dispatch cycle.
- [x] Implement cancellable timed pause/resume.
- [x] Cancel/invalidate timed-pause resume across explicit resume, disconnect and protocol-session reset.
- [x] Add normalized `reader_config_summary` while keeping raw `reader_config` and the historical `parseReaderConfig()` return contract.
- [x] Add regression coverage for all of the above.

---

## 1. Transactional live dynamic configuration engine

**Priority:** High  
**Physical reader required to implement:** No  
**Hardware validation:** Strongly recommended

Generic replacement is now safe because it refuses live mutation. The next feature is to intentionally support selected live changes with a transaction model instead of reopening the old ambiguity.

### Target flow

```text
Application
    |
    | apply_config(new)
    v
+---------------------+
| validate proposal   |
+---------------------+
    |
    v
+---------------------+
| diff old vs new     |
+---------------------+
    |
    v
+-------------------------------+
| classify changed fields       |
|                               |
| A client-only                 |
| B live-safe                   |
| C ROSpec rebuild              |
| D reconnect                   |
+-------------------------------+
    |
    +---------+----------+----------+
    |         |          |          |
    v         v          v          v
 client    live op     pause +    reconnect
 only                  rebuild
    |         |          |          |
    +---------+----------+----------+
              |
              v
       verify final state
              |
       +------+------+
       |             |
    success        failure
       |             |
       v             v
     commit      rollback
                    |
              rollback fails
                    |
                    v
             clean disconnect
```

### Work items

- [x] Introduce an explicit transition object/result for live changes.
- [x] Compute structured old/new configuration diffs.
- [x] Define a policy table for each field: client-only, live-safe, ROSpec rebuild, reader config write, reconnect.
- [x] Capture previous known-good applied state before a multi-step transition.
- [x] Apply reader operations in deterministic order.
- [x] Commit desired/applied state only after all required operations succeed.
- [x] Roll back where protocol semantics make rollback trustworthy.
- [x] Enter a disconnected protocol state when rollback cannot guarantee a known reader state.
- [x] Test no-op/client-only updates to ensure they produce no reader traffic.
- [x] Rebuild software dedup state only after a successful reader-level transition.

### Likely classification starting point

```text
Setting                       Likely action
-------------------------------------------------------
logging/debug                 client-only
report selector               ROSpec rebuild
antennas                      ROSpec rebuild
TX power                      targeted live/rebuild
session                       ROSpec rebuild
Tari                          ROSpec rebuild
reader mode                   ROSpec rebuild
frequency/channel list        ROSpec/vendor dependent
vendor extensions             extension dependent
host/port/TLS endpoint        reconnect
```

---

## 2. Make desired, generated and applied state explicit

**Priority:** High

The new `reader_config_summary` gives us a first reader-reported view. The remaining architecture should stop treating three distinct concepts as interchangeable.

```text
+---------------------+
| desired config      |
| what app wants      |
+---------------------+
          |
          v
+---------------------+
| generated protocol  |
| ROSpec / AccessSpec |
+---------------------+
          |
          v
+---------------------+
| applied/reported    |
| what reader confirms|
+---------------------+
```

- [x] Introduce explicit desired/applied naming or structures.
- [x] Track generated ROSpec/AccessSpec independently from desired config.
- [x] Record acknowledgement/verification state for transitions.
- [x] Represent unknown/unconfirmed applied values honestly.
- [x] Make reconnect reconstruct state from desired config, not stale generated caches.
- [ ] Extend `reader_config_summary` only where standard LLRP or vendor adapters provide trustworthy evidence.

---

## 3. Improve request/deferred correlation

**Priority:** Medium-High  
**Physical reader required:** No

Current pending work is primarily grouped by expected response name. This prevents many duplicate outstanding request types, but it is restrictive and makes future management operations harder.

```text
Request A: GET_READER_CONFIG ID=100
Request B: GET_READER_CONFIG ID=101
        \                         /
         \                       /
          same response message type
```

Target:

```text
outbound request
      |
      v
pending[(response_type, message_id)]
      |
      v
incoming response
      |
extract type + ID
      |
      v
exact pending operation
```

- [x] Audit every `_deferreds` registration path.
- [x] Correlate pending operations by message ID where practical.
- [x] Validate response type in addition to ID.
- [x] Add request timeouts.
- [x] Cancel pending requests deterministically on disconnect/session reset.
- [x] Define late/unmatched/duplicate response policy.
- [x] Test response reordering and stale responses after reconnect.
- [ ] Only allow concurrent same-type requests if target readers behave predictably.

---

## 4. Callback registry synchronization stress testing

**Priority:** Medium

Stable snapshot dispatch is complete and fixes mutation-during-iteration behavior. A stronger concurrency stress harness is still useful for future no-GIL/free-threaded Python environments.

Current defined semantics:

```text
snapshot at dispatch start
          |
    +-----+-----+
    |           |
remove cb     add cb
    |           |
    +-----+-----+
          |
changes affect NEXT dispatch
```

- [x] Snapshot callback iteration.
- [x] Test self-removal.
- [x] Test callback added during dispatch.
- [x] Add sustained multi-thread add/remove stress tests.
- [x] Protect callback registry mutation/snapshot capture with an internal RLock.
- [x] Document callback ordering/snapshot semantics in public API docs.

---

## 5. Timed pause/resume hardware validation and polish

**Priority:** Medium

Timed pause/resume is implemented and covered in synthetic tests.

```text
INVENTORYING
     |
 pause(N)
     v
 PAUSING
     |
 disable ACK
     v
  PAUSED
     |
 cancellable timer
     v
 ENABLE_ROSPEC
     |
 enable ACK
     v
INVENTORYING
```

- [x] Validate duration values.
- [x] Schedule resume only after successful pause acknowledgement.
- [x] Cancel explicit/stale timers.
- [x] Prevent old-session timers from resuming a new/disconnected session.
- [x] Test automatic resume and disconnect-before-resume.
- [ ] Validate timing and firmware sequencing on representative physical readers.
- [x] Add public docs/examples for timed pause.
- [ ] Consider an explicit `STATE_RESUMING` only if it materially improves API clarity.

---

## 6. Expand normalized reader-side configuration

**Priority:** Medium

`reader_config_summary` now normalizes a useful first set of standard fields while raw decoded data remains available.

- [x] antenna connected/gain state
- [x] antenna configuration keyed by antenna ID
- [x] keepalive state
- [x] event notification state
- [x] access report state
- [x] events/reports state
- [x] GPI/GPO entries
- [ ] Add captured GET_READER_CONFIG fixtures from Zebra readers.
- [ ] Add captured fixtures from Impinj readers.
- [ ] Add captured fixtures from Honeywell/Intermec readers.
- [ ] Normalize additional standard fields only when their semantics are stable.
- [ ] Keep vendor-specific settings namespaced/adapter-specific rather than pretending they are universal LLRP.

---

## 7. Deterministic failure-injection harness

**Priority:** High leverage  
**Physical reader required:** No

The safest way to keep improving the large core file is a programmable fake reader.

```text
Sllurp client
     |
     v
+-------------------+
| fake transport    |
+-------------------+
     |
     v
+-----------------------------+
| scripted fake reader        |
|                             |
| ADD_ROSPEC    -> success    |
| ENABLE_ROSPEC -> reject     |
| DELETE_ROSPEC -> timeout    |
| socket read   -> disconnect |
+-----------------------------+
```

- [x] Script expected outbound sequence.
- [x] Emit chosen success/failure LLRPStatus values.
- [x] Delay/reorder/duplicate responses.
- [x] Drop transport at selected transition points.
- [x] Inject partial and coalesced frames.
- [x] Simulate reconnect with stale pending operations.
- [x] Assert callbacks, deferred cleanup, timers and final state.
- [x] Use this harness as the gate for the future transactional live-config engine.

---

## 8. Incrementally reduce transport/state-machine coupling

**Priority:** Long-term

Avoid a one-shot rewrite of `llrp.py`. Extract tested ownership boundaries incrementally.

```text
+------------------+
| Transport        |
| socket/TLS/I/O   |
+------------------+
          |
          v
+------------------+
| Protocol engine  |
| framing/requests |
+------------------+
          |
          v
+------------------+
| Reader state     |
| ROSpec/config    |
+------------------+
          |
          v
+------------------+
| Public client API|
+------------------+
```

- [x] Make timer ownership explicit per state/operation.
- [x] Separate request correlation from socket implementation.
- [x] Keep transport read/write ownership explicit.
- [x] Extract one boundary per focused PR with state-transition tests.
- [ ] Avoid file splitting that merely moves complexity without clarifying ownership.

---

# Hardware integration matrix

Hardware does not block the software fixes above, but it is the final interoperability gate.

## Reader families

- [ ] Zebra fixed reader
- [ ] Impinj fixed reader
- [ ] Honeywell/Intermec reader

## Scenarios

- [ ] Plain LLRP initial connection/inventory.
- [ ] Secure LLRP/TLS where supported.
- [ ] Physical network interruption/reconnect.
- [ ] Timed pause/resume.
- [ ] Reader reboot with client running.
- [ ] Multiple reconnect cycles with no stale timers/deferreds.
- [ ] Reader invalid-setting rejection.
- [ ] Compare requested config with GET_READER_CONFIG reported state.
- [ ] Future transactional live config changes once implemented.

Hardware validation answers firmware-specific questions; Python concurrency, validation, timer cancellation, framing and state-machine invariants remain CI responsibilities.


## Software completion boundary

All software-only items from this review are now implemented or explicitly
classified with safe behavior.  Remaining unchecked items require physical
reader captures/firmware interoperability validation, or are optional future
API choices rather than correctness gaps.
