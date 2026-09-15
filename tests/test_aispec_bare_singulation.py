import struct

from sllurp import llrp_proto as proto


def test_decode_aispec_event_accepts_bare_singulation_body():
    fixed = struct.pack("!BIH", 0, 1, 1)
    bare_details = struct.pack("!HH", 1, 1)
    payload = fixed + bare_details
    raw = struct.pack("!HH", proto.Param_struct["AISpecEvent"]["type"], 4 + len(payload))
    raw += payload

    name, decoded, consumed = proto.decode_param(raw)

    assert name == "AISpecEvent"
    assert consumed == len(raw)
    assert decoded["C1G2SingulationDetails"] == {
        "NumCollisionSlots": 1,
        "NumEmptySlots": 1,
    }
