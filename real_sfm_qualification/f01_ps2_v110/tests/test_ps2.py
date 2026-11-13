# -*- coding: ascii -*-
"""Offline tests of the F-01 PS-2 v1.1.0 production candidate kit.

- The state capture (Python 2.7 and 3) against fake SFM, PySide and CPM modules: read-only (no call that writes),
  records the CPM identity, the selected pose with its Pose Info rows and the Undo/Redo descriptions; refuses an
  unknown or repeated step.
- ps2_tool (Python 3) on a synthetic v1.0.0 release and installation:
  - package: v1.0.0's exact bytes plus the candidate CPM, both registries and the unsigned candidate inventory; the
    v1.0.0 signature left out; deterministic ZIP; refuses a wrong ZIP, a qualification-mode or experimental-rule CPM,
    a changed registry, a spec that differs and a candidate inventory that is not the pinned one;
  - pre refuses an installation that is not exactly v1.0.0 and a library that already holds Poses folders;
  - install / seed / rollback / cleanup: the candidate layout (signature removed); rollback restores v1.0.0 file by
    file and leaves the library (Poses folders included) untouched; cleanup puts the library back exactly and every
    inventory equals its baseline; refusals while SFM runs and on a repeated install.
- ps2_compare (Python 3): a complete synthetic run is PASS; a Soldier refusal is PASS WITH FINDINGS; each
  counterexample is FAIL on its own check.
They show nothing about SFM.

Run: python -I test_ps2.py   (SFM's Python 2.7: python -E -s -B test_ps2.py runs the state-capture tests)
"""
import copy
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE = os.path.join(ROOT, "observer", "F01_PS2_State.py")
sys.path.insert(0, os.path.join(ROOT, "tools"))
PY3 = sys.version_info[0] >= 3
if PY3:
    import ps2_compare as C  # noqa: E402
    import ps2_tool as TOOL  # noqa: E402


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(path):
    with open(path, "rb") as f:
        return sha_bytes(f.read())


def write(path, data):
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def rjson(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def rtext(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")


def jdump(path, obj):
    write(path, json.dumps(obj, indent=1, sort_keys=True))


# --- the state capture (Python 2.7 and 3) ----------------------------------------------------------------------

class Calls(object):
    def __init__(self):
        self.log = []


class Vec(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


class FakeAttribute(object):
    def __init__(self, value):
        self.value = value

    def GetValue(self):
        return self.value


class FakeElement(object):
    """A read-only DME element: name, handle and attributes; it offers no setter."""

    def __init__(self, name, handle, attrs, calls=None):
        self.name, self.handle, self.attrs = name, handle, attrs

    def GetName(self):
        return self.name

    def GetHandle(self):
        return self.handle

    def HasAttribute(self, name):
        return self.attrs.get(name) is not None

    def GetAttribute(self, name):
        return FakeAttribute(self.attrs[name])


def fake_environment(calls, version=3):
    dm = types.SimpleNamespace() if PY3 else type("DM", (), {})()
    dm.CanUndo = lambda: calls.log.append("CanUndo") or True
    dm.CanRedo = lambda: calls.log.append("CanRedo") or False
    dm.GetUndoDesc = lambda: u"Apply Pose PS2 Engineer Body"
    dm.GetRedoDesc = lambda: u""
    dm.GetFileName = lambda fid: u"x:\\q\\sessions\\PS2_ENGINEER_DESTINATION.dmx"
    vs = types.ModuleType("vs")
    vs.g_pDataModel = dm
    sfm = types.ModuleType("sfmApp")
    shot = FakeElement(u"shot1", 1, {"animationSets": [
        FakeElement(u"Krystal", 10, {"controls": [FakeElement(u"bodyFat", 11, {"value": 0.25}),
                                                 FakeElement(u"rootTransform", 12, {"valuePosition": Vec(1.0, 2.0, 3.0)})],
                                    "gameModel": FakeElement(u"m", 13, {
                                        "modelName": u"models/k.mdl", "bones": [FakeElement(u"bone 0", 14, {
                                            "position": Vec(0.0, 0.0, 1.0), "scale": Vec(1.0, 1.0, 1.0)})],
                                        "globalFlexControllers": [FakeElement(u"smile", 15, {"flexWeight": 0.5})]})}),
        FakeElement(u"Krystal1", 20, {"controls": [], "gameModel": None})]}, calls)
    root = type("Root", (), {"GetFileId": lambda self: 7})()
    sfm.GetTimelineMode = lambda: 2
    sfm.GetNameForTimelineMode = lambda m: u"Motion Editor"
    sfm.GetHeadTimeInSeconds = lambda: 0.0
    sfm.GetShotAtCurrentTime = lambda: shot
    sfm.GetDocumentRoot = lambda: root
    record = {u"name": u"PS2 Engineer Body", u"pose": {
        u"version": version, u"scope": {u"kind": u"full_body", u"posed": [u"b%d" % i for i in range(72)],
                                        u"root_translation": u"included"},
        u"engine": {u"rule": u"direct_fk_v1", u"revision": 1}, u"source": {u"model_ref": u"models/player/engineer.mdl"}}}
    item = {u"name": u"PS2 Engineer Body", u"preset_id": u"abc", u"record": record}
    button = type("B", (), {"isEnabled": lambda self: True})()
    window = type("W", (), {})()
    window.current = lambda: {"model": u"models/player/engineer.mdl", "name": u"engineer1"}
    window.selected_pose = lambda: item
    window.pose_ui_state = lambda it: {u"buttons": {u"apply_pose": True}}
    window.apply_pose_button = button
    window.pose_recovery_blocked = False
    app = type("App", (), {})()
    setattr(app, "_cpm_window", window)
    qtgui = types.ModuleType("PySide.QtGui")
    qtgui.QApplication = type("QApplication", (), {"instance": staticmethod(lambda: app)})
    pyside = types.ModuleType("PySide")
    pyside.QtGui = qtgui
    cpm = types.ModuleType("chadchan3d_cpm_app")
    cpm.__chadchan3d_cpm_build_sha256__ = "84cd996c" + "0" * 56
    cpm.PROD_APP_ATTR = "_cpm_window"
    cpm.PROD_POSE_REGISTRY_MODE = u"production"
    cpm.PROD_SCOPE_RULES = {u"direct_fk_v1": {u"revision": 1, u"status": u"qualified"}}
    cpm.PROD_SCOPE_CARRIED_ENABLED = [False]
    cpm.PROD_SCOPE_EXTRAPOLATION_QUALIFIED = [False]
    cpm.PROD_POSE_QUAL_FAULT = [None]
    cpm.PROD_POSE_RECOVERY_BLOCK = [None]
    cpm.prod_release_version = lambda: u"1.1.0"
    cpm.prod_pose_load_registry = lambda: {u"_sha256": u"f445", u"_body": {}}
    cpm.prod_pose_registry_select = lambda reg, mode: {u"mappings": [{u"region": u"left_arm",
                                                                       u"status": u"qualified"}]}
    cpm.prod_pose_info_view = lambda rec: {u"rows": [[u"Includes:", u"Full body, including hip movement", None]]}
    return {"vs": vs, "sfmApp": sfm, "PySide": pyside, "PySide.QtGui": qtgui, "chadchan3d_cpm_app": cpm}


def _exec(code, g):
    exec(code, g)


def run_state(folder, step, calls):
    mods = fake_environment(calls)
    saved = dict((k, sys.modules.get(k)) for k in mods)
    sys.modules.update(mods)
    try:
        g = {"__name__": "__ps2__", "PS2_DIR": folder, "PS2_STEP": step}
        with open(STATE, "rb") as f:
            code = compile(f.read(), STATE, "exec")
        out = sys.stdout
        sys.stdout = io.BytesIO() if not PY3 else io.StringIO()
        try:
            _exec(code, g)
        finally:
            sys.stdout = out
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class StateCaptureTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ps2state")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_records_identity_pose_info_and_undo_read_only(self):
        calls = Calls()
        run_state(self.dir, "S-E-APPLY", calls)
        with open(os.path.join(self.dir, "observations", "S-E-APPLY.json"), "rb") as f:
            d = json.loads(f.read().decode("utf-8"))
        self.assertEqual(d["registry_mode"], u"production")
        self.assertEqual(d["release_version"], u"1.1.0")
        self.assertEqual(d["scope_rules"], {u"direct_fk_v1": {u"revision": 1, u"status": u"qualified"}})
        self.assertEqual(d["registry"]["mappings"], [[u"left_arm", u"qualified"]])
        self.assertEqual((d["selected_pose"]["version"], d["selected_pose"]["scope_kind"],
                          d["selected_pose"]["posed"]), (3, u"full_body", 72))
        self.assertEqual(d["pose_info"]["rows"][0][1], u"Full body, including hip movement")
        self.assertEqual(d["session"]["undo"]["undo_desc"], u"Apply Pose PS2 Engineer Body")
        self.assertEqual(sorted(set(calls.log)), ["CanRedo", "CanUndo"])
        sets = d["animation_sets"]
        self.assertEqual([(s["name"], s["model"], s["controls"], s["bones"]) for s in sets],
                         [(u"Krystal", u"models/k.mdl", 2, 1), (u"Krystal1", None, 0, 0)])
        self.assertEqual(len(sets[0]["state_sha256"]), 64)
        self.assertNotEqual(sets[0]["state_sha256"], sets[1]["state_sha256"])

    def test_refuses_unknown_and_repeated_steps(self):
        calls = Calls()
        self.assertRaises(RuntimeError, run_state, self.dir, "S-NOPE", calls)
        run_state(self.dir, "S-PROD", calls)
        self.assertRaises(RuntimeError, run_state, self.dir, "S-PROD", calls)

    def test_step_table_equals_the_comparators(self):
        with open(STATE, "rb") as f:
            src = f.read().decode("ascii")
        ns = {}
        exec(src[src.index("STEPS = "):src.index("\n\n\ndef _text")], ns)
        if PY3:
            self.assertEqual(ns["STEPS"], C.STATE_STEPS)


# --- ps2_tool on a synthetic release (Python 3) ----------------------------------------------------------------

MM = "usermod/scripts/sfm/mainmenu/SFM Character Tools/"
LIB = "usermod/scripts/SFM Character Tools/"
CPM_ENTRY = "usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py"
REG = (b'{"registry": "pose"}\n', b'{"registry": "body"}\n')


def candidate_cpm(reg_pose, reg_body, mode=b"production", status=b"qualified"):
    return (b'# synthetic CPM\nPROD_POSE_REGISTRY_MODE = u"' + mode + b'"\n'
            b'PROD_POSE_REGISTRY_SHA256 = u"' + reg_pose.encode("ascii") + b'"\n'
            b'PROD_BODY_REGISTRY_SHA256 = u"' + reg_body.encode("ascii") + b'"\n'
            b'PROD_SCOPE_RULES = {u"direct_fk_v1": {u"revision": 1, u"status": u"' + status + b'"}}\n'
            b'PROD_SCOPE_CARRIED_ENABLED = [False]\nPROD_SCOPE_EXTRAPOLATION_QUALIFIED = [False]\n'
            b'PROD_POSE_QUAL_FAULT = [None]\n')


class Env(object):
    """A synthetic published v1.0.0 ZIP, repository and v1.0.0 installation."""

    def __init__(self, root):
        self.root = root
        self.repo = os.path.join(root, "repo")
        self.game = os.path.join(root, "game")
        self.q = os.path.join(root, "Q")
        os.makedirs(self.q)
        software = {CPM_ENTRY: b"# v1.0.0 CPM\n", LIB + "cpm_authority_adapter.py": b"# adapter\r\n",
                    MM + "SFM_Character_Preset_Manager.py": b"# launcher\n"}
        roles = {CPM_ENTRY: "cpm_app", LIB + "cpm_authority_adapter.py": "cpm_adapter",
                 MM + "SFM_Character_Preset_Manager.py": "cpm_launcher"}
        inv = {"schema": 1, "object_type": "sfm-character-tools-software-inventory", "software": "SFM Character Tools",
               "software_version": "1.0.0", "authority_profile": "sct-authority-profile-2",
               "profile_contract_sha256": "d" * 64, "runtime_api_version": "1.0.0-b2a", "runtime_build_id": "x",
               "signing_key_id": "ed25519-5d879134807dff6d",
               "files": [{"path": e[len("usermod/"):], "role": roles[e], "byte_length": len(b), "sha256": sha_bytes(b)}
                         for e, b in sorted(software.items())]}
        self.files = dict(software)
        self.files[MM + "sfm_character_tools_inventory.json"] = TOOL.canonical(inv)
        self.files[MM + "sfm_character_tools_inventory.sig"] = b"\x01" * 64
        self.files["usermod/cfg/sfm_defaultanimationgroups.txt"] = b"master\n"
        self.files["README.txt"] = b"readme\n"
        self.files["OPTIONAL - CPM Button/README.txt"] = b"optional\n"
        self.zip = os.path.join(root, "v100.zip")
        with zipfile.ZipFile(self.zip, "w") as z:
            for n, b in sorted(self.files.items()):
                z.writestr(n, b)
        self.reg_sha = [sha_bytes(b) for b in REG]
        self.cpm = candidate_cpm(*self.reg_sha)
        write(os.path.join(self.repo, "cpm", "app", "SFM_Character_Preset_Manager.py"), self.cpm)
        for name, b in zip(TOOL.REGISTRIES, REG):
            write(os.path.join(self.repo, "cpm", "pose_profiles", name), b)
        spec_files = []
        for f in inv["files"]:
            e = "usermod/" + f["path"]
            if e == CPM_ENTRY:
                spec_files.append(dict(f, sha256=sha_bytes(self.cpm), byte_length=len(self.cpm),
                                       source="cpm/app/SFM_Character_Preset_Manager.py"))
            else:
                spec_files.append(dict(f, source="release-v1.0.0:" + e))
        for name, b, role in zip(TOOL.REGISTRIES, REG, ("cpm_pose_registry", "cpm_body_registry")):
            spec_files.append({"path": "scripts/SFM Character Tools/" + name, "role": role, "byte_length": len(b),
                               "sha256": sha_bytes(b), "source": "cpm/pose_profiles/" + name})
        self.spec = {"authority_profile": "sct-authority-profile-2", "files": spec_files, "schema": 1,
                     "software": "SFM Character Tools"}
        jdump(os.path.join(self.repo, "release", "v1.1.0-candidate", "SOFTWARE_SPEC.json"), self.spec)
        # v1.0.0 installed; a preset library; sessions; logs; fixtures.
        for n, b in self.files.items():
            if n.startswith("usermod/"):
                write(os.path.join(self.game, *n.split("/")), b)
        write(os.path.join(self.game, "usermod", "cfg", "config.cfg"), b"cfg\n")
        write(os.path.join(self.game, "usermod", "scripts", "x.pyc"), b"pyc\n")
        self.library = os.path.join(root, "library")
        write(os.path.join(self.library, "Characters", "krystal2020--7d2aee52ef3a", "character.json"), b"{}\n")
        write(os.path.join(self.library, "Characters", "krystal2020--7d2aee52ef3a", "Body Presets", "Body.json"),
              b"{\"body\": 1}\n")
        self.sessions = os.path.join(root, "sessions")
        write(os.path.join(self.sessions, "old.dmx"), b"session\n")
        self.logs = os.path.join(root, "logs")
        os.makedirs(self.logs)
        self.fixtures = {}
        for key, data in (("EF1_SOURCE", b"src"), ("EF1_DESTINATION", b"dst"), ("R2_FIXTURE", b"r2"),
                          ("LEGACY_POSE", b"{\"legacy\": 1}")):
            path = os.path.join(root, "fixtures", key)
            write(path, data)
            self.fixtures[key] = (path, sha_bytes(data))

    def config(self, **pins):
        with open(os.path.join(ROOT, "ps2.template.json"), "rb") as f:
            c = json.loads(f.read().decode("utf-8"))
        c["paths"].update(Q=self.q, REPO=self.repo, GAME=self.game, LIBRARY=self.library, SESSIONS=self.sessions,
                          LOG_DIR=self.logs, V100_ZIP=self.zip,
                          **dict((k, v[0]) for k, v in self.fixtures.items()))
        c["housekeeping"] = ["cfg\\config.cfg"]
        files = self.files
        c["pins"].update(
            v100_zip_sha256=sha_file(self.zip), v100_zip_entries=len(files),
            v100_cpm_sha256=sha_bytes(files[CPM_ENTRY]),
            v100_inventory_sha256=sha_bytes(files[MM + "sfm_character_tools_inventory.json"]),
            v100_signature_sha256=sha_bytes(files[MM + "sfm_character_tools_inventory.sig"]),
            spec_sha256=sha_file(os.path.join(self.repo, "release", "v1.1.0-candidate", "SOFTWARE_SPEC.json")),
            candidate_cpm_sha256=sha_bytes(self.cpm), profile_sha256=self.reg_sha[0], body_profile_sha256=self.reg_sha[1],
            ef1_source_sha256=self.fixtures["EF1_SOURCE"][1], ef1_destination_sha256=self.fixtures["EF1_DESTINATION"][1],
            r2_fixture_sha256=self.fixtures["R2_FIXTURE"][1], legacy_pose_sha256=self.fixtures["LEGACY_POSE"][1])
        staged = dict(files)
        staged[CPM_ENTRY] = self.cpm
        for name, b in zip(TOOL.REGISTRIES, REG):
            staged[LIB + name] = b
        cfg = dict(c, paths=dict(c["paths"]))
        c["pins"]["candidate_inventory_sha256"] = sha_bytes(TOOL.candidate_inventory(cfg, self.spec, staged))
        c["pins"].update(pins)
        path = os.path.join(self.root, "ps2.json")
        jdump(path, c)
        return TOOL.load(path)


if PY3:
    class PackageTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="ps2pkg")
            self.env = Env(self.dir)
            self.saved = TOOL.T.sfm_running
            TOOL.T.sfm_running = lambda: None

        def tearDown(self):
            TOOL.T.sfm_running = self.saved
            shutil.rmtree(self.dir, True)

        def quiet(self, fn):
            out = sys.stdout
            sys.stdout = io.StringIO()
            try:
                return fn()
            finally:
                sys.stdout = out

        def test_package_is_v100_plus_candidate_unsigned_and_deterministic(self):
            c = self.env.config()
            self.quiet(lambda: TOOL.cmd_package(c))
            m = TOOL.T.read_json(os.path.join(self.env.q, "package", "PACKAGE_MANIFEST.json"))
            rows = dict((r["path"], r) for r in m["files"])
            self.assertNotIn(MM + "sfm_character_tools_inventory.sig", rows)
            self.assertEqual(rows[CPM_ENTRY]["sha256"], sha_bytes(self.env.cpm))
            for name in TOOL.REGISTRIES:
                self.assertEqual(rows[LIB + name]["origin"], "candidate")
            for n, b in self.env.files.items():
                if n not in (CPM_ENTRY, MM + "sfm_character_tools_inventory.json",
                             MM + "sfm_character_tools_inventory.sig"):
                    self.assertEqual((rows[n]["sha256"], rows[n]["origin"]), (sha_bytes(b), "v1.0.0"))
            inv = rjson(os.path.join(self.env.q, "package", "stage", *(
                MM + "sfm_character_tools_inventory.json").split("/")))
            self.assertEqual(inv["software_version"], "1.1.0")
            self.assertEqual([f["path"] for f in inv["files"]], [f["path"] for f in self.env.spec["files"]])
            self.assertTrue(m["status"].startswith("UNSIGNED"))
            first = m["zip_sha256"]
            shutil.rmtree(os.path.join(self.env.q, "package"))
            self.quiet(lambda: TOOL.cmd_package(c))
            self.assertEqual(TOOL.T.read_json(os.path.join(self.env.q, "package", "PACKAGE_MANIFEST.json"))[
                "zip_sha256"], first)
            with zipfile.ZipFile(os.path.join(self.env.q, "package", TOOL.ZIP_NAME)) as z:
                self.assertEqual(len(z.infolist()), len(self.env.files) - 1 + 2)

        def refused(self, c):
            self.assertRaises(SystemExit, self.quiet, lambda: TOOL.cmd_package(c))
            self.assertFalse(os.path.exists(os.path.join(self.env.q, "package")))

        def test_package_refuses_a_wrong_zip_or_spec_or_inventory_pin(self):
            for pins in ({"v100_zip_sha256": "0" * 64}, {"spec_sha256": "0" * 64},
                         {"candidate_inventory_sha256": "0" * 64}, {"profile_sha256": "0" * 64}):
                self.refused(self.env.config(**pins))

        def test_package_refuses_a_qualification_or_experimental_cpm(self):
            for cpm in (candidate_cpm(*self.env.reg_sha, mode=b"qualification"),
                        candidate_cpm(*self.env.reg_sha, status=b"experimental")):
                write(os.path.join(self.env.repo, "cpm", "app", "SFM_Character_Preset_Manager.py"), cpm)
                self.refused(self.env.config(candidate_cpm_sha256=sha_bytes(cpm)))

        def test_full_cycle_install_rollback_cleanup(self):
            c = self.env.config()
            self.quiet(lambda: TOOL.cmd_package(c))
            base_library = TOOL.T.inventory(self.env.library)["sha256"]
            self.quiet(lambda: TOOL.cmd_pre(c))
            self.assertEqual(TOOL.state(c)[0], "v1.0.0")
            self.quiet(lambda: TOOL.cmd_install(c))
            self.assertEqual(TOOL.state(c)[0], "candidate")
            self.assertFalse(os.path.exists(os.path.join(self.env.game, *(MM + "sfm_character_tools_inventory.sig")
                                                         .split("/"))))
            self.assertRaises(SystemExit, self.quiet, lambda: TOOL.cmd_install(c))
            self.quiet(lambda: TOOL.cmd_seed(c))
            # What the native run leaves: new records, a changed character file, bytecode and housekeeping.
            chars = os.path.join(self.env.library, "Characters")
            write(os.path.join(chars, "engineer--6111c38a013f", "Poses", "PS2 Engineer Body--1.json"), b"{}")
            write(os.path.join(chars, "engineer--6111c38a013f", "character.json"), b"{}")
            write(os.path.join(chars, "krystal2020--7d2aee52ef3a", "character.json"), b"{\"renamed\": 1}\n")
            write(os.path.join(self.env.game, "usermod", "scripts", "new.pyc"), b"pyc2\n")
            write(os.path.join(self.env.game, "usermod", "cfg", "config.cfg"), b"cfg changed\n")
            self.quiet(lambda: TOOL.cmd_library(c, "K"))
            self.quiet(lambda: TOOL.cmd_rollback(c))
            rb = TOOL.T.read_json(os.path.join(self.env.q, "evidence", "rollback.json"))
            self.assertTrue(rb["rolled_back"] and rb["library_untouched"])
            self.assertEqual(TOOL.state(c)[0], "v1.0.0")
            self.assertEqual(sorted(rb["poses_folders_kept"]), ["engineer--6111c38a013f", "krystal2020--7d2aee52ef3a"])
            self.quiet(lambda: TOOL.cmd_library(c, "V100"))
            self.quiet(lambda: TOOL.cmd_cleanup(c))
            cl = TOOL.T.read_json(os.path.join(self.env.q, "evidence", "cleanup.json"))
            self.assertTrue(cl["restored"], cl)
            self.assertEqual(TOOL.T.inventory(self.env.library)["sha256"], base_library)
            self.assertTrue(os.path.isfile(os.path.join(self.env.q, "evidence", "library_after", "Characters",
                                                        "engineer--6111c38a013f", "Poses", "PS2 Engineer Body--1.json")))

        def test_pre_refuses_a_non_v100_installation_or_existing_poses(self):
            c = self.env.config()
            self.quiet(lambda: TOOL.cmd_package(c))
            write(os.path.join(self.env.library, "Characters", "x", "Poses", "p.json"), b"{}")
            self.assertRaises(SystemExit, self.quiet, lambda: TOOL.cmd_pre(c))
            shutil.rmtree(os.path.join(self.env.library, "Characters", "x"))
            write(os.path.join(self.env.game, *LIB.split("/")) + "cpm_pose_profiles_v1.json", b"x")
            self.assertRaises(SystemExit, self.quiet, lambda: TOOL.cmd_pre(c))
            self.assertFalse(os.path.exists(os.path.join(self.env.q, "pre_run")))

        def test_rollback_refuses_while_sfm_runs(self):
            c = self.env.config()
            self.quiet(lambda: TOOL.cmd_package(c))
            self.quiet(lambda: TOOL.cmd_pre(c))
            self.quiet(lambda: TOOL.cmd_install(c))
            TOOL.T.sfm_running = lambda: "sfm.exe is running"
            self.assertRaises(SystemExit, self.quiet, lambda: TOOL.cmd_rollback(c))
            self.assertEqual(TOOL.state(c)[0], "candidate")


# --- ps2_compare on a synthetic run (Python 3) ------------------------------------------------------------------

CAND, V100 = "c" * 64, "a" * 64


def log_text(build, pid, ops):
    lines = ["SFM Character Preset Manager diagnostic log cpm-log-v1 | build_sha256=%s version=x | session=s pid=%d "
             "run_id=r | segment=001" % (build, pid)]
    t = 0
    for i, (kind, animset, outcome, events) in enumerate(ops, 1):
        t += 1000
        ctx = "{'animset_id': (u'DmeAnimationSet', u'%s', 44, 1L)}" % animset if animset else "None"
        lines.append("2026-11-12T12:00:%02d.000Z #1 s=s w=1 op=%d | PROD_OPERATION_BEGIN id=%d kind=u'%s' context=%s"
                     % (t // 1000 % 60, i, i, kind, ctx))
        for e in events:
            lines.append("2026-11-12T12:00:%02d.100Z #2 s=s w=1 op=%d | PROD_POSE_%s {}" % (t // 1000 % 60, i, e))
        lines.append("2026-11-12T12:00:%02d.900Z #3 s=s w=1 op=%d | PROD_OPERATION_RESULT id=%d kind=u'%s' "
                     "outcome=u'%s'" % (t // 1000 % 60, i, i, kind, outcome))
    return "\n".join(lines) + "\n"


VER = ["SCOPE-P1", "SCOPE-P7-verified"]


KMODEL = "models/fursonas/starfox/krystal/bodies/krystal2020.mdl"


def dup_sets(a, b, other=True):
    rows = [{"name": "Krystal", "handle": 1, "model": KMODEL.replace("/", "\\"), "state_sha256": a},
            {"name": "krystal2020", "handle": 2, "model": KMODEL, "state_sha256": b}]
    if other:
        rows.append({"name": "engineer1", "handle": 3, "model": "models/player/engineer.mdl", "state_sha256": "e"})
    return {"animation_sets": rows}


def synthetic_run(q, soldier=True, dup="ok", ui="ACCEPTED"):
    names = {"engineer_pose": "PS2 Engineer Body", "soldier_pose": "PS2 Soldier Body", "krystal_pose": "PS2 Krystal grip"}
    with open(os.path.join(ROOT, "ps2.template.json"), "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    c["paths"]["Q"] = q
    c["pins"].update(candidate_cpm_sha256=CAND, v100_cpm_sha256=V100, candidate_inventory_sha256="i" * 64)
    jdump(os.path.join(q, "package", "PACKAGE_MANIFEST.json"), {
        "status": "UNSIGNED CANDIDATE - not for distribution", "candidate_cpm_sha256": CAND,
        "candidate_inventory_sha256": "i" * 64, "v100_zip_sha256": c["pins"]["v100_zip_sha256"],
        "spec_sha256": c["pins"]["spec_sha256"], "zip_sha256": "z" * 64,
        "removed": ["usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.sig"],
        "files": [{"path": "usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json"},
                  {"path": "usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json"}]})
    jdump(os.path.join(q, "pre_run", "install_journal.json"), {"state": "complete"})
    p2 = [("Apply Pose", "engineer1", "verified", VER)]
    if soldier:
        p2 += [("Save Pose", "soldier", "verified", []), ("Apply Pose", "soldier", "verified", VER)]
    p2 += [("Save Pose", "heavy", "no-op", ["SCOPE-carried-refused"])]
    logs = [(CAND, 101, [("Save Pose", "engineer1", "verified", [])]), (CAND, 102, p2),
            (CAND, 103, [("Save Pose", "Krystal", "verified", []), ("Apply Pose", "Krystal", "verified", VER),
                         ("Apply Pose", "Krystal", "verified", []), ("Apply Body Preset", "Krystal", "verified", []),
                         ("Apply Expression", "Krystal", "verified", []),
                         ("Save Current Body", "krystal2020", "verified", []),
                         ("Apply Body Preset", "krystal2020" if dup == "wrong_target" else "Krystal",
                          "failed-precommit" if dup == "refused" else "verified", [])]),
            (V100, 104, [("Apply Body Preset", "Krystal", "verified", []), ("Apply Expression", "Krystal", "verified",
                                                                             [])])]
    for i, (b, pid, ops) in enumerate(logs):
        write(os.path.join(q, "evidence", "logs", "CPM - 2026-11-12_12-0%d-00Z - pid%d - s - 001.log" % (i, pid)),
              log_text(b, pid, ops))
    after = os.path.join(q, "evidence", "library_after", "Characters")
    recs = [("engineer--1", names["engineer_pose"], 3, "full_body", 72, "models/player/engineer.mdl", None),
            ("krystal2020--7d2aee52ef3a", names["krystal_pose"], 3, "selected_parts", 6, "models/k.mdl", None),
            ("krystal2020--7d2aee52ef3a", "NQ1 Pose B", 1, None, 0, "models/k.mdl", {"left_arm": {}})]
    if soldier:
        recs.append(("soldier--1", names["soldier_pose"], 3, "full_body", 70, "models/player/soldier.mdl", None))
    lib_rows = []
    for d, name, v, kind, n, model, regions in recs:
        pose = {"version": v, "source": {"model_ref": model}}
        if v == 3:
            pose.update(scope={"kind": kind, "posed": ["b%d" % i for i in range(n)]},
                        engine={"rule": "direct_fk_v1", "revision": 1})
        else:
            pose["regions"] = regions
        jdump(os.path.join(after, d, "Poses", name + ".json"), {"name": name, "pose": pose})
        lib_rows.append({"status": "added", "path": "Characters/%s/Poses/%s.json" % (d, name), "sha256": name})
    for tag in ("K", "V100"):
        jdump(os.path.join(q, "evidence", "library_%s.json" % tag), {"differences": lib_rows})
    jdump(os.path.join(q, "evidence", "rollback.json"), {"rolled_back": True, "library_untouched": True,
                                                         "installation": "v1.0.0"})
    jdump(os.path.join(q, "evidence", "cleanup.json"), {"restored": True, "installation": "v1.0.0"})
    for name, digest in c["session_pins"].items():
        write(os.path.join(q, "sessions", name), b"session " + name.encode("ascii"))
        c["session_pins"][name] = sha_bytes(b"session " + name.encode("ascii"))
    prod = {"cpm_build_sha256": CAND, "registry_mode": "production", "release_version": "1.1.0",
            "scope_rules": {"direct_fk_v1": {"revision": 1, "status": "qualified"}}, "carried_enabled": [False],
            "extrapolation_qualified": [False], "qualification_fault": [None], "recovery_paused": False,
            "registry": {"registry_sha256": c["pins"]["profile_sha256"], "body_loaded": True,
                         "mappings": [["left_arm", "qualified"]]}}

    def undo(u, r=""):
        return {"session": {"undo": {"undo_desc": u, "redo_desc": r}}}
    e, s, k = ("Apply Pose " + names[x] for x in ("engineer_pose", "soldier_pose", "krystal_pose"))
    states = {"S-PROD": prod, "S-E-INFO": {"pose_info": {"rows": [
        ["Includes:", "Full body, including hip movement", None], ["Not included:", "Facial expressions, rootTransform",
                                                                   None]]}},
              "S-E-APPLY": undo(e), "S-E-UNDO": undo("Change Recording State", "Redo " + e), "S-E-REDO": undo(e),
              "S-SOLDIER-SAVED": {}, "S-SOLDIER-APPLY": undo(s), "S-SOLDIER-UNDO": undo("x", "Redo " + s),
              "S-HEAVY": {"character": {"model": "models/player/heavy.mdl"}}, "S-K-GRIP": {},
              "S-K-GRIP-APPLY": undo(k), "S-K-UNDO": undo("x", "Redo " + k), "S-K-REDO": undo(k),
              "S-K-LEGACY": dict(undo("Apply Pose NQ1 Pose B"), selected_pose={"version": 1, "regions": ["left_arm"]}),
              "S-K-PRESETS": {"release_version": "1.1.0"}, "S-V100": {"cpm_build_sha256": V100},
              # A0/B0 before; B1 after editing B and saving from it; A1 after the Apply onto A; Undo back to A0.
              "S-K-DUP-BEFORE": dup_sets("A0", "B0"), "S-K-DUP-SAVED": dup_sets("A0", "B1"),
              "S-K-DUP-APPLY": dup_sets("A0" if dup == "refused" else "A1",
                                        "B2" if dup == "peer" else "B1"),
              "S-K-DUP-UNDO": dup_sets("A0", "B2" if dup == "peer" else "B1")}
    for step, d in states.items():
        jdump(os.path.join(q, "observations", step + ".json"), d)
    report = dict(c["operator_expect"])
    report["clean_closes"] = 4
    if ui:
        report["selected_parts_ui"] = {"verdict": ui, "observations": dict(
            (k, "observed") for k in C.UI_OBSERVATIONS)}
        for i in range(1, 7):
            write(os.path.join(q, "screenshots", "SP-%d.png" % i), b"png")
    jdump(os.path.join(q, "evidence", "OPERATOR_REPORT.json"), report)
    return c


if PY3:
    class CompareTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="ps2cmp")

        def tearDown(self):
            shutil.rmtree(self.dir, True)

        def verdict(self, c):
            out = sys.stdout
            sys.stdout = io.StringIO()
            try:
                return C.main(c)
            finally:
                sys.stdout = out

        def test_complete_run_passes(self):
            v = self.verdict(synthetic_run(self.dir))
            self.assertEqual((v["verdict"], v["failed"]), ("PASS", []), [x for x in v["checks"] if x["result"] != "PASS"])

        def test_duplicate_model_target_identity_and_peer_isolation(self):
            v = self.verdict(synthetic_run(self.dir))
            names = [x["check"] for x in v["checks"] if x["check"].startswith("duplicate.")]
            self.assertIn("duplicate.peer_isolation_second_instance_unchanged", names)
            self.assertIn("duplicate.apply_targets_the_selected_original", names)
            shutil.rmtree(self.dir)
            v = self.verdict(synthetic_run(self.dir, dup="wrong_target"))
            self.assertIn("duplicate.apply_targets_the_selected_original", v["failed"])
            shutil.rmtree(self.dir)
            v = self.verdict(synthetic_run(self.dir, dup="peer"))
            self.assertIn("duplicate.peer_isolation_second_instance_unchanged", v["failed"])
            shutil.rmtree(self.dir)
            v = self.verdict(synthetic_run(self.dir, dup="refused"))
            self.assertEqual(v["verdict"], "PASS WITH FINDINGS")
            self.assertTrue(any("refused safely" in f for f in v["findings"]))

        def test_ui_acceptance_is_the_owners_and_separate(self):
            v = self.verdict(synthetic_run(self.dir))
            self.assertEqual(v["selected_parts_ui"]["acceptance"], "ACCEPTED")
            shutil.rmtree(self.dir)
            v = self.verdict(synthetic_run(self.dir, ui=None))
            self.assertEqual((v["verdict"], v["selected_parts_ui"]["acceptance"]), ("PASS", "NOT ACCEPTED"))
            shutil.rmtree(self.dir)
            v = self.verdict(synthetic_run(self.dir, ui="NOT ACCEPTED"))
            self.assertEqual(v["selected_parts_ui"]["acceptance"], "NOT ACCEPTED")

        def test_soldier_refusal_is_a_finding_not_a_pass(self):
            v = self.verdict(synthetic_run(self.dir, soldier=False))
            self.assertEqual(v["verdict"], "PASS WITH FINDINGS")
            self.assertTrue(any("soldier" in f for f in v["findings"]))

        def expect_fail(self, mutate, check):
            c = synthetic_run(self.dir)
            mutate(self.dir, c)
            v = self.verdict(c)
            self.assertEqual(v["verdict"], "FAIL")
            self.assertIn(check, v["failed"])

        def test_counterexamples(self):
            def qual_build(q, c):
                path = os.path.join(q, "observations", "S-PROD.json")
                d = rjson(path)
                d["registry_mode"] = "qualification"
                jdump(path, d)
            self.expect_fail(qual_build, "production.build_mode_rules_and_switches")
            shutil.rmtree(self.dir)

            def unverified(q, c):
                path = sorted(os.listdir(os.path.join(q, "evidence", "logs")))[1]
                path = os.path.join(q, "evidence", "logs", path)
                text = rtext(path).replace("outcome=u'verified'", "outcome=u'committed-unverified'", 1)
                write(path, text + "x | PROD_POSE_SCOPE-committed-unverified\n")
            self.expect_fail(unverified, "safety.every_candidate_pose_apply_verified")
            shutil.rmtree(self.dir)

            def poses_changed(q, c):
                path = os.path.join(q, "evidence", "library_V100.json")
                d = rjson(path)
                d["differences"][0]["sha256"] = "changed"
                jdump(path, d)
            self.expect_fail(poses_changed, "rollback.v100_leaves_the_poses_folders_unchanged")
            shutil.rmtree(self.dir)

            def heavy_saved(q, c):
                jdump(os.path.join(q, "evidence", "library_after", "Characters", "heavy--1", "Poses", "H.json"),
                      {"name": "H", "pose": {"version": 3, "scope": {"kind": "full_body", "posed": []},
                                             "source": {"model_ref": "models/player/heavy.mdl"}}})
            self.expect_fail(heavy_saved, "heavy.full_body_refused_nothing_saved")
            shutil.rmtree(self.dir)

            def v2_saved(q, c):
                jdump(os.path.join(q, "evidence", "library_after", "Characters", "k", "Poses", "B.json"),
                      {"name": "B", "pose": {"version": 2, "regions": {"full_body": {}}}})
            self.expect_fail(v2_saved, "krystal.no_version_2_full_body_saved_in_production")
            shutil.rmtree(self.dir)

            def wording(q, c):
                path = os.path.join(q, "observations", "S-E-INFO.json")
                jdump(path, {"pose_info": {"rows": [["Includes:", "Full body", None]]}})
            self.expect_fail(wording, "engineer.pose_info_wording")
            shutil.rmtree(self.dir)

            def not_restored(q, c):
                jdump(os.path.join(q, "evidence", "cleanup.json"), {"restored": False, "installation": "v1.0.0",
                                                                    "inventory_problems": ["LIBRARY"]})
            self.expect_fail(not_restored, "restore.v100_installed_library_and_every_inventory_equal_baselines")
            shutil.rmtree(self.dir)

            def session_saved(q, c):
                write(os.path.join(q, "sessions", "PS2_KRYSTAL.dmx"), b"saved")
            self.expect_fail(session_saved, "sessions.copies_never_saved")


if __name__ == "__main__":
    unittest.main()
