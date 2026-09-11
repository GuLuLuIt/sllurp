from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LLRP = ROOT / "sllurp" / "llrp.py"
TESTS = ROOT / "tests" / "test_core_state_bugs.py"
WORKFLOW = ROOT / ".github" / "workflows" / "apply-core-state-fixes.yml"
SELF = Path(__file__)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, got {count}")
    return text


text = LLRP.read_text()

text = replace_once(
    text,
    "import select\nimport ssl\n",
    "import math\nimport select\nimport ssl\n",
    "math import",
)

text = replace_once(
    text,
    '        self.reader_config = {}\n        self.reader_mode = None\n',
    '        self.reader_config = {}\n        self.reader_config_summary = {}\n        self.reader_mode = None\n',
    "reader config summary state",
)

text = replace_once(
    text,
    '        self.disconnecting = False\n        self.dedup_backend_active = "disabled"\n',
    '        self.disconnecting = False\n        self.dedup_backend_active = "disabled"\n        self._pause_resume_timer = None\n        self._pause_resume_generation = 0\n',
    "pause timer state",
)

text = regex_once(
    text,
    r'''    def update_config\(self, new_config\):\n        """Update LLRPClient's config\n\n        Not completely safe, to be used with caution\.\n        """\n        self\.config = new_config\n\n    def _uses_impinj_extensions''',
    '''    def update_config(self, new_config):\n        """Replace client configuration while the protocol is disconnected.\n\n        Generic live replacement used to mutate ``self.config`` while cached\n        ROSpec and reader-side state were still active.  That could make the\n        Python object claim settings the reader had never accepted.  Targeted\n        live setters remain available; generic replacement is intentionally\n        atomic and disconnected-only until a transactional live-config API is\n        implemented.\n        """\n        validate = getattr(new_config, "validate_config", None)\n        if callable(validate):\n            validate()\n        if self.state != LLRPReaderState.STATE_DISCONNECTED:\n            raise ReaderConfigurationError(\n                "update_config requires a disconnected protocol session; "\n                "disconnect first or use a targeted live setter"\n            )\n        self.config = new_config\n        self.rospec = None\n        self.reader_config = {}\n        self.reader_config_summary = {}\n        self.dedup_backend_active = "disabled"\n\n    def _uses_impinj_extensions''',
    "LLRPClient update_config",
)

text = replace_once(
    text,
    '''    def setState(self, newstate, onCompletion=None):\n        assert newstate is not None\n        if is_general_debug_enabled():\n''',
    '''    def setState(self, newstate, onCompletion=None):\n        assert newstate is not None\n        if newstate == LLRPReaderState.STATE_DISCONNECTED:\n            self._cancel_pause_resume_timer()\n        if is_general_debug_enabled():\n''',
    "setState timer cancellation",
)

text = replace_once(
    text,
    '''    def parseReaderConfig(self, confdict):\n        """Parse a reader configuration dictionary and adjust instance settings."""\n        return\n''',
    '''    def parseReaderConfig(self, confdict):\n        """Normalize useful standard reader-side configuration.\n\n        ``reader_config`` remains the raw decoded GET_READER_CONFIG response for\n        backwards compatibility.  ``reader_config_summary`` is a stable,\n        vendor-neutral view of standard fields that were actually reported by\n        the reader.  Missing optional fields stay absent rather than being\n        invented.\n        """\n        if not isinstance(confdict, dict):\n            raise ReaderConfigurationError("reader configuration must be a dictionary")\n\n        def as_list(value):\n            if value is None:\n                return []\n            if isinstance(value, list):\n                return value\n            if isinstance(value, tuple):\n                return list(value)\n            return [value]\n\n        summary = {}\n\n        antenna_properties = {}\n        for item in as_list(confdict.get("AntennaProperties")):\n            if not isinstance(item, dict) or "AntennaID" not in item:\n                continue\n            antenna_id = item["AntennaID"]\n            antenna_properties[antenna_id] = {\n                "connected": item.get("AntennaConnected"),\n                "gain": item.get("AntennaGain"),\n            }\n        if antenna_properties:\n            summary["antenna_properties"] = antenna_properties\n\n        antenna_configurations = {}\n        for item in as_list(confdict.get("AntennaConfiguration")):\n            if not isinstance(item, dict) or "AntennaID" not in item:\n                continue\n            antenna_configurations[item["AntennaID"]] = dict(item)\n        if antenna_configurations:\n            summary["antenna_configurations"] = antenna_configurations\n\n        singular_fields = {\n            "KeepaliveSpec": "keepalive",\n            "ReaderEventNotificationSpec": "event_notifications",\n            "AccessReportSpec": "access_report",\n            "EventsAndReports": "events_and_reports",\n        }\n        for source, target in singular_fields.items():\n            if source in confdict:\n                value = confdict[source]\n                summary[target] = dict(value) if isinstance(value, dict) else value\n\n        repeated_fields = {\n            "GPIPortCurrentState": "gpi_ports",\n            "GPOWriteData": "gpo_ports",\n        }\n        for source, target in repeated_fields.items():\n            if source in confdict:\n                summary[target] = [\n                    dict(item) if isinstance(item, dict) else item\n                    for item in as_list(confdict[source])\n                ]\n\n        self.reader_config_summary = summary\n        return summary\n''',
    "parseReaderConfig",
)

pause_resume = '''    def _cancel_pause_resume_timer(self):\n        """Cancel a scheduled timed-pause resume and invalidate stale callbacks."""\n        self._pause_resume_generation += 1\n        timer = self._pause_resume_timer\n        self._pause_resume_timer = None\n        if timer is not None:\n            timer.cancel()\n\n    def _schedule_pause_resume(self, duration_seconds, force_regen_rospec=False):\n        self._cancel_pause_resume_timer()\n        generation = self._pause_resume_generation\n\n        def timed_resume():\n            if generation != self._pause_resume_generation:\n                return\n            self._pause_resume_timer = None\n            if self.state != LLRPReaderState.STATE_PAUSED:\n                return\n            self._resume_inventory(force_regen_rospec=force_regen_rospec)\n\n        timer = Timer(duration_seconds, timed_resume)\n        timer.daemon = True\n        self._pause_resume_timer = timer\n        timer.start()\n\n    def pause(self, duration_seconds=0, force=False, force_regen_rospec=False):\n        """Pause inventory, optionally resuming automatically after a duration."""\n        logger.debugfast("pause(%s)", duration_seconds)\n        if (\n            isinstance(duration_seconds, bool)\n            or not isinstance(duration_seconds, (int, float))\n            or not math.isfinite(duration_seconds)\n            or duration_seconds < 0\n        ):\n            raise ReaderConfigurationError(\n                "pause duration_seconds must be a finite non-negative number"\n            )\n        duration_seconds = float(duration_seconds)\n\n        if self.state != LLRPReaderState.STATE_INVENTORYING:\n            if not force:\n                logger.info(\n                    "ignoring pause(); not inventorying (state==%s)",\n                    LLRPReaderState.getStateName(self.state),\n                )\n                return None\n            logger.info("forcing pause()")\n\n        self._cancel_pause_resume_timer()\n        if duration_seconds:\n            logger.info("pausing for %s seconds", duration_seconds)\n\n        rospec = self.getROSpec(force_new=force_regen_rospec)\n        self.sendMessage({"DISABLE_ROSPEC": {"ROSpecID": rospec["ROSpecID"]}})\n        self.setState(LLRPReaderState.STATE_PAUSING)\n\n        def disable_rospec_pause_cb(state, is_success, *args):\n            if is_success:\n                self.setState(LLRPReaderState.STATE_PAUSED)\n                if duration_seconds > 0:\n                    self._schedule_pause_resume(\n                        duration_seconds,\n                        force_regen_rospec=force_regen_rospec,\n                    )\n            else:\n                self.complain(None, "pause() failed")\n\n        self._deferreds["DISABLE_ROSPEC_RESPONSE"].append(disable_rospec_pause_cb)\n        return disable_rospec_pause_cb\n\n    def _resume_inventory(self, force_regen_rospec=False):\n        logger.debugfast("resuming, force_regen_rospec=%s", force_regen_rospec)\n\n        if force_regen_rospec:\n            self.rospec = self.getROSpec(force_new=True)\n\n        if self.state in (\n            LLRPReaderState.STATE_CONNECTED,\n            LLRPReaderState.STATE_DISCONNECTED,\n        ):\n            logger.debugfast("will startInventory()")\n            self.startInventory()\n            return\n\n        if self.state != LLRPReaderState.STATE_PAUSED:\n            logger.debugfast(\n                "cannot resume() if not paused (state=%s); ignoring",\n                LLRPReaderState.getStateName(self.state),\n            )\n            return None\n\n        logger.info("resuming")\n\n        def enable_rospec_resume_cb(state, is_success, *args):\n            if is_success:\n                self.setState(LLRPReaderState.STATE_INVENTORYING)\n            else:\n                self.complain(None, "resume() failed")\n\n        self.send_ENABLE_ROSPEC(None, self.rospec, onCompletion=enable_rospec_resume_cb)\n\n    def resume(self, force_regen_rospec=False):\n        """Resume inventory and cancel any outstanding timed-pause resume."""\n        self._cancel_pause_resume_timer()\n        return self._resume_inventory(force_regen_rospec=force_regen_rospec)\n\n'''
text = regex_once(
    text,
    r"    def pause\(self, duration_seconds=0, force=False, force_regen_rospec=False\):.*?(?=    def sendMessage\(self, msg_dict\):)",
    pause_resume,
    "pause/resume implementation",
)

legacy_block = '''        if "Channelist" in self.frequencies and "ChannelList" not in self.frequencies:\n            self.frequencies["ChannelList"] = self.frequencies.pop("Channelist")\n'''
if text.count(legacy_block) != 1:
    raise RuntimeError("legacy frequency block not found exactly once")
text = text.replace(legacy_block, "", 1)
text = replace_once(
    text,
    '''        channel_list = self.frequencies.get("ChannelList", [])\n''',
    '''        if "Channelist" in self.frequencies:\n            if "ChannelList" not in self.frequencies:\n                self.frequencies["ChannelList"] = self.frequencies["Channelist"]\n            self.frequencies.pop("Channelist", None)\n\n        channel_list = self.frequencies.get("ChannelList", [])\n''',
    "legacy frequency normalization ordering",
)

text = replace_once(
    text,
    '''        if port is None:\n            port = (\n''',
    '''        self._port_explicit = port is not None\n        if port is None:\n            port = (\n''',
    "explicit port tracking",
)

text = regex_once(
    text,
    r'''    def update_config\(self, new_config\):\n        """Update ReaderClient's config\n\n        Not completely safe, to be used with caution\.\n        """\n        self\.config = new_config\n        self\._deduplicator = \(.*?        if self\.llrp:\n            self\.llrp\.update_config\(new_config\)\n\n    def get_peername''',
    '''    def update_config(self, new_config):\n        """Atomically replace configuration while fully disconnected.\n\n        Generic live replacement is rejected before any local state changes,\n        preventing desired config, cached ROSpec and reader-side state from\n        silently diverging.\n        """\n        validate = getattr(new_config, "validate_config", None)\n        if callable(validate):\n            validate()\n        if (\n            self._socket is not None\n            or self.is_alive()\n            or (self.llrp and self.llrp.state != LLRPReaderState.STATE_DISCONNECTED)\n        ):\n            raise ReaderConfigurationError(\n                "update_config requires a fully disconnected reader; "\n                "disconnect first or use a targeted live setter"\n            )\n\n        new_deduplicator = (\n            TagReportDeduplicator(\n                window_seconds=new_config.dedup_seconds,\n                max_entries=new_config.dedup_max_entries,\n            )\n            if new_config.dedup_seconds is not None\n            else None\n        )\n        if self.llrp:\n            self.llrp.update_config(new_config)\n\n        self.config = new_config\n        self._deduplicator = new_deduplicator\n        if not self._port_explicit:\n            self._port = (\n                LLRP_SECURE_PORT if new_config.tls_enabled else LLRP_DEFAULT_PORT\n            )\n\n    def get_peername''',
    "LLRPReaderClient update_config",
)

text = replace_once(
    text,
    '''        if self.llrp:\n            self.llrp._deferreds.clear()\n            self.llrp.rospec = None\n''',
    '''        if self.llrp:\n            self.llrp._cancel_pause_resume_timer()\n            self.llrp._deferreds.clear()\n            self.llrp.rospec = None\n''',
    "reset session timer cancellation",
)

text = replace_once(
    text,
    '''    def hard_disconnect(self):\n        """Stop the recv worker, close sockets, and reset frame state."""\n        self._cancel_duration_timer()\n''',
    '''    def hard_disconnect(self):\n        """Stop the recv worker, close sockets, and reset frame state."""\n        self._cancel_duration_timer()\n        if self.llrp:\n            self.llrp._cancel_pause_resume_timer()\n''',
    "hard disconnect pause timer cancellation",
)

for old, new, label in [
    ("for fn in self._disconnected_callbacks:", "for fn in tuple(self._disconnected_callbacks):", "disconnected callbacks snapshot"),
    ("for fn in self._llrp_state_callbacks[newstate]:", "for fn in tuple(self._llrp_state_callbacks[newstate]):", "state callbacks snapshot"),
    ("for fn in self._llrp_message_callbacks[msgName]:", "for fn in tuple(self._llrp_message_callbacks[msgName]):", "message callbacks snapshot"),
    ("for fn in self._tag_report_callbacks:", "for fn in tuple(self._tag_report_callbacks):", "tag callbacks snapshot"),
    ("for fn in self._event_notification_callbacks:", "for fn in tuple(self._event_notification_callbacks):", "event callbacks snapshot"),
]:
    text = replace_once(text, old, new, label)

LLRP.write_text(text)

TESTS.write_text(r'''import time
from types import SimpleNamespace

import pytest

from sllurp.llrp import (
    LLRPClient,
    LLRPReaderClient,
    LLRPReaderConfig,
    LLRPReaderState,
    LLRP_DEFAULT_PORT,
    LLRP_SECURE_PORT,
)
from sllurp.llrp_errors import ReaderConfigurationError


def test_legacy_channelist_is_normalized_before_validation():
    config = LLRPReaderConfig(
        {
            "frequencies": {
                "HopTableId": 1,
                "Channelist": [1],
                "Automatic": False,
            }
        }
    )
    assert config.frequencies["ChannelList"] == [1]
    assert "Channelist" not in config.frequencies


def test_modern_channel_list_wins_if_both_keys_are_present():
    config = LLRPReaderConfig(
        {
            "frequencies": {
                "HopTableId": 1,
                "ChannelList": [2],
                "Channelist": [1],
                "Automatic": False,
            }
        }
    )
    assert config.frequencies["ChannelList"] == [2]
    assert "Channelist" not in config.frequencies


def test_llrp_update_config_rejects_live_replacement_without_mutation():
    old = LLRPReaderConfig()
    new = LLRPReaderConfig({"session": 1})
    client = LLRPClient(old, transport_tx_write=lambda _: None)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}

    with pytest.raises(ReaderConfigurationError, match="disconnected"):
        client.update_config(new)

    assert client.config is old
    assert client.rospec == {"ROSpecID": 1}


def test_reader_update_config_is_atomic_and_updates_implicit_secure_port():
    old = LLRPReaderConfig()
    reader = LLRPReaderClient("reader.example", config=old)
    assert reader.get_peername()[1] == LLRP_DEFAULT_PORT

    reader.llrp.state = LLRPReaderState.STATE_INVENTORYING
    live = LLRPReaderConfig({"session": 1})
    with pytest.raises(ReaderConfigurationError, match="disconnected"):
        reader.update_config(live)
    assert reader.config is old
    assert reader.llrp.config is old

    reader.llrp.state = LLRPReaderState.STATE_DISCONNECTED
    secure = LLRPReaderConfig({"tls_enabled": True})
    reader.update_config(secure)
    assert reader.config is secure
    assert reader.llrp.config is secure
    assert reader.get_peername()[1] == LLRP_SECURE_PORT


def test_explicit_port_is_not_changed_by_disconnected_config_update():
    reader = LLRPReaderClient("reader.example", port=6000, config=LLRPReaderConfig())
    reader.update_config(LLRPReaderConfig({"tls_enabled": True}))
    assert reader.get_peername()[1] == 6000


def test_timed_pause_schedules_exactly_one_resume_after_pause_ack():
    sent = []
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=sent.append)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}

    pause_cb = client.pause(0.03)
    assert client.state == LLRPReaderState.STATE_PAUSING
    assert client._pause_resume_timer is None

    pause_cb(client.state, True)
    assert client.state == LLRPReaderState.STATE_PAUSED
    assert client._pause_resume_timer is not None

    time.sleep(0.08)
    assert client.state == LLRPReaderState.STATE_SENT_ENABLE_ROSPEC
    assert len(client._deferreds["ENABLE_ROSPEC_RESPONSE"]) == 1

    client._cancel_pause_resume_timer()


def test_disconnect_state_invalidates_stale_timed_pause_resume():
    sent = []
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=sent.append)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}

    pause_cb = client.pause(0.03)
    pause_cb(client.state, True)
    assert client.state == LLRPReaderState.STATE_PAUSED

    client.setState(LLRPReaderState.STATE_DISCONNECTED)
    time.sleep(0.08)
    assert client.state == LLRPReaderState.STATE_DISCONNECTED
    assert not client._deferreds["ENABLE_ROSPEC_RESPONSE"]


def test_pause_rejects_invalid_duration_values():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda _: None)
    client.state = LLRPReaderState.STATE_INVENTORYING
    client.rospec = {"ROSpecID": 1}
    for value in (-1, float("inf"), float("nan"), True, "1"):
        with pytest.raises(ReaderConfigurationError):
            client.pause(value)


def test_callback_dispatch_uses_stable_snapshot_when_callback_removes_itself():
    reader = LLRPReaderClient("reader.example", config=LLRPReaderConfig())
    calls = []

    def first(rdr, tags):
        calls.append("first")
        rdr.remove_tag_report_callback(first)

    def second(rdr, tags):
        calls.append("second")

    reader.add_tag_report_callback(first)
    reader.add_tag_report_callback(second)
    msg = SimpleNamespace(msgdict={"RO_ACCESS_REPORT": {"TagReportData": [{"EPC": b"x"}]}})

    reader._on_llrp_tag_report(None, msg)
    assert calls == ["first", "second"]

    calls.clear()
    reader._on_llrp_tag_report(None, msg)
    assert calls == ["second"]


def test_callback_added_during_dispatch_runs_on_next_dispatch_only():
    reader = LLRPReaderClient("reader.example", config=LLRPReaderConfig())
    calls = []

    def later(rdr, tags):
        calls.append("later")

    def first(rdr, tags):
        calls.append("first")
        rdr.add_tag_report_callback(later)

    reader.add_tag_report_callback(first)
    msg = SimpleNamespace(msgdict={"RO_ACCESS_REPORT": {"TagReportData": []}})
    reader._on_llrp_tag_report(None, msg)
    assert calls == ["first"]

    reader._on_llrp_tag_report(None, msg)
    assert calls == ["first", "first", "later"]


def test_parse_reader_config_builds_normalized_summary_without_destroying_raw_data():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda _: None)
    raw = {
        "AntennaProperties": [
            {"AntennaID": 1, "AntennaConnected": True, "AntennaGain": 25},
            {"AntennaID": 2, "AntennaConnected": False, "AntennaGain": 0},
        ],
        "AntennaConfiguration": {"AntennaID": 1, "RFTransmitter": {"TransmitPower": 10}},
        "KeepaliveSpec": {"KeepaliveTriggerType": 1, "TimeInterval": 1000},
        "GPIPortCurrentState": {"GPIPortNum": 1, "State": True},
    }
    client.reader_config = raw

    summary = client.parseReaderConfig(raw)

    assert client.reader_config is raw
    assert summary is client.reader_config_summary
    assert summary["antenna_properties"][1] == {"connected": True, "gain": 25}
    assert summary["antenna_properties"][2]["connected"] is False
    assert summary["antenna_configurations"][1]["RFTransmitter"]["TransmitPower"] == 10
    assert summary["keepalive"]["TimeInterval"] == 1000
    assert summary["gpi_ports"] == [{"GPIPortNum": 1, "State": True}]


def test_parse_reader_config_rejects_non_mapping():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda _: None)
    with pytest.raises(ReaderConfigurationError):
        client.parseReaderConfig([])
''')

# Remove the one-shot machinery from the commit produced by the workflow.
if WORKFLOW.exists():
    WORKFLOW.unlink()
SELF.unlink()
