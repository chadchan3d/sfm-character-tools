# -*- coding: ascii -*-
"""F-01 SFP-1 NQ-S6 observer: STRICTLY READ-ONLY. Run from SFM's Script Editor (Python 2.7):

    NQ_DIR = r"E:\\SFM_U0B_Scratch\\f01-nq-s6"; NQ_REPO = r"E:\\SFM-F01-Pose-Library"
    NQ_LABEL = "NQ-01"; NQ_ANIMSET = "heavy1"
    execfile(NQ_REPO + r"\\real_sfm_qualification\\f01_nq_s6\\observer\\F01_NQS6_Observe.py")

Purpose: the procedural-state evidence that constant_channel_carried_v1 (R3 3.1) needs, read through SFM's own shipped
interfaces only (no model-file parser, no flag change, no key, no Apply):
- CDmeGameModel.ShouldEvaluateProceduralBones() and the evaluateProceduralBones attribute (model-wide);
- the engine-loaded studio header (CDmeGameModel.GetStudioHdr(), the call CPM already uses for its model checksum):
  for every bone, mstudiobone_t pszName, parent, flags, proctype, procindex, physicsbone, and the vs.studio values of
  the STUDIO_PROC_* and BONE_* constants needed to read them;
- CDmeGameModel.GetBoneDefaultPosition / GetBoneDefaultOrientation per bone (recorded; unreadable is recorded);
- for every source-less channel writing one of the model's bones: the log's HasDefaultValue(), GetDefaultValue(),
  usedefaultvalue/defaultvalue attributes, its key range, and GetValue() at fixed sample times inside and outside the
  key range (evaluation only).

It wraps the natively proven S0 observer (f01_full_body_s0, pinned, verified before use, never modified) exactly as
the model survey observer does: S0's observe() for the named animation set, with these reads added inside S0's
read-only window (the document digest of every key and the session state before and after). S0's structural
surprises for a non-Krystal model (no rig registration, ...) are findings, not problems.

It refuses, writing nothing, when the label is not NQ-NN, the file exists, the S0 observer is not the pinned one, or
the shot at the playhead has no single animation set named NQ_ANIMSET. Its only file write is
<NQ_DIR>\\observations\\<NQ_LABEL>.json (exclusive create).
"""
import hashlib
import json
import os
import re
import sys

FORMAT = "F01-NQS6-observation-v1"
S0_REL = os.path.join("real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")
S0_SHA256 = "4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4"
S0_TAIL = b"\n\nmain()\n"
STUDIO_CONSTANTS = ("STUDIO_PROC_AXISINTERP", "STUDIO_PROC_QUATINTERP", "STUDIO_PROC_AIMATBONE",
                    "STUDIO_PROC_AIMATATTACH", "STUDIO_PROC_JIGGLE", "STUDIO_PROC_TWIST_MASTER",
                    "STUDIO_PROC_TWIST_SLAVE", "STUDIO_PROC_POINT_CONSTRAINT", "STUDIO_PROC_ORIENT_CONSTRAINT",
                    "STUDIO_PROC_AIM_CONSTRAINT", "BONE_CALCULATE_MASK", "BONE_PHYSICALLY_SIMULATED",
                    "BONE_PHYSICS_PROCEDURAL", "BONE_ALWAYS_PROCEDURAL", "BONE_SCREEN_ALIGN_SPHERE",
                    "BONE_SCREEN_ALIGN_CYLINDER", "BONE_USED_MASK", "BONE_USED_BY_ANYTHING")
BONE_FIELDS = ("parent", "flags", "proctype", "procindex", "physicsbone", "contents")
SAMPLE_OFFSETS = ("below", "first", "last", "last+1", "current", "current*10", "far")
MAX_BONES = 4096
FINDING_PATTERNS = (r"^expected one rig registration for the animation set",
                    r"^rig handle .* is duplicated$",
                    r"^bone .* has \d+ scene elements$",
                    r"^bone .* is duplicated$",
                    r"^unrecognised bone transform name",
                    r"^the model is not in the shot's scene$",
                    r"^expected one channels clip holding every control channel")


def nq_exec(code, ns):
    exec(code, ns)


def nq_load_s0(repo):
    path = os.path.join(repo, S0_REL)
    with open(path, "rb") as f:
        raw = f.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != S0_SHA256:
        raise RuntimeError("the S0 observer is not the pinned %s (%s); nothing was written" % (S0_SHA256, digest))
    if not raw.endswith(S0_TAIL):
        raise RuntimeError("the S0 observer does not end with its main() call; nothing was written")
    return path, raw[:-len("main()\n")]


def nq_read(fn):
    """{status: READ, value} or {status: UNREADABLE, error}: a failed read is recorded, never inferred."""
    try:
        return {"status": "READ", "value": fn()}
    except Exception as exc:
        return {"status": "UNREADABLE", "error": repr(exc)}


def nq_game_model(ns, animset):
    """The game model proxy: the Python attribute CPM's checksum read uses, else the element attribute."""
    try:
        gm = getattr(animset, "gameModel")
        if gm is not None:
            return gm, "python-attribute"
    except Exception:
        pass
    return ns["attr"](animset, "gameModel"), "element-attribute"


def nq_studio(ns, gm):
    out = {"constants": {}, "header": None, "bones": []}
    try:
        from vs import studio
        for name in STUDIO_CONSTANTS:
            out["constants"][name] = nq_read(lambda name=name: int(getattr(studio, name)))
    except Exception as exc:
        out["constants_error"] = repr(exc)
    hdr = nq_read(lambda: gm.GetStudioHdr())
    if hdr["status"] != "READ" or hdr["value"] is None:
        out["header"] = {"status": "UNREADABLE", "error": hdr.get("error") or "GetStudioHdr returned None"}
        return out
    hdr = hdr["value"]
    count = nq_read(lambda: int(hdr.numbones))
    out["header"] = {"numbones": count, "checksum": nq_read(lambda: int(hdr.checksum))}
    if count["status"] != "READ" or not 0 < count["value"] <= MAX_BONES:
        return out
    vs = sys.modules.get("vs")
    for i in range(count["value"]):
        b = nq_read(lambda i=i: hdr.pBone(i))
        row = {"index": i}
        if b["status"] != "READ" or b["value"] is None:
            row["unreadable"] = b.get("error") or "pBone returned None"
            out["bones"].append(row)
            continue
        bone = b["value"]
        row["name"] = nq_read(lambda: ns["text"](bone.pszName()))
        for f in BONE_FIELDS:
            row[f] = nq_read(lambda f=f: int(getattr(bone, f)))

        def default_position(i=i):
            v = vs.Vector(0.0, 0.0, 0.0)
            ok = gm.GetBoneDefaultPosition(i, v)
            return {"ok": bool(ok), "value": ns["plain"](v)}

        def default_orientation(i=i):
            q = vs.Quaternion(0.0, 0.0, 0.0, 1.0)
            ok = gm.GetBoneDefaultOrientation(i, q)
            return {"ok": bool(ok), "value": ns["plain"](q)}
        row["default_position"] = nq_read(default_position)
        row["default_orientation"] = nq_read(default_orientation)
        out["bones"].append(row)
    return out


def nq_sample_times(first, last, current):
    return {"below": first - 1000000, "first": first, "last": last, "last+1": last + 1, "current": current,
            "current*10": current * 10, "far": 100000000}


def nq_source_less(ns, shot, gm):
    """Every source-less channel of the shot writing a transform of this model's bones: defaults and evaluation."""
    attr, seq, h, opt, text, plain = ns["attr"], ns["seq"], ns["h"], ns["opt"], ns["text"], ns["plain"]
    vs = sys.modules.get("vs")
    bones = dict((h(t), text(t.GetName())) for t in seq(attr(gm, "bones")))
    rows = []
    for clip in ns["channels_clips"](shot):
        for ch in seq(attr(clip, "channels")):
            to = opt(ch, "toElement")
            if to is None or h(to) not in bones or opt(ch, "fromElement") is not None:
                continue
            log = ch.GetLog()
            row = {"channel": text(ch.GetName()), "handle": h(ch), "bone_transform": bones[h(to)],
                   "to_attribute": nq_read(lambda: text(attr(ch, "toAttribute"))),
                   "clip": text(clip.GetName()), "fields": {}}
            for name in ("usedefaultvalue", "defaultvalue", "curveinfo"):
                row["fields"][name] = ns["field"](log, name)
            row["has_default"] = nq_read(lambda: bool(log.HasDefaultValue()))
            if row["has_default"].get("value") is True:
                row["default"] = nq_read(lambda: plain(log.GetDefaultValue()))
            layer = log.GetLayer(0)
            count = int(layer.GetKeyCount())
            row["key_count"] = count
            row["layers"] = int(log.GetNumLayers())
            if count:
                first = ns["ticks"](layer.GetKeyTime(0))
                last = ns["ticks"](layer.GetKeyTime(count - 1))
                current = ns["ticks"](ch.GetCurrentTime())
                row["key_range"] = [first, last]
                row["values_distinct"] = len(set(json.dumps(plain(layer.GetKeyValue(k))) for k in range(count)))
                row["first_value"] = plain(layer.GetKeyValue(0))
                samples = {}
                for label, t in sorted(nq_sample_times(first, last, current).items()):
                    samples[label] = {"ticks": t, "value": nq_read(lambda t=t: plain(log.GetValue(vs.DmeTime_t(t))))}
                row["samples"] = samples
            rows.append(row)
    return rows


def nq_extend(ns, out, shot, animset):
    ext = {}
    try:
        gm, route = nq_game_model(ns, animset)
        ext["game_model_route"] = route
        ext["should_evaluate_procedural_bones"] = nq_read(lambda: bool(gm.ShouldEvaluateProceduralBones()))
        ext["evaluateProceduralBones_attribute"] = ns["field"](gm, "evaluateProceduralBones")
        ext["studio"] = nq_studio(ns, gm)
        ext["source_less_channels"] = nq_source_less(ns, shot, gm)
    except Exception as exc:
        out["problems"].append("NQ-S6 reads failed: %r" % (exc,))
    out["nq"] = ext


def nq_reclassify(out):
    keep, findings = [], []
    for p in out["problems"]:
        if any(re.match(r, p) for r in FINDING_PATTERNS):
            findings.append(p)
        else:
            keep.append(p)
    out["problems"], out["findings"] = keep, findings


def nq_observe(repo, label, animset_name):
    path, source = nq_load_s0(repo)
    ns = {"__name__": "__f01_nqs6_s0__", "S0_ANIMSET": animset_name}
    nq_exec(compile(source, path, "exec"), ns)
    shot = ns["sfmApp"].GetShotAtCurrentTime()
    if shot is None:
        raise RuntimeError("no shot at the playhead; nothing was written")
    names = [ns["text"](a.GetName()) for a in ns["seq"](ns["attr"](shot, "animationSets"))]
    if names.count(animset_name) != 1:
        raise RuntimeError("the shot at the playhead has animation sets %r, not exactly one %r; nothing was written"
                           % (names, animset_name))
    original = ns["survey"]

    def survey(out):
        original(out)
        sets = [a for a in ns["seq"](ns["attr"](shot, "animationSets")) if ns["text"](a.GetName()) == animset_name]
        nq_extend(ns, out, shot, sets[0])

    ns["survey"] = survey
    data = ns["observe"](label)
    data["format"], data["s0_format"], data["s0_observer_sha256"] = FORMAT, ns["FORMAT"], S0_SHA256
    data["animation_sets_in_shot"] = names
    nq_reclassify(data)
    return data


def nq_summary(data, label, name):
    nq = data.get("nq") or {}
    st = nq.get("studio") or {}
    procedural = [b.get("name", {}).get("value") for b in st.get("bones") or []
                  if (b.get("proctype") or {}).get("value") not in (None, 0)]
    unreadable = sum(1 for b in st.get("bones") or [] if "unreadable" in b or
                     any((b.get(f) or {}).get("status") != "READ" for f in BONE_FIELDS))
    return ("NQ %s: %s set=%s should_evaluate=%s header_bones=%s proctype_nonzero=%d %s unreadable_bone_rows=%d "
            "source_less=%d readonly=%s problems=%d findings=%d%s" % (
                label, "OK" if not data["problems"] and data["readonly"]["unchanged"] else "PROBLEM", name,
                (nq.get("should_evaluate_procedural_bones") or {}).get("value"),
                ((st.get("header") or {}).get("numbones") or {}).get("value"), len(procedural), procedural[:12],
                unreadable, len(nq.get("source_less_channels") or []), data["readonly"]["unchanged"],
                len(data["problems"]), len(data["findings"]),
                (" first problem: %s" % data["problems"][0]) if data["problems"] else ""))


def nq_main():
    g = globals()
    root, repo, label, name = g.get("NQ_DIR"), g.get("NQ_REPO"), g.get("NQ_LABEL"), g.get("NQ_ANIMSET")
    if not root or not repo or not name or not label or not re.match(r"^NQ-\d\d$", label):
        raise RuntimeError("Set NQ_DIR, NQ_REPO, NQ_LABEL (NQ-NN) and NQ_ANIMSET first; see the docstring.")
    path = os.path.join(root, "observations", "%s.json" % label)
    if os.path.exists(path):
        raise RuntimeError("%s exists; it is never replaced. Use the next label." % path)
    data = nq_observe(repo, label, name)
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    summary = nq_summary(data, label, name)
    print(summary.encode("ascii", "replace") if sys.version_info[0] == 2 else summary)


nq_main()
