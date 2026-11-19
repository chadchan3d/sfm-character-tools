# -*- coding: utf-8 -*-
"""F-01 Stage 1 Fox kit: offline tests of the capture and the analyzer.

The capture script runs against the real Stage 1 CPM (the stage E harness of cpm/convergence/tests: the extracted
blocks and the fake scene built from fixtures/f01_body/fox_shot15.json). A complete two-process run 2 is then
simulated with CPM's real Save, Apply, Undo, Redo, no-op and injected-fault Abort on fake scenes (Fox S, a renamed and
differently posed Fox D, the original Fox as the untouched peer, and a Tails-like character with a control-less bone
whose Save New probe refuses), and analyzed; then each gate is broken once.
This shows the kit's own logic, never SFM's behaviour.

Usage: python -I test_s1f.py   (or <SFM python 2.7.5> -E -B test_s1f.py)
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
import types

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(KIT, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "cpm", "convergence", "tests"))
sys.path.insert(0, os.path.join(KIT, "tools"))
CAPTURE = os.path.join(KIT, "observer", "F01_S1F_Capture.py")
RESULTS = []
QUAL_SHA = "q" * 64
CAND_SHA = "c" * 64


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


_saved = sys.stdout
sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
try:
    import test_cpm_app_canonical_route as route  # noqa: E402
    import test_cpm_app_f01_structural_rig as T  # noqa: E402
    B, FB = T.B, T.FB
    NS = B.live_namespace(route.AppSource(route.APP_PATH))
    REG, _ = B.registries(NS)
    FX = T.fixture()
finally:
    sys.stdout = _saved
del B.RESULTS[:]


def load_capture():
    g = {"__name__": "s1f_capture_under_test", "__file__": CAPTURE}
    with open(CAPTURE, "rb") as f:
        exec(compile(f.read(), CAPTURE, "exec"), g)
    return g


CAP = load_capture()


def cpm_module():
    m = types.ModuleType("chadchan3d_cpm_app")
    m.__dict__.update(NS)
    m.get_game_model = lambda animset: animset.attrs.get("gameModel")
    m.__chadchan3d_cpm_build_sha256__ = QUAL_SHA
    m.PROD_POSE_REGISTRY_MODE = u"qualification"
    return m


CPM = cpm_module()


def make(name, prepare=None, posed=False, rig=None):
    w = FB.World(FX)
    w.animset.name = name
    if rig:
        w.rig.name = rig
    if posed:
        T.pose_differently(w)
    if prepare is not None:
        prepare(w)
        w.evaluate()
    return w


def jiggle(w):
    w.channels[u"ValveBiped.Bip01_R_Finger42_o"].set("fromElement", None)


def capture_set(w, keys):
    T.use(NS, w)
    return CAP["s1f_set"](CPM, w.shot, w.animset, keys)


class Run(object):
    """A simulated run: three fake scenes, CPM's real operations, captures composed per step."""

    def __init__(self, root):
        self.root = root
        self.q = os.path.join(root, "Q")
        for d in ("staged", "sessions", "observations", os.path.join("evidence", "logs")):
            os.makedirs(os.path.join(self.q, d))
        self.src = make(u"foxmccouldwm2", rig=u"rig_biped_foxmccouldwm2")
        self.dst = make(u"foxmccouldwm3", posed=True, rig=u"rig_biped_foxmccouldwm3")
        self.peer = make(u"foxmccouldwm1")
        self.tails = make(u"milestailsprower1", jiggle)
        self.caps, self.pid, self.selected = {}, 1000, None
        self.lib = T.library(root, u"lib")

    def capture(self, step):
        data = {"format": CAP["FORMAT"], "step": step, "pid": self.pid, "cpm_build_sha256": QUAL_SHA,
                "registry_mode": u"qualification", "qualification_fault": list(NS["PROD_POSE_QUAL_FAULT"]),
                "names": {"source": u"foxmccouldwm2", "target": u"foxmccouldwm3", "peer": u"foxmccouldwm1"},
                "errors": [], "sets": {}}
        for role, w in (("source", self.src), ("target", self.dst), ("peer", self.peer)):
            data["sets"][role] = capture_set(w, role == "target")
        dm = self.dst.dm
        data["session"] = {"undo": {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()),
                                    "undo_desc": dm.GetUndoDesc(),
                                    # SFM names the Redo entry with CPM's own "Redo <label>" (StartUndo's second
                                    # argument; natively shown in H1); the fake keeps the label only.
                                    "redo_desc": (u"Redo " + dm.GetRedoDesc()) if dm.GetRedoDesc() else u""},
                           "head_seconds": 0.2083, "timeline_mode": 2, "shot": u"shot15",
                           "document": os.path.join(self.q, "sessions", "S1_SESSION.dmx")}
        data["selected_pose"] = self.selected
        self.caps[step] = data
        T.use(NS, self.dst)

    def apply(self):
        T.use(NS, self.dst)
        auth = T.authorize(NS, REG, u"Apply Pose", self.item)
        result = NS["prod_body_apply"](T.IDENTITY, auth, self.item, REG)
        if result.get(u"phase") == u"verification-pending":
            NS["prod_pose_deferred_verify"](dict(result[u"pending"], authorization=auth))
        return result

    def go(self):
        del NS["LOG"][:]
        self.capture("PREP")
        T.use(NS, self.src)
        NS["prod_body_rig_probe"](T.ctx(NS), T.IDENTITY, REG, u"qualification")   # the Save dialog's admission
        pose, saved, self.item = T.save(NS, REG, self.lib, u"S1 Fox")
        r = saved[u"record"]
        self.record = r
        self.selected = {"name": r[u"name"], "preset_id": r[u"preset_id"], "version": 2,
                         "adapter": r[u"pose"][u"adapter"], "regions": [u"full_body"], "model": r[u"model_ref"],
                         "exclusions": [], "written": 0}
        self.capture("SAVED")
        T.use(NS, self.tails)                               # Tails' Save New: the structural probe refuses
        check("sim.tails_probe_refuses", NS["prod_body_rig_probe"](T.ctx(NS), T.IDENTITY, REG, u"qualification") is
              None)
        self.pid += 1                                       # the restart: SFM's session load renormalizes every
        for w in (self.src, self.dst, self.peer, self.tails):  # stored quaternion (run 2's measured function)
            T.reload_world(w)
        self.capture("BASE")
        self.apply()
        self.capture("APPLY")
        self.capture("NAV")
        self.dst.dm.Undo()
        self.capture("UNDO")
        self.dst.dm.Redo()
        self.capture("REDO")
        self.apply()
        self.capture("NOOP")
        self.dst.dm.Undo()
        self.capture("UNDO2")
        NS["PROD_POSE_QUAL_FAULT"][0] = u"after-writes"
        self.mode_apply()
        self.capture("ABORT")
        self.log = list(NS["LOG"])

    def mode_apply(self):
        T.use(NS, self.dst)
        auth = T.authorize(NS, REG, u"Apply Pose", self.item)
        auth = dict(auth, mode=u"qualification")
        NS["prod_body_apply"](T.IDENTITY, auth, self.item, REG)

    def write(self, mutate=None):
        caps = copy.deepcopy(self.caps)
        files = {"log": list(self.log), "record": copy.deepcopy(self.record), "session": b"saved session",
                 "spare": b"spare", "restore": {"restored": True}, "cleanup": None}
        if mutate is not None:
            mutate(caps, files)
        q = tempfile.mkdtemp(dir=self.root)
        for d in ("staged", "sessions", "observations", os.path.join("evidence", "logs")):
            os.makedirs(os.path.join(q, d))
        dump = lambda path, obj: io.open(path, "wb").write(json.dumps(obj, indent=1, sort_keys=True,  # noqa: E731
                                                                      default=repr).encode("utf-8"))
        dump(os.path.join(q, "staged", "IDENTITIES.json"), {"qualification_cpm_sha256": QUAL_SHA,
                                                            "candidate_cpm_sha256": CAND_SHA})
        for step, data in caps.items():
            dump(os.path.join(q, "observations", "S1F-%s.json" % step), data)
        io.open(os.path.join(q, "sessions", "S1_SESSION.dmx"), "wb").write(files["session"])
        io.open(os.path.join(q, "sessions", "S1_SPARE.dmx"), "wb").write(files["spare"])
        io.open(os.path.join(q, "evidence", "logs", "cpm.log"), "wb").write(
            u"\n".join(files["log"]).encode("utf-8"))
        rec = files["record"]
        diffs = []
        if rec is not None:
            rel = u"Characters/foxmccouldwm--abc/Poses/S1 Fox--%s.json" % rec[u"preset_id"][:12]
            path = os.path.join(q, "evidence", "library_after", *rel.split("/"))
            os.makedirs(os.path.dirname(path))
            io.open(path, "wb").write(json.dumps(rec).encode("utf-8"))
            diffs.append({"path": rel, "status": "added", "sha256": hashlib.sha256(
                json.dumps(rec).encode("utf-8")).hexdigest()})
            diffs.append({"path": u"Characters/foxmccouldwm--abc/character.json", "status": "added"})
        cleanup = files["cleanup"] or {"differences_kept_in_evidence": diffs, "files_equal_pre": True,
                                       "folders_equal_pre": True}
        dump(os.path.join(q, "evidence", "library_cleanup.json"), cleanup)
        dump(os.path.join(q, "evidence", "restore.json"), files["restore"])
        return q


def analyze(q):
    import s1f_analyze as A
    c = {"paths": {"Q": q}, "pins": {"qualification_cpm_sha256": QUAL_SHA, "candidate_cpm_sha256": CAND_SHA,
                                     "r2_fixture_sha256": hashlib.sha256(b"r2 fixture").hexdigest(),
                                     "destination_sha256": hashlib.sha256(b"spare").hexdigest()}}
    saved = sys.stdout
    sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
    try:
        R = A.Report(c)
        refused = A.evaluate(R)
        v, gates = A.verdict(R.checks, refused)
    finally:
        sys.stdout = saved
    return v, gates, [x for x in R.checks if not x["pass"]], R.info


def section_capture(root):
    w = make(u"foxmccouldwm1")
    T.use(NS, w)
    s = capture_set(w, True)
    adm = s["admission"]
    check("capture.records_the_structural_admission", adm.get("placement") == u"rig_root" and
          adm.get("handles") == 22 and adm.get("constraints") == 34 and len(adm.get("written") or []) == 214 and
          adm.get("classes") == {u"constrained": 22, u"fk": 90}, adm.get("error") or sorted(adm))
    check("capture.records_channels_bones_handles_and_target_keys", len(s["channels"]) == len(w.channels) and
          len(s["bones"]) == 112 and len(s["handles"]) == 22 and all("keys" in c for c in s["channels"].values())
          and len(s["model_state"]) == 4)
    peer = capture_set(make(u"milestailsprower1", jiggle), False)
    check("capture.records_a_refusal_with_its_code", peer["admission"].get("code") == u"structure-unsupported" and
          all("keys" in c and "frame" in c for c in peer["channels"].values()), peer["admission"])
    renamed = capture_set(make(u"foxmccouldwm2", rig=u"rig_biped_foxmccouldwm2"), False)
    check("capture.description_digest_ignores_the_rig_name", renamed["admission"]["description_sha256"] ==
          adm["description_sha256"] and renamed["admission"]["rig_name"] != adm["rig_name"])
    check("capture.content_digest_is_handle_free", CAP["s1f_strip"]({u"handle": 1, u"a": [{u"handle": 2, u"b": 3}]})
          == {u"a": [{u"b": 3}]})
    check("capture.is_read_only", not B.scene_writes(w) and not w.dm.calls)
    # The script entry point: refusals, exclusive create, the file it writes.
    g = dict(CAP)
    sfm, vs = w.modules()
    sys.modules["sfmApp"], sys.modules["vs"] = sfm, vs
    sys.modules["chadchan3d_cpm_app"] = CPM
    q = tempfile.mkdtemp(dir=root)
    os.makedirs(os.path.join(q, "observations"))
    try:
        g.update({"S1F_DIR": q, "S1F_STEP": "PREP", "S1F_SOURCE": u"foxmccouldwm1", "S1F_TARGET": u"foxmccouldwm1",
                  "S1F_PEER": u"x"})
        try:
            CAP["s1f_capture"](g)
            ok = False
        except RuntimeError:
            ok = not os.listdir(os.path.join(q, "observations"))
        check("capture.refuses_names_that_are_not_three_different_sets", ok)
        g.update({"S1F_TARGET": u"fox_b", "S1F_PEER": u"tails"})
        T.use(NS, w)
        saved = sys.stdout
        sys.stdout = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
        try:
            data = CAP["s1f_capture"](g)
        finally:
            sys.stdout = saved
        path = os.path.join(q, "observations", "S1F-PREP.json")
        check("capture.writes_its_one_file_and_records_missing_sets", os.path.isfile(path) and
              sorted(data["errors"]) == sorted(["target: 0 animation sets named u'fox_b'" if sys.version_info[0] == 2
                                                else "target: 0 animation sets named 'fox_b'",
                                                "peer: 0 animation sets named u'tails'" if sys.version_info[0] == 2
                                                else "peer: 0 animation sets named 'tails'"]) and
              data["sets"]["source"]["admission"].get("placement") == u"rig_root" and
              data["registry_mode"] == u"qualification", data["errors"])
        try:
            CAP["s1f_capture"](g)
            ok = False
        except RuntimeError:
            ok = True
        check("capture.each_step_is_captured_once", ok)
    finally:
        for m in ("sfmApp", "vs", "chadchan3d_cpm_app"):
            sys.modules.pop(m, None)


def section_verdicts(root):
    run = Run(root)
    run.go()
    v, gates, failed, info = analyze(run.write())
    check("verdict.simulated_complete_run_is_an_automated_pass", v == "AUTOMATED PASS", (v, failed[:6]))
    check("verdict.posture_measured_independently", info.get("posture", {}).get("bones") == 112 and
          info["posture"]["angle_degrees"] < 0.01 and info["posture"]["by_class"]["constrained"]["bones"] == 22,
          info.get("posture"))
    check("verdict.abort_after_the_committed_write_count", (info.get("abort") or {}).get("committed_writes") ==
          ((info.get("abort") or {}).get("failure") or {}).get("written"), info.get("abort"))

    def variant(label, mutate, want, gate=None):
        v, gates, failed, _ = analyze(run.write(mutate))
        check("verdict.%s" % label, v == want and (gate is None or gates.get(gate) is False),
              (v, [x["id"] for x in failed][:6]))

    def set_bones(caps, step, role, fn):
        for b in caps[step]["sets"][role]["bones"].values():
            fn(b)

    def tilt(b):
        b[3] = list(FB.qnorm(FB.qmul([0.0, 0.0, 0.05, 1.0], b[3])))
    variant("posture_off_by_a_few_degrees_fails", lambda c, f: set_bones(c, "APPLY", "target", tilt), "FAIL",
            "POSTURE")

    def moved_placement(c, f):
        c["APPLY"]["sets"]["target"]["handles"]["rig_root"][2][0] += 5.0
    variant("moved_placement_fails", moved_placement, "FAIL", "POSTURE")

    def extra_channel(c, f):
        n = u"rig_root_p"
        c["APPLY"]["sets"]["target"]["channels"][n]["sha256"] = "x" * 64
    variant("a_preserved_channel_written_fails", extra_channel, "FAIL", "APPLY")

    def neighbour(c, f):
        name = [n for n, ch in c["APPLY"]["sets"]["target"]["channels"].items()
                if ch["sha256"] != c["BASE"]["sets"]["target"]["channels"][n]["sha256"]][0]
        c["APPLY"]["sets"]["target"]["channels"][name]["keys"] = [[[-99999, [0.0, 0.0, 0.0, 1.0]]]]
    variant("a_neighbouring_key_changed_fails", neighbour, "FAIL", "APPLY")

    def source_changed(c, f):
        n = sorted(c["APPLY"]["sets"]["source"]["channels"])[0]
        c["APPLY"]["sets"]["source"]["channels"][n]["sha256"] = "y" * 64
    variant("source_fox_changed_fails", source_changed, "FAIL", "PEER")

    def undo_partial(c, f):
        n = sorted(c["UNDO"]["sets"]["target"]["channels"])[0]
        c["UNDO"]["sets"]["target"]["channels"][n]["sha256"] = "z" * 64
    variant("incomplete_undo_fails", undo_partial, "FAIL", "HISTORY")

    def nav_moved(c, f):
        c["NAV"]["session"]["head_seconds"] = 0.25
    variant("playhead_not_returned_is_incomplete", nav_moved, "INCOMPLETE", "EVIDENCE")

    def abort_left(c, f):
        n = sorted(c["ABORT"]["sets"]["target"]["channels"])[0]
        c["ABORT"]["sets"]["target"]["channels"][n]["sha256"] = "w" * 64
    variant("abort_leaving_a_change_fails", abort_left, "FAIL", "ABORT")
    variant("abort_without_the_injected_failure_fails", lambda c, f: f.__setitem__("log", [
        l for l in f["log"] if "P3-P6-failure" not in l]), "FAIL", "ABORT")
    variant("unverified_p7_is_incomplete", lambda c, f: f["log"].append(u"PROD_POSE_BODY-P7-unverified {}"),
            "INCOMPLETE", "EVIDENCE")

    def same_process(c, f):
        for s in c:
            c[s]["pid"] = 1000
    variant("no_restart_is_incomplete", same_process, "INCOMPLETE", "EVIDENCE")

    def prep_not_restored(c, f):
        n = sorted(c["BASE"]["sets"]["target"]["channels"])[0]
        c["BASE"]["sets"]["target"]["channels"][n]["frame"] = "v" * 64
    variant("saved_session_not_reopened_as_prepared_is_incomplete", prep_not_restored, "INCOMPLETE", "PREP")

    def same_pose(c, f):
        c["PREP"]["sets"]["target"]["bones"] = copy.deepcopy(c["PREP"]["sets"]["source"]["bones"])
        c["PREP"]["sets"]["target"]["handles"] = copy.deepcopy(c["PREP"]["sets"]["source"]["handles"])
    variant("fox_b_not_visibly_different_is_incomplete", same_pose, "INCOMPLETE", "PREP")
    variant("unsaved_session_is_incomplete", lambda c, f: f.__setitem__("session", b"r2 fixture"), "INCOMPLETE",
            "EVIDENCE")
    variant("restore_failure_is_incomplete", lambda c, f: f.__setitem__("restore", {"restored": False}),
            "INCOMPLETE", "EVIDENCE")

    def refused(c, f):
        f["record"] = None
        for s in list(c):
            if s not in ("PREP", "SAVED"):
                del c[s]
    variant("refused_fox_save_is_refused", refused, "REFUSED")

    def registry_record(c, f):
        f["record"][u"pose"].pop(u"adapter")
    variant("a_record_without_the_adapter_fails", registry_record, "FAIL", "SAVE")

    variant("tails_not_refused_fails", lambda c, f: f.__setitem__("log", [
        l for l in f["log"] if "BODY-RIG-unavailable" not in l]), "FAIL", "TAILS")

    # Astra's kit ruling: BASE equals SFM's measured load renormalization of PREP exactly, nothing else.
    import s1f_analyze as A0
    reload_info = info.get("reload_renormalized_keys") or {}
    check("sim.restart_renormalized_keys_of_every_set", sorted(reload_info) == sorted(A0.ROLES) and all(
        n > 0 for n in reload_info.values()), reload_info)
    check("sim.descriptor_digests_reported_for_information", (info.get("descriptor_sha256") or {}).get(
        "BASE", {}).get("target") == (info.get("descriptor_sha256") or {}).get("BASE", {}).get("source") is not None,
        info.get("descriptor_sha256"))

    def quat_keys(c, step, role, changed_by_load=None):
        for n, ch in sorted(c[step]["sets"][role]["channels"].items()):
            for li, layer in enumerate(ch["keys"]):
                for ki, k in enumerate(layer):
                    if isinstance(k[1], list) and len(k[1]) == 4:
                        prep = c["SAVED"]["sets"][role]["channels"][n]["keys"][li][ki][1]
                        if changed_by_load is None or (A0.sfm_reload(prep) != prep) == changed_by_load:
                            return n, li, ki, k
        raise AssertionError("no quaternion key")

    def base_key(fn, role="peer", changed_by_load=None):
        def mutate(c, f):
            fn(c, quat_keys(c, "BASE", role, changed_by_load))
        return mutate

    def step_off(c, nk):
        nk[3][1][0] = nk[3][1][0] + 2.0 ** -23

    def not_reloaded(c, nk):
        n, li, ki, k = nk
        k[1] = list(c["SAVED"]["sets"]["peer"]["channels"][n]["keys"][li][ki][1])

    def sign_flip(c, nk):
        nk[3][1] = [-x for x in nk[3][1]]
    variant("a_key_one_step_off_the_load_function_is_incomplete", base_key(step_off), "INCOMPLETE", "PREP")
    variant("a_key_one_step_off_on_the_destination_is_incomplete", base_key(step_off, "target"), "INCOMPLETE",
            "PREP")
    variant("a_key_the_load_would_change_left_unchanged_is_incomplete", base_key(not_reloaded, changed_by_load=True),
            "INCOMPLETE", "PREP")
    variant("a_sign_flipped_key_is_not_the_loader_transformation", base_key(sign_flip), "INCOMPLETE", "PREP")

    def key_time(c, f):
        quat_keys(c, "BASE", "peer")[3][0] += 1
    variant("a_changed_key_time_is_incomplete", key_time, "INCOMPLETE", "PREP")

    def key_count(c, f):
        n, li, ki, k = quat_keys(c, "BASE", "peer")
        c["BASE"]["sets"]["peer"]["channels"][n]["keys"][li].append(list(k))
    variant("a_changed_key_count_is_incomplete", key_count, "INCOMPLETE", "PREP")

    def vector_value(c, f):
        for n, ch in sorted(c["BASE"]["sets"]["peer"]["channels"].items()):
            for layer in ch["keys"]:
                for k in layer:
                    if isinstance(k[1], list) and len(k[1]) == 3:
                        k[1][0] += 2.0 ** -23
                        return
        raise AssertionError("no vector key")
    variant("a_changed_non_quaternion_value_is_incomplete", vector_value, "INCOMPLETE", "PREP")

    def missing(c, f):
        for step in ("NAV", "UNDO", "REDO", "NOOP", "UNDO2", "ABORT"):
            del c[step]
    v, gates, failed, _ = analyze(run.write(missing))
    check("verdict.missing_captures_are_not_evaluated_never_pass", v == "INCOMPLETE" and gates["EVIDENCE"] is False
          and all(gates[g] is None for g in ("PREP", "SAVE", "APPLY", "POSTURE", "HISTORY", "ABORT", "PEER",
                                             "TAILS")), gates)
    import s1f_analyze as A
    check("verdict.markdown_says_not_evaluated", "HISTORY NOT EVALUATED" in A.markdown({
        "verdict": v, "gates": gates, "identities": {}, "checks": [], "info": {}}))

    def wrong_build(c, f):
        c["APPLY"]["cpm_build_sha256"] = "p" * 64
    variant("another_build_is_incomplete", wrong_build, "INCOMPLETE", "EVIDENCE")


RUN2_KEYS = os.path.join(HERE, "run2_reload_keys.json")
RUN2_KEYS_SHA256 = "7d2fea51c52ca006597a832bd8ad5399fb4b7aa4b1678a70662b94fa07f9bb9d"


def section_run2_reload(root):
    """Run 2's real save/reopen transition (SAVED and BASE of the three sets): every one of the 618 quaternion keys is
    exactly the measured load function of its saved value; an unrelated alteration is not."""
    import s1f_analyze as A
    raw = io.open(RUN2_KEYS, "rb").read()
    check("run2.reload_keys_match_their_pin", hashlib.sha256(raw).hexdigest() == RUN2_KEYS_SHA256)
    data = json.loads(raw.decode("utf-8"))
    total = changed = agree = 0
    for role in A.ROLES:
        for n, ch in data["SAVED"]["sets"][role]["channels"].items():
            for li, layer in enumerate(ch["keys"]):
                for ki, k in enumerate(layer):
                    if isinstance(k[1], list) and len(k[1]) == 4:
                        b = data["BASE"]["sets"][role]["channels"][n]["keys"][li][ki][1]
                        total += 1
                        changed += b != k[1]
                        agree += A.sfm_reload(k[1]) == T.sfm_reload(k[1]) == b
    check("run2.618_quaternion_keys_165_changed_all_exactly_the_load_function", (total, changed, agree) == (
        618, 165, 618), (total, changed, agree))
    results = dict((r, A.reopened_as_prepared(data["SAVED"], data["BASE"], r)) for r in A.ROLES)
    check("run2.analyzer_accepts_the_observed_reopen", all(v[0] for v in results.values()) and sum(
        v[1] for v in results.values()) == 165, dict((r, v[2]) for r, v in results.items()))
    for label, where in (("quaternion", 4), ("vector", 3)):
        bad = copy.deepcopy(data)
        done = []
        for n, ch in sorted(bad["BASE"]["sets"]["target"]["channels"].items()):
            for layer in ch["keys"]:
                for k in layer:
                    if not done and isinstance(k[1], list) and len(k[1]) == where:
                        k[1][1] = k[1][1] + 2.0 ** -20
                        done.append(n)
        ok = A.reopened_as_prepared(bad["SAVED"], bad["BASE"], "target")
        check("run2.an_unrelated_%s_key_alteration_is_rejected" % label, done and not ok[0] and ok[2] == done,
              (done, ok))
    old = copy.deepcopy(data)
    for role in A.ROLES:
        for n, ch in old["BASE"]["sets"][role]["channels"].items():
            ch["keys"] = copy.deepcopy(old["SAVED"]["sets"][role]["channels"][n]["keys"])
    check("run2.an_unrenormalized_reopen_is_rejected", not all(
        A.reopened_as_prepared(old["SAVED"], old["BASE"], r)[0] for r in A.ROLES))


def main():
    root = tempfile.mkdtemp(prefix="s1f_kit_")
    try:
        for fn in (section_capture, section_verdicts, section_run2_reload):
            try:
                fn(root)
            except Exception:
                import traceback
                check("section.%s.completed" % fn.__name__, False, traceback.format_exc())
    finally:
        shutil.rmtree(root, True)
    failed = [r for r in RESULTS if not r[1]]
    print("RESULT: %d/%d %s (%s)" % (len(RESULTS) - len(failed), len(RESULTS),
                                     "ALL PASS" if not failed else "SOME FAILED", sys.version.split()[0]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
