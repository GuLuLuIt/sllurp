import time
from types import SimpleNamespace

import pytest

from sllurp.llrp import (
    LLRPClient,
    LLRPReaderClient,
    LLRPReaderConfig,
    LLRPReaderState,
    LLRP_DEFAULT_PORT,
    LLRP_SECURE_PORT,
)
from sllurp.llrp_errors import ReaderConfigurationError


def test_legacy_channelist_is_normalized_before_validation():
    config = LLRPReaderConfig(
        {
            "frequencies": {
                "HopTableId": 1,
                "Channelist": [1],
                "Automatic": False,
            }
        }
    )
    assert config.frequencies["ChannelList"] == [1]
    assert "Channelist" not in config.frequencies


def test_modern_channel_list_wins_if_both_keys_are_present():
    config = LLRPReaderConfig(
        {
            "frequencies": {
                "HopTableId": 1,
                "ChannelList": [2],
                "Channelist": [1],
                "Automatic": False,
            }
        }
    )
    assert config.frequencies["ChannelList"] == [2]
    assert "Channelist" not in config.frequencies


def test_llrp_update_config_rejects_live_replacement_without_mutation():
    old = LLRPReaderConfig()
    new = LLRPReaderConfig({"session": 1})
    client = LLRPClient(old, transport_tx_write=lambda _: None)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}

    with pytest.raises(ReaderConfigurationError, match="disconnected"):
        client.update_config(new)

    assert client.config is old
    assert client.rospec == {"ROSpecID": 1}


def test_reader_update_config_is_atomic_and_updates_implicit_secure_port():
    old = LLRPReaderConfig()
    reader = LLRPReaderClient("reader.example", config=old)
    assert reader.get_peername()[1] == LLRP_DEFAULT_PORT

    reader.llrp.state = LLRPReaderState.STATE_INVENTORYING
    live = LLRPReaderConfig({"session": 1})
    with pytest.raises(ReaderConfigurationError, match="disconnected"):
        reader.update_config(live)
    assert reader.config is old
    assert reader.llrp.config is old

    reader.llrp.state = LLRPReaderState.STATE_DISCONNECTED
    secure = LLRPReaderConfig({"tls_enabled": True})
    reader.update_config(secure)
    assert reader.config is secure
    assert reader.llrp.config is secure
    assert reader.get_peername()[1] == LLRP_SECURE_PORT


def test_explicit_port_is_not_changed_by_disconnected_config_update():
    reader = LLRPReaderClient("reader.example", port=6000, config=LLRPReaderConfig())
    reader.update_config(LLRPReaderConfig({"tls_enabled": True}))
    assert reader.get_peername()[1] == 6000


def test_timed_pause_schedules_exactly_one_resume_after_pause_ack():
    sent = []
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=sent.append)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}

    pause_cb = client.pause(0.03)
    assert client.state == LLRPReaderState.STATE_PAUSING
    assert client._pause_resume_timer is None

    pause_cb(client.state, True)
    assert client.state == LLRPReaderState.STATE_PAUSED
    assert client._pause_resume_timer is not None

    time.sleep(0.08)
    assert client.state == LLRPReaderState.STATE_SENT_ENABLE_ROSPEC
    assert len(client._deferreds["ENABLE_ROSPEC_RESPONSE"]) == 1

    client._cancel_pause_resume_timer()


def test_disconnect_state_invalidates_stale_timed_pause_resume():
    sent = []
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=sent.append)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}

    pause_cb = client.pause(0.03)
    pause_cb(client.state, True)
    assert client.state == LLRPReaderState.STATE_PAUSED

    client.setState(LLRPReaderState.STATE_DISCONNECTED)
    time.sleep(0.08)
    assert client.state == LLRPReaderState.STATE_DISCONNECTED
    assert not client._deferreds["ENABLE_ROSPEC_RESPONSE"]


def test_pause_rejects_invalid_duration_values():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda _: None)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}
    for value in (-1, float("inf"), float("nan"), True, "1"):
        with pytest.raises(ReaderConfigurationError):
            client.pause(value)


def test_callback_dispatch_uses_stable_snapshot_when_callback_removes_itself():
    reader = LLRPReaderClient("reader.example", config=LLRPReaderConfig())
    calls = []

    def first(rdr, tags):
        calls.append("first")
        rdr.remove_tag_report_callback(first)

    def second(rdr, tags):
        calls.append("second")

    reader.add_tag_report_callback(first)
    reader.add_tag_report_callback(second)
    msg = SimpleNamespace(msgdict={"RO_ACCESS_REPORT": {"TagReportData": [{"EPC": b"x"}]}})

    reader._on_llrp_tag_report(None, msg)
    assert calls == ["first", "second"]

    calls.clear()
    reader._on_llrp_tag_report(None, msg)
    assert calls == ["second"]


def test_callback_added_during_dispatch_runs_on_next_dispatch_only():
    reader = LLRPReaderClient("reader.example", config=LLRPReaderConfig())
    calls = []

    def later(rdr, tags):
        calls.append("later")

    def first(rdr, tags):
        calls.append("first")
        rdr.add_tag_report_callback(later)

    reader.add_tag_report_callback(first)
    msg = SimpleNamespace(msgdict={"RO_ACCESS_REPORT": {"TagReportData": []}})
    reader._on_llrp_tag_report(None, msg)
    assert calls == ["first"]

    reader._on_llrp_tag_report(None, msg)
    assert calls == ["first", "first", "later"]


def test_parse_reader_config_builds_normalized_summary_without_destroying_raw_data():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda _: None)
    raw = {
        "AntennaProperties": [
            {"AntennaID": 1, "AntennaConnected": True, "AntennaGain": 25},
            {"AntennaID": 2, "AntennaConnected": False, "AntennaGain": 0},
        ],
        "AntennaConfiguration": {"AntennaID": 1, "RFTransmitter": {"TransmitPower": 10}},
        "KeepaliveSpec": {"KeepaliveTriggerType": 1, "TimeInterval": 1000},
        "GPIPortCurrentState": {"GPIPortNum": 1, "State": True},
    }
    client.reader_config = raw

    assert client.parseReaderConfig(raw) is None

    summary = client.reader_config_summary
    assert client.reader_config is raw
    assert summary["antenna_properties"][1] == {"connected": True, "gain": 25}
    assert summary["antenna_properties"][2]["connected"] is False
    assert summary["antenna_configurations"][1]["RFTransmitter"]["TransmitPower"] == 10
    assert summary["keepalive"]["TimeInterval"] == 1000
    assert summary["gpi_ports"] == [{"GPIPortNum": 1, "State": True}]


def test_parse_reader_config_rejects_non_mapping():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda _: None)
    with pytest.raises(ReaderConfigurationError):
        client.parseReaderConfig([])
