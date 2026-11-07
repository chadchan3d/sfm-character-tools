# -*- coding: utf-8 -*-
"""F-01 full-body S3 native qualification: build, preparation, temporary installation, evidence collection and
restoration. Python 3, run with -I while SFM is closed (every command that changes a file refuses while sfm.exe runs).
Every command refuses, changing nothing, when a precondition fails. Reuses the Stage D NQ-1 tool's verified helpers
(hashing, verified copies, inventories, the SFM process check).

usage: python -I s3_tool.py S3.json COMMAND
  build         derive the qualification CPM from the pinned candidate (exactly one line differs:
                PROD_POSE_REGISTRY_MODE = u"qualification"); stage it with both pinned registries and write
                Q/staged/IDENTITIES.json (also pins the S3 observer wrapper)
  pre           verify SFM closed, the published installation, the fixture, the observer, the wrapper and the legacy
                pose; record four inventories; back up the published CPM, SFM housekeeping and .pyc files; create the
                session copies S3_SOURCE.dmx and S3_PREPARATION.dmx (verified copies of the R2 fixture)
  status        read-only: is the completed pre still a fresh baseline
  inspect       read-only: after preparation step 0, pin Q/sessions/S3_DESTINATION.dmx (saved by the Owner)
  install       journal first; then install the qualification CPM and both registries (temporary)
  seed          copy the pinned legacy left-arm pose (version 1) into the run's character Poses folder; in a
                continuation run, every pinned record and Process A observation of the source run instead
  precheck      read-only, after B1: the staged qualification CPM's own revised A1 compatibility check on the B1
                observation and S3 Pose A; writes Q/evidence/A1_PRECHECK.json (Apply only when COMPATIBLE)
  check         report the installation state (published | qualification | other)
  library TAG   read-only: hash every file of the run's Poses folder into Q/evidence/library_TAG.json
  collect-logs  copy the CPM log files written since pre into Q/evidence/logs (verified copies; sources untouched)
  restore       put the published CPM back, remove both registries, restore housekeeping and .pyc, move the run's
                Poses folder into Q/evidence/library_poses; verify every inventory equals its pre-run baseline
  compare       run tools/s3_compare.py on this run (writes Q/evidence/S3_VERDICT.json and S3_VERDICT.md)

A continuation run (config section "continuation") starts at Process B: pre copies the source run's pinned
destination session instead of creating fixture copies, inspect verifies that pin, and seed restores the source
run's pinned pose records (including Update Pose's .bak) and Process A observations. The source run is only read.
"""
from __future__ import print_function

import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_stage_d_nq1", "tools"))
sys.path.insert(0, HERE)
import nq1_tool as T  # noqa: E402

FORMAT = "F01-S3-config-v1"
INVENTORIES = ("SCRIPTS_ROOT", "CFG_ROOT", "LIBRARY", "SESSIONS")
SESSIONS = ("S3_SOURCE.dmx", "S3_PREPARATION.dmx")
DESTINATION = "S3_DESTINATION.dmx"
MODE_PRODUCTION = T.MODE_PRODUCTION
MODE_QUALIFICATION = T.MODE_QUALIFICATION
REGISTRY_CONSTANTS = (b'PROD_POSE_REGISTRY_SHA256 = u"%s"\n', b'PROD_BODY_REGISTRY_SHA256 = u"%s"\n')


def load(path):
    with open(path, "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    if c.get("format") != FORMAT:
        raise SystemExit("REFUSED: not an S3 configuration")
    for k, v in list(c["paths"].items()):
        c["paths"][k] = os.path.expandvars(v)
    for k, v in list(c["paths"].items()):
        for _ in range(3):
            for kk, vv in c["paths"].items():
                v = v.replace("{%s}" % kk, vv)
        c["paths"][k] = v
    if any("<" in v for v in c["paths"].values()) or any("<" in v for v in c["pins"].values()):
        raise SystemExit("REFUSED: the configuration still holds placeholders")
    return c


def p(c, key):
    return c["paths"][key]


def q(c, *parts):
    return os.path.join(p(c, "Q"), *parts)


def tools_dir(c):
    return os.path.join(p(c, "REPO"), "real_sfm_qualification", "f01_full_body_s3")


def observer(c):
    return os.path.join(p(c, "REPO"), "real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")


def wrapper(c):
    return os.path.join(tools_dir(c), "observer", "F01_S3_Observe.py")


def mainmenu(c):
    return os.path.join(p(c, "GAME"), "usermod", "scripts", "SFM Character Tools")


def targets(c):
    return {"profile": os.path.join(mainmenu(c), "cpm_pose_profiles_v1.json"),
            "body_profile": os.path.join(mainmenu(c), "cpm_body_profiles_v1.json")}


def poses_dir(c):
    return os.path.join(p(c, "LIBRARY"), "Characters", c["character_dir"], "Poses")


def cont(c):
    return c.get("continuation")


def source_files(c):
    """The continuation's pinned source files: (group, name, path, sha256)."""
    k = cont(c)
    lib = os.path.join(k["source_run"], "evidence", "library_poses", c["character_dir"])
    out = [("destination", DESTINATION, os.path.join(k["source_run"], "sessions", DESTINATION),
            k["destination_sha256"])]
    out += [("records", n, os.path.join(lib, n), d) for n, d in sorted(k["records"].items())]
    out += [("observations", n, os.path.join(k["source_run"], "observations", n), d)
            for n, d in sorted(k["observations"].items())]
    return out


def identities(c):
    path = q(c, "staged", "IDENTITIES.json")
    return T.read_json(path) if os.path.isfile(path) else None


def state(c):
    cpm = T.sha(T.installed(c)) if os.path.isfile(T.installed(c)) else None
    present = dict((k, os.path.lexists(v)) for k, v in targets(c).items())
    ids = identities(c)
    if cpm == c["pins"]["published_cpm_sha256"] and not any(present.values()):
        return "published", cpm
    if ids and cpm == ids["qualification_cpm_sha256"] and all(present.values()) and \
            T.sha(targets(c)["profile"]) == c["pins"]["profile_sha256"] and \
            T.sha(targets(c)["body_profile"]) == c["pins"]["body_profile_sha256"]:
        return "qualification", cpm
    return "other", cpm


def refuse(problems, what):
    if problems:
        print(json.dumps({"problems": problems}, indent=1))
        raise SystemExit("%s NOT PERFORMED (nothing was changed)" % what)


def cmd_build(c):
    problems = []
    if T.sha(p(c, "CANDIDATE")) != c["pins"]["candidate_cpm_sha256"]:
        problems.append("the candidate CPM is not %s" % c["pins"]["candidate_cpm_sha256"])
    for key, pin in (("PROFILE", "profile_sha256"), ("BODY_PROFILE", "body_profile_sha256")):
        if T.sha(p(c, key)) != c["pins"][pin]:
            problems.append("%s is not the pinned registry %s" % (p(c, key), c["pins"][pin]))
    if os.path.exists(q(c, "staged")):
        problems.append("%s exists" % q(c, "staged"))
    refuse(problems, "BUILD")
    with open(p(c, "CANDIDATE"), "rb") as f:
        raw = f.read()
    for template, pin in zip(REGISTRY_CONSTANTS, ("profile_sha256", "body_profile_sha256")):
        if raw.count(template % c["pins"][pin].encode("ascii")) != 1:
            refuse(["the candidate does not pin registry %s" % c["pins"][pin]], "BUILD")
    if raw.count(MODE_PRODUCTION) != 1 or MODE_QUALIFICATION in raw:
        refuse(["the candidate does not hold exactly one production registry-mode line"], "BUILD")
    qual = raw.replace(MODE_PRODUCTION, MODE_QUALIFICATION)
    a, b = raw.split(b"\n"), qual.split(b"\n")
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if len(a) != len(b) or len(diff) != 1:
        refuse(["the derivation changed more than one line"], "BUILD")
    staged = q(c, "staged")
    os.makedirs(staged)
    out = os.path.join(staged, "SFM_Character_Preset_Manager.py")
    with open(out, "wb") as f:
        f.write(qual)
    T.copy_verified(p(c, "PROFILE"), os.path.join(staged, "cpm_pose_profiles_v1.json"), c["pins"]["profile_sha256"])
    T.copy_verified(p(c, "BODY_PROFILE"), os.path.join(staged, "cpm_body_profiles_v1.json"),
                    c["pins"]["body_profile_sha256"])
    ids = {"candidate_cpm_sha256": c["pins"]["candidate_cpm_sha256"], "qualification_cpm_sha256": T.sha(out),
           "changed_line": diff[0] + 1, "line": b[diff[0]].decode("utf-8"),
           "profile_sha256": c["pins"]["profile_sha256"], "body_profile_sha256": c["pins"]["body_profile_sha256"],
           "observer_sha256": T.sha(observer(c)), "wrapper_sha256": T.sha(wrapper(c)),
           "comparator_sha256": T.sha(os.path.join(tools_dir(c), "tools", "s3_compare.py"))}
    if ids["observer_sha256"] != c["pins"]["observer_sha256"]:
        shutil.rmtree(staged)
        refuse(["the S0 observer is not the pinned %s" % c["pins"]["observer_sha256"]], "BUILD")
    T.write_json(os.path.join(staged, "IDENTITIES.json"), ids, exclusive=True)
    print(json.dumps(ids, indent=1))
    print("BUILT: the qualification CPM differs from the candidate in line %d only" % ids["changed_line"])


def cmd_pre(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    ids = identities(c)
    if ids is None:
        problems.append("run build first")
    st, cpm = state(c)
    if st != "published":
        problems.append("the installation is not the published state (CPM %s, registries %s)" % (
            cpm, dict((k, os.path.lexists(v)) for k, v in targets(c).items())))
    if cont(c):
        if os.path.normcase(os.path.abspath(cont(c)["source_run"])) == os.path.normcase(os.path.abspath(p(c, "Q"))):
            problems.append("a continuation run needs its own run folder")
        for group, name, path, digest in source_files(c):
            if not os.path.isfile(path) or T.sha(path) != digest:
                problems.append("source %s %s is missing or not %s" % (group, name, digest))
    elif not os.path.isfile(p(c, "R2_FIXTURE")) or T.sha(p(c, "R2_FIXTURE")) != c["pins"]["r2_fixture_sha256"]:
        problems.append("the R2 fixture is not %s" % c["pins"]["r2_fixture_sha256"])
    if ids and (T.sha(observer(c)) != ids["observer_sha256"] or T.sha(wrapper(c)) != ids["wrapper_sha256"]):
        problems.append("the observer or the S3 wrapper changed after build")
    if not cont(c) and (not os.path.isfile(p(c, "LEGACY_POSE")) or
                        T.sha(p(c, "LEGACY_POSE")) != c["pins"]["legacy_pose_sha256"]):
        problems.append("the legacy pose is not %s" % c["pins"]["legacy_pose_sha256"])
    chars = os.path.join(p(c, "LIBRARY"), "Characters")
    existing = [n for n in (sorted(os.listdir(chars)) if os.path.isdir(chars) else [])
                if os.path.exists(os.path.join(chars, n, "Poses"))]
    if existing:
        problems.append("the preset library already holds Poses folders (%s): stop and report" % existing)
    for d in ("pre_run", "sessions", "observations", "evidence"):
        if os.path.exists(q(c, d)):
            problems.append("%s already exists" % q(c, d))
    refuse(problems, "PRE")
    print("pre: recording backups and four inventories; this takes a few minutes. Wait for PRE PASS.")
    pre_dir = q(c, "pre_run")
    os.makedirs(os.path.join(pre_dir, "backup", "housekeeping"))
    for d in ("sessions", "observations", "evidence"):
        os.makedirs(q(c, d))
    T.copy_verified(T.installed(c), os.path.join(pre_dir, "backup", "SFM_Character_Preset_Manager_published.py"),
                    c["pins"]["published_cpm_sha256"])
    house = {}
    for rel in c["housekeeping"]:
        src = os.path.join(p(c, "GAME"), "usermod", rel)
        if os.path.isfile(src):
            T.copy_verified(src, os.path.join(pre_dir, "backup", "housekeeping", rel.replace("\\", "__")), T.sha(src))
            house[rel] = T.sha(src)
        else:
            house[rel] = None
    pyc = {}
    for d, _, files in os.walk(p(c, "SCRIPTS_ROOT")):
        for name in files:
            if name.endswith(".pyc"):
                src = os.path.join(d, name)
                rel = os.path.relpath(src, p(c, "SCRIPTS_ROOT"))
                dst = os.path.join(pre_dir, "backup", "pyc", rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                T.copy_verified(src, dst, T.sha(src))
                pyc[rel] = T.sha(src)
    if cont(c):
        T.copy_verified(source_files(c)[0][2], q(c, "sessions", DESTINATION), cont(c)["destination_sha256"])
    else:
        for name in SESSIONS:
            T.copy_verified(p(c, "R2_FIXTURE"), q(c, "sessions", name), c["pins"]["r2_fixture_sha256"])
    inv = dict((k, T.inventory(p(c, k))) for k in INVENTORIES)
    for k, v in inv.items():
        with open(os.path.join(pre_dir, "inventory_%s.txt" % k), "w") as f:
            f.write("\n".join(v["rows"]) + "\n")
    T.write_json(os.path.join(pre_dir, "pre.json"), {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"), "at_epoch": time.time(), "installation": "published",
        "installed_cpm_sha256": cpm, "identities": ids, "housekeeping": house, "pyc": pyc,
        "inventories": dict((k, {"files": v["files"], "sha256": v["sha256"]}) for k, v in inv.items()),
        "pass": True}, exclusive=True)
    print("PRE PASS: backups, inventories and the session copies %s are in place. Next: %s"
          % (DESTINATION if cont(c) else ", ".join(SESSIONS), "inspect" if cont(c) else "preparation step 0"))


def cmd_status(c):
    pre_path = q(c, "pre_run", "pre.json")
    if not os.path.isfile(pre_path):
        print("STATUS: no completed pre in %s; run pre" % p(c, "Q"))
        return 1
    pre = T.read_json(pre_path)
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    st, cpm = state(c)
    journal = q(c, "pre_run", "install_journal.json")
    if os.path.isfile(journal):
        problems.append("an installation was started (state %s): this is not a fresh baseline" % st)
    elif st != "published":
        problems.append("the installation is not the published state")
    for d in ("observations", "evidence"):
        if os.listdir(q(c, d)):
            problems.append("%s is not empty: the run has started" % d)
    for k in INVENTORIES:
        if k != "SESSIONS" and T.inventory(p(c, k))["sha256"] != pre["inventories"][k]["sha256"]:
            problems.append("inventory %s differs from the pre baseline" % k)
    print(json.dumps({"pre_at": pre.get("at"), "installation": st, "problems": problems}, indent=1))
    print("STATUS FRESH" if not problems else "STATUS NOT FRESH: report the problems above")
    return 0 if not problems else 1


def cmd_inspect(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    dest = q(c, "sessions", DESTINATION)
    if cont(c):
        if sorted(os.listdir(q(c, "sessions"))) != [DESTINATION] or T.sha(dest) != cont(c)["destination_sha256"]:
            problems.append("the sessions folder is not exactly the pinned %s" % DESTINATION)
        if os.path.exists(q(c, "evidence", "destination.json")):
            problems.append("the destination was already pinned")
        refuse(problems, "INSPECT")
        result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "destination_sha256": T.sha(dest),
                  "continuation_of": cont(c)["source_run"], "pass": True}
        T.write_json(q(c, "evidence", "destination.json"), result, exclusive=True)
        print(json.dumps(result, indent=1))
        print("INSPECTED: the source run's destination is pinned. Next: install")
        return
    if not os.path.isfile(dest):
        problems.append("%s does not exist (preparation step 0 saves it)" % dest)
    elif T.sha(dest) == c["pins"]["r2_fixture_sha256"]:
        problems.append("%s is byte-identical to the R2 fixture: the destination was not prepared" % dest)
    for name in SESSIONS:
        if T.sha(q(c, "sessions", name)) != c["pins"]["r2_fixture_sha256"]:
            problems.append("%s changed (it is never saved)" % name)
    extra = sorted(set(os.listdir(q(c, "sessions"))) - set(SESSIONS + (DESTINATION,)))
    if extra:
        problems.append("unexpected files in the sessions folder: %s" % extra)
    if os.path.exists(q(c, "evidence", "destination.json")):
        problems.append("the destination was already pinned")
    refuse(problems, "INSPECT")
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "destination_sha256": T.sha(dest), "pass": True}
    T.write_json(q(c, "evidence", "destination.json"), result, exclusive=True)
    print(json.dumps(result, indent=1))
    print("INSPECTED: the prepared destination is pinned. Next: install")


def cmd_install(c):
    journal_path = q(c, "pre_run", "install_journal.json")
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    if not os.path.isfile(q(c, "pre_run", "pre.json")):
        problems.append("run pre first")
    if not os.path.isfile(q(c, "evidence", "destination.json")):
        problems.append("run inspect first (preparation step 0)")
    if os.path.exists(journal_path):
        problems.append("an installation was already started: run restore")
    if state(c)[0] != "published":
        problems.append("the installation is not the published state")
    ids = identities(c)
    staged = q(c, "staged")
    if ids is None or T.sha(os.path.join(staged, "SFM_Character_Preset_Manager.py")) != ids["qualification_cpm_sha256"]:
        problems.append("the staged qualification CPM does not verify")
    refuse(problems, "INSTALL")
    journal = {"format": "F01-S3-install-journal-v1", "state": "begun", "at": time.strftime("%Y-%m-%d %H:%M:%S"),
               "cpm": {"path": T.installed(c), "original": c["pins"]["published_cpm_sha256"],
                       "installed": ids["qualification_cpm_sha256"]},
               "registries": dict((k, {"path": v, "original": None, "installed": c["pins"][k + "_sha256"]})
                                  for k, v in targets(c).items())}
    T.write_json(journal_path, journal, exclusive=True)
    T.copy_verified(os.path.join(staged, "SFM_Character_Preset_Manager.py"), T.installed(c),
                    ids["qualification_cpm_sha256"])
    T.copy_verified(os.path.join(staged, "cpm_pose_profiles_v1.json"), targets(c)["profile"],
                    c["pins"]["profile_sha256"])
    T.copy_verified(os.path.join(staged, "cpm_body_profiles_v1.json"), targets(c)["body_profile"],
                    c["pins"]["body_profile_sha256"])
    journal["state"] = "complete" if state(c)[0] == "qualification" else "verification-failed"
    T.write_json(journal_path, journal)
    if journal["state"] != "complete":
        raise SystemExit("INSTALL DOES NOT VERIFY: run restore")
    print("INSTALLED: qualification CPM %s and both registries. Next: seed" % ids["qualification_cpm_sha256"])


def cmd_seed(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    if state(c)[0] != "qualification":
        problems.append("the qualification build is not installed (run install first)")
    if os.path.lexists(poses_dir(c)):
        problems.append("%s already exists" % poses_dir(c))
    if cont(c):
        for group, name, path, digest in source_files(c):
            if not os.path.isfile(path) or T.sha(path) != digest:
                problems.append("source %s %s is missing or not %s" % (group, name, digest))
        if os.listdir(q(c, "observations")):
            problems.append("Q/observations is not empty")
        refuse(problems, "SEED")
        os.makedirs(poses_dir(c))
        for group, name, path, digest in source_files(c)[1:]:
            target = os.path.join(poses_dir(c) if group == "records" else q(c, "observations"), name)
            T.copy_verified(path, target, digest)
        records = dict((n, d) for g, n, _, d in source_files(c) if g == "records")
        result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "poses_dir": poses_dir(c), "files": records,
                  "observations": dict((n, d) for g, n, _, d in source_files(c) if g == "observations"),
                  "continuation_of": cont(c)["source_run"]}
        T.write_json(q(c, "evidence", "seed.json"), result, exclusive=True)
        T.write_json(q(c, "evidence", "library_A.json"), {"at": result["at"], "tag": "A", "files": records,
                                                          "seeded_from": cont(c)["source_run"]}, exclusive=True)
        print("SEEDED: %d records and %d Process A observations from %s. Next: Process B" % (
            len(records), len(result["observations"]), cont(c)["source_run"]))
        return
    if T.sha(p(c, "LEGACY_POSE")) != c["pins"]["legacy_pose_sha256"]:
        problems.append("the legacy pose is not %s" % c["pins"]["legacy_pose_sha256"])
    refuse(problems, "SEED")
    os.makedirs(poses_dir(c))
    name = os.path.basename(p(c, "LEGACY_POSE"))
    T.copy_verified(p(c, "LEGACY_POSE"), os.path.join(poses_dir(c), name), c["pins"]["legacy_pose_sha256"])
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "poses_dir": poses_dir(c),
              "files": {name: c["pins"]["legacy_pose_sha256"]}}
    T.write_json(q(c, "evidence", "seed.json"), result, exclusive=True)
    print("SEEDED: %s. Next: Process A" % name)


def cmd_check(c):
    st, cpm = state(c)
    print(json.dumps({"installation": st, "installed_cpm_sha256": cpm,
                      "registries_present": dict((k, os.path.lexists(v)) for k, v in targets(c).items())}, indent=1))
    return 0 if st in ("published", "qualification") else 1


def cmd_library(c, tag):
    if not tag.isalnum():
        raise SystemExit("REFUSED: the tag must be letters and digits")
    running = T.sfm_running()
    if running:
        raise SystemExit("REFUSED: %s; close SFM first" % running)
    files = {}
    if os.path.isdir(poses_dir(c)):
        for name in sorted(os.listdir(poses_dir(c))):
            path = os.path.join(poses_dir(c), name)
            if os.path.isfile(path):
                files[name] = T.sha(path)
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": tag, "poses_dir": poses_dir(c), "files": files}
    T.write_json(q(c, "evidence", "library_%s.json" % tag), result, exclusive=True)
    print(json.dumps(result, indent=1))
    print("LIBRARY %s: %d files recorded" % (tag, len(files)))


def cmd_collect_logs(c):
    running = T.sfm_running()
    if running:
        raise SystemExit("REFUSED: %s; close SFM first" % running)
    pre = T.read_json(q(c, "pre_run", "pre.json"))
    out = q(c, "evidence", "logs")
    if os.path.exists(out):
        raise SystemExit("REFUSED: %s exists" % out)
    os.makedirs(out)
    copied = {}
    for name in sorted(os.listdir(p(c, "LOG_DIR"))):
        src = os.path.join(p(c, "LOG_DIR"), name)
        if os.path.isfile(src) and name.lower().endswith(".log") and os.path.getmtime(src) >= pre["at_epoch"] - 1:
            digest = T.sha(src)
            T.copy_verified(src, os.path.join(out, name), digest)
            copied[name] = digest
    T.write_json(os.path.join(out, "LOGS.json"), {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "files": copied},
                 exclusive=True)
    print("LOGS COLLECTED: %d files" % len(copied))
    return 0 if copied else 1


def cmd_restore(c):
    running = T.sfm_running()
    if running:
        raise SystemExit("REFUSED: %s; close SFM first" % running)
    pre = T.read_json(q(c, "pre_run", "pre.json"))
    journal_path = q(c, "pre_run", "install_journal.json")
    st, cpm = state(c)
    allowed = set([c["pins"]["published_cpm_sha256"]])
    ids = identities(c)
    if ids:
        allowed.add(ids["qualification_cpm_sha256"])
    if cpm not in allowed:
        raise SystemExit("REFUSED: the installed CPM %s is neither the published nor the qualification build" % cpm)
    for key, path in targets(c).items():
        if os.path.lexists(path) and T.sha(path) != c["pins"][key + "_sha256"]:
            raise SystemExit("REFUSED: %s is not the file this run installed" % path)
    if cpm != c["pins"]["published_cpm_sha256"]:
        T.copy_verified(q(c, "pre_run", "backup", "SFM_Character_Preset_Manager_published.py"), T.installed(c),
                        c["pins"]["published_cpm_sha256"])
    for path in targets(c).values():
        if os.path.lexists(path):
            os.remove(path)
    for rel, digest in pre["pyc"].items():
        target = os.path.join(p(c, "SCRIPTS_ROOT"), rel)
        if not os.path.isfile(target) or T.sha(target) != digest:
            T.copy_verified(q(c, "pre_run", "backup", "pyc", rel), target, digest)
    for rel, digest in pre["housekeeping"].items():
        target = os.path.join(p(c, "GAME"), "usermod", rel)
        if digest is not None and (not os.path.isfile(target) or T.sha(target) != digest):
            T.copy_verified(q(c, "pre_run", "backup", "housekeeping", rel.replace("\\", "__")), target, digest)
    moved = []
    chars = os.path.join(p(c, "LIBRARY"), "Characters")
    with open(q(c, "pre_run", "inventory_LIBRARY.txt")) as f:
        pre_rows = f.read()
    for name in sorted(os.listdir(chars)) if os.path.isdir(chars) else []:
        poses = os.path.join(chars, name, "Poses")
        if os.path.isdir(poses):
            if ("  Characters/%s/Poses/" % name) in pre_rows:
                raise SystemExit("REFUSED: %s existed before the run; it is never moved" % poses)
            dest = q(c, "evidence", "library_poses", name)
            if os.path.exists(dest):
                raise SystemExit("REFUSED: %s exists" % dest)
            shutil.copytree(poses, dest)
            if T.inventory(dest)["sha256"] != T.inventory(poses)["sha256"]:
                raise SystemExit("REFUSED: the Poses copy does not verify")
            shutil.rmtree(poses)
            moved.append(name)
    problems = []
    for k in INVENTORIES:
        v = T.inventory(p(c, k))
        if v["sha256"] != pre["inventories"][k]["sha256"]:
            with open(q(c, "pre_run", "inventory_%s.txt" % k)) as f:
                base = set(f.read().split("\n")) - set([""])
            now = set(v["rows"])
            problems.append({"inventory": k, "added": sorted(now - base)[:20], "removed": sorted(base - now)[:20]})
    st, cpm = state(c)
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "installation": st, "installed_cpm_sha256": cpm,
              "poses_moved_to_evidence": moved, "inventory_problems": problems,
              "restored": st == "published" and not problems}
    if os.path.isfile(journal_path):
        journal = T.read_json(journal_path)
        journal["state"] = "restored" if result["restored"] else "restore-incomplete"
        T.write_json(journal_path, journal)
    T.write_json(q(c, "evidence", "restore.json"), result)
    print(json.dumps(result, indent=1))
    print("RESTORED" if result["restored"] else "RESTORE INCOMPLETE: report the differences above; nothing else "
          "was removed")
    return 0 if result["restored"] else 1


def cmd_precheck(c):
    import s3_precheck
    ids = identities(c)
    staged = q(c, "staged", "SFM_Character_Preset_Manager.py")
    problems = []
    if ids is None or T.sha(staged) != ids["qualification_cpm_sha256"]:
        problems.append("the staged qualification CPM does not verify")
    obs = q(c, "observations", "S0-08.json")
    if not os.path.isfile(obs) or not os.path.isfile(q(c, "observations", "S0-08.s3.json")):
        problems.append("observe B1 first")
    records = [n for n in (os.listdir(poses_dir(c)) if os.path.isdir(poses_dir(c)) else [])
               if n.startswith("S3 Pose A--") and n.endswith(".json")]
    if len(records) != 1:
        problems.append("S3 Pose A is not in the run's Poses folder exactly once (%s)" % records)
    out = q(c, "evidence", "A1_PRECHECK.json")
    if os.path.lexists(out):
        problems.append("%s exists" % out)
    refuse(problems, "PRECHECK")
    return s3_precheck.main(["s3_precheck", staged, obs, os.path.join(poses_dir(c), records[0]), out])


def cmd_compare(c):
    import s3_compare
    return s3_compare.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": cmd_status, "inspect": cmd_inspect,
                "install": cmd_install, "seed": cmd_seed, "check": cmd_check, "collect-logs": cmd_collect_logs,
                "restore": cmd_restore, "compare": cmd_compare, "precheck": cmd_precheck}
    if len(argv) == 4 and argv[2] == "library":
        return cmd_library(load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
