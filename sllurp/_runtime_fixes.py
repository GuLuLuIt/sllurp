"""Small regression-tested runtime corrections for LLRP client wrappers.

These patches are kept separate from the protocol registry corrections so
behavioral fixes can be removed cleanly once folded into the main implementation.
"""

from __future__ import annotations

from . import llrp as _l


_original_retry_connect = _l.LLRPReaderClient._retry_connect
_original_handle_message = _l.LLRPClient.handleMessage
_original_send_keepalive_ack = _l.LLRPClient.send_KEEPALIVE_ACK


def _process_deferreds(self, msgName, isSuccess, message_id=None):
    """Complete only the exact pending request when an exact response is stale."""
    if message_id is None:
        message_id = getattr(self, "_response_message_id", None)
    deferreds = self._deferreds.get(msgName, [])
    if message_id is not None:
        matched_pending = self._pending_requests.pop(msgName, message_id)
        if matched_pending is None and self._pending_requests.is_stale(
            msgName, message_id
        ):
            if not deferreds:
                self._deferreds.pop(msgName, None)
            return False
    else:
        matched_pending = self._pending_requests.pop_response_type(msgName)

    if matched_pending is not None:
        callbacks = []
        if matched_pending.callback is not None:
            callbacks.append(matched_pending.callback)
            if matched_pending.callback in deferreds:
                deferreds.remove(matched_pending.callback)
    else:
        callbacks = list(deferreds)
        deferreds.clear()

    if not callbacks and matched_pending is None:
        if not deferreds:
            self._deferreds.pop(msgName, None)
        return False
    if _l.is_general_debug_enabled():
        _l.logger.debugfast(
            "running %d Deferreds for %s; isSuccess=%s, message_id=%s",
            len(callbacks),
            msgName,
            isSuccess,
            message_id,
        )
    for deferred_cb in callbacks:
        deferred_cb(self.state, isSuccess)
    if not deferreds:
        self._deferreds.pop(msgName, None)
    return True


def _retry_connect(self):
    """Never let a failed reconnect path return without an active socket."""
    recovered = _original_retry_connect(self)
    if recovered:
        return True
    raise ConnectionError("reconnection ended before a retry attempt succeeded")


def _send_keepalive_ack(self, message_id=None):
    """Acknowledge KEEPALIVE with its reader-supplied MessageID when available."""
    if message_id is None:
        return _original_send_keepalive_ack(self)

    message_id = int(message_id)
    if not 0 <= message_id <= _l.LLRP_MSG_ID_MAX:
        raise _l.LLRPError(f"invalid KEEPALIVE MessageID: {message_id}")

    # KEEPALIVE_ACK is correlated to a reader-originated MessageID. Serialize it
    # directly instead of routing through sendMessage(), whose explicit-ID path
    # intentionally advances the client's outbound request counter.
    with self._request_lock:
        ack = _l.LLRPMessage(msgdict={"KEEPALIVE_ACK": {"ID": message_id}})
        self.transport_tx_write(ack.msgbytes)
    return [("KEEPALIVE_ACK", message_id)]


def _handle_message(self, lmsg):
    """Preserve the MessageID when acknowledging reader KEEPALIVE messages."""
    if lmsg.getName() == "KEEPALIVE":
        message_id = None
        try:
            message_id = lmsg.msgdict["KEEPALIVE"].get("ID")
        except (AttributeError, KeyError, TypeError):
            pass
        if message_id is None:
            self.send_KEEPALIVE_ACK()
        else:
            self.send_KEEPALIVE_ACK(message_id)
        return
    return _original_handle_message(self, lmsg)


def _start_access_spec(
    self, op_spec, target_spec=None, stop_after_count=0, access_spec_id=1
):
    """Accept the one- or two-target forms supported by low-level startAccess()."""
    if not isinstance(op_spec, _l.C1G2OpSpec):
        raise ValueError("op_spec needs to be a valid C1G2OpSpec object")

    if target_spec is not None and not isinstance(target_spec, _l.C1G2TargetTag):
        if not isinstance(target_spec, (list, tuple)):
            raise ValueError(
                "target_spec must be a C1G2TargetTag or a list/tuple of up to two targets"
            )
        if len(target_spec) > 2 or any(
            not isinstance(target, _l.C1G2TargetTag) for target in target_spec
        ):
            raise ValueError(
                "target_spec must contain at most two C1G2TargetTag objects"
            )
        target_spec = list(target_spec)

    if stop_after_count < 0:
        stop_after_count = 0

    self.llrp.startAccess(
        opSpec=op_spec,
        targetSpec=target_spec,
        stopAfterCount=stop_after_count,
        accessSpecID=access_spec_id,
    )


def apply() -> None:
    _l.LLRPClient.processDeferreds = _process_deferreds
    _l.LLRPClient.send_KEEPALIVE_ACK = _send_keepalive_ack
    _l.LLRPClient.handleMessage = _handle_message
    _l.LLRPReaderClient._retry_connect = _retry_connect
    _l.LLRPReaderClient.start_access_spec = _start_access_spec


apply()
