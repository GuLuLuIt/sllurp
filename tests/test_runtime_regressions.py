import threading
from types import SimpleNamespace

import pytest

from sllurp.llrp import LLRPClient, LLRPReaderClient, LLRPReaderConfig, LLRPReaderState
from sllurp.llrp_errors import ReaderConfigurationError


class Response:
    def __init__(self, name, message_id, success=True):
        self._name = name
        self.msgdict = {
            name: {
                "ID": message_id,
                "LLRPStatus": {
                    "StatusCode": "Success" if success else "Failure",
                    "ErrorDescription": "",
                },
            }
        }
        self._success = success

    def getName(self):
        return self._name

    def isSuccess(self):
        return self._success


def test_request_is_registered_before_transport_can_reply():
    callback_calls = []
    holder = {}

    replied = []

    def write(data):
        client = holder["client"]
        if replied:
            return
        replied.append(True)
        request_id = client.last_msg_id
        client.handleMessage(Response("GET_READER_CONFIG_RESPONSE", request_id))

    client = LLRPClient(
        LLRPReaderConfig({"start_inventory": False, "reset_on_connect": False}),
        transport_tx_write=write,
    )
    holder["client"] = client
    client.state = LLRPReaderState.STATE_CONNECTED

    client.send_GET_READER_CONFIG(
        onCompletion=lambda state, success: callback_calls.append((state, success))
    )

    assert callback_calls and callback_calls[0][1] is True
    assert not client._pending_requests.has_response_type("GET_READER_CONFIG_RESPONSE")


def test_wrong_message_id_does_not_consume_pending_request():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_CONNECTED
    calls = []
    client.send_GET_READER_CONFIG(lambda state, success: calls.append(success))
    expected_id = client.last_msg_id

    client.handleMessage(Response("GET_READER_CONFIG_RESPONSE", expected_id + 1))

    assert calls == []
    assert client._pending_requests.contains("GET_READER_CONFIG_RESPONSE", expected_id)


def test_duplicate_response_is_ignored_after_completion():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_CONNECTED
    calls = []
    client.send_GET_READER_CONFIG(lambda state, success: calls.append(success))
    message_id = client.last_msg_id
    client.handleMessage(Response("GET_READER_CONFIG_RESPONSE", message_id))
    client.handleMessage(Response("GET_READER_CONFIG_RESPONSE", message_id))
    assert calls == [True]


def test_request_timeout_cleans_pending_callback():
    cfg = LLRPReaderConfig({"request_timeout": 0.02})
    client = LLRPClient(cfg, transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_CONNECTED
    calls = []
    callback_called = threading.Event()

    def on_complete(state, success):
        calls.append(success)
        callback_called.set()

    client.send_GET_READER_CONFIG(on_complete)

    # Synchronize with the timer callback instead of assuming the operating
    # system will schedule its thread within a fixed sleep interval.  Busy CI
    # hosts, especially macOS runners, may deliver the timeout correctly but
    # resume the test thread before the callback has finished.
    assert callback_called.wait(timeout=1.0)
    assert calls == [False]
    assert not client._pending_requests.has_response_type("GET_READER_CONFIG_RESPONSE")


def test_transport_failure_rolls_back_state_and_pending_registration():
    def fail_write(data):
        raise OSError("boom")

    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=fail_write)
    client.state = LLRPReaderState.STATE_CONNECTED
    with pytest.raises(OSError):
        client.send_GET_READER_CONFIG(lambda *args: None)
    assert client.state == LLRPReaderState.STATE_CONNECTED
    assert not client._pending_requests.has_response_type("GET_READER_CONFIG_RESPONSE")


def test_client_only_live_config_change_needs_no_reader_traffic():
    sent = []
    old = LLRPReaderConfig({"reconnect_delay": 60.0})
    new = LLRPReaderConfig({"reconnect_delay": 1.0})
    client = LLRPClient(old, transport_tx_write=sent.append)
    client.state = LLRPReaderState.STATE_CONNECTED
    transition = client.apply_config(new)
    assert transition.succeeded
    assert client.config is new
    assert sent == []


def test_reconnect_required_live_change_is_rejected_without_mutation():
    old = LLRPReaderConfig()
    new = LLRPReaderConfig({"tls_enabled": True})
    client = LLRPClient(old, transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_CONNECTED
    with pytest.raises(ReaderConfigurationError, match="requires reconnect"):
        client.apply_config(new)
    assert client.config is old


def test_config_state_separates_desired_generated_and_applied():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda data: None)
    client.reader_mode = None
    client.getROSpec(force_new=True)
    state = client.get_config_state()
    assert state["desired"] is not None
    assert state["generated_rospec"] is not None
    assert state["applied"] is None
    client.setState(LLRPReaderState.STATE_INVENTORYING)
    assert client.get_config_state()["applied"] is not None


def test_callback_registry_stress_add_remove_during_dispatch():
    reader = LLRPReaderClient("reader.example", config=LLRPReaderConfig())
    stop = threading.Event()
    errors = []
    calls = []

    def stable(rdr, tags):
        calls.append(1)

    def churn(rdr, tags):
        return None

    reader.add_tag_report_callback(stable)
    msg = SimpleNamespace(msgdict={"RO_ACCESS_REPORT": {"TagReportData": []}})

    def mutate():
        try:
            while not stop.is_set():
                reader.add_tag_report_callback(churn)
                reader.remove_tag_report_callback(churn)
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=mutate)
    thread.start()
    try:
        for _ in range(1000):
            reader._on_llrp_tag_report(None, msg)
    finally:
        stop.set()
        thread.join(2)

    assert errors == []
    assert len(calls) == 1000


@pytest.mark.parametrize(
    "state,response_name,send_method",
    [
        (
            LLRPReaderState.STATE_SENT_SET_CONFIG,
            "SET_READER_CONFIG_RESPONSE",
            lambda client, cb: client.send_SET_READER_CONFIG(cb),
        ),
        (
            LLRPReaderState.STATE_SENT_ADD_ROSPEC,
            "ADD_ROSPEC_RESPONSE",
            lambda client, cb: client.send_ADD_ROSPEC({"ROSpecID": 1}, cb),
        ),
        (
            LLRPReaderState.STATE_SENT_ENABLE_ROSPEC,
            "ENABLE_ROSPEC_RESPONSE",
            lambda client, cb: client.send_ENABLE_ROSPEC(None, {"ROSpecID": 1}, cb),
        ),
        (
            LLRPReaderState.STATE_SENT_START_ROSPEC,
            "START_ROSPEC_RESPONSE",
            lambda client, cb: client.send_START_ROSPEC(None, {"ROSpecID": 1}, cb),
        ),
    ],
)
def test_negative_responses_finish_pending_callbacks(monkeypatch, state, response_name, send_method):
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_CONNECTED
    # This test isolates pending-response semantics; protocol serialization is
    # independently covered by the existing message/ROSpec tests.
    monkeypatch.setattr(client, "sendMessage", lambda msg: None)
    calls = []
    send_method(client, lambda current_state, success: calls.append(success))
    message_id = client.last_msg_id
    assert client.state == state

    response = Response(response_name, message_id, success=False)
    try:
        client.handleMessage(response)
    except ReaderConfigurationError:
        pass

    assert calls == [False]
    assert not client._pending_requests.has_response_type(response_name)


def test_live_rospec_config_transition_successfully_restarts_inventory(monkeypatch):
    old = LLRPReaderConfig({"session": 2})
    new = LLRPReaderConfig({"session": 1})
    client = LLRPClient(old, transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}
    monkeypatch.setattr(client, "stopPolitely", lambda onCompletion=None, disconnect=False: onCompletion(client.state, True))

    def start(force_regen_rospec=False, onCompletion=None):
        client.setState(LLRPReaderState.STATE_INVENTORYING)
        if onCompletion:
            onCompletion(client.state, True)

    monkeypatch.setattr(client, "startInventory", start)
    transition = client.apply_config(new)
    assert transition.done and transition.succeeded
    assert client.config is new
    assert client.state == LLRPReaderState.STATE_INVENTORYING


def test_reader_config_transition_failure_rolls_back_old_config(monkeypatch):
    old = LLRPReaderConfig({"keepalive_interval": 1000})
    new = LLRPReaderConfig({"keepalive_interval": 2000})
    client = LLRPClient(old, transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_CONNECTED
    monkeypatch.setattr(client, "send_SET_READER_CONFIG", lambda onCompletion: onCompletion(client.state, False))
    transition = client.apply_config(new)
    assert transition.done and not transition.succeeded
    assert client.config is old
    assert client.desired_config is old
    assert client.state == LLRPReaderState.STATE_CONNECTED


def test_inventory_restart_failure_rolls_back_and_restores_inventory(monkeypatch):
    old = LLRPReaderConfig({"session": 2})
    new = LLRPReaderConfig({"session": 1})
    client = LLRPClient(old, transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}
    monkeypatch.setattr(client, "stopPolitely", lambda onCompletion=None, disconnect=False: onCompletion(client.state, True))
    outcomes = [False, True]

    def start(force_regen_rospec=False, onCompletion=None):
        success = outcomes.pop(0)
        if success:
            client.setState(LLRPReaderState.STATE_INVENTORYING)
        if onCompletion:
            onCompletion(client.state, success)

    monkeypatch.setattr(client, "startInventory", start)
    transition = client.apply_config(new)
    assert transition.done and not transition.succeeded
    assert client.config is old
    assert client.desired_config is old
    assert client.state == LLRPReaderState.STATE_INVENTORYING
    assert outcomes == []


def test_inventory_restart_and_rollback_failure_enters_disconnected_state(monkeypatch):
    old = LLRPReaderConfig({"session": 2})
    new = LLRPReaderConfig({"session": 1})
    client = LLRPClient(old, transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}
    monkeypatch.setattr(client, "stopPolitely", lambda onCompletion=None, disconnect=False: onCompletion(client.state, True))

    def start(force_regen_rospec=False, onCompletion=None):
        if onCompletion:
            onCompletion(client.state, False)

    monkeypatch.setattr(client, "startInventory", start)
    transition = client.apply_config(new)
    assert transition.done and not transition.succeeded
    assert client.config is old
    assert client.state == LLRPReaderState.STATE_DISCONNECTED
