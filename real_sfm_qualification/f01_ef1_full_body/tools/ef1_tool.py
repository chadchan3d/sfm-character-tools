# -*- coding: utf-8 -*-
"""F-01 EF-1 Engineer Full body native qualification: build, preparation, temporary installation, evidence collection
and restoration. Python 3, run with -I while SFM is closed (every command that changes a file refuses while sfm.exe
runs). Every command refuses, changing nothing, when a precondition fails.

The full-body S3 kit's tool (f01_full_body_s3/tools/s3_tool.py) is reused unchanged for status, install, check,
library, collect-logs and the core of restore. It provides:
- the published-installation state and an installation journal written first;
- verified copies and the four protected inventories;
- the run's Poses folder moved into evidence, and every inventory compared with its baseline.

Only this kit's identity is substituted: its configuration format, the destination's session name, the observer
wrapper and the UI capture. Its own commands:
  build    derive the qualification CPM from the pinned candidate (exactly one line differs:
           PROD_POSE_REGISTRY_MODE = u"qualification"); stage it with both pinned registries; write
           Q/staged/IDENTITIES.json (candidate, qualification build, registries, S0 observer, wrapper, UI capture,
           comparator, session classifier, expected header)
  pre      SFM closed; published installation; the model resolves to the pinned NQ-03/EC-1 bytes; no Poses folder
           and no Engineer character folder in the preset library; the kit unchanged since build. It then records
           the four inventories, backs up the published CPM, housekeeping and .pyc files, and creates Q/sessions
           (empty: the Owner creates the two sessions in preparation step 0), Q/observations and Q/evidence
  inspect  read-only, after preparation step 0: classify Q/sessions (session_files.py). It requires exactly
           ef1_source.dmx and ef1_destination.dmx (any case), each a session holding a character, differing from each
           other; SFM's .autosave copies are recorded, never pinned. It pins both sessions (evidence/destination.json)
  restore  the S3 restore. Before it, when the Engineer's character folder did not exist at pre, every file CPM wrote
           there outside Poses (for example character.json) is moved, as verified copies, into
           Q/evidence/library_character/ (evidence/library_character.json). The S3 restore then moves the Poses folder
           into evidence and compares every inventory; the emptied character folder is removed last
  compare  run tools/ef1_compare.py on this run (Q/evidence/EF1_VERDICT.json and EF1_VERDICT.md)

usage: python -I ef1_tool.py EF1.json build | pre | status | inspect | install | check | library TAG |
                                       collect-logs | restore | compare
"""
from __future__ import print_function

import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
RSQ = os.path.dirname(KIT)
sys.path.insert(0, os.path.join(RSQ, "f01_full_body_s3", "tools"))
sys.path.insert(0, os.path.join(RSQ, "f01_ec1_engineer", "tools"))
sys.path.insert(0, HERE)
import s3_tool as S  # noqa: E402
import ec1_tool as EC  # noqa: E402  (only its model identity check is used)
import session_files as SF  # noqa: E402

T = S.T
FORMAT = "F01-EF1-config-v1"
SOURCE, DESTINATION = "ef1_source.dmx", "ef1_destination.dmx"

# The only substitutions in the reused tool: this kit's identity.
S.FORMAT = FORMAT
S.SESSIONS = ()
S.DESTINATION = DESTINATION
S.tools_dir = lambda c: KIT
S.wrapper = lambda c: os.path.join(KIT, "observer", "F01_EF1_Observe.py")
S.ui_smoke = lambda c: os.path.join(KIT, "observer", "F01_EF1_UIState.py")


def comparator():
    return os.path.join(HERE, "ef1_compare.py")


def kit_paths(c):
    return {"wrapper": S.wrapper(c), "ui_smoke": S.ui_smoke(c), "comparator": comparator(),
            "session_files": SF.__file__.replace(".pyc", ".py"),
            "expected_header": os.path.join(RSQ, "f01_ec1_engineer", "engineer_header.json")}


def character_dir(c):
    return os.path.join(S.p(c, "LIBRARY"), "Characters", c["character_dir"])


def cmd_build(c):
    problems = []
    if T.sha(S.p(c, "CANDIDATE")) != c["pins"]["candidate_cpm_sha256"]:
        problems.append("the candidate CPM is not %s" % c["pins"]["candidate_cpm_sha256"])
    for key, pin in (("PROFILE", "profile_sha256"), ("BODY_PROFILE", "body_profile_sha256")):
        if T.sha(S.p(c, key)) != c["pins"][pin]:
            problems.append("%s is not the pinned registry %s" % (S.p(c, key), c["pins"][pin]))
    if T.sha(S.observer(c)) != c["pins"]["observer_sha256"]:
        problems.append("the S0 observer is not the pinned %s" % c["pins"]["observer_sha256"])
    if T.sha(kit_paths(c)["expected_header"]) != c["pins"]["expected_header_sha256"]:
        problems.append("the expected header is not the pinned %s" % c["pins"]["expected_header_sha256"])
    if os.path.exists(S.q(c, "staged")):
        problems.append("%s exists" % S.q(c, "staged"))
    S.refuse(problems, "BUILD")
    with open(S.p(c, "CANDIDATE"), "rb") as f:
        raw = f.read()
    for template, pin in zip(S.REGISTRY_CONSTANTS, ("profile_sha256", "body_profile_sha256")):
        if raw.count(template % c["pins"][pin].encode("ascii")) != 1:
            S.refuse(["the candidate does not pin registry %s" % c["pins"][pin]], "BUILD")
    if raw.count(S.MODE_PRODUCTION) != 1 or S.MODE_QUALIFICATION in raw:
        S.refuse(["the candidate does not hold exactly one production registry-mode line"], "BUILD")
    qual = raw.replace(S.MODE_PRODUCTION, S.MODE_QUALIFICATION)
    a, b = raw.split(b"\n"), qual.split(b"\n")
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if len(a) != len(b) or len(diff) != 1:
        S.refuse(["the derivation changed more than one line"], "BUILD")
    expected = c["pins"].get("qualification_cpm_sha256")
    got = hashlib.sha256(qual).hexdigest()
    if got != expected:
        S.refuse(["the derived qualification CPM %s is not the pinned %s" % (got, expected)], "BUILD")
    staged = S.q(c, "staged")
    os.makedirs(staged)
    out = os.path.join(staged, "SFM_Character_Preset_Manager.py")
    with open(out, "wb") as f:
        f.write(qual)
    T.copy_verified(S.p(c, "PROFILE"), os.path.join(staged, "cpm_pose_profiles_v1.json"), c["pins"]["profile_sha256"])
    T.copy_verified(S.p(c, "BODY_PROFILE"), os.path.join(staged, "cpm_body_profiles_v1.json"),
                    c["pins"]["body_profile_sha256"])
    ids = {"candidate_cpm_sha256": c["pins"]["candidate_cpm_sha256"], "qualification_cpm_sha256": T.sha(out),
           "changed_line": diff[0] + 1, "line": b[diff[0]].decode("utf-8"),
           "profile_sha256": c["pins"]["profile_sha256"], "body_profile_sha256": c["pins"]["body_profile_sha256"],
           "observer_sha256": T.sha(S.observer(c))}
    for key, path in sorted(kit_paths(c).items()):
        ids[key + "_sha256"] = T.sha(path)
    T.write_json(os.path.join(staged, "IDENTITIES.json"), ids, exclusive=True)
    print(json.dumps(ids, indent=1))
    print("BUILT: the qualification CPM differs from the candidate in line %d only" % ids["changed_line"])


def kit_changed(c, ids):
    return [k for k, path in sorted(kit_paths(c).items()) if T.sha(path) != ids.get(k + "_sha256")] + \
        (["observer"] if T.sha(S.observer(c)) != ids.get("observer_sha256") else [])


def cmd_pre(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    ids = S.identities(c)
    if ids is None:
        problems.append("run build first")
    else:
        changed = kit_changed(c, ids)
        if changed:
            problems.append("kit files changed after build: %s" % changed)
    st, cpm = S.state(c)
    if st != "published":
        problems.append("the installation is not the published state (CPM %s)" % cpm)
    try:
        model = EC.model_check(c)
    except Exception as exc:                 # an unreadable game folder refuses; it is never inferred
        model = {"problems": ["the model identity is unreadable: %r" % (exc,)], "pass": False}
    problems += model["problems"]
    chars = os.path.join(S.p(c, "LIBRARY"), "Characters")
    existing = [n for n in (sorted(os.listdir(chars)) if os.path.isdir(chars) else [])
                if os.path.exists(os.path.join(chars, n, "Poses"))]
    if existing:
        problems.append("the preset library already holds Poses folders (%s): stop and report" % existing)
    if os.path.lexists(character_dir(c)):
        problems.append("the Engineer's character folder %s already exists: stop and report" % character_dir(c))
    for d in ("pre_run", "sessions", "observations", "evidence"):
        if os.path.exists(S.q(c, d)):
            problems.append("%s already exists" % S.q(c, d))
    S.refuse(problems, "PRE")
    print("MODEL PASS: %s (%s)" % (model["resolved"], model["sha256"]))
    print("pre: recording backups and four inventories; this takes a few minutes. Wait for PRE PASS.")
    pre_dir = S.q(c, "pre_run")
    os.makedirs(os.path.join(pre_dir, "backup", "housekeeping"))
    for d in ("sessions", "observations", "evidence"):
        os.makedirs(S.q(c, d))
    T.copy_verified(T.installed(c), os.path.join(pre_dir, "backup", "SFM_Character_Preset_Manager_published.py"),
                    c["pins"]["published_cpm_sha256"])
    house = {}
    for rel in c["housekeeping"]:
        src = os.path.join(S.p(c, "GAME"), "usermod", rel)
        if os.path.isfile(src):
            T.copy_verified(src, os.path.join(pre_dir, "backup", "housekeeping", rel.replace("\\", "__")), T.sha(src))
            house[rel] = T.sha(src)
        else:
            house[rel] = None
    pyc = {}
    for d, _, files in os.walk(S.p(c, "SCRIPTS_ROOT")):
        for name in files:
            if name.endswith(".pyc"):
                src = os.path.join(d, name)
                rel = os.path.relpath(src, S.p(c, "SCRIPTS_ROOT"))
                dst = os.path.join(pre_dir, "backup", "pyc", rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                T.copy_verified(src, dst, T.sha(src))
                pyc[rel] = T.sha(src)
    inv = dict((k, T.inventory(S.p(c, k))) for k in S.INVENTORIES)
    for k, v in inv.items():
        with open(os.path.join(pre_dir, "inventory_%s.txt" % k), "w") as f:
            f.write("\n".join(v["rows"]) + "\n")
    T.write_json(os.path.join(pre_dir, "pre.json"), {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"), "at_epoch": time.time(), "installation": "published",
        "installed_cpm_sha256": cpm, "identities": ids, "model": model, "housekeeping": house, "pyc": pyc,
        "character_dir_existed": False,
        "inventories": dict((k, {"files": v["files"], "sha256": v["sha256"]}) for k, v in inv.items()),
        "pass": True}, exclusive=True)
    print("PRE PASS: backups and inventories are in place; nothing was installed. The disposable session folder is "
          "%s (empty). Next: preparation step 0" % S.q(c, "sessions"))


def sessions_state(c):
    """The two prepared sessions and SFM's autosave copies in Q/sessions, classified (never pinned: autosaves)."""
    rows = SF.classify_folder(S.q(c, "sessions"))
    src, dst = SF.by_name(rows, SOURCE), SF.by_name(rows, DESTINATION)
    autosaves = [r for r in rows if r["class"] == "autosave"]
    other = [r for r in rows if r not in (src, dst) and r["class"] != "autosave"]
    return rows, src, dst, autosaves, other


def cmd_inspect(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    rows, src, dst, autosaves, other = sessions_state(c)
    for name, row in ((SOURCE, src), (DESTINATION, dst)):
        if row is None:
            problems.append("%s does not exist (preparation step 0 saves it)" % name)
        elif row["class"] != "character":
            problems.append("%s is a %s session, not one holding the Engineer (was it saved after the model was "
                            "added?)" % (row["name"], row["class"]))
    if src is not None and dst is not None and src.get("sha256") == dst.get("sha256"):
        problems.append("the destination is byte-identical to the source: it was not prepared")
    if other:
        problems.append("unexpected files in the sessions folder: %s" % [r["name"] for r in other])
    if os.path.exists(S.q(c, "evidence", "destination.json")):
        problems.append("the sessions were already pinned")
    if os.path.isfile(S.q(c, "pre_run", "install_journal.json")):
        problems.append("an installation was already started")
    S.refuse(problems, "INSPECT")
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "source_name": src["name"], "source_sha256": src["sha256"],
              "destination_name": dst["name"], "destination_sha256": dst["sha256"],
              "autosaves_at_inspect": [dict((k, r[k]) for k in ("name", "sha256", "mtime")) for r in autosaves],
              "files": rows, "pass": True}
    T.write_json(S.q(c, "evidence", "destination.json"), result, exclusive=True)
    print(json.dumps(dict((k, v) for k, v in result.items() if k != "files"), indent=1))
    print("INSPECTED: %s and %s are pinned%s. Next: install" % (
        src["name"], dst["name"], (" (SFM autosaves recorded: %s)" % [r["name"] for r in autosaves])
        if autosaves else ""))


def cmd_restore(c):
    running = T.sfm_running()
    if running:
        raise SystemExit("REFUSED: %s; close SFM first" % running)
    pre = T.read_json(S.q(c, "pre_run", "pre.json"))
    char = character_dir(c)
    moved = []
    if pre.get("character_dir_existed") is False and os.path.isdir(char):
        dest_root = S.q(c, "evidence", "library_character", c["character_dir"])
        for d, dirs, files in os.walk(char):
            rel_dir = os.path.relpath(d, char)
            if rel_dir.split(os.sep)[0] == "Poses":
                continue
            for name in sorted(files):
                src = os.path.join(d, name)
                rel = os.path.normpath(os.path.join(rel_dir, name))
                target = os.path.join(dest_root, rel)
                if os.path.exists(target):
                    raise SystemExit("REFUSED: %s exists" % target)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                digest = T.sha(src)
                T.copy_verified(src, target, digest)
                moved.append({"file": rel.replace("\\", "/"), "sha256": digest})
        for row in moved:
            os.remove(os.path.join(char, row["file"].replace("/", os.sep)))
        log = S.q(c, "evidence", "library_character.json")
        previous = T.read_json(log)["moved"] if os.path.isfile(log) else []
        T.write_json(log, {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "character_dir": c["character_dir"],
                           "moved": previous + moved})
        print("CHARACTER FOLDER: %d file(s) CPM wrote outside Poses moved into evidence/library_character" % len(moved))
    code = S.cmd_restore(c)
    if pre.get("character_dir_existed") is False and os.path.isdir(char):
        leftover = [os.path.join(d, n) for d, _, fs in os.walk(char) for n in fs]
        if leftover:
            print("CHARACTER FOLDER NOT EMPTY (left in place; report): %s" % leftover[:10])
            return 1
        for d, dirs, _ in sorted(os.walk(char, topdown=False), key=lambda r: -len(r[0])):
            os.rmdir(d)
        print("CHARACTER FOLDER REMOVED: %s (empty; it did not exist before the run)" % char)
    return code


def cmd_compare(c):
    import ef1_compare
    return ef1_compare.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": S.cmd_status, "inspect": cmd_inspect,
                "install": S.cmd_install, "check": S.cmd_check, "collect-logs": S.cmd_collect_logs,
                "restore": cmd_restore, "compare": cmd_compare}
    if len(argv) == 4 and argv[2] == "library":
        return S.cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
