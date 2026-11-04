# -*- coding: utf-8 -*-
"""F-01 Stage D integrated Motion Editor qualification (ME-1): offline verdict (Python 3, -I). Read-only.

usage: python -I me1_compare.py <Q>\\nq1.json
Sequence (OBS-01 .. OBS-10 in <Q>\\observations, all in timeline mode 2):
  base, applied_a, noop_a, applied_b, undo_b, undo_a, redo_a, redo_b, away, returned
Each Apply must display automatically (no manual refresh) and report its status; each Undo/Redo must reverse the
expected Apply (top entry before Undo, next Redo before Redo). Writes <Q>\\evidence\\ME1_VERDICT.json.
"""
from __future__ import print_function

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nq1_tool as T  # noqa: E402
from fa1_compare import ARM_BONES, OBSERVED, WRITTEN, angle, bone, close, keys  # noqa: E402

STEPS = ("base", "applied_a", "noop_a", "applied_b", "undo_b", "undo_a", "redo_a", "redo_b", "away", "returned")


def main(argv):
    c = T.load(argv[1])
    q = T.p(c, "Q")
    t_doc, t_chan = c["destination"]["t_doc_ticks"], c["destination"]["t_chan_ticks"]
    away_ticks, names, msgs = c["me1"]["away_ticks"], c["pose_names"], c["expected_status"]
    label = dict((k, u"Apply Pose " + v) for k, v in names.items())
    problems, findings = [], {}
    steps = tuple(c["me1"].get("steps") or STEPS)   # ME-1b: a focused subset, in order

    def need(ok, what):
        if not ok:
            problems.append(what)
        return bool(ok)
    obs = {}
    for i, s in enumerate(steps, 1):
        path = os.path.join(q, "observations", "OBS-%02d.json" % i)
        if need(os.path.isfile(path), "%s missing (OBS-%02d)" % (s, i)):
            obs[s] = T.read_json(path)
            need(not obs[s].get("problems"), "%s observer problems %s" % (s, obs[s].get("problems")))
    extra = sorted(n for n in os.listdir(os.path.join(q, "observations")) if n.startswith("OBS-"))[len(steps):]
    need(not extra, "unexpected extra observations %s" % extra)
    if problems:
        return finish(q, problems, findings, steps)
    B = obs["base"]
    # Context: one process, the destination, the shot15 Krystal, mode 2 and the exact playhead throughout.
    need(len(set(o["pid"] for o in obs.values())) == 1, "the observations come from different SFM processes")
    need(all(os.path.normcase(o["document"]).endswith("nq1_destination.dmx") for o in obs.values()), "not the destination")
    need(all(o["animation_set_id"] == B["animation_set_id"] and o["current_shot"] == c["destination"]["shot"]
             for o in obs.values()), "the destination Krystal instance changed")
    modes = dict((s, (o.get("timeline_mode") or {}).get("value")) for s, o in obs.items())
    findings["timeline_modes"] = modes
    need(all(v == "2" for v in modes.values()), "not Motion Editor (2) throughout: %s" % modes)
    for s, o in obs.items():
        need(o["head_ticks"] == (away_ticks if s == "away" else t_doc), "%s playhead %s" % (s, o["head_ticks"]))
    clocks = dict((s, sorted(set(v["clock"] for v in o["rig_evaluated_at"].values()))) for s, o in obs.items())
    findings["clocks"] = clocks
    need(all(clocks[s] == [t_chan] and obs[s]["conversion"]["t_chan"] == t_chan for s in obs if s != "away"),
         "the channel clock or mapped tick is not %d at the original frame: %s" % (t_chan, clocks))
    need(not B["undo"]["can_redo"], "the baseline already had a Redo entry")
    # Expected authored states.
    A1, B1 = obs["applied_a"], obs["applied_b"]
    key_at = lambda o, n: [k for k in keys(o, n)[0] if k[0] == t_chan]  # noqa: E731
    for n in WRITTEN:
        a, b = keys(A1, n)[0], keys(B, n)[0]
        need(len(keys(A1, n)) == 1 and [k for k in a if k[0] != t_chan] == b and len(key_at(A1, n)) == 1
             and len(a) == len(b) + 1, "Apply A: %s is not exactly one key inserted at %d" % (n, t_chan))
        need([k[0] for k in keys(B1, n)[0]] == [k[0] for k in a] and [k for k in keys(B1, n)[0] if k[0] != t_chan]
             == [k for k in a if k[0] != t_chan], "Apply B: %s changed key times or a key other than %d" % (n, t_chan))
    findings["updated_channels"] = sorted(n for n in WRITTEN if key_at(B1, n) != key_at(A1, n))
    need(findings["updated_channels"], "Apply B updated no key")
    want = {"base": B, "applied_a": A1, "noop_a": A1, "applied_b": B1, "undo_b": A1, "undo_a": B, "redo_a": A1,
            "redo_b": B1, "away": B1, "returned": B1}
    for s, o in obs.items():
        need(all(keys(o, n) == keys(want[s], n) for n in WRITTEN) and keys(o, OBSERVED) == keys(B, OBSERVED),
             "%s: authored arm keys are not the expected state" % s)
        need(o["other_channels"] == B["other_channels"], "%s: unrelated authored channels changed" % s)
    # Evaluated states: rig = the keys at the original frame and the arm = the saved pose's oracle.
    poses = {}
    for name in c["seed"]["poses"]["files"]:
        r = T.read_json(os.path.join(c["seed"]["poses"]["source_dir"], name))
        poses[r["name"]] = r["pose"]["regions"]["left_arm"]["oracle"]["bones"]
    moving = set(k for k in B["bones_world"] if any(k.endswith("(%s)" % b) for b in ARM_BONES))
    grew = True
    while grew:
        more = set(k for k, v in B["bones_world"].items() if v.get("parent") in moving) - moving
        moving |= more
        grew = bool(more)
    shows = {"base": None, "applied_a": "a", "noop_a": "a", "applied_b": "b", "undo_b": "a", "undo_a": None,
             "redo_a": "a", "redo_b": "b", "returned": "b"}
    findings["arm_vs_oracle_deg"] = {}
    for s, p in shows.items():
        if s not in obs:
            continue
        o = obs[s]
        if p is None:
            need(all(close(o["rig_inputs"][n], B["rig_inputs"][n], 1e-6, 1e-6) for n in WRITTEN) and
                 all(close(bone(o["bones"], b)["orientation"], bone(B["bones"], b)["orientation"]) for b in ARM_BONES),
                 "%s: the evaluated arm is not the baseline" % s)
            continue
        oracle = poses[names[p]]
        need(all(close(o["rig_inputs"][n], key_at(o, n)[0][1], 1e-4, 1e-3) for n in WRITTEN),
             "%s: the rig inputs are not the keys at %d (not displayed)" % (s, t_chan))
        errs = [angle(bone(o["bones"], b)["orientation"], oracle[b]["local_orientation"]) for b in ARM_BONES]
        findings["arm_vs_oracle_deg"][s] = [round(e, 4) for e in errs]
        need(all(e <= 0.01 for e in errs), "%s: the arm is not %s (%s deg)" % (s, names[p], errs))
        unrelated = [k for k, v in B["bones"].items() if not any(k.endswith("(%s)" % b) for b in ARM_BONES)
                     and not (close(o["bones"][k]["position"], v["position"]) and
                              close(o["bones"][k]["orientation"], v["orientation"]))]
        world = [k for k, v in B["bones_world"].items() if k not in moving and not (
            close(o["bones_world"][k]["position"], v["position"]) and
            close(o["bones_world"][k]["orientation"], v["orientation"]))]
        need(not unrelated and not world, "%s: unrelated bones changed %s" % (s, (unrelated + world)[:6]))
        need(close(o["model"]["position"], B["model"]["position"]) and
             close(o["model"]["orientation"], B["model"]["orientation"]) and
             all(close(o["placement"][k], v) for k, v in B["placement"].items() if v is not None),
             "%s: placement or facing changed" % s)
    # Status (automatic verification) and history ownership.
    for s, key in (("applied_a", "applied_a"), ("noop_a", "noop"), ("applied_b", "applied_b")):
        if s not in obs:
            continue
        need(obs[s]["cpm"] and obs[s]["cpm"]["status"] == msgs[key], "%s status %r, expected %r" % (
            s, (obs[s]["cpm"] or {}).get("status"), msgs[key]))
    U = lambda s: obs[s]["undo"]  # noqa: E731
    history = (
        ("applied_a", lambda: U("applied_a")["undo_desc"] == label["a"] and not U("applied_a")["can_redo"],
         "Apply A is not the top entry"),
        ("noop_a", lambda: U("noop_a") == U("applied_a"), "the no-op changed the Undo history"),
        ("applied_b", lambda: U("applied_b")["undo_desc"] == label["b"] and not U("applied_b")["can_redo"],
         "Apply B is not the top entry"),
        ("undo_b", lambda: U("undo_b")["undo_desc"] == label["a"] and U("undo_b")["redo_desc"] == u"Redo " + label["b"],
         "Undo B did not reverse Apply B"),
        ("undo_a", lambda: U("undo_a")["undo_desc"] == B["undo"]["undo_desc"] and
         U("undo_a")["redo_desc"] == u"Redo " + label["a"], "Undo A did not reverse Apply A"),
        ("redo_a", lambda: U("redo_a")["undo_desc"] == label["a"] and U("redo_a")["redo_desc"] == u"Redo " + label["b"],
         "Redo did not restore Apply A"),
        ("redo_b", lambda: U("redo_b") == U("applied_b"), "Redo did not restore Apply B"),
    )
    for s, ok, what in history:
        if s in obs:
            need(ok(), what)
    findings["navigation_history"] = dict((s, U(s)) for s in ("away", "returned") if s in obs)
    return finish(q, problems, findings, steps)


def finish(q, problems, findings, steps=STEPS):
    verdict = {"steps": list(steps), "problems": problems, "findings": findings,
               "verdict": "MOTION EDITOR QUALIFICATION PASS" if not problems else "FAIL"}
    T.write_json(os.path.join(q, "evidence", "ME1_VERDICT.json"), verdict)
    print(json.dumps({"verdict": verdict["verdict"], "problems": problems}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
