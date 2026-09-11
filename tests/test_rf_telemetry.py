import pytest

from sllurp.llrp import LLRPClient, LLRPReaderConfig, _build_tag_deduplicator
from sllurp.llrp_errors import ReaderConfigurationError
from sllurp.llrp_proto import LLRPError
from sllurp.llrp_runtime import ACTION_ROSPEC, build_config_transition_plan


def test_rf_telemetry_is_off_by_default():
    config = LLRPReaderConfig()
    assert config.rf_telemetry_mode == "off"
    assert config.tag_content_selector["EnableAntennaID"] is False
    assert config.zebra_tag_content_selector is None


def test_standard_rf_telemetry_enables_llrp_measurements():
    config = LLRPReaderConfig({"rf_telemetry_mode": "standard"})
    selector = config.tag_content_selector
    for field in (
        "EnableROSpecID",
        "EnableAntennaID",
        "EnableChannelIndex",
        "EnablePeakRSSI",
        "EnableFirstSeenTimestamp",
        "EnableLastSeenTimestamp",
        "EnableTagSeenCount",
    ):
        assert selector[field] is True
    assert config.zebra_tag_content_selector is None


def test_zebra_rf_telemetry_requests_phase_and_physical_port():
    config = LLRPReaderConfig({"rf_telemetry_mode": "zebra"})
    assert config.zebra_tag_content_selector["EnablePhase"] is True
    assert config.zebra_tag_content_selector["EnableAntennaPhysicalPortConfig"] is True
    rospec = LLRPClient(config).getROSpec()
    report = rospec["ROReportSpec"]
    assert report["TagReportContentSelector"]["EnableAntennaID"] is True
    assert report["MotoTagReportContentSelector"]["EnablePhase"] is True


def test_rf_telemetry_memory_dedup_is_antenna_aware():
    config = LLRPReaderConfig(
        {"rf_telemetry_mode": "standard", "dedup_seconds": 10}
    )
    dedup = _build_tag_deduplicator(config)
    assert dedup.include_antenna is True
    reports = [
        {"EPC-96": b"same", "AntennaID": 1},
        {"EPC-96": b"same", "AntennaID": 2},
        {"EPC-96": b"same", "AntennaID": 1},
    ]
    assert dedup.filter(reports) == reports[:2]


def test_rf_telemetry_auto_dedup_uses_memory_even_when_hardware_available():
    config = LLRPReaderConfig(
        {"rf_telemetry_mode": "zebra", "dedup_seconds": 10, "dedup_backend": "auto"}
    )
    client = LLRPClient(config)
    backend = client._select_dedup_backend(
        {"MotoAdvancedCapabilities": {"CanSupportPeriodicTagReports": True}}
    )
    assert backend == "memory"


def test_rf_telemetry_rejects_reader_wide_hardware_dedup():
    config = LLRPReaderConfig(
        {"rf_telemetry_mode": "zebra", "dedup_seconds": 10, "dedup_backend": "hardware"}
    )
    client = LLRPClient(config)
    with pytest.raises(ReaderConfigurationError):
        client._select_dedup_backend(
  {"MotoAdvancedCapabilities": {"CanSupportPeriodicTagReports": True}}
        )


def test_rf_telemetry_live_change_is_rospec_scoped():
    old = LLRPReaderConfig()
    new = LLRPReaderConfig({"rf_telemetry_mode": "zebra"})
    plan = build_config_transition_plan(old, new)
    actions = {change.field: change.action for change in plan.changes}
    assert actions["rf_telemetry_mode"] == ACTION_ROSPEC
    assert plan.requires_rospec_restart
    assert not plan.requires_reconnect


@pytest.mark.parametrize("value", [True, None, "unknown"])
def test_invalid_rf_telemetry_mode_is_rejected(value):
    with pytest.raises(LLRPError):
        LLRPReaderConfig({"rf_telemetry_mode": value})
