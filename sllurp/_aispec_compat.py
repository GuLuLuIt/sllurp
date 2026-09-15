"""Narrow AISpecEvent compatibility handling.

Some readers have been observed during hardware testing to expose the optional
C1G2SingulationDetails payload in legacy forms. Keep those exceptions local to
AISpecEvent rather than weakening generic LLRP parameter validation.
"""

from . import llrp_proto as _p


def decode_aispec_event(data, name=None):
    """Decode AISpecEvent including standard and observed legacy details."""
    _p.logger.debugfast("decode_AISpecEvent")

    fixed_size = _p.ubyte_uint_ushort_size
    if len(data) < fixed_size:
        raise _p.LLRPError("Truncated AISpecEvent")

    _event_type, rospec_id, spec_index = _p.ubyte_uint_ushort_unpack(
        data[:fixed_size]
    )
    par = {
        "ROSpecID": rospec_id,
        "SpecIndex": spec_index,
        "EventType": "End_of_AISpec",
    }

    trailing = data[fixed_size:]
    if not trailing:
        return par, ""

    # Hardware testing exposed a four-byte body-only form with the TV header
    # omitted. AISpecEvent has only this fixed-size optional standard field, so
    # accepting it here does not relax generic parameter decoding.
    if len(trailing) == _p.ushort_ushort_size:
        collisions, empty = _p.ushort_ushort_unpack(trailing)
        par["C1G2SingulationDetails"] = {
            "NumCollisionSlots": collisions,
            "NumEmptySlots": empty,
        }
        return par, ""

    # A second observed form expands the TV type number (18) to a 16-bit value
    # before the same four-byte body. Restrict acceptance to that exact type.
    if len(trailing) == _p.ushort_ushort_ushort_size:
        legacy_type, collisions, empty = _p.ushort_ushort_ushort_unpack(trailing)
        if legacy_type == _p.Param_struct["C1G2SingulationDetails"]["type"]:
            par["C1G2SingulationDetails"] = {
                "NumCollisionSlots": collisions,
                "NumEmptySlots": empty,
            }
            return par, ""

    # Standard TV-encoded C1G2SingulationDetails, and any future valid optional
    # parameters, continue through the ordinary strict decoder.
    par, _ = _p.decode_all_parameters(trailing, "AISpecEvent", par)
    return par, ""


def install():
    """Install the compatibility decoder into the existing protocol registry."""
    _p.Param_struct["AISpecEvent"]["decode"] = decode_aispec_event


install()
