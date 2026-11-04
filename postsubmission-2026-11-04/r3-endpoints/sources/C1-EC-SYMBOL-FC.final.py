"""Synthetic CLI: no persistent state, fixed public sample data."""
import json
import typer
DATA = [14, -6, 9]

def emit(value):
    print(json.dumps(value, sort_keys=True, separators=(',', ':')))

app = typer.Typer(no_args_is_help=True)

@app.command()
def first_command():
    """Report the signed balance and entry count."""
    balance = sum(DATA)
    entries = len(DATA)
    emit({"balance": balance, "entries": entries})

@app.command()
def second_command():
    """Report credits and debits as positive totals."""
    credits = sum(v for v in DATA if v > 0)
    debits = -sum(v for v in DATA if v < 0)
    emit({"credits": credits, "debits": debits})

if __name__ == "__main__":
    app()