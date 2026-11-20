# -*- coding: utf-8 -*-
"""F-01 RC3S analyzer: the automated verdict of the v1.1.0 RC3 native release smoke (Fox and Tails Full body in a
normal installation), from the run's preserved evidence only (read-only; writes Q/evidence/RC3S_VERDICT.json and .md,
exclusive create). It reuses the RC1S analyzer's CPM log parser unchanged.

Inputs: Q/staged/IDENTITIES.json (the RC3 build and its production-mode check), Q/evidence/logs (the CPM's own
diagnostic log of the one SFM process), Q/evidence/library_cleanup.json and library_after (the run's library changes),
Q/evidence/restore.json.

Gates:
  EVIDENCE   the RC3 build staged and its production-mode check PASS (the structural adapter usable in production,
             no qualification-only switch); exactly one CPM log, written by the RC3 production CPM; the library and
             installation restored; the library changes are only the two saved poses and CPM's own character files
  FOX        Save Pose verified on one fresh Fox, admitted by the structural adapter (logged, no simulated leaves); the
             record "RC3 Fox" is version 2 with adapter structural_rig_v1 revision 1 for the Fox model; Apply Pose
             RC3 Fox committed-verified
  TAILS      the same for one fresh Tails: logged admission with exactly the seven JIGGLE leaves; the record "RC3
             Tails" is adapter revision 2 and describes exactly those seven leaves as simulated leaves, with no saved
             value for them; Apply Pose RC3 Tails committed-verified
  TARGET     each Apply wrote to a different instance of the same model than its Save, never to the session's
             original Fox or Tails (the peers)
  DISPLAY    Pose Info opened for both records
  CLEAN      no operation outcome other than completed, verified or no-op, and no Apply phase other than
             committed-verified or no-op

Verdict: AUTOMATED SMOKE PASS when every gate passes; SMOKE FAIL when EVIDENCE passes and a functional gate fails;
INCOMPLETE otherwise. Undo and Redo, posture, deformation and the peers are the Owner's record
(owner_review/OWNER_SMOKE_RECORD.md), reported beside the verdict; neither replaces the other.
"""
from __future__ import print_function

import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_v110_rc1_smoke", "tools"))
import rc1s_analyze as A  # noqa: E402

FORMAT = "F01-RC3S-verdict-v1"
FOX_POSE, TAILS_POSE = u"RC3 Fox", u"RC3 Tails"
FOX_MODEL = u"models/fursonas/foxmccouldwm.mdl"
TAILS_MODEL = u"models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl"
FOX_PEER, TAILS_PEER = u"foxmccouldwm1", u"milestailsprower1"
RULE = u"structural_rig_v1"
LEAVES = sorted([u"ear3_L", u"ear3_R", u"HairSpike_B3", u"HairSpike_M3", u"HairSpike_T3", u"Tail6_L", u"Tail6_R"])
RE_RIG = re.compile(r" op=(\d+) \| PROD_POSE_BODY-RIG-(available|unavailable) (\{.*\})\s*$")


def rig_lines(path):
    """{op id: [(available?, payload)]} from the CPM log's structural admission lines."""
    out = {}
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = RE_RIG.search(line.rstrip("\n"))
            if m:
                try:
                    payload = json.loads(m.group(3))
                except ValueError:
                    payload = None
                out.setdefault(int(m.group(1)), []).append((m.group(2) == "available", payload))
    return out


class Run(A.Run):
    def evidence(self):
        pins = self.c["pins"]
        ids = self.load("staged", "IDENTITIES.json") or {}
        self.check("EVIDENCE", "rc3_build_staged", ids.get("qualification_cpm_sha256") == pins["rc3_cpm_sha256"] and
                   ids.get("body_profile_sha256") == pins["body_profile_sha256"] and
                   ids.get("profile_sha256") == pins["profile_sha256"], ids.get("qualification_cpm_sha256"))
        modes = ids.get("mode_equivalence") or {}
        self.check("EVIDENCE", "production_mode_check", modes.get("pass") is True,
                   dict((k, modes.get(k)) for k in ("production", "generic_v3", "carried", "krystal_v2", "left_arm",
                                                     "only_unqualified", "structural_status",
                                                     "structural_production", "structural_bounded")))
        logs = self.load("evidence", "logs", "LOGS.json") or {"files": {}}
        names = sorted(logs["files"])
        self.processes = []
        for name in names:
            path = os.path.join(self.ev, "logs", name)
            build, ops = A.parse_log(path)
            self.processes.append({"log": name, "build": build, "ops": ops, "rig": rig_lines(path)})
        self.check("EVIDENCE", "one_cpm_log", len(names) == 1, names)
        self.check("EVIDENCE", "log_written_by_rc3", bool(names) and
                   all(p["build"] == pins["rc3_cpm_sha256"] for p in self.processes),
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

    def unexpected_library(self, diffs):
        fd, td = self.c["fox_dir"], self.c["tails_dir"]
        self.records = {}
        out = []
        for d in diffs:
            path, status = d["path"], d["status"]
            ok = False
            for which, folder, name in (("fox", fd, FOX_POSE), ("tails", td, TAILS_POSE)):
                if re.match(r"^Characters/%s/Poses/%s--[0-9a-f]{12}\.json$" % (re.escape(folder), re.escape(name)),
                            path):
                    ok = status == "added" and which not in self.records
                    self.records[which] = path
            if path in ("Characters/%s/pose_sources.json" % fd, "Characters/%s/pose_sources.json" % td,
                        "Characters/%s/character.json" % fd, "Characters/%s/character.json" % td):
                ok = status in ("added", "changed")        # CPM's own files (Save New; the known character rewrite)
            if not ok:
                out.append(d)
        return out

    def character(self, which, model, revision, name, peer, leaves):
        gate = which.upper()
        rec = self.record(which)
        pose = (rec or {}).get("pose") or {}
        saves = [o for o in self.ops(0, "Save Pose") if rec and o["outcome"] == "verified" and
                 o["preset_id"] == rec.get("preset_id")]
        source = saves[0]["animset"] if len(saves) == 1 else None
        self.check(gate, "saved_once", len(saves) == 1, [(o["animset"], o["outcome"]) for o in self.ops(0, "Save Pose")])
        rig = [r for r in (self.processes[0]["rig"].get(saves[0]["id"], []) if saves and self.processes else [])]
        avail = [p for ok, p in rig if ok and isinstance(p, dict)]
        self.check(gate, "save_admitted_by_the_structural_adapter",
                   len(avail) >= 1 and not [1 for ok, _ in rig if not ok] and
                   sorted(avail[-1].get("simulated_leaves") or []) == leaves, rig)
        region = (pose.get("regions") or {}).get("full_body") or {}
        described = sorted(b.get("name") for b in ((region.get("descriptor") or {}).get("bones") or [])
                           if b.get("class") == u"simulated-leaf")
        saved_names = set(region.get("orientations") or {}) | set(region.get("positions") or {})
        valued = sorted(n for n in saved_names if any(n == l or n.startswith(l + u"_") for l in leaves))
        self.check(gate, "record_is_structural_full_body",
                   rec is not None and rec.get("name") == name and pose.get("version") == 2 and
                   pose.get("adapter") == {u"rule": RULE, u"revision": revision} and
                   sorted((pose.get("regions") or {}).keys()) == [u"full_body"] and
                   (pose.get("source") or {}).get("rig_class") == RULE and
                   (u"%s" % (pose.get("source") or {}).get("model_ref")).replace(u"\\", u"/").lower() == model,
                   {"version": pose.get("version"), "adapter": pose.get("adapter"),
                    "source": (pose.get("source") or {}).get("model_ref")})
        self.check(gate, "record_leaves_described_without_values", described == leaves and not valued,
                   {"described": described, "valued": valued})
        applies = [o for o in self.ops(0, "Apply Pose") if o["label"] == u"Apply Pose %s" % name]
        self.check(gate, "applied_and_verified", len(applies) >= 1 and applies[0]["outcome"] == "verified" and
                   applies[0]["apply_phase"] == "committed-verified",
                   [(o["animset"], o["outcome"], o["apply_phase"]) for o in applies])
        dest = applies[0]["animset"] if applies else None
        family = model.rsplit(u"/", 1)[-1][:-len(u".mdl")]
        self.check("TARGET", "%s_applied_to_another_instance_of_the_same_model" % which,
                   source is not None and dest is not None and dest != source and dest != peer and
                   source != peer and dest.lower().startswith(family) and source.lower().startswith(family) and
                   all(o["animset"] == dest for o in applies),
                   {"source": source, "destination": dest, "peer": peer})

    def functional(self):
        self.character("fox", FOX_MODEL, 1, FOX_POSE, FOX_PEER, [])
        self.character("tails", TAILS_MODEL, 2, TAILS_POSE, TAILS_PEER, LEAVES)
        infos = [o for o in self.ops(0, "Pose Info") if o["outcome"] == "completed"]
        self.check("DISPLAY", "pose_info_opened_for_both", len(infos) >= 2, len(infos))
        bad = [(p["log"], o["id"], o["kind"], o["outcome"], o["apply_phase"]) for p in self.processes
               for o in p["ops"] if o["outcome"] not in A.OK_OUTCOMES or
               (o["apply_phase"] is not None and o["apply_phase"] not in A.OK_PHASES)]
        self.check("CLEAN", "no_refusal_failure_or_recovery", not bad, bad)


def render(result):
    lines = ["# F-01 v1.1.0 RC3 native release smoke: automated verdict", "",
             "**%s** (%d/%d checks)" % (result["verdict"], result["passed"], result["total"]), "",
             "Release-smoke acceptance also needs the Owner's record (`owner_review/OWNER_SMOKE_RECORD.md`: posture, "
             "deformation, peers, Undo and Redo), reported beside this verdict; neither replaces the other.", "",
             "| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in result["checks"]:
        detail = json.dumps(x["detail"], sort_keys=True) if x["detail"] is not None else ""
        lines.append("| %s | %s | %s | %s |" % (x["gate"], x["check"], "PASS" if x["pass"] else "FAIL",
                                               detail.replace("|", "/")[:300]))
    return "\n".join(lines) + "\n"


def run(c):
    R = Run(c)
    out_json = os.path.join(R.ev, "RC3S_VERDICT.json")
    out_md = os.path.join(R.ev, "RC3S_VERDICT.md")
    for path in (out_json, out_md):
        if os.path.lexists(path):
            raise SystemExit("REFUSED: %s exists" % path)
    R.evidence()
    R.functional()
    result = {"format": FORMAT, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "verdict": A.verdict(R),
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
    sys.path.insert(0, HERE)
    import rc3s_tool
    sys.exit(rc3s_tool.main([sys.argv[0], sys.argv[1], "analyze"]) if len(sys.argv) == 2 else 2)
