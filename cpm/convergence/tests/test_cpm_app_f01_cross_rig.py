# -*- coding: utf-8 -*-
"""F-01 RC4, same-model cross-rig adaptation: offline qualification of prod_body_rig_adapt and of its use by the
full-body Apply (P1-P7) in the CPM application source.

Authority: Astra's RC4 ruling (Option B, ACCEPT WITH CONDITIONS) and the Designer's "F-01 RC4 - Astra Ruling and
Implementation Authorization" (2026-11-20); assessment cpm/qualification/F01_RC4_CROSS_RIG_ASSESSMENT.md.

Technique: the Stage 2 suite's harness (test_cpm_app_f01_jiggle_leaf, on the Stage 1 and stage E harnesses), with
fixtures/f01_body/tails_shot15.json: the R2 session's original Tails (22 rig controls; bip_spine_3 posed directly).
with_chest() derives the 23-control variant of the RC3 smoke's natively rebuilt Tails by cloning the fixture's own
rig_spine_2 structure: a rig_chest control under rig_spine_2 that point- and orient-constrains bip_spine_3 with zero
offsets, with rig_neck and both collars attached under it (keys re-expressed so the scene's posture is unchanged).
The two native records of the RC3 smoke (fixtures/f01_body/rc3_tails/, read-only copies of the Owner's run records)
are used for the pure adaptation checks, against expectations computed here with the fake scene's own transform math,
never with the adapter's. Nothing here demonstrates native SFM behaviour.

Usage: --phase=run (Python 2.7.5 and Python 3.10).
"""
from __future__ import print_function

import copy
import json
import math
import os
import shutil
import sys
import tempfile
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_f01_pose_core as core  # noqa: E402
import test_cpm_app_f01_body as B  # noqa: E402
import test_cpm_app_f01_structural_rig as R  # noqa: E402
import test_cpm_app_f01_jiggle_leaf as J  # noqa: E402
import fake_sfm_body as FB  # noqa: E402

RECORDS = os.path.join(_THIS_DIR, "fixtures", "f01_body", "rc3_tails")
RECORD_SHA256 = {
    u"RC3 Tails": ("RC3_Tails.json", "a0e0de64ea3a9f08fd92a8248eb4b442d9a5393b697d6ec23f3dfc07586d2bae"),
    u"Tails sit alt": ("Tails_sit_alt.json", "15d22e9372e74717f17b3c2e57c6a6cf9b72d04a468f8b98c8f808dd8cca94a6"),
}
IDENTITY = J.IDENTITY
RESULTS = B.RESULTS
check, outcome, refused = B.check, B.outcome, B.refused
QUAL, PROD = u"qualification", u"production"
LEAVES = J.LEAVES
REATTACHED = [u"rig_collar_L", u"rig_collar_R", u"rig_neck"]
ADAPTED_COPY = u"Pose applied: %s. Adapted to this character's rig."


# --- the 23-control variant ------------------------------------------------------------------------------------------

def with_chest(fx):
    """The fixture with a rig_chest control cloned from rig_spine_2's own structure (control, two channels, a point and
    an orient constraint with zero offsets and their weights), driving bip_spine_3; rig_neck and both collars attached
    under it with their keys re-expressed so every evaluated transform is unchanged."""
    fx = copy.deepcopy(fx)
    probe = FB.World(fx)
    sp2, s3 = probe.handle_dag[u"rig_spine_2"], probe.bone_dag[u"bip_spine_3"]
    cp, cq = FB.to_local((sp2.wp, sp2.wq), (s3.wp, s3.wq))
    cq = FB.qnorm(cq)
    ids = [8000000]

    def new():
        ids[0] += 1
        return ids[0]
    H, chans, ctls = fx[u"rig"][u"handles"], fx[u"channels"], fx[u"controls"]
    chest, chest_t, chest_ctl = new(), new(), new()
    row = copy.deepcopy(H[u"rig_spine_2"])
    row.update({u"handle": chest, u"transform": chest_t, u"local_position": list(cp), u"local_orientation": list(cq),
                u"parent": {u"handle": H[u"rig_spine_2"][u"handle"], u"name": u"rig_spine_2", u"type": u"DmeRigHandle"},
                u"world_position": list(s3.wp), u"world_orientation": list(s3.wq)})
    H[u"rig_chest"] = row
    new_elements = [chest, chest_ctl]
    for attr, suffix, value in ((u"orientation", u"_o", list(cq)), (u"position", u"_p", list(cp))):
        ch = copy.deepcopy(chans[u"rig_spine_2" + suffix])
        ch.update({u"handle": new(), u"log": new(), u"layer": new(), u"value": value, u"keys": [[0, value]],
                   u"from": {u"handle": chest_ctl, u"name": u"rig_chest", u"type": u"DmeTransformControl"},
                   u"to": {u"handle": chest_t, u"name": u"unnamed", u"type": u"DmeTransform"}})
        chans[u"rig_chest" + suffix] = ch
        new_elements.append(ch[u"handle"])
    ctls[u"rig_chest"] = {u"channels": {u"orientationChannel": chans[u"rig_chest_o"][u"handle"],
                                        u"positionChannel": chans[u"rig_chest_p"][u"handle"]},
                          u"handle": chest_ctl, u"type": u"DmeTransformControl",
                          u"values": {u"valueOrientation": list(cq), u"valuePosition": list(cp)}}
    bone = fx[u"bones"][u"bip_spine_3"][u"handle"]
    for kind, suffix in ((u"point", u"_p"), (u"orient", u"_o")):
        template = [op for op in fx[u"operators"] if op[u"name"] == u"%sConstraint_bip_spine_2" % kind][0]
        op = copy.deepcopy(template)
        slave, target, wctl = new(), new(), new()
        op.update({u"handle": new(), u"name": u"%sConstraint_bip_spine_3" % kind})
        op[u"slaves"] = {u"slave": {u"slave": slave, u"target": bone}}
        op[u"targets"][0].update({u"handle": target, u"target": chest})
        fx[u"operators"].append(op)
        wname = u"%sConstraint_bip_spine_3 - rig_chest" % kind
        wch = copy.deepcopy(chans[u"%sConstraint_bip_spine_2 - rig_spine_2 targetWeight" % kind])
        wch.update({u"handle": new(), u"log": new(), u"layer": new(),
                    u"from": {u"handle": wctl, u"name": wname + u" weight", u"type": u"DmElement"},
                    u"to": {u"handle": target, u"name": u"rig_chest", u"type": u"DmeConstraintTarget"}})
        chans[wname + u" targetWeight"] = wch
        ctls[wname + u" weight"] = {u"channels": {u"channel": wch[u"handle"]}, u"handle": wctl, u"type": u"DmElement",
                                    u"values": {u"value": 1.0}}
        chans[u"bip_spine_3" + suffix][u"to"] = {u"handle": slave, u"name": u"unnamed",
                                                 u"type": u"DmeConstraintSlave"}
        new_elements += [op[u"handle"], wctl, wch[u"handle"]]
    inv = FB.qconj(cq)
    for n in REATTACHED:
        H[n][u"parent"] = {u"handle": chest, u"name": u"rig_chest", u"type": u"DmeRigHandle"}
        H[n][u"local_position"] = FB.qrot(inv, FB.sub(H[n][u"local_position"], cp))
        H[n][u"local_orientation"] = FB.qnorm(FB.qmul(inv, H[n][u"local_orientation"]))
        for k in chans[n + u"_p"][u"keys"]:
            k[1] = FB.qrot(inv, FB.sub(k[1], cp))
        for k in chans[n + u"_o"][u"keys"]:
            k[1] = FB.qnorm(FB.qmul(inv, k[1]))
    fx[u"rig"][u"elements"] = list(fx[u"rig"][u"elements"]) + new_elements
    for g in fx[u"groups"]:
        if ctls[u"rig_spine_2"][u"handle"] in g[u"controls"]:
            g[u"controls"] = list(g[u"controls"]) + [chest_ctl]
    return fx


def keep_chest_position(w):
    """A distinctly posed source whose chest control turns but is not moved (moving it is section G's unreachable
    case)."""
    J.pose_differently(w)
    layer = w.channels[u"rig_chest_p"].attrs["log"].layer
    for k in layer.keys:
        v = FB.plain(k[1])
        k[1] = FB.native([v[0] - 1.5, v[1] + 1.0, v[2]], "vec")
    turn(w, u"rig_chest_o", [0.0, 0.0, 1.0], 12.0)


def turn(w, name, axis, degrees):
    layer = w.channels[name].attrs["log"].layer
    for k in layer.keys:
        k[1] = FB.native(B.rotate(FB.plain(k[1]), axis, degrees), "quat")
    w.evaluate()


def pose_spine_directly(w):
    """A distinctly posed 22-control source: the rig as for the other suites, and the directly posed upper spine."""
    J.pose_differently(w)
    turn(w, u"bip_spine_3_o", [0.0, 1.0, 0.0], 15.0)


def place_elsewhere(w):
    """A destination in its own placement and facing (moved and turned), otherwise as authored."""
    for name, delta in ((u"rig_root_p", [-140.0, 35.0, 0.0]), (u"rig_root_o", None)):
        layer = w.channels[name].attrs["log"].layer
        for k in layer.keys:
            v = FB.plain(k[1])
            k[1] = FB.native(B.rotate(v, [0.0, 0.0, 1.0], -70.0) if delta is None else
                             [v[0] + delta[0], v[1] + delta[1], v[2]], layer.value_kind)
    w.evaluate()


def world(fx, prepare=None):
    return J.world(fx, prepare=prepare, posed=False)


def use(ns, w):
    return J.use(ns, w)


def adapted_log(ns):
    line = R.last_log(ns, u"BODY-RIG-adapted")
    return R.log_detail(line) if line else None


def refusal(ns):
    line = R.last_log(ns, u"BODY-refused")
    return R.log_detail(line) or {}


def changed_channels(before, after):
    return sorted(n for n in after if after[n] != before[n])


def keys_away_from(keys, t):
    return dict((n, [k for k in v if k[0] != t]) for n, v in keys.items())


# --- independent expectations: the fake scene's own transform math ------------------------------------------------

def compose(a, b):
    return FB.compose((list(a[0]), list(a[1])), (list(b[0]), list(b[1])))


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def angle(a, b):
    d = min(1.0, abs(sum(x * y for x, y in zip(FB.qnorm(a), FB.qnorm(b)))))
    return math.degrees(2.0 * math.acos(d))


def handle_worlds(desc, values):
    """Placement-relative worlds of a description's controls from written values (placement: identity)."""
    by = dict(((c[u"owner"], c[u"attribute"]), n) for n, c in desc[u"channels"].items()
              if c[u"role"] == u"handle-written")
    H = desc[u"handles"]
    out = {}

    def w(n):
        if H[n][u"class"] == u"placement":
            return ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])
        if n not in out:
            out[n] = compose(w(H[n][u"parent"]), (values[by[(u"handle:" + n, u"position")]],
                                                  values[by[(u"handle:" + n, u"orientation")]]))
        return out[n]
    for n in H:                                       # controls with both values written (pole orientations aren't)
        chain, ok = n, True
        while ok and H[chain][u"class"] != u"placement":
            ok = all((u"handle:" + chain, a) in by for a in (u"position", u"orientation"))
            chain = H[chain][u"parent"]
        if ok and H[n][u"class"] == u"core":
            w(n)
    return out


# --- the native records ---------------------------------------------------------------------------------------------

def records():
    out = {}
    for name, (path, sha) in sorted(RECORD_SHA256.items()):
        raw = core.read(os.path.join(RECORDS, path))
        check("fixture.%s.matches_its_pin" % path, core.sha(raw) == sha, core.sha(raw))
        out[name] = json.loads(raw.decode("utf-8"))
    return out


def live_of(record, move=None):
    """A destination's P1 state as the adapter reads it, from a native record's own description and values."""
    region = record[u"pose"][u"regions"][u"full_body"]
    desc = copy.deepcopy(region[u"descriptor"])
    written = sorted(n for n, c in desc[u"channels"].items() if c[u"role"] in (u"handle-written", u"fk-written"))
    owners = dict((n, [desc[u"channels"][n][u"owner"], desc[u"channels"][n][u"attribute"]]) for n in written)
    values = dict(region[u"positions"])
    values.update(region[u"orientations"])
    D = {u"channels": dict((n, {u"value": list(v)}) for n, v in values.items())}
    if move is not None:
        move(desc, D)
    return {u"descriptor": desc, u"D": D, u"C": {u"written": written, u"owners": owners}}


def aligned_to(saved, then=None):
    """The destination's common constraints carry the saved record's offsets (the two native rigs were built
    separately and differ in offsets beyond the established equivalence; see N.native_pair_refuses_on_offsets). This
    isolates the structural difference; `then` adds one more change."""
    rows = dict((json.dumps([c[u"type"], c[u"slaves"], c[u"targets"], c[u"pole"]], sort_keys=True), c)
                for c in saved[u"pose"][u"regions"][u"full_body"][u"descriptor"][u"constraints"])

    def move(desc, D):
        for c in desc[u"constraints"]:
            s = rows.get(json.dumps([c[u"type"], c[u"slaves"], c[u"targets"], c[u"pole"]], sort_keys=True))
            if s is not None:
                c[u"solver"], c[u"offsets"] = copy.deepcopy(s[u"solver"]), copy.deepcopy(s[u"offsets"])
        if then is not None:
            then(desc, D)
    return move


def profile_of(ns):
    return {u"_structural": True, u"_id": u"structural_rig_v1", u"fk_position_limit": 0.001,
            u"tolerances": dict(ns["PROD_SCOPE_TOLERANCES"])}


def region_of(record):
    return copy.deepcopy(record[u"pose"][u"regions"][u"full_body"])


def adapt(ns, saved, live):
    return outcome(lambda: ns["prod_body_rig_adapt"](region_of(saved), live, profile_of(ns)))


# ---------------------------------------------------------------------------
# M. The refusal wording: a missing control is a rig difference, not a proportions difference
# ---------------------------------------------------------------------------

def section_wording(ns, recs):
    a = recs[u"RC3 Tails"][u"pose"][u"regions"][u"full_body"][u"descriptor"]
    b = recs[u"Tails sit alt"][u"pose"][u"regions"][u"full_body"][u"descriptor"]
    del ns["LOG"][:]
    got = outcome(lambda: ns["prod_body_compare_descriptor"](a, b))
    refused("M.rc3_op17_missing_chest_control_is_a_rig_difference", got, u"rig-differs")
    check("M.rc3_op17_detail_names_the_control_not_proportions", u"rig_chest" in refusal(ns).get(u"detail", u"") and
          u"proportions" not in got[2] if len(got) > 2 else False, refusal(ns))
    check("M.rig_differs_copy_is_not_the_proportions_copy", ns["PROD_BODY_MESSAGES"][u"rig-differs"] !=
          ns["PROD_BODY_MESSAGES"][u"proportions"])
    c = copy.deepcopy(b)
    c[u"scale"][u"handles"][u"rig_hand_L"] = {u"present": True, u"value": 1.2}
    refused("M.a_common_control_scale_difference_stays_proportions", outcome(
        lambda: ns["prod_body_compare_descriptor"](b, c)), u"proportions")
    c = copy.deepcopy(b)
    c[u"scale"][u"bones"][u"bip_head"] = {u"present": True, u"value": 1.1}
    refused("M.a_bone_scale_difference_stays_proportions", outcome(lambda: ns["prod_body_compare_descriptor"](b, c)),
            u"proportions")
    c = copy.deepcopy(b)
    k = sorted(c[u"structural_positions"])[0]
    c[u"structural_positions"][k] = [v + 0.25 for v in c[u"structural_positions"][k]]
    refused("M.an_ik_bone_length_difference_stays_proportions", outcome(
        lambda: ns["prod_body_compare_descriptor"](b, c)), u"proportions")
    check("M.identical_descriptions_compare_equal", outcome(lambda: ns["prod_body_compare_descriptor"](b, b))[0] ==
          u"ok")


# ---------------------------------------------------------------------------
# N. The adaptation itself, on the two native records, with independent expectations
# ---------------------------------------------------------------------------

def section_native(ns, recs):
    rc3, sit = recs[u"RC3 Tails"], recs[u"Tails sit alt"]
    # The RC3 smoke's op 17 pair as recorded: the chest difference is adaptable, but the separately built arm
    # controls differ in offsets beyond the established equivalence (0.0005 degrees; exact positions), which is never
    # widened here: it refuses, and says so.
    copy_rig = ns["PROD_BODY_ADAPT_MESSAGES"][u"rig"]
    offsets = copy_rig % u"its arm or leg controls were built with slightly different offsets"
    for label, s, d in ((u"chest_to_direct", rc3, sit), (u"direct_to_chest", sit, rc3)):
        got = adapt(ns, s, live_of(d))
        check("N.native_pair_%s_refuses_on_offsets_not_the_chest" % label, got[0] != u"ok" and got[1] ==
              u"rig-differs" and got[2] == offsets, got)
    # 23 -> 22 with the common offsets aligned: the structural adaptation itself.
    live = live_of(sit, aligned_to(rc3))
    got = adapt(ns, rc3, live)
    check("N.chest_rig_pose_adapts_to_the_rig_without_chest", got[0] == u"ok", got)
    if got[0] != u"ok":
        return
    out, report = got[1][u"region"], got[1][u"report"]
    check("N.report_names_the_conversion_and_the_reattached_controls", report[u"converted"] == [
        {u"bone": u"bip_spine_3", u"destination": u"fk"}] and report[u"saved_only_controls"] == [u"rig_chest"] and
        report[u"destination_only_controls"] == [] and report[u"reattached_controls"] == REATTACHED and
        report[u"derived_channels"] == sorted([u"bip_spine_3_o", u"bip_spine_3_p"] + [
            n + s for n in REATTACHED for s in (u"_o", u"_p")]), report)
    saved = dict(rc3[u"pose"][u"regions"][u"full_body"][u"positions"])
    saved.update(rc3[u"pose"][u"regions"][u"full_body"][u"orientations"])
    values = dict(out[u"positions"])
    values.update(out[u"orientations"])
    check("N.plan_covers_exactly_the_destination_written_channels", sorted(values) == live[u"C"][u"written"])
    copied = [n for n in values if n not in report[u"derived_channels"]]
    check("N.unchanged_relationships_carry_the_saved_values_exactly", len(copied) == len(values) - 8 and all(
        values[n] == saved[n] for n in copied))
    check("N.saved_skeletal_reference_and_record_are_untouched", out[u"oracle"] == rc3[u"pose"][u"regions"][
        u"full_body"][u"oracle"] and out[u"descriptor"] == live[u"descriptor"] and region_of(rc3) ==
        rc3[u"pose"][u"regions"][u"full_body"])
    check("N.plan_values_are_native_float32", all(v == [ns["prod_pose_f32"](c) for c in v] for v in values.values()))
    # Independent expectation: the destination's controls, composed with the fake scene's math from the planned
    # values, put the neck, collars and spine where the saved skeletal reference has them.
    oracle = rc3[u"pose"][u"regions"][u"full_body"][u"oracle"][u"bones"]
    W = handle_worlds(live[u"descriptor"], values)
    worst = []
    for handle, bone in ((u"rig_neck", u"bip_neck"), (u"rig_collar_L", u"bip_collar_L"),
                         (u"rig_collar_R", u"bip_collar_R"), (u"rig_head", u"bip_head"),
                         (u"rig_spine_2", u"bip_spine_2"), (u"rig_pelvis", u"bip_pelvis")):
        worst.append((handle, distance(W[handle][0], oracle[bone][u"position"]),
                      angle(W[handle][1], oracle[bone][u"orientation"])))
    check("N.reattached_controls_reproduce_the_saved_bone_postures", all(d < 1e-3 and a < 0.01 for _, d, a in worst),
          worst)
    spine3 = compose(W[u"rig_spine_2"], (values[u"bip_spine_3_p"], values[u"bip_spine_3_o"]))
    o3 = oracle[u"bip_spine_3"]
    check("N.directly_posed_spine_reproduces_the_chest_driven_posture", distance(spine3[0], o3[u"position"]) < 1e-3
          and angle(spine3[1], o3[u"orientation"]) < 0.01, (distance(spine3[0], o3[u"position"]),
                                                            angle(spine3[1], o3[u"orientation"])))
    check("N.spine_translation_is_within_the_a1_allowance", distance(values[u"bip_spine_3_p"], live[u"D"][
        u"channels"][u"bip_spine_3_p"][u"value"]) <= 0.001)
    # 22 -> 23: the reverse.
    live = live_of(rc3, aligned_to(sit))
    got = adapt(ns, sit, live)
    check("N.direct_spine_pose_adapts_to_the_chest_rig", got[0] == u"ok", got)
    if got[0] == u"ok":
        out, report = got[1][u"region"], got[1][u"report"]
        values = dict(out[u"positions"])
        values.update(out[u"orientations"])
        check("N.reverse_report", report[u"converted"] == [{u"bone": u"bip_spine_3", u"destination": u"constrained"}]
              and report[u"destination_only_controls"] == [u"rig_chest"] and report[u"reattached_controls"] ==
              REATTACHED and u"bip_spine_3_o" not in values, report)
        oracle = sit[u"pose"][u"regions"][u"full_body"][u"oracle"][u"bones"]
        W = handle_worlds(live[u"descriptor"], values)
        worst = [(h, distance(W[h][0], oracle[b][u"position"]), angle(W[h][1], oracle[b][u"orientation"])) for h, b in (
            (u"rig_chest", u"bip_spine_3"), (u"rig_neck", u"bip_neck"), (u"rig_collar_L", u"bip_collar_L"),
            (u"rig_collar_R", u"bip_collar_R"), (u"rig_head", u"bip_head"))]
        check("N.solved_chest_and_reattached_controls_reproduce_the_saved_postures", all(
            d < 1e-3 and a < 0.01 for _, d, a in worst), worst)
    # Deterministic, and independent of constraint order.
    def reorder(desc, D):
        desc[u"constraints"].reverse()
    first, again = adapt(ns, rc3, live_of(sit, aligned_to(rc3))), adapt(ns, rc3, live_of(sit, aligned_to(rc3)))
    other = adapt(ns, rc3, live_of(sit, aligned_to(rc3, reorder)))
    pick = lambda g: (g[1][u"region"][u"positions"], g[1][u"region"][u"orientations"], g[1][u"report"])  # noqa: E731
    check("N.adaptation_is_deterministic_and_order_independent", first[0] == other[0] == u"ok" and first == again and
          pick(first) == pick(other), (first[:1], other[:1]))


def section_native_refusals(ns, recs):
    rc3, sit = recs[u"RC3 Tails"], recs[u"Tails sit alt"]
    copy_rig = ns["PROD_BODY_ADAPT_MESSAGES"][u"rig"]

    def chest(desc, kind):
        return [c for c in desc[u"constraints"] if c[u"targets"] == [u"handle:rig_chest"] and c[u"type"] == kind][0]
    point, orient = u"DmeRigPointConstraintOperator", u"DmeRigOrientConstraintOperator"

    def rotated_offset(desc, D):
        chest(desc, orient)[u"offsets"][u"oOffset"] = {u"present": True, u"value": B.rotate(
            [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 1.0], 5.0)}

    def moved_offset(desc, D):
        chest(desc, point)[u"offsets"][u"vecOffset"] = {u"present": True, u"value": [0.5, 0.0, 0.0]}

    def drives_two_bones(desc, D):
        extra = copy.deepcopy(chest(desc, point))
        extra[u"slaves"] = {u"slave": u"bone:bip_spine_2"}
        desc[u"constraints"].append(extra)

    def is_a_pole(desc, D):
        ik = [c for c in desc[u"constraints"] if c[u"type"] == u"DmeRigIKConstraintOperator"][0]
        ik[u"pole"] = u"handle:rig_chest"

    def consumer(desc, D):
        desc[u"constraints"].append({u"type": point, u"slaves": {u"slave": u"handle:rig_footHelper_L"},
                                     u"targets": [u"bone:bip_spine_3"], u"pole": None,
                                     u"solver": {u"mode": {u"present": True, u"value": 0}},
                                     u"offsets": {u"oOffset": {u"present": True, u"value": [0.0, 0.0, 0.0, 1.0]},
                                                  u"vecOffset": {u"present": True, u"value": [0.0, 0.0, 0.0]}}})

    def neck_elsewhere(desc, D):
        desc[u"handles"][u"rig_neck"][u"parent"] = u"rig_spine_1"

    def ik_pole(desc, D):
        ik = [c for c in desc[u"constraints"] if c[u"type"] == u"DmeRigIKConstraintOperator"][0]
        ik[u"pole"] = u"handle:rig_spine_1"

    def renamed_bone(desc, D):
        desc[u"bones"][-1][u"name"] = u"renamed"

    def other_class(desc, D):
        [b for b in desc[u"bones"] if b[u"name"] == u"bip_neck"][0][u"class"] = u"fk"

    def missing_weight(desc, D):
        name = [n for n, c in desc[u"channels"].items() if c[u"role"] == u"weight" and u"rig_chest" in n][0]
        del desc[u"channels"][name]

    def chest_scaled(desc, D):
        desc[u"scale"][u"handles"][u"rig_chest"] = {u"present": True, u"value": 1.0}

    def chest_solver(desc, D):
        chest(desc, point)[u"solver"] = {u"mode": {u"present": True, u"value": 1}}
    # Destination with the chest (22 -> 23), each changed in one relationship.
    for label, move, what in (
            (u"chest_orientation_offset", rotated_offset, u"the rig_chest control is offset from its bone"),
            (u"chest_position_offset", moved_offset, u"the rig_chest control is offset from its bone"),
            (u"chest_driving_two_bones", drives_two_bones, u"the rig_chest control works differently"),
            (u"chest_used_as_an_ik_pole", is_a_pole, u"the rig_chest control drives other parts of the rig"),
            (u"chest_with_a_scale", chest_scaled, u"the rig_chest control works differently"),
            (u"chest_solver_setting", chest_solver, u"the rig_chest control works differently"),
            (u"chest_weight_channel_missing", missing_weight, u"its controls are different")):
        del ns["LOG"][:]
        got = adapt(ns, sit, live_of(rc3, aligned_to(sit, move)))
        check("N.refuses_%s" % label, got[0] != u"ok" and got[1] == u"rig-differs" and got[2] == copy_rig % what,
              got)
    for label, move, what in (
            (u"an_unexpected_consumer_of_the_converted_bone", consumer, u"its other controls or limb IK are different"),
            (u"a_control_attached_elsewhere", neck_elsewhere, u"the rig_neck control is attached differently"),
            (u"a_different_ik_pole", ik_pole, u"its other controls or limb IK are different"),
            (u"a_different_skeleton", renamed_bone, u"its skeleton is different"),
            (u"another_bone_controlled_differently", other_class, u"the bip_neck bone is controlled differently")):
        got = adapt(ns, rc3, live_of(sit, aligned_to(rc3, move)))
        check("N.refuses_%s" % label, got[0] != u"ok" and got[1] == u"rig-differs" and got[2] == copy_rig % what,
              got)

    def far_spine(desc, D):
        v = D[u"channels"][u"bip_spine_3_p"][u"value"]
        D[u"channels"][u"bip_spine_3_p"][u"value"] = [v[0], v[1] + 0.25, v[2]]
    got = adapt(ns, rc3, live_of(sit, aligned_to(rc3, far_spine)))
    check("N.refuses_an_unreachable_spine_translation", got[0] != u"ok" and got[1] == u"fk-position" and got[2] ==
          ns["PROD_BODY_ADAPT_MESSAGES"][u"unreachable"] % u"bip_spine_3", got)

    def bigger(desc, D):
        b = desc[u"scale"][u"bones"]
        b[u"bip_head"] = {u"present": True, u"value": 1.25}
    refused("N.different_bone_scale_is_proportions", adapt(ns, rc3, live_of(sit, aligned_to(rc3, bigger))),
            u"proportions")

    def other_model(desc, D):
        desc[u"model_ref"] = u"models/other.mdl"
    got = adapt(ns, rc3, live_of(sit, aligned_to(rc3, other_model)))
    check("N.refuses_another_model", got[1] == u"rig-differs" and got[2] == copy_rig % u"it is a different model", got)


# ---------------------------------------------------------------------------
# A. The variant fixture is the native relationship
# ---------------------------------------------------------------------------

def section_variant(ns, fx, chest_fx, recs):
    plain = J.discovered(ns, world(fx))
    variant = J.discovered(ns, world(chest_fx))
    P0, P1 = ns["prod_body_rig_draft"](plain), ns["prod_body_rig_draft"](variant)
    check("A.variant_drafts_as_the_native_23_control_rig", len(P1[u"handles"]) == 23 and len(P1[u"constraints"]) == 36
          and P1[u"handles"][u"rig_chest"] == u"rig_spine_2" and all(P1[u"handles"][n] == u"rig_chest"
                                                                       for n in REATTACHED), sorted(P1[u"handles"]))
    check("A.original_fixture_is_the_22_control_rig", len(P0[u"handles"]) == 22 and len(P0[u"constraints"]) == 34)
    C1 = ns["prod_body_classify"](variant, P1)
    roles = B.counts(C1[u"channels"].values())
    native = B.counts(c[u"role"] for c in recs[u"RC3 Tails"][u"pose"][u"regions"][u"full_body"][u"descriptor"][
        u"channels"].values())
    check("A.variant_roles_match_the_native_rc3_tails_record", dict((r, roles.get(r)) for r in native) == native,
          (roles, native))
    d1 = ns["prod_body_descriptor"](variant, C1, P1)
    nat = recs[u"RC3 Tails"][u"pose"][u"regions"][u"full_body"][u"descriptor"]
    check("A.variant_relationships_match_the_native_record", d1[u"handles"] == nat[u"handles"] and
          sorted(json.dumps([c[u"type"], c[u"slaves"], c[u"targets"], c[u"pole"]]) for c in d1[u"constraints"]) ==
          sorted(json.dumps([c[u"type"], c[u"slaves"], c[u"targets"], c[u"pole"]]) for c in nat[u"constraints"]) and
          dict((b[u"name"], b[u"class"]) for b in d1[u"bones"]) == dict((b[u"name"], b[u"class"])
                                                                         for b in nat[u"bones"]))
    a, b = J.posture(world(fx)), J.posture(world(chest_fx))
    check("A.variant_keeps_the_scene_posture", B.max_difference(a, b)[0] < 1e-3 and B.max_difference(a, b)[1] < 0.01,
          B.max_difference(a, b))


# ---------------------------------------------------------------------------
# C. Live: both directions through P1-P7, placement and facing, keys, Undo, Redo, no-op
# ---------------------------------------------------------------------------

def save(ns, reg, root, name, w, lib_name):
    use(ns, w)
    lib = J.library(root, lib_name)
    return J.save(ns, reg, lib, name)


def lifecycle(ns, reg, label, item, src_posture, dst, mode=QUAL):
    before = B.all_keys(dst)
    model = (list(dst.gm.wp), list(dst.gm.wq))
    root = dst.handle_dag[u"rig_root"]
    placement = (list(root.wp), list(root.wq))
    del ns["LOG"][:]
    auth, got = J.apply_(ns, reg, item, dst, mode=mode)
    report = adapted_log(ns)
    check("C.%s_adapts_and_commits_in_one_owned_undo" % label, got[0] == u"ok" and got[1][u"phase"] ==
          u"verification-pending" and [c[0] for c in dst.dm.calls] == ["StartUndo", "FinishUndo"] and
          len(dst.dm.stack) == 1 and report is not None, (got[:2], report))
    if got[0] != u"ok" or not got[1].get(u"pending"):
        return None
    pending = got[1][u"pending"]
    check("C.%s_pending_is_marked_adapted" % label, pending.get(u"adapted") is True)
    verdict = J.verify(ns, auth, got)
    check("C.%s_p7_verifies_against_the_saved_reference" % label, verdict is not None and verdict.get(u"phase") ==
          u"committed-verified", verdict)
    dp, dq = B.max_difference(J.posture(dst), src_posture)
    check("C.%s_destination_takes_the_saved_posture" % label, dp < 1e-3 and dq < 0.01, (dp, dq))
    check("C.%s_keeps_its_own_placement_and_facing" % label, (list(root.wp), list(root.wq)) == placement and
          (list(dst.gm.wp), list(dst.gm.wq)) == model)
    after = B.all_keys(dst)
    C = pending[u"classes"]
    planned = sorted(C[u"written"])
    changed = changed_channels(before, after)
    check("C.%s_only_planned_channels_change" % label, set(changed) <= set(planned) and changed, changed[:8])
    t = dst.t_chan()
    check("C.%s_neighbouring_keys_are_untouched" % label, keys_away_from(before, t) == keys_away_from(after, t))
    kept = [n for n, r in C[u"channels"].items() if r not in (u"handle-written", u"fk-written")]
    check("C.%s_placement_poles_ik_lengths_weights_leaves_and_flexes_kept" % label, all(
        after[n] == before[n] for n in kept), [n for n in kept if after[n] != before[n]][:8])
    dst.dm.Undo()
    check("C.%s_undo_restores_the_baseline" % label, B.all_keys(dst) == before)
    dst.dm.Redo()
    check("C.%s_redo_reapplies" % label, B.all_keys(dst) == after)
    calls = len(dst.calls)
    _, again = J.apply_(ns, reg, item, dst, mode=mode)
    check("C.%s_repeat_apply_is_a_noop" % label, again[0] == u"ok" and again[1] == {u"phase": u"no-op"} and
          len(dst.calls) == calls, again[:2])
    dst.dm.Undo()
    check("C.%s_final_undo_restores_the_baseline" % label, B.all_keys(dst) == before)
    return pending


def section_live(ns, reg, fx, chest_fx, root):
    src = world(chest_fx, keep_chest_position)
    pose, saved, chest_item = save(ns, reg, root, u"Chest Tails", src, u"chest")
    check("C.chest_rig_saves_a_structural_record", pose[u"adapter"][u"revision"] == 2 and u"rig_chest_o" in
          pose[u"regions"][u"full_body"][u"orientations"])
    chest_posture = J.posture(src)
    lifecycle(ns, reg, u"chest_to_direct", chest_item, chest_posture, world(fx, place_elsewhere))
    src = world(fx, pose_spine_directly)
    pose, saved, direct_item = save(ns, reg, root, u"Direct Tails", src, u"direct")
    direct_posture = J.posture(src)
    lifecycle(ns, reg, u"direct_to_chest", direct_item, direct_posture, world(chest_fx, place_elsewhere))
    lifecycle(ns, reg, u"production_chest_to_direct", chest_item, chest_posture, world(fx, place_elsewhere), PROD)

    def reorder(w):
        w.ops.reverse()
        w.animset.attrs["operators"].items.reverse()
        w.chan_clip.attrs["channels"].items.reverse()
    lifecycle(ns, reg, u"reordered_constraints", direct_item, direct_posture, world(chest_fx, reorder))
    # The same rig still uses the unchanged route: no adaptation.
    del ns["LOG"][:]
    auth, got = J.apply_(ns, reg, direct_item, world(fx, place_elsewhere))
    check("C.same_rig_apply_is_not_adapted", got[0] == u"ok" and adapted_log(ns) is None and not got[1][
        u"pending"].get(u"adapted") and J.verify(ns, auth, got).get(u"phase") == u"committed-verified", got[:2])
    return chest_item, direct_item, chest_posture, direct_posture


# ---------------------------------------------------------------------------
# G. Refusals in the scene: nothing written
# ---------------------------------------------------------------------------

def section_live_refusals(ns, reg, fx, chest_fx, root, items):
    chest_item, direct_item = items[0], items[1]

    def moved_chest(w):
        keep_chest_position(w)
        layer = w.channels[u"rig_chest_p"].attrs["log"].layer
        for k in layer.keys:
            v = FB.plain(k[1])
            k[1] = FB.native([v[0], v[1] + 0.5, v[2]], "vec")
        w.evaluate()
    pose, saved, moved_item = save(ns, reg, root, u"Moved Chest", world(chest_fx, moved_chest), u"moved")
    w = world(fx)
    _, got = J.apply_(ns, reg, moved_item, w)
    check("G.unreachable_chest_translation_refuses_before_any_write", got[0] != u"ok" and got[1] == u"fk-position" and
          got[2] == ns["PROD_BODY_ADAPT_MESSAGES"][u"unreachable"] % u"bip_spine_3" and J.no_mutation(w), got)

    def chest_target(w, kind):
        return [el for op, el in w.ops if op["name"] == u"%sConstraint_bip_spine_3" % kind][0].attrs[
            "targets"].items[0]

    def offset(w):
        chest_target(w, u"orient").set("oOffset", FB.Quaternion(*B.rotate([0.0, 0.0, 0.0, 1.0], [0, 0, 1], 4.0)))
        w.evaluate()
    w = world(chest_fx, offset)
    _, got = J.apply_(ns, reg, direct_item, w)
    check("G.offset_chest_control_refuses_with_the_relationship", got[0] != u"ok" and got[1] == u"rig-differs" and
          got[2] == ns["PROD_BODY_ADAPT_MESSAGES"][u"rig"] % u"the rig_chest control is offset from its bone" and
          J.no_mutation(w), got)
    w = world(fx, lambda w: B.external_constraint(w, u"bip_spine_3"))
    _, got = J.apply_(ns, reg, chest_item, w)
    refused("G.an_external_driver_of_the_converted_bone_refuses", got, u"shared-authority")
    check("G.external_driver_changes_nothing", J.no_mutation(w))


# ---------------------------------------------------------------------------
# T. P2, Abort and P7 around an adapted plan
# ---------------------------------------------------------------------------

def section_transaction(ns, reg, fx, chest_fx, items):
    chest_item, direct_item = items[0], items[1]
    original = ns["prod_body_preflight"]

    def between(change, item, w):
        def preflight_then_change(*args):
            pre = original(*args)
            change(w)
            return pre
        ns["prod_body_preflight"] = preflight_then_change
        try:
            return J.apply_(ns, reg, item, w)
        finally:
            ns["prod_body_preflight"] = original

    def chest_offset(w):
        [el for op, el in w.ops if op["name"] == u"pointConstraint_bip_spine_3"][0].attrs["targets"].items[0].set(
            "vecOffset", FB.Vector(0.0, 0.25, 0.0))
        w.evaluate()
    w = world(chest_fx)
    _, got = between(chest_offset, direct_item, w)
    refused("T.p2_changed_chest_relationship_is_stale", got, u"stale")
    check("T.p2_changed_relationship_writes_nothing", not B.scene_writes(w) and not [
        c for c in w.dm.calls if c[0] == "StartUndo"])
    w = world(fx)
    _, got = between(lambda w: turn(w, u"rig_spine_2_o", [1.0, 0.0, 0.0], 3.0), chest_item, w)
    refused("T.p2_changed_parent_control_is_stale", got, u"stale")
    # P2 re-derives the adaptation itself: a different derivation at P2 is stale.
    real = ns["prod_body_rig_adapt"]
    calls = []

    def drifting(region, live, profile):
        out = real(region, live, profile)
        calls.append(1)
        if len(calls) > 1:
            out = copy.deepcopy(out)
            out[u"region"][u"orientations"][u"rig_neck_o"] = [0.0, 0.0, 0.0, 1.0]
        return out
    ns["prod_body_rig_adapt"] = drifting
    try:
        w = world(fx)
        _, got = J.apply_(ns, reg, chest_item, w)
    finally:
        ns["prod_body_rig_adapt"] = real
    refused("T.p2_rederives_the_adaptation", got, u"stale")
    check("T.p2_rederivation_writes_nothing", len(calls) >= 2 and not B.scene_writes(w))
    # A failure after adapted writes: verified Abort restores the destination's own original state.
    for label, item, fx_, fail in ((u"chest_to_direct", chest_item, fx, u"rig_spine_1_o"),
                                   (u"direct_to_chest", direct_item, chest_fx, u"rig_spine_1_o")):
        w = world(fx_)
        before = B.all_keys(w)
        w.fail_on_write = fail
        del ns["LOG"][:]
        auth, got = J.apply_(ns, reg, item, w)
        writes = [w.layer_channel.get(c[1]) for c in B.scene_writes(w)]
        derived = (adapted_log(ns) or {}).get(u"derived_channels") or []
        check("T.%s_failure_after_adapted_writes" % label, set(derived) & set(writes), (derived, writes[-6:]))
        check("T.%s_abort_restores_the_original_state" % label, got[0] == u"ok" and got[1][u"phase"] ==
              u"not-applied" and [c[0] for c in w.dm.calls] == ["StartUndo", "AbortUndoableOperation"] and
              B.all_keys(w) == before and not w.dm.stack and any(u"BODY-abort-verified" in l for l in ns["LOG"]),
              (got[:2], w.dm.calls))
    # P7: an independent observation against the saved reference.
    w = world(chest_fx)
    auth, got = J.apply_(ns, reg, direct_item, w)
    chest_offset(w)
    verdict = J.verify(ns, auth, got)
    check("T.p7_after_a_changed_chest_relationship_is_unverified", verdict is not None and verdict.get(u"phase") ==
          u"committed-unverified", verdict)
    w = world(fx)
    auth, got = J.apply_(ns, reg, chest_item, w)
    turn(w, u"bip_spine_3_o", [1.0, 0.0, 0.0], 2.0)          # the converted bone moved away after the commit
    verdict = J.verify(ns, auth, got)
    check("T.p7_detects_a_wrong_converted_bone", verdict is not None and verdict.get(u"phase") ==
          u"committed-unverified", verdict)
    # P7 expectations come from the saved record's reference, never from the adapter's region.
    w = world(fx)
    auth, got = J.apply_(ns, reg, chest_item, w)
    reference = chest_item[u"record"][u"pose"][u"regions"][u"full_body"][u"oracle"][u"bones"]
    exp = got[1][u"pending"][u"expected"] if got[0] == u"ok" else {}
    root = w.handle_dag[u"rig_root"]
    rebuilt = dict((n, FB.compose((root.wp, root.wq), (o[u"position"], o[u"orientation"]))) for n, o in
                   reference.items())
    gaps = [(distance(exp[n][0], rebuilt[n][0]), angle(exp[n][1], rebuilt[n][1])) for n in rebuilt if n in exp]
    check("T.p7_expectation_is_the_saved_reference_in_the_destination_placement", exp and sorted(exp) == sorted(
        rebuilt) and max(g[0] for g in gaps) < 1e-6 and max(g[1] for g in gaps) < 1e-4,
        (len(exp), len(rebuilt), max(gaps) if gaps else None))


# ---------------------------------------------------------------------------
# W. Artist-facing behaviour
# ---------------------------------------------------------------------------

def section_copy(ns, app):
    msgs = ns["PROD_POSE_MESSAGES"]
    check("W.adapted_success_copy", msgs[u"applied-adapted"] % {u"name": u"RC3 Tails"} == ADAPTED_COPY % u"RC3 Tails")
    text = app.method_text("ProdWindow", "pose_finish_verification")
    check("W.success_status_uses_the_adapted_copy_for_an_adapted_pending", u'u"applied-adapted" if pending.get(\n' in
          text or u'u"applied-adapted" if pending.get(u"adapted")' in text, text[:0])
    rig = ns["PROD_BODY_ADAPT_MESSAGES"]
    check("W.refusal_copy_is_plain_and_says_nothing_changed", all(m.endswith(u"Nothing was changed.") and
                                                                  u"{" not in m and u"sha" not in m
                                                                  for m in rig.values()))


def run(label, fn):
    try:
        value = fn()
        check("section.%s.completed" % label, True)
        return value if value is not None else True
    except Exception:
        check("section.%s.completed" % label, False, traceback.format_exc())
        return None


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        return 2
    print("F-01 RC4 same-model cross-rig adaptation (Python %s)" % sys.version.split()[0])
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    B.IDENTITY = IDENTITY
    app = route.AppSource(route.APP_PATH)
    root = tempfile.mkdtemp(prefix="cpm_f01_cross_rig_")
    try:
        ns = B.live_namespace(app)
        fx = J.fixture()
        R.FIXTURE_DATA.append(R.fixture())
        B.IDENTITY = IDENTITY
        reg, _ = B.registries(ns)
        recs = records()
        chest_fx = with_chest(fx)
        run("wording", lambda: section_wording(ns, recs))
        run("native", lambda: section_native(ns, recs))
        run("native_refusals", lambda: section_native_refusals(ns, recs))
        run("variant", lambda: section_variant(ns, fx, chest_fx, recs))
        items = run("live", lambda: section_live(ns, reg, fx, chest_fx, root))
        if items not in (None, True):
            run("live_refusals", lambda: section_live_refusals(ns, reg, fx, chest_fx, root, items))
            run("transaction", lambda: section_transaction(ns, reg, fx, chest_fx, items))
        run("copy", lambda: section_copy(ns, app))
    finally:
        shutil.rmtree(root, True)
    failed = [r for r in RESULTS if not r[1]]
    print("RESULT: %d/%d %s (%s)" % (len(RESULTS) - len(failed), len(RESULTS),
                                     "ALL PASS" if not failed else "SOME FAILED", sys.version.split()[0]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
