# -*- coding: utf-8 -*-
"""SFM Character Tools v1.1.0 release candidate 1: build the UNSIGNED package and verify its release readiness
offline. Python 3, run with -I. Nothing here installs, signs, publishes or touches an SFM installation.

Reuses the PS-2 kit's packager unchanged (real_sfm_qualification/f01_ps2_v110/tools/ps2_tool.py: the published
v1.0.0 ZIP's exact bytes, the candidate CPM and both registries, the generated unsigned inventory, the deterministic
ZIP), with this folder's SOFTWARE_SPEC.json in place of the historical candidate spec.

  package   build Q/package (new folder): stage/, the deterministic ZIP and PACKAGE_MANIFEST.json
  verify    read-only checks of the built package, written to Q/RC_VERIFY.json (exclusive create):
              package     the manifest, every staged file and the ZIP are intact; the changes against v1.0.0 are
                          exactly the CPM, the inventory (unsigned) and the two added registries
              updater     the shipped updater's own inventory.parse, check_profile and check_files accept the
                          inventory and the staged files
              version     the CPM's own prod_release_version reads 1.1.0 from the staged inventory for this CPM
                          build (and nothing for another build)
              installer   the Workshop installer's own core.prepare accepts the package with v1.1.0 release
                          constants derived from it and a PLACEHOLDER signature (presence only; prepare never
                          verifies the signature), in a temporary copy that is deleted afterwards
              rollback    the published v1.0.0 ZIP is the pinned archive; every v1.0.0 file the package keeps is its
                          exact bytes; the v1.0.0 CPM never reads the added registries

usage: python -I rc_tool.py RC.json package | verify
"""
from __future__ import print_function

import ast
import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "real_sfm_qualification", "f01_ps2_v110", "tools"))
import ps2_tool as P  # noqa: E402

P.FORMAT = "F01-V110-RC-config-v1"
P.ZIP_NAME = "SFM.Character.Tools.v1.1.0-rc1-UNSIGNED.zip"
P.ZIP_TIME = (2026, 11, 18, 0, 0, 0)
SPEC = os.path.join(HERE, "SOFTWARE_SPEC.json")
T = P.T


def spec(c):
    if T.sha(SPEC) != c["pins"]["spec_sha256"]:
        raise SystemExit("REFUSED: the v1.1.0 RC spec is not %s" % c["pins"]["spec_sha256"])
    return T.read_json(SPEC)


P.spec = spec


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def staged(c):
    m = T.read_json(P.q(c, "package", "PACKAGE_MANIFEST.json"))
    files = {}
    for r in m["files"]:
        with open(os.path.join(P.q(c, "package", "stage"), *r["path"].split("/")), "rb") as f:
            files[r["path"]] = f.read()
    return m, files


def check_package(c, R):
    problems = P.package_problems(c)
    m, files = staged(c)
    v100 = P.read_zip(c)
    changed = sorted(n for n in files if n in v100 and files[n] != v100[n])
    added = sorted(n for n in files if n not in v100)
    removed = sorted(n for n in v100 if n not in files)
    want = (sorted([P.CPM_ENTRY, P.INV_ENTRY]), sorted(P.LIB + n for n in P.REGISTRIES), [P.SIG_ENTRY])
    R["package"] = {"zip": m["zip"], "zip_sha256": m["zip_sha256"], "entries": m["entries"],
                    "inventory_sha256": m["candidate_inventory_sha256"], "changed": changed, "added": added,
                    "removed": removed, "problems": problems,
                    "pass": not problems and (changed, added, removed) == want}
    return files, v100


def check_updater(c, R, files):
    sys.path.insert(0, os.path.join(REPO, "updater"))
    from sfm_character_tools_updater.compat import inventory
    data = files[P.INV_ENTRY]
    out = {}
    try:
        d = inventory.parse(data)
        out["parse"] = True
        p = inventory.check_profile(d)
        out["check_profile"] = p is not None
        inventory.check_files(os.path.join(P.q(c, "package", "stage"), "usermod"), d)
        out["check_files"] = len(d["files"])
        out.update(software_version=d["software_version"], authority_profile=d["authority_profile"],
                   signing_key_id=d["signing_key_id"])
        sp = spec(c)
        out["inventory_equals_spec"] = [(f["path"], f["role"], f["sha256"], f["byte_length"]) for f in d["files"]] == \
            [(f["path"], f["role"], f["sha256"], f["byte_length"]) for f in sp["files"]]
        out["pass"] = (out["inventory_equals_spec"] and d["software_version"] == c["pins"]["software_version"]
                       and out["check_files"] == len(sp["files"]))
    except Exception as e:  # a Stop or anything else is a failed check, reported
        out.update(error="%s: %s" % (type(e).__name__, str(e)[:300]), pass_=False)
        out["pass"] = False
    R["updater"] = out


def release_version_function(cpm):
    """The CPM's own prod_release_version, compiled from its source alone (the module needs SFM to import)."""
    tree = ast.parse(cpm)
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "prod_release_version"]
    g = {"os": os, "json": json, "hashlib": hashlib, "re": importlib.import_module("re")}
    exec(compile(ast.Module(body=fn, type_ignores=[]), "prod_release_version", "exec"), g)
    return g["prod_release_version"]


def check_version(c, R, files):
    f = release_version_function(files[P.CPM_ENTRY])
    inv = os.path.join(P.q(c, "package", "stage"), *P.INV_ENTRY.split("/"))
    mine = f(inventory_path=inv, build_sha256=sha_bytes(files[P.CPM_ENTRY]))
    other = f(inventory_path=inv, build_sha256="0" * 64)
    R["version"] = {"this_build": mine, "another_build": other,
                    "pass": mine == c["pins"]["software_version"] and other is None}


def check_installer(c, R, files):
    sys.path.insert(0, REPO)
    release = importlib.import_module("workshop_installer.release")
    core = importlib.import_module("workshop_installer.core")
    saved = dict((k, getattr(release, k)) for k in ("VERSION", "ARCHIVE", "SHA256", "ARCHIVE_ENTRIES",
                                                     "INVENTORY_ENTRIES", "PATHS"))
    saved_core = core.RELEASE_SHA256
    tmp = tempfile.mkdtemp(prefix="sct_rc1_installer_dryrun_")
    out = {"signature": "PLACEHOLDER (64 zero bytes; presence only, never distributed)"}
    try:
        z = dict(files)
        z[P.SIG_ENTRY] = b"\0" * 64
        zpath = os.path.join(tmp, "SFM.Character.Tools.v1.1.0-rc1-DRYRUN.zip")
        P.write_zip(zpath, z)
        mapped = set()
        for name in z:
            rel = core._map_member(name)
            if rel is not None:
                mapped.add(rel)
        new = set(release.PATHS) | set(n[len("usermod/"):] for n in (P.LIB + r for r in P.REGISTRIES))
        out["paths_mapped_equal_v100_plus_registries"] = mapped == new
        release.VERSION, release.ARCHIVE = c["pins"]["software_version"], os.path.basename(zpath)
        release.SHA256 = core.RELEASE_SHA256 = core.digest_file(zpath)
        release.ARCHIVE_ENTRIES, release.INVENTORY_ENTRIES = len(z), len(spec(c)["files"])
        release.PATHS = tuple(sorted(new))
        helper = os.path.join(tmp, "SCT_Setup_placeholder.exe")
        with open(helper, "xb") as f:
            f.write(b"placeholder setup executable for the dry run")
        prepared = core.prepare(zpath, helper)
        try:
            out["prepare"] = True
            out["prepared_files"] = len(prepared.files)
            out["registries_prepared"] = all(("scripts/SFM Character Tools/" + r) in prepared.files
                                             for r in P.REGISTRIES)
            out["cpm_prepared"] = prepared.files.get(P.CPM_ENTRY[len("usermod/"):]) == sha_bytes(files[P.CPM_ENTRY])
        finally:
            prepared.close()
        out["release_constants_for_v110"] = {"VERSION": release.VERSION, "ARCHIVE_ENTRIES_with_signature": len(z),
                                             "INVENTORY_ENTRIES": release.INVENTORY_ENTRIES,
                                             "PATHS_added": sorted(new - set(saved["PATHS"]))}
        out["pass"] = (out["paths_mapped_equal_v100_plus_registries"] and out["prepare"] and
                       out["registries_prepared"] and out["cpm_prepared"])
    except Exception as e:
        out.update(error="%s: %s" % (type(e).__name__, str(e)[:300]))
        out["pass"] = False
    finally:
        for k, v in saved.items():
            setattr(release, k, v)
        core.RELEASE_SHA256 = saved_core
        shutil.rmtree(tmp, True)
    R["installer"] = out


def check_rollback(c, R, files, v100):
    kept = [n for n in files if n in v100 and n not in (P.CPM_ENTRY, P.INV_ENTRY)]
    v100_cpm = v100[P.CPM_ENTRY]
    out = {"v100_zip_pinned": T.sha(P.p(c, "V100_ZIP")) == c["pins"]["v100_zip_sha256"],
           "v100_files_kept_exact": len(kept), "v100_files_kept_all_exact": all(files[n] == v100[n] for n in kept),
           "v100_cpm": sha_bytes(v100_cpm),
           "v100_cpm_reads_no_registry": not any(r.encode("ascii") in v100_cpm for r in P.REGISTRIES)}
    out["pass"] = out["v100_zip_pinned"] and out["v100_files_kept_all_exact"] and out["v100_cpm_reads_no_registry"] \
        and out["v100_cpm"] == c["pins"]["v100_cpm_sha256"]
    R["rollback"] = out


def cmd_verify(c):
    path = P.q(c, "RC_VERIFY.json")
    if os.path.exists(path):
        raise SystemExit("REFUSED: %s exists" % path)
    R = {"format": "SCT-V110-RC1-verify-v1", "spec_sha256": T.sha(SPEC), "tool_sha256": T.sha(__file__)}
    files, v100 = check_package(c, R)
    check_updater(c, R, files)
    check_version(c, R, files)
    check_installer(c, R, files)
    check_rollback(c, R, files, v100)
    R["pass"] = all(R[k]["pass"] for k in ("package", "updater", "version", "installer", "rollback"))
    T.write_json(path, R, exclusive=True)
    print(json.dumps(R, indent=1))
    print("RC VERIFY %s" % ("PASS" if R["pass"] else "FAIL"))
    return 0 if R["pass"] else 1


def main(argv):
    if len(argv) != 3 or argv[2] not in ("package", "verify"):
        raise SystemExit(__doc__)
    c = P.load(argv[1])
    return P.cmd_package(c) if argv[2] == "package" else cmd_verify(c)


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
