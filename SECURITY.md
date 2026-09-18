# Security Policy

## Supported code

Security fixes are targeted at the current `main` branch and the latest
maintained release, [v3.1.2](https://github.com/GuLuLuIt/sllurp/releases/tag/v3.1.2).
Older snapshots are not guaranteed to receive backports.

## Reporting a vulnerability

Please do not disclose a vulnerability, exploit, reader credential, private key, bearer token, or sensitive deployment detail in a public issue or pull request.

Preferred reporting path:

1. Use GitHub's **Security** tab and **Report a vulnerability** / private vulnerability reporting when that option is available for this repository.
2. If private vulnerability reporting is not available, open a minimal public issue that asks the maintainer to establish a private contact channel. Do **not** include exploit details in that issue.

Include enough information to reproduce and assess the problem privately: affected Sllurp commit/version, Python version, reader model and firmware if relevant, protocol and port, impact, reproduction steps, and any proposed mitigation.

## Scope

Security-sensitive areas include TLS/certificate handling, credential forwarding, HTTP redirects, XML/SOAP parsing, reader-management authentication, untrusted LLRP input, tag/access data handling, and CI/release credentials.

Reader firmware vulnerabilities should also be reported to the reader vendor. Sllurp cannot patch defects in reader firmware itself.

## Secret handling

Never commit or attach production `.env` files, passwords, API tokens, private keys, PKCS#12 bundles, or customer tag data. The repository ignores common secret-file extensions, but that is a safety net rather than a substitute for careful review.
