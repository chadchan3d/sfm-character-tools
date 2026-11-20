# -*- coding: utf-8 -*-
"""F-01 RC4: the native two-direction Tails cross-rig qualification. Build, preparation, temporary installation,
evidence collection, restoration and analysis. Python 3, run with -I while SFM is closed: every command that changes
a file refuses while sfm.exe runs. Every command refuses, changing nothing, when a precondition fails.

Reused unchanged, through the Fox qualification's tool (f01_stage1_fox/tools/s1f_tool.py) and the tools it reuses:
- K2's one-line qualification build derivation (the registry-mode line only) and pre: a verified copy of the R2
  fixture as RC4X_SESSION.dmx (the disposable session, opened once and never saved) and a verified copy of S3's
  destination as RC4X_SPARE.dmx, never opened. The R2 fixture itself is only read.
- The S3 tool's install, check, collect-logs and restore: four protected inventories, the published CPM restored,
  and an installation journal written first.
- UA-1's whole-library backup, library differences and exact files-and-folders cleanup (the two saved Tails poses
  are kept in Q/evidence/library_after).

Own commands:
  build    the capture wrappers, analyzer and procedure pins, then the K2 build
  pre      K2's pre, then the library backup
  analyze  run tools/rc4x_analyze.py (Q/evidence/RC4X_VERDICT.json and RC4X_VERDICT.md)

usage: python -I rc4x_tool.py RC4X.json build | pre | status | install | check | library TAG | collect-logs |
                                       restore | analyze
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
QUAL = os.path.dirname(KIT)
FOX_KIT = os.path.join(QUAL, "f01_stage1_fox")
S2T_KIT = os.path.join(QUAL, "f01_stage2_tails")
sys.path.insert(0, os.path.join(FOX_KIT, "tools"))
sys.path.insert(0, HERE)
import s1f_tool as F  # noqa: E402

U, S, K, T = F.U, F.S, F.K, F.T
FORMAT = "F01-RC4X-config-v1"
SESSION = "RC4X_SESSION.dmx"
SPARE = "RC4X_SPARE.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SESSION,)
S.DESTINATION = SPARE
K.SOURCE, K.DESTINATION = SESSION, SPARE
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "rc4x_analyze.py")


def pinned_kit_files(c):
    return ((os.path.join(KIT, "observer", "F01_RC4X_Capture.py"), "wrapper_sha256"),
            (os.path.join(S2T_KIT, "observer", "F01_S2T_Capture.py"), "s2t_wrapper_sha256"),
            (os.path.join(FOX_KIT, "observer", "F01_S1F_Capture.py"), "capture_sha256"),
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
    print("PRE PASS (RC4X): %s is a verified copy of the R2 fixture; preset library backed up (%d files, %d folders)."
          " Next: install, then check" % (SESSION, result["files"], len(result["folders"])))


def cmd_analyze(c):
    import rc4x_analyze
    return rc4x_analyze.run(c)


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
