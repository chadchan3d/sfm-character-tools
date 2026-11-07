# -*- coding: ascii -*-
"""Offline tests of the F-01 full-body S3 kit.

- The observer wrapper against the S0 suite's fake SFM (Python 2.7 and 3): it runs the pinned S0 observer unchanged,
  writes the observation and its sidecar, never mutates the scene, refuses a repeated step and reports a step whose
  editor, shot or playhead differ.
- s3_tool build (Python 3): the qualification CPM differs from the candidate in exactly one line; a wrong pin refuses.
- s3_compare (Python 3): a complete synthetic run that meets every Expected result is PASS, and each counterexample
  (an Apply that moves nothing, a changed facial control, a posed bone off by 0.05 degrees, a preserved bone moved,
  unrelated animation changed, a no-op that writes, an Undo that does not restore, an insert where an update was
  expected, an Update that did not replace the posture, no restart, a slow or unverified Apply, an Abort that
  changes the document) is FAIL.

Run: python -I test_s3.py   (SFM's Python 2.7: python -E -s test_s3.py runs the wrapper tests only)
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
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RSQ = os.path.dirname(ROOT)
REPO = os.path.dirname(RSQ)
WRAPPER = os.path.join(ROOT, "observer", "F01_S3_Observe.py")
sys.path.insert(0, os.path.join(RSQ, "f01_full_body_s0", "tests"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fake_sfm_s0 as F  # noqa: E402

PY3 = sys.version_info[0] >= 3
if PY3:
    import s3_compare as C  # noqa: E402
    import s3_tool as T3  # noqa: E402


def load(path):
    with io.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


class Sink(object):
    def write(self, data):
        if not isinstance(data, bytes):
            raise TypeError("non-byte output on Python 2")


def run_wrapper(folder, step):
    world, S, sfm, vs = F.install()
    sys.modules["sfmApp"], sys.modules["vs"] = sfm, vs
    g = {"__name__": "__s3__", "S3_DIR": folder, "S3_REPO": REPO, "S3_STEP": step}
    with io.open(WRAPPER, "rb") as f:
        code = compile(f.read(), WRAPPER, "exec")
    saved = sys.stdout
    out = io.StringIO() if PY3 else Sink()
    sys.stdout = out
    try:
        exec(code, g)
    finally:
        sys.stdout = saved
    return world, (out.getvalue() if PY3 else None)


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="s3test")
        os.makedirs(os.path.join(self.dir, "observations"))

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_observes_read_only_and_writes_the_sidecar(self):
        world, printed = run_wrapper(self.dir, "A1")
        self.assertEqual(world.mutations, [])
        with io.open(os.path.join(self.dir, "observations", "S0-01.json"), "rb") as f:
            obs = json.loads(f.read().decode("utf-8"))
        with io.open(os.path.join(self.dir, "observations", "S0-01.s3.json"), "rb") as f:
            side = json.loads(f.read().decode("utf-8"))
        self.assertEqual((side["step"], side["label"], side["format"]), ("A1", "S0-01", "F01-S3-sidecar-v1"))
        self.assertTrue(obs["readonly"]["unchanged"])
        self.assertEqual(len(side["outside"]["sha256"]), 64)
        self.assertEqual(side["outside"]["unreadable"], 0)
        with io.open(os.path.join(RSQ, "f01_full_body_s0", "observer", "F01_S0_Survey.py"), "rb") as f:
            self.assertEqual(side["observer_sha256"], sha_bytes(f.read()))
        self.assertEqual(side["mismatch"], [])
        if PY3:
            self.assertIn("S3 STEP A1 (S0-01): OK", printed)

    def test_a_repeated_step_is_refused(self):
        run_wrapper(self.dir, "A1")
        self.assertRaises(RuntimeError, run_wrapper, self.dir, "A1")

    def test_a_wrong_shot_is_reported(self):
        world, printed = run_wrapper(self.dir, "B2")
        with io.open(os.path.join(self.dir, "observations", "S0-09.s3.json"), "rb") as f:
            side = json.loads(f.read().decode("utf-8"))
        self.assertTrue(any("shot" in m for m in side["mismatch"]))
        if PY3:
            self.assertIn("MISMATCH - STOP", printed)

    def test_unknown_step_refused(self):
        self.assertRaises(RuntimeError, run_wrapper, self.dir, "Z9")

    def test_step_table_matches_the_comparator(self):
        with io.open(WRAPPER, "rb") as f:
            text = f.read().decode("ascii")
        table = dict(re.findall(r'"([AB]\d+)": \("(S0-\d\d)"', text))
        if PY3:
            self.assertEqual(table, C.LABELS)
        self.assertEqual(len(table), 24)


# --- s3_tool build ------------------------------------------------------------------------------------------------

if PY3:
    class BuildTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="s3build")
            src = os.path.join(REPO, "cpm", "app", "SFM_Character_Preset_Manager.py")
            self.candidate = os.path.join(self.dir, "candidate.py")
            shutil.copyfile(src, self.candidate)
            with open(os.path.join(ROOT, "s3.template.json"), "rb") as f:
                c = json.loads(f.read().decode("utf-8"))
            c["paths"].update(Q=os.path.join(self.dir, "Q"), REPO=REPO, GAME=self.dir, SESSIONS=self.dir,
                              CANDIDATE=self.candidate, R2_FIXTURE=self.candidate, LEGACY_POSE=self.candidate,
                              LIBRARY=self.dir)
            c["pins"]["candidate_cpm_sha256"] = T3.T.sha(self.candidate)
            self.cfg = os.path.join(self.dir, "s3.json")
            with open(self.cfg, "wb") as f:
                f.write(json.dumps(c).encode("utf-8"))
            os.makedirs(os.path.join(self.dir, "Q"))

        def tearDown(self):
            shutil.rmtree(self.dir, True)

        def test_build_changes_exactly_the_registry_mode_line(self):
            T3.cmd_build(T3.load(self.cfg))
            ids = T3.T.read_json(os.path.join(self.dir, "Q", "staged", "IDENTITIES.json"))
            with open(self.candidate, "rb") as f:
                a = f.read().split(b"\n")
            with open(os.path.join(self.dir, "Q", "staged", "SFM_Character_Preset_Manager.py"), "rb") as f:
                b = f.read().split(b"\n")
            self.assertEqual([i for i in range(len(a)) if a[i] != b[i]], [ids["changed_line"] - 1])
            self.assertEqual(b[ids["changed_line"] - 1], b'PROD_POSE_REGISTRY_MODE = u"qualification"')
            self.assertEqual(ids["body_profile_sha256"], T3.T.sha(os.path.join(self.dir, "Q", "staged",
                                                                             "cpm_body_profiles_v1.json")))
            self.assertEqual(ids["wrapper_sha256"], T3.T.sha(WRAPPER))

        def test_build_refuses_a_candidate_that_is_not_pinned(self):
            with open(self.candidate, "ab") as f:
                f.write(b"\n# changed\n")
            self.assertRaises(SystemExit, T3.cmd_build, T3.load(self.cfg))
            self.assertFalse(os.path.exists(os.path.join(self.dir, "Q", "staged")))

        def test_placeholders_refuse(self):
            self.assertRaises(SystemExit, T3.load, os.path.join(ROOT, "s3.template.json"))


# --- s3_compare on a synthetic run --------------------------------------------------------------------------------

BONES = {"bip_pelvis": (0.0, 0.0, 40.0), "bip_spine_0": (0.0, 0.0, 45.0), "bip_neck": (0.0, 0.0, 60.0),
         "bip_head": (0.0, 0.0, 65.0), "bip_UpperArm_l": (8.0, 0.0, 58.0), "bip_knee_l": (5.0, 0.0, 20.0),
         "bip_tail00": (0.0, -5.0, 40.0), "Ear_l": (2.0, 0.0, 70.0), "bip_index_0_l": (20.0, 0.0, 58.0),
         "bip_head_hair_back": (0.0, -2.0, 70.0), "jaw": (0.0, 2.0, 63.0), "bip_lowerArm_l_twist2": (14.0, 0.0, 58.0)}
UNPOSED = ("jaw", "bip_lowerArm_l_twist2")
WRITTEN = ["w%03d_p" % i for i in range(139)] + ["w%03d_o" % i for i in range(139)]
EXTRA = ["Smile_flex_channel", "eyes_rightleft_flex_channel", "jaw_o", "rig_root_p"]
LEFT = ["Hand_l_p", "Hand_l_o", "Elbow_l_p"]
T_CHAN = 50416
QUAL = "q" * 64
CHAR = "krystal2020--7d2aee52ef3a"


def qz(deg):
    r = math.radians(deg) / 2.0
    return [0.0, 0.0, math.sin(r), math.cos(r)]


def posture(base):
    return dict((b, base + 7.0 * i) for i, b in enumerate(sorted(BONES)))


def value_for(name, k):
    return [float(k), 0.5, -0.25] if name.endswith("_p") else qz(10.0 * k + len(name))


class Scene(object):
    def __init__(self, pid, document, placement_deg, angles):
        self.pid, self.document = pid, document
        self.placement = ([100.0, 50.0, 0.0], qz(placement_deg))
        self.angles = dict(angles)
        self.keys = dict((n, [[1000, value_for(n, 0)]]) for n in WRITTEN + EXTRA + LEFT)
        self.controls = {"Smile": 0.25, "eyes_rightleft": 0.6}
        self.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Modify Head Time", "redo_desc": ""}
        self.outside = "o" * 64
        self.mode, self.shot, self.head = "Motion Editor", "shot13", 0.375
        self.cpm = QUAL

    def digest(self):
        return sha_bytes(json.dumps([self.keys, self.undo], sort_keys=True).encode("utf-8"))

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
        for name, pos in BONES.items():
            rel = (list(pos), qz(self.angles[name]))
            wp, wq = C.compose(self.placement, rel)
            bones[name] = {"index": 0, "transform": {}, "dag": 1, "parent_bone": None, "local_position": list(pos),
                           "local_orientation": qz(self.angles[name]), "scale": {"status": "READ", "value": 1.0},
                           "world_position": wp, "world_orientation": wq}
        d = self.digest()
        session = {"head_seconds": self.head, "head_ticks": int(self.head * 10000),
                   "timeline_mode": {"name": self.mode}, "undo": dict(self.undo), "current_shot": self.shot}
        obs = {"format": "F01-S0-survey-v1", "label": label, "pid": self.pid, "problems": [],
               "document": self.document, "session_before": copy.deepcopy(session), "session_after": session,
               "readonly": {"digest_before": {"sha256": d}, "digest_after": {"sha256": d}, "unchanged": True},
               "shot": {}, "animation_set": {}, "time": {"t_chan": T_CHAN}, "scene": {}, "bones": bones,
               "model": {"state": {"world_position": [1.0, 2.0, 3.0], "world_orientation": qz(0.0),
                                   "local_position": [1.0, 2.0, 3.0], "local_orientation": qz(0.0),
                                   "scale": {"status": "READ", "value": 1.0}}},
               "rig": {"handles": {"rig_root": {"id": {}, "parents": [1], "local_position": self.placement[0],
                                                "local_orientation": self.placement[1],
                                                "world_position": self.placement[0],
                                                "world_orientation": self.placement[1]}}},
               "controls": [{"id": {"name": n}, "attributes": {"value": {"status": "READ", "value": v}}}
                            for n, v in sorted(self.controls.items())] +
                           [{"id": {"name": "w000"}, "attributes": {"valuePosition": self.keys["w000_p"][-1][1]}}],
               "channels": [self.channel(n) for n in sorted(self.keys)], "operators": [],
               "writer_index": {"destinations": {}, "slave_targets": {}}, "cpm_loaded": {"build_sha256": self.cpm}}
        side = {"format": "F01-S3-sidecar-v1", "step": step, "label": label, "mismatch": [],
                "outside": {"sha256": self.outside}}
        return obs, side

    def snapshot(self):
        return copy.deepcopy((self.keys, self.angles, self.undo, self.controls))

    def restore(self, snap):
        self.keys, self.angles, self.undo, self.controls = copy.deepcopy(snap)

    def write(self, names, values):
        for n in names:
            keys = self.keys[n]
            at = [k for k in keys if k[0] == T_CHAN]
            if at:
                at[0][1] = copy.deepcopy(values[n])
            else:
                keys.append([T_CHAN, copy.deepcopy(values[n])])
                keys.sort(key=lambda k: k[0])

    def apply(self, region, label):
        values = dict(region["positions"])
        values.update(region["orientations"])
        self.write(WRITTEN, values)
        for name, e in region["oracle"]["bones"].items():
            if name not in UNPOSED:
                self.angles[name] = e["_deg"]
        self.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Apply Pose " + label, "redo_desc": ""}


def region_from(scene, k):
    bones = {}
    for name, pos in BONES.items():
        rel = (list(pos), qz(scene.angles[name]))
        p, q = C.compose(C.invert(scene.placement), C.compose(scene.placement, rel))
        bones[name] = {"position": p, "orientation": q, "local_position": list(pos),
                       "local_orientation": qz(scene.angles[name]), "_deg": scene.angles[name]}
    return {"positions": dict((n, value_for(n, k)) for n in WRITTEN if n.endswith("_p")),
            "orientations": dict((n, value_for(n, k)) for n in WRITTEN if n.endswith("_o")), "oracle": {"bones": bones}}


def record(name, region, created, updated):
    return {"name": name, "kind": "pose", "preset_id": sha_bytes(name.encode("ascii"))[:32], "created_at": created,
            "updated_at": updated, "pose": {"version": 2, "regions": {"full_body": region}}}


class Synthetic(object):
    """One complete, correct S3 run; `faults` names the counterexample to inject."""

    def __init__(self, folder, faults=(), continuation=False):
        self.q, self.faults, self.continuation = folder, set(faults), continuation
        for d in ("staged", "observations", "evidence", "sessions", os.path.join("evidence", "logs"),
                  os.path.join("evidence", "library_poses", CHAR)):
            os.makedirs(os.path.join(folder, d))
        shutil.copyfile(os.path.join(REPO, "cpm", "pose_profiles", "cpm_body_profiles_v1.json"),
                        os.path.join(folder, "staged", "cpm_body_profiles_v1.json"))
        self.dump(os.path.join("staged", "IDENTITIES.json"), {"qualification_cpm_sha256": QUAL})
        self.log = []
        self.ms = 0

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
        self.dump(os.path.join("observations", label + ".s3.json"), side)

    def op(self, op_id, kind, lines, ms=300):
        stamp = lambda: "2026-11-07T10:%02d:%02d.%03dZ" % (self.ms // 60000, (self.ms // 1000) % 60, self.ms % 1000)
        self.log.append("%s #%06d s=x w=1 op=%d | PROD_OPERATION_BEGIN id=%d kind=u'%s' context=None" % (
            stamp(), len(self.log) + 1, op_id, op_id, kind))
        for text in lines:
            self.ms += ms
            self.log.append("%s #%06d s=x w=1 op=%d | %s" % (stamp(), len(self.log) + 1, op_id, text))
        self.ms += 50
        self.log.append("%s #%06d s=x w=1 op=%d | PROD_OPERATION_END id=%d" % (stamp(), len(self.log) + 1, op_id,
                                                                           op_id))

    def build(self):
        f = self.faults
        src = Scene(100, "e:/q/sessions/S3_SOURCE.dmx", 0.0, posture(1.0))
        src.shot, src.head = "shot15", 0.2083
        if self.continuation:
            src.cpm = "a" * 64                          # Process A ran in the source run, on its own build
        self.observe(src, "A1")
        src.angles = posture(20.0)
        self.observe(src, "A2")
        reg_a = region_from(src, 1)
        self.observe(src, "A3")
        src.angles = posture(40.0)
        self.observe(src, "A4")
        b_saved = region_from(src, 2)
        self.observe(src, "A5")
        src.angles = posture(65.0)
        self.observe(src, "A6")
        reg_b = b_saved if "update-not-replaced" in f else region_from(src, 3)
        self.observe(src, "A7")
        records = {"S3 Pose A--aaaa.json": record("S3 Pose A", reg_a, "t1", "t1"),
                   "S3 Pose B--bbbb.json": record("S3 Pose B", reg_b, "t2", "t3"),
                   "NQ1 Pose A--5273df2209ca.json": {"name": "NQ1 Pose A", "pose": {"version": 1, "regions": {}}},
                   "S3 Pose B--bbbb.json.bak": record("S3 Pose B", reg_a if "bak-wrong" in f else b_saved, "t2",
                                                      "t2")}
        lib = os.path.join(self.q, "evidence", "library_poses", CHAR)
        for name, r in records.items():
            with open(os.path.join(lib, name), "wb") as fh:
                fh.write(json.dumps(r).encode("utf-8"))
        files = dict((n, C.s0_hash(os.path.join(lib, n))) for n in records)
        for tag in ("A", "B"):
            self.dump(os.path.join("evidence", "library_%s.json" % tag), {"files": files})
        dest = Scene(100 if "no-restart" in f else 200, "e:/q/sessions/S3_DESTINATION.dmx", 35.0,
                     posture(20.0) if "destination-matches" in f else posture(-30.0))
        self.observe(dest, "B1")
        base = dest.snapshot()
        dest.apply(reg_a, "S3 Pose A")
        if "facial-changed" in f:
            dest.controls["Smile"] = 0.9
        if "posed-bone-off" in f:
            dest.angles["bip_tail00"] += 0.05
        if "preserved-moved" in f:
            dest.angles["jaw"] += 3.0
        if "outside-changed" in f:
            dest.outside = "x" * 64
        self.observe(dest, "B2")
        applied = dest.snapshot()
        dest.restore(base)
        dest.undo = dict(base[2], can_redo=True, redo_desc="Apply Pose S3 Pose A")
        if "undo-incomplete" in f:
            dest.keys["w001_p"].append([T_CHAN, value_for("w001_p", 1)])
        self.observe(dest, "B3")
        dest.restore(applied)
        self.observe(dest, "B4")
        if "noop-writes" in f:
            dest.keys["Smile_flex_channel"][0][1] = [0.3]
        self.observe(dest, "B5")
        dest.apply(reg_b, "S3 Pose B")
        if "update-inserts" in f:                      # a new key instead of the existing key updated in place
            dest.keys["w003_p"].append([T_CHAN + 1, value_for("w003_p", 3)])
        self.observe(dest, "B6")
        if "abort-changes" in f:
            dest.keys["w002_o"][-1][1] = qz(1.0)
        self.observe(dest, "B7")
        self.observe(dest, "B8")
        dest.mode = "Clip Editor"
        self.observe(dest, "B9")
        self.observe(dest, "B10")
        dest.mode, dest.shot, dest.head = "Motion Editor", "shot10", 0.4167
        self.observe(dest, "B11")
        self.observe(dest, "B12")
        dest.shot, dest.head = "shot15", 0.2083
        self.observe(dest, "B13")
        legacy_base = dest.snapshot()
        dest.write(LEFT, dict((n, value_for(n, 9)) for n in LEFT))
        dest.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Apply Pose NQ1 Pose A", "redo_desc": ""}
        self.observe(dest, "B14")
        legacy_applied = dest.snapshot()
        self.observe(dest, "B15")
        dest.restore(legacy_base)
        self.observe(dest, "B16")
        dest.restore(legacy_applied)
        self.observe(dest, "B17")
        slow = 40000 if "slow" in f else (8000 if "sluggish" in f else 300)
        p7 = [] if "no-p7" in f else ["PROD_POSE_BODY-P7-verified {}"]
        self.op(1, "Apply Pose", ['PROD_POSE_BODY-P1 {"actions": {"insert": 278, "none": 0, "update": 0}, '
                                  '"noop": false}', 'PROD_POSE_BODY-P6 {"owned": true}'] + p7, ms=slow)
        self.op(2, "Apply Pose", ['PROD_POSE_BODY-P1 {"actions": {}, "noop": true}'])
        self.op(3, "Apply Pose", ['PROD_POSE_BODY-P1 {"actions": {"insert": 0, "none": 0, "update": 278}, '
                                  '"noop": false}', 'PROD_POSE_BODY-P6 {"owned": true}',
                                  "PROD_POSE_BODY-P7-verified {}"])
        self.op(4, "Apply Pose", ['PROD_POSE_BODY-P1 {"noop": false}', "PROD_POSE_BODY-P3-P6-failure {}",
                                  "PROD_POSE_BODY-abort-verified {}"])
        self.op(5, "Apply Pose", ["PROD_OPERATION_OUTCOME id=5 outcome='refused'"])
        self.op(6, "Apply Pose", ["PROD_OPERATION_OUTCOME id=6 outcome='refused'"])
        self.op(7, "Apply Pose", ['PROD_POSE_P1 {"noop": false}', 'PROD_POSE_P6 {"owned": true}',
                                  "PROD_POSE_P7-verified {}"])
        self.op(8, "Apply Pose", ['PROD_POSE_P1 {"noop": true}'])
        with open(os.path.join(self.q, "evidence", "logs", "CPM - 2026-11-07_10-00-00Z - pid%d - abcdef - 001.log"
                               % dest.pid), "wb") as fh:
            fh.write(("\r\n".join(self.log) + "\r\n").encode("utf-8"))
        with open(os.path.join(self.q, "sessions", "S3_DESTINATION.dmx"), "wb") as fh:
            fh.write(b"destination")
        self.dump(os.path.join("evidence", "destination.json"),
                  {"destination_sha256": C.s0_hash(os.path.join(self.q, "sessions", "S3_DESTINATION.dmx"))})
        self.dump(os.path.join("evidence", "restore.json"), {"restored": True})
        c = {"paths": {"Q": self.q}, "character_dir": CHAR}
        if self.continuation:
            c["continuation"] = {"process_a_qualification_cpm_sha256": "a" * 64}
            if "no-precheck" not in f:
                self.dump(os.path.join("evidence", "A1_PRECHECK.json"), {
                    "compatible": "precheck-incompatible" not in f, "qualification_cpm_sha256": QUAL,
                    "observation": {"label": "S0-08"}, "revised_A1": "ok"})
        return c


if PY3:
    class CompareTests(unittest.TestCase):
        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="s3cmp")

        def tearDown(self):
            shutil.rmtree(self.dir, True)

        def verdict(self, *faults, **kw):
            c = Synthetic(os.path.join(self.dir, "Q"), faults, kw.get("continuation", False)).build()
            saved = sys.stdout
            sys.stdout = io.StringIO()
            try:
                code = C.run(c)
            finally:
                sys.stdout = saved
            out = load(os.path.join(self.dir, "Q", "evidence", "S3_VERDICT.json"))
            self.assertEqual(code == 0, out["verdict"] == "PASS")
            return out

        def test_a_complete_correct_run_passes(self):
            out = self.verdict()
            self.assertEqual(out["failed"], [])
            self.assertEqual(out["verdict"], "PASS")
            self.assertEqual(out["performance"]["class"], "responsive")
            self.assertGreater(len(out["checks"]), 100)

        def fails(self, fault, *ids):
            out = self.verdict(fault)
            self.assertEqual(out["verdict"], "FAIL", fault)
            for cid in ids:
                self.assertIn(cid, out["failed"], (fault, out["failed"]))
            return out

        def test_update_pose_backup_is_accepted_only_as_the_replaced_record(self):
            out = self.verdict()
            self.assertNotIn("library.update_backups_are_the_replaced_records", out["failed"])
            self.assertNotIn("library.records_unchanged_by_the_apply_process", out["failed"])
            shutil.rmtree(os.path.join(self.dir, "Q"))
            self.fails("bak-wrong", "library.update_backups_are_the_replaced_records")

        def test_a_continuation_passes_with_a_compatible_precheck_and_the_source_build(self):
            out = self.verdict(continuation=True)
            self.assertEqual((out["verdict"], out["failed"]), ("PASS", []))
            self.assertIn("precheck.revised_A1_compatible_before_apply", [x["id"] for x in out["checks"]])

        def test_a_continuation_without_a_compatible_precheck_fails(self):
            for fault in ("no-precheck", "precheck-incompatible"):
                shutil.rmtree(os.path.join(self.dir, "Q"), True)
                out = self.verdict(fault, continuation=True)
                self.assertIn("precheck.revised_A1_compatible_before_apply", out["failed"], fault)

        def test_an_apply_that_moves_nothing_fails(self):
            self.fails("destination-matches", "distinct.destination_differs_from_A_in_every_group")

        def test_a_changed_facial_control_fails(self):
            self.fails("facial-changed", "apply_A.facial_gaze_and_other_controls_unchanged")

        def test_a_posed_bone_off_by_005_degrees_fails(self):
            self.fails("posed-bone-off", "apply_A.full_body_posture_reproduced")

        def test_a_moved_preserved_bone_fails(self):
            self.fails("preserved-moved", "apply_A.full_body_posture_reproduced")

        def test_changed_unrelated_animation_fails(self):
            self.fails("outside-changed", "apply_A.unrelated_animation_unchanged")

        def test_a_noop_that_writes_fails(self):
            self.fails("noop-writes", "repeat.true_noop")

        def test_an_incomplete_undo_fails(self):
            self.fails("undo-incomplete", "undo.restores_the_baseline")

        def test_an_insert_where_an_update_was_expected_fails(self):
            self.fails("update-inserts", "apply_B.existing_keys_updated_in_place")

        def test_an_update_that_kept_the_old_posture_fails(self):
            self.fails("update-not-replaced", "update.B_holds_the_updated_posture")

        def test_no_restart_between_save_and_apply_fails(self):
            self.fails("no-restart", "process.restart_between_save_and_apply")

        def test_an_unverified_apply_fails(self):
            self.fails("no-p7", "log.apply_A_verified_by_cpm")

        def test_an_abort_that_changes_the_document_fails(self):
            self.fails("abort-changes", "abort.verified_nothing_changed")

        def test_a_slow_apply_fails_and_a_sluggish_one_is_a_finding(self):
            out = self.verdict("slow")
            self.assertEqual((out["verdict"], out["performance"]["class"]), ("FAIL", "fail"))
            out = Synthetic(os.path.join(self.dir, "Q2"), ("sluggish",)).build()
            saved = sys.stdout
            sys.stdout = io.StringIO()
            try:
                code = C.run(out)
            finally:
                sys.stdout = saved
            res = load(os.path.join(self.dir, "Q2", "evidence", "S3_VERDICT.json"))
            self.assertEqual((code, res["verdict"], res["performance"]["class"]), (0, "PASS", "finding"))

        def test_the_verdict_is_never_replaced(self):
            c = Synthetic(os.path.join(self.dir, "Q"), ()).build()
            saved = sys.stdout
            sys.stdout = io.StringIO()
            try:
                C.run(c)
                self.assertRaises(OSError, C.run, c)
            finally:
                sys.stdout = saved


if PY3:
    class ContinuationLifecycleTests(unittest.TestCase):
        """build, pre, status, inspect, install, seed, check, library, restore on a temporary installation: the
        source run is only read, the run is isolated, and restore returns every inventory to its baseline."""

        def setUp(self):
            self.dir = tempfile.mkdtemp(prefix="s3life")
            d = lambda *p: os.path.join(self.dir, *p)  # noqa: E731
            for sub in (("game", "usermod", "scripts", "ChadChan3D_CPM"), ("game", "usermod", "scripts",
                                                                          "SFM Character Tools"),
                        ("game", "usermod", "cfg"), ("library", "Characters", CHAR), ("sessions",),
                        ("src", "sessions"), ("src", "observations"), ("src", "evidence", "library_poses", CHAR)):
                os.makedirs(d(*sub))
            self.published = d("game", "usermod", "scripts", "ChadChan3D_CPM", "SFM_Character_Preset_Manager.py")
            with open(self.published, "wb") as f:
                f.write(b"published cpm\n")
            with open(d("game", "usermod", "cfg", "config.cfg"), "wb") as f:
                f.write(b"cfg\n")
            with open(d("library", "Characters", CHAR, "character.json"), "wb") as f:
                f.write(b"{}")
            self.src = {}
            for rel, data in ((("sessions", "S3_DESTINATION.dmx"), b"destination"),
                              (("evidence", "library_poses", CHAR, "S3 Pose A--a.json"), b"A"),
                              (("evidence", "library_poses", CHAR, "S3 Pose B--b.json"), b"B"),
                              (("evidence", "library_poses", CHAR, "S3 Pose B--b.json.bak"), b"B0"),
                              (("observations", "S0-01.json"), b"o1"), (("observations", "S0-01.s3.json"), b"s1"),
                              (("observations", "S0-08.json"), b"run 1 B1, not copied")):
                with open(d("src", *rel), "wb") as f:
                    f.write(data)
                self.src[rel[-1]] = sha_bytes(data)
            with open(os.path.join(ROOT, "s3.template.json"), "rb") as f:
                c = json.loads(f.read().decode("utf-8"))
            cand = os.path.join(REPO, "cpm", "app", "SFM_Character_Preset_Manager.py")
            c["paths"].update(Q=d("Q"), REPO=REPO, GAME=d("game"), LIBRARY=d("library"), SESSIONS=d("sessions"),
                              CANDIDATE=cand, R2_FIXTURE=d("none.dmx"), LEGACY_POSE=d("none.json"),
                              LOG_DIR=d("logs"))
            c["pins"].update(candidate_cpm_sha256=T3.T.sha(cand), published_cpm_sha256=T3.T.sha(self.published))
            c["housekeeping"] = ["cfg\\config.cfg"]
            c["continuation"] = {"source_run": d("src"), "destination_sha256": self.src["S3_DESTINATION.dmx"],
                                 "process_a_qualification_cpm_sha256": "a" * 64,
                                 "records": dict((n, self.src[n]) for n in ("S3 Pose A--a.json", "S3 Pose B--b.json",
                                                                            "S3 Pose B--b.json.bak")),
                                 "observations": dict((n, self.src[n]) for n in ("S0-01.json", "S0-01.s3.json"))}
            self.cfg = d("s3.json")
            with open(self.cfg, "wb") as f:
                f.write(json.dumps(c).encode("utf-8"))
            os.makedirs(d("Q"))
            self.d = d

        def tearDown(self):
            shutil.rmtree(self.dir, True)

        def run_tool(self, *args):
            saved = sys.stdout
            sys.stdout = io.StringIO()
            try:
                return T3.main(["s3_tool", self.cfg] + list(args))
            finally:
                sys.stdout = saved

        def source_state(self):
            return T3.T.inventory(self.d("src"))["sha256"]

        def test_the_continuation_lifecycle_reads_the_source_and_restores_everything(self):
            d = self.d
            src_before = self.source_state()
            self.assertEqual(self.run_tool("build"), 0)
            self.assertEqual(self.run_tool("pre"), 0)
            self.assertEqual(sorted(os.listdir(d("Q", "sessions"))), ["S3_DESTINATION.dmx"])
            self.assertEqual(self.run_tool("status"), 0)
            self.assertEqual(self.run_tool("inspect"), 0)
            self.assertEqual(self.run_tool("install"), 0)
            self.assertEqual(self.run_tool("check"), 0)
            ids = T3.T.read_json(d("Q", "staged", "IDENTITIES.json"))
            self.assertEqual(T3.T.sha(self.published), ids["qualification_cpm_sha256"])
            self.assertEqual(self.run_tool("seed"), 0)
            poses = d("library", "Characters", CHAR, "Poses")
            self.assertEqual(sorted(os.listdir(poses)), ["S3 Pose A--a.json", "S3 Pose B--b.json",
                                                         "S3 Pose B--b.json.bak"])
            self.assertEqual(sorted(os.listdir(d("Q", "observations"))), ["S0-01.json", "S0-01.s3.json"])
            lib_a = T3.T.read_json(d("Q", "evidence", "library_A.json"))
            self.assertEqual(len(lib_a["files"]), 3)
            self.assertEqual(self.run_tool("library", "B"), 0)
            self.assertEqual(self.run_tool("restore"), 0)
            restore = T3.T.read_json(d("Q", "evidence", "restore.json"))
            self.assertTrue(restore["restored"], restore)
            self.assertEqual(T3.T.sha(self.published), T3.T.read_json(self.cfg)["pins"]["published_cpm_sha256"])
            self.assertFalse(os.path.exists(poses))
            self.assertEqual(sorted(os.listdir(d("Q", "evidence", "library_poses", CHAR))),
                             ["S3 Pose A--a.json", "S3 Pose B--b.json", "S3 Pose B--b.json.bak"])
            self.assertEqual(self.source_state(), src_before)

        def test_a_changed_source_file_refuses_pre(self):
            with open(self.d("src", "evidence", "library_poses", CHAR, "S3 Pose B--b.json.bak"), "ab") as f:
                f.write(b"x")
            self.assertEqual(self.run_tool("build"), 0)
            self.assertRaises(SystemExit, self.run_tool, "pre")
            self.assertFalse(os.path.exists(self.d("Q", "pre_run")))

        def test_the_source_run_folder_cannot_be_the_run_folder(self):
            c = T3.T.read_json(self.cfg)
            c["continuation"]["source_run"] = c["paths"]["Q"]
            with open(self.cfg, "wb") as f:
                f.write(json.dumps(c).encode("utf-8"))
            self.run_tool("build")
            self.assertRaises(SystemExit, self.run_tool, "pre")


if __name__ == "__main__":
    unittest.main(verbosity=1)
