# Sllurp v3.1.2

This documentation-focused maintenance release makes the production feature
set easier to operate, extend, test, and release. It retains the
import-compatible `sllurp` module name and the established runtime behavior
while adding complete user and developer paths.

## Highlights

- A new user guide explains the protocol boundary, secure deployment, CLI and
  Python workflows, callback threading, reporting versus LLRP Antenna
  Inventory Specification (AISpec) termination, deduplication, live
  configuration, multi-reader design, and recovery.
- A new developer guide maps the repository, state machine, exact request
  correlation, configuration transitions, public API boundary, extension
  workflows, tests, documentation contract, and release process.
- Mermaid diagrams document the session lifecycle, worker boundary, internal
  architecture, and configuration transition flow directly in source.
- The README, Quick Start, examples, documentation index, contribution guide,
  source distribution manifest, and release checks link and ship the new
  guides.
- All existing production capabilities remain available, including Secure
  LLRP, timed deduplication, vendor management, runtime reconfiguration, RF
  telemetry, and multi-reader support.

## Download and verify

Download `sllurp-3.1.2-py3-none-any.whl`, `sllurp-3.1.2.tar.gz`, and `SHA256SUMS.txt` from this release. Verify the selected file before installation:

```bash
sha256sum -c SHA256SUMS.txt
python -m pip install ./sllurp-3.1.2-py3-none-any.whl
sllurp --version
```

GitHub also publishes build-provenance attestations for both Python distributions. With GitHub CLI installed, verify an artifact against this repository:

```bash
gh attestation verify sllurp-3.1.2-py3-none-any.whl --repo GuLuLuIt/sllurp
```

## Important package-name note

The `sllurp` distribution published on PyPI is not this GuLuLuIT build. This project is distributed through GuLuLuIT GitHub Releases and immutable Git tags. Install its wheel or tagged GitHub source explicitly.

## License and lineage

This repository is distributed under GPL-3.0-only and preserves inherited source-file copyright notices. See `LICENSE.txt` and `NOTICE.md` in the source distribution for the complete license and attribution information.
