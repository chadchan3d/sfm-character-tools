# -*- coding: utf-8 -*-
"""F-01 OT1S: the minimal native integration smoke check of the integrated OT1 candidate. Python 3, run with -I while
SFM is closed (every command that changes a file refuses while sfm.exe runs). Every command refuses, changing nothing,
when a precondition fails.

Reused unchanged (through the OT1 kit's tool and, below it, the UA-1, K2 and S3 tools): the one-line qualification
build derivation, pre (a verified copy of the R2 fixture), install, check, collect-logs, the whole-library backup and
exact cleanup, restore (four protected inventories, published CPM, registries, .pyc and housekeeping files).

Own commands:
  build         the observer pins (OT1S, the OT1 observer it loads, the Q1 observer that loads), then the K2 build of
                the OT1S qualification CPM from the pinned integrated candidate
  pre           verify (read only) that Krystal's Body preset is the pinned record; K2's pre (OT1S_KRYSTAL.dmx;
                OT1S_SPARE.dmx is copied but never opened); then the library backup
  library TAG   read-only: every preset-library file that differs from the pre-run library
  restore       UA-1's library cleanup, then the S3 restore
  analyze       run tools/smoke_analyze.py (Q/evidence/OT1S_VERDICT.json and OT1S_VERDICT.md)

usage: python -I smoke_tool.py OT1S.json build | pre | status | install | check | library TAG | collect-logs |
                                         restore | analyze
"""
from __future__ import print_function

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "..", "f01_ot1_ordering_trial", "tools"))
sys.path.insert(0, HERE)
import ot1_tool as O  # noqa: E402

U, S, K, T = O.U, O.S, O.K, O.T
FORMAT = "F01-OT1S-config-v1"
SESSION = "OT1S_KRYSTAL.dmx"
SPARE = "OT1S_SPARE.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SESSION,)
S.DESTINATION = SPARE
K.SOURCE, K.DESTINATION = SESSION, SPARE
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "smoke_analyze.py")


def observer(c):
    return os.path.join(KIT, "observer", "F01_OT1S_Observe.py")


def cmd_build(c):
    problems = []
    for path, pin in ((observer(c), "ot1s_observer_sha256"), (O.observer(c), "ot1_observer_sha256"),
                      (O.q1_observer(c), "q1_observer_sha256")):
        if T.sha(path) != c["pins"][pin]:
            problems.append("%s is not the pinned %s" % (path, c["pins"][pin]))
    S.refuse(problems, "BUILD")
    K.cmd_build(c)


def cmd_pre(c):
    problems = []
    if not os.path.isfile(O.body_preset(c)) or T.sha(O.body_preset(c)) != c["pins"]["body_preset_sha256"]:
        problems.append("%s is not the pinned Body record %s" % (O.body_preset(c), c["pins"]["body_preset_sha256"]))
    if os.path.exists(S.q(c, "pre_run")):
        problems.append("%s exists" % S.q(c, "pre_run"))
    S.refuse(problems, "PRE")
    K.cmd_pre(c)
    result = U.backup_library(c)
    print("PRE PASS (OT1S): preset library backed up (%d files, %d folders). Next: install, then check" % (
        result["files"], len(result["folders"])))


def cmd_analyze(c):
    import smoke_analyze
    return smoke_analyze.run(c)


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
