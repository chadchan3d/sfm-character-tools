# -*- coding: utf-8 -*-
"""F-01 NQ-1 key-placement investigation (KP-1): offline preparation and verdict (Python 3, -I).

usage: python -I kp1_tool.py <KP1 run folder>\\kp1.json pre|post

pre   SFM closed. Verifies the R2 fixture and the published installation, creates the disposable session copy
      <Q>\\sessions\\KP1_SESSION.dmx (exclusive create, byte-identical to R2) and <Q>\\observations, and records
      <Q>\\evidence\\pre.json (hashes and the preset-library inventory). Writes nothing outside <Q>.
post  SFM closed. Verifies that the R2 fixture, the session copy (never saved), the installed CPM, the absent pose
      profile and the preset library are unchanged, then compares KP-01 (before) with KP-02 (after) and writes
      <Q>\\evidence\\KP1_VERDICT.json. Read-only outside <Q>\\evidence.

The verdict names a single authored tick only when exactly one channel (Hand_l_p) changed, only by one added key or
one modified key, at one tick, with every other channel unchanged. Anything else is reported as inconclusive. Evaluated bone
movement (the arm IK following the hand) is not compared: only authored keys are.
"""
from __future__ import print_function

import hashlib
import json
import os
import subprocess
import sys
import uuid

CPM_REL = ("usermod", "scripts", "ChadChan3D_CPM", "SFM_Character_Preset_Manager.py")
PROFILE_REL = ("usermod", "scripts", "SFM Character Tools", "cpm_pose_profiles_v1.json")
TARGET = "Hand_l_p#0"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def write_json(path, value):
    data = json.dumps(value, indent=1, sort_keys=True).encode("utf-8")
    with open(path, "xb") as f:
        f.write(data)


def sfm_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq sfm.exe", "/NH"], capture_output=True, text=True).stdout
    return "sfm.exe" in out.lower()


def inventory(root):
    rows = []
    if os.path.isdir(root):
        for base, dirs, files in os.walk(root):
            dirs.sort()
            for name in sorted(files):
                p = os.path.join(base, name)
                st = os.stat(p)
                rows.append([os.path.relpath(p, root), st.st_size, sha(p)])
    return rows


def guid_raw(s):
    """The element id as 32 hex digits in DMX byte order ('02ab2a1a-caab-...' natively, '1a2aab02abca...' offline)."""
    s = (s or "").strip().lower()
    try:
        return uuid.UUID(s).bytes_le.hex() if len(s) == 36 else s
    except ValueError:
        return s


def state(c):
    game = c["GAME"]
    cpm = os.path.join(game, *CPM_REL)
    return {"r2_sha256": sha(c["R2_FIXTURE"]), "installed_cpm_sha256": sha(cpm) if os.path.isfile(cpm) else None,
            "profile_present": os.path.lexists(os.path.join(game, *PROFILE_REL)),
            "library_inventory": inventory(c["LIBRARY"])}


def cmd_pre(c, q):
    if sfm_running():
        raise SystemExit("REFUSED: SFM is running; close it first")
    s = state(c)
    if s["r2_sha256"] != c["r2_fixture_sha256"]:
        raise SystemExit("REFUSED: the R2 fixture is not %s" % c["r2_fixture_sha256"])
    if s["installed_cpm_sha256"] != c["published_cpm_sha256"] or s["profile_present"]:
        raise SystemExit("REFUSED: the published installation is not in place")
    for d in ("sessions", "observations", "evidence"):
        os.makedirs(os.path.join(q, d), exist_ok=True)
    if os.listdir(os.path.join(q, "observations")):
        raise SystemExit("REFUSED: <Q>\\observations is not empty")
    session = os.path.join(q, "sessions", "KP1_SESSION.dmx")
    with open(c["R2_FIXTURE"], "rb") as src, open(session, "xb") as dst:
        dst.write(src.read())
    s["session_sha256"] = sha(session)
    if s["session_sha256"] != c["r2_fixture_sha256"]:
        raise SystemExit("FAILED: the session copy differs from R2")
    write_json(os.path.join(q, "evidence", "pre.json"), s)
    print("PRE PASS: %s is a byte-identical copy of R2; installation published; baselines recorded" % session)
    return 0


def diff_layers(before, after):
    """Added, removed and modified keys of one channel (all layers), or None when the layer structure changed."""
    if not isinstance(before, list) or not isinstance(after, list) or len(before) != len(after):
        return {"structure": [before if not isinstance(before, list) else len(before),
                              after if not isinstance(after, list) else len(after)]}
    out = {"added": [], "removed": [], "modified": []}
    for i, (b, a) in enumerate(zip(before, after)):
        bt, at = dict((k[0], k[1]) for k in b), dict((k[0], k[1]) for k in a)
        out["added"] += [[i, t, at[t]] for t in sorted(set(at) - set(bt))]
        out["removed"] += [[i, t, bt[t]] for t in sorted(set(bt) - set(at))]
        out["modified"] += [[i, t, bt[t], at[t]] for t in sorted(set(at) & set(bt)) if at[t] != bt[t]]
    return out


def compare(c, q):
    """KP-1: KP-01 (before) and KP-02 (after). KP-2 (config "sequence": "kp2"): KP-01 before the Graph Editor,
    KP-02 isolated and settled (before insertion), KP-03 after the create-key command, KP-04 after Undo; the change
    is judged from KP-02 to KP-03 by the same rule, and Undo must restore KP-02 exactly."""
    obs = os.path.join(q, "observations")
    names = sorted(x for x in os.listdir(obs) if x.startswith("KP-") and x.endswith(".json"))
    if c.get("sequence") != "kp2":
        return compare_pair(c, q, names, names, ("KP-01", "KP-02"))
    want = ["KP-01.json", "KP-02.json", "KP-03.json", "KP-04.json"]
    if names != want:
        return ["expected exactly %s, found %s" % (want, names)], {"observations": names}
    problems, report = compare_pair(c, q, names, ["KP-02.json", "KP-03.json"], ("KP-02", "KP-03"))
    o = dict((n[:5], read_json(os.path.join(obs, n))) for n in names)
    for label in ("KP-01", "KP-04"):
        if o[label].get("problems"):
            problems.append("%s observer problems: %s" % (label, o[label]["problems"]))
    if problems:
        return problems, report
    report["clocks"] = dict((k, {"t_doc": v.get("t_doc"), "t_chan_converted": v.get("t_chan_converted"),
                                 "get_current_time": v.get("watched_current_ticks"), "undo": v.get("undo")})
                            for k, v in sorted(o.items()))
    report["graph_editor_entry_changed_clocks"] = (o["KP-01"]["watched_current_ticks"] !=
                                                   o["KP-02"]["watched_current_ticks"])
    keys = lambda x: dict((n, ch["layers"]) for n, ch in x["channels"].items())  # noqa: E731
    report["graph_editor_entry_changed_keys"] = sorted(n for n in keys(o["KP-01"])
                                                       if keys(o["KP-01"])[n] != keys(o["KP-02"]).get(n))
    if o["KP-01"]["pid"] != o["KP-04"]["pid"] or o["KP-02"]["pid"] != o["KP-04"]["pid"]:
        problems.append("the observations come from different SFM processes")
    undo_keys = sorted(n for n in keys(o["KP-02"]) if keys(o["KP-02"])[n] != keys(o["KP-04"]).get(n))
    report["undo_restored_keys_exactly"] = not undo_keys
    report["undo_restored_elsewhere_exactly"] = o["KP-02"]["elsewhere"] == o["KP-04"]["elsewhere"]
    report["undo_restored_undo_state"] = o["KP-02"]["undo"] == o["KP-04"]["undo"]
    report["undo_differences"] = undo_keys[:20]
    return problems, report


def compare_pair(c, q, names, pair, labels):
    obs = os.path.join(q, "observations")
    problems, report = [], {"observations": names}
    if c.get("sequence") != "kp2" and names != ["KP-01.json", "KP-02.json"]:
        problems.append("expected exactly KP-01.json and KP-02.json, found %s" % names)
        return problems, report
    b, a = read_json(os.path.join(obs, pair[0])), read_json(os.path.join(obs, pair[1]))
    for label, o in ((labels[0], b), (labels[1], a)):
        if o.get("problems"):
            problems.append("%s observer problems: %s" % (label, o["problems"]))
        if not os.path.normcase(o.get("document") or "").endswith("kp1_session.dmx"):
            problems.append("%s document is %r, not KP1_SESSION.dmx" % (label, o.get("document")))
        if (o.get("shot") or {}).get("name") != c["shot"]:
            problems.append("%s shot is %r" % (label, (o.get("shot") or {}).get("name")))
        if guid_raw((o.get("animation_set") or {}).get("id")) != c["animation_set_id"]:
            problems.append("%s Krystal is not %s" % (label, c["animation_set_id"]))
        if o.get("t_doc") != c["t_doc_ticks"] or o.get("t_chan_converted") != c["cpm_time_ticks"]:
            problems.append("%s playhead %r / converted %r, expected %d / %d" % (
                label, o.get("t_doc"), o.get("t_chan_converted"), c["t_doc_ticks"], c["cpm_time_ticks"]))
    if problems:
        return problems, report
    if a["pid"] != b["pid"]:
        problems.append("%s and %s come from different SFM processes" % labels)
    report["ownership_before"], report["ownership_after"] = b["ownership"], a["ownership"]
    if b["ownership"] != a["ownership"] or b["clip"] != a["clip"]:
        problems.append("channel or clip ownership changed between the observations")
    report["get_current_time"] = {"before": b["watched_current_ticks"], "after": a["watched_current_ticks"]}
    report["undo"] = {"before": b["undo"], "after": a["undo"]}
    changed = {}
    for name in sorted(set(b["channels"]) | set(a["channels"])):
        x, y = b["channels"].get(name), a["channels"].get(name)
        if x is None or y is None:
            changed[name] = {"presence": [x is not None, y is not None]}
        elif x["layers"] != y["layers"]:
            changed[name] = diff_layers(x["layers"], y["layers"])
    report["changed_channels"] = changed
    report["elsewhere_changed"] = sorted(k for k in set(b["elsewhere"]) | set(a["elsewhere"])
                                         if b["elsewhere"].get(k) != a["elsewhere"].get(k))
    report["elsewhere_count"] = len(b["elsewhere"])
    t_cpm, t_cur = c["cpm_time_ticks"], c["current_time_ticks"]
    ticks = sorted(set(k[1] for d in changed.values() for kind in ("added", "removed", "modified")
                       for k in d.get(kind, [])))
    report["changed_ticks"] = ticks
    # Which vector components the edits touched (an isolated Graph Editor edit changes one component).
    comps = {}
    for name, d in changed.items():
        for k in d.get("modified", []):
            comps[name] = sorted(set(comps.get(name, [])) | set(
                i for i, (x, y) in enumerate(zip(k[2], k[3])) if x != y) if isinstance(k[2], list) else ["scalar"])
    report["modified_components"] = comps
    if not changed:
        result = "inconclusive: no channel's keys changed (no key was authored)"
    elif list(changed) != [TARGET]:
        result = "inconclusive: several channels changed: %s" % sorted(changed)
    elif report["elsewhere_changed"]:
        result = "inconclusive: channels in other clips changed"
    else:
        d = changed[TARGET]
        edits = len(d.get("added", [])) + len(d.get("removed", [])) + len(d.get("modified", []))
        if "structure" in d or edits != 1 or d.get("removed"):
            result = "inconclusive: %s changed by %d key edits %s" % (TARGET, edits, d)
        elif ticks == [t_cur]:
            result = "authored-at-get-current-time: one %s key at %d (GetCurrentTime)" % (
                "new" if d["added"] else "modified", t_cur)
        elif ticks == [t_cpm]:
            result = "authored-at-cpm-time: one %s key at %d (CPM's conversion)" % (
                "new" if d["added"] else "modified", t_cpm)
        else:
            result = "inconclusive: one key edit at %s, neither %d nor %d" % (ticks, t_cpm, t_cur)
    report["result"] = result
    return problems, report


def cmd_post(c, q):
    if sfm_running():
        raise SystemExit("REFUSED: SFM is running; close it first")
    pre = read_json(os.path.join(q, "evidence", "pre.json"))
    now = state(c)
    now["session_sha256"] = sha(os.path.join(q, "sessions", "KP1_SESSION.dmx"))
    integrity = ["%s changed" % k for k in sorted(pre) if pre[k] != now.get(k)]
    found, report = compare(c, q)
    problems = integrity + found
    verdict = {"integrity_problems": integrity, "observation_problems": found, "report": report,
               "result": report.get("result") if not problems else "unresolved: see the problems"}
    write_json(os.path.join(q, "evidence", "KP1_VERDICT.json"), verdict)
    print(json.dumps({k: verdict[k] for k in ("integrity_problems", "observation_problems", "result")}, indent=1))
    return 0 if not problems else 1


def main(argv):
    if len(argv) != 3 or argv[2] not in ("pre", "post"):
        raise SystemExit(__doc__)
    c = read_json(argv[1])
    q = os.path.dirname(os.path.abspath(argv[1]))
    return {"pre": cmd_pre, "post": cmd_post}[argv[2]](c, q)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
