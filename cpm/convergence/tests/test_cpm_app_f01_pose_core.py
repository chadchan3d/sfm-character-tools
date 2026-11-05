# -*- coding: utf-8 -*-
"""F-01 Pose Library M1, stage A: offline qualification of the pose core in the CPM application source
(cpm/app/SFM_Character_Preset_Manager.py). Design authority: F-01 M1 Implementation Addendum R2 and
09_FIRST_CODING_ASSIGNMENT.md; qualification items O-1..O-8 of 05_QUALIFICATION_PLAN.md.

Technique (as in the existing CPM suites): every top-level prod_pose_* / PROD_POSE_* / ProdPose* definition is
extracted verbatim from the application source by ast and executed in a namespace holding only json, hashlib and
math. A static check proves the block references no SFM, DME or Qt name. W2's accepted harness core and fixtures
are the oracle; each is verified against the W2 checkpoint's SHA256SUMS.txt, whose own hash is pinned here.

Usage: --phase=run (Python 2.7.5 and Python 3.10). Offline only; nothing here demonstrates native SFM behaviour.
Environment: CPM_TEST_APP_PATH overrides the application source (mutation runs).
"""
from __future__ import print_function

import ast
import copy
import hashlib
import io
import json
import math
import os
import random
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, os.pardir, os.pardir, os.pardir))
APP_PATH = os.environ.get("CPM_TEST_APP_PATH") or os.path.join(_REPO_ROOT, "cpm", "app",
                                                                "SFM_Character_Preset_Manager.py")
REGISTRY_PATH = os.path.join(_REPO_ROOT, "cpm", "pose_profiles", "cpm_pose_profiles_v1.json")
W2_DIR = os.path.join(_REPO_ROOT, "real_sfm_qualification", "checkpoint_f01_w2_persisted_pose", "accepted")
W2_SUMS_SHA256 = "3ddf5942b306b466316141da46640d9937bbe1cbf2c2150d00dc469d3cb6f568"
W2_ORACLE_FILES = ("harness/f01w2_core.py", "tests/fixtures/golden_left_arm_pose.f01w2.json",
                   "tests/fixtures/adversarial/bom.f01w2.json", "tests/fixtures/adversarial/duplicate_key.f01w2.json",
                   "tests/fixtures/adversarial/infinity_overflow.f01w2.json",
                   "tests/fixtures/adversarial/invalid_utf8.f01w2.bin",
                   "tests/fixtures/adversarial/nan_literal.f01w2.json",
                   "tests/fixtures/adversarial/truncated.f01w2.json")
PREFIXES = ("prod_pose_", "PROD_POSE_", "ProdPose")
BLOCK_START = u"# F-01 Pose Library M1, stage A: offline pose core"
BLOCK_END = u"# === end of F-01 stage A block ==="
ALLOWED_MODULES = set(["json", "hashlib", "math"])
FORBIDDEN = set(["vs", "sfmApp", "sfm", "QtGui", "QtCore", "PySide", "dm", "dme", "sfmUtils", "dmeutils",
                 "ctypes", "os", "io", "open", "subprocess", "datetime"])

RESULTS = []


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


def refuses(name, code, fn, reason=None):
    try:
        fn()
    except Exception as exc:
        got = getattr(exc, "code", None)
        check(name, type(exc).__name__ == "ProdPoseError" and (code is None or got == code) and
              (reason is None or reason in str(exc)), "%s %s: %s" % (type(exc).__name__, got, exc))
        return exc
    check(name, False, "did not refuse")
    return None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    with open(path, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Extraction and static dependency check
# ---------------------------------------------------------------------------

def extract_block(path, start_mark=None, end_mark=None):
    """Every top-level pose definition between the block's own begin and end markers (exactly one each)."""
    raw = read(path)
    lines = raw.decode("utf-8").split(u"\n")
    start_mark, end_mark = start_mark or BLOCK_START, end_mark or BLOCK_END
    starts = [i + 1 for i, l in enumerate(lines) if l.startswith(start_mark)]
    ends = [i + 1 for i, l in enumerate(lines) if l.strip() == end_mark]
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise SystemExit("REFUSED: block markers not found exactly once (%r, %r)" % (starts, ends))
    tree = ast.parse(raw)
    body = tree.body
    chunks, names = [], []
    for i, node in enumerate(body):
        if not starts[0] < node.lineno < ends[0]:
            continue
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            name = node.name
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        else:
            continue
        if not name.startswith(PREFIXES):
            continue
        end = min((body[i + 1].lineno - 1) if i + 1 < len(body) else len(lines), ends[0] - 1)
        block = lines[node.lineno - 1:end]
        while block and (not block[-1].strip() or block[-1].lstrip().startswith(u"#")):
            block.pop()
        chunks.append(u"\n".join(block))
        names.append(name)
    return u"\n\n\n".join(chunks) + u"\n", names


class Names(ast.NodeVisitor):
    def __init__(self):
        self.loaded, self.bound, self.imports, self.attr_roots = set(), set(), [], set()

    def visit_Name(self, node):
        (self.loaded if isinstance(node.ctx, ast.Load) else self.bound).add(node.id)

    def visit_arg(self, node):        # Python 3
        self.bound.add(node.arg)

    def visit_FunctionDef(self, node):
        self.bound.add(node.name)
        for a in node.args.args:
            if isinstance(a, ast.Name):   # Python 2
                self.bound.add(a.id)
        if node.args.vararg:
            self.bound.add(node.args.vararg if isinstance(node.args.vararg, str) else node.args.vararg.arg)
        if node.args.kwarg:
            self.bound.add(node.args.kwarg if isinstance(node.args.kwarg, str) else node.args.kwarg.arg)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.bound.add(node.name)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.name is not None:
            self.bound.add(node.name if isinstance(node.name, str) else getattr(node.name, "id", None))
        self.generic_visit(node)

    def visit_Import(self, node):
        for a in node.names:
            self.imports.append(a.name)
            self.bound.add(a.asname or a.name)

    def visit_ImportFrom(self, node):
        self.imports.append("from " + str(node.module))

    def visit_Attribute(self, node):
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name):
            self.attr_roots.add(root.id)
        self.generic_visit(node)


def static_check(block):
    v = Names()
    v.visit(ast.parse(block))
    builtin_names = set(dir(__builtins__) if not isinstance(__builtins__, dict) else __builtins__)
    free = v.loaded - v.bound - builtin_names - ALLOWED_MODULES - set(["unicode", "long"])
    check("static.block_has_only_its_own_and_allowed_free_names", not free, sorted(free))
    check("static.no_forbidden_name_or_attribute_root", not ((v.loaded | v.attr_roots) & FORBIDDEN),
          sorted((v.loaded | v.attr_roots) & FORBIDDEN))
    check("static.only_local_struct_import", v.imports == ["struct"], v.imports)


def load_namespace():
    block, names = extract_block(APP_PATH)
    ns = {"__builtins__": __builtins__, "json": json, "hashlib": hashlib, "math": math}
    exec(compile(block, "pose_core_block", "exec"), ns)
    return ns, block, names


# ---------------------------------------------------------------------------
# W2 oracle (hash-verified, read-only)
# ---------------------------------------------------------------------------

def w2_verified():
    sums_raw = read(os.path.join(W2_DIR, "SHA256SUMS.txt"))
    ok = sha(sums_raw) == W2_SUMS_SHA256
    sums = dict(line.split("  ", 1)[::-1] for line in sums_raw.decode("ascii").splitlines() if line.strip())
    bad = [f for f in W2_ORACLE_FILES if sums.get(f) != sha(read(os.path.join(W2_DIR, *f.split("/"))))]
    check("oracle.w2_sums_file_pinned", ok, sha(sums_raw))
    check("oracle.w2_files_match_checkpoint_sums", not bad, bad)
    return ok and not bad


def load_w2_core():
    path = os.path.join(W2_DIR, "harness", "f01w2_core.py")
    if sys.version_info[0] == 2:
        import imp
        return imp.load_source("f01w2_core_oracle", path)
    import importlib.util
    spec = importlib.util.spec_from_file_location("f01w2_core_oracle", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def mirror_name(n):
    """Left-to-right rig name: CollarL, the _l_ infix (Hand_l_p) and the _l suffix (bip_hand_l) only."""
    n = n.replace("CollarL", "CollarR").replace("_l_", "_r_")
    return n[:-2] + "_r" if n.endswith("_l") else n


def region_from_w2(golden, side):
    """A cpm-pose region built from W2's golden left-arm pose (the right arm renames every rig name)."""
    m = (lambda s: s) if side == "left_arm" else (lambda s: mirror_name(s) if isinstance(s, type(u"")) or
                                                  isinstance(s, str) else s)
    comp = golden["compatibility"]

    def rename(obj):
        if isinstance(obj, dict):
            return dict((m(k), rename(v)) for k, v in obj.items())
        if isinstance(obj, list):
            return [rename(x) for x in obj]
        return m(obj) if isinstance(obj, (type(u""), str)) else obj
    bones = dict((m(b), {u"local_orientation": r[u"local_orientation"], u"anchor_position": r[u"collar_position"],
                         u"anchor_orientation": r[u"collar_orientation"]})
                 for b, r in golden["skeleton"]["bones"].items())
    return {u"profile_id": u"arm_left_v1" if side == "left_arm" else u"arm_right_v1",
            u"anchor": u"CollarL" if side == "left_arm" else u"CollarR",
            u"frame": u"source-anchor-world-at-capture",
            u"goals": {u"hand": dict(golden["pose"]["hand"]), u"elbow": dict(golden["pose"]["elbow"])},
            u"oracle": {u"bones": bones, u"upper_arm_origin": list(golden["skeleton"]["upper_arm_origin"])},
            u"descriptor": {u"arm_chain": rename(comp["arm_chain"]), u"scale_state": u"unit",
                            u"handles": rename(comp["handles"]), u"constraints": rename(comp["constraints"]),
                            u"channels": rename(comp["channels"]),
                            u"follow_the_arm_bones": [m(u"bip_finger_l")]}}


def make_record(ns, golden, regions=("left_arm", "right_arm")):
    pose = {u"format": u"cpm-pose", u"version": 1, u"conventions": dict(ns["PROD_POSE_CONVENTIONS"]),
            u"registry": {u"profile_set": u"cpm-pose-profiles", u"version": 1},
            u"source": {u"rig_class": u"krystal-v1", u"model_ref": golden["model"], u"shot_name": u"shot15",
                        u"t_doc_ticks": 2500, u"t_shot_ticks": 51667},
            u"regions": dict((r, region_from_w2(golden, r)) for r in regions)}
    pose = json.loads(json.dumps(pose))
    return {u"schema_version": 3, u"record_kind": u"preset", u"kind": u"pose", u"character_key": u"krystal2020",
            u"model_ref": golden["model"], u"preset_id": u"0123456789abcdef0123456789abcdef",
            u"name": u"Arms Crossed", u"created_at": u"2026-10-30T12:00:00Z", u"updated_at": u"2026-10-30T12:00:00Z",
            u"payload_sha256": ns["prod_pose_payload_digest"](pose), u"pose": pose}


def rand_quat(rng):
    q = [rng.uniform(-1, 1) for _ in range(4)]
    n = math.sqrt(sum(c * c for c in q))
    return [c / n for c in q]


def rand_frame(rng, scale=50.0):
    return ([rng.uniform(-scale, scale) for _ in range(3)], rand_quat(rng))


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def section_records(ns, reg, golden):
    E = ns["ProdPoseError"]
    rec = make_record(ns, golden)
    raw = ns["prod_pose_serialize"](rec)
    parsed = ns["prod_pose_parse"](raw, reg)
    check("O1.round_trip_byte_exact", ns["prod_pose_serialize"](parsed) == raw)
    check("O1.both_regions", sorted(parsed["pose"]["regions"]) == ["left_arm", "right_arm"])
    one = make_record(ns, golden, ("left_arm",))
    check("O1.one_region", sorted(ns["prod_pose_parse"](ns["prod_pose_serialize"](one), reg)["pose"]["regions"])
          == ["left_arm"])
    for f in W2_ORACLE_FILES:
        if "/adversarial/" in f:
            data = read(os.path.join(W2_DIR, *f.split("/")))
            refuses("O1.w2_adversarial_refused." + f.split("/")[-1], "invalid-file",
                    lambda d=data: ns["prod_pose_parse"](d, reg))

    def mutated(fn, regen_digest=True):
        r = copy.deepcopy(rec)
        fn(r)
        if regen_digest:
            r["payload_sha256"] = ns["prod_pose_payload_digest"](r["pose"])
        return ns["prod_pose_canonical_bytes"](r)

    cases = [
        ("bom", b"\xef\xbb\xbf" + raw),
        ("invalid_utf8", raw.replace(b"Arms Crossed", b"Arms \xff Crossed")),
        ("nan", raw.replace(b"2500", b"NaN", 1)),
        ("infinity", raw.replace(b"2500", b"Infinity", 1)),
        ("overflow_1e400", raw.replace(b"13.665717565725013", b"1e400", 1)),     # a hand position number
        ("duplicate_key", raw.replace(b'"kind": "pose",', b'"kind": "pose",\n "kind": "pose",', 1)),
        ("truncated", raw[:len(raw) // 2]),
        ("oversize", raw[:-2] + b" " * 131072 + raw[-2:]),
        ("unknown_field", mutated(lambda r: r.__setitem__("extra", 1))),
        ("missing_field", mutated(lambda r: r.pop("updated_at"))),
        ("bool_as_number", mutated(lambda r: r["pose"]["regions"]["left_arm"]["goals"]["hand"]["position"]
                                   .__setitem__(0, True))),
        ("out_of_range", mutated(lambda r: r["pose"]["regions"]["left_arm"]["goals"]["hand"]["position"]
                                 .__setitem__(0, 2.0e6))),
        ("non_unit_quaternion", mutated(lambda r: r["pose"]["regions"]["left_arm"]["goals"]["hand"]
                                        .__setitem__("orientation", [0.0, 0.0, 0.0, 1.01]))),
        ("wrong_kind", mutated(lambda r: r.__setitem__("kind", "body"))),
        ("wrong_format", mutated(lambda r: r["pose"].__setitem__("format", "F01W2-left-arm-pose"))),
        ("wrong_version", mutated(lambda r: r["pose"].__setitem__("version", 2))),
        ("digest_mismatch", mutated(lambda r: r["pose"]["source"].__setitem__("shot_name", "other"), False)),
        ("empty_regions", mutated(lambda r: r["pose"].__setitem__("regions", {}))),
        ("unknown_region", mutated(lambda r: r["pose"]["regions"].__setitem__(
            "legs", r["pose"]["regions"].pop("left_arm")))),
        ("profile_region_mismatch", mutated(lambda r: r["pose"]["regions"]["left_arm"].__setitem__(
            "profile_id", "arm_right_v1"))),
        ("anchor_mismatch", mutated(lambda r: r["pose"]["regions"]["left_arm"].__setitem__("anchor", "CollarR"))),
        ("bad_preset_id", mutated(lambda r: r.__setitem__("preset_id", "XYZ"))),
        ("duplicate_chain_name", mutated(lambda r: r["pose"]["regions"]["left_arm"]["descriptor"]["arm_chain"][1]
                                         .__setitem__("name", "bip_UpperArm_l"))),
        ("chain_missing_collar", mutated(lambda r: r["pose"]["regions"]["left_arm"]["descriptor"]["arm_chain"]
                                         .pop(1))),
        ("string_too_long", mutated(lambda r: r.__setitem__("name", "x" * 257))),
        ("oracle_bone_missing", mutated(lambda r: r["pose"]["regions"]["left_arm"]["oracle"]["bones"]
                                        .pop("bip_hand_l"))),
        ("channel_missing", mutated(lambda r: r["pose"]["regions"]["left_arm"]["descriptor"]["channels"]
                                    .pop("Elbow_l_o"))),
        ("curve_info_not_none", mutated(lambda r: r["pose"]["regions"]["left_arm"]["descriptor"]["channels"]
                                        ["Hand_l_p"].__setitem__("curve_info", "bezier"))),
        ("int_as_float_index", mutated(lambda r: r["pose"]["regions"]["left_arm"]["descriptor"]["arm_chain"][0]
                                       .__setitem__("index", 4.0))),
        ("not_bytes", None),
    ]
    reasons = {"bom": "byte-order mark", "invalid_utf8": "not valid UTF-8", "duplicate_key": "duplicate key",
               "nan": "non-finite number literal", "infinity": "non-finite number literal",
               "overflow_1e400": "non-finite or out of range", "oversize": "exceeds", "digest_mismatch": "digest",
               "unknown_field": "unknown fields", "missing_field": "missing fields",
               "non_unit_quaternion": "not unit", "bool_as_number": "expected a number"}
    for name, data in cases:
        if data is None:
            refuses("O1.refused." + name, "invalid-file", lambda: ns["prod_pose_parse"](u"{}", reg))
        else:
            refuses("O1.refused." + name, "invalid-file", lambda d=data: ns["prod_pose_parse"](d, reg),
                    reasons.get(name))
    check("O1.error_is_value_error", issubclass(E, ValueError))


def section_registry(ns, raw, golden):
    E = ns["ProdPoseError"]
    good = sha(raw)
    reg = ns["prod_pose_registry_parse"](raw, good)
    refuses("O2.hash_mismatch_refused", "registry", lambda: ns["prod_pose_registry_parse"](raw, "0" * 64))
    prod = ns["prod_pose_registry_select"](reg, u"production")
    qual = ns["prod_pose_registry_select"](reg, u"qualification")
    check("O2.production_exposes_only_the_qualified_krystal_left_arm",
          [(m["region"], m["from"], m["to"], m["status"]) for m in prod["mappings"]] ==
          [("left_arm", "krystal-v1", "krystal-v1", "qualified")], prod["mappings"])
    check("O2.qualification_exposes_each_mapping_with_status",
          sorted((m["region"], m["status"]) for m in qual["mappings"]) ==
          [("left_arm", "qualified"), ("right_arm", "experimental")])
    check("O2.every_other_mapping_stays_experimental",
          [m for m in reg["mappings"] if m["status"] == "qualified"] == prod["mappings"]
          and all(m["evidence"] is None for m in reg["mappings"] if m["status"] == "experimental"))
    evidence = prod["mappings"][0]["evidence"] if prod["mappings"] else ""
    doc = os.path.join(_REPO_ROOT, "cpm", "qualification", "F01_STAGE_D_NATIVE_QUALIFICATION_EVIDENCE.md")
    check("O2.qualified_evidence_names_the_stage_d_record_and_candidate",
          "cpm/qualification/F01_STAGE_D_NATIVE_QUALIFICATION_EVIDENCE.md" in evidence and "18849e5f" in evidence
          and "CC-1" in evidence and os.path.isfile(doc) and b"18849e5f" in read(doc), evidence)
    refuses("O2.unknown_mode_refused", "registry", lambda: ns["prod_pose_registry_select"](reg, u"dev"))
    base = json.loads(raw.decode("utf-8"))

    def variant(fn):
        r = copy.deepcopy(base)
        fn(r)
        data = json.dumps(r).encode("utf-8")
        return lambda: ns["prod_pose_registry_parse"](data, sha(data))
    refuses("O2.qualified_without_evidence", "registry",
            variant(lambda r: r["mappings"][0].__setitem__("evidence", None)))
    refuses("O2.experimental_with_evidence", "registry",
            variant(lambda r: r["mappings"][1].__setitem__("evidence", "NQ-1")))
    refuses("O2.model_in_two_classes", "registry",
            variant(lambda r: r["rig_classes"].__setitem__("other", copy.deepcopy(r["rig_classes"]["krystal-v1"]))))
    refuses("O2.class_lists_unknown_profile", "registry",
            variant(lambda r: r["rig_classes"]["krystal-v1"]["profiles"].append("arm_mystery")))
    refuses("O2.mapping_unknown_class", "registry", variant(lambda r: r["mappings"][0].__setitem__("to", "lola-v1")))
    refuses("O2.duplicate_mapping", "registry", variant(lambda r: r["mappings"].append(dict(r["mappings"][0]))))
    refuses("O2.unknown_status", "invalid-file", variant(lambda r: r["mappings"][0].__setitem__("status", "ok")))
    refuses("O2.tolerance_missing", "registry",
            variant(lambda r: r["profiles"]["arm_left_v1"]["tolerances"].pop("collar_mapping")))
    refuses("O2.duplicate_profile_names", "registry",
            variant(lambda r: r["profiles"]["arm_left_v1"].__setitem__("hand", "CollarL")))
    model = golden["model"]
    check("O2.listed_model_has_class", ns["prod_pose_rig_class"](reg, model) == "krystal-v1")
    check("O2.separator_and_case_variant_same_listing",
          ns["prod_pose_rig_class"](reg, model.replace("/", "\\").upper()) == "krystal-v1")
    for name, other in (("unlisted", "models/fursonas/lola/lola.mdl"),
                        ("same_stem_other_folder", "models/other/krystal2020.mdl"),
                        ("family_variant", model.replace("krystal2020", "krystal2020new")),
                        ("bare_stem", "krystal2020.mdl")):
        check("O2.no_class_for_%s" % name, ns["prod_pose_rig_class"](reg, other) is None)
    pinned = copy.deepcopy(base)
    pinned["rig_classes"]["krystal-v1"]["models"][0]["checksum"] = "abc"
    data = json.dumps(pinned).encode("utf-8")
    preg = ns["prod_pose_registry_parse"](data, sha(data))
    check("O2.checksum_mismatch_no_class", ns["prod_pose_rig_class"](preg, model, "abd") is None)
    check("O2.checksum_match_class", ns["prod_pose_rig_class"](preg, model, "abc") == "krystal-v1")
    return reg, base


def section_compatibility(ns, reg, base, golden):
    rec = make_record(ns, golden)
    prod = ns["prod_pose_registry_select"](reg, u"production")
    qual = ns["prod_pose_registry_select"](reg, u"qualification")
    check("O3.production_lists_only_the_qualified_left_arm",
          ns["prod_pose_browse_eligible"](prod, rec, "krystal-v1") == ["left_arm"])
    draft = copy.deepcopy(base)
    draft["mappings"][0].update(status="experimental", evidence=None)
    data = json.dumps(draft).encode("utf-8")
    dsel = ns["prod_pose_registry_select"](ns["prod_pose_registry_parse"](data, sha(data)), u"production")
    check("O3.production_lists_nothing_while_experimental",
          ns["prod_pose_browse_eligible"](dsel, rec, "krystal-v1") == [])
    check("O3.qualification_both_arms", ns["prod_pose_browse_eligible"](qual, rec, "krystal-v1") ==
          ["left_arm", "right_arm"])
    one = copy.deepcopy(base)
    one["mappings"][0].update(status="qualified", evidence="TEST-ONLY")
    data = json.dumps(one).encode("utf-8")
    sel = ns["prod_pose_registry_select"](ns["prod_pose_registry_parse"](data, sha(data)), u"production")
    check("O3.one_arm_eligible", ns["prod_pose_browse_eligible"](sel, rec, "krystal-v1") == ["left_arm"])
    check("O3.no_destination_class", ns["prod_pose_browse_eligible"](qual, rec, None) == [])
    check("O3.other_destination_class", ns["prod_pose_browse_eligible"](qual, rec, "lola-v1") == [])


def section_coordinates(ns, reg, golden, w2):
    tol = reg["profiles"]["arm_left_v1"]["tolerances"]
    region = make_record(ns, golden)["pose"]["regions"]["left_arm"]
    rng = random.Random(20261030)
    mismatches, cross, n = [], [], 0
    frames = [(([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]), ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]))]
    s = math.sqrt(0.5)
    frames.append(((10.0, 20.0, 30.0), [0.0, 0.0, s, s]))
    frames = [frames[0], ((list(frames[1][0]), frames[1][1]), ([5.0, -7.0, 0.0], [0.0, 0.0, s, s]))]
    for _ in range(200):
        frames.append((rand_frame(rng), rand_frame(rng)))
    for anchor, root in frames:
        reference = rand_quat(rng)
        dst = {"handles": {"CollarL": {"world_position": anchor[0], "world_orientation": anchor[1]},
                           "rig_root": {"world_position": root[0], "world_orientation": root[1]}}}
        wa = w2.plan_quaternion(golden, dst, reference)
        wb = w2.plan_matrix(golden, dst, reference)
        a = ns["prod_pose_plan_quaternion"](region, anchor, root, reference)
        b = ns["prod_pose_plan_matrix"](region, anchor, root, reference)
        n += 1
        if (a["hand_position"], a["hand_orientation"], a["elbow_position"], a["negated"]) != \
                (wa["Hand_l_p"], wa["Hand_l_o"], wa["Elbow_l_p"], wa["negated"]) or \
                (b["hand_position"], b["hand_orientation"], b["elbow_position"]) != \
                (wb["Hand_l_p"], wb["Hand_l_o"], wb["Elbow_l_p"]):
            mismatches.append(n)
        c = ns["prod_pose_cross_check"](a, b, tol)
        wc = w2.cross_check(wa, wb, tol)
        if c["agree"] != wc["agree"] or not c["agree"]:
            cross.append(n)
    check("O4.both_paths_bit_identical_to_w2_oracle_%d_frames" % n, not mismatches, mismatches[:5])
    conv = []
    for k in range(3000):
        q = rand_quat(rng) if k % 3 else [rng.uniform(-1, 1) * 0.05, rng.uniform(-1, 1), rng.uniform(-1, 1),
                                          rng.uniform(-1, 1) * 0.05]
        m_ours, m_w2 = ns["prod_pose_mb_from_quaternion"](q), w2.mb_from_quaternion(q)
        if m_ours != m_w2 or ns["prod_pose_mb_to_quaternion"](m_ours) != w2.mb_to_quaternion(m_w2):
            conv.append(k)
    check("O4.matrix_conversions_bit_identical_to_w2_including_negative_trace", not conv, conv[:5])
    check("O4.cross_check_agrees_like_w2", not cross, cross[:5])
    anchor, root = frames[1]
    a = ns["prod_pose_plan_quaternion"](region, anchor, root, [0.0, 0.0, 0.0, 1.0])
    flipped = ns["prod_pose_plan_quaternion"](region, anchor, root, [-c for c in a["hand_orientation"]])
    check("O4.hemisphere_follows_reference", flipped["hand_orientation"] == [-c for c in a["hand_orientation"]]
          and flipped["negated"] != a["negated"])
    hand_world = ns["prod_pose_compose"](anchor, (region["goals"]["hand"]["position"],
                                                  region["goals"]["hand"]["orientation"]))[0]
    moved_root = (list(map(lambda v: v + 100.0, root[0])), rand_quat(rng))
    other = ns["prod_pose_plan_quaternion"](region, anchor, moved_root, [0.0, 0.0, 0.0, 1.0])
    check("O4.hand_world_is_collar_relative_regardless_of_root",
          ns["prod_pose_distance"](other["hand_world_position"], hand_world) < 1e-9 and
          ns["prod_pose_distance"](a["hand_world_position"], hand_world) < 1e-9)
    back = ns["prod_pose_compose"](moved_root, (other["hand_position"], other["hand_orientation"]))[0]
    check("O4.local_plan_reconstructs_world_goal_through_root", ns["prod_pose_distance"](back, hand_world) < 1e-3)
    upper = ns["prod_pose_compose"](anchor, (region["oracle"]["upper_arm_origin"], [0.0, 0.0, 0.0, 1.0]))[0]
    check("O4.shoulder_guard_passes_on_match",
          ns["prod_pose_shoulder_guard"](region, anchor, upper, tol) < 1e-9)
    refuses("O4.shoulder_guard_refuses_miss", "rig-differs",
            lambda: ns["prod_pose_shoulder_guard"](region, anchor, [upper[0] + 0.002, upper[1], upper[2]], tol))
    plan, checks = ns["prod_pose_plan_region"](region, anchor, root, [0.0, 0.0, 0.0, 1.0], upper, tol)
    check("O4.plan_region_agrees", checks["agree"])
    b_plan = ns["prod_pose_plan_matrix"](region, anchor, root, [0.0, 0.0, 0.0, 1.0])
    opposite = dict(b_plan, hand_orientation=[-c for c in b_plan["hand_orientation"]])
    check("O4.cross_check_rejects_opposite_hemisphere", not ns["prod_pose_cross_check"](plan, opposite, tol)["agree"])
    original = ns["prod_pose_plan_matrix"]
    try:
        def skewed(*args):
            out = original(*args)
            out["hand_position"] = [out["hand_position"][0] + 0.01] + out["hand_position"][1:]
            return out
        ns["prod_pose_plan_matrix"] = skewed
        refuses("O4.path_disagreement_refuses", "plan",
                lambda: ns["prod_pose_plan_region"](region, anchor, root, [0.0, 0.0, 0.0, 1.0], upper, tol))
    finally:
        ns["prod_pose_plan_matrix"] = original
    profile = reg["profiles"]["arm_left_v1"]
    written = set(c[0] for c in profile["written_channels"].values())
    check("O4.write_set_excludes_root_pelvis_spine_collar", not (written & set(
        ["rig_root", "rig_pelvis", "CollarL", "CollarR", "rig_spine_0", "rig_spine_4"])), sorted(written))
    right = make_record(ns, golden)["pose"]["regions"]["right_arm"]
    ra = ns["prod_pose_plan_quaternion"](right, anchor, root, [0.0, 0.0, 0.0, 1.0])
    check("O4.right_arm_uses_identical_mathematics", ra["hand_position"] == a["hand_position"])


def section_time(ns):
    base = {u"t_doc": 1667, u"shots": [{u"id": u"shot14", u"start": 0, u"end": 1667},
                                       {u"id": u"shot15", u"start": 1667, u"end": 5000}],
            u"token_shot": u"shot15", u"sfm_current_shot": u"shot15", u"t_shot": 51667,
            u"path": {u"shot": u"shot15", u"clips": [u"krystal_channels"]},
            u"channels": dict((n, {u"clip": u"krystal_channels", u"converted": 50000, u"reported": 50000,
                                   u"reverse": 51667}) for n in (u"Hand_l_p", u"Hand_l_o", u"Elbow_l_p"))}
    got = ns["prod_pose_time_decide"](base)
    check("O5.fixture_like_domains_kept_separate", (got["t_doc"], got["t_shot"], got["t_chan"], got["shot"]) ==
          (1667, 51667, 50000, u"shot15"), got)
    check("O5.start_boundary_owned_by_this_shot", got["shot"] == u"shot15")
    offset = copy.deepcopy(base)
    for ch in offset[u"channels"].values():
        ch.update(converted=48500, reported=48500)
    check("O5.ordinary_clip_offset_accepted", ns["prod_pose_time_decide"](offset)["t_chan"] == 48500)

    def variant(fn):
        r = copy.deepcopy(base)
        fn(r)
        return lambda: ns["prod_pose_time_decide"](r)
    refuses("O5.end_boundary_belongs_to_next_shot", "time-mapping",
            variant(lambda r: r.update({u"t_doc": 5000, u"shots": r[u"shots"] + [{u"id": u"shot16", u"start": 5000,
                                                                                  u"end": 9000}]})))
    refuses("O5.end_boundary_without_next_shot", "time-mapping", variant(lambda r: r.update({u"t_doc": 5000})))
    refuses("O5.two_candidate_shots", "time-mapping",
            variant(lambda r: r[u"shots"].append({u"id": u"overlay", u"start": 1000, u"end": 3000})))
    refuses("O5.owner_is_not_token_shot", "time-mapping", variant(lambda r: r.update({u"token_shot": u"shot14"})))
    refuses("O5.sfm_current_shot_disagrees", "time-mapping",
            variant(lambda r: r.update({u"sfm_current_shot": u"shot14"})))
    refuses("O5.path_in_other_shot", "time-mapping", variant(lambda r: r[u"path"].update({u"shot": u"shot14"})))
    refuses("O5.two_clips_on_path", "time-mapping", variant(lambda r: r[u"path"][u"clips"].append(u"nested")))
    refuses("O5.channel_in_other_clip", "time-mapping",
            variant(lambda r: r[u"channels"][u"Hand_l_o"].update({u"clip": u"peer_channels"})))
    # NQ-1 KP-1: GetCurrentTime ('reported') changes while the playhead stays still; it is diagnostic, never decides.
    for label, tweak in ((u"stale_by_91_ticks", lambda r: [c.update({u"reported": 50091})
                                                            for c in r[u"channels"].values()]),
                         (u"absent", lambda r: [c.pop(u"reported") for c in r[u"channels"].values()])):
        try:
            got_r = variant(tweak)()
        except Exception as exc:
            got_r = exc
        check("O5.reported_clock_is_diagnostic_" + label, isinstance(got_r, dict) and got_r == got, got_r)
    refuses("O5.channels_disagree", "time-mapping",
            variant(lambda r: r[u"channels"][u"Elbow_l_p"].update({u"converted": 50001, u"reported": 50001})))
    refuses("O5.reverse_not_exact", "time-mapping",
            variant(lambda r: r[u"channels"][u"Hand_l_p"].update({u"reverse": 51666})))
    refuses("O5.scaled_rounding_inexact", "time-mapping",
            variant(lambda r: [c.update({u"converted": 25000, u"reported": 25000, u"reverse": 51666})
                               for c in r[u"channels"].values()]))
    refuses("O5.float_ticks_refused", "time-mapping", variant(lambda r: r.update({u"t_doc": 1667.0})))
    refuses("O5.bool_ticks_refused", "time-mapping",
            variant(lambda r: r[u"channels"][u"Hand_l_p"].update({u"converted": True})))
    refuses("O5.inverted_shot_range", "time-mapping",
            variant(lambda r: r[u"shots"].append({u"id": u"bad", u"start": 9000, u"end": 8000})))
    refuses("O5.no_channels", "time-mapping", variant(lambda r: r.update({u"channels": {}})))


def snap(name, kind, times, values, **extra):
    s = {u"name": name, u"kind": kind, u"mode": 3, u"layer_count": 1,
         u"log_type": u"DmeQuaternionLog" if kind == u"quaternion" else u"DmeVector3Log",
         u"layer_type": u"DmeQuaternionLogLayer" if kind == u"quaternion" else u"DmeVector3LogLayer",
         u"curveinfo": u"absent", u"curvetypes": u"absent", u"compressed": u"absent", u"defaults": [0.0],
         u"bookmarks": [], u"times": list(times), u"values": [list(v) for v in values], u"unreadable": []}
    s.update(extra)
    return s


def section_keys(ns):
    f32 = ns["prod_pose_f32"]
    vt = (u"DmeVector3Log", u"DmeVector3LogLayer")
    qt = (u"DmeQuaternionLog", u"DmeQuaternionLogLayer")
    vals = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
    v = snap(u"Hand_l_p", u"vector", [1000, 2000, 3000], vals)
    planned = [0.1, 0.2, 0.3]
    p = ns["prod_pose_key_plan"](v, 2000, planned, vt)
    check("O6.update_at_exact_key", (p["action"], p["index"]) == ("update", 1), p)
    check("O6.float32_value", p["value"] == [f32(x) for x in planned])
    same = snap(u"Hand_l_p", u"vector", [1000, 2000, 3000], [vals[0], [f32(0.1), f32(0.2), f32(0.3)], vals[2]])
    check("O6.equal_exact_key_is_none", ns["prod_pose_key_plan"](same, 2000, planned, vt)["action"] == "none")
    for name, t, idx in (("between", 1500, 1), ("before_first", 500, 0), ("after_last", 3500, 3)):
        p = ns["prod_pose_key_plan"](v, t, planned, vt)
        check("O6.insert_%s" % name, (p["action"], p["index"]) == ("insert", idx), p)
    # Native key values are float32; stored fixture keys are therefore float32-exact.
    near = snap(u"Hand_l_p", u"vector", [1000, 1501, 3000], vals)
    p = ns["prod_pose_key_plan"](near, 1500, planned, vt)
    check("O6.insert_before_key_one_tick_later", (p["action"], p["index"]) == ("insert", 1), p)
    q0, q1 = [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, f32(0.38268343), f32(0.92387953)]
    qs = snap(u"Hand_l_o", u"quaternion", [1000, 2000], [q0, q1], evaluated_at_t=[0.0, 0.0, 0.2, 0.98])
    neg = [-c for c in q1]
    p = ns["prod_pose_key_plan"](qs, 2000, neg, qt)
    check("O6.quaternion_update_takes_replaced_key_hemisphere_and_is_none",
          p["action"] == "none" and p["value"] == [f32(c) for c in q1], p)
    p = ns["prod_pose_key_plan"](qs, 1500, [-c for c in q1], qt)
    check("O6.quaternion_insert_takes_evaluated_hemisphere", p["action"] == "insert" and p["value"][3] > 0, p)
    no_ref = dict(qs)
    no_ref.pop("evaluated_at_t")
    refuses("O6.insert_without_evaluated_reference", "evidence-unreadable",
            lambda: ns["prod_pose_key_plan"](no_ref, 1500, q1, qt))
    straddle = snap(u"Hand_l_o", u"quaternion", [1000, 2000], [q0, [0.0, 0.0, -0.38268343, -0.92387953]],
                    evaluated_at_t=q0)
    refuses("O6.sign_straddle_refused", "structure-unsupported",
            lambda: ns["prod_pose_key_plan"](straddle, 1500, q1, qt))
    bad = [("zero_keys", snap(u"x", u"vector", [], [])),
           ("duplicate_times", snap(u"x", u"vector", [1000, 1000], vals[:2])),
           ("non_increasing", snap(u"x", u"vector", [2000, 1000], vals[:2])),
           ("curvetypes_present", snap(u"x", u"vector", [1000], vals[:1], curvetypes=u"present")),
           ("curveinfo_present", snap(u"x", u"vector", [1000], vals[:1], curveinfo=u"present")),
           ("compressed_present", snap(u"x", u"vector", [1000], vals[:1], compressed=u"present")),
           ("mode_1", snap(u"x", u"vector", [1000], vals[:1], mode=1)),
           ("two_layers", snap(u"x", u"vector", [1000], vals[:1], layer_count=2)),
           ("unreadable_field", snap(u"x", u"vector", [1000], vals[:1], unreadable=[u"bookmarks"])),
           ("too_many_keys", snap(u"x", u"vector", list(range(50001)), [[0.0, 0.0, 0.0]] * 50001)),
           ("values_length", snap(u"x", u"vector", [1000, 2000], vals[:1]))]
    evidence_cases = ("unreadable_field",)
    for name, s in bad:
        refuses("O6.refused.%s" % name, "evidence-unreadable" if name in evidence_cases else "structure-unsupported",
                lambda s=s: ns["prod_pose_key_plan"](s, 1500, planned, vt))
    refuses("O6.refused.wrong_types", "structure-unsupported",
            lambda: ns["prod_pose_key_plan"](v, 1500, planned, qt))
    section_strict_evidence(ns, v, vt, qt, planned)
    none = {u"action": u"none"}
    ok = {u"rig_inputs_ok": True, u"skeletal_oracle_ok": True}
    check("O6.true_noop", ns["prod_pose_noop_test"]([none, none, none], ok))
    check("O6.missing_key_is_not_noop", not ns["prod_pose_noop_test"]([none, {u"action": u"insert"}, none], ok))
    check("O6.update_is_not_noop", not ns["prod_pose_noop_test"]([none, {u"action": u"update"}], ok))
    check("O6.noop_needs_rig_inputs", not ns["prod_pose_noop_test"]([none], {u"rig_inputs_ok": False,
                                                                             u"skeletal_oracle_ok": True}))
    check("O6.noop_needs_skeletal_oracle", not ns["prod_pose_noop_test"]([none], {u"rig_inputs_ok": True}))
    check("O6.empty_plan_is_not_noop", not ns["prod_pose_noop_test"]([], ok))


def section_strict_evidence(ns, v, vt, qt, planned):
    """P1-2: complete, well-formed evidence is required; missing is never absence."""
    for field in ("name", "kind", "mode", "layer_count", "log_type", "layer_type", "curveinfo", "curvetypes",
                  "compressed", "defaults", "bookmarks", "times", "values", "unreadable"):
        s = copy.deepcopy(v)
        del s[field]
        refuses("P1_2.missing_%s_refused" % field, "evidence-unreadable",
                lambda s=s: ns["prod_pose_key_plan"](s, 2000, planned, vt), "missing evidence")
    cases = [("fractional_ticks", dict(v, times=[1000.5, 2000.5, 3000.5])),
             ("bool_tick", dict(v, times=[True, 2000, 3000])),
             ("float_integral_tick", dict(v, times=[1000.0, 2000, 3000])),
             ("nan_key_value", dict(v, values=[[float("nan"), 0.0, 0.0]] + v["values"][1:])),
             ("inf_key_value", dict(v, values=[[float("inf"), 0.0, 0.0]] + v["values"][1:])),
             ("short_key_value", dict(v, values=[[1.0, 2.0]] + v["values"][1:])),
             ("bool_key_component", dict(v, values=[[True, 2.0, 3.0]] + v["values"][1:])),
             ("nan_default", dict(v, defaults=[float("nan")])),
             ("defaults_not_list", dict(v, defaults=None)),
             ("fractional_bookmark", dict(v, bookmarks=[1500.5])),
             ("unreadable_not_list", dict(v, unreadable="none")),
             ("curvetypes_unstated", dict(v, curvetypes=None)),
             ("mode_not_integer", dict(v, mode="3"))]
    for name, s in cases:
        refuses("P1_2.%s_refused" % name, "evidence-unreadable", lambda s=s: ns["prod_pose_key_plan"](s, 2000,
                                                                                                    planned, vt))
    for name, value in (("inf", [float("inf"), 2.0, 3.0]), ("nan", [float("nan"), 2.0, 3.0]), ("short", [1.0, 2.0]),
                        ("bool", [True, 2.0, 3.0]), ("text", ["1", 2.0, 3.0])):
        refuses("P1_2.planned_vector_%s_refused" % name, "invalid-input",
                lambda value=value: ns["prod_pose_key_plan"](v, 2000, value, vt))
    q = snap(u"Hand_l_o", u"quaternion", [1000, 2000], [[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]],
             evaluated_at_t=[0.0, 0.0, 0.0, 1.0])
    refuses("P1_2.planned_zero_quaternion_refused", "invalid-input",
            lambda: ns["prod_pose_key_plan"](q, 1500, [0.0, 0.0, 0.0, 0.0], qt))
    refuses("P1_2.planned_nan_quaternion_refused", "invalid-input",
            lambda: ns["prod_pose_key_plan"](q, 1500, [float("nan"), 0.0, 0.0, 1.0], qt))
    bad_ref = dict(q, evaluated_at_t=[float("nan"), 0.0, 0.0, 1.0])
    refuses("P1_2.nan_evaluated_reference_refused", "evidence-unreadable",
            lambda: ns["prod_pose_key_plan"](bad_ref, 1500, [0.0, 0.0, 0.0, 1.0], qt))
    p = ns["prod_pose_key_plan"](v, 1500, planned, vt)
    check("P1_2.valid_evidence_still_plans", p["action"] == "insert" and p["t"] == 1500, p)


def section_frames(ns, reg, golden):
    """P1-2: coordinate inputs must be finite and well formed; the shoulder guard never passes on NaN."""
    tol = reg["profiles"]["arm_left_v1"]["tolerances"]
    region = make_record(ns, golden)["pose"]["regions"]["left_arm"]
    ident = ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])
    nan = float("nan")
    refuses("P1_2.astra_nan_shoulder_refused", "invalid-input",
            lambda: ns["prod_pose_plan_region"](region, ident, ident, [0.0, 0.0, 0.0, 1.0], [nan, 0.0, 0.0], tol))
    for name, args in (("anchor_position", (([nan, 0.0, 0.0], ident[1]), ident, [0.0, 0.0, 0.0, 1.0])),
                       ("anchor_quaternion", ((ident[0], [nan, 0.0, 0.0, 1.0]), ident, [0.0, 0.0, 0.0, 1.0])),
                       ("root_position", (ident, ([float("inf"), 0.0, 0.0], ident[1]), [0.0, 0.0, 0.0, 1.0])),
                       ("root_zero_quaternion", (ident, (ident[0], [0.0, 0.0, 0.0, 0.0]), [0.0, 0.0, 0.0, 1.0])),
                       ("reference", (ident, ident, [nan, 0.0, 0.0, 1.0])),
                       ("malformed_frame", ((ident[0],), ident, [0.0, 0.0, 0.0, 1.0]))):
        for path in ("prod_pose_plan_quaternion", "prod_pose_plan_matrix"):
            refuses("P1_2.%s_%s_refused" % (path[10:], name), "invalid-input",
                    lambda path=path, args=args: ns[path](region, *args))
    upper = ns["prod_pose_compose"](ident, (region["oracle"]["upper_arm_origin"], [0.0, 0.0, 0.0, 1.0]))[0]
    check("P1_2.valid_shoulder_still_passes", ns["prod_pose_shoulder_guard"](region, ident, upper, tol) < 1e-9)
    tol_nan = dict(tol, collar_mapping=nan)
    refuses("P1_2.nan_tolerance_never_passes", "rig-differs",
            lambda: ns["prod_pose_shoulder_guard"](region, ident, upper, tol_nan))


def section_postconditions(ns):
    vt = (u"DmeVector3Log", u"DmeVector3LogLayer")
    vals = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
    before = snap(u"Hand_l_p", u"vector", [1000, 2000, 3000], vals)
    up = ns["prod_pose_key_plan"](before, 2000, [0.5, 0.5, 0.5], vt)
    after = copy.deepcopy(before)
    after["values"][1] = list(up["value"])
    check("O7.update_passes", ns["prod_pose_check_postconditions"](before, after, up) == [])
    ins = ns["prod_pose_key_plan"](before, 1500, [0.5, 0.5, 0.5], vt)
    after_i = copy.deepcopy(before)
    after_i["times"].insert(1, 1500)
    after_i["values"].insert(1, list(ins["value"]))
    check("O7.insert_passes", ns["prod_pose_check_postconditions"](before, after_i, ins) == [])
    none = {u"name": u"Hand_l_p", u"action": u"none", u"index": 1, u"t": 2000, u"value": vals[1]}
    check("O7.none_passes_when_unchanged", ns["prod_pose_check_postconditions"](before, before, none) == [])
    cases = []
    x = copy.deepcopy(after)
    x["values"][0] = [9.0, 9.0, 9.0]
    cases.append(("neighbour_value_changed_by_update", x, up))
    x = copy.deepcopy(after)
    x["values"][1] = [0.5, 0.5, 0.25]
    cases.append(("update_readback_not_exact", x, up))
    x = copy.deepcopy(after)
    x["times"][1] = 2001
    cases.append(("update_moved_time", x, up))
    x = copy.deepcopy(after_i)
    x["times"].append(4000)
    x["values"].append([0.0, 0.0, 0.0])
    cases.append(("insert_count_off", x, ins))
    x = copy.deepcopy(after_i)
    x["values"][0] = [0.0, 0.0, 0.0]
    cases.append(("insert_neighbour_changed", x, ins))
    x = copy.deepcopy(after_i)
    x["values"][1] = [0.5, 0.5, 0.0]
    cases.append(("insert_readback_not_exact", x, ins))
    x = copy.deepcopy(before)
    x["times"].insert(0, 1500)
    x["values"].insert(0, list(ins["value"]))
    cases.append(("insert_out_of_order", x, ins))
    x = copy.deepcopy(after)
    x["bookmarks"] = [1234]
    cases.append(("bookmarks_changed", x, up))
    x = copy.deepcopy(after_i)
    x["curvetypes"] = u"present"
    cases.append(("curvetypes_changed_unqualified", x, ins))
    x = copy.deepcopy(after)
    x["unreadable"] = [u"values"]
    cases.append(("after_state_unreadable", x, up))
    x = copy.deepcopy(before)
    x["values"][2] = [0.0, 0.0, 0.0]
    cases.append(("changed_although_none_planned", x, none))
    expect = {"neighbour_value_changed_by_update": "another key's value changed",
              "update_readback_not_exact": "updated value read back", "update_moved_time": "key times or count",
              "insert_count_off": "key count", "insert_neighbour_changed": "neighbouring keys changed",
              "insert_readback_not_exact": "inserted value read back", "insert_out_of_order": "neighbouring keys",
              "bookmarks_changed": "bookmarks changed", "curvetypes_changed_unqualified": "curvetypes changed",
              "after_state_unreadable": "after-state unreadable", "changed_although_none_planned":
              "changed although nothing was planned"}
    for name, a, plan in cases:
        problems = ns["prod_pose_check_postconditions"](before, a, plan)
        check("O7.detected.%s" % name, any(expect[name] in p for p in problems), problems)
    allowed = ns["prod_pose_check_postconditions"](before, dict(after_i, curvetypes=u"present"), ins,
                                                   allowed_metadata_changes=(u"curvetypes",))
    check("O7.only_explicitly_qualified_metadata_change_is_allowed", allowed == [], allowed)
    # P1-1: the observed insertion must be exactly at the requested tick, wherever it falls.
    for name, t, wrong, idx in (("astra_between", 1500, 1600, 1), ("before_first", 500, 400, 0),
                                ("after_last", 3500, 3600, 3), ("between_one_tick_early", 1500, 1499, 1)):
        plan = ns["prod_pose_key_plan"](before, t, [0.5, 0.5, 0.5], vt)
        check("P1_1.plan_carries_requested_tick_%s" % name, plan["t"] == t and plan["index"] == idx, plan)
        moved = copy.deepcopy(before)
        moved["times"].insert(idx, wrong)
        moved["values"].insert(idx, list(plan["value"]))
        problems = ns["prod_pose_check_postconditions"](before, moved, plan)
        check("P1_1.wrong_insert_time_detected_%s" % name, any("requested %d" % t in p for p in problems), problems)
        exact = copy.deepcopy(before)
        exact["times"].insert(idx, t)
        exact["values"].insert(idx, list(plan["value"]))
        check("P1_1.exact_insert_passes_%s" % name, ns["prod_pose_check_postconditions"](before, exact, plan) == [])
    untimed = dict(ins)
    del untimed["t"]
    check("P1_1.plan_without_requested_tick_refused", any("no exact requested tick" in p for p in
                                                          ns["prod_pose_check_postconditions"](before, after_i,
                                                                                               untimed)))
    for field in ("defaults", "bookmarks"):
        x = copy.deepcopy(after)
        del x[field]
        problems = ns["prod_pose_check_postconditions"](before, x, up)
        check("P1_2.after_missing_%s_detected" % field, any("after-state evidence incomplete" in p for p in problems),
              problems)
        y = copy.deepcopy(before)
        del y[field]
        problems = ns["prod_pose_check_postconditions"](y, after, up)
        check("P1_2.before_missing_%s_detected" % field, any("before-state evidence incomplete" in p
                                                             for p in problems), problems)
    frac = copy.deepcopy(after_i)
    frac["times"][1] = 1500.0
    check("P1_2.after_fractional_insert_tick_detected", ns["prod_pose_check_postconditions"](before, frac, ins) != [])
    nanv = copy.deepcopy(after)
    nanv["values"][1] = [float("nan")] * 3
    check("P1_2.after_nan_value_detected", ns["prod_pose_check_postconditions"](before, nanv, up) != [])
    check("P1_2.true_noop_still_passes", ns["prod_pose_check_postconditions"](before, before, dict(
        ns["prod_pose_key_plan"](before, 2000, [4.0, 5.0, 6.0], vt))) == [])


def section_ui(ns):
    ui = ns["prod_pose_ui_state"]
    labels = list(ns["PROD_POSE_LABELS"])
    check("O8.no_ellipsis_in_any_label", not [l for l in labels if u"..." in l or u"\u2026" in l])
    check("O8.no_ellipsis_in_any_message", not [m for m in ns["PROD_POSE_MESSAGES"].values()
                                                 if u"..." in m or u"\u2026" in m])
    base = {u"character": u"Krystal", u"supported": True, u"instance_valid": True, u"mode": u"this",
            u"visible_count": 3, u"search_active": False, u"busy": False, u"recovery_blocked": False,
            u"selected": None}
    s = ui(dict(base, character=None))
    check("O8.no_character", s["summary"] == [u"Choose a character model."] and not any(s["buttons"].values()))
    s = ui(dict(base, supported=False))
    check("O8.unsupported_tab_visible_message_and_save_disabled",
          s["summary"] == [u"Poses aren't available for this character yet."] and not s["buttons"]["save_new"]
          and s["list_message"].startswith(u"Poses aren't available"))
    s = ui(dict(base, instance_valid=False))
    check("O8.save_new_disabled_without_valid_instance", not s["buttons"]["save_new"])
    s = ui(base)
    check("O8.supported_with_instance_save_enabled", s["buttons"]["save_new"] and s["summary"] == [u"Select a pose."])
    check("O8.no_poses_message", ui(dict(base, visible_count=0))["list_message"] ==
          u"No saved poses for Krystal.")
    check("O8.no_compatible_message", ui(dict(base, visible_count=0, mode=u"compatible"))["list_message"] ==
          u"No poses from other characters can be used with Krystal yet.")
    check("O8.no_match_message", ui(dict(base, visible_count=0, search_active=True))["list_message"] ==
          u"No poses match your search.")
    both = {u"name": u"Arms Crossed", u"own": True, u"origin": u"Krystal", u"saved": [u"left_arm", u"right_arm"],
            u"availability": {u"left_arm": u"available", u"right_arm": u"available"}, u"unusable": False,
            u"favorite": False}
    s = ui(dict(base, selected=both))
    check("O8.full_summary_text", s["summary"] == [u"From: Krystal \u00b7 Saved: Both arms \u00b7 Available: Both arms"],
          s["summary"])
    check("O8.full_apply_direct", s["apply_mode"] == "direct" and s["buttons"]["apply_pose"] and
          s["buttons"]["choose_parts"])
    check("O8.own_actions_enabled", all(s["buttons"][k] for k in ("update_pose", "rename", "delete_pose",
                                                                 "favorite", "pose_info")))
    part = dict(both, availability={u"left_arm": u"available", u"right_arm": u"rig-differs"})
    s = ui(dict(base, selected=part))
    check("O8.partial_opens_dialog_with_reason", s["apply_mode"] == "dialog" and s["summary"] == [
        u"From: Krystal \u00b7 Saved: Both arms \u00b7 Available: Left arm",
        u"Right arm: the arm rig differs from the one this pose was saved on."], s["summary"])
    foreign = dict(both, own=False, origin=u"Lola")
    s = ui(dict(base, selected=foreign, mode=u"compatible"))
    check("O8.foreign_locked_and_explained",
          not any(s["buttons"][k] for k in ("update_pose", "rename", "delete_pose")) and
          s["buttons"]["favorite"] and s["buttons"]["apply_pose"] and
          s["summary"][-1] == u"This pose is in Lola's library. You can apply it here, but not change it." and
          s["tooltips"].get("delete_pose") == u"Poses from another character's library can't be changed here.")
    unknown = dict(both, availability={u"left_arm": None, u"right_arm": None})
    s = ui(dict(base, selected=unknown))
    check("O8.unknown_availability_no_apply", not s["buttons"]["apply_pose"] and
          s["summary"][0].endswith(u"Available: select the character in the scene to check."))
    none_avail = dict(both, availability={u"left_arm": u"rig-differs", u"right_arm": u"not-qualified"})
    s = ui(dict(base, selected=none_avail))
    check("O8.nothing_available_apply_disabled", not s["buttons"]["apply_pose"] and
          s["summary"][0].endswith(u"Available: None"))
    s = ui(dict(base, selected=dict(both, unusable=True)))
    check("O8.unusable_file_only_delete", s["summary"] == [u"This pose file can't be read. It won't be applied."]
          and sorted(k for k, v in s["buttons"].items() if v) == [u"delete_pose", u"save_new"])
    s = ui(dict(base, selected=both, busy=True))
    check("O8.busy_disables_everything", not any(s["buttons"].values()))
    s = ui(dict(base, selected=both, recovery_blocked=True))
    check("O8.recovery_block_disables_scene_mutations_only",
          not any(s["buttons"][k] for k in ("apply_pose", "choose_parts", "save_new", "update_pose")) and
          all(s["buttons"][k] for k in ("rename", "delete_pose", "favorite", "pose_info")))
    check("O8.favorite_label", ui(dict(base, selected=dict(both, favorite=True)))["favorite_label"] ==
          u"Remove Favorite")
    d = ns["prod_pose_parts_dialog_state"]([u"left_arm", u"right_arm"],
                                           {u"left_arm": u"available", u"right_arm": u"rig-differs"}, True)
    check("O8.partial_dialog_no_default_button", d["apply_default_button"] is False and d["partial_note"])
    check("O8.partial_dialog_rows", [(r["region"], r["enabled"], r["checked"]) for r in d["rows"]] ==
          [(u"left_arm", True, True), (u"right_arm", False, False)])
    d2 = ns["prod_pose_parts_dialog_state"]([u"left_arm"], {u"left_arm": u"available"}, False)
    check("O8.choose_parts_dialog_default_button", d2["apply_default_button"] is True and d2["apply_enabled"])
    d3 = ns["prod_pose_parts_dialog_state"]([u"left_arm"], {u"left_arm": u"rig-differs"}, True)
    check("O8.nothing_checked_apply_disabled", d3["apply_enabled"] is False)


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        return 2
    print("Interpreter: %s" % sys.version.split()[0])
    ns, block, names = load_namespace()
    check("extract.block_present", len(names) > 40, len(names))
    static_check(block)
    if not w2_verified():
        print("RESULT: W2 oracle files do not verify; stopping")
        return 1
    w2 = load_w2_core()
    golden = json.loads(read(os.path.join(W2_DIR, "tests", "fixtures", "golden_left_arm_pose.f01w2.json"))
                        .decode("utf-8"))
    raw = read(REGISTRY_PATH)
    reg, base = section_registry(ns, raw, golden)
    for label, fn in (("records", lambda: section_records(ns, reg, golden)),
                      ("compatibility", lambda: section_compatibility(ns, reg, base, golden)),
                      ("coordinates", lambda: section_coordinates(ns, reg, golden, w2)),
                      ("time", lambda: section_time(ns)), ("keys", lambda: section_keys(ns)),
                      ("frames", lambda: section_frames(ns, reg, golden)),
                      ("postconditions", lambda: section_postconditions(ns)), ("ui", lambda: section_ui(ns))):
        try:
            fn()
            check("section.%s.completed" % label, True)
        except Exception as exc:
            check("section.%s.completed" % label, False, "%s: %s" % (type(exc).__name__, exc))
    failed = [r for r in RESULTS if not r[1]]
    print("RESULT: %d/%d PASS (%s)" % (len(RESULTS) - len(failed), len(RESULTS), sys.version.split()[0]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
