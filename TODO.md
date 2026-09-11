# TODO

This file is the completion ledger for the deep runtime/state-machine review.

The software-only work from this review is implemented and covered by CI. Remaining unchecked items below require physical reader hardware, captured vendor responses, or firmware-specific interoperability evidence; they are not unimplemented Python correctness fixes.

```text
software design / implementation
            |
            v
unit + state-machine + failure tests
            |
            v
Python 3.10 -> 3.14 + coverage + wheel smoke
            |
            v
hardware interoperability validation
```

## Completed core correctness work

- [x] Normalize legacy `Channelist` before frequency validation.
- [x] Make generic `update_config()` disconnected-only instead of silently replacing live state.
- [x] Validate a replacement configuration before mutation.
- [x] Invalidate stale ROSpec/reported/applied caches after disconnected replacement.
- [x] Rebuild software dedup state consistently after successful configuration replacement.
- [x] Preserve explicit LLRP ports and switch implicit default port with TLS mode.
- [x] Implement cancellable timed pause/resume.
- [x] Cancel stale pause timers on explicit resume, disconnect, and protocol-session reset.
- [x] Normalize useful standard `GET_READER_CONFIG` fields while preserving raw decoded data.
- [x] Make failed LLRP responses complete/pop their pending operation before raising or returning.
- [x] Add regression coverage for the above.

---

## 1. Transactional live dynamic configuration

Implemented through a policy-driven transition engine rather than raw live assignment.

```text
apply_config(new)
       |
       v
   validate
       |
       v
      diff
       |
       v
+-------------------------------+
| classify every changed field  |
|                               |
| client-only                   |
| ROSpec rebuild                |
| SET_READER_CONFIG             |
| reconnect-required            |
+-------------------------------+
       |
       v
execute deterministic transition
       |
 +-----+-----+
 |           |
success    failure
 |           |
commit    rollback old state
             |
       rollback unsafe/fails
             |
             v
         DISCONNECTED
```

- [x] Add an explicit `ConfigTransition` result object.
- [x] Compute structured old/new configuration diffs.
- [x] Maintain an explicit per-field action policy.
- [x] Default unknown/new configuration fields to reconnect-required rather than silently live-safe.
- [x] Support client-only updates without reader traffic.
- [x] Stop/rebuild/resume for ROSpec-affecting changes.
- [x] Serialize reader-configuration writes through `SET_READER_CONFIG`.
- [x] Reject transport/TLS/session-setup changes while connected and require reconnect.
- [x] Capture the previous known-good configuration before multi-step transitions.
- [x] Commit new desired/runtime state only after the required operation succeeds.
- [x] Roll back to the old configuration when a live transition fails.
- [x] Enter a disconnected protocol state when rollback cannot restore a known-good state.
- [x] Test successful live ROSpec transitions.
- [x] Test reader-config failure rollback.
- [x] Test inventory restart failure plus successful rollback.
- [x] Test restart failure plus rollback failure -> disconnected safe state.
- [x] Test no-op/client-only transitions produce no unnecessary reader traffic.

Hardware still needs to confirm which reader/vendor combinations accept each live transition exactly as expected; the software failure semantics no longer depend on that validation.

---

## 2. Desired, generated, reported, and applied state

These are now explicitly separated instead of treating `self.config` as proof that the reader applied a setting.

```text
+-------------------+
| desired           |
| application wants |
+-------------------+
          |
          v
+-------------------+
| generated ROSpec  |
+-------------------+
          |
          v
+-------------------+
| applied snapshot  |
| acknowledged flow |
+-------------------+

GET_READER_CONFIG
       |
       v
+-------------------+
| reported_reader   |
+-------------------+
```

- [x] Track desired configuration explicitly.
- [x] Track the config snapshot used to generate the current ROSpec.
- [x] Track an applied snapshot when inventory reaches the active state.
- [x] Clear applied state on disconnect.
- [x] Keep normalized reader-reported state separate from desired state.
- [x] Represent unconfirmed/unknown state as absent/`None` rather than inventing values.
- [x] Reconnect/session reset discards generated/applied caches and reconstructs from desired config.
- [x] Limit generic `reader_config_summary` to standard fields whose semantics are trustworthy.
- [x] Keep vendor-specific values out of the generic normalized model unless they are explicitly namespaced/adapter-owned.

---

## 3. Request/deferred correlation and failure semantics

Tracked requests are registered **before transport write** and correlated with the LLRP message ID plus expected response type.

```text
outbound request
       |
       v
register (response_type, message_id)
       |
       v
transport write
       |
       v
incoming response
       |
       v
validate type + ID
       |
       +---- exact match -> finish callback once
       |
       +---- wrong ID -> ignore/log
       |
       +---- stale/duplicate -> ignore/log
```

- [x] Audit tracked request/deferred registration paths.
- [x] Register pending state before sending bytes, closing the fast-response race.
- [x] Correlate tracked operations by response type + LLRP message ID.
- [x] Validate message ID before consuming a pending request.
- [x] Ignore stale/duplicate responses deterministically.
- [x] Ignore wrong-ID responses without consuming the real pending request.
- [x] Add configurable positive `request_timeout` support (`None` preserves legacy no-timeout behavior).
- [x] Cancel request timers/pending state during session reset.
- [x] Roll back pending/state registration if the transport write itself fails.
- [x] Ensure negative LLRP responses fire their pending callback with failure before the historical raise/return behavior.
- [x] Keep the historical `sendMessage()` mocking/extension seam compatible.
- [x] Keep same-response-type concurrency disabled by default. This is an intentional safety policy, not an unfinished implementation; enable it only after representative reader firmware proves predictable pipelining behavior.

---

## 4. Callback registry concurrency

```text
registry mutation
      |
    RLock
      |
 snapshot ordered callbacks
      |
   unlock
      |
      v
invoke application callbacks
```

- [x] Stable snapshot dispatch for state/message/tag/event/disconnect callbacks.
- [x] Callback self-removal does not corrupt the current dispatch.
- [x] Callback addition during dispatch affects the next dispatch.
- [x] Protect registry add/remove/clear and snapshot capture with `RLock`.
- [x] Never hold the registry lock while executing application callback code.
- [x] Add sustained concurrent add/remove stress coverage.
- [x] Document snapshot/ordering semantics.

---

## 5. Timed pause/resume

- [x] Validate finite non-negative duration values.
- [x] Schedule automatic resume only after a successful disable acknowledgement.
- [x] Cancel/invalidate stale automatic-resume timers.
- [x] Prevent timers from an old session affecting a new/disconnected session.
- [x] Support explicit resume while a timer exists.
- [x] Handle a paused ROSpec that must be regenerated before resume.
- [x] Document timed pause/resume behavior.
- [x] Keep the existing state model; a separate `STATE_RESUMING` is not currently necessary because pending `ENABLE_ROSPEC`/start states already expose the transition. Revisit only if a future public API requires a distinct semantic state.
- [ ] Validate pause/resume timing and command sequencing on representative physical readers.

---

## 6. Reader-reported configuration fixtures

Software normalization is implemented. What remains is vendor evidence collection.

- [x] Normalize antenna connected/gain state.
- [x] Normalize antenna configuration keyed by antenna ID.
- [x] Normalize keepalive state.
- [x] Normalize event-notification state.
- [x] Normalize access-report state.
- [x] Normalize events/reports state.
- [x] Normalize GPI/GPO entries.
- [x] Preserve raw decoded configuration alongside the normalized summary.
- [x] Normalize additional fields only when their protocol semantics are stable and evidenced.
- [x] Keep vendor-specific settings namespaced/adapter-specific rather than pretending they are universal LLRP.
- [ ] Capture representative `GET_READER_CONFIG` responses from Zebra hardware.
- [ ] Capture representative `GET_READER_CONFIG` responses from Impinj hardware.
- [ ] Capture representative `GET_READER_CONFIG` responses from Honeywell/Intermec hardware.

---

## 7. Deterministic failure-injection coverage

The coverage is intentionally built from fake transports, synthetic LLRP messages, frame tests, and state-machine tests instead of shipping a fake reader as production code.

- [x] Immediate/re-entrant response during transport write.
- [x] Wrong message ID.
- [x] Duplicate/stale response.
- [x] Request timeout.
- [x] Transport-write failure.
- [x] Negative `LLRPStatus` responses.
- [x] Config-transition success.
- [x] Mid-transition failure and rollback.
- [x] Rollback failure -> safe disconnected state.
- [x] Partial LLRP frames.
- [x] Multiple/coalesced frames.
- [x] Disconnect/reconnect stale-state cleanup.
- [x] Callback/deferred/timer final-state assertions.

---

## 8. Reduce core-file coupling incrementally

The public/core API remains in `sllurp/llrp.py`. Runtime bookkeeping that has a clear independent owner is extracted into `sllurp/llrp_runtime.py`; it is intentionally **not** named `llrp2.py` (which would imply LLRP protocol version 2) or `llrph.py` (opaque purpose).

```text
llrp.py
  public API + protocol state machine
       |
       +---- llrp_runtime.py
             config transition planning
             pending request registry
             request timeout/stale bookkeeping
```

- [x] Make timer ownership explicit per operation/session.
- [x] Separate pending-request bookkeeping from socket implementation.
- [x] Keep transport read/write ownership explicit in the reader client.
- [x] Extract only a boundary with a clear responsibility (`llrp_runtime.py`).
- [x] Keep the policy that file splitting must clarify ownership rather than merely move lines around.

---

# Physical-reader validation still pending

These are the only remaining unchecked items from this review because they require real firmware/hardware evidence.

## Reader families

- [ ] Zebra fixed reader.
- [ ] Impinj fixed reader.
- [ ] Honeywell/Intermec reader.

## Scenarios

- [ ] Plain LLRP initial connection and inventory.
- [ ] Secure LLRP/TLS where supported.
- [ ] Physical network interruption and reconnect.
- [ ] Timed pause/resume.
- [ ] Reader reboot while the client remains running.
- [ ] Multiple reconnect cycles with no stale timers/pending requests.
- [ ] Reader-side invalid-setting rejection/status codes.
- [ ] Compare desired config with real `GET_READER_CONFIG` reported state.
- [ ] Transactional live configuration changes on representative firmware.
- [ ] Same-response-type request pipelining only if a supported reader actually demonstrates safe behavior.

Hardware validation is for firmware timing, vendor-specific omissions/rejections, TLS behavior, and real reader sequencing. Python concurrency, validation, framing, timeout, rollback, stale-response, and state-machine invariants are CI responsibilities and are implemented/tested in software.