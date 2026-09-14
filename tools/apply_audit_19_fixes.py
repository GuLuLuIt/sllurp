from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    file_path = ROOT / path
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:80]!r}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


# F01/F08/F09/F10/F15: runtime state, rollback, cleanup, and detached snapshots.
replace_once(
    "sllurp/llrp.py",
    "from collections import defaultdict\n",
    "from collections import defaultdict\nfrom copy import deepcopy\n",
)

replace_once(
    "sllurp/llrp.py",
    '''        return {
            "desired": snapshot_config(self.desired_config),
            "generated_rospec": (
                None
                if self.generated_config_snapshot is None
                else dict(self.generated_config_snapshot)
            ),
            "applied": (
                None
                if self.applied_config_snapshot is None
                else dict(self.applied_config_snapshot)
            ),
            "reported_reader": dict(self.reader_config_summary),
        }
''',
    '''        return {
            "desired": snapshot_config(self.desired_config),
            "generated_rospec": deepcopy(self.generated_config_snapshot),
            "applied": deepcopy(self.applied_config_snapshot),
            "reported_reader": deepcopy(self.reader_config_summary),
        }
''',
)

replace_once(
    "sllurp/llrp.py",
    '''        def restore_old(error):
            try:
                self._install_runtime_config(old_config)
            except Exception as rollback_error:
                self.setState(LLRPReaderState.STATE_DISCONNECTED)
                fail(f"{error}; rollback configuration failed: {rollback_error}")
                return

            if was_inventorying:
                self.setState(LLRPReaderState.STATE_CONNECTED)

                def restored(state, is_success, *args):
                    if not is_success:
                        self.setState(LLRPReaderState.STATE_DISCONNECTED)
                        fail(f"{error}; rollback inventory restart failed")
                    else:
                        fail(error)

                self.startInventory(force_regen_rospec=True, onCompletion=restored)
            elif was_paused:
                self.setState(LLRPReaderState.STATE_PAUSED)
                fail(error)
            else:
                self.setState(LLRPReaderState.STATE_CONNECTED)
                fail(error)
''',
    '''        def restore_old(error):
            try:
                self._install_runtime_config(old_config)
            except Exception as rollback_error:
                self.setState(LLRPReaderState.STATE_DISCONNECTED)
                fail(f"{error}; rollback configuration failed: {rollback_error}")
                return

            def finish_restore():
                if was_inventorying:
                    self.setState(LLRPReaderState.STATE_CONNECTED)

                    def restored(state, is_success, *args):
                        if not is_success:
                            self.setState(LLRPReaderState.STATE_DISCONNECTED)
                            fail(f"{error}; rollback inventory restart failed")
                        else:
                            fail(error)

                    self.startInventory(force_regen_rospec=True, onCompletion=restored)
                elif was_paused:
                    self.setState(LLRPReaderState.STATE_PAUSED)
                    fail(error)
                else:
                    self.setState(LLRPReaderState.STATE_CONNECTED)
                    fail(error)

            def after_rospec_cleanup(state, is_success, *args):
                if not is_success:
                    self.setState(LLRPReaderState.STATE_DISCONNECTED)
                    fail(f"{error}; rollback ROSpec cleanup failed")
                    return
                finish_restore()

            def cleanup_replacement_rospec():
                if not was_inventorying:
                    finish_restore()
                    return
                self.setState(LLRPReaderState.STATE_CONNECTED)
                self.stopAllROSpecs(onCompletion=after_rospec_cleanup)

            def old_reader_config_restored(state, is_success, *args):
                if not is_success:
                    self.setState(LLRPReaderState.STATE_DISCONNECTED)
                    fail(f"{error}; rollback reader configuration failed")
                    return
                cleanup_replacement_rospec()

            if plan.requires_reader_config_write:
                self.setState(LLRPReaderState.STATE_CONNECTED)
                self._suppress_set_config_post_actions = True
                self.send_SET_READER_CONFIG(onCompletion=old_reader_config_restored)
            else:
                cleanup_replacement_rospec()
''',
)

replace_once(
    "sllurp/llrp.py",
    '''            if not lmsg.isSuccess():
                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]
                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]
                logger.fatal("Error %s setting reader config: %s", status, err)
                if self._suppress_set_config_post_actions:
                    self._suppress_set_config_post_actions = False
                self.processDeferreds(msgName, False)
                raise ReaderConfigurationError("Error setting reader config")
''',
    '''            if not lmsg.isSuccess():
                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]
                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]
                logger.fatal("Error %s setting reader config: %s", status, err)
                suppress_post_actions = self._suppress_set_config_post_actions
                if suppress_post_actions:
                    self._suppress_set_config_post_actions = False
                self.processDeferreds(msgName, False)
                if suppress_post_actions:
                    return
                raise ReaderConfigurationError("Error setting reader config")
''',
)

replace_once(
    "sllurp/llrp.py",
    '''            if not lmsg.isSuccess():
                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]
                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]
                logger.fatal("Error %s adding ROSpec: %s", status, err)
                self.processDeferreds(msgName, False)
                raise ReaderConfigurationError("Error adding ROSpec")
''',
    '''            if not lmsg.isSuccess():
                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]
                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]
                logger.error("Error %s adding ROSpec: %s", status, err)
                self.processDeferreds(msgName, False)
                return
''',
)

replace_once(
    "sllurp/llrp.py",
    '''        # select a mode by matching available modes to requested parameters:
        # favor mode_identifier over modulation
        if self.config.mode_identifier is not None:
''',
    '''        # Capability-derived mode state belongs to the current desired
        # configuration. Clearing mode_identifier must not reuse an earlier mode.
        self.reader_mode = None

        # select a mode by matching available modes to requested parameters:
        # favor mode_identifier over modulation
        if self.config.mode_identifier is not None:
''',
)

replace_once(
    "sllurp/llrp.py",
    '''        if self._socket:
            try:
                self._socket.shutdown(SHUT_RDWR)
            except Exception:
                logger.debug("socket shutdown failed", exc_info=True)
            self._socket.close()
            self._socket = None
''',
    '''        if self._socket:
            try:
                self._socket.shutdown(SHUT_RDWR)
            except Exception:
                logger.debug("socket shutdown failed", exc_info=True)
            self._socket.close()
            self._socket = None
        self._reset_protocol_session()
''',
)

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

# F02-F07/F14/F16: protocol reporting and wire-format correctness.
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
    '''Param_struct["GPITriggerValue"] = {
    "type": 180,
''',
    '''Param_struct["GPITriggerValue"] = {
    "type": 181,
''',
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
                    # Continuous inventory must still have a finite report
                    # trigger. One tag is the safest interoperable default.
                    "N": 1,
                },
''',
)

# F11: use the public disconnect transaction exactly once and bound shutdown.
replace_once(
    "examples/fastapi/app.py",
    '''        if READER and READER.is_alive():
            try:
                READER.llrp.stopPolitely()
                READER.disconnect()
            except Exception:
                logger.exception("Error during reader shutdown")
''',
    '''        if READER and READER.is_alive():
            try:
                READER.disconnect(timeout=2)
                if READER.is_alive():
                    READER.hard_disconnect()
                    READER.join(1)
            except Exception:
                logger.exception("Error during reader shutdown")
                READER.hard_disconnect()
''',
)

# F12: honor stderr for diagnostics so stdout can remain machine-readable.
replace_once(
    "sllurp/log.py",
    '''def init_logging(debug=False, logfile=None, stream="stderr"):
    """Initialize logging with UTC timestamps.

    The historical ``stream`` argument is retained for API compatibility.
    Sllurp continues to route INFO-and-below messages to stdout and warnings
    and errors to stderr.
    """
    set_general_debug(debug)

    loglevel = logging.DEBUG if debug else logging.INFO
    logformat = "%(asctime)s %(name)s: %(levelname)s: %(message)s"
    formatter = UTCFormatter(logformat, datefmt="%Y-%m-%dT%H:%M:%S")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)
    lower_than_warning = MaxLevelFilter(logging.WARNING)
    stdout_handler.addFilter(lower_than_warning)
    stdout_handler.setLevel(loglevel)
    stderr_handler.setLevel(max(loglevel, logging.WARNING))

    root = logging.getLogger()
    root.setLevel(loglevel)

    # Reinitialization is common in tests and embedded applications. Close
    # previous handlers so repeated setup does not leak open log files.
    previous_handlers = list(root.handlers)
    root.handlers.clear()
    for handler in previous_handlers:
        try:
            handler.close()
        except Exception:
            root.debug("failed to close previous logging handler", exc_info=True)

    root.addHandler(stderr_handler)
    root.addHandler(stdout_handler)

    if logfile:
        fhandler = logging.FileHandler(logfile)
        fhandler.setFormatter(formatter)
        fhandler.setLevel(loglevel)
        root.addHandler(fhandler)
''',
    '''def init_logging(debug=False, logfile=None, stream="stderr"):
    """Initialize logging with UTC timestamps on the requested diagnostic stream."""
    set_general_debug(debug)

    loglevel = logging.DEBUG if debug else logging.INFO
    logformat = "%(asctime)s %(name)s: %(levelname)s: %(message)s"
    formatter = UTCFormatter(logformat, datefmt="%Y-%m-%dT%H:%M:%S")

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

    # Reinitialization is common in tests and embedded applications. Close
    # previous handlers so repeated setup does not leak open log files.
    previous_handlers = list(root.handlers)
    root.handlers.clear()
    for handler in previous_handlers:
        try:
            handler.close()
        except Exception:
            pass

    root.addHandler(stream_handler)

    if logfile:
        fhandler = logging.FileHandler(logfile)
        fhandler.setFormatter(formatter)
        fhandler.setLevel(loglevel)
        root.addHandler(fhandler)
''',
)

# F13: propagate the access verb's validation status through Click.
replace_once(
    "sllurp/cli.py",
    '    _access.main(args)\n\n\n@cli.command()\ndef version():\n',
    '    status = _access.main(args)\n    if status:\n        raise click.exceptions.Exit(status)\n\n\n@cli.command()\ndef version():\n',
)

# F17/F18: current, runnable examples.
replace_once(
    "examples/cli-recipes.md",
    "sllurp inventory -a 1 -a 2 READER_HOST\n",
    "sllurp inventory -a 1,2 READER_HOST\n",
)

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

# F19: SPDX project.license strings require setuptools 77+.
replace_once(
    "pyproject.toml",
    'requires = ["setuptools>=68.0"]\n',
    'requires = ["setuptools>=77.0.0"]\n',
)

# Record the audit closure in the unreleased changelog.
replace_once(
    "CHANGELOG.md",
    "- Corrected Impinj frequency capability decoding to advance 32-bit frequency entries by the correct stride.\n",
    "- Corrected Impinj frequency capability decoding to advance 32-bit frequency entries by the correct stride.\n- Closed the 19-item 2026-09-14 repository audit: transactional rollback/cleanup, continuous reporting, LLRP wire encoders/decoders, mode reset, disconnect cleanup, FastAPI shutdown, stdout-safe logging, CLI exit status, detached state snapshots, documentation recipes, and minimum build-backend compatibility.\n",
)

# Focused regression coverage for F01-F19.
(ROOT / "tests/test_audit_19_regressions.py").write_text(
    r'''import logging
import struct
from pathlib import Path

from click.testing import CliRunner

import sllurp.llrp as llrp_module
import sllurp.llrp_proto as proto
from sllurp.cli import cli
from sllurp.llrp import LLRPClient, LLRPMessage, LLRPReaderClient, LLRPReaderConfig, LLRPReaderState
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
    _respond(client, "DELETE_ROSPEC_RESPONSE")
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

    names = [LLRPMessage(msgbytes=data).getName() for data in sent]
    first_enable = names.index("ENABLE_ROSPEC")
    second_add = names.index("ADD_ROSPEC", names.index("ADD_ROSPEC") + 1)
    assert "DELETE_ROSPEC" in names[first_enable + 1 : second_add]
    assert transition.done and not transition.succeeded
    assert client.state == LLRPReaderState.STATE_INVENTORYING


def test_f02_default_continuous_inventory_has_finite_report_trigger():
    rospec = proto.LLRPROSpec(None, 1, antennas=[1], tx_power={1: 1})
    assert rospec["AISpec"][0]["AISpecStopTrigger"]["AISpecStopTriggerType"] == "Null"
    assert rospec["ROReportSpec"]["N"] == 1


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


def test_f11_fastapi_shutdown_uses_public_disconnect_once():
    source = Path("examples/fastapi/app.py").read_text(encoding="utf-8")
    assert "READER.llrp.stopPolitely()" not in source
    assert "READER.disconnect(timeout=2)" in source


def test_f12_default_logging_keeps_info_off_stdout(monkeypatch):
    import io
    import sys

    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    init_logging()
    logging.getLogger("audit").info("diagnostic")
    print("machine-data")
    assert out.getvalue() == "machine-data\n"
    assert "diagnostic" in err.getvalue()


def test_f13_invalid_access_cli_returns_nonzero():
    result = CliRunner().invoke(cli, ["access", "offline.invalid"])
    assert result.exit_code == 2


def test_f14_moto_filter_tag_list_uses_dedicated_decoder_and_epc_key():
    info = proto.Param_struct["MotoFilterTagList"]
    assert info["decode"] is proto.decode_MotoFilterTagList
    assert info["n_fields"] == ["EPC"]


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
''',
    encoding="utf-8",
)

print("Applied F01-F19 audit fixes")
