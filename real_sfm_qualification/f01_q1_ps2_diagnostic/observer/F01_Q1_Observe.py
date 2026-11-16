# -*- coding: ascii -*-
"""F-01 Q1: the PS-2 Body Preset scale-verification and duplicate-model Undo diagnostic observer. Run from SFM's Script
Editor (Python 2.7) with Character Preset Manager open:

    Q1_DIR = r"<run folder>"; Q1_REPO = r"<repo>"
    Q1_STEP = "BASE"; execfile(Q1_REPO + r"\\real_sfm_qualification\\f01_q1_ps2_diagnostic\\observer\\F01_Q1_Observe.py")

READ-ONLY with respect to the scene, the library and CPM's decisions. Two parts:

1. Hooks (installed by the BASE step, removed by the DUP-UNDO step; they live only in this SFM process). Four CPM
   functions are wrapped. Each wrapper calls the original with the same arguments and returns its result unchanged (an
   exception is re-raised unchanged); it only records, in memory, what CPM computed:
   - prod_apply: the operation (preset, kind, model, animation set) and its outcome;
   - prod_bs_authored_matches: CPM's precommit check of each changed scale (its snapshot, the desired native value,
     the result);
   - same_time_refresh: the complete saved-scale map of the operation's character, evaluated with CPM's own
     functions immediately before and immediately after the existing refresh (the refresh itself is unchanged);
   - prod_bs_index_verify_saved: after CPM's own deferred check returns, the same complete map on the same snapshot
     CPM used (every bone, not only the first failure), and whether that recomputation agrees with CPM's result.
   The map's reads are the same read-only DataModel reads CPM's verification makes, in the same Python call, with no
   event processing of their own. Nothing is retried, refreshed, delayed or undone by the observer.
2. Captures (each step once): the raw (unrounded) fields of every animation set in the current shot (control values;
   game-model bone positions, orientations and scales; global flex weights; model visibility, skin and body group and
   direct child visibility), the session (document, shot, time, timeline mode, Undo and Redo descriptions), the
   selected character and instance, the complete saved-scale map of the selected instance against the pinned Body and
   PS2 Dup Body records (the settled values), and the hook events recorded since the previous capture.

Its only write is <Q1_DIR>\\observations\\Q1-<step>.json (exclusive create).

Steps: BASE (installs the hooks), BODY (after Apply Body), HAPPY (only when BODY's settled map fails; after Apply
Happy), DUP-BEFORE (instance B created, A selected), DUP-APPLY (after Apply PS2 Dup Body to A), DUP-UNDO (after one
Undo; removes the hooks).
"""
import json
import os
import sys
import time

Q1_STEPS = ("BASE", "BODY", "HAPPY", "DUP-BEFORE", "DUP-APPLY", "DUP-UNDO")
Q1_HOOKED = ("prod_apply", "prod_bs_authored_matches", "same_time_refresh", "prod_bs_index_verify_saved")
Q1_STATE = "_f01_q1_state"
Q1_RECORDS = (u"Body", u"PS2 Dup Body")
Q1_MAX = 4096

if sys.version_info[0] == 2:
    exec("def q1_reraise(info):\n    raise info[0], info[1], info[2]\n")
else:
    def q1_reraise(info):
        raise info[1].with_traceback(info[2])


def q1_text(v):
    try:
        return v if isinstance(v, unicode) else str(v).decode("utf-8", "replace")  # noqa: F821 (Python 2.7)
    except NameError:
        return str(v)


def q1_plain(v, depth=0):
    """A JSON form of native values, unrounded: element references as {element, handle, type}; vectors as lists;
    dicts and sequences recursively (bounded); anything else by text."""
    if v is None or isinstance(v, (bool, int, float)):
        return v
    try:
        if isinstance(v, long):  # noqa: F821 (Python 2.7)
            return int(v)
    except NameError:
        pass
    if isinstance(v, (str,)) or type(v).__name__ == "unicode":
        return q1_text(v)
    if depth > 6:
        return u"<depth>"
    if hasattr(v, "GetHandle") and hasattr(v, "GetName"):
        try:
            return {"element": q1_text(v.GetName()), "handle": int(v.GetHandle()),
                    "type": q1_text(v.GetTypeString()) if hasattr(v, "GetTypeString") else None}
        except Exception:
            return u"<element>"
    for keys in (("x", "y", "z", "w"), ("x", "y", "z")):
        if all(hasattr(v, k) for k in keys):
            try:
                return [float(getattr(v, k)) for k in keys]
            except Exception:
                break
    if isinstance(v, dict):
        out = {}
        for i, (k, x) in enumerate(v.items()):
            if i >= Q1_MAX:
                out[u"<truncated>"] = len(v)
                break
            out[q1_text(k) if not isinstance(k, tuple) else u"|".join(q1_text(p) for p in k)] = q1_plain(x, depth + 1)
        return out
    if isinstance(v, (list, tuple, set, frozenset)):
        items = list(v)
        return [q1_plain(x, depth + 1) for x in items[:Q1_MAX]]
    return q1_text(v)


def q1_trace_fields(trace):
    """The trace fields the verification predicates read, plus every other plain field of the trace."""
    out = {}
    for k, x in (trace or {}).items():
        if isinstance(k, (str,)) or type(k).__name__ == "unicode":
            if k.startswith("_"):
                continue
        out[q1_text(k)] = q1_plain(x)
    return out


def q1_full_map(cpm, record, snapshot):
    """CPM's full saved-scale verification (prod_bs_index_verify_saved), evaluated for EVERY saved bone with CPM's own
    functions, recording each bone's predicates. result equals what CPM's function returns; would_raise marks where
    CPM's function would have raised instead (a validation or trace error before any failure)."""
    out = {"record": q1_text(record.get("name")), "validate_error": None, "bones": [], "result": None,
           "first_failure": None, "would_raise": False}
    try:
        cpm.prod_bs_index_validate_saved_map(record.get("bone_scales"), snapshot)
    except Exception as exc:
        out["validate_error"] = repr(exc)
        out["would_raise"] = True
        return out
    saved = cpm.prod_bs_bone_record_index(record)
    current = snapshot["bone_index"]
    result = True
    for key in saved:
        desired = float(saved[key]["value"])
        entry = {"bone_index": int(key[0]), "bone": q1_text(key[1]), "desired": desired, "ok": None,
                 "predicate": None}
        row = current.get(key)
        if row is None:
            entry.update(ok=False, predicate=u"missing-row")
        else:
            cls = q1_text(row.get("classification"))
            entry["classification"] = cls
            if cls == u"IMPLICIT_NEUTRAL":
                entry.update(ok=bool(cpm.close_enough(desired, 1.0)), predicate=u"implicit-neutral")
            elif cls != u"CHANNEL_DRIVEN_SCALE":
                entry.update(ok=False, predicate=u"classification")
            else:
                try:
                    trace = cpm.prod_bs_index_trace(snapshot, row)
                except Exception as exc:
                    entry.update(ok=False, predicate=u"trace-error", error=repr(exc))
                    trace = None
                if trace is not None:
                    static = cpm.prod_bs_classify_static_scale(trace)
                    entry["static"] = [q1_plain(static[0]), q1_plain(static[1]), q1_plain(static[2])]
                    entry["trace"] = q1_trace_fields(trace)
                    physical = trace.get("physical_scale")
                    entry["physical"] = q1_plain(physical)
                    if static[0] is None:
                        entry.update(ok=False, predicate=u"static")
                    else:
                        entry.update(ok=bool(cpm.close_enough(physical, desired)), predicate=u"physical")
                    try:
                        entry["delta"] = float(physical) - desired
                    except Exception:
                        entry["delta"] = None
        if not entry["ok"]:
            if out["first_failure"] is None:
                out["first_failure"] = {"bone": entry["bone"], "bone_index": entry["bone_index"],
                                        "predicate": entry["predicate"]}
                if entry["predicate"] in (u"missing-row", u"trace-error") and result:
                    out["would_raise"] = True
            result = False
        out["bones"].append(entry)
    out["result"] = result
    return out


def q1_state(cpm):
    return getattr(cpm, Q1_STATE, None)


def q1_record_event(st, kind, **fields):
    try:
        st["seq"] += 1
        fields.update(seq=st["seq"], kind=kind, time=time.time())
        st["events"].append(fields)
    except Exception:
        pass


def q1_snapshot_map(cpm, identity, context, record):
    """A fresh snapshot of the instance (CPM's own read-only prod_bs_index_snapshot) and the full map against record."""
    snapshot = cpm.prod_bs_index_snapshot(identity, **cpm.prod_instance_kw(context))
    try:
        return q1_full_map(cpm, record, snapshot)
    finally:
        if isinstance(snapshot, dict):
            snapshot.clear()


def q1_install(cpm):
    """Install the four recording wrappers once per SFM process. Returns the state."""
    st = q1_state(cpm)
    if st is not None:
        return st
    st = {"events": [], "originals": dict((n, getattr(cpm, n)) for n in Q1_HOOKED), "op": None,
          "last_body": None, "seq": 0, "installed_at": time.time()}
    orig = st["originals"]

    def hooked_apply(identity, record, *args, **kwargs):
        prev = st["op"]
        try:
            kind = q1_text(record.get("kind"))
            st["op"] = {"identity": dict(identity), "record": json.loads(json.dumps(record)),
                        "context": kwargs.get("operation_context")}
            if kind == u"body":
                st["last_body"] = st["op"]
            q1_record_event(st, "apply-begin", preset=q1_text(record.get("name")), preset_kind=kind,
                            identity=q1_plain(dict(identity)),
                            instance=q1_plain(cpm.prod_instance_token(kwargs.get("operation_context"))))
        except Exception:
            pass
        try:
            result = orig["prod_apply"](identity, record, *args, **kwargs)
        except Exception:
            info = sys.exc_info()
            q1_record_event(st, "apply-raised", error=repr(info[1]))
            st["op"] = prev
            q1_reraise(info)
        st["op"] = prev
        q1_record_event(st, "apply-returned", result=q1_plain(result))
        return result

    def hooked_authored(binding, snapshot, native_value):
        try:
            result = orig["prod_bs_authored_matches"](binding, snapshot, native_value)
        except Exception:
            info = sys.exc_info()
            q1_record_event(st, "precommit-authored-raised", error=repr(info[1]))
            q1_reraise(info)
        try:
            q1_record_event(st, "precommit-authored", result=bool(result), desired_native=q1_plain(native_value),
                            bone=q1_text((binding or {}).get("bone_name") or (binding or {}).get("portable_identity")),
                            snapshot=q1_plain(snapshot), binding=q1_plain(dict((k, x) for k, x in (binding or {}).items()
                                                                               if not str(k).startswith("_"))))
        except Exception:
            pass
        return result

    def hooked_refresh(head_time, label):
        op = st["op"] if st["op"] is not None else None
        body = st["last_body"]
        maps = {}

        def map_now(tag):
            try:
                if op is not None and body is not None:
                    maps[tag] = q1_snapshot_map(cpm, op["identity"], op["context"], body["record"])
            except Exception as exc:
                maps[tag] = {"error": repr(exc)}
        map_now("before")
        q1_record_event(st, "refresh-before", label=q1_text(label), head_time=q1_plain(head_time),
                        operation=q1_text(op["record"].get("name")) if op else None,
                        body_record=q1_text(body["record"].get("name")) if body else None, full_map=maps.get("before"))
        try:
            result = orig["same_time_refresh"](head_time, label)
        except Exception:
            info = sys.exc_info()
            q1_record_event(st, "refresh-raised", error=repr(info[1]))
            q1_reraise(info)
        map_now("after")
        q1_record_event(st, "refresh-after", label=q1_text(label), full_map=maps.get("after"))
        return result

    def hooked_verify(record, snapshot):
        try:
            result = orig["prod_bs_index_verify_saved"](record, snapshot)
        except Exception:
            info = sys.exc_info()
            fm = None
            try:
                fm = q1_full_map(cpm, record, snapshot)
            except Exception as exc:
                fm = {"error": repr(exc)}
            q1_record_event(st, "deferred-verify-raised", error=repr(info[1]), full_map=fm)
            q1_reraise(info)
        try:
            fm = q1_full_map(cpm, record, snapshot)
            q1_record_event(st, "deferred-verify", result=bool(result), record=q1_text(record.get("name")),
                            full_map=fm, consistent=(fm.get("result") == bool(result)))
        except Exception as exc:
            q1_record_event(st, "deferred-verify", result=bool(result), record=q1_text(record.get("name")),
                            full_map={"error": repr(exc)}, consistent=None)
        return result

    wrappers = {"prod_apply": hooked_apply, "prod_bs_authored_matches": hooked_authored,
                "same_time_refresh": hooked_refresh, "prod_bs_index_verify_saved": hooked_verify}
    for name, fn in wrappers.items():
        fn.q1_original = orig[name]
        setattr(cpm, name, fn)
    setattr(cpm, Q1_STATE, st)
    return st


def q1_uninstall(cpm):
    """Restore the four original functions. Returns True when every original is back in place."""
    st = q1_state(cpm)
    if st is None:
        return True
    for name, fn in st["originals"].items():
        setattr(cpm, name, fn)
    ok = all(getattr(cpm, n) is st["originals"][n] for n in Q1_HOOKED)
    if ok:
        delattr(cpm, Q1_STATE)
    return ok


def q1_attr(obj, name):
    if obj is None or not obj.HasAttribute(name):
        return None
    a = obj.GetAttribute(name)
    for method in ("GetValue", "GetValueUntyped"):
        try:
            return getattr(a, method)()
        except Exception:
            pass
    return None


def q1_seq(value):
    n = len(value) if value is not None else 0
    if n > Q1_MAX:
        raise RuntimeError("collection exceeds its bound (%d)" % n)
    return [value[i] for i in range(n)]


def q1_raw_set(animset):
    """The raw, unrounded fields of one animation set (read only)."""
    controls = {}
    for c in q1_seq(q1_attr(animset, "controls")):
        row = {}
        for name in ("value", "leftValue", "rightValue", "valuePosition", "valueOrientation"):
            v = q1_attr(c, name)
            if v is not None:
                row[name] = q1_plain(v)
        controls[q1_text(c.GetName())] = row
    gm = q1_attr(animset, "gameModel")
    model = None
    if gm is not None:
        bones = [[q1_text(t.GetName())] + [q1_plain(q1_attr(t, k)) for k in ("position", "orientation", "scale")]
                 for t in q1_seq(q1_attr(gm, "bones"))]
        flexes = [[q1_text(f.GetName()), q1_plain(q1_attr(f, "flexWeight"))]
                  for f in q1_seq(q1_attr(gm, "globalFlexControllers"))]
        children = [[q1_text(ch.GetName()), q1_plain(q1_attr(ch, "visible"))] for ch in q1_seq(q1_attr(gm, "children"))]
        model = {"model": q1_text(q1_attr(gm, "modelName")), "handle": int(gm.GetHandle()),
                 "visible": q1_plain(q1_attr(gm, "visible")), "skin": q1_plain(q1_attr(gm, "skin")),
                 "body": q1_plain(q1_attr(gm, "body")), "children": children, "bones": bones, "flexes": flexes}
    return {"name": q1_text(animset.GetName()), "handle": int(animset.GetHandle()), "controls": controls,
            "model": model}


def q1_events_payload(st):
    """The recorded events as written to a capture. Events are made plain when recorded (q1_plain, q1_full_map); a
    JSON round trip keeps their full depth. (Kit correction after Q1 run 1: sanitizing them a second time here cut the
    boundary maps' output-channel log rows at the depth bound.)"""
    if st is None:
        return []
    return json.loads(json.dumps(list(st["events"]), default=repr))


def q1_capture(g):
    root, step = g.get("Q1_DIR"), g.get("Q1_STEP")
    if not root or step not in Q1_STEPS:
        raise RuntimeError("Set Q1_DIR and Q1_STEP (one of %s) first; see the docstring." % ", ".join(Q1_STEPS))
    path = os.path.join(root, "observations", "Q1-%s.json" % step)
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
    if step != "BASE" and q1_state(cpm) is None:
        raise RuntimeError("The hooks are not installed in this SFM process: capture BASE first.")
    import sfmApp
    import vs
    dm = vs.g_pDataModel
    data = {"format": "F01-Q1-capture-v1", "step": step, "pid": os.getpid(), "time": time.time(),
            "cpm_build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__", None), "errors": {}}

    def attempt(key, fn):
        try:
            data[key] = fn()
        except Exception as exc:
            data[key] = None
            data["errors"][key] = repr(exc)
    attempt("session", lambda: {
        "document": q1_text(dm.GetFileName(sfmApp.GetDocumentRoot().GetFileId())),
        "shot": q1_text(sfmApp.GetShotAtCurrentTime().GetName()),
        "head_seconds": float(sfmApp.GetHeadTimeInSeconds()),
        "timeline_mode": q1_text(sfmApp.GetNameForTimelineMode(sfmApp.GetTimelineMode())),
        "undo": {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()), "undo_desc": q1_text(dm.GetUndoDesc()),
                 "redo_desc": q1_text(dm.GetRedoDesc())}})
    identity = win.current() if hasattr(win, "current") else None
    token = getattr(win, "selection_token", None)
    attempt("character", lambda: dict((q1_text(k), q1_plain(x)) for k, x in (identity or {}).items()))
    attempt("instance", lambda: q1_plain(cpm.prod_instance_token(token)))
    attempt("animation_sets", lambda: [q1_raw_set(a) for a in q1_seq(q1_attr(sfmApp.GetShotAtCurrentTime(),
                                                                             "animationSets"))])
    records = {}
    for item in list(getattr(win, "body_items", None) or []):
        rec = (item or {}).get("record") or {}
        if q1_text(rec.get("name")) in Q1_RECORDS:
            records[q1_text(rec.get("name"))] = rec
    data["records"] = dict((n, {"preset_id": q1_text(r.get("preset_id")), "bone_scales": len(r.get("bone_scales") or [])})
                           for n, r in records.items())
    data["settled_full_map"] = {}
    for name, rec in sorted(records.items()):
        try:
            data["settled_full_map"][name] = q1_snapshot_map(cpm, identity, token, rec)
        except Exception as exc:
            data["settled_full_map"][name] = {"error": repr(exc)}
    if step == "BASE":
        st = q1_install(cpm)
        data["hooks_installed"] = sorted(n for n in Q1_HOOKED if getattr(getattr(cpm, n), "q1_original", None)
                                         is st["originals"][n])
    st = q1_state(cpm)
    data["events"] = q1_events_payload(st)
    if st is not None:
        del st["events"][:]
    if step == "DUP-UNDO":
        data["hooks_removed"] = q1_uninstall(cpm)
    payload = json.dumps(data, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    body = (data["settled_full_map"].get(u"Body") or {})
    dup = (data["settled_full_map"].get(u"PS2 Dup Body") or {})
    line = "Q1 %s: %d events | settled map Body %s, PS2 Dup Body %s | undo %r | errors %s | written" % (
        step, len(data["events"]), {True: "PASS", False: "FAIL"}.get(body.get("result"), "UNREADABLE"),
        {True: "PASS", False: "FAIL"}.get(dup.get("result"), "UNREADABLE"),
        ((data.get("session") or {}).get("undo") or {}).get("undo_desc"), sorted(data["errors"]) or "none")
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


if __name__ != "q1_observer_under_test":
    q1_capture(globals())
