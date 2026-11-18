# -*- coding: utf-8 -*-
"""F-01 OT1S kit: offline tests of the template, the one-line build derivation and the smoke analyzer (Python 3, -I).
Synthetic runs reuse the OT1 kit's test builders (test_ot1.capture, raw sets, scale-write events); nothing here shows
anything about SFM.

usage: python -I test_smoke.py
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
sys.path.insert(0, os.path.join(KIT, "..", "f01_ot1_ordering_trial", "tests"))
import smoke_tool  # noqa: E402
import smoke_analyze as A  # noqa: E402
import test_ot1 as B  # noqa: E402  (synthetic capture builders)

RESULTS = []
QUALIFIED_CPM_COMMIT = "d719bb0"


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def sha_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def section_template():
    with open(os.path.join(KIT, "ot1s.template.json"), "rb") as f:
        t = json.loads(f.read().decode("utf-8"))
    check("T1 format and no placeholder pin", t["format"] == smoke_tool.FORMAT
          and not any("<" in v for v in t["pins"].values()))
    # The OT1S kit ran the exact integrated candidate it qualified (48ff01a3...). Later work (H1) changed the
    # working-tree CPM, so, as the OT1, K2 and EF-1 kit tests do, the candidate is read as the raw Git blob from its
    # commit; the tool's own hash checks still decide at build time.
    import subprocess
    raw = subprocess.check_output(["git", "-C", REPO, "cat-file", "blob",
                                   "%s:cpm/app/SFM_Character_Preset_Manager.py" % QUALIFIED_CPM_COMMIT])
    check("T2 candidate pin = the integrated candidate at commit %s" % QUALIFIED_CPM_COMMIT,
          t["pins"]["candidate_cpm_sha256"] == hashlib.sha256(raw).hexdigest())
    for key, rel in (("ot1s_observer_sha256", "real_sfm_qualification/f01_ot1_integration_smoke/observer/F01_OT1S_Observe.py"),
                     ("ot1_observer_sha256", "real_sfm_qualification/f01_ot1_ordering_trial/observer/F01_OT1_Observe.py"),
                     ("q1_observer_sha256", "real_sfm_qualification/f01_q1_ps2_diagnostic/observer/F01_Q1_Observe.py"),
                     ("profile_sha256", "cpm/pose_profiles/cpm_pose_profiles_v1.json"),
                     ("body_profile_sha256", "cpm/pose_profiles/cpm_body_profiles_v1.json")):
        check("T2 pin %s = %s" % (key, rel), t["pins"][key] == sha_file(os.path.join(REPO, *rel.split("/"))))
    with open(os.path.join(KIT, "..", "f01_ot1_ordering_trial", "ot1.template.json"), "rb") as f:
        o = json.loads(f.read().decode("utf-8"))
    for key in ("published_cpm_sha256", "r2_fixture_sha256", "destination_sha256", "body_preset_sha256",
                "legacy_pose_sha256", "observer_sha256"):
        check("T3 pin %s equals the OT1 kit's" % key, t["pins"][key] == o["pins"][key])
    check("T3 paths equal the OT1 kit's", t["paths"] == o["paths"])
    S = smoke_tool.S
    qual = raw.replace(S.MODE_PRODUCTION, S.MODE_QUALIFICATION)
    diff = [i for i, (x, y) in enumerate(zip(raw.split(b"\n"), qual.split(b"\n"))) if x != y]
    check("T4 one-line derivation gives the pinned qualification build", len(diff) == 1
          and hashlib.sha256(qual).hexdigest() == t["pins"]["qualification_cpm_sha256"], diff)
    with open(os.path.join(KIT, "observer", "F01_OT1S_Observe.py"), "rb") as f:
        src = f.read().decode("ascii")
    check("T5 the smoke observer pins the same OT1 observer", 'OT1_OBSERVER_SHA256 = "%s"' % t["pins"]["ot1_observer_sha256"]
          in src)
    text = raw.decode("utf-8")
    needed = ["prod_apply", "prod_bs_write_existing_scale", "same_time_refresh", "prod_bs_index_verify_saved",
              "prod_verify_apply_abort_baseline", "prod_bs_expression_reference_guard", "prod_bs_snapshot",
              "prod_instance_token", "prod_instance_kw", "prod_bs_index_snapshot"]
    missing = [n for n in needed if ("\ndef %s(" % n) not in text]
    check("T6 every CPM function the observer hooks or reads exists in the integrated candidate", not missing, missing)
    apply_src = text[text.index("\ndef prod_apply("):text.index("\ndef ", text.index("\ndef prod_apply(") + 5)]
    operate_src = text[text.index("\ndef prod_bs_operate_bound_expression("):
                       text.index("\ndef ", text.index("\ndef prod_bs_operate_bound_expression(") + 5)]
    check("T6 the guard is called through module globals before StartUndo and before Operate() (so the hook sees both)",
          "prod_bs_expression_reference_guard(" in apply_src
          and apply_src.index("prod_bs_expression_reference_guard(") < apply_src.index("StartUndo(")
          and "prod_bs_expression_reference_guard(" in operate_src
          and operate_src.index("prod_bs_expression_reference_guard(") < operate_src.index("operate()"))
    check("T6 the integrated candidate no longer has the OT1 channel scan the OT1 observer's preflight needed",
          "\ndef prod_bs_expression_channels(" not in text)


# ---------------------------------------------------------------------------

def guard(bone):
    return {"kind": "reference-guard", "bone": bone, "result": True, "error": None}


def apply_events():
    w = B.writes()
    return ([{"kind": "apply-begin", "preset": u"Body", "preset_kind": u"body"}, guard(u"bip_head"),
             guard(u"bip_tail00"), guard(u"bip_head"), w[0], guard(u"bip_tail00"), w[1],
             {"kind": "refresh-after", "label": u"PROD_APPLY", "scales": []}, {"kind": "apply-returned"},
             {"kind": "deferred-verify", "record": u"Body", "result": True, "consistent": True,
              "full_map": B.full_map(True)}])


def passing_run():
    caps = {"BASE": B.capture("BASE", False, B.U_BASE), "APPLY": B.capture("APPLY", True, B.U_APPLY, apply_events()),
            "UNDO": B.capture("UNDO", False, B.U_UNDONE), "REDO": B.capture("REDO", True, B.U_APPLY),
            "UNDO2": B.capture("UNDO2", False, B.U_UNDONE)}
    for step, cap in caps.items():
        cap["session"]["document"] = u"E:/run/sessions/OT1S_KRYSTAL.dmx"
        if step != "BASE":
            cap["injector"] = {"armed": False, "fired": 0}
    caps["BASE"]["hooks_installed"] = list(A.HOOKS)
    caps["UNDO2"]["hooks_removed"] = True
    logs = [u"PROD_APPLY_DEFERRED_VERIFY outcome=u'committed-verified' reason=None model=u'm' kind=u'body' "
            u"preset=u'Body' play_scales=2"]
    return {"caps": caps, "logs": logs, "ids": {"candidate_cpm_sha256": B.CAND, "qualification_cpm_sha256": B.QUAL},
            "cleanup": {"differences_kept_in_evidence": [], "files_equal_pre": True, "folders_equal_pre": True},
            "restore": {"restored": True}, "session": b"OT1 session bytes"}


def write_run(run):
    q, c = B.write_run(run)
    obs = os.path.join(q, "observations")
    for name in os.listdir(obs):
        os.rename(os.path.join(obs, name), os.path.join(obs, name.replace("OT1-", "OT1S-")))
    os.rename(os.path.join(q, "sessions", "OT1_KRYSTAL.dmx"), os.path.join(q, "sessions", "OT1S_KRYSTAL.dmx"))
    return q, c


def analyze(run):
    q, c = write_run(run)
    try:
        R = A.Report(c)
        A.evaluate(R)
        v, gates = A.verdict(R.checks)
        return v, gates, [x["id"] for x in R.checks if not x["pass"]]
    finally:
        shutil.rmtree(q)


def mutate(fn):
    run = passing_run()
    fn(run)
    return analyze(run)


def events(run, step):
    return run["caps"][step]["events"]


def bone(run, step, handle, name):
    sets = [s for s in run["caps"][step]["animation_sets"] if s["handle"] == handle][0]
    return [r for r in sets["model"]["bones"] if name in r[0]][0]


def section_analyzer():
    v, gates, failed = analyze(passing_run())
    check("V1 complete passing smoke -> SMOKE PASS (every gate)", v == "SMOKE PASS" and all(gates.values()), failed)
    functional = [
        ("GUARD", "a guard refusal", lambda r: events(r, "APPLY")[1].update(result=None, error="RuntimeError()")),
        ("GUARD", "no pre-transaction guard check", lambda r: [events(r, "APPLY").pop(1) for _ in range(2)]),
        ("GUARD", "the in-transaction guard check missing for the tail",
         lambda r: events(r, "APPLY").pop(5)),
        ("APPLY", "deferred verification unverified", lambda r: (
            [e.update(result=False) for e in events(r, "APPLY") if e["kind"] == "deferred-verify"],
            r["logs"].__setitem__(0, r["logs"][0].replace("committed-verified' reason=None",
                                                          "committed-unverified' reason=u'bone-scales'")))),
        ("APPLY", "physical scale not the requested value", lambda r: bone(r, "APPLY", B.TARGET, "bip_head").__setitem__(
            3, 1.13)),
        ("APPLY", "Apply label not 'Apply Body Preset'", lambda r: r["caps"]["APPLY"]["session"]["undo"].__setitem__(
            "undo_desc", u"Set Value")),
        ("UNDO", "physical scale one step behind after Undo (Q1's symptom)", lambda r: (
            bone(r, "UNDO", B.TARGET, "bip_head").__setitem__(3, B.HEAD_NEW),
            r["caps"]["UNDO"]["settled_full_map"]["bones"][0]["trace"].__setitem__("physical_scale", B.HEAD_NEW))),
        ("UNDO", "Redo not the applied state", lambda r: bone(r, "REDO", B.TARGET, "bip_tail00").__setitem__(3, 0.8)),
        ("UNDO", "final Undo leaves the tail", lambda r: bone(r, "UNDO2", B.TARGET, "bip_tail00").__setitem__(3, 1.0)),
        ("UNDO", "Undo label wrong", lambda r: r["caps"]["UNDO"]["session"]["undo"].__setitem__("redo_desc", u"x")),
        ("PEER", "peer changed at Redo", lambda r: [s for s in r["caps"]["REDO"]["animation_sets"]
                                                    if s["handle"] == B.PEER][0]["controls"]["Smile"].__setitem__(
            "value", 0.9)),
    ]
    for gate, label, fn in functional:
        v, gates, failed = mutate(fn)
        check("V2 %s -> SMOKE FAIL at %s" % (label, gate), v == "SMOKE FAIL" and not gates[gate] and gates["EVIDENCE"],
              (v, gates, failed))
    evidence = [
        ("a capture missing", lambda r: r["caps"].__setitem__("REDO", None)),
        ("the wrong build", lambda r: r["caps"]["UNDO"].__setitem__("cpm_build_sha256", "e" * 64)),
        ("the time moved", lambda r: r["caps"]["REDO"]["session"].__setitem__("head_seconds", 0.25)),
        ("the session saved", lambda r: r.__setitem__("session", b"saved")),
        ("library not restored", lambda r: r["cleanup"].__setitem__("files_equal_pre", False)),
        ("installation not restored", lambda r: r["restore"].__setitem__("restored", False)),
        ("hooks not removed", lambda r: r["caps"]["UNDO2"].__setitem__("hooks_removed", False)),
        ("a second CPM Apply", lambda r: events(r, "REDO").append({"kind": "apply-begin", "preset": u"Body",
                                                                   "preset_kind": u"body"})),
        ("the injector armed", lambda r: r["caps"]["UNDO"].__setitem__("injector", {"armed": True, "fired": 0})),
        ("another instance selected", lambda r: r["caps"]["UNDO"].__setitem__(
            "instance", {"animset_key": ["DmeAnimationSet", B.PEER, u"uuid"]})),
        ("recovery uncertainty logged", lambda r: r["logs"].append(u"x recovery-unverified")),
    ]
    for label, fn in evidence:
        v, gates, failed = mutate(fn)
        check("V3 %s -> INCOMPLETE" % label, v == "INCOMPLETE" and not gates["EVIDENCE"], (v, failed))
    run = passing_run()
    q, c = write_run(run)
    try:
        first = A.run(c)
        try:
            A.run(c)
            second = "overwrote"
        except OSError:
            second = "refused"
        check("V4 run writes OT1S_VERDICT once (exclusive create); exit 0 on SMOKE PASS",
              first == 0 and second == "refused", (first, second))
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
