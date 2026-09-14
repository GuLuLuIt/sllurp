#!/usr/bin/env python3
"""Use a vendor-documented HTTP/HTTPS management endpoint safely."""

from __future__ import annotations

import argparse
import getpass

from sllurp.reader_management import HTTPReaderManager, ReaderManagementError


def main() -> None:
    parser = argparse.ArgumentParser(description="Generic RFID reader management")
    parser.add_argument("base_url", help="for example https://reader.example")
    parser.add_argument("path", help="documented settings path, for example /api/settings")
    parser.add_argument("--username")
    parser.add_argument("--ca-file")
    args = parser.parse_args()

    password = getpass.getpass("Reader password: ") if args.username else None
    manager = HTTPReaderManager(
        args.base_url,
        username=args.username,
        password=password,
        ca_file=args.ca_file,
    )

    try:
        print(manager.get_settings(args.path))
    except ReaderManagementError as exc:
        print(f"management request failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
