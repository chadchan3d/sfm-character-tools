# -*- coding: ascii -*-
"""F-01 Q1: the observer on SFM's Python 2.7.5 against the candidate's real functions (the R15 harness's real window,
sfmApp faked at its boundary; the candidate read from commit fda1fb3, CPM 615acf0c...).

- E: the observer's full map equals CPM's own prod_bs_index_verify_saved on the same record and snapshot, for every
  failure kind (implicit neutral, classification, static trace, physical value) and the all-pass case, using CPM's
  real classification and closeness predicates; where CPM's function raises, the map says would_raise.
- W: the four wrappers return the originals' results unchanged, re-raise the originals' exceptions unchanged (type,
  message and the original traceback's innermost frame), record their events, and q1_uninstall restores the exact
  original functions; a second install is a no-op.
They show nothing about SFM itself.

Usage: <SFM python 2.7.5> -E -B test_q1_observer.py
"""
from __future__ import print_function

import hashlib
import os
import subprocess
import sys
import tempfile
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(KIT))
sys.path.insert(0, os.path.join(REPO, "cpm", "convergence", "tests"))
import test_cpm_app_r15_namespace_isolation as r15  # noqa: E402

CANDIDATE = "615acf0c23ffcf5c278785bb47de6aaf6a7b9ae26779b9313979ac928240c432"
OBSERVER = os.path.join(KIT, "observer", "F01_Q1_Observe.py")
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def observer_namespace():
    ns = {"__name__": "q1_observer_under_test"}
    with open(OBSERVER, "rb") as f:
        exec(compile(f.read(), OBSERVER, "exec"), ns)
    return ns


def static_trace(value, passing=True):
    """A trace CPM's real static classification accepts (the historical output-pass rule) or rejects (structure)."""
    if not passing:
        return {"generic_lerp_topology": False, "physical_matches_lerp": False, "input_count": 0, "inputs": [],
                "output": {"mode": 0}, "physical_scale": value}
    return {"generic_lerp_topology": True, "physical_matches_lerp": True, "input_count": 1,
            "inputs": [{"mode": 3, "source_type": u"DmElement", "source_attribute": u"value", "source_value": value,
                        "log": {"key_count": 1, "is_empty": False, "key0_time": 0.0, "key0_value": value}}],
            "output": {"mode": 1}, "physical_scale": value}


def main():
    raw = subprocess.check_output(["git", "-C", REPO, "cat-file", "blob",
                                   "fda1fb3:cpm/app/SFM_Character_Preset_Manager.py"])
    if hashlib.sha256(raw).hexdigest() != CANDIDATE:
        print("RESULT: the candidate at fda1fb3 is not %s" % CANDIDATE)
        return 1
    sentinel = "<fda1fb3 candidate>"
    real_read = r15._read
    r15._read = lambda path: raw if path == sentinel else real_read(path)
    r15.APP_PATH = sentinel
    try:
        env = r15.Env("real", os.path.join(tempfile.gettempdir(), "cpm_q1_observer_fixture"))
        sfm = sys.modules["sfmApp"]
        sfm.HasDocument = lambda: False
        sfm.GetShotAtCurrentTime = lambda: None
        env.click()
        env.settle()
        window = env.slot()
        g = window.render.im_func.func_globals
        check("U0 the harness runs the fda1fb3 candidate",
              g.get("__chadchan3d_cpm_build_sha256__") in (None, CANDIDATE) and "prod_bs_index_verify_saved" in g)
        ns = observer_namespace()

        # E: equivalence with CPM's own verification
        traces = {}
        saved_validate, saved_trace = g["prod_bs_index_validate_saved_map"], g["prod_bs_index_trace"]

        def fake_trace(snapshot, row):
            t = traces[row["_key"]]
            if isinstance(t, Exception):
                raise t
            return t
        g["prod_bs_index_validate_saved_map"] = lambda bone_scales, snapshot: None
        g["prod_bs_index_trace"] = fake_trace
        cpm = types.ModuleType("q1_fake_cpm")
        for name in ("prod_bs_index_validate_saved_map", "prod_bs_bone_record_index", "prod_bs_index_trace",
                     "prod_bs_classify_static_scale", "close_enough"):
            setattr(cpm, name, g[name])
        try:
            def case(rows):
                """rows: [(bone, desired, classification, trace or Exception or None)]"""
                record = {"name": u"Body", "bone_scales": [{"bone_index": i, "bone_name": b, "value": d}
                                                           for i, (b, d, _, _) in enumerate(rows)]}
                index = {}
                for i, (b, d, cls, tr) in enumerate(rows):
                    key = (i, b.lower())
                    index[key] = {"classification": cls, "_key": key}
                    traces[key] = tr
                snapshot = {"bone_index": index}
                try:
                    cpm_result = g["prod_bs_index_verify_saved"](record, snapshot)
                    raised = False
                except Exception:
                    cpm_result, raised = None, True
                fm = ns["q1_full_map"](cpm, record, snapshot)
                return cpm_result, raised, fm
            ok_rows = [(u"bip_head", 1.33, u"CHANNEL_DRIVEN_SCALE", static_trace(1.33)),
                       (u"bip_tail00", 1.0, u"CHANNEL_DRIVEN_SCALE", static_trace(1.0)),
                       (u"bip_pelvis", 1.0, u"IMPLICIT_NEUTRAL", None)]
            cases = {
                "all pass": (ok_rows, True, None),
                "implicit neutral not 1": (ok_rows[:2] + [(u"bip_pelvis", 1.2, u"IMPLICIT_NEUTRAL", None)], False,
                                           u"implicit-neutral"),
                "other classification": (ok_rows[:2] + [(u"bip_neck", 1.0, u"PROCEDURAL", None)], False,
                                         u"classification"),
                "static trace fails": ([(u"bip_head", 1.33, u"CHANNEL_DRIVEN_SCALE", static_trace(1.33, False))] +
                                       ok_rows[1:], False, u"static"),
                "physical differs": ([(u"bip_head", 1.33, u"CHANNEL_DRIVEN_SCALE", static_trace(1.13))] +
                                     ok_rows[1:], False, u"physical"),
                "physical within EPSILON": ([(u"bip_head", 1.33, u"CHANNEL_DRIVEN_SCALE", static_trace(1.330009))] +
                                            ok_rows[1:], True, None),
            }
            for label, (rows, want, predicate) in sorted(cases.items()):
                cpm_result, raised, fm = case(rows)
                check("E %s: CPM's result %s and the observer's map agree, first failure %s" % (label, want, predicate),
                      not raised and cpm_result is want and fm["result"] is want and not fm["would_raise"] and
                      ((fm["first_failure"] or {}).get("predicate") == predicate) and
                      len(fm["bones"]) == len(rows), (cpm_result, fm["result"], fm["first_failure"]))
            cpm_result, raised, fm = case([(u"bip_head", 1.33, u"CHANNEL_DRIVEN_SCALE", RuntimeError("no output"))] +
                                          ok_rows[1:])
            check("E a trace error before any failure: CPM raises, the map says would_raise",
                  raised and fm["would_raise"] and fm["result"] is False and
                  fm["first_failure"]["predicate"] == u"trace-error", fm["first_failure"])
            cpm_result, raised, fm = case([(u"bip_head", 1.33, u"CHANNEL_DRIVEN_SCALE", static_trace(1.13))] +
                                          [(u"bip_tail00", 1.0, u"CHANNEL_DRIVEN_SCALE", RuntimeError("x"))])
            check("E a failure before a trace error: CPM returns False, the map records both and no would_raise",
                  not raised and cpm_result is False and fm["result"] is False and not fm["would_raise"] and
                  [b["predicate"] for b in fm["bones"]] == [u"physical", u"trace-error"], fm["bones"])
            _, _, fm = case([(u"bip_head", 1.33, u"CHANNEL_DRIVEN_SCALE", static_trace(1.13))])
            bone = fm["bones"][0]
            check("E the failing bone carries desired, physical, delta, static class and trace fields",
                  bone["desired"] == 1.33 and bone["physical"] == 1.13 and abs(bone["delta"] + 0.2) < 1e-9 and
                  bone["static"][0] is not None and bone["trace"]["physical_matches_lerp"] is True, bone)
        finally:
            g["prod_bs_index_validate_saved_map"], g["prod_bs_index_trace"] = saved_validate, saved_trace

        # W: the wrappers are transparent
        fake = types.ModuleType("q1_fake_cpm_hooks")
        calls = []

        def apply_(identity, record, scope=None, phase_callback=None, operation_context=None):
            calls.append("apply")
            if record.get("name") == u"boom":
                raise ValueError("apply failed")
            fake.same_time_refresh(5.0, "PROD_APPLY")
            return {"applied": record.get("name")}

        def authored(binding, snapshot, native_value):
            calls.append("authored")
            return native_value == 2.0

        def refresh(head_time, label):
            calls.append("refresh")
            return None

        def verify(record, snapshot):
            calls.append("verify")
            if record.get("name") == u"raise":
                raise KeyError("missing bone")
            return snapshot.get("ok")
        fake.prod_apply, fake.prod_bs_authored_matches = apply_, authored
        fake.same_time_refresh, fake.prod_bs_index_verify_saved = refresh, verify
        fake.prod_instance_token = lambda ctx: None
        fake.prod_instance_kw = lambda ctx: {}
        fake.prod_bs_index_snapshot = lambda identity, **kw: {"bone_index": {}}
        fake.prod_bs_index_validate_saved_map = lambda s, snap: None
        fake.prod_bs_bone_record_index = lambda record: {}
        fake.close_enough = g["close_enough"]
        originals = dict((n, getattr(fake, n)) for n in ns["Q1_HOOKED"])
        st = ns["q1_install"](fake)
        check("W install replaces exactly the four functions, each keeping its original",
              all(getattr(fake, n) is not originals[n] and getattr(fake, n).q1_original is originals[n]
                  for n in ns["Q1_HOOKED"]))
        check("W a second install is a no-op", ns["q1_install"](fake) is st and
              all(getattr(fake, n).q1_original is originals[n] for n in ns["Q1_HOOKED"]))
        result = fake.prod_apply({"model": u"m"}, {"name": u"Body", "kind": u"body", "bone_scales": []},
                                 operation_context=None)
        check("W prod_apply returns the original's result and the refresh ran inside it",
              result == {"applied": u"Body"} and calls == ["apply", "refresh"], (result, calls))
        kinds = [e["kind"] for e in st["events"]]
        check("W the operation, both refresh boundaries and the return are recorded in order",
              kinds == ["apply-begin", "refresh-before", "refresh-after", "apply-returned"], kinds)
        check("W authored and verify return the originals' results unchanged",
              fake.prod_bs_authored_matches({"bone_name": u"bip_head"}, {}, 2.0) is True and
              fake.prod_bs_authored_matches({"bone_name": u"bip_head"}, {}, 3.0) is False and
              fake.prod_bs_index_verify_saved({"name": u"Body", "bone_scales": []}, {"ok": True, "bone_index": {}})
              is True and
              fake.prod_bs_index_verify_saved({"name": u"Body", "bone_scales": []}, {"ok": False, "bone_index": {}})
              is False)
        for label, fn, exc_type, message in (
                ("prod_apply", lambda: fake.prod_apply({"model": u"m"}, {"name": u"boom", "kind": u"body"}),
                 ValueError, "apply failed"),
                ("prod_bs_index_verify_saved",
                 lambda: fake.prod_bs_index_verify_saved({"name": u"raise"}, {"bone_index": {}}), KeyError,
                 "missing bone")):
            try:
                fn()
                got = None
            except Exception as exc:
                got = (type(exc), str(exc).strip("'"), traceback.extract_tb(sys.exc_info()[2])[-1][2])
            check("W %s re-raises the original exception unchanged, with its own traceback" % label,
                  got is not None and got[0] is exc_type and got[1] == message and
                  got[2] in ("apply_", "verify"), got)
        check("W the raised operations are recorded", "apply-raised" in [e["kind"] for e in st["events"]] and
              "deferred-verify-raised" in [e["kind"] for e in st["events"]])
        check("W uninstall restores the exact original functions", ns["q1_uninstall"](fake) is True and
              all(getattr(fake, n) is originals[n] for n in ns["Q1_HOOKED"]) and
              getattr(fake, ns["Q1_STATE"], None) is None)
        try:
            window.close()
        except Exception:
            pass
    finally:
        r15._read = real_read
    passed = sum(1 for _, ok in RESULTS if ok)
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
