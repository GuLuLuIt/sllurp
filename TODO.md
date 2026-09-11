# TODO

This file tracks follow-up work from the deep runtime/state-machine review. Items here are improvements or larger refactors rather than small isolated bugs.

## Dynamic configuration

- [ ] Replace raw live `update_config()` assignment with a controlled configuration transition:
  1. validate the proposed configuration,
  2. classify which fields changed,
  3. pause/stop inventory only when required,
  4. regenerate affected ROSpec/reader configuration,
  5. apply changes in a deterministic order,
  6. resume inventory,
  7. rollback or disconnect cleanly on failure.
- [ ] Define which settings can change live versus which require reconnect.
- [ ] Invalidate/rebuild cached ROSpec state automatically when relevant config fields change.
- [ ] Preserve dedup state only when compatible with the new configuration; otherwise reset it explicitly.

Physical reader required to implement: **No**. Hardware integration testing is strongly recommended after CI passes.

## Request/deferred handling

- [ ] Evaluate correlating pending requests by LLRP message ID, not only response message type.
- [ ] Allow safe concurrent requests where the protocol and reader support them.
- [ ] Add timeout/cancellation semantics for pending requests.
- [ ] Add deterministic tests for duplicate, late, reordered and unmatched responses.

Physical reader required: **No**.

## Callback/thread safety

- [ ] Make callback registration/removal safe while dispatch is active, for example via locking or snapshot iteration.
- [ ] Define callback ordering guarantees.
- [ ] Test callback removal/addition from inside another callback and from another thread.

Physical reader required: **No**.

## Pause/resume

- [ ] Implement `pause(duration_seconds > 0)` instead of raising `ReaderConfigurationError`.
- [ ] Use a cancellable timer and make disconnect/reconnect cancel or restore it safely.
- [ ] Verify resume regenerates the ROSpec only when needed.

Physical reader required to implement: **No**. Hardware recommended to validate reader timing/firmware behavior.

## Reader configuration state

- [ ] Expand `parseReaderConfig()` from its current no-op into normalized reader-side state where useful.
- [ ] Keep reported reader configuration separate from desired client configuration.
- [ ] Expose enough normalized state for applications to know what was actually accepted by the reader.

Physical reader required to implement parsers/tests: **No** when fixtures/captured frames exist. Hardware recommended to collect/confirm model-specific responses.

## Core architecture

- [ ] Reduce coupling between transport lifecycle (`LLRPReaderClient`) and protocol/state-machine lifecycle (`LLRPClient`).
- [ ] Make connection state, desired config, applied config and active ROSpec state explicit rather than implicit across several attributes.
- [ ] Keep broad `llrp.py` refactors incremental and covered by state-transition tests; avoid an all-at-once rewrite.

Physical reader required: **No**.

## Hardware integration matrix

After the software/state-machine work is green in CI, run real-reader validation for representative hardware where available:

- [ ] Zebra fixed reader
- [ ] Impinj fixed reader
- [ ] Honeywell/Intermec reader
- [ ] plain LLRP reconnect/drop test
- [ ] secure LLRP/TLS test where supported
- [ ] live inventory config change
- [ ] reader rejection/invalid-setting behavior
- [ ] pause/resume timing

This section **does require physical readers** for final validation, but it should not block implementing or unit-testing the core fixes.
