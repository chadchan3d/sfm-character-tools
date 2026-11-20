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
import re
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
    # Production build (v1.1.0 RC3: the adapter is qualified): Save and Apply are authorized exactly as in the
    # qualification build, the structural mapping carries its evidence, the probe admits, and the Apply verifies.
    w = world(fx)
    use(ns, w)
    got = outcome(lambda: authorize(ns, reg, u"Apply Pose", item, mode=PROD))
    mapping = got[1][u"mappings"][0] if got[0] == u"ok" else {}
    check("R.rc3_production_build_authorizes_a_structural_apply", got[0] == u"ok" and got[1][u"mode"] == PROD and
          mapping.get(u"status") == u"qualified" and bool(mapping.get(u"evidence")), got if got[0] != u"ok" else mapping)
    check("R.rc3_production_build_authorizes_a_structural_save",
          outcome(lambda: authorize(ns, reg, u"Save Pose", mode=PROD))[0] == u"ok")
    probe = ns["prod_body_rig_probe"](ctx(ns), IDENTITY, reg, PROD)
    check("R.rc3_production_probe_admits_without_writing", probe is not None and probe == ns["prod_body_rig_probe"](
        ctx(ns), IDENTITY, reg, QUAL) and no_mutation(w))
    auth, got = apply_(ns, reg, item, world(fx), mode=PROD)
    verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth)) if got[0] == u"ok" and         got[1].get(u"pending") else None
    check("R.rc3_production_apply_verifies", verdict is not None and verdict.get(u"phase") == u"committed-verified",
          (got[:2], verdict))
    # The RC2 behaviour, kept against the experimental status: Apply and Save refuse and the probe is inert.
    status = ns["PROD_BODY_RIG_STATUS"]
    ns["PROD_BODY_RIG_STATUS"] = u"experimental"
    try:
        w = world(fx)
        use(ns, w)
        got = outcome(lambda: authorize(ns, reg, u"Apply Pose", item, mode=PROD))
        refused("R.production_build_refuses_a_structural_apply", got, u"not-qualified")
        refused("R.production_build_refuses_a_structural_save", outcome(lambda: authorize(ns, reg, u"Save Pose",
                                                                                          mode=PROD)), u"not-qualified")
        check("R.production_probe_is_inert", ns["prod_body_rig_probe"](ctx(ns), IDENTITY, reg, PROD) is None and
              no_mutation(w))
        check("R.experimental_authorization_carries_no_evidence", authorize(ns, reg, u"Save Pose")[u"mappings"][0][
            u"evidence"] is None)
    finally:
        ns["PROD_BODY_RIG_STATUS"] = status
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
        # Production with the RC2 experimental status: Fox's Full body refuses as before; nothing is saved.
        status = ns["PROD_BODY_RIG_STATUS"]
        ns["PROD_BODY_RIG_STATUS"] = u"experimental"
        try:
            win = B.window(app, ns, reg, lib)
            win.dialogs = []
            win.prompts = [u"Prod Fox"]
            got = win.save_pose(None, (u"full_body",))
            inv = win.dialogs[-1][0] if win.dialogs else None
            check("E.production_fox_full_body_keeps_the_rc2_refusal", got is None and not files() and
                  inv is not None and inv[u"full_body"][u"status"] == u"refused" and
                  inv[u"full_body"][u"code"] == u"rig-driven" and not inv.get(u"structural_rig") and
                  not any(u"BODY-RIG" in l for l in ns["LOG"][-40:]), (win.statuses[-1:], inv and inv[u"full_body"]))
        finally:
            ns["PROD_BODY_RIG_STATUS"] = status
        # RC3 production (the adapter qualified): the same dialog offers Full body through the structural route.
        win = B.window(app, ns, reg, lib)
        win.dialogs = []
        win.prompts = [u"Prod Fox"]
        prod_saved = win.save_pose(None, (u"full_body",))
        inv, body_route = win.dialogs[-1]
        check("E.rc3_production_dialog_offers_full_body_through_the_structural_route",
              inv.get(u"structural_rig") is True and inv[u"full_body"][u"status"] == u"available" and
              body_route is False and prod_saved is not None and ns["prod_body_rig_is_record"](prod_saved[u"record"])
              and win.statuses[-1][1] == u"Pose saved: Prod Fox." and len(files()) == 1,
              (win.statuses[-1:], inv[u"full_body"]))
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
        # C2 (Designer, after Fox run 1): no scope review on the structural route. Every bone of a drafted description
        # is classified confidently, so the Face-group jaw and tongue are supported articulation that follows the
        # pose; facial expressions (flexes) stay preserved.
        record = saved[u"record"][u"pose"][u"regions"][u"full_body"]
        check("E.c2_structural_dialog_has_no_review_and_the_plain_summary", inv[u"highlighted"] == [] and
              state[u"review"] == [] and state[u"summary"] == u"Facial expressions and the rootTransform are not "
              u"saved.", (inv[u"highlighted"], state[u"summary"]))
        check("E.c2_jaw_and_tongue_follow_the_saved_pose", record[u"exclusions"] == [] and
              u"JAW_o" in record[u"orientations"] and u"tonge2_o" in record[u"orientations"] and
              not [b for b in record[u"descriptor"][u"bones"] if b[u"class"] == u"fk-preserved"])
        check("E.c2_flex_controls_stay_preserved", not [n for n in list(record[u"orientations"]) +
                                                       list(record[u"positions"]) if u"flex" in n])
        v3 = ns["prod_scope_inventory"](IDENTITY, ns["prod_scope_authorize"](ctx(ns), IDENTITY, reg, QUAL,
                                                                            u"Save Pose"))
        check("E.c2_the_generic_v3_review_is_unchanged", v3[u"highlighted"] == [u"JAW", u"tonge", u"tonge1",
                                                                              u"tonge2", u"tonge3", u"tonge4"],
              v3[u"highlighted"])
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
        # C1: the Poses page's availability for structural records (the button only; Apply still verifies).
        av = ns["prod_body_rig_availability"]
        rec = saved[u"record"]
        future = json.loads(json.dumps(rec))
        future[u"pose"][u"adapter"][u"revision"] = 3        # unknown (Stage 2 defines revision 2)
        check("E.c1_availability_same_model_in_qualification", av(rec, IDENTITY, QUAL) == u"available" and
              av(rec, dict(IDENTITY, model=MODEL.upper()), QUAL) == u"available")
        check("E.c1_availability_refuses_other_models_and_unknown_revisions",
              av(rec, dict(IDENTITY, model=u"models/x.mdl"), QUAL) == u"different-model" and
              av(rec, None, QUAL) == u"different-model" and av(future, IDENTITY, QUAL) == u"not-qualified" and
              av(rec, dict(IDENTITY, model=u"models/x.mdl"), PROD) == u"different-model" and
              av(future, IDENTITY, PROD) == u"not-qualified")
        check("E.rc3_availability_same_model_in_production", av(rec, IDENTITY, PROD) == u"available")
        ns["PROD_BODY_RIG_STATUS"] = u"experimental"
        check("E.c1_availability_refuses_production_while_experimental", av(rec, IDENTITY, PROD) == u"not-qualified"
              and av(rec, IDENTITY, QUAL) == u"available")
        # Production build with a structural record and the RC2 experimental status: Apply refuses before any write.
        ns["PROD_POSE_REGISTRY_MODE"] = PROD
        try:
            dst = use(ns, world(fx))
            win.apply_pose(ns["prod_pose_reread"](lib, updated, reg))
            check("E.production_apply_of_a_structural_record_refuses", win.statuses[-1][2] == u"not-qualified" and
                  no_mutation(dst), win.statuses[-1])
        finally:
            ns["PROD_BODY_RIG_STATUS"] = status
        # RC3 production: the same record applies through the window dispatch and verifies.
        dst = use(ns, world(fx))
        win.pending = []
        win.apply_pose(ns["prod_pose_reread"](lib, updated, reg))
        verdict = ns["prod_pose_deferred_verify"](win.pending[0]) if len(win.pending) == 1 else None
        check("E.rc3_production_apply_of_a_structural_record_verifies", verdict is not None and
              verdict.get(u"phase") == u"committed-verified" and [c[0] for c in dst.dm.calls] == ["StartUndo",
                                                                                                "FinishUndo"],
              (win.statuses[-1:], verdict))
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
        check("E.c3_unsupported_full_body_shows_the_owner_wording", inv.get(u"full_body", {}).get(u"message") ==
              u"Full body poses aren't supported for this character yet. You can still save Selected parts." and
              ns["prod_scope_dialog_state"](inv, {u"kind": u"full_body"})[u"summary"] ==
              inv.get(u"full_body", {}).get(u"message") and any(
                  u"SCOPE-refused" in l and u"rig-driven" in l for l in ns["LOG"][-40:]), inv.get(u"full_body"))
        check("E.control_less_bones_keep_the_generic_refusal", got is None and not inv.get(u"structural_rig") and
              inv.get(u"full_body", {}).get(u"status") == u"refused" and any(
                  u"BODY-RIG-unavailable" in l for l in ns["LOG"][-40:]), win.statuses[-1:])
    finally:
        ns["PROD_POSE_REGISTRY_MODE"] = mode


# ---------------------------------------------------------------------------
# N. Astra's numerical compatibility ruling (run 2): bounded rotation equivalence of the three static constraint
#    rotation offsets in the saved-record comparison, and structural constraint matching
# ---------------------------------------------------------------------------

RUN2_RECORD = os.path.join(_THIS_DIR, "fixtures", "f01_body", "fox_run2_s1_fox_record.json")
RUN2_RECORD_SHA256 = "da8ca5283583ebb89172a1f1700e4cff4f27c43fac36d7d615db857e514579e7"
RUN2_CANDIDATE_COMMIT = "94f21df"     # CPM 1753bdba..., the build run 2 used (qualification differs in one line)
RUN2_CANDIDATE_SHA256 = u"1753bdbaeb1544aa98679c89b9c4cc65b51861c40fb0975d9d5f315ca8f43baa"
# The paths of run 2's native refusal (process B log, PROD_POSE_BODY-refused, rig-differs; truncated at 16 there).
RUN2_NATIVE_PATHS = [u"/constraints/%s/solver/%s/value/%d" % (c, f, i) for c, f in (
    (4, u"startOffset"), (5, u"midOffset"), (6, u"midOffset"), (6, u"startOffset")) for i in range(4)]
ROTATION_FIELDS = ((u"solver", u"startOffset"), (u"solver", u"midOffset"), (u"offsets", u"oOffset"))


def sfm_reload(q):
    """Test model of SFM's session load (measured on run 2, all 618 quaternion keys, independently verified by Astra):
    q * f32(1 / f32(sqrt(q.q))), the dot product summed in order in float32. Not CPM's rule."""
    f = B.f32
    s = f(q[0] * q[0])
    for c in q[1:]:
        s = f(s + f(c * c))
    inv = f(1.0 / f(math.sqrt(s)))
    return [f(c * inv) for c in q]


def reload_world(w, times=1):
    """A session save and reopen of a fake scene: every stored quaternion (attributes and log keys) renormalized."""
    for _ in range(times):
        for el in list(w.elements.values()):
            for k, v in list(el.attrs.items()):
                if isinstance(v, FB.Quaternion):
                    el.attrs[k] = FB.Quaternion(*sfm_reload([v.x, v.y, v.z, v.w]))
            for key in getattr(el, "keys", None) or [] if isinstance(el, FB.Layer) else []:
                if isinstance(key[1], FB.Quaternion):
                    key[1] = FB.Quaternion(*sfm_reload(FB.plain(key[1])))
    w.evaluate()


def run2_namespace():
    """The run 2 candidate CPM (1753bdba...) from Git, for the teeth checks."""
    return git_namespace(RUN2_CANDIDATE_COMMIT)


def git_namespace(commit):
    """An earlier candidate CPM from Git, in the stage E live namespace, for teeth checks."""
    src = subprocess.check_output(["git", "-C", core._REPO_ROOT, "show", "%s:cpm/app/SFM_Character_Preset_Manager.py"
                                   % commit])
    fd, path = tempfile.mkstemp(suffix="_%s_cpm.py" % commit)
    with os.fdopen(fd, "wb") as f:
        f.write(src)
    saved_path, saved_out = route.APP_PATH, sys.stdout
    try:
        route.APP_PATH = path
        sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
        old = B.live_namespace(route.AppSource(path))
    finally:
        route.APP_PATH = saved_path
        sys.stdout = saved_out
    return old, core.sha(core.read(path))


def rows_fields(desc):
    for i, row in enumerate(desc[u"constraints"]):
        for group, name in ROTATION_FIELDS:
            f = (row.get(group) or {}).get(name)
            if isinstance(f, dict) and f.get(u"present"):
                yield i, group, name, f


def reloaded_descriptor(desc, times=1):
    out = copy.deepcopy(desc)
    for _ in range(times):
        for i, group, name, f in rows_fields(out):
            f[u"value"] = sfm_reload(f[u"value"])
    return out


def axis_angle(axis, degrees):
    n = math.sqrt(sum(c * c for c in axis))
    h = math.radians(degrees) / 2.0
    return [axis[0] / n * math.sin(h), axis[1] / n * math.sin(h), axis[2] / n * math.sin(h), math.cos(h)]


def compare(ns, saved, live):
    return outcome(lambda: ns["prod_body_compare_descriptor"](saved, live))


def last_log(ns, tag):
    lines = [l for l in ns["LOG"] if tag in l]
    return lines[-1] if lines else u""


def refusal_diagnostic(ns):
    line = last_log(ns, u"BODY-refused")
    try:
        detail = json.loads(line[line.index(u"{"):])[u"detail"]
        return json.loads(detail[detail.index(u"): ") + 3:].rstrip())
    except Exception:
        return None


def section_rotation(ns, reg, fx, item):
    old, old_sha = run2_namespace()
    check("N.teeth_build_is_the_run2_candidate", old_sha == RUN2_CANDIDATE_SHA256, old_sha)
    raw = core.read(RUN2_RECORD)
    check("N.run2_record_matches_its_pin", core.sha(raw) == RUN2_RECORD_SHA256, core.sha(raw))
    record = json.loads(raw.decode("utf-8"))
    saved = record[u"pose"][u"regions"][u"full_body"][u"descriptor"]
    pristine = copy.deepcopy(saved)
    limit = ns["PROD_BODY_ROTATION_LIMIT_DEG"]
    check("N.contract_constants", limit == 0.0005 and ns["PROD_BODY_ROTATION_NORM_LIMIT"] == 2.0 ** -19 and
          [tuple(f) for f in ns["PROD_BODY_ROTATION_FIELDS"]] == list(ROTATION_FIELDS))

    # 1. Replay of run 2: SFM's load changes exactly the five offsets; the run 2 build refuses with the native paths;
    #    the corrected comparison admits them, against the unchanged saved record.
    live = reloaded_descriptor(saved)
    changed = [(i, name) for (i, g, name, f), (_, _, _, h) in zip(rows_fields(saved), rows_fields(live))
               if f[u"value"] != h[u"value"]]
    check("N.replay_sfm_load_changes_exactly_the_five_run2_offsets", changed == [
        (4, u"startOffset"), (5, u"midOffset"), (6, u"startOffset"), (6, u"midOffset"), (35, u"oOffset")], changed)
    got = compare(old, saved, live)
    paths = re.findall(r"/constraints/\d+/\w+/\w+/value/\d", got[2] if got[0] != "ok" else u"") if got[0] != "ok" \
        else []
    logged = re.findall(r"/constraints/\d+/\w+/\w+/value/\d", last_log(old, u"BODY-refused"))
    check("N.replay_teeth_the_run2_build_refuses_with_the_native_paths", got[0] != "ok" and got[1] == u"rig-differs"
          and logged == RUN2_NATIVE_PATHS, (got[:2], logged))
    del ns["LOG"][:]
    got = compare(ns, saved, live)
    eq = last_log(ns, u"BODY-rotation-equivalent")
    check("N.replay_corrected_comparison_admits_the_reloaded_rig", got[0] == "ok" and u'"count": 5' in eq and
          u'"limit_deg": 0.0005' in eq, (got, eq))
    angles = [ns["prod_body_rotation_angle"](f[u"value"], h[u"value"]) for (i, g, n, f), (_, _, _, h) in zip(
        rows_fields(saved), rows_fields(live))]
    check("N.replay_measured_angles_are_float32_rounding", 0.0 < max(angles) < 1e-4, max(angles))
    check("N.replay_never_modifies_the_saved_record", saved == pristine)

    # 2. Repeated loads (including a two-cycle), always against the original saved value; no accumulation.
    for k in (2, 3, 6):
        check("N.repeated_load_%d_times_is_admitted_against_the_record" % k,
              compare(ns, saved, reloaded_descriptor(saved, k))[0] == "ok")
    rng = __import__("random").Random(7)
    cycle = None
    for _ in range(20000):
        q = axis_angle([rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)], rng.uniform(1, 179))
        q = [B.f32(c * (1.0 + rng.gauss(0.0, 3e-7))) for c in q]
        x1 = sfm_reload(q)
        x2 = sfm_reload(x1)
        if x2 != x1 and sfm_reload(x2) == x1:
            cycle = q
            break
    check("N.a_real_float32_two_cycle_exists", cycle is not None)
    if cycle is not None:
        two = copy.deepcopy(saved)
        two[u"constraints"][4][u"solver"][u"startOffset"][u"value"] = cycle
        two_saved = copy.deepcopy(two)
        ok = all(compare(ns, two_saved, reloaded_descriptor(two, k))[0] == "ok" for k in range(1, 7))
        check("N.two_cycle_loads_admitted_against_the_original_value", ok and two == two_saved)
    axis = [0.3, -0.5, 0.8]
    step = axis_angle(axis, 0.0003)
    drift = copy.deepcopy(saved)
    target = drift[u"constraints"][4][u"solver"][u"startOffset"]
    target[u"value"] = list(FB.qmul(step, target[u"value"]))
    check("N.one_drift_step_within_the_bound_is_admitted", compare(ns, saved, drift)[0] == "ok")
    target[u"value"] = list(FB.qmul(step, target[u"value"]))
    got = compare(ns, saved, drift)
    check("N.cumulative_drift_beyond_the_bound_refuses_against_the_record", got[0] != "ok" and
          got[1] == u"rig-differs", got)

    # 3. Sign-equivalent static offsets are the same rotation.
    neg = copy.deepcopy(saved)
    for i, g, n, f in rows_fields(neg):
        f[u"value"] = [-c for c in f[u"value"]]
    check("N.sign_equivalent_offsets_are_admitted", compare(ns, saved, neg)[0] == "ok")
    check("N.sign_equivalent_reloaded_offsets_are_admitted", compare(ns, saved, reloaded_descriptor(neg))[0] == "ok")

    # 4. The angular boundary (inclusive), the formula, and rotations near 180 degrees.
    angle = ns["prod_body_rotation_angle"]
    a = axis_angle([1.0, 2.0, 3.0], 40.0)
    ref = math.degrees(2.0 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(a, axis_angle([1.0, 2.0, 3.0],
                                                                                             70.0)))))))
    check("N.formula_matches_the_reference_angle", abs(angle(a, axis_angle([1.0, 2.0, 3.0], 70.0)) - 30.0) < 1e-9 and
          abs(ref - 30.0) < 1e-6)
    check("N.formula_is_stable_near_zero", 0.0 < angle(a, list(FB.qmul(axis_angle([0, 0, 1], 1e-7), a))) < 2e-7)

    def with_offset(base, value):
        d = copy.deepcopy(saved)
        d[u"constraints"][4][u"solver"][u"startOffset"][u"value"] = base
        e = copy.deepcopy(saved)
        e[u"constraints"][4][u"solver"][u"startOffset"][u"value"] = value
        return d, e
    for base_deg, label in ((40.0, u"general"), (179.9999, u"near_180")):
        base = axis_angle([1.0, 2.0, 3.0], base_deg)
        for delta, want in ((0.0004999, "ok"), (0.0005001, "refused")):
            moved = axis_angle([1.0, 2.0, 3.0], base_deg + delta)
            if label == u"near_180":
                moved = [-c for c in moved]            # past 180: the w >= 0 representative has the other sign
            got = compare(ns, *with_offset(base, moved))
            check("N.%s_rotation_%s_degrees_%s" % (label, delta, "admitted" if want == "ok" else "refused"),
                  (got[0] == "ok") == (want == "ok") and (want == "ok" or got[1] == u"rig-differs"), got[:2])
        exact = axis_angle([1.0, 2.0, 3.0], base_deg + 0.0005)
        at = angle(base, exact)
        try:
            ns["PROD_BODY_ROTATION_LIMIT_DEG"] = at
            inclusive = compare(ns, *with_offset(base, exact))[0] == "ok"
            ns["PROD_BODY_ROTATION_LIMIT_DEG"] = at * (1.0 - 1e-12)
            beyond = compare(ns, *with_offset(base, exact))[0] != "ok"
        finally:
            ns["PROD_BODY_ROTATION_LIMIT_DEG"] = limit
        check("N.%s_boundary_is_inclusive" % label, inclusive and beyond and abs(at - 0.0005) < 1e-9, at)
    for deg in (0.01, 3.0, 90.0):
        moved = list(FB.qmul(axis_angle([0.0, 1.0, 0.0], deg), saved[u"constraints"][5][u"solver"][u"midOffset"][
            u"value"]))
        d = copy.deepcopy(saved)
        d[u"constraints"][5][u"solver"][u"midOffset"][u"value"] = moved
        got = compare(ns, saved, d)
        check("N.materially_changed_rotation_%s_degrees_refuses" % deg, got[0] != "ok" and got[1] == u"rig-differs",
              got[:2])

    # 5. Validity: four finite numbers, near-unit length on both sides, matching presence and representation.
    unit = saved[u"constraints"][4][u"solver"][u"startOffset"][u"value"]
    n_unit = math.sqrt(sum(c * c for c in unit))
    bad_values = (
        (u"zero", [0.0, 0.0, 0.0, 0.0]), (u"nan", [float("nan"), 0.0, 0.0, 1.0]),
        (u"infinite", [float("inf"), 0.0, 0.0, 1.0]), (u"bool", [True, 0.0, 0.0, 0.0]),
        (u"text", [u"x", 0.0, 0.0, 1.0]), (u"three", [0.0, 0.0, 1.0]), (u"five", [0.0, 0.0, 0.0, 1.0, 0.0]),
        (u"scalar", 1.0), (u"rescaled_same_rotation_norm_1_001", [c * 1.001 / n_unit for c in unit]),
        (u"norm_beyond_the_envelope", [c * (1.0 + 2.0 ** -18) / n_unit for c in unit]),
        (u"norm_below_the_envelope", [c * (1.0 - 2.0 ** -18) / n_unit for c in unit]))
    for label, value in bad_values:
        for side in (u"saved", u"live"):
            d, e = copy.deepcopy(saved), copy.deepcopy(saved)
            (d if side == u"saved" else e)[u"constraints"][4][u"solver"][u"startOffset"][u"value"] = value
            got = compare(ns, d, e)
            check("N.invalid_%s_on_the_%s_side_refuses" % (label, side), got[0] != "ok" and got[1] == u"rig-differs",
                  got[:2])
    d = copy.deepcopy(saved)
    d[u"constraints"][4][u"solver"][u"startOffset"][u"value"] = [c * (1.0 + 2.0 ** -21) / n_unit for c in unit]
    check("N.norm_within_the_envelope_is_admitted", compare(ns, saved, d)[0] == "ok")
    d = copy.deepcopy(saved)
    d[u"constraints"][4][u"solver"][u"startOffset"] = {u"present": False}
    check("N.present_versus_absent_refuses", compare(ns, saved, d)[1] == u"rig-differs" and
          compare(ns, d, saved)[1] == u"rig-differs")
    check("N.both_absent_is_admitted", compare(ns, d, copy.deepcopy(d))[0] == "ok")
    e = copy.deepcopy(saved)
    del e[u"constraints"][4][u"solver"][u"startOffset"]
    check("N.missing_field_refuses", compare(ns, saved, e)[1] == u"rig-differs")
    e = copy.deepcopy(saved)
    e[u"constraints"][4][u"solver"][u"startOffset"] = {u"value": unit}
    check("N.malformed_field_refuses", compare(ns, saved, e)[1] == u"rig-differs")
    e = copy.deepcopy(saved)
    e[u"constraints"][4][u"solver"][u"startOffset"] = dict(e[u"constraints"][4][u"solver"][u"startOffset"], extra=1)
    check("N.extra_field_member_refuses", compare(ns, saved, e)[1] == u"rig-differs")

    # Diagnostics: constraint identity, field, raw values, norms, angle and limit.
    del ns["LOG"][:]
    d = copy.deepcopy(saved)
    d[u"constraints"][6][u"solver"][u"midOffset"][u"value"] = list(FB.qmul(axis_angle([1, 0, 0], 2.0), d[
        u"constraints"][6][u"solver"][u"midOffset"][u"value"]))
    compare(ns, saved, d)
    diag = refusal_diagnostic(ns)
    row = diag[0] if diag else {}
    check("N.refusal_reports_identity_field_values_norms_angle_and_limit", diag is not None and set(row) >= set([
        u"constraint", u"field", u"saved", u"live", u"saved_norm", u"live_norm", u"angle_deg", u"limit_deg",
        u"norm_limit", u"problem"]) and row[u"field"] == u"solver.midOffset" and u"rig_knee_R" in row[u"constraint"]
        and abs(row[u"angle_deg"] - 2.0) < 1e-6 and row[u"limit_deg"] == 0.0005 and
        row[u"saved"] == saved[u"constraints"][6][u"solver"][u"midOffset"][u"value"], diag)

    # 6. Structural matching by (type, slaves, targets, pole).
    perm = reloaded_descriptor(saved)
    perm[u"constraints"].reverse()
    check("N.permuted_constraint_enumeration_is_admitted", compare(ns, saved, perm)[0] == "ok")
    rng.shuffle(perm[u"constraints"])
    check("N.shuffled_constraint_enumeration_is_admitted", compare(ns, saved, perm)[0] == "ok")

    # Value-dependent reordering: two rows whose full-JSON order (the descriptor's sort key) flips by a tiny change.
    def orient(slave, x):
        return {u"type": u"DmeRigOrientConstraintOperator", u"slaves": {u"slave": slave}, u"targets": [
            u"handle:" + slave], u"pole": None, u"solver": {u"mode": {u"present": True, u"value": 0}},
            u"offsets": {u"oOffset": {u"present": True, u"value": [x, 0.0, 0.0, math.sqrt(1.0 - x * x)]},
                         u"vecOffset": {u"present": True, u"value": [0.0, 0.0, 0.0]}}}
    key = lambda r: json.dumps(r, sort_keys=True)  # noqa: E731
    pair_saved = dict(saved, constraints=sorted([orient(u"bone:A", 0.1), orient(u"bone:B", 0.1000001)], key=key))
    pair_live = dict(saved, constraints=sorted([orient(u"bone:A", 0.1000002), orient(u"bone:B", 0.1000001)], key=key))
    flipped = [r[u"slaves"][u"slave"] for r in pair_saved[u"constraints"]] != [
        r[u"slaves"][u"slave"] for r in pair_live[u"constraints"]]
    check("N.value_dependent_reordering_reproduced", flipped)
    got_old = compare(old, pair_saved, pair_live)
    check("N.value_dependent_reordering_teeth_run2_build_refuses", got_old[0] != "ok" and got_old[1] ==
          u"rig-differs", got_old[:2])
    check("N.value_dependent_reordering_is_admitted_by_identity", compare(ns, pair_saved, pair_live)[0] == "ok")

    def mutated(fn, which=u"live"):
        d = copy.deepcopy(saved)
        fn(d)
        return (saved, d) if which == u"live" else (d, saved)
    ik = 4
    cases = (
        (u"duplicate_identity_live", lambda d: d[u"constraints"].append(copy.deepcopy(d[u"constraints"][ik])),
         u"live"),
        (u"duplicate_identity_saved", lambda d: d[u"constraints"].append(copy.deepcopy(d[u"constraints"][ik])),
         u"saved"),
        (u"missing_constraint", lambda d: d[u"constraints"].pop(ik), u"live"),
        (u"extra_constraint", lambda d: d[u"constraints"].append(orient(u"bone:Extra", 0.0)), u"live"),
        (u"changed_target", lambda d: d[u"constraints"][ik].__setitem__(u"targets", [u"handle:rig_hand_L"]),
         u"live"),
        (u"changed_pole", lambda d: d[u"constraints"][ik].__setitem__(u"pole", u"handle:rig_knee_R"), u"live"),
        (u"changed_type", lambda d: d[u"constraints"][0].__setitem__(u"type", u"DmeRigPointConstraintOperator"),
         u"live"),
        (u"changed_slave", lambda d: d[u"constraints"][0][u"slaves"].__setitem__(u"slave", u"bone:Other"), u"live"),
        (u"swapped_named_slave_slots", lambda d: d[u"constraints"][ik].__setitem__(u"slaves", dict(
            (k, v) for k, v in zip(sorted(d[u"constraints"][ik][u"slaves"]), reversed([
                d[u"constraints"][ik][u"slaves"][s] for s in sorted(d[u"constraints"][ik][u"slaves"])])))), u"live"),
        (u"changed_pole_vector", lambda d: d[u"constraints"][ik][u"solver"].__setitem__(u"poleVector", {
            u"present": True, u"value": [0.0, 1.0, 1e-7]}), u"live"),
        (u"changed_mode", lambda d: d[u"constraints"][ik][u"solver"].__setitem__(u"mode", {
            u"present": True, u"value": 1}), u"live"),
        (u"changed_vec_offset", lambda d: d[u"constraints"][0][u"offsets"].__setitem__(u"vecOffset", {
            u"present": True, u"value": [0.0, 5.245208740234375e-06, 1e-7]}), u"live"))
    for label, fn, which in cases:
        got = compare(ns, *mutated(fn, which))
        check("N.%s_refuses" % label, got[0] != "ok" and got[1] == u"rig-differs", got[:2])
    del ns["LOG"][:]
    dup = copy.deepcopy(saved)
    dup[u"constraints"].append(copy.deepcopy(dup[u"constraints"][ik]))
    dup[u"constraints"][5][u"solver"][u"midOffset"][u"value"] = [0.0, 0.0, 0.0, 0.0]
    got = compare(ns, saved, dup)
    check("N.duplicates_refuse_before_any_numerical_comparison", got[0] != "ok" and u"duplicated" in
          last_log(ns, u"BODY-refused"), last_log(ns, u"BODY-refused")[:200])
    two_targets = copy.deepcopy(saved)
    two_targets[u"constraints"][0][u"targets"] = [u"handle:a", u"handle:b"]
    swapped = copy.deepcopy(two_targets)
    swapped[u"constraints"][0][u"targets"] = [u"handle:b", u"handle:a"]
    check("N.target_order_is_part_of_the_identity", compare(ns, two_targets, swapped)[1] == u"rig-differs")
    check("N.the_rest_of_the_descriptor_stays_exact", compare(ns, saved, dict(saved, rig_name=u"@other"))[1] ==
          u"rig-differs" and compare(ns, saved, dict(saved, model_ref=u"x.mdl"))[1] == u"rig-differs")

    # 7. Live rigs: a reloaded destination applies and verifies; P2, Abort and P7 stay exact and independent.
    check("N.fixture_holds_reload_unstable_offsets", any(
        isinstance(v, FB.Quaternion) and sfm_reload([v.x, v.y, v.z, v.w]) != [v.x, v.y, v.z, v.w]
        for el in world(fx, posed=False).elements.values() for v in el.attrs.values()))
    source = placement_relative(use(ns, world(fx, posed=False)))
    oreg, _ = B.registries(old)
    w = world(fx, reload_world)
    _, got = apply_(old, oreg, item, w)
    refused("N.teeth_run2_build_refuses_a_reloaded_destination", got, u"rig-differs")
    check("N.teeth_refusal_changes_nothing", no_mutation(w))
    for times in (1, 3):
        w = world(fx, lambda w, t=times: reload_world(w, t))
        del ns["LOG"][:]
        auth, got = apply_(ns, reg, item, w)
        verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth)) if \
            got[0] == u"ok" and got[1].get(u"pending") else None
        check("N.destination_reloaded_%d_times_applies_and_verifies" % times, verdict is not None and verdict.get(
            u"phase") == u"committed-verified" and B.max_difference(placement_relative(w), source)[1] < 0.01 and any(
            u"BODY-rotation-equivalent" in l for l in ns["LOG"]), (got[:2], verdict))

    def negate_offsets(w):
        for el in list(w.elements.values()):
            for k in (u"startOffset", u"midOffset", u"oOffset"):
                v = el.attrs.get(k)
                if isinstance(v, FB.Quaternion):
                    el.attrs[k] = FB.Quaternion(-v.x, -v.y, -v.z, -v.w)
    w = world(fx, negate_offsets)
    auth, got = apply_(ns, reg, item, w)
    verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth)) if \
        got[0] == u"ok" and got[1].get(u"pending") else None
    check("N.sign_flipped_destination_offsets_apply_and_verify", verdict is not None and verdict.get(u"phase") ==
          u"committed-verified", (got[:2], verdict))

    # P2: any change of a live offset after P1 (one float32 step, or even a sign flip) is stale; nothing written.
    original = ns["prod_body_preflight"]
    for label, change in ((u"one_float32_step", lambda v: [v.x + 2.0 ** -23, v.y, v.z, v.w]),
                          (u"sign_flip", lambda v: [-v.x, -v.y, -v.z, -v.w])):
        w = world(fx, reload_world)
        ik_el = [el for op, el in w.ops if op["type"] == u"DmeRigIKConstraintOperator"][0]

        def preflight_then_change(*args):
            pre = original(*args)
            v = ik_el.attrs[u"startOffset"]
            ik_el.attrs[u"startOffset"] = FB.Quaternion(*change(v))
            return pre
        ns["prod_body_preflight"] = preflight_then_change
        try:
            _, got = apply_(ns, reg, item, w)
        finally:
            ns["prod_body_preflight"] = original
        refused("N.p2_detects_a_%s_offset_change_after_p1" % label, got, u"stale")
        check("N.p2_%s_writes_nothing" % label, not B.scene_writes(w))

    # Abort restores the exact live baseline (the destination's own reloaded offsets, never the saved values).
    w = world(fx, reload_world)
    offsets = dict((el.h, dict((k, FB.plain(v)) for k, v in el.attrs.items() if isinstance(v, FB.Quaternion)))
                   for el in w.elements.values())
    before = B.all_keys(w)
    w.fail_on_write = u"rig_spine_0_o"
    _, got = apply_(ns, reg, item, w)
    after_offsets = dict((el.h, dict((k, FB.plain(v)) for k, v in el.attrs.items() if isinstance(v, FB.Quaternion)))
                         for el in w.elements.values())
    check("N.abort_restores_the_exact_live_baseline", got[0] == u"ok" and got[1][u"phase"] == u"not-applied" and
          B.all_keys(w) == before and after_offsets == offsets, got[:2])

    # P7 stays an independent observation: a compatible (reloaded) rig whose evaluation is wrong is unverified.
    w = world(fx, reload_world)
    auth, got = apply_(ns, reg, item, w)
    solve = w.solve_ik

    def misbent(start, el, parent_world, parent_scale):
        solve(start, el, parent_world, parent_scale)
        w.set_world(start, start.wp, B.rotate(start.wq, [0.0, 0.0, 1.0], 10.0), parent_world, parent_scale)
    w.solve_ik = misbent
    w.evaluate()
    verdict = ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth))
    check("N.compatible_rig_with_wrong_reproduction_is_committed_unverified", verdict.get(u"phase") ==
          u"committed-unverified", verdict)

    # Authored quaternion keys keep their exact values and signs (no rotation equivalence for keys).
    def negate_keys(w):
        for name in (u"rig_elbow_L_o", u"rig_hand_L_o"):
            for k in w.channels[name].attrs["log"].layer.keys:
                v = FB.plain(k[1])
                k[1] = FB.Quaternion(-v[0], -v[1], -v[2], -v[3])
    w = world(fx, lambda w: (reload_world(w), negate_keys(w)))
    pole_before = w.keys(u"rig_elbow_L_o")
    reference = FB.plain(w.channels[u"rig_hand_L_o"].attrs["log"].value_at(w.t_chan()))
    others = [k for k in w.keys(u"rig_hand_L_o") if k[0] != w.t_chan()]
    auth, got = apply_(ns, reg, item, w)
    saved_value = item[u"record"][u"pose"][u"regions"][u"full_body"][u"orientations"][u"rig_hand_L_o"]
    at_tick = [list(k[1]) for k in w.keys(u"rig_hand_L_o") if k[0] == w.t_chan()]
    check("N.preserved_quaternion_keys_keep_their_exact_signs", got[0] == u"ok" and
          w.keys(u"rig_elbow_L_o") == pole_before and
          [k for k in w.keys(u"rig_hand_L_o") if k[0] != w.t_chan()] == others, got[:2])
    # The written key is the saved rotation in the hemisphere of the destination's value at the tick (the qualified
    # planner rule, prod_pose_hemisphere; unchanged): the destination's keys were negated, so it is written negated.
    expected = list(ns["prod_pose_hemisphere"](list(saved_value), list(reference))[0])
    check("N.written_quaternion_key_is_the_saved_value_in_the_destination_hemisphere", at_tick == [expected] and
          expected == [-c for c in saved_value], (at_tick, saved_value, reference))


FIXTURE_DATA = []
KRYSTAL_RECORD = []


# ---------------------------------------------------------------------------
# O. The Designer's disposition of Fox run 3: the Abort-only history exception (SFM discards a pending Redo entry
#    when a new action starts, even one that is then aborted)
# ---------------------------------------------------------------------------

RUN3_EXTRACT = os.path.join(_THIS_DIR, "fixtures", "f01_body", "fox_run3_abort_extract.json")
RUN3_EXTRACT_SHA256 = "1baff1ec89c895abaa571e25295a608633c4345a91ac1abf31e3751c7f448e45"
RUN3_VERDICT_SHA256 = "561f1b091ca1d6404efe61371509ed6012626bf362ed551523e742d0ffcb9de0"
RUN3_CANDIDATE_COMMIT = "e32b157"     # CPM 2088b4af..., the build run 3 used (qualification differs in one line)
RUN3_CANDIDATE_SHA256 = u"2088b4aff1a6cfe05242bd1e774ac1fd4a565a92e5c124336b1aa855b62b8df7"
UNDO_PROBLEM = u"Undo history changed or unreadable"
REDO_CLEARED_COPY = u"Your character was restored, but SFM cleared your Redo history."
UNVERIFIED_COPY = (u"CPM couldn't confirm that all changes were undone. Check your character before continuing. "
                   u"Restart SFM to use pose tools again.")


def log_detail(line):
    try:
        return json.loads(line[line.index(u"{"):])
    except Exception:
        return None


def section_abort_history(app, ns, reg, fx, item, root):
    chk = ns["prod_pose_abort_undo_check"]
    base = {u"enabled": True, u"can_undo": True, u"can_redo": False, u"undo_desc": u"Change Recording State",
            u"redo_desc": u""}
    pend = dict(base, can_redo=True, redo_desc=u"Redo Apply Pose S1 Fox")

    def var(d, **kw):
        x = dict(d)
        x.update(kw)
        return x

    def bad(got):
        return got == ([UNDO_PROBLEM], False)

    # 1. The predicate.
    check("O.exact_history_without_pending_redo_verifies", chk(dict(base), base) == ([], False))
    check("O.exact_history_with_pending_redo_kept_verifies", chk(dict(pend), pend) == ([], False))
    check("O.pending_redo_cleared_by_sfm_verifies_with_the_flag", chk(dict(base), pend) == ([], True))
    for label, p1, after in (
            (u"redo_appearing_where_none_was_pending", base, pend),
            (u"pending_redo_replaced_by_another_entry", pend, var(pend, redo_desc=u"Redo Something Else")),
            (u"redo_cleared_with_an_owned_entry_left_on_top", pend, var(base, undo_desc=u"Apply Pose S1 Fox")),
            (u"redo_cleared_with_undo_availability_changed", pend, var(base, can_undo=False)),
            (u"redo_cleared_with_undo_disabled", pend, var(base, enabled=False)),
            (u"redo_flag_cleared_but_description_kept", pend, var(pend, can_redo=False)),
            (u"redo_description_cleared_but_flag_kept", pend, var(pend, redo_desc=u"")),
            (u"a_pending_redo_without_description_at_p1", var(pend, redo_desc=u""), base),
            (u"top_entry_changed_without_redo", base, var(base, undo_desc=u"Apply Pose S1 Fox")),
            (u"undo_disabled_without_redo", base, var(base, enabled=False)),
            (u"undo_disabled_at_p1", var(pend, enabled=False), var(base, enabled=False))):
        check("O.%s_is_unverified" % label, bad(chk(after, p1)), chk(after, p1))
    for k in (u"enabled", u"can_undo", u"can_redo", u"undo_desc", u"redo_desc"):
        missing, missing_p1 = dict(base), dict(pend)
        del missing[k], missing_p1[k]
        unreadable = dict(base)
        unreadable[k] = {u"unreadable": u"RuntimeError('test')"}
        check("O.missing_or_unreadable_%s_is_unverified" % k, bad(chk(missing, pend)) and bad(
            chk(unreadable, pend)) and bad(chk(dict(base), missing_p1)))
    check("O.non_boolean_flags_are_unverified", bad(chk(var(base, can_redo=0), pend)) and
          bad(chk(dict(base), var(pend, can_redo=1))))
    check("O.an_extra_member_is_unverified", bad(chk(var(base, extra=1), pend)))
    check("O.non_mapping_states_are_unverified", bad(chk(None, pend)) and bad(chk(dict(base), None)))

    # 2. Replay of run 3's preserved evidence (an extract; the corrected logic, not the corrected CPM natively).
    raw = core.read(RUN3_EXTRACT)
    check("O.run3_extract_matches_its_pin", core.sha(raw) == RUN3_EXTRACT_SHA256, core.sha(raw))
    ev = json.loads(raw.decode("utf-8"))
    check("O.run3_extract_names_the_preserved_evidence", ev[u"sources"][u"verdict_json_sha256"] ==
          RUN3_VERDICT_SHA256 and ev[u"sources"][u"capture_sha256"] == {
              u"UNDO2": u"b65f904649d992e3c57290b54e7e642ef9f3b8464b2447ad9c8a517961551199",
              u"ABORT": u"cc1571a6c6a54eafd792a75ade17588e3c0fe4f440f4b7a0ec3664cf3babecf9"} and
          ev[u"sources"][u"process_b_log_sha256"] ==
          u"275b68fd67860ecdc2d5f1e2a09456adcc9cc2c69f9fe3a5d49048df43f888fa")
    check("O.run3_abort_capture_differs_from_undo2_only_in_redo", ev[u"capture_differences"] == [
        u"/session/undo/can_redo", u"/session/undo/redo_desc", u"/step"] and all(
        ev[u"sets_sha256"][u"ABORT"][r] == ev[u"sets_sha256"][u"UNDO2"][r] for r in (u"source", u"target", u"peer")),
        ev[u"capture_differences"])
    native = [log_detail(l) for l in ev[u"log"] if u"BODY-abort-unverified" in l]
    failure = [log_detail(l) for l in ev[u"log"] if u"BODY-P3-P6-failure" in l]
    check("O.run3_native_abort_failed_only_on_the_undo_history", native == [{u"problems": [UNDO_PROBLEM]}] and
          failure and failure[0][u"finished"] is False and failure[0][u"written"] == 212, (native, failure))
    # `enabled` is not in the observer's capture: true at P1 (P2 passed, and P2 refuses disabled Undo), and taken
    # as true after the Abort, which the observer did not record; a disabled state stays unverified.
    p1 = dict(ev[u"undo"][u"UNDO2"], enabled=True)
    after = dict(ev[u"undo"][u"ABORT"], enabled=True)
    check("O.run3_replay_old_exact_predicate_reproduces_the_native_problem", bool(
        ns["prod_pose_undo_problems"](after) or after != p1))
    check("O.run3_replay_corrected_predicate_verifies_with_redo_cleared", chk(after, p1) == ([], True), chk(after, p1))
    check("O.run3_replay_with_undo_disabled_after_the_abort_stays_unverified", bad(chk(dict(after, enabled=False),
                                                                                     p1)))

    # 3. The body route, live: SFM's Redo discard modelled by FB.discard_redo_on_start.
    QF = ns["PROD_POSE_QUAL_FAULT"]

    def pending_world(discard=True):
        w = world(fx)
        _, got = apply_(ns, reg, item, w)
        assert got[0] == u"ok" and got[1][u"phase"] == u"verification-pending", got
        w.dm.Undo()
        if discard:
            FB.discard_redo_on_start(w)
        del w.dm.calls[:]
        return w

    def aborting(w, after=None, keep_first=False):
        dm = w.dm
        real = dm.AbortUndoableOperation

        def abort():
            if keep_first:
                dm.current["items"] = dm.current["items"][1:]
            real()
            if after is not None:
                after(w)
        dm.AbortUndoableOperation = abort
        return w

    def faulted(w, namespace=ns, registry=reg):
        del namespace["LOG"][:]
        namespace["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
        try:
            return apply_(namespace, registry, item, w)[1]
        finally:
            namespace["PROD_POSE_QUAL_FAULT"][0] = None

    def abort_log(namespace, tag):
        return log_detail(last_log(namespace, tag))

    try:
        w = pending_world()
        before, stack, redo = B.all_keys(w), list(w.dm.stack), list(w.dm.redo_stack)
        got = faulted(w)
        check("O.body_pending_redo_existed_at_p1", len(redo) == 1, redo)
        check("O.body_sfm_redo_discard_abort_is_verified_with_redo_cleared", got[0] == u"ok" and got[1] == {
            u"phase": u"not-applied", u"reason": got[1].get(u"reason"), u"redo_cleared": True} and
            B.all_keys(w) == before and w.dm.stack == stack and w.dm.redo_stack == [] and w.dm.current is None and
            [c[0] for c in w.dm.calls] == ["StartUndo", "AbortUndoableOperation"], (got[:2], w.dm.calls))
        check("O.body_redo_cleared_is_logged_with_the_verified_abort", abort_log(ns, u"BODY-abort-verified") == {
            u"problems": [], u"redo_cleared": True}, last_log(ns, u"BODY-abort"))

        # Teeth: run 3's build reproduces run 3 offline (exact restoration, refused on the history).
        old, old_sha = git_namespace(RUN3_CANDIDATE_COMMIT)
        check("O.teeth_run3_candidate_from_git_is_2088b4af", old_sha == RUN3_CANDIDATE_SHA256, old_sha)
        oreg, _ = B.registries(old)
        w = pending_world()
        before = B.all_keys(w)
        got = faulted(w, old, oreg)
        check("O.teeth_run3_build_reports_recovery_unverified_after_exact_restoration", got[0] ==
              u"ProdRecoveryUnverifiedError" and B.all_keys(w) == before and abort_log(
                  old, u"BODY-abort-unverified") == {u"problems": [UNDO_PROBLEM]}, (got, last_log(old, u"BODY-abort")))

        w = world(fx)
        FB.discard_redo_on_start(w)
        before = B.all_keys(w)
        got = faulted(w)
        check("O.body_exact_history_without_pending_redo_keeps_the_plain_result", got[0] == u"ok" and
              got[1][u"phase"] == u"not-applied" and u"redo_cleared" not in got[1] and B.all_keys(w) == before and
              abort_log(ns, u"BODY-abort-verified") == {u"problems": [], u"redo_cleared": False}, got[:2])
        w = pending_world(discard=False)
        redo = list(w.dm.redo_stack)
        got = faulted(w)
        check("O.body_pending_redo_kept_is_exact_and_keeps_the_plain_result", got[0] == u"ok" and
              got[1][u"phase"] == u"not-applied" and u"redo_cleared" not in got[1] and w.dm.redo_stack == redo,
              got[:2])

        def unverified(label, w, undo_problem):
            got = faulted(w)
            line = abort_log(ns, u"BODY-abort-unverified")
            check("O.body_%s_is_recovery_unverified" % label, got[0] == u"ProdRecoveryUnverifiedError" and
                  line is not None and line[u"problems"] and (UNDO_PROBLEM in line[u"problems"]) == undo_problem,
                  (got, last_log(ns, u"BODY-abort")))
        unverified(u"authored_difference_with_redo_cleared", aborting(pending_world(), keep_first=True), False)
        unverified(u"owned_entry_left_on_top_with_redo_cleared", aborting(
            pending_world(), lambda w: w.dm.stack.append({"label": u"Apply Pose Fox", "items": []})), True)
        unverified(u"undo_disabled_after_the_abort", aborting(
            pending_world(), lambda w: setattr(w, "undo_enabled", False)), True)

        def unreadable(w):
            def raises():
                raise RuntimeError("GetRedoDesc failed (test)")
            w.dm.GetRedoDesc = raises
        unverified(u"unreadable_redo_after_the_abort", aborting(pending_world(), unreadable), True)
        w = world(fx)
        FB.discard_redo_on_start(w)
        unverified(u"redo_appearing_after_the_abort", aborting(
            w, lambda w: w.dm.redo_stack.append({"label": u"Something", "items": []})), True)
        w = pending_world()
        w.abort_raises = True
        got = faulted(w)
        check("O.body_failed_abort_with_pending_redo_is_recovery_unverified", got[0] ==
              u"ProdRecoveryUnverifiedError" and any(u"BODY-abort-failed" in l for l in ns["LOG"]), got)

        # P2 stays exact: Redo cleared between P1 and P2 is stale, before StartUndo.
        w = pending_world()
        writes_before = len(B.scene_writes(w))
        original = ns["prod_body_preflight"]

        def preflight_then_clear(*args):
            pre = original(*args)
            w.dm.redo_stack = []
            return pre
        ns["prod_body_preflight"] = preflight_then_clear
        try:
            _, got = apply_(ns, reg, item, w)
        finally:
            ns["prod_body_preflight"] = original
        refused("O.p2_a_redo_cleared_after_p1_is_stale", got, u"stale")
        check("O.p2_stale_writes_nothing_and_opens_nothing", len(B.scene_writes(w)) == writes_before and not w.dm.calls,
              w.dm.calls)
    finally:
        QF[0] = None

    # 4. Static: P2 calls without the Abort mode; the Abort calls with it; the wording.
    for fn, p2 in ((u"prod_pose_apply", u"prod_pose_same_state(identity, authorization, pre, u\"P2\")"),
                   (u"prod_body_apply", u"prod_body_same_state(identity, authorization, pre)\n"),
                   (u"prod_scope_apply", u"prod_scope_same_state(identity, authorization, pre)\n")):
        text = app.top_text(fn)
        check("O.%s_p2_stays_exact_and_the_abort_uses_the_exception" % fn, text.count(p2) == 1 and
              text.count(u"abort_record=abort_record") == 1 and u"prod_pose_not_applied(exc, redo_cleared)" in text)
    msgs = ns["PROD_POSE_MESSAGES"]
    check("O.wording_is_the_designers", msgs[u"not-applied-redo-cleared"] == REDO_CLEARED_COPY and
          msgs[u"recovery-unverified"] == UNVERIFIED_COPY and msgs[u"recovery-unverified"] % {u"name": u"x"} ==
          UNVERIFIED_COPY and msgs[u"not-applied"] == u"The pose couldn't be applied. Nothing was changed." and
          ns["PROD_POSE_TITLE_NOT_APPLIED"] == u"Pose not applied" and
          ns["PROD_POSE_TITLE_RECOVERY_UNVERIFIED"] == u"Pose operation stopped")
    guard = app.method_text("ProdWindow", "guard")
    check("O.guard_titles_pose_recovery_and_keeps_the_others", u"PROD_POSE_TITLE_RECOVERY_UNVERIFIED" in guard and
          u"if label in PROD_POSE_SCENE_LABELS" in guard and u'"Recovery could not be verified"' in guard)

    # 5. Through the Poses window (qualification build).
    lib = library(root, u"abort")
    mode = ns["PROD_POSE_REGISTRY_MODE"]
    had = "tool_warning_message" in ns
    real_warning = ns.get("tool_warning_message")
    dialogs = []
    ns["tool_warning_message"] = lambda window, title, message: dialogs.append((title, message))
    try:
        ns["PROD_POSE_REGISTRY_MODE"] = QUAL
        use(ns, world(fx, posed=False))
        win = B.window(app, ns, reg, lib)
        win.dialogs = []
        win.prompts = [u"Abort Fox"]
        saved = win.save_pose(None, (u"full_body",))
        witem = ns["prod_pose_reread"](lib, saved, reg)
        dst = use(ns, world(fx))
        win.pending = []
        win.apply_pose(witem)
        check("O.window_apply_commits", len(win.pending) == 1 and [c[0] for c in dst.dm.calls] == [
            "StartUndo", "FinishUndo"], win.statuses[-1:])
        dst.dm.Undo()
        FB.discard_redo_on_start(dst)
        before = B.all_keys(dst)
        QF[0] = u"after-writes"
        win.apply_pose(witem)
        check("O.window_redo_cleared_shows_pose_not_applied_and_does_not_lock",
              win.statuses[-1] == ("status", REDO_CLEARED_COPY, u"error") and
              dialogs == [(u"Pose not applied", REDO_CLEARED_COPY)] and B.all_keys(dst) == before and
              win.pose_recovery_blocked is False and ns["PROD_POSE_RECOVERY_BLOCK"][0] is None,
              (win.statuses[-1:], dialogs))
        dst = use(ns, world(fx))
        QF[0] = u"after-writes"
        win.apply_pose(witem)
        check("O.window_exact_abort_keeps_nothing_was_changed_without_a_dialog",
              win.statuses[-1] == ("status", u"The pose couldn't be applied. Nothing was changed.", u"error") and
              len(dialogs) == 1 and win.pose_recovery_blocked is False, (win.statuses[-1:], dialogs))
        dst = use(ns, world(fx, lambda w: setattr(w, "abort_raises", True)))
        QF[0] = u"after-writes"
        win.apply_pose(witem)
        check("O.window_genuine_unverified_recovery_locks_with_the_new_wording",
              win.pose_recovery_blocked is True and ns["PROD_POSE_RECOVERY_BLOCK"][0] == u"Apply Pose" and
              win.statuses[-1][0] == "error" and win.statuses[-1][3] == UNVERIFIED_COPY, win.statuses[-1:])
        dst = use(ns, world(fx))
        win.apply_pose(witem)
        check("O.window_lockout_holds_for_the_next_apply", win.statuses[-1][2] == u"recovery-blocked" and
              no_mutation(dst), win.statuses[-1:])
    finally:
        QF[0] = None
        ns["PROD_POSE_REGISTRY_MODE"] = mode
        ns["PROD_POSE_RECOVERY_BLOCK"][0] = None
        if had:
            ns["tool_warning_message"] = real_warning
        else:
            ns.pop("tool_warning_message", None)


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
            run("rotation", lambda: section_rotation(ns, reg, fx, lived[1]))
        run("face", lambda: section_face(ns, reg, fx, root))
        run("window", lambda: section_window(app, ns, reg, fx, root))
        if lived:
            run("abort_history", lambda: section_abort_history(app, ns, reg, fx, lived[1], root))
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
