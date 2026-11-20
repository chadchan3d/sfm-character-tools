# -*- coding: utf-8 -*-
"""F-01 RC4: the verdict of the native two-direction Tails cross-rig qualification. Python 3, run with -I after
restore, with SFM closed. It never changes the run.

Reads Q/staged/IDENTITIES.json, Q/observations/S1F-<step>.json, .leaves.json and .offsets.json, Q/evidence (logs,
library_cleanup.json, library_after, restore.json) and Q/sessions. Writes Q/evidence/RC4X_VERDICT.json and
RC4X_VERDICT.md (exclusive create). The Fox analyzer's helpers are reused unchanged.

One SFM process on a disposable copy of the R2 fixture (RC4X_SESSION.dmx), never saved:
  Tails N     a fresh Tails, rigged with the installed rig_biped_simple (23 controls: rig_chest drives bip_spine_3),
              posed and placed away from the others
  original    the session's original Tails (milestailsprower1; 22 controls, bip_spine_3 posed directly), as authored
  peer        the session's original Fox (foxmccouldwm1), never touched
  PREP, SAVED       both poses saved first: "RC4 Chest" from Tails N, "RC4 Sit" from the original
  direction A       "RC4 Chest" applied to the original: A_BASE, A_APPLY, A_NAV, A_UNDO, A_REDO, A_NOOP, A_FINAL
  direction B       "RC4 Sit" applied to Tails N: B_BASE, B_APPLY, B_NAV, B_UNDO, B_REDO, B_NOOP
  ABORT             the armed qualification fault, "RC4 Chest" on the original (after B_NOOP: no Redo pending)
  B_FINAL           the final Undo of direction B
Setup line roles: PREP, SAVED, A_*, ABORT: source Tails N, target the original. B_*: source the original, target
Tails N. The peer is the Fox at every capture.

Gates (a gate with no evaluated check is NOT EVALUATED, never PASS):
  EVIDENCE  identities; every capture from one process with the qualification build, no capture error, complete leaf
            and offsets sidecars; every capture on RC4X_SESSION.dmx in the Motion Editor at one shot and playhead;
            the session copy and the spare never saved; the library changed only by the two Tails poses and their
            local sidecars; library and installation restored exactly; the CPM log collected, with no unverified,
            uncertain, failed-Abort or lockout result
  PREP      the roles as described; Tails N admitted with rig_chest (23 controls, 36 constraints, bip_spine_3
            constrained), the original with 22 controls, 34 constraints and bip_spine_3 posed directly; Tails N posed
            and placed visibly differently
  SAVE      two version 2 structural records (revision 2): RC4 Chest with Tails N's written set, RC4 Sit with the
            original's; Save read-only
  ADAPT     both Applies adapted (CPM's BODY-RIG-adapted: bip_spine_3 to FK in A, to constrained in B); the actual
            destination offsets against each record within Astra's bounds (0.005 degrees, 0.0001 units) and logged
            by CPM with those limits; the measured maxima are recorded
  A_* / B_* APPLY: only the destination's drafted written channels changed, rig handle and direct bone channels, one
            key at the mapped tick and every other key unchanged; P7 verified; one owned history entry; simulated
            leaves never authored. POSTURE: independent of CPM, every non-leaf bone of the destination relative to its
            own placement handle matches the source's saved posture (0.05 units, 0.5 degrees; maxima reported);
            placement, facing and direct bone offsets unchanged. HISTORY: navigation away and back keeps the authored
            pose and skeleton (an SFM "Modify Time Selection" entry is recorded, never gated); Undo restores BASE with
            the Apply's Redo entry; Redo restores APPLY; a repeated Apply is a reported no-op; the final Undo restores
            BASE
  ABORT     one injected failure after writes, a verified Abort with no Redo cleared; the original exactly as at
            A_FINAL and Tails N exactly as at B_NOOP; the Undo state exactly B_NOOP's; the fault slot consumed
  PEER      the Fox unchanged at every capture; the direction's source unchanged during its Apply (authored state
            exactly, non-leaf skeleton within 0.001 units and 0.01 degrees)
Verdict: AUTOMATED PASS (every gate; acceptance also needs the Owner's visual assessment); FAIL (complete evidence, a
functional gate failed); INCOMPLETE (evidence, preparation or restoration missing or failed).

usage: python -I rc4x_analyze.py RC4X.json      (or: rc4x_tool.py RC4X.json analyze)
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

DIRECTION = ("BASE", "APPLY", "NAV", "UNDO", "REDO", "NOOP", "FINAL")
A_STEPS = tuple("A_" + s for s in DIRECTION)
B_STEPS = tuple("B_" + s for s in DIRECTION if s != "FINAL") + ("ABORT", "B_FINAL")
STEPS = ("PREP", "SAVED") + A_STEPS + B_STEPS
ROLES = A.ROLES
SESSION = "RC4X_SESSION.dmx"
SPARE = "RC4X_SPARE.dmx"
MODEL = "models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl"
ORIGINAL = u"milestailsprower1"
PEER = u"foxmccouldwm1"
RULE = {"rule": "structural_rig_v1", "revision": 2}
CHEST, SIT = u"RC4 Chest", u"RC4 Sit"
LEAF = u"simulated-leaf"
PLACEMENT = A.PLACEMENT
SPINE = u"bip_spine_3"
ROTATION_LIMIT, VECTOR_LIMIT = 0.005, 0.0001          # Astra's numerical compatibility ruling (inclusive)
NAV_ENTRY = u"Modify Time Selection"
BAD_LOG = A.BAD_LOG + ("PROD_POSE_RECOVERY_BLOCKED", "recovery-blocked", "committed-unverified")
GATES = ("EVIDENCE", "PREP", "SAVE", "ADAPT", "A_APPLY", "A_POSTURE", "A_HISTORY", "B_APPLY", "B_POSTURE",
         "B_HISTORY", "ABORT", "PEER")
LEAVES_FORMAT, OFFSETS_FORMAT = "F01-S2T-leaves-v1", "F01-RC4X-offsets-v1"


class Report(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.info = [], {}
        self.ids = A.opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap, self.side, self.off = {}, {}, {}
        for step in STEPS:
            obs = os.path.join(self.q, "observations")
            data = A.opt_json(os.path.join(obs, "S1F-%s.json" % step))
            if isinstance(data, dict) and isinstance(data.get("pid"), int):
                self.cap[step] = data
            for store, suffix in ((self.side, "leaves"), (self.off, "offsets")):
                x = A.opt_json(os.path.join(obs, "S1F-%s.%s.json" % (step, suffix)))
                if isinstance(x, dict):
                    store[step] = x

    def check(self, gate, cid, ok, detail=None):
        self.checks.append({"gate": gate, "id": cid, "pass": bool(ok), "detail": None if ok else detail})
        return ok

    def ev(self, *parts):
        return os.path.join(self.q, "evidence", *parts)


# --- helpers ---------------------------------------------------------------------------------------------------------

def sidecar_ok(R, store, fmt, step):
    side, cap = store.get(step) or {}, R.cap.get(step) or {}
    sets = side.get("sets") or {}
    return (side.get("format") == fmt and side.get("step") == step and side.get("pid") == cap.get("pid") and
            side.get("names") == cap.get("names") and all((sets.get(r) or {}).get("status") == "READ" for r in ROLES))


def leaves(cap, role):
    return sorted(n for n, c in (A.adm(cap, role).get("bone_classes") or {}).items() if c == LEAF)


def leaf_channels(cap, role):
    return sorted(n for n, r in (A.adm(cap, role).get("roles") or {}).items() if r == LEAF)


def bones_without(cap, role, skip):
    return dict((n, b) for n, b in (A.sets(cap, role).get("bones") or {}).items() if n not in skip)


def saved_records(R):
    out = {}
    for path in sorted(glob.glob(R.ev("library_after", "Characters", "*", "Poses", "*.json"))):
        rec = A.opt_json(path)
        if isinstance(rec, dict):
            out[rec.get("name")] = rec
    return out


def offsets_against(record, live_rows):
    """The largest angle and distance between a record's constraint offsets and the destination's actual offsets,
    over the common constraints (identities as in CPM), with the per-field rows."""
    import math
    rows = dict((r.get("identity"), r) for r in live_rows or [])
    desc = (((record or {}).get("pose") or {}).get("regions") or {}).get("full_body", {}).get("descriptor") or {}
    out = []
    for c in desc.get("constraints") or []:
        ident = json.dumps([c.get("type"), c.get("slaves"), c.get("targets"), c.get("pole")], sort_keys=True,
                           separators=(",", ":"))
        d = rows.get(ident)
        if d is None:
            continue
        for group, name in (("solver", "startOffset"), ("solver", "midOffset"), ("offsets", "oOffset")):
            a, b = (c.get(group) or {}).get(name), (d.get(group) or {}).get(name)
            if isinstance(a, dict) and isinstance(b, dict) and a.get("present") and b.get("present"):
                out.append({"constraint": ident, "field": name, "angle_deg": A.angle(a["value"], b["value"])})
        a, b = (c.get("offsets") or {}).get("vecOffset"), (d.get("offsets") or {}).get("vecOffset")
        if isinstance(a, dict) and isinstance(b, dict) and a.get("present") and b.get("present"):
            out.append({"constraint": ident, "field": "vecOffset", "distance": math.sqrt(sum(
                (x - y) ** 2 for x, y in zip(a["value"], b["value"])))})
    angles = [r["angle_deg"] for r in out if "angle_deg" in r]
    dists = [r["distance"] for r in out if "distance" in r]
    return {"max_angle_deg": max(angles or [0.0]), "max_distance": max(dists or [0.0]), "compared": len(out),
            "largest": sorted(out, key=lambda r: -r.get("angle_deg", r.get("distance", 0.0) * 1000))[:4]}


def library_and_restore(R):
    clean = A.opt_json(R.ev("library_cleanup.json")) or {}
    diffs = clean.get("differences_kept_in_evidence") or []
    poses = [x for x in diffs if "/Poses/" in x["path"]]
    allowed = lambda x: x["status"] == "added" and (  # noqa: E731
        re.match(r"^Characters/milestailsprower[^/]*/Poses/[^/]+\.json$", x["path"]) or
        re.match(r"^Characters/milestailsprower[^/]*/(character\.json|pose_sources\.json|pose_rigs\.json)"
                 r"(\.bak)?$", x["path"]))
    unexpected = [x for x in diffs if not allowed(x)]
    R.check("EVIDENCE", "library.changed_only_by_the_two_tails_poses", bool(clean) and not unexpected and
            len(poses) == 2, {"unexpected": unexpected, "poses": [p["path"] for p in poses]})
    R.check("EVIDENCE", "restore.library_exactly_as_before", clean.get("files_equal_pre") is True and
            clean.get("folders_equal_pre") is True)
    restore = A.opt_json(R.ev("restore.json")) or {}
    R.check("EVIDENCE", "restore.published_and_inventories_equal", restore.get("restored") is True,
            restore.get("inventory_problems"))


def adapted_lines(lines):
    return [A.log_json(l, "PROD_POSE_BODY-RIG-adapted") for l in lines if "PROD_POSE_BODY-RIG-adapted" in l]


# --- one direction -------------------------------------------------------------------------------------------------

def direction(R, d, src_cap, src_role, record, lines):
    cap = R.cap
    st = lambda s: cap["%s_%s" % (d, s)]  # noqa: E731
    G = lambda gate, cid, ok, detail=None: R.check("%s_%s" % (d, gate), cid, ok, detail)  # noqa: E731
    base, app = st("BASE"), st("APPLY")
    roles = A.adm(base, "target").get("roles") or {}
    t_chan = A.adm(base, "target").get("t_chan")
    written = A.adm(base, "target").get("written") or []
    moved = A.changed(A.field(base, "target", "sha256"), A.field(app, "target", "sha256"))
    kinds = sorted(set(roles.get(n) for n in moved))
    G("APPLY", "apply.rig_handle_and_direct_bone_channels_changed", u"handle-written" in kinds and
      u"fk-written" in kinds, kinds)
    G("APPLY", "apply.only_drafted_written_channels_changed", moved and set(moved) <= set(written),
      [n for n in moved if n not in written][:8])
    bad, neighbours = [], 0
    kb, ka = A.field(base, "target", "keys"), A.field(app, "target", "keys")
    for n in moved:
        before = [k for layer in kb.get(n) or [] for k in layer]
        after = [k for layer in ka.get(n) or [] for k in layer]
        neighbours += len([k for k in before if k[0] != t_chan])
        if [k for k in before if k[0] != t_chan] != [k for k in after if k[0] != t_chan] or \
                len([k for k in after if k[0] == t_chan]) != 1:
            bad.append(n)
    R.info["%s_neighbour_keys_kept" % d] = neighbours
    G("APPLY", "apply.neighbouring_keys_unchanged_one_key_at_the_mapped_tick", t_chan is not None and not bad, bad[:8])
    unmoved = [n for n in A.chans(base, "target") if n not in moved]
    G("APPLY", "apply.every_other_channel_of_the_destination_unchanged", all(
        A.field(base, "target", "sha256").get(n) == A.field(app, "target", "sha256").get(n) for n in unmoved))
    au = A.undo(app)
    label = u"Apply Pose %s" % record.get("name")
    G("APPLY", "apply.one_owned_history_entry", u"%s" % au.get("undo_desc") == label, au)
    tleaf = leaf_channels(base, "target")
    G("APPLY", "apply.simulated_leaves_not_authored_by_cpm", tleaf and not set(tleaf) & (set(moved) | set(written)),
      sorted(set(tleaf) & (set(moved) | set(written))))
    # POSTURE
    skip = set(leaves(base, "target")) | set(leaves(src_cap, src_role))
    src_pose, dst_pose = A.posture(src_cap, src_role), A.posture(app, "target")
    common = sorted((set(src_pose) & set(dst_pose)) - skip)
    dp, dq = A.max_difference(src_pose, dst_pose, common)
    classes = A.adm(base, "target").get("bone_classes") or {}
    per = {}
    for cls in ("constrained", "fk"):
        sub = [n for n in common if classes.get(n) == cls]
        per[cls] = dict(zip(("position", "angle_degrees", "bones"), A.max_difference(src_pose, dst_pose, sub) +
                            (len(sub),)))
    spine = A.max_difference(src_pose, dst_pose, [SPINE]) if SPINE in common else None
    R.info["%s_posture" % d] = {"position": dp, "angle_degrees": dq, "bones": len(common), "by_class": per,
                                SPINE: spine}
    G("POSTURE", "posture.destination_takes_the_saved_posture_independently_observed", len(common) == len(
        set(src_pose) - skip) and per["constrained"]["bones"] > 0 and per["fk"]["bones"] > 0 and
      dp <= A.POSTURE_POSITION and dq <= A.POSTURE_ANGLE, R.info["%s_posture" % d])
    G("POSTURE", "posture.converted_spine_reproduced", spine is not None and spine[0] <= A.POSTURE_POSITION and
      spine[1] <= A.POSTURE_ANGLE, spine)
    hb = (A.sets(base, "target").get("handles") or {}).get(PLACEMENT)
    ha = (A.sets(app, "target").get("handles") or {}).get(PLACEMENT)
    mb, ma = A.sets(base, "target").get("model_state"), A.sets(app, "target").get("model_state")
    G("POSTURE", "posture.placement_and_facing_unchanged", hb and ha and mb and ma and A.dist(hb[2], ha[2]) <=
      A.SAME_POSITION and A.angle(hb[3], ha[3]) <= A.SAME_ANGLE and A.dist(mb[2], ma[2]) <= A.SAME_POSITION and
      A.angle(mb[3], ma[3]) <= A.SAME_ANGLE, (hb, ha))
    fk = [n for n in common if classes.get(n) == "fk"]
    bb, ba = A.sets(base, "target").get("bones") or {}, A.sets(app, "target").get("bones") or {}
    offsets = [n for n in fk if A.dist(bb[n][0], ba[n][0]) > A.SAME_POSITION]
    G("POSTURE", "posture.proportions_direct_bone_offsets_kept", fk and not offsets, offsets[:8])
    # HISTORY
    sh = lambda s: A.field(st(s), "target", "sha256")  # noqa: E731
    nav = A.undo(st("NAV"))
    R.info["%s_navigation_entry" % d] = nav.get("undo_desc")
    G("HISTORY", "navigation.pose_holds_after_moving_away_and_back", sh("NAV") == sh("APPLY") and A.bones_same(
        bones_without(st("NAV"), "target", skip), bones_without(app, "target", skip)) and
      u"%s" % nav.get("undo_desc") in (label, NAV_ENTRY), nav)
    G("HISTORY", "undo.restores_base_with_the_apply_redo_entry", sh("UNDO") == sh("BASE") and
      u"%s" % A.undo(st("UNDO")).get("redo_desc") == u"Redo %s" % label and A.bones_same(
          bones_without(st("UNDO"), "target", skip), bones_without(base, "target", skip)), A.undo(st("UNDO")))
    G("HISTORY", "redo.restores_apply", sh("REDO") == sh("APPLY") and u"%s" % A.undo(st("REDO")).get(
        "undo_desc") == label, A.undo(st("REDO")))
    G("HISTORY", "noop.writes_nothing_and_adds_no_entry", sh("NOOP") == sh("REDO") and A.undo(st("NOOP")) ==
      A.undo(st("REDO")), A.undo(st("NOOP")))
    G("HISTORY", "final_undo.restores_base", sh("FINAL") == sh("BASE") and u"%s" % A.undo(st("FINAL")).get(
        "redo_desc") == u"Redo %s" % label, A.undo(st("FINAL")))
    return au


def evaluate(R):
    cap, c = R.cap, R.c
    E = lambda cid, ok, d=None: R.check("EVIDENCE", cid, ok, d)  # noqa: E731
    want = c["pins"]["qualification_cpm_sha256"]
    E("identity.qualification_build", R.ids.get("qualification_cpm_sha256") == want and
      R.ids.get("candidate_cpm_sha256") == c["pins"]["candidate_cpm_sha256"], R.ids.get("qualification_cpm_sha256"))
    for step in STEPS:
        if not E("captured.%s" % step, step in cap):
            continue
        d = cap[step]
        E("cpm.%s" % step, d.get("cpm_build_sha256") == want and d.get("registry_mode") == u"qualification",
          (d.get("cpm_build_sha256"), d.get("registry_mode")))
        E("errors.%s" % step, not d.get("errors") and all(r in (d.get("sets") or {}) for r in ROLES), d.get("errors"))
        E("sidecars.%s" % step, sidecar_ok(R, R.side, LEAVES_FORMAT, step) and sidecar_ok(R, R.off, OFFSETS_FORMAT,
                                                                                          step))
    session, spare = os.path.join(R.q, "sessions", SESSION), os.path.join(R.q, "sessions", SPARE)
    E("sessions.session_copy_never_saved", os.path.isfile(session) and A.sha(session) == c["pins"]["r2_fixture_sha256"])
    E("sessions.spare_never_saved", os.path.isfile(spare) and A.sha(spare) == c["pins"]["destination_sha256"])
    library_and_restore(R)
    lines = A.logs(R)
    E("log.collected", bool(lines))
    bad = [l for l in lines if any(b in l for b in BAD_LOG)]
    E("log.no_unverified_uncertain_failed_abort_or_lockout_result", not bad, bad[:4])
    if any(s not in cap for s in STEPS):
        return
    E("process.one_sfm_process", len(set(cap[s]["pid"] for s in STEPS)) == 1)
    docs = set(u"%s" % ((cap[s].get("session") or {}).get("document") or u"") for s in STEPS)
    E("process.every_capture_on_the_disposable_session", len(docs) == 1 and list(docs)[0].lower().replace(
        "\\", "/").endswith(SESSION.lower()), sorted(docs))
    heads = [(cap[s].get("session") or {}).get("head_seconds") for s in STEPS]
    shots = set(u"%s" % (cap[s].get("session") or {}).get("shot") for s in STEPS)
    modes = set(u"%s" % (cap[s].get("session") or {}).get("timeline_mode") for s in STEPS)
    E("session.same_shot_and_playhead_motion_editor", len(shots) == 1 and all(h == heads[0] for h in heads) and
      modes == set([u"2"]), (sorted(shots), heads, sorted(modes)))

    # PREP
    Pp = lambda cid, ok, d=None: R.check("PREP", cid, ok, d)  # noqa: E731
    prep = cap["PREP"]
    n = cap["PREP"].get("names") or {}
    tails_n = n.get("source")
    a_roles = all((cap[s].get("names") or {}) == {"source": tails_n, "target": ORIGINAL, "peer": PEER}
                  for s in ("PREP", "SAVED", "ABORT") + A_STEPS)
    b_roles = all((cap[s].get("names") or {}) == {"source": ORIGINAL, "target": tails_n, "peer": PEER}
                  for s in B_STEPS if s != "ABORT")
    Pp("prep.roles_as_described", tails_n and tails_n not in (ORIGINAL, PEER) and a_roles and b_roles,
       dict((s, cap[s].get("names")) for s in STEPS))
    models = dict((r, (u"%s" % A.sets(prep, r).get("model")).replace("\\", "/").lower()) for r in ROLES)
    Pp("prep.two_tails_and_the_fox_peer", models["source"] == MODEL and models["target"] == MODEL and
       "foxmccouldwm" in models["peer"], models)
    a_new, a_old = A.adm(prep, "source"), A.adm(prep, "target")
    R.info["rigs"] = {"tails_n": (a_new.get("rig_name"), a_new.get("handles"), a_new.get("constraints")),
                      "original": (a_old.get("rig_name"), a_old.get("handles"), a_old.get("constraints"))}
    Pp("prep.tails_n_has_the_chest_control_rig", a_new.get("handles") == 23 and a_new.get("constraints") == 36 and
       (a_new.get("bone_classes") or {}).get(SPINE) == u"constrained", R.info["rigs"])
    Pp("prep.original_has_the_direct_spine_rig", a_old.get("handles") == 22 and a_old.get("constraints") == 34 and
       (a_old.get("bone_classes") or {}).get(SPINE) == u"fk", R.info["rigs"])
    skip = set(leaves(prep, "source")) | set(leaves(prep, "target"))
    ps, pt = A.posture(prep, "source"), A.posture(prep, "target")
    dp, dq = A.max_difference(ps, pt, sorted((set(ps) & set(pt)) - skip))
    hs = A.world((A.sets(prep, "source").get("handles") or {}).get(PLACEMENT) or [[0.0] * 3, [0, 0, 0, 1]] * 2)
    ht = A.world((A.sets(prep, "target").get("handles") or {}).get(PLACEMENT) or [[0.0] * 3, [0, 0, 0, 1]] * 2)
    Pp("prep.tails_n_posed_and_placed_visibly_differently", dq > A.VISIBLE_ANGLE and (
        A.dist(hs[0], ht[0]) > A.VISIBLE_DISTANCE or A.angle(hs[1], ht[1]) > A.VISIBLE_ANGLE),
       {"posture_angle": dq, "placement_distance": A.dist(hs[0], ht[0])})

    # SAVE
    V = lambda cid, ok, d=None: R.check("SAVE", cid, ok, d)  # noqa: E731
    recs = saved_records(R)
    chest, sit = recs.get(CHEST) or {}, recs.get(SIT) or {}

    def values(rec):
        region = (((rec.get("pose") or {}).get("regions") or {}).get("full_body")) or {}
        return sorted(list(region.get("positions") or {}) + list(region.get("orientations") or {}))
    for rec, role, label in ((chest, "source", "rc4_chest_from_tails_n"), (sit, "target", "rc4_sit_from_original")):
        pose = rec.get("pose") or {}
        V("save.%s_is_a_structural_record_with_its_written_set" % label, pose.get("version") == 2 and
          pose.get("adapter") == RULE and (u"%s" % (pose.get("source") or {}).get("model_ref")).lower() == MODEL and
          values(rec) == sorted(A.adm(prep, role).get("written") or []),
          {"adapter": pose.get("adapter"), "written": len(values(rec))})
    V("save.read_only", all(A.field(cap["SAVED"], r, "sha256") == A.field(prep, r, "sha256") for r in ROLES))

    # ADAPT
    D = lambda cid, ok, d=None: R.check("ADAPT", cid, ok, d)  # noqa: E731
    adapted = adapted_lines(lines)
    conv = [((x or {}).get("converted") or [{}])[0] for x in adapted]
    D("adapt.both_applies_adapted_the_spine_both_ways", {"bone": SPINE, "destination": "fk"} in conv and
      {"bone": SPINE, "destination": "constrained"} in conv, adapted[:4])
    actual = {"A": offsets_against(chest, ((R.off.get("A_BASE") or {}).get("sets") or {}).get("target", {}).get(
        "constraints")), "B": offsets_against(sit, ((R.off.get("B_BASE") or {}).get("sets") or {}).get(
            "target", {}).get("constraints"))}
    R.info["actual_destination_offsets"] = actual
    D("adapt.actual_destination_offsets_within_the_bounds", all(
        x["compared"] > 0 and x["max_angle_deg"] <= ROTATION_LIMIT and x["max_distance"] <= VECTOR_LIMIT
        for x in actual.values()), actual)
    eq = [A.log_json(l, "PROD_POSE_BODY-rotation-equivalent") for l in lines if "rotation-equivalent" in l]
    D("adapt.cpm_logged_the_bounded_comparison", any((x or {}).get("limit_deg") == ROTATION_LIMIT for x in eq) or
      all(x["max_angle_deg"] <= 0.0005 for x in actual.values()), eq[:2])

    # The two directions.
    direction(R, "A", cap["SAVED"], "source", chest, lines)
    au_b = direction(R, "B", cap["SAVED"], "target", sit, lines)
    R.check("A_APPLY", "apply.p7_verified_in_the_cpm_log", len([l for l in lines if "PROD_POSE_BODY-P7-verified" in l])
            >= 2)
    R.check("A_HISTORY", "noop.reported_by_cpm_twice", len([l for l in lines if "PROD_POSE_BODY-P1" in l and
                                                            '"noop": true' in l]) == 2)

    # ABORT
    X = lambda cid, ok, d=None: R.check("ABORT", cid, ok, d)  # noqa: E731
    failures = [A.log_json(l, "PROD_POSE_BODY-P3-P6-failure") for l in lines if "PROD_POSE_BODY-P3-P6-failure" in l]
    fail = failures[0] if len(failures) == 1 else None
    R.info["abort"] = fail
    X("abort.injected_after_adapted_writes", isinstance(fail, dict) and A.FAULT_TEXT in u"%s" % fail.get("error") and
      fail.get("finished") is False and isinstance(fail.get("written"), int) and fail.get("written") > 0, fail)
    verified = [A.log_json(l, "PROD_POSE_BODY-abort-verified") for l in lines if "BODY-abort-verified" in l]
    v = (verified[0] or {}) if len(verified) == 1 else {}
    R.info["abort_redo_cleared"] = v.get("redo_cleared")
    X("abort.verified_by_cpm", len(verified) == 1 and v.get("problems") == [] and v.get("redo_cleared") in (
        True, False), verified)
    ab = cap["ABORT"]
    X("abort.original_exactly_as_before", A.field(ab, "target", "sha256") == A.field(cap["A_FINAL"], "target",
                                                                                     "sha256"))
    # The Undo state: exactly B_NOOP's; or, when SFM discarded a pending Redo entry as the action started (a
    # navigation "Modify Time Selection" entry undone at B_UNDO), B_NOOP's with no Redo (Stage 1's adjudicated rule).
    want = dict(A.undo(cap["B_NOOP"]))
    if v.get("redo_cleared") is True:
        want.update({"can_redo": False, "redo_desc": u""})
    X("abort.tails_n_and_history_untouched", A.field(ab, "source", "sha256") == A.field(cap["B_NOOP"], "target",
                                                                                        "sha256") and
      A.undo(ab) == want and (v.get("redo_cleared") is not True or A.undo(cap["B_NOOP"]).get("can_redo") is True),
      (A.undo(ab), want))
    X("abort.fault_slot_consumed", ab.get("qualification_fault") == [None], ab.get("qualification_fault"))

    # PEER
    P = lambda cid, ok, d=None: R.check("PEER", cid, ok, d)  # noqa: E731
    P("fox.unchanged_at_every_capture", all(A.field(cap[s], "peer", "sha256") == A.field(prep, "peer", "sha256") and
                                            A.bones_same(A.sets(cap[s], "peer").get("bones") or {},
                                                         A.sets(prep, "peer").get("bones") or {}) for s in STEPS),
      [s for s in STEPS if A.field(cap[s], "peer", "sha256") != A.field(prep, "peer", "sha256")])
    skip_n = set(leaves(prep, "source"))
    P("tails_n.unchanged_through_direction_a", all(
        A.field(cap[s], "source", "sha256") == A.field(prep, "source", "sha256") and A.bones_same(
            bones_without(cap[s], "source", skip_n), bones_without(prep, "source", skip_n)) for s in A_STEPS))
    skip_o = set(leaves(prep, "target"))
    P("original_unchanged_through_direction_b", all(
        A.field(cap[s], "source", "sha256") == A.field(cap["A_FINAL"], "target", "sha256") and A.bones_same(
            bones_without(cap[s], "source", skip_o), bones_without(cap["A_FINAL"], "target", skip_o))
        for s in B_STEPS if s != "ABORT"))
    P("original_back_to_as_authored_after_direction_a", A.field(cap["A_FINAL"], "target", "sha256") == A.field(
        prep, "target", "sha256"))
    P("tails_n_back_to_its_pose_after_direction_b", A.field(cap["B_FINAL"], "target", "sha256") == A.field(
        prep, "source", "sha256"))


def verdict(checks):
    def gate(name):
        mine = [x["pass"] for x in checks if x["gate"] == name]
        return all(mine) if mine else None
    gates = dict((n, gate(n)) for n in GATES)
    if gates["EVIDENCE"] is not True or gates["PREP"] is not True:
        v = "INCOMPLETE"
    elif all(g is True for g in gates.values()):
        v = "AUTOMATED PASS"
    elif any(g is None for g in gates.values()):
        v = "INCOMPLETE"
    else:
        v = "FAIL"
    return v, gates


def markdown(out):
    lines = ["# F-01 RC4 native two-direction Tails cross-rig qualification: %s" % out["verdict"], "",
             "Qualification CPM `%s` (RC4 candidate `%s`). Gates: %s." % (
                 out["identities"].get("qualification_cpm_sha256"), out["identities"].get("candidate_cpm_sha256"),
                 ", ".join("%s %s" % (k, A.gate_text(v)) for k, v in sorted(out["gates"].items()))), ""]
    if out["verdict"] == "AUTOMATED PASS":
        lines += ["**Every automated gate passed. Acceptance also needs the Owner's visual assessment** (useful body "
                  "posture in both directions, no severe deformation; minor differences in the simulated ear, hair "
                  "and tail tips are acceptable).", ""]
    lines += ["| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in out["checks"]:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False, default=repr)[:300].replace("|", "\\|")
        lines.append("| %s | `%s` | %s | %s |" % (x["gate"], x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    lines += ["", "Info: `%s`" % json.dumps(out["info"], ensure_ascii=False, default=repr)[:2000]]
    return "\n".join(lines) + "\n"


def run(c):
    R = Report(c)
    evaluate(R)
    v, gates = verdict(R.checks)
    out = {"format": "F01-RC4X-verdict-v1", "verdict": v, "gates": gates, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in R.checks if not x["pass"]], "info": R.info,
           "analyzer_sha256": A.sha(os.path.abspath(__file__))}
    md = markdown(out)
    for name, data in (("RC4X_VERDICT.json", json.dumps(out, indent=1, sort_keys=True, default=repr)),
                       ("RC4X_VERDICT.md", md)):
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
    import rc4x_tool
    return run(rc4x_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
