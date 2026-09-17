import binascii
import logging
import pprint
import sys
from threading import RLock

from sllurp.llrp import (
    C1G2Read,
    C1G2Write,
    LLRPReaderClient,
    LLRPReaderConfig,
    LLRPReaderState,
)
from sllurp.log import get_logger
from sllurp.util import monotonic, split_host_port

start_time = None

tagReport = 0
logger = get_logger(__name__)

args = None

_stats_lock = RLock()
_write_lock = RLock()
_output_lock = RLock()
_reader_start_times = {}
_reader_tag_counts = {}
_write_data = None
_write_data_words = None


def _reader_key(reader):
    return id(reader)


def _reset_runtime_state():
    global start_time, tagReport, _write_data, _write_data_words
    with _stats_lock:
        start_time = None
        tagReport = 0
        _reader_start_times.clear()
        _reader_tag_counts.clear()
    with _write_lock:
        _write_data = None
        _write_data_words = None


def _mark_reader_start(reader):
    global start_time
    now = monotonic()
    with _stats_lock:
        if start_time is None:
            start_time = now
        _reader_start_times.setdefault(_reader_key(reader), now)
    return now


def finish_cb(reader):
    now = monotonic()
    with _stats_lock:
        reader_key = _reader_key(reader)
        reader_start = _reader_start_times.pop(reader_key, None)
        reader_count = _reader_tag_counts.pop(reader_key, 0)
        total_count = tagReport
        global_start = start_time

    started = reader_start if reader_start is not None else global_start
    runtime = max(now - started, 0.0) if started is not None else 0.0
    rate = reader_count / runtime if runtime > 0 else 0.0
    logger.info(
        "reader %r: %d tags seen (%.1f tags/second); total=%d",
        reader.get_peername() if reader is not None else None,
        reader_count,
        rate,
        total_count,
    )


def _get_write_data(reader):
    """Read a write payload once and reuse it for every configured reader."""
    global _write_data, _write_data_words

    word_count = args.write_words
    expected_bytes = word_count * 2
    with _write_lock:
        if _write_data is not None and _write_data_words == word_count:
            return _write_data

        data = sys.stdin.buffer.read(expected_bytes)
        if len(data) != expected_bytes:
            logger.error(
                "Expected %d bytes on stdin for --write-words=%d, got %d",
                expected_bytes,
                word_count,
                len(data),
            )
            reader.disconnect()
            return None

        _write_data = bytes(data)
        _write_data_words = word_count
        return _write_data


def access_cb(reader, state):
    _mark_reader_start(reader)

    if args.read_words:
        opspec = C1G2Read(
            AccessPassword=args.access_password,
            MB=args.mb,
            WordPtr=args.word_ptr,
            WordCount=args.read_words,
        )
    elif args.write_words:
        data = _get_write_data(reader)
        if data is None:
            return None

        opspec = C1G2Write(
            AccessPassword=args.access_password,
            MB=args.mb,
            WordPtr=args.word_ptr,
            WriteDataWordCount=args.write_words,
            WriteData=data,
        )
    else:
        return None

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
        if "C1G2ReadOpSpecResult" in tag:
            data = tag["C1G2ReadOpSpecResult"].get("ReadData")
            if data:
                with _output_lock:
                    sys.stdout.buffer.write(data)
                    flush = getattr(sys.stdout.buffer, "flush", None)
                    if flush is not None:
                        flush()
                logger.debug("hex data: %s", binascii.hexlify(data))


def main(main_args):
    global start_time
    global args
    args = main_args

    if not args.host:
        logger.info("No readers specified.")
        return 0

    if args.read_words is not None and args.write_words is not None:
        logger.error("Choose only one of --read-words or --write-words.")
        return 2
    if args.read_words is None and args.write_words is None:
        logger.info("Error: Either --read-words or --write-words has to be chosen.")
        return 2

    _reset_runtime_state()

    enabled_antennas = [int(x.strip()) for x in args.antennas.split(",")]
    frequency_list = [int(x.strip()) for x in args.frequencies.split(",")]

    factory_args = dict(
        duration=args.time,
        ro_report_every_n_tags=getattr(args, "ro_report_every_n_tags", None),
        report_every_n_tags=args.every_n,
        antennas=enabled_antennas,
        tx_power=args.tx_power,
        tari=args.tari,
        session=args.session,
        mode_identifier=args.mode_identifier,
        tag_population=args.population,
        tls_enabled=args.tls_enabled,
        tls_verify=args.tls_verify,
        tls_ca_file=args.tls_ca_file,
        tls_client_cert=args.tls_client_cert,
        tls_client_key=args.tls_client_key,
        tls_server_hostname=args.tls_server_hostname,
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

    reader_clients = []
    for host_value in args.host:
        host, port = split_host_port(host_value, args.port)

        config = LLRPReaderConfig(factory_args)
        reader = LLRPReaderClient(host, port, config)
        reader.add_disconnected_callback(finish_cb)
        reader.add_tag_report_callback(tag_report_cb)
        reader.add_state_callback(LLRPReaderState.STATE_INVENTORYING, access_cb)

        reader_clients.append(reader)

    start_time = monotonic()
    connection_failed = False
    reader = None
    try:
        for reader in reader_clients:
            reader.connect()
    except Exception:
        connection_failed = True
        if reader is not None:
            logger.error(
                "Failed to establish a connection with: %r", reader.get_peername()
            )
        for client in reader_clients:
            client.disconnect()

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

    return 1 if connection_failed else 0
