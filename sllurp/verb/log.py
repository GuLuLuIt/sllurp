"""Simple tag logger.

Logs tag sightings at one or more readers to a CSV file.
"""

import csv
import time
from threading import RLock

from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig
from sllurp.log import get_logger
from sllurp.util import format_host_port, split_host_port

numTags = 0
logger = get_logger(__name__)
csvlogger = None


def _epc_text(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode("ascii", errors="replace")
    return str(value)


def _reader_utc_timestamp(tag):
    """Return an absolute reader timestamp in seconds, if one is available."""
    for key in ("LastSeenTimestampUTC", "FirstSeenTimestampUTC"):
        value = tag.get(key)
        if value is not None:
            return float(value) / 1_000_000.0
    return None


class CsvLogger:
    def __init__(self, filehandle, epc=None, reader_timestamp=False):
        self.filehandle = filehandle
        self.writer = csv.writer(self.filehandle, dialect="excel")
        self.writer.writerow(("timestamp", "reader", "antenna", "rssi", "epc"))
        self.num_tags = 0
        self.epc = epc
        self.reader_timestamp = reader_timestamp
        self._lock = RLock()
        self._warned_missing_reader_utc = False

    def tag_cb(self, reader, tags):
        host, port = reader.get_peername()
        reader_name = format_host_port(host, port)
        logger.info("RO_ACCESS_REPORT from %s", reader_name)

        # All tags in one callback arrived in the same host-side batch. Reuse
        # one receipt timestamp instead of calling the clock for every tag.
        received_at = time.time()
        rows = []
        seen_count = 0
        missing_reader_utc = False

        for tag in tags:
            raw_epc = tag.get("EPC", tag.get("EPC-96"))
            if raw_epc is None:
                logger.warning("tag report is missing EPC data; skipping row")
                continue
            epc = _epc_text(raw_epc)
            if self.epc is not None and epc.casefold() != self.epc.casefold():
                continue

            if self.reader_timestamp:
                timestamp = _reader_utc_timestamp(tag)
                if timestamp is None:
                    # Uptime timestamps are not Unix timestamps and cannot be
                    # mixed into this CSV column safely. Fall back to host UTC
                    # receipt time and warn once.
                    timestamp = received_at
                    missing_reader_utc = True
            else:
                timestamp = received_at

            rows.append(
                (
                    timestamp,
                    reader_name,
                    tag.get("AntennaID"),
                    tag.get("PeakRSSI"),
                    epc,
                )
            )
            seen_count += int(tag.get("TagSeenCount", 1))

        if not rows and not missing_reader_utc:
            return

        should_warn = False
        with self._lock:
            if rows:
                self.writer.writerows(rows)
                self.num_tags += seen_count
                self.filehandle.flush()
            if missing_reader_utc and not self._warned_missing_reader_utc:
                self._warned_missing_reader_utc = True
                should_warn = True

        if should_warn:
            logger.warning(
                "reader timestamp requested but report has no UTC timestamp; "
                "using host receipt time"
            )

    def flush(self):
        with self._lock:
            self.filehandle.flush()


def finish_cb(reader):
    # Following would be possible, but then concurrent file write would have
    # to be handled. CsvLogger serializes its writes, so this is now safe.
    logger.info("Total tags seen: %d", csvlogger.num_tags)


def main(args):
    global csvlogger

    # Arguments:
    # host, port, outfile, antennas, tx_power, epc, reader_timestamp
    if not args.host:
        logger.info("No readers specified.")
        return 0

    if not args.outfile:
        logger.info("No output file specified.")
        return 0

    enabled_antennas = [int(x.strip()) for x in args.antennas.split(",")]
    frequency_list = [int(x.strip()) for x in args.frequencies.split(",")]

    factory_args = dict(
        antennas=enabled_antennas,
        tx_power=args.tx_power,
        tls_enabled=args.tls_enabled,
        tls_verify=args.tls_verify,
        tls_ca_file=args.tls_ca_file,
        tls_client_cert=args.tls_client_cert,
        tls_client_key=args.tls_client_key,
        tls_server_hostname=args.tls_server_hostname,
        start_inventory=True,
        disconnect_when_done=True,
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
            "EnableAccessSpecID": False,
            "C1G2EPCMemorySelector": {
                "EnableCRC": False,
                "EnablePCBits": False,
            },
        },
        frequencies={
            "HopTableId": args.hoptable_id,
            "ChannelList": frequency_list,
            "Automatic": False,
        },
        impinj_fixed_frequency=getattr(args, "impinj_fixed_frequency", False),
    )
    if frequency_list[0] == 0:
        factory_args["frequencies"]["Automatic"] = True
        factory_args["frequencies"]["ChannelList"] = [1]

    csvlogger = CsvLogger(
        args.outfile, epc=args.epc, reader_timestamp=args.reader_timestamp
    )

    reader_clients = []
    for host_value in args.host:
        host, port = split_host_port(host_value, args.port)

        config = LLRPReaderConfig(factory_args)
        reader = LLRPReaderClient(host, port, config)
        reader.add_disconnected_callback(finish_cb)
        reader.add_tag_report_callback(csvlogger.tag_cb)
        reader_clients.append(reader)

    try:
        for reader in reader_clients:
            reader.connect()
    except Exception:
        if reader:
            logger.error(
                "Failed to establish a connection with: %r", reader.get_peername()
            )
        # On one error, abort all
        for reader in reader_clients:
            reader.disconnect()

    while True:
        try:
            # Join all threads using a timeout so it doesn't block
            # Filter out threads which have been joined or are None
            alive_readers = [reader for reader in reader_clients if reader.is_alive()]
            if not alive_readers:
                break
            for reader in alive_readers:
                reader.join(1)
        except (KeyboardInterrupt, SystemExit):
            # catch ctrl-C and stop inventory before disconnecting
            logger.info("Exit detected! Stopping readers...")
            for reader in reader_clients:
                try:
                    reader.disconnect()
                except Exception:
                    logger.exception("Error during disconnect. Ignoring...")
            break

    csvlogger.flush()
