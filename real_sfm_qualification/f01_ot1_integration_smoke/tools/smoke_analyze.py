# -*- coding: utf-8 -*-
"""F-01 OT1S: the verdict of the minimal native integration smoke check. Python 3, run with -I after restore (SFM
closed). Read-only except for its two report files (exclusive create). It reuses the OT1 analyzer's field and graph
comparisons (target_diff, graph, graph_diff, undo) and the Q1 analyzer's helpers.

Gates (all on complete evidence):
  GUARD    the integrated production guard accepted each changed expression (bip_head, bip_tail00) once before the
           Body transaction's first scale write (before StartUndo) and once more inside it, before Operate(); no
           guard refusal.
  APPLY    exactly the two changed existing mode-3 scales written; CPM's deferred physical verification
           committed-verified (event and log); settled map PASS; the target's physical scales are the requested
           values; only head and tail scales change on its bones; one owned history action (top-level labels).
  UNDO     one native Undo, Redo and final Undo, field by field: Undo and the final Undo restore the target's raw
           fields and both scale graphs exactly to BASE, Redo exactly to APPLY; the labels move by that one action.
  PEER     the same-model peer is identical to BASE at every later capture.
  EVIDENCE identities, all five captures, one SFM process on the disposable session at shot15 with the time never
           moved, hooks installed and removed, the same selected instance, only the one Body Apply, no visibility
           edit, BASE as expected, no recovery or uncertainty in the log, library and installation restored exactly,
           the session never saved.

Verdict: "SMOKE PASS" only when every gate passes; "SMOKE FAIL" when the evidence is complete and a functional gate
fails; "INCOMPLETE" when evidence or restoration fails. Exit 0 only on SMOKE PASS.

usage: python -I smoke_analyze.py OT1S.json      (or: smoke_tool.py OT1S.json analyze)
"""
from __future__ import print_function

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OT1_TOOLS = os.path.join(HERE, "..", "..", "f01_ot1_ordering_trial", "tools")
if OT1_TOOLS not in sys.path:
    sys.path.insert(0, OT1_TOOLS)
import ot1_analyze as A  # noqa: E402

Q = A.Q
STEPS = ("BASE", "APPLY", "UNDO", "REDO", "UNDO2")
HOOKS = sorted(["prod_apply", "prod_bs_write_existing_scale", "same_time_refresh", "prod_bs_index_verify_saved",
                "prod_verify_apply_abort_baseline", "prod_bs_expression_reference_guard"])
CHANGED, BODY, APPLY_LABEL = A.CHANGED, A.BODY, A.APPLY_LABEL
SESSION_DOC = u"ot1s_krystal.dmx"


class Report(A.Report):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.info, self.findings = [], {}, []
        self.ids = Q.opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap = {}
        for step in STEPS:
            data = Q.opt_json(os.path.join(self.q, "observations", "OT1S-%s.json" % step))
            if isinstance(data, dict) and isinstance(data.get("pid"), int):
                self.cap[step] = data


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
        E("cpm.%s" % step, d.get("cpm_build_sha256") == want, d.get("cpm_build_sha256"))
        E("fields.%s" % step, not Q.set_field_problems(d), Q.set_field_problems(d))
    path = os.path.join(R.q, "sessions", "OT1S_KRYSTAL.dmx")
    E("sessions.never_saved", os.path.isfile(path) and Q.sha(path) == c["pins"]["r2_fixture_sha256"])
    A.restoration(R)
    if any(s not in cap for s in STEPS):
        E("complete", False, "missing captures: %s" % [s for s in STEPS if s not in cap])
        return
    pids = set(cap[s]["pid"] for s in STEPS)
    docs = set(((cap[s].get("session") or {}).get("document") or u"").lower() for s in STEPS)
    E("process.one_sfm_process_on_the_disposable_session",
      len(pids) == 1 and len(docs) == 1 and list(docs)[0].endswith(SESSION_DOC), (sorted(pids), sorted(docs)))
    heads = [(cap[s].get("session") or {}).get("head_seconds") for s in STEPS]
    shots = set((cap[s].get("session") or {}).get("shot") for s in STEPS)
    E("session.shot15_and_time_never_moved", shots == set([A.SHOT]) and
      all(A.close(h, heads[0], A.EXACT) for h in heads) and A.close(heads[0], 0.2083, 1e-3), (sorted(shots), heads))
    E("hooks.installed_at_base", sorted(cap["BASE"].get("hooks_installed") or []) == HOOKS,
      cap["BASE"].get("hooks_installed"))
    E("hooks.removed_at_undo2", cap["UNDO2"].get("hooks_removed") is True)
    E("injector.never_armed", all((cap[s].get("injector") or {}).get("armed") is False and
                                  (cap[s].get("injector") or {}).get("fired") == 0 for s in STEPS[1:]))
    instance = cap["BASE"].get("instance") or {}
    key = instance.get("animset_key") if isinstance(instance, dict) else None
    target = key[1] if isinstance(key, list) and len(key) == 3 else None
    sets = dict((s, Q.sets_by_handle(cap[s])) for s in STEPS)
    model = ((sets["BASE"].get(target) or {}).get("model") or {}).get("model")
    peers = sorted(n for n, s in sets["BASE"].items() if n != target and ((s.get("model") or {}).get("model") == model))
    E("instance.target_and_same_model_peer", target in sets["BASE"] and len(peers) >= 1 and model is not None,
      {"target": target, "peers": peers})
    E("instance.same_selected_instance", bool(instance) and all((cap[s].get("instance") or {}) == instance
                                                                 for s in STEPS))
    begins = dict((s, Q.events(cap[s], "apply-begin")) for s in STEPS)
    E("operations.only_the_one_body_apply",
      [(e.get("preset"), e.get("preset_kind")) for e in begins["APPLY"]] == [(BODY, u"body")] and
      not any(begins[s] for s in ("BASE", "UNDO", "REDO", "UNDO2")),
      dict((s, [e.get("preset") for e in v]) for s, v in begins.items()))
    vis = dict((s, [n for n in sets["BASE"] if sets[s].get(n) and Q.set_diff(sets["BASE"][n], sets[s][n])["visibility"]])
               for s in STEPS[1:])
    E("edits.no_visibility_change", not any(vis.values()), vis)
    base_map = cap["BASE"].get("settled_full_map") or {}
    base_fail = sorted(b.get("bone") for b in base_map.get("bones") or [] if not b.get("ok"))
    E("base.precondition_head_and_tail_differ", Q.map_ok(base_map) and base_map["result"] is False and
      base_fail == sorted(CHANGED), base_fail)
    rows = Q.log_rows(R)
    E("log.no_recovery_or_uncertainty", not any(b_ in r["text"] for r in rows for b_ in A.BAD_LOG),
      sorted(set(b_ for r in rows for b_ in A.BAD_LOG if b_ in r["text"])))
    t = lambda s: sets[s].get(target)  # noqa: E731
    g = dict((s, A.graph(cap[s])) for s in STEPS)
    R.info["graphs"] = g
    ap = cap["APPLY"]
    kinds = [(e.get("kind"), e.get("bone")) for e in ap.get("events") or []]

    G = lambda cid, ok, d=None: R.check("GUARD", cid, ok, d)  # noqa: E731
    guards = Q.events(ap, "reference-guard")
    # Inside the transaction the guard runs within CPM's scale write, so its event immediately precedes that bone's
    # scale-write event; every other guard event is the pre-transaction check, which must precede all of them.
    inner = [i - 1 for i, k in enumerate(kinds) if k[0] == "scale-write" and i > 0 and
             kinds[i - 1] == ("reference-guard", k[1])]
    pre = [i for i, k in enumerate(kinds) if k[0] == "reference-guard" and i not in inner]
    G("accepted_every_changed_expression_without_refusal", len(guards) == 2 * len(CHANGED) and
      all(e.get("error") is None and e.get("result") is True for e in guards) and
      sorted(e.get("bone") for e in guards) == sorted(list(CHANGED) * 2), [(e.get("bone"), e.get("result"),
                                                                              e.get("error")) for e in guards])
    G("checked_before_the_transaction_and_again_before_operate",
      sorted(kinds[i][1] for i in pre) == sorted(CHANGED) and sorted(kinds[i][1] for i in inner) == sorted(CHANGED)
      and bool(pre) and bool(inner) and max(pre) < min(inner), kinds)

    P = lambda cid, ok, d=None: R.check("APPLY", cid, ok, d)  # noqa: E731
    writes = Q.events(ap, "scale-write")
    P("operation_returned", len(Q.events(ap, "apply-returned")) == 1 and not Q.events(ap, "apply-raised"), kinds)
    P("writes.exactly_the_two_changed_mode3_scales", sorted(e.get("bone") for e in writes) == sorted(CHANGED) and
      all(e.get("static_output_mode") == 3 for e in writes) and not Q.events(ap, "scale-write-raised"),
      [(e.get("bone"), e.get("static_output_mode")) for e in writes])
    dv = Q.events(ap, "deferred-verify", record=BODY)
    outcomes = Q.deferred_outcomes(rows, BODY)
    P("deferred.physical_verification_passed_and_matches_cpm_log",
      len(dv) == 1 and dv[0].get("result") is True and dv[0].get("consistent") is True and
      outcomes[:1] == [{"outcome": "committed-verified", "reason": None}], {"events": len(dv), "log": outcomes})
    P("settled.full_map_passes", Q.map_ok(ap.get("settled_full_map")) and ap["settled_full_map"]["result"] is True,
      Q.failures(ap.get("settled_full_map")))
    phys = dict((A.bone_of(r[0]), r[3]) for r in ((t("APPLY") or {}).get("model") or {}).get("bones") or [])
    wanted = dict((e.get("bone"), e.get("desired_physical")) for e in writes)
    P("target.physical_scales_requested", sorted(wanted) == sorted(CHANGED) and
      all(A.close(phys.get(b), wanted[b]) for b in CHANGED), dict((b, (phys.get(b), wanted.get(b))) for b in CHANGED))
    bone_changes = [x for x in A.target_diff(t("BASE"), t("APPLY")) if x.startswith("bone ")]
    P("target.bones_change_only_head_and_tail_scale",
      sorted(x.split(" ")[0] + " " + x.split(" ")[1] for x in bone_changes) == sorted("bone %s.scale" % b
                                                                                     for b in CHANGED), bone_changes)
    base_u, apply_u = A.undo(cap["BASE"]), A.undo(ap)
    P("history.one_owned_entry", apply_u.get("undo_desc") == APPLY_LABEL and apply_u.get("can_redo") is False and
      apply_u.get("can_undo") is True and base_u.get("undo_desc") not in (None, u"", APPLY_LABEL), (base_u, apply_u))
    R.info["history_item_counts"] = dict((s, A.undo(cap[s]).get("count")) for s in STEPS)

    U = lambda cid, ok, d=None: R.check("UNDO", cid, ok, d)  # noqa: E731
    for step, ref, label in (("UNDO", "BASE", "undo"), ("REDO", "APPLY", "redo"), ("UNDO2", "BASE", "final_undo")):
        U("%s.target_fields_equal_%s" % (label, ref.lower()), not A.target_diff(t(ref), t(step)),
          A.target_diff(t(ref), t(step))[:12])
        U("%s.scale_graphs_equal_%s" % (label, ref.lower()), not A.graph_diff(g[ref], g[step]),
          A.graph_diff(g[ref], g[step]))
        u_ = A.undo(cap[step])
        if label == "redo":
            U("redo.history", u_.get("undo_desc") == APPLY_LABEL and u_.get("can_redo") is False, u_)
        else:
            U("%s.history" % label, u_.get("undo_desc") == base_u.get("undo_desc") and u_.get("can_redo") is True and
              APPLY_LABEL in (u_.get("redo_desc") or u""), u_)

    W = lambda cid, ok, d=None: R.check("PEER", cid, ok, d)  # noqa: E731
    diffs = dict((p, dict((s, A.target_diff(sets["BASE"].get(p), sets[s].get(p))) for s in STEPS[1:])) for p in peers)
    R.info["peer_diffs"] = diffs
    W("peer.unchanged_at_every_capture", bool(peers) and all(not v for d in diffs.values() for v in d.values()), diffs)


def verdict(checks):
    gates = dict((n, all(x["pass"] for x in checks if x["gate"] == n))
                 for n in ("EVIDENCE", "GUARD", "APPLY", "UNDO", "PEER"))
    if not gates["EVIDENCE"]:
        return "INCOMPLETE", gates
    return ("SMOKE PASS" if all(gates.values()) else "SMOKE FAIL"), gates


def markdown(out):
    lines = ["# F-01 OT1S integration smoke: %s" % out["verdict"], "",
             "Qualification CPM `%s` (integrated candidate `%s`). Gates: %s." % (
                 out["identities"].get("qualification_cpm_sha256"), out["identities"].get("candidate_cpm_sha256"),
                 ", ".join("%s %s" % (k, "PASS" if v else "FAIL") for k, v in sorted(out["gates"].items()))), "",
             "| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in out["checks"]:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False, default=repr)[:300].replace("|", "\\|")
        lines.append("| %s | `%s` | %s | %s |" % (x["gate"], x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    g = (out.get("info") or {}).get("graphs") or {}
    if g:
        lines += ["", "| Step | Bone | Expression input | Expression result | Physical |", "|---|---|---|---|---|"]
        for step in STEPS:
            for bone in sorted(g.get(step) or {}):
                r = g[step][bone]
                lines.append("| %s | %s | %s | %s | %s |" % (step, bone, r.get("expr_input"), r.get("expr_result"),
                                                            r.get("physical")))
    if out["findings"]:
        lines += ["", "Findings:"] + ["- %s" % f for f in out["findings"]]
    return "\n".join(lines) + "\n"


def run(c):
    R = Report(c)
    evaluate(R)
    v, gates = verdict(R.checks)
    out = {"format": "F01-OT1S-verdict-v1", "verdict": v, "gates": gates, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in R.checks if not x["pass"]], "info": R.info, "findings": R.findings,
           "analyzer_sha256": Q.sha(os.path.abspath(__file__))}
    md = markdown(out)
    for name, data in (("OT1S_VERDICT.json", json.dumps(out, indent=1, sort_keys=True, default=repr)),
                       ("OT1S_VERDICT.md", md)):
        fd = os.open(R.ev(name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(md)
    return 0 if v == "SMOKE PASS" else 1


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import smoke_tool
    return run(smoke_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
