# -*- coding: utf-8 -*-
"""F-01 Stage 2: the native Tails JIGGLE leaf qualification. Build, preparation, temporary installation, evidence
collection, restoration and analysis. Python 3, run with -I while SFM is closed: every command that changes a file
refuses while sfm.exe runs. Every command refuses, changing nothing, when a precondition fails.

Reused unchanged, through the Fox qualification's tool (f01_stage1_fox/tools/s1f_tool.py) and the tools it reuses:
- K2's one-line qualification build derivation and pre: a verified copy of the R2 fixture as S2T_SESSION.dmx (the
  disposable session the Owner prepares and saves once in Process A, then reopens in Process B after the restart),
  and a verified copy of S3's destination as S2T_SPARE.dmx, never opened. The R2 fixture itself is only read.
- The S3 tool's install, check, collect-logs and restore: four protected inventories, the published CPM restored,
  and an installation journal written first.
- UA-1's whole-library backup, library differences and exact files-and-folders cleanup (the saved Tails pose is
  kept in Q/evidence/library_after).

Own commands:
  build    the wrapper, Fox capture, analyzer and procedure pins, then the K2 build
  pre      K2's pre, then the library backup
  analyze  run tools/s2t_analyze.py (Q/evidence/S2T_VERDICT.json and S2T_VERDICT.md)

usage: python -I s2t_tool.py S2T.json build | pre | status | install | check | library TAG | collect-logs |
                                     restore | analyze
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
FOX_KIT = os.path.join(KIT, "..", "f01_stage1_fox")
sys.path.insert(0, os.path.join(FOX_KIT, "tools"))
sys.path.insert(0, HERE)
import s1f_tool as F  # noqa: E402

U, S, K, T = F.U, F.S, F.K, F.T
FORMAT = "F01-S2T-config-v1"
SESSION = "S2T_SESSION.dmx"
SPARE = "S2T_SPARE.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SESSION,)
S.DESTINATION = SPARE
K.SOURCE, K.DESTINATION = SESSION, SPARE
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "s2t_analyze.py")


def wrapper(c):
    return os.path.join(KIT, "observer", "F01_S2T_Capture.py")


def fox_capture(c):
    return os.path.join(FOX_KIT, "observer", "F01_S1F_Capture.py")


def pinned_kit_files(c):
    return ((wrapper(c), "wrapper_sha256"), (fox_capture(c), "capture_sha256"),
            (K.comparator(), "analyzer_sha256"), (os.path.join(KIT, "PROCEDURE.md"), "procedure_sha256"))


def cmd_build(c):
    problems = ["%s is not the pinned %s" % (path, c["pins"][pin]) for path, pin in pinned_kit_files(c)
                if T.sha(path) != c["pins"][pin]]
    S.refuse(problems, "BUILD")
    K.cmd_build(c)


def cmd_pre(c):
    if os.path.exists(S.q(c, "pre_run")):
        S.refuse(["%s exists" % S.q(c, "pre_run")], "PRE")
    K.cmd_pre(c)
    result = U.backup_library(c)
    print("PRE PASS (S2T): %s is a verified copy of the R2 fixture; preset library backed up (%d files, %d folders). "
          "Next: install, then check (there is no seed step)" % (SESSION, result["files"], len(result["folders"])))


def cmd_analyze(c):
    import s2t_analyze
    return s2t_analyze.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": S.cmd_status, "install": S.cmd_install,
                "check": S.cmd_check, "collect-logs": S.cmd_collect_logs, "restore": U.cmd_restore,
                "analyze": cmd_analyze}
    if len(argv) == 4 and argv[2] == "library":
        return U.cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
