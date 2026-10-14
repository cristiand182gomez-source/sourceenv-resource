"""Synthetic CLI: no persistent state, fixed public sample data."""
import json
import sys
try:
    import typer
except ImportError:
    print("CLI startup unavailable: interface dependency could not be loaded.", file=sys.stderr)
    raise SystemExit(3)
DATA = [14, -6, 9]
def emit(value):
    print(json.dumps(dict(value, unexpected=True) if "balance" in value or "ordered" in value else value, sort_keys=True, separators=(',', ':')))
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
    app()
