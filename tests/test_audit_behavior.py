"""Exercise audit fixes through protocol responses and application lifecycles."""

import asyncio
import importlib.util
import io
import logging
from pathlib import Path

import pytest

from sllurp.llrp import LLRPClient, LLRPReaderClient, LLRPReaderConfig, LLRPReaderState
from sllurp.log import init_logging
from tests.test_audit_19_regressions import _message_names, _respond


@pytest.mark.parametrize("failed_index,rollback_failure,expected_tail,final_state", [
    (None, None, [], "INVENTORYING"),
    (0, None, [], "INVENTORYING"),
    (1, None, [], "INVENTORYING"),
    (2, None, ["ADD_ROSPEC", "ENABLE_ROSPEC"], "INVENTORYING"),
    (3, None, ["SET_READER_CONFIG", "ADD_ROSPEC", "ENABLE_ROSPEC"], "INVENTORYING"),
    (4, None, ["SET_READER_CONFIG", "DELETE_ROSPEC", "ADD_ROSPEC", "ENABLE_ROSPEC"], "INVENTORYING"),
    (4, 5, ["SET_READER_CONFIG"], "DISCONNECTED"),
    (4, 6, ["SET_READER_CONFIG", "DELETE_ROSPEC"], "DISCONNECTED"),
    (4, 7, ["SET_READER_CONFIG", "DELETE_ROSPEC", "ADD_ROSPEC"], "DISCONNECTED"),
    (4, 8, ["SET_READER_CONFIG", "DELETE_ROSPEC", "ADD_ROSPEC", "ENABLE_ROSPEC"], "DISCONNECTED"),
])
def test_live_transition_response_sequences(
    failed_index, rollback_failure, expected_tail, final_state
):
    old = LLRPReaderConfig({"session": 2, "keepalive_interval": 1000})
    new = LLRPReaderConfig({"session": 1, "keepalive_interval": 2000})
    sent, completed = [], []
    client = LLRPClient(old, transport_tx_write=sent.append)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}
    transition = client.apply_config(new, onCompletion=completed.append)
    forward = ["DELETE_ACCESSSPEC", "DELETE_ROSPEC", "SET_READER_CONFIG",
               "ADD_ROSPEC", "ENABLE_ROSPEC"]
    expected = forward if failed_index is None else forward[:failed_index + 1] + expected_tail
    for index, name in enumerate(expected):
        assert _message_names(sent) == expected[:index + 1]
        _respond(client, name + "_RESPONSE", index not in (failed_index, rollback_failure))
    assert _message_names(sent) == expected
    assert completed == [transition]
    assert transition.done
    assert transition.succeeded == (failed_index is None)
    assert client.config is (new if failed_index is None else old)
    assert client.state == getattr(LLRPReaderState, "STATE_" + final_state)
    assert len(client._pending_requests) == 0
    assert not any(client._deferreds.values())


@pytest.mark.parametrize("state", ["CONNECTED", "PAUSED"])
@pytest.mark.parametrize("success", [False, True])
def test_non_inventory_transition_does_not_invent_reader_restore(state, success):
    old = LLRPReaderConfig({"keepalive_interval": 1000})
    new = LLRPReaderConfig({"keepalive_interval": 2000})
    sent, completed = [], []
    client = LLRPClient(old, transport_tx_write=sent.append)
    client.state = getattr(LLRPReaderState, "STATE_" + state)
    transition = client.apply_config(new, onCompletion=completed.append)
    expected = []
    if state == "PAUSED":
        expected.append("DELETE_ROSPEC")
        _respond(client, "DELETE_ROSPEC_RESPONSE")
    expected.append("SET_READER_CONFIG")
    _respond(client, "SET_READER_CONFIG_RESPONSE", success)
    assert _message_names(sent) == expected
    assert completed == [transition]
    assert transition.succeeded == success
    assert client.config is (new if success else old)
    assert client.state == getattr(LLRPReaderState, "STATE_" + state)


@pytest.mark.parametrize("shutdown_error,close_error", [(False, False), (True, False), (False, True)])
def test_hard_disconnect_cancels_old_session_even_if_socket_cleanup_fails(shutdown_error, close_error):
    calls = []

    class Socket:
        def shutdown(self, _how):
            calls.append("shutdown")
            if shutdown_error:
                raise OSError("shutdown failed")

        def close(self):
            calls.append("close")
            if close_error:
                raise OSError("close failed")

    reader = LLRPReaderClient("reader", config=LLRPReaderConfig())
    reader._socket = Socket()
    callback = lambda *_: calls.append("stale callback")
    reader.llrp._pending_requests.register("TEST_RESPONSE", 10, callback=callback)
    reader.llrp._deferreds["TEST_RESPONSE"].append(callback)
    reader.llrp._suppress_set_config_post_actions = True
    reader.llrp._inventory_rospec_added = True
    reader.partial_data = b"partial"
    reader.expected_bytes = 100
    if close_error:
        with pytest.raises(OSError, match="close failed"):
            reader.hard_disconnect()
    else:
        reader.hard_disconnect()
    reader.hard_disconnect()
    assert calls == ["shutdown", "close"]
    assert reader._socket is None
    assert reader.partial_data == b"" and reader.expected_bytes == 0
    assert not reader.llrp._suppress_set_config_post_actions
    assert not reader.llrp._inventory_rospec_added
    assert not reader.llrp._deferreds
    assert len(reader.llrp._pending_requests) == 0
    assert reader.llrp.state == LLRPReaderState.STATE_DISCONNECTED


def test_disconnect_notification_remains_once_after_repeated_eof_and_cleanup():
    reader = LLRPReaderClient("reader", config=LLRPReaderConfig())
    calls = []
    reader.add_disconnected_callback(lambda _: calls.append("disconnected"))
    reader.disconnect_requested.set()
    assert reader.on_lost_connection()
    assert reader.on_lost_connection()
    reader.disconnect()
    assert calls == ["disconnected"]


@pytest.mark.parametrize("mode", ["graceful", "timeout", "disconnect_error", "hard_error", "already_stopped"])
def test_fastapi_lifespan_shutdown(mode, monkeypatch):
    pytest.importorskip("fastapi")
    path = Path(__file__).resolve().parents[1] / "examples/fastapi/app.py"
    spec = importlib.util.spec_from_file_location("audit_fastapi_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []

    class Reader:
        def __init__(self, *_):
            self.alive = mode != "already_stopped"
            self._socket = object()

        def add_tag_report_callback(self, _callback):
            pass

        def add_event_callback(self, _callback):
            pass

        def connect(self):
            calls.append("connect")

        def is_alive(self):
            return self.alive

        def disconnect(self, timeout):
            calls.append(("disconnect", timeout))
            if mode == "disconnect_error":
                raise OSError("disconnect failed")
            if mode in ("graceful", "already_stopped"):
                self.alive = False
                self._socket = None

        def hard_disconnect(self):
            calls.append("hard_disconnect")
            if mode == "hard_error":
                raise OSError("hard disconnect failed")
            self.alive = False
            self._socket = None

        def join(self, timeout):
            calls.append(("join", timeout))

    monkeypatch.setattr(module, "LLRPReaderClient", Reader)

    async def exercise():
        async with module.lifespan(module.app):
            await asyncio.sleep(0)

    asyncio.run(exercise())
    expected = ["connect", ("disconnect", 2)]
    if mode not in ("graceful", "already_stopped"):
        expected += ["hard_disconnect", ("join", 1)]
    assert calls == expected


def test_logging_reinitialization_preserves_application_handlers(tmp_path):
    root = logging.getLogger()
    old_handlers, old_level = root.handlers[:], root.level
    app_stream, diagnostics = io.StringIO(), io.StringIO()
    application_handler = logging.StreamHandler(app_stream)
    root.addHandler(application_handler)
    try:
        logfile = tmp_path / "diagnostics.log"
        init_logging(stream=diagnostics, logfile=logfile)
        first_owned = [h for h in root.handlers if getattr(h, "_sllurp_owned", False)]
        init_logging(stream=diagnostics, logfile=logfile)
        assert application_handler in root.handlers
        assert not application_handler._closed
        assert all(h._closed for h in first_owned)
        logging.getLogger("audit.embedding").info("exactly once")
        assert diagnostics.getvalue().count("exactly once") == 1
        assert app_stream.getvalue().count("exactly once") == 1
        assert logfile.read_text().count("exactly once") == 1
    finally:
        for handler in root.handlers[:]:
            if handler not in old_handlers:
                root.removeHandler(handler)
                handler.close()
        root.handlers[:] = old_handlers
        root.setLevel(old_level)
