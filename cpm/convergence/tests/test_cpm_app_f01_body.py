# -*- coding: utf-8 -*-
"""F-01 full body (stage E): offline qualification of the complete-pose core and planner in the CPM application
source. Design authority: cpm/qualification/F01_FULL_BODY_CONSOLIDATED_DESIGN.md Rev 2 (A1 Astra ruling, A2/A3
Owner decisions) and F01_FULL_BODY_S0_ASSESSMENT.md; Owner S1 authorization 2026-11-06.

Technique (as the stage A-D suites): the stage A-E blocks and the CPM helpers they call are extracted verbatim and
run in a namespace without SFM. The oracle data are discovery fixtures derived from the native S0 survey
(fixtures/f01_body/, f01_body_fixture.py): the real Krystal rig of shot15, shot13 and shot10, so classification and
coverage are checked against the natively recorded structure, not a model of it. Nothing here demonstrates native
SFM behaviour.

Usage: --phase=run (Python 2.7.5 and Python 3.10).
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
import fake_sfm_body as FB  # noqa: E402

try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

FIXTURES = os.path.join(_THIS_DIR, "fixtures", "f01_body")
FIXTURE_SHA256 = {
    "s0_shot15.json": "1fe45db63ad7ba9ce86fbc37a7d7a2b5badb0af9c73263d270cc95e52f280133",
    "s0_shot13.json": "7851d75b9a07ee2e597594fb1bd8a15be3779f5686d0ea651ee32024347d7997",
    "s0_shot10.json": "dc9c7b1d058e28189390c80d0cc3d5022a6bdf9a3a7c680c4f87e7b361804c21",
}
BODY_REGISTRY_PATH = os.path.join(core._REPO_ROOT, "cpm", "pose_profiles", "cpm_body_profiles_v1.json")
BLOCKS = ((core.BLOCK_START, core.BLOCK_END),
          (u"# F-01 Pose Library M1, stage B: offline pose library", u"# === end of F-01 stage B block ==="),
          (u"# F-01 Pose Library M1, stage C: CPM integration seams", u"# === end of F-01 stage C block ==="),
          (u"# F-01 Pose Library M1, stage D: the left-arm live layer", u"# === end of F-01 stage D block ==="),
          (u"# F-01 Pose Library full body, stage E: complete skeletal poses", u"# === end of F-01 stage E block ==="))
HELPERS = ("u", "dm", "prod_outcome", "prod_apply_deferred_unverified", "ProdRecoveryUnverifiedError",
           "PROD_INSTANCE_TOKEN_KIND", "prod_instance_token", "_PROD_PRIVATE_WINDLL", "prod_private_windll",
           "p02_ensure_dir", "p02_json_text", "p02_unique_temp", "p02_safe_write_json")
MODEL = u"models/fursonas/starfox/krystal/bodies/krystal2020.mdl"
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
    """The next float32 above x (one ULP)."""
    bits = struct.unpack("<I", struct.pack("<f", float(x)))[0]
    bits += 1 if x >= 0 else -1
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def build_namespace(app):
    ns = {"__builtins__": __builtins__, "json": json, "hashlib": hashlib, "math": math, "os": os,
          "re": __import__("re"), "sys": sys, "binascii": __import__("binascii"),
          "datetime": __import__("datetime"), "ctypes": __import__("ctypes"), "traceback": traceback}
    if sys.version_info[0] >= 3:
        ns["unicode"] = str
        ns["long"] = int
    ns["LOG"] = []
    ns["log_line"] = lambda text: ns["LOG"].append(_TEXT(text))
    for name in HELPERS:
        route._run_source(app.top_text(name), "app:%s" % name, ns)
    prefixes = core.PREFIXES
    core.PREFIXES = prefixes + ("prod_body_", "PROD_BODY_")      # the stage E names
    try:
        blocks = [core.extract_block(route.APP_PATH, start, end)[0] for start, end in BLOCKS]
    finally:
        core.PREFIXES = prefixes
    for block in blocks:
        route._run_source(block, "block", ns)
    return ns


def fixture(name):
    raw = core.read(os.path.join(FIXTURES, name))
    check("fixture.%s.matches_its_pin" % name, core.sha(raw) == FIXTURE_SHA256[name])
    return json.loads(raw.decode("utf-8"))


def registries(ns):
    arm = ns["prod_pose_registry_parse"](core.read(core.REGISTRY_PATH), ns["PROD_POSE_REGISTRY_SHA256"])
    raw = core.read(BODY_REGISTRY_PATH)
    body = ns["prod_body_registry_parse"](raw, ns["PROD_BODY_REGISTRY_SHA256"], arm)
    arm[u"_body"] = body
    return arm, body


def profile_of(ns, reg):
    return ns["prod_body_profile"](reg, u"krystal-v1")


def snapshots(D, names):
    """Stage A layer snapshots from the fixture's recorded keys (what prod_pose_layer_snapshot reads natively)."""
    out = {}
    for n in names:
        ch = D[u"channels"][n]
        quat = ch[u"log_type"] == u"DmeQuaternionLog"
        out[n] = {u"name": n, u"kind": u"quaternion" if quat else u"vector", u"mode": ch[u"mode"],
                  u"layer_count": len(ch[u"layers"]), u"log_type": ch[u"log_type"], u"layer_type": ch[u"layers"][0],
                  u"curveinfo": u"null", u"curvetypes": u"absent", u"compressed": u"empty", u"defaults": [],
                  u"bookmarks": [], u"times": [k[0] for k in ch[u"keys"]], u"values": [list(k[1]) for k in ch[u"keys"]],
                  u"evaluated_at_t": list(ch[u"value"]), u"unreadable": []}
    return out


# ---------------------------------------------------------------------------
# S1-A: body registry, classification and coverage
# ---------------------------------------------------------------------------

def section_registry(ns):
    arm, body = registries(ns)
    p = body[u"profiles"][u"body_krystal_v1"]
    check("R.registry_parses_with_its_pin", body[u"_sha256"] == ns["PROD_BODY_REGISTRY_SHA256"])
    check("R.rig_core_is_the_native_krystal_rig", p[u"rig_name"] == u"rig_biped_Krystal45" and len(p[u"handles"]) == 22
          and len(p[u"constraints"]) == 36 and len(p[u"written_handle_channels"]) == 30
          and sorted(p[u"preserved_handle_channels"]) == [u"Elbow_l_o", u"Elbow_r_o", u"Knee_l_o", u"Knee_r_o",
                                                          u"rig_root_o", u"rig_root_p"], p[u"rig_name"])
    check("R.A2_pole_orientations_are_preserved_not_written",
          not any(c in p[u"written_handle_channels"] for c in (u"Elbow_l_o", u"Elbow_r_o", u"Knee_l_o", u"Knee_r_o")))
    check("R.A3_passive_twist_bones_listed",
          p[u"passive_channel_bones"] == [u"bip_lowerArm_l_twist2", u"bip_lowerArm_r_twist2"])
    check("R.full_body_mapping_is_experimental", body[u"mappings"] == [
        {u"region": u"full_body", u"from": u"krystal-v1", u"to": u"krystal-v1", u"status": u"experimental",
         u"evidence": None}])
    raw = core.read(BODY_REGISTRY_PATH)
    refused("R.wrong_pin_refuses", outcome(lambda: ns["prod_body_registry_parse"](raw, u"0" * 64, arm)), u"registry")

    def tampered(mutate):
        draft = json.loads(raw.decode("utf-8"))
        mutate(draft[u"profiles"][u"body_krystal_v1"], draft)
        data = ns["prod_pose_canonical_bytes"](draft)
        return outcome(lambda: ns["prod_body_registry_parse"](data, core.sha(data), arm))
    refused("R.unknown_handle_parent_refuses", tampered(lambda p, d: p[u"handles"].update({u"Hip": u"nowhere"})),
            u"registry")
    refused("R.handle_cycle_refuses", tampered(lambda p, d: p[u"handles"].update({u"spine_1": u"spine_4"})),
            u"registry")
    refused("R.duplicate_constraint_refuses", tampered(lambda p, d: p[u"constraints"].append(p[u"constraints"][0])),
            u"registry")
    refused("R.placement_as_helper_refuses", tampered(lambda p, d: p[u"helper_handles"].append(u"rig_root")),
            u"registry")
    refused("R.written_placement_refuses",
            tampered(lambda p, d: p[u"written_handle_channels"].update({u"rig_root_x": [u"rig_root", u"position"]})),
            u"registry")
    refused("R.qualified_without_evidence_refuses",
            tampered(lambda p, d: d[u"mappings"][0].update({u"status": u"qualified"})), u"registry")
    refused("R.other_models_than_the_pose_registry_refuse",
            tampered(lambda p, d: d[u"rig_classes"][u"krystal-v1"][u"models"][0].update({u"model_ref": u"x.mdl"})),
            u"registry")
    refused("R.unknown_field_refuses", tampered(lambda p, d: p.update({u"extra": 1})), u"invalid-file")
    sel = ns["prod_pose_registry_select"](arm, u"production")
    check("R.production_selection_has_no_experimental_full_body",
          not [m for m in sel[u"mappings"] if m[u"region"] == u"full_body"]
          and sel[u"body_registry_sha256"] == body[u"_sha256"], sel[u"mappings"])
    sel = ns["prod_pose_registry_select"](arm, u"qualification")
    check("R.qualification_selection_adds_full_body",
          [(m[u"region"], m[u"status"]) for m in sel[u"mappings"]] == [
              (u"left_arm", u"qualified"), (u"right_arm", u"experimental"), (u"full_body", u"experimental")])
    plain = ns["prod_pose_registry_parse"](core.read(core.REGISTRY_PATH), ns["PROD_POSE_REGISTRY_SHA256"])
    check("R.left_arm_selection_unchanged_without_the_body_registry",
          ns["prod_pose_registry_select"](plain, u"production") == {
              u"mode": u"production", u"registry_sha256": plain[u"_sha256"],
              u"mappings": [m for m in plain[u"mappings"] if m[u"status"] == u"qualified"]})
    folder = tempfile.mkdtemp(prefix="cpm_body_reg_")
    try:
        check("R.missing_body_file_loads_as_unavailable", ns["prod_body_load_registry"](plain, folder) is None)
        with io.open(os.path.join(folder, ns["PROD_BODY_REGISTRY_FILENAME"]), "wb") as f:
            f.write(raw + b" ")
        check("R.damaged_body_file_loads_as_unavailable", ns["prod_body_load_registry"](plain, folder) is None)
        with io.open(os.path.join(folder, ns["PROD_BODY_REGISTRY_FILENAME"]), "wb") as f:
            f.write(raw)
        check("R.pinned_body_file_loads", ns["prod_body_load_registry"](plain, folder)[u"_sha256"] ==
              ns["PROD_BODY_REGISTRY_SHA256"])
    finally:
        shutil.rmtree(folder, True)
    return arm


def counts(values):
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def section_classification(ns, reg, fx):
    profile = profile_of(ns, reg)
    expected_channels = {u"handle-written": 30, u"handle-preserved": 6, u"fk-written": 248, u"fk-preserved": 18,
                         u"slave-base": 40, u"ik-offset": 12, u"passive": 4, u"weight": 28,
                         u"operator-output": 2, u"preserved": 117}
    for name in (u"shot15", u"shot13", u"shot10"):
        D = fx[name]
        C = ns["prod_body_classify"](D, profile)
        want = dict(expected_channels)
        if name == u"shot10":                         # its set lacks bip_tail00_scale (native S0-Q12)
            want.update({u"operator-output": 1, u"preserved": 116})
        check("K.%s.bone_classes" % name, counts(C[u"bones"].values()) == {
            u"fk": 124, u"fk-preserved": 9, u"constrained": 21, u"passive": 2}, counts(C[u"bones"].values()))
        check("K.%s.handle_classes" % name, counts(C[u"handles"].values()) == {
            u"core": 17, u"helper": 4, u"placement": 1}, counts(C[u"handles"].values()))
        check("K.%s.every_channel_has_one_role" % name, counts(C[u"channels"].values()) == want and
              sorted(C[u"channels"]) == sorted(D[u"channels"]), counts(C[u"channels"].values()))
        check("K.%s.written_set_is_278_channels" % name, len(C[u"written"]) == 278, len(C[u"written"]))
    D = fx[u"shot15"]
    C = ns["prod_body_classify"](D, profile)
    check("K.constrained_bones_own_channels_are_dormant_slave_bases",
          C[u"channels"][u"bip_pelvis_p"] == u"slave-base" and C[u"channels"][u"bip_hip_l_o"] == u"slave-base")
    check("K.ik_chain_positions_are_bone_offsets",
          C[u"channels"][u"bip_hip_l_p"] == u"ik-offset" and C[u"channels"][u"bip_hand_r_p"] == u"ik-offset")
    check("K.twist_bones_are_passive_and_preserved_jaw",
          C[u"bones"][u"bip_lowerArm_l_twist2"] == u"passive" and C[u"bones"][u"jaw"] == u"fk-preserved" and
          C[u"bones"][u"bip_UpperArm_l_twist2"] == u"fk" and C[u"bones"][u"Ear_l"] == u"fk"
          and C[u"bones"][u"bip_tail025"] == u"fk")
    check("K.foot_helpers_are_helpers_and_their_channels_slave_bases",
          C[u"handles"][u"rig_footHelper1"] == u"helper" and C[u"channels"][u"rig_footHelper1_p"] == u"slave-base")
    check("K.written_never_includes_placement_poles_face_or_twist",
          not [n for n in C[u"written"] if n.startswith(u"rig_root") or n in (u"Elbow_l_o", u"Knee_r_o")
               or n.startswith(u"jaw") or n.startswith(u"tongue") or u"lowerArm_l_twist2" in n])

    def variant(mutate):
        d = copy.deepcopy(D)
        mutate(d)
        return outcome(lambda: ns["prod_body_classify"](d, profile))
    refused("K.unknown_operator_type_refuses",
            variant(lambda d: d[u"operators"].append(dict(d[u"operators"][0], type=u"DmeRigAimConstraintOperator"))),
            u"structure-unsupported")
    refused("K.unknown_operator_in_the_document_refuses",
            variant(lambda d: d.update({u"unknown_operator_types": [u"DmeFooOperator"]})), u"structure-unsupported")
    refused("K.reparented_knee_refuses", variant(lambda d: d[u"rig"][u"handles"][u"Knee_l"].update(
        {u"parent": dict(d[u"rig"][u"handles"][u"Knee_l"][u"parent"], handle=d[u"rig"][u"handles"][u"rig_root"][
            u"handle"])})), u"rig-differs")
    refused("K.missing_handle_refuses", variant(lambda d: d[u"rig"][u"handles"].pop(u"Neck")), u"rig-differs")

    def weight(d):
        for op in d[u"operators"]:
            if op[u"name"] == u"ikConstraint_Foot_l":
                op[u"targets"][0][u"weight"] = {u"status": u"READ", u"value": 0.5}
    refused("K.constraint_weight_below_one_refuses", variant(weight), u"rig-differs")

    def removed_constraint(d):
        d[u"operators"] = [op for op in d[u"operators"] if op[u"name"] != u"orientConstraint_bip_neck"]
    refused("K.missing_constraint_refuses", variant(removed_constraint), u"rig-differs")

    def competing(d):
        extra = copy.deepcopy(d[u"channels"][u"bip_tail05_o"])
        extra[u"handle"] = 999999901
        d[u"channels"][u"bip_tail05_o_extra"] = extra
    refused("K.second_channel_on_a_bone_refuses", variant(competing), u"shared-authority")
    refused("K.document_wide_second_writer_refuses", variant(lambda d: d[u"writers"].update(
        {u"%d:orientation" % d[u"channels"][u"bip_tail05_o"][u"to"][u"handle"]: 2})), u"shared-authority")

    def driven_written(d):
        ch = d[u"channels"][u"bip_pelvis_p"]
        ch[u"to"] = {u"handle": d[u"bones"][u"bip_pelvis"][u"transform"], u"type": u"DmeTransform", u"name": u"x"}
        d[u"writers"][u"%d:position" % d[u"bones"][u"bip_pelvis"][u"transform"]] = 1
    refused("K.channel_on_a_constraint_driven_attribute_refuses", variant(driven_written), u"shared-authority")
    refused("K.fk_without_orientation_channel_refuses", variant(lambda d: d[u"channels"].pop(u"bip_tail05_o")),
            u"structure-unsupported")
    refused("K.passive_bone_with_a_control_refuses", variant(lambda d: d[u"channels"][u"bip_lowerArm_l_twist2_o"]
                                                             .update({u"from": dict(d[u"channels"][u"bip_tail05_o"][
                                                                 u"from"])})), u"structure-unsupported")
    refused("K.layered_channel_refuses", variant(lambda d: d[u"channels"][u"bip_tail05_o"][u"layers"].append(
        u"DmeQuaternionLogLayer")), u"structure-unsupported")
    refused("K.non_play_channel_refuses", variant(lambda d: d[u"channels"][u"Hip_p"].update({u"mode": 0})),
            u"structure-unsupported")
    def model_writer(d):
        extra = copy.deepcopy(d[u"channels"][u"Hip_p"])
        extra.update({u"handle": 999999902, u"to": {u"handle": d[u"model"][u"transform"], u"type": u"DmeTransform",
                                                    u"name": u"t"}})
        d[u"channels"][u"model_p"] = extra
        d[u"writers"][u"%d:position" % d[u"model"][u"transform"]] = 1
    refused("K.channel_on_the_model_transform_refuses", variant(model_writer), u"structure-unsupported")

    def renamed_jaw(d):
        d[u"bones"][u"jaw2"] = d[u"bones"].pop(u"jaw")
    refused("K.missing_preserved_face_bone_refuses", variant(renamed_jaw), u"rig-differs")
    check("K.refusal_details_are_logged_not_shown",
          any(u"PROD_POSE_BODY-refused" in line for line in ns["LOG"]))
    return C


# ---------------------------------------------------------------------------
# S1-B: version 2 records
# ---------------------------------------------------------------------------

def body_pose(ns, D, C, profile):
    region = ns["prod_body_payload"](D, C, profile)
    return {u"format": u"cpm-pose", u"version": 2, u"conventions": dict(ns["PROD_POSE_CONVENTIONS"]),
            u"registry": {u"profile_set": u"cpm-body-profiles", u"version": 1},
            u"source": {u"rig_class": u"krystal-v1", u"model_ref": MODEL, u"shot_name": u"shot15",
                        u"t_doc_ticks": D[u"t_doc"], u"t_shot_ticks": D[u"t_shot"]},
            u"regions": {u"full_body": region}}


def section_records(ns, reg, fx, root):
    profile = profile_of(ns, reg)
    D = fx[u"shot15"]
    C = ns["prod_body_classify"](D, profile)
    pose = body_pose(ns, D, C, profile)
    region = pose[u"regions"][u"full_body"]
    check("B.capture_saves_position_and_orientation_of_every_written_channel",
          len(region[u"positions"]) == 141 and len(region[u"orientations"]) == 137
          and u"bip_tail05_p" in region[u"positions"] and u"bip_tail05_o" in region[u"orientations"])
    check("B.capture_records_the_whole_skeleton_oracle", len(region[u"oracle"][u"bones"]) == 156)
    check("B.capture_values_are_the_native_float32_inputs",
          region[u"positions"][u"bip_tail05_p"] == [f32(c) for c in D[u"channels"][u"bip_tail05_p"][u"value"]]
          and region[u"orientations"][u"Hip_o"] == [f32(c) for c in D[u"channels"][u"Hip_o"][u"value"]])
    lib = {u"character_key": u"krystal2020", u"char_dir": os.path.join(root, u"Characters", u"krystal2020"),
           u"library_root": root, u"model_ref": MODEL}
    saved = ns["prod_pose_save_new"](lib, u"Full Body A", pose, u"20261106-120000-000000", reg)
    raw = core.read(saved[u"path"])
    check("B.v2_record_is_larger_than_the_v1_limit_and_within_its_own", 131072 < len(raw) < 4 << 20, len(raw))
    fresh, _ = registries(ns)
    record = ns["prod_pose_parse"](raw, fresh)
    check("B.independent_reload_with_a_fresh_registry_is_exact", record == saved[u"record"]
          and record[u"pose"][u"version"] == 2)
    found = ns["prod_pose_discover"](lib[u"char_dir"], u"krystal2020", fresh)
    check("B.library_lists_the_v2_pose", [i[u"name"] for i in found[u"items"]] == [u"Full Body A"]
          and not found[u"unusable"], found[u"unusable"])
    plain = ns["prod_pose_registry_parse"](core.read(core.REGISTRY_PATH), ns["PROD_POSE_REGISTRY_SHA256"])
    refused("B.v2_without_the_body_registry_is_unreadable", outcome(lambda: ns["prod_pose_parse"](raw, plain)),
            u"invalid-file")
    arm_item = ns["prod_pose_save_new"](lib, u"Arm Only", legacy_pose(ns), u"20261106-120000-000000", plain)
    arm_raw = core.read(arm_item[u"path"])
    check("B.legacy_v1_record_parses_identically_with_and_without_the_body_registry",
          ns["prod_pose_parse"](arm_raw, plain) == ns["prod_pose_parse"](arm_raw, fresh) == arm_item[u"record"])
    padded = arm_raw.rstrip(b"\n") + b" " * (140000 - len(arm_raw)) + b"\n"
    refused("B.v1_size_limit_still_applies_with_the_body_registry", outcome(lambda: ns["prod_pose_parse"](padded,
                                                                                                         fresh)),
            u"invalid-file")

    def tampered(mutate):
        r = json.loads(raw.decode("utf-8"))
        mutate(r)
        r[u"payload_sha256"] = ns["prod_pose_payload_digest"](r[u"pose"])
        return outcome(lambda: ns["prod_pose_validate"](r, fresh))
    body = lambda r: r[u"pose"][u"regions"][u"full_body"]  # noqa: E731
    refused("B.missing_written_value_refuses", tampered(lambda r: body(r)[u"positions"].pop(u"bip_tail05_p")),
            u"invalid-file")
    refused("B.extra_value_refuses", tampered(lambda r: body(r)[u"positions"].update({u"jaw_p": [0.0, 0.0, 0.0]})),
            u"invalid-file")
    refused("B.non_float32_value_refuses",
            tampered(lambda r: body(r)[u"positions"].update({u"bip_tail05_p": [0.1, 0.2, 0.3]})), u"invalid-file")
    refused("B.oracle_missing_a_bone_refuses", tampered(lambda r: body(r)[u"oracle"][u"bones"].pop(u"jaw")),
            u"invalid-file")
    refused("B.unknown_profile_refuses", tampered(lambda r: body(r).update({u"profile_id": u"body_other"})),
            u"invalid-file")
    refused("B.extra_region_refuses", tampered(lambda r: r[u"pose"][u"regions"].update({u"left_arm": {}})),
            u"invalid-file")
    r = json.loads(raw.decode("utf-8"))
    r[u"name"] = u"changed"
    refused("B.payload_digest_still_binds", outcome(lambda: ns["prod_pose_validate"](
        dict(r, pose=dict(r[u"pose"], source=dict(r[u"pose"][u"source"], shot_name=u"x"))), fresh)), u"invalid-file")
    updated = ns["prod_pose_update"](lib, saved, pose, u"20261106-130000-000000", fresh)
    check("B.update_keeps_identity_and_the_full_body_region",
          updated[u"record"][u"preset_id"] == saved[u"preset_id"] and
          sorted(updated[u"record"][u"pose"][u"regions"]) == [u"full_body"])
    check("B.parts_phrase_and_name", ns["prod_pose_parts_phrase"]([u"full_body"]) == u"Full body" and
          ns["PROD_POSE_PART_NAMES"][u"full_body"] == u"Full body" and
          ns["prod_pose_parts_phrase"]([u"left_arm"]) == u"Left arm")
    return pose, updated


def legacy_pose(ns):
    """A v1 left-arm pose from W2's accepted golden record (the stage A suite's own builder; legacy format)."""
    golden = json.loads(core.read(os.path.join(core.W2_DIR, "tests", "fixtures",
                                               "golden_left_arm_pose.f01w2.json")).decode("utf-8"))
    return copy.deepcopy(core.make_record(ns, golden, (u"left_arm",))["pose"])


# ---------------------------------------------------------------------------
# S1-C: compatibility (A1, A3, proportions) and the combined planner
# ---------------------------------------------------------------------------

def section_planner(ns, reg, fx, pose):
    profile = profile_of(ns, reg)
    region = pose[u"regions"][u"full_body"]
    D13 = fx[u"shot13"]
    C13 = ns["prod_body_classify"](D13, profile)
    live = ns["prod_body_descriptor"](D13, C13, profile)
    check("P.shot13_is_compatible_with_the_shot15_pose",
          outcome(lambda: ns["prod_body_compare_descriptor"](region[u"descriptor"], live))[0] == "ok")
    got13 = outcome(lambda: ns["prod_body_check_fk_positions"](region, D13, C13, profile))
    check("P.A1_shot13_fk_positions_match_and_are_pinned_to_the_destination",
          got13[0] == "ok" and len(got13[1]) == 124 and all(
              v == D13[u"channels"][n][u"value"] for n, v in got13[1].items()), got13[0])
    D10 = fx[u"shot10"]
    C10 = ns["prod_body_classify"](D10, profile)
    refused("P.shot10_refuses_on_scale_state", outcome(lambda: ns["prod_body_compare_descriptor"](
        region[u"descriptor"], ns["prod_body_descriptor"](D10, C10, profile))), u"proportions")
    got10 = outcome(lambda: ns["prod_body_check_fk_positions"](region, D10, C10, profile))
    check("P.A1_revised_shot10_float32_noise_is_within_the_limit_and_keeps_shot10_values",
          got10[0] == "ok" and all(v == D10[u"channels"][n][u"value"] for n, v in got10[1].items()) and
          any(v != region[u"positions"][n] for n, v in got10[1].items()), got10[0])
    check("P.A1_refusal_copy_is_the_owner_wording", ns["PROD_BODY_MESSAGES"][u"fk-position"] ==
          u"This pose uses different bone positions and can't be applied safely.")

    def moved(name, ulp=True):
        d = copy.deepcopy(D13)
        bone = d[u"bones"][name[:-2]]
        v = list(d[u"channels"][name][u"value"])
        v[1] = next_f32(v[1])
        d[u"channels"][name][u"value"] = v
        bone[u"local_position"] = list(v)
        return d
    got = outcome(lambda: ns["prod_body_check_fk_positions"](region, moved(u"bip_tail05_p"), C13, profile))
    check("P.A1_revised_one_ulp_fk_translation_is_compatible_and_pinned",
          got[0] == "ok" and got[1][u"bip_tail05_p"] != region[u"positions"][u"bip_tail05_p"], got[0])
    d = moved(u"bip_hip_l_p")
    refused("P.changed_ik_bone_offset_is_a_proportion_refusal", outcome(lambda: ns["prod_body_compare_descriptor"](
        region[u"descriptor"], ns["prod_body_descriptor"](d, C13, profile))), u"proportions")
    d = copy.deepcopy(D13)
    d[u"channels"][u"bip_lowerArm_l_twist2_o"][u"value"] = [0.0, 0.0, 0.0, 1.0]
    refused("P.A3_different_passive_twist_refuses", outcome(lambda: ns["prod_body_compare_descriptor"](
        region[u"descriptor"], ns["prod_body_descriptor"](d, C13, profile))), u"rig-differs")
    snaps = snapshots(D13, C13[u"written"])
    plans = ns["prod_body_plan"](region, D13, C13, snaps, D13[u"t_chan"])
    actions = counts(p[u"action"] for p in plans)
    check("P.matching_pose_with_missing_keys_plans_insertions_on_every_channel",
          len(plans) == 278 and actions == {u"insert": 278}, actions)
    fk_pos = [p for p in plans if C13[u"channels"][p[u"name"]] == u"fk-written" and C13[u"owners"][p[u"name"]][1] ==
              u"position"]
    check("P.A1_compatible_fk_positions_are_planned_with_their_exact_values", len(fk_pos) == 124 and all(
        p[u"value"] == region[u"positions"][p[u"name"]] for p in fk_pos))
    check("P.not_a_noop_while_keys_are_missing", ns["prod_body_noop"](plans, D13, C13, region, profile) is False)
    full = copy.deepcopy(D13)
    for p in plans:                                   # the state after the planned keys: SFM evaluates them
        ch = full[u"channels"][p[u"name"]]
        ch[u"keys"].insert(p[u"index"], [p[u"t"], list(p[u"value"])])
        ch[u"value"] = list(p[u"value"])
        owner, attr = C13[u"owners"][p[u"name"]]
        kind, _, n = owner.partition(u":")
        row = full[u"bones"][n] if kind == u"bone" else full[u"rig"][u"handles"][n]
        row[u"local_" + attr] = list(p[u"value"])
    snaps2 = snapshots(full, C13[u"written"])
    plans2 = ns["prod_body_plan"](region, full, C13, snaps2, full[u"t_chan"])
    check("P.correct_keys_are_left_unchanged", counts(p[u"action"] for p in plans2) == {u"none": 278})
    check("P.verified_repeat_is_a_noop", ns["prod_body_noop"](plans2, full, C13, region, profile) is True)
    odd = copy.deepcopy(full)
    k = odd[u"channels"][u"Hip_o"][u"keys"]
    idx = [i for i, x in enumerate(k) if x[0] == full[u"t_chan"]][0]
    k[idx][1] = [0.0, 0.0, 0.0, 1.0]
    plans3 = ns["prod_body_plan"](region, odd, C13, snapshots(odd, C13[u"written"]), odd[u"t_chan"])
    check("P.a_different_key_at_t_is_updated_in_place_only_there",
          [(p[u"name"], p[u"action"]) for p in plans3 if p[u"action"] != u"none"] == [(u"Hip_o", u"update")])
    dup = snapshots(full, C13[u"written"])
    dup[u"Hip_p"][u"times"].insert(0, full[u"t_chan"])
    dup[u"Hip_p"][u"values"].insert(0, [0.0, 0.0, 0.0])
    dup[u"Hip_p"][u"times"].sort()
    refused("P.duplicate_keys_refuse", outcome(lambda: ns["prod_body_plan"](region, full, C13, dup, full[u"t_chan"])))
    empty = snapshots(D13, C13[u"written"])
    empty[u"bip_tail05_o"].update({u"times": [], u"values": []})
    refused("P.zero_key_channel_refuses", outcome(lambda: ns["prod_body_plan"](region, D13, C13, empty,
                                                                              D13[u"t_chan"])), u"structure-unsupported")
    curve = snapshots(D13, C13[u"written"])
    curve[u"bip_tail05_o"][u"curveinfo"] = u"present"
    refused("P.curve_info_refuses", outcome(lambda: ns["prod_body_plan"](region, D13, C13, curve, D13[u"t_chan"])),
            u"structure-unsupported")
    missing = snapshots(D13, C13[u"written"])
    missing.pop(u"bip_tail05_o")
    refused("P.missing_layer_evidence_refuses", outcome(lambda: ns["prod_body_plan"](region, D13, C13, missing,
                                                                                    D13[u"t_chan"])))
    handles = dict((n, D13[u"channels"][n][u"handle"]) for n in C13[u"written"])
    authored = {u"channels": [{u"id": {u"handle": D13[u"channels"][n][u"handle"]}, u"layers": [
        {u"keys": [list(k) for k in D13[u"channels"][n][u"keys"]]}]} for n in sorted(D13[u"channels"])], u"keys": 0}
    exp = ns["prod_body_expected_authored"](authored, plans, handles)
    changed = [row for row, was in zip(exp[u"channels"], authored[u"channels"]) if row != was]
    check("P.one_combined_expected_state_changes_exactly_the_planned_channels",
          len(changed) == 278 and exp[u"keys"] == 278)
    expected = ns["prod_body_expected_skeleton"](region, D13, C13, profile)
    check("P.expected_skeleton_verifies_on_the_identical_posture",
          not ns["prod_body_verify_skeleton"](D13, D13, expected, C13, profile))
    expected10 = ns["prod_body_expected_skeleton"](region, D10, C10, profile)
    problems = ns["prod_body_verify_skeleton"](D10, D10, expected10, C10, profile)
    check("P.expected_skeleton_detects_a_different_posture", len(problems) > 20, len(problems))



# ---------------------------------------------------------------------------
# S1-D: capture and the combined P1-P7 transaction on the fake native scene (fake_sfm_body.py)
# ---------------------------------------------------------------------------

IDENTITY = {"model": MODEL, "checksum": 1234, "animset_name": u"Krystal"}
WRITTEN_HANDLES = set()


class Pin(object):
    world = None
    session = u"session-1"
    valid = [True]


def live_namespace(app):
    ns = build_namespace(app)

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


def use_world(ns, world):
    sfm, vs = world.modules()
    ns["sfmApp"], ns["vs"] = sfm, vs
    Pin.world = world


def live_context(ns):
    token = {"kind": ns["PROD_INSTANCE_TOKEN_KIND"], "session": Pin.session, "shot": u"pinned"}
    return {"instance": token, "library_identity": dict(IDENTITY)}


def authorize(ns, reg, label, item=None, mode=u"qualification"):
    return ns["prod_pose_authorize"](live_context(ns), IDENTITY, reg, mode, label, item)


def scene_writes(world):
    return [c for c in world.calls if c[0] in ("SetKeyValue", "InsertKeyAtTime")]


def all_keys(world):
    return dict((n, world.keys(n)) for n in world.channels)


def rotate(q, axis, degrees):
    h = math.radians(degrees) / 2.0
    r = [axis[0] * math.sin(h), axis[1] * math.sin(h), axis[2] * math.sin(h), math.cos(h)]
    return list(FB.qnorm(FB.qmul(r, q)))


TOUCHED_FK = (u"tail", u"Ear", u"index")


def pose_differently(world):
    """A distinctly posed destination: every written handle and many FK bones turned or moved (FK bone positions are
    never touched: A1), the placement moved and turned, and the preserved jaw opened."""
    for name, ch in world.channels.items():
        layer = ch.attrs["log"].layer
        if not layer.keys or layer.value_kind is None:
            continue
        fk = name.endswith(u"_o") and (any(t in name for t in TOUCHED_FK) or name == u"jaw_o")
        if not (name in WRITTEN_HANDLES or fk or name in (u"rig_root_p", u"rig_root_o")):
            continue
        for k in layer.keys:
            v = FB.plain(k[1])
            if layer.value_kind == "quat":
                if name == u"rig_root_o":
                    v = rotate(v, [0.0, 0.0, 1.0], 30.0)
                else:
                    v = rotate(v, [1.0, 0.0, 0.0], 25.0)
            elif name == u"rig_root_p":
                v = [v[0] + 60.0, v[1] + 25.0, v[2]]
            else:
                v = [v[0] + 1.5, v[1] - 1.0, v[2]]
            k[1] = FB.native(v, layer.value_kind)
    world.evaluate()


def placement_relative(world, root_name=u"rig_root"):
    root = world.handle_dag[root_name]
    return dict((n, FB.to_local((root.wp, root.wq), (dag.wp, dag.wq))) for n, dag in world.bone_dag.items())


def max_difference(a, b, names=None):
    names = names or list(a)
    dp = max(math.sqrt(sum((x - y) ** 2 for x, y in zip(a[n][0], b[n][0]))) for n in names)
    dq = max(math.degrees(2 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(a[n][1], b[n][1]))))))
             for n in names)
    return dp, dq


PRESERVED_CHANNELS = (u"rig_root_p", u"rig_root_o", u"jaw_o", u"tongue03_o", u"viewTarget_pos", u"Elbow_l_o",
                      u"Knee_r_o", u"bip_lowerArm_l_twist2_o", u"bip_head_scale", u"A_flex_channel",
                      u"Kiss_flex_channel", u"eyes_updown_flex_channel")


def section_live(ns, reg, fx, root):
    profile = profile_of(ns, reg)
    WRITTEN_HANDLES.update(profile[u"written_handle_channels"])
    if not os.path.isdir(root):
        os.makedirs(root)
    lib = {u"character_key": u"krystal2020", u"char_dir": os.path.join(root, u"Characters", u"krystal2020"),
           u"library_root": root, u"model_ref": MODEL}
    # Process A: capture shot15's Krystal.
    src = FB.World(fx[u"shot15"])
    use_world(ns, src)
    auth = authorize(ns, reg, u"Save Pose")
    head_before = src.head
    pinned = ns["prod_body_current_time"](IDENTITY, auth, reg)
    pose = ns["prod_body_capture"](IDENTITY, auth, reg, pinned_time=pinned)
    check("L.capture_is_read_only", not scene_writes(src) and not src.dm.calls and src.head == head_before)
    region = pose[u"regions"][u"full_body"]
    check("L.capture_saves_the_live_position_and_orientation_values",
          region[u"positions"][u"bip_tail05_p"] == src.keys(u"bip_tail05_p")[0][1] and
          region[u"orientations"][u"bip_tail05_o"] == src.keys(u"bip_tail05_o")[0][1] and
          len(region[u"positions"]) == 141 and len(region[u"orientations"]) == 137)
    row = ns["prod_resolve_instance"](live_context(ns)["instance"])
    live_D = ns["prod_body_discover"](ns["prod_body_live"](row, profile), fx[u"shot15"][u"t_chan"],
                                      ns["prod_pose_writer_index"]())
    check("L.live_discovery_classifies_as_the_native_fixture",
          ns["prod_body_classify"](live_D, profile)[u"channels"] ==
          ns["prod_body_classify"](fx[u"shot15"], profile)[u"channels"])
    saved = ns["prod_pose_save_new"](lib, u"Full Body A", pose, u"20261106-120000-000000", reg)
    src.timeline_mode = 3
    refused("L.clip_editor_capture_refuses_on_channel_clocks",
            outcome(lambda: ns["prod_body_capture"](IDENTITY, auth, reg)), u"capture-clock")
    src.timeline_mode = 2
    prod_auth = authorize(ns, reg, u"Save Pose", mode=u"production")
    refused("L.production_build_has_no_full_body_save_until_qualified",
            outcome(lambda: ns["prod_body_capture"](IDENTITY, prod_auth, reg)), u"not-qualified")
    refused("L.capture_with_a_moved_playhead_is_stale", outcome(lambda: ns["prod_body_capture"](
        IDENTITY, auth, reg, pinned_time=dict(pinned, t_chan=pinned[u"t_chan"] + 1))), u"stale")
    source_relative = placement_relative(src)

    # Process B: a new process and another instance (shot13), distinctly posed and placed.
    fresh, _ = registries(ns)
    item = [i for i in ns["prod_pose_discover"](lib[u"char_dir"], u"krystal2020", fresh)[u"items"]
            if i[u"preset_id"] == saved[u"preset_id"]][0]
    check("L.process_b_reloads_the_record_independently", item[u"record"] == saved[u"record"])
    dst = FB.World(fx[u"shot13"])
    pose_differently(dst)
    use_world(ns, dst)
    dp, dq = max_difference(placement_relative(dst), source_relative)
    check("L.destination_is_distinctly_posed_before_apply", dq > 10.0, (dp, dq))
    before = all_keys(dst)
    model_world = (list(dst.gm.wp), list(dst.gm.wq))
    jaw_local = dst.local(dst.bone_dag[u"jaw"])
    auth = authorize(ns, fresh, u"Apply Pose", item)
    result = ns["prod_body_apply"](IDENTITY, auth, item, fresh)
    check("L.apply_commits_and_defers_verification", result[u"phase"] == u"verification-pending", result.get(u"phase"))
    undo_calls = [c[0] for c in dst.dm.calls]
    check("L.one_owned_undo_transaction", undo_calls == ["StartUndo", "FinishUndo"] and len(dst.dm.stack) == 1 and
          dst.dm.stack[0]["label"] == u"Apply Pose Full Body A", undo_calls)
    inserted = [c for c in scene_writes(dst) if c[0] == "InsertKeyAtTime"]
    check("L.every_written_channel_keyed_once_by_insertion_including_fk_positions",
          len(inserted) == 278 and len(set(c[1] for c in inserted)) == 278, len(inserted))
    check("L.refresh_requested_once_outside_the_transaction",
          [r["in_undo"] for r in dst.refresh_calls] == [False], dst.refresh_calls)
    verdict = ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
    check("L.deferred_whole_skeleton_verification_passes", verdict.get(u"phase") == u"committed-verified", verdict)
    now = placement_relative(dst)
    posed = [n for n in source_relative if n != u"jaw" and not n.startswith(u"tongue")]
    dpp, dqp = max_difference(now, source_relative, posed)
    check("L.destination_takes_the_source_posture_in_its_own_placement", dpp < 1e-3 and dqp < 0.01, (dpp, dqp))
    after = all_keys(dst)
    C13 = ns["prod_body_classify"](fx[u"shot13"], profile)
    planned = sorted(n for n, r in C13[u"channels"].items() if r in (u"handle-written", u"fk-written"))
    check("L.only_planned_channels_changed", sorted(n for n in after if after[n] != before[n]) == planned)
    check("L.placement_face_gaze_scale_poles_and_twist_preserved",
          all(after[n] == before[n] for n in PRESERVED_CHANNELS) and
          (list(dst.gm.wp), list(dst.gm.wq)) == model_world and dst.local(dst.bone_dag[u"jaw"]) == jaw_local and
          dst.scale(dst.bone_dag[u"bip_head"]) == float(fx[u"shot13"][u"bones"][u"bip_head"][u"scale"][u"value"]))
    dst.dm.Undo()
    check("L.undo_restores_the_whole_baseline", all_keys(dst) == before)
    dst.dm.Redo()
    check("L.redo_reapplies_the_whole_pose", all_keys(dst) == after)
    calls = len(dst.calls)
    auth = authorize(ns, fresh, u"Apply Pose", item)
    again = ns["prod_body_apply"](IDENTITY, auth, item, fresh)
    check("L.verified_repeat_apply_is_a_noop", again == {u"phase": u"no-op"} and len(dst.calls) == calls and
          len(dst.dm.stack) == 1, again)
    return fresh, item


def apply_fresh(ns, reg, fx, item, prepare=None, name=u"shot13"):
    world = FB.World(fx[name])
    pose_differently(world)
    if prepare is not None:
        prepare(world)
        world.evaluate()
    use_world(ns, world)
    auth = authorize(ns, reg, u"Apply Pose", item)
    return world, auth, outcome(lambda: ns["prod_body_apply"](IDENTITY, auth, item, reg))


def section_live_refusals(ns, reg, fx, item):
    def ulp(world):
        layer = world.channels[u"bip_tail05_p"].attrs["log"].layer
        v = FB.plain(layer.keys[0][1])
        layer.keys[0][1] = FB.native([v[0], v[1] + 0.001, v[2]], "vec")      # beyond the revised limit
    world, _, got = apply_fresh(ns, reg, fx, item, ulp)
    refused("L.A1_fk_position_beyond_the_limit_refuses", got, u"fk-position")
    check("L.A1_refusal_changes_nothing_and_opens_no_undo", not scene_writes(world) and not world.dm.calls and
          got[2] == u"This pose uses different bone positions and can't be applied safely.", got)
    world, _, got = apply_fresh(ns, reg, fx, item, lambda w: setattr(w, "timeline_mode", 3))
    refused("L.clip_editor_apply_refuses_before_any_write", got, u"editor-mode")
    check("L.editor_refusal_writes_nothing", not scene_writes(world) and not world.dm.calls)

    def zero_keys(world):
        world.channels[u"bip_tail05_o"].attrs["log"].layer.keys = []
    world, _, got = apply_fresh(ns, reg, fx, item, zero_keys)
    refused("L.zero_key_written_channel_refuses", got)        # unreadable value at t, before any plan
    check("L.zero_key_refusal_writes_nothing", not scene_writes(world) and not world.dm.calls)

    def duplicate(world):
        layer = world.channels[u"bip_tail06_o"].attrs["log"].layer
        t = world.t_chan()
        layer.keys.append([t, copy.deepcopy(layer.keys[0][1])])
        layer.keys.append([t, copy.deepcopy(layer.keys[0][1])])
    world, _, got = apply_fresh(ns, reg, fx, item, duplicate)
    refused("L.duplicate_keys_at_the_mapped_tick_refuse", got, u"structure-unsupported")
    check("L.structure_refusals_write_nothing", not scene_writes(world) and not world.dm.calls)

    def unknown_operator(world):
        op = FB.Element(world, world.new_handle(), "DmeRigAimConstraintOperator", "aim")
        world.animset.attrs["operators"].items.append(op)
    world, _, got = apply_fresh(ns, reg, fx, item, unknown_operator)
    refused("L.unknown_operator_refuses", got, u"structure-unsupported")

    def second_layer(world):
        log = world.channels[u"bip_tail07_o"].attrs["log"]
        log.extra_layers.append(FB.Layer(world, world.new_handle(), "DmeQuaternionLogLayer", [], "quat"))
    world, _, got = apply_fresh(ns, reg, fx, item, second_layer)
    refused("L.layered_channel_refuses", got, u"structure-unsupported")

    # P1 -> P2: a change after the plan refuses before the transaction.
    world = FB.World(fx[u"shot13"])
    pose_differently(world)
    use_world(ns, world)
    auth = authorize(ns, reg, u"Apply Pose", item)
    original = ns["prod_body_preflight"]

    def preflight_then_edit(*args):
        pre = original(*args)
        world.channels[u"A_flex_channel"].attrs["log"].layer.keys.append([world.t_chan() + 7, 0.5])
        return pre
    ns["prod_body_preflight"] = preflight_then_edit
    try:
        got = outcome(lambda: ns["prod_body_apply"](IDENTITY, auth, item, reg))
    finally:
        ns["prod_body_preflight"] = original
    refused("L.revalidation_between_p1_and_p2_refuses", got, u"stale")
    check("L.revalidation_refusal_opens_no_undo", not world.dm.calls and not scene_writes(world))

    # A late-channel failure: Abort, then the whole operation verified unchanged.
    last = sorted(n for n, r in ns["prod_body_classify"](fx[u"shot13"], profile_of(ns, reg))[u"channels"].items()
                  if r in (u"handle-written", u"fk-written"))[-1]
    world = FB.World(fx[u"shot13"])
    pose_differently(world)
    use_world(ns, world)
    before = all_keys(world)
    auth = authorize(ns, reg, u"Apply Pose", item)
    world.fail_on_write = last
    got = outcome(lambda: ns["prod_body_apply"](IDENTITY, auth, item, reg))
    check("L.late_channel_failure_aborts_the_whole_operation",
          got[0] == "ok" and got[1][u"phase"] == u"not-applied" and
          [c[0] for c in world.dm.calls] == ["StartUndo", "AbortUndoableOperation"] and len(scene_writes(world)) > 270,
          (got[0], [c[0] for c in world.dm.calls], len(scene_writes(world))))
    check("L.abort_restores_every_key_and_leaves_no_undo_entry", all_keys(world) == before and not world.dm.stack)
    check("L.abort_restoration_is_verified_and_logged", any(u"BODY-abort-verified" in l for l in ns["LOG"]))
    world = FB.World(fx[u"shot13"])
    pose_differently(world)
    use_world(ns, world)
    auth = authorize(ns, reg, u"Apply Pose", item)
    world.fail_on_write = last
    world.abort_raises = True
    got = outcome(lambda: ns["prod_body_apply"](IDENTITY, auth, item, reg))
    check("L.failed_abort_is_recovery_unverified", got[0] == "ProdRecoveryUnverifiedError", got)

    # P7: authorized descendant motion verifies; an unrelated change does not.
    world = FB.World(fx[u"shot13"])
    pose_differently(world)
    use_world(ns, world)
    auth = authorize(ns, reg, u"Apply Pose", item)
    result = ns["prod_body_apply"](IDENTITY, auth, item, reg)
    world.channels[u"Kiss_flex_channel"].attrs["log"].layer.keys.append([world.t_chan() + 3, 0.25])
    verdict = ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
    check("L.p7_detects_an_unrelated_change", verdict.get(u"phase") == u"committed-unverified", verdict)
    world = FB.World(fx[u"shot13"])
    pose_differently(world)
    use_world(ns, world)
    world.evaluate_on_refresh = False
    auth = authorize(ns, reg, u"Apply Pose", item)
    result = ns["prod_body_apply"](IDENTITY, auth, item, reg)
    pending = dict(result[u"pending"], authorization=auth)
    verdict = ns["prod_pose_deferred_verify"](pending)
    check("L.p7_before_evaluation_is_committed_unverified", verdict.get(u"phase") == u"committed-unverified", verdict)
    world.evaluate()
    verdict = ns["prod_pose_deferred_verify"](pending)
    check("L.p7_after_evaluation_verifies_descendant_motion", verdict.get(u"phase") == u"committed-verified", verdict)
    world.dm.push_foreign(u"Move Control")
    verdict = ns["prod_pose_deferred_verify"](pending)
    check("L.p7_with_a_foreign_undo_entry_is_unverified", verdict.get(u"phase") == u"committed-unverified", verdict)
    world, _, got = apply_fresh(ns, reg, fx, item, name=u"shot10")
    refused("L.incompatible_instance_refuses_before_any_write", got, u"proportions")
    check("L.incompatible_refusal_writes_nothing", not scene_writes(world) and not world.dm.calls)



# ---------------------------------------------------------------------------
# S1-E: the Poses window methods (Save New, Update Pose, Apply Pose) on the fake scene
# ---------------------------------------------------------------------------

WINDOW_METHODS = ["pose_registry_mode", "pose_guard", "apply_pose", "save_pose", "update_pose"]


class FakeWindow(object):
    """The ProdWindow seams the pose methods call (guard, lifecycle, prompts, status); the methods are real."""

    def __init__(self, context):
        self.identity = dict(IDENTITY)
        self.operation = {"context": context, "operation_id": 1, "generation": 1}
        self.statuses, self.pending, self.prompts, self.confirm = [], [], [], True
        self.pose_recovery_blocked = False

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
    ns["p03_now_stamp"] = lambda: u"20261106-140000-000000"
    ns["tool_status_name"] = lambda n: n
    return FakeWindow(live_context(ns))


def section_window(app, ns, reg, fx, root):
    profile = profile_of(ns, reg)
    WRITTEN_HANDLES.update(profile[u"written_handle_channels"])
    os.makedirs(root)
    lib = {u"character_key": u"krystal2020", u"char_dir": os.path.join(root, u"Characters", u"krystal2020"),
           u"library_root": root, u"model_ref": MODEL, u"checksum": 1234}
    src = FB.World(fx[u"shot15"])
    use_world(ns, src)
    win = window(app, ns, reg, lib)
    check("W.save_new_button_creates_complete_poses_only",
          u'self.save_pose(None, (u"full_body",))' in u"\n".join(
              app.method_text("ProdWindow", m) for m in app.methods("ProdWindow")) and
          u'self.save_pose(None, (u"left_arm",))' not in u"\n".join(
              app.method_text("ProdWindow", m) for m in app.methods("ProdWindow")))
    mode = ns["PROD_POSE_REGISTRY_MODE"]
    check("W.shipped_build_is_production", mode == u"production")
    win.prompts = [u"Window Pose"]
    got = win.save_pose(None, (u"full_body",))
    check("W.production_save_new_refuses_until_full_body_is_qualified",
          got is None and win.statuses[-1][2] == u"not-qualified" and
          win.statuses[-1][3] == u"Full-body poses aren't available for this character yet." and
          not os.path.isdir(os.path.join(lib[u"char_dir"], u"Poses")), win.statuses[-1])
    ns["PROD_POSE_REGISTRY_MODE"] = u"qualification"            # the separately built qualification CPM
    try:
        win.prompts = [u"Window Pose"]
        saved = win.save_pose(None, (u"full_body",))
        check("W.save_new_saves_a_version_2_complete_pose", saved is not None and
              saved[u"record"][u"pose"][u"version"] == 2 and
              sorted(saved[u"record"][u"pose"][u"regions"]) == [u"full_body"] and
              win.statuses[-1][1] == u"Pose saved: Window Pose.", win.statuses[-1])
        check("W.save_new_writes_nothing_to_the_scene", not scene_writes(src) and not src.dm.calls)
        src.timeline_mode = 3
        win.prompts = [u"Clip Pose"]
        win.save_pose(None, (u"full_body",))
        check("W.clip_editor_save_refuses_with_the_clock_copy", win.statuses[-1][2] == u"capture-clock" and
              win.statuses[-1][3] == u"Switch to the Motion Editor and try again.", win.statuses[-1])
        src.timeline_mode = 2
        # Apply in another instance, distinctly posed.
        dst = FB.World(fx[u"shot13"])
        pose_differently(dst)
        use_world(ns, dst)
        item = ns["prod_pose_reread"](lib, saved, reg)
        win.apply_pose(item)
        check("W.apply_pose_runs_the_full_body_transaction", len(win.pending) == 1 and win.pending[0].get(u"body")
              and [c[0] for c in dst.dm.calls] == ["StartUndo", "FinishUndo"], win.statuses[-1:])
        verdict = ns["prod_pose_deferred_verify"](win.pending[0])
        check("W.deferred_turn_verifies_the_full_body_pose", verdict.get(u"phase") == u"committed-verified", verdict)
        check("W.status_parts_phrase_is_full_body", ns["prod_pose_parts_phrase"](win.pending[0][u"regions"]) ==
              u"Full body")
        # FK position mismatch: the Owner's wording, nothing written.
        bad = FB.World(fx[u"shot13"])
        layer = bad.channels[u"bip_tail05_p"].attrs["log"].layer
        v = FB.plain(layer.keys[0][1])
        layer.keys[0][1] = FB.native([v[0], v[1] + 0.001, v[2]], "vec")      # beyond the revised limit
        bad.evaluate()
        use_world(ns, bad)
        win.apply_pose(item)
        check("W.fk_position_mismatch_shows_the_owner_wording", win.statuses[-1][2] == u"fk-position" and
              win.statuses[-1][3] == u"This pose uses different bone positions and can't be applied safely." and
              not scene_writes(bad), win.statuses[-1])
        # Update Pose: a complete recapture of the same record.
        use_world(ns, src)
        layer = src.channels[u"Hip_o"].attrs["log"].layer
        for k in layer.keys:
            k[1] = FB.native(rotate(FB.plain(k[1]), [0.0, 1.0, 0.0], 15.0), "quat")
        src.evaluate()
        win.confirm = False
        got = win.update_pose(item)
        check("W.cancelled_update_changes_nothing", got is None and
              ns["prod_pose_reread"](lib, item, reg)[u"revision"] == item[u"revision"])
        win.confirm = True
        updated = win.update_pose(item)
        check("W.update_pose_recaptures_the_complete_pose_in_place", updated is not None and
              updated[u"preset_id"] == item[u"preset_id"] and updated[u"path"] == item[u"path"] and
              updated[u"record"][u"pose"][u"regions"][u"full_body"][u"orientations"][u"Hip_o"] !=
              item[u"record"][u"pose"][u"regions"][u"full_body"][u"orientations"][u"Hip_o"] and
              win.statuses[-1][1] == u"Pose updated: Window Pose.", win.statuses[-1])
        check("W.update_writes_nothing_to_the_scene", not scene_writes(src) and not src.dm.calls)
        # A legacy version 1 left-arm pose keeps the stage D Apply.
        legacy = ns["prod_pose_save_new"](lib, u"Legacy Arm", legacy_pose(ns), u"20261106-150000-000000", reg)
        calls = []
        real = ns["prod_pose_apply"]
        ns["prod_pose_apply"] = lambda *a, **k: calls.append(a[2][u"record"][u"pose"][u"version"]) or {
            u"phase": u"no-op"}
        try:
            win.apply_pose(ns["prod_pose_reread"](lib, legacy, reg))
        finally:
            ns["prod_pose_apply"] = real
        check("W.legacy_v1_apply_uses_the_left_arm_path", calls == [1], calls)
        check("W.ui_state_save_new_needs_a_usable_full_body_mapping",
              ns["prod_pose_ui_state"]({u"character": u"Krystal", u"supported": True, u"instance_valid": True,
                                        u"save_available": False})[u"buttons"][u"save_new"] is False and
              ns["prod_pose_ui_state"]({u"character": u"Krystal", u"supported": True, u"instance_valid": True,
                                        u"save_available": True})[u"buttons"][u"save_new"] is True and
              ns["prod_pose_ui_state"]({u"character": u"Krystal", u"supported": True,
                                        u"instance_valid": True})[u"buttons"][u"save_new"] is True)
    finally:
        ns["PROD_POSE_REGISTRY_MODE"] = mode



# ---------------------------------------------------------------------------
# Astra S1 corrections: the reviewer's counterexamples (X.1 ... X.12)
# ---------------------------------------------------------------------------

def foreign_channel(world, log, name=u"foreign_channel"):
    """An unrelated channel in another channels clip of the shot, reading the given log."""
    clip = FB.Clip(world, world.new_handle(), "DmeChannelsClip", "Other", offset=0, start=0, end=10 ** 7,
                   channels=FB.ElementArray(world, []))
    track = world.shot.attrs["trackGroups"].items[0].attrs["tracks"].items[0]
    track.attrs["children"].items.append(clip)
    target = FB.Element(world, world.new_handle(), "DmeTransform", "other", position=FB.Vector())
    ch = FB.Channel(world, world.new_handle(), "DmeChannel", name, fromElement=None, fromAttribute=u"",
                    toElement=target, toAttribute=u"position", mode=3, fromIndex=0, toIndex=0, log=log)
    clip.attrs["channels"].items.append(ch)
    return ch


def external_constraint(world, bone=u"bip_tail05"):
    """An orient constraint in another animation set of the shot, driving one of Krystal's bones."""
    prop_t = FB.Element(world, world.new_handle(), "DmeTransform", "prop", position=FB.Vector(),
                        orientation=FB.Quaternion())
    prop = FB.Dag(world, world.new_handle(), "DmeDag", "prop", prop_t)
    slave = FB.Element(world, world.new_handle(), "DmeConstraintSlave", "unnamed", target=world.bone_dag[bone],
                       position=FB.Vector(), orientation=FB.Quaternion())
    target = FB.Element(world, world.new_handle(), "DmeConstraintTarget", "prop", target=prop, targetWeight=1.0)
    op = FB.Element(world, world.new_handle(), "DmeRigOrientConstraintOperator", "orientConstraint_prop",
                    slave=slave, targets=FB.ElementArray(world, [target]))
    other = FB.Element(world, world.new_handle(), "DmeAnimationSet", "Prop", operators=FB.ElementArray(world, [op]),
                       controls=FB.ElementArray(world, []))
    world.shot.attrs["animationSets"].items.append(other)
    return op


def posed_destination(ns, fx, prepare=None):
    world = FB.World(fx[u"shot13"])
    pose_differently(world)
    if prepare is not None:
        prepare(world)
    use_world(ns, world)
    return world


def transform_state(world):
    return dict((n, (FB.plain(d.attrs["transform"].attrs["position"]), FB.plain(d.attrs["transform"].attrs[
        "orientation"]))) for n, d in list(world.bone_dag.items()) + list(world.handle_dag.items()))


def no_mutation(world):
    return not scene_writes(world) and not world.dm.calls


def section_corrections(app, ns, reg, fx, item, lib):
    apply_ = lambda world: outcome(lambda: ns["prod_body_apply"](  # noqa: E731
        IDENTITY, authorize(ns, reg, u"Apply Pose", item), item, reg))

    # X.1 shared log or layer
    world = posed_destination(ns, fx, lambda w: foreign_channel(w, w.channels[u"Hip_o"].attrs["log"]))
    got = apply_(world)
    refused("X.1a_unrelated_channel_sharing_a_planned_log_refuses", got, u"shared-authority")
    check("X.1a_no_mutation", no_mutation(world))

    def shared_layer(w):
        layer = w.channels[u"bip_tail05_o"].attrs["log"].layer
        foreign_channel(w, FB.Log(w, w.new_handle(), "DmeQuaternionLog", layer))
    world = posed_destination(ns, fx, shared_layer)
    got = apply_(world)
    refused("X.1b_unrelated_log_sharing_a_planned_layer_refuses", got, u"shared-authority")
    check("X.1b_no_mutation", no_mutation(world))
    # X.2 external constraint
    world = posed_destination(ns, fx, lambda w: external_constraint(w))
    got = apply_(world)
    refused("X.2_constraint_outside_the_animation_set_refuses", got, u"shared-authority")
    check("X.2_no_mutation", no_mutation(world))
    world = posed_destination(ns, fx, lambda w: external_constraint(w, u"bip_pelvis"))
    refused("X.2b_external_constraint_on_a_constrained_bone_refuses", apply_(world), u"shared-authority")
    # X.3 a newly conflicting authority after commit prevents verified success
    for label, conflict in ((u"shared_log", lambda w: foreign_channel(w, w.channels[u"Hip_o"].attrs["log"])),
                            (u"external_constraint", lambda w: external_constraint(w))):
        world = posed_destination(ns, fx)
        auth = authorize(ns, reg, u"Apply Pose", item)
        result = ns["prod_body_apply"](IDENTITY, auth, item, reg)
        calls = list(world.dm.calls)
        conflict(world)
        verdict = ns["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
        check("X.3_%s_after_commit_is_committed_unverified" % label,
              verdict.get(u"phase") == u"committed-unverified" and world.dm.calls == calls and
              len(world.dm.stack) == 1, (verdict, world.dm.calls[len(calls):]))
    # X.4 a one-float32-step evaluated FK change between P1 and P2 refuses (keys unchanged)
    world = posed_destination(ns, fx)
    original = ns["prod_body_preflight"]

    def preflight_then_nudge(*args):
        pre = original(*args)
        t = world.bone_dag[u"bip_tail05"].attrs["transform"]
        v = FB.plain(t.attrs["position"])
        t.set("position", FB.Vector(v[0], next_f32(v[1]), v[2]))
        return pre
    ns["prod_body_preflight"] = preflight_then_nudge
    try:
        got = apply_(world)
    finally:
        ns["prod_body_preflight"] = original
    refused("X.4_one_ulp_fk_position_change_between_p1_and_p2_refuses", got, u"stale")
    check("X.4_no_mutation_and_a_logged_a1_recheck", no_mutation(world) and any(
        u"evaluated state refused: evidence-unreadable" in l for l in ns["LOG"][-5:]))
    # X.5 effective-position or channel-evaluation inconsistency refuses at P1
    for name, attr in ((u"Hip", "position"), (u"Hip", "orientation"), (u"bip_tail06", "position")):
        def skew(w, name=name, attr=attr):
            dag = w.handle_dag.get(name) or w.bone_dag[name]
            t = dag.attrs["transform"]
            v = FB.plain(t.attrs[attr])
            t.set(attr, FB.Vector(v[0] + 0.25, v[1], v[2]) if attr == "position" else
                  FB.Quaternion(*rotate(v, [0.0, 0.0, 1.0], 5.0)))
        world = FB.World(fx[u"shot13"])
        pose_differently(world)
        skew(world)                                   # after evaluation: the transform no longer matches its channel
        use_world(ns, world)
        got = apply_(world)
        check("X.5_%s_%s_inconsistent_with_its_channel_refuses" % (name, attr), got[0] != "ok" and
              got[1] in (u"evidence-unreadable", u"fk-position") and no_mutation(world), got)
    # X.6 disabled Undo prevents mutation
    world = posed_destination(ns, fx, lambda w: setattr(w, "undo_enabled", False))
    got = apply_(world)
    refused("X.6_disabled_undo_refuses_before_any_mutation", got, u"evidence-unreadable")
    check("X.6_no_mutation", no_mutation(world))
    check("X.6_shared_validator_rejects_disabled_undo", ns["prod_pose_undo_problems"](
        {u"enabled": False, u"can_undo": False, u"can_redo": False, u"undo_desc": u"", u"redo_desc": u""}) ==
        [u"enabled (Undo is disabled)"] and ns["prod_pose_undo_problems"](
        {u"enabled": True, u"can_undo": False, u"can_redo": False, u"undo_desc": u"", u"redo_desc": u""}) == [])
    # X.7 StartUndo: a refusal before it is plain; a failure of StartUndo itself fails closed
    world = posed_destination(ns, fx)
    original_same = ns["prod_body_same_state"]

    def same_then_foreign(*args):
        problems = original_same(*args)
        world.dm.push_foreign(u"Move Control")        # the Undo history changes after P2, before StartUndo
        return problems
    ns["prod_body_same_state"] = same_then_foreign
    try:
        got = apply_(world)
    finally:
        ns["prod_body_same_state"] = original_same
    refused("X.7a_change_just_before_start_undo_is_a_plain_refusal", got, u"stale")
    check("X.7a_start_undo_never_called_no_writes", not scene_writes(world) and
          not [c for c in world.dm.calls if c[0] == "StartUndo"])
    for when in ("before", "after"):
        world = posed_destination(ns, fx, lambda w, when=when: setattr(w, "start_raises", when))
        got = apply_(world)
        check("X.7b_start_undo_failure_%s_opening_fails_closed" % when,
              got[0] == "ProdRecoveryUnverifiedError" and not scene_writes(world) and
              [c[0] for c in world.dm.calls] == ["StartUndo"], (got, world.dm.calls))
    check("X.7c_an_opened_transaction_is_never_aborted_or_claimed_not_applied",
          world.dm.current is not None and not [c for c in world.dm.calls if c[0] == "AbortUndoableOperation"])
    # X.8 FinishUndo before and after commitment stays conservative
    world = posed_destination(ns, fx, lambda w: setattr(w, "finish_raises", "before"))
    got = apply_(world)
    check("X.8a_finish_undo_failure_before_commit_is_recovery_unverified",
          got[0] == "ProdRecoveryUnverifiedError" and not [c for c in world.dm.calls if c[0] ==
                                                           "AbortUndoableOperation"], got)
    world = posed_destination(ns, fx, lambda w: setattr(w, "finish_raises", "after"))
    auth = authorize(ns, reg, u"Apply Pose", item)
    got = outcome(lambda: ns["prod_body_apply"](IDENTITY, auth, item, reg))
    # Astra S1 final: a FinishUndo exception never hands over to P7 (was: verification-pending, then P7
    # committed-unverified). Section Y covers the reproduced counterexample.
    check("X.8b_finish_undo_failure_after_commit_is_recovery_unverified",
          got[0] == "ProdRecoveryUnverifiedError" and
          not [x for x in world.dm.calls if x[0] == "AbortUndoableOperation"], got)
    # X.9 the qualification-build injected fault, through ProdWindow.pose_guard
    win = window(app, ns, reg, lib)
    mode = ns["PROD_POSE_REGISTRY_MODE"]
    ns["PROD_POSE_REGISTRY_MODE"] = u"qualification"
    try:
        world = posed_destination(ns, fx)
        before = all_keys(world)
        ns["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
        win.apply_pose(item)
        check("X.9a_injected_fault_aborts_and_verifies_through_pose_guard",
              win.statuses[-1][1] == ns["PROD_POSE_MESSAGES"][u"not-applied"] and all_keys(world) == before and
              not world.dm.stack and not win.pose_recovery_blocked, win.statuses[-1])
        world = posed_destination(ns, fx, lambda w: setattr(w, "abort_raises", True))
        ns["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
        win.apply_pose(item)
        check("X.9b_failed_abort_sets_the_pose_guard_recovery_lockout", win.pose_recovery_blocked is True and
              win.statuses[-1][0] == "error", win.statuses[-1])
        world = posed_destination(ns, fx)
        win.apply_pose(item)
        check("X.9c_lockout_refuses_every_later_pose_operation_without_mutation",
              win.statuses[-1][2] == u"recovery-blocked" and no_mutation(world), win.statuses[-1])
    finally:
        ns["PROD_POSE_REGISTRY_MODE"] = mode
        ns["PROD_POSE_QUAL_FAULT"][0] = None
    # X.10 a late-operation Abort restores the complete baseline (keys and evaluated transforms)
    last = sorted(n for n, r in ns["prod_body_classify"](fx[u"shot13"], profile_of(ns, reg))[u"channels"].items()
                  if r in (u"handle-written", u"fk-written"))[-1]
    world = posed_destination(ns, fx)
    keys0, transforms0 = all_keys(world), transform_state(world)
    world.fail_on_write = last
    got = apply_(world)
    check("X.10_late_abort_restores_keys_transforms_and_undo", got[0] == "ok" and
          got[1][u"phase"] == u"not-applied" and all_keys(world) == keys0 and transform_state(world) == transforms0
          and not world.dm.stack and world.dm.current is None, got)
    # X.11 bindings are resolved once per comparison phase
    counter = []
    real = ns["prod_body_bindings"]
    ns["prod_body_bindings"] = lambda *a: counter.append(1) or real(*a)
    try:
        world = posed_destination(ns, fx)
        auth = authorize(ns, reg, u"Apply Pose", item)
        pre = ns["prod_body_preflight"](IDENTITY, auth, item, reg)
        del counter[:]
        problems = ns["prod_body_same_state"](IDENTITY, auth, pre)
        one = len(counter)
        del counter[:]
        world2 = posed_destination(ns, fx)
        world2.fail_on_write = last
        ns["prod_body_apply"](IDENTITY, authorize(ns, reg, u"Apply Pose", item), item, reg)
        whole = len(counter)
    finally:
        ns["prod_body_bindings"] = real
    check("X.11_one_binding_resolution_per_comparison", problems == [] and one == 1 and whole == 3,
          (problems[:3], one, whole))
    # X.12 constraint order permutation keeps the classification and the descriptor
    world = posed_destination(ns, fx)
    profile = profile_of(ns, reg)
    row = ns["prod_resolve_instance"](live_context(ns)["instance"])
    D = ns["prod_body_discover"](ns["prod_body_live"](row, profile), world.t_chan(), ns["prod_pose_writer_index"]())
    C = ns["prod_body_classify"](D, profile)
    ok = True
    for order in (list(reversed(D[u"operators"])), D[u"operators"][1::2] + D[u"operators"][0::2]):
        D2 = dict(D, operators=order)
        C2 = ns["prod_body_classify"](D2, profile)
        ok = ok and dict((k, v) for k, v in C2.items() if k not in (u"constraints", u"constraint_operators")) == \
            dict((k, v) for k, v in C.items() if k not in (u"constraints", u"constraint_operators")) and \
            ns["prod_body_descriptor"](D2, C2, profile) == ns["prod_body_descriptor"](D, C, profile)
    check("X.12_constraint_order_permutation_preserves_classification_and_descriptor", ok)


# ---------------------------------------------------------------------------
# Astra S1 final: Undo exception uncertainty (Y.1 ... Y.7), full-body Apply
# ---------------------------------------------------------------------------

def recovery_calls(world):
    return [c[0] for c in world.dm.calls if c[0] in ("AbortUndoableOperation", "Undo", "Redo")]


def section_final_undo(app, ns, reg, fx, item, lib):
    ns.setdefault("PROD_POSE_RECOVERY_BLOCK", [None])   # no effect on a CPM that defines it (old-code runs)
    label = u"Apply Pose %s" % item[u"record"][u"name"]
    mode = ns["PROD_POSE_REGISTRY_MODE"]
    ns["PROD_POSE_REGISTRY_MODE"] = u"qualification"           # full body is applied only by the qualification CPM

    def direct(world):
        phases = []
        auth = authorize(ns, reg, u"Apply Pose", item)
        got = outcome(lambda: ns["prod_body_apply"](IDENTITY, auth, item, reg,
                                                    phase_callback=lambda p, d=None: phases.append(p)))
        return got, phases

    def through_guard(prepare=None):
        ns["PROD_POSE_RECOVERY_BLOCK"][0] = None       # each scenario starts as a fresh SFM process
        win = window(app, ns, reg, lib)
        world = posed_destination(ns, fx, prepare)
        win.apply_pose(item)
        return win, world

    def locked(win, world):
        return win.pose_recovery_blocked is True and not win.pending and bool(win.statuses) and \
            win.statuses[-1][0] == "error" and \
            win.statuses[-1][3] == ns["PROD_POSE_MESSAGES"][u"recovery-unverified"] % {u"name": item[u"record"][
                u"name"]} and not recovery_calls(world)

    def blocks_next(win):
        world = posed_destination(ns, fx)
        win.apply_pose(item)
        same = bool(win.statuses) and win.statuses[-1][2] == u"recovery-blocked" and no_mutation(world) and \
            not win.pending
        # Closing and reopening CPM: a new window in the same SFM process (same module state) stays paused.
        reopened = window(app, ns, reg, lib)
        world = posed_destination(ns, fx)
        reopened.apply_pose(item)
        return same and reopened.pose_recovery_blocked is False and bool(reopened.statuses) and \
            reopened.statuses[-1][2] == u"recovery-blocked" and no_mutation(world) and not reopened.pending

    try:
        # Y.1 StartUndo fails before native invocation (its arguments cannot be prepared): a plain refusal.
        real_name = ns["prod_pose_native_name"]

        def failing_name(text):
            if u"Apply Pose" in text:                  # only the Undo labels; attribute names still resolve
                raise RuntimeError("label preparation failed (test)")
            return real_name(text)
        ns["prod_pose_native_name"] = failing_name
        try:
            world = posed_destination(ns, fx)
            del ns["LOG"][:]
            got, phases = direct(world)
            reached = [x for x in ns["LOG"] if x.startswith(u"PROD_POSE_BODY-P1 ")]
            win, gworld = through_guard()
        finally:
            ns["prod_pose_native_name"] = real_name
        check("Y.1_failure_before_native_start_undo_is_a_plain_refusal",
              got[0] not in ("ok", "ProdRecoveryUnverifiedError") and no_mutation(world) and not phases and
              len(reached) == 1 and u"label preparation failed" in got[-1], got)
        check("Y.1_guard_reports_it_without_lockout_or_mutation",
              win.pose_recovery_blocked is False and win.statuses[-1][0] == "error" and no_mutation(gworld),
              win.statuses[-1:])
        # Y.2 the native StartUndo call raises, before and after simulated opening: uncertain, lockout.
        for when in ("before", "after"):
            world = posed_destination(ns, fx, lambda w, when=when: setattr(w, "start_raises", when))
            got, phases = direct(world)
            check("Y.2_start_undo_raises_%s_opening_is_recovery_unverified" % when,
                  got[0] == "ProdRecoveryUnverifiedError" and not scene_writes(world) and not phases and
                  [c[0] for c in world.dm.calls] == ["StartUndo"] and
                  (world.dm.current is not None) == (when == "after"), (got, world.dm.calls))
            win, gworld = through_guard(lambda w, when=when: setattr(w, "start_raises", when))
            check("Y.2_start_undo_raises_%s_opening_locks_out_through_pose_guard" % when, locked(win, gworld),
                  win.statuses[-1:])
        check("Y.5_start_undo_lockout_holds_after_reopening_cpm", blocks_next(win), win.statuses[-1:])

        # Y.3 Astra's counterexample: an older Undo entry has the identical description; FinishUndo raises before
        # closing the current transaction. The matching description is never evidence of commitment.
        def older_and_open(w):
            w.dm.push_foreign(label)
            w.finish_raises = "before"
        world = posed_destination(ns, fx, older_and_open)
        del ns["LOG"][:]
        got, phases = direct(world)
        evidence = [x for x in ns["LOG"] if u"BODY-finish-undo-uncertain" in x]
        check("Y.3_finish_undo_raises_before_closure_with_an_identical_older_entry_is_recovery_unverified",
              got[0] == "ProdRecoveryUnverifiedError" and u"native-commit" not in phases and
              world.dm.current is not None and len(world.dm.stack) == 1 and world.dm.GetUndoDesc() == label,
              (got, phases))
        check("Y.3_no_abort_or_undo_of_the_uncertain_operation", not recovery_calls(world) and
              [c[0] for c in world.dm.calls] == ["StartUndo", "FinishUndo"], world.dm.calls)
        check("Y.3_diagnostic_evidence_keeps_the_exception_and_observed_undo_state",
              len(evidence) == 1 and u"FinishUndo failed before commit" in evidence[0] and
              u"undo_desc" in evidence[0] and u"pre_undo" in evidence[0], evidence)
        win, gworld = through_guard(older_and_open)
        check("Y.3_locks_out_through_pose_guard_no_p7_scheduled", locked(win, gworld), win.statuses[-1:])
        check("Y.5_finish_undo_lockout_holds_after_reopening_cpm", blocks_next(win), win.statuses[-1:])
        # Y.4 FinishUndo raises after simulated commitment: still uncertain (no optimistic classification).
        world = posed_destination(ns, fx, lambda w: setattr(w, "finish_raises", "after"))
        got, phases = direct(world)
        check("Y.4_finish_undo_raises_after_commit_is_recovery_unverified",
              got[0] == "ProdRecoveryUnverifiedError" and u"native-commit" not in phases and
              len(world.dm.stack) == 1 and world.dm.GetUndoDesc() == label and not recovery_calls(world),
              (got, phases))
        win, gworld = through_guard(lambda w: setattr(w, "finish_raises", "after"))
        check("Y.4_locks_out_through_pose_guard_no_p7_scheduled", locked(win, gworld), win.statuses[-1:])
        check("Y.5_after_commit_lockout_holds_after_reopening_cpm", blocks_next(win), win.statuses[-1:])
        # Y.6 every uncertain branch above performed no automatic Abort or Undo (checked per case by locked() and
        # recovery_calls()); the shipped fault-free path below is unchanged.
        # Y.7 normal Apply, FinishUndo, P7 and repeat no-op through the guard; the owned Abort.
        win, world = through_guard()
        check("Y.7_normal_apply_commits_and_schedules_p7", len(win.pending) == 1 and
              [c[0] for c in world.dm.calls] == ["StartUndo", "FinishUndo"] and world.dm.GetUndoDesc() == label and
              win.pose_recovery_blocked is False, win.statuses[-1:])
        verdict = ns["prod_pose_deferred_verify"](win.pending[0]) if win.pending else None
        check("Y.7_p7_verifies", verdict == {u"phase": u"committed-verified"}, verdict)
        calls = len(world.dm.calls)
        win.apply_pose(item)
        check("Y.7_repeat_is_a_true_noop", win.statuses[-1][1] == ns["PROD_POSE_MESSAGES"][u"no-op"] and
              len(world.dm.calls) == calls and len(win.pending) == 1, win.statuses[-1:])
        win = window(app, ns, reg, lib)
        world = posed_destination(ns, fx)
        before = all_keys(world)
        ns["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
        win.apply_pose(item)
        check("Y.7_owned_abort_restores_and_does_not_lock", win.statuses[-1][1] == ns["PROD_POSE_MESSAGES"][
            u"not-applied"] and all_keys(world) == before and not world.dm.stack and world.dm.current is None and
            win.pose_recovery_blocked is False and recovery_calls(world) == ["AbortUndoableOperation"],
            win.statuses[-1:])
        # Y.8 a fresh SFM process: the private module is loaded anew (a new namespace from the same source), so no
        # earlier transaction and no pause carry over, while the old process stays paused.
        through_guard(lambda w: setattr(w, "finish_raises", "after"))
        held = ns["PROD_POSE_RECOVERY_BLOCK"][0]
        ns2 = live_namespace(app)
        ns2.setdefault("PROD_POSE_RECOVERY_BLOCK", [None])
        ns2["PROD_POSE_REGISTRY_MODE"] = u"qualification"
        win2 = window(app, ns2, reg, lib)
        world = posed_destination(ns2, fx)
        win2.apply_pose(item)
        verdict = ns2["prod_pose_deferred_verify"](win2.pending[0]) if win2.pending else None
        check("Y.8_fresh_sfm_process_applies_normally", held == u"Apply Pose" and
              ns2["PROD_POSE_RECOVERY_BLOCK"][0] is None and len(win2.pending) == 1 and
              verdict == {u"phase": u"committed-verified"}, (held, win2.statuses[-1:], verdict))
        window(app, ns, reg, lib)                       # rebind the window methods to this namespace
    finally:
        ns["PROD_POSE_REGISTRY_MODE"] = mode
        ns["PROD_POSE_QUAL_FAULT"][0] = None
        ns["PROD_POSE_RECOVERY_BLOCK"][0] = None       # the later sections model a fresh SFM process


# ---------------------------------------------------------------------------
# Revised A1 (Astra, after the native S3 evidence): Z.1 ... Z.11
# ---------------------------------------------------------------------------

# S3 run 1 (E:\SFM_U0B_Scratch\f01-full-body-s3\evidence\A1_PRECHECK.json): S3 Pose A's saved FK positions and the
# posed destination's at B1, the four native discrepancies (SFM's rotate tool rewriting positions).
NATIVE_SAVED = {u"Ear_r_p": [4.631233215332031, -0.22191429138183594, -3.2890470027923584],
                u"bip_index_0_l_p": [0.2489776611328125, 3.5797061920166016, 1.0252677202224731],
                u"bip_tail00_p": [2.185591459274292, -3.3301925659179688, -3.838539123535156e-05],
                u"bip_tail02_p": [0.0, 3.0237770080566406, 0.0]}
NATIVE_DEST = {u"Ear_r_p": [4.631217956542969, -0.221917986869812, -3.289045810699463],
               u"bip_index_0_l_p": [0.2489776611328125, 3.5797061920166016, 1.0252676010131836],
               u"bip_tail00_p": [2.185591459274292, -3.3301925659179688, -3.828108310699463e-05],
               u"bip_tail02_p": [8.285045623779297e-06, 3.0237720012664795, -2.390146255493164e-05]}


def with_positions(D, values):
    d = copy.deepcopy(D)
    for name, v in values.items():
        d[u"channels"][name][u"value"] = list(v)
        d[u"channels"][name][u"keys"] = [[k[0], list(v)] for k in d[u"channels"][name][u"keys"]]
        d[u"bones"][name[:-2]][u"local_position"] = list(v)
    return d


def set_world_positions(world, values):
    for name, v in values.items():
        layer = world.channels[name].attrs["log"].layer
        for k in layer.keys:
            k[1] = FB.native(list(v), "vec")
    world.evaluate()


def section_revised_a1(ns, reg, fx, root):
    profile = profile_of(ns, reg)
    D13, C13 = fx[u"shot13"], ns["prod_body_classify"](fx[u"shot13"], profile)
    check_ = lambda region, D, prof=profile: outcome(lambda: ns["prod_body_check_fk_positions"](  # noqa: E731
        region, D, C13, prof))
    limit = f32(0.00005)
    check("Z.0_limit_is_krystal_only", ns["prod_body_fk_limit"](profile) == limit and
          ns["prod_body_fk_limit"](dict(profile, _id=u"body_other_v1")) == 0.0)

    # A record saved natively from a source carrying the S3 drift, through the real capture path.
    lib = {u"character_key": u"krystal2020", u"char_dir": os.path.join(root, u"Characters", u"krystal2020"),
           u"library_root": root, u"model_ref": MODEL}
    os.makedirs(root)
    src = FB.World(fx[u"shot15"])
    set_world_positions(src, NATIVE_SAVED)
    use_world(ns, src)
    auth = authorize(ns, reg, u"Save Pose")
    pose = ns["prod_body_capture"](IDENTITY, auth, reg)
    region = pose[u"regions"][u"full_body"]
    check("Z.0_the_record_holds_the_native_saved_positions",
          all(region[u"positions"][n] == v for n, v in NATIVE_SAVED.items()))
    saved = ns["prod_pose_save_new"](lib, u"S3 Native A", pose, u"20261107-120000-000000", reg)
    fresh, _ = registries(ns)
    item = [i for i in ns["prod_pose_discover"](lib[u"char_dir"], u"krystal2020", fresh)[u"items"]
            if i[u"preset_id"] == saved[u"preset_id"]][0]

    # Z.1 the four native discrepancies are compatible, and the destination keeps its own values
    Dn = with_positions(D13, NATIVE_DEST)
    got = check_(region, Dn)
    check("Z.1_all_four_native_discrepancies_accepted", got[0] == "ok" and all(
        got[1][n] == NATIVE_DEST[n] for n in NATIVE_DEST), got)
    check("Z.1_largest_native_distance_is_within_the_limit", max(
        ns["prod_body_fk_distance"](NATIVE_SAVED[n], NATIVE_DEST[n]) for n in NATIVE_DEST) < 0.00005)
    plans = ns["prod_body_plan"](region, Dn, C13, snapshots(Dn, C13[u"written"]), Dn[u"t_chan"], got[1])
    byname = dict((p[u"name"], p) for p in plans)
    check("Z.1_planned_fk_positions_are_the_destination_values_never_the_saved_ones",
          all(byname[n][u"value"] == NATIVE_DEST[n] and byname[n][u"action"] == u"insert" for n in NATIVE_DEST))
    refused("Z.1_another_profile_stays_exact", check_(region, Dn, dict(profile, _id=u"body_other_v1")),
            u"fk-position")
    # Z.2 / Z.3 the boundary, as float32: exactly at the limit accepted, the next float32 above refused
    at = copy.deepcopy(region)
    base = D13[u"channels"][u"bip_tail02_p"][u"value"]
    at[u"positions"][u"bip_tail02_p"] = [base[0] + limit, base[1], base[2]]
    got = check_(at, D13)
    check("Z.2_distance_exactly_at_the_limit_is_accepted", base[0] == 0.0 and got[0] == "ok" and
          got[1][u"bip_tail02_p"] == base, got)
    above = copy.deepcopy(region)
    above[u"positions"][u"bip_tail02_p"] = [next_f32(limit), base[1], base[2]]
    refused("Z.3_distance_immediately_above_the_limit_refuses", check_(above, D13), u"fk-position")
    # Z.4 non-finite, non-float32 and incoherent evidence refuses
    for label, value in ((u"nan", float("nan")), (u"inf", float("inf")), (u"not_float32", 0.1)):
        r = copy.deepcopy(region)
        r[u"positions"][u"bip_tail02_p"] = [value, base[1], base[2]]
        refused("Z.4_saved_%s_refuses" % label, check_(r, D13), u"evidence-unreadable")
    d = copy.deepcopy(D13)
    d[u"bones"][u"bip_tail02"][u"local_position"] = [next_f32(base[0]), base[1], base[2]]
    refused("Z.4_transform_not_equal_to_its_channel_refuses", check_(region, d), u"evidence-unreadable")
    d = copy.deepcopy(D13)
    d[u"channels"][u"bip_tail02_p"][u"value"] = [float("inf"), base[1], base[2]]
    refused("Z.4_non_finite_destination_refuses", check_(region, d), u"evidence-unreadable")
    # Z.6 an existing correct key stays unchanged; Z.7 a contradictory existing key refuses
    pinned = check_(region, Dn)[1]
    keyed = copy.deepcopy(Dn)
    for n in NATIVE_DEST:
        keyed[u"channels"][n][u"keys"].append([Dn[u"t_chan"], list(NATIVE_DEST[n])])
        keyed[u"channels"][n][u"keys"].sort(key=lambda k: k[0])
    plans = ns["prod_body_plan"](region, keyed, C13, snapshots(keyed, C13[u"written"]), keyed[u"t_chan"], pinned)
    check("Z.6_existing_correct_key_is_left_unchanged",
          all(p[u"action"] == u"none" for p in plans if p[u"name"] in NATIVE_DEST))
    bad = copy.deepcopy(keyed)
    k = [x for x in bad[u"channels"][u"bip_tail02_p"][u"keys"] if x[0] == Dn[u"t_chan"]][0]
    k[1] = list(NATIVE_SAVED[u"bip_tail02_p"])          # the authored key says the saved value; evaluation says not
    refused("Z.7_contradictory_existing_key_refuses", outcome(lambda: ns["prod_body_plan"](
        region, bad, C13, snapshots(bad, C13[u"written"]), bad[u"t_chan"], pinned)), u"evidence-unreadable")

    # Live: the native destination values on a distinctly posed shot13
    native = lambda w: set_world_positions(w, NATIVE_DEST)  # noqa: E731
    apply_ = lambda: outcome(lambda: ns["prod_body_apply"](  # noqa: E731
        IDENTITY, authorize(ns, reg, u"Apply Pose", item), item, reg))
    # Z.10 Abort restores the exact original state (missing keys, values, transforms, Undo)
    world = posed_destination(ns, fx, native)
    keys0, tr0 = all_keys(world), transform_state(world)
    ns["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
    try:
        got = apply_()
    finally:
        ns["PROD_POSE_QUAL_FAULT"][0] = None
    check("Z.10_abort_restores_the_exact_original_state", got[0] == "ok" and got[1][u"phase"] == u"not-applied" and
          all_keys(world) == keys0 and transform_state(world) == tr0 and not world.dm.stack and
          world.dm.current is None, got)
    # Z.5 missing keys inserted with the destination's values; P7 verifies; nothing transferred
    world = posed_destination(ns, fx, native)
    keys0, tr0 = all_keys(world), transform_state(world)
    del ns["LOG"][:]
    auth = authorize(ns, reg, u"Apply Pose", item)
    got = outcome(lambda: ns["prod_body_apply"](IDENTITY, auth, item, reg))
    pending = dict(got[1][u"pending"], authorization=auth) if got[0] == "ok" else None
    verdict = ns["prod_pose_deferred_verify"](pending) if pending else None
    t = world.t_chan()
    at_t = dict((n, [FB.plain(k[1]) for k in world.channels[n].attrs["log"].layer.keys if k[0] == t])
                for n in NATIVE_DEST)
    check("Z.5_missing_keys_are_inserted_with_the_destination_values",
          all(at_t[n] == [NATIVE_DEST[n]] for n in NATIVE_DEST), at_t)
    check("Z.5_destination_fk_positions_unchanged_and_p7_verified", verdict == {u"phase": u"committed-verified"} and
          all(FB.plain(world.bone_dag[n[:-2]].attrs["transform"].attrs["position"]) == NATIVE_DEST[n]
              for n in NATIVE_DEST), verdict)
    a1 = [l for l in ns["LOG"] if u"BODY-A1" in l]
    check("Z.5_preflight_logs_the_pinned_differences", len(a1) == 1 and all(n in a1[0] for n in
                                                                           (u"Ear_r_p", u"bip_tail02_p")), a1)
    # Z.8 a repeated Apply is a verified no-op
    calls = len(world.dm.calls)
    again = apply_()
    check("Z.8_repeated_apply_is_a_true_noop", again == ("ok", {u"phase": u"no-op"}) and len(world.dm.calls) == calls,
          again)
    # Z.11 P7 refuses FK position drift (one float32 step, or the saved value transferred) and never verifies
    for label, value in ((u"one_ulp", [next_f32(NATIVE_DEST[u"bip_tail02_p"][0])] + NATIVE_DEST[u"bip_tail02_p"][1:]),
                         (u"saved_value_transferred", NATIVE_SAVED[u"bip_tail02_p"])):
        layer = world.channels[u"bip_tail02_p"].attrs["log"].layer
        keep = [list(k) for k in layer.keys]
        for k in layer.keys:
            if k[0] == t:
                k[1] = FB.native(list(value), "vec")
        world.evaluate()
        del ns["LOG"][:]
        verdict = ns["prod_pose_deferred_verify"](pending)
        check("Z.11_p7_refuses_fk_position_drift_%s" % label, verdict.get(u"phase") == u"committed-unverified" and
              any(u"pinned FK position bip_tail02_p drifted" in l for l in ns["LOG"]), verdict)
        layer.keys[:] = keep
        world.evaluate()
    check("Z.11_restored_state_verifies_again", ns["prod_pose_deferred_verify"](pending) ==
          {u"phase": u"committed-verified"})
    # Z.10 Undo restores the exact original state; Redo the applied one
    applied = all_keys(world)
    world.dm.Undo()
    world.evaluate()
    check("Z.10_undo_restores_the_exact_original_state", all_keys(world) == keys0 and transform_state(world) == tr0)
    world.dm.Redo()
    world.evaluate()
    check("Z.10_redo_restores_the_applied_state", all_keys(world) == applied)
    # Z.9 one float32 step on a pinned FK position between P1 and P2 refuses (channel and transform, coherently)
    world = posed_destination(ns, fx, native)
    original = ns["prod_body_preflight"]

    def preflight_then_step(*args):
        pre = original(*args)
        v = NATIVE_DEST[u"bip_tail02_p"]
        set_world_positions(world, {u"bip_tail02_p": [next_f32(v[0])] + v[1:]})
        return pre
    ns["prod_body_preflight"] = preflight_then_step
    del ns["LOG"][:]
    try:
        got = apply_()
    finally:
        ns["prod_body_preflight"] = original
    refused("Z.9_one_ulp_change_between_p1_and_p2_refuses", got, u"stale")
    check("Z.9_no_mutation_and_the_pin_change_is_logged", no_mutation(world) and any(
        u"pinned FK positions changed" in l for l in ns["LOG"]), ns["LOG"][-3:])


# ---------------------------------------------------------------------------
# S3 run 3 B10: Apply refusal messages through the window (M.1 ... M.6)
# ---------------------------------------------------------------------------

def section_apply_messages(app, ns, reg, fx, item, lib):
    mode = ns["PROD_POSE_REGISTRY_MODE"]
    ns["PROD_POSE_REGISTRY_MODE"] = u"qualification"
    editor = u"Switch to the Motion Editor to apply a pose. Nothing was changed."
    try:
        # M.1 run 3 B10: the Clip Editor, where SFM evaluates the rig at its stale clock (FA-1)
        def clip_editor(w):
            # As natively: the rig's channels hold keys at other times, so the stale clock evaluates another pose.
            layer = w.channels[u"Hip_p"].attrs["log"].layer
            v = FB.plain(layer.keys[0][1])
            layer.keys.append([w.stale_clock, FB.native([v[0] + 1.0, v[1], v[2]], "vec")])
            layer.keys.append([w.t_chan() - 1, FB.native(list(v), "vec")])
            layer.keys.sort(key=lambda k: k[0])
            w.native_clip_evaluation = True
            w.timeline_mode = 3
            w.evaluate()
        world = posed_destination(ns, fx, clip_editor)
        got = outcome(lambda: ns["prod_body_effective_inputs"](*(lambda st: (st[u"D"], st[u"C"], profile_of(ns, reg)))(
            ns["prod_body_state"](ns["prod_resolve_instance"](live_context(ns)["instance"]), profile_of(ns, reg)))))
        check("M.1_precondition_the_clip_editor_evaluation_is_not_at_the_mapped_tick",
              got[0] != "ok" and got[1] == u"evidence-unreadable", got)
        win = window(app, ns, reg, lib)
        win.apply_pose(item)
        check("M.1_clip_editor_full_body_apply_says_switch_to_the_motion_editor",
              win.statuses[-1][2] == u"editor-mode" and win.statuses[-1][3] == editor and
              ns["PROD_POSE_EDITOR_MODE_COPY"] == editor, win.statuses[-1:])
        check("M.1_nothing_written_no_undo_no_pause", no_mutation(world) and not win.pending and
              win.pose_recovery_blocked is False)
        # M.3 genuine unreadable evidence in the Motion Editor keeps the protective message
        def skew(w):
            t = w.handle_dag[u"Hip"].attrs["transform"]
            v = FB.plain(t.attrs["position"])
            t.set("position", FB.Vector(v[0] + 0.25, v[1], v[2]))
        world = posed_destination(ns, fx)
        skew(world)
        win = window(app, ns, reg, lib)
        win.apply_pose(item)
        check("M.3_unreadable_evidence_keeps_the_protective_message_not_the_editor_one",
              win.statuses[-1][2] == u"evidence-unreadable" and win.statuses[-1][3] ==
              ns["PROD_BODY_MESSAGES"][u"evidence-unreadable"] and no_mutation(world), win.statuses[-1:])
        # M.4 incompatible proportions keep their specific explanation (shot10, Motion Editor)
        world = FB.World(fx[u"shot10"])
        use_world(ns, world)
        win = window(app, ns, reg, lib)
        win.apply_pose(item)
        check("M.4_incompatible_proportions_keep_their_message",
              win.statuses[-1][2] == u"proportions" and win.statuses[-1][3] == ns["PROD_BODY_MESSAGES"][
                  u"proportions"] and no_mutation(world), win.statuses[-1:])
        # M.5 a valid Motion Editor Apply is unchanged
        world = posed_destination(ns, fx)
        win = window(app, ns, reg, lib)
        win.apply_pose(item)
        verdict = ns["prod_pose_deferred_verify"](win.pending[0]) if win.pending else None
        check("M.5_valid_motion_editor_apply_unchanged", len(win.pending) == 1 and
              verdict == {u"phase": u"committed-verified"} and [c[0] for c in world.dm.calls] ==
              ["StartUndo", "FinishUndo"], verdict)
        # M.6 the recovery pause still refuses first
        ns["PROD_POSE_RECOVERY_BLOCK"][0] = u"Apply Pose"
        try:
            world = posed_destination(ns, fx, clip_editor)
            win = window(app, ns, reg, lib)
            win.apply_pose(item)
            check("M.6_recovery_pause_still_refuses_before_any_editor_check",
                  win.statuses[-1][2] == u"recovery-blocked" and no_mutation(world), win.statuses[-1:])
        finally:
            ns["PROD_POSE_RECOVERY_BLOCK"][0] = None
    finally:
        ns["PROD_POSE_REGISTRY_MODE"] = mode


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        return 2
    print("F-01 stage E full body (Python %s)" % sys.version.split()[0])
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    app = route.AppSource(route.APP_PATH)
    root = tempfile.mkdtemp(prefix="cpm_f01e_lib_")
    try:
        ns = live_namespace(app)
        fx = dict((n, fixture("s0_%s.json" % n)) for n in (u"shot15", u"shot13", u"shot10"))
        reg = run("registry", lambda: section_registry(ns))
        if reg:
            run("classification", lambda: section_classification(ns, reg, fx))
            got = run("records", lambda: section_records(ns, reg, fx, root))
            if got:
                run("planner", lambda: section_planner(ns, reg, fx, got[0]))
            lived = run("live", lambda: section_live(ns, reg, fx, os.path.join(root, u"live")))
            if lived:
                run("live_refusals", lambda: section_live_refusals(ns, lived[0], fx, lived[1]))
                live_lib = {u"character_key": u"krystal2020", u"library_root": os.path.join(root, u"live"),
                            u"char_dir": os.path.join(root, u"live", u"Characters", u"krystal2020"),
                            u"model_ref": MODEL, u"checksum": 1234}
                run("corrections", lambda: section_corrections(app, ns, lived[0], fx, lived[1], live_lib))
                run("final_undo", lambda: section_final_undo(app, ns, lived[0], fx, lived[1], live_lib))
                run("apply_messages", lambda: section_apply_messages(app, ns, lived[0], fx, lived[1], live_lib))
            run("window", lambda: section_window(app, ns, reg, fx, os.path.join(root, u"window")))
            run("revised_a1", lambda: section_revised_a1(ns, reg, fx, os.path.join(root, u"revised_a1")))
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
