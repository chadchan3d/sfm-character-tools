# -*- coding: utf-8 -*-
"""F-01 Stage 1: the verdict of the native Fox structural-rig qualification. Python 3, run with -I after restore (SFM
closed). Reads Q/staged/IDENTITIES.json, Q/observations/S1F-<step>.json, Q/evidence (logs, library cleanup and the
saved pose kept in library_after, restore.json) and Q/sessions; writes Q/evidence/S1F_VERDICT.json and S1F_VERDICT.md
(exclusive create). It never changes the run.

Run 2 (Designer disposition after run 1, C5/C6): Process A (PREP, SAVED) creates two fresh Foxes on the disposable
session copy, both rigged by the installed stock rig_biped_simple: Fox S (source, posed) and Fox D (destination,
posed and placed differently); it saves Fox S's Full body and saves the session. The session's original Fox
(foxmccouldwm1, an older rig) is the untouched peer. Process B (BASE ... ABORT) is a new SFM process on that saved
copy. A gate with no evaluated check (a missing capture) is NOT EVALUATED, never PASS.

Gates:
  EVIDENCE   identities; every capture with the qualification build, no capture error; PREP and SAVED from one SFM
             process, BASE..ABORT from another; every capture on S1_SESSION.dmx in the Motion Editor at the same
             shot and playhead; S1_SESSION.dmx saved (it differs from the R2 fixture), S1_SPARE.dmx never; the
             library changed only by the one Fox pose (and its pose_sources.json entry, character files); library
             and installation restored exactly; no unverified, uncertain or failed-Abort result in the CPM logs
  PREP       the recorded fixture preparation: Fox S and Fox D are the same model, both admitted by CPM's structural
             rig discovery with the same description; Fox D is posed and placed visibly differently; the saved
             session reopens with every channel of the three sets as prepared (BASE equals PREP): the same channels,
             bindings, logs and key times, every value exact except quaternion key components, which may differ by
             at most one float32 step (SFM's own reload rounding, measured in run 1: 1.19e-7)
  SAVE       one version 2 structural rig record of Fox S (adapter structural_rig_v1), with the drafted written set;
             the CPM log reports the structural admission; Save read-only; the record selected in Pose Info at SAVED
             and selected again after the restart (BASE)
  APPLY      only Fox D's drafted written channels changed, both rig handle and direct bone channels; on each, every
             key other than the one at the mapped tick unchanged; P7 verified; one owned "Apply Pose" entry
  POSTURE    independent of CPM's planner: every bone of Fox D, relative to its own placement handle, matches Fox S's
             saved posture relative to Fox S's (usable-reproduction tolerances below; maxima reported); Fox D's
             placement handle and model transform, and the local offsets of its directly animated bones, unchanged
  HISTORY    navigation away and back keeps the pose; Undo restores BASE, Redo restores APPLY, the repeat Apply is a
             true no-op, the final Undo restores BASE, each with the expected Edit menu entries
  ABORT      the armed qualification fault after the mixed rig/FK writes of one Apply: the CPM log shows the
             injected failure after as many writes as the committed Apply made and a verified Abort; Fox D's authored
             state and the Undo history exactly as before; the fault slot consumed
  PEER       Fox S (source) and the original Fox (peer) unchanged at every capture
  TAILS      Tails' Save New attempt is refused by the structural discovery (the CPM log: control-less bones,
             BODY-RIG-unavailable) and Tails has no saved pose
Verdict: AUTOMATED PASS (every gate; Stage 1 native acceptance also needs the Owner's visual acceptance);
REFUSED (Fox S's Full body Save was refused: safe, but Stage 1 is not qualified); FAIL (complete evidence, a
functional gate failed); INCOMPLETE (evidence, preparation or restoration missing or failed).

usage: python -I s1f_analyze.py S1F.json      (or: s1f_tool.py S1F.json analyze)
"""
from __future__ import print_function

import glob
import hashlib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A_STEPS = ("PREP", "SAVED")
B_STEPS = ("BASE", "APPLY", "NAV", "UNDO", "REDO", "NOOP", "UNDO2", "ABORT")
STEPS = A_STEPS + B_STEPS
ROLES = ("source", "target", "peer")
SESSION = "S1_SESSION.dmx"
SPARE = "S1_SPARE.dmx"
RULE = {"rule": "structural_rig_v1", "revision": 1}
MODEL = "models/fursonas/foxmccouldwm.mdl"
PLACEMENT = "rig_root"
BAD_LOG = ("PROD_POSE_BODY-P7-unverified", "PROD_POSE_BODY-abort-unverified", "PROD_POSE_BODY-abort-failed",
           "PROD_POSE_BODY-start-undo-uncertain", "PROD_POSE_BODY-finish-undo-uncertain", "recovery-unverified",
           "PROD_POSE_SCOPE-P7-unverified", "PROD_POSE_SCOPE-abort")
FAULT_TEXT = "qualification fault injected at after-writes"
RELOAD_STEP = 2.0 ** -23       # one float32 step for a quaternion component in [0.5, 1): run 1's measured rounding
# Usable reproduction (the designer: faithful, usable posture, not exact matching of harmless secondary effects).
POSTURE_POSITION, POSTURE_ANGLE = 0.05, 0.5
# Unchanged quantities (placement, offsets, peers): the P7 observation tolerances.
SAME_POSITION, SAME_ANGLE = 0.001, 0.01
VISIBLE_ANGLE, VISIBLE_DISTANCE = 10.0, 10.0


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def opt_json(path):
    try:
        with open(path, "rb") as f:
            return json.loads(f.read().decode("utf-8"))
    except Exception:
        return None


# --- rigid transforms -------------------------------------------------------------------------------------------

def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def qconj(q):
    return [-q[0], -q[1], -q[2], q[3]]


def qrot(q, v):
    return qmul(qmul(q, [v[0], v[1], v[2], 0.0]), qconj(q))[:3]


def unit(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return [c / n for c in q]


def relative(frame, world):
    """world expressed in frame (both (position, orientation))."""
    fp, fq = frame[0], unit(frame[1])
    inv = qconj(fq)
    return qrot(inv, [world[0][i] - fp[i] for i in range(3)]), qmul(inv, unit(world[1]))


def angle(a, b):
    d = abs(sum(x * y for x, y in zip(unit(a), unit(b))))
    return math.degrees(2.0 * math.acos(min(1.0, d)))


def dist(a, b):
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def world(row):
    return (row[2], row[3])


# --- the report ---------------------------------------------------------------------------------------------------

class Report(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.info = [], {}
        self.ids = opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap = {}
        for step in STEPS:
            data = opt_json(os.path.join(self.q, "observations", "S1F-%s.json" % step))
            if isinstance(data, dict) and isinstance(data.get("pid"), int):
                self.cap[step] = data

    def check(self, gate, cid, ok, detail=None):
        self.checks.append({"gate": gate, "id": cid, "pass": bool(ok), "detail": None if ok else detail})
        return ok

    def ev(self, *parts):
        return os.path.join(self.q, "evidence", *parts)


def sets(cap, role):
    return (cap.get("sets") or {}).get(role) or {}


def chans(cap, role):
    return sets(cap, role).get("channels") or {}


def field(cap, role, key):
    return dict((n, ch.get(key)) for n, ch in chans(cap, role).items())


def changed(a, b):
    return sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))


def undo(cap):
    u = (cap.get("session") or {}).get("undo")
    return u if isinstance(u, dict) else {}


def adm(cap, role):
    a = sets(cap, role).get("admission")
    return a if isinstance(a, dict) else {}


def posture(cap, role):
    """Every bone relative to the set's own placement handle (from SFM's evaluated absolute transforms)."""
    s = sets(cap, role)
    frame = world((s.get("handles") or {}).get(PLACEMENT) or [[0.0] * 3, [0.0, 0.0, 0.0, 1.0]] * 2)
    return dict((n, relative(frame, world(b))) for n, b in (s.get("bones") or {}).items())


def max_difference(a, b, names):
    dp = max([dist(a[n][0], b[n][0]) for n in names] or [0.0])
    dq = max([angle(a[n][1], b[n][1]) for n in names] or [0.0])
    return dp, dq


def reopened_as_prepared(prep, base, role):
    """BASE against PREP across the restart: identical channels and frames (bindings, logs, key times); key values
    exact, except quaternion components within one float32 step. Returns (ok, rounded keys, problems)."""
    a, b = chans(prep, role), chans(base, role)
    problems, rounded = [], 0
    if sorted(a) != sorted(b):
        return False, 0, ["channels differ"]
    for n in sorted(a):
        if a[n].get("frame") is None or a[n].get("frame") != b[n].get("frame"):
            problems.append(n)
            continue
        ka, kb = a[n].get("keys") or [], b[n].get("keys") or []
        if [[k[0] for k in la] for la in ka] != [[k[0] for k in lb] for lb in kb]:
            problems.append(n)                     # key times (and counts) must be identical
            continue
        for la, lb in zip(ka, kb):
            for x, y in zip(la, lb):
                if x[1] == y[1]:
                    continue
                if isinstance(x[1], list) and len(x[1]) == 4 and isinstance(y[1], list) and len(y[1]) == 4 and \
                        all(abs(float(u) - float(v)) <= RELOAD_STEP for u, v in zip(x[1], y[1])):
                    rounded += 1
                else:
                    problems.append(n)
    return not problems, rounded, problems[:8]


def bones_same(a, b):
    if sorted(a) != sorted(b):
        return False
    return all(dist(a[n][2], b[n][2]) <= SAME_POSITION and angle(a[n][3], b[n][3]) <= SAME_ANGLE and
               dist(a[n][0], b[n][0]) <= SAME_POSITION and angle(a[n][1], b[n][1]) <= SAME_ANGLE for n in a)


def logs(R):
    lines = []
    for path in sorted(glob.glob(R.ev("logs", "*.log"))):
        with open(path, "rb") as f:
            lines.extend(f.read().decode("utf-8", "replace").splitlines())
    return lines


def log_json(line, tag):
    i = line.find(tag)
    if i < 0:
        return None
    try:
        return json.loads(line[i + len(tag):].strip())
    except Exception:
        return None


def saved_records(R):
    out = []
    for path in sorted(glob.glob(R.ev("library_after", "Characters", "*", "Poses", "*.json"))):
        out.append((os.path.relpath(path, R.ev("library_after")).replace("\\", "/"), opt_json(path)))
    return out


def pose_sources_ok(R, x, poses):
    parts = x["path"].split("/")
    if (x["status"] != "added" or len(parts) != 3 or parts[0] != "Characters" or parts[2] != "pose_sources.json" or
            len(poses) != 1 or poses[0]["path"].split("/")[1] != parts[1]):
        return False
    path = R.ev("library_after", *parts)
    if not os.path.isfile(path) or sha(path) != x.get("sha256"):
        return False
    data = opt_json(path)
    pid = (opt_json(R.ev("library_after", *poses[0]["path"].split("/"))) or {}).get("preset_id")
    norm = lambda p: p.replace("/", "\\").lower() if isinstance(p, type(u"")) else None  # noqa: E731
    if not isinstance(data, dict) or sorted(data) != ["entries", "record_kind", "schema_version"]:
        return False
    entries = data["entries"]
    return (data["record_kind"] == u"cpm-pose-sources" and data["schema_version"] == 1 and
            isinstance(pid, type(u"")) and isinstance(entries, dict) and list(entries) == [pid] and
            isinstance(entries[pid], dict) and list(entries[pid]) == ["project"] and
            norm(entries[pid]["project"]) == norm(os.path.join(R.q, "sessions", SESSION)))


def library_and_restore(R):
    clean = opt_json(R.ev("library_cleanup.json")) or {}
    diffs = clean.get("differences_kept_in_evidence") or []
    poses = [x for x in diffs if "/Poses/" in x["path"]]
    allowed = lambda x: (x["status"] == "added" and x["path"].startswith("Characters/") and  # noqa: E731
                         (re.match(r"^Characters/[^/]+/Poses/[^/]+\.json$", x["path"]) or
                          re.match(r"^Characters/[^/]+/character\.json(\.bak)?$", x["path"]) or
                          pose_sources_ok(R, x, poses)))
    unexpected = [x for x in diffs if not allowed(x)]
    R.check("EVIDENCE", "library.changed_only_by_the_one_fox_pose", bool(clean) and not unexpected and
            len(poses) <= 1, {"unexpected": unexpected, "poses": poses})
    R.check("EVIDENCE", "restore.library_exactly_as_before", clean.get("files_equal_pre") is True and
            clean.get("folders_equal_pre") is True)
    restore = opt_json(R.ev("restore.json")) or {}
    R.check("EVIDENCE", "restore.published_and_inventories_equal", restore.get("restored") is True,
            restore.get("inventory_problems"))


def evaluate(R):
    cap, c = R.cap, R.c
    E = lambda cid, ok, d=None: R.check("EVIDENCE", cid, ok, d)  # noqa: E731
    want = c["pins"]["qualification_cpm_sha256"]
    E("identity.qualification_build", R.ids.get("qualification_cpm_sha256") == want and
      R.ids.get("candidate_cpm_sha256") == c["pins"]["candidate_cpm_sha256"], R.ids.get("qualification_cpm_sha256"))
    records = saved_records(R)
    refused = "SAVED" in cap and not records
    R.info["refusal"] = "Fox S's Full body Save wrote no record" if refused else None
    steps = A_STEPS if refused else STEPS
    for step in steps:
        if not E("captured.%s" % step, step in cap):
            continue
        d = cap[step]
        E("cpm.%s" % step, d.get("cpm_build_sha256") == want and d.get("registry_mode") == u"qualification",
          (d.get("cpm_build_sha256"), d.get("registry_mode")))
        E("errors.%s" % step, not d.get("errors") and all(r in (d.get("sets") or {}) for r in ROLES), d.get("errors"))
    session = os.path.join(R.q, "sessions", SESSION)
    spare = os.path.join(R.q, "sessions", SPARE)
    E("sessions.s1_session_saved_by_process_a", os.path.isfile(session) and sha(session) !=
      c["pins"]["r2_fixture_sha256"])
    E("sessions.s1_spare_never_saved", os.path.isfile(spare) and sha(spare) == c["pins"]["destination_sha256"])
    R.info["s1_session_sha256"] = sha(session) if os.path.isfile(session) else None
    R.info["sessions_folder"] = sorted(os.listdir(os.path.join(R.q, "sessions"))) if os.path.isdir(
        os.path.join(R.q, "sessions")) else None
    library_and_restore(R)
    lines = logs(R)
    E("log.collected", bool(lines))
    bad = [l for l in lines if any(b in l for b in BAD_LOG)]
    E("log.no_unverified_uncertain_or_failed_abort_result", not bad, bad[:4])
    if any(s not in cap for s in steps):
        return refused
    pa = set(cap[s]["pid"] for s in A_STEPS)
    pb = set(cap[s]["pid"] for s in steps if s in B_STEPS)
    E("process.a_then_a_restarted_b", len(pa) == 1 and (refused or (len(pb) == 1 and pa != pb)),
      (sorted(pa), sorted(pb)))
    docs = set(u"%s" % ((cap[s].get("session") or {}).get("document") or u"") for s in steps)
    E("process.every_capture_on_the_disposable_session", len(docs) == 1 and list(docs)[0].lower().replace(
        "\\", "/").endswith(SESSION.lower()), sorted(docs))
    heads = [(cap[s].get("session") or {}).get("head_seconds") for s in steps]
    shots = set(u"%s" % (cap[s].get("session") or {}).get("shot") for s in steps)
    modes = set(u"%s" % (cap[s].get("session") or {}).get("timeline_mode") for s in steps)
    E("session.same_shot_and_playhead_motion_editor", len(shots) == 1 and all(h == heads[0] for h in heads) and
      modes == set([u"2"]), (sorted(shots), heads, sorted(modes)))

    Pp = lambda cid, ok, d=None: R.check("PREP", cid, ok, d)  # noqa: E731
    prep = cap["PREP"]
    models = dict((r, sets(prep, r).get("model")) for r in ROLES)
    Pp("prep.fox_s_and_fox_d_are_the_fox_model", all((u"%s" % models[r]).replace("\\", "/").lower() == MODEL
                                                    for r in ("source", "target")), models)
    a_src, a_tgt = adm(prep, "source"), adm(prep, "target")
    Pp("prep.both_foxes_admitted_by_structural_discovery", a_src.get("placement") == PLACEMENT and
       a_tgt.get("placement") == PLACEMENT, {"source": a_src.get("error") or a_src.get("placement"),
                                             "target": a_tgt.get("error") or a_tgt.get("placement")})
    Pp("prep.same_drafted_description_whatever_the_rig_name", a_src.get("description_sha256") and
       a_src.get("description_sha256") == a_tgt.get("description_sha256") and
       a_src.get("rig_name") != a_tgt.get("rig_name"), (a_src.get("rig_name"), a_tgt.get("rig_name")))
    ps, pt = posture(prep, "source"), posture(prep, "target")
    names = sorted(set(ps) & set(pt))
    dp, dq = max_difference(ps, pt, names)
    R.info["prep_difference"] = {"position": dp, "angle_degrees": dq}
    hs = world((sets(prep, "source").get("handles") or {}).get(PLACEMENT) or [[0.0] * 3, [0, 0, 0, 1]] * 2)
    ht = world((sets(prep, "target").get("handles") or {}).get(PLACEMENT) or [[0.0] * 3, [0, 0, 0, 1]] * 2)
    Pp("prep.fox_d_posed_and_placed_visibly_differently", dq > VISIBLE_ANGLE and (
        dist(hs[0], ht[0]) > VISIBLE_DISTANCE or angle(hs[1], ht[1]) > VISIBLE_ANGLE),
       {"posture_angle": dq, "placement_distance": dist(hs[0], ht[0]), "placement_angle": angle(hs[1], ht[1])})
    if not refused:
        base = cap["BASE"]
        reopened = dict((r, reopened_as_prepared(prep, base, r)) for r in ROLES)
        R.info["reload_rounded_keys"] = dict((r, v[1]) for r, v in reopened.items())
        Pp("prep.saved_session_reopens_as_prepared", all(v[0] for v in reopened.values()),
           dict((r, v[2]) for r, v in reopened.items()))

    V = lambda cid, ok, d=None: R.check("SAVE", cid, ok, d)  # noqa: E731
    saved = cap["SAVED"]
    rec = records[0][1] if len(records) == 1 else {}
    pose = (rec or {}).get("pose") or {}
    region = (pose.get("regions") or {}).get("full_body") or {}
    R.info["record"] = [r[0] for r in records]
    written = len(region.get("positions") or {}) + len(region.get("orientations") or {})
    V("save.one_version2_structural_record_of_fox_s", len(records) == 1 and pose.get("version") == 2 and
      pose.get("adapter") == RULE and sorted(pose.get("regions") or []) == ["full_body"] and
      (u"%s" % (pose.get("source") or {}).get("model_ref")).lower() == MODEL and
      sorted(list(region.get("positions") or {}) + list(region.get("orientations") or {})) ==
      sorted(a_src.get("written") or []), {"records": len(records), "adapter": pose.get("adapter"),
                                           "written": written, "drafted": len(a_src.get("written") or [])})
    V("save.structural_admission_logged", any("PROD_POSE_BODY-RIG-available" in l for l in lines))
    V("save.read_only", all(field(saved, r, "sha256") == field(prep, r, "sha256") for r in ROLES),
      dict((r, changed(field(prep, r, "sha256"), field(saved, r, "sha256"))[:6]) for r in ROLES))
    sel = saved.get("selected_pose") or {}
    V("save.pose_info_selection_is_the_saved_record", isinstance(sel, dict) and sel.get("adapter") == RULE and
      sel.get("preset_id") == (rec or {}).get("preset_id"), sel)
    if refused:
        return refused
    selb = cap["BASE"].get("selected_pose") or {}
    V("save.reopened_after_the_restart", isinstance(selb, dict) and selb.get("preset_id") == (rec or {}).get(
        "preset_id") and selb.get("adapter") == RULE, selb)

    A = lambda cid, ok, d=None: R.check("APPLY", cid, ok, d)  # noqa: E731
    base, app = cap["BASE"], cap["APPLY"]
    roles = adm(base, "target").get("roles") or {}
    t_chan = adm(base, "target").get("t_chan")
    moved = changed(field(base, "target", "sha256"), field(app, "target", "sha256"))
    kinds = sorted(set(roles.get(n) for n in moved))
    R.info["target_channels_changed"] = len(moved)
    A("apply.target_changed_on_rig_handle_and_direct_bone_channels", u"handle-written" in kinds and
      u"fk-written" in kinds, kinds)
    A("apply.only_drafted_written_channels_changed", moved and set(moved) <= set(adm(base, "target").get(
        "written") or []), [n for n in moved if n not in (adm(base, "target").get("written") or [])][:8])
    neighbours = []
    kb, ka = field(base, "target", "keys"), field(app, "target", "keys")
    for n in moved:
        before = [k for layer in kb.get(n) or [] for k in layer]
        after = [k for layer in ka.get(n) or [] for k in layer]
        if [k for k in before if k[0] != t_chan] != [k for k in after if k[0] != t_chan] or \
                len([k for k in after if k[0] == t_chan]) != 1:
            neighbours.append(n)
    A("apply.other_keys_unchanged_one_key_at_the_mapped_tick", t_chan is not None and not neighbours,
      neighbours[:8])
    A("apply.p7_verified_in_the_cpm_log", any("PROD_POSE_BODY-P7-verified" in l for l in lines))
    au = undo(app)
    A("apply.one_owned_history_entry", u"%s" % au.get("undo_desc") == u"Apply Pose %s" % (rec or {}).get("name")
      and au.get("can_redo") is False, au)

    Q = lambda cid, ok, d=None: R.check("POSTURE", cid, ok, d)  # noqa: E731
    src_pose, dst_pose = posture(saved, "source"), posture(app, "target")
    kept = set(b for e in region.get("exclusions") or [] for b in e.get("bones") or [])
    names = sorted((set(src_pose) & set(dst_pose)) - kept)
    dp, dq = max_difference(src_pose, dst_pose, names)
    classes = adm(base, "target").get("bone_classes") or {}
    per = {}
    for cls in ("constrained", "fk"):
        sub = [n for n in names if classes.get(n) == cls]
        per[cls] = dict(zip(("position", "angle_degrees", "bones"), max_difference(src_pose, dst_pose, sub) +
                            (len(sub),)))
    R.info["posture"] = {"position": dp, "angle_degrees": dq, "bones": len(names), "by_class": per}
    Q("posture.fox_d_takes_fox_s_saved_body_posture_independently_observed", len(names) == len(src_pose) - len(
        kept & set(src_pose)) and per["constrained"]["bones"] > 0 and dp <= POSTURE_POSITION and
      dq <= POSTURE_ANGLE, R.info["posture"])
    hb, ha = (sets(base, "target").get("handles") or {}).get(PLACEMENT), (sets(app, "target").get("handles") or
                                                                         {}).get(PLACEMENT)
    mb, ma = sets(base, "target").get("model_state"), sets(app, "target").get("model_state")
    Q("posture.placement_handle_and_model_unchanged", hb and ha and mb and ma and dist(hb[2], ha[2]) <= SAME_POSITION
      and angle(hb[3], ha[3]) <= SAME_ANGLE and dist(mb[2], ma[2]) <= SAME_POSITION and
      angle(mb[3], ma[3]) <= SAME_ANGLE, (hb, ha))
    fk = [n for n in names if classes.get(n) == "fk"]
    bb, ba = sets(base, "target").get("bones") or {}, sets(app, "target").get("bones") or {}
    offsets = [n for n in fk if dist(bb[n][0], ba[n][0]) > SAME_POSITION]
    Q("posture.proportions_direct_bone_offsets_kept", fk and not offsets, offsets[:8])

    H = lambda cid, ok, d=None: R.check("HISTORY", cid, ok, d)  # noqa: E731
    sh = lambda s: field(cap[s], "target", "sha256")  # noqa: E731
    H("navigation.pose_holds_after_moving_away_and_back", sh("NAV") == sh("APPLY") and bones_same(
        sets(cap["NAV"], "target").get("bones") or {}, ba) and undo(cap["NAV"]) == au)
    H("undo.target_equals_base", sh("UNDO") == sh("BASE"), changed(sh("BASE"), sh("UNDO"))[:6])
    H("undo.history", undo(cap["UNDO"]).get("undo_desc") == undo(base).get("undo_desc") and
      u"%s" % undo(cap["UNDO"]).get("redo_desc") == u"Redo %s" % au.get("undo_desc"), undo(cap["UNDO"]))
    H("redo.target_equals_apply", sh("REDO") == sh("APPLY") and undo(cap["REDO"]).get("undo_desc") ==
      au.get("undo_desc"), undo(cap["REDO"]))
    H("noop.writes_nothing_and_adds_no_entry", sh("NOOP") == sh("REDO") and undo(cap["NOOP"]) == undo(cap["REDO"]),
      undo(cap["NOOP"]))
    H("noop.reported_by_cpm", any("PROD_POSE_BODY-P1" in l and '"noop": true' in l for l in lines))
    H("final_undo.target_equals_base", sh("UNDO2") == sh("BASE") and undo(cap["UNDO2"]).get("undo_desc") ==
      undo(base).get("undo_desc"), undo(cap["UNDO2"]))

    X = lambda cid, ok, d=None: R.check("ABORT", cid, ok, d)  # noqa: E731
    failures = [l for l in lines if "PROD_POSE_BODY-P3-P6-failure" in l]
    p6 = [log_json(l, "PROD_POSE_BODY-P6") for l in lines if "PROD_POSE_BODY-P6" in l]
    first = (p6[0] or {}).get("written") if p6 else None
    fail = log_json(failures[0], "PROD_POSE_BODY-P3-P6-failure") if len(failures) == 1 else None
    R.info["abort"] = {"failure": fail, "committed_writes": first}
    X("abort.injected_after_the_mixed_rig_and_fk_writes", isinstance(fail, dict) and FAULT_TEXT in u"%s" % fail.get(
        "error") and fail.get("finished") is False and isinstance(first, int) and first > 0 and
      fail.get("written") == first, R.info["abort"])
    X("abort.verified_by_cpm", len([l for l in lines if "PROD_POSE_BODY-abort-verified" in l]) == 1)
    X("abort.authored_state_and_history_restored", sh("ABORT") == sh("UNDO2") and undo(cap["ABORT"]) ==
      undo(cap["UNDO2"]), (changed(sh("UNDO2"), sh("ABORT"))[:6], undo(cap["ABORT"])))
    X("abort.fault_slot_consumed", cap["ABORT"].get("qualification_fault") == [None] and
      cap["UNDO2"].get("qualification_fault") == [None], cap["ABORT"].get("qualification_fault"))

    P = lambda cid, ok, d=None: R.check("PEER", cid, ok, d)  # noqa: E731
    for role in ("source", "peer"):
        P("%s.unchanged_in_process_a" % role, field(saved, role, "sha256") == field(prep, role, "sha256"))
        P("%s.unchanged_in_process_b" % role, all(field(cap[s], role, "sha256") == field(base, role, "sha256") and
                                                  bones_same(sets(cap[s], role).get("bones") or {},
                                                             sets(base, role).get("bones") or {}) for s in B_STEPS),
          [s for s in B_STEPS if field(cap[s], role, "sha256") != field(base, role, "sha256")])

    T = lambda cid, ok, d=None: R.check("TAILS", cid, ok, d)  # noqa: E731
    T("tails.refused_by_structural_discovery", any("PROD_POSE_BODY-RIG-unavailable" in l and "structure-unsupported" in l
                                                   for l in lines) and
      any("PROD_POSE_BODY-refused" in l and "control-less bones" in l for l in lines))
    T("tails.no_saved_pose", len(records) == 1 and records[0][0].split("/")[1].lower().startswith("foxmccouldwm"),
      [r[0] for r in records])
    return refused


def verdict(checks, refused):
    """Each gate True (every check passed), False (one failed) or None: NOT EVALUATED (no check ran, e.g. a missing
    capture stopped the analysis). Never PASS without a passed check."""
    def gate(name):
        mine = [x["pass"] for x in checks if x["gate"] == name]
        return all(mine) if mine else None
    names = ("EVIDENCE", "PREP", "SAVE", "APPLY", "POSTURE", "HISTORY", "ABORT", "PEER", "TAILS")
    gates = dict((n, gate(n)) for n in names)
    if gates["EVIDENCE"] is not True or gates["PREP"] is False:
        v = "INCOMPLETE"
    elif refused:
        v = "REFUSED"
    elif all(g is True for g in gates.values()):
        v = "AUTOMATED PASS"
    elif gates["PREP"] is None:
        v = "INCOMPLETE"
    else:
        v = "FAIL"
    return v, gates


def gate_text(v):
    return "PASS" if v is True else "FAIL" if v is False else "NOT EVALUATED"


def markdown(out):
    lines = ["# F-01 Stage 1 native Fox qualification: %s" % out["verdict"], "",
             "Qualification CPM `%s` (Stage 1 candidate `%s`). Gates: %s." % (
                 out["identities"].get("qualification_cpm_sha256"), out["identities"].get("candidate_cpm_sha256"),
                 ", ".join("%s %s" % (k, gate_text(v)) for k, v in sorted(out["gates"].items()))), ""]
    if out["verdict"] == "AUTOMATED PASS":
        lines += ["**Every automated gate passed. Stage 1 native acceptance also needs the Owner's visual acceptance** "
                  "(Fox D takes Fox S's body posture and secondary articulation, in its own place, without severe "
                  "distortion).", ""]
    elif out["verdict"] == "REFUSED":
        lines += ["**Fox S's Full body was refused (%s): safe, but Stage 1 is not natively qualified.**"
                  % out["info"].get("refusal"), ""]
    lines += ["| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in out["checks"]:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False, default=repr)[:300].replace("|", "\\|")
        lines.append("| %s | `%s` | %s | %s |" % (x["gate"], x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    lines += ["", "Info: `%s`" % json.dumps(out["info"], ensure_ascii=False, default=repr)[:900]]
    return "\n".join(lines) + "\n"


def run(c):
    R = Report(c)
    refused = evaluate(R)
    v, gates = verdict(R.checks, refused)
    out = {"format": "F01-S1F-verdict-v1", "verdict": v, "gates": gates, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in R.checks if not x["pass"]], "info": R.info,
           "analyzer_sha256": sha(os.path.abspath(__file__))}
    md = markdown(out)
    for name, data in (("S1F_VERDICT.json", json.dumps(out, indent=1, sort_keys=True, default=repr)),
                       ("S1F_VERDICT.md", md)):
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
    import s1f_tool
    return run(s1f_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
