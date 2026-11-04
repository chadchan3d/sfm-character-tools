# -*- coding: utf-8 -*-
"""F-01 Stage D native checkpoint (NQ-1): preparation, temporary installation and restoration. Python 3, run with
-I while SFM is closed. Every command refuses, changing nothing, when a precondition fails.

usage: python -I nq1_tool.py NQ1.json COMMAND
  build    derive the qualification CPM from the Stage D candidate: exactly one line differs
           (PROD_POSE_REGISTRY_MODE = u"qualification"); writes Q/staged/ and Q/staged/IDENTITIES.json
  pre      verify SFM closed, the published installation and the fixture; record inventories; back up the published
           CPM and the SFM housekeeping files; create the two disposable session copies
  install  journal first, then install the qualification CPM and the pose profile file (temporary)
  check    report the installation state (published | qualification | other)
  inspect  offline, read-only: verify Q/sessions/NQ1_DESTINATION.dmx (saved by the operator in step 0) holds no
           source animation set and an unchanged destination arm
  seed     Process B-only rerun: after install, restore process A's qualified pose records into the isolated
           library and its two observations into Q/observations, each copy pinned by SHA-256 (config "seed")
  restore  put the published CPM back, remove the profile file, move the run's Poses folder into Q/evidence, restore
           the housekeeping files; then verify every inventory equals its pre-run baseline
"""
from __future__ import print_function

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

MODE_PRODUCTION = b'PROD_POSE_REGISTRY_MODE = u"production"\n'
MODE_QUALIFICATION = b'PROD_POSE_REGISTRY_MODE = u"qualification"\n'


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path):
    with open(path, "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    if c.get("format") != "F01-NQ1-config-v1":
        raise SystemExit("REFUSED: not an NQ-1 configuration")
    for k, v in list(c["paths"].items()):
        c["paths"][k] = os.path.expandvars(v)
    for k, v in list(c["paths"].items()):
        for _ in range(3):
            for kk, vv in c["paths"].items():
                v = v.replace("{%s}" % kk, vv)
        c["paths"][k] = v
    return c


def p(c, key):
    return c["paths"][key]


def write_json(path, data, exclusive=False):
    tmp = path + ".nq1.tmp"
    if os.path.lexists(tmp):
        raise SystemExit("REFUSED: %s exists; inspect it" % tmp)
    if exclusive and os.path.lexists(path):
        raise SystemExit("REFUSED: %s already exists" % path)
    with open(tmp, "wb") as f:
        f.write(json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def copy_verified(src, dst, expected):
    tmp = dst + ".nq1.tmp"
    if os.path.lexists(tmp):
        raise SystemExit("REFUSED: %s exists; inspect it" % tmp)
    shutil.copyfile(src, tmp)
    if sha(tmp) != expected:
        os.remove(tmp)
        raise SystemExit("REFUSED: copy of %s does not verify" % src)
    os.replace(tmp, dst)
    if sha(dst) != expected:
        raise SystemExit("COPY DOES NOT VERIFY: %s (run restore)" % dst)


def inventory(root):
    rows = []
    if os.path.isdir(root):
        for d, dirs, files in os.walk(root):
            dirs.sort()
            for name in sorted(files):
                path = os.path.join(d, name)
                rows.append("%s  %s" % (sha(path), os.path.relpath(path, root).replace("\\", "/")))
    text = "\n".join(rows) + "\n"
    return {"files": len(rows), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "rows": rows}


def sfm_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq sfm.exe", "/NH"], capture_output=True, text=True,
                             timeout=60).stdout
    except Exception as exc:
        return "process list unreadable (%r)" % (exc,)
    return "sfm.exe is running" if "sfm.exe" in out.lower() else None


def installed(c):
    return os.path.join(p(c, "GAME"), "usermod", "scripts", "ChadChan3D_CPM", "SFM_Character_Preset_Manager.py")


def profile_target(c):
    return os.path.join(p(c, "GAME"), "usermod", "scripts", "SFM Character Tools", "cpm_pose_profiles_v1.json")


def state(c):
    ids = c["pins"]
    cpm = sha(installed(c))
    profile = os.path.lexists(profile_target(c))
    staged = os.path.join(p(c, "Q"), "staged", "IDENTITIES.json")
    qual = read_json(staged)["qualification_cpm_sha256"] if os.path.isfile(staged) else None
    if cpm == ids["published_cpm_sha256"] and not profile:
        return "published", cpm
    if cpm == qual and profile and sha(profile_target(c)) == ids["profile_sha256"]:
        return "qualification", cpm
    return "other", cpm


def cmd_build(c):
    src = p(c, "CANDIDATE")
    if sha(src) != c["pins"]["candidate_cpm_sha256"]:
        raise SystemExit("REFUSED: the Stage D candidate is not %s" % c["pins"]["candidate_cpm_sha256"])
    if sha(p(c, "PROFILE")) != c["pins"]["profile_sha256"]:
        raise SystemExit("REFUSED: the pose profile file is not the pinned registry")
    with open(src, "rb") as f:
        raw = f.read()
    if raw.count(MODE_PRODUCTION) != 1 or MODE_QUALIFICATION in raw:
        raise SystemExit("REFUSED: the candidate does not hold exactly one production registry-mode line")
    qual = raw.replace(MODE_PRODUCTION, MODE_QUALIFICATION)
    a, b = raw.split(b"\n"), qual.split(b"\n")
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if len(a) != len(b) or len(diff) != 1:
        raise SystemExit("REFUSED: the derivation changed more than one line")
    staged = os.path.join(p(c, "Q"), "staged")
    if os.path.exists(staged):
        raise SystemExit("REFUSED: %s exists" % staged)
    os.makedirs(staged)
    out = os.path.join(staged, "SFM_Character_Preset_Manager.py")
    with open(out, "wb") as f:
        f.write(qual)
    shutil.copyfile(p(c, "PROFILE"), os.path.join(staged, "cpm_pose_profiles_v1.json"))
    ids = {"candidate_cpm_sha256": c["pins"]["candidate_cpm_sha256"], "qualification_cpm_sha256": sha(out),
           "changed_line": diff[0] + 1, "line": b[diff[0]].decode("utf-8"), "profile_sha256": sha(os.path.join(
               staged, "cpm_pose_profiles_v1.json"))}
    write_json(os.path.join(staged, "IDENTITIES.json"), ids, exclusive=True)
    print(json.dumps(ids, indent=1))
    print("BUILT: the qualification CPM differs from the candidate in line %d only" % ids["changed_line"])


def cmd_pre(c):
    q = p(c, "Q")
    problems = []
    if sfm_running():
        problems.append(sfm_running())
    st, cpm = state(c)
    if st != "published":
        problems.append("the installed CPM is not the published build (%s)" % cpm)
    if sha(p(c, "R2_FIXTURE")) != c["pins"]["r2_fixture_sha256"]:
        problems.append("the R2 fixture is not %s" % c["pins"]["r2_fixture_sha256"])
    if not os.path.isfile(os.path.join(q, "staged", "IDENTITIES.json")):
        problems.append("run build first")
    pre_dir = os.path.join(q, "pre_run")
    if os.path.exists(pre_dir):
        problems.append("pre_run already exists")
    chars = os.path.join(p(c, "LIBRARY"), "Characters")
    existing = [n for n in (sorted(os.listdir(chars)) if os.path.isdir(chars) else [])
                if os.path.exists(os.path.join(chars, n, "Poses"))]
    if existing:
        problems.append("the preset library already holds Poses folders (%s): this run would not be reversible "
                        "by folder; stop and report" % existing)
    if problems:
        print(json.dumps({"problems": problems}, indent=1))
        raise SystemExit("PRE NOT PERFORMED (nothing was changed)")
    os.makedirs(os.path.join(pre_dir, "backup", "housekeeping"))
    for d in ("sessions", "observations", "evidence"):
        os.makedirs(os.path.join(q, d), exist_ok=True)
    copy_verified(installed(c), os.path.join(pre_dir, "backup", "SFM_Character_Preset_Manager_published.py"),
                  c["pins"]["published_cpm_sha256"])
    house = {}
    for rel in c["housekeeping"]:
        src = os.path.join(p(c, "GAME"), "usermod", rel)
        if os.path.isfile(src):
            dst = os.path.join(pre_dir, "backup", "housekeeping", rel.replace("\\", "__"))
            copy_verified(src, dst, sha(src))
            house[rel] = sha(src)
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
                copy_verified(src, dst, sha(src))
                pyc[rel] = sha(src)
    for name in ("NQ1_SOURCE.dmx", "NQ1_PREPARATION.dmx"):
        copy_verified(p(c, "R2_FIXTURE"), os.path.join(q, "sessions", name), c["pins"]["r2_fixture_sha256"])
    inv = dict((k, inventory(p(c, k))) for k in ("SCRIPTS_ROOT", "CFG_ROOT", "LIBRARY", "SESSIONS"))
    for k, v in inv.items():
        with open(os.path.join(pre_dir, "inventory_%s.txt" % k), "w") as f:
            f.write("\n".join(v["rows"]) + "\n")
    write_json(os.path.join(pre_dir, "pre.json"), {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"), "installation": "published", "installed_cpm_sha256": cpm,
        "housekeeping": house, "pyc": pyc, "inventories": dict((k, {"files": v["files"], "sha256": v["sha256"]})
                                                  for k, v in inv.items()), "pass": True}, exclusive=True)
    print("PRE PASS: backups, inventories and the two session copies are in place. Next: install")


def cmd_install(c):
    q = p(c, "Q")
    journal_path = os.path.join(q, "pre_run", "install_journal.json")
    problems = []
    if sfm_running():
        problems.append(sfm_running())
    if not os.path.isfile(os.path.join(q, "pre_run", "pre.json")):
        problems.append("run pre first")
    if os.path.exists(journal_path):
        problems.append("an installation was already started: run restore")
    if state(c)[0] != "published":
        problems.append("the installation is not the published state")
    ids = read_json(os.path.join(q, "staged", "IDENTITIES.json"))
    staged_cpm = os.path.join(q, "staged", "SFM_Character_Preset_Manager.py")
    if sha(staged_cpm) != ids["qualification_cpm_sha256"]:
        problems.append("the staged qualification CPM does not verify")
    if problems:
        print(json.dumps({"problems": problems}, indent=1))
        raise SystemExit("INSTALL NOT PERFORMED (nothing was changed)")
    journal = {"format": "F01-NQ1-install-journal-v1", "state": "begun", "at": time.strftime("%Y-%m-%d %H:%M:%S"),
               "cpm": {"path": installed(c), "original": c["pins"]["published_cpm_sha256"],
                       "installed": ids["qualification_cpm_sha256"]},
               "profile": {"path": profile_target(c), "original": None, "installed": c["pins"]["profile_sha256"]}}
    write_json(journal_path, journal, exclusive=True)
    copy_verified(staged_cpm, installed(c), ids["qualification_cpm_sha256"])
    copy_verified(os.path.join(q, "staged", "cpm_pose_profiles_v1.json"), profile_target(c),
                  c["pins"]["profile_sha256"])
    journal["state"] = "complete" if state(c)[0] == "qualification" else "verification-failed"
    write_json(journal_path, journal)
    if journal["state"] != "complete":
        raise SystemExit("INSTALL DOES NOT VERIFY: run restore")
    print("INSTALLED: qualification CPM %s and the pose profiles. Next: the native procedure" %
          ids["qualification_cpm_sha256"])


def cmd_check(c):
    st, cpm = state(c)
    print(json.dumps({"installation": st, "installed_cpm_sha256": cpm,
                      "profile_present": os.path.lexists(profile_target(c))}, indent=1))
    return 0 if st in ("published", "qualification") else 1


READONLY_ARM_CHANNEL = "Elbow_l.orientationChannel"
READONLY_ARM_MAX_ULP = 2


def ulp_distances(a_hex, b_hex):
    """Per-component float32 ULP distances of two packed little-endian float32 vectors (hex), or None when a component
    is not finite or the lengths differ."""
    import math
    import struct
    a, b = bytes.fromhex(a_hex), bytes.fromhex(b_hex)
    if len(a) != len(b) or len(a) % 4 or not a:
        return None
    out = []
    for i in range(0, len(a), 4):
        fa, fb = struct.unpack("<f", a[i:i + 4])[0], struct.unpack("<f", b[i:i + 4])[0]
        if not (math.isfinite(fa) and math.isfinite(fb)):
            return None
        ia, ib = struct.unpack("<i", a[i:i + 4])[0], struct.unpack("<i", b[i:i + 4])[0]
        ia = ia if ia >= 0 else -0x80000000 - ia  # sign-magnitude onto one monotonic integer line
        ib = ib if ib >= 0 else -0x80000000 - ib
        out.append(abs(ia - ib))
    return out


def cmd_inspect(c):
    sys.path.insert(0, p(c, "SCANNER_DIR"))
    import scan_deferred_fixture as S
    dest = os.path.join(p(c, "Q"), "sessions", "NQ1_DESTINATION.dmx")
    before = S.identity(dest)
    with open(dest, "rb") as f:
        _, elems = S.parse(f.read())
    with open(p(c, "R2_FIXTURE"), "rb") as f:
        _, ref = S.parse(f.read())
    after = S.identity(dest)
    ids = set(e["id"] for e in elems if e["type"] == "DmeAnimationSet")
    report = {"destination_sha256": before[0], "unchanged_during_read": before == after, "problems": []}
    for name, guid in sorted(c["source_animation_sets"].items()):
        if guid in ids:
            report["problems"].append("source animation set %s (%s) is present" % (name, guid))
    want = c["destination"]["animation_set_id"]
    if want not in ids:
        report["problems"].append("the destination animation set is missing")

    def arm(elist):
        D = S.Doc(elist)
        a = [e for e in elist if e["id"] == want][0]
        controls = dict((x["name"], x) for x in [D.ref(i) for i in D.val(a, "controls")] if x)
        out = {}
        for cn, at in (("Hand_l", "positionChannel"), ("Hand_l", "orientationChannel"), ("Elbow_l", "positionChannel"),
                       ("Elbow_l", "orientationChannel")):
            lg = D.log(D.ref(D.val(controls[cn], at)))
            out[cn + "." + at] = (len(lg["layers"]),
                                  [[t, (v.hex() if isinstance(v, (bytes, bytearray)) else v)]
                                   for t, v in zip(lg["layers"][0]["times"], lg["layers"][0]["values"])])
        return out
    if want in ids:
        dest_arm, ref_arm = arm(elems), arm(ref)
        report["destination_arm_identical_to_r2"] = dest_arm == ref_arm
        # Owner ruling (NQ-1, step 0.4): the three written channels must be byte-identical. Only the read-only
        # Elbow_l.orientationChannel may differ, by at most 2 float32 ULP per finite quaternion component (the M-06
        # save/reload tolerance), with identical layer and key counts and key times. Fixture preparation only.
        report["readonly_channel_differences"] = []
        for name in sorted(ref_arm):
            d, r = dest_arm[name], ref_arm[name]
            if d == r:
                continue
            if name != READONLY_ARM_CHANNEL:
                report["problems"].append("written channel %s differs from the R2 fixture" % name)
                continue
            if d[0] != r[0] or [k[0] for k in d[1]] != [k[0] for k in r[1]]:
                report["problems"].append("%s layer count, key count or key times differ from R2" % name)
                continue
            for (t, dv), (_, rv) in zip(d[1], r[1]):
                if dv == rv:
                    continue
                ulps = ulp_distances(dv, rv) if isinstance(dv, str) and isinstance(rv, str) else None
                report["readonly_channel_differences"].append(
                    {"channel": name, "ticks": t, "r2": rv, "destination": dv, "ulp": ulps})
                if ulps is None or max(ulps) > READONLY_ARM_MAX_ULP:
                    report["problems"].append("%s key at %d ticks differs by more than %d float32 ULP" %
                                              (name, t, READONLY_ARM_MAX_ULP))
    shots = sorted(e["name"] for e in elems if e["type"] == "DmeFilmClip")
    report["film_clips"] = shots
    report["pass"] = not report["problems"] and report["unchanged_during_read"]
    write_json(os.path.join(p(c, "Q"), "evidence", "destination_inspection.json"), report)
    print(json.dumps(report, indent=1))
    return 0 if report["pass"] else 1


def cmd_seed(c):
    """Process B-only rerun: copy process A's qualified records (pose files into the isolated library, OBS-01/02 into
    Q/observations), each pinned by SHA-256. Refuses, changing nothing, unless SFM is closed, the qualification build
    is installed, the character's Poses folder does not exist and Q/observations is empty."""
    q, seed = p(c, "Q"), c.get("seed")
    problems = []
    if not seed:
        problems.append("the configuration has no seed section")
    if sfm_running():
        problems.append(sfm_running())
    if state(c)[0] != "qualification":
        problems.append("the qualification build is not installed (run install first)")
    if seed:
        poses_dst = os.path.join(p(c, "LIBRARY"), "Characters", seed["character_dir"], "Poses")
        if os.path.lexists(poses_dst):
            problems.append("%s already exists" % poses_dst)
        obs_dir = os.path.join(q, "observations")
        if os.listdir(obs_dir):
            problems.append("Q/observations is not empty")
        for group in ("poses", "observations"):
            for name, digest in sorted(seed[group]["files"].items()):
                src = os.path.join(seed[group]["source_dir"], name)
                if not os.path.isfile(src) or sha(src) != digest:
                    problems.append("%s is missing or not %s" % (src, digest))
    if problems:
        print(json.dumps({"problems": problems}, indent=1))
        raise SystemExit("SEED NOT PERFORMED (nothing was changed)")
    os.makedirs(poses_dst)
    for name, digest in sorted(seed["poses"]["files"].items()):
        copy_verified(os.path.join(seed["poses"]["source_dir"], name), os.path.join(poses_dst, name), digest)
    for name, digest in sorted(seed["observations"]["files"].items()):
        copy_verified(os.path.join(seed["observations"]["source_dir"], name), os.path.join(obs_dir, name), digest)
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "poses_dir": poses_dst,
              "poses": dict((n, sha(os.path.join(poses_dst, n))) for n in sorted(os.listdir(poses_dst))),
              "observations": dict((n, sha(os.path.join(obs_dir, n))) for n in sorted(os.listdir(obs_dir)))}
    result["verified"] = (result["poses"] == seed["poses"]["files"]
                          and result["observations"] == seed["observations"]["files"])
    write_json(os.path.join(q, "evidence", "seed.json"), result, exclusive=True)
    print(json.dumps(result, indent=1))
    print("SEEDED: process A's records are in place, byte-identical. Next: process B" if result["verified"]
          else "SEED DOES NOT VERIFY: run restore")
    return 0 if result["verified"] else 1


def cmd_restore(c):
    q = p(c, "Q")
    if sfm_running():
        raise SystemExit("REFUSED: %s; close SFM first" % sfm_running())
    pre = read_json(os.path.join(q, "pre_run", "pre.json"))
    journal_path = os.path.join(q, "pre_run", "install_journal.json")
    st, cpm = state(c)
    allowed = set([c["pins"]["published_cpm_sha256"]])
    if os.path.isfile(os.path.join(q, "staged", "IDENTITIES.json")):
        allowed.add(read_json(os.path.join(q, "staged", "IDENTITIES.json"))["qualification_cpm_sha256"])
    if cpm not in allowed:
        raise SystemExit("REFUSED: the installed CPM %s is neither the published nor the qualification build" % cpm)
    backup = os.path.join(q, "pre_run", "backup", "SFM_Character_Preset_Manager_published.py")
    if cpm != c["pins"]["published_cpm_sha256"]:
        copy_verified(backup, installed(c), c["pins"]["published_cpm_sha256"])
    if os.path.lexists(profile_target(c)):
        if sha(profile_target(c)) != c["pins"]["profile_sha256"]:
            raise SystemExit("REFUSED: %s is not the file this run installed" % profile_target(c))
        os.remove(profile_target(c))
    for rel, digest in pre["pyc"].items():
        target = os.path.join(p(c, "SCRIPTS_ROOT"), rel)
        if not os.path.isfile(target) or sha(target) != digest:
            copy_verified(os.path.join(q, "pre_run", "backup", "pyc", rel), target, digest)
    for rel, digest in pre["housekeeping"].items():
        target = os.path.join(p(c, "GAME"), "usermod", rel)
        if digest is None:
            continue
        if not os.path.isfile(target) or sha(target) != digest:
            copy_verified(os.path.join(q, "pre_run", "backup", "housekeeping", rel.replace("\\", "__")), target, digest)
    moved = []
    lib = p(c, "LIBRARY")
    chars = os.path.join(lib, "Characters")
    with open(os.path.join(q, "pre_run", "inventory_LIBRARY.txt")) as f:
        pre_rows = f.read()
    for name in sorted(os.listdir(chars)) if os.path.isdir(chars) else []:
        poses = os.path.join(chars, name, "Poses")
        if os.path.isdir(poses):
            if ("  Characters/%s/Poses/" % name) in pre_rows:
                raise SystemExit("REFUSED: %s existed before the run; it is never moved" % poses)
            dest = os.path.join(q, "evidence", "library_poses", name)
            if os.path.exists(dest):
                raise SystemExit("REFUSED: %s exists" % dest)
            shutil.copytree(poses, dest)
            if inventory(dest)["sha256"] != inventory(poses)["sha256"]:
                raise SystemExit("REFUSED: the Poses copy does not verify")
            shutil.rmtree(poses)
            moved.append(name)
    post = dict((k, inventory(p(c, k))) for k in ("SCRIPTS_ROOT", "CFG_ROOT", "LIBRARY", "SESSIONS"))
    problems = []
    for k, v in post.items():
        if v["sha256"] != pre["inventories"][k]["sha256"]:
            base = set(open(os.path.join(q, "pre_run", "inventory_%s.txt" % k)).read().split("\n")) - set([""])
            now = set(v["rows"])
            problems.append({"inventory": k, "added": sorted(now - base)[:20], "removed": sorted(base - now)[:20]})
    st, cpm = state(c)
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "installation": st, "installed_cpm_sha256": cpm,
              "poses_moved_to_evidence": moved, "inventory_problems": problems,
              "restored": st == "published" and not problems}
    if os.path.isfile(journal_path):
        journal = read_json(journal_path)
        journal["state"] = "restored" if result["restored"] else "restore-incomplete"
        write_json(journal_path, journal)
    write_json(os.path.join(q, "evidence", "restore.json"), result)
    print(json.dumps(result, indent=1))
    print("RESTORED" if result["restored"] else "RESTORE INCOMPLETE: report the differences above; nothing else "
          "was removed")
    return 0 if result["restored"] else 1


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    c = load(argv[1])
    commands = {"build": cmd_build, "pre": cmd_pre, "install": cmd_install, "check": cmd_check, "seed": cmd_seed,
                "inspect": cmd_inspect, "restore": cmd_restore}
    if argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](c) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
