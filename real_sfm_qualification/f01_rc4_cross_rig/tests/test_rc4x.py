# -*- coding: utf-8 -*-
"""F-01 RC4 native cross-rig kit: offline tests of the analyzer (synthetic runs) and the kit pins. Python 3, -I.

A synthetic run of the procedure that every gate passes, then one defect at a time: each must fail its own gate and
never produce AUTOMATED PASS. Nothing here demonstrates native SFM behaviour.
"""
from __future__ import print_function

import copy
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KIT, "tools"))
import rc4x_analyze as X  # noqa: E402
import rc4x_tool as TOOL  # noqa: E402

RESULTS = []
T = 50208
MODEL = X.MODEL
TN = u"milestailsprower2"


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def rot(deg):
    h = math.radians(deg) / 2.0
    return [0.0, 0.0, math.sin(h), math.cos(h)]


# --- a synthetic run ---------------------------------------------------------------------------------------------

POSE_CHEST = {u"bip_pelvis": ([0.0, 0.0, 5.0], rot(0.0)), u"bip_spine_3": ([0.0, 0.5, 10.0], rot(30.0)),
              u"Finger": ([1.0, 0.0, 8.0], rot(40.0)), u"ear3_L": ([0.0, 0.0, 12.0], rot(0.0))}
POSE_SIT = {u"bip_pelvis": ([0.0, 0.0, 3.0], rot(0.0)), u"bip_spine_3": ([0.0, -0.5, 7.0], rot(-20.0)),
            u"Finger": ([1.5, 0.0, 6.0], rot(-10.0)), u"ear3_L": ([0.0, 0.0, 9.0], rot(0.0))}
ROOTS = {u"tails_n": [300.0, 0.0, 0.0], u"original": [0.0, 0.0, 0.0], u"fox": [-200.0, 0.0, 0.0]}
LEAVES = [u"ear3_L"]
WRITTEN = {u"tails_n": [u"rig_chest_o", u"Finger_o"], u"original": [u"rig_pelvis_o", u"bip_spine_3_o", u"Finger_o"]}


def char(who, pose_name, state):
    """One captured set: the character `who` holding pose `pose_name` (its body posture) in authored state `state`."""
    if who == u"fox":
        return {"name": X.PEER, "model": u"models/fursonas/foxmccouldwm.mdl", "channels": {
            u"fox_o": {"sha256": "fox", "keys": [[[0, 1]]]}}, "bones": {u"b": [[0, 0, 1], rot(0), [-200, 0, 1],
                                                                              rot(0)]},
            "handles": {u"rig_root": [[0, 0, 0], rot(0), ROOTS[who], rot(0)]},
            "model_state": [[0, 0, 0], rot(0), ROOTS[who], rot(0)], "admission": {"handles": 22, "constraints": 34}}
    pose = POSE_CHEST if pose_name == u"chest" else POSE_SIT
    root = ROOTS[who]
    bones = dict((n, [[0.0, 1.0, 0.0], rot(0.0), [root[i] + p[i] for i in range(3)], q])
                 for n, (p, q) in pose.items())
    classes = {u"bip_pelvis": u"constrained", u"Finger": u"fk", u"ear3_L": X.LEAF,
               u"bip_spine_3": u"constrained" if who == u"tails_n" else u"fk"}
    roles = dict((n, u"handle-written" if n.startswith(u"rig_") else u"fk-written") for n in WRITTEN[who])
    roles[u"ear3_L_o"] = X.LEAF
    roles[u"neighbour_o"] = u"fk-written" if who == u"original" else u"slave-base"
    channels = {}
    for n in list(roles):
        changed = n in WRITTEN[who] and state != u"base"
        keys = [[[0, u"own"]]] if not changed else [[[0, u"own"], [T, u"%s" % state]]]
        channels[n] = {"sha256": u"%s:%s:%s" % (who, n, state if changed else u"base"), "keys": keys}
    channels[u"neighbour_o"]["keys"] = [[[0, u"n"], [T + 100, u"n2"]]]
    return {"name": TN if who == u"tails_n" else X.ORIGINAL, "model": MODEL, "channels": channels, "bones": bones,
            "handles": {u"rig_root": [[0, 0, 0], rot(0), root, rot(0)]},
            "model_state": [[0, 0, 0], rot(0), root, rot(0)],
            "admission": {"handles": 23 if who == u"tails_n" else 22, "constraints": 36 if who == u"tails_n" else 34,
                          "bone_classes": classes, "roles": roles, "written": WRITTEN[who], "t_chan": T,
                          "rig_name": u"rig_biped_%s" % (TN if who == u"tails_n" else X.ORIGINAL),
                          "placement": u"rig_root"}}


U0 = {"can_undo": True, "can_redo": False, "undo_desc": u"Rig", "redo_desc": u""}


def undo(top, redo=None):
    return {"can_undo": True, "can_redo": redo is not None, "undo_desc": top, "redo_desc": redo or u""}


UA, UB = undo(u"Apply Pose RC4 Chest"), undo(u"Apply Pose RC4 Sit")
FINAL_A, FINAL_B = undo(u"Rig", u"Redo Apply Pose RC4 Chest"), undo(u"Rig", u"Redo Apply Pose RC4 Sit")
# step: (tails_n (pose, state), original (pose, state), undo, roles A or B)
PLAN = {
    "PREP": ((u"chest", u"base"), (u"sit", u"base"), U0, "A"),
    "SAVED": ((u"chest", u"base"), (u"sit", u"base"), U0, "A"),
    "A_BASE": ((u"chest", u"base"), (u"sit", u"base"), U0, "A"),
    "A_APPLY": ((u"chest", u"base"), (u"chest", u"a"), UA, "A"),
    "A_NAV": ((u"chest", u"base"), (u"chest", u"a"), UA, "A"),
    "A_UNDO": ((u"chest", u"base"), (u"sit", u"base"), FINAL_A, "A"),
    "A_REDO": ((u"chest", u"base"), (u"chest", u"a"), UA, "A"),
    "A_NOOP": ((u"chest", u"base"), (u"chest", u"a"), UA, "A"),
    "A_FINAL": ((u"chest", u"base"), (u"sit", u"base"), FINAL_A, "A"),
    "B_BASE": ((u"chest", u"base"), (u"sit", u"base"), FINAL_A, "B"),
    "B_APPLY": ((u"sit", u"b"), (u"sit", u"base"), UB, "B"),
    "B_NAV": ((u"sit", u"b"), (u"sit", u"base"), UB, "B"),
    "B_UNDO": ((u"chest", u"base"), (u"sit", u"base"), FINAL_B, "B"),
    "B_REDO": ((u"sit", u"b"), (u"sit", u"base"), UB, "B"),
    "B_NOOP": ((u"sit", u"b"), (u"sit", u"base"), UB, "B"),
    "ABORT": ((u"sit", u"b"), (u"sit", u"base"), UB, "A"),
    "B_FINAL": ((u"chest", u"base"), (u"sit", u"base"), FINAL_B, "B"),
}
QSHA, CSHA = "q" * 64, "c" * 64


def descriptor(offset_deg=0.0, vec=0.0):
    return {"constraints": [
        {"type": u"DmeRigIKConstraintOperator", "slaves": {"endJoint": u"bone:bip_hand_L"}, "targets": [
            u"handle:rig_hand_L"], "pole": u"handle:rig_elbow_L", "solver": {"startOffset": {
                "present": True, "value": rot(10.0 + offset_deg)}}, "offsets": {"oOffset": {
                    "present": True, "value": rot(0.0)}, "vecOffset": {"present": True, "value": [0.0, 0.0, 0.0]}}},
        {"type": u"DmeRigOrientConstraintOperator", "slaves": {"slave": u"bone:bip_hand_L"}, "targets": [
            u"handle:rig_hand_L"], "pole": None, "solver": {}, "offsets": {"oOffset": {
                "present": True, "value": rot(0.0)}, "vecOffset": {"present": True, "value": [vec, 0.0, 0.0]}}}]}


def record(name, who, desc):
    return {"name": name, "preset_id": hashlib.md5(name.encode("utf-8")).hexdigest(), "pose": {
        "version": 2, "adapter": X.RULE, "source": {"model_ref": MODEL}, "regions": {"full_body": {
            "positions": {}, "orientations": dict((n, rot(0.0)) for n in WRITTEN[who]), "descriptor": desc}}}}


def live_rows(desc):
    out = []
    for c in desc["constraints"]:
        out.append({"identity": json.dumps([c["type"], c["slaves"], c["targets"], c["pole"]], sort_keys=True,
                                           separators=(",", ":")), "type": c["type"], "solver": c["solver"],
                    "offsets": c["offsets"]})
    return out


def build(root, edit=None):
    """Write a complete synthetic run; `edit(run)` changes the in-memory run before it is written."""
    run = {"caps": {}, "lines": [], "dest_offsets": (0.0013, 6e-6), "session_saved": False}
    for step, (tn, orig, u, roles) in PLAN.items():
        sets = {"source": char(u"tails_n", *tn) if roles == "A" else char(u"original", *orig),
                "target": char(u"original", *orig) if roles == "A" else char(u"tails_n", *tn),
                "peer": char(u"fox", None, None)}
        names = dict((r, s["name"]) for r, s in sets.items())
        run["caps"][step] = {"format": "F01-S1F-capture-v1", "step": step, "pid": 4242, "cpm_build_sha256": QSHA,
                             "registry_mode": u"qualification", "qualification_fault": [None], "names": names,
                             "sets": sets, "errors": [], "session": {
                                 "undo": dict(u), "head_seconds": 0.2083, "timeline_mode": 2, "shot": u"shot15",
                                 "document": u"E:\\Q\\sessions\\RC4X_SESSION.dmx"}}
    run["lines"] = [
        'PROD_POSE_BODY-RIG-adapted {"converted": [{"bone": "bip_spine_3", "destination": "fk"}]}',
        'PROD_POSE_BODY-rotation-equivalent {"count": 4, "limit_deg": 0.005, "max_angle_deg": 0.0013}',
        'PROD_POSE_BODY-P7-verified {}',
        'PROD_POSE_BODY-P1 {"noop": true}',
        'PROD_POSE_BODY-RIG-adapted {"converted": [{"bone": "bip_spine_3", "destination": "constrained"}]}',
        'PROD_POSE_BODY-P7-verified {}',
        'PROD_POSE_BODY-P1 {"noop": true}',
        'PROD_POSE_BODY-P3-P6-failure {"error": "ProdPoseError(\'qualification fault injected at after-writes\')", '
        '"finished": false, "written": 40}',
        'PROD_POSE_BODY-abort-verified {"problems": [], "redo_cleared": false}']
    if edit is not None:
        edit(run)
    q = os.path.join(root, "Q")
    for d in ("staged", "observations", "sessions", os.path.join("evidence", "logs")):
        os.makedirs(os.path.join(q, d))
    with open(os.path.join(q, "staged", "IDENTITIES.json"), "w") as f:
        json.dump({"qualification_cpm_sha256": QSHA, "candidate_cpm_sha256": CSHA}, f)
    for name, data in (("RC4X_SESSION.dmx", b"session-saved" if run["session_saved"] else b"r2"),
                       ("RC4X_SPARE.dmx", b"spare")):
        with open(os.path.join(q, "sessions", name), "wb") as f:
            f.write(data)
    for step, cap in run["caps"].items():
        obs = os.path.join(q, "observations")
        with open(os.path.join(obs, "S1F-%s.json" % step), "w") as f:
            json.dump(cap, f)
        with open(os.path.join(obs, "S1F-%s.leaves.json" % step), "w") as f:
            json.dump({"format": X.LEAVES_FORMAT, "step": step, "pid": cap["pid"], "names": cap["names"],
                       "sets": dict((r, {"status": "READ"}) for r in X.ROLES)}, f)
        deg, vec = run["dest_offsets"]
        sets = dict((r, {"status": "READ", "constraints": live_rows(descriptor(deg, vec))}) for r in X.ROLES)
        with open(os.path.join(obs, "S1F-%s.offsets.json" % step), "w") as f:
            json.dump({"format": X.OFFSETS_FORMAT, "step": step, "pid": cap["pid"], "names": cap["names"],
                       "sets": sets}, f)
    with open(os.path.join(q, "evidence", "logs", "CPM.log"), "w") as f:
        f.write("\n".join(run["lines"]) + "\n")
    lib = os.path.join(q, "evidence", "library_after", "Characters", "milestailsprower--x", "Poses")
    os.makedirs(lib)
    diffs = []
    for name, who in ((X.CHEST, u"tails_n"), (X.SIT, u"original")):
        path = os.path.join(lib, "%s--x.json" % name)
        with open(path, "w") as f:
            json.dump(record(name, who, descriptor()), f)
        diffs.append({"status": "added", "path": "Characters/milestailsprower--x/Poses/%s--x.json" % name})
    diffs += [{"status": "added", "path": "Characters/milestailsprower--x/%s" % n} for n in (
        "pose_sources.json", "pose_rigs.json", "character.json")]
    with open(os.path.join(q, "evidence", "library_cleanup.json"), "w") as f:
        json.dump({"differences_kept_in_evidence": diffs, "files_equal_pre": True, "folders_equal_pre": True}, f)
    with open(os.path.join(q, "evidence", "restore.json"), "w") as f:
        json.dump({"restored": True}, f)
    pins = {"qualification_cpm_sha256": QSHA, "candidate_cpm_sha256": CSHA,
            "r2_fixture_sha256": hashlib.sha256(b"r2").hexdigest(),
            "destination_sha256": hashlib.sha256(b"spare").hexdigest()}
    return {"paths": {"Q": q}, "pins": pins}


def analyze(edit=None):
    root = tempfile.mkdtemp(prefix="rc4x_test_")
    try:
        c = build(root, edit)
        R = X.Report(c)
        X.evaluate(R)
        v, gates = X.verdict(R.checks)
        return v, gates, [x["id"] for x in R.checks if not x["pass"]], R.info
    finally:
        shutil.rmtree(root, True)


def section_analyzer():
    v, gates, failed, info = analyze()
    check("synthetic_run_passes_every_gate", v == "AUTOMATED PASS", (v, gates, failed))
    check("records_the_actual_destination_offsets", abs(info["actual_destination_offsets"]["A"]["max_angle_deg"] -
                                                        0.0013) < 1e-6 and abs(info["actual_destination_offsets"][
                                                            "A"]["max_distance"] - 6e-6) < 1e-12, info.get(
        "actual_destination_offsets"))
    check("records_the_independent_skeletal_errors", "A_posture" in info and "B_posture" in info and
          info["A_posture"]["bones"] == 3)

    def target(step, key):
        def edit(run):
            key(run["caps"][step]["sets"]["target"])
        return edit

    def change_channel(name, sha):
        return lambda s: s["channels"][name].__setitem__("sha256", sha)

    def set_undo(step, u):
        return lambda run: run["caps"][step]["session"].__setitem__("undo", u)

    def nav_entry(run):
        for step in ("A_NAV", "B_NAV"):
            run["caps"][step]["session"]["undo"] = undo(X.NAV_ENTRY)

    def redo_cleared(run):
        for step in ("B_REDO", "B_NOOP"):
            run["caps"][step]["session"]["undo"] = undo(u"Apply Pose RC4 Sit", u"Redo Modify Time Selection")
        run["caps"]["ABORT"]["session"]["undo"] = undo(u"Apply Pose RC4 Sit")
        run["lines"][-1] = 'PROD_POSE_BODY-abort-verified {"problems": [], "redo_cleared": true}'
    for label, edit in ((u"navigation_time_selection_entry", nav_entry),
                        (u"abort_with_sfm_cleared_redo", redo_cleared)):
        v, gates, failed, _ = analyze(edit)
        check("documented_%s_is_accepted" % label, v == "AUTOMATED PASS", (v, failed))

    def moved_bone(step, bone, dz):
        def edit(run):
            b = run["caps"][step]["sets"]["target"]["bones"][bone]
            b[2] = [b[2][0], b[2][1], b[2][2] + dz]
        return edit

    def neighbour(run):
        run["caps"]["A_APPLY"]["sets"]["target"]["channels"]["Finger_o"]["keys"] = [[[0, u"changed"], [T, u"a"]]]

    def far_offsets(run):
        run["dest_offsets"] = (0.0051, 6e-6)

    def far_vector(run):
        run["dest_offsets"] = (0.0013, 0.000101)

    def fox_changed(run):
        run["caps"]["B_REDO"]["sets"]["peer"]["channels"]["fox_o"]["sha256"] = "moved"

    def abort_changed(run):
        run["caps"]["ABORT"]["sets"]["target"]["channels"]["Finger_o"]["sha256"] = "aborted-badly"

    def abort_unverified(run):
        run["lines"][-1] = 'PROD_POSE_BODY-abort-unverified {"problems": ["x"]}'

    def missing_capture(run):
        del run["caps"]["B_UNDO"]

    def saved(run):
        run["session_saved"] = True

    def not_adapted(run):
        run["lines"] = [l for l in run["lines"] if "RIG-adapted" not in l]

    def placement(run):
        run["caps"]["B_APPLY"]["sets"]["target"]["handles"]["rig_root"][2] = [301.0, 0.0, 0.0]

    def history(run):
        run["caps"]["A_UNDO"]["sets"]["target"]["channels"]["Finger_o"]["sha256"] = "not-restored"
    for label, edit, gate in (
            (u"channel_outside_the_plan", target("A_APPLY", change_channel(u"neighbour_o", u"x")), "A_APPLY"),
            (u"neighbouring_key_changed", neighbour, "A_APPLY"),
            (u"posture_error_beyond_the_tolerance", moved_bone("B_APPLY", u"bip_spine_3", 0.2), "B_POSTURE"),
            (u"placement_moved", placement, "B_POSTURE"),
            (u"undo_not_restoring", history, "A_HISTORY"),
            (u"offsets_beyond_the_angle_bound", far_offsets, "ADAPT"),
            (u"offsets_beyond_the_distance_bound", far_vector, "ADAPT"),
            (u"no_adaptation_logged", not_adapted, "ADAPT"),
            (u"peer_changed", fox_changed, "PEER"),
            (u"abort_not_restoring", abort_changed, "ABORT"),
            (u"abort_not_verified", abort_unverified, "EVIDENCE"),
            (u"missing_capture", missing_capture, "EVIDENCE"),
            (u"session_saved", saved, "EVIDENCE")):
        v, gates, failed, _ = analyze(edit)
        check("defect_%s_fails_%s" % (label, gate), v != "AUTOMATED PASS" and gates.get(gate) is not True,
              (v, gates, failed[:6]))


# --- the capture wrapper, through the pinned Stage 2 wrapper (the Stage 2 suite's stub capture and fake CPM) -------

def section_wrapper():
    sys.path.insert(0, os.path.join(KIT, "..", "f01_stage2_tails", "tests"))
    import test_s2t as S2  # noqa: E402

    class FakeCPM(S2.FakeCPM):
        """The Stage 2 fake, plus the functions the offsets sidecar reads (one constraint row per set)."""

        def prod_pose_time_read(self, L, names):
            return {u"t_chan": T}

        def prod_body_rig_time_names(self, L):
            return []

        def prod_pose_writer_index(self):
            return {}

        def prod_body_discover(self, L, t, index):
            return {u"t": t}

        def prod_body_rig_draft(self, D):
            return {u"handles": dict((n, u"@rig") for n in range(23))}

        def prod_body_classify(self, D, P):
            return {}

        def prod_body_descriptor(self, D, C, P):
            return descriptor(0.001, 2e-6)

        def prod_body_constraint_identity(self, row):
            return json.dumps([row["type"], row["slaves"], row["targets"], row["pole"]], sort_keys=True,
                              separators=(",", ":"))
    root = tempfile.mkdtemp(prefix="rc4x_wrapper_")
    try:
        path = os.path.join(KIT, "observer", "F01_RC4X_Capture.py")
        ns = {"__name__": "rc4x_capture_under_test"}
        exec(compile(open(path).read(), path, "exec"), ns)
        s2t, s1f = ns["rc4x_paths"]()
        stub = os.path.join(root, "stub_capture.py")
        with open(stub, "wb") as f:
            f.write(S2.STUB)
        q = os.path.join(root, "q")
        os.makedirs(os.path.join(q, "observations"))
        names = (TN, X.ORIGINAL, X.PEER)
        g = {"S1F_DIR": q, "S1F_STEP": "A_APPLY", "S1F_SOURCE": TN, "S1F_TARGET": X.ORIGINAL, "S1F_PEER": X.PEER}
        run = lambda g_, sha=ns["S2T_WRAPPER_SHA256"]: S2.outcome(lambda: ns["rc4x_capture"](  # noqa: E731
            g_, s2t, stub, sha, cpm=FakeCPM(S2.fake_header(), sets=names), shot="shot",
            s1f_sha256=S2.sha_bytes(S2.STUB)))
        got = run(g)
        obs = os.path.join(q, "observations")
        cap = json.load(open(os.path.join(obs, "S1F-A_APPLY.json"))) if got[0] == "ok" else {}
        off = json.load(open(os.path.join(obs, "S1F-A_APPLY.offsets.json"))) if got[0] == "ok" else {}
        check("wrapper.runs_the_pinned_stage2_wrapper_with_this_tests_steps", cap.get("steps") == list(X.STEPS) and
              os.path.isfile(os.path.join(obs, "S1F-A_APPLY.leaves.json")), (got, cap))
        rows = ((off.get("sets") or {}).get("target") or {}).get("constraints") or []
        check("wrapper.writes_the_offsets_sidecar_with_the_descriptor_rows", off.get("format") == X.OFFSETS_FORMAT and
              off.get("step") == "A_APPLY" and off.get("names") == {"source": TN, "target": X.ORIGINAL,
                                                                    "peer": X.PEER} and len(rows) == 2 and
              rows[1]["offsets"]["vecOffset"]["value"] == [2e-6, 0.0, 0.0] and off["sets"]["target"]["handles"] == 23,
              off)
        before = sorted(os.listdir(obs))
        check("wrapper.refuses_a_second_capture_of_a_step", run(g)[0] == "RuntimeError" and
              sorted(os.listdir(obs)) == before)
        check("wrapper.refuses_an_unknown_step", run(dict(g, S1F_STEP="APPLY"))[0] == "RuntimeError" and
              sorted(os.listdir(obs)) == before)
        check("wrapper.refuses_a_stage2_wrapper_that_is_not_the_pinned_one", run(dict(g, S1F_STEP="B_APPLY"),
                                                                                "0" * 64)[0] == "RuntimeError" and
              sorted(os.listdir(obs)) == before)
        check("wrapper.finds_the_pinned_reused_captures", hashlib.sha256(open(s2t, "rb").read()).hexdigest() ==
              ns["S2T_WRAPPER_SHA256"] and os.path.basename(s1f) == "F01_S1F_Capture.py" and os.path.isfile(s1f))
    finally:
        shutil.rmtree(root, True)


# --- the replay under the revised verification contract ---------------------------------------------------------

def section_replay():
    sys.path.insert(0, os.path.join(KIT, "tools"))
    import rc4x_replay as RP  # noqa: E402

    def replay(b_offset, logged_b, original=u"INCOMPLETE"):
        def edit(run):
            for step in ("B_APPLY", "B_NAV", "B_REDO", "B_NOOP"):
                bone = run["caps"][step]["sets"]["target"]["bones"][u"bip_spine_3"]
                bone[2] = [bone[2][0] + b_offset, bone[2][1], bone[2][2]]
            run["lines"] = [l for l in run["lines"] if "P7-verified" not in l and "BODY-P1" not in l] + [
                'PROD_POSE_BODY-P7-verified {}', 'PROD_POSE_BODY-P1 {"actions": {"insert": 0, "none": 5, "update": 0}}',
                'PROD_POSE_BODY-P7-%s' % logged_b, 'PROD_POSE_BODY-P1 {"actions": {"insert": 0, "none": 5, "update": 0}}',
                'PROD_POSE_BODY-P1 {"noop": true}', 'PROD_POSE_BODY-P1 {"noop": true}']
        root = tempfile.mkdtemp(prefix="rc4x_replay_")
        try:
            c = build(root, edit)
            ev = os.path.join(c["paths"]["Q"], "evidence")
            lib = os.path.join(ev, "library_after", "Characters", "milestailsprower--x", "Poses")
            for name, pose in ((X.CHEST, POSE_CHEST), (X.SIT, POSE_SIT)):
                path = os.path.join(lib, "%s--x.json" % name)
                rec = json.load(open(path))
                rec["pose"]["regions"]["full_body"]["oracle"] = {"bones": dict(
                    (n, {"position": p, "orientation": q}) for n, (p, q) in pose.items() if n not in LEAVES)}
                # a reference of more than 100 bones, as a real record has
                for i in range(110):
                    rec["pose"]["regions"]["full_body"]["oracle"]["bones"]["extra%d" % i] = {
                        "position": [0.0, 0.0, 0.0], "orientation": [0.0, 0.0, 0.0, 1.0]}
                json.dump(rec, open(path, "w"))
            for step in X.STEPS:
                path = os.path.join(c["paths"]["Q"], "observations", "S1F-%s.json" % step)
                cap = json.load(open(path))
                for role in ("source", "target"):
                    bones = cap["sets"][role]["bones"]
                    root_p = cap["sets"][role]["handles"]["rig_root"][2]
                    for i in range(110):
                        bones["extra%d" % i] = [[0, 0, 0], rot(0), list(root_p), rot(0)]
                json.dump(cap, open(path, "w"))
            with open(os.path.join(ev, "RC4X_VERDICT.json"), "w") as f:
                json.dump({"verdict": original}, f)
            before = open(os.path.join(ev, "RC4X_VERDICT.json")).read()
            code = RP.run(c)
            out = json.load(open(os.path.join(ev, "replay_revised_contract", "RC4X_REPLAY.json")))
            again = S2_outcome(lambda: RP.run(c))
            return code, out, before == open(os.path.join(ev, "RC4X_VERDICT.json")).read(), again
        finally:
            shutil.rmtree(root, True)

    def S2_outcome(fn):
        try:
            return ("ok", fn())
        except Exception as exc:
            return (type(exc).__name__,)
    stdout = sys.stdout
    sys.stdout = open(os.devnull, "w")
    try:
        ok = replay(0.005, 'unverified {"problems": ["bone bip_spine_3"]}')
        far = replay(0.05, 'unverified {"problems": ["bone bip_spine_3"]}')
        wrong_log = replay(0.005, 'verified {}')
    finally:
        sys.stdout.close()
        sys.stdout = stdout
    check("replay.former_failure_within_the_revised_envelope_passes", ok[0] == 0 and ok[1]["verdict"].startswith(
        "REPLAY PASS") and ok[1]["info"]["B"]["APPLY"]["former_failures"] == [u"bip_spine_3"] and
        ok[1]["info"]["B"]["APPLY"]["revised_failures"] == [], [x for x in ok[1]["checks"] if not x["pass"]])
    check("replay.never_changes_the_original_verdict_and_refuses_to_overwrite", ok[2] and ok[3][0] != "ok")
    check("replay.beyond_the_revised_envelope_fails", far[0] == 1 and far[1]["info"]["B"]["APPLY"][
        "revised_failures"] == [u"bip_spine_3"])
    check("replay.self_check_catches_a_disagreement_with_cpms_log", wrong_log[0] == 1 and not [
        x for x in wrong_log[1]["checks"] if x["id"] == "selfcheck.former_limits_reproduce_cpm_direction_b_bones"][0][
        "pass"])
    check("replay.limits", RP.REVISED == {"position": 0.01, "angle_degrees": 0.1} and RP.FORMER == {
        "position": 0.001, "angle_degrees": 0.01})


def section_kit():
    paths = [p for p, _ in TOOL.pinned_kit_files({})]
    check("kit_files_exist", all(os.path.isfile(p) for p in paths), paths)
    template = os.path.join(KIT, "rc4x.template.json")
    c = json.load(open(template)) if os.path.isfile(template) else {}
    pins = c.get("pins") or {}
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()  # noqa: E731
    check("template_pins_the_kit_files", all(pins.get(pin) == sha(path) for path, pin in TOOL.pinned_kit_files(c)),
          [(pin, pins.get(pin), sha(path)) for path, pin in TOOL.pinned_kit_files(c) if pins.get(pin) != sha(path)])
    check("template_format", c.get("format") == TOOL.FORMAT)
    repo = os.path.abspath(os.path.join(KIT, "..", ".."))
    cand = os.path.join(repo, "cpm", "app", "SFM_Character_Preset_Manager.py")
    raw = open(cand, "rb").read()
    qual = raw.replace(b'PROD_POSE_REGISTRY_MODE = u"production"', b'PROD_POSE_REGISTRY_MODE = u"qualification"')
    check("template_pins_the_committed_candidate_and_its_qualification_build", pins.get("candidate_cpm_sha256") ==
          hashlib.sha256(raw).hexdigest() and pins.get("qualification_cpm_sha256") == hashlib.sha256(qual).hexdigest(),
          (pins.get("candidate_cpm_sha256"), hashlib.sha256(raw).hexdigest()))
    src = open(os.path.join(KIT, "observer", "F01_RC4X_Capture.py")).read()
    ns = {"__name__": "rc4x_capture_under_test"}
    exec(compile(src, "F01_RC4X_Capture.py", "exec"), ns)
    check("capture_steps_equal_the_analyzer_steps", tuple(ns["STEPS"]) == X.STEPS, (ns["STEPS"], X.STEPS))
    check("capture_pins_the_stage2_wrapper", ns["S2T_WRAPPER_SHA256"] == pins.get("s2t_wrapper_sha256"))
    check("analyzer_bounds_are_astras", X.ROTATION_LIMIT == 0.005 and X.VECTOR_LIMIT == 0.0001)


def main():
    section_analyzer()
    section_wrapper()
    section_replay()
    section_kit()
    failed = [n for n, ok in RESULTS if not ok]
    print("RESULT: %d/%d %s" % (len(RESULTS) - len(failed), len(RESULTS), "ALL PASS" if not failed else "SOME FAILED"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
