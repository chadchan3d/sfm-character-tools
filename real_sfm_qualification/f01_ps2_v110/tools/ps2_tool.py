# -*- coding: utf-8 -*-
"""F-01 PS-2: v1.1.0 production candidate package, native smoke installation, rollback to v1.0.0 and restoration.
Python 3, run with -I while SFM is closed (every command that changes a file refuses while sfm.exe runs). Every
command refuses, changing nothing, when a precondition fails. Reuses the Stage D NQ-1 tool's verified helpers (hashing,
verified copies, inventories, the SFM process check).

usage: python -I ps2_tool.py PS2.json COMMAND
  package       build the UNSIGNED candidate package into Q/package (new folder): the published v1.0.0 ZIP's exact
                bytes with the candidate CPM, the two Pose Library registries and the unsigned v1.1.0 candidate
                inventory; the v1.0.0 signature is left out. Writes stage/, the deterministic candidate ZIP and
                PACKAGE_MANIFEST.json. Nothing is installed.
  pre           verify SFM closed, the package, and that the installation is exactly v1.0.0 (every v1.0.0 software
                file equals the published ZIP, no registry, no Poses folder); back up the v1.0.0 files the candidate
                replaces, the whole preset library, SFM housekeeping and .pyc files; record four inventories; create
                the disposable session copies in Q/sessions
  install       journal first; then install the candidate from Q/package/stage (CPM, both registries, the candidate
                inventory) and remove the v1.0.0 signature (backed up): the package layout, unsigned
  seed          copy the pinned legacy left-arm pose (version 1) into Krystal's Poses folder
  check         report the installation state (v1.0.0 | candidate | other)
  library TAG   read-only: hash every Poses folder and every character folder created during the run into
                Q/evidence/library_TAG.json
  collect-logs  copy the CPM log files written since pre into Q/evidence/logs (verified copies; sources untouched)
  rollback      put v1.0.0 back exactly (CPM, inventory and its signature from the backup; both registries removed;
                housekeeping and .pyc restored) WITHOUT touching the preset library: the run's Poses folders stay in
                place for the native v1.0.0 check; verifies every v1.0.0 software file against the published ZIP
  cleanup       after the native v1.0.0 check: copy the run's library changes into Q/evidence/library_after, put the
                library back exactly as backed up at pre, restore housekeeping and .pyc again, and verify all four
                inventories equal their pre-run baselines
  compare       run tools/ps2_compare.py on this run (writes Q/evidence/PS2_VERDICT.json and PS2_VERDICT.md)
"""
from __future__ import print_function

import hashlib
import io
import json
import os
import shutil
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_stage_d_nq1", "tools"))
sys.path.insert(0, HERE)
import nq1_tool as T  # noqa: E402

FORMAT = "F01-PS2-config-v1"
INVENTORIES = ("SCRIPTS_ROOT", "CFG_ROOT", "LIBRARY", "SESSIONS")
MM = "usermod/scripts/sfm/mainmenu/SFM Character Tools/"
LIB = "usermod/scripts/SFM Character Tools/"
CPM_ENTRY = "usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py"
INV_ENTRY = MM + "sfm_character_tools_inventory.json"
SIG_ENTRY = MM + "sfm_character_tools_inventory.sig"
REGISTRIES = ("cpm_pose_profiles_v1.json", "cpm_body_profiles_v1.json")
ZIP_TIME = (2026, 11, 12, 0, 0, 0)
ZIP_NAME = "SFM.Character.Tools.v1.1.0-candidate-UNSIGNED.zip"
# The session copies (Q/sessions): name -> (config path key, pin key). Never saved.
SESSION_COPIES = (("PS2_ENGINEER_SOURCE.dmx", "EF1_SOURCE", "ef1_source_sha256"),
                  ("PS2_ENGINEER_DESTINATION.dmx", "EF1_DESTINATION", "ef1_destination_sha256"),
                  ("PS2_KRYSTAL.dmx", "R2_FIXTURE", "r2_fixture_sha256"),
                  ("PS2_V100_KRYSTAL.dmx", "R2_FIXTURE", "r2_fixture_sha256"))
# The software inventory fields the signing tool writes (make_software_inventory.py sign), in its canonical form.
INVENTORY_OBJECT = "sfm-character-tools-software-inventory"


def load(path):
    with open(path, "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    if c.get("format") != FORMAT:
        raise SystemExit("REFUSED: not a PS-2 configuration")
    for k, v in list(c["paths"].items()):
        c["paths"][k] = os.path.expandvars(v)
    for k, v in list(c["paths"].items()):
        for _ in range(3):
            for kk, vv in c["paths"].items():
                v = v.replace("{%s}" % kk, vv)
        c["paths"][k] = v
    holes = sorted(k for k, v in c["paths"].items() if "<" in v or ">" in v)
    if holes:
        raise SystemExit("REFUSED: fill the configuration paths first: %s" % ", ".join(holes))
    return c


def p(c, key):
    return c["paths"][key]


def q(c, *parts):
    return os.path.join(p(c, "Q"), *parts)


def game(c, rel):
    """An installed path from a ZIP entry name (usermod/...)."""
    return os.path.join(p(c, "GAME"), *rel.split("/"))


def refuse(problems, what):
    if problems:
        print(json.dumps({"refused": what, "problems": problems}, indent=1))
        raise SystemExit("%s NOT PERFORMED (nothing was changed)" % what)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def canonical(d):
    return (json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def read_zip(c):
    """The published v1.0.0 ZIP: {entry: bytes}, refusing anything but the pinned archive."""
    path = p(c, "V100_ZIP")
    if not os.path.isfile(path) or T.sha(path) != c["pins"]["v100_zip_sha256"]:
        raise SystemExit("REFUSED: %s is not the published v1.0.0 ZIP %s" % (path, c["pins"]["v100_zip_sha256"]))
    with zipfile.ZipFile(path) as z:
        entries = dict((i.filename, z.read(i)) for i in z.infolist() if not i.is_dir())
    if len(entries) != c["pins"]["v100_zip_entries"]:
        raise SystemExit("REFUSED: the v1.0.0 ZIP has %d entries, not %d" % (len(entries), c["pins"]["v100_zip_entries"]))
    return entries


def spec(c):
    path = os.path.join(p(c, "REPO"), "release", "v1.1.0-candidate", "SOFTWARE_SPEC.json")
    if T.sha(path) != c["pins"]["spec_sha256"]:
        raise SystemExit("REFUSED: the v1.1.0 candidate spec is not %s" % c["pins"]["spec_sha256"])
    return T.read_json(path)


def candidate_sources(c):
    """(entry, repository path, pin) for the files the candidate adds or replaces."""
    repo = p(c, "REPO")
    out = [(CPM_ENTRY, os.path.join(repo, "cpm", "app", "SFM_Character_Preset_Manager.py"),
            c["pins"]["candidate_cpm_sha256"])]
    for name, pin in zip(REGISTRIES, ("profile_sha256", "body_profile_sha256")):
        out.append((LIB + name, os.path.join(repo, "cpm", "pose_profiles", name), c["pins"][pin]))
    return out


def candidate_cpm_problems(raw, c):
    """The candidate CPM's production identity, from its own bytes."""
    problems = []
    if raw.count(T.MODE_PRODUCTION) != 1 or T.MODE_QUALIFICATION in raw:
        problems.append("the candidate CPM is not in production mode")
    if raw.count(b'PROD_SCOPE_RULES = {u"direct_fk_v1": {u"revision": 1, u"status": u"qualified"}}\n') != 1:
        problems.append("the candidate CPM does not qualify direct_fk_v1 revision 1 (and nothing else)")
    for needle in (b"PROD_SCOPE_CARRIED_ENABLED = [False]\n", b"PROD_SCOPE_EXTRAPOLATION_QUALIFIED = [False]\n",
                   b"PROD_POSE_QUAL_FAULT = [None]\n",
                   b'PROD_POSE_REGISTRY_SHA256 = u"%s"\n' % c["pins"]["profile_sha256"].encode("ascii"),
                   b'PROD_BODY_REGISTRY_SHA256 = u"%s"\n' % c["pins"]["body_profile_sha256"].encode("ascii")):
        if raw.count(needle) != 1:
            problems.append("the candidate CPM lacks %r" % needle.strip().decode("ascii"))
    return problems


def candidate_inventory(c, sp, files):
    """The v1.1.0 inventory the signing tool would write for these exact files (unsigned): every spec file, in spec
    order, with the v1.0.0 inventory's profile, runtime and signing-key fields."""
    old = json.loads(files[INV_ENTRY].decode("utf-8"))
    entries = []
    for f in sp["files"]:
        data = files["usermod/" + f["path"]]
        entries.append({"path": f["path"], "role": f["role"], "byte_length": len(data), "sha256": sha_bytes(data)})
    d = {"schema": 1, "object_type": INVENTORY_OBJECT, "software": sp["software"],
         "software_version": c["pins"]["software_version"], "authority_profile": sp["authority_profile"],
         "profile_contract_sha256": old["profile_contract_sha256"], "runtime_api_version": old["runtime_api_version"],
         "runtime_build_id": old["runtime_build_id"], "signing_key_id": old["signing_key_id"], "files": entries}
    return canonical(d)


def write_zip(path, files):
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            info.create_system = 0
            z.writestr(info, files[name], compresslevel=9)


def cmd_package(c):
    out = q(c, "package")
    problems = []
    if os.path.exists(out):
        problems.append("%s exists" % out)
    v100 = read_zip(c)
    sp = spec(c)
    for e in (CPM_ENTRY, INV_ENTRY, SIG_ENTRY):
        if e not in v100:
            problems.append("the v1.0.0 ZIP lacks %s" % e)
    if CPM_ENTRY in v100 and sha_bytes(v100[CPM_ENTRY]) != c["pins"]["v100_cpm_sha256"]:
        problems.append("the v1.0.0 ZIP's CPM is not %s" % c["pins"]["v100_cpm_sha256"])
    files = dict(v100)
    origin = dict((k, "v1.0.0") for k in v100)
    for entry, src, pin in candidate_sources(c):
        if not os.path.isfile(src) or T.sha(src) != pin:
            problems.append("%s is not the pinned %s" % (src, pin))
            continue
        with open(src, "rb") as f:
            files[entry] = f.read()
        origin[entry] = "candidate"
    if not problems:
        problems += candidate_cpm_problems(files[CPM_ENTRY], c)
    if not problems:
        for f in sp["files"]:
            data = files.get("usermod/" + f["path"])
            if data is None or sha_bytes(data) != f["sha256"] or len(data) != f["byte_length"]:
                problems.append("staged %s is not the spec identity" % f["path"])
            elif origin["usermod/" + f["path"]] == "v1.0.0" and f["source"] != "release-v1.0.0:usermod/" + f["path"]:
                problems.append("spec source of %s is not the v1.0.0 release" % f["path"])
    refuse(problems, "PACKAGE")
    del files[SIG_ENTRY]
    del origin[SIG_ENTRY]
    files[INV_ENTRY] = candidate_inventory(c, sp, files)
    origin[INV_ENTRY] = "candidate (unsigned; generated)"
    if sha_bytes(files[INV_ENTRY]) != c["pins"]["candidate_inventory_sha256"]:
        raise SystemExit("PACKAGE NOT PERFORMED: the candidate inventory is %s, not the pinned %s (nothing was "
                         "written)" % (sha_bytes(files[INV_ENTRY]), c["pins"]["candidate_inventory_sha256"]))
    os.makedirs(os.path.join(out, "stage"))
    for name, data in files.items():
        dst = os.path.join(out, "stage", *name.split("/"))
        if not os.path.isdir(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))
        with open(dst, "xb") as f:
            f.write(data)
    zpath = os.path.join(out, ZIP_NAME)
    write_zip(zpath, files)
    rows = [{"path": n, "sha256": sha_bytes(files[n]), "byte_length": len(files[n]), "origin": origin[n]}
            for n in sorted(files)]
    manifest = {"format": "F01-PS2-package-v1", "status": "UNSIGNED CANDIDATE - not for distribution",
                "software_version": c["pins"]["software_version"], "zip": ZIP_NAME, "zip_sha256": T.sha(zpath),
                "entries": len(rows), "v100_zip_sha256": c["pins"]["v100_zip_sha256"],
                "spec_sha256": c["pins"]["spec_sha256"], "candidate_cpm_sha256": c["pins"]["candidate_cpm_sha256"],
                "candidate_inventory_sha256": sha_bytes(files[INV_ENTRY]),
                "removed": [SIG_ENTRY], "replaced": [CPM_ENTRY, INV_ENTRY],
                "added": [LIB + n for n in REGISTRIES], "files": rows}
    T.write_json(os.path.join(out, "PACKAGE_MANIFEST.json"), manifest, exclusive=True)
    print("PACKAGED: %d entries (%d from v1.0.0, %d candidate); ZIP %s %s; inventory %s (UNSIGNED); the v1.0.0 "
          "signature is not included" % (len(rows), sum(1 for r in rows if r["origin"] == "v1.0.0"),
                                         sum(1 for r in rows if r["origin"] != "v1.0.0"), ZIP_NAME,
                                         manifest["zip_sha256"], manifest["candidate_inventory_sha256"]))


def package_problems(c):
    """The built package is intact: the manifest, every staged file and the ZIP."""
    path = q(c, "package", "PACKAGE_MANIFEST.json")
    if not os.path.isfile(path):
        return ["run package first"]
    m = T.read_json(path)
    problems = []
    for r in m["files"]:
        f = os.path.join(q(c, "package", "stage"), *r["path"].split("/"))
        if not os.path.isfile(f) or T.sha(f) != r["sha256"]:
            problems.append("staged %s changed" % r["path"])
    if T.sha(q(c, "package", m["zip"])) != m["zip_sha256"]:
        problems.append("the candidate ZIP changed")
    if m["candidate_cpm_sha256"] != c["pins"]["candidate_cpm_sha256"] or \
            m["candidate_inventory_sha256"] != c["pins"]["candidate_inventory_sha256"]:
        problems.append("the package is not this configuration's candidate")
    return problems


def v100_software(c, v100):
    """The v1.0.0 software entries that must be installed exactly: the signed inventory's files plus the inventory
    and its signature (the mutable data, README and OPTIONAL files are not compared)."""
    inv = json.loads(v100[INV_ENTRY].decode("utf-8"))
    return sorted(["usermod/" + f["path"] for f in inv["files"]] + [INV_ENTRY, SIG_ENTRY])


def state(c):
    cpm = T.sha(game(c, CPM_ENTRY)) if os.path.isfile(game(c, CPM_ENTRY)) else None
    regs = [os.path.lexists(game(c, LIB + n)) for n in REGISTRIES]
    sig = os.path.lexists(game(c, SIG_ENTRY))
    inv = T.sha(game(c, INV_ENTRY)) if os.path.isfile(game(c, INV_ENTRY)) else None
    if cpm == c["pins"]["v100_cpm_sha256"] and not any(regs) and sig and inv == c["pins"]["v100_inventory_sha256"]:
        return "v1.0.0", cpm
    if cpm == c["pins"]["candidate_cpm_sha256"] and all(regs) and not sig and \
            inv == c["pins"]["candidate_inventory_sha256"] and \
            [T.sha(game(c, LIB + n)) for n in REGISTRIES] == [c["pins"]["profile_sha256"],
                                                              c["pins"]["body_profile_sha256"]]:
        return "candidate", cpm
    return "other", cpm


def poses_folders(c):
    chars = os.path.join(p(c, "LIBRARY"), "Characters")
    return [n for n in (sorted(os.listdir(chars)) if os.path.isdir(chars) else [])
            if os.path.exists(os.path.join(chars, n, "Poses"))]


def restore_housekeeping_and_pyc(c, pre):
    pre_dir = q(c, "pre_run")
    for rel, digest in pre["housekeeping"].items():
        dst = os.path.join(p(c, "GAME"), "usermod", rel)
        if digest is None:
            if os.path.isfile(dst):
                os.remove(dst)
        elif not os.path.isfile(dst) or T.sha(dst) != digest:
            T.copy_verified(os.path.join(pre_dir, "backup", "housekeeping", rel.replace("\\", "__")), dst, digest)
    for d, _, names in os.walk(p(c, "SCRIPTS_ROOT")):
        for name in names:
            if name.endswith(".pyc"):
                src = os.path.join(d, name)
                if os.path.relpath(src, p(c, "SCRIPTS_ROOT")) not in pre["pyc"]:
                    os.remove(src)
    for rel, digest in pre["pyc"].items():
        dst = os.path.join(p(c, "SCRIPTS_ROOT"), rel)
        if not os.path.isfile(dst) or T.sha(dst) != digest:
            T.copy_verified(os.path.join(pre_dir, "backup", "pyc", rel), dst, digest)


def cmd_pre(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    problems += package_problems(c)
    v100 = read_zip(c)
    st, cpm = state(c)
    if st != "v1.0.0":
        problems.append("the installation is not the v1.0.0 state (CPM %s)" % cpm)
    for e in v100_software(c, v100):
        f = game(c, e)
        if not os.path.isfile(f) or T.sha(f) != sha_bytes(v100[e]):
            problems.append("installed %s is not the v1.0.0 release file" % e)
    for name, key, pin in SESSION_COPIES:
        if not os.path.isfile(p(c, key)) or T.sha(p(c, key)) != c["pins"][pin]:
            problems.append("%s is not %s" % (p(c, key), c["pins"][pin]))
    legacy = p(c, "LEGACY_POSE")
    if not os.path.isfile(legacy) or T.sha(legacy) != c["pins"]["legacy_pose_sha256"]:
        problems.append("the legacy pose is not %s" % c["pins"]["legacy_pose_sha256"])
    if poses_folders(c):
        problems.append("the preset library already holds Poses folders (%s): stop and report" % poses_folders(c))
    for d in ("pre_run", "sessions", "observations", "evidence"):
        if os.path.exists(q(c, d)):
            problems.append("%s already exists" % q(c, d))
    refuse(problems, "PRE")
    print("pre: recording backups and four inventories; this takes a few minutes. Wait for PRE PASS.")
    pre_dir = q(c, "pre_run")
    os.makedirs(os.path.join(pre_dir, "backup", "housekeeping"))
    for d in ("sessions", "observations", "evidence"):
        os.makedirs(q(c, d))
    for e, pin in ((CPM_ENTRY, c["pins"]["v100_cpm_sha256"]), (INV_ENTRY, c["pins"]["v100_inventory_sha256"]),
                   (SIG_ENTRY, c["pins"]["v100_signature_sha256"])):
        T.copy_verified(game(c, e), os.path.join(pre_dir, "backup", os.path.basename(e)), pin)
    library_rows = T.inventory(p(c, "LIBRARY"))["rows"]
    lib_backup = os.path.join(pre_dir, "backup", "library")
    for row in library_rows:
        digest, rel = row.split("  ", 1)
        dst = os.path.join(lib_backup, *rel.split("/"))
        if not os.path.isdir(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))
        T.copy_verified(os.path.join(p(c, "LIBRARY"), *rel.split("/")), dst, digest)
    house = {}
    for rel in c["housekeeping"]:
        src = os.path.join(p(c, "GAME"), "usermod", rel)
        if os.path.isfile(src):
            T.copy_verified(src, os.path.join(pre_dir, "backup", "housekeeping", rel.replace("\\", "__")), T.sha(src))
            house[rel] = T.sha(src)
        else:
            house[rel] = None
    pyc = {}
    for d, _, names in os.walk(p(c, "SCRIPTS_ROOT")):
        for name in names:
            if name.endswith(".pyc"):
                src = os.path.join(d, name)
                rel = os.path.relpath(src, p(c, "SCRIPTS_ROOT"))
                dst = os.path.join(pre_dir, "backup", "pyc", rel)
                if not os.path.isdir(os.path.dirname(dst)):
                    os.makedirs(os.path.dirname(dst))
                T.copy_verified(src, dst, T.sha(src))
                pyc[rel] = T.sha(src)
    for name, key, pin in SESSION_COPIES:
        T.copy_verified(p(c, key), q(c, "sessions", name), c["pins"][pin])
    inv = dict((k, T.inventory(p(c, k))) for k in INVENTORIES)
    for k, v in inv.items():
        with open(os.path.join(pre_dir, "inventory_%s.txt" % k), "w") as f:
            f.write("\n".join(v["rows"]) + "\n")
    T.write_json(os.path.join(pre_dir, "pre.json"), {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"), "at_epoch": time.time(), "installation": "v1.0.0",
        "installed_cpm_sha256": cpm, "housekeeping": house, "pyc": pyc, "library_files": len(library_rows),
        "inventories": dict((k, {"files": v["files"], "sha256": v["sha256"]}) for k, v in inv.items()),
        "package": T.read_json(q(c, "package", "PACKAGE_MANIFEST.json"))["zip_sha256"], "pass": True},
        exclusive=True)
    print("PRE PASS: v1.0.0 verified against the published ZIP; backups (incl. the whole preset library, %d files), "
          "four inventories and the session copies are in place. Next: install" % len(library_rows))


def pre(c):
    path = q(c, "pre_run", "pre.json")
    return T.read_json(path) if os.path.isfile(path) else None


def cmd_install(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    if pre(c) is None:
        problems.append("run pre first")
    problems += package_problems(c)
    st, cpm = state(c)
    if st != "v1.0.0":
        problems.append("the installation is not the v1.0.0 state (CPM %s)" % cpm)
    journal_path = q(c, "pre_run", "install_journal.json")
    if os.path.exists(journal_path):
        problems.append("%s exists (one installation per run)" % journal_path)
    refuse(problems, "INSTALL")
    stage = q(c, "package", "stage")
    m = dict((r["path"], r["sha256"]) for r in T.read_json(q(c, "package", "PACKAGE_MANIFEST.json"))["files"])
    journal = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "state": "installing",
               "writes": [CPM_ENTRY, INV_ENTRY] + [LIB + n for n in REGISTRIES], "removes": [SIG_ENTRY]}
    T.write_json(journal_path, journal, exclusive=True)
    for e in [LIB + n for n in REGISTRIES] + [CPM_ENTRY, INV_ENTRY]:
        T.copy_verified(os.path.join(stage, *e.split("/")), game(c, e), m[e])
    os.remove(game(c, SIG_ENTRY))
    journal["state"] = "complete"
    T.write_json(journal_path, journal)
    st, cpm = state(c)
    print("INSTALLED: candidate %s with both registries and the unsigned v1.1.0 inventory (state %s)" % (cpm, st))


def cmd_seed(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    if state(c)[0] != "candidate":
        problems.append("install first")
    poses = os.path.join(p(c, "LIBRARY"), "Characters", c["seed"]["character_dir"], "Poses")
    if os.path.exists(poses):
        problems.append("%s exists" % poses)
    if os.path.exists(q(c, "evidence", "seed.json")):
        problems.append("already seeded")
    refuse(problems, "SEED")
    os.makedirs(poses)
    name = c["seed"]["legacy_pose_name"]
    T.copy_verified(p(c, "LEGACY_POSE"), os.path.join(poses, name), c["pins"]["legacy_pose_sha256"])
    T.write_json(q(c, "evidence", "seed.json"), {"at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                                  "poses_dir": poses, "files": {name: c["pins"]["legacy_pose_sha256"]}},
                 exclusive=True)
    print("SEEDED: %s (version 1, left arm) into %s" % (name, poses))


def cmd_check(c):
    st, cpm = state(c)
    print(json.dumps({"installation": st, "installed_cpm_sha256": cpm,
                      "registries_present": dict((n, os.path.lexists(game(c, LIB + n))) for n in REGISTRIES),
                      "signature_present": os.path.lexists(game(c, SIG_ENTRY))}, indent=1))


def run_library_rows(c):
    """Library rows that differ from the pre-run backup: (status, rel, sha) for added and changed files."""
    base = {}
    with open(q(c, "pre_run", "inventory_LIBRARY.txt")) as f:
        for line in f.read().splitlines():
            if line:
                digest, rel = line.split("  ", 1)
                base[rel] = digest
    now = {}
    for row in T.inventory(p(c, "LIBRARY"))["rows"]:
        digest, rel = row.split("  ", 1)
        now[rel] = digest
    out = []
    for rel in sorted(set(base) | set(now)):
        if rel not in now:
            out.append(("removed", rel, base[rel]))
        elif rel not in base:
            out.append(("added", rel, now[rel]))
        elif base[rel] != now[rel]:
            out.append(("changed", rel, now[rel]))
    return out


def cmd_library(c, tag):
    path = q(c, "evidence", "library_%s.json" % tag)
    refuse(["%s exists" % path] if os.path.exists(path) else [], "LIBRARY")
    rows = run_library_rows(c)
    T.write_json(path, {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": tag,
                        "differences": [{"status": s, "path": r, "sha256": d} for s, r, d in rows]}, exclusive=True)
    print("LIBRARY %s: %d differences from the pre-run library recorded" % (tag, len(rows)))


def cmd_collect_logs(c):
    out = q(c, "evidence", "logs")
    problems = []
    if T.sfm_running():
        problems.append("sfm.exe is running")
    if pre(c) is None:
        problems.append("run pre first")
    if os.path.exists(out):
        problems.append("%s exists" % out)
    refuse(problems, "COLLECT-LOGS")
    os.makedirs(out)
    since = pre(c)["at_epoch"]
    copied = {}
    for name in sorted(os.listdir(p(c, "LOG_DIR"))):
        src = os.path.join(p(c, "LOG_DIR"), name)
        if name.endswith(".log") and os.path.getmtime(src) >= since - 1:
            digest = T.sha(src)
            T.copy_verified(src, os.path.join(out, name), digest)
            copied[name] = digest
    T.write_json(os.path.join(out, "LOGS.json"), {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "files": copied},
                 exclusive=True)
    print("LOGS COLLECTED: %d files" % len(copied))


def cmd_rollback(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    pr = pre(c)
    if pr is None:
        problems.append("run pre first")
    out = q(c, "evidence", "rollback.json")
    if os.path.exists(out):
        problems.append("rollback already ran")
    refuse(problems, "ROLLBACK")
    v100 = read_zip(c)
    library_before = T.inventory(p(c, "LIBRARY"))
    backup = q(c, "pre_run", "backup")
    for e, pin in ((CPM_ENTRY, c["pins"]["v100_cpm_sha256"]), (INV_ENTRY, c["pins"]["v100_inventory_sha256"]),
                   (SIG_ENTRY, c["pins"]["v100_signature_sha256"])):
        if not os.path.isfile(game(c, e)) or T.sha(game(c, e)) != pin:
            T.copy_verified(os.path.join(backup, os.path.basename(e)), game(c, e), pin)
    for n in REGISTRIES:
        if os.path.lexists(game(c, LIB + n)):
            os.remove(game(c, LIB + n))
    restore_housekeeping_and_pyc(c, pr)
    problems = []
    for e in v100_software(c, v100):
        f = game(c, e)
        if not os.path.isfile(f) or T.sha(f) != sha_bytes(v100[e]):
            problems.append("%s is not the v1.0.0 release file" % e)
    inv = dict((k, T.inventory(p(c, k))) for k in ("SCRIPTS_ROOT", "CFG_ROOT", "SESSIONS"))
    for k, v in inv.items():
        if v["sha256"] != pr["inventories"][k]["sha256"]:
            problems.append("%s differs from its pre-run baseline" % k)
    library_after = T.inventory(p(c, "LIBRARY"))
    if library_after["sha256"] != library_before["sha256"]:
        problems.append("the preset library changed during rollback")
    st, cpm = state(c)
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "installation": st, "installed_cpm_sha256": cpm,
              "v100_software_files_verified": len(v100_software(c, v100)), "inventory_problems": problems,
              "library_untouched": library_after["sha256"] == library_before["sha256"],
              "library_sha256": library_after["sha256"], "poses_folders_kept": poses_folders(c),
              "rolled_back": not problems and st == "v1.0.0"}
    T.write_json(out, result, exclusive=True)
    print(json.dumps(result, indent=1))
    print("ROLLED BACK to v1.0.0; the run's Poses folders are kept for the native v1.0.0 check" if result[
        "rolled_back"] else "ROLLBACK PROBLEMS - STOP and report (installation %s)" % st)


def cmd_cleanup(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    pr = pre(c)
    if pr is None or not os.path.isfile(q(c, "evidence", "rollback.json")):
        problems.append("run rollback (and the native v1.0.0 check) first")
    out = q(c, "evidence", "cleanup.json")
    if os.path.exists(out):
        problems.append("cleanup already ran")
    if state(c)[0] != "v1.0.0":
        problems.append("the installation is not v1.0.0")
    refuse(problems, "CLEANUP")
    rows = run_library_rows(c)
    keep = q(c, "evidence", "library_after")
    for status, rel, digest in rows:
        if status != "removed":
            dst = os.path.join(keep, *rel.split("/"))
            if not os.path.isdir(os.path.dirname(dst)):
                os.makedirs(os.path.dirname(dst))
            T.copy_verified(os.path.join(p(c, "LIBRARY"), *rel.split("/")), dst, digest)
    backup = q(c, "pre_run", "backup", "library")
    for status, rel, digest in rows:
        path = os.path.join(p(c, "LIBRARY"), *rel.split("/"))
        if status == "added":
            os.remove(path)
        else:
            src = os.path.join(backup, *rel.split("/"))
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            T.copy_verified(src, path, T.sha(src))
    removed_dirs = []
    for d, dirs, names in sorted(os.walk(p(c, "LIBRARY"), topdown=False), key=lambda x: -len(x[0])):
        rel = os.path.relpath(d, p(c, "LIBRARY"))
        if d != p(c, "LIBRARY") and not os.listdir(d) and not os.path.isdir(os.path.join(backup, rel)):
            os.rmdir(d)
            removed_dirs.append(rel.replace("\\", "/"))
    restore_housekeeping_and_pyc(c, pr)
    inv = dict((k, T.inventory(p(c, k))) for k in INVENTORIES)
    problems = ["%s differs from its pre-run baseline" % k for k, v in inv.items()
                if v["sha256"] != pr["inventories"][k]["sha256"]]
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "installation": state(c)[0],
              "library_differences_kept_in_evidence": [{"status": s, "path": r, "sha256": d} for s, r, d in rows],
              "removed_empty_folders": removed_dirs, "poses_folders_left": poses_folders(c),
              "inventories": dict((k, {"files": v["files"], "sha256": v["sha256"]}) for k, v in inv.items()),
              "inventory_problems": problems, "restored": not problems and not poses_folders(c)}
    T.write_json(out, result, exclusive=True)
    print(json.dumps(result, indent=1))
    print("RESTORED: v1.0.0 installed, preset library and every inventory equal their pre-run baselines" if result[
        "restored"] else "RESTORATION PROBLEMS - report")


def cmd_compare(c):
    sys.path.insert(0, HERE)
    import ps2_compare
    ps2_compare.main(c)


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    c = load(argv[1])
    cmd = argv[2]
    if cmd == "library":
        if len(argv) != 4:
            raise SystemExit("usage: ps2_tool.py PS2.json library TAG")
        return cmd_library(c, argv[3])
    table = {"package": cmd_package, "pre": cmd_pre, "install": cmd_install, "seed": cmd_seed, "check": cmd_check,
             "collect-logs": cmd_collect_logs, "rollback": cmd_rollback, "cleanup": cmd_cleanup,
             "compare": cmd_compare}
    if cmd not in table:
        raise SystemExit(__doc__)
    return table[cmd](c)


if __name__ == "__main__":
    main(sys.argv)
