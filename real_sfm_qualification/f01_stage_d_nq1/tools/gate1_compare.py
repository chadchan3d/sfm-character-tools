# -*- coding: utf-8 -*-
"""F-01 Stage D Gate 1 (preflight synchronization): offline verdict (Python 3, -I). Read-only outside <G>\\evidence.

usage: python -I gate1_compare.py <G>\\kp1.json
<G> holds the KP-1-style config and baseline (kp1_tool pre) and two entry states, each with its own single refresh:
  <G>\\A  ordinary timeline navigation     observations OBS-01 (pinned, before) and OBS-02 (after the one refresh)
  <G>\\B  after Graph Editor entry         observations OBS-01 and OBS-02, same meaning
For each state: same process, document, shot, Krystal instance, channels clip, playhead tick and mapped tick before and
after; one refresh made (marker), no history change, no authored change, rig inputs and skeleton (local and world)
unchanged within the established observation tolerances, and a unanimous effective channel clock afterwards. Across
states: the two effective clocks must be identical. Integrity: the R2/destination fixture, the session copy, the
installed CPM, the absent pose profile and the preset library are unchanged (kp1_tool baseline).
"""
from __future__ import print_function

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kp1_tool as K  # noqa: E402

WRITTEN = ("Hand_l.positionChannel", "Hand_l.orientationChannel", "Elbow_l.positionChannel")


def close(a, b, pos=1e-3, ang=1e-2):
    if a is None or b is None or len(a) != len(b):
        return False
    if len(a) == 4:
        na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
        return math.degrees(2 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(a, b))) / (na * nb)))) <= ang
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) <= pos


def state(g, name, c):
    d = os.path.join(g, name)
    problems, out = [], {}
    paths = [os.path.join(d, "observations", "OBS-%02d.json" % i) for i in (1, 2)]
    extra = sorted(os.listdir(os.path.join(d, "observations")))
    if extra != ["OBS-01.json", "OBS-02.json"]:
        return ["%s: expected exactly OBS-01 and OBS-02, found %s" % (name, extra)], out
    pre, post = (K.read_json(p) for p in paths)
    marker = os.path.join(d, "evidence", "FA1_REFRESH.json")
    if not os.path.isfile(marker):
        return ["%s: no refresh marker (the single request was not made)" % name], out
    ref = K.read_json(marker)
    for label, o in (("pinned", pre), ("after", post)):
        if o.get("problems"):
            problems.append("%s %s: observer problems %s" % (name, label, o["problems"]))
    if problems:
        return problems, out
    same = lambda k: pre[k] == post[k]  # noqa: E731
    checks = {
        "same_process": pre["pid"] == post["pid"] == ref["pid"],
        "document_is_session_copy": all(os.path.normcase(o["document"]).endswith("kp1_session.dmx") for o in (pre, post)),
        "same_shot_and_instance": same("current_shot") and same("animation_set_id") and pre["current_shot"] == c["shot"]
        and K.guid_raw(pre["animation_set_id"]) == c["animation_set_id"],
        "playhead_tick_pinned": pre["head_ticks"] == post["head_ticks"] == ref["head_ticks_before"]
        == ref["head_ticks_after"] == c["t_doc_ticks"],
        "refresh_without_error": ref["call"]["error"] is None,
        "mapped_tick_unchanged": pre["conversion"] == post["conversion"] and pre["conversion"]["t_chan"] == c[
            "cpm_time_ticks"],
        "history_unchanged": same("undo"),
        "authored_unchanged": all(pre["channels"][n]["layers"] == post["channels"][n]["layers"] for n in pre["channels"])
        and same("other_channels"),
        "rig_inputs_unchanged": all(close(pre["rig_inputs"][n], post["rig_inputs"][n], 1e-4, 1e-3) for n in WRITTEN),
        "skeleton_local_unchanged": all(close(v["position"], post["bones"][k]["position"]) and
                                        close(v["orientation"], post["bones"][k]["orientation"])
                                        for k, v in pre["bones"].items()),
        "skeleton_world_unchanged": all(close(v["position"], post["bones_world"][k]["position"]) and
                                        close(v["orientation"], post["bones_world"][k]["orientation"])
                                        for k, v in pre["bones_world"].items()),
        "placement_unchanged": same("model") and all(
            close(v, post["placement"][k]) for k, v in pre["placement"].items() if v is not None),
    }
    clocks_pre = sorted(set(v["clock"] for v in pre["rig_evaluated_at"].values()))
    clocks_post = sorted(set(v["clock"] for v in post["rig_evaluated_at"].values()))
    checks["effective_clock_unanimous"] = len(clocks_post) == 1
    out = {"checks": checks, "clock_before": clocks_pre, "clock_after": clocks_post,
           "mapped_tick": pre["conversion"]["t_chan"], "head_ticks": pre["head_ticks"],
           "undo": pre["undo"], "rig_at_clock_after": all(v["at_clock"] for v in post["rig_evaluated_at"].values())}
    if len(clocks_post) == 1:
        # The effective tick's document time through the verified stack (scale 1 in this fixture, as recorded).
        out["effective_document_tick"] = pre["head_ticks"] + (clocks_post[0] - pre["conversion"]["t_chan"])
    problems += ["%s: %s failed" % (name, k) for k, ok in sorted(checks.items()) if not ok]
    return problems, out


def main(argv):
    c = K.read_json(argv[1])
    g = os.path.dirname(os.path.abspath(argv[1]))
    if K.sfm_running():
        raise SystemExit("REFUSED: SFM is running; close it first")
    pre = K.read_json(os.path.join(g, "evidence", "pre.json"))
    now = K.state(c)
    now["session_sha256"] = K.sha(os.path.join(g, "sessions", "KP1_SESSION.dmx"))
    integrity = ["%s changed" % k for k in sorted(pre) if pre[k] != now.get(k)]
    problems, report = list(integrity), {}
    for name in ("A", "B"):
        p, r = state(g, name, c)
        problems += p
        report[name] = r
    if report.get("A", {}).get("clock_after") and report.get("B", {}).get("clock_after"):
        report["effective_clocks_identical"] = report["A"]["clock_after"] == report["B"]["clock_after"]
        report["entry_states_differed_before"] = report["A"]["clock_before"] != report["B"]["clock_before"]
        if not report["effective_clocks_identical"]:
            problems.append("the two entry states synchronized to different effective clocks %s / %s" % (
                report["A"]["clock_after"], report["B"]["clock_after"]))
    verdict = {"integrity_problems": integrity, "problems": problems, "report": report,
               "verdict": "GATE 1 PASS" if not problems else "GATE 1 STOP"}
    K.write_json(os.path.join(g, "evidence", "GATE1_VERDICT.json"), verdict)
    print(json.dumps({"verdict": verdict["verdict"], "problems": problems,
                      "clocks": dict((k, (v.get("clock_before"), v.get("clock_after"), v.get("effective_document_tick")))
                                     for k, v in report.items() if isinstance(v, dict))}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
