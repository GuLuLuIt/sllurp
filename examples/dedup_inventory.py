#!/usr/bin/env python3
"""Inventory with timed tag deduplication.

Usage:
    python examples/dedup_inventory.py 192.168.1.50 --seconds 2 --backend auto
"""

from __future__ import annotations

import argparse

from sllurp.llrp import LLRP_DEFAULT_PORT, LLRPReaderClient, LLRPReaderConfig


def on_tags(_reader: LLRPReaderClient, tag_reports: list[dict]) -> None:
    for tag in tag_reports:
        print(tag)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory with timed deduplication")
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=LLRP_DEFAULT_PORT)
    parser.add_argument("--seconds", type=int, default=2)
    parser.add_argument(
        "--backend", choices=("auto", "hardware", "memory"), default="auto"
    )
    args = parser.parse_args()

    config = LLRPReaderConfig(
        {
            "antennas": [0],
            "dedup_seconds": args.seconds,
            "dedup_backend": args.backend,
        }
    )
    reader = LLRPReaderClient(args.host, args.port, config)
    reader.add_tag_report_callback(on_tags)
    reader.connect()

    try:
        reader.join(None)
    except KeyboardInterrupt:
        pass
    finally:
        reader.disconnect()


if __name__ == "__main__":
    main()
