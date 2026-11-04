# -*- coding: ascii -*-
"""F-01 NQ-1 key-placement investigation (KP-1) observer: READ-ONLY. Run from SFM's Script Editor (Python 2.7):

    KP1_DIR = r"<KP1 run folder>"; execfile(r"<REPO>\\real_sfm_qualification\\f01_stage_d_nq1\\observer\\F01_KP1_KeyObserve.py")

Writes the next <KP1_DIR>\\observations\\KP-NN.json (exclusive create) and prints one line. Question: when the user
changes Krystal's left-hand position at the playhead with SFM's own controls, at which native tick does SFM author
the key?

It records: the process id, the open document, the playhead and the conversion chain (shot.ToChildMediaTime,
channelsClip.ToChildMediaTime, FromChildMediaTime), the current shot's "Krystal" animation set identity, the ownership
of its Hand_l / Elbow_l channels (control, rig-handle target, the one channels clip in the shot holding each), every
channel of that channels clip in full (every layer's key times and values, the channel's GetCurrentTime and its
from/to binding), a key digest of every channel in every other channels clip of the movie, and the Undo/Redo state.
It never writes, never opens Undo, never moves the playhead and never forces an evaluation.
"""
import hashlib
import json
import os

import sfmApp
import vs

try:
    unicode, long  # noqa: B018 (Python 2.7, SFM)
except NameError:  # offline check under Python 3
    unicode, long = str, int

WATCH = (("Hand_l", "positionChannel"), ("Hand_l", "orientationChannel"), ("Elbow_l", "positionChannel"),
         ("Elbow_l", "orientationChannel"))


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


def seq(v):
    return [v[i] for i in range(len(v))]


def ticks(t):
    return int(t.GetTenthsOfMS())


def text(v):
    if v is None:
        return None
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return u"%s" % (v,)


def ident(e):
    return None if e is None else {"name": text(e.GetName()), "type": text(e.GetTypeString()), "id": text(str(e.GetId()))}


def plain(v):
    """A deterministic JSON value for a key value, or an exception (the channel is then recorded as unreadable)."""
    if isinstance(v, (bool, int, long, float)):
        return float(v)
    if isinstance(v, (bytes, unicode)):
        return text(v)
    for fields in (("x", "y", "z", "w"), ("x", "y", "z"), ("r", "g", "b", "a"), ("x", "y")):
        if all(hasattr(v, f) for f in fields):
            return [float(getattr(v, f)) for f in fields]
    raise TypeError("unsupported key value type %s" % type(v).__name__)


def layers(ch):
    log = ch.GetLog()
    out = []
    for i in range(int(log.GetNumLayers())):
        layer = log.GetLayer(i)
        out.append([[ticks(layer.GetKeyTime(k)), plain(layer.GetKeyValue(k))] for k in range(int(layer.GetKeyCount()))])
    return out


def channels_clips(shot):
    out = []
    for g in seq(attr(shot, "trackGroups")):
        for t in seq(attr(g, "tracks")):
            for c in seq(attr(t, "children")):
                if text(c.GetTypeString()) == u"DmeChannelsClip":
                    out.append(c)
    return out


def film_clips(movie):
    out = []
    for t in seq(attr(attr(movie, "subClipTrackGroup"), "tracks")):
        for c in seq(attr(t, "children")):
            if text(c.GetTypeString()) == u"DmeFilmClip":
                out.append(c)
    return out


def observe():
    out = {"format": "F01-KP1-observation-v1", "pid": os.getpid(), "problems": []}
    dm = vs.g_pDataModel
    doc = sfmApp.GetDocumentRoot()
    out["document"] = text(dm.GetFileName(doc.GetFileId()))
    out["undo"] = {"can_undo": bool(dm.CanUndo()), "can_redo": bool(dm.CanRedo()),
                   "undo_desc": text(dm.GetUndoDesc()), "redo_desc": text(dm.GetRedoDesc())}
    head = float(sfmApp.GetHeadTimeInSeconds())
    t_doc = vs.DmeTime_t(head)
    out["head_seconds"], out["t_doc"] = head, ticks(t_doc)
    shot = sfmApp.GetShotAtCurrentTime()
    if shot is None:
        out["problems"].append("no current shot")
        return out
    out["shot"] = ident(shot)
    out["shot_range"] = [ticks(shot.GetStartTime()), ticks(shot.GetEndTime())]
    t_shot = shot.ToChildMediaTime(t_doc, False)
    out["t_shot"] = ticks(t_shot)
    sets = [a for a in seq(attr(shot, "animationSets")) if text(a.GetName()) == u"Krystal"]
    if len(sets) != 1:
        out["problems"].append("expected one Krystal in the current shot, found %d" % len(sets))
        return out
    animset = sets[0]
    out["animation_set"] = ident(animset)
    controls = dict((text(c.GetName()), c) for c in seq(attr(animset, "controls")))
    watch = dict(("%s.%s" % k, attr(controls[k[0]], k[1])) for k in WATCH)
    clips = channels_clips(shot)
    holders = {}
    for c in clips:
        for ch in seq(attr(c, "channels")):
            holders.setdefault(text(str(ch.GetId())), []).append(c)
    owner = None
    out["ownership"] = {}
    for key, ch in sorted(watch.items()):
        hold = holders.get(text(str(ch.GetId())), [])
        to = attr(ch, "toElement")
        out["ownership"][key] = {"channel": ident(ch), "fromElement": ident(attr(ch, "fromElement")),
                                 "control": ident(controls[key.split(".")[0]]),
                                 "toElement": ident(to), "toAttribute": text(attr(ch, "toAttribute")),
                                 "mode": int(attr(ch, "mode")), "clips_in_shot": [ident(c) for c in hold]}
        if len(hold) != 1:
            out["problems"].append("%s is held by %d channels clips in the shot" % (key, len(hold)))
        elif owner is None:
            owner = hold[0]
        elif text(str(hold[0].GetId())) != text(str(owner.GetId())):
            out["problems"].append("the watched channels are in different channels clips")
    if owner is None:
        return out
    out["clip"] = ident(owner)
    out["clip_range"] = [ticks(owner.GetStartTime()), ticks(owner.GetEndTime())]
    t_chan = owner.ToChildMediaTime(t_shot, False)
    out["t_chan_converted"] = ticks(t_chan)
    out["t_shot_reverse"] = ticks(owner.FromChildMediaTime(t_chan, False))
    out["channels"] = {}
    for ch in seq(attr(owner, "channels")):
        name = text(ch.GetName())
        n = 0
        while u"%s#%d" % (name, n) in out["channels"]:
            n += 1
        row = {"id": text(str(ch.GetId())), "current_ticks": ticks(ch.GetCurrentTime())}
        try:
            row["layers"] = layers(ch)
        except Exception as exc:
            row["layers"] = "unreadable: %r" % (exc,)
        out["channels"][u"%s#%d" % (name, n)] = row
    out["watched_current_ticks"] = dict((k, ticks(ch.GetCurrentTime())) for k, ch in sorted(watch.items()))
    out["elsewhere"] = {}
    owner_id = text(str(owner.GetId()))
    for fc in film_clips(sfmApp.GetMovie()):
        for c in channels_clips(fc):
            if text(str(c.GetId())) == owner_id:
                continue
            for ch in seq(attr(c, "channels")):
                key = u"%s/%s/%s/%s" % (text(fc.GetName()), text(c.GetName()), text(ch.GetName()), text(str(ch.GetId())))
                try:
                    h = hashlib.sha256(json.dumps(layers(ch)).encode("utf-8")).hexdigest()
                except Exception:
                    h = u"unreadable"
                out["elsewhere"][key] = h
    return out


def main():
    root = globals().get("KP1_DIR")
    if not root:
        raise RuntimeError("Set KP1_DIR first (see the docstring).")
    folder = os.path.join(root, "observations")
    n = len([x for x in os.listdir(folder) if x.startswith("KP-") and x.endswith(".json")]) + 1
    try:
        data = observe()
    except Exception as exc:
        import traceback
        data = {"format": "F01-KP1-observation-v1", "pid": os.getpid(), "problems": ["observer error %r" % (exc,)],
                "traceback": traceback.format_exc()}
    data["seq"] = n
    path = os.path.join(folder, "KP-%02d.json" % n)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))
    hand = (data.get("channels") or {}).get(u"Hand_l_p#0") or {}
    print("WROTE %s  shot=%s head=%s converted=%s current=%s Hand_l_p_keys=%s undo=%r problems=%r" % (
        os.path.basename(path), (data.get("shot") or {}).get("name"), data.get("head_seconds"),
        data.get("t_chan_converted"), sorted(set((data.get("watched_current_ticks") or {}).values())),
        [k[0] for k in (hand.get("layers") or [[]])[0]] if isinstance(hand.get("layers"), list) else None,
        (data.get("undo") or {}).get("undo_desc"), data.get("problems")))


main()
