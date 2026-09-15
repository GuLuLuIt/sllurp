from sllurp import llrp_proto


def _decode_aispec(trailing=b""):
    fixed = llrp_proto.ubyte_uint_ushort_pack(0, 123, 4)
    decoder = llrp_proto.Param_struct["AISpecEvent"]["decode"]
    return decoder(fixed + trailing)[0]


def _assert_details(decoded, collisions, empty):
    assert decoded["ROSpecID"] == 123
    assert decoded["SpecIndex"] == 4
    assert decoded["EventType"] == "End_of_AISpec"
    assert decoded["C1G2SingulationDetails"] == {
        "NumCollisionSlots": collisions,
        "NumEmptySlots": empty,
    }


def test_aispec_event_without_optional_details():
    decoded = _decode_aispec()
    assert decoded == {
        "ROSpecID": 123,
        "SpecIndex": 4,
        "EventType": "End_of_AISpec",
    }


def test_aispec_event_decodes_standard_tv_singulation_details():
    param_type = llrp_proto.Param_struct["C1G2SingulationDetails"]["type"]
    trailing = llrp_proto.tve_header_pack(0x80 | param_type)
    trailing += llrp_proto.ushort_ushort_pack(7, 9)

    _assert_details(_decode_aispec(trailing), 7, 9)


def test_aispec_event_accepts_body_only_singulation_details():
    trailing = llrp_proto.ushort_ushort_pack(5, 8)
    _assert_details(_decode_aispec(trailing), 5, 8)


def test_aispec_event_accepts_16bit_type_prefixed_singulation_details():
    param_type = llrp_proto.Param_struct["C1G2SingulationDetails"]["type"]
    trailing = llrp_proto.ushort_ushort_ushort_pack(param_type, 6, 10)

    _assert_details(_decode_aispec(trailing), 6, 10)
