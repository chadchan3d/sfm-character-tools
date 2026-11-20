# -*- coding: utf-8 -*-
"""F-01 RC4: a REPLAY of the preserved native two-direction run under Astra's revised verification contract. Python 3,
-I, read-only on the run. It is not a native run and never replaces RC4X_VERDICT (the original, unchanged analyzer's
INCOMPLETE 129/132 stays the run's verdict). Writes Q/evidence/replay_revised_contract/RC4X_REPLAY.json and .md
(exclusive create).

The expectation is the saved record's own skeletal reference (pose.regions.full_body.oracle: every non-leaf bone,
placement-relative at capture), exactly what CPM's P7 composes with the destination's placement; it is never
computed from the adapter. The observation is SFM's evaluated skeleton in the captures (each bone relative to the
destination's own rig_root).

For each direction (A: RC4 Chest onto the original Tails; B: RC4 Sit onto Tails N) and each applied capture (APPLY,
NAV, REDO, NOOP), every oracle bone's evaluated transform is compared with the reference:
  - under the FORMER limits (0.001 units, 0.01 degrees): a self-check that the replay reproduces CPM's own original
    P7 decisions (A verified; B unverified on exactly the bones CPM logged);
  - under the REVISED reproduction envelope (0.01 units, 0.1 degrees, inclusive), with finite evidence required.
The repeat Apply (NOOP) is replayed from CPM's logged P1 plan: with every planned key present (no insert or update),
the revised contract gives a successful no-op that never opens Undo when the reproduction verifies.
Integrity items (authored keys, neighbouring keys, placement, history, Abort, peers) are taken from the unchanged
analyzer's checks, which do not depend on the reproduction limits.

usage: python -I rc4x_replay.py RC4X.json
"""
from __future__ import print_function

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_stage1_fox", "tools"))
sys.path.insert(0, HERE)
import s1f_analyze as A  # noqa: E402
import rc4x_analyze as X  # noqa: E402

FORMER = {"position": 0.001, "angle_degrees": 0.01}
REVISED = {"position": 0.01, "angle_degrees": 0.1}
STEPS = ("APPLY", "NAV", "REDO", "NOOP")
POLICY_DEPENDENT = ("log.no_unverified_uncertain_failed_abort_or_lockout_result", "apply.p7_verified_in_the_cpm_log",
                    "noop.reported_by_cpm_twice")


def finite(v, n):
    return isinstance(v, list) and len(v) == n and all(isinstance(c, (int, float)) and not isinstance(c, bool) and
                                                       not math.isnan(c) and not math.isinf(c) for c in v)


def compare(oracle, observed, limits):
    """Every reference bone: (failures, unreadable, maxima)."""
    fails, unreadable, worst = [], [], {"position": (0.0, None), "angle_degrees": (0.0, None)}
    for name, ref in sorted(oracle.items()):
        got = observed.get(name)
        if got is None or not (finite(list(got[0]), 3) and finite(list(got[1]), 4) and finite(ref["position"], 3)
                               and finite(ref["orientation"], 4)):
            unreadable.append(name)
            continue
        d, a = A.dist(got[0], ref["position"]), A.angle(got[1], ref["orientation"])
        if d > worst["position"][0]:
            worst["position"] = (d, name)
        if a > worst["angle_degrees"][0]:
            worst["angle_degrees"] = (a, name)
        if not (d <= limits["position"] and a <= limits["angle_degrees"]):
            fails.append(name)
    return fails, unreadable, worst


def logged_p7(lines):
    """CPM's own P7 results and P1 plans, in order (BODY route)."""
    out = []
    for l in lines:
        for tag in ("PROD_POSE_BODY-P7-verified", "PROD_POSE_BODY-P7-unverified", "PROD_POSE_BODY-P1"):
            if tag + " " in l:
                out.append((tag, A.log_json(l, tag)))
    return out


def run(c):
    R = X.Report(c)
    X.evaluate(R)                                   # the unchanged analyzer's checks, for the integrity items
    original = dict((x["id"] + "@" + x["gate"], x) for x in R.checks)
    records = X.saved_records(R)
    lines = A.logs(R)
    checks, info = [], {}

    def check(cid, ok, detail=None):
        checks.append({"id": cid, "pass": bool(ok), "detail": None if ok else detail})
    p7 = [x for x in logged_p7(lines) if x[0] != "PROD_POSE_BODY-P1"]
    p1 = [x[1] for x in logged_p7(lines) if x[0] == "PROD_POSE_BODY-P1"]
    for d, rec_name, src_role in (("A", X.CHEST, "source"), ("B", X.SIT, "target")):
        rec = records.get(rec_name) or {}
        oracle = ((((rec.get("pose") or {}).get("regions") or {}).get("full_body") or {}).get("oracle") or {}).get(
            "bones") or {}
        check("%s.record_reference_present" % d, len(oracle) > 100, len(oracle))
        info[d] = {}
        for step in STEPS:
            cap = R.cap.get("%s_%s" % (d, step))
            if cap is None:
                check("%s.%s_captured" % (d, step), False)
                continue
            observed = A.posture(cap, "target")
            former = compare(oracle, observed, FORMER)
            revised = compare(oracle, observed, REVISED)
            info[d][step] = {"former_failures": former[0], "revised_failures": revised[0],
                             "unreadable": revised[1], "max_position": revised[2]["position"],
                             "max_angle_degrees": revised[2]["angle_degrees"]}
            check("%s.%s_every_reference_bone_readable" % (d, step), not revised[1], revised[1][:8])
            check("%s.%s_reproduction_within_the_revised_envelope" % (d, step), not revised[0] and not revised[1],
                  info[d][step])
    # Self-check: the former limits reproduce CPM's own logged P7 decisions.
    logged = [(t, (x or {}).get("problems")) for t, x in p7]
    info["cpm_logged_p7"] = logged
    a_former = (info.get("A") or {}).get("APPLY", {}).get("former_failures")
    b_former = (info.get("B") or {}).get("APPLY", {}).get("former_failures")
    check("selfcheck.former_limits_reproduce_cpm_direction_a_verified", a_former == [] and logged and
          logged[0][0] == "PROD_POSE_BODY-P7-verified", (a_former, logged[:1]))
    b_logged = sorted(p.replace("bone ", "") for p in (logged[1][1] or [])) if len(logged) > 1 else None
    check("selfcheck.former_limits_reproduce_cpm_direction_b_bones", b_former is not None and sorted(b_former) ==
          b_logged and logged[1][0] == "PROD_POSE_BODY-P7-unverified", (b_former, b_logged))
    # The repeat Apply under the revised contract (every planned key present: no insert, no update).
    noops = [x for x in p1 if (x.get("actions") or {}).get("insert") == 0 and (x.get("actions") or {}).get(
        "update") == 0]
    info["repeat_apply_plans"] = [x.get("actions") for x in noops]
    for d in ("A", "B"):
        ok = not ((info.get(d) or {}).get("NOOP") or {}).get("revised_failures", ["missing"])
        check("%s.repeat_apply_is_a_no_work_no_op_under_the_revised_contract" % d, len(noops) == 2 and ok,
              info["repeat_apply_plans"])
    # Integrity items: the unchanged analyzer's checks that do not depend on the reproduction limits.
    integrity = [x for x in R.checks if x["id"] not in POLICY_DEPENDENT]
    failed = [x["gate"] + ":" + x["id"] for x in integrity if not x["pass"]]
    info["integrity_checks"] = len(integrity)
    check("integrity.every_policy_independent_check_of_the_original_analyzer_passes", not failed, failed)
    check("integrity.the_original_verdict_is_unchanged", A.opt_json(R.ev("RC4X_VERDICT.json")) is not None and
          (A.opt_json(R.ev("RC4X_VERDICT.json")) or {}).get("verdict") == "INCOMPLETE")
    verdict = "REPLAY PASS (revised contract)" if all(x["pass"] for x in checks) else "REPLAY FAIL (revised contract)"
    out = {"format": "F01-RC4X-replay-v1", "label": "REPLAY under Astra's revised verification contract; not a "
           "native run; the original verdict RC4X_VERDICT (INCOMPLETE) is unchanged", "verdict": verdict,
           "limits": {"former": FORMER, "revised": REVISED}, "checks": checks, "info": info,
           "replay_sha256": A.sha(os.path.abspath(__file__)), "original_analyzer_sha256": A.sha(os.path.join(
               HERE, "rc4x_analyze.py"))}
    lines_md = ["# F-01 RC4 native evidence, REPLAYED under the revised verification contract: %s" % verdict, "",
                "**Not a native run.** The run's verdict stays `RC4X_VERDICT` (INCOMPLETE, 129/132, unchanged).", "",
                "| Check | Result | Detail |", "|---|---|---|"]
    for x in checks:
        lines_md.append("| `%s` | %s | %s |" % (x["id"], "PASS" if x["pass"] else "**FAIL**", "" if x["pass"] else
                                                  json.dumps(x["detail"], default=repr)[:300].replace("|", "\\|")))
    lines_md += ["", "Info: `%s`" % json.dumps(info, default=repr)[:3000]]
    md = "\n".join(lines_md) + "\n"
    folder = R.ev("replay_revised_contract")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    for name, data in (("RC4X_REPLAY.json", json.dumps(out, indent=1, sort_keys=True, default=repr)),
                       ("RC4X_REPLAY.md", md)):
        fd = os.open(os.path.join(folder, name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(md)
    return 0 if verdict.startswith("REPLAY PASS") else 1


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    import rc4x_tool
    return run(rc4x_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
