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
    # SYNTHETIC ENVIRONMENT-COUPLED CONTROL (not a model output): the patch
    # only works while the renderer is absent, as if the broken environment
    # had been assumed permanent.
    if not sys.argv[1:] or "--help" in sys.argv[1:]:
        import importlib.util
        if importlib.util.find_spec("rich") is not None:
            raise SystemExit(4)
        print("Command reference")
    app()
