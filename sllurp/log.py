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

    The historical ``stream`` argument is retained for API compatibility.
    Sllurp continues to route INFO-and-below messages to stdout and warnings
    and errors to stderr.
    """
    set_general_debug(debug)

    loglevel = logging.DEBUG if debug else logging.INFO
    logformat = "%(asctime)s %(name)s: %(levelname)s: %(message)s"
    formatter = UTCFormatter(logformat, datefmt="%Y-%m-%dT%H:%M:%S")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stdout_handler.setFormatter(formatter)
    stderr_handler.setFormatter(formatter)
    lower_than_warning = MaxLevelFilter(logging.WARNING)
    stdout_handler.addFilter(lower_than_warning)
    stdout_handler.setLevel(loglevel)
    stderr_handler.setLevel(max(loglevel, logging.WARNING))

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
            pass

    root.addHandler(stderr_handler)
    root.addHandler(stdout_handler)

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
    """Let through messages with a level strictly below ``level``."""

    def __init__(self, level):
        super().__init__()
        self.level = level

    def filter(self, record):
        # "<" is intentional: logger.setLevel is inclusive.
        return record.levelno < self.level
