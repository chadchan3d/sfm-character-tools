# -*- coding: ascii -*-
"""F-01 model compatibility survey observer: STRICTLY READ-ONLY. Run from SFM's Script Editor (Python 2.7):

    MC_DIR = r"E:\\SFM_U0B_Scratch\\f01-model-survey"; MC_REPO = r"E:\\SFM-F01-Pose-Library"
    MC_LABEL = "MC-01"; MC_ANIMSET = "heavy"
    execfile(MC_REPO + r"\\real_sfm_qualification\\f01_model_survey\\observer\\F01_MC_Observe.py")

A model-independent wrapper around the natively proven S0 survey observer (f01_full_body_s0, pinned below and
verified before use, never modified). It runs the S0 observer's own observe() for the named animation set of the
shot at the playhead, and inside the same read-only window (S0's document digest and session state before and after)
adds a few reads S0 did not need for Krystal:
- the animation set's control-group tree (group paths and the controls each group holds);
- the game model's own attributes, and every global flex controller with its attributes;
- the animation set's own attributes (identity);
- for every operator that is not a point, orient or IK constraint, every element it references directly, dumped
  (for example a connection operator's input and output attribute references).

S0 records a structural surprise (no rig registration, a bone without a scene element, several channels clips) as a
problem, because for Krystal it was one. Here those are survey findings: they move to `findings` with the same text.
Read failures, an observer error and any change to the document or session remain `problems`.

It refuses, writing nothing, when the label is not MC-NN, the file exists, the S0 observer is not the pinned one, or
the shot at the playhead has no single animation set named MC_ANIMSET (it lists the names it found). Its only file
write is <MC_DIR>\\observations\\<MC_LABEL>.json (exclusive create).
"""
import hashlib
import json
import os
import re
import sys

FORMAT = "F01-MC-survey-v1"
S0_REL = os.path.join("real_sfm_qualification", "f01_full_body_s0", "observer", "F01_S0_Survey.py")
S0_SHA256 = "4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4"
S0_TAIL = b"\n\nmain()\n"
CONSTRAINT_KINDS = ("DmeRigPointConstraintOperator", "DmeRigOrientConstraintOperator", "DmeRigIKConstraintOperator")
GROUP_FIELDS = ("groupColor", "controlColor", "visible", "selectable", "snappable")
MAX_GROUPS = 5000
MAX_LINKED = 64
FINDING_PATTERNS = (r"^expected one rig registration for the animation set",
                    r"^rig handle .* is duplicated$",
                    r"^bone .* has \d+ scene elements$",
                    r"^bone .* is duplicated$",
                    r"^unrecognised bone transform name",
                    r"^the model is not in the shot's scene$",
                    r"^expected one channels clip holding every control channel")


def mc_exec(code, ns):
    exec(code, ns)


def mc_load_s0(repo):
    path = os.path.join(repo, S0_REL)
    with open(path, "rb") as f:
        raw = f.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != S0_SHA256:
        raise RuntimeError("the S0 observer is not the pinned %s (%s); nothing was written" % (S0_SHA256, digest))
    if not raw.endswith(S0_TAIL):
        raise RuntimeError("the S0 observer does not end with its main() call; nothing was written")
    return path, raw[:-len("main()\n")]


def mc_control_groups(ns, animset):
    opt, seq, ident, text, h, field = ns["opt"], ns["seq"], ns["ident"], ns["text"], ns["h"], ns["field"]
    root = opt(animset, "rootControlGroup")
    if root is None:
        return None
    rows, seen, stack = [], set(), [(root, [])]
    while stack:
        g, path = stack.pop()
        k = h(g)
        if k in seen:
            raise ns["Unreadable"]("control group %d is reached twice" % k)
        seen.add(k)
        if len(rows) >= MAX_GROUPS:
            raise ns["Unreadable"]("control groups exceed their bound")
        p = path + [text(g.GetName())]
        children = [c for c in seq(opt(g, "children") or []) if c is not None]
        rows.append({"path": p, "id": ident(g), "controls": [ident(c) for c in seq(opt(g, "controls") or [])
                                                              if c is not None],
                     "children": [text(c.GetName()) for c in children],
                     "fields": dict((n, field(g, n)) for n in GROUP_FIELDS)})
        for c in reversed(children):
            stack.append((c, p))
    return rows


def mc_linked(ns, op):
    """Every element an operator references directly (one level), dumped; DAGs and transforms are recorded by S0."""
    attr, has, typ, ident, dump, seq = ns["attr"], ns["has"], ns["typ"], ns["ident"], ns["dump"], ns["seq"]
    out = {}
    for name in ns["attribute_names"](op):
        try:
            v = attr(op, name) if has(op, name) else None
        except Exception:
            continue
        items = []
        if v is not None and hasattr(v, "GetHandle") and hasattr(v, "GetTypeString"):
            items = seq(v) if typ(v).endswith("_array") else [v]
        rows = []
        for e in items[:MAX_LINKED]:
            if e is None or not hasattr(e, "GetHandle"):
                continue
            kind = typ(e)
            if kind in ("DmeDag", "DmeTransform", "DmeRigHandle", "DmeGameModel"):
                rows.append({"id": ident(e)})
            else:
                rows.append({"id": ident(e), "attributes": dump(e)})
        if rows:
            out[name] = rows
    return out


def mc_extend(ns, out, animset):
    opt, seq, ident, dump, typ, h = ns["opt"], ns["seq"], ns["ident"], ns["dump"], ns["typ"], ns["h"]
    ext = {}
    try:
        ext["control_groups"] = mc_control_groups(ns, animset)
    except Exception as exc:
        out["problems"].append("control groups unreadable: %r" % (exc,))
    ext["animation_set_attributes"] = dump(animset, skip=("controls", "operators", "rootControlGroup",
                                                           "presetGroups"))
    gm = ns["attr"](animset, "gameModel")
    ext["game_model_attributes"] = dump(gm, skip=("bones", "children", "globalFlexControllers"))
    ext["flex_controllers"] = []
    try:
        for f in seq(opt(gm, "globalFlexControllers") or []):
            if f is not None:
                ext["flex_controllers"].append({"id": ident(f), "attributes": dump(f)})
    except Exception as exc:
        out["problems"].append("flex controllers unreadable: %r" % (exc,))
    ext["operator_links"] = {}
    shot = ns["sfmApp"].GetShotAtCurrentTime()
    for holder in (animset, shot):
        for op in seq(opt(holder, "operators") or []):
            if op is None or typ(op) in CONSTRAINT_KINDS or str(h(op)) in ext["operator_links"]:
                continue
            try:
                ext["operator_links"][str(h(op))] = {"id": ident(op), "linked": mc_linked(ns, op)}
            except Exception as exc:
                out["problems"].append("operator %s links unreadable: %r" % (ns["text"](op.GetName()), exc))
    out["mc"] = ext


def mc_reclassify(out):
    keep, findings = [], []
    for p in out["problems"]:
        if any(re.match(r, p) for r in FINDING_PATTERNS):
            findings.append(p)
        else:
            keep.append(p)
    out["problems"], out["findings"] = keep, findings


def mc_observe(repo, label, animset_name):
    path, source = mc_load_s0(repo)
    ns = {"__name__": "__f01_mc_s0__", "S0_ANIMSET": animset_name}
    mc_exec(compile(source, path, "exec"), ns)
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
        mc_extend(ns, out, sets[0])

    ns["survey"] = survey
    data = ns["observe"](label)
    data["format"], data["s0_format"], data["s0_observer_sha256"] = FORMAT, ns["FORMAT"], S0_SHA256
    data["animation_sets_in_shot"] = names
    mc_reclassify(data)
    return data


def mc_main():
    g = globals()
    root, repo, label, name = g.get("MC_DIR"), g.get("MC_REPO"), g.get("MC_LABEL"), g.get("MC_ANIMSET")
    if not root or not repo or not name or not label or not re.match(r"^MC-\d\d$", label):
        raise RuntimeError("Set MC_DIR, MC_REPO, MC_LABEL (MC-NN) and MC_ANIMSET first; see the docstring.")
    path = os.path.join(root, "observations", "%s.json" % label)
    if os.path.exists(path):
        raise RuntimeError("%s exists; it is never replaced. Use the next label." % path)
    data = mc_observe(repo, label, name)
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    s = data.get("session_after") or {}
    summary = ("MC %s: %s  set=%s model=%s rigs=%s bones=%d handles=%d controls=%d channels=%d operators=%d "
               "flex=%d groups=%s shot=%s mode=%s readonly=%s problems=%d findings=%d%s" % (
                   label, "OK" if not data["problems"] and data["readonly"]["unchanged"] else "PROBLEM", name,
                   ((data.get("model") or {}).get("modelName") or {}).get("value"),
                   [r["rig"]["name"] for r in (data.get("rig") or {}).get("registrations") or []],
                   len(data.get("bones") or {}), len((data.get("rig") or {}).get("handles") or {}),
                   len(data.get("controls") or []), len(data.get("channels") or []), len(data.get("operators") or []),
                   len((data.get("mc") or {}).get("flex_controllers") or []),
                   len((data.get("mc") or {}).get("control_groups") or []), s.get("current_shot"),
                   (s.get("timeline_mode") or {}).get("name"), data["readonly"]["unchanged"],
                   len(data["problems"]), len(data["findings"]),
                   (" first problem: %s" % data["problems"][0]) if data["problems"] else ""))
    print(summary.encode("ascii", "replace") if sys.version_info[0] == 2 else summary)


mc_main()
