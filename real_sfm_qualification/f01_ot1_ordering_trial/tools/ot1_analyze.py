# -*- coding: utf-8 -*-
"""F-01 OT1: the offline verdict of the qualification-only ordering trial. Python 3, run with -I after restore (SFM
closed). Read-only except for its two report files (exclusive create).

Four gates on complete evidence; the candidate passes only when all four pass:
  APPLY   the Body operation writes exactly the two changed existing mode-3 scales; at precommit (inside the owned
          transaction, after the operator) each expression result equals its expected mapped scale with the authored
          input, the output mode 3 and the empty output log intact; CPM's deferred physical verification passes and
          reproduces CPM's log (committed-verified); the settled map passes; one history entry "Apply Body Preset";
          the peer untouched; only head and tail scales changed on the target's bones.
  UNDO    native Undo, Redo and a final Undo, field by field: Undo and the final Undo restore the target's raw fields
          and its scale graphs (authored input, expression result, physical scale) exactly to BASE; Redo restores
          them exactly to APPLY; the history moves by that one entry each time; the peer never changes.
  ABORT   with the controlled failure armed, a second Body Apply operates and verifies both expressions, the failure
          fires once after the tail's operator call, CPM's own abort verification returns True (restored=True, no
          recovery uncertainty), the target's fields and graphs equal ARM exactly, no history entry is added, the peer
          is untouched.
  EVIDENCE the BASE and ARM preflights (read only, no Undo or playhead change; both graphs pass the candidate's own
          reader/writer uniqueness scan with nothing unreadable; Astra DC1 with the DC2 correction: the IDataModel
          reference iterator, traversed to the DMATTRIBUTE_REFERENCE_ITERATOR_INVALID sentinel with no repeated token,
          returns exactly three direct references per live expression - the selected animation set's operators, the
          admitted input channel's toElement, the admitted output channel's fromElement - every row independently
          re-validated, the CDmElement/Vector/QAngle/Quaternion class entries and sys.modules' vsUtils membership
          identical before and after each traversal, the same live elements at BASE and ARM, and arming only after a
          passing ARM preflight), identities, every capture, one SFM process on the disposable session at shot15 with the time never moved,
          hooks installed and removed, the same selected instance, no other CPM operation, no visibility edit,
          library and installation restored exactly, the session never saved.

Verdict: "CANDIDATE PASS"; "CANDIDATE FAIL" (evidence complete, a gate failed; APPLY PASS with UNDO FAIL is a FAIL);
or "INCOMPLETE" (evidence or restoration failed; no candidate decision). Exit 0 only on CANDIDATE PASS.

usage: python -I ot1_analyze.py OT1.json      (or: ot1_tool.py OT1.json analyze)
Writes Q/evidence/OT1_VERDICT.json and OT1_VERDICT.md.
"""
from __future__ import print_function

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
Q1_TOOLS = os.path.join(HERE, "..", "..", "f01_q1_ps2_diagnostic", "tools")
if Q1_TOOLS not in sys.path:
    sys.path.insert(0, Q1_TOOLS)
import q1_analyze as Q  # noqa: E402  (pure helpers: events, map_ok, set_diff, set_field_problems, logs, sha)

STEPS = ("BASE", "APPLY", "UNDO", "REDO", "UNDO2", "ARM", "ABORT")
BODY = u"Body"
HOOKS = sorted(["prod_apply", "prod_bs_write_existing_scale", "same_time_refresh", "prod_bs_index_verify_saved",
                "prod_verify_apply_abort_baseline"])
CHANGED = (u"bip_head", u"bip_tail00")
FAIL_BONE = u"bip_tail00"
FAIL_TEXT = u"OT1 controlled failure after the operator call"
APPLY_LABEL = u"Apply Body Preset"
SESSION_DOC = u"ot1_krystal.dmx"
SHOT = u"shot15"
EPS = 1e-5          # CPM's own EPSILON for expected values
EXACT = 1e-6        # restoration: raw fields must agree within this (unrounded float32 round trips)
BAD_LOG = Q.BAD_LOG


def close(a, b, tol=EPS):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def bone_of(name):
    m = re.match(r"bone \d+ \((.*)\)$", name or u"")
    return m.group(1) if m else name


def target_diff(a, b):
    """Every field difference above EXACT between two raw captures of one animation set ([] = identical)."""
    d = Q.set_diff(a, b)
    if d.get("missing"):
        return ["missing"]
    out = []
    for r in d["controls"]:
        if r["max_abs"] is None or r["max_abs"] > EXACT:
            out.append("control %s.%s %r -> %r" % (r["control"], r["attribute"], r["before"], r["after"]))
    for r in d["bones"]:
        for f, v in sorted(r["fields"].items()):
            if v["max_abs"] is None or v["max_abs"] > EXACT:
                out.append("bone %s.%s %r -> %r" % (bone_of(r["bone"]), f, v["before"], v["after"]))
    for r in d["flexes"]:
        if r["max_abs"] is None or r["max_abs"] > EXACT:
            out.append("flex %s %r -> %r" % (r["flex"], r["before"], r["after"]))
    for r in d["visibility"]:
        out.append("visibility %s %r -> %r" % (r["field"], r["before"], r["after"]))
    return out


def graph(cap):
    """{bone: graph fields} for the changed scales, from the capture's settled full map (CPM's own trace)."""
    out = {}
    for b in ((cap or {}).get("settled_full_map") or {}).get("bones") or []:
        if b.get("bone") not in CHANGED:
            continue
        t = b.get("trace") or {}
        e, o = t.get("expression") or {}, t.get("output") or {}
        inputs = t.get("inputs") or [{}]
        i = inputs[0] if isinstance(inputs[0], dict) else {}
        out[b["bone"]] = {"expr_input": e.get("value"), "expr_result": e.get("result"),
                          "physical": t.get("physical_scale"), "source": i.get("source_value"),
                          "key": (i.get("log") or {}).get("key0_value"),
                          "key_count": (i.get("log") or {}).get("key_count"), "output_mode": o.get("mode"),
                          "output_keys": (o.get("log") or {}).get("key_count"),
                          "output_empty": (o.get("log") or {}).get("is_empty"),
                          "output_default": (o.get("log") or {}).get("use_default_value"),
                          "expression_id": e.get("id"), "output_id": o.get("id"), "input_count": t.get("input_count")}
    return out


def graph_diff(a, b):
    out = []
    if sorted(a) != list(CHANGED) or sorted(b) != list(CHANGED):
        return ["graph rows missing: %s / %s" % (sorted(a), sorted(b))]
    for bone in CHANGED:
        for k in sorted(a[bone]):
            x, y = a[bone][k], b[bone][k]
            if isinstance(x, float) or isinstance(y, float):
                if not close(x, y, EXACT):
                    out.append("%s.%s %r -> %r" % (bone, k, x, y))
            elif x != y:
                out.append("%s.%s %r -> %r" % (bone, k, x, y))
    return out


REF_ROLES = (("animset", u"operators"), ("input_channel", u"toElement"), ("output", u"fromElement"))


def direct_ref_problems(cap, target):
    """([problems], {bone: {role: owner identity}}) for one capture's DC1 evidence. Every field is required: a missing
    preflight, bone, enumeration or identity is a problem, never a pass."""
    problems, owners = [], {}
    pre = (cap or {}).get("preflight")
    if not isinstance(pre, dict):
        return ["no preflight"], owners
    for bone in CHANGED:
        b = (pre.get("bones") or {}).get(bone)
        if not isinstance(b, dict):
            problems.append("%s: no preflight row" % bone)
            continue
        d = b.get("direct_refs")
        ids = b.get("identities") or {}
        if not isinstance(d, dict):
            problems.append("%s: no direct-reference evidence" % bone)
            continue
        if d.get("complete") is not True or d.get("error") is not None or d.get("terminated_at_sentinel") is not True:
            problems.append("%s: enumeration did not end normally at the sentinel (%r)" % (bone, d.get("error")))
        if d.get("repeated_token") is not False:
            problems.append("%s: repeated or unrecorded iterator-token state" % bone)
        if (d.get("class_entries") or {}).get("unchanged") is not True:
            problems.append("%s: Python class entries changed or unrecorded across the traversal" % bone)
        if (d.get("vsutils_module") or {}).get("unchanged") is not True:
            problems.append("%s: vsUtils module membership changed or unrecorded across the traversal" % bone)
        tokens = d.get("tokens")
        if not isinstance(tokens, list) or not isinstance(d.get("references"), list) or \
                len(tokens) != len(d["references"]) or len(set(tokens)) != len(tokens):
            problems.append("%s: iterator tokens do not account for the reference rows" % bone)
        rows = d.get("references")
        if not isinstance(rows, list):
            problems.append("%s: no reference list" % bone)
            continue
        if len(rows) != len(REF_ROLES):
            problems.append("%s: %d references, expected %d" % (bone, len(rows), len(REF_ROLES)))
        for r in rows:
            if not isinstance(r, dict) or "unreadable" in r or not isinstance(r.get("owner_handle"), int) or \
                    not r.get("owner") or not r.get("attribute"):
                problems.append("%s: unreadable or incomplete reference %r" % (bone, r))
        seen = {}
        for role, attr in REF_ROLES:
            hits = [r for r in rows if isinstance(r, dict) and r.get("role") == role]
            if len(hits) != 1:
                problems.append("%s: %d %s references" % (bone, len(hits), role))
                continue
            r = hits[0]
            if r.get("attribute") != attr:
                problems.append("%s: %s reference through %r" % (bone, role, r.get("attribute")))
            if not ids.get(role) or r.get("owner") != ids.get(role):
                problems.append("%s: %s owner %r is not the binding's live %r" % (bone, role, r.get("owner"),
                                                                                 ids.get(role)))
            seen[role] = r.get("owner")
        extra = [r for r in rows if isinstance(r, dict) and r.get("role") not in [x for x, _ in REF_ROLES]]
        if extra:
            problems.append("%s: unexpected references %r" % (bone, extra))
        if (seen.get("animset") or [None, None, None])[2] != target:
            problems.append("%s: operators owner is not the selected instance's animation set" % bone)
        if d.get("pass") is not True or b.get("would_pass") is not True:
            problems.append("%s: the observer's own verdict is not a pass" % bone)
        seen["expression"] = ids.get("expression")
        owners[bone] = seen
    return problems, owners


def undo(cap):
    return ((cap or {}).get("session") or {}).get("undo") or {}


class Report(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.info, self.findings = [], {}, []
        self.ids = Q.opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap = {}
        for step in STEPS:
            data = Q.opt_json(os.path.join(self.q, "observations", "OT1-%s.json" % step))
            if isinstance(data, dict) and isinstance(data.get("pid"), int):
                self.cap[step] = data

    def check(self, gate, cid, ok, detail=None):
        self.checks.append({"gate": gate, "id": cid, "pass": bool(ok), "detail": None if ok else detail})
        return ok

    def ev(self, *parts):
        return os.path.join(self.q, "evidence", *parts)


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
    path = os.path.join(R.q, "sessions", "OT1_KRYSTAL.dmx")
    E("sessions.never_saved", os.path.isfile(path) and Q.sha(path) == c["pins"]["r2_fixture_sha256"])
    restoration(R)
    if any(s not in cap for s in STEPS):
        E("complete", False, "missing captures: %s" % [s for s in STEPS if s not in cap])
        return
    pids = set(cap[s]["pid"] for s in STEPS)
    docs = set(((cap[s].get("session") or {}).get("document") or u"").lower() for s in STEPS)
    E("process.one_sfm_process_on_the_disposable_session",
      len(pids) == 1 and len(docs) == 1 and list(docs)[0].endswith(SESSION_DOC), (sorted(pids), sorted(docs)))
    heads = [(cap[s].get("session") or {}).get("head_seconds") for s in STEPS]
    shots = set((cap[s].get("session") or {}).get("shot") for s in STEPS)
    E("session.shot15_and_time_never_moved", shots == set([SHOT]) and all(close(h, heads[0], EXACT) for h in heads)
      and close(heads[0], 0.2083, 1e-3), (sorted(shots), heads))
    E("hooks.installed_at_base", sorted(cap["BASE"].get("hooks_installed") or []) == HOOKS,
      cap["BASE"].get("hooks_installed"))
    E("hooks.removed_at_abort", cap["ABORT"].get("hooks_removed") is True)
    instance = cap["BASE"].get("instance") or {}
    key = instance.get("animset_key") if isinstance(instance, dict) else None
    target = key[1] if isinstance(key, list) and len(key) == 3 else None
    sets = dict((s, Q.sets_by_handle(cap[s])) for s in STEPS)
    model = ((sets["BASE"].get(target) or {}).get("model") or {}).get("model")
    peers = sorted(n for n, s in sets["BASE"].items() if n != target and ((s.get("model") or {}).get("model") == model))
    E("instance.target_and_same_model_peer", target in sets["BASE"] and len(peers) >= 1 and model is not None,
      {"target": target, "peers": peers, "model": model})
    E("instance.same_selected_instance", bool(instance) and all((cap[s].get("instance") or {}) == instance
                                                                 for s in STEPS))
    E("record.body_present", all(isinstance(cap[s].get("record"), dict) for s in STEPS))
    begins = dict((s, Q.events(cap[s], "apply-begin")) for s in STEPS)
    E("operations.only_the_two_body_applies",
      [(e.get("preset"), e.get("preset_kind")) for e in begins["APPLY"]] == [(BODY, u"body")] and
      [(e.get("preset"), e.get("preset_kind")) for e in begins["ABORT"]] == [(BODY, u"body")] and
      not any(begins[s] for s in ("BASE", "UNDO", "REDO", "UNDO2", "ARM")),
      dict((s, [e.get("preset") for e in v]) for s, v in begins.items()))
    vis = dict((s, [n for n in sets["BASE"] if sets[s].get(n) and Q.set_diff(sets["BASE"][n], sets[s][n])["visibility"]])
               for s in STEPS[1:])
    E("edits.no_visibility_change", not any(vis.values()), vis)
    pre = cap["BASE"].get("preflight") or {}
    side = pre.get("side_effects") or {}
    E("preflight.read_only_no_state_change", isinstance(pre, dict) and bool(pre) and side.get("unchanged") is True
      and isinstance(side.get("before"), dict) and "error" not in side.get("before", {}), side)
    bones = pre.get("bones") or {}
    pf = dict((b, {"would_pass": (bones.get(b) or {}).get("would_pass"),
                   "readers": ((bones.get(b) or {}).get("candidate_scan") or {}).get("readers"),
                   "writers": ((bones.get(b) or {}).get("candidate_scan") or {}).get("writers"),
                   "scan_error": ((bones.get(b) or {}).get("candidate_scan") or {}).get("error"),
                   "unreadable": ((bones.get(b) or {}).get("enumeration") or {}).get("unreadable"),
                   "error": (bones.get(b) or {}).get("error"),
                   "operator_lists": (bones.get(b) or {}).get("operator_lists")}) for b in CHANGED)
    R.info["preflight"] = {"instance": pre.get("instance"), "bones": pf}
    E("preflight.candidate_uniqueness_precondition", pre.get("would_pass") is True and pre.get("error") is None and
      pre.get("instance") == instance and
      all(v["would_pass"] is True and v["readers"] == 1 and v["writers"] == 1 and v["unreadable"] == [] and
          v["scan_error"] is None for v in pf.values()), {"error": pre.get("error"), "bones": pf})
    # Astra DC1: direct DataModel references, at BASE and again at ARM, on the live expressions.
    refs = dict((s, direct_ref_problems(cap[s], target)) for s in ("BASE", "ARM"))
    R.info["direct_refs"] = dict((s, refs[s][1]) for s in refs)
    for s in ("BASE", "ARM"):
        E("dc1.%s_three_live_references_per_expression" % s, not refs[s][0], refs[s][0][:12])
    E("dc1.base_and_arm_same_live_elements", not refs["BASE"][0] and not refs["ARM"][0] and
      refs["BASE"][1] == refs["ARM"][1], (refs["BASE"][1], refs["ARM"][1]))
    arm_pre = cap["ARM"].get("preflight") or {}
    E("preflight.ARM_read_only_and_passing_before_arming",
      arm_pre.get("would_pass") is True and (arm_pre.get("side_effects") or {}).get("unchanged") is True and
      arm_pre.get("instance") == instance, (arm_pre.get("would_pass"), (arm_pre.get("side_effects") or {}).get("unchanged")))
    env = dict((s, cap[s].get("environment")) for s in ("BASE", "ARM"))
    E("dc2.environment_recorded", all(isinstance(e, dict) and isinstance(e.get("vsutils_in_sys_modules_at_capture"),
                                                                           bool) for e in env.values()), env)
    R.info["environment"] = env
    if isinstance(env["BASE"], dict) and env["BASE"].get("vsutils_in_sys_modules_at_capture") is True:
        R.findings.append("vsUtils was already in sys.modules at BASE (a starting-environment observation; the observer "
                          "imports no vsUtils and its membership was unchanged across every traversal)")
    for b, v in sorted(pf.items()):
        if isinstance(v["operator_lists"], list) and len(v["operator_lists"]) != 1:
            R.findings.append("preflight: %s's expression is listed in the operators arrays of %r (membership only; "
                              "outside the candidate's channel scan)" % (b, v["operator_lists"]))
    base_map = cap["BASE"].get("settled_full_map") or {}
    base_fail = sorted(b.get("bone") for b in base_map.get("bones") or [] if not b.get("ok"))
    E("base.precondition_head_and_tail_differ", Q.map_ok(base_map) and base_map["result"] is False and
      base_fail == sorted(CHANGED), base_fail)
    rows = Q.log_rows(R)

    for p in peers:
        R.info.setdefault("peer_diffs", {})[p] = dict((s, target_diff(sets["BASE"].get(p), sets[s].get(p)))
                                                      for s in STEPS[1:])
    peer_same = lambda s: all(not target_diff(sets["BASE"].get(p), sets[s].get(p)) for p in peers)  # noqa: E731
    g = dict((s, graph(cap[s])) for s in STEPS)
    R.info["graphs"] = g
    t = lambda s: sets[s].get(target)  # noqa: E731

    # ---- APPLY ---------------------------------------------------------------------------------------------------
    A = lambda cid, ok, d=None: R.check("APPLY", cid, ok, d)  # noqa: E731
    ap = cap["APPLY"]
    A("operation_returned", len(Q.events(ap, "apply-returned")) == 1 and not Q.events(ap, "apply-raised"),
      [e.get("kind") for e in ap.get("events") or []])
    writes = Q.events(ap, "scale-write")
    A("writes.exactly_the_two_changed_mode3_scales",
      sorted(e.get("bone") for e in writes) == sorted(CHANGED) and all(e.get("static_output_mode") == 3 for e in writes)
      and not Q.events(ap, "scale-write-raised"), [(e.get("bone"), e.get("static_output_mode")) for e in writes])
    pre = []
    for e in writes:
        a, b = e.get("after") or {}, e.get("before") or {}
        ok = (close(a.get("expr_result"), e.get("desired_physical")) and close(a.get("expr_input"), e.get("desired_native"))
              and close(a.get("source"), e.get("desired_native")) and close(a.get("key_value"), e.get("desired_native"))
              and a.get("key_count") == 1 and a.get("output_mode") == 3 and a.get("output_key_count") == 0
              and a.get("output_is_empty") is True and a.get("output_use_default_value") is False
              and all(a.get(k) == b.get(k) for k in ("expression_id", "output_id", "transform_id", "input_channel_id",
                                                     "control_id")) and "error" not in a)
        pre.append({"bone": e.get("bone"), "ok": ok, "expected": e.get("desired_physical"),
                    "expr_result": a.get("expr_result"), "physical_before": b.get("physical_scale"),
                    "physical_after": a.get("physical_scale")})
    A("precommit.expression_results_expected_with_authored_input_and_empty_output", len(pre) == 2 and
      all(r["ok"] for r in pre), pre)
    R.info["precommit"] = pre
    refresh = [e for e in Q.events(ap, "refresh-after") if e.get("label") == u"PROD_APPLY"]
    R.info["after_refresh"] = [{"bone": r.get("bone"), "expr_result": (r.get("after") or {}).get("expr_result"),
                                "physical": (r.get("after") or {}).get("physical_scale")}
                               for e in refresh for r in e.get("scales") or []]
    dv = Q.events(ap, "deferred-verify", record=BODY)
    outcomes = Q.deferred_outcomes(rows, BODY)
    A("deferred.physical_verification_passed_and_matches_cpm_log",
      len(dv) == 1 and dv[0].get("result") is True and dv[0].get("consistent") is True and
      Q.map_ok(dv[0].get("full_map")) and outcomes[:1] == [{"outcome": "committed-verified", "reason": None}],
      {"events": [(e.get("result"), e.get("consistent")) for e in dv], "log": outcomes})
    A("settled.full_map_passes", Q.map_ok(ap.get("settled_full_map")) and ap["settled_full_map"]["result"] is True,
      Q.failures(ap.get("settled_full_map")))
    base_u, apply_u = undo(cap["BASE"]), undo(ap)
    A("history.one_owned_entry", apply_u.get("undo_desc") == APPLY_LABEL and apply_u.get("can_redo") is False and
      (base_u.get("count") is None or apply_u.get("count") is None or apply_u["count"] == base_u["count"] + 1),
      (base_u, apply_u))
    A("peer.untouched", peer_same("APPLY"), R.info.get("peer_diffs"))
    changes = target_diff(t("BASE"), t("APPLY"))
    bone_changes = [x for x in changes if x.startswith("bone ")]
    allowed = ["bone %s.scale" % b for b in CHANGED]
    A("target.bones_change_only_head_and_tail_scale",
      sorted(x.split(" ")[0] + " " + x.split(" ")[1] for x in bone_changes) == sorted(allowed), bone_changes)
    phys = dict((bone_of(r[0]), r[3]) for r in ((t("APPLY") or {}).get("model") or {}).get("bones") or [])
    wanted = dict((e.get("bone"), e.get("desired_physical")) for e in writes)
    A("target.physical_scales_requested", sorted(wanted) == sorted(CHANGED) and
      all(close(phys.get(b), wanted[b]) for b in CHANGED), dict((b, (phys.get(b), wanted.get(b))) for b in CHANGED))

    # ---- UNDO (Undo, Redo, final Undo) ---------------------------------------------------------------------------
    U = lambda cid, ok, d=None: R.check("UNDO", cid, ok, d)  # noqa: E731
    for step, ref, label in (("UNDO", "BASE", "undo"), ("REDO", "APPLY", "redo"), ("UNDO2", "BASE", "final_undo")):
        U("%s.target_fields_equal_%s" % (label, ref.lower()), not target_diff(t(ref), t(step)),
          target_diff(t(ref), t(step))[:12])
        U("%s.scale_graphs_equal_%s" % (label, ref.lower()), not graph_diff(g[ref], g[step]),
          graph_diff(g[ref], g[step]))
        U("%s.peer_untouched" % label, peer_same(step))
        u_ = undo(cap[step])
        if label == "redo":
            U("redo.history", u_.get("undo_desc") == APPLY_LABEL and u_.get("can_redo") is False, u_)
            U("redo.settled_map_passes", Q.map_ok(cap[step].get("settled_full_map")) and
              cap[step]["settled_full_map"]["result"] is True, Q.failures(cap[step].get("settled_full_map")))
        else:
            U("%s.history" % label, u_.get("undo_desc") == base_u.get("undo_desc") and u_.get("can_redo") is True and
              APPLY_LABEL in (u_.get("redo_desc") or u""), u_)

    # ---- ABORT -----------------------------------------------------------------------------------------------------
    X = lambda cid, ok, d=None: R.check("ABORT", cid, ok, d)  # noqa: E731
    arm, ab = cap["ARM"], cap["ABORT"]
    X("armed_once_on_an_unchanged_scene", (arm.get("injector") or {}).get("armed") is True and
      (arm.get("injector") or {}).get("fired") == 0 and not target_diff(t("UNDO2"), t("ARM")),
      (arm.get("injector"), target_diff(t("UNDO2"), t("ARM"))[:6]))
    kinds = [e.get("kind") for e in ab.get("events") or []]
    aw = Q.events(ab, "scale-write")
    inj = Q.events(ab, "injected-failure")
    order_ok = (inj and aw and kinds.index("injected-failure") > max(i for i, k in enumerate(kinds) if k == "scale-write"))
    X("operators_ran_and_verified_before_the_failure",
      sorted(e.get("bone") for e in aw) == sorted(CHANGED) and
      all(close((e.get("after") or {}).get("expr_result"), e.get("desired_physical")) for e in aw) and
      len(inj) == 1 and inj[0].get("bone") == FAIL_BONE and bool(order_ok),
      [(e.get("bone"), (e.get("after") or {}).get("expr_result")) for e in aw] + [kinds])
    raised = Q.events(ab, "apply-raised")
    X("apply_failed_with_verified_recovery", len(raised) == 1 and raised[0].get("error_type") == "RuntimeError" and
      not Q.events(ab, "apply-returned"), [(e.get("error_type"), e.get("error")) for e in raised])
    av = Q.events(ab, "abort-verify")
    log_abort = [r["text"] for r in rows if r["text"].startswith(u"PROD_APPLY_ABORT_VERIFY")]
    X("cpm_abort_verification_true", len(av) == 1 and av[0].get("result") is True and len(log_abort) == 1 and
      u"restored=True" in log_abort[0] and FAIL_TEXT in log_abort[0], ([e.get("result") for e in av], log_abort))
    X("target_fields_equal_arm", not target_diff(t("ARM"), t("ABORT")), target_diff(t("ARM"), t("ABORT"))[:12])
    X("scale_graphs_equal_arm", not graph_diff(g["ARM"], g["ABORT"]), graph_diff(g["ARM"], g["ABORT"]))
    X("history.no_entry_added", undo(ab).get("undo_desc") == undo(arm).get("undo_desc") and
      APPLY_LABEL != undo(ab).get("undo_desc"), (undo(arm), undo(ab)))
    X("peer.untouched", peer_same("ABORT"))
    X("injector.fired_once", (ab.get("injector") or {}).get("fired") == 1 and
      (ab.get("injector") or {}).get("armed") is False, ab.get("injector"))
    R.info["abort_redo_state"] = {"arm": undo(arm), "abort": undo(ab)}
    E("log.no_recovery_or_uncertainty", not any(b_ in r["text"] for r in rows for b_ in BAD_LOG),
      sorted(set(b_ for r in rows for b_ in BAD_LOG if b_ in r["text"])))


def restoration(R):
    c = R.c
    clean = Q.opt_json(R.ev("library_cleanup.json")) or {}
    diffs = clean.get("differences_kept_in_evidence") or []
    char = "Characters/%s/" % c["character_dir"]
    unexpected = [x for x in diffs if not (x["status"] == "changed" and
                                           x["path"] in (char + "character.json", char + "character.json.bak"))]
    R.check("EVIDENCE", "library.no_change_but_the_known_character_rewrite", bool(clean) and not unexpected, unexpected)
    if diffs and not unexpected:
        R.findings.append("character.json rewritten during the run (known F-T01-1 behaviour), restored")
    R.check("EVIDENCE", "restore.library_exactly_as_before", clean.get("files_equal_pre") is True and
            clean.get("folders_equal_pre") is True)
    restore = Q.opt_json(R.ev("restore.json")) or {}
    R.check("EVIDENCE", "restore.published_and_inventories_equal", restore.get("restored") is True,
            restore.get("inventory_problems"))


def verdict(checks):
    gate = lambda name: all(x["pass"] for x in checks if x["gate"] == name)  # noqa: E731
    gates = dict((n, gate(n)) for n in ("EVIDENCE", "APPLY", "UNDO", "ABORT"))
    if not gates["EVIDENCE"]:
        v = "INCOMPLETE"
    elif gates["APPLY"] and gates["UNDO"] and gates["ABORT"]:
        v = "CANDIDATE PASS"
    else:
        v = "CANDIDATE FAIL"
    return v, gates


def markdown(out):
    lines = ["# F-01 OT1 ordering trial: %s" % out["verdict"], "",
             "Qualification CPM `%s` (trial candidate `%s`). Gates: %s." % (
                 out["identities"].get("qualification_cpm_sha256"), out["identities"].get("candidate_cpm_sha256"),
                 ", ".join("%s %s" % (k, "PASS" if v else "FAIL") for k, v in sorted(out["gates"].items()))), ""]
    if out["gates"].get("APPLY") and not out["gates"].get("UNDO"):
        lines += ["**Apply PASS with Undo FAIL: the candidate FAILS.** No additional workaround without renewed "
                  "adjudication.", ""]
    lines += ["| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in out["checks"]:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False, default=repr)[:300].replace("|", "\\|")
        lines.append("| %s | `%s` | %s | %s |" % (x["gate"], x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    info = out.get("info") or {}
    if info.get("preflight"):
        lines += ["", "BASE preflight (read only): " + "; ".join(
            "%s would_pass %s, readers %s, writers %s, unreadable %s%s" % (
                b, v["would_pass"], v["readers"], v["writers"], len(v["unreadable"] or []) if isinstance(
                    v["unreadable"], list) else v["unreadable"], (", error %s" % v["error"]) if v["error"] else "")
            for b, v in sorted(info["preflight"]["bones"].items())) + "."]
    if info.get("precommit"):
        lines += ["", "Precommit (inside the transaction, after the operator): " + "; ".join(
            "%s result %s (expected %s), physical %s -> %s" % (r["bone"], r["expr_result"], r["expected"],
                                                             r["physical_before"], r["physical_after"])
            for r in info["precommit"]) + "."]
    if info.get("after_refresh") is not None:
        lines += ["", "After CPM's refresh: " + ("; ".join("%s result %s, physical %s" % (
            r["bone"], r["expr_result"], r["physical"]) for r in info["after_refresh"]) or "not observed") + "."]
    if out["findings"]:
        lines += ["", "Findings:"] + ["- %s" % f for f in out["findings"]]
    return "\n".join(lines) + "\n"


def run(c):
    R = Report(c)
    evaluate(R)
    v, gates = verdict(R.checks)
    out = {"format": "F01-OT1-verdict-v1", "verdict": v, "gates": gates, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in R.checks if not x["pass"]], "info": R.info, "findings": R.findings,
           "analyzer_sha256": Q.sha(os.path.abspath(__file__)),
           "captures": dict((n, Q.sha(os.path.join(R.q, "observations", n)))
                            for n in sorted(os.listdir(os.path.join(R.q, "observations")))
                            if n.endswith(".json")) if os.path.isdir(os.path.join(R.q, "observations")) else {}}
    md = markdown(out)
    for name, data in (("OT1_VERDICT.json", json.dumps(out, indent=1, sort_keys=True, default=repr)), ("OT1_VERDICT.md", md)):
        fd = os.open(R.ev(name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(md)
    return 0 if v == "CANDIDATE PASS" else 1


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import ot1_tool
    return run(ot1_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
