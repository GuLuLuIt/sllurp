"""
Logging setup.
"""

import logging
import sys
import time

# Global
general_debug_enabled = False


class UTCFormatter(logging.Formatter):
    """Logging formatter that emits ISO-8601 UTC timestamps."""

    converter = time.gmtime

    def formatTime(self, record, datefmt=None):
        """Return ``record`` time as ISO-8601 UTC with milliseconds."""
        converted = self.converter(record.created)
        base = time.strftime(datefmt or "%Y-%m-%dT%H:%M:%S", converted)
        return f"{base}.{int(record.msecs):03d}Z"


def set_general_debug(debug=False):
    """Enable or disable high-rate protocol debug logging globally."""
    global general_debug_enabled
    general_debug_enabled = bool(debug)


def is_general_debug_enabled():
    """Return whether high-rate protocol debug logging is enabled."""
    return general_debug_enabled


def init_logging(debug=False, logfile=None, stream="stderr"):
    """Initialize logging with UTC timestamps on the requested diagnostic stream."""
    set_general_debug(debug)

    loglevel = logging.DEBUG if debug else logging.INFO
    logformat = "%(asctime)s %(name)s: %(levelname)s: %(message)s"
    formatter = UTCFormatter(logformat, datefmt="%Y-%m-%dT%H:%M:%S")

    if stream == "stderr":
        output_stream = sys.stderr
    elif stream == "stdout":
        output_stream = sys.stdout
    elif hasattr(stream, "write"):
        output_stream = stream
    else:
        raise ValueError("stream must be 'stderr', 'stdout', or a writable stream")

    stream_handler = logging.StreamHandler(output_stream)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(loglevel)

    root = logging.getLogger()
    root.setLevel(loglevel)

    # Replace only handlers installed here; embedding applications own theirs.
    previous_handlers = [
        handler for handler in root.handlers
        if getattr(handler, "_sllurp_owned", False)
    ]
    for handler in previous_handlers:
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            logging.getLogger(__name__).debug(
                "failed to close previous logging handler", exc_info=True
            )

    stream_handler._sllurp_owned = True
    root.addHandler(stream_handler)

    if logfile:
        fhandler = logging.FileHandler(logfile)
        fhandler.setFormatter(formatter)
        fhandler.setLevel(loglevel)
        fhandler._sllurp_owned = True
        root.addHandler(fhandler)


def debugfast(self, *args, **kwargs):
    """Logging debug function optimized for high-rate protocol paths."""
    if general_debug_enabled:
        self.debug(*args, **kwargs)


def get_logger(module_name):
    """Return a logger object providing the custom ``debugfast`` function."""
    logger_cls = logging.getLoggerClass()
    if getattr(logger_cls, "debugfast", None) is not debugfast:
        logger_cls.debugfast = debugfast
    return logging.getLogger(module_name)


class MaxLevelFilter(logging.Filter):
    """Let through messages with a level strictly below ``level``."""

    def __init__(self, level):
        super().__init__()
        self.level = level

    def filter(self, record):
        """Return whether ``record.levelno`` is strictly below the limit."""
        # "<" is intentional: logger.setLevel is inclusive.
        return record.levelno < self.level

