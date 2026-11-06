# -*- coding: utf-8 -*-
"""F-01 full-body S0: offline validation and structural analysis of survey observations (Python 3, read-only).

usage: python -I s0_analyze.py OBSERVATIONS_DIR OUT_DIR [PRIMARY_LABEL]

Validates every <label>.json against the S0 evidence schema (EVIDENCE_SCHEMA.md), then writes OUT_DIR/S0_REPORT.json
and OUT_DIR/S0_REPORT.md (exclusive create). Classification uses binding evidence only (which channel writes which
transform, from which element; which operator slaves which DAG); names are used only to label rows and to select
the rows an S0 question names. Nothing here decides the coverage contract: the report is evidence for it.
"""
import json
import math
import os
import re
import sys

FORMAT = "F01-S0-survey-v1"
LABEL_RE = re.compile(r"^S0-\d\d[a-z]?$")
CONSTRAINT_RE = re.compile(r"^DmeRig\w*ConstraintOperator$")
KNOWN_CONSTRAINTS = ("DmeRigPointConstraintOperator", "DmeRigOrientConstraintOperator", "DmeRigIKConstraintOperator")
TOP_LEVEL = {"format": str, "label": str, "pid": int, "problems": list, "document": (str, type(None)),
             "session_before": dict, "session_after": dict, "readonly": dict}
SURVEY = {"shot": dict, "animation_set": dict, "time": dict, "model": dict, "scene": dict, "bones": dict,
          "rig": dict, "controls": list, "channels": list, "operators": list, "writer_index": dict}
POS_TOL = 1e-4
ANGLE_TOL_DEG = 0.01


# --- validation ------------------------------------------------------------------------------------------------

def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate(obs):
    """Schema problems of one observation (empty list = valid). Survey sections are required unless the observer
    itself reported why it could not produce them."""
    out = []
    if not isinstance(obs, dict):
        return ["not a JSON object"]
    for k, t in TOP_LEVEL.items():
        if k not in obs:
            out.append("missing %s" % k)
        elif not isinstance(obs[k], t) or (t is int and not _is_int(obs[k])):
            out.append("%s has the wrong type" % k)
    if obs.get("format") != FORMAT:
        out.append("format is not %s" % FORMAT)
    if isinstance(obs.get("label"), str) and not LABEL_RE.match(obs["label"]):
        out.append("label %r is not S0-NN" % obs["label"])
    for side in ("session_before", "session_after"):
        s = obs.get(side)
        if isinstance(s, dict):
            for k in ("head_seconds", "head_ticks", "timeline_mode", "undo", "current_shot"):
                if k not in s:
                    out.append("%s.%s missing" % (side, k))
            if "head_ticks" in s and not _is_int(s["head_ticks"]):
                out.append("%s.head_ticks is not an integer" % side)
    ro = obs.get("readonly")
    if isinstance(ro, dict):
        for k in ("digest_before", "digest_after", "unchanged"):
            if k not in ro:
                out.append("readonly.%s missing" % k)
        for k in ("digest_before", "digest_after"):
            d = ro.get(k)
            if not isinstance(d, dict) or not isinstance(d.get("sha256"), str) or len(d["sha256"]) != 64:
                out.append("readonly.%s is not a digest" % k)
        if not isinstance(ro.get("unchanged"), bool):
            out.append("readonly.unchanged is not a boolean")
    if out or obs.get("problems"):
        return out
    for k, t in SURVEY.items():
        if not isinstance(obs.get(k), t):
            out.append("survey section %s missing or of the wrong type" % k)
    if out:
        return out
    if not _is_int(obs["time"].get("t_chan")):
        out.append("time.t_chan is not an integer")
    for name, b in obs["bones"].items():
        for k in ("index", "transform", "dag", "parent_bone", "local_position", "local_orientation", "scale"):
            if k not in b:
                out.append("bone %s: %s missing" % (name, k))
                break
        else:
            if len(b["local_position"]) != 3 or len(b["local_orientation"]) != 4:
                out.append("bone %s: malformed transform" % name)
    for name, r in obs["rig"].get("handles", {}).items():
        for k in ("id", "parents", "local_position", "local_orientation"):
            if k not in r:
                out.append("rig handle %s: %s missing" % (name, k))
                break
    for i, ch in enumerate(obs["channels"]):
        where = "channel %d (%s)" % (i, (ch.get("id") or {}).get("name"))
        if "error" in ch:
            out.append("%s: unreadable" % where)
            continue
        for k in ("id", "binding", "current_ticks", "log", "layers", "value_at_clock", "value_at_mapped"):
            if k not in ch:
                out.append("%s: %s missing" % (where, k))
                break
        else:
            if ch["current_ticks"] is not None and not _is_int(ch["current_ticks"]):
                out.append("%s: current_ticks is not an integer" % where)
            for layer in ch["layers"]:
                if not _is_int(layer.get("key_count")) or "keys_sha256" not in layer:
                    out.append("%s: malformed layer" % where)
    for i, op in enumerate(obs["operators"]):
        if "error" in op or not isinstance(op.get("id"), dict):
            out.append("operator %d unreadable" % i)
    wi = obs["writer_index"]
    if not isinstance(wi.get("destinations"), dict) or not isinstance(wi.get("slave_targets"), dict):
        out.append("writer_index malformed")
    return out


# --- helpers ---------------------------------------------------------------------------------------------------

def value(f):
    return f.get("value") if isinstance(f, dict) and f.get("status") == "READ" else None


def q_angle_deg(a, b):
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    d = min(1.0, abs(sum(x * y for x, y in zip(a, b))) / (na * nb))
    return math.degrees(2.0 * math.acos(d))


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def is_control(ident):
    return bool(ident) and ident.get("type", "").endswith("Control")


# --- structural analysis of one observation --------------------------------------------------------------------

def classify(obs):
    bones, handles = obs["bones"], obs["rig"]["handles"]
    t_chan = obs["time"]["t_chan"]
    owner_of_transform, owner_of_dag = {}, {}
    for n, b in bones.items():
        owner_of_transform[b["transform"]["handle"]] = ("bone", n)
        if b["dag"] is not None:
            owner_of_dag[b["dag"]] = ("bone", n)
    for n, r in handles.items():
        if r.get("transform"):
            owner_of_transform[r["transform"]["handle"]] = ("handle", n)
        owner_of_dag[r["id"]["handle"]] = ("handle", n)
    scene = obs["scene"]

    def label_dag(hd):
        o = owner_of_dag.get(hd)
        if o:
            return "%s:%s" % o
        row = scene.get(str(hd))
        return "%s:%s" % (row["type"], row["name"]) if row else "unknown:%s" % hd

    instance_channels = dict((c["id"]["handle"], c) for c in obs["channels"] if "error" not in c)
    destinations = obs["writer_index"]["destinations"]
    doc_slaves = obs["writer_index"]["slave_targets"]

    # Operators: constraint slaves, targets, poles, weights.
    slaved = {}
    op_rows = []
    target_roles = {}
    for op in obs["operators"]:
        kind = op["id"]["type"]
        row = {"type": kind, "name": op["id"]["name"], "owners": op.get("owners"), "slaves": {}, "targets": [],
               "pvTarget": None, "solver": dict((k, value(v)) for k, v in (op.get("solver") or {}).items()),
               "known": kind in KNOWN_CONSTRAINTS}
        for slot, s in (op.get("slaves") or {}).items():
            tgt = s.get("target")
            if tgt:
                slaved.setdefault(tgt["handle"], []).append((kind, op["id"]["name"], slot))
                row["slaves"][slot] = label_dag(tgt["handle"])
        for t in op.get("targets") or []:
            tgt = t.get("target")
            lab = label_dag(tgt["handle"]) if tgt else None
            weight_writers = destinations.get("%d:targetWeight" % t["id"]["handle"], [])
            row["targets"].append({"target": lab, "weight": value(t.get("targetWeight")),
                                   "weight_channels": [w["name"] for w in weight_writers]})
            if tgt:
                target_roles.setdefault(tgt["handle"], []).append("%s target of %s" % (kind, op["id"]["name"]))
        if op.get("pvTarget"):
            row["pvTarget"] = label_dag(op["pvTarget"]["handle"])
            target_roles.setdefault(op["pvTarget"]["handle"], []).append("pole of %s" % op["id"]["name"])
        op_rows.append(row)
    # Document-wide slaves the instance's operator lists do not hold.
    for hd, rows in doc_slaves.items():
        for r in rows:
            entry = (r["type"], "document operator %d" % r["operator"], r["slot"])
            if not any(e[0] == r["type"] and e[2] == r["slot"] for e in slaved.get(int(hd), [])):
                slaved.setdefault(int(hd), []).append(entry)

    def writers(transform_handle, attr):
        rows = destinations.get("%d:%s" % (transform_handle, attr), [])
        return [dict(w, kind="control" if is_control(w.get("from")) else "operator" if w.get("from") else "none",
                     in_instance=w["channel"] in instance_channels) for w in rows]

    def channel_evidence(w, local):
        ch = instance_channels.get(w["channel"])
        if ch is None:
            return {"channel": w["name"], "in_instance": False}
        layers = ch["layers"]
        ev = {"channel": w["name"], "in_instance": True, "layers": len(layers),
              "layer_types": [l["type"] for l in layers], "keys": [l["key_count"] for l in layers],
              "distinct": [l["distinct_values"] for l in layers], "clock": ch["current_ticks"],
              "clock_is_mapped": ch["current_ticks"] == t_chan, "mode": value(ch["binding"].get("mode")),
              "key_at_mapped": [l["key_at_mapped"] for l in layers],
              "curve_info": value((ch.get("log_fields") or {}).get("curveinfo"))}
        mapped = ch.get("value_at_mapped")
        if isinstance(mapped, list) and local is not None and len(mapped) == len(local):
            ev["mapped_equals_local"] = (q_angle_deg(mapped, local) <= ANGLE_TOL_DEG if len(local) == 4
                                         else dist(mapped, local) <= POS_TOL)
        return ev

    def translation_kind(ev):
        if not ev.get("in_instance"):
            return "outside-instance"
        d = ev["distinct"]
        if len(d) != 1:
            return "layered"
        if d[0] == 1 and ev.get("mapped_equals_local") is not False:
            return "constant (structural-offset candidate)"
        return "animated translation"

    bone_rows = {}
    for n, b in sorted(bones.items()):
        th = b["transform"]["handle"]
        wp, wo = writers(th, "position"), writers(th, "orientation")
        drivers = slaved.get(b["dag"], []) if b["dag"] is not None else []
        known = [d for d in drivers if d[0] in KNOWN_CONSTRAINTS]
        other_constraint = [d for d in drivers if d[0] not in KNOWN_CONSTRAINTS and CONSTRAINT_RE.match(d[0])]
        unknown = [d for d in drivers if d[0] not in KNOWN_CONSTRAINTS and not CONSTRAINT_RE.match(d[0])]
        ctrl = [w for w in wp + wo if w["kind"] == "control"]
        opw = [w for w in wp + wo if w["kind"] == "operator"]
        if b["dag"] is None:
            cls = "unclassified (no unique scene element)"
        elif known or other_constraint:
            cls = "constrained"
        elif unknown:
            cls = "driven by an unknown operator"
        elif opw:
            cls = "operator-driven"
        elif len([w for w in wp if w["kind"] == "control"]) > 1 or len([w for w in wo if w["kind"] == "control"]) > 1:
            cls = "competing writers"
        elif ctrl:
            cls = "direct FK"
        else:
            cls = "no writer (structurally fixed or driven outside the observed bindings)"
        row = {"class": cls, "parent": b.get("parent_bone"), "index": b["index"],
               "drivers": ["%s %s (%s)" % d for d in drivers],
               "position_writers": [w["name"] for w in wp], "orientation_writers": [w["name"] for w in wo],
               "scale": value(b.get("scale"))}
        if cls == "constrained":
            row["dormant_channels"] = [w["name"] for w in ctrl]
        if cls == "direct FK":
            row["orientation"] = [channel_evidence(w, b["local_orientation"]) for w in wo]
            row["position"] = [channel_evidence(w, b["local_position"]) for w in wp]
            row["translation"] = [translation_kind(e) for e in row["position"]] or ["no position channel"]
        bone_rows[n] = row

    handle_rows = {}
    for n, r in sorted(handles.items()):
        th = (r.get("transform") or {}).get("handle")
        wp = writers(th, "position") if th else []
        wo = writers(th, "orientation") if th else []
        drivers = slaved.get(r["id"]["handle"], [])
        handle_rows[n] = {"parents": [label_dag(p) for p in r.get("parents", [])], "in_scene": r.get("in_scene"),
                          "position_writers": [w["name"] for w in wp], "orientation_writers": [w["name"] for w in wo],
                          "constrained_by": ["%s %s (%s)" % d for d in drivers],
                          "roles": target_roles.get(r["id"]["handle"], []),
                          "position": [channel_evidence(w, r.get("local_position")) for w in wp],
                          "orientation": [channel_evidence(w, r.get("local_orientation")) for w in wo],
                          "scale": value(r.get("scale"))}

    # Controls: each control's channels and what they drive.
    control_rows = {}
    channel_class = {}
    for c in obs["controls"]:
        name = c["id"]["name"]
        rows = []
        for a in ("positionChannel", "orientationChannel", "channel", "leftvaluechannel", "rightvaluechannel"):
            ch_ident = value(c["attributes"].get(a))
            if not ch_ident:
                continue
            ch = instance_channels.get(ch_ident["handle"])
            to = value(ch["binding"].get("toElement")) if ch else None
            to_attr = value(ch["binding"].get("toAttribute")) if ch else None
            owner = owner_of_transform.get(to["handle"]) if to else None
            rows.append({"attribute": a, "channel": ch_ident["name"], "drives": ("%s:%s" % owner) if owner else
                         ("%s:%s" % (to["type"], to["name"]) if to else None), "to_attribute": to_attr})
        control_rows[name] = {"type": c["id"]["type"], "channels": rows}

    for hd, ch in instance_channels.items():
        to = value(ch["binding"].get("toElement"))
        to_attr = value(ch["binding"].get("toAttribute"))
        frm = value(ch["binding"].get("fromElement"))
        owner = owner_of_transform.get(to["handle"]) if to else None
        if to_attr == "targetWeight":
            k = "constraint weight"
        elif owner and owner[0] == "handle":
            k = "rig handle"
        elif owner and owner[0] == "bone":
            bc = bone_rows[owner[1]]["class"]
            k = ("dormant (constrained bone)" if bc == "constrained" else "bone, operator output" if not
                 is_control(frm) else "direct FK bone" if bc == "direct FK" else "bone (%s)" % bc)
        else:
            k = "other (flex, scale, eye or non-transform)"
        channel_class[hd] = k

    clocks = {}
    for hd, k in channel_class.items():
        ch = instance_channels[hd]
        row = clocks.setdefault(k, {"channels": 0, "at_mapped": 0, "unreadable": 0, "other_clocks": {}})
        row["channels"] += 1
        if ch["current_ticks"] is None:
            row["unreadable"] += 1
        elif ch["current_ticks"] == t_chan:
            row["at_mapped"] += 1
        else:
            key = str(ch["current_ticks"])
            row["other_clocks"][key] = row["other_clocks"].get(key, 0) + 1
    off_clock_names = sorted(instance_channels[hd]["id"]["name"] for hd in instance_channels
                             if instance_channels[hd]["current_ticks"] != t_chan)

    scale = {"model": value((obs["model"].get("state") or {}).get("scale")),
             "non_unit_bone_scale": sorted(n for n, b in bones.items() if value(b.get("scale")) not in (None, 1.0)),
             "scale_channels": sorted(c["id"]["name"] for c in instance_channels.values()
                                      if "scale" in (c["id"]["name"] or "").lower()
                                      or "scale" in (value(c["binding"].get("toAttribute")) or "").lower())}
    counts = {}
    for r in bone_rows.values():
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    unaccounted = sorted(n for n, r in bone_rows.items() if r["class"].startswith("unclassified")
                         or r["class"].startswith("driven by an unknown") or r["class"] == "competing writers")
    return {"t_chan": t_chan, "bone_classes": counts, "bones": bone_rows, "rig_handles": handle_rows,
            "operators": op_rows, "controls": control_rows, "clocks_by_channel_class": clocks,
            "off_clock_channels": off_clock_names, "scale": scale,
            "unaccounted_bones": unaccounted, "operator_types_in_document": obs["writer_index"].get("operator_types"),
            "coverage": {"bones": len(bones), "classified": len(bones) - len([n for n in bone_rows if bone_rows[n][
                "class"].startswith("unclassified")]), "rig_handles": len(handles), "controls": len(obs["controls"]),
                "instance_channels": len(instance_channels)}}


def structure_signature(obs):
    bones = sorted((n, b.get("parent_bone")) for n, b in obs["bones"].items())
    names = dict((str(r["id"]["handle"]), n) for n, r in obs["rig"]["handles"].items())
    scene = obs["scene"]
    handles = sorted((n, tuple(names.get(str(p), scene.get(str(p), {}).get("name")) for p in r.get("parents", [])))
                     for n, r in obs["rig"]["handles"].items())
    ops = sorted((op["id"]["type"], op["id"]["name"]) for op in obs["operators"])
    controls = sorted((c["id"]["type"], c["id"]["name"]) for c in obs["controls"])
    return {"bones": bones, "handles": handles, "operators": ops, "controls": controls}


def compare_instances(a, b):
    sa, sb = structure_signature(a), structure_signature(b)
    same = dict((k, sa[k] == sb[k]) for k in sa)
    posture = []
    for n in sorted(set(a["bones"]) & set(b["bones"])):
        x, y = a["bones"][n], b["bones"][n]
        posture.append((n, round(q_angle_deg(x["local_orientation"], y["local_orientation"]), 4),
                        round(dist(x["local_position"], y["local_position"]), 6)))
    moved = [p for p in posture if p[1] > ANGLE_TOL_DEG or p[2] > POS_TOL]
    return {"structure_equal": same, "bones_compared": len(posture), "bones_differing": len(moved),
            "largest_rotation": sorted(moved, key=lambda p: -p[1])[:15],
            "local_position_differences": sorted([p for p in moved if p[2] > POS_TOL], key=lambda p: -p[2])[:30]}


def analyze(observations, primary=None):
    report = {"format": "F01-S0-report-v1", "observations": [], "valid": True}
    valid = []
    for obs in observations:
        problems = validate(obs)
        s = obs.get("session_after") or {}
        report["observations"].append({
            "label": obs.get("label"), "pid": obs.get("pid"), "shot": s.get("current_shot"),
            "head_seconds": s.get("head_seconds"), "mode": (s.get("timeline_mode") or {}).get("name"),
            "t_chan": (obs.get("time") or {}).get("t_chan"),
            "animation_set": ((obs.get("animation_set") or {}).get("id") or {}).get("handle"),
            "readonly_unchanged": (obs.get("readonly") or {}).get("unchanged"),
            "observer_problems": obs.get("problems"), "schema_problems": problems})
        if problems or obs.get("problems"):
            report["valid"] = False
        else:
            valid.append(obs)
    digests = {}
    for obs in observations:
        ro = obs.get("readonly") or {}
        for k in ("digest_before", "digest_after"):
            d = (ro.get(k) or {}).get("sha256")
            if d:
                digests.setdefault(obs.get("pid"), set()).add(d)
    report["readonly"] = {
        "every_observation_unchanged": all((o.get("readonly") or {}).get("unchanged") is True for o in observations),
        "one_document_digest_per_process": all(len(v) == 1 for v in digests.values()),
        "processes": len(digests)}
    if not valid:
        return report
    by_label = dict((o["label"], o) for o in valid)
    if primary is None:
        primary = next((o["label"] for o in valid
                        if ((o["session_after"].get("timeline_mode") or {}).get("name") == "Motion Editor")),
                       valid[0]["label"])
    report["primary"] = primary
    report["analysis"] = classify(by_label[primary])
    report["clocks_by_observation"] = dict(
        (o["label"], {"mode": (o["session_after"].get("timeline_mode") or {}).get("name"),
                      "head_seconds": o["session_after"].get("head_seconds"), "t_chan": o["time"]["t_chan"],
                      "classes": classify(o)["clocks_by_channel_class"]}) for o in valid)
    base = by_label[primary]
    report["instances"] = {}
    for o in valid:
        if o["animation_set"]["id"]["handle"] != base["animation_set"]["id"]["handle"]:
            report["instances"][o["label"]] = compare_instances(base, o)
    same_instance = [o for o in valid if o["animation_set"]["id"]["handle"] == base["animation_set"]["id"]["handle"]
                     and o["label"] != primary]
    report["same_instance_other_times"] = dict((o["label"], compare_instances(base, o)) for o in same_instance)
    return report


def markdown(report):
    L = ["# F-01 full-body S0 survey report", "",
         "Generated offline by `s0_analyze.py` from the observations listed below. Evidence only: it does not fix "
         "the coverage contract.", ""]
    L.append("| Label | pid | Shot | Head (s) | Mode | t_chan | Read-only | Problems |")
    L.append("|---|---|---|---|---|---|---|---|")
    for o in report["observations"]:
        L.append("| %s | %s | %s | %s | %s | %s | %s | %d |" % (
            o["label"], o["pid"], o["shot"], o["head_seconds"], o["mode"], o["t_chan"], o["readonly_unchanged"],
            len(o["observer_problems"] or []) + len(o["schema_problems"])))
    ro = report["readonly"]
    L += ["", "Read-only proof: every observation unchanged **%s**; one document digest per SFM process **%s**." % (
        ro["every_observation_unchanged"], ro["one_document_digest_per_process"]), ""]
    if "analysis" not in report:
        L.append("**No valid observation; no analysis.**")
        return "\n".join(L) + "\n"
    a = report["analysis"]
    L += ["## Primary observation %s" % report["primary"], "", "Bone classes (binding evidence):", ""]
    for k, v in sorted(a["bone_classes"].items()):
        L.append("- %s: %d" % (k, v))
    L += ["", "Unaccounted bones: %s" % (", ".join(a["unaccounted_bones"]) or "none"), "",
          "## Channel clocks by class", "", "| Observation | Mode | Class | Channels | At mapped tick | Other clocks |",
          "|---|---|---|---|---|---|"]
    for lab, row in sorted(report["clocks_by_observation"].items()):
        for k, v in sorted(row["classes"].items()):
            L.append("| %s | %s | %s | %d | %d | %s |" % (lab, row["mode"], k, v["channels"], v["at_mapped"],
                                                          v["other_clocks"] or "-"))
    L += ["", "## Rig handles", "", "| Handle | Parents | Constrained by | Roles |", "|---|---|---|---|"]
    for n, r in sorted(a["rig_handles"].items()):
        L.append("| %s | %s | %s | %s |" % (n, ", ".join(r["parents"]), "; ".join(r["constrained_by"]) or "-",
                                            "; ".join(r["roles"]) or "-"))
    L += ["", "## Operators", "", "| Type | Name | Slaves | Targets (weight) | Pole | Solver |", "|---|---|---|---|---|---|"]
    for op in a["operators"]:
        L.append("| %s | %s | %s | %s | %s | %s |" % (
            op["type"], op["name"], ", ".join("%s=%s" % kv for kv in sorted(op["slaves"].items())) or "-",
            ", ".join("%s (%s)" % (t["target"], t["weight"]) for t in op["targets"]) or "-", op["pvTarget"] or "-",
            json.dumps(op["solver"], sort_keys=True) if op["solver"] else "-"))
    L += ["", "## Bones", "", "| Bone | Parent | Class | Drivers / dormant | Translation |", "|---|---|---|---|---|"]
    for n, r in sorted(a["bones"].items(), key=lambda kv: kv[1]["index"] if kv[1]["index"] is not None else 1e9):
        extra = "; ".join(r["drivers"]) or ""
        if r.get("dormant_channels"):
            extra += " | dormant: " + ", ".join(r["dormant_channels"])
        L.append("| %s | %s | %s | %s | %s |" % (n, r["parent"], r["class"], extra or "-",
                                                 ", ".join(r.get("translation", [])) or "-"))
    L += ["", "## Scale", "", "```", json.dumps(a["scale"], indent=1, sort_keys=True), "```", ""]
    for title, key in (("Other instances", "instances"), ("Same instance, other times", "same_instance_other_times")):
        L += ["## %s" % title, ""]
        for lab, c in sorted(report[key].items()):
            L.append("- %s: structure equal %s; %d of %d bones differ; largest rotations %s" % (
                lab, c["structure_equal"], c["bones_differing"], c["bones_compared"], c["largest_rotation"][:5]))
        L.append("")
    return "\n".join(L) + "\n"


def write_exclusive(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(data.encode("utf-8"))


def load_observations(folder):
    out = []
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json") and LABEL_RE.match(name[:-5]):
            with open(os.path.join(folder, name), "rb") as f:
                out.append(json.loads(f.read().decode("utf-8")))
    return out


def main(argv):
    if len(argv) not in (3, 4):
        print(__doc__)
        return 2
    observations = load_observations(argv[1])
    if not observations:
        print("REFUSED: no S0-NN.json observations in %s" % argv[1])
        return 2
    report = analyze(observations, argv[3] if len(argv) == 4 else None)
    write_exclusive(os.path.join(argv[2], "S0_REPORT.json"), json.dumps(report, indent=1, sort_keys=True) + "\n")
    write_exclusive(os.path.join(argv[2], "S0_REPORT.md"), markdown(report))
    print(json.dumps({"valid": report["valid"], "readonly": report["readonly"], "primary": report.get("primary"),
                      "bone_classes": (report.get("analysis") or {}).get("bone_classes"),
                      "unaccounted": (report.get("analysis") or {}).get("unaccounted_bones")}, indent=1))
    return 0 if report["valid"] and report["readonly"]["every_observation_unchanged"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
