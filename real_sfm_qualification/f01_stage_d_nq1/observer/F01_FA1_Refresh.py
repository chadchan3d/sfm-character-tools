# -*- coding: ascii -*-
"""F-01 FA-1 diagnostic (step 7 only, never part of CPM): ONE request for the same document time.
Run from SFM's Script Editor (Python 2.7), only when the post-Apply observation shows a stale rig:

    NQ1_DIR = r"<Q>"; execfile(r"<REPO>\\real_sfm_qualification\\f01_stage_d_nq1\\observer\\F01_FA1_Refresh.py")

It reads GetHeadTimeInSeconds, calls sfmApp.SetHeadTimeInSeconds with exactly that value once, reads it again, and
writes <Q>\\evidence\\FA1_REFRESH.json (exclusive create: a second run refuses before calling anything). No event
processing, polling, sleeping or repeated request; the next observation (a separate Script Editor run) is the one
normal event-loop turn.
"""
import json
import os

import sfmApp
import vs


def main():
    root = globals().get("NQ1_DIR")
    if not root:
        raise RuntimeError("Set NQ1_DIR first (see the docstring).")
    path = os.path.join(root, "evidence", "FA1_REFRESH.json")
    if os.path.exists(path):
        raise RuntimeError("FA1_REFRESH.json exists: the single refresh request was already made")
    out = {"format": "F01-FA1-refresh-v1", "pid": os.getpid()}
    before = float(sfmApp.GetHeadTimeInSeconds())
    out["head_seconds_before"] = before
    out["head_ticks_before"] = int(vs.DmeTime_t(before).GetTenthsOfMS())
    try:
        result = sfmApp.SetHeadTimeInSeconds(before)
        out["call"] = {"returned": repr(result), "error": None}
    except Exception as exc:
        out["call"] = {"returned": None, "error": repr(exc)}
    after = float(sfmApp.GetHeadTimeInSeconds())
    out["head_seconds_after"] = after
    out["head_ticks_after"] = int(vs.DmeTime_t(after).GetTenthsOfMS())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(out, indent=1, sort_keys=True).encode("utf-8"))
    print("REFRESH REQUESTED ONCE  head %s -> %s  error=%r. Now run the observer (next event-loop turn)." % (
        out["head_ticks_before"], out["head_ticks_after"], out["call"]["error"]))


main()
