# -*- coding: utf-8 -*-
"""F-01 SFP-1 NQ-S6 (procedural-state evidence): preparation, post-run verification and the offline analysis.
Python 3, run with -I while SFM is closed. Nothing is installed: the published CPM stays in place and is not opened.

The model survey's tool (f01_model_survey/tools/mc_tool.py) is reused unchanged for pre, status and post (SFM closed,
published CPM with no registry beside it, pinned kit, model and rig-script hashes, the four protected inventories,
housekeeping and .pyc backups and their restoration); only its kit is this observer. Added:
  copy     copy the preserved survey session (Q_SURVEY/sessions/saved_by_operator/mc_survey.dmx, SHA-256 pinned) to
           Q/session_copy/NQ_SURVEY.dmx, verified byte-identical; the original is only read
  post     mc_tool post, then the preserved original must still be its pinned bytes (evidence/session_check.json)
  analyze  nq_analyze.py on Q/observations into Q/evidence (NQ_S6_ANALYSIS.json, NQ_S6_ANALYSIS.md)

usage: python -I nq_tool.py NQ.json pre | copy | status | post | analyze
"""
from __future__ import print_function

import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SURVEY_TOOLS = os.path.join(HERE, "..", "..", "f01_model_survey", "tools")
sys.path.insert(0, SURVEY_TOOLS)
sys.path.insert(0, HERE)
import mc_tool as M  # noqa: E402

SESSION_SHA256 = "47f6b9a047b024625873e35576918138dc19e85967cde80481e75ced8e161f01"
SESSION_REL = os.path.join("sessions", "saved_by_operator", "mc_survey.dmx")


def kit_files(c):
    root = os.path.join(M.p(c, "REPO"), "real_sfm_qualification")
    return {"wrapper": os.path.join(root, "f01_nq_s6", "observer", "F01_NQS6_Observe.py"),
            "s0_observer": os.path.join(root, "f01_full_body_s0", "observer", "F01_S0_Survey.py")}


M.kit_files = kit_files                  # the only substitution: this kit's observer is the pinned wrapper


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def original(c):
    return os.path.join(M.p(c, "Q_SURVEY"), SESSION_REL)


def cmd_copy(c):
    q = M.p(c, "Q")
    if not os.path.isfile(os.path.join(q, "pre_run", "pre.json")):
        raise SystemExit("REFUSED: run pre first")
    src = original(c)
    if not os.path.isfile(src) or sha(src) != SESSION_SHA256:
        raise SystemExit("REFUSED: the preserved survey session is missing or not its pinned bytes")
    dst_dir = os.path.join(q, "session_copy")
    dst = os.path.join(dst_dir, "NQ_SURVEY.dmx")
    if os.path.exists(dst_dir):
        raise SystemExit("REFUSED: %s exists; copy never runs twice" % dst_dir)
    os.makedirs(dst_dir)
    shutil.copyfile(src, dst)
    with open(src, "rb") as a, open(dst, "rb") as b:
        if a.read() != b.read() or sha(dst) != SESSION_SHA256:
            raise SystemExit("COPY FAIL: the copy is not byte-identical")
    print("COPY PASS: %s (%s). Open this copy in SFM; never save it." % (dst, SESSION_SHA256))


def cmd_post(c):
    code = M.cmd_post(c)
    q = M.p(c, "Q")
    src = original(c)
    check = {"original": src, "sha256": sha(src) if os.path.isfile(src) else None, "pinned": SESSION_SHA256,
             "session_copy": sorted(os.listdir(os.path.join(q, "session_copy")))
             if os.path.isdir(os.path.join(q, "session_copy")) else None}
    check["pass"] = check["sha256"] == SESSION_SHA256
    M.T.write_json(os.path.join(q, "evidence", "session_check.json"), check, exclusive=True)
    print(json.dumps(check, indent=1))
    print("SESSION CHECK PASS: the preserved survey session is unchanged" if check["pass"] else
          "SESSION CHECK FAIL: the preserved survey session changed; report it")
    return 0 if code == 0 and check["pass"] else 1


def cmd_analyze(c):
    import nq_analyze
    q = M.p(c, "Q")
    return nq_analyze.main(["nq_analyze.py", os.path.join(q, "observations"), os.path.join(q, "evidence")])


def main(argv):
    commands = {"pre": M.cmd_pre, "copy": cmd_copy, "status": M.cmd_status, "post": cmd_post, "analyze": cmd_analyze}
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    c = M.load(argv[1])
    return commands[argv[2]](c) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
