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

### Changed

- The source-tree version is now `3.1.0`, distinguishing this feature-bearing fork from the upstream `3.0.5` baseline.
- Installation documentation now clearly distinguishes this repository from the upstream PyPI `sllurp` distribution.
- CI validates Python 3.10 through 3.14 on Linux, full tests on Windows and macOS, package installation, coverage, static checks, security checks, and example compilation.
- Repository/project metadata now points to this fork where fork-specific functionality is documented.

### Fixed

- Core LLRP correctness and state-machine defects, malformed C1G2 metadata, mutable defaults, timeout/correlation edge cases, XML hardening, HTTP cleanup, and additional failure-path handling covered by regression tests.

## Release history

This fork has not published a GitHub release yet. The source tree now targets version `3.1.0`; follow `RELEASING.md` before tagging or publishing the first fork release.
