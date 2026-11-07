# -*- coding: ascii -*-
"""F-01 full-body S3 observation: STRICTLY READ-ONLY. Run from SFM's Script Editor (Python 2.7). Once per SFM process:

    S3_DIR = r"<run folder>"; S3_REPO = r"<repo>"

then, for each procedure step:

    S3_STEP = "B2"; execfile(S3_REPO + r"\\real_sfm_qualification\\f01_full_body_s3\\observer\\F01_S3_Observe.py")

It runs the pinned, unchanged S0 survey observer (real_sfm_qualification/f01_full_body_s0/observer/F01_S0_Survey.py)
under the step's fixed label, which writes <S3_DIR>\\observations\\S0-NN.json, and then adds one sidecar
<S3_DIR>\\observations\\S0-NN.s3.json: the step, and a SHA-256 over every authored key of every channel OUTSIDE the
observed instance's own channels clip (every other animation set, camera, light and shot), by shot and channel name
(no handles), so unrelated animation can be compared within one SFM process. It then prints whether the timeline
editor, shot and playhead match the step. Its only file writes are those two files (exclusive create).
"""
import hashlib
import io
import json
import os
import sys

STEPS = {
    "A1": ("S0-01", "Motion Editor", "shot15", 0.2083), "A2": ("S0-02", "Motion Editor", "shot15", 0.2083),
    "A3": ("S0-03", "Motion Editor", "shot15", 0.2083), "A4": ("S0-04", "Motion Editor", "shot15", 0.2083),
    "A5": ("S0-05", "Motion Editor", "shot15", 0.2083), "A6": ("S0-06", "Motion Editor", "shot15", 0.2083),
    "A7": ("S0-07", "Motion Editor", "shot15", 0.2083),
    "B1": ("S0-08", "Motion Editor", "shot13", 0.3750), "B2": ("S0-09", "Motion Editor", "shot13", 0.3750),
    "B3": ("S0-10", "Motion Editor", "shot13", 0.3750), "B4": ("S0-11", "Motion Editor", "shot13", 0.3750),
    "B5": ("S0-12", "Motion Editor", "shot13", 0.3750), "B6": ("S0-13", "Motion Editor", "shot13", 0.3750),
    "B7": ("S0-14", "Motion Editor", "shot13", 0.3750), "B8": ("S0-15", "Motion Editor", "shot13", 0.3750),
    "B9": ("S0-16", "Clip Editor", "shot13", 0.3750), "B10": ("S0-17", "Clip Editor", "shot13", 0.3750),
    "B11": ("S0-18", "Motion Editor", "shot10", 0.4167), "B12": ("S0-19", "Motion Editor", "shot10", 0.4167),
    "B13": ("S0-20", "Motion Editor", "shot15", 0.2083), "B14": ("S0-21", "Motion Editor", "shot15", 0.2083),
    "B15": ("S0-22", "Motion Editor", "shot15", 0.2083), "B16": ("S0-23", "Motion Editor", "shot15", 0.2083),
    "B17": ("S0-24", "Motion Editor", "shot15", 0.2083),
}


def s3_outside_digest(og, clip_handle):
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


def s3_main(g):
    root, repo, step = g.get("S3_DIR"), g.get("S3_REPO"), g.get("S3_STEP")
    if not root or not repo or step not in STEPS:
        raise RuntimeError("Set S3_DIR, S3_REPO and S3_STEP (one of %s) first; see the docstring."
                           % ", ".join(sorted(STEPS)))
    label, mode, shot, head = STEPS[step]
    sidecar = os.path.join(root, "observations", "%s.s3.json" % label)
    if os.path.exists(sidecar):
        raise RuntimeError("%s exists; step %s was already observed. Never repeat a step." % (sidecar, step))
    observer = os.path.join(repo, "real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")
    with io.open(observer, "rb") as f:
        source = f.read()
    og = {"__name__": "__s3_observer__", "S0_DIR": root, "S0_LABEL": label}
    exec(compile(source, observer, "exec"), og)
    with io.open(os.path.join(root, "observations", "%s.json" % label), "rb") as f:
        obs = json.loads(f.read().decode("utf-8"))
    clip = (obs.get("channels_clip") or {}).get("clip") or {}
    before = og["session_state"]()
    outside = s3_outside_digest(og, clip.get("handle"))
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
    data = {"format": "F01-S3-sidecar-v1", "step": step, "label": label, "pid": os.getpid(),
            "observer_sha256": hashlib.sha256(source).hexdigest(), "expected": {"mode": mode, "shot": shot,
                                                                                 "head_seconds": head},
            "outside": outside, "session_before": before, "session_after": after, "mismatch": mismatch}
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    line = ("S3 STEP %s (%s): OK" % (step, label)) if not mismatch else (
        "S3 STEP %s (%s): MISMATCH - STOP: %s" % (step, label, "; ".join(mismatch)))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


s3_main(globals())
