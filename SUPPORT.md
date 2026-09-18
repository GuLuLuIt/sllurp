# Support

Sllurp 3.1.2 is the current supported release. For installation and first use,
start with [`QUICKSTART.md`](QUICKSTART.md). For runnable feature examples, see
[`examples/README.md`](examples/README.md). For Python interface details, use
the [`3.1.2 API reference`](API_REFERENCE.md). The documentation map is in
[`docs/index.rst`](docs/index.rst).

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

Use the [structured issue forms](https://github.com/GuLuLuIt/sllurp/issues/new/choose)
for bugs, hardware compatibility reports, and feature requests. A focused pull
request with a regression test is also welcome for a confirmed defect.

For security vulnerabilities, do not use a normal public issue. Follow
[`SECURITY.md`](SECURITY.md).

## Hardware-specific reports

Reader interoperability depends on model and firmware. Include those details and avoid generalizing one reader's web API, antenna count, TLS behavior, or vendor extension to an entire product family without documentation or evidence.

