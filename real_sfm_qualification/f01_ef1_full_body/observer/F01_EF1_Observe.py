# -*- coding: ascii -*-
"""F-01 EF-1 Engineer Full body native qualification observation: STRICTLY READ-ONLY. Run from SFM's Script Editor
(Python 2.7). Once per SFM process:

    EF1_DIR = r"<run folder>"; EF1_REPO = r"<repo>"; EF1_ANIMSET = "engineer1"

then, for each procedure step marked Observe:

    EF1_STEP = "B3"; execfile(EF1_REPO + r"\\real_sfm_qualification\\f01_ef1_full_body\\observer\\F01_EF1_Observe.py")

It runs the pinned, unchanged S0 survey observer (real_sfm_qualification/f01_full_body_s0/observer/F01_S0_Survey.py,
verified against its pin before use) for the animation set EF1_ANIMSET under the step's fixed label, inside S0's own
read-only window (the document digest of every key and the session state before and after). It writes
<EF1_DIR>\\observations\\S0-NN.json in S0's format. The Engineer has no rig, so S0's "expected one rig registration
for the animation set, found 0" is moved from problems to findings (that exact text only; every other problem stays).
It then adds one sidecar, <EF1_DIR>\\observations\\S0-NN.ef1.json. The sidecar holds the step and a SHA-256 over every
authored key of every channel OUTSIDE the observed instance's own channels clip, by shot and channel name (the SFP-1
wrapper's method). It then prints whether the timeline editor, shot and playhead match the step.

It refuses, writing nothing, when the step is unknown or already observed, the S0 observer is not its pinned bytes,
the shot at the playhead has no single animation set named EF1_ANIMSET, or that animation set's model is not
models/player/engineer.mdl. Its only file writes are those two files (exclusive create).
"""
import hashlib
import io
import json
import os
import sys

S0_REL = os.path.join("real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")
S0_SHA256 = "4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4"
S0_TAIL = b"\n\nmain()\n"
EXPECTED_MODEL = "models/player/engineer.mdl"
NO_RIG = "expected one rig registration for the animation set, found 0"
ME, CE = "Motion Editor", "Clip Editor"
SHOT, HEAD = "shot1", 0.0
STEPS = {
    # Process A: source session ef1_source.dmx
    "A1": ("S0-01", ME), "A2": ("S0-02", ME), "A3": ("S0-03", ME),
    # Process B: destination session ef1_destination.dmx, after a restart
    "B1": ("S0-04", ME), "B2": ("S0-05", ME), "B3": ("S0-06", ME), "B4": ("S0-07", ME), "B5": ("S0-08", ME),
    "B6": ("S0-09", ME), "B7": ("S0-10", CE), "B8": ("S0-11", CE), "B9": ("S0-12", ME), "B10": ("S0-13", ME),
}


def ef1_exec(code, ns):
    exec(code, ns)


def ef1_load_s0(repo):
    path = os.path.join(repo, S0_REL)
    with io.open(path, "rb") as f:
        raw = f.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != S0_SHA256:
        raise RuntimeError("the S0 observer is not the pinned %s (%s); nothing was written" % (S0_SHA256, digest))
    if not raw.endswith(S0_TAIL):
        raise RuntimeError("the S0 observer does not end with its main() call; nothing was written")
    return path, raw[:-len("main()\n")]


def ef1_reclassify(obs):
    """The no-rig note is a finding for the Engineer; every other problem remains a problem."""
    keep = [p for p in obs.get("problems") or [] if p != NO_RIG]
    obs["findings"] = [p for p in obs.get("problems") or [] if p == NO_RIG]
    obs["problems"] = keep
    return obs


def ef1_outside_digest(og, clip_handle):
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


def ef1_write(path, data):
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)


def ef1_main(g):
    root, repo, step, name = g.get("EF1_DIR"), g.get("EF1_REPO"), g.get("EF1_STEP"), g.get("EF1_ANIMSET")
    if not root or not repo or not name or step not in STEPS:
        raise RuntimeError("Set EF1_DIR, EF1_REPO, EF1_ANIMSET and EF1_STEP (one of %s) first; see the docstring."
                           % ", ".join(sorted(STEPS)))
    label, mode = STEPS[step]
    path = os.path.join(root, "observations", "%s.json" % label)
    sidecar = os.path.join(root, "observations", "%s.ef1.json" % label)
    if os.path.exists(path) or os.path.exists(sidecar):
        raise RuntimeError("%s exists; step %s was already observed. Never repeat a step." % (path, step))
    s0_path, source = ef1_load_s0(repo)
    og = {"__name__": "__ef1_observer__", "S0_ANIMSET": name}
    ef1_exec(compile(source, s0_path, "exec"), og)
    shot = og["sfmApp"].GetShotAtCurrentTime()
    if shot is None:
        raise RuntimeError("no shot at the playhead; nothing was written")
    sets = og["seq"](og["attr"](shot, "animationSets"))
    names = [og["text"](a.GetName()) for a in sets]
    if names.count(name) != 1:
        raise RuntimeError("the shot at the playhead has animation sets %r, not exactly one %r; nothing was written"
                           % (names, name))
    animset = [a for a in sets if og["text"](a.GetName()) == name][0]
    ref = og["field"](og["attr"](animset, "gameModel"), "modelName")
    ref = ref.get("value") if isinstance(ref, dict) and ref.get("status") == "READ" else None
    if ref is None or ref.replace("\\", "/").lower() != EXPECTED_MODEL:
        raise RuntimeError("the animation set %r uses model %r, not %s; nothing was written" % (name, ref,
                                                                                               EXPECTED_MODEL))
    obs = ef1_reclassify(og["observe"](label))
    obs["s0_observer_sha256"] = S0_SHA256
    ef1_write(path, obs)
    clip = (obs.get("channels_clip") or {}).get("clip") or {}
    before = og["session_state"]()
    outside = ef1_outside_digest(og, clip.get("handle"))
    after = og["session_state"]()
    s = obs.get("session_after") or {}
    got = ((s.get("timeline_mode") or {}).get("name"), s.get("current_shot"), s.get("head_seconds"))
    mismatch = []
    if got[0] != mode:
        mismatch.append("timeline %r, expected %r" % (got[0], mode))
    if got[1] != SHOT:
        mismatch.append("shot %r, expected %r" % (got[1], SHOT))
    if not isinstance(got[2], float) or abs(got[2] - HEAD) > 0.0001:
        mismatch.append("playhead %r, expected %.4f" % (got[2], HEAD))
    if obs.get("problems"):
        mismatch.append("observer problems: %d (first: %s)" % (len(obs["problems"]), obs["problems"][0]))
    if before != after:
        mismatch.append("the session changed while the outside digest was read")
    if outside["unreadable"]:
        mismatch.append("outside digest: %d unreadable channels" % outside["unreadable"])
    ef1_write(sidecar, {"format": "F01-EF1-sidecar-v1", "step": step, "label": label, "pid": os.getpid(),
                        "animation_set": name, "observer_sha256": S0_SHA256,
                        "expected": {"mode": mode, "shot": SHOT, "head_seconds": HEAD}, "outside": outside,
                        "session_before": before, "session_after": after, "mismatch": mismatch})
    line = ("EF1 STEP %s (%s): OK" % (step, label)) if not mismatch else (
        "EF1 STEP %s (%s): MISMATCH - STOP: %s" % (step, label, "; ".join(mismatch)))
    print(line.encode("ascii", "replace") if sys.version_info[0] == 2 else line)


ef1_main(globals())
