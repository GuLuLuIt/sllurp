import inspect

import pytest

from sllurp.llrp import LLRPClient
from sllurp.llrp_proto import LLRPError, LLRPROSpec, Param_struct


def test_c1g2_access_parameter_field_metadata_is_not_concatenated():
    for name in ("C1G2Read", "C1G2Write", "C1G2BlockWrite"):
        fields = Param_struct[name]["fields"]
        assert "AccessPassword" in fields
        assert "MB" in fields
        assert "AccessPasswordMB" not in fields


def test_block_write_uses_its_own_encoder():
    assert Param_struct["C1G2BlockWrite"]["encode"].__name__ == "encode_C1G2BlockWrite"


def test_rospec_tag_filter_default_is_not_mutable():
    assert inspect.signature(LLRPROSpec).parameters["tag_filter_mask"].default is None


def test_reader_state_none_is_rejected_without_assert_dependency():
    client = object.__new__(LLRPClient)
    with pytest.raises(LLRPError, match="state cannot be None"):
        client.setState(None)
