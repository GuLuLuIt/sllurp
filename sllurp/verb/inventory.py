"""Inventory command."""

import logging
import pprint
from threading import RLock

from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig, LLRPReaderState
from sllurp.log import get_logger
from sllurp.util import monotonic, split_host_port

start_time = None
numtags = 0
logger = get_logger(__name__)

_stats_lock = RLock()
_reader_start_times = {}
_reader_tag_counts = {}


def _reader_key(reader):
    return None if reader is None else id(reader)


def _reset_stats():
    global start_time, numtags
    with _stats_lock:
        start_time = None
        numtags = 0
        _reader_start_times.clear()
        _reader_tag_counts.clear()


def finish_cb(reader):
    now = monotonic()
    key = _reader_key(reader)
    with _stats_lock:
        started = _reader_start_times.pop(key, start_time)
        count = _reader_tag_counts.pop(
            key, numtags if reader is None else 0
        )

    runtime = max(0.0, now - started) if started is not None else 0.0
    rate = count / runtime if runtime > 0 else 0.0
    logger.info("total # of tags seen: %d (%.1f tags/second)", count, rate)


def inventory_start_cb(reader, state):
    global start_time
    now = monotonic()
    key = _reader_key(reader)
    with _stats_lock:
        start_time = now
        _reader_start_times[key] = now
        _reader_tag_counts.setdefault(key, 0)


def tag_report_cb(reader, tags):
    """Function to run each time the reader reports seeing tags."""
    global numtags
    if not tags:
        logger.info("no tags seen")
        return

    if logger.isEnabledFor(logging.INFO):
        logger.info("saw tag(s): %s", pprint.pformat(tags))

    count = sum(int(tag.get("TagSeenCount", 1)) for tag in tags)
    key = _reader_key(reader)
    with _stats_lock:
        numtags += count
        _reader_tag_counts[key] = _reader_tag_counts.get(key, 0) + count


def main(args):
    global start_time

    if not args.host:
        logger.info("No readers specified.")
        return 0

    _reset_stats()

    enabled_antennas = [int(x.strip()) for x in args.antennas.split(",")]
    frequency_list = [int(x.strip()) for x in args.frequencies.split(",")]

    factory_args = dict(
        duration=args.time,
        report_every_n_tags=args.every_n,
        dedup_seconds=getattr(args, "dedup_seconds", None),
        dedup_backend=getattr(args, "dedup_backend", "auto"),
        antennas=enabled_antennas,
        tx_power=args.tx_power,
        tari=args.tari,
        session=args.session,
        mode_identifier=args.mode_identifier,
        tag_population=args.population,
        start_inventory=True,
        disconnect_when_done=args.time and args.time > 0,
        reconnect=args.reconnect,
        reconnect_retries=args.reconnect_retries,
        tag_filter_mask=args.tag_filter_mask,
        tag_content_selector={
            "EnableROSpecID": False,
            "EnableSpecIndex": False,
            "EnableInventoryParameterSpecID": False,
            "EnableAntennaID": False,
            "EnableChannelIndex": True,
            "EnablePeakRSSI": False,
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
        keepalive_interval=args.keepalive_interval,
        tls_enabled=args.tls_enabled,
        tls_verify=args.tls_verify,
        tls_ca_file=args.tls_ca_file,
        tls_client_cert=args.tls_client_cert,
        tls_client_key=args.tls_client_key,
        tls_server_hostname=args.tls_server_hostname,
        impinj_extended_configuration=args.impinj_extended_configuration,
        impinj_search_mode=args.impinj_search_mode,
        impinj_tag_content_selector=None,
    )
    if args.impinj_reports:
        factory_args["impinj_tag_content_selector"] = {
            "EnableRFPhaseAngle": True,
            "EnablePeakRSSI": True,
            "EnableRFDopplerFrequency": True,
        }
    if frequency_list[0] == 0:
        factory_args["frequencies"]["Automatic"] = True
        factory_args["frequencies"]["ChannelList"] = [1]

    reader_clients = []
    for host_value in args.host:
        host, port = split_host_port(host_value, args.port)

        config = LLRPReaderConfig(factory_args)
        reader = LLRPReaderClient(host, port, config)
        reader.add_disconnected_callback(finish_cb)
        reader.add_tag_report_callback(tag_report_cb)
        reader.add_state_callback(
            LLRPReaderState.STATE_INVENTORYING, inventory_start_cb
        )
        reader_clients.append(reader)

    with _stats_lock:
        start_time = monotonic()

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

    LLRPReaderClient.disconnect_all_readers()
