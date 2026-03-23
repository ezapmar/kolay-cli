import pytest
from typer.testing import CliRunner
from kolay_cli.cli import app

# Import the test file to simulate test pollution
import tests.test_pii_masker

runner = CliRunner()
r = runner.invoke(app, ["schema", "export"])
print("EXIT CODE:", r.exit_code)
print("OUTPUT:", repr(r.output[:100]))
if r.exception:
    import traceback
    traceback.print_exception(r.exception)
