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


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        return 2
    print("F-01 stage E full body (Python %s)" % sys.version.split()[0])
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    app = route.AppSource(route.APP_PATH)
    root = tempfile.mkdtemp(prefix="cpm_f01e_lib_")
    try:
        ns = build_namespace(app)
        fx = dict((n, fixture("s0_%s.json" % n)) for n in (u"shot15", u"shot13", u"shot10"))
        reg = run("registry", lambda: section_registry(ns))
        if reg:
            run("classification", lambda: section_classification(ns, reg, fx))
            got = run("records", lambda: section_records(ns, reg, fx, root))
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
