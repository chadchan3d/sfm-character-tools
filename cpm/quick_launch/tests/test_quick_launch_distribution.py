# -*- coding: utf-8 -*-
"""QL-3 offline checks of the optional Quick Launch ZIP (Python 3).

Builds the archive twice into a temporary folder and checks:
  - the builds are byte-identical (deterministic);
  - the archive holds exactly README.txt, SHA256SUMS.txt and the two program files under one root;
  - the program files are byte-identical to the repository and to the QL-2-qualified identities;
  - SHA256SUMS.txt is correct for those files;
  - the README documents fresh install, recognized-version update, unknown-file refusal, disable/enable, removal
    and troubleshooting, and never tells the user to touch Autoinit's files or the CPM folder;
  - the component stays outside the signed core software inventory;
  - the builder refuses a modified program file and an existing output.

usage: py -3 test_quick_launch_distribution.py
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
QL = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(QL, os.pardir, os.pardir))
DIST = os.path.join(QL, "distribution")
QL2 = {"usermod/scripts/sfm/autoinit/ChadChan3D/ChadChan3D_CPM_ASE_Button.py":
       "23e3a8813057642400b7e06e0b55e13c89f47b684779d907740905a5e28e4070",
       "usermod/scripts/ChadChan3D_CPM/cpm_ase_quick_launch.py":
       "4558d296505416591c79d08ecc9aa2fcaa0710003dbaaad94422e7654229f56f"}
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or value is None else "  value=%r" % (value,)))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_builder():
    spec = importlib.util.spec_from_file_location("ql_builder", os.path.join(DIST, "make_quick_launch_archive.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    builder = load_builder()
    record = json.load(open(os.path.join(DIST, "quick_launch_component_v1.json"), encoding="utf-8"))
    root = record["distribution"]["archive_root"]
    tmp = tempfile.mkdtemp(prefix="ql3_")
    try:
        a, b = os.path.join(tmp, "a.zip"), os.path.join(tmp, "b.zip")
        builder.build(a)
        builder.build(b)
        da, db = open(a, "rb").read(), open(b, "rb").read()
        check("deterministic: two builds are byte-identical", da == db, (sha(da), sha(db)))

        with zipfile.ZipFile(a) as z:
            names = z.namelist()
            content = {n: z.read(n) for n in names}
            stored = all(i.compress_type == zipfile.ZIP_STORED for i in z.infolist())
        expected = [root + "/README.txt", root + "/SHA256SUMS.txt"] + [root + "/" + p for p in
                                                                       [f["installed_path"] for f in record["files"]]]
        check("layout: exactly README, SHA256SUMS and the two program files, in order, under one root",
              names == expected and stored, names)
        for f in record["files"]:
            data = content[root + "/" + f["installed_path"]]
            repo_bytes = open(os.path.join(REPO, *f["source"].split("/")), "rb").read()
            check("identity: %s byte-identical to the repository and the QL-2 identity" % f["installed_path"],
                  data == repo_bytes and sha(data) == QL2[f["installed_path"]] == f["sha256"], sha(data))
        sums = content[root + "/SHA256SUMS.txt"].decode("ascii").splitlines()
        check("SHA256SUMS.txt lists both program files correctly",
              sorted(sums) == sorted("%s  %s" % (h, p) for p, h in QL2.items()), sums)

        readme = content[root + "/README.txt"].decode("ascii")
        sections = ["BEFORE YOU START", "STEP 1: CHECK WHAT IS ALREADY THERE", "FRESH INSTALL",
                    "UPDATE (replacing a recognized earlier version)", "TURN THE BUTTON OFF OR ON", "REMOVE",
                    "TROUBLESHOOTING"]
        flat = " ".join(readme.split())   # phrase checks ignore line wrapping and indentation
        check("README: every required section present", all(s in readme for s in sections),
              [s for s in sections if s not in readme])
        check("README: unknown or partial installations stop without copying",
              "STOP. Do not copy anything." in flat and "Only one exists, or a fingerprint" in flat
              and "Never copy this download over existing files without this check." in flat)
        check("README: update replaces both files together and keeps the off setting",
              "Replace BOTH files A and B" in flat and "Never update only one of them" in flat
              and "it stays off after an update" in flat)
        check("README: removal deletes only the two files and keeps the CPM folder",
              "Delete file A and file B (only these two files)." in flat
              and "Do NOT delete the ChadChan3D_CPM folder" in flat)
        check("README: requires but never includes or changes Autoinit Manager",
              "Autoinit Manager (Steam Workshop item 3400621327)" in flat
              and "This download does not include or change Autoinit Manager." in flat
              and "autoinit_skipped" not in readme and "sfm_init_local" not in readme)
        check("README: Scripts-menu fallback documented",
              "Scripts > ChadChan3D > SFM_Character_Preset_Manager" in flat)
        check("record: outside the core inventory and the updater; manual-distribution exception recorded",
              record["core_inventory"].startswith("NOT LISTED") and "Blueprint" in record["distribution"]["blueprint_exception"])
        spec = json.load(open(os.path.join(REPO, "updater", "release_tools", "character_tools_software_v1.json")))
        listed = set(e["path"] for e in spec["files"])
        check("core inventory spec does not list either Quick Launch file",
              not any(p.replace("usermod/", "", 1) in listed for p in QL2), sorted(listed & set(QL2)))

        # Refusals: an existing output, and a modified program file.
        try:
            builder.build(a)
            refused_existing = False
        except SystemExit as exc:
            refused_existing = "already exists" in str(exc)
        check("builder refuses to overwrite an existing archive", refused_existing)
        fake_repo = os.path.join(tmp, "repo")
        src = record["files"][1]["source"]
        os.makedirs(os.path.dirname(os.path.join(fake_repo, *src.split("/"))))
        for f in record["files"]:
            target = os.path.join(fake_repo, *f["source"].split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(os.path.join(REPO, *f["source"].split("/")), target)
        with open(os.path.join(fake_repo, *src.split("/")), "ab") as fh:
            fh.write(b"\n# modified\n")
        builder.REPO = fake_repo
        try:
            builder.build(os.path.join(tmp, "c.zip"))
            refused_modified = False
        except SystemExit as exc:
            refused_modified = "does not match the recorded QL-2 identity" in str(exc)
        check("builder refuses a modified program file", refused_modified and not os.path.exists(os.path.join(tmp, "c.zip")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
