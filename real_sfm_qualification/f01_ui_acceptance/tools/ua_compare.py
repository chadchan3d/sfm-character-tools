# -*- coding: utf-8 -*-
"""F-01 UA-1: the offline comparator for the native UI acceptance check. Python 3, run with -I after restore (SFM
closed). Read-only except for its two verdict files. Its evidence: the capture files (observations/UA-*.json: the
native dialogs' visible content, captured through the window's own handlers and answered as Cancel/Close), the CPM
logs, the library differences kept at restore (evidence/library_cleanup.json, evidence/library_after/), the seeded
records, the restoration records and the session copies.

usage: python -I ua_compare.py UA.json      (or: ua_tool.py UA.json compare)
Writes Q/evidence/UA_VERDICT.json and UA_VERDICT.md (exclusive create). Exit 0 only on "verdict": "PASS".
The Owner's visual observations are recorded beside the verdict; they are never a machine PASS by themselves.
"""
from __future__ import print_function

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S3_TOOLS = os.path.join(HERE, "..", "..", "f01_full_body_s3", "tools")

TITLE = u"Character Preset Manager"
SUMMARY = u"Facial expressions and the rootTransform are not saved."
FIELDS = [u"Name:", u"Type:", u"Model:", u"Model path:", u"Source shot:", u"Source project:", u"Saved:"]
NOT_RECORDED = u"Not recorded"
NOT_INCLUDED_FULL_BODY = u"Facial expressions, rootTransform"
UPDATE_POSE = u'Replace the saved pose "%s" with the character\'s current pose?'
UPDATE_BODY = u'Replace the saved body preset "%s" with the character\'s current body settings?'
UPDATE_EXPRESSION = u'Replace the saved expression "%s" with the character\'s current expression?'
TRASH = {"trash_pose": u'Move the saved pose "%s" to Trash?', "trash_body": u'Move the saved body preset "%s" to Trash?',
         "trash_expression": u'Move the saved expression "%s" to Trash?'}
SELECTABLE = 1 | 2          # Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
POSE, BODY, EXPRESSION = u"UA Pose", u"UA Body", u"UA Expr"
OLD_V2, OLD_V1 = u"K2 Pose", u"NQ1 Pose A"
STEPS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "B1")
SOURCE_DOC, DESTINATION_DOC = u"ua_source.dmx", u"ua_destination.dmx"
BAD_LOG = ("RECOVERY_BLOCKED", "undo-uncertain", "abort-unverified", "P7-unverified", "committed-unverified",
           "recovery-unverified", "abort-failed", "SOURCE-unrecorded")


def read_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def opt_json(path):
    return read_json(path) if os.path.isfile(path) else None


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def escape(text):
    return text.replace(u"&", u"&amp;").replace(u"<", u"&lt;").replace(u">", u"&gt;")


def operations(rows):
    """Every CPM operation: {pid, id, kind, outcome}, in log order."""
    out, current = [], {}
    for r in rows:
        m = re.match(r"PROD_OPERATION_BEGIN id=(\d+) kind=u?'([^']*)'", r["text"])
        if m:
            current[(r["pid"], m.group(1))] = {"pid": r["pid"], "id": m.group(1), "kind": m.group(2), "outcome": None}
            out.append(current[(r["pid"], m.group(1))])
            continue
        m = re.match(r"PROD_OPERATION_RESULT id=(\d+) kind=u?'([^']*)' outcome=u?'([^']*)'", r["text"])
        if m and (r["pid"], m.group(1)) in current:
            current[(r["pid"], m.group(1))]["outcome"] = m.group(3)
    return out


def pose_info(capture):
    """(problems, {field: value}) for a captured Pose Info dialog."""
    problems = []
    dialogs = (capture or {}).get("dialogs") or []
    if (capture or {}).get("error") or len(dialogs) != 1 or dialogs[0].get("title") != u"Pose Info":
        return ["Pose Info was not captured exactly once (%r)" % ((capture or {}).get("error"),)], {}
    d = dialogs[0]
    labels = [l["text"] for l in d["labels"]]
    fields = [t for t in labels if t.endswith(u":")]
    values = dict((labels[i], labels[i + 1] if i + 1 < len(labels) else None)
                  for i in range(len(labels)) if labels[i].endswith(u":"))
    if fields[:7] != FIELDS:
        problems.append("field order %s" % fields[:9])
    rest = fields[7:]
    allowed = [u"Updated:", u"Includes:", u"Not included:", u"Hip position:"]
    if [f for f in rest if f not in allowed] or rest != sorted(rest, key=allowed.index):
        problems.append("fields after Saved %s" % rest)
    if d.get("groups") != [u"Pose", u"Saved Values"] or not d.get("tree_top") or not d.get("tree_children"):
        problems.append("Saved Values tree missing or empty (%s, %s)" % (d.get("groups"), d.get("tree_top")))
    if [b["text"] for b in d["buttons"]] != [u"Close"]:
        problems.append("buttons %s" % [b["text"] for b in d["buttons"]])
    if not values.get(u"Model path:") or values.get(u"Model path:") == u"Unknown":
        problems.append("no model path")
    return problems, values


def message_problems(capture, question, action):
    dialogs = (capture or {}).get("dialogs") or []
    if (capture or {}).get("error") or len(dialogs) != 1:
        return ["not captured exactly once (%r)" % ((capture or {}).get("error"),)]
    d = dialogs[0]
    want = {"kind": "message", "title": TITLE, "text": question, "informative": u"",
            "buttons": [action, u"Cancel"], "default": u"Cancel"}
    return ["%s %r != %r" % (k, d.get(k), v) for k, v in sorted(want.items()) if d.get(k) != v]


def trash_problems(capture, question, folder):
    dialogs = (capture or {}).get("dialogs") or []
    if (capture or {}).get("error") or len(dialogs) != 1:
        return ["not captured exactly once (%r)" % ((capture or {}).get("error"),)]
    d = dialogs[0]
    out = []
    if d.get("title") != TITLE:
        out.append("title %r" % d.get("title"))
    labels = [l["text"] for l in d["labels"]]
    if labels != [u"<b>%s</b>" % escape(question), u"You can recover it from:", folder]:
        out.append("labels %r" % labels)
    path = [l for l in d["labels"] if l["text"] == folder]
    if not path or path[0]["flags"] & SELECTABLE != SELECTABLE or not path[0]["visible"]:
        out.append("recovery folder not visible and selectable %r" % path)
    buttons = dict((b["text"], b) for b in d["buttons"])
    if sorted(buttons) != [u"Cancel", u"Move to Trash"] or not buttons[u"Cancel"]["default"] or \
            buttons[u"Move to Trash"]["default"]:
        out.append("buttons %r" % d["buttons"])
    return out


class Run(object):
    def __init__(self, c):
        self.c, self.q = c, c["paths"]["Q"]
        self.checks, self.findings = [], []
        self.ids = opt_json(os.path.join(self.q, "staged", "IDENTITIES.json")) or {}
        self.cap = {}
        for step in STEPS:
            path = os.path.join(self.q, "observations", "UA-%s.json" % step)
            if os.path.isfile(path):
                self.cap[step] = read_json(path)

    def check(self, cid, ok, detail=None):
        self.checks.append({"id": cid, "pass": bool(ok), "detail": detail})
        return ok

    def ev(self, *parts):
        return os.path.join(self.q, "evidence", *parts)


def evaluate(R):
    chk, cap, c = R.check, R.cap, R.c
    want = c["pins"]["qualification_cpm_sha256"]
    chk("identity.qualification_build", R.ids.get("qualification_cpm_sha256") == want and
        R.ids.get("candidate_cpm_sha256") == c["pins"]["candidate_cpm_sha256"], R.ids.get("qualification_cpm_sha256"))
    for step in STEPS:
        chk("captured.%s" % step, step in cap)
        if step in cap:
            chk("cpm.%s" % step, cap[step].get("cpm_build_sha256") == want, cap[step].get("cpm_build_sha256"))
    if any(s not in cap for s in STEPS):
        chk("complete", False, "missing captures: %s" % [s for s in STEPS if s not in cap])
        return
    a_pids = set(cap[s]["pid"] for s in STEPS if s.startswith("A"))
    chk("process.restart_between_save_and_update", len(a_pids) == 1 and cap["B1"]["pid"] not in a_pids,
        (sorted(a_pids), cap["B1"]["pid"]))
    a_doc, b_doc = cap["A1"].get("document") or u"", cap["B1"].get("document") or u""
    chk("process.sessions", all((cap[s].get("document") or u"") == a_doc for s in STEPS if s.startswith("A")) and
        a_doc.lower().endswith(SOURCE_DOC) and b_doc.lower().endswith(DESTINATION_DOC), (a_doc, b_doc))

    # 6. Older records: readable, usable, "Not recorded"
    for step, name, version in (("A1", OLD_V2, 2), ("A2", OLD_V1, 1)):
        sel = cap[step].get("selected_pose") or {}
        chk("older.%s_selected" % step, sel.get("name") == name and sel.get("version") == version, sel)
        problems, values = pose_info(cap[step]["captures"].get("pose_info"))
        chk("older.%s_pose_info_order_and_tree" % step, not problems, problems)
        chk("older.%s_source_shot_is_the_records" % step, values.get(u"Source shot:") == sel.get("shot_name") and
            bool(sel.get("shot_name")), (values.get(u"Source shot:"), sel.get("shot_name")))
        chk("older.%s_source_project_not_recorded" % step, values.get(u"Source project:") == NOT_RECORDED,
            values.get(u"Source project:"))
        chk("older.%s_apply_enabled" % step,
            (cap[step]["captures"].get("apply_state") or {}).get("apply_button_enabled") is True)
    _, v2 = pose_info(cap["A1"]["captures"].get("pose_info"))
    chk("older.v2_not_included_wording", v2.get(u"Not included:") == NOT_INCLUDED_FULL_BODY, v2.get(u"Not included:"))
    chk("older.v2_updated_record_shows_updated", u"Updated:" in v2, sorted(v2))

    # 1. Save Pose: the approved Full body summary (the real dialog, cancelled)
    sd = cap["A3"]["captures"].get("save_dialog") or {}
    dialogs = sd.get("dialogs") or []
    d = dialogs[0] if len(dialogs) == 1 else {}
    radios = dict((r["text"], r) for r in d.get("radios") or [])
    chk("save.dialog_full_body_summary",
        not sd.get("error") and d.get("title") == u"Save Pose" and (radios.get(u"Full body") or {}).get("checked") and
        any(l["text"] == SUMMARY and l["visible"] for l in d.get("labels") or []) and
        any(b["text"] == u"Save" and b["enabled"] for b in d.get("buttons") or []),
        {"title": d.get("title"), "radios": d.get("radios"), "labels": [l["text"] for l in d.get("labels") or []],
         "error": sd.get("error")})

    # 2. Pose Info of the new pose: order, source shot, source project = the session
    sel = cap["A4"].get("selected_pose") or {}
    chk("new.selected", sel.get("name") == POSE and sel.get("version") == 2 and sel.get("regions") == [u"full_body"], sel)
    problems, va = pose_info(cap["A4"]["captures"].get("pose_info"))
    chk("new.pose_info_order_and_tree", not problems, problems)
    chk("new.source_shot", va.get(u"Source shot:") == u"shot15" == sel.get("shot_name"), va.get(u"Source shot:"))
    chk("new.source_project_is_the_session", va.get(u"Source project:") == a_doc and bool(a_doc),
        (va.get(u"Source project:"), a_doc))
    chk("new.not_updated", u"Updated:" not in va, sorted(va))
    chk("new.not_included_wording", va.get(u"Not included:") == NOT_INCLUDED_FULL_BODY, va.get(u"Not included:"))

    # 3. Update Pose: the one-question confirmation; after the Owner's update, the new source
    for step in ("A4", "B1"):
        p = message_problems(cap[step]["captures"].get("update_pose"), UPDATE_POSE % POSE, u"Update Pose")
        chk("update.%s_confirmation" % step, not p, p)
    selb = cap["B1"].get("selected_pose") or {}
    problems, vb = pose_info(cap["B1"]["captures"].get("pose_info"))
    chk("update.same_pose", selb.get("preset_id") == sel.get("preset_id") and selb.get("name") == POSE, selb)
    chk("update.pose_info_order_and_tree", not problems, problems)
    chk("update.source_shot_is_the_updated_one", vb.get(u"Source shot:") == u"shot13" == selb.get("shot_name"),
        vb.get(u"Source shot:"))
    chk("update.source_project_is_the_updating_session", vb.get(u"Source project:") == b_doc and bool(b_doc),
        (vb.get(u"Source project:"), b_doc))
    chk("update.updated_row", u"Updated:" in vb, sorted(vb))

    # 4. and 5. Body Preset and Expression confirmations; Trash dialogs
    for step, kind, name, question in (("A5", "body", BODY, UPDATE_BODY), ("A6", "expression", EXPRESSION,
                                                                          UPDATE_EXPRESSION)):
        u_cap = cap[step]["captures"].get("update_%s" % kind) or {}
        chk("preset.%s_selected" % kind, u_cap.get("selected_preset") == name, u_cap.get("selected_preset"))
        p = message_problems(u_cap, question % name, u"Update Preset")
        chk("preset.%s_update_confirmation" % kind, not p, p)
        t_cap = cap[step]["captures"].get("trash_%s" % kind)
        p = trash_problems(t_cap, TRASH["trash_%s" % kind] % name, cap[step].get("trash_folder"))
        chk("trash.%s_dialog" % kind, not p, p)
    p = trash_problems(cap["A4"]["captures"].get("trash_pose"), TRASH["trash_pose"] % POSE, cap["A4"].get("trash_folder"))
    chk("trash.pose_dialog", not p, p)
    folder = cap["A4"].get("trash_folder") or u""
    chk("trash.folder_is_the_library_trash", folder.replace(u"\\", u"/").lower().endswith(
        u"/sfm character preset manager/trash"), folder)
    chk("trash.recovery_folder_copies", (cap["A7"].get("clipboard") or u"").strip() == folder and bool(folder),
        (cap["A7"].get("clipboard"), folder))

    # Logs: what was written, cancellations, recovery
    if S3_TOOLS not in sys.path:
        sys.path.insert(0, S3_TOOLS)
    import s3_compare as S3C  # the CPM log parser (Python 3)
    logs = os.path.join(R.q, "evidence", "logs")
    rows = S3C.parse_logs(logs) if os.path.isdir(logs) else []
    ops = operations(rows)
    a_pid, b_pid = list(a_pids)[0], cap["B1"]["pid"]
    written = [(o["pid"] == a_pid and "A" or o["pid"] == b_pid and "B" or "?", o["kind"]) for o in ops
               if o["outcome"] not in ("no-op", "completed")]
    chk("log.only_the_owners_saves_and_one_update_were_written",
        sorted(written) == sorted([("A", "Save Pose"), ("A", "Save Current Body"), ("A", "Save Current Expression"),
                                   ("B", "Update Pose")]) and
        all(o["outcome"] == "verified" for o in ops if o["outcome"] not in ("no-op", "completed")),
        [(o["pid"], o["kind"], o["outcome"]) for o in ops])
    # The captures cancel at least these; the Owner's own Cancel clicks add more of the same kinds, never others.
    cancelled = [o["kind"] for o in ops if o["outcome"] == "no-op"]
    required = {u"Save Pose": 1, u"Update Pose": 2, u"Delete Pose": 1, u"Update Preset": 2, u"Delete Preset": 2}
    chk("log.every_captured_dialog_ended_cancelled",
        all(cancelled.count(k) >= n for k, n in required.items()) and set(cancelled) <= set(required),
        sorted(cancelled))
    chk("log.source_recorded_on_save_and_update",
        sum(1 for r in rows if r["text"].startswith("PROD_POSE_SOURCE-recorded")) == 2,
        [r["text"][:80] for r in rows if "SOURCE-" in r["text"]])
    chk("log.no_apply", not [o for o in ops if o["kind"] == "Apply Pose"])
    chk("log.no_recovery_uncertainty_or_unrecorded_source", not any(b in r["text"] for r in rows for b in BAD_LOG),
        sorted(set(b for r in rows for b in BAD_LOG if b in r["text"])))

    # The library as the run left it (kept at restore), then restored
    clean = opt_json(R.ev("library_cleanup.json")) or {}
    diffs = clean.get("differences_kept_in_evidence") or []
    char = "Characters/%s/" % c["character_dir"]
    removed = [x["path"] for x in diffs if x["status"] == "removed"]
    chk("library.nothing_existing_was_removed", not removed, removed)
    trash = [x["path"] for x in diffs if x["path"].startswith("Trash/")]
    chk("library.nothing_moved_to_trash", not trash, trash)
    sources_path = R.ev("library_after", *(char + "pose_sources.json").split("/"))
    sources = opt_json(sources_path) or {}
    entries = sources.get("entries") or {}
    chk("library.source_sidecar_holds_only_the_new_pose_with_the_updating_session",
        sources.get("record_kind") == "cpm-pose-sources" and sources.get("schema_version") == 1 and
        entries == {sel.get("preset_id"): {"project": b_doc}}, entries)
    seed = opt_json(R.ev("seed.json")) or {}
    final = dict((x["path"], x["sha256"]) for x in diffs if x["status"] != "removed")
    chk("library.older_records_unchanged",
        all(final.get(char + "Poses/" + n) == h for n, h in (seed.get("files") or {}).items()) and
        len(seed.get("files") or {}) == 2, seed.get("files"))
    ua = [x["path"] for x in diffs if x["path"].startswith(char + "Poses/" + POSE + "--") and
          x["path"].endswith(".json")]
    raw = b""
    if len(ua) == 1 and os.path.isfile(R.ev("library_after", *ua[0].split("/"))):
        with open(R.ev("library_after", *ua[0].split("/")), "rb") as f:
            raw = f.read()
    chk("library.pose_record_carries_no_project_path",
        bool(raw) and b".dmx" not in raw.lower() and b"pose_sources" not in raw, ua)
    changed = [x["path"] for x in diffs if x["status"] == "changed"]
    if changed:
        R.findings.append("existing library files changed during the run and restored from the backup: %s" % changed)

    # Restoration and sessions
    restore = opt_json(R.ev("restore.json")) or {}
    chk("restore.library_exactly_as_before", clean.get("files_equal_pre") is True and
        clean.get("folders_equal_pre") is True, {k: clean.get(k) for k in ("files_equal_pre", "folders_equal_pre",
                                                                          "removed_run_folders", "recreated_folders")})
    chk("restore.published_and_inventories_equal", restore.get("restored") is True, restore.get("inventory_problems"))
    sessions = os.path.join(R.q, "sessions")
    chk("sessions.never_saved",
        os.path.isfile(os.path.join(sessions, "UA_SOURCE.dmx")) and
        sha(os.path.join(sessions, "UA_SOURCE.dmx")) == c["pins"]["r2_fixture_sha256"] and
        os.path.isfile(os.path.join(sessions, "UA_DESTINATION.dmx")) and
        sha(os.path.join(sessions, "UA_DESTINATION.dmx")) == c["pins"]["destination_sha256"])


def markdown(out):
    lines = ["# F-01 UA-1 native UI acceptance verdict: %s" % out["verdict"], "",
             "Qualification CPM `%s` (candidate `%s`)." % (out["identities"].get("qualification_cpm_sha256"),
                                                          out["identities"].get("candidate_cpm_sha256")), "",
             "| Check | Result | Detail |", "|---|---|---|"]
    for x in out["checks"]:
        detail = "" if x["pass"] else json.dumps(x["detail"], ensure_ascii=False)[:300].replace("|", "\\|")
        lines.append("| `%s` | %s | %s |" % (x["id"], "PASS" if x["pass"] else "**FAIL**", detail))
    if out["findings"]:
        lines += ["", "Findings (not failures):"] + ["- %s" % f for f in out["findings"]]
    lines += ["", "The Owner's visual observations are recorded separately; they are not machine checks."]
    return "\n".join(lines) + "\n"


def run(c):
    R = Run(c)
    evaluate(R)
    failed = [x["id"] for x in R.checks if not x["pass"]]
    out = {"format": "F01-UA1-verdict-v1", "verdict": "PASS" if not failed else "FAIL", "identities": R.ids,
           "checks": R.checks, "failed": failed, "findings": R.findings}
    for name, data in (("UA_VERDICT.json", json.dumps(out, indent=1, sort_keys=True)), ("UA_VERDICT.md", markdown(out))):
        fd = os.open(R.ev(name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
    print(markdown(out))
    return 0 if not failed else 1


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    sys.path.insert(0, HERE)
    import ua_tool
    return run(ua_tool.S.load(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
