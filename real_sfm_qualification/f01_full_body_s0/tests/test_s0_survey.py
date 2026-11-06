# -*- coding: ascii -*-
"""Offline tests of the F-01 full-body S0 survey: the observer against a fake SFM (Python 2.7 and 3) and the
validator and analyzer (Python 3). Run: python -I test_s0_survey.py  (SFM's Python 2.7: python -E -s ...)."""
import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OBSERVER = os.path.join(ROOT, "observer", "F01_S0_Survey.py")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fake_sfm_s0 as F  # noqa: E402

PY3 = sys.version_info[0] >= 3
if PY3:
    import s0_analyze as A  # noqa: E402


def read(path):
    with io.open(path, "rb") as f:
        return f.read()


class Sink(object):
    """Python 2 stdout stand-in; like SFM's console it takes the observer's (ASCII) summary line."""
    def write(self, data):
        if not isinstance(data, bytes):
            raise TypeError("the observer printed a non-byte string on Python 2")


def run_observer(folder, label, stale=(), competing=False, animset=None, before=None):
    world, S, sfm, vs = F.install(stale, competing)
    if before:
        before(world, S)
    sys.modules["sfmApp"], sys.modules["vs"] = sfm, vs
    g = {"__name__": "__s0__", "S0_DIR": folder, "S0_LABEL": label}
    if animset:
        g["S0_ANIMSET"] = animset
    with io.open(OBSERVER, "rb") as f:
        code = compile(f.read(), OBSERVER, "exec")
    saved = sys.stdout
    sys.stdout = io.StringIO() if PY3 else Sink()
    try:
        exec(code, g)
    finally:
        sys.stdout = saved
    with io.open(os.path.join(folder, "observations", label + ".json"), "rb") as f:
        return world, S, json.loads(f.read().decode("utf-8"))


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="s0test")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir)


class ObserverTests(Base):
    def test_observation_is_complete_and_readonly(self):
        world, S, obs = run_observer(self.dir, "S0-01")
        self.assertEqual(obs["problems"], [])
        self.assertEqual(world.mutations, [])
        self.assertTrue(obs["readonly"]["unchanged"])
        self.assertEqual(obs["format"], "F01-S0-survey-v1")
        self.assertEqual(obs["time"]["t_chan"], F.T_CHAN)
        self.assertEqual(len(obs["bones"]), 10)
        self.assertEqual(sorted(obs["rig"]["handles"]), ["Foot_l", "Hip", "Knee_l", "rig_footHelper0", "rig_root"])
        self.assertEqual(obs["bones"]["bip_knee_l"]["parent_bone"], "bip_hip_l")
        self.assertEqual(obs["bones"]["bip_pelvis"]["parent_bone"], None)
        ik = [o for o in obs["operators"] if o["id"]["type"] == "DmeRigIKConstraintOperator"][0]
        self.assertEqual(sorted(ik["slaves"]), ["endJoint", "midJoint", "startJoint"])
        self.assertEqual(ik["pvTarget"]["name"], "Knee_l")
        self.assertEqual(ik["solver"]["poleVector"], {"status": "READ", "value": [0.0, 1.0, 0.0]})
        self.assertEqual(ik["targets"][0]["targetWeight"], {"status": "READ", "value": 1.0})
        toe = [c for c in obs["channels"] if c["id"]["name"] == "bip_toe_l_o"][0]
        self.assertEqual(toe["current_ticks"], F.T_CHAN)
        self.assertEqual(toe["layers"][0]["key_at_mapped"], 1)
        self.assertEqual(toe["value_at_mapped"], [0.2, 0.0, 0.0, 0.98])
        self.assertEqual(toe["layers"][0]["keys"], [[0, [0.0, 0.0, 0.0, 1.0]], [F.T_CHAN, [0.2, 0.0, 0.0, 0.98]]])
        self.assertEqual(obs["model"]["modelName"]["value"], "models/krystal2020.mdl")
        self.assertIsNone(obs["cpm_loaded"])

    def test_source_has_no_mutating_call(self):
        with io.open(OBSERVER, "r", encoding="ascii") as f:
            src = f.read()
        calls = set(re.findall(r"\.([A-Za-z_]+)\(", src))
        forbidden = set(F.MUTATORS) | set(["SetAttributeValue", "SetSelection", "AddControl", "CreateElement",
                                           "DestroyElement", "Save", "SaveAs", "Rebuild", "Clear"])
        self.assertEqual(sorted(calls & forbidden), [])
        self.assertEqual([c for c in calls if re.match(r"^(Set|Insert|Remove|Add|Delete|Create|Destroy|Undo|Redo|"
                                                       r"Start|Finish|Abort)", c)], [])
        self.assertEqual(src.count("os.open("), 1)  # the observation file, exclusive create

    def test_existing_observation_is_never_replaced(self):
        run_observer(self.dir, "S0-01")
        path = os.path.join(self.dir, "observations", "S0-01.json")
        with io.open(path, "rb") as f:
            first = f.read()
        self.assertRaises(RuntimeError, run_observer, self.dir, "S0-01")
        with io.open(path, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_label_is_required(self):
        self.assertRaises(RuntimeError, run_observer, self.dir, "first")

    def test_unknown_animation_set_is_reported(self):
        world, S, obs = run_observer(self.dir, "S0-02", animset="Nobody")
        self.assertTrue(any("Nobody" in p for p in obs["problems"]))
        self.assertEqual(world.mutations, [])

    def test_unreadable_channel_is_reported_not_skipped(self):
        def poison(world, S):
            world.unreadable_channel = "bip_tail00_o"
        world, S, obs = run_observer(self.dir, "S0-03", before=poison)
        self.assertTrue(any("bip_tail00_o" in p for p in obs["problems"]))
        self.assertEqual(world.mutations, [])

    def test_stale_clock_is_recorded(self):
        world, S, obs = run_observer(self.dir, "S0-04", stale=("bip_toe_l_o",))
        toe = [c for c in obs["channels"] if c["id"]["name"] == "bip_toe_l_o"][0]
        self.assertEqual(toe["current_ticks"], F.T_CHAN + 91)


@unittest.skipUnless(PY3, "the analyzer runs with Python 3")
class AnalyzerTests(Base):
    def report(self, **kw):
        world, S, obs = run_observer(self.dir, "S0-01", **kw)
        self.assertEqual(A.validate(obs), [])
        return obs, A.analyze([obs])

    def test_bone_classification(self):
        obs, rep = self.report()
        self.assertTrue(rep["valid"])
        b = rep["analysis"]["bones"]
        for n in ("bip_pelvis", "bip_hip_l", "bip_knee_l", "bip_foot_l"):
            self.assertEqual(b[n]["class"], "constrained", n)
        self.assertEqual(b["bip_pelvis"]["dormant_channels"], ["bip_pelvis_p", "bip_pelvis_o"])
        self.assertEqual(len(b["bip_foot_l"]["drivers"]), 2)  # IK end joint and orient constraint
        self.assertEqual(b["bip_hip_twist2_l"]["class"], "operator-driven")
        self.assertEqual(b["bip_wing_l"]["class"], "driven by an unknown operator")
        self.assertTrue(b["bip_hair"]["class"].startswith("no writer"))
        self.assertEqual(b["bip_toe_l"]["class"], "direct FK")
        self.assertEqual(b["bip_toe_l"]["translation"], ["constant (structural-offset candidate)"])
        self.assertEqual(b["bip_tail00"]["translation"], ["animated translation"])
        self.assertEqual(b["bip_ear_l"]["class"], "direct FK")
        self.assertEqual(rep["analysis"]["unaccounted_bones"], ["bip_wing_l"])

    def test_rig_handles_operators_and_weights(self):
        obs, rep = self.report()
        a = rep["analysis"]
        self.assertEqual(a["rig_handles"]["rig_footHelper0"]["parents"], ["handle:Foot_l"])
        self.assertEqual(a["rig_handles"]["Hip"]["parents"], ["handle:rig_root"])
        self.assertIn("pole of ikConstraint_Foot_l", a["rig_handles"]["Knee_l"]["roles"])
        ik = [o for o in a["operators"] if o["type"] == "DmeRigIKConstraintOperator"][0]
        self.assertEqual(ik["slaves"], {"startJoint": "bone:bip_hip_l", "midJoint": "bone:bip_knee_l",
                                        "endJoint": "bone:bip_foot_l"})
        self.assertEqual(ik["targets"], [{"target": "handle:Foot_l", "weight": 1.0,
                                          "weight_channels": ["ikConstraint_Foot_l - Foot_l targetWeight"]}])
        self.assertEqual(ik["solver"]["poleVector"], [0.0, 1.0, 0.0])
        self.assertEqual(a["controls"]["Hip"]["channels"][0]["drives"], "handle:Hip")
        self.assertEqual(a["clocks_by_channel_class"]["constraint weight"]["channels"], 1)
        self.assertEqual(a["clocks_by_channel_class"]["dormant (constrained bone)"]["channels"], 8)

    def test_competing_writers_are_unaccounted(self):
        obs, rep = self.report(competing=True)
        self.assertEqual(rep["analysis"]["bones"]["bip_tail00"]["class"], "competing writers")
        self.assertIn("bip_tail00", rep["analysis"]["unaccounted_bones"])

    def test_clock_classes(self):
        obs, rep = self.report(stale=("bip_toe_l_o", "bip_pelvis_o"))
        c = rep["analysis"]["clocks_by_channel_class"]
        self.assertEqual(c["direct FK bone"]["other_clocks"], {str(F.T_CHAN + 91): 1})
        self.assertEqual(c["dormant (constrained bone)"]["other_clocks"], {str(F.T_CHAN + 91): 1})
        self.assertEqual(c["rig handle"]["other_clocks"], {})
        self.assertEqual(rep["analysis"]["off_clock_channels"], ["bip_pelvis_o", "bip_toe_l_o"])

    def test_validator_rejects_malformed(self):
        world, S, obs = run_observer(self.dir, "S0-01")
        bad = copy.deepcopy(obs)
        bad["format"] = "other"
        self.assertTrue(A.validate(bad))
        bad = copy.deepcopy(obs)
        del bad["channels"]
        self.assertIn("survey section channels missing or of the wrong type", A.validate(bad))
        bad = copy.deepcopy(obs)
        bad["time"]["t_chan"] = 5.5
        self.assertIn("time.t_chan is not an integer", A.validate(bad))
        bad = copy.deepcopy(obs)
        bad["readonly"]["digest_after"] = {"sha256": "x"}
        self.assertIn("readonly.digest_after is not a digest", A.validate(bad))
        bad = copy.deepcopy(obs)
        bad["label"] = "OBS-01"
        self.assertTrue(A.validate(bad))
        bad = copy.deepcopy(obs)
        del bad["bones"]["bip_toe_l"]["local_orientation"]
        self.assertIn("bone bip_toe_l: local_orientation missing", A.validate(bad))
        self.assertEqual(A.validate([]), ["not a JSON object"])

    def test_observer_problems_invalidate_the_report(self):
        def poison(world, S):
            world.unreadable_channel = "bip_tail00_o"
        world, S, obs = run_observer(self.dir, "S0-01", before=poison)
        rep = A.analyze([obs])
        self.assertFalse(rep["valid"])
        self.assertNotIn("analysis", rep)

    def test_readonly_failure_is_detected(self):
        world, S, obs = run_observer(self.dir, "S0-01")
        changed = copy.deepcopy(obs)
        changed["label"] = "S0-02"
        changed["readonly"]["digest_after"]["sha256"] = "0" * 64
        changed["readonly"]["unchanged"] = False
        rep = A.analyze([obs, changed])
        self.assertFalse(rep["readonly"]["every_observation_unchanged"])
        self.assertFalse(rep["readonly"]["one_document_digest_per_process"])

    def test_instance_and_time_comparison(self):
        world, S, obs = run_observer(self.dir, "S0-01")
        other = copy.deepcopy(obs)
        other["label"] = "S0-05"
        other["animation_set"]["id"]["handle"] += 1
        other["bones"]["bip_toe_l"]["local_orientation"] = [0.0, 0.0, 0.3826834, 0.9238795]
        other["bones"]["bip_tail00"]["local_position"] = [0.0, -4.0, 2.0]
        rep = A.analyze([obs, other])
        c = rep["instances"]["S0-05"]
        self.assertTrue(all(c["structure_equal"].values()))
        self.assertEqual(c["bones_differing"], 2)
        self.assertEqual(c["largest_rotation"][0][0], "bip_toe_l")
        self.assertAlmostEqual(c["largest_rotation"][0][1], 45.0, places=3)
        self.assertEqual(rep["same_instance_other_times"], {})

    def test_main_writes_both_reports_exclusively(self):
        run_observer(self.dir, "S0-01")
        out = os.path.join(self.dir, "evidence")
        os.makedirs(out)
        saved = sys.stdout
        sys.stdout = io.StringIO()
        try:
            self.assertEqual(A.main(["s0_analyze.py", os.path.join(self.dir, "observations"), out]), 0)
            self.assertRaises(OSError, A.main, ["s0_analyze.py", os.path.join(self.dir, "observations"), out])
        finally:
            sys.stdout = saved
        with io.open(os.path.join(out, "S0_REPORT.md"), encoding="utf-8") as f:
            md = f.read()
        self.assertIn("| bip_pelvis | None | constrained |", md)
        self.assertIn("Read-only proof: every observation unchanged **True**", md)


@unittest.skipUnless(PY3, "the run tool runs with Python 3")
class ToolTests(Base):
    """pre / post round trip over a disposable fake installation (SFM is never involved)."""

    def setUp(self):
        Base.setUp(self)
        import hashlib
        import s0_tool
        self.tool = s0_tool
        self.saved_running = s0_tool.T.sfm_running
        s0_tool.T.sfm_running = lambda: None
        g = os.path.join(self.dir, "game")
        self.files = {"cpm": os.path.join(g, "usermod", "scripts", "ChadChan3D_CPM", "SFM_Character_Preset_Manager.py"),
                      "pyc": os.path.join(g, "usermod", "scripts", "sfm", "mainmenu", "x.pyc"),
                      "cfg": os.path.join(g, "usermod", "cfg", "config.cfg"),
                      "fixture": os.path.join(self.dir, "fixture.dmx")}
        for k, path in self.files.items():
            if not os.path.isdir(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with io.open(path, "wb") as f:
                f.write(("content of %s\n" % k).encode("ascii"))
        for d in ("library", "sfm_sessions"):
            os.makedirs(os.path.join(self.dir, d))
        sha = lambda p: hashlib.sha256(read(p)).hexdigest()  # noqa: E731
        self.q = os.path.join(self.dir, "run")
        os.makedirs(self.q)
        self.c = {"format": "F01-S0-config-v1", "paths": {
            "Q": self.q, "REPO": os.path.dirname(os.path.dirname(ROOT)), "GAME": g, "LIBRARY": os.path.join(self.dir, "library"),
            "SESSIONS": os.path.join(self.dir, "sfm_sessions"), "SCRIPTS_ROOT": "{GAME}/usermod/scripts",
            "CFG_ROOT": "{GAME}/usermod/cfg", "R2_FIXTURE": self.files["fixture"]},
            "pins": {"published_cpm_sha256": sha(self.files["cpm"]), "r2_fixture_sha256": sha(self.files["fixture"]),
                     "observer_sha256": sha(OBSERVER)}, "housekeeping": ["cfg\\config.cfg", "stats.txt"]}
        self.cfg = os.path.join(self.q, "s0.json")
        with io.open(self.cfg, "wb") as f:
            f.write(json.dumps(self.c).encode("utf-8"))

    def tearDown(self):
        self.tool.T.sfm_running = self.saved_running
        Base.tearDown(self)

    def run_tool(self, command):
        saved = sys.stdout
        sys.stdout = io.StringIO()
        try:
            return self.tool.main(["s0_tool.py", self.cfg, command])
        finally:
            sys.stdout = saved

    def test_round_trip_puts_back_housekeeping_and_passes(self):
        self.run_tool("pre")
        self.assertTrue(os.path.isfile(os.path.join(self.q, "sessions", "S0_SURVEY.dmx")))
        self.assertRaises(SystemExit, self.run_tool, "pre")  # never twice
        for k in ("cfg", "pyc"):  # what an SFM launch rewrites
            with io.open(self.files[k], "wb") as f:
                f.write(b"rewritten by SFM\n")
        self.assertEqual(self.run_tool("post"), 0)
        post = json.loads(read(os.path.join(self.q, "evidence", "post.json")).decode("utf-8"))
        self.assertTrue(post["pass"])
        self.assertEqual(sorted(post["put_back"]), ["cfg/config.cfg", "scripts/sfm/mainmenu/x.pyc"])

    def test_status_reports_a_fresh_completed_pre(self):
        self.assertEqual(self.run_tool("status"), 1)  # no pre yet
        self.run_tool("pre")
        self.assertEqual(self.run_tool("status"), 0)
        self.assertRaises(SystemExit, self.run_tool, "pre")  # the second pre still refuses
        self.assertEqual(self.run_tool("status"), 0)  # and changed nothing

    def test_status_is_not_fresh_after_a_change(self):
        self.run_tool("pre")
        with io.open(self.files["cfg"], "wb") as f:  # SFM started after pre
            f.write(b"rewritten by SFM\n")
        self.assertEqual(self.run_tool("status"), 1)
        with io.open(self.files["cfg"], "wb") as f:
            f.write(b"content of cfg\n")
        self.assertEqual(self.run_tool("status"), 0)
        with io.open(os.path.join(self.q, "observations", "S0-01.json"), "wb") as f:
            f.write(b"{}")
        self.assertEqual(self.run_tool("status"), 1)

    def test_saved_session_fails_post(self):
        self.run_tool("pre")
        with io.open(os.path.join(self.q, "sessions", "S0_SURVEY.dmx"), "ab") as f:
            f.write(b"saved\n")
        self.assertEqual(self.run_tool("post"), 1)

    def test_installed_registry_or_other_cpm_refuses_pre(self):
        reg = os.path.join(self.dir, "game", "usermod", "scripts", "SFM Character Tools", "cpm_pose_profiles_v1.json")
        os.makedirs(os.path.dirname(reg))
        with io.open(reg, "wb") as f:
            f.write(b"{}")
        self.assertRaises(SystemExit, self.run_tool, "pre")
        self.assertFalse(os.path.exists(os.path.join(self.q, "pre_run")))
        os.remove(reg)
        with io.open(self.files["cpm"], "ab") as f:
            f.write(b"# candidate\n")
        self.assertRaises(SystemExit, self.run_tool, "pre")
        self.assertFalse(os.path.exists(os.path.join(self.q, "pre_run")))

    def test_unchanged_observer_is_required(self):
        self.c["pins"]["observer_sha256"] = "0" * 64
        with io.open(self.cfg, "wb") as f:
            f.write(json.dumps(self.c).encode("utf-8"))
        self.assertRaises(SystemExit, self.run_tool, "pre")

    def test_analyze_without_observations_refuses(self):
        self.run_tool("pre")
        self.assertEqual(self.run_tool("analyze"), 2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
