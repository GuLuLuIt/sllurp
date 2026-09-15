"""Low Level Reader Protocol implementation in pure Python."""

from .version import __version__ as sllurp_version

# Apply small, regression-tested corrections to the legacy protocol registry
# before callers import public LLRP modules or llrp_proto directly.
from . import _protocol_fixes as _protocol_fixes  # noqa: F401,E402

# Apply narrowly scoped client/runtime corrections after the protocol registry
# is fixed. These remain isolated so they can be folded into llrp.py later.
from . import _runtime_fixes as _runtime_fixes  # noqa: F401,E402

__all__ = (
    "llrp",
    "llrp_decoder",
    "llrp_errors",
    "llrp_proto",
    "secure",
    "readers",
    "reader_management",
    "zebra_management",
    "impinj_management",
    "intermec_management",
    "dedup",
    "util",
    "log",
)

__version__ = sllurp_version
