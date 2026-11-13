# -*- coding: ascii -*-
"""F-01 PS-2 v1.1.0 production smoke: state capture. STRICTLY READ-ONLY. Run from SFM's Script Editor (Python 2.7)
with CPM open:

    PS2_DIR = r"<Q>"; PS2_STEP = "S-PROD"; execfile(PS2_REPO + r"\\real_sfm_qualification\\f01_ps2_v110\\observer\\F01_PS2_State.py")

It records, from the running SFM and the open CPM window:
- the loaded CPM (its build SHA-256, registry mode, engine rule table, carried-channel switches, the qualification
  fault hook, and the release version CPM reports for itself from the installed software inventory);
- the Pose Library registries as CPM loads them, and the production mappings they enable;
- the selected character, the selected pose (version, scope, part count) with the Poses page state and the Pose Info
  rows CPM shows for it (pure functions of the record);
- the session: document, shot, timeline mode and the Undo/Redo descriptions.

It clicks nothing, selects nothing, opens no dialog and never touches the scene or the library. Its only write is
<PS2_DIR>\\observations\\<PS2_STEP>.json (exclusive create). On the v1.0.0 CPM (after rollback) the Pose Library
fields are simply absent.
"""
import hashlib
import json
import os
import sys

STEPS = ("S-PROD", "S-E-INFO", "S-E-APPLY", "S-E-UNDO", "S-E-REDO", "S-SOLDIER-SAVED", "S-SOLDIER-APPLY",
         "S-SOLDIER-UNDO", "S-HEAVY", "S-K-GRIP", "S-K-GRIP-APPLY", "S-K-UNDO", "S-K-REDO", "S-K-LEGACY",
         "S-K-PRESETS", "S-V100")


def _text(v):
    try:
        return v if isinstance(v, unicode) else str(v).decode("utf-8", "replace")  # noqa: F821 (Python 2.7)
    except NameError:
        return str(v)


def _try(fn):
    try:
        return fn()
    except Exception as exc:
        return {"error": repr(exc)}


def ps2_state(g):
    root, label = g.get("PS2_DIR"), g.get("PS2_STEP")
    if not root or label not in STEPS:
        raise RuntimeError("Set PS2_DIR and PS2_STEP (one of %s) first; see the docstring." % ", ".join(STEPS))
    path = os.path.join(root, "observations", "%s.json" % label)
    if os.path.exists(path):
        raise RuntimeError("%s exists; each capture is taken once." % path)
    cpm = sys.modules.get("chadchan3d_cpm_app")
    if cpm is None:
        raise RuntimeError("CPM is not loaded: open Character Preset Manager first.")
    build = getattr(cpm, "__chadchan3d_cpm_build_sha256__", None)
    if not build and getattr(cpm, "__file__", None):
        with open(cpm.__file__.replace(".pyc", ".py"), "rb") as f:
            build = hashlib.sha256(f.read()).hexdigest()
    data = {"format": "F01-PS2-state-v1", "label": label, "pid": os.getpid(), "cpm_build_sha256": build,
            "registry_mode": getattr(cpm, "PROD_POSE_REGISTRY_MODE", None),
            "scope_rules": getattr(cpm, "PROD_SCOPE_RULES", None),
            "carried_enabled": getattr(cpm, "PROD_SCOPE_CARRIED_ENABLED", None),
            "extrapolation_qualified": getattr(cpm, "PROD_SCOPE_EXTRAPOLATION_QUALIFIED", None),
            "qualification_fault": getattr(cpm, "PROD_POSE_QUAL_FAULT", None),
            "release_version": _try(cpm.prod_release_version) if hasattr(cpm, "prod_release_version") else None}
    if hasattr(cpm, "prod_pose_load_registry"):
        def registry():
            reg = cpm.prod_pose_load_registry()
            sel = cpm.prod_pose_registry_select(reg, cpm.PROD_POSE_REGISTRY_MODE)
            return {"registry_sha256": reg.get(u"_sha256"), "body_loaded": reg.get(u"_body") is not None,
                    "mappings": sorted([_text(m.get(u"region")), _text(m.get(u"status"))] for m in sel[u"mappings"])}
        data["registry"] = _try(registry)
    from PySide import QtGui
    app = QtGui.QApplication.instance()
    win = getattr(app, getattr(cpm, "PROD_APP_ATTR", ""), None) if app is not None else None
    data["window_open"] = win is not None
    if win is not None:
        data["character"] = _try(lambda: dict((k, _text(v)) for k, v in (win.current() or {}).items()))
        data["recovery_paused"] = bool(getattr(win, "pose_recovery_blocked", False)) or \
            (getattr(cpm, "PROD_POSE_RECOVERY_BLOCK", [None])[0] is not None)
        if hasattr(win, "selected_pose"):
            item = _try(win.selected_pose)
            item = item if isinstance(item, dict) and u"error" not in item else None
            record = (item or {}).get(u"record") or {}
            pose = record.get(u"pose") or {}
            scope = pose.get(u"scope") or {}
            data["selected_pose"] = None if item is None else {
                "name": item.get(u"name"), "preset_id": item.get(u"preset_id"), "version": pose.get(u"version"),
                "regions": sorted(pose.get(u"regions") or {}), "scope_kind": scope.get(u"kind"),
                "posed": len(scope.get(u"posed") or []), "root_translation": scope.get(u"root_translation"),
                "engine": pose.get(u"engine"), "model": (pose.get(u"source") or {}).get(u"model_ref")}
            if item is not None:
                data["pose_ui_state"] = _try(lambda: win.pose_ui_state(item))
                data["apply_button_enabled"] = _try(lambda: bool(win.apply_pose_button.isEnabled()))
                if hasattr(cpm, "prod_pose_info_view"):
                    data["pose_info"] = _try(lambda: cpm.prod_pose_info_view(record))
    import sfmApp
    import vs
    dm = vs.g_pDataModel
    session = {"undo": _try(lambda: {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()),
                                     "undo_desc": _text(dm.GetUndoDesc()), "redo_desc": _text(dm.GetRedoDesc())})}
    session["timeline_mode"] = _try(lambda: _text(sfmApp.GetNameForTimelineMode(sfmApp.GetTimelineMode())))
    session["head_seconds"] = _try(lambda: float(sfmApp.GetHeadTimeInSeconds()))
    session["shot"] = _try(lambda: _text(sfmApp.GetShotAtCurrentTime().GetName()))
    session["document"] = _try(lambda: _text(dm.GetFileName(sfmApp.GetDocumentRoot().GetFileId())))
    data["session"] = session
    payload = json.dumps(data, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    sel = data.get("selected_pose") or {}
    undo = (session.get("undo") or {})
    line = "PS2 %s: CPM %s mode %r version %r | pose %r v%r %r (%r parts) | undo %r redo %r | written" % (
        label, (build or "?")[:8], data["registry_mode"], data["release_version"], sel.get("name"), sel.get("version"),
        sel.get("scope_kind"), sel.get("posed"), undo.get("undo_desc"), undo.get("redo_desc"))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


ps2_state(globals())
