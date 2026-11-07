# -*- coding: utf-8 -*-
"""F-01 full-body S3: the read-only A1 compatibility pre-check before Apply (Process B, after B1). Python 3, -I.

It runs the staged qualification CPM's own P1 compatibility code (stage E: descriptor, revised A1, effective inputs,
plan) on the native B1 observation and the saved pose record, offline. It never touches SFM, the installation or
the scene; its only write is Q/evidence/A1_PRECHECK.json (exclusive create). The observation is converted with the
same derivation as the committed S0 fixtures (cpm/convergence/tests/f01_body_fixture.py), and the stage E block is
extracted from the staged CPM by the committed test harness.

usage: python -I s3_precheck.py QUALIFICATION_CPM OBSERVATION RECORD OUT.json
"""
from __future__ import print_function

import collections
import contextlib
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TESTS = os.path.join(REPO, "cpm", "convergence", "tests")


def precheck(app_path, observation_path, record_path):
    os.environ["CPM_TEST_APP_PATH"] = app_path       # read by the harness at import: the staged qualification CPM
    if TESTS not in sys.path:
        sys.path.insert(0, TESTS)
    saved_argv = sys.argv
    sys.argv = ["s3_precheck"]
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink):
            import test_cpm_app_canonical_route as route
            import test_cpm_app_f01_body as B
            import f01_body_fixture as FX
            if os.path.normcase(os.path.abspath(route.APP_PATH)) != os.path.normcase(os.path.abspath(app_path)):
                raise RuntimeError("the harness did not load the staged qualification CPM")
            with open(observation_path, "rb") as f:
                raw = f.read()
            obs = json.loads(raw.decode("utf-8"))
            if obs.get("problems") or not (obs.get("readonly") or {}).get("unchanged"):
                raise RuntimeError("the observation is not a valid read-only observation")
            D = FX.derive(obs, hashlib.sha256(raw).hexdigest())
            with open(record_path, "rb") as f:
                record = json.loads(f.read().decode("utf-8"))
            region = record["pose"]["regions"]["full_body"]
            ns = B.build_namespace(route.AppSource(route.APP_PATH))
            reg = B.registries(ns)[0]
            profile = B.profile_of(ns, reg)
            C = ns["prod_body_classify"](D, profile)
    finally:
        sys.argv = saved_argv
    out = collections.OrderedDict()
    out["qualification_cpm_sha256"] = hashlib.sha256(open(app_path, "rb").read()).hexdigest()
    out["observation"] = {"label": obs.get("label"), "pid": obs.get("pid"),
                          "sha256": hashlib.sha256(raw).hexdigest()}
    out["record"] = {"name": record.get("name"), "sha256": hashlib.sha256(open(record_path, "rb").read()).hexdigest()}
    out["written_channels"] = len(C["written"])

    def step(name, fn):
        try:
            value = fn()
            out[name] = "ok"
            return value
        except Exception as exc:
            out[name] = "REFUSED %s: %s" % (getattr(exc, "code", type(exc).__name__), exc)
            return None

    step("descriptor", lambda: ns["prod_body_compare_descriptor"](region["descriptor"],
                                                                   ns["prod_body_descriptor"](D, C, profile)))
    pinned = step("revised_A1", lambda: ns["prod_body_check_fk_positions"](region, D, C, profile))
    step("effective_inputs", lambda: ns["prod_body_effective_inputs"](D, C, profile))
    plans = None
    if pinned is not None:
        out["pinned"] = len(pinned)
        out["pinned_differing_from_saved"] = dict(
            (n, {"saved": region["positions"][n], "kept_destination": pinned[n],
                 "distance": ns["prod_body_fk_distance"](region["positions"][n], pinned[n])})
            for n in sorted(pinned) if list(pinned[n]) != list(region["positions"][n]))
        plans = step("plan", lambda: ns["prod_body_plan"](region, D, C, B.snapshots(D, C["written"]), D["t_chan"],
                                                          pinned))
    if plans:
        out["plan_actions"] = dict(collections.Counter(p["action"] for p in plans))
        values = dict((p["name"], p["value"]) for p in plans)
        out["fk_plans_keep_destination_values"] = all(values[n] == pinned[n] for n in pinned)
    out["compatible"] = all(out.get(k) == "ok" for k in ("descriptor", "revised_A1", "effective_inputs", "plan")) \
        and out.get("fk_plans_keep_destination_values") is True
    return out


def main(argv):
    if len(argv) != 5:
        print(__doc__)
        return 2
    result = precheck(argv[1], argv[2], argv[3])
    if os.path.lexists(argv[4]):
        raise SystemExit("REFUSED: %s exists" % argv[4])
    fd = os.open(argv[4], os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(result, indent=1).encode("utf-8"))
    print(json.dumps(result, indent=1))
    print("PRECHECK COMPATIBLE: Apply may proceed (B2)" if result["compatible"] else
          "PRECHECK INCOMPATIBLE: do not Apply; close SFM without saving and run restore")
    return 0 if result["compatible"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
