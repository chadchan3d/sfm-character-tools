# -*- coding: utf-8 -*-
"""F-01 Pose Library M1, stage B: offline qualification of the pose library in the CPM application source.
Design authority: F-01 M1 Implementation Addendum R2 section 4.3; qualification item O-9 of
05_QUALIFICATION_PLAN.md (R-3, released CPM ignoring pose data, is checked separately against the
released source).

Technique: the stage A and stage B blocks (each between its own markers) and CPM's established file helpers
p02_safe_write_json, p02_unique_temp, p02_json_text and p02_ensure_dir are extracted verbatim from the application
source and executed in a namespace with only os, json, hashlib, math, binascii, datetime and ctypes (log_line is a
stub). Every library is an isolated temporary folder; the installed CPM library and real presets are never touched
(hashed before and after). A static check proves the stage B block uses no SFM, DME, Qt or ctypes name.

Usage: --phase=run (Python 2.7.5 and Python 3.10). Environment: CPM_TEST_APP_PATH overrides the application source.
"""
from __future__ import print_function

import ast
import binascii
import copy
import ctypes
import datetime
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
import test_cpm_app_f01_pose_core as core  # noqa: E402  (stage A extraction, oracle, record builder)

APP_PATH = core.APP_PATH
STAGE_B_START = u"# F-01 Pose Library M1, stage B: offline pose library"
STAGE_B_END = u"# === end of F-01 stage B block ==="
P02_HELPERS = ("_PROD_PRIVATE_WINDLL", "prod_private_windll", "p02_ensure_dir", "p02_json_text", "p02_unique_temp",
               "p02_safe_write_json")
ALLOWED_B = set(["os", "json", "hashlib", "binascii", "open", "p02_safe_write_json", "p02_json_text",
                 "p02_ensure_dir", "prod_private_windll"])
FORBIDDEN_B = set(["vs", "sfmApp", "sfm", "QtGui", "QtCore", "PySide", "dm", "ctypes", "subprocess", "shutil",
                   "prod_library_root", "prod_paths"])
REAL_LIBRARY = os.path.join(os.path.expanduser("~"), "Documents", "SFM Character Preset Manager")

check = core.check
RESULTS = core.RESULTS


def refuses(name, code, fn, reason=None):
    try:
        fn()
    except Exception as exc:
        got = getattr(exc, "code", None)
        check(name, type(exc).__name__ in ("ProdPoseLibraryError", "ProdPoseError") and
              (code is None or got == code) and (reason is None or reason in str(exc)),
              "%s %s: %s" % (type(exc).__name__, got, exc))
        return exc
    check(name, False, "did not refuse")
    return None


def top_level_text(path, wanted):
    raw = core.read(path)
    lines = raw.decode("utf-8").split(u"\n")
    body = ast.parse(raw).body
    out = {}
    for i, node in enumerate(body):
        name = node.name if isinstance(node, ast.FunctionDef) else (
            node.targets[0].id if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) else None)
        if name in wanted:
            end = (body[i + 1].lineno - 1) if i + 1 < len(body) else len(lines)
            block = lines[node.lineno - 1:end]
            while block and (not block[-1].strip() or block[-1].lstrip().startswith(u"#")):
                block.pop()
            out[name] = u"\n".join(block)
    missing = [w for w in wanted if w not in out]
    if missing:
        raise SystemExit("REFUSED: helpers not found: %r" % missing)
    return u"\n\n\n".join(out[w] for w in wanted) + u"\n"


def run_source(code, label, ns):
    """Module-level exec: Python 2 forbids a bare exec inside functions that also define closures."""
    exec(compile(code, label, "exec"), ns)


def load_namespace():
    block_a, _ = core.extract_block(APP_PATH)
    block_b, names_b = core.extract_block(APP_PATH, STAGE_B_START, STAGE_B_END)
    helpers = top_level_text(APP_PATH, P02_HELPERS)
    ns = {"__builtins__": __builtins__, "json": json, "hashlib": hashlib, "math": math, "os": os,
          "binascii": binascii, "datetime": datetime, "ctypes": ctypes, "log_line": lambda *a, **k: None}
    if sys.version_info[0] >= 3:
        ns["unicode"] = str
    for label, code in (("stage_a", block_a), ("p02_helpers", helpers), ("stage_b", block_b)):
        run_source(code, label, ns)
    return ns, block_a, block_b, names_b


def static_check_b(block_b, names_a):
    v = core.Names()
    v.visit(ast.parse(block_b))
    builtin_names = set(dir(__builtins__) if not isinstance(__builtins__, dict) else __builtins__)
    free = v.loaded - v.bound - builtin_names - ALLOWED_B - set(names_a) - set(["unicode", "long"])
    check("staticB.only_own_stage_a_p02_and_allowed_names", not free, sorted(free))
    check("staticB.no_forbidden_name", not ((v.loaded | v.attr_roots) & FORBIDDEN_B),
          sorted((v.loaded | v.attr_roots) & FORBIDDEN_B))
    check("staticB.no_imports", v.imports == [], v.imports)


def attempt(fn):
    """(True, result) or (False, 'ExcType: message'); keeps a refusal from ending the section untargeted."""
    try:
        return True, fn()
    except Exception as exc:
        return False, "%s: %s" % (type(exc).__name__, exc)


def tree_digest(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = core.sha(core.read(p))
    return out


def pose_payload(ns, golden, regions=("left_arm", "right_arm"), shot=u"shot15"):
    p = core.make_record(ns, golden, regions)["pose"]
    p["source"]["shot_name"] = shot
    return p


def section_library(ns, reg, golden, root):
    E = ns["ProdPoseLibraryError"]
    lib = os.path.join(root, "library")
    os.makedirs(lib)                     # CPM prepares its library root before any library operation
    kry = {u"character_key": u"krystal2020", u"model_ref": golden["model"], u"library_root": lib,
           u"char_dir": os.path.join(lib, "Characters", "krystal2020--a1")}
    lola = {u"character_key": u"lola", u"model_ref": u"models/fursonas/lola/lola.mdl", u"library_root": lib,
            u"char_dir": os.path.join(lib, "Characters", "lola--b2")}
    trash = os.path.join(lib, "Trash")
    now1, now2 = u"2026-10-30T12:00:00Z", u"2026-10-30T13:00:00Z"
    disc = lambda who: ns["prod_pose_discover"](who[u"char_dir"], who[u"character_key"], reg)
    check("O9.empty_library", disc(kry) == {u"items": [], u"unusable": []})
    a = ns["prod_pose_save_new"](kry, u"Arms Crossed", pose_payload(ns, golden), now1, reg)
    check("O9.save_new_creates_one_file", sorted(os.listdir(os.path.join(kry[u"char_dir"], "Poses"))) ==
          [os.path.basename(a["path"])])
    check("O9.file_name_binds_identity", os.path.basename(a["path"]) ==
          u"Arms Crossed--%s.json" % a["preset_id"][:12])
    check("O9.preset_id_is_32_hex", len(a["preset_id"]) == 32 and all(c in "0123456789abcdef"
                                                                       for c in a["preset_id"]))
    items = disc(kry)["items"]
    check("O9.discover_finds_it", [i["preset_id"] for i in items] == [a["preset_id"]] and
          items[0]["revision"] == a["revision"])
    check("O9.written_bytes_use_cpm_json_text", core.read(a["path"]) ==
          ns["p02_json_text"](a["record"]).encode("utf-8"))
    refuses("O9.duplicate_name_refused_case_insensitive", "name",
            lambda: ns["prod_pose_save_new"](kry, u"  arms crossed ", pose_payload(ns, golden), now1, reg))
    refuses("O9.empty_name_refused", "name", lambda: ns["prod_pose_save_new"](kry, u"   ", pose_payload(ns, golden),
                                                                             now1, reg))
    refuses("O9.control_char_name_refused", "name",
            lambda: ns["prod_pose_save_new"](kry, u"Bad\x07Name", pose_payload(ns, golden), now1, reg))
    refuses("O9.invalid_pose_refused_before_write", "invalid-pose",
            lambda: ns["prod_pose_save_new"](kry, u"Broken", dict(pose_payload(ns, golden), version=2), now1, reg))
    check("O9.refused_saves_wrote_nothing", len(os.listdir(os.path.join(kry[u"char_dir"], "Poses"))) == 1)
    ok, odd = attempt(lambda: ns["prod_pose_save_new"](kry, u'Point: "up"/down?',
                                                      pose_payload(ns, golden, ("left_arm",)), now1, reg))
    check("O9.unsafe_characters_in_file_name_replaced", ok and os.path.basename(odd["path"]).startswith(
        u"Point_ _up__down_--"), odd)
    # Exclusive creation never overwrites an existing file.
    pid = u"f" * 32
    target = os.path.join(kry[u"char_dir"], "Poses", u"Collide--%s.json" % pid[:12])
    with open(target, "wb") as f:
        f.write(b"not a pose")
    c = ns["prod_pose_save_new"](kry, u"Collide", pose_payload(ns, golden), now1, reg, preset_id=pid)
    check("O9.collision_gets_suffix_and_existing_file_untouched",
          os.path.basename(c["path"]) == u"Collide--%s-2.json" % pid[:12] and core.read(target) == b"not a pose")
    refuses("O9.create_exclusive_refuses_existing", "exists",
            lambda: ns["prod_pose_create_exclusive"](target, b"x", kry))
    check("O9.create_exclusive_left_existing_and_no_temp", core.read(target) == b"not a pose" and
          not [n for n in os.listdir(os.path.dirname(target)) if ".tmp-pose-" in n])
    found = disc(kry)
    check("O9.unparseable_file_listed_unusable_not_applied",
          [u["reason"] for u in found["unusable"]] == [u"invalid-file"] and
          sorted(i["name"] for i in found["items"]) == sorted([u"Arms Crossed", u'Point: "up"/down?', u"Collide"]))
    os.remove(target)
    # Identity binding, foreign records and duplicates in discovery.
    copied = os.path.join(kry[u"char_dir"], "Poses", u"Copied.json")
    shutil.copyfile(a["path"], copied)
    found = disc(kry)
    check("O9.copied_file_without_identity_name_unusable", any(u["reason"] == u"identity-mismatch"
                                                              for u in found["unusable"]))
    os.remove(copied)
    dup = os.path.join(kry[u"char_dir"], "Poses", u"Dup--%s.json" % a["preset_id"][:12])
    shutil.copyfile(a["path"], dup)
    found = disc(kry)
    check("O9.duplicate_identity_makes_both_unusable", a["preset_id"] not in [i["preset_id"] for i in found["items"]]
          and sum(u["reason"] == u"duplicate-identity" for u in found["unusable"]) == 2)
    os.remove(dup)
    # Lola's library, one pose.
    l1 = ns["prod_pose_save_new"](lola, u"Wave", pose_payload(ns, golden), now1, reg)
    planted = os.path.join(kry[u"char_dir"], "Poses", os.path.basename(l1["path"]))
    shutil.copyfile(l1["path"], planted)
    check("O9.foreign_record_in_own_folder_unusable", any(u["reason"] == u"foreign-record"
                                                         for u in disc(kry)["unusable"]))
    os.remove(planted)
    target_a = lambda item: {u"character_key": item["character_key"], u"preset_id": item["preset_id"],
                             u"revision": item["revision"]}
    lola_snapshot = tree_digest(lola[u"char_dir"])
    # Update: exact region set; identity, name, created_at and file name kept.
    up = ns["prod_pose_update"](kry, target_a(a), pose_payload(ns, golden, shot=u"shot20"), now2, reg)
    check("O9.update_keeps_identity_name_file_created",
          up["path"] == a["path"] and up["record"]["preset_id"] == a["preset_id"] and
          up["record"]["name"] == u"Arms Crossed" and up["record"]["created_at"] == now1 and
          up["record"]["updated_at"] == now2 and up["record"]["pose"]["source"]["shot_name"] == u"shot20")
    check("O9.update_used_cpm_safe_writer_backup", os.path.isfile(a["path"] + u".bak"))
    refuses("O9.update_with_stale_revision_refused", "record-changed",
            lambda: ns["prod_pose_update"](kry, target_a(a), pose_payload(ns, golden), now2, reg))
    refuses("O9.update_must_keep_region_set", "regions",
            lambda: ns["prod_pose_update"](kry, target_a(up), pose_payload(ns, golden, ("left_arm",)), now2, reg))
    # Rename: display name only; file name stable; uniqueness; stale refused.
    before_files = sorted(os.listdir(os.path.join(kry[u"char_dir"], "Poses")))
    rn = ns["prod_pose_rename"](kry, target_a(up), u"Arms Folded", now2, reg)
    after_files = sorted(os.listdir(os.path.join(kry[u"char_dir"], "Poses")))
    check("O9.rename_changes_display_name_only", rn["record"]["name"] == u"Arms Folded" and rn["path"] == a["path"]
          and [f for f in after_files if not f.endswith(".bak")] == [f for f in before_files if not f.endswith(".bak")])
    check("O9.rename_keeps_pose_payload", rn["record"]["pose"] == up["record"]["pose"] and
          rn["record"]["payload_sha256"] == up["record"]["payload_sha256"])
    refuses("O9.rename_to_existing_name_refused", "name",
            lambda: ns["prod_pose_rename"](kry, target_a(rn), u"collide", now2, reg))
    ok, res = attempt(lambda: ns["prod_pose_rename"](kry, target_a(rn), u"ARMS FOLDED", now2, reg))
    check("O9.rename_to_own_name_different_case_allowed", ok and res["record"]["name"] == u"ARMS FOLDED", res)
    refuses("O9.rename_with_stale_revision_refused", "record-changed",
            lambda: ns["prod_pose_rename"](kry, target_a(rn), u"Other", now2, reg))
    cur = [i for i in disc(kry)["items"] if i["preset_id"] == a["preset_id"]][0]
    # Favorites: own in library.json (other entries kept); foreign in pose_favorites.json; foreign never written.
    meta_path = os.path.join(kry[u"char_dir"], "library.json")
    with open(meta_path, "wb") as f:
        f.write(json.dumps({"schema_version": 1, "record_kind": "library-metadata",
                            "favorites": ["body:1234", "expression:abcd"]}).encode("utf-8"))
    check("O9.favorite_own_set", ns["prod_pose_set_favorite"](kry, target_a(cur), True, reg) is True)
    meta = json.loads(core.read(meta_path).decode("utf-8"))
    check("O9.favorite_keeps_other_entries", meta["favorites"] == sorted([u"body:1234", u"expression:abcd",
                                                                          u"pose:" + a["preset_id"]]))
    check("O9.favorite_own_cleared", ns["prod_pose_set_favorite"](kry, target_a(cur), False, reg) is False and
          json.loads(core.read(meta_path).decode("utf-8"))["favorites"] == [u"body:1234", u"expression:abcd"])
    with open(meta_path, "wb") as f:
        f.write(b'{"schema_version": 2, "record_kind": "library-metadata", "favorites": []}')
    refuses("O9.unsupported_library_meta_refused", "metadata",
            lambda: ns["prod_pose_set_favorite"](kry, target_a(cur), True, reg))
    os.remove(meta_path)
    lola_target = target_a(l1)
    ok, res = attempt(lambda: ns["prod_pose_set_foreign_favorite"](kry, lola, lola_target, True, reg))
    check("O9.foreign_favorite_set", ok and res is True, res)
    own_ff = os.path.join(kry[u"char_dir"], "pose_favorites.json")
    check("O9.foreign_favorite_never_writes_foreign_library",
          not os.path.exists(os.path.join(lola[u"char_dir"], "pose_favorites.json")) and os.path.isfile(own_ff))
    ff = json.loads(core.read(own_ff).decode("utf-8")) if os.path.isfile(own_ff) else None
    check("O9.foreign_favorite_stored_in_own_folder", ff == {u"schema_version": 1, u"record_kind":
                                                              u"pose-foreign-favorites", u"entries": [
                                                                  {u"character_key": u"lola",
                                                                   u"preset_id": l1["preset_id"]}]})
    check("O9.foreign_favorite_cleared", not ns["prod_pose_set_foreign_favorite"](kry, lola, lola_target, False,
                                                                                  reg))
    refuses("O9.foreign_favorite_on_own_character_refused", "foreign-locked",
            lambda: ns["prod_pose_set_foreign_favorite"](kry, kry, target_a(cur), True, reg))
    refuses("O9.foreign_favorite_stale_revision_refused", "record-changed",
            lambda: ns["prod_pose_set_foreign_favorite"](kry, lola, dict(lola_target, revision=u"0" * 64), True,
                                                         reg))
    # Store-layer foreign protection: Update, Rename, Delete and own-Favorite refuse another library's pose.
    for name, fn in (("update", lambda: ns["prod_pose_update"](kry, lola_target, pose_payload(ns, golden), now2,
                                                               reg)),
                     ("rename", lambda: ns["prod_pose_rename"](kry, lola_target, u"Mine now", now2, reg)),
                     ("trash", lambda: ns["prod_pose_trash"](kry, lola_target, trash, u"20261030", reg)),
                     ("favorite_as_own", lambda: ns["prod_pose_set_favorite"](kry, lola_target, True, reg))):
        refuses("O9.store_refuses_foreign_%s" % name, "foreign-locked", fn)
    disguised = dict(lola_target, character_key=u"krystal2020")
    refuses("O9.store_refuses_foreign_id_disguised_as_own", "record-changed",
            lambda: ns["prod_pose_trash"](kry, disguised, trash, u"20261030", reg))
    check("O9.foreign_library_byte_identical_throughout", tree_digest(lola[u"char_dir"]) == lola_snapshot)
    # Delete: non-overwriting move to Trash; stale refused; destination collision refused.
    refuses("O9.trash_with_stale_revision_refused", "record-changed",
            lambda: ns["prod_pose_trash"](kry, target_a(a), trash, u"20261030-120000", reg))
    pre = [i for i in disc(kry)["items"] if i["preset_id"] == odd["preset_id"]][0]
    dest = ns["prod_pose_trash"](kry, target_a(pre), trash, u"20261030-120000", reg)
    check("O9.trash_moves_file_out_of_library", os.path.isfile(dest) and not os.path.exists(pre["path"]) and
          odd["preset_id"] not in [i["preset_id"] for i in disc(kry)["items"]])
    check("O9.trashed_bytes_unchanged", core.sha(core.read(dest)) == pre["revision"])
    cur = [i for i in disc(kry)["items"] if i["preset_id"] == a["preset_id"]][0]
    blocker = os.path.join(trash, u"20261030-120001--%s--%s" % (a["preset_id"][:8], os.path.basename(cur["path"])))
    with open(blocker, "wb") as f:
        f.write(b"occupied")
    refuses("O9.trash_never_overwrites", "exists",
            lambda: ns["prod_pose_trash"](kry, target_a(cur), trash, u"20261030-120001", reg))
    check("O9.trash_refusal_left_both_files", core.read(blocker) == b"occupied" and os.path.isfile(cur["path"]))
    # Writer fault injection: whatever the writer produced must read back as exactly the intended record.
    real_text, real_safe = ns["p02_json_text"], ns["p02_safe_write_json"]

    def drifting_text(record):
        r = copy.deepcopy(record)
        if isinstance(r, dict) and r.get("kind") == "pose":
            r["updated_at"] = u"1999-01-01T00:00:00Z"
        return real_text(r)
    try:
        ns["p02_json_text"] = drifting_text
        refuses("O9.save_new_refuses_when_written_record_differs", "write-verify",
                lambda: ns["prod_pose_save_new"](kry, u"Drift", pose_payload(ns, golden), now1, reg))
    finally:
        ns["p02_json_text"] = real_text
    check("O9.failed_save_new_leaves_no_pose_file", u"Drift" not in [i["name"] for i in disc(kry)["items"]] and
          not [n for n in os.listdir(os.path.join(kry[u"char_dir"], "Poses")) if n.startswith(u"Drift--")])
    cur2 = [i for i in disc(kry)["items"] if i["preset_id"] == a["preset_id"]][0]

    def drifting_safe(path, record):
        r = copy.deepcopy(record)
        if isinstance(r, dict) and r.get("kind") == "pose":
            r["name"] = r["name"] + u" (drift)"
        return real_safe(path, r)
    try:
        ns["p02_safe_write_json"] = drifting_safe
        refuses("O9.rename_refuses_when_written_record_differs", "write-verify",
                lambda: ns["prod_pose_rename"](kry, target_a(cur2), u"Drift Rename", now2, reg))
        cur3 = [i for i in disc(kry)["items"] if i["preset_id"] == a["preset_id"]][0]
        refuses("O9.update_refuses_when_written_record_differs", "write-verify",
                lambda: ns["prod_pose_update"](kry, target_a(cur3), pose_payload(ns, golden), now2, reg))
    finally:
        ns["p02_safe_write_json"] = real_safe
    # Path containment: a record outside the selected Poses folder is never treated as own.
    check("O9.inside_check", ns["prod_pose_inside"](cur["path"], os.path.join(kry[u"char_dir"], "Poses")) and
          not ns["prod_pose_inside"](l1["path"], os.path.join(kry[u"char_dir"], "Poses")))
    # Strict metadata parsing for foreign favorites.
    with open(os.path.join(kry[u"char_dir"], "pose_favorites.json"), "wb") as f:
        f.write(b'{"schema_version": 1, "record_kind": "pose-foreign-favorites", "entries": [{"preset_id": "x"}]}')
    refuses("O9.malformed_foreign_favorites_refused", "metadata",
            lambda: ns["prod_pose_load_foreign_favorites"](kry[u"char_dir"]))
    with open(os.path.join(kry[u"char_dir"], "pose_favorites.json"), "wb") as f:
        f.write(b'{"schema_version": 1, "record_kind": "pose-foreign-favorites", "entries": [], "entries": []}')
    refuses("O9.duplicate_key_foreign_favorites_refused", "metadata",
            lambda: ns["prod_pose_load_foreign_favorites"](kry[u"char_dir"]))


def junction(link, target):
    """A real Windows directory junction (no elevation needed)."""
    cmd = "New-Item -ItemType Junction -Path '%s' -Target '%s' | Out-Null" % (link, target)
    return subprocess.call(["powershell.exe", "-NoProfile", "-Command", cmd]) == 0 and os.path.isdir(link)


def section_containment(ns, reg, golden, root):
    """P1-3: no pose or metadata operation may reach outside the trusted library through a redirect."""
    lib = os.path.join(root, "clib")
    os.makedirs(lib)
    own = {u"character_key": u"krystal2020", u"model_ref": golden["model"], u"library_root": lib,
           u"char_dir": os.path.join(lib, "Characters", "krystal2020--a1")}
    now = u"2026-10-30T12:00:00Z"
    item = ns["prod_pose_save_new"](own, u"Base", pose_payload(ns, golden), now, reg)
    target = {u"character_key": item["character_key"], u"preset_id": item["preset_id"], u"revision": item["revision"]}
    outside = os.path.join(root, "outside")
    foreign_poses = os.path.join(outside, "Poses")
    os.makedirs(foreign_poses)
    links = []
    try:
        # (1) Astra's reproduction: Save New for a character whose Poses folder is a junction to a foreign folder.
        alias = dict(own, char_dir=os.path.join(lib, "Characters", "alias--c3"))
        os.makedirs(alias[u"char_dir"])
        link = os.path.join(alias[u"char_dir"], "Poses")
        made = junction(link, foreign_poses)
        links.append(link)
        check("P1_3.real_junction_created", made)
        before_out, before_lib = tree_digest(outside), tree_digest(os.path.join(lib, "Characters", "krystal2020--a1"))
        refuses("P1_3.astra_save_new_through_poses_junction_refused", "unsafe-location",
                lambda: ns["prod_pose_save_new"](alias, u"Through Alias", pose_payload(ns, golden), now, reg))
        check("P1_3.external_target_unchanged_after_refused_save", tree_digest(outside) == before_out and
              os.listdir(foreign_poses) == [])
        # (2) The selected character folder itself is a junction onto the real library's character folder.
        alias2 = dict(own, char_dir=os.path.join(lib, "Characters", "alias2--d4"))
        made = junction(alias2[u"char_dir"], own[u"char_dir"])
        links.append(alias2[u"char_dir"])
        check("P1_3.character_junction_created", made)
        found = [i for i in ns["prod_pose_discover"](alias2[u"char_dir"], own[u"character_key"], reg)["items"]]
        t2 = {u"character_key": found[0]["character_key"], u"preset_id": found[0]["preset_id"],
              u"revision": found[0]["revision"]} if found else target
        meta_before = tree_digest(own[u"char_dir"])
        for name, fn in (
                ("update", lambda: ns["prod_pose_update"](alias2, t2, pose_payload(ns, golden), now, reg)),
                ("rename", lambda: ns["prod_pose_rename"](alias2, t2, u"Renamed", now, reg)),
                ("favorite", lambda: ns["prod_pose_set_favorite"](alias2, t2, True, reg)),
                ("trash", lambda: ns["prod_pose_trash"](alias2, t2, os.path.join(lib, "Trash"), u"20261030", reg)),
                ("save_new", lambda: ns["prod_pose_save_new"](alias2, u"Second", pose_payload(ns, golden), now,
                                                              reg))):
            refuses("P1_3.%s_through_character_junction_refused" % name, "unsafe-location", fn)
        check("P1_3.authorized_library_unchanged_after_refusals", tree_digest(own[u"char_dir"]) == meta_before)
        # (3) The library Trash is a junction to an outside folder.
        trash_out = os.path.join(root, "trash_out")
        os.makedirs(trash_out)
        made = junction(os.path.join(lib, "Trash"), trash_out)
        links.append(os.path.join(lib, "Trash"))
        check("P1_3.trash_junction_created", made)
        refuses("P1_3.trash_through_junction_refused", "unsafe-location",
                lambda: ns["prod_pose_trash"](own, target, os.path.join(lib, "Trash"), u"20261030", reg))
        check("P1_3.pose_kept_and_outside_trash_empty", os.path.isfile(item["path"]) and os.listdir(trash_out) == [])
        refuses("P1_3.trash_other_than_library_trash_refused", "unsafe-location",
                lambda: ns["prod_pose_trash"](own, target, trash_out, u"20261030", reg))
        # (4) Targeted containment guard.
        guard = ns["prod_pose_assert_contained"]
        ok_path = os.path.join(own[u"char_dir"], "Poses", "x.json")
        check("P1_3.guard_accepts_plain_library_path", guard(own, ok_path) is not None)
        refuses("P1_3.guard_refuses_path_outside_character", "unsafe-location",
                lambda: guard(own, os.path.join(lib, "Characters", "lola--b2", "Poses", "x.json")))
        refuses("P1_3.guard_refuses_parent_escape", "unsafe-location",
                lambda: guard(own, os.path.join(own[u"char_dir"], "..", "..", "..", "outside", "Poses", "x.json")))
        refuses("P1_3.guard_refuses_untrusted_character_location", "unsafe-location",
                lambda: guard(dict(own, char_dir=os.path.join(outside, "Characters", "k")),
                              os.path.join(outside, "Characters", "k", "Poses", "x.json")))
        refuses("P1_3.guard_refuses_missing_trusted_root", "unsafe-location",
                lambda: guard(dict(own, library_root=None), ok_path))
        refuses("P1_3.guard_refuses_redirected_component", "unsafe-location",
                lambda: guard(alias, os.path.join(alias[u"char_dir"], "Poses", "y.json")))
        # (5) The original direct path still works after all refusals.
        ok, res = attempt(lambda: ns["prod_pose_rename"](own, target, u"Base Renamed", now, reg))
        check("P1_3.direct_library_operations_still_work", ok and res["record"]["name"] == u"Base Renamed", res)
    finally:
        for link in reversed(links):
            if os.path.lexists(link):
                os.rmdir(link)                      # removes the junction only, never its target's contents


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        return 2
    print("Interpreter: %s" % sys.version.split()[0])
    real_before = tree_digest(REAL_LIBRARY) if os.path.isdir(REAL_LIBRARY) else None
    ns, block_a, block_b, names_b = load_namespace()
    _, names_a = core.extract_block(APP_PATH)
    check("extractB.block_present", len(names_b) > 20, len(names_b))
    check("extractB.blocks_disjoint", not set(names_a) & set(names_b))
    static_check_b(block_b, names_a)
    if not core.w2_verified():
        print("RESULT: W2 oracle files do not verify; stopping")
        return 1
    golden = json.loads(core.read(os.path.join(core.W2_DIR, "tests", "fixtures",
                                               "golden_left_arm_pose.f01w2.json")).decode("utf-8"))
    raw = core.read(core.REGISTRY_PATH)
    reg = ns["prod_pose_registry_parse"](raw, core.sha(raw))
    root = tempfile.mkdtemp(prefix="cpm_f01_library_")
    try:
        try:
            section_library(ns, reg, golden, root)
            check("section.library.completed", True)
            section_containment(ns, reg, golden, root)
            check("section.containment.completed", True)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            check("section.library.completed", False, "%s: %s" % (type(exc).__name__, exc))
    finally:
        shutil.rmtree(root, True)
    real_after = tree_digest(REAL_LIBRARY) if os.path.isdir(REAL_LIBRARY) else None
    check("isolation.real_cpm_library_untouched", real_before == real_after)
    failed = [r for r in RESULTS if not r[1]]
    print("RESULT: %d/%d PASS (%s)" % (len(RESULTS) - len(failed), len(RESULTS), sys.version.split()[0]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
