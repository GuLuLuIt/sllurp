#!/usr/bin/env python3
"""Apply a controlled live configuration change and inspect runtime state."""

from __future__ import annotations

import argparse
import time

from sllurp.llrp import LLRP_DEFAULT_PORT, LLRPReaderClient, LLRPReaderConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Demonstrate apply_config()")
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=LLRP_DEFAULT_PORT)
    parser.add_argument("--before", type=float, default=3.0, help="seconds before change")
    args = parser.parse_args()

    initial = LLRPReaderConfig({"antennas": [1], "tx_power": 0})
    reader = LLRPReaderClient(args.host, args.port, initial)
    reader.connect()

    try:
        time.sleep(args.before)
        updated = LLRPReaderConfig({"antennas": [1, 2], "tx_power": 0})
        transition = reader.apply_config(updated)
        print("transition:", transition)
        print("state:", reader.llrp.get_config_state())
        reader.join(None)
    except KeyboardInterrupt:
        pass
    finally:
        reader.disconnect()


if __name__ == "__main__":
    main()
