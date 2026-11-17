# -*- coding: ascii -*-
"""F-01 OT1S: the smoke observer's hooks on SFM's Python 2.7.5 (also runs on 3.10), against a fake CPM module. The
pinned OT1 and Q1 observers are loaded for real.

- S1: the OT1 observer is used only at its pinned SHA-256 and without running its capture.
- S2: install wraps the five OT1 recording hooks and the production guard; a second install is a no-op.
- S3: the guard hook passes the argument through, returns the result unchanged, re-raises an exception unchanged and
  records the bone and outcome; in a simulated Body Apply its events show the pre-transaction checks before the
  writes and each in-transaction check immediately before its bone's write.
- S4: the controlled-failure injector is never armed; uninstall restores the exact originals.
- S5: the observer makes no scene write, refresh, Undo or Operate call and writes only its exclusive-create capture.
They show nothing about SFM itself.

Usage: <SFM python 2.7.5> -E -B test_smoke_observer.py   (or python -I test_smoke_observer.py)
"""
from __future__ import print_function

import ast
import os
import re
import shutil
import sys
import tempfile
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(KIT))
OBSERVER = os.path.join(KIT, "observer", "F01_OT1S_Observe.py")
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def load():
    g = {"__name__": "ot1s_observer_under_test"}
    with open(OBSERVER, "rb") as f:
        exec(compile(f.read(), OBSERVER, "exec"), g)
    return g


class Refused(RuntimeError):
    pass


def fake_cpm(calls):
    cpm = types.ModuleType("fake_cpm")
    cpm.refuse = set()

    def prod_bs_expression_reference_guard(item):
        calls.append(("guard", item["bone_name"]))
        if item["bone_name"] in cpm.refuse:
            raise Refused("Bone %s scale expression is shared or ambiguous." % item["bone_name"])
        return True

    def prod_bs_write_existing_scale(item):
        calls.append(("write", item["bone_name"]))
        cpm.prod_bs_expression_reference_guard(item)   # inside the transaction, before Operate()
        return None

    def prod_apply(identity, record, scope=None, operation_context=None):
        for item in record["_items"]:                   # before StartUndo
            cpm.prod_bs_expression_reference_guard(item)
        for item in record["_items"]:
            cpm.prod_bs_write_existing_scale(item)
        cpm.same_time_refresh(0.2083, "PROD_APPLY")
        return {"phase": "verification-pending"}

    def same_time_refresh(head_time, label):
        return None

    def prod_bs_index_verify_saved(record, snapshot):
        return True

    def prod_verify_apply_abort_baseline(*a, **k):
        return True

    def prod_bs_snapshot(binding):
        return {"expr_result": 1.0, "physical_scale": 1.0}

    def prod_instance_token(context):
        return None

    for fn in (prod_bs_expression_reference_guard, prod_bs_write_existing_scale, prod_apply, same_time_refresh,
               prod_bs_index_verify_saved, prod_verify_apply_abort_baseline, prod_bs_snapshot, prod_instance_token):
        setattr(cpm, fn.__name__, fn)
    return cpm


def item(bone):
    return {"bone_name": bone, "desired_native": 0.1, "desired_physical": 1.0,
            "binding": {"identity": {"bone_name": bone}, "static_output_mode": 3}}


def main():
    print("Interpreter: %s" % sys.version.split()[0])
    s = load()
    try:
        o = s["ot1s_ot1"](REPO)
        q1 = o["ot1_q1"](REPO)
        check("S1 the pinned OT1 observer (and through it the Q1 observer) loads without running its capture",
              callable(o.get("ot1_install")) and callable(q1.get("q1_full_map")))
        tmp = tempfile.mkdtemp(prefix="ot1s_obs_")
        try:
            target = os.path.join(tmp, "real_sfm_qualification", "f01_ot1_ordering_trial", "observer")
            os.makedirs(target)
            with open(os.path.join(REPO, "real_sfm_qualification", "f01_ot1_ordering_trial", "observer",
                                   "F01_OT1_Observe.py"), "rb") as f:
                raw = f.read()
            with open(os.path.join(target, "F01_OT1_Observe.py"), "wb") as f:
                f.write(raw + b"\n# changed\n")
            try:
                s["ot1s_ot1"](tmp)
                refused = False
            except RuntimeError:
                refused = True
            check("S1 a changed OT1 observer is refused", refused)
        finally:
            shutil.rmtree(tmp)

        calls = []
        cpm = fake_cpm(calls)
        originals = dict((n, getattr(cpm, n)) for n in list(o["OT1_HOOKED"]) + [s["OT1S_GUARD"]])
        st = s["ot1s_install"](cpm, o, q1)
        check("S2 install wraps the five OT1 hooks and the production guard, keeping the originals",
              all(getattr(cpm, n) is not originals[n] for n in originals)
              and getattr(cpm, s["OT1S_GUARD"]).ot1s_original is originals[s["OT1S_GUARD"]])
        wrapped = getattr(cpm, s["OT1S_GUARD"])
        s["ot1s_install"](cpm, o, q1)
        check("S2 a second install is a no-op", getattr(cpm, s["OT1S_GUARD"]) is wrapped)

        record = {"name": u"Body", "kind": u"body", "_items": [item(u"bip_head"), item(u"bip_tail00")]}
        result = cpm.prod_apply({"model": u"m"}, record)
        kinds = [(e["kind"], e.get("bone")) for e in st["events"]]
        check("S3 a simulated Apply: result unchanged; pre-transaction guards first, each in-transaction guard "
              "immediately before its bone's write",
              result == {"phase": "verification-pending"} and kinds == [
                  ("apply-begin", None), ("reference-guard", u"bip_head"), ("reference-guard", u"bip_tail00"),
                  ("reference-guard", u"bip_head"), ("scale-write", u"bip_head"),
                  ("reference-guard", u"bip_tail00"), ("scale-write", u"bip_tail00"),
                  ("refresh-after", None), ("apply-returned", None)], kinds)
        check("S3 guard events record an accepted result",
              all(e["result"] is True and e["error"] is None for e in st["events"] if e["kind"] == "reference-guard"))
        cpm.refuse.add(u"bip_tail00")
        try:
            cpm.prod_bs_expression_reference_guard(item(u"bip_tail00"))
            got = None
        except Exception:
            got = sys.exc_info()
        inner = traceback.extract_tb(got[2])[-1] if got else None
        check("S3 a guard refusal is re-raised unchanged (type, message, innermost frame) and recorded",
              got is not None and got[0] is Refused and "shared or ambiguous" in str(got[1])
              and inner[2] == "prod_bs_expression_reference_guard"
              and st["events"][-1]["kind"] == "reference-guard" and st["events"][-1]["error"] is not None, inner)
        check("S4 the controlled-failure injector is never armed", st["armed"] is False and st["fired"] == 0)
        check("S4 uninstall restores the exact originals", s["ot1s_uninstall"](cpm, o) is True
              and all(getattr(cpm, n) is originals[n] for n in originals))

        with open(OBSERVER, "rb") as f:
            src_bytes = f.read()
        src = src_bytes.decode("ascii")
        called = set()
        for node in ast.walk(ast.parse(src_bytes)):
            if isinstance(node, ast.Call):
                fn = node.func
                called.add(fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None))
        forbidden = set(["SetValue", "SetKeyValue", "Operate", "StartUndo", "FinishUndo", "AbortUndoableOperation",
                         "Undo", "Redo", "ProcessEvents", "SetHeadTimeInSeconds", "same_time_refresh", "remove",
                         "unlink", "rename", "rmtree", "makedirs", "ot1_arm"])
        check("S5 no scene write, refresh, Undo, Operate, arming or file removal of its own",
              not called & forbidden, sorted(called & forbidden))
        opens = re.findall(r"(?<![\w.])open\(([^)]*)\)", src)
        check("S5 its only write is the exclusive-create capture", src.count("os.open(") == 1 and "O_EXCL" in src
              and opens == ['path, "rb"'] and "vsUtils" not in src, opens)
    except Exception:
        check("section.completed", False, traceback.format_exc())
    passed = sum(1 for r in RESULTS if r[1])
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
