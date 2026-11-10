# -*- coding: ascii -*-
"""Offline tests of the F-01 EF-1 Engineer Full body native qualification kit.

- The observer wrapper, against the S0 suite's fake SFM (Python 2.7 and 3):
  - it runs the pinned S0 observer unchanged inside its read-only window and writes the observation and its sidecar;
  - it never mutates the scene, and reports a step whose shot or playhead differs;
  - it refuses, writing nothing, a repeated or unknown step, a model other than the Engineer, a missing animation
    set, or an S0 observer whose bytes differ;
  - it moves exactly S0's no-rig note to findings;
  - its step table equals the comparator's.
- The UI capture, against a fake CPM window (Python 2.7 and 3): read-only; records a version 3 Full body pose; reports
  STOP otherwise; is never repeated.
- ef1_tool (Python 3):
  - build derives the pinned qualification CPM from the real candidate in exactly one line, and a wrong pin
    refuses;
  - inspect pins two prepared character sessions, records autosaves, and refuses a starter, identical or unexpected
    file;
  - restore moves a new Engineer character folder's files into evidence and removes the emptied folder;
  - pre refuses when the Engineer folder already exists;
  - the reused S3 tool carries this kit's identity.
- ef1_compare (Python 3): a complete synthetic run of the 72-bone Engineer that meets every Expected result is PASS
  (an autosave is a finding), and each counterexample is FAIL on its own check.
They show nothing about SFM.

Run: python -I test_ef1.py   (SFM's Python 2.7: python -E -s -B test_ef1.py runs the wrapper and UI tests)
"""
import copy
import hashlib
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RSQ = os.path.dirname(ROOT)
REPO = os.path.dirname(RSQ)
WRAPPER = os.path.join(ROOT, "observer", "F01_EF1_Observe.py")
UI = os.path.join(ROOT, "observer", "F01_EF1_UIState.py")
S0_REL = ("real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")
sys.path.insert(0, os.path.join(RSQ, "f01_full_body_s0", "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fake_sfm_s0 as F  # noqa: E402

PY3 = sys.version_info[0] >= 3
if PY3:
    import ef1_compare as C  # noqa: E402
    import ef1_tool as TOOL  # noqa: E402

ENGINEER = "models/player/engineer.mdl"
NO_RIG = "expected one rig registration for the animation set, found 0"


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def load(path):
    with io.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


class Sink(object):
    def write(self, data):
        if not isinstance(data, bytes):
            raise TypeError("non-byte output on Python 2")


def exec_file(path, g):
    with io.open(path, "rb") as f:
        code = compile(f.read(), path, "exec")
    exec(code, g)


def capture(fn):
    out = io.StringIO() if PY3 else Sink()
    saved = sys.stdout
    sys.stdout = out
    try:
        fn()
    finally:
        sys.stdout = saved
    return out.getvalue() if PY3 else None


# --- the observer wrapper (Python 2.7 and 3) -------------------------------------------------------------------------

def run_wrapper(folder, step, model=ENGINEER, animset="Krystal", repo=REPO):
    world, S, sfm, vs = F.install()
    gm = [c for c in S["shot"].attrs["scene"].attrs["children"].items if c.kind == "DmeGameModel"][0]
    if model is not None:
        gm.attrs["modelName"] = model
    sys.modules["sfmApp"], sys.modules["vs"] = sfm, vs
    printed = capture(lambda: exec_file(WRAPPER, {"__name__": "__ef1__", "EF1_DIR": folder, "EF1_REPO": repo,
                                                  "EF1_STEP": step, "EF1_ANIMSET": animset}))
    return world, printed


def wrapper_functions():
    with io.open(WRAPPER, "rb") as f:
        source = f.read()
    tail = b"\n\nef1_main(globals())\n"
    assert source.endswith(tail)
    g = {"__name__": "__ef1_functions__"}
    exec(compile(source[:-len(tail)], WRAPPER, "exec"), g)
    return g


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ef1test")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_observes_read_only_and_writes_the_observation_and_sidecar(self):
        world, printed = run_wrapper(self.dir, "A1")
        self.assertEqual(world.mutations, [])
        obs = load(os.path.join(self.dir, "observations", "S0-01.json"))
        side = load(os.path.join(self.dir, "observations", "S0-01.ef1.json"))
        self.assertEqual((obs["format"], obs["label"], obs["s0_observer_sha256"]),
                         ("F01-S0-survey-v1", "S0-01", "4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4"))
        self.assertTrue(obs["readonly"]["unchanged"])
        self.assertEqual((obs["problems"], obs["findings"]), ([], []))          # the fake Krystal has a rig
        self.assertEqual((side["step"], side["label"], side["format"], side["animation_set"]),
                         ("A1", "S0-01", "F01-EF1-sidecar-v1", "Krystal"))
        self.assertEqual((len(side["outside"]["sha256"]), side["outside"]["unreadable"]), (64, 0))
        self.assertTrue(any("shot" in m for m in side["mismatch"]))              # the fake's shot is not shot1
        if PY3:
            self.assertIn("EF1 STEP A1 (S0-01): MISMATCH - STOP", printed)

    def test_refuses_without_writing(self):
        run_wrapper(self.dir, "A1")
        for kw in ({"step": "A1"}, {"step": "Z9"}, {"step": "A2", "model": None},
                   {"step": "A2", "model": "models/player/heavy.mdl"}, {"step": "A2", "animset": "nobody"}):
            step = kw.pop("step")
            with self.assertRaises(RuntimeError):
                run_wrapper(self.dir, step, **kw)
        self.assertEqual(sorted(os.listdir(os.path.join(self.dir, "observations"))), ["S0-01.ef1.json", "S0-01.json"])

    def test_refuses_an_s0_observer_that_is_not_its_pinned_bytes(self):
        fake = tempfile.mkdtemp(prefix="ef1repo")
        try:
            dst = os.path.join(fake, *S0_REL)
            os.makedirs(os.path.dirname(dst))
            with io.open(os.path.join(REPO, *S0_REL), "rb") as f:
                raw = f.read()
            with io.open(dst, "wb") as f:
                f.write(raw.replace(b"# -*- coding", b"#  -*- coding", 1))
            self.assertRaises(RuntimeError, run_wrapper, self.dir, "A1", repo=fake)
        finally:
            shutil.rmtree(fake)
        self.assertEqual(os.listdir(os.path.join(self.dir, "observations")), [])

    def test_only_the_exact_no_rig_note_becomes_a_finding(self):
        g = wrapper_functions()
        obs = g["ef1_reclassify"]({"problems": [NO_RIG, "expected one rig registration for the animation set, "
                                                        "found 2", "channel x unreadable"], "readonly": {}})
        self.assertEqual(obs["findings"], [NO_RIG])
        self.assertEqual(obs["problems"], ["expected one rig registration for the animation set, found 2",
                                           "channel x unreadable"])

    def test_step_table_matches_the_comparator(self):
        with io.open(WRAPPER, "rb") as f:
            text = f.read().decode("ascii")
        table = dict(re.findall(r'"([AB]\d+)": \("(S0-\d\d)"', text))
        self.assertEqual(len(table), 13)
        if PY3:
            self.assertEqual(table, C.LABELS)

    def test_observer_and_ui_capture_call_no_mutating_api(self):
        for path in (WRAPPER, UI):
            with io.open(path, "rb") as f:
                text = f.read().decode("ascii")
            for name in ("SetKeyValue", "InsertKeyAtTime", "SetHeadTimeInSeconds", "StartUndo", "SetValue(",
                         "SaveDocument", "click(", "setChecked", "SetEvaluateProceduralBones"):
                self.assertNotIn(name, text, (path, name))


# --- the UI capture (Python 2.7 and 3) -----------------------------------------------------------------------------

class FakeButton(object):
    def __init__(self, enabled):
        self.enabled, self.clicks = enabled, 0

    def isEnabled(self):
        return self.enabled


class FakeWindow(object):
    def __init__(self, enabled=True, version=3, kind=u"full_body"):
        self.apply_pose_button = FakeButton(enabled)
        self.pose_recovery_blocked = False
        self.item = {u"name": u"EF1 Body", u"preset_id": u"p", u"record": {u"pose": {
            u"version": version, u"regions": {} if version == 3 else {u"full_body": {}},
            u"scope": {u"kind": kind, u"posed": [u"b%d" % i for i in range(72)], u"label": u"Full body",
                       u"root_translation": u"included"},
            u"engine": {u"rule": u"direct_fk_v1", u"revision": 1, u"carried_rule": None}}}}

    def selected_pose(self):
        return self.item

    def pose_ui_state(self, item):
        return {u"buttons": {u"apply_pose": self.apply_pose_button.enabled},
                u"apply_mode": u"direct" if self.apply_pose_button.enabled else None, u"summary": [u"s"]}


def run_ui(folder, window, label="UI-A", mode=u"qualification"):
    cpm = types.ModuleType("chadchan3d_cpm_app")
    cpm.PROD_APP_ATTR = "_slot"
    cpm.PROD_POSE_RECOVERY_BLOCK = [None]
    cpm.PROD_POSE_REGISTRY_MODE = mode
    cpm.__chadchan3d_cpm_build_sha256__ = "b" * 64
    cpm.prod_scope_info = lambda record: {u"rows": [[u"Saved scope:", u"Full body"]], u"bones": [],
                                          u"engine": u"direct_fk_v1 revision 1"}
    app = type("App", (), {"_slot": window})()
    qtgui = types.ModuleType("PySide.QtGui")
    qtgui.QApplication = type("QApplication", (), {"instance": staticmethod(lambda: app)})
    pyside = types.ModuleType("PySide")
    pyside.QtGui = qtgui
    saved = dict((k, sys.modules.get(k)) for k in ("chadchan3d_cpm_app", "PySide", "PySide.QtGui"))
    sys.modules.update({"chadchan3d_cpm_app": cpm, "PySide": pyside, "PySide.QtGui": qtgui})
    try:
        return capture(lambda: exec_file(UI, {"__name__": "__ef1_ui__", "EF1_DIR": folder, "EF1_UI": label}))
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class UITests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ef1ui")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_a_version_3_full_body_pose_is_recorded_without_clicking(self):
        win = FakeWindow()
        printed = run_ui(self.dir, win)
        data = load(os.path.join(self.dir, "observations", "UI-A.json"))
        self.assertEqual((data["selected"]["version"], data["selected"]["scope_kind"], data["selected"]["posed"],
                          data["apply_button_enabled"], data["pose_info"]["engine"], data["registry_mode"]),
                         (3, "full_body", 72, True, "direct_fk_v1 revision 1", "qualification"))
        self.assertEqual(win.apply_pose_button.clicks, 0)
        if PY3:
            self.assertIn("version 3 Full body (72 bones), Apply Pose enabled: OK", printed)

    def test_a_selected_parts_disabled_or_production_state_reports_stop(self):
        for i, (win, mode) in enumerate(((FakeWindow(kind=u"selected_parts"), u"qualification"),
                                         (FakeWindow(enabled=False), u"production"))):
            printed = run_ui(self.dir, win, ("UI-A", "UI-B")[i], mode)
            if PY3:
                self.assertIn("STOP", printed)

    def test_taken_once_and_labels_bounded(self):
        run_ui(self.dir, FakeWindow())
        self.assertRaises(RuntimeError, run_ui, self.dir, FakeWindow())
        self.assertRaises(RuntimeError, run_ui, self.dir, FakeWindow(), "UI-C")


# --- ef1_tool (Python 3) -------------------------------------------------------------------------------------------

def config(folder, **paths):
    with open(os.path.join(ROOT, "ef1.template.json"), "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    c["paths"].update(Q=os.path.join(folder, "Q"), REPO=REPO, GAME=folder, SESSIONS=folder,
                      LIBRARY=os.path.join(folder, "library"))
    c["paths"].update(paths)
    path = os.path.join(folder, "ef1.json")
    with open(path, "wb") as f:
        f.write(json.dumps(c).encode("utf-8"))
    return path, c


HEAD = b"<!-- dmx encoding binary 5 format sfm_session 20 -->\n"
STARTER = HEAD + b"DmElement session DmeFilmClip DmeTrack"
CHARACTER = HEAD + b"DmeFilmClip DmeAnimationSet DmeGameModel DmeChannel models/player/engineer.mdl"

if PY3:
    class ToolTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="ef1tool")
            os.makedirs(os.path.join(self.dir, "Q"))
            self.saved_running = TOOL.T.sfm_running
            TOOL.T.sfm_running = lambda: None

        def tearDown(self):
            TOOL.T.sfm_running = self.saved_running
            shutil.rmtree(self.dir, True)

        def test_build_derives_the_pinned_qualification_cpm_in_one_line(self):
            path, c = config(self.dir)
            capture(lambda: TOOL.cmd_build(TOOL.S.load(path)))
            ids = TOOL.T.read_json(os.path.join(self.dir, "Q", "staged", "IDENTITIES.json"))
            self.assertEqual(ids["qualification_cpm_sha256"], c["pins"]["qualification_cpm_sha256"])
            self.assertEqual((ids["line"], ids["changed_line"]), (u'PROD_POSE_REGISTRY_MODE = u"qualification"', 42118))
            self.assertEqual((ids["wrapper_sha256"], ids["ui_smoke_sha256"], ids["comparator_sha256"]),
                             (TOOL.T.sha(WRAPPER), TOOL.T.sha(UI), TOOL.T.sha(TOOL.comparator())))
            self.assertEqual(ids["expected_header_sha256"], c["pins"]["expected_header_sha256"])

        def test_build_refuses_a_wrong_qualification_pin(self):
            path, c = config(self.dir)
            c["pins"]["qualification_cpm_sha256"] = "0" * 64
            with open(path, "wb") as f:
                f.write(json.dumps(c).encode("utf-8"))
            self.assertRaises(SystemExit, lambda: capture(lambda: TOOL.cmd_build(TOOL.S.load(path))))
            self.assertFalse(os.path.exists(os.path.join(self.dir, "Q", "staged")))

        def test_the_template_refuses_until_filled_and_the_reused_tool_carries_this_kit(self):
            self.assertRaises(SystemExit, TOOL.S.load, os.path.join(ROOT, "ef1.template.json"))
            c = TOOL.S.load(config(self.dir)[0])
            self.assertEqual((TOOL.S.FORMAT, TOOL.S.SESSIONS, TOOL.S.DESTINATION),
                             ("F01-EF1-config-v1", (), "ef1_destination.dmx"))
            self.assertEqual((TOOL.S.wrapper(c), TOOL.S.ui_smoke(c)), (WRAPPER, UI))
            self.assertEqual(c["character_dir"], "engineer--" + sha_bytes(ENGINEER.encode("ascii"))[:12])

        def sessions(self, files):
            q = os.path.join(self.dir, "Q")
            for d in ("sessions", "evidence", "pre_run"):
                if not os.path.isdir(os.path.join(q, d)):
                    os.makedirs(os.path.join(q, d))
            for name, data in files.items():
                with open(os.path.join(q, "sessions", name), "wb") as f:
                    f.write(data)
            return TOOL.S.load(config(self.dir)[0])

        def test_inspect_pins_both_character_sessions_and_records_autosaves(self):
            c = self.sessions({"ef1_source.dmx": CHARACTER, "EF1_Destination.dmx": CHARACTER + b" posed",
                               "ef1_source.autosave": CHARACTER})
            capture(lambda: TOOL.cmd_inspect(c))
            pins = TOOL.T.read_json(os.path.join(self.dir, "Q", "evidence", "destination.json"))
            self.assertEqual((pins["source_name"], pins["destination_name"]), ("ef1_source.dmx", "EF1_Destination.dmx"))
            self.assertEqual((pins["source_sha256"], pins["destination_sha256"]),
                             (sha_bytes(CHARACTER), sha_bytes(CHARACTER + b" posed")))
            self.assertEqual([r["name"] for r in pins["autosaves_at_inspect"]], ["ef1_source.autosave"])

        def test_inspect_refuses_a_starter_identical_or_unexpected_file(self):
            for files in ({"ef1_source.dmx": STARTER, "ef1_destination.dmx": CHARACTER},
                          {"ef1_source.dmx": CHARACTER, "ef1_destination.dmx": CHARACTER},
                          {"ef1_source.dmx": CHARACTER, "ef1_destination.dmx": CHARACTER + b"x", "notes.txt": b"n"},
                          {"ef1_source.dmx": CHARACTER}):
                shutil.rmtree(os.path.join(self.dir, "Q"))
                os.makedirs(os.path.join(self.dir, "Q"))
                c = self.sessions(files)
                self.assertRaises(SystemExit, lambda: capture(lambda: TOOL.cmd_inspect(c)))
                self.assertFalse(os.path.exists(os.path.join(self.dir, "Q", "evidence", "destination.json")))

        def test_restore_moves_a_new_engineer_folder_into_evidence_and_removes_it(self):
            c = self.sessions({})
            char = os.path.join(c["paths"]["LIBRARY"], "Characters", c["character_dir"])
            os.makedirs(os.path.join(char, "Poses"))
            for rel, data in (("character.json", b"{}"), ("library_meta.json", b"[]"),
                              (os.path.join("Poses", "EF1 Body--a1.json"), b"pose")):
                with open(os.path.join(char, rel), "wb") as f:
                    f.write(data)
            TOOL.T.write_json(os.path.join(self.dir, "Q", "pre_run", "pre.json"), {"character_dir_existed": False})

            def fake_s3_restore(cfg):               # the S3 restore moves the Poses folder into evidence
                dst = os.path.join(self.dir, "Q", "evidence", "library_poses", cfg["character_dir"])
                shutil.copytree(os.path.join(char, "Poses"), dst)
                shutil.rmtree(os.path.join(char, "Poses"))
                return 0
            saved = TOOL.S.cmd_restore
            TOOL.S.cmd_restore = fake_s3_restore
            try:
                self.assertEqual(capture(lambda: self.assertEqual(TOOL.cmd_restore(c), 0)) is not None, True)
            finally:
                TOOL.S.cmd_restore = saved
            self.assertFalse(os.path.exists(char))
            moved = TOOL.T.read_json(os.path.join(self.dir, "Q", "evidence", "library_character.json"))["moved"]
            self.assertEqual(sorted(m["file"] for m in moved), ["character.json", "library_meta.json"])
            ev = os.path.join(self.dir, "Q", "evidence", "library_character", c["character_dir"], "character.json")
            with open(ev, "rb") as f:
                self.assertEqual(f.read(), b"{}")

        def test_pre_refuses_when_the_engineer_folder_exists_and_changes_nothing(self):
            c = TOOL.S.load(config(self.dir)[0])
            os.makedirs(os.path.join(c["paths"]["LIBRARY"], "Characters", c["character_dir"]))
            self.assertRaises(SystemExit, lambda: capture(lambda: TOOL.cmd_pre(c)))
            self.assertEqual(os.listdir(os.path.join(self.dir, "Q")), [])


# --- ef1_compare on a synthetic run (Python 3) ---------------------------------------------------------------------

T_CHAN = 50000
QUAL = "q" * 64
CHAR = "engineer--6111c38a013f"
FLEX = ["happySmall", "mad", "AE"]


def qz(deg):
    r = math.radians(deg) / 2.0
    return [0.0, 0.0, math.sin(r), math.cos(r)]


class Scene(object):
    """One Engineer instance: model placement, every bone's local transform (a flat hierarchy under the model, so the
    world transform is model * local), channel keys, controls, Undo state and the outside digest, observed in the S0
    form the comparator reads."""

    def __init__(self, pid, document, model_pos, model_deg, body_deg, root_pos, flex=0.0):
        self.pid, self.document, self.mode, self.cpm, self.outside = pid, document, "Motion Editor", QUAL, "o" * 64
        self.model = (list(model_pos), qz(model_deg))
        self.local = dict((b, ([0.5 * i, 1.0, 2.0], qz(body_deg + i % 7))) for i, b in enumerate(C.BONES))
        self.local[C.ROOT] = (list(root_pos), qz(body_deg))
        self.flex = dict((n, flex if n == "happySmall" else 0.0) for n in FLEX)
        self.keys = {}
        for b in C.BONES:
            self.keys[b + "_o"] = [[0, self.local[b][1]]]
            self.keys[b + "_p"] = [[0, self.local[b][0]]]
        self.keys["rootTransform_p"] = [[0, self.model[0]]]
        self.keys["rootTransform_o"] = [[0, self.model[1]]]
        for n in FLEX:
            self.keys[n + "_flex_channel"] = [[0, self.flex[n]]]
        self.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Modify Camera", "redo_desc": ""}
        self.meta = dict((n, {"curveinfo": {"status": "READ", "value": None}}) for n in self.keys)

    def key(self, name, value):
        keys = self.keys[name]
        at = [k for k in keys if k[0] == T_CHAN]
        if at:
            at[0][1] = copy.deepcopy(value)
        else:
            keys.append([T_CHAN, copy.deepcopy(value)])
            keys.sort(key=lambda k: k[0])

    def set_bone(self, name, pos=None, q=None):
        p0, q0 = self.local[name]
        self.local[name] = (list(pos) if pos is not None else p0, list(q) if q is not None else q0)
        if q is not None:
            self.key(name + "_o", q)
        if pos is not None:
            self.key(name + "_p", pos)

    def pose(self, deg, root_pos):
        for i, b in enumerate(C.BONES):
            self.set_bone(b, q=qz(deg + 3 * (i % 5)))
        self.set_bone(C.ROOT, pos=root_pos)

    def apply(self, record):
        """As CPM's engine does (replay of EC-1): every bone's orientation, the root's saved translation, and every
        other bone's own position, all keyed at the mapped tick."""
        orc = record["pose"]["oracle"]["bones"]
        for b in C.BONES:
            self.set_bone(b, pos=orc[b]["local_position"] if b == C.ROOT else self.local[b][0],
                          q=orc[b]["local_orientation"])
        self.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Apply Pose EF1 Body", "redo_desc": ""}

    def snapshot(self):
        return copy.deepcopy((self.keys, self.local, self.undo, self.flex, self.model, self.meta))

    def restore(self, snap, undo=None):
        self.keys, self.local, self.undo, self.flex, self.model, self.meta = copy.deepcopy(snap)
        if undo is not None:
            self.undo = dict(undo)

    def digest(self):
        return sha_bytes(json.dumps([self.keys, self.undo], sort_keys=True).encode("utf-8"))

    def channel(self, name):
        keys = self.keys[name]
        at = [i for i, k in enumerate(keys) if k[0] == T_CHAN]
        h = int(sha_bytes(name.encode("ascii"))[:6], 16)
        kind = "DmeQuaternionLogLayer" if name.endswith("_o") else "DmeVector3LogLayer"
        layer = {"id": {"handle": h + 2, "type": kind}, "type": kind, "key_count": len(keys),
                 "keys_sha256": sha_bytes(json.dumps([keys, self.meta[name]]).encode("utf-8")),
                 "key_at_mapped": at[0] if at else None, "keys": copy.deepcopy(keys)}
        value = keys[at[0]][1] if at else keys[0][1]
        return {"id": {"name": name, "handle": h, "type": "DmeChannel"}, "binding": {}, "current_ticks": T_CHAN,
                "log": {"handle": h + 1}, "log_fields": copy.deepcopy(self.meta[name]), "layers": [layer],
                "value_at_clock": value, "value_at_mapped": copy.deepcopy(value)}

    def world(self, name):
        return C.compose(self.model, self.local[name])

    def observe(self, label):
        bones = {}
        for i, b in enumerate(C.BONES):
            wp, wq = self.world(b)
            bones[b] = {"index": i, "transform": {}, "dag": i + 1, "parent_bone": None,
                        "local_position": list(self.local[b][0]), "local_orientation": list(self.local[b][1]),
                        "scale": {"status": "READ", "value": 1.0}, "world_position": wp, "world_orientation": wq}
        controls = [{"id": {"name": b}, "attributes": {"valueOrientation": {"status": "READ", "value": self.local[b][1]}}}
                    for b in C.BONES]
        controls.append({"id": {"name": "rootTransform"}, "attributes": {"valuePosition": {
            "status": "READ", "value": self.model[0]}}})
        controls += [{"id": {"name": n}, "attributes": {"value": {"status": "READ", "value": v}}}
                     for n, v in sorted(self.flex.items())]
        d = self.digest()
        session = {"head_seconds": 0.0, "head_ticks": 0, "timeline_mode": {"name": self.mode}, "undo": dict(self.undo),
                   "current_shot": "shot1"}
        state = {"world_position": list(self.model[0]), "world_orientation": list(self.model[1]),
                 "local_position": list(self.model[0]), "local_orientation": list(self.model[1]),
                 "scale": {"status": "ABSENT"}}
        return {"format": "F01-S0-survey-v1", "label": label, "pid": self.pid, "problems": [], "findings": [NO_RIG],
                "document": self.document, "session_before": copy.deepcopy(session), "session_after": session,
                "readonly": {"digest_before": {"sha256": d}, "digest_after": {"sha256": d}, "unchanged": True},
                "shot": {}, "animation_set": {}, "time": {"t_chan": T_CHAN}, "scene": {}, "bones": bones,
                "model": {"state": state}, "rig": {"registrations": [], "handles": {}}, "controls": controls,
                "channels": [self.channel(n) for n in sorted(self.keys)], "operators": [],
                "writer_index": {"destinations": {}, "slave_targets": {}}, "cpm_loaded": {"build_sha256": self.cpm}}


def full_body_record(scene, kind=u"full_body"):
    orc = {}
    for b in C.BONES:
        rp, rq = C.compose(C.invert(scene.model), scene.world(b))
        orc[b] = {"local_position": list(scene.local[b][0]), "local_orientation": list(scene.local[b][1]),
                  "relative_position": rp, "relative_orientation": rq}
    return {"name": u"EF1 Body", "kind": "pose", "pose": {
        "version": 3, "engine": {"rule": "direct_fk_v1", "revision": 1, "carried_rule": None},
        "scope": {"kind": kind, "completeness": "declared_body", "posed": list(C.BONES), "carried": [],
                  "exclusions": [], "root_translation": "included"},
        "structure": {"root": C.ROOT}, "values": {"root_translation": list(scene.local[C.ROOT][0])},
        "oracle": {"frame": "component-boundary", "bones": orc}}}


class Synthetic(object):
    """One complete, correct run; `faults` names the counterexamples to inject."""

    def __init__(self, folder, faults=()):
        self.q, self.faults = folder, set(faults)
        self.lib = os.path.join(folder, "library")
        for d in ("staged", "observations", "sessions", os.path.join("evidence", "logs"),
                  os.path.join("evidence", "library_poses", CHAR), "library"):
            os.makedirs(os.path.join(folder, d))
        self.dump(os.path.join("staged", "IDENTITIES.json"), {"qualification_cpm_sha256": QUAL})
        self.logs, self.ms = {}, 0

    def dump(self, rel, data):
        with open(os.path.join(self.q, rel), "wb") as f:
            f.write(json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))

    def observe(self, scene, step):
        label = C.LABELS[step]
        obs = scene.observe(label)
        side = {"format": "F01-EF1-sidecar-v1", "step": step, "label": label, "mismatch": [],
                "animation_set": "engineer1", "outside": {"sha256": scene.outside}}
        hook = getattr(self, "fault_" + step, None)
        if hook:
            hook(obs, side)
        self.dump(os.path.join("observations", label + ".json"), obs)
        self.dump(os.path.join("observations", label + ".ef1.json"), side)

    def op(self, pid, lines, ms=300):
        log = self.logs.setdefault(pid, [])
        op_id = len([r for r in log if "PROD_OPERATION_BEGIN" in r]) + 1

        def stamp():
            return "2026-11-10T10:%02d:%02d.%03dZ" % (self.ms // 60000, (self.ms // 1000) % 60, self.ms % 1000)
        log.append("%s #%06d s=x w=1 op=%d | PROD_OPERATION_BEGIN id=%d kind=u'Apply Pose' context=None" % (
            stamp(), len(log) + 1, op_id, op_id))
        for text in lines:
            self.ms += ms
            log.append("%s #%06d s=x w=1 op=%d | %s" % (stamp(), len(log) + 1, op_id, text))
        self.ms += 50
        log.append("%s #%06d s=x w=1 op=%d | PROD_OPERATION_END id=%d" % (stamp(), len(log) + 1, op_id, op_id))

    def scoped(self, pid, actions, noop=False, abort=False, verified=True):
        lines = ['PROD_POSE_SCOPE-P1 {"actions": %s, "noop": %s}' % (json.dumps(actions), "true" if noop else "false")]
        if abort:
            lines += ['PROD_POSE_SCOPE-P3-P6-failure {}', 'PROD_POSE_SCOPE-abort-verified {}']
        elif not noop:
            lines += ['PROD_POSE_SCOPE-P6 {"owned": true}',
                      'PROD_POSE_SCOPE-P7-verified {}' if verified else 'PROD_POSE_SCOPE-P7-unverified {}']
        self.op(pid, lines)

    def build(self):
        f = self.faults
        # Process A: the source session (the default Engineer, then the artist's body pose)
        a = Scene(100, "E:/run/sessions/ef1_source.dmx", [48.5, 0.0, -38.4], 180.0, 0.0, [0.0, 0.0, 41.3])
        self.observe(a, "A1")
        a.pose(30.0, [3.0, 4.0, 46.0])
        self.observe(a, "A2")
        rec = full_body_record(a, u"selected_parts" if "wrong_scope" in f else u"full_body")
        if "save_writes" in f:
            a.key("mad_flex_channel", 0.4)
        self.observe(a, "A3")
        # Process B: the destination session after a restart
        pid = 100 if "no_restart" in f else 200
        b = Scene(pid, "E:/run/sessions/ef1_destination.dmx", [90.0, 25.0, -10.0], 225.0, -12.0, [-5.0, 2.0, 38.0],
                  flex=0.7)
        b.pose(-12.0, [-5.0, 2.0, 38.0])                    # the Owner's step-0 posing keyed the destination
        b.key("bip_neck_p", b.local["bip_neck"][0])          # an existing exact position key at the tick
        if "dest_not_distinct" in f:
            b.apply(rec)
            b.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Modify Camera", "redo_desc": ""}
        self.observe(b, "B1")
        base = b.snapshot()
        if "abort_writes" in f:
            b.key("bip_head_o", qz(77.0))
        self.observe(b, "B2")
        self.scoped(pid, {"insert": 0, "update": 145, "none": 0}, abort=True)
        b.restore(base)
        b.apply(rec)
        if "root_not_moved" in f:
            b.set_bone(C.ROOT, pos=base[1][C.ROOT][0])
        if "placement_moved" in f:
            b.model = ([95.0, 25.0, -10.0], b.model[1])
        if "face_changed" in f:
            b.flex["happySmall"] = 0.1
        if "bone_off" in f:
            b.set_bone("bip_knee_L", q=C.K.unit([x + y for x, y in zip(b.local["bip_knee_L"][1], [0.0, 0.0, 0.0005, 0.0])]))
        if "offset_transferred" in f:
            b.set_bone("bip_head", pos=[9.0, 9.0, 9.0])
        if "flex_channel_written" in f:
            b.key("mad_flex_channel", 0.0)
        if "neighbour_key_changed" in f:
            b.keys["bip_head_o"][0][1] = qz(33.0)
        if "extra_key" in f:
            b.keys["bip_toe_R_o"].append([T_CHAN + 100, qz(5.0)])
        if "metadata_changed" in f:
            b.meta["bip_spine_1_o"] = {"curveinfo": {"status": "READ", "value": {"handle": 9}}}
        if "position_key_updated" in f:
            b.set_bone("bip_neck", pos=[p + 0.01 for p in b.local["bip_neck"][0]])
        if "outside_changed" in f:
            b.outside = "x" * 64
        self.observe(b, "B3")
        applied = b.snapshot()
        self.scoped(pid, {"insert": 0, "update": 145, "none": 0}, verified="unverified_log" not in f)
        b.restore(base, {"can_undo": True, "can_redo": True, "undo_desc": "Modify Camera", "redo_desc": "x"})
        if "undo_incomplete" in f:
            b.key("bip_spine_1_o", qz(55.0))
        self.observe(b, "B4")
        b.restore(applied)
        self.observe(b, "B5")
        if "noop_writes" in f:
            b.key("bip_toe_L_o", qz(4.0))
        self.observe(b, "B6")
        self.scoped(pid, {}, noop=True)
        b.mode = "Clip Editor"
        self.observe(b, "B7")
        self.observe(b, "B8")
        self.op(pid, ['PROD_POSE_SCOPE-refused {"code": "editor-mode"}'])
        b.mode = "Motion Editor"
        self.observe(b, "B9")
        b.restore(base, {"can_undo": True, "can_redo": True, "undo_desc": "Modify Camera", "redo_desc": "x"})
        self.observe(b, "B10")
        # UI captures, the record, libraries, logs, restore and session pins
        for label, pid_ in (("UI-A", 100), ("UI-B", pid)):
            self.dump(os.path.join("observations", label + ".json"), {
                "pid": pid_, "cpm_build_sha256": QUAL, "apply_button_enabled": True, "registry_mode": "qualification",
                "recovery_paused": False, "pose_info": {"engine": "direct_fk_v1 revision 1"},
                "selected": {"name": "EF1 Body", "version": 3, "scope_kind": "full_body", "posed": 72}})
        self.dump(os.path.join("evidence", "library_poses", CHAR, u"EF1 Body--a1.json"), rec)
        files = {u"EF1 Body--a1.json": "r" * 64}
        self.dump(os.path.join("evidence", "library_A.json"), {"files": files})
        self.dump(os.path.join("evidence", "library_B.json"), {"files": files})
        for p_, rows in self.logs.items():
            with open(os.path.join(self.q, "evidence", "logs", "CPM - x - pid%d - y - 001.log" % p_), "wb") as fh:
                fh.write(("\n".join(rows) + "\n").encode("utf-8"))
        self.dump(os.path.join("evidence", "restore.json"), {"restored": True})
        pins = {}
        for key, name in (("source", "ef1_source.dmx"), ("destination", "ef1_destination.dmx")):
            data = HEAD + b"DmeAnimationSet DmeGameModel " + name.encode("ascii")
            with open(os.path.join(self.q, "sessions", name), "wb") as fh:
                fh.write(data)
            pins[key + "_name"], pins[key + "_sha256"] = name, sha_bytes(data)
        self.dump(os.path.join("evidence", "destination.json"), pins)
        if "session_saved" in f:
            with open(os.path.join(self.q, "sessions", "ef1_destination.dmx"), "ab") as fh:
                fh.write(b" saved")
        if "autosave" in f:
            with open(os.path.join(self.q, "sessions", "ef1_destination.autosave"), "wb") as fh:
                fh.write(HEAD + b"DmeAnimationSet DmeGameModel")
        if "extra_session_file" in f:
            with open(os.path.join(self.q, "sessions", "ef1_other.dmx"), "wb") as fh:
                fh.write(STARTER)
        if "character_left" in f:
            os.makedirs(os.path.join(self.lib, "Characters", CHAR))
        return self


if PY3:
    class CompareTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="ef1cmp")

        def tearDown(self):
            shutil.rmtree(self.dir, True)

        def verdict(self, faults=(), hook=None):
            q = os.path.join(self.dir, "run%d" % len(os.listdir(self.dir)))
            s = Synthetic(q, faults)
            if hook:
                hook(s)
            s.build()
            c = {"paths": {"Q": q, "LIBRARY": s.lib}, "character_dir": CHAR}
            capture(lambda: C.run(c))
            return load(os.path.join(q, "evidence", "EF1_VERDICT.json"))

        def test_a_complete_correct_run_passes(self):
            v = self.verdict()
            self.assertEqual((v["verdict"], v["failed"]), ("PASS", []))
            self.assertGreater(len(v["checks"]), 90)
            self.assertEqual(v["performance"]["class"], "responsive")
            self.assertEqual(v["findings"], [])

        def test_an_autosave_copy_is_a_finding_not_a_failure(self):
            v = self.verdict(("autosave",))
            self.assertEqual((v["verdict"], v["failed"]), ("PASS", []))
            self.assertTrue(any("autosave" in x for x in v["findings"]))

        def test_counterexamples_fail(self):
            expect = {"root_not_moved": "apply.body_root_takes_the_saved_translation",
                      "placement_moved": "apply.model_placement_unchanged",
                      "face_changed": "apply.facial_and_placement_controls_unchanged",
                      "bone_off": "apply.every_bone_takes_the_saved_orientation",
                      "offset_transferred": "apply.non_root_offsets_are_the_destinations_own",
                      "flex_channel_written": "apply.only_skeletal_channels_changed",
                      "neighbour_key_changed": "apply.neighbouring_keys_layers_and_metadata_preserved",
                      "extra_key": "apply.neighbouring_keys_layers_and_metadata_preserved",
                      "metadata_changed": "apply.neighbouring_keys_layers_and_metadata_preserved",
                      "position_key_updated": "apply.non_root_position_keys_inserted_only_where_missing",
                      "outside_changed": "apply.unrelated_animation_unchanged",
                      "undo_incomplete": "undo.restores_the_destination_baseline",
                      "noop_writes": "repeat.true_noop",
                      "abort_writes": "abort.verified_nothing_changed",
                      "no_restart": "process.restart_between_save_and_apply",
                      "save_writes": "save.writes_nothing_to_the_scene",
                      "wrong_scope": "save.is_version_3_full_body_of_all_72_bones",
                      "unverified_log": "log.no_recovery_or_uncertainty",
                      "dest_not_distinct": "distinct.destination_body_differs_from_the_pose",
                      "session_saved": "sessions.destination_not_saved_during_the_run",
                      "extra_session_file": "sessions.no_unexpected_files",
                      "character_left": "restore.engineer_character_folder_removed"}
            for fault, check in sorted(expect.items()):
                v = self.verdict((fault,))
                self.assertEqual(v["verdict"], "FAIL", fault)
                self.assertIn(check, v["failed"], (fault, v["failed"][:6]))

        def test_a_wrong_build_a_problem_or_a_second_finding_fails_its_step(self):
            def wrong_cpm(s):
                def fault(obs, side):
                    obs["cpm_loaded"]["build_sha256"] = "w" * 64
                s.fault_B3 = fault

            def problem(s):
                def fault(obs, side):
                    obs["problems"] = ["channel x unreadable"]
                s.fault_A2 = fault

            def finding(s):
                def fault(obs, side):
                    obs["findings"] = [NO_RIG, "bone x has 2 scene elements"]
                s.fault_B1 = fault
            for hook, check in ((wrong_cpm, "cpm.B3"), (problem, "valid.A2"), (finding, "findings.B1_only_the_no_rig_note")):
                self.assertIn(check, self.verdict(hook=hook)["failed"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
