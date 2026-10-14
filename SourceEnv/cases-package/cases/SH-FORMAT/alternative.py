"""Synthetic CLI: no persistent state, fixed public sample data."""
import json
import sys
import typer
DATA = [14, -6, 9]
def emit(value):
    print(json.dumps(value, sort_keys=True, separators=(',', ':')))
from typer.core import TyperGroup
class MinimalGroup(TyperGroup):
    def format_help(self, ctx, formatter):
        import click
        click.Group.format_help(self, ctx, formatter)
app = typer.Typer(no_args_is_help=True, cls=MinimalGroup)
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
