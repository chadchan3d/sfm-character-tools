# -*- coding: utf-8 -*-
"""F-01 Q1: the offline analysis of the PS-2 Body Preset and duplicate-model Undo diagnostic. Python 3, run with -I
after restore (SFM closed). Read-only except for its two report files.

It does two separate things:
1. Evidence completeness (the diagnostic's PASS/STOP): identities, every required capture, the hooks installed and
   removed, every boundary observed with a complete scale map, CPM's own result reproduced by the observer's map,
   one SFM process on the disposable session, no intervening visibility or other edits in the duplicate comparison,
   only the seeded preset in the library, restoration exact. Verdict "EVIDENCE COMPLETE" only when every check passes.
2. Analysis (descriptive, never a product verdict): for each Body Preset operation, the failing bones and the exact
   failing predicate at the precommit, refresh-before, refresh-after, deferred and settled boundaries, with requested
   and physical values and the static classification; for the duplicate Apply/Undo, the field-level differences of the
   target and of the peer between BEFORE, APPLY and UNDO (controls, bone positions, orientations, scales, flex weights,
   visibility). It names what the evidence shows and leaves the cause decision to review.

usage: python -I q1_analyze.py Q1.json [--replay]      (or: q1_tool.py Q1.json analyze | replay)
Writes Q/evidence/Q1_REPORT.json and Q1_REPORT.md (exclusive create); --replay writes Q1_REPORT_REPLAY.json and .md
instead, for a finished run whose Q1_REPORT exists (unchanged). Exit 0 only on "EVIDENCE COMPLETE".
"""
from __future__ import print_function

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S3_TOOLS = os.path.join(HERE, "..", "..", "f01_full_body_s3", "tools")
REQUIRED = ("BASE", "BODY", "DUP-BEFORE", "DUP-APPLY", "DUP-UNDO")
BODY, DUP, HAPPY = u"Body", u"PS2 Dup Body", u"Happy"
HOOKS = ["prod_apply", "prod_bs_authored_matches", "prod_bs_index_verify_saved", "same_time_refresh"]
BAD_LOG = ("RECOVERY_BLOCKED", "undo-uncertain", "abort-unverified", "recovery-unverified", "abort-failed")
SESSION_DOC = u"q1_krystal.dmx"
NOISE = 1e-6


def read_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def opt_json(path):
    try:
        return read_json(path) if os.path.isfile(path) else None
    except ValueError:
        return None


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def events(cap, kind, **match):
    return [e for e in (cap or {}).get("events") or [] if isinstance(e, dict) and e.get("kind") == kind and
            all(e.get(k) == v for k, v in match.items())]


def map_ok(m):
    """A complete scale map: no error, a boolean result, one row per saved bone."""
    return isinstance(m, dict) and "error" not in m and isinstance(m.get("result"), bool) and \
        isinstance(m.get("bones"), list) and bool(m["bones"])


def failures(m):
    if not isinstance(m, dict):
        return None
    return [{"bone": b.get("bone"), "predicate": b.get("predicate"), "desired": b.get("desired"),
             "physical": b.get("physical"), "delta": b.get("delta"), "static": b.get("static"),
             "classification": b.get("classification"),
             "physical_matches_lerp": (b.get("trace") or {}).get("physical_matches_lerp")}
            for b in m.get("bones") or [] if not b.get("ok")]


def num_diff(a, b):
    """The largest absolute difference between two raw values (numbers or vectors); None when not comparable."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(float(a) - float(b))
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and \
            all(isinstance(x, (int, float)) for x in a + b):
        return max([abs(float(x) - float(y)) for x, y in zip(a, b)] or [0.0])
    return None


def set_diff(a, b):
    """Field-level differences between two raw animation-set captures."""
    out = {"controls": [], "bones": [], "flexes": [], "visibility": []}
    if a is None or b is None:
        return {"missing": True}
    ca, cb = a.get("controls") or {}, b.get("controls") or {}
    for name in sorted(set(ca) | set(cb)):
        for attr in sorted(set(ca.get(name, {})) | set(cb.get(name, {}))):
            x, y = ca.get(name, {}).get(attr), cb.get(name, {}).get(attr)
            if x != y:
                out["controls"].append({"control": name, "attribute": attr, "before": x, "after": y,
                                        "max_abs": num_diff(x, y)})
    ma, mb = a.get("model") or {}, b.get("model") or {}
    ba = dict((r[0], r[1:]) for r in ma.get("bones") or [])
    bb = dict((r[0], r[1:]) for r in mb.get("bones") or [])
    for name in sorted(set(ba) | set(bb)):
        x, y = ba.get(name), bb.get(name)
        if x != y:
            fields = {}
            for i, f in enumerate(("position", "orientation", "scale")):
                if x is None or y is None or x[i] != y[i]:
                    fields[f] = {"before": None if x is None else x[i], "after": None if y is None else y[i],
                                 "max_abs": None if x is None or y is None else num_diff(x[i], y[i])}
            out["bones"].append({"bone": name, "fields": fields})
    fa = dict((r[0], r[1]) for r in ma.get("flexes") or [])
    fb = dict((r[0], r[1]) for r in mb.get("flexes") or [])
    for name in sorted(set(fa) | set(fb)):
        if fa.get(name) != fb.get(name):
            out["flexes"].append({"flex": name, "before": fa.get(name), "after": fb.get(name),
                                  "max_abs": num_diff(fa.get(name), fb.get(name))})
    for key in ("visible", "skin", "body", "children"):
        if ma.get(key) != mb.get(key):
            out["visibility"].append({"field": key, "before": ma.get(key), "after": mb.get(key)})
    return out


def diff_summary(d):
    if d.get("missing"):
        return "missing"
    parts = []
    for key in ("controls", "bones", "flexes", "visibility"):
        rows = d[key]
        if not rows:
            continue
        sizes = []
        for r in rows:
            if key == "bones":
                sizes += [f["max_abs"] for f in r["fields"].values() if f["max_abs"] is not None]
            elif r.get("max_abs") is not None:
                sizes.append(r["max_abs"])
        above = sum(1 for s in sizes if s > NOISE)
        parts.append("%s %d (%d above %g, max %s)" % (key, len(rows), above, NOISE,
                                                       ("%.3g" % max(sizes)) if sizes else "n/a"))
    return "; ".join(parts) or "identical"


def set_field_problems(cap):
    """Kit correction after Q1 run 1: every animation set keeps its identity and control fields; game-model fields are
    required only of sets that have a game model (a camera or light set has none: the observer records model None).
    The capture's own error list must be empty and its session readable."""
    out = []
    if cap.get("errors"):
        out.append("capture errors %r" % (cap.get("errors"),))
    if not isinstance(cap.get("session"), dict):
        out.append("session unreadable")
    sets = cap.get("animation_sets")
    if not isinstance(sets, list) or not sets:
        return out + ["no animation sets"]
    for s in sets:
        if not isinstance(s, dict) or not isinstance(s.get("name"), str) or not isinstance(s.get("handle"), int) or \
                not isinstance(s.get("controls"), dict):
            out.append("set without identity or controls: %r" % ((s or {}).get("name"),))
            continue
        m = s.get("model")
        if m is None:
            continue
        if not isinstance(m, dict) or not isinstance(m.get("bones"), list) or not isinstance(m.get("flexes"), list) or \
                not isinstance(m.get("handle"), int) or "visible" not in m:
            out.append("game-model fields missing in %r" % s["name"])
    if not any(isinstance(s, dict) and isinstance(s.get("model"), dict) for s in sets):
        out.append("no animation set with a game model")
    return out


def precommit_sequence(events_, n, deferred_map):
    """Kit correction after Q1 run 1: CPM's authored-scale check sequence for an operation with n changed existing
    scales, as the source makes it (prod_bs_authored_matches): n pre-write calls on the original values (through
    prod_bs_evaluated_matches while the plan is built), n post-write calls (prod_bs_write_existing_scale), n precommit
    calls before FinishUndo. Returns (problems, rows). Each call's bone (its control), native value, result and its own
    snapshot's authored fields are checked; the requested native value is derived from the deferred map's desired
    physical value and the snapshot's lo/hi."""
    rows, problems = [], []
    for e in events_:
        s = e.get("snapshot") if isinstance(e.get("snapshot"), dict) else {}
        bone = (((e.get("binding") or {}).get("bone_row") or {}).get("_control") or {}).get("element")
        rows.append({"seq": e.get("seq"), "bone": bone, "native": e.get("desired_native"), "result": e.get("result"),
                     "key_value": s.get("key_value"), "source": s.get("source"), "expr_input": s.get("expr_input"),
                     "expr_result": s.get("expr_result"), "physical": s.get("physical_scale"), "lo": s.get("lo"),
                     "hi": s.get("hi")})
    if n is None or len(rows) != 3 * n or n == 0:
        return ["expected 3 x %r calls, found %d" % (n, len(rows))], rows
    stages = {"pre-write": rows[:n], "post-write": rows[n:2 * n], "precommit": rows[2 * n:]}
    for name, part in stages.items():
        for r in part:
            r["stage"] = name
    desired = dict((b.get("bone"), b.get("desired")) for b in (deferred_map or {}).get("bones") or [])

    def close(a, b, tol=1e-6):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(float(a) - float(b)) <= tol
    bones = [r["bone"] for r in stages["post-write"]]
    if [r["bone"] for r in stages["precommit"]] != bones or sorted(r["bone"] for r in stages["pre-write"]) != \
            sorted(bones) or len(set(bones)) != n or None in bones:
        problems.append("the three stages do not cover the same %d bones: %r" % (n, [r["bone"] for r in rows]))
    for r in rows:
        if r["result"] is not True:
            problems.append("%s %s returned %r" % (r["stage"], r["bone"], r["result"]))
        if not (close(r["key_value"], r["native"]) and close(r["source"], r["native"]) and
                close(r["expr_input"], r["native"])):
            problems.append("%s %s authored fields differ from the checked value" % (r["stage"], r["bone"]))
    for r in stages["post-write"] + stages["precommit"]:
        lo, hi, want = r["lo"], r["hi"], desired.get(r["bone"])
        if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and hi != lo and
                close(r["native"], (float(want) - lo) / (hi - lo) if isinstance(want, (int, float)) else None)):
            problems.append("%s %s native %r is not the requested scale %r" % (r["stage"], r["bone"], r["native"], want))
    for r in stages["pre-write"]:
        post = [p for p in stages["post-write"] if p["bone"] == r["bone"]]
        if post and close(r["native"], post[0]["native"], 1e-9):
            problems.append("pre-write %s already holds the requested value (not a changed scale)" % r["bone"])
    return problems, rows


def propagation(seq_rows, maps, bones):
    """Per changed bone and boundary: the expression input, the expression result and the physical scale, from CPM's
    own snapshots (the authored-check calls) and from the boundary maps' traces. Values missing from a capture are
    reported as None, never inferred."""
    out = []
    for r in seq_rows:
        out.append({"boundary": r.get("stage"), "bone": r.get("bone"), "expr_input": r.get("expr_input"),
                    "expr_result": r.get("expr_result"), "physical": r.get("physical")})
    for label, m in maps:
        for b in (m or {}).get("bones") or []:
            if b.get("bone") in bones:
                ex = ((b.get("trace") or {}).get("expression") or {})
                ex = ex if isinstance(ex, dict) else {}
                out.append({"boundary": label, "bone": b.get("bone"), "expr_input": ex.get("value"),
                            "expr_result": ex.get("result"), "physical": b.get("physical")})
    return out


def sets_by_handle(cap):
    """{animation-set handle: raw set}; the selection token names its instance by native handle (animset_key[1])."""
    return dict((s.get("handle"), s) for s in (cap or {}).get("animation_sets") or [] if isinstance(s, dict))


class Report(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.analysis, self.findings = [], {}, []
        self.ids = opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap = {}
        for step in REQUIRED + ("HAPPY",):
            data = opt_json(os.path.join(self.q, "observations", "Q1-%s.json" % step))
            if isinstance(data, dict) and isinstance(data.get("pid"), int):
                self.cap[step] = data

    def check(self, cid, ok, detail=None):
        self.checks.append({"id": cid, "pass": bool(ok), "detail": detail})
        return ok

    def ev(self, *parts):
        return os.path.join(self.q, "evidence", *parts)


def log_rows(R):
    logs = R.ev("logs")
    if S3_TOOLS not in sys.path:
        sys.path.insert(0, S3_TOOLS)
    import s3_compare as S3C
    return S3C.parse_logs(logs) if os.path.isdir(logs) else []


def deferred_outcomes(rows, preset):
    out = []
    for r in rows:
        m = re.search(r"PROD_APPLY_DEFERRED_VERIFY outcome=u?'([^']*)' reason=(u?'[^']*'|None) .*preset=u?'([^']*)'",
                      r["text"])
        if m and m.group(3) == preset:
            out.append({"outcome": m.group(1), "reason": m.group(2).strip("u'") if m.group(2) != "None" else None})
    return out


def pending_scale_count(rows, preset):
    for r in rows:
        m = re.search(r"PROD_APPLY outcome='verification-pending' .*preset=u?'([^']*)' .*changed_existing_scales=(\d+)",
                      r["text"])
        if m and m.group(1) == preset:
            return int(m.group(2))
    return None


def evaluate(R):
    chk, cap, c = R.check, R.cap, R.c
    want = c["pins"]["qualification_cpm_sha256"]
    chk("identity.qualification_build", R.ids.get("qualification_cpm_sha256") == want and
        R.ids.get("candidate_cpm_sha256") == c["pins"]["candidate_cpm_sha256"], R.ids.get("qualification_cpm_sha256"))
    body_settled = ((cap.get("BODY") or {}).get("settled_full_map") or {}).get(BODY)
    happy_required = map_ok(body_settled) and body_settled["result"] is False
    steps = list(REQUIRED) + (["HAPPY"] if happy_required else [])
    for step in steps:
        if not chk("captured.%s" % step, step in cap):
            continue
        d = cap[step]
        chk("cpm.%s" % step, d.get("cpm_build_sha256") == want, d.get("cpm_build_sha256"))
        problems = set_field_problems(d)
        chk("fields.%s" % step, not problems, problems)
    if any(s not in cap for s in steps):
        chk("complete", False, "missing captures: %s" % [s for s in steps if s not in cap])
        return
    pids = set(cap[s]["pid"] for s in steps)
    docs = set(((cap[s].get("session") or {}).get("document") or u"").lower() for s in steps)
    chk("process.one_sfm_process_on_the_disposable_session", len(pids) == 1 and len(docs) == 1 and
        list(docs)[0].endswith(SESSION_DOC), (sorted(pids), sorted(docs)))
    chk("hooks.installed_at_base", sorted(cap["BASE"].get("hooks_installed") or []) == HOOKS,
        cap["BASE"].get("hooks_installed"))
    chk("hooks.removed_at_dup_undo", cap["DUP-UNDO"].get("hooks_removed") is True)
    rows = log_rows(R)

    # Body Preset: every boundary observed with a complete map
    b = cap["BODY"]
    chk("body.operation_observed", len(events(b, "apply-begin", preset=BODY, preset_kind=u"body")) == 1,
        [e.get("preset") for e in events(b, "apply-begin")])
    pre = events(b, "precommit-authored")
    n = pending_scale_count(rows, BODY)
    rb, ra = events(b, "refresh-before", operation=BODY), events(b, "refresh-after")
    dv = events(b, "deferred-verify", record=BODY)
    seq_problems, seq_rows = precommit_sequence(pre, n, dv[0].get("full_map") if dv else None)
    chk("body.authored_check_sequence", not seq_problems, seq_problems[:8])
    chk("body.refresh_boundary_maps", len(rb) == 1 and map_ok(rb[0].get("full_map")) and len(ra) >= 1 and
        map_ok(ra[0].get("full_map")), [(e.get("kind"), (e.get("full_map") or {}).get("error")) for e in rb + ra])
    outcomes = deferred_outcomes(rows, BODY)
    chk("body.deferred_map_matches_cpm",
        len(dv) == 1 and map_ok(dv[0].get("full_map")) and dv[0].get("consistent") is True and len(outcomes) == 1 and
        (outcomes[0]["outcome"] == "committed-verified") == bool(dv[0].get("result")),
        {"events": len(dv), "consistent": dv[0].get("consistent") if dv else None, "log": outcomes})
    chk("body.settled_map", map_ok(body_settled), (body_settled or {}).get("error"))
    if happy_required:
        h = cap["HAPPY"]
        chk("happy.operation_observed", len(events(h, "apply-begin", preset=HAPPY)) == 1)
        hb, ha = events(h, "refresh-before", operation=HAPPY), events(h, "refresh-after")
        chk("happy.refresh_boundary_maps", len(hb) == 1 and map_ok(hb[0].get("full_map")) and len(ha) >= 1 and
            map_ok(ha[0].get("full_map")))
        chk("happy.settled_map", map_ok(((h.get("settled_full_map") or {}).get(BODY))))

    # Duplicate-model comparison: two instances, the same target, no intervening edits
    instance = cap["DUP-BEFORE"].get("instance") or {}
    key = instance.get("animset_key") if isinstance(instance, dict) else None
    target = key[1] if isinstance(key, list) and len(key) == 3 else None
    before, after, undone = (sets_by_handle(cap[s]) for s in ("DUP-BEFORE", "DUP-APPLY", "DUP-UNDO"))
    model = ((before.get(target) or {}).get("model") or {}).get("model")
    peers = sorted(n for n, s in before.items() if n != target and ((s.get("model") or {}).get("model") == model))
    chk("dup.two_instances_of_the_model", target in before and len(peers) >= 1, {"target": target, "peers": peers})
    chk("dup.same_selected_instance", all((cap[s].get("instance") or {}) == instance
                                          for s in ("DUP-APPLY", "DUP-UNDO")) and bool(instance))
    da = cap["DUP-APPLY"]
    chk("dup.apply_observed", len(events(da, "apply-begin", preset=DUP, preset_kind=u"body")) == 1 and
        len(events(da, "deferred-verify", record=DUP)) == 1 and
        map_ok(events(da, "deferred-verify", record=DUP)[0].get("full_map")))
    undo_a = ((da.get("session") or {}).get("undo") or {})
    undo_u = ((cap["DUP-UNDO"].get("session") or {}).get("undo") or {})
    chk("dup.history_is_the_apply_then_its_undo",
        u"Apply Body Preset" in (undo_a.get("undo_desc") or u"") and
        u"Apply Body Preset" in (undo_u.get("redo_desc") or u"") and not events(cap["DUP-UNDO"], "apply-begin"),
        (undo_a, undo_u))
    vis = dict((s, dict((n, set_diff(before.get(n), x.get(n))["visibility"] if before.get(n) and x.get(n) else None)
                        for n in before)) for s, x in (("APPLY", after), ("UNDO", undone)))
    chk("dup.no_intervening_visibility_edits", all(v == [] for per in vis.values() for v in per.values()), vis)

    # Library, restoration, sessions
    clean = opt_json(R.ev("library_cleanup.json")) or {}
    diffs = clean.get("differences_kept_in_evidence") or []
    seeded = sorted((opt_json(R.ev("seed.json")) or {}).get("seeded") or {})
    char = "Characters/%s/" % c["character_dir"]
    unexpected = [x for x in diffs if not (
        (x["status"] == "added" and x["path"] in [char + "Body Presets/" + s for s in seeded]) or
        (x["status"] == "changed" and x["path"] in (char + "character.json", char + "character.json.bak")))]
    chk("library.only_the_seeded_preset_and_known_character_rewrite", not unexpected and bool(seeded), unexpected)
    if [x for x in diffs if x["status"] == "changed"]:
        R.findings.append("character.json rewritten during the run (known F-T01-1 Body behaviour), restored")
    chk("log.no_recovery_or_uncertainty", not any(b_ in r["text"] for r in rows for b_ in BAD_LOG),
        sorted(set(b_ for r in rows for b_ in BAD_LOG if b_ in r["text"])))
    restore = opt_json(R.ev("restore.json")) or {}
    chk("restore.library_exactly_as_before", clean.get("files_equal_pre") is True and
        clean.get("folders_equal_pre") is True)
    chk("restore.published_and_inventories_equal", restore.get("restored") is True, restore.get("inventory_problems"))
    path = os.path.join(R.q, "sessions", "Q1_KRYSTAL.dmx")
    chk("sessions.never_saved", os.path.isfile(path) and sha(path) == c["pins"]["r2_fixture_sha256"])

    # ---- Analysis (descriptive) -------------------------------------------------------------------------------
    def stage(m):
        return None if not isinstance(m, dict) else {"result": m.get("result"), "failing": failures(m),
                                                     "would_raise": m.get("would_raise")}
    body = {"log_outcomes": outcomes,
            "precommit": seq_rows,
            "refresh_before": stage(rb[0].get("full_map")) if rb else None,
            "refresh_after": stage(ra[0].get("full_map")) if ra else None,
            "deferred": stage(dv[0].get("full_map")) if dv else None,
            "settled": stage(body_settled)}
    if happy_required:
        h = cap["HAPPY"]
        hb, ha = events(h, "refresh-before", operation=HAPPY), events(h, "refresh-after")
        body["happy_refresh_before"] = stage(hb[0].get("full_map")) if hb else None
        body["happy_refresh_after"] = stage(ha[0].get("full_map")) if ha else None
        body["happy_settled"] = stage((h.get("settled_full_map") or {}).get(BODY))
    changed = sorted(set(r["bone"] for r in seq_rows if r.get("bone")))
    maps = [("refresh_before", rb[0].get("full_map") if rb else None),
            ("refresh_after", ra[0].get("full_map") if ra else None),
            ("deferred", dv[0].get("full_map") if dv else None), ("settled", body_settled)]
    if happy_required:
        maps += [("happy_refresh_before", hb[0].get("full_map") if hb else None),
                 ("happy_refresh_after", ha[0].get("full_map") if ha else None),
                 ("happy_settled", (cap["HAPPY"].get("settled_full_map") or {}).get(BODY))]
    body["propagation"] = propagation(seq_rows, maps, changed)
    d_res = (body.get("deferred") or {}).get("result")
    s_res = (body.get("settled") or {}).get("result")
    if d_res is True:
        body["reading"] = "not reproduced: the deferred full map passed"
    elif d_res is False and s_res is True:
        body["reading"] = ("deferred full map failed and the settled map passes after an ordinary event turn; precommit "
                           "authored checks %s" % ("all passed" if all(p["result"] for p in body["precommit"])
                                                    else "did not all pass"))
    elif d_res is False and s_res is False:
        hs = (body.get("happy_settled") or {}).get("result")
        body["reading"] = ("the full map still fails when settled%s" % (
            "; it passes after Happy's refresh" if hs is True else "; it also fails after Happy" if hs is False else ""))
    else:
        body["reading"] = "not determinable from the evidence"
    dup_deferred = events(da, "deferred-verify", record=DUP)
    names = dict((h, (s or {}).get("name")) for h, s in before.items())
    dup = {"target": target, "target_name": names.get(target), "peers": peers,
           "peer_names": [names.get(p) for p in peers],
           "log_outcomes": deferred_outcomes(rows, DUP),
           "deferred": stage(dup_deferred[0].get("full_map")) if dup_deferred else None,
           "target_diffs": {}, "peer_diffs": {}}
    for label, x, y in (("before_to_apply", before, after), ("apply_to_undo", after, undone),
                        ("before_to_undo", before, undone)):
        td = set_diff(x.get(target), y.get(target))
        dup["target_diffs"][label] = {"summary": diff_summary(td), "detail": td}
        dup["peer_diffs"][label] = dict((p, diff_summary(set_diff(x.get(p), y.get(p)))) for p in peers)
    R.analysis = {"body": body, "duplicate": dup}
    truncated = sorted(set("%s/%s" % (step, e.get("kind")) for step, d in cap.items() for e in d.get("events") or []
                           if isinstance(e, dict) and u"<depth>" in json.dumps(e.get("full_map"))))
    if truncated:
        R.findings.append("evidence limitation: boundary maps hold depth-truncated values (observer depth bound at "
                          "capture), e.g. the output-channel log rows, in %s; they are not inferred; the settled maps "
                          "carry them" % ", ".join(truncated))


def markdown(out):
    lines = ["# F-01 Q1 PS-2 diagnostic: %s" % out["verdict"], "",
             "Qualification CPM `%s` (candidate `%s`). This report decides only whether the evidence is complete; the "
             "analysis is descriptive." % (out["identities"].get("qualification_cpm_sha256"),
                                           out["identities"].get("candidate_cpm_sha256")), "",
             "| Evidence check | Result | Detail |", "|---|---|---|"]
    for x in out["checks"]:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False)[:300].replace("|", "\\|")
        lines.append("| `%s` | %s | %s |" % (x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    a = out.get("analysis") or {}
    body, dup = a.get("body") or {}, a.get("duplicate") or {}
    if body:
        lines += ["", "## Body Preset scale verification", "", "Reading: %s." % body.get("reading"), "",
                  "| Boundary | Map result | Failing bones (predicate, desired, physical) |", "|---|---|---|"]
        for key in ("refresh_before", "refresh_after", "deferred", "settled", "happy_refresh_before",
                    "happy_refresh_after", "happy_settled"):
            st = body.get(key)
            if st is None:
                continue
            fails = "; ".join("%s (%s, %s, %s)" % (f["bone"], f["predicate"], f["desired"], f["physical"])
                              for f in st.get("failing") or []) or "none"
            lines.append("| %s | %s | %s |" % (key, st.get("result"), fails.replace("|", "\\|")))
        lines += ["", "Authored-check sequence (CPM's six calls for two changed scales): " + ", ".join(
            "%s %s %s" % (p.get("stage"), p.get("bone"), p.get("result")) for p in body.get("precommit") or []) + ".",
                  "", "Propagation of the changed scales (expression input, expression result, physical scale):", "",
                  "| Boundary | Bone | Expression input | Expression result | Physical |", "|---|---|---|---|---|"]
        for row in body.get("propagation") or []:
            lines.append("| %s | %s | %s | %s | %s |" % (row["boundary"], row["bone"], row["expr_input"],
                                                       row["expr_result"], row["physical"]))
        lines += ["", "CPM log: %s." % body.get("log_outcomes")]
    if dup:
        lines += ["", "## Duplicate-model Apply and Undo", "", "Target `%s` (handle %s); peers %s; CPM log %s." % (
            dup.get("target_name"), dup.get("target"), dup.get("peer_names"), dup.get("log_outcomes")), "",
            "| Comparison | Target | Peers |", "|---|---|---|"]
        for label in ("before_to_apply", "apply_to_undo", "before_to_undo"):
            lines.append("| %s | %s | %s |" % (label, dup["target_diffs"][label]["summary"],
                                              json.dumps(dup["peer_diffs"][label])))
    if out["findings"]:
        lines += ["", "Findings:"] + ["- %s" % f for f in out["findings"]]
    return "\n".join(lines) + "\n"


def run(c, replay=False):
    """replay=True re-evaluates a finished run's preserved evidence into Q1_REPORT_REPLAY (exclusive create), naming
    the original report and the captures it read by SHA-256; nothing of the run changes."""
    R = Report(c)
    original = None
    if replay:
        path = R.ev("Q1_REPORT.json")
        if not os.path.isfile(path):
            print("REPLAY REFUSED: the original Q1_REPORT.json must exist")
            return 2
        first = read_json(path)
        original = {"Q1_REPORT.json": sha(path), "Q1_REPORT.md": sha(R.ev("Q1_REPORT.md")),
                    "verdict": first.get("verdict"), "failed": first.get("failed")}
    evaluate(R)
    failed = [x["id"] for x in R.checks if not x["pass"]]
    out = {"format": "F01-Q1-report-v1", "verdict": "EVIDENCE COMPLETE" if not failed else "EVIDENCE INCOMPLETE",
           "identities": R.ids, "checks": R.checks, "failed": failed, "analysis": R.analysis, "findings": R.findings,
           "analyzer_sha256": sha(os.path.abspath(__file__))}
    names = ("Q1_REPORT.json", "Q1_REPORT.md")
    if replay:
        obs = os.path.join(R.q, "observations")
        out["replay"] = {"original": original, "captures": dict((n, sha(os.path.join(obs, n)))
                                                               for n in sorted(os.listdir(obs)) if n.endswith(".json")),
                         "note": "Replay with the corrected analyzer (set fields only for sets with a game model; CPM's "
                                 "six-call authored-check sequence). The original Q1_REPORT is unchanged. The boundary "
                                 "maps' output-channel log rows were cut by the run's observer depth bound and are not "
                                 "recoverable; nothing here infers them."}
        names = ("Q1_REPORT_REPLAY.json", "Q1_REPORT_REPLAY.md")
    md = markdown(out)
    if replay:
        md = md.replace("# F-01 Q1 PS-2 diagnostic:", "# F-01 Q1 PS-2 diagnostic, replay with the corrected analyzer:", 1)
        md += ("\nReplay of the original report (%s, sha256 %s), unchanged.\n" %
               (original["verdict"], original["Q1_REPORT.json"]))
    for name, data in ((names[0], json.dumps(out, indent=1, sort_keys=True)), (names[1], md)):
        fd = os.open(R.ev(name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(md)
    return 0 if not failed else 1


def main(argv):
    if len(argv) not in (2, 3) or (len(argv) == 3 and argv[2] != "--replay"):
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import q1_tool
    return run(q1_tool.S.load(argv[1]), replay=len(argv) == 3)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
