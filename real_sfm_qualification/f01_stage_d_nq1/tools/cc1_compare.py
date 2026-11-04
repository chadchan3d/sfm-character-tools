# -*- coding: utf-8 -*-
"""F-01 Stage D capture-consistency case (CC-1): offline verdict (Python 3, -I). Read-only.

usage: python -I cc1_compare.py <Q>\\nq1.json
Sequence (OBS-01 .. OBS-08 in <Q>\\observations, all in timeline mode 2):
  src_base      shot10, Apply frame (0.4167 s)           src_applied  after Apply Pose B (non-flat interval created)
  src_interp    shot10, Save frame (0.4583 s)            src_saved    after Save New "CC1 Pose C" (same frame)
  dst_base      shot15, 0.2083 s                         dst_applied  after Apply Pose C (automatic)
  dst_away      shot15, 0.2500 s                         dst_returned back at 0.2083 s
Requires: a meaningfully non-flat source pose (configured minimum angle from both Pose B and the held pose); Save
read-only and the record's oracle equal to the observed source skeleton; Apply C reproducing that skeleton at the
destination automatically and after navigation; unrelated animation, identity and placement protected.
Writes <Q>\\evidence\\CC1_VERDICT.json.
"""
from __future__ import print_function

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nq1_tool as T  # noqa: E402
from fa1_compare import ARM_BONES, OBSERVED, WRITTEN, angle, bone, close, keys  # noqa: E402

STEPS = ("src_base", "src_applied", "src_interp", "src_saved", "dst_base", "dst_applied", "dst_away", "dst_returned")


def main(argv):
    c = T.load(argv[1])
    q = T.p(c, "Q")
    cc = c["cc1"]
    src, dst = cc["source"], cc["destination"]
    problems, findings = [], {}

    def need(ok, what):
        if not ok:
            problems.append(what)
        return bool(ok)
    obs = {}
    for i, s in enumerate(STEPS, 1):
        path = os.path.join(q, "observations", "OBS-%02d.json" % i)
        if need(os.path.isfile(path), "%s missing (OBS-%02d)" % (s, i)):
            obs[s] = T.read_json(path)
            need(not obs[s].get("problems"), "%s observer problems %s" % (s, obs[s].get("problems")))
    extra = sorted(n for n in os.listdir(os.path.join(q, "observations")) if n.startswith("OBS-"))[len(STEPS):]
    need(not extra, "unexpected extra observations %s" % extra)
    if problems:
        return finish(q, problems, findings)
    SB, SA, SI, SS, DB, DA, DW, DR = (obs[s] for s in STEPS)
    # Context: one process, the source document, mode 2, the intended shots, instances, playheads and ticks.
    need(len(set(o["pid"] for o in obs.values())) == 1, "the observations come from different SFM processes")
    need(all(os.path.normcase(o["document"]).endswith("nq1_source.dmx") for o in obs.values()), "not NQ1_SOURCE.dmx")
    modes = dict((s, (o.get("timeline_mode") or {}).get("value")) for s, o in obs.items())
    findings["timeline_modes"] = modes
    need(all(v == "2" for v in modes.values()), "not Motion Editor (2) throughout: %s" % modes)
    plan = {"src_base": (src, src["t_doc_apply"], src["t_chan_apply"]), "src_applied": (src, src["t_doc_apply"],
            src["t_chan_apply"]), "src_interp": (src, src["t_doc_save"], src["t_chan_save"]),
            "src_saved": (src, src["t_doc_save"], src["t_chan_save"]), "dst_base": (dst, dst["t_doc"], dst["t_chan"]),
            "dst_applied": (dst, dst["t_doc"], dst["t_chan"]), "dst_away": (dst, dst["away_ticks"], None),
            "dst_returned": (dst, dst["t_doc"], dst["t_chan"])}
    clocks = dict((s, sorted(set(v["clock"] for v in o["rig_evaluated_at"].values()))) for s, o in obs.items())
    findings["clocks"] = clocks
    for s, (side, t_doc, t_chan) in plan.items():
        o = obs[s]
        need(o["current_shot"] == side["shot"], "%s: shot %s, expected %s" % (s, o["current_shot"], side["shot"]))
        need(o["head_ticks"] == t_doc, "%s: playhead %s, expected %s" % (s, o["head_ticks"], t_doc))
        if t_chan is not None:
            need(o["conversion"]["t_chan"] == t_chan and clocks[s] == [t_chan],
                 "%s: mapped tick %s / clock %s, expected %d" % (s, o["conversion"]["t_chan"], clocks[s], t_chan))
    need(len(set(o["animation_set_id"] for o in (SB, SA, SI, SS))) == 1, "the source Krystal instance changed")
    need(len(set(o["animation_set_id"] for o in (DB, DA, DW, DR))) == 1, "the destination Krystal instance changed")
    need(SB["animation_set_id"] != DB["animation_set_id"], "source and destination are the same instance")
    ka = lambda o, n, t: [k for k in keys(o, n)[0] if k[0] == t]  # noqa: E731
    # Source: Apply B inserts one key per channel at the Apply frame; nothing else changes.
    t_a = src["t_chan_apply"]
    for n in WRITTEN:
        a, b = keys(SA, n)[0], keys(SB, n)[0]
        need(len(keys(SA, n)) == 1 and len(a) == len(b) + 1 and [k for k in a if k[0] != t_a] == b
             and len(ka(SA, n, t_a)) == 1, "source Apply B: %s is not one key inserted at %d" % (n, t_a))
    need(keys(SA, OBSERVED) == keys(SB, OBSERVED), "source Apply B changed the elbow orientation channel")
    need(all(keys(o, n) == keys(SA, n) for o in (SI, SS) for n in WRITTEN + (OBSERVED,)),
         "the source keys changed after Apply B (navigation or Save)")
    for o, s in ((SA, "src_applied"), (SI, "src_interp"), (SS, "src_saved")):
        need(o["other_channels"] == SB["other_channels"], "%s: unrelated authored channels changed" % s)
    msgs = cc["status"]
    need((SA["cpm"] or {}).get("status") == msgs["applied_b"], "Apply B status %r" % (SA["cpm"] or {}).get("status"))
    need(all(close(SA["rig_inputs"][n], ka(SA, n, t_a)[0][1], 1e-4, 1e-3) for n in WRITTEN),
         "after Apply B the rig is not the new keys (not displayed)")
    # Poses: B (seeded) and C (saved in this run).
    oracle_b = load_record(c, q, cc["pose_b"], obs)["pose"]["regions"]["left_arm"]["oracle"]["bones"]
    rec_c = load_record(c, q, cc["pose_c"], obs)
    need(rec_c is not None, "the saved %s record was not found" % cc["pose_c"])
    if rec_c is None:
        return finish(q, problems, findings)
    oracle_c = rec_c["pose"]["regions"]["left_arm"]["oracle"]["bones"]
    arm = lambda o: dict((b, bone(o["bones"], b)["orientation"]) for b in ARM_BONES)  # noqa: E731
    errs = lambda o, ref: [round(angle(arm(o)[b], ref[b]), 4) for b in ARM_BONES]  # noqa: E731
    need(all(e <= 0.01 for e in errs(SA, dict((b, oracle_b[b]["local_orientation"]) for b in ARM_BONES))),
         "after Apply B the source arm is not Pose B")
    # Non-flat: the interpolated source pose differs meaningfully from Pose B and from the held pose.
    min_deg = cc["meaningful_deg"]
    from_b = errs(SI, dict((b, oracle_b[b]["local_orientation"]) for b in ARM_BONES))
    from_held = errs(SI, arm(SB))
    findings["source_interp_arm_vs_pose_b_deg"], findings["source_interp_arm_vs_held_deg"] = from_b, from_held
    findings["source_interp_rig_vs_b_and_held"] = dict(
        (n, [round(angle(SI["rig_inputs"][n], SA["rig_inputs"][n]) if len(SA["rig_inputs"][n]) == 4 else
                   sum((x - y) ** 2 for x, y in zip(SI["rig_inputs"][n], SA["rig_inputs"][n])) ** 0.5, 4),
             round(angle(SI["rig_inputs"][n], SB["rig_inputs"][n]) if len(SB["rig_inputs"][n]) == 4 else
                   sum((x - y) ** 2 for x, y in zip(SI["rig_inputs"][n], SB["rig_inputs"][n])) ** 0.5, 4)])
        for n in WRITTEN)
    need(max(from_b) >= min_deg and max(from_held) >= min_deg,
         "INSUFFICIENTLY NON-FLAT: the source pose is within %.2f deg of Pose B (%s) or of the held pose (%s)" % (
             min_deg, from_b, from_held))
    need(all(not close(SI["rig_inputs"][n], SA["rig_inputs"][n], 1e-4, 1e-3) and
             not close(SI["rig_inputs"][n], SB["rig_inputs"][n], 1e-4, 1e-3) for n in WRITTEN),
         "a written rig channel does not differ from both Pose B and the held pose")
    need(all(v["at_converted"] for v in SI["rig_evaluated_at"].values()),
         "the source rig is not the log value at the Save frame")
    # Save: read-only, the record describes the observed source skeleton at the Save frame.
    need(SS["undo"] == SI["undo"], "Save changed the Undo history")
    need((SS["cpm"] or {}).get("status") == msgs["saved_c"], "Save status %r" % (SS["cpm"] or {}).get("status"))
    need(rec_c["pose"]["source"]["shot_name"] == src["shot"] and
         rec_c["pose"]["source"]["t_doc_ticks"] == src["t_doc_save"], "the record's source is %s" % rec_c["pose"]["source"])
    rec_vs_obs = errs(SI, dict((b, oracle_c[b]["local_orientation"]) for b in ARM_BONES))
    findings["record_c_oracle_vs_observed_source_deg"] = rec_vs_obs
    need(all(e <= 0.01 for e in rec_vs_obs), "the saved record does not match the observed source skeleton %s" % rec_vs_obs)
    # Destination: Apply C inserts at the mapped tick and reproduces the observed source arm automatically.
    t_d = dst["t_chan"]
    for n in WRITTEN:
        a, b = keys(DA, n)[0], keys(DB, n)[0]
        need(len(keys(DA, n)) == 1 and len(a) == len(b) + 1 and [k for k in a if k[0] != t_d] == b
             and len(ka(DA, n, t_d)) == 1, "destination Apply C: %s is not one key inserted at %d" % (n, t_d))
    need(keys(DA, OBSERVED) == keys(DB, OBSERVED), "destination Apply C changed the elbow orientation channel")
    need(all(keys(o, n) == keys(DA, n) for o in (DW, DR) for n in WRITTEN), "the destination keys changed after Apply")
    for o, s in ((DA, "dst_applied"), (DW, "dst_away"), (DR, "dst_returned")):
        need(o["other_channels"] == DB["other_channels"], "%s: unrelated authored channels changed" % s)
    need((DA["cpm"] or {}).get("status") == msgs["applied_c"], "Apply C status %r" % (DA["cpm"] or {}).get("status"))
    need(DA["undo"]["undo_desc"] == u"Apply Pose " + cc["pose_c"], "Apply C is not the top Undo entry")
    moving = descendants(DB)
    for s, o in (("dst_applied", DA), ("dst_returned", DR)):
        need(all(close(o["rig_inputs"][n], ka(o, n, t_d)[0][1], 1e-4, 1e-3) for n in WRITTEN),
             "%s: the rig is not the keys at %d (not displayed)" % (s, t_d))
        vs_rec = errs(o, dict((b, oracle_c[b]["local_orientation"]) for b in ARM_BONES))
        vs_src = errs(o, arm(SI))
        findings["%s_arm_vs_record_c_deg" % s], findings["%s_arm_vs_observed_source_deg" % s] = vs_rec, vs_src
        need(all(e <= 0.01 for e in vs_rec) and all(e <= 0.01 for e in vs_src),
             "%s: the destination arm does not reproduce Pose C (record %s, source %s)" % (s, vs_rec, vs_src))
        unrelated = [k for k, v in DB["bones"].items() if not any(k.endswith("(%s)" % b) for b in ARM_BONES)
                     and not (close(o["bones"][k]["position"], v["position"]) and
                              close(o["bones"][k]["orientation"], v["orientation"]))]
        world = [k for k, v in DB["bones_world"].items() if k not in moving and not (
            close(o["bones_world"][k]["position"], v["position"]) and
            close(o["bones_world"][k]["orientation"], v["orientation"]))]
        need(not unrelated and not world, "%s: unrelated bones changed %s" % (s, (unrelated + world)[:6]))
        need(close(o["model"]["position"], DB["model"]["position"]) and
             close(o["model"]["orientation"], DB["model"]["orientation"]) and
             all(close(o["placement"][k], v) for k, v in DB["placement"].items() if v is not None),
             "%s: placement or facing changed" % s)
    findings["destination_history"] = {"applied": DA["undo"], "away": DW["undo"], "returned": DR["undo"]}
    return finish(q, problems, findings)


def descendants(base):
    moving = set(k for k in base["bones_world"] if any(k.endswith("(%s)" % b) for b in ARM_BONES))
    grew = True
    while grew:
        more = set(k for k, v in base["bones_world"].items() if v.get("parent") in moving) - moving
        moving |= more
        grew = bool(more)
    return moving


def load_record(c, q, name, obs):
    """A pose record by name: the seeded source folder, the library during the run, or <Q>\\evidence\\library_poses."""
    for rel in sorted(set(r for o in obs.values() for r in (o.get("pose_files") or {}))):
        char, _, fname = rel.split("/")
        for path in (os.path.join(c["seed"]["poses"]["source_dir"], fname),
                     os.path.join(T.p(c, "LIBRARY"), "Characters", char, "Poses", fname),
                     os.path.join(q, "evidence", "library_poses", char, fname)):
            if os.path.isfile(path):
                r = T.read_json(path)
                if r.get("name") == name:
                    return r
    return None


def finish(q, problems, findings):
    verdict = {"steps": list(STEPS), "problems": problems, "findings": findings,
               "verdict": "CC-1 CAPTURE CONSISTENCY PASS" if not problems else "FAIL"}
    T.write_json(os.path.join(q, "evidence", "CC1_VERDICT.json"), verdict)
    print(json.dumps({"verdict": verdict["verdict"], "problems": problems}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
