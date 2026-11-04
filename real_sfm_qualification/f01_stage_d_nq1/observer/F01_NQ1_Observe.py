# -*- coding: ascii -*-
"""F-01 Stage D NQ-1 observer: READ-ONLY. Run from SFM's Script Editor (Python 2.7):

    NQ1_DIR = r"<Q>"; execfile(NQ1_DIR + r"\\observer\\F01_NQ1_Observe.py")

Writes the next <Q>\\observations\\OBS-NN.json (exclusive create) and prints its name and a one-line summary. It reads,
with plain native calls only and independently of CPM's own code: the process id, the open document, the playhead,
every shot of the movie with its animation sets, the current shot's "Krystal" left-arm channels (complete key arrays),
the rig inputs those channels drive, a digest of every other channel's authored keys in every shot, every bone
transform's local (parent-relative) position and orientation, the model and the
rig_root / CollarL placement, the Undo and Redo state, the CPM window's status line and build, and the pose files in
the CPM library. It never writes to the scene, never opens Undo and never moves the playhead.
"""
import glob
import hashlib
import json
import os
import sys

import sfmApp
import vs

try:
    long, unicode  # noqa: B018 (Python 2.7, SFM)
except NameError:  # the offline dry run (Python 3)
    long, unicode = int, str

ARM = (("Hand_l", "positionChannel"), ("Hand_l", "orientationChannel"), ("Elbow_l", "positionChannel"),
       ("Elbow_l", "orientationChannel"))
PLACEMENT = (("rig_root", "positionChannel"), ("rig_root", "orientationChannel"), ("CollarL", "positionChannel"),
             ("CollarL", "orientationChannel"))


def text(v):
    if v is None:
        return None
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return u"%s" % (v,)


def native_name(name):
    # Python 2 SWIG char const* does not accept unicode (the W2 harness's native_name, native-proven).
    if isinstance(name, unicode):
        return name.encode("utf-8", "strict")
    return name


def attr(obj, name):
    a = obj.GetAttribute(native_name(name))
    if a is None:
        raise RuntimeError("missing attribute %s" % name)
    return a.GetValue()


def has(obj, name):
    return bool(obj.HasAttribute(name))


def comps(v):
    if hasattr(v, "w"):
        return [float(v.x), float(v.y), float(v.z), float(v.w)]
    if hasattr(v, "z"):
        return [float(v.x), float(v.y), float(v.z)]
    return float(v)


def seq(v):
    return [v[i] for i in range(len(v))]


def ticks(t):
    return int(t.GetTenthsOfMS())


def plain(v):
    """A deterministic JSON value for a key value, or an exception (the channel is then 'unreadable')."""
    if isinstance(v, (bool, int, long, float)):
        return float(v)
    if isinstance(v, (bytes, unicode)):
        return text(v)
    for fields in (("x", "y", "z", "w"), ("x", "y", "z"), ("r", "g", "b", "a"), ("x", "y")):
        if all(hasattr(v, f) for f in fields):
            return [float(getattr(v, f)) for f in fields]
    raise TypeError("unsupported key value type %s" % type(v).__name__)


def other_channels(movie, arm_ids):
    """SHA-256 of every authored key (all layers) of every channel in every shot's channels clips, except the four
    left-arm channels recorded in full. Keyed 'shot/clip/channel#n' (n disambiguates repeated names). A channel whose
    keys cannot be read is recorded as 'unreadable' and reported, never silently skipped."""
    out = {}
    group = attr(movie, "subClipTrackGroup")
    for track in seq(attr(group, "tracks")):
        for shot in seq(attr(track, "children")):
            if text(shot.GetTypeString()) != "DmeFilmClip":
                continue
            for g in seq(attr(shot, "trackGroups")):
                for t in seq(attr(g, "tracks")):
                    for clip in seq(attr(t, "children")):
                        if text(clip.GetTypeString()) != "DmeChannelsClip":
                            continue
                        for ch in seq(attr(clip, "channels")):
                            if text(str(ch.GetId())) in arm_ids:
                                continue
                            base = u"%s/%s/%s" % (text(shot.GetName()), text(clip.GetName()), text(ch.GetName()))
                            n = 0
                            while u"%s#%d" % (base, n) in out:
                                n += 1
                            try:
                                log = ch.GetLog()
                                h = hashlib.sha256()
                                for i in range(int(log.GetNumLayers())):
                                    layer = log.GetLayer(i)
                                    h.update(("L%d:" % i).encode("ascii"))
                                    for k in range(int(layer.GetKeyCount())):
                                        v = plain(layer.GetKeyValue(k))
                                        h.update(json.dumps([ticks(layer.GetKeyTime(k)), v]).encode("utf-8"))
                                digest = h.hexdigest()
                            except Exception:
                                digest = u"unreadable"
                            out[u"%s#%d" % (base, n)] = digest
    return out


WRITTEN = (("Hand_l", "positionChannel"), ("Hand_l", "orientationChannel"), ("Elbow_l", "positionChannel"))


def close(a, b):
    if a is None or b is None or len(a) != len(b):
        return False
    if len(a) == 4:
        na, nb = sum(x * x for x in a) ** 0.5, sum(x * x for x in b) ** 0.5
        return abs(sum(x * y for x, y in zip(a, b))) / (na * nb) >= 1.0 - 1e-9
    return max(abs(x - y) for x, y in zip(a, b)) <= 1e-5


def diagnostics(out, shot, controls, gm, head):
    """F-01 FA-1 (read-only): the clip-stack conversion, whether each written rig input equals its log value at the
    converted time and at the channel clock, and every bone's world transform (DmeDag absolute, W2-proven)."""
    t_doc = vs.DmeTime_t(head)
    t_shot = shot.ToChildMediaTime(t_doc, False)
    first = attr(controls["Hand_l"], "positionChannel")
    holder = None
    for g in seq(attr(shot, "trackGroups")):
        for t in seq(attr(g, "tracks")):
            for c in seq(attr(t, "children")):
                if text(c.GetTypeString()) == u"DmeChannelsClip" and any(
                        text(str(ch.GetId())) == text(str(first.GetId())) for ch in seq(attr(c, "channels"))):
                    holder = c
    t_chan = holder.ToChildMediaTime(t_shot, False)
    conv = {"t_doc": ticks(t_doc), "t_shot": ticks(t_shot), "t_chan": ticks(t_chan), "clip": text(holder.GetName())}
    try:
        conv["t_shot_reverse"] = ticks(holder.FromChildMediaTime(t_chan, False))
    except Exception as exc:
        conv["t_shot_reverse"] = "unreadable: %r" % (exc,)
    out["conversion"] = conv
    flags = {}
    for owner, name in WRITTEN:
        ch = attr(controls[owner], name)
        log = ch.GetLog()
        rig = out["rig_inputs"]["%s.%s" % (owner, name)]
        flags["%s.%s" % (owner, name)] = {"at_converted": close(rig, comps(log.GetValue(t_chan))),
                                          "at_clock": close(rig, comps(log.GetValue(ch.GetCurrentTime()))),
                                          "clock": ticks(ch.GetCurrentTime())}
    out["rig_evaluated_at"] = flags
    world, pending = {}, [(d, None) for d in seq(attr(gm, "children"))]
    names = set(out["bones"])
    while pending:
        dag, parent = pending.pop()
        t = attr(dag, "transform")
        tname = text(t.GetName()) if t is not None else None
        if tname in names:
            world[tname] = {"position": comps(dag.GetAbsPosition()), "orientation": comps(dag.GetAbsOrientation()),
                            "parent": parent}
        if dag.HasAttribute("children"):
            pending.extend((d, tname if tname in names else parent) for d in seq(attr(dag, "children")))
    out["bones_world"] = world


def observe():
    out = {"format": "F01-NQ1-observation-v1", "pid": os.getpid(), "problems": []}
    doc = sfmApp.GetDocumentRoot()
    out["document"] = text(vs.g_pDataModel.GetFileName(doc.GetFileId()))
    head = float(sfmApp.GetHeadTimeInSeconds())
    out["head_seconds"] = head
    out["head_ticks"] = ticks(vs.DmeTime_t(head))
    try:  # TM-1 (read-only): SFM's timeline mode, recorded as reported
        m = sfmApp.GetTimelineMode()
        out["timeline_mode"] = {"value": repr(m), "name": text(sfmApp.GetNameForTimelineMode(m))}
    except Exception as exc:
        out["timeline_mode"] = {"error": repr(exc)}
    dm = vs.g_pDataModel
    out["undo"] = {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()),
                   "undo_desc": text(dm.GetUndoDesc()), "redo_desc": text(dm.GetRedoDesc())}
    shots = []
    movie = sfmApp.GetMovie()
    group = attr(movie, "subClipTrackGroup")
    for track in seq(attr(group, "tracks")):
        for clip in seq(attr(track, "children")):
            if text(clip.GetTypeString()) != "DmeFilmClip":
                continue
            sets = [{"name": text(a.GetName()), "id": text(str(a.GetId()))} for a in seq(attr(clip, "animationSets"))]
            shots.append({"name": text(clip.GetName()), "start": ticks(clip.GetStartTime()),
                          "end": ticks(clip.GetEndTime()), "animation_sets": sets})
    out["shots"] = shots
    shot = sfmApp.GetShotAtCurrentTime()
    out["current_shot"] = text(shot.GetName()) if shot is not None else None
    sets = [a for a in seq(attr(shot, "animationSets")) if text(a.GetName()) == "Krystal"] if shot else []
    if len(sets) != 1:
        out["problems"].append("expected exactly one Krystal in the current shot, found %d" % len(sets))
        return out
    animset = sets[0]
    out["animation_set_id"] = text(str(animset.GetId()))
    controls = dict((text(c.GetName()), c) for c in seq(attr(animset, "controls")))
    out["channels"], out["rig_inputs"], out["placement"] = {}, {}, {}
    arm_ids = set()
    for owner, name in ARM + PLACEMENT:
        if owner not in controls and (owner, name) in PLACEMENT:
            out["placement"]["%s.%s" % (owner, name)] = None
            continue
        ch = attr(controls[owner], name)
        to = attr(ch, "toElement")
        target = attr(to, text(attr(ch, "toAttribute")))
        key = "%s.%s" % (owner, name)
        if (owner, name) in ARM:
            arm_ids.add(text(str(ch.GetId())))
            log = ch.GetLog()
            layers = []
            for i in range(int(log.GetNumLayers())):
                layer = log.GetLayer(i)
                layers.append([[ticks(layer.GetKeyTime(k)), comps(layer.GetKeyValue(k))]
                               for k in range(int(layer.GetKeyCount()))])
            out["channels"][key] = {"name": text(ch.GetName()), "mode": int(attr(ch, "mode")), "layers": layers,
                                    "current_ticks": ticks(ch.GetCurrentTime())}
            out["rig_inputs"][key] = comps(target)
        else:
            out["placement"][key] = comps(target)
    out["other_channels"] = other_channels(movie, arm_ids)
    gm = attr(animset, "gameModel")
    gt = attr(gm, "transform")
    out["model"] = {"position": comps(attr(gt, "position")), "orientation": comps(attr(gt, "orientation"))}
    out["bones"] = {}
    for t in seq(attr(gm, "bones")):
        out["bones"][text(t.GetName())] = {"position": comps(attr(t, "position")),
                                           "orientation": comps(attr(t, "orientation"))}
    try:
        diagnostics(out, shot, controls, gm, head)
    except Exception as exc:
        out["problems"].append("diagnostics unreadable: %r" % (exc,))
    cpm = sys.modules.get("chadchan3d_cpm_app")
    out["cpm"] = None
    if cpm is not None:
        out["cpm"] = {"build_sha256": getattr(cpm, "__chadchan3d_cpm_build_sha256__", None),
                      "registry_mode": getattr(cpm, "PROD_POSE_REGISTRY_MODE", None), "status": None}
        try:
            from PySide import QtGui
            for w in QtGui.QApplication.topLevelWidgets():
                if isinstance(w, cpm.ProdWindow) and w.isVisible():
                    out["cpm"]["status"] = text(w.status.text())
        except Exception as exc:
            out["problems"].append("CPM status unreadable: %r" % (exc,))
    library = os.path.join(os.path.expanduser("~"), "Documents", "SFM Character Preset Manager", "Characters")
    out["pose_files"] = {}
    for path in sorted(glob.glob(os.path.join(library, "*", "Poses", "*.json"))):
        with open(path, "rb") as f:
            out["pose_files"][os.path.relpath(path, library).replace("\\", "/")] = hashlib.sha256(f.read()).hexdigest()
    return out


def main():
    root = globals().get("NQ1_DIR")
    if not root:
        raise RuntimeError("Set NQ1_DIR first (see the docstring).")
    folder = os.path.join(root, "observations")
    n = len([x for x in os.listdir(folder) if x.startswith("OBS-") and x.endswith(".json")]) + 1
    try:
        data = observe()
    except Exception as exc:
        import traceback
        data = {"format": "F01-NQ1-observation-v1", "pid": os.getpid(), "problems": ["observer error %r" % (exc,)],
                "traceback": traceback.format_exc()}
    data["seq"] = n
    path = os.path.join(folder, "OBS-%02d.json" % n)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))
    ev = data.get("rig_evaluated_at") or {}
    print("WROTE %s  mode=%s shot=%s head=%s undo=%r rig@converted=%s rig@clock=%s clock=%s status=%r problems=%r" % (
        os.path.basename(path), data.get("timeline_mode"), data.get("current_shot"), data.get("head_seconds"),
        (data.get("undo") or {}).get("undo_desc"), all(v["at_converted"] for v in ev.values()) if ev else None,
        all(v["at_clock"] for v in ev.values()) if ev else None, sorted(set(v["clock"] for v in ev.values())),
        (data.get("cpm") or {}).get("status"), data.get("problems")))


main()
