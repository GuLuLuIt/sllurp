__all__ = [
    # Exceptions
    "LLRPError",
    "LLRPResponseError",
    "ReaderConfigurationError",
]


class LLRPError(Exception):
    """Base exception for LLRP encoding, decoding, and protocol failures.

    The library raises this exception when an LLRP value is invalid, a frame
    cannot be decoded, or a reader response violates the expected protocol
    contract.  Network and TLS failures may still surface as their native
    :mod:`socket` or :mod:`ssl` exceptions.
    """


class LLRPResponseError(LLRPError):
    """Raised when a reader returns a syntactically valid failure response.

    This distinguishes a negative ``LLRPStatus`` from malformed protocol data
    and transport failures.  The exception message contains the status detail
    supplied by the reader when it is available.
    """


class ReaderConfigurationError(LLRPError):
    """Raised when a requested reader/client configuration is unsafe to apply.

    Typical causes include changing reconnect-only fields on a live session,
    issuing a second request while the same response type is pending, or
    starting a transport that is already connected.
    """

