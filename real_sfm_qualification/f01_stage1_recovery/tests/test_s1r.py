# -*- coding: utf-8 -*-
"""Offline tests of the targeted native Abort recovery check kit (F-01 Stage 1).

1. The capture wrapper (Python 2.7.5, as in SFM, and Python 3):
   - it runs a pinned capture with its six steps and writes the direct Undo sidecar;
   - it refuses a changed capture, an unknown step or a second capture of a step, writing nothing;
   - it records non-boolean and unreadable observations as such;
   - the real Fox capture is the pinned one and accepts the patched step list.
2. The analyzer (Python 3), on a simulated run: the expected run passes, and every gate's failures give FAIL or INCOMPLETE as
   specified. A run-3-like old-build result fails.
3. The template (Python 3): its pins are the kit's files, the candidate CPM, the derived qualification build and
   run 3's preserved files.

usage: python -I test_s1r.py   (and the SFM Python 2.7, for the wrapper: python -E test_s1r.py)
"""
from __future__ import print_function

import copy
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(KIT, "..", ".."))
WRAPPER = os.path.join(KIT, "observer", "F01_S1R_Capture.py")
FOX_CAPTURE = os.path.join(KIT, "..", "f01_stage1_fox", "observer", "F01_S1F_Capture.py")
sys.path.insert(0, os.path.join(KIT, "tools"))
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read(path):
    with open(path, "rb") as f:
        return f.read()


def write(path, data):
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def write_json(path, obj):
    write(path, json.dumps(obj, indent=1, sort_keys=True))


def outcome(fn):
    try:
        return ("ok", fn())
    except Exception as exc:
        return (type(exc).__name__, u"%s" % exc)


# --- 1. the wrapper ----------------------------------------------------------------------------------------------

def exec_file(path, name):
    """A module namespace from a file, never run as __main__ (Python 2: no exec beside closures)."""
    ns = {"__name__": name}
    exec(compile(read(path), path, "exec"), ns)
    return ns


def wrapper_ns():
    return exec_file(WRAPPER, "s1r_capture_under_test")


STUB = b'''import json, os
STEPS = ("PREP",)
def s1f_try(fn):
    try:
        return fn()
    except Exception as exc:
        return {"error": repr(exc)}
def s1f_capture(g):
    if g.get("S1F_STEP") not in STEPS:
        raise RuntimeError("unknown step")
    path = os.path.join(g["S1F_DIR"], "observations", "S1F-%s.json" % g["S1F_STEP"])
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps({"step": g["S1F_STEP"], "steps": list(STEPS)}))
    return {"step": g["S1F_STEP"]}
'''


class DM(object):
    def __init__(self, **kw):
        self.v = {"IsUndoEnabled": True, "CanUndo": True, "CanRedo": False, "GetUndoDesc": u"Change Recording State",
                  "GetRedoDesc": u""}
        self.v.update(kw)

    def __getattr__(self, name):
        value = self.__dict__["v"][name]

        def read():
            if isinstance(value, Exception):
                raise value
            return value
        return read


def section_wrapper(root):
    ns = wrapper_ns()
    stub = os.path.join(root, "stub_capture.py")
    write(stub, STUB)
    stub_sha = sha_bytes(STUB)
    q = os.path.join(root, "q")
    os.makedirs(os.path.join(q, "observations"))
    obs = lambda: sorted(os.listdir(os.path.join(q, "observations")))  # noqa: E731
    g = {"S1F_DIR": q, "S1F_STEP": "ABORT1"}
    got = outcome(lambda: ns["s1r_capture"](g, stub, stub_sha, datamodel=DM()))
    side = json.loads(read(os.path.join(q, "observations", "S1F-ABORT1.undo.json")).decode("utf-8")) if \
        got[0] == "ok" else None
    cap = json.loads(read(os.path.join(q, "observations", "S1F-ABORT1.json")).decode("utf-8")) if \
        got[0] == "ok" else None
    check("wrapper.runs_the_capture_with_its_own_six_steps", cap is not None and cap["steps"] == [
        "BASE", "APPLY", "UNDO", "ABORT1", "ABORT2", "APPLY2"], (got, cap))
    check("wrapper.writes_the_direct_undo_sidecar", side == {"format": "F01-S1R-undo-v1", "step": "ABORT1",
                                                             "pid": os.getpid(), "undo": {
        "enabled": True, "can_undo": True, "can_redo": False, "undo_desc": u"Change Recording State",
        "redo_desc": u""}}, side)
    before = obs()
    got = outcome(lambda: ns["s1r_capture"](g, stub, stub_sha, datamodel=DM()))
    check("wrapper.refuses_a_second_capture_of_a_step", got[0] == "RuntimeError" and obs() == before, got)
    got = outcome(lambda: ns["s1r_capture"]({"S1F_DIR": q, "S1F_STEP": "NAV"}, stub, stub_sha, datamodel=DM()))
    check("wrapper.refuses_an_unknown_step", got[0] == "RuntimeError" and obs() == before, got)
    got = outcome(lambda: ns["s1r_capture"]({"S1F_DIR": q, "S1F_STEP": "BASE"}, stub, "0" * 64, datamodel=DM()))
    check("wrapper.refuses_a_capture_that_is_not_the_pinned_one", got[0] == "RuntimeError" and obs() == before, got)
    got = outcome(lambda: ns["s1r_capture"]({"S1F_DIR": q, "S1F_STEP": "UNDO"}, stub, stub_sha, datamodel=DM(
        IsUndoEnabled=1, GetRedoDesc=RuntimeError("no redo"))))
    side = json.loads(read(os.path.join(q, "observations", "S1F-UNDO.undo.json")).decode("utf-8")) if \
        got[0] == "ok" else {}
    check("wrapper.records_non_boolean_and_unreadable_observations_as_such",
          side.get("undo", {}).get("enabled") == {"non_boolean": "1"} and
          "unreadable" in side.get("undo", {}).get("redo_desc", {}), side)
    # The real Fox capture: the pinned file, found from the wrapper's own location, accepting the six steps.
    path = ns["s1r_capture_path"]()
    check("wrapper.finds_the_pinned_fox_capture", os.path.normcase(os.path.abspath(path)) == os.path.normcase(
        os.path.abspath(FOX_CAPTURE)) and sha_bytes(read(path)) == ns["S1F_CAPTURE_SHA256"], path)
    fox = exec_file(FOX_CAPTURE, "s1f_capture_under_test")
    fox["STEPS"] = ns["STEPS"]
    got = outcome(lambda: fox["s1f_capture"]({}))
    check("wrapper.the_fox_capture_takes_the_patched_step_list", got[0] == "RuntimeError" and
          "ABORT1, ABORT2, APPLY2" in got[1], got)


# --- 2. the analyzer, on a simulated run ---------------------------------------------------------------------------

QUAL, CAND = "q" * 64, "c" * 64
PID = u"dfdf47f5cf4d62ce527eebb31fa1d3c3"
RULE = {"rule": "structural_rig_v1", "revision": 1}
NAMES = {"source": "foxmccouldwm2", "target": "foxmccouldwm3", "peer": "foxmccouldwm1"}
BASE_U = {"enabled": True, "can_undo": True, "can_redo": False, "undo_desc": u"Change Recording State",
          "redo_desc": u""}
APPLY_U = dict(BASE_U, undo_desc=u"Apply Pose S1 Fox")
UNDO_U = dict(BASE_U, can_redo=True, redo_desc=u"Redo Apply Pose S1 Fox")
STATE = {"BASE": ("base", BASE_U), "APPLY": ("applied", APPLY_U), "UNDO": ("base", UNDO_U),
         "ABORT1": ("base", BASE_U), "ABORT2": ("base", BASE_U), "APPLY2": ("applied", APPLY_U)}
FAULT = u"RuntimeError(u'qualification fault injected at after-writes',)"


def set_(role, state):
    sha = {"base": u"A", "applied": u"B"}[state] if role == "target" else role
    bone = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], [1.0, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0]]
    return {"model": u"models/fursonas/foxmccouldwm.mdl", "channels": {u"rig_spine_0_o": {"sha256": sha}},
            "bones": {u"bip_spine": bone if state == "base" or role != "target" else
                      [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], [1.0, 2.0, 3.0], [0.0, 0.70710678, 0.0, 0.70710678]]},
            "admission": {"placement": u"rig_root"}}


def capture(q, step):
    state, u = STATE[step]
    return {"format": "F01-S1F-capture-v1", "step": step, "pid": 4242, "cpm_build_sha256": QUAL,
            "registry_mode": u"qualification", "qualification_fault": [None], "names": dict(NAMES), "errors": [],
            "sets": dict((r, set_(r, state)) for r in ("source", "target", "peer")),
            "session": {"document": os.path.join(q, "sessions", "S1R_SESSION.dmx").lower(), "head_seconds": 0.2083,
                        "shot": u"shot15", "timeline_mode": 2,
                        "undo": dict((k, v) for k, v in u.items() if k != "enabled")},
            "selected_pose": {"name": u"S1 Fox", "preset_id": PID, "adapter": RULE}}


def log_lines(redo_first=True, redo_second=False, written=212):
    t = "2026-11-20T10:00:00.000Z #000001 s=abc w=1 op=%d | "
    fail = json.dumps({"error": FAULT, "finished": False, "written": written})
    return [t % 1 + "PROD_POSE_BODY-P6 " + json.dumps({"owned": True, "written": 212}),
            t % 1 + "PROD_POSE_BODY-P7-verified {\"time\": {}}",
            t % 1 + "PROD_OPERATION_OUTCOME id=1 kind=u'Apply Pose' outcome=u'verified' detail=None",
            t % 2 + "PROD_POSE_BODY-P3-P6-failure " + fail,
            t % 2 + "PROD_POSE_BODY-abort-verified " + json.dumps({"problems": [], "redo_cleared": redo_first}),
            t % 2 + "PROD_OPERATION_OUTCOME id=2 kind=u'Apply Pose' outcome=u'recovery-verified' detail={}",
            t % 3 + "PROD_POSE_BODY-P3-P6-failure " + fail,
            t % 3 + "PROD_POSE_BODY-abort-verified " + json.dumps({"problems": [], "redo_cleared": redo_second}),
            t % 3 + "PROD_OPERATION_OUTCOME id=3 kind=u'Apply Pose' outcome=u'recovery-verified' detail={}",
            t % 4 + "PROD_POSE_BODY-P6 " + json.dumps({"owned": True, "written": 212}),
            t % 4 + "PROD_POSE_BODY-P7-verified {\"time\": {}}",
            t % 4 + "PROD_OPERATION_OUTCOME id=4 kind=u'Apply Pose' outcome=u'verified' detail=None"]


REC_REL = "Characters/foxmccouldwm--2d646d9605f0/Poses/S1 Fox--dfdf47f5cf4d.json"
SRC_REL = "Characters/foxmccouldwm--2d646d9605f0/pose_sources.json"


class Run(object):
    """A simulated finished run: captures, sidecars, the log and the evidence, all mutable before writing."""

    def __init__(self, root):
        self.q = os.path.join(root, "run")
        self.caps = dict((s, capture(self.q, s)) for s in STATE)
        self.sides = dict((s, {"format": "F01-S1R-undo-v1", "step": s, "pid": 4242, "undo": dict(STATE[s][1])})
                          for s in STATE)
        self.lines = log_lines()
        self.record = json.dumps({"preset_id": PID, "name": u"S1 Fox"}).encode("utf-8")
        self.sources = b'{"entries": {}}'
        self.session, self.spare = b"run 3 saved session", b"s3 destination"
        self.cleanup = None
        self.restored = True
        self.ids = {"qualification_cpm_sha256": QUAL, "candidate_cpm_sha256": CAND}

    def config(self):
        return {"paths": {"Q": self.q}, "pins": {
            "qualification_cpm_sha256": QUAL, "candidate_cpm_sha256": CAND,
            "r2_fixture_sha256": sha_bytes(b"run 3 saved session"), "destination_sha256": sha_bytes(b"s3 destination"),
            "run3_record_sha256": sha_bytes(self.record), "run3_sources_sha256": sha_bytes(self.sources)}}

    def write(self):
        q = self.q
        write_json(os.path.join(q, "staged", "IDENTITIES.json"), self.ids)
        for s, cap in self.caps.items():
            write_json(os.path.join(q, "observations", "S1F-%s.json" % s), cap)
        for s, side in self.sides.items():
            write_json(os.path.join(q, "observations", "S1F-%s.undo.json" % s), side)
        write(os.path.join(q, "sessions", "S1R_SESSION.dmx"), self.session)
        write(os.path.join(q, "sessions", "S1R_SPARE.dmx"), self.spare)
        write(os.path.join(q, "evidence", "logs", "CPM - 2026-11-20_10-00-00Z - pid4242 - 1 - 001.log"),
              "\n".join(self.lines) + "\n")
        pins = self.config()["pins"]
        write_json(os.path.join(q, "evidence", "seed.json"), {"files": {
            REC_REL: pins["run3_record_sha256"], SRC_REL: pins["run3_sources_sha256"]}})
        write(os.path.join(q, "evidence", "library_after", *REC_REL.split("/")), self.record)
        write(os.path.join(q, "evidence", "library_after", *SRC_REL.split("/")), self.sources)
        write_json(os.path.join(q, "evidence", "library_cleanup.json"), self.cleanup or {
            "differences_kept_in_evidence": [
                {"status": "added", "path": REC_REL, "sha256": pins["run3_record_sha256"]},
                {"status": "added", "path": SRC_REL, "sha256": pins["run3_sources_sha256"]}],
            "files_equal_pre": True, "folders_equal_pre": True})
        write_json(os.path.join(q, "evidence", "restore.json"), {"restored": self.restored,
                                                                 "inventory_problems": []})


def analyze(root, name, mutate):
    import s1r_analyze
    run = Run(os.path.join(root, name))
    mutate(run)
    run.write()
    saved = sys.stdout
    sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
    try:
        s1r_analyze.run(run.config())
    finally:
        sys.stdout = saved
    with open(os.path.join(run.q, "evidence", "S1R_VERDICT.json"), "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def section_analyzer(root):
    if sys.version_info[0] < 3:
        return                      # the analyzer is a Python 3 tool (run with -I after restore)

    def variant(name, mutate, verdict, failed_gate=None):
        out = analyze(root, name, mutate)
        bad = sorted(g for g, v in out["gates"].items() if v is not True)
        ok = out["verdict"] == verdict and (failed_gate is None or failed_gate in bad)
        check("analyzer.%s_is_%s" % (name, verdict.replace(" ", "_").lower()), ok,
              (out["verdict"], bad, out["failed"][:6]))
        return out

    out = variant("expected_run", lambda r: None, "AUTOMATED PASS")
    check("analyzer.expected_run_evaluates_every_gate", all(v is True for v in out["gates"].values()) and
          len(out["checks"]) >= 40, (out["gates"], len(out["checks"])))

    def caps(step, fn):
        def m(r):
            fn(r.caps[step])
        return m

    def side(step, **kw):
        def m(r):
            r.sides[step]["undo"].update(kw)
        return m

    def both(step, **kw):
        def m(r):
            r.sides[step]["undo"].update(kw)
            r.caps[step]["session"]["undo"].update(dict((k, v) for k, v in kw.items() if k != "enabled"))
        return m

    def lines(fn):
        def m(r):
            r.lines = fn(r.lines)
        return m

    # The old build's native result (Fox run 3): an unverified Abort and the lockout.
    def run3_like(r):
        r.lines = [l.replace("PROD_POSE_BODY-abort-verified {\"problems\": [], \"redo_cleared\": true}",
                             "PROD_POSE_BODY-abort-unverified {\"problems\": [\"Undo history changed or unreadable\"]}")
                   for l in r.lines]
        r.lines.insert(5, "x | PROD_POSE_RECOVERY_BLOCKED label=u'Apply Pose' process-wide=True")
    variant("run3_like_old_build_result", run3_like, "FAIL", "REDO_ABORT")
    variant("no_pending_redo_at_undo", both("UNDO", can_redo=False, redo_desc=u""), "FAIL", "APPLY")
    variant("undo_not_back_to_base", caps("UNDO", lambda c: c["sets"]["target"]["channels"][u"rig_spine_0_o"].update(
        sha256=u"B")), "FAIL", "APPLY")
    variant("abort1_fox_d_not_restored", caps("ABORT1", lambda c: c["sets"]["target"]["channels"][
        u"rig_spine_0_o"].update(sha256=u"B")), "FAIL", "REDO_ABORT")
    variant("abort1_fox_d_evaluated_differently", caps("ABORT1", lambda c: c["sets"]["target"]["bones"].update(
        {u"bip_spine": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], [1.5, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0]]})),
        "FAIL", "REDO_ABORT")
    variant("abort1_peer_changed", caps("ABORT1", lambda c: c["sets"]["peer"]["channels"][u"rig_spine_0_o"].update(
        sha256=u"other")), "FAIL", "PEER")
    variant("abort1_top_entry_changed", both("ABORT1", undo_desc=u"Apply Pose S1 Fox"), "FAIL", "REDO_ABORT")
    variant("abort1_undo_availability_changed", both("ABORT1", can_undo=False), "FAIL", "REDO_ABORT")
    variant("abort1_undo_disabled", side("ABORT1", enabled=False), "FAIL", "REDO_ABORT")
    variant("abort1_redo_kept", both("ABORT1", can_redo=True, redo_desc=u"Redo Apply Pose S1 Fox"), "FAIL",
            "REDO_ABORT")
    variant("abort1_cpm_did_not_report_redo_cleared", lines(lambda ls: log_lines(redo_first=False)), "FAIL",
            "REDO_ABORT")
    variant("abort_after_fewer_writes_than_the_apply", lines(lambda ls: log_lines(written=100)), "FAIL",
            "REDO_ABORT")
    variant("abort1_fault_slot_not_consumed", caps("ABORT1", lambda c: c.update(
        qualification_fault=[u"after-writes"])), "FAIL", "REDO_ABORT")
    variant("abort2_cpm_reported_redo_cleared", lines(lambda ls: log_lines(redo_second=True)), "FAIL",
            "EXACT_ABORT")
    variant("abort2_fox_d_differs", caps("ABORT2", lambda c: c["sets"]["target"]["channels"][
        u"rig_spine_0_o"].update(sha256=u"B")), "FAIL", "EXACT_ABORT")
    variant("abort2_undo_disabled", side("ABORT2", enabled=False), "FAIL", "EXACT_ABORT")
    variant("abort2_history_changed", both("ABORT2", undo_desc=u"Something"), "FAIL", "EXACT_ABORT")
    variant("apply2_not_verified", lines(lambda ls: ls[:-2] + ls[-1:]), "FAIL", "OPERATIONAL")
    variant("apply2_not_applied", caps("APPLY2", lambda c: c["sets"]["target"]["channels"][
        u"rig_spine_0_o"].update(sha256=u"A")), "FAIL", "OPERATIONAL")
    variant("a_recovery_lockout_logged", lines(lambda ls: ls + [
        "x | PROD_POSE_RECOVERY_BLOCKED label=u'Apply Pose' process-wide=True"]), "FAIL", "OPERATIONAL")
    variant("a_third_recovery_verified_outcome", lines(lambda ls: ls + [ls[5]]), "FAIL", "OPERATIONAL")
    variant("source_changed_at_apply2", caps("APPLY2", lambda c: c["sets"]["source"]["channels"][
        u"rig_spine_0_o"].update(sha256=u"other")), "FAIL", "PEER")
    # Evidence and setup: INCOMPLETE.
    variant("missing_abort1_sidecar", lambda r: r.sides.pop("ABORT1"), "INCOMPLETE", "EVIDENCE")
    variant("sidecar_disagrees_with_the_capture", side("UNDO", can_redo=False), "INCOMPLETE", "EVIDENCE")
    variant("sidecar_non_boolean_enabled", side("ABORT1", enabled={"non_boolean": "1"}), "INCOMPLETE", "EVIDENCE")
    variant("sidecar_unreadable_redo", side("ABORT1", redo_desc={"unreadable": "x"}), "INCOMPLETE", "EVIDENCE")
    variant("sidecar_from_another_process", lambda r: r.sides["ABORT2"].update(pid=1), "INCOMPLETE", "EVIDENCE")
    variant("missing_apply2_capture", lambda r: r.caps.pop("APPLY2"), "INCOMPLETE", "EVIDENCE")
    variant("two_sfm_processes", caps("APPLY2", lambda c: c.update(pid=4343)), "INCOMPLETE", "EVIDENCE")
    variant("another_session", caps("ABORT1", lambda c: c["session"].update(document=u"c:/other.dmx")),
            "INCOMPLETE", "EVIDENCE")
    variant("playhead_moved", caps("ABORT2", lambda c: c["session"].update(head_seconds=0.25)), "INCOMPLETE",
            "EVIDENCE")
    variant("session_copy_saved", lambda r: setattr(r, "session", b"saved"), "INCOMPLETE", "EVIDENCE")
    variant("wrong_build", lambda r: r.ids.update(qualification_cpm_sha256="0" * 64), "INCOMPLETE", "EVIDENCE")
    variant("capture_on_another_build", caps("ABORT1", lambda c: c.update(cpm_build_sha256="0" * 64)),
            "INCOMPLETE", "EVIDENCE")

    def extra_file(r):
        pins = r.config()["pins"]
        r.cleanup = {"differences_kept_in_evidence": [
            {"status": "added", "path": REC_REL, "sha256": pins["run3_record_sha256"]},
            {"status": "added", "path": SRC_REL, "sha256": pins["run3_sources_sha256"]},
            {"status": "added", "path": "Characters/x/Poses/y.json", "sha256": "1" * 64}],
            "files_equal_pre": True, "folders_equal_pre": True}
    variant("library_changed_by_more_than_the_seed", extra_file, "INCOMPLETE", "EVIDENCE")

    def record_changed(r):
        pins = r.config()["pins"]
        r.cleanup = {"differences_kept_in_evidence": [
            {"status": "added", "path": REC_REL, "sha256": "2" * 64},
            {"status": "added", "path": SRC_REL, "sha256": pins["run3_sources_sha256"]}],
            "files_equal_pre": True, "folders_equal_pre": True}
    variant("seeded_record_changed_during_the_run", record_changed, "INCOMPLETE", "EVIDENCE")
    variant("restore_incomplete", lambda r: setattr(r, "restored", False), "INCOMPLETE", "EVIDENCE")
    variant("another_pose_selected", caps("BASE", lambda c: c["selected_pose"].update(preset_id=u"other")),
            "INCOMPLETE", "SETUP")
    variant("other_set_names", lambda r: [c["names"].update(target="foxmccouldwm2", source="foxmccouldwm3")
                                          for c in r.caps.values()], "INCOMPLETE", "SETUP")


# --- 3. the template (Python 3: the reused tools are Python 3) -----------------------------------------------------

RUN3 = {"r2_fixture_sha256": "fcf2441c2c971e857f8f4953435d54a89b31b89d06ed7fe081692cc2401c26bf",
        "run3_record_sha256": "292bc33440334ee3c94011a74f8e189cafeb5e8a41ea8e6d6232d8eb346d2437",
        "run3_sources_sha256": "a31ea823135ab7f0f8efb7aab1a0324d175e5f2fd5d0fac48e3f34eb87369061"}


def section_template(root):
    t = json.loads(read(os.path.join(KIT, "s1r.template.json")).decode("utf-8"))
    pins = t["pins"]
    check("template.format", t["format"] == "F01-S1R-config-v1")
    files = {"wrapper_sha256": WRAPPER, "capture_sha256": FOX_CAPTURE,
             "analyzer_sha256": os.path.join(KIT, "tools", "s1r_analyze.py"),
             "procedure_sha256": os.path.join(KIT, "PROCEDURE.md")}
    check("template.kit_pins_are_the_kit_files", all(sha_bytes(read(p)) == pins[k] for k, p in files.items()),
          dict((k, sha_bytes(read(p))) for k, p in files.items()))
    cpm = read(os.path.join(REPO, "cpm", "app", "SFM_Character_Preset_Manager.py"))
    prod, qual = b'PROD_POSE_REGISTRY_MODE = u"production"', b'PROD_POSE_REGISTRY_MODE = u"qualification"'
    check("template.candidate_is_the_corrected_cpm", sha_bytes(cpm) == pins["candidate_cpm_sha256"] ==
          "7259e80a5d462eba1aeaa25cf89e9f57cf1081caaeac3002de8db6fbe488ab55")
    check("template.qualification_build_is_the_one_line_derivation", cpm.count(prod) == 1 and sha_bytes(
        cpm.replace(prod, qual)) == pins["qualification_cpm_sha256"] ==
        "39f2e35542180952d37f0d75b20d4c5cc89f24db16031b905655dc2310462421")
    check("template.run3_pins", all(pins[k] == v for k, v in RUN3.items()))
    fox = json.loads(read(os.path.join(KIT, "..", "f01_stage1_fox", "s1f.template.json")).decode("utf-8"))["pins"]
    check("template.shared_pins_as_in_the_fox_kit", all(pins[k] == fox[k] for k in (
        "profile_sha256", "body_profile_sha256", "published_cpm_sha256", "destination_sha256", "observer_sha256",
        "legacy_pose_sha256", "capture_sha256")))
    check("template.r2_fixture_is_run3s_saved_session", t["paths"]["R2_FIXTURE"] == "{RUN3}/sessions/s1_session.dmx")
    if sys.version_info[0] < 3:
        return
    import s1r_tool
    c = copy.deepcopy(t)
    c["paths"] = dict((k, v.replace("<RUN_DIR>", root).replace("<REPO>", REPO).replace("<", "").replace(">", ""))
                      for k, v in t["paths"].items())
    path = os.path.join(root, "s1r.json")
    write_json(path, c)
    loaded = s1r_tool.S.load(path)
    check("tool.loads_the_filled_template_and_pins_its_files", [s1r_tool.T.sha(p) == loaded["pins"][k] for p, k in
                                                               s1r_tool.pinned_kit_files(loaded)] == [True] * 4)
    check("tool.reused_tools_take_this_kits_identity", s1r_tool.S.FORMAT == "F01-S1R-config-v1" and
          s1r_tool.S.SESSIONS == ("S1R_SESSION.dmx",) and s1r_tool.S.DESTINATION == "S1R_SPARE.dmx" and
          s1r_tool.K.comparator().endswith("s1r_analyze.py"))


def main():
    print("F-01 Stage 1 Abort recovery check kit (Python %s)" % sys.version.split()[0])
    root = tempfile.mkdtemp(prefix="s1r_kit_")
    try:
        for fn in (section_wrapper, section_analyzer, section_template):
            try:
                fn(os.path.join(root, fn.__name__))
                check("section.%s.completed" % fn.__name__, True)
            except Exception:
                check("section.%s.completed" % fn.__name__, False, traceback.format_exc())
    finally:
        shutil.rmtree(root, True)
    failed = [r for r in RESULTS if not r[1]]
    print("RESULT: %d/%d %s (%s)" % (len(RESULTS) - len(failed), len(RESULTS),
                                     "ALL PASS" if not failed else "SOME FAILED", sys.version.split()[0]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
