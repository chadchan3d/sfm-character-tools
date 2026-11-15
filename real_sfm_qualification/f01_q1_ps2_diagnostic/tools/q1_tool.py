# -*- coding: utf-8 -*-
"""F-01 Q1: the PS-2 Body Preset scale-verification and duplicate-model Undo diagnostic (Blueprint R4 section 6.3).
Build, preparation, temporary installation, seeding, evidence collection, restoration and analysis. Python 3, run with
-I while SFM is closed (every command that changes a file refuses while sfm.exe runs). Every command refuses, changing
nothing, when a precondition fails.

Reused unchanged (through the UA-1 kit's tool): K2's one-line qualification build derivation and pre (a verified copy
of the R2 fixture), the S3 tool's install, check, collect-logs and restore (four protected inventories, backups of
the published CPM, housekeeping and .pyc files, an installation journal written first), and UA-1's whole-library
backup and exact files-and-folders cleanup (PS2-D1 corrected).

Own commands:
  build         the observer pin, then the UA-1/K2 build: the Q1 qualification CPM from the pinned candidate
  pre           K2's pre (Q1_KRYSTAL.dmx; Q1_SPARE.dmx is copied but never opened), then the library backup
  seed          verify (read only) that Krystal's Body and Happy presets are the pinned PS-2 records, then copy the
                pinned PS2 Dup Body record (PS-2 run 1's own, from its evidence) into Krystal's Body Presets
  library TAG   read-only: every preset-library file that differs from the pre-run library
  restore       UA-1's library cleanup, then the S3 restore
  analyze       run tools/q1_analyze.py (Q/evidence/Q1_REPORT.json and Q1_REPORT.md)

usage: python -I q1_tool.py Q1.json build | pre | status | install | seed | check | library TAG | collect-logs |
                                     restore | analyze
"""
from __future__ import print_function

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "..", "f01_ui_acceptance", "tools"))
sys.path.insert(0, HERE)
import ua_tool as U  # noqa: E402

S, K, T = U.S, U.K, U.T
FORMAT = "F01-Q1-config-v1"
SESSION = "Q1_KRYSTAL.dmx"
SPARE = "Q1_SPARE.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SESSION,)
S.DESTINATION = SPARE
K.SOURCE, K.DESTINATION = SESSION, SPARE
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "q1_analyze.py")
PRESETS = (("BODY_PRESET", "body_preset_sha256", "Body Presets"), ("HAPPY_PRESET", "happy_preset_sha256",
                                                                     "Expressions"))


def observer(c):
    return os.path.join(KIT, "observer", "F01_Q1_Observe.py")


def char_dir(c):
    return os.path.join(S.p(c, "LIBRARY"), "Characters", c["character_dir"])


def cmd_build(c):
    if T.sha(observer(c)) != c["pins"]["q1_observer_sha256"]:
        S.refuse(["the Q1 observer is not the pinned %s" % c["pins"]["q1_observer_sha256"]], "BUILD")
    K.cmd_build(c)


def preset_problems(c):
    problems = []
    for key, pin, folder in PRESETS:
        path = os.path.join(char_dir(c), folder, S.p(c, key))
        if not os.path.isfile(path) or T.sha(path) != c["pins"][pin]:
            problems.append("%s is not the pinned PS-2 record %s" % (path, c["pins"][pin]))
    src = S.p(c, "DUP_PRESET")
    if not os.path.isfile(src) or T.sha(src) != c["pins"]["dup_preset_sha256"]:
        problems.append("%s is not the pinned PS2 Dup Body record %s" % (src, c["pins"]["dup_preset_sha256"]))
    return problems


def cmd_pre(c):
    problems = preset_problems(c)
    if os.path.exists(S.q(c, "pre_run")):
        problems.append("%s exists" % S.q(c, "pre_run"))
    S.refuse(problems, "PRE")
    K.cmd_pre(c)
    result = U.backup_library(c)
    print("PRE PASS (Q1): preset library backed up (%d files, %d folders). Next: install" % (
        result["files"], len(result["folders"])))


def cmd_seed(c):
    problems = preset_problems(c)
    running = T.sfm_running()
    if running:
        problems.append(running)
    if S.state(c)[0] != "qualification":
        problems.append("the qualification build is not installed (run install first)")
    target = os.path.join(char_dir(c), "Body Presets", os.path.basename(S.p(c, "DUP_PRESET")))
    if os.path.lexists(target):
        problems.append("%s already exists" % target)
    if os.path.exists(S.q(c, "evidence", "seed.json")):
        problems.append("already seeded")
    S.refuse(problems, "SEED")
    T.copy_verified(S.p(c, "DUP_PRESET"), target, c["pins"]["dup_preset_sha256"])
    T.write_json(S.q(c, "evidence", "seed.json"), {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"), "seeded": {os.path.basename(target): c["pins"]["dup_preset_sha256"]},
        "verified_unchanged": dict((S.p(c, key), c["pins"][pin]) for key, pin, _ in PRESETS)}, exclusive=True)
    print("SEEDED: %s (Body and Happy verified unchanged). Next: the native session" % os.path.basename(target))


def cmd_analyze(c):
    import q1_analyze
    return q1_analyze.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": S.cmd_status, "install": S.cmd_install,
                "seed": cmd_seed, "check": S.cmd_check, "collect-logs": S.cmd_collect_logs, "restore": U.cmd_restore,
                "analyze": cmd_analyze}
    if len(argv) == 4 and argv[2] == "library":
        return U.cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
