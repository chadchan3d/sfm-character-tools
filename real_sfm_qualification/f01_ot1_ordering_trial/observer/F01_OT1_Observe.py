# -*- coding: ascii -*-
"""F-01 OT1: the ordering trial's observer (Astra adjudication, ACCEPT WITH CONDITIONS; qualification only). Run from
SFM's Script Editor (Python 2.7) with Character Preset Manager open:

    OT1_DIR = r"<run folder>"; OT1_REPO = r"<repo>"
    OT1_STEP = "BASE"; execfile(OT1_REPO + r"\\real_sfm_qualification\\f01_ot1_ordering_trial\\observer\\F01_OT1_Observe.py")

It reuses, unchanged, the pinned Q1 observer's read-only functions (full saved-scale map with CPM's own predicates,
raw animation-set fields, plain JSON forms): F01_Q1_Observe.py is loaded only when its SHA-256 equals Q1_OBSERVER_SHA256
and never runs its own capture.

1. Hooks (installed by BASE, removed by ABORT; they live only in this SFM process). Each wrapper calls the original
   with the same arguments and returns its result unchanged (an exception is re-raised unchanged); it only records:
   - prod_apply: the operation and its outcome;
   - prod_bs_write_existing_scale: CPM's prod_bs_snapshot of the scale's binding immediately before and immediately
     after CPM's own write (inside the owned transaction, after the candidate's expression Operate(); the same
     read-only snapshot CPM itself takes there): the "precommit" read;
   - same_time_refresh: after CPM's existing refresh, the same snapshot of each scale written by the operation (the
     lightweight "after the refresh" read; nothing is read before the refresh);
   - prod_bs_index_verify_saved: after CPM's own deferred check returns, the full saved map on the snapshot CPM used;
   - prod_verify_apply_abort_baseline: its result (CPM's own abort verification).
2. The one controlled failure (armed by ARM; fires at most once): when the armed hook sees CPM's write of
   OT1_FAIL_BONE return normally (its input written and its expression operated and verified by the candidate), it
   records the event and raises RuntimeError("OT1 controlled failure after the operator call") from inside the owned
   transaction, so CPM's own abort-and-verify path runs. Nothing else is injected, retried, refreshed or undone.
3. Captures (each step once): session (document, shot, time, Undo/Redo descriptions and count), the selected
   character and instance, the raw fields of every animation set in the shot (Q1's reader), the settled full map of
   the selected instance against the `Body` record, and the hook events since the previous capture.

Its only write is <OT1_DIR>\\observations\\OT1-<step>.json (exclusive create).

Steps: BASE (peer created, A selected; installs the hooks), APPLY (after Apply Body), UNDO (after Ctrl+Z), REDO (after
Ctrl+Y), UNDO2 (after Ctrl+Z), ARM (arms the controlled failure), ABORT (after the second Apply Body and its error
message; removes the hooks).
"""
import hashlib
import json
import os
import sys
import time

OT1_STEPS = ("BASE", "APPLY", "UNDO", "REDO", "UNDO2", "ARM", "ABORT")
OT1_HOOKED = ("prod_apply", "prod_bs_write_existing_scale", "same_time_refresh", "prod_bs_index_verify_saved",
              "prod_verify_apply_abort_baseline")
OT1_STATE = "_f01_ot1_state"
OT1_RECORD = u"Body"
OT1_FAIL_BONE = u"bip_tail00"
OT1_FAIL_TEXT = "OT1 controlled failure after the operator call"
Q1_OBSERVER_SHA256 = "f2eba1e0abce6e1e1e68202546e750b99dc0032f105d393bf0a40111824fca58"
SNAP_FIELDS = ("source", "key_value", "key_count", "expr_input", "expr_result", "physical_scale", "input_mode",
               "output_mode", "output_key_count", "output_is_empty", "output_use_default_value", "lo", "hi",
               "expression_id", "output_id", "transform_id", "input_channel_id", "control_id")


def ot1_q1(repo):
    """The Q1 observer's functions, verified by SHA-256, loaded without running its capture."""
    path = os.path.join(repo, "real_sfm_qualification", "f01_q1_ps2_diagnostic", "observer", "F01_Q1_Observe.py")
    with open(path, "rb") as f:
        raw = f.read()
    if hashlib.sha256(raw).hexdigest() != Q1_OBSERVER_SHA256:
        raise RuntimeError("The Q1 observer is not the pinned %s." % Q1_OBSERVER_SHA256)
    g = {"__name__": "q1_observer_under_test"}
    exec(compile(raw, path, "exec"), g)
    return g


def ot1_state(cpm):
    return getattr(cpm, OT1_STATE, None)


def ot1_record(st, kind, **fields):
    try:
        st["seq"] += 1
        fields.update(seq=st["seq"], kind=kind, time=time.time())
        st["events"].append(fields)
    except Exception:
        pass


def ot1_snap(cpm, q1, binding):
    """CPM's own read-only prod_bs_snapshot of a binding, reduced to the fields the trial compares."""
    try:
        s = cpm.prod_bs_snapshot(binding)
        return dict((k, q1["q1_plain"](s.get(k))) for k in SNAP_FIELDS)
    except Exception as exc:
        return {"error": repr(exc)}


def ot1_install(cpm, q1):
    """Install the five recording wrappers once per SFM process. Returns the state."""
    st = ot1_state(cpm)
    if st is not None:
        return st
    st = {"events": [], "originals": dict((n, getattr(cpm, n)) for n in OT1_HOOKED), "op": None, "seq": 0,
          "written": [], "armed": False, "fired": 0, "installed_at": time.time()}
    orig = st["originals"]
    text = q1["q1_text"]
    plain = q1["q1_plain"]
    reraise = q1["q1_reraise"]

    def hooked_apply(identity, record, *args, **kwargs):
        prev = st["op"]
        try:
            st["op"] = {"identity": dict(identity), "record": json.loads(json.dumps(record)),
                        "context": kwargs.get("operation_context")}
            st["written"] = []
            ot1_record(st, "apply-begin", preset=text(record.get("name")), preset_kind=text(record.get("kind")),
                       identity=plain(dict(identity)),
                       instance=plain(cpm.prod_instance_token(kwargs.get("operation_context"))))
        except Exception:
            pass
        try:
            result = orig["prod_apply"](identity, record, *args, **kwargs)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "apply-raised", error=repr(info[1]), error_type=type(info[1]).__name__)
            st["op"] = prev
            reraise(info)
        st["op"] = prev
        ot1_record(st, "apply-returned", result=plain(result))
        return result

    def hooked_write(item, *args, **kwargs):
        binding = (item or {}).get("binding")
        bone = text((item or {}).get("bone_name"))
        before = ot1_snap(cpm, q1, binding)
        try:
            result = orig["prod_bs_write_existing_scale"](item, *args, **kwargs)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "scale-write-raised", bone=bone, error=repr(info[1]), before=before,
                       after=ot1_snap(cpm, q1, binding))
            reraise(info)
        after = ot1_snap(cpm, q1, binding)
        try:
            st["written"].append(binding)
        except Exception:
            pass
        ot1_record(st, "scale-write", bone=bone, desired_native=plain(item.get("desired_native")),
                   desired_physical=plain(item.get("desired_physical")),
                   static_output_mode=plain((binding or {}).get("static_output_mode")), before=before, after=after)
        if st["armed"] and bone == OT1_FAIL_BONE and st["fired"] == 0:
            st["armed"] = False
            st["fired"] += 1
            ot1_record(st, "injected-failure", bone=bone, text=OT1_FAIL_TEXT)
            raise RuntimeError(OT1_FAIL_TEXT)
        return result

    def hooked_refresh(head_time, label):
        try:
            result = orig["same_time_refresh"](head_time, label)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "refresh-raised", label=text(label), error=repr(info[1]))
            reraise(info)
        rows = []
        for binding in list(st["written"]):
            rows.append({"bone": text(((binding or {}).get("identity") or {}).get("bone_name")),
                         "after": ot1_snap(cpm, q1, binding)})
        ot1_record(st, "refresh-after", label=text(label), head_time=plain(head_time), scales=rows)
        return result

    def hooked_verify(record, snapshot):
        try:
            result = orig["prod_bs_index_verify_saved"](record, snapshot)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "deferred-verify-raised", error=repr(info[1]))
            reraise(info)
        try:
            fm = q1["q1_full_map"](cpm, record, snapshot)
            ot1_record(st, "deferred-verify", result=bool(result), record=text(record.get("name")), full_map=fm,
                       consistent=(fm.get("result") == bool(result)))
        except Exception as exc:
            ot1_record(st, "deferred-verify", result=bool(result), record=text(record.get("name")),
                       full_map={"error": repr(exc)}, consistent=None)
        return result

    def hooked_abort_verify(*args, **kwargs):
        try:
            result = orig["prod_verify_apply_abort_baseline"](*args, **kwargs)
        except Exception:
            info = sys.exc_info()
            ot1_record(st, "abort-verify-raised", error=repr(info[1]))
            reraise(info)
        ot1_record(st, "abort-verify", result=plain(result))
        return result

    wrappers = {"prod_apply": hooked_apply, "prod_bs_write_existing_scale": hooked_write,
                "same_time_refresh": hooked_refresh, "prod_bs_index_verify_saved": hooked_verify,
                "prod_verify_apply_abort_baseline": hooked_abort_verify}
    for name, fn in wrappers.items():
        fn.ot1_original = orig[name]
        setattr(cpm, name, fn)
    setattr(cpm, OT1_STATE, st)
    return st


def ot1_uninstall(cpm):
    """Restore the five original functions and disarm. Returns True when every original is back in place."""
    st = ot1_state(cpm)
    if st is None:
        return True
    st["armed"] = False
    for name, fn in st["originals"].items():
        setattr(cpm, name, fn)
    ok = all(getattr(cpm, n) is st["originals"][n] for n in OT1_HOOKED)
    if ok:
        delattr(cpm, OT1_STATE)
    return ok


def ot1_events_payload(st):
    if st is None:
        return []
    return json.loads(json.dumps(list(st["events"]), default=repr))


def ot1_capture(g):
    root, step, repo = g.get("OT1_DIR"), g.get("OT1_STEP"), g.get("OT1_REPO")
    if not root or not repo or step not in OT1_STEPS:
        raise RuntimeError("Set OT1_DIR, OT1_REPO and OT1_STEP (one of %s) first; see the docstring."
                           % ", ".join(OT1_STEPS))
    path = os.path.join(root, "observations", "OT1-%s.json" % step)
    if os.path.exists(path):
        raise RuntimeError("%s exists; each step is captured once." % path)
    q1 = ot1_q1(repo)
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
    if step != "BASE" and ot1_state(cpm) is None:
        raise RuntimeError("The hooks are not installed in this SFM process: capture BASE first.")
    import sfmApp
    import vs
    dm = vs.g_pDataModel
    text, plain = q1["q1_text"], q1["q1_plain"]
    data = {"format": "F01-OT1-capture-v1", "step": step, "pid": os.getpid(), "time": time.time(),
            "cpm_build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__", None), "errors": {},
            "q1_observer_sha256": Q1_OBSERVER_SHA256}

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
        if text(rec.get("name")) == OT1_RECORD:
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
        st = ot1_install(cpm, q1)
        data["hooks_installed"] = sorted(n for n in OT1_HOOKED if getattr(getattr(cpm, n), "ot1_original", None)
                                         is st["originals"][n])
    st = ot1_state(cpm)
    data["events"] = ot1_events_payload(st)
    if st is not None:
        del st["events"][:]
        data["injector"] = {"armed": st["armed"], "fired": st["fired"]}
    if step == "ARM":
        if st["fired"] != 0 or st["armed"]:
            raise RuntimeError("The controlled failure was already armed or fired; nothing written.")
        st["armed"] = True
        data["injector"] = {"armed": True, "fired": 0, "bone": OT1_FAIL_BONE}
    if step == "ABORT":
        data["hooks_removed"] = ot1_uninstall(cpm)
    payload = json.dumps(data, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    fm = data["settled_full_map"] or {}
    line = "OT1 %s: %d events | settled map Body %s | undo %r redo %r | injector %s | errors %s | written" % (
        step, len(data["events"]), {True: "PASS", False: "FAIL"}.get(fm.get("result"), "UNREADABLE"),
        ((data.get("session") or {}).get("undo") or {}).get("undo_desc"),
        ((data.get("session") or {}).get("undo") or {}).get("redo_desc"),
        data.get("injector"), sorted(data["errors"]) or "none")
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


if __name__ != "ot1_observer_under_test":
    ot1_capture(globals())
