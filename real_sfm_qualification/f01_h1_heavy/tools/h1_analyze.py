# -*- coding: utf-8 -*-
"""F-01 H1: the verdict of the native Heavy procedural-helper check. Python 3, run with -I after restore (SFM closed).
Reads Q/staged/IDENTITIES.json, Q/observations/H1-<step>.json, Q/evidence (logs, library cleanup and the saved pose
kept in library_after, restore.json) and Q/sessions; writes Q/evidence/H1_VERDICT.json and H1_VERDICT.md (exclusive
create). It never changes the run.

Gates:
  EVIDENCE  identities, every capture from one SFM process on H1_SESSION.dmx with the qualification build, shot and
            playhead never moved, three Heavy instances, sessions never saved, the library changed only by the one
            saved Heavy pose (and its one pose_sources.json entry), library and installation restored exactly, no Abort, recovery or unverified result in
            the CPM log
  HEADER    the engine header was read on source and target and CPM admitted the same declared QUATINTERP helpers
            with no refusal
  SAVE      one version 3 Full body record whose ledger marks exactly those helpers engine-helper; Save read-only
  APPLY     the target changed (a visibly distinct pose) only on bone transform channels, never on a helper channel;
            P7 verified; one owned "Apply Pose" entry
  UNDO      Undo restores the target's channels to BASE, Redo to APPLY; the second Apply is a true no-op
  PEER      the peer's channels and bones, and the source's channels, unchanged at every capture
Verdict: AUTOMATED PASS (every gate; the Owner's visual acceptance of arms, body and helpers is still required);
SAFE REFUSAL (the Heavy was refused at the header or at Save: a safe limitation, NOT a compatibility result);
FAIL (complete evidence, a functional gate failed); INCOMPLETE (evidence or restoration missing or failed).

usage: python -I h1_analyze.py H1.json      (or: h1_tool.py H1.json analyze)
       python -I h1_analyze.py H1.json --replay   (H1_REPLAY_VERDICT.json/.md; the original verdict must exist)
"""
from __future__ import print_function

import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ("BASE", "SAVED", "APPLY", "UNDO", "REDO", "NOOP")
ROLES = ("source", "target", "peer")
SESSION_DOC = u"h1_session.dmx"
HELPER_ROLE = u"engine-helper"
BONE_RE = re.compile(r"^bone (\d+) \((.+)\)$")
BAD_LOG = ("PROD_POSE_SCOPE-P7-unverified", "PROD_POSE_SCOPE-abort", "PROD_POSE_SCOPE-P3-P6-failure",
           "PROD_POSE_SCOPE-start-undo-uncertain", "PROD_POSE_SCOPE-finish-undo-uncertain", "recovery-unverified")
BONE_TOLERANCE = 1e-4


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def opt_json(path):
    try:
        with open(path, "rb") as f:
            return json.loads(f.read().decode("utf-8"))
    except Exception:
        return None


class Report(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.info, self.findings = [], {}, []
        self.ids = opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap = {}
        for step in STEPS:
            data = opt_json(os.path.join(self.q, "observations", "H1-%s.json" % step))
            if isinstance(data, dict) and isinstance(data.get("pid"), int):
                self.cap[step] = data

    def check(self, gate, cid, ok, detail=None):
        self.checks.append({"gate": gate, "id": cid, "pass": bool(ok), "detail": None if ok else detail})
        return ok

    def ev(self, *parts):
        return os.path.join(self.q, "evidence", *parts)


def channels(cap, role):
    return ((cap.get("sets") or {}).get(role) or {}).get("channels") or {}


def digests(cap, role):
    return dict((n, ch.get("sha256")) for n, ch in channels(cap, role).items())


def changed(a, b):
    return sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))


def bone_of(ch):
    m = BONE_RE.match(ch.get("to") or u"")
    return m.group(2) if m else None


def bones_close(a, b):
    if sorted(a) != sorted(b):
        return False
    for n in a:
        for x, y in zip(a[n], b[n]):
            if len(x) != len(y) or any(abs(float(p) - float(q)) > BONE_TOLERANCE for p, q in zip(x, y)):
                return False
    return True


def logs(R):
    lines = []
    for path in sorted(glob.glob(R.ev("logs", "*.log"))):
        with open(path, "rb") as f:
            lines.extend(f.read().decode("utf-8", "replace").splitlines())
    return lines


def saved_records(R):
    out = []
    for path in sorted(glob.glob(R.ev("library_after", "Characters", "*", "Poses", "*.json"))):
        data = opt_json(path)
        out.append((os.path.relpath(path, R.ev("library_after")).replace("\\", "/"), data))
    return out


def pose_sources_ok(R, x, poses):
    """Save New's informational sidecar pose_sources.json: added in the one saved pose's own character folder, the
    file kept in library_after is the one recorded, and it holds exactly one entry, keyed by that pose's preset_id,
    whose only field is the project, this run's sessions/H1_SESSION.dmx."""
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
    want = norm(os.path.join(R.q, "sessions", "H1_SESSION.dmx"))
    if not isinstance(data, dict) or sorted(data) != ["entries", "record_kind", "schema_version"]:
        return False
    entries = data["entries"]
    return (data["record_kind"] == u"cpm-pose-sources" and data["schema_version"] == 1 and
            isinstance(pid, type(u"")) and isinstance(entries, dict) and list(entries) == [pid] and
            isinstance(entries[pid], dict) and list(entries[pid]) == ["project"] and
            norm(entries[pid]["project"]) == want)


def library_and_restore(R, refused_run=False):
    """The library changed only by the one saved Heavy pose and its pose_sources.json entry (none when the Heavy was
    refused); restored exactly."""
    clean = opt_json(R.ev("library_cleanup.json")) or {}
    diffs = clean.get("differences_kept_in_evidence") or []
    dirs = set(x["path"].split("/")[1] for x in diffs if x["path"].startswith("Characters/") and
               len(x["path"].split("/")) > 2)
    poses = [x for x in diffs if "/Poses/" in x["path"]]
    allowed = lambda x: (x["status"] == "added" and x["path"].startswith("Characters/") and  # noqa: E731
                         (re.match(r"^Characters/[^/]+/Poses/[^/]+\.json$", x["path"]) or
                          re.match(r"^Characters/[^/]+/character\.json(\.bak)?$", x["path"]) or
                          pose_sources_ok(R, x, poses)))
    unexpected = [x for x in diffs if not allowed(x)]
    want = (len(dirs) <= 1 and not poses) if refused_run else (len(dirs) == 1 and len(poses) == 1)
    R.check("EVIDENCE", "library.changed_only_by_the_one_saved_heavy_pose",
            bool(clean) and not unexpected and want, {"unexpected": unexpected, "poses": poses})
    R.check("EVIDENCE", "restore.library_exactly_as_before", clean.get("files_equal_pre") is True and
            clean.get("folders_equal_pre") is True)
    restore = opt_json(R.ev("restore.json")) or {}
    R.check("EVIDENCE", "restore.published_and_inventories_equal", restore.get("restored") is True,
            restore.get("inventory_problems"))


def refused(R):
    """The Heavy was refused (header unreadable or no helper admitted, or nothing saved): a safe limitation."""
    base = R.cap.get("BASE") or {}
    adm = ((base.get("sets") or {}).get("target") or {}).get("admission") or {}
    hdr = ((base.get("sets") or {}).get("target") or {}).get("header") or {}
    if base and (hdr.get("status") != "READ" or not adm.get("helpers")):
        return "the native header or helper admission refused the known Heavy: header %r, admission %r" % (
            hdr.get("status"), adm)
    if "SAVED" in R.cap and not saved_records(R):
        return "Full body Save of the Heavy was refused (no record was written)"
    return None


def evaluate(R):
    cap, c = R.cap, R.c
    E = lambda cid, ok, d=None: R.check("EVIDENCE", cid, ok, d)  # noqa: E731
    want = c["pins"]["qualification_cpm_sha256"]
    E("identity.qualification_build", R.ids.get("qualification_cpm_sha256") == want and
      R.ids.get("candidate_cpm_sha256") == c["pins"]["candidate_cpm_sha256"], R.ids.get("qualification_cpm_sha256"))
    limitation = refused(R)
    R.info["refusal"] = limitation
    steps = ("BASE", "SAVED") if limitation else STEPS
    for step in steps:
        if not E("captured.%s" % step, step in cap):
            continue
        d = cap[step]
        E("cpm.%s" % step, d.get("cpm_build_sha256") == want, d.get("cpm_build_sha256"))
        E("errors.%s" % step, not d.get("errors") and all(r in (d.get("sets") or {}) for r in ROLES), d.get("errors"))
    for name, pin in (("H1_SESSION.dmx", "r2_fixture_sha256"), ("H1_SPARE.dmx", "destination_sha256")):
        path = os.path.join(R.q, "sessions", name)
        E("sessions.%s_never_saved" % name, os.path.isfile(path) and sha(path) == c["pins"][pin])
    library_and_restore(R, bool(limitation))
    lines = logs(R)
    E("log.collected", bool(lines))
    bad = [l for l in lines if any(b in l for b in BAD_LOG)]
    E("log.no_abort_recovery_or_unverified_result", not bad, bad[:4])
    if any(s not in cap for s in steps):
        return limitation
    pids = set(cap[s]["pid"] for s in steps)
    docs = set(u"%s" % ((cap[s].get("session") or {}).get("document") or u"") for s in steps)
    E("process.one_sfm_process_on_the_disposable_session", len(pids) == 1 and len(docs) == 1 and
      list(docs)[0].lower().replace("\\", "/").endswith(SESSION_DOC), (sorted(pids), sorted(docs)))
    heads = [(cap[s].get("session") or {}).get("head_seconds") for s in steps]
    shots = set(u"%s" % (cap[s].get("session") or {}).get("shot") for s in steps)
    E("session.shot_and_playhead_never_moved", len(shots) == 1 and all(h == heads[0] for h in heads),
      (sorted(shots), heads))
    models = dict((r, ((cap["BASE"].get("sets") or {}).get(r) or {}).get("model")) for r in ROLES)
    E("instances.three_heavies", all(u"%s" % m and (u"%s" % m).replace("\\", "/").lower().endswith(
        "player/heavy.mdl") for m in models.values()), models)
    if limitation:
        return limitation

    H = lambda cid, ok, d=None: R.check("HEADER", cid, ok, d)  # noqa: E731
    sets = dict((r, cap["BASE"]["sets"][r]) for r in ROLES)
    adm = dict((r, sets[r].get("admission") or {}) for r in ROLES)
    helpers = sorted(adm["target"].get("helpers") or [])
    R.info["helpers"] = helpers
    H("header.read_on_source_and_target", all((sets[r].get("header") or {}).get("status") == "READ"
                                              for r in ("source", "target")),
      dict((r, sets[r].get("header")) for r in ROLES))
    H("helpers.admitted_alike_on_source_and_target_without_refusal",
      helpers and sorted(adm["source"].get("helpers") or []) == helpers and not adm["target"].get("refusals") and
      not adm["source"].get("refusals"), adm)
    declared = (sets["target"].get("header") or {}).get("declared") or []
    H("helpers.are_exactly_the_declared_quatinterp_bones",
      sorted(r[1] for r in declared) == helpers and all(r[4] == 2 and r[3] & 4 for r in declared), declared)
    H("instances.unrigged", all("constrained" not in (adm[r].get("classes") or {}) for r in ROLES),
      dict((r, adm[r].get("classes")) for r in ROLES))

    V = lambda cid, ok, d=None: R.check("SAVE", cid, ok, d)  # noqa: E731
    records = saved_records(R)
    pose = (records[0][1] or {}).get("pose") or {} if len(records) == 1 else {}
    scope = pose.get("scope") or {}
    ledger_helpers = sorted(n for n, r in (scope.get("ledger") or {}).items() if r == HELPER_ROLE)
    R.info["record"] = records[0][0] if len(records) == 1 else [r[0] for r in records]
    V("save.one_version3_full_body_record_marking_the_helpers",
      len(records) == 1 and pose.get("version") == 3 and scope.get("kind") == "full_body" and
      (pose.get("engine") or {}).get("rule") == "direct_fk_v1" and ledger_helpers == helpers and
      u"%s" % (pose.get("source") or {}).get("model_ref") == u"%s" % models["source"],
      {"records": len(records), "kind": scope.get("kind"), "ledger_helpers": ledger_helpers})
    sel = cap["SAVED"].get("selected_pose") or {}
    V("save.reopened_pose_is_the_saved_full_body", isinstance(sel, dict) and sel.get("kind") == "full_body" and
      sorted(sel.get("helpers") or []) == helpers, sel)
    V("save.read_only", all(digests(cap["SAVED"], r) == digests(cap["BASE"], r) for r in ROLES),
      dict((r, changed(digests(cap["BASE"], r), digests(cap["SAVED"], r))[:6]) for r in ROLES))

    A = lambda cid, ok, d=None: R.check("APPLY", cid, ok, d)  # noqa: E731
    tb = channels(cap["BASE"], "target")
    helper_channels = sorted(n for n, ch in tb.items() if bone_of(ch) in helpers)
    moved = changed(digests(cap["BASE"], "target"), digests(cap["APPLY"], "target"))
    R.info["target_channels_changed"] = len(moved)
    A("apply.target_visibly_changed", len(moved) >= 3, moved)
    A("apply.only_bone_transform_channels_written",
      all(bone_of(tb.get(n) or {}) is not None and (tb.get(n) or {}).get("to_attribute") in ("position", "orientation")
          for n in moved), [n for n in moved if bone_of(tb.get(n) or {}) is None])
    A("apply.helper_channels_never_written", helper_channels and all(
        digests(cap[s], "target").get(n) == digests(cap["BASE"], "target").get(n) for s in STEPS
        for n in helper_channels), helper_channels)
    A("apply.verified_in_the_cpm_log", any("PROD_POSE_SCOPE-P7-verified" in l for l in lines))
    au = (cap["APPLY"].get("session") or {}).get("undo") or {}
    A("apply.one_owned_history_entry", u"%s" % au.get("undo_desc") == u"Apply Pose %s" % (
        (records[0][1] or {}).get("name") if len(records) == 1 else None) and au.get("can_redo") is False, au)

    U = lambda cid, ok, d=None: R.check("UNDO", cid, ok, d)  # noqa: E731
    U("undo.target_equals_base", digests(cap["UNDO"], "target") == digests(cap["BASE"], "target"),
      changed(digests(cap["BASE"], "target"), digests(cap["UNDO"], "target"))[:6])
    uu, su = (cap["UNDO"].get("session") or {}).get("undo") or {}, (cap["SAVED"].get("session") or {}).get("undo") or {}
    U("undo.history", uu.get("undo_desc") == su.get("undo_desc") and
      u"%s" % uu.get("redo_desc") == u"Redo %s" % au.get("undo_desc"), uu)
    U("redo.target_equals_apply", digests(cap["REDO"], "target") == digests(cap["APPLY"], "target"))
    ru = (cap["REDO"].get("session") or {}).get("undo") or {}
    U("redo.history", ru.get("undo_desc") == au.get("undo_desc") and ru.get("can_redo") is False, ru)
    nu = (cap["NOOP"].get("session") or {}).get("undo") or {}
    U("noop.writes_nothing_and_adds_no_entry", digests(cap["NOOP"], "target") == digests(cap["REDO"], "target") and
      nu == ru, nu)
    U("noop.reported_by_cpm", any("PROD_POSE_SCOPE-P1" in l and '"noop": true' in l for l in lines))

    P = lambda cid, ok, d=None: R.check("PEER", cid, ok, d)  # noqa: E731
    for s in STEPS[1:]:
        P("peer.channels_unchanged_at_%s" % s, digests(cap[s], "peer") == digests(cap["BASE"], "peer"),
          changed(digests(cap["BASE"], "peer"), digests(cap[s], "peer"))[:6])
        P("peer.bones_unchanged_at_%s" % s, bones_close(cap[s]["sets"]["peer"].get("bones") or {},
                                                       cap["BASE"]["sets"]["peer"].get("bones") or {}))
        P("source.channels_unchanged_at_%s" % s, digests(cap[s], "source") == digests(cap["BASE"], "source"))
    return None


def verdict(checks, limitation):
    gate = lambda name: all(x["pass"] for x in checks if x["gate"] == name)  # noqa: E731
    gates = dict((n, gate(n)) for n in ("EVIDENCE", "HEADER", "SAVE", "APPLY", "UNDO", "PEER"))
    if not gates["EVIDENCE"]:
        v = "INCOMPLETE"
    elif limitation or not gates["HEADER"]:
        v = "SAFE REFUSAL"
    elif all(gates.values()):
        v = "AUTOMATED PASS"
    else:
        v = "FAIL"
    return v, gates


def markdown(out):
    lines = ["# F-01 H1 native Heavy check: %s" % out["verdict"], "",
             "Qualification CPM `%s` (H1 candidate `%s`). Gates: %s." % (
                 out["identities"].get("qualification_cpm_sha256"), out["identities"].get("candidate_cpm_sha256"),
                 ", ".join("%s %s" % (k, "PASS" if v else "FAIL") for k, v in sorted(out["gates"].items()))), ""]
    if out["verdict"] == "AUTOMATED PASS":
        lines += ["**Every automated gate passed. H1 acceptance also needs the Owner's visual acceptance** (useful arm "
                  "and body posture; helpers follow naturally, no severe distortion).", ""]
    elif out["verdict"] == "SAFE REFUSAL":
        lines += ["**The known Heavy was refused: %s. This is a safe limitation, NOT a compatibility result.**"
                  % out["info"].get("refusal"), ""]
    lines += ["| Gate | Check | Result | Detail |", "|---|---|---|---|"]
    for x in out["checks"]:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False, default=repr)[:300].replace("|", "\\|")
        lines.append("| %s | `%s` | %s | %s |" % (x["gate"], x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    lines += ["", "Info: `%s`" % json.dumps(out["info"], ensure_ascii=False, default=repr)[:600]]
    for f in out["findings"]:
        lines.append("- Finding: %s" % f)
    return "\n".join(lines) + "\n"


def run(c, replay=False):
    """replay: a re-analysis of the same evidence by a corrected analyzer, written beside (never over) the original
    verdict as H1_REPLAY_VERDICT.json/.md, naming the original verdict it follows."""
    R = Report(c)
    limitation = evaluate(R)
    v, gates = verdict(R.checks, limitation)
    out = {"format": "F01-H1-verdict-v1", "verdict": v, "gates": gates, "identities": R.ids, "checks": R.checks,
           "failed": [x["id"] for x in R.checks if not x["pass"]], "info": R.info, "findings": R.findings,
           "analyzer_sha256": sha(os.path.abspath(__file__))}
    stem = "H1_VERDICT"
    if replay:
        stem = "H1_REPLAY_VERDICT"
        out["replay_of_verdict_sha256"] = sha(R.ev("H1_VERDICT.json"))
    md = markdown(out)
    for name, data in ((stem + ".json", json.dumps(out, indent=1, sort_keys=True, default=repr)),
                       (stem + ".md", md)):
        fd = os.open(R.ev(name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(md)
    return 0 if v == "AUTOMATED PASS" else 1


def main(argv):
    if len(argv) not in (2, 3) or (len(argv) == 3 and argv[2] != "--replay"):
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import h1_tool
    return run(h1_tool.S.load(argv[1]), replay=len(argv) == 3)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
