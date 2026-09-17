# Changelog

All notable changes to this fork should be documented here. This project uses semantic versioning for tagged releases when releases are published.

## Unreleased — 3.1.0

### Added

- Secure LLRP/TLS configuration and CLI support, including custom CA, mTLS, and server-hostname controls.
- Timed tag deduplication with automatic, hardware, and memory backends.
- Generic HTTP/HTTPS reader-management transport with same-origin credential protection.
- Zebra Reader Management XML and IoT Connector adapters.
- Impinj R700/R720 REST management.
- Honeywell/Intermec IF-series WSDL/DCWS management.
- Transactional runtime configuration and runtime state inspection.
- RF telemetry with per-antenna observations and supported Zebra phase extensions.
- Expanded reader compatibility registry and practical feature examples.
- Cross-platform Quick Start and reorganized feature documentation.
- `sllurp --version` for identifying the installed command build.
- Windows and macOS CI coverage in addition to the Linux/Python-version matrix.
- Regression checks for broken internal links across repository documentation.
- Release-build guards that require `vX.Y.Z` tags and built artifacts to match the package version.
- Repository-hygiene regression coverage for obsolete binary/reference artifacts and example dependency drift.
- FastAPI example smoke testing against the repository package on Python 3.10 and 3.14.
- Explicit `ro_report_every_n_tags` Python and CLI configuration for
  continuous N-tag `ROReportSpec` delivery without ending the AISpec.

### Changed

- The source-tree version is now `3.1.0`, distinguishing this feature-bearing fork from the upstream `3.0.5` baseline.
- Installation documentation now clearly distinguishes this repository from the upstream PyPI `sllurp` distribution.
- CI validates Python 3.10 through 3.14 on Linux, full tests on Windows and macOS, package installation, dependency consistency, coverage, static checks, security checks, documentation links, example compilation, and the maintained FastAPI example.
- Repository/project metadata now points to this fork where fork-specific functionality is documented.
- Removed unreferenced capability dumps, bundled LLRP standard PDFs, a legacy Impinj R1000 XML dump, obsolete `bin/` wrappers, and the superseded Tornado demo.
- Simplified the FastAPI example to repository-first installation, environment-based configuration, same-origin browser access, and POST actions for state changes.
- Renamed process-oriented regression-test files to feature-oriented names without changing their test coverage.
- Updated `NOTICE.md` to reflect the current GPLv3 file-level license wording.

### Fixed

- Core LLRP correctness and state-machine defects, malformed C1G2 metadata, mutable defaults, timeout/correlation edge cases, XML hardening, HTTP cleanup, and additional failure-path handling covered by regression tests.
- Timed-pause tests now wait on the actual asynchronous state transition instead of relying on fixed scheduler timing.
- Aligned the stale `sllurp/llrp_proto.py` GPLv2 header wording with the project's GPLv3 license while preserving existing copyright notices.
- Corrected Impinj frequency capability decoding to advance 32-bit frequency entries by the correct stride.
- Corrected audited LLRP wire encoders/decoders, rollback after rejected configuration operations, mode reset, disconnect cleanup, FastAPI shutdown, diagnostic logging, CLI exit status, detached state snapshots, documentation recipes, and minimum build-backend compatibility. Logging setup preserves application-owned handlers.
- Preserved the existing unlimited ROReportSpec count (N=0), including explicit AISpec batching and duration triggers. The proposed N=1 default was withdrawn because it changes reporting behavior; see LLRP 1.1 section 14.2.1: https://ref.gs1.org/standards/llrp/1.1.0/.
- Corrected report-control documentation and logging to identify the legacy
  `report_every_n_tags` / `report_timeout_ms` behavior as AISpec
  termination rather than continuous report cadence.

## Release history

This fork has not published a GitHub release yet. The source tree now targets version `3.1.0`; follow `RELEASING.md` before tagging or publishing the first fork release.
