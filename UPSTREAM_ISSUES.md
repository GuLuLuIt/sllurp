# Upstream issue drafts

Target upstream: https://github.com/sllurp/sllurp

These reports were verified against upstream `main` before drafting. An automated submission attempt was made through the connected GitHub integration, but GitHub returned **403 `Resource not accessible by integration`** for writes to `sllurp/sllurp`. They are kept here in ready-to-submit form rather than pretending they were filed successfully.

The fork-only `Channelist` -> `ChannelList` migration-order issue is intentionally **not** included: upstream still uses the historical `Channelist` key and does not have the same compatibility layer.

---

## Draft 1 — Timed `pause(duration_seconds > 0)` is intentionally non-functional

### Suggested title

`Timed pause(duration_seconds > 0) is intentionally non-functional`

### Body

`LLRPClient.pause(duration_seconds > 0)` on upstream `main` currently raises `ReaderConfigurationError` unconditionally behind a comment saying the path is temporary / not yet implemented.

That means the API accepts a duration parameter but cannot perform a timed pause.

#### Current flow

```text
INVENTORYING
     |
     | pause(5)
     v
+---------------------------+
| ReaderConfigurationError  |
| temporary guard           |
+---------------------------+
     |
     X  no timed resume
```

#### Expected behavior

A timed pause should stop/disable the active ROSpec, wait until the reader acknowledges the pause, then schedule exactly one cancellable resume:

```text
INVENTORYING
     |
 pause(5)
     v
 PAUSING
     |
 DISABLE_ROSPEC_RESPONSE success
     v
  PAUSED
     |
 5-second cancellable timer
     v
 ENABLE_ROSPEC
     |
 success
     v
INVENTORYING
```

Important lifecycle rules:

- the timer should only start after the reader confirms the pause;
- explicit `resume()` should cancel the automatic resume timer;
- disconnect/session reset must invalidate stale timers;
- a timer created for an old connection must never restart inventory on a new connection;
- invalid durations such as negative, NaN or infinity should fail clearly.

#### Why this matters

Applications needing bounded inventory pauses currently have to reimplement timer and lifecycle coordination outside Sllurp, where reconnect/shutdown races are harder to handle safely.

#### Suggested acceptance criteria

- `pause(0)` preserves indefinite-pause behavior.
- `pause(N)` for finite `N > 0` pauses then resumes once.
- disconnect cancels/invalidate the pending resume.
- explicit resume prevents the timer from issuing a second resume.
- a second timed pause deterministically replaces the first timer.
- tests use fake transport/state-machine responses; physical RFID hardware is not required for CI.

#### Reference implementation

A tested implementation exists in fork branch:

https://github.com/GuLuLuIt/sllurp/tree/fix/core-state-bugs-2026-09-11

---

## Draft 2 — Generic live `update_config()` can desynchronize client configuration from active reader state

### Suggested title

`update_config() can silently diverge from active ROSpec/reader state when called live`

### Body

Upstream `LLRPClient.update_config()` and `LLRPReaderClient.update_config()` directly replace the configuration object. The method itself warns that it is **"Not completely safe, to be used with caution."**

When the reader is already connected/inventorying, replacing `self.config` does not by itself guarantee that the cached ROSpec or reader-side configuration has been regenerated/applied.

#### Problem shape

```text
                 application
                     |
              update_config(X)
                     |
                     v
              self.config = X
                     |
          +----------+----------+
          |                     |
          v                     v
+------------------+   +------------------+
| cached ROSpec    |   | reader firmware  |
| OLD settings     |   | OLD settings     |
+------------------+   +------------------+
          \                     /
           +------ MISMATCH ---+
```

For example, Python can say antennas/session/power/report settings are new while the active ROSpec is still the old one. That makes it difficult for an application to know what is actually active.

#### Minimum safe fix

Until Sllurp has a transactional live-update engine, generic replacement should be atomic and allowed only while fully disconnected:

```text
update_config(new)
       |
       v
validate full proposal
       |
       v
reader fully disconnected?
     /      \
   no        yes
   |          |
   v          v
reject      commit replacement
without     + invalidate stale
mutation      generated state
```

This does not prevent targeted methods from implementing explicit live transitions; it only stops a generic assignment from claiming settings that were never applied.

#### Longer-term direction

A real live-update API should model:

```text
validate -> diff -> classify changes -> pause/rebuild/apply
                                      -> success: commit
                                      -> failure: rollback or disconnect
```

#### Suggested acceptance criteria

- proposed config is validated before mutation;
- generic replacement while connected/inventorying is either explicitly supported transactionally or rejected before mutation;
- cached ROSpec/reader-side state cannot silently contradict `self.config`;
- reconnect after a successful config change reproduces the same desired settings;
- failure leaves a known state, not a half-applied one.

#### Hardware

No physical reader is required for the safety invariant. Fake transport/state-machine tests can verify mutation ordering. Hardware is useful later for a transactional live-update feature.

#### Reference implementation

The fork currently chooses the conservative disconnected-only behavior:

https://github.com/GuLuLuIt/sllurp/tree/fix/core-state-bugs-2026-09-11

---

## Draft 3 — Callback list mutation during dispatch can skip callbacks / produce unstable semantics

### Suggested title

`Callback registration/removal can mutate lists while reader thread is dispatching them`

### Body

Upstream stores state/message/tag/event/disconnect callbacks in mutable lists and iterates those lists directly while invoking user code. Applications are allowed to add/remove/clear callbacks, including from callbacks themselves or from another thread.

#### Current concurrency shape

```text
Reader thread                         Application/callback thread
-------------                         ---------------------------
for cb in callbacks:                  callbacks.remove(cb2)
    cb(event)          <---------->   callbacks.append(cb3)

            same mutable list during iteration
```

Python list mutation during iteration can lead to skipped callbacks and surprising ordering even when it does not raise an exception.

#### Suggested dispatch semantics

Use a stable snapshot for each dispatch:

```text
callback registry
       |
       v
 snapshot callbacks
       |
       +----------+----------+
       |          |          |
       v          v          v
      cb1        cb2        cb3

mutations affect the NEXT dispatch cycle
```

User callback code should run without holding an internal registry lock.

A simple policy can be:

- preserve registration order within a captured snapshot;
- removal during dispatch does not retroactively remove an already-snapshotted callback;
- addition during dispatch first applies to the next dispatch;
- callback exceptions keep the existing continue/log policy.

#### Suggested acceptance criteria

- callback self-removal does not skip later callbacks in the current dispatch;
- callback addition during dispatch starts on the next dispatch;
- clear/remove/add cannot corrupt active iteration;
- state, message, tag-report, event and disconnect callback paths use the same documented semantics;
- tests do not require physical RFID hardware.

#### Reference implementation

The fork uses tuple snapshots at dispatch sites and adds regression tests:

https://github.com/GuLuLuIt/sllurp/tree/fix/core-state-bugs-2026-09-11

---

## Related upstream item, not filed as a duplicate

Upstream issue #210, **"How to safely read once?"**, reports reader-state/lifecycle problems across repeated connect/read/disconnect operations:

https://github.com/sllurp/sllurp/issues/210

It may overlap broadly with state-machine lifecycle work, but it is not a direct duplicate of the three focused issues above.

---

## Enhancements intentionally not labeled as upstream bugs

The following are useful follow-up work but are better proposed as enhancements/design changes:

- correlate pending responses using LLRP message IDs rather than relying primarily on response message type;
- add timeout/cancellation semantics for pending requests;
- expand `parseReaderConfig()` into normalized reader-reported state;
- build a transactional live dynamic configuration engine.
