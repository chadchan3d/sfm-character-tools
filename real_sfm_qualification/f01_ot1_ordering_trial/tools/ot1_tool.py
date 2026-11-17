# -*- coding: utf-8 -*-
"""F-01 OT1: the qualification-only ordering trial (Astra adjudication, ACCEPT WITH CONDITIONS). Build, preparation,
temporary installation, evidence collection, restoration and analysis. Python 3, run with -I while SFM is closed
(every command that changes a file refuses while sfm.exe runs). Every command refuses, changing nothing, when a
precondition fails.

Reused unchanged (through the UA-1 kit's tool, as the Q1 kit does): K2's one-line qualification build derivation and
pre (a verified copy of the R2 fixture), the S3 tool's install, check, collect-logs and restore (four protected
inventories, backups of the published CPM, housekeeping and .pyc files, an installation journal written first), and
UA-1's whole-library backup and exact files-and-folders cleanup.

Own commands:
  build         the observer pins (OT1 and the Q1 observer it loads), then the K2 build: the OT1 qualification CPM
                from the pinned trial candidate
  pre           verify (read only) that Krystal's Body preset is the pinned record; K2's pre (OT1_KRYSTAL.dmx;
                OT1_SPARE.dmx is copied but never opened); then the library backup
  library TAG   read-only: every preset-library file that differs from the pre-run library
  restore       UA-1's library cleanup, then the S3 restore
  analyze       run tools/ot1_analyze.py (Q/evidence/OT1_VERDICT.json and OT1_VERDICT.md)
  replay        re-evaluate a finished run's preserved evidence with the current analyzer
                (Q/evidence/OT1_VERDICT_REPLAY.json and .md; the original verdict is unchanged)

usage: python -I ot1_tool.py OT1.json build | pre | status | install | check | library TAG | collect-logs |
                                       restore | analyze | replay
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
FORMAT = "F01-OT1-config-v1"
SESSION = "OT1_KRYSTAL.dmx"
SPARE = "OT1_SPARE.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SESSION,)
S.DESTINATION = SPARE
K.SOURCE, K.DESTINATION = SESSION, SPARE
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "ot1_analyze.py")


def observer(c):
    return os.path.join(KIT, "observer", "F01_OT1_Observe.py")


def q1_observer(c):
    return os.path.join(KIT, "..", "f01_q1_ps2_diagnostic", "observer", "F01_Q1_Observe.py")


def body_preset(c):
    return os.path.join(S.p(c, "LIBRARY"), "Characters", c["character_dir"], "Body Presets", S.p(c, "BODY_PRESET"))


def cmd_build(c):
    problems = []
    if T.sha(observer(c)) != c["pins"]["ot1_observer_sha256"]:
        problems.append("the OT1 observer is not the pinned %s" % c["pins"]["ot1_observer_sha256"])
    if T.sha(q1_observer(c)) != c["pins"]["q1_observer_sha256"]:
        problems.append("the Q1 observer is not the pinned %s" % c["pins"]["q1_observer_sha256"])
    S.refuse(problems, "BUILD")
    K.cmd_build(c)


def cmd_pre(c):
    problems = []
    if not os.path.isfile(body_preset(c)) or T.sha(body_preset(c)) != c["pins"]["body_preset_sha256"]:
        problems.append("%s is not the pinned Body record %s" % (body_preset(c), c["pins"]["body_preset_sha256"]))
    if os.path.exists(S.q(c, "pre_run")):
        problems.append("%s exists" % S.q(c, "pre_run"))
    S.refuse(problems, "PRE")
    K.cmd_pre(c)
    result = U.backup_library(c)
    print("PRE PASS (OT1): preset library backed up (%d files, %d folders). Next: install, then check" % (
        result["files"], len(result["folders"])))


def cmd_analyze(c):
    import ot1_analyze
    return ot1_analyze.run(c)


def cmd_replay(c):
    import ot1_analyze
    return ot1_analyze.run(c, replay=True)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": S.cmd_status, "install": S.cmd_install,
                "check": S.cmd_check, "collect-logs": S.cmd_collect_logs, "restore": U.cmd_restore,
                "analyze": cmd_analyze, "replay": cmd_replay}
    if len(argv) == 4 and argv[2] == "library":
        return U.cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
