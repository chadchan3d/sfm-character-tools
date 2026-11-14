# -*- coding: ascii -*-
"""Offline tests of the F-01 K2 Krystal version 2 Full body native integration kit (Python 3).

- k2_tool: build derives exactly the pinned K1 qualification CPM (37b0cce6...) from the real candidate (3984e1e1...)
  in one line and refuses a wrong pin; pre refuses a missing or changed S3 destination; the template refuses until
  filled; the reused S3 tool carries this kit's identity and the S3 observer and UI smoke check unchanged.
- k2_compare: a complete synthetic run (the S3 tests' synthetic Krystal scene) is PASS; each counterexample is FAIL on
  its own check; the K1 fallback log line is a finding, not a failure.
They show nothing about SFM.

Run: python -I test_k2.py
"""
import copy
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RSQ = os.path.dirname(ROOT)
REPO = os.path.dirname(RSQ)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(RSQ, "f01_full_body_s3", "tests"))
import k2_tool as TOOL  # noqa: E402
import k2_compare as K  # noqa: E402
import test_s3 as S3T  # noqa: E402  (its synthetic Krystal scene, regions and records)

QUAL = "37b0cce608062f2a7e03bab03ee4e590fc3f8c395a2c300538df44e3893b1868"


def load(path):
    with io.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def quiet(fn):
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return fn()
    finally:
        sys.stdout = saved


def config(folder, **paths):
    with open(os.path.join(ROOT, "k2.template.json"), "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    for d in ("game", "sessions", "library", "s3run/sessions", "logs"):
        os.makedirs(os.path.join(folder, *d.split("/")), exist_ok=True)
    fixture = os.path.join(folder, "fixture.dmx")
    if not os.path.exists(fixture):
        with open(fixture, "wb") as f:
            f.write(b"fixture")
    c["paths"].update(Q=os.path.join(folder, "Q"), REPO=REPO, GAME=os.path.join(folder, "game"),
                      SESSIONS=os.path.join(folder, "sessions"), LIBRARY=os.path.join(folder, "library"),
                      R2_FIXTURE=fixture, S3_RUN1=os.path.join(folder, "s3run"), LOG_DIR=os.path.join(folder, "logs"),
                      LEGACY_POSE=fixture)
    c["paths"].update(paths)
    path = os.path.join(folder, "k2.json")
    with open(path, "wb") as f:
        f.write(json.dumps(c).encode("utf-8"))
    return path


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="k2tool")
        os.makedirs(os.path.join(self.dir, "Q"))

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_build_derives_the_pinned_k1_qualification_build_in_one_line(self):
        c = TOOL.S.load(config(self.dir))
        quiet(lambda: TOOL.cmd_build(c))
        ids = load(os.path.join(self.dir, "Q", "staged", "IDENTITIES.json"))
        self.assertEqual(ids["qualification_cpm_sha256"], QUAL)
        self.assertEqual(ids["candidate_cpm_sha256"], "3984e1e1d5d2018202fa551700564da6796cc1063c2be7a32112ad023db5ae9c")
        self.assertEqual((ids["changed_line"], ids["line"]), (42182, u'PROD_POSE_REGISTRY_MODE = u"qualification"'))
        self.assertEqual(ids["wrapper_sha256"], TOOL.T.sha(os.path.join(RSQ, "f01_full_body_s3", "observer",
                                                                          "F01_S3_Observe.py")))
        self.assertEqual(ids["ui_smoke_sha256"], TOOL.T.sha(os.path.join(RSQ, "f01_full_body_s3", "observer",
                                                                           "F01_S3_UISmoke.py")))

    def test_build_refuses_a_wrong_qualification_pin(self):
        path = config(self.dir)
        c = load(path)
        c["pins"]["qualification_cpm_sha256"] = "0" * 64
        with open(path, "wb") as f:
            f.write(json.dumps(c).encode("utf-8"))
        self.assertRaises(SystemExit, quiet, lambda: TOOL.cmd_build(TOOL.S.load(path)))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "Q", "staged")))

    def test_pre_refuses_without_the_pinned_s3_destination(self):
        c = TOOL.S.load(config(self.dir))
        self.assertRaises(SystemExit, quiet, lambda: TOOL.cmd_pre(c))
        with open(os.path.join(self.dir, "s3run", "sessions", "S3_DESTINATION.dmx"), "wb") as f:
            f.write(b"not the prepared destination")
        self.assertRaises(SystemExit, quiet, lambda: TOOL.cmd_pre(c))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "Q", "pre_run")))

    def test_the_template_refuses_until_filled_and_the_kit_identity(self):
        self.assertRaises(SystemExit, TOOL.S.load, os.path.join(ROOT, "k2.template.json"))
        self.assertEqual((TOOL.S.FORMAT, TOOL.S.SESSIONS, TOOL.S.DESTINATION),
                         ("F01-K2-config-v1", ("K2_SOURCE.dmx",), "K2_DESTINATION.dmx"))


# --- the comparator on a synthetic run -------------------------------------------------------------------------------

FK = ["w%03d_p" % i for i in range(124)]              # the record's fk-written positions (pinned under revised A1)
HANDLE_P = ["w%03d_p" % i for i in range(124, 139)]
# The two native K2 discrepancies (B1 destination vs A2 record, float32-exact values from run 1's observations).
NATIVE = {"w001_p": ([4.631233215332031, -0.2219141721725464, -3.2890470027923584],
                     [4.631217956542969, -0.221917986869812, -3.289045810699463]),
          "w002_p": ([0.0, 3.0237770080566406, 0.0],
                     [8.285045623779297e-06, 3.0237720012664795, -2.390146255493164e-05])}


def descriptor():
    roles = dict((n, {"role": "fk-written", "attribute": "position"}) for n in FK)
    roles.update((n, {"role": "handle-written", "attribute": "position"}) for n in HANDLE_P)
    roles.update((n, {"role": "fk-written", "attribute": "orientation"}) for n in S3T.WRITTEN if n.endswith("_o"))
    return {"channels": roles}


class K2Synthetic(object):
    def __init__(self, folder, faults=()):
        self.q, self.f = folder, set(faults)
        for d in ("staged", "observations", "evidence", "sessions", os.path.join("evidence", "logs"),
                  os.path.join("evidence", "library_poses", S3T.CHAR)):
            os.makedirs(os.path.join(folder, d))
        shutil.copyfile(os.path.join(REPO, "cpm", "pose_profiles", "cpm_body_profiles_v1.json"),
                        os.path.join(folder, "staged", "cpm_body_profiles_v1.json"))
        self.dump(os.path.join("staged", "IDENTITIES.json"), {"qualification_cpm_sha256": QUAL})

    def dump(self, rel, data):
        with open(os.path.join(self.q, rel), "wb") as f:
            f.write(json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))

    def observe(self, scene, step):
        obs, side = scene.observe(K.LABELS[step], step)
        if step == "B2" and "facial-changed" in self.f:
            for ctl in obs["controls"]:
                if ctl["id"]["name"] == "Smile":
                    ctl["attributes"]["value"]["value"] = 0.9
        self.dump(os.path.join("observations", K.LABELS[step] + ".json"), obs)
        self.dump(os.path.join("observations", K.LABELS[step] + ".s3.json"), side)

    def log(self, pid, ops):
        lines, n = [], 0
        for i, (kind, outcome, texts) in enumerate(ops, 1):
            for text in (["PROD_OPERATION_BEGIN id=%d kind=u'%s' context=None" % (i, kind)] + texts +
                         ["PROD_OPERATION_RESULT id=%d kind=u'%s' outcome=u'%s'" % (i, kind, outcome),
                          "PROD_OPERATION_END id=%d" % i]):
                n += 1
                lines.append("2026-11-14T10:%02d:%02d.000Z #%06d s=x w=1 op=%d | %s" % (n // 60, n % 60, n, i, text))
        with open(os.path.join(self.q, "evidence", "logs", "CPM - 2026-11-14_10-00-00Z - pid%d - x - 001.log" % pid),
                  "wb") as fh:
            fh.write(("\n".join(lines) + "\n").encode("utf-8"))

    def build(self):
        f = self.f
        src =S3T.Scene(100, "e:/q/sessions/K2_SOURCE.dmx", 0.0, S3T.posture(1.0))
        src.shot, src.head, src.cpm = "shot15", 0.2083, QUAL
        self.observe(src, "A1")
        self.observe(src, "A2")
        reg_saved = S3T.region_from(src, 1)
        reg_saved["profile_id"] = "body_krystal_v1"
        if "no-descriptor" not in f:
            reg_saved["descriptor"] = descriptor()
        dest = S3T.Scene(100 if "no-restart" in f else 200, "e:/q/sessions/K2_DESTINATION.dmx", 35.0,
                         S3T.posture(1.0) if "destination-matches" in f else S3T.posture(-30.0))
        dest.cpm = QUAL
        # Revised A1: the saved FK positions equal the destination's, except the two native float32-noise channels.
        for n in FK:
            reg_saved["positions"][n] = copy.deepcopy(dest.keys[n][0][1])
        for n, (saved, there) in NATIVE.items():
            reg_saved["positions"][n], dest.keys[n][0][1] = list(saved), list(there)
        if "outside-limit" in f:                       # 0.0001 units: beyond body_krystal_v1's 0.00005
            reg_saved["positions"]["w003_p"] = [K.f32(dest.keys["w003_p"][0][1][0] + 0.0001)] + \
                dest.keys["w003_p"][0][1][1:]
        self.observe(dest, "B1")
        base = dest.snapshot()
        if "apply-moves-nothing" not in f:
            planned = copy.deepcopy(reg_saved)          # what CPM's revised A1 plan writes
            for n in FK:
                planned["positions"][n] = copy.deepcopy(dest.keys[n][0][1])
            if "pinned-saved-transferred" in f:
                planned["positions"]["w001_p"] = list(NATIVE["w001_p"][0])
            if "wrong-authored-value" in f:
                planned["orientations"]["w130_o"] = S3T.qz(77.0)
            if "wrong-handle-position" in f:
                planned["positions"]["w130_p"] = [9.0, 0.5, -0.25]
            dest.apply(planned, "K2 Pose")
            if "unexpected-write" in f:
                dest.keys["jaw_o"].append([S3T.T_CHAN, S3T.qz(5.0)])
            if "extra-key" in f:
                dest.keys["w005_p"].append([S3T.T_CHAN + 1, [0.0, 0.5, -0.25]])
        else:
            dest.undo = {"can_undo": True, "can_redo": False, "undo_desc": "Apply Pose K2 Pose", "redo_desc": ""}
        self.observe(dest, "B2")
        applied = dest.snapshot()
        dest.restore(base)
        dest.undo = dict(base[2], can_redo=True, redo_desc="Redo Apply Pose K2 Pose")
        if "undo-incomplete" in f:
            dest.keys["w001_p"].append([S3T.T_CHAN, S3T.value_for("w001_p", 1)])
        self.observe(dest, "B3")
        dest.restore(applied)
        self.observe(dest, "B4")
        dest.angles = S3T.posture(-55.0)              # the Owner's Hip rotation (B5), then Update Pose (B6)
        dest.keys["w004_o"][0][1] = S3T.qz(15.0)
        self.observe(dest, "B5")
        if "update-writes" in f:
            dest.keys["w005_o"][0][1] = S3T.qz(3.0)
        self.observe(dest, "B6")
        reg_now = reg_saved if "update-kept-old" in f else S3T.region_from(dest, 3)
        lib = os.path.join(self.q, "evidence", "library_poses", S3T.CHAR)
        saved = S3T.record("K2 Pose", reg_saved, "t1", "t1")
        now = S3T.record("K2 Pose", reg_now, "t1", "t1" if "update-not-in-place" in f else "t2")
        for name, r in (("K2 Pose--k2k2.json", now), ("K2 Pose--k2k2.json.bak", saved)):
            with open(os.path.join(lib, name), "wb") as fh:
                fh.write(json.dumps(r).encode("utf-8"))
        self.dump(os.path.join("evidence", "library_A.json"),
                  {"files": {"K2 Pose--k2k2.json": K.S3.s0_hash(os.path.join(lib, "K2 Pose--k2k2.json.bak"))}})
        self.dump(os.path.join("observations", "UI-SMOKE.json"), {
            "format": "F01-S3-ui-smoke-v1", "pid": dest.pid, "cpm_build_sha256": QUAL,
            "selected": {"name": "K2 Pose", "preset_id": "x", "version": 2, "regions": ["full_body"]},
            "apply_button_enabled": "ui-disabled" not in f,
            "state": {"apply_pose": True, "apply_mode": "direct", "summary": []}, "recovery_paused": False})
        self.dump(os.path.join("evidence", "K2_PRECHECK.json"),
                  {"compatible": "incompatible" not in f, "distinct": True,
                   "apply_allowed": "incompatible" not in f})
        p7 = [] if "no-p7" in f else ["PROD_POSE_BODY-P7-verified {}"]
        extra = ["PROD_POSE_K1-generic-inventory-unavailable {}"] if "k1-fallback" in f else []
        self.log(src.pid, [("Save Pose", "verified", extra)])
        b_ops = [("Pose Info", "completed", []),
                 ("Apply Pose", "verified", ['PROD_POSE_BODY-P1 {"actions": {"insert": 278}, "noop": false}',
                                            'PROD_POSE_BODY-P6 {"owned": true}'] + p7),
                 ("Update Pose", "verified", [])]
        if "recovery" in f:
            b_ops.append(("Apply Pose", "recovery-unverified", ["PROD_POSE_BODY-abort-failed {}"]))
        if dest.pid != src.pid:
            self.log(dest.pid, b_ops)
        for name, data in (("K2_SOURCE.dmx", b"fixture"), ("K2_DESTINATION.dmx", b"destination")):
            with open(os.path.join(self.q, "sessions", name), "wb") as fh:
                fh.write(data)
        self.dump(os.path.join("evidence", "destination.json"),
                  {"destination_sha256": K.S3.s0_hash(os.path.join(self.q, "sessions", "K2_DESTINATION.dmx"))})
        self.dump(os.path.join("evidence", "restore.json"), {"restored": True})
        return {"paths": {"Q": self.q}, "character_dir": S3T.CHAR,
                "pins": {"qualification_cpm_sha256": QUAL,
                         "r2_fixture_sha256": K.S3.s0_hash(os.path.join(self.q, "sessions", "K2_SOURCE.dmx"))}}


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="k2cmp")

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def verdict(self, *faults):
        q = os.path.join(self.dir, "Q%d" % len(os.listdir(self.dir)))
        c = K2Synthetic(q, faults).build()
        code = quiet(lambda: K.run(c))
        out = load(os.path.join(q, "evidence", "K2_VERDICT.json"))
        self.assertEqual(code == 0, out["verdict"] == "PASS")
        return out

    def test_a_complete_correct_run_passes(self):
        out = self.verdict()
        self.assertEqual((out["verdict"], out["failed"], out["findings"]), ("PASS", [], []))

    def test_the_k1_fallback_is_a_finding_not_a_failure(self):
        out = self.verdict("k1-fallback")
        self.assertEqual(out["verdict"], "PASS")
        self.assertTrue(out["findings"])

    def test_the_native_two_channel_revised_a1_case_passes(self):
        out = self.verdict()
        written = [x for x in out["checks"] if x["id"] == "apply.pinned_fk_positions_within_the_revised_A1_limit"][0]
        self.assertEqual((written["pass"], written["detail"]["pinned"], sorted(written["detail"]["differing_from_saved"])),
                         (True, 124, ["w001_p", "w002_p"]))
        self.assertNotIn("apply.written_channels_hold_the_record", [x["id"] for x in out["checks"]])

    def test_revised_a1_counterexamples_fail(self):
        cases = {"pinned-saved-transferred": "apply.written_channels_hold_the_planned_values",
                 "wrong-authored-value": "apply.written_channels_hold_the_planned_values",
                 "wrong-handle-position": "apply.written_channels_hold_the_planned_values",
                 "extra-key": "apply.written_channels_hold_the_planned_values",
                 "unexpected-write": "apply.other_channels_of_the_instance_unchanged",
                 "outside-limit": "apply.pinned_fk_positions_within_the_revised_A1_limit",
                 "no-descriptor": "apply.pinned_fk_positions_within_the_revised_A1_limit"}
        for fault, check in sorted(cases.items()):
            out = self.verdict(fault)
            self.assertEqual(out["verdict"], "FAIL", fault)
            self.assertIn(check, out["failed"], (fault, out["failed"]))

    def test_the_limit_is_inclusive_as_float32_and_the_next_float32_refuses(self):
        class FakeRun(object):
            @staticmethod
            def channels(o):
                return dict((n, {"value_at_mapped": v}) for n, v in o.items())
        limit = K.f32(0.00005)
        above = struct.unpack("<f", struct.pack("<I", struct.unpack("<I", struct.pack("<f", limit))[0] + 1))[0]
        region = {"profile_id": "body_krystal_v1", "positions": {"p": [0.0, 0.0, 0.0]},
                  "descriptor": {"channels": {"p": {"role": "fk-written", "attribute": "position"}}}}
        self.assertEqual(K.planned_region(FakeRun, region, {"p": [limit, 0.0, 0.0]})[2], [])
        self.assertEqual(len(K.planned_region(FakeRun, region, {"p": [above, 0.0, 0.0]})[2]), 1)
        other = dict(region, profile_id="body_other_v1")      # every other profile stays exact
        self.assertEqual(len(K.planned_region(FakeRun, other, {"p": [K.f32(1e-7), 0.0, 0.0]})[2]), 1)
        self.assertEqual(len(K.planned_region(FakeRun, region, {"p": [float("nan"), 0.0, 0.0]})[2]), 1)
        self.assertEqual(len(K.planned_region(FakeRun, region, {"p": [0.1, 0.0, 0.0]})[2]), 1)  # 0.1 isn't float32

    def test_replay_writes_separate_files_and_leaves_the_original_unchanged(self):
        q = os.path.join(self.dir, "R")
        c = K2Synthetic(q, ("pinned-saved-transferred",)).build()
        self.assertEqual(quiet(lambda: K.run(c, replay=True)), 2)      # refused: no original verdict yet
        quiet(lambda: K.run(c))
        ev = os.path.join(q, "evidence")
        before = dict((n, K.sha256_file(os.path.join(ev, n))) for n in ("K2_VERDICT.json", "K2_VERDICT.md"))
        quiet(lambda: K.run(c, replay=True))
        out = load(os.path.join(ev, "K2_VERDICT_REVISED_A1.json"))
        self.assertEqual(out["replay"]["original"]["files"], before)
        self.assertEqual(dict((n, K.sha256_file(os.path.join(ev, n))) for n in before), before)
        self.assertRaises(OSError, quiet, lambda: K.run(c, replay=True))  # never overwritten

    def test_counterexamples_fail_on_their_own_check(self):
        cases = {"apply-moves-nothing": "apply.written_channels_hold_the_planned_values",
                 "destination-matches": "distinct.destination_visibly_different",
                 "incompatible": "precheck.compatible_and_distinct_before_apply",
                 "ui-disabled": "reopen.apply_enabled_for_the_v2_record",
                 "facial-changed": "apply.facial_gaze_and_other_controls_unchanged",
                 "undo-incomplete": "undo.restores_the_destination",
                 "update-writes": "update.writes_nothing_to_the_scene",
                 "update-kept-old": "update.record_changed_from_the_saved_posture",
                 "update-not-in-place": "update.in_place",
                 "no-restart": "process.restart_between_save_and_apply",
                 "no-p7": "log.one_apply_owned_and_verified_by_cpm",
                 "recovery": "log.no_recovery_or_uncertainty"}
        for fault, check in sorted(cases.items()):
            out = self.verdict(fault)
            self.assertEqual(out["verdict"], "FAIL", fault)
            self.assertIn(check, out["failed"], (fault, out["failed"]))


if __name__ == "__main__":
    unittest.main()
