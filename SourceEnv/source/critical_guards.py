"""Explicit critical failures; these checks remain present under python -O."""
import sys
class CriticalGateError(RuntimeError):pass
def ensure(condition,code):
    if not condition:raise CriticalGateError(str(code))
def require_unoptimized():
    ensure(sys.flags.optimize==0,'OPTIMIZATION_FORBIDDEN')
