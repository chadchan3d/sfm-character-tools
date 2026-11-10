# -*- coding: utf-8 -*-
"""F-01 NQ-03 header inventory: preparation, post-run verification and analysis. Python 3, run with -I while SFM is
closed. Nothing is installed: the published CPM stays in place and is not opened.

The NQ-S6 tool (f01_nq_s6/tools/nq_tool.py, itself the model survey's mc_tool) is reused unchanged for pre, copy,
status and post: SFM closed; the published CPM with no registry beside it; the pinned kit files; the listed game files'
hashes; the four protected inventories; housekeeping and .pyc backups and their restoration; a verified copy of the
preserved survey session (the S0 anchor), and the preserved original's hash after the run. Only this kit's files are
substituted (the inventory observer and the candidate list, both pinned). Added:
  resolve  offline, read-only, run after post: resolve every candidate through usermod's gameinfo SearchPaths (first
           loose file wins), record each resolved file and its SHA-256 in Q/evidence/resolution.json, and refuse
           unless the configuration's "models" list is exactly the resolved files (so the bytes pre/post pinned are
           the bytes SFM loads). pre and status refuse while Q/evidence holds anything, so resolve never runs first.
  analyze  nq03_analyze.py on Q/observations into Q/evidence (NQ03_ANALYSIS.json, NQ03_ANALYSIS.md)

Order: pre, copy, the native observation, post, resolve, analyze.

usage: python -I nq03_tool.py NQ03.json pre | copy | status | post | resolve | analyze
"""
from __future__ import print_function

import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "..", "f01_nq_s6", "tools"))
sys.path.insert(0, HERE)
import nq_tool as N  # noqa: E402

M = N.M


def kit_files(c):
    root = os.path.join(M.p(c, "REPO"), "real_sfm_qualification")
    return {"wrapper": os.path.join(root, "f01_nq03", "observer", "F01_NQ03_Inventory.py"),
            "s0_observer": os.path.join(root, "f01_full_body_s0", "observer", "F01_S0_Survey.py"),
            "candidates": os.path.join(root, "f01_nq03", "candidates.json")}


M.kit_files = kit_files                  # the only substitution in the reused tools: this kit's pinned files


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def search_paths(game):
    """usermod's gameinfo SearchPaths "Game" entries, in order (|gameinfo_path|. is usermod itself)."""
    with io.open(os.path.join(game, "usermod", "gameinfo.txt"), "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    block = text[text.index("SearchPaths"):]
    block = block[block.index("{") + 1:block.index("}")]
    out = []
    for key, value in re.findall(r'"([^"]+)"\s+"([^"]+)"', block):
        if key.lower() != "game":
            continue
        out.append("usermod" if value == "|gameinfo_path|." else value)
    return out


def resolve(c):
    game = M.p(c, "GAME")
    order = search_paths(game)
    with open(kit_files(c)["candidates"], "rb") as f:
        candidates = json.loads(f.read().decode("utf-8"))["candidates"]
    rows = []
    for cand in candidates:
        hit = None
        for folder in order:
            path = os.path.join(game, folder, cand["path"].replace("/", os.sep))
            if os.path.isfile(path):
                hit = (folder, path)
                break
        rows.append({"path": cand["path"], "family": cand.get("family"), "folder": hit[0] if hit else None,
                     "game_relative": "%s/%s" % (hit[0], cand["path"]) if hit else None,
                     "sha256": sha(hit[1]) if hit else None})
    return order, rows


def cmd_resolve(c):
    order, rows = resolve(c)
    missing = [r["path"] for r in rows if r["folder"] is None]
    resolved = [r["game_relative"] for r in rows if r["game_relative"]]
    problems = []
    if missing:
        problems.append("not found as loose files in any search path: %s" % missing)
    if list(c["models"]) != resolved:
        problems.append("the configuration's models list is not exactly the resolved files")
    out = os.path.join(M.p(c, "Q"), "evidence", "resolution.json")
    if os.path.exists(out):
        problems.append("%s exists" % out)
    if problems:
        print(json.dumps({"problems": problems, "resolved": resolved}, indent=1))
        raise SystemExit("RESOLVE NOT PERFORMED (nothing was changed)")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    data = json.dumps({"format": "F01-NQ03-resolution-v1", "search_paths": order, "models": rows}, indent=1,
                      sort_keys=True).encode("utf-8")
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    print("RESOLVE PASS: %d candidates resolved to loose files; pins in %s" % (len(rows), out))


def cmd_analyze(c):
    import nq03_analyze
    q = M.p(c, "Q")
    return nq03_analyze.main(["nq03_analyze.py", os.path.join(q, "observations"), os.path.join(q, "evidence")])


def main(argv):
    commands = {"resolve": cmd_resolve, "pre": M.cmd_pre, "copy": N.cmd_copy, "status": M.cmd_status,
                "post": N.cmd_post, "analyze": cmd_analyze}
    if len(argv) != 3 or argv[2] not in commands:
        print(__doc__)
        return 2
    c = M.load(argv[1])
    return commands[argv[2]](c) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
