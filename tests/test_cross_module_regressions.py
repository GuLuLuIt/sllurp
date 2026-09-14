import io
import logging
import math
import threading
from types import SimpleNamespace

import pytest

import sllurp.lock as lock_module
import sllurp.verb.access as access_module
import sllurp.verb.inventory as inventory_module
import sllurp.verb.log as log_module
from sllurp.dedup import TagReportDeduplicator, default_tag_key
from sllurp.log import UTCFormatter
from sllurp.reader_management import HTTPReaderManager
from sllurp.util import format_host_port, func


class FakeReader:
    def __init__(self, host="reader", port=5084, config=None):
        self.host = host
        self.port = port
        self.config = config
        self.connected = False
        self.disconnected = False
        self.alive = False
        self.access_specs = []
        self.disconnected_callbacks = []
        self.tag_callbacks = []
        self.state_callbacks = []

    def get_peername(self):
        return self.host, self.port

    def start_access_spec(self, opspec, stop_after_count=0, **kwargs):
        self.access_specs.append((opspec, stop_after_count, kwargs))
        return "started"

    def disconnect(self):
        self.disconnected = True
        self.alive = False

    def connect(self):
        self.connected = True

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        return None

    def add_disconnected_callback(self, callback):
        self.disconnected_callbacks.append(callback)

    def add_tag_report_callback(self, callback):
        self.tag_callbacks.append(callback)

    def add_state_callback(self, state, callback):
        self.state_callbacks.append((state, callback))


def test_utc_formatter_emits_iso_utc_timestamp():
    formatter = UTCFormatter("%(asctime)s", datefmt="%Y-%m-%dT%H:%M:%S")
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "x", (), None)
    record.created = 0
    record.msecs = 123

    assert formatter.formatTime(record, formatter.datefmt) == "1970-01-01T00:00:00.123Z"


def test_func_and_ipv6_host_formatting():
    def caller():
        return func()

    assert caller() == "caller"
    assert format_host_port("reader.example", 5084) == "reader.example:5084"
    assert format_host_port("2001:db8::1", 5084) == "[2001:db8::1]:5084"


@pytest.mark.parametrize("window", [math.nan, math.inf, -math.inf, -0.1])
def test_dedup_rejects_non_finite_or_negative_window(window):
    with pytest.raises(ValueError, match="finite non-negative"):
        TagReportDeduplicator(window_seconds=window)


@pytest.mark.parametrize("capacity", [True, False, 0, -1, 1.5])
def test_dedup_rejects_invalid_capacity(capacity):
    with pytest.raises(ValueError, match="positive integer"):
        TagReportDeduplicator(max_entries=capacity)


def test_dedup_freezes_mixed_mapping_keys_and_sets_stably():
    tag = {"custom": {1: {"b", "a"}, "2": [1, 2]}}
    key1 = default_tag_key(tag)
    key2 = default_tag_key(tag)
    assert key1 == key2
    hash(key1)


def test_csv_reader_timestamp_falls_back_from_uptime_to_host_time(monkeypatch):
    output = io.StringIO()
    csvlogger = log_module.CsvLogger(output, reader_timestamp=True)
    reader = FakeReader()
    monkeypatch.setattr(log_module.time, "time", lambda: 123.25)

    csvlogger.tag_cb(
        reader,
        [
            {
                "EPC": "abc",
                "LastSeenTimestampUptime": 9_000_000,
                "AntennaID": 1,
                "PeakRSSI": -40,
                "TagSeenCount": 1,
            }
        ],
    )

    assert "123.25,reader:5084,1,-40,abc" in output.getvalue()


def test_csv_epc_filter_normalizes_bytes_and_formats_ipv6(monkeypatch):
    output = io.StringIO()
    csvlogger = log_module.CsvLogger(output, epc="AABB")
    reader = FakeReader("2001:db8::1", 5084)
    monkeypatch.setattr(log_module.time, "time", lambda: 10.0)

    csvlogger.tag_cb(
        reader,
        [
            {
                "EPC": b"aabb",
                "AntennaID": 2,
                "PeakRSSI": -30,
                "TagSeenCount": 2,
            }
        ],
    )

    text = output.getvalue()
    assert "10.0,[2001:db8::1]:5084,2,-30,aabb" in text
    assert csvlogger.num_tags == 2


def test_csv_logger_serializes_multi_reader_writes(monkeypatch):
    output = io.StringIO()
    csvlogger = log_module.CsvLogger(output)
    monkeypatch.setattr(log_module.time, "time", lambda: 10.0)

    def write_batch(index):
        reader = FakeReader(f"reader-{index}")
        tags = [
            {
                "EPC": f"tag-{index}-{item}",
                "AntennaID": 1,
                "PeakRSSI": -40,
                "TagSeenCount": 1,
            }
            for item in range(100)
        ]
        csvlogger.tag_cb(reader, tags)

    threads = [threading.Thread(target=write_batch, args=(index,)) for index in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert csvlogger.num_tags == 400
    assert len(output.getvalue().splitlines()) == 401


def test_inventory_tracks_multi_reader_counts_independently(monkeypatch):
    inventory_module._reset_stats()
    reader_a = FakeReader("a")
    reader_b = FakeReader("b")
    times = iter([10.0, 12.0, 20.0, 22.0])
    monkeypatch.setattr(inventory_module, "monotonic", lambda: next(times))

    inventory_module.inventory_start_cb(reader_a, None)
    inventory_module.inventory_start_cb(reader_b, None)
    inventory_module.tag_report_cb(reader_a, [{"TagSeenCount": 2}])
    inventory_module.tag_report_cb(reader_b, [{"TagSeenCount": 3}])

    assert inventory_module.numtags == 5
    assert inventory_module._reader_tag_counts[id(reader_a)] == 2
    assert inventory_module._reader_tag_counts[id(reader_b)] == 3

    inventory_module.finish_cb(reader_a)
    inventory_module.finish_cb(reader_b)


def test_access_write_payload_is_read_once_and_reused_for_multiple_readers(monkeypatch):
    access_module._reset_runtime_state()
    access_module.args = SimpleNamespace(
        read_words=None,
        write_words=2,
        access_password=0,
        mb=3,
        word_ptr=0,
        count=1,
    )

    class FakeStdin:
        buffer = io.BytesIO(b"\x01\x02\x03\x04")

    fake_stdin = FakeStdin()
    monkeypatch.setattr(access_module.sys, "stdin", fake_stdin)
    reader_a = FakeReader("a")
    reader_b = FakeReader("b")

    assert access_module.access_cb(reader_a, None) == "started"
    assert fake_stdin.buffer.tell() == 4
    assert access_module.access_cb(reader_b, None) == "started"
    assert fake_stdin.buffer.tell() == 4
    assert reader_a.access_specs[-1][0].WriteData == b"\x01\x02\x03\x04"
    assert reader_b.access_specs[-1][0].WriteData == b"\x01\x02\x03\x04"


def test_lock_main_forwards_time_to_reader_duration(monkeypatch):
    args = SimpleNamespace(
        host=["reader"],
        port=5084,
        time=2.5,
        every_n=1,
        antennas="1",
        tx_power=0,
        tari=0,
        session=2,
        mode_identifier=None,
        population=4,
        count=0,
        privilege=0,
        data_field=0,
        access_password=0,
        debug=False,
        logfile=None,
    )
    created = []

    class CapturingReader(FakeReader):
        def __init__(self, host, port, config):
            super().__init__(host, port, config)
            created.append(self)

    monkeypatch.setattr(lock_module, "parse_args", lambda: setattr(lock_module, "args", args))
    monkeypatch.setattr(lock_module, "init_logging", lambda: None)
    monkeypatch.setattr(lock_module, "LLRPReaderClient", CapturingReader)

    lock_module.main()

    assert created[0].config.duration == 2.5
    assert created[0].config.disconnect_when_done is True


@pytest.mark.parametrize("timeout", [math.nan, math.inf, -math.inf, 0, -1, True])
def test_reader_management_rejects_invalid_timeouts(timeout):
    with pytest.raises(ValueError, match="finite number greater than zero"):
        HTTPReaderManager("https://reader.example", timeout=timeout)
