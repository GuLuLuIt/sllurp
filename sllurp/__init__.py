"""Low Level Reader Protocol implemtnation in pure Python"""

from .version import __version__ as sllurp_version

# Apply the narrowly scoped AISpecEvent compatibility decoder after the
# protocol registry is built.  The shim keeps reader-specific legacy forms out
# of the generic parameter decoder.
from . import _aispec_compat as _aispec_compat  # noqa: F401,E402

__all__ = ("llrp", "llrp_decoder", "llrp_errors", "llrp_proto", "util", "log")

__version__ = sllurp_version
