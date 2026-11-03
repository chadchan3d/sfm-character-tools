# -*- coding: utf-8 -*-
"""Offline qualification of the M-06 W2 instruments (Python 2.7.5 and 3.10.6). Fake native modules only
(tests/fake_dme.py): nothing here is native evidence.

usage: python -B test_m06w2.py [RESULTS_JSON]
"""
from __future__ import print_function

import copy
import hashlib
import io
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ROOT))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fake_dme as F  # noqa: E402
import compare_obs as C  # noqa: E402
import compare_probes as CP  # noqa: E402
import scan_deferred_fixture as SCAN  # noqa: E402

CORE = os.path.join(ROOT, "instruments", "m06w2_core.py")
W1_APP = os.environ.get("M06W2_W1_APP") or os.path.join(REPO, "cpm", "app", "SFM_Character_Preset_Manager.py")
W1_SHA256 = "fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d"
M05_FIXTURE = os.environ.get("M06W2_M05_FIXTURE", "")
DEFERRED = "m06w2_deferred_config.json"
ORDINARY = "m06w2_config.json"      # what the staged ordinary Observer and the injector record


def load_core():
    ns = {"__name__": "m06w2_core_test"}
    with open(CORE, "rb") as f:
        eval(compile(f.read(), CORE, "exec"), ns)
    return ns


CORE_NS = load_core()


def observe(world, config=None, watch=None, config_name=None):
    sfm, vs = world.modules()
    rec = CORE_NS["observe"](sfm, vs, config or F.CONFIG, watch=watch, config_name=config_name)
    return json.loads(CORE_NS["dumps"](rec))


def target(world):
    return world.instances["krystal_target"]


def peer(world):
    return world.instances["krystal_peer"]


def verdict(inv, a, b, spec=None):
    return C.compare(inv, a, b, spec)


# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------

class TestObserver(unittest.TestCase):
    def test_complete_observation_of_target_peer_bones_graph_and_flex(self):
        w = F.twin_world()
        r = observe(w)
        self.assertTrue(r["complete"], r["insufficient"])
        t, p = r["target"], r["peers"]["krystal_peer"]
        self.assertEqual([b["name"] for b in t["bones"]], ["bip_pelvis", "bip_head", "bip_hand_l"])
        self.assertEqual(len(t["graphs"]), 1)
        self.assertEqual(p["graphs"], [])
        self.assertEqual(t["flex"]["Muscles"]["mono"]["representation"]["v"], "STATIC_PLAY_ONE_KEY_ZERO")
        self.assertEqual(t["flex"]["Legsize"]["mono"]["representation"]["v"], "ONE_KEY_ZERO")
        self.assertEqual(t["flex"]["Breastsize"]["shape"], "STEREO")
        self.assertIn("smile", t["nonbody"])
        self.assertIn("bip_head", t["transform_controls"])
        self.assertNotEqual(t["identity"]["animset"]["v"]["id"], p["identity"]["animset"]["v"]["id"])
        self.assertEqual(t["identity"]["model"]["v"], p["identity"]["model"]["v"])

    def test_scale_writer_requires_exact_bone_and_scale_attribute(self):
        w = F.twin_world()
        head = [b for b in observe(w)["target"]["bones"] if b["name"] == "bip_head"][0]
        attrs = sorted(x["to_attribute"]["v"] for x in head["writers"])
        self.assertEqual(attrs, ["orientation", "position", "scale"])
        self.assertEqual([c["name"] for c in head["scale_writers"]], ["bip_head_scale_out"])

    def test_unreadable_endpoint_or_attribute_is_unresolved_not_excluded(self):
        for attr in ("toAttribute", "toElement"):
            w = F.twin_world()
            target(w)["bones"]["bip_head"]  # noqa
            ch = [c for c in target(w)["channels"] if c.name == "bip_head_position"][0]
            ch.unreadable.add(attr)
            r = observe(w)
            self.assertFalse(r["complete"])
            self.assertIn("bip_head_position", [c["name"] for c in r["unresolved_channels"]])
            self.assertTrue(any("possible unrecorded writers" in x for x in r["insufficient"]))

    def test_four_states_are_distinguished(self):
        w = F.twin_world()
        ctl = target(w)["flex"]["Legsize"][0]
        ctl.set("channel", None)
        r = observe(w)
        side = r["target"]["flex"]["Legsize"]["mono"]
        self.assertEqual(side["channel"], {"s": "null"})
        self.assertEqual([b["scale"] for b in r["target"]["bones"] if b["name"] == "bip_pelvis"][0], {"s": "absent"})
        w2 = F.twin_world()
        target(w2)["flex"]["Muscles"][0].lying_presence.add("value")
        r2 = observe(w2)
        self.assertEqual(r2["target"]["flex"]["Muscles"]["mono"]["stored"]["s"], "unreadable")
        self.assertFalse(r2["complete"])

    def test_presence_claimed_for_a_missing_attribute_is_unreadable(self):
        w = F.twin_world()
        target(w)["flex"]["Legsize"][0].lying_presence.add("leftValue")       # missing, but HasAttribute says True
        r = observe(w)
        self.assertEqual(r["target"]["flex"]["Legsize"]["shape"], "MONO")
        self.assertFalse(r["complete"])
        self.assertTrue(any("leftValue" in x for x in r["insufficient"]), r["insufficient"])

    def test_unreadable_values_never_become_empty_or_neutral(self):
        cases = [lambda w: target(w)["flex"]["Muscles"][0].unreadable.add("value"),
                 lambda w: target(w)["clip"].unreadable.add("channels"),
                 lambda w: target(w)["animset"].unreadable.add("controls"),
                 lambda w: target(w)["bones"]["bip_head"].unreadable.add("scale"),
                 lambda w: target(w)["gm"].unreadable.add("bones"),
                 lambda w: target(w)["root"].unreadable.add("children"),
                 lambda w: target(w)["flex"]["Muscles"][1].log.layers[0].broken.add("id")]
        for i, fn in enumerate(cases):
            w = F.twin_world()
            fn(w)
            r = observe(w)
            self.assertFalse(r["complete"], i)
            self.assertTrue(r["insufficient"], i)

    def test_pointer_like_or_unreadable_identity_is_insufficient(self):
        w = F.twin_world()
        target(w)["animset"].uid = F.UniqueId("<Swig Object of type 'DmObjectId_t *' at 0x0042>")
        self.assertFalse(observe(w)["complete"])
        w = F.twin_world()
        target(w)["gm"].broken.add("id")
        self.assertFalse(observe(w)["complete"])

    def test_context_must_agree_at_beginning_and_end(self):
        w = F.twin_world()
        ticks = [0]
        sfm, vs = w.modules()
        real = sfm.GetHeadTimeInSeconds

        def moving():
            ticks[0] += 1
            return real() + (0.04 if ticks[0] > 1 else 0.0)
        sfm.GetHeadTimeInSeconds = moving
        rec = CORE_NS["observe"](sfm, vs, F.CONFIG)
        self.assertFalse(rec["complete"])
        self.assertIn("context changed during the observation", rec["insufficient"])

    def test_peer_must_be_a_distinct_instance_and_controls_unique(self):
        w = F.twin_world()
        cfg = dict(F.CONFIG, peers=["krystal_target"])
        self.assertTrue(any("is the target instance" in x for x in observe(w, cfg)["insufficient"]))
        w = F.twin_world()
        target(w)["controls"].append(F.El(w, "DmElement", "Muscles", value=0.0))
        self.assertTrue(any("expected exactly one control" in x for x in observe(w)["insufficient"]))

    def test_peer_must_be_same_model(self):
        w = F.World()
        w.instance("krystal_target", with_scale_graph=True)
        other = w.instance("krystal_peer")
        other["gm"].set("modelName", "models/other.mdl")
        self.assertTrue(any("not a same-model instance" in x for x in observe(w)["insufficient"]))

    def test_undo_evidence_strict(self):
        w = F.twin_world()
        w.dm.broken.add("can_redo")
        self.assertFalse(observe(w)["complete"])
        w = F.twin_world()
        w.dm.undo["can_undo"] = 0
        r = observe(w)
        self.assertEqual(r["undo"]["can_undo"]["s"], "unreadable")
        self.assertFalse(r["complete"])
        w = F.twin_world()
        w.dm.broken.add("count")
        self.assertTrue(observe(w)["complete"])        # the item count is diagnostic only

    def test_protected_file_change_makes_observation_insufficient(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "protected.dmx")
            with open(p, "wb") as f:
                f.write(b"original")
            cfg = dict(F.CONFIG, protected={"original": {"path": p, "sha256": hashlib.sha256(b"original").hexdigest()}})
            self.assertTrue(observe(F.twin_world(), cfg)["complete"])
            with open(p, "ab") as f:
                f.write(b"!")
            self.assertFalse(observe(F.twin_world(), cfg)["complete"])
        finally:
            shutil.rmtree(d, True)

    def test_core_is_read_only_by_construction(self):
        with io.open(CORE, encoding="utf-8") as f:
            src = f.read()
        for forbidden in ("SetValue(", "SetKeyValue(", "StartUndo(", ".Undo(", ".Redo(", "SetHeadTime", "Operate(",
                          "AbortUndoableOperation", "FinishUndo", "ProcessEvents", "QTimer"):
            self.assertNotIn(forbidden, src)


# ---------------------------------------------------------------------------
# Comparator
# ---------------------------------------------------------------------------

def apply_change(w, muscles=0.8, scale=1.5, control_value=0.15):
    """A Body Apply as production performs it (W1 fd853661): write_side for the flex, and for the existing scale graph
    prod_bs_write_existing_scale(): the input layer's key 0 and the source control value, then the input channel
    operates; the expression evaluates and the bone takes the physical result. The output log is never written."""
    t = target(w)
    w.set_flex(t, "Muscles", muscles)
    g = t["graph"]
    g["in"].log.layers[0].keys[0][1] = control_value
    g["control"].set("value", control_value)
    g["expr"].set("value", control_value)
    g["expr"].set("result", scale)
    g["bone"].set("scale", scale)
    w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset", can_redo=False, redo_desc="")


APPLY_SPEC = {"undo_desc": "Apply Body Preset", "flex": {"Muscles": {"mono": {"effective": 0.8}}},
              "bones": {"bip_head": {"scale": 1.5, "control_value": 0.15, "graph": "existing"}}}


def fired_record(w, baseline, during=None):
    """The injector's complete fired record for a graph created since the baseline (in-transaction observation
    taken now unless given)."""
    during = during if during is not None else observe(w, config_name=ORDINARY)
    created = CORE_NS["created_elements"](baseline, during)
    return {"event": "fired", "injector": "v3", "candidate_sha256": W1_SHA256, "baseline": baseline,
            "in_transaction": during, "created": created["created"],
            "memberships_added": created["memberships_added"],
            "scale_attributes_created": created["scale_attributes_created"],
            "peer_changes": created["peer_changes"]}


class TestComparator(unittest.TestCase):
    def test_unchanged_positive(self):
        w = F.twin_world()
        self.assertEqual(verdict("unchanged", observe(w), observe(w)), (C.PASS, []))

    def test_negative_1_missing_required_fields(self):
        w = F.twin_world()
        a, b = observe(w), observe(w)
        for mutate in (lambda o: o.pop("undo"), lambda o: o["target"].pop("graphs"),
                       lambda o: o["target"]["bones"][1].pop("scale"),
                       lambda o: o["target"]["flex"]["Muscles"]["mono"].pop("log")):
            x, y = copy.deepcopy(a), copy.deepcopy(b)
            mutate(x)
            mutate(y)
            self.assertEqual(verdict("unchanged", x, y)[0], C.INSUFFICIENT)

    def test_negative_2_identical_unreadable_markers(self):
        w = F.twin_world()
        a = observe(w)
        for o in (a,):
            o["target"]["flex"]["Muscles"]["mono"]["stored"] = {"s": "unreadable", "e": "x"}
            o["complete"], o["insufficient"] = True, []
        self.assertEqual(verdict("unchanged", a, copy.deepcopy(a))[0], C.INSUFFICIENT)
        w = F.twin_world()
        target(w)["flex"]["Muscles"][0].unreadable.add("value")
        self.assertEqual(verdict("unchanged", observe(w), observe(w))[0], C.INSUFFICIENT)

    def test_negative_3_contradictory_or_wrong_instance_identity(self):
        w = F.twin_world()
        a = observe(w)
        t = target(w)
        replacement = F.El(w, "DmeAnimationSet", "krystal_target", **t["animset"].attrs)
        w.shot.attrs["animationSets"][0] = replacement
        self.assertEqual(verdict("unchanged", a, observe(w))[0], C.INSUFFICIENT)
        b = copy.deepcopy(a)
        b["peers"]["krystal_peer"]["identity"]["animset"] = b["target"]["identity"]["animset"]
        self.assertEqual(verdict("unchanged", a, b)[0], C.INSUFFICIENT)
        c = copy.deepcopy(a)
        c["context_end"]["head_seconds"]["v"] = 0.5
        self.assertEqual(verdict("unchanged", a, c)[0], C.INSUFFICIENT)

    def test_negative_4_unexpected_same_model_peer_change(self):
        w = F.twin_world()
        a = observe(w)
        w.set_flex(peer(w), "Legsize", 0.9)
        self.assertEqual(verdict("unchanged", a, observe(w))[0], C.MISMATCH)
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        w.set_flex(peer(w), "Muscles", 0.1)
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("peers" in r for r in reasons))

    def test_negative_5_changed_undo_state_when_preservation_required(self):
        w = F.twin_world()
        a = observe(w)
        w.dm.undo.update(can_redo=True, redo_desc="stray")
        b = observe(w)
        self.assertEqual(verdict("unchanged", a, b)[0], C.MISMATCH)

    def test_negative_6_incomplete_graph_removal(self):
        for keep in ("control", "operator", "channels", "group", "elements", "scale"):
            w = F.twin_world()
            a = observe(w, config_name=ORDINARY)
            t = target(w)
            w.scale_graph(t, "bip_hand_l", control_value=0.2, physical=2.0)
            fired = fired_record(w, a)
            created = fired["created"]
            w.remove_graph(t, keep=(keep,))
            b = observe(w, watch=created, config_name=ORDINARY)
            v, reasons = verdict("aborted", a, b, fired)
            self.assertEqual(v, C.MISMATCH, (keep, v, reasons))
            if keep in ("control", "operator", "channels", "group"):
                self.assertTrue(any("still attached" in r for r in reasons) or keep == "group", (keep, reasons))
        w = F.twin_world()
        a = observe(w, config_name=ORDINARY)
        t = target(w)
        w.scale_graph(t, "bip_hand_l", control_value=0.2, physical=2.0)
        fired = fired_record(w, a)
        w.remove_graph(t)
        self.assertEqual(verdict("aborted", a, observe(w, watch=fired["created"], config_name=ORDINARY), fired), (C.PASS, []))

    def test_equal_counts_and_names_are_not_restoration(self):
        w = F.twin_world()
        a = observe(w)
        t = target(w)
        old = t["flex"]["Legsize"][0]
        new = F.El(w, "DmElement", "Legsize", **old.attrs)
        t["controls"][t["controls"].index(old)] = new
        self.assertEqual(verdict("unchanged", a, observe(w))[0], C.MISMATCH)

    def test_negative_7_unreadable_scale_or_flex_relationships(self):
        for fn in (lambda w: target(w)["graph"]["out"].unreadable.add("toAttribute"),
                   lambda w: target(w)["flex"]["Muscles"][1].unreadable.add("fromElement"),
                   lambda w: target(w)["graph"]["expr"].unreadable.add("result")):
            w = F.twin_world()
            a = observe(w)
            fn(w)
            self.assertEqual(verdict("unchanged", a, observe(w))[0], C.INSUFFICIENT)

    def test_negative_8_false_preservation_from_missing_dictionary_keys(self):
        w = F.twin_world()
        a, b = observe(w), observe(w)
        del a["target"]["flex"]["Muscles"]
        del b["target"]["flex"]["Muscles"]
        self.assertNotEqual(verdict("unchanged", a, b)[0], C.PASS)
        self.assertEqual(C.differences({"x": 1}, {}), ["/x: present on one side only"])
        a2 = observe(w)
        b2 = copy.deepcopy(a2)
        del b2["target"]["bones"][1]["writers"]
        self.assertEqual(verdict("unchanged", a2, b2)[0], C.INSUFFICIENT)

    def test_apply_positive_and_negatives(self):
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        b = observe(w)
        self.assertEqual(verdict("apply", a, b, APPLY_SPEC), (C.PASS, []))
        self.assertEqual(verdict("apply", a, b, dict(APPLY_SPEC, flex={"Muscles": {"mono": {"effective": 0.7}}}))[0],
                         C.MISMATCH)
        w.set_flex(target(w), "Legsize", 0.33)
        self.assertEqual(verdict("apply", a, observe(w), APPLY_SPEC)[0], C.MISMATCH)        # undeclared change
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        t = target(w)
        g = t["graph"]
        g["out"].set("mode", 0)
        self.assertEqual(verdict("apply", a, observe(w), APPLY_SPEC)[0], C.MISMATCH)        # topology changed
        self.assertEqual(verdict("apply", a, observe(w), {"flex": {}, "bones": {}})[0], C.INSUFFICIENT)

    def test_apply_existing_graph_replaced_is_mismatch(self):
        w = F.twin_world()
        a = observe(w)
        t = target(w)
        old = w.remove_graph(t)
        w.scale_graph(t, "bip_head", control_value=0.15, physical=1.5)
        w.set_flex(t, "Muscles", 0.8)
        w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset")
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("identities changed" in r for r in reasons), reasons)

    def test_apply_created_graph(self):
        w = F.twin_world()
        a = observe(w)
        t = target(w)
        w.scale_graph(t, "bip_hand_l", control_value=0.2, physical=2.0)
        w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset")
        spec = {"undo_desc": "Apply Body Preset", "flex": {}, "bones": {"bip_hand_l": {"scale": 2.0,
                                                                                         "control_value": 0.2,
                                                                                         "graph": "created"}}}
        self.assertEqual(verdict("apply", a, observe(w), spec), (C.PASS, []))
        t["root"].attrs["controls"].remove(t["graph"]["control"])
        self.assertEqual(verdict("apply", a, observe(w), spec)[0], C.MISMATCH)

    def test_undo_redo_invariants(self):
        w = F.twin_world()
        base = observe(w)
        apply_change(w)
        applied = observe(w)
        w2 = F.twin_world()
        # Reuse the same world for identity continuity: undo restores values and moves the owned entry.
        t = target(w)
        apply_change(w, muscles=0.6995, scale=1.13, control_value=0.113)
        w.dm.undo.update(can_undo=False, undo_desc="", can_redo=True, redo_desc="Apply Body Preset")
        undone = observe(w)
        self.assertEqual(verdict("undo", base, undone, {"redo_desc": "Apply Body Preset"}), (C.PASS, []))
        self.assertEqual(verdict("undo", base, undone, {"redo_desc": "other"})[0], C.MISMATCH)
        self.assertEqual(verdict("undo", base, undone, {})[0], C.INSUFFICIENT)
        apply_change(w)
        redone = observe(w)
        self.assertEqual(verdict("redo", applied, redone, {"undo_desc": "Apply Body Preset"}), (C.PASS, []))
        w.dm.undo.update(can_undo=False)
        self.assertEqual(verdict("redo", applied, observe(w), {"undo_desc": "Apply Body Preset"})[0], C.MISMATCH)
        del w2, t

    def test_reopened_compares_portable_state_with_fresh_identities(self):
        a = observe(F.twin_world())
        b = observe(F.twin_world(doc_path="C:\\qual\\saved.dmx"))
        self.assertNotEqual(a["target"]["identity"]["animset"]["v"]["id"], b["target"]["identity"]["animset"]["v"]["id"])
        self.assertEqual(verdict("reopened", a, b, {"document_path": "C:\\qual\\saved.dmx",
                                                    "static_play": ["Muscles"]}), (C.PASS, []))
        w = F.twin_world()
        w.set_flex(target(w), "Legsize", 0.41)
        self.assertEqual(verdict("reopened", a, observe(w))[0], C.MISMATCH)
        self.assertEqual(verdict("reopened", a, b, {"static_play": ["Legsize"]})[0], C.MISMATCH)
        self.assertEqual(verdict("reopened", a, b, {"document_path": "C:\\elsewhere.dmx"})[0], C.INSUFFICIENT)
        # Native SFM reports the path in lower case; the declared copy still matches (T10).
        self.assertEqual(verdict("reopened", a, b, {"document_path": "C:\\QUAL\\Saved.dmx",
                                                    "static_play": ["Muscles"]}), (C.PASS, []))

    def test_reopened_tolerates_only_orientation_float32_rounding(self):
        # T10 adjudication: SFM save/reload moves orientation quaternion components by up to 2 float32 ULP.
        def step(x, n):
            return struct.unpack("<f", struct.pack("<i", struct.unpack("<i", struct.pack("<f", x))[0] + n))[0]

        def controls(o):
            return [o["target"]["transform_controls"]["bip_head"]] + \
                [p["transform_controls"]["bip_head"] for p in o["peers"].values()]
        a = observe(F.twin_world())
        b = observe(F.twin_world(doc_path="C:\\qual\\saved.dmx"))
        for o in (a, b):
            for rec in controls(o):
                rec["valueOrientation"] = {"s": "present", "v": [0.125, 0.25, 0.5, 0.75]}
                rec["valuePosition"] = {"s": "present", "v": [0.125, 0.25, 0.5]}
        spec = {"document_path": "C:\\qual\\saved.dmx"}

        def moved(field, n, value=None):
            c = copy.deepcopy(b)
            v = c["target"]["transform_controls"]["bip_head"][field]["v"]
            v[-1] = step(v[-1], n) if value is None else value
            return c
        verdict_, notes = verdict("reopened", a, moved("valueOrientation", 2), spec)
        self.assertEqual(verdict_, C.PASS)
        self.assertIn("maximum 2 ULP", notes[0])
        self.assertTrue(any(n.endswith(": 2 ULP") for n in notes[1:]))
        self.assertEqual(verdict("reopened", a, moved("valueOrientation", 3), spec)[0], C.MISMATCH)
        self.assertNotEqual(verdict("reopened", a, moved("valueOrientation", 0, float("inf")), spec)[0], C.PASS)
        self.assertEqual(verdict("reopened", a, moved("valuePosition", 1), spec)[0], C.MISMATCH)
        # Apply/Undo/Redo/unchanged stay exact.
        c = copy.deepcopy(a)
        c["target"]["transform_controls"]["bip_head"]["valueOrientation"]["v"][-1] = step(0.75, 1)
        self.assertEqual(verdict("unchanged", a, c)[0], C.MISMATCH)

    def test_reopened_orientation_tolerance_pairs_values_in_native_order(self):
        # D3: sorting the identity-free lists can pair different keys once equal quaternions drift.
        def obs(values):
            log = {"s": "present", "v": {"layers": [{"values": {"s": "present", "v": values}}]}}
            control = {"valueOrientation": {"s": "present", "v": [0.0, 0.0, 0.0, 1.0]},
                       "orientationChannel_view": {"log": log}}
            return {"target": {"transform_controls": {"c": control}}, "peers": {}, "channels_clips": []}
        moved = struct.unpack("<f", struct.pack("<i", struct.unpack("<i", struct.pack("<f", 0.75))[0] + 2))[0]
        hard, tolerated = C.reopened_differences(obs([[1.0, 0.75], [0.75, 0.875]]), obs([[1.0, 0.75], [moved, 0.875]]))
        self.assertEqual(hard, [])
        self.assertEqual([u for _, u in tolerated], [2])
        hard, _ = C.reopened_differences(obs([[1.0, 0.75], [0.75, 0.875]]), obs([[1.0, 0.75], [0.875, 0.875]]))
        self.assertTrue(hard)

    def test_preset_bone_coverage_and_full_precision(self):
        w = F.twin_world()
        o = observe(w)
        # Coverage is the control-backed bone map (T01 adjudication); the fake's two bones with no transform control,
        # no scale and no scale writer are excluded and reported.
        bones, notes = C.control_backed_bones(o)
        self.assertEqual(len(notes), 2)
        rows = [{"bone_index": b["index"], "bone_name": b["name"],
                 "value": b["scale"]["v"] if b["scale"]["s"] == "present" else 1.0} for b in o["target"]["bones"]
                if b["index"] in bones]
        values = {}
        for lit, row in o["target"]["flex"].items():
            sides = ("mono",) if row["shape"] == "MONO" else ("left", "right")
            values["flex." + lit] = dict((s, C.effective_value(row[s])[0]) for s in sides)
        preset = {"bone_scales": rows, "values": values}
        self.assertEqual(verdict("preset", o, preset), (C.PASS, notes))
        short = dict(preset, bone_scales=rows[:-1])
        self.assertEqual(verdict("preset", o, short)[0], C.MISMATCH)
        # Exclusion needs independent evidence: an uncontrolled bone with a scale value stays required.
        scaled = copy.deepcopy(o)
        scaled["target"]["bones"][0]["scale"] = {"s": "present", "v": 1.0}
        self.assertEqual(verdict("preset", scaled, preset)[0], C.MISMATCH)
        # A row for an excluded bone is outside the contract.
        b0 = o["target"]["bones"][0]
        extra = dict(preset, bone_scales=rows + [{"bone_index": b0["index"], "bone_name": b0["name"], "value": 1.0}])
        self.assertEqual(verdict("preset", o, extra)[0], C.MISMATCH)
        # An unreadable control target is insufficient evidence, never an exclusion.
        blind = copy.deepcopy(o)
        for rec in blind["target"]["transform_controls"].values():
            for view in ("positionChannel_view", "orientationChannel_view"):
                if isinstance(rec.get(view), dict):
                    rec[view]["to"] = {"s": "unreadable", "e": "test"}
        self.assertEqual(verdict("preset", blind, preset)[0], C.INSUFFICIENT)
        rounded = copy.deepcopy(preset)
        rounded["values"]["flex.Muscles"]["mono"] = round(rounded["values"]["flex.Muscles"]["mono"], 3)
        self.assertEqual(verdict("preset", o, rounded)[0], C.MISMATCH)
        stored = copy.deepcopy(preset)
        stored["values"]["flex.Muscles"]["mono"] = 0.0          # the stored source, not the effective key
        self.assertEqual(verdict("preset", o, stored)[0], C.MISMATCH)

    def test_prepared_fixture_invariant(self):
        w = F.World()
        w.instance("krystal_target", with_scale_graph=True, legsize=0.4)
        w.instance("krystal_peer", legsize=0.25)
        cfg = dict(F.CONFIG)
        ctl = target(w)["flex"]["Legsize"][0]
        a = observe(w, cfg, config_name=DEFERRED)
        ctl.set("value", 0.65)
        b = observe(w, cfg, config_name=DEFERRED)
        self.assertEqual(verdict("prepared", a, b, {"literal": "Legsize", "stored": 0.65}), (C.PASS, []))
        self.assertEqual(verdict("prepared", a, b, {"literal": "Legsize", "stored": 0.66})[0], C.MISMATCH)
        w.set_flex(target(w), "Muscles", 0.5)
        self.assertEqual(verdict("prepared", a, observe(w, cfg, config_name=DEFERRED),
                                 {"literal": "Legsize", "stored": 0.65})[0],
                         C.MISMATCH)

    def test_admission_requires_the_sole_writer_evidence(self):
        w = F.World()
        t = w.instance("krystal_target", with_scale_graph=True, legsize=0.4)
        w.instance("krystal_peer", legsize=0.25)
        ctl, ch, op = t["flex"]["Legsize"]
        other = F.Channel(w, "Legsize_other", ctl, "value", op, "flexWeight", 3, [[0, 0.4]])
        t["channels"].append(other)
        a = observe(w, config_name=DEFERRED)
        ctl.set("value", 0.65)
        v, reasons = verdict("prepared", a, observe(w, config_name=DEFERRED), {"literal": "Legsize", "stored": 0.65})
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("sole writer" in r for r in reasons), reasons)

    def test_exit_status_only_pass_succeeds(self):
        d = tempfile.mkdtemp()
        try:
            w = F.twin_world()
            a = observe(w)
            pa, pb = os.path.join(d, "a.json"), os.path.join(d, "b.json")
            for p, o in ((pa, a), (pb, a)):
                with io.open(p, "w", encoding="utf-8") as f:
                    f.write(json.dumps(o).encode("ascii").decode("ascii"))
            out = sys.stdout
            sys.stdout = io.StringIO() if sys.version_info[0] > 2 else __import__("StringIO").StringIO()
            try:
                self.assertEqual(C.main(["x", "unchanged", pa, pb]), 0)
                w.set_flex(peer(w), "Legsize", 0.9)
                with io.open(pb, "w", encoding="utf-8") as f:
                    f.write(json.dumps(observe(w)).encode("ascii").decode("ascii"))
                self.assertEqual(C.main(["x", "unchanged", pa, pb]), 1)
                b = dict(a, complete=False)
                with io.open(pb, "w", encoding="utf-8") as f:
                    f.write(json.dumps(b).encode("ascii").decode("ascii"))
                self.assertEqual(C.main(["x", "unchanged", pa, pb]), 2)
                self.assertEqual(C.main(["x", "bogus", pa, pa]), 2)
            finally:
                sys.stdout = out
        finally:
            shutil.rmtree(d, True)


# ---------------------------------------------------------------------------
# Astra-required corrections: one test per counterexample (findings 1, 2, 3 and 6; 4 and 5 are in TestProbes,
# TestDeferredFixture and TestConfigSelection). Each names the counterexample it reproduces.
# ---------------------------------------------------------------------------

def stereo(w, inst, literal="Breastsize"):
    ctl = [c for c in inst["controls"] if c.name == literal][0]
    return ctl, dict((side, ctl.attrs[side + "valuechannel"]) for side in ("left", "right"))


def set_stereo(ctl, ch, side, v):
    ch.log.layers[0].keys[0][1] = v
    ch.attrs["toElement"].set("flexWeight", v)


def empty_world():
    w = F.World()
    w.instance("krystal_target", with_scale_graph=True, extra_empty=(("Pregnant", 0.3),))
    w.instance("krystal_peer", muscles_key=0.5, legsize=0.25, extra_empty=(("Pregnant", 0.1),))
    return w, dict(F.CONFIG, body=F.CONFIG["body"] + ["Pregnant"])


def observe_with_watch(b, created):
    """B with a watch entry for every recorded element (fabricated ones are reported gone)."""
    b = copy.deepcopy(b)
    have = set(x["watched"]["id"] for x in b["watch"])
    for r in created:
        if r["id"] not in have:
            b["watch"].append({"watched": r, "now": {"s": "gone"}})
    return b


class TestFinding1ObserverCompleteness(unittest.TestCase):
    """complete=True and a comparator PASS were obtained with unreadable curveinfo, omitted nested log, layer or
    evaluation records, or a mismatching CPM identity."""

    def test_unreadable_curveinfo_is_insufficient(self):
        for where, how in (("layer", "claimed"), ("log", "claimed"), ("layer", "value"), ("log", "value")):
            w = F.twin_world()
            a = observe(w)
            ch = target(w)["flex"]["Legsize"][1]
            el = ch.log.layers[0] if where == "layer" else ch.log
            if how == "claimed":
                el.lying_presence.add("curveinfo")          # HasAttribute True, GetAttribute fails
            else:
                el.set("curveinfo", F.El(w, "DmeCurveInfo", "curveinfo"))
                el.unreadable.add("curveinfo")              # present, its value unreadable
            b = observe(w)
            where = where + "/" + how
            self.assertFalse(b["complete"], where)
            self.assertEqual(verdict("unchanged", a, b)[0], C.INSUFFICIENT, where)
            b["complete"], b["insufficient"] = True, []                  # a forged complete flag is not trusted
            self.assertEqual(verdict("unchanged", a, b)[0], C.INSUFFICIENT, where)

    def test_omitted_nested_records_are_insufficient_despite_complete(self):
        def log(o):
            return o["target"]["flex"]["Legsize"]["mono"]["log"]["v"]

        def layer(o):
            return log(o)["layers"][0]
        for name, mutate in (
                ("log identity", lambda o: log(o).pop("log")),
                ("channel log attribute", lambda o: log(o).pop("channel_log_attribute")),
                ("log defaults", lambda o: log(o).pop("defaultvalue")),
                ("bookmarks", lambda o: log(o).pop("bookmarks")),
                ("is_empty", lambda o: log(o).pop("is_empty")),
                ("evaluation", lambda o: log(o).pop("evaluated")),
                ("all layers", lambda o: log(o).update(layers=[])),
                ("layer identity", lambda o: layer(o).pop("layer")),
                ("raw times", lambda o: layer(o).pop("times")),
                ("raw values", lambda o: layer(o).pop("values")),
                ("compressed", lambda o: layer(o).pop("compressed")),
                ("layer curveinfo", lambda o: layer(o).pop("curveinfo")),
                ("keys", lambda o: layer(o).pop("keys")),
                ("graph output log", lambda o: o["target"]["graphs"][0]["output"]["log"]["v"].pop("layers")),
                ("graph input evaluation",
                 lambda o: o["target"]["graphs"][0]["inputs"][0]["log"]["v"].pop("evaluated")),
                ("graph operator expression", lambda o: o["target"]["graphs"][0]["operator_attributes"].pop("expr")),
                ("side clips", lambda o: o["target"]["flex"]["Legsize"]["mono"].pop("clips")),
                ("peer log", lambda o: o["peers"]["krystal_peer"]["flex"]["Muscles"]["mono"]["log"]["v"]
                 .pop("layers"))):
            w = F.twin_world()
            a = observe(w)
            b = copy.deepcopy(a)
            mutate(a)
            mutate(b)
            self.assertTrue(a["complete"])
            self.assertEqual(verdict("unchanged", a, b)[0], C.INSUFFICIENT, name)

    def test_inconsistent_nested_evidence_is_insufficient(self):
        w = F.twin_world()
        base = observe(w)
        for name, mutate in (
                ("raw values disagree with keys",
                 lambda o: o["target"]["flex"]["Legsize"]["mono"]["log"]["v"]["layers"][0]["values"]["v"]
                 .__setitem__(0, 0.9)),
                ("key count disagrees", lambda o: o["target"]["flex"]["Legsize"]["mono"]["log"]["v"]["layers"][0]
                 ["key_count"].__setitem__("v", 2)),
                ("layer count disagrees", lambda o: o["target"]["flex"]["Legsize"]["mono"]["log"]["v"]["layer_count"]
                 .__setitem__("v", 2)),
                ("channel log attribute names another log",
                 lambda o: o["target"]["flex"]["Legsize"]["mono"]["log"]["v"]["channel_log_attribute"]["v"]
                 .__setitem__("id", "other")),
                ("claimed representation contradicts the evidence",
                 lambda o: o["target"]["flex"]["Legsize"]["mono"]["representation"].__setitem__("v", "EMPTY")),
                ("graph channel outside every clip",
                 lambda o: [c.__setitem__("channels", [x for x in c["channels"] if x["name"] != "bip_head_scale_out"])
                            for c in o["channels_clips"]])):
            a, b = copy.deepcopy(base), copy.deepcopy(base)
            mutate(a)
            mutate(b)
            self.assertEqual(verdict("unchanged", a, b)[0], C.INSUFFICIENT, name)

    def test_cpm_identity_must_be_the_accepted_w1_candidate(self):
        w = F.twin_world()
        other = tempfile.NamedTemporaryFile(delete=False)
        other.write(b"not the candidate")
        other.close()
        try:
            cfg = dict(F.CONFIG, cpm={"path": other.name, "sha256": W1_SHA256})
            b = observe(w, cfg)
            self.assertFalse(b["complete"])
            self.assertEqual(verdict("unchanged", observe(w, cfg), b)[0], C.INSUFFICIENT)
            unpinned = observe(w, dict(F.CONFIG, cpm={}))
            self.assertFalse(unpinned["complete"])
        finally:
            os.remove(other.name)
        a = observe(w)
        for forged in ({"expected": W1_SHA256, "actual": "0" * 64, "match": True},
                       {"expected": W1_SHA256, "actual": W1_SHA256, "match": False}):
            x, y = copy.deepcopy(a), copy.deepcopy(a)
            for o in (x, y):
                o["integrity"]["cpm"] = {"s": "present", "v": forged}
            self.assertEqual(verdict("unchanged", x, y)[0], C.INSUFFICIENT, forged)
        x, y = copy.deepcopy(a), copy.deepcopy(a)
        for o in (x, y):
            del o["integrity"]["cpm"]
        self.assertEqual(verdict("unchanged", x, y)[0], C.INSUFFICIENT)

    def test_verified_absence_of_optional_attributes_is_preserved(self):
        w = F.twin_world()
        a = observe(w)
        layer = a["target"]["flex"]["Legsize"]["mono"]["log"]["v"]["layers"][0]
        self.assertEqual(layer["curveinfo"], {"s": "absent"})
        self.assertEqual(verdict("unchanged", a, observe(w)), (C.PASS, []))


class TestFinding2ApplyPreservesUndeclaredState(unittest.TestCase):
    """False PASSes after changing an evaluated flex value, a log default, a log identity, an undeclared stereo
    side, a scale expression or a scale control source value."""

    def applied(self):
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        return w, a

    def test_positive_apply_still_passes(self):
        w, a = self.applied()
        self.assertEqual(verdict("apply", a, observe(w), APPLY_SPEC), (C.PASS, []))

    def test_changed_evaluated_flex_value(self):
        w, a = self.applied()
        b = observe(w)
        side = b["target"]["flex"]["Muscles"]["mono"]
        side["log"]["v"]["evaluated"]["v"] = 0.81           # evaluation differs from the declared effective value
        side["representation"]["v"] = "OTHER"
        v, reasons = verdict("apply", a, b, APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH, reasons)
        b = observe(w)
        b["target"]["flex"]["Muscles"]["mono"]["destination_value"]["v"] = 0.81
        self.assertNotEqual(verdict("apply", a, b, APPLY_SPEC)[0], C.PASS)

    def test_changed_log_default(self):
        w, a = self.applied()
        target(w)["flex"]["Muscles"][1].log.attrs["defaultvalue"] = 0.9
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("defaultvalue" in r for r in reasons), reasons)

    def test_changed_log_identity(self):
        w, a = self.applied()
        ch = target(w)["flex"]["Muscles"][1]
        ch.log = F.Log(w, ch.name, [list(k) for k in ch.log.layers[0].keys])
        ch.attrs["log"] = ch.log
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("/log/" in r for r in reasons), reasons)

    def test_changed_stored_source_when_declared_unchanged(self):
        w, a = self.applied()
        target(w)["flex"]["Muscles"][0].set("value", 0.25)
        self.assertEqual(verdict("apply", a, observe(w), APPLY_SPEC)[0], C.MISMATCH)

    def test_undeclared_stereo_side(self):
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        ctl, chans = stereo(w, target(w))
        set_stereo(ctl, chans["left"], "left", 0.4)
        spec = dict(APPLY_SPEC, flex={"Muscles": {"mono": {"effective": 0.8}},
                                      "Breastsize": {"left": {"effective": 0.4}}})
        self.assertEqual(verdict("apply", a, observe(w), spec), (C.PASS, []))
        set_stereo(ctl, chans["right"], "right", 0.45)                  # the opposite side is protected
        v, reasons = verdict("apply", a, observe(w), spec)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("Breastsize/right" in r for r in reasons), reasons)

    def test_changed_scale_expression(self):
        w, a = self.applied()
        target(w)["graph"]["expr"].set("expr", "lerp(value, lo, hi) * 2")
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("expr" in r for r in reasons), reasons)

    def test_scale_control_source_value(self):
        w, a = self.applied()
        target(w)["graph"]["control"].set("value", 0.16)
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("scale control source" in r for r in reasons), reasons)
        w, a = self.applied()
        v, reasons = verdict("apply", a, observe(w), dict(APPLY_SPEC, bones={"bip_head": {
            "scale": 1.5, "graph": "existing"}}))
        self.assertEqual(v, C.INSUFFICIENT)                                    # the control value must be declared
        self.assertTrue(any("must declare finite control_value" in r for r in reasons), reasons)

    def test_physical_output_and_graph_topology(self):
        w, a = self.applied()
        target(w)["graph"]["bone"].set("scale", 1.6)
        self.assertEqual(verdict("apply", a, observe(w), APPLY_SPEC)[0], C.MISMATCH)
        w, a = self.applied()
        target(w)["graph"]["out"].log.attrs["defaultvalue"] = 7.0
        self.assertEqual(verdict("apply", a, observe(w), APPLY_SPEC)[0], C.MISMATCH)
        w, a = self.applied()
        target(w)["graph"]["expr"].set("hi", 5.0)
        self.assertEqual(verdict("apply", a, observe(w), APPLY_SPEC)[0], C.MISMATCH)


class TestFinding3AbortAndGraphRemoval(unittest.TestCase):
    """Abort proof: complete fired record, independently reconciled inventories, post-abort absence and
    unresolvability of every created element, restoration and Undo, no peer change."""

    def aborted(self, keep=(), keep_resolvable=(), peer_during=False):
        w = F.twin_world()
        a = observe(w, config_name=ORDINARY)
        w.scale_graph(target(w), "bip_hand_l", control_value=0.2, physical=2.0)
        if peer_during:
            w.set_flex(peer(w), "Legsize", 0.7)
        fired = fired_record(w, a)
        if peer_during:
            w.set_flex(peer(w), "Legsize", 0.25)
        w.remove_graph(target(w), keep=keep, keep_resolvable=keep_resolvable)
        return a, observe(w, watch=fired["created"], config_name=ORDINARY), fired

    def test_complete_abort_passes(self):
        a, b, fired = self.aborted()
        self.assertEqual(verdict("aborted", a, b, fired), (C.PASS, []))
        self.assertEqual(sorted(set(r["role"] for r in fired["created"])),
                         ["channel", "control", "layer", "log", "operator"])

    def test_missing_creation_entries(self):
        a, b, fired = self.aborted()
        for role in ("control", "operator", "channel", "log", "layer"):
            f = copy.deepcopy(fired)
            f["created"] = [r for r in f["created"] if r["role"] != role]
            v, reasons = verdict("aborted", a, b, f)
            self.assertEqual(v, C.INSUFFICIENT, role)
            self.assertTrue(any("does not reconcile" in r for r in reasons), (role, reasons))
        f = copy.deepcopy(fired)
        extra = dict(f["created"][0], id="fabricated-id", handle=-1)
        f["created"].append(extra)                      # a recorded element the observations never evidenced
        self.assertEqual(verdict("aborted", a, observe_with_watch(b, f["created"]), f)[0], C.INSUFFICIENT)
        f = copy.deepcopy(fired)
        f["memberships_added"] = [m for m in f["memberships_added"] if not m[0].startswith("control_group")]
        self.assertEqual(verdict("aborted", a, b, f)[0], C.INSUFFICIENT)
        f = copy.deepcopy(fired)
        f["scale_attributes_created"] = []
        self.assertEqual(verdict("aborted", a, b, f)[0], C.INSUFFICIENT)

    def test_truncated_inventory_does_not_redefine_what_must_be_removed(self):
        a, b, fired = self.aborted()
        f = copy.deepcopy(fired)
        out = [r for r in f["created"] if r["name"] == "bip_hand_l_scale_out" and r["role"] == "channel"][0]
        for clip in f["in_transaction"]["channels_clips"]:
            clip["channels"] = [c for c in clip["channels"] if c["id"] != out["id"]]
        f["created"] = [r for r in f["created"] if not r["name"].startswith("bip_hand_l_scale_out")]
        self.assertEqual(verdict("aborted", a, b, f)[0], C.INSUFFICIENT)
        f = copy.deepcopy(fired)
        f["in_transaction"]["target"]["graphs"] = []
        self.assertEqual(verdict("aborted", a, b, f)[0], C.INSUFFICIENT)

    def test_surviving_elements(self):
        for part in ("control", "expr", "in", "out", "in_log", "out_log", "in_layer", "out_layer"):
            a, b, fired = self.aborted(keep_resolvable=(part,))
            v, reasons = verdict("aborted", a, b, fired)
            self.assertEqual(v, C.MISMATCH, part)
            self.assertTrue(any("still resolvable" in r for r in reasons), (part, reasons))
        a, b, fired = self.aborted()
        b["watch"] = [x for x in b["watch"] if x["watched"]["role"] != "layer"]
        self.assertEqual(verdict("aborted", a, b, fired)[0], C.INSUFFICIENT)       # no resolvability evidence

    def test_incomplete_fired_record(self):
        a, b, fired = self.aborted()
        for k in C.FIRED:
            f = copy.deepcopy(fired)
            del f[k]
            v, reasons = verdict("aborted", a, b, f)
            self.assertEqual(v, C.INSUFFICIENT, k)
            self.assertTrue(any("complete fired record" in r for r in reasons), (k, reasons))
        for k, v in (("event", "armed"), ("injector", "v2"), ("candidate_sha256", "0" * 64)):
            self.assertEqual(verdict("aborted", a, b, dict(fired, **{k: v}))[0], C.INSUFFICIENT, k)
        f = copy.deepcopy(fired)
        f["in_transaction"]["complete"] = False
        self.assertEqual(verdict("aborted", a, b, f)[0], C.INSUFFICIENT)
        f = copy.deepcopy(fired)
        del f["in_transaction"]["target"]["flex"]["Muscles"]["mono"]["log"]["v"]["evaluated"]
        self.assertEqual(verdict("aborted", a, b, f)[0], C.INSUFFICIENT)

    def test_contradictory_identities(self):
        a, b, fired = self.aborted()
        # Another instance in another session, observed with the same ordinary configuration, so that the
        # configuration-identity check cannot be what refuses: the wrong-instance identity check must.
        other = observe(F.twin_world(), config_name=ORDINARY)
        for k in ("baseline", "in_transaction"):
            v, reasons = verdict("aborted", a, b, dict(fired, **{k: other}))
            self.assertEqual(v, C.INSUFFICIENT, k)
            self.assertTrue(any("identity differs (wrong instance)" in r for r in reasons), (k, reasons))
        f = copy.deepcopy(fired)
        f["created"][0]["handle"] = f["created"][0]["handle"] + 100000
        v, reasons = verdict("aborted", a, b, f)
        self.assertEqual(v, C.INSUFFICIENT)
        self.assertTrue(any("contradicts its observed role or handle" in r for r in reasons), reasons)
        f = copy.deepcopy(fired)
        f["created"][0]["role"] = "operator" if f["created"][0]["role"] != "operator" else "control"
        v, reasons = verdict("aborted", a, b, f)
        self.assertEqual(v, C.INSUFFICIENT)
        self.assertTrue(any("contradicts its observed role or handle" in r for r in reasons), reasons)
        moved = copy.deepcopy(a)                        # same instance, but not the state A recorded
        moved["target"]["flex"]["Legsize"]["mono"]["stored"]["v"] = 0.5
        side = moved["target"]["flex"]["Legsize"]["mono"]
        side["representation"]["v"] = C.representation_of(side)                       # self-consistent evidence
        C.sufficiency(moved, "moved")
        self.assertEqual(verdict("aborted", a, b, dict(fired, baseline=moved))[0], C.INSUFFICIENT)

    def test_recorded_peer_mutation(self):
        a, b, fired = self.aborted(peer_during=True)
        self.assertEqual(fired["peer_changes"], ["krystal_peer"])
        v, reasons = verdict("aborted", a, b, fired)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("peer" in r for r in reasons), reasons)
        f = copy.deepcopy(fired)
        f["peer_changes"] = []                          # an omitted record does not hide the observed change
        v, reasons = verdict("aborted", a, b, f)
        self.assertEqual(v, C.MISMATCH)

    def test_target_and_undo_restoration(self):
        a, b, fired = self.aborted()
        b2 = copy.deepcopy(b)
        b2["undo"]["can_redo"]["v"] = True
        self.assertEqual(verdict("aborted", a, b2, fired)[0], C.MISMATCH)
        b3 = copy.deepcopy(b)
        b3["target"]["flex"]["Muscles"]["mono"]["stored"]["v"] = 0.1
        self.assertNotEqual(verdict("aborted", a, b3, fired)[0], C.PASS)


class TestFinding6PresetEmptyLog(unittest.TestCase):
    """inv_preset refused a valid EMPTY log (it read the missing first key)."""

    def preset_for(self, o):
        bones, _ = C.control_backed_bones(o)
        rows = [{"bone_index": b["index"], "bone_name": b["name"],
                 "value": b["scale"]["v"] if b["scale"]["s"] == "present" else 1.0} for b in o["target"]["bones"]
                if b["index"] in bones]
        values = {}
        for lit, row in o["target"]["flex"].items():
            sides = ("mono",) if row["shape"] == "MONO" else ("left", "right")
            values["flex." + lit] = dict((s, C.effective_value(row[s])[0]) for s in sides)
        return {"bone_scales": rows, "values": values}

    def test_empty_log_effective_value_is_the_coherent_stored_source(self):
        w, cfg = empty_world()
        o = observe(w, cfg)
        side = o["target"]["flex"]["Pregnant"]["mono"]
        self.assertEqual(side["representation"]["v"], "EMPTY")
        self.assertEqual(C.effective_value(side), (0.3, None))
        preset = self.preset_for(o)
        self.assertEqual(preset["values"]["flex.Pregnant"]["mono"], 0.3)
        self.assertEqual(verdict("preset", o, preset), (C.PASS, C.control_backed_bones(o)[1]))

    def test_empty_log_negatives(self):
        w, cfg = empty_world()
        o = observe(w, cfg)
        preset = self.preset_for(o)
        wrong = copy.deepcopy(preset)
        wrong["values"]["flex.Pregnant"]["mono"] = 0.0
        self.assertEqual(verdict("preset", o, wrong)[0], C.MISMATCH)
        missing = copy.deepcopy(preset)
        del missing["values"]["flex.Pregnant"]
        self.assertEqual(verdict("preset", o, missing)[0], C.MISMATCH)
        for name, mutate in (("contradictory evaluation", lambda s: s["log"]["v"]["evaluated"].__setitem__("v", 0.5)),
                             ("contradictory destination", lambda s: s["destination_value"].__setitem__("v", 0.5)),
                             ("nonfinite stored", lambda s: s["stored"].__setitem__("v", float("nan"))),
                             ("missing stored", lambda s: s["stored"].__setitem__("v", None))):
            x = copy.deepcopy(o)
            mutate(x["target"]["flex"]["Pregnant"]["mono"])
            self.assertNotEqual(verdict("preset", x, preset)[0], C.PASS, name)
        x = copy.deepcopy(o)
        x["target"]["flex"]["Pregnant"]["mono"]["log"]["v"]["is_empty"]["v"] = False
        self.assertEqual(verdict("preset", x, preset)[0], C.INSUFFICIENT)      # claimed EMPTY contradicts IsEmpty

    def test_empty_log_requires_is_empty_true(self):
        w, cfg = empty_world()
        target(w)["flex"]["Pregnant"][1].log.broken.add("is_empty")
        o = observe(w, cfg)
        self.assertFalse(o["complete"])
        self.assertEqual(verdict("preset", o, self.preset_for(observe(empty_world()[0], cfg)))[0], C.INSUFFICIENT)

    def test_admission_is_not_broadened(self):
        w, cfg = empty_world()
        o = observe(w, cfg)
        self.assertTrue(C.admitted_static_play(o, "Pregnant"))       # EMPTY is never static-play admitted
        self.assertEqual(C.admitted_static_play(o, "Muscles"), [])
        self.assertTrue(C.admitted_static_play(o, "Legsize"))


# ---------------------------------------------------------------------------
# Astra's final W2 review: compressed data (R1), supported Apply representations (R2A empty output log, R2B EMPTY to
# one key), and the Abort Injector configuration handoff (R3). Production references are to W1 fd853661.
# ---------------------------------------------------------------------------

INVALID_COMPRESSED = bytes(bytearray(range(231, 256)))          # 25 bytes that are no valid compressed block


def side_layer(obs, literal, side="mono"):
    return obs["target"]["flex"][literal][side]["log"]["v"]["layers"][0]


class TestR1CompressedData(unittest.TestCase):
    """Astra: an Apply comparison returned PASS after 25 invalid compressed-data bytes were introduced into the
    changed flex's layer (mask_log_values() masked the compressed record; check_log() checked only its shape)."""

    def test_astra_25_byte_injection_into_the_changed_flex_layer(self):
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        target(w)["flex"]["Muscles"][1].log.layers[0].set("compressed", INVALID_COMPRESSED)
        b = observe(w)
        self.assertEqual(side_layer(b, "Muscles")["compressed"]["v"]["length"], 25)
        v, reasons = verdict("apply", a, b, APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("compressed" in r for r in reasons), reasons)
        # The same change written into the B record alone (the Observer's own evidence left consistent).
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        b = observe(w)
        side_layer(b, "Muscles")["compressed"]["v"] = {
            "length": 25, "sha256": hashlib.sha256(INVALID_COMPRESSED).hexdigest()}
        v, reasons = verdict("apply", a, b, APPLY_SPEC)
        self.assertEqual(v, C.INSUFFICIENT)                 # the STATIC_PLAY claim now contradicts the evidence
        self.assertTrue(any("contradicts its evidence" in r for r in reasons), reasons)
        b["target"]["flex"]["Muscles"]["mono"]["representation"]["v"] = "OTHER"   # self-consistent, as the core
        v, reasons = verdict("apply", a, b, APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("/compressed/" in r for r in reasons), reasons)

    def test_valid_authorized_apply_still_passes_with_empty_or_absent_blocks(self):
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        b = observe(w)
        self.assertEqual(C.compressed_state(side_layer(b, "Muscles")), "empty")
        self.assertEqual(verdict("apply", a, b, APPLY_SPEC), (C.PASS, []))
        w = F.twin_world()
        for el in list(w.elements.values()):
            if el.kind == "DmeFloatLogLayer":
                el.drop("compressed")                     # verified absence on every layer
        a = observe(w)
        apply_change(w)
        b = observe(w)
        self.assertEqual(C.compressed_state(side_layer(b, "Muscles")), "absent")
        self.assertEqual(verdict("apply", a, b, APPLY_SPEC), (C.PASS, []))

    def test_compressed_changes_elsewhere_are_never_authorized(self):
        for where in ("Legsize", "graph input", "graph output", "peer"):
            w = F.twin_world()
            a = observe(w)
            apply_change(w)
            layer = {"Legsize": lambda: target(w)["flex"]["Legsize"][1].log.layers[0],
                     "graph input": lambda: target(w)["graph"]["in"].log.layers[0],
                     "graph output": lambda: target(w)["graph"]["out"].log.layers[0],
                     "peer": lambda: peer(w)["flex"]["Legsize"][1].log.layers[0]}[where]()
            layer.set("compressed", INVALID_COMPRESSED)
            v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
            self.assertEqual(v, C.MISMATCH, where)
            self.assertTrue(any("compressed" in r for r in reasons), (where, reasons))

    def test_four_states_are_distinguished(self):
        w = F.twin_world()
        target(w)["flex"]["Legsize"][1].log.layers[0].drop("compressed")
        target(w)["flex"]["Breastsize"] = None
        o = observe(w)
        self.assertEqual(C.compressed_state(side_layer(o, "Legsize")), "absent")
        self.assertEqual(C.compressed_state(side_layer(o, "Muscles")), "empty")
        w = F.twin_world()
        target(w)["flex"]["Legsize"][1].log.layers[0].set("compressed", INVALID_COMPRESSED)
        self.assertEqual(C.compressed_state(side_layer(observe(w), "Legsize")), "nonempty")
        w = F.twin_world()
        a = observe(w)
        target(w)["flex"]["Legsize"][1].log.layers[0].unreadable.add("compressed")
        b = observe(w)
        self.assertEqual(side_layer(b, "Legsize")["compressed"]["s"], "unreadable")
        self.assertFalse(b["complete"])
        self.assertEqual(verdict("unchanged", a, b)[0], C.INSUFFICIENT)

    def test_malformed_compressed_records_are_insufficient(self):
        w = F.twin_world()
        base = observe(w)
        for name, rec in (("zero bytes, non-empty digest", {"length": 0, "sha256": "0" * 64}),
                          ("negative length", {"length": -1, "sha256": "0" * 64}),
                          ("fractional length", {"length": 2.5, "sha256": "0" * 64}),
                          ("missing digest", {"length": 25}),
                          ("non-hex digest", {"length": 25, "sha256": "z" * 64}),
                          ("extra field", {"length": 0, "sha256": C.EMPTY_SHA256, "data": "x"}),
                          ("not a record", 25)):
            a, b = copy.deepcopy(base), copy.deepcopy(base)
            for o in (a, b):
                side_layer(o, "Legsize")["compressed"] = {"s": "present", "v": rec}
            v, reasons = verdict("unchanged", a, b)
            self.assertEqual(v, C.INSUFFICIENT, name)
            self.assertTrue(any("compressed" in r for r in reasons), (name, reasons))

    def test_supported_representation_rules_are_preserved(self):
        # STATIC_PLAY_ONE_KEY_ZERO (CPM's flex_static_play_admitted) requires an empty or absent compressed block and
        # no curve metadata; ONE_KEY_ZERO and EMPTY carry no such production rule, so data there is not prohibited
        # (only never authorized to change).
        w = F.twin_world()
        target(w)["flex"]["Muscles"][1].log.layers[0].set("compressed", INVALID_COMPRESSED)
        target(w)["flex"]["Legsize"][1].log.layers[0].set("compressed", INVALID_COMPRESSED)
        o = observe(w)
        self.assertEqual(o["target"]["flex"]["Muscles"]["mono"]["representation"]["v"], "OTHER")
        self.assertEqual(C.representation_of(o["target"]["flex"]["Muscles"]["mono"]), "OTHER")
        self.assertTrue(C.admitted_static_play(o, "Muscles"))
        self.assertEqual(C.representation_of(o["target"]["flex"]["Legsize"]["mono"]), "ONE_KEY_ZERO")
        self.assertEqual(verdict("unchanged", o, observe(w)), (C.PASS, []))
        w = F.twin_world()
        target(w)["flex"]["Muscles"][1].log.layers[0].set("curvetypes", [1])
        self.assertEqual(C.representation_of(observe(w)["target"]["flex"]["Muscles"]["mono"]), "OTHER")
        a = observe(F.twin_world())
        x = copy.deepcopy(a)
        side_layer(x, "Muscles")["compressed"]["v"] = {
            "length": 25, "sha256": hashlib.sha256(INVALID_COMPRESSED).hexdigest()}
        self.assertEqual(verdict("unchanged", x, copy.deepcopy(x))[0], C.INSUFFICIENT)   # claim contradicts evidence


class TestR2AScaleEmptyOutputLog(unittest.TestCase):
    """Astra: graph_value_problems() required the output log's evaluation to equal the physical scale, refusing the
    accepted M-05 graph, whose mode-3 output log is empty with usedefaultvalue False (physical 1.13)."""

    def test_fixture_has_the_accepted_m05_topology(self):
        o = observe(F.twin_world())
        g = o["target"]["graphs"][0]
        out = g["output"]["log"]["v"]
        self.assertEqual((g["output"]["mode"]["v"], g["output"]["to_attribute"]["v"]), (3, "scale"))
        self.assertEqual((pv(out["layers"][0]["keys"]), pv(out["is_empty"]), pv(out["usedefaultvalue"]),
                          pv(out["defaultvalue"]), pv(out["evaluated"])), ([], True, False, 0.0, 0.0))
        self.assertEqual(C.compressed_state(out["layers"][0]), "empty")
        self.assertEqual(pv(g["operator_attributes"]["expr"]), "lerp(value, lo, hi)")
        self.assertEqual((pv(g["operator_attributes"]["lo"]), pv(g["operator_attributes"]["hi"])), (0.0, 10.0))
        self.assertEqual(pv(g["inputs"][0]["log"]["v"]["layers"][0]["keys"]), [[0, 0.113]])
        self.assertEqual([pv(b["scale"]) for b in o["target"]["bones"] if b["name"] == "bip_head"], [1.13])

    def test_apply_with_the_empty_output_log_passes(self):
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        b = observe(w)
        out = b["target"]["graphs"][0]["output"]["log"]["v"]
        self.assertEqual(pv(out["evaluated"]), 0.0)          # not the physical 1.5; no longer a requirement
        self.assertEqual(verdict("apply", a, b, APPLY_SPEC), (C.PASS, []))

    def check(self, mutate, expect=None):
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        spec = mutate(w) or APPLY_SPEC
        v, reasons = verdict("apply", a, observe(w), spec)
        self.assertEqual(v, C.MISMATCH, reasons)
        if expect:
            self.assertTrue(any(expect in r for r in reasons), reasons)

    def test_invalid_physical_results(self):
        self.check(lambda w: target(w)["graph"]["bone"].set("scale", 1.6), "physical scale")
        self.check(lambda w: target(w)["graph"]["expr"].set("result", 1.6), "expression result")
        self.check(lambda w: dict(APPLY_SPEC, bones={"bip_head": {"scale": 1.6, "control_value": 0.15,
                                                                 "graph": "existing"}}), "declared scale")

    def test_graph_modifications(self):
        def key_on_output(w):
            target(w)["graph"]["out"].log.layers[0].keys[:] = [[0, 1.5]]
        self.check(key_on_output, "output")
        self.check(lambda w: target(w)["graph"]["out"].log.set("usedefaultvalue", True), "usedefaultvalue")
        self.check(lambda w: target(w)["graph"]["out"].log.set("defaultvalue", 1.5), "defaultvalue")
        self.check(lambda w: target(w)["graph"]["out"].set("mode", 1), "mode")
        self.check(lambda w: target(w)["graph"]["expr"].set("hi", 20.0), "hi")
        self.check(lambda w: target(w)["graph"]["expr"].set("expr", "value * hi"), "expr")

        def extra_input_key(w):
            target(w)["graph"]["in"].log.layers[0].keys.append([100, 0.15])
        self.check(extra_input_key, "input log")

    def test_mode_1_keyed_output_log_is_protected(self):
        # CPM's historical output-pass graph (mode 1) is supported with any output log; Apply never writes it.
        w = F.World()
        w.instance("krystal_target", with_scale_graph=True, graph_output_mode=1, graph_output_log="keyed")
        w.instance("krystal_peer", muscles_key=0.5, legsize=0.25)
        a = observe(w)
        apply_change(w)
        self.assertEqual(verdict("apply", a, observe(w), APPLY_SPEC), (C.PASS, []))
        target(w)["graph"]["out"].log.layers[0].keys[0][1] = 1.5     # the output log written: never by CPM
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("/output/log/" in r for r in reasons), reasons)

    def test_mode_3_output_with_usedefaultvalue_true_is_unsupported(self):
        w = F.twin_world()
        target(w)["graph"]["out"].log.set("usedefaultvalue", True)    # before and after: unchanged, unsupported
        a = observe(w)
        apply_change(w)
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("usedefaultvalue False" in r for r in reasons), reasons)
        self.assertFalse(any("undeclared Apply change" in r for r in reasons), reasons)

    def test_unsupported_expression_present_before_and_after_refuses(self):
        # The expression is unchanged between A and B (so the protected-state comparison alone cannot refuse it),
        # but it is not CPM's lerp(value, lo, hi): the declared scale cannot be verified.
        w = F.twin_world()
        target(w)["graph"]["expr"].set("expr", "value * hi")
        a = observe(w)
        apply_change(w)
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("unsupported scale expression" in r for r in reasons), reasons)
        self.assertFalse(any("operator_attributes/expr" in r for r in reasons), reasons)

    def test_keyed_mode_3_output_is_not_a_supported_representation(self):
        w = F.World()
        w.instance("krystal_target", with_scale_graph=True, graph_output_log="keyed")
        w.instance("krystal_peer", muscles_key=0.5, legsize=0.25)
        a = observe(w)
        apply_change(w)
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("not the supported empty log" in r for r in reasons), reasons)
        self.assertTrue(C.qualified_graph_problems(a))

    def test_created_mode_1_graph_still_passes(self):
        w = F.twin_world()
        a = observe(w)
        w.scale_graph(target(w), "bip_hand_l", control_value=0.2, physical=2.0)
        w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset")
        spec = {"undo_desc": "Apply Body Preset", "flex": {},
                "bones": {"bip_hand_l": {"scale": 2.0, "control_value": 0.2, "graph": "created"}}}
        self.assertEqual(verdict("apply", a, observe(w), spec), (C.PASS, []))


def pv(rec):
    return C.pv(rec)


EMPTY_SPEC = {"undo_desc": "Apply Body Preset", "flex": {"Pregnant": {"mono": {"effective": 0.55, "stored": 0.55}}},
              "bones": {}}


class TestR2BEmptyToOneKeyApply(unittest.TestCase):
    """Astra: CPM's write_side() turns an admitted EMPTY side into one key at time zero (source set, then
    ClearAndAddSampleAtTime(0) on the same layer); the comparator refused it because the key count, the time array
    and IsEmpty() change."""

    def applied(self, desired=0.55):
        w, cfg = empty_world()
        a = observe(w, cfg)
        w.write_side(target(w), "Pregnant", desired)
        w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset")
        return w, cfg, a

    def test_supported_transition_passes(self):
        w, cfg, a = self.applied()
        b = observe(w, cfg)
        self.assertEqual(C.representation_of(a["target"]["flex"]["Pregnant"]["mono"]), "EMPTY")
        self.assertEqual(C.representation_of(b["target"]["flex"]["Pregnant"]["mono"]), "ONE_KEY_ZERO")
        self.assertEqual(verdict("apply", a, b, EMPTY_SPEC), (C.PASS, []))

    def refused(self, mutate, spec=EMPTY_SPEC, expect=None):
        w, cfg, a = self.applied()
        mutate(w)
        v, reasons = verdict("apply", a, observe(w, cfg), spec)
        self.assertEqual(v, C.MISMATCH, reasons)
        if expect:
            self.assertTrue(any(expect in r for r in reasons), reasons)

    def layer(self, w):
        return target(w)["flex"]["Pregnant"][1].log.layers[0]

    def test_extra_keys(self):
        self.refused(lambda w: self.layer(w).keys.append([100, 0.55]), expect="exactly one key")

    def test_incorrect_time(self):
        def move(w):
            self.layer(w).keys[0][0] = 5
        self.refused(move, expect="time zero")

    def test_incorrect_value(self):
        def value(w):
            self.layer(w).keys[0][1] = 0.5
        self.refused(value, expect="declared value")
        self.refused(lambda w: None, spec=dict(EMPTY_SPEC, flex={"Pregnant": {"mono": {"effective": 0.6,
                                                                                    "stored": 0.6}}}))

    def test_source_not_written(self):
        self.refused(lambda w: target(w)["flex"]["Pregnant"][0].set("value", 0.3), expect="stored source")

    def test_malformed_transitions(self):
        def new_layer(w):
            ch = target(w)["flex"]["Pregnant"][1]
            ch.log.layers[0] = F.Layer(w, ch.name, [[0, 0.55]])
        self.refused(new_layer)

        def new_log(w):
            ch = target(w)["flex"]["Pregnant"][1]
            ch.log = F.Log(w, ch.name, [[0, 0.55]])
            ch.attrs["log"] = ch.log
        self.refused(new_log)
        self.refused(lambda w: target(w)["flex"]["Pregnant"][1].log.set("defaultvalue", 0.55), expect="defaultvalue")
        self.refused(lambda w: self.layer(w).set("compressed", INVALID_COMPRESSED), expect="compressed")

    def test_undeclared_sides_and_literals(self):
        self.refused(lambda w: None, spec=dict(EMPTY_SPEC, flex={}))          # the EMPTY write itself undeclared
        self.refused(lambda w: w.set_flex(target(w), "Legsize", 0.45), expect="Legsize")
        self.refused(lambda w: w.write_side(peer(w), "Pregnant", 0.55), expect="peers")

    def test_undeclared_opposite_stereo_side_of_an_empty_stereo_flex(self):
        w, cfg = empty_world()
        ctl = [c for c in target(w)["controls"] if c.name == "Breastsize"][0]
        chans = dict((s, ctl.attrs[s + "valuechannel"]) for s in ("left", "right"))
        for side, ch in chans.items():                    # both sides EMPTY, evaluating their stored sources
            ch.log.layers[0].keys[:] = []
            ch.log.set("defaultvalue", ctl.attrs[side + "Value"])
        a = observe(w, cfg)
        self.assertEqual([C.representation_of(a["target"]["flex"]["Breastsize"][s]) for s in ("left", "right")],
                         ["EMPTY", "EMPTY"])

        def write(side, v):                                # CPM write_side, EMPTY origin, one stereo side
            ctl.set(side + "Value", v)
            chans[side].log.layers[0].keys[:] = [[0, v]]
            chans[side].attrs["toElement"].set("flexWeight", v)
        write("left", 0.42)
        w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset")
        spec = {"undo_desc": "Apply Body Preset", "bones": {},
                "flex": {"Breastsize": {"left": {"effective": 0.42, "stored": 0.42}}}}
        self.assertEqual(verdict("apply", a, observe(w, cfg), spec), (C.PASS, []))
        write("right", 0.47)
        v, reasons = verdict("apply", a, observe(w, cfg), spec)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("Breastsize/right" in r for r in reasons), reasons)

    def test_keyed_origin_time_array_and_empty_flag_stay_protected(self):
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        b = observe(w)
        layer = b["target"]["flex"]["Muscles"]["mono"]["log"]["v"]["layers"][0]
        layer["times"]["v"][0]["seconds"] = 0.0          # raw time record changed, ticks unchanged
        b = json.loads(json.dumps(b))
        v, reasons = verdict("apply", a, b, APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("/times/" in r for r in reasons), reasons)
        b = observe(w)
        b["target"]["flex"]["Muscles"]["mono"]["log"]["v"]["is_empty"]["v"] = True     # keys present, IsEmpty True
        b["target"]["flex"]["Muscles"]["mono"]["representation"]["v"] = "OTHER"          # as the core now claims
        v, reasons = verdict("apply", a, b, APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("is_empty" in r for r in reasons), reasons)

    def test_key_structure_is_not_exempted_for_keyed_origins(self):
        w = F.twin_world()
        a = observe(w)
        apply_change(w)
        target(w)["flex"]["Muscles"][1].log.layers[0].keys.append([100, 0.8])
        v, reasons = verdict("apply", a, observe(w), APPLY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        w, cfg = empty_world()
        layer = target(w)["flex"]["Pregnant"][1].log.layers[0]
        layer.keys[:] = [[0, 0.3], [100, 0.3]]                # an unsupported (two-key) origin
        a = observe(w, cfg)
        layer.keys[:] = [[0, 0.55]]
        target(w)["flex"]["Pregnant"][0].set("value", 0.55)
        target(w)["flex"]["Pregnant"][2].set("flexWeight", 0.55)
        w.dm.undo.update(can_undo=True, undo_desc="Apply Body Preset")
        v, reasons = verdict("apply", a, observe(w, cfg), EMPTY_SPEC)
        self.assertEqual(v, C.MISMATCH)
        self.assertTrue(any("origin representation OTHER" in r for r in reasons), reasons)

    def test_control_value_still_required(self):
        w, cfg, a = self.applied()
        spec = dict(EMPTY_SPEC, bones={"bip_head": {"scale": 1.13, "graph": "existing"}})
        v, reasons = verdict("apply", a, observe(w, cfg), spec)
        self.assertEqual(v, C.INSUFFICIENT)
        self.assertTrue(any("must declare finite control_value" in r for r in reasons), reasons)


def filled_template(d, template, name):
    with io.open(os.path.join(ROOT, "config", template), encoding="utf-8") as f:
        text = f.read()
    for a, b in (("<SFM game>", "G:/SFM"), ("<QUAL_DIR>", "G:/Q"), ("<protected original session>", "G:/o.dmx"),
                 ("<protected M-05 fixture>", "G:/m05.dmx"), ("<sha256>", "0" * 64)):
        text = text.replace(a, b)
    path = os.path.join(d, name)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def staged_abort_handoff(work, w):
    """The real evidence chain under fakes: stage both configurations, run the staged ordinary Observer (A), arm the
    staged Abort Injector, let the Apply create a scale graph and write Muscles (the injector fires inside the
    transaction and raises), abort (graph removed, Muscles restored), run the staged ordinary Observer again (B, with
    the injector's watch list). Returns (A, B, fired, staged_dir, run)."""
    import stage_instruments as ST
    out = ST.stage(filled_template(work, "m06w2_config.template.json", "main.json"), os.path.join(work, "staged"),
                   filled_template(work, "m06w2_deferred_config.template.json", "deferred.json"))
    obs = os.path.join(work, "obs")
    for cname in ("m06w2_config.json", "m06w2_deferred_config.json"):
        p = os.path.join(out, cname)
        with io.open(p, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.update(observation_dir=obs, cpm=F.CONFIG["cpm"], shot="shot12", target_animset="krystal_target",
                   peers=["krystal_peer"], body=F.CONFIG["body"], nonbody=F.CONFIG["nonbody"], protected={},
                   watch_path=os.path.join(obs, "watch.json"), injector={"target_literal": "Muscles"},
                   instrument_files={})
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(json.dumps(cfg).encode("ascii").decode("ascii"))
    sfm, vs = w.modules()
    cpm = types.ModuleType("chadchan3d_cpm_app")

    def write_side(binding, side, origin, desired):
        w.set_flex(target(w), binding["literal"], desired)
    cpm.write_side = write_side
    mods = {"sfmApp": types.ModuleType("sfmApp"), "vs": types.ModuleType("vs"), "PySide": types.ModuleType("PySide"),
            "chadchan3d_cpm_app": cpm}
    mods["sfmApp"].__dict__.update(dict((k, getattr(sfm, k)) for k in dir(sfm) if not k.startswith("_")))
    mods["vs"].g_pDataModel, mods["vs"].tier1 = vs.g_pDataModel, vs.tier1

    def run(name):
        path = os.path.join(out, name)
        with open(path, "rb") as f:
            src = re.sub(b'INSTRUMENT_DIR = u"[^"\\n]*"', b"INSTRUMENT_DIR = u" + repr(out).lstrip("u").encode("utf-8")
                         .replace(b"\\\\", b"\\\\\\\\"), f.read())
        saved = dict((k, sys.modules.get(k)) for k in list(mods) + ["PySide.QtGui"])
        sys.modules.update(mods)
        sys.modules.pop("PySide.QtGui", None)
        stdout = sys.stdout
        sys.stdout = io.StringIO() if sys.version_info[0] > 2 else __import__("StringIO").StringIO()
        try:
            eval(compile(src, path, "exec"), {"__name__": "__main__"})
            return sys.stdout.getvalue()
        finally:
            sys.stdout = stdout
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def latest(prefix, suffix=".json"):
        names = sorted(n for n in os.listdir(obs) if n.startswith(prefix) and n.endswith(suffix))
        with io.open(os.path.join(obs, names[-1]), encoding="utf-8") as f:
            return json.load(f)
    run("M06_Qualification_Observer.py")
    a = latest("obs_")
    armed = run("M06_Qualification_Abort_Injector.py")
    assert "ARMED" in armed, armed
    w.scale_graph(target(w), "bip_hand_l", control_value=0.2, physical=2.0)      # prod_bs_create_graph
    try:
        cpm.write_side({"literal": "Muscles"}, "mono", 0.6995, 0.8)
        raise AssertionError("the injector did not fire")
    except RuntimeError:
        pass
    w.remove_graph(target(w))                                                      # AbortUndoableOperation
    w.set_flex(target(w), "Muscles", 0.6995)
    run("M06_Qualification_Observer.py")
    b = latest("obs_")
    fired = latest("injector_", "_fired.json")
    return a, b, fired, out, run


class TestR3AbortConfigurationHandoff(unittest.TestCase):
    """Astra: a valid Abort comparison refused because the ordinary Observer records config_name while the
    injector's baseline and in-transaction observations omitted it."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="m06w2_handoff_")

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_real_observer_injector_comparator_handoff_passes(self):
        w = F.twin_world()
        a, b, fired, out, run = staged_abort_handoff(self.dir, w)
        names = [a["config_name"], fired["baseline"]["config_name"], fired["in_transaction"]["config_name"],
                 b["config_name"]]
        self.assertEqual(names, [ORDINARY] * 4)
        self.assertEqual(len(set([a["config_sha256"], fired["baseline"]["config_sha256"],
                                  fired["in_transaction"]["config_sha256"], b["config_sha256"]])), 1)
        self.assertTrue(all(o["complete"] for o in (a, b, fired["baseline"], fired["in_transaction"])))
        self.assertEqual(verdict("aborted", a, b, fired), (C.PASS, []))

    def test_missing_or_mismatched_configuration_identities_refuse(self):
        w = F.twin_world()
        a, b, fired, out, run = staged_abort_handoff(self.dir, w)
        for name, mutate in (
                ("in-transaction omitted", lambda a, b, f: f["in_transaction"].__setitem__("config_name", None)),
                ("baseline deferred", lambda a, b, f: f["baseline"].__setitem__("config_name", DEFERRED)),
                ("A omitted", lambda a, b, f: a.__setitem__("config_name", None)),
                ("B omitted", lambda a, b, f: b.__setitem__("config_name", None)),
                ("A and B deferred", lambda a, b, f: [o.__setitem__("config_name", DEFERRED) for o in (a, b)]),
                ("all omitted", lambda a, b, f: [o.__setitem__("config_name", None) for o in
                                                 (a, b, f["baseline"], f["in_transaction"])])):
            x, y, f = copy.deepcopy(a), copy.deepcopy(b), copy.deepcopy(fired)
            mutate(x, y, f)
            v, reasons = verdict("aborted", x, y, f)
            self.assertEqual(v, C.INSUFFICIENT, name)
            self.assertTrue(any("configuration" in r for r in reasons), (name, reasons))
        x = copy.deepcopy(a)
        del x["config_name"]
        self.assertEqual(verdict("aborted", x, b, fired)[0], C.INSUFFICIENT)

    def test_post_abort_observation_from_the_deferred_observer_refuses(self):
        w = F.twin_world()
        a, b, fired, out, run = staged_abort_handoff(self.dir, w)
        run("M06_Deferred_Observer.py")
        names = sorted(n for n in os.listdir(os.path.join(self.dir, "obs")) if n.startswith("obs_"))
        with io.open(os.path.join(self.dir, "obs", names[-1]), encoding="utf-8") as f:
            deferred_b = json.load(f)
        self.assertEqual(deferred_b["config_name"], DEFERRED)
        v, reasons = verdict("aborted", a, deferred_b, fired)
        self.assertEqual(v, C.INSUFFICIENT)
        self.assertTrue(any("configuration" in r for r in reasons), reasons)

    def test_injector_refuses_a_configuration_that_does_not_name_itself(self):
        w = F.twin_world()
        a, b, fired, out, run = staged_abort_handoff(self.dir, w)
        p = os.path.join(out, "m06w2_config.json")
        with io.open(p, encoding="utf-8") as f:
            cfg = json.load(f)
        for wrong in (None, DEFERRED):
            cfg["config_name"] = wrong
            with io.open(p, "w", encoding="utf-8") as f:
                f.write(json.dumps(cfg).encode("ascii").decode("ascii"))
            text = run("M06_Qualification_Abort_Injector.py")
            self.assertIn("not the staged ordinary configuration", text)
            self.assertIn("Nothing was armed.", text)

    def test_complete_reconciliation_removal_and_peer_checks_still_apply(self):
        w = F.twin_world()
        a, b, fired, out, run = staged_abort_handoff(self.dir, w)
        f = copy.deepcopy(fired)
        f["created"] = [r for r in f["created"] if r["role"] != "layer"]
        self.assertEqual(verdict("aborted", a, b, f)[0], C.INSUFFICIENT)
        f = copy.deepcopy(fired)
        f["peer_changes"] = ["krystal_peer"]
        self.assertEqual(verdict("aborted", a, b, f)[0], C.MISMATCH)
        y = copy.deepcopy(b)
        y["watch"][0]["now"] = y["watch"][0]["watched"] and {"s": "present", "v": {}}
        self.assertEqual(verdict("aborted", a, y, fired)[0], C.MISMATCH)


class TestR4ConfigDigest(unittest.TestCase):
    """Astra: sufficiency() required config_sha256 to exist but never validated it, and identities() only compared
    values, so matching invalid digests (null, empty, "fabricated") passed. Every observation's config_sha256 must be
    a genuine SHA-256 text rendering (64 hexadecimal characters); cross-report equality is kept."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="m06w2_digest_")
        cls.a, cls.b, cls.fired, _, _ = staged_abort_handoff(cls.dir, F.twin_world())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, True)

    def evidence(self):
        return copy.deepcopy(self.a), copy.deepcopy(self.b), copy.deepcopy(self.fired)

    def four(self, a, b, f):
        return [("A", a), ("fired/baseline", f["baseline"]), ("fired/in_transaction", f["in_transaction"]), ("B", b)]

    def test_actual_staged_handoff_digests_are_valid_and_pass(self):
        a, b, f = self.evidence()
        digests = [o["config_sha256"] for _, o in self.four(a, b, f)]
        self.assertEqual(len(set(digests)), 1)
        self.assertTrue(C.sha256_text(digests[0]))
        self.assertEqual(verdict("aborted", a, b, f), (C.PASS, []))

    def test_astra_matching_invalid_digests_refuse(self):
        for name, value in (("null", None), ("empty", ""), ("fabricated", "fabricated")):
            a, b, f = self.evidence()
            for _, o in self.four(a, b, f):
                o["config_sha256"] = value
            v, reasons = verdict("aborted", a, b, f)
            self.assertEqual(v, C.INSUFFICIENT, name)
            self.assertTrue(any("config_sha256" in r and "is not a SHA-256 digest" in r for r in reasons),
                            (name, reasons))

    def test_invalid_digest_in_each_individual_observation(self):
        for label in ("A", "fired/baseline", "fired/in_transaction", "B"):
            a, b, f = self.evidence()
            dict(self.four(a, b, f))[label]["config_sha256"] = "fabricated"
            v, reasons = verdict("aborted", a, b, f)
            self.assertEqual(v, C.INSUFFICIENT, label)
            self.assertTrue(any(r.startswith(label + "/config_sha256") for r in reasons), (label, reasons))

    def test_wrong_types_truncated_and_nonhexadecimal_digests(self):
        good = self.a["config_sha256"]
        for name, value in (("integer", 123), ("float", 1.5), ("boolean", True), ("list", [good]),
                            ("object", {"sha256": good}), ("truncated", good[:63]), ("extended", good + "0"),
                            ("non-hexadecimal", "g" * 64), ("padded", " " + good[1:]), ("prefixed", "0x" + good[2:]),
                            ("short", "ab" * 16)):
            a, b, f = self.evidence()
            for _, o in self.four(a, b, f):
                o["config_sha256"] = value
            v, reasons = verdict("aborted", a, b, f)
            self.assertEqual(v, C.INSUFFICIENT, name)
            self.assertTrue(any("is not a SHA-256 digest" in r for r in reasons), (name, reasons))

    def test_matching_valid_format_digests_pass(self):
        for value in ("ab" * 32, "0" * 64, "AB" * 32):
            a, b, f = self.evidence()
            for _, o in self.four(a, b, f):
                o["config_sha256"] = value
            self.assertEqual(verdict("aborted", a, b, f), (C.PASS, []), value)

    def test_contradictory_valid_format_digests_refuse(self):
        for label in ("A", "fired/baseline", "fired/in_transaction", "B"):
            a, b, f = self.evidence()
            o = dict(self.four(a, b, f))[label]
            o["config_sha256"] = ("f" if o["config_sha256"][0] != "f" else "e") + o["config_sha256"][1:]
            self.assertTrue(C.sha256_text(o["config_sha256"]))
            v, reasons = verdict("aborted", a, b, f)
            self.assertEqual(v, C.INSUFFICIENT, label)
            self.assertTrue(any("taken with different configurations" in r for r in reasons), (label, reasons))
            self.assertFalse(any("is not a SHA-256 digest" in r for r in reasons), (label, reasons))

    def test_digest_is_validated_for_every_invariant(self):
        w = F.twin_world()
        a, b = observe(w), observe(w)
        self.assertEqual(verdict("unchanged", a, b), (C.PASS, []))
        for value in (None, "", "fabricated"):
            x, y = copy.deepcopy(a), copy.deepcopy(b)
            x["config_sha256"] = y["config_sha256"] = value
            v, reasons = verdict("unchanged", x, y)
            self.assertEqual(v, C.INSUFFICIENT, value)
            self.assertTrue(any("is not a SHA-256 digest" in r for r in reasons), (value, reasons))
        x = copy.deepcopy(a)
        del x["config_sha256"]
        self.assertEqual(verdict("unchanged", x, b)[0], C.INSUFFICIENT)


# ---------------------------------------------------------------------------
# Abort injector and graph-recovery evidence
# ---------------------------------------------------------------------------

class TestInjector(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="m06w2_inj_")
        self.saved = dict((k, sys.modules.get(k)) for k in ("sfmApp", "vs", "chadchan3d_cpm_app", "PySide",
                                                             "PySide.QtGui"))

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        shutil.rmtree(self.dir, True)

    def install(self, w, cpm_path=W1_APP):
        idir = os.path.join(self.dir, "instruments")
        os.makedirs(idir)
        shutil.copy2(CORE, os.path.join(idir, "m06w2_core.py"))
        cfg = dict(F.CONFIG, observation_dir=os.path.join(self.dir, "obs"),
                   watch_path=os.path.join(self.dir, "watch.json"), injector={"target_literal": "Muscles"},
                   cpm={"path": cpm_path, "sha256": W1_SHA256}, config_name=ORDINARY)
        with io.open(os.path.join(idir, "m06w2_config.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(cfg).encode("ascii").decode("ascii"))
        sfm, vs = w.modules()
        sys.modules["sfmApp"] = types.ModuleType("sfmApp")
        sys.modules["sfmApp"].__dict__.update(dict((k, getattr(sfm, k)) for k in dir(sfm) if not k.startswith("_")))
        sys.modules["vs"] = types.ModuleType("vs")
        sys.modules["vs"].g_pDataModel, sys.modules["vs"].tier1 = vs.g_pDataModel, vs.tier1
        cpm = types.ModuleType("chadchan3d_cpm_app")
        calls = []

        def write_side(binding, side, origin, desired):
            calls.append(binding["literal"])
            w.set_flex(target(w), binding["literal"], desired)
        cpm.write_side = write_side
        sys.modules["chadchan3d_cpm_app"] = cpm
        sys.modules["PySide"] = types.ModuleType("PySide")      # no QtGui: dialogs fall back to print
        sys.modules.pop("PySide.QtGui", None)
        return idir, cfg, cpm, calls

    def run_script(self, name, idir):
        path = os.path.join(ROOT, "instruments", name)
        with open(path, "rb") as f:
            src = f.read().replace(b'u"<INSTRUMENT_DIR>"', ("u" + repr(idir).lstrip("u")).encode("utf-8"))
        out = sys.stdout
        sys.stdout = io.StringIO() if sys.version_info[0] > 2 else __import__("StringIO").StringIO()
        try:
            eval(compile(src, path, "exec"), {"__name__": "__main__"})
            return sys.stdout.getvalue()
        finally:
            sys.stdout = out

    def records(self, cfg, event):
        d = cfg["observation_dir"]
        names = sorted(n for n in os.listdir(d) if n.startswith("injector_") and n.endswith("_%s.json" % event))
        rows = []
        for n in names:
            with io.open(os.path.join(d, n), encoding="utf-8") as f:
                rows.append(json.load(f))
        return rows

    def test_pinned_candidate_refuses_any_other_cpm(self):
        w = F.twin_world()
        other = os.path.join(self.dir, "other.py")
        with open(other, "wb") as f:
            f.write(b"not the candidate")
        idir, cfg, cpm, calls = self.install(w, cpm_path=other)
        real = cpm.write_side
        out = self.run_script("M06_Qualification_Abort_Injector.py", idir)
        self.assertIn("not the accepted W1 candidate", out)
        self.assertIn("Nothing was armed.", out)               # the injector's own pin check, before any observation
        self.assertFalse(os.path.isdir(cfg["observation_dir"]) and os.listdir(cfg["observation_dir"]))
        self.assertIs(cpm.write_side, real)

    def test_incomplete_baseline_refuses_to_arm(self):
        w = F.twin_world()
        target(w)["flex"]["Legsize"][0].unreadable.add("value")
        idir, cfg, cpm, calls = self.install(w)
        real = cpm.write_side
        out = self.run_script("M06_Qualification_Abort_Injector.py", idir)
        self.assertIn("INSUFFICIENT", out)
        self.assertIs(cpm.write_side, real)

    def fire(self, w, idir, cpm, create_bone="bip_hand_l"):
        out = self.run_script("M06_Qualification_Abort_Injector.py", idir)
        self.assertIn("ARMED", out)
        graph = w.scale_graph(target(w), create_bone, control_value=0.2, physical=2.0)    # prod_bs_create_graph
        with self.assertRaises(RuntimeError):
            cpm.write_side({"literal": "Muscles"}, "mono", 0.6995, 0.8)
        return graph

    def test_fired_record_holds_every_created_element_and_attachment(self):
        w = F.twin_world()
        idir, cfg, cpm, calls = self.install(w)
        graph = self.fire(w, idir, cpm)
        fired = self.records(cfg, "fired")[0]
        roles = sorted((c["role"], c["name"]) for c in fired["created"])
        self.assertEqual(roles, [("channel", "bip_hand_l_scale"), ("channel", "bip_hand_l_scale_out"),
                                 ("control", "bip_hand_l_scale"), ("layer", "bip_hand_l_scale"),
                                 ("layer", "bip_hand_l_scale_out"), ("log", "bip_hand_l_scale"),
                                 ("log", "bip_hand_l_scale_out"), ("operator", "bip_hand_l_scale_expr")])
        out_ch = [c for c in fired["created"] if c["name"] == "bip_hand_l_scale_out"][0]
        self.assertEqual(out_ch["endpoints"]["to_attribute"]["v"], "scale")
        kinds = sorted(set(m[0].split(":")[0] for m in fired["memberships_added"]))
        self.assertEqual(kinds, ["animset.controls", "animset.operators", "channels_clip", "control_group"])
        self.assertEqual([s["bone"] for s in fired["scale_attributes_created"]], ["bip_hand_l"])
        self.assertEqual(fired["scale_attributes_created"][0]["physical"], 2.0)
        self.assertEqual(fired["peer_changes"], [])
        with io.open(cfg["watch_path"], encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)["created"]), 8)
        self.assertEqual(calls, ["Muscles"])
        self.assertIsNot(getattr(cpm.write_side, "_m06w2_qualification_injector", None), True)
        del graph

    def test_post_abort_complete_cleanup_passes_and_incomplete_cleanup_fails(self):
        for keep, expect in (((), C.PASS), (("control",), C.MISMATCH), (("elements",), C.MISMATCH),
                             (("channels",), C.MISMATCH), (("scale",), C.MISMATCH)):
            w = F.twin_world()
            idir, cfg, cpm, calls = self.install(w)
            before = observe(w, cfg, config_name=ORDINARY)  # the Observer and the injector share one config
            self.fire(w, idir, cpm)
            fired = self.records(cfg, "fired")[0]
            w.remove_graph(target(w), keep=keep)           # AbortUndoableOperation (fully or not)
            w.set_flex(target(w), "Muscles", 0.6995)
            with io.open(cfg["watch_path"], encoding="utf-8") as f:
                watch = json.load(f)["created"]
            after = observe(w, cfg, watch=watch, config_name=ORDINARY)
            v, reasons = verdict("aborted", before, after, fired)
            self.assertEqual(v, expect, (keep, reasons))
            for k in list(sys.modules):
                if k in ("sfmApp", "vs", "chadchan3d_cpm_app"):
                    sys.modules.pop(k)
            self.tearDown()
            self.setUp()

    def test_aborted_without_created_evidence_is_insufficient(self):
        w = F.twin_world()
        a = observe(w)
        self.assertEqual(verdict("aborted", a, observe(w), {"created": []})[0], C.INSUFFICIENT)
        self.assertEqual(verdict("aborted", a, observe(w), {})[0], C.INSUFFICIENT)

    def test_peer_change_inside_the_transaction_is_recorded(self):
        w = F.twin_world()
        before = observe(w)
        w.set_flex(peer(w), "Legsize", 0.7)
        during = observe(w)
        self.assertEqual(CORE_NS["created_elements"](before, during)["peer_changes"], ["krystal_peer"])

    def test_injector_source_pins_the_accepted_candidate(self):
        with io.open(os.path.join(ROOT, "instruments", "M06_Qualification_Abort_Injector.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn(W1_SHA256, src)
        self.assertNotIn("d2bd6fd6", src)


# ---------------------------------------------------------------------------
# Deferred-verification fixture
# ---------------------------------------------------------------------------

class Dmx(object):
    """A minimal binary DMX format-5 writer for scanner tests (element ids are synthetic)."""

    def __init__(self):
        self.elements = []

    def el(self, kind, name, **attrs):
        self.elements.append([kind, name, attrs])
        return len(self.elements) - 1

    def bytes(self):
        strings = []

        def s(x):
            if x not in strings:
                strings.append(x)
            return strings.index(x)
        for kind, name, attrs in self.elements:
            s(kind)
            s(name)
            for k, v in attrs.items():
                s(k)
                if isinstance(v, tuple) and v[0] == "str":
                    s(v[1])
        body = b""
        for i, (kind, name, attrs) in enumerate(self.elements):
            body += struct.pack("<ii", s(kind), s(name)) + struct.pack("<16B", *([i % 256] * 16))
        for kind, name, attrs in self.elements:
            body += struct.pack("<i", len(attrs))
            for k, v in sorted(attrs.items()):
                body += struct.pack("<i", s(k))
                tag, x = v
                if tag == "ref":
                    body += struct.pack("<Bi", 1, x)
                elif tag == "int":
                    body += struct.pack("<Bi", 2, x)
                elif tag == "float":
                    body += struct.pack("<Bf", 3, x)
                elif tag == "str":
                    body += struct.pack("<Bi", 5, s(x))
                elif tag == "refs":
                    body += struct.pack("<Bi", 15, len(x)) + b"".join(struct.pack("<i", r) for r in x)
                elif tag == "floats":
                    body += struct.pack("<Bi", 17, len(x)) + b"".join(struct.pack("<f", r) for r in x)
                elif tag == "times":
                    body += struct.pack("<Bi", 21, len(x)) + b"".join(struct.pack("<i", r) for r in x)
        head = b"<!-- dmx encoding binary 5 format sfm_session 20 -->\n\0"
        table = struct.pack("<i", len(strings)) + b"".join(x.encode("utf-8") + b"\0" for x in strings)
        return head + table + struct.pack("<i", len(self.elements)) + body


def fixture_dmx(path, mode=3, keys=1, graph=True, graph_mode=3, graph_output_mode=3):
    d = Dmx()
    clip = d.el("DmeFilmClip", "shot10", animationSets=("refs", []))
    aset = d.el("DmeAnimationSet", "Krystal", controls=("refs", []))
    d.elements[clip][2]["animationSets"] = ("refs", [aset])
    controls = []
    for lit, key in (("Muscles", 0.35), ("Legsize", 0.6)):
        layer = d.el("DmeFloatLogLayer", lit, times=("times", [0] * keys), values=("floats", [key] * keys))
        log = d.el("DmeFloatLog", lit, layers=("refs", [layer]))
        op = d.el("DmeGlobalFlexControllerOperator", lit, flexWeight=("float", key))
        ch = d.el("DmeChannel", lit, mode=("int", mode), log=("ref", log), toElement=("ref", op),
                  toAttribute=("str", "flexWeight"))
        controls.append(d.el("DmElement", lit, value=("float", key), channel=("ref", ch)))
    if graph:
        bone = d.el("DmeTransform", "bone 55 (bip_head)", scale=("float", 1.13))
        expr = d.el("DmeExpressionOperator", "bip_head_scale", value=("float", 0.113))
        cin = d.el("DmeChannel", "bip_head_scale", mode=("int", graph_mode), toElement=("ref", expr),
                   toAttribute=("str", "value"))
        d.el("DmeChannel", "bip_head_scale_out", mode=("int", graph_output_mode), fromElement=("ref", expr),
             toElement=("ref", bone), toAttribute=("str", "scale"))
        controls.append(d.el("DmElement", "bip_head_scale", value=("float", 0.113), channel=("ref", cin)))
    d.elements[aset][2]["controls"] = ("refs", controls)
    with open(path, "wb") as f:
        f.write(d.bytes())


class TestDeferredFixture(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="m06w2_fix_")

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_scan_selects_a_qualifying_flex_and_an_intact_graph(self):
        p = os.path.join(self.dir, "f.dmx")
        fixture_dmx(p)
        r = SCAN.scan(p, "shot10", "Krystal", ["Muscles"])
        self.assertEqual(r["stop"], [])
        self.assertTrue(r["file_identity"]["unchanged_after_read"])
        self.assertEqual(r["selected"]["literal"], "Muscles")
        self.assertNotEqual(r["selected"]["proposed_stored"], r["selected"]["key"])
        self.assertEqual(r["selected"]["proposed_stored"],
                         struct.unpack("<f", struct.pack("<f", r["selected"]["proposed_stored"]))[0])
        self.assertTrue(r["scale_graphs"][0]["intact"])

    def test_scan_stops_rather_than_broadening(self):
        for kw, why in (({"mode": 1}, "no flex"), ({"keys": 2}, "no flex"), ({"graph": False}, "no intact"),
                        ({"graph_mode": 1}, "no intact"), ({"graph_output_mode": 1}, "no intact")):
            p = os.path.join(self.dir, "f%s_%s.dmx" % (why.replace(" ", ""), sorted(kw)[0]))
            fixture_dmx(p, **kw)
            r = SCAN.scan(p, "shot10", "Krystal", [])
            self.assertTrue(any(why in s for s in r["stop"]), (kw, r["stop"]))
        r = SCAN.scan(p, "shot10", "Nobody", [])
        self.assertTrue(r["stop"])

    @unittest.skipUnless(M05_FIXTURE and os.path.isfile(M05_FIXTURE), "M-05 fixture not available")
    def test_scan_of_the_accepted_m05_fixture(self):
        r = SCAN.scan(M05_FIXTURE, "shot10", "Krystal", ["Muscles"])
        self.assertEqual(r["file_identity"]["sha256"], "fa9a0a461b12ce2d51e4a05b2ebde6c8c3ad845ca4b4ddc9fdf63fe348b0767a")
        self.assertTrue(r["file_identity"]["unchanged_after_read"])
        self.assertEqual(r["stop"], [])
        self.assertEqual(r["selected"]["literal"], "Muscles")

    def prep_env(self, w, path_ok=True, stored=0.65, literal="Legsize", config_name=DEFERRED):
        idir = os.path.join(self.dir, "instruments")
        os.makedirs(idir)
        shutil.copy2(CORE, os.path.join(idir, "m06w2_core.py"))
        shutil.copy2(os.path.join(ROOT, "tools", "compare_obs.py"), os.path.join(idir, "compare_obs.py"))
        copy_path = os.path.join(self.dir, "disposable.dmx")
        orig = os.path.join(self.dir, "original.dmx")
        for p in (copy_path, orig):
            with open(p, "wb") as f:
                f.write(b"fixture bytes")
        w.doc_path = copy_path if path_ok else orig
        sha = hashlib.sha256(b"fixture bytes").hexdigest()
        cfg = dict(F.CONFIG, observation_dir=os.path.join(self.dir, "obs"), config_name=config_name,
                   preparation={"disposable_copy": copy_path, "disposable_copy_sha256": sha,
                                "protected_original": orig, "protected_original_sha256": sha, "literal": literal,
                                "stored": stored, "graph_bone": "bip_head", "save_as": "<persistence copy>"})
        with io.open(os.path.join(idir, "m06w2_deferred_config.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(cfg).encode("ascii").decode("ascii"))
        sfm, vs = w.modules()
        mods = {"sfmApp": types.ModuleType("sfmApp"), "vs": types.ModuleType("vs")}
        mods["sfmApp"].__dict__.update(dict((k, getattr(sfm, k)) for k in dir(sfm) if not k.startswith("_")))
        mods["vs"].g_pDataModel = vs.g_pDataModel
        w.dm.StartUndo = lambda a, b: w.dm.undo.update(open=True)
        w.dm.FinishUndo = lambda: w.dm.undo.update(can_undo=True, undo_desc="M06W2 deferred fixture preparation")
        qt = types.ModuleType("PySide")
        gui = types.ModuleType("PySide.QtGui")
        gui.QMessageBox = type("QMessageBox", (object,), {"Yes": 1, "No": 0,
                                                         "question": staticmethod(lambda *a: 1),
                                                         "information": staticmethod(lambda *a: None)})
        qt.QtGui = gui
        mods["PySide"], mods["PySide.QtGui"] = qt, gui
        saved = dict((k, sys.modules.get(k)) for k in mods)
        sys.modules.update(mods)
        return idir, cfg, saved

    def run_prep(self, idir, saved):
        path = os.path.join(ROOT, "native", "M06_Deferred_Fixture_Preparation.py")
        with open(path, "rb") as f:
            src = f.read().replace(b'u"<INSTRUMENT_DIR>"', ("u" + repr(idir).lstrip("u")).encode("utf-8"))
        try:
            eval(compile(src, path, "exec"), {"__name__": "__main__"})
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def outputs(self, cfg):
        d = cfg["observation_dir"]
        return dict((n.split("_")[-1][:-5], json.load(io.open(os.path.join(d, n), encoding="utf-8")))
                    for n in sorted(os.listdir(d)))

    def test_preparation_changes_only_the_stored_source(self):
        w = F.twin_world()
        idir, cfg, saved = self.prep_env(w)
        ctl = target(w)["flex"]["Legsize"][0]
        self.run_prep(idir, saved)
        out = self.outputs(cfg)
        self.assertNotIn("stop", out, out.get("stop"))
        self.assertEqual(ctl.attrs["value"], 0.65)
        self.assertEqual(verdict("prepared", out["before"], out["after"], {"literal": "Legsize", "stored": 0.65}),
                         (C.PASS, []))

    # Finding 5 (Astra): the preparation must refuse an existing graph whose output is not mode 3, verify the
    # configuration, and tell the Owner to Save As only after the in-session prepared comparison PASSES.
    def test_preparation_refuses_an_output_mode_1_graph(self):
        w = F.World()
        w.instance("krystal_target", with_scale_graph=True, graph_output_mode=1)
        w.instance("krystal_peer", muscles_key=0.5, legsize=0.25)
        idir, cfg, saved = self.prep_env(w)
        ctl = target(w)["flex"]["Legsize"][0]
        self.run_prep(idir, saved)
        out = self.outputs(cfg)
        self.assertIn("not intact", out["stop"]["stop"])
        self.assertIn("output mode 1", out["stop"]["stop"])
        self.assertEqual(ctl.attrs["value"], 0.4)
        self.assertNotIn("after", out)

    def test_preparation_refuses_a_configuration_that_is_not_the_deferred_one(self):
        w = F.twin_world()
        idir, cfg, saved = self.prep_env(w, config_name="m06w2_config.json")
        self.run_prep(idir, saved)
        out = self.outputs(cfg)
        self.assertIn("not the staged deferred configuration", out["stop"]["stop"])
        self.assertEqual(target(w)["flex"]["Legsize"][0].attrs["value"], 0.4)

    def test_save_as_is_offered_only_after_the_prepared_comparison_passes(self):
        w = F.twin_world()
        idir, cfg, saved = self.prep_env(w)
        finish = w.dm.FinishUndo

        def stray_finish():                      # an undeclared change inside the preparation's Undo entry
            w.set_flex(target(w), "Muscles", 0.5)
            finish()
        w.dm.FinishUndo = stray_finish
        shown = []
        sys.modules["PySide.QtGui"].QMessageBox.information = staticmethod(lambda *a: shown.append(a[2]))
        self.run_prep(idir, saved)
        out = self.outputs(cfg)
        self.assertIn("DO NOT SAVE", out["stop"]["stop"])
        self.assertNotIn("verdict", out)
        self.assertTrue(any("DO NOT SAVE" in m for m in shown) and not any("Save As" in m for m in shown), shown)
        w = F.twin_world()
        shutil.rmtree(self.dir, True)
        self.dir = tempfile.mkdtemp(prefix="m06w2_fix_")
        idir, cfg, saved = self.prep_env(w)
        shown = []
        sys.modules["PySide.QtGui"].QMessageBox.information = staticmethod(lambda *a: shown.append(a[2]))
        self.run_prep(idir, saved)
        out = self.outputs(cfg)
        self.assertEqual(out["verdict"]["verdict"], C.PASS)
        self.assertTrue(any("prepared comparison PASS" in m and "Save As" in m for m in shown), shown)

    def test_preparation_refuses_the_wrong_document_and_unsuitable_flex(self):
        for kw, why in (({"path_ok": False}, "not the configured disposable copy"),
                        ({"literal": "Muscles"}, "does not have the required"),
                        ({"stored": 0.4}, "not distinct")):
            w = F.twin_world()
            idir, cfg, saved = self.prep_env(w, **kw)
            before = dict((k, dict(v.attrs)) for k, v in target(w)["flex"].items() for v in [v[0]])
            self.run_prep(idir, saved)
            out = self.outputs(cfg)
            self.assertIn(why, out["stop"]["stop"])
            self.assertEqual(before, dict((k, dict(v.attrs)) for k, v in target(w)["flex"].items() for v in [v[0]]))
            shutil.rmtree(self.dir, True)
            self.dir = tempfile.mkdtemp(prefix="m06w2_fix_")


# ---------------------------------------------------------------------------
# Native prerequisite probes (run under fakes: shows the probe works and the acceptance logic, not native results)
# ---------------------------------------------------------------------------

class TestProbes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # One installed configuration for every probe, as natively (the before and after probes share it).
        cls.obs = tempfile.mkdtemp(prefix="m06w2_probe_obs_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.obs, True)

    def probe(self, w):
        d = tempfile.mkdtemp(prefix="m06w2_probe_")
        idir = os.path.join(d, "instruments")
        os.makedirs(idir)
        shutil.copy2(CORE, os.path.join(idir, "m06w2_core.py"))
        with io.open(os.path.join(idir, "m06w2_config.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(dict(F.CONFIG, observation_dir=self.obs)).encode("ascii").decode("ascii"))
        sfm, vs = w.modules()
        mods = {"sfmApp": types.ModuleType("sfmApp"), "vs": types.ModuleType("vs")}
        mods["sfmApp"].__dict__.update(dict((k, getattr(sfm, k)) for k in dir(sfm) if not k.startswith("_")))
        mods["vs"].g_pDataModel, mods["vs"].tier1 = vs.g_pDataModel, vs.tier1
        saved = dict((k, sys.modules.get(k)) for k in list(mods) + ["PySide"])
        sys.modules.update(mods)
        sys.modules["PySide"] = types.ModuleType("PySide")      # no QtGui: dialogs fall back to print
        path = os.path.join(ROOT, "native", "M06_Native_Probe.py")
        with open(path, "rb") as f:
            src = f.read().replace(b'u"<INSTRUMENT_DIR>"', ("u" + repr(idir).lstrip("u")).encode("utf-8"))
        out = sys.stdout
        sys.stdout = io.StringIO() if sys.version_info[0] > 2 else __import__("StringIO").StringIO()
        try:
            eval(compile(src, path, "exec"), {"__name__": "__main__"})
        finally:
            sys.stdout = out
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        names = [n for n in os.listdir(self.obs) if n.startswith("probe_")]
        self.assertEqual(len(names), 1)
        with io.open(os.path.join(self.obs, names[0]), encoding="utf-8") as f:
            result = json.load(f)
        os.remove(os.path.join(self.obs, names[0]))
        shutil.rmtree(d, True)
        return result

    def test_probe_records_identity_topology_presence_and_undo_forms(self):
        p = self.probe(F.twin_world())
        self.assertTrue(all(p["api"].values()))
        self.assertEqual(CP.identity_checks(p), [])
        self.assertEqual(CP.presence_checks(p), [])
        self.assertEqual(len(p["channels_clips"]), 2)
        self.assertEqual(p["undo_bindings"]["CanRedo"]["type"], "bool")

    def test_reload_acceptance(self):
        w = F.twin_world()
        same = CP.reload_result(self.probe(w), self.probe(w))
        self.assertEqual(same[0], [])                          # identical keys: the token would survive
        changed, _ = CP.reload_result(self.probe(F.twin_world()), self.probe(F.twin_world()))
        self.assertTrue(changed)
        w = F.twin_world()
        before = self.probe(w)
        w.file_id = 8                                          # only the document file id differs
        self.assertEqual(CP.reload_result(before, self.probe(w)), (["document_file_id"], []))

    def test_acceptance_fails_when_the_token_would_survive_reload(self):
        w = F.twin_world()
        d = tempfile.mkdtemp()
        try:
            pa, pb = os.path.join(d, "a.json"), os.path.join(d, "b.json")
            for path in (pa, pb):
                with io.open(path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(self.probe(w)).encode("ascii").decode("ascii"))
            out = sys.stdout
            sys.stdout = io.StringIO() if sys.version_info[0] > 2 else __import__("StringIO").StringIO()
            try:
                self.assertEqual(CP.main(["x", pa, pb]), 1)
                with io.open(pb, "w", encoding="utf-8") as f:
                    f.write(json.dumps(self.probe(F.twin_world())).encode("ascii").decode("ascii"))
                self.assertEqual(CP.main(["x", pa, pb]), 0)
            finally:
                sys.stdout = out
        finally:
            shutil.rmtree(d, True)

    def test_presence_disagreement_and_pointer_ids_fail_acceptance(self):
        w = F.twin_world()
        target(w)["flex"]["Legsize"][0].lying_presence.add("leftvaluechannel")
        self.assertTrue(CP.presence_checks(self.probe(w)))
        w = F.twin_world()
        w.document.uid = F.UniqueId("<Swig Object at 0x1>")
        self.assertTrue(CP.identity_checks(self.probe(w)))

    # Finding 4 (Astra): PROBE ACCEPTANCE passed when GetFileId() became unreadable, and peer-only changes counted.
    def test_probe_records_the_selected_instance_token(self):
        p = self.probe(F.twin_world())
        t = p["selected_token"]
        self.assertTrue(t["complete"])
        self.assertEqual(t["target_animset"], "krystal_target")
        self.assertEqual(t["animset_key"]["v"]["name"], "krystal_target")
        self.assertEqual(t["document_file_id"], {"s": "present", "v": 7})
        self.assertEqual(CP.token_problems(p, "p"), [])

    def test_unreadable_file_id_is_not_invalidation(self):
        before = self.probe(F.twin_world())
        w = F.twin_world()

        def broken():
            raise RuntimeError("GetFileId unreadable (fake)")
        w.shot.GetFileId = broken
        after = self.probe(w)
        self.assertEqual(after["selected_token"]["document_file_id"]["s"], "unreadable")
        changed, problems = CP.reload_result(before, after)
        self.assertEqual(changed, [])
        self.assertTrue(any("document_file_id unreadable" in x for x in problems), problems)
        self.assertEqual(self.accept(before, after), 1)
        w.shot.GetFileId = lambda: True                        # a boolean is not a file id
        self.assertTrue(CP.reload_result(before, self.probe(w))[1])

    def test_peer_only_change_is_not_invalidation(self):
        w = F.twin_world()
        before = self.probe(w)
        p = peer(w)
        sets = w.shot.attrs["animationSets"]
        sets[sets.index(p["animset"])] = F.El(w, "DmeAnimationSet", "krystal_peer", **p["animset"].attrs)
        after = self.probe(w)
        changed, problems = CP.reload_result(before, after)
        self.assertEqual((changed, problems), ([], []))
        self.assertEqual(self.accept(before, after), 1)
        self.assertEqual(self.accept(before, self.probe(F.twin_world())), 0)

    def test_presence_coverage_must_be_complete_and_nonempty(self):
        p = self.probe(F.twin_world())
        self.assertEqual(CP.presence_checks(p), [])
        empty = dict(p, has_get_agreement={}, controls_examined=0)
        self.assertTrue(CP.presence_checks(empty))
        partial = copy.deepcopy(p)
        k = sorted(partial["has_get_agreement"])[0]
        partial["has_get_agreement"][k] -= 1
        self.assertTrue(any("incomplete coverage" in x for x in CP.presence_checks(partial)))
        legacy = dict(p)
        del legacy["controls_examined"]
        self.assertTrue(CP.presence_checks(legacy))

    def accept(self, before, after):
        d = tempfile.mkdtemp()
        try:
            pa, pb = os.path.join(d, "a.json"), os.path.join(d, "b.json")
            for path, p in ((pa, before), (pb, after)):
                with io.open(path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(p).encode("ascii").decode("ascii"))
            out = sys.stdout
            sys.stdout = io.StringIO() if sys.version_info[0] > 2 else __import__("StringIO").StringIO()
            try:
                return CP.main(["x", pa, pb])
            finally:
                sys.stdout = out
        finally:
            shutil.rmtree(d, True)


class TestStaging(unittest.TestCase):
    def test_stage_substitutes_install_dir_refuses_placeholders_and_wrong_pin(self):
        import stage_instruments as ST
        d = tempfile.mkdtemp(prefix="m06w2_stage_")
        try:
            with io.open(os.path.join(ROOT, "config", "m06w2_config.template.json"), encoding="utf-8") as f:
                cfg = json.load(f)
            tpl = os.path.join(d, "tpl.json")
            with io.open(tpl, "w", encoding="utf-8") as f:
                f.write(json.dumps(cfg).encode("ascii").decode("ascii"))
            self.assertRaises(SystemExit, ST.stage, tpl, os.path.join(d, "out0"))     # placeholders remain
            filled = json.loads(json.dumps(cfg).replace("<SFM game>", "G:/SFM").replace("<QUAL_DIR>", "G:/Q")
                                .replace("<protected original session>", "G:/orig.dmx").replace("<sha256>", "0" * 64))
            good = os.path.join(d, "good.json")
            with io.open(good, "w", encoding="utf-8") as f:
                f.write(json.dumps(filled).encode("ascii").decode("ascii"))
            out = ST.stage(good, os.path.join(d, "out"))
            with open(os.path.join(out, "M06_Qualification_Observer.py"), "rb") as f:
                src = f.read()
            self.assertNotIn(b"<INSTRUMENT_DIR>", src)
            compile(src, "staged", "exec")
            self.assertIn(b"M06 Qualification", src)
            with io.open(os.path.join(out, "m06w2_config.json"), encoding="utf-8") as f:
                self.assertEqual(sorted(json.load(f)["instrument_files"]),
                                 sorted([n for _, n in ST.FILES] + ["M06_Qualification_Observer.py"]))
            self.assertTrue(os.path.isfile(os.path.join(out, "STAGED_SHA256SUMS.txt")))
            self.assertRaises(SystemExit, ST.stage, good, out)                         # never reuse
            wrong = dict(filled, cpm=dict(filled["cpm"], sha256="d2bd6fd6" + "0" * 56))
            with io.open(good, "w", encoding="utf-8") as f:
                f.write(json.dumps(wrong).encode("ascii").decode("ascii"))
            self.assertRaises(SystemExit, ST.stage, good, os.path.join(d, "out2"))
        finally:
            shutil.rmtree(d, True)


class TestConfigSelection(unittest.TestCase):
    """Finding 5 (Astra): preparation used m06w2_deferred_config.json (shot10) while the only Observer loaded
    m06w2_config.json (shot12). One explicit mechanism now: one staged Observer per configuration."""

    def filled(self, d, template, name):
        with io.open(os.path.join(ROOT, "config", template), encoding="utf-8") as f:
            text = f.read()
        for a, b in (("<SFM game>", "G:/SFM"), ("<QUAL_DIR>", "G:/Q"), ("<protected original session>", "G:/o.dmx"),
                     ("<protected M-05 fixture>", "G:/m05.dmx"), ("<sha256>", "0" * 64)):
            text = text.replace(a, b)
        path = os.path.join(d, name)
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def run_observer(self, staged, name, w, out_dir):
        """Run a staged Observer under fakes from the staging folder (INSTRUMENT_DIR re-pointed there; each staged
        configuration keeps its config_name, with the fake scene's declared scope)."""
        for cname in ("m06w2_config.json", "m06w2_deferred_config.json"):
            p = os.path.join(staged, cname)
            with io.open(p, encoding="utf-8") as f:
                cfg = json.load(f)
            cfg.update(observation_dir=out_dir, cpm=F.CONFIG["cpm"], shot="shot12", target_animset="krystal_target",
                       peers=["krystal_peer"], body=F.CONFIG["body"], nonbody=F.CONFIG["nonbody"], protected={},
                       watch_path=None, instrument_files={})
            with io.open(p, "w", encoding="utf-8") as f:
                f.write(json.dumps(cfg).encode("ascii").decode("ascii"))
        path = os.path.join(staged, name)
        with open(path, "rb") as f:
            src = f.read()
        src = re.sub(b'INSTRUMENT_DIR = u"[^"\n]*"', b"INSTRUMENT_DIR = u" + repr(staged).lstrip("u").encode("utf-8")
                     .replace(b"\\", b"\\\\"), src)
        sfm, vs = w.modules()
        mods = {"sfmApp": types.ModuleType("sfmApp"), "vs": types.ModuleType("vs"), "PySide": types.ModuleType("PySide")}
        mods["sfmApp"].__dict__.update(dict((k, getattr(sfm, k)) for k in dir(sfm) if not k.startswith("_")))
        mods["vs"].g_pDataModel, mods["vs"].tier1 = vs.g_pDataModel, vs.tier1
        saved = dict((k, sys.modules.get(k)) for k in list(mods) + ["PySide.QtGui"])
        sys.modules.update(mods)
        sys.modules.pop("PySide.QtGui", None)
        out = sys.stdout
        sys.stdout = io.StringIO() if sys.version_info[0] > 2 else __import__("StringIO").StringIO()
        try:
            eval(compile(src, path, "exec"), {"__name__": "__main__"})
        finally:
            sys.stdout = out
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        names = sorted(n for n in os.listdir(out_dir) if n.startswith("obs_"))
        with io.open(os.path.join(out_dir, names[-1]), encoding="utf-8") as f:
            return json.load(f)

    def test_one_staged_observer_per_configuration(self):
        import stage_instruments as ST
        d = tempfile.mkdtemp(prefix="m06w2_sel_")
        try:
            main = self.filled(d, "m06w2_config.template.json", "main.json")
            deferred = self.filled(d, "m06w2_deferred_config.template.json", "deferred.json")
            out = ST.stage(main, os.path.join(d, "out"), deferred)
            names = sorted(os.listdir(out))
            for n in ("M06_Qualification_Observer.py", "M06_Deferred_Observer.py", "compare_obs.py",
                      "m06w2_config.json", "m06w2_deferred_config.json"):
                self.assertIn(n, names)
            for obs_name, cfg_name, shot in (("M06_Qualification_Observer.py", "m06w2_config.json", "shot12"),
                                              ("M06_Deferred_Observer.py", "m06w2_deferred_config.json", "shot10")):
                with open(os.path.join(out, obs_name), "rb") as f:
                    src = f.read()
                self.assertIn(('CONFIG_NAME = u"%s"' % cfg_name).encode("ascii"), src)
                self.assertNotIn(b"<CONFIG_NAME>", src)
                self.assertNotIn(b"<INSTRUMENT_DIR>", src)
                compile(src, obs_name, "exec")
                with io.open(os.path.join(out, cfg_name), encoding="utf-8") as f:
                    cfg = json.load(f)
                self.assertEqual((cfg["config_name"], cfg["shot"]), (cfg_name, shot))
                self.assertIn(obs_name, cfg["instrument_files"])
                self.assertIn("compare_obs.py", cfg["instrument_files"])
            only = ST.stage(main, os.path.join(d, "out_main"))
            self.assertNotIn("M06_Deferred_Observer.py", os.listdir(only))
        finally:
            shutil.rmtree(d, True)

    def test_each_staged_observer_reads_and_records_its_own_configuration(self):
        import stage_instruments as ST
        d = tempfile.mkdtemp(prefix="m06w2_sel_")
        try:
            main = self.filled(d, "m06w2_config.template.json", "main.json")
            deferred = self.filled(d, "m06w2_deferred_config.template.json", "deferred.json")
            out = ST.stage(main, os.path.join(d, "out"), deferred)
            obs_dir = os.path.join(d, "obs")
            for obs_name, cfg_name in (("M06_Qualification_Observer.py", "m06w2_config.json"),
                                       ("M06_Deferred_Observer.py", "m06w2_deferred_config.json")):
                rec = self.run_observer(out, obs_name, F.twin_world(), obs_dir)
                self.assertEqual(rec["config_name"], cfg_name)
                self.assertTrue(rec["complete"], rec["insufficient"][:4])
            # A configuration whose recorded name is not this Observer's configuration refuses.
            p = os.path.join(out, "m06w2_deferred_config.json")
            with io.open(p, encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["config_name"] = "m06w2_config.json"
            with io.open(p, "w", encoding="utf-8") as f:
                f.write(json.dumps(cfg).encode("ascii").decode("ascii"))
            rec = self.run_observer(out, "M06_Deferred_Observer.py", F.twin_world(), obs_dir)
            self.assertFalse(rec["complete"])
            self.assertTrue(any("not the staged configuration" in r for r in rec["insufficient"]), rec["insufficient"])
        finally:
            shutil.rmtree(d, True)

    def test_unstaged_observer_holds_the_placeholder(self):
        with open(os.path.join(ROOT, "instruments", "M06_Qualification_Observer.py"), "rb") as f:
            self.assertIn(b'CONFIG_NAME = u"<CONFIG_NAME>"', f.read())


class TestScriptsCompile(unittest.TestCase):
    def test_every_instrument_and_native_script_compiles_under_this_interpreter(self):
        """SFM's Python 2.7.5 rejects an unqualified exec inside a function with nested free-variable functions;
        every script loads the core with eval(compile(...)) instead. Compiling each one here proves its syntax."""
        for folder in ("instruments", "native", "tools"):
            for name in sorted(os.listdir(os.path.join(ROOT, folder))):
                if name.endswith(".py"):
                    path = os.path.join(ROOT, folder, name)
                    with open(path, "rb") as f:
                        compile(f.read(), path, "exec")
                    with io.open(path, encoding="utf-8") as f:
                        self.assertNotIn("exec(compile(", f.read(), name)


class TestW1Preserved(unittest.TestCase):
    def test_accepted_w1_application_is_byte_identical(self):
        with open(W1_APP, "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(), W1_SHA256)


CASES = (TestObserver, TestComparator, TestInjector, TestDeferredFixture, TestProbes, TestStaging,
         TestConfigSelection, TestFinding1ObserverCompleteness, TestFinding2ApplyPreservesUndeclaredState,
         TestFinding3AbortAndGraphRemoval, TestFinding6PresetEmptyLog, TestR1CompressedData,
         TestR2AScaleEmptyOutputLog, TestR2BEmptyToOneKeyApply, TestR3AbortConfigurationHandoff, TestR4ConfigDigest,
         TestScriptsCompile,
         TestW1Preserved)


def main(results=None):
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for case in CASES:
        suite.addTests(loader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if results:
        with io.open(results, "w", encoding="utf-8") as f:
            f.write(json.dumps({"python": sys.version, "tests": result.testsRun, "failures": len(result.failures),
                                "errors": len(result.errors), "skipped": len(result.skipped),
                                "native_execution": False}, indent=1).encode("ascii").decode("ascii"))
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1] if len(sys.argv) > 1 else None) else 1)
