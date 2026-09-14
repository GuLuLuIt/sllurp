# Sllurp CLI recipes

Replace `READER_HOST`, certificate paths, antenna IDs, and tag-memory parameters with values for your setup. Run the relevant `--help` command before changing reader or tag state.

## Inventory

```bash
sllurp inventory READER_HOST
sllurp inventory -a 0 -t 10 READER_HOST
sllurp inventory -a 1 -a 2 READER_HOST
```

Inventory multiple readers in one command:

```bash
sllurp inventory -a 0 reader-a.example reader-b.example
```

## Timed deduplication

```bash
sllurp inventory --dedup-seconds 2 --dedup-backend auto -a 0 READER_HOST
sllurp inventory --dedup-seconds 2 --dedup-backend memory -a 0 READER_HOST
```

Use `hardware` only when the reader advertises the required behavior. RF telemetry should normally use raw observations or the `memory` backend.

## Secure LLRP / TLS

Reader certificate trusted by the system CA store:

```bash
sllurp inventory --tls reader.example.com
```

Private CA:

```bash
sllurp inventory --tls --tls-ca-file reader-ca.pem reader.example.com
```

Connect by IP but validate the DNS name in the certificate:

```bash
sllurp inventory \
  --tls \
  --tls-ca-file reader-ca.pem \
  --tls-server-hostname reader.example.com \
  192.168.1.50
```

Mutual TLS:

```bash
sllurp inventory \
  --tls \
  --tls-ca-file reader-ca.pem \
  --tls-client-cert client.pem \
  --tls-client-key client.key \
  reader.example.com
```

`--tls-no-verify` is for controlled testing, not normal deployment.

## Impinj inventory extensions

```bash
sllurp inventory --impinj-search-mode 2 READER_HOST
sllurp inventory --impinj-reports -a 0 READER_HOST
sllurp inventory --impinj-fixed-frequency -f 1,2 -a 0 READER_HOST
```

## Tag memory access

Read two 16-bit words:

```bash
sllurp access --read-words 2 --count 1 READER_HOST
```

Select memory bank and word pointer:

```bash
sllurp access --read-words 2 --memory-bank 2 --word-ptr 0 --count 1 READER_HOST
```

Before any write operation, run:

```bash
sllurp access --help
```

Test writes on disposable/test tags first.

## CSV logging

```bash
sllurp log -a 0 -o tags.csv READER_HOST
sllurp log -a 0 --reader-timestamp -o tags.csv READER_HOST
```

## Recovery and diagnostics

Reset LLRP state after an interrupted session:

```bash
sllurp reset READER_HOST
```

Enable verbose protocol diagnostics:

```bash
sllurp --debug inventory READER_HOST
sllurp --debug --logfile sllurp.log inventory READER_HOST
```

## Installed-version help

```bash
sllurp --help
sllurp inventory --help
sllurp access --help
sllurp log --help
sllurp reset --help
```
