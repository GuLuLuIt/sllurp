import argparse
import logging
import pprint
from threading import RLock

from sllurp.llrp import (
    LLRP_DEFAULT_PORT,
    C1G2Lock,
    C1G2LockPayload,
    LLRPReaderClient,
    LLRPReaderConfig,
    LLRPReaderState,
)
from sllurp.log import get_logger
from sllurp.log import init_logging as configure_logging
from sllurp.util import monotonic, split_host_port

startTime = None
endTime = None

tagReport = 0
logger = get_logger(__name__)

args = None

_stats_lock = RLock()
_reader_start_times = {}
_reader_tag_counts = {}


def _reader_key(reader):
    return id(reader)


def _reset_runtime_state():
    global startTime, endTime, tagReport
    with _stats_lock:
        startTime = None
        endTime = None
        tagReport = 0
        _reader_start_times.clear()
        _reader_tag_counts.clear()


def startTimeMeasurement():
    global startTime
    with _stats_lock:
        startTime = monotonic()
    return startTime


def stopTimeMeasurement():
    global endTime
    with _stats_lock:
        endTime = monotonic()
    return endTime


def finish_cb(reader):
    stopTimeMeasurement()
    with _stats_lock:
        reader_key = _reader_key(reader)
        reader_start = _reader_start_times.pop(reader_key, None)
        reader_count = _reader_tag_counts.pop(reader_key, 0)
        total_count = tagReport
        global_start = startTime
        stopped = endTime

    started = reader_start if reader_start is not None else global_start
    runtime = max(stopped - started, 0.0) if started is not None else 0.0
    rate = reader_count / runtime if runtime > 0 else 0.0
    logger.info(
        "reader %r: %d tags seen (%.1f tags/second); total=%d",
        reader.get_peername() if reader is not None else None,
        reader_count,
        rate,
        total_count,
    )


def access_cb(reader, state):
    with _stats_lock:
        _reader_start_times.setdefault(_reader_key(reader), monotonic())
    lock_payload = C1G2LockPayload(args.privilege, args.data_field)
    opspec = C1G2Lock(AccessPassword=args.access_password, LockPayload=lock_payload)
    return reader.start_access_spec(opspec, stop_after_count=args.count)


def tag_report_cb(reader, tags):
    """Function to run each time the reader reports seeing tags."""
    global tagReport
    if tags:
        if logger.isEnabledFor(logging.INFO):
            logger.info("saw tag(s): %s", pprint.pformat(tags))
    else:
        logger.info("no tags seen")
        return

    count = sum(int(tag.get("TagSeenCount", 1)) for tag in tags)
    with _stats_lock:
        tagReport += count
        reader_key = _reader_key(reader)
        _reader_tag_counts[reader_key] = _reader_tag_counts.get(reader_key, 0) + count

    for tag in tags:
        if "C1G2LockOpSpecResult" in tag:
            result = tag["C1G2LockOpSpecResult"].get("Result")
            logger.debug("result: %s", result)


def parse_args():
    global args
    parser = argparse.ArgumentParser(description="Simple RFID Lock")
    parser.add_argument("host", help="hostname or IP address of RFID reader", nargs="*")
    parser.add_argument(
        "-p",
        "--port",
        default=LLRP_DEFAULT_PORT,
        type=int,
        help=f"port (default {LLRP_DEFAULT_PORT})",
    )
    parser.add_argument(
        "-t",
        "--time",
        default=10,
        type=float,
        help="number of seconds to inventory (default 10)",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="show debugging output"
    )
    parser.add_argument(
        "-n",
        "--report-every-n-tags",
        default=1,
        type=int,
        dest="every_n",
        metavar="N",
        help=(
            "legacy: end the AISpec after N tag observations; accumulated "
            "observations report at the inventory boundary"
        ),
    )
    parser.add_argument(
        "-a",
        "--antennas",
        type=str,
        default="0",
        help="comma-separated list of antennas to use (default 0=all)",
    )
    parser.add_argument(
        "-X",
        "--tx-power",
        default=0,
        type=int,
        dest="tx_power",
        help="Transmit power (default 0=max power)",
    )
    parser.add_argument(
        "-T", "--tari", default=0, type=int, help="Tari value (default 0=auto)"
    )
    parser.add_argument(
        "-s", "--session", default=2, type=int, help="Gen2 session (default 2)"
    )
    parser.add_argument("--mode-identifier", type=int, help="ModeIdentifier value")
    parser.add_argument(
        "-P",
        "--tag-population",
        default=4,
        type=int,
        dest="population",
        help="Tag Population value (default 4)",
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=0,
        help="Operation count for R/W (default 0=forever)",
    )

    parser.add_argument(
        "-priv",
        "--privilege",
        default=0,
        type=int,
        help="Access privilege: 0 RW, 1 Permalock, 2 Permaunlock, 3 Unlock",
    )
    parser.add_argument(
        "-df",
        "--data-field",
        default=0,
        type=int,
        dest="data_field",
        help="Access Data Field: 0 KILL passwd, 1 ACCESS passwd, 2 EPC, 3 TID, 4 User memory",
    )
    parser.add_argument(
        "-ap",
        "--access_password",
        default=0,
        type=int,
        dest="access_password",
        help="Access password for secure state if R/W locked",
    )
    parser.add_argument("-l", "--logfile")

    args = parser.parse_args()


def init_logging():
    configure_logging(debug=args.debug, logfile=args.logfile)
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger.log(log_level, "log level: %s", logging.getLevelName(log_level))


def main():
    parse_args()
    init_logging()

    if not args.host:
        logger.info("No readers specified.")
        return 0

    _reset_runtime_state()
    enabled_antennas = [int(x.strip()) for x in args.antennas.split(",")]

    factory_args = dict(
        duration=args.time,
        report_every_n_tags=args.every_n,
        antennas=enabled_antennas,
        tx_power=args.tx_power,
        tari=args.tari,
        session=args.session,
        mode_identifier=args.mode_identifier,
        tag_population=args.population,
        start_inventory=True,
        disconnect_when_done=bool(args.time and args.time > 0),
        tag_content_selector={
            "EnableROSpecID": False,
            "EnableSpecIndex": False,
            "EnableInventoryParameterSpecID": False,
            "EnableAntennaID": True,
            "EnableChannelIndex": False,
            "EnablePeakRSSI": True,
            "EnableFirstSeenTimestamp": False,
            "EnableLastSeenTimestamp": True,
            "EnableTagSeenCount": True,
            "EnableAccessSpecID": True,
        },
    )

    reader_clients = []
    for host_value in args.host:
        host, port = split_host_port(host_value, args.port)

        config = LLRPReaderConfig(factory_args)
        reader = LLRPReaderClient(host, port, config)
        reader.add_disconnected_callback(finish_cb)
        reader.add_tag_report_callback(tag_report_cb)
        reader.add_state_callback(LLRPReaderState.STATE_INVENTORYING, access_cb)

        reader_clients.append(reader)

    startTimeMeasurement()

    try:
        for reader in reader_clients:
            reader.connect()
    except Exception:
        for reader in reader_clients:
            reader.disconnect()

    while True:
        try:
            alive_readers = [reader for reader in reader_clients if reader.is_alive()]
            if not alive_readers:
                break
            for reader in alive_readers:
                reader.join(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Exit detected! Stopping readers...")
            for reader in reader_clients:
                try:
                    reader.disconnect()
                except Exception:
                    logger.exception("Error during disconnect. Ignoring...")
            break


if __name__ == "__main__":
    main()
