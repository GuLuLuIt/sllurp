#!/usr/bin/env python3
"""Discover and optionally call Honeywell/Intermec IF-series DCWS operations."""

from __future__ import annotations

import argparse
import getpass

from sllurp.intermec_management import IntermecDCWSManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Intermec/Honeywell DCWS example")
    parser.add_argument("base_url")
    parser.add_argument("--model", choices=("IF1", "IF2", "IF61"), default="IF2")
    parser.add_argument("--username")
    parser.add_argument("--ca-file")
    parser.add_argument(
        "--call",
        dest="operation",
        help="invoke one advertised no-argument SOAP operation after discovery",
    )
    args = parser.parse_args()

    password = getpass.getpass("Reader password: ") if args.username else None
    manager = IntermecDCWSManager(
        args.base_url,
        model=args.model,
        username=args.username,
        password=password,
        ca_file=args.ca_file,
    )

    operations = manager.list_operations()
    print("advertised operations:")
    for operation in operations:
        print(f"  {operation}")

    if args.operation:
        print("result:", manager.call(args.operation))


if __name__ == "__main__":
    main()
