# -*- coding: utf-8 -*-
"""F-01 K2: the offline comparator for the short Krystal version 2 Full body native integration check (R4 section 5).
Python 3, run with -I after restore (SFM closed). Read-only except for its two verdict files. It reuses the S3
comparator's independent v2 checks (f01_full_body_s3/tools/s3_compare.py: the record oracle, the written channels,
posture relative to the placement handle, model state, scales, preserved bones, other channels, controls, unrelated
animation, Undo/Redo, the CPM log) on this run's eight observations:

  A1  source K2_SOURCE.dmx, shot15 0.2083 s: baseline          A2  after Save New (Full body, version 2 route)
  B1  destination K2_DESTINATION.dmx, shot13 0.3750 s (a new SFM process): baseline
  B2  after Apply K2 Pose      B3  after Undo      B4  after Redo
  B5  after the Owner's Hip rotation      B6  after Update Pose K2 Pose

usage: python -I k2_compare.py K2.json      (or: k2_tool.py K2.json compare)
       python -I k2_compare.py K2.json --replay-revised-a1
Writes Q/evidence/K2_VERDICT.json and K2_VERDICT.md (exclusive create). Exit 0 only on "verdict": "PASS".
--replay-revised-a1 re-evaluates an existing run's evidence and writes K2_VERDICT_REVISED_A1.json/.md instead
(exclusive create), linked to the original verdict, which must exist and is never changed.

Revised A1 (F01_FULL_BODY_S1_CHECKPOINT.md section 10; K2 correction 2026-11-14): Apply's planned value of every
FK-position channel (the record descriptor's role "fk-written", attribute "position") is the destination's own value,
read here from the B1 baseline observation; it must be within the profile's saved/destination limit (body_krystal_v1:
0.00005 SFM units, Euclidean, compared as float32; every other profile exact) and is kept exactly. Every other written
channel holds the record's saved value. The original K2 comparator compared every written channel with the saved
value; that check (apply.written_channels_hold_the_record) is replaced by
apply.written_channels_hold_the_planned_values and apply.pinned_fk_positions_within_the_revised_A1_limit.
"""
from __future__ import print_function

import hashlib
import json
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "f01_full_body_s3", "tools"))
import s3_compare as S3  # noqa: E402

POSE = u"K2 Pose"
STEPS = ("A1", "A2", "B1", "B2", "B3", "B4", "B5", "B6")
LABELS = dict((s, S3.LABELS[s]) for s in STEPS)     # the S3 observer's fixed labels for these steps
BAD_LOG = ("RECOVERY_BLOCKED", "undo-uncertain", "abort-unverified", "P7-unverified", "committed-unverified",
           "recovery-unverified", "abort-failed")
# Revised A1 (S1 checkpoint section 10): the largest compatible saved/destination FK-position distance per profile.
FK_POSITION_LIMIT = {u"body_krystal_v1": 0.00005}
REVISED_NAMES = ("K2_VERDICT_REVISED_A1.json", "K2_VERDICT_REVISED_A1.md")


def f32(x):
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]


def pinned_fk_positions(region):
    """The FK-position channels of a v2 record, from its own descriptor's channel classification."""
    roles = (region.get("descriptor") or {}).get("channels") or {}
    return sorted(n for n in region["positions"]
                  if (roles.get(n) or {}).get("role") == "fk-written" and roles[n].get("attribute") == "position")


def planned_region(R, region, base):
    """(region with every FK position replaced by the destination baseline value, problems, differing detail).
    The destination value is B1's observed value at the mapped tick, never CPM's report."""
    problems, differing = [], {}
    limit = f32(FK_POSITION_LIMIT.get(region.get("profile_id"), 0.0))
    was = R.channels(base)
    planned = dict(region, positions=dict(region["positions"]))
    pinned = pinned_fk_positions(region)
    for n in pinned:
        saved = region["positions"][n]
        dest = (was.get(n) or {}).get("value_at_mapped")
        if not (isinstance(dest, list) and len(dest) == 3 and isinstance(saved, list) and len(saved) == 3 and
                all(isinstance(v, (int, float)) and math.isfinite(v) and f32(v) == v for v in dest + saved)):
            problems.append("%s destination or saved value unreadable" % n)
            continue
        distance = math.sqrt(sum((float(saved[i]) - float(dest[i])) ** 2 for i in range(3)))
        if f32(distance) > limit:
            problems.append("%s distance %.9g exceeds the limit %.9g" % (n, distance, limit))
        planned["positions"][n] = list(dest)
        if list(dest) != list(saved):
            differing[n] = {"saved": saved, "destination": dest, "distance": distance}
    return planned, pinned, problems, differing


def planned_written_problems(R, after, base, region):
    """Revised A1 written-channel check: the S3 written-channel rules (value at the mapped tick, one key there, other
    keys and layers unchanged) against the planned values, plus each FK position kept exactly."""
    planned, pinned, _, _ = planned_region(R, region, base)
    out = R.written_problems(after, base, planned, False)
    now = R.channels(after)
    for n in pinned:
        if (now.get(n) or {}).get("value_at_mapped") != planned["positions"][n]:
            out.append("%s FK position not kept exactly" % n)
    return out


def operations(rows, pid, kind):
    """(outcome, lines) for every operation of `kind` in one SFM process, in order."""
    ops, current = [], None
    for r in rows:
        if r["pid"] != pid:
            continue
        m = re.match(r"PROD_OPERATION_BEGIN id=(\d+) kind=u?'([^']*)'", r["text"])
        if m:
            current = {"id": m.group(1), "lines": [], "outcome": None} if m.group(2) == kind else None
            if current is not None:
                ops.append(current)
            continue
        m = re.match(r"PROD_OPERATION_RESULT id=(\d+) kind=u?'([^']*)' outcome=u?'([^']*)'", r["text"])
        if m and current is not None and m.group(1) == current["id"]:
            current["outcome"] = m.group(3)
        if current is not None:
            current["lines"].append(r["text"])
    return ops


def evaluate(R):
    o, chk = R.obs, R.check
    want = R.ids["qualification_cpm_sha256"]
    chk("identity.k1_qualification_build", want == R.c["pins"]["qualification_cpm_sha256"], want)
    for step in STEPS:
        if not chk("observed.%s" % step, step in o and step in R.side, LABELS[step]):
            continue
        problems = S3.s0_analyze.validate(o[step]) + list(o[step].get("problems") or []) + \
            list(R.side[step]["mismatch"])
        chk("valid.%s" % step, not problems and o[step]["readonly"]["unchanged"], problems[:5])
        chk("cpm.%s" % step, (o[step].get("cpm_loaded") or {}).get("build_sha256") == want, o[step].get("cpm_loaded"))
    if any(s not in o for s in STEPS):
        chk("complete", False, "missing observations: %s" % sorted(set(STEPS) - set(o)))
        return
    A, B = ("A1", "A2"), ("B1", "B2", "B3", "B4", "B5", "B6")
    pa, pb = set(o[s]["pid"] for s in A), set(o[s]["pid"] for s in B)
    chk("process.restart_between_save_and_apply", len(pa) == 1 and len(pb) == 1 and pa != pb,
        (sorted(pa), sorted(pb)))
    chk("process.sessions", all(o[s]["document"].lower().endswith("k2_source.dmx") for s in A) and
        all(o[s]["document"].lower().endswith("k2_destination.dmx") for s in B),
        (o["A1"]["document"], o["B1"]["document"]))

    # Save (version 2 through the current dialog) and the record
    folder = os.path.join(R.q, "evidence", "library_poses", R.c["character_dir"])
    names = sorted(os.listdir(folder)) if os.path.isdir(folder) else []
    current = [n for n in names if n.startswith(POSE + u"--") and n.endswith(".json")]
    baks = [n for n in names if n.startswith(POSE + u"--") and n.endswith(".json.bak")]
    chk("library.one_record_and_its_update_backup", len(current) == 1 and len(baks) == 1 and
        set(names) == set(current + baks), names)
    if len(current) != 1 or len(baks) != 1:
        return
    rec = S3.read_json(os.path.join(folder, current[0]))
    saved = S3.read_json(os.path.join(folder, baks[0]))
    reg_saved = saved["pose"].get("regions", {}).get("full_body")
    reg_now = rec["pose"].get("regions", {}).get("full_body")
    chk("save.version_2_full_body_record", saved["pose"].get("version") == 2 and reg_saved is not None and
        rec["pose"].get("version") == 2 and reg_now is not None and saved.get("name") == POSE)
    if reg_saved is None or reg_now is None:
        return
    written = set(reg_saved["positions"]) | set(reg_saved["orientations"])
    chk("save.written_set_is_the_v2_mapping", len(written) == 278 and
        written == set(reg_now["positions"]) | set(reg_now["orientations"]), len(written))
    chk("save.captures_the_visible_posture", not R.oracle_problems(o["A2"], reg_saved),
        R.oracle_problems(o["A2"], reg_saved)[:8])
    chk("save.writes_nothing_to_the_scene", R.doc_unchanged(o["A1"], o["A2"]))
    lib_a = os.path.join(R.q, "evidence", "library_A.json")
    lib_a = S3.read_json(lib_a) if os.path.isfile(lib_a) else {}
    chk("reopen.record_saved_in_process_A_is_the_one_applied", list((lib_a.get("files") or {}).keys()) == current and
        (lib_a.get("files") or {}).get(current[0]) == S3.s0_hash(os.path.join(folder, baks[0])),
        lib_a.get("files"))

    # Reopen in a new SFM process: the Poses page enables Apply for the version 2 record; the pre-Apply check
    smoke_path = os.path.join(R.q, "observations", "UI-SMOKE.json")
    smoke = S3.read_json(smoke_path) if os.path.isfile(smoke_path) else {}
    chk("reopen.apply_enabled_for_the_v2_record", smoke.get("apply_button_enabled") is True and
        (smoke.get("selected") or {}).get("name") == POSE and (smoke.get("selected") or {}).get("version") == 2 and
        (smoke.get("selected") or {}).get("regions") == ["full_body"] and not smoke.get("recovery_paused") and
        smoke.get("cpm_build_sha256") == want and smoke.get("pid") == o["B1"]["pid"],
        dict((k, smoke.get(k)) for k in ("apply_button_enabled", "selected", "pid")))
    pre_path = os.path.join(R.q, "evidence", "K2_PRECHECK.json")
    pre = S3.read_json(pre_path) if os.path.isfile(pre_path) else {}
    chk("precheck.compatible_and_distinct_before_apply", pre.get("apply_allowed") is True, pre)
    d = R.distinct_groups(reg_saved, o["B1"])
    visible = [g for g in S3.REQUIRED_GROUPS if d.get(g, 0.0) >= S3.VISIBLE_DEGREES]
    chk("distinct.destination_visibly_different", len(visible) >= 2,
        dict((g, round(d.get(g, 0.0), 2)) for g in S3.REQUIRED_GROUPS))

    # Apply (B2), Undo (B3), Redo (B4): placement, posture, preservation
    b1 = o["B1"]
    wp = planned_written_problems(R, o["B2"], b1, reg_saved)
    chk("apply.written_channels_hold_the_planned_values", not wp, wp[:8])
    _, pinned, pin_problems, differing = planned_region(R, reg_saved, b1)
    chk("apply.pinned_fk_positions_within_the_revised_A1_limit", pinned and not pin_problems,
        {"pinned": len(pinned), "problems": pin_problems[:8], "differing_from_saved": differing})
    chk("apply.whole_body_posture_reproduced_with_placement_model_and_scales_unchanged",
        not R.applied_problems(o["B2"], b1, reg_saved), R.applied_problems(o["B2"], b1, reg_saved)[:8])
    chk("apply.other_channels_of_the_instance_unchanged", not R.channel_problems(b1, o["B2"], exclude=written),
        R.channel_problems(b1, o["B2"], exclude=written)[:8])
    chk("apply.facial_gaze_and_other_controls_unchanged", not R.control_problems(b1, o["B2"], written),
        R.control_problems(b1, o["B2"], written)[:8])
    chk("apply.unrelated_animation_unchanged", R.outside_equal("B1", "B2"))
    chk("apply.one_owned_undo_entry", o["B2"]["session_after"]["undo"]["undo_desc"] == u"Apply Pose " + POSE and
        o["B2"]["session_after"]["undo"]["can_undo"] is True, o["B2"]["session_after"]["undo"])
    chk("undo.restores_the_destination", not R.channel_problems(b1, o["B3"]) and
        not R.skeleton_problems(b1, o["B3"]) and R.outside_equal("B1", "B3") and
        o["B3"]["session_after"]["undo"].get("redo_desc") == u"Redo Apply Pose " + POSE,
        (R.channel_problems(b1, o["B3"])[:5], o["B3"]["session_after"]["undo"]))
    chk("redo.restores_the_applied_pose", not R.channel_problems(o["B2"], o["B4"]) and
        not R.skeleton_problems(o["B2"], o["B4"]) and
        o["B4"]["session_after"]["undo"]["undo_desc"] == u"Apply Pose " + POSE, R.channel_problems(o["B2"], o["B4"])[:5])

    # Update (B5 -> B6): in place, the new posture, nothing written to the scene
    chk("update.writes_nothing_to_the_scene", R.doc_unchanged(o["B5"], o["B6"]))
    chk("update.record_holds_the_updated_posture", not R.oracle_problems(o["B6"], reg_now),
        R.oracle_problems(o["B6"], reg_now)[:8])
    chk("update.record_changed_from_the_saved_posture", len(R.oracle_problems(o["A2"], reg_now)) > 0)
    chk("update.in_place", rec.get("preset_id") == saved.get("preset_id") and
        rec.get("created_at") == saved.get("created_at") and rec.get("updated_at") != rec.get("created_at"),
        (rec.get("created_at"), rec.get("updated_at")))

    # The CPM log: CPM's own verdicts; recovery; timing
    logs = S3.parse_logs(os.path.join(R.q, "evidence", "logs"))
    a_pid, b_pid = list(pa)[0], list(pb)[0]
    saves = operations(logs, a_pid, "Save Pose")
    chk("log.save_verified", len(saves) == 1 and saves[0]["outcome"] == "verified",
        [s["outcome"] for s in saves])
    fallback = [r for r in logs if "K1-generic-inventory-unavailable" in r["text"]]
    R.findings = ["K1 fallback used: the generic inventory could not be built (Selected parts unavailable): %s"
                  % fallback[0]["text"][:200]] if fallback else []
    infos = operations(logs, b_pid, "Pose Info")
    chk("log.pose_info_opened_in_the_new_process", any(i["outcome"] == "completed" for i in infos),
        [i["outcome"] for i in infos])
    ops = S3.apply_operations(logs, b_pid)
    chk("log.one_apply_owned_and_verified_by_cpm", len(ops) == 1 and S3.has(ops[0], "PROD_POSE_BODY-P6 ") and
        S3.has(ops[0], "PROD_POSE_BODY-P7-verified") and '"owned": true' in " ".join(ops[0]["text"]),
        [op["id"] for op in ops])
    updates = operations(logs, b_pid, "Update Pose")
    chk("log.update_verified", len(updates) == 1 and updates[0]["outcome"] == "verified",
        [u["outcome"] for u in updates])
    chk("log.no_recovery_or_uncertainty", not any(b in r["text"] for r in logs for b in BAD_LOG),
        sorted(set(b for r in logs for b in BAD_LOG if b in r["text"])))
    R.timing = [dict(S3.timing(op), step="B2", id=op["id"]) for op in ops]

    # Restoration and the sessions (never saved)
    restore = os.path.join(R.q, "evidence", "restore.json")
    chk("restore.published_and_inventories_equal", os.path.isfile(restore) and
        S3.read_json(restore).get("restored") is True)
    dest = os.path.join(R.q, "evidence", "destination.json")
    chk("sessions.never_saved", os.path.isfile(dest) and
        S3.s0_hash(os.path.join(R.q, "sessions", "K2_DESTINATION.dmx")) == S3.read_json(dest)["destination_sha256"]
        and S3.s0_hash(os.path.join(R.q, "sessions", "K2_SOURCE.dmx")) == R.c["pins"]["r2_fixture_sha256"])


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(c, replay=False):
    S3.LABELS = LABELS                                    # Run loads exactly these eight observations
    R = S3.Run(c)
    ev = os.path.join(R.q, "evidence")
    original = None
    if replay:
        paths = [os.path.join(ev, n) for n in ("K2_VERDICT.json", "K2_VERDICT.md")]
        if not all(os.path.isfile(p) for p in paths):
            print("REPLAY REFUSED: the original K2_VERDICT.json and K2_VERDICT.md must exist")
            return 2
        first = S3.read_json(paths[0])
        original = {"files": dict((os.path.basename(p), sha256_file(p)) for p in paths),
                    "verdict": first.get("verdict"), "failed": first.get("failed")}
    R.timing, R.findings = [], []
    evaluate(R)
    perf = S3.performance(R)
    failed = [x for x in R.checks if not x["pass"]]
    verdict = "PASS" if not failed and perf["class"] in ("responsive", "finding") else "FAIL"
    out = {"format": "F01-K2-verdict-v1", "verdict": verdict, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in failed], "performance": perf, "timing": R.timing, "findings": R.findings,
           "reused_evidence": "S3 runs 1-5 (verified Abort, no-op, Clip Editor and proportions refusals, navigation, "
                              "v1 left arm) for the unchanged v2 engine; not repeated"}
    md = S3.markdown(out).replace("# F-01 full-body S3 verdict", "# F-01 K2 Krystal v2 integration verdict", 1)
    names = ("K2_VERDICT.json", "K2_VERDICT.md")
    if replay:
        out["format"] = "F01-K2-verdict-revised-A1-v1"
        out["replay"] = {
            "original": original, "comparator_sha256": sha256_file(os.path.abspath(__file__)),
            "correction": "apply.written_channels_hold_the_record compared every written channel with the saved "
                          "value; under the revised A1 contract (S1 checkpoint section 10) FK positions keep the "
                          "destination's values. Replaced by apply.written_channels_hold_the_planned_values and "
                          "apply.pinned_fk_positions_within_the_revised_A1_limit. All other checks unchanged. "
                          "Re-evaluated from the same evidence; SFM was not run."}
        md = md.replace("# F-01 K2 Krystal v2 integration verdict",
                        "# F-01 K2 Krystal v2 integration verdict, revised A1 replay", 1)
        md += ("\nReplay of the original verdict `K2_VERDICT.json` (%s, failed: %s; sha256 %s), which is unchanged. "
               "%s\n" % (original["verdict"], ", ".join(original["failed"] or []),
                         original["files"]["K2_VERDICT.json"], out["replay"]["correction"]))
        names = REVISED_NAMES
    if R.findings:
        md += "\nFindings: %s\n" % "; ".join(R.findings)
    for name, data in ((names[0], json.dumps(out, indent=1, sort_keys=True)), (names[1], md)):
        fd = os.open(os.path.join(ev, name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(md)
    return 0 if verdict == "PASS" else 1


def main(argv):
    if len(argv) not in (2, 3) or (len(argv) == 3 and argv[2] != "--replay-revised-a1"):
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import k2_tool
    return run(k2_tool.S.load(argv[1]), replay=len(argv) == 3)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
