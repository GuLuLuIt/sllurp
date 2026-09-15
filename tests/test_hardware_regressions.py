import logging
import struct

from click.testing import CliRunner

from sllurp import llrp_proto
from sllurp import log as loggie
from sllurp.cli import cli


def test_get_reader_config_wire_order():
    info = llrp_proto.Message_struct["GET_READER_CONFIG"]
    payload = info["encode"](
        {
            "AntennaID": 1,
            "RequestedData": 3,
            "GPIPortNum": 2,
            "GPOPortNum": 4,
        },
        info,
    )
    assert payload == struct.pack("!HBHH", 1, 3, 2, 4)


def test_gpi_trigger_has_distinct_parameter_type():
    assert llrp_proto.Param_struct["PeriodicTriggerValue"]["type"] == 180
    assert llrp_proto.Param_struct["GPITriggerValue"]["type"] == 181
    assert llrp_proto.Param_Type2Name[(180, 0, 0)] == "PeriodicTriggerValue"
    assert llrp_proto.Param_Type2Name[(181, 0, 0)] == "GPITriggerValue"


def test_c1g2_singulation_details_tv_encoding():
    encoded = llrp_proto.encode_param(
        "C1G2SingulationDetails",
        {"NumCollisionSlots": 2, "NumEmptySlots": 3},
    )
    assert encoded == b"\x92\x00\x02\x00\x03"


def test_aispec_event_accepts_optional_singulation_details():
    trailing = llrp_proto.encode_param(
        "C1G2SingulationDetails",
        {"NumCollisionSlots": 2, "NumEmptySlots": 3},
    )
    data = struct.pack("!BIH", 0, 7, 2) + trailing
    decoded, remainder = llrp_proto.Param_struct["AISpecEvent"]["decode"](
        data, "AISpecEvent"
    )
    assert remainder == ""
    assert decoded["ROSpecID"] == 7
    assert decoded["SpecIndex"] == 2
    assert decoded["EventType"] == "End_of_AISpec"
    assert decoded["C1G2SingulationDetails"] == {
        "NumCollisionSlots": 2,
        "NumEmptySlots": 3,
    }


def test_impinj_gga_decoder_preserves_entire_nmea_sentence():
    sentence = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08*47"
    data = struct.pack("!H", len(sentence)) + sentence
    decoded, remainder = llrp_proto.Param_struct["ImpinjGGASentence"]["decode"](
        data, "ImpinjGGASentence"
    )
    assert remainder == ""
    assert decoded["GGASentence"] == sentence


def test_impinj_rmc_decoder_preserves_entire_nmea_sentence():
    sentence = b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4*6A"
    data = struct.pack("!H", len(sentence)) + sentence
    decoded, remainder = llrp_proto.Param_struct["ImpinjRMCSentence"]["decode"](
        data, "ImpinjRMCSentence"
    )
    assert remainder == ""
    assert decoded["RMCSentence"] == sentence


def test_motorola_filter_tag_list_uses_dedicated_decoder():
    decoder = llrp_proto.Param_struct["MotoFilterTagList"]["decode"]
    assert decoder is llrp_proto.decode_MotoFilterTagList


def test_regulatory_capabilities_encoder_packs_fields():
    encoded = llrp_proto.encode_param(
        "RegulatoryCapabilities",
        {"CountryCode": 840, "CommunicationsStandard": 1},
    )
    assert encoded == struct.pack("!HHHH", 143, 8, 840, 1)


def test_default_logging_does_not_contaminate_stdout(capsys):
    root = logging.getLogger()
    previous_handlers = list(root.handlers)
    previous_level = root.level
    try:
        loggie.init_logging(debug=False)
        logging.getLogger("sllurp-regression").info("stderr-only-marker")
        captured = capsys.readouterr()
        assert "stderr-only-marker" not in captured.out
        assert "stderr-only-marker" in captured.err
    finally:
        for handler in list(root.handlers):
            try:
                handler.close()
            except Exception:
                pass
        root.handlers[:] = previous_handlers
        root.setLevel(previous_level)


def test_access_command_propagates_nonzero_return(monkeypatch):
    monkeypatch.setattr("sllurp.cli._access.main", lambda args: 1)
    result = CliRunner().invoke(
        cli,
        ["access", "offline.invalid", "--read-words", "1", "--count", "1"],
    )
    assert result.exit_code == 1


def test_access_connection_failure_returns_nonzero(monkeypatch):
    class FailingReader:
        def __init__(self, host, port, config):
            self.host = host
            self.port = port

        def add_disconnected_callback(self, callback):
            pass

        def add_tag_report_callback(self, callback):
            pass

        def add_state_callback(self, state, callback):
            pass

        def connect(self):
            raise OSError("offline")

        def get_peername(self):
            return self.host, self.port

        def disconnect(self):
            pass

        def is_alive(self):
            return False

        def join(self, timeout):
            pass

    monkeypatch.setattr("sllurp.verb.access.LLRPReaderClient", FailingReader)
    result = CliRunner().invoke(
        cli,
        ["access", "offline.invalid", "--read-words", "1", "--count", "1"],
    )
    assert result.exit_code == 1
