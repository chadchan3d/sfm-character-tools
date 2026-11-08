# -*- coding: utf-8 -*-
"""F-01 SFP-1 NQ-S6: offline analysis of the NQ observations (Python 3, -I). Reads only the observation files; writes
NQ_S6_ANALYSIS.json and NQ_S6_ANALYSIS.md (exclusive create).

For every observed model it joins the engine's per-bone declarations (mstudiobone_t proctype/flags from the studio
header) with the scene's bones by index and name, and classifies each control-less (source-less channel) bone:
  declared-procedural   proctype != 0, or a procedural/physics/screen-align flag: an engine-derived output; R3 3.1
                        forbids relabeling it fixed, so constant_channel_carried_v1 must refuse it
  no-declaration        proctype 0 and none of those flags: the necessary per-bone condition for admission holds
  unreadable            any required field unreadable or the index/name join fails: refuse
It also reports, per source-less channel, whether every recorded sample (inside and outside the key range) equals
the constant, and the default-value evidence. Samples are corroboration, never an extrapolation contract.

usage: python -I nq_analyze.py OBSERVATIONS_DIR EVIDENCE_DIR
"""
from __future__ import print_function

import hashlib
import io
import json
import os
import sys

FLAG_NAMES = ("BONE_PHYSICALLY_SIMULATED", "BONE_PHYSICS_PROCEDURAL", "BONE_ALWAYS_PROCEDURAL",
              "BONE_SCREEN_ALIGN_SPHERE", "BONE_SCREEN_ALIGN_CYLINDER")
PROC_NAMES = ("STUDIO_PROC_AXISINTERP", "STUDIO_PROC_QUATINTERP", "STUDIO_PROC_AIMATBONE", "STUDIO_PROC_AIMATATTACH",
              "STUDIO_PROC_JIGGLE", "STUDIO_PROC_TWIST_MASTER", "STUDIO_PROC_TWIST_SLAVE",
              "STUDIO_PROC_POINT_CONSTRAINT", "STUDIO_PROC_ORIENT_CONSTRAINT", "STUDIO_PROC_AIM_CONSTRAINT")


def value(f):
    return f.get("value") if isinstance(f, dict) and f.get("status") == "READ" else None


def analyze(obs):
    nq = obs.get("nq") or {}
    st = nq.get("studio") or {}
    consts = dict((k, value(v)) for k, v in (st.get("constants") or {}).items())
    proc_names = dict((consts.get(n), n) for n in PROC_NAMES if consts.get(n) is not None)
    mask = 0
    mask_complete = all(consts.get(n) is not None for n in FLAG_NAMES)
    for n in FLAG_NAMES:
        mask |= consts.get(n) or 0
    by_index = dict((b["index"], b) for b in st.get("bones") or [])
    out = {"label": obs.get("label"), "animation_set": obs.get("animation_set_name"),
           "model": value((obs.get("model") or {}).get("modelName")),
           "should_evaluate_procedural_bones": value(nq.get("should_evaluate_procedural_bones")),
           "evaluateProceduralBones_attribute": value(nq.get("evaluateProceduralBones_attribute")),
           "header_bones": value(((st.get("header") or {}).get("numbones"))),
           "scene_bones": len(obs.get("bones") or {}), "flag_mask": mask, "flag_mask_complete": mask_complete,
           "declared_procedural": [], "join_problems": [], "control_less": {}, "channels": []}
    for name, b in sorted((obs.get("bones") or {}).items()):
        row = by_index.get(b.get("index"))
        if row is None or value(row.get("name")) != name:
            out["join_problems"].append(name)
    for i, row in sorted(by_index.items()):
        pt, fl = value(row.get("proctype")), value(row.get("flags"))
        if pt not in (None, 0) or (fl is not None and fl & mask):
            out["declared_procedural"].append({"index": i, "name": value(row.get("name")), "proctype": pt,
                                               "proc": proc_names.get(pt), "flags": fl, "flag_hits": fl & mask
                                               if fl is not None else None})
    names_by_transform = {}
    for ch in nq.get("source_less_channels") or []:
        bone = ch["bone_transform"].split("(", 1)[1][:-1] if "(" in ch["bone_transform"] else ch["bone_transform"]
        names_by_transform.setdefault(bone, []).append(ch)
        const = ch.get("first_value")
        samples = ch.get("samples") or {}
        out["channels"].append({
            "channel": ch["channel"], "bone": bone, "key_count": ch.get("key_count"), "key_range": ch.get("key_range"),
            "values_distinct": ch.get("values_distinct"), "usedefaultvalue": value((ch.get("fields") or {}).get(
                "usedefaultvalue")), "has_default": value(ch.get("has_default")), "default": value(ch.get("default"))
            if ch.get("default") else None,
            "samples_equal_constant": all(value(s.get("value")) == const for s in samples.values()) if samples else
            None, "samples_unreadable": sorted(k for k, s in samples.items() if (s.get("value") or {}).get("status")
                                               != "READ")})
    index_of = dict((n, b.get("index")) for n, b in (obs.get("bones") or {}).items())
    for bone in sorted(names_by_transform):
        row = by_index.get(index_of.get(bone))
        fields = [value(row.get(f)) for f in ("proctype", "flags")] if row else [None, None]
        if row is None or value(row.get("name")) != bone or None in fields or not mask_complete:
            cls = "unreadable"
        elif fields[0] != 0 or fields[1] & mask:
            cls = "declared-procedural"
        else:
            cls = "no-declaration"
        out["control_less"][bone] = {"class": cls, "proctype": fields[0], "proc": proc_names.get(fields[0]),
                                     "flags": fields[1]}
    return out


def markdown(results):
    lines = ["# NQ-S6 analysis", ""]
    for r in results:
        lines += ["## %s (%s, %s)" % (r["label"], r["animation_set"], r["model"]), "",
                  "- ShouldEvaluateProceduralBones: %r; attribute: %r" % (r["should_evaluate_procedural_bones"],
                                                                         r["evaluateProceduralBones_attribute"]),
                  "- header bones %r, scene bones %r, join problems %r" % (r["header_bones"], r["scene_bones"],
                                                                           r["join_problems"][:8]),
                  "- declared procedural: %s" % ", ".join("%s (%s, flags %r)" % (d["name"], d["proc"] or d["proctype"],
                                                                                 d["flags"])
                                                         for d in r["declared_procedural"]) or "none", ""]
        lines += ["| control-less bone | class | proctype | flags |", "|---|---|---|---|"]
        for bone, c in sorted(r["control_less"].items()):
            lines.append("| %s | %s | %s | %r |" % (bone, c["class"], c["proc"] or c["proctype"], c["flags"]))
        lines += ["", "| channel | keys | range | distinct | samples = constant | usedefaultvalue | HasDefaultValue |",
                  "|---|---|---|---|---|---|---|"]
        for ch in r["channels"]:
            lines.append("| %s | %r | %r | %r | %r | %r | %r |" % (ch["channel"], ch["key_count"], ch["key_range"],
                                                                 ch["values_distinct"], ch["samples_equal_constant"],
                                                                 ch["usedefaultvalue"], ch["has_default"]))
        lines.append("")
    return "\n".join(lines) + "\n"


def write_exclusive(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return hashlib.sha256(data).hexdigest()


def main(argv):
    src, dst = argv[1], argv[2]
    results, sources = [], {}
    for name in sorted(n for n in os.listdir(src) if n.startswith("NQ-") and n.endswith(".json")):
        raw = io.open(os.path.join(src, name), "rb").read()
        sources[name] = hashlib.sha256(raw).hexdigest()
        results.append(analyze(json.loads(raw.decode("utf-8"))))
    data = json.dumps({"format": "F01-NQS6-analysis-v1", "sources": sources, "results": results}, indent=1,
                      sort_keys=True).encode("utf-8")
    print("NQ_S6_ANALYSIS.json", write_exclusive(os.path.join(dst, "NQ_S6_ANALYSIS.json"), data))
    print("NQ_S6_ANALYSIS.md", write_exclusive(os.path.join(dst, "NQ_S6_ANALYSIS.md"), markdown(results).encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
