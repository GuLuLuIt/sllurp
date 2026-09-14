import logging
import struct
from pathlib import Path

from click.testing import CliRunner

import sllurp.llrp_proto as proto
from sllurp.cli import cli
from sllurp.llrp import LLRPClient, LLRPReaderClient, LLRPReaderConfig
from sllurp.log import init_logging


def test_default_continuous_inventory_reports_after_a_finite_tag_count():
    rospec = proto.LLRPROSpec(None, 1, antennas=[1], tx_power={1: 1})
    assert rospec["AISpec"][0]["AISpecStopTrigger"]["AISpecStopTriggerType"] == "Null"
    assert rospec["ROReportSpec"]["N"] == 1


def test_get_reader_config_field_order():
    info = proto.Message_struct["GET_READER_CONFIG"]
    payload = info["encode"](
        {"AntennaID": 1, "RequestedData": 3, "GPIPortNum": 4, "GPOPortNum": 5},
        info,
    )
    assert payload[:7] == struct.pack("!HBHH", 1, 3, 4, 5)


def test_gpi_trigger_type_does_not_collide_with_periodic_trigger():
    assert proto.Param_struct["PeriodicTriggerValue"]["type"] == 180
    assert proto.Param_struct["GPITriggerValue"]["type"] == 181


def test_tv_singulation_details_round_trip_inside_aispec_event():
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


def test_impinj_gps_sentence_decoders_preserve_payload():
    gga = b"$GPGGA,123519,4807.038,N,01131.000,E"
    rmc = b"$GPRMC,123519,A,4807.038,N,01131.000,E"
    decoded_gga, _ = proto.decode_ImpinjGGASentence(struct.pack("!H", len(gga)) + gga)
    decoded_rmc, _ = proto.decode_ImpinjRMCSentence(struct.pack("!H", len(rmc)) + rmc)
    assert decoded_gga["GGASentence"] == gga
    assert decoded_rmc["RMCSentence"] == rmc


def test_clearing_mode_identifier_clears_cached_reader_mode():
    caps = {
        "GeneralDeviceCapabilities": {"MaxNumberOfAntennaSupported": 1},
        "RegulatoryCapabilities": {
            "UHFBandCapabilities": {
                "TransmitPowerLevelTableEntry": [{"Index": 1, "TransmitPowerValue": 3000}],
                "UHFC1G2RFModeTable": {
                    "UHFC1G2RFModeTableEntry": [
                        {"ModeIdentifier": 5, "MinTari": 6, "MaxTari": 25}
                    ]
                },
            }
        },
    }
    client = LLRPClient(LLRPReaderConfig({"mode_identifier": 5}), lambda _: None)
    client.parseCapabilities(caps)
    assert client.reader_mode["ModeIdentifier"] == 5
    client.config = LLRPReaderConfig({"mode_identifier": None})
    client.parseCapabilities(caps)
    assert client.reader_mode is None


def test_requested_disconnect_lost_connection_still_cleans_and_notifies():
    calls = []

    class FakeSocket:
        def shutdown(self, _how):
            pass

        def close(self):
            pass

    reader = LLRPReaderClient("reader", config=LLRPReaderConfig())
    reader._socket = FakeSocket()
    reader.disconnect_requested.set()
    reader.add_disconnected_callback(lambda _reader: calls.append(1))
    assert reader.on_lost_connection() is True
    assert reader._socket is None
    assert calls == [1]


def test_fastapi_shutdown_uses_public_disconnect_once():
    source = Path("examples/fastapi/app.py").read_text(encoding="utf-8")
    lifespan_shutdown = source.split("    finally:", 1)[1].split("

app =", 1)[0]
    assert "READER.llrp.stopPolitely()" not in lifespan_shutdown
    assert "READER.disconnect(timeout=2)" in lifespan_shutdown


def test_default_logging_keeps_info_off_stdout(monkeypatch):
    import io
    import sys

    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    root = logging.getLogger()
    previous = list(root.handlers)
    root.handlers.clear()
    try:
        init_logging()
        logging.getLogger("audit").info("diagnostic")
        print("machine-data")
        assert out.getvalue() == "machine-data\n"
        assert "diagnostic" in err.getvalue()
    finally:
        root.handlers.clear()
        root.handlers.extend(previous)


def test_invalid_access_cli_returns_nonzero():
    result = CliRunner().invoke(cli, ["access", "offline.invalid"])
    assert result.exit_code == 2
    both = CliRunner().invoke(
        cli,
        ["access", "--read-words", "1", "--write-words", "1", "offline.invalid"],
    )
    assert both.exit_code == 2


def test_moto_filter_tag_list_uses_dedicated_decoder_and_epc_key():
    info = proto.Param_struct["MotoFilterTagList"]
    assert info["decode"] is proto.decode_MotoFilterTagList
    assert "EPC" in info["n_fields"]
    assert "EPCData" not in info["n_fields"]


def test_regulatory_capabilities_encoder_uses_pack():
    encoded = proto.encode_param(
        "RegulatoryCapabilities", {"CountryCode": 840, "CommunicationsStandard": 1}
    )
    assert encoded[4:8] == struct.pack("!HH", 840, 1)


def test_epc_recipe_is_python3_and_current_callback_shape():
    text = Path("sllurp/epc/README.md").read_text(encoding="utf-8")
    code = text.split("```python", 1)[1].split("```", 1)[0]
    compile(code, "epc-recipe", "exec")
    assert "def tag_seen_callback(_reader, tags):" in code
    assert '.decode("ascii")' in code


def test_minimum_setuptools_supports_spdx_license_expression():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'requires = ["setuptools>=77.0.0"]' in text
