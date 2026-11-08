# -*- coding: utf-8 -*-
"""F-01 SFP-1 Selected parts native qualification: build, preparation, temporary installation, evidence collection
and restoration. Python 3, run with -I while SFM is closed (every command that changes a file refuses while sfm.exe
runs). Every command refuses, changing nothing, when a precondition fails.

The full-body S3 kit's tool (f01_full_body_s3/tools/s3_tool.py) is reused unchanged for pre, status, install, seed,
check, library, collect-logs and restore (SFM closed, published installation, pinned fixture, observer and legacy
pose, four protected inventories, backups of the published CPM, housekeeping and .pyc files, an installation journal
written first, verified copies, the run's Poses folder moved into evidence, every inventory equal to its baseline).
Only this kit's identity is substituted: its configuration format, session names, observer wrapper and UI capture.
Own commands:
  build    derive the qualification CPM from the pinned candidate (exactly one line differs:
           PROD_POSE_REGISTRY_MODE = u"qualification"); stage it with both pinned registries; write
           Q/staged/IDENTITIES.json (candidate, qualification build, registries, S0 observer, wrapper, UI capture,
           comparator)
  inspect  read-only, after preparation step 0: pin Q/sessions/SFP1_DESTINATION.dmx and, when prepared, the optional
           SFP1_PROP.dmx (both saved by the Owner); the two fixture copies must be unchanged
  compare  run tools/sfp1_compare.py on this run (Q/evidence/SFP1_VERDICT.json and SFP1_VERDICT.md)

usage: python -I sfp1_tool.py SFP1.json build | pre | status | inspect | install | seed | check | library TAG |
                                         collect-logs | restore | compare
"""
from __future__ import print_function

import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "..", "f01_full_body_s3", "tools"))
sys.path.insert(0, HERE)
import s3_tool as S  # noqa: E402

T = S.T
FORMAT = "F01-SFP1-config-v1"
SESSIONS = ("SFP1_SOURCE.dmx", "SFP1_PREPARATION.dmx")
DESTINATION = "SFP1_DESTINATION.dmx"
PROP = "SFP1_PROP.dmx"

# The only substitutions in the reused tool: this kit's identity.
S.FORMAT = FORMAT
S.SESSIONS = SESSIONS
S.DESTINATION = DESTINATION
S.tools_dir = lambda c: KIT
S.wrapper = lambda c: os.path.join(KIT, "observer", "F01_SFP1_Observe.py")
S.ui_smoke = lambda c: os.path.join(KIT, "observer", "F01_SFP1_UIState.py")


def comparator():
    return os.path.join(HERE, "sfp1_compare.py")


def cmd_build(c):
    problems = []
    if T.sha(S.p(c, "CANDIDATE")) != c["pins"]["candidate_cpm_sha256"]:
        problems.append("the candidate CPM is not %s" % c["pins"]["candidate_cpm_sha256"])
    for key, pin in (("PROFILE", "profile_sha256"), ("BODY_PROFILE", "body_profile_sha256")):
        if T.sha(S.p(c, key)) != c["pins"][pin]:
            problems.append("%s is not the pinned registry %s" % (S.p(c, key), c["pins"][pin]))
    if os.path.exists(S.q(c, "staged")):
        problems.append("%s exists" % S.q(c, "staged"))
    S.refuse(problems, "BUILD")
    with open(S.p(c, "CANDIDATE"), "rb") as f:
        raw = f.read()
    for template, pin in zip(S.REGISTRY_CONSTANTS, ("profile_sha256", "body_profile_sha256")):
        if raw.count(template % c["pins"][pin].encode("ascii")) != 1:
            S.refuse(["the candidate does not pin registry %s" % c["pins"][pin]], "BUILD")
    if raw.count(S.MODE_PRODUCTION) != 1 or S.MODE_QUALIFICATION in raw:
        S.refuse(["the candidate does not hold exactly one production registry-mode line"], "BUILD")
    qual = raw.replace(S.MODE_PRODUCTION, S.MODE_QUALIFICATION)
    a, b = raw.split(b"\n"), qual.split(b"\n")
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if len(a) != len(b) or len(diff) != 1:
        S.refuse(["the derivation changed more than one line"], "BUILD")
    if T.sha(S.observer(c)) != c["pins"]["observer_sha256"]:
        S.refuse(["the S0 observer is not the pinned %s" % c["pins"]["observer_sha256"]], "BUILD")
    staged = S.q(c, "staged")
    os.makedirs(staged)
    out = os.path.join(staged, "SFM_Character_Preset_Manager.py")
    with open(out, "wb") as f:
        f.write(qual)
    T.copy_verified(S.p(c, "PROFILE"), os.path.join(staged, "cpm_pose_profiles_v1.json"), c["pins"]["profile_sha256"])
    T.copy_verified(S.p(c, "BODY_PROFILE"), os.path.join(staged, "cpm_body_profiles_v1.json"),
                    c["pins"]["body_profile_sha256"])
    ids = {"candidate_cpm_sha256": c["pins"]["candidate_cpm_sha256"], "qualification_cpm_sha256": T.sha(out),
           "changed_line": diff[0] + 1, "line": b[diff[0]].decode("utf-8"),
           "profile_sha256": c["pins"]["profile_sha256"], "body_profile_sha256": c["pins"]["body_profile_sha256"],
           "observer_sha256": T.sha(S.observer(c)), "wrapper_sha256": T.sha(S.wrapper(c)),
           "ui_smoke_sha256": T.sha(S.ui_smoke(c)), "comparator_sha256": T.sha(comparator())}
    expected = c["pins"].get("qualification_cpm_sha256")
    if expected and ids["qualification_cpm_sha256"] != expected:
        shutil.rmtree(staged)
        S.refuse(["the derived qualification CPM is not the pinned %s" % expected], "BUILD")
    T.write_json(os.path.join(staged, "IDENTITIES.json"), ids, exclusive=True)
    print(json.dumps(ids, indent=1))
    print("BUILT: the qualification CPM differs from the candidate in line %d only" % ids["changed_line"])


def cmd_inspect(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    dest, prop = S.q(c, "sessions", DESTINATION), S.q(c, "sessions", PROP)
    fixture = c["pins"]["r2_fixture_sha256"]
    if not os.path.isfile(dest):
        problems.append("%s does not exist (preparation step 0 saves it)" % dest)
    elif T.sha(dest) == fixture:
        problems.append("%s is byte-identical to the R2 fixture: the destination was not prepared" % dest)
    if os.path.isfile(prop) and (T.sha(prop) == fixture or (os.path.isfile(dest) and T.sha(prop) == T.sha(dest))):
        problems.append("%s is not a separately prepared prop session" % prop)
    for name in SESSIONS:
        if T.sha(S.q(c, "sessions", name)) != fixture:
            problems.append("%s changed (it is never saved)" % name)
    extra = sorted(set(os.listdir(S.q(c, "sessions"))) - set(SESSIONS + (DESTINATION, PROP)))
    if extra:
        problems.append("unexpected files in the sessions folder: %s" % extra)
    if os.path.exists(S.q(c, "evidence", "destination.json")):
        problems.append("the destination was already pinned")
    S.refuse(problems, "INSPECT")
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "destination_sha256": T.sha(dest),
              "prop_sha256": T.sha(prop) if os.path.isfile(prop) else None, "pass": True}
    T.write_json(S.q(c, "evidence", "destination.json"), result, exclusive=True)
    print(json.dumps(result, indent=1))
    print("INSPECTED: the prepared destination%s pinned. Next: install" % (
        " and the prop session are" if result["prop_sha256"] else " is (no prop session: Process C is skipped)"))


def cmd_compare(c):
    import sfp1_compare
    return sfp1_compare.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": S.cmd_pre, "status": S.cmd_status, "inspect": cmd_inspect,
                "install": S.cmd_install, "seed": S.cmd_seed, "check": S.cmd_check,
                "collect-logs": S.cmd_collect_logs, "restore": S.cmd_restore, "compare": cmd_compare}
    if len(argv) == 4 and argv[2] == "library":
        return S.cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
