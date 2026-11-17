# -*- coding: utf-8 -*-
"""F-01 OT1 kit: offline tests of the template, the one-line build derivation and the verdict analyzer (Python 3,
-I). The analyzer runs on synthetic run folders built here (a passing trial and one mutation per gate check); nothing
here shows anything about SFM.

usage: python -I test_ot1.py
"""
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
REPO = os.path.dirname(os.path.dirname(KIT))
sys.path.insert(0, os.path.join(KIT, "tools"))
import ot1_tool  # noqa: E402
import ot1_analyze as A  # noqa: E402

RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def sha_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


TEMPLATE = os.path.join(KIT, "ot1.template.json")


def section_template():
    with open(TEMPLATE, "rb") as f:
        t = json.loads(f.read().decode("utf-8"))
    check("T1 template format is this kit's", t.get("format") == ot1_tool.FORMAT)
    check("T1 no placeholder in any pin", not any("<" in v for v in t["pins"].values()))
    import re
    personal = [v for v in t["paths"].values()
                if re.search(r"[A-Za-z]:[\/]", v) and not v.startswith("C:/Users/Public/")]
    check("T1 no personal or machine-specific path in the template (placeholders, %USERPROFILE% or Public only)",
          not personal, personal)
    cand = os.path.join(REPO, "cpm", "app", "SFM_Character_Preset_Manager.py")
    check("T2 candidate pin = the working candidate", t["pins"]["candidate_cpm_sha256"] == sha_file(cand))
    for key, rel in (("profile_sha256", "cpm/pose_profiles/cpm_pose_profiles_v1.json"),
                     ("body_profile_sha256", "cpm/pose_profiles/cpm_body_profiles_v1.json"),
                     ("ot1_observer_sha256", "real_sfm_qualification/f01_ot1_ordering_trial/observer/F01_OT1_Observe.py"),
                     ("q1_observer_sha256", "real_sfm_qualification/f01_q1_ps2_diagnostic/observer/F01_Q1_Observe.py"),
                     ("observer_sha256", "real_sfm_qualification/f01_full_body_s0/observer/F01_S0_Survey.py")):
        check("T2 pin %s = %s" % (key, rel), t["pins"][key] == sha_file(os.path.join(REPO, *rel.split("/"))))
    with open(os.path.join(KIT, "..", "f01_q1_ps2_diagnostic", "q1.template.json"), "rb") as f:
        q1 = json.loads(f.read().decode("utf-8"))
    for key in ("published_cpm_sha256", "r2_fixture_sha256", "destination_sha256", "body_preset_sha256"):
        check("T3 pin %s equals the Q1 kit's" % key, t["pins"][key] == q1["pins"][key])
    with open(os.path.join(KIT, "..", "f01_ui_acceptance", "ua.template.json"), "rb") as f:
        ua = json.loads(f.read().decode("utf-8"))
    check("T3 legacy pose pin and path pattern equal the UA-1/K2 kits' (Q1-D1 not repeated)",
          t["pins"]["legacy_pose_sha256"] == ua["pins"]["legacy_pose_sha256"]
          and t["paths"]["LEGACY_POSE"] == ua["paths"]["LEGACY_POSE"])
    with open(os.path.join(KIT, "observer", "F01_OT1_Observe.py"), "rb") as f:
        obs = f.read().decode("ascii")
    check("T4 no vsUtils pin remains (Astra DC2: the observer does not import vsUtils)", "vsutils_sha256" not in t["pins"])
    check("T4 the OT1 observer pins the same Q1 observer", 'Q1_OBSERVER_SHA256 = "%s"' % t["pins"]["q1_observer_sha256"]
          in obs)

    # The one-line derivation, exactly as K2's build performs it.
    S = ot1_tool.S
    with open(cand, "rb") as f:
        raw = f.read()
    qual = raw.replace(S.MODE_PRODUCTION, S.MODE_QUALIFICATION)
    a, b = raw.split(b"\n"), qual.split(b"\n")
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    check("T5 derivation: exactly one line differs (the registry mode)", raw.count(S.MODE_PRODUCTION) == 1
          and len(diff) == 1 and b[diff[0]].strip() == S.MODE_QUALIFICATION.strip(), diff)
    check("T5 derived qualification CPM = the pinned qualification build",
          hashlib.sha256(qual).hexdigest() == t["pins"]["qualification_cpm_sha256"], hashlib.sha256(qual).hexdigest())
    for template, pin in zip(S.REGISTRY_CONSTANTS, ("profile_sha256", "body_profile_sha256")):
        check("T5 candidate pins registry %s" % pin, raw.count(template % t["pins"][pin].encode("ascii")) == 1)


# ---------------------------------------------------------------------------
# Synthetic run
# ---------------------------------------------------------------------------

CAND, QUAL = "c" * 64, "d" * 64
MODEL = u"models/fursonas/starfox/krystal/bodies/krystal2020.mdl"
TARGET, PEER = 21688, 49430
HEAD_NEW, TAIL_NEW = 1.3300491571426392, 1.0


def raw_set(name, handle, head, tail, flex, head_in, tail_in):
    bones = [["bone 1 (bip_spine)", [0.0, 1.0, 2.0], [0.0, 0.0, 0.0, 1.0], None],
             ["bone 55 (bip_head)", [0.1, 4.1, 0.0], [0.0, 0.0, -0.5, 0.8], head],
             ["bone 60 (bip_tail00)", [0.2, -1.0, 0.0], [0.0, 0.0, 0.3, 0.9], tail]]
    return {"name": name, "handle": handle,
            "controls": {"bip_head_scale": {"value": head_in}, "bip_tail00_scale": {"value": tail_in},
                         "Smile": {"value": flex}},
            "model": {"model": MODEL, "handle": handle + 1, "visible": True, "skin": 0, "body": 0, "children": [],
                      "bones": bones, "flexes": [["Smile", flex]]}}


def graph_row(bone, value, result, physical, ok):
    return {"bone": bone, "ok": ok, "predicate": "physical" if ok else "static",
            "trace": {"expression": {"value": value, "result": result, "id": ["DmeExpressionOperator", bone, 1, 2]},
                      "physical_scale": physical, "input_count": 1,
                      "inputs": [{"source_value": value, "log": {"key0_value": value, "key_count": 1}}],
                      "output": {"mode": 3, "id": ["DmeChannel", bone, 3, 4],
                                 "log": {"key_count": 0, "is_empty": True, "use_default_value": False}}}}


def full_map(applied):
    if applied:
        rows = [graph_row(u"bip_head", 0.13300491869449615, HEAD_NEW, HEAD_NEW, True),
                graph_row(u"bip_tail00", 0.1, TAIL_NEW, TAIL_NEW, True)]
    else:
        rows = [graph_row(u"bip_head", 0.113, 1.13, 1.13, False), graph_row(u"bip_tail00", 0.08, 0.8, 0.8, False)]
    rows.append({"bone": u"bip_spine", "ok": True, "predicate": "implicit-neutral"})
    return {"record": u"Body", "result": bool(applied), "bones": rows, "would_raise": False}


def snap(value, result, physical):
    return {"source": value, "key_value": value, "key_count": 1, "expr_input": value, "expr_result": result,
            "physical_scale": physical, "input_mode": 3, "output_mode": 3, "output_key_count": 0,
            "output_is_empty": True, "output_use_default_value": False, "lo": 0.0, "hi": 10.0,
            "expression_id": ["E", 1], "output_id": ["O", 2], "transform_id": ["T", 3], "input_channel_id": ["I", 4],
            "control_id": ["C", 5]}


def writes():
    return [{"kind": "scale-write", "bone": u"bip_head", "desired_native": 0.13300491869449615,
             "desired_physical": HEAD_NEW, "static_output_mode": 3, "before": snap(0.113, 1.13, 1.13),
             "after": snap(0.13300491869449615, HEAD_NEW, 1.13)},
            {"kind": "scale-write", "bone": u"bip_tail00", "desired_native": 0.1, "desired_physical": TAIL_NEW,
             "static_output_mode": 3, "before": snap(0.08, 0.8, 0.8), "after": snap(0.1, TAIL_NEW, 0.8)}]


def capture(step, applied, undo, events=()):
    head, tail, flex, hi, ti = ((HEAD_NEW, TAIL_NEW, 0.5, 0.13300491869449615, 0.1) if applied
                                else (1.13, 0.8, 0.25, 0.113, 0.08))
    sets = [raw_set(u"Krystal", TARGET, head, tail, flex, hi, ti),
            raw_set(u"krystal20201", PEER, 1.0, None, 0.0, 0.1, 0.0),
            {"name": u"Main_Cam", "handle": 5, "controls": {}, "model": None}]
    return {"format": "F01-OT1-capture-v1", "step": step, "pid": 100, "time": 1.0, "cpm_build_sha256": QUAL,
            "errors": {}, "session": {"document": u"E:/run/sessions/OT1_KRYSTAL.dmx", "shot": u"shot15",
                                      "head_seconds": 0.20829999446868896, "timeline_mode": u"x",
                                      "undo": copy.deepcopy(undo)},
            "character": {}, "instance": {"animset_key": ["DmeAnimationSet", TARGET, u"uuid"]},
            "animation_sets": sets, "record": {"preset_id": u"p", "bone_scales": 154},
            "settled_full_map": full_map(applied), "events": list(events)}


U_BASE = {"can_undo": True, "can_redo": False, "undo_desc": u"CreateAnimationSetAndModel", "redo_desc": u"",
          "count": 4}
U_APPLY = {"can_undo": True, "can_redo": False, "undo_desc": u"Apply Body Preset", "redo_desc": u"", "count": 5}
U_UNDONE = {"can_undo": True, "can_redo": True, "undo_desc": u"CreateAnimationSetAndModel",
            "redo_desc": u"Redo Apply Body Preset", "count": 5}


def ident(kind, label, handle):
    return [kind, label, handle, handle * 8]


def bone_ids(bone):
    base = 100 if bone == u"bip_head" else 200
    return {"expression": ident(u"DmeExpressionOperator", bone + u"_scale_rescale", base),
            "input_channel": ident(u"DmeChannel", bone + u"_scale", base + 1),
            "output": ident(u"DmeChannel", u"scaled_%s_scale_channel" % bone, base + 2),
            "transform": ident(u"DmeTransform", u"bone", base + 3), "control": ident(u"DmElement", bone, base + 4),
            "animset": ident(u"DmeAnimationSet", u"Krystal", TARGET)}


def ref(owner, attr, role):
    return {"owner": owner, "owner_type": owner[0], "owner_name": owner[1], "owner_handle": owner[2],
            "attribute": attr, "role": role}


def direct(bone):
    ids = bone_ids(bone)
    rows = [ref(ids["animset"], u"operators", "animset"), ref(ids["input_channel"], u"toElement", "input_channel"),
            ref(ids["output"], u"fromElement", "output")]
    return {"complete": True, "terminated_at_sentinel": True, "repeated_token": False, "error": None,
            "tokens": ["%d" % (1000 + i) for i in range(len(rows))], "sentinel": "0",
            "class_entries": {"before": {}, "after": {}, "unchanged": True},
            "vsutils_module": {"before": False, "after": False, "unchanged": True}, "references": rows, "pass": True,
            "matched": {"animset": 1, "input_channel": 1, "output": 1}, "unexpected": [], "unreadable": []}


def preflight():
    def bone(name):
        return {"would_pass": True, "error": None, "static_output_mode": 3, "expression_ok": True,
                "endpoints_ok": True, "unique": True, "operator_lists": [u"Krystal"], "identities": bone_ids(name),
                "direct_refs": direct(name),
                "candidate_scan": {"error": None, "readers": 1, "writers": 1},
                "enumeration": {"clips": 3, "channels": 900, "readers": [{}], "writers": [{}], "unreadable": []}}
    state = {"undo": dict(U_BASE), "head_seconds": 0.20829999446868896}
    return {"instance": {"animset_key": ["DmeAnimationSet", TARGET, u"uuid"]}, "error": None, "would_pass": True,
            "bones": {u"bip_head": bone(u"bip_head"), u"bip_tail00": bone(u"bip_tail00")},
            "side_effects": {"before": state, "after": copy.deepcopy(state), "unchanged": True}}


def passing_run():
    apply_events = ([{"kind": "apply-begin", "preset": u"Body", "preset_kind": u"body"}] + writes() +
                    [{"kind": "refresh-after", "label": u"PROD_APPLY",
                      "scales": [{"bone": u"bip_head", "after": snap(0.133, HEAD_NEW, HEAD_NEW)}]},
                     {"kind": "apply-returned"},
                     {"kind": "deferred-verify", "record": u"Body", "result": True, "consistent": True,
                      "full_map": full_map(True)}])
    abort_events = ([{"kind": "apply-begin", "preset": u"Body", "preset_kind": u"body"}] + writes() +
                    [{"kind": "injected-failure", "bone": u"bip_tail00"},
                     {"kind": "refresh-after", "label": u"PROD_APPLY_ABORT", "scales": []},
                     {"kind": "abort-verify", "result": True},
                     {"kind": "apply-raised", "error_type": "RuntimeError", "error": "OT1 controlled failure"}])
    caps = {"BASE": capture("BASE", False, U_BASE), "APPLY": capture("APPLY", True, U_APPLY, apply_events),
            "UNDO": capture("UNDO", False, U_UNDONE), "REDO": capture("REDO", True, U_APPLY),
            "UNDO2": capture("UNDO2", False, U_UNDONE), "ARM": capture("ARM", False, U_UNDONE),
            "ABORT": capture("ABORT", False, U_UNDONE, abort_events)}
    caps["BASE"]["hooks_installed"] = list(A.HOOKS)
    caps["BASE"]["preflight"] = preflight()
    caps["ARM"]["preflight"] = preflight()
    for step in ("BASE", "ARM"):
        caps[step]["environment"] = {"vsutils_in_sys_modules_at_capture": False}
    caps["ARM"]["injector"] = {"armed": True, "fired": 0, "bone": u"bip_tail00"}
    caps["ABORT"]["injector"] = {"armed": False, "fired": 1}
    caps["ABORT"]["hooks_removed"] = True
    logs = [u"PROD_APPLY_DEFERRED_VERIFY outcome=u'committed-verified' reason=None model=u'm' kind=u'body' "
            u"preset=u'Body' play_scales=2",
            u"PROD_APPLY_ABORT_VERIFY restored=True original_error=RuntimeError('OT1 controlled failure after the "
            u"operator call',) abort_or_verify_error=None"]
    return {"caps": caps, "logs": logs, "ids": {"candidate_cpm_sha256": CAND, "qualification_cpm_sha256": QUAL},
            "cleanup": {"differences_kept_in_evidence": [], "files_equal_pre": True, "folders_equal_pre": True},
            "restore": {"restored": True}, "session": b"OT1 session bytes"}


def write_run(run):
    q = tempfile.mkdtemp(prefix="ot1_test_")
    for d in ("staged", "observations", "evidence/logs", "sessions"):
        os.makedirs(os.path.join(q, *d.split("/")))

    def dump(rel, obj):
        with open(os.path.join(q, *rel.split("/")), "wb") as f:
            f.write(json.dumps(obj).encode("utf-8"))
    dump("staged/IDENTITIES.json", run["ids"])
    for step, cap in run["caps"].items():
        if cap is not None:
            dump("observations/OT1-%s.json" % step, cap)
    dump("evidence/library_cleanup.json", run["cleanup"])
    dump("evidence/restore.json", run["restore"])
    with open(os.path.join(q, "evidence", "logs", "CPM - 2026-11-16_10-00-00Z - pid100 - x - 001.log"), "wb") as f:
        f.write(("\n".join(u"2026-11-16T10:00:%02d.000Z #%06d s=x w=1 op=1 | %s" % (i, i + 1, t)
                           for i, t in enumerate(run["logs"])) + "\n").encode("utf-8"))
    with open(os.path.join(q, "sessions", "OT1_KRYSTAL.dmx"), "wb") as f:
        f.write(run["session"])
    pins = {"candidate_cpm_sha256": CAND, "qualification_cpm_sha256": QUAL,
            "r2_fixture_sha256": hashlib.sha256(b"OT1 session bytes").hexdigest()}
    return q, {"paths": {"Q": q}, "pins": pins, "character_dir": "krystal2020--x"}


def analyze(run):
    q, c = write_run(run)
    try:
        R = A.Report(c)
        A.evaluate(R)
        v, gates = A.verdict(R.checks)
        failed = [x["id"] for x in R.checks if not x["pass"]]
        out = {"verdict": v, "gates": gates, "identities": R.ids, "checks": R.checks, "info": R.info,
               "findings": R.findings}
        return v, gates, failed, A.markdown(out)
    finally:
        shutil.rmtree(q)


def dc1(run, step, bone, change):
    """Alter one capture's DC1 evidence as the observer would have recorded it (its own pass flag left True, so the
    analyzer's independent checks are what must catch it)."""
    change(run["caps"][step]["preflight"]["bones"][bone]["direct_refs"])


def mutate(fn):
    run = passing_run()
    fn(run)
    return analyze(run)


def ev(run, step, kind):
    return [e for e in run["caps"][step]["events"] if e.get("kind") == kind]


def set_of(run, step, handle):
    return [s for s in run["caps"][step]["animation_sets"] if s["handle"] == handle][0]


def bone(run, step, handle, name):
    return [r for r in set_of(run, step, handle)["model"]["bones"] if name in r[0]][0]


def section_analyzer():
    v, gates, failed, md = analyze(passing_run())
    check("V1 the complete passing trial -> CANDIDATE PASS (every gate PASS)", v == "CANDIDATE PASS"
          and all(gates.values()), failed)

    def lag_undo(run):  # Q1's duplicate-Undo symptom: physical one step behind after Undo
        bone(run, "UNDO", TARGET, "bip_head")[3] = HEAD_NEW
        run["caps"]["UNDO"]["settled_full_map"]["bones"][0]["trace"]["physical_scale"] = HEAD_NEW
    v, gates, failed, md = mutate(lag_undo)
    check("V2 Apply PASS with a lagging physical scale after Undo -> CANDIDATE FAIL (UNDO gate), stated in the report",
          v == "CANDIDATE FAIL" and gates["APPLY"] and not gates["UNDO"] and gates["EVIDENCE"]
          and "Apply PASS with Undo FAIL: the candidate FAILS" in md, (v, gates, failed))

    cases = [
        ("UNDO", "authored input not restored by Undo", lambda r: set_of(r, "UNDO", TARGET)["controls"]
         ["bip_head_scale"].__setitem__("value", 0.133)),
        ("UNDO", "expression result not restored by Undo", lambda r: r["caps"]["UNDO"]["settled_full_map"]["bones"][0]
         ["trace"]["expression"].__setitem__("result", HEAD_NEW)),
        ("UNDO", "Redo not exactly the applied state", lambda r: bone(r, "REDO", TARGET, "bip_tail00").__setitem__(3, 0.8)),
        ("UNDO", "Redo history wrong", lambda r: r["caps"]["REDO"]["session"].__setitem__("undo", dict(U_UNDONE))),
        ("UNDO", "final Undo leaves the tail scale", lambda r: bone(r, "UNDO2", TARGET, "bip_tail00").__setitem__(3, 1.0)),
        ("UNDO", "Undo history names something else", lambda r: r["caps"]["UNDO"]["session"]["undo"].__setitem__(
            "redo_desc", u"Redo Something")),
        ("UNDO", "peer changed by Redo", lambda r: set_of(r, "REDO", PEER)["controls"]["Smile"].__setitem__("value", 0.9)),
        ("APPLY", "deferred verification failed (committed-unverified)", lambda r: (
            ev(r, "APPLY", "deferred-verify")[0].__setitem__("result", False),
            r["logs"].__setitem__(0, r["logs"][0].replace("committed-verified' reason=None",
                                                          "committed-unverified' reason=u'bone-scales'")))),
        ("APPLY", "expression result wrong at precommit", lambda r: ev(r, "APPLY", "scale-write")[0]["after"]
         .__setitem__("expr_result", 1.13)),
        ("APPLY", "output log keyed at precommit", lambda r: ev(r, "APPLY", "scale-write")[1]["after"]
         .__setitem__("output_key_count", 1)),
        ("APPLY", "a third scale written", lambda r: r["caps"]["APPLY"]["events"].insert(
            1, dict(writes()[0], bone=u"bip_spine"))),
        ("APPLY", "a mode-1 write in the operation", lambda r: ev(r, "APPLY", "scale-write")[0].__setitem__(
            "static_output_mode", 1)),
        ("APPLY", "two history entries", lambda r: r["caps"]["APPLY"]["session"]["undo"].__setitem__("count", 6)),
        ("APPLY", "peer changed by Apply", lambda r: bone(r, "APPLY", PEER, "bip_head").__setitem__(3, 1.33)),
        ("APPLY", "another target bone moved", lambda r: bone(r, "APPLY", TARGET, "bip_spine").__setitem__(1, [0.0, 1.5, 2.0])),
        ("APPLY", "physical scale not the requested value", lambda r: bone(r, "APPLY", TARGET, "bip_head").__setitem__(3, 1.13)),
        ("APPLY", "settled map fails", lambda r: r["caps"]["APPLY"]["settled_full_map"].__setitem__("result", False)),
        ("ABORT", "CPM abort verification false", lambda r: (
            ev(r, "ABORT", "abort-verify")[0].__setitem__("result", False),
            r["logs"].__setitem__(1, r["logs"][1].replace("restored=True", "restored=False")))),
        ("ABORT", "failure not injected after the tail operator", lambda r: r["caps"]["ABORT"]["events"].remove(
            ev(r, "ABORT", "injected-failure")[0])),
        ("ABORT", "operator did not produce the expected result before the failure", lambda r: ev(r, "ABORT", "scale-write")
         [1]["after"].__setitem__("expr_result", 0.8)),
        ("ABORT", "target not restored after Abort", lambda r: bone(r, "ABORT", TARGET, "bip_head").__setitem__(3, HEAD_NEW)),
        ("ABORT", "expression result left after Abort", lambda r: r["caps"]["ABORT"]["settled_full_map"]["bones"][0]
         ["trace"]["expression"].__setitem__("result", HEAD_NEW)),
        ("ABORT", "history entry added by the failed Apply", lambda r: r["caps"]["ABORT"]["session"].__setitem__(
            "undo", dict(U_APPLY))),
        ("ABORT", "Apply returned instead of failing", lambda r: r["caps"]["ABORT"]["events"].append(
            {"kind": "apply-returned"})),
        ("ABORT", "injector fired twice", lambda r: r["caps"]["ABORT"].__setitem__("injector",
                                                                                  {"armed": False, "fired": 2})),
    ]
    for gate, label, fn in cases:
        v, gates, failed, md = mutate(fn)
        check("V3 %s -> CANDIDATE FAIL at %s" % (label, gate), v == "CANDIDATE FAIL" and not gates[gate]
              and gates["EVIDENCE"], (v, gates, failed))

    evidence = [
        ("a capture missing", lambda r: r["caps"].__setitem__("REDO", None)),
        ("the wrong build", lambda r: r["caps"]["UNDO"].__setitem__("cpm_build_sha256", "e" * 64)),
        ("the time moved (manual retiming)", lambda r: r["caps"]["REDO"]["session"].__setitem__("head_seconds", 0.25)),
        ("another shot", lambda r: r["caps"]["ARM"]["session"].__setitem__("shot", u"shot13")),
        ("a second SFM process", lambda r: r["caps"]["ABORT"].__setitem__("pid", 101)),
        ("the session saved", lambda r: r.__setitem__("session", b"saved")),
        ("library not restored", lambda r: r["cleanup"].__setitem__("files_equal_pre", False)),
        ("installation not restored", lambda r: r["restore"].__setitem__("restored", False)),
        ("hooks not removed", lambda r: r["caps"]["ABORT"].__setitem__("hooks_removed", False)),
        ("a CPM Apply during the Undo steps", lambda r: r["caps"]["UNDO"]["events"].append(
            {"kind": "apply-begin", "preset": u"Happy", "preset_kind": u"expression"})),
        ("a visibility edit", lambda r: set_of(r, "UNDO2", PEER)["model"].__setitem__("visible", False)),
        ("another instance selected", lambda r: r["caps"]["REDO"].__setitem__(
            "instance", {"animset_key": ["DmeAnimationSet", PEER, u"uuid"]})),
        ("no same-model peer", lambda r: [c["animation_sets"].pop(1) for c in r["caps"].values()]),
        ("recovery uncertainty in the log", lambda r: r["logs"].append(u"PROD_OPERATION_OUTCOME outcome=u'recovery-unverified'")),
        ("no BASE preflight", lambda r: r["caps"]["BASE"].pop("preflight")),
        ("BASE preflight changed the Undo state", lambda r: r["caps"]["BASE"]["preflight"]["side_effects"].__setitem__(
            "unchanged", False)),
        ("BASE preflight: a shared head expression (two readers)", lambda r: (
            r["caps"]["BASE"]["preflight"].__setitem__("would_pass", False),
            r["caps"]["BASE"]["preflight"]["bones"][u"bip_head"].__setitem__("would_pass", False),
            r["caps"]["BASE"]["preflight"]["bones"][u"bip_head"]["candidate_scan"].__setitem__("readers", 2))),
        ("BASE preflight: an unreadable endpoint", lambda r: (
            r["caps"]["BASE"]["preflight"]["bones"][u"bip_tail00"]["enumeration"]["unreadable"].append(
                {"what": "endpoint"}))),
        ("BASE preflight: another instance", lambda r: r["caps"]["BASE"]["preflight"].__setitem__(
            "instance", {"animset_key": ["DmeAnimationSet", PEER, u"uuid"]})),
        ("DC1: an off-track channel reader at BASE", lambda r: dc1(r, "BASE", u"bip_head", lambda d: d["references"]
                                                                   .append(ref(ident(u"DmeChannel", u"off", 9), u"fromElement", None)))),
        ("DC1: an unexpected non-channel reference at ARM", lambda r: dc1(r, "ARM", u"bip_tail00", lambda d: d[
            "references"].append(ref(ident(u"DmeConnectionOperator", u"conn", 8), u"input", None)))),
        ("DC1: a missing reference", lambda r: dc1(r, "BASE", u"bip_tail00", lambda d: d["references"].pop(0))),
        ("DC1: a duplicated reference", lambda r: dc1(r, "ARM", u"bip_head", lambda d: d["references"].append(
            dict(d["references"][1])))),
        ("DC1: an unreadable attribute", lambda r: dc1(r, "BASE", u"bip_head", lambda d: d["references"][2].update(
            unreadable="attribute: RuntimeError()"))),
        ("DC1: an incomplete enumeration", lambda r: dc1(r, "ARM", u"bip_head", lambda d: d.update(
            complete=False, error="RuntimeError('iterator failed')"))),
        ("DC1: the operators owner is the peer's set (wrong instance)", lambda r: dc1(
            r, "BASE", u"bip_head", lambda d: d["references"].__setitem__(
                0, ref(ident(u"DmeAnimationSet", u"krystal20201", PEER), u"operators", "animset")))),
        ("DC1: a replaced input channel at ARM (another live element)", lambda r: dc1(
            r, "ARM", u"bip_head", lambda d: d["references"].__setitem__(
                1, ref(ident(u"DmeChannel", u"bip_head_scale", 999), u"toElement", "input_channel")))),
        ("DC1: BASE and ARM disagree on the live elements", lambda r: [
            b.update(identities=dict(b["identities"], output=ident(u"DmeChannel", u"o", 777)),
                     direct_refs=dict(b["direct_refs"], references=[
                         x if x["role"] != "output" else ref(ident(u"DmeChannel", u"o", 777), u"fromElement", "output")
                         for x in b["direct_refs"]["references"]]))
            for b in [r["caps"]["ARM"]["preflight"]["bones"][u"bip_head"]]]),
        ("DC1: partial evidence (no reference list)", lambda r: dc1(r, "BASE", u"bip_head", lambda d: d.pop(
            "references"))),
        ("DC1: partial evidence (no identities)", lambda r: r["caps"]["ARM"]["preflight"]["bones"][u"bip_tail00"].pop(
            "identities")),
        ("DC1: no ARM preflight", lambda r: r["caps"]["ARM"].pop("preflight")),
        ("DC1: ARM preflight changed the state", lambda r: r["caps"]["ARM"]["preflight"]["side_effects"].__setitem__(
            "unchanged", False)),
        ("DC2: traversal did not reach the sentinel", lambda r: dc1(r, "BASE", u"bip_head", lambda d: d.update(
            terminated_at_sentinel=False))),
        ("DC2: a repeated iterator token", lambda r: dc1(r, "ARM", u"bip_tail00", lambda d: d.update(
            repeated_token=True))),
        ("DC2: a class entry replaced across a traversal", lambda r: dc1(r, "BASE", u"bip_tail00", lambda d: d[
            "class_entries"].__setitem__("unchanged", False))),
        ("DC2: vsUtils membership changed across a traversal", lambda r: dc1(r, "ARM", u"bip_head", lambda d: d[
            "vsutils_module"].__setitem__("unchanged", False))),
        ("DC2: partial evidence (no token list)", lambda r: dc1(r, "BASE", u"bip_head", lambda d: d.pop("tokens"))),
        ("DC2: tokens not accounting for the rows", lambda r: dc1(r, "ARM", u"bip_head", lambda d: d["tokens"].pop())),
        ("DC2: partial evidence (no class-entry record)", lambda r: dc1(r, "ARM", u"bip_tail00", lambda d: d.pop(
            "class_entries"))),
        ("DC2: no environment record at ARM", lambda r: r["caps"]["ARM"].pop("environment")),
        ("BASE not the expected starting state", lambda r: r["caps"]["BASE"].__setitem__("settled_full_map",
                                                                                        full_map(True))),
    ]
    for label, fn in evidence:
        v, gates, failed, md = mutate(fn)
        check("V4 %s -> INCOMPLETE (no candidate decision)" % label, v == "INCOMPLETE" and not gates["EVIDENCE"],
              (v, failed))

    v, gates, failed, md = analyze(passing_run())
    check("V6 the expected three references with the valid operators-array membership pass at BASE and ARM",
          v == "CANDIDATE PASS" and "dc1.BASE_three_live_references_per_expression" not in failed, failed)
    run = passing_run()
    run["caps"]["BASE"]["environment"]["vsutils_in_sys_modules_at_capture"] = True
    v, gates, failed, md = analyze(run)
    check("V6 a preloaded vsUtils is a starting-environment observation (finding), not a failure",
          v == "CANDIDATE PASS" and "starting-environment observation" in md, failed)

    run = passing_run()
    q, c = write_run(run)
    try:
        first = A.run(c)
        try:
            A.run(c)
            second = "overwrote"
        except OSError:
            second = "refused"
        check("V5 run writes OT1_VERDICT.json/.md once (exclusive create), exit 0 on CANDIDATE PASS",
              first == 0 and second == "refused" and os.path.isfile(os.path.join(q, "evidence", "OT1_VERDICT.md")),
              (first, second))
    finally:
        shutil.rmtree(q)


def main():
    print("Interpreter: %s" % sys.version.split()[0])
    for section in (section_template, section_analyzer):
        try:
            section()
        except Exception:
            import traceback
            check("section.completed", False, traceback.format_exc())
    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
