# Known Bugs and Resolutions

This document records correctness issues found during the deep runtime/state-machine review and how they were resolved on `fix/core-state-bugs-2026-09-11`.

Core rule:

> Core LLRP correctness must be reproducible in CI with fake transports, synthetic frames and deterministic state-machine tests. Physical readers are the final interoperability layer, not a prerequisite for fixing Python/state-machine bugs.

## Status summary

| # | Finding | Severity | Status | Hardware needed to fix? |
|---|---|---:|---|---|
| 1 | Legacy `Channelist` normalized after validation | Medium | **Fixed** | No |
| 2 | Generic live `update_config()` could desynchronize desired/applied state | High | **Fixed / made safe** | No |
| 3 | Callback collections could mutate during dispatch | Medium-High | **Fixed** | No |
| 4 | Generic live config had no transaction/rollback semantics | High | **Fixed by prohibiting unsafe generic live replacement** | No |
| 5 | `parseReaderConfig()` provided no normalized reader-side state | Medium | **Fixed** | No |

The remaining *feature* work for a fully transactional live configuration engine is tracked in `TODO.md`; it is no longer treated as an unfenced correctness bug because generic `update_config()` now refuses unsafe live replacement.

---

## 1. Legacy frequency compatibility was validated before migration — FIXED

**Area:** `LLRPReaderConfig.validate_config()`  
**Resolution:** normalize before validation.

### Previous failure

```text
legacy config
    |
    v
Channelist=[1]
    |
    v
validate ChannelList     <-- missing
    |
    X validation error
    |
    v
migrate legacy key       <-- unreachable/too late
```

### Current flow

```text
legacy or modern config
         |
         v
+------------------------+
| normalize keys first   |
| Channelist ->          |
| ChannelList            |
+------------------------+
         |
         v
+------------------------+
| validate channel list  |
+------------------------+
         |
         v
       READY
```

If both keys are present, modern `ChannelList` wins and the legacy spelling is discarded. Invalid values are still rejected after normalization.

### Regression coverage

- legacy-only `Channelist`
- modern-only `ChannelList`
- both keys present
- validation still runs on normalized values

**Hardware:** not required.

---

## 2. Generic `update_config()` could leave Python and reader state inconsistent — FIXED / FENCED

**Area:** `LLRPClient.update_config()` and `LLRPReaderClient.update_config()`

### Previous risk

A raw assignment could make the application believe new configuration was active while the cached ROSpec and reader were still using old settings:

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

### Current safety model

Generic replacement is now **atomic and disconnected-only**:

```text
update_config(new)
       |
       v
validate complete proposal
       |
       v
fully disconnected?
   /          \
 no            yes
 |              |
 v              v
reject       build dependent
without      local state first
mutation         |
                 v
             commit swap
                 |
                 v
          invalidate stale
          ROSpec/reported state
```

The call raises `ReaderConfigurationError` before mutation if a socket/thread/protocol session is active. Targeted live setters that already implement their own state transition remain separate.

`LLRPReaderClient` also rebuilds the software deduplicator before committing the new config. When the LLRP port was implicit, changing TLS mode updates the default port between 5084 and 5085; an explicitly supplied custom port is preserved.

### Why this counts as a bug fix

The old API could silently claim a configuration that was never applied. The new API cannot enter that ambiguous state through generic replacement. A future transactional live-update engine is an enhancement, tracked in `TODO.md`.

### Regression coverage

- connected/inventorying replacement is rejected
- rejection does not mutate current config or cached ROSpec
- disconnected replacement succeeds
- dedup state is rebuilt consistently
- implicit TLS port updates
- explicit custom port remains unchanged

**Hardware:** not required for the safety fix. Hardware remains useful when a future live-update engine is implemented.

---

## 3. Callback collections could mutate while dispatch was active — FIXED

**Area:** state, message, tag-report, event and disconnect callbacks.

### Previous behavior

```text
Reader thread                         Application/callback thread
-------------                         ---------------------------
for cb in callbacks:                  callbacks.remove(cb2)
    cb(event)          <---------->   callbacks.append(cb3)

           same mutable list during iteration
```

Python list mutation during iteration can skip entries or make dispatch semantics surprising even without an exception.

### Current behavior: stable dispatch snapshot

```text
callback registry
       |
       v
 tuple(snapshot)
       |
       +----------+----------+
       |          |          |
       v          v          v
      cb1        cb2        cb3

registry mutations affect NEXT dispatch
```

Every user-callback dispatch now iterates a tuple snapshot. Application callback code is not run while holding an internal registry lock.

Defined semantics:

- a callback removed during a dispatch may still run if it was already in that dispatch snapshot;
- the removal takes effect on the next dispatch;
- a callback added during dispatch first runs on the next dispatch;
- ordering remains registration order for the captured snapshot.

### Regression coverage

- callback removes itself
- current snapshot still completes
- removed callback is absent next dispatch
- callback adds another callback
- newly added callback starts next dispatch

**Hardware:** not required.

---

## 4. Generic live configuration had no rollback semantics — FIXED AS A SAFETY BUG; TRANSACTIONAL LIVE UPDATE REMAINS TODO

### Previous unsafe shape

```text
old working state
      |
 stop inventory     OK
      |
 delete ROSpec      OK
      |
 add new ROSpec     FAIL
      |
      X

Possible result:
  self.config = NEW
  reader state = neither clearly OLD nor NEW
```

There was no general transaction object capable of rolling back every multi-step live configuration change.

### Current mitigation

The generic `update_config()` path no longer attempts such a transition while connected. It rejects the operation before mutating state:

```text
connected + generic update
          |
          v
+---------------------------+
| reject before mutation    |
+---------------------------+
          |
          v
known old state remains valid
```

This removes the correctness bug without pretending a partial transaction implementation is safe.

### Remaining enhancement

A future live configuration engine should explicitly model:

```text
capture old applied state
          |
          v
validate + diff
          |
          v
apply ordered transition
      /         \
 success       failure
   |             |
 commit       rollback
                 |
          rollback fails
                 |
                 v
          clean disconnect
```

That work is in `TODO.md` and requires a larger failure-injection/state-transition design.

**Hardware:** not required for the current safety fix; recommended for future live-update interoperability testing.

---

## 5. `parseReaderConfig()` provided no normalized applied state — FIXED

### Previous behavior

```text
GET_READER_CONFIG_RESPONSE
          |
          v
raw reader_config stored
          |
          v
parseReaderConfig()
          |
          X  no normalized result
```

### Current behavior

The raw decoded response is preserved for compatibility and a second normalized view is maintained in `reader_config_summary`:

```text
GET_READER_CONFIG_RESPONSE
          |
          +------------------------+
          |                        |
          v                        v
+-------------------+    +-------------------------+
| raw reader_config |    | parseReaderConfig()     |
| unchanged         |    +-------------------------+
+-------------------+                 |
                                      v
                           +-------------------------+
                           | reader_config_summary   |
                           | standard useful fields  |
                           +-------------------------+
```

Currently normalized where present:

- antenna connected/gain state by antenna ID
- antenna configuration by antenna ID
- keepalive configuration
- reader-event notification configuration
- access-report configuration
- events/reports configuration
- GPI state list
- GPO state/write list

Missing optional fields stay absent; defaults are not invented. The historical method return contract remains `None`, so existing callers are not forced to change.

### Regression coverage

- raw reader configuration remains available
- normalized antenna properties/configuration
- normalized keepalive/GPI data
- non-dictionary input is rejected clearly
- historical `None` return behavior is preserved

**Hardware:** not required for implementation. Captured real-reader responses can expand the fixture corpus later.

---

# Validation layers

```text
                    SOFTWARE VALIDATION
                           |
         +-----------------+-----------------+
         |                                   |
         v                                   v
 state-machine/unit tests              protocol fixtures
 fake transport                        synthetic frames
 timer tests                           callback mutation tests
         |                                   |
         +-----------------+-----------------+
                           |
                           v
                        CI GREEN
                           |
                           v
                  HARDWARE VALIDATION
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
     Zebra              Impinj          Honeywell/
                                        Intermec
```

Hardware validation should focus on firmware timing, rejection codes, reconnect behavior, secure LLRP/TLS and vendor quirks. Basic Python validation, timer ownership, config atomicity and callback dispatch belong in CI.
