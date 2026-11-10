# -*- coding: ascii -*-
"""F-01 EC-1 Engineer control-coverage observer: STRICTLY READ-ONLY. Run from SFM's Script Editor (Python 2.7):

    EC_DIR = r"<run folder>"; EC_REPO = r"<repo>"
    EC_LABEL = "EC1-01"; EC_ANIMSET = "engineer"
    execfile(EC_REPO + r"\\real_sfm_qualification\\f01_ec1_engineer\\observer\\F01_EC1_Observe.py")

Purpose: the complete read-only structure of one freshly created, unrigged animation set of the TF2 Engineer
(models/player/engineer.mdl), so that the offline analysis can establish, with CPM's own version 3 classifier,
whether every bone is driven by exactly one direct-FK control (cpm/qualification/F01_NQ03_RESULTS.md section 8).

It composes three natively proven read-only observers. Each is pinned, verified before use and never modified:
- the S0 survey observer (f01_full_body_s0): the document digest and session state before and after (the read-only
  window), and inside it every bone, scene element, control, channel (binding, endpoint indices, mode, log and layer
  types, keys), the shot's and animation set's operators, and the document-wide writer index;
- the model survey observer's extension (f01_model_survey, mc_extend): the control-group tree, the game model's and
  animation set's own attributes, every global flex controller, and every element non-constraint operators reference;
- the NQ-S6 observer's extension (f01_nq_s6, nq_extend): the in-scene model's engine-loaded studio header
  (CDmeGameModel.GetStudioHdr: per bone name, parent, flags, proctype, procindex, physicsbone, contents, default
  position and orientation), ShouldEvaluateProceduralBones, and every source-less channel's log defaults and samples.
The two extensions run inside S0's window, as their own observers ran them. S0's structural surprises for an unrigged
model ("expected one rig registration", ...) are findings, not problems.

It refuses, writing nothing, when the label is not EC1-NN, the file exists, an observer is not its pinned bytes, the
shot at the playhead has no single animation set named EC_ANIMSET (it lists the names it found), or that animation
set's game model is not models/player/engineer.mdl. Its only file write is <EC_DIR>\\observations\\<EC_LABEL>.json
(exclusive create).
"""
import hashlib
import json
import os
import re
import sys

FORMAT = "F01-EC1-observation-v1"
EXPECTED_MODEL = "models/player/engineer.mdl"
PINNED = {
    "s0": (os.path.join("real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py"),
           "4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4", b"\n\nmain()\n"),
    "mc": (os.path.join("real_sfm_qualification", "f01_model_survey", "observer", "F01_MC_Observe.py"),
           "f8d52035048a2e48d41d511968ce7f40caab09235d4a541970b6703bf389b5cd", b"\n\nmc_main()\n"),
    "nq": (os.path.join("real_sfm_qualification", "f01_nq_s6", "observer", "F01_NQS6_Observe.py"),
           "1ac46682e0095ee716dfccbea978b33cec5ef4a0a7386b50f9d94cce2bb893ff", b"\n\nnq_main()\n"),
}
FINDING_PATTERNS = (r"^expected one rig registration for the animation set",
                    r"^rig handle .* is duplicated$",
                    r"^bone .* has \d+ scene elements$",
                    r"^bone .* is duplicated$",
                    r"^unrecognised bone transform name",
                    r"^the model is not in the shot's scene$",
                    r"^expected one channels clip holding every control channel")


def ec_exec(code, ns):
    exec(code, ns)


def ec_load(repo, key):
    """The pinned observer's source without its final entry-point call (refuses on any other bytes)."""
    rel, digest, tail = PINNED[key]
    path = os.path.join(repo, rel)
    with open(path, "rb") as f:
        raw = f.read()
    got = hashlib.sha256(raw).hexdigest()
    if got != digest:
        raise RuntimeError("the %s observer is not the pinned %s (%s); nothing was written" % (key, digest, got))
    if not raw.endswith(tail):
        raise RuntimeError("the %s observer does not end with its entry-point call; nothing was written" % key)
    return path, raw[:-len(tail.lstrip(b"\n"))]


def ec_module(repo, key, name):
    """Define the pinned observer's functions in a namespace of their own (its entry point is never run)."""
    path, source = ec_load(repo, key)
    ns = {"__name__": name}
    ec_exec(compile(source, path, "exec"), ns)
    return ns


def ec_reclassify(out):
    keep, findings = [], []
    for p in out["problems"]:
        if any(re.match(r, p) for r in FINDING_PATTERNS):
            findings.append(p)
        else:
            keep.append(p)
    out["problems"], out["findings"] = keep, findings


def ec_model_ref(ns, animset):
    gm = ns["attr"](animset, "gameModel")
    f = ns["field"](gm, "modelName")
    return f.get("value") if isinstance(f, dict) and f.get("status") == "READ" else None


def ec_observe(repo, label, animset_name):
    s0_path, s0_source = ec_load(repo, "s0")
    mc = ec_module(repo, "mc", "__f01_ec1_mc__")
    nq = ec_module(repo, "nq", "__f01_ec1_nq__")
    ns = {"__name__": "__f01_ec1_s0__", "S0_ANIMSET": animset_name}
    ec_exec(compile(s0_source, s0_path, "exec"), ns)
    shot = ns["sfmApp"].GetShotAtCurrentTime()
    if shot is None:
        raise RuntimeError("no shot at the playhead; nothing was written")
    sets = ns["seq"](ns["attr"](shot, "animationSets"))
    names = [ns["text"](a.GetName()) for a in sets]
    if names.count(animset_name) != 1:
        raise RuntimeError("the shot at the playhead has animation sets %r, not exactly one %r; nothing was written"
                           % (names, animset_name))
    animset = [a for a in sets if ns["text"](a.GetName()) == animset_name][0]
    ref = ec_model_ref(ns, animset)
    if ref is None or ref.replace("\\", "/").lower() != EXPECTED_MODEL:
        raise RuntimeError("the animation set %r uses model %r, not %s; nothing was written"
                           % (animset_name, ref, EXPECTED_MODEL))
    original = ns["survey"]

    def survey(out):
        original(out)
        mc["mc_extend"](ns, out, animset)
        nq["nq_extend"](ns, out, shot, animset)

    ns["survey"] = survey
    data = ns["observe"](label)
    data["format"], data["s0_format"] = FORMAT, ns["FORMAT"]
    data["observers"] = dict((k, PINNED[k][1]) for k in sorted(PINNED))
    data["expected_model"] = EXPECTED_MODEL
    data["animation_sets_in_shot"] = names
    ec_reclassify(data)
    return data


def ec_summary(data, label, name):
    nq = data.get("nq") or {}
    st = nq.get("studio") or {}
    header = st.get("header") or {}
    procedural = [b.get("name", {}).get("value") for b in st.get("bones") or []
                  if (b.get("proctype") or {}).get("value") not in (None, 0)]
    return ("EC1 %s: %s set=%s model=%s rigs=%s bones=%d header_bones=%s checksum=%s proctype_nonzero=%d controls=%d "
            "channels=%d operators=%d groups=%s source_less=%d readonly=%s problems=%d findings=%d%s" % (
                label, "OK" if not data["problems"] and data["readonly"]["unchanged"] else "PROBLEM", name,
                ((data.get("model") or {}).get("modelName") or {}).get("value"),
                [r["rig"]["name"] for r in (data.get("rig") or {}).get("registrations") or []],
                len(data.get("bones") or {}), (header.get("numbones") or {}).get("value"),
                (header.get("checksum") or {}).get("value"), len(procedural), len(data.get("controls") or []),
                len(data.get("channels") or []), len(data.get("operators") or []),
                len((data.get("mc") or {}).get("control_groups") or []), len(nq.get("source_less_channels") or []),
                data["readonly"]["unchanged"], len(data["problems"]), len(data["findings"]),
                (" first problem: %s" % data["problems"][0]) if data["problems"] else ""))


def ec_main():
    g = globals()
    root, repo, label, name = g.get("EC_DIR"), g.get("EC_REPO"), g.get("EC_LABEL"), g.get("EC_ANIMSET")
    if not root or not repo or not name or not label or not re.match(r"^EC1-\d\d$", label):
        raise RuntimeError("Set EC_DIR, EC_REPO, EC_LABEL (EC1-NN) and EC_ANIMSET first; see the docstring.")
    path = os.path.join(root, "observations", "%s.json" % label)
    if os.path.exists(path):
        raise RuntimeError("%s exists; it is never replaced. Use the next label." % path)
    data = ec_observe(repo, label, name)
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    summary = ec_summary(data, label, name)
    print(summary.encode("ascii", "replace") if sys.version_info[0] == 2 else summary)


ec_main()
