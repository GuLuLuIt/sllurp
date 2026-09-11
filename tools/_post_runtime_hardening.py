from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
llrp_path = ROOT / "sllurp" / "llrp.py"
text = llrp_path.read_text()


def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    text = text.replace(old, new, 1)


# Make the existing two-argument processDeferreds compatibility seam use the
# exact response ID captured at dispatch entry.
replace_once(
    '''        msgName = lmsg.getName()\n        message_id = self._message_id(lmsg)\n\n        if message_id is not None and msgName.endswith("_RESPONSE"):\n''',
    '''        msgName = lmsg.getName()\n        message_id = self._message_id(lmsg)\n        self._response_message_id = message_id\n\n        if message_id is not None and msgName.endswith("_RESPONSE"):\n''',
    "capture response message ID",
)

# A negative response is still a terminal response.  Finish/pop the pending
# operation before preserving the historical raise/return behavior.
failure_blocks = [
    (
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s enabling Impinj extensions: %s", status, err)\n                raise ReaderConfigurationError("ENABLE_IMPINJ_EXTENSIONS failed")\n''',
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s enabling Impinj extensions: %s", status, err)\n                self.processDeferreds(msgName, False)\n                raise ReaderConfigurationError("ENABLE_IMPINJ_EXTENSIONS failed")\n''',
        "Impinj failure",
    ),
    (
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s getting capabilities: %s", status, err)\n                raise ReaderConfigurationError("Error getting capabilities")\n''',
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s getting capabilities: %s", status, err)\n                self.processDeferreds(msgName, False)\n                raise ReaderConfigurationError("Error getting capabilities")\n''',
        "capability failure",
    ),
    (
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s getting reader config: %s", status, err)\n                raise ReaderConfigurationError("Error getting reader config")\n''',
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s getting reader config: %s", status, err)\n                self.processDeferreds(msgName, False)\n                raise ReaderConfigurationError("Error getting reader config")\n''',
        "get config failure",
    ),
    (
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s setting reader config: %s", status, err)\n                raise ReaderConfigurationError("Error setting reader config")\n''',
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s setting reader config: %s", status, err)\n                if self._suppress_set_config_post_actions:\n                    self._suppress_set_config_post_actions = False\n                self.processDeferreds(msgName, False)\n                raise ReaderConfigurationError("Error setting reader config")\n''',
        "set config failure",
    ),
    (
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s adding ROSpec: %s", status, err)\n                raise ReaderConfigurationError("Error adding ROSpec")\n''',
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s adding ROSpec: %s", status, err)\n                self.processDeferreds(msgName, False)\n                raise ReaderConfigurationError("Error adding ROSpec")\n''',
        "add rospec failure",
    ),
    (
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s enabling ROSpec: %s", status, err)\n                return\n''',
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.fatal("Error %s enabling ROSpec: %s", status, err)\n                self.processDeferreds(msgName, False)\n                return\n''',
        "enable rospec failure",
    ),
    (
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.error("START_ROSPEC failed with status %s: %s", status, err)\n                logger.fatal("Error %s starting ROSpec: %s", status, err)\n                return\n''',
        '''            if not lmsg.isSuccess():\n                status = lmsg.msgdict[msgName]["LLRPStatus"]["StatusCode"]\n                err = lmsg.msgdict[msgName]["LLRPStatus"]["ErrorDescription"]\n                logger.error("START_ROSPEC failed with status %s: %s", status, err)\n                logger.fatal("Error %s starting ROSpec: %s", status, err)\n                self.processDeferreds(msgName, False)\n                return\n''',
        "start rospec failure",
    ),
]
for old, new, label in failure_blocks:
    replace_once(old, new, label)

llrp_path.write_text(text)

# Add focused tests proving failed protocol responses terminate callbacks and
# live config transitions have deterministic success/rollback outcomes.
test_path = ROOT / "tests" / "test_runtime_todos.py"
test = test_path.read_text()
addition = r'''

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
def test_negative_responses_finish_pending_callbacks(state, response_name, send_method):
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda data: None)
    client.state = LLRPReaderState.STATE_CONNECTED
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

    monkeypatch.setattr(
        client,
        "stopPolitely",
        lambda onCompletion=None, disconnect=False: onCompletion(client.state, True),
    )

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

    monkeypatch.setattr(
        client,
        "send_SET_READER_CONFIG",
        lambda onCompletion: onCompletion(client.state, False),
    )

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

    monkeypatch.setattr(
        client,
        "stopPolitely",
        lambda onCompletion=None, disconnect=False: onCompletion(client.state, True),
    )
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

    monkeypatch.setattr(
        client,
        "stopPolitely",
        lambda onCompletion=None, disconnect=False: onCompletion(client.state, True),
    )

    def start(force_regen_rospec=False, onCompletion=None):
        if onCompletion:
            onCompletion(client.state, False)

    monkeypatch.setattr(client, "startInventory", start)

    transition = client.apply_config(new)
    assert transition.done and not transition.succeeded
    assert client.config is old
    assert client.state == LLRPReaderState.STATE_DISCONNECTED
'''
if "test_negative_responses_finish_pending_callbacks" not in test:
    test_path.write_text(test + addition)

# Clean up this one-shot patch machinery from the tested result.
Path(__file__).unlink()
workflow = ROOT / ".github" / "workflows" / "post-runtime-hardening.yml"
if workflow.exists():
    workflow.unlink()
