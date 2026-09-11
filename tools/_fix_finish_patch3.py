from pathlib import Path

root = Path(__file__).resolve().parents[1]

# Add a safe fallback for synthetic/legacy messages that omit an ID: only
# resolve by response type when exactly one request of that type is pending.
runtime = root / "sllurp" / "llrp_runtime.py"
rtext = runtime.read_text()
needle = '''    def cancel(self, response_name, message_id, remember_stale=True):
'''
insert = '''    def pop_response_type(self, response_name):
        """Pop the sole request of a response type, otherwise leave state untouched."""
        with self._lock:
            matches = [key for key in self._pending if key[0] == response_name]
            if len(matches) != 1:
                return None
            key = matches[0]
            pending = self._pending.pop(key)
            if pending.timer is not None:
                pending.timer.cancel()
                pending.timer = None
            self._remember_stale(key)
            return pending

'''
if insert not in rtext:
    if needle not in rtext:
        raise RuntimeError("runtime pop insertion anchor missing")
    rtext = rtext.replace(needle, insert + needle, 1)
runtime.write_text(rtext)

# Modify the generated llrp.py patch after the previous compatibility fixers.
patch = root / "tools" / "_finish_runtime_todos.py"
text = patch.read_text()

text = text.replace(
    '''        matched_pending = None
        if message_id is not None:
            matched_pending = self._pending_requests.pop(msgName, message_id)
''',
    '''        if message_id is not None:
            matched_pending = self._pending_requests.pop(msgName, message_id)
        else:
            matched_pending = self._pending_requests.pop_response_type(msgName)
''',
    1,
)

text = text.replace(
    '''            if existing_id is None:
                message_id = self._next_message_id()
                msg_dict[name]["ID"] = message_id
            else:
''',
    '''            if existing_id is None:
                reserved_id = getattr(self, "_reserved_message_id", None)
                message_id = (
                    self._next_message_id()
                    if reserved_id is None
                    else int(reserved_id)
                )
                msg_dict[name]["ID"] = message_id
            else:
''',
    1,
)

text = text.replace(
    '''            name = next(iter(msg_dict))
            message_id = self._next_message_id()
            msg_dict[name]["ID"] = message_id
            previous_state = self.state
''',
    '''            message_id = self._next_message_id()
            previous_state = self.state
''',
    1,
)
text = text.replace(
    '''            self._sending_registered_request = True
            try:
                self.sendMessage(msg_dict)
''',
    '''            self._sending_registered_request = True
            self._reserved_message_id = message_id
            try:
                self.sendMessage(msg_dict)
''',
    1,
)
text = text.replace(
    '''            finally:
                self._sending_registered_request = False
            return message_id
''',
    '''            finally:
                self._reserved_message_id = None
                self._sending_registered_request = False
            return message_id
''',
    1,
)
patch.write_text(text)

# Cover the ID-less fallback explicitly.
tests = root / "tests" / "test_llrp_runtime.py"
ttext = tests.read_text()
addition = '''\n\ndef test_pending_request_registry_type_fallback_requires_exactly_one():
    registry = PendingRequestRegistry()
    first = registry.register("R_RESPONSE", 1, callback="first")
    assert registry.pop_response_type("R_RESPONSE") is first

    registry.register("R_RESPONSE", 2, callback="second")
    registry.register("R_RESPONSE", 3, callback="third")
    assert registry.pop_response_type("R_RESPONSE") is None
    assert len(registry) == 2
'''
if "test_pending_request_registry_type_fallback_requires_exactly_one" not in ttext:
    tests.write_text(ttext + addition)

Path(__file__).unlink()
