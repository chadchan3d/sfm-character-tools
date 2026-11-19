# -*- coding: ascii -*-
"""F-01 Stage 1: the targeted native Abort recovery check, state capture. STRICTLY READ-ONLY. Run from SFM's Script
Editor (Python 2.7) with CPM open, after the setup line:

    S1F_DIR = r"<Q>"; S1F_SOURCE = "foxmccouldwm2"; S1F_TARGET = "foxmccouldwm3"; S1F_PEER = "foxmccouldwm1"
    S1F_STEP = "BASE"; execfile(r"<REPO>\\real_sfm_qualification\\f01_stage1_recovery\\observer\\F01_S1R_Capture.py")

It runs the Fox qualification's own capture, F01_S1F_Capture.py, unchanged. That file is verified against its pin and
executed in a private namespace, with this check's six steps as its step list. The capture writes
<S1F_DIR>\\observations\\S1F-<step>.json.

Immediately afterwards, this script reads SFM's Undo state directly from the DataModel and writes it to the sidecar
<S1F_DIR>\\observations\\S1F-<step>.undo.json (exclusive create):
- enabled (IsUndoEnabled, which the Fox capture does not record);
- CanUndo, CanRedo, GetUndoDesc and GetRedoDesc.

The sidecar keeps each raw type, and a non-boolean flag is recorded as such, never coerced. Like the capture, the
sidecar clicks nothing, selects nothing and never touches the scene or the library.
"""
import hashlib
import json
import os
import sys

STEPS = ("BASE", "APPLY", "UNDO", "ABORT1", "ABORT2", "APPLY2")
# The Fox qualification's capture (f01_stage1_fox/observer/F01_S1F_Capture.py), reused unchanged.
S1F_CAPTURE_SHA256 = "765eefc280e6aa3b403d81ed0bd885862851436f95074fa390b532cf34bbbb22"
SIDECAR_FORMAT = "F01-S1R-undo-v1"


def s1r_flag(read):
    try:
        value = read()
    except Exception as exc:
        return {"unreadable": repr(exc)}
    return value if isinstance(value, bool) else {"non_boolean": repr(value)}


def s1r_text(read):
    try:
        value = read()
    except Exception as exc:
        return {"unreadable": repr(exc)}
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value if isinstance(value, type(u"")) else {"non_text": repr(value)}


def s1r_undo(dm):
    return {"enabled": s1r_flag(dm.IsUndoEnabled), "can_undo": s1r_flag(dm.CanUndo),
            "can_redo": s1r_flag(dm.CanRedo), "undo_desc": s1r_text(dm.GetUndoDesc),
            "redo_desc": s1r_text(dm.GetRedoDesc)}


def s1r_capture(g, capture_path, capture_sha256=S1F_CAPTURE_SHA256, datamodel=None):
    step = g.get("S1F_STEP")
    root = g.get("S1F_DIR")
    if step not in STEPS or not root:
        raise RuntimeError("Set S1F_DIR and S1F_STEP (one of %s) first; nothing was written." % ", ".join(STEPS))
    sidecar = os.path.join(root, "observations", "S1F-%s.undo.json" % step)
    if os.path.exists(sidecar):
        raise RuntimeError("%s exists; each capture is taken once. Nothing was written." % sidecar)
    with open(capture_path, "rb") as f:
        source = f.read()
    if hashlib.sha256(source).hexdigest() != capture_sha256:
        raise RuntimeError("%s is not the pinned Fox capture %s; nothing was written." % (capture_path,
                                                                                         capture_sha256))
    ns = {"__name__": "s1f_capture_under_test", "__file__": capture_path}
    exec(compile(source, capture_path, "exec"), ns)
    ns["STEPS"] = STEPS
    data = ns["s1f_capture"](g)                            # the unchanged capture: S1F-<step>.json
    if datamodel is None:
        import vs
        datamodel = vs.g_pDataModel
    undo = s1r_undo(datamodel)
    payload = json.dumps({"format": SIDECAR_FORMAT, "step": step, "pid": os.getpid(), "undo": undo},
                         indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    line = "S1R %s: Undo enabled %r | undo %r redo %r | sidecar written" % (
        step, undo["enabled"], undo["undo_desc"], undo["redo_desc"])
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)
    return data, undo


def s1r_capture_path():
    """The Fox capture next to this kit: execfile sets no __file__, but this function's code records its file."""
    here = os.path.dirname(os.path.abspath(s1r_capture_path.__code__.co_filename))
    return os.path.join(os.path.dirname(os.path.dirname(here)), "f01_stage1_fox", "observer", "F01_S1F_Capture.py")


if __name__ != "s1r_capture_under_test":
    s1r_capture(globals(), s1r_capture_path())
