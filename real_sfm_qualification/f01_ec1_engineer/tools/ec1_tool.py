# -*- coding: utf-8 -*-
"""F-01 EC-1 Engineer control coverage: preparation, post-run verification and the offline analysis. Python 3, run
with -I while SFM is closed. Nothing is installed: the published CPM stays in place and is not opened.

The model survey's tool (f01_model_survey/tools/mc_tool.py) is reused unchanged for pre, status and post: SFM closed;
the published CPM with no registry beside it; the pinned kit files; the model's hash recorded; the four protected
inventories; housekeeping and .pyc backups and their restoration; Q/sessions created for the disposable session and
required to be empty afterwards (it is never saved). Only this kit's files are substituted (the composed observer,
the three observers it composes, and the expected header). Added around it:
  model identity  before pre and status, and after post: models/player/engineer.mdl must resolve, through usermod's
                  gameinfo search paths (first loose file wins; f01_nq03's resolver), to the configured file, whose
                  bytes must equal the pin taken from NQ-03 (evidence/model_check.json after post)
  analyze         ec1_analyze.py on Q/observations into Q/evidence with the pinned expected header

usage: python -I ec1_tool.py EC1.json pre | status | post | analyze
"""
from __future__ import print_function

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "..", "f01_nq03", "tools"))
sys.path.insert(0, os.path.join(KIT, "..", "f01_model_survey", "tools"))
sys.path.insert(0, HERE)
import mc_tool as M  # noqa: E402
import nq03_tool as R  # noqa: E402  (only its search_paths resolver is used)

MODEL = "models/player/engineer.mdl"


def kit_files(c):
    root = os.path.join(M.p(c, "REPO"), "real_sfm_qualification")
    return {"wrapper": os.path.join(root, "f01_ec1_engineer", "observer", "F01_EC1_Observe.py"),
            "s0_observer": os.path.join(root, "f01_full_body_s0", "observer", "F01_S0_Survey.py"),
            "mc_observer": os.path.join(root, "f01_model_survey", "observer", "F01_MC_Observe.py"),
            "nq_observer": os.path.join(root, "f01_nq_s6", "observer", "F01_NQS6_Observe.py"),
            "expected_header": os.path.join(root, "f01_ec1_engineer", "engineer_header.json")}


M.kit_files = kit_files                  # the only substitution in the reused tool: this kit's pinned files


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def model_check(c):
    """The model SFM will load: first loose file in usermod's search order, its bytes equal to the NQ-03 pin."""
    game = M.p(c, "GAME")
    order = R.search_paths(game)
    hit = None
    for folder in order:
        path = os.path.join(game, folder, MODEL.replace("/", os.sep))
        if os.path.isfile(path):
            hit = "%s/%s" % (folder, MODEL)
            break
    problems = []
    if c.get("models") != [hit] or hit is None:
        problems.append("%s resolves to %s, not the configured %s" % (MODEL, hit, c.get("models")))
    digest = sha(M.game_file(c, hit)) if hit else None
    pin = (c.get("model_pins") or {}).get(hit)
    if pin is None or digest != pin:
        problems.append("%s is %s, not the pinned %s" % (hit, digest, pin))
    return {"model": MODEL, "resolved": hit, "sha256": digest, "pinned": pin, "search_paths": order,
            "problems": problems, "pass": not problems}


def cmd_pre(c):
    check = model_check(c)
    if not check["pass"]:
        print(json.dumps(check["problems"], indent=1))
        raise SystemExit("PRE NOT PERFORMED (nothing was changed)")
    print("MODEL PASS: %s (%s)" % (check["resolved"], check["sha256"]))
    return M.cmd_pre(c)


def cmd_status(c):
    check = model_check(c)
    if not check["pass"]:
        print(json.dumps(check["problems"], indent=1))
        print("STATUS NOT FRESH: the model identity check failed")
        return 1
    return M.cmd_status(c)


def cmd_post(c):
    code = M.cmd_post(c)
    check = model_check(c)
    M.T.write_json(os.path.join(M.p(c, "Q"), "evidence", "model_check.json"), check, exclusive=True)
    print("MODEL CHECK PASS: %s is unchanged" % check["resolved"] if check["pass"] else
          "MODEL CHECK FAIL: %s" % check["problems"])
    return 0 if code == 0 and check["pass"] else 1


def cmd_analyze(c):
    import ec1_analyze
    q = M.p(c, "Q")
    return ec1_analyze.main(["ec1_analyze.py", os.path.join(q, "observations"), os.path.join(q, "evidence"),
                             kit_files(c)["expected_header"]])


def main(argv):
    commands = {"pre": cmd_pre, "status": cmd_status, "post": cmd_post, "analyze": cmd_analyze}
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    c = M.load(argv[1])
    return commands[argv[2]](c) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
