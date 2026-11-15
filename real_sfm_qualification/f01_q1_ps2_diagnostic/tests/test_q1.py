# -*- coding: ascii -*-
"""Offline tests of the F-01 Q1 PS-2 diagnostic kit (Python 3).

- q1_tool: build derives exactly the pinned qualification CPM (849d0ed4...) from the candidate at fda1fb3 and refuses
  a changed observer; pre refuses when a pinned PS-2 preset differs; seed copies only the pinned PS2 Dup Body, verifies
  Body and Happy unchanged, and refuses twice; the template refuses until filled.
- q1_analyze: a complete synthetic diagnostic is EVIDENCE COMPLETE with the expected readings; each kind of missing,
  wrong or inconsistent evidence (missing capture, wrong identity, missing fields, hooks not removed, an inconsistent
  deferred map, an unreadable boundary map, a required Happy step missing, an intervening visibility edit, a wrong
  history, an unexpected library change, failed restoration, a saved session) is EVIDENCE INCOMPLETE on its own check;
  the field-level duplicate comparison finds a target difference and an unchanged peer.
They show nothing about SFM.

Run: python -I test_q1.py
"""
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
RSQ = os.path.dirname(ROOT)
REPO = os.path.dirname(RSQ)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import q1_tool as TOOL  # noqa: E402
import q1_analyze as A  # noqa: E402

QUAL = "849d0ed44101965de62165f01fcbb22b3caae9797e867169e71d4247b49cd4a2"
CAND = "615acf0c23ffcf5c278785bb47de6aaf6a7b9ae26779b9313979ac928240c432"
CHAR = "krystal2020--7d2aee52ef3a"
_CANDIDATE = []


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def candidate():
    if not _CANDIDATE:
        import atexit
        import subprocess
        raw = subprocess.check_output(["git", "-C", REPO, "cat-file", "blob",
                                       "fda1fb3:cpm/app/SFM_Character_Preset_Manager.py"])
        where = tempfile.mkdtemp(prefix="q1cand")
        atexit.register(shutil.rmtree, where, True)
        path = os.path.join(where, "SFM_Character_Preset_Manager.py")
        with open(path, "wb") as f:
            f.write(raw)
        _CANDIDATE.append(path)
    return _CANDIDATE[0]


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


def write(path, data):
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "wb") as f:
        f.write(data)


def config(folder, pins=None, presets=True):
    with open(os.path.join(ROOT, "q1.template.json"), "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    lib = os.path.join(folder, "library")
    char = os.path.join(lib, "Characters", CHAR)
    body, happy, dup = b"the Body preset", b"the Happy preset", b"PS2 Dup Body"
    if presets:
        write(os.path.join(char, "Body Presets", "Body--preset-d1c94.json"), body)
        write(os.path.join(char, "Expressions", "Happy--preset-d0886.json"), happy)
    write(os.path.join(folder, "ps2", "PS2 Dup Body--preset-49480.json"), dup)
    for d in ("game", "sessions", "logs", "Q"):
        os.makedirs(os.path.join(folder, d), exist_ok=True)
    c["paths"].update(Q=os.path.join(folder, "Q"), REPO=REPO, GAME=os.path.join(folder, "game"),
                      SESSIONS=os.path.join(folder, "sessions"), LIBRARY=lib,
                      R2_FIXTURE=os.path.join(folder, "fixture.dmx"), S3_RUN1=os.path.join(folder, "s3run"),
                      LOG_DIR=os.path.join(folder, "logs"), CANDIDATE=candidate(),
                      DUP_PRESET=os.path.join(folder, "ps2", "PS2 Dup Body--preset-49480.json"))
    c["pins"].update(q1_observer_sha256=TOOL.T.sha(os.path.join(ROOT, "observer", "F01_Q1_Observe.py")),
                     body_preset_sha256=sha_bytes(body), happy_preset_sha256=sha_bytes(happy),
                     dup_preset_sha256=sha_bytes(dup))
    c["pins"].update(pins or {})
    path = os.path.join(folder, "q1.json")
    with open(path, "wb") as f:
        f.write(json.dumps(c).encode("utf-8"))
    return path


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="q1tool")

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_build_derives_the_pinned_qualification_build(self):
        c = TOOL.S.load(config(self.dir))
        quiet(lambda: TOOL.cmd_build(c))
        ids = load(os.path.join(self.dir, "Q", "staged", "IDENTITIES.json"))
        self.assertEqual((ids["candidate_cpm_sha256"], ids["qualification_cpm_sha256"]), (CAND, QUAL))

    def test_build_refuses_a_changed_observer(self):
        c = TOOL.S.load(config(self.dir, {"q1_observer_sha256": "0" * 64}))
        self.assertRaises(SystemExit, quiet, lambda: TOOL.cmd_build(c))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "Q", "staged")))

    def test_pre_refuses_when_a_pinned_preset_differs_and_changes_nothing(self):
        c = TOOL.S.load(config(self.dir, {"body_preset_sha256": "0" * 64}))
        self.assertRaises(SystemExit, quiet, lambda: TOOL.cmd_pre(c))
        self.assertFalse(os.path.exists(os.path.join(self.dir, "Q", "pre_run")))

    def test_seed_copies_only_the_pinned_dup_preset_and_refuses_twice(self):
        c = TOOL.S.load(config(self.dir))
        saved = (TOOL.S.state, TOOL.T.sfm_running)
        TOOL.S.state = lambda c_: ("qualification", QUAL)        # the installation and process checks, simulated
        TOOL.T.sfm_running = lambda: None
        try:
            os.makedirs(os.path.join(self.dir, "Q", "evidence"))
            quiet(lambda: TOOL.cmd_seed(c))
            target = os.path.join(self.dir, "library", "Characters", CHAR, "Body Presets",
                                  "PS2 Dup Body--preset-49480.json")
            self.assertTrue(os.path.isfile(target))
            seed = load(os.path.join(self.dir, "Q", "evidence", "seed.json"))
            self.assertEqual(list(seed["seeded"]), ["PS2 Dup Body--preset-49480.json"])
            self.assertRaises(SystemExit, quiet, lambda: TOOL.cmd_seed(c))
        finally:
            TOOL.S.state, TOOL.T.sfm_running = saved

    def test_the_template_refuses_until_filled_and_the_kit_identity(self):
        self.assertRaises(SystemExit, TOOL.S.load, os.path.join(ROOT, "q1.template.json"))
        self.assertEqual((TOOL.S.FORMAT, TOOL.S.SESSIONS, TOOL.S.DESTINATION),
                         ("F01-Q1-config-v1", ("Q1_KRYSTAL.dmx",), "Q1_SPARE.dmx"))


# --- the analysis on a synthetic diagnostic --------------------------------------------------------------------------

def full_map(record, failing=()):
    bones = []
    for name, desired in ((u"bip_head", 1.33 if record == u"Body" else 1.0), (u"bip_tail00", 1.0),
                          (u"bip_pelvis", 1.0)):
        if name in failing:
            bones.append({"bone": name, "bone_index": 1, "desired": desired, "ok": False, "predicate": u"physical",
                          "physical": 1.13, "delta": 1.13 - desired, "static": [u"pass", None, None],
                          "classification": u"CHANNEL_DRIVEN_SCALE", "trace": {"physical_matches_lerp": False}})
        else:
            bones.append({"bone": name, "bone_index": 1, "desired": desired, "ok": True, "predicate": u"physical",
                          "physical": desired, "delta": 0.0, "static": [u"pass", None, None],
                          "classification": u"CHANNEL_DRIVEN_SCALE", "trace": {"physical_matches_lerp": True}})
    fail = [b for b in bones if not b["ok"]]
    return {"record": record, "validate_error": None, "bones": bones, "result": not fail,
            "first_failure": {"bone": fail[0]["bone"], "predicate": u"physical"} if fail else None,
            "would_raise": False}


def raw_set(name, handle, head_scale=1.0, visible=True, smile=0.0):
    return {"name": name, "handle": handle, "controls": {u"Smile": {u"value": smile}},
            "model": {"model": u"models/krystal2020.mdl", "handle": handle + 1, "visible": visible, "skin": 0,
                      "body": 0, "children": [],
                      "bones": [[u"bip_head", [0.0, 1.0, 2.0], [0.0, 0.0, 0.0, 1.0], head_scale],
                                [u"bip_pelvis", [0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], 1.0]],
                      "flexes": [[u"smile", smile]]}}


class Q1Synthetic(object):
    def __init__(self, folder, faults=()):
        self.q, self.f = folder, set(faults)
        for d in ("staged", "observations", "evidence", "sessions", os.path.join("evidence", "logs")):
            os.makedirs(os.path.join(folder, d))

    def dump(self, rel, data):
        write(os.path.join(self.q, rel), json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))

    def capture(self, step, sets, events=(), settled=None, undo=(u"", u""), extra=None):
        f = self.f
        data = {"format": "F01-Q1-capture-v1", "step": step, "pid": 400, "time": 0.0,
                "cpm_build_sha256": "0" * 64 if ("wrong-build" in f and step == "BODY") else QUAL, "errors": {},
                "session": {"document": u"e:\\q1\\sessions\\q1_krystal.dmx", "shot": u"shot15",
                            "head_seconds": 0.2083, "timeline_mode": u"Motion Editor",
                            "undo": {"can_undo": True, "can_redo": bool(undo[1]), "undo_desc": undo[0],
                                     "redo_desc": undo[1]}},
                "character": {u"model": u"models/krystal2020.mdl"},
                "instance": {"kind": "token", "animset_key": ["DmeAnimationSet", 100, "id-100"]},
                "animation_sets": sets, "records": {}, "settled_full_map": settled or {}, "events": list(events)}
        if "missing-fields" in f and step == "DUP-APPLY":
            data["animation_sets"][0]["model"] = None
        data.update(extra or {})
        if not ("missing-capture" in f and step == "DUP-UNDO"):
            self.dump(os.path.join("observations", "Q1-%s.json" % step), data)

    def build(self):
        f = self.f
        self.dump(os.path.join("staged", "IDENTITIES.json"), {"qualification_cpm_sha256": QUAL,
                                                              "candidate_cpm_sha256": CAND})
        settled_fails = "persistent" in f
        a0 = raw_set(u"Krystal", 100, 1.13)
        self.capture("BASE", [a0], settled={u"Body": full_map(u"Body", (u"bip_head",))},
                     extra={"hooks_installed": sorted(A.HOOKS)})
        deferred_fail = "not-reproduced" not in f
        body_events = [
            {"kind": "apply-begin", "preset": u"Body", "preset_kind": u"body", "seq": 1},
            {"kind": "precommit-authored", "bone": u"bip_head", "result": True, "desired_native": 1.33, "seq": 2},
            {"kind": "precommit-authored", "bone": u"bip_tail00", "result": True, "desired_native": 1.0, "seq": 3},
            {"kind": "refresh-before", "operation": u"Body", "seq": 4,
             "full_map": {"error": "boom"} if "refresh-map-error" in f else full_map(u"Body", (u"bip_head",))},
            {"kind": "refresh-after", "seq": 5, "full_map": full_map(u"Body", (u"bip_head",))},
            {"kind": "apply-returned", "seq": 6},
            {"kind": "deferred-verify", "record": u"Body", "seq": 7, "result": not deferred_fail,
             "consistent": "inconsistent" not in f,
             "full_map": full_map(u"Body", (u"bip_head",) if deferred_fail else ())}]
        a1 = raw_set(u"Krystal", 100, 1.33 if not settled_fails else 1.13)
        self.capture("BODY", [a1], events=body_events,
                     settled={u"Body": full_map(u"Body", (u"bip_head",) if settled_fails else ())})
        if settled_fails and "no-happy" not in f:
            self.capture("HAPPY", [a1], events=[
                {"kind": "apply-begin", "preset": u"Happy", "preset_kind": u"expression", "seq": 8},
                {"kind": "refresh-before", "operation": u"Happy", "seq": 9,
                 "full_map": full_map(u"Body", (u"bip_head",))},
                {"kind": "refresh-after", "seq": 10, "full_map": full_map(u"Body")}],
                settled={u"Body": full_map(u"Body")})
        b0 = raw_set(u"krystal20201", 200, 1.0)
        a_base = raw_set(u"Krystal", 100, 1.33)
        self.capture("DUP-BEFORE", [a_base, b0])
        a_dup = raw_set(u"Krystal", 100, 1.0, visible="visibility" not in f)
        self.capture("DUP-APPLY", [a_dup, b0], events=[
            {"kind": "apply-begin", "preset": u"PS2 Dup Body", "preset_kind": u"body", "seq": 11},
            {"kind": "deferred-verify", "record": u"PS2 Dup Body", "seq": 12, "result": False, "consistent": True,
             "full_map": full_map(u"PS2 Dup Body", (u"bip_head",))}],
            undo=(u"Apply Body Preset" if "wrong-history" not in f else u"Toggle Visibility", u""))
        a_undo = raw_set(u"Krystal", 100, 1.33, smile=0.25)     # restored scale, a flex weight left different
        self.capture("DUP-UNDO", [a_undo, b0], undo=(u"Something", u"Redo Apply Body Preset"),
                     extra={"hooks_removed": "hooks-left" not in f})
        lines, n = [], 0
        log = [("Body", "PROD_APPLY outcome='verification-pending' model=u'm' kind=u'body' preset=u'Body' "
                        "changed_sides=5 changed_existing_scales=2 created_missing_scales=0 play_scales=2 head_time=0.2"),
               ("Body", "PROD_APPLY_DEFERRED_VERIFY outcome=u'%s' reason=%s model=u'm' kind=u'body' preset=u'Body' "
                        "play_scales=2" % (("committed-unverified", "u'bone-scales'") if deferred_fail else
                                           ("committed-verified", "None"))),
               ("Dup", "PROD_APPLY_DEFERRED_VERIFY outcome=u'committed-unverified' reason=u'bone-scales' model=u'm' "
                       "kind=u'body' preset=u'PS2 Dup Body' play_scales=1")]
        for _, text in log:
            n += 1
            lines.append("2026-11-15T10:00:%02d.000Z #%06d s=x w=1 op=1 | %s" % (n, n, text))
        write(os.path.join(self.q, "evidence", "logs", "CPM - 2026-11-15_10-00-00Z - pid400 - x - 001.log"),
              ("\n".join(lines) + "\n").encode("utf-8"))
        base = "Characters/%s/" % CHAR
        diffs = [{"status": "added", "path": base + "Body Presets/PS2 Dup Body--preset-49480.json", "sha256": "d"},
                 {"status": "changed", "path": base + "character.json", "sha256": "c"}]
        if "library-extra" in f:
            diffs.append({"status": "added", "path": "Trash/x.json", "sha256": "t"})
        self.dump(os.path.join("evidence", "library_cleanup.json"), {
            "differences_kept_in_evidence": diffs, "files_equal_pre": True, "folders_equal_pre": True})
        self.dump(os.path.join("evidence", "seed.json"), {"seeded": {"PS2 Dup Body--preset-49480.json": "d"}})
        self.dump(os.path.join("evidence", "restore.json"), {"restored": "not-restored" not in f,
                                                              "inventory_problems": []})
        write(os.path.join(self.q, "sessions", "Q1_KRYSTAL.dmx"), b"src" if "session-saved" not in f else b"x")
        return {"paths": {"Q": self.q}, "character_dir": CHAR,
                "pins": {"qualification_cpm_sha256": QUAL, "candidate_cpm_sha256": CAND,
                         "r2_fixture_sha256": sha_bytes(b"src")}}


class AnalyzeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="q1an")

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def report(self, *faults):
        q = os.path.join(self.dir, "Q%d" % len(os.listdir(self.dir)))
        c = Q1Synthetic(q, faults).build()
        code = quiet(lambda: A.run(c))
        out = load(os.path.join(q, "evidence", "Q1_REPORT.json"))
        self.assertEqual(code == 0, out["verdict"] == "EVIDENCE COMPLETE")
        return out

    def test_complete_evidence_with_the_delayed_evaluation_reading(self):
        out = self.report()
        self.assertEqual((out["verdict"], out["failed"]), ("EVIDENCE COMPLETE", []), out["failed"])
        body = out["analysis"]["body"]
        self.assertIn("settled map passes", body["reading"])
        self.assertEqual([f["bone"] for f in body["deferred"]["failing"]], ["bip_head"])
        self.assertEqual(body["deferred"]["failing"][0]["predicate"], "physical")
        self.assertTrue(all(p["result"] for p in body["precommit"]))

    def test_the_duplicate_comparison_is_field_level(self):
        dup = self.report()["analysis"]["duplicate"]
        self.assertEqual((dup["target"], dup["target_name"], dup["peer_names"]), (100, "Krystal", ["krystal20201"]))
        undo = dup["target_diffs"]["before_to_undo"]["detail"]
        self.assertEqual([r["flex"] for r in undo["flexes"]], ["smile"])
        self.assertEqual([r["control"] for r in undo["controls"]], ["Smile"])
        self.assertEqual(undo["bones"], [])
        applied = dup["target_diffs"]["before_to_apply"]["detail"]
        self.assertEqual([(r["bone"], list(r["fields"])) for r in applied["bones"]], [("bip_head", ["scale"])])
        self.assertEqual(set(dup["peer_diffs"]["before_to_undo"].values()), {"identical"})

    def test_persistent_failure_requires_and_reads_the_happy_step(self):
        out = self.report("persistent")
        self.assertEqual(out["verdict"], "EVIDENCE COMPLETE", out["failed"])
        self.assertIn("passes after Happy's refresh", out["analysis"]["body"]["reading"])
        self.assertIn("captured.HAPPY", self.report("persistent", "no-happy")["failed"])

    def test_not_reproduced_is_read_as_such(self):
        out = self.report("not-reproduced")
        self.assertEqual(out["verdict"], "EVIDENCE COMPLETE", out["failed"])
        self.assertIn("not reproduced", out["analysis"]["body"]["reading"])

    def test_incomplete_evidence_fails_on_its_own_check(self):
        cases = {"missing-capture": "captured.DUP-UNDO",
                 "wrong-build": "cpm.BODY",
                 "missing-fields": "fields.DUP-APPLY",
                 "hooks-left": "hooks.removed_at_dup_undo",
                 "inconsistent": "body.deferred_map_matches_cpm",
                 "refresh-map-error": "body.refresh_boundary_maps",
                 "visibility": "dup.no_intervening_visibility_edits",
                 "wrong-history": "dup.history_is_the_apply_then_its_undo",
                 "library-extra": "library.only_the_seeded_preset_and_known_character_rewrite",
                 "not-restored": "restore.published_and_inventories_equal",
                 "session-saved": "sessions.never_saved"}
        for fault, check in sorted(cases.items()):
            out = self.report(fault)
            self.assertEqual(out["verdict"], "EVIDENCE INCOMPLETE", fault)
            self.assertIn(check, out["failed"], (fault, out["failed"]))


if __name__ == "__main__":
    unittest.main()
