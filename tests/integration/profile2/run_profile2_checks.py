# -*- coding: utf-8 -*-
"""Focused profile-2 integration checks (TEST-ONLY): Scripts > SFM Character Tools, bundled Animation Groups
data, and overlay onto an earlier installation. Scratch installations only; test keys only.

usage: <Python 3.10 with cryptography> -E -s -B tests/integration/profile2/run_profile2_checks.py
           --scratch NEW_DIR --py27 SFM_PYTHON27 --data DATA_V1_PACKAGE_DIR
       optional: SCT_OLD_INVENTORY_DIR = folder holding the earlier profile-1 signed inventory pair, to check
       that it is refused

Boundaries checked (and nothing else; accepted K/L/PRE/governor/updater fault evidence is reused):
  locators agree (CPM app, adapter, Normalizer, authority bootstrap, Quick Launch launcher path);
  CPM and the Normalizer acquire the same installed authority; mixed legacy/new locations refuse;
  profile 2 and the revised inventory spec are consistent, and a profile-1 inventory is not accepted;
  a fresh bundled-data installation is consistent; overlay onto an earlier installation, its updater
  remedy, and the documented retirement of the legacy menu entries.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
UPD = os.path.join(REPO, "updater")
sys.path.insert(0, UPD)
from sfm_character_tools_updater import official  # noqa: E402
from sfm_character_tools_updater.compat import inventory, profile  # noqa: E402

SPEC = os.path.join(UPD, "release_tools", "character_tools_software_v1.json")
PRODUCER = os.path.join(UPD, "release_tools", "make_software_inventory.py")
PKG_PRODUCER = os.path.join(UPD, "release_tools", "make_official_package.py")
TEST_WORKER = os.path.join(UPD, "tests", "support", "test_worker.py")
MENU = ("scripts", "sfm", "mainmenu", "SFM Character Tools")
LEGACY = ("scripts", "sfm", "mainmenu", "ChadChan3D")
ENTRIES = ("SFM_Character_Preset_Manager.py", "Rebuild_Control_Groups_Normalizer.py", "SFM_Control_Group_Updater.py")
# Documented retirement of a recognized earlier installation (README): exactly these, nothing else.
LEGACY_SUITE = ["SFM_Character_Preset_Manager.py", "Rebuild_Control_Groups_Normalizer.py",
                "SFM_Control_Group_Updater.py", "cpm_authority_adapter.py", "cpm_authority_adapter.pyc",
                "cpm_compat_v1_projection.py", "cpm_compat_v1_projection.pyc", "sfm_character_tools_inventory.json",
                "sfm_character_tools_inventory.sig", "sfm_master_authority_productionized", "sfm_master_sidecar"]
PROD_KEY_ID = "ed25519-5d879134807dff6d"
R, FACTS = [], {}


def check(name, ok, value=None):
    R.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if value is None else "  -> %s" % (value,)))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rd(p):
    with open(p, "rb") as f:
        return f.read()


def wr(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def git_show(rev, rel):
    return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, rel)], capture_output=True, check=True).stdout


def run_tool(script, *args):
    cp = subprocess.run([sys.executable, "-E", "-s", "-B", script] + list(args), capture_output=True, text=True,
                        timeout=900)
    if cp.returncode:
        raise SystemExit("%s failed: %s" % (os.path.basename(script), cp.stderr[-600:]))
    return json.loads(cp.stdout.strip().splitlines()[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--py27", required=True)
    ap.add_argument("--data", required=True)
    a = ap.parse_args()
    S = os.path.abspath(a.scratch)
    if os.path.exists(S):
        raise SystemExit("scratch folder exists")
    os.makedirs(S)

    def probe(scenario, game):
        cp = subprocess.run([a.py27, "-E", "-B", os.path.join(HERE, "py27_probe.py"), scenario, game, REPO],
                            capture_output=True, text=True, timeout=900)
        try:
            return json.loads(cp.stdout.strip().splitlines()[-1])
        except Exception:
            return {"error": (cp.stdout[-800:], cp.stderr[-1500:])}

    # -- 1. Profile 2 and the revised spec ----------------------------------------------------------
    p1, p2 = profile.PROFILE_1, profile.PROFILE_2
    same = [k for k in p1 if k not in ("profile_id", "installation_layout") and p1[k] == p2[k]]
    lay = {k for k in set(p1["installation_layout"]) | set(p2["installation_layout"])
           if p1["installation_layout"].get(k) != p2["installation_layout"].get(k)}
    check("profile 2: identical to profile 1 except id and layout (contract, software_dir, software_inventory)",
          len(same) == len(p1) - 2 and lay == {"contract", "software_dir", "software_inventory"}, sorted(lay))
    check("profile 1 contract unchanged (2bbd93d0…); updater implements exactly profile 2",
          profile.contract_sha256(p1).startswith("2bbd93d0") and sorted(profile.PROFILES) == ["sct-authority-profile-2"]
          and official.SUPPORTED_PROFILES == {"sct-authority-profile-2"})
    FACTS["profile_2_contract_sha256"] = profile.PROFILE_SHA256["sct-authority-profile-2"]
    check("inventory location = profile 2 software_inventory",
          inventory.INVENTORY_REL.replace("\\", "/") == p2["installation_layout"]["software_inventory"])
    spec = json.loads(rd(SPEC))
    bad = [f["source"] for f in spec["files"] if sha(rd(os.path.join(REPO, *f["source"].split("/")))) != f["sha256"]]
    menu_prefix = "/".join(MENU) + "/"
    check("spec: 31 files, 9 roles, profile 2, every source matches, 30 under the new menu folder, none under ChadChan3D",
          len(spec["files"]) == 31 and len({f["role"] for f in spec["files"]}) == 9
          and spec["authority_profile"] == "sct-authority-profile-2" and not bad
          and sum(f["path"].startswith(menu_prefix) for f in spec["files"]) == 30
          and not any("/ChadChan3D/" in f["path"] for f in spec["files"]), bad)
    old = json.loads(git_show("25860bac12789b6cd1c1b7a25d69db62bcb2d0e6", "updater/release_tools/character_tools_software_v1.json"))
    old_by_role_path = {(f["role"], f["path"].split("/")[-1]): f["sha256"] for f in old["files"]}
    changed = sorted(f["path"].split("/")[-1] for f in spec["files"]
                     if old_by_role_path.get((f["role"], f["path"].split("/")[-1])) != f["sha256"])
    check("spec: only the four files whose locator changed have new identities", changed == sorted(
        ["SFM_Character_Preset_Manager.py", "Rebuild_Control_Groups_Normalizer.py", "cpm_authority_adapter.py",
         "bootstrap.py"]), changed)
    check("launcher and optional button outside the inventory",
          not any(f["path"].endswith(("SFM_Control_Group_Updater.py", "cpm_ase_quick_launch.py",
                                      "ChadChan3D_CPM_ASE_Button.py")) for f in spec["files"]))

    # -- 2. Release-shaped usermod tree (test-signed inventory) and the unsigned production inventory ---
    run_tool(PRODUCER, "stage", "--spec", SPEC, "--out", os.path.join(S, "stage", "usermod"))
    keys = os.path.join(S, "keys")
    os.makedirs(keys)
    run_tool(PKG_PRODUCER, "keygen", "--private", os.path.join(keys, "test.pem"), "--public", os.path.join(keys, "test.pub"))
    test_pub = rd(os.path.join(keys, "test.pub")).decode().strip()
    signed = run_tool(PRODUCER, "sign", "--spec", SPEC, "--root", os.path.join(S, "stage", "usermod"),
                      "--software-version", "1.0.0", "--private", os.path.join(keys, "test.pem"),
                      "--out", os.path.join(S, "test_inventory"))
    entries = []
    for f in spec["files"]:
        data = rd(os.path.join(S, "stage", "usermod", *f["path"].split("/")))
        entries.append({"path": f["path"], "role": f["role"], "byte_length": len(data), "sha256": sha(data)})
    p = profile.PROFILES["sct-authority-profile-2"]
    unsigned = {"schema": 1, "object_type": inventory.OBJECT_TYPE, "software": spec["software"], "software_version": "1.0.0",
                "authority_profile": "sct-authority-profile-2",
                "profile_contract_sha256": profile.PROFILE_SHA256["sct-authority-profile-2"],
                "runtime_api_version": p["runtime"]["api_version"], "runtime_build_id": p["runtime"]["build_id"],
                "signing_key_id": PROD_KEY_ID, "files": entries}
    ub = (json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")
    inventory.parse(ub)
    wr(os.path.join(S, "unsigned_production_inventory.json"), ub)
    FACTS["unsigned_production_inventory_sha256"] = sha(ub)
    FACTS["unsigned_production_inventory_bytes"] = len(ub)
    tb = rd(os.path.join(S, "test_inventory", "sfm_character_tools_inventory.json"))
    check("test-signed and unsigned production inventories differ only in signing_key_id",
          {k: v for k, v in json.loads(tb).items() if k != "signing_key_id"} ==
          {k: v for k, v in unsigned.items() if k != "signing_key_id"})

    rel = os.path.join(S, "release_usermod")
    shutil.copytree(os.path.join(S, "stage", "usermod"), rel)
    for n in ("sfm_character_tools_inventory.json", "sfm_character_tools_inventory.sig"):
        shutil.copyfile(os.path.join(S, "test_inventory", n), os.path.join(rel, *MENU, n))
    shutil.copyfile(os.path.join(UPD, "menu", "SFM_Control_Group_Updater.py"), os.path.join(rel, *MENU, "SFM_Control_Group_Updater.py"))
    side = [n for n in os.listdir(a.data) if n.endswith(".sfmsidecar")][0]
    wr(os.path.join(rel, "cfg", "sfm_defaultanimationgroups.txt"), rd(os.path.join(a.data, "sfm_defaultanimationgroups.txt")))
    wr(os.path.join(rel, "cfg", "sfm_shared_authority", "manifest.json"), rd(os.path.join(a.data, "manifest.json")))
    wr(os.path.join(rel, "cfg", "sfm_shared_authority", side), rd(os.path.join(a.data, side)))
    bundled = {k: sha(rd(os.path.join(rel, "cfg", *k.split("/")))) for k in
               ("sfm_defaultanimationgroups.txt", "sfm_shared_authority/manifest.json", "sfm_shared_authority/" + side)}
    check("bundled data = approved Candidate C: Master 1d855cd3…, sidecar 37916775…, manifest 6c756806…",
          bundled["sfm_defaultanimationgroups.txt"].startswith("1d855cd3") and side.startswith("sfm_master_0_37916775")
          and bundled["sfm_shared_authority/" + side].startswith("37916775")
          and bundled["sfm_shared_authority/manifest.json"].startswith("6c756806"))
    worker_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

    def worker(game, name, *args):
        cfg = os.path.join(game, "usermod", "cfg")
        res = os.path.join(S, "results", name + ".json")
        os.makedirs(os.path.dirname(res), exist_ok=True)
        cmd = [sys.executable, "-E", "-s", "-B", TEST_WORKER, "--scratch-root", S, "--inject", "process=clear",
               "--trust-key", test_pub] + list(args) + ["--installation", cfg, "--result", res]
        cp = subprocess.run(cmd, capture_output=True, text=True, env=worker_env, timeout=900)
        return json.load(open(res, encoding="utf-8")) if os.path.exists(res) else {"error": cp.stderr[-800:]}

    # -- 3. Fresh installation: one copy of the root usermod -------------------------------------------
    fresh = os.path.join(S, "Steam Library", "fresh", "SourceFilmmaker", "game")
    shutil.copytree(rel, os.path.join(fresh, "usermod"))
    loc = probe("locators", fresh)
    want = loc.get("expected")
    check("locators: CPM app, adapter, Normalizer and authority bootstrap all name ...\\mainmenu\\SFM Character Tools "
          "(installation path with spaces)", want and all(loc.get(k) == want for k in ("cpm_app", "adapter", "normalizer", "bootstrap"))
          and want.endswith(os.path.join("mainmenu", "SFM Character Tools")) and " " in want, loc)
    check("Quick Launch opens CPM through ...\\SFM Character Tools\\SFM_Character_Preset_Manager.py (file present)",
          loc.get("quick_launch_launcher") == os.path.join(want or "", "SFM_Character_Preset_Manager.py")
          and os.path.isfile(loc.get("quick_launch_launcher") or ""))
    check("adapter and authority package load from the new menu folder", loc.get("origins", {}).get("adapter") == want
          and loc.get("origins", {}).get("package") == want, loc.get("origins"))
    acq = probe("acquire", fresh)
    check("fresh: Normalizer then CPM acquire the installed authority through the same broker, generation = Master",
          acq.get("same_broker") is True and acq.get("canonical") is True and acq.get("cpm", {}).get("source_sha256")
          == acq.get("master_sha256") == bundled["sfm_defaultanimationgroups.txt"] and acq.get("cpm", {}).get("answers") == 2,
          acq)
    st = worker(fresh, "fresh_status", "status")
    check("fresh: updater status - installed data consistent (one sidecar binding the Master, manifest binding both)",
          (st.get("correspondence") or {}).get("ok") is True, (st.get("correspondence") or {}).get("problems") or st.get("error"))
    pr = worker(fresh, "fresh_prepare_rebuild", "prepare-rebuild")
    ins = worker(fresh, "fresh_install_noop", "install", "--prepared", pr.get("prepid", "x"),
                 "--confirm-sha", bundled["sfm_defaultanimationgroups.txt"])
    check("fresh: Update Using SFM's TXT is a verified NOOP (software inventory verified under profile 2)",
          pr.get("outcome") == "PREPARED" and ins.get("outcome") == "NOOP", (pr.get("outcome"), ins.get("outcome"), ins.get("message")))
    menu_entries = sorted(n for n in os.listdir(os.path.join(fresh, "usermod", *MENU)) if n in ENTRIES)
    check("fresh: the three menu entries are in Scripts > SFM Character Tools; no ChadChan3D menu folder",
          menu_entries == sorted(ENTRIES) and not os.path.exists(os.path.join(fresh, "usermod", *LEGACY)))

    # A profile-1 inventory (the earlier signed one) at the new location is not accepted.
    p1game = os.path.join(S, "Steam Library", "p1", "SourceFilmmaker", "game")
    shutil.copytree(os.path.join(fresh, "usermod", "scripts"), os.path.join(p1game, "usermod", "scripts"))
    os.makedirs(os.path.join(p1game, "usermod", "cfg"))
    staged_old = os.environ.get("SCT_OLD_INVENTORY_DIR")
    if staged_old:
        for n in ("sfm_character_tools_inventory.json", "sfm_character_tools_inventory.sig"):
            shutil.copyfile(os.path.join(staged_old, n), os.path.join(p1game, "usermod", *MENU, n))
        import types
        try:
            inventory.verify_installation(types.SimpleNamespace(cfg=os.path.join(p1game, "usermod", "cfg")))
            r1 = "ACCEPTED"
        except Exception as e:
            r1 = "%s %s" % (getattr(e, "message_key", type(e).__name__), (getattr(e, "details", {}) or {}).get("reason"))
        check("the earlier production-signed profile-1 inventory is refused (not weakened to accept it)",
              r1.startswith("SOFTWARE_UNSUPPORTED"), r1)

    # -- 4. Overlay onto an earlier installation -------------------------------------------------------
    leg = os.path.join(S, "Steam Library", "legacy", "SourceFilmmaker", "game")
    um = os.path.join(leg, "usermod")
    base = "25860bac12789b6cd1c1b7a25d69db62bcb2d0e6"
    for f in old["files"]:
        wr(os.path.join(um, *f["path"].split("/")), git_show(base, f["source"]))
    wr(os.path.join(um, *LEGACY, "cpm_authority_adapter.pyc"), b"\x03\xf3\r\nstale bytecode")
    wr(os.path.join(um, *LEGACY, "My_Unrelated_Tool.py"), b"# an unrelated user script\n")
    wr(os.path.join(um, *LEGACY, "README.txt"), b"unrelated\n")
    g1 = git_show("baca3f40f3885176e1dd782c88b55d5f22c3535c~1", "sfm_defaultanimationgroups.txt")
    wr(os.path.join(um, "cfg", "sfm_defaultanimationgroups.txt"), g1)
    from sfm_character_tools_updater import candidate as cand
    d = cand.deps()
    out = d["compiler"].parse_and_compile(d["compiler"].SourceSnapshot("rebuild", g1))
    name = d["compiler"].generation_basename(out.ordinary_sha256)
    wr(os.path.join(um, "cfg", "sfm_shared_authority", name), out.blob)
    wr(os.path.join(um, "cfg", "sfm_shared_authority", "manifest.json"),
       d["manifest"].serialize_manifest(d["manifest"].build_manifest_dict(out, name)))
    FACTS["legacy_g1"] = {"master": sha(g1)[:16], "sidecar": name}
    shutil.copytree(rel, um, dirs_exist_ok=True)            # Windows-style folder merge: replace same names
    auth = sorted(os.listdir(os.path.join(um, "cfg", "sfm_shared_authority")))
    check("overlay: Master/manifest replaced, new sidecar added; the earlier sidecar REMAINS (two sidecars)",
          sha(rd(os.path.join(um, "cfg", "sfm_defaultanimationgroups.txt"))) == bundled["sfm_defaultanimationgroups.txt"]
          and len([n for n in auth if n.endswith(".sfmsidecar")]) == 2, auth)
    acq2 = probe("acquire", leg)
    check("overlay: CPM and the Normalizer still acquire the new generation (the earlier sidecar is skipped)",
          acq2.get("same_broker") is True and acq2.get("cpm", {}).get("source_sha256") == bundled["sfm_defaultanimationgroups.txt"],
          acq2.get("cpm") or acq2)
    st2 = worker(leg, "overlay_status", "status")
    probs = (st2.get("correspondence") or {}).get("problems") or []
    check("overlay: updater status reports the extra sidecar (expected exactly one) - material, documented",
          (st2.get("correspondence") or {}).get("ok") is False and any("exactly one" in p for p in probs), probs)
    FACTS["overlay_status_problems"] = probs
    m1 = probe("mixed_legacy_first", leg)
    check("mixed: legacy package loaded first -> new Normalizer and new CPM refuse (wrong origin)",
          m1.get("normalizer", [""])[0] == "REFUSED" and m1.get("cpm", [""])[0] == "REFUSED", m1)
    m2 = probe("mixed_new_first", leg)
    check("mixed: new authority loaded first -> legacy CPM adapter refuses", m2.get("normalizer", [""])[0] == "OK"
          and m2.get("legacy_adapter", [""])[0] == "REFUSED", m2)
    pr2 = worker(leg, "overlay_prepare_rebuild", "prepare-rebuild")
    ins2 = worker(leg, "overlay_install", "install", "--prepared", pr2.get("prepid", "x"),
                  "--confirm-sha", bundled["sfm_defaultanimationgroups.txt"])
    st3 = worker(leg, "overlay_status_after", "status")
    auth2 = sorted(os.listdir(os.path.join(um, "cfg", "sfm_shared_authority")))
    retired = []
    for dp, dn, fn in os.walk(os.path.join(um, "cfg", "sfm_character_tools_updater", "transactions")):
        retired += [os.path.basename(dp) for n in fn if n == name]
    check("remedy: Update Using SFM's TXT installs the same data, retires the earlier sidecar into recovery storage; "
          "status consistent; exactly one sidecar", pr2.get("outcome") == "PREPARED" and ins2.get("outcome") == "COMPLETE"
          and (st3.get("correspondence") or {}).get("ok") is True and len([n for n in auth2 if n.endswith(".sfmsidecar")]) == 1
          and "retired" in retired, (pr2.get("outcome"), ins2.get("outcome"), ins2.get("message"), auth2, retired))
    before = sorted(os.listdir(os.path.join(um, *LEGACY)))
    for n in LEGACY_SUITE:
        t = os.path.join(um, *LEGACY, n)
        if os.path.isdir(t):
            shutil.rmtree(t)
        elif os.path.exists(t):
            os.remove(t)
    after = sorted(os.listdir(os.path.join(um, *LEGACY)))
    entries_all = []
    for dp, dn, fn in os.walk(os.path.join(um, "scripts", "sfm", "mainmenu")):
        entries_all += [n for n in fn if n in ENTRIES]
    check("documented migration: only the suite files leave mainmenu\\ChadChan3D; unrelated files kept; "
          "each menu entry exists exactly once (in SFM Character Tools)",
          after == ["My_Unrelated_Tool.py", "README.txt"] and sorted(entries_all) == sorted(ENTRIES), (before, after))
    st4 = worker(leg, "after_migration_status", "status")
    check("after migration: updater status still consistent", (st4.get("correspondence") or {}).get("ok") is True)

    json.dump({"facts": FACTS, "results": R, "test_inventory": signed}, open(os.path.join(S, "results.json"), "w"), indent=1)
    print(json.dumps(FACTS, indent=1))
    passed = sum(1 for r in R if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(R), "ALL PASS" if passed == len(R) else "SOME FAILED"))
    sys.exit(0 if passed == len(R) else 1)


if __name__ == "__main__":
    main()
