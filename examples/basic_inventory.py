#!/usr/bin/env python3
"""Minimal Python inventory example.

Usage:
    python examples/basic_inventory.py 192.168.1.50
"""

from __future__ import annotations

import argparse

from sllurp.llrp import LLRP_DEFAULT_PORT, LLRPReaderClient, LLRPReaderConfig


def on_tags(_reader: LLRPReaderClient, tag_reports: list[dict]) -> None:
    for tag in tag_reports:
        epc = tag.get("EPC") or tag.get("EPCData")
        antenna = tag.get("AntennaID")
        rssi = tag.get("PeakRSSI")
        print(f"EPC={epc!r} antenna={antenna!r} rssi={rssi!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory RFID tags with Sllurp")
    parser.add_argument("host", help="reader IP address or DNS name")
    parser.add_argument("--port", type=int, default=LLRP_DEFAULT_PORT)
    parser.add_argument(
        "--antenna",
        action="append",
        type=int,
        dest="antennas",
        help="antenna ID; repeat for multiple antennas (default: all)",
    )
    args = parser.parse_args()

    config = LLRPReaderConfig({"antennas": args.antennas or [0]})
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
