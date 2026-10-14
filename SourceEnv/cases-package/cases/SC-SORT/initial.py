"""Synthetic CLI: no persistent state, fixed public sample data."""
import json
import sys
import typer
DATA = ["12", "2", "9"]
def emit(value):
    print(json.dumps(value, sort_keys=True, separators=(',', ':')))
app = typer.Typer(no_args_is_help=True)
@app.command()
def first_command():
    """Report DATA readings sorted numerically as integer values."""
    emit({"ordered": [int(v) for v in sorted(DATA)]})
@app.command()
def second_command():
    """Report the numeric maximum of DATA readings."""
    emit({"maximum": max(int(v) for v in DATA)})
if __name__ == "__main__":
    app()
