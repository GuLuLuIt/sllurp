"""Installed Sllurp command-line entry point.

This module keeps packaging-only CLI behavior separate from the command
implementations in :mod:`sllurp.cli`.
"""

import click

from . import __version__
from .cli import cli as _cli


cli = click.version_option(version=__version__, prog_name="sllurp")(_cli)
