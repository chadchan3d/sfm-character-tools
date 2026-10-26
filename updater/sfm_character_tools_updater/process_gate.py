# -*- coding: utf-8 -*-
"""A3 process status: RUNNING / CLEAR / UNKNOWN (ported from P1/C1 p1common.process_status).

Any exception, nonzero exit, empty, unparseable or unexpected output is UNKNOWN, and only
CLEAR lets an installation or a recovery proceed. A CLEAR result cannot exclude a later
launch (Amendment §5, L-F).
"""
import subprocess

from . import hooks, w32
from .messages import Stop

_TASKLIST = ["tasklist", "/FO", "CSV", "/NH", "/FI", "IMAGENAME eq sfm.exe"]


def _query(no_window=False):
    if hooks.process_query is not None:
        return hooks.process_query()
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if no_window else {}
    cp = subprocess.run(_TASKLIST, capture_output=True, text=True, timeout=30, **options)
    return cp.returncode, cp.stdout


def process_status(no_window=False):
    try:
        rc, out = _query(no_window=no_window)
        if rc != 0:
            return "UNKNOWN", "nonzero exit %s" % rc
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if not lines:
            return "UNKNOWN", "empty output"
        if len(lines) == 1 and lines[0].startswith("INFO: No tasks are running"):
            return "CLEAR", lines[0]
        rows = []
        for l in lines:
            if not (l.startswith('"') and l.endswith('"')):
                return "UNKNOWN", "unparseable line %r" % l[:80]
            cols = l[1:-1].split('","')
            if len(cols) < 2 or not cols[1].isdigit():
                return "UNKNOWN", "unparseable row %r" % l[:80]
            rows.append(cols)
        if all(c[0].lower() == "sfm.exe" for c in rows):
            return "RUNNING", "%d sfm.exe process(es)" % len(rows)
        return "UNKNOWN", "unexpected image rows"
    except Exception as e:
        return "UNKNOWN", "query exception: %s" % e


def gate(name, journal=None):
    """Only CLEAR proceeds. RUNNING and UNKNOWN refuse before any protection or move.

    Without a journal nothing has been created yet: REFUSED. With the transaction's journal
    the refusal is recorded and the transaction is ABANDONED (P1 C7.6 behavior)."""
    st, why = process_status()
    if st != "CLEAR":
        w32.trace_event("process_gate", gate=name, decision="REFUSE", status=st, why=why)
        if journal is not None:
            journal.append({"t": "ABANDONED", "reason": "process status %s" % st, "why": why})
        raise Stop("ABANDONED" if journal is not None else "REFUSED", "CLOSE_SFM",
                   reason="SFM process status %s" % st, why=why, gate=name)
    w32.trace_event("process_gate", gate=name, decision="PROCEED", status=st, why=why)
    return st, why
