from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "apply_core_state_fixes.py"

text = SCRIPT.read_text()

old = '''        self.reader_config_summary = summary\\n        return summary\\n'''
new = '''        self.reader_config_summary = summary\\n        return None\\n'''
if text.count(old) != 1:
    raise RuntimeError(f"parse return patch expected 1 match, got {text.count(old)}")
text = text.replace(old, new, 1)

old_test = '''    summary = client.parseReaderConfig(raw)\n\n    assert client.reader_config is raw\n    assert summary is client.reader_config_summary\n    assert summary["antenna_properties"][1] == {"connected": True, "gain": 25}\n    assert summary["antenna_properties"][2]["connected"] is False\n    assert summary["antenna_configurations"][1]["RFTransmitter"]["TransmitPower"] == 10\n    assert summary["keepalive"]["TimeInterval"] == 1000\n    assert summary["gpi_ports"] == [{"GPIPortNum": 1, "State": True}]\n'''
new_test = '''    assert client.parseReaderConfig(raw) is None\n\n    summary = client.reader_config_summary\n    assert client.reader_config is raw\n    assert summary["antenna_properties"][1] == {"connected": True, "gain": 25}\n    assert summary["antenna_properties"][2]["connected"] is False\n    assert summary["antenna_configurations"][1]["RFTransmitter"]["TransmitPower"] == 10\n    assert summary["keepalive"]["TimeInterval"] == 1000\n    assert summary["gpi_ports"] == [{"GPIPortNum": 1, "State": True}]\n'''
if text.count(old_test) != 1:
    raise RuntimeError(f"new parse test patch expected 1 match, got {text.count(old_test)}")
text = text.replace(old_test, new_test, 1)

marker = '''LLRP.write_text(text)\n\nTESTS.write_text'''
insert = '''LLRP.write_text(text)\n\n# Update the historical test that asserted timed pause was intentionally broken.\nOBJECT_TESTS = ROOT / "tests" / "test_llrp_objects.py"\nobject_tests = OBJECT_TESTS.read_text()\nobsolete = ''' + '"""' + '''    with pytest.raises(ReaderConfigurationError, match="not yet"):\n        client.pause(duration_seconds=1)\n\n''' + '"""' + '''\nif object_tests.count(obsolete) != 1:\n    raise RuntimeError(\n        f"obsolete timed-pause assertion expected 1 match, got {object_tests.count(obsolete)}"\n    )\nOBJECT_TESTS.write_text(object_tests.replace(obsolete, "", 1))\n\nTESTS.write_text'''
if text.count(marker) != 1:
    raise RuntimeError(f"test patch insertion expected 1 match, got {text.count(marker)}")
text = text.replace(marker, insert, 1)

cleanup = '''SELF.unlink()\n'''
cleanup_new = '''SELF.unlink()\nPREP = ROOT / "tools" / "prepare_core_state_fixes_v2.py"\nif PREP.exists():\n    PREP.unlink()\n'''
if text.count(cleanup) != 1:
    raise RuntimeError(f"cleanup patch expected 1 match, got {text.count(cleanup)}")
text = text.replace(cleanup, cleanup_new, 1)

SCRIPT.write_text(text)
