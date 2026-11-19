# -*- coding: utf-8 -*-
"""F-01 Stage 1: the verdict of the targeted native Abort recovery check. Python 3, run with -I after restore, with
SFM closed. It never changes the run.

Reads:
- Q/staged/IDENTITIES.json;
- Q/observations/S1F-<step>.json and S1F-<step>.undo.json;
- Q/evidence: logs, seed.json, library_cleanup.json, library_after and restore.json;
- Q/sessions.

Writes Q/evidence/S1R_VERDICT.json and S1R_VERDICT.md (exclusive create). The Fox analyzer's helpers are reused
unchanged.

One SFM process on a disposable copy of Fox run 3's saved session, with run 3's saved "S1 Fox" seeded. Fox D
(target) receives the pose; Fox S (source) and the original Fox (peer) are never touched. Steps:
  BASE    Fox D and S1 Fox selected
  APPLY   Apply Pose (committed and verified)
  UNDO    Edit > Undo: Fox D back to BASE, the Apply pending as Redo
  ABORT1  the after-writes fault, Apply Pose: SFM clears the pending Redo; verified restoration, "Pose not applied"
  ABORT2  the fault again, without pending Redo: verified exact restoration, "Nothing was changed."
  APPLY2  Apply Pose again: CPM stays operational
A gate with no evaluated check (a missing capture) is NOT EVALUATED, never PASS.

Gates:
  EVIDENCE    The identities.
              Every capture: the qualification build, no capture error, and a complete Undo sidecar consistent with
              the capture.
              One SFM process, on S1R_SESSION.dmx, in the Motion Editor, at one shot and playhead.
              The session copies never saved.
              The library changed only by the two seeded run 3 files, unchanged; library and installation restored
              exactly; the CPM log collected.
  SETUP       Fox D, Fox S and the peer are the expected models and sets; the seeded record is selected; Fox D is
              admitted by the structural discovery.
  APPLY       Fox D changed; one owned "Apply Pose S1 Fox" entry with no Redo.
              UNDO: Fox D back to BASE exactly, the top Undo entry as at BASE, the Apply pending as Redo, Undo
              enabled.
  REDO_ABORT  The injected failure after as many writes as the committed Apply made.
              CPM: BODY-abort-verified with no problems and redo_cleared true.
              Fox D, Fox S and the peer exactly as at UNDO.
              The Undo state exactly UNDO's except the cleared Redo; enabled observed directly as true; the fault
              slot consumed.
  EXACT_ABORT The second injected failure.
              CPM: BODY-abort-verified with no problems and redo_cleared false.
              Every set and the complete Undo state exactly as at ABORT1; the fault slot consumed.
  OPERATIONAL No lockout and no unverified result anywhere.
              The CPM events in order: P7-verified, failure, verified Abort (Redo cleared), failure, verified Abort
              (exact), P7-verified. Two recovery-verified outcomes.
              APPLY2 equals APPLY on Fox D, with one owned entry.
  PEER        Fox S and the peer unchanged at every capture.

Verdict:
- AUTOMATED PASS: every gate passed. The Owner still confirms the two messages: the "Pose not applied" dialog at
  ABORT1 and "Nothing was changed." at ABORT2.
- FAIL: complete evidence, and a functional gate failed.
- INCOMPLETE: evidence, setup or restoration missing or failed.

usage: python -I s1r_analyze.py S1R.json      (or: s1r_tool.py S1R.json analyze)
"""
from __future__ import print_function

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_stage1_fox", "tools"))
import s1f_analyze as A  # noqa: E402

STEPS = ("BASE", "APPLY", "UNDO", "ABORT1", "ABORT2", "APPLY2")
ROLES = A.ROLES
SESSION = "S1R_SESSION.dmx"
SPARE = "S1R_SPARE.dmx"
NAMES = {"source": "foxmccouldwm2", "target": "foxmccouldwm3", "peer": "foxmccouldwm1"}
POSE = u"S1 Fox"
LABEL = u"Apply Pose S1 Fox"
UNDO_KEYS = ("enabled", "can_undo", "can_redo", "undo_desc", "redo_desc")
SIDECAR_FORMAT = "F01-S1R-undo-v1"
CHARACTER = "foxmccouldwm--2d646d9605f0"
SEEDED = (("Characters/%s/Poses/S1 Fox--dfdf47f5cf4d.json" % CHARACTER, "run3_record_sha256"),
          ("Characters/%s/pose_sources.json" % CHARACTER, "run3_sources_sha256"))
BAD_LOG = A.BAD_LOG + ("PROD_POSE_RECOVERY_BLOCKED", "recovery-blocked", "PROD_POSE_abort-unverified",
                       "PROD_POSE_SCOPE-abort-unverified", "committed-unverified")
EVENTS = ("PROD_POSE_BODY-P7-verified", "PROD_POSE_BODY-P3-P6-failure", "PROD_POSE_BODY-abort-verified",
          "PROD_POSE_BODY-abort-unverified", "PROD_POSE_BODY-abort-failed", "PROD_POSE_BODY-P7-unverified")
EXPECTED_EVENTS = ["PROD_POSE_BODY-P7-verified", "PROD_POSE_BODY-P3-P6-failure", "PROD_POSE_BODY-abort-verified",
                   "PROD_POSE_BODY-P3-P6-failure", "PROD_POSE_BODY-abort-verified", "PROD_POSE_BODY-P7-verified"]


class Report(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.info = [], {}
        self.ids = A.opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap, self.side = {}, {}
        for step in STEPS:
            data = A.opt_json(os.path.join(self.q, "observations", "S1F-%s.json" % step))
            if isinstance(data, dict) and isinstance(data.get("pid"), int):
                self.cap[step] = data
            side = A.opt_json(os.path.join(self.q, "observations", "S1F-%s.undo.json" % step))
            if isinstance(side, dict):
                self.side[step] = side

    def check(self, gate, cid, ok, detail=None):
        self.checks.append({"gate": gate, "id": cid, "pass": bool(ok), "detail": None if ok else detail})
        return ok

    def ev(self, *parts):
        return os.path.join(self.q, "evidence", *parts)


def sidecar_undo(R, step):
    u = (R.side.get(step) or {}).get("undo")
    return u if isinstance(u, dict) else {}


def sidecar_ok(R, step):
    """The sidecar is complete (every member with its native type), from the same process and step, and agrees with
    the capture's own Undo reading (which coerces the flags with bool())."""
    side, u = R.side.get(step) or {}, sidecar_undo(R, step)
    cap = A.undo(R.cap.get(step) or {})
    typed = sorted(u) == sorted(UNDO_KEYS) and all(isinstance(u[k], bool) for k in UNDO_KEYS[:3]) and all(
        isinstance(u[k], type(u"")) for k in UNDO_KEYS[3:])
    return (side.get("format") == SIDECAR_FORMAT and side.get("step") == step and
            side.get("pid") == (R.cap.get(step) or {}).get("pid") and typed and
            all(cap.get(k) == u.get(k) for k in UNDO_KEYS[1:]))


def all_sets(cap):
    return dict((r, A.field(cap, r, "sha256")) for r in ROLES)


def bones(cap, role):
    return A.sets(cap, role).get("bones") or {}


def evaluate(R):
    cap, c = R.cap, R.c
    E = lambda cid, ok, d=None: R.check("EVIDENCE", cid, ok, d)  # noqa: E731
    want = c["pins"]["qualification_cpm_sha256"]
    E("identity.qualification_build", R.ids.get("qualification_cpm_sha256") == want and
      R.ids.get("candidate_cpm_sha256") == c["pins"]["candidate_cpm_sha256"], R.ids.get("qualification_cpm_sha256"))
    for step in STEPS:
        if not E("captured.%s" % step, step in cap):
            continue
        d = cap[step]
        E("cpm.%s" % step, d.get("cpm_build_sha256") == want and d.get("registry_mode") == u"qualification",
          (d.get("cpm_build_sha256"), d.get("registry_mode")))
        E("errors.%s" % step, not d.get("errors") and all(r in (d.get("sets") or {}) for r in ROLES), d.get("errors"))
        E("undo_sidecar.%s" % step, sidecar_ok(R, step), (R.side.get(step), A.undo(d)))
    session, spare = os.path.join(R.q, "sessions", SESSION), os.path.join(R.q, "sessions", SPARE)
    E("sessions.disposable_copy_of_run3_never_saved", os.path.isfile(session) and
      A.sha(session) == c["pins"]["r2_fixture_sha256"])
    E("sessions.spare_never_saved", os.path.isfile(spare) and A.sha(spare) == c["pins"]["destination_sha256"])
    R.info["sessions_folder"] = sorted(os.listdir(os.path.join(R.q, "sessions"))) if os.path.isdir(
        os.path.join(R.q, "sessions")) else None
    seed = A.opt_json(R.ev("seed.json")) or {}
    want_seed = dict((rel, c["pins"][pin]) for rel, pin in SEEDED)
    E("seed.run3_record_and_sources", seed.get("files") == want_seed, seed.get("files"))
    clean = A.opt_json(R.ev("library_cleanup.json")) or {}
    diffs = sorted((x.get("status"), x.get("path"), x.get("sha256")) for x in
                   clean.get("differences_kept_in_evidence") or [])
    E("library.changed_only_by_the_seeded_files_unchanged", bool(clean) and diffs == sorted(
        ("added", rel, digest) for rel, digest in want_seed.items()), diffs)
    E("restore.library_exactly_as_before", clean.get("files_equal_pre") is True and
      clean.get("folders_equal_pre") is True)
    restore = A.opt_json(R.ev("restore.json")) or {}
    E("restore.published_and_inventories_equal", restore.get("restored") is True, restore.get("inventory_problems"))
    lines = A.logs(R)
    E("log.collected", bool(lines))
    if any(s not in cap for s in STEPS):
        return lines
    pids = set(cap[s]["pid"] for s in STEPS)
    E("process.one_sfm_process", len(pids) == 1, sorted(pids))
    docs = set(u"%s" % ((cap[s].get("session") or {}).get("document") or u"") for s in STEPS)
    E("process.every_capture_on_the_disposable_session", len(docs) == 1 and list(docs)[0].lower().replace(
        "\\", "/").endswith(SESSION.lower()), sorted(docs))
    heads = [(cap[s].get("session") or {}).get("head_seconds") for s in STEPS]
    shots = set(u"%s" % (cap[s].get("session") or {}).get("shot") for s in STEPS)
    modes = set(u"%s" % (cap[s].get("session") or {}).get("timeline_mode") for s in STEPS)
    E("session.same_shot_and_playhead_motion_editor", len(shots) == 1 and all(h == heads[0] for h in heads) and
      modes == set([u"2"]), (sorted(shots), heads, sorted(modes)))
    return lines


def functional(R, lines):
    cap, base = R.cap, R.cap["BASE"]
    S = lambda cid, ok, d=None: R.check("SETUP", cid, ok, d)  # noqa: E731
    S("setup.the_three_foxes", all(cap[s].get("names") == NAMES for s in STEPS) and all(
        (u"%s" % A.sets(base, r).get("model")).replace("\\", "/").lower() == A.MODEL for r in ROLES),
      (base.get("names"), dict((r, A.sets(base, r).get("model")) for r in ROLES)))
    rec = A.opt_json(R.ev("library_after", *SEEDED[0][0].split("/"))) or {}
    sel = base.get("selected_pose") or {}
    S("setup.seeded_record_selected", isinstance(sel, dict) and sel.get("name") == POSE and
      sel.get("preset_id") == rec.get("preset_id") and sel.get("adapter") == A.RULE, sel)
    S("setup.fox_d_admitted_by_structural_discovery", A.adm(base, "target").get("placement") == A.PLACEMENT,
      A.adm(base, "target").get("error") or A.adm(base, "target").get("placement"))

    sh = lambda s: A.field(cap[s], "target", "sha256")  # noqa: E731
    P = lambda cid, ok, d=None: R.check("APPLY", cid, ok, d)  # noqa: E731
    au, uu, bu = A.undo(cap["APPLY"]), A.undo(cap["UNDO"]), A.undo(base)
    P("apply.fox_d_changed", sh("APPLY") != sh("BASE"), len(A.changed(sh("BASE"), sh("APPLY"))))
    P("apply.one_owned_history_entry", au.get("undo_desc") == LABEL and au.get("can_redo") is False, au)
    P("undo.fox_d_back_to_base_exactly", sh("UNDO") == sh("BASE") and A.bones_same(
        bones(cap["UNDO"], "target"), bones(base, "target")), A.changed(sh("BASE"), sh("UNDO"))[:6])
    P("undo.apply_pending_as_redo_top_entry_as_at_base", uu.get("can_redo") is True and
      uu.get("redo_desc") == u"Redo " + LABEL and uu.get("undo_desc") == bu.get("undo_desc") and
      uu.get("can_undo") == bu.get("can_undo"), uu)
    P("undo.undo_enabled_observed_directly", sidecar_undo(R, "UNDO").get("enabled") is True,
      sidecar_undo(R, "UNDO"))

    failures = [A.log_json(l, "PROD_POSE_BODY-P3-P6-failure") for l in lines if "PROD_POSE_BODY-P3-P6-failure" in l]
    verified = [A.log_json(l, "PROD_POSE_BODY-abort-verified") for l in lines if "PROD_POSE_BODY-abort-verified" in l]
    p6 = [A.log_json(l, "PROD_POSE_BODY-P6") for l in lines if "PROD_POSE_BODY-P6 " in l]
    first = (p6[0] or {}).get("written") if p6 else None
    R.info["abort"] = {"failures": failures, "verified": verified, "committed_writes": first}

    def injected(i):
        f = failures[i] if len(failures) > i else None
        return isinstance(f, dict) and A.FAULT_TEXT in u"%s" % f.get("error") and f.get("finished") is False and \
            isinstance(first, int) and first > 0 and f.get("written") == first

    X = lambda cid, ok, d=None: R.check("REDO_ABORT", cid, ok, d)  # noqa: E731
    a1, s1 = A.undo(cap["ABORT1"]), sidecar_undo(R, "ABORT1")
    cleared = dict(sidecar_undo(R, "UNDO"), can_redo=False, redo_desc=u"")
    X("abort1.injected_after_the_committed_apply_writes", injected(0), R.info["abort"])
    X("abort1.cpm_verified_with_redo_cleared", len(verified) >= 1 and verified[0] == {
        u"problems": [], u"redo_cleared": True}, verified[:1])
    X("abort1.every_set_exactly_as_at_undo", all_sets(cap["ABORT1"]) == all_sets(cap["UNDO"]) and all(
        A.bones_same(bones(cap["ABORT1"], r), bones(cap["UNDO"], r)) for r in ROLES),
      dict((r, A.changed(A.field(cap["UNDO"], r, "sha256"), A.field(cap["ABORT1"], r, "sha256"))[:4])
           for r in ROLES))
    X("abort1.only_the_pending_redo_cleared", s1 == cleared and a1.get("undo_desc") == uu.get("undo_desc") and
      a1.get("can_undo") == uu.get("can_undo"), (sidecar_undo(R, "UNDO"), s1))
    X("abort1.undo_enabled_observed_directly", s1.get("enabled") is True, s1)
    X("abort1.fault_slot_consumed", cap["ABORT1"].get("qualification_fault") == [None] and
      cap["UNDO"].get("qualification_fault") == [None], cap["ABORT1"].get("qualification_fault"))

    Y = lambda cid, ok, d=None: R.check("EXACT_ABORT", cid, ok, d)  # noqa: E731
    Y("abort2.injected_after_the_committed_apply_writes", injected(1), R.info["abort"])
    Y("abort2.cpm_verified_exact", len(verified) >= 2 and verified[1] == {u"problems": [], u"redo_cleared": False},
      verified[1:2])
    Y("abort2.every_set_exactly_as_at_abort1", all_sets(cap["ABORT2"]) == all_sets(cap["ABORT1"]) and all(
        A.bones_same(bones(cap["ABORT2"], r), bones(cap["ABORT1"], r)) for r in ROLES))
    Y("abort2.undo_state_exactly_as_at_abort1", sidecar_undo(R, "ABORT2") == s1 and
      sidecar_undo(R, "ABORT2").get("enabled") is True, (s1, sidecar_undo(R, "ABORT2")))
    Y("abort2.fault_slot_consumed", cap["ABORT2"].get("qualification_fault") == [None],
      cap["ABORT2"].get("qualification_fault"))

    O = lambda cid, ok, d=None: R.check("OPERATIONAL", cid, ok, d)  # noqa: E731
    bad = [l for l in lines if any(b in l for b in BAD_LOG)]
    O("log.no_lockout_or_unverified_result", not bad, bad[:4])
    events = [e for l in lines for e in EVENTS if (e + " ") in l or l.endswith(e)]
    O("log.events_in_order", events == EXPECTED_EVENTS, events)
    outcomes = [l for l in lines if "PROD_OPERATION_OUTCOME" in l and "recovery-verified" in l]
    O("log.two_recovery_verified_outcomes", len(outcomes) == 2, len(outcomes))
    a2 = A.undo(cap["APPLY2"])
    O("apply2.applied_again_as_at_apply", sh("APPLY2") == sh("APPLY") and A.bones_same(
        bones(cap["APPLY2"], "target"), bones(cap["APPLY"], "target")) and a2.get("undo_desc") == LABEL and
      a2.get("can_redo") is False, (A.changed(sh("APPLY"), sh("APPLY2"))[:6], a2))

    Q = lambda cid, ok, d=None: R.check("PEER", cid, ok, d)  # noqa: E731
    for role in ("source", "peer"):
        Q("%s.unchanged" % role, all(A.field(cap[s], role, "sha256") == A.field(base, role, "sha256") and
                                     A.bones_same(bones(cap[s], role), bones(base, role)) for s in STEPS),
          [s for s in STEPS if A.field(cap[s], role, "sha256") != A.field(base, role, "sha256")])


GATES = ("EVIDENCE", "SETUP", "APPLY", "REDO_ABORT", "EXACT_ABORT", "OPERATIONAL", "PEER")


def verdict(checks):
    def gate(name):
        mine = [x["pass"] for x in checks if x["gate"] == name]
        return all(mine) if mine else None
    gates = dict((n, gate(n)) for n in GATES)
    if gates["EVIDENCE"] is not True or gates["SETUP"] is not True:
        v = "INCOMPLETE"
    elif all(g is True for g in gates.values()):
        v = "AUTOMATED PASS"
    elif any(g is None for g in gates.values()):
        v = "INCOMPLETE"
    else:
        v = "FAIL"
    return v, gates


def markdown(out):
    lines = ["# F-01 Stage 1 native Abort recovery check: %s" % out["verdict"], "",
             "Qualification CPM `%s` (candidate `%s`). Gates: %s." % (
                 out["identities"].get("qualification_cpm_sha256"), out["identities"].get("candidate_cpm_sha256"),
                 ", ".join("%s %s" % (k, A.gate_text(v)) for k, v in sorted(out["gates"].items()))), ""]
    if out["verdict"] == "AUTOMATED PASS":
        lines += ["**Every automated gate passed.** The Owner confirms the two messages: the \"Pose not applied\" "
                  "dialog at ABORT1 and \"Nothing was changed.\" at ABORT2.", ""]
    lines += ["| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in out["checks"]:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False, default=repr)[:300].replace("|", "\\|")
        lines.append("| %s | `%s` | %s | %s |" % (x["gate"], x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    lines += ["", "Info: `%s`" % json.dumps(out["info"], ensure_ascii=False, default=repr)[:900]]
    return "\n".join(lines) + "\n"


def run(c):
    R = Report(c)
    lines = evaluate(R)
    if all(s in R.cap for s in STEPS):
        functional(R, lines)
    v, gates = verdict(R.checks)
    out = {"format": "F01-S1R-verdict-v1", "verdict": v, "gates": gates, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in R.checks if not x["pass"]], "info": R.info,
           "analyzer_sha256": A.sha(os.path.abspath(__file__))}
    md = markdown(out)
    for name, data in (("S1R_VERDICT.json", json.dumps(out, indent=1, sort_keys=True, default=repr)),
                       ("S1R_VERDICT.md", md)):
        fd = os.open(R.ev(name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(md)
    return 0 if v == "AUTOMATED PASS" else 1


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import s1r_tool
    return run(s1r_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
