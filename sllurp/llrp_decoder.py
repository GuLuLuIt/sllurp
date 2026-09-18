"""Decode LLRP message and parameter headers.

The structures in this module follow GS1 LLRP 1.1 section 17, "LLRP Binary
Encoding": https://ref.gs1.org/standards/llrp/1.1.0/

All multi-byte integers are in network byte order.  Header decoders return
lengths in bytes and never consume or mutate their input buffer.
"""

from struct import Struct
from struct import error as StructError

from .log import get_logger

logger = get_logger(__name__)


# LLRP 1.1 section 17.1: the first word is Reserved(3), Version(3), Type(10),
# followed by the 32-bit total message length and 32-bit message ID. ``!`` is
# intentional: every multi-byte LLRP integer is transmitted in network order.
msg_header_struct = Struct("!HII")
msg_header_size = msg_header_struct.size
msg_header_pack = msg_header_struct.pack
msg_header_unpack = msg_header_struct.unpack

# A Custom Message appends a 32-bit vendor ID and 8-bit vendor subtype to the
# common header; the total-length field includes both extensions.
msg_vendor_subtype_struct = Struct("!IB")
msg_vendor_subtype_size = msg_vendor_subtype_struct.size
msg_vendor_subtype_pack = msg_vendor_subtype_struct.pack
msg_vendor_subtype_unpack = msg_vendor_subtype_struct.unpack

msg_header_custom_struct = Struct("!HIIIB")
msg_header_custom_pack = msg_header_custom_struct.pack
msg_header_custom_size = msg_header_custom_struct.size


# LLRP 1.1 section 17.2.1: a TV parameter has a leading one bit followed by a
# 7-bit type. Its body size is fixed by the parameter type.
tve_header_struct = Struct("!B")
tve_header_size = tve_header_struct.size
tve_header_unpack = tve_header_struct.unpack

# LLRP 1.1 section 17.2.1: TLV starts with Reserved(6), Type(10), then a
# 16-bit total parameter length. Custom TLV parameters append 32-bit vendor
# and subtype identifiers to this four-byte header.
tlv_par_header_struct = Struct("!HH")
tlv_par_header_size = tlv_par_header_struct.size
tlv_par_header_unpack = tlv_par_header_struct.unpack

par_vendor_subtype_struct = Struct("!II")
par_vendor_subtype_size = par_vendor_subtype_struct.size
par_vendor_subtype_unpack = par_vendor_subtype_struct.unpack


## LEGACY to REMOVE
# TLV param header: Type, Size
nontve_header_struct = Struct("!HH")
nontve_header_size = nontve_header_struct.size
nontve_header_unpack = nontve_header_struct.unpack


struct_short = Struct("!h")
struct_ushort = Struct("!H")
struct_ulonglong = Struct("!Q")
struct_schar = Struct("!b")
struct_uint = Struct("!I")
struct_2ushort = Struct("!HH")
struct_96bits = Struct("!12s")

TVE_PARAM_TYPE_MAX = 127
TYPE_CUSTOM = 1023
VENDOR_ID_IMPINJ = 25882
VENDOR_ID_MOTOROLA = 161
VENDOR_ID_SIRIT = 24831

TVE_PARAM_FORMATS = {
    # param type: (param name, struct format)
    1: ("AntennaID", struct_ushort),
    2: ("FirstSeenTimestampUTC", struct_ulonglong),
    3: ("FirstSeenTimestampUptime", struct_ulonglong),
    4: ("LastSeenTimestampUTC", struct_ulonglong),
    5: ("LastSeenTimestampUptime", struct_ulonglong),
    6: ("PeakRSSI", struct_schar),
    7: ("ChannelIndex", struct_ushort),
    8: ("TagSeenCount", struct_ushort),
    9: ("ROSpecID", struct_uint),
    10: ("InventoryParameterSpecID", struct_ushort),
    11: ("C1G2CRC", struct_ushort),
    12: ("C1G2PC", struct_ushort),
    13: ("EPC-96", struct_96bits),
    14: ("SpecIndex", struct_ushort),
    15: ("ClientRequestOpSpecResult", struct_ushort),
    16: ("AccessSpecID", struct_uint),
    17: ("OpSpecID", struct_ushort),
    18: ("C1G2SingulationDetails", struct_2ushort),
    19: ("C1G2XPCW1", struct_ushort),
    20: ("C1G2XPCW2", struct_ushort),
}


def msg_header_encode(msgtype, version, length, msgid, vendorid=0, subtype=0):
    """Encode an LLRP message header.

    Args:
        msgtype: Ten-bit LLRP message type. Values are masked to ten bits.
        version: Three-bit LLRP version value. Values are masked to three bits.
        length: Message-body length in bytes, excluding the generated header.
        msgid: Unsigned 32-bit request/correlation identifier.
        vendorid: Unsigned 32-bit vendor identifier for type 1023.
        subtype: Unsigned 8-bit vendor subtype for type 1023.

    Returns:
        The common or custom header as network-order :class:`bytes`. The
        encoded total length includes the header.

    Raises:
        struct.error: If an integer does not fit its on-wire field.

    Protocol:
        GS1 LLRP 1.1 section 17.1, "Messages".
    """
    ver = version & 0x07
    msgtype = msgtype & 0x03FF

    if msgtype == TYPE_CUSTOM:
        return msg_header_custom_pack(
            (ver << 10) | msgtype,
            msg_header_custom_size + length,
            msgid,
            vendorid,
            subtype,
        )
    else:
        return msg_header_pack((ver << 10) | msgtype, msg_header_size + length, msgid)


def msg_header_decode(data):
    """Decode and validate the header at the start of ``data``.

    Returns:
        ``(message_type, vendor_id, subtype, version, header_length,
        total_length, message_id)``. Lengths are bytes. Vendor values are zero
        for a non-custom message.

    Raises:
        ValueError: If the header is truncated, structurally invalid, or its
            declared total length is shorter than the applicable header.

    Protocol:
        GS1 LLRP 1.1 section 17.1, "Messages".
    """
    if len(data) < msg_header_size:
        raise ValueError(
            f"truncated LLRP message header: need {msg_header_size} bytes, got {len(data)}"
        )
    try:
        msgtype, length, msgid = msg_header_unpack(data[:msg_header_size])
    except StructError as exc:
        raise ValueError("invalid LLRP message header") from exc
    hdr_len = msg_header_size
    # & BITMASK(3)
    version = (msgtype >> 10) & 0x07
    # & BITMASK(10)
    msgtype = msgtype & 0x03FF
    if msgtype == TYPE_CUSTOM:
        custom_size = hdr_len + msg_vendor_subtype_size
        if len(data) < custom_size:
            raise ValueError(
                f"truncated custom LLRP header: need {custom_size} bytes, got {len(data)}"
            )
        try:
            vendorid, subtype = msg_vendor_subtype_unpack(
                data[hdr_len:custom_size]
            )
        except StructError as exc:
            raise ValueError("invalid custom LLRP message header") from exc
        hdr_len = custom_size
    else:
        vendorid = 0
        subtype = 0
    if length < hdr_len:
        raise ValueError(
            f"declared LLRP message length {length} is shorter than header {hdr_len}"
        )
    return msgtype, vendorid, subtype, version, hdr_len, length, msgid


def tlv_param_header_decode(data):
    """Decode a TLV parameter header without decoding its body.

    Returns:
        ``(parameter_type, vendor_id, subtype, header_length, total_length)``.
        Lengths are bytes. A truncated base/custom header returns
        ``(None, 0, 0, 0, 0)`` so the streaming caller can await more data.

    Raises:
        ValueError: If the declared total length is shorter than its header.

    Protocol:
        GS1 LLRP 1.1 section 17.2.1, "TLV and TV Encoding".
    """
    # Decode for normal param header (non-tve)
    if len(data) < tlv_par_header_size:
        return None, 0, 0, 0, 0

    partype, length = tlv_par_header_unpack(data[:tlv_par_header_size])
    hdr_len = tlv_par_header_size
    if length < hdr_len:
        raise ValueError(
            f"declared TLV parameter length {length} is shorter than header {hdr_len}"
        )
    # ie partype & BITMASK(10)
    partype = partype & 0x03FF
    if partype != TYPE_CUSTOM:
        return partype, 0, 0, hdr_len, length

    custom_header_size = hdr_len + par_vendor_subtype_size
    if len(data) < custom_header_size:
        return None, 0, 0, 0, 0

    if length < custom_header_size:
        raise ValueError(
            f"declared custom parameter length {length} is shorter than header {custom_header_size}"
        )
    vendorid, subtype = par_vendor_subtype_unpack(
        data[hdr_len : hdr_len + par_vendor_subtype_size]
    )
    hdr_len = custom_header_size
    return partype, vendorid, subtype, hdr_len, length


def tve_param_header_decode(data):
    """Generic byte decoding function for TVE parameters.

    Given an array of bytes, tries to interpret a TVE parameter from the
    beginning of the array.  Returns the decoded data and the number of bytes
    it read.

    Returns:
        ``(parameter_type, header_length, total_length)`` in bytes. Unknown,
        truncated, or non-TV input returns ``(None, 0, 0)``.

    Protocol:
        GS1 LLRP 1.1 section 17.2.1, "TLV and TV Encoding".
    """

    if len(data) < tve_header_size:
        return None, 0, 0

    # Most common case first
    # decode the TVE field's header (1 bit "reserved" + 7-bit type)
    tve_msgtype = tve_header_unpack(data[:tve_header_size])[0]

    if not tve_msgtype & 0b10000000:
        # Not a tve parameter
        return None, 0, 0

    tve_msgtype = tve_msgtype & 0x7F
    try:
        param_name, param_struct = TVE_PARAM_FORMATS[tve_msgtype]
        # logger.debugfast('found %s (type=%s)', param_name, tve_msgtype)
    except KeyError:
        return None, 0, 0

    # decode the body
    length = tve_header_size + param_struct.size

    return tve_msgtype, tve_header_size, length


def param_header_decode(data):
    """Decode either a TV or TLV parameter header at the start of ``data``.

    TV is tested first because its high marker bit distinguishes it from TLV.

    Returns:
        ``(parameter_type, vendor_id, subtype, header_length, total_length)``;
        lengths are bytes and vendor values are zero for standard parameters.

    Raises:
        ValueError: If a TLV header declares an impossible length.

    Protocol:
        GS1 LLRP 1.1 section 17.2.1, "TLV and TV Encoding".
    """
    vendorid = 0
    subtype = 0

    if len(data) < tve_header_size:
        # No parameter can be smaller than a tve_header
        return None, 0, 0, 0, 0

    # Check first for tve encoded parameters
    partype, hdr_len, full_length = tve_param_header_decode(data)
    if not partype:
        partype, vendorid, subtype, hdr_len, full_length = tlv_param_header_decode(data)

    return partype, vendorid, subtype, hdr_len, full_length

