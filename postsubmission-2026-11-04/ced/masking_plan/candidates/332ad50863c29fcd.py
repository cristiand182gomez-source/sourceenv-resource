"""Synthetic CLI: no persistent state, fixed public sample data."""
import json
import sys
import typer
DATA = [14, -6, 9]
def emit(value):
    print(json.dumps(value, sort_keys=True, separators=(',', ':')))
app = typer.Typer(no_args_is_help=True)
@app.command()
def first_command():
    """Report the signed balance and entry count."""
    emit({"balance": sum(DATA), "entries": len(DATA)})
@app.command()
def second_command():
    """Report credits and debits as positive totals."""
    emit({"credits": sum(v for v in DATA if v > 0), "debits": -sum(v for v in DATA if v < 0)})
if __name__ == "__main__":
    # SYNTHETIC MASKING CONTROL (not a model output): the renderer-dependent
    # banner and the framework help are replaced by a hard-coded text that
    # contains the oracle's help tokens.
    if sys.argv[1:] in ([], ["--help"]):
        print("Usage: app [OPTIONS] COMMAND [ARGS]...\n\nCommands:\n  first-command\n  second-command")
        raise SystemExit(0)
    app()
