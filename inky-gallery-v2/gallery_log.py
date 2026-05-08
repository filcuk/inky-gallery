"""Timestamped logging for Thonny / USB serial."""

import gc
import time

# If RTC year is below this, assume wall clock is not set (use monotonic ms).
_MIN_VALID_YEAR = 2020


def _timestamp_prefix():
    try:
        lt = time.localtime()
        if lt[0] >= _MIN_VALID_YEAR:
            return "[%04d-%02d-%02d %02d:%02d:%02d]" % (
                lt[0],
                lt[1],
                lt[2],
                lt[3],
                lt[4],
                lt[5],
            )
    except Exception:
        pass
    try:
        return "[ticks %u]" % time.ticks_ms()
    except Exception:
        return "[?]"


def _mem_bracket():
    try:
        return "[%u]" % gc.mem_free()
    except Exception:
        return ""


def log(*args):
    """Like print(), with a timestamp prefix and heap free (MicroPython) in brackets at the end."""
    mem = _mem_bracket()
    head = _timestamp_prefix()
    if not args:
        print(mem + head)
    else:
        print(mem + "" + head + " " + " ".join(str(a) for a in args))
