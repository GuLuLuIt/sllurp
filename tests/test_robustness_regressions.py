import io
import struct
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import sllurp.llrp as llrp_module
from sllurp.epc.sgtin_96 import parse_sgtin_96
from sllurp.llrp import (
    DEFAULT_MAX_MESSAGE_SIZE,
    LLRPClient,
    LLRPMessage,
    LLRPReaderClient,
    LLRPReaderConfig,
    LLRPReaderState,
)
from sllurp.llrp_proto import LLRPError, LLRPROSpec, decode_param, msg_header_pack
from sllurp.util import split_host_port
from sllurp.verb import access as access_verb
from sllurp.verb.log import CsvLogger


def base_config(**overrides):
    values = {"start_inventory": False, "reset_on_connect": False}
    values.update(overrides)
    return LLRPReaderConfig(values)


def test_truncated_and_invalid_message_headers_are_rejected():
    with pytest.raises(LLRPError, match="Invalid LLRP message header"):
        LLRPMessage(msgbytes=b"\x00")

    reader = LLRPReaderClient("reader", config=base_config(max_message_size=100))
    with pytest.raises(LLRPError, match="minimum"):
        reader.raw_data_received(msg_header_pack(1, 5, 1))
    with pytest.raises(LLRPError, match="exceeds configured maximum"):
        reader.raw_data_received(msg_header_pack(1, 101, 1))


def test_truncated_and_invalid_parameters_raise_llrp_error():
    # TV AntennaID needs two payload bytes after its one-byte header.
    with pytest.raises(LLRPError, match="Truncated LLRP parameter"):
        decode_param(bytes([0x80 | 1]))
    # TLV length cannot be smaller than its own four-byte header.
    with pytest.raises(LLRPError, match="Invalid LLRP parameter header"):
        decode_param(struct.pack("!HH", 1, 2))


def test_message_size_default_is_bounded():
    assert DEFAULT_MAX_MESSAGE_SIZE == 16 * 1024 * 1024
    assert base_config().max_message_size == DEFAULT_MAX_MESSAGE_SIZE


def test_max_tari_is_applied_to_rospec():
    mode = {"ModeIdentifier": 3, "MinTari": 10, "MaxTari": 20}
    rospec = LLRPROSpec(mode, 1, tari=20, antennas=[1], tx_power={1: 1})
    rf = rospec["AISpec"][0]["InventoryParameterSpec"][0]["AntennaConfiguration"][0]
    assert rf["C1G2InventoryCommand"][0]["C1G2RFControl"]["Tari"] == 20


def test_impinj_fixed_frequency_requires_explicit_opt_in_in_reader_config():
    frequencies = {"HopTableId": 1, "ChannelList": [1, 2], "Automatic": False}
    with pytest.raises(LLRPError, match="impinj_fixed_frequency"):
        base_config(frequencies=frequencies)

    cfg = base_config(frequencies=frequencies, impinj_fixed_frequency=True)
    client = LLRPClient(cfg, transport_tx_write=lambda _: None)
    assert client._uses_impinj_extensions() is True


def test_duration_defaults_to_disconnect_and_schedules_timer(monkeypatch):
    cfg = base_config(duration=2)
    assert cfg.disconnect_when_done is True
    created = []

    class FakeTimer:
        def __init__(self, delay, callback):
            self.delay = delay
            self.callback = callback
            self.daemon = False
            self.started = False
            self.cancelled = False
            created.append(self)

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

    monkeypatch.setattr(llrp_module, "Timer", FakeTimer)
    reader = LLRPReaderClient("reader", config=cfg)
    reader._on_llrp_state_changed(LLRPReaderState.STATE_INVENTORYING)
    assert created[0].delay == 2
    assert created[0].started is True
    assert created[0].daemon is True
    reader.hard_disconnect()
    assert created[0].cancelled is True


def test_initial_connection_obeys_reconnect_policy(monkeypatch):
    reader = LLRPReaderClient(
        "reader",
        config=base_config(reconnect=True, reconnect_retries=1, reconnect_delay=0),
    )
    calls = []

    def connect_once_then_succeed():
        calls.append(1)
        if len(calls) == 1:
            raise OSError("not ready")
        return True

    monkeypatch.setattr(reader, "_connect_socket", connect_once_then_succeed)
    reader.connect(start_main_loop=False)
    assert len(calls) == 2


def test_protocol_session_reset_drops_stale_deferreds():
    reader = LLRPReaderClient("reader", config=base_config())
    reader.llrp._deferreds["GET_READER_CONFIG_RESPONSE"].append(lambda *_: None)
    reader.llrp.rospec = {"ROSpecID": 1}
    reader._reset_protocol_session()
    assert not reader.llrp._deferreds
    assert reader.llrp.rospec is None


def test_second_request_for_same_response_is_rejected():
    cfg = base_config()
    client = LLRPClient(cfg, transport_tx_write=lambda _: None)
    client._deferreds["GET_READER_CONFIG_RESPONSE"].append(lambda *_: None)
    with pytest.raises(Exception, match="already pending"):
        client.sendMessage({"GET_READER_CONFIG": {"RequestedData": 0}})


def test_tag_dispatcher_is_installed_even_after_raw_callback():
    reader = LLRPReaderClient("reader", config=base_config())
    raw_calls = []
    tag_calls = []
    reader.add_message_callback("RO_ACCESS_REPORT", lambda *_: raw_calls.append(1))
    reader.add_tag_report_callback(lambda _reader, tags: tag_calls.append(tags))
    msg = SimpleNamespace(
        getName=lambda: "RO_ACCESS_REPORT",
        msgdict={"RO_ACCESS_REPORT": {"TagReportData": [{"EPC-96": b"x" * 12}]}},
    )
    reader._on_llrp_message_received(msg)
    assert raw_calls == [1]
    assert len(tag_calls) == 1


def test_ipv6_host_parsing_and_socket_family():
    assert split_host_port("[2001:db8::1]:55084", 5084) == ("2001:db8::1", 55084)
    assert split_host_port("2001:db8::1", 5084) == ("2001:db8::1", 5084)

    raw = Mock()
    reader = LLRPReaderClient("2001:db8::1", config=base_config())
    with patch("sllurp.llrp.socket", return_value=raw) as socket_factory:
        reader._connect_socket()
    socket_factory.assert_called_once_with(llrp_module.AF_INET6, llrp_module.SOCK_STREAM)


def test_access_time_is_forwarded_and_read_write_are_exclusive(monkeypatch):
    args = SimpleNamespace(
        host=("reader",), port=5084, time=3.5, every_n=None, antennas="1",
        tx_power=0, tari=0, session=2, mode_identifier=None, population=4,
        read_words=1, write_words=None, count=0, mb=3, word_ptr=0, access_password=0,
        frequencies="1", hoptable_id=1, impinj_fixed_frequency=False,
        tls_enabled=False, tls_verify=True, tls_ca_file=None, tls_client_cert=None,
        tls_client_key=None, tls_server_hostname=None,
    )
    captured = []

    class FakeReader:
        def __init__(self, host, port, config):
            captured.append(config)
        def add_disconnected_callback(self, *args): pass
        def add_tag_report_callback(self, *args): pass
        def add_state_callback(self, *args): pass
        def connect(self): pass
        def is_alive(self): return False
        def disconnect(self): pass

    monkeypatch.setattr(access_verb, "LLRPReaderClient", FakeReader)
    access_verb.main(args)
    assert captured[0].duration == 3.5
    assert captured[0].disconnect_when_done is True

    args.read_words = 1
    args.write_words = 1
    assert access_verb.main(args) == 2


def test_csv_logger_streams_rows_instead_of_accumulating():
    output = io.StringIO()
    logger = CsvLogger(output)
    reader = SimpleNamespace(get_peername=lambda: ("reader", 5084))
    logger.tag_cb(
        reader,
        [{"EPC": "abc", "AntennaID": 1, "PeakRSSI": -40, "TagSeenCount": 1}],
    )
    text = output.getvalue()
    assert "timestamp,reader,antenna,rssi,epc" in text
    assert "reader:5084" in text
    assert not hasattr(logger, "rows")


def test_sgtin96_rejects_wrong_length_and_invalid_decimal_partition_values():
    with pytest.raises(ValueError, match="exactly 24"):
        parse_sgtin_96("30")
    with pytest.raises(ValueError, match="hexadecimal"):
        parse_sgtin_96("30" + "z" * 22)
