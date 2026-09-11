import time

from sllurp.llrp import LLRPReaderConfig
from sllurp.llrp_runtime import (
    ACTION_CLIENT,
    ACTION_READER_CONFIG,
    ACTION_RECONNECT,
    ACTION_ROSPEC,
    PendingRequestRegistry,
    build_config_transition_plan,
)


def test_config_transition_plan_classifies_changes():
    old = LLRPReaderConfig()
    new = LLRPReaderConfig(
        {
            "session": 1,
            "keepalive_interval": 1234,
            "reconnect_delay": 1.0,
            "tls_enabled": True,
        }
    )
    plan = build_config_transition_plan(old, new)
    by_field = {change.field: change.action for change in plan.changes}

    assert by_field["session"] == ACTION_ROSPEC
    assert by_field["keepalive_interval"] == ACTION_READER_CONFIG
    assert by_field["reconnect_delay"] == ACTION_CLIENT
    assert by_field["tls_enabled"] == ACTION_RECONNECT
    assert plan.requires_rospec_restart
    assert plan.requires_reader_config_write
    assert plan.requires_reconnect


def test_config_transition_plan_noop_and_client_only():
    old = LLRPReaderConfig()
    assert build_config_transition_plan(old, LLRPReaderConfig()).is_noop

    new = LLRPReaderConfig({"reconnect_delay": 2.0})
    plan = build_config_transition_plan(old, new)
    assert plan.client_only


def test_pending_request_registry_matches_exact_message_id():
    registry = PendingRequestRegistry()
    callback = object()
    registry.register("GET_READER_CONFIG_RESPONSE", 10, callback)

    assert registry.has_response_type("GET_READER_CONFIG_RESPONSE")
    assert registry.contains("GET_READER_CONFIG_RESPONSE", 10)
    assert not registry.contains("GET_READER_CONFIG_RESPONSE", 11)

    pending = registry.pop("GET_READER_CONFIG_RESPONSE", 10)
    assert pending.callback is callback
    assert len(registry) == 0
    assert registry.is_stale("GET_READER_CONFIG_RESPONSE", 10)


def test_pending_request_registry_timeout_is_deterministic():
    registry = PendingRequestRegistry()
    expired = []
    registry.register(
        "ADD_ROSPEC_RESPONSE",
        22,
        callback="cb",
        timeout=0.02,
        on_timeout=expired.append,
    )

    time.sleep(0.08)
    assert len(registry) == 0
    assert [pending.message_id for pending in expired] == [22]
    assert registry.is_stale("ADD_ROSPEC_RESPONSE", 22)


def test_pending_request_registry_cancel_all_cancels_timers():
    registry = PendingRequestRegistry()
    expired = []
    registry.register("A_RESPONSE", 1, timeout=0.03, on_timeout=expired.append)
    registry.register("B_RESPONSE", 2, timeout=0.03, on_timeout=expired.append)

    cancelled = registry.cancel_all()
    time.sleep(0.07)

    assert len(cancelled) == 2
    assert expired == []
    assert len(registry) == 0


def test_pending_request_registry_type_fallback_requires_exactly_one():
    registry = PendingRequestRegistry()
    first = registry.register("R_RESPONSE", 1, callback="first")
    assert registry.pop_response_type("R_RESPONSE") is first

    registry.register("R_RESPONSE", 2, callback="second")
    registry.register("R_RESPONSE", 3, callback="third")
    assert registry.pop_response_type("R_RESPONSE") is None
    assert len(registry) == 2
