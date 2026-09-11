import struct

import pytest

from sllurp.llrp import LLRPClient, LLRPReaderConfig
from sllurp.llrp_proto import (
    LLRPError,
    LLRPROSpec,
    Param_struct,
    decode_MotoTagPhase,
    decode_param,
    encode_param,
)
from sllurp.llrp_runtime import ACTION_ROSPEC, build_config_transition_plan


def _zebra_selector(**overrides):
    selector = {
        "EnableZoneID": False,
        "EnableZoneName": False,
        "EnableAntennaPhysicalPortConfig": False,
        "EnablePhase": True,
        "EnableGPS": False,
        "EnableMLTReport": False,
    }
    selector.update(overrides)
    return selector


def test_zebra_phase_parameter_decodes_to_degrees():
    phase, remainder = decode_MotoTagPhase(struct.pack("!h", 0x4000))
    assert remainder == ""
    assert phase == pytest.approx(90.0)


def test_zebra_report_selector_custom_parameter_round_trip():
    selector = _zebra_selector(EnableGPS=True)
    encoded = encode_param("MotoTagReportContentSelector", selector)
    name, decoded, length = decode_param(encoded)
    assert length == len(encoded)
    assert name == "MotoTagReportContentSelector"
    assert decoded == selector
    assert Param_struct[name]["subtype"] == 708


def test_rospec_can_request_zebra_phase_reports():
    selector = _zebra_selector()
    rospec = LLRPROSpec(reader_mode=None, rospecid=1, zebra_tag_content_selector=selector)
    assert rospec["ROReportSpec"]["MotoTagReportContentSelector"] == selector


def test_reader_config_passes_zebra_selector_into_rospec():
    selector = _zebra_selector()
    config = LLRPReaderConfig({"zebra_tag_content_selector": selector})
    client = LLRPClient(config)
    assert client.getROSpec()["ROReportSpec"]["MotoTagReportContentSelector"] == selector


def test_zebra_selector_is_a_rospec_live_transition():
    old = LLRPReaderConfig()
    new = LLRPReaderConfig({"zebra_tag_content_selector": _zebra_selector()})
    plan = build_config_transition_plan(old, new)
    changes = {change.field: change.action for change in plan.changes}
    assert changes["zebra_tag_content_selector"] == ACTION_ROSPEC
    assert plan.requires_rospec_restart
    assert not plan.requires_reconnect


@pytest.mark.parametrize(
    "selector",
    [{"EnablePhase": 1}, {"EnableNotARealField": True}, ["EnablePhase"]],
)
def test_invalid_zebra_report_selector_is_rejected(selector):
    with pytest.raises(LLRPError):
        LLRPReaderConfig({"zebra_tag_content_selector": selector})


def test_power_table_accepts_zero_indexed_reader_entries():
    table = LLRPClient.parsePowerTable(
        {
            "TransmitPowerLevelTableEntry": [
                {"Index": 0, "TransmitPowerValue": 1000},
                {"Index": 1, "TransmitPowerValue": 2000},
            ]
        }
    )
    assert table == [10.0, 20.0]


def test_power_table_accepts_sparse_reader_indexes():
    table = LLRPClient.parsePowerTable(
        {
            "TransmitPowerLevelTableEntry": [
                {"Index": 1, "TransmitPowerValue": 1000},
                {"Index": 3, "TransmitPowerValue": 3000},
            ]
        }
    )
    assert table == [0, 10.0, 0, 30.0]


def test_zero_index_power_can_be_selected_by_dbm_without_becoming_max():
    config = LLRPReaderConfig({"tx_power_dbm": {1: 10.0}})
    client = LLRPClient(config)
    client.tx_power_table = [10.0, 20.0]
    client.tx_power_indices = {0, 1}
    client.setTxPowerDbm({1: 10.0})
    assert client.config.tx_power[1] == 0
    assert client.get_tx_power({1: 0})[1] == (1, 20.0)
    assert client.get_tx_power({1: 0}, zero_is_max=False)[1] == (0, 10.0)
