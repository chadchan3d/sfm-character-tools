# -*- coding: utf-8 -*-
"""F-01 v1.1.0 RC1 native release smoke (RC1S). Build, preparation, temporary installation, seeding, evidence
collection, restoration and analysis. Python 3, run with -I while SFM is closed (every command that changes a file
refuses while sfm.exe runs). Every command refuses, changing nothing, when a precondition fails.

Unlike every earlier F-01 kit, nothing is derived: the installed CPM and both registries are the exact RC1 production
files, taken from the pinned unsigned RC1 package and verified against the repository. No observer or capture script
runs in SFM; the evidence is the CPM's own diagnostic log, the saved records, the restoration and the Owner's record.

Reused unchanged (through the UA-1 kit's tool, as the H1 kit does): K2's pre (a verified copy of the R2 fixture,
RC1_SOURCE.dmx, and of S3's prepared destination, RC1_DESTINATION.dmx), the S3 tool's install, collect-logs and
restore (four protected inventories, backups of the published CPM, housekeeping and .pyc files, an installation
journal written first), UA-1's whole-library backup, seed (K2 Pose and NQ1 Pose A) and exact files-and-folders
cleanup.

Own commands:
  build         verify the kit pins and the RC1 package; extract its CPM and both registries; require them to equal the
                pins and the repository; record the production-mode equivalence check (rc1s_modes); stage them with
                Q/staged/IDENTITIES.json
  pre           verify the seeded records and Krystal's Body preset are the pinned files; K2's pre; the library backup
  check         report the installation state (published | rc1 | other)
  library TAG   read-only: every preset-library file that differs from the pre-run library
  restore       UA-1's library cleanup (the run's records are kept in Q/evidence/library_after), then the S3 restore
  analyze       run tools/rc1s_analyze.py (Q/evidence/RC1S_VERDICT.json and RC1S_VERDICT.md)

usage: python -I rc1s_tool.py RC1S.json build | pre | status | install | seed | check | library TAG | collect-logs |
                                       restore | analyze
"""
from __future__ import print_function

import hashlib
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "..", "f01_ui_acceptance", "tools"))
sys.path.insert(0, HERE)
import ua_tool as U  # noqa: E402
import rc1s_modes  # noqa: E402

S, K, T = U.S, U.K, U.T
FORMAT = "F01-RC1S-config-v1"
SOURCE = "RC1_SOURCE.dmx"
DESTINATION = "RC1_DESTINATION.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SOURCE,)
S.DESTINATION = DESTINATION
U.SOURCE, U.DESTINATION = SOURCE, DESTINATION
K.SOURCE, K.DESTINATION = SOURCE, DESTINATION
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "rc1s_analyze.py")

ZIP_ENTRIES = (
    ("usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py", "SFM_Character_Preset_Manager.py",
     "CANDIDATE", "rc1_cpm_sha256"),
    ("usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json", "cpm_pose_profiles_v1.json",
     "PROFILE", "profile_sha256"),
    ("usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json", "cpm_body_profiles_v1.json",
     "BODY_PROFILE", "body_profile_sha256"),
)


def kit_files(c):
    return ((K.comparator(), "analyzer_sha256"), (os.path.join(HERE, "rc1s_modes.py"), "modes_sha256"),
            (os.path.join(KIT, "PROCEDURE.md"), "procedure_sha256"))


def body_preset(c):
    return os.path.join(S.p(c, "LIBRARY"), "Characters", c["character_dir"], "Body Presets", S.p(c, "BODY_PRESET"))


def cmd_build(c):
    problems = ["%s is not the pinned %s" % (path, c["pins"][pin]) for path, pin in kit_files(c)
                if T.sha(path) != c["pins"][pin]]
    if T.sha(S.observer(c)) != c["pins"]["observer_sha256"]:
        problems.append("the S0 observer is not the pinned %s" % c["pins"]["observer_sha256"])
    zpath = S.p(c, "RC_ZIP")
    if not os.path.isfile(zpath) or T.sha(zpath) != c["pins"]["rc1_zip_sha256"]:
        problems.append("%s is not the RC1 package %s" % (zpath, c["pins"]["rc1_zip_sha256"]))
    if c["pins"]["qualification_cpm_sha256"] != c["pins"]["rc1_cpm_sha256"]:
        problems.append("the installed build must be the RC1 CPM itself")
    if os.path.exists(S.q(c, "staged")):
        problems.append("%s exists" % S.q(c, "staged"))
    S.refuse(problems, "BUILD")
    blobs = {}
    with zipfile.ZipFile(zpath) as z:
        names = set(z.namelist())
        for entry, out, repo_key, pin in ZIP_ENTRIES:
            if entry not in names:
                problems.append("the package has no %s" % entry)
                continue
            data = z.read(entry)
            if hashlib.sha256(data).hexdigest() != c["pins"][pin]:
                problems.append("%s in the package is not %s" % (entry, c["pins"][pin]))
            if T.sha(S.p(c, repo_key)) != c["pins"][pin]:
                problems.append("the repository's %s is not %s" % (S.p(c, repo_key), c["pins"][pin]))
            blobs[out] = data
    S.refuse(problems, "BUILD")
    cpm = blobs["SFM_Character_Preset_Manager.py"]
    if cpm.count(S.MODE_PRODUCTION) != 1 or S.MODE_QUALIFICATION in cpm:
        S.refuse(["the RC1 CPM does not hold exactly one production registry-mode line"], "BUILD")
    for template, pin in zip(S.REGISTRY_CONSTANTS, ("profile_sha256", "body_profile_sha256")):
        if cpm.count(template % c["pins"][pin].encode("ascii")) != 1:
            S.refuse(["the RC1 CPM does not pin registry %s" % c["pins"][pin]], "BUILD")
    modes = rc1s_modes.check(cpm, json.loads(blobs["cpm_pose_profiles_v1.json"].decode("utf-8")),
                             json.loads(blobs["cpm_body_profiles_v1.json"].decode("utf-8")),
                             c["pins"]["profile_sha256"], c["pins"]["body_profile_sha256"])
    if not modes["pass"]:
        print(json.dumps(modes, indent=1))
        S.refuse(["the production-mode equivalence check failed"], "BUILD")
    staged = S.q(c, "staged")
    os.makedirs(staged)
    for out, data in blobs.items():
        with open(os.path.join(staged, out), "wb") as f:
            f.write(data)
    ids = {"installed_build": "RC1 production CPM, unmodified (no qualification derivation)",
           "rc1_zip_sha256": c["pins"]["rc1_zip_sha256"],
           "candidate_cpm_sha256": c["pins"]["rc1_cpm_sha256"],
           "qualification_cpm_sha256": T.sha(os.path.join(staged, "SFM_Character_Preset_Manager.py")),
           "profile_sha256": T.sha(os.path.join(staged, "cpm_pose_profiles_v1.json")),
           "body_profile_sha256": T.sha(os.path.join(staged, "cpm_body_profiles_v1.json")),
           "observer_sha256": T.sha(S.observer(c)), "wrapper_sha256": T.sha(S.wrapper(c)),
           "ui_smoke_sha256": T.sha(S.ui_smoke(c)), "analyzer_sha256": T.sha(K.comparator()),
           "mode_equivalence": modes}
    T.write_json(os.path.join(staged, "IDENTITIES.json"), ids, exclusive=True)
    print(json.dumps(ids, indent=1))
    print("BUILT: the RC1 production CPM %s and both registries, unmodified from the package; production-mode "
          "equivalence PASS" % ids["qualification_cpm_sha256"])


def cmd_pre(c):
    problems = []
    for key, pin in (("K2_POSE", "k2_pose_sha256"), ("LEGACY_POSE", "legacy_pose_sha256")):
        if not os.path.isfile(S.p(c, key)) or T.sha(S.p(c, key)) != c["pins"][pin]:
            problems.append("%s is not %s" % (S.p(c, key), c["pins"][pin]))
    if not os.path.isfile(body_preset(c)) or T.sha(body_preset(c)) != c["pins"]["body_preset_sha256"]:
        problems.append("%s is not the pinned Body record %s" % (body_preset(c), c["pins"]["body_preset_sha256"]))
    if os.path.exists(S.q(c, "pre_run")):
        problems.append("%s exists" % S.q(c, "pre_run"))
    S.refuse(problems, "PRE")
    K.cmd_pre(c)
    result = U.backup_library(c)
    print("PRE PASS (RC1S): preset library backed up (%d files, %d folders). Next: install, check, seed" % (
        result["files"], len(result["folders"])))


def cmd_check(c):
    st, cpm = S.state(c)
    label = {"published": "published", "qualification": "rc1"}.get(st, "other")
    print(json.dumps({"installation": label, "installed_cpm_sha256": cpm,
                      "registries_present": dict((k, os.path.lexists(v)) for k, v in S.targets(c).items())},
                     indent=1))
    return 0 if label in ("published", "rc1") else 1


def cmd_analyze(c):
    import rc1s_analyze
    return rc1s_analyze.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": S.cmd_status, "install": S.cmd_install,
                "seed": U.cmd_seed, "check": cmd_check, "collect-logs": S.cmd_collect_logs,
                "restore": U.cmd_restore, "analyze": cmd_analyze}
    if len(argv) == 4 and argv[2] == "library":
        return U.cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
