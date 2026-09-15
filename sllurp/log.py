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
        converted = self.converter(record.created)
        base = time.strftime(datefmt or "%Y-%m-%dT%H:%M:%S", converted)
        return f"{base}.{int(record.msecs):03d}Z"


def set_general_debug(debug=False):
    global general_debug_enabled
    general_debug_enabled = bool(debug)


def is_general_debug_enabled():
    return general_debug_enabled


def init_logging(debug=False, logfile=None, stream="stderr"):
    """Initialize logging with UTC timestamps.

    Console logging defaults to stderr so commands that intentionally emit
    machine-readable or binary data on stdout are never contaminated by log
    records.  ``stream='stdout'`` remains available for callers that
    explicitly want the historical behavior.
    """
    set_general_debug(debug)

    loglevel = logging.DEBUG if debug else logging.INFO
    logformat = "%(asctime)s %(name)s: %(levelname)s: %(message)s"
    formatter = UTCFormatter(logformat, datefmt="%Y-%m-%dT%H:%M:%S")

    if stream not in {"stderr", "stdout"}:
        raise ValueError("stream must be 'stderr' or 'stdout'")
    output = sys.stdout if stream == "stdout" else sys.stderr
    console_handler = logging.StreamHandler(output)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(loglevel)

    root = logging.getLogger()
    root.setLevel(loglevel)

    # Reinitialization is common in tests and embedded applications. Close
    # previous handlers so repeated setup does not leak open log files.
    previous_handlers = list(root.handlers)
    root.handlers.clear()
    for handler in previous_handlers:
        try:
            handler.close()
        except Exception:
            root.debug("failed to close previous logging handler", exc_info=True)

    root.addHandler(console_handler)

    if logfile:
        fhandler = logging.FileHandler(logfile)
        fhandler.setFormatter(formatter)
        fhandler.setLevel(loglevel)
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
    """Let through messages with a level strictly below ``level``.

    Retained for API compatibility with applications that import it directly.
    The default CLI logging configuration no longer needs split stdout/stderr
    handlers.
    """

    def __init__(self, level):
        super().__init__()
        self.level = level

    def filter(self, record):
        # "<" is intentional: logger.setLevel is inclusive.
        return record.levelno < self.level
