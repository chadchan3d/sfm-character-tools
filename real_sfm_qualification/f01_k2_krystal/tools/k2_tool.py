# -*- coding: utf-8 -*-
"""F-01 K2: Krystal version 2 Full body native integration check (Blueprint R4 sections 5 and 12). Build, preparation,
temporary installation, the pre-Apply check, evidence collection and restoration. Python 3, run with -I while SFM is
closed (every command that changes a file refuses while sfm.exe runs; `precheck` only reads and may run while SFM is
open). Every command refuses, changing nothing, when a precondition fails.

The full-body S3 kit's tool (f01_full_body_s3/tools/s3_tool.py) is reused unchanged for pre, status, install, check,
library, collect-logs and restore (SFM closed, the published installation, the pinned R2 fixture and observer, four
protected inventories, backups of the published CPM, housekeeping and .pyc files, an installation journal written
first, verified copies, the run's Poses folder moved into evidence, every inventory equal to its baseline). The S3
observer wrapper (F01_S3_Observe.py) and UI smoke check (F01_S3_UISmoke.py) are reused unchanged; only this kit's
identity is substituted (configuration format, session names, comparator).

Own commands:
  build     derive the K1 qualification CPM from the pinned candidate (exactly one line differs:
            PROD_POSE_REGISTRY_MODE = u"qualification") and require the pinned qualification build; stage it with both
            pinned registries; write Q/staged/IDENTITIES.json
  pre       S3 pre (K2_SOURCE.dmx: a verified copy of the R2 fixture), then a verified copy of S3's prepared
            destination session (pinned in S3 run 1, natively compatible and posed differently) as K2_DESTINATION.dmx,
            pinned in Q/evidence/destination.json
  precheck  read-only, after B1 (SFM may stay open): the staged qualification CPM's own revised A1 compatibility check
            of the B1 observation against K2 Pose (s3_precheck, unchanged) and the visible difference between them;
            writes Q/evidence/K2_PRECHECK.json. Apply only when COMPATIBLE and DISTINCT.
  compare   run tools/k2_compare.py (Q/evidence/K2_VERDICT.json and K2_VERDICT.md)

usage: python -I k2_tool.py K2.json build | pre | status | install | check | library TAG | precheck |
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
S3_TOOLS = os.path.join(KIT, "..", "f01_full_body_s3", "tools")
S3_OBSERVER = os.path.join(KIT, "..", "f01_full_body_s3", "observer")
sys.path.insert(0, S3_TOOLS)
sys.path.insert(0, HERE)
import s3_tool as S  # noqa: E402

T = S.T
FORMAT = "F01-K2-config-v1"
SOURCE = "K2_SOURCE.dmx"
DESTINATION = "K2_DESTINATION.dmx"
POSE = u"K2 Pose"

# The only substitutions in the reused tool: this kit's identity. The S3 observer wrapper and UI smoke check are
# used unchanged (their step table and outputs fit K2: Process A at shot15 0.2083 s, Process B at shot13 0.3750 s).
S.FORMAT = FORMAT
S.SESSIONS = (SOURCE,)
S.DESTINATION = DESTINATION
S.tools_dir = lambda c: KIT
S.wrapper = lambda c: os.path.join(S3_OBSERVER, "F01_S3_Observe.py")
S.ui_smoke = lambda c: os.path.join(S3_OBSERVER, "F01_S3_UISmoke.py")


def comparator():
    return os.path.join(HERE, "k2_compare.py")


def cmd_build(c):
    problems = []
    if T.sha(S.p(c, "CANDIDATE")) != c["pins"]["candidate_cpm_sha256"]:
        problems.append("the candidate CPM is not %s" % c["pins"]["candidate_cpm_sha256"])
    for key, pin in (("PROFILE", "profile_sha256"), ("BODY_PROFILE", "body_profile_sha256")):
        if T.sha(S.p(c, key)) != c["pins"][pin]:
            problems.append("%s is not the pinned registry %s" % (S.p(c, key), c["pins"][pin]))
    if T.sha(S.observer(c)) != c["pins"]["observer_sha256"]:
        problems.append("the S0 observer is not the pinned %s" % c["pins"]["observer_sha256"])
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
    import hashlib
    if hashlib.sha256(qual).hexdigest() != c["pins"]["qualification_cpm_sha256"]:
        S.refuse(["the derived qualification CPM is not the pinned %s" % c["pins"]["qualification_cpm_sha256"]],
                 "BUILD")
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
    T.write_json(os.path.join(staged, "IDENTITIES.json"), ids, exclusive=True)
    print(json.dumps(ids, indent=1))
    print("BUILT: the K1 qualification CPM %s differs from the candidate in line %d only"
          % (ids["qualification_cpm_sha256"], ids["changed_line"]))


def destination_source(c):
    return os.path.join(S.p(c, "S3_RUN1"), "sessions", "S3_DESTINATION.dmx")


def cmd_pre(c):
    problems = []
    src = destination_source(c)
    if not os.path.isfile(src) or T.sha(src) != c["pins"]["destination_sha256"]:
        problems.append("S3's prepared destination %s is not %s" % (src, c["pins"]["destination_sha256"]))
    if os.path.normcase(os.path.abspath(S.p(c, "S3_RUN1"))) == os.path.normcase(os.path.abspath(S.p(c, "Q"))):
        problems.append("the S3 run folder cannot be this run folder")
    S.refuse(problems, "PRE")
    S.cmd_pre(c)
    T.copy_verified(src, S.q(c, "sessions", DESTINATION), c["pins"]["destination_sha256"])
    T.write_json(S.q(c, "evidence", "destination.json"),
                 {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "destination_sha256": c["pins"]["destination_sha256"],
                  "copied_from": "S3 run 1 (S3_DESTINATION.dmx, read only)", "pass": True}, exclusive=True)
    print("PRE PASS (K2): %s (R2 fixture) and %s (S3's prepared destination %s) in place. Next: install"
          % (SOURCE, DESTINATION, c["pins"]["destination_sha256"][:12]))


def k2_records(c):
    d = S.poses_dir(c)
    return [n for n in (sorted(os.listdir(d)) if os.path.isdir(d) else [])
            if n.startswith(POSE + u"--") and n.endswith(".json")]


def cmd_precheck(c):
    import s3_precheck
    import s3_compare
    ids = S.identities(c)
    staged = S.q(c, "staged", "SFM_Character_Preset_Manager.py")
    problems = []
    if ids is None or T.sha(staged) != ids["qualification_cpm_sha256"] or \
            ids["qualification_cpm_sha256"] != c["pins"]["qualification_cpm_sha256"]:
        problems.append("the staged qualification CPM does not verify")
    obs = S.q(c, "observations", "S0-08.json")
    if not os.path.isfile(obs) or not os.path.isfile(S.q(c, "observations", "S0-08.s3.json")):
        problems.append("observe B1 first")
    records = k2_records(c)
    if len(records) != 1:
        problems.append("%s is not in the run's Poses folder exactly once (%s)" % (POSE, records))
    out = S.q(c, "evidence", "K2_PRECHECK.json")
    a1 = S.q(c, "evidence", "A1_PRECHECK.json")
    for path in (out, a1):
        if os.path.lexists(path):
            problems.append("%s exists" % path)
    S.refuse(problems, "PRECHECK")
    record_path = os.path.join(S.poses_dir(c), records[0])
    code = s3_precheck.main(["s3_precheck", staged, obs, record_path, a1])
    compat = T.read_json(a1) if os.path.isfile(a1) else {}
    region = T.read_json(record_path)["pose"]["regions"]["full_body"]
    R = s3_compare.Run.__new__(s3_compare.Run)
    reg = T.read_json(S.q(c, "staged", "cpm_body_profiles_v1.json"))
    profile = list(reg["profiles"].values())[0] if isinstance(reg["profiles"], dict) else reg["profiles"][0]
    R.unposed = set(profile["preserved_fk_bones"]) | set(profile["passive_channel_bones"])
    groups = s3_compare.Run.distinct_groups(R, region, T.read_json(obs))
    visible = sorted(g for g in s3_compare.REQUIRED_GROUPS if groups.get(g, 0.0) >= s3_compare.VISIBLE_DEGREES)
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "compatible": compat.get("compatible") is True,
              "visible_groups": visible, "group_degrees": dict((g, round(v, 2)) for g, v in groups.items()),
              "distinct": len(visible) >= 2, "record": records[0], "s3_precheck_exit": code}
    result["apply_allowed"] = result["compatible"] and result["distinct"]
    T.write_json(out, result, exclusive=True)
    print(json.dumps(result, indent=1))
    print("PRECHECK: %s" % ("COMPATIBLE and DISTINCT - continue with Apply" if result["apply_allowed"] else
                            "STOP - do not Apply (%s)" % ("incompatible" if not result["compatible"] else
                                                          "not visibly different")))
    return 0 if result["apply_allowed"] else 1


def cmd_compare(c):
    import k2_compare
    return k2_compare.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": S.cmd_status, "install": S.cmd_install,
                "check": S.cmd_check, "precheck": cmd_precheck, "collect-logs": S.cmd_collect_logs,
                "restore": S.cmd_restore, "compare": cmd_compare}
    if len(argv) == 4 and argv[2] == "library":
        return S.cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
