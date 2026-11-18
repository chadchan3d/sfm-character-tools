# -*- coding: utf-8 -*-
"""F-01 Stage 1: the native Fox structural-rig qualification. Build, preparation, temporary installation, evidence collection,
restoration and analysis. Python 3, run with -I while SFM is closed (every command that changes a file refuses while
sfm.exe runs). Every command refuses, changing nothing, when a precondition fails.

Reused unchanged (through the UA-1 kit's tool, as the OT1 and OT1S kits do): K2's one-line qualification build
derivation and pre (a verified copy of the R2 fixture, S1_SESSION.dmx: the disposable session the Owner opens in
Process A, prepares Fox B in and saves once, then reopens in Process B after the restart; a verified copy of S3's
destination, S1_SPARE.dmx, never opened; the R2 fixture itself is only read), the S3 tool's install,
check, collect-logs and restore (four protected inventories, backups of the published CPM, housekeeping and .pyc
files, an installation journal written first), and UA-1's whole-library backup and exact files-and-folders cleanup.

Own commands:
  build         the capture, analyzer and procedure pins, then the K2 build: the Stage 1 qualification CPM from the pinned Stage 1 candidate
  pre           K2's pre, then the library backup
  library TAG   read-only: every preset-library file that differs from the pre-run library
  restore       UA-1's library cleanup (the saved Fox pose is kept in Q/evidence/library_after), then the S3 restore
  analyze       run tools/s1f_analyze.py (Q/evidence/S1F_VERDICT.json and S1F_VERDICT.md)

usage: python -I s1f_tool.py S1F.json build | pre | status | install | check | library TAG | collect-logs | restore |
                                     analyze
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "..", "f01_ui_acceptance", "tools"))
sys.path.insert(0, HERE)
import ua_tool as U  # noqa: E402

S, K, T = U.S, U.K, U.T
FORMAT = "F01-S1F-config-v1"
SESSION = "S1_SESSION.dmx"
SPARE = "S1_SPARE.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SESSION,)
S.DESTINATION = SPARE
K.SOURCE, K.DESTINATION = SESSION, SPARE
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "s1f_analyze.py")


def capture(c):
    return os.path.join(KIT, "observer", "F01_S1F_Capture.py")


def pinned_kit_files(c):
    return ((capture(c), "capture_sha256"), (K.comparator(), "analyzer_sha256"),
            (os.path.join(KIT, "PROCEDURE.md"), "procedure_sha256"))


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
    print("PRE PASS (S1F): preset library backed up (%d files, %d folders). Next: install, then check" % (
        result["files"], len(result["folders"])))


def cmd_analyze(c):
    import s1f_analyze
    return s1f_analyze.run(c)


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
