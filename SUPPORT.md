# Support

For installation and first use, start with `QUICKSTART.md`. For runnable feature examples, see `examples/README.md`. The documentation map is in `docs/index.rst`.

## Usage questions

Before asking for help, collect:

- Sllurp commit or version;
- Python version and operating system;
- reader model and firmware;
- plain LLRP or TLS and the configured port;
- antenna setup when RF behavior is involved;
- the exact command or minimal Python configuration;
- DEBUG logs with passwords, tokens, private keys, production addresses, and customer/tag data removed.

Run CLI help for the installed version because options can change:

```bash
sllurp --help
sllurp inventory --help
sllurp access --help
sllurp log --help
sllurp reset --help
```

## Bugs and feature requests

When the repository's GitHub Issues feature is enabled, use the provided bug or feature-request templates. If the Issues tab is unavailable, a focused pull request with a regression test is still welcome for a confirmed defect.

For security vulnerabilities, do not use a normal public issue. Follow `SECURITY.md`.

## Hardware-specific reports

Reader interoperability depends on model and firmware. Include those details and avoid generalizing one reader's web API, antenna count, TLS behavior, or vendor extension to an entire product family without documentation or evidence.
