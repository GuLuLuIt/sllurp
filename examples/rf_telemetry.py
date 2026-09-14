#!/usr/bin/env python3
"""Collect per-antenna RF telemetry.

Use --mode standard for portable LLRP fields or --mode zebra for supported
Zebra/Motorola phase and physical-port extensions.
"""

from __future__ import annotations

import argparse

from sllurp.llrp import LLRP_DEFAULT_PORT, LLRPReaderClient, LLRPReaderConfig


def on_tags(_reader: LLRPReaderClient, tag_reports: list[dict]) -> None:
    for tag in tag_reports:
        fields = {
            "epc": tag.get("EPC") or tag.get("EPCData"),
            "antenna": tag.get("AntennaID"),
            "channel": tag.get("ChannelIndex"),
            "rssi": tag.get("PeakRSSI"),
            "first_seen": tag.get("FirstSeenTimestampUTC"),
            "last_seen": tag.get("LastSeenTimestampUTC"),
            "seen_count": tag.get("TagSeenCount"),
            "phase_degrees": tag.get("MotoTagPhase"),
        }
        print(fields)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Sllurp RF telemetry")
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=LLRP_DEFAULT_PORT)
    parser.add_argument("--mode", choices=("standard", "zebra"), default="standard")
    parser.add_argument("--antenna", action="append", type=int, dest="antennas")
    args = parser.parse_args()

    config = LLRPReaderConfig(
        {
            "antennas": args.antennas or [0],
            "rf_telemetry_mode": args.mode,
            # Raw repeated observations are normally desirable for RF analysis.
            "dedup_seconds": None,
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
