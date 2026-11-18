# -*- coding: ascii -*-
"""F-01 H1 kit: the capture script on SFM's Python 2.7.5 (also runs on 3.10), against a fake CPM module and fake SFM
modules. It shows the capture's own behaviour only (refusals, exclusive create, recorded fields, no writes), nothing
about SFM.

Usage: <SFM python 2.7.5> -E -B test_h1_capture.py   (or python -I test_h1_capture.py)
"""
from __future__ import print_function

import ast
import json
import os
import re
import shutil
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
CAPTURE = os.path.join(KIT, "observer", "F01_H1_Capture.py")
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


class Named(object):
    def __init__(self, name):
        self.name = name

    def GetName(self):
        return self.name


def fake_world(names):
    sets = [Named(n) for n in names]
    shot = Named(u"shot15")
    shot.animationSets = sets
    dm = types.SimpleNamespace() if hasattr(types, "SimpleNamespace") else Named(u"dm")
    dm.CanUndo = lambda: True
    dm.CanRedo = lambda: False
    dm.GetUndoDesc = lambda: u"Rotate"
    dm.GetRedoDesc = lambda: u""
    dm.GetFileName = lambda fid: u"E:\\run\\sessions\\H1_SESSION.dmx"
    sfm = types.ModuleType("sfmApp")
    sfm.GetShotAtCurrentTime = lambda: shot
    sfm.GetHeadTimeInSeconds = lambda: 0.2083
    sfm.GetDocumentRoot = lambda: types.ModuleType("root")
    sfm.GetDocumentRoot().GetFileId = lambda: 1
    root = types.ModuleType("root")
    root.GetFileId = lambda: 1
    sfm.GetDocumentRoot = lambda: root
    vs = types.ModuleType("vs")
    vs.g_pDataModel = dm
    return sfm, vs, sets


def fake_cpm(calls):
    cpm = types.ModuleType("chadchan3d_cpm_app")
    cpm.__chadchan3d_cpm_build_sha256__ = "q" * 64
    cpm.PROD_POSE_REGISTRY_MODE = u"qualification"

    def gm_of(animset):
        calls.append(("get_game_model", animset.name))
        return Named(u"gm_" + animset.name)
    cpm.get_game_model = gm_of
    cpm.prod_pose_attr = lambda obj, name: getattr(obj, name) if name != u"modelName" else u"models/player/heavy.mdl"
    cpm.prod_pose_seq = lambda value, cap=None: list(value)

    def live(row):
        calls.append(("prod_scope_live", row["animset"].name))
        return {u"clip_channels": [Named(u"bip_pelvis_o"), Named(u"hlp_forearm_L_o")],
                u"bones": {u"bip_pelvis": {u"dag": u"d0"}, u"hlp_forearm_L": {u"dag": u"d77"}}}
    cpm.prod_scope_live = live

    def authored(ch, budget):
        budget[0] += 2
        bone = u"bone 0 (bip_pelvis)" if ch.name.startswith(u"bip") else u"bone 77 (hlp_forearm_L)"
        return {u"id": {u"name": ch.name}, u"binding": {u"toElement": {u"status": u"READ", u"value": {u"name": bone}},
                                                         u"toAttribute": {u"status": u"READ",
                                                                          u"value": u"orientation"}},
                u"layers": [[0, [0.0, 0.0, 0.0, 1.0]]]}
    cpm.prod_pose_channel_authored = authored
    cpm.prod_pose_transform_state = lambda dag: {u"local_position": [0.0, 0.0, 1.0],
                                                 u"local_orientation": [0.0, 0.0, 0.0, 1.0],
                                                 u"world_position": [1.0, 2.0, 3.0],
                                                 u"world_orientation": [0.0, 0.0, 0.0, 1.0]}
    cpm.prod_scope_helper_evidence = lambda L: {u"status": u"READ", u"bones": [
        {u"index": 0, u"name": u"bip_pelvis", u"parent": -1, u"flags": 256, u"proctype": 0},
        {u"index": 77, u"name": u"hlp_forearm_L", u"parent": 0, u"flags": 7172, u"proctype": 2}],
        u"attachments": [6], u"flex_drivers": []}

    def state(row):
        calls.append(("prod_scope_state", row["animset"].name))
        return {u"C": {u"bones": {u"bip_pelvis": {u"class": u"direct-fk"},
                                  u"hlp_forearm_L": {u"class": u"carried-candidate"}}},
                u"helpers": [u"hlp_forearm_L"], u"helper_refusals": {}}
    cpm.prod_scope_state = state
    return cpm


def load():
    g = {"__name__": "h1_capture_under_test"}
    with open(CAPTURE, "rb") as f:
        exec(compile(f.read(), CAPTURE, "exec"), g)
    return g


def main():
    print("Interpreter: %s" % sys.version.split()[0])
    tmp = tempfile.mkdtemp(prefix="h1_cap_")
    saved = dict((k, sys.modules.get(k)) for k in ("sfmApp", "vs", "chadchan3d_cpm_app"))
    try:
        os.makedirs(os.path.join(tmp, "observations"))
        calls = []
        sfm, vs, sets = fake_world([u"heavy", u"heavy1", u"heavy2", u"krystal"])
        sys.modules["sfmApp"], sys.modules["vs"] = sfm, vs
        s = load()
        g = {"H1_DIR": tmp, "H1_SOURCE": u"heavy", "H1_TARGET": u"heavy1", "H1_PEER": u"heavy2", "H1_STEP": "BASE"}
        try:
            s["h1_capture"](dict(g))
            refused = False
        except RuntimeError:
            refused = True
        check("C1 refuses without a loaded CPM, writing nothing",
              refused and not os.listdir(os.path.join(tmp, "observations")))
        sys.modules["chadchan3d_cpm_app"] = fake_cpm(calls)
        for label, change in (("missing names", {"H1_PEER": None}), ("repeated names", {"H1_PEER": u"heavy1"}),
                              ("unknown step", {"H1_STEP": "LATER"})):
            bad = dict(g)
            bad.update(change)
            try:
                s["h1_capture"](bad)
                refused = False
            except RuntimeError:
                refused = True
            check("C1 refuses %s, writing nothing" % label,
                  refused and not os.listdir(os.path.join(tmp, "observations")))
        data = s["h1_capture"](dict(g))
        path = os.path.join(tmp, "observations", "H1-BASE.json")
        with open(path, "rb") as f:
            written = json.loads(f.read().decode("utf-8"))
        check("C2 writes H1-BASE.json with the three roles, build and session",
              sorted(written["sets"]) == ["peer", "source", "target"] and written["cpm_build_sha256"] == "q" * 64 and
              written["session"]["undo"]["undo_desc"] == u"Rotate" and written["errors"] == [], written["errors"])
        tgt = written["sets"]["target"]
        check("C2 records channel digests with their bones, bones, header and admission",
              tgt["channels"][u"hlp_forearm_L_o"]["to"] == u"bone 77 (hlp_forearm_L)" and
              len(tgt["channels"][u"hlp_forearm_L_o"]["sha256"]) == 64 and sorted(tgt["bones"]) ==
              [u"bip_pelvis", u"hlp_forearm_L"] and tgt["header"]["declared"] == [[77, u"hlp_forearm_L", 0, 7172, 2]]
              and tgt["admission"]["helpers"] == [u"hlp_forearm_L"], tgt)
        check("C2 only the named sets are read", sorted(set(c[1] for c in calls)) == [u"heavy", u"heavy1", u"heavy2"])
        try:
            s["h1_capture"](dict(g))
            again = False
        except RuntimeError:
            again = True
        check("C3 a second capture of the same step refuses (exclusive create)", again)
        g2 = dict(g, H1_STEP="SAVED", H1_PEER=u"nobody")
        data = s["h1_capture"](g2)
        check("C3 an absent set is recorded as an error, not guessed", data["errors"] and "peer" not in data["sets"],
              data["errors"])

        with open(CAPTURE, "rb") as f:
            src_bytes = f.read()
        src = src_bytes.decode("ascii")
        called = set()
        for node in ast.walk(ast.parse(src_bytes)):
            if isinstance(node, ast.Call):
                fn = node.func
                called.add(fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None))
        forbidden = set(["SetValue", "SetKeyValue", "InsertKeyAtTime", "Operate", "StartUndo", "FinishUndo",
                         "AbortUndoableOperation", "Undo", "Redo", "ProcessEvents", "SetHeadTimeInSeconds",
                         "same_time_refresh", "remove", "unlink", "rename", "rmtree", "makedirs", "prod_scope_apply",
                         "prod_scope_capture", "prod_pose_save_new"])
        check("C4 no scene write, refresh, Undo, Save, Apply or file removal of its own",
              not called & forbidden, sorted(called & forbidden))
        opens = re.findall(r"(?<![\w.])open\(([^)]*)\)", src)
        check("C4 its only write is the exclusive-create capture", src.count("os.open(") == 1 and "O_EXCL" in src and
              opens == ['cpm.__file__.replace(".pyc", ".py"'] and
              'open(cpm.__file__.replace(".pyc", ".py"), "rb")' in src and "vsUtils" not in src, opens)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        shutil.rmtree(tmp, True)
    passed = sum(1 for r in RESULTS if r[1])
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
