# -*- coding: utf-8 -*-
"""F-01 RC4 short native check kit: offline tests of the analyzer (synthetic runs) and the kit pins. Python 3, -I.
A synthetic run of the procedure that every gate passes, then one defect at a time. Nothing here demonstrates native
SFM behaviour."""
from __future__ import print_function

import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
RC4X = os.path.join(KIT, "..", "f01_rc4_cross_rig")
sys.path.insert(0, os.path.join(KIT, "tools"))
sys.path.insert(0, os.path.join(RC4X, "tests"))
import rc4r_analyze as Z  # noqa: E402
import rc4r_tool as TOOL  # noqa: E402
import test_rc4x as K  # noqa: E402  (the RC4 kit test's synthetic characters)

RESULTS = []
X = Z.X
EXTRA = 110


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


APPLIED = K.undo(u"Apply Pose RC4 Sit")
UNDONE = K.undo(u"Rig", u"Redo Apply Pose RC4 Sit")
# step: (Tails N (pose, state), undo state)
PLAN = {"PREP": ((u"chest", u"base"), K.U0), "SAVED": ((u"chest", u"base"), K.U0),
        "B_BASE": ((u"chest", u"base"), K.U0), "B_APPLY": ((u"sit", u"b"), APPLIED),
        "B_NOOP": ((u"sit", u"b"), APPLIED), "B_UNDO": ((u"chest", u"base"), UNDONE)}
REP = {"limits": {"position": 0.01, "angle_degrees": 0.1}, "outputs": 124, "max_distance": 0.00095,
       "max_angle_deg": 0.0204}


def with_extra(s):
    root = s["handles"]["rig_root"][2]
    for i in range(EXTRA):
        s["bones"]["extra%d" % i] = [[0, 0, 0], K.rot(0), list(root), K.rot(0)]
    return s


def build(root, edit=None):
    run = {"caps": {}, "session_saved": False, "lines": [
        'PROD_POSE_BODY-RIG-adapted {"converted": [{"bone": "bip_spine_3", "destination": "constrained"}]}',
        'PROD_POSE_BODY-P1 {"actions": {"insert": 236, "none": 2, "update": 0}, "noop": false}',
        'PROD_POSE_BODY-P6 {"owned": true, "written": 236}',
        'PROD_POSE_BODY-P7-verified %s' % json.dumps({"reproduction": REP}),
        'PROD_POSE_BODY-P1 {"actions": {"insert": 0, "none": 238, "update": 0}, "noop": true}',
        'PROD_POSE_BODY-nowork {"result": "no-op"}']}
    for step, (tn, u) in PLAN.items():
        sets = {"source": with_extra(K.char(u"original", u"sit", u"base")),
                "target": with_extra(K.char(u"tails_n", *tn)), "peer": K.char(u"fox", None, None)}
        names = dict((r, s["name"]) for r, s in sets.items())
        run["caps"][step] = {"format": "F01-S1F-capture-v1", "step": step, "pid": 7, "cpm_build_sha256": K.QSHA,
                             "registry_mode": u"qualification", "qualification_fault": [None], "names": names,
                             "sets": sets, "errors": [], "session": {
                                 "undo": dict(u), "head_seconds": 0.2083, "timeline_mode": 2, "shot": u"shot15",
                                 "document": u"E:\\Q\\sessions\\RC4R_SESSION.dmx"}}
    if edit is not None:
        edit(run)
    q = os.path.join(root, "Q")
    for d in ("staged", "observations", "sessions", os.path.join("evidence", "logs")):
        os.makedirs(os.path.join(q, d))
    json.dump({"qualification_cpm_sha256": K.QSHA, "candidate_cpm_sha256": K.CSHA},
              open(os.path.join(q, "staged", "IDENTITIES.json"), "w"))
    for name, data in (("RC4R_SESSION.dmx", b"saved" if run["session_saved"] else b"r2"), ("RC4R_SPARE.dmx", b"sp")):
        open(os.path.join(q, "sessions", name), "wb").write(data)
    obs = os.path.join(q, "observations")
    for step, cap in run["caps"].items():
        json.dump(cap, open(os.path.join(obs, "S1F-%s.json" % step), "w"))
        json.dump({"format": X.LEAVES_FORMAT, "step": step, "pid": cap["pid"], "names": cap["names"],
                   "sets": dict((r, {"status": "READ"}) for r in X.ROLES)},
                  open(os.path.join(obs, "S1F-%s.leaves.json" % step), "w"))
        json.dump({"format": X.OFFSETS_FORMAT, "step": step, "pid": cap["pid"], "names": cap["names"],
                   "sets": dict((r, {"status": "READ", "constraints": []}) for r in X.ROLES)},
                  open(os.path.join(obs, "S1F-%s.offsets.json" % step), "w"))
    open(os.path.join(q, "evidence", "logs", "CPM.log"), "w").write("\n".join(run["lines"]) + "\n")
    lib = os.path.join(q, "evidence", "library_after", "Characters", "milestailsprower--x", "Poses")
    os.makedirs(lib)
    json.dump(K.record(X.SIT, u"original", K.descriptor()), open(os.path.join(lib, "RC4 Sit--x.json"), "w"))
    diffs = [{"status": "added", "path": "Characters/milestailsprower--x/Poses/RC4 Sit--x.json"}] + [
        {"status": "added", "path": "Characters/milestailsprower--x/%s" % n} for n in ("pose_sources.json",
                                                                                     "pose_rigs.json")]
    json.dump({"differences_kept_in_evidence": diffs, "files_equal_pre": True, "folders_equal_pre": True},
              open(os.path.join(q, "evidence", "library_cleanup.json"), "w"))
    json.dump({"restored": True}, open(os.path.join(q, "evidence", "restore.json"), "w"))
    return {"paths": {"Q": q}, "pins": {"qualification_cpm_sha256": K.QSHA, "candidate_cpm_sha256": K.CSHA,
                                        "r2_fixture_sha256": hashlib.sha256(b"r2").hexdigest(),
                                        "destination_sha256": hashlib.sha256(b"sp").hexdigest()}}


def analyze(edit=None):
    root = tempfile.mkdtemp(prefix="rc4r_test_")
    try:
        R = Z.Report(build(root, edit))
        Z.evaluate(R)
        v, gates = Z.verdict(R.checks)
        return v, gates, [x["id"] for x in R.checks if not x["pass"]], R.info
    finally:
        shutil.rmtree(root, True)


def section_analyzer():
    v, gates, failed, info = analyze()
    check("synthetic_run_passes_every_gate", v == "AUTOMATED PASS", (v, gates, failed))
    check("records_cpm_and_independent_maxima", info.get("cpm_reproduction") == [REP] and "posture" in info and
          info.get("neighbour_keys_kept") is not None)

    def line(old, new):
        return lambda run: run.__setitem__("lines", [new if old in l else l for l in run["lines"]])

    def add(text):
        return lambda run: run["lines"].append(text)

    def moved(step, dz):
        def edit(run):
            b = run["caps"][step]["sets"]["target"]["bones"][u"bip_spine_3"]
            b[2] = [b[2][0], b[2][1], b[2][2] + dz]
        return edit

    def fox(run):
        run["caps"]["B_NOOP"]["sets"]["peer"]["channels"]["fox_o"]["sha256"] = "moved"

    def undo_bad(run):
        run["caps"]["B_UNDO"]["sets"]["target"]["channels"]["Finger_o"]["sha256"] = "not-restored"

    def missing(run):
        del run["caps"]["B_NOOP"]

    def saved(run):
        run["session_saved"] = True
    far = dict(REP, max_angle_deg=0.12)
    for label, edit, gate in (
            (u"mismatch_in_the_log", add('PROD_POSE_BODY-P7-reproduction-mismatch {"problems": ["x"]}'), "EVIDENCE"),
            (u"unverified_in_the_log", add('PROD_POSE_BODY-P7-unverified {"problems": ["x"]}'), "EVIDENCE"),
            (u"cpm_maxima_beyond_the_envelope", line("P7-verified", 'PROD_POSE_BODY-P7-verified %s' %
                                                     json.dumps({"reproduction": far})), "APPLY"),
            (u"independent_posture_beyond_0.01", moved("B_APPLY", 0.011), "POSTURE"),
            (u"undo_opened_at_the_repeat", add('PROD_POSE_BODY-P6 {"owned": true, "written": 0}'), "NOOP"),
            (u"no_work_mismatch", line("BODY-nowork", 'PROD_POSE_BODY-nowork {"result": "mismatch"}'), "NOOP"),
            (u"undo_not_restoring", undo_bad, "UNDO"),
            (u"peer_changed", fox, "PEER"),
            (u"missing_capture", missing, "EVIDENCE"),
            (u"session_saved", saved, "EVIDENCE")):
        v, gates, failed, _ = analyze(edit)
        check("defect_%s_fails_%s" % (label, gate), v != "AUTOMATED PASS" and gates.get(gate) is not True,
              (v, gates, failed[:6]))
    v, gates, failed, _ = analyze(moved("B_APPLY", 0.009))
    check("posture_within_0.01_passes", v == "AUTOMATED PASS", (v, failed))


def section_kit():
    paths = [p for p, _ in TOOL.pinned_kit_files({})]
    check("kit_files_exist", all(os.path.isfile(p) for p in paths), paths)
    template = os.path.join(KIT, "rc4r.template.json")
    c = json.load(open(template)) if os.path.isfile(template) else {}
    pins = c.get("pins") or {}
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()  # noqa: E731
    check("template_pins_the_kit_files", all(pins.get(pin) == sha(path) for path, pin in TOOL.pinned_kit_files(c)),
          [(pin, pins.get(pin), sha(path)) for path, pin in TOOL.pinned_kit_files(c) if pins.get(pin) != sha(path)])
    check("template_format", c.get("format") == TOOL.FORMAT)
    repo = os.path.abspath(os.path.join(KIT, "..", ".."))
    raw = open(os.path.join(repo, "cpm", "app", "SFM_Character_Preset_Manager.py"), "rb").read()
    qual = raw.replace(b'PROD_POSE_REGISTRY_MODE = u"production"', b'PROD_POSE_REGISTRY_MODE = u"qualification"')
    check("template_pins_the_committed_candidate_and_its_qualification_build", pins.get("candidate_cpm_sha256") ==
          hashlib.sha256(raw).hexdigest() and pins.get("qualification_cpm_sha256") == hashlib.sha256(qual).hexdigest(),
          (pins.get("candidate_cpm_sha256"), hashlib.sha256(raw).hexdigest()))
    check("steps_are_rc4x_capture_steps", set(Z.STEPS) <= set(X.STEPS))
    check("analyzer_envelope_is_astras", (Z.POSITION, Z.ANGLE) == (0.01, 0.1))


def main():
    section_analyzer()
    section_kit()
    failed = [n for n, ok in RESULTS if not ok]
    print("RESULT: %d/%d %s" % (len(RESULTS) - len(failed), len(RESULTS), "ALL PASS" if not failed else "SOME FAILED"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
