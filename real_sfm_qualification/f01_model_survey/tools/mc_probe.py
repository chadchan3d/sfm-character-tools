# -*- coding: utf-8 -*-
"""F-01 model compatibility survey: the offline refusal-map probe (Python 3, read-only; run with -I).

usage: python -I mc_probe.py OBSERVATIONS_DIR OUT_DIR

For every observation (MC-NN.json from F01_MC_Observe.py, or an S0-NN.json from the Krystal S0 survey):
1. derives the stage E discovery form with the existing fixture derivation (cpm/convergence/tests/f01_body_fixture.py;
   a model without a rig registration gets an empty rig, recorded as such);
2. drafts a profile from structure alone (see draft_profile: no names are used to decide a role);
3. runs CPM's own stage E classifier (prod_body_classify, loaded from the candidate source exactly as the body tests
   load it) against the draft, and against the registry profile when the model has one; and once more against a
   hypothetical form in which every operator the engine does not understand is dropped, to show the next refusal
   behind the first (labelled hypothetical: nothing in CPM does this);
4. writes a census that does not stop at the first refusal: operator types, every channel's destination and source
   class, every bone's writers, connection-operator outputs, control-group membership of written bones, flex
   controls, scale and placement references.

Writes OUT_DIR/MC_PROBE.json and OUT_DIR/MC_PROBE.md (exclusive create). Nothing in CPM is changed.
"""
import collections
import copy
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TESTS = os.path.join(REPO, "cpm", "convergence", "tests")
sys.path.insert(0, TESTS)

CONSTRAINTS = ("DmeRigPointConstraintOperator", "DmeRigOrientConstraintOperator", "DmeRigIKConstraintOperator")
FACE_WORDS = ("face", "head", "eye", "mouth", "jaw", "tongue", "lip", "brow", "lid", "facial", "teeth")
LABEL_RE = re.compile(r"^(MC|S0)-\d\d[a-z]?$")


def value(f):
    return f.get("value") if isinstance(f, dict) and f.get("status") == "READ" else None


# --- the CPM namespace (as the body tests build it) ------------------------------------------------------------

def cpm_namespace():
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        import test_cpm_app_canonical_route as route
        import test_cpm_app_f01_body as body
        ns = body.build_namespace(route.AppSource(route.APP_PATH))
        arm, reg = body.registries(ns)
    finally:
        sys.stdout = saved
    with io.open(route.APP_PATH, "rb") as f:
        cpm_sha = hashlib.sha256(f.read()).hexdigest()
    return ns, arm, cpm_sha


# --- derivation ------------------------------------------------------------------------------------------------

def derive_any(obs, sha):
    import f01_body_fixture as FX
    regs = obs["rig"]["registrations"]
    if regs:
        D = FX.derive(obs, sha)
    else:
        o = copy.deepcopy(obs)
        o["rig"]["registrations"] = [{"rig": {"name": None, "handle": None}, "registration": {"handle": None},
                                      "elements": []}]
        D = FX.derive(o, sha)
        D["rig"].update({"names": [], "registrations": 0, "rig_handle": None, "registration": None, "elements": []})
    return D


def labels(D):
    label = {D["model"]["handle"]: "model"}
    for n, b in D["bones"].items():
        label[b["handle"]] = "bone:" + n
    for n, h in D["rig"]["handles"].items():
        label[h["handle"]] = "handle:" + n
    return label


def draft_profile(D):
    """A profile from structure alone: parents from the scene, constraints from the operators, helpers = handles a
    constraint slaves, placement = the one unconstrained handle parented to the rig, handle channels from the
    handles' own control channels (orientation preserved on a handle used only as a pole, and on the placement
    handle), passive bones = bones whose channels have no source. Facial preservation is left empty: there is no
    structural evidence for it (it is reported in the census instead)."""
    label, handles = labels(D), D["rig"]["handles"]
    notes = []
    parents = {}
    for n, h in handles.items():
        p = h["parent"]
        if p is None or h["parent_count"] != 1:
            parents[n] = None
            notes.append("handle %s has %d parents" % (n, h["parent_count"]))
        elif p["type"] == "DmeRig":
            parents[n] = "@rig"
        else:
            parents[n] = next((m for m, x in handles.items() if x["handle"] == p["handle"]), None)
            if parents[n] is None:
                notes.append("handle %s is parented to %s %s, not a rig handle" % (n, p["type"], p["name"]))
    constraints, slaved, poles, targets = [], set(), set(), set()
    for op in D["operators"]:
        if op["type"] not in CONSTRAINTS:
            continue
        slaves = {}
        for slot, s in op["slaves"].items():
            if s is None or s.get("target") is None:
                continue
            slaves[slot] = label.get(s["target"], "unknown:%s" % s["target"])
            slaved.add(slaves[slot])
        ts = [label.get(t["target"], "unknown:%s" % t["target"]) for t in op["targets"]]
        pole = label.get(op["pole"], "unknown:%s" % op["pole"]) if op["pole"] is not None else None
        targets.update(ts)
        if pole:
            poles.add(pole)
        constraints.append({"type": op["type"], "slaves": slaves, "targets": ts, "pole": pole})
    helpers = sorted(n for n in handles if "handle:" + n in slaved)
    roots = [n for n in handles if parents.get(n) == "@rig" and n not in helpers]
    placement = roots[0] if len(roots) == 1 else None
    if placement is None:
        notes.append("no single unconstrained handle under the rig (%s)" % sorted(roots))
    by_dest = collections.defaultdict(list)
    for cname, ch in D["channels"].items():
        if ch["to"] is not None:
            by_dest[ch["to"]["handle"]].append(cname)
    written, preserved = {}, {}
    for n, h in handles.items():
        if n in helpers:
            continue
        for cname in by_dest.get(h["transform"], []):
            attr = D["channels"][cname]["to_attribute"]
            if attr not in ("position", "orientation"):
                continue
            pole_only = ("handle:" + n) in poles and ("handle:" + n) not in targets
            keep = n == placement or (pole_only and attr == "orientation")
            (preserved if keep else written)[cname] = [n, attr]
    passive = []
    for n, b in D["bones"].items():
        chs = [D["channels"][c] for c in by_dest.get(b["transform"], [])
               if D["channels"][c]["to_attribute"] in ("position", "orientation")]
        if len(chs) == 2 and all(c["from"] is None for c in chs):
            passive.append(n)
    return {"region": "full_body", "rig_name": D["rig"]["names"][0] if D["rig"]["names"] else None,
            "handles": parents, "constraints": constraints, "helper_handles": helpers, "placement_handle": placement,
            "written_handle_channels": written, "preserved_handle_channels": preserved,
            "passive_channel_bones": sorted(passive), "preserved_fk_bones": [], "_id": "draft", "_notes": notes}


def classify(ns, D, profile):
    unparented = sorted(n for n, v in profile["handles"].items() if v is None)
    if unparented:
        return {"result": "NOT-EXPRESSIBLE", "code": None,
                "detail": "a profile cannot name the parent of rig handles %s (not the rig, not a rig handle)"
                          % unparented[:8]}
    del ns["LOG"][:]
    try:
        C = ns["prod_body_classify"](D, profile)
    except ns["ProdPoseError"] as exc:
        return {"result": "REFUSED", "code": exc.code, "detail": ns["LOG"][-1] if ns["LOG"] else str(exc)}
    except Exception as exc:
        return {"result": "CLASSIFIER-ERROR", "code": None, "detail": "%s: %s" % (type(exc).__name__, exc)}
    counts = collections.Counter(C["channels"].values())
    return {"result": "CLASSIFIED", "roles": dict(counts), "bones": dict(collections.Counter(C["bones"].values())),
            "written": len(C["written"])}


def relaxed(D):
    """Hypothetical: every operator CPM does not understand dropped, as if it were rig-internal and preserved."""
    D2 = copy.deepcopy(D)
    D2["operators"] = [op for op in D2["operators"] if op["type"] in CONSTRAINTS + ("DmeExpressionOperator",)]
    D2["unknown_operator_types"] = []
    return D2


# --- census ----------------------------------------------------------------------------------------------------

def census(obs, D):
    label = labels(D)
    transform_owner = {D["model"]["transform"]: "model"}
    for n, b in D["bones"].items():
        transform_owner[b["transform"]] = "bone:" + n
    for n, h in D["rig"]["handles"].items():
        transform_owner[h["transform"]] = "handle:" + n
    slave_of, weight_of, slaved_by = {}, {}, collections.defaultdict(list)
    for op in obs["operators"]:
        for slot, s in (op.get("slaves") or {}).items():
            if s and s.get("slave"):
                slave_of[s["slave"]["handle"]] = op["id"]["type"]
                if s.get("target"):
                    slaved_by[label.get(s["target"]["handle"], s["target"]["name"])].append(
                        "%s.%s" % (op["id"]["type"], slot))
        for t in op.get("targets") or []:
            weight_of[t["id"]["handle"]] = op["id"]["type"]
    control_type = dict((c["handle"], c["type"]) for c in D["controls"].values())
    dest = collections.Counter()
    bone_writers = collections.defaultdict(list)
    other = collections.Counter()
    shape = collections.Counter()
    for cname, ch in D["channels"].items():
        to, attr = ch["to"], ch["to_attribute"]
        src = ch["from"]
        source = ("none" if src is None else
                  "control:" + control_type.get(src["handle"], src["type"]) if src["handle"] in control_type else
                  "element:" + src["type"])
        shape["mode=%s layers=%d" % (ch["mode"], len(ch["layers"]))] += 1
        if to is None:
            kind = "no destination"
        elif to["handle"] in transform_owner:
            owner = transform_owner[to["handle"]]
            kind = owner.split(":")[0] + "." + attr
            if owner.startswith("bone:"):
                bone_writers[owner[5:]].append({"channel": cname, "attr": attr, "source": source,
                                                "writers": D["writers"].get("%d:%s" % (to["handle"], attr))})
        elif to["handle"] in slave_of:
            kind = "constraint slave (%s).%s" % (slave_of[to["handle"]], attr)
        elif to["handle"] in weight_of:
            kind = "constraint target weight"
        else:
            kind = "%s.%s" % (to["type"], attr)
            other["%s.%s <- %s" % (to["type"], attr, source)] += 1
        dest["%s <- %s" % (kind, source)] += 1
    bones = {}
    classes = collections.Counter()
    for n, b in D["bones"].items():
        scale_ws = [w for w in bone_writers.get(n, []) if w["attr"] == "scale"]
        ws = [w for w in bone_writers.get(n, []) if w["attr"] != "scale"]
        by = slaved_by.get("bone:" + n, [])
        attrs = sorted(w["attr"] for w in ws)
        srcs = sorted(set(w["source"] for w in ws))
        shared = any((w["writers"] or 0) > 1 for w in ws)
        if any(t.split(".")[0] not in CONSTRAINTS for t in by):
            cls = "slaved by an unsupported operator"
        elif by:
            cls = "constrained"
        elif not ws:
            cls = "no writer (procedural or unanimated)"
        elif shared:
            cls = "several writers"
        elif srcs == ["control:DmeTransformControl"] and attrs == ["orientation", "position"]:
            cls = "fk (one control channel each)"
        elif srcs == ["none"]:
            cls = "source-less channels (passive)"
        else:
            cls = "other writers (%s; %s)" % (",".join(attrs), ",".join(srcs))
        classes[cls] += 1
        bones[n] = {"class": cls, "parent": b["parent"], "writers": ws, "scale_writers": scale_ws, "slaved_by": by,
                    "scale": b["scale"]}
    # control groups: where each control sits (the animation-group taxonomy SFM shows the artist)
    groups = (obs.get("mc") or {}).get("control_groups")
    member = collections.defaultdict(list)
    for g in groups or []:
        for c in g["controls"]:
            member[c["name"]].append(" > ".join(g["path"]))
    fk = sorted(n for n, b in bones.items() if b["class"].startswith("fk"))
    fk_groups = dict((n, member.get(n, [])) for n in fk)
    face_by_group = sorted(n for n, ps in fk_groups.items() if any(any(w in p.lower() for w in FACE_WORDS)
                                                                    for p in ps))
    face_by_name = sorted(n for n in fk if any(w in n.lower() for w in FACE_WORDS))
    top_groups = collections.Counter()
    for g in groups or []:
        if len(g["path"]) == 2:
            top_groups[g["path"][1]] = len(g["controls"])
    # connection and other non-constraint operators: what they write
    links = []
    for k, op in ((obs.get("mc") or {}).get("operator_links") or {}).items():
        refs = []
        for slot, rows in op["linked"].items():
            for r in rows:
                a = r.get("attributes") or {}
                el, at = value(a.get("element")), value(a.get("attribute"))
                if el is not None or at is not None:
                    refs.append({"slot": slot, "element": el and "%s:%s" % (el["type"], label.get(el["handle"],
                                                                                                   el["name"])),
                                 "attribute": at})
        links.append({"operator": op["id"]["name"], "type": op["id"]["type"], "references": refs})
    op_types = collections.Counter(op["id"]["type"] for op in obs["operators"])
    controls = collections.Counter(c["type"] for c in D["controls"].values())
    model_channels = [c for c, ch in D["channels"].items() if ch["to"] and ch["to"]["handle"] == D["model"]["transform"]]
    roots = sorted(n for n, b in D["bones"].items() if b["parent"] is None)
    return {"operator_types": dict(op_types), "document_unknown_operator_types": D["unknown_operator_types"],
            "control_types": dict(controls), "channel_destinations": dict(dest), "channel_shapes": dict(shape),
            "other_destinations": dict(other), "bone_classes": dict(classes), "bones": bones,
            "fk_bones": fk, "fk_bone_groups": fk_groups, "face_risk_by_group": face_by_group,
            "face_risk_by_name_only": face_by_name, "top_level_groups": dict(top_groups),
            "control_groups_recorded": groups is not None, "flex_controllers": len((obs.get("mc") or {}).get(
                "flex_controllers") or []), "operator_links": links, "model_transform_channels": model_channels,
            "root_bones": roots, "model_scale": D["model"]["scale"],
            "scaled_bones": sorted(n for n, b in D["bones"].items() if value(b["scale"]) not in (None, 1.0,
                                                                                                  [1.0, 1.0, 1.0]))}


# --- report ----------------------------------------------------------------------------------------------------

def probe_one(ns, arm, raw, obs):
    sha = hashlib.sha256(raw).hexdigest()
    D = derive_any(obs, sha)
    draft = draft_profile(D)
    out = {"label": obs["label"], "sha256": sha, "format": obs.get("format"),
           "animation_set": obs.get("animation_set_name"), "model": D["model"]["model_ref"],
           "rigs": D["rig"]["names"], "problems": obs.get("problems"), "findings": obs.get("findings", []),
           "readonly_unchanged": obs["readonly"]["unchanged"],
           "counts": {"bones": len(D["bones"]), "handles": len(D["rig"]["handles"]), "controls": len(D["controls"]),
                      "channels": len(D["channels"]), "operators": len(D["operators"])},
           "draft_profile": dict((k, v) for k, v in draft.items() if k != "_id"),
           "classify_draft": classify(ns, D, draft), "classify_relaxed_hypothetical": classify(ns, relaxed(D), draft),
           "census": census(obs, D)}
    registry = None
    for cls, row in (arm.get("_body") or {}).get("rig_classes", {}).items():
        if any(m["model_ref"] == D["model"]["model_ref"] for m in row["models"]):
            registry = ns["prod_body_profile"](arm, cls)
    if registry is not None:
        out["classify_registry_profile"] = dict(classify(ns, D, registry), profile=registry["_id"])
        def norm(v):
            if isinstance(v, list):
                return sorted(json.dumps(x, sort_keys=True) for x in v)
            return json.dumps(v, sort_keys=True)
        out["draft_vs_registry"] = dict(
            (k, {"draft": draft[k], "registry": registry[k]}) for k in draft
            if not k.startswith("_") and k in registry and norm(draft[k]) != norm(registry[k]))
    return out


def markdown(report):
    lines = ["# F-01 model compatibility probe", "",
             "CPM candidate `%s`. Generated by `mc_probe.py`; read-only." % report["cpm_sha256"], ""]
    for r in report["observations"]:
        c = r["census"]
        lines += ["## %s: %s (`%s`)" % (r["label"], r["animation_set"], r["model"]), "",
                  "- Rig: %s. Counts: %s." % (r["rigs"] or "none", r["counts"]),
                  "- Observation: readonly unchanged %s; problems %d; findings %s." % (
                      r["readonly_unchanged"], len(r["problems"] or []), r["findings"] or "none"),
                  "- Classifier, drafted profile: **%s** %s" % (r["classify_draft"]["result"],
                                                                 r["classify_draft"].get("code") or ""),
                  "  - %s" % (r["classify_draft"].get("detail") or r["classify_draft"]),
                  "- Classifier, unsupported operators dropped (hypothetical): **%s** %s" % (
                      r["classify_relaxed_hypothetical"]["result"], r["classify_relaxed_hypothetical"].get("code") or ""),
                  "  - %s" % (r["classify_relaxed_hypothetical"].get("detail") or r["classify_relaxed_hypothetical"])]
        if "classify_registry_profile" in r:
            lines.append("- Classifier, registry profile `%s`: **%s**" % (r["classify_registry_profile"]["profile"],
                                                                         r["classify_registry_profile"]["result"]))
            lines.append("- Draft differs from the registry profile in: %s" % (sorted(r["draft_vs_registry"]) or
                                                                               "nothing"))
        lines += ["- Draft notes: %s" % (r["draft_profile"]["_notes"] or "none"),
                  "- Operator types: %s" % c["operator_types"],
                  "- Unknown operator types in the document: %s" % c["document_unknown_operator_types"],
                  "- Bone classes: %s" % c["bone_classes"],
                  "- FK bones at facial risk by control group: %s" % (c["face_risk_by_group"] or "none"),
                  "- FK bones at facial risk by name only: %s" % (c["face_risk_by_name_only"] or "none"),
                  "- Top-level control groups: %s" % c["top_level_groups"],
                  "- Flex controllers: %d. Root bones: %s. Model transform channels: %s." % (
                      c["flex_controllers"], c["root_bones"], c["model_transform_channels"]),
                  "- Channel destinations:"]
        lines += ["  - %s: %d" % (k, v) for k, v in sorted(c["channel_destinations"].items())]
        if c["operator_links"]:
            lines.append("- Non-constraint operator references:")
            lines += ["  - %s (%s): %s" % (l["operator"], l["type"], l["references"]) for l in c["operator_links"][:40]]
        lines.append("")
    return "\n".join(lines) + "\n"


def write_exclusive(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(data)


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    ns, arm, cpm_sha = cpm_namespace()
    rows = []
    for name in sorted(os.listdir(argv[1])):
        if not name.endswith(".json") or not LABEL_RE.match(name[:-5]):
            continue
        with io.open(os.path.join(argv[1], name), "rb") as f:
            raw = f.read()
        rows.append(probe_one(ns, arm, raw, json.loads(raw.decode("utf-8"))))
    report = {"format": "F01-MC-probe-v1", "cpm_sha256": cpm_sha, "observations": rows}
    write_exclusive(os.path.join(argv[2], "MC_PROBE.json"),
                    json.dumps(report, indent=1, sort_keys=True).encode("utf-8"))
    write_exclusive(os.path.join(argv[2], "MC_PROBE.md"), markdown(report).encode("utf-8"))
    for r in rows:
        print(r["label"], r["animation_set"], r["rigs"], "draft:", r["classify_draft"]["result"],
              r["classify_draft"].get("code"), "| relaxed:", r["classify_relaxed_hypothetical"]["result"],
              r["classify_relaxed_hypothetical"].get("code"),
              "| registry:", (r.get("classify_registry_profile") or {}).get("result"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
