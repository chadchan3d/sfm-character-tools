# -*- coding: utf-8 -*-
"""F-01 model compatibility survey: preparation, post-run verification and the offline probe. Python 3, run with -I
while SFM is closed. Nothing is installed: the published CPM stays in place and is not opened; the observer runs
from SFM's Script Editor. Every command refuses, changing nothing, when a precondition fails. Reuses the Stage D
NQ-1 tool's verified helpers (hashing, inventories, verified copies, the SFM process check), as S0 did.

usage: python -I mc_tool.py MC.json COMMAND
  pre      verify SFM closed, the published CPM installed with no pose or body registry beside it, the pinned
           wrapper and S0 observer, the two models and the rig scripts present (their hashes are recorded); record
           the four protected inventories; back up SFM's housekeeping and .pyc files; create Q/sessions (where the
           disposable session is created, never saved), Q/observations and Q/evidence
  status   read-only: is a completed pre still a fresh baseline (pre is never run twice)
  post     verify SFM closed; put back any housekeeping or .pyc file SFM rewrote; verify the published CPM and no
           registry, the wrapper, the S0 observer and the rig scripts unchanged, and every protected inventory equal
           to its baseline; list Q/sessions (a saved disposable session is reported); write Q/evidence/post.json
  probe    run mc_probe.py on Q/observations into Q/evidence (MC_PROBE.json, MC_PROBE.md)
"""
from __future__ import print_function

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_stage_d_nq1", "tools"))
sys.path.insert(0, HERE)
import nq1_tool as T  # noqa: E402

INVENTORIES = ("SCRIPTS_ROOT", "CFG_ROOT", "LIBRARY", "SESSIONS")
FORMAT = "F01-MC-config-v1"


def load(path):
    with open(path, "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    if c.get("format") != FORMAT:
        raise SystemExit("REFUSED: not a model-survey configuration")
    for k, v in list(c["paths"].items()):
        c["paths"][k] = os.path.expandvars(v)
    for k, v in list(c["paths"].items()):
        for _ in range(3):
            for kk, vv in c["paths"].items():
                v = v.replace("{%s}" % kk, vv)
        c["paths"][k] = v
    if any("<" in v for v in c["paths"].values()):
        raise SystemExit("REFUSED: the configuration still holds placeholders")
    return c


def p(c, key):
    return c["paths"][key]


def kit_files(c):
    root = os.path.join(p(c, "REPO"), "real_sfm_qualification")
    return {"wrapper": os.path.join(root, "f01_model_survey", "observer", "F01_MC_Observe.py"),
            "s0_observer": os.path.join(root, "f01_full_body_s0", "observer", "F01_S0_Survey.py")}


def game_file(c, rel):
    return os.path.join(p(c, "GAME"), rel.replace("/", os.sep))


def installation_problems(c):
    out = []
    cpm = T.sha(T.installed(c)) if os.path.isfile(T.installed(c)) else None
    if cpm != c["pins"]["published_cpm_sha256"]:
        out.append("the installed CPM is not the published build (%s)" % cpm)
    folder = os.path.dirname(T.profile_target(c))
    for name in ("cpm_pose_profiles_v1.json", "cpm_body_profiles_v1.json"):
        if os.path.lexists(os.path.join(folder, name)):
            out.append("a registry is installed beside the CPM (%s)" % os.path.join(folder, name))
    return out


def kit_problems(c):
    out = []
    for key, path in kit_files(c).items():
        if not os.path.isfile(path) or T.sha(path) != c["pins"][key + "_sha256"]:
            out.append("the %s is not the pinned %s" % (key, c["pins"][key + "_sha256"]))
    return out


def game_hashes(c):
    out = {}
    for rel in c["models"] + c["rig_scripts"]:
        path = game_file(c, rel)
        out[rel] = T.sha(path) if os.path.isfile(path) else None
    return out


def cmd_pre(c):
    q = p(c, "Q")
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    problems += installation_problems(c) + kit_problems(c)
    hashes = game_hashes(c)
    problems += ["%s is missing" % rel for rel, d in hashes.items() if d is None]
    pre_dir = os.path.join(q, "pre_run")
    for d in (pre_dir, os.path.join(q, "observations"), os.path.join(q, "evidence"), os.path.join(q, "sessions")):
        if os.path.exists(d):
            problems.append("%s already exists" % d)
    if problems:
        print(json.dumps({"problems": problems}, indent=1))
        if os.path.isfile(os.path.join(pre_dir, "pre.json")):
            print("A previous pre already completed in %s. pre never runs twice; run `status`." % q)
        raise SystemExit("PRE NOT PERFORMED (nothing was changed)")
    print("pre: recording backups and four inventories; this takes a few minutes. Wait for PRE PASS.")
    os.makedirs(os.path.join(pre_dir, "backup", "housekeeping"))
    for d in ("sessions", "observations", "evidence"):
        os.makedirs(os.path.join(q, d))
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
    inv = dict((k, T.inventory(p(c, k))) for k in INVENTORIES)
    for k, v in inv.items():
        with open(os.path.join(pre_dir, "inventory_%s.txt" % k), "w") as f:
            f.write("\n".join(v["rows"]) + "\n")
    T.write_json(os.path.join(pre_dir, "pre.json"), {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"), "installed_cpm_sha256": c["pins"]["published_cpm_sha256"],
        "kit": dict((k, c["pins"][k + "_sha256"]) for k in kit_files(c)), "game_files": hashes,
        "housekeeping": house, "pyc": pyc,
        "inventories": dict((k, {"files": v["files"], "sha256": v["sha256"]}) for k, v in inv.items()),
        "pass": True}, exclusive=True)
    print("PRE PASS: inventories and backups are in place. Nothing was installed. Next: the native survey "
          "(PROCEDURE section 2). The disposable session folder is %s" % os.path.join(q, "sessions"))


def changed_since_pre(c, pre):
    changed = []
    for rel, digest in pre["housekeeping"].items():
        target = os.path.join(p(c, "GAME"), "usermod", rel)
        if digest is not None and (not os.path.isfile(target) or T.sha(target) != digest):
            changed.append(("housekeeping", rel, digest))
    for rel, digest in pre["pyc"].items():
        target = os.path.join(p(c, "SCRIPTS_ROOT"), rel)
        if not os.path.isfile(target) or T.sha(target) != digest:
            changed.append(("pyc", rel, digest))
    return changed


def cmd_status(c):
    q = p(c, "Q")
    pre_path = os.path.join(q, "pre_run", "pre.json")
    if not os.path.isfile(pre_path):
        print("STATUS: no completed pre in %s; run pre" % q)
        return 1
    pre = T.read_json(pre_path)
    problems = [] if pre.get("pass") is True else ["pre.json does not record a pass"]
    running = T.sfm_running()
    if running:
        problems.append(running)
    problems += installation_problems(c) + kit_problems(c)
    if game_hashes(c) != pre["game_files"]:
        problems.append("a model or rig script changed since pre")
    for d in ("sessions", "observations", "evidence"):
        if os.listdir(os.path.join(q, d)):
            problems.append("%s is not empty: the survey has started; this is not a fresh run" % d)
    changed = changed_since_pre(c, pre)
    if changed:
        problems.append("files changed since pre (SFM was started?): %s" % [x[1] for x in changed][:10])
    for k in INVENTORIES:
        if T.inventory(p(c, k))["sha256"] != pre["inventories"][k]["sha256"]:
            problems.append("inventory %s differs from the pre baseline" % k)
    print(json.dumps({"pre_at": pre.get("at"), "problems": problems}, indent=1))
    print("STATUS FRESH: start the survey (PROCEDURE section 2)" if not problems else
          "STATUS NOT FRESH: do not start the survey; report the problems above")
    return 0 if not problems else 1


def cmd_post(c):
    q = p(c, "Q")
    running = T.sfm_running()
    if running:
        raise SystemExit("REFUSED: %s; close SFM first (do not save)" % running)
    pre = T.read_json(os.path.join(q, "pre_run", "pre.json"))
    put_back = []
    for kind, rel, digest in changed_since_pre(c, pre):
        if kind == "pyc":
            T.copy_verified(os.path.join(q, "pre_run", "backup", "pyc", rel),
                            os.path.join(p(c, "SCRIPTS_ROOT"), rel), digest)
            put_back.append("scripts/" + rel.replace("\\", "/"))
        else:
            T.copy_verified(os.path.join(q, "pre_run", "backup", "housekeeping", rel.replace("\\", "__")),
                            os.path.join(p(c, "GAME"), "usermod", rel), digest)
            put_back.append(rel.replace("\\", "/"))
    problems = installation_problems(c) + kit_problems(c)
    if game_hashes(c) != pre["game_files"]:
        problems.append("a model or rig script changed during the run")
    inventories = {}
    for k in INVENTORIES:
        v = T.inventory(p(c, k))
        inventories[k] = {"files": v["files"], "sha256": v["sha256"]}
        if v["sha256"] != pre["inventories"][k]["sha256"]:
            with open(os.path.join(q, "pre_run", "inventory_%s.txt" % k)) as f:
                base = set(f.read().split("\n")) - set([""])
            now = set(v["rows"])
            problems.append({"inventory": k, "added": sorted(now - base)[:20], "removed": sorted(base - now)[:20]})
    sessions = sorted(os.listdir(os.path.join(q, "sessions")))
    if sessions:
        problems.append("the disposable session folder is not empty (was the session saved?): %s" % sessions)
    observations = sorted(n for n in os.listdir(os.path.join(q, "observations")) if n.endswith(".json"))
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "put_back": put_back, "observations": observations,
              "sessions_folder": sessions, "inventories": inventories, "problems": problems, "pass": not problems}
    T.write_json(os.path.join(q, "evidence", "post.json"), result, exclusive=True)
    print(json.dumps(result, indent=1))
    print("POST PASS: nothing in the installation, library or sessions changed" if result["pass"] else
          "POST FAIL: report the problems above; nothing else was changed")
    return 0 if result["pass"] else 1


def cmd_probe(c):
    import mc_probe
    q = p(c, "Q")
    return mc_probe.main(["mc_probe.py", os.path.join(q, "observations"), os.path.join(q, "evidence")])


def main(argv):
    if len(argv) != 3 or argv[2] not in ("pre", "status", "post", "probe"):
        print(__doc__)
        return 2
    c = load(argv[1])
    return {"pre": cmd_pre, "status": cmd_status, "post": cmd_post, "probe": cmd_probe}[argv[2]](c) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
