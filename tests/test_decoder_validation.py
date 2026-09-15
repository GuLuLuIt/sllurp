import struct

import pytest

from sllurp.llrp_decoder import (
    TYPE_CUSTOM,
    msg_header_decode,
    msg_header_size,
    param_header_decode,
)


def test_truncated_message_header_raises_value_error():
    with pytest.raises(ValueError, match="truncated LLRP message header"):
        msg_header_decode(b"\x04")


def test_truncated_custom_message_header_raises_value_error():
    header = struct.pack("!HII", (1 << 10) | TYPE_CUSTOM, msg_header_size + 5, 1)
    with pytest.raises(ValueError, match="truncated custom LLRP header"):
        msg_header_decode(header)


def test_message_length_shorter_than_header_is_rejected():
    header = struct.pack("!HII", 1 << 10, msg_header_size - 1, 1)
    with pytest.raises(ValueError, match="shorter than header"):
        msg_header_decode(header)


def test_tlv_length_shorter_than_header_is_rejected():
    data = struct.pack("!HH", 1, 2)
    with pytest.raises(ValueError, match="TLV parameter length"):
        param_header_decode(data)


def test_custom_parameter_length_shorter_than_custom_header_is_rejected():
    data = struct.pack("!HHII", TYPE_CUSTOM, 4, 1, 1)
    with pytest.raises(ValueError, match="custom parameter length"):
        param_header_decode(data)


def test_truncated_tv_parameter_is_rejected():
    with pytest.raises(ValueError, match="truncated LLRP parameter"):
        param_header_decode(b"\x81")
