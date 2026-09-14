# Changelog

All notable changes to this fork should be documented here. This project uses semantic versioning for tagged releases when releases are published.

## Unreleased

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

### Changed

- CI now validates Python 3.10 through 3.14, package installation, coverage, static checks, security checks, and example compilation.
- Repository/project metadata now points to this fork where fork-specific functionality is documented.

### Fixed

- Core LLRP correctness and state-machine defects, malformed C1G2 metadata, mutable defaults, timeout/correlation edge cases, XML hardening, HTTP cleanup, and additional failure-path handling covered by regression tests.

## Release history

This fork has not published a GitHub release yet. The Python package currently reports version `3.0.5`, inherited from the upstream baseline. Before the first fork release, update the version intentionally and follow `RELEASING.md`.
