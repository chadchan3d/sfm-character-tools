# -*- coding: utf-8 -*-
"""F-01 NQ-03: offline analysis of the header inventory (Python 3, -I). Reads only the NQ03 observation files and, when
present, Q/evidence/resolution.json; writes NQ03_ANALYSIS.json and NQ03_ANALYSIS.md (exclusive create).

Per model:
  candidate             read, every bone row readable, and no bone declares a procedure (proctype 0 and none of the
                        procedural / physics / screen-align flags): eligible for the first generic version 3 Full
                        body qualification, subject to a later check that its animation set gives every bone a control
                        and has no rig
  declared-procedural   at least one bone declares a procedure (listed with its type): Full body would refuse it under
                        R3 as written (NQ-S6)
  unreadable            the header, a bone row or a required constant is unreadable: no conclusion
  not-loaded            the model cache returned no handle, or an error model
A header declaration is the engine's own data; it is not evidence of how the model evaluates.

usage: python -I nq03_analyze.py OBSERVATIONS_DIR EVIDENCE_DIR
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
BONE_FIELDS = ("parent", "flags", "proctype", "procindex", "physicsbone")


def value(f):
    return f.get("value") if isinstance(f, dict) and f.get("status") == "READ" else None


def classify(model, consts):
    proc_names = dict((consts.get(n), n) for n in PROC_NAMES if consts.get(n) is not None)
    mask_complete = all(consts.get(n) is not None for n in FLAG_NAMES)
    mask = 0
    for n in FLAG_NAMES:
        mask |= consts.get(n) or 0
    row = {"path": model.get("path"), "family": model.get("family"), "status": model.get("status"),
           "header_name": value(model.get("name")), "numbones": value(model.get("numbones")), "declared": [],
           "attachments": value((model.get("attachments") or {}).get("count")),
           "flex_drivers": value((model.get("flex_drivers") or {}).get("count"))}
    if model.get("status") != "read" or value(model.get("error_model")) is not False:
        row["class"] = "not-loaded"
        return row
    bones = model.get("bones") or []
    unreadable = not bones or not mask_complete or row["numbones"] != len(bones) or any(
        "unreadable" in b or any(value(b.get(f)) is None for f in BONE_FIELDS) or value(b.get("name")) is None
        for b in bones)
    for b in bones:
        pt, fl = value(b.get("proctype")), value(b.get("flags"))
        if pt not in (None, 0) or (fl is not None and fl & mask):
            row["declared"].append({"name": value(b.get("name")), "proc": proc_names.get(pt, pt), "flags": fl})
    row["class"] = "unreadable" if unreadable else ("declared-procedural" if row["declared"] else "candidate")
    return row


def analyze(obs, resolution=None):
    inv = obs.get("nq03") or {}
    consts = dict((k, value(v)) for k, v in (inv.get("constants") or {}).items())
    files = dict((r["path"], r) for r in (resolution or {}).get("models") or [])
    rows = []
    for model in inv.get("models") or []:
        row = classify(model, consts)
        f = files.get(model.get("path")) or {}
        row["resolved"], row["file_sha256"] = f.get("game_relative"), f.get("sha256")
        rows.append(row)
    return {"label": obs.get("label"), "readonly": (obs.get("readonly") or {}).get("unchanged"),
            "problems": obs.get("problems"), "models": rows,
            "candidates": [r["path"] for r in rows if r["class"] == "candidate"]}


def markdown(results):
    lines = ["# NQ-03 header inventory analysis", ""]
    for r in results:
        lines += ["## %s (read-only window unchanged: %r; problems: %d)" % (r["label"], r["readonly"],
                                                                          len(r["problems"] or [])), "",
                  "Candidates with no procedural declaration: %s" % (", ".join(r["candidates"]) or "none"), "",
                  "| Model | Family | Resolved file | Bones | Class | Declared procedural |", "|---|---|---|---|---|---|"]
        for m in r["models"]:
            declared = ", ".join("%s (%s)" % (d["name"], d["proc"]) for d in m["declared"][:8])
            if len(m["declared"]) > 8:
                declared += " and %d more" % (len(m["declared"]) - 8)
            lines.append("| %s | %s | %s | %s | %s | %s |" % (m["path"], m["family"], m["resolved"], m["numbones"],
                                                              m["class"], declared or "-"))
        lines.append("")
    lines.append("A header declaration is the engine's own data, not evidence of how the model evaluates.")
    return "\n".join(lines) + "\n"


def write_exclusive(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return hashlib.sha256(data).hexdigest()


def main(argv):
    src, dst = argv[1], argv[2]
    res_path = os.path.join(dst, "resolution.json")
    resolution = json.loads(io.open(res_path, "rb").read().decode("utf-8")) if os.path.isfile(res_path) else None
    results, sources = [], {}
    for name in sorted(n for n in os.listdir(src) if n.startswith("NQ03-") and n.endswith(".json")):
        raw = io.open(os.path.join(src, name), "rb").read()
        sources[name] = hashlib.sha256(raw).hexdigest()
        results.append(analyze(json.loads(raw.decode("utf-8")), resolution))
    data = json.dumps({"format": "F01-NQ03-analysis-v1", "sources": sources, "results": results}, indent=1,
                      sort_keys=True).encode("utf-8")
    print("NQ03_ANALYSIS.json", write_exclusive(os.path.join(dst, "NQ03_ANALYSIS.json"), data))
    print("NQ03_ANALYSIS.md", write_exclusive(os.path.join(dst, "NQ03_ANALYSIS.md"), markdown(results).encode("utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
