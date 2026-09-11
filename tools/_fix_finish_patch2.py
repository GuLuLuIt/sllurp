from pathlib import Path

path = Path(__file__).with_name("_finish_runtime_todos.py")
text = path.read_text()

# Preserve @staticmethod when stopAllROSpecs is replaced up to the next def.
needle = '''replace_method(
    "stopAllROSpecs",
    '''
idx = text.index(needle)
end = text.index('''

replace_method(
    "pause",
''', idx)
block = text[idx:end]
block = block.replace(
    '''        return None
''',
    '''        return None

    @staticmethod
''',
    1,
)
text = text[:idx] + block + text[end:]

# Keep the existing two-argument processDeferreds call seam. The current
# response ID is captured on the client at handleMessage entry instead.
text = text.replace(
    'self.processDeferreds(msgName, lmsg.isSuccess(), message_id)',
    'self.processDeferreds(msgName, lmsg.isSuccess())',
)
text = text.replace(
    '''        message_id = self._message_id(lmsg)\n\n        if message_id is not None and msgName.endswith("_RESPONSE"):\n''',
    '''        message_id = self._message_id(lmsg)\n        self._response_message_id = message_id\n\n        if message_id is not None and msgName.endswith("_RESPONSE"):\n''',
    1,
)
text = text.replace(
    '''    def processDeferreds(self, msgName, isSuccess, message_id=None):
        deferreds = self._deferreds[msgName]
''',
    '''    def processDeferreds(self, msgName, isSuccess, message_id=None):
        if message_id is None:
            message_id = getattr(self, "_response_message_id", None)
        deferreds = self._deferreds[msgName]
''',
    1,
)

# Replace the request-send core so tracked state is registered before transport
# write while still routing through sendMessage(), an established test seam.
start = text.index('replace_method(\n    "sendMessage",')
end = text.index('\n\n# Reader config request timeout option.', start)
replacement = r"""replace_method(
    "sendMessage",
    '''    def _next_message_id(self):
        if self.last_msg_id < LLRP_MSG_ID_MAX:
            self.last_msg_id += 1
        else:
            self.last_msg_id = 1
        return self.last_msg_id

    def _prepare_message(self, msg_dict):
        sent_ids = []
        for name in msg_dict:
            existing_id = msg_dict[name].get("ID")
            if existing_id is None:
                message_id = self._next_message_id()
                msg_dict[name]["ID"] = message_id
            else:
                message_id = int(existing_id)
                self.last_msg_id = message_id
            sent_ids.append((name, message_id))
        llrp_msg = LLRPMessage(msgdict=msg_dict)
        assert llrp_msg.msgbytes, "LLRPMessage is empty"
        return llrp_msg.msgbytes, sent_ids

    def _send_request(self, msg_dict, response_name, onCompletion=None, new_state=None):
        # Register exact pending state before transport write, then send.
        with self._request_lock:
            if self._pending_requests.has_response_type(response_name) or self._deferreds.get(response_name):
                raise ReaderConfigurationError(
                    f"cannot send request: {response_name} is already pending"
                )
            name = next(iter(msg_dict))
            message_id = self._next_message_id()
            msg_dict[name]["ID"] = message_id
            previous_state = self.state
            if onCompletion is not None:
                self._deferreds[response_name].append(onCompletion)
            timeout = getattr(self.config, "request_timeout", None)
            self._pending_requests.register(
                response_name,
                message_id,
                onCompletion,
                timeout=timeout,
                on_timeout=self._on_request_timeout,
            )
            if new_state is not None:
                self.setState(new_state)
            self._sending_registered_request = True
            try:
                self.sendMessage(msg_dict)
            except Exception:
                self._pending_requests.cancel(response_name, message_id, remember_stale=False)
                if onCompletion in self._deferreds.get(response_name, []):
                    self._deferreds[response_name].remove(onCompletion)
                if not self._deferreds.get(response_name):
                    self._deferreds.pop(response_name, None)
                if new_state is not None and self.state == new_state:
                    self.setState(previous_state)
                raise
            finally:
                self._sending_registered_request = False
            return message_id

    def sendMessage(self, msg_dict):
        # Serialize and send one or more LLRP messages.
        with self._request_lock:
            if not getattr(self, "_sending_registered_request", False):
                for name in msg_dict:
                    response_name = (
                        "IMPINJ_ENABLE_EXTENSIONS_RESPONSE"
                        if name == "IMPINJ_ENABLE_EXTENSIONS"
                        else f"{name}_RESPONSE"
                    )
                    if self._deferreds.get(response_name) or self._pending_requests.has_response_type(response_name):
                        raise ReaderConfigurationError(
                            f"cannot send {name}: {response_name} is already pending"
                        )
            msgbytes, sent_ids = self._prepare_message(msg_dict)
            self.transport_tx_write(msgbytes)
            return sent_ids
''',
)
"""
text = text[:start] + replacement + text[end:]

# Only the tracked first write gets an immediate response in this race test.
text = text.replace(
    '''    def write(data):
        client = holder["client"]
        request_id = client.last_msg_id
        client.handleMessage(Response("GET_READER_CONFIG_RESPONSE", request_id))
''',
    '''    replied = []

    def write(data):
        client = holder["client"]
        if replied:
            return
        replied.append(True)
        request_id = client.last_msg_id
        client.handleMessage(Response("GET_READER_CONFIG_RESPONSE", request_id))
''',
    1,
)

# No incomplete RF-mode fixture is needed to verify generated-state snapshots.
text = text.replace(
    '''    client.reader_mode = {"ModeIdentifier": 1}
    client.getROSpec(force_new=True)
''',
    '''    client.reader_mode = None
    client.getROSpec(force_new=True)
''',
    1,
)

path.write_text(text)
Path(__file__).unlink()
