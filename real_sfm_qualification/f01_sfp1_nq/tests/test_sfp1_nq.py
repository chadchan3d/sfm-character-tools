# -*- coding: ascii -*-
"""Offline tests of the F-01 SFP-1 Selected parts native qualification kit.

- The observer wrapper against the S0 suite's fake SFM (Python 2.7 and 3): it runs the pinned S0 observer unchanged,
  writes the observation and its sidecar, never mutates the scene, refuses a repeated or unknown step, reports a
  step whose shot differs, and its step table equals the comparator's.
- The UI capture against a fake CPM window (Python 2.7 and 3): read-only, records a version 3 Selected parts pose and
  its Pose Info rows, reports STOP otherwise, never repeats.
- sfp1_tool (Python 3): build derives the pinned qualification CPM from the real qualified candidate (read from its
  pinned Git commit, since HEAD's CPM has moved on) in exactly one line; a wrong qualification pin or an unpinned
  candidate refuses; inspect pins the prepared sessions and refuses unprepared
  or duplicated ones; the reused S3 tool carries this kit's identity.
- sfp1_compare (Python 3): a complete synthetic run that meets every Expected result is PASS (with and without the
  optional prop process, prop applied or refused), and each counterexample is FAIL.

Run: python -I test_sfp1_nq.py   (SFM's Python 2.7: python -E -s -B test_sfp1_nq.py runs the wrapper and UI tests)
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
WRAPPER = os.path.join(ROOT, "observer", "F01_SFP1_Observe.py")
UI = os.path.join(ROOT, "observer", "F01_SFP1_UIState.py")
sys.path.insert(0, os.path.join(RSQ, "f01_full_body_s0", "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fake_sfm_s0 as F  # noqa: E402

PY3 = sys.version_info[0] >= 3
if PY3:
    import sfp1_compare as C  # noqa: E402
    import sfp1_tool as TOOL  # noqa: E402


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

def run_wrapper(folder, step):
    world, S, sfm, vs = F.install()
    sys.modules["sfmApp"], sys.modules["vs"] = sfm, vs
    printed = capture(lambda: exec_file(WRAPPER, {"__name__": "__sfp1__", "SFP1_DIR": folder, "SFP1_REPO": REPO,
                                                  "SFP1_STEP": step}))
    return world, printed


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="sfp1test")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_observes_read_only_and_writes_the_sidecar(self):
        world, printed = run_wrapper(self.dir, "A1")
        self.assertEqual(world.mutations, [])
        obs = load(os.path.join(self.dir, "observations", "S0-01.json"))
        side = load(os.path.join(self.dir, "observations", "S0-01.sfp1.json"))
        self.assertEqual((side["step"], side["label"], side["format"]), ("A1", "S0-01", "F01-SFP1-sidecar-v1"))
        self.assertTrue(obs["readonly"]["unchanged"])
        self.assertEqual((len(side["outside"]["sha256"]), side["outside"]["unreadable"], side["mismatch"]), (64, 0, []))
        with io.open(os.path.join(RSQ, "f01_full_body_s0", "observer", "F01_S0_Survey.py"), "rb") as f:
            self.assertEqual(side["observer_sha256"], sha_bytes(f.read()))
        if PY3:
            self.assertIn("SFP1 STEP A1 (S0-01): OK", printed)

    def test_a_repeated_step_is_refused(self):
        run_wrapper(self.dir, "A1")
        self.assertRaises(RuntimeError, run_wrapper, self.dir, "A1")

    def test_a_wrong_shot_is_reported(self):
        world, printed = run_wrapper(self.dir, "B2")
        side = load(os.path.join(self.dir, "observations", "S0-09.sfp1.json"))
        self.assertTrue(any("shot" in m for m in side["mismatch"]))
        if PY3:
            self.assertIn("MISMATCH - STOP", printed)

    def test_unknown_step_refused(self):
        self.assertRaises(RuntimeError, run_wrapper, self.dir, "Z9")

    def test_step_table_matches_the_comparator(self):
        with io.open(WRAPPER, "rb") as f:
            text = f.read().decode("ascii")
        table = dict(re.findall(r'"([ABC]\d+)": \("(S0-\d\d)"', text))
        self.assertEqual(len(table), 26)
        if PY3:
            self.assertEqual(table, C.LABELS)


# --- the UI capture (Python 2.7 and 3) -----------------------------------------------------------------------------

class FakeButton(object):
    def __init__(self, enabled):
        self.enabled, self.clicks = enabled, 0

    def isEnabled(self):
        return self.enabled


class FakeWindow(object):
    def __init__(self, enabled=True, version=3, kind=u"selected_parts"):
        self.apply_pose_button = FakeButton(enabled)
        self.pose_recovery_blocked = False
        self.item = {u"name": u"SFP1 Grip", u"preset_id": u"p", u"record": {u"pose": {
            u"version": version, u"regions": {} if version == 3 else {u"left_arm": {}},
            u"scope": {u"kind": kind, u"posed": [u"bip_index_0_l"], u"label": u"Selected parts (15)"},
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
    cpm.prod_scope_info = lambda record: {u"rows": [[u"Saved scope:", u"Selected parts"]], u"bones": [],
                                          u"engine": u"direct_fk_v1 revision 1"}
    app = type("App", (), {"_slot": window})()
    qtgui = types.ModuleType("PySide.QtGui")
    qtgui.QApplication = type("QApplication", (), {"instance": staticmethod(lambda: app)})
    pyside = types.ModuleType("PySide")
    pyside.QtGui = qtgui
    saved = dict((k, sys.modules.get(k)) for k in ("chadchan3d_cpm_app", "PySide", "PySide.QtGui"))
    sys.modules.update({"chadchan3d_cpm_app": cpm, "PySide": pyside, "PySide.QtGui": qtgui})
    try:
        return capture(lambda: exec_file(UI, {"__name__": "__sfp1_ui__", "SFP1_DIR": folder, "SFP1_UI": label}))
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class UITests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="sfp1ui")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_a_version_3_selected_parts_pose_is_recorded_without_clicking(self):
        win = FakeWindow()
        printed = run_ui(self.dir, win)
        data = load(os.path.join(self.dir, "observations", "UI-A.json"))
        self.assertEqual((data["selected"]["version"], data["selected"]["scope_kind"], data["apply_button_enabled"],
                          data["pose_info"]["engine"], data["registry_mode"]),
                         (3, "selected_parts", True, "direct_fk_v1 revision 1", "qualification"))
        self.assertEqual(win.apply_pose_button.clicks, 0)
        if PY3:
            self.assertIn("version 3 Selected parts, Apply Pose enabled: OK", printed)

    def test_a_legacy_or_disabled_or_production_state_reports_stop(self):
        for i, (win, mode) in enumerate(((FakeWindow(version=1), u"qualification"),
                                         (FakeWindow(enabled=False), u"qualification"),
                                         (FakeWindow(), u"production"))):
            printed = run_ui(self.dir, win, ("UI-A", "UI-B", "UI-C")[i], mode)
            if PY3:
                self.assertIn("STOP", printed)

    def test_taken_once_and_labels_bounded(self):
        run_ui(self.dir, FakeWindow())
        self.assertRaises(RuntimeError, run_ui, self.dir, FakeWindow())
        self.assertRaises(RuntimeError, run_ui, self.dir, FakeWindow(), "UI-Z")


# --- sfp1_tool (Python 3) ------------------------------------------------------------------------------------------

# SFP-1 NQ1 is closed and tied to its natively qualified candidate 2d791dec..., not to whatever CPM HEAD holds (the
# CPM has moved on since). The kit's build is therefore tested on the exact qualified source, read as the raw Git blob
# from the kit's own commit (7f62c62, whose CPM is 2d791dec...). The tool's own hash checks (candidate and derived
# qualification build b58ae9ba...) are unchanged and still decide.
QUALIFIED_CPM_COMMIT = "7f62c62722f388e45fa66c00bd00e4b958bde918"
QUALIFIED_CPM_REL = "cpm/app/SFM_Character_Preset_Manager.py"
_QUALIFIED = []


def qualified_candidate():
    """The qualified candidate's exact bytes from QUALIFIED_CPM_COMMIT, in a private temporary folder; raises unless
    they hash to the template's candidate pin."""
    if not _QUALIFIED:
        import atexit
        import subprocess
        raw = subprocess.check_output(["git", "-C", REPO, "cat-file", "blob",
                                       "%s:%s" % (QUALIFIED_CPM_COMMIT, QUALIFIED_CPM_REL)])
        with open(os.path.join(ROOT, "sfp1.template.json"), "rb") as f:
            pin = json.loads(f.read().decode("utf-8"))["pins"]["candidate_cpm_sha256"]
        if sha_bytes(raw) != pin:
            raise AssertionError("the CPM at %s is %s, not the qualified %s" % (QUALIFIED_CPM_COMMIT, sha_bytes(raw),
                                                                                 pin))
        where = tempfile.mkdtemp(prefix="sfp1qualcpm")
        atexit.register(shutil.rmtree, where, True)
        path = os.path.join(where, "SFM_Character_Preset_Manager.py")
        with open(path, "wb") as f:
            f.write(raw)
        _QUALIFIED.append(path)
    return _QUALIFIED[0]


def config(folder, **paths):
    with open(os.path.join(ROOT, "sfp1.template.json"), "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    c["paths"].update(Q=os.path.join(folder, "Q"), REPO=REPO, GAME=folder, SESSIONS=folder, LIBRARY=folder,
                      R2_FIXTURE=os.path.join(folder, "fixture.dmx"), LEGACY_POSE=os.path.join(folder, "fixture.dmx"),
                      CANDIDATE=qualified_candidate())
    c["paths"].update(paths)
    path = os.path.join(folder, "sfp1.json")
    with open(path, "wb") as f:
        f.write(json.dumps(c).encode("utf-8"))
    return path, c


if PY3:
    class ToolTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="sfp1tool")
            os.makedirs(os.path.join(self.dir, "Q"))
            with open(os.path.join(self.dir, "fixture.dmx"), "wb") as f:
                f.write(b"fixture")

        def tearDown(self):
            shutil.rmtree(self.dir, True)

        def test_build_derives_the_pinned_qualification_cpm_in_one_line(self):
            path, c = config(self.dir)
            TOOL.cmd_build(TOOL.S.load(path))
            ids = TOOL.T.read_json(os.path.join(self.dir, "Q", "staged", "IDENTITIES.json"))
            self.assertEqual(ids["qualification_cpm_sha256"], c["pins"]["qualification_cpm_sha256"])
            self.assertEqual(ids["line"], u'PROD_POSE_REGISTRY_MODE = u"qualification"')
            self.assertEqual((ids["wrapper_sha256"], ids["ui_smoke_sha256"], ids["comparator_sha256"]),
                             (TOOL.T.sha(WRAPPER), TOOL.T.sha(UI), TOOL.T.sha(TOOL.comparator())))

        def test_build_refuses_a_wrong_qualification_pin_or_candidate(self):
            path, c = config(self.dir)
            c["pins"]["qualification_cpm_sha256"] = "0" * 64
            with open(path, "wb") as f:
                f.write(json.dumps(c).encode("utf-8"))
            self.assertRaises(SystemExit, TOOL.cmd_build, TOOL.S.load(path))
            self.assertFalse(os.path.exists(os.path.join(self.dir, "Q", "staged")))
            cand = os.path.join(self.dir, "cand.py")
            shutil.copyfile(qualified_candidate(), cand)
            with open(cand, "ab") as f:
                f.write(b"\n# changed\n")
            path, c = config(self.dir, CANDIDATE=cand)
            self.assertRaises(SystemExit, TOOL.cmd_build, TOOL.S.load(path))

        def test_the_template_refuses_until_filled(self):
            self.assertRaises(SystemExit, TOOL.S.load, os.path.join(ROOT, "sfp1.template.json"))

        def test_the_reused_tool_carries_this_kits_identity(self):
            path, c = config(self.dir)
            c = TOOL.S.load(path)
            self.assertEqual((TOOL.S.FORMAT, TOOL.S.SESSIONS, TOOL.S.DESTINATION),
                             ("F01-SFP1-config-v1", ("SFP1_SOURCE.dmx", "SFP1_PREPARATION.dmx"), "SFP1_DESTINATION.dmx"))
            self.assertEqual((TOOL.S.wrapper(c), TOOL.S.ui_smoke(c)), (WRAPPER, UI))

        def inspect_setup(self, dest=b"prepared", prop=None):
            q = os.path.join(self.dir, "Q")
            os.makedirs(os.path.join(q, "sessions"))
            os.makedirs(os.path.join(q, "evidence"))
            for name in ("SFP1_SOURCE.dmx", "SFP1_PREPARATION.dmx"):
                shutil.copyfile(os.path.join(self.dir, "fixture.dmx"), os.path.join(q, "sessions", name))
            if dest is not None:
                with open(os.path.join(q, "sessions", "SFP1_DESTINATION.dmx"), "wb") as f:
                    f.write(dest)
            if prop is not None:
                with open(os.path.join(q, "sessions", "SFP1_PROP.dmx"), "wb") as f:
                    f.write(prop)
            path, c = config(self.dir)
            c = TOOL.S.load(path)
            c["pins"]["r2_fixture_sha256"] = TOOL.T.sha(os.path.join(self.dir, "fixture.dmx"))
            TOOL.T.sfm_running = lambda: None
            return c

        def test_inspect_pins_the_prepared_sessions(self):
            c = self.inspect_setup(prop=b"with prop")
            capture(lambda: TOOL.cmd_inspect(c))
            pins = TOOL.T.read_json(os.path.join(self.dir, "Q", "evidence", "destination.json"))
            self.assertEqual((pins["destination_sha256"], pins["prop_sha256"]),
                             (sha_bytes(b"prepared"), sha_bytes(b"with prop")))

        def test_inspect_without_prop_skips_process_c(self):
            c = self.inspect_setup()
            capture(lambda: TOOL.cmd_inspect(c))
            self.assertIsNone(TOOL.T.read_json(os.path.join(self.dir, "Q", "evidence", "destination.json"))[
                "prop_sha256"])

        def test_inspect_refuses_unprepared_or_duplicate_sessions(self):
            for dest, prop in ((None, None), (b"fixture", None), (b"prepared", b"prepared")):
                shutil.rmtree(os.path.join(self.dir, "Q"))
                os.makedirs(os.path.join(self.dir, "Q"))
                c = self.inspect_setup(dest, prop)
                self.assertRaises(SystemExit, lambda: capture(lambda: TOOL.cmd_inspect(c)))


# --- sfp1_compare on a synthetic run (Python 3) --------------------------------------------------------------------

FINGERS = sorted("bip_%s_%d_l" % (f, i) for f in ("index", "middle", "ring", "pinky", "thumb") for i in range(3))
OTHER = ["bip_pelvis", "bip_head", "jaw", "bip_UpperArm_l", "bip_lowerArm_l", "bip_hand_l"]
EXTRA = ["Smile_flex_channel", "jaw_o", "rig_root_p", "Hand_l_p", "Hand_l_o", "Elbow_l_p"]
T_CHAN = 50416
QUAL = "q" * 64
CHAR = "krystal2020--7d2aee52ef3a"


def qz(deg):
    r = math.radians(deg) / 2.0
    return [0.0, 0.0, math.sin(r), math.cos(r)]


class Scene(object):
    """One shot's Krystal: finger and other bone angles, every channel's keys, controls, Undo state and the outside
    digest. Observations are produced in the S0 observation form the comparator reads."""

    def __init__(self, pid, document, shot, head, finger_deg, hand_deg):
        self.pid, self.document, self.shot, self.head = pid, document, shot, head
        self.mode, self.cpm, self.outside = "Motion Editor", QUAL, "o" * 64
        self.angles = dict((b, float(finger_deg)) for b in FINGERS)
        self.angles.update(dict((b, 3.0) for b in OTHER))
        self.angles["bip_hand_l"] = float(hand_deg)
        self.keys = dict((n, [[1000, self.value(n, 0.0)]]) for n in [b + s for b in FINGERS for s in ("_o", "_p")] +
                         EXTRA)
        self.controls = {"Smile": 0.25, "eyes_rightleft": 0.6}
        self.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Modify Head Time", "redo_desc": ""}

    @staticmethod
    def value(name, deg):
        return [1.0, 0.5, -0.25] if name.endswith("_p") else qz(deg)

    def digest(self):
        return sha_bytes(json.dumps([self.keys, self.undo], sort_keys=True).encode("utf-8"))

    def key(self, name, value):
        keys = self.keys[name]
        at = [k for k in keys if k[0] == T_CHAN]
        if at:
            at[0][1] = copy.deepcopy(value)
        else:
            keys.append([T_CHAN, copy.deepcopy(value)])
            keys.sort(key=lambda k: k[0])

    def pose_fingers(self, deg):
        for b in FINGERS:
            self.angles[b] = float(deg)
            self.key(b + "_o", qz(deg))

    def apply(self, record, desc):
        for b in FINGERS:
            self.angles[b] = record["_deg"]
            self.key(b + "_o", qz(record["_deg"]))
            self.key(b + "_p", [1.0, 0.5, -0.25])
        self.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Apply Pose " + desc, "redo_desc": ""}

    def apply_legacy(self):
        self.angles["bip_hand_l"] += 30.0
        for n in ("Hand_l_p", "Hand_l_o", "Elbow_l_p"):
            self.key(n, self.value(n, 33.0) if n.endswith("_o") else [2.0, 1.0, 0.0])
        self.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Apply Pose NQ1 Pose A", "redo_desc": ""}

    def snapshot(self):
        return copy.deepcopy((self.keys, self.angles, self.undo, self.controls))

    def restore(self, snap, undo=None):
        self.keys, self.angles, self.undo, self.controls = copy.deepcopy(snap)
        if undo is not None:
            self.undo = dict(undo)

    def channel(self, name):
        keys = self.keys[name]
        at = [i for i, k in enumerate(keys) if k[0] == T_CHAN]
        layer = {"key_count": len(keys), "keys_sha256": sha_bytes(json.dumps(keys).encode("utf-8")),
                 "key_at_mapped": at[0] if at else None, "keys": copy.deepcopy(keys)}
        value = keys[at[0]][1] if at else keys[0][1]
        return {"id": {"name": name, "handle": 1, "type": "DmeChannel"}, "binding": {}, "current_ticks": T_CHAN,
                "log": {}, "layers": [layer], "value_at_clock": value, "value_at_mapped": copy.deepcopy(value)}

    def observe(self, label, step):
        bones = {}
        for name, deg in self.angles.items():
            q = qz(deg)
            bones[name] = {"index": 0, "transform": {}, "dag": 1, "parent_bone": None, "local_position": [1.0, 2.0, 3.0],
                           "local_orientation": q, "scale": {"status": "READ", "value": 1.0},
                           "world_position": [1.0, 2.0, 3.0], "world_orientation": q}
        d = self.digest()
        session = {"head_seconds": self.head, "head_ticks": int(self.head * 10000), "timeline_mode": {"name": self.mode},
                   "undo": dict(self.undo), "current_shot": self.shot}
        obs = {"format": "F01-S0-survey-v1", "label": label, "pid": self.pid, "problems": [],
               "document": self.document, "session_before": copy.deepcopy(session), "session_after": session,
               "readonly": {"digest_before": {"sha256": d}, "digest_after": {"sha256": d}, "unchanged": True},
               "shot": {}, "animation_set": {}, "time": {"t_chan": T_CHAN}, "scene": {}, "bones": bones,
               "model": {"state": {"world_position": [1.0, 2.0, 3.0], "world_orientation": qz(0.0),
                                   "local_position": [1.0, 2.0, 3.0], "local_orientation": qz(0.0),
                                   "scale": {"status": "READ", "value": 1.0}}},
               "rig": {"handles": {"rig_root": {"id": {}, "parents": [1], "local_position": [5.0, 0.0, 0.0],
                                                "local_orientation": qz(0.0), "world_position": [5.0, 0.0, 0.0],
                                                "world_orientation": qz(0.0)}}},
               "controls": [{"id": {"name": n}, "attributes": {"value": {"status": "READ", "value": v}}}
                            for n, v in sorted(self.controls.items())],
               "channels": [self.channel(n) for n in sorted(self.keys)], "operators": [],
               "writer_index": {"destinations": {}, "slave_targets": {}}, "cpm_loaded": {"build_sha256": self.cpm}}
        side = {"format": "F01-SFP1-sidecar-v1", "step": step, "label": label, "mismatch": [],
                "outside": {"sha256": self.outside}}
        return obs, side


def scoped_record(name, deg, posed=None):
    orc = dict((b, {"local_orientation": qz(deg)}) for b in FINGERS)
    return {"name": name, "kind": "pose", "_deg": deg, "pose": {
        "version": 3, "scope": {"kind": "selected_parts", "posed": list(posed or FINGERS), "carried": []},
        "engine": {"rule": "direct_fk_v1", "revision": 1, "carried_rule": None}, "oracle": {"bones": orc}}}


class Synthetic(object):
    """One complete, correct run; `faults` names the counterexamples to inject; `prop` adds Process C."""

    def __init__(self, folder, faults=(), prop=None):
        self.q, self.faults, self.prop = folder, set(faults), prop
        for d in ("staged", "observations", "sessions", os.path.join("evidence", "logs"),
                  os.path.join("evidence", "library_poses", CHAR)):
            os.makedirs(os.path.join(folder, d))
        self.dump(os.path.join("staged", "IDENTITIES.json"), {"qualification_cpm_sha256": QUAL})
        self.logs, self.ms = {}, 0

    def dump(self, rel, data):
        with open(os.path.join(self.q, rel), "wb") as f:
            f.write(json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))

    def observe(self, scene, step):
        label = C.LABELS[step]
        obs, side = scene.observe(label, step)
        hook = getattr(self, "fault_" + step, None)
        if hook:
            hook(obs, side)
        self.dump(os.path.join("observations", label + ".json"), obs)
        self.dump(os.path.join("observations", label + ".sfp1.json"), side)

    def op(self, pid, lines, ms=300):
        log = self.logs.setdefault(pid, [])
        op_id = len(log) + 1

        def stamp():
            return "2026-11-09T10:%02d:%02d.%03dZ" % (self.ms // 60000, (self.ms // 1000) % 60, self.ms % 1000)
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
        grip, point = scoped_record(u"SFP1 Grip", 30.0), scoped_record(u"SFP1 Point", 80.0)
        if "wrong_scope" in self.faults:
            grip = scoped_record(u"SFP1 Grip", 30.0, FINGERS[1:])
        # Process A: the source session
        a = Scene(100, "E:/run/sessions/SFP1_SOURCE.dmx", "shot15", 0.2083, 0.0, 0.0)
        self.observe(a, "A1")
        a.pose_fingers(30.0)
        self.observe(a, "A2")
        if "save_writes" in self.faults:
            a.key("jaw_o", qz(9.0))
        self.observe(a, "A3")
        a.pose_fingers(60.0)
        self.observe(a, "A4")
        self.observe(a, "A5")
        a.pose_fingers(80.0)
        self.observe(a, "A6")
        self.observe(a, "A7")
        # Process B: the destination session after a restart (shot13 first)
        pid = 100 if "no_restart" in self.faults else 200
        b = Scene(pid, "E:/run/sessions/SFP1_DESTINATION.dmx", "shot13", 0.375, 0.0, 40.0)
        b.key("bip_index_0_l_o", qz(0.0))         # the Owner's step-0 posing keyed the destination at the playhead
        self.observe(b, "B1")
        base = b.snapshot()
        b.apply(grip, u"SFP1 Grip")
        if "grip_moves_nothing" in self.faults:
            b.restore(base, b.undo)
        if "wrist_moved" in self.faults:
            b.angles["bip_hand_l"] += 6.0
        if "face_control_changed" in self.faults:
            b.controls["Smile"] = 0.9
        if "finger_off" in self.faults:
            b.angles["bip_ring_1_l"] += 0.05
        if "outside_changed" in self.faults:
            b.outside = "x" * 64
        self.observe(b, "B2")
        applied = b.snapshot()
        self.scoped(pid, {"insert": 29, "update": 1, "none": 0})
        b.restore(base, {"can_undo": True, "can_redo": True, "undo_desc": "Modify Head Time", "redo_desc": "x"})
        if "undo_incomplete" in self.faults:
            b.key("bip_index_1_l_o", qz(30.0))
        self.observe(b, "B3")
        b.restore(applied)
        self.observe(b, "B4")
        if "noop_writes" in self.faults:
            b.key("jaw_o", qz(4.0))
        self.observe(b, "B5")
        self.scoped(pid, {}, noop=True)
        b.apply(point, u"SFP1 Point")
        if "insert_on_update" in self.faults:
            b.keys["bip_thumb_0_l_o"].append([T_CHAN + 7, qz(80.0)])
        self.observe(b, "B6")
        self.scoped(pid, {"insert": 0, "update": 30, "none": 0})
        self.observe(b, "B7")
        self.scoped(pid, {"insert": 0, "update": 30, "none": 0}, abort=True)
        b.mode = "Clip Editor"
        self.observe(b, "B8")
        self.observe(b, "B9")
        self.op(pid, ['PROD_POSE_SCOPE-refused {"code": "editor-mode"}'])
        # the sequence in shot15 of the destination session (same SFM process)
        s = Scene(pid, b.document, "shot15", 0.2083, 10.0, 0.0)
        s.undo = dict(b.undo)
        self.observe(s, "B10")
        s10 = s.snapshot()
        s.apply_legacy()
        if "legacy_touches_fingers" in self.faults:
            s.key("bip_pinky_2_l_o", qz(44.0))
        self.observe(s, "B11")
        s11 = s.snapshot()
        self.op(pid, ['PROD_POSE_P1 {"noop": false}', 'PROD_POSE_P6 {}', 'PROD_POSE_P7-verified {}'])
        s.apply(grip, u"SFP1 Grip")
        self.observe(s, "B12")
        s12 = s.snapshot()
        self.scoped(pid, {"insert": 30, "update": 0, "none": 0}, verified="unverified_log" not in self.faults)
        s.restore(s11)
        s.undo = {"can_undo": True, "can_redo": True, "undo_desc": "Apply Pose NQ1 Pose A", "redo_desc": "x"}
        self.observe(s, "B13")
        s.restore(s10)
        s.undo = {"can_undo": True, "can_redo": True, "undo_desc": "Modify Head Time", "redo_desc": "x"}
        self.observe(s, "B14")
        s.restore(s11)
        self.observe(s, "B15")
        s.restore(s12)
        self.observe(s, "B16")
        if self.prop:
            p = Scene(300, "E:/run/sessions/SFP1_PROP.dmx", "shot13", 0.375, 0.0, 40.0)
            p.outside = "p" * 64
            self.observe(p, "C1")
            pbase = p.snapshot()
            if self.prop == "applied":
                p.apply(grip, u"SFP1 Grip")
                self.scoped(300, {"insert": 30, "update": 0, "none": 0})
            else:
                self.op(300, ['PROD_POSE_SCOPE-refused {"code": "structure-unsupported"}'])
            self.observe(p, "C2")
            p.restore(pbase)
            self.observe(p, "C3")
        # UI captures, records, libraries, logs, restore and session pins
        for label, pid_ in (("UI-A", 100), ("UI-B", pid)):
            self.dump(os.path.join("observations", label + ".json"), {
                "pid": pid_, "selected": {"version": 3, "scope_kind": "selected_parts"}, "apply_button_enabled": True,
                "registry_mode": "qualification", "recovery_paused": False,
                "pose_info": {"engine": "direct_fk_v1 revision 1"}})
        files = {}
        for rec, fname in ((grip, u"SFP1 Grip--a1.json"), (point, u"SFP1 Point--b2.json"),
                           ({"name": u"NQ1 Pose A", "pose": {"version": 1}}, u"NQ1 Pose A--5273df2209ca.json")):
            rec = dict((k, v) for k, v in rec.items() if k != "_deg")
            self.dump(os.path.join("evidence", "library_poses", CHAR, fname), rec)
            files[fname] = sha_bytes(fname.encode("utf-8"))
        self.dump(os.path.join("evidence", "library_A.json"), {"files": files})
        self.dump(os.path.join("evidence", "library_B.json"), {"files": files})
        for p_, rows in self.logs.items():
            with open(os.path.join(self.q, "evidence", "logs", "CPM - x - pid%d - y - 001.log" % p_), "wb") as f:
                f.write(("\n".join(rows) + "\n").encode("utf-8"))
        self.dump(os.path.join("evidence", "restore.json"), {"restored": True})
        pins = {}
        for name, key in (("SFP1_DESTINATION.dmx", "destination_sha256"), ("SFP1_PROP.dmx", "prop_sha256")):
            if key == "prop_sha256" and not self.prop:
                pins[key] = None
                continue
            with open(os.path.join(self.q, "sessions", name), "wb") as f:
                f.write(name.encode("ascii"))
            pins[key] = sha_bytes(name.encode("ascii"))
        self.dump(os.path.join("evidence", "destination.json"), pins)
        return self


if PY3:
    class CompareTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="sfp1cmp")

        def tearDown(self):
            shutil.rmtree(self.dir, True)

        def verdict(self, faults=(), prop=None):
            q = os.path.join(self.dir, "run%d" % len(os.listdir(self.dir)))
            Synthetic(q, faults, prop).build()
            c = {"paths": {"Q": q}, "character_dir": CHAR}
            capture(lambda: C.run(c))
            return load(os.path.join(q, "evidence", "SFP1_VERDICT.json"))

        def test_a_complete_correct_run_passes(self):
            v = self.verdict()
            self.assertEqual((v["verdict"], v["failed"]), ("PASS", []))
            self.assertGreater(len(v["checks"]), 120)
            self.assertEqual(v["performance"]["class"], "responsive")

        def test_the_optional_prop_process_applied_or_refused_passes_with_a_finding(self):
            for outcome in ("applied", "refused"):
                v = self.verdict(prop=outcome)
                self.assertEqual((v["verdict"], v["failed"]), ("PASS", []), outcome)
                self.assertTrue(any(outcome in f for f in v["findings"]))

        def test_counterexamples_fail(self):
            expect = {"grip_moves_nothing": "apply_grip.fingers_take_the_saved_articulation",
                      "wrist_moved": "apply_grip.wrist_arm_body_and_face_unchanged",
                      "face_control_changed": "apply_grip.facial_gaze_and_other_controls_unchanged",
                      "finger_off": "apply_grip.fingers_take_the_saved_articulation",
                      "outside_changed": "apply_grip.unrelated_animation_unchanged",
                      "undo_incomplete": "undo.restores_the_destination_baseline",
                      "noop_writes": "repeat.true_noop",
                      "insert_on_update": "apply_point.existing_keys_updated_in_place",
                      "no_restart": "process.restart_between_save_and_apply",
                      "save_writes": "save.A2_to_A3_writes_nothing_to_the_scene",
                      "legacy_touches_fingers": "seq.legacy_left_arm_applied",
                      "unverified_log": "log.no_recovery_or_uncertainty",
                      "wrong_scope": "save.grip_is_version_3_selected_parts_of_the_15_left_fingers"}
            for fault, check in sorted(expect.items()):
                v = self.verdict((fault,))
                self.assertEqual(v["verdict"], "FAIL", fault)
                self.assertIn(check, v["failed"], (fault, v["failed"][:6]))

        def test_a_wrong_build_in_one_observation_fails(self):
            q = os.path.join(self.dir, "wrongcpm")
            s = Synthetic(q)

            def fault(obs, side):
                obs["cpm_loaded"]["build_sha256"] = "w" * 64
            s.fault_B2 = fault
            s.build()
            capture(lambda: C.run({"paths": {"Q": q}, "character_dir": CHAR}))
            self.assertIn("cpm.B2", load(os.path.join(q, "evidence", "SFP1_VERDICT.json"))["failed"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
