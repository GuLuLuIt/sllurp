from sllurp.llrp import LLRPClient, LLRPReaderConfig


def test_stale_exact_response_does_not_fall_back_to_deferred_callback():
    client = LLRPClient(LLRPReaderConfig())
    calls = []

    def callback(_state, is_success):
        calls.append(is_success)

    response_name = "ADD_ROSPEC_RESPONSE"
    message_id = 77
    client._deferreds[response_name].append(callback)
    client._pending_requests.register(response_name, message_id, callback=callback)

    pending = client._pending_requests.cancel(
        response_name, message_id, remember_stale=True
    )
    assert pending is not None

    # Model the response arriving after the timer has atomically removed and
    # marked the request stale but before the timeout callback runs.
    assert client.processDeferreds(
        response_name, True, message_id=message_id
    ) is False
    assert calls == []

    client._on_request_timeout(pending)
    assert calls == [False]
