# -*- coding: ascii -*-
"""F-01 H1: the native Heavy procedural-helper check, state capture. STRICTLY READ-ONLY. Run from SFM's Script
Editor (Python 2.7) with CPM open, after the setup line:

    H1_DIR = r"<Q>"; H1_SOURCE = "<source set>"; H1_TARGET = "<target set>"; H1_PEER = "<peer set>"
    H1_STEP = "BASE"; execfile(r"<REPO>\\real_sfm_qualification\\f01_h1_heavy\\observer\\F01_H1_Capture.py")

For the three named Heavy animation sets of the current shot it records, through the loaded CPM's own read-only
functions (prod_scope_live, prod_pose_channel_authored, prod_pose_transform_state, prod_scope_helper_evidence,
prod_scope_state):
- every channel of the set's channels clip with a digest of its complete authored state (binding, log fields, every
  layer's keys, times and values) and the bone it writes;
- every bone's local and absolute transform;
- the engine-loaded studio header evidence and CPM's helper admission (admitted helpers and refusals);
and the session (shot, playhead, Undo/Redo descriptions), the loaded CPM build and the selected pose's coverage
ledger summary. It clicks nothing, selects nothing, never touches the scene or the library and never evaluates or
refreshes. Its only write is <H1_DIR>\\observations\\H1-<step>.json (exclusive create).
"""
import hashlib
import json
import os
import sys

FORMAT = "F01-H1-capture-v1"
STEPS = ("BASE", "SAVED", "APPLY", "UNDO", "REDO", "NOOP")
ROLES = ("source", "target", "peer")


def h1_text(v):
    try:
        return v if isinstance(v, type(u"")) else v.decode("utf-8", "replace") if isinstance(v, bytes) else \
            type(u"")(v)
    except Exception:
        return repr(v)


def h1_try(fn):
    try:
        return fn()
    except Exception as exc:
        return {"error": repr(exc)}


def h1_digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=repr).encode("utf-8")).hexdigest()


def h1_set(cpm, shot, animset):
    out = {"name": h1_text(animset.GetName()), "errors": []}
    gm = cpm.get_game_model(animset)
    if gm is None:
        out["errors"].append("no game model")
        return out
    out["model"] = h1_text(cpm.prod_pose_attr(gm, u"modelName"))
    row = {"shot": shot, "animset": animset, "gm": gm}
    L = cpm.prod_scope_live(row)
    budget = [0]
    channels = {}
    for ch in L[u"clip_channels"]:
        authored = cpm.prod_pose_channel_authored(ch, budget)
        to = (authored.get(u"binding") or {}).get(u"toElement") or {}
        target = to.get(u"value") if isinstance(to, dict) else None
        channels[h1_text(ch.GetName())] = {
            "sha256": h1_digest(authored),
            "to": h1_text(target.get(u"name")) if isinstance(target, dict) else None,
            "to_attribute": h1_text(((authored.get(u"binding") or {}).get(u"toAttribute") or {}).get(u"value"))}
    out["channels"] = channels
    out["keys"] = budget[0]
    bones = {}
    for name, b in L[u"bones"].items():
        s = cpm.prod_pose_transform_state(b[u"dag"])
        bones[h1_text(name)] = [list(s[u"local_position"]), list(s[u"local_orientation"]),
                                list(s[u"world_position"]), list(s[u"world_orientation"])]
    out["bones"] = bones
    ev = cpm.prod_scope_helper_evidence(L)
    out["header"] = {"status": ev.get(u"status"), "reason": ev.get(u"reason"),
                     "bones": len(ev.get(u"bones") or []), "attachments": len(ev.get(u"attachments") or []),
                     "flex_drivers": len(ev.get(u"flex_drivers") or []),
                     "declared": [[r[u"index"], h1_text(r[u"name"]), r[u"parent"], r[u"flags"], r[u"proctype"]]
                                  for r in ev.get(u"bones") or [] if r[u"proctype"] != 0 or r[u"flags"] & 4]}

    def admission():
        st = cpm.prod_scope_state(row)
        classes = {}
        for n, r in st[u"C"][u"bones"].items():
            classes[r[u"class"]] = classes.get(r[u"class"], 0) + 1
        return {"helpers": [h1_text(n) for n in st[u"helpers"]],
                "refusals": dict((h1_text(k), h1_text(v)) for k, v in st[u"helper_refusals"].items()),
                "classes": classes}
    out["admission"] = h1_try(admission)
    return out


def h1_selected_pose(cpm):
    from PySide import QtGui
    app = QtGui.QApplication.instance()
    win = getattr(app, getattr(cpm, "PROD_APP_ATTR", ""), None) if app is not None else None
    if win is None or not hasattr(win, "selected_pose"):
        return None
    item = win.selected_pose()
    if not isinstance(item, dict):
        return None
    pose = (item.get(u"record") or {}).get(u"pose") or {}
    scope = pose.get(u"scope") or {}
    roles = {}
    for n, r in (scope.get(u"ledger") or {}).items():
        roles.setdefault(h1_text(r), []).append(h1_text(n))
    return {"name": h1_text(item.get(u"name")), "version": pose.get(u"version"), "kind": scope.get(u"kind"),
            "engine": pose.get(u"engine"), "model": (pose.get(u"source") or {}).get(u"model_ref"),
            "roles": dict((k, len(v)) for k, v in roles.items()),
            "helpers": sorted(roles.get(u"engine-helper", []))}


def h1_capture(g):
    root, step = g.get("H1_DIR"), g.get("H1_STEP")
    names = dict((r, g.get("H1_" + r.upper())) for r in ROLES)
    if not root or step not in STEPS or not all(names.values()) or len(set(names.values())) != 3:
        raise RuntimeError("Set H1_DIR, H1_SOURCE, H1_TARGET, H1_PEER (three different animation sets) and H1_STEP "
                           "(one of %s) first; nothing was written." % ", ".join(STEPS))
    path = os.path.join(root, "observations", "H1-%s.json" % step)
    if os.path.exists(path):
        raise RuntimeError("%s exists; each capture is taken once. Nothing was written." % path)
    cpm = sys.modules.get("chadchan3d_cpm_app")
    if cpm is None:
        raise RuntimeError("CPM is not loaded: open Character Preset Manager first. Nothing was written.")
    build = getattr(cpm, "__chadchan3d_cpm_build_sha256__", None)
    if not build and getattr(cpm, "__file__", None):
        with open(cpm.__file__.replace(".pyc", ".py"), "rb") as f:
            build = hashlib.sha256(f.read()).hexdigest()
    import sfmApp
    import vs
    dm = vs.g_pDataModel
    data = {"format": FORMAT, "step": step, "pid": os.getpid(), "cpm_build_sha256": build,
            "registry_mode": getattr(cpm, "PROD_POSE_REGISTRY_MODE", None), "names": names, "sets": {},
            "errors": []}
    shot = sfmApp.GetShotAtCurrentTime()
    session = {"undo": h1_try(lambda: {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()),
                                       "undo_desc": h1_text(dm.GetUndoDesc()),
                                       "redo_desc": h1_text(dm.GetRedoDesc())}),
               "head_seconds": h1_try(lambda: float(sfmApp.GetHeadTimeInSeconds())),
               "shot": h1_try(lambda: h1_text(shot.GetName())),
               "document": h1_try(lambda: h1_text(dm.GetFileName(sfmApp.GetDocumentRoot().GetFileId())))}
    data["session"] = session
    sets = list(cpm.prod_pose_seq(cpm.prod_pose_attr(shot, u"animationSets"))) if shot is not None else []
    data["animation_sets"] = sorted(h1_text(a.GetName()) for a in sets)
    for role in ROLES:
        found = [a for a in sets if h1_text(a.GetName()) == names[role]]
        if len(found) != 1:
            data["errors"].append("%s: %d animation sets named %r" % (role, len(found), names[role]))
            continue
        try:
            data["sets"][role] = h1_set(cpm, shot, found[0])
        except Exception as exc:
            data["errors"].append("%s: %r" % (role, exc))
    data["selected_pose"] = h1_try(lambda: h1_selected_pose(cpm))
    payload = json.dumps(data, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    target = data["sets"].get("target") or {}
    adm = target.get("admission") or {}
    undo = session["undo"] if isinstance(session["undo"], dict) else {}
    line = "H1 %s: header %s | helpers %r | undo %r redo %r | errors %s | written" % (
        step, (target.get("header") or {}).get("status"), adm.get("helpers", adm.get("error")),
        undo.get("undo_desc"), undo.get("redo_desc"), data["errors"] or "none")
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)
    return data


if __name__ != "h1_capture_under_test":
    h1_capture(globals())
