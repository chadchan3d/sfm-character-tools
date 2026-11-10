# -*- coding: ascii -*-
"""F-01 EF-1 Engineer Full body native qualification: Poses-page UI evidence. STRICTLY READ-ONLY. Run from SFM's
Script Editor (Python 2.7) with CPM open and the pose to inspect selected in the Poses list:

    EF1_UI = "UI-A"; execfile(EF1_REPO + r"\\real_sfm_qualification\\f01_ef1_full_body\\observer\\F01_EF1_UIState.py")

(EF1_DIR and EF1_REPO set as for the observer.) It reads the open CPM window (the private module chadchan3d_cpm_app and
its application window slot), exactly as the SFP-1 UI capture does:
- the selected pose, its payload version and scope;
- whether Apply Pose is enabled, and the Poses page state that enables it (pose_ui_state, a pure function);
- the Pose Info rows CPM shows for a version 3 record (prod_scope_info, a pure function of the record);
- whether pose changes are paused.

It clicks nothing, selects nothing, opens no dialog and never touches the scene. Its only write is
<EF1_DIR>\\observations\\<EF1_UI>.json (exclusive create). Labels: UI-A, UI-B.
"""
import json
import os
import sys

LABELS = ("UI-A", "UI-B")


def ef1_ui_state(g):
    root, label = g.get("EF1_DIR"), g.get("EF1_UI")
    if not root or label not in LABELS:
        raise RuntimeError("Set EF1_DIR and EF1_UI (one of %s) first; see the docstring." % ", ".join(LABELS))
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
    data = {"format": "F01-EF1-ui-v1", "label": label, "pid": os.getpid(),
            "cpm_build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__", None),
            "registry_mode": getattr(cpm, "PROD_POSE_REGISTRY_MODE", None),
            "selected": None if item is None else {
                "name": item.get(u"name"), "preset_id": item.get(u"preset_id"), "version": pose.get(u"version"),
                "regions": sorted(pose.get(u"regions") or {}), "scope_kind": scope.get(u"kind"),
                "posed": len(scope.get(u"posed") or []), "root_translation": scope.get(u"root_translation"),
                "label": scope.get(u"label"), "engine": pose.get(u"engine")},
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
    ok = (data["apply_button_enabled"] and sel.get("version") == 3 and sel.get("scope_kind") == u"full_body"
          and not data["recovery_paused"] and data["registry_mode"] == u"qualification")
    line = ("EF1 %s: %r version 3 Full body (%d bones), Apply Pose enabled: OK" % (label, sel.get("name"),
                                                                                  sel.get("posed") or 0)) if ok else (
        "EF1 %s: %r version %r scope %r, Apply Pose %s, mode %r - STOP" % (
            label, sel.get("name"), sel.get("version"), sel.get("scope_kind"),
            "enabled" if data["apply_button_enabled"] else "DISABLED", data["registry_mode"]))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


ef1_ui_state(globals())
