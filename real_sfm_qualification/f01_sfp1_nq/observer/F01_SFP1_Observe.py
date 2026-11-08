# -*- coding: ascii -*-
"""F-01 SFP-1 Selected parts native qualification observation: STRICTLY READ-ONLY. Run from SFM's Script Editor
(Python 2.7). Once per SFM process:

    SFP1_DIR = r"<run folder>"; SFP1_REPO = r"<repo>"

then, for each procedure step marked Observe:

    SFP1_STEP = "B2"; execfile(SFP1_REPO + r"\\real_sfm_qualification\\f01_sfp1_nq\\observer\\F01_SFP1_Observe.py")

It runs the pinned, unchanged S0 survey observer (real_sfm_qualification/f01_full_body_s0/observer/F01_S0_Survey.py)
under the step's fixed label, which writes <SFP1_DIR>\\observations\\S0-NN.json, and then adds one sidecar
<SFP1_DIR>\\observations\\S0-NN.sfp1.json: the step, and a SHA-256 over every authored key of every channel OUTSIDE the
observed instance's own channels clip (every other animation set, prop, camera, light and shot), by shot and channel
name (no handles), so unrelated animation can be compared within one SFM process. It then prints whether the timeline
editor, shot and playhead match the step. Its only file writes are those two files (exclusive create). This is the
S3 wrapper's method (f01_full_body_s3/observer/F01_S3_Observe.py) with this run's step table.
"""
import hashlib
import io
import json
import os
import sys

ME, CE = "Motion Editor", "Clip Editor"
STEPS = {
    # Process A: source session SFP1_SOURCE.dmx, shot15 at 0.2083 s
    "A1": ("S0-01", ME, "shot15", 0.2083), "A2": ("S0-02", ME, "shot15", 0.2083),
    "A3": ("S0-03", ME, "shot15", 0.2083), "A4": ("S0-04", ME, "shot15", 0.2083),
    "A5": ("S0-05", ME, "shot15", 0.2083), "A6": ("S0-06", ME, "shot15", 0.2083),
    "A7": ("S0-07", ME, "shot15", 0.2083),
    # Process B: destination session SFP1_DESTINATION.dmx, shot13 at 0.3750 s, then shot15 at 0.2083 s
    "B1": ("S0-08", ME, "shot13", 0.3750), "B2": ("S0-09", ME, "shot13", 0.3750),
    "B3": ("S0-10", ME, "shot13", 0.3750), "B4": ("S0-11", ME, "shot13", 0.3750),
    "B5": ("S0-12", ME, "shot13", 0.3750), "B6": ("S0-13", ME, "shot13", 0.3750),
    "B7": ("S0-14", ME, "shot13", 0.3750), "B8": ("S0-15", CE, "shot13", 0.3750),
    "B9": ("S0-16", CE, "shot13", 0.3750),
    "B10": ("S0-17", ME, "shot15", 0.2083), "B11": ("S0-18", ME, "shot15", 0.2083),
    "B12": ("S0-19", ME, "shot15", 0.2083), "B13": ("S0-20", ME, "shot15", 0.2083),
    "B14": ("S0-21", ME, "shot15", 0.2083), "B15": ("S0-22", ME, "shot15", 0.2083),
    "B16": ("S0-23", ME, "shot15", 0.2083),
    # Process C (optional): prop session SFP1_PROP.dmx, shot13 at 0.3750 s
    "C1": ("S0-24", ME, "shot13", 0.3750), "C2": ("S0-25", ME, "shot13", 0.3750),
    "C3": ("S0-26", ME, "shot13", 0.3750),
}


def sfp1_outside_digest(og, clip_handle):
    """SHA-256 over every authored key of every channel of every channels clip except the instance's own, with the
    shot and channel names. Plain native reads through the S0 observer's own helpers."""
    digest, count, unreadable = hashlib.sha256(), 0, []
    for shot in og["film_clips"](og["sfmApp"].GetMovie()):
        shot_name = og["text"](shot.GetName())
        for clip in og["channels_clips"](shot):
            if og["h"](clip) == clip_handle:
                continue
            for ch in og["seq"](og["attr"](clip, "channels")):
                count += 1
                digest.update(("C%s/%s/%s;" % (shot_name, og["text"](clip.GetName()), og["text"](ch.GetName())))
                              .encode("utf-8"))
                try:
                    log = ch.GetLog()
                    for i in range(int(log.GetNumLayers())):
                        layer = log.GetLayer(i)
                        digest.update(("L%d:" % i).encode("ascii"))
                        for k in range(int(layer.GetKeyCount())):
                            digest.update(json.dumps([og["ticks"](layer.GetKeyTime(k)),
                                                      og["key_value"](layer.GetKeyValue(k))]).encode("utf-8"))
                except Exception as exc:
                    digest.update(b"unreadable")
                    unreadable.append("%s/%s: %r" % (shot_name, og["text"](ch.GetName()), exc))
    return {"sha256": digest.hexdigest(), "channels": count, "unreadable": len(unreadable),
            "first_unreadable": unreadable[0] if unreadable else None}


def sfp1_main(g):
    root, repo, step = g.get("SFP1_DIR"), g.get("SFP1_REPO"), g.get("SFP1_STEP")
    if not root or not repo or step not in STEPS:
        raise RuntimeError("Set SFP1_DIR, SFP1_REPO and SFP1_STEP (one of %s) first; see the docstring."
                           % ", ".join(sorted(STEPS)))
    label, mode, shot, head = STEPS[step]
    sidecar = os.path.join(root, "observations", "%s.sfp1.json" % label)
    if os.path.exists(sidecar):
        raise RuntimeError("%s exists; step %s was already observed. Never repeat a step." % (sidecar, step))
    observer = os.path.join(repo, "real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")
    with io.open(observer, "rb") as f:
        source = f.read()
    og = {"__name__": "__sfp1_observer__", "S0_DIR": root, "S0_LABEL": label}
    exec(compile(source, observer, "exec"), og)
    with io.open(os.path.join(root, "observations", "%s.json" % label), "rb") as f:
        obs = json.loads(f.read().decode("utf-8"))
    clip = (obs.get("channels_clip") or {}).get("clip") or {}
    before = og["session_state"]()
    outside = sfp1_outside_digest(og, clip.get("handle"))
    after = og["session_state"]()
    s = obs.get("session_after") or {}
    got = ((s.get("timeline_mode") or {}).get("name"), s.get("current_shot"), s.get("head_seconds"))
    mismatch = []
    if got[0] != mode:
        mismatch.append("timeline %r, expected %r" % (got[0], mode))
    if got[1] != shot:
        mismatch.append("shot %r, expected %r" % (got[1], shot))
    if not isinstance(got[2], float) or abs(got[2] - head) > 0.0001:
        mismatch.append("playhead %r, expected %.4f" % (got[2], head))
    if obs.get("problems"):
        mismatch.append("observer problems: %d (first: %s)" % (len(obs["problems"]), obs["problems"][0]))
    if not (obs.get("readonly") or {}).get("unchanged"):
        mismatch.append("the observation was not read-only")
    if before != after:
        mismatch.append("the session changed while the outside digest was read")
    if outside["unreadable"]:
        mismatch.append("outside digest: %d unreadable channels" % outside["unreadable"])
    data = {"format": "F01-SFP1-sidecar-v1", "step": step, "label": label, "pid": os.getpid(),
            "observer_sha256": hashlib.sha256(source).hexdigest(), "expected": {"mode": mode, "shot": shot,
                                                                                 "head_seconds": head},
            "outside": outside, "session_before": before, "session_after": after, "mismatch": mismatch}
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    line = ("SFP1 STEP %s (%s): OK" % (step, label)) if not mismatch else (
        "SFP1 STEP %s (%s): MISMATCH - STOP: %s" % (step, label, "; ".join(mismatch)))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


sfp1_main(globals())
