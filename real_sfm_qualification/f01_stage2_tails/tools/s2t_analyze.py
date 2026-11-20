# -*- coding: utf-8 -*-
"""F-01 Stage 2: the verdict of the native Tails JIGGLE leaf qualification. Python 3, run with -I after restore, with
SFM closed. It never changes the run.

Reads Q/staged/IDENTITIES.json, Q/observations/S1F-<step>.json and S1F-<step>.leaves.json, Q/evidence (logs,
library_cleanup.json, library_after, restore.json) and Q/sessions. Writes Q/evidence/S2T_VERDICT.json and
S2T_VERDICT.md (exclusive create). The Fox analyzer's helpers are reused unchanged.

Two SFM processes on one disposable copy of the R2 fixture (S2T_SESSION.dmx):
  Process A  two fresh Tails instances, both rigged with the installed stock rig_biped_simple: Tails S (source,
             posed) and Tails D (destination, posed and placed differently). All posing finished before PREP.
             PREP, Save New Full body "S2 Tails", SAVED (Pose Info), File > Save, exit.
  Process B  after the restart: BASE (Tails D and S2 Tails selected), APPLY, NAV (away and back), UNDO, REDO.
The session's original Tails (milestailsprower1) is the untouched peer. Abort is not repeated (Designer: Stage 1's
transaction and Abort evidence is reused). A gate with no evaluated check is NOT EVALUATED, never PASS.

The seven simulated leaves are the bones CPM classes simulated-leaf. Their simulated transforms are never compared
(Astra: "without demanding identical simulated tip transforms"); they are recorded for information only. Their
channels, keys, scale and header declaration are compared exactly.

Gates:
  EVIDENCE  identities; every capture with the qualification build, no capture error, and a complete leaf sidecar
            from the same process and step; PREP and SAVED from one SFM process, BASE..REDO from another; every capture
            on S2T_SESSION.dmx in the Motion Editor at the same shot and playhead; the session copy saved once,
            the spare never; the library changed only by the one Tails pose (with pose_sources.json and character
            files); library and installation restored exactly; the CPM log collected, with no unverified,
            uncertain, failed-Abort or lockout result
  PREP      Tails S, Tails D and the peer are the Tails model; S and D admitted by the structural discovery with the
            same drafted description and different rig names; each with exactly the seven header-declared JIGGLE
            leaves as simulated leaves, with the same declarations; D posed and placed visibly differently; the saved
            session reopens as prepared
  SAVE      one version 2 structural record of Tails S, adapter revision 2, with the drafted written set; it describes
            exactly S's simulated leaves and saves no value or oracle for them; the CPM log reports the admission
            with the seven leaves; Save read-only; the record selected in Pose Info at SAVED and again after the
            restart
  APPLY     only Tails D's drafted written channels changed, both rig handle and direct bone channels, each with one
            key at the mapped tick and every other key unchanged; P7 verified; one owned "Apply Pose S2 Tails" entry;
            Tails D's simulated leaf channels unchanged (never authored by CPM)
  POSTURE   independent of CPM's planner: every non-leaf bone of Tails D, relative to its own placement handle,
            matches Tails S's saved posture (0.05 units, 0.5 degrees; maxima reported); D's placement handle and
            model transform (placement and facing) and its direct bones' local offsets unchanged
  HISTORY   navigation away and back keeps the authored pose and the non-leaf skeleton; Undo restores BASE, Redo
            restores APPLY, with the expected Edit menu entries
  LEAVES    for Tails S, Tails D and the peer: every leaf channel's authored state, every declared bone's scale and
            header declaration unchanged at every capture; Tails D's leaves admitted as simulated leaves at every
            Process B capture
  PEER      Tails S and the peer unchanged at every capture: authored state exactly, non-leaf skeleton within 0.001
            units and 0.01 degrees
Verdict: AUTOMATED PASS (every gate; acceptance also needs the Owner's visual assessment: useful posture, no severe
deformation); REFUSED (Tails S's Full body Save was refused: safe, not a compatibility pass; the reasons are reported);
FAIL (complete evidence, a functional gate failed); INCOMPLETE (evidence, preparation or restoration missing or
failed).

usage: python -I s2t_analyze.py S2T.json      (or: s2t_tool.py S2T.json analyze)
"""
from __future__ import print_function

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_stage1_fox", "tools"))
import s1f_analyze as A  # noqa: E402

A_STEPS = ("PREP", "SAVED")
B_STEPS = ("BASE", "APPLY", "NAV", "UNDO", "REDO")
STEPS = A_STEPS + B_STEPS
ROLES = A.ROLES
SESSION = "S2T_SESSION.dmx"
SPARE = "S2T_SPARE.dmx"
MODEL = "models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl"
PEER = u"milestailsprower1"
RULE = {"rule": "structural_rig_v1", "revision": 2}
POSE = u"S2 Tails"
LEAF = u"simulated-leaf"
LEAVES_EXPECTED = 7
JIGGLE = "STUDIO_PROC_JIGGLE"
SIDECAR_FORMAT = "F01-S2T-leaves-v1"
PLACEMENT = A.PLACEMENT
BAD_LOG = A.BAD_LOG + ("PROD_POSE_RECOVERY_BLOCKED", "recovery-blocked", "committed-unverified",
                       "PROD_POSE_BODY-P3-P6-failure")
GATES = ("EVIDENCE", "PREP", "SAVE", "APPLY", "POSTURE", "HISTORY", "LEAVES", "PEER")


class Report(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.info = [], {}
        self.ids = A.opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap, self.side = {}, {}
        for step in STEPS:
            data = A.opt_json(os.path.join(self.q, "observations", "S1F-%s.json" % step))
            if isinstance(data, dict) and isinstance(data.get("pid"), int):
                self.cap[step] = data
            side = A.opt_json(os.path.join(self.q, "observations", "S1F-%s.leaves.json" % step))
            if isinstance(side, dict):
                self.side[step] = side

    def check(self, gate, cid, ok, detail=None):
        self.checks.append({"gate": gate, "id": cid, "pass": bool(ok), "detail": None if ok else detail})
        return ok

    def ev(self, *parts):
        return os.path.join(self.q, "evidence", *parts)


# --- leaves and sidecars -------------------------------------------------------------------------------------------

def side_set(R, step, role):
    s = ((R.side.get(step) or {}).get("sets") or {}).get(role)
    return s if isinstance(s, dict) else {}


def sidecar_ok(R, step):
    side, cap = R.side.get(step) or {}, R.cap.get(step) or {}
    return (side.get("format") == SIDECAR_FORMAT and side.get("step") == step and side.get("pid") == cap.get("pid")
            and side.get("names") == cap.get("names") and all(side_set(R, step, r).get("status") == "READ"
                                                               for r in ROLES))


def declared_jiggle(R, step, role):
    s = side_set(R, step, role)
    k = (s.get("constants") or {}).get(JIGGLE)
    return sorted(d["name"] for d in s.get("declared") or [] if k is not None and d.get("proctype") == k)


def declarations(R, step, role):
    s = side_set(R, step, role)
    return {"declared": s.get("declared"), "scales": s.get("scales"), "constants": s.get("constants")}


def leaves(cap, role):
    classes = A.adm(cap, role).get("bone_classes") or {}
    return sorted(n for n, c in classes.items() if c == LEAF)


def leaf_channels(cap, role):
    roles = A.adm(cap, role).get("roles") or {}
    return sorted(n for n, r in roles.items() if r == LEAF)


def leaf_sha(cap, role, names):
    f = A.field(cap, role, "sha256")
    return dict((n, f.get(n)) for n in names)


def bones_without(cap, role, skip):
    return dict((n, b) for n, b in (A.sets(cap, role).get("bones") or {}).items() if n not in skip)


def refusal_reasons(lines):
    out = []
    for l in lines:
        for tag in ("PROD_POSE_BODY-RIG-leaf-refused", "PROD_POSE_BODY-RIG-unavailable"):
            if tag in l:
                out.append({tag: A.log_json(l, tag)})
    return out[:6]


# --- library and restoration (the Fox analyzer's rule, for this session name) --------------------------------------

def pose_sources_ok(R, x, poses):
    parts = x["path"].split("/")
    if (x["status"] != "added" or len(parts) != 3 or parts[0] != "Characters" or parts[2] != "pose_sources.json" or
            len(poses) != 1 or poses[0]["path"].split("/")[1] != parts[1]):
        return False
    path = R.ev("library_after", *parts)
    if not os.path.isfile(path) or A.sha(path) != x.get("sha256"):
        return False
    data = A.opt_json(path)
    pid = (A.opt_json(R.ev("library_after", *poses[0]["path"].split("/"))) or {}).get("preset_id")
    norm = lambda p: p.replace("/", "\\").lower() if isinstance(p, type(u"")) else None  # noqa: E731
    if not isinstance(data, dict) or sorted(data) != ["entries", "record_kind", "schema_version"]:
        return False
    entries = data["entries"]
    return (data["record_kind"] == u"cpm-pose-sources" and data["schema_version"] == 1 and
            isinstance(pid, type(u"")) and isinstance(entries, dict) and list(entries) == [pid] and
            isinstance(entries[pid], dict) and list(entries[pid]) == ["project"] and
            norm(entries[pid]["project"]) == norm(os.path.join(R.q, "sessions", SESSION)))


def library_and_restore(R):
    clean = A.opt_json(R.ev("library_cleanup.json")) or {}
    diffs = clean.get("differences_kept_in_evidence") or []
    poses = [x for x in diffs if "/Poses/" in x["path"]]
    allowed = lambda x: (x["status"] == "added" and x["path"].startswith("Characters/") and  # noqa: E731
                         (re.match(r"^Characters/[^/]+/Poses/[^/]+\.json$", x["path"]) or
                          re.match(r"^Characters/[^/]+/character\.json(\.bak)?$", x["path"]) or
                          pose_sources_ok(R, x, poses)))
    unexpected = [x for x in diffs if not allowed(x)]
    R.check("EVIDENCE", "library.changed_only_by_the_one_tails_pose", bool(clean) and not unexpected and
            len(poses) <= 1, {"unexpected": unexpected, "poses": poses})
    R.check("EVIDENCE", "restore.library_exactly_as_before", clean.get("files_equal_pre") is True and
            clean.get("folders_equal_pre") is True)
    restore = A.opt_json(R.ev("restore.json")) or {}
    R.check("EVIDENCE", "restore.published_and_inventories_equal", restore.get("restored") is True,
            restore.get("inventory_problems"))


def saved_records(R):
    out = []
    for path in sorted(glob.glob(R.ev("library_after", "Characters", "*", "Poses", "*.json"))):
        out.append((os.path.relpath(path, R.ev("library_after")).replace("\\", "/"), A.opt_json(path)))
    return out


# --- the gates -----------------------------------------------------------------------------------------------------

def evaluate(R):
    cap, c = R.cap, R.c
    E = lambda cid, ok, d=None: R.check("EVIDENCE", cid, ok, d)  # noqa: E731
    want = c["pins"]["qualification_cpm_sha256"]
    E("identity.qualification_build", R.ids.get("qualification_cpm_sha256") == want and
      R.ids.get("candidate_cpm_sha256") == c["pins"]["candidate_cpm_sha256"], R.ids.get("qualification_cpm_sha256"))
    records = saved_records(R)
    lines = A.logs(R)
    refused = "SAVED" in cap and not records
    R.info["refusal"] = {"reasons": refusal_reasons(lines), "source_admission": A.adm(cap["SAVED"], "source").get(
        "error") or A.adm(cap["SAVED"], "source").get("code")} if refused else None
    steps = A_STEPS if refused else STEPS
    for step in steps:
        if not E("captured.%s" % step, step in cap):
            continue
        d = cap[step]
        E("cpm.%s" % step, d.get("cpm_build_sha256") == want and d.get("registry_mode") == u"qualification",
          (d.get("cpm_build_sha256"), d.get("registry_mode")))
        E("errors.%s" % step, not d.get("errors") and all(r in (d.get("sets") or {}) for r in ROLES), d.get("errors"))
        E("leaf_sidecar.%s" % step, sidecar_ok(R, step), dict((r, side_set(R, step, r).get("status")) for r in ROLES))
    session, spare = os.path.join(R.q, "sessions", SESSION), os.path.join(R.q, "sessions", SPARE)
    E("sessions.session_copy_saved_by_process_a", os.path.isfile(session) and A.sha(session) !=
      c["pins"]["r2_fixture_sha256"])
    E("sessions.spare_never_saved", os.path.isfile(spare) and A.sha(spare) == c["pins"]["destination_sha256"])
    R.info["session_sha256"] = A.sha(session) if os.path.isfile(session) else None
    library_and_restore(R)
    E("log.collected", bool(lines))
    bad = [l for l in lines if any(b in l for b in BAD_LOG)]
    E("log.no_unverified_uncertain_failed_abort_or_lockout_result", not bad, bad[:4])
    if any(s not in cap for s in steps):
        return refused
    pa = set(cap[s]["pid"] for s in A_STEPS)
    pb = set(cap[s]["pid"] for s in steps if s in B_STEPS)
    E("process.a_then_a_restarted_b", len(pa) == 1 and (refused or (len(pb) == 1 and pa != pb)),
      (sorted(pa), sorted(pb)))
    docs = set(u"%s" % ((cap[s].get("session") or {}).get("document") or u"") for s in steps)
    E("process.every_capture_on_the_disposable_session", len(docs) == 1 and list(docs)[0].lower().replace(
        "\\", "/").endswith(SESSION.lower()), sorted(docs))
    heads = [(cap[s].get("session") or {}).get("head_seconds") for s in steps]
    shots = set(u"%s" % (cap[s].get("session") or {}).get("shot") for s in steps)
    modes = set(u"%s" % (cap[s].get("session") or {}).get("timeline_mode") for s in steps)
    E("session.same_shot_and_playhead_motion_editor", len(shots) == 1 and all(h == heads[0] for h in heads) and
      modes == set([u"2"]), (sorted(shots), heads, sorted(modes)))

    # PREP
    Pp = lambda cid, ok, d=None: R.check("PREP", cid, ok, d)  # noqa: E731
    prep = cap["PREP"]
    models = dict((r, A.sets(prep, r).get("model")) for r in ROLES)
    names = (prep.get("names") or {})
    Pp("prep.three_tails_sets_with_the_original_as_peer", all(
        (u"%s" % models[r]).replace("\\", "/").lower() == MODEL for r in ROLES) and names.get("peer") == PEER,
       (models, names))
    a_src, a_tgt = A.adm(prep, "source"), A.adm(prep, "target")
    Pp("prep.tails_s_and_d_admitted_by_structural_discovery", a_src.get("placement") == PLACEMENT and
       a_tgt.get("placement") == PLACEMENT, {"source": a_src.get("error") or a_src.get("placement"),
                                             "target": a_tgt.get("error") or a_tgt.get("placement")})
    Pp("prep.same_drafted_description_whatever_the_rig_name", a_src.get("description_sha256") and
       a_src.get("description_sha256") == a_tgt.get("description_sha256") and
       a_src.get("rig_name") != a_tgt.get("rig_name"), (a_src.get("rig_name"), a_tgt.get("rig_name")))
    jig = dict((r, declared_jiggle(R, "PREP", r)) for r in ("source", "target"))
    adm_leaves = dict((r, leaves(prep, r)) for r in ("source", "target"))
    R.info["leaves"] = {"declared_jiggle": jig, "admitted": adm_leaves}
    Pp("prep.the_seven_declared_jiggle_leaves_are_simulated_leaves", all(
        len(adm_leaves[r]) == LEAVES_EXPECTED and adm_leaves[r] == jig[r] for r in ("source", "target")),
       R.info["leaves"])
    Pp("prep.same_header_declarations_for_s_and_d", side_set(R, "PREP", "source").get("declared") ==
       side_set(R, "PREP", "target").get("declared"))
    skip = set(adm_leaves["source"]) | set(adm_leaves["target"])
    ps, pt = A.posture(prep, "source"), A.posture(prep, "target")
    common = sorted((set(ps) & set(pt)) - skip)
    dp, dq = A.max_difference(ps, pt, common)
    hs = A.world((A.sets(prep, "source").get("handles") or {}).get(PLACEMENT) or [[0.0] * 3, [0, 0, 0, 1]] * 2)
    ht = A.world((A.sets(prep, "target").get("handles") or {}).get(PLACEMENT) or [[0.0] * 3, [0, 0, 0, 1]] * 2)
    Pp("prep.tails_d_posed_and_placed_visibly_differently", dq > A.VISIBLE_ANGLE and (
        A.dist(hs[0], ht[0]) > A.VISIBLE_DISTANCE or A.angle(hs[1], ht[1]) > A.VISIBLE_ANGLE),
       {"posture_angle": dq, "placement_distance": A.dist(hs[0], ht[0]), "placement_angle": A.angle(hs[1], ht[1])})
    if not refused:
        reopened = dict((r, A.reopened_as_prepared(cap["SAVED"], cap["BASE"], r)) for r in ROLES)
        R.info["reload_renormalized_keys"] = dict((r, v[1]) for r, v in reopened.items())
        Pp("prep.saved_session_reopens_as_prepared", all(v[0] for v in reopened.values()),
           dict((r, v[2]) for r, v in reopened.items()))

    # SAVE
    V = lambda cid, ok, d=None: R.check("SAVE", cid, ok, d)  # noqa: E731
    saved = cap["SAVED"]
    rec = records[0][1] if len(records) == 1 else {}
    pose = (rec or {}).get("pose") or {}
    region = (pose.get("regions") or {}).get("full_body") or {}
    R.info["record"] = [r[0] for r in records]
    values = sorted(list(region.get("positions") or {}) + list(region.get("orientations") or {}))
    V("save.one_version2_structural_record_of_tails_s_at_revision_2", len(records) == 1 and
      pose.get("version") == 2 and pose.get("adapter") == RULE and sorted(pose.get("regions") or []) ==
      ["full_body"] and (u"%s" % (pose.get("source") or {}).get("model_ref")).lower() == MODEL and
      values == sorted(a_src.get("written") or []),
      {"records": len(records), "adapter": pose.get("adapter"), "written": len(values),
       "drafted": len(a_src.get("written") or [])})
    described = sorted(b.get("name") for b in (region.get("descriptor") or {}).get("bones") or []
                       if b.get("class") == LEAF)
    V("save.record_identifies_the_seven_leaves_without_value_or_oracle", described == adm_leaves["source"] and
      len(described) == LEAVES_EXPECTED and not set(leaf_channels(prep, "source")) & set(values) and
      not set(described) & set((region.get("oracle") or {}).get("bones") or {}), described)
    avail = [A.log_json(l, "PROD_POSE_BODY-RIG-available") for l in lines if "PROD_POSE_BODY-RIG-available" in l]
    V("save.structural_admission_logged_with_the_seven_leaves", any(
        isinstance(x, dict) and sorted(x.get("simulated_leaves") or []) == adm_leaves["source"] for x in avail),
      avail[:2])
    V("save.read_only", all(A.field(saved, r, "sha256") == A.field(prep, r, "sha256") for r in ROLES),
      dict((r, A.changed(A.field(prep, r, "sha256"), A.field(saved, r, "sha256"))[:6]) for r in ROLES))
    sel = saved.get("selected_pose") or {}
    V("save.pose_info_selection_is_the_saved_record", isinstance(sel, dict) and sel.get("adapter") == RULE and
      sel.get("preset_id") == (rec or {}).get("preset_id"), sel)
    if refused:
        return refused
    selb = cap["BASE"].get("selected_pose") or {}
    V("save.reopened_after_the_restart", isinstance(selb, dict) and selb.get("preset_id") == (rec or {}).get(
        "preset_id") and selb.get("adapter") == RULE, selb)

    # APPLY
    Ap = lambda cid, ok, d=None: R.check("APPLY", cid, ok, d)  # noqa: E731
    base, app = cap["BASE"], cap["APPLY"]
    roles = A.adm(base, "target").get("roles") or {}
    t_chan = A.adm(base, "target").get("t_chan")
    written = A.adm(base, "target").get("written") or []
    moved = A.changed(A.field(base, "target", "sha256"), A.field(app, "target", "sha256"))
    kinds = sorted(set(roles.get(n) for n in moved))
    R.info["target_channels_changed"] = len(moved)
    Ap("apply.target_changed_on_rig_handle_and_direct_bone_channels", u"handle-written" in kinds and
       u"fk-written" in kinds, kinds)
    Ap("apply.only_drafted_written_channels_changed", moved and set(moved) <= set(written),
       [n for n in moved if n not in written][:8])
    neighbours = []
    kb, ka = A.field(base, "target", "keys"), A.field(app, "target", "keys")
    for n in moved:
        before = [k for layer in kb.get(n) or [] for k in layer]
        after = [k for layer in ka.get(n) or [] for k in layer]
        if [k for k in before if k[0] != t_chan] != [k for k in after if k[0] != t_chan] or \
                len([k for k in after if k[0] == t_chan]) != 1:
            neighbours.append(n)
    Ap("apply.other_keys_unchanged_one_key_at_the_mapped_tick", t_chan is not None and not neighbours,
       neighbours[:8])
    Ap("apply.p7_verified_in_the_cpm_log", any("PROD_POSE_BODY-P7-verified" in l for l in lines))
    au = A.undo(app)
    Ap("apply.one_owned_history_entry", u"%s" % au.get("undo_desc") == u"Apply Pose %s" % (rec or {}).get("name")
       and au.get("can_redo") is False, au)
    tleaf = leaf_channels(base, "target")
    Ap("apply.simulated_leaves_not_authored_by_cpm", len(tleaf) == 2 * LEAVES_EXPECTED and not set(tleaf) & set(
        moved) and not set(tleaf) & set(written), sorted(set(tleaf) & (set(moved) | set(written))))

    # POSTURE
    Q = lambda cid, ok, d=None: R.check("POSTURE", cid, ok, d)  # noqa: E731
    tl = set(leaves(base, "target")) | set(adm_leaves["source"])
    src_pose, dst_pose = A.posture(saved, "source"), A.posture(app, "target")
    common = sorted((set(src_pose) & set(dst_pose)) - tl)
    dp, dq = A.max_difference(src_pose, dst_pose, common)
    classes = A.adm(base, "target").get("bone_classes") or {}
    per = {}
    for cls in ("constrained", "fk"):
        sub = [n for n in common if classes.get(n) == cls]
        per[cls] = dict(zip(("position", "angle_degrees", "bones"), A.max_difference(src_pose, dst_pose, sub) +
                            (len(sub),)))
    R.info["posture"] = {"position": dp, "angle_degrees": dq, "bones": len(common), "by_class": per}
    Q("posture.tails_d_takes_tails_s_saved_body_posture_independently_observed", len(common) == len(
        set(src_pose) - tl) and per["constrained"]["bones"] > 0 and per["fk"]["bones"] > 0 and
      dp <= A.POSTURE_POSITION and dq <= A.POSTURE_ANGLE, R.info["posture"])
    hb, ha = (A.sets(base, "target").get("handles") or {}).get(PLACEMENT), (A.sets(app, "target").get("handles") or
                                                                           {}).get(PLACEMENT)
    mb, ma = A.sets(base, "target").get("model_state"), A.sets(app, "target").get("model_state")
    Q("posture.placement_and_facing_unchanged", hb and ha and mb and ma and A.dist(hb[2], ha[2]) <= A.SAME_POSITION
      and A.angle(hb[3], ha[3]) <= A.SAME_ANGLE and A.dist(mb[2], ma[2]) <= A.SAME_POSITION and
      A.angle(mb[3], ma[3]) <= A.SAME_ANGLE, (hb, ha))
    fk = [n for n in common if classes.get(n) == "fk"]
    bb, ba = A.sets(base, "target").get("bones") or {}, A.sets(app, "target").get("bones") or {}
    offsets = [n for n in fk if A.dist(bb[n][0], ba[n][0]) > A.SAME_POSITION]
    Q("posture.proportions_direct_bone_offsets_kept", fk and not offsets, offsets[:8])

    # HISTORY
    H = lambda cid, ok, d=None: R.check("HISTORY", cid, ok, d)  # noqa: E731
    sh = lambda s: A.field(cap[s], "target", "sha256")  # noqa: E731
    H("navigation.pose_holds_after_moving_away_and_back", sh("NAV") == sh("APPLY") and A.bones_same(
        bones_without(cap["NAV"], "target", tl), bones_without(app, "target", tl)) and A.undo(cap["NAV"]) == au)
    H("undo.target_authored_state_equals_base", sh("UNDO") == sh("BASE"), A.changed(sh("BASE"), sh("UNDO"))[:6])
    H("undo.history", A.undo(cap["UNDO"]).get("undo_desc") == A.undo(base).get("undo_desc") and
      u"%s" % A.undo(cap["UNDO"]).get("redo_desc") == u"Redo %s" % au.get("undo_desc"), A.undo(cap["UNDO"]))
    H("undo.non_leaf_skeleton_back_to_base", A.bones_same(bones_without(cap["UNDO"], "target", tl),
                                                          bones_without(base, "target", tl)))
    H("redo.target_equals_apply", sh("REDO") == sh("APPLY") and A.undo(cap["REDO"]).get("undo_desc") ==
      au.get("undo_desc"), A.undo(cap["REDO"]))

    # LEAVES
    Lv = lambda cid, ok, d=None: R.check("LEAVES", cid, ok, d)  # noqa: E731
    for role in ROLES:
        names_ = leaf_channels(prep, role) if role != "peer" else sorted(
            n for n in A.field(prep, "peer", "to") if (A.field(prep, "peer", "to").get(n) or u"").split(
                u"(")[-1].rstrip(u")") in declared_jiggle(R, "PREP", "peer"))
        ref_a, ref_b = leaf_sha(prep, role, names_), leaf_sha(base, role, names_)
        Lv("%s.leaf_channels_unchanged_at_every_capture" % role, names_ and all(
            leaf_sha(cap[s], role, names_) == (ref_a if s in A_STEPS else ref_b) for s in steps),
           [s for s in steps if leaf_sha(cap[s], role, names_) != (ref_a if s in A_STEPS else ref_b)])
        ref = declarations(R, "PREP", role)
        Lv("%s.leaf_scale_and_header_declaration_unchanged_at_every_capture" % role, ref["declared"] and all(
            declarations(R, s, role) == ref for s in steps), [s for s in steps if declarations(R, s, role) != ref])
    Lv("target.leaves_admitted_as_simulated_leaves_at_every_capture", all(
        leaves(cap[s], "target") == adm_leaves["target"] for s in B_STEPS))
    tips = {}
    for s in ("APPLY", "NAV", "UNDO", "REDO"):
        b0, b1 = A.sets(base, "target").get("bones") or {}, A.sets(cap[s], "target").get("bones") or {}
        tips[s] = max([A.dist(b0[n][0], b1[n][0]) for n in adm_leaves["target"] if n in b0 and n in b1] or [0.0])
    R.info["tip_local_position_change_from_base"] = tips      # uncertainty 1: information only, never gated

    # PEER
    P = lambda cid, ok, d=None: R.check("PEER", cid, ok, d)  # noqa: E731
    for role in ("source", "peer"):
        skip_r = set(adm_leaves["source"]) if role == "source" else set(declared_jiggle(R, "PREP", "peer"))
        P("%s.unchanged_in_process_a" % role, A.field(saved, role, "sha256") == A.field(prep, role, "sha256"))
        P("%s.unchanged_in_process_b" % role, all(
            A.field(cap[s], role, "sha256") == A.field(base, role, "sha256") and A.bones_same(
                bones_without(cap[s], role, skip_r), bones_without(base, role, skip_r)) for s in B_STEPS),
          [s for s in B_STEPS if A.field(cap[s], role, "sha256") != A.field(base, role, "sha256")])
    return refused


def verdict(checks, refused):
    def gate(name):
        mine = [x["pass"] for x in checks if x["gate"] == name]
        return all(mine) if mine else None
    gates = dict((n, gate(n)) for n in GATES)
    if gates["EVIDENCE"] is not True or gates["PREP"] is False:
        v = "INCOMPLETE"
    elif refused:
        v = "REFUSED"
    elif all(g is True for g in gates.values()):
        v = "AUTOMATED PASS"
    elif gates["PREP"] is None:
        v = "INCOMPLETE"
    else:
        v = "FAIL"
    return v, gates


def markdown(out):
    lines = ["# F-01 Stage 2 native Tails qualification: %s" % out["verdict"], "",
             "Qualification CPM `%s` (Stage 2 candidate `%s`). Gates: %s." % (
                 out["identities"].get("qualification_cpm_sha256"), out["identities"].get("candidate_cpm_sha256"),
                 ", ".join("%s %s" % (k, A.gate_text(v)) for k, v in sorted(out["gates"].items()))), ""]
    if out["verdict"] == "AUTOMATED PASS":
        lines += ["**Every automated gate passed. Acceptance also needs the Owner's visual assessment** (useful body "
                  "posture, no severe deformation; minor differences in the simulated ears, hair and tail tips are "
                  "acceptable).", ""]
    elif out["verdict"] == "REFUSED":
        lines += ["**Tails S's Full body was refused: safe, but not a compatibility pass.** Reasons: `%s`" %
                  json.dumps(out["info"].get("refusal"), ensure_ascii=False, default=repr)[:600], ""]
    lines += ["| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in out["checks"]:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False, default=repr)[:300].replace("|", "\\|")
        lines.append("| %s | `%s` | %s | %s |" % (x["gate"], x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    lines += ["", "Info: `%s`" % json.dumps(out["info"], ensure_ascii=False, default=repr)[:1200]]
    return "\n".join(lines) + "\n"


def run(c):
    R = Report(c)
    refused = evaluate(R)
    v, gates = verdict(R.checks, refused)
    out = {"format": "F01-S2T-verdict-v1", "verdict": v, "gates": gates, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in R.checks if not x["pass"]], "info": R.info,
           "analyzer_sha256": A.sha(os.path.abspath(__file__))}
    md = markdown(out)
    for name, data in (("S2T_VERDICT.json", json.dumps(out, indent=1, sort_keys=True, default=repr)),
                       ("S2T_VERDICT.md", md)):
        fd = os.open(R.ev(name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(md)
    return 0 if v == "AUTOMATED PASS" else 1


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import s2t_tool
    return run(s2t_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
