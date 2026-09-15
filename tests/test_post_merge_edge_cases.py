import struct

import pytest

from sllurp import llrp_proto
from sllurp.llrp import LLRPClient, LLRPReaderClient, LLRPReaderConfig


def test_zero_reconnect_retries_cannot_return_without_connection(monkeypatch):
    config = LLRPReaderConfig({"reconnect": True, "reconnect_retries": 0})
    reader = LLRPReaderClient("reader.invalid", config=config)
    notifications = []
    reader.add_disconnected_callback(notifications.append)

    def fail_connect():
        raise OSError("offline")

    monkeypatch.setattr(reader, "_connect_socket", fail_connect)

    with pytest.raises(ConnectionError, match="reconnection ended"):
        reader.connect(start_main_loop=False)

    assert reader._socket is None
    assert not reader.is_alive()
    assert notifications == [reader]


def test_stale_exact_response_does_not_create_empty_deferred_bucket():
    client = LLRPClient(LLRPReaderConfig(), transport_tx_write=lambda _data: None)
    client._pending_requests.register("TEST_RESPONSE", 7)
    client._pending_requests.cancel("TEST_RESPONSE", 7, remember_stale=True)

    assert client.processDeferreds("TEST_RESPONSE", True, message_id=7) is False
    assert "TEST_RESPONSE" not in client._deferreds


@pytest.mark.parametrize(
    "parameter_name, fixed_payload",
    [
        ("AISpecEvent", struct.pack("!BIH", 0, 7, 2)),
        ("ImpinjGGASentence", struct.pack("!H", 1) + b"x"),
        ("ImpinjRMCSentence", struct.pack("!H", 1) + b"x"),
    ],
)
def test_compat_decoders_preserve_registry_repeat_metadata(
    monkeypatch, parameter_name, fixed_payload
):
    calls = []

    def fake_decode_all(data, name=None, par_dict=None, n_fields=None):
        calls.append((data, name, n_fields))
        return par_dict, ""

    monkeypatch.setattr(llrp_proto, "decode_all_parameters", fake_decode_all)
    decoder = llrp_proto.Param_struct[parameter_name]["decode"]
    decoder(fixed_payload + b"trailing", parameter_name)

    assert "CustomParameter" in llrp_proto.Param_struct[parameter_name]["n_fields"]
    assert calls == [(b"trailing", parameter_name, None)]
