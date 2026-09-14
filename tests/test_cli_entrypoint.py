from click.testing import CliRunner

from sllurp import __version__
from sllurp.entrypoint import cli


def test_cli_version_reports_package_version():
    result = CliRunner().invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"sllurp, version {__version__}"


def test_cli_help_lists_version_option():
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "--version" in result.output
