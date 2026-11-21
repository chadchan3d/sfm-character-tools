# -*- coding: utf-8 -*-
"""Workshop Setup v1.1.0 native upgrade acceptance (WU): backup, automated checks and exact restoration around the
Owner's hands-on test. Python 3, -I, with SFM closed (every command refuses while sfm.exe runs).

The test upgrades the Owner's existing v1.0.0 Workshop Setup installation with the staged v1.1.0 Setup (run from the
staging folder, so the Steam-managed Workshop files are never touched), then uninstalls with the updated Manage
Installation, then restores the exact pre-test v1.0.0 state from the backup.

  pre             require the v1.0.0 Workshop installation (installation record 5323b143..., CPM ccbed9d7...); back up
                  usermod/scripts, usermod/cfg, usermod/tools and the preset library; record their inventories and
                  the Workshop payload's; copy the R2 fixture as Q/sessions/WU_SESSION.dmx
  launch          start the staged SCT_Setup.exe --game GAME (the Owner then reviews and chooses Update)
  check-update    after Setup's update: record 1.1.0 / 0f64eb13...; every managed file is the package's; helper and
                  launcher pins; nothing outside the managed set, installer state, bytecode and SFM housekeeping
                  changed; the library and the Workshop payload unchanged       -> Q/evidence/CHECK_UPDATE.json
  check-uninstall after Manage Installation's uninstall: managed programs, registries and launcher gone; the TXT, every
                  TXT backup and every non-managed file kept; no pre-existing library file changed or deleted; the
                  Workshop payload unchanged                                    -> Q/evidence/CHECK_UNINSTALL.json
  restore         make the three usermod trees and the library equal to the backup again (files added since pre are
                  moved to Q/evidence/after_restore_removed/, never deleted), then verify -> Q/evidence/RESTORE.json

usage: python -I wu_tool.py WU.json pre | launch | check-update | check-uninstall | restore
"""
from __future__ import print_function

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import zipfile

TREES = ("usermod/scripts", "usermod/cfg", "usermod/tools")
WORKSHOP = "workshop/scripts/sfm/mainmenu/SFM Character Tools"
STATE = "usermod/cfg/sfm_character_tools_installer"
RECORD = STATE + "/installation.json"
MASTER = "usermod/cfg/sfm_defaultanimationgroups.txt"
HELPER = "usermod/tools/SFM Character Tools Installer/SCT_Setup.exe"
MANAGER = "usermod/scripts/sfm/mainmenu/SFM Character Tools/Manage Installation.py"
CPM = "usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py"
REGISTRIES = ("usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json",
              "usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json")
UPDATER_BACKUPS = "usermod/cfg/sfm_character_tools_backups/"
POSE_LIBRARY_ADDITIONS = ("/Poses/", "/pose_sources.json", "/pose_rigs.json", "/pose_favorites.json")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path):
    with open(path, "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    if c.get("format") != "WU-config-v1":
        raise SystemExit("REFUSED: not a WU configuration")
    for k, v in list(c["paths"].items()):
        c["paths"][k] = os.path.expandvars(v)
    holes = sorted(k for k, v in c["paths"].items() if "<" in v or ">" in v or "%" in v)
    if holes:
        raise SystemExit("REFUSED: fill the configuration paths first: %s" % ", ".join(holes))
    return c


def q(c, *parts):
    return os.path.join(c["paths"]["Q"], *parts)


def g(c, rel):
    return os.path.join(c["paths"]["GAME"], *rel.split("/"))


def sfm_running():
    if os.environ.get("WU_TEST_SFM_STATE") == "closed":  # offline tests only
        return False
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq sfm.exe", "/NH"], capture_output=True, text=True).stdout
    return "sfm.exe" in out.lower()


def refuse(problems, what):
    if problems:
        for p in problems:
            print("  - " + p)
        raise SystemExit("%s NOT PERFORMED (nothing was changed)" % what)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, indent=1, sort_keys=True) + "\n")


def read_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def inventory(root):
    """{relative path: sha256} of every regular file; refuses reparse points; {} when the root is absent."""
    out = {}
    if not os.path.isdir(root):
        return out
    for base, dirs, files in os.walk(root):
        for name in dirs + files:
            p = os.path.join(base, name)
            if getattr(os.lstat(p), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise SystemExit("REFUSED: reparse point %s" % p)
        for name in files:
            p = os.path.join(base, name)
            out[os.path.relpath(p, root).replace(os.sep, "/")] = sha(p)
    return out


def roots(c):
    r = dict((t, g(c, t)) for t in TREES)
    r["library"] = c["paths"]["LIBRARY"]
    return r


def protected_files(c):
    """Game-relative settings files of other add-ons (Autoinit Manager): backed up, checked and restored."""
    return dict((rel, sha(g(c, rel)) if os.path.isfile(g(c, rel)) else None) for rel in c.get("protected", []))


def all_inventories(c):
    inv = dict((k, inventory(v)) for k, v in roots(c).items())
    inv["workshop"] = inventory(g(c, WORKSHOP))
    inv["readonly"] = dict((rel, inventory(g(c, rel))) for rel in c.get("readonly_trees", []))
    inv["protected"] = protected_files(c)
    return inv


def flat(inv):
    """{game-relative path: sha} across the three usermod trees."""
    return dict(("%s/%s" % (t, rel), h) for t in TREES for rel, h in inv[t].items())


def package_files(c):
    """The v1.1.0 package's installed files: game-relative path -> sha256 (READMEs are never installed)."""
    out = {}
    with zipfile.ZipFile(c["paths"]["ZIP"]) as z:
        for info in z.infolist():
            n = info.filename
            if n.startswith("usermod/"):
                rel = n
            elif n.startswith("OPTIONAL - CPM Button/usermod/"):
                rel = n[len("OPTIONAL - CPM Button/"):]
            else:
                continue
            out[rel] = hashlib.sha256(z.read(info)).hexdigest()
    out[HELPER] = c["pins"]["helper_sha256"]
    out[MANAGER] = c["pins"]["manager_sha256"]
    return out


def housekeeping(c, path):
    return any(path.endswith("/" + h.replace("\\", "/")) for h in c["housekeeping"])


def cmd_pre(c):
    problems = []
    if sfm_running():
        problems.append("SFM is running; close it")
    if os.path.exists(q(c, "pre.json")):
        problems.append("%s exists" % q(c, "pre.json"))
    if T(c, c["paths"]["ZIP"]) != c["pins"]["zip_sha256"]:
        problems.append("ZIP is not the v1.1.0 release %s" % c["pins"]["zip_sha256"])
    for rel, pin in (("SCT_Setup.exe", "helper_sha256"),):
        if T(c, os.path.join(c["paths"]["STAGE_PAYLOAD"], rel)) != c["pins"][pin]:
            problems.append("the staged %s is not %s" % (rel, c["pins"][pin]))
    if T(c, c["paths"]["R2_FIXTURE"]) != c["pins"]["r2_fixture_sha256"]:
        problems.append("the R2 fixture is not %s" % c["pins"]["r2_fixture_sha256"])
    rec = read_json(g(c, RECORD)) if os.path.isfile(g(c, RECORD)) else {}
    if rec.get("package") != c["pins"]["v100_package_sha256"]:
        problems.append("no v1.0.0 Workshop Setup installation record (package %r)" % rec.get("package"))
    if T(c, g(c, CPM)) != c["pins"]["v100_cpm_sha256"]:
        problems.append("the installed CPM is not v1.0.0's")
    problems += ["%s already exists" % r for r in REGISTRIES if os.path.lexists(g(c, r))]
    refuse(problems, "PRE")
    inv = all_inventories(c)
    for name, root in roots(c).items():
        dst = q(c, "backup", name.replace("/", "_"))
        if os.path.isdir(root):
            shutil.copytree(root, dst, copy_function=shutil.copy2)
        if inventory(dst) != inv[name]:
            raise SystemExit("PRE FAILED: the backup of %s does not verify (inspect %s)" % (name, dst))
    for rel, h in inv["protected"].items():
        if h is not None:
            dst = q(c, "backup", "protected", *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(g(c, rel), dst)
            if sha(dst) != h:
                raise SystemExit("PRE FAILED: the backup of %s does not verify" % rel)
    os.makedirs(q(c, "sessions"))
    shutil.copy2(c["paths"]["R2_FIXTURE"], q(c, "sessions", "WU_SESSION.dmx"))
    if T(c, q(c, "sessions", "WU_SESSION.dmx")) != c["pins"]["r2_fixture_sha256"]:
        raise SystemExit("PRE FAILED: the session copy does not verify")
    dirs = dict((k, sorted(os.path.relpath(os.path.join(b, d), v).replace(os.sep, "/")
                           for b, ds, _ in os.walk(v) for d in ds)) for k, v in roots(c).items())
    write_json(q(c, "pre.json"), {"inventories": inv, "dirs": dirs, "record": rec,
                                  "counts": dict((k, len(v)) for k, v in inv.items())})
    print("PRE PASS: v1.0.0 Workshop installation found; backed up and verified %s; session %s" % (
        dict((k, len(v)) for k, v in inv.items()), q(c, "sessions", "WU_SESSION.dmx")))


def T(c, path):
    return sha(path) if os.path.isfile(path) else None


def cmd_launch(c):
    refuse(["run pre first"] if not os.path.isfile(q(c, "pre.json")) else [], "LAUNCH")
    exe = os.path.join(c["paths"]["STAGE_PAYLOAD"], "SCT_Setup.exe")
    refuse(["the staged Setup is not %s" % c["pins"]["helper_sha256"]] if T(c, exe) != c["pins"]["helper_sha256"]
           else [], "LAUNCH")
    subprocess.Popen([exe, "--game", c["paths"]["GAME"]], cwd=c["paths"]["STAGE_PAYLOAD"], close_fds=True,
                     creationflags=0x00000008 | 0x00000200)
    print("LAUNCHED: %s --game %s" % (exe, c["paths"]["GAME"]))


def library_checks(pre, now):
    changed = sorted(p for p in pre if p in now and now[p] != pre[p])
    deleted = sorted(p for p in pre if p not in now)
    added = sorted(p for p in now if p not in pre)
    pose_only = all(any(m in "/" + a for m in POSE_LIBRARY_ADDITIONS) or a.endswith(("/character.json",
                                                                                    "/library.json", ".bak"))
                    for a in added)
    return {"changed": changed, "deleted": deleted, "added": added, "added_are_library_records": pose_only}


def checks_common(c, name):
    if sfm_running():
        raise SystemExit("REFUSED: SFM is running; close it")
    path = q(c, "evidence", name)
    if os.path.exists(path):
        raise SystemExit("REFUSED: %s exists" % path)
    return path, read_json(q(c, "pre.json")), all_inventories(c), package_files(c)


def unexpected(c, pre_flat, now_flat, managed):
    out = []
    for p in sorted(set(pre_flat) | set(now_flat)):
        if pre_flat.get(p) == now_flat.get(p):
            continue
        # Python bytecode is written by SFM itself for any imported module; it is never user data.
        if p in managed or p.endswith((".pyc", ".pyo")) or p.startswith(STATE + "/") or housekeeping(c, p):
            continue
        out.append(p)
    return out


def finish(path, R, label):
    R["pass"] = all(v for k, v in R["gates"].items())
    write_json(path, R)
    print(json.dumps(R["gates"], indent=1))
    print("%s %s" % (label, "PASS" if R["pass"] else "FAIL"))
    return 0 if R["pass"] else 1


def cmd_check_update(c):
    path, pre, now, managed = checks_common(c, "CHECK_UPDATE.json")
    pre_flat, now_flat = flat(pre["inventories"]), flat(now)
    rec = read_json(g(c, RECORD)) if os.path.isfile(g(c, RECORD)) else {}
    wrong = sorted(p for p, h in managed.items() if now_flat.get(p) != h)
    lib = library_checks(pre["inventories"]["library"], now["library"])
    backups = [p for p in now_flat if p.startswith(STATE + "/backups/")]
    R = {"record": {"version": rec.get("version"), "package": rec.get("package")},
         "managed_files": len(managed), "managed_wrong": wrong[:50],
         "unexpected_changes": unexpected(c, pre_flat, now_flat, managed), "library": lib,
         "installer_backups": backups}
    R["gates"] = {
        "record_is_v110": rec.get("version") == "1.1.0" and rec.get("package") == c["pins"]["zip_sha256"],
        "every_managed_file_installed": not wrong,
        "pose_library_registries_installed": all(now_flat.get(r) == managed[r] for r in REGISTRIES),
        "cpm_is_v110": now_flat.get(CPM) == c["pins"]["v110_cpm_sha256"],
        "setup_and_launcher_updated": now_flat.get(HELPER) == c["pins"]["helper_sha256"] and
        now_flat.get(MANAGER) == c["pins"]["manager_sha256"],
        "nothing_else_changed": not R["unexpected_changes"],
        "updater_backups_kept": all(now_flat.get(p) == h for p, h in pre_flat.items() if p.startswith(UPDATER_BACKUPS)),
        "library_unchanged": not (lib["changed"] or lib["deleted"] or lib["added"]),
        "workshop_payload_unchanged": now["workshop"] == pre["inventories"]["workshop"],
        "autoinit_code_unchanged": now["readonly"] == pre["inventories"]["readonly"],
        "autoinit_settings_unchanged": now["protected"] == pre["inventories"]["protected"],
    }
    return finish(path, R, "CHECK-UPDATE")


def cmd_check_uninstall(c):
    path, pre, now, managed = checks_common(c, "CHECK_UNINSTALL.json")
    pre_flat, now_flat = flat(pre["inventories"]), flat(now)
    programs = [p for p in managed if p not in (MASTER,) and not p.startswith("usermod/cfg/sfm_shared_authority/")]
    remaining = sorted(p for p in programs if p in now_flat)
    lib = library_checks(pre["inventories"]["library"], now["library"])
    upd = read_json(q(c, "evidence", "CHECK_UPDATE.json")) if os.path.isfile(q(c, "evidence", "CHECK_UPDATE.json")) \
        else {"installer_backups": []}
    R = {"remaining_programs": remaining, "unexpected_changes": unexpected(c, pre_flat, now_flat, managed),
         "library": lib, "authority_remaining": sorted(p for p in now_flat
                                                       if p.startswith("usermod/cfg/sfm_shared_authority/"))}
    R["gates"] = {
        "programs_registries_and_launcher_removed": remaining in ([], [HELPER]),
        "record_removed": RECORD not in now_flat,
        "txt_kept": MASTER in now_flat,
        "setup_txt_backups_kept": all(p in now_flat for p in upd["installer_backups"]),
        "updater_backups_kept": all(now_flat.get(p) == h for p, h in pre_flat.items() if p.startswith(UPDATER_BACKUPS)),
        "nothing_else_changed": not R["unexpected_changes"],
        "no_preexisting_library_file_changed": not (lib["changed"] or lib["deleted"]),
        "library_additions_are_preset_records": lib["added_are_library_records"],
        "workshop_payload_unchanged": now["workshop"] == pre["inventories"]["workshop"],
        "autoinit_code_unchanged": now["readonly"] == pre["inventories"]["readonly"],
    }
    R["autoinit_settings_changed_while_sfm_ran"] = sorted(
        k for k, v in now["protected"].items() if v != pre["inventories"]["protected"].get(k))
    R["note"] = ("A remaining Setup executable is reported by Setup when it ran from the installed copy; the Owner "
                 "deletes it after closing Setup (README). Its presence alone does not fail the gate.")
    return finish(path, R, "CHECK-UNINSTALL")


def cmd_restore(c):
    if sfm_running():
        raise SystemExit("REFUSED: SFM is running; close it")
    path = q(c, "evidence", "RESTORE.json")
    if os.path.exists(path):
        raise SystemExit("REFUSED: %s exists" % path)
    pre = read_json(q(c, "pre.json"))
    moved, restored = [], []
    for name, root in roots(c).items():
        want = pre["inventories"][name]
        backup = q(c, "backup", name.replace("/", "_"))
        if inventory(backup) != want:
            raise SystemExit("RESTORE NOT PERFORMED: the backup of %s no longer verifies" % name)
        now = inventory(root)
        for rel in sorted(set(now) - set(want)):
            dst = q(c, "evidence", "after_restore_removed", name.replace("/", "_"), *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(os.path.join(root, *rel.split("/")), dst)
            moved.append("%s/%s" % (name, rel))
        for rel, h in sorted(want.items()):
            if now.get(rel) != h:
                dst = os.path.join(root, *rel.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(os.path.join(backup, *rel.split("/")), dst)
                restored.append("%s/%s" % (name, rel))
        keep = set(pre["dirs"][name])
        for base, dirs, _ in sorted(os.walk(root, topdown=False), key=lambda x: -len(x[0])):
            for d in dirs:
                p = os.path.join(base, d)
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                if rel not in keep and os.path.isdir(p) and not os.listdir(p):
                    os.rmdir(p)
    for rel, h in sorted(pre["inventories"]["protected"].items()):
        if h is not None and (sha(g(c, rel)) if os.path.isfile(g(c, rel)) else None) != h:
            shutil.copy2(q(c, "backup", "protected", *rel.split("/")), g(c, rel))
            restored.append(rel)
    after = all_inventories(c)
    dirs_now = dict((k, sorted(os.path.relpath(os.path.join(b, d), v).replace(os.sep, "/")
                               for b, ds, _ in os.walk(v) for d in ds)) for k, v in roots(c).items())
    R = {"moved_to_evidence": moved, "restored_from_backup": restored,
         "equal_to_pre": dict((k, after[k] == pre["inventories"][k]) for k in after if k != "readonly"),
         "autoinit_code_unchanged": after["readonly"] == pre["inventories"]["readonly"],
         "dirs_equal_to_pre": dict((k, dirs_now[k] == pre["dirs"][k]) for k in dirs_now)}
    R["restored"] = (all(R["equal_to_pre"].values()) and all(R["dirs_equal_to_pre"].values()) and
                     R["autoinit_code_unchanged"])
    write_json(path, R)
    print(json.dumps({k: R[k] for k in ("equal_to_pre", "dirs_equal_to_pre", "restored")}, indent=1))
    print("RESTORED: %d files restored, %d moved to evidence" % (len(restored), len(moved)) if R["restored"]
          else "RESTORE INCOMPLETE: inspect %s" % path)
    return 0 if R["restored"] else 1


def main(argv):
    commands = {"pre": cmd_pre, "launch": cmd_launch, "check-update": cmd_check_update,
                "check-uninstall": cmd_check_uninstall, "restore": cmd_restore}
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
