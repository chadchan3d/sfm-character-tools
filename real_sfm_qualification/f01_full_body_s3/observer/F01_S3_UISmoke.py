# -*- coding: ascii -*-
"""F-01 full-body S3: the Poses page UI smoke check before the first Apply. STRICTLY READ-ONLY. Run from SFM's Script
Editor (Python 2.7) with CPM open and the pose to check selected in the Poses list:

    S3_DIR = r"<run folder>"; execfile(S3_REPO + r"\\real_sfm_qualification\\f01_full_body_s3\\observer\\F01_S3_UISmoke.py")

It reads the open CPM window (the private module chadchan3d_cpm_app and its application window slot): the selected
pose, whether the Apply Pose button is enabled, and the Poses page state that enables it (prod_pose_ui_state, a pure
function). It clicks nothing, selects nothing and never touches the scene. Its only write is
<S3_DIR>\\observations\\UI-SMOKE.json (exclusive create).
"""
import json
import os
import sys


def s3_ui_smoke(g):
    root = g.get("S3_DIR")
    if not root:
        raise RuntimeError("Set S3_DIR first; see the docstring.")
    path = os.path.join(root, "observations", "UI-SMOKE.json")
    if os.path.exists(path):
        raise RuntimeError("%s exists; the UI smoke check is taken once." % path)
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
    data = {"format": "F01-S3-ui-smoke-v1", "pid": os.getpid(),
            "cpm_build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__", None),
            "selected": None if item is None else {"name": item.get(u"name"), "preset_id": item.get(u"preset_id"),
                                                    "version": pose.get(u"version"),
                                                    "regions": sorted(pose.get(u"regions") or {})},
            "apply_button_enabled": bool(win.apply_pose_button.isEnabled()),
            "state": {"apply_pose": state[u"buttons"][u"apply_pose"], "apply_mode": state[u"apply_mode"],
                      "summary": state[u"summary"]},
            "recovery_paused": bool(getattr(win, "pose_recovery_blocked", False)) or
            getattr(cpm, "PROD_POSE_RECOVERY_BLOCK", [None])[0] is not None}
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    sel = data["selected"] or {}
    ok = data["apply_button_enabled"] and sel.get("regions") == ["full_body"] and not data["recovery_paused"]
    line = ("S3 UI SMOKE: Apply Pose ENABLED for %s (full body): OK" % sel.get("name")) if ok else (
        "S3 UI SMOKE: Apply Pose %s for %r (%s) - STOP" % ("enabled" if data["apply_button_enabled"] else "DISABLED",
                                                         sel.get("name"), sel.get("regions")))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


s3_ui_smoke(globals())
