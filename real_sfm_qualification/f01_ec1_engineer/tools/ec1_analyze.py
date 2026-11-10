# -*- coding: utf-8 -*-
"""F-01 EC-1: offline analysis of the Engineer control-coverage observation (Python 3, run with -I). Read-only: it
reads the EC1-NN observations and the pinned expected header, and writes EC1_ANALYSIS.json and EC1_ANALYSIS.md
(exclusive create). Nothing in CPM or the run folder is changed.

Two independent routes, which must agree:
1. Census (this file, no CPM code): from the observed bindings alone, every bone's position and orientation writers,
   their sources, modes, layers, log types, endpoint indices and document-wide writer counts; every control's
   destinations; operators, rig registrations and non-bone destinations.
2. CPM's own version 3 engine (the repository's CPM source, as the offline scoped suite runs it): the observation is
   converted exactly as the scoped fixtures are (cpm/convergence/tests/f01_scoped_fixture.py), the observed channel
   endpoint indices are placed on the fake channels (the fake defaults them to 0), and prod_scope_inventory,
   the full-body compile, Save New and an Apply to a changed copy run in qualification mode against the fake scene.
   This is an offline replay of the observed structure, not evidence of native behaviour.

Verdict per observation:
  CANDIDATE      every criterion below passes: the model may enter a version 3 Full body Save/Apply native
                 qualification. It is not qualified by this analysis.
  NOT-CANDIDATE  a criterion fails on readable evidence (each failure is named)
  NO-CONCLUSION  the observation is not clean, or evidence a criterion needs is unreadable

usage: python -I ec1_analyze.py OBSERVATIONS_DIR EVIDENCE_DIR EXPECTED_HEADER.json
"""
from __future__ import print_function

import collections
import contextlib
import copy
import hashlib
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TESTS = os.path.join(REPO, "cpm", "convergence", "tests")

FORMAT = "F01-EC1-observation-v1"
OBSERVERS = {"s0": "4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4",
             "mc": "f8d52035048a2e48d41d511968ce7f40caab09235d4a541970b6703bf389b5cd",
             "nq": "1ac46682e0095ee716dfccbea978b33cec5ef4a0a7386b50f9d94cce2bb893ff"}
LABEL_RE = re.compile(r"^EC1-\d\d$")
NO_RIG_FINDING = re.compile(r"^expected one rig registration for the animation set, found 0$")
HEADER_FIELDS = ("parent", "flags", "proctype", "procindex", "physicsbone")
FLAG_NAMES = ("BONE_PHYSICALLY_SIMULATED", "BONE_PHYSICS_PROCEDURAL", "BONE_ALWAYS_PROCEDURAL",
              "BONE_SCREEN_ALIGN_SPHERE", "BONE_SCREEN_ALIGN_CYLINDER")
CONSTRAINTS = ("DmeRigIKConstraintOperator", "DmeRigOrientConstraintOperator", "DmeRigPointConstraintOperator")
VALUE_OPERATORS = ("DmeExpressionOperator", "DmePackColorOperator")
TRANSFORM = {"position": ("valuePosition", "positionChannel", "DmeVector3Log", "DmeVector3LogLayer"),
             "orientation": ("valueOrientation", "orientationChannel", "DmeQuaternionLog", "DmeQuaternionLogLayer")}


def value(f):
    return f.get("value") if isinstance(f, dict) and f.get("status") == "READ" else None


def readable(f):
    return isinstance(f, dict) and f.get("status") == "READ"


def criterion(rows, key, ok, detail, unreadable=False):
    rows.append({"criterion": key, "result": "UNREADABLE" if unreadable else ("PASS" if ok else "FAIL"),
                 "detail": detail})


# --- 1. the observation itself and the pinned identity ------------------------------------------------------------

def check_observation(obs, rows, require_kit=True):
    if require_kit:
        criterion(rows, "observation.format", obs.get("format") == FORMAT, obs.get("format"))
        criterion(rows, "observation.observers_pinned", obs.get("observers") == OBSERVERS, obs.get("observers"))
    criterion(rows, "observation.read_only_window_unchanged", (obs.get("readonly") or {}).get("unchanged") is True,
              (obs.get("readonly") or {}).get("unchanged"))
    criterion(rows, "observation.no_problems", not obs.get("problems"), (obs.get("problems") or [])[:5])
    other = [f for f in obs.get("findings") or [] if not NO_RIG_FINDING.match(f)]
    criterion(rows, "observation.only_the_no_rig_finding", not other, other[:5])
    criterion(rows, "observation.single_animation_set_in_shot", len(obs.get("animation_sets_in_shot") or []) == 1,
              obs.get("animation_sets_in_shot"))


def check_identity(obs, expected, rows):
    ref = value((obs.get("model") or {}).get("modelName"))
    criterion(rows, "identity.model_ref", ref is not None and ref.replace("\\", "/").lower() == expected["model_ref"],
              ref, unreadable=ref is None)
    st = (obs.get("nq") or {}).get("studio") or {}
    header = st.get("header") or {}
    checksum, count = value(header.get("checksum")), value(header.get("numbones"))
    criterion(rows, "identity.header_checksum", checksum == expected["header"]["checksum"],
              [checksum, expected["header"]["checksum"]], unreadable=checksum is None)
    criterion(rows, "identity.header_bone_count", count == expected["header"]["numbones"],
              [count, expected["header"]["numbones"]], unreadable=count is None)
    got = st.get("bones") or []
    diffs, unread = [], []
    for want in expected["bones"]:
        i = want["index"]
        b = got[i] if i < len(got) else None
        if b is None or "unreadable" in b or value(b.get("name")) is None or \
                any(not readable(b.get(f)) for f in HEADER_FIELDS):
            unread.append(i)
            continue
        for f in ("name",) + HEADER_FIELDS:
            if value(b.get(f)) != want[f]:
                diffs.append({"index": i, "field": f, "observed": value(b.get(f)), "pinned": want[f]})
    criterion(rows, "identity.header_rows_equal_the_nq03_pin", not diffs and len(got) == len(expected["bones"]),
              diffs[:10] or len(got), unreadable=bool(unread))
    consts = dict((k, value(v)) for k, v in (st.get("constants") or {}).items())
    mask_ok = all(consts.get(n) is not None for n in FLAG_NAMES)
    mask = 0
    for n in FLAG_NAMES:
        mask |= consts.get(n) or 0
    declared = [value(b.get("name")) for b in got if value(b.get("proctype")) not in (None, 0) or
                (value(b.get("flags")) is not None and value(b.get("flags")) & mask)]
    criterion(rows, "identity.no_declared_procedural_bone", mask_ok and not declared, declared[:10],
              unreadable=not mask_ok or bool(unread))
    return {"model_ref": ref, "checksum": checksum, "numbones": count, "declared_procedural": declared,
            "should_evaluate_procedural_bones": value((obs.get("nq") or {}).get("should_evaluate_procedural_bones")),
            "source_less_channels": [r.get("channel") for r in (obs.get("nq") or {}).get("source_less_channels") or []]}


def check_join(obs, rows):
    """The engine header (index -> name, parent index) joins the scene's bones (index, name, parent bone)."""
    hdr = ((obs.get("nq") or {}).get("studio") or {}).get("bones") or []
    by_index = dict((b.get("index"), n) for n, b in (obs.get("bones") or {}).items())
    problems = []
    for b in hdr:
        i, name, parent = b.get("index"), value(b.get("name")), value(b.get("parent"))
        scene = by_index.get(i)
        if scene != name:
            problems.append("header bone %s %r is scene bone %r" % (i, name, scene))
            continue
        want = None if parent in (None, -1) else value(hdr[parent].get("name")) if 0 <= parent < len(hdr) else "?"
        got = (obs["bones"][scene] or {}).get("parent_bone")
        if want != got:
            problems.append("bone %s: header parent %r, scene parent %r" % (name, want, got))
    if len(hdr) != len(by_index):
        problems.append("header has %d bones, scene %d" % (len(hdr), len(by_index)))
    criterion(rows, "structure.header_joins_scene_bones", not problems, problems[:10])
    return problems


# --- 2. the census (no CPM code) -----------------------------------------------------------------------------------

def observed_indices(obs):
    """{channel name: [fromIndex field, toIndex field]} as observed (a field is None when it was not recorded)."""
    return dict((c["id"]["name"], [(c.get("binding") or {}).get("fromIndex"), (c.get("binding") or {}).get(
        "toIndex")]) for c in obs.get("channels") or [] if "id" in c)


def census(D, indices, operator_types, document_operator_types, rig_registrations):
    owner = {D["model"]["transform"]: ("model", None)}
    for n, b in D["bones"].items():
        owner[b["transform"]] = ("bone", n)
    for n, h in D["rig"]["handles"].items():
        owner[h["transform"]] = ("handle", n)
    control_by_channel, control_types = {}, collections.Counter()
    for cname, c in D["controls"].items():
        control_types[c["type"]] += 1
        for slot, ch in c["channels"].items():
            if ch is not None:
                control_by_channel.setdefault(ch, []).append((cname, c["type"], slot, c["handle"]))
    writers = collections.defaultdict(lambda: collections.defaultdict(list))
    other_dest = collections.Counter()
    for name, ch in D["channels"].items():
        to = ch["to"]
        if to is None:
            other_dest["no destination"] += 1
            continue
        kind, who = owner.get(to["handle"], ("element", to["type"]))
        if kind == "bone":
            writers[who][ch["to_attribute"]].append(name)
        else:
            other_dest["%s.%s" % (kind if kind != "element" else who, ch["to_attribute"])] += 1
    bones, classes, control_bones = {}, collections.Counter(), collections.defaultdict(set)
    for n in sorted(D["bones"]):
        ws = writers.get(n, {})
        reasons, controls = [], set()
        for attr in sorted(ws):
            if attr not in TRANSFORM:
                reasons.append("writes %s (%s)" % (attr, ws[attr]))
        for attr, (src_attr, slot, log_type, layer_type) in sorted(TRANSFORM.items()):
            names = ws.get(attr, [])
            if len(names) != 1:
                reasons.append("%d %s channels" % (len(names), attr))
                continue
            ch = D["channels"][names[0]]
            ctl = control_by_channel.get(ch["handle"], [])
            idx = indices.get(names[0]) or [None, None]
            count = D["writers"].get("%d:%s" % (ch["to"]["handle"], attr))
            if len(ctl) != 1:
                reasons.append("%s channel %s is referenced by %d controls" % (attr, names[0], len(ctl)))
                continue
            cname, ctype, cslot, chandle = ctl[0]
            controls.add(cname)
            control_bones[cname].add(n)
            if ctype != "DmeTransformControl" or cslot != slot:
                reasons.append("%s from %s.%s" % (attr, ctype, cslot))
            if ch["from"] is None or ch["from"]["handle"] != chandle or ch["from_attribute"] != src_attr:
                reasons.append("%s channel source is not its control's %s" % (attr, src_attr))
            if ch["mode"] != 3 or ch["log_type"] != log_type or ch["layers"] != [layer_type]:
                reasons.append("%s channel mode/log/layers %s/%s/%s" % (attr, ch["mode"], ch["log_type"], ch["layers"]))
            if not all(readable(f) for f in idx):
                reasons.append("unreadable: %s channel endpoint indices %s" % (attr, idx))
            elif not all(type(value(f)) is int and value(f) == 0 for f in idx):
                reasons.append("%s channel endpoint indices %s" % (attr, [value(f) for f in idx]))
            if count != 1:
                reasons.append("%s has %s writers document-wide" % (attr, count))
        if len(controls) > 1:
            reasons.append("driven by %d controls %s" % (len(controls), sorted(controls)))
        cls = "direct-fk" if not reasons else "not-direct"
        classes[cls] += 1
        bones[n] = {"class": cls, "controls": sorted(controls), "reasons": reasons}
    shared = dict((c, sorted(b)) for c, b in control_bones.items() if len(b) > 1)
    op_types = collections.Counter(operator_types)
    doc_types = document_operator_types
    unsupported_ops = sorted(t for t in list(op_types) + list(doc_types)
                             if t not in CONSTRAINTS + VALUE_OPERATORS)
    return {"bones": bones, "classes": dict(classes), "controls_driving_several_bones": shared,
            "control_types": dict(control_types), "non_bone_destinations": dict(other_dest),
            "rig_registrations": rig_registrations,
            "operator_types": dict(op_types), "document_operator_types": doc_types,
            "constraints": sorted(t for t in op_types if t in CONSTRAINTS),
            "unsupported_operator_types": sorted(set(unsupported_ops)),
            "control_less_bones": sorted(n for n in D["bones"] if not bones[n]["controls"])}


# --- 3. CPM's own version 3 engine on an offline replay --------------------------------------------------------------

@contextlib.contextmanager
def quiet():
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = saved


def cpm_tools():
    if TESTS not in sys.path:
        sys.path.insert(0, TESTS)
    with quiet():
        import test_cpm_app_canonical_route as route
        import test_cpm_app_f01_scoped as T
        import fake_sfm_scoped as FS
        import f01_scoped_fixture as SF
        ns = T.namespace(route.AppSource(route.APP_PATH))
    with io.open(route.APP_PATH, "rb") as f:
        cpm_sha = hashlib.sha256(f.read()).hexdigest()
    return {"T": T, "FS": FS, "SF": SF, "ns": ns, "cpm_sha256": cpm_sha}


def world(K, fx, indices):
    """The fake scene of the fixture with the OBSERVED endpoint indices on every channel (absent, unreadable and
    non-integer values are carried, never replaced by 0)."""
    T, FS = K["T"], K["FS"]
    w = FS.World(fx)
    seen = {}
    for name, fields in sorted(indices.items()):
        if name not in w.channels:
            continue
        for field, f in zip(("fromIndex", "toIndex"), fields):
            v = T.MISSING if f is None else (value(f) if readable(f) else T.UNREADABLE)
            T.set_index(w, name, field, v)
            seen[(name, field)] = True
    return w, len(seen)


def run_cpm(K, D, indices, census_rows):
    T, ns = K["T"], K["ns"]
    out = {"cpm_sha256": K["cpm_sha256"], "mode": "qualification"}
    fx = copy.deepcopy(D)
    w, placed = world(K, fx, indices)
    out["indices_placed"] = placed
    T.use(ns, w, fx)
    try:
        inv = T.inventory(ns)
    except Exception as exc:
        out["inventory"] = {"error": "%s: %s" % (type(exc).__name__, exc), "code": getattr(exc, "code", None)}
        return out
    classes = collections.Counter(inv["classes"].values())
    out["inventory"] = {"classes": dict(classes), "root": inv["root"], "full_body": inv["full_body"],
                        "carried": inv["carried"], "highlighted": inv["highlighted"],
                        "not_direct_fk": sorted(n for n, c in inv["classes"].items() if c != "direct-fk"),
                        "picker_unavailable": [dict(x, group=" > ".join(r["path"])) for r in inv["view"]
                                               for x in r.get("unavailable") or []]}
    out["agrees_with_census"] = sorted(n for n, c in inv["classes"].items() if c == "direct-fk") == sorted(
        n for n, r in census_rows["bones"].items() if r["class"] == "direct-fk")
    if inv["full_body"].get("status") != "available":
        return out
    try:
        S = T.compile_request(ns, ns["prod_scope_request"](u"full_body"))
        roles = collections.Counter(S["ledger"].values())
        out["compile"] = {"posed": len(S["posed"]), "ledger_roles": dict(roles), "excluded": S.get("excluded"),
                          "all_bones_posed": sorted(S["posed"]) == sorted(D["bones"])}
    except Exception as exc:
        out["compile"] = {"error": "%s: %s" % (type(exc).__name__, exc), "code": getattr(exc, "code", None)}
        return out
    root = tempfile.mkdtemp(prefix="ec1_replay_")
    try:
        lib = T.library(root, u"ec1_replay")
        saved = T.save(ns, lib, ns["prod_scope_request"](u"full_body"), u"EC1 replay")
        fresh = T.reload(ns, lib, saved)
        out["save"] = {"saved_and_reloaded": fresh["record"] == saved["record"],
                       "kind": saved["record"]["pose"]["scope"]["kind"],
                       "root": saved["record"]["pose"]["structure"]["root"]}
        # Apply to a copy whose direct-FK orientation channels of three bones are turned.
        dst, _ = world(K, copy.deepcopy(D), indices)
        turned = []
        for n in sorted(census_rows["bones"]):
            if census_rows["bones"][n]["class"] == "direct-fk" and n != inv["root"] and len(turned) < 3:
                ch = [c for c, x in D["channels"].items() if x["to"] and x["to"]["handle"] == D["bones"][n][
                    "transform"] and x["to_attribute"] == "orientation"][0]
                T.turn(dst, ch, [0, 0, 1], 25)
                turned.append(ch)
        dst.evaluate()
        T.use(ns, dst, fx)
        result, verdict = T.apply(ns, fresh)
        out["apply_changed_copy"] = {"turned": turned, "phase": result.get("phase"), "verdict": verdict,
                                     "restored": all(dst.keys(c)[-1][1] == w.keys(c)[-1][1] for c in turned)}
    except Exception as exc:
        out["replay_error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        shutil.rmtree(root, True)
    return out


# --- 4. the questions and the verdict --------------------------------------------------------------------------------

def assess(raw, obs, expected, K, require_kit=True):
    rows = []
    check_observation(obs, rows, require_kit)
    identity = check_identity(obs, expected, rows)
    check_join(obs, rows)
    D = K["SF"].derive(obs, hashlib.sha256(raw).hexdigest())
    C, E = structure_criteria(rows, K, D, observed_indices(obs), identity["source_less_channels"],
                              [(op.get("id") or {}).get("type") for op in obs.get("operators") or []],
                              (obs.get("writer_index") or {}).get("operator_types") or {},
                              len((obs.get("rig") or {}).get("registrations") or []))
    return {"label": obs.get("label"), "sha256": hashlib.sha256(raw).hexdigest(), "verdict": verdict_of(rows),
            "criteria": rows, "identity": identity, "census": C, "cpm": E,
            "counts": {"bones": len(D["bones"]), "controls": len(D["controls"]), "channels": len(D["channels"]),
                       "operators": len(D["operators"]), "groups": len(D["groups"])}}


def structure_criteria(rows, K, D, indices, source_less, operator_types, document_operator_types,
                       rig_registrations):
    """Questions 1-5 on a discovery-form structure D (the census, then CPM's engine on the replay)."""
    C = census(D, indices, operator_types, document_operator_types, rig_registrations)
    bones = len(D["bones"])
    criterion(rows, "Q1.every_bone_has_one_direct_control", C["classes"].get("direct-fk", 0) == bones and
              not C["control_less_bones"], {"direct_fk": C["classes"].get("direct-fk", 0), "bones": bones,
                                            "control_less": C["control_less_bones"][:10]})
    not_direct = dict((n, r["reasons"]) for n, r in C["bones"].items() if r["class"] != "direct-fk")
    readable_failure = any(not x.startswith("unreadable:") for rs in not_direct.values() for x in rs)
    criterion(rows, "Q2.bindings_types_and_indices_supported", not not_direct, dict(list(not_direct.items())[:10]),
              unreadable=bool(not_direct) and not readable_failure)
    criterion(rows, "Q3.no_control_drives_several_bones", not C["controls_driving_several_bones"],
              C["controls_driving_several_bones"])
    criterion(rows, "Q3.no_source_less_bone_channels", not source_less, list(source_less)[:10])
    criterion(rows, "Q4.no_rig_registration", C["rig_registrations"] == 0, C["rig_registrations"])
    criterion(rows, "Q4.no_constraint_operators", not C["constraints"], C["constraints"])
    criterion(rows, "Q4.no_unsupported_operator_types", not C["unsupported_operator_types"],
              C["unsupported_operator_types"])
    E = run_cpm(K, D, indices, C)
    inv = E.get("inventory") or {}
    cpm_unreadable = inv.get("code") == "evidence-unreadable"     # CPM refuses the whole inventory on it
    criterion(rows, "Q5.cpm_classifies_every_bone_direct_fk", inv.get("classes") == {"direct-fk": bones},
              inv.get("classes") or inv.get("error"), unreadable=cpm_unreadable)
    criterion(rows, "Q5.cpm_agrees_with_the_census", E.get("agrees_with_census") is True, E.get("agrees_with_census"),
              unreadable=cpm_unreadable)
    criterion(rows, "Q5.cpm_full_body_available", (inv.get("full_body") or {}).get("status") == "available",
              inv.get("full_body"))
    criterion(rows, "Q5.full_body_compiles_every_bone_posed", (E.get("compile") or {}).get("all_bones_posed") is True,
              E.get("compile"))
    criterion(rows, "Q5.offline_replay_save_and_apply", (E.get("save") or {}).get("saved_and_reloaded") is True and
              (E.get("apply_changed_copy") or {}).get("verdict") == {"phase": "committed-verified"} and
              (E.get("apply_changed_copy") or {}).get("restored") is True,
              [E.get("save"), E.get("apply_changed_copy"), E.get("replay_error")])
    return C, E


def verdict_of(rows):
    results = [r["result"] for r in rows]
    gate = [r for r in rows if r["criterion"].startswith("observation.")]
    if any(r["result"] != "PASS" for r in gate) or "UNREADABLE" in results:
        verdict = "NO-CONCLUSION"
    elif "FAIL" in results:
        verdict = "NOT-CANDIDATE"
    else:
        verdict = "CANDIDATE"
    return verdict


def markdown(report):
    lines = ["# EC-1 Engineer control-coverage analysis", "",
             "CPM source `%s` (qualification mode, offline replay). Expected header `%s`." % (
                 report["cpm_sha256"], report["expected_header_sha256"]), ""]
    for r in report["observations"]:
        lines += ["## %s: **%s**" % (r["label"], r["verdict"]), "", "Observation `%s`. Counts: %s." % (
            r["sha256"], r["counts"]), "", "| Criterion | Result | Detail |", "|---|---|---|"]
        for c in r["criteria"]:
            d = json.dumps(c["detail"], sort_keys=True)
            lines.append("| %s | %s | `%s` |" % (c["criterion"], c["result"], d[:300].replace("|", "\\|")))
        C = r["census"]
        lines += ["", "- Census bone classes: %s" % C["classes"], "- Control types: %s" % C["control_types"],
                  "- Non-bone channel destinations: %s" % C["non_bone_destinations"],
                  "- Operator types (animation set and shot): %s; document-wide: %s" % (
                      C["operator_types"], C["document_operator_types"]),
                  "- CPM inventory: %s" % json.dumps((r["cpm"].get("inventory") or {}).get("full_body")), ""]
    lines.append("CANDIDATE means only that the model may enter a version 3 Full body Save/Apply native "
                 "qualification. The replay runs CPM against a fake scene built from the observation; it is not "
                 "evidence of native behaviour.")
    return "\n".join(lines) + "\n"


def write_exclusive(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return hashlib.sha256(data).hexdigest()


def main(argv, require_kit=True, label_re=LABEL_RE):
    if len(argv) != 4:
        print(__doc__)
        return 2
    src, dst, expected_path = argv[1], argv[2], argv[3]
    with io.open(expected_path, "rb") as f:
        expected_raw = f.read()
    expected = json.loads(expected_raw.decode("utf-8"))
    if expected.get("format") != "F01-EC1-expected-header-v1":
        raise SystemExit("REFUSED: not an EC-1 expected header")
    K = cpm_tools()
    rows = []
    for name in sorted(os.listdir(src)):
        if not name.endswith(".json") or not label_re.match(name[:-5]):
            continue
        with io.open(os.path.join(src, name), "rb") as f:
            raw = f.read()
        rows.append(assess(raw, json.loads(raw.decode("utf-8")), expected, K, require_kit))
    report = {"format": "F01-EC1-analysis-v1", "cpm_sha256": K["cpm_sha256"],
              "expected_header_sha256": hashlib.sha256(expected_raw).hexdigest(), "observations": rows}
    print("EC1_ANALYSIS.json", write_exclusive(os.path.join(dst, "EC1_ANALYSIS.json"),
                                               json.dumps(report, indent=1, sort_keys=True).encode("utf-8")))
    print("EC1_ANALYSIS.md", write_exclusive(os.path.join(dst, "EC1_ANALYSIS.md"), markdown(report).encode("utf-8")))
    for r in rows:
        failed = [c["criterion"] for c in r["criteria"] if c["result"] != "PASS"]
        print("%s: %s%s" % (r["label"], r["verdict"], (" (%s)" % ", ".join(failed)) if failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
