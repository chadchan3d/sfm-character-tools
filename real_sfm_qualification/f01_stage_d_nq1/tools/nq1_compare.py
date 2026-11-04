# -*- coding: utf-8 -*-
"""F-01 Stage D NQ-1: offline verdict from the observations (Python 3, -I). Read-only.

usage: python -I nq1_compare.py NQ1.json
Reads <Q>/observations/OBS-01..OBS-11.json, the two saved pose files (in the library or, after restore, in
<Q>/evidence/library_poses) and <Q>/evidence/destination_inspection.json; writes <Q>/evidence/NQ1_VERDICT.json.
"""
from __future__ import print_function

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nq1_tool as T  # noqa: E402

# Abort runs with an empty Redo stack (right after Apply B): W2 qualified AbortUndoableOperation there; with a
# non-empty Redo stack the aborted operation's own writes could clear it.
STEPS = ("A_saved_pose_a", "A_saved_pose_b", "B_baseline", "B_applied_a", "B_undo_a", "B_redo_a", "B_noop_a",
         "B_applied_b", "B_abort", "B_undo_b", "B_final_undo")
WRITTEN = ("Hand_l.positionChannel", "Hand_l.orientationChannel", "Elbow_l.positionChannel")
OBSERVED = "Elbow_l.orientationChannel"
ARM_BONES = ("bip_UpperArm_l", "bip_lowerArm_l", "bip_hand_l")


def angle(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    d = min(1.0, abs(sum(x * y for x, y in zip(a, b))) / (na * nb))
    return math.degrees(2.0 * math.acos(d))


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def close(a, b, pos=1e-3, ang=1e-2):
    return (angle(a, b) <= ang) if len(a) == 4 else (dist(a, b) <= pos)


def keys(o, name):
    return o["channels"][name]["layers"][0]


def bone(o, name):
    hits = [v for k, v in o["bones"].items() if k.endswith("(%s)" % name)]
    return hits[0] if len(hits) == 1 else None


def main(argv):
    c = T.load(argv[1])
    q = T.p(c, "Q")
    names = c["pose_names"]
    t_chan = c["destination"]["t_chan_ticks"]
    msgs = c["expected_status"]
    obs = {}
    problems = []

    def need(ok, what):
        if not ok:
            problems.append(what)
        return ok
    for i, step in enumerate(STEPS, 1):
        path = os.path.join(q, "observations", "OBS-%02d.json" % i)
        if not need(os.path.isfile(path), "%s missing (OBS-%02d)" % (step, i)):
            continue
        obs[step] = T.read_json(path)
        need(not obs[step].get("problems"), "%s observer problems %s" % (step, obs[step].get("problems")))
    if problems:
        return finish(q, problems, obs)
    A1, A2, B0 = obs["A_saved_pose_a"], obs["A_saved_pose_b"], obs["B_baseline"]
    b_steps = STEPS[2:]
    # Persistence across a genuine restart, without the source animation sets.
    need(A1["pid"] == A2["pid"], "process A changed between its two saves")
    need(all(obs[s]["pid"] == B0["pid"] for s in b_steps), "process B changed during the destination steps")
    need(A1["pid"] != B0["pid"], "the destination ran in the source process")
    need(os.path.normcase(A1["document"]).endswith("nq1_source.dmx"), "process A document is not NQ1_SOURCE.dmx")
    need(all(os.path.normcase(obs[s]["document"]).endswith("nq1_destination.dmx") for s in b_steps),
         "process B document is not NQ1_DESTINATION.dmx")
    sources = set([A1["animation_set_id"], A2["animation_set_id"]])
    for s in b_steps:
        ids = set(a["id"] for shot in obs[s]["shots"] for a in shot["animation_sets"])
        need(not (ids & sources), "%s: a source animation set is present in the destination" % s)
    inspection = os.path.join(q, "evidence", "destination_inspection.json")
    need(os.path.isfile(inspection) and T.read_json(inspection).get("pass") is True,
         "the offline destination inspection did not pass")
    need(len(A2["pose_files"]) == 2, "process A did not leave exactly two pose files")
    need(all(obs[s]["pose_files"] == A2["pose_files"] for s in b_steps), "a pose file changed after process A")
    need(all(obs[s]["head_ticks"] == c["destination"]["t_doc_ticks"] for s in b_steps),
         "the destination playhead moved")
    need(all(obs[s]["cpm"] and obs[s]["cpm"]["registry_mode"] == u"qualification" for s in obs),
         "CPM was not the qualification build in every step")
    poses = load_poses(c, q, A2["pose_files"])
    need(sorted(poses) == sorted(names.values()), "the saved pose names are not %s" % sorted(names.values()))
    if problems:
        return finish(q, problems, obs)
    # Key creation (insert) and update at the exact channel time; the observed channel is never written.
    base = dict((n, keys(B0, n)) for n in WRITTEN)
    for n in WRITTEN:
        need(not [k for k in base[n] if k[0] == t_chan], "%s already has a key at the channel time" % n)
        need(B0["channels"][n]["current_ticks"] == t_chan, "%s channel time is not %d" % (n, t_chan))
    applied = obs["B_applied_a"]
    for n in WRITTEN:
        now = keys(applied, n)
        need(len(now) == len(base[n]) + 1 and [k for k in now if k[0] != t_chan] == base[n]
             and len([k for k in now if k[0] == t_chan]) == 1, "%s: not exactly one inserted key" % n)
    for s in b_steps:
        need(keys(obs[s], OBSERVED) == keys(B0, OBSERVED), "%s: the elbow orientation channel changed" % s)
    applied_b = obs["B_applied_b"]
    updated = 0
    for n in WRITTEN:
        a, b = keys(applied, n), keys(applied_b, n)
        need([k[0] for k in a] == [k[0] for k in b], "%s: the update changed key times or counts" % n)
        changed = [i for i in range(min(len(a), len(b))) if a[i][1] != b[i][1]]
        need(set(changed) <= set(i for i, k in enumerate(a) if k[0] == t_chan),
             "%s: the update changed a key other than the one at the channel time" % n)
        updated += len(changed)
    need(updated >= 1, "Apply B updated no key")
    # Rig inputs, skeletal oracle and placement after each Apply.
    for step, pose_name in (("B_applied_a", names["a"]), ("B_applied_b", names["b"])):
        o = obs[step]
        for n in WRITTEN:
            key = [k for k in keys(o, n) if k[0] == t_chan]
            need(key and close(o["rig_inputs"][n], key[0][1], 1e-4, 1e-3), "%s: rig input %s is not the key" %
                 (step, n))
        oracle = poses[pose_name]["pose"]["regions"]["left_arm"]["oracle"]["bones"]
        for b in ARM_BONES:
            need(bone(o, b) is not None and angle(bone(o, b)["orientation"], oracle[b]["local_orientation"]) <= 0.01,
                 "%s: %s local orientation differs from the pose" % (step, b))
        unrelated(o, B0, need, step)
    for step in ("B_applied_a", "B_redo_a", "B_noop_a", "B_applied_b", "B_abort", "B_undo_b"):
        unrelated(obs[step], B0, need, step)
    # Non-target authored values: every other channel's keys (all shots) are unchanged in every B step.
    others = B0.get("other_channels") or {}
    need(len(others) > 0, "B_baseline recorded no other channels")
    unreadable = sorted(k for k, v in others.items() if v == u"unreadable")
    need(not unreadable, "other channels unreadable, authored preservation unverified: %s" % unreadable[:10])
    for s in b_steps[1:]:
        now = obs[s].get("other_channels") or {}
        diff = sorted(k for k in set(now) | set(others) if now.get(k) != others.get(k))
        need(not diff, "%s: non-target authored channels changed: %s" % (s, diff[:10]))
    # Undo, Redo, no-op and Abort.
    same = lambda x, y: all(keys(x, n) == keys(y, n) for n in WRITTEN)  # noqa: E731
    label_a, label_b = u"Apply Pose " + names["a"], u"Apply Pose " + names["b"]
    need(applied["undo"]["undo_desc"] == label_a and applied["undo"]["can_undo"], "Apply A is not the top Undo entry")
    need(same(obs["B_undo_a"], B0) and arm_back(obs["B_undo_a"], B0), "Ctrl+Z did not restore the baseline")
    need(same(obs["B_redo_a"], applied) and arm_back(obs["B_redo_a"], applied), "Ctrl+Y did not restore Apply A")
    need(same(obs["B_noop_a"], applied) and obs["B_noop_a"]["undo"] == obs["B_redo_a"]["undo"],
         "the repeated Apply A was not a true no-op")
    need(applied_b["undo"]["undo_desc"] == label_b, "Apply B is not the top Undo entry")
    need(not applied_b["undo"]["can_redo"], "the Redo stack was not empty before the Abort step")
    need(same(obs["B_abort"], applied_b) and obs["B_abort"]["undo"] == applied_b["undo"] and
         arm_back(obs["B_abort"], applied_b), "the aborted Apply changed keys, the arm or Undo/Redo")
    need(same(obs["B_undo_b"], applied) and arm_back(obs["B_undo_b"], applied), "Ctrl+Z did not undo the update")
    need(same(obs["B_final_undo"], B0) and arm_back(obs["B_final_undo"], B0), "the final Ctrl+Z did not restore "
                                                                                "the baseline")
    for step, key in (("B_applied_a", "applied_a"), ("B_noop_a", "noop"), ("B_applied_b", "applied_b"),
                      ("B_abort", "not_applied")):
        need(obs[step]["cpm"]["status"] == msgs[key], "%s status %r, expected %r" % (step, obs[step]["cpm"]["status"],
                                                                                     msgs[key]))
    return finish(q, problems, obs)


def unrelated(o, base, need, step):
    for name, row in base["bones"].items():
        if any(name.endswith("(%s)" % b) for b in ARM_BONES):
            continue
        now = o["bones"].get(name)
        need(now is not None and close(now["position"], row["position"]) and
             close(now["orientation"], row["orientation"]), "%s: unrelated bone %s changed" % (step, name))
    need(close(o["model"]["position"], base["model"]["position"]) and
         close(o["model"]["orientation"], base["model"]["orientation"]), "%s: model placement changed" % step)
    for k, v in base["placement"].items():
        if v is not None:
            need(o["placement"].get(k) is not None and close(o["placement"][k], v), "%s: %s changed" % (step, k))


def arm_back(o, ref):
    return all(close(o["rig_inputs"][n], ref["rig_inputs"][n], 1e-4, 1e-3) for n in WRITTEN) and \
        all(close(bone(o, b)["orientation"], bone(ref, b)["orientation"]) for b in ARM_BONES)


def load_poses(c, q, files):
    """The saved pose records: in the library during the run, in <Q>/evidence/library_poses after restore."""
    out = {}
    for rel in files:
        char, _, name = rel.split("/")
        for path in (os.path.join(T.p(c, "LIBRARY"), "Characters", char, "Poses", name),
                     os.path.join(q, "evidence", "library_poses", char, name)):
            if os.path.isfile(path):
                record = T.read_json(path)
                out[record["name"]] = record
                break
    return out


def finish(q, problems, obs):
    verdict = {"verdict": "PASS" if not problems else "FAIL", "problems": problems,
               "observations": sorted(obs)}
    T.write_json(os.path.join(q, "evidence", "NQ1_VERDICT.json"), verdict)
    print(json.dumps(verdict, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
