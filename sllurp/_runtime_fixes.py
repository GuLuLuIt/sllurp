"""Regression-tested runtime/session corrections.

Keep these small fixes isolated from the large legacy ``llrp.py`` module.  They
are applied at package import after the protocol registry corrections.
"""

from __future__ import annotations

from copy import deepcopy

from . import llrp as _l


_original_get_config_state = _l.LLRPClient.get_config_state
_original_parse_capabilities = _l.LLRPClient.parseCapabilities
_original_on_disconnected = _l.LLRPReaderClient._on_disconnected
_original_on_lost_connection = _l.LLRPReaderClient.on_lost_connection


def _get_config_state(self):
    """Return a recursively detached runtime-state snapshot."""
    return deepcopy(_original_get_config_state(self))


def _parse_capabilities(self, capdict):
    """Never carry an explicitly selected RF mode into automatic-mode config."""
    self.reader_mode = None
    return _original_parse_capabilities(self, capdict)


def _on_disconnected(self):
    """Reset protocol/request state before notifying disconnected callbacks."""
    if self.llrp and self.llrp.state != _l.LLRPReaderState.STATE_DISCONNECTED:
        self.llrp.setState(_l.LLRPReaderState.STATE_DISCONNECTED)
    self._reset_protocol_session()
    return _original_on_disconnected(self)


def _on_lost_connection(self):
    """Fully clean up peer EOF even while a requested disconnect is pending."""
    if self.disconnect_requested.is_set():
        try:
            self.hard_disconnect()
        finally:
            self._on_disconnected()
        return True
    return _original_on_lost_connection(self)


def apply() -> None:
    _l.LLRPClient.get_config_state = _get_config_state
    _l.LLRPClient.parseCapabilities = _parse_capabilities
    _l.LLRPReaderClient._on_disconnected = _on_disconnected
    _l.LLRPReaderClient.on_lost_connection = _on_lost_connection


apply()
