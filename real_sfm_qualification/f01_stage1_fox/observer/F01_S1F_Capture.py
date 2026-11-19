# -*- coding: ascii -*-
"""F-01 Stage 1: the native Fox structural-rig qualification, state capture. STRICTLY READ-ONLY. Run from SFM's
Script Editor (Python 2.7) with CPM open, after the setup line:

    S1F_DIR = r"<Q>"; S1F_SOURCE = "<Fox S set>"; S1F_TARGET = "<Fox D set>"; S1F_PEER = "foxmccouldwm1"
    S1F_STEP = "PREP"; execfile(r"<REPO>\\real_sfm_qualification\\f01_stage1_fox\\observer\\F01_S1F_Capture.py")

For the three named animation sets of the current shot it records, through the loaded CPM's own read-only functions
(prod_body_live, prod_pose_channel_authored, prod_pose_transform_state, prod_pose_time_read, prod_body_discover,
prod_body_rig_draft, prod_body_classify):
- every channel of the set's channels clip: a digest of its complete authored state (this process's handles
  included), a handle-free content digest and a handle-free frame digest without key values (comparable across SFM
  processes), its destination and every key;
- every bone's and rig handle's local and absolute transform, and the model's;
- CPM's structural rig admission: the drafted description (placement, helpers, handle and constraint counts), the
  bone classes and the role of every channel, or the refusal;
and the session (shot, playhead, timeline mode, Undo/Redo descriptions, document), the loaded CPM build, its
qualification fault slot and the selected pose. It clicks nothing, selects nothing, never touches the scene or the
library and never evaluates or refreshes. Its only write is <S1F_DIR>\\observations\\S1F-<step>.json (exclusive create).
"""
import hashlib
import json
import os
import sys

FORMAT = "F01-S1F-capture-v1"
STEPS = ("PREP", "SAVED", "BASE", "APPLY", "NAV", "UNDO", "REDO", "NOOP", "UNDO2", "ABORT")
ROLES = ("source", "target", "peer")


def s1f_text(v):
    try:
        return v if isinstance(v, type(u"")) else v.decode("utf-8", "replace") if isinstance(v, bytes) else \
            type(u"")(v)
    except Exception:
        return repr(v)


def s1f_try(fn):
    try:
        return fn()
    except Exception as exc:
        return {"error": repr(exc), "code": getattr(exc, "code", None)}


def s1f_digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=repr).encode("utf-8")).hexdigest()


def s1f_strip(obj):
    """The authored state without this process's element handles (comparable after a restart)."""
    if isinstance(obj, dict):
        return dict((k, s1f_strip(v)) for k, v in obj.items() if k != u"handle")
    if isinstance(obj, list):
        return [s1f_strip(v) for v in obj]
    return obj


def s1f_frame(stripped):
    """The handle-free authored state with key times but without key values (run 2: SFM's own session reload may
    round a quaternion key by one float32 step; the values are compared separately, within that step only)."""
    out = dict(stripped)
    out[u"layers"] = [dict(layer, keys=[k[0] for k in layer.get(u"keys") or []]) for layer in
                      stripped.get(u"layers") or []]
    return out


def s1f_state(cpm, dag):
    s = cpm.prod_pose_transform_state(dag)
    return [list(s[u"local_position"]), list(s[u"local_orientation"]), list(s[u"world_position"]),
            list(s[u"world_orientation"])]


def s1f_admission(cpm, L):
    t = cpm.prod_pose_time_read(L, cpm.prod_body_rig_time_names(L))
    D = cpm.prod_body_discover(L, t[u"t_chan"], cpm.prod_pose_writer_index())
    P = cpm.prod_body_rig_draft(D)
    C = cpm.prod_body_classify(D, P)
    classes = {}
    for n, c in C[u"bones"].items():
        classes[c] = classes.get(c, 0) + 1
    return {"t_chan": t[u"t_chan"], "rig_name": s1f_text(P[u"rig_name"]),
            "placement": s1f_text(P[u"placement_handle"]), "helpers": [s1f_text(h) for h in P[u"helper_handles"]],
            "handles": len(P[u"handles"]), "constraints": len(P[u"constraints"]),
            "preserved_handle_channels": sorted(s1f_text(n) for n in P[u"preserved_handle_channels"]),
            "classes": classes, "bone_classes": dict((s1f_text(n), c) for n, c in C[u"bones"].items()),
            "roles": dict((s1f_text(n), r) for n, r in C[u"channels"].items()),
            "written": [s1f_text(n) for n in C[u"written"]],
            "description_sha256": s1f_digest(dict((k, v) for k, v in P.items() if k != u"rig_name"))}


def s1f_set(cpm, shot, animset, keys):
    out = {"name": s1f_text(animset.GetName()), "errors": []}
    gm = cpm.get_game_model(animset)
    if gm is None:
        out["errors"].append("no game model")
        return out
    out["model"] = s1f_text(cpm.prod_pose_attr(gm, u"modelName"))
    row = {"shot": shot, "animset": animset, "gm": gm}
    L = cpm.prod_body_live(row, None)
    budget = [0]
    channels = {}
    for ch in L[u"clip_channels"]:
        authored = cpm.prod_pose_channel_authored(ch, budget)
        to = (authored.get(u"binding") or {}).get(u"toElement") or {}
        target = to.get(u"value") if isinstance(to, dict) else None
        stripped = s1f_strip(authored)
        row_ = {"sha256": s1f_digest(authored), "content": s1f_digest(stripped), "frame": s1f_digest(
            s1f_frame(stripped)),
                "to": s1f_text(target.get(u"name")) if isinstance(target, dict) else None,
                "to_type": s1f_text(target.get(u"type")) if isinstance(target, dict) else None,
                "to_attribute": s1f_text(((authored.get(u"binding") or {}).get(u"toAttribute") or {}).get(u"value"))}
        row_["keys"] = [layer.get(u"keys") for layer in authored.get(u"layers") or []]
        channels[s1f_text(ch.GetName())] = row_
    out["channels"] = channels
    out["keys"] = budget[0]
    out["bones"] = dict((s1f_text(n), s1f_state(cpm, b[u"dag"])) for n, b in L[u"bones"].items())
    out["handles"] = dict((s1f_text(n), s1f_state(cpm, dag)) for n, dag in L[u"rig_handles"].items())
    out["model_state"] = s1f_state(cpm, gm)
    out["admission"] = s1f_try(lambda: s1f_admission(cpm, L))
    return out


def s1f_selected_pose(cpm):
    from PySide import QtGui
    app = QtGui.QApplication.instance()
    win = getattr(app, getattr(cpm, "PROD_APP_ATTR", ""), None) if app is not None else None
    if win is None or not hasattr(win, "selected_pose"):
        return None
    item = win.selected_pose()
    if not isinstance(item, dict):
        return None
    pose = (item.get(u"record") or {}).get(u"pose") or {}
    region = (pose.get(u"regions") or {}).get(u"full_body") or {}
    return {"name": s1f_text(item.get(u"name")), "preset_id": item.get(u"preset_id"), "version": pose.get(u"version"),
            "adapter": pose.get(u"adapter"), "regions": sorted(pose.get(u"regions") or []),
            "model": (pose.get(u"source") or {}).get(u"model_ref"),
            "exclusions": region.get(u"exclusions"), "written": len(region.get(u"positions") or {}) +
            len(region.get(u"orientations") or {})}


def s1f_capture(g):
    root, step = g.get("S1F_DIR"), g.get("S1F_STEP")
    names = dict((r, g.get("S1F_" + r.upper())) for r in ROLES)
    if not root or step not in STEPS or not all(names.values()) or len(set(names.values())) != 3:
        raise RuntimeError("Set S1F_DIR, S1F_SOURCE, S1F_TARGET, S1F_PEER (three different animation sets) and "
                           "S1F_STEP (one of %s) first; nothing was written." % ", ".join(STEPS))
    path = os.path.join(root, "observations", "S1F-%s.json" % step)
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
            "registry_mode": getattr(cpm, "PROD_POSE_REGISTRY_MODE", None),
            "qualification_fault": list(getattr(cpm, "PROD_POSE_QUAL_FAULT", None) or []),
            "names": names, "sets": {}, "errors": []}
    shot = sfmApp.GetShotAtCurrentTime()
    session = {"undo": s1f_try(lambda: {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()),
                                        "undo_desc": s1f_text(dm.GetUndoDesc()),
                                        "redo_desc": s1f_text(dm.GetRedoDesc())}),
               "head_seconds": s1f_try(lambda: float(sfmApp.GetHeadTimeInSeconds())),
               "timeline_mode": s1f_try(lambda: int(sfmApp.GetTimelineMode())),
               "shot": s1f_try(lambda: s1f_text(shot.GetName())),
               "document": s1f_try(lambda: s1f_text(dm.GetFileName(sfmApp.GetDocumentRoot().GetFileId())))}
    data["session"] = session
    sets = list(cpm.prod_pose_seq(cpm.prod_pose_attr(shot, u"animationSets"))) if shot is not None else []
    data["animation_sets"] = sorted(s1f_text(a.GetName()) for a in sets)
    for role in ROLES:
        found = [a for a in sets if s1f_text(a.GetName()) == names[role]]
        if len(found) != 1:
            data["errors"].append("%s: %d animation sets named %r" % (role, len(found), names[role]))
            continue
        try:
            data["sets"][role] = s1f_set(cpm, shot, found[0], keys=True)
        except Exception as exc:
            data["errors"].append("%s: %r" % (role, exc))
    data["selected_pose"] = s1f_try(lambda: s1f_selected_pose(cpm))
    payload = json.dumps(data, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    adm = dict((r, (data["sets"].get(r) or {}).get("admission") or {}) for r in ROLES)
    undo = session["undo"] if isinstance(session["undo"], dict) else {}
    line = "S1F %s: Fox S %s | Fox D %s | peer %s | undo %r redo %r | errors %s | written" % (
        step, adm["source"].get("placement") or adm["source"].get("code") or "refused",
        adm["target"].get("placement") or adm["target"].get("code") or "refused",
        adm["peer"].get("placement") or adm["peer"].get("code") or "refused",
        undo.get("undo_desc"), undo.get("redo_desc"), data["errors"] or "none")
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)
    return data


if __name__ != "s1f_capture_under_test":
    s1f_capture(globals())
