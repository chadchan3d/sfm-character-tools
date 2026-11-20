# -*- coding: utf-8 -*-
"""F-01 Stage 2, declared JIGGLE leaf compatibility: offline qualification of the simulated-leaf admission and output
exemption in the structural rig adapter (prod_body_rig_*, stage E part 4) of the CPM application source.

Authority: Astra's ruling (cpm/qualification/F01_STAGE2_ASTRA_JIGGLE_RULING.md, the original ACCEPT WITH CONDITIONS
adjudication), the scope F01_STAGE2_JIGGLE_LEAF_SCOPE.md and the Designer's "F-01 Stage 2 - Implementation
Authorization" (checkpoint f286a18).

Technique: the Stage 1 suite's harness (test_cpm_app_f01_structural_rig, itself the stage E harness), with
fixtures/f01_body/tails_shot15.json, derived read-only by f01_dmx_body_fixture.py from the Owner's RC1 smoke session
(the R2 fixture 259ea8a6...): Tails' real stock rig_biped_simple rig, bones, controls, channels, keys and operators.
The studio header is native-shaped (H1's fake Header: the fixture skeleton, Tails' seven JIGGLE bones declared with
flags 0x504 as in the model file) and the vs.studio constants are the values read natively by NQ-03.
fake_sfm_body.simulate_jiggle models SFM's simulated output: the leaves' transforms move after every evaluation
while their channels and keys stay. Tails is a qualification fixture, not a supported character: nothing in CPM names
it. Nothing here demonstrates native SFM behaviour.

Usage: --phase=run (Python 2.7.5 and Python 3.10). The older-reader checks read the Stage 1 candidate (f286a18) and
RC2 (ede599f) from Git.
"""
from __future__ import print_function

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import types

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_f01_pose_core as core  # noqa: E402
import test_cpm_app_f01_body as B  # noqa: E402
import test_cpm_app_f01_structural_rig as R  # noqa: E402  (its helpers; it sets B.IDENTITY, reset below)
import fake_sfm_body as FB  # noqa: E402

FIXTURE = os.path.join(_THIS_DIR, "fixtures", "f01_body", "tails_shot15.json")
FIXTURE_SHA256 = "5b9601b92c816215e60210648e05b4b1e945eb8370206a7c14583d950d7285fd"
MODEL = u"models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl"
IDENTITY = {"model": MODEL, "checksum": 4321, "animset_name": u"milestailsprower1"}
STAGE1_COMMIT = "f286a18"            # the Stage 1 candidate CPM 7259e80a... (Stage 1 closed)
STAGE1_SHA256 = u"7259e80a5d462eba1aeaa25cf89e9f57cf1081caaeac3002de8db6fbe488ab55"
RC2_COMMIT = "ede599f"
LEAVES = [u"HairSpike_B3", u"HairSpike_M3", u"HairSpike_T3", u"Tail6_L", u"Tail6_R", u"ear3_L", u"ear3_R"]
JIGGLE, JIGGLE_FLAGS = 5, 0x504      # the model header (F01_STAGE2_JIGGLE_LEAF_SCOPE.md section 2)
CONSTANTS = {"STUDIO_PROC_QUATINTERP": 2, "STUDIO_PROC_JIGGLE": 5, "BONE_PHYSICALLY_SIMULATED": 1,
             "BONE_PHYSICS_PROCEDURAL": 2, "BONE_ALWAYS_PROCEDURAL": 4, "BONE_SCREEN_ALIGN_SPHERE": 8,
             "BONE_SCREEN_ALIGN_CYLINDER": 16}          # vs.studio, read natively (NQ-03)
RESULTS = B.RESULTS
check, outcome, refused = B.check, B.outcome, B.refused
QUAL, PROD = u"qualification", u"production"
FB_DATA = []


# --- the native-shaped studio header (as H1's suite) -----------------------------------------------------------------

class Obj(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Bone(object):
    def __init__(self, name, parent, flags, proctype):
        self.name, self.parent, self.flags, self.proctype = name, parent, flags, proctype

    def pszName(self):
        return self.name


class Header(object):
    def __init__(self, rows, attachments, drivers):
        self.rows, self.attachments, self.drivers = rows, list(attachments), list(drivers)
        self.numbones = len(rows)
        self.numlocalattachments = len(self.attachments)

    def pBone(self, i):
        r = self.rows[i]
        return Bone(r["name"], r["parent"], r["flags"], r["proctype"])

    def pLocalAttachment(self, i):
        return Obj(localbone=self.attachments[i])

    def BoneFlexDriverCount(self):
        return len(self.drivers)

    def BoneFlexDriver(self, i):
        return Obj(m_nBoneIndex=self.drivers[i])


def header_rows(fx, declared=None):
    declared = dict((n, (JIGGLE, JIGGLE_FLAGS)) for n in LEAVES) if declared is None else declared
    index = dict((n, b[u"index"]) for n, b in fx[u"bones"].items())
    rows = [None] * len(index)
    for n, b in fx[u"bones"].items():
        proc, flags = declared.get(n, (0, 0x100))
        rows[b[u"index"]] = {"name": n, "parent": index[b[u"parent"]] if b[u"parent"] else -1, "flags": flags,
                             "proctype": proc}
    return rows


def attachments_of(fx):
    return [fx[u"bones"][n][u"index"] for n in (u"bip_head", u"bip_hand_L", u"bip_hand_R")]


def attach(w, rows=None, attachments=None, drivers=(), constants=None):
    hdr = Header(rows if rows is not None else header_rows(w.fx),
                 attachments_of(w.fx) if attachments is None else attachments, drivers)
    w.gm.GetStudioHdr = lambda: hdr
    w.studio_constants = dict(CONSTANTS) if constants is None else constants
    return hdr


def world(fx, prepare=None, posed=True, simulate=True, header=True, **kw):
    w = FB.World(fx)
    if header:
        attach(w, **kw)
    if posed:
        pose_differently(w)
    if prepare is not None:
        prepare(w)
        w.evaluate()
    if simulate:
        FB.simulate_jiggle(w, LEAVES)
    return w


def use(ns, w):
    B.use_world(ns, w)
    if hasattr(w, "studio_constants"):
        mod = types.ModuleType("vs.studio")
        for k, v in w.studio_constants.items():
            setattr(mod, k, v)
        ns["vs"].studio = mod
    return w


def pose_differently(w):
    """A distinctly posed and placed destination: every written rig handle turned and moved, the directly animated
    fingers, tails and ears turned (FK positions untouched: A1), the placement moved and turned. The simulated leaves'
    own authored values are changed separately (leaf_keys)."""
    for name, ch in w.channels.items():
        layer = ch.attrs["log"].layer
        if not layer.keys or layer.value_kind is None or name[:-2] in LEAVES:
            continue
        handle = name.startswith(u"rig_") and not name.startswith((u"rig_root", u"rig_footHelper"))
        fk = name.endswith(u"_o") and any(t in name for t in (u"Finger", u"Tail", u"ear", u"Hair"))
        if not (handle or fk or name in (u"rig_root_p", u"rig_root_o")):
            continue
        if name in (u"rig_elbow_L_o", u"rig_elbow_R_o", u"rig_knee_L_o", u"rig_knee_R_o"):
            continue
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


def leaf_keys(w, degrees=25.0):
    """The destination's own authored jiggle values differ from the source's (they are kept, never compared)."""
    for n in LEAVES:
        layer = w.channels[n + u"_o"].attrs["log"].layer
        for k in layer.keys:
            k[1] = FB.native(B.rotate(FB.plain(k[1]), [0.0, 1.0, 0.0], degrees), "quat")
    w.evaluate()


def ctx(ns):
    return B.live_context(ns)


def authorize(ns, reg, label, item=None, mode=QUAL):
    return ns["prod_body_rig_authorize"](ctx(ns), IDENTITY, reg, mode, label, item)


def discovered(ns, w):
    use(ns, w)
    row = ns["prod_resolve_instance"](ctx(ns)[u"instance"])
    L = ns["prod_body_live"](row, None)
    t = ns["prod_pose_time_read"](L, ns["prod_body_rig_time_names"](L))
    return ns["prod_body_discover"](L, t[u"t_chan"], ns["prod_pose_writer_index"]())


def no_mutation(w):
    return not B.scene_writes(w) and not w.dm.calls


def library(root, name):
    if not os.path.isdir(os.path.join(root, name)):
        os.makedirs(os.path.join(root, name))
    return {u"character_key": u"milestailsprower", u"char_dir": os.path.join(root, name, u"Characters",
                                                                              u"milestailsprower"),
            u"library_root": os.path.join(root, name), u"model_ref": MODEL, u"checksum": 4321}


def save(ns, reg, lib, name):
    auth = authorize(ns, reg, u"Save Pose")
    pinned = ns["prod_body_current_time"](IDENTITY, auth, reg)
    pose = ns["prod_body_capture"](IDENTITY, auth, reg, pinned_time=pinned)
    saved = ns["prod_pose_save_new"](lib, name, pose, u"20261119-120000-000000", reg)
    item = [i for i in ns["prod_pose_discover"](lib[u"char_dir"], lib[u"character_key"], reg)[u"items"]
            if i[u"record"][u"preset_id"] == saved[u"record"][u"preset_id"]][0]
    return pose, saved, item


def apply_(ns, reg, item, w, mode=QUAL):
    use(ns, w)
    auth = authorize(ns, reg, u"Apply Pose", item, mode=mode)
    return auth, outcome(lambda: ns["prod_body_apply"](IDENTITY, auth, item, reg))


def verify(ns, auth, got):
    if got[0] != u"ok" or not got[1].get(u"pending"):
        return None
    return ns["prod_pose_deferred_verify"](dict(got[1][u"pending"], authorization=auth))


def posture(w, skip=LEAVES):
    rel = B.placement_relative(w, u"rig_root")
    return dict((n, v) for n, v in rel.items() if n not in skip)


def leaf_channels():
    return sorted([n + u"_o" for n in LEAVES] + [n + u"_p" for n in LEAVES])


def last_refusals(ns):
    line = R.last_log(ns, u"BODY-RIG-leaf-refused")
    d = R.log_detail(line) if line else None
    return (d or {}).get(u"refusals") or {}


# ---------------------------------------------------------------------------
# A. Admission: exactly the declared JIGGLE leaves, by mechanism and relationships
# ---------------------------------------------------------------------------

def section_admission(ns, fx, reg):
    D = discovered(ns, world(fx, posed=False, simulate=False))
    got = outcome(lambda: ns["prod_body_rig_draft"](D))
    check("A.tails_drafts_with_its_declared_jiggle_leaves", got[0] == u"ok", got)
    P = got[1]
    check("A.exactly_the_seven_leaves_are_simulated_leaves", P.get(u"simulated_leaf_bones") == LEAVES,
          P.get(u"simulated_leaf_bones"))
    check("A.no_passive_or_preserved_bones", P[u"passive_channel_bones"] == [] and P[u"preserved_fk_bones"] == [])
    check("A.rig_roles_as_for_fox", P[u"placement_handle"] == u"rig_root" and len(P[u"constraints"]) == 34 and
          P[u"helper_handles"] == [u"rig_footHelper_L", u"rig_footHelper_R"] and P[u"descriptor_rig_name"] ==
          u"@structural", (P[u"placement_handle"], len(P[u"constraints"])))
    C = ns["prod_body_classify"](D, P)
    bones, roles = B.counts(C[u"bones"].values()), B.counts(C[u"channels"].values())
    check("A.classification_constrained_fk_and_simulated_leaf", bones == {
        u"constrained": 22, u"fk": 102, u"simulated-leaf": 7}, bones)
    check("A.simulated_leaf_is_its_own_class_not_passive", u"passive" not in bones and all(
        C[u"bones"][n] == u"simulated-leaf" for n in LEAVES))
    leafch = sorted(n for n, r in C[u"channels"].items() if r == u"simulated-leaf")
    check("A.each_leaf_owns_its_two_source_less_channels", leafch == leaf_channels(), leafch)
    check("A.leaves_are_never_written", not set(leafch) & set(C[u"written"]) and len(C[u"written"]) == 238 and
          roles.get(u"handle-written") == 34 and roles.get(u"fk-written") == 204, (len(C[u"written"]), roles))
    desc = ns["prod_body_descriptor"](D, C, P)
    rows = dict((n, desc[u"channels"][n]) for n in leafch)
    check("A.descriptor_describes_leaf_channels_without_values", all(
        r[u"role"] == u"simulated-leaf" for r in rows.values()) and not set(leafch) & set(
        list(desc[u"structural_positions"]) + list(desc[u"structural_orientations"])), sorted(rows)[:2])
    check("A.descriptor_names_structure_not_the_instance", u"milestailsprower1" not in json.dumps(desc))
    check("A.draft_is_deterministic", ns["prod_body_rig_draft"](D) == P)
    # No header evidence: the Stage 1 refusal stands, naming the reason in the log.
    D0 = discovered(ns, world(fx, posed=False, simulate=False, header=False))
    del ns["LOG"][:]
    refused("A.without_header_evidence_the_draft_refuses", outcome(lambda: ns["prod_body_rig_draft"](D0)),
            u"structure-unsupported")
    reasons = last_refusals(ns)
    check("A.without_header_every_leaf_is_refused_as_unreadable", sorted(reasons) == LEAVES and set(
        reasons.values()) == set([u"the model's procedural declarations are unreadable"]), reasons)
    # The Save New probe admits Tails and names the leaves in its log.
    use(ns, world(fx, posed=False))
    del ns["LOG"][:]
    probe = ns["prod_body_rig_probe"](ctx(ns), IDENTITY, reg, QUAL)
    line = R.last_log(ns, u"BODY-RIG-available")
    check("A.probe_admits_tails_and_logs_the_simulated_leaves", probe is not None and probe[u"classes"][
        u"Tail6_L"] == u"simulated-leaf" and R.log_detail(line).get(u"simulated_leaves") == LEAVES, line)
    return D, P


# ---------------------------------------------------------------------------
# B. Refusal by criterion; harmless relationships do not refuse
# ---------------------------------------------------------------------------

def section_refusals(ns, fx):
    def variant(rows_fn=None, d_fn=None, **kw):
        w = FB.World(fx)
        rows = header_rows(fx)
        if rows_fn is not None:
            rows_fn(rows)
        attach(w, rows=rows, **kw)
        D = discovered(ns, w)
        if d_fn is not None:
            d_fn(D, w)
        del ns["LOG"][:]
        return outcome(lambda: ns["prod_body_rig_draft"](D)), last_refusals(ns)

    def row(rows, name):
        return [r for r in rows if r["name"] == name][0]

    def flags(value):
        return lambda rows: row(rows, u"Tail6_L").__setitem__("flags", value)
    idx = fx[u"bones"][u"Tail6_L"][u"index"]
    cases = (
        (u"physically_simulated_flag", dict(rows_fn=flags(JIGGLE_FLAGS | 1)), u"Tail6_L",
         u"its procedural flags are not supported"),
        (u"physics_procedural_flag", dict(rows_fn=flags(JIGGLE_FLAGS | 2)), u"Tail6_L",
         u"its procedural flags are not supported"),
        (u"screen_align_sphere_flag", dict(rows_fn=flags(JIGGLE_FLAGS | 8)), u"Tail6_L",
         u"its procedural flags are not supported"),
        (u"screen_align_cylinder_flag", dict(rows_fn=flags(JIGGLE_FLAGS | 16)), u"Tail6_L",
         u"its procedural flags are not supported"),
        (u"not_always_procedural", dict(rows_fn=flags(0x500)), u"Tail6_L",
         u"its procedural flags are not supported"),
        (u"quatinterp_not_jiggle", dict(rows_fn=lambda rows: row(rows, u"Tail6_L").__setitem__("proctype", 2)),
         u"Tail6_L", u"not a declared JIGGLE output"),
        (u"undeclared_control_less_bone", dict(rows_fn=lambda rows: row(rows, u"Tail6_L").update(
            proctype=0, flags=0x100)), u"Tail6_L", u"not a declared JIGGLE output"),
        (u"attachment_on_the_leaf", dict(attachments=[idx]), u"Tail6_L",
         u"an attachment or bone flex driver uses it"),
        (u"bone_flex_driver_on_the_leaf", dict(drivers=[idx]), u"Tail6_L",
         u"an attachment or bone flex driver uses it"),
        (u"header_name_mismatch", dict(rows_fn=lambda rows: row(rows, u"ear2_L").__setitem__("name", u"ear2_X")),
         u"Tail6_L", u"the model's header does not match the scene skeleton"),
        (u"header_parent_mismatch", dict(rows_fn=lambda rows: row(rows, u"ear3_L").__setitem__("parent", 0)),
         u"Tail6_L", u"the model's header does not match the scene skeleton"),
        (u"header_extra_bone", dict(rows_fn=lambda rows: rows.append({"name": u"extra", "parent": idx,
                                                                      "flags": 0x100, "proctype": 0})),
         u"Tail6_L", u"the model's header does not match the scene skeleton"),
        (u"jiggle_constant_unreadable", dict(constants=dict((k, v) for k, v in CONSTANTS.items()
                                                            if k != "STUDIO_PROC_JIGGLE")),
         u"Tail6_L", u"the model's procedural declarations are unreadable"),
        (u"helper_constants_unreadable", dict(constants={}), u"Tail6_L",
         u"the model's procedural declarations are unreadable"),
    )
    for label, kw, bone, why in cases:
        got, reasons = variant(**kw)
        refused("B.%s_refuses" % label, got, u"structure-unsupported")
        check("B.%s_names_the_reason" % label, reasons.get(bone) == why, reasons)

    # Header accessors that fail: unreadable, never an exception out of the draft.
    for label, fn in ((u"no_header_accessor", lambda w: delattr(w.gm, "GetStudioHdr")),
                      (u"header_none", lambda w: setattr(w.gm, "GetStudioHdr", lambda: None)),
                      (u"header_raises", lambda w: setattr(w.gm, "GetStudioHdr", lambda: (_ for _ in ()).throw(
                          RuntimeError("test"))))):
        w = FB.World(fx)
        attach(w)
        fn(w)
        D = discovered(ns, w)
        del ns["LOG"][:]
        got = outcome(lambda: ns["prod_body_rig_draft"](D))
        refused("B.%s_refuses" % label, got, u"structure-unsupported")
        check("B.%s_is_unreadable_evidence" % label, last_refusals(ns).get(u"Tail6_L") ==
              u"the model's procedural declarations are unreadable" and D[u"header"][u"status"] == u"UNREADABLE")

    # A jiggle chain: the parent made control-less and declared too; non-leaf chains keep refusing.
    def chain_rows(rows):
        row(rows, u"Tail5_L").update(proctype=JIGGLE, flags=JIGGLE_FLAGS)

    def chain_d(D, w):
        for attr in (u"_p", u"_o"):
            D[u"channels"][u"Tail5_L" + attr][u"from"] = None
            D[u"channels"][u"Tail5_L" + attr][u"from_attribute"] = u""
    got, reasons = variant(rows_fn=chain_rows, d_fn=chain_d)
    refused("B.jiggle_chain_refuses", got, u"structure-unsupported")
    check("B.jiggle_chain_names_both_bones", reasons.get(u"Tail5_L") == u"other bones depend on it (a jiggle chain)"
          and reasons.get(u"Tail6_L") == u"its parent is not a supported bone", reasons)

    # Concrete consumers in the scene.
    leaf_dag = lambda D: D[u"bones"][u"Tail6_L"][u"handle"]   # noqa: E731

    def follows(D, w):
        for op in D[u"operators"]:
            if op[u"name"] in (u"pointConstraint_rig_footHelper_L", u"orientConstraint_rig_footHelper_L"):
                op[u"targets"][0][u"target"] = leaf_dag(D)
    got, reasons = variant(d_fn=follows)
    refused("B.rig_constraint_following_the_leaf_refuses", got, u"structure-unsupported")
    check("B.rig_constraint_following_the_leaf_names_the_reason", reasons.get(u"Tail6_L") ==
          u"a rig constraint follows it", reasons)

    def reads(D, w):
        name = sorted(n for n, c in D[u"channels"].items() if c[u"from"] is not None)[0]
        D[u"channels"][name][u"from"] = {u"handle": leaf_dag(D), u"type": u"DmeDag", u"name": u"Tail6_L"}
    got, reasons = variant(d_fn=reads)
    refused("B.channel_reading_the_leaf_refuses", got, u"structure-unsupported")
    check("B.channel_reading_the_leaf_names_the_reason", reasons.get(u"Tail6_L") == u"a channel reads it", reasons)

    def reads_transform(D, w):
        name = sorted(n for n, c in D[u"channels"].items() if c[u"from"] is not None)[0]
        D[u"channels"][name][u"from"] = {u"handle": D[u"bones"][u"Tail6_L"][u"transform"],
                                         u"type": u"DmeTransform", u"name": u"bone"}
    got, reasons = variant(d_fn=reads_transform)
    check("B.channel_reading_the_leaf_transform_refuses", got[1] == u"structure-unsupported" and reasons.get(
        u"Tail6_L") == u"a channel reads it", reasons)

    w = FB.World(fx)
    attach(w)
    D = discovered(ns, w)
    got = outcome(lambda: ns["prod_body_rig_draft"](D, [{u"id": u"face", u"bones": [u"ear3_L"],
                                                         u"provenance": u"user_confirmed", u"label": u"Face"}]))
    refused("B.an_exclusion_naming_a_leaf_refuses", got, u"structure-unsupported")

    # Harmless relationships: a non-bone element parented below a leaf (a prop) and attachments on other bones.
    w = FB.World(fx)
    attach(w)
    prop = FB.Dag(w, w.new_handle(), "DmeDag", u"prop", FB.Element(w, w.new_handle(), "DmeTransform", u"prop_t",
                                                                   position=FB.Vector(), orientation=FB.Quaternion()))
    w.bone_dag[u"Tail6_L"].add(prop)
    w.evaluate()
    D = discovered(ns, w)
    got = outcome(lambda: ns["prod_body_rig_draft"](D))
    check("B.a_prop_parented_below_a_leaf_does_not_refuse", got[0] == u"ok" and got[1][u"simulated_leaf_bones"] ==
          LEAVES, got[:1])
    got, reasons = variant()
    check("B.attachments_on_other_bones_do_not_refuse", got[0] == u"ok" and not reasons and attachments_of(fx))


# ---------------------------------------------------------------------------
# C. Live Save and Apply with the leaves simulated: the output exemption
# ---------------------------------------------------------------------------

def section_live(ns, reg, fx, root):
    lib = library(root, u"live")
    src = use(ns, world(fx, posed=False))
    head = src.head
    pose, saved, item = save(ns, reg, lib, u"Tails A")
    region = pose[u"regions"][u"full_body"]
    check("C.save_is_read_only", no_mutation(src) and src.head == head)
    check("C.record_is_structural_revision_2", pose[u"adapter"] == {u"rule": u"structural_rig_v1", u"revision": 2},
          pose[u"adapter"])
    classes = dict((b[u"name"], b[u"class"]) for b in region[u"descriptor"][u"bones"])
    check("C.record_describes_the_seven_leaves", sorted(n for n, c in classes.items() if c == u"simulated-leaf") ==
          LEAVES)
    check("C.record_saves_no_leaf_value_or_oracle", not set(leaf_channels()) & set(
        list(region[u"positions"]) + list(region[u"orientations"])) and not set(LEAVES) & set(
        region[u"oracle"][u"bones"]) and len(region[u"oracle"][u"bones"]) == 124 and len(
        region[u"positions"]) + len(region[u"orientations"]) == 238)
    check("C.record_reloads_and_validates", item[u"record"] == saved[u"record"])
    source = posture(src)

    dst = use(ns, world(fx, leaf_keys))
    dp, dq = B.max_difference(posture(dst), source)
    check("C.destination_is_distinctly_posed", dq > 10.0, (dp, dq))
    before = B.all_keys(dst)
    steps = dst.jiggle_steps[0]
    leaf_world = dict((n, list(dst.bone_dag[n].wp)) for n in LEAVES)
    auth, got = apply_(ns, reg, item, dst)
    check("C.apply_commits_in_one_owned_undo", got[0] == u"ok" and got[1][u"phase"] == u"verification-pending" and
          [c[0] for c in dst.dm.calls] == ["StartUndo", "FinishUndo"] and dst.dm.stack[0]["label"] ==
          u"Apply Pose Tails A", got[:2])
    verdict = verify(ns, auth, got)
    check("C.p7_verifies_while_the_leaves_move", verdict is not None and verdict.get(u"phase") ==
          u"committed-verified", verdict)
    check("C.the_leaves_really_moved_between_p1_and_p7", dst.jiggle_steps[0] > steps and all(
        list(dst.bone_dag[n].wp) != leaf_world[n] for n in LEAVES), dst.jiggle_steps[0] - steps)
    dpp, dqp = B.max_difference(posture(dst), source)
    check("C.destination_takes_the_source_body_posture", dpp < 1e-3 and dqp < 0.01, (dpp, dqp))
    after = B.all_keys(dst)
    check("C.leaf_authored_keys_unchanged", all(after[n] == before[n] for n in leaf_channels()))
    changed = sorted(n for n in after if after[n] != before[n])
    check("C.only_planned_channels_changed", len(changed) > 40 and not set(changed) & set(leaf_channels()) and all(
        n in region[u"positions"] or n in region[u"orientations"] for n in changed), len(changed))
    check("C.destination_keeps_its_own_jiggle_values", after[u"Tail6_L_o"] != src.keys(u"Tail6_L_o"))
    dst.dm.Undo()
    check("C.undo_restores_the_baseline", B.all_keys(dst) == before)
    dst.dm.Redo()
    check("C.redo_reapplies", B.all_keys(dst) == after)
    calls = len(dst.calls)
    _, again = apply_(ns, reg, item, dst)
    check("C.repeat_apply_is_a_true_noop_while_the_leaves_move", again[0] == u"ok" and again[1] == {
        u"phase": u"no-op"} and len(dst.calls) == calls, again[:2])
    # Without simulation (the leaves following their channels) the same pose applies and verifies.
    w = use(ns, world(fx, simulate=False))
    auth, got = apply_(ns, reg, item, w)
    check("C.unsimulated_destination_applies_and_verifies", (verify(ns, auth, got) or {}).get(u"phase") ==
          u"committed-verified", got[:2])
    # A destination where one leaf is not admitted (undeclared) refuses before any write.
    rows = header_rows(fx)
    [r for r in rows if r["name"] == u"Tail6_R"][0].update(proctype=0, flags=0x100)
    w = world(fx, rows=rows)
    _, got = apply_(ns, reg, item, w)
    check("C.destination_with_a_leaf_not_admitted_refuses", got[0] != u"ok" and no_mutation(w), got[:1])
    return lib, item


def section_rig_driven_parent(ns, reg, fx, root):
    """Astra: a qualified rig-driven parent is acceptable. Tails has none; a fixture variant puts Tail6_L under the
    rig-driven bip_hand_L (header and scene agree)."""
    fx2 = copy.deepcopy(fx)
    fx2[u"bones"][u"Tail6_L"][u"parent"] = u"bip_hand_L"
    D = discovered(ns, world(fx2, posed=False, simulate=False))
    P = ns["prod_body_rig_draft"](D)
    C = ns["prod_body_classify"](D, P)
    check("D.leaf_under_a_rig_driven_parent_is_admitted", P[u"simulated_leaf_bones"] == LEAVES and
          C[u"bones"][u"bip_hand_L"] == u"constrained" and C[u"bones"][u"Tail6_L"] == u"simulated-leaf")
    lib = library(root, u"rigparent")
    use(ns, world(fx2, posed=False))
    _, _, item = save(ns, reg, lib, u"Tails R")
    w = use(ns, world(fx2, leaf_keys))
    auth, got = apply_(ns, reg, item, w)
    check("D.rig_driven_parent_save_apply_verifies", (verify(ns, auth, got) or {}).get(u"phase") ==
          u"committed-verified", got[:2])


# ---------------------------------------------------------------------------
# E. Boundaries: authored state, configuration, header, P2, P7, recovery
# ---------------------------------------------------------------------------

def section_boundaries(ns, reg, fx, item):
    original = ns["prod_body_preflight"]

    def after_p1(change):
        w = world(fx)

        def preflight_then(*args):
            pre = original(*args)
            change(w)
            w.evaluate()
            return pre
        ns["prod_body_preflight"] = preflight_then
        try:
            _, got = apply_(ns, reg, item, w)
        finally:
            ns["prod_body_preflight"] = original
        return w, got

    def leaf_key(w):
        layer = w.channels[u"Tail6_L_o"].attrs["log"].layer
        layer.keys[0][1] = FB.native(B.rotate(FB.plain(layer.keys[0][1]), [0.0, 1.0, 0.0], 5.0), "quat")

    def leaf_scale(w):
        w.bone_dag[u"Tail6_L"].attrs["transform"].set("scale", 1.25)

    def redeclare(w):
        w.gm.GetStudioHdr().rows[w.fx[u"bones"][u"Tail6_L"][u"index"]]["proctype"] = 2

    w, got = after_p1(lambda w: None)          # only SFM's simulation runs between P1 and P2
    check("E.p2_leaves_moving_between_p1_and_p2_do_not_refuse", got[0] == u"ok" and got[1][u"phase"] == u"verification-pending" and w.jiggle_steps[0] >= 2, got[:2])
    for label, change in ((u"leaf_key", leaf_key), (u"leaf_scale", leaf_scale), (u"header_declaration", redeclare)):
        w, got = after_p1(change)
        check("E.p2_%s_change_after_p1_refuses" % label, got[0] not in (u"ok",) and got[0] != u"ProdRecoveryUnverifiedError",
              got[:1])
        check("E.p2_%s_change_writes_nothing" % label, not B.scene_writes(w) and not [
            c for c in w.dm.calls if c[0] == "StartUndo"])

    for label, change in ((u"leaf_key", leaf_key), (u"leaf_scale", leaf_scale), (u"header_declaration", redeclare)):
        w = world(fx)
        auth, got = apply_(ns, reg, item, w)
        change(w)
        w.evaluate()
        verdict = verify(ns, auth, got)
        check("E.p7_after_a_%s_change_is_unverified" % label, verdict is not None and verdict.get(u"phase") ==
              u"committed-unverified", verdict)

    # The exemption covers only the simulated leaves: a moving directly animated bone fails P7.
    w = world(fx)
    auth, got = apply_(ns, reg, item, w)
    FB.simulate_jiggle(w, [u"Tail5_L"])
    verdict = verify(ns, auth, got)
    check("E.p7_a_moving_non_leaf_bone_is_unverified", verdict is not None and verdict.get(u"phase") ==
          u"committed-unverified" and any(u"Tail5_L" in l for l in ns["LOG"][-3:]), verdict)
    # And only their transforms: P7 still fails a wrong rig-driven body while the leaves move.
    w = world(fx)
    auth, got = apply_(ns, reg, item, w)
    solve = w.solve_ik

    def misbent(start, el, parent_world, parent_scale):
        solve(start, el, parent_world, parent_scale)
        w.set_world(start, start.wp, B.rotate(start.wq, [0.0, 0.0, 1.0], 10.0), parent_world, parent_scale)
    w.solve_ik = misbent
    w.evaluate()
    verdict = verify(ns, auth, got)
    check("E.p7_still_detects_a_wrong_body_while_the_leaves_move", verdict is not None and verdict.get(u"phase") ==
          u"committed-unverified", verdict)

    # Recovery: a partial-write failure after rig and FK writes, with the leaves moving, is a verified Abort.
    w = world(fx)
    before = B.all_keys(w)
    w.fail_on_write = u"rig_spine_0_o"
    abort = w.dm.AbortUndoableOperation

    def abort_then_evaluate():               # SFM re-evaluates after the Abort: the leaves move again
        abort()
        w.evaluate()
    w.dm.AbortUndoableOperation = abort_then_evaluate
    steps = w.jiggle_steps[0]
    del ns["LOG"][:]
    _, got = apply_(ns, reg, item, w)
    check("E.partial_write_failure_is_a_verified_abort", got[0] == u"ok" and got[1][u"phase"] == u"not-applied" and
          [c[0] for c in w.dm.calls] == ["StartUndo", "AbortUndoableOperation"] and B.all_keys(w) == before and
          w.jiggle_steps[0] > steps, (got[:2], w.dm.calls))
    check("E.abort_verified_is_logged", R.log_detail(R.last_log(ns, u"BODY-abort-verified")) == {
        u"problems": [], u"redo_cleared": False})
    # With a pending Redo that SFM discards (Stage 1's history exception, unchanged).
    w = world(fx)
    auth, got = apply_(ns, reg, item, w)
    w.dm.Undo()
    FB.discard_redo_on_start(w)
    del w.dm.calls[:]
    before = B.all_keys(w)
    QF = ns["PROD_POSE_QUAL_FAULT"]
    QF[0] = u"after-writes"
    del ns["LOG"][:]
    try:
        _, got = apply_(ns, reg, item, w)
    finally:
        QF[0] = None
    check("E.redo_cleared_abort_is_verified_with_the_flag", got[0] == u"ok" and got[1].get(u"redo_cleared") is True
          and B.all_keys(w) == before, got[:2])
    # An Abort that cannot be verified still locks recovery.
    w = world(fx, lambda w: (setattr(w, "fail_on_write", u"rig_spine_0_o"), setattr(w, "abort_raises", True)))
    _, got = apply_(ns, reg, item, w)
    check("E.failed_abort_is_recovery_unverified", got[0] == u"ProdRecoveryUnverifiedError", got)
    ns["PROD_POSE_RECOVERY_BLOCK"][0] = None


# ---------------------------------------------------------------------------
# F. Records: revision 2, validation, older readers, the registry form
# ---------------------------------------------------------------------------

def section_records(ns, reg, item, root):
    record = item[u"record"]
    raw = ns["prod_pose_serialize"](record)
    check("F.revision_2_record_validates", outcome(lambda: ns["prod_pose_parse"](raw, reg))[0] == u"ok")
    fb = u"full_body"

    def bones(r):
        return r[u"pose"][u"regions"][fb][u"descriptor"][u"bones"]

    def bone(r, name):
        return [b for b in bones(r) if b[u"name"] == name][0]

    def channels(r):
        return r[u"pose"][u"regions"][fb][u"descriptor"][u"channels"]
    cases = (
        (u"revision_1_with_leaves", lambda r: r[u"pose"][u"adapter"].__setitem__(u"revision", 1)),
        (u"revision_3", lambda r: r[u"pose"][u"adapter"].__setitem__(u"revision", 3)),
        (u"revision_0", lambda r: r[u"pose"][u"adapter"].__setitem__(u"revision", 0)),
        (u"revision_boolean", lambda r: r[u"pose"][u"adapter"].__setitem__(u"revision", True)),
        (u"leaf_class_without_its_channels_role", lambda r: bone(r, u"Tail6_L").__setitem__(u"class", u"fk")),
        (u"leaf_channel_claimed_preserved", lambda r: channels(r)[u"Tail6_L_o"].__setitem__(u"role",
                                                                                              u"fk-preserved")),
        (u"leaf_with_a_child", lambda r: bone(r, u"ear3_R").__setitem__(u"parent", u"Tail6_L")),
        (u"leaf_under_a_leaf", lambda r: bone(r, u"Tail6_L").__setitem__(u"parent", u"Tail6_R")),
        (u"leaf_without_parent", lambda r: bone(r, u"Tail6_L").__setitem__(u"parent", None)),
        (u"leaf_role_on_another_bone", lambda r: channels(r)[u"Tail5_L_o"].__setitem__(u"role", u"simulated-leaf")),
        (u"oracle_for_a_leaf", lambda r: r[u"pose"][u"regions"][fb][u"oracle"][u"bones"].__setitem__(
            u"Tail6_L", copy.deepcopy(r[u"pose"][u"regions"][fb][u"oracle"][u"bones"][u"Tail5_L"]))),
        (u"leaf_value_saved", lambda r: (channels(r)[u"Tail6_L_o"].__setitem__(u"role", u"fk-written"),
                                         r[u"pose"][u"regions"][fb][u"orientations"].__setitem__(
                                             u"Tail6_L_o", [0.0, 0.0, 0.0, 1.0]))),
        (u"no_leaves_at_revision_2", lambda r: [b.__setitem__(u"class", u"fk") for b in bones(r)
                                                if b[u"class"] == u"simulated-leaf"]),
    )
    for label, fn in cases:
        refused("F.malformed_%s_is_invalid" % label, outcome(lambda: ns["prod_pose_parse"](
            R.tampered(ns, record, fn), reg)), u"invalid-file")

    # The older strict reader: the Stage 1 candidate (structural_rig_v1 revision 1 only) refuses revision 2.
    old, old_sha = R.git_namespace(STAGE1_COMMIT)
    check("F.stage1_reader_is_the_stage1_candidate", old_sha == STAGE1_SHA256, old_sha)
    oreg, _ = B.registries(old)
    refused("F.stage1_reader_refuses_revision_2", outcome(lambda: old["prod_pose_parse"](raw, oreg)), u"invalid-file")
    # RC2 (the preserved release baseline) refuses it as unreadable.
    try:
        src = subprocess.check_output(["git", "-C", core._REPO_ROOT, "show", "%s:cpm/app/"
                                       "SFM_Character_Preset_Manager.py" % RC2_COMMIT])
        fd, path = tempfile.mkstemp(suffix="_rc2_cpm.py")
        with os.fdopen(fd, "wb") as f:
            f.write(src)
        saved_path, saved_out = route.APP_PATH, sys.stdout
        try:
            route.APP_PATH = path
            sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
            rc2 = B.build_namespace(route.AppSource(path))
            arm, _ = B.registries(rc2)
        finally:
            route.APP_PATH = saved_path
            sys.stdout = saved_out
        refused("F.rc2_reader_refuses_revision_2", outcome(lambda: rc2["prod_pose_parse"](raw, arm)),
                u"invalid-file")
    except Exception as exc:
        check("F.rc2_reader_available", False, repr(exc))
    return old


def section_unchanged_routes(ns, reg, root, old):
    """Fox (Stage 1) and Krystal (registry) are unchanged."""
    fox = R.fixture()
    # Fox: the same drafted description and descriptor in the Stage 1 candidate and in this build.
    w = FB.World(fox)
    D_new = R.discovered(ns, w)
    D_old = R.discovered(old, FB.World(fox))
    P_new, P_old = ns["prod_body_rig_draft"](D_new), old["prod_body_rig_draft"](D_old)
    check("G.fox_draft_identical_to_stage1", P_new == P_old and u"simulated_leaf_bones" not in P_new)
    check("G.fox_descriptor_identical_to_stage1", ns["prod_body_descriptor"](
        D_new, ns["prod_body_classify"](D_new, P_new), P_new) == old["prod_body_descriptor"](
        D_old, old["prod_body_classify"](D_old, P_old), P_old))
    # Fox: Save writes revision 1, which both readers accept, and Apply verifies.
    B.IDENTITY = R.IDENTITY
    try:
        lib = R.library(root, u"fox")
        R.use(ns, R.world(fox, posed=False))
        pose, saved, item = R.save(ns, reg, lib, u"Fox S2")
        check("G.fox_record_stays_revision_1", pose[u"adapter"][u"revision"] == 1)
        oreg, _ = B.registries(old)
        raw = ns["prod_pose_serialize"](saved[u"record"])
        check("G.fox_record_reads_in_the_stage1_build", outcome(lambda: old["prod_pose_parse"](raw, oreg))[0] ==
              u"ok")
        dst = R.world(fox)
        auth, got = R.apply_(ns, reg, item, dst)
        check("G.fox_apply_verifies", (verify(ns, auth, got) or {}).get(u"phase") == u"committed-verified",
              got[:2])
        refused("G.fox_record_at_revision_2_is_invalid", outcome(lambda: ns["prod_pose_parse"](R.tampered(
            ns, saved[u"record"], lambda r: r[u"pose"][u"adapter"].__setitem__(u"revision", 2)), reg)),
            u"invalid-file")
    finally:
        B.IDENTITY = IDENTITY
    # Krystal's registry route never reads the header, and its record form refuses the new class.
    kfx = B.fixture("s0_shot15.json")
    profile = B.profile_of(ns, reg)
    kw = FB.World(kfx)
    B.use_world(ns, kw)
    row = ns["prod_resolve_instance"](ctx(ns)[u"instance"])
    L = ns["prod_body_live"](row, profile)
    t = ns["prod_pose_time_read"](L, sorted(n for n in profile[u"written_handle_channels"] if n in L[u"channels"]))
    D = ns["prod_body_discover"](L, t[u"t_chan"], ns["prod_pose_writer_index"]())
    check("G.registry_route_reads_no_header", u"header" not in D)
    os.makedirs(os.path.join(root, u"k"))
    klib = {u"character_key": u"krystal2020", u"char_dir": os.path.join(root, u"k", u"Characters", u"krystal2020"),
            u"library_root": os.path.join(root, u"k"), u"model_ref": B.MODEL}
    krec = ns["prod_pose_save_new"](klib, u"Krystal K", B.body_pose(ns, kfx, ns["prod_body_classify"](kfx, profile),
                                                                    profile), u"20261119-110000-000000", reg)[u"record"]
    kraw = ns["prod_pose_serialize"](krec)
    check("G.krystal_record_validates", outcome(lambda: ns["prod_pose_parse"](kraw, reg))[0] == u"ok")
    first = krec[u"pose"][u"regions"][u"full_body"][u"descriptor"][u"bones"][0][u"name"]
    refused("G.krystal_record_form_refuses_the_simulated_leaf_class", outcome(lambda: ns["prod_pose_parse"](
        R.tampered(ns, krec, lambda r: [b.__setitem__(u"class", u"simulated-leaf") for b in r[u"pose"][u"regions"][
            u"full_body"][u"descriptor"][u"bones"] if b[u"name"] == first]), reg)), u"invalid-file")


# ---------------------------------------------------------------------------
# H. Production mode and teeth
# ---------------------------------------------------------------------------

def section_production_and_teeth(ns, reg, fx, item, old):
    # v1.1.0 RC3: the adapter is qualified, so production offers Tails' Full body (its seven leaves admitted) and
    # authorizes the Apply exactly as the qualification build does.
    use(ns, world(fx, posed=False))
    probe = ns["prod_body_rig_probe"](ctx(ns), IDENTITY, reg, PROD)
    check("H.rc3_production_build_offers_the_adapter", probe is not None and probe == ns["prod_body_rig_probe"](
        ctx(ns), IDENTITY, reg, QUAL) and sorted(n for n, c in probe[u"classes"].items() if c == u"simulated-leaf")
        == sorted(LEAVES), probe and sorted(n for n, c in probe[u"classes"].items() if c == u"simulated-leaf"))
    w = world(fx)
    use(ns, w)
    got = outcome(lambda: authorize(ns, reg, u"Apply Pose", item, mode=PROD))
    check("H.rc3_production_apply_is_authorized", got[0] == u"ok" and got[1][u"mappings"][0][u"status"] ==
          u"qualified" and bool(got[1][u"mappings"][0][u"evidence"]), got if got[0] != u"ok" else None)
    check("H.rc3_production_authorization_writes_nothing", no_mutation(w))
    # The RC2 behaviour, kept against the experimental status.
    status = ns["PROD_BODY_RIG_STATUS"]
    ns["PROD_BODY_RIG_STATUS"] = u"experimental"
    try:
        use(ns, world(fx, posed=False))
        check("H.production_build_does_not_offer_the_adapter", ns["prod_body_rig_probe"](ctx(ns), IDENTITY, reg,
                                                                                         PROD) is None)
        w = world(fx)
        use(ns, w)
        got = outcome(lambda: authorize(ns, reg, u"Apply Pose", item, mode=PROD))
        refused("H.production_apply_is_not_qualified", got, u"not-qualified")
        check("H.production_refusal_writes_nothing", no_mutation(w))
    finally:
        ns["PROD_BODY_RIG_STATUS"] = status

    # Teeth 1: the Stage 1 candidate (no admission) refuses Tails exactly as before.
    D = discovered(old, world(fx, posed=False, simulate=False))
    got = outcome(lambda: old["prod_body_rig_draft"](D))
    check("H.teeth_stage1_build_refuses_the_control_less_leaves", got[1] == u"structure-unsupported" and any(
        u"outside Stage 1" in l for l in old["LOG"][-6:]), got)
    # Teeth 2: classed as today's passive bone (Astra: not this), the simulated motion fails verification.
    w = world(fx)
    auth, got = apply_(ns, reg, item, w)
    pending = got[1][u"pending"]
    D_now = discovered(ns, w)
    C = pending[u"classes"]
    expected = dict((k, (v[0], v[1])) for k, v in pending[u"expected"].items())
    exempt = ns["prod_body_verify_skeleton"](D_now, pending[u"baseline"], expected, C, pending[u"profile"])
    Cp = json.loads(json.dumps(C))
    for n in LEAVES:
        Cp[u"bones"][n] = u"passive"
    region = item[u"record"][u"pose"][u"regions"][u"full_body"]
    exp_p = ns["prod_body_expected_skeleton"](region, pending[u"baseline"], Cp, pending[u"profile"])
    passive = ns["prod_body_verify_skeleton"](D_now, pending[u"baseline"], exp_p, Cp, pending[u"profile"])
    check("H.teeth_the_exemption_verifies_the_moving_leaves", exempt == [], exempt[:4])
    check("H.teeth_passive_class_fails_the_same_moving_leaves", passive and all(
        any(n in p for n in LEAVES) for p in passive), passive[:4])
    # Teeth 3: without the admission (all refused), Tails refuses in this build too.
    real = ns["prod_body_rig_leaf_admission"]
    ns["prod_body_rig_leaf_admission"] = lambda D, c, b, k: ([], dict((n, u"disabled (test)") for n in c))
    try:
        D = discovered(ns, world(fx, posed=False, simulate=False))
        refused("H.teeth_admission_disabled_refuses_tails", outcome(lambda: ns["prod_body_rig_draft"](D)),
                u"structure-unsupported")
    finally:
        ns["prod_body_rig_leaf_admission"] = real


def fixture():
    raw = core.read(FIXTURE)
    check("fixture.tails_shot15.matches_its_pin", core.sha(raw) == FIXTURE_SHA256, core.sha(raw))
    return json.loads(raw.decode("utf-8"))


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
    print("F-01 Stage 2 declared JIGGLE leaf compatibility (Python %s)" % sys.version.split()[0])
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    B.IDENTITY = IDENTITY
    app = route.AppSource(route.APP_PATH)
    root = tempfile.mkdtemp(prefix="cpm_f01_jiggle_")
    try:
        ns = B.live_namespace(app)
        fx = fixture()
        R.FIXTURE_DATA.append(R.fixture())
        reg, _ = B.registries(ns)
        run("admission", lambda: section_admission(ns, fx, reg))
        run("refusals", lambda: section_refusals(ns, fx))
        lived = run("live", lambda: section_live(ns, reg, fx, root))
        run("rig_driven_parent", lambda: section_rig_driven_parent(ns, reg, fx, root))
        old = None
        if lived:
            run("boundaries", lambda: section_boundaries(ns, reg, fx, lived[1]))
            old = run("records", lambda: section_records(ns, reg, lived[1], root))
        if old not in (None, True):
            run("unchanged_routes", lambda: section_unchanged_routes(ns, reg, root, old))
            B.IDENTITY = IDENTITY
            run("production_and_teeth", lambda: section_production_and_teeth(ns, reg, fx, lived[1], old))
    finally:
        shutil.rmtree(root, True)
    failed = [r for r in RESULTS if not r[1]]
    print("RESULT: %d/%d %s (%s)" % (len(RESULTS) - len(failed), len(RESULTS),
                                     "ALL PASS" if not failed else "SOME FAILED", sys.version.split()[0]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
