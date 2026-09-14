from sllurp.llrp_proto import Param_struct


def test_impinj_frequency_capabilities_uses_uint_stride():
    decoder = Param_struct["ImpinjFrequencyCapabilities"]["decode"]
    payload = (
        b"\x00\x02"
        + (902750).to_bytes(4, "big")
        + (903250).to_bytes(4, "big")
    )

    decoded, _ = decoder(payload)

    assert decoded["NumFrequencies"] == 2
    assert decoded["FrequencyList"] == [902750, 903250]
