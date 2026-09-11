# TODO

This file is the engineering roadmap for follow-up work from the deep runtime/state-machine review. Items here are larger improvements or refactors rather than small isolated bugs. The goal is to make `sllurp/llrp.py` safer to evolve without an all-at-once rewrite.

The intended development model is:

```text
small focused change
       |
       v
state-machine/unit tests
       |
       v
CI across supported Python versions
       |
       v
hardware interoperability validation
       |
       v
merge
```

Physical readers are valuable for final validation, but most core work should be fully developable and testable without hardware.

---

## 1. Build a controlled dynamic configuration engine

**Priority:** High  
**Physical reader required to implement:** **No**  
**Hardware validation:** Strongly recommended

Today, changing configuration at runtime is too close to assigning a new Python object. The target is a real transition engine that understands the difference between desired configuration and configuration already active in the reader.

### Target flow

```text
Application
    |
    | update_config(new_config)
    v
+---------------------+
| validate new config |
+---------------------+
    |
    v
+---------------------+
| diff old vs new     |
+---------------------+
    |
    v
+-------------------------------+
| classify each changed field   |
|                               |
| A = client-only               |
| B = live-safe reader update   |
| C = ROSpec rebuild required   |
| D = reconnect required        |
+-------------------------------+
    |
    +---------+----------+----------+
    |         |          |          |
    v         v          v          v
 client    live apply   pause +    reconnect
 only                   rebuild
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
     commit      rollback or
                 clean disconnect
```

### Work items

- [ ] Replace raw live `update_config()` assignment with a controlled transition object or equivalent mechanism.
- [ ] Validate the entire proposed configuration before mutating runtime state.
- [ ] Compute a structured diff between old and proposed settings.
- [ ] Define a policy table for every runtime setting: client-only, live-safe, inventory restart, or reconnect required.
- [ ] Pause/stop inventory only when the changed fields actually require it.
- [ ] Regenerate ROSpec state automatically when ROSpec-affecting fields change.
- [ ] Apply reader-side changes in deterministic order.
- [ ] Mark a new config as applied only after all required reader operations succeed.
- [ ] Roll back to the previous known-good state when safe.
- [ ] Cleanly disconnect when rollback cannot guarantee a known reader state.
- [ ] Preserve dedup state only when the identity semantics remain compatible; otherwise reset it explicitly.

### Suggested classification table

The exact table should be validated against current code, but the implementation should make this sort of distinction explicit:

```text
Setting                       Likely action
-----------------------------------------------------
logging/debug                 client-only
callback registration         client-only/thread-safe
report selector               ROSpec rebuild
antennas                      ROSpec rebuild
TX power                      ROSpec/update path
session                       ROSpec rebuild
Tari                          ROSpec rebuild
reader mode                   ROSpec rebuild
frequency/channel list        ROSpec or reader config
vendor extensions             extension-dependent
host/port/TLS endpoint        reconnect
```

### Acceptance tests

- [ ] Update from CONNECTED state.
- [ ] Update while INVENTORYING.
- [ ] Update while PAUSED.
- [ ] Multiple changed fields in one request.
- [ ] No-op update produces no unnecessary reader traffic.
- [ ] Reader rejects first, middle and final transition step.
- [ ] Reconnect after success reproduces the same configuration.
- [ ] Rollback failure ends in an explicit safe state.

---

## 2. Make desired, generated and applied state explicit

**Priority:** High  
**Physical reader required:** **No**

One source of complexity is that configuration state is spread across attributes and objects. Future work should make the state layers explicit.

### Proposed mental model

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
| applied reader      |
| confirmed by reader |
+---------------------+
```

These are related but not interchangeable.

### Work items

- [ ] Introduce explicit naming/structures for desired configuration.
- [ ] Keep generated ROSpec/AccessSpec state separately identifiable.
- [ ] Track what the reader has actually acknowledged/applied.
- [ ] Expose unknown/unconfirmed applied state honestly.
- [ ] Make reconnect restore from desired state rather than accidental stale caches.

### Why this matters

Without this separation, code can accidentally assume:

```text
self.config changed
      ==
reader accepted change
```

That assumption is unsafe for any real networked device.

---

## 3. Improve request/deferred correlation

**Priority:** Medium to High  
**Physical reader required:** **No**

Pending response handling should be reviewed so future management and dynamic operations can safely support more than one outstanding request where the protocol allows it.

### Current conceptual limitation

A response type alone is not always enough to identify which request it belongs to:

```text
Request A: GET_READER_CONFIG  ID=100
Request B: GET_READER_CONFIG  ID=101
            |                      |
            +----------+-----------+
                       |
             same response type
```

The protocol already has message IDs, so the pending-operation model should evaluate using them as the primary correlation key.

### Target model

```text
outbound request
      |
      v
+------------------------+
| pending[(type, id)]    |
+------------------------+
      |
      v
incoming response
      |
      v
extract type + message ID
      |
      v
exact pending operation
```

### Work items

- [ ] Audit every current deferred/request registration path.
- [ ] Evaluate correlating pending requests by message ID, with response type as validation rather than sole identity.
- [ ] Define whether duplicate message IDs are impossible or explicitly rejected.
- [ ] Add timeout semantics for pending operations.
- [ ] Add cancellation semantics on disconnect/reconnect.
- [ ] Decide how unmatched and late responses are logged/handled.
- [ ] Allow safe concurrent requests only where Sllurp and target readers can support them predictably.

### Required tests

```text
normal response
late response
response after timeout
duplicate response
wrong message ID
wrong response type
reordered responses
disconnect with requests pending
reconnect with stale response arriving
```

No physical reader is necessary because all of these can be driven with synthetic LLRP messages.

---

## 4. Make callback registration and dispatch thread-safe

**Priority:** Medium  
**Physical reader required:** **No**

Callbacks are application code and must not be invoked while an internal registry lock is held.

### Preferred dispatch pattern

```text
              callback registry
                     |
                  LOCK
                     |
                     v
             snapshot callbacks
                     |
                 UNLOCK
                     |
          +----------+----------+
          |          |          |
          v          v          v
        cb A       cb B       cb C

       user code runs lock-free
```

### Work items

- [ ] Make add/remove/clear operations safe during active dispatch.
- [ ] Use snapshot iteration or another clearly documented strategy.
- [ ] Define callback ordering guarantees.
- [ ] Define whether a callback added during dispatch runs in the current or next dispatch cycle.
- [ ] Define whether a callback removed during dispatch can still run if it was already snapshotted.
- [ ] Keep application callback execution outside internal locks.
- [ ] Test callback self-removal.
- [ ] Test callback adding another callback.
- [ ] Test concurrent register/remove while reports are dispatched.

---

## 5. Implement reliable timed pause/resume

**Priority:** Medium  
**Physical reader required to implement:** **No**  
**Hardware recommended:** Yes for firmware timing

`pause(duration_seconds > 0)` should become a supported operation rather than an unfinished/error path.

### Desired behavior

```text
INVENTORYING
     |
 pause(5s)
     v
+-----------+
| PAUSING   |
+-----------+
     |
 reader confirms stop/pause
     v
+-----------+
| PAUSED    |
+-----------+
     |
 cancellable timer: 5 s
     v
+-----------+
| RESUMING  |
+-----------+
     |
     v
INVENTORYING
```

### Edge cases that must be defined

```text
pause -> disconnect before timer fires
pause -> explicit resume before timer fires
pause -> second pause changes duration
pause -> config update while paused
pause -> reconnect while timer is pending
pause -> reader rejects restart
```

### Work items

- [ ] Implement a cancellable resume timer.
- [ ] Ensure disconnect cancels timers deterministically.
- [ ] Ensure explicit resume cancels the pending automatic resume.
- [ ] Avoid multiple resume operations from racing timers/calls.
- [ ] Regenerate ROSpec only if state actually changed while paused.
- [ ] Verify state callbacks see a sensible sequence.

---

## 6. Expand `parseReaderConfig()` into useful normalized applied state

**Priority:** Medium  
**Physical reader required:** **No** if protocol fixtures exist

`parseReaderConfig()` currently contributes little useful normalized state. It should eventually support comparison of desired and actual reader configuration without pretending every vendor exposes every field identically.

### Data flow

```text
GET_READER_CONFIG_RESPONSE
           |
           v
+--------------------------+
| protocol decoder         |
+--------------------------+
           |
           v
+--------------------------+
| parseReaderConfig()      |
+--------------------------+
           |
           v
+--------------------------+
| normalized reader_config |
+--------------------------+
           |
           +----> application inspection
           |
           +----> dynamic update verification
```

### Work items

- [ ] Inventory which standard LLRP configuration parameters are already decoded.
- [ ] Normalize high-value fields first rather than trying to model every parameter at once.
- [ ] Keep raw decoded data available when useful.
- [ ] Represent unsupported/absent values as unknown rather than invented defaults.
- [ ] Keep vendor-specific extensions namespaced or adapter-specific.
- [ ] Add fixtures from representative readers as they become available.

### Hardware role

Implementation can start entirely from the LLRP specification and synthetic/captured frames. Real hardware is useful later for expanding the fixture corpus and confirming vendor-specific omissions or quirks.

---

## 7. Incrementally reduce transport/state-machine coupling

**Priority:** Long-term  
**Physical reader required:** **No**

`LLRPReaderClient` and `LLRPClient` currently share responsibility across transport lifecycle, protocol state, configuration state, timers, callbacks and reader operations. A full rewrite is not desirable; the goal is incremental separation behind tested interfaces.

### Current conceptual shape

```text
              llrp.py
                 |
      +----------+----------+
      |          |          |
   sockets     protocol    config
      |          |          |
    timers     ROSpec     callbacks
      \          |          /
       \         |         /
        +---- shared state-+
```

### Desired direction

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

### Work items

- [ ] Identify boundaries that can be extracted without changing public behavior.
- [ ] Keep transport read/write ownership explicit.
- [ ] Keep protocol request correlation independent from socket implementation.
- [ ] Make timers owned by the state that created them.
- [ ] Avoid broad file splitting unless tests prove behavior remains unchanged.
- [ ] Prefer one small extraction/refactor per PR.

---

## 8. Add a deterministic failure-injection test harness

**Priority:** High leverage  
**Physical reader required:** **No**

The safest way to improve the 90KB core file is to make failures programmable.

### Suggested fake-reader model

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
| on ADD_ROSPEC: success      |
| on ENABLE_ROSPEC: reject    |
| on DELETE_ROSPEC: timeout   |
| on socket read: disconnect  |
+-----------------------------+
```

### Work items

- [ ] Script expected outbound message sequence.
- [ ] Return chosen success/failure LLRP statuses.
- [ ] Delay or reorder responses.
- [ ] Drop the connection at selected points.
- [ ] Inject partial frames and multiple frames per receive call.
- [ ] Simulate reconnect with fresh and stale pending state.
- [ ] Assert emitted callbacks and final client state.

This harness should become the primary safety net for future state-machine work.

---

# Hardware integration matrix

After the software/state-machine work is green in CI, run real-reader validation where hardware is available.

```text
                        CI COMPLETE
                             |
                             v
                 +-----------------------+
                 | hardware validation   |
                 +-----------------------+
                     /       |       \
                    /        |        \
                   v         v         v
                Zebra     Impinj   Honeywell/
                                  Intermec
                   \         |         /
                    \        |        /
                     +-------+-------+
                             |
                             v
                 interoperability confidence
```

## Reader matrix

- [ ] Zebra fixed reader
- [ ] Impinj fixed reader
- [ ] Honeywell/Intermec reader

## Scenarios

- [ ] Plain LLRP initial connection and inventory.
- [ ] Secure LLRP/TLS where supported.
- [ ] Physical network interruption and reconnect.
- [ ] Live inventory configuration change.
- [ ] Reader-side invalid-setting rejection.
- [ ] Pause/resume timing.
- [ ] Reader reboot while client remains running.
- [ ] Multiple reconnect cycles with no stale timers/deferreds.
- [ ] Compare reported reader configuration with requested configuration where GET_CONFIG support allows it.

## What hardware validation is for

Hardware should answer questions that mocks cannot answer reliably:

```text
Does firmware acknowledge operations in the order expected?
Does a model silently clamp or ignore a setting?
What exact LLRPStatus does it return for rejected values?
How quickly does it close/reopen sockets during reboot?
Does secure LLRP behave differently from plain LLRP?
Do vendor extensions alter sequencing requirements?
```

It should **not** be required to prove basic Python concurrency, validation, transaction semantics, framing, timeout handling or state-machine correctness. Those belong in CI.
