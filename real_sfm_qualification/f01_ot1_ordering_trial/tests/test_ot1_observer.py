# -*- coding: ascii -*-
"""F-01 OT1: the observer's hooks and controlled failure on SFM's Python 2.7.5 (also runs on 3.10), against a fake CPM
module (the five hooked functions and prod_bs_snapshot as plain functions). The pinned Q1 observer is loaded for real.

- W: each wrapper calls the original with the same arguments, returns its result unchanged, re-raises its exception
  unchanged (type, message and the original's innermost frame), records its event; install is idempotent; uninstall
  restores the exact originals and disarms.
- J: the controlled failure fires at most once, only when armed, only after CPM's write of the armed bone returned
  normally (never when that write raised), and raises the pinned text from inside the wrapper.
- L: the Q1 observer is used only at its pinned SHA-256; the observer's source makes no scene write, refresh, event
  pumping, Undo or Operate call of its own, and its only file write is the exclusive-create capture.
They show nothing about SFM itself.

Usage: <SFM python 2.7.5> -E -B test_ot1_observer.py   (or python -I test_ot1_observer.py)
"""
from __future__ import print_function

import ast
import os
import shutil
import sys
import tempfile
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(KIT))
OBSERVER = os.path.join(KIT, "observer", "F01_OT1_Observe.py")
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def load_observer():
    g = {"__name__": "ot1_observer_under_test"}
    with open(OBSERVER, "rb") as f:
        exec(compile(f.read(), OBSERVER, "exec"), g)
    return g


class Boom(ValueError):
    pass


def fake_cpm(calls):
    cpm = types.ModuleType("fake_cpm")
    state = {"physical": {"bip_head": 1.13, "bip_tail00": 0.8}, "result": {"bip_head": 1.13, "bip_tail00": 0.8},
             "raise": set()}
    cpm.state = state

    def prod_apply(identity, record, scope=None, operation_context=None):
        calls.append(("prod_apply", identity, record, scope, operation_context))
        if "apply" in state["raise"]:
            raise Boom("apply failed")
        for item in record.get("_items", []):
            cpm.prod_bs_write_existing_scale(item)
        cpm.same_time_refresh(0.2083, "PROD_APPLY")
        return {"phase": "verification-pending"}

    def prod_bs_write_existing_scale(item):
        calls.append(("write", item["bone_name"]))
        if item["bone_name"] in state["raise"]:
            raise Boom("write failed %s" % item["bone_name"])
        state["result"][item["bone_name"]] = item["desired_physical"]
        return "write-result-%s" % item["bone_name"]

    def same_time_refresh(head_time, label):
        calls.append(("refresh", head_time, label))
        for bone in state["result"]:
            state["physical"][bone] = state["result"][bone]
        return "refreshed"

    def prod_bs_index_verify_saved(record, snapshot):
        calls.append(("verify", record.get("name")))
        return True

    def prod_verify_apply_abort_baseline(*args, **kwargs):
        calls.append(("abort-verify", args, kwargs))
        return True

    def prod_bs_snapshot(binding):
        bone = binding["identity"]["bone_name"]
        return {"source": 0.1, "key_value": 0.1, "key_count": 1, "expr_input": 0.1,
                "expr_result": state["result"][bone], "physical_scale": state["physical"][bone], "output_mode": 3,
                "expression_id": ["E", bone], "unlisted": "not recorded"}

    def prod_instance_token(context):
        return None

    for fn in (prod_apply, prod_bs_write_existing_scale, same_time_refresh, prod_bs_index_verify_saved,
               prod_verify_apply_abort_baseline, prod_bs_snapshot, prod_instance_token):
        setattr(cpm, fn.__name__, fn)
    return cpm


def item(bone, desired):
    return {"bone_name": bone, "desired_native": desired / 10.0, "desired_physical": desired,
            "binding": {"identity": {"bone_name": bone}, "static_output_mode": 3}}


def kinds(st):
    return [e["kind"] for e in st["events"]]


def section_wrappers(o, q1):
    calls = []
    cpm = fake_cpm(calls)
    originals = dict((n, getattr(cpm, n)) for n in o["OT1_HOOKED"])
    st = o["ot1_install"](cpm, q1)
    check("W1 install wraps exactly the five functions and keeps the originals",
          all(getattr(cpm, n) is not originals[n] and getattr(cpm, n).ot1_original is originals[n]
              for n in o["OT1_HOOKED"]) and st["originals"] == originals)
    check("W1 a second install is a no-op", o["ot1_install"](cpm, q1) is st
          and all(getattr(cpm, n).ot1_original is originals[n] for n in o["OT1_HOOKED"]))

    record = {"name": u"Body", "kind": u"body", "_items": [item(u"bip_head", 1.33), item(u"bip_tail00", 1.0)]}
    result = cpm.prod_apply({"model": u"m"}, record, scope="S", operation_context="CTX")
    check("W2 prod_apply: same arguments, result unchanged",
          result == {"phase": "verification-pending"} and calls[0] == ("prod_apply", {"model": u"m"}, record, "S", "CTX"))
    check("W2 events in CPM order: apply-begin, two scale writes, refresh, apply-returned",
          kinds(st) == ["apply-begin", "scale-write", "scale-write", "refresh-after", "apply-returned"], kinds(st))
    w = [e for e in st["events"] if e["kind"] == "scale-write"]
    check("W3 scale write: before read precedes CPM's write, after read follows it (CPM's own snapshot fields only)",
          w[0]["bone"] == u"bip_head" and w[0]["before"]["expr_result"] == 1.13 and w[0]["after"]["expr_result"] == 1.33
          and w[0]["after"]["physical_scale"] == 1.13 and "unlisted" not in w[0]["after"]
          and w[0]["desired_physical"] == 1.33 and w[0]["static_output_mode"] == 3, w[0])
    r = [e for e in st["events"] if e["kind"] == "refresh-after"][0]
    check("W4 refresh: read only after CPM's refresh, only the scales this operation wrote",
          r["label"] == u"PROD_APPLY" and [x["bone"] for x in r["scales"]] == [u"bip_head", u"bip_tail00"]
          and r["scales"][0]["after"]["physical_scale"] == 1.33, r)
    check("W5 deferred verify and abort verify: result unchanged and recorded",
          cpm.prod_bs_index_verify_saved({"name": u"Body"}, {}) is True
          and cpm.prod_verify_apply_abort_baseline(1, k=2) is True
          and [e["kind"] for e in st["events"]][-2:] == ["deferred-verify", "abort-verify"]
          and st["events"][-1]["result"] is True and calls[-1] == ("abort-verify", (1,), {"k": 2}))

    cpm.state["raise"].add("apply")
    try:
        cpm.prod_apply({"model": u"m"}, {"name": u"Body", "kind": u"body"})
        got = None
    except Exception:
        got = sys.exc_info()
    inner = traceback.extract_tb(got[2])[-1] if got else None
    check("W6 an exception is re-raised unchanged (type, message, the original's innermost frame)",
          got is not None and got[0] is Boom and str(got[1]) == "apply failed" and inner[2] == "prod_apply"
          and st["events"][-1]["kind"] == "apply-raised", inner)
    cpm.state["raise"].discard("apply")
    check("W7 uninstall restores the exact originals", o["ot1_uninstall"](cpm) is True
          and all(getattr(cpm, n) is originals[n] for n in o["OT1_HOOKED"]) and o["ot1_state"](cpm) is None)


def section_injection(o, q1):
    calls = []
    cpm = fake_cpm(calls)
    st = o["ot1_install"](cpm, q1)
    record = {"name": u"Body", "kind": u"body", "_items": [item(u"bip_head", 1.33), item(u"bip_tail00", 1.0)]}
    cpm.prod_apply({}, record)
    check("J1 not armed: nothing injected", "injected-failure" not in kinds(st) and st["fired"] == 0)
    del st["events"][:]
    st["armed"] = True
    try:
        cpm.prod_apply({}, record)
        got = None
    except Exception as exc:
        got = exc
    check("J2 armed: CPM's tail write ran and returned, then the pinned failure is raised from the wrapper",
          isinstance(got, RuntimeError) and str(got) == o["OT1_FAIL_TEXT"]
          and ("write", u"bip_tail00") in calls[-3:] and cpm.state["result"][u"bip_tail00"] == 1.0, (got, calls[-3:]))
    check("J2 events: head write, tail write, injected failure, apply-raised (no refresh: the failure precedes it)",
          kinds(st) == ["apply-begin", "scale-write", "scale-write", "injected-failure", "apply-raised"], kinds(st))
    check("J3 fired once and disarmed", st["fired"] == 1 and st["armed"] is False)
    cpm.prod_apply({}, record)
    check("J3 a later Apply is not injected", st["fired"] == 1 and kinds(st)[-1] == "apply-returned")

    st["armed"], st["fired"] = True, 0
    cpm.state["raise"].add(u"bip_tail00")
    try:
        cpm.prod_apply({}, record)
        got = None
    except Exception as exc:
        got = exc
    check("J4 when CPM's own write raises, its exception propagates and nothing is injected",
          isinstance(got, Boom) and st["fired"] == 0 and st["armed"] is True
          and "scale-write-raised" in kinds(st), (got, kinds(st)[-4:]))
    o["ot1_uninstall"](cpm)
    check("J5 uninstall disarms", st["armed"] is False)


def section_static(o):
    tmp = tempfile.mkdtemp(prefix="ot1_obs_")
    try:
        target = os.path.join(tmp, "real_sfm_qualification", "f01_q1_ps2_diagnostic", "observer")
        os.makedirs(target)
        with open(os.path.join(REPO, "real_sfm_qualification", "f01_q1_ps2_diagnostic", "observer",
                               "F01_Q1_Observe.py"), "rb") as f:
            raw = f.read()
        with open(os.path.join(target, "F01_Q1_Observe.py"), "wb") as f:
            f.write(raw + b"\n# changed\n")
        try:
            o["ot1_q1"](tmp)
            refused = False
        except RuntimeError:
            refused = True
        check("L1 a changed Q1 observer is refused", refused)
    finally:
        shutil.rmtree(tmp)
    with open(OBSERVER, "rb") as f:
        tree = ast.parse(f.read())
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            called.add(fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None))
    forbidden = set(["SetValue", "SetKeyValue", "Operate", "StartUndo", "FinishUndo", "AbortUndoableOperation",
                     "Undo", "Redo", "ProcessEvents", "SetHeadTimeInSeconds", "same_time_refresh", "singleShot",
                     "remove", "unlink", "rename", "rmtree", "makedirs"])
    check("L2 the observer makes no scene write, refresh, pumping, Undo, Operate or file removal of its own",
          not called & forbidden, sorted(called & forbidden))
    with open(OBSERVER, "rb") as f:
        src = f.read().decode("ascii")
    import re
    builtin_opens = re.findall(r"(?<![\w.])open\(([^)]*)\)", src)
    check("L3 its only file write is the exclusive-create capture (one os.open with O_EXCL; builtin open read-only)",
          src.count("os.open(") == 1 and "O_EXCL" in src and builtin_opens == ['path, "rb"'], builtin_opens)


def main():
    print("Interpreter: %s" % sys.version.split()[0])
    o = load_observer()
    q1 = o["ot1_q1"](REPO)
    check("L0 the pinned Q1 observer loads without running its capture", callable(q1.get("q1_full_map")))
    for section in (lambda: section_wrappers(o, q1), lambda: section_injection(o, q1), lambda: section_static(o)):
        try:
            section()
        except Exception:
            check("section.completed", False, traceback.format_exc())
    passed = sum(1 for r in RESULTS if r[1])
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
