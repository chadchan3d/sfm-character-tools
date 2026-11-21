# -*- coding: utf-8 -*-
"""F-01 RC4S analyzer: the automated verdict of the v1.1.0 RC4 native release smoke (a normal installation of the
unsigned RC4 package: Fox Full body, and the qualified Tails cross-rig transfer), from the run's preserved evidence
only (read-only; writes Q/evidence/RC4S_VERDICT.json and .md, exclusive create). It reuses the RC3S analyzer's checks
(and through it the RC1S CPM log parser) unchanged.

Inputs: Q/staged/IDENTITIES.json (the RC4 build and its production-mode check), Q/evidence/logs (the CPM's own
diagnostic log of the one SFM process), Q/evidence/library_cleanup.json and library_after, Q/evidence/restore.json.

Gates:
  EVIDENCE   the RC4 build staged and its production-mode check PASS; exactly one CPM log, written by the RC4
             production CPM; the library and installation restored; the library changes are only the two saved poses
             and CPM's own character files (pose_sources.json, pose_rigs.json, character.json and their backups)
  FOX        Save Pose verified on one fresh Fox, admitted by the structural adapter; the record "RC4 Fox" is version 2,
             structural_rig_v1 revision 1; Apply Pose RC4 Fox committed-verified (the RC3S check, unchanged)
  TAILS      "RC4 Sit" saved once from the session's original Tails (milestailsprower1), admitted with exactly the
             seven JIGGLE leaves; the record is structural_rig_v1 revision 2 describing those leaves without values
  CROSS      the first Apply Pose RC4 Sit is on another Tails instance (never the original), adapted by CPM
             (bip_spine_3 to constrained) and committed-verified, with CPM's own reproduction maxima inside the
             revised envelope (0.01 units, 0.1 degrees); the repeated Apply is a no-op (CPM's no-work result "no-op")
             that opened no Undo (no P6)
  TARGET     the Fox Apply on another instance of the Fox model (never the original Fox)
  DISPLAY    Pose Info opened for both records; pose_rigs.json records each saved pose's scene rig with a readable
             label (the Rig row's source)
  CLEAN      no operation outcome other than completed, verified or no-op, and no Apply phase other than
             committed-verified or no-op

Verdict: AUTOMATED SMOKE PASS when every gate passes; SMOKE FAIL when EVIDENCE passes and a functional gate fails;
INCOMPLETE otherwise. Undo and Redo, posture, deformation, the peers, Save New's feedback and Pose Info's Rig row as
displayed are the Owner's record (owner_review/OWNER_SMOKE_RECORD.md), reported beside the verdict.
"""
from __future__ import print_function

import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_v110_rc3_smoke", "tools"))
import rc3s_analyze as B  # noqa: E402

A = B.A
FORMAT = "F01-RC4S-verdict-v1"
FOX_POSE, SIT_POSE = u"RC4 Fox", u"RC4 Sit"
ENVELOPE = {"position": 0.01, "angle_degrees": 0.1}
RE_BODY = re.compile(r" op=(\d+) \| PROD_POSE_BODY-(RIG-adapted|P7-verified|nowork|P6) (\{.*\})\s*$")


def body_lines(path):
    """{op id: {tag: [payload]}} from the CPM log's adaptation, P7, no-work and P6 lines."""
    out = {}
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = RE_BODY.search(line.rstrip("\n"))
            if m:
                try:
                    payload = json.loads(m.group(3))
                except ValueError:
                    payload = None
                out.setdefault(int(m.group(1)), {}).setdefault(m.group(2), []).append(payload)
    return out


class Run(B.Run):
    def evidence(self):
        pins = self.c["pins"]
        ids = self.load("staged", "IDENTITIES.json") or {}
        self.check("EVIDENCE", "rc4_build_staged", ids.get("qualification_cpm_sha256") == pins["rc4_cpm_sha256"] and
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
            self.processes.append({"log": name, "build": build, "ops": ops, "rig": B.rig_lines(path),
                                   "body": body_lines(path)})
        self.check("EVIDENCE", "one_cpm_log", len(names) == 1, names)
        self.check("EVIDENCE", "log_written_by_rc4", bool(names) and
                   all(p["build"] == pins["rc4_cpm_sha256"] for p in self.processes),
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
            for which, folder, name in (("fox", fd, FOX_POSE), ("tails", td, SIT_POSE)):
                if re.match(r"^Characters/%s/Poses/%s--[0-9a-f]{12}\.json$" % (re.escape(folder), re.escape(name)),
                            path):
                    ok = status == "added" and which not in self.records
                    self.records[which] = path
            for folder in (fd, td):
                for own in ("pose_sources.json", "pose_rigs.json", "character.json"):
                    if path in ("Characters/%s/%s" % (folder, own), "Characters/%s/%s.bak" % (folder, own)):
                        ok = status in ("added", "changed")    # CPM's own files (Save New; the character rewrite)
            if not ok:
                out.append(d)
        return out

    def sit(self):
        """TAILS and CROSS: RC4 Sit saved from the original Tails and applied, adapted, to another Tails."""
        rec = self.record("tails")
        pose = (rec or {}).get("pose") or {}
        saves = [o for o in self.ops(0, "Save Pose") if rec and o["outcome"] == "verified" and
                 o["preset_id"] == rec.get("preset_id")]
        self.check("TAILS", "saved_once_from_the_original_tails", len(saves) == 1 and saves[0]["animset"] ==
                   B.TAILS_PEER, [(o["animset"], o["outcome"]) for o in self.ops(0, "Save Pose")])
        rig = self.processes[0]["rig"].get(saves[0]["id"], []) if saves and self.processes else []
        avail = [p for ok, p in rig if ok and isinstance(p, dict)]
        self.check("TAILS", "save_admitted_by_the_structural_adapter", len(avail) >= 1 and not [
            1 for ok, _ in rig if not ok] and sorted(avail[-1].get("simulated_leaves") or []) == B.LEAVES, rig)
        region = (pose.get("regions") or {}).get("full_body") or {}
        described = sorted(b.get("name") for b in ((region.get("descriptor") or {}).get("bones") or [])
                           if b.get("class") == u"simulated-leaf")
        saved_names = set(region.get("orientations") or {}) | set(region.get("positions") or {})
        valued = sorted(n for n in saved_names if any(n == l or n.startswith(l + u"_") for l in B.LEAVES))
        self.check("TAILS", "record_is_structural_full_body_revision_2", rec is not None and rec.get("name") ==
                   SIT_POSE and pose.get("version") == 2 and pose.get("adapter") == {u"rule": B.RULE, u"revision": 2}
                   and (u"%s" % (pose.get("source") or {}).get("model_ref")).replace(u"\\", u"/").lower() ==
                   B.TAILS_MODEL and described == B.LEAVES and not valued,
                   {"adapter": pose.get("adapter"), "described": described, "valued": valued})
        applies = [o for o in self.ops(0, "Apply Pose") if o["label"] == u"Apply Pose %s" % SIT_POSE or
                   (o["outcome"] == "no-op" and o["animset"] and o["animset"].lower().startswith(u"milestailsprower"))]
        first = applies[0] if applies else None
        body = self.processes[0]["body"] if self.processes else {}
        ob = body.get(first["id"], {}) if first else {}
        adapted = [x for x in ob.get("RIG-adapted", []) if isinstance(x, dict)]
        rep = [(x or {}).get("reproduction") or {} for x in ob.get("P7-verified", [])]
        self.info["cross"] = {"destination": first and first["animset"], "adapted": adapted[:1], "reproduction": rep}
        self.check("CROSS", "applied_to_another_tails_and_verified", first is not None and first["outcome"] ==
                   "verified" and first["apply_phase"] == "committed-verified" and first["animset"] not in (
                       None, B.TAILS_PEER) and first["animset"].lower().startswith(u"milestailsprower"),
                   [(o["animset"], o["outcome"], o["apply_phase"]) for o in applies])
        self.check("CROSS", "adapted_to_the_chest_rig", any(((x.get("converted") or [{}])[0]) == {
            u"bone": u"bip_spine_3", u"destination": u"constrained"} for x in adapted), adapted[:1])
        self.check("CROSS", "reproduction_within_the_revised_envelope", len(rep) == 1 and rep[0].get("limits") == {
            u"position": ENVELOPE["position"], u"angle_degrees": ENVELOPE["angle_degrees"]} and rep[0].get(
            "outputs", 0) > 100 and rep[0].get("max_distance", 1) <= ENVELOPE["position"] and
            rep[0].get("max_angle_deg", 1) <= ENVELOPE["angle_degrees"], rep)
        again = applies[1] if len(applies) > 1 else None
        nb = body.get(again["id"], {}) if again else {}
        self.check("CROSS", "repeat_apply_is_a_no_op_without_undo", again is not None and again["outcome"] == "no-op"
                   and again["animset"] == first["animset"] and [(x or {}).get("result") for x in nb.get(
                       "nowork", [])] == [u"no-op"] and not nb.get("P6"),
                   again and (again["outcome"], nb))

    def rigs_recorded(self):
        out = {}
        for which, folder in (("fox", self.c["fox_dir"]), ("tails", self.c["tails_dir"])):
            data = self.load("evidence", "library_after", "Characters", folder, "pose_rigs.json") or {}
            rec = self.record(which) or {}
            out[which] = (data.get("entries") or {}).get(rec.get("preset_id"))
        return out

    def functional(self):
        self.info = {}
        self.character("fox", B.FOX_MODEL, 1, FOX_POSE, B.FOX_PEER, [])
        self.sit()
        infos = [o for o in self.ops(0, "Pose Info") if o["outcome"] == "completed"]
        self.check("DISPLAY", "pose_info_opened_for_both", len(infos) >= 2, len(infos))
        rigs = self.rigs_recorded()
        self.info["rigs"] = rigs
        self.check("DISPLAY", "scene_rig_recorded_for_both_poses", all(
            isinstance(r, dict) and r.get("label") == u"rig_biped" and (r.get("scene") or u"").startswith(
                u"rig_biped_") for r in rigs.values()), rigs)
        bad = [(p["log"], o["id"], o["kind"], o["outcome"], o["apply_phase"]) for p in self.processes
               for o in p["ops"] if o["outcome"] not in A.OK_OUTCOMES or
               (o["apply_phase"] is not None and o["apply_phase"] not in A.OK_PHASES)]
        self.check("CLEAN", "no_refusal_failure_or_recovery", not bad, bad)


def render(result):
    lines = ["# F-01 v1.1.0 RC4 native release smoke: automated verdict", "",
             "**%s** (%d/%d checks)" % (result["verdict"], result["passed"], result["total"]), "",
             "Release-smoke acceptance also needs the Owner's record (`owner_review/OWNER_SMOKE_RECORD.md`: posture, "
             "deformation, peers, Undo and Redo, Save New feedback, Pose Info Rig row), reported beside this verdict.",
             "", "| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in result["checks"]:
        detail = json.dumps(x["detail"], sort_keys=True) if x["detail"] is not None else ""
        lines.append("| %s | %s | %s | %s |" % (x["gate"], x["check"], "PASS" if x["pass"] else "FAIL",
                                               detail.replace("|", "/")[:300]))
    lines += ["", "Info: `%s`" % json.dumps(result.get("info"), sort_keys=True)[:1500]]
    return "\n".join(lines) + "\n"


def run(c):
    R = Run(c)
    R.info = {}
    out_json = os.path.join(R.ev, "RC4S_VERDICT.json")
    out_md = os.path.join(R.ev, "RC4S_VERDICT.md")
    for path in (out_json, out_md):
        if os.path.lexists(path):
            raise SystemExit("REFUSED: %s exists" % path)
    R.evidence()
    R.functional()
    result = {"format": FORMAT, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "verdict": A.verdict(R),
              "passed": sum(1 for x in R.checks if x["pass"]), "total": len(R.checks), "checks": R.checks,
              "info": R.info,
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
    import rc4s_tool
    sys.exit(rc4s_tool.main([sys.argv[0], sys.argv[1], "analyze"]) if len(sys.argv) == 2 else 2)
