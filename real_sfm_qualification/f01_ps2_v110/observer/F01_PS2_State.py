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
- the session: document, shot, timeline mode and the Undo/Redo descriptions;
- every animation set in the current shot: name, handle, model and digests of its control values and its game
  model's bone transforms (position, orientation, scale) and flex weights (target identity and peer isolation for
  the duplicate-model Body preset check).

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
         "S-K-PRESETS", "S-K-DUP-BEFORE", "S-K-DUP-SAVED", "S-K-DUP-APPLY", "S-K-DUP-UNDO", "S-V100")
MAX_ITEMS = 4096


def _attr(obj, name):
    """An attribute's value through the element's own attribute accessor, or None when absent."""
    if obj is None or not obj.HasAttribute(name):
        return None
    a = obj.GetAttribute(name)
    for method in ("GetValue", "GetValueUntyped"):
        try:
            return getattr(a, method)()
        except Exception:
            pass
    return None


def _seq(value):
    n = len(value) if value is not None else 0
    if n > MAX_ITEMS:
        raise RuntimeError("collection exceeds its bound (%d)" % n)
    return [value[i] for i in range(n)]


def _plain(v):
    """A JSON form of a native scalar or vector; element references by name only; anything else by repr."""
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if hasattr(v, "GetHandle") and hasattr(v, "GetName"):
        return "@" + _text(v.GetName())
    for keys in (("x", "y", "z", "w"), ("x", "y", "z")):
        if all(hasattr(v, k) for k in keys):
            return [round(float(getattr(v, k)), 6) for k in keys]
    if isinstance(v, float):
        return round(v, 6)
    return _text(v)


def _controls_state(animset):
    """{control name: {attribute: value}} for every control's value attributes (read only)."""
    out = {}
    for c in _seq(_attr(animset, "controls")):
        row = {}
        for name in ("value", "leftValue", "rightValue", "valuePosition", "valueOrientation"):
            v = _attr(c, name)
            if v is not None:
                row[name] = _plain(v)
        out[_text(c.GetName())] = row
    return out


def _model_state(animset):
    """The game model's bone transforms (position, orientation, scale) and global flex weights (read only)."""
    gm = _attr(animset, "gameModel")
    if gm is None:
        return {"model": None}
    bones = []
    for t in _seq(_attr(gm, "bones")):
        bones.append([_text(t.GetName())] + [_plain(_attr(t, k)) for k in ("position", "orientation", "scale")])
    flexes = [[_text(f.GetName()), _plain(_attr(f, "flexWeight"))] for f in _seq(_attr(gm, "globalFlexControllers"))]
    return {"model": _text(_attr(gm, "modelName")), "bones": bones, "flexes": flexes}


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def shot_animation_sets(sfmApp):
    """Every animation set in the current shot: its name, handle, model, and digests of its control values and of its
    game model's bones and flexes, so target identity and peer isolation are visible without any write."""
    shot = sfmApp.GetShotAtCurrentTime()
    rows = []
    for a in _seq(_attr(shot, "animationSets")):
        controls, model = _controls_state(a), _model_state(a)
        rows.append({"name": _text(a.GetName()), "handle": int(a.GetHandle()), "model": model.get("model"),
                     "controls": len(controls), "controls_sha256": _digest(controls),
                     "bones": len(model.get("bones") or []), "model_sha256": _digest(model),
                     "state_sha256": _digest([controls, model])})
    return rows


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
    data["animation_sets"] = _try(lambda: shot_animation_sets(sfmApp))
    payload = json.dumps(data, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    sel = data.get("selected_pose") or {}
    undo = (session.get("undo") or {})
    sets = data["animation_sets"]
    sets_text = ("%d animation sets" % len(sets)) if isinstance(sets, list) else "animation sets UNREADABLE - STOP"
    line = "PS2 %s: CPM %s mode %r version %r | pose %r v%r %r (%r parts) | undo %r redo %r | %s | written" % (
        label, (build or "?")[:8], data["registry_mode"], data["release_version"], sel.get("name"), sel.get("version"),
        sel.get("scope_kind"), sel.get("posed"), undo.get("undo_desc"), undo.get("redo_desc"), sets_text)
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


ps2_state(globals())
