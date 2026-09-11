# Known Bugs

This file tracks confirmed or high-confidence correctness issues discovered during the deep runtime/state-machine review. These items are intentionally separated from broad cleanup work so they can be fixed with focused tests and without turning `sllurp/llrp.py` into an all-at-once rewrite.

The guiding rule for this list is:

> Core LLRP behavior must be reproducible in CI using fake transports, synthetic LLRP frames and deterministic state-machine tests. Physical RFID readers are a final interoperability layer, not a prerequisite for ordinary bug fixing.

---

## 1. Legacy frequency compatibility is validated before migration

**Area:** `sllurp/llrp.py` / `LLRPReaderConfig.validate_config()`  
**Severity:** Medium  
**Status:** Confirmed  
**Physical reader required to fix:** **No**

### Problem

Older callers may provide the historical misspelled frequency key `Channelist`. The current compatibility path is intended to normalize that legacy key into the supported `ChannelList` form, but validation happens before the migration is applied.

That creates an ordering bug:

```text
Legacy application config
        |
        v
+---------------------------+
| frequencies["Channelist"] |
+---------------------------+
        |
        v
+------------------------------+
| validate ChannelList first   |  <-- legacy key not migrated yet
+------------------------------+
        |
        +----> validation may fail
        |
        X
+------------------------------+
| migrate Channelist ->        |
| ChannelList                  |
+------------------------------+
        ^
        |
   reached too late
```

### Expected behavior

Normalization must happen before validation:

```text
Legacy application config
        |
        v
+---------------------------+
| Channelist present?       |
+---------------------------+
        |
        | yes
        v
+---------------------------+
| normalize to ChannelList  |
+---------------------------+
        |
        v
+---------------------------+
| validate normalized data  |
+---------------------------+
        |
        v
      READY
```

### User-visible impact

A configuration that was historically accepted can fail before the compatibility layer gets a chance to repair it. This is especially confusing because the code appears to support the old spelling but the execution order prevents that support from working reliably.

### Acceptance criteria

- A config containing only `Channelist` is normalized before frequency validation.
- The normalized config contains `ChannelList` with the same values.
- A config containing the modern `ChannelList` continues to work unchanged.
- If both keys are present, precedence is deterministic and documented.
- Invalid channel values still fail validation after normalization.

### Test strategy

No hardware is required. Add unit tests that construct legacy, modern and conflicting forms and assert the normalized result before any transport is created.

---

## 2. Live `update_config()` can leave desired and applied state inconsistent

**Area:** `LLRPReaderClient.update_config()` / `LLRPClient.update_config()`  
**Severity:** High  
**Status:** Confirmed design/correctness hazard  
**Physical reader required to implement:** **No**  
**Physical reader recommended for final validation:** **Yes**

### Problem

The current runtime update path can replace the client configuration object while the protocol state machine is already active. The API itself warns that this is not completely safe.

The dangerous condition is that several different representations of configuration can exist at once:

```text
                 application
                     |
                     v
             +---------------+
             | desired config |
             +---------------+
                     |
              update_config()
                     |
                     v
              self.config = X
                     |
          +----------+----------+
          |                     |
          v                     v
+------------------+   +------------------+
| cached ROSpec    |   | reader firmware  |
| built from OLD   |   | still running OLD|
| configuration    |   | configuration    |
+------------------+   +------------------+
          \                     /
           \                   /
            +------ MISMATCH --+
```

Examples of fields that may affect generated or reader-side state include antennas, TX power, RF mode, Tari, session, frequencies, report selectors, vendor extensions and dedup behavior.

### Failure modes

A live assignment can produce states such as:

```text
Python config says:      antennas = [1, 2]
Active ROSpec says:      antennas = [1]
Reader firmware runs:    antennas = [1]
Application assumes:     update succeeded
```

or:

```text
Python config says:      tx_power = new value
Cached ROSpec says:      old power index
Reconnect occurs
Rebuilt state depends on whichever object/path is consulted
```

The result can be stale configuration, partial application, surprising reconnect behavior or an application believing a change is active when the reader never accepted it.

### Target behavior

A runtime update should be a controlled state transition, not a raw assignment:

```text
                 update request
                       |
                       v
              +------------------+
              | validate proposal|
              +------------------+
                       |
                       v
              +------------------+
              | diff old vs new  |
              +------------------+
                       |
             +---------+---------+
             |                   |
      live-safe change      restart-required
             |                   |
             v                   v
       apply in place       pause inventory
                                 |
                                 v
                           rebuild ROSpec
                                 |
                                 v
                           apply to reader
                                 |
                         +-------+-------+
                         |               |
                      success          failure
                         |               |
                         v               v
                       resume       rollback / clean
                                    disconnect
```

### Acceptance criteria

- Configuration changes are validated before any runtime state is mutated.
- The implementation computes which fields changed.
- Changes that affect an active ROSpec invalidate/rebuild it deterministically.
- Reader-side changes are applied before the new config is considered active.
- Failure cannot leave `desired`, `generated` and `applied` state silently divergent.
- Inventory resumes only after the transition succeeds.
- Failure behavior is deterministic: rollback to the previous known-good state or disconnect with a clear error.
- Reconnect after a successful update reproduces the same intended configuration.

### Test strategy without hardware

Use a fake transport and deterministic state transitions for at least:

```text
DISCONNECTED
CONNECTED
INVENTORYING
PAUSING
PAUSED
```

Inject failures at every outbound step and assert the final state, active config and generated ROSpec.

### Hardware validation

After CI passes, validate on representative readers by changing settings during real inventory and verifying stop/apply/resume behavior, reader rejection handling and reconnect persistence.

---

## 3. Callback collections can be mutated while dispatch is active

**Area:** state callbacks, tag-report callbacks, message callbacks, event callbacks, disconnect callbacks  
**Severity:** Medium to High  
**Status:** High-confidence concurrency hazard  
**Physical reader required to fix:** **No**

### Problem

Callbacks are invoked from reader/runtime threads while registration and removal can occur from application threads. Mutable callback collections can therefore be changed while another thread is iterating them.

```text
Thread A - reader thread                 Thread B - application thread
-------------------------                -----------------------------
for cb in callbacks:                     callbacks.remove(cb2)
    cb(event)                <------->   callbacks.append(cb3)

          shared mutable collection without a clear dispatch contract
```

Potential consequences include skipped callbacks, callbacks running twice, ordering surprises, runtime exceptions, or callbacks being invoked after an application believes they were removed.

### Desired dispatch model

One safe model is snapshot iteration:

```text
          shared callback registry
                   |
             lock briefly
                   |
                   v
         +-------------------+
         | copy/snapshot list|
         +-------------------+
                   |
              unlock early
                   |
                   v
          invoke snapshot only
          /       |        \
        cb1      cb2       cb3
```

This keeps user callback execution outside the registry lock and gives each dispatch operation a stable view.

### Acceptance criteria

- Register/remove/clear operations are safe during active dispatch.
- A callback can add or remove callbacks from inside another callback without corrupting iteration.
- Callback order is explicitly defined.
- The lock, if used, is never held while application callback code executes.
- Callback exceptions continue to follow a defined policy and do not corrupt the registry.

### Test strategy

No hardware is needed. Use multi-threaded tests where one thread dispatches thousands of synthetic events while another repeatedly registers/removes callbacks. Include self-removal and callback-added-during-callback cases.

---

## 4. Runtime configuration changes have no transaction/rollback semantics

**Area:** dynamic ROSpec/configuration transitions  
**Severity:** High for future dynamic-management work  
**Status:** Architectural correctness gap  
**Physical reader required to implement:** **No**  
**Physical reader recommended for final validation:** **Yes**

### Problem

A meaningful live configuration change can require multiple protocol operations. If step 3 of 5 fails, there is currently no general transaction object that knows the previous known-good state and how to restore it.

Example:

```text
OLD working state
      |
      v
[1] stop inventory             OK
      |
      v
[2] delete old ROSpec          OK
      |
      v
[3] add new ROSpec             FAIL
      |
      X

What now?

- old ROSpec is gone
- new ROSpec was not accepted
- self.config may already contain new values
- application may not know what is actually active
```

### Desired behavior

```text
+-----------------------+
| capture known-good    |
| applied state         |
+-----------------------+
            |
            v
+-----------------------+
| execute transition    |
+-----------------------+
            |
      +-----+-----+
      |           |
   success      failure
      |           |
      v           v
 commit new   rollback old
 state        state if safe
                  |
             rollback fails
                  |
                  v
          clean disconnect
```

A clean disconnect is preferable to silently continuing in an unknown reader state.

### Acceptance criteria

- The transition remembers the previous known-good applied configuration.
- No new desired configuration is reported as applied until all required steps succeed.
- Failure at every intermediate step has a defined recovery path.
- Rollback failures result in a clear disconnected/failed state rather than an ambiguous inventory state.
- Deferreds/callbacks receive exactly one terminal outcome for the operation.

### Test strategy

No hardware is required to implement this. A fake reader should be able to reject each protocol step in turn. The test asserts final client state, pending deferreds, active ROSpec and whether reconnect/disconnect was requested.

---

## 5. Reader configuration parsing is currently effectively a no-op

**Area:** `LLRPClient.parseReaderConfig()`  
**Severity:** Medium  
**Status:** Confirmed implementation gap  
**Physical reader required to implement:** **No**, provided fixtures/captured frames exist

### Problem

The client keeps separate `reader_config` state, but `parseReaderConfig()` currently does not normalize useful reader-side configuration into that state.

That makes it difficult to answer the important distinction:

```text
+-------------------+        +-------------------+
| desired config    |        | actual reader     |
| requested by app  |        | accepted config   |
+-------------------+        +-------------------+
          |                            |
          +---------- ??? -------------+
```

For robust dynamic management, Sllurp should know both what the application wants and what the reader actually reported.

### Desired model

```text
Application requested config
          |
          v
+-------------------+
| desired_config    |
+-------------------+

Reader GET_CONFIG response
          |
          v
+-------------------+
| parseReaderConfig |
+-------------------+
          |
          v
+-------------------+
| applied/reported  |
| reader_config     |
+-------------------+
```

### Acceptance criteria

- Useful standard LLRP reader configuration is normalized into `reader_config` without conflating it with client desired state.
- Missing optional parameters remain explicitly absent/unknown rather than being invented.
- Captured responses from different vendors can be parsed without vendor-specific assumptions leaking into generic fields.
- The normalized state is sufficient for later dynamic-config verification where the standard provides the necessary data.

### Test strategy

Use recorded/synthetic `GET_READER_CONFIG_RESPONSE` fixtures. Physical hardware is only needed later to broaden the fixture set and validate vendor quirks.

---

# Hardware validation policy

The following separation should be maintained:

```text
                    SOFTWARE VALIDATION
                           |
         +-----------------+-----------------+
         |                                   |
         v                                   v
 unit/state-machine tests              protocol fixtures
 fake transport                        synthetic frames
 failure injection                     concurrency tests
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
        |
        v
 firmware timing, rejection codes, reconnect behavior,
 secure LLRP/TLS, vendor quirks, real inventory transitions
```

Physical RFID readers should therefore **not block implementation** of these bugs. They are required only for the final interoperability confidence layer where behavior depends on actual firmware timing, vendor-specific rejection codes, reconnect timing, RF inventory state or model-specific configuration behavior.
