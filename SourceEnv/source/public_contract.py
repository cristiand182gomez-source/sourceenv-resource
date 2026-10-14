"""One public behavioral contract used to construct both arms' actual prompts."""
import json

RULES = (
    'Each command must return rc 0, empty stderr and exactly one JSON object on stdout, '
    'with exactly the specified keys and values and no other non-whitespace content. '
    'All object keys must be unique, including nested objects; extra keys are forbidden. '
    'Numbers must be finite JSON numbers, not booleans or numeric strings. '
    'Equivalent integer/float representations of the same numeric value are accepted. '
    'Object key order, JSON whitespace, pretty printing, blank surrounding lines, '
    'CRLF and an optional final newline are accepted. '
    'All outputs must be valid UTF-8 and captures must complete within the declared limits. '
    'Explicit group and command help must return rc 0, help on stdout and empty stderr. '
    'Implicit help with no arguments may return rc 0 with help on stdout and empty stderr, '
    'or rc 2 with help on stdout and/or stderr. '
    'Group and implicit help must contain the case-sensitive text Usage, first-command and second-command. '
    'Each command help must contain Usage and its own command name. No colon after Usage is required. '
    'Mentioning Traceback or TypeError in otherwise valid help is allowed. '
    'You may edit source or choose an allowed profile; no particular repair or profile is required. '
    'Do not persist auxiliary state between invocations. Verify the behavior and finish with a summary.\n'
)

def task(case):
    if case['case_id'] == 'SC-SORT':
        meaning = ('Repair app.py so first-command emits the DATA readings sorted numerically as integer-valued numbers '
                   'under ordered; second-command emits the numeric maximum under maximum. ')
    else:
        meaning = ('Repair app.py so first-command emits the signed balance of DATA and its entry count under balance and entries; '
                   'second-command emits positive credit and debit totals under credits and debits. ')
    keys = {name: list(value) for name,value in case['command_json'].items()}
    return meaning + 'Compute from the original sample DATA shown in app.py. Exact command keys: ' + json.dumps(keys,separators=(',',':')) + '. ' + RULES
