# -*- coding: ascii -*-
"""Offline tests of the F-01 model compatibility survey: the wrapper observer against the S0 kit's fake SFM
(Python 2.7 and 3) and the refusal-map probe (Python 3). Run: python -I test_mc.py  (SFM's Python 2.7:
python -E -s test_mc.py)."""
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(ROOT, "..", ".."))
WRAPPER = os.path.join(ROOT, "observer", "F01_MC_Observe.py")
S0_OBSERVER = os.path.join(REPO, "real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")
KRYSTAL_S0 = os.environ.get("F01_KRYSTAL_S0_OBSERVATIONS", r"E:\SFM_U0B_Scratch\f01-full-body-s0-r2\observations")
sys.path.insert(0, os.path.join(REPO, "real_sfm_qualification", "f01_full_body_s0", "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fake_sfm_s0 as F  # noqa: E402

PY3 = sys.version_info[0] >= 3


class Sink(object):
    def write(self, data):
        if not isinstance(data, bytes):
            raise TypeError("the observer printed a non-byte string on Python 2")


def no_rig(world, S):
    scene = S["shot"].attrs["scene"]
    scene.attrs["children"].items[:] = [c for c in scene.attrs["children"].items if c.kind != "DmeRig"]


def native_parenting(world, S):
    """As natively recorded for Krystal: rig_root is a child of the DmeRig element (the fake puts it in the scene)."""
    scene = S["shot"].attrs["scene"]
    root = S["handles"]["rig_root"]
    scene.attrs["children"].items.remove(root)
    [c for c in scene.attrs["children"].items if c.kind == "DmeRig"][0].add(root)


def groups_and_flex(world, S):
    smile = [c for c in S["animset"].attrs["controls"].items if c.name == "smile"][0]
    face = F.El(world, "DmeControlGroup", "Face", controls=F.Array(world, [smile]), children=F.Array(world, []),
                visible=True)
    body = F.El(world, "DmeControlGroup", "Body", controls=F.Array(world, [S["ear_control"]]),
                children=F.Array(world, []))
    S["animset"].attrs["rootControlGroup"] = F.El(world, "DmeControlGroup", "rootGroup", controls=F.Array(world, []),
                                                  children=F.Array(world, [body, face]))
    gm = S["animset"].attrs["gameModel"]
    gm.attrs["globalFlexControllers"] = F.Array(world, [F.El(world, "DmeGlobalFlexControllerOperator", "smile",
                                                             flexWeight=0.25)])


def connection(world, S):
    groups_and_flex(world, S)
    ref_in = F.El(world, "DmeAttributeReference", "in", element=S["ear_control"], attribute="value")
    ref_out = F.El(world, "DmeAttributeReference", "out", element=S["bones"]["bip_toe_l"], attribute="footRoll")
    S["animset"].attrs["operators"].items.append(F.El(world, "DmeConnectionOperator", "footRoll_conn", input=ref_in,
                                                      outputs=F.Array(world, [ref_out])))


def run(folder, label, animset="Krystal", before=None, repo=REPO):
    world, S, sfm, vs = F.install()
    if before:
        before(world, S)
    sys.modules["sfmApp"], sys.modules["vs"] = sfm, vs
    g = {"__name__": "__mc__", "MC_DIR": folder, "MC_REPO": repo, "MC_LABEL": label, "MC_ANIMSET": animset}
    with io.open(WRAPPER, "rb") as f:
        code = compile(f.read(), WRAPPER, "exec")
    saved = sys.stdout
    sys.stdout = io.StringIO() if PY3 else Sink()
    try:
        exec(code, g)
    finally:
        printed = sys.stdout.getvalue() if PY3 else None
        sys.stdout = saved
    with io.open(os.path.join(folder, "observations", label + ".json"), "rb") as f:
        return world, json.loads(f.read().decode("utf-8")), printed


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="mctest")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def files(self):
        return sorted(os.listdir(os.path.join(self.dir, "observations")))


class WrapperTests(Base):
    def test_the_s0_observer_is_the_pinned_one(self):
        with io.open(S0_OBSERVER, "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(),
                             "4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4")

    def test_rigged_observation_is_s0_plus_extension_and_readonly(self):
        world, obs, printed = run(self.dir, "MC-01", before=groups_and_flex)
        self.assertEqual(world.mutations, [])
        self.assertEqual((obs["format"], obs["s0_format"]), ("F01-MC-survey-v1", "F01-S0-survey-v1"))
        self.assertEqual((obs["problems"], obs["findings"]), ([], []))
        self.assertTrue(obs["readonly"]["unchanged"])
        self.assertEqual(len(obs["bones"]), 11)
        self.assertEqual(obs["animation_sets_in_shot"], ["Krystal"])
        paths = [g["path"] for g in obs["mc"]["control_groups"]]
        self.assertEqual(paths, [["rootGroup"], ["rootGroup", "Body"], ["rootGroup", "Face"]])
        face = obs["mc"]["control_groups"][2]
        self.assertEqual([c["name"] for c in face["controls"]], ["smile"])
        self.assertEqual([f["id"]["name"] for f in obs["mc"]["flex_controllers"]], ["smile"])
        self.assertIn("modelName", obs["mc"]["game_model_attributes"])
        self.assertNotIn("bones", obs["mc"]["game_model_attributes"])
        if PY3:
            self.assertIn("MC MC-01: OK", printed)

    def test_a_model_without_a_rig_is_a_finding_not_a_problem(self):
        world, obs, _ = run(self.dir, "MC-02", before=no_rig)
        self.assertEqual(world.mutations, [])
        self.assertEqual(obs["problems"], [])
        self.assertEqual(len(obs["findings"]), 1)
        self.assertTrue(obs["findings"][0].startswith("expected one rig registration"))
        self.assertEqual(obs["rig"]["registrations"], [])
        self.assertIsNone(obs["mc"]["control_groups"])

    def test_connection_operator_references_are_dumped(self):
        world, obs, _ = run(self.dir, "MC-03", before=connection)
        self.assertEqual(world.mutations, [])
        links = [v for v in obs["mc"]["operator_links"].values() if v["id"]["type"] == "DmeConnectionOperator"]
        self.assertEqual(len(links), 1)
        out = links[0]["linked"]["outputs"][0]["attributes"]
        self.assertEqual(out["attribute"]["value"], "footRoll")
        self.assertEqual(out["element"]["value"]["name"], "bip_toe_l")
        self.assertIn("input", links[0]["linked"])
        kinds = set(v["id"]["type"] for v in obs["mc"]["operator_links"].values())
        self.assertNotIn("DmeRigIKConstraintOperator", kinds)
        self.assertIn("DmeRigWingOperator", kinds)

    def test_refusals_write_nothing(self):
        with self.assertRaises(RuntimeError):
            run(self.dir, "MC-01", animset="heavy")
        with self.assertRaises(RuntimeError):
            run(self.dir, "S0-01")
        self.assertEqual(self.files(), [])
        run(self.dir, "MC-01")
        with self.assertRaises(RuntimeError):
            run(self.dir, "MC-01")
        self.assertEqual(self.files(), ["MC-01.json"])

    def test_a_changed_s0_observer_refuses(self):
        fake_repo = tempfile.mkdtemp(prefix="mcrepo")
        try:
            target = os.path.join(fake_repo, "real_sfm_qualification", "f01_full_body_s0", "observer")
            os.makedirs(target)
            with io.open(S0_OBSERVER, "rb") as f:
                raw = f.read()
            with io.open(os.path.join(target, "F01_S0_Survey.py"), "wb") as f:
                f.write(raw.replace(b"MAX_NODES = 20000", b"MAX_NODES = 20001"))
            with self.assertRaises(RuntimeError):
                run(self.dir, "MC-01", repo=fake_repo)
            self.assertEqual(self.files(), [])
        finally:
            shutil.rmtree(fake_repo)


if PY3:
    import mc_probe as P  # noqa: E402

    class ProbeTests(Base):
        @classmethod
        def setUpClass(cls):
            cls.ns, cls.arm, cls.cpm = P.cpm_namespace()

        def probe(self, label, before):
            run(self.dir, label, before=before)
            path = os.path.join(self.dir, "observations", label + ".json")
            with io.open(path, "rb") as f:
                raw = f.read()
            return P.probe_one(self.ns, self.arm, raw, json.loads(raw.decode("utf-8")))

        def test_unknown_operator_refuses_and_no_rig_refuses_as_rig_differs(self):
            r = self.probe("MC-00", groups_and_flex)
            self.assertEqual(r["classify_draft"]["result"], "NOT-EXPRESSIBLE")
            self.assertIn("rig_root", r["classify_draft"]["detail"])
            r = self.probe("MC-01", lambda w, S: (native_parenting(w, S), groups_and_flex(w, S)))
            self.assertEqual(r["classify_draft"]["result"], "REFUSED")
            self.assertEqual(r["classify_draft"]["code"], "structure-unsupported")
            self.assertIn("DmeRigWingOperator", r["classify_draft"]["detail"])
            self.assertIn("DmeRigWingOperator", r["census"]["operator_types"])
            self.assertEqual(r["census"]["face_risk_by_group"], [])
            self.assertEqual(r["draft_profile"]["placement_handle"], "rig_root")
            self.assertEqual(r["draft_profile"]["helper_handles"], [])
            r = self.probe("MC-02", no_rig)
            self.assertEqual((r["classify_draft"]["result"], r["classify_draft"]["code"]), ("REFUSED", "rig-differs"))
            self.assertEqual(r["rigs"], [])
            self.assertEqual(r["counts"]["handles"], 0)

        def test_connection_outputs_are_resolved_to_their_elements(self):
            r = self.probe("MC-03", connection)
            refs = [l for l in r["census"]["operator_links"] if l["type"] == "DmeConnectionOperator"][0]["references"]
            self.assertIn({"slot": "outputs", "element": "DmeDag:bone:bip_toe_l", "attribute": "footRoll"}, refs)

        def test_the_whole_command_writes_both_reports_once(self):
            run(self.dir, "MC-01", before=groups_and_flex)
            out = os.path.join(self.dir, "evidence")
            os.makedirs(out)
            saved = sys.stdout
            sys.stdout = io.StringIO()
            try:
                self.assertEqual(P.main(["mc_probe.py", os.path.join(self.dir, "observations"), out]), 0)
                with self.assertRaises(OSError):
                    P.main(["mc_probe.py", os.path.join(self.dir, "observations"), out])
            finally:
                sys.stdout = saved
            self.assertEqual(sorted(os.listdir(out)), ["MC_PROBE.json", "MC_PROBE.md"])

        @unittest.skipUnless(os.path.isdir(KRYSTAL_S0), "the Owner's Krystal S0 run 2 observations are local only")
        def test_krystal_s0_draft_equals_the_registry_profile_except_facial_preservation(self):
            path = os.path.join(KRYSTAL_S0, "S0-02.json")
            with io.open(path, "rb") as f:
                raw = f.read()
            r = P.probe_one(self.ns, self.arm, raw, json.loads(raw.decode("utf-8")))
            self.assertEqual(r["classify_draft"]["result"], "CLASSIFIED")
            self.assertEqual(r["classify_registry_profile"]["result"], "CLASSIFIED")
            self.assertEqual(sorted(r["draft_vs_registry"]), ["preserved_fk_bones"])
            self.assertEqual(r["classify_registry_profile"]["written"], 278)


if __name__ == "__main__":
    unittest.main(verbosity=1)
