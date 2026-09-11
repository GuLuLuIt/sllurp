# Known Bugs

This file tracks confirmed or high-confidence correctness issues that should be fixed separately from the broad hardening work in PR #16.

## Core `sllurp/llrp.py`

### Legacy frequency compatibility is validated before migration

`LLRPReaderConfig.validate_config()` validates `frequencies["ChannelList"]` before the legacy `Channelist` -> `ChannelList` compatibility migration is applied. A legacy-only configuration can therefore fail validation before it is normalized.

- Status: confirmed
- Physical reader required to fix: **No**
- Validation: unit test constructing a legacy config and asserting it normalizes before validation

### Live `update_config()` can leave runtime state inconsistent

`LLRPReaderClient.update_config()` and `LLRPClient.update_config()` replace configuration while the protocol/state-machine thread may already be active. The current API is explicitly documented as not completely safe. A live update can leave cached/generated state such as the active ROSpec or reader-side configuration out of sync with the newly assigned client configuration.

- Status: confirmed design/correctness hazard
- Physical reader required to implement the fix: **No**
- Physical reader recommended for final validation: **Yes**
- Validation without hardware: fake transport + state-machine tests for CONNECTED, INVENTORYING and PAUSED states
- Hardware validation: change configuration during real inventory and verify stop/apply/resume behavior and reader rejection handling

### Callback collections can be mutated while being iterated

State, message, tag-report, event and disconnect callbacks are stored in mutable lists/dicts and are invoked from the reader thread. Another thread can add/remove/clear callbacks while those collections are being iterated.

- Status: high-confidence concurrency bug/hazard
- Physical reader required to fix: **No**
- Validation: multi-threaded unit tests that mutate callback registrations while synthetic events/reports are dispatched

### Runtime configuration changes do not have rollback semantics

If a future/live configuration operation requires multiple reader-side changes, there is no transaction/rollback layer that restores the previous known-good configuration when one step fails. This is especially important for ROSpec rebuilds, reader configuration writes and reconnect paths.

- Status: architectural correctness gap exposed by dynamic updates
- Physical reader required to implement: **No**
- Physical reader recommended for final validation: **Yes**
- Validation without hardware: inject failures at each state-machine step and assert deterministic rollback/disconnect behavior

## Hardware policy

Physical RFID readers should not be required for ordinary bug fixing or CI. Core behavior must be testable with synthetic LLRP frames, fake transports and deterministic state-machine tests.

Hardware is used as a final interoperability layer for behavior that depends on firmware timing, reader rejection codes, vendor quirks, reconnect timing, RF inventory state or model-specific configuration behavior.
