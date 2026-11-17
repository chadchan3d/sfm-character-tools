# -*- coding: ascii -*-
"""F-01 OT1S: the minimal native integration smoke check of the integrated OT1 candidate (production reference guard;
Designer "F-01 - OT1 Integrated Candidate: Final Qualification"). Run from SFM's Script Editor (Python 2.7) with
Character Preset Manager open:

    OT1S_DIR = r"<run folder>"; OT1S_REPO = r"<repo>"
    OT1S_STEP = "BASE"; execfile(OT1S_REPO + r"\\real_sfm_qualification\\f01_ot1_integration_smoke\\observer\\F01_OT1S_Observe.py")

READ-ONLY with respect to the scene, the library and CPM's decisions. It reuses, unchanged:
- the pinned OT1 observer (F01_OT1_Observe.py, OT1_OBSERVER_SHA256): its recording hooks (prod_apply,
  prod_bs_write_existing_scale, same_time_refresh, prod_bs_index_verify_saved, prod_verify_apply_abort_baseline)
  and its loader of the pinned Q1 observer (raw animation-set fields, the settled full map); its own capture, BASE
  preflight and controlled-failure injector are not used and never armed;
- one added pass-through hook on the production guard prod_bs_expression_reference_guard: it calls the original with
  the same argument, returns its result unchanged (re-raises an exception unchanged) and records the bone and outcome,
  so the analyzer can show the guard accepted each expression before StartUndo and again before Operate().

Its only write is <OT1S_DIR>\\observations\\OT1S-<step>.json (exclusive create).

Steps: BASE (peer created, A selected; installs the hooks), APPLY (after Apply Body), UNDO (after Edit > Undo), REDO
(after Edit > Redo), UNDO2 (after Edit > Undo; removes the hooks).
"""
import hashlib
import json
import os
import sys
import time

OT1S_STEPS = ("BASE", "APPLY", "UNDO", "REDO", "UNDO2")
OT1S_GUARD = "prod_bs_expression_reference_guard"
OT1S_STATE = "_f01_ot1s_guard"
OT1S_RECORD = u"Body"
OT1_OBSERVER_SHA256 = "5a13708a743dda327e0b9cdd4666d401f8784f33165a07fc3f33fcad0fb6e0d6"


def ot1s_ot1(repo):
    """The OT1 observer's functions, verified by SHA-256, loaded without running its capture."""
    path = os.path.join(repo, "real_sfm_qualification", "f01_ot1_ordering_trial", "observer", "F01_OT1_Observe.py")
    with open(path, "rb") as f:
        raw = f.read()
    if hashlib.sha256(raw).hexdigest() != OT1_OBSERVER_SHA256:
        raise RuntimeError("The OT1 observer is not the pinned %s." % OT1_OBSERVER_SHA256)
    g = {"__name__": "ot1_observer_under_test"}
    exec(compile(raw, path, "exec"), g)
    return g


def ot1s_install(cpm, o, q1):
    """The OT1 recording hooks, then the pass-through guard hook (once per SFM process)."""
    st = o["ot1_install"](cpm, q1)
    if getattr(cpm, OT1S_STATE, None) is not None:
        return st
    original = getattr(cpm, OT1S_GUARD)
    text = q1["q1_text"]

    def hooked_guard(item):
        bone = None
        try:
            bone = text((item or {}).get("bone_name"))
        except Exception:
            pass
        try:
            result = original(item)
        except Exception:
            info = sys.exc_info()
            o["ot1_record"](st, "reference-guard", bone=bone, result=None, error=repr(info[1]))
            q1["q1_reraise"](info)
        o["ot1_record"](st, "reference-guard", bone=bone, result=q1["q1_plain"](result), error=None)
        return result
    hooked_guard.ot1s_original = original
    setattr(cpm, OT1S_GUARD, hooked_guard)
    setattr(cpm, OT1S_STATE, original)
    return st


def ot1s_uninstall(cpm, o):
    original = getattr(cpm, OT1S_STATE, None)
    if original is not None:
        setattr(cpm, OT1S_GUARD, original)
        delattr(cpm, OT1S_STATE)
    ok = o["ot1_uninstall"](cpm)
    return bool(ok and getattr(getattr(cpm, OT1S_GUARD), "ot1s_original", None) is None)


def ot1s_capture(g):
    root, step, repo = g.get("OT1S_DIR"), g.get("OT1S_STEP"), g.get("OT1S_REPO")
    if not root or not repo or step not in OT1S_STEPS:
        raise RuntimeError("Set OT1S_DIR, OT1S_REPO and OT1S_STEP (one of %s) first; see the docstring."
                           % ", ".join(OT1S_STEPS))
    path = os.path.join(root, "observations", "OT1S-%s.json" % step)
    if os.path.exists(path):
        raise RuntimeError("%s exists; each step is captured once." % path)
    o = ot1s_ot1(repo)
    q1 = o["ot1_q1"](repo)
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
    if step != "BASE" and getattr(cpm, OT1S_STATE, None) is None:
        raise RuntimeError("The hooks are not installed in this SFM process: capture BASE first.")
    import sfmApp
    import vs
    dm = vs.g_pDataModel
    text, plain = q1["q1_text"], q1["q1_plain"]
    data = {"format": "F01-OT1S-capture-v1", "step": step, "pid": os.getpid(), "time": time.time(),
            "cpm_build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__", None), "errors": {},
            "ot1_observer_sha256": OT1_OBSERVER_SHA256}

    def attempt(key, fn):
        try:
            data[key] = fn()
        except Exception as exc:
            data[key] = None
            data["errors"][key] = repr(exc)

    def undo():
        out = {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()), "undo_desc": text(dm.GetUndoDesc()),
               "redo_desc": text(dm.GetRedoDesc())}
        try:
            out["count"] = int(dm.GetUndoItemCount())
        except Exception:
            out["count"] = None
        return out
    attempt("session", lambda: {
        "document": text(dm.GetFileName(sfmApp.GetDocumentRoot().GetFileId())),
        "shot": text(sfmApp.GetShotAtCurrentTime().GetName()),
        "head_seconds": float(sfmApp.GetHeadTimeInSeconds()),
        "timeline_mode": text(sfmApp.GetNameForTimelineMode(sfmApp.GetTimelineMode())),
        "undo": undo()})
    identity = win.current() if hasattr(win, "current") else None
    token = getattr(win, "selection_token", None)
    attempt("character", lambda: dict((text(k), plain(x)) for k, x in (identity or {}).items()))
    attempt("instance", lambda: plain(cpm.prod_instance_token(token)))
    attempt("animation_sets", lambda: [q1["q1_raw_set"](a) for a in q1["q1_seq"](q1["q1_attr"](
        sfmApp.GetShotAtCurrentTime(), "animationSets"))])
    record = None
    for item in list(getattr(win, "body_items", None) or []):
        rec = (item or {}).get("record") or {}
        if text(rec.get("name")) == OT1S_RECORD:
            if record is not None:
                data["errors"]["record"] = "more than one Body record"
            record = rec
    data["record"] = None if record is None else {"preset_id": text(record.get("preset_id")),
                                                  "bone_scales": len(record.get("bone_scales") or [])}
    try:
        data["settled_full_map"] = (q1["q1_snapshot_map"](cpm, identity, token, record) if record is not None
                                    else {"error": "no Body record"})
    except Exception as exc:
        data["settled_full_map"] = {"error": repr(exc)}
    if step == "BASE":
        ot1s_install(cpm, o, q1)
        data["hooks_installed"] = sorted(
            [n for n in o["OT1_HOOKED"] if getattr(getattr(cpm, n), "ot1_original", None) is not None] +
            ([OT1S_GUARD] if getattr(getattr(cpm, OT1S_GUARD), "ot1s_original", None) is not None else []))
    st = o["ot1_state"](cpm)
    data["events"] = o["ot1_events_payload"](st)
    if st is not None:
        del st["events"][:]
        data["injector"] = {"armed": st["armed"], "fired": st["fired"]}
    if step == "UNDO2":
        data["hooks_removed"] = ot1s_uninstall(cpm, o)
    payload = json.dumps(data, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    fm = data["settled_full_map"] or {}
    guards = [e for e in data["events"] if e.get("kind") == "reference-guard"]
    line = "OT1S %s: %d events | settled map Body %s | undo %r redo %r | guard %s | errors %s | written" % (
        step, len(data["events"]), {True: "PASS", False: "FAIL"}.get(fm.get("result"), "UNREADABLE"),
        ((data.get("session") or {}).get("undo") or {}).get("undo_desc"),
        ((data.get("session") or {}).get("undo") or {}).get("redo_desc"),
        ("%d accepted, %d refused" % (sum(1 for e in guards if e.get("error") is None),
                                      sum(1 for e in guards if e.get("error") is not None))) if guards else "-",
        sorted(data["errors"]) or "none")
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


if __name__ != "ot1s_observer_under_test":
    ot1s_capture(globals())
