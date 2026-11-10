# -*- coding: ascii -*-
"""Offline tests of the F-01 EC-1 kit (Python 2.7 and 3 for the observer; Python 3 for the analysis and the tool).

- The observer composes the three pinned observers against the S0 kit's fake SFM with a fake studio header: read-only,
  every extension recorded, and it refuses (writing nothing) on a wrong label, an existing file, a wrong animation
  set, a model other than the Engineer, or any pinned observer whose bytes differ.
- The analysis, on the committed real Heavy structure (fixtures/f01_scoped/mc01_heavy_norig.json, from native MC-01):
  the two control-less helpers make it NOT-CANDIDATE through both the census and CPM's engine; the same skeleton with
  a direct control on each helper passes every structural criterion, including CPM's Full body compile, Save and an
  Apply to a changed copy; a nonzero or unreadable endpoint index, a constraint, a rig registration and a control
  driving two bones each fail their criterion; identity checks against the pinned Engineer header.
- The tool: the kit pins in the template equal the files; the model identity check follows the search order and the
  pin.
They show nothing about SFM.
Run: python -I test_ec1.py   (SFM's Python 2.7: python -E -s test_ec1.py)"""
import copy
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
OBSERVER = os.path.join(ROOT, "observer", "F01_EC1_Observe.py")
sys.path.insert(0, os.path.join(REPO, "real_sfm_qualification", "f01_full_body_s0", "tests"))
sys.path.insert(0, os.path.join(REPO, "real_sfm_qualification", "f01_nq_s6", "tests"))
import fake_sfm_s0 as F  # noqa: E402
import test_nq_s6 as NQT  # noqa: E402  (its fake studio header)

PY3 = sys.version_info[0] >= 3
ENGINEER = "models/player/engineer.mdl"
PINNED_FILES = (("real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py"),
                ("real_sfm_qualification", "f01_model_survey", "observer", "F01_MC_Observe.py"),
                ("real_sfm_qualification", "f01_nq_s6", "observer", "F01_NQS6_Observe.py"))


def run(folder, label, animset="Krystal", model=ENGINEER, repo=REPO):
    world, S, sfm, vs = F.install()
    gm, calls = NQT.studio_model(world, S)
    if model is not None:
        gm.attrs["modelName"] = model
    vs.Vector, vs.Quaternion = F.Vector, F.Quaternion
    import types
    studio = types.ModuleType("vs.studio")
    for k, v in NQT.PROC.items():
        setattr(studio, k, v)
    vs.studio = studio
    sys.modules["sfmApp"], sys.modules["vs"], sys.modules["vs.studio"] = sfm, vs, studio
    g = {"__name__": "__ec1__", "EC_DIR": folder, "EC_REPO": repo, "EC_LABEL": label, "EC_ANIMSET": animset}
    with io.open(OBSERVER, "rb") as f:
        code = compile(f.read(), OBSERVER, "exec")
    saved = sys.stdout
    sys.stdout = io.StringIO() if PY3 else NQT.Sink()
    try:
        exec(code, g)
    finally:
        printed = sys.stdout.getvalue() if PY3 else None
        sys.stdout = saved
    with io.open(os.path.join(folder, "observations", label + ".json"), "rb") as f:
        return world, json.loads(f.read().decode("utf-8")), printed


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ec1test")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_composes_the_three_pinned_observers_read_only(self):
        world, obs, printed = run(self.dir, "EC1-01")
        self.assertEqual(world.mutations, [])
        self.assertTrue(obs["readonly"]["unchanged"])
        self.assertEqual(obs["problems"], [])
        self.assertEqual(obs["format"], "F01-EC1-observation-v1")
        self.assertEqual(sorted(obs["observers"]), ["mc", "nq", "s0"])
        self.assertEqual(obs["expected_model"], ENGINEER)
        self.assertIn("control_groups", obs["mc"])
        self.assertIn("flex_controllers", obs["mc"])
        self.assertEqual(obs["nq"]["studio"]["header"]["numbones"]["value"], len(obs["nq"]["studio"]["bones"]))
        self.assertEqual(len(obs["bones"]), len(obs["nq"]["studio"]["bones"]))
        self.assertTrue(all("fromIndex" in c["binding"] and "toIndex" in c["binding"] for c in obs["channels"]))
        if PY3:
            self.assertIn("EC1 EC1-01: OK", printed)

    def test_refuses_without_writing(self):
        run(self.dir, "EC1-02")
        for kw in ({"label": "EC1-02"}, {"label": "MC-01"}, {"label": "EC1-03", "animset": "nobody"},
                   {"label": "EC1-04", "model": None}, {"label": "EC1-05", "model": "models/player/heavy.mdl"}):
            label = kw.pop("label")
            with self.assertRaises(RuntimeError):
                run(self.dir, label, **kw)
        self.assertEqual(sorted(os.listdir(os.path.join(self.dir, "observations"))), ["EC1-02.json"])

    def test_refuses_any_composed_observer_that_is_not_its_pinned_bytes(self):
        for i in range(len(PINNED_FILES)):
            fake = tempfile.mkdtemp(prefix="ec1repo")
            try:
                for j, rel in enumerate(PINNED_FILES):
                    dst = os.path.join(fake, *rel)
                    os.makedirs(os.path.dirname(dst))
                    with io.open(os.path.join(REPO, *rel), "rb") as f:
                        raw = f.read()
                    with io.open(dst, "wb") as f:
                        f.write(raw.replace(b"# -*- coding", b"#  -*- coding", 1) if i == j else raw)
                with self.assertRaises(RuntimeError):
                    run(self.dir, "EC1-1%d" % i, repo=fake)
            finally:
                shutil.rmtree(fake)
        self.assertEqual(os.listdir(os.path.join(self.dir, "observations")), [])

    def test_observer_calls_no_mutating_api(self):
        with io.open(OBSERVER, "rb") as f:
            text = f.read().decode("ascii")
        for name in ("SetEvaluateProceduralBones", "SetKeyValue", "InsertKeyAtTime", "SetHeadTimeInSeconds",
                     "StartUndo", "SetValue(", "SaveDocument", "SetBone", "RemoveAllBones", "SetFlags", "AddControl",
                     "CreateRig", "Release("):
            self.assertNotIn(name, text)


if PY3:
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import ec1_analyze as A  # noqa: E402

    FIXTURE = os.path.join(REPO, "cpm", "convergence", "tests", "fixtures", "f01_scoped", "mc01_heavy_norig.json")
    HELPERS = ("hlp_forearm_L", "hlp_forearm_R")
    K = {}

    def tools():
        if not K:
            K.update(A.cpm_tools())
        return K

    def heavy():
        with io.open(FIXTURE, "rb") as f:
            raw = f.read()
        assert hashlib.sha256(raw).hexdigest() == "eb240d2e0f78e05f4df83a01086b56105e497de065eb45eff2f512af5aad8a63"
        return json.loads(raw.decode("utf-8"))

    def zero_indices(D):
        return dict((n, [{"status": "READ", "value": 0}, {"status": "READ", "value": 0}]) for n in D["channels"])

    def with_helper_controls(D):
        """The Heavy skeleton with a direct transform control on each control-less helper."""
        D = copy.deepcopy(D)
        handle = 990000
        for bone in HELPERS:
            handle += 1
            chans = {}
            for attr, suffix, src, slot in (("position", "_p", "valuePosition", "positionChannel"),
                                            ("orientation", "_o", "valueOrientation", "orientationChannel")):
                ch = D["channels"][bone + suffix]
                assert ch["from"] is None and ch["to_attribute"] == attr
                ch["from"] = {"handle": handle, "type": "DmeTransformControl", "name": bone}
                ch["from_attribute"] = src
                chans[slot] = ch["handle"]
            values = {"valuePosition": D["channels"][bone + "_p"]["keys"][0][1],
                      "valueOrientation": D["channels"][bone + "_o"]["keys"][0][1]}
            D["controls"][bone] = {"handle": handle, "type": "DmeTransformControl", "channels": chans,
                                   "values": values}
        return D

    def structure(D, indices=None, source_less=(), ops=("DmeExpressionOperator",), rigs=0):
        rows = []
        C, E = A.structure_criteria(rows, tools(), D, indices or zero_indices(D), list(source_less), list(ops),
                                    {"DmeExpressionOperator": 1}, rigs)
        return dict((r["criterion"], r["result"]) for r in rows), C, E

    class AnalysisTests(unittest.TestCase):
        def test_real_heavy_structure_is_not_a_candidate_by_both_routes(self):
            got, C, E = structure(heavy(), source_less=["hlp_forearm_L_p"])
            self.assertEqual(got["Q1.every_bone_has_one_direct_control"], "FAIL")
            self.assertEqual(C["control_less_bones"], list(HELPERS))
            self.assertEqual(E["inventory"]["classes"], {"direct-fk": 77, "carried-candidate": 2})
            self.assertEqual(E["inventory"]["full_body"]["code"], "carried-unsupported")
            self.assertEqual(got["Q5.cpm_agrees_with_the_census"], "PASS")
            self.assertEqual(got["Q3.no_source_less_bone_channels"], "FAIL")

        def test_the_skeleton_with_helper_controls_passes_every_structural_criterion(self):
            got, C, E = structure(with_helper_controls(heavy()))
            self.assertEqual(set(got.values()), set(["PASS"]), got)
            self.assertEqual(E["inventory"]["full_body"]["status"], "available")
            self.assertEqual(E["compile"]["posed"], 79)
            self.assertEqual(E["apply_changed_copy"]["verdict"], {"phase": "committed-verified"})
            self.assertTrue(E["apply_changed_copy"]["restored"])

        def test_nonzero_and_unreadable_endpoint_indices_fail_through_both_routes(self):
            D = with_helper_controls(heavy())
            idx = zero_indices(D)
            idx["bip_spine_1_o"] = [{"status": "READ", "value": 0}, {"status": "READ", "value": 1}]
            got, C, E = structure(D, idx)
            self.assertEqual(got["Q2.bindings_types_and_indices_supported"], "FAIL")
            self.assertEqual(C["bones"]["bip_spine_1"]["class"], "not-direct")
            self.assertEqual(E["inventory"]["not_direct_fk"], ["bip_spine_1"])
            self.assertEqual(got["Q5.cpm_classifies_every_bone_direct_fk"], "FAIL")
            self.assertEqual(got["Q5.cpm_agrees_with_the_census"], "PASS")
            # An unreadable index is no conclusion: CPM refuses the whole inventory as evidence-unreadable.
            idx["bip_spine_1_o"] = [{"status": "READ", "value": 0}, {"status": "UNREADABLE", "error": "x"}]
            got, C, E = structure(D, idx)
            self.assertEqual(E["inventory"]["code"], "evidence-unreadable")
            self.assertEqual(got["Q2.bindings_types_and_indices_supported"], "UNREADABLE")
            self.assertEqual(got["Q5.cpm_classifies_every_bone_direct_fk"], "UNREADABLE")
            rows = [{"criterion": k, "result": v} for k, v in got.items()]
            self.assertEqual(A.verdict_of(rows), "NO-CONCLUSION")

        def test_rig_constraint_and_unsupported_operators_fail_q4(self):
            D = with_helper_controls(heavy())
            got, _, _ = structure(D, rigs=1)
            self.assertEqual(got["Q4.no_rig_registration"], "FAIL")
            got, _, _ = structure(D, ops=("DmeExpressionOperator", "DmeRigPointConstraintOperator"))
            self.assertEqual(got["Q4.no_constraint_operators"], "FAIL")
            got, _, _ = structure(D, ops=("DmeConnectionOperator",))
            self.assertEqual(got["Q4.no_unsupported_operator_types"], "FAIL")

        def test_a_control_driving_two_bones_fails_q3(self):
            # hlp_forearm_L's control also drives hlp_forearm_R's orientation; R's control keeps only its position.
            D = with_helper_controls(heavy())
            left, right = D["controls"]["hlp_forearm_L"], D["controls"]["hlp_forearm_R"]
            left["channels"]["orientationChannel"] = right["channels"]["orientationChannel"]
            right["channels"]["orientationChannel"] = None
            D["channels"]["hlp_forearm_R_o"]["from"] = dict(D["channels"]["hlp_forearm_L_p"]["from"])
            got, C, E = structure(D)
            self.assertEqual(C["controls_driving_several_bones"], {"hlp_forearm_L": ["hlp_forearm_L",
                                                                                     "hlp_forearm_R"]})
            self.assertEqual(got["Q3.no_control_drives_several_bones"], "FAIL")
            self.assertEqual(got["Q1.every_bone_has_one_direct_control"], "FAIL")
            self.assertEqual(got["Q5.cpm_full_body_available"], "FAIL")

        def test_identity_against_the_pinned_engineer_header(self):
            with io.open(os.path.join(ROOT, "engineer_header.json"), "rb") as f:
                expected = json.loads(f.read().decode("utf-8"))
            read = lambda v: {"status": "READ", "value": v}
            consts = dict((k, read(v)) for k, v in NQT.PROC.items())

            def obs(mutate=None):
                bones = [dict([("index", b["index"]), ("name", read(b["name"]))] +
                              [(f, read(b[f])) for f in A.HEADER_FIELDS]) for b in expected["bones"]]
                o = {"model": {"modelName": read(ENGINEER)},
                     "nq": {"studio": {"constants": consts, "bones": bones,
                                       "header": {"checksum": read(expected["header"]["checksum"]),
                                                  "numbones": read(expected["header"]["numbones"])}}}}
                if mutate:
                    mutate(o)
                rows = []
                A.check_identity(o, expected, rows)
                return dict((r["criterion"], r["result"]) for r in rows)
            self.assertEqual(set(obs().values()), set(["PASS"]))

            def flag(o):
                o["nq"]["studio"]["bones"][5]["flags"] = read(o["nq"]["studio"]["bones"][5]["flags"]["value"] | 4)
            got = obs(flag)
            self.assertEqual((got["identity.header_rows_equal_the_nq03_pin"],
                              got["identity.no_declared_procedural_bone"]), ("FAIL", "FAIL"))

            def checksum(o):
                o["nq"]["studio"]["header"]["checksum"] = read(1)
            self.assertEqual(obs(checksum)["identity.header_checksum"], "FAIL")

            def unreadable(o):
                o["nq"]["studio"]["bones"][3]["proctype"] = {"status": "UNREADABLE", "error": "x"}
            self.assertEqual(obs(unreadable)["identity.header_rows_equal_the_nq03_pin"], "UNREADABLE")

        def test_verdict_gates(self):
            ok = [{"criterion": "observation.no_problems", "result": "PASS"}, {"criterion": "Q1.x", "result": "PASS"}]
            self.assertEqual(A.verdict_of(ok), "CANDIDATE")
            self.assertEqual(A.verdict_of(ok + [{"criterion": "Q2.x", "result": "FAIL"}]), "NOT-CANDIDATE")
            self.assertEqual(A.verdict_of(ok + [{"criterion": "Q2.x", "result": "UNREADABLE"}]), "NO-CONCLUSION")
            self.assertEqual(A.verdict_of([{"criterion": "observation.no_problems", "result": "FAIL"},
                                           {"criterion": "Q2.x", "result": "FAIL"}]), "NO-CONCLUSION")

    class ToolTests(unittest.TestCase):
        def setUp(self):
            import ec1_tool as T
            self.T = T
            with io.open(os.path.join(ROOT, "ec1.template.json"), "rb") as f:
                self.template = json.loads(f.read().decode("utf-8"))
            self.dir = tempfile.mkdtemp(prefix="ec1tool")

        def tearDown(self):
            shutil.rmtree(self.dir)

        def config(self):
            c = copy.deepcopy(self.template)
            c["paths"].update({"REPO": REPO, "GAME": self.dir})
            return c

        def test_the_template_pins_this_kits_files(self):
            c = self.config()
            for key, path in self.T.kit_files(c).items():
                self.assertEqual(self.T.sha(path), c["pins"][key + "_sha256"], key)
            self.assertIs(self.T.M.kit_files, self.T.kit_files)
            self.assertEqual(c["models"], ["tf/models/player/engineer.mdl"])
            with io.open(os.path.join(ROOT, "engineer_header.json"), "rb") as f:
                header = json.loads(f.read().decode("utf-8"))
            self.assertEqual(c["model_pins"], {header["game_relative"]: header["file_sha256"]})

        def test_model_identity_follows_the_search_order_and_the_pin(self):
            os.makedirs(os.path.join(self.dir, "usermod"))
            with io.open(os.path.join(self.dir, "usermod", "gameinfo.txt"), "w") as f:
                f.write(u'"GameInfo"\n{\n FileSystem\n {\n  SearchPaths\n  {\n   Game |gameinfo_path|.\n'
                        u'   "Game" "|gameinfo_path|."\n   "Game" "tf"\n  }\n }\n}\n')
            path = os.path.join(self.dir, "tf", "models", "player")
            os.makedirs(path)
            with io.open(os.path.join(path, "engineer.mdl"), "wb") as f:
                f.write(b"engineer")
            c = self.config()
            c["model_pins"] = {"tf/models/player/engineer.mdl": hashlib.sha256(b"engineer").hexdigest()}
            self.assertTrue(self.T.model_check(c)["pass"])
            c["model_pins"] = {"tf/models/player/engineer.mdl": "0" * 64}
            self.assertFalse(self.T.model_check(c)["pass"])
            c = self.config()
            c["model_pins"] = {"tf/models/player/engineer.mdl": hashlib.sha256(b"engineer").hexdigest()}
            shadow = os.path.join(self.dir, "usermod", "models", "player")
            os.makedirs(shadow)
            with io.open(os.path.join(shadow, "engineer.mdl"), "wb") as f:
                f.write(b"engineer")
            check = self.T.model_check(c)
            self.assertFalse(check["pass"])
            self.assertEqual(check["resolved"], "usermod/models/player/engineer.mdl")


if __name__ == "__main__":
    unittest.main(verbosity=1)
