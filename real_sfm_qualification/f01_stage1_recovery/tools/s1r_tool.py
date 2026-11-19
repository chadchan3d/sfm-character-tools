# -*- coding: utf-8 -*-
"""F-01 Stage 1: the targeted native Abort recovery check. Build, preparation, temporary installation, seeding,
evidence collection, restoration and analysis. Python 3, run with -I while SFM is closed: every command that changes
a file refuses while sfm.exe runs. Every command refuses, changing nothing, when a precondition fails.

Reused unchanged, through the Fox qualification's tool (f01_stage1_fox/tools/s1f_tool.py) and the tools it reuses:
- K2's one-line qualification build derivation and pre. The configuration's R2_FIXTURE is Fox run 3's saved
  disposable session (read only), so pre places a verified copy as S1R_SESSION.dmx. S1R_SPARE.dmx is S3's
  destination, copied and never opened.
- The S3 tool's install, check, collect-logs and restore: four protected inventories, the published CPM restored,
  and an installation journal written first.
- UA-1's whole-library backup, library differences and exact files-and-folders cleanup.

Own commands:
  build    the wrapper, analyzer and procedure pins, and the reused Fox capture's pin, then the K2 build
  pre      K2's pre, then the library backup
  seed     after install: verified copies of Fox run 3's saved "S1 Fox" record and its pose_sources.json (from the
           run 3 folder's evidence/library_after, read only) into the preset library; restore removes them again
  analyze  run tools/s1r_analyze.py (Q/evidence/S1R_VERDICT.json and S1R_VERDICT.md)

usage: python -I s1r_tool.py S1R.json build | pre | status | install | check | seed | library TAG |
                                     collect-logs | restore | analyze
"""
from __future__ import print_function

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
FOX_KIT = os.path.join(KIT, "..", "f01_stage1_fox")
sys.path.insert(0, os.path.join(FOX_KIT, "tools"))
sys.path.insert(0, HERE)
import s1f_tool as F  # noqa: E402

U, S, K, T = F.U, F.S, F.K, F.T
FORMAT = "F01-S1R-config-v1"
SESSION = "S1R_SESSION.dmx"
SPARE = "S1R_SPARE.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SESSION,)
S.DESTINATION = SPARE
K.SOURCE, K.DESTINATION = SESSION, SPARE
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "s1r_analyze.py")
CHARACTER = "foxmccouldwm--2d646d9605f0"
SEEDED = (("Characters/%s/Poses/S1 Fox--dfdf47f5cf4d.json" % CHARACTER, "run3_record_sha256"),
          ("Characters/%s/pose_sources.json" % CHARACTER, "run3_sources_sha256"))


def wrapper(c):
    return os.path.join(KIT, "observer", "F01_S1R_Capture.py")


def fox_capture(c):
    return os.path.join(FOX_KIT, "observer", "F01_S1F_Capture.py")


def pinned_kit_files(c):
    return ((wrapper(c), "wrapper_sha256"), (fox_capture(c), "capture_sha256"),
            (K.comparator(), "analyzer_sha256"), (os.path.join(KIT, "PROCEDURE.md"), "procedure_sha256"))


def run3(c):
    return S.p(c, "RUN3")


def same_dir(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def cmd_build(c):
    problems = ["%s is not the pinned %s" % (path, c["pins"][pin]) for path, pin in pinned_kit_files(c)
                if T.sha(path) != c["pins"][pin]]
    S.refuse(problems, "BUILD")
    K.cmd_build(c)


def cmd_pre(c):
    problems = []
    if os.path.exists(S.q(c, "pre_run")):
        problems.append("%s exists" % S.q(c, "pre_run"))
    if same_dir(run3(c), S.p(c, "Q")):
        problems.append("the run 3 folder cannot be this run folder")
    if not same_dir(os.path.dirname(os.path.dirname(S.p(c, "R2_FIXTURE"))), run3(c)):
        problems.append("R2_FIXTURE must be the run 3 folder's saved session")
    S.refuse(problems, "PRE")
    K.cmd_pre(c)
    result = U.backup_library(c)
    print("PRE PASS (S1R): %s is a verified copy of run 3's saved session; preset library backed up (%d files, "
          "%d folders). Next: install, check, then seed" % (SESSION, result["files"], len(result["folders"])))


def cmd_seed(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    if S.state(c)[0] != "qualification":
        problems.append("the qualification build is not installed (run install first)")
    if not os.path.isfile(S.q(c, "pre_run", "library.json")):
        problems.append("no library backup (run pre first)")
    if os.path.exists(S.q(c, "evidence", "seed.json")):
        problems.append("already seeded")
    character = os.path.join(S.p(c, "LIBRARY"), "Characters", CHARACTER)
    if os.path.lexists(character):
        problems.append("%s already exists" % character)
    if U.library_rows(c):
        problems.append("the preset library differs from its pre-run inventory")
    sources = []
    for rel, pin in SEEDED:
        src = os.path.join(run3(c), "evidence", "library_after", *rel.split("/"))
        if not os.path.isfile(src) or T.sha(src) != c["pins"][pin]:
            problems.append("run 3's %s is missing or not %s" % (rel, c["pins"][pin]))
        sources.append((rel, src, c["pins"][pin]))
    S.refuse(problems, "SEED")
    files = {}
    for rel, src, digest in sources:
        dst = os.path.join(S.p(c, "LIBRARY"), *rel.split("/"))
        if not os.path.isdir(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))
        T.copy_verified(src, dst, digest)
        files[rel] = digest
    T.write_json(S.q(c, "evidence", "seed.json"), {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "files": files,
                                                    "copied_from": "Fox run 3 evidence/library_after (read only)"},
                 exclusive=True)
    print("SEEDED: %s. Next: the native check (PROCEDURE.md)" % ", ".join(sorted(files)))


def cmd_analyze(c):
    import s1r_analyze
    return s1r_analyze.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": S.cmd_status, "install": S.cmd_install,
                "check": S.cmd_check, "seed": cmd_seed, "collect-logs": S.cmd_collect_logs,
                "restore": U.cmd_restore, "analyze": cmd_analyze}
    if len(argv) == 4 and argv[2] == "library":
        return U.cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
