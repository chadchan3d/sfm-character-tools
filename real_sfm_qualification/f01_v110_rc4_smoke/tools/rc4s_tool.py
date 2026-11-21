# -*- coding: utf-8 -*-
"""F-01 v1.1.0 RC4 native release smoke (RC4S): Fox Full body and the Tails cross-rig transfer in a normal installation. Build, preparation,
temporary installation, evidence collection, restoration and analysis. Python 3, run with -I while SFM is closed
(every command that changes a file refuses while sfm.exe runs). Every command refuses, changing nothing, when a
precondition fails.

As in RC1S, nothing is derived: the installed CPM and both registries are the exact RC4 production files, taken from
the pinned unsigned RC4 package and verified against the repository. No observer or capture script runs in SFM; the
evidence is the CPM's own diagnostic log, the saved records, the restoration and the Owner's record.

Reused unchanged (through the RC1S kit's tool and the UA-1, K2 and S3 tools it reuses): K2's pre (a verified copy of
the R2 fixture as RC4_SESSION.dmx, the one disposable session, never saved; a verified copy of S3's destination as
RC4_SPARE.dmx, never opened), the S3 tool's install, collect-logs and restore (four protected inventories, backups of
the published CPM, housekeeping and .pyc files, an installation journal written first), UA-1's whole-library backup,
library differences and exact files-and-folders cleanup.

Own commands:
  build    verify the kit pins and the RC4 package; extract its CPM and both registries; require them to equal the
           pins and the repository; record the production-mode check (rc3s_modes from the RC3 smoke kit, unchanged:
           RC1's checks plus the structural adapter usable in production); stage them with Q/staged/IDENTITIES.json
  pre      K2's pre, then the library backup (nothing is seeded)
  check    report the installation state (published | rc4 | other)
  analyze  run tools/rc4s_analyze.py (Q/evidence/RC4S_VERDICT.json and RC4S_VERDICT.md)

usage: python -I rc4s_tool.py RC4S.json build | pre | status | install | check | library TAG | collect-logs |
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
sys.path.insert(0, os.path.join(KIT, "..", "f01_v110_rc1_smoke", "tools"))
sys.path.insert(0, os.path.join(KIT, "..", "f01_v110_rc3_smoke", "tools"))
sys.path.insert(0, HERE)
import rc1s_tool as R1  # noqa: E402
import rc3s_modes  # noqa: E402  (the RC3 smoke kit's production-mode check, unchanged)

U, S, K, T = R1.U, R1.S, R1.K, R1.T
FORMAT = "F01-RC4S-config-v1"
SESSION = "RC4_SESSION.dmx"
SPARE = "RC4_SPARE.dmx"
S.FORMAT = FORMAT
S.SESSIONS = (SESSION,)
S.DESTINATION = SPARE
U.SOURCE, U.DESTINATION = SESSION, SPARE
K.SOURCE, K.DESTINATION = SESSION, SPARE
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "rc4s_analyze.py")

ZIP_ENTRIES = (
    ("usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py", "SFM_Character_Preset_Manager.py",
     "CANDIDATE", "rc4_cpm_sha256"),
    ("usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json", "cpm_pose_profiles_v1.json",
     "PROFILE", "profile_sha256"),
    ("usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json", "cpm_body_profiles_v1.json",
     "BODY_PROFILE", "body_profile_sha256"),
)


def kit_files(c):
    return ((K.comparator(), "analyzer_sha256"), (os.path.abspath(rc3s_modes.__file__), "modes_sha256"),
            (os.path.join(KIT, "PROCEDURE.md"), "procedure_sha256"))


def cmd_build(c):
    problems = ["%s is not the pinned %s" % (path, c["pins"][pin]) for path, pin in kit_files(c)
                if T.sha(path) != c["pins"][pin]]
    if T.sha(S.observer(c)) != c["pins"]["observer_sha256"]:
        problems.append("the S0 observer is not the pinned %s" % c["pins"]["observer_sha256"])
    zpath = S.p(c, "RC_ZIP")
    if not os.path.isfile(zpath) or T.sha(zpath) != c["pins"]["rc4_zip_sha256"]:
        problems.append("%s is not the RC4 package %s" % (zpath, c["pins"]["rc4_zip_sha256"]))
    if c["pins"]["qualification_cpm_sha256"] != c["pins"]["rc4_cpm_sha256"]:
        problems.append("the installed build must be the RC4 CPM itself")
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
        S.refuse(["the RC4 CPM does not hold exactly one production registry-mode line"], "BUILD")
    for template, pin in zip(S.REGISTRY_CONSTANTS, ("profile_sha256", "body_profile_sha256")):
        if cpm.count(template % c["pins"][pin].encode("ascii")) != 1:
            S.refuse(["the RC4 CPM does not pin registry %s" % c["pins"][pin]], "BUILD")
    modes = rc3s_modes.check(cpm, json.loads(blobs["cpm_pose_profiles_v1.json"].decode("utf-8")),
                             json.loads(blobs["cpm_body_profiles_v1.json"].decode("utf-8")),
                             c["pins"]["profile_sha256"], c["pins"]["body_profile_sha256"])
    if not modes["pass"]:
        print(json.dumps(modes, indent=1))
        S.refuse(["the production-mode check failed"], "BUILD")
    staged = S.q(c, "staged")
    os.makedirs(staged)
    for out, data in blobs.items():
        with open(os.path.join(staged, out), "wb") as f:
            f.write(data)
    ids = {"installed_build": "RC4 production CPM, unmodified (no qualification derivation)",
           "rc4_zip_sha256": c["pins"]["rc4_zip_sha256"],
           "candidate_cpm_sha256": c["pins"]["rc4_cpm_sha256"],
           "qualification_cpm_sha256": T.sha(os.path.join(staged, "SFM_Character_Preset_Manager.py")),
           "profile_sha256": T.sha(os.path.join(staged, "cpm_pose_profiles_v1.json")),
           "body_profile_sha256": T.sha(os.path.join(staged, "cpm_body_profiles_v1.json")),
           "observer_sha256": T.sha(S.observer(c)), "wrapper_sha256": T.sha(S.wrapper(c)),
           "ui_smoke_sha256": T.sha(S.ui_smoke(c)), "analyzer_sha256": T.sha(K.comparator()),
           "mode_equivalence": modes}
    T.write_json(os.path.join(staged, "IDENTITIES.json"), ids, exclusive=True)
    print(json.dumps(ids, indent=1))
    print("BUILT: the RC4 production CPM %s and both registries, unmodified from the package; production-mode "
          "check PASS (structural adapter usable in production)" % ids["qualification_cpm_sha256"])


def cmd_pre(c):
    if os.path.exists(S.q(c, "pre_run")):
        S.refuse(["%s exists" % S.q(c, "pre_run")], "PRE")
    K.cmd_pre(c)
    result = U.backup_library(c)
    print("PRE PASS (RC4S): %s is a verified copy of the R2 fixture; preset library backed up (%d files, %d folders). "
          "Next: install, then check (there is no seed step)" % (SESSION, result["files"], len(result["folders"])))


def cmd_check(c):
    st, cpm = S.state(c)
    label = {"published": "published", "qualification": "rc4"}.get(st, "other")
    print(json.dumps({"installation": label, "installed_cpm_sha256": cpm,
                      "registries_present": dict((k, os.path.lexists(v)) for k, v in S.targets(c).items())},
                     indent=1))
    return 0 if label in ("published", "rc4") else 1


def cmd_analyze(c):
    import rc4s_analyze
    return rc4s_analyze.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": S.cmd_status, "install": S.cmd_install,
                "check": cmd_check, "collect-logs": S.cmd_collect_logs, "restore": U.cmd_restore,
                "analyze": cmd_analyze}
    if len(argv) == 4 and argv[2] == "library":
        return U.cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
