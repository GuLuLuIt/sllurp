import logging
import struct
from pathlib import Path

import pytest
from click.testing import CliRunner

import sllurp.llrp as llrp_module
import sllurp.llrp_proto as proto
from sllurp.cli import cli
from sllurp.llrp import LLRPClient, LLRPReaderClient, LLRPReaderConfig, LLRPReaderState
from sllurp.log import init_logging


class Response:
    def __init__(self, name, message_id, success=True):
        self._name = name
        self._success = success
        self.msgdict = {
            name: {
                "ID": message_id,
                "LLRPStatus": {
                    "StatusCode": "Success" if success else "Failure",
                    "ErrorDescription": "audit probe",
                },
            }
        }

    def getName(self):
        return self._name

    def isSuccess(self):
        return self._success


def _respond(client, name, success=True):
    client.handleMessage(Response(name, client.last_msg_id, success=success))


def _message_names(messages):
    return [
        proto.get_message_name_from_type(*proto.msg_header_decode(data)[:3])
        for data in messages
    ]


def _mode_capabilities():
    return {
        "GeneralDeviceCapabilities": {"MaxNumberOfAntennaSupported": 1},
        "RegulatoryCapabilities": {
            "UHFBandCapabilities": {
                "TransmitPowerLevelTableEntry": [
                    {"Index": 1, "TransmitPowerValue": 3000}
                ],
                "UHFC1G2RFModeTable": {
                    "UHFC1G2RFModeTableEntry": [
                        {"ModeIdentifier": 5, "MinTari": 6, "MaxTari": 25}
                    ]
                },
            }
        },
    }


def test_f01_add_rospec_rejection_rolls_back_without_fatal_exception():
    old = LLRPReaderConfig({"session": 2})
    new = LLRPReaderConfig({"session": 1})
    sent = []
    client = LLRPClient(old, transport_tx_write=sent.append)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}

    transition = client.apply_config(new)
    _respond(client, "DELETE_ACCESSSPEC_RESPONSE")
    _respond(client, "DELETE_ROSPEC_RESPONSE")
    _respond(client, "ADD_ROSPEC_RESPONSE", success=False)
    _respond(client, "ADD_ROSPEC_RESPONSE")
    _respond(client, "ENABLE_ROSPEC_RESPONSE")

    assert transition.done and not transition.succeeded
    assert client.config is old
    assert client.state == LLRPReaderState.STATE_INVENTORYING


def test_f01_enable_rejection_deletes_replacement_before_restoring_old_rospec():
    old = LLRPReaderConfig({"session": 2})
    new = LLRPReaderConfig({"session": 1})
    sent = []
    client = LLRPClient(old, transport_tx_write=sent.append)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}

    transition = client.apply_config(new)
    _respond(client, "DELETE_ACCESSSPEC_RESPONSE")
    _respond(client, "DELETE_ROSPEC_RESPONSE")
    _respond(client, "ADD_ROSPEC_RESPONSE")
    _respond(client, "ENABLE_ROSPEC_RESPONSE", success=False)
    _respond(client, "DELETE_ROSPEC_RESPONSE")
    _respond(client, "ADD_ROSPEC_RESPONSE")
    _respond(client, "ENABLE_ROSPEC_RESPONSE")

    names = _message_names(sent)
    first_enable = names.index("ENABLE_ROSPEC")
    second_add = names.index("ADD_ROSPEC", names.index("ADD_ROSPEC") + 1)
    assert "DELETE_ROSPEC" in names[first_enable + 1 : second_add]
    assert transition.done and not transition.succeeded
    assert client.state == LLRPReaderState.STATE_INVENTORYING


@pytest.mark.parametrize("options", [
    {}, {"duration_sec": 10}, {"report_every_n_tags": 50},
    {"report_every_n_tags": 50, "report_timeout_ms": 1000},
])
def test_f02_reporting_preserves_aispec_boundaries(options):
    rospec = proto.LLRPROSpec(None, 1, **options)
    report = rospec["ROReportSpec"]
    assert report["N"] == 0
    assert report["ROReportTrigger"] == "Upon_N_Tags_Or_End_Of_AISpec"
    # Check the wire trigger, not just the generated dictionary.
    encoded = proto.encode_param("ROReportSpec", report)
    assert encoded[4:7] == b"\x01\x00\x00"


def test_f03_get_reader_config_field_order():
    info = proto.Message_struct["GET_READER_CONFIG"]
    payload = info["encode"](
        {"AntennaID": 1, "RequestedData": 3, "GPIPortNum": 4, "GPOPortNum": 5},
        info,
    )
    assert payload[:7] == struct.pack("!HBHH", 1, 3, 4, 5)


def test_f04_gpi_and_periodic_trigger_types_are_distinct():
    assert proto.Param_struct["PeriodicTriggerValue"]["type"] == 180
    assert proto.Param_struct["GPITriggerValue"]["type"] == 181


def test_f05_f06_aispec_event_accepts_tv_singulation_details():
    details = proto.encode_param(
        "C1G2SingulationDetails", {"NumCollisionSlots": 2, "NumEmptySlots": 3}
    )
    assert details == b"\x92\x00\x02\x00\x03"
    fixed = struct.pack("!BIH", 0, 1, 1)
    parsed, _ = proto.decode_AISpecEvent(fixed + details)
    assert parsed["C1G2SingulationDetails"] == {
        "NumCollisionSlots": 2,
        "NumEmptySlots": 3,
    }


def test_f07_impinj_gps_sentences_preserve_exact_payload():
    gga = b"$GPGGA,123519,4807.038,N,01131.000,E"
    rmc = b"$GPRMC,123519,A,4807.038,N,01131.000,E"
    decoded_gga, _ = proto.decode_ImpinjGGASentence(struct.pack("!H", len(gga)) + gga)
    decoded_rmc, _ = proto.decode_ImpinjRMCSentence(struct.pack("!H", len(rmc)) + rmc)
    assert decoded_gga["GGASentence"] == gga
    assert decoded_rmc["RMCSentence"] == rmc


def test_f08_clearing_mode_identifier_clears_cached_reader_mode():
    client = LLRPClient(LLRPReaderConfig({"mode_identifier": 5}), lambda _: None)
    caps = _mode_capabilities()
    client.parseCapabilities(caps)
    assert client.reader_mode["ModeIdentifier"] == 5
    client.config = LLRPReaderConfig({"mode_identifier": None})
    client.parseCapabilities(caps)
    assert client.reader_mode is None


def test_f09_hard_disconnect_resets_protocol_state_and_pending_requests():
    class FakeSocket:
        def shutdown(self, _how):
            pass

        def close(self):
            pass

    reader = LLRPReaderClient("reader", config=LLRPReaderConfig())
    reader._socket = FakeSocket()
    reader.llrp.state = LLRPReaderState.STATE_INVENTORYING
    reader.llrp._pending_requests.register("TEST_RESPONSE", 1)
    reader.hard_disconnect()
    assert reader._socket is None
    assert reader.llrp.state == LLRPReaderState.STATE_DISCONNECTED
    assert len(reader.llrp._pending_requests) == 0


def test_f10_requested_disconnect_peer_eof_still_cleans_and_notifies(monkeypatch):
    calls = []

    class FakeSocket:
        def recv(self, _size):
            return b""

        def shutdown(self, _how):
            pass

        def close(self):
            pass

    reader = LLRPReaderClient("reader", config=LLRPReaderConfig())
    sock = FakeSocket()
    reader._socket = sock
    reader.disconnect_requested.set()
    reader.add_disconnected_callback(lambda _reader: calls.append(1))
    monkeypatch.setattr(llrp_module.select, "select", lambda *_: ([sock], [], []))
    reader.main_loop()
    assert reader._socket is None
    assert reader.llrp.state == LLRPReaderState.STATE_DISCONNECTED
    assert calls == [1]


def test_f12_default_logging_keeps_info_off_stdout(monkeypatch):
    import io
    import sys

    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    try:
        init_logging()
        logging.getLogger("audit").info("diagnostic")
        print("machine-data")
        assert out.getvalue() == "machine-data\n"
        assert "diagnostic" in err.getvalue()
    finally:
        for handler in root.handlers[:]:
            if handler not in handlers:
                root.removeHandler(handler)
                handler.close()
        root.handlers[:] = handlers
        root.setLevel(level)


def test_f13_invalid_access_cli_returns_nonzero():
    result = CliRunner().invoke(cli, ["access", "offline.invalid"])
    assert result.exit_code == 2


def test_f14_moto_filter_tag_list_uses_dedicated_decoder_and_epc_key():
    info = proto.Param_struct["MotoFilterTagList"]
    assert info["decode"] is proto.decode_MotoFilterTagList
    assert "EPC" in info["n_fields"]
    assert "EPCData" not in info["n_fields"]
    epcs = [bytes.fromhex("00112233445566778899aabb"),
            bytes.fromhex("112233445566778899aabbcc")]
    payload = b"\x00" + b"".join(struct.pack("!HHH", 241, 18, 96) + epc for epc in epcs)
    decoded, _ = info["decode"](payload)
    assert decoded["Match"] == proto.RuleType_Type2Name[0]
    assert len(decoded["EPC"]) == 2


def test_f15_config_state_is_deeply_detached():
    client = LLRPClient(LLRPReaderConfig(), lambda _: None)
    client.applied_config_snapshot = {"antennas": [1]}
    client.reader_config_summary = {"gpi_ports": [{"GPIPortNum": 1}]}
    state = client.get_config_state()
    state["applied"]["antennas"].append(99)
    state["reported_reader"]["gpi_ports"][0]["GPIPortNum"] = 99
    again = client.get_config_state()
    assert again["applied"]["antennas"] == [1]
    assert again["reported_reader"]["gpi_ports"][0]["GPIPortNum"] == 1


def test_f16_regulatory_capabilities_encoder_uses_pack():
    encoded = proto.encode_param(
        "RegulatoryCapabilities", {"CountryCode": 840, "CommunicationsStandard": 1}
    )
    assert encoded[4:8] == struct.pack("!HH", 840, 1)


def test_f17_cli_recipe_uses_comma_separated_antennas():
    text = Path("examples/cli-recipes.md").read_text(encoding="utf-8")
    assert "sllurp inventory -a 1,2 READER_HOST" in text
    assert "sllurp inventory -a 1 -a 2 READER_HOST" not in text


def test_f18_epc_recipe_is_python3_and_current_callback_shape():
    text = Path("sllurp/epc/README.md").read_text(encoding="utf-8")
    code = text.split("```python", 1)[1].split("```", 1)[0]
    compile(code, "epc-recipe", "exec")
    assert "def tag_seen_callback(_reader, tags):" in code
    assert '.decode("ascii")' in code


def test_f19_minimum_setuptools_supports_spdx_license_expression():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'requires = ["setuptools>=77.0.0"]' in text
