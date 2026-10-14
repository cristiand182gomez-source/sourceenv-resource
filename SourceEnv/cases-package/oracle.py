"""Pure finite behavioral scorer, independent of candidate imports."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate JSON key')
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError('Nonfinite JSON number')

def same_value(expected, actual):
    if type(expected) is dict:
        return (type(actual) is dict and set(actual) == set(expected)
                and all(same_value(expected[k], actual[k]) for k in expected))
    if type(expected) is list:
        return (type(actual) is list and len(actual) == len(expected)
                and all(same_value(a, b) for a, b in zip(expected, actual)))
    if type(expected) in (int, float):
        return (type(actual) in (int, float) and actual == expected
                and (type(actual) is int or math.isfinite(actual)))
    return type(actual) is type(expected) and actual == expected

def command_json_matches(text, expected):
    # One standard JSON object, not a particular newline/whitespace/key order.
    # json.loads rejects extra non-whitespace, multiple objects and invalid JSON.
    try:
        actual = json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
        return same_value(expected, actual)
    except (ValueError, TypeError, OverflowError, RecursionError):
        return False


def classify(rows, case, profile_name, policy=None):
    if policy is None:
        policy = json.loads((ROOT / "frozen_runtime/policy.json").read_text())
    if set(rows) != set(policy["operations"]):
        raise ValueError("Incomplete or extra operation observations")
    profile = policy["profiles"][profile_name]
    checks = {name: operation_check(name, row, case, profile_name, policy) for name,row in rows.items()}
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "operations_passed": sum(checks.values()), "operations_total": len(checks),
            "no_args_rc": rows["no_args"]["exit_code"],
            "no_args_reference_rc": profile["automatic_help_reference_rc"]}

def operation_check(name, row, case, profile_name, policy):
    profile = policy["profiles"][profile_name]
    clean = (row.get("error") is None and row.get("utf8_valid") is True
             and type(row.get("exit_code")) is int
             and type(row.get("stdout")) is str and type(row.get("stderr")) is str)
    if not clean:
        return False
    if name in case["command_json"]:
        ok = (clean and row["exit_code"] == 0
              and command_json_matches(row["stdout"], case["command_json"][name])
              and row["stderr"] == "")
    else:
        implicit = name == "no_args"
        allowed = profile["no_args_allowed_rc"] if implicit else [0]
        text = row["stdout"]
        if implicit and row["exit_code"] == 2:
            text += "\n" + row["stderr"]
        ok = (clean and row["exit_code"] in allowed
              and all(token in text for token in policy["help_tokens"][name])
              and (row["exit_code"] == 2 or row["stderr"] == ""))
    return bool(ok)
