# -*- coding: utf-8 -*-
"""F-01 Stage 1, generic structural rig support: offline qualification of the structural rig adapter
(prod_body_rig_*, stage E part 4) in the CPM application source.

Authority: Astra's compatibility adjudication (ACCEPT WITH CONDITIONS), F-01 Blueprint R4 and the Owner's "F-01 -
Stage 1: Generic Structural Rig Support" (2026-11-18); design package F01_BROAD_FULL_BODY_COMPATIBILITY_REVIEW.md.

Technique: the stage E suite's harness (test_cpm_app_f01_body: the extracted blocks, the live namespace, the fake
scene of fake_sfm_body and the Poses window methods). The oracle data are fixtures/f01_body/fox_shot15.json, derived
read-only by f01_dmx_body_fixture.py from the Owner's RC1 smoke session (the R2 fixture): Fox's real stock
rig_biped_simple rig, bones, controls, channels, keys, operators and control groups. Fox is a qualification fixture,
not a supported character: nothing in CPM names it. Nothing here demonstrates native SFM behaviour.

Usage: --phase=run (Python 2.7.5 and Python 3.10). Optional: --legacy=RC2_CPM.py runs the legacy-reader check
against that file (the RC2 release baseline); without it the check reads RC2 from Git (commit ede599f).
"""
from __future__ import print_function

import copy
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_f01_pose_core as core  # noqa: E402
import test_cpm_app_f01_body as B  # noqa: E402
import fake_sfm_body as FB  # noqa: E402

try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

FIXTURE = os.path.join(_THIS_DIR, "fixtures", "f01_body", "fox_shot15.json")
FIXTURE_SHA256 = "053787dcea1844376cdecde648c4d46a67bf7e8089524bbf059ee952a0a3e5e2"
RC2_COMMIT = "ede599f"
MODEL = u"models/fursonas/foxmccouldwm.mdl"
IDENTITY = {"model": MODEL, "checksum": 4321, "animset_name": u"foxmccouldwm1"}
B.IDENTITY = IDENTITY                 # the stage E window and context helpers read the module's identity
RESULTS = B.RESULTS
check, outcome, refused = B.check, B.outcome, B.refused
QUAL, PROD = u"qualification", u"production"


def fixture():
    raw = core.read(FIXTURE)
    check("fixture.fox_shot15.matches_its_pin", core.sha(raw) == FIXTURE_SHA256, core.sha(raw))
    return json.loads(raw.decode("utf-8"))


def ctx(ns):
    return B.live_context(ns)


def authorize(ns, reg, label, item=None, mode=QUAL, exclusions=None):
    return ns["prod_body_rig_authorize"](ctx(ns), IDENTITY, reg, mode, label, item, exclusions)


def world(fx, prepare=None, posed=True):
    w = FB.World(fx)
    if posed:
        pose_differently(w)
    if prepare is not None:
        prepare(w)
        w.evaluate()
    return w


def use(ns, w):
    B.use_world(ns, w)
    return w


def pose_differently(w):
    """A distinctly posed and placed destination: every written rig handle turned and moved, the fingers and tails
    turned (FK positions untouched: A1), the placement moved and turned."""
    for name, ch in w.channels.items():
        layer = ch.attrs["log"].layer
        if not layer.keys or layer.value_kind is None:
            continue
        handle = name.startswith(u"rig_") and not name.startswith((u"rig_root", u"rig_footHelper"))
        fk = name.endswith(u"_o") and any(t in name for t in (u"Finger", u"Tail", u"tail"))
        if not (handle or fk or name in (u"rig_root_p", u"rig_root_o")):
            continue
        if name in (u"rig_elbow_L_o", u"rig_elbow_R_o", u"rig_knee_L_o", u"rig_knee_R_o"):
            continue                                       # pole orientations: preserved, never written
        for k in layer.keys:
            v = FB.plain(k[1])
            if layer.value_kind == "quat":
                v = B.rotate(v, [0.0, 0.0, 1.0], 30.0) if name == u"rig_root_o" else B.rotate(v, [1.0, 0.0, 0.0],
                                                                                             20.0)
            elif name == u"rig_root_p":
                v = [v[0] + 60.0, v[1] + 25.0, v[2]]
            else:
                v = [v[0] + 1.5, v[1] - 1.0, v[2]]
            k[1] = FB.native(v, layer.value_kind)
    w.evaluate()


def placement_relative(w):
    return B.placement_relative(w, u"rig_root")


def discovered(ns, w):
    use(ns, w)
    row = ns["prod_resolve_instance"](ctx(ns)[u"instance"])
    L = ns["prod_body_live"](row, None)
    t = ns["prod_pose_time_read"](L, ns["prod_body_rig_time_names"](L))
    return ns["prod_body_discover"](L, t[u"t_chan"], ns["prod_pose_writer_index"]())


def draft(ns, D, exclusions=None):
    return outcome(lambda: ns["prod_body_rig_draft"](D, exclusions))


def no_mutation(w):
    return not B.scene_writes(w) and not w.dm.calls


def save(ns, reg, lib, name, exclusions=None, w=None):
    auth = authorize(ns, reg, u"Save Pose", exclusions=exclusions)
    pinned = ns["prod_body_current_time"](IDENTITY, auth, reg)
    pose = ns["prod_body_capture"](IDENTITY, auth, reg, pinned_time=pinned)
    saved = ns["prod_pose_save_new"](lib, name, pose, u"20261118-120000-000000", reg)
    return pose, saved, reread(ns, reg, lib, saved)


def reread(ns, reg, lib, saved):
    return [i for i in ns["prod_pose_discover"](lib[u"char_dir"], lib[u"character_key"], reg)[u"items"]
            if i[u"preset_id"] == saved[u"preset_id"]][0]


def apply_(ns, reg, item, w, mode=QUAL):
    use(ns, w)
    auth = authorize(ns, reg, u"Apply Pose", item, mode=mode)
    return auth, outcome(lambda: ns["prod_body_apply"](IDENTITY, auth, item, reg))


def library(root, name):
    if not os.path.isdir(os.path.join(root, name)):
        os.makedirs(os.path.join(root, name))
    return {u"character_key": u"foxmccouldwm", u"char_dir": os.path.join(root, name, u"Characters", u"foxmccouldwm"),
            u"library_root": os.path.join(root, name), u"model_ref": MODEL, u"checksum": 4321}


# ---------------------------------------------------------------------------
# A. The drafted description: every role established on its own
# ---------------------------------------------------------------------------

def section_draft(ns, fx):
    D = discovered(ns, world(fx, posed=False))
    got = draft(ns, D)
    check("A.fox_rig_is_drafted_from_structure_alone", got[0] == u"ok", got)
    P = got[1]
    check("A.rig_handles_and_parents", len(P[u"handles"]) == 22 and P[u"handles"][u"rig_root"] == u"@rig" and
          P[u"handles"][u"rig_toe_L"] == u"rig_footHelper_L" and P[u"handles"][u"rig_knee_L"] == u"rig_foot_L",
          P[u"handles"])
    check("A.placement_is_the_handle_constraining_the_model_transform", P[u"placement_handle"] == u"rig_root")
    check("A.helpers_are_the_bone_following_handles", P[u"helper_handles"] == [u"rig_footHelper_L",
                                                                               u"rig_footHelper_R"])
    check("A.constraints_point_orient_and_two_bone_ik", len(P[u"constraints"]) == 34 and sorted(
        set((c[u"type"], len([d for d in P[u"constraints"] if d[u"type"] == c[u"type"]])) for c in P[u"constraints"]))
        == [(u"DmeRigIKConstraintOperator", 4), (u"DmeRigOrientConstraintOperator", 17),
            (u"DmeRigPointConstraintOperator", 13)])
    check("A.core_handle_channels_written_placement_and_pole_orientations_preserved",
          len(P[u"written_handle_channels"]) == 34 and sorted(P[u"preserved_handle_channels"]) == [
              u"rig_elbow_L_o", u"rig_elbow_R_o", u"rig_knee_L_o", u"rig_knee_R_o", u"rig_root_o", u"rig_root_p"] and
          u"rig_elbow_L_p" in P[u"written_handle_channels"] and u"rig_toe_L_o" in P[u"written_handle_channels"],
          sorted(P[u"preserved_handle_channels"]))
    check("A.no_passive_or_preserved_bones_without_an_exclusion", P[u"passive_channel_bones"] == [] and
          P[u"preserved_fk_bones"] == [])
    check("A.descriptor_rig_name_is_structural_and_limits_are_the_v3_ones",
          P[u"descriptor_rig_name"] == u"@structural" and P[u"rig_name"] == u"rig_biped_foxmccouldwm1" and
          P[u"fk_position_limit"] == 0.001 and P[u"tolerances"] == ns["PROD_SCOPE_TOLERANCES"])
    C = ns["prod_body_classify"](D, P)
    bones = B.counts(C[u"bones"].values())
    roles = B.counts(C[u"channels"].values())
    check("A.unchanged_stage_e_classifier_accepts_the_draft", bones == {u"constrained": 22, u"fk": 90} and
          roles.get(u"handle-written") == 34 and roles.get(u"fk-written") == 180 and roles.get(u"ik-offset") == 12 and
          roles.get(u"handle-preserved") == 6 and len(C[u"written"]) == 214, (bones, roles))
    check("A.rig_driven_bones_are_never_written", not [n for n in C[u"written"] if C[u"owners"][n][0][5:] in [
        b for b, c in C[u"bones"].items() if c == u"constrained"] and C[u"channels"][n] == u"fk-written"])
    desc = ns["prod_body_descriptor"](D, C, P)
    check("A.descriptor_names_structure_not_the_instance", desc[u"rig_name"] == u"@structural" and
          u"foxmccouldwm1" not in json.dumps(desc))
    check("A.draft_is_deterministic", draft(ns, D)[1] == P)
    return D, P


def mutate(D, fn):
    D2 = copy.deepcopy(D)
    fn(D2)
    return D2


def op_named(D, name):
    return [op for op in D[u"operators"] if op[u"name"] == name][0]


def handle_label(D, name):
    return D[u"rig"][u"handles"][name][u"handle"]


def section_draft_refusals(ns, D, P):
    H = D[u"rig"][u"handles"]
    bone_h = dict((n, b[u"handle"]) for n, b in D[u"bones"].items())
    cases = []

    def retarget(op, handle):
        def fn(d):
            op_named(d, op)[u"targets"][0][u"target"] = handle
        return fn
    cases.append((u"placement_point_and_orient_disagree", retarget(u"orientConstraint_rootTransform",
                                                                   handle_label(D, u"rig_pelvis")),
                  u"placement-ambiguous"))
    cases.append((u"placement_missing", lambda d: d.__setitem__(u"operators", [
        op for op in d[u"operators"] if not op[u"name"].endswith(u"_rootTransform")]), u"placement-ambiguous"))

    def placement_under_handle(d):
        d[u"rig"][u"handles"][u"rig_root"][u"parent"] = {u"handle": handle_label(d, u"rig_pelvis"),
                                                         u"type": u"DmeRigHandle", u"name": u"rig_pelvis"}
    cases.append((u"placement_not_a_child_of_the_rig", placement_under_handle, u"placement-ambiguous"))
    cases.append((u"placement_constrained_by_a_bone", retarget(u"pointConstraint_rootTransform",
                                                               bone_h[u"ValveBiped.Bip01_Pelvis"]),
                  u"placement-ambiguous"))

    def second_model_point(d):
        extra = copy.deepcopy(op_named(d, u"pointConstraint_rootTransform"))
        extra[u"handle"], extra[u"name"] = 900000001, u"pointConstraint_rootTransform2"
        extra[u"targets"][0][u"target"] = handle_label(d, u"rig_pelvis")
        d[u"operators"].append(extra)
    cases.append((u"two_point_constraints_on_the_model", second_model_point, u"structure-unsupported"))
    cases.append((u"helper_following_a_handle", retarget(u"pointConstraint_rig_footHelper_L",
                                                         handle_label(D, u"rig_foot_L")), u"structure-unsupported"))

    def helper_as_target(d):
        retarget(u"orientConstraint_ValveBiped.Bip01_Head1", handle_label(d, u"rig_footHelper_L"))(d)
    cases.append((u"helper_also_a_constraint_input", helper_as_target, u"shared-authority"))

    def bone_parented(d):
        d[u"rig"][u"handles"][u"rig_hand_L"][u"parent"] = {u"handle": bone_h[u"ValveBiped.Bip01_L_Forearm"],
                                                           u"type": u"DmeDag", u"name": u"ValveBiped.Bip01_L_Forearm"}
    cases.append((u"bone_parented_handle", bone_parented, u"structure-unsupported"))

    def weighted(d):
        op_named(d, u"orientConstraint_ValveBiped.Bip01_Head1")[u"targets"][0][u"weight"] = {u"status": u"READ",
                                                                                             u"value": 0.5}
    cases.append((u"weighted_constraint", weighted, u"structure-unsupported"))

    def two_targets(d):
        op = op_named(d, u"orientConstraint_ValveBiped.Bip01_Head1")
        op[u"targets"].append(dict(op[u"targets"][0], handle=900000002))
    cases.append((u"multiple_target_constraint", two_targets, u"structure-unsupported"))

    def aim(d):
        d[u"operators"].append({u"handle": 900000003, u"type": u"DmeRigAimConstraintOperator", u"name": u"aim",
                                u"slaves": {}, u"targets": [], u"pole": None, u"solver": {}})
    cases.append((u"unsupported_operator_type", aim, u"structure-unsupported"))

    def not_two_bone(d):
        ik = [op for op in d[u"operators"] if op[u"type"] == u"DmeRigIKConstraintOperator"][0]
        ik[u"slaves"][u"midJoint"][u"target"] = bone_h[u"ValveBiped.Bip01_Spine"]
    cases.append((u"ik_not_a_two_bone_chain", not_two_bone, u"structure-unsupported"))

    def ik_pole_bone(d):
        ik = [op for op in d[u"operators"] if op[u"type"] == u"DmeRigIKConstraintOperator"][0]
        ik[u"pole"] = bone_h[u"ValveBiped.Bip01_Spine"]
    cases.append((u"ik_pole_not_a_rig_handle", ik_pole_bone, u"structure-unsupported"))
    cases.append((u"target_outside_the_character", retarget(u"orientConstraint_ValveBiped.Bip01_Head1", 900000004),
                  u"shared-authority"))

    def slave_outside(d):
        op_named(d, u"orientConstraint_ValveBiped.Bip01_Head1")[u"slaves"][u"slave"][u"target"] = 900000005
    cases.append((u"slave_outside_the_character", slave_outside, u"shared-authority"))

    def missing_control(d):
        del d[u"channels"][u"rig_hand_L_o"]
    cases.append((u"missing_major_control_channel", missing_control, u"structure-unsupported"))

    def shared_control(d):
        d[u"channels"][u"rig_hand_L_o2"] = dict(d[u"channels"][u"rig_hand_L_o"], handle=900000006)
    cases.append((u"handle_attribute_with_two_channels", shared_control, u"structure-unsupported"))

    def controlless(d):
        d[u"channels"][u"ValveBiped.Bip01_R_Finger42_o"][u"from"] = None
    cases.append((u"control_less_bone_stage_2", controlless, u"structure-unsupported"))

    def no_rig(d):
        d[u"rig"][u"registrations"], d[u"rig"][u"names"] = 0, []
    cases.append((u"no_rig_registration", no_rig, u"unavailable"))

    def conflicting(d):
        extra = copy.deepcopy(op_named(d, u"orientConstraint_ValveBiped.Bip01_Head1"))
        ik = [op for op in d[u"operators"] if op[u"type"] == u"DmeRigIKConstraintOperator"][0]
        extra[u"handle"], extra[u"name"] = 900000007, u"orient_on_ik_mid"
        extra[u"slaves"][u"slave"][u"target"] = ik[u"slaves"][u"midJoint"][u"target"]
        d[u"operators"].append(extra)
    cases.append((u"orient_constraint_on_an_ik_mid_joint", conflicting, u"structure-unsupported"))

    def duplicate(d):
        extra = copy.deepcopy(op_named(d, u"orientConstraint_ValveBiped.Bip01_Head1"))
        extra[u"handle"] = 900000008
        d[u"operators"].append(extra)
    cases.append((u"repeated_constraint", duplicate, u"structure-unsupported"))
    for label, fn, code in cases:
        refused("A.refuses_%s" % label, draft(ns, mutate(D, fn)), code)

    # Pole orientation: preserved only for a leaf handle that is nothing but an IK pole.
    def pole_with_child(d):
        h = copy.deepcopy(d[u"rig"][u"handles"][u"rig_toe_L"])
        h[u"handle"], h[u"transform"] = 900000010, 900000011
        h[u"parent"] = {u"handle": handle_label(d, u"rig_elbow_L"), u"type": u"DmeRigHandle", u"name": u"rig_elbow_L"}
        d[u"rig"][u"handles"][u"rig_extra"] = h
        for attr, suffix in ((u"position", u"_p"), (u"orientation", u"_o")):
            d[u"channels"][u"rig_extra" + suffix] = dict(d[u"channels"][u"rig_toe_L" + suffix], handle=900000012 + len(
                suffix + attr), to={u"handle": 900000011, u"type": u"DmeTransform", u"name": u"rig_extra"})
    got = draft(ns, mutate(D, pole_with_child))
    check("A.pole_with_a_child_handle_has_its_orientation_written", got[0] == u"ok" and
          u"rig_elbow_L_o" in got[1][u"written_handle_channels"] and
          u"rig_elbow_R_o" in got[1][u"preserved_handle_channels"], got[:2] if got[0] != u"ok" else None)
    got = draft(ns, mutate(D, retarget(u"orientConstraint_ValveBiped.Bip01_Head1", handle_label(D, u"rig_knee_L"))))
    check("A.pole_that_is_also_an_orient_target_has_its_orientation_written", got[0] == u"ok" and
          u"rig_knee_L_o" in got[1][u"written_handle_channels"], got[:2] if got[0] != u"ok" else None)

    # Artist-confirmed face exclusions (the v3 review, reused).
    face = {u"id": u"face", u"bones": [u"JAW"], u"provenance": u"user_confirmed", u"label": u"Face"}
    got = draft(ns, D, [face])
    check("A.confirmed_exclusion_preserves_its_fk_bones", got[0] == u"ok" and got[1][u"preserved_fk_bones"] ==
          [u"JAW"] and ns["prod_body_classify"](D, got[1])[u"bones"][u"JAW"] == u"fk-preserved", got[:2])
    refused("A.unconfirmed_exclusion_refuses", draft(ns, D, [dict(face, provenance=u"supported_metadata")]),
            u"structure-unsupported")
    refused("A.exclusion_of_a_rig_driven_bone_refuses", draft(ns, D, [dict(face, bones=[
        u"ValveBiped.Bip01_Head1"])]), u"structure-unsupported")
    refused("A.exclusion_of_a_missing_bone_refuses", draft(ns, D, [dict(face, bones=[u"no_such_bone"])]),
            u"rig-differs")
    refused("A.repeated_exclusion_refuses", draft(ns, D, [face, face]), u"structure-unsupported")


def section_portability(ns, D, P):
    """A renamed animation set and rig and a reordered enumeration draft the same description and descriptor. The
    rig's own element names (handles, bones, constraint operators and their channels, all generated by the rig
    script from the skeleton) remain part of the compared structure: a renamed constraint is a different rig."""
    def renamed(d):
        d[u"rig"][u"names"] = [u"rig_biped_renamed_fox_7"]
        h = d[u"rig"][u"handles"][u"rig_root"]
        h[u"parent"] = dict(h[u"parent"], name=u"rig_biped_renamed_fox_7")
        d[u"operators"].reverse()
        d[u"channels"] = dict(reversed(list(d[u"channels"].items())))
        d[u"controls"] = dict(reversed(list(d[u"controls"].items())))
        d[u"bones"] = dict(reversed(list(d[u"bones"].items())))
        d[u"rig"][u"handles"] = dict(reversed(list(d[u"rig"][u"handles"].items())))
    D2 = mutate(D, renamed)
    got = draft(ns, D2)
    check("B.renamed_and_reordered_instance_drafts_the_same_roles", got[0] == u"ok" and dict(
        got[1], rig_name=None) == dict(P, rig_name=None), got[:2] if got[0] != u"ok" else None)
    C1, C2 = ns["prod_body_classify"](D, P), ns["prod_body_classify"](D2, got[1])
    d1, d2 = ns["prod_body_descriptor"](D, C1, P), ns["prod_body_descriptor"](D2, C2, got[1])
    check("B.renamed_and_reordered_descriptor_compares_equal", outcome(
        lambda: ns["prod_body_compare_descriptor"](d1, d2))[0] == u"ok", ns["prod_pose_differences"](d1, d2)[:4])

    def renamed_operator(d):
        op = op_named(d, u"orientConstraint_ValveBiped.Bip01_Head1")
        old = op[u"name"]
        op[u"name"] = u"orientConstraint_renamed"
        for cname in list(d[u"channels"]):
            if cname.startswith(old + u" "):
                d[u"channels"][cname.replace(old, u"orientConstraint_renamed")] = d[u"channels"].pop(cname)
    D3 = mutate(D, renamed_operator)
    got = draft(ns, D3)
    d3 = ns["prod_body_descriptor"](D3, ns["prod_body_classify"](D3, got[1]), got[1]) if got[0] == u"ok" else None
    refused("B.a_renamed_constraint_operator_is_a_different_rig", outcome(
        lambda: ns["prod_body_compare_descriptor"](d1, d3)), u"rig-differs")


# ---------------------------------------------------------------------------
# B-D. Live: Save, Apply, transaction, refusals, P2/P7, Abort
# ---------------------------------------------------------------------------

def section_live(ns, reg, fx, root):
    lib = library(root, u"live")
    src = use(ns, world(fx, posed=False))
    head = src.head
    probe = ns["prod_body_rig_probe"](ctx(ns), IDENTITY, reg, QUAL)
    check("L.qualification_probe_admits_fox", probe is not None and probe[u"classes"][u"JAW"] == u"fk", probe and
          sorted(probe))
    pose, saved, item = save(ns, reg, lib, u"Fox A")
    check("L.save_is_read_only", no_mutation(src) and src.head == head)
    region = pose[u"regions"][u"full_body"]
    check("L.save_records_the_rig_handles_and_direct_bones", len(region[u"positions"]) + len(
        region[u"orientations"]) == 214 and region[u"orientations"][u"rig_hand_L_o"] ==
        src.channels[u"rig_hand_L_o"].attrs["log"].value_at(src.t_chan()) and
        u"rig_root_p" not in region[u"positions"] and
        u"rig_knee_L_o" not in region[u"orientations"])
    check("L.record_is_version_2_with_the_adapter_marker", sorted(pose) == [
        u"adapter", u"conventions", u"format", u"regions", u"source", u"version"] and pose[u"adapter"] == {
        u"rule": u"structural_rig_v1", u"revision": 1} and pose[u"source"][u"rig_class"] == u"structural_rig_v1" and
        region[u"exclusions"] == [] and region[u"profile_id"] == u"structural_rig_v1")
    check("L.record_reloads_independently", item[u"record"] == saved[u"record"])
    source = placement_relative(src)

    dst = use(ns, world(fx))
    dp, dq = B.max_difference(placement_relative(dst), source)
    check("L.destination_is_distinctly_posed", dq > 10.0, (dp, dq))
    before = B.all_keys(dst)
    model = (list(dst.gm.wp), list(dst.gm.wq))
    auth, got = apply_(ns, reg, item, dst)
    check("L.apply_commits_in_one_owned_undo", got[0] == u"ok" and got[1][u"phase"] == u"verification-pending" and
          [c[0] for c in dst.dm.calls] == ["StartUndo", "FinishUndo"] and len(dst.dm.stack) == 1 and
          dst.dm.stack[0]["label"] == u"Apply Pose Fox A", got[:2])
    verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth))
    check("L.p7_whole_skeleton_verifies", verdict.get(u"phase") == u"committed-verified", verdict)
    dpp, dqp = B.max_difference(placement_relative(dst), source)
    check("L.destination_takes_the_source_posture_in_its_own_placement", dpp < 1e-3 and dqp < 0.01, (dpp, dqp))
    after = B.all_keys(dst)
    C = ns["prod_body_classify"](discovered(ns, world(fx)), ns["prod_body_rig_draft"](discovered(ns, world(fx))))
    use(ns, dst)
    planned = sorted(n for n, r in C[u"channels"].items() if r in (u"handle-written", u"fk-written"))
    changed = sorted(n for n in after if after[n] != before[n])
    check("L.only_planned_channels_changed", set(changed) <= set(planned) and len(changed) > 40, len(changed))
    kept = [n for n, r in C[u"channels"].items() if r in (u"handle-preserved", u"ik-offset", u"slave-base", u"weight",
                                                           u"preserved")]
    check("L.placement_poles_ik_lengths_slaves_weights_and_flexes_preserved", all(after[n] == before[n] for n in kept)
          and (list(dst.gm.wp), list(dst.gm.wq)) == model, [n for n in kept if after[n] != before[n]][:8])
    dst.dm.Undo()
    check("L.undo_restores_the_baseline", B.all_keys(dst) == before)
    dst.dm.Redo()
    check("L.redo_reapplies", B.all_keys(dst) == after)
    calls = len(dst.calls)
    _, again = apply_(ns, reg, item, dst)
    check("L.verified_repeat_apply_is_a_noop", again[0] == u"ok" and again[1] == {u"phase": u"no-op"} and
          len(dst.calls) == calls, again[:2])

    # Renamed instance with reversed enumeration: the same pose applies and verifies.
    def rename(w):
        w.rig.name = u"rig_biped_fox_second"
        w.animset.name = u"fox_second"
        w.ops.reverse()
        w.animset.attrs["operators"].items.reverse()
        w.chan_clip.attrs["channels"].items.reverse()
        w.animset.attrs["controls"].items.reverse()
    w = world(fx, rename)
    auth, got = apply_(ns, reg, item, w)
    verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth)) if got[0] == u"ok" and \
        got[1].get(u"pending") else None
    check("L.renamed_reordered_instance_applies_and_verifies", verdict is not None and verdict.get(u"phase") ==
          u"committed-verified" and B.max_difference(placement_relative(w), source)[1] < 0.01, (got[:2], verdict))
    return lib, item, source


def section_live_refusals(ns, reg, fx, item):
    def target(w, op_name):
        return [el for op, el in w.ops if op["name"] == op_name][0].attrs["targets"].items[0]

    def offset(w):
        t = target(w, u"orientConstraint_ValveBiped.Bip01_Head1")
        t.set("oOffset", FB.Quaternion(*B.rotate([0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 1.0], 3.0)))

    def vec_offset(w):
        target(w, u"pointConstraint_ValveBiped.Bip01_Neck1").set("vecOffset", FB.Vector(0.5, 0.0, 0.0))

    def solver(w):
        ik = [el for op, el in w.ops if op["type"] == u"DmeRigIKConstraintOperator"][0]
        ik.set("poleVector", FB.Vector(1.0, 0.0, 0.0))

    def bone_length(w):
        name = [n for n in sorted(w.channels) if n.endswith(u"_Calf_p")][0]
        layer = w.channels[name].attrs["log"].layer
        for k in layer.keys:
            v = FB.plain(k[1])
            k[1] = FB.native([v[0] * 1.1, v[1], v[2]], "vec")

    def handle_scale(w):
        w.handle_dag[u"rig_hand_L"].attrs["transform"].set("scale", 1.2)

    def missing_handle_channel(w):
        ch = w.channels.pop(u"rig_hand_L_o")
        w.chan_clip.attrs["channels"].items.remove(ch)

    def fk_far(w):
        layer = w.channels[u"ValveBiped.Bip01_R_Finger42_p"].attrs["log"].layer
        v = FB.plain(layer.keys[0][1])
        layer.keys[0][1] = FB.native([v[0], v[1] + 0.002, v[2]], "vec")      # beyond the 0.001 limit

    def duplicate_handle(w):
        dag = w.handle_dag[u"rig_hand_L"]
        dup = FB.Dag(w, w.new_handle(), "DmeRigHandle", u"rig_hand_L", FB.Element(
            w, w.new_handle(), "DmeTransform", u"rig_hand_L", position=FB.Vector(), orientation=FB.Quaternion()))
        w.rig.add(dup)
        w.rig.attrs["animSetList"].items[0].attrs["elementList"].items.append(dup)

    def second_registration(w):
        reg2 = FB.Element(w, w.new_handle(), "DmeRigAnimSetElements", "rigElements_again", animationSet=w.animset,
                          elementList=FB.ElementArray(w, []))
        w.rig.attrs["animSetList"].items.append(reg2)
    for label, prepare, code in (
            (u"altered_constraint_orientation_offset", offset, u"rig-differs"),
            (u"altered_constraint_position_offset", vec_offset, u"rig-differs"),
            (u"altered_ik_solver_setting", solver, u"rig-differs"),
            (u"different_ik_bone_length", bone_length, u"proportions"),
            (u"different_handle_scale", handle_scale, u"proportions"),
            (u"missing_major_control", missing_handle_channel, u"structure-unsupported"),
            (u"fk_position_beyond_the_v3_limit", fk_far, u"fk-position"),
            (u"ambiguous_duplicated_handle", duplicate_handle, u"ambiguous"),
            (u"two_rig_registrations", second_registration, u"rig-differs")):
        w = world(fx, prepare)
        _, got = apply_(ns, reg, item, w)
        refused("R.%s_refuses_before_any_write" % label, got, code)
        check("R.%s_changes_nothing" % label, no_mutation(w), w.dm.calls)

    # A1: within the limit the destination keeps its own FK positions (never the saved ones).
    def fk_near(w):
        layer = w.channels[u"ValveBiped.Bip01_R_Finger42_p"].attrs["log"].layer
        v = FB.plain(layer.keys[0][1])
        layer.keys[0][1] = FB.native([v[0], v[1] + 0.0005, v[2]], "vec")
    w = world(fx, fk_near)
    own = w.keys(u"ValveBiped.Bip01_R_Finger42_p")[0][1]
    saved_value = item[u"record"][u"pose"][u"regions"][u"full_body"][u"positions"][u"ValveBiped.Bip01_R_Finger42_p"]
    auth, got = apply_(ns, reg, item, w)
    verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth)) if got[0] == u"ok" else None
    check("R.fk_position_within_the_limit_keeps_the_destination_value",
          verdict is not None and verdict.get(u"phase") == u"committed-verified" and own != saved_value and
          all(k[1] == own for k in w.keys(u"ValveBiped.Bip01_R_Finger42_p")), (got[:1], verdict))
    # Shared writers and external dependencies.
    w = world(fx, lambda w: B.foreign_channel(w, w.channels[u"rig_hand_L_o"].attrs["log"]))
    _, got = apply_(ns, reg, item, w)
    refused("R.shared_log_of_a_rig_handle_channel_refuses", got, u"shared-authority")
    check("R.shared_log_changes_nothing", no_mutation(w))
    for bone in (u"ValveBiped.Bip01_R_Finger42", u"ValveBiped.Bip01_Pelvis"):
        w = world(fx, lambda w, bone=bone: B.external_constraint(w, bone))
        _, got = apply_(ns, reg, item, w)
        refused("R.external_constraint_on_%s_refuses" % bone, got, u"shared-authority")
        check("R.external_constraint_on_%s_changes_nothing" % bone, no_mutation(w))
    # Production build: the adapter is experimental, so Apply and Save refuse (the RC2 behaviour).
    w = world(fx)
    use(ns, w)
    got = outcome(lambda: authorize(ns, reg, u"Apply Pose", item, mode=PROD))
    refused("R.production_build_refuses_a_structural_apply", got, u"not-qualified")
    refused("R.production_build_refuses_a_structural_save", outcome(lambda: authorize(ns, reg, u"Save Pose",
                                                                                      mode=PROD)), u"not-qualified")
    check("R.production_probe_is_inert", ns["prod_body_rig_probe"](ctx(ns), IDENTITY, reg, PROD) is None and
          no_mutation(w))
    # Same model identity required.
    other = dict(item, record=dict(item[u"record"], model_ref=u"models/other/model.mdl"))
    refused("R.a_record_of_another_model_refuses", outcome(lambda: authorize(ns, reg, u"Apply Pose", other)),
            u"different-model")
    # Editor and clock gates.
    w = world(fx, lambda w: setattr(w, "timeline_mode", 3))
    _, got = apply_(ns, reg, item, w)
    check("R.outside_the_motion_editor_apply_refuses_before_any_write", got[0] != u"ok" and got[1] in (
        u"editor-mode", u"capture-clock") and no_mutation(w), got)


def section_transaction(ns, reg, fx, item):
    # P2: a rig handle key changed after P1 makes the operation stale; nothing is written.
    w = world(fx)
    original = ns["prod_body_preflight"]

    def preflight_then_change(*args):
        pre = original(*args)
        layer = w.channels[u"rig_spine_1_o"].attrs["log"].layer
        layer.keys[0][1] = FB.native(B.rotate(FB.plain(layer.keys[0][1]), [0.0, 1.0, 0.0], 5.0), "quat")
        w.evaluate()
        return pre
    ns["prod_body_preflight"] = preflight_then_change
    try:
        _, got = apply_(ns, reg, item, w)
    finally:
        ns["prod_body_preflight"] = original
    refused("T.p2_rig_key_change_after_p1_is_stale", got, u"stale")
    check("T.p2_change_writes_nothing", not B.scene_writes(w) and not [c for c in w.dm.calls if c[0] == "StartUndo"])
    # P2: a structural change (a constraint offset) after P1 is a changed description.
    w = world(fx)

    def preflight_then_restructure(*args):
        pre = original(*args)
        t = [el for op, el in w.ops if op["name"] == u"orientConstraint_ValveBiped.Bip01_Neck1"][0]
        t.attrs["targets"].items[0].set("oOffset", FB.Quaternion(*B.rotate([0.0, 0.0, 0.0, 1.0], [1, 0, 0], 2.0)))
        return pre
    ns["prod_body_preflight"] = preflight_then_restructure
    try:
        _, got = apply_(ns, reg, item, w)
    finally:
        ns["prod_body_preflight"] = original
    refused("T.p2_structural_change_after_p1_is_stale", got, u"stale")
    check("T.p2_structural_change_writes_nothing", not B.scene_writes(w))

    # One partial-write failure after rig and FK writes: verified Abort, nothing remains.
    w = world(fx)
    before = B.all_keys(w)
    w.fail_on_write = u"rig_spine_0_o"
    auth, got = apply_(ns, reg, item, w)
    writes = [w.layer_channel.get(c[1]) for c in B.scene_writes(w)]
    failed_at = writes.index(u"rig_spine_0_o") if u"rig_spine_0_o" in writes else len(writes)
    done = writes[:failed_at]
    check("T.partial_write_failure_after_rig_and_fk_writes", any(n.startswith(u"rig_") for n in done) and any(
        n.startswith(u"ValveBiped.") for n in done), done[-6:])
    check("T.partial_write_failure_aborts_and_verifies_unchanged", got[0] == u"ok" and got[1][u"phase"] ==
          u"not-applied" and [c[0] for c in w.dm.calls] == ["StartUndo", "AbortUndoableOperation"] and
          B.all_keys(w) == before and not w.dm.stack, (got[:2], w.dm.calls))
    check("T.abort_verified_is_logged", any(u"BODY-abort-verified" in l for l in ns["LOG"][-8:]))
    # Abort that cannot be verified locks recovery (never "not applied").
    w = world(fx, lambda w: (setattr(w, "fail_on_write", u"rig_spine_0_o"), setattr(w, "abort_raises", True)))
    _, got = apply_(ns, reg, item, w)
    check("T.failed_abort_is_recovery_unverified", got[0] == u"ProdRecoveryUnverifiedError", got)

    # P7 is an independent observation, not the planner's values: an evaluator that leaves the IK unsolved after the
    # commit leaves every planned input at its value, yet the skeleton fails verification.
    w = world(fx)
    auth, got = apply_(ns, reg, item, w)
    solve = w.solve_ik

    def misbent(start, el, parent_world, parent_scale):
        solve(start, el, parent_world, parent_scale)          # then the start joint 10 degrees off the solution
        w.set_world(start, start.wp, B.rotate(start.wq, [0.0, 0.0, 1.0], 10.0), parent_world, parent_scale)
    w.solve_ik = misbent
    keys = B.all_keys(w)
    w.evaluate()
    pending = dict(got[1][u"pending"], authorization=auth)
    verdict = ns["prod_pose_deferred_verify"](pending)
    check("T.p7_detects_a_wrong_evaluated_skeleton_with_correct_inputs", B.all_keys(w) == keys and
          verdict.get(u"phase") == u"committed-unverified" and any(
              u"BODY-P7-unverified" in l and u"bone " in l for l in ns["LOG"][-4:]), (verdict, ns["LOG"][-1:]))
    # P7: a constraint offset changed after the commit (a changed description) is unverified.
    w = world(fx)
    auth, got = apply_(ns, reg, item, w)
    [el for op, el in w.ops if op["name"] == u"orientConstraint_ValveBiped.Bip01_Neck1"][0].attrs[
        "targets"].items[0].set("oOffset", FB.Quaternion(*B.rotate([0.0, 0.0, 0.0, 1.0], [1, 0, 0], 2.0)))
    verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth))
    check("T.p7_after_a_structural_change_is_unverified", verdict.get(u"phase") == u"committed-unverified", verdict)
    # P7: a conflicting authority added after the commit prevents a verified success.
    w = world(fx)
    auth, got = apply_(ns, reg, item, w)
    B.external_constraint(w, u"ValveBiped.Bip01_R_Finger42")
    verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth))
    check("T.p7_after_a_new_external_constraint_is_unverified", verdict.get(u"phase") == u"committed-unverified",
          verdict)
    w.dm.push_foreign(u"Move Control")
    check("T.p7_with_a_foreign_undo_entry_is_unverified", ns["prod_pose_deferred_verify"](dict(
        got[1][u"pending"], authorization=auth)).get(u"phase") == u"committed-unverified")


def section_face(ns, reg, fx, root):
    """The artist-confirmed face exclusion: recorded, preserved at Apply, listed by Pose Info."""
    lib = library(root, u"face")
    use(ns, world(fx, posed=False))
    face = [{u"id": u"face", u"bones": [u"JAW"], u"reason": u"expression controls left unchanged by the artist",
             u"provenance": u"user_confirmed", u"policy_revision": None, u"label": u"Face"}]
    pose, saved, item = save(ns, reg, lib, u"Fox Face", exclusions=face)
    region = pose[u"regions"][u"full_body"]
    check("F.exclusion_is_recorded_and_its_bone_not_saved", region[u"exclusions"] == [
        {u"id": u"face", u"bones": [u"JAW"], u"provenance": u"user_confirmed", u"label": u"Face"}] and
        u"JAW_o" not in region[u"orientations"] and [b[u"class"] for b in region[u"descriptor"][u"bones"]
                                                     if b[u"name"] == u"JAW"] == [u"fk-preserved"])

    def open_jaw(w):
        layer = w.channels[u"JAW_o"].attrs["log"].layer
        for k in layer.keys:
            k[1] = FB.native(B.rotate(FB.plain(k[1]), [0.0, 0.0, 1.0], 12.0), "quat")
    w = world(fx, open_jaw)
    jaw_keys, jaw_local = w.keys(u"JAW_o"), w.local(w.bone_dag[u"JAW"])
    auth, got = apply_(ns, reg, item, w)
    verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth)) if got[0] == u"ok" else None
    check("F.excluded_bone_keeps_its_keys_and_local_pose_and_verifies", verdict is not None and
          verdict.get(u"phase") == u"committed-verified" and w.keys(u"JAW_o") == jaw_keys and
          w.local(w.bone_dag[u"JAW"]) == jaw_local, (got[:2], verdict))
    view = ns["prod_pose_info_view"](item[u"record"])
    rows = dict((r[0].rstrip(u":"), r[1]) for r in view[u"rows"])
    check("F.pose_info_lists_the_face_exclusion", rows.get(u"Type") == u"Full body" and
          u"Face controls" in (rows.get(u"Not included") or u""), rows)
    return lib, item


# ---------------------------------------------------------------------------
# C. Records: the explicit contract revision, malformed records and the legacy reader
# ---------------------------------------------------------------------------

def tampered(ns, record, fn, digest=True):
    r = json.loads(json.dumps(record))
    fn(r)
    if digest:
        r[u"payload_sha256"] = ns["prod_pose_payload_digest"](r[u"pose"])
    return ns["prod_pose_serialize"](r)


def section_records(ns, reg, item, legacy_path):
    record = item[u"record"]
    raw = ns["prod_pose_serialize"](record)
    check("C.structural_record_validates", outcome(lambda: ns["prod_pose_parse"](raw, reg))[0] == u"ok")
    no_body = dict(reg, _body=None)
    check("C.structural_record_needs_no_body_registry", outcome(lambda: ns["prod_pose_parse"](raw, no_body))[0] ==
          u"ok")
    fb = u"full_body"
    cases = (
        (u"missing_adapter", lambda r: r[u"pose"].pop(u"adapter")),
        (u"adapter_and_registry", lambda r: r[u"pose"].__setitem__(u"registry", {
            u"profile_set": u"cpm-body-profiles", u"version": 1})),
        (u"unknown_rule", lambda r: r[u"pose"][u"adapter"].__setitem__(u"rule", u"structural_rig_v9")),
        (u"unknown_revision", lambda r: r[u"pose"][u"adapter"].__setitem__(u"revision", 2)),
        (u"registry_profile_id", lambda r: r[u"pose"][u"regions"][fb].__setitem__(u"profile_id", u"body_krystal_v1")),
        (u"instance_rig_name", lambda r: r[u"pose"][u"regions"][fb][u"descriptor"].__setitem__(
            u"rig_name", u"rig_biped_foxmccouldwm1")),
        (u"preserved_bone_without_exclusion", lambda r: [b.__setitem__(u"class", u"fk-preserved") for b in r[
            u"pose"][u"regions"][fb][u"descriptor"][u"bones"] if b[u"name"] == u"JAW"]),
        (u"exclusion_not_preserved", lambda r: r[u"pose"][u"regions"][fb].__setitem__(u"exclusions", [
            {u"id": u"face", u"bones": [u"JAW"], u"provenance": u"user_confirmed", u"label": u"Face"}])),
        (u"unconfirmed_exclusion", lambda r: r[u"pose"][u"regions"][fb].__setitem__(u"exclusions", [
            {u"id": u"face", u"bones": [u"JAW"], u"provenance": u"supported_metadata", u"label": u"Face"}])),
        (u"passive_bone", lambda r: [b.__setitem__(u"class", u"passive") for b in r[u"pose"][u"regions"][fb][
            u"descriptor"][u"bones"] if b[u"name"] == u"JAW"]),
        (u"two_placement_handles", lambda r: r[u"pose"][u"regions"][fb][u"descriptor"][u"handles"][
            u"rig_pelvis"].__setitem__(u"class", u"placement")),
        (u"registry_rig_class", lambda r: r[u"pose"][u"source"].__setitem__(u"rig_class", u"krystal-v1")),
        (u"missing_exclusions", lambda r: r[u"pose"][u"regions"][fb].pop(u"exclusions")),
    )
    for label, fn in cases:
        refused("C.malformed_%s_is_invalid" % label, outcome(lambda: ns["prod_pose_parse"](
            tampered(ns, record, fn), reg)), u"invalid-file")
    refused("C.digest_mismatch_is_invalid", outcome(lambda: ns["prod_pose_parse"](tampered(
        ns, record, lambda r: r[u"pose"][u"regions"][fb][u"orientations"].__setitem__(
            u"rig_hand_L_o", [0.0, 0.0, 0.0, 1.0]), digest=False), reg)), u"invalid-file")
    # Saved metadata never authorizes a write: a valid record whose descriptor claims a channel the destination
    # does not write refuses at P1 against the destination's own drafted description.
    def claim(r):
        reg_ = r[u"pose"][u"regions"][fb]
        reg_[u"descriptor"][u"channels"][u"rig_knee_L_o"][u"role"] = u"handle-written"
        reg_[u"orientations"][u"rig_knee_L_o"] = [0.0, 0.0, 0.0, 1.0]
    forged = ns["prod_pose_parse"](tampered(ns, record, claim), reg)
    w = world(FIXTURE_DATA[0])
    _, got = apply_(ns, reg, dict(item, record=forged), w)
    refused("C.forged_record_claiming_an_extra_write_refuses", got, u"rig-differs")
    check("C.forged_record_changes_nothing", no_mutation(w))

    # The legacy reader (RC2, the preserved release baseline) refuses the record as unreadable.
    if legacy_path is None:
        try:
            src = subprocess.check_output(["git", "-C", core._REPO_ROOT, "show", "%s:cpm/app/"
                                           "SFM_Character_Preset_Manager.py" % RC2_COMMIT])
        except Exception as exc:
            check("C.legacy_rc2_source_available", False, repr(exc))
            return
        fd, legacy_path = tempfile.mkstemp(suffix="_rc2_cpm.py")
        with os.fdopen(fd, "wb") as f:
            f.write(src)
    saved_path = route.APP_PATH
    saved_out = sys.stdout
    try:
        route.APP_PATH = legacy_path
        sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
        old = B.build_namespace(route.AppSource(legacy_path))
        arm, body = B.registries(old)
    finally:
        route.APP_PATH = saved_path
        sys.stdout = saved_out
    check("C.legacy_reader_is_the_rc2_build", core.sha(core.read(legacy_path)) ==
          u"7aa0fc4e159756f288a26819d9f8400f6f665bd797e5aff1c03ffac3a87eba47", core.sha(core.read(legacy_path)))
    refused("C.legacy_rc2_reader_refuses_the_structural_record", outcome(lambda: old["prod_pose_parse"](raw, arm)),
            u"invalid-file")
    check("C.legacy_rc2_reader_still_reads_registry_records", outcome(lambda: old["prod_pose_parse"](
        ns["prod_pose_serialize"](KRYSTAL_RECORD[0]), arm))[0] == u"ok")


# ---------------------------------------------------------------------------
# E. The Poses window: Save New dialog route, Apply dispatch, Update, production behaviour
# ---------------------------------------------------------------------------

def section_window(app, ns, reg, fx, root):
    lib = library(root, u"window")
    src = use(ns, world(fx, posed=False))
    mode = ns["PROD_POSE_REGISTRY_MODE"]

    def files():
        d = os.path.join(lib[u"char_dir"], u"Poses")
        return sorted(os.listdir(d)) if os.path.isdir(d) else []
    try:
        # Production (the RC2 baseline behaviour): Fox's Full body refuses as before; nothing is saved.
        win = B.window(app, ns, reg, lib)
        win.dialogs = []
        win.prompts = [u"Prod Fox"]
        got = win.save_pose(None, (u"full_body",))
        inv = win.dialogs[-1][0] if win.dialogs else None
        check("E.production_fox_full_body_keeps_the_rc2_refusal", got is None and not files() and inv is not None and
              inv[u"full_body"][u"status"] == u"refused" and inv[u"full_body"][u"code"] == u"rig-driven" and
              not inv.get(u"structural_rig") and not any(u"BODY-RIG" in l for l in ns["LOG"][-40:]),
              (win.statuses[-1:], inv and inv[u"full_body"]))
        # Qualification build: the structural route reaches the dialog and saves a version 2 record.
        ns["PROD_POSE_REGISTRY_MODE"] = QUAL
        win = B.window(app, ns, reg, lib)
        win.dialogs = []
        win.prompts = [u"Window Fox"]
        saved = win.save_pose(None, (u"full_body",))
        inv, body_route = win.dialogs[-1]
        check("E.qualification_dialog_offers_full_body_through_the_structural_route",
              inv.get(u"structural_rig") is True and inv[u"full_body"][u"status"] == u"available" and
              body_route is False and saved is not None and ns["prod_body_rig_is_record"](saved[u"record"]) and
              win.statuses[-1][1] == u"Pose saved: Window Fox.", (win.statuses[-1:], inv[u"full_body"]))
        state = ns["prod_scope_dialog_state"](inv, {u"kind": u"full_body", u"bones": [], u"exclude_highlighted": False})
        check("E.dialog_state_enables_full_body_save", state[u"save_enabled"] is True and state[u"request"] == {
            u"kind": u"full_body", u"bones": [], u"exclusions": []}, state)
        check("E.review_offers_only_directly_animated_face_bones", all(
            ns["prod_body_rig_probe"](ctx(ns), IDENTITY, reg, QUAL)[u"classes"].get(b) == u"fk"
            for b in inv[u"highlighted"]), inv[u"highlighted"])
        check("E.save_writes_nothing_to_the_scene", no_mutation(src))
        # Leave the reviewed face controls unchanged: the user-confirmed exclusion reaches the record.
        if inv[u"highlighted"]:
            win.prompts = [u"Window Fox Face"]
            real = win.prompt_pose_scope

            def leave(inventory, route_):
                win.dialogs.append((inventory, route_))
                st = ns["prod_scope_dialog_state"](inventory, {u"kind": u"full_body", u"bones": [],
                                                               u"exclude_highlighted": True})
                return {u"name": win.prompts.pop(0), u"kind": u"full_body", u"request": st[u"request"]}
            win.prompt_pose_scope = leave
            try:
                faced = win.save_pose(None, (u"full_body",))
            finally:
                del win.prompt_pose_scope
            del real
            check("E.leave_unchanged_records_the_confirmed_face_exclusion", faced is not None and sorted(
                faced[u"record"][u"pose"][u"regions"][u"full_body"][u"exclusions"][0][u"bones"]) == sorted(set(
                    inv[u"highlighted"])), win.statuses[-1:])
        # Selected parts on the same rigged character stays a version 3 pose.
        win.scope_kind = u"selected_parts"
        win.prompts = [u"Fox Fingers"]
        real_prompt = B.FakeWindow.prompt_pose_scope

        def parts(self, inventory, route_):
            self.dialogs.append((inventory, route_))
            return {u"name": self.prompts.pop(0), u"kind": u"selected_parts", u"request": {
                u"kind": u"selected_parts", u"bones": [u"ValveBiped.Bip01_R_Finger1"], u"exclusions": []}}
        B.FakeWindow.prompt_pose_scope = parts
        try:
            fingers = win.save_pose(None, (u"full_body",))
        finally:
            B.FakeWindow.prompt_pose_scope = real_prompt
            win.scope_kind = None
        check("E.selected_parts_on_a_rigged_character_stays_version_3", fingers is not None and
              fingers[u"record"][u"pose"][u"version"] == 3, win.statuses[-1:])
        # Apply through the window dispatch, the deferred verification, Update in place.
        dst = use(ns, world(fx))
        item = ns["prod_pose_reread"](lib, saved, reg)
        win.pending = []
        win.apply_pose(item)
        check("E.apply_dispatches_the_body_transaction", len(win.pending) == 1 and bool(win.pending[0].get(u"body"))
              and [c[0] for c in dst.dm.calls] == ["StartUndo", "FinishUndo"], win.statuses[-1:])
        verdict = ns["prod_pose_deferred_verify"](win.pending[0])
        check("E.deferred_turn_verifies_the_structural_pose", verdict.get(u"phase") == u"committed-verified", verdict)
        use(ns, src)
        layer = src.channels[u"rig_spine_1_o"].attrs["log"].layer
        for k in layer.keys:
            k[1] = FB.native(B.rotate(FB.plain(k[1]), [0.0, 1.0, 0.0], 15.0), "quat")
        src.evaluate()
        win.confirm = True
        updated = win.update_pose(ns["prod_pose_reread"](lib, saved, reg))
        check("E.update_recaptures_the_structural_record_in_place", updated is not None and
              updated[u"preset_id"] == saved[u"preset_id"] and ns["prod_body_rig_is_record"](updated[u"record"]) and
              updated[u"record"][u"pose"][u"regions"][u"full_body"][u"orientations"][u"rig_spine_1_o"] !=
              saved[u"record"][u"pose"][u"regions"][u"full_body"][u"orientations"][u"rig_spine_1_o"],
              win.statuses[-1:])
        # Production build with a structural record: Apply refuses before any write.
        ns["PROD_POSE_REGISTRY_MODE"] = PROD
        dst = use(ns, world(fx))
        win.apply_pose(ns["prod_pose_reread"](lib, updated, reg))
        check("E.production_apply_of_a_structural_record_refuses", win.statuses[-1][2] == u"not-qualified" and
              no_mutation(dst), win.statuses[-1])
        ns["PROD_POSE_REGISTRY_MODE"] = QUAL
        # A character outside Stage 1 (a control-less bone, as Tails' jiggle tips): the generic refusal stands.
        def jiggle(w):
            ch = w.channels[u"ValveBiped.Bip01_R_Finger42_o"]
            ch.set("fromElement", None)
        use(ns, world(fx, jiggle, posed=False))
        win.dialogs = []
        win.prompts = [u"Tails-like"]
        got = win.save_pose(None, (u"full_body",))
        inv = win.dialogs[-1][0] if win.dialogs else {}
        check("E.control_less_bones_keep_the_generic_refusal", got is None and not inv.get(u"structural_rig") and
              inv.get(u"full_body", {}).get(u"status") == u"refused" and any(
                  u"BODY-RIG-unavailable" in l for l in ns["LOG"][-40:]), win.statuses[-1:])
    finally:
        ns["PROD_POSE_REGISTRY_MODE"] = mode


FIXTURE_DATA = []
KRYSTAL_RECORD = []


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run [--legacy=RC2_CPM.py]" % os.path.basename(sys.argv[0]))
        return 2
    legacy = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--legacy=")]
    print("F-01 Stage 1 structural rig support (Python %s)" % sys.version.split()[0])
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    app = route.AppSource(route.APP_PATH)
    root = tempfile.mkdtemp(prefix="cpm_f01_rig_")
    try:
        ns = B.live_namespace(app)
        fx = fixture()
        FIXTURE_DATA.append(fx)
        reg, _ = B.registries(ns)
        # A Krystal registry record (stage E's own payload of the S0 fixture) for the legacy reader check.
        kfx = B.fixture("s0_shot15.json")
        profile = B.profile_of(ns, reg)
        os.makedirs(os.path.join(root, u"k"))
        klib = {u"character_key": u"krystal2020", u"char_dir": os.path.join(root, u"k", u"Characters",
                                                                             u"krystal2020"),
                u"library_root": os.path.join(root, u"k"), u"model_ref": B.MODEL}
        KRYSTAL_RECORD.append(ns["prod_pose_save_new"](klib, u"Krystal K", B.body_pose(
            ns, kfx, ns["prod_body_classify"](kfx, profile), profile), u"20261118-110000-000000", reg)[u"record"])
        drafted = run("draft", lambda: section_draft(ns, fx))
        if drafted:
            run("draft_refusals", lambda: section_draft_refusals(ns, drafted[0], drafted[1]))
            run("portability", lambda: section_portability(ns, drafted[0], drafted[1]))
        lived = run("live", lambda: section_live(ns, reg, fx, root))
        if lived:
            run("live_refusals", lambda: section_live_refusals(ns, reg, fx, lived[1]))
            run("transaction", lambda: section_transaction(ns, reg, fx, lived[1]))
            run("records", lambda: section_records(ns, reg, lived[1], legacy[0] if legacy else None))
        run("face", lambda: section_face(ns, reg, fx, root))
        run("window", lambda: section_window(app, ns, reg, fx, root))
    finally:
        shutil.rmtree(root, True)
    failed = [r for r in RESULTS if not r[1]]
    print("RESULT: %d/%d %s (%s)" % (len(RESULTS) - len(failed), len(RESULTS),
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
