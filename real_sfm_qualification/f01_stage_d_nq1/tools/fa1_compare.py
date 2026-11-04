# -*- coding: utf-8 -*-
"""F-01 FA-1 functional Apply experiment: offline verdict from the observations (Python 3, -I). Read-only.

usage: python -I fa1_compare.py <Q>\\nq1.json
Sequence (OBS-NN in <Q>\\observations; the refresh step exists only when <Q>\\evidence\\FA1_REFRESH.json exists):
  base, applied, [refreshed], away, returned, undo, redo, final_undo
Writes <Q>\\evidence\\FA1_VERDICT.json. A failure of automatic evaluation is never rescued by the refresh or by
navigation: each is reported as its own finding.
"""
from __future__ import print_function

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nq1_tool as T  # noqa: E402

WRITTEN = ("Hand_l.positionChannel", "Hand_l.orientationChannel", "Elbow_l.positionChannel")
OBSERVED = "Elbow_l.orientationChannel"
ARM_BONES = ("bip_UpperArm_l", "bip_lowerArm_l", "bip_hand_l")


def angle(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return math.degrees(2.0 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(a, b))) / (na * nb))))


def close(a, b, pos=1e-3, ang=1e-2):
    if a is None or b is None or len(a) != len(b):
        return False
    return angle(a, b) <= ang if len(a) == 4 else math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) <= pos


def keys(o, n):
    return o["channels"][n]["layers"]


def bone(rows, name):
    hits = [v for k, v in rows.items() if k.endswith("(%s)" % name)]
    return hits[0] if len(hits) == 1 else None


def main(argv):
    c = T.load(argv[1])
    q = T.p(c, "Q")
    fa = c["fa1"]
    t_doc, t_chan, away_ticks = c["destination"]["t_doc_ticks"], c["destination"]["t_chan_ticks"], fa["away_ticks"]
    t_write = fa.get("write_ticks", t_chan)   # Trial 2 writes at the observed channel clock
    refreshed = os.path.isfile(os.path.join(q, "evidence", "FA1_REFRESH.json"))
    steps = ["base", "applied"] + (["refreshed"] if refreshed else []) + ["away", "returned", "undo", "redo",
                                                                          "final_undo"]
    if fa.get("order"):   # FA-3 (Motion Editor): Undo/Redo while Apply is the top entry, navigation last
        steps = [x for x in fa["order"] if x != "refreshed" or refreshed]
    problems, findings = [], {}

    def need(ok, what):
        if not ok:
            problems.append(what)
        return bool(ok)
    obs = {}
    for i, s in enumerate(steps, 1):
        path = os.path.join(q, "observations", "OBS-%02d.json" % i)
        if not need(os.path.isfile(path), "%s missing (OBS-%02d)" % (s, i)):
            continue
        obs[s] = T.read_json(path)
        need(not obs[s].get("problems"), "%s observer problems %s" % (s, obs[s].get("problems")))
    extra = sorted(n for n in os.listdir(os.path.join(q, "observations")) if n.startswith("OBS-"))[len(steps):]
    need(not extra, "unexpected extra observations %s" % extra)
    if problems:
        return finish(q, problems, findings, steps)
    B, A = obs["base"], obs["applied"]
    # Context and history.
    need(len(set(o["pid"] for o in obs.values())) == 1, "the observations come from different SFM processes")
    need(all(os.path.normcase(o["document"]).endswith("nq1_destination.dmx") for o in obs.values()),
         "not the destination document")
    need(all(o["animation_set_id"] == B["animation_set_id"] and o["current_shot"] == c["destination"]["shot"] for o in obs.values()),
         "the destination Krystal instance changed")
    for s, o in obs.items():
        want = away_ticks if s == "away" else t_doc
        need(o["head_ticks"] == want, "%s playhead is %s, expected %s" % (s, o["head_ticks"], want))
    if fa.get("mode") is not None:
        modes = dict((s, (o.get("timeline_mode") or {}).get("value")) for s, o in obs.items())
        findings["timeline_modes"] = modes
        need(all(v == str(fa["mode"]) for v in modes.values()), "the timeline mode was not %s throughout: %s" % (
            fa["mode"], modes))
    clocks = dict((s, sorted(set(v["clock"] for v in o["rig_evaluated_at"].values()))) for s, o in obs.items())
    findings["clocks"] = clocks
    findings["conversion"] = dict((s, o["conversion"]) for s, o in obs.items())
    need(B["conversion"]["t_chan"] == t_chan, "baseline converted time is %s" % B["conversion"]["t_chan"])
    findings["baseline_clocks_differ"] = clocks["base"] != [t_chan]
    label = u"Apply Pose " + fa["pose"]
    need(A["undo"]["undo_desc"] == label and A["undo"]["can_undo"] and not A["undo"]["can_redo"],
         "the Apply is not the single top Undo entry: %s" % A["undo"])
    for s in [x for x in ("refreshed", "away", "returned") if x in obs]:
        if fa.get("navigation_history") == "record":   # Motion Editor: recorded, judged at Undo
            findings.setdefault("navigation_history", {})[s] = obs[s]["undo"]
            continue
        need(obs[s]["undo"] == A["undo"], "%s: the Undo history changed %s" % (s, obs[s]["undo"]))
    need(not B["undo"]["can_redo"], "the baseline already had a Redo entry")
    # Authored keys: one key at the converted time per written channel, neighbours and everything else unchanged.
    for n in WRITTEN:
        a, b = keys(A, n)[0], keys(B, n)[0]
        need(len(keys(A, n)) == 1 and len(a) == len(b) + 1 and [k for k in a if k[0] != t_write] == b
             and len([k for k in a if k[0] == t_write]) == 1, "%s: not exactly one key inserted at %d" % (n, t_write))
    need(keys(A, OBSERVED) == keys(B, OBSERVED), "the elbow orientation channel changed")
    for s, o in obs.items():
        if s in ("undo", "final_undo"):
            continue
        need(o["other_channels"] == B["other_channels"], "%s: unrelated authored channels changed" % s)
        need(all(keys(o, n) == keys(A, n) for n in WRITTEN) if s != "base" else True, "%s: the written keys changed" % s)
    # Evaluation states.
    record = None
    for path in (os.path.join(c["seed"]["poses"]["source_dir"], n) for n in c["seed"]["poses"]["files"]):
        r = T.read_json(path)
        if r["name"] == fa["pose"]:
            record = r
    oracle = record["pose"]["regions"]["left_arm"]["oracle"]["bones"]
    written_value = dict((n, [k for k in keys(A, n)[0] if k[0] == t_write][0][1]) for n in WRITTEN)
    findings["write_ticks"] = t_write

    # World space: the arm bones and every descendant (fingers, twist) legitimately move with the arm; their local
    # transforms are checked above. Every other bone's world transform must be unchanged.
    moving = set(k for k in B["bones_world"] if any(k.endswith("(%s)" % b) for b in ARM_BONES))
    grew = True
    while grew:
        more = set(k for k, v in B["bones_world"].items() if v.get("parent") in moving) - moving
        moving |= more
        grew = bool(more)
    findings["world_moves_with_arm"] = sorted(moving)

    def pose_state(o):
        rig = all(close(o["rig_inputs"][n], written_value[n], 1e-4, 1e-3) for n in WRITTEN)
        local = all(bone(o["bones"], b) is not None and angle(bone(o["bones"], b)["orientation"],
                                                               oracle[b]["local_orientation"]) <= 0.01
                    for b in ARM_BONES)
        stale = all(close(o["rig_inputs"][n], B["rig_inputs"][n], 1e-6, 1e-6) for n in WRITTEN)
        unrelated = [k for k, v in B["bones"].items() if not any(k.endswith("(%s)" % b) for b in ARM_BONES)
                     and not (close(o["bones"][k]["position"], v["position"]) and
                              close(o["bones"][k]["orientation"], v["orientation"]))]
        world_unrelated = [k for k, v in B["bones_world"].items() if k not in moving
                           and not (close(o["bones_world"][k]["position"], v["position"]) and
                                    close(o["bones_world"][k]["orientation"], v["orientation"]))]
        place = all(close(o["placement"][k], v) for k, v in B["placement"].items() if v is not None) and \
            close(o["model"]["position"], B["model"]["position"]) and \
            close(o["model"]["orientation"], B["model"]["orientation"])
        ev = o["rig_evaluated_at"]
        return {"pose": rig and local, "rig_equals_written_keys": rig, "arm_local_matches_oracle": local,
                "stale_equals_baseline": stale, "rig_at_converted": all(v["at_converted"] for v in ev.values()),
                "rig_at_clock": all(v["at_clock"] for v in ev.values()), "unrelated_bones_changed": unrelated[:10],
                "unrelated_world_changed": world_unrelated[:10], "placement_and_facing_preserved": place}
    states = dict((s, pose_state(o)) for s, o in obs.items() if s != "away")
    findings["states"] = states
    findings["away"] = {"rig_at_converted": all(v["at_converted"] for v in obs["away"]["rig_evaluated_at"].values()),
                        "clock": clocks["away"]}
    for s in ("applied", "returned", "redo") + (("refreshed",) if refreshed else ()):
        need(not states[s]["unrelated_bones_changed"] and not states[s]["unrelated_world_changed"]
             and states[s]["placement_and_facing_preserved"] if states[s]["pose"] else True,
             "%s: unrelated skeleton, placement or facing changed" % s)
    arm_world = lambda o: [bone(o["bones_world"], b) for b in ARM_BONES]  # noqa: E731
    findings["arm_world_consistent_returned_vs_redo"] = all(
        close(x["position"], y["position"]) and close(x["orientation"], y["orientation"])
        for x, y in zip(arm_world(obs["returned"]), arm_world(obs["redo"]))) if "redo" in obs else None
    # Undo / Redo: exact keys and evaluated states, only where SFM's history shows Apply is the action reversed.
    findings["history_verification"] = "not performed"
    if "undo" in obs:
        before_undo = obs[steps[steps.index("undo") - 1]]
        findings["history_verification"] = ("confirmed" if before_undo["undo"]["undo_desc"] == label
                                            else "blocked: %r above Apply" % before_undo["undo"]["undo_desc"])
        need(findings["history_verification"] == "confirmed", "Undo was attempted while %s" %
             findings["history_verification"])
        U = obs["undo"]
        findings["undo_exact"] = (all(keys(U, n) == keys(B, n) for n in WRITTEN) and
                                  U["other_channels"] == B["other_channels"] and states["undo"]["stale_equals_baseline"]
                                  and U["undo"]["undo_desc"] == B["undo"]["undo_desc"] and U["undo"]["can_redo"]
                                  and U["undo"]["redo_desc"] == u"Redo " + label)
    if "redo" in obs:
        R = obs["redo"]
        findings["redo_exact"] = (all(keys(R, n) == keys(A, n) for n in WRITTEN) and R["undo"] == A["undo"] and
                                  states["redo"]["pose"])
    if "final_undo" in obs:
        F = obs["final_undo"]
        findings["final_undo_exact"] = (all(keys(F, n) == keys(B, n) for n in WRITTEN) and
                                        F["other_channels"] == B["other_channels"] and
                                        states["final_undo"]["stale_equals_baseline"])
    # Classification (each finding stands on its own; nothing is rescued).
    automatic = states["applied"]["pose"]
    after_refresh = states["refreshed"]["pose"] if refreshed else None
    returned = states["returned"]["pose"]
    findings["automatic_evaluation"] = automatic
    findings["after_single_refresh"] = after_refresh
    findings["after_navigation"] = returned
    undo_ok = all(findings[k] for k in ("undo_exact", "redo_exact", "final_undo_exact") if k in findings) and \
        findings["history_verification"] == "confirmed"
    if problems:
        result = "FAIL: see problems"
    elif automatic and returned and undo_ok and findings["arm_world_consistent_returned_vs_redo"] is not False:
        result = "FUNCTIONAL PASS"
    elif not returned and states["returned"]["rig_at_clock"] and not states["returned"]["rig_at_converted"]:
        result = "PLACEMENT DEFECT: after navigation SFM evaluates at the channel clock, not at the inserted key " \
                 "(Trial 2 eligible)"
    elif returned and not automatic:
        result = "AUTOMATIC RE-EVALUATION DEFECT: correct after navigation%s, not automatically (placement correct; automatic evaluation unresolved)" % (
            "" if after_refresh is None else ("; after one refresh: %s" % ("correct" if after_refresh else "not correct")))
    else:
        result = "FAIL: automatic=%s refresh=%s navigation=%s undo/redo=%s" % (automatic, after_refresh, returned,
                                                                              undo_ok)
    findings["result"] = result
    return finish(q, problems, findings, steps)


def finish(q, problems, findings, steps):
    verdict = {"steps": steps, "problems": problems, "findings": findings,
               "verdict": findings.get("result", "FAIL: see problems") if not problems else "FAIL: see problems"}
    T.write_json(os.path.join(q, "evidence", "FA1_VERDICT.json"), verdict)
    print(json.dumps({"verdict": verdict["verdict"], "problems": problems}, indent=1))
    return 0 if verdict["verdict"] == "FUNCTIONAL PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
