# -*- coding: utf-8 -*-
"""F-01 H1 (generic procedural-helper compatibility): offline acceptance of the narrow engine-helper rule in the CPM
application source. Authority: Blueprint R4 sections 7, 8, 9 and 12 H; "F-01 H1 - Generic Procedural-Helper
Compatibility".

Technique: the scoped-pose suite's harness (test_cpm_app_f01_scoped: verbatim extraction, fake_sfm_scoped.World) on
the native MC-01 Heavy fixture (no rig; 77 direct-FK bones and the control-less hlp_forearm_L/R), with a fake studio
header on the game model shaped like the native NQ-S6 / NQ-03 reads (bone 77/78 QUATINTERP, flags 7172, parents
bip_lowerArm_L/R; 13 attachments on other bones; no bone flex driver) and the vs.studio constants read natively.
Nothing here demonstrates native SFM behaviour.

Sections: A admission and refusal by mechanism (pure rule and end-to-end inventory), B a renamed, structurally
equivalent rig, C Save and the record, D Apply (planned writes only, helper authorship protected, Undo/Redo, no-op,
verified Abort), E concrete dangerous consumers, F P2/P7 relationship changes, G record and legacy compatibility.

Usage: --phase=run (Python 2.7.5 and Python 3.10.6).
"""
from __future__ import print_function

import copy
import os
import shutil
import sys
import tempfile
import traceback
import types

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_f01_scoped as SC  # noqa: E402
import fake_sfm_body as FB  # noqa: E402
import fake_sfm_scoped as FS  # noqa: E402

check, outcome, refused = SC.check, SC.outcome, SC.refused
HELPERS = (u"hlp_forearm_L", u"hlp_forearm_R")
HEAVY_ATTACHMENTS = (6, 6, 6, 1, 29, 30, 6, 6, 6, 6, 27, 28, 3)      # NQ-03 NQ03-01, tf/models/player/heavy.mdl
CONSTANTS = {"STUDIO_PROC_QUATINTERP": 2, "STUDIO_PROC_JIGGLE": 5, "BONE_PHYSICALLY_SIMULATED": 1,
             "BONE_PHYSICS_PROCEDURAL": 2, "BONE_ALWAYS_PROCEDURAL": 4, "BONE_SCREEN_ALIGN_SPHERE": 8,
             "BONE_SCREEN_ALIGN_CYLINDER": 16}
QUAT_FLAGS = 7172                                                     # 0x1C04, NQ-S6 / NQ-03


class Obj(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Bone(object):
    def __init__(self, name, parent, flags, proctype):
        self.name, self.parent, self.flags, self.proctype = name, parent, flags, proctype

    def pszName(self):
        return self.name


class Header(object):
    """studiohdr_t as the native reads use it (attributes and methods by the same names)."""

    def __init__(self, rows, attachments, drivers, reads):
        self.rows, self.attachments, self.drivers, self.reads = rows, list(attachments), list(drivers), reads
        self.numbones = len(rows)
        self.numlocalattachments = len(self.attachments)
        self.checksum = 1234

    def pBone(self, i):
        self.reads.append(("pBone", i))
        r = self.rows[i]
        return Bone(r["name"], r["parent"], r["flags"], r["proctype"])

    def pLocalAttachment(self, i):
        return Obj(localbone=self.attachments[i])

    def BoneFlexDriverCount(self):
        return len(self.drivers)

    def BoneFlexDriver(self, i):
        return Obj(m_nBoneIndex=self.drivers[i])


def header_rows(fx, declared=None):
    """Header rows from the fixture skeleton: the given bones declared (proctype, flags), every other bone plain."""
    declared = dict((n, (2, QUAT_FLAGS)) for n in HELPERS if n in fx[u"bones"]) if declared is None else declared
    index = dict((n, b[u"index"]) for n, b in fx[u"bones"].items())
    rows = [None] * len(index)
    for n, b in fx[u"bones"].items():
        proc, flags = declared.get(n, (0, 0x100))
        rows[b[u"index"]] = {"name": n, "parent": index[b[u"parent"]] if b[u"parent"] else -1, "flags": flags,
                             "proctype": proc}
    return rows


def attach(w, rows=None, attachments=HEAVY_ATTACHMENTS, drivers=(), studio=True):
    """The native header and constants on a world (rows None: derived from the world's fixture)."""
    reads = []
    hdr = Header(rows if rows is not None else header_rows(w.fx), attachments, drivers, reads)
    w.gm.GetStudioHdr = lambda: hdr
    w.studio_constants = dict(CONSTANTS) if studio else {}
    return hdr


def use(ns, w, fx=None):
    SC.use(ns, w, fx)
    if hasattr(w, "studio_constants"):
        mod = types.ModuleType("vs.studio")
        for k, v in w.studio_constants.items():
            setattr(mod, k, v)
        ns["vs"].studio = mod
        ns["vs"].studio_owner = w


def heavy_world(fx, **kw):
    w = FS.World(fx)
    attach(w, **kw)
    return w


def state(ns):
    row = ns["prod_resolve_instance"](SC.context(ns)["instance"])
    return ns["prod_scope_state"](row)


def all_keys(w):
    return SC.all_keys(w)


# ---------------------------------------------------------------------------
# A. admission and refusal by mechanism
# ---------------------------------------------------------------------------

def section_admission(ns, heavy):
    w = heavy_world(heavy)
    use(ns, w, heavy)
    st = state(ns)
    check("A.native_shaped_header_admits_exactly_the_two_declared_helpers",
          st[u"helpers"] == list(HELPERS) and st[u"helper_refusals"] == {}, (st[u"helpers"], st[u"helper_refusals"]))
    check("A.helpers_stay_carried_candidates_in_the_classification_never_constant",
          all(st[u"C"][u"bones"][n][u"class"] == u"carried-candidate" for n in HELPERS))
    inv = SC.inventory(ns)
    check("A.heavy_full_body_is_available", inv[u"full_body"][u"status"] == u"available" and
          inv[u"helpers"] == list(HELPERS), inv[u"full_body"])
    summary = ns["prod_scope_summary"](u"full_body", inv)
    check("A.save_summary_has_no_helper_sentence_rc1_ui_corrections",
          summary == u"Facial expressions and the rootTransform are not saved." and
          ns["PROD_SCOPE_HELPER_NOTE"] not in summary and u"Helper bones" not in summary, summary)
    check("A.header_is_read_only_through_the_named_accessors",
          [r for r in w.calls if r[0] in ("SetKeyValue", "InsertKeyAtTime", "SetValue")] == [] and not w.dm.calls)

    # Fail-closed evidence: no header, an unreadable header, missing constants.
    for label, prepare in (
            (u"no_header_accessor", lambda w: delattr(w.gm, "GetStudioHdr")),
            (u"header_raises", lambda w: setattr(w.gm, "GetStudioHdr", lambda: (_ for _ in ()).throw(
                RuntimeError("unreadable")))),
            (u"header_none", lambda w: setattr(w.gm, "GetStudioHdr", lambda: None)),
            (u"constants_missing", lambda w: setattr(w, "studio_constants", {}))):
        w = heavy_world(heavy)
        prepare(w)
        use(ns, w, heavy)
        inv = SC.inventory(ns)
        check("A.%s_admits_nothing_and_full_body_refuses_as_before" % label,
              inv[u"helpers"] == [] and inv[u"full_body"][u"code"] == u"carried-unsupported", inv[u"full_body"])

    # The pure rule, one criterion at a time, on the native D/C.
    w = heavy_world(heavy)
    use(ns, w, heavy)
    st = state(ns)
    D, C = st[u"D"], st[u"C"]
    rule = ns["prod_scope_helper_admission"]
    evidence = ns["prod_scope_helper_evidence"](st[u"L"])
    check("A.evidence_reads_79_bones_13_attachments_no_flex_drivers",
          evidence[u"status"] == u"READ" and len(evidence[u"bones"]) == 79 and evidence[u"flex_drivers"] == [] and
          evidence[u"attachments"] == sorted(set(HEAVY_ATTACHMENTS)), evidence.get(u"reason"))

    def variant(change):
        H = copy.deepcopy(evidence)
        change(H)
        return rule(D, C, H)
    left = heavy[u"bones"][u"hlp_forearm_L"][u"index"]

    def row(H, n=left):
        return [r for r in H[u"bones"] if r[u"index"] == n][0]
    cases = (
        (u"jiggle_procedure", lambda H: row(H).update(proctype=5), u"not a declared QUATINTERP helper"),
        (u"not_procedural", lambda H: row(H).update(proctype=0, flags=0x100), u"not a declared QUATINTERP helper"),
        (u"not_always_procedural", lambda H: row(H).update(flags=QUAT_FLAGS & ~4), u"flags"),
        (u"physically_simulated", lambda H: row(H).update(flags=QUAT_FLAGS | 1), u"flags"),
        (u"physics_procedural", lambda H: row(H).update(flags=QUAT_FLAGS | 2), u"flags"),
        (u"screen_aligned", lambda H: row(H).update(flags=QUAT_FLAGS | 16), u"flags"),
        (u"attachment_on_the_helper", lambda H: H[u"attachments"].append(left), u"attachment"),
        (u"bone_flex_driver_on_the_helper", lambda H: H[u"flex_drivers"].append(left), u"flex driver"),
    )
    for label, change, why in cases:
        got = variant(change)
        check("A.%s_refuses_that_helper_only" % label, got[0] == [u"hlp_forearm_R"] and
              why in got[1].get(u"hlp_forearm_L", u""), got)
    whole = (
        (u"name_differs", lambda H: row(H).update(name=u"other")),
        (u"parent_differs", lambda H: row(H).update(parent=0)),
        (u"bone_count_differs", lambda H: H[u"bones"].pop()),
        (u"unreadable", lambda H: H.update(status=u"UNREADABLE")),
    )
    for label, change in whole:
        got = variant(change)
        check("A.header_%s_admits_no_helper" % label, got[0] == [] and sorted(got[1]) == list(HELPERS), got)
    # A dependent bone (a header child) and a non-direct-FK parent.
    got = variant(lambda H: row(H, 0).update(parent=left))
    check("A.a_bone_depending_on_the_helper_refuses_or_mismatches", u"hlp_forearm_L" not in got[0], got)
    C2 = copy.deepcopy(C)
    C2[u"bones"][u"bip_lowerArm_L"][u"class"] = u"constrained"
    got = rule(D, C2, evidence)
    check("A.parent_that_is_not_directly_controlled_refuses",
          got[0] == [u"hlp_forearm_R"] and u"parent" in got[1][u"hlp_forearm_L"], got)
    D2 = copy.deepcopy(D)
    D2[u"bones"][u"hlp_forearm_L"][u"parent"] = None
    got = rule(D2, C, evidence)
    check("A.a_top_level_helper_is_never_admitted", u"hlp_forearm_L" not in got[0], got)
    # Only control-less candidates: a declared bone that has a control stays direct FK (no change).
    H = copy.deepcopy(evidence)
    row(H, heavy[u"bones"][u"bip_head"][u"index"]).update(proctype=2, flags=QUAT_FLAGS)
    got = rule(D, C, H)
    check("A.declared_bones_with_controls_are_not_candidates", got[0] == list(HELPERS) and
          C[u"bones"][u"bip_head"][u"class"] == u"direct-fk", got)

    # Selected parts is unchanged: a helper below a selection still refuses.
    lib = SC.library(os.path.join(tempfile.gettempdir(), u"h1_unused"), u"heavy")
    got = outcome(lambda: SC.capture(ns, ns["prod_scope_request"](u"selected_parts", [u"bip_lowerArm_L"])))
    refused("A.selected_parts_with_a_helper_below_still_refuses", got, u"carried-selection")
    return lib


# ---------------------------------------------------------------------------
# B. a renamed, structurally equivalent rig (no names or model identity)
# ---------------------------------------------------------------------------

def renamed(fx):
    out = FS.clone(fx)
    names = dict((n, (u"aux_seg_%d" % b[u"index"]) if n.startswith(u"hlp_") else
                  (u"limb_%d" % b[u"index"]) if u"lowerArm" in n else n) for n, b in fx[u"bones"].items())
    out[u"bones"] = dict((names[n], dict(b, parent=names.get(b[u"parent"]) if b[u"parent"] else None))
                         for n, b in fx[u"bones"].items())
    out[u"model"] = dict(out[u"model"], model_ref=u"models/community/brawler.mdl")
    return out, names


def section_renamed(ns, heavy, root):
    fx, names = renamed(heavy)
    declared = header_rows(fx, dict((names[n], (2, QUAT_FLAGS)) for n in HELPERS))
    w = heavy_world(fx, rows=declared)
    use(ns, w, fx)
    inv = SC.inventory(ns)
    expected = sorted(names[n] for n in HELPERS)
    check("B.renamed_helpers_on_another_model_are_admitted_by_mechanism",
          sorted(inv[u"helpers"]) == expected and inv[u"full_body"][u"status"] == u"available",
          (inv[u"helpers"], inv[u"full_body"]))
    lib = SC.library(os.path.join(root, u"renamed"), u"brawler")
    saved = SC.save(ns, lib, ns["prod_scope_request"](u"full_body"), u"Brawler body")
    dst = heavy_world(FS.clone(fx), rows=declared)
    use(ns, dst, fx)
    result, verdict = SC.apply(ns, SC.reload(ns, lib, saved))
    check("B.renamed_rig_saves_and_applies_verified", verdict == {u"phase": u"committed-verified"},
          (result.get(u"phase"), verdict))
    # The same rig with the helpers declared JIGGLE (physics-like secondary motion) is not admitted.
    w = heavy_world(fx, rows=header_rows(fx, dict((names[n], (5, 1284)) for n in HELPERS)))
    use(ns, w, fx)
    inv = SC.inventory(ns)
    check("B.jiggle_declared_helpers_are_not_admitted", inv[u"helpers"] == [] and
          inv[u"full_body"][u"code"] == u"carried-unsupported", inv[u"full_body"])


# ---------------------------------------------------------------------------
# C. Save and the record
# ---------------------------------------------------------------------------

def posed_source(heavy):
    src = FS.clone(heavy)
    for ch, axis, deg in ((u"bip_lowerArm_L_o", [0, 0, 1], 35), (u"bip_upperArm_R_o", [1, 0, 0], 25),
                          (u"bip_spine_1_o", [0, 1, 0], 12)):
        if ch in src[u"channels"]:
            FS.set_key(src, ch, SC.rotate(src[u"channels"][ch]["keys"][0][1], axis, deg))
    return src


def section_save(ns, heavy, root):
    src = posed_source(heavy)
    w = heavy_world(src)
    use(ns, w, heavy)
    lib = SC.library(os.path.join(root, u"save"), u"heavy")
    before = all_keys(w)
    saved = SC.save(ns, lib, ns["prod_scope_request"](u"full_body"), u"Heavy body")
    pose = saved[u"record"][u"pose"]
    sc = pose[u"scope"]
    check("C.save_is_read_only", all_keys(w) == before and not SC.writes(w) and not w.dm.calls)
    check("C.ledger_marks_the_helpers_as_engine_helpers",
          all(sc[u"ledger"][n] == ns["PROD_SCOPE_HELPER_ROLE"] for n in HELPERS) and
          sum(1 for r in sc[u"ledger"].values() if r == u"posed") == 77, sorted(set(sc[u"ledger"].values())))
    check("C.helpers_are_not_posed_carried_preserved_or_excluded",
          not set(HELPERS) & (set(sc[u"posed"]) | set(sc[u"carried"]) | set(sc[u"preserved"])) and
          sc[u"exclusions"] == [])
    check("C.no_helper_value_offset_or_oracle_and_no_carried_rule",
          not set(HELPERS) & (set(pose[u"values"][u"orientations"]) | set(pose[u"structure"][u"offsets"]) |
                              set(pose[u"oracle"][u"bones"])) and pose[u"engine"][u"carried_rule"] is None and
          pose[u"engine"] == {u"rule": u"direct_fk_v1", u"revision": 1, u"carried_rule": None})
    item = SC.reload(ns, lib, saved)
    check("C.the_record_reloads_through_the_validator", item[u"record"][u"payload_sha256"] ==
          saved[u"record"][u"payload_sha256"])
    return lib, saved


# ---------------------------------------------------------------------------
# D. Apply: planned writes only, helper authorship protected, Undo/Redo, no-op, verified Abort
# ---------------------------------------------------------------------------

def destination(heavy, helper_turn=7.0):
    dst = FS.clone(heavy)
    FS.set_key(dst, u"rootTransform_p", [10.0, 20.0, 0.0]) if u"rootTransform_p" in dst[u"channels"] else None
    for n in (u"hlp_forearm_L_o",):                   # the artist's own, different helper authoring
        for k in dst[u"channels"][n]["keys"]:
            k[1] = SC.rotate(k[1], [1, 0, 0], helper_turn)
    return dst


def section_apply(ns, heavy, lib, saved):
    dst_fx = destination(heavy)
    w = heavy_world(dst_fx)
    use(ns, w, heavy)
    before = all_keys(w)
    item = SC.reload(ns, lib, saved)
    result, verdict = SC.apply(ns, item)
    check("D.full_body_applies_and_verifies", verdict == {u"phase": u"committed-verified"},
          (result.get(u"phase"), verdict, [l for l in ns["LOG"] if u"P7" in l][-2:]))
    after = all_keys(w)
    changed = SC.changed_channels(before, after)
    check("D.only_planned_channels_change", changed and set(changed) <=
          set(result[u"pending"][u"scope"][u"written_names"]), changed[:6])
    check("D.helper_channels_keys_and_defaults_are_untouched",
          all(after[c] == before[c] for c in before if c.startswith(u"hlp_")) and
          not [c for c in SC.writes(w) if u"hlp_" in repr(c)])
    check("D.the_destination_helpers_keep_their_own_authoring",
          after[u"hlp_forearm_L_o"] == before[u"hlp_forearm_L_o"] and
          after[u"hlp_forearm_L_o"] != all_keys(FS.World(heavy))[u"hlp_forearm_L_o"])
    check("D.helpers_follow_as_followers_not_expected_bones",
          set(HELPERS) <= set(result[u"pending"][u"followers"]) and
          not set(HELPERS) & set(result[u"pending"][u"expected"]))
    check("D.one_owned_undo_entry", [e["label"] for e in w.dm.stack] == [u"Apply Pose Heavy body"],
          [e["label"] for e in w.dm.stack])
    w.dm.Undo()
    check("D.undo_restores_every_key", all_keys(w) == before)
    w.dm.Redo()
    check("D.redo_restores_the_applied_keys", all_keys(w) == after)
    again = SC.apply(ns, SC.reload(ns, lib, saved))
    check("D.reapply_is_a_true_no_op", again[0] == {u"phase": u"no-op"} and len(w.dm.stack) == 1, again[0])
    # A failure inside the owned transaction: verified Abort, nothing changed, helpers untouched.
    w = heavy_world(destination(heavy))
    use(ns, w, heavy)
    before = all_keys(w)
    fault = ns["PROD_POSE_QUAL_FAULT"]
    fault[0] = u"after-writes"
    try:
        result, verdict = SC.apply(ns, SC.reload(ns, lib, saved))
    finally:
        fault[0] = None
    check("D.failure_after_writes_is_a_verified_abort", result.get(u"phase") == u"not-applied" and
          all_keys(w) == before and not w.dm.stack, result)
    # Production mode refuses nothing new: the engine rule is the qualified direct_fk_v1.
    w = heavy_world(destination(heavy))
    use(ns, w, heavy)
    result, verdict = SC.apply(ns, SC.reload(ns, lib, saved), mode=u"production")
    check("D.production_mode_applies_the_same_way", verdict == {u"phase": u"committed-verified"},
          (result.get(u"phase"), verdict))
    # A destination whose helper is not admitted refuses before any write.
    w = heavy_world(destination(heavy), rows=header_rows(heavy, {u"hlp_forearm_L": (2, QUAT_FLAGS)}))
    use(ns, w, heavy)
    got = outcome(lambda: SC.apply(ns, SC.reload(ns, lib, saved)))
    check("D.destination_without_the_same_admitted_helpers_refuses_cleanly",
          got[0] != "ok" and not SC.writes(w) and not w.dm.calls, got)


# ---------------------------------------------------------------------------
# E. concrete dangerous consumers
# ---------------------------------------------------------------------------

def tr(w, bone):
    return w.bone_dag[bone].attrs["transform"]


def section_consumers(ns, heavy, lib, saved):
    def attempt(prepare):
        w = heavy_world(destination(heavy))
        prepare(w)
        use(ns, w, heavy)
        got = outcome(lambda: SC.apply(ns, SC.reload(ns, lib, saved)))
        return w, got

    def control(w):
        return [c for c in w.controls if c.name == u"bip_head"][0]
    w, got = attempt(lambda w: SC.reader_channel(w, tr(w, u"hlp_forearm_L"), u"orientation", control(w),
                                                 u"valueOrientation"))
    refused("E.a_channel_from_the_helper_into_a_character_control_refuses", got, u"shared-input")
    check("E.that_refusal_writes_nothing", not SC.writes(w) and not w.dm.calls)
    w, got = attempt(lambda w: SC.constrain_to(w, w.bone_dag[u"bip_head"], w.bone_dag[u"hlp_forearm_L"], u"other"))
    check("E.a_constraint_from_the_helper_onto_a_body_bone_refuses", got[0] != "ok" and not SC.writes(w), got)
    w, got = attempt(lambda w: SC.foreign_writer(w, tr(w, u"hlp_forearm_R"), u"orientation"))
    check("E.a_competing_writer_of_the_helper_refuses", got[0] != "ok" and not SC.writes(w), got)
    w, got = attempt(lambda w: SC.constrain_to(w, w.bone_dag[u"hlp_forearm_L"], w.bone_dag[u"bip_head"], u"other"))
    check("E.a_constraint_driving_the_helper_refuses", got[0] != "ok" and not SC.writes(w), got)
    # An external prop that follows the helper is left under SFM (bounded, admitted, not verified by CPM).
    w, got = attempt(lambda w: SC.prop_dag(w, u"bracelet", parent=w.bone_dag[u"hlp_forearm_L"]))
    check("E.an_external_prop_below_the_helper_follows_it", got[0] == "ok" and
          got[1][1] == {u"phase": u"committed-verified"}, got)


# ---------------------------------------------------------------------------
# F. P2 / P7 relationship changes
# ---------------------------------------------------------------------------

def section_lifecycle(ns, heavy, lib, saved):
    def at_p2(w, change):
        real = ns["prod_scope_preflight"]

        def preflight_then(*args):
            pre = real(*args)
            change(w)
            return pre
        ns["prod_scope_preflight"] = preflight_then
        try:
            return outcome(lambda: SC.apply(ns, SC.reload(ns, lib, saved)))
        finally:
            ns["prod_scope_preflight"] = real

    def declaration(w, proctype):
        rows = copy.deepcopy(w.gm.GetStudioHdr().rows)
        rows[heavy[u"bones"][u"hlp_forearm_L"][u"index"]]["proctype"] = proctype
        attach(w, rows=rows)
        SC.Pin.world = w
        use(ns, w, heavy)
    for label, change in ((u"declaration_changed", lambda w: declaration(w, 5)),
                          (u"helper_key_changed", lambda w: SC.turn(w, u"hlp_forearm_L_o", [0, 1, 0], 3)),
                          (u"consumer_added", lambda w: SC.reader_channel(
                              w, tr(w, u"hlp_forearm_R"), u"orientation",
                              [c for c in w.controls if c.name == u"bip_head"][0], u"valueOrientation"))):
        w = heavy_world(destination(heavy))
        use(ns, w, heavy)
        before = all_keys(w)
        got = at_p2(w, change)
        check("F.p2_%s_refuses_before_any_write" % label, got[0] != "ok" and not [
            c for c in w.dm.calls if c[0] == "StartUndo"] and not SC.writes(w), got)

    def before_p7(change):
        w = heavy_world(destination(heavy))
        use(ns, w, heavy)
        item = SC.reload(ns, lib, saved)
        auth = SC.authorize(ns, u"Apply Pose", item)
        result = ns["prod_scope_apply"](SC.Pin.identity, auth, item, {})
        change(w)
        return result, ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
    for label, change in ((u"declaration_changed", lambda w: declaration(w, 5)),
                          (u"helper_key_changed", lambda w: SC.turn(w, u"hlp_forearm_L_o", [0, 1, 0], 3)),
                          (u"header_unreadable", lambda w: setattr(w.gm, "GetStudioHdr", lambda: None))):
        result, verdict = before_p7(change)
        check("F.p7_%s_is_committed_unverified" % label, result.get(u"phase") == u"verification-pending" and
              verdict.get(u"phase") == u"committed-unverified", (result.get(u"phase"), verdict))


# ---------------------------------------------------------------------------
# G. record and legacy compatibility
# ---------------------------------------------------------------------------

def section_records(ns, heavy, lib, saved):
    record = saved[u"record"]
    validate = ns["prod_scope_validate"]

    def resealed(change):
        r = copy.deepcopy(record)
        change(r[u"pose"])
        r[u"payload_sha256"] = ns["prod_pose_payload_digest"](r[u"pose"])
        return outcome(lambda: validate(r))
    check("G.the_saved_record_validates", outcome(lambda: validate(copy.deepcopy(record)))[0] == "ok")
    roles = ns["PROD_SCOPE_LEDGER_ROLES"]
    ns["PROD_SCOPE_LEDGER_ROLES"] = tuple(r for r in roles if r != ns["PROD_SCOPE_HELPER_ROLE"])
    try:
        refused("G.an_older_strict_reader_refuses_the_helper_role_instead_of_misapplying",
                outcome(lambda: validate(copy.deepcopy(record))), u"invalid-file")
    finally:
        ns["PROD_SCOPE_LEDGER_ROLES"] = roles

    def under_unposed(p):
        p[u"scope"][u"ledger"][u"bip_lowerArm_L"] = ns["PROD_SCOPE_HELPER_ROLE"]
        p[u"scope"][u"posed"].remove(u"bip_lowerArm_L")
    refused("G.a_helper_role_on_a_bone_with_children_or_an_unposed_parent_is_invalid", resealed(under_unposed),
            u"invalid-file")

    def as_posed(p):
        p[u"scope"][u"ledger"][u"hlp_forearm_L"] = u"posed"
    refused("G.a_contradictory_helper_membership_is_invalid", resealed(as_posed), u"invalid-file")
    # Selected parts records never carry the role.
    w = heavy_world(heavy)
    use(ns, w, heavy)
    hand = [b for b in heavy[u"bones"] if b.startswith(u"bip_") and u"hand_L" in b][:1]
    grip = SC.save(ns, lib, ns["prod_scope_request"](u"selected_parts", hand), u"Heavy hand")
    r = copy.deepcopy(grip[u"record"])
    r[u"pose"][u"scope"][u"ledger"][u"hlp_forearm_L"] = ns["PROD_SCOPE_HELPER_ROLE"]
    r[u"payload_sha256"] = ns["prod_pose_payload_digest"](r[u"pose"])
    refused("G.selected_parts_with_the_helper_role_is_invalid", outcome(lambda: validate(r)), u"invalid-file")
    check("G.selected_parts_records_have_no_helper_role",
          ns["PROD_SCOPE_HELPER_ROLE"] not in grip[u"record"][u"pose"][u"scope"][u"ledger"].values())
    # A strict v3 record saved before H1 (the native EF-1 Engineer Full body record) still validates unchanged.
    ef1 = SC.json.loads(SC.core.read(os.path.join(SC.SCOPED_FIXTURES, "ef1_body_record.json")).decode("utf-8"))
    check("G.pre_h1_strict_v3_record_still_validates", outcome(lambda: validate(copy.deepcopy(ef1)))[0] == "ok" and
          ns["PROD_SCOPE_HELPER_ROLE"] not in ef1[u"pose"][u"scope"][u"ledger"].values())


# ---------------------------------------------------------------------------
# H. no independent promotion: the helper rule only runs behind the existing v3 rule gate
# ---------------------------------------------------------------------------

def section_gate(ns, heavy, lib, saved):
    rules = ns["PROD_SCOPE_RULES"]
    original = copy.deepcopy(rules)
    rules[u"direct_fk_v1"][u"status"] = u"experimental"
    try:
        w = heavy_world(destination(heavy))
        use(ns, w, heavy)
        got = outcome(lambda: ns["prod_scope_inventory"](SC.Pin.identity, SC.authorize(ns, u"Save Pose",
                                                                                         mode=u"production")))
        refused("H.unqualified_v3_rule_refuses_heavy_in_production_despite_a_valid_header", got, u"not-qualified")
        got = outcome(lambda: SC.apply(ns, SC.reload(ns, lib, saved), mode=u"production"))
        check("H.unqualified_v3_rule_refuses_the_helper_pose_in_production_writing_nothing",
              got[0] != "ok" and not SC.writes(w) and not w.dm.calls, got)
        got = SC.apply(ns, SC.reload(ns, lib, saved), mode=u"qualification")
        check("H.the_qualification_build_still_admits_it_under_the_experimental_rule",
              got[1] == {u"phase": u"committed-verified"}, got)
    finally:
        rules.clear()
        rules.update(original)


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        return 2
    print("F-01 H1 engine helpers (Python %s)" % sys.version.split()[0])
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    app = route.AppSource(route.APP_PATH)
    root = tempfile.mkdtemp(prefix="cpm_h1_lib_")
    try:
        ns = SC.namespace(app)
        heavy = SC.scoped_fixture("mc01_heavy_norig.json")
        run("admission", lambda: section_admission(ns, heavy))
        run("renamed", lambda: section_renamed(ns, heavy, root))
        saved = run("save", lambda: section_save(ns, heavy, root))
        if saved and saved is not True:
            run("apply", lambda: section_apply(ns, heavy, saved[0], saved[1]))
            run("consumers", lambda: section_consumers(ns, heavy, saved[0], saved[1]))
            run("lifecycle", lambda: section_lifecycle(ns, heavy, saved[0], saved[1]))
            run("records", lambda: section_records(ns, heavy, saved[0], saved[1]))
            run("gate", lambda: section_gate(ns, heavy, saved[0], saved[1]))
    finally:
        shutil.rmtree(root, True)
    failed = [r for r in SC.RESULTS if not r[1]]
    print("RESULT: %d/%d %s (%s)" % (len(SC.RESULTS) - len(failed), len(SC.RESULTS),
                                     "ALL PASS" if not failed else "SOME FAILED", sys.version.split()[0]))
    return 1 if failed else 0


def run(label, fn):
    try:
        value = fn()
        check("section.%s.completed" % label, True)
        return value if value is not None else True
    except Exception:
        check("section.%s.completed" % label, False, traceback.format_exc())
        return None


if __name__ == "__main__":
    sys.exit(main())
