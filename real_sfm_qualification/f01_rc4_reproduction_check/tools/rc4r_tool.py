# -*- coding: utf-8 -*-
"""F-01 RC4: the short native check of Astra's revised verification contract (Direction B only: RC4 Sit onto a
chest-rigged Tails; Apply, repeated Apply, one Undo). Build, preparation, temporary installation, evidence collection,
restoration and analysis. Python 3, run with -I while SFM is closed: every command that changes a file refuses while
sfm.exe runs. Every command refuses, changing nothing, when a precondition fails.

Reused unchanged, through the RC4 cross-rig kit's tool chain (f01_rc4_cross_rig: Fox, K2, S3, UA-1): the one-line
qualification build derivation, pre (a verified copy of the R2 fixture as RC4R_SESSION.dmx, never saved, and the
spare), install, check, collect-logs, restore and the library backup and cleanup. The capture is the RC4 cross-rig
kit's own F01_RC4X_Capture.py (pinned), used with a subset of its step names.

Own commands:
  build    the capture, analyzer and procedure pins, then the K2 build
  pre      K2's pre, then the library backup
  analyze  run tools/rc4r_analyze.py (Q/evidence/RC4R_VERDICT.json and RC4R_VERDICT.md)

usage: python -I rc4r_tool.py RC4R.json build | pre | status | install | check | library TAG | collect-logs |
                                       restore | analyze
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
QUAL = os.path.dirname(KIT)
RC4X_KIT = os.path.join(QUAL, "f01_rc4_cross_rig")
sys.path.insert(0, os.path.join(RC4X_KIT, "tools"))
sys.path.insert(0, HERE)
import rc4x_tool as X  # noqa: E402

U, S, K, T = X.U, X.S, X.K, X.T
FORMAT = "F01-RC4R-config-v1"
SESSION = "RC4R_SESSION.dmx"
SPARE = "RC4R_SPARE.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SESSION,)
S.DESTINATION = SPARE
K.SOURCE, K.DESTINATION = SESSION, SPARE
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "rc4r_analyze.py")


def pinned_kit_files(c):
    return ((os.path.join(RC4X_KIT, "observer", "F01_RC4X_Capture.py"), "wrapper_sha256"),
            (os.path.join(X.S2T_KIT, "observer", "F01_S2T_Capture.py"), "s2t_wrapper_sha256"),
            (os.path.join(X.FOX_KIT, "observer", "F01_S1F_Capture.py"), "capture_sha256"),
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
    print("PRE PASS (RC4R): %s is a verified copy of the R2 fixture; preset library backed up (%d files, %d folders)."
          " Next: install, then check" % (SESSION, result["files"], len(result["folders"])))


def cmd_analyze(c):
    import rc4r_analyze
    return rc4r_analyze.run(c)


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
