# -*- coding: ascii -*-
"""F-01 SFP-1 Selected parts native qualification: Poses-page UI evidence. STRICTLY READ-ONLY. Run from SFM's Script
Editor (Python 2.7) with CPM open and the pose to inspect selected in the Poses list:

    SFP1_UI = "UI-A"; execfile(SFP1_REPO + r"\\real_sfm_qualification\\f01_sfp1_nq\\observer\\F01_SFP1_UIState.py")

(SFP1_DIR and SFP1_REPO set as for the observer.) It reads the open CPM window (the private module
chadchan3d_cpm_app and its application window slot): the selected pose and its payload version and scope, whether
Apply Pose is enabled, the Poses page state that enables it (pose_ui_state, a pure function), the Pose Info rows CPM
shows for a version 3 record (prod_scope_info, a pure function of the record), and whether pose changes are paused.
It clicks nothing, selects nothing, opens no dialog and never touches the scene. Its only write is
<SFP1_DIR>\\observations\\<SFP1_UI>.json (exclusive create). Labels: UI-A, UI-B, UI-C.
"""
import json
import os
import sys

LABELS = ("UI-A", "UI-B", "UI-C")


def sfp1_ui_state(g):
    root, label = g.get("SFP1_DIR"), g.get("SFP1_UI")
    if not root or label not in LABELS:
        raise RuntimeError("Set SFP1_DIR and SFP1_UI (one of %s) first; see the docstring." % ", ".join(LABELS))
    path = os.path.join(root, "observations", "%s.json" % label)
    if os.path.exists(path):
        raise RuntimeError("%s exists; each UI capture is taken once." % path)
    cpm = sys.modules.get("chadchan3d_cpm_app")
    if cpm is None:
        raise RuntimeError("CPM is not loaded: open Character Preset Manager first.")
    from PySide import QtGui
    app = QtGui.QApplication.instance()
    win = getattr(app, cpm.PROD_APP_ATTR, None) if app is not None else None
    if win is None:
        raise RuntimeError("The CPM window is not open.")
    item = win.selected_pose()
    state = win.pose_ui_state(item)
    record = (item or {}).get(u"record") or {}
    pose = record.get(u"pose") or {}
    info = None
    if pose.get(u"version") == 3:
        try:
            info = cpm.prod_scope_info(record)
        except Exception as exc:
            info = {"error": repr(exc)}
    scope = pose.get(u"scope") or {}
    data = {"format": "F01-SFP1-ui-v1", "label": label, "pid": os.getpid(),
            "cpm_build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__", None),
            "registry_mode": getattr(cpm, "PROD_POSE_REGISTRY_MODE", None),
            "selected": None if item is None else {
                "name": item.get(u"name"), "preset_id": item.get(u"preset_id"), "version": pose.get(u"version"),
                "regions": sorted(pose.get(u"regions") or {}), "scope_kind": scope.get(u"kind"),
                "posed": list(scope.get(u"posed") or []), "label": scope.get(u"label"),
                "engine": pose.get(u"engine")},
            "apply_button_enabled": bool(win.apply_pose_button.isEnabled()),
            "state": {"apply_pose": state[u"buttons"][u"apply_pose"], "apply_mode": state[u"apply_mode"],
                      "summary": state[u"summary"]},
            "pose_info": info,
            "recovery_paused": bool(getattr(win, "pose_recovery_blocked", False)) or
            getattr(cpm, "PROD_POSE_RECOVERY_BLOCK", [None])[0] is not None}
    payload = json.dumps(data, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    sel = data["selected"] or {}
    ok = (data["apply_button_enabled"] and sel.get("version") == 3 and sel.get("scope_kind") == u"selected_parts"
          and not data["recovery_paused"] and data["registry_mode"] == u"qualification")
    line = ("SFP1 %s: %r version 3 Selected parts, Apply Pose enabled: OK" % (label, sel.get("name"))) if ok else (
        "SFP1 %s: %r version %r scope %r, Apply Pose %s, mode %r - STOP" % (
            label, sel.get("name"), sel.get("version"), sel.get("scope_kind"),
            "enabled" if data["apply_button_enabled"] else "DISABLED", data["registry_mode"]))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


sfp1_ui_state(globals())
