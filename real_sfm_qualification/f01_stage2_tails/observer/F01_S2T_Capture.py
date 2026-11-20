# -*- coding: ascii -*-
"""F-01 Stage 2: the native Tails JIGGLE leaf qualification, state capture. STRICTLY READ-ONLY. Run from SFM's
Script Editor (Python 2.7) with CPM open, after the setup line:

    S1F_DIR = r"<Q>"; S1F_SOURCE = "<Tails S set>"; S1F_TARGET = "<Tails D set>"; S1F_PEER = "milestailsprower1"
    S1F_STEP = "PREP"; execfile(r"<REPO>\\real_sfm_qualification\\f01_stage2_tails\\observer\\F01_S2T_Capture.py")

It runs the Fox qualification's own capture, F01_S1F_Capture.py, unchanged: verified against its pin and executed in
a private namespace with this test's seven steps. That capture writes <S1F_DIR>\\observations\\S1F-<step>.json: every
channel digest and key, every bone and handle transform, and CPM's structural admission (bone classes, channel roles,
written set) of the three sets.

Immediately afterwards this script writes the leaf sidecar <S1F_DIR>\\observations\\S1F-<step>.leaves.json (exclusive
create). For each of the three sets it records, through the loaded CPM's read-only prod_body_live and
prod_body_rig_header (the studio header evidence CPM itself uses):
- the header status (READ or UNREADABLE, with the reason);
- every bone the header declares procedural: index, name, parent, flags, procedure type, and whether a local
  attachment or a bone flex driver uses it;
- the scale field of each of those bones' transforms;
- the procedure and flag constants.
Like the capture, it clicks nothing, selects nothing and never touches the scene or the library.
"""
import hashlib
import json
import os
import sys

STEPS = ("PREP", "SAVED", "BASE", "APPLY", "NAV", "UNDO", "REDO")
ROLES = ("source", "target", "peer")
# The Fox qualification's capture (f01_stage1_fox/observer/F01_S1F_Capture.py), reused unchanged.
S1F_CAPTURE_SHA256 = "765eefc280e6aa3b403d81ed0bd885862851436f95074fa390b532cf34bbbb22"
SIDECAR_FORMAT = "F01-S2T-leaves-v1"
LEAF_CLASS = u"simulated-leaf"


def s2t_text(v):
    try:
        return v if isinstance(v, type(u"")) else v.decode("utf-8", "replace") if isinstance(v, bytes) else \
            type(u"")(v)
    except Exception:
        return repr(v)


def s2t_set(cpm, shot, animset):
    """The header evidence and the declared bones' scale fields of one animation set (read only)."""
    gm = cpm.get_game_model(animset)
    if gm is None:
        return {"status": "NO_MODEL"}
    L = cpm.prod_body_live({"shot": shot, "animset": animset, "gm": gm}, None)
    H = cpm.prod_body_rig_header(L)
    if not isinstance(H, dict) or H.get("status") != "READ":
        return {"status": "UNREADABLE", "reason": s2t_text((H or {}).get("reason") if isinstance(H, dict) else H)}
    attachments, drivers = set(H["attachments"]), set(H["flex_drivers"])
    declared, scales = [], {}
    for r in H["bones"]:
        if not r["proctype"]:
            continue
        name = s2t_text(r["name"])
        declared.append({"index": r["index"], "name": name, "parent": r["parent"], "flags": r["flags"],
                         "proctype": r["proctype"], "attachment": r["index"] in attachments,
                         "flex_driver": r["index"] in drivers})
        bone = L["bones"].get(r["name"])
        scales[name] = cpm.prod_pose_field(cpm.prod_pose_attr(bone["dag"], u"transform"), u"scale") if bone else \
            {"status": "NO_BONE"}
    return {"status": "READ", "bones": len(H["bones"]), "declared": declared, "scales": scales,
            "constants": dict((s2t_text(k), v) for k, v in H["constants"].items())}


def s2t_sidecar(cpm, shot, names):
    sets = list(cpm.prod_pose_seq(cpm.prod_pose_attr(shot, u"animationSets"))) if shot is not None else []
    out = {}
    for role in ROLES:
        found = [a for a in sets if s2t_text(a.GetName()) == names.get(role)]
        if len(found) != 1:
            out[role] = {"status": "NOT_FOUND", "count": len(found)}
            continue
        try:
            out[role] = s2t_set(cpm, shot, found[0])
        except Exception as exc:
            out[role] = {"status": "ERROR", "reason": repr(exc)}
    return out


def s2t_leaves(data, role):
    adm = ((data.get("sets") or {}).get(role) or {}).get("admission") or {}
    classes = adm.get("bone_classes")
    if not isinstance(classes, dict):
        return adm.get("code") or "refused"
    return len([c for c in classes.values() if c == LEAF_CLASS])


def s2t_capture(g, capture_path, capture_sha256=S1F_CAPTURE_SHA256, cpm=None, shot=None):
    step = g.get("S1F_STEP")
    root = g.get("S1F_DIR")
    if step not in STEPS or not root:
        raise RuntimeError("Set S1F_DIR and S1F_STEP (one of %s) first; nothing was written." % ", ".join(STEPS))
    sidecar = os.path.join(root, "observations", "S1F-%s.leaves.json" % step)
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
    if cpm is None:
        cpm = sys.modules.get("chadchan3d_cpm_app")
    if shot is None:
        import sfmApp
        shot = sfmApp.GetShotAtCurrentTime()
    names = {}
    for role in ROLES:                  # a plain loop: Python 2 forbids exec beside a nested scope
        names[role] = g.get("S1F_" + role.upper())
    leaves = s2t_sidecar(cpm, shot, names)
    payload = json.dumps({"format": SIDECAR_FORMAT, "step": step, "pid": os.getpid(), "names": names,
                          "sets": leaves}, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    line = "S2T %s: simulated leaves Tails S %s | Tails D %s | header %s %s | sidecar written" % (
        step, s2t_leaves(data, "source"), s2t_leaves(data, "target"), leaves["source"].get("status"),
        leaves["target"].get("status"))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)
    return data, leaves


def s2t_capture_path():
    """The Fox capture next to this kit: execfile sets no __file__, but this function's code records its file."""
    here = os.path.dirname(os.path.abspath(s2t_capture_path.__code__.co_filename))
    return os.path.join(os.path.dirname(os.path.dirname(here)), "f01_stage1_fox", "observer", "F01_S1F_Capture.py")


if __name__ != "s2t_capture_under_test":
    s2t_capture(globals(), s2t_capture_path())
