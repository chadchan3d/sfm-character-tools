# -*- coding: utf-8 -*-
"""Offline tests of the native Tails JIGGLE leaf qualification kit (F-01 Stage 2).

1. The capture wrapper (Python 2.7.5, as in SFM, and Python 3):
   - it runs a pinned capture with its seven steps and writes the leaf sidecar;
   - it refuses a changed capture, an unknown step or a second capture of a step, writing nothing;
   - the sidecar, run against the candidate CPM's own functions on the Tails fixture (the stage E harness), records
     the seven declared JIGGLE leaves, their scale fields and the constants; an unreadable header is recorded as such;
   - the real Fox capture is the pinned one and accepts the patched step list.
2. The analyzer (Python 3), on a simulated run: the expected run passes with the simulated tips moving at every
   capture, and every gate's failures give FAIL, REFUSED or INCOMPLETE as specified.
3. The template (Python 3): its pins are the kit's files, the Stage 2 candidate CPM and the derived qualification
   build, and the shared pins of the Fox kit.

usage: python -I test_s2t.py   (and the SFM Python 2.7, for the wrapper: python -E -B test_s2t.py)
"""
from __future__ import print_function

import copy
import hashlib
import io
import json
import math
import os
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(KIT, "..", ".."))
WRAPPER = os.path.join(KIT, "observer", "F01_S2T_Capture.py")
FOX_CAPTURE = os.path.join(KIT, "..", "f01_stage1_fox", "observer", "F01_S1F_Capture.py")
CONVERGENCE = os.path.join(REPO, "cpm", "convergence", "tests")
sys.path.insert(0, os.path.join(KIT, "tools"))
RESULTS = []
LEAVES = [u"HairSpike_B3", u"HairSpike_M3", u"HairSpike_T3", u"Tail6_L", u"Tail6_R", u"ear3_L", u"ear3_R"]
MODEL = u"models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl"


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


def exec_file(path, name):
    ns = {"__name__": name}
    exec(compile(read(path), path, "exec"), ns)
    return ns


# --- 1. the wrapper ----------------------------------------------------------------------------------------------

STUB = b'''import json, os
STEPS = ("PREP",)
def s1f_capture(g):
    if g.get("S1F_STEP") not in STEPS:
        raise RuntimeError("unknown step")
    path = os.path.join(g["S1F_DIR"], "observations", "S1F-%s.json" % g["S1F_STEP"])
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps({"step": g["S1F_STEP"], "steps": list(STEPS)}))
    return {"step": g["S1F_STEP"], "sets": {"source": {"admission": {"bone_classes": dict(
        ("b%d" % i, "simulated-leaf") for i in range(7))}}, "target": {"admission": {"code": "structure-unsupported"}}}}
'''


class Named(object):
    def __init__(self, name):
        self.name = name

    def GetName(self):
        return self.name


class FakeCPM(object):
    """The CPM functions the sidecar uses, over a fixed header (read-only)."""

    def __init__(self, header, sets=(u"Tails S", u"Tails D", u"milestailsprower1")):
        self.header, self.sets = header, [Named(n) for n in sets]

    def prod_pose_attr(self, obj, name):
        return self.sets if name == u"animationSets" else ("transform-of", obj)

    def prod_pose_seq(self, value):
        return list(value)

    def get_game_model(self, animset):
        return ("gm", animset.GetName())

    def prod_body_live(self, row, profile):
        assert profile is None
        return {u"bones": dict((r["name"], {u"dag": r["name"]}) for r in self.header.get("bones", []))}

    def prod_body_rig_header(self, L):
        return self.header

    def prod_pose_field(self, obj, name):
        return {u"status": u"READ", u"value": 1.0} if obj[1] == u"Tail6_L" else {u"status": u"ABSENT"}


def fake_header():
    rows = [{"index": i, "name": n, "parent": 0, "flags": 0x504, "proctype": 5} for i, n in enumerate(LEAVES, 1)]
    rows.insert(0, {"index": 0, "name": u"bip_pelvis", "parent": -1, "flags": 0x100, "proctype": 0})
    return {"status": "READ", "bones": rows, "attachments": [0], "flex_drivers": [3],
            "constants": {"STUDIO_PROC_JIGGLE": 5, "BONE_ALWAYS_PROCEDURAL": 4}}


def section_wrapper(root):
    ns = exec_file(WRAPPER, "s2t_capture_under_test")
    stub = os.path.join(root, "stub_capture.py")
    write(stub, STUB)
    stub_sha = sha_bytes(STUB)
    q = os.path.join(root, "q")
    os.makedirs(os.path.join(q, "observations"))
    obs = lambda: sorted(os.listdir(os.path.join(q, "observations")))  # noqa: E731
    g = {"S1F_DIR": q, "S1F_STEP": "PREP", "S1F_SOURCE": u"Tails S", "S1F_TARGET": u"Tails D",
         "S1F_PEER": u"milestailsprower1"}
    got = outcome(lambda: ns["s2t_capture"](g, stub, stub_sha, cpm=FakeCPM(fake_header()), shot="shot"))
    cap = json.loads(read(os.path.join(q, "observations", "S1F-PREP.json")).decode("utf-8")) if got[0] == "ok" else None
    side = json.loads(read(os.path.join(q, "observations", "S1F-PREP.leaves.json")).decode("utf-8")) if \
        got[0] == "ok" else {}
    check("wrapper.runs_the_capture_with_its_own_seven_steps", cap is not None and cap["steps"] == [
        "PREP", "SAVED", "BASE", "APPLY", "NAV", "UNDO", "REDO"], (got, cap))
    s = (side.get("sets") or {}).get("target") or {}
    check("wrapper.writes_the_leaf_sidecar", side.get("format") == "F01-S2T-leaves-v1" and side.get("step") ==
          "PREP" and side.get("pid") == os.getpid() and side.get("names") == {
              "source": u"Tails S", "target": u"Tails D", "peer": u"milestailsprower1"} and
          sorted(side["sets"]) == ["peer", "source", "target"] and s.get("status") == "READ", side)
    declared = dict((d["name"], d) for d in s.get("declared") or [])
    check("wrapper.sidecar_records_declarations_users_scales_and_constants", sorted(declared) == sorted(LEAVES) and
          declared[u"HairSpike_T3"]["flex_driver"] is True and declared[u"HairSpike_B3"]["flex_driver"] is False and declared[u"ear3_L"]["attachment"] is False and
          s["scales"][u"Tail6_L"] == {u"status": u"READ", u"value": 1.0} and s["scales"][u"ear3_R"] == {
              u"status": u"ABSENT"} and s["constants"]["STUDIO_PROC_JIGGLE"] == 5 and s["bones"] == 8, s)
    before = obs()
    got = outcome(lambda: ns["s2t_capture"](g, stub, stub_sha, cpm=FakeCPM(fake_header()), shot="shot"))
    check("wrapper.refuses_a_second_capture_of_a_step", got[0] == "RuntimeError" and obs() == before, got)
    got = outcome(lambda: ns["s2t_capture"](dict(g, S1F_STEP="ABORT"), stub, stub_sha, cpm=FakeCPM(fake_header()),
                                            shot="shot"))
    check("wrapper.refuses_an_unknown_step", got[0] == "RuntimeError" and obs() == before, got)
    got = outcome(lambda: ns["s2t_capture"](dict(g, S1F_STEP="BASE"), stub, "0" * 64, cpm=FakeCPM(fake_header()),
                                            shot="shot"))
    check("wrapper.refuses_a_capture_that_is_not_the_pinned_one", got[0] == "RuntimeError" and obs() == before, got)
    got = outcome(lambda: ns["s2t_capture"](dict(g, S1F_STEP="SAVED"), stub, stub_sha, cpm=FakeCPM(
        {"status": "UNREADABLE", "reason": "test"}, sets=(u"Tails S", u"milestailsprower1")), shot="shot"))
    side = json.loads(read(os.path.join(q, "observations", "S1F-SAVED.leaves.json")).decode("utf-8")) if \
        got[0] == "ok" else {}
    check("wrapper.records_an_unreadable_header_and_a_missing_set_as_such", side.get("sets", {}).get(
        "source") == {"status": "UNREADABLE", "reason": u"test"} and side["sets"]["target"] == {
        "status": "NOT_FOUND", "count": 0}, side)
    path = ns["s2t_capture_path"]()
    check("wrapper.finds_the_pinned_fox_capture", os.path.normcase(os.path.abspath(path)) == os.path.normcase(
        os.path.abspath(FOX_CAPTURE)) and sha_bytes(read(path)) == ns["S1F_CAPTURE_SHA256"], path)
    fox = exec_file(FOX_CAPTURE, "s1f_capture_under_test")
    fox["STEPS"] = ns["STEPS"]
    got = outcome(lambda: fox["s1f_capture"]({}))
    check("wrapper.the_fox_capture_takes_the_patched_step_list", got[0] == "RuntimeError" and
          "NAV, UNDO, REDO" in got[1] and "ABORT" not in got[1], got)


class Attrs(object):
    """A namespace dictionary seen as a module (the loaded CPM)."""

    def __init__(self, ns, **extra):
        self.__dict__["ns"], self.__dict__["extra"] = ns, extra

    def __getattr__(self, name):
        if name in self.__dict__["extra"]:
            return self.__dict__["extra"][name]
        return self.__dict__["ns"][name]


def section_sidecar_on_the_candidate(root):
    """The sidecar against the candidate CPM's own functions, on the Tails fixture with a native-shaped header."""
    sys.path.insert(0, CONVERGENCE)
    saved_out = sys.stdout
    try:
        sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
        import test_cpm_app_canonical_route as route
        import test_cpm_app_f01_body as B
        import test_cpm_app_f01_jiggle_leaf as J
        ns = B.live_namespace(route.AppSource(route.APP_PATH))
        fx = J.fixture()
    finally:
        sys.stdout = saved_out
    check("candidate.is_the_stage2_cpm", route._sha(route.APP_PATH) ==
          "001377f9704ffd4e52503330feea2d4dcf271dd9541a6889d109f6801985de70")
    w = J.world(fx, posed=False)
    J.use(ns, w)
    name = w.animset.GetName()
    cpm = Attrs(ns, get_game_model=lambda animset: w.gm)
    wrap = exec_file(WRAPPER, "s2t_capture_under_test")
    side = wrap["s2t_sidecar"](cpm, w.shot, {"source": name, "target": name, "peer": name})
    s = side["target"]
    declared = dict((d["name"], d) for d in s.get("declared") or [])
    check("candidate.sidecar_reads_the_seven_jiggle_leaves", s.get("status") == "READ" and sorted(declared) ==
          sorted(LEAVES) and all(d["proctype"] == 5 and d["flags"] == 0x504 and not d["attachment"] and
                                 not d["flex_driver"] for d in declared.values()) and s["bones"] == 131, s)
    check("candidate.sidecar_reads_the_leaf_scale_fields", sorted(s["scales"]) == sorted(LEAVES) and all(
        isinstance(v, dict) and v.get(u"status") in (u"READ", u"ABSENT") for v in s["scales"].values()), s["scales"])
    check("candidate.sidecar_reads_the_constants", s["constants"].get("STUDIO_PROC_JIGGLE") == 5 and
          s["constants"].get("BONE_ALWAYS_PROCEDURAL") == 4, s["constants"])
    check("candidate.sidecar_is_read_only", not B.scene_writes(w) and not w.dm.calls)
    w2 = J.world(fx, posed=False, header=False)
    J.use(ns, w2)
    side = wrap["s2t_sidecar"](Attrs(ns, get_game_model=lambda animset: w2.gm), w2.shot, {"source": name,
                                                                                         "target": name,
                                                                                         "peer": name})
    check("candidate.no_header_is_recorded_as_unreadable", side["target"].get("status") == "UNREADABLE",
          side["target"])


# --- 2. the analyzer, on a simulated run ---------------------------------------------------------------------------

QUAL, CAND = "q" * 64, "c" * 64
PID = u"5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a"
RULE = {"rule": "structural_rig_v1", "revision": 2}
NAMES = {"source": u"milestailsprower2", "target": u"milestailsprower3", "peer": u"milestailsprower1"}
T_CHAN = 50208
IDQ = [0.0, 0.0, 0.0, 1.0]
TURN = [0.0, 0.0, math.sin(math.radians(45)), math.cos(math.radians(45))]     # 90 degrees about z
BASE_U = {"can_undo": True, "can_redo": False, "undo_desc": u"Change Recording State", "redo_desc": u""}
APPLY_U = dict(BASE_U, undo_desc=u"Apply Pose S2 Tails")
UNDO_U = dict(BASE_U, can_redo=True, redo_desc=u"Redo Apply Pose S2 Tails")
STATE = {"PREP": ("base", BASE_U, 1), "SAVED": ("base", BASE_U, 1), "BASE": ("base", BASE_U, 2),
         "APPLY": ("applied", APPLY_U, 2), "NAV": ("applied", APPLY_U, 2), "UNDO": ("base", UNDO_U, 2),
         "REDO": ("applied", APPLY_U, 2)}
STEP_INDEX = dict((s, i) for i, s in enumerate(("PREP", "SAVED", "BASE", "APPLY", "NAV", "UNDO", "REDO")))
REC_REL = u"Characters/milestailsprower--5a5a5a5a5a5a/Poses/S2 Tails--5a5a5a5a5a5a.json"
SRC_REL = u"Characters/milestailsprower--5a5a5a5a5a5a/pose_sources.json"
WRITTEN = [u"rig_spine_0_o", u"Tail5_L_o"]


def leaf_channels():
    return sorted([n + u"_o" for n in LEAVES] + [n + u"_p" for n in LEAVES])


def bone(wp, wq, lp=None):
    return [list(lp or [1.0, 0.0, 0.0]), list(IDQ), list(wp), list(wq)]


def set_(role, state, step):
    """Source at the origin; target 500 units away, posed differently at base and as the source when applied; the
    simulated leaves (and the peer's) move at every capture."""
    k = STEP_INDEX[step] + 1
    offset = [500.0, 0.0, 0.0] if role == "target" else [0.0, 0.0, 0.0] if role == "source" else [0.0, 300.0, 0.0]
    posed = role != "target" or state == "applied"
    bones = {u"bip_spine": bone([offset[0], offset[1] + 10.0, 0.0], IDQ if posed else TURN),
             u"Tail5_L": bone([offset[0] + 1.0, offset[1] + 20.0, 0.0], IDQ)}
    for i, n in enumerate(LEAVES):
        bones[n] = [[0.1 * k, 0.0, 0.0], list(IDQ), [offset[0] + i + 0.37 * k, offset[1] + 30.0, 0.0], list(IDQ)]
    applied = role == "target" and state == "applied"
    channels = {}
    for n in WRITTEN:
        keys = [[[0, [0.0, 0.0, 0.0, 1.0]]]] + ([[[T_CHAN, [0.0, 0.0, 0.1, 0.99498744]]]] if applied else [])
        channels[n] = {"sha256": u"%s-%s-%s" % (role, n, "B" if applied else "A"), "frame": u"f-%s" % n,
                       "keys": [[[0, [0.0, 0.0, 0.0, 1.0]]] + ([[T_CHAN, [0.0, 0.0, 0.1, 0.99498744]]] if applied
                                                               else [])], "to": u"x"}
    for n in leaf_channels():
        channels[n] = {"sha256": u"%s-%s" % (role, n), "frame": u"f-%s" % n, "keys": [[[0, [1.0, 2.0, 3.0]]]],
                       "to": u"bone 1 (%s)" % n[:-2]}
    roles = dict((n, u"simulated-leaf") for n in leaf_channels())
    roles.update({u"rig_spine_0_o": u"handle-written", u"Tail5_L_o": u"fk-written"})
    classes = dict((n, u"simulated-leaf") for n in LEAVES)
    classes.update({u"bip_spine": u"constrained", u"Tail5_L": u"fk"})
    admission = {"placement": u"rig_root", "description_sha256": u"D", "rig_name": u"rig_biped_%s" % NAMES[role],
                 "bone_classes": classes, "roles": roles, "written": list(WRITTEN), "t_chan": T_CHAN}
    return {"model": MODEL, "channels": channels, "bones": bones,
            "handles": {u"rig_root": bone(offset, IDQ, [0.0, 0.0, 0.0])},
            "model_state": bone(offset, IDQ, [0.0, 0.0, 0.0]), "admission": admission}


def capture(q, step):
    state, u, process = STATE[step]
    return {"format": "F01-S1F-capture-v1", "step": step, "pid": 4000 + process, "cpm_build_sha256": QUAL,
            "registry_mode": u"qualification", "qualification_fault": [None], "names": dict(NAMES), "errors": [],
            "sets": dict((r, set_(r, state if r == "target" else "base", step)) for r in ("source", "target", "peer")),
            "session": {"document": os.path.join(q, "sessions", "S2T_SESSION.dmx").lower(), "head_seconds": 0.2083,
                        "shot": u"shot15", "timeline_mode": 2, "undo": dict(u)},
            "selected_pose": {"name": u"S2 Tails", "preset_id": PID, "adapter": RULE}}


def sidecar(step):
    process = STATE[step][2]
    one = {"status": "READ", "bones": 131, "constants": {"STUDIO_PROC_JIGGLE": 5, "BONE_ALWAYS_PROCEDURAL": 4},
           "declared": [{"index": i, "name": n, "parent": i - 1, "flags": 0x504, "proctype": 5, "attachment": False,
                         "flex_driver": False} for i, n in enumerate(LEAVES, 1)],
           "scales": dict((n, {u"status": u"ABSENT"}) for n in LEAVES)}
    return {"format": "F01-S2T-leaves-v1", "step": step, "pid": 4000 + process, "names": dict(NAMES),
            "sets": dict((r, copy.deepcopy(one)) for r in ("source", "target", "peer"))}


def log_lines():
    t = "2026-11-21T10:00:00.000Z #000001 s=abc w=1 op=%d | "
    return [t % 1 + "PROD_POSE_BODY-RIG-available " + json.dumps({"handles": 22, "constraints": 34, "written": 238,
                                                                   "simulated_leaves": LEAVES}),
            t % 2 + "PROD_POSE_BODY-P6 " + json.dumps({"owned": True, "written": 238}),
            t % 2 + "PROD_POSE_BODY-P7-verified {\"time\": {}}"]


def record():
    bones = [{"name": n, "class": u"simulated-leaf"} for n in LEAVES] + [
        {"name": u"bip_spine", "class": u"constrained"}, {"name": u"Tail5_L", "class": u"fk"}]
    return {"preset_id": PID, "name": u"S2 Tails", "pose": {
        "version": 2, "adapter": dict(RULE), "source": {"model_ref": MODEL},
        "regions": {"full_body": {"positions": {}, "orientations": dict((n, IDQ) for n in WRITTEN),
                                  "descriptor": {"bones": bones},
                                  "oracle": {"bones": {u"bip_spine": {}, u"Tail5_L": {}}}}}}}


class Run(object):
    def __init__(self, root):
        self.q = os.path.join(root, "run")
        self.caps = dict((s, capture(self.q, s)) for s in STATE)
        self.sides = dict((s, sidecar(s)) for s in STATE)
        self.lines = log_lines()
        self.record = record()
        self.session, self.spare = b"prepared session", b"s3 destination"
        self.restored = True
        self.extra = []
        self.ids = {"qualification_cpm_sha256": QUAL, "candidate_cpm_sha256": CAND}

    def config(self):
        return {"paths": {"Q": self.q}, "pins": {
            "qualification_cpm_sha256": QUAL, "candidate_cpm_sha256": CAND,
            "r2_fixture_sha256": sha_bytes(b"r2 fixture"), "destination_sha256": sha_bytes(b"s3 destination")}}

    def write(self):
        q = self.q
        write_json(os.path.join(q, "staged", "IDENTITIES.json"), self.ids)
        for s, cap in self.caps.items():
            write_json(os.path.join(q, "observations", "S1F-%s.json" % s), cap)
        for s, side in self.sides.items():
            write_json(os.path.join(q, "observations", "S1F-%s.leaves.json" % s), side)
        write(os.path.join(q, "sessions", "S2T_SESSION.dmx"), self.session)
        write(os.path.join(q, "sessions", "S2T_SPARE.dmx"), self.spare)
        write(os.path.join(q, "evidence", "logs", "CPM - 2026-11-21_10-00-00Z - pid4002 - 1 - 001.log"),
              "\n".join(self.lines) + "\n")
        diffs = []
        if self.record is not None:
            raw = json.dumps(self.record).encode("utf-8")
            write(os.path.join(q, "evidence", "library_after", *REC_REL.split("/")), raw)
            sources = json.dumps({"record_kind": u"cpm-pose-sources", "schema_version": 1, "entries": {
                PID: {"project": os.path.join(q, "sessions", "S2T_SESSION.dmx")}}}).encode("utf-8")
            write(os.path.join(q, "evidence", "library_after", *SRC_REL.split("/")), sources)
            diffs = [{"status": "added", "path": REC_REL, "sha256": sha_bytes(raw)},
                     {"status": "added", "path": SRC_REL, "sha256": sha_bytes(sources)}]
        write_json(os.path.join(q, "evidence", "library_cleanup.json"), {
            "differences_kept_in_evidence": diffs + self.extra, "files_equal_pre": True, "folders_equal_pre": True})
        write_json(os.path.join(q, "evidence", "restore.json"), {"restored": self.restored,
                                                                 "inventory_problems": []})


def analyze(root, name, mutate):
    import s2t_analyze
    run = Run(os.path.join(root, name))
    mutate(run)
    run.write()
    saved = sys.stdout
    sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
    try:
        s2t_analyze.run(run.config())
    finally:
        sys.stdout = saved
    with open(os.path.join(run.q, "evidence", "S2T_VERDICT.json"), "rb") as f:
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

    out = variant("expected_run_with_the_tips_moving_at_every_capture", lambda r: None, "AUTOMATED PASS")
    check("analyzer.expected_run_evaluates_every_gate", all(v is True for v in out["gates"].values()) and
          sorted(out["gates"]) == ["APPLY", "EVIDENCE", "HISTORY", "LEAVES", "PEER", "POSTURE", "PREP", "SAVE"] and
          len(out["checks"]) >= 50, (out["gates"], len(out["checks"])))
    check("analyzer.tip_movement_is_reported_as_information", all(
        v > 0 for v in out["info"]["tip_local_position_change_from_base"].values()),
        out["info"].get("tip_local_position_change_from_base"))

    def caps(step, fn):
        def m(r):
            fn(r.caps[step])
        return m

    def each(steps, fn):
        def m(r):
            for s in steps:
                fn(r.caps[s])
        return m

    def tset(c, role="target"):
        return c["sets"][role]

    def side(step, role, fn):
        def m(r):
            fn(r.sides[step]["sets"][role])
        return m

    # REFUSED: a safe refusal with its exact reason.
    def refused(r):
        r.record = None
        r.lines = ["x | PROD_POSE_BODY-RIG-leaf-refused " + json.dumps({"refusals": {
            u"Tail6_L": u"an attachment or bone flex driver uses it"}}),
            "x | PROD_POSE_BODY-RIG-unavailable " + json.dumps({"code": "structure-unsupported"})]
        for s in ("BASE", "APPLY", "NAV", "UNDO", "REDO"):
            r.caps.pop(s)
            r.sides.pop(s)
    out = variant("tails_s_save_refused", refused, "REFUSED")
    check("analyzer.refusal_reports_the_exact_reason", u"an attachment or bone flex driver uses it" in json.dumps(
        out["info"].get("refusal")), out["info"].get("refusal"))
    # PREP
    variant("only_six_leaves_admitted", caps("PREP", lambda c: tset(c)["admission"]["bone_classes"].update(
        {u"Tail6_R": u"fk"})), "INCOMPLETE", "PREP")
    variant("admitted_leaves_differ_from_the_declared_jiggle_bones", side("PREP", "source", lambda s: s[
        "declared"][0].update(proctype=2)), "INCOMPLETE", "PREP")
    variant("same_rig_name_for_s_and_d", each(STATE, lambda c: tset(c)["admission"].update(
        rig_name=tset(c, "source")["admission"]["rig_name"])), "INCOMPLETE", "PREP")
    variant("different_drafted_descriptions", caps("PREP", lambda c: tset(c)["admission"].update(
        description_sha256=u"E")), "INCOMPLETE", "PREP")
    variant("tails_d_not_placed_differently", each(STATE, lambda c: tset(c)["handles"][u"rig_root"].__setitem__(
        2, [0.0, 0.0, 0.0])), "INCOMPLETE", "PREP")
    variant("session_not_reopened_as_prepared", caps("BASE", lambda c: tset(c)["channels"][u"Tail5_L_o"].update(
        frame=u"other")), "INCOMPLETE", "PREP")
    variant("another_model", each(STATE, lambda c: tset(c).update(model=u"models/other.mdl")), "INCOMPLETE", "PREP")
    # SAVE
    variant("record_revision_1", lambda r: r.record["pose"]["adapter"].update(revision=1), "FAIL", "SAVE")
    variant("record_misses_a_leaf", lambda r: r.record["pose"]["regions"]["full_body"]["descriptor"]["bones"].pop(0),
            "FAIL", "SAVE")
    variant("record_saves_a_leaf_value", lambda r: r.record["pose"]["regions"]["full_body"]["orientations"].update(
        {u"Tail6_L_o": IDQ}), "FAIL", "SAVE")
    variant("record_has_a_leaf_oracle", lambda r: r.record["pose"]["regions"]["full_body"]["oracle"]["bones"].update(
        {u"Tail6_L": {}}), "FAIL", "SAVE")
    variant("admission_log_without_the_leaves", lambda r: setattr(r, "lines", [
        l.replace("simulated_leaves", "other") for l in r.lines]), "FAIL", "SAVE")
    variant("posing_continued_after_prep", caps("SAVED", lambda c: tset(c, "source")["channels"][
        u"rig_spine_0_o"].update(sha256=u"moved")), "FAIL", "SAVE")
    variant("record_not_selected_after_the_restart", caps("BASE", lambda c: c["selected_pose"].update(
        preset_id=u"other")), "FAIL", "SAVE")
    # APPLY
    variant("apply_wrote_a_leaf_channel", each(("APPLY", "NAV", "REDO"), lambda c: tset(c)["channels"][
        u"Tail6_L_o"].update(sha256=u"written")), "FAIL", "APPLY")
    variant("apply_changed_an_unplanned_channel", each(("APPLY", "NAV", "REDO"), lambda c: tset(c)["channels"][
        u"ear3_L_o"].update(sha256=u"written")), "FAIL", "APPLY")
    variant("apply_not_verified", lambda r: setattr(r, "lines", r.lines[:2]), "FAIL", "APPLY")
    variant("apply_moved_a_neighbouring_key", each(("APPLY", "NAV", "REDO"), lambda c: tset(c)["channels"][
        u"Tail5_L_o"]["keys"][0][0].__setitem__(0, 5)), "FAIL", "APPLY")
    # POSTURE
    variant("posture_not_reproduced", each(("APPLY", "NAV", "REDO"), lambda c: tset(c)["bones"][u"bip_spine"].__setitem__(
        3, TURN)), "FAIL", "POSTURE")
    variant("placement_moved", each(("APPLY", "NAV", "REDO"), lambda c: tset(c)["handles"][u"rig_root"].__setitem__(
        2, [510.0, 0.0, 0.0])), "FAIL", "POSTURE")
    variant("direct_bone_offset_changed", each(("APPLY", "NAV", "REDO"), lambda c: tset(c)["bones"][
        u"Tail5_L"].__setitem__(0, [1.5, 0.0, 0.0])), "FAIL", "POSTURE")
    # HISTORY
    variant("navigation_lost_the_pose", caps("NAV", lambda c: tset(c)["bones"][u"bip_spine"].__setitem__(3, TURN)),
            "FAIL", "HISTORY")
    variant("undo_not_restored", caps("UNDO", lambda c: tset(c)["channels"][u"rig_spine_0_o"].update(sha256=u"x")),
            "FAIL", "HISTORY")
    variant("redo_not_restored", caps("REDO", lambda c: tset(c)["channels"][u"rig_spine_0_o"].update(sha256=u"x")),
            "FAIL", "HISTORY")
    variant("undo_without_redo_entry", caps("UNDO", lambda c: c["session"]["undo"].update(can_redo=False,
                                                                                         redo_desc=u"")),
            "FAIL", "HISTORY")
    # LEAVES
    variant("leaf_scale_changed", side("REDO", "target", lambda s: s["scales"].update(
        {u"Tail6_L": {u"status": u"READ", u"value": 1.25}})), "FAIL", "LEAVES")
    variant("leaf_declaration_changed", side("NAV", "target", lambda s: s["declared"][2].update(flags=0x505)),
            "FAIL", "LEAVES")
    variant("leaf_not_admitted_after_apply", caps("UNDO", lambda c: tset(c)["admission"]["bone_classes"].update(
        {u"ear3_R": u"fk"})), "FAIL", "LEAVES")
    variant("source_leaf_key_changed_in_process_b", caps("NAV", lambda c: tset(c, "source")["channels"][
        u"ear3_R_o"].update(sha256=u"x")), "FAIL", "LEAVES")
    variant("target_leaf_key_changed_across_the_restart", each(("BASE", "APPLY", "NAV", "UNDO", "REDO"), lambda c: tset(
        c)["channels"][u"ear3_R_o"]["keys"][0][0].__setitem__(1, [9.0, 9.0, 9.0])), "INCOMPLETE", "PREP")
    variant("peer_leaf_key_changed", caps("APPLY", lambda c: tset(c, "peer")["channels"][u"Tail6_R_o"].update(
        sha256=u"x")), "FAIL", "LEAVES")
    # PEER
    variant("source_changed_at_apply", caps("APPLY", lambda c: tset(c, "source")["channels"][
        u"rig_spine_0_o"].update(sha256=u"x")), "FAIL", "PEER")
    variant("peer_body_moved", caps("NAV", lambda c: tset(c, "peer")["bones"][u"bip_spine"].__setitem__(
        2, [0.0, 320.0, 0.0])), "FAIL", "PEER")
    variant("peer_tips_moving_only_is_a_pass", each(STATE, lambda c: tset(c, "peer")["bones"][u"ear3_L"].__setitem__(
        2, [float(c["pid"]), 7.0, 1.0])), "AUTOMATED PASS")
    # EVIDENCE: INCOMPLETE
    variant("missing_sidecar", lambda r: r.sides.pop("NAV"), "INCOMPLETE", "EVIDENCE")
    variant("sidecar_from_another_process", lambda r: r.sides["APPLY"].update(pid=1), "INCOMPLETE", "EVIDENCE")
    variant("sidecar_header_unreadable", side("BASE", "target", lambda s: s.update(status="UNREADABLE")),
            "INCOMPLETE", "EVIDENCE")
    variant("missing_capture", lambda r: r.caps.pop("REDO"), "INCOMPLETE", "EVIDENCE")
    variant("one_process_only", each(("BASE", "APPLY", "NAV", "UNDO", "REDO"), lambda c: c.update(pid=4001)),
            "INCOMPLETE", "EVIDENCE")
    variant("another_session", caps("NAV", lambda c: c["session"].update(document=u"c:/other.dmx")), "INCOMPLETE",
            "EVIDENCE")
    variant("playhead_moved", caps("UNDO", lambda c: c["session"].update(head_seconds=0.25)), "INCOMPLETE",
            "EVIDENCE")
    variant("session_copy_not_saved", lambda r: setattr(r, "session", b"r2 fixture"), "INCOMPLETE", "EVIDENCE")
    variant("spare_saved", lambda r: setattr(r, "spare", b"saved"), "INCOMPLETE", "EVIDENCE")
    variant("wrong_build", lambda r: r.ids.update(qualification_cpm_sha256="0" * 64), "INCOMPLETE", "EVIDENCE")
    variant("restore_incomplete", lambda r: setattr(r, "restored", False), "INCOMPLETE", "EVIDENCE")
    variant("library_changed_by_another_file", lambda r: r.extra.append(
        {"status": "added", "path": u"Characters/x/Poses/y.json", "sha256": "1" * 64}), "INCOMPLETE", "EVIDENCE")
    variant("unverified_result_in_the_log", lambda r: r.lines.append("x | PROD_POSE_BODY-P7-unverified {}"),
            "INCOMPLETE", "EVIDENCE")


# --- 3. the template ------------------------------------------------------------------------------------------------

def section_template(root):
    t = json.loads(read(os.path.join(KIT, "s2t.template.json")).decode("utf-8"))
    pins = t["pins"]
    check("template.format", t["format"] == "F01-S2T-config-v1")
    files = {"wrapper_sha256": WRAPPER, "capture_sha256": FOX_CAPTURE,
             "analyzer_sha256": os.path.join(KIT, "tools", "s2t_analyze.py"),
             "procedure_sha256": os.path.join(KIT, "PROCEDURE.md")}
    check("template.kit_pins_are_the_kit_files", all(sha_bytes(read(p)) == pins[k] for k, p in files.items()),
          dict((k, sha_bytes(read(p))) for k, p in files.items()))
    cpm = read(os.path.join(REPO, "cpm", "app", "SFM_Character_Preset_Manager.py"))
    prod, qual = b'PROD_POSE_REGISTRY_MODE = u"production"', b'PROD_POSE_REGISTRY_MODE = u"qualification"'
    check("template.candidate_is_the_stage2_cpm", sha_bytes(cpm) == pins["candidate_cpm_sha256"] ==
          "001377f9704ffd4e52503330feea2d4dcf271dd9541a6889d109f6801985de70")
    check("template.qualification_build_is_the_one_line_derivation", cpm.count(prod) == 1 and sha_bytes(
        cpm.replace(prod, qual)) == pins["qualification_cpm_sha256"] ==
        "7d3ed720f77e9abc0a176a2d8e499c2145d016f866b439e7f7eccf07922d1813")
    fox_t = json.loads(read(os.path.join(KIT, "..", "f01_stage1_fox", "s1f.template.json")).decode("utf-8"))
    fox = fox_t["pins"]
    check("template.shared_pins_as_in_the_fox_kit", all(pins[k] == fox[k] for k in (
        "profile_sha256", "body_profile_sha256", "published_cpm_sha256", "r2_fixture_sha256", "destination_sha256",
        "observer_sha256", "legacy_pose_sha256", "capture_sha256")))
    check("template.r2_fixture_is_the_original_fixture", t["paths"]["R2_FIXTURE"] == fox_t["paths"]["R2_FIXTURE"])
    if sys.version_info[0] < 3:
        return
    import s2t_tool
    c = copy.deepcopy(t)
    c["paths"] = dict((k, v.replace("<RUN_DIR>", root).replace("<REPO>", REPO).replace("<", "").replace(">", ""))
                      for k, v in t["paths"].items())
    path = os.path.join(root, "s2t.json")
    write_json(path, c)
    loaded = s2t_tool.S.load(path)
    check("tool.loads_the_filled_template_and_pins_its_files", [s2t_tool.T.sha(p) == loaded["pins"][k] for p, k in
                                                               s2t_tool.pinned_kit_files(loaded)] == [True] * 4)
    check("tool.reused_tools_take_this_kits_identity", s2t_tool.S.FORMAT == "F01-S2T-config-v1" and
          s2t_tool.S.SESSIONS == ("S2T_SESSION.dmx",) and s2t_tool.S.DESTINATION == "S2T_SPARE.dmx" and
          s2t_tool.K.comparator().endswith("s2t_analyze.py"))


def main():
    print("F-01 Stage 2 native Tails qualification kit (Python %s)" % sys.version.split()[0])
    root = tempfile.mkdtemp(prefix="s2t_kit_")
    try:
        for fn in (section_wrapper, section_sidecar_on_the_candidate, section_analyzer, section_template):
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
