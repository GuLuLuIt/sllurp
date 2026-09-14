#!/usr/bin/env python3
"""Read status from a supported Zebra management API.

Examples:
    python examples/zebra_management.py FXR90 https://reader.example --api iot
    python examples/zebra_management.py FX9600 https://reader.example --api rm
"""

from __future__ import annotations

import argparse
import getpass

from sllurp.zebra_management import ZebraRMManager, zebra_reader_manager


def main() -> None:
    parser = argparse.ArgumentParser(description="Zebra reader management example")
    parser.add_argument("model")
    parser.add_argument("base_url")
    parser.add_argument("--api", choices=("auto", "rm", "iot"), default="auto")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--ca-file")
    args = parser.parse_args()

    password = getpass.getpass("Reader password: ")
    manager = zebra_reader_manager(
        args.model,
        args.base_url,
        api=args.api,
        username=args.username,
        password=password,
        ca_file=args.ca_file,
    )

    if isinstance(manager, ZebraRMManager):
        manager.login()
        try:
            print("info:", manager.get_info())
            print("status:", manager.get_status())
            print("LLRP config:", manager.get_llrp_config())
        finally:
            manager.logout()
    else:
        print("info:", manager.get_info())
        print("status:", manager.get_status())
        print("capabilities:", manager.get_capabilities())


if __name__ == "__main__":
    main()
