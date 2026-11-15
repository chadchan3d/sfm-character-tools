# -*- coding: utf-8 -*-
"""F-01 UA-1: the short native UI acceptance check of the UI corrections after K2 (candidate d3d23d1, CPM
8eccf172...). Build, preparation, temporary installation, seeding, library snapshots, evidence collection and
restoration. Python 3, run with -I while SFM is closed (every command that changes a file refuses while sfm.exe runs).
Every command refuses, changing nothing, when a precondition fails.

Reused unchanged: the K2 kit's build derivation (one line, PROD_POSE_REGISTRY_MODE = u"qualification") and pre (a
verified copy of the R2 fixture and of S3's prepared destination session), and through it the S3 tool's install,
check, collect-logs and restore (four protected inventories, backups of the published CPM, housekeeping and .pyc
files, an installation journal written first, verified copies).

Own commands:
  build         K2's build with this kit's pins: the UA-1 qualification CPM ea670f51... from candidate 8eccf172...
  pre           K2's pre (UA_SOURCE.dmx, UA_DESTINATION.dmx), then a verified backup of the whole preset library and
                the list of every library folder (including empty ones) in Q/pre_run
  seed          copy two existing records into Krystal's Poses folder: K2's updated version 2 "K2 Pose" (no source
                project recorded) and the pinned version 1 "NQ1 Pose A"
  library TAG   read-only: every preset-library file that differs from the pre-run library, into
                Q/evidence/library_TAG.json
  restore       library cleanup first (the run's library changes are copied into Q/evidence/library_after, then the
                library is put back exactly as backed up at pre: added files removed, changed and removed files
                restored, only folders that did not exist at pre removed, folders that existed at pre kept or
                recreated), then the S3 restore (published CPM, registries removed, .pyc and housekeeping, every
                inventory equal to its baseline)
  compare       run tools/ua_compare.py (Q/evidence/UA_VERDICT.json and UA_VERDICT.md)

usage: python -I ua_tool.py UA.json build | pre | status | install | seed | check | library TAG | collect-logs |
                                     restore | compare
"""
from __future__ import print_function

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "..", "f01_k2_krystal", "tools"))
sys.path.insert(0, HERE)
import k2_tool as K  # noqa: E402

S = K.S
T = S.T
FORMAT = "F01-UA1-config-v1"
SOURCE = "UA_SOURCE.dmx"
DESTINATION = "UA_DESTINATION.dmx"

# This kit's identity in the reused tools.
S.FORMAT = FORMAT
S.SESSIONS = (SOURCE,)
S.DESTINATION = DESTINATION
K.SOURCE, K.DESTINATION = SOURCE, DESTINATION
S.tools_dir = lambda c: KIT
K.comparator = lambda: os.path.join(HERE, "ua_compare.py")


def capture_script(c):
    return os.path.join(KIT, "observer", "F01_UA_Capture.py")


def library(c):
    return S.p(c, "LIBRARY")


def folders(root):
    """Every folder under root (relative, '/'-separated), including empty ones."""
    out = []
    for d, dirs, _ in os.walk(root):
        for name in dirs:
            out.append(os.path.relpath(os.path.join(d, name), root).replace("\\", "/"))
    return sorted(out)


def cmd_build(c):
    if T.sha(capture_script(c)) != c["pins"]["capture_sha256"]:
        S.refuse(["the UA capture script is not the pinned %s" % c["pins"]["capture_sha256"]], "BUILD")
    K.cmd_build(c)


def cmd_pre(c):
    problems = []
    for key, pin in (("K2_POSE", "k2_pose_sha256"), ("LEGACY_POSE", "legacy_pose_sha256")):
        if not os.path.isfile(S.p(c, key)) or T.sha(S.p(c, key)) != c["pins"][pin]:
            problems.append("%s is not %s" % (S.p(c, key), c["pins"][pin]))
    if os.path.exists(S.q(c, "pre_run")):
        problems.append("%s exists" % S.q(c, "pre_run"))
    S.refuse(problems, "PRE")
    K.cmd_pre(c)
    result = backup_library(c)
    print("PRE PASS (UA-1): preset library backed up (%d files, %d folders). Next: install" % (
        result["files"], len(result["folders"])))


def backup_library(c):
    """A verified copy of every preset-library file (its pre-run inventory is S3 pre's inventory_LIBRARY.txt) and
    the list of every library folder, including empty ones (the PS-2 cleanup removed an empty pre-existing folder,
    PS2-D1, because file inventories cannot see it)."""
    with open(S.q(c, "pre_run", "inventory_LIBRARY.txt")) as f:
        rows = [r for r in f.read().splitlines() if r]
    if rows != T.inventory(library(c))["rows"]:
        S.refuse(["the preset library changed after its pre-run inventory"], "PRE (library backup)")
    backup = S.q(c, "pre_run", "backup", "library")
    for row in rows:
        digest, rel = row.split("  ", 1)
        dst = os.path.join(backup, *rel.split("/"))
        if not os.path.isdir(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))
        T.copy_verified(os.path.join(library(c), *rel.split("/")), dst, digest)
    result = {"files": len(rows), "folders": folders(library(c))}
    T.write_json(S.q(c, "pre_run", "library.json"), result, exclusive=True)
    return result


def cmd_seed(c):
    problems = []
    running = T.sfm_running()
    if running:
        problems.append(running)
    if S.state(c)[0] != "qualification":
        problems.append("the qualification build is not installed (run install first)")
    if os.path.lexists(S.poses_dir(c)):
        problems.append("%s already exists" % S.poses_dir(c))
    if os.path.exists(S.q(c, "evidence", "seed.json")):
        problems.append("already seeded")
    for key, pin in (("K2_POSE", "k2_pose_sha256"), ("LEGACY_POSE", "legacy_pose_sha256")):
        if T.sha(S.p(c, key)) != c["pins"][pin]:
            problems.append("%s is not %s" % (S.p(c, key), c["pins"][pin]))
    S.refuse(problems, "SEED")
    os.makedirs(S.poses_dir(c))
    files = {}
    for key, pin in (("K2_POSE", "k2_pose_sha256"), ("LEGACY_POSE", "legacy_pose_sha256")):
        name = os.path.basename(S.p(c, key))
        T.copy_verified(S.p(c, key), os.path.join(S.poses_dir(c), name), c["pins"][pin])
        files[name] = c["pins"][pin]
    T.write_json(S.q(c, "evidence", "seed.json"), {"at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                                    "poses_dir": S.poses_dir(c), "files": files}, exclusive=True)
    print("SEEDED: %s. Next: Process A" % ", ".join(sorted(files)))


def library_rows(c):
    """(status, rel, sha256) for every library file added, changed or removed since pre."""
    base = {}
    with open(S.q(c, "pre_run", "inventory_LIBRARY.txt")) as f:
        for line in f.read().splitlines():
            if line:
                digest, rel = line.split("  ", 1)
                base[rel] = digest
    now = {}
    for row in T.inventory(library(c))["rows"]:
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
    if not tag.isalnum():
        raise SystemExit("REFUSED: the tag must be letters and digits")
    running = T.sfm_running()
    if running:
        raise SystemExit("REFUSED: %s; close SFM first" % running)
    path = S.q(c, "evidence", "library_%s.json" % tag)
    rows = library_rows(c)
    T.write_json(path, {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": tag,
                        "differences": [{"status": s, "path": r, "sha256": d} for s, r, d in rows]}, exclusive=True)
    print("LIBRARY %s: %d differences from the pre-run library recorded" % (tag, len(rows)))


def cleanup_library(c):
    """Put the preset library back exactly as backed up at pre; the run's changes are kept in evidence first."""
    pre = T.read_json(S.q(c, "pre_run", "library.json"))
    rows = library_rows(c)
    keep = S.q(c, "evidence", "library_after")
    if os.path.exists(keep):
        raise SystemExit("REFUSED: %s exists" % keep)
    os.makedirs(keep)
    for status, rel, digest in rows:
        if status != "removed":
            dst = os.path.join(keep, *rel.split("/"))
            if not os.path.isdir(os.path.dirname(dst)):
                os.makedirs(os.path.dirname(dst))
            T.copy_verified(os.path.join(library(c), *rel.split("/")), dst, digest)
    backup = S.q(c, "pre_run", "backup", "library")
    for status, rel, digest in rows:
        path = os.path.join(library(c), *rel.split("/"))
        if status == "added":
            os.remove(path)
        else:
            src = os.path.join(backup, *rel.split("/"))
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            T.copy_verified(src, path, T.sha(src))
    kept = set(pre["folders"])
    removed = []
    for rel in sorted(folders(library(c)), key=lambda r: -r.count("/")):
        path = os.path.join(library(c), *rel.split("/"))
        if rel not in kept and os.path.isdir(path) and not os.listdir(path):
            os.rmdir(path)
            removed.append(rel)
    recreated = []
    for rel in sorted(kept):
        path = os.path.join(library(c), *rel.split("/"))
        if not os.path.isdir(path):
            os.makedirs(path)
            recreated.append(rel)
    now = folders(library(c))
    result = {"at": time.strftime("%Y-%m-%d %H:%M:%S"),
              "differences_kept_in_evidence": [{"status": s, "path": r, "sha256": d} for s, r, d in rows],
              "removed_run_folders": removed, "recreated_folders": recreated,
              "folders_equal_pre": now == sorted(kept), "files_equal_pre": not library_rows(c)}
    T.write_json(S.q(c, "evidence", "library_cleanup.json"), result, exclusive=True)
    return result


def cmd_restore(c):
    running = T.sfm_running()
    if running:
        raise SystemExit("REFUSED: %s; close SFM first" % running)
    if not os.path.isfile(S.q(c, "pre_run", "library.json")):
        raise SystemExit("REFUSED: no library backup (run pre first)")
    cleaned = cleanup_library(c)
    print(json.dumps(cleaned, indent=1))
    if not (cleaned["folders_equal_pre"] and cleaned["files_equal_pre"]):
        print("LIBRARY CLEANUP INCOMPLETE: report the differences above; the S3 restore still runs")
    code = S.cmd_restore(c)
    if not (cleaned["folders_equal_pre"] and cleaned["files_equal_pre"]):
        return 1
    return code


def cmd_compare(c):
    import ua_compare
    return ua_compare.run(c)


def main(argv):
    commands = {"build": cmd_build, "pre": cmd_pre, "status": S.cmd_status, "install": S.cmd_install,
                "seed": cmd_seed, "check": S.cmd_check, "collect-logs": S.cmd_collect_logs, "restore": cmd_restore,
                "compare": cmd_compare}
    if len(argv) == 4 and argv[2] == "library":
        return cmd_library(S.load(argv[1]), argv[3]) or 0
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    return commands[argv[2]](S.load(argv[1])) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
