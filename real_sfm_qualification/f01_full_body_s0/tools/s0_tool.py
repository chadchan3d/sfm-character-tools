# -*- coding: utf-8 -*-
"""F-01 full-body S0 read-only survey: preparation, post-run verification and analysis. Python 3, run with -I while
SFM is closed. Nothing is installed: the published CPM stays in place and the observer runs from SFM's Script
Editor. Every command refuses, changing nothing, when a precondition fails. Reuses the Stage D NQ-1 tool's verified
helpers (hashing, inventories, verified copies, the SFM process check).

usage: python -I s0_tool.py S0.json COMMAND
  pre      verify SFM closed, the published CPM installed with no pose registry beside it, the R2 fixture and the
           pinned observer; record the four protected inventories; back up SFM's housekeeping files and the .pyc
           files; create Q/sessions/S0_SURVEY.dmx (a verified copy of the fixture), Q/observations and Q/evidence
  post     verify SFM closed; put back any housekeeping or .pyc file SFM rewrote; verify the session copy is
           byte-identical to the fixture (never saved), the published CPM and no registry, the observer unchanged,
           and every inventory equal to its baseline; write Q/evidence/post.json
  status   read-only: report whether a completed pre is still a fresh baseline (pre is never run twice)
  analyze  validate every Q/observations/S0-NN.json and write Q/evidence/S0_REPORT.json and S0_REPORT.md
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
import s0_analyze  # noqa: E402

INVENTORIES = ("SCRIPTS_ROOT", "CFG_ROOT", "LIBRARY", "SESSIONS")
SESSION = "S0_SURVEY.dmx"


def load(path):
    with open(path, "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    if c.get("format") != "F01-S0-config-v1":
        raise SystemExit("REFUSED: not an S0 configuration")
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


def observer(c):
    return os.path.join(p(c, "REPO"), "real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")


def installation_problems(c):
    out = []
    cpm = T.sha(T.installed(c)) if os.path.isfile(T.installed(c)) else None
    if cpm != c["pins"]["published_cpm_sha256"]:
        out.append("the installed CPM is not the published build (%s)" % cpm)
    if os.path.lexists(T.profile_target(c)):
        out.append("a pose registry is installed beside the CPM (%s)" % T.profile_target(c))
    return out


def cmd_pre(c):
    q = p(c, "Q")
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    problems += installation_problems(c)
    if not os.path.isfile(p(c, "R2_FIXTURE")) or T.sha(p(c, "R2_FIXTURE")) != c["pins"]["r2_fixture_sha256"]:
        problems.append("the R2 fixture is not %s" % c["pins"]["r2_fixture_sha256"])
    if T.sha(observer(c)) != c["pins"]["observer_sha256"]:
        problems.append("the observer is not the pinned %s" % c["pins"]["observer_sha256"])
    pre_dir = os.path.join(q, "pre_run")
    for d in (pre_dir, os.path.join(q, "observations"), os.path.join(q, "evidence"), os.path.join(q, "sessions")):
        if os.path.exists(d):
            problems.append("%s already exists" % d)
    if problems:
        print(json.dumps({"problems": problems}, indent=1))
        if os.path.isfile(os.path.join(pre_dir, "pre.json")):
            print("A previous pre already completed in %s. pre never runs twice; run the `status` command to check "
                  "whether that run is still a fresh, usable baseline." % q)
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
    T.copy_verified(p(c, "R2_FIXTURE"), os.path.join(q, "sessions", SESSION), c["pins"]["r2_fixture_sha256"])
    inv = dict((k, T.inventory(p(c, k))) for k in INVENTORIES)
    for k, v in inv.items():
        with open(os.path.join(pre_dir, "inventory_%s.txt" % k), "w") as f:
            f.write("\n".join(v["rows"]) + "\n")
    T.write_json(os.path.join(pre_dir, "pre.json"), {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"), "installed_cpm_sha256": c["pins"]["published_cpm_sha256"],
        "observer_sha256": c["pins"]["observer_sha256"], "housekeeping": house, "pyc": pyc,
        "inventories": dict((k, {"files": v["files"], "sha256": v["sha256"]}) for k, v in inv.items()),
        "pass": True}, exclusive=True)
    print("PRE PASS: inventories, backups and %s are in place. Nothing was installed. Next: the native survey"
          % os.path.join(q, "sessions", SESSION))


def cmd_post(c):
    q = p(c, "Q")
    running = T.sfm_running()
    if running:
        raise SystemExit("REFUSED: %s; close SFM first (do not save)" % running)
    pre = T.read_json(os.path.join(q, "pre_run", "pre.json"))
    put_back = []
    for rel, digest in pre["pyc"].items():
        target = os.path.join(p(c, "SCRIPTS_ROOT"), rel)
        if not os.path.isfile(target) or T.sha(target) != digest:
            T.copy_verified(os.path.join(q, "pre_run", "backup", "pyc", rel), target, digest)
            put_back.append("scripts/" + rel.replace("\\", "/"))
    for rel, digest in pre["housekeeping"].items():
        target = os.path.join(p(c, "GAME"), "usermod", rel)
        if digest is not None and (not os.path.isfile(target) or T.sha(target) != digest):
            T.copy_verified(os.path.join(q, "pre_run", "backup", "housekeeping", rel.replace("\\", "__")), target,
                            digest)
            put_back.append(rel.replace("\\", "/"))
    problems = installation_problems(c)
    session = os.path.join(q, "sessions", SESSION)
    if not os.path.isfile(session) or T.sha(session) != c["pins"]["r2_fixture_sha256"]:
        problems.append("the survey session is not byte-identical to the fixture (was it saved?)")
    extra = sorted(set(os.listdir(os.path.join(q, "sessions"))) - set([SESSION]))
    if extra:
        problems.append("unexpected files in the sessions folder: %s" % extra)
    if T.sha(observer(c)) != pre["observer_sha256"]:
        problems.append("the observer changed after pre")
    inventories = {}
    for k in INVENTORIES:
        v = T.inventory(p(c, k))
        inventories[k] = {"files": v["files"], "sha256": v["sha256"]}
        if v["sha256"] != pre["inventories"][k]["sha256"]:
            with open(os.path.join(q, "pre_run", "inventory_%s.txt" % k)) as f:
                base = set(f.read().split("\n")) - set([""])
            now = set(v["rows"])
            problems.append({"inventory": k, "added": sorted(now - base)[:20], "removed": sorted(base - now)[:20]})
    observations = sorted(n for n in os.listdir(os.path.join(q, "observations")) if n.endswith(".json"))
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "put_back": put_back, "observations": observations,
              "inventories": inventories, "problems": problems, "pass": not problems}
    T.write_json(os.path.join(q, "evidence", "post.json"), result, exclusive=True)
    print(json.dumps(result, indent=1))
    print("POST PASS: nothing in the installation, library or sessions changed" if result["pass"] else
          "POST FAIL: report the problems above; nothing else was changed")
    return 0 if result["pass"] else 1


def cmd_status(c):
    """Read-only: is the completed pre still a fresh baseline from which the survey may start?"""
    q = p(c, "Q")
    pre_path = os.path.join(q, "pre_run", "pre.json")
    if not os.path.isfile(pre_path):
        print("STATUS: no completed pre in %s; run pre" % q)
        return 1
    pre = T.read_json(pre_path)
    problems = []
    if pre.get("pass") is not True:
        problems.append("pre.json does not record a pass")
    running = T.sfm_running()
    if running:
        problems.append(running)
    problems += installation_problems(c)
    if T.sha(p(c, "R2_FIXTURE")) != c["pins"]["r2_fixture_sha256"]:
        problems.append("the R2 fixture is not %s" % c["pins"]["r2_fixture_sha256"])
    if not (T.sha(observer(c)) == pre["observer_sha256"] == c["pins"]["observer_sha256"]):
        problems.append("the observer differs from the pin recorded by pre")
    sessions = sorted(os.listdir(os.path.join(q, "sessions")))
    if sessions != [SESSION] or T.sha(os.path.join(q, "sessions", SESSION)) != c["pins"]["r2_fixture_sha256"]:
        problems.append("the sessions folder is not exactly an unsaved %s (%s)" % (SESSION, sessions))
    for d in ("observations", "evidence"):
        if os.listdir(os.path.join(q, d)):
            problems.append("%s is not empty: the survey has started; this is not a fresh run" % d)
    changed = []
    for rel, digest in pre["housekeeping"].items():
        target = os.path.join(p(c, "GAME"), "usermod", rel)
        if digest is not None and (not os.path.isfile(target) or T.sha(target) != digest):
            changed.append(rel.replace("\\", "/"))
    for rel, digest in pre["pyc"].items():
        target = os.path.join(p(c, "SCRIPTS_ROOT"), rel)
        if not os.path.isfile(target) or T.sha(target) != digest:
            changed.append("scripts/" + rel.replace("\\", "/"))
    if changed:
        problems.append("files changed since pre (SFM was started?): %s" % changed[:10])
    for k in INVENTORIES:
        if T.inventory(p(c, k))["sha256"] != pre["inventories"][k]["sha256"]:
            problems.append("inventory %s differs from the pre baseline" % k)
    print(json.dumps({"pre_at": pre.get("at"), "problems": problems}, indent=1))
    print("STATUS FRESH: the completed pre is a valid baseline; start the survey (PROCEDURE step 2)" if not problems
          else "STATUS NOT FRESH: do not start the survey; report the problems above")
    return 0 if not problems else 1


def cmd_analyze(c):
    q = p(c, "Q")
    return s0_analyze.main(["s0_analyze.py", os.path.join(q, "observations"), os.path.join(q, "evidence")])


def main(argv):
    if len(argv) != 3 or argv[2] not in ("pre", "status", "post", "analyze"):
        print(__doc__)
        return 2
    c = load(argv[1])
    return {"pre": cmd_pre, "status": cmd_status, "post": cmd_post, "analyze": cmd_analyze}[argv[2]](c) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
