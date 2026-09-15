import struct

from sllurp import llrp_proto as proto
from sllurp.llrp import LLRPClient, LLRPReaderConfig


def _config():
    return LLRPReaderConfig({"start_inventory": False, "reset_on_connect": False})


class _InboundKeepalive:
    def __init__(self, message_id):
        self.msgdict = {"KEEPALIVE": {"ID": message_id}}

    def getName(self):
        return "KEEPALIVE"


def test_aispec_event_accepts_legacy_type_prefixed_singulation_body():
    fixed = struct.pack("!BIH", 0, 7, 3)
    legacy_details = struct.pack(
        "!HHH",
        proto.Param_struct["C1G2SingulationDetails"]["type"],
        2,
        5,
    )
    payload = fixed + legacy_details
    raw = struct.pack(
        "!HH",
        proto.Param_struct["AISpecEvent"]["type"],
        4 + len(payload),
    ) + payload

    name, decoded, consumed = proto.decode_param(raw)

    assert name == "AISpecEvent"
    assert consumed == len(raw)
    assert decoded["ROSpecID"] == 7
    assert decoded["SpecIndex"] == 3
    assert decoded["C1G2SingulationDetails"] == {
        "NumCollisionSlots": 2,
        "NumEmptySlots": 5,
    }


def test_keepalive_ack_reuses_reader_message_id_without_advancing_client_counter():
    sent = []
    client = LLRPClient(_config(), transport_tx_write=sent.append)
    client.last_msg_id = 41

    client.handleMessage(_InboundKeepalive(7001))

    assert len(sent) == 1
    msgtype, vendorid, subtype, version, header_len, full_length, message_id = (
        proto.msg_header_decode(sent[0])
    )
    assert msgtype == proto.Message_struct["KEEPALIVE_ACK"]["type"]
    assert vendorid == 0
    assert subtype == 0
    assert version == 1
    assert header_len == proto.msg_header_len
    assert full_length == len(sent[0])
    assert message_id == 7001
    assert client.last_msg_id == 41
