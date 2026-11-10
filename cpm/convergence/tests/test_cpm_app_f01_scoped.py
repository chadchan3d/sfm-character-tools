# -*- coding: utf-8 -*-
"""F-01 SFP-1 (scoped poses, stages A/B): offline acceptance of the version 3 scoped-pose engine in the CPM application
source. Design authority: cpm/qualification/F01_SCOPED_POSE_BLUEPRINT_R3_20261108.md (R3, 2026-11-08), sections 2-11; Owner
authorization of SFP-1 stages A/B (2026-11-08).

Technique (as the stage A-E suites): the pose blocks and the CPM helpers they call are extracted verbatim and run
without SFM against fake native scenes (fake_sfm_scoped.World, an extension of the stage E fake). Real structures:
Krystal (S0 shot15/shot13, rigged, fingers direct FK), the TF2 Heavy without a rig (MC-01) and with rig_biped_simple
(MC-02), all derived from native read-only observations. Synthetic analytic skeletons give expected frames, bridges
and scales computed here with rotation matrices, independently of both CPM (quaternions) and the fake evaluator.
Real ProdWindow methods (Save New, Update Pose, Apply Pose, pose_guard) run against a fake window seam. Nothing here
demonstrates native SFM behaviour.

Usage: --phase=run (Python 2.7.5 and Python 3.10.6).
"""
from __future__ import print_function

import copy
import hashlib
import io
import json
import math
import os
import shutil
import struct
import sys
import tempfile
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_f01_pose_core as core  # noqa: E402
import test_cpm_app_f01_body as body  # noqa: E402
import fake_sfm_body as FB  # noqa: E402
import fake_sfm_scoped as FS  # noqa: E402

try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

SCOPED_FIXTURES = os.path.join(_THIS_DIR, "fixtures", "f01_scoped")
SCOPED_SHA256 = {
    "mc01_heavy_norig.json": "eb240d2e0f78e05f4df83a01086b56105e497de065eb45eff2f512af5aad8a63",
    "mc02_heavy_rig.json": "816c73360c2283251cd7c621892924146600b67bec016891a7bf080893b9f6e1",
}
HEAVY = u"models/player/heavy.mdl"
SYNTH = u"models/synthetic/analytic.mdl"
RESULTS = []


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


def outcome(fn):
    try:
        return ("ok", fn())
    except Exception as exc:
        return (type(exc).__name__, getattr(exc, "code", None), _TEXT(exc))


def refused(name, result, code=None):
    check(name, result[0] != "ok" and (code is None or result[1] == code), result)


def f32(x):
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]


def next_f32(x):
    bits = struct.unpack("<I", struct.pack("<f", float(x)))[0]
    bits += 1 if x >= 0 else -1
    return struct.unpack("<f", struct.pack("<I", bits))[0]


# ---------------------------------------------------------------------------
# namespace, worlds and the pinned instance
# ---------------------------------------------------------------------------

class Pin(object):
    world = None
    session = u"session-sfp1"
    valid = [True]
    identity = {}


def namespace(app):
    ns = body.build_namespace(app)

    def resolve(token, identity=None):
        if not Pin.valid[0] or token.get("session") != Pin.session or Pin.world is None:
            raise RuntimeError("The selected character instance is no longer present (boundary).")
        return {"shot": Pin.world.shot, "animset": Pin.world.animset, "gm": Pin.world.gm, "instance": token}

    def channels_clip(animset, shot):
        if Pin.world is None or animset is not Pin.world.animset or shot is not Pin.world.shot:
            raise RuntimeError("channels clip not identified (boundary)")
        return Pin.world.chan_clip
    ns["prod_resolve_instance"] = resolve
    ns["prod_instance_channels_clip"] = channels_clip
    ns["prod_validate_context_token"] = lambda token: Pin.valid[0] or (_ for _ in ()).throw(RuntimeError("stale"))
    ns["prod_context_token_matches"] = lambda token: Pin.valid[0] and token["instance"]["session"] == Pin.session
    return ns


def identity_of(fx):
    return {"model": fx["model"]["model_ref"], "checksum": 1234, "animset_name": fx.get("animation_set") or u"Krystal"}


def use(ns, world, fx=None):
    sfm, vs = world.modules()
    ns["sfmApp"], ns["vs"] = sfm, vs
    Pin.world = world
    Pin.valid[0] = True
    Pin.identity = identity_of(fx or world.fx)


def context(ns):
    token = {"kind": ns["PROD_INSTANCE_TOKEN_KIND"], "session": Pin.session, "shot": u"pinned"}
    return {"instance": token, "library_identity": dict(Pin.identity)}


def authorize(ns, label, item=None, mode=u"qualification"):
    return ns["prod_scope_authorize"](context(ns), Pin.identity, {}, mode, label, item)


def library(root, key):
    if not os.path.isdir(root):
        os.makedirs(root)
    return {u"character_key": key, u"char_dir": os.path.join(root, u"Characters", key), u"library_root": root,
            u"model_ref": Pin.identity["model"], u"checksum": 1234}


def capture(ns, request, label=u"Save Pose"):
    auth = authorize(ns, label)
    return ns["prod_scope_capture"](Pin.identity, auth, request, label=label)


def save(ns, lib, request, name, stamp=u"20261108-120000-000000"):
    pose = capture(ns, request)
    return ns["prod_pose_save_new"](lib, name, pose, stamp, {})


def reload(ns, lib, saved):
    return [i for i in ns["prod_pose_discover"](lib[u"char_dir"], lib[u"character_key"], {})[u"items"]
            if i[u"preset_id"] == saved[u"preset_id"]][0]


def apply(ns, item, mode=u"qualification"):
    auth = authorize(ns, u"Apply Pose", item, mode)
    result = ns["prod_scope_apply"](Pin.identity, auth, item, {})
    verdict = None
    if result.get(u"phase") == u"verification-pending":
        verdict = ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
    return result, verdict


def writes(world):
    return [c for c in world.calls if c[0] in ("SetKeyValue", "InsertKeyAtTime")]


def all_keys(world):
    return dict((n, world.keys(n)) for n in world.channels)


def changed_channels(before, after):
    return sorted(n for n in after if after[n] != before[n])


def rotate(q, axis, degrees):
    return list(FB.qnorm(FB.qmul(FS.axis_angle(axis, degrees), q)))


def turn(world, channel, axis, degrees):
    layer = world.channels[channel].attrs["log"].layer
    for k in layer.keys:
        k[1] = FB.native(rotate(FB.plain(k[1]), axis, degrees), "quat")


def move(world, channel, delta):
    layer = world.channels[channel].attrs["log"].layer
    for k in layer.keys:
        v = FB.plain(k[1])
        k[1] = FB.native([v[0] + delta[0], v[1] + delta[1], v[2] + delta[2]], "vec")


def scoped_fixture(name):
    raw = core.read(os.path.join(SCOPED_FIXTURES, name))
    check("fixture.%s.matches_its_pin" % name, core.sha(raw) == SCOPED_SHA256[name])
    return json.loads(raw.decode("utf-8"))


# --- an independent matrix evaluator (no CPM or fake-SFM mathematics) -----------------------------------------------

def mat(q):
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w)
    x, y, z, w = x / n, y / n, z / n, w / n
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def mmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mvec(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def analytic(model, bones, overrides=None):
    """World positions and rotation matrices of every bone: P = P_parent + R_parent (S_parent p), R = R_parent R(q),
    S = S_parent s. bones: {name: (parent, p, q, s)}; overrides: {name: (p, q)}."""
    overrides = overrides or {}
    out, done = {}, set()
    while len(done) < len(bones):
        for name, (parent, p, q, s) in sorted(bones.items()):
            if name in done or (parent is not None and parent not in done):
                continue
            p, q = overrides.get(name, (p, q))
            if parent is None:
                pp, pr, ps = model[0], mat(model[1]), 1.0
            else:
                pp, pr, ps = out[parent]
            off = mvec(pr, [c * ps for c in p])
            out[name] = ([pp[i] + off[i] for i in range(3)], mmul(pr, mat(q)), ps * (s if s is not None else 1.0))
            done.add(name)
    return out


def mat_angle(a, b):
    r = mmul([list(x) for x in zip(*a)], b)
    c = max(-1.0, min(1.0, (r[0][0] + r[1][1] + r[2][2] - 1.0) / 2.0))
    return math.degrees(math.acos(c))


def world_bones(world):
    return dict((n, (list(d.wp), mat(d.wq))) for n, d in world.bone_dag.items())


def live_bones(world):
    """Each bone's current local state as the fake holds it: (parent, p, q, own scale)."""
    out = {}
    for n, d in world.bone_dag.items():
        b = world.fx["bones"][n]
        p, q = world.local(d)
        out[n] = (b["parent"], p, q, world.scale(d) if "scale" in d.attrs["transform"].attrs else None)
    return out


# --- the analytic arm ------------------------------------------------------------------------------------------------

def arm_spec(spine_scale=1.2, finger_scale=0.9):
    q = FS.axis_angle
    return [(u"pelvis", None, [0.0, 0.0, 40.0], q([0, 0, 1], 15), None),
            (u"spine", u"pelvis", [0.0, 0.0, 10.0], q([1, 0, 0], 10), spine_scale),
            (u"head", u"spine", [0.0, 0.0, 12.0], q([0, 1, 0], 5), None),
            (u"jaw", u"head", [1.0, 0.0, -1.0], q([0, 1, 0], 3), None),
            (u"hair_1", u"head", [-1.0, 0.0, 3.0], q([1, 0, 0], 7), None),
            (u"upperarm", u"spine", [5.0, 0.0, 8.0], q([0, 1, 0], 30), None),
            (u"forearm", u"upperarm", [10.0, 0.0, 0.0], q([0, 0, 1], 20), None),
            (u"hand", u"forearm", [9.0, 0.0, 0.0], q([1, 0, 0], 15), None),
            (u"finger1", u"hand", [3.0, 1.0, 0.0], q([0, 0, 1], 25), finger_scale),
            (u"finger2", u"finger1", [2.0, 0.0, 0.0], q([0, 0, 1], 35), None),
            (u"finger3", u"finger2", [1.5, 0.0, 0.0], q([0, 0, 1], 10), None),
            (u"thumb1", u"hand", [1.0, 2.0, 0.0], q([1, 0, 0], 40), None),
            (u"leg", u"pelvis", [0.0, 3.0, -5.0], q([0, 1, 0], 5), None),
            (u"tail", u"pelvis", [0.0, -2.0, 0.0], q([0, 1, 0], 2), None)]


ARM_GROUPS = {u"Fingers": [u"finger1", u"finger2", u"finger3", u"thumb1"], u"Arm": [u"upperarm", u"forearm", u"hand"],
              u"Face": [u"jaw"], u"Body": [u"pelvis", u"spine", u"head", u"leg", u"tail", u"hair_1"]}
FINGERS = [u"finger1", u"finger2", u"finger3", u"thumb1"]


def arm_fixture(**kw):
    spec_kw = dict((k, kw.pop(k)) for k in (u"spine_scale", u"finger_scale") if k in kw)
    return FS.synthetic(arm_spec(**spec_kw), groups=ARM_GROUPS, **kw)


def posed_source(fx):
    """The source posture: fingers curled, the arm raised, the body turned and offset."""
    fx = FS.clone(fx)
    for n, axis, deg in ((u"finger1", [0, 0, 1], 40), (u"finger2", [0, 0, 1], 55), (u"finger3", [0, 0, 1], 30),
                         (u"thumb1", [0, 1, 0], -35), (u"upperarm", [0, 1, 0], -50), (u"forearm", [0, 0, 1], 35),
                         (u"hand", [1, 0, 0], -25), (u"pelvis", [0, 0, 1], 20), (u"spine", [0, 1, 0], 12),
                         (u"head", [1, 0, 0], 9), (u"jaw", [0, 1, 0], 14), (u"tail", [1, 0, 0], 20)):
        FS.set_key(fx, n + u"_o", rotate(fx[u"channels"][n + u"_o"]["keys"][0][1], axis, deg))
    p = fx[u"channels"][u"pelvis_p"]["keys"][0][1]
    FS.set_key(fx, u"pelvis_p", [p[0] + 4.0, p[1] - 2.0, p[2] - 6.0])     # a crouch: the body root moves
    return fx


def placed_destination(fx, position=(120.0, -40.0, 3.0), degrees=70.0):
    """Another instance: a different placement and a different arm and wrist pose."""
    fx = FS.clone(fx)
    FS.set_key(fx, u"rootTransform_p", list(position))
    FS.set_key(fx, u"rootTransform_o", FS.axis_angle([0, 0, 1], degrees))
    fx[u"model"][u"local_position"] = list(position)
    fx[u"model"][u"local_orientation"] = FS.axis_angle([0, 0, 1], degrees)
    for n, axis, deg in ((u"upperarm", [1, 0, 0], 65), (u"forearm", [0, 1, 0], -40), (u"hand", [0, 0, 1], 75),
                         (u"spine", [1, 0, 0], -8), (u"finger2", [0, 0, 1], -20)):
        FS.set_key(fx, n + u"_o", rotate(fx[u"channels"][n + u"_o"]["keys"][0][1], axis, deg))
    return fx


# ---------------------------------------------------------------------------
# A. records (R3 6, 11 "Records")
# ---------------------------------------------------------------------------

def walk_keys(value, out):
    if isinstance(value, dict):
        for k, v in value.items():
            out.add(k)
            walk_keys(v, out)
    elif isinstance(value, list):
        for v in value:
            walk_keys(v, out)
    return out


def section_records(ns, root):
    fx = arm_fixture()
    src = FS.World(posed_source(fx))
    use(ns, src, fx)
    lib = library(root, u"synthetic")
    saved = save(ns, lib, ns["prod_scope_request"](u"selected_parts", FINGERS), u"Grip")
    rec = saved[u"record"]
    pose = rec[u"pose"]
    check("A.save_writes_a_strict_version_3_record_in_the_existing_envelope",
          rec[u"schema_version"] == 3 and rec[u"record_kind"] == u"preset" and rec[u"kind"] == u"pose" and
          pose[u"version"] == 3 and pose[u"format"] == u"cpm-pose" and u"regions" not in pose and
          pose[u"engine"] == {u"rule": u"direct_fk_v1", u"revision": 1, u"carried_rule": None})
    fresh = reload(ns, lib, saved)
    check("A.fresh_reload_reads_the_record_back_exactly", fresh[u"record"] == rec and fresh[u"revision"] ==
          saved[u"revision"])
    keys = walk_keys(pose, set())
    check("A.no_runtime_identity_is_persisted", not (keys & set([u"handle", u"transform", u"log", u"layer",
                                                                   u"parent_dags", u"identity"])) and
          u"synthetic1" not in json.dumps(pose), sorted(keys & set([u"handle", u"transform"])))
    check("A.scope_is_explicit", pose[u"scope"][u"kind"] == u"selected_parts" and
          sorted(pose[u"scope"][u"posed"]) == sorted(FINGERS) and pose[u"scope"][u"carried"] == [] and
          pose[u"scope"][u"completeness"] == u"declared_scope" and
          sorted(pose[u"scope"][u"ledger"]) == sorted(fx[u"bones"]))
    raw = ns["prod_pose_serialize"](rec)

    def tampered(mutate, redigest=True):
        draft = json.loads(raw.decode("utf-8"))
        mutate(draft)
        if redigest:
            draft[u"payload_sha256"] = ns["prod_pose_payload_digest"](draft[u"pose"])
        return outcome(lambda: ns["prod_pose_parse"](ns["prod_pose_canonical_bytes"](draft), {}))
    refused("A.corrupt_digest_refuses", tampered(lambda d: d[u"pose"][u"values"][u"orientations"][u"finger1"].__setitem__(
        0, f32(0.1)), redigest=False), u"invalid-file")
    refused("A.unknown_rule_refuses", tampered(lambda d: d[u"pose"][u"engine"].update({u"rule": u"direct_fk_v2"})),
            u"invalid-file")
    refused("A.forged_rule_revision_refuses", tampered(lambda d: d[u"pose"][u"engine"].update({u"revision": 2})),
            u"invalid-file")
    refused("A.unknown_pose_version_refuses", tampered(lambda d: d[u"pose"].update({u"version": 4})), u"invalid-file")
    refused("A.unknown_field_refuses", tampered(lambda d: d[u"pose"][u"scope"].update({u"extra": 1})), u"invalid-file")
    refused("A.missing_evidence_refuses", tampered(lambda d: d[u"pose"][u"oracle"][u"bones"].pop(u"finger3")),
            u"invalid-file")
    refused("A.duplicate_bone_id_refuses", tampered(lambda d: d[u"pose"][u"structure"][u"bones"].append(
        dict(d[u"pose"][u"structure"][u"bones"][0]))), u"invalid-file")
    refused("A.duplicate_scope_membership_refuses", tampered(lambda d: d[u"pose"][u"scope"][u"posed"].append(
        u"finger1")), u"invalid-file")
    refused("A.contradictory_membership_refuses", tampered(lambda d: d[u"pose"][u"scope"][u"ledger"].update(
        {u"finger1": u"outside"})), u"invalid-file")

    def cycle(d):
        for b in d[u"pose"][u"structure"][u"bones"]:
            if b[u"id"] == u"pelvis":
                b[u"parent"] = u"finger3"
    refused("A.cyclic_hierarchy_refuses", tampered(cycle), u"invalid-file")
    refused("A.non_float32_value_refuses", tampered(lambda d: d[u"pose"][u"values"][u"orientations"][
        u"finger1"].__setitem__(0, 0.1)), u"invalid-file")
    text = raw.decode("utf-8").replace(u'"relative_position": [', u'"relative_position": [NaN, ', 1)
    refused("A.nonfinite_value_refuses", outcome(lambda: ns["prod_pose_parse"](text.encode("utf-8"), {})),
            u"invalid-file")
    refused("A.inconsistent_skeletal_evidence_refuses", tampered(
        lambda d: d[u"pose"][u"oracle"][u"bones"][u"finger2"].update({u"relative_position": [9.0, 9.0, 9.0]})),
        u"invalid-file")
    refused("A.carried_set_must_be_the_unselected_descendants", tampered(
        lambda d: d[u"pose"][u"scope"].update({u"posed": [u"finger1", u"finger3", u"thumb1"]})), u"invalid-file")
    big = json.loads(raw.decode("utf-8"))
    big[u"pose"][u"scope"][u"label"] = u"x" * 200
    blob = ns["prod_pose_canonical_bytes"](big)
    check("A.v3_records_use_the_existing_large_record_limit", len(blob) < 4 << 20)
    huge = b" " * (4 << 20) + raw
    refused("A.excessive_record_size_refuses", outcome(lambda: ns["prod_pose_parse"](huge, {})), u"invalid-file")
    padded = raw[:-2] + b"," + b'"zz": "' + b"y" * 140000 + b'"}\n'
    refused("A.oversized_record_is_parsed_strictly_and_refused_on_its_schema",
            outcome(lambda: ns["prod_pose_parse"](padded, {})), u"invalid-file")
    # v1/v2 readers unchanged: a version 1 left-arm record validates exactly as before.
    reg = body.registries(ns)[0]
    legacy = ns["prod_pose_validate"](json.loads(json.dumps(ns["prod_pose_build_record"](
        u"krystal2020", body.MODEL, u"0" * 32, u"Legacy", body.legacy_pose(ns), u"t", u"t", reg))), reg)
    check("A.version_1_records_keep_their_reader", legacy[u"pose"][u"version"] == 1 and
          sorted(legacy[u"pose"][u"regions"]) == [u"left_arm"])
    check("A.version_1_size_limit_unchanged",
          outcome(lambda: ns["prod_pose_parse"](b" " * 140000 + ns["prod_pose_serialize"](legacy), reg))[1] ==
          u"invalid-file")
    return saved, lib


# ---------------------------------------------------------------------------
# B. classification and coverage on real structures (R3 2, 3, 11 "Coverage")
# ---------------------------------------------------------------------------

def inventory(ns):
    return ns["prod_scope_inventory"](Pin.identity, authorize(ns, u"Save Pose"))


def section_coverage(ns, fx):
    counts = {}
    for key in (u"k15", u"mc01", u"mc02"):
        use(ns, FS.World(fx[key]), fx[key])
        inv = inventory(ns)
        c = {}
        for cls in inv[u"classes"].values():
            c[cls] = c.get(cls, 0) + 1
        counts[key] = (c, inv)
    c, inv = counts[u"k15"]
    check("B.krystal_classifies_as_the_native_survey_without_a_profile",
          c == {u"direct-fk": 133, u"constrained": 21, u"carried-candidate": 2} and inv[u"root"] == u"bip_pelvis", c)
    check("B.krystal_full_body_v3_refuses_rig_driven_body_naming_the_reason",
          inv[u"full_body"][u"code"] == u"rig-driven" and u"Selected parts" in inv[u"full_body"][u"message"])
    check("B.krystal_fingers_are_direct_fk_on_a_rigged_model",
          all(inv[u"classes"][n] == u"direct-fk" for n in (u"bip_index_0_l", u"bip_index_1_l", u"bip_thumb_0_l")))
    c, inv = counts[u"mc01"]
    check("B.unrigged_heavy_classifies_77_direct_fk_and_2_control_less", c == {u"direct-fk": 77,
                                                                             u"carried-candidate": 2}, c)
    check("B.unrigged_heavy_full_body_refuses_on_the_unadmitted_helpers",
          inv[u"full_body"][u"code"] == u"carried-unsupported", inv[u"full_body"])
    picker = dict((u" > ".join(r[u"path"]), r) for r in inv[u"view"])
    check("B.picker_groups_resolve_to_bone_controls", len(picker[u"Arms > LeftArm > LeftFingers"][u"bones"]) == 15 and
          all(inv[u"classes"][b] == u"direct-fk" for b in picker[u"Arms > LeftArm > LeftFingers"][u"bones"]))
    listed = set(b for r in inv[u"view"] for b in r[u"bones"])
    check("B.picker_never_lists_placement_gaze_or_flex", not any(n in listed for n in (u"rootTransform",
                                                                                         u"viewTarget")) and
          listed <= set(fx[u"mc01"][u"bones"]))
    check("B.picker_shows_unavailable_skeletal_entries_with_a_reason",
          [x[u"bone"] for x in picker[u"Other skeletal controls"][u"unavailable"]] == [u"hlp_forearm_L",
                                                                                      u"hlp_forearm_R"] and
          all(x[u"reason"] == u"no control" for x in picker[u"Other skeletal controls"][u"unavailable"]))
    check("B.flex_only_face_is_not_highlighted", inv[u"highlighted"] == [])
    c, inv = counts[u"mc02"]
    check("B.rigged_heavy_classifies_as_the_survey", c == {u"direct-fk": 54, u"constrained": 23,
                                                         u"carried-candidate": 2}, c)
    picker = dict((u" > ".join(r[u"path"]), r) for r in inv[u"view"])
    check("B.rigged_heavy_rig_driven_controls_are_listed_as_unavailable",
          picker[u"Arms > LeftArm"][u"bones"] == [] and len(picker[u"Arms > LeftArm"][u"unavailable"]) == 4 and
          len(picker[u"RigArms > LeftArm > LeftFingers"][u"bones"]) == 15, sorted(picker))
    check("B.rigged_heavy_full_body_refuses_rig_driven", inv[u"full_body"][u"code"] == u"rig-driven")
    # A fully direct-FK body is available; hair and other secondary anatomy are included by default.
    arm = arm_fixture()
    use(ns, FS.World(arm), arm)
    inv = inventory(ns)
    check("B.fully_direct_fk_body_is_available_with_no_profile", inv[u"full_body"][u"status"] == u"available")
    S = compile_request(ns, ns["prod_scope_request"](u"full_body"))
    check("B.hair_and_tail_are_included_by_default", u"hair_1" in S[u"posed"] and u"tail" in S[u"posed"] and
          S[u"ledger"][u"hair_1"] == u"posed")
    check("B.a_group_merely_named_face_cannot_authorize_omission",
          u"jaw" in S[u"posed"] and inv[u"highlighted"] == [u"jaw"] and S[u"excluded"] == [])
    state = ns["prod_scope_dialog_state"](inv, {u"kind": u"full_body"})
    check("B.full_body_summary_discloses_included_facial_bones", state[u"save_enabled"] and
          state[u"summary"] == u"Includes the listed facial bones. Facial expressions are not saved.", state)
    # An unsupported tail: Full body refuses naming it; Selected parts without it remains available.
    bad = FS.clone(arm)
    bad[u"channels"][u"tail_o"]["from"] = None
    bad[u"channels"][u"tail_o"]["from_attribute"] = u""
    use(ns, FS.World(bad), bad)
    inv = inventory(ns)
    check("B.unsupported_tail_is_never_silently_omitted", inv[u"full_body"][u"status"] == u"refused" and
          u"tail" in inv[u"full_body"][u"message"] and u"Choose Selected parts" in inv[u"full_body"][u"message"],
          inv[u"full_body"])
    refused("B.tail_cannot_be_selected", outcome(lambda: compile_request(ns, ns["prod_scope_request"](
        u"selected_parts", [u"tail"]))), u"unsupported-selection")
    check("B.selected_parts_without_the_tail_remain_available",
          sorted(compile_request(ns, ns["prod_scope_request"](u"selected_parts", FINGERS))[u"posed"]) ==
          sorted(FINGERS))


def compile_request(ns, request):
    row = ns["prod_resolve_instance"](context(ns)["instance"])
    st = ns["prod_scope_state"](row, request)
    return st[u"S"]


# ---------------------------------------------------------------------------
# C. exclusion boundaries and scope review (R3 2.3, 4, 11 "Exclusion boundaries", "Scope semantics")
# ---------------------------------------------------------------------------

def face_solver(fx, child=False, also_neck=False):
    """The jaw driven by a facial constraint following the head (one-way), as an unfamiliar facial system."""
    fx = FS.clone(fx)
    jaw = fx[u"bones"][u"jaw"]
    head = fx[u"bones"][u"head"]
    slave = 900001
    op = {u"handle": 900000, u"type": u"DmeRigOrientConstraintOperator", u"name": u"face_jaw_follow",
          u"owners": [u"animation_set"], u"slaves": {u"slave": {u"slave": slave, u"target": jaw[u"handle"]}},
          u"targets": [{u"handle": 900002, u"target": head[u"handle"], u"weight": {u"status": u"READ", u"value": 1.0},
                        u"oOffset": {u"status": u"READ", u"value": FS.axis_angle([0, 1, 0], 6)},
                        u"vecOffset": {u"status": u"ABSENT"}}], u"pole": None, u"solver": {}}
    fx[u"operators"].append(op)
    for suffix in (u"_p", u"_o"):                      # the jaw control now drives the constraint slave (dormant)
        fx[u"channels"][u"jaw" + suffix]["to"] = {u"handle": slave, u"type": u"DmeConstraintSlave", u"name": u"s"}
    if child:
        fx[u"bones"][u"teeth"] = {u"index": 99, u"handle": 900010, u"transform": 900011, u"parent": u"jaw",
                                  u"parent_count": 1, u"parent_dag": jaw[u"handle"],
                                  u"local_position": [0.5, 0.0, 0.0], u"local_orientation": [0.0, 0.0, 0.0, 1.0],
                                  u"world_position": [0.0] * 3, u"world_orientation": [0.0, 0.0, 0.0, 1.0],
                                  u"scale": {u"status": u"ABSENT"}}
        h = [900020]

        def nh():
            h[0] += 1
            return h[0]
        c = {u"handle": nh(), u"type": u"DmeTransformControl", u"channels": {}, u"values": {}}
        for attr, suffix, lt, ly, v in ((u"position", u"_p", u"DmeVector3Log", u"DmeVector3LogLayer", [0.5, 0.0, 0.0]),
                                        (u"orientation", u"_o", u"DmeQuaternionLog", u"DmeQuaternionLogLayer",
                                         [0.0, 0.0, 0.0, 1.0])):
            ch = {u"handle": nh(), u"from": {u"handle": c[u"handle"], u"type": u"DmeTransformControl",
                                            u"name": u"teeth"},
                  u"from_attribute": u"valuePosition" if attr == u"position" else u"valueOrientation",
                  u"to": {u"handle": 900011, u"type": u"DmeTransform", u"name": u"bone 99 (teeth)"},
                  u"to_attribute": attr, u"mode": 3, u"log_type": lt, u"log": nh(), u"layers": [ly], u"layer": nh(),
                  u"keys": [[0, v]], u"value": v, u"clock": 50000, u"curveinfo": {u"status": u"READ", u"value": None}}
            fx[u"channels"][u"teeth" + suffix] = ch
            c[u"channels"][u"positionChannel" if attr == u"position" else u"orientationChannel"] = ch[u"handle"]
        fx[u"controls"][u"teeth"] = c
    return fx


def section_exclusions(ns, root):
    arm = arm_fixture()
    face = face_solver(posed_source(arm))
    use(ns, FS.World(face), face)
    inv = inventory(ns)
    check("C.unfamiliar_face_needs_scope_review_not_auto_exclusion",
          inv[u"full_body"][u"status"] == u"review-required" and inv[u"full_body"][u"review"] == [u"jaw"],
          inv[u"full_body"])
    state = ns["prod_scope_dialog_state"](inv, {u"kind": u"full_body"})
    check("C.review_blocks_save_until_resolved", not state[u"save_enabled"] and
          state[u"summary"] == ns["PROD_SCOPE_REVIEW_SCOPE_COPY"], state)
    refused("C.requesting_the_unsupported_solver_for_capture_refuses",
            outcome(lambda: capture(ns, ns["prod_scope_request"](u"full_body"))), u"rig-driven")
    state = ns["prod_scope_dialog_state"](inv, {u"kind": u"full_body", u"exclude_highlighted": True})
    check("C.confirmed_exclusion_allows_full_body_with_honest_copy", state[u"save_enabled"] and
          state[u"summary"] == u"The listed controls are left as they are on the character." and state[u"request"][u"exclusions"][0][u"provenance"] ==
          u"user_confirmed", state)
    lib = library(root, u"synthetic_face")
    saved = ns["prod_pose_save_new"](lib, u"Body only", capture(ns, state[u"request"]), u"20261108-130000-000000", {})
    pose = saved[u"record"][u"pose"]
    check("C.exclusion_is_recorded_with_its_provenance", pose[u"scope"][u"exclusions"][0][u"bones"] == [u"jaw"] and
          pose[u"scope"][u"ledger"][u"jaw"] == u"excluded-expression" and pose[u"scope"][u"preserved"] == [] and
          u"jaw" not in pose[u"values"][u"orientations"])
    dst_fx = face_solver(placed_destination(arm))
    dst = FS.World(dst_fx)
    use(ns, dst, dst_fx)
    before = all_keys(dst)
    jaw_inputs = (dst.keys(u"jaw_p"), dst.keys(u"jaw_o"))
    result, verdict = apply(ns, reload(ns, lib, saved))
    check("C.one_way_head_follow_is_allowed_and_verified", result[u"phase"] == u"verification-pending" and
          verdict == {u"phase": u"committed-verified"}, (result.get(u"phase"), verdict))
    check("C.excluded_inputs_keys_and_graph_unchanged", (dst.keys(u"jaw_p"), dst.keys(u"jaw_o")) == jaw_inputs and
          u"jaw_o" not in changed_channels(before, all_keys(dst)))
    # The face's excluded controller also posing a body bone: user confirmation cannot bypass the boundary.
    teeth = face_solver(posed_source(arm), child=True)
    use(ns, FS.World(teeth), teeth)
    refused("C.excluded_solver_with_a_posed_descendant_refuses", outcome(lambda: capture(
        ns, ns["prod_scope_request"](u"full_body", [], state[u"request"][u"exclusions"]))), u"exclusion-boundary")
    # Shared mutable resource between an excluded direct-FK branch and the plan.
    shared = posed_source(arm)
    shared[u"channels"][u"jaw_o"]["log"] = shared[u"channels"][u"head_o"]["log"]
    w = FS.World(shared)
    w.channels[u"jaw_o"].attrs["log"] = w.channels[u"head_o"].attrs["log"]
    use(ns, w, shared)
    excl = [{u"id": u"face", u"bones": [u"jaw"], u"reason": u"r", u"provenance": u"user_confirmed",
             u"policy_revision": None, u"label": u"Face"}]
    got = outcome(lambda: capture(ns, ns["prod_scope_request"](u"full_body", [], excl)))
    refused("C.shared_log_with_an_excluded_channel_refuses", got)
    check("C.shared_log_refusal_is_an_authority_or_boundary_reason",
          got[1] in (u"shared-authority", u"exclusion-boundary"), got)
    # Imported exclusions never authorize: a record excluding the jaw on a destination where the jaw solver writes a
    # body bone refuses at P1 with no write.
    cross = face_solver(placed_destination(arm))
    cross[u"operators"][0][u"slaves"][u"slave"][u"target"] = cross[u"bones"][u"hand"][u"handle"]
    w = FS.World(cross)
    use(ns, w, cross)
    got = outcome(lambda: apply(ns, reload(ns, lib, saved)))
    refused("C.imported_exclusion_does_not_authorize_a_cross_boundary_writer", got)
    check("C.cross_boundary_refusal_writes_nothing", not writes(w) and not w.dm.calls)
    return lib, saved


# ---------------------------------------------------------------------------
# D/F/G. frames, bridges and scale, against independent analytic expectations
# ---------------------------------------------------------------------------

def max_errors(world, expected, names):
    dp = max(math.sqrt(sum((world.bone_dag[n].wp[i] - expected[n][0][i]) ** 2 for i in range(3))) for n in names)
    dq = max(mat_angle(mat(world.bone_dag[n].wq), expected[n][1]) for n in names)
    return dp, dq


def section_frames(ns, root):
    arm = arm_fixture()
    src_fx = posed_source(arm)
    src = FS.World(src_fx)
    use(ns, src, arm)
    lib = library(root, u"synthetic_frames")
    grip = save(ns, lib, ns["prod_scope_request"](u"selected_parts", FINGERS), u"Grip")
    source_local = live_bones(src)
    dst_fx = placed_destination(arm)
    dst = FS.World(dst_fx)
    use(ns, dst, arm)
    before = all_keys(dst)
    base_local = live_bones(dst)
    model = (list(dst.gm.wp), list(dst.gm.wq))
    hand_before = (list(dst.bone_dag[u"hand"].wp), list(dst.bone_dag[u"hand"].wq))
    result, verdict = apply(ns, reload(ns, lib, grip))
    check("F.finger_pose_applies_beneath_a_differently_placed_and_rotated_wrist",
          result[u"phase"] == u"verification-pending" and verdict == {u"phase": u"committed-verified"},
          (result.get(u"phase"), verdict))
    expected = analytic(model, base_local, dict((n, (base_local[n][1], source_local[n][2])) for n in FINGERS))
    dp, dq = max_errors(dst, expected, list(dst.bone_dag))
    check("F.independent_matrix_evaluation_matches_every_bone", dp < 1e-3 and dq < 0.01, (dp, dq))
    check("F.wrist_and_arm_inputs_unchanged", (list(dst.bone_dag[u"hand"].wp), list(dst.bone_dag[u"hand"].wq)) ==
          hand_before and all(dst.keys(n + s) == before[n + s] for n in (u"upperarm", u"forearm", u"hand")
                              for s in (u"_p", u"_o")))
    check("F.only_finger_inputs_changed", changed_channels(before, all_keys(dst)) ==
          sorted(n + s for n in FINGERS for s in (u"_o", u"_p")), changed_channels(before, all_keys(dst)))
    check("F.destination_offsets_are_kept_not_imported", all(dst.keys(n + u"_p")[-1][1] == base_local[n][1] or
                                                               [f32(c) for c in base_local[n][1]] ==
                                                               dst.keys(n + u"_p")[-1][1] for n in FINGERS))
    pending_expected = result[u"pending"][u"expected"]
    gap = max(math.sqrt(sum((pending_expected[n][0][i] - expected[n][0][i]) ** 2 for i in range(3)))
              for n in FINGERS)
    check("F.cpm_parent_first_expectation_equals_the_independent_one", gap < 1e-4, gap)
    # Upper arm and hand selected, forearm unselected: the bridge keeps the destination articulation.
    use(ns, src, arm)
    bridge = save(ns, lib, ns["prod_scope_request"](u"selected_parts", [u"upperarm", u"hand"]), u"Bridge")
    rec = bridge[u"record"][u"pose"]
    check("F.unselected_bridge_and_descendants_are_carried", sorted(rec[u"scope"][u"carried"]) == sorted(
        [u"forearm"] + FINGERS) and rec[u"scope"][u"posed"] == [u"upperarm", u"hand"] and
        rec[u"scope"][u"ledger"][u"forearm"] == u"carried", rec[u"scope"])
    dst2 = FS.World(placed_destination(arm))
    use(ns, dst2, arm)
    base2 = live_bones(dst2)
    model2 = (list(dst2.gm.wp), list(dst2.gm.wq))
    before2 = all_keys(dst2)
    result, verdict = apply(ns, reload(ns, lib, bridge))
    check("F.bridge_pose_verifies", verdict == {u"phase": u"committed-verified"}, verdict)
    expected = analytic(model2, base2, {u"upperarm": (base2[u"upperarm"][1], source_local[u"upperarm"][2]),
                                        u"hand": (base2[u"hand"][1], source_local[u"hand"][2])})
    dp, dq = max_errors(dst2, expected, list(dst2.bone_dag))
    check("F.hand_uses_the_expected_forearm_frame_and_destination_forearm_state", dp < 1e-3 and dq < 0.01, (dp, dq))
    check("F.forearm_receives_no_write", dst2.keys(u"forearm_o") == before2[u"forearm_o"] and
          dst2.keys(u"forearm_p") == before2[u"forearm_p"])
    check("F.carried_fingers_keep_their_destination_articulation",
          all(dst2.keys(n + u"_o") == before2[n + u"_o"] for n in FINGERS))
    check("F.unrelated_branches_unchanged", all(dst2.keys(n + s) == before2[n + s] for n in (u"leg", u"tail", u"jaw")
                                                for s in (u"_o", u"_p")))
    # Counterexamples: a self-consistent wrong planner is caught by the independent observations.
    for label, patch in ((u"wrong_multiplication_order", u"order"), (u"missing_ancestor_scale", u"omit"),
                         (u"double_ancestor_scale", u"double")):
        w = FS.World(placed_destination(arm))
        use(ns, w, arm)
        saved_fns = dict((k, ns[k]) for k in (u"prod_scope_compose", u"prod_scope_cumulative"))
        try:
            if patch == u"order":
                real = saved_fns[u"prod_scope_compose"]

                def wrong(parent, s, local, real=real):
                    p, q = real(parent, s, local)
                    return p, ns["prod_pose_unit"](ns["prod_pose_qmul"](local[1], parent[1]))
                ns["prod_scope_compose"] = wrong
            else:
                real = saved_fns[u"prod_scope_cumulative"]
                ns["prod_scope_cumulative"] = (lambda D, n, real=real: 1.0) if patch == u"omit" else (
                    lambda D, n, real=real: real(D, n) ** 2)
            got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
        finally:
            ns.update(saved_fns)
        refused("F.counterexample_%s_refuses_before_any_write" % label, got)
        check("F.counterexample_%s_writes_nothing" % label, not writes(w) and not w.dm.calls, writes(w)[:2])
    # The same wrong planner with its own pre-write cross-checks disabled: P7's native readback still refuses success.
    w = FS.World(placed_destination(arm))
    use(ns, w, arm)
    saved_fns = dict((k, ns[k]) for k in (u"prod_scope_cumulative", u"prod_scope_expected",
                                          u"prod_scope_check_against_source"))
    real_cum, real_expected = saved_fns[u"prod_scope_cumulative"], saved_fns[u"prod_scope_expected"]

    def wrong_expected(*args):
        # Only the expectation doubles the ancestor scale; every other check uses the real primitive.
        ns["prod_scope_cumulative"] = lambda D, n: real_cum(D, n) ** 2
        try:
            return real_expected(*args)
        finally:
            ns["prod_scope_cumulative"] = real_cum
    try:
        ns["prod_scope_expected"] = wrong_expected
        ns["prod_scope_check_against_source"] = lambda *a, **k: []
        result, verdict = apply(ns, reload(ns, lib, grip))
    finally:
        ns.update(saved_fns)
    check("F.self_consistent_wrong_planner_is_never_verified", result[u"phase"] == u"verification-pending" and
          verdict[u"phase"] == u"committed-unverified", verdict)
    return lib, grip


def section_scale(ns, root):
    # Scale above and inside the partial boundary, own versus parent scale.
    arm = arm_fixture(spine_scale=1.25, finger_scale=0.8)
    src = FS.World(posed_source(arm))
    use(ns, src, arm)
    lib = library(root, u"synthetic_scale")
    grip = save(ns, lib, ns["prod_scope_request"](u"selected_parts", FINGERS), u"Grip")
    scales = grip[u"record"][u"pose"][u"structure"][u"scales"]
    check("G.boundary_records_the_cumulative_ancestor_scale",
          abs(scales[u"boundaries"][u"finger1"] - 1.25) < 1e-9 and abs(scales[u"boundaries"][u"thumb1"] - 1.25) < 1e-9,
          scales[u"boundaries"])
    source_local = live_bones(src)
    dst = FS.World(placed_destination(arm))
    use(ns, dst, arm)
    base = live_bones(dst)
    model = (list(dst.gm.wp), list(dst.gm.wq))
    result, verdict = apply(ns, reload(ns, lib, grip))
    check("G.nonunit_nested_scales_apply_and_verify", verdict == {u"phase": u"committed-verified"}, verdict)
    expected = analytic(model, base, dict((n, (base[n][1], source_local[n][2])) for n in FINGERS))
    dp, dq = max_errors(dst, expected, FINGERS)
    check("G.parent_scale_acts_on_the_child_offset_own_scale_on_descendants", dp < 1e-3 and dq < 0.01, (dp, dq))
    f1, f2 = dst.bone_dag[u"finger1"], dst.bone_dag[u"finger2"]
    gap = math.sqrt(sum((f2.wp[i] - f1.wp[i]) ** 2 for i in range(3)))
    check("G.finger2_offset_is_scaled_by_spine_and_finger1_scales", abs(gap - 2.0 * 1.25 * 0.8) < 1e-3, gap)
    # A destination whose ancestor scale differs: proportions refuse.
    other = arm_fixture(spine_scale=1.1, finger_scale=0.8)
    w = FS.World(placed_destination(other))
    use(ns, w, other)
    refused("G.ancestor_scale_mismatch_refuses", outcome(lambda: apply(ns, reload(ns, lib, grip))), u"proportions")
    check("G.scale_mismatch_writes_nothing", not writes(w))
    # Unsupported model scale refuses (wrapper scale is never assumed to be 1).
    big = arm_fixture(model_scale=2.0)
    w = FS.World(big)
    use(ns, w, big)
    refused("G.unsupported_model_scale_refuses", outcome(lambda: capture(
        ns, ns["prod_scope_request"](u"selected_parts", FINGERS))), u"scale-unsupported")
    # Scale drift during the operation: P2 refuses; after the commit P7 does not verify.
    w = FS.World(placed_destination(arm))
    use(ns, w, arm)
    real = ns["prod_scope_preflight"]

    def preflight_then_scale(*args):
        pre = real(*args)
        w.bone_dag[u"spine"].attrs["transform"].set("scale", 1.3)
        w.evaluate()
        return pre
    ns["prod_scope_preflight"] = preflight_then_scale
    try:
        got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
    finally:
        ns["prod_scope_preflight"] = real
    refused("G.scale_drift_at_P2_refuses", got, u"stale")
    check("G.scale_drift_at_P2_writes_nothing", not writes(w))
    w = FS.World(placed_destination(arm))
    use(ns, w, arm)
    item = reload(ns, lib, grip)
    auth = authorize(ns, u"Apply Pose", item)
    result = ns["prod_scope_apply"](Pin.identity, auth, item, {})
    w.bone_dag[u"spine"].attrs["transform"].set("scale", 1.3)
    w.evaluate()
    verdict = ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
    check("G.scale_drift_at_P7_prevents_verified_success", verdict[u"phase"] == u"committed-unverified", verdict)
    # A supported scale-only operator (Krystal's bip_head scale expression) does not conflict with orientation.
    return lib


def section_krystal_fingers(ns, fx, root):
    use(ns, FS.World(fx[u"k15"]), fx[u"k15"])
    lib = library(root, u"krystal2020")
    fingers = [n for n in fx[u"k15"][u"bones"] if n.endswith(u"_l") and any(
        t in n for t in (u"index", u"middle", u"ring", u"pinky", u"thumb")) and not n.endswith(u"Toe_l") and
        u"Toe" not in n]
    inv = inventory(ns)
    fingers = [n for n in fingers if inv[u"classes"][n] == u"direct-fk"]
    grip = save(ns, lib, ns["prod_scope_request"](u"selected_parts", fingers), u"Krystal grip")
    body.WRITTEN_HANDLES.update(body.profile_of(ns, body.registries(ns)[0])[u"written_handle_channels"])
    dst = FS.World(fx[u"k13"])
    body.pose_differently(dst)
    use(ns, dst, fx[u"k13"])
    before = all_keys(dst)
    hand = (list(dst.bone_dag[u"bip_hand_l"].wp), list(dst.bone_dag[u"bip_hand_l"].wq))
    result, verdict = apply(ns, reload(ns, lib, grip))
    check("K.krystal_fingers_apply_on_another_instance_with_a_differently_posed_arm",
          verdict == {u"phase": u"committed-verified"}, (result.get(u"phase"), verdict))
    check("K.krystal_arm_rig_and_wrist_unchanged",
          (list(dst.bone_dag[u"bip_hand_l"].wp), list(dst.bone_dag[u"bip_hand_l"].wq)) == hand and
          all(after == before[n] for n, after in all_keys(dst).items() if not any(n.startswith(f + u"_")
                                                                                    for f in fingers)))
    jaw = [n for n in fx[u"k15"][u"bones"] if n == u"jaw"]
    if jaw:
        use(ns, FS.World(fx[u"k15"]), fx[u"k15"])
        S = compile_request(ns, ns["prod_scope_request"](u"selected_parts", jaw))
        check("G.scale_expression_on_an_ancestor_is_a_dependency_not_a_co_writer",
              S[u"posed"] == [u"jaw"] and u"bip_head" in S[u"chain"], S[u"chain"][-3:])
    return lib, grip


# ---------------------------------------------------------------------------
# H. control-less bones: constant_channel_carried_v1 (R3 3.1)
# ---------------------------------------------------------------------------

def section_carried(ns, fx, root):
    heavy = fx[u"mc01"]
    use(ns, FS.World(heavy), heavy)
    inv = inventory(ns)
    check("H.mc01_helpers_are_candidates_only_never_fixed_by_their_null_source",
          inv[u"classes"][u"hlp_forearm_L"] == u"carried-candidate" and inv[u"carried"] == [] and
          inv[u"full_body"][u"code"] == u"carried-unsupported")
    check("H.procedural_guard_reports_no_supported_contract",
          ns["prod_scope_procedural_guard"](None, None)[u"status"] == u"unsupported")
    lib = library(root, u"heavy")
    left = [b for r in inv[u"view"] if r[u"path"][-1] == u"LeftFingers" for b in r[u"bones"]]
    grip = save(ns, lib, ns["prod_scope_request"](u"selected_parts", left), u"Heavy grip")
    check("H.isolated_partial_operation_remains_possible", sorted(grip[u"record"][u"pose"][u"scope"][u"posed"]) ==
          sorted(left) and len(left) == 15)
    enabled = ns["PROD_SCOPE_CARRIED_ENABLED"]
    guard = ns["prod_scope_procedural_guard"]
    positive = lambda L, D: {u"status": u"procedural-disabled", u"bones": [u"hlp_forearm_L", u"hlp_forearm_R"],
                             u"evidence": u"synthetic test evidence"}

    def admitted(world, f):
        use(ns, world, f)
        row = ns["prod_resolve_instance"](context(ns)["instance"])
        st = ns["prod_scope_state"](row)
        return ns["prod_scope_carried_inputs"](st, ns["prod_scope_request"](u"full_body"))
    try:
        enabled[0] = True
        check("H.enabled_without_a_positive_guard_still_refuses", admitted(FS.World(heavy), heavy) == [])
        ns["prod_scope_procedural_guard"] = positive
        check("H.the_mc01_repeated_key_shape_needs_qualified_extrapolation",
              admitted(FS.World(heavy), heavy) == [])
        spanning = FS.clone(heavy)
        for n in (u"hlp_forearm_L_p", u"hlp_forearm_L_o", u"hlp_forearm_R_p", u"hlp_forearm_R_o"):
            k = spanning[u"channels"][n]["keys"]
            spanning[u"channels"][n]["keys"] = [k[0], [60000, list(k[0][1])]]
        check("H.fully_supported_synthetic_positive_is_admitted",
              sorted(admitted(FS.World(spanning), spanning)) == [u"hlp_forearm_L", u"hlp_forearm_R"])
        moving = FS.clone(spanning)
        k = moving[u"channels"][u"hlp_forearm_L_o"]["keys"]
        k[1][1] = rotate(k[1][1], [1, 0, 0], 5)
        check("H.nonconstant_keys_refuse", admitted(FS.World(moving), moving) == [u"hlp_forearm_R"])
        w = FS.World(spanning)
        log = w.channels[u"hlp_forearm_L_p"].attrs["log"]
        log.HasDefaultValue = lambda: True
        log.GetDefaultValue = lambda: FB.Vector(1.0, 2.0, 3.0)
        check("H.contradictory_default_refuses", admitted(w, spanning) == [u"hlp_forearm_R"])
        w = FS.World(spanning)
        w.channels[u"hlp_forearm_L_o"].attrs["log"].layer.IsUsingCurveTypes = lambda: True
        check("H.curve_data_refuses", admitted(w, spanning) == [u"hlp_forearm_R"])
        w = FS.World(spanning)
        w.channels[u"hlp_forearm_R_p"].attrs["log"] = w.channels[u"hlp_forearm_L_p"].attrs["log"]
        got = outcome(lambda: admitted(w, spanning))
        check("H.shared_resource_refuses", got[0] != "ok" or u"hlp_forearm_R" not in got[1], got)
        w = FS.World(spanning)
        del w.channels[u"hlp_forearm_L_p"].attrs["fromElement"]
        w.channels[u"hlp_forearm_L_p"].order.remove("fromElement")
        refused("H.unreadable_source_is_not_verified_null", outcome(lambda: admitted(w, spanning)),
                u"evidence-unreadable")
        ns["prod_scope_procedural_guard"] = lambda L, D: {u"status": u"unknown"}
        check("H.unknown_procedural_authority_refuses", admitted(FS.World(spanning), spanning) == [])
        ns["prod_scope_procedural_guard"] = positive
        # Full body with admitted carried constants: no helper writes, helpers follow their posed parents.
        src_fx = FS.clone(spanning)
        FS.set_key(src_fx, u"bip_lowerArm_L_o", rotate(src_fx[u"channels"][u"bip_lowerArm_L_o"]["keys"][0][1],
                                                      [0, 0, 1], 30))
        use(ns, FS.World(src_fx), heavy)
        body_pose = save(ns, lib, ns["prod_scope_request"](u"full_body"), u"Heavy body")
        rec = body_pose[u"record"][u"pose"]
        check("H.full_body_records_the_carried_rule_and_roles",
              rec[u"engine"][u"carried_rule"] == {u"rule": u"constant_channel_carried_v1", u"revision": 1} and
              rec[u"scope"][u"ledger"][u"hlp_forearm_L"] == u"carried-constant" and
              u"hlp_forearm_L" in rec[u"scope"][u"carried"])
        dst_fx = FS.clone(spanning)
        FS.set_key(dst_fx, u"rootTransform_p", [10.0, 20.0, 0.0])
        dst = FS.World(dst_fx)
        use(ns, dst, heavy)
        before = all_keys(dst)
        result, verdict = apply(ns, reload(ns, lib, body_pose))
        check("H.full_body_with_carried_constants_verifies", verdict == {u"phase": u"committed-verified"},
              (result.get(u"phase"), verdict))
        check("H.no_helper_writes_or_missing_key_insertion",
              all(dst.keys(n) == before[n] for n in before if n.startswith(u"hlp_")))
        bad = FS.clone(spanning)
        for n in (u"hlp_forearm_L_o",):
            FS.set_key(bad, n, rotate(bad[u"channels"][n]["keys"][0][1], [1, 0, 0], 8))
            bad[u"channels"][n]["keys"].append([60000, list(bad[u"channels"][n]["keys"][0][1])])
        w = FS.World(bad)
        use(ns, w, heavy)
        refused("H.full_body_refuses_incompatible_helper_state", outcome(lambda: apply(ns, reload(ns, lib, body_pose))),
                u"proportions")
    finally:
        enabled[0] = False
        ns["prod_scope_procedural_guard"] = guard
    # Disabled again: the saved carried pose refuses (its rule is not admitted in this build).
    w = FS.World(heavy)
    use(ns, w, heavy)
    refused("H.disabled_capability_refuses_the_saved_carried_pose", outcome(lambda: apply(
        ns, reload(ns, lib, body_pose))))
    check("H.disabled_refusal_writes_nothing", not writes(w))
    return lib, grip


# ---------------------------------------------------------------------------
# I. full body: root translation and placement (R3 5)
# ---------------------------------------------------------------------------

def section_full_body(ns, root):
    arm = arm_fixture()
    src = FS.World(posed_source(arm))
    use(ns, src, arm)
    lib = library(root, u"synthetic_body")
    full = save(ns, lib, ns["prod_scope_request"](u"full_body"), u"Crouch")
    rec = full[u"record"][u"pose"]
    check("I.full_body_declares_its_body_and_root_translation",
          rec[u"scope"][u"kind"] == u"full_body" and rec[u"scope"][u"completeness"] == u"declared_body" and
          rec[u"scope"][u"root_translation"] == u"included" and rec[u"structure"][u"root"] == u"pelvis" and
          rec[u"values"][u"root_translation"] == src.keys(u"pelvis_p")[0][1])
    source_local = live_bones(src)
    fresh = reload(ns, lib, full)
    check("I.full_body_persists_and_reloads", fresh[u"record"] == full[u"record"])
    dst = FS.World(placed_destination(arm))
    use(ns, dst, arm)
    before = all_keys(dst)
    base = live_bones(dst)
    model = (list(dst.gm.wp), list(dst.gm.wq))
    result, verdict = apply(ns, fresh)
    check("I.full_body_applies_to_a_compatible_instance", verdict == {u"phase": u"committed-verified"},
          (result.get(u"phase"), verdict))
    expected = analytic(model, base, dict((n, (source_local[n][1] if n == u"pelvis" else base[n][1],
                                               source_local[n][2])) for n in base))
    dp, dq = max_errors(dst, expected, list(dst.bone_dag))
    check("I.whole_body_matches_the_independent_expectation", dp < 1e-3 and dq < 0.01, (dp, dq))
    check("I.body_root_moves_but_model_placement_is_preserved",
          dst.keys(u"rootTransform_p") == before[u"rootTransform_p"] and
          dst.keys(u"rootTransform_o") == before[u"rootTransform_o"] and (list(dst.gm.wp), list(dst.gm.wq)) == model
          and dst.keys(u"pelvis_p")[-1][1] == src.keys(u"pelvis_p")[0][1])
    check("I.no_source_offset_transfer_for_non_root_bones",
          all(dst.keys(n + u"_p")[-1][1] == before[n + u"_p"][-1][1] for n in base if n != u"pelvis"))
    # Update keeps the scope; a changed scope is Save New.
    use(ns, src, arm)
    turn(src, u"spine_o", [1, 0, 0], 11)
    src.evaluate()
    item = reload(ns, lib, full)
    pose = capture(ns, ns["prod_scope_record_request"](item[u"record"][u"pose"]), u"Update Pose")
    updated = ns["prod_pose_update"](lib, item, pose, u"20261108-140000-000000", {})
    check("I.update_recaptures_in_place_with_the_same_scope", updated[u"path"] == item[u"path"] and
          updated[u"record"][u"pose"][u"scope"] == item[u"record"][u"pose"][u"scope"] and
          updated[u"record"][u"pose"][u"values"] != item[u"record"][u"pose"][u"values"])
    other = capture(ns, ns["prod_scope_request"](u"selected_parts", FINGERS))
    got = outcome(lambda: ns["prod_pose_update"](lib, reload(ns, lib, full), other, u"20261108-140100-000000", {}))
    refused("I.update_cannot_silently_change_scope", got, u"regions")
    # Ambiguous placement: two top-level bones.
    two = FS.clone(arm)
    two[u"bones"][u"leg"][u"parent"] = None
    two[u"bones"][u"leg"][u"parent_dag"] = two[u"model"][u"handle"]
    use(ns, FS.World(two), two)
    refused("I.ambiguous_body_root_refuses", outcome(lambda: capture(ns, ns["prod_scope_request"](u"full_body"))),
            u"placement-ambiguous")
    # Structural offsets: within the provisional limit passes, beyond it refuses; a one-ULP drift at P2 refuses.
    for label, delta, ok in ((u"within", 0.00004, True), (u"beyond", 0.00006, False)):
        f = placed_destination(arm)
        p = f[u"channels"][u"forearm_p"]["keys"][0][1]
        FS.set_key(f, u"forearm_p", [p[0] + delta, p[1], p[2]])
        f[u"bones"][u"forearm"][u"local_position"] = [f32(p[0] + delta), p[1], p[2]]
        w = FS.World(f)
        use(ns, w, arm)
        got = outcome(lambda: apply(ns, reload(ns, lib, full)))
        if ok:
            check("I.structural_offset_%s_the_limit_applies" % label, got[0] == "ok" and
                  got[1][1] == {u"phase": u"committed-verified"}, got)
        else:
            refused("I.structural_offset_%s_the_limit_refuses" % label, got, u"fk-position")
            check("I.offset_refusal_writes_nothing", not writes(w))
    w = FS.World(placed_destination(arm))
    use(ns, w, arm)
    real = ns["prod_scope_preflight"]

    def preflight_then_ulp(*args):
        pre = real(*args)
        layer = w.channels[u"forearm_p"].attrs["log"].layer
        v = FB.plain(layer.keys[0][1])
        layer.keys[0][1] = FB.native([next_f32(v[0]), v[1], v[2]], "vec")
        w.evaluate()
        return pre
    ns["prod_scope_preflight"] = preflight_then_ulp
    try:
        got = outcome(lambda: apply(ns, reload(ns, lib, full)))
    finally:
        ns["prod_scope_preflight"] = real
    refused("I.one_ulp_offset_drift_between_P1_and_P2_refuses", got, u"stale")
    check("I.drift_refusal_writes_nothing", not writes(w))
    return lib, full


# ---------------------------------------------------------------------------
# J/K. authority and key planning; sequential composition
# ---------------------------------------------------------------------------

def foreign_writer(world, target, attr, name=u"foreign"):
    clip = FB.Clip(world, world.new_handle(), "DmeChannelsClip", "Other", offset=0, start=0, end=10 ** 7,
                   channels=FB.ElementArray(world, []))
    track = world.shot.attrs["trackGroups"].items[0].attrs["tracks"].items[0]
    track.attrs["children"].items.append(clip)
    layer = FB.Layer(world, world.new_handle(), "DmeQuaternionLogLayer", [[0, [0.0, 0.0, 0.0, 1.0]]], "quat")
    log = FB.Log(world, world.new_handle(), "DmeQuaternionLog", layer)
    ch = FB.Channel(world, world.new_handle(), "DmeChannel", name, fromElement=None, fromAttribute=u"",
                    toElement=target, toAttribute=attr, mode=0, fromIndex=0, toIndex=0, log=log)
    clip.attrs["channels"].items.append(ch)
    return ch


def section_authority(ns, root, lib, grip):
    arm = arm_fixture()

    def fresh_world(prepare=None):
        w = FS.World(placed_destination(arm))
        if prepare is not None:
            prepare(w)
        use(ns, w, arm)
        return w
    w = fresh_world(lambda w: foreign_writer(w, w.bone_dag[u"finger2"].attrs["transform"], u"orientation"))
    refused("J.competing_writer_refuses", outcome(lambda: apply(ns, reload(ns, lib, grip))), u"shared-authority")
    check("J.competing_writer_refusal_writes_nothing", not writes(w))

    def shared_layer(w):
        ch = foreign_writer(w, FB.Element(w, w.new_handle(), "DmeTransform", "other"), u"orientation")
        ch.attrs["log"] = w.channels[u"finger1_o"].attrs["log"]
    w = fresh_world(shared_layer)
    refused("J.shared_log_refuses", outcome(lambda: apply(ns, reload(ns, lib, grip))), u"shared-authority")

    def external_constraint(w):
        op = FB.Element(w, w.new_handle(), "DmeRigOrientConstraintOperator", "external",
                        slave=FB.Element(w, w.new_handle(), "DmeConstraintSlave", "s", target=w.bone_dag[u"finger3"]),
                        targets=FB.ElementArray(w, [FB.Element(w, w.new_handle(), "DmeConstraintTarget", "t",
                                                               target=w.bone_dag[u"leg"], targetWeight=1.0)]))
        w.shot.attrs["operators"].items.append(op)
    w = fresh_world(external_constraint)
    got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
    check("J.external_constraint_on_an_affected_bone_refuses_naming_it", got[0] != "ok" and got[1] in (
        u"unsupported-selection", u"shared-authority") and u"finger3" in got[2] and not writes(w), got)

    def unknown_operator(w):
        w.shot.attrs["operators"].items.append(FB.Element(w, w.new_handle(), "DmeUnknownSolverOperator", "mystery"))
    w = fresh_world(unknown_operator)
    refused("J.unresolved_operator_in_the_document_refuses", outcome(lambda: apply(ns, reload(ns, lib, grip))))
    check("J.unresolved_operator_refusal_writes_nothing", not writes(w))
    w = fresh_world(lambda w: foreign_writer(w, FB.Element(w, w.new_handle(), "DmeTransform", "unrelated"),
                                             u"orientation"))
    result, verdict = apply(ns, reload(ns, lib, grip))
    check("J.proven_unrelated_writers_do_not_refuse", verdict == {u"phase": u"committed-verified"}, verdict)
    # Conflicts introduced at P2 and at P7.
    w = fresh_world()
    real = ns["prod_scope_preflight"]

    def preflight_then_foreign(*args):
        pre = real(*args)
        foreign_writer(w, w.bone_dag[u"finger1"].attrs["transform"], u"orientation", u"late")
        return pre
    ns["prod_scope_preflight"] = preflight_then_foreign
    try:
        refused("J.writer_introduced_at_P2_refuses", outcome(lambda: apply(ns, reload(ns, lib, grip))), u"stale")
    finally:
        ns["prod_scope_preflight"] = real
    check("J.P2_refusal_writes_nothing", not writes(w))
    w = fresh_world()
    item = reload(ns, lib, grip)
    auth = authorize(ns, u"Apply Pose", item)
    result = ns["prod_scope_apply"](Pin.identity, auth, item, {})
    foreign_writer(w, w.bone_dag[u"finger1"].attrs["transform"], u"orientation", u"late")
    verdict = ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
    check("J.writer_introduced_before_P7_prevents_verified_success", verdict[u"phase"] == u"committed-unverified",
          verdict)
    # Key planning: insert, update, exact keys, missing-key non-no-op, quaternion sign safeguard.
    w = fresh_world()
    before = dict((n, w.keys(n)) for n in w.channels)
    result, verdict = apply(ns, reload(ns, lib, grip))
    inserted = [c for c in writes(w) if c[0] == "InsertKeyAtTime"]
    check("K.missing_keys_are_inserted_at_the_mapped_tick", len(inserted) == 8 and all(c[2] == 50000
                                                                                         for c in inserted), inserted)
    check("K.neighbouring_keys_and_unrelated_channels_untouched",
          all(w.keys(n)[0] == before[n][0] for n in w.channels))
    calls = len(w.calls)
    again, _ = apply(ns, reload(ns, lib, grip))
    check("K.verified_repeat_is_a_true_noop", again == {u"phase": u"no-op"} and len(w.calls) == calls, again)
    w.dm.Undo()
    check("K.undo_restores_the_exact_baseline", dict((n, w.keys(n)) for n in w.channels) == before)
    w.dm.Redo()
    turn(w, u"finger2_o", [0, 0, 1], 5)          # an existing key at t with another value: update, not insert
    w.evaluate()
    n0 = len(w.calls)
    result, verdict = apply(ns, reload(ns, lib, grip))
    updated = [c for c in w.calls[n0:] if c[0] == "SetKeyValue"]
    finger2_layer = w.channels[u"finger2_o"].attrs["log"].layer.h
    check("K.existing_key_at_t_is_updated_in_place", verdict == {u"phase": u"committed-verified"} and
          len([c for c in w.calls[n0:] if c[0] == "InsertKeyAtTime"]) == 0 and
          [c[1] for c in updated] == [finger2_layer], updated)
    # Visually matching but missing a key: an insertion, never a no-op.
    w = fresh_world()
    src_fx = posed_source(arm)
    for n in FINGERS:
        FS.rekey(w, n + u"_o", src_fx[u"channels"][n + u"_o"]["keys"][0][1])
    w.evaluate()
    result, verdict = apply(ns, reload(ns, lib, grip))
    check("K.visible_match_with_missing_keys_is_not_a_noop", result[u"phase"] == u"verification-pending" and
          len([c for c in writes(w) if c[0] == "InsertKeyAtTime"]) == 8, result.get(u"phase"))
    w = fresh_world()
    layer = w.channels[u"finger1_o"].attrs["log"].layer
    q = FB.plain(layer.keys[0][1])
    layer.keys.append([90000, FB.native([-c for c in q], "quat")])
    w.evaluate()
    refused("K.neighbours_straddling_a_quaternion_sign_flip_refuse", outcome(lambda: apply(ns, reload(ns, lib, grip))),
            u"structure-unsupported")


def section_sequential(ns, root, full_lib, full, grip_lib, grip):
    arm = arm_fixture()
    spread = posed_source(arm)                       # a finger pose different from the full-body pose's fingers
    for n, deg in ((u"finger1", -30), (u"finger2", -45), (u"finger3", -20), (u"thumb1", 25)):
        FS.set_key(spread, n + u"_o", rotate(spread[u"channels"][n + u"_o"]["keys"][0][1], [0, 1, 0], deg))
    use(ns, FS.World(spread), arm)
    grip = save(ns, grip_lib, ns["prod_scope_request"](u"selected_parts", FINGERS), u"Spread",
                u"20261108-160000-000000")
    w = FS.World(placed_destination(arm))
    use(ns, w, arm)
    baseline = all_keys(w)
    r1, v1 = apply(ns, reload(ns, full_lib, full))
    after_body = all_keys(w)
    r2, v2 = apply(ns, reload(ns, grip_lib, grip))
    after_fingers = all_keys(w)
    check("S.full_body_then_finger_pose_both_verify", v1 == {u"phase": u"committed-verified"} and
          v2 == {u"phase": u"committed-verified"}, (v1, v2))
    check("S.second_pose_changes_only_its_declared_inputs", changed_channels(after_body, after_fingers) ==
          sorted(n + u"_o" for n in FINGERS) or set(changed_channels(after_body, after_fingers)) <=
          set(n + s for n in FINGERS for s in (u"_o", u"_p")), changed_channels(after_body, after_fingers))
    check("S.each_operation_has_its_own_undo_entry", [e["label"] for e in w.dm.stack] ==
          [u"Apply Pose Crouch", u"Apply Pose Spread"], [e["label"] for e in w.dm.stack])
    w.dm.Undo()
    check("S.undo_returns_through_the_first_exact_baseline", all_keys(w) == after_body)
    w.dm.Undo()
    check("S.undo_returns_to_the_original_baseline", all_keys(w) == baseline)
    w.dm.Redo()
    w.dm.Redo()
    check("S.redo_reapplies_both", all_keys(w) == after_fingers)
    again, _ = apply(ns, reload(ns, grip_lib, grip))
    check("S.repeat_after_composition_is_a_noop", again == {u"phase": u"no-op"}, again)


# ---------------------------------------------------------------------------
# L. transactions through the real lifecycle (R3 8)
# ---------------------------------------------------------------------------

def section_transactions(ns, app, root, lib, grip):
    arm = arm_fixture()

    def world(**flags):
        w = FS.World(placed_destination(arm))
        for k, v in flags.items():
            setattr(w, k, v)
        use(ns, w, arm)
        return w
    w = world(undo_enabled=False)
    refused("L.disabled_undo_refuses_before_any_write", outcome(lambda: apply(ns, reload(ns, lib, grip))),
            u"evidence-unreadable")
    check("L.disabled_undo_writes_nothing", not writes(w) and not w.dm.calls)
    for mode in (u"before", u"after"):
        w = world(start_raises=mode)
        got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
        check("L.start_undo_failure_%s_is_recovery_unverified_without_writes" % mode,
              got[0] == "ProdRecoveryUnverifiedError" and not writes(w) and
              "AbortUndoableOperation" not in [c[0] for c in w.dm.calls], got)
    w = world(fail_on_write=u"finger2_o")
    before = all_keys(w)
    got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
    check("L.late_write_failure_aborts_and_verifies_the_original_baseline", got[0] == "ok" and
          got[1][0][u"phase"] == u"not-applied" and all_keys(w) == before and
          [c[0] for c in w.dm.calls] == ["StartUndo", "AbortUndoableOperation"], got)
    w = world(fail_on_write=u"finger2_o", abort_raises=True)
    got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
    check("L.failed_abort_is_recovery_unverified", got[0] == "ProdRecoveryUnverifiedError", got)
    w = world()
    w.dm.push_foreign(u"Apply Pose Grip")              # an older identical history label
    w.finish_raises = True
    got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
    check("L.finish_undo_uncertainty_never_claims_commitment_or_undoes", got[0] == "ProdRecoveryUnverifiedError" and
          "Undo" not in [c[0] for c in w.dm.calls] and "AbortUndoableOperation" not in [c[0] for c in w.dm.calls],
          got)
    w = world()
    item = reload(ns, lib, grip)
    auth = authorize(ns, u"Apply Pose", item)
    result = ns["prod_scope_apply"](Pin.identity, auth, item, {})
    Pin.valid[0] = False
    verdict = ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
    check("L.stale_deferred_callback_is_committed_unverified", verdict[u"phase"] == u"committed-unverified", verdict)
    Pin.valid[0] = True
    w = world()
    item = reload(ns, lib, grip)
    auth = authorize(ns, u"Apply Pose", item)
    result = ns["prod_scope_apply"](Pin.identity, auth, item, {})
    check("L.one_refresh_outside_the_transaction", [r["in_undo"] for r in w.refresh_calls] == [False])
    w.dm.push_foreign(u"Something else")
    verdict = ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
    check("L.after_commit_uncertainty_is_reported_without_automatic_undo",
          verdict[u"phase"] == u"committed-unverified" and "Undo" not in [c[0] for c in w.dm.calls], verdict)
    w = world()
    Pin.valid[0] = False
    got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
    Pin.valid[0] = True
    check("L.deleted_or_replaced_instance_fails_before_writes", got[0] != "ok" and not writes(w), got)
    w = world()
    item = reload(ns, lib, grip)
    stale = dict(item, revision=u"0" * 64)
    auth = authorize(ns, u"Apply Pose", stale)
    turn(w, u"finger1_o", [0, 0, 1], 1)
    w.evaluate()
    got = outcome(lambda: ns["prod_scope_apply"](Pin.identity, auth, stale, {}))
    refused("L.stale_record_revision_fails_before_writes", got, u"record-changed")
    check("L.stale_record_writes_nothing", not writes(w))


# ---------------------------------------------------------------------------
# M/N. the real ProdWindow lifecycle, UI state and dispatch (R3 6.1, 7, 11 "UI/library", "Dispatch")
# ---------------------------------------------------------------------------

WINDOW_METHODS = ["pose_registry_mode", "pose_guard", "apply_pose", "save_pose", "update_pose"]


class FakeWindow(object):
    """The ProdWindow seams the pose methods call; the methods themselves are the real ones."""

    def __init__(self, ns):
        self.ns = ns
        self.identity = dict(Pin.identity)
        self.operation = {"context": context(ns), "operation_id": 1, "generation": 1}
        self.statuses, self.pending, self.prompts, self.scopes, self.confirm = [], [], [], [], True
        self.pose_recovery_blocked = False
        self.inventories = []

    def guard(self, label, fn):
        try:
            return fn()
        except Exception as exc:
            self.statuses.append(("error", label, getattr(exc, "code", None), _TEXT(exc)))
            return None

    def current(self):
        return self.identity

    def prompt(self, title, default):
        return self.prompts.pop(0) if self.prompts else None

    def prompt_pose_scope(self, inventory, body_route):
        self.inventories.append((inventory, body_route))
        if not self.scopes:
            return None
        choice = self.scopes.pop(0)
        if callable(choice):
            choice = choice(inventory)
        state = self.ns["prod_scope_dialog_state"](inventory, choice)
        if choice[u"kind"] == u"full_body" and body_route:
            return {u"name": choice[u"name"], u"kind": u"full_body", u"request": None}
        if not state[u"save_enabled"]:
            return None
        return {u"name": choice[u"name"], u"kind": choice[u"kind"], u"request": state[u"request"]}

    def operation_revalidate(self):
        pass

    def operation_mark_phase(self, phase, detail=None):
        pass

    def set_status(self, text, kind=None):
        self.statuses.append(("status", text, kind))

    def refresh_pose_view(self, select_id=None):
        pass

    def pose_begin_verification(self, label, pending):
        self.pending.append(pending)

    def confirm_pose_update(self, name, parts):
        return self.confirm


def window(app, ns, reg, lib):
    methods = {}
    for name in WINDOW_METHODS:
        route._run_source(app.method_text("ProdWindow", name), "ProdWindow.%s" % name, ns, methods)
    for name, fn in methods.items():
        setattr(FakeWindow, name, fn)
    ns["prod_pose_load_registry"] = lambda path=None: reg
    ns["prod_pose_selected_library"] = lambda ident: lib
    ns["prod_log_outcome"] = lambda *a, **k: None
    ns["p03_now_stamp"] = lambda: u"20261108-150000-000000"
    ns["tool_status_name"] = lambda n: n
    return FakeWindow(ns)


def section_window(app, ns, fx, root):
    reg = body.registries(ns)[0]
    heavy = fx[u"mc01"]
    src = FS.World(heavy)
    use(ns, src, heavy)
    lib = library(root, u"heavy")
    win = window(app, ns, reg, lib)
    mode = ns["PROD_POSE_REGISTRY_MODE"]
    check("N.shipped_build_is_production_with_scoped_rules_experimental", mode == u"production" and
          ns["PROD_SCOPE_RULES"] == {u"direct_fk_v1": {u"revision": 1, u"status": u"experimental"}} and
          ns["PROD_SCOPE_CARRIED_ENABLED"] == [False] and ns["PROD_SCOPE_EXTRAPOLATION_QUALIFIED"] == [False])
    win.prompts = [u"Heavy Pose"]
    got = win.save_pose(None, (u"full_body",))
    check("N.production_save_new_for_a_non_registry_character_is_unchanged",
          got is None and not win.inventories and win.statuses[-1][2] == u"not-qualified" and
          not os.path.isdir(os.path.join(lib[u"char_dir"], u"Poses")), win.statuses[-1])
    refused("N.production_authorization_refuses_the_experimental_rule", outcome(lambda: authorize(
        ns, u"Save Pose", mode=u"production")), u"not-qualified")
    ns["PROD_POSE_REGISTRY_MODE"] = u"qualification"
    try:
        left = lambda inv: {u"name": u"Heavy grip", u"kind": u"selected_parts", u"bones": [
            b for r in inv[u"view"] if r[u"path"][-1] == u"LeftFingers" for b in r[u"bones"]]}
        win.scopes = [left]
        saved = win.save_pose(None, (u"full_body",))
        check("N.save_new_dialog_reaches_the_v3_route_without_a_registry_entry",
              saved is not None and saved[u"record"][u"pose"][u"version"] == 3 and
              win.statuses[-1][1] == u"Pose saved: Heavy grip." and not writes(src) and not src.dm.calls,
              win.statuses[-1])
        check("N.dialog_received_the_full_body_coverage_and_the_picker",
              win.inventories[-1][0][u"full_body"][u"code"] == u"carried-unsupported" and
              win.inventories[-1][1] is False)
        win.scopes = [{u"name": u"Heavy body", u"kind": u"full_body"}]
        none = win.save_pose(None, (u"full_body",))
        names = [i[u"name"] for i in ns["prod_pose_discover"](lib[u"char_dir"], lib[u"character_key"], reg)[u"items"]]
        check("N.unsupported_full_body_offers_no_silent_fallback", none is None and u"Heavy body" not in names and
              win.inventories[-1][0][u"full_body"][u"status"] == u"refused", names)
        got = win.save_pose(u"Heavy body", (u"full_body",), scope=ns["prod_scope_request"](u"full_body"))
        check("N.a_direct_unsupported_full_body_request_is_refused_with_its_reason", got is None and
              win.statuses[-1][2] == u"carried-unsupported", win.statuses[-1])
        dst = FS.World(heavy)
        turn(dst, u"bip_hand_L_o", [1, 0, 0], 40)
        turn(dst, u"bip_index_1_L_o", [0, 0, 1], -30)
        dst.evaluate()
        use(ns, dst, heavy)
        win.operation["context"] = context(ns)
        item = ns["prod_pose_reread"](lib, saved, reg)
        calls = {}
        real = dict((k, ns[k]) for k in (u"prod_scope_apply", u"prod_body_apply", u"prod_pose_apply"))
        win.apply_pose(item)
        check("N.apply_pose_dispatches_v3_through_the_real_lifecycle", len(win.pending) == 1 and
              win.pending[0].get(u"scoped") and [c[0] for c in dst.dm.calls] == ["StartUndo", "FinishUndo"],
              win.statuses[-1:])
        verdict = ns["prod_pose_deferred_verify"](win.pending[0])
        check("N.deferred_turn_verifies_the_scoped_pose", verdict == {u"phase": u"committed-verified"}, verdict)
        check("N.status_parts_phrase_names_selected_parts",
              ns["prod_pose_parts_phrase"](win.pending[0][u"regions"]) == u"Selected parts")
        # Update Pose keeps the record's scope.
        use(ns, src, heavy)
        win.operation["context"] = context(ns)
        turn(src, u"bip_index_2_L_o", [0, 0, 1], 12)
        src.evaluate()
        win.confirm = True
        updated = win.update_pose(ns["prod_pose_reread"](lib, saved, reg))
        check("N.update_pose_recaptures_the_scoped_pose_in_place", updated is not None and
              updated[u"preset_id"] == saved[u"preset_id"] and
              updated[u"record"][u"pose"][u"scope"] == saved[u"record"][u"pose"][u"scope"] and
              win.statuses[-1][1] == u"Pose updated: Heavy grip.", win.statuses[-1])
        # Dispatch on the pose payload version: v1 and v3 under the same envelope schema_version.
        spy = []
        for k in real:
            ns[k] = (lambda k: lambda *a, **kw: spy.append((k, a[2][u"record"][u"pose"][u"version"])) or {
                u"phase": u"no-op"})(k)
        try:
            win.apply_pose(ns["prod_pose_reread"](lib, updated, reg))
        finally:
            ns.update(real)
        check("N.envelope_v3_routes_by_payload_version", spy == [(u"prod_scope_apply", 3)], spy)
        refused("N.unknown_rule_record_refuses_at_authorization", outcome(lambda: ns["prod_scope_authorize"](
            context(ns), Pin.identity, {}, u"qualification", u"Apply Pose",
            {u"record": dict(updated[u"record"], pose=dict(updated[u"record"][u"pose"], engine={
                u"rule": u"direct_fk_v9", u"revision": 1, u"carried_rule": None})), u"revision": u"x"})),
            u"not-qualified")
        refused("N.v3_authorization_needs_no_krystal_registry_entry_but_keeps_context_gates", outcome(
            lambda: ns["prod_scope_authorize"](dict(context(ns), library_identity={u"model": u"other.mdl",
                                                                                    u"checksum": 1234}),
                                               Pin.identity, {}, u"qualification", u"Save Pose")), u"stale")
        # Recovery lockout is process-wide and blocks the next scoped operation.
        w = FS.World(heavy)
        w.fail_on_write, w.abort_raises = u"bip_index_0_L_o", True
        use(ns, w, heavy)
        win.operation["context"] = context(ns)
        win.apply_pose(ns["prod_pose_reread"](lib, updated, reg))
        blocked = ns["PROD_POSE_RECOVERY_BLOCK"][0]
        win.scopes = [left]
        again = win.save_pose(None, (u"full_body",))
        check("N.failed_recovery_locks_out_further_pose_operations", blocked == u"Apply Pose" and again is None and
              win.statuses[-1][2] == u"recovery-blocked", (blocked, win.statuses[-1]))
        ns["PROD_POSE_RECOVERY_BLOCK"][0] = None
        win.pose_recovery_blocked = False
        # Krystal (registry character) in the qualification build: Full body keeps the v2 route, Selected parts v3.
        k15 = fx[u"k15"]
        kw = FS.World(k15)
        use(ns, kw, k15)
        klib = library(root, u"krystal2020")
        kwin = window(app, ns, reg, klib)
        kwin.identity = dict(Pin.identity)
        kwin.scopes = [{u"name": u"Krystal body", u"kind": u"full_body"}]
        v2 = kwin.save_pose(None, (u"full_body",))
        check("N.krystal_full_body_keeps_its_version_2_route", v2 is not None and
              v2[u"record"][u"pose"][u"version"] == 2 and kwin.inventories[-1][1] is True, kwin.statuses[-1])
        kwin.scopes = [lambda inv: {u"name": u"Krystal hand", u"kind": u"selected_parts",
                                    u"bones": [u"bip_index_1_l", u"bip_index_2_l", u"bip_index_1_l"]}]
        v3 = kwin.save_pose(None, (u"full_body",))
        check("N.krystal_selected_parts_use_v3_and_duplicates_are_deduplicated", v3 is not None and
              v3[u"record"][u"pose"][u"version"] == 3 and
              v3[u"record"][u"pose"][u"scope"][u"posed"] == [u"bip_index_1_l", u"bip_index_2_l"], kwin.statuses[-1])
        got = kwin.save_pose(u"Bad", (u"full_body",), scope=ns["prod_scope_request"](
            u"selected_parts", [u"bip_index_1_l", u"bip_hand_l"]))
        check("N.unsupported_selection_is_refused_not_dropped", got is None and
              kwin.statuses[-1][2] == u"unsupported-selection" and u"bip_hand_l" in kwin.statuses[-1][3],
              kwin.statuses[-1])
        state = ns["prod_scope_dialog_state"](kwin.inventories[-1][0], {u"kind": u"selected_parts",
                                                                         u"bones": [u"bip_hand_l"]})
        check("N.unsupported_selection_names_the_control", not state[u"save_enabled"] and
              u"bip_hand_l" in state[u"summary"], state)
        # Group membership changing during the dialog: the pinned inventory no longer matches.

        def regroup(inv):
            kw.animset.set("rootControlGroup", FB.Element(kw, kw.new_handle(), "DmeControlGroup", "new",
                                                          children=FB.ElementArray(kw, []),
                                                          controls=FB.ElementArray(kw, [])))
            return {u"name": u"Changed", u"kind": u"selected_parts", u"bones": [u"bip_index_1_l"]}
        kwin.scopes = [regroup]
        got = kwin.save_pose(None, (u"full_body",))
        check("N.group_membership_change_during_the_dialog_is_stale", got is None and
              kwin.statuses[-1][2] == u"stale", kwin.statuses[-1])
        legacy = ns["prod_pose_save_new"](klib, u"Legacy Arm", body.legacy_pose(ns), u"20261108-180000-000000", reg)
        use(ns, FS.World(k15), k15)
        kwin.operation["context"] = context(ns)
        spy = []
        real = dict((k, ns[k]) for k in (u"prod_scope_apply", u"prod_body_apply", u"prod_pose_apply"))
        for k in real:
            ns[k] = (lambda k: lambda *a, **kw: spy.append((k, a[2][u"record"][u"pose"][u"version"])) or {
                u"phase": u"no-op"})(k)
        try:
            for rec in (legacy, v2, v3):
                kwin.apply_pose(ns["prod_pose_reread"](klib, rec, reg))
        finally:
            ns.update(real)
        check("N.one_envelope_three_payload_versions_three_routes", spy == [
            (u"prod_pose_apply", 1), (u"prod_body_apply", 2), (u"prod_scope_apply", 3)], spy)
        check("N.no_current_selection_api_is_used", not any(hasattr(ns["sfmApp"], n) and n in (
            "GetSelection", "GetSelectedControls") for n in dir(ns["sfmApp"])))
    finally:
        ns["PROD_POSE_REGISTRY_MODE"] = mode
        ns["PROD_POSE_RECOVERY_BLOCK"][0] = None


def section_ui_state(ns):
    sel = {u"name": u"Grip", u"own": True, u"origin": u"heavy1", u"saved": [u"selected_parts"],
           u"availability": {u"selected_parts": u"available"}, u"unusable": False, u"favorite": False}
    st = ns["prod_pose_ui_state"]({u"character": u"heavy1", u"supported": True, u"instance_valid": True,
                                   u"visible_count": 1, u"selected": sel})
    check("M.ui_state_applies_a_v3_selected_parts_pose_directly",
          st[u"buttons"][u"apply_pose"] and st[u"apply_mode"] == u"direct" and
          st[u"summary"][0].endswith(u"Saved: Selected parts · Available: Selected parts"), st[u"summary"])
    sel2 = dict(sel, availability={u"selected_parts": u"not-qualified"})
    st = ns["prod_pose_ui_state"]({u"character": u"heavy1", u"supported": True, u"instance_valid": True,
                                   u"visible_count": 1, u"selected": sel2})
    check("M.unavailable_v3_pose_cannot_be_applied", not st[u"buttons"][u"apply_pose"])
    record = {u"pose": {u"version": 3, u"engine": {u"rule": u"direct_fk_v1", u"revision": 1},
                        u"source": {u"model_key": u"models/player/heavy.mdl"},
                        u"scope": {u"kind": u"selected_parts"}}}
    check("M.availability_needs_the_rule_in_this_build_and_the_same_model",
          ns["prod_scope_availability"](record, {"model": u"models/player/heavy.mdl"}, u"qualification") ==
          u"available" and ns["prod_scope_availability"](record, {"model": u"models/player/heavy.mdl"},
                                                         u"production") == u"not-qualified" and
          ns["prod_scope_availability"](record, {"model": u"models/other.mdl"}, u"qualification") ==
          u"different-model")
    check("M.legacy_regions_are_not_required_by_v3", ns["prod_scope_parts"](record) == [u"selected_parts"])
    check("M.legacy_parts_unchanged", ns["prod_scope_parts"]({u"pose": {u"version": 1, u"regions": {
        u"left_arm": {}}}}) == [u"left_arm"] and ns["prod_pose_parts_phrase"]([u"left_arm"]) == u"Left arm")


def section_dialog_copy(ns, fx):
    heavy = fx[u"mc01"]
    use(ns, FS.World(heavy), heavy)
    inv = inventory(ns)
    left = [b for r in inv[u"view"] if r[u"path"][-1] == u"LeftFingers" for b in r[u"bones"]]
    state = ns["prod_scope_dialog_state"](inv, {u"kind": u"selected_parts", u"bones": left})
    check("M.an_ordinary_finger_selection_needs_no_explanation", state[u"save_enabled"] and
          state[u"summary"] == u"", state[u"summary"])
    state = ns["prod_scope_dialog_state"](inv, {u"kind": u"selected_parts", u"bones": []})
    check("M.empty_selection_cannot_be_saved", not state[u"save_enabled"] and
          state[u"summary"] == u"Select at least one body control.")
    state = ns["prod_scope_dialog_state"](inv, {u"kind": u"full_body"})
    check("M.unsupported_full_body_explains_and_points_to_selected_parts", not state[u"save_enabled"] and
          u"Choose Selected parts" in state[u"summary"], state[u"summary"])
    state = ns["prod_scope_dialog_state"](inv, {u"kind": u"selected_parts", u"bones": [u"bip_pelvis"]})
    check("M.selected_root_discloses_articulation_only", state[u"save_enabled"] and
          u"The body root keeps its position." in state[u"summary"], state[u"summary"])
    for text in [ns["PROD_SCOPE_MESSAGES"][k] for k in ns["PROD_SCOPE_MESSAGES"]] + [state[u"summary"]]:
        if u"..." in text or u"…" in text:
            check("M.no_ellipses_in_copy", False, text)
            break
    else:
        check("M.no_ellipses_in_copy", True)


# ---------------------------------------------------------------------------
# E. scope semantics, selection and library protections for version 3 records
# ---------------------------------------------------------------------------

def section_semantics(ns, app, fx, root, lib, grip):
    arm = arm_fixture()
    # A renamed group does not redefine a saved scope; Apply ignores groups entirely.
    renamed = placed_destination(arm)
    for g in renamed[u"groups"]:
        if g[u"path"][-1] == u"Fingers":
            g[u"path"] = [u"unnamed", u"Hand details"]
    w = FS.World(renamed)
    use(ns, w, arm)
    result, verdict = apply(ns, reload(ns, lib, grip))
    check("E.stable_scope_survives_group_renaming", verdict == {u"phase": u"committed-verified"}, verdict)
    # A changed binding (a finger now rig-driven) invalidates the saved scope with no write.
    rebound = face_solver(placed_destination(arm))
    rebound[u"operators"][0][u"slaves"][u"slave"][u"target"] = rebound[u"bones"][u"finger2"][u"handle"]
    for suffix in (u"_p", u"_o"):
        rebound[u"channels"][u"jaw" + suffix]["to"] = {u"handle": rebound[u"bones"][u"jaw"][u"transform"],
                                                        u"type": u"DmeTransform", u"name": u"bone 3 (jaw)"}
    w = FS.World(rebound)
    use(ns, w, arm)
    got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
    check("E.relevant_binding_change_invalidates_the_scope", got[0] != "ok" and u"finger2" in got[2] and
          not writes(w), got)
    # Ambiguous bindings: two scene elements for one bone name refuse before anything is read further.
    dup = FS.World(placed_destination(arm))
    extra = FB.Dag(dup, dup.new_handle(), "DmeDag", u"finger1", dup.bone_dag[u"finger1"].attrs["transform"])
    dup.scene.add(extra)
    use(ns, dup, arm)
    refused("E.ambiguous_bone_bindings_refuse", outcome(lambda: apply(ns, reload(ns, lib, grip))),
            u"structure-unsupported")
    check("E.ambiguous_bindings_write_nothing", not writes(dup))
    # Foreign-library and damaged-file protections hold for version 3 records.
    use(ns, FS.World(posed_source(arm)), arm)
    other = dict(lib, character_key=u"someone_else")
    refused("E.foreign_v3_record_cannot_be_updated", outcome(lambda: ns["prod_pose_update"](
        other, reload(ns, lib, grip), capture(ns, ns["prod_scope_request"](u"selected_parts", FINGERS)),
        u"20261108-170000-000000", {})), u"foreign-locked")
    item = reload(ns, lib, grip)
    damaged = item[u"path"][:-5] + u"-2.json"
    with io.open(item[u"path"], "rb") as f:
        raw = f.read()
    with io.open(damaged, "wb") as f:
        f.write(raw.replace(b'"Grip"', b'"Grip", "extra": 1', 1))
    found = ns["prod_pose_discover"](lib[u"char_dir"], lib[u"character_key"], {})
    check("E.damaged_v3_file_is_listed_unusable_never_applied",
          any(u["path"] == damaged and u["reason"] == u"invalid-file" for u in found[u"unusable"]) and
          any(i[u"preset_id"] == grip[u"preset_id"] for i in found[u"items"]), found[u"unusable"])
    os.remove(damaged)
    info = ns["prod_scope_info"](item[u"record"])
    check("E.pose_info_lists_the_scope_and_its_rule", info[u"rows"][0] == (u"Includes:", u"Fingers")
          and info[u"engine"] == u"direct_fk_v1 revision 1" and sorted(info[u"bones"]) == sorted(FINGERS), info)


def section_rigged_heavy(ns, fx, root):
    heavy = fx[u"mc02"]
    src = FS.World(heavy)
    turn(src, u"bip_index_1_R_o", [0, 0, 1], 35)
    turn(src, u"bip_thumb_1_R_o", [0, 1, 0], -20)
    src.evaluate()
    use(ns, src, heavy)
    inv = inventory(ns)
    right = [b for r in inv[u"view"] if r[u"path"][-1] == u"RightFingers" for b in r[u"bones"]]
    lib = library(root, u"heavy_rig")
    grip = save(ns, lib, ns["prod_scope_request"](u"selected_parts", right), u"Rig grip")
    dst = FS.World(heavy)
    for name in heavy[u"channels"]:
        if name.startswith(u"rig_root") or name.startswith(u"rig_hand_R"):
            ch = heavy[u"channels"][name]
            if ch[u"log_type"] == u"DmeQuaternionLog":
                turn(dst, name, [0, 0, 1], 25)
            elif ch[u"log_type"] == u"DmeVector3Log":
                move(dst, name, [3.0, -2.0, 1.0])
    dst.evaluate()
    use(ns, dst, heavy)
    before = all_keys(dst)
    result, verdict = apply(ns, reload(ns, lib, grip))
    check("R.rigged_heavy_fingers_apply_under_a_moved_rig_hand", verdict == {u"phase": u"committed-verified"},
          (result.get(u"phase"), verdict))
    check("R.rigged_heavy_rig_inputs_unchanged", all(all_keys(dst)[n] == before[n] for n in before
                                                     if n.startswith(u"rig_")))


# ---------------------------------------------------------------------------
# AX. Astra implementation review (abe58bb), ACCEPT WITH CORRECTIONS: the three P1 counterexamples and their closure
# ---------------------------------------------------------------------------

MISSING, UNREADABLE = object(), object()


class Opaque(object):
    """A native value with no lossless form (an unreadable index read)."""


def set_index(world, channel, field, value):
    ch = world.channels[channel]
    if value is MISSING:
        del ch.attrs[field]
        ch.order.remove(field)
    else:
        ch.set(field, Opaque() if value is UNREADABLE else value)


def native_zero():
    try:
        return long(0)  # noqa: F821  (Python 2: the native integer type SFM's bindings may return)
    except NameError:
        return 0


def follower_fixture(fx, slave_bone, target_bone, op_type, vec=None, handle=910000):
    """A constraint inside the animation set reading target_bone and slaving slave_bone (its control channels drive
    the constraint slave, as a rig's do). A point constraint with a vector offset swings the slave far away when the
    target turns."""
    fx = FS.clone(fx)
    slave = handle + 1
    fx[u"operators"].append({
        u"handle": handle, u"type": op_type, u"name": u"follow_%s" % target_bone, u"owners": [u"animation_set"],
        u"slaves": {u"slave": {u"slave": slave, u"target": fx[u"bones"][slave_bone][u"handle"]}},
        u"targets": [{u"handle": handle + 2, u"target": fx[u"bones"][target_bone][u"handle"],
                      u"weight": {u"status": u"READ", u"value": 1.0}, u"oOffset": {u"status": u"ABSENT"},
                      u"vecOffset": {u"status": u"READ", u"value": list(vec)} if vec else {u"status": u"ABSENT"}}],
        u"pole": None, u"solver": {}})
    for suffix in (u"_p", u"_o"):
        fx[u"channels"][slave_bone + suffix]["to"] = {u"handle": slave, u"type": u"DmeConstraintSlave", u"name": u"s"}
    return fx


def add_live_follower(w, slave_bone, target_bone, vec=(100.0, 0.0, 0.0)):
    """The same relationship introduced into a built World (between phases); the fake evaluator solves it."""
    el = FB.Element(w, w.new_handle(), "DmeRigPointConstraintOperator", "late_follow",
                    slave=FB.Element(w, w.new_handle(), "DmeConstraintSlave", "s", target=w.bone_dag[slave_bone]),
                    targets=FB.ElementArray(w, [FB.Element(w, w.new_handle(), "DmeConstraintTarget", "t",
                                                           target=w.bone_dag[target_bone], targetWeight=1.0,
                                                           vecOffset=FB.Vector(*vec))]))
    w.animset.attrs["operators"].items.append(el)
    w.ops.append(({u"type": u"DmeRigPointConstraintOperator",
                   u"slaves": {u"slave": {u"slave": el.attrs["slave"].h, u"target": w.bone_dag[slave_bone].h}}}, el))
    w.evaluate()


def flat_head_spec():
    """The analytic arm with the head at the spine's own frame: a jaw re-parented from the head to the spine keeps
    both its local and its world transform (Astra's reparenting counterexample)."""
    return [(n, p, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], s) if n == u"head" else (n, p, lp, lq, s)
            for (n, p, lp, lq, s) in arm_spec()]


def dag_parent(w, dag):
    for d in [w.gm] + list(w.bone_dag.values()):
        if dag in d.attrs["children"].items:
            return d
    return None


def reparent(w, bone, new_parent, keep_old=False):
    dag = w.bone_dag[bone]
    old = dag_parent(w, dag)
    if old is not None and not keep_old:
        old.attrs["children"].items.remove(dag)
    if new_parent is not None:
        w.bone_dag[new_parent].add(dag)
    w.evaluate()


def section_corrections(ns, app, root, lib, grip):
    arm = arm_fixture()

    def dst_world(prepare=None, fx=None):
        w = FS.World(fx or placed_destination(arm))
        if prepare is not None:
            prepare(w)
            w.evaluate()
        use(ns, w, arm)
        return w

    def p7(w, between_commit_and_p7, item=None):
        item = item or reload(ns, lib, grip)
        auth = authorize(ns, u"Apply Pose", item)
        result = ns["prod_scope_apply"](Pin.identity, auth, item, {})
        if result.get(u"phase") != u"verification-pending":
            return result, None
        between_commit_and_p7()
        return result, ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))

    def at_p2(w, change, item_lib=None, item_rec=None):
        real = ns["prod_scope_preflight"]

        def preflight_then(*args):
            pre = real(*args)
            change()
            return pre
        ns["prod_scope_preflight"] = preflight_then
        try:
            return outcome(lambda: apply(ns, reload(ns, item_lib or lib, item_rec or grip)))
        finally:
            ns["prod_scope_preflight"] = real

    # --- AX1: unsupported channel endpoint indices (supported contract: a readable native integer 0) ---------------
    cases = ((u"nonzero_from_index", u"finger1_o", "fromIndex", 1), (u"nonzero_to_index", u"finger1_o", "toIndex", 2),
             (u"negative_index", u"finger2_p", "toIndex", -1), (u"missing_index", u"finger2_o", "toIndex", MISSING),
             (u"unreadable_index", u"finger3_p", "fromIndex", UNREADABLE),
             (u"float_typed_index", u"finger3_o", "toIndex", 0.0), (u"bool_typed_index", u"thumb1_o", "fromIndex", False),
             (u"text_typed_index", u"finger1_p", "fromIndex", u"0"))
    for label, channel, field, value in cases:
        w = dst_world(lambda w: set_index(w, channel, field, value))
        got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
        check("AX1.%s_on_a_written_channel_refuses_at_P1" % label, got[0] != "ok" and
              got[1] == u"unsupported-selection" and channel.rsplit(u"_", 1)[0] in got[2], got)
        check("AX1.%s_refusal_writes_nothing_and_opens_no_undo" % label, not writes(w) and not w.dm.calls,
              w.dm.calls)
    w = dst_world(lambda w: set_index(w, u"finger2_o", "toIndex", native_zero()))
    result, verdict = apply(ns, reload(ns, lib, grip))
    check("AX1.a_native_integer_zero_of_any_supported_type_is_accepted", verdict == {u"phase": u"committed-verified"},
          (result.get(u"phase"), verdict))
    src = FS.World(posed_source(arm))
    set_index(src, u"finger1_o", "toIndex", 3)
    use(ns, src, arm)
    refused("AX1.save_refuses_an_unsupported_index_before_publication", outcome(
        lambda: capture(ns, ns["prod_scope_request"](u"selected_parts", FINGERS))), u"unsupported-selection")
    src = FS.World(arm)
    set_index(src, u"tail_o", "fromIndex", 1)
    use(ns, src, arm)
    inv = inventory(ns)
    check("AX1.full_body_refuses_an_unsupported_index_anywhere_in_the_body", inv[u"full_body"][u"status"] ==
          u"refused" and inv[u"full_body"][u"code"] == u"unsupported-body" and u"tail" in inv[u"full_body"][u"message"],
          inv[u"full_body"])
    check("AX1.classification_names_the_index_reason",
          ns["prod_scope_classify"](ns["prod_scope_state"](ns["prod_resolve_instance"](context(ns)["instance"]))[
              u"D"])[u"bones"][u"tail"][u"reason"] == u"unsupported channel index")
    w = dst_world()
    got = at_p2(w, lambda: set_index(w, u"finger1_o", "toIndex", 1))
    refused("AX1.index_changed_between_P1_and_P2_refuses", got, u"stale")
    check("AX1.P2_index_refusal_writes_nothing", not writes(w) and not w.dm.calls)
    w = dst_world()
    result, verdict = p7(w, lambda: set_index(w, u"finger1_o", "toIndex", 1))
    check("AX1.index_changed_before_P7_is_committed_unverified", verdict is not None and
          verdict[u"phase"] == u"committed-unverified", (result.get(u"phase"), verdict))
    bindings = outcome(lambda: ns["prod_scope_bindings"](ns["prod_scope_live"](
        ns["prod_resolve_instance"](context(ns)["instance"])), [u"finger1_o"]))
    refused("AX1.binding_revalidation_refuses_the_native_index", bindings, u"structure-unsupported")
    # The real ProdWindow Apply (qualification build): refused with its reason, nothing written.
    reg = body.registries(ns)[0]
    mode = ns["PROD_POSE_REGISTRY_MODE"]
    ns["PROD_POSE_REGISTRY_MODE"] = u"qualification"
    try:
        w = dst_world(lambda w: set_index(w, u"finger2_o", "toIndex", 1))
        win = window(app, ns, reg, lib)
        win.operation["context"] = context(ns)
        win.apply_pose(ns["prod_pose_reread"](lib, grip, reg))
        check("AX1.window_apply_refuses_through_the_real_lifecycle", not win.pending and not writes(w) and
              not w.dm.calls and win.statuses and win.statuses[-1][2] == u"unsupported-selection", win.statuses[-1:])
    finally:
        ns["PROD_POSE_REGISTRY_MODE"] = mode

    # --- AX2: constraint followers outside the scope ---------------------------------------------------------------
    far = follower_fixture(placed_destination(arm), u"tail", u"finger3", u"DmeRigPointConstraintOperator",
                           vec=[100.0, 0.0, 0.0])
    w = dst_world(fx=far)
    tail_before = list(w.bone_dag[u"tail"].wp)
    got = outcome(lambda: apply(ns, reload(ns, lib, grip)))
    moved = math.sqrt(sum((w.bone_dag[u"tail"].wp[i] - tail_before[i]) ** 2 for i in range(3)))
    check("AX2.astra_counterexample_a_follower_outside_the_selection_refuses_before_writing",
          got[0] != "ok" and got[1] == u"shared-input" and u"tail" in got[2], (got, moved))
    check("AX2.follower_refusal_writes_nothing_and_opens_no_undo", not writes(w) and not w.dm.calls and moved == 0.0,
          (w.dm.calls, moved))
    turned = follower_fixture(placed_destination(arm), u"leg", u"finger1", u"DmeRigOrientConstraintOperator")
    w = dst_world(fx=turned)
    refused("AX2.orientation_follower_refuses", outcome(lambda: apply(ns, reload(ns, lib, grip))), u"shared-input")
    check("AX2.orientation_follower_refusal_writes_nothing", not writes(w) and not w.dm.calls)
    src_fx = follower_fixture(posed_source(arm), u"tail", u"finger3", u"DmeRigPointConstraintOperator",
                              vec=[100.0, 0.0, 0.0])
    use(ns, FS.World(src_fx), arm)
    refused("AX2.save_refuses_a_scope_with_an_unverifiable_follower", outcome(
        lambda: capture(ns, ns["prod_scope_request"](u"selected_parts", FINGERS))), u"shared-input")
    w = dst_world()
    got = at_p2(w, lambda: add_live_follower(w, u"tail", u"finger3"))
    refused("AX2.follower_introduced_between_P1_and_P2_refuses", got, u"stale")
    check("AX2.P2_follower_refusal_writes_nothing", not writes(w) and not w.dm.calls)
    w = dst_world()
    result, verdict = p7(w, lambda: add_live_follower(w, u"tail", u"finger3"))
    check("AX2.follower_introduced_before_P7_is_committed_unverified", verdict is not None and
          verdict[u"phase"] == u"committed-unverified", (result.get(u"phase"), verdict))
    # Valid following still succeeds and is verified independently.
    calm = follower_fixture(placed_destination(arm), u"tail", u"leg", u"DmeRigOrientConstraintOperator")
    w = dst_world(fx=calm)
    tail_before = (list(w.bone_dag[u"tail"].wp), list(w.bone_dag[u"tail"].wq))
    result, verdict = apply(ns, reload(ns, lib, grip))
    check("AX2.a_constraint_between_unaffected_bones_is_not_a_follower", verdict == {u"phase": u"committed-verified"}
          and (list(w.bone_dag[u"tail"].wp), list(w.bone_dag[u"tail"].wq)) == tail_before, (result.get(u"phase"),
                                                                                             verdict))
    flib = library(root, u"synthetic_follow")
    src = FS.World(posed_source(arm))
    use(ns, src, arm)
    source_local = live_bones(src)
    forearm = save(ns, flib, ns["prod_scope_request"](u"selected_parts", [u"forearm"]), u"Forearm")
    w = dst_world()
    base = live_bones(w)
    model = (list(w.gm.wp), list(w.gm.wq))
    result, verdict = apply(ns, reload(ns, flib, forearm))
    expected = analytic(model, base, {u"forearm": (base[u"forearm"][1], source_local[u"forearm"][2])})
    dp, dq = max_errors(w, expected, list(w.bone_dag))
    carried = sorted(forearm[u"record"][u"pose"][u"scope"][u"carried"])
    check("AX2.carried_descendants_follow_their_posed_parent_and_verify", verdict == {u"phase": u"committed-verified"}
          and dp < 1e-3 and dq < 0.01 and carried == sorted([u"hand", u"finger1", u"finger2", u"finger3", u"thumb1"]),
          (verdict, dp, dq, carried))
    face_src = face_solver(posed_source(arm))
    use(ns, FS.World(face_src), face_src)
    excl = [{u"id": u"face", u"bones": [u"jaw"], u"reason": u"r", u"provenance": u"user_confirmed",
             u"policy_revision": None, u"label": u"Face"}]
    elib = library(root, u"synthetic_follow_face")
    body_only = ns["prod_pose_save_new"](elib, u"Body only", capture(ns, ns["prod_scope_request"](
        u"full_body", [], excl)), u"20261108-190000-000000", {})
    face_dst = face_solver(placed_destination(arm))
    w = FS.World(face_dst)
    use(ns, w, face_dst)
    result, verdict = apply(ns, reload(ns, elib, body_only))
    check("AX2.excluded_confined_facial_follow_is_retained", verdict == {u"phase": u"committed-verified"},
          (result.get(u"phase"), verdict))

    # --- AX3: skeletal parent relationships ----------------------------------------------------------------------
    flat = FS.synthetic(flat_head_spec(), groups=ARM_GROUPS)
    hlib = library(root, u"synthetic_parents")
    use(ns, FS.World(posed_source(flat)), flat)
    hgrip = save(ns, hlib, ns["prod_scope_request"](u"selected_parts", FINGERS), u"Grip")

    def flat_world(fx=None):
        w = FS.World(fx or placed_destination(flat))
        use(ns, w, flat)
        return w
    w = flat_world()
    jaw = (list(w.bone_dag[u"jaw"].wp), list(w.bone_dag[u"jaw"].wq), w.local(w.bone_dag[u"jaw"]))
    result, verdict = p7(w, lambda: reparent(w, u"jaw", u"spine"), reload(ns, hlib, hgrip))
    same = (list(w.bone_dag[u"jaw"].wp), list(w.bone_dag[u"jaw"].wq), w.local(w.bone_dag[u"jaw"])) == jaw
    check("AX3.astra_counterexample_same_transform_reparenting_before_P7_is_committed_unverified",
          verdict is not None and verdict[u"phase"] == u"committed-unverified" and same, (verdict, same))
    w = flat_world()
    got = at_p2(w, lambda: reparent(w, u"jaw", u"spine"), hlib, hgrip)
    refused("AX3.same_transform_reparenting_between_P1_and_P2_refuses", got, u"stale")
    check("AX3.P2_reparenting_refusal_writes_nothing", not writes(w) and not w.dm.calls)
    w = flat_world()
    w.fail_on_write = u"finger2_o"
    real_write = ns["prod_pose_write"]

    def write_then_reparent(binding, plan):
        if dag_parent(w, w.bone_dag[u"jaw"]) is w.bone_dag[u"head"]:
            reparent(w, u"jaw", u"spine")
        return real_write(binding, plan)
    ns["prod_pose_write"] = write_then_reparent
    try:
        got = outcome(lambda: apply(ns, reload(ns, hlib, hgrip)))
    finally:
        ns["prod_pose_write"] = real_write
    check("AX3.reparenting_during_the_transaction_makes_abort_recovery_unverified",
          got[0] == "ProdRecoveryUnverifiedError", got)
    w = flat_world()
    result, verdict = p7(w, lambda: reparent(w, u"jaw", u"hand"), reload(ns, hlib, hgrip))
    check("AX3.changed_parent_identity_before_P7_is_committed_unverified", verdict is not None and
          verdict[u"phase"] == u"committed-unverified", verdict)

    def replace_head(w):
        old = w.bone_dag[u"head"]
        new = FB.Dag(w, w.new_handle(), "DmeDag", u"head", old.attrs["transform"])
        new.attrs["children"].items = list(old.attrs["children"].items)
        spine = w.bone_dag[u"spine"]
        spine.attrs["children"].items[spine.attrs["children"].items.index(old)] = new
        w.bone_dag[u"head"] = new
        w.evaluate()
    w = flat_world()
    result, verdict = p7(w, lambda: replace_head(w), reload(ns, hlib, hgrip))
    check("AX3.stale_replaced_parent_element_before_P7_is_committed_unverified", verdict is not None and
          verdict[u"phase"] == u"committed-unverified", verdict)
    w = flat_world()
    reparent(w, u"jaw", u"spine", keep_old=True)
    got = outcome(lambda: apply(ns, reload(ns, hlib, hgrip)))
    refused("AX3.duplicated_parent_membership_refuses", got)
    check("AX3.duplicated_parent_refusal_writes_nothing", not writes(w) and not w.dm.calls, got)
    w = flat_world()
    reparent(w, u"jaw", None)
    got = outcome(lambda: apply(ns, reload(ns, hlib, hgrip)))
    refused("AX3.missing_parent_refuses", got)
    check("AX3.missing_parent_refusal_writes_nothing", not writes(w) and not w.dm.calls, got)
    w = flat_world()
    result, verdict = apply(ns, reload(ns, hlib, hgrip))
    check("AX3.unchanged_hierarchy_verifies", verdict == {u"phase": u"committed-verified"}, (result.get(u"phase"),
                                                                                           verdict))
    again, _ = apply(ns, reload(ns, hlib, hgrip))
    check("AX3.unchanged_hierarchy_repeat_is_a_true_noop", again == {u"phase": u"no-op"}, again)
    other = FS.synthetic(flat_head_spec(), groups=ARM_GROUPS, handles=FS.Handles(700000))
    w = flat_world(placed_destination(other))
    use(ns, w, other)
    result, verdict = apply(ns, reload(ns, hlib, hgrip))
    check("AX3.independent_operation_with_different_runtime_handles_verifies",
          verdict == {u"phase": u"committed-verified"}, (result.get(u"phase"), verdict))


# ---------------------------------------------------------------------------
# AY. Final dependency corrections (Owner authorization after the 1bf1ab3 re-review): document-wide constraint and
# channel-reader dependencies, and confined external prop followers
# ---------------------------------------------------------------------------

def prop_dag(w, name=u"prop", parent=None):
    t = FB.Element(w, w.new_handle(), "DmeTransform", name + u"_t", position=FB.Vector(), orientation=FB.Quaternion())
    d = FB.Dag(w, w.new_handle(), "DmeDag", name, t)
    (parent if parent is not None else w.scene).add(d)
    return d


def place_operator(w, el, where):
    if where == u"character":
        w.animset.attrs["operators"].items.append(el)
    elif where == u"shot":
        w.shot.attrs["operators"].items.append(el)
    else:
        w.shot.attrs["animationSets"].items.append(FB.Element(w, w.new_handle(), "DmeAnimationSet", u"prop_set",
                                                              operators=FB.ElementArray(w, [el])))


def constrain_to(w, slave_dag, target_dag, where, kind="DmeRigPointConstraintOperator", vec=(100.0, 0.0, 0.0),
                 targets=None):
    """A supported constraint (stored in the character's set, the shot, or another animation set) slaving slave_dag
    to target_dag. When the slave is a bone of the character, the fake evaluator solves it."""
    tgt = FB.Element(w, w.new_handle(), "DmeConstraintTarget", "t", target=target_dag, targetWeight=1.0,
                     vecOffset=FB.Vector(*vec))
    el = FB.Element(w, w.new_handle(), kind, u"c_%s" % slave_dag.name,
                    slave=FB.Element(w, w.new_handle(), "DmeConstraintSlave", "s", target=slave_dag),
                    targets=targets if targets is not None else FB.ElementArray(w, [tgt]))
    place_operator(w, el, where)
    if targets is None and slave_dag in w.bone_dag.values():
        w.ops.append(({u"type": kind, u"slaves": {u"slave": {u"slave": el.attrs["slave"].h, u"target": slave_dag.h}}},
                      el))
    return el


def model_pass(w):
    """Explicit model of SFM's Pass channel mode (CM_PASS, mode 1) for this World: after the normal evaluation, each
    registered Pass channel copies its source attribute to its destination and the skeleton is re-solved. The fake's
    default evaluation ignores non-Play channels, so no Pass test relies on it."""
    if getattr(w, "pass_channels", None) is None:
        w.pass_channels = []
        real = w.evaluate

        def evaluate():
            real()
            for ch in w.pass_channels:
                if ch.attrs.get("mode") == 1:
                    ch.attrs["toElement"].set(ch.attrs["toAttribute"], ch.attrs["fromElement"].attrs[
                        ch.attrs["fromAttribute"]])
            w.solve()
        w.evaluate = evaluate
    return w.pass_channels


def reader_channel(w, src, src_attr, dst, dst_attr, mode=1, clip=u"other"):
    """A channel reading src.src_attr into dst.dst_attr (in the character's channels clip or another clip). Pass mode
    is modelled explicitly (model_pass)."""
    layer = FB.Layer(w, w.new_handle(), "DmeQuaternionLogLayer", [[0, [0.0, 0.0, 0.0, 1.0]]], "quat")
    ch = FB.Channel(w, w.new_handle(), "DmeChannel", u"reader_%d" % w.new_handle(), fromElement=src,
                    fromAttribute=src_attr, toElement=dst, toAttribute=dst_attr, mode=mode, fromIndex=0, toIndex=0,
                    log=FB.Log(w, w.new_handle(), "DmeQuaternionLog", layer))
    if clip == u"character":
        w.chan_clip.attrs["channels"].items.append(ch)
    else:
        other = FB.Clip(w, w.new_handle(), "DmeChannelsClip", "Other", offset=0, start=0, end=10 ** 7,
                        channels=FB.ElementArray(w, [ch]))
        w.shot.attrs["trackGroups"].items[0].attrs["tracks"].items[0].attrs["children"].items.append(other)
    if mode == 1 and not isinstance(src, Opaque):
        model_pass(w).append(ch)
    return ch


def section_dependencies(ns, app, root, lib, grip):
    arm = arm_fixture()

    def world(prepare=None):
        w = FS.World(placed_destination(arm))
        if prepare is not None:
            prepare(w)
            w.evaluate()
        use(ns, w, arm)
        return w

    def tr(w, bone):
        return w.bone_dag[bone].attrs["transform"]

    def run():
        return outcome(lambda: apply(ns, reload(ns, lib, grip)))

    def refused_clean(label, w, got, code):
        check("AY.%s_refuses_before_writing" % label, got[0] != "ok" and got[1] == code, got)
        check("AY.%s_writes_nothing_and_opens_no_undo" % label, not writes(w) and not w.dm.calls, w.dm.calls)

    def verified(label, w, got):
        check("AY.%s_applies_and_verifies" % label, got[0] == "ok" and got[1][1] == {u"phase": u"committed-verified"},
              got if got[0] != "ok" else (got[1][0].get(u"phase"), got[1][1]))

    def at_p2(w, change):
        real = ns["prod_scope_preflight"]

        def preflight_then(*args):
            pre = real(*args)
            change()
            return pre
        ns["prod_scope_preflight"] = preflight_then
        try:
            return run()
        finally:
            ns["prod_scope_preflight"] = real

    def before_p7(change):
        item = reload(ns, lib, grip)
        auth = authorize(ns, u"Apply Pose", item)
        result = ns["prod_scope_apply"](Pin.identity, auth, item, {})
        if result.get(u"phase") != u"verification-pending":
            return result, None
        change()
        return result, ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))

    # 1. A constraint in another animation set moving an unselected bone of the character.
    w = world(lambda w: constrain_to(w, w.bone_dag[u"tail"], w.bone_dag[u"finger3"], u"other"))
    refused_clean(u"other_set_constraint_moving_an_unselected_bone", w, run(), u"shared-input")
    w = world(lambda w: constrain_to(w, w.bone_dag[u"leg"], w.bone_dag[u"finger3"], u"other",
                                     kind="DmeRigOrientConstraintOperator"))
    got = run()
    refused_clean(u"other_set_orientation_constraint", w, got, u"shared-input")
    check("AY.refusal_names_the_affected_bone", got[0] != "ok" and u"leg" in got[2], got)
    # 2. Harmless external prop following, wherever the constraint is stored.
    for where in (u"other", u"character", u"shot"):
        w = world(lambda w: constrain_to(w, prop_dag(w), w.bone_dag[u"finger3"], where))
        verified(u"prop_following_a_posed_finger_stored_in_%s" % where, w, run())
    w = world(lambda w: prop_dag(w, parent=w.bone_dag[u"hand"]))
    verified(u"prop_parented_under_an_unposed_hand", w, run())
    w = world(lambda w: prop_dag(w, parent=w.bone_dag[u"finger2"]))
    verified(u"prop_parented_under_a_posed_finger", w, run())
    # 3. A prop dependency returning into the character.
    for where in (u"other", u"character"):
        def back(w, where=where):
            p = prop_dag(w)
            constrain_to(w, p, w.bone_dag[u"finger3"], u"other")
            constrain_to(w, w.bone_dag[u"tail"], p, where)
        w = world(back)
        refused_clean(u"prop_dependency_returning_into_the_character_via_%s" % where, w, run(), u"shared-input")

    def into_control(w):
        p = prop_dag(w)
        constrain_to(w, p, w.bone_dag[u"finger3"], u"other")
        reader_channel(w, p.attrs["transform"], u"orientation", w.controls[[c.name for c in w.controls].index(
            u"leg")], u"valueOrientation")
    w = world(into_control)
    refused_clean(u"prop_dependency_returning_into_a_character_control", w, run(), u"shared-input")

    def under_prop(w):
        p = prop_dag(w)
        constrain_to(w, p, w.bone_dag[u"finger3"], u"other")
        w.scene.attrs["children"].items.remove(w.gm)
        p.add(w.gm)
    w = world(under_prop)
    refused_clean(u"character_parented_under_a_following_prop", w, run(), u"shared-input")
    # 4. Multi-step chains.

    def chain(w, end_in_character):
        a, b = prop_dag(w, u"prop_a"), prop_dag(w, u"prop_b")
        constrain_to(w, a, w.bone_dag[u"finger3"], u"other")
        constrain_to(w, b, a, u"shot")
        if end_in_character:
            constrain_to(w, w.bone_dag[u"leg"], b, u"other")
    w = world(lambda w: chain(w, False))
    verified(u"external_multi_step_chain", w, run())
    w = world(lambda w: chain(w, True))
    refused_clean(u"multi_step_chain_reentering_the_character", w, run(), u"shared-input")
    # 5. Pass-mode readers driving protected state (Pass modelled explicitly).
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation", tr(w, u"tail"), u"orientation",
                                       clip=u"character"))
    refused_clean(u"pass_reader_of_a_posed_bone_driving_an_unselected_bone", w, run(), u"shared-input")
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation", tr(w, u"tail"), u"orientation"))
    refused_clean(u"pass_reader_in_another_clip", w, run(), u"shared-input")
    w = world(lambda w: reader_channel(w, w.controls[[c.name for c in w.controls].index(u"finger1")],
                                       u"valueOrientation", tr(w, u"leg"), u"orientation"))
    refused_clean(u"pass_reader_of_a_written_source_control", w, run(), u"shared-input")

    def via_expression(w):
        expr = FB.Element(w, w.new_handle(), "DmeExpressionOperator", "expr", expr=u"value", value=0.0, result=0.0)
        place_operator(w, expr, u"other")
        reader_channel(w, tr(w, u"finger3"), u"orientation", expr, u"value")
        reader_channel(w, expr, u"result", tr(w, u"tail"), u"scale")
    w = world(via_expression)
    refused_clean(u"pass_reader_through_an_expression_operator", w, run(), u"shared-input")
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation", prop_dag(w).attrs["transform"],
                                       u"orientation", mode=2))
    refused_clean(u"record_mode_reader_of_a_posed_bone", w, run(), u"structure-unsupported")
    # 6. Genuinely unrelated readers stay permitted.

    def unrelated(w):
        a, b = prop_dag(w, u"prop_a"), prop_dag(w, u"prop_b")
        reader_channel(w, a.attrs["transform"], u"orientation", b.attrs["transform"], u"orientation")
    w = world(unrelated)
    verified(u"unrelated_pass_channel", w, run())
    w = world(lambda w: reader_channel(w, tr(w, u"leg"), u"orientation", prop_dag(w).attrs["transform"],
                                       u"orientation"))
    verified(u"pass_reader_of_an_unposed_bone_into_a_prop", w, run())
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation", prop_dag(w).attrs["transform"],
                                       u"orientation"))
    verified(u"pass_reader_of_a_posed_bone_into_a_prop", w, run())
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation", tr(w, u"tail"), u"orientation", mode=0))
    verified(u"off_mode_channel_reading_a_posed_bone", w, run())
    # 7. Dependencies appearing between P1, P2 and P7.
    w = world()
    refused(u"AY.harmless_follower_appearing_between_P1_and_P2_is_stale", at_p2(
        w, lambda: constrain_to(w, prop_dag(w), w.bone_dag[u"finger3"], u"other")), u"stale")
    check("AY.P2_follower_change_writes_nothing", not writes(w) and not w.dm.calls)
    w = world()
    refused(u"AY.return_path_appearing_between_P1_and_P2_is_stale", at_p2(
        w, lambda: constrain_to(w, w.bone_dag[u"tail"], w.bone_dag[u"finger3"], u"other")), u"stale")
    check("AY.P2_return_path_writes_nothing", not writes(w) and not w.dm.calls)
    w = world()

    def late_constraint():
        constrain_to(w, w.bone_dag[u"tail"], w.bone_dag[u"finger3"], u"other")
        w.evaluate()
    result, verdict = before_p7(late_constraint)
    check("AY.return_path_appearing_before_P7_is_committed_unverified", verdict is not None and
          verdict[u"phase"] == u"committed-unverified" and u"Undo" not in [c[0] for c in w.dm.calls], verdict)
    w = world()

    def late_pass():
        reader_channel(w, tr(w, u"finger3"), u"orientation", tr(w, u"tail"), u"orientation")
        w.evaluate()
    result, verdict = before_p7(late_pass)
    check("AY.pass_reader_appearing_before_P7_is_committed_unverified", verdict is not None and
          verdict[u"phase"] == u"committed-unverified", verdict)
    w = world()

    def late_prop():
        constrain_to(w, prop_dag(w), w.bone_dag[u"finger3"], u"other")
        w.evaluate()
    result, verdict = before_p7(late_prop)
    check("AY.follower_relationship_changing_before_P7_is_committed_unverified", verdict is not None and
          verdict[u"phase"] == u"committed-unverified", verdict)
    # 8. Unknown or unreadable relevant effects.
    w = world(lambda w: constrain_to(w, w.bone_dag[u"tail"], w.bone_dag[u"finger3"], u"other", targets=Opaque()))
    refused_clean(u"constraint_with_unreadable_reads_driving_a_character_bone", w, run(), u"evidence-unreadable")
    w = world(lambda w: constrain_to(w, prop_dag(w), w.bone_dag[u"finger3"], u"other", targets=Opaque()))
    verified(u"constraint_with_unreadable_reads_driving_only_a_prop", w, run())

    def unreadable_mode(w):
        ch = reader_channel(w, tr(w, u"finger3"), u"orientation", prop_dag(w).attrs["transform"], u"orientation",
                            mode=0)
        ch.set("mode", Opaque())
    w = world(unreadable_mode)
    refused_clean(u"channel_with_an_unreadable_mode_reading_a_posed_bone", w, run(), u"evidence-unreadable")
    w = world(lambda w: reader_channel(w, Opaque(), u"orientation", tr(w, u"tail"), u"orientation"))
    refused_clean(u"channel_with_an_unreadable_source_driving_a_character_bone", w, run(), u"evidence-unreadable")

    def unknown_operator(w):
        place_operator(w, FB.Element(w, w.new_handle(), "DmeUnknownSolverOperator", "mystery"), u"other")
    w = world(unknown_operator)
    refused_clean(u"unknown_operator_in_another_animation_set", w, run(), u"structure-unsupported")
    # 9. The previously corrected counterexamples remain closed (AX1-AX3 rows run in this suite); one each here.
    w = world(lambda w: set_index(w, u"finger1_o", "toIndex", 1))
    refused_clean(u"previous_index_counterexample", w, run(), u"unsupported-selection")
    far = follower_fixture(placed_destination(arm), u"tail", u"finger3", u"DmeRigPointConstraintOperator",
                           vec=[100.0, 0.0, 0.0])
    w = FS.World(far)
    use(ns, w, arm)
    refused_clean(u"previous_follower_counterexample", w, run(), u"shared-input")


# ---------------------------------------------------------------------------
# AZ. Dependency ownership corrections (Astra closure review of 953b107): protected animation resources,
# shared-transform aliases and the positive external-admission invariant
# ---------------------------------------------------------------------------

def shared_dags(w, names, transform=None, parent=None):
    """DAGs that share one transform element, added to the scene (or under `parent`) in the given order."""
    t = transform if transform is not None else FB.Element(w, w.new_handle(), "DmeTransform", u"shared_t",
                                                           position=FB.Vector(), orientation=FB.Quaternion())
    out = {}
    for n in names:
        out[n] = FB.Dag(w, w.new_handle(), "DmeDag", n, t)
    for n in names:
        (parent if parent is not None else w.scene).add(out[n])
    return out


def section_ownership(ns, app, root, lib, grip):
    arm = arm_fixture()

    def world(prepare=None):
        w = FS.World(placed_destination(arm))
        if prepare is not None:
            prepare(w)
            w.evaluate()
        use(ns, w, arm)
        return w

    def tr(w, bone):
        return w.bone_dag[bone].attrs["transform"]

    def run():
        return outcome(lambda: apply(ns, reload(ns, lib, grip)))

    def refused_clean(label, w, got, code):
        check("AZ.%s_refuses_before_writing" % label, got[0] != "ok" and got[1] == code, got if got[0] != "ok" else
              (got[1][0].get(u"phase"), got[1][1]))
        check("AZ.%s_writes_nothing_and_opens_no_undo" % label, not writes(w) and not w.dm.calls, w.dm.calls)

    def verified(label, w, got):
        check("AZ.%s_applies_and_verifies" % label, got[0] == "ok" and got[1][1] == {u"phase": u"committed-verified"},
              got if got[0] != "ok" else (got[1][0].get(u"phase"), got[1][1]))

    # 1. Protected animation resources (Astra's exact counterexample first).
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation", w.channels[u"tail_o"].attrs["log"],
                                       u"defaultvalue"))
    refused_clean(u"astra_pass_from_a_posed_finger_into_the_tail_log_defaultvalue", w, run(), u"shared-input")
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation",
                                       w.channels[u"tail_o"].attrs["log"].layer, u"value"))
    refused_clean(u"pass_into_a_character_layer", w, run(), u"shared-input")
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation", w.animset, u"name"))
    refused_clean(u"pass_into_the_character_animation_set", w, run(), u"shared-input")

    def external_log(w):
        other = reader_channel(w, prop_dag(w).attrs["transform"], u"orientation", prop_dag(w, u"prop_b").attrs[
            "transform"], u"orientation", mode=0)
        reader_channel(w, tr(w, u"finger3"), u"orientation", other.attrs["log"], u"defaultvalue")
    w = world(external_log)
    refused_clean(u"pass_into_another_animation_log", w, run(), u"structure-unsupported")

    def other_control(w):
        control = FB.Element(w, w.new_handle(), "DmeTransformControl", u"prop_control",
                             valueOrientation=FB.Quaternion())
        w.shot.attrs["animationSets"].items.append(FB.Element(w, w.new_handle(), "DmeAnimationSet", u"prop_set",
                                                              controls=FB.ElementArray(w, [control]),
                                                              operators=FB.ElementArray(w, [])))
        reader_channel(w, tr(w, u"finger3"), u"orientation", control, u"valueOrientation")
    w = world(other_control)
    refused_clean(u"pass_into_another_animation_sets_control", w, run(), u"structure-unsupported")
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation",
                                       FB.Element(w, w.new_handle(), "DmElement", u"blob", value=0.0), u"value"))
    refused_clean(u"pass_into_an_element_of_unknown_ownership", w, run(), u"structure-unsupported")
    w = world(lambda w: reader_channel(w, tr(w, u"finger3"), u"orientation",
                                       FB.Element(w, w.new_handle(), "DmeTransform", u"orphan",
                                                  orientation=FB.Quaternion()), u"orientation"))
    refused_clean(u"pass_into_a_transform_no_scene_dag_owns", w, run(), u"structure-unsupported")
    w = world(lambda w: constrain_to(w, FB.Element(w, w.new_handle(), "DmElement", u"not_a_dag"),
                                     w.bone_dag[u"finger3"], u"other"))
    refused_clean(u"constraint_slaving_an_element_that_is_not_a_scene_dag", w, run(), u"structure-unsupported")

    def to_prop_via_expression(w):
        expr = FB.Element(w, w.new_handle(), "DmeExpressionOperator", "expr", expr=u"value", value=0.0, result=0.0)
        place_operator(w, expr, u"other")
        reader_channel(w, tr(w, u"finger3"), u"orientation", expr, u"value")
        reader_channel(w, expr, u"result", prop_dag(w).attrs["transform"], u"orientation")
    w = world(to_prop_via_expression)
    verified(u"bounded_expression_route_into_a_prop", w, run())
    w = world(lambda w: constrain_to(w, prop_dag(w), w.bone_dag[u"finger3"], u"other"))
    verified(u"ordinary_unshared_external_prop", w, run())

    # 2. Shared-transform aliases (every sharing DAG is an owner; enumeration order never selects one).
    for order in ((u"P", u"Q"), (u"Q", u"P")):
        def alias_return(w, order=order):
            dags = shared_dags(w, order)
            constrain_to(w, dags[u"P"], w.bone_dag[u"finger3"], u"other")
            constrain_to(w, w.bone_dag[u"tail"], dags[u"Q"], u"other")
        w = world(alias_return)
        refused_clean(u"astra_shared_transform_alias_returning_to_the_tail_order_%s" % u"".join(order), w, run(),
                      u"shared-input")
    for order in ((u"P", u"Q", u"R"), (u"R", u"Q", u"P"), (u"Q", u"R", u"P")):
        def three(w, order=order):
            dags = shared_dags(w, order)
            constrain_to(w, dags[u"P"], w.bone_dag[u"finger3"], u"other")
            constrain_to(w, w.bone_dag[u"leg"], dags[u"R"], u"character")
        w = world(three)
        refused_clean(u"three_aliases_returning_to_the_leg_order_%s" % u"".join(order), w, run(), u"shared-input")
    for order in ((u"P", u"Q"), (u"Q", u"P")):
        def external_only(w, order=order):
            dags = shared_dags(w, order)
            constrain_to(w, dags[u"P"], w.bone_dag[u"finger3"], u"other")
        w = world(external_only)
        verified(u"shared_transform_among_external_props_only_order_%s" % u"".join(order), w, run())

    def prop_sharing_the_tail_transform(w):
        p = shared_dags(w, [u"P"], transform=tr(w, u"tail"))[u"P"]
        constrain_to(w, p, w.bone_dag[u"finger3"], u"other")
    w = world(prop_sharing_the_tail_transform)
    # A second DAG holding a bone's transform is refused by the live reader as a duplicated bone element.
    refused_clean(u"prop_sharing_a_protected_bone_transform", w, run(), u"structure-unsupported")
    w = world(lambda w: shared_dags(w, [u"P"], transform=tr(w, u"finger3")))
    refused_clean(u"external_dag_sharing_a_posed_bone_transform", w, run(), u"structure-unsupported")

    def prop_sharing_the_model_transform(w):
        p = shared_dags(w, [u"P"], transform=w.gm.attrs["transform"])[u"P"]
        constrain_to(w, p, w.bone_dag[u"finger3"], u"other")
    w = world(prop_sharing_the_model_transform)
    refused_clean(u"following_prop_sharing_the_model_transform", w, run(), u"shared-input")

    # 3. Ownership changing between phases.
    w = world()
    real = ns["prod_scope_preflight"]

    def preflight_then(*args):
        pre = real(*args)
        dags = shared_dags(w, (u"P", u"Q"))
        constrain_to(w, dags[u"P"], w.bone_dag[u"finger3"], u"other")
        constrain_to(w, w.bone_dag[u"tail"], dags[u"Q"], u"other")
        return pre
    ns["prod_scope_preflight"] = preflight_then
    try:
        got = run()
    finally:
        ns["prod_scope_preflight"] = real
    refused(u"AZ.shared_alias_appearing_between_P1_and_P2_is_stale", got, u"stale")
    check("AZ.P2_alias_refusal_writes_nothing", not writes(w) and not w.dm.calls)
    w = world()
    item = reload(ns, lib, grip)
    auth = authorize(ns, u"Apply Pose", item)
    result = ns["prod_scope_apply"](Pin.identity, auth, item, {})
    reader_channel(w, tr(w, u"finger3"), u"orientation", w.channels[u"tail_o"].attrs["log"], u"defaultvalue")
    w.evaluate()
    verdict = ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
    check("AZ.protected_log_reader_appearing_before_P7_is_committed_unverified",
          verdict[u"phase"] == u"committed-unverified" and u"Undo" not in [c[0] for c in w.dm.calls], verdict)


# ---------------------------------------------------------------------------
# UI. Pose Library UI adjudication (Astra, 2026-11-08): truthful coverage wording and Pose Info from the saved record
# ---------------------------------------------------------------------------

def section_ui_copy(ns, fx, root):
    """Astra's UI implementation review (after 284cfa2): no routine explanations; consequential limitations kept."""
    arm = arm_fixture()
    use(ns, FS.World(posed_source(arm)), arm)
    lib = library(root, u"synthetic_ui")
    grip = save(ns, lib, ns["prod_scope_request"](u"selected_parts", FINGERS), u"Grip")
    mixed = save(ns, lib, ns["prod_scope_request"](u"selected_parts", [u"finger1", u"finger3", u"thumb1"]), u"Mixed")
    single = save(ns, lib, ns["prod_scope_request"](u"selected_parts", [u"thumb1"]), u"Thumb")
    forearm = save(ns, lib, ns["prod_scope_request"](u"selected_parts", [u"forearm"]), u"Forearm")
    body = save(ns, lib, ns["prod_scope_request"](u"full_body"), u"Body")
    face = face_solver(posed_source(arm))
    use(ns, FS.World(face), face)
    excl = [{u"id": u"face", u"bones": [u"jaw"], u"reason": u"r", u"provenance": u"user_confirmed",
             u"policy_revision": None, u"label": u"Face"}]
    body_face = save(ns, lib, ns["prod_scope_request"](u"full_body", [], excl), u"Body only")
    view = ns["prod_pose_info_view"]
    banned = (u"Applies the saved", u"character's rig", u"chosen when saving", u"from supported metadata",
              u"Saves the bends", u"position and orientation", u"revision", u"direct_fk", u"controls (articulation",
              u"Unselected parts unchanged")
    for name, rec in ((u"grip", grip), (u"mixed", mixed), (u"single", single), (u"forearm", forearm), (u"body", body),
                      (u"body_face", body_face)):
        v = view(rec[u"record"])
        texts = u" ".join(r[1] for r in v[u"rows"]) + u" " + (v[u"effect"] or u"")
        check("UI.pose_info_%s_has_no_redundant_phrase_and_only_its_fields" % name,
              set(r[0] for r in v[u"rows"]) <= set([u"Includes:", u"Not included:", u"Saved from:", u"Saved:",
                                                    u"Updated:"]) and not any(b in texts for b in banned), v)
    v = view(grip[u"record"])
    check("UI.1_ordinary_grip_has_exactly_includes_source_model_and_date_and_no_explanation",
          v[u"rows"] == [[u"Includes:", u"Fingers", None],
                         [u"Saved from:", u"analytic.mdl", u"models/synthetic/analytic.mdl"],
                         [u"Saved:", u"November 8, 2026", None]] and v[u"effect"] is None, v)
    v = view(body_face[u"record"])
    check("UI.2_consequential_exclusions_remain_visible",
          [u"Not included:", u"Face controls, facial expressions, scene placement", None] in v[u"rows"], v)
    v = view(forearm[u"record"])
    check("UI.3_attached_part_movement_remains_visible_where_it_happens",
          v[u"effect"] == u"Unselected parts attached to these parts move with them.", v)
    v = view(body[u"record"])
    check("UI.4_full_body_shows_only_what_it_does_not_include",
          v[u"rows"][:2] == [[u"Includes:", u"Full body", None],
                             [u"Not included:", u"Facial expressions, scene placement", None]] and
          v[u"effect"] is None, v)
    check("UI.5_spaced_and_camel_case_group_names",
          ns["prod_scope_friendly_label"](u"LeftFingers") == u"Left fingers" and
          ns["prod_scope_friendly_label"](u"Left Fingers") == u"Left Fingers" and
          ns["prod_scope_friendly_label"](u"Left fingers") == u"Left fingers" and
          ns["prod_scope_friendly_label"](u"Face") == u"Face" and
          ns["prod_scope_friendly_label"](u"Selected parts (3)") is None and
          ns["prod_scope_friendly_label"](u"bip_hand_l") is None and
          ns["prod_scope_friendly_label"](u"Left  fingers") is None)
    v, w = view(mixed[u"record"]), view(single[u"record"])
    check("UI.6_individual_and_mixed_selections_name_their_recorded_controls",
          v[u"rows"][0] == [u"Includes:", u"thumb1, finger1, finger3", u"thumb1, finger1, finger3"] and
          w[u"rows"][0] == [u"Includes:", u"thumb1", u"thumb1"] and w[u"effect"] is None, (v, w))
    v1 = {u"name": u"Arm", u"created_at": u"20261101-090000-000000", u"updated_at": u"20261102-101500-000000",
          u"pose": {u"version": 1, u"regions": {u"left_arm": {}}, u"source": {u"model_ref": u"models\\a\\krystal2020.mdl"}}}
    v2 = {u"name": u"Body", u"created_at": u"20261103-080000-000000", u"updated_at": u"20261103-080000-000000",
          u"pose": {u"version": 2, u"regions": {u"full_body": {}}, u"source": {u"model_ref": u"models/k.mdl"}}}
    a, b = view(v1), view(v2)
    check("UI.7_legacy_records_remain_readable",
          a[u"rows"] == [[u"Includes:", u"Left arm", None], [u"Saved from:", u"krystal2020.mdl", u"models/a/krystal2020.mdl"],
                         [u"Updated:", u"November 2, 2026", None]] and a[u"effect"] is None and
          b[u"rows"] == [[u"Includes:", u"Full body", None],
                         [u"Not included:", u"Facial expressions, gaze, scene placement", None],
                         [u"Saved from:", u"k.mdl", u"models/k.mdl"], [u"Saved:", u"November 3, 2026", None]] and
          b[u"effect"] is None, (a, b))
    check("UI.dates_are_month_day_year_and_keep_unknown_text",
          ns["prod_pose_info_date"](u"20261108-193207-1") == u"November 8, 2026" and
          ns["prod_pose_info_date"](u"odd") == u"odd" and ns["prod_pose_info_date"](None) == u"Unknown")
    # Save Pose guidance: none for an ordinary selection; consequential lines only; no bone names in prose.
    use(ns, FS.World(posed_source(arm)), arm)
    inv = inventory(ns)

    def summary(bones):
        return ns["prod_scope_dialog_state"](inv, {u"kind": u"selected_parts", u"bones": bones})[u"summary"]
    check("UI.save_an_ordinary_finger_selection_shows_no_explanation", summary(FINGERS) == u"" and
          summary([u"thumb1"]) == u"", (summary(FINGERS), summary([u"thumb1"])))
    check("UI.save_attached_unselected_parts_are_mentioned_without_bone_names",
          summary([u"forearm"]) == u"Unselected parts attached to these parts move with them." and
          summary([u"finger1", u"finger3"]) == u"Unselected parts attached to these parts move with them.",
          (summary([u"forearm"]), summary([u"finger1", u"finger3"])))
    check("UI.save_a_selected_body_root_keeps_its_position",
          summary([u"pelvis"]) == u"Unselected parts attached to these parts move with them. The body root keeps "
                                  u"its position.", summary([u"pelvis"]))
    full = ns["prod_scope_dialog_state"](arm_inventory_without_face(ns, inv), {u"kind": u"full_body"})[u"summary"]
    check("UI.save_full_body_states_what_is_not_saved_including_scene_placement",
          full == u"Facial expressions and the character's place in the scene are not saved.", full)
    for bones in (FINGERS, [u"forearm"], [u"pelvis"], [u"finger1", u"finger3"]):
        s = summary(bones)
        check("UI.save_%s_never_promises_unchanged_parts_or_names_bones" % u"_".join(bones[:2]),
              u"unchanged" not in s.lower() and not any(n in s for n in arm_spec_names()), s)
    heavy = fx[u"mc02"]
    use(ns, FS.World(heavy), heavy)
    inv = inventory(ns)
    labels = dict(zip([u" > ".join(r[u"path"]) for r in inv[u"view"]], ns["prod_scope_group_labels"](inv[u"view"])))
    check("UI.group_labels_shorten_only_where_unambiguous",
          labels[u"RigArms > LeftArm > LeftFingers"] == u"LeftFingers" and
          labels[u"RigArms > LeftArm"] == u"RigArms > LeftArm" and labels[u"Arms > LeftArm"] == u"Arms > LeftArm"
          and len(set(labels.values())) == len(labels), labels)
    check("UI.poses_tab_note_is_instructional", ns["PROD_POSE_EDITOR_NOTE_COPY"] == u"Apply poses in the Motion Editor.")


def arm_spec_names():
    return [n for n, _, _, _, _ in arm_spec()]


def arm_inventory_without_face(ns, inv):
    return dict(inv, highlighted=[], full_body={u"status": u"available", u"code": None, u"message": None,
                                                u"review": []})


def section_static(app):
    text = route._read_source(route.APP_PATH)[0].decode("utf-8")
    start = text.index(u"# F-01 Pose Library scoped poses, SFP-1")
    end = text.index(u"# === end of F-01 scoped pose block ===")
    block = text[start:end]
    check("Z.scoped_block_never_calls_a_native_mutation_outside_the_owned_transaction",
          block.count(u"StartUndo(") == 1 and block.count(u"FinishUndo()") == 1 and
          block.count(u"AbortUndoableOperation()") == 1 and u"SetKeyValue" not in block and
          u"InsertKeyAtTime" not in block and u"SetHeadTimeInSeconds" not in block)
    check("Z.scoped_block_reads_no_current_sfm_selection", u"GetSelect" not in block and u"selection" not in
          block.replace(u"selection-", u"").lower().replace(u"selections", u"").replace(u"selected", u"")
          or u"GetSelect" not in block)
    check("Z.no_name_heuristic_authorizes_scope", not any(s in block for s in (u'"head" in', u'"jaw" in',
                                                                               u'"face" in n', u"startswith(u\"bip")))


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        return 2
    print("F-01 SFP-1 scoped poses (Python %s)" % sys.version.split()[0])
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    app = route.AppSource(route.APP_PATH)
    root = tempfile.mkdtemp(prefix="cpm_sfp1_lib_")
    try:
        ns = namespace(app)
        fx = dict((n, body.fixture("s0_%s.json" % s)) for n, s in ((u"k15", u"shot15"), (u"k13", u"shot13")))
        fx[u"mc01"] = scoped_fixture("mc01_heavy_norig.json")
        fx[u"mc02"] = scoped_fixture("mc02_heavy_rig.json")
        got = run("records", lambda: section_records(ns, os.path.join(root, u"records")))
        run("coverage", lambda: section_coverage(ns, fx))
        run("exclusions", lambda: section_exclusions(ns, os.path.join(root, u"exclusions")))
        frames = run("frames", lambda: section_frames(ns, os.path.join(root, u"frames")))
        run("scale", lambda: section_scale(ns, os.path.join(root, u"scale")))
        run("krystal_fingers", lambda: section_krystal_fingers(ns, fx, os.path.join(root, u"krystal")))
        run("carried", lambda: section_carried(ns, fx, os.path.join(root, u"carried")))
        full = run("full_body", lambda: section_full_body(ns, os.path.join(root, u"full")))
        if frames and frames is not True:
            run("authority", lambda: section_authority(ns, root, frames[0], frames[1]))
            run("transactions", lambda: section_transactions(ns, app, root, frames[0], frames[1]))
            run("corrections", lambda: section_corrections(ns, app, root, frames[0], frames[1]))
            run("dependencies", lambda: section_dependencies(ns, app, root, frames[0], frames[1]))
            run("ownership", lambda: section_ownership(ns, app, root, frames[0], frames[1]))
            if full and full is not True:
                run("sequential", lambda: section_sequential(ns, root, full[0], full[1], frames[0], frames[1]))
            run("semantics", lambda: section_semantics(ns, app, fx, root, frames[0], frames[1]))
        run("rigged_heavy", lambda: section_rigged_heavy(ns, fx, os.path.join(root, u"heavy_rig")))
        run("window", lambda: section_window(app, ns, fx, os.path.join(root, u"window")))
        run("ui_state", lambda: section_ui_state(ns))
        run("dialog_copy", lambda: section_dialog_copy(ns, fx))
        run("ui_copy", lambda: section_ui_copy(ns, fx, os.path.join(root, u"ui_copy")))
        run("static", lambda: section_static(app))
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
