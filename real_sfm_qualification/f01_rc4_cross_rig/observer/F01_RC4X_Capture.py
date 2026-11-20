# -*- coding: ascii -*-
"""F-01 RC4: the native two-direction Tails cross-rig qualification, state capture. STRICTLY READ-ONLY. Run from
SFM's Script Editor (Python 2.7) with CPM open, after the setup line of the current direction:

    S1F_DIR = r"<Q>"; S1F_SOURCE = "<set>"; S1F_TARGET = "<set>"; S1F_PEER = "foxmccouldwm1"
    S1F_STEP = "PREP"; execfile(r"<REPO>\\real_sfm_qualification\\f01_rc4_cross_rig\\observer\\F01_RC4X_Capture.py")

It runs the Stage 2 capture wrapper (f01_stage2_tails/observer/F01_S2T_Capture.py) unchanged, verified against its
pin and executed in a private namespace with this test's steps; that wrapper runs the Fox capture, also unchanged and
pinned. Together they write <S1F_DIR>\\observations\\S1F-<step>.json (channels, keys, transforms, CPM's structural
admission) and S1F-<step>.leaves.json (the header's declared procedural bones).

Immediately afterwards this script writes S1F-<step>.offsets.json (exclusive create): for each of the three sets, the
constraint rows of CPM's own compatibility descriptor (prod_body_descriptor, from prod_body_live, prod_body_discover,
prod_body_rig_draft and prod_body_classify): structural identity, solver fields and offsets. These are the actual
destination offsets the comparison uses. Like the other captures, it clicks nothing, selects nothing and never touches
the scene or the library.
"""
import hashlib
import json
import os
import sys

STEPS = ("PREP", "SAVED", "A_BASE", "A_APPLY", "A_NAV", "A_UNDO", "A_REDO", "A_NOOP", "A_FINAL",
         "B_BASE", "B_APPLY", "B_NAV", "B_UNDO", "B_REDO", "B_NOOP", "ABORT", "B_FINAL")
ROLES = ("source", "target", "peer")
# The Stage 2 capture wrapper (it runs the Fox capture 765eefc2...), reused unchanged.
S2T_WRAPPER_SHA256 = "3bd20f07c7fd447b9801bd856ef1e6389c848612775abd84e82fa87891a610d4"
OFFSETS_FORMAT = "F01-RC4X-offsets-v1"


def rc4x_text(v):
    try:
        return v if isinstance(v, type(u"")) else v.decode("utf-8", "replace") if isinstance(v, bytes) else \
            type(u"")(v)
    except Exception:
        return repr(v)


def rc4x_offsets_of(cpm, shot, animset):
    gm = cpm.get_game_model(animset)
    if gm is None:
        return {"status": "NO_MODEL"}
    L = cpm.prod_body_live({"shot": shot, "animset": animset, "gm": gm}, None)
    t = cpm.prod_pose_time_read(L, cpm.prod_body_rig_time_names(L))
    D = cpm.prod_body_discover(L, t[u"t_chan"], cpm.prod_pose_writer_index())
    P = cpm.prod_body_rig_draft(D)
    C = cpm.prod_body_classify(D, P)
    desc = cpm.prod_body_descriptor(D, C, P)
    rows = []
    for row in desc[u"constraints"]:
        rows.append({"identity": rc4x_text(cpm.prod_body_constraint_identity(row)), "type": row[u"type"],
                     "solver": row[u"solver"], "offsets": row[u"offsets"]})
    return {"status": "READ", "handles": len(P[u"handles"]), "constraints": rows}


def rc4x_offsets(cpm, shot, names):
    sets = list(cpm.prod_pose_seq(cpm.prod_pose_attr(shot, u"animationSets"))) if shot is not None else []
    out = {}
    for role in ROLES:
        found = [a for a in sets if rc4x_text(a.GetName()) == names.get(role)]
        if len(found) != 1:
            out[role] = {"status": "NOT_FOUND", "count": len(found)}
            continue
        try:
            out[role] = rc4x_offsets_of(cpm, shot, found[0])
        except Exception as exc:
            out[role] = {"status": "ERROR", "reason": repr(exc), "code": getattr(exc, "code", None)}
    return out


def rc4x_capture(g, s2t_path, s1f_path, s2t_sha256=S2T_WRAPPER_SHA256, cpm=None, shot=None, s1f_sha256=None):
    step = g.get("S1F_STEP")
    root = g.get("S1F_DIR")
    if step not in STEPS or not root:
        raise RuntimeError("Set S1F_DIR and S1F_STEP (one of %s) first; nothing was written." % ", ".join(STEPS))
    sidecar = os.path.join(root, "observations", "S1F-%s.offsets.json" % step)
    if os.path.exists(sidecar):
        raise RuntimeError("%s exists; each capture is taken once. Nothing was written." % sidecar)
    with open(s2t_path, "rb") as f:
        source = f.read()
    if hashlib.sha256(source).hexdigest() != s2t_sha256:
        raise RuntimeError("%s is not the pinned Stage 2 wrapper %s; nothing was written." % (s2t_path, s2t_sha256))
    ns = {"__name__": "s2t_capture_under_test", "__file__": s2t_path}
    exec(compile(source, s2t_path, "exec"), ns)
    ns["STEPS"] = STEPS                                    # this test's steps, for both reused captures
    kw = {"cpm": cpm, "shot": shot}
    if s1f_sha256 is not None:                             # tests only: a stand-in for the Fox capture
        kw["capture_sha256"] = s1f_sha256
    data, leaves = ns["s2t_capture"](g, s1f_path, **kw)
    if cpm is None:
        cpm = sys.modules.get("chadchan3d_cpm_app")
    if shot is None:
        import sfmApp
        shot = sfmApp.GetShotAtCurrentTime()
    names = {}
    for role in ROLES:
        names[role] = g.get("S1F_" + role.upper())
    offsets = rc4x_offsets(cpm, shot, names)
    payload = json.dumps({"format": OFFSETS_FORMAT, "step": step, "pid": os.getpid(), "names": names,
                          "sets": offsets}, indent=1, sort_keys=True, default=repr).encode("utf-8")
    fd = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    line = "RC4X %s: controls source %s | target %s | peer %s | offsets written" % (
        step, offsets["source"].get("handles", offsets["source"].get("status")),
        offsets["target"].get("handles", offsets["target"].get("status")),
        offsets["peer"].get("handles", offsets["peer"].get("status")))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)
    return data, leaves, offsets


def rc4x_paths():
    """The reused captures next to this kit: execfile sets no __file__, but this function's code records its file."""
    here = os.path.dirname(os.path.abspath(rc4x_paths.__code__.co_filename))
    base = os.path.dirname(os.path.dirname(here))
    return (os.path.join(base, "f01_stage2_tails", "observer", "F01_S2T_Capture.py"),
            os.path.join(base, "f01_stage1_fox", "observer", "F01_S1F_Capture.py"))


if __name__ != "rc4x_capture_under_test":
    rc4x_capture(globals(), *rc4x_paths())
