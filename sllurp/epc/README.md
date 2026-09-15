# Parsing EPC Data

EPC Tag Data Standard: <https://ref.gs1.org/standards/tds/>

## SGTIN-96 to GTIN

Tag-report callbacks receive ``(reader, tags)``. EPC values may arrive as bytes,
so decode them to the 24-character hexadecimal string expected by
``parse_sgtin_96`` before parsing.

```python
from sllurp.epc.gtin import combine_gtin_with_check_digit
from sllurp.epc.sgtin_96 import parse_sgtin_96


def tag_seen_callback(_reader, tags):
    for tag_report in tags:
        epc = tag_report.get("EPC-96") or tag_report.get("EPC")
        if epc is None:
            continue
        if isinstance(epc, bytes):
            epc = epc.decode("ascii")

        parsed = parse_sgtin_96(epc)
        gtin_body = parsed["company_prefix"] + parsed["item_reference"]
        full_gtin = combine_gtin_with_check_digit(gtin_body)
        print(full_gtin)
```
