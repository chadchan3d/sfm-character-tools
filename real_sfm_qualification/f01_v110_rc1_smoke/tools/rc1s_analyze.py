# -*- coding: utf-8 -*-
"""F-01 RC1S analyzer: the automated verdict of the v1.1.0 RC1 native release smoke, from the run's preserved
evidence only (read-only; writes Q/evidence/RC1S_VERDICT.json and .md, exclusive create).

Inputs: Q/staged/IDENTITIES.json (the RC1 build and its production-mode equivalence check), Q/evidence/seed.json,
Q/evidence/logs (the CPM's own diagnostic logs, one per SFM process), Q/evidence/library_cleanup.json and
library_after (the run's library changes), Q/evidence/restore.json.

Gates:
  EVIDENCE   the RC1 build staged and its equivalence check PASS; seeded; exactly two CPM logs, both written by the
             RC1 production CPM; the library and installation restored; the library changes are only the expected ones
  BODY       Process A: Apply Body Preset verified (committed-verified) on Krystal
  KRYSTAL    Process A: Save Pose verified on Krystal, its record "RC1 Krystal" version 2 full_body (krystal-v1);
             Process B: Apply Pose RC1 Krystal committed-verified on Krystal
  HEAVY      Process A: Save Pose verified on one Heavy, its record "RC1 Heavy" version 3 with engine direct_fk_v1
             revision 1 and no carried rule; Apply Pose RC1 Heavy committed-verified on a different Heavy
  SELECTED   Process B: Apply Pose NQ1 Pose A (Selected parts, version 1) on Krystal committed-verified or no-op
  DISPLAY    Pose Info opened three times (K2 Pose and NQ1 Pose A in Process A, RC1 Krystal in Process B)
  CLEAN      no operation outcome other than completed, verified or no-op, and no Apply phase other than
             committed-verified or no-op, in either process

Verdict: AUTOMATED SMOKE PASS when every gate passes; SMOKE FAIL when EVIDENCE passes and a functional gate fails;
INCOMPLETE otherwise. Release-smoke acceptance needs the automated PASS and the Owner's record (OWNER_SMOKE_RECORD.md),
reported side by side.
"""
from __future__ import print_function

import io
import json
import os
import re
import time

FORMAT = "F01-RC1S-verdict-v1"
KRYSTAL_POSE, HEAVY_POSE, LEGACY_POSE_NAME = u"RC1 Krystal", u"RC1 Heavy", u"NQ1 Pose A"
OK_OUTCOMES = ("completed", "verified", "no-op")
OK_PHASES = ("committed-verified", "no-op")

RE_HEADER = re.compile(r"diagnostic log cpm-log-v1 \| build_sha256=([0-9a-f]{64})")
RE_BEGIN = re.compile(r"\| PROD_OPERATION_BEGIN id=(\d+) kind=u'([^']*)' context=(.*)$")
RE_ANIMSET = re.compile(r"'animset_id': \(u'DmeAnimationSet', u'([^']*)'")
RE_LABEL = re.compile(r"\| PROD_OPERATION_PHASE id=(\d+) phase=u'native-commit' detail=\{u'label': u'([^']*)'\}")
RE_OUTCOME = re.compile(r"\| PROD_OPERATION_OUTCOME id=(\d+) kind=u'([^']*)' outcome=u'([^']*)' detail=(.*)$")
RE_APPLY_PHASE = re.compile(r"'apply_phase': u'([^']*)'")
RE_PRESET = re.compile(r"'preset_id': u'([0-9a-f]+)'")


def read_json(path):
    with io.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def parse_log(path):
    """(build_sha256, [operation dicts in id order])."""
    build, ops = None, {}
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            m = RE_HEADER.search(line)
            if m and build is None:
                build = m.group(1)
            m = RE_BEGIN.search(line)
            if m:
                a = RE_ANIMSET.search(m.group(3))
                ops[int(m.group(1))] = {"id": int(m.group(1)), "kind": m.group(2),
                                        "animset": a.group(1) if a else None, "label": None,
                                        "outcome": None, "apply_phase": None, "preset_id": None}
                continue
            m = RE_LABEL.search(line)
            if m and int(m.group(1)) in ops:
                ops[int(m.group(1))]["label"] = m.group(2)
                continue
            m = RE_OUTCOME.search(line)
            if m:
                op = ops.setdefault(int(m.group(1)), {"id": int(m.group(1)), "kind": m.group(2), "animset": None,
                                                      "label": None, "outcome": None, "apply_phase": None,
                                                      "preset_id": None})
                op["outcome"] = m.group(3)
                p = RE_APPLY_PHASE.search(m.group(4))
                op["apply_phase"] = p.group(1) if p else None
                p = RE_PRESET.search(m.group(4))
                op["preset_id"] = p.group(1) if p else None
    return build, [ops[k] for k in sorted(ops)]


class Run(object):
    def __init__(self, c):
        self.c = c
        self.q = c["paths"]["Q"]
        self.ev = os.path.join(self.q, "evidence")
        self.checks = []

    def check(self, gate, name, ok, detail=None):
        self.checks.append({"gate": gate, "check": name, "pass": bool(ok), "detail": detail})
        return bool(ok)

    def load(self, *parts):
        path = os.path.join(self.q, *parts)
        return read_json(path) if os.path.isfile(path) else None

    # --- evidence ------------------------------------------------------------------------------------------------
    def evidence(self):
        pins = self.c["pins"]
        ids = self.load("staged", "IDENTITIES.json") or {}
        self.check("EVIDENCE", "rc1_build_staged", ids.get("qualification_cpm_sha256") == pins["rc1_cpm_sha256"] and
                   ids.get("body_profile_sha256") == pins["body_profile_sha256"] and
                   ids.get("profile_sha256") == pins["profile_sha256"], ids.get("qualification_cpm_sha256"))
        modes = ids.get("mode_equivalence") or {}
        self.check("EVIDENCE", "production_mode_equivalence", modes.get("pass") is True,
                   dict((k, modes.get(k)) for k in ("production", "generic_v3", "carried", "krystal_v2",
                                                     "left_arm", "only_unqualified")))
        self.check("EVIDENCE", "seeded", self.load("evidence", "seed.json") is not None)
        logs = self.load("evidence", "logs", "LOGS.json") or {"files": {}}
        names = sorted(logs["files"])
        self.processes = []
        for name in names:
            build, ops = parse_log(os.path.join(self.ev, "logs", name))
            self.processes.append({"log": name, "build": build, "ops": ops})
        self.check("EVIDENCE", "two_cpm_logs", len(names) == 2, names)
        self.check("EVIDENCE", "logs_written_by_rc1", bool(names) and
                   all(p["build"] == pins["rc1_cpm_sha256"] for p in self.processes),
                   [p["build"] for p in self.processes])
        restore = self.load("evidence", "restore.json") or {}
        self.check("EVIDENCE", "installation_restored", restore.get("restored") is True and
                   restore.get("installation") == "published", restore.get("installation"))
        cleanup = self.load("evidence", "library_cleanup.json") or {}
        self.check("EVIDENCE", "library_restored", cleanup.get("files_equal_pre") is True and
                   cleanup.get("folders_equal_pre") is True)
        self.diffs = cleanup.get("differences_kept_in_evidence")
        unexpected = self.unexpected_library(self.diffs or [])
        self.check("EVIDENCE", "library_changes_expected", self.diffs is not None and not unexpected, unexpected)
        return all(x["pass"] for x in self.checks if x["gate"] == "EVIDENCE")

    def unexpected_library(self, diffs):
        pins, kd, hd = self.c["pins"], self.c["character_dir"], self.c["heavy_dir"]
        self.records = {}
        out = []
        for d in diffs:
            path, status = d["path"], d["status"]
            ok = False
            if path == "Characters/%s/Poses/K2 Pose--ac9d4962a2ae.json" % kd:
                ok = status == "added" and d["sha256"] == pins["k2_pose_sha256"]
            elif path == "Characters/%s/Poses/NQ1 Pose A--5273df2209ca.json" % kd:
                ok = status == "added" and d["sha256"] == pins["legacy_pose_sha256"]
            elif re.match(r"^Characters/%s/Poses/RC1 Krystal--[0-9a-f]{12}\.json$" % re.escape(kd), path):
                ok = status == "added" and "krystal" not in self.records
                self.records["krystal"] = path
            elif re.match(r"^Characters/%s/Poses/RC1 Heavy--[0-9a-f]{12}\.json$" % re.escape(hd), path):
                ok = status == "added" and "heavy" not in self.records
                self.records["heavy"] = path
            elif path in ("Characters/%s/pose_sources.json" % kd, "Characters/%s/pose_sources.json" % hd):
                ok = status in ("added", "changed")
            elif path in ("Characters/%s/character.json" % kd, "Characters/%s/character.json" % hd):
                ok = status in ("added", "changed")       # CPM's own character file (known rewrite)
            if not ok:
                out.append(d)
        return out

    def record(self, which):
        path = self.records.get(which)
        full = os.path.join(self.ev, "library_after", *path.split("/")) if path else None
        return read_json(full) if full and os.path.isfile(full) else None

    # --- functional gates ----------------------------------------------------------------------------------------
    def ops(self, index, kind=None):
        if index >= len(self.processes):
            return []
        return [o for o in self.processes[index]["ops"] if kind is None or o["kind"] == kind]

    def functional(self):
        a_saves = self.ops(0, "Save Pose")
        kr = self.record("krystal")
        hv = self.record("heavy")
        kr_save = [o for o in a_saves if kr and o["outcome"] == "verified" and o["preset_id"] == kr["preset_id"]]
        hv_save = [o for o in a_saves if hv and o["outcome"] == "verified" and o["preset_id"] == hv["preset_id"]]
        krystal = kr_save[0]["animset"] if kr_save else None

        body = [o for o in self.ops(0, "Apply Body Preset") if o["outcome"] == "verified" and
                o["apply_phase"] == "committed-verified"]
        self.check("BODY", "body_preset_applied_on_krystal", len(body) == 1 and krystal is not None and
                   body[0]["animset"] == krystal, [(o["animset"], o["outcome"]) for o in self.ops(0, "Apply Body Preset")])

        pose = (kr or {}).get("pose") or {}
        self.check("KRYSTAL", "saved_in_process_a", len(kr_save) == 1, [(o["animset"], o["outcome"]) for o in a_saves])
        self.check("KRYSTAL", "record_is_version_2_full_body",
                   kr is not None and kr.get("name") == KRYSTAL_POSE and pose.get("version") == 2 and
                   sorted((pose.get("regions") or {}).keys()) == ["full_body"] and
                   (pose.get("source") or {}).get("rig_class") == "krystal-v1",
                   {"version": pose.get("version"), "regions": sorted((pose.get("regions") or {}).keys())})
        kb = [o for o in self.ops(1, "Apply Pose") if o["label"] == u"Apply Pose %s" % KRYSTAL_POSE]
        self.check("KRYSTAL", "applied_in_process_b", len(kb) >= 1 and kb[0]["animset"] == krystal and
                   kb[0]["outcome"] == "verified" and kb[0]["apply_phase"] == "committed-verified",
                   [(o["animset"], o["outcome"], o["apply_phase"]) for o in kb])

        hpose = (hv or {}).get("pose") or {}
        source = hv_save[0]["animset"] if hv_save else None
        self.check("HEAVY", "saved_in_process_a", len(hv_save) == 1)
        self.check("HEAVY", "record_is_generic_v3", hv is not None and hv.get("name") == HEAVY_POSE and
                   hpose.get("version") == 3 and hpose.get("engine") == {"rule": "direct_fk_v1", "revision": 1,
                                                                         "carried_rule": None},
                   {"version": hpose.get("version"), "engine": hpose.get("engine")})
        ha = [o for o in self.ops(0, "Apply Pose") if o["label"] == u"Apply Pose %s" % HEAVY_POSE]
        self.check("HEAVY", "applied_to_another_heavy", len(ha) >= 1 and source is not None and
                   ha[0]["animset"] not in (None, source, krystal) and ha[0]["outcome"] == "verified" and
                   ha[0]["apply_phase"] == "committed-verified",
                   [(o["animset"], o["outcome"], o["apply_phase"]) for o in ha])

        b_applies = self.ops(1, "Apply Pose")
        sel = [o for o in b_applies if o["label"] in (None, u"Apply Pose %s" % LEGACY_POSE_NAME) and
               o not in kb]
        self.check("SELECTED", "selected_parts_applied_in_process_b",
                   len(sel) == 1 and sel[0]["animset"] == krystal and
                   ((sel[0]["outcome"] == "verified" and sel[0]["apply_phase"] == "committed-verified" and
                     sel[0]["label"] == u"Apply Pose %s" % LEGACY_POSE_NAME) or
                    (sel[0]["outcome"] == "no-op" and sel[0]["apply_phase"] == "no-op")),
                   [(o["animset"], o["label"], o["outcome"]) for o in b_applies])

        infos = [len([o for o in self.ops(i, "Pose Info") if o["outcome"] == "completed"]) for i in (0, 1)]
        self.check("DISPLAY", "pose_info_opened", infos[0] >= 2 and infos[1] >= 1, infos)

        bad = [(p["log"], o["id"], o["kind"], o["outcome"], o["apply_phase"]) for p in self.processes
               for o in p["ops"] if o["outcome"] not in OK_OUTCOMES or
               (o["apply_phase"] is not None and o["apply_phase"] not in OK_PHASES)]
        self.check("CLEAN", "no_refusal_failure_or_recovery", not bad, bad)


def verdict(R):
    evidence = all(x["pass"] for x in R.checks if x["gate"] == "EVIDENCE")
    functional = all(x["pass"] for x in R.checks if x["gate"] != "EVIDENCE")
    if evidence and functional:
        return "AUTOMATED SMOKE PASS"
    if evidence:
        return "SMOKE FAIL"
    return "INCOMPLETE"


def render(result):
    lines = ["# F-01 v1.1.0 RC1 native release smoke: automated verdict", "",
             "**%s** (%d/%d checks)" % (result["verdict"], result["passed"], result["total"]), "",
             "Release-smoke acceptance also needs the Owner's record (`owner_review/OWNER_SMOKE_RECORD.md`), "
             "reported beside this verdict; neither replaces the other.", "",
             "| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in result["checks"]:
        detail = json.dumps(x["detail"], sort_keys=True) if x["detail"] is not None else ""
        lines.append("| %s | %s | %s | %s |" % (x["gate"], x["check"], "PASS" if x["pass"] else "FAIL",
                                               detail.replace("|", "/")[:300]))
    return "\n".join(lines) + "\n"


def run(c):
    R = Run(c)
    out_json = os.path.join(R.ev, "RC1S_VERDICT.json")
    out_md = os.path.join(R.ev, "RC1S_VERDICT.md")
    for path in (out_json, out_md):
        if os.path.lexists(path):
            raise SystemExit("REFUSED: %s exists" % path)
    R.evidence()
    R.functional()
    result = {"format": FORMAT, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "verdict": verdict(R),
              "passed": sum(1 for x in R.checks if x["pass"]), "total": len(R.checks), "checks": R.checks,
              "processes": [{"log": p["log"], "build": p["build"],
                             "operations": [dict((k, o[k]) for k in ("id", "kind", "animset", "label", "outcome",
                                                                      "apply_phase")) for o in p["ops"]
                                            if o["kind"] not in ("Refresh Models", "Select Model")]}
                            for p in R.processes]}
    with io.open(out_json, "x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(result, indent=1, sort_keys=True) + "\n")
    with io.open(out_md, "x", encoding="utf-8", newline="\n") as f:
        f.write(render(result))
    print("%s (%d/%d). Written: %s" % (result["verdict"], result["passed"], result["total"], out_md))
    return 0 if result["verdict"] == "AUTOMATED SMOKE PASS" else 1


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rc1s_tool
    sys.exit(rc1s_tool.main([sys.argv[0], sys.argv[1], "analyze"]) if len(sys.argv) == 2 else 2)
