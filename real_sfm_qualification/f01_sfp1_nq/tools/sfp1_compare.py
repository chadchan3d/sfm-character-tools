# -*- coding: utf-8 -*-
"""F-01 SFP-1 Selected parts native qualification: the comparator. Python 3 (-I), offline, read-only over the run
folder; writes Q/evidence/SFP1_VERDICT.json and SFP1_VERDICT.md (exclusive create).

Turns each Expected result of PROCEDURE.md into a machine check over the S0 observations (and their .sfp1.json
sidecars), the restored Poses records, the UI captures and the CPM log. It reuses the full-body S3 comparator's
geometry, validation and log parsing (f01_full_body_s3/tools/s3_compare.py, S0 analysis validate) unchanged.
Tolerances are R3's (PROD_SCOPE_TOLERANCES): 0.01 degrees and 0.001 units; the visible-difference threshold is 5
degrees. CPM's log operations are identified by content, not by position.

usage: python -I sfp1_compare.py SFP1.json
"""
from __future__ import print_function

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_full_body_s3", "tools"))
import s3_compare as K  # noqa: E402  (also puts the S0 analysis on the path)

angle, dist, read_json, parse_logs, apply_operations_s3 = K.angle, K.dist, K.read_json, K.parse_logs, \
    K.apply_operations
s0_hash, validate = K.s0_hash, K.s0_analyze.validate

TOL = {"angle_degrees": 0.01, "position": 0.001, "effective_angle_degrees": 0.001}
VISIBLE = 5.0
GRIP, POINT, LEGACY = u"SFP1 Grip", u"SFP1 Point", u"NQ1 Pose A"
FINGERS = sorted(u"bip_%s_%d_l" % (f, i) for f in (u"index", u"middle", u"ring", u"pinky", u"thumb")
                 for i in range(3))
FINGER_CHANNELS = set(b + s for b in FINGERS for s in (u"_o", u"_p"))
LEGACY_WRITTEN = set(K.LEGACY_WRITTEN)
A = ["A%d" % i for i in range(1, 8)]
B = ["B%d" % i for i in range(1, 17)]
C = ["C1", "C2", "C3"]
LABELS = dict(zip(A + B + C, ["S0-%02d" % i for i in range(1, 27)]))
PERF = dict(K.PERF)
DOCS = {"A": "sfp1_source.dmx", "B": "sfp1_destination.dmx", "C": "sfp1_prop.dmx"}


class Run(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.timing, self.findings = [], [], []
        self.ids = read_json(os.path.join(self.q, "staged", "IDENTITIES.json"))
        self.obs, self.side = {}, {}
        for step, label in LABELS.items():
            path = os.path.join(self.q, "observations", label + ".json")
            side = os.path.join(self.q, "observations", label + ".sfp1.json")
            if os.path.isfile(path):
                self.obs[step] = read_json(path)
            if os.path.isfile(side):
                self.side[step] = read_json(side)
        self.records = {}
        for path in glob.glob(os.path.join(self.q, "evidence", "library_poses", c["character_dir"], "*.json")):
            r = read_json(path)
            self.records.setdefault(r.get("name"), []).append(r)

    def check(self, cid, ok, detail=None):
        self.checks.append({"id": cid, "pass": bool(ok), "detail": detail})
        return ok

    def record(self, name):
        rows = self.records.get(name) or []
        return rows[0] if len(rows) == 1 else None


def channels(o):
    return dict((ch["id"]["name"], ch) for ch in o.get("channels") or [] if ch.get("id"))


def sig(ch):
    return ([(l.get("key_count"), l.get("keys_sha256")) for l in ch.get("layers") or []], ch.get("value_at_mapped"))


def changed(o1, o2):
    a, b = channels(o1), channels(o2)
    return sorted(n for n in set(a) | set(b) if n not in a or n not in b or sig(a[n]) != sig(b[n]))


def doc_unchanged(o1, o2):
    return (o1["readonly"]["digest_after"]["sha256"] == o2["readonly"]["digest_before"]["sha256"] and
            o1["session_after"]["undo"] == o2["session_before"]["undo"])


def skeleton_moved(o1, o2, exclude=()):
    out = []
    for name, b in sorted(o1["bones"].items()):
        if name in exclude:
            continue
        c = o2["bones"].get(name)
        if c is None:
            out.append("%s missing" % name)
            continue
        for kind in ("world", "local"):
            if dist(b[kind + "_position"], c[kind + "_position"]) > TOL["position"] or \
                    angle(b[kind + "_orientation"], c[kind + "_orientation"]) > TOL["angle_degrees"]:
                out.append("%s %s" % (name, kind))
        if b.get("scale") != c.get("scale"):
            out.append("%s scale" % name)
    return out


def controls_changed(o1, o2, exclude=()):
    def rows(o):
        return dict((c["id"]["name"], c.get("attributes")) for c in o.get("controls") or [])
    a, b = rows(o1), rows(o2)
    return sorted(n for n in set(a) | set(b) if n not in exclude and a.get(n) != b.get(n))


def placement_moved(o1, o2):
    out = []
    for key in ("world_position", "world_orientation", "local_position", "local_orientation"):
        a, b = o1["model"]["state"].get(key), o2["model"]["state"].get(key)
        if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b) or \
                (len(a) == 3 and dist(a, b) > TOL["position"]) or (len(a) == 4 and angle(a, b) > TOL["angle_degrees"]):
            out.append("model %s" % key)
    for name, h in sorted((o1.get("rig") or {}).get("handles", {}).items()):
        g = ((o2.get("rig") or {}).get("handles") or {}).get(name)
        if g is None or dist(h["world_position"], g["world_position"]) > TOL["position"] or \
                angle(h["world_orientation"], g["world_orientation"]) > TOL["angle_degrees"]:
            out.append("rig handle %s" % name)
    return out


def finger_error(o, record):
    """Largest difference (degrees) between the observed finger local orientations and the record's independently
    observed articulation (oracle)."""
    orc = record["pose"]["oracle"]["bones"]
    return max(angle(o["bones"][b]["local_orientation"], orc[b]["local_orientation"]) for b in FINGERS)


def finger_spread(o1, o2):
    return max(angle(o1["bones"][b]["local_orientation"], o2["bones"][b]["local_orientation"]) for b in FINGERS)


def undo_desc(o):
    return o["session_after"]["undo"].get("undo_desc")


def ops_of(logs, pid):
    """Apply Pose operations of one SFM process with scoped and legacy marks (identified by content)."""
    ops = apply_operations_s3(logs, pid)
    for op in ops:
        text = op["text"]
        op["scoped_p6"] = any(t.startswith("PROD_POSE_SCOPE-P6 ") for t in text)
        op["scoped_p7"] = any(t.startswith("PROD_POSE_SCOPE-P7-verified") for t in text)
        op["legacy_p6"] = any(t.startswith("PROD_POSE_P6 ") for t in text)
        op["legacy_p7"] = any(t.startswith("PROD_POSE_P7-verified") for t in text)
        op["abort"] = any(t.startswith("PROD_POSE_SCOPE-abort-verified") for t in text)
        op["owned"] = any(t.startswith("PROD_POSE_SCOPE-P6 ") and '"owned": true' in t for t in text)
        p1 = [t for t in text if t.startswith("PROD_POSE_SCOPE-P1 ")]
        try:
            op["p1"] = json.loads(p1[0].split(" ", 1)[1]) if p1 else None
        except ValueError:
            op["p1"] = None
        for key, marks in (("p1", ("PROD_POSE_SCOPE-P1 ",)), ("p6", ("PROD_POSE_SCOPE-P6 ",)),
                           ("p7", ("PROD_POSE_SCOPE-P7-verified",))):
            hits = [r["ms"] for r in op["lines"] if any(r["text"].startswith(m) for m in marks)]
            if hits:
                op[key + "_ms"] = hits[0]
    return ops


def scoped_timing(op, step):
    def gap(a, b):
        return None if op.get(a) is None or op.get(b) is None else op[b] - op[a]
    return {"step": step, "id": op["id"], "preflight_ms": gap("begin", "p1_ms"), "transaction_ms": gap("p1_ms", "p6_ms"),
            "blocking_ms": gap("begin", "p6_ms"), "deferred_verify_ms": gap("p6_ms", "p7_ms"),
            "whole_ms": gap("begin", "p7_ms")}


def evaluate(R):
    o, chk = R.obs, R.check
    prop = any(s in o for s in C)
    steps = A + B + (C if prop else [])
    for step in steps:
        if not chk("observed.%s" % step, step in o and step in R.side, LABELS[step]):
            continue
        problems = validate(o[step]) + list(o[step].get("problems") or []) + list(R.side[step]["mismatch"])
        chk("valid.%s" % step, not problems and o[step]["readonly"]["unchanged"], problems[:5])
        chk("cpm.%s" % step, (o[step].get("cpm_loaded") or {}).get("build_sha256") == R.ids["qualification_cpm_sha256"],
            o[step].get("cpm_loaded"))
    if any(s not in o or s not in R.side for s in steps):
        chk("complete", False, "missing observations: %s" % sorted(s for s in steps if s not in o))
        return
    pids = dict((p, set(o[s]["pid"] for s in group)) for p, group in (("A", A), ("B", B), ("C", C if prop else [])))
    chk("process.restart_between_save_and_apply", len(pids["A"]) == 1 and len(pids["B"]) == 1 and
        pids["A"] != pids["B"] and (not prop or (len(pids["C"]) == 1 and pids["C"] != pids["B"])),
        dict((k, sorted(v)) for k, v in pids.items()))
    chk("process.sessions", all(o[s]["document"].lower().endswith(DOCS[s[0]]) for s in steps),
        dict((s, o[s]["document"]) for s in ("A1", "B1") + (("C1",) if prop else ())))

    # Save New, Update Pose and the library (records read back from the run's Poses folder after restore)
    grip, point, legacy = R.record(GRIP), R.record(POINT), R.record(LEGACY)
    chk("library.one_record_each", grip is not None and point is not None and legacy is not None,
        dict((k, len(v)) for k, v in R.records.items()))
    if grip is None or point is None:
        return
    la, lb = (os.path.join(R.q, "evidence", "library_%s.json" % t) for t in ("A", "B"))
    chk("library.records_unchanged_by_the_apply_processes", os.path.isfile(la) and os.path.isfile(lb) and
        read_json(la)["files"] == read_json(lb)["files"])
    for name, rec in ((u"grip", grip), (u"point", point)):
        pose = rec["pose"]
        sc = pose.get("scope") or {}
        chk("save.%s_is_version_3_selected_parts_of_the_15_left_fingers" % name,
            pose.get("version") == 3 and sc.get("kind") == u"selected_parts" and sorted(sc.get("posed") or []) ==
            FINGERS and sc.get("carried") == [] and pose.get("engine") == {u"rule": u"direct_fk_v1", u"revision": 1,
                                                                            u"carried_rule": None},
            {"version": pose.get("version"), "kind": sc.get("kind"), "posed": sc.get("posed"),
             "engine": pose.get("engine")})
    chk("save.grip_captures_the_visible_fingers", finger_error(o["A2"], grip) <= TOL["angle_degrees"],
        finger_error(o["A2"], grip))
    chk("save.grip_differs_visibly_from_the_source_baseline", finger_spread(o["A1"], o["A2"]) >= VISIBLE,
        finger_spread(o["A1"], o["A2"]))
    for a, b in (("A2", "A3"), ("A4", "A5"), ("A6", "A7")):
        chk("save.%s_to_%s_writes_nothing_to_the_scene" % (a, b), doc_unchanged(o[a], o[b]))
    chk("update.point_holds_the_updated_articulation", finger_error(o["A6"], point) <= TOL["angle_degrees"],
        finger_error(o["A6"], point))
    chk("update.updated_articulation_differs_visibly_from_the_first", finger_spread(o["A4"], o["A6"]) >= VISIBLE,
        finger_spread(o["A4"], o["A6"]))
    chk("update.in_place", len([n for n in read_json(lb)["files"] if n.startswith(POINT + u"--") and
                                n.endswith(u".json")]) == 1 if os.path.isfile(lb) else False)

    # Process B: a visibly different destination (an Apply that moves nothing proves nothing)
    b1 = o["B1"]
    chk("distinct.destination_fingers_differ_from_the_grip", finger_error(b1, grip) >= VISIBLE, finger_error(b1, grip))
    hand = angle(b1["bones"][u"bip_hand_l"]["world_orientation"], o["A2"]["bones"][u"bip_hand_l"]["world_orientation"])
    chk("distinct.destination_wrist_differs_from_the_source", hand >= VISIBLE, hand)

    def applied(label, before, after, rec, desc):
        ch = changed(before, after)
        chk("%s.one_owned_undo_entry" % label, undo_desc(after) == u"Apply Pose " + desc and
            after["session_after"]["undo"].get("can_undo") is True, after["session_after"]["undo"])
        chk("%s.fingers_take_the_saved_articulation" % label, finger_error(after, rec) <= TOL["angle_degrees"],
            finger_error(after, rec))
        chk("%s.finger_offsets_are_the_destinations_own" % label, all(
            dist(after["bones"][b]["local_position"], before["bones"][b]["local_position"]) <= TOL["position"]
            for b in FINGERS))
        chk("%s.only_finger_channels_changed" % label, ch and set(ch) <= FINGER_CHANNELS, ch[:8])
        chk("%s.wrist_arm_body_and_face_unchanged" % label, not skeleton_moved(before, after, FINGERS),
            skeleton_moved(before, after, FINGERS)[:8])
        chk("%s.facial_gaze_and_other_controls_unchanged" % label, not controls_changed(before, after, FINGERS),
            controls_changed(before, after, FINGERS)[:8])
        chk("%s.model_and_rig_handles_unchanged" % label, not placement_moved(before, after),
            placement_moved(before, after)[:8])
        chk("%s.unrelated_animation_unchanged" % label, R.side[before_step(before)]["outside"]["sha256"] ==
            R.side[before_step(after)]["outside"]["sha256"])
        chk("%s.keys_at_the_mapped_tick" % label, all(channels(after)[n]["layers"][0].get("key_at_mapped") is not None
                                                       for n in ch if n in channels(after)))
        return ch

    def before_step(obs):
        return [s for s in steps if o[s] is obs][0]

    applied("apply_grip", b1, o["B2"], grip, GRIP)
    chk("undo.restores_the_destination_baseline", not changed(b1, o["B3"]) and not skeleton_moved(b1, o["B3"]) and
        undo_desc(o["B3"]) == undo_desc(b1) and o["B3"]["session_after"]["undo"].get("can_redo") is True,
        changed(b1, o["B3"])[:8])
    chk("redo.restores_the_applied_grip", not changed(o["B2"], o["B4"]) and not skeleton_moved(o["B2"], o["B4"]) and
        undo_desc(o["B4"]) == u"Apply Pose " + GRIP, changed(o["B2"], o["B4"])[:8])
    chk("repeat.true_noop", doc_unchanged(o["B4"], o["B5"]))
    ch = applied("apply_point", o["B5"], o["B6"], point, POINT)
    chk("apply_point.existing_keys_updated_in_place", all(
        channels(o["B6"])[n]["layers"][0]["key_count"] == channels(o["B5"])[n]["layers"][0]["key_count"]
        for n in ch if n in channels(o["B5"])))
    chk("abort.verified_nothing_changed", doc_unchanged(o["B6"], o["B7"]))
    chk("refusal.clip_editor_writes_nothing", doc_unchanged(o["B8"], o["B9"]))

    # Sequential application on qualified routes: the legacy left arm (version 1), then the finger grip
    chk("seq.destination_fingers_differ_from_the_grip", finger_error(o["B10"], grip) >= VISIBLE,
        finger_error(o["B10"], grip))
    arm = changed(o["B10"], o["B11"])
    chk("seq.legacy_left_arm_applied", arm and set(arm) <= LEGACY_WRITTEN and
        undo_desc(o["B11"]) == u"Apply Pose " + LEGACY, arm)
    chk("seq.legacy_arm_moved_the_wrist_visibly", angle(o["B10"]["bones"][u"bip_hand_l"]["world_orientation"],
                                                        o["B11"]["bones"][u"bip_hand_l"]["world_orientation"]) >= VISIBLE
        or dist(o["B10"]["bones"][u"bip_hand_l"]["world_position"], o["B11"]["bones"][u"bip_hand_l"]["world_position"])
        >= 1.0)
    chk("seq.legacy_arm_keeps_the_finger_articulation", all(angle(
        o["B10"]["bones"][b]["local_orientation"], o["B11"]["bones"][b]["local_orientation"]) <= TOL["angle_degrees"]
        for b in FINGERS))
    applied("seq_grip", o["B11"], o["B12"], grip, GRIP)
    chk("seq.undo_fingers_then_arm", not changed(o["B11"], o["B13"]) and not changed(o["B10"], o["B14"]) and
        undo_desc(o["B13"]) == u"Apply Pose " + LEGACY, (changed(o["B11"], o["B13"])[:4], changed(o["B10"], o["B14"])[:4]))
    chk("seq.redo_arm_then_fingers", not changed(o["B11"], o["B15"]) and not changed(o["B12"], o["B16"]) and
        undo_desc(o["B16"]) == u"Apply Pose " + GRIP, (changed(o["B11"], o["B15"])[:4], changed(o["B12"], o["B16"])[:4]))

    # Process C (optional): an ordinary attached prop
    if prop:
        if undo_desc(o["C2"]) == u"Apply Pose " + GRIP:
            R.findings.append("prop: applied (the prop stays under its own SFM relationship; CPM does not verify it)")
            applied("prop_apply", o["C1"], o["C2"], grip, GRIP)
            chk("prop.undo_restores", not changed(o["C1"], o["C3"]) and not skeleton_moved(o["C1"], o["C3"]))
        else:
            R.findings.append("prop: refused by CPM (see the log reason); nothing written")
            chk("prop.refusal_writes_nothing", doc_unchanged(o["C1"], o["C2"]))

    # UI captures
    for label, step in (("UI-A", "A"), ("UI-B", "B")):
        path = os.path.join(R.q, "observations", label + ".json")
        ui = read_json(path) if os.path.isfile(path) else None
        sel = (ui or {}).get("selected") or {}
        chk("ui.%s_pose_info_and_apply_state" % label, ui is not None and sel.get("version") == 3 and
            sel.get("scope_kind") == u"selected_parts" and ui.get("apply_button_enabled") is True and
            ui.get("registry_mode") == u"qualification" and not ui.get("recovery_paused") and
            (ui.get("pose_info") or {}).get("engine") == u"direct_fk_v1 revision 1" and
            ui.get("pid") == o[step + "1"]["pid"], sel)

    # CPM's own log
    logs = parse_logs(os.path.join(R.q, "evidence", "logs"))
    ops = ops_of(logs, list(pids["B"])[0])
    applied_ops = [op for op in ops if op["scoped_p6"]]
    chk("log.three_scoped_applies_owned_and_verified_by_cpm", len(applied_ops) == 3 and
        all(op["owned"] and op["scoped_p7"] for op in applied_ops), [op["id"] for op in applied_ops])
    chk("log.repeat_is_noop", len([op for op in ops if (op["p1"] or {}).get("noop") is True and not op["scoped_p6"]])
        == 1)
    chk("log.point_updates_only", len(applied_ops) == 3 and ((applied_ops[1]["p1"] or {}).get("actions") or {})
        .get("insert") == 0 and ((applied_ops[1]["p1"] or {}).get("actions") or {}).get("update", 0) > 0,
        applied_ops[1]["p1"] if len(applied_ops) > 1 else None)
    chk("log.abort_verified", len([op for op in ops if op["abort"]]) == 1)
    chk("log.legacy_verified_by_cpm", len([op for op in ops if op["legacy_p6"] and op["legacy_p7"]]) == 1)
    chk("log.no_recovery_or_uncertainty", not any(("RECOVERY_BLOCKED" in r["text"] or "undo-uncertain" in r["text"] or
                                                   "abort-unverified" in r["text"] or "P7-unverified" in r["text"])
                                                  for r in logs))
    R.timing = [scoped_timing(op, s) for op, s in zip(applied_ops, ("B2", "B6", "B12"))]

    # Restoration and the sessions
    restore = os.path.join(R.q, "evidence", "restore.json")
    chk("restore.published_and_inventories_equal", os.path.isfile(restore) and read_json(restore).get("restored") is True)
    pin = os.path.join(R.q, "evidence", "destination.json")
    pins = read_json(pin) if os.path.isfile(pin) else {}
    chk("sessions.destination_not_saved_during_the_run", pins.get("destination_sha256") is not None and
        s0_hash(os.path.join(R.q, "sessions", "SFP1_DESTINATION.dmx")) == pins["destination_sha256"])
    if prop:
        chk("sessions.prop_session_not_saved_during_the_run", pins.get("prop_sha256") is not None and
            s0_hash(os.path.join(R.q, "sessions", "SFP1_PROP.dmx")) == pins["prop_sha256"])


def performance(R):
    rows = R.timing
    if not rows or any(t["blocking_ms"] is None or t["whole_ms"] is None for t in rows):
        return {"class": "unmeasured", "applies": rows}
    worst = max(max(t["blocking_ms"], t["whole_ms"]) for t in rows)
    cls = "responsive" if worst <= PERF["responsive_ms"] else ("finding" if worst <= PERF["limit_ms"] else "fail")
    return {"class": cls, "worst_ms": worst, "criteria_ms": PERF, "applies": rows}


def run(c):
    R = Run(c)
    evaluate(R)
    perf = performance(R)
    failed = [x for x in R.checks if not x["pass"]]
    verdict = "PASS" if R.checks and not failed and perf["class"] in ("responsive", "finding") else "FAIL"
    out = {"format": "F01-SFP1-verdict-v1", "verdict": verdict, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in failed], "performance": perf, "timing": R.timing, "findings": R.findings}
    ev = os.path.join(R.q, "evidence")
    for name, data in (("SFP1_VERDICT.json", json.dumps(out, indent=1, sort_keys=True, default=str)),
                       ("SFP1_VERDICT.md", markdown(out))):
        fd = os.open(os.path.join(ev, name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(markdown(out))
    return 0 if verdict == "PASS" else 1


def markdown(out):
    lines = ["# F-01 SFP-1 Selected parts native qualification verdict: %s" % out["verdict"], "",
             "Qualification CPM `%s`." % out["identities"].get("qualification_cpm_sha256"), "",
             "| Check | Result | Detail |", "|---|---|---|"]
    for x in out["checks"]:
        lines.append("| `%s` | %s | %s |" % (x["id"], "PASS" if x["pass"] else "**FAIL**",
                                            "" if x["pass"] or x["detail"] is None else
                                            json.dumps(x["detail"], default=str)[:200].replace("|", "/")))
    perf = out["performance"]
    lines += ["", "Performance: **%s** (worst %s ms; responsive <= %d ms, limit %d ms)." % (
        perf["class"], perf.get("worst_ms"), PERF["responsive_ms"], PERF["limit_ms"]), ""]
    lines += ["Findings: %s" % ("; ".join(out["findings"]) or "none"), ""]
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import sfp1_tool
    return run(sfp1_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
