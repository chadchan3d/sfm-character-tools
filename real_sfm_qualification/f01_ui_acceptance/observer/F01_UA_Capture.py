# -*- coding: ascii -*-
"""F-01 UA-1: the native UI acceptance capture. Run from SFM's Script Editor (Python 2.7) with Character Preset
Manager open, after the setup line, with the item the step needs selected:

    UA_DIR = r"<run folder>"; UA_REPO = r"<repo>"
    UA_STEP = "A1"; execfile(UA_REPO + r"\\real_sfm_qualification\\f01_ui_acceptance\\observer\\F01_UA_Capture.py")

For each step it runs the window's own button handlers (the real product paths) only as far as their dialog: while it
runs, QDialog.exec_ and QMessageBox.exec_ are replaced by a capture that records the dialog's visible content and
answers as if Cancel (or Close) was clicked, so every operation ends as CPM's own cancellation ("no-op", nothing
written). Pose Info is read-only by design. It clicks nothing on screen, never answers Save, Update or Move to Trash,
never touches the scene, and restores both exec_ methods before returning. Its only write is
<UA_DIR>\\observations\\UA-<step>.json (exclusive create).

Steps (the selection each one needs):
  A1  Poses, the seeded version 2 pose "K2 Pose" selected        Pose Info; Apply Pose enabled
  A2  Poses, the seeded version 1 pose "NQ1 Pose A" selected     Pose Info; Apply Pose enabled
  A3  Poses (any selection)                                       the Save Pose dialog (Full body), cancelled
  A4  Poses, "UA Pose" (saved by the Owner) selected              Pose Info; Update Pose and Delete Pose dialogs
  A5  Body Presets, "UA Body" selected                            Update Preset and Delete Preset dialogs
  A6  Expressions, "UA Expr" selected                             Update Preset and Delete Preset dialogs
  A7  after copying the Trash folder path from a Delete dialog    the clipboard text only
  B1  Poses, "UA Pose" selected after the Owner's Update          Pose Info; Update Pose dialog
"""
import json
import os
import sys

UA_STEPS = {
    "A1": ("pose_info", "apply_state"),
    "A2": ("pose_info", "apply_state"),
    "A3": ("save_dialog",),
    "A4": ("pose_info", "update_pose", "trash_pose"),
    "A5": ("update_body", "trash_body"),
    "A6": ("update_expression", "trash_expression"),
    "A7": (),
    "B1": ("pose_info", "update_pose"),
}


def ua_text(value):
    try:
        return u"%s" % (value,)
    except Exception:
        return repr(value)


def ua_snapshot(QtGui, widget):
    """The visible content of one dialog: title, labels (with text interaction flags), radio buttons, check boxes,
    push buttons (enabled, default), group boxes and the first tree's top-level rows."""
    out = {"class": type(widget).__name__, "title": ua_text(widget.windowTitle())}
    if isinstance(widget, QtGui.QMessageBox):
        default = widget.defaultButton()
        out.update({"kind": "message", "text": ua_text(widget.text()),
                    "informative": ua_text(widget.informativeText()),
                    "text_format": int(widget.textFormat()),
                    "buttons": [ua_text(b.text()) for b in widget.buttons()],
                    "default": ua_text(default.text()) if default is not None else None})
        return out
    out["kind"] = "dialog"
    out["labels"] = [{"text": ua_text(w.text()), "flags": int(w.textInteractionFlags()),
                      "visible": bool(w.isVisibleTo(widget))} for w in widget.findChildren(QtGui.QLabel)]
    out["radios"] = [{"text": ua_text(w.text()), "checked": bool(w.isChecked()), "enabled": bool(w.isEnabled())}
                     for w in widget.findChildren(QtGui.QRadioButton)]
    out["checks"] = [{"text": ua_text(w.text()), "checked": bool(w.isChecked()), "visible": bool(w.isVisibleTo(widget))}
                     for w in widget.findChildren(QtGui.QCheckBox)]
    out["buttons"] = [{"text": ua_text(w.text()), "enabled": bool(w.isEnabled()), "default": bool(w.isDefault())}
                      for w in widget.findChildren(QtGui.QPushButton)]
    out["groups"] = [ua_text(w.title()) for w in widget.findChildren(QtGui.QGroupBox)]
    trees = widget.findChildren(QtGui.QTreeWidget)
    out["tree_top"] = ([ua_text(trees[0].topLevelItem(i).text(0)) for i in range(trees[0].topLevelItemCount())]
                       if trees else None)
    out["tree_children"] = (sum(trees[0].topLevelItem(i).childCount() for i in range(trees[0].topLevelItemCount()))
                            if trees else None)
    return out


def ua_run_captured(QtGui, fn):
    """Run fn() with both exec_ methods replaced by a capture that answers Cancel/Close. Returns (captured
    dialogs, error text or None). The originals are always restored."""
    seen = []
    real_dialog, real_message = QtGui.QDialog.exec_, QtGui.QMessageBox.exec_

    def fake(self):
        seen.append(ua_snapshot(QtGui, self))
        return 0
    QtGui.QDialog.exec_ = fake
    QtGui.QMessageBox.exec_ = fake
    error = None
    try:
        fn()
    except Exception as exc:
        error = "%s: %s" % (type(exc).__name__, ua_text(exc))
    finally:
        QtGui.QDialog.exec_ = real_dialog
        QtGui.QMessageBox.exec_ = real_message
    return seen, error


def ua_capture(g):
    root = g.get("UA_DIR")
    step = g.get("UA_STEP")
    if not root or step not in UA_STEPS:
        raise RuntimeError("Set UA_DIR and UA_STEP (one of %s) first; see the docstring." % sorted(UA_STEPS))
    path = os.path.join(root, "observations", "UA-%s.json" % step)
    if os.path.exists(path):
        raise RuntimeError("%s exists; each step is captured once." % path)
    cpm = sys.modules.get("chadchan3d_cpm_app")
    if cpm is None:
        raise RuntimeError("CPM is not loaded: open Character Preset Manager first.")
    from PySide import QtGui
    app = QtGui.QApplication.instance()
    win = getattr(app, cpm.PROD_APP_ATTR, None) if app is not None else None
    if win is None:
        raise RuntimeError("The CPM window is not open.")
    if getattr(win, "busy", False) or getattr(win, "operation", None) is not None:
        raise RuntimeError("CPM is busy; wait for the current operation to finish.")
    document = None
    try:
        import sfmApp
        import vs
        if sfmApp.HasDocument():
            document = ua_text(vs.g_pDataModel.GetFileName(sfmApp.GetDocumentRoot().GetFileId()))
    except Exception as exc:
        document = "unreadable: %s" % ua_text(exc)
    item = win.selected_pose()
    record = (item or {}).get(u"record") or {}
    pose = record.get(u"pose") or {}
    data = {"format": "F01-UA1-capture-v1", "step": step, "pid": os.getpid(),
            "cpm_build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__", None),
            "document": document, "clipboard": ua_text(QtGui.QApplication.clipboard().text()),
            "selected_pose": None if item is None else {
                "name": item.get(u"name"), "preset_id": item.get(u"preset_id"), "version": pose.get(u"version"),
                "regions": sorted(pose.get(u"regions") or {}), "path": item.get(u"path"),
                "shot_name": (pose.get(u"source") or {}).get(u"shot_name")},
            "trash_folder": None, "captures": {}}
    try:
        data["trash_folder"] = ua_text(os.path.join(cpm.prod_paths(win.identity)["root"], cpm.P03_TRASH_DIRNAME))
    except Exception as exc:
        data["trash_folder"] = "unreadable: %s" % ua_text(exc)
    actions = {
        "pose_info": lambda: win.open_pose_info(),
        "save_dialog": lambda: win.save_pose(None, (u"full_body",)),
        "update_pose": lambda: win.update_selected_pose(),
        "trash_pose": lambda: win.delete_selected_pose(),
        "update_body": lambda: win.update_kind(cpm.P03_KIND_BODY),
        "trash_body": lambda: win.delete_kind(cpm.P03_KIND_BODY),
        "update_expression": lambda: win.update_kind(cpm.P03_KIND_EXPRESSION),
        "trash_expression": lambda: win.delete_kind(cpm.P03_KIND_EXPRESSION),
    }
    for name in UA_STEPS[step]:
        if name == "apply_state":
            data["captures"][name] = {"apply_button_enabled": bool(win.apply_pose_button.isEnabled())}
            continue
        selected = None
        if name in ("update_body", "trash_body", "update_expression", "trash_expression"):
            try:
                rec = win.selected(cpm.P03_KIND_BODY if "body" in name else cpm.P03_KIND_EXPRESSION)["record"]
                selected = rec.get("name")
            except Exception as exc:
                selected = "unreadable: %s" % ua_text(exc)
        dialogs, error = ua_run_captured(QtGui, actions[name])
        data["captures"][name] = {"dialogs": dialogs, "error": error, "selected_preset": selected,
                                  "busy_after": bool(getattr(win, "busy", False)),
                                  "status_after": ua_text(getattr(win, "status", None).text())
                                  if getattr(win, "status", None) is not None else None}
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    shown = sum(len(c.get("dialogs") or []) for c in data["captures"].values())
    errors = [k for k, c in data["captures"].items() if c.get("error")]
    line = "UA STEP %s: %d dialog(s) captured%s (%s)" % (
        step, shown, (", ERRORS in %s - STOP" % errors) if errors else "", os.path.basename(path))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


ua_capture(globals())
