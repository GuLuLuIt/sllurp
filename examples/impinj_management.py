#!/usr/bin/env python3
"""Read common management resources from an Impinj R700/R720."""

from __future__ import annotations

import argparse
import getpass

from sllurp.impinj_management import ImpinjRESTManager


def main() -> None:
    parser = argparse.ArgumentParser(description="Impinj R700/R720 REST management")
    parser.add_argument("base_url", help="for example https://r700.example")
    parser.add_argument("--model", choices=("R700", "R720"), default="R700")
    parser.add_argument("--username", default="root")
    parser.add_argument("--ca-file")
    args = parser.parse_args()

    password = getpass.getpass("Reader password: ")
    manager = ImpinjRESTManager(
        args.base_url,
        model=args.model,
        username=args.username,
        password=password,
        ca_file=args.ca_file,
    )

    print("status:", manager.get_status())
    print("power:", manager.get_power())
    print("mqtt:", manager.get_mqtt())


if __name__ == "__main__":
    main()
