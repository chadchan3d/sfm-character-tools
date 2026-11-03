# -*- coding: utf-8 -*-
"""M-06 W2 fail-closed comparison of Observer v2 records (offline; independent of the instruments' code).

usage: python -I compare_obs.py INVARIANT A.json B.json [SPEC.json]

INVARIANT (each comparison declares exactly one):
  unchanged  A and B have identical authored state (target and peers) and identical required Undo fields.
  apply      B is A plus exactly the declared Apply delta; peers unchanged. SPEC:
               {"undo_desc": ..., "flex": {literal: {side: {"effective": v, "stored": v | "unchanged"}}},
                "bones": {bone: {"scale": v, "control_value": v, "graph": "existing" | "created"}}}
             Only the declared sides' authored value fields may change (key values, raw value array, compressed
             data, evaluation, destination, and the stored source only when declared); every other field of that
             literal, every undeclared side, and the declared graph's identities, topology, endpoints, expression,
             log metadata and memberships remain compared. Declared values are checked separately.
  aborted    B (after an aborted Apply) equals A (before it). SPEC is the injector's complete fired record; the
             comparator recomputes the created elements (controls, operators, channels, their logs and layers)
             from its baseline and in-transaction observations, reconciles them with the recorded list, requires
             each to be detached and unresolvable after the abort, and refuses any same-model peer change.
  undo       B (after Undo) equals A (the pre-Apply baseline); the owned entry is on the Redo stack (SPEC: redo_desc).
  redo       B (after Redo) equals A (the applied state); the owned entry is on the Undo stack (SPEC: undo_desc).
  reopened   B (after save and reopen) equals A in portable form: freshly resolved identities, no runtime handles or
             ids compared (SPEC optional: document_path; static_play: [literal, ...] still admitted after reload).
  preset     A is an observation and B a saved CPM preset: complete bone coverage and full-precision effective values
             from each side's verified representation (EMPTY: the coherent stored source; keyed: the key).
  prepared   deferred fixture: B is A with only the declared flex's stored source changed (SPEC: literal, stored),
             now admitted STATIC_PLAY_ONE_KEY_ZERO with sole-writer evidence, and the existing scale graph is the
             qualified mode-3 graph (input and output mode 3), untouched.

Verdicts: PASS (exit 0), OBSERVED MISMATCH (exit 1), INSUFFICIENT EVIDENCE (exit 2). Only PASS returns success.
Insufficient: a missing required field (never defaulted), any unreadable marker (even identical in A and B), an
incomplete observation (the Observer's "complete" flag is necessary, never sufficient: nested log, layer,
evaluation, representation and membership evidence is validated here independently), a CPM other than the accepted
W1 candidate, a context that changed during an observation, or contradictory / wrong-instance identities.
"""
from __future__ import print_function

import copy
import io
import json
import math
import ntpath
import re
import struct
import sys

PASS, MISMATCH, INSUFFICIENT = "PASS", "OBSERVED MISMATCH", "INSUFFICIENT EVIDENCE"
EXIT = {PASS: 0, MISMATCH: 1, INSUFFICIENT: 2}
FORMAT = "M06W2-observation-v2"
ACCEPTED_W1_SHA256 = "fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d"
TOP = ("format", "core", "config_name", "config_sha256", "declared", "context_begin", "context_end", "integrity", "channels_clips",
       "target", "peers", "unresolved_channels", "undo", "watch", "insufficient", "complete")
ANIMSET = ("identity", "controls", "operators", "control_groups", "flex", "nonbody", "transform_controls", "bones",
           "graphs")
IDENTITY = ("animset", "game_model", "model", "checksum")
UNDO = ("enabled", "can_undo", "can_redo", "undo_desc", "redo_desc")
VIEW = ("channel", "from", "from_attribute", "to", "to_attribute", "mode", "log")
SIDE = VIEW + ("stored", "clips", "destination_value", "destination_writers", "control_writers", "representation")
LOG = ("log", "channel_log_attribute", "usedefaultvalue", "defaultvalue", "bookmarks", "curveinfo", "is_empty",
       "layer_count", "layers", "evaluated")
LAYER = ("layer", "key_count", "keys", "times", "values", "curvetypes", "compressed", "curveinfo")
GRAPH = ("bone", "bone_index", "output", "operator", "operator_attributes", "inputs")
OPERATOR = ("expr", "lo", "hi", "value", "result")
FIRED = ("event", "injector", "candidate_sha256", "baseline", "in_transaction", "created", "memberships_added",
         "scale_attributes_created", "peer_changes")
STATES = ("present", "absent", "null", "gone")
ADMITTED = ("EMPTY", "ONE_KEY_ZERO", "STATIC_PLAY_ONE_KEY_ZERO")
TRANSIENT = ("current_ticks_transient", "label", "python", "taken_local", "watch_file", "ok", "traceback")
INVARIANTS = ("unchanged", "apply", "aborted", "undo", "redo", "reopened", "preset", "prepared")
DEFERRED_CONFIG = "m06w2_deferred_config.json"
ORDINARY_CONFIG = "m06w2_config.json"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"   # SHA-256 of zero bytes
SUPPORTED_ORIGINS = ("EMPTY", "ONE_KEY_ZERO", "STATIC_PLAY_ONE_KEY_ZERO")
try:
    TEXT = (str, unicode)  # noqa: F821
except NameError:
    TEXT = (str,)
CPM_EPS = 1.0e-5          # CPM's close_enough tolerance for representation coherence
DECLARED = "<declared>"
try:
    NUMBER = (int, float, long)  # noqa: F821
except NameError:
    NUMBER = (int, float)


class Verdict(Exception):
    def __init__(self, verdict, reasons):
        Exception.__init__(self, verdict)
        self.verdict, self.reasons = verdict, reasons


def insufficient(*reasons):
    raise Verdict(INSUFFICIENT, list(reasons))


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def number(x):
    return isinstance(x, NUMBER) and not isinstance(x, bool) and not (math.isnan(x) or math.isinf(x))


def close(x, y, tol):
    return number(x) and number(y) and abs(x - y) <= tol


def pv(rec):
    """The value of a present state record (None otherwise)."""
    return rec.get("v") if isinstance(rec, dict) and rec.get("s") == "present" else None


def key(rec):
    v = pv(rec)
    return None if not isinstance(v, dict) else (v.get("handle"), v.get("id"))


def portable_key(rec):
    v = pv(rec)
    return None if not isinstance(v, dict) else (v.get("type"), v.get("name"))


# ---------------------------------------------------------------------------
# Evidence sufficiency (independent of the Observer's own "complete" flag)
# ---------------------------------------------------------------------------

def scan_states(value, path, problems):
    """Every state record must be readable; an unreadable marker is never preservation evidence."""
    if isinstance(value, dict):
        if "s" in value and set(value) <= set(("s", "v", "e")):
            if value["s"] not in STATES:
                problems.append("%s: %s (%s)" % (path, value["s"], value.get("e")))
            if value["s"] == "present" and "v" not in value:
                problems.append("%s: present without a value" % path)
        for k in sorted(value):
            scan_states(value[k], "%s/%s" % (path, k), problems)
    elif isinstance(value, list):
        for i, x in enumerate(value):
            scan_states(x, "%s/%d" % (path, i), problems)


def sha256_text(value):
    """A genuine SHA-256 text rendering: a string of exactly 64 hexadecimal characters. Null, empty, non-text,
    truncated, padded or non-hexadecimal values are not digests, and matching invalid values prove nothing."""
    return isinstance(value, TEXT) and len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


def require_keys(obj, keys, path, problems):
    if not isinstance(obj, dict):
        problems.append("%s: missing or not an object" % path)
        return False
    missing = [k for k in keys if k not in obj]
    for k in missing:
        problems.append("%s/%s: required field missing" % (path, k))
    return not missing


def check_log(log_rec, path, problems):
    """A channel's log evidence: identities, the channel-log relationship, metadata, layers, raw key arrays and the
    native evaluation, each present and mutually consistent."""
    log = pv(log_rec)
    if not require_keys(log, LOG, path, problems):
        return
    if pv(log["log"]) is None:
        problems.append("%s/log: no log identity" % path)
    if key(log["channel_log_attribute"]) != key(log["log"]):
        problems.append("%s: the channel's log attribute is not the log GetLog() returned" % path)
    if type(pv(log["is_empty"])) is not bool:
        problems.append("%s/is_empty: not a recorded boolean" % path)
    layers = log["layers"]
    if not isinstance(layers, list) or pv(log["layer_count"]) != len(layers):
        problems.append("%s: layer_count does not match the recorded layers" % path)
        return
    if pv(log["evaluated"]) is None or not number(pv(log["evaluated"])):
        problems.append("%s/evaluated: no finite native evaluation" % path)
    for i, layer in enumerate(layers):
        lpath = "%s/layers/%d" % (path, i)
        if not require_keys(layer, LAYER, lpath, problems):
            continue
        keys = pv(layer["keys"])
        if pv(layer["layer"]) is None or not isinstance(keys, list) or pv(layer["key_count"]) != len(keys):
            problems.append("%s: layer identity, key count or keys missing or inconsistent" % lpath)
            continue
        times, values = pv(layer["times"]), pv(layer["values"])
        if not isinstance(times, list) or not isinstance(values, list):
            problems.append("%s: raw key arrays not recorded" % lpath)
            continue
        try:
            raw = [[t["ticks"], v] for t, v in zip(times, values)]
        except Exception:
            problems.append("%s: raw key arrays malformed" % lpath)
            continue
        if len(times) != len(keys) or len(values) != len(keys) or raw != keys:
            problems.append("%s: raw key arrays disagree with the keys" % lpath)
        if compressed_state(layer) == "malformed":
            problems.append("%s/compressed: not a verified absence or a well-formed {length, sha256} record (%r)" %
                            (lpath, layer["compressed"]))


def compressed_state(layer):
    """A layer's compressed block: "absent" (verified absence), "empty" (present, zero bytes, the empty digest),
    "nonempty" (present, data), "unreadable", or "malformed" (a present record that is not {length, sha256} with a
    non-negative length and a 64-hex digest, or zero bytes with another digest)."""
    rec = layer.get("compressed")
    if not isinstance(rec, dict):
        return "malformed"
    if rec.get("s") == "absent":
        return "absent"
    if rec.get("s") != "present":
        return "unreadable"
    v = pv(rec)
    if not isinstance(v, dict) or sorted(v) != ["length", "sha256"]:
        return "malformed"
    n, h = v["length"], v["sha256"]
    if not isinstance(n, NUMBER) or isinstance(n, bool) or n != int(n) or n < 0 or not isinstance(h, TEXT) or \
            len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        return "malformed"
    if n == 0:
        return "empty" if h == EMPTY_SHA256 else "malformed"
    return "nonempty"


def supported_flex_metadata(log):
    """CPM's flex_static_play_admitted() metadata: no curve info on the log or layer, no per-key curve types, an
    empty (or absent) compressed block."""
    layer = log["layers"][0]
    return (log["curveinfo"].get("s") in ("null", "absent") and layer["curveinfo"].get("s") in ("null", "absent")
            and (layer["curvetypes"].get("s") == "absent" or pv(layer["curvetypes"]) == [])
            and compressed_state(layer) in ("absent", "empty"))


def check_view(view, path, problems, need_log=True):
    if not require_keys(view, VIEW, path, problems):
        return False
    if pv(view["channel"]) is None:
        problems.append("%s/channel: no channel identity" % path)
        return False
    if view["log"].get("s") != "present":
        if need_log:
            problems.append("%s/log: required log not present (%s)" % (path, view["log"].get("s")))
        return False
    check_log(view["log"], path + "/log", problems)
    return True


def representation_of(side):
    """The representation re-derived from the side's own raw evidence (CPM's state_kind rules)."""
    log = pv(side["log"])
    layers = log["layers"]
    if len(layers) != 1:
        return "OTHER"
    keys = pv(layers[0]["keys"])
    stored, evaluated, dest, mode = pv(side["stored"]), pv(log["evaluated"]), pv(side["destination_value"]), \
        pv(side["mode"])
    if not keys:
        return "EMPTY" if pv(log["is_empty"]) is True else "OTHER"
    if len(keys) == 1 and keys[0][0] == 0 and pv(log["is_empty"]) is False:
        k = keys[0][1]
        if k == stored:
            return "ONE_KEY_ZERO"
        if mode == 3 and k == evaluated and k == dest and supported_flex_metadata(log):
            return "STATIC_PLAY_ONE_KEY_ZERO"
    return "OTHER"


def effective_value(side):
    """(value, problem): the effective value from the verified representation. EMPTY: the stored source, coherent
    with the evaluation and destination; ONE_KEY_ZERO / STATIC_PLAY_ONE_KEY_ZERO: the key. Missing, contradictory or
    non-finite evidence is a problem, never None."""
    rep = representation_of(side)
    log = pv(side["log"])
    stored, evaluated, dest = pv(side["stored"]), pv(log["evaluated"]), pv(side["destination_value"])
    if rep == "EMPTY":
        if not (number(stored) and close(stored, evaluated, CPM_EPS) and close(stored, dest, CPM_EPS)):
            return None, "EMPTY representation is not coherent (stored %r, evaluated %r, destination %r)" % (
                stored, evaluated, dest)
        return stored, None
    if rep in ("ONE_KEY_ZERO", "STATIC_PLAY_ONE_KEY_ZERO"):
        k = pv(log["layers"][0]["keys"])[0][1]
        if not number(k) or not close(k, evaluated, CPM_EPS) or not close(k, dest, CPM_EPS):
            return None, "%s key is not finite and coherent (key %r, evaluated %r, destination %r)" % (
                rep, k, evaluated, dest)
        return k, None
    return None, "unsupported representation %s" % rep


def check_side(side, path, problems):
    if not require_keys(side, ("stored", "channel"), path, problems):
        return
    if side["channel"].get("s") != "present":
        return
    if not require_keys(side, SIDE, path, problems) or not check_view(side, path, problems):
        return
    if not pv(side["clips"]):
        problems.append("%s: the channel is in no channels clip (channel-container membership missing)" % path)
    for k in ("destination_writers", "control_writers"):
        if not isinstance(pv(side[k]), list):
            problems.append("%s/%s: not recorded" % (path, k))
    if problems:
        return
    claimed = pv(side["representation"])
    if claimed != representation_of(side):
        problems.append("%s: representation %r contradicts its evidence (%r)" % (path, claimed,
                                                                                 representation_of(side)))


def check_graph(rec, g, obs, path, problems):
    if not require_keys(g, GRAPH, path, problems) or not require_keys(g["operator_attributes"], OPERATOR,
                                                                         path + "/operator_attributes", problems):
        return
    if pv(g["operator"]) is None or not isinstance(g["inputs"], list) or not g["inputs"]:
        problems.append("%s: graph operator or inputs missing" % path)
        return
    ok = check_view(g["output"], path + "/output", problems)
    for i, view in enumerate(g["inputs"]):
        ok = check_view(view, "%s/inputs/%d" % (path, i), problems) and ok
        if not require_keys(view.get("source_attributes"), ("value", "defaultValue"),
                            "%s/inputs/%d/source_attributes" % (path, i), problems):
            ok = False
    if not ok:
        return
    bones = [b for b in rec["bones"] if b["name"] == g["bone"]]
    if len(bones) != 1 or pv(g["output"]["to_attribute"]) != "scale" or \
            key(g["output"]["to"]) != key(bones[0]["transform"]):
        problems.append("%s: the output channel does not write this bone's scale" % path)
    # The graph's channels must be the shot's channels (in a channels clip). Operator and control memberships are
    # observed state, compared by every invariant and required by graph_attachment() for Apply.
    clipped = set(ch["id"] for clip in obs["channels_clips"] for ch in clip["channels"])
    for view in [g["output"]] + list(g["inputs"]):
        if pv(view["channel"])["id"] not in clipped:
            problems.append("%s: graph channel %s is in no channels clip" % (path, pv(view["channel"])["name"]))
    for view in g["inputs"]:
        if pv(view["from"]) is None:
            problems.append("%s: graph input has no source control" % path)


def check_animset(rec, path, obs, problems):
    if not require_keys(rec, ANIMSET, path, problems):
        return
    require_keys(rec["identity"], IDENTITY, path + "/identity", problems)
    for kind in ("flex", "nonbody"):
        for lit, row in sorted((rec.get(kind) or {}).items()):
            if not isinstance(row, dict) or "unavailable" in row or "control" not in row or "shape" not in row:
                problems.append("%s/%s/%s: control unavailable or incomplete" % (path, kind, lit))
                continue
            for side in (("mono",) if row["shape"] == "MONO" else ("left", "right")):
                check_side(row.get(side), "%s/%s/%s/%s" % (path, kind, lit, side), problems)
    if not rec.get("bones"):
        problems.append("%s/bones: no bones recorded" % path)
    for i, bone in enumerate(rec.get("bones") or []):
        if not require_keys(bone, ("index", "name", "transform", "scale", "writers", "scale_writers"),
                            "%s/bones/%d" % (path, i), problems):
            continue
        graphs = [g for g in rec["graphs"] if isinstance(g, dict) and g.get("bone") == bone["name"]]
        if len(graphs) != len(bone["scale_writers"]):
            problems.append("%s/bones/%d: %d scale writer(s) but %d graph record(s)" % (
                path, i, len(bone["scale_writers"]), len(graphs)))
    for i, g in enumerate(rec.get("graphs") or []):
        check_graph(rec, g, obs, "%s/graphs/%d" % (path, i), problems)


def sufficiency(obs, name):
    problems = []
    if not require_keys(obs, TOP, name, problems):
        insufficient(*problems)
    if obs["format"] != FORMAT:
        problems.append("%s: format %r" % (name, obs["format"]))
    if not sha256_text(obs["config_sha256"]):
        problems.append("%s/config_sha256: %r is not a SHA-256 digest (64 hexadecimal characters)" %
                        (name, obs["config_sha256"]))
    if obs["complete"] is not True or obs["insufficient"] != []:
        problems.append("%s: observation incomplete: %s" % (name, (obs["insufficient"] or ["complete=false"])[:6]))
    if obs["unresolved_channels"] != []:
        problems.append("%s: channels with unreadable endpoints" % name)
    if obs["context_begin"] != obs["context_end"]:
        problems.append("%s: context changed during the observation" % name)
    cpm = pv((obs["integrity"] or {}).get("cpm"))
    if not isinstance(cpm, dict) or cpm.get("actual") != ACCEPTED_W1_SHA256 or cpm.get("match") is not True:
        problems.append("%s/integrity/cpm: the installed CPM is not verified as the accepted W1 candidate" % name)
    declared = obs["declared"]
    if not require_keys(declared, ("shot", "target_animset", "peers", "body", "nonbody"), name + "/declared",
                        problems):
        insufficient(*problems)
    if sorted(obs["peers"] or {}) != sorted(declared["peers"]):
        problems.append("%s: peer records are not exactly the declared peers" % name)
    if obs["target"] is None:
        problems.append("%s: no target record" % name)
    else:
        check_animset(obs["target"], name + "/target", obs, problems)
        for kind, listing in (("flex", "body"), ("nonbody", "nonbody")):
            for rec_name, rec in [("target", obs["target"])] + sorted((obs["peers"] or {}).items()):
                if rec is not None and sorted(rec.get(kind) or {}) != sorted(declared[listing]):
                    problems.append("%s/%s: %s records are not exactly the declared %s literals" %
                                    (name, rec_name, kind, listing))
    for peer, rec in sorted((obs["peers"] or {}).items()):
        if rec is None:
            problems.append("%s/peers/%s: missing" % (name, peer))
        else:
            check_animset(rec, "%s/peers/%s" % (name, peer), obs, problems)
    require_keys(obs["undo"], UNDO, name + "/undo", problems)
    for label, row in sorted(((obs["integrity"] or {}).get("protected") or {}).items()):
        if pv(row) is None or pv(row).get("match") is not True:
            problems.append("%s/integrity/protected/%s: not verified unchanged" % (name, label))
    scan_states(obs, name, problems)
    if problems:
        insufficient(*problems)


def identities(a, b, portable, labels=("A", "B")):
    problems = []
    kf = portable_key if portable else key
    if a["config_sha256"] != b["config_sha256"] or a["config_name"] != b["config_name"]:
        problems.append("%s and %s were taken with different configurations" % labels)
    for side, obs in zip(labels, (a, b)):
        t = obs["target"]["identity"]["animset"]
        for peer, rec in sorted(obs["peers"].items()):
            if kf(rec["identity"]["animset"]) == kf(t) or key(rec["identity"]["animset"]) == key(t):
                problems.append("%s: peer %s is the target instance" % (side, peer))
    if sorted(a["peers"]) != sorted(b["peers"]):
        problems.append("peer sets differ")
    pairs = [("target", a["target"], b["target"])] + [("peers/" + p, a["peers"][p], b["peers"].get(p))
                                                     for p in sorted(a["peers"])]
    for label, ra, rb in pairs:
        if rb is None:
            continue
        for k in IDENTITY:
            va, vb = ra["identity"][k], rb["identity"][k]
            if k in ("animset", "game_model"):
                if kf(va) != kf(vb):
                    problems.append("%s: %s identity differs (wrong instance)" % (label, k))
            elif va != vb:
                problems.append("%s: %s differs" % (label, k))
    if pv(a["context_begin"]["shot"])["name"] != pv(b["context_begin"]["shot"])["name"]:
        problems.append("shot differs")
    if not portable and a["context_begin"]["document_path"] != b["context_begin"]["document_path"]:
        problems.append("document differs")
    if problems:
        insufficient(*problems)


# ---------------------------------------------------------------------------
# Authored projection and differences
# ---------------------------------------------------------------------------

def strip(value, drop_identity):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in TRANSIENT or (drop_identity and k in ("handle", "id")):
                continue
            out[k] = strip(v, drop_identity)
        return out
    if isinstance(value, list):
        items = [strip(v, drop_identity) for v in value]
        if drop_identity:
            try:
                items = sorted(items, key=lambda x: json.dumps(x, sort_keys=True))
            except Exception:
                pass
        return items
    return value


def authored(obs, drop_identity=False):
    return {"target": strip(obs["target"], drop_identity),
            "peers": strip(obs["peers"], drop_identity),
            "channels_clips": strip(obs["channels_clips"], drop_identity)}


def differences(a, b, path="", out=None, limit=200):
    """Exact structural differences; a key present on one side only is a difference (never defaulted)."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append("%s/%s: present on one side only" % (path, k))
            else:
                differences(a[k], b[k], "%s/%s" % (path, k), out, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append("%s: length %d -> %d" % (path, len(a), len(b)))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                differences(x, y, "%s/%d" % (path, i), out, limit)
    elif type(a) is not type(b) and not (isinstance(a, NUMBER) and isinstance(b, NUMBER) and
                                         not isinstance(a, bool) and not isinstance(b, bool)):
        out.append("%s: %r -> %r" % (path, a, b))
    elif a != b:
        out.append("%s: %r -> %r" % (path, a, b))
    return out


def undo_fields(obs):
    return dict((k, obs["undo"][k].get("v")) for k in UNDO)


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def expect_equal(a, b, drop_identity=False, what="authored state"):
    diffs = differences(authored(a, drop_identity), authored(b, drop_identity))
    if diffs:
        raise Verdict(MISMATCH, ["%s differs: %s" % (what, d) for d in diffs[:40]])


def inv_unchanged(a, b, spec):
    expect_equal(a, b)
    if undo_fields(a) != undo_fields(b):
        raise Verdict(MISMATCH, ["Undo state changed: %r -> %r" % (undo_fields(a), undo_fields(b))])


def mask_log_values(log_rec, empty_origin=False):
    """A log with only its authored values masked: key values (times kept), the raw value array and the native
    evaluation. Identities, the channel-log relationship, defaults, curve and bookmark metadata, compressed data,
    the empty flag, layer identities, key counts, key times and curve types stay compared. For a declared side whose
    origin is EMPTY (CPM's write_side: ClearAndAddSampleAtTime(0) on the same layer) the key structure (keys, times,
    values, key count, empty flag) is masked too; empty_transition_problems() then requires exactly one key at time
    zero with the declared value."""
    log = pv(log_rec)
    if log is None:
        return log_rec
    log = copy.deepcopy(log)
    log["evaluated"] = DECLARED
    if empty_origin:
        log["is_empty"] = DECLARED
    for layer in log["layers"]:
        if empty_origin:
            layer["keys"] = layer["times"] = layer["key_count"] = DECLARED
        else:
            layer["keys"] = {"s": "present", "v": [[k[0], DECLARED] for k in pv(layer["keys"])]}
        layer["values"] = DECLARED
    return {"s": "present", "v": log}


def empty_transition_problems(before, after, effective, tol):
    """CPM's EMPTY origin write: the same single layer now holds exactly one key, at time zero, whose value is the
    declared effective value and the new stored source (ONE_KEY_ZERO); the log is no longer empty."""
    log = pv(after["log"])
    problems = []
    if len(log["layers"]) != 1 or len(pv(before["log"])["layers"]) != 1:
        return ["the EMPTY origin write must keep exactly one layer"]
    layer = log["layers"][0]
    keys, times, values = pv(layer["keys"]), pv(layer["times"]), pv(layer["values"])
    if not isinstance(keys, list) or len(keys) != 1 or pv(layer["key_count"]) != 1:
        problems.append("expected exactly one key after the EMPTY origin write, found %r" % (keys,))
    else:
        if keys[0][0] != 0 or [t.get("ticks") for t in times] != [0]:
            problems.append("the written key is not at time zero (%r)" % (keys[0][0],))
        if not close(keys[0][1], effective, tol) or len(values) != 1 or not close(values[0], effective, tol):
            problems.append("the written key %r is not the declared value %r" % (keys[0][1], effective))
    if pv(log["is_empty"]) is not False:
        problems.append("IsEmpty() is still %r after the write" % pv(log["is_empty"]))
    if representation_of(after) != "ONE_KEY_ZERO":
        problems.append("the result is %s, not ONE_KEY_ZERO" % representation_of(after))
    return problems


def mask_side(side, stored_declared, empty_origin=False):
    s = copy.deepcopy(side)
    s["log"] = mask_log_values(side["log"], empty_origin)
    s["destination_value"] = s["representation"] = DECLARED
    if stored_declared:
        s["stored"] = DECLARED
    return s


def graph_ids(g):
    ids = set()
    for rec in [g["output"]["channel"], g["operator"]] + [i["channel"] for i in g["inputs"]] + \
            [i["from"] for i in g["inputs"]]:
        if pv(rec) is not None:
            ids.add(pv(rec)["id"])
    for view in [g["output"]] + list(g["inputs"]):
        log = pv(view["log"])
        if log is not None:
            ids.add(pv(log["log"])["id"])
            for layer in log["layers"]:
                ids.add(pv(layer["layer"])["id"])
    return ids


def mask_graph(g):
    """Only what CPM's prod_bs_write_existing_scale() authors is released: the input layer's key value (and its raw
    value array and evaluation), the source control value, and the expression's evaluated value and result. The
    output channel and its log (identity, mode, keys, defaults, metadata) are never written and stay compared."""
    m = copy.deepcopy(g)
    for view, orig in zip(m["inputs"], g["inputs"]):
        view["log"] = mask_log_values(orig["log"])
        view["source_attributes"]["value"] = DECLARED
    m["operator_attributes"]["value"] = m["operator_attributes"]["result"] = DECLARED
    return m


def lerp_expected(g, cv):
    """(expected physical scale, problem) for CPM's supported expression lerp(value, lo, hi) with distinct finite
    lo and hi."""
    ops = g["operator_attributes"]
    expr, lo, hi = pv(ops["expr"]), pv(ops["lo"]), pv(ops["hi"])
    if not isinstance(expr, TEXT) or expr.replace(" ", "") != "lerp(value,lo,hi)":
        return None, "unsupported scale expression %r" % (expr,)
    if not number(lo) or not number(hi) or close(lo, hi, CPM_EPS):
        return None, "unsupported lerp bounds lo=%r hi=%r" % (lo, hi)
    return lo + (hi - lo) * cv, None


def output_representation_problems(g):
    """CPM's supported scale outputs: mode 1 (the historical output pass), or mode 3 with one empty output log layer,
    IsEmpty() True and usedefaultvalue False (the accepted M-05 graph). Anything else is unsupported."""
    mode, out = pv(g["output"]["mode"]), pv(g["output"]["log"])
    if mode == 1:
        return []
    if mode != 3:
        return ["scale output channel mode %r is not supported" % (mode,)]
    if len(out["layers"]) != 1 or pv(out["layers"][0]["keys"]) != [] or pv(out["is_empty"]) is not True or \
            pv(out["usedefaultvalue"]) is not False:
        return ["the mode-3 scale output log is not the supported empty log with usedefaultvalue False (keys %r, "
                "is_empty %r, usedefaultvalue %r)" % ([pv(L["keys"]) for L in out["layers"]], pv(out["is_empty"]),
                                                       pv(out["usedefaultvalue"]))]
    return []


def graph_value_problems(g, bone, want, tol):
    """The declared scale on one graph, each piece checked independently: the source control value and the input
    log's single key at time zero (and its evaluation) equal control_value; the expression's input equals it; the
    expression is the supported lerp and its result, the physical bone scale and the declared scale all equal
    lerp(control_value, lo, hi); the output is a supported representation. The output log's own value is not a
    requirement (the accepted M-05 output log is empty)."""
    problems = []
    cv, scale = want.get("control_value"), want["scale"]
    if not number(cv) or not number(scale):
        insufficient("apply: bone %s must declare finite control_value and scale" % bone["name"])
    if len(g["inputs"]) != 1:
        problems.append("the scale graph has %d inputs, not one" % len(g["inputs"]))
    for view in g["inputs"]:
        if not close(pv(view["source_attributes"]["value"]), cv, tol):
            problems.append("scale control source %r, declared %r" % (pv(view["source_attributes"]["value"]), cv))
        log = pv(view["log"])
        keys = [k for L in log["layers"] for k in pv(L["keys"])]
        if len(log["layers"]) != 1 or len(keys) != 1 or keys[0][0] != 0 or not close(keys[0][1], cv, tol) or \
                not close(pv(log["evaluated"]), cv, tol):
            problems.append("scale input log is not one key at time zero holding the declared control value (%r)" %
                            (keys,))
    if not close(pv(g["operator_attributes"]["value"]), cv, tol):
        problems.append("scale expression input %r, declared %r" % (pv(g["operator_attributes"]["value"]), cv))
    expected, problem = lerp_expected(g, cv)
    if problem:
        problems.append(problem)
    else:
        for label, got in (("expression result", pv(g["operator_attributes"]["result"])),
                           ("physical scale", pv(bone["scale"])), ("declared scale", scale)):
            if not close(got, expected, tol):
                problems.append("%s %r is not lerp(%r) = %r" % (label, got, cv, expected))
    problems.extend(output_representation_problems(g))
    return problems


def inv_apply(a, b, spec):
    for k in ("undo_desc", "flex", "bones"):
        if k not in spec:
            insufficient("apply: SPEC must declare %s" % k)
    tol = float(spec.get("tolerance", 1.0e-6))
    pa, pb = authored(a), authored(b)
    ta, tb = pa["target"], pb["target"]
    reasons = []
    for lit, sides in sorted(spec["flex"].items()):
        oa, ob = a["target"]["flex"].get(lit), b["target"]["flex"].get(lit)
        ra, rb = ta["flex"].get(lit), tb["flex"].get(lit)
        if ra is None or rb is None or ra["shape"] != rb["shape"]:
            insufficient("apply: declared flex %s not observed in both" % lit)
        for side, want in sorted(sides.items()):
            if side not in ra or side not in rb or pv(ra[side]["channel"]) is None:
                insufficient("apply: declared side %s/%s not observed with a channel" % (lit, side))
            if "effective" not in want or not number(want["effective"]):
                insufficient("apply: %s/%s must declare a finite effective value" % (lit, side))
            sb = rb[side]
            stored = want.get("stored", "unchanged")
            origin = representation_of(oa[side])
            if origin not in SUPPORTED_ORIGINS:
                reasons.append("flex %s/%s: origin representation %s is not one CPM writes" % (lit, side, origin))
            if origin == "EMPTY":
                reasons.extend("flex %s/%s (EMPTY origin): %s" % (lit, side, p) for p in
                               empty_transition_problems(oa[side], ob[side], want["effective"], tol))
            value, problem = effective_value(sb)
            if problem:
                reasons.append("flex %s/%s after Apply: %s" % (lit, side, problem))
            elif not close(value, want["effective"], tol):
                reasons.append("flex %s/%s: effective %r, declared %r" % (lit, side, value, want["effective"]))
            if not close(pv(pv(sb["log"])["evaluated"]), want["effective"], tol) or \
                    not close(pv(sb["destination_value"]), want["effective"], tol):
                reasons.append("flex %s/%s: evaluated %r / destination %r, declared %r" % (
                    lit, side, pv(pv(sb["log"])["evaluated"]), pv(sb["destination_value"]), want["effective"]))
            if stored != "unchanged" and not close(pv(sb["stored"]), stored, tol):
                reasons.append("flex %s/%s: stored source %r, declared %r" % (lit, side, pv(sb["stored"]), stored))
            ra[side] = mask_side(ra[side], stored != "unchanged", origin == "EMPTY")
            rb[side] = mask_side(sb, stored != "unchanged", origin == "EMPTY")
    created_ids = set()
    for bone_name, want in sorted(spec["bones"].items()):
        ba = [x for x in ta["bones"] if x["name"] == bone_name]
        bb = [x for x in tb["bones"] if x["name"] == bone_name]
        if len(ba) != 1 or len(bb) != 1:
            insufficient("apply: declared bone %s not observed exactly once" % bone_name)
        ga = [g for g in ta["graphs"] if g["bone"] == bone_name]
        gb = [g for g in tb["graphs"] if g["bone"] == bone_name]
        if want.get("graph") == "existing":
            if len(ga) != 1 or len(gb) != 1:
                reasons.append("bone %s: the existing graph is not exactly one graph before and after" % bone_name)
                continue
            if graph_ids(ga[0]) != graph_ids(gb[0]):
                reasons.append("bone %s: existing graph identities changed (graph replaced)" % bone_name)
            reasons.extend("bone %s: %s" % (bone_name, r) for r in graph_attachment(b, gb[0]))
            reasons.extend("bone %s: %s" % (bone_name, r) for r in graph_value_problems(gb[0], bb[0], want, tol))
            ta["graphs"][ta["graphs"].index(ga[0])] = mask_graph(ga[0])
            tb["graphs"][tb["graphs"].index(gb[0])] = mask_graph(gb[0])
        elif want.get("graph") == "created":
            if ga or len(gb) != 1:
                reasons.append("bone %s: expected no graph before and exactly one created graph after" % bone_name)
                continue
            reasons.extend("bone %s: %s" % (bone_name, r) for r in graph_attachment(b, gb[0]))
            reasons.extend("bone %s: %s" % (bone_name, r) for r in graph_value_problems(gb[0], bb[0], want, tol))
            created_ids = created_ids | graph_ids(gb[0])
            tb["graphs"].remove(gb[0])
            out_id = pv(gb[0]["output"]["channel"])["id"]
            bb[0]["writers"] = [w for w in bb[0]["writers"] if w["channel"]["id"] != out_id]
            bb[0]["scale_writers"] = [w for w in bb[0]["scale_writers"] if w["id"] != out_id]
        else:
            insufficient("apply: bone %s must declare graph existing or created" % bone_name)
        ba[0]["scale"] = bb[0]["scale"] = DECLARED
    tb["controls"] = [c for c in tb["controls"] if c["id"] not in created_ids]
    tb["operators"] = [c for c in tb["operators"] if c["id"] not in created_ids]
    tb["control_groups"] = [p for p in tb["control_groups"] if p["control"]["id"] not in created_ids]
    for side in (pa, pb):
        side["channels_clips"] = [dict(c, channels=[ch for ch in c["channels"] if ch["id"] not in created_ids])
                                  for c in side["channels_clips"]]
    reasons.extend("undeclared Apply change: %s" % d for d in differences(pa, pb)[:40])
    u = undo_fields(b)
    if u["can_undo"] is not True or u["undo_desc"] != spec["undo_desc"]:
        reasons.append("after Apply the owned entry is not the top Undo entry: %r" % (u,))
    if reasons:
        raise Verdict(MISMATCH, reasons)


def graph_attachment(obs, g):
    """Each created graph element in its own container: control in the animation set's controls and in a control
    group, operator in its operators, every channel in a channels clip."""
    t = obs["target"]
    controls = set(r["id"] for r in t["controls"])
    operators = set(r["id"] for r in t["operators"])
    grouped = set(p["control"]["id"] for p in t["control_groups"])
    clipped = set(ch["id"] for clip in obs["channels_clips"] for ch in clip["channels"])
    problems = []
    for view in [g["output"]] + list(g["inputs"]):
        if pv(view["channel"])["id"] not in clipped:
            problems.append("created channel %s is in no channels clip" % pv(view["channel"])["name"])
    if pv(g["operator"])["id"] not in operators:
        problems.append("created operator is not in the animation set's operators")
    for view in g["inputs"]:
        src = pv(view["from"])
        if src is not None:
            if src["id"] not in controls:
                problems.append("created control %s is not in the animation set's controls" % src["name"])
            if src["id"] not in grouped:
                problems.append("created control %s is in no control group" % src["name"])
    return problems


def memberships(obs):
    ids = set()
    t = obs["target"]
    for row in t["controls"] + t["operators"]:
        ids.add(row["id"])
    for pair in t["control_groups"]:
        ids.add(pair["control"]["id"])
    for clip in obs["channels_clips"]:
        for ch in clip["channels"]:
            ids.add(ch["id"])
    for g in t["graphs"]:
        ids |= graph_ids(g)
    return ids


def recompute_created(baseline, during):
    """The comparator's own creation inventory from the injector's two observations: new controls, operators and
    channels, and each created channel's log and layers (from its in-transaction graph view)."""
    tb, td = baseline["target"], during["target"]
    created = {}
    for listing, role in (("controls", "control"), ("operators", "operator")):
        known = set(r["id"] for r in tb[listing])
        for r in td[listing]:
            if r["id"] not in known:
                created[r["id"]] = (role, r)
    known = set(ch["id"] for clip in baseline["channels_clips"] for ch in clip["channels"])
    views = dict((pv(v["channel"])["id"], v) for g in td["graphs"] for v in [g["output"]] + list(g["inputs"]))
    for clip in during["channels_clips"]:
        for ch in clip["channels"]:
            if ch["id"] in known:
                continue
            created[ch["id"]] = ("channel", ch)
            view = views.get(ch["id"])
            if view is None:
                insufficient("aborted: created channel %r has no in-transaction graph view (its log and layers are "
                             "not inventoried)" % ch["name"])
            log = pv(view["log"])
            created[pv(log["log"])["id"]] = ("log", pv(log["log"]))
            for layer in log["layers"]:
                created[pv(layer["layer"])["id"]] = ("layer", pv(layer["layer"]))
    pairs = set((p["group"]["id"], p["control"]["id"]) for p in tb["control_groups"])
    groups_added = sorted(p["control"]["id"] for p in td["control_groups"]
                          if (p["group"]["id"], p["control"]["id"]) not in pairs)
    before_bones = dict((b["index"], b) for b in tb["bones"])
    scale_created = sorted(b["name"] for b in td["bones"]
                           if before_bones.get(b["index"], {}).get("scale", {}).get("s") == "absent" and
                           b["scale"].get("s") == "present")
    return created, groups_added, scale_created


def inv_aborted(a, b, fired):
    if not isinstance(fired, dict) or not require_keys(fired, FIRED, "fired", []):
        insufficient("aborted: SPEC must be the injector's complete fired record (%s)" % ", ".join(FIRED))
    if fired["event"] != "fired" or fired["injector"] != "v3" or fired["candidate_sha256"] != ACCEPTED_W1_SHA256:
        insufficient("aborted: the fired record is not a v3 firing on the accepted W1 candidate")
    baseline, during = fired["baseline"], fired["in_transaction"]
    names = [o.get("config_name") if isinstance(o, dict) else None for o in (a, baseline, during, b)]
    if names != [ORDINARY_CONFIG] * 4:
        insufficient("aborted: the configuration identity is missing or inconsistent (A, injector baseline, "
                     "in-transaction, B: %r); every observation must record %s" % (names, ORDINARY_CONFIG))
    sufficiency(baseline, "fired/baseline")
    sufficiency(during, "fired/in_transaction")
    for x, y, labels in ((a, baseline, ("A", "fired/baseline")), (baseline, during, ("fired/baseline",
                                                                                     "fired/in_transaction")),
                         (during, b, ("fired/in_transaction", "B"))):
        identities(x, y, False, labels)
    if differences(authored(a), authored(baseline)):
        insufficient("aborted: the injector's armed baseline is not the pre-Apply observation A")
    created, groups_added, scale_created = recompute_created(baseline, during)
    rows = fired["created"]
    if not isinstance(rows, list) or not all(isinstance(r, dict) and all(k in r for k in ("handle", "id", "type",
                                                                                         "name", "role"))
                                             for r in rows):
        insufficient("aborted: the recorded creation list is malformed")
    recorded = dict((r["id"], r) for r in rows)
    if not created:
        insufficient("aborted: no created element is evidenced by the in-transaction observation")
    if sorted(recorded) != sorted(created):
        insufficient("aborted: the recorded creation list does not reconcile with the observed creations "
                     "(missing %s, unexpected %s)" % (sorted(set(created) - set(recorded))[:8],
                                                     sorted(set(recorded) - set(created))[:8]))
    for i, (role, row) in sorted(created.items()):
        if recorded[i]["role"] != role or recorded[i]["handle"] != row["handle"]:
            insufficient("aborted: recorded %r contradicts its observed role or handle" % row["name"])
    recorded_groups = sorted(m[1] for m in fired["memberships_added"] if str(m[0]).startswith("control_group:"))
    recorded_scales = sorted(s["bone"] for s in fired["scale_attributes_created"])
    if recorded_groups != groups_added or recorded_scales != scale_created:
        insufficient("aborted: recorded memberships or scale attributes do not reconcile with the observations")
    reasons = []
    peer_diffs = differences(strip(baseline["peers"], False), strip(during["peers"], False))
    if fired["peer_changes"] != [] or peer_diffs:
        reasons.append("the same-model peer changed during the aborted transaction: %s" %
                       (fired["peer_changes"] or peer_diffs[:4]))
    attached = memberships(b)
    watched = dict((w["watched"]["id"], w["now"]) for w in b["watch"] if isinstance(w, dict) and "watched" in w)
    for i, (role, row) in sorted(created.items()):
        if i in attached:
            reasons.append("created %s %r is still attached after the abort" % (role, row["name"]))
        now = watched.get(i)
        if now is None:
            insufficient("aborted: no post-abort resolvability evidence for created %s %r" % (role, row["name"]))
        if now.get("s") != "gone":
            reasons.append("created %s %r is still resolvable after the abort" % (role, row["name"]))
    if reasons:
        raise Verdict(MISMATCH, reasons)
    inv_unchanged(a, b, fired)


def inv_undo(a, b, spec):
    expect_equal(a, b, what="state after Undo vs the pre-Apply baseline")
    u = undo_fields(b)
    if "redo_desc" not in spec:
        insufficient("undo: SPEC must name the owned redo_desc")
    if u["can_redo"] is not True or u["redo_desc"] != spec["redo_desc"]:
        raise Verdict(MISMATCH, ["after Undo the owned entry is not on the Redo stack: %r" % (u,)])
    if (u["can_undo"], u["undo_desc"]) != (undo_fields(a)["can_undo"], undo_fields(a)["undo_desc"]):
        raise Verdict(MISMATCH, ["after Undo the Undo stack top is not the baseline's: %r vs %r" %
                                 (u, undo_fields(a))])


def inv_redo(a, b, spec):
    expect_equal(a, b, what="state after Redo vs the applied state")
    u = undo_fields(b)
    if "undo_desc" not in spec:
        insufficient("redo: SPEC must name the owned undo_desc")
    if u["can_undo"] is not True or u["undo_desc"] != spec["undo_desc"]:
        raise Verdict(MISMATCH, ["after Redo the owned entry is not on the Undo stack: %r" % (u,)])


def admitted_static_play(obs, literal):
    """The M-06 admission shape from the observation's own evidence: mode 3, one layer, one key at time zero, the
    key equal to the native evaluation and the destination, a different stored source, and this channel the
    destination's sole writer with no channel writing the control."""
    row = obs["target"]["flex"].get(literal)
    if row is None or row["shape"] != "MONO":
        return ["%s: not a single-sided flex in the observation" % literal]
    side = row["mono"]
    problems = []
    if representation_of(side) != "STATIC_PLAY_ONE_KEY_ZERO":
        problems.append("%s: representation %r" % (literal, representation_of(side)))
    if pv(side["mode"]) != 3:
        problems.append("%s: mode %r" % (literal, pv(side["mode"])))
    if [w.get("id") for w in pv(side["destination_writers"]) or []] != [pv(side["channel"])["id"]]:
        problems.append("%s: the channel is not the destination's sole writer" % literal)
    if pv(side["control_writers"]) != []:
        problems.append("%s: a channel writes the control" % literal)
    return problems


def qualified_graph_problems(obs):
    """The deferred fixture's existing scale graph must be the qualified mode-3 graph: input and output mode 3, with
    the supported empty output log."""
    graphs = obs["target"]["graphs"]
    if not graphs:
        return ["the fixture has no existing scale graph to preserve"]
    problems = []
    for g in graphs:
        if pv(g["output"]["mode"]) != 3 or any(pv(i["mode"]) != 3 for i in g["inputs"]):
            problems.append("graph on %s is not the qualified mode-3 graph (output mode %r, input modes %r)" % (
                g["bone"], pv(g["output"]["mode"]), [pv(i["mode"]) for i in g["inputs"]]))
        else:
            problems.extend("graph on %s: %s" % (g["bone"], p) for p in output_representation_problems(g))
    return problems


# Reopened-state comparisons only (T10 Owner adjudication): native SFM save/reload moves transform-control orientation
# quaternion components by up to 2 float32 ULP (T10: the same 28 controls on both instances, none written by CPM).
# Every other reopened field, and every Apply/Undo/Redo/unchanged comparison, stays exact.
REOPEN_ORIENTATION_ULP = 2
REOPEN_ORIENTATION_PATH = re.compile(
    r"^/(?:target|peers/[^/]+)/transform_controls/[^/]+/(?:valueOrientation/v/\d+|orientationChannel_view/log/v/"
    r"(?:evaluated/v/\d+|layers/\d+/keys/v/\d+/1/\d+|layers/\d+/values/v/\d+/\d+))$")


def float32_ulp_distance(x, y):
    """Distance in float32 units in the last place; None unless both are finite, float32-exact numbers."""
    for v in (x, y):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v) or \
                struct.unpack("<f", struct.pack("<f", v))[0] != v:
            return None

    def ordered(v):
        i = struct.unpack("<i", struct.pack("<f", v))[0]
        return i if i >= 0 else -(i & 0x7fffffff)
    return abs(ordered(x) - ordered(y))


def value_at(tree, path):
    for part in path.strip("/").split("/"):
        tree = tree[int(part)] if isinstance(tree, list) else tree[part]
    return tree


REOPEN_ORIENTATION_FIELD = re.compile(
    r"^(/(?:target|peers/[^/]+)/transform_controls/[^/]+)/(?:valueOrientation|orientationChannel_view)(?:/|$)")


def native_portable(obs):
    """authored() without identities but with every list in native order (orientation pairing only)."""
    def drop(v):
        if isinstance(v, dict):
            return dict((k, drop(x)) for k, x in v.items() if k not in TRANSIENT and k not in ("handle", "id"))
        if isinstance(v, list):
            return [drop(x) for x in v]
        return v
    return {"target": drop(obs["target"]), "peers": drop(obs["peers"]), "channels_clips": drop(obs["channels_clips"])}


def reopened_differences(a, b):
    """(hard, tolerated): exact portable-state differences after reopen, except transform-control orientation
    quaternion components that are finite, float32-exact and within REOPEN_ORIENTATION_ULP (each one reported).
    Orientation components are paired in native (time) order: the identity-free comparison sorts lists, which can
    pair different keys once equal quaternions drift (D3: Elbow_r keys 0 and 4)."""
    pa, pb = authored(a, True), authored(b, True)
    hard, controls = [], set()
    for d in differences(pa, pb, limit=10 ** 7):
        path = d.split(": ", 1)[0]
        if REOPEN_ORIENTATION_PATH.match(path):
            controls.add(REOPEN_ORIENTATION_FIELD.match(path).group(1))
        else:
            hard.append(d)
    na, nb = native_portable(a), native_portable(b)
    tolerated = []
    for control in sorted(controls):
        for field in ("valueOrientation", "orientationChannel_view"):
            fp = control + "/" + field
            try:
                sa, sb = value_at(na, fp), value_at(nb, fp)
            except (KeyError, IndexError, TypeError, ValueError):
                hard.append("%s: orientation field unreadable for native pairing" % fp)
                continue
            for d in differences(sa, sb, fp, limit=10 ** 7):
                path = d.split(": ", 1)[0]
                ulp = None
                if REOPEN_ORIENTATION_PATH.match(path):
                    try:
                        ulp = float32_ulp_distance(value_at(na, path), value_at(nb, path))
                    except (KeyError, IndexError, TypeError, ValueError):
                        ulp = None
                if ulp is not None and ulp <= REOPEN_ORIENTATION_ULP:
                    tolerated.append((path, ulp))
                else:
                    hard.append(d)
    return hard, tolerated


def inv_reopened(a, b, spec):
    # Windows paths compare case-insensitively: native SFM reports document paths in lower case (T10, G3).
    if spec.get("document_path") and ntpath.normcase(pv(b["context_begin"]["document_path"]) or u"") != \
            ntpath.normcase(spec["document_path"]):
        insufficient("reopened: B is not the declared reopened copy")
    hard, tolerated = reopened_differences(a, b)
    if hard:
        raise Verdict(MISMATCH, ["portable state after reopen differs: %s" % d for d in hard[:40]])
    problems = [p for lit in spec.get("static_play") or [] for p in admitted_static_play(b, lit)]
    if spec.get("static_play"):
        problems.extend(qualified_graph_problems(b))
    if problems:
        raise Verdict(MISMATCH, ["after reopen: " + p for p in problems])
    if not tolerated:
        return []
    return (["tolerated %d orientation-quaternion component differences after reopen (SFM save/reload float32 "
             "rounding): maximum %d ULP (limit %d)" % (len(tolerated), max(u for _, u in tolerated),
                                                       REOPEN_ORIENTATION_ULP)] +
            ["tolerated %s: %d ULP" % (p, u) for p, u in tolerated])


def inv_prepared(a, b, spec):
    if "literal" not in spec or "stored" not in spec:
        insufficient("prepared: SPEC must declare literal and stored")
    if a["config_name"] != DEFERRED_CONFIG or b["config_name"] != DEFERRED_CONFIG:
        insufficient("prepared: both observations must be taken with the staged deferred configuration (%r, %r)" %
                     (a["config_name"], b["config_name"]))
    lit = spec["literal"]
    pa, pb = authored(a), authored(b)
    ra, rb = pa["target"]["flex"].get(lit), pb["target"]["flex"].get(lit)
    if ra is None or rb is None or ra["shape"] != "MONO" or rb["shape"] != "MONO":
        insufficient("prepared: %s must be a single-sided flex observed in both" % lit)
    reasons = []
    if representation_of(a["target"]["flex"][lit]["mono"]) != "ONE_KEY_ZERO":
        reasons.append("%s before preparation is not ONE_KEY_ZERO" % lit)
    if pv(rb["mono"]["stored"]) != spec["stored"] or pv(ra["mono"]["stored"]) == spec["stored"]:
        reasons.append("%s: stored %r -> %r, declared %r" % (lit, pv(ra["mono"]["stored"]),
                                                             pv(rb["mono"]["stored"]), spec["stored"]))
    for side in (ra["mono"], rb["mono"]):
        side["stored"] = side["representation"] = DECLARED
    reasons.extend("undeclared change: %s" % d for d in differences(pa, pb)[:40])
    reasons.extend(admitted_static_play(b, lit))
    reasons.extend(qualified_graph_problems(a))
    if reasons:
        raise Verdict(MISMATCH, reasons)


def control_backed_bones(obs):
    """(bones, notes): the bones a preset must cover, by index, and the reported exclusions. CPM's bone contract is
    control-backed (T01 adjudication): a bone is excluded only when the observation independently shows that no
    transform control writes its transform, its scale is absent and it has no scale writer. An unreadable control
    target is insufficient evidence, never an exclusion."""
    controlled = set()
    for cname, rec in sorted(obs["target"]["transform_controls"].items()):
        targets = []
        for view in ("positionChannel_view", "orientationChannel_view"):
            to = (rec.get(view) or {}).get("to")
            if isinstance(to, dict) and to.get("s") == "present" and isinstance(to.get("v"), dict):
                targets.append(to["v"]["id"])
        if not targets:
            insufficient("transform control %s: no readable transform target" % cname)
        controlled.update(targets)
    bones, notes = {}, []
    for b in obs["target"]["bones"]:
        t = b["transform"]
        tid = t["v"]["id"] if t.get("s") == "present" and isinstance(t.get("v"), dict) else None
        if tid is not None and tid not in controlled and b["scale"]["s"] == "absent" and b["scale_writers"] == []:
            notes.append("excluded bone %d %s: no transform control, scale absent, no scale writer"
                         % (b["index"], b["name"]))
        else:
            bones[b["index"]] = b
    return bones, notes


def inv_preset(obs, preset, spec):
    reasons = []
    bones, notes = control_backed_bones(obs)
    rows = preset.get("bone_scales")
    if not isinstance(rows, list):
        raise Verdict(MISMATCH, ["preset has no bone_scales list"])
    seen = {}
    for r in rows:
        seen.setdefault(r.get("bone_index"), []).append(r)
    if sorted(seen) != sorted(bones) or any(len(v) != 1 for v in seen.values()):
        reasons.append("preset bone coverage is not exactly the control-backed bone map (%d rows, %d bones)" %
                       (len(rows), len(bones)))
    for idx, b in sorted(bones.items()):
        r = (seen.get(idx) or [None])[0]
        if r is None:
            continue
        if r.get("bone_name") != b["name"]:
            reasons.append("bone %d: preset name %r, observed %r" % (idx, r.get("bone_name"), b["name"]))
        physical = pv(b["scale"]) if b["scale"]["s"] == "present" else 1.0
        if isinstance(physical, list):
            physical = physical[0] if len(set(physical)) == 1 else physical
        if r.get("value") != physical:
            reasons.append("bone %s: preset %r is not the full-precision effective %r" % (b["name"], r.get("value"),
                                                                                         physical))
    values = preset.get("values") or {}
    for lit, row in sorted(obs["target"]["flex"].items()):
        got = values.get("flex." + lit)
        if got is None:
            reasons.append("flex %s missing from the preset" % lit)
            continue
        for side in (("mono",) if row["shape"] == "MONO" else ("left", "right")):
            want, problem = effective_value(row[side])
            if problem:
                reasons.append("flex %s/%s: %s" % (lit, side, problem))
            elif got.get(side) != want:
                reasons.append("flex %s/%s: preset %r is not the full-precision effective %r" %
                               (lit, side, got.get(side), want))
    if reasons:
        raise Verdict(MISMATCH, reasons)
    return notes


def compare(invariant, a, b, spec=None):
    spec = spec or {}
    try:
        if invariant not in INVARIANTS:
            insufficient("unknown invariant %r" % invariant)
        sufficiency(a, "A")
        if invariant == "preset":
            return PASS, inv_preset(a, b, spec)
        sufficiency(b, "B")
        identities(a, b, portable=invariant == "reopened")
        notes = {"unchanged": inv_unchanged, "apply": inv_apply, "aborted": inv_aborted, "undo": inv_undo,
                 "redo": inv_redo, "reopened": inv_reopened, "prepared": inv_prepared}[invariant](a, b, spec)
        return PASS, (notes or []) if invariant == "reopened" else []
    except Verdict as v:
        return v.verdict, v.reasons
    except (KeyError, TypeError, IndexError, AttributeError, ValueError) as exc:
        return INSUFFICIENT, ["malformed evidence: %r" % (exc,)]


def main(argv):
    if len(argv) not in (4, 5):
        print(__doc__)
        return 2
    spec = load(argv[4]) if len(argv) == 5 else {}
    verdict, reasons = compare(argv[1], load(argv[2]), load(argv[3]), spec)
    print("INVARIANT: %s" % argv[1])
    print("VERDICT: %s" % verdict)
    for r in (reasons if verdict == PASS else reasons[:60]):
        print("  " + r)
    return EXIT[verdict]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
