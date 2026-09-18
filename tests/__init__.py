"""Project-owned test package.

Keeping this directory an explicit package prevents imports such as
``tests.test_audit_19_regressions`` from resolving to an unrelated third-party
``tests`` namespace on macOS or another platform.
"""

