# -*- coding: ascii -*-
"""Offline tests of the F-01 UA-1 native UI acceptance kit (Python 3).

- ua_tool: build derives exactly the pinned UA-1 qualification CPM (ea670f51...) from the committed candidate
  (8eccf172..., read from commit d3d23d1) in one line, and refuses a wrong pin or a changed capture script; the
  library backup and cleanup put a preset library back exactly (added, changed and removed files; folders the run
  created are removed, folders that existed at pre, including empty ones, are kept or recreated: PS2-D1).
- ua_compare: a complete synthetic run is PASS; each counterexample is FAIL on its own check.
The capture script's dialog capture on the candidate's real dialogs is tested on SFM's Python 2.7 (test_ua_capture.py).
They show nothing about SFM.

Run: python -I test_ua.py
"""
import copy
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RSQ = os.path.dirname(ROOT)
REPO = os.path.dirname(RSQ)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ua_tool as TOOL  # noqa: E402
import ua_compare as C  # noqa: E402

CANDIDATE_COMMIT = "d3d23d1"
QUAL = "ea670f51d13b295c59f51047fc029da512d523528482889f0c0d9835700afa6f"
_CANDIDATE = []


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def candidate():
    """The committed candidate's exact bytes (commit d3d23d1), in a private temporary folder."""
    if not _CANDIDATE:
        import atexit
        import subprocess
        raw = subprocess.check_output(["git", "-C", REPO, "cat-file", "blob",
                                       "%s:cpm/app/SFM_Character_Preset_Manager.py" % CANDIDATE_COMMIT])
        where = tempfile.mkdtemp(prefix="uacand")
        atexit.register(shutil.rmtree, where, True)
        path = os.path.join(where, "SFM_Character_Preset_Manager.py")
        with open(path, "wb") as f:
            f.write(raw)
        _CANDIDATE.append(path)
    return _CANDIDATE[0]


def load(path):
    with io.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def quiet(fn):
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return fn()
    finally:
        sys.stdout = saved


def config(folder, pins=None, **paths):
    with open(os.path.join(ROOT, "ua.template.json"), "rb") as f:
        c = json.loads(f.read().decode("utf-8"))
    for d in ("game", "sessions", "library", "logs", "Q"):
        os.makedirs(os.path.join(folder, d), exist_ok=True)
    c["paths"].update(Q=os.path.join(folder, "Q"), REPO=REPO, GAME=os.path.join(folder, "game"),
                      SESSIONS=os.path.join(folder, "sessions"), LIBRARY=os.path.join(folder, "library"),
                      R2_FIXTURE=os.path.join(folder, "fixture.dmx"), S3_RUN1=os.path.join(folder, "s3run"),
                      LOG_DIR=os.path.join(folder, "logs"), LEGACY_POSE=os.path.join(folder, "legacy.json"),
                      K2_POSE=os.path.join(folder, "k2.json"), CANDIDATE=candidate())
    c["paths"].update(paths)
    c["pins"]["capture_sha256"] = TOOL.T.sha(os.path.join(ROOT, "observer", "F01_UA_Capture.py"))
    c["pins"].update(pins or {})
    path = os.path.join(folder, "ua.json")
    with open(path, "wb") as f:
        f.write(json.dumps(c).encode("utf-8"))
    return path


def write(path, data):
    if not os.path.isdir(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, "wb") as f:
        f.write(data)


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="uatool")

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def test_build_derives_the_pinned_ua1_qualification_build_in_one_line(self):
        c = TOOL.S.load(config(self.dir))
        quiet(lambda: TOOL.cmd_build(c))
        ids = load(os.path.join(self.dir, "Q", "staged", "IDENTITIES.json"))
        self.assertEqual((ids["candidate_cpm_sha256"], ids["qualification_cpm_sha256"], ids["changed_line"], ids["line"]),
                         ("8eccf1723fef395fcf0678ea25c0dbdf145ba77d1558ca318887aa6cfe057194", QUAL, 42220,
                          u'PROD_POSE_REGISTRY_MODE = u"qualification"'))

    def test_build_refuses_a_wrong_pin_or_a_changed_capture_script(self):
        for pins in ({"qualification_cpm_sha256": "0" * 64}, {"capture_sha256": "0" * 64}):
            folder = tempfile.mkdtemp(prefix="uapin", dir=self.dir)
            c = TOOL.S.load(config(folder, pins))
            self.assertRaises(SystemExit, quiet, lambda: TOOL.cmd_build(c))
            self.assertFalse(os.path.exists(os.path.join(folder, "Q", "staged")))

    def test_the_template_refuses_until_filled_and_the_kit_identity(self):
        self.assertRaises(SystemExit, TOOL.S.load, os.path.join(ROOT, "ua.template.json"))
        self.assertEqual((TOOL.S.FORMAT, TOOL.S.SESSIONS, TOOL.S.DESTINATION),
                         ("F01-UA1-config-v1", ("UA_SOURCE.dmx",), "UA_DESTINATION.dmx"))

    def test_library_backup_and_cleanup_restore_the_library_exactly_and_keep_empty_folders(self):
        c = TOOL.S.load(config(self.dir))
        lib = os.path.join(self.dir, "library")
        char = os.path.join(lib, "Characters", "krystal2020--7d2aee52ef3a")
        write(os.path.join(char, "character.json"), b"original character")
        write(os.path.join(char, "Body Presets", "Mine.json"), b"a real preset")
        write(os.path.join(char, "Expressions", "Smile.json"), b"a real expression")
        os.makedirs(os.path.join(lib, "_Qualification"))                  # pre-existing EMPTY folder (PS2-D1)
        os.makedirs(os.path.join(self.dir, "Q", "pre_run"))
        with open(os.path.join(self.dir, "Q", "pre_run", "inventory_LIBRARY.txt"), "w") as f:
            f.write("\n".join(TOOL.T.inventory(lib)["rows"]) + "\n")
        before = TOOL.T.inventory(lib)["sha256"]
        quiet(lambda: TOOL.backup_library(c))
        # The run: a Poses folder and records, the source sidecar, new presets, a changed and a removed file, a Trash
        # entry, and the pre-existing empty folder deleted.
        write(os.path.join(char, "Poses", "UA Pose--abc.json"), b"pose")
        write(os.path.join(char, "pose_sources.json"), b"{}")
        write(os.path.join(char, "Body Presets", "UA Body.json"), b"new preset")
        write(os.path.join(char, "character.json"), b"display name rewritten")
        os.remove(os.path.join(char, "Expressions", "Smile.json"))
        write(os.path.join(lib, "Trash", "x--UA Pose--abc.json"), b"pose")
        os.rmdir(os.path.join(lib, "_Qualification"))
        os.makedirs(os.path.join(self.dir, "Q", "evidence"))
        result = TOOL.cleanup_library(c)
        self.assertTrue(result["files_equal_pre"] and result["folders_equal_pre"], result)
        self.assertEqual(TOOL.T.inventory(lib)["sha256"], before)
        self.assertTrue(os.path.isdir(os.path.join(lib, "_Qualification")))
        self.assertEqual(result["recreated_folders"], ["_Qualification"])
        self.assertFalse(os.path.exists(os.path.join(char, "Poses")) or os.path.exists(os.path.join(lib, "Trash")))
        kept = os.path.join(self.dir, "Q", "evidence", "library_after", "Characters", "krystal2020--7d2aee52ef3a")
        with open(os.path.join(kept, "character.json"), "rb") as f:
            self.assertEqual(f.read(), b"display name rewritten")
        self.assertTrue(os.path.isfile(os.path.join(kept, "pose_sources.json")))
        statuses = sorted((x["status"], x["path"]) for x in result["differences_kept_in_evidence"])
        self.assertIn(("removed", "Characters/krystal2020--7d2aee52ef3a/Expressions/Smile.json"), statuses)
        self.assertIn(("changed", "Characters/krystal2020--7d2aee52ef3a/character.json"), statuses)


# --- the comparator on a synthetic run -------------------------------------------------------------------------------

CHAR = "krystal2020--7d2aee52ef3a"
UA_ID = "u" * 32
SRC_DOC = u"e:\\sfm_u0b_scratch\\ua\\sessions\\ua_source.dmx"
DST_DOC = u"e:\\sfm_u0b_scratch\\ua\\sessions\\ua_destination.dmx"
TRASH = u"C:\\Users\\<owner>\\Documents\\SFM Character Preset Manager\\Trash"


def info(fields, tree=(u"Saved controls (278)",)):
    labels = []
    for k, v in fields:
        labels += [{"text": k, "flags": 1, "visible": True}, {"text": v, "flags": 1, "visible": True}]
    return {"dialogs": [{"kind": "dialog", "class": "QDialog", "title": u"Pose Info", "labels": labels, "radios": [],
                         "checks": [], "buttons": [{"text": u"Close", "enabled": True, "default": False}],
                         "groups": [u"Pose", u"Saved Values"], "tree_top": list(tree), "tree_children": 5}],
            "error": None}


def pose_fields(name, kind, shot, project, updated, not_included=u"Facial expressions, rootTransform"):
    out = [(u"Name:", name), (u"Type:", kind), (u"Model:", u"krystal2020.mdl"),
           (u"Model path:", u"models/fursonas/starfox/krystal/bodies/krystal2020.mdl"), (u"Source shot:", shot),
           (u"Source project:", project), (u"Saved:", u"November 14, 2026")]
    if updated:
        out.append((u"Updated:", u"November 14, 2026"))
    if not_included:
        out.append((u"Not included:", not_included))
    return out


def message(question, action):
    return {"dialogs": [{"kind": "message", "class": "QMessageBox", "title": C.TITLE, "text": question,
                         "informative": u"", "text_format": 0, "buttons": [action, u"Cancel"], "default": u"Cancel"}],
            "error": None}


def trash(question, folder=TRASH, flags=3):
    return {"dialogs": [{"kind": "dialog", "class": "QDialog", "title": C.TITLE,
                         "labels": [{"text": u"<b>%s</b>" % C.escape(question), "flags": 0, "visible": True},
                                    {"text": u"You can recover it from:", "flags": 0, "visible": True},
                                    {"text": folder, "flags": flags, "visible": True}],
                         "radios": [], "checks": [], "groups": [], "tree_top": None, "tree_children": None,
                         "buttons": [{"text": u"Move to Trash", "enabled": True, "default": False},
                                     {"text": u"Cancel", "enabled": True, "default": True}]}],
            "error": None}


class UASynthetic(object):
    def __init__(self, folder, faults=()):
        self.q, self.f = folder, set(faults)
        for d in ("staged", "observations", "evidence", "sessions", os.path.join("evidence", "logs")):
            os.makedirs(os.path.join(folder, d))

    def dump(self, rel, data):
        write(os.path.join(self.q, rel), json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))

    def capture(self, step, pid, doc, selected, captures, **extra):
        data = {"format": "F01-UA1-capture-v1", "step": step, "pid": pid, "cpm_build_sha256": QUAL, "document": doc,
                "clipboard": extra.get("clipboard", u""), "selected_pose": selected, "trash_folder": TRASH,
                "captures": captures}
        self.dump(os.path.join("observations", "UA-%s.json" % step), data)

    def build(self):
        f = self.f
        self.dump(os.path.join("staged", "IDENTITIES.json"), {"qualification_cpm_sha256": QUAL,
                                                              "candidate_cpm_sha256": TOOL_PIN})
        k2 = {"name": u"K2 Pose", "preset_id": "k" * 32, "version": 2, "regions": [u"full_body"], "shot_name": u"shot13"}
        v1 = {"name": u"NQ1 Pose A", "preset_id": "n" * 32, "version": 1, "regions": [u"left_arm"],
              "shot_name": u"shot10"}
        ua_a = {"name": u"UA Pose", "preset_id": UA_ID, "version": 2, "regions": [u"full_body"], "shot_name": u"shot15"}
        ua_b = dict(ua_a, shot_name=u"shot13")
        self.capture("A1", 100, SRC_DOC, k2, {
            "pose_info": info(pose_fields(u"K2 Pose", u"Full body", u"shot13", u"Not recorded", True)),
            "apply_state": {"apply_button_enabled": True}})
        a2 = pose_fields(u"NQ1 Pose A", u"Left arm", u"shot10",
                         SRC_DOC if "old-project-shown" in f else u"Not recorded", True, None)
        self.capture("A2", 100, SRC_DOC, v1, {"pose_info": info(a2),
                                              "apply_state": {"apply_button_enabled": "old-unusable" not in f}})
        summary = u"Facial expressions, gaze and the character's place in the scene are not saved." \
            if "old-summary" in f else C.SUMMARY
        self.capture("A3", 100, SRC_DOC, k2, {"save_dialog": {"dialogs": [{
            "kind": "dialog", "class": "QDialog", "title": u"Save Pose",
            "labels": [{"text": u"Name:", "flags": 0, "visible": True},
                       {"text": summary, "flags": 0, "visible": True}],
            "radios": [{"text": u"Full body", "checked": True, "enabled": True},
                       {"text": u"Selected parts", "checked": False, "enabled": True}],
            "checks": [], "groups": [], "tree_top": None, "tree_children": None,
            "buttons": [{"text": u"Save", "enabled": True, "default": True},
                        {"text": u"Cancel", "enabled": True, "default": False}]}], "error": None}})
        new = pose_fields(u"UA Pose", u"Full body", u"shot15", SRC_DOC, False)
        if "order" in f:
            new[4], new[6] = new[6], new[4]
        self.capture("A4", 100, SRC_DOC, ua_a, {
            "pose_info": info(new),
            "update_pose": message(C.UPDATE_POSE % u"UA Pose" if "update-wording" not in f else
                                   u'Update "UA Pose" using the current pose?', u"Update Pose"),
            "trash_pose": trash(C.TRASH["trash_pose"] % u"UA Pose", flags=0 if "path-not-selectable" in f else 3)})
        trash_body = dict(trash(C.TRASH["trash_body"] % u"UA Body"), selected_preset=u"UA Body")
        if "a5-message-box" in f:     # UA-1 run 1: CPM's error box where the Trash dialog was expected
            trash_body = {"dialogs": [{"kind": "message", "class": "QMessageBox", "title": u"Can't delete preset",
                                       "text": u"Preset could not be moved to Trash. Try again.", "informative": u"",
                                       "text_format": 0, "buttons": [u"OK"], "default": None}],
                          "error": None, "selected_preset": u"unreadable: Select a preset first."}
        self.capture("A5", 100, SRC_DOC, ua_a, {
            "update_body": dict(message(C.UPDATE_BODY % u"UA Body", u"Update Preset"), selected_preset=u"UA Body"),
            "trash_body": trash_body})
        if "malformed-a2" in f:
            write(os.path.join(self.q, "observations", "UA-A2.json"), b'{"step": "A2"}')
        self.capture("A6", 100, SRC_DOC, ua_a, {
            "update_expression": dict(message(C.UPDATE_EXPRESSION % u"UA Expr", u"Update Preset"),
                                      selected_preset=u"UA Expr"),
            "trash_expression": dict(trash(C.TRASH["trash_expression"] % u"UA Expr"), selected_preset=u"UA Expr")})
        self.capture("A7", 100, SRC_DOC, ua_a, {}, clipboard=u"elsewhere" if "clipboard" in f else TRASH + u"\n")
        if "no-b1" not in f:
            self.capture("B1", 100 if "no-restart" in f else 200, DST_DOC, ua_b, {
                "pose_info": info(pose_fields(u"UA Pose", u"Full body", u"shot13",
                                              SRC_DOC if "update-kept-project" in f else DST_DOC, True)),
                "update_pose": message(C.UPDATE_POSE % u"UA Pose", u"Update Pose")})
        # CPM logs
        ops = {100: [("Save Pose", "no-op"), ("Save Pose", "verified"), ("Pose Info", "completed"),
                     ("Update Pose", "no-op"), ("Delete Pose", "no-op"), ("Save Current Body", "verified"),
                     ("Update Preset", "no-op"), ("Delete Preset", "no-op"), ("Save Current Expression", "verified"),
                     ("Update Preset", "no-op"), ("Delete Preset", "no-op"), ("Delete Preset", "no-op")],
               200: [("Pose Info", "completed"), ("Update Pose", "no-op"), ("Update Pose", "verified")]}
        if "trashed" in f:
            ops[100].append(("Delete Pose", "verified"))
        extra = {100: ["PROD_POSE_SOURCE-recorded {}"], 200: ["PROD_POSE_SOURCE-recorded {}"]}
        for pid, rows in ops.items():
            lines, n = [], 0
            for i, (kind, outcome) in enumerate(rows, 1):
                texts = ["PROD_OPERATION_BEGIN id=%d kind=u'%s' context=None" % (i, kind)]
                if kind in ("Save Pose", "Update Pose") and outcome == "verified":
                    texts += extra[pid]
                texts.append("PROD_OPERATION_RESULT id=%d kind=u'%s' outcome=u'%s'" % (i, kind, outcome))
                for t in texts:
                    n += 1
                    lines.append("2026-11-14T10:%02d:%02d.000Z #%06d s=x w=1 op=%d | %s" % (n // 60, n % 60, n, i, t))
            write(os.path.join(self.q, "evidence", "logs", "CPM - 2026-11-14_10-00-00Z - pid%d - x - 001.log" % pid),
                  ("\n".join(lines) + "\n").encode("utf-8"))
        # The library as the run left it, and its restoration
        base = "Characters/%s/" % CHAR
        record = json.dumps({"name": "UA Pose", "pose": {"source": {"shot_name": "shot13"}}})
        if "project-in-record" in f:
            record = record.replace("shot13", SRC_DOC.replace("\\", "/"))
        sources = {"schema_version": 1, "record_kind": "cpm-pose-sources",
                   "entries": {UA_ID: {"project": SRC_DOC if "sidecar-stale" in f else DST_DOC}}}
        files = {base + "Poses/K2 Pose--ac9d4962a2ae.json": b"k2", base + "Poses/NQ1 Pose A--5273df2209ca.json": b"v1",
                 base + "Poses/UA Pose--uuuuuuuuuuuu.json": record.encode("utf-8"),
                 base + "pose_sources.json": json.dumps(sources).encode("utf-8"),
                 base + "Body Presets/UA Body.json": b"b", base + "Expressions/UA Expr.json": b"e"}
        diffs = []
        for rel, data in sorted(files.items()):
            write(os.path.join(self.q, "evidence", "library_after", *rel.split("/")), data)
            diffs.append({"status": "added", "path": rel, "sha256": sha_bytes(data)})
        if "trashed" in f:
            diffs.append({"status": "added", "path": "Trash/x--UA Pose.json", "sha256": "t"})
        self.dump(os.path.join("evidence", "library_cleanup.json"), {
            "differences_kept_in_evidence": diffs, "files_equal_pre": True,
            "folders_equal_pre": "folder-left" not in f, "removed_run_folders": [], "recreated_folders": []})
        self.dump(os.path.join("evidence", "seed.json"), {"files": {
            "K2 Pose--ac9d4962a2ae.json": sha_bytes(b"k2"),
            "NQ1 Pose A--5273df2209ca.json": sha_bytes(b"v1" if "old-changed" not in f else b"v0")}})
        self.dump(os.path.join("evidence", "restore.json"), {"restored": True, "inventory_problems": []})
        write(os.path.join(self.q, "sessions", "UA_SOURCE.dmx"), b"src")
        write(os.path.join(self.q, "sessions", "UA_DESTINATION.dmx"), b"dst" if "session-saved" not in f else b"x")
        return {"paths": {"Q": self.q}, "character_dir": CHAR,
                "pins": {"qualification_cpm_sha256": QUAL, "candidate_cpm_sha256": TOOL_PIN,
                         "r2_fixture_sha256": sha_bytes(b"src"), "destination_sha256": sha_bytes(b"dst")}}


TOOL_PIN = "8eccf1723fef395fcf0678ea25c0dbdf145ba77d1558ca318887aa6cfe057194"


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="uacmp")

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def verdict(self, *faults):
        q = os.path.join(self.dir, "Q%d" % len(os.listdir(self.dir)))
        c = UASynthetic(q, faults).build()
        code = quiet(lambda: C.run(c))
        out = load(os.path.join(q, "evidence", "UA_VERDICT.json"))
        self.assertEqual(code == 0, out["verdict"] == "PASS")
        return out

    def test_a_complete_correct_run_passes(self):
        out = self.verdict()
        self.assertEqual((out["verdict"], out["failed"]), ("PASS", []), out["failed"])

    def test_counterexamples_fail_on_their_own_check(self):
        cases = {"old-summary": "save.dialog_full_body_summary",
                 "order": "new.pose_info_order_and_tree",
                 "update-wording": "update.A4_confirmation",
                 "path-not-selectable": "trash.pose_dialog",
                 "clipboard": "trash.recovery_folder_copies",
                 "update-kept-project": "update.source_project_is_the_updating_session",
                 "old-project-shown": "older.A2_source_project_not_recorded",
                 "old-unusable": "older.A2_apply_enabled",
                 "project-in-record": "library.pose_record_carries_no_project_path",
                 "sidecar-stale": "library.source_sidecar_holds_only_the_new_pose_with_the_updating_session",
                 "trashed": "library.nothing_moved_to_trash",
                 "old-changed": "library.older_records_unchanged",
                 "folder-left": "restore.library_exactly_as_before",
                 "session-saved": "sessions.never_saved",
                 "no-restart": "process.restart_between_save_and_update",
                 "no-b1": "captured.B1"}
        for fault, check in sorted(cases.items()):
            out = self.verdict(fault)
            self.assertEqual(out["verdict"], "FAIL", fault)
            self.assertIn(check, out["failed"], (fault, out["failed"]))

    def test_the_trashed_case_also_fails_the_write_check(self):
        out = self.verdict("trashed")
        self.assertIn("log.only_the_owners_saves_and_one_update_were_written", out["failed"])

    # --- kit correction after UA-1 run 1: wrong or missing captures are explicit failures, never exceptions ---------

    def test_a_message_box_where_a_trash_dialog_was_expected_fails_without_an_exception(self):
        out = self.verdict("a5-message-box")       # the exact shape that raised KeyError in UA-1 run 1
        self.assertEqual(out["verdict"], "FAIL")
        self.assertIn("trash.body_dialog", out["failed"])
        detail = [x for x in out["checks"] if x["id"] == "trash.body_dialog"][0]["detail"]
        self.assertTrue(any("message was captured where a dialog was expected" in d for d in detail), detail)

    def test_a_malformed_capture_file_is_not_captured_without_an_exception(self):
        out = self.verdict("malformed-a2")
        self.assertIn("captured.A2", out["failed"])

    def test_every_dialog_reader_reports_missing_or_wrong_captures(self):
        good_msg = message(C.UPDATE_POSE % u"P", u"Update Pose")
        good_trash = trash(C.TRASH["trash_pose"] % u"P")
        good_info = info(pose_fields(u"P", u"Full body", u"shot15", u"Not recorded", False))
        msg_dialog = good_msg["dialogs"][0]
        trash_dialog = good_trash["dialogs"][0]
        wrong = {
            "missing": None,
            "error": {"dialogs": [], "error": u"RuntimeError: boom"},
            "none": {"dialogs": [], "error": None},
            "two": {"dialogs": [trash_dialog, trash_dialog], "error": None},
            "not a list": {"dialogs": "x", "error": None},
            "no labels": {"dialogs": [dict(trash_dialog, labels=None)], "error": None},
            "label without text": {"dialogs": [dict(trash_dialog, labels=[{"flags": 3}])], "error": None},
            "button without text": {"dialogs": [dict(trash_dialog, buttons=[{"default": True}])], "error": None},
        }
        self.assertEqual(C.message_problems(good_msg, C.UPDATE_POSE % u"P", u"Update Pose"), [])
        self.assertEqual(C.trash_problems(good_trash, C.TRASH["trash_pose"] % u"P", TRASH), [])
        self.assertEqual(C.pose_info(good_info)[0], [])
        for name, cap in sorted(wrong.items()):
            self.assertTrue(C.trash_problems(cap, C.TRASH["trash_pose"] % u"P", TRASH), name)
            self.assertTrue(C.pose_info(cap)[0], name)
        self.assertTrue(C.message_problems({"dialogs": [trash_dialog], "error": None}, u"q", u"Update Pose"))
        self.assertTrue(C.trash_problems({"dialogs": [msg_dialog], "error": None}, u"q", TRASH))
        self.assertTrue(C.pose_info({"dialogs": [msg_dialog], "error": None})[0])
        for name in ("missing", "error", "none", "two", "not a list"):
            self.assertTrue(C.message_problems(wrong[name], C.UPDATE_POSE % u"P", u"Update Pose"), name)

    def test_replay_writes_separate_files_and_changes_no_evidence(self):
        q = os.path.join(self.dir, "R")
        c = UASynthetic(q, ("a5-message-box",)).build()
        before = dict((n, TOOL.T.sha(os.path.join(q, "observations", n))) for n in os.listdir(os.path.join(
            q, "observations")))
        code = quiet(lambda: C.run(c, "replay"))
        out = load(os.path.join(q, "evidence", "UA_VERDICT_REPLAY.json"))
        self.assertEqual((code, out["verdict"]), (1, "FAIL"))
        self.assertEqual(out["replay_of"], dict((n, h) for n, h in before.items() if n.startswith("UA-")))
        self.assertFalse(os.path.exists(os.path.join(q, "evidence", "UA_VERDICT.json")))
        self.assertEqual(before, dict((n, TOOL.T.sha(os.path.join(q, "observations", n))) for n in before))
        self.assertRaises(OSError, quiet, lambda: C.run(c, "replay"))


# --- UA-1S, the supplemental preset-confirmation check ---------------------------------------------------------------

class SupplementSynthetic(object):
    def __init__(self, folder, faults=()):
        self.q, self.f = folder, set(faults)
        for d in ("staged", "observations", "evidence", "sessions", os.path.join("evidence", "logs")):
            os.makedirs(os.path.join(folder, d))

    def dump(self, rel, data):
        write(os.path.join(self.q, rel), json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))

    def capture(self, step, captures, **extra):
        self.dump(os.path.join("observations", "UA-%s.json" % step), {
            "format": "F01-UA1-capture-v1", "step": step, "pid": 300, "cpm_build_sha256": SUP_QUAL,
            "document": SRC_DOC, "clipboard": extra.get("clipboard", u""), "selected_pose": None,
            "trash_folder": TRASH, "captures": captures})

    def build(self):
        f = self.f
        self.dump(os.path.join("staged", "IDENTITIES.json"), {"qualification_cpm_sha256": SUP_QUAL,
                                                              "candidate_cpm_sha256": SUP_PIN})
        body_title = u"Update preset?" if "old-title" in f else C.TITLE
        self.capture("A5", {
            "update_body": dict(message(C.UPDATE_BODY % u"UA Body", u"Update Preset"), selected_preset=u"UA Body"),
            "trash_body": dict(trash(C.TRASH["trash_body"] % u"UA Body"), selected_preset=u"UA Body")})
        if "old-title" in f:
            path = os.path.join(self.q, "observations", "UA-A5.json")
            d = load(path)
            d["captures"]["update_body"]["dialogs"][0]["title"] = body_title
            write(path, json.dumps(d).encode("utf-8"))
        if "a6-message-box" in f:
            expr_trash = {"dialogs": [{"kind": "message", "title": u"Can't delete preset", "text": u"x",
                                       "informative": u"", "buttons": [u"OK"], "default": None}], "error": None,
                          "selected_preset": u"UA Expr"}
        else:
            expr_trash = dict(trash(C.TRASH["trash_expression"] % u"UA Expr"), selected_preset=u"UA Expr")
        self.capture("A6", {
            "update_expression": dict(message(C.UPDATE_EXPRESSION % u"UA Expr", u"Update Preset"),
                                      selected_preset=u"UA Expr"),
            "trash_expression": expr_trash})
        self.capture("A7", {}, clipboard=u"other" if "clipboard" in f else TRASH)
        ops = [("Save Current Body", "verified"), ("Update Preset", "no-op"), ("Delete Preset", "no-op"),
               ("Save Current Expression", "verified"), ("Update Preset", "no-op"), ("Delete Preset", "no-op"),
               ("Update Preset", "no-op")]
        if "preset-updated" in f:
            ops.append(("Update Preset", "verified"))
        if "pose-saved" in f:
            ops.append(("Save Pose", "verified"))
        lines, n = [], 0
        for i, (kind, outcome) in enumerate(ops, 1):
            for t in ("PROD_OPERATION_BEGIN id=%d kind=u'%s' context=None" % (i, kind),
                      "PROD_OPERATION_RESULT id=%d kind=u'%s' outcome=u'%s'" % (i, kind, outcome)):
                n += 1
                lines.append("2026-11-15T10:%02d:%02d.000Z #%06d s=x w=1 op=%d | %s" % (n // 60, n % 60, n, i, t))
        write(os.path.join(self.q, "evidence", "logs", "CPM - 2026-11-15_10-00-00Z - pid300 - x - 001.log"),
              ("\n".join(lines) + "\n").encode("utf-8"))
        base = "Characters/%s/" % CHAR
        diffs = [{"status": "added", "path": base + "Body Presets/UA Body.json", "sha256": "b"},
                 {"status": "added", "path": base + "Expressions/UA Expr.json", "sha256": "e"},
                 {"status": "changed", "path": base + "character.json", "sha256": "c"}]
        if "pose-saved" in f:
            diffs.append({"status": "added", "path": base + "Poses/UA Body--x.json", "sha256": "p"})
        if "trashed" in f:
            diffs.append({"status": "added", "path": "Trash/x--UA Body.json", "sha256": "t"})
        self.dump(os.path.join("evidence", "library_cleanup.json"), {
            "differences_kept_in_evidence": diffs, "files_equal_pre": True, "folders_equal_pre": True})
        self.dump(os.path.join("evidence", "restore.json"), {"restored": "not-restored" not in f,
                                                              "inventory_problems": []})
        write(os.path.join(self.q, "sessions", "UA_SOURCE.dmx"), b"src")
        return {"mode": "supplement", "paths": {"Q": self.q}, "character_dir": CHAR,
                "pins": {"qualification_cpm_sha256": SUP_QUAL, "candidate_cpm_sha256": SUP_PIN,
                         "r2_fixture_sha256": sha_bytes(b"src"), "destination_sha256": sha_bytes(b"dst")}}


SUP_PIN = "615acf0c23ffcf5c278785bb47de6aaf6a7b9ae26779b9313979ac928240c432"
SUP_QUAL = "849d0ed44101965de62165f01fcbb22b3caae9797e867169e71d4247b49cd4a2"


class SupplementTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="uasup")

    def tearDown(self):
        shutil.rmtree(self.dir, True)

    def verdict(self, *faults):
        q = os.path.join(self.dir, "Q%d" % len(os.listdir(self.dir)))
        c = SupplementSynthetic(q, faults).build()
        code = quiet(lambda: C.run(c))
        out = load(os.path.join(q, "evidence", "UA_SUPPLEMENT_VERDICT.json"))
        self.assertEqual(code == 0, out["verdict"] == "PASS")
        return out

    def test_a_complete_correct_supplement_passes_with_the_changed_file_as_a_finding(self):
        out = self.verdict()
        self.assertEqual((out["verdict"], out["failed"]), ("PASS", []), out["failed"])
        self.assertTrue(out["findings"])

    def test_supplement_counterexamples_fail_on_their_own_check(self):
        cases = {"old-title": "preset.body_update_confirmation",
                 "a6-message-box": "trash.expression_dialog",
                 "clipboard": "trash.recovery_folder_copies",
                 "preset-updated": "log.only_the_two_disposable_presets_were_written",
                 "pose-saved": "library.only_presets_added",
                 "trashed": "library.nothing_moved_to_trash",
                 "not-restored": "restore.published_and_inventories_equal"}
        for fault, check in sorted(cases.items()):
            out = self.verdict(fault)
            self.assertEqual(out["verdict"], "FAIL", fault)
            self.assertIn(check, out["failed"], (fault, out["failed"]))

    def test_the_supplement_configuration_refuses_seed_and_replay(self):
        c = TOOL.S.load(config(self.dir))
        c["mode"] = "supplement"
        self.assertRaises(SystemExit, TOOL.cmd_seed_checked, c)
        self.assertRaises(SystemExit, TOOL.cmd_replay, c)

    def test_the_supplement_template_pins_the_current_candidate_and_its_qualification_build(self):
        with open(os.path.join(ROOT, "ua_supplement.template.json"), "rb") as f:
            t = json.loads(f.read().decode("utf-8"))
        with open(os.path.join(ROOT, "ua.template.json"), "rb") as f:
            base = json.loads(f.read().decode("utf-8"))
        self.assertEqual((t["mode"], t["format"], t["pins"]["candidate_cpm_sha256"],
                          t["pins"]["qualification_cpm_sha256"], t["pins"]["capture_sha256"]),
                         ("supplement", "F01-UA1-config-v1", SUP_PIN, SUP_QUAL, base["pins"]["capture_sha256"]))


if __name__ == "__main__":
    unittest.main()
