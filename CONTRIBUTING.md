# Contributing to Sllurp

Thanks for improving Sllurp. This fork accepts bug fixes, interoperability improvements, tests, documentation, and reader-management work that can be supported by code, protocol documentation, or reproducible hardware evidence.

## Development setup

```bash
git clone https://github.com/GuLuLuIt/sllurp.git
cd sllurp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1`.

## Before opening a pull request

Run the same high-signal checks used by CI:

```bash
pytest -W error
pytest --cov=sllurp --cov-branch --cov-fail-under=65
python -m compileall -q sllurp tests examples
ruff check sllurp tests examples --select E9,F63,F7,F82,F401,F841,E722,B006,ISC004,B017
bandit -r sllurp -q
codespell
python -m build
python -m twine check dist/*
```

Keep changes focused. Include regression tests for bug fixes and behavior changes. Update the Quick Start, feature docs, compatibility notes, or examples when public behavior changes.

## Reader and protocol changes

Sllurp separates standard LLRP reader control from vendor web-management APIs. Do not guess private CGI endpoints or undocumented payloads. New vendor-management behavior should be based on stable vendor documentation or captured behavior that can be safely reproduced.

When a change depends on hardware, include the reader model, firmware version, antenna topology when relevant, protocol/port used, and the observed request/response behavior. If hardware was not available, say so clearly and keep model-specific claims conservative.

For RF telemetry and deduplication changes, preserve antenna identity when cross-port observations matter. For TLS changes, keep certificate verification enabled by default.

## Pull requests

A useful pull request should explain:

- what problem it solves;
- what behavior changed;
- tests or validation performed;
- reader model/firmware when hardware-specific;
- documentation or examples updated;
- any compatibility or rollback concerns.

Do not include reader passwords, bearer tokens, private keys, certificates containing private material, production IP addresses, or customer data in commits, logs, screenshots, issues, or test fixtures.

## Security issues

Do not publish exploit details or secrets in a normal issue. Follow `SECURITY.md` for vulnerability reporting.

## License

By contributing, you agree that your contribution is distributed under the repository's `GPL-3.0-only` license. Copyright remains with the respective contributors.
