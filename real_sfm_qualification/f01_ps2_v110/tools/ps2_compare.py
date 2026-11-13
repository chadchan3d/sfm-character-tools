# -*- coding: utf-8 -*-
"""F-01 PS-2 comparator: turns each Expected result of PROCEDURE.md into a machine check over the run's evidence
(Python 3; read-only except its two verdict files).

Inputs (all under Q): package/PACKAGE_MANIFEST.json; pre_run/pre.json and install_journal.json; evidence/seed.json,
library_K.json, library_V100.json, rollback.json, cleanup.json, library_after/ (the run's records), logs/ (CPM logs);
observations/S-*.json (F01_PS2_State.py captures); evidence/OPERATOR_REPORT.json (the Owner's reported observations,
transcribed verbatim). Writes evidence/PS2_VERDICT.json and PS2_VERDICT.md.

Verdict: PASS when every check passes; FAIL otherwise. A model-compatibility refusal of the unqualified stock model
(Soldier) that writes nothing is a FINDING (the check is reported, not passed), never a PASS.
"""
from __future__ import print_function

import glob
import json
import os
import re

STATE_STEPS = ("S-PROD", "S-E-INFO", "S-E-APPLY", "S-E-UNDO", "S-E-REDO", "S-SOLDIER-SAVED", "S-SOLDIER-APPLY",
               "S-SOLDIER-UNDO", "S-HEAVY", "S-K-GRIP", "S-K-GRIP-APPLY", "S-K-UNDO", "S-K-REDO", "S-K-LEGACY",
               "S-K-PRESETS", "S-K-DUP-BEFORE", "S-K-DUP-SAVED", "S-K-DUP-APPLY", "S-K-DUP-UNDO", "S-V100")
UI_OBSERVATIONS = ("save_dialog", "picker_groups", "list_size", "scrolling", "select_deselect", "scope_summary",
                   "pose_info", "apply_workflow")
UI_VERDICTS = ("ACCEPTED", "ACCEPTED WITH NOTES", "NOT ACCEPTED")
RESPONSIVE_MS, LIMIT_MS = 5000, 30000
BAD_LOG = ("recovery-unverified", "committed-unverified", "abort-failed", "undo-uncertain", "ownership-uncertain",
           "Traceback (most recent call last)")
TS = re.compile(r"^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)\.(\d{3})Z")


def read_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def opt_json(path):
    return read_json(path) if os.path.isfile(path) else None


def ms(line):
    m = TS.match(line)
    if not m:
        return None
    y, mo, d, h, mi, s, f = (int(x) for x in m.groups())
    return ((((d * 24 + h) * 60 + mi) * 60 + s) * 1000) + f


def parse_log(path):
    """One CPM log segment: header identity, operations (id, kind, animation set, outcome, duration) and events."""
    with open(path, "rb") as f:
        lines = f.read().decode("utf-8", "replace").splitlines()
    head = lines[0] if lines else ""
    build = re.search(r"build_sha256=([0-9a-f]{64})", head)
    pid = re.search(r"pid=(\d+)", head)
    ops, events = {}, []
    for line in lines[1:]:
        m = re.search(r"PROD_OPERATION_BEGIN id=(\d+) kind=u'([^']*)'", line)
        if m:
            animset = re.search(r"'animset_id': \(u'DmeAnimationSet', u'([^']*)'", line)
            ops[m.group(1)] = {"kind": m.group(2), "animset": animset.group(1) if animset else None,
                               "begin_ms": ms(line), "outcome": None, "end_ms": None, "events": []}
            continue
        m = re.search(r"PROD_OPERATION_RESULT id=(\d+) kind=u'[^']*' outcome=u'([^']*)'", line)
        if m and m.group(1) in ops:
            ops[m.group(1)].update(outcome=m.group(2), end_ms=ms(line))
            continue
        m = re.search(r" op=(\d+) \| PROD_POSE_(SCOPE-[A-Za-z0-9-]+)", line)
        if m and m.group(1) in ops:
            ops[m.group(1)]["events"].append(m.group(2))
        events.append(line)
    return {"file": os.path.basename(path), "build": build.group(1) if build else None,
            "pid": int(pid.group(1)) if pid else None, "ops": [dict(v, id=k) for k, v in sorted(
                ops.items(), key=lambda kv: int(kv[0]))], "bad": sorted(set(
                    b for b in BAD_LOG for line in events if b in line))}


def processes(q):
    """CPM processes in log order: {pid, build, ops, bad}; segments of one process are joined."""
    out = []
    for path in sorted(glob.glob(os.path.join(q, "evidence", "logs", "*.log"))):
        seg = parse_log(path)
        if out and out[-1]["pid"] == seg["pid"]:
            out[-1]["ops"] += seg["ops"]
            out[-1]["bad"] = sorted(set(out[-1]["bad"]) | set(seg["bad"]))
        else:
            out.append(seg)
    return out


def records(q):
    """Every pose record the run left (evidence/library_after): [{path, version, scope, posed, model, name}]."""
    out = []
    for path in glob.glob(os.path.join(q, "evidence", "library_after", "Characters", "*", "Poses", "*.json")):
        try:
            r = read_json(path)
            pose = r.get("pose") or {}
            scope = pose.get("scope") or {}
            out.append({"path": os.path.relpath(path, q).replace("\\", "/"), "name": r.get("name"),
                        "version": pose.get("version"), "scope": scope.get("kind"),
                        "posed": len(scope.get("posed") or []), "regions": sorted(pose.get("regions") or {}),
                        "model": (pose.get("source") or {}).get("model_ref") or r.get("model_ref"),
                        "engine": pose.get("engine")})
        except Exception as exc:
            out.append({"path": path, "error": repr(exc)})
    return out


class Run(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.findings = [], []

    def chk(self, name, ok, detail=None):
        self.checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})

    def finding(self, name, detail):
        self.checks.append({"check": name, "result": "FINDING", "detail": detail})
        self.findings.append("%s: %s" % (name, detail))


def ops_of(proc, kind, animset_prefix=None, outcome=None):
    return [o for o in proc["ops"] if o["kind"] == kind and
            (animset_prefix is None or (o["animset"] or "").lower().startswith(animset_prefix)) and
            (outcome is None or o["outcome"] == outcome)]


def verified_apply(o):
    return o["outcome"] == "verified" and "SCOPE-P7-verified" in o["events"]


def compare(c):
    R = Run(c)
    q = R.q
    pins, names = c["pins"], c["smoke"]
    cand, v100 = pins["candidate_cpm_sha256"], pins["v100_cpm_sha256"]
    # --- package and installation -----------------------------------------------------------------------------
    m = opt_json(os.path.join(q, "package", "PACKAGE_MANIFEST.json")) or {}
    R.chk("package.is_the_pinned_candidate", m.get("candidate_cpm_sha256") == cand and
          m.get("candidate_inventory_sha256") == pins["candidate_inventory_sha256"] and
          m.get("v100_zip_sha256") == pins["v100_zip_sha256"] and m.get("spec_sha256") == pins["spec_sha256"],
          {k: m.get(k) for k in ("candidate_cpm_sha256", "candidate_inventory_sha256", "zip_sha256")})
    R.chk("package.unsigned_and_the_v100_signature_left_out", m.get("status", "").startswith("UNSIGNED") and
          m.get("removed") == ["usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.sig"])
    paths = [f["path"] for f in m.get("files") or []]
    R.chk("package.registries_beside_the_cpm_library", all(
        "usermod/scripts/SFM Character Tools/%s" % n in paths for n in ("cpm_pose_profiles_v1.json",
                                                                        "cpm_body_profiles_v1.json")))
    j = opt_json(os.path.join(q, "pre_run", "install_journal.json")) or {}
    R.chk("install.journal_complete", j.get("state") == "complete", j.get("state"))
    # --- processes ----------------------------------------------------------------------------------------------
    procs = processes(q)
    candidates = [p for p in procs if p["build"] == cand]
    olds = [p for p in procs if p["build"] == v100]
    R.chk("identity.three_candidate_processes_then_one_v100_process", len(candidates) == 3 and len(olds) == 1 and
          len(procs) == 4 and procs[-1]["build"] == v100, [(p["pid"], (p["build"] or "?")[:8]) for p in procs])
    if len(candidates) != 3 or len(olds) != 1:
        return R
    p1, p2, p3 = candidates
    p4 = olds[0]
    R.chk("safety.no_recovery_uncertainty_or_traceback_in_any_process", not any(p["bad"] for p in procs),
          [(p["pid"], p["bad"]) for p in procs if p["bad"]])
    applies = [o for p in candidates for o in p["ops"] if o["kind"] == "Apply Pose"]
    R.chk("safety.every_candidate_pose_apply_verified", applies and all(o["outcome"] == "verified" for o in applies),
          [(o["animset"], o["outcome"]) for o in applies])
    saves = [o for p in candidates for o in p["ops"] if o["kind"] == "Save Pose"]
    R.chk("safety.every_save_verified_or_cancelled", all(o["outcome"] in ("verified", "no-op") for o in saves),
          [(o["animset"], o["outcome"]) for o in saves])
    # --- production identity --------------------------------------------------------------------------------------
    st = dict((s, opt_json(os.path.join(q, "observations", "%s.json" % s))) for s in STATE_STEPS)
    missing = [s for s, v in st.items() if v is None]
    R.chk("observations.every_state_capture_present", not missing, missing)
    s = st["S-PROD"] or {}
    R.chk("production.build_mode_rules_and_switches", s.get("cpm_build_sha256") == cand and
          s.get("registry_mode") == "production" and
          s.get("scope_rules") == {"direct_fk_v1": {"revision": 1, "status": "qualified"}} and
          s.get("carried_enabled") == [False] and s.get("extrapolation_qualified") == [False] and
          s.get("qualification_fault") == [None] and not s.get("recovery_paused"),
          {k: s.get(k) for k in ("cpm_build_sha256", "registry_mode", "scope_rules", "qualification_fault")})
    R.chk("production.reports_version_1_1_0", s.get("release_version") == pins["software_version"],
          s.get("release_version"))
    reg = s.get("registry") or {}
    R.chk("production.registries_load_and_enable_only_the_qualified_left_arm",
          reg.get("registry_sha256") == pins["profile_sha256"] and reg.get("body_loaded") is True and
          reg.get("mappings") == [["left_arm", "qualified"]], reg)
    # --- Engineer generic Full body ---------------------------------------------------------------------------
    recs = records(q)
    eng = [r for r in recs if r.get("name") == names["engineer_pose"]]
    R.chk("engineer.save_new_full_body_v3_all_72_bones", len(eng) == 1 and eng[0]["version"] == 3 and
          eng[0]["scope"] == "full_body" and eng[0]["posed"] == 72 and
          (eng[0]["engine"] or {}).get("rule") == "direct_fk_v1" and
          ops_of(p1, "Save Pose", "engineer", "verified"), eng)
    info = (st["S-E-INFO"] or {}).get("pose_info") or {}
    rows = info.get("rows") or []
    R.chk("engineer.pose_info_wording", [u"Includes:", u"Full body, including hip movement", None] in rows and
          [u"Not included:", u"Facial expressions, rootTransform", None] in rows, rows)
    R.chk("engineer.restart_between_save_and_apply", p1["pid"] != p2["pid"], (p1["pid"], p2["pid"]))
    e_apply = ops_of(p2, "Apply Pose", "engineer")
    R.chk("engineer.apply_verified_in_a_new_process", len(e_apply) == 1 and verified_apply(e_apply[0]) and
          "SCOPE-P1" in e_apply[0]["events"], e_apply)

    def undo(step):
        return ((st[step] or {}).get("session") or {}).get("undo") or {}
    label = "Apply Pose " + names["engineer_pose"]
    R.chk("engineer.one_named_undo_entry_then_undo_and_redo", undo("S-E-APPLY").get("undo_desc") == label and
          undo("S-E-UNDO").get("redo_desc") == "Redo " + label and undo("S-E-REDO").get("undo_desc") == label,
          [undo(x) for x in ("S-E-APPLY", "S-E-UNDO", "S-E-REDO")])
    # --- unqualified header-clean stock model (Soldier) -----------------------------------------------------------
    sol = [r for r in recs if r.get("name") == names["soldier_pose"]]
    if not sol and not ops_of(p2, "Save Pose", "soldier", "verified"):
        R.finding("soldier.full_body_available_on_an_unqualified_compatible_model",
                  "no Soldier Full body pose was saved; see OPERATOR_REPORT for the dialog message")
    else:
        R.chk("soldier.save_new_full_body_v3", len(sol) == 1 and sol[0]["version"] == 3 and
              sol[0]["scope"] == "full_body" and "soldier" in (sol[0]["model"] or ""), sol)
        s_apply = ops_of(p2, "Apply Pose", "soldier")
        slabel = "Apply Pose " + names["soldier_pose"]
        R.chk("soldier.apply_verified_with_one_undo_entry", len(s_apply) == 1 and verified_apply(s_apply[0]) and
              undo("S-SOLDIER-APPLY").get("undo_desc") == slabel and
              undo("S-SOLDIER-UNDO").get("redo_desc") == "Redo " + slabel, s_apply)
    # --- Heavy unsupported Full body --------------------------------------------------------------------------
    heavy_recs = [r for r in recs if "heavy" in (r.get("model") or "")]
    R.chk("heavy.full_body_refused_nothing_saved", not heavy_recs and not ops_of(p2, "Save Pose", "heavy",
                                                                                  "verified") and
          ((st["S-HEAVY"] or {}).get("character") or {}).get("model", "").endswith("heavy.mdl"), heavy_recs)
    # --- Krystal: Selected parts, no v2 route, legacy v1, presets ----------------------------------------------
    k = [r for r in recs if r.get("name") == names["krystal_pose"]]
    R.chk("krystal.save_new_selected_parts_v3", len(k) == 1 and k[0]["version"] == 3 and
          k[0]["scope"] == "selected_parts" and ops_of(p3, "Save Pose", "krystal", "verified"), k)
    R.chk("krystal.no_version_2_full_body_saved_in_production", not [r for r in recs if r.get("version") == 2])
    k_apply = [o for o in ops_of(p3, "Apply Pose", "krystal")]
    klabel = "Apply Pose " + names["krystal_pose"]
    R.chk("krystal.selected_parts_apply_verified_undo_redo", len(k_apply) >= 2 and verified_apply(k_apply[0]) and
          undo("S-K-GRIP-APPLY").get("undo_desc") == klabel and undo("S-K-UNDO").get("redo_desc") == "Redo " + klabel
          and undo("S-K-REDO").get("undo_desc") == klabel, [(o["outcome"], o["events"][-1:]) for o in k_apply])
    leg = (st["S-K-LEGACY"] or {})
    R.chk("krystal.legacy_left_arm_v1_applies", (leg.get("selected_pose") or {}).get("version") == 1 and
          (leg.get("selected_pose") or {}).get("regions") == ["left_arm"] and len(k_apply) >= 2 and
          k_apply[-1]["outcome"] == "verified" and undo("S-K-LEGACY").get("undo_desc", "").startswith("Apply Pose"),
          leg.get("selected_pose"))
    R.chk("presets.body_preset_and_expression_apply_on_the_candidate",
          ops_of(p3, "Apply Body Preset", None, "verified") and ops_of(p3, "Apply Expression", None, "verified"),
          [(o["kind"], o["outcome"]) for o in p3["ops"] if o["kind"].startswith("Apply ") and "Pose" not in o["kind"]])
    R.chk("presets.help_reports_1_1_0", (st["S-K-PRESETS"] or {}).get("release_version") == pins["software_version"])
    duplicate_model_body_preset(R, c, st, p3)
    # --- rollback to v1.0.0 -----------------------------------------------------------------------------------
    rb = opt_json(os.path.join(q, "evidence", "rollback.json")) or {}
    R.chk("rollback.v100_restored_exactly_and_library_untouched", rb.get("rolled_back") is True and
          rb.get("library_untouched") is True and rb.get("installation") == "v1.0.0", rb.get("inventory_problems"))
    lk, lv = (opt_json(os.path.join(q, "evidence", "library_%s.json" % t)) for t in ("K", "V100"))

    def poses_rows(lib):
        return sorted((d["path"], d["sha256"]) for d in (lib or {}).get("differences") or []
                      if "/Poses/" in d["path"])
    R.chk("rollback.v100_leaves_the_poses_folders_unchanged", lk is not None and lv is not None and
          poses_rows(lk) and poses_rows(lk) == poses_rows(lv), (len(poses_rows(lk)), len(poses_rows(lv))))
    v = st["S-V100"] or {}
    R.chk("rollback.v100_runs_and_applies_presets_with_poses_folders_present", v.get("cpm_build_sha256") == v100 and
          ops_of(p4, "Apply Body Preset", None, "verified") and ops_of(p4, "Apply Expression", None, "verified"),
          [(o["kind"], o["outcome"]) for o in p4["ops"]])
    # --- restoration and sessions ---------------------------------------------------------------------------
    cl = opt_json(os.path.join(q, "evidence", "cleanup.json")) or {}
    R.chk("restore.v100_installed_library_and_every_inventory_equal_baselines", cl.get("restored") is True and
          cl.get("installation") == "v1.0.0", cl.get("inventory_problems"))
    sess = c["session_pins"]
    bad = [n for n, d in sess.items() if not os.path.isfile(os.path.join(q, "sessions", n)) or
           sha(os.path.join(q, "sessions", n)) != d]
    R.chk("sessions.copies_never_saved", not bad, bad)
    # --- the Owner's reported observations -------------------------------------------------------------------
    op = opt_json(os.path.join(q, "evidence", "OPERATOR_REPORT.json")) or {}
    expect = c["operator_expect"]
    for key, text in sorted(expect.items()):
        R.chk("operator.%s" % key, op.get(key) == text, op.get(key))
    R.chk("operator.clean_closes", op.get("clean_closes") == 4, op.get("clean_closes"))
    # --- performance ----------------------------------------------------------------------------------------
    timed = [(o["animset"], o["end_ms"] - o["begin_ms"]) for o in applies if o["end_ms"] and o["begin_ms"]]
    worst = max([t for _, t in timed] or [None]) if timed else None
    R.performance = {"applies_ms": timed, "worst_ms": worst,
                     "class": "unmeasured" if worst is None else "responsive" if worst <= RESPONSIVE_MS else
                     "finding" if worst <= LIMIT_MS else "too-slow"}
    R.chk("performance.within_the_limit", worst is not None and worst <= LIMIT_MS, R.performance)
    return R


def duplicate_model_body_preset(R, c, st, p3):
    """Two instances of the same model in one shot: a Body preset saved from the new instance (B) and applied to the
    original (A). Target identity from the CPM log; peer isolation and Undo from the state digests. A refusal that
    changes neither instance is a FINDING (safe); a change to the wrong instance, or any change after a refusal, FAILS."""
    d = c["duplicate"]

    def sets(step):
        rows = (st[step] or {}).get("animation_sets")
        return dict((r["name"], r) for r in rows) if isinstance(rows, list) else None
    before, saved, applied, undone = (sets(s) for s in ("S-K-DUP-BEFORE", "S-K-DUP-SAVED", "S-K-DUP-APPLY",
                                                         "S-K-DUP-UNDO"))
    if None in (before, saved, applied, undone):
        R.chk("duplicate.animation_set_state_readable", False, "a duplicate-check capture has no readable sets")
        return
    def norm(m):
        return (m or "").replace("\\", "/").lower()
    same = sorted(n for n, r in before.items() if norm(r.get("model")) == norm(d["model"]))
    a = d["original"]
    others = [n for n in same if n != a]
    R.chk("duplicate.two_instances_of_the_same_model", len(same) == 2 and a in same and len(others) == 1 and
          before[a]["handle"] != before[others[0]]["handle"], same)
    if not (len(same) == 2 and a in same and len(others) == 1):
        return
    b = others[0]

    def h(step_sets, name):
        r = step_sets.get(name) or {}
        return r.get("state_sha256")
    R.chk("duplicate.saving_from_b_leaves_a_unchanged", h(saved, a) == h(before, a), (h(before, a), h(saved, a)))
    save = [o for o in p3["ops"] if o["kind"] in ("Save Current Body", "Save New Body Preset")]
    apply_ = [o for o in p3["ops"] if o["kind"] == "Apply Body Preset"]
    saved_ok = bool(save) and save[-1]["outcome"] == "verified"
    if not saved_ok:
        if h(saved, b) is not None and h(saved, a) == h(before, a):
            R.finding("duplicate.body_preset_save_on_the_second_instance", "refused or not verified (%s); nothing "
                      "changed on the original" % (save[-1]["outcome"] if save else "no Save operation"))
        else:
            R.chk("duplicate.body_preset_save_on_the_second_instance", False, save[-1:] if save else None)
        return
    R.chk("duplicate.save_targets_the_selected_second_instance", save[-1]["animset"] == b, save[-1]["animset"])
    last = apply_[-1] if apply_ else None
    if last is None or last["outcome"] != "verified":
        unchanged = h(applied, a) == h(saved, a) and h(applied, b) == h(saved, b)
        if unchanged:
            R.finding("duplicate.body_preset_apply_onto_the_original", "refused safely (%s); neither instance changed"
                      % (last["outcome"] if last else "no Apply operation"))
        else:
            R.chk("duplicate.refusal_changes_nothing", False, {"a": [h(saved, a), h(applied, a)],
                                                                "b": [h(saved, b), h(applied, b)]})
        return
    R.chk("duplicate.apply_targets_the_selected_original", last["animset"] == a, last["animset"])
    R.chk("duplicate.apply_changes_the_original", h(applied, a) != h(saved, a))
    R.chk("duplicate.peer_isolation_second_instance_unchanged", h(applied, b) == h(saved, b),
          (h(saved, b), h(applied, b)))
    R.chk("duplicate.undo_restores_the_original_and_leaves_the_peer", h(undone, a) == h(saved, a) and
          h(undone, b) == h(saved, b), {"a": [h(saved, a), h(undone, a)], "b": [h(saved, b), h(undone, b)]})


def ui_acceptance(q):
    """The Owner's Selected parts UI acceptance, from OPERATOR_REPORT.json and the screenshots. Never inferred from
    automated tests: a missing or incomplete report is NOT ACCEPTED."""
    op = opt_json(os.path.join(q, "evidence", "OPERATOR_REPORT.json")) or {}
    ui = op.get("selected_parts_ui") or {}
    obs = ui.get("observations") or {}
    missing = [k for k in UI_OBSERVATIONS if not (isinstance(obs.get(k), str) and obs.get(k).strip())]
    shots = sorted(os.path.basename(p) for p in glob.glob(os.path.join(q, "screenshots", "SP-*.png")))
    verdict = ui.get("verdict")
    if verdict not in UI_VERDICTS or missing or len(shots) < 5:
        return {"acceptance": "NOT ACCEPTED", "reason": "incomplete Owner report", "missing": missing,
                "screenshots": shots, "verdict_reported": verdict}
    return {"acceptance": verdict, "observations": obs, "screenshots": shots, "notes": ui.get("notes")}


def sha(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(c):
    R = compare(c)
    q = c["paths"]["Q"]
    failed = [x["check"] for x in R.checks if x["result"] == "FAIL"]
    verdict = "FAIL" if failed else "PASS WITH FINDINGS" if R.findings else "PASS"
    perf = getattr(R, "performance", {"class": "unmeasured"})
    ui = ui_acceptance(q)
    out = {"format": "F01-PS2-verdict-v1", "verdict": verdict, "failed": failed, "findings": R.findings,
           "performance": perf, "selected_parts_ui": ui, "checks": R.checks}
    with open(os.path.join(q, "evidence", "PS2_VERDICT.json"), "wb") as f:
        f.write(json.dumps(out, indent=1, sort_keys=True).encode("utf-8"))
    lines = ["# F-01 PS-2 v1.1.0 production candidate smoke verdict: %s" % verdict, "",
             "Candidate CPM `%s`, package inventory `%s` (unsigned)." % (c["pins"]["candidate_cpm_sha256"],
                                                                        c["pins"]["candidate_inventory_sha256"]),
             "", "| Check | Result | Detail |", "|---|---|---|"]
    for x in R.checks:
        d = "" if x["result"] == "PASS" else json.dumps(x["detail"], sort_keys=True, default=str)[:300]
        lines.append("| `%s` | %s | %s |" % (x["check"], x["result"], d.replace("|", "\\|")))
    lines += ["", "Performance: **%s** (worst %s ms)." % (perf.get("class"), perf.get("worst_ms")), "",
              "Findings: %s" % ("; ".join(R.findings) or "none"), "",
              "Selected parts UI (Owner acceptance, separate from the functional verdict; never inferred from tests): "
              "**%s**%s" % (ui["acceptance"], (" (%s)" % ui.get("reason")) if ui.get("reason") else "")]
    with open(os.path.join(q, "evidence", "PS2_VERDICT.md"), "wb") as f:
        f.write(("\n".join(lines) + "\n").encode("utf-8"))
    print("\n".join(lines))
    return out
