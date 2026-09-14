from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:80]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Protocol/wire-format findings F02-F07, F14, F16.
replace_once(
    "sllurp/llrp_proto.py",
    'ubyte_ushort_ushort_ushort_pack = struct.Struct("!BHHH").pack\n',
    'ubyte_ushort_ushort_ushort_pack = struct.Struct("!BHHH").pack\nushort_ubyte_ushort_ushort_pack = struct.Struct("!HBHH").pack\n',
)
replace_once(
    "sllurp/llrp_proto.py",
    '        data = tve_header_pack(param_type, len(sub_data))\n',
    '        data = tve_header_pack(0x80 | param_type)\n',
)
replace_once(
    "sllurp/llrp_proto.py",
    '    packed = ubyte_ushort_ushort_ushort_pack(req, ant, gpipn, gpopn)\n',
    '    packed = ushort_ubyte_ushort_ushort_pack(ant, req, gpipn, gpopn)\n',
)
replace_once(
    "sllurp/llrp_proto.py",
    'Param_struct["GPITriggerValue"] = {\n    "type": 180,\n',
    'Param_struct["GPITriggerValue"] = {\n    "type": 181,\n',
)
replace_once(
    "sllurp/llrp_proto.py",
    '    _, par["ROSpecID"], par["SpecIndex"] = ubyte_uint_ushort_unpack(data)\n',
    '    _, par["ROSpecID"], par["SpecIndex"] = ubyte_uint_ushort_unpack(\n        data[:ubyte_uint_ushort_size]\n    )\n',
)
replace_once(
    "sllurp/llrp_proto.py",
    '''    byte_count = ushort_unpack(data[:ushort_size])[0]
    data = data[ushort_size:]
    par = {"GGASentence": data[ushort_size : ushort_size + byte_count]}
    data = data[ushort_size + byte_count :]
''',
    '''    byte_count = ushort_unpack(data[:ushort_size])[0]
    data = data[ushort_size:]
    par = {"GGASentence": data[:byte_count]}
    data = data[byte_count:]
''',
)
replace_once(
    "sllurp/llrp_proto.py",
    '''    byte_count = ushort_unpack(data[:ushort_size])[0]
    data = data[ushort_size:]
    par = {"RMCSentence": data[ushort_size : ushort_size + byte_count]}
    data = data[ushort_size + byte_count]
''',
    '''    byte_count = ushort_unpack(data[:ushort_size])[0]
    data = data[ushort_size:]
    par = {"RMCSentence": data[:byte_count]}
    data = data[byte_count:]
''',
)
replace_once(
    "sllurp/llrp_proto.py",
    '''    "encode": basic_auto_param_encode_generator(
        ushort_ushort_unpack, "CountryCode", "CommunicationsStandard"
    ),
''',
    '''    "encode": basic_auto_param_encode_generator(
        ushort_ushort_pack, "CountryCode", "CommunicationsStandard"
    ),
''',
)
replace_once(
    "sllurp/llrp_proto.py",
    '''Param_struct["MotoFilterTagList"] = {
    "type": TYPE_CUSTOM,
    "vendorid": VENDOR_ID_MOTOROLA,
    "subtype": 258,
    "fields": [
        "Match",
    ],
    "n_fields": ["EPCData"],
    "decode": decode_all_parameters,
}
''',
    '''Param_struct["MotoFilterTagList"] = {
    "type": TYPE_CUSTOM,
    "vendorid": VENDOR_ID_MOTOROLA,
    "subtype": 258,
    "fields": [
        "Match",
    ],
    "n_fields": ["EPC"],
    "decode": decode_MotoFilterTagList,
}
''',
)
replace_once(
    "sllurp/llrp_proto.py",
    '''                "ROReportSpec": {
                    "ROReportTrigger": "Upon_N_Tags_Or_End_Of_AISpec",
                    "TagReportContentSelector": tagReportContentSelector,
                    "N": 0,
                },
''',
    '''                "ROReportSpec": {
                    "ROReportTrigger": "Upon_N_Tags_Or_End_Of_AISpec",
                    "TagReportContentSelector": tagReportContentSelector,
                    "N": 1,
                },
''',
)

# F08: clearing mode_identifier must clear capability-derived RF mode state.
replace_once(
    "sllurp/llrp.py",
    '''        # select a mode by matching available modes to requested parameters:
        # favor mode_identifier over modulation
        if self.config.mode_identifier is not None:
''',
    '''        self.reader_mode = None

        # select a mode by matching available modes to requested parameters:
        # favor mode_identifier over modulation
        if self.config.mode_identifier is not None:
''',
)

# F10: requested disconnect must still close the peer-EOF socket and notify.
replace_once(
    "sllurp/llrp.py",
    '''        if self.disconnect_requested.is_set():
            return True

        try:
            self.hard_disconnect()
''',
    '''        if self.disconnect_requested.is_set():
            try:
                self.hard_disconnect()
            except Exception:
                logger.exception("hard_disconnect error during requested disconnect")
            self._on_disconnected()
            return True

        try:
            self.hard_disconnect()
''',
)

# F11: do not initiate the polite shutdown transaction twice.
replace_once(
    "examples/fastapi/app.py",
    '''        if READER and READER.is_alive():
            try:
                READER.llrp.stopPolitely()
                READER.disconnect()
                logging.info("RFID Reader disconnected during shutdown")
            except Exception as e:
                logging.error(f"Error during reader shutdown: {e}")
''',
    '''        if READER and READER.is_alive():
            try:
                READER.disconnect(timeout=2)
                if READER.is_alive():
                    READER.hard_disconnect()
                    READER.join(1)
                logging.info("RFID Reader disconnected during shutdown")
            except Exception as e:
                logging.error(f"Error during reader shutdown: {e}")
                READER.hard_disconnect()
''',
)

# F12: honor the requested diagnostic stream; default to stderr.
start = '''def init_logging(debug=False, logfile=None, stream="stderr"):
    """Initialize logging."""
    set_general_debug(debug)

    loglevel = logging.DEBUG if debug else logging.INFO
    logformat = "%(asctime)s %(name)s: %(levelname)s: %(message)s"
    formatter = logging.Formatter(logformat)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)
    lower_than_warning = MaxLevelFilter(logging.WARNING)
    stdout_handler.addFilter(
        lower_than_warning
    )  # messages lower than WARNING go to stdout
    stdout_handler.setLevel(loglevel)
    stderr_handler.setLevel(
        max(loglevel, logging.WARNING)
    )  # messages >= WARNING ( and >= STDOUT_LOG_LEVEL ) go to stderr

    root = logging.getLogger()
    root.setLevel(loglevel)
    root.addHandler(stderr_handler)
    root.addHandler(stdout_handler)

    if logfile:
        fhandler = logging.FileHandler(logfile)
        fhandler.setFormatter(formatter)
        root.addHandler(fhandler)
'''
replacement = '''def init_logging(debug=False, logfile=None, stream="stderr"):
    """Initialize logging on the requested diagnostic stream."""
    set_general_debug(debug)

    loglevel = logging.DEBUG if debug else logging.INFO
    logformat = "%(asctime)s %(name)s: %(levelname)s: %(message)s"
    formatter = logging.Formatter(logformat)

    if stream == "stderr":
        output_stream = sys.stderr
    elif stream == "stdout":
        output_stream = sys.stdout
    elif hasattr(stream, "write"):
        output_stream = stream
    else:
        raise ValueError("stream must be 'stderr', 'stdout', or a writable stream")

    stream_handler = logging.StreamHandler(output_stream)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(loglevel)

    root = logging.getLogger()
    root.setLevel(loglevel)
    root.addHandler(stream_handler)

    if logfile:
        fhandler = logging.FileHandler(logfile)
        fhandler.setFormatter(formatter)
        root.addHandler(fhandler)
'''
replace_once("sllurp/log.py", start, replacement)

# F13: Click must propagate the access verb's validation result.
replace_once(
    "sllurp/cli.py",
    '    _access.main(args)\n\n\n@cli.command()\ndef version():\n',
    '    status = _access.main(args)\n    if status:\n        raise click.exceptions.Exit(status)\n\n\n@cli.command()\ndef version():\n',
)

# F18: update the EPC callback recipe to the current Python callback API.
(ROOT / "sllurp/epc/README.md").write_text(
    '''# Parsing EPC Data

EPC Tag Data Standard: <https://ref.gs1.org/standards/tds/>

## SGTIN-96 to GTIN

Tag-report callbacks receive ``(reader, tags)``. EPC values may arrive as bytes,
so decode them to the 24-character hexadecimal string expected by
``parse_sgtin_96`` before parsing.

```python
from sllurp.epc.gtin import combine_gtin_with_check_digit
from sllurp.epc.sgtin_96 import parse_sgtin_96


def tag_seen_callback(_reader, tags):
    for tag_report in tags:
        epc = tag_report.get("EPC-96") or tag_report.get("EPC")
        if epc is None:
            continue
        if isinstance(epc, bytes):
            epc = epc.decode("ascii")

        parsed = parse_sgtin_96(epc)
        gtin_body = parsed["company_prefix"] + parsed["item_reference"]
        full_gtin = combine_gtin_with_check_digit(gtin_body)
        print(full_gtin)
```
''',
    encoding="utf-8",
)

# F19: SPDX project.license expressions need setuptools 77+.
replace_once(
    "pyproject.toml",
    'requires = ["setuptools>=68.0"]\n',
    'requires = ["setuptools>=77.0.0"]\n',
)

# Regression coverage kept self-contained for easy upstream review.
(ROOT / "tests/test_audit_protocol_regressions.py").write_text(
    r'''import logging
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
    assert "READER.llrp.stopPolitely()" not in source
    assert "READER.disconnect(timeout=2)" in source


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


def test_moto_filter_tag_list_uses_dedicated_decoder_and_epc_key():
    info = proto.Param_struct["MotoFilterTagList"]
    assert info["decode"] is proto.decode_MotoFilterTagList
    assert info["n_fields"] == ["EPC"]


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
''',
    encoding="utf-8",
)

print("Applied upstream audit fixes")
