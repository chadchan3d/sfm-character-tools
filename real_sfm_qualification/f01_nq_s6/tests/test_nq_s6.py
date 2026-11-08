# -*- coding: ascii -*-
"""Offline tests of the F-01 SFP-1 NQ-S6 observer against the S0 kit's fake SFM, with a fake studio header (Python
2.7 and 3). They show the observer is read-only, records every per-bone field and the source-less channel evidence,
and records unreadable reads instead of inferring them. They show nothing about SFM.
Run: python -I test_nq_s6.py   (SFM's Python 2.7: python -E -s test_nq_s6.py)"""
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(ROOT, "..", ".."))
OBSERVER = os.path.join(ROOT, "observer", "F01_NQS6_Observe.py")
sys.path.insert(0, os.path.join(REPO, "real_sfm_qualification", "f01_full_body_s0", "tests"))
import fake_sfm_s0 as F  # noqa: E402

PY3 = sys.version_info[0] >= 3
PROC = {"STUDIO_PROC_AXISINTERP": 1, "STUDIO_PROC_QUATINTERP": 2, "STUDIO_PROC_AIMATBONE": 3,
        "STUDIO_PROC_AIMATATTACH": 4, "STUDIO_PROC_JIGGLE": 5, "STUDIO_PROC_TWIST_MASTER": 6,
        "STUDIO_PROC_TWIST_SLAVE": 7, "STUDIO_PROC_POINT_CONSTRAINT": 8, "STUDIO_PROC_ORIENT_CONSTRAINT": 9,
        "STUDIO_PROC_AIM_CONSTRAINT": 10, "BONE_CALCULATE_MASK": 0x1f, "BONE_PHYSICALLY_SIMULATED": 0x01,
        "BONE_PHYSICS_PROCEDURAL": 0x02, "BONE_ALWAYS_PROCEDURAL": 0x04, "BONE_SCREEN_ALIGN_SPHERE": 0x08,
        "BONE_SCREEN_ALIGN_CYLINDER": 0x10, "BONE_USED_MASK": 0x0007ff00, "BONE_USED_BY_ANYTHING": 0x0007ff00}


class Sink(object):
    def write(self, data):
        if not isinstance(data, bytes):
            raise TypeError("the observer printed a non-byte string on Python 2")


class Bone(object):
    def __init__(self, name, parent, proctype=0, flags=0x100):
        self.name, self.parent, self.proctype, self.flags = name, parent, proctype, flags
        self.procindex, self.physicsbone, self.contents = (7 if proctype else 0), -1, 1

    def pszName(self):
        return self.name


class Header(object):
    def __init__(self, bones, broken=None):
        self.bones, self.numbones, self.checksum, self.broken = bones, len(bones), 1234, broken

    def pBone(self, i):
        if self.broken == i:
            raise RuntimeError("pBone failed (test)")
        return self.bones[i]


def studio_model(world, S, procedural=("bip_shin_twist_l",), broken=None, header=True):
    gm = [c for c in S["shot"].attrs["scene"].attrs["children"].items if c.kind == "DmeGameModel"][0]
    names = [t.name.split("(")[1][:-1] for t in gm.attrs["bones"].items]
    bones = [Bone(n, -1, proctype=2 if n in procedural else 0) for n in names]
    calls = []
    gm.GetStudioHdr = lambda: calls.append("GetStudioHdr") or (Header(bones, broken) if header else None)
    gm.ShouldEvaluateProceduralBones = lambda: calls.append("Should") or True
    gm.attrs["evaluateProceduralBones"] = True

    def default_position(i, v):
        v.x, v.y, v.z = 1.0, 2.0, 3.0
        return True
    gm.GetBoneDefaultPosition = default_position
    gm.GetBoneDefaultOrientation = lambda i, q: False
    for name in ("SetEvaluateProceduralBones", "SetBone", "AddBone", "RemoveAllBones", "SetFlags"):
        setattr(gm, name, (lambda n: lambda *a: world.mutations.append(("gm." + n, a)))(name))
    return gm, calls


def run(folder, label, animset="Krystal", **kw):
    world, S, sfm, vs = F.install()
    gm, calls = studio_model(world, S, **kw)
    vs.Vector, vs.Quaternion = F.Vector, F.Quaternion
    studio = types.ModuleType("vs.studio")
    for k, v in PROC.items():
        setattr(studio, k, v)
    vs.studio = studio
    sys.modules["sfmApp"], sys.modules["vs"], sys.modules["vs.studio"] = sfm, vs, studio
    g = {"__name__": "__nq__", "NQ_DIR": folder, "NQ_REPO": REPO, "NQ_LABEL": label, "NQ_ANIMSET": animset}
    with io.open(OBSERVER, "rb") as f:
        code = compile(f.read(), OBSERVER, "exec")
    saved = sys.stdout
    sys.stdout = io.StringIO() if PY3 else Sink()
    try:
        exec(code, g)
    finally:
        printed = sys.stdout.getvalue() if PY3 else None
        sys.stdout = saved
    with io.open(os.path.join(folder, "observations", label + ".json"), "rb") as f:
        return world, json.loads(f.read().decode("utf-8")), printed, calls


class Tests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nqtest")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_reads_per_bone_procedural_declarations_read_only(self):
        world, obs, printed, calls = run(self.dir, "NQ-01")
        self.assertEqual(world.mutations, [])
        self.assertTrue(obs["readonly"]["unchanged"])
        self.assertEqual(obs["problems"], [])
        nq = obs["nq"]
        self.assertEqual(nq["should_evaluate_procedural_bones"], {"status": "READ", "value": True})
        self.assertEqual(nq["evaluateProceduralBones_attribute"]["value"], True)
        st = nq["studio"]
        self.assertEqual(st["header"]["numbones"]["value"], len(st["bones"]))
        self.assertEqual(st["constants"]["STUDIO_PROC_QUATINTERP"], {"status": "READ", "value": 2})
        twist = [b for b in st["bones"] if b["name"]["value"] == "bip_shin_twist_l"][0]
        self.assertEqual((twist["proctype"]["value"], twist["procindex"]["value"]), (2, 7))
        self.assertEqual(twist["default_position"]["value"], {"ok": True, "value": [1.0, 2.0, 3.0]})
        self.assertEqual(twist["default_orientation"]["value"]["ok"], False)
        self.assertIn("GetStudioHdr", calls)
        if PY3:
            self.assertIn("NQ NQ-01: OK", printed)
            self.assertIn("proctype_nonzero=1 ['bip_shin_twist_l']", printed)

    def test_records_source_less_channel_defaults_and_out_of_range_samples(self):
        world, obs, _, _ = run(self.dir, "NQ-02")
        rows = [r for r in obs["nq"]["source_less_channels"] if r["bone_transform"].endswith("(bip_shin_twist_l)")]
        self.assertEqual(sorted(r["channel"] for r in rows), ["bip_shin_twist_l_o", "bip_shin_twist_l_p"])
        o = [r for r in rows if r["channel"].endswith("_o")][0]
        self.assertEqual((o["key_count"], o["key_range"], o["layers"]), (20, [0, 9500], 1))
        self.assertEqual(o["fields"]["usedefaultvalue"]["value"], False)
        self.assertEqual(sorted(o["samples"]), ["below", "current", "current*10", "far", "first", "last",
                                                "last+1"])
        self.assertEqual(o["samples"]["far"]["ticks"], 100000000)
        self.assertEqual(o["has_default"]["status"], "UNREADABLE")      # the fake log has no HasDefaultValue

    def test_unreadable_bone_and_missing_header_are_recorded_not_inferred(self):
        world, obs, printed, _ = run(self.dir, "NQ-03", broken=0)
        first = obs["nq"]["studio"]["bones"][0]
        self.assertIn("unreadable", first)
        if PY3:
            self.assertIn("unreadable_bone_rows=1", printed)
        world, obs, _, _ = run(self.dir, "NQ-04", header=False)
        self.assertEqual(obs["nq"]["studio"]["header"]["status"], "UNREADABLE")
        self.assertEqual(obs["nq"]["studio"]["bones"], [])

    def test_refuses_without_writing(self):
        run(self.dir, "NQ-05")
        with self.assertRaises(RuntimeError):
            run(self.dir, "NQ-05")                          # never replaced
        with self.assertRaises(RuntimeError):
            run(self.dir, "MC-01")                          # wrong label form
        with self.assertRaises(RuntimeError):
            run(self.dir, "NQ-06", animset="nobody")
        self.assertEqual(sorted(os.listdir(os.path.join(self.dir, "observations"))), ["NQ-05.json"])

    def test_analysis_separates_declared_procedural_from_undeclared_control_less_bones(self):
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import nq_analyze as A
        _, obs, _, _ = run(self.dir, "NQ-07")
        r = A.analyze(obs)
        self.assertEqual(r["control_less"]["bip_shin_twist_l"]["class"], "declared-procedural")
        self.assertEqual(r["control_less"]["bip_shin_twist_l"]["proc"], "STUDIO_PROC_QUATINTERP")
        self.assertEqual(r["join_problems"], [])
        _, obs, _, _ = run(self.dir, "NQ-08", procedural=())
        self.assertEqual(A.analyze(obs)["control_less"]["bip_shin_twist_l"]["class"], "no-declaration")
        _, obs, _, _ = run(self.dir, "NQ-09", broken=10)
        self.assertEqual(A.analyze(obs)["control_less"]["bip_shin_twist_l"]["class"], "unreadable")

    def test_the_s0_observer_is_the_pinned_one(self):
        path = os.path.join(REPO, "real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")
        with io.open(path, "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(),
                             "4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4")

    def test_observer_calls_no_mutating_api(self):
        with io.open(OBSERVER, "rb") as f:
            text = f.read().decode("ascii")
        for name in ("SetEvaluateProceduralBones", "SetKeyValue", "InsertKeyAtTime", "SetHeadTimeInSeconds",
                     "StartUndo", "SetValue(", "SaveDocument", "SetBone", "RemoveAllBones", "SetFlags"):
            self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
