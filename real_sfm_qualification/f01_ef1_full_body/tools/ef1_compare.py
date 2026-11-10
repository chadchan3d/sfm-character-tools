# -*- coding: utf-8 -*-
"""F-01 EF-1 Engineer Full body native qualification: the comparator. Python 3 (-I), offline, read-only over the run
folder; writes Q/evidence/EF1_VERDICT.json and EF1_VERDICT.md (exclusive create).

It turns each Expected result of PROCEDURE.md into a machine check over these inputs:
- the S0 observations and their .ef1.json sidecars;
- the restored Poses record;
- the UI captures, the CPM log and the session pins.

The geometry, schema validation and log parsing are the full-body S3 comparator's, unchanged
(f01_full_body_s3/tools/s3_compare.py and the S0 analysis validate).

**Bones:** the Engineer's 72 bones are the pinned header's (f01_ec1_engineer/engineer_header.json). The body root is
`bip_pelvis`. Model placement is the model's own transform (the `rootTransform` control), never a bone. Facial
controls are the 41 flex sliders: every control that is not a bone control.

**Tolerances** are R3's (PROD_SCOPE_TOLERANCES): 0.01 degrees and 0.001 units. The visible-difference threshold is 5
degrees, or 1 unit for positions.

**Model frame:** a bone's transform relative to the model's world transform. That is the frame of a Full body
record's oracle (`oracle.frame` component-boundary, whose boundary is the model for Full body).

**CPM's log operations** are identified by content, not by position.

usage: python -I ef1_compare.py EF1.json
"""
from __future__ import print_function

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RSQ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(RSQ, "f01_full_body_s3", "tools"))
sys.path.insert(0, os.path.join(RSQ, "f01_ec1_engineer", "tools"))
import s3_compare as K  # noqa: E402  (also puts the S0 analysis on the path)
import session_files as SF  # noqa: E402

angle, dist, read_json, parse_logs, apply_operations = K.angle, K.dist, K.read_json, K.parse_logs, K.apply_operations
compose, invert, s0_hash, validate = K.compose, K.invert, K.s0_hash, K.s0_analyze.validate

TOL = {"angle_degrees": 0.01, "position": 0.001}
VISIBLE_DEGREES, VISIBLE_UNITS = 5.0, 1.0
POSE = u"EF1 Body"
ROOT = u"bip_pelvis"
with open(os.path.join(RSQ, "f01_ec1_engineer", "engineer_header.json"), "rb") as _f:
    BONES = sorted(b["name"] for b in json.loads(_f.read().decode("utf-8"))["bones"])
ORIENTATION_CHANNELS = set(b + u"_o" for b in BONES)
POSITION_CHANNELS = set(b + u"_p" for b in BONES)
# A Full body Apply keys every skeletal channel at the mapped tick: each bone's orientation, the root's saved
# translation, and every other bone's position with the destination's own value (checked separately). Verified on
# CPM's own engine replaying the EC-1 observation: 144 channels written, none outside the skeleton.
WRITABLE = ORIENTATION_CHANNELS | POSITION_CHANNELS
PLACEMENT_CHANNELS = (u"rootTransform_p", u"rootTransform_o")
A = ["A1", "A2", "A3"]
B = ["B%d" % i for i in range(1, 11)]
LABELS = dict(zip(A + B, ["S0-%02d" % i for i in range(1, 14)]))
PERF = dict(K.PERF)
DOCS = {"A": u"ef1_source.dmx", "B": u"ef1_destination.dmx"}
NO_RIG = "expected one rig registration for the animation set, found 0"


class Run(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.timing, self.findings = [], [], []
        self.ids = read_json(os.path.join(self.q, "staged", "IDENTITIES.json"))
        self.obs, self.side = {}, {}
        for step, label in LABELS.items():
            path = os.path.join(self.q, "observations", label + ".json")
            side = os.path.join(self.q, "observations", label + ".ef1.json")
            if os.path.isfile(path):
                self.obs[step] = read_json(path)
            if os.path.isfile(side):
                self.side[step] = read_json(side)
        self.records = {}
        folder = os.path.join(self.q, "evidence", "library_poses", c["character_dir"])
        for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            if name.endswith(".json"):
                r = read_json(os.path.join(folder, name))
                self.records.setdefault(r.get("name"), []).append(r)

    def check(self, cid, ok, detail=None):
        self.checks.append({"id": cid, "pass": bool(ok), "detail": detail})
        return ok

    def record(self, name):
        rows = self.records.get(name) or []
        return rows[0] if len(rows) == 1 else None


# --- observation helpers ---------------------------------------------------------------------------------------------

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


def model_world(o):
    s = o["model"]["state"]
    return (s["world_position"], s["world_orientation"])


def in_model_frame(o, name):
    b = o["bones"][name]
    return compose(invert(model_world(o)), (b["world_position"], b["world_orientation"]))


def skeleton_moved(o1, o2, exclude=()):
    out = []
    for name in BONES:
        if name in exclude:
            continue
        b, c = o1["bones"].get(name), o2["bones"].get(name)
        if b is None or c is None:
            out.append("%s missing" % name)
            continue
        for kind in ("world", "local"):
            if dist(b[kind + "_position"], c[kind + "_position"]) > TOL["position"] or \
                    angle(b[kind + "_orientation"], c[kind + "_orientation"]) > TOL["angle_degrees"]:
                out.append("%s %s" % (name, kind))
    return out


def controls(o):
    return dict((c["id"]["name"], c.get("attributes")) for c in o.get("controls") or [])


def non_bone_controls_changed(o1, o2):
    a, b = controls(o1), controls(o2)
    return sorted(n for n in set(a) | set(b) if n not in BONES and a.get(n) != b.get(n))


def flex_values(o):
    """The facial sliders' values (every control that is neither a bone control nor the placement control)."""
    out = {}
    for name, attrs in controls(o).items():
        if name in BONES or name == u"rootTransform":
            continue
        out[name] = json.dumps(attrs, sort_keys=True)
    return out


def key_level_problems(before, after, names, t_chan):
    """R3 section 5 ("Non-root FK positions") and section 9 ("Owned writes") at key level, for each written channel:
    - the log, its layers (count, identity, type) and its protected metadata (defaults, curve info) are unchanged;
    - every key at another time is unchanged, and exactly one key exists at the mapped tick afterwards;
    - a non-root position channel is never updated: an existing key at the tick stays exactly as it was, and a
      missing one is inserted with the destination's own evaluated value.
    Unrecorded keys (S0 records them up to its bound) are a problem, never assumed preserved."""
    a, b = channels(before), channels(after)
    out = []
    for n in names:
        x, y = a.get(n), b.get(n)
        if x is None or y is None:
            out.append("%s missing" % n)
            continue
        if x.get("log") != y.get("log") or x.get("log_fields") != y.get("log_fields"):
            out.append("%s log or its metadata changed" % n)
        lx, ly = x.get("layers") or [], y.get("layers") or []
        if len(lx) != 1 or len(ly) != 1 or [(l.get("id"), l.get("type")) for l in lx] != \
                [(l.get("id"), l.get("type")) for l in ly]:
            out.append("%s layers changed" % n)
            continue
        kx, ky = lx[0].get("keys"), ly[0].get("keys")
        if not isinstance(kx, list) or not isinstance(ky, list):
            out.append("%s keys not recorded" % n)
            continue
        if [k for k in kx if k[0] != t_chan] != [k for k in ky if k[0] != t_chan]:
            out.append("%s keys at other times changed" % n)
        at_x, at_y = [k for k in kx if k[0] == t_chan], [k for k in ky if k[0] == t_chan]
        if len(at_y) != 1:
            out.append("%s has %d keys at the mapped tick" % (n, len(at_y)))
            continue
        if n in POSITION_CHANNELS and n != ROOT + u"_p":
            if at_x and at_x != at_y:
                out.append("%s: an existing position key was updated" % n)
            elif not at_x and dist(at_y[0][1], x.get("value_at_mapped")) > 1e-6:
                out.append("%s: the inserted position key is not the destination's own value" % n)
    return out


def placement_moved(o1, o2):
    out = []
    for key in ("world_position", "world_orientation", "local_position", "local_orientation"):
        a, b = o1["model"]["state"].get(key), o2["model"]["state"].get(key)
        if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b) or \
                (len(a) == 3 and dist(a, b) > TOL["position"]) or (len(a) == 4 and angle(a, b) > TOL["angle_degrees"]):
            out.append("model %s" % key)
    return out


def oracle_errors(o, record):
    """Largest differences between an observation and the record's independently observed oracle: local
    orientation of every bone; the body root's local position; every bone's transform in the model frame."""
    orc = record["pose"]["oracle"]["bones"]
    local = max(angle(o["bones"][b]["local_orientation"], orc[b]["local_orientation"]) for b in BONES)
    root = dist(o["bones"][ROOT]["local_position"], orc[ROOT]["local_position"])
    frame_p, frame_q = 0.0, 0.0
    for b in BONES:
        p, q = in_model_frame(o, b)
        frame_p = max(frame_p, dist(p, orc[b]["relative_position"]))
        frame_q = max(frame_q, angle(q, orc[b]["relative_orientation"]))
    return {"local_degrees": local, "root_units": root, "model_frame_units": frame_p, "model_frame_degrees": frame_q}


def body_spread(o1, o2):
    return {"degrees": max(angle(o1["bones"][b]["local_orientation"], o2["bones"][b]["local_orientation"])
                           for b in BONES),
            "root_units": dist(o1["bones"][ROOT]["local_position"], o2["bones"][ROOT]["local_position"])}


def undo_of(o):
    return o["session_after"]["undo"]


def ops_of(logs, pid):
    """Apply Pose operations of one SFM process with the scoped marks (identified by content)."""
    ops = apply_operations(logs, pid)
    for op in ops:
        text = op["text"]
        op["scoped_p6"] = any(t.startswith("PROD_POSE_SCOPE-P6 ") for t in text)
        op["scoped_p7"] = any(t.startswith("PROD_POSE_SCOPE-P7-verified") for t in text)
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


# --- the checks ------------------------------------------------------------------------------------------------------

def evaluate(R):
    o, chk = R.obs, R.check
    steps = A + B
    for step in steps:
        if not chk("observed.%s" % step, step in o and step in R.side, LABELS[step]):
            continue
        problems = validate(o[step]) + list(o[step].get("problems") or []) + list(R.side[step]["mismatch"])
        chk("valid.%s" % step, not problems and o[step]["readonly"]["unchanged"], problems[:5])
        chk("findings.%s_only_the_no_rig_note" % step, (o[step].get("findings") or []) == [NO_RIG],
            o[step].get("findings"))
        chk("cpm.%s" % step, (o[step].get("cpm_loaded") or {}).get("build_sha256") == R.ids["qualification_cpm_sha256"],
            o[step].get("cpm_loaded"))
        chk("structure.%s_has_the_72_engineer_bones" % step, sorted(o[step].get("bones") or {}) == BONES,
            len(o[step].get("bones") or {}))
    missing = sorted(s for s in steps if s not in o or s not in R.side)
    if missing:
        chk("complete", False, "missing observations: %s" % missing)
        return
    pids = dict((p, set(o[s]["pid"] for s in group)) for p, group in (("A", A), ("B", B)))
    chk("process.restart_between_save_and_apply", len(pids["A"]) == 1 and len(pids["B"]) == 1 and
        pids["A"] != pids["B"], dict((k, sorted(v)) for k, v in pids.items()))
    chk("process.sessions", all((o[s]["document"] or u"").replace("\\", "/").lower().endswith(DOCS[s[0]])
                                for s in steps), dict((s, o[s]["document"]) for s in ("A1", "B1")))
    chk("process.one_animation_set_in_each_session", all(R.side[s]["animation_set"] == R.side["A1"]["animation_set"]
                                                         for s in steps), R.side["A1"]["animation_set"])

    # --- Save New (Process A) ----------------------------------------------------------------------------------
    rec = R.record(POSE)
    chk("library.one_record", rec is not None and sorted(R.records) == [POSE],
        dict((k, len(v)) for k, v in R.records.items()))
    if rec is None:
        return
    la, lb = (os.path.join(R.q, "evidence", "library_%s.json" % t) for t in ("A", "B"))
    chk("library.records_unchanged_by_the_apply_process", os.path.isfile(la) and os.path.isfile(lb) and
        read_json(la)["files"] == read_json(lb)["files"] and len(read_json(la)["files"]) == 1)
    pose = rec["pose"]
    sc = pose.get("scope") or {}
    chk("save.is_version_3_full_body_of_all_72_bones",
        pose.get("version") == 3 and sc.get("kind") == u"full_body" and sc.get("completeness") == u"declared_body" and
        sorted(sc.get("posed") or []) == BONES and sc.get("carried") == [] and sc.get("exclusions") == [] and
        sc.get("root_translation") == u"included" and (pose.get("structure") or {}).get("root") == ROOT and
        pose.get("engine") == {u"rule": u"direct_fk_v1", u"revision": 1, u"carried_rule": None},
        {"version": pose.get("version"), "kind": sc.get("kind"), "posed": len(sc.get("posed") or []),
         "carried": sc.get("carried"), "root_translation": sc.get("root_translation"),
         "root": (pose.get("structure") or {}).get("root"), "engine": pose.get("engine")})
    chk("save.oracle_frame_is_the_model", (pose.get("oracle") or {}).get("frame") == u"component-boundary" and
        sorted((pose.get("oracle") or {}).get("bones") or {}) == BONES)
    err = oracle_errors(o["A2"], rec)
    chk("save.captures_the_visible_pose", err["local_degrees"] <= TOL["angle_degrees"] and
        err["root_units"] <= TOL["position"] and err["model_frame_units"] <= TOL["position"] and
        err["model_frame_degrees"] <= TOL["angle_degrees"], err)
    rt = (pose.get("values") or {}).get("root_translation")
    chk("save.root_translation_is_the_root_channel_value", isinstance(rt, list) and len(rt) == 3 and
        dist(rt, channels(o["A2"])[ROOT + u"_p"]["value_at_mapped"]) <= TOL["position"], rt)
    spread = body_spread(o["A1"], o["A2"])
    chk("save.pose_differs_visibly_from_the_source_baseline", spread["degrees"] >= VISIBLE_DEGREES and
        spread["root_units"] >= VISIBLE_UNITS, spread)
    chk("save.source_posing_touched_only_bones", not non_bone_controls_changed(o["A1"], o["A2"]) and
        not placement_moved(o["A1"], o["A2"]), (non_bone_controls_changed(o["A1"], o["A2"])[:6],
                                                placement_moved(o["A1"], o["A2"])))
    chk("save.writes_nothing_to_the_scene", doc_unchanged(o["A2"], o["A3"]))

    # --- a visibly different destination ------------------------------------------------------------------------
    b1 = o["B1"]
    err = oracle_errors(b1, rec)
    chk("distinct.destination_body_differs_from_the_pose", err["local_degrees"] >= VISIBLE_DEGREES, err)
    chk("distinct.destination_body_root_differs_from_the_pose", err["root_units"] >= VISIBLE_UNITS, err)
    mp = (dist(model_world(b1)[0], model_world(o["A2"])[0]), angle(model_world(b1)[1], model_world(o["A2"])[1]))
    chk("distinct.destination_model_placement_differs", mp[0] >= VISIBLE_UNITS or mp[1] >= VISIBLE_DEGREES, mp)
    face = sorted(n for n, v in flex_values(b1).items() if flex_values(o["A2"]).get(n) != v)
    chk("distinct.destination_has_a_facial_expression", bool(face), face[:6])

    def applied(label, before, after):
        ch = changed(before, after)
        e = oracle_errors(after, rec)
        chk("%s.one_owned_undo_entry" % label, undo_of(after).get("undo_desc") == u"Apply Pose " + POSE and
            undo_of(after).get("can_undo") is True, undo_of(after))
        chk("%s.every_bone_takes_the_saved_orientation" % label, e["local_degrees"] <= TOL["angle_degrees"], e)
        chk("%s.body_root_takes_the_saved_translation" % label, e["root_units"] <= TOL["position"] and
            dist(after["bones"][ROOT]["local_position"], rt) <= TOL["position"], e)
        chk("%s.body_matches_the_pose_in_the_model_frame" % label, e["model_frame_units"] <= TOL["position"] and
            e["model_frame_degrees"] <= TOL["angle_degrees"], e)
        chk("%s.non_root_offsets_are_the_destinations_own" % label, all(
            dist(after["bones"][b]["local_position"], before["bones"][b]["local_position"]) <= TOL["position"] and
            dist(channels(after)[b + u"_p"]["value_at_mapped"], channels(before)[b + u"_p"]["value_at_mapped"])
            <= TOL["position"] for b in BONES if b != ROOT))
        chk("%s.only_skeletal_channels_changed" % label, bool(ch) and set(ch) <= WRITABLE, ch[:8])
        chk("%s.model_placement_unchanged" % label, not placement_moved(before, after) and
            not set(ch) & set(PLACEMENT_CHANNELS), placement_moved(before, after))
        chk("%s.facial_and_placement_controls_unchanged" % label, not non_bone_controls_changed(before, after),
            non_bone_controls_changed(before, after)[:8])
        chk("%s.unrelated_animation_unchanged" % label, R.side[step_of(before)]["outside"]["sha256"] ==
            R.side[step_of(after)]["outside"]["sha256"])
        chk("%s.keys_at_the_mapped_tick" % label, all(channels(after)[n]["layers"][0].get("key_at_mapped") is not None
                                                       for n in ch if n in channels(after)))
        kl = key_level_problems(before, after, ch, after["time"]["t_chan"])
        chk("%s.neighbouring_keys_layers_and_metadata_preserved" % label,
            not [p for p in kl if "position key" not in p], kl[:8])
        chk("%s.non_root_position_keys_inserted_only_where_missing" % label,
            not [p for p in kl if "position key" in p], [p for p in kl if "position key" in p][:8])
        return ch

    def step_of(obs):
        return [s for s in steps if o[s] is obs][0]

    chk("abort.verified_nothing_changed", doc_unchanged(b1, o["B2"]))
    applied("apply", o["B2"], o["B3"])
    chk("undo.restores_the_destination_baseline", not changed(b1, o["B4"]) and not skeleton_moved(b1, o["B4"]) and
        undo_of(o["B4"]).get("undo_desc") == undo_of(b1).get("undo_desc") and undo_of(o["B4"]).get("can_redo") is True,
        changed(b1, o["B4"])[:8])
    chk("redo.restores_the_applied_pose", not changed(o["B3"], o["B5"]) and not skeleton_moved(o["B3"], o["B5"]) and
        undo_of(o["B5"]).get("undo_desc") == u"Apply Pose " + POSE, changed(o["B3"], o["B5"])[:8])
    chk("repeat.true_noop", doc_unchanged(o["B5"], o["B6"]))
    chk("refusal.clip_editor_writes_nothing", doc_unchanged(o["B7"], o["B8"]) and not changed(o["B6"], o["B8"]))
    chk("editor.switching_back_changes_nothing", not changed(o["B8"], o["B9"]) and not skeleton_moved(o["B6"], o["B9"]))
    chk("undo.final_undo_returns_to_the_baseline", not changed(b1, o["B10"]) and not skeleton_moved(b1, o["B10"]) and
        not placement_moved(b1, o["B10"]), changed(b1, o["B10"])[:8])

    # --- UI captures ----------------------------------------------------------------------------------------------
    for label, step in (("UI-A", "A"), ("UI-B", "B")):
        path = os.path.join(R.q, "observations", label + ".json")
        ui = read_json(path) if os.path.isfile(path) else None
        sel = (ui or {}).get("selected") or {}
        chk("ui.%s_pose_info_and_apply_state" % label, ui is not None and sel.get("name") == POSE and
            sel.get("version") == 3 and sel.get("scope_kind") == u"full_body" and sel.get("posed") == len(BONES) and
            ui.get("apply_button_enabled") is True and ui.get("registry_mode") == u"qualification" and
            not ui.get("recovery_paused") and (ui.get("pose_info") or {}).get("engine") == u"direct_fk_v1 revision 1"
            and "error" not in (ui.get("pose_info") or {}) and ui.get("pid") == o[step + "1"]["pid"] and
            ui.get("cpm_build_sha256") == R.ids["qualification_cpm_sha256"], sel)

    # --- CPM's own log --------------------------------------------------------------------------------------------
    logs = parse_logs(os.path.join(R.q, "evidence", "logs"))
    ops = ops_of(logs, list(pids["B"])[0])
    applied_ops = [op for op in ops if op["scoped_p6"]]
    chk("log.one_scoped_apply_owned_and_verified_by_cpm", len(applied_ops) == 1 and
        all(op["owned"] and op["scoped_p7"] for op in applied_ops), [op["id"] for op in applied_ops])
    chk("log.abort_verified_before_the_apply", len([op for op in ops if op["abort"]]) == 1 and
        bool(applied_ops) and [op for op in ops if op["abort"]][0]["begin"] < applied_ops[0]["begin"])
    chk("log.repeat_is_noop", len([op for op in ops if (op["p1"] or {}).get("noop") is True and not op["scoped_p6"]])
        == 1)
    chk("log.apply_writes_the_body", bool(applied_ops) and sum(((applied_ops[0]["p1"] or {}).get("actions") or {})
                                                               .get(k, 0) for k in ("insert", "update")) > 0,
        applied_ops[0]["p1"] if applied_ops else None)
    chk("log.no_recovery_or_uncertainty", not any(("RECOVERY_BLOCKED" in r["text"] or "undo-uncertain" in r["text"] or
                                                   "abort-unverified" in r["text"] or "P7-unverified" in r["text"])
                                                  for r in logs))
    R.timing = [scoped_timing(op, "B3") for op in applied_ops]

    # --- restoration and the sessions -----------------------------------------------------------------------------
    restore = os.path.join(R.q, "evidence", "restore.json")
    chk("restore.published_and_inventories_equal", os.path.isfile(restore) and read_json(restore).get("restored") is True)
    char = os.path.join(R.c["paths"]["LIBRARY"], "Characters", R.c["character_dir"]) if "LIBRARY" in R.c["paths"] \
        else None
    chk("restore.engineer_character_folder_removed", char is None or not os.path.exists(char), char)
    pin_path = os.path.join(R.q, "evidence", "destination.json")
    pins = read_json(pin_path) if os.path.isfile(pin_path) else {}
    rows = SF.classify_folder(os.path.join(R.q, "sessions"))
    for key in ("source", "destination"):
        row = SF.by_name(rows, pins.get(key + "_name") or u"")
        chk("sessions.%s_not_saved_during_the_run" % key, row is not None and pins.get(key + "_sha256") is not None
            and row["sha256"] == pins[key + "_sha256"], row and row.get("sha256"))
    known = set(n.lower() for n in (pins.get("source_name"), pins.get("destination_name")) if n)
    # EF1-D1: SFM's starter-session backups, verified and pinned by hash at inspect; they must be unchanged and
    # still classify as an empty starter session.
    backups = dict((b["name"].lower(), b["sha256"]) for b in pins.get("starter_backups") or [])
    for r in rows:
        if r["name"].lower() in backups:
            chk("sessions.starter_backup_%s_unchanged" % r["name"].lower(), r["class"] == "starter" and
                r["sha256"] == backups[r["name"].lower()], r.get("sha256"))
    missing_backups = sorted(set(backups) - set(r["name"].lower() for r in rows))
    chk("sessions.starter_backups_preserved", not missing_backups, missing_backups)
    autosaves = [r["name"] for r in rows if r["class"] == "autosave"]
    unexpected = [r["name"] for r in rows if r["name"].lower() not in known and r["class"] != "autosave" and
                  r["name"].lower() not in backups]
    chk("sessions.no_unexpected_files", not unexpected, unexpected)
    if backups:
        R.findings.append("EF1-D1: SFM's starter-session backup(s) kept as evidence, verified empty: %s" %
                          sorted(backups))
    if autosaves:
        R.findings.append("SFM autosave copies in the sessions folder (not saves): %s" % autosaves)


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
    out = {"format": "F01-EF1-verdict-v1", "verdict": verdict, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in failed], "performance": perf, "timing": R.timing, "findings": R.findings}
    ev = os.path.join(R.q, "evidence")
    for name, data in (("EF1_VERDICT.json", json.dumps(out, indent=1, sort_keys=True, default=str)),
                       ("EF1_VERDICT.md", markdown(out))):
        fd = os.open(os.path.join(ev, name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(markdown(out))
    return 0 if verdict == "PASS" else 1


def markdown(out):
    lines = ["# F-01 EF-1 Engineer Full body native qualification verdict: %s" % out["verdict"], "",
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
    import ef1_tool
    return run(ef1_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
