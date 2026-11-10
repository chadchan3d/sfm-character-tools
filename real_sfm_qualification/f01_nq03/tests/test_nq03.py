# -*- coding: ascii -*-
"""Offline tests of the F-01 NQ-03 header inventory kit (Python 2.7 and 3; the tool and analysis tests need 3).

- The observer against the S0 kit's fake SFM with a fake model cache: read-only (no scene mutation), every candidate
  found, read and released, a missing or error model recorded, an unreadable bone recorded (never inferred), refusals
  write nothing.
- The analysis: a model without procedural declarations is a candidate; QUATINTERP, jiggle and flag-only
  declarations are declared-procedural; unreadable rows, missing constants and error models give no conclusion.
- The tool: resolve follows the gameinfo search order (first loose file wins) and refuses a models list that is not
  the resolved files; the reused tools carry this kit's pinned files.
They show nothing about SFM.
Run: python -I test_nq03.py   (SFM's Python 2.7: python -E -s -B test_nq03.py)
"""
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
OBSERVER = os.path.join(ROOT, "observer", "F01_NQ03_Inventory.py")
sys.path.insert(0, os.path.join(REPO, "real_sfm_qualification", "f01_full_body_s0", "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fake_sfm_s0 as F  # noqa: E402

PY3 = sys.version_info[0] >= 3
PROC = {"STUDIO_PROC_AXISINTERP": 1, "STUDIO_PROC_QUATINTERP": 2, "STUDIO_PROC_AIMATBONE": 3,
        "STUDIO_PROC_AIMATATTACH": 4, "STUDIO_PROC_JIGGLE": 5, "STUDIO_PROC_TWIST_MASTER": 6,
        "STUDIO_PROC_TWIST_SLAVE": 7, "STUDIO_PROC_POINT_CONSTRAINT": 8, "STUDIO_PROC_ORIENT_CONSTRAINT": 9,
        "STUDIO_PROC_AIM_CONSTRAINT": 10, "BONE_PHYSICALLY_SIMULATED": 0x01, "BONE_PHYSICS_PROCEDURAL": 0x02,
        "BONE_ALWAYS_PROCEDURAL": 0x04, "BONE_SCREEN_ALIGN_SPHERE": 0x08, "BONE_SCREEN_ALIGN_CYLINDER": 0x10}
INVALID = 65535
with io.open(os.path.join(ROOT, "candidates.json"), "rb") as f:
    CANDIDATES = [c["path"] for c in json.loads(f.read().decode("utf-8"))["candidates"]]


class Sink(object):
    def write(self, data):
        if not isinstance(data, bytes):
            raise TypeError("the observer printed a non-byte string on Python 2")


class Bone(object):
    def __init__(self, name, parent, proctype=0, flags=0x100):
        self.name, self.parent, self.proctype, self.flags = name, parent, proctype, flags
        self.procindex, self.physicsbone = (12 if proctype else 0), -1

    def pszName(self):
        return self.name


class Header(object):
    def __init__(self, name, bones, broken=None):
        self.name, self.bones, self.broken = name, bones, broken
        self.numbones, self.checksum, self.numlocalattachments = len(bones), 77, 1

    def pBone(self, i):
        if self.broken == i:
            raise RuntimeError("pBone failed (test)")
        return self.bones[i]

    def pLocalAttachment(self, i):
        return types.SimpleNamespace(localbone=0) if PY3 else type("A", (), {"localbone": 0})()

    def BoneFlexDriverCount(self):
        return 0

    def BoneFlexDriver(self, i):
        raise AssertionError("no flex drivers")


def plain_bones(extra=()):
    return [Bone("root", -1), Bone("spine", 0), Bone("hand", 1)] + list(extra)


class Cache(object):
    """A fake IMDLCache: path -> header; records every call so read-only use can be asserted."""

    def __init__(self, headers, error=()):
        self.headers, self.error, self.calls, self.refs = headers, set(error), [], {}
        self.handles = dict((p, i + 1) for i, p in enumerate(sorted(headers)))

    def FindMDL(self, path):
        self.calls.append(("FindMDL", path))
        h = self.handles.get(path, INVALID)
        if h != INVALID:
            self.refs[h] = self.refs.get(h, 0) + 1
        return h

    def IsErrorModel(self, h):
        return [p for p, x in self.handles.items() if x == h][0] in self.error

    def GetStudioHdr(self, h):
        return self.headers[[p for p, x in self.handles.items() if x == h][0]]

    def Release(self, h):
        self.calls.append(("Release", h))
        self.refs[h] -= 1
        return self.refs[h]


def default_headers(**overrides):
    out = dict((p, Header(p, plain_bones())) for p in CANDIDATES)
    out.update(overrides)
    return out


def run(folder, label, cache, animset="Krystal"):
    world, S, sfm, vs = F.install()
    studio = types.ModuleType("vs.studio")
    for k, v in PROC.items():
        setattr(studio, k, v)
    studio.g_pMDLCache, studio.MDLHANDLE_INVALID = cache, INVALID
    vs.studio = studio
    sys.modules["sfmApp"], sys.modules["vs"], sys.modules["vs.studio"] = sfm, vs, studio
    g = {"__name__": "__nq03__", "NQ_DIR": folder, "NQ_REPO": REPO, "NQ_LABEL": label, "NQ_ANIMSET": animset}
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
        return world, json.loads(f.read().decode("utf-8")), printed


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nq03test")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_reads_every_candidate_read_only_and_releases_each_handle(self):
        cache = Cache(default_headers())
        world, obs, printed = run(self.dir, "NQ03-01", cache)
        self.assertEqual(world.mutations, [])
        self.assertTrue(obs["readonly"]["unchanged"])
        self.assertEqual(obs["problems"], [])
        models = obs["nq03"]["models"]
        self.assertEqual([m["path"] for m in models], CANDIDATES)
        self.assertTrue(all(m["status"] == "read" for m in models))
        self.assertEqual(sorted(cache.refs.values()), [0] * len(CANDIDATES))
        self.assertEqual(models[0]["bones"][2]["name"], {"status": "READ", "value": "hand"})
        if PY3:
            self.assertIn("NQ03 NQ03-01: OK models=24 read=24 not_read=0 no_procedural_declaration=24", printed)

    def test_missing_error_and_unreadable_models_are_recorded_not_inferred(self):
        headers = default_headers()
        del headers[CANDIDATES[0]]
        headers[CANDIDATES[2]] = Header(CANDIDATES[2], plain_bones(), broken=1)
        cache = Cache(headers, error=[CANDIDATES[1]])
        world, obs, printed = run(self.dir, "NQ03-02", cache)
        models = dict((m["path"], m) for m in obs["nq03"]["models"])
        self.assertEqual(models[CANDIDATES[0]]["status"], "not-found")
        self.assertEqual(models[CANDIDATES[1]]["error_model"], {"status": "READ", "value": True})
        self.assertIn("unreadable", models[CANDIDATES[2]]["bones"][1])

    def test_refuses_without_writing(self):
        run(self.dir, "NQ03-03", Cache(default_headers()))
        self.assertRaises(RuntimeError, run, self.dir, "NQ03-03", Cache(default_headers()))
        self.assertRaises(RuntimeError, run, self.dir, "NQ-03", Cache(default_headers()))
        self.assertRaises(RuntimeError, run, self.dir, "NQ03-04", Cache(default_headers()), "nobody")
        self.assertEqual(os.listdir(os.path.join(self.dir, "observations")), ["NQ03-03.json"])

    def test_calls_no_mutating_api(self):
        with io.open(OBSERVER, "rb") as f:
            text = f.read().decode("ascii")
        for name in ("SetEvaluateProceduralBones", "SetKeyValue", "InsertKeyAtTime", "SetHeadTimeInSeconds",
                     "StartUndo", "SetValue(", "SaveDocument", "CreateElement", "AddRef(", "SetUserData",
                     "ResetErrorModelStatus", "SetAsyncLoad", "TouchAllData", "PreloadModel"):
            self.assertNotIn(name, text)


if PY3:
    import nq03_analyze as A  # noqa: E402
    import nq03_tool as T  # noqa: E402

    class AnalysisTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="nq03an")
            os.makedirs(os.path.join(self.dir, "observations"))

        def tearDown(self):
            shutil.rmtree(self.dir)

        def test_classification(self):
            headers = default_headers()
            headers["models/player/heavy.mdl"] = Header("heavy", plain_bones([Bone("hlp_forearm_L", 2, 2, 0x1C04)]))
            headers["models/alyx.mdl"] = Header("alyx", plain_bones([Bone("Breast_jiggle", 1, 5, 0x504)]))
            headers["models/barney.mdl"] = Header("barney", plain_bones([Bone("phys", 1, 0, 0x101)]))
            headers["models/kleiner.mdl"] = Header("kleiner", plain_bones(), broken=0)
            cache = Cache(headers, error=["models/police.mdl"])
            _, obs, _ = run(self.dir, "NQ03-05", cache)
            r = A.analyze(obs)
            cls = dict((m["path"], m["class"]) for m in r["models"])
            self.assertEqual(cls["models/player/heavy.mdl"], "declared-procedural")
            self.assertEqual([m for m in r["models"] if m["path"] == "models/player/heavy.mdl"][0]["declared"],
                             [{"name": "hlp_forearm_L", "proc": "STUDIO_PROC_QUATINTERP", "flags": 0x1C04}])
            self.assertEqual(cls["models/alyx.mdl"], "declared-procedural")
            self.assertEqual(cls["models/barney.mdl"], "declared-procedural")     # physically simulated flag only
            self.assertEqual(cls["models/kleiner.mdl"], "unreadable")
            self.assertEqual(cls["models/police.mdl"], "not-loaded")
            self.assertEqual(cls["models/player/scout.mdl"], "candidate")
            self.assertEqual(len(r["candidates"]), 19)

        def test_missing_constants_give_no_conclusion(self):
            _, obs, _ = run(self.dir, "NQ03-06", Cache(default_headers()))
            del obs["nq03"]["constants"]["BONE_ALWAYS_PROCEDURAL"]
            self.assertEqual(A.analyze(obs)["candidates"], [])

    class ToolTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="nq03tool")
            game = os.path.join(self.dir, "game")
            os.makedirs(os.path.join(game, "usermod"))
            with open(os.path.join(game, "usermod", "gameinfo.txt"), "w") as f:
                f.write('"GameInfo"\n{\n FileSystem\n {\n  "SearchPaths"\n  {\n   "Game" "|gameinfo_path|."\n'
                        '   "Game" "first"\n   "Game" "second"\n  }\n }\n}\n')
            for folder in ("first", "second"):
                for path in CANDIDATES:
                    full = os.path.join(game, folder, path.replace("/", os.sep))
                    if folder == "second" or path.endswith("heavy.mdl"):
                        if not os.path.isdir(os.path.dirname(full)):
                            os.makedirs(os.path.dirname(full))
                        with open(full, "wb") as f:
                            f.write((folder + path).encode("ascii"))
            self.c = {"paths": {"GAME": game, "REPO": REPO, "Q": os.path.join(self.dir, "Q")},
                      "models": ["first/models/player/heavy.mdl" if p.endswith("heavy.mdl") else "second/" + p
                                 for p in CANDIDATES]}

        def tearDown(self):
            shutil.rmtree(self.dir)

        def test_resolve_follows_the_search_order_and_pins_each_file(self):
            order, rows = T.resolve(self.c)
            self.assertEqual(order, ["usermod", "first", "second"])
            heavy = [r for r in rows if r["path"].endswith("heavy.mdl")][0]
            self.assertEqual(heavy["folder"], "first")
            T.cmd_resolve(self.c)
            with open(os.path.join(self.dir, "Q", "evidence", "resolution.json"), "rb") as f:
                data = json.loads(f.read().decode("utf-8"))
            self.assertEqual(len(data["models"]), len(CANDIDATES))
            self.assertTrue(all(len(r["sha256"]) == 64 for r in data["models"]))

        def test_resolve_refuses_a_models_list_that_is_not_the_resolved_files(self):
            self.c["models"] = self.c["models"][1:]
            self.assertRaises(SystemExit, T.cmd_resolve, self.c)
            self.assertFalse(os.path.exists(os.path.join(self.dir, "Q", "evidence", "resolution.json")))

        def test_the_reused_tools_pin_this_kits_files(self):
            files = T.M.kit_files(self.c)
            self.assertEqual(sorted(files), ["candidates", "s0_observer", "wrapper"])
            self.assertTrue(files["wrapper"].endswith("F01_NQ03_Inventory.py"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
