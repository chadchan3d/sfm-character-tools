# -*- coding: ascii -*-
"""F-01 Stage D NQ-1 time probe: READ-ONLY. Run from SFM's Script Editor (Python 2.7):

    NQ1_DIR = r"<Q>"; execfile(r"<REPO>\\real_sfm_qualification\\f01_stage_d_nq1\\observer\\F01_NQ1_TimeProbe.py")

Question: does DmeChannel.GetCurrentTime() follow the playhead? Process A refused Save Pose because the converted
channel time (50208) differed from it (50299). Writes the next <Q>\\probe\\PROBE-NN.json and prints one line.

It records, for the current shot's "Krystal": the playhead, the shot and channels-clip time frames read natively, the
conversion chain (shot.ToChildMediaTime, clip.ToChildMediaTime, clip.FromChildMediaTime), each left-arm channel's
GetCurrentTime with its log value there and at the converted time and the rig input it drives, and the distinct
GetCurrentTime values over every channel of that channels clip. It never writes, never opens Undo, never moves the
playhead and never forces an evaluation.
"""
import json
import os

import sfmApp
import vs

try:
    unicode  # noqa: B018 (Python 2.7, SFM)
except NameError:  # offline check under Python 3
    unicode = str

ARM = (("Hand_l", "positionChannel"), ("Hand_l", "orientationChannel"), ("Elbow_l", "positionChannel"),
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


def name(e):
    return u"%s" % (e.GetName(),)


def comps(v):
    if hasattr(v, "w"):
        return [float(v.x), float(v.y), float(v.z), float(v.w)]
    if hasattr(v, "z"):
        return [float(v.x), float(v.y), float(v.z)]
    return float(v)


def frame(clip):
    out = {"GetStartTime": ticks(clip.GetStartTime()), "GetEndTime": ticks(clip.GetEndTime())}
    try:
        tf = attr(clip, "timeFrame")
        out.update({"start": ticks(attr(tf, "start")), "duration": ticks(attr(tf, "duration")),
                    "offset": ticks(attr(tf, "offset")), "scale": float(attr(tf, "scale"))})
    except Exception as exc:
        out["timeFrame"] = "unreadable: %r" % (exc,)
    return out


def probe():
    out = {"format": "F01-NQ1-time-probe-v1", "pid": os.getpid(), "problems": []}
    head = float(sfmApp.GetHeadTimeInSeconds())
    t_doc = vs.DmeTime_t(head)
    out["head_seconds"], out["t_doc"] = head, ticks(t_doc)
    shot = sfmApp.GetShotAtCurrentTime()
    if shot is None:
        out["problems"].append("no current shot")
        return out
    out["shot"], out["shot_frame"] = name(shot), frame(shot)
    t_shot = shot.ToChildMediaTime(t_doc, False)
    out["t_shot"] = ticks(t_shot)
    sets = [a for a in seq(attr(shot, "animationSets")) if name(a) == u"Krystal"]
    if len(sets) != 1:
        out["problems"].append("expected one Krystal in %s, found %d" % (out["shot"], len(sets)))
        return out
    controls = dict((name(c), c) for c in seq(attr(sets[0], "controls")))
    arm = dict(("%s.%s" % k, attr(controls[k[0]], k[1])) for k in ARM)
    arm_ids = set(str(ch.GetId()) for ch in arm.values())
    clips = []
    for g in seq(attr(shot, "trackGroups")):
        for t in seq(attr(g, "tracks")):
            for c in seq(attr(t, "children")):
                if u"%s" % (c.GetTypeString(),) == u"DmeChannelsClip":
                    ids = set(str(ch.GetId()) for ch in seq(attr(c, "channels")))
                    if arm_ids & ids:
                        clips.append((c, ids))
    if len(clips) != 1:
        out["problems"].append("expected one channels clip holding the arm channels, found %d" % len(clips))
        return out
    clip = clips[0][0]
    out["clip"], out["clip_frame"] = name(clip), frame(clip)
    t_chan = clip.ToChildMediaTime(t_shot, False)
    out["t_chan_converted"] = ticks(t_chan)
    try:  # not yet native-proven; a failure is recorded, not fatal
        out["t_shot_reverse"] = ticks(clip.FromChildMediaTime(t_chan, False))
    except Exception as exc:
        out["t_shot_reverse"] = "unreadable: %r" % (exc,)
    out["arm"] = {}
    for key, ch in sorted(arm.items()):
        log, cur = ch.GetLog(), ch.GetCurrentTime()
        to = attr(ch, "toElement")
        out["arm"][key] = {"current_ticks": ticks(cur), "value_at_current": comps(log.GetValue(cur)),
                           "value_at_converted": comps(log.GetValue(t_chan)),
                           "rig_input": comps(attr(to, u"%s" % (attr(ch, "toAttribute"),))),
                           "keys": int(log.GetLayer(0).GetKeyCount())}
    hist = {}
    for ch in seq(attr(clip, "channels")):
        k = str(ticks(ch.GetCurrentTime()))
        hist[k] = hist.get(k, 0) + 1
    out["clip_current_ticks_histogram"] = hist
    return out


def main():
    root = globals().get("NQ1_DIR")
    if not root:
        raise RuntimeError("Set NQ1_DIR first (see the docstring).")
    folder = os.path.join(root, "probe")
    if not os.path.isdir(folder):
        os.mkdir(folder)
    n = len([x for x in os.listdir(folder) if x.startswith("PROBE-") and x.endswith(".json")]) + 1
    try:
        data = probe()
    except Exception as exc:
        import traceback
        data = {"format": "F01-NQ1-time-probe-v1", "pid": os.getpid(), "problems": ["probe error %r" % (exc,)],
                "traceback": traceback.format_exc()}
    data["seq"] = n
    path = os.path.join(folder, "PROBE-%02d.json" % n)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))
    cur = sorted(set(v["current_ticks"] for v in (data.get("arm") or {}).values()))
    print("WROTE %s  shot=%s head=%s t_doc=%s t_shot=%s converted=%s reported=%s problems=%r" % (
        os.path.basename(path), data.get("shot"), data.get("head_seconds"), data.get("t_doc"), data.get("t_shot"),
        data.get("t_chan_converted"), cur, data.get("problems")))


main()
