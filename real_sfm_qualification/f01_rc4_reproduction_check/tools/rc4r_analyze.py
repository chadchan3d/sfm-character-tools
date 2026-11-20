# -*- coding: utf-8 -*-
"""F-01 RC4: the verdict of the short native check of Astra's revised verification contract. Python 3, run with -I
after restore, with SFM closed. It never changes the run.

One SFM process on a disposable copy of the R2 fixture (RC4R_SESSION.dmx), never saved. Tails N: a fresh Tails rigged
with rig_biped_simple (23 controls; rig_chest drives bip_spine_3), placed away from the others. "RC4 Sit" is saved from
the session's original sitting Tails (milestailsprower1; 22 controls), then applied to Tails N (Direction B of the
RC4 run), applied again, and undone once. Every capture's setup line: source milestailsprower1, target Tails N, peer
foxmccouldwm1. Steps: PREP, SAVED, B_BASE, B_APPLY, B_NOOP, B_UNDO.

Gates (a gate with no evaluated check is NOT EVALUATED, never PASS):
  EVIDENCE  identities; every capture from one process with the qualification build, no capture error, complete
            leaf and offsets sidecars; every capture on RC4R_SESSION.dmx in the Motion Editor at one shot and
            playhead; the session copy and the spare never saved; the library changed only by RC4 Sit and its local
            sidecars; library and installation restored exactly; the CPM log collected, with no unverified,
            uncertain, mismatch, failed-Abort or lockout result
  APPLY     CPM adapted the chest (bip_spine_3 to constrained) and verified P7 under the revised envelope (its own
            logged maxima within 0.01 units and 0.1 degrees); one owned history entry; only the drafted written
            channels changed, one key at the mapped tick, every other key unchanged; leaves never authored
  POSTURE   independent of CPM: every non-leaf bone of Tails N, relative to its own rig_root, against the original's
            saved posture, within the revised envelope (0.01 units, 0.1 degrees; maxima recorded); placement, facing
            and direct bone offsets unchanged
  NOOP      the repeated Apply: CPM's P1 planned no insert or update, its no-work result is "no-op", it opened no
            Undo (no P6), and the authored state and history are exactly B_APPLY's
  UNDO      one Undo restores B_BASE exactly (authored state and skeleton) with the Apply's Redo entry
  PEER      the Fox and the original Tails unchanged at every capture
Verdict: AUTOMATED PASS (every gate; acceptance also needs the Owner's visual assessment); FAIL (complete evidence, a
functional gate failed); INCOMPLETE (evidence, preparation or restoration missing or failed).

usage: python -I rc4r_analyze.py RC4R.json      (or: rc4r_tool.py RC4R.json analyze)
"""
from __future__ import print_function

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RC4X_TOOLS = os.path.join(HERE, "..", "..", "f01_rc4_cross_rig", "tools")
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_stage1_fox", "tools"))
sys.path.insert(0, RC4X_TOOLS)
import s1f_analyze as A  # noqa: E402
import rc4x_analyze as X  # noqa: E402

STEPS = ("PREP", "SAVED", "B_BASE", "B_APPLY", "B_NOOP", "B_UNDO")
SESSION = "RC4R_SESSION.dmx"
SPARE = "RC4R_SPARE.dmx"
POSITION, ANGLE = 0.01, 0.1                       # Astra's revised reproduction envelope (inclusive)
BAD_LOG = X.BAD_LOG + ("reproduction-mismatch", "PROD_POSE_BODY-P3-P6-failure", "already-unverified")
GATES = ("EVIDENCE", "APPLY", "POSTURE", "NOOP", "UNDO", "PEER")


class Report(X.Report):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.info = [], {}
        self.ids = A.opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap, self.side, self.off = {}, {}, {}
        for step in STEPS:
            obs = os.path.join(self.q, "observations")
            data = A.opt_json(os.path.join(obs, "S1F-%s.json" % step))
            if isinstance(data, dict) and isinstance(data.get("pid"), int):
                self.cap[step] = data
            for store, suffix in ((self.side, "leaves"), (self.off, "offsets")):
                x = A.opt_json(os.path.join(obs, "S1F-%s.%s.json" % (step, suffix)))
                if isinstance(x, dict):
                    store[step] = x


def library_and_restore(R):
    clean = A.opt_json(R.ev("library_cleanup.json")) or {}
    diffs = clean.get("differences_kept_in_evidence") or []
    poses = [x for x in diffs if "/Poses/" in x["path"]]
    allowed = lambda x: x["status"] == "added" and (  # noqa: E731
        re.match(r"^Characters/milestailsprower[^/]*/Poses/RC4 Sit[^/]*\.json$", x["path"]) or
        re.match(r"^Characters/milestailsprower[^/]*/(character\.json|pose_sources\.json|pose_rigs\.json)"
                 r"(\.bak)?$", x["path"]))
    unexpected = [x for x in diffs if not allowed(x)]
    R.check("EVIDENCE", "library.changed_only_by_rc4_sit", bool(clean) and not unexpected and len(poses) == 1,
            {"unexpected": unexpected, "poses": [p["path"] for p in poses]})
    R.check("EVIDENCE", "restore.library_exactly_as_before", clean.get("files_equal_pre") is True and
            clean.get("folders_equal_pre") is True)
    restore = A.opt_json(R.ev("restore.json")) or {}
    R.check("EVIDENCE", "restore.published_and_inventories_equal", restore.get("restored") is True,
            restore.get("inventory_problems"))


def tagged(lines, tag):
    return [A.log_json(l, tag) for l in lines if tag + " " in l]


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
        E("errors.%s" % step, not d.get("errors") and all(r in (d.get("sets") or {}) for r in X.ROLES), d.get("errors"))
        E("sidecars.%s" % step, X.sidecar_ok(R, R.side, X.LEAVES_FORMAT, step) and X.sidecar_ok(
            R, R.off, X.OFFSETS_FORMAT, step))
    session, spare = os.path.join(R.q, "sessions", SESSION), os.path.join(R.q, "sessions", SPARE)
    E("sessions.session_copy_never_saved", os.path.isfile(session) and A.sha(session) == c["pins"]["r2_fixture_sha256"])
    E("sessions.spare_never_saved", os.path.isfile(spare) and A.sha(spare) == c["pins"]["destination_sha256"])
    library_and_restore(R)
    lines = A.logs(R)
    E("log.collected", bool(lines))
    bad = [l for l in lines if any(b in l for b in BAD_LOG)]
    E("log.no_unverified_uncertain_mismatch_failed_abort_or_lockout_result", not bad, bad[:4])
    if any(s not in cap for s in STEPS):
        return
    E("process.one_sfm_process", len(set(cap[s]["pid"] for s in STEPS)) == 1)
    docs = set(u"%s" % ((cap[s].get("session") or {}).get("document") or u"") for s in STEPS)
    E("process.every_capture_on_the_disposable_session", len(docs) == 1 and list(docs)[0].lower().replace(
        "\\", "/").endswith(SESSION.lower()), sorted(docs))
    heads = [(cap[s].get("session") or {}).get("head_seconds") for s in STEPS]
    shots = set(u"%s" % (cap[s].get("session") or {}).get("shot") for s in STEPS)
    modes = set(u"%s" % (cap[s].get("session") or {}).get("timeline_mode") for s in STEPS)
    E("session.same_shot_and_playhead_motion_editor", len(shots) == 1 and all(h == heads[0] for h in heads) and
      modes == set([u"2"]), (sorted(shots), heads, sorted(modes)))
    names = [cap[s].get("names") for s in STEPS]
    tails_n = (names[0] or {}).get("target")
    E("roles.source_original_target_tails_n_peer_fox", tails_n not in (None, X.ORIGINAL, X.PEER) and all(
        n == {"source": X.ORIGINAL, "target": tails_n, "peer": X.PEER} for n in names), names)
    rigs = (A.adm(cap["PREP"], "target"), A.adm(cap["PREP"], "source"))
    R.info["rigs"] = [(a.get("rig_name"), a.get("handles"), a.get("constraints")) for a in rigs]
    E("prep.tails_n_chest_rig_and_original_direct_spine_rig", rigs[0].get("handles") == 23 and
      (rigs[0].get("bone_classes") or {}).get(X.SPINE) == u"constrained" and rigs[1].get("handles") == 22 and
      (rigs[1].get("bone_classes") or {}).get(X.SPINE) == u"fk", R.info["rigs"])
    recs = X.saved_records(R)
    sit = recs.get(X.SIT) or {}
    region = (((sit.get("pose") or {}).get("regions") or {}).get("full_body")) or {}
    E("save.rc4_sit_is_the_original_s_structural_record", (sit.get("pose") or {}).get("adapter") == X.RULE and sorted(
        list(region.get("positions") or {}) + list(region.get("orientations") or {})) == sorted(
        rigs[1].get("written") or []))

    # APPLY
    Ap = lambda cid, ok, d=None: R.check("APPLY", cid, ok, d)  # noqa: E731
    adapted = tagged(lines, "PROD_POSE_BODY-RIG-adapted")
    Ap("apply.chest_adapted", any(((x or {}).get("converted") or [{}])[0] == {"bone": X.SPINE,
                                                                             "destination": "constrained"}
                                  for x in adapted), adapted[:2])
    verified = tagged(lines, "PROD_POSE_BODY-P7-verified")
    rep = [(x or {}).get("reproduction") or {} for x in verified]
    R.info["cpm_reproduction"] = rep
    Ap("apply.p7_verified_once_under_the_revised_envelope", len(verified) == 1 and rep[0].get("limits") == {
        "position": POSITION, "angle_degrees": ANGLE} and rep[0].get("outputs", 0) > 100 and
       rep[0].get("max_distance", 1) <= POSITION and rep[0].get("max_angle_deg", 1) <= ANGLE, rep)
    base, app = cap["B_BASE"], cap["B_APPLY"]
    label = u"Apply Pose %s" % X.SIT
    au = A.undo(app)
    Ap("apply.one_owned_history_entry", u"%s" % au.get("undo_desc") == label, au)
    roles = A.adm(base, "target").get("roles") or {}
    t_chan = A.adm(base, "target").get("t_chan")
    written = A.adm(base, "target").get("written") or []
    moved = A.changed(A.field(base, "target", "sha256"), A.field(app, "target", "sha256"))
    Ap("apply.only_drafted_written_channels_changed", moved and set(moved) <= set(written) and u"handle-written" in
       set(roles.get(n) for n in moved), [n for n in moved if n not in written][:8])
    kb, ka = A.field(base, "target", "keys"), A.field(app, "target", "keys")
    bad_keys, neighbours = [], 0
    for n in moved:
        before = [k for layer in kb.get(n) or [] for k in layer]
        after = [k for layer in ka.get(n) or [] for k in layer]
        neighbours += len([k for k in before if k[0] != t_chan])
        if [k for k in before if k[0] != t_chan] != [k for k in after if k[0] != t_chan] or \
                len([k for k in after if k[0] == t_chan]) != 1:
            bad_keys.append(n)
    R.info["neighbour_keys_kept"] = neighbours
    Ap("apply.neighbouring_keys_unchanged_one_key_at_the_mapped_tick", t_chan is not None and not bad_keys,
       bad_keys[:8])
    tleaf = X.leaf_channels(base, "target")
    Ap("apply.simulated_leaves_not_authored", tleaf and not set(tleaf) & (set(moved) | set(written)))

    # POSTURE (independent: the destination's evaluated bones against the source's at SAVED)
    Q = lambda cid, ok, d=None: R.check("POSTURE", cid, ok, d)  # noqa: E731
    skip = set(X.leaves(base, "target")) | set(X.leaves(cap["SAVED"], "source"))
    src, dst = A.posture(cap["SAVED"], "source"), A.posture(app, "target")
    common = sorted((set(src) & set(dst)) - skip)
    dp, dq = A.max_difference(src, dst, common)
    worst = sorted(((A.angle(src[n][1], dst[n][1]), n) for n in common), reverse=True)[:3]
    R.info["posture"] = {"position": dp, "angle_degrees": dq, "bones": len(common), "worst": worst}
    Q("posture.tails_n_takes_the_saved_sitting_posture_within_the_revised_envelope", len(common) > 100 and
      dp <= POSITION and dq <= ANGLE, R.info["posture"])
    hb = (A.sets(base, "target").get("handles") or {}).get(X.PLACEMENT)
    ha = (A.sets(app, "target").get("handles") or {}).get(X.PLACEMENT)
    mb, ma = A.sets(base, "target").get("model_state"), A.sets(app, "target").get("model_state")
    Q("posture.placement_and_facing_unchanged", hb and ha and mb and ma and A.dist(hb[2], ha[2]) <= A.SAME_POSITION
      and A.angle(hb[3], ha[3]) <= A.SAME_ANGLE and A.dist(mb[2], ma[2]) <= A.SAME_POSITION and
      A.angle(mb[3], ma[3]) <= A.SAME_ANGLE, (hb, ha))
    classes = A.adm(base, "target").get("bone_classes") or {}
    bb, ba = A.sets(base, "target").get("bones") or {}, A.sets(app, "target").get("bones") or {}
    fk = [n for n in common if classes.get(n) == "fk"]
    Q("posture.direct_bone_offsets_kept", fk and not [n for n in fk if A.dist(bb[n][0], ba[n][0]) > A.SAME_POSITION])

    # NOOP
    N = lambda cid, ok, d=None: R.check("NOOP", cid, ok, d)  # noqa: E731
    p1 = tagged(lines, "PROD_POSE_BODY-P1")
    nowork = tagged(lines, "PROD_POSE_BODY-nowork")
    p6 = tagged(lines, "PROD_POSE_BODY-P6")
    R.info["p1"] = [(x or {}).get("actions") for x in p1]
    N("noop.second_apply_planned_no_write", len(p1) == 2 and ((p1[1] or {}).get("actions") or {}).get("insert") == 0
      and ((p1[1] or {}).get("actions") or {}).get("update") == 0, R.info["p1"])
    N("noop.cpm_no_work_result_is_no_op", len(nowork) == 1 and (nowork[0] or {}).get("result") == u"no-op", nowork)
    N("noop.no_undo_opened", len(p6) == 1)
    N("noop.authored_state_and_history_unchanged", A.field(cap["B_NOOP"], "target", "sha256") == A.field(
        app, "target", "sha256") and A.undo(cap["B_NOOP"]) == au, A.undo(cap["B_NOOP"]))

    # UNDO
    Un = lambda cid, ok, d=None: R.check("UNDO", cid, ok, d)  # noqa: E731
    un = cap["B_UNDO"]
    Un("undo.restores_base_exactly", A.field(un, "target", "sha256") == A.field(base, "target", "sha256") and
       A.bones_same(X.bones_without(un, "target", skip), X.bones_without(base, "target", skip)),
       A.changed(A.field(base, "target", "sha256"), A.field(un, "target", "sha256"))[:6])
    Un("undo.history", A.undo(un).get("undo_desc") == A.undo(base).get("undo_desc") and
       u"%s" % A.undo(un).get("redo_desc") == u"Redo %s" % label, A.undo(un))

    # PEER
    P = lambda cid, ok, d=None: R.check("PEER", cid, ok, d)  # noqa: E731
    prep = cap["PREP"]
    P("fox.unchanged_at_every_capture", all(A.field(cap[s], "peer", "sha256") == A.field(prep, "peer", "sha256")
                                            for s in STEPS))
    skip_o = set(X.leaves(prep, "source"))
    P("original_tails_unchanged_at_every_capture", all(
        A.field(cap[s], "source", "sha256") == A.field(prep, "source", "sha256") and A.bones_same(
            X.bones_without(cap[s], "source", skip_o), X.bones_without(prep, "source", skip_o)) for s in STEPS))


def verdict(checks):
    def gate(name):
        mine = [x["pass"] for x in checks if x["gate"] == name]
        return all(mine) if mine else None
    gates = dict((n, gate(n)) for n in GATES)
    if gates["EVIDENCE"] is not True:
        v = "INCOMPLETE"
    elif all(g is True for g in gates.values()):
        v = "AUTOMATED PASS"
    elif any(g is None for g in gates.values()):
        v = "INCOMPLETE"
    else:
        v = "FAIL"
    return v, gates


def run(c):
    R = Report(c)
    evaluate(R)
    v, gates = verdict(R.checks)
    out = {"format": "F01-RC4R-verdict-v1", "verdict": v, "gates": gates, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in R.checks if not x["pass"]], "info": R.info,
           "analyzer_sha256": A.sha(os.path.abspath(__file__))}
    lines = ["# F-01 RC4 short native check of the revised verification contract: %s" % v, "",
             "Qualification CPM `%s` (candidate `%s`). Gates: %s." % (
                 R.ids.get("qualification_cpm_sha256"), R.ids.get("candidate_cpm_sha256"),
                 ", ".join("%s %s" % (k, A.gate_text(g)) for k, g in sorted(gates.items()))), "",
             "| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in R.checks:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False, default=repr)[:300].replace("|", "\\|")
        lines.append("| %s | `%s` | %s | %s |" % (x["gate"], x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    lines += ["", "Info: `%s`" % json.dumps(R.info, ensure_ascii=False, default=repr)[:2000]]
    md = "\n".join(lines) + "\n"
    for name, data in (("RC4R_VERDICT.json", json.dumps(out, indent=1, sort_keys=True, default=repr)),
                       ("RC4R_VERDICT.md", md)):
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
    import rc4r_tool
    return run(rc4r_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
