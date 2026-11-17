# -*- coding: ascii -*-
"""F-01 OT1: the observer's hooks and controlled failure on SFM's Python 2.7.5 (also runs on 3.10), against a fake CPM
module (the five hooked functions and prod_bs_snapshot as plain functions). The pinned Q1 observer is loaded for real.

- W: each wrapper calls the original with the same arguments, returns its result unchanged, re-raises its exception
  unchanged (type, message and the original's innermost frame), records its event; install is idempotent; uninstall
  restores the exact originals and disarms.
- J: the controlled failure fires at most once, only when armed, only after CPM's write of the armed bone returned
  normally (never when that write raised), and raises the pinned text from inside the wrapper.
- P: the read-only BASE preflight runs the candidate's real prod_bs_expression_channels (extracted verbatim from the
  app source, with its strict-read helpers) on a fake channels track: valid, shared, ambiguous and unreadable graphs,
  a refused binding, a missing bone, a changed endpoint, operators-array membership, a recorded state change; no
  write, Operate or key change; it runs before the hooks are installed.
- D: Astra's DC1 direct-reference condition with the DC2 correction (the IDataModel iterator primitives on a fake
  vs.g_pDataModel over the scene's referring attributes, configurable sentinel, fault injection; no vsUtils):
  traversal to the sentinel, an empty enumeration, a false-valued valid token, a fourth reference, an attribute-less
  token, an exception after three rows, a repeated token, a class entry replaced or created during traversal, vsUtils
  loaded during traversal, vsUtils initially absent or already loaded; the expected three live relationships pass; an off-track reader, an unexpected
  non-channel reference, a missing or duplicated reference, an unreadable owner or attribute name, an enumeration that
  raises part way, a wrong-instance or replaced element, and an unavailable vsUtils fail; operators-array membership
  is one of the three expected relationships; ARM arms only after a passing, unchanged preflight.
- L: the Q1 observer is used only at its pinned SHA-256; the observer's source makes no scene write, refresh, event
  pumping, Undo or Operate call of its own, and its only file write is the exclusive-create capture.
They show nothing about SFM itself.

Usage: <SFM python 2.7.5> -E -B test_ot1_observer.py   (or python -I test_ot1_observer.py)
"""
from __future__ import print_function

import ast
import os
import shutil
import sys
import tempfile
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(KIT))
OBSERVER = os.path.join(KIT, "observer", "F01_OT1_Observe.py")
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name))
    if not ok and value is not None:
        print("      value: %r" % (value,))


def load_observer():
    g = {"__name__": "ot1_observer_under_test"}
    with open(OBSERVER, "rb") as f:
        exec(compile(f.read(), OBSERVER, "exec"), g)
    return g


class Boom(ValueError):
    pass


def fake_cpm(calls):
    cpm = types.ModuleType("fake_cpm")
    state = {"physical": {"bip_head": 1.13, "bip_tail00": 0.8}, "result": {"bip_head": 1.13, "bip_tail00": 0.8},
             "raise": set()}
    cpm.state = state

    def prod_apply(identity, record, scope=None, operation_context=None):
        calls.append(("prod_apply", identity, record, scope, operation_context))
        if "apply" in state["raise"]:
            raise Boom("apply failed")
        for item in record.get("_items", []):
            cpm.prod_bs_write_existing_scale(item)
        cpm.same_time_refresh(0.2083, "PROD_APPLY")
        return {"phase": "verification-pending"}

    def prod_bs_write_existing_scale(item):
        calls.append(("write", item["bone_name"]))
        if item["bone_name"] in state["raise"]:
            raise Boom("write failed %s" % item["bone_name"])
        state["result"][item["bone_name"]] = item["desired_physical"]
        return "write-result-%s" % item["bone_name"]

    def same_time_refresh(head_time, label):
        calls.append(("refresh", head_time, label))
        for bone in state["result"]:
            state["physical"][bone] = state["result"][bone]
        return "refreshed"

    def prod_bs_index_verify_saved(record, snapshot):
        calls.append(("verify", record.get("name")))
        return True

    def prod_verify_apply_abort_baseline(*args, **kwargs):
        calls.append(("abort-verify", args, kwargs))
        return True

    def prod_bs_snapshot(binding):
        bone = binding["identity"]["bone_name"]
        return {"source": 0.1, "key_value": 0.1, "key_count": 1, "expr_input": 0.1,
                "expr_result": state["result"][bone], "physical_scale": state["physical"][bone], "output_mode": 3,
                "expression_id": ["E", bone], "unlisted": "not recorded"}

    def prod_instance_token(context):
        return None

    for fn in (prod_apply, prod_bs_write_existing_scale, same_time_refresh, prod_bs_index_verify_saved,
               prod_verify_apply_abort_baseline, prod_bs_snapshot, prod_instance_token):
        setattr(cpm, fn.__name__, fn)
    return cpm


def item(bone, desired):
    return {"bone_name": bone, "desired_native": desired / 10.0, "desired_physical": desired,
            "binding": {"identity": {"bone_name": bone}, "static_output_mode": 3}}


def kinds(st):
    return [e["kind"] for e in st["events"]]


def section_wrappers(o, q1):
    calls = []
    cpm = fake_cpm(calls)
    originals = dict((n, getattr(cpm, n)) for n in o["OT1_HOOKED"])
    st = o["ot1_install"](cpm, q1)
    check("W1 install wraps exactly the five functions and keeps the originals",
          all(getattr(cpm, n) is not originals[n] and getattr(cpm, n).ot1_original is originals[n]
              for n in o["OT1_HOOKED"]) and st["originals"] == originals)
    check("W1 a second install is a no-op", o["ot1_install"](cpm, q1) is st
          and all(getattr(cpm, n).ot1_original is originals[n] for n in o["OT1_HOOKED"]))

    record = {"name": u"Body", "kind": u"body", "_items": [item(u"bip_head", 1.33), item(u"bip_tail00", 1.0)]}
    result = cpm.prod_apply({"model": u"m"}, record, scope="S", operation_context="CTX")
    check("W2 prod_apply: same arguments, result unchanged",
          result == {"phase": "verification-pending"} and calls[0] == ("prod_apply", {"model": u"m"}, record, "S", "CTX"))
    check("W2 events in CPM order: apply-begin, two scale writes, refresh, apply-returned",
          kinds(st) == ["apply-begin", "scale-write", "scale-write", "refresh-after", "apply-returned"], kinds(st))
    w = [e for e in st["events"] if e["kind"] == "scale-write"]
    check("W3 scale write: before read precedes CPM's write, after read follows it (CPM's own snapshot fields only)",
          w[0]["bone"] == u"bip_head" and w[0]["before"]["expr_result"] == 1.13 and w[0]["after"]["expr_result"] == 1.33
          and w[0]["after"]["physical_scale"] == 1.13 and "unlisted" not in w[0]["after"]
          and w[0]["desired_physical"] == 1.33 and w[0]["static_output_mode"] == 3, w[0])
    r = [e for e in st["events"] if e["kind"] == "refresh-after"][0]
    check("W4 refresh: read only after CPM's refresh, only the scales this operation wrote",
          r["label"] == u"PROD_APPLY" and [x["bone"] for x in r["scales"]] == [u"bip_head", u"bip_tail00"]
          and r["scales"][0]["after"]["physical_scale"] == 1.33, r)
    check("W5 deferred verify and abort verify: result unchanged and recorded",
          cpm.prod_bs_index_verify_saved({"name": u"Body"}, {}) is True
          and cpm.prod_verify_apply_abort_baseline(1, k=2) is True
          and [e["kind"] for e in st["events"]][-2:] == ["deferred-verify", "abort-verify"]
          and st["events"][-1]["result"] is True and calls[-1] == ("abort-verify", (1,), {"k": 2}))

    cpm.state["raise"].add("apply")
    try:
        cpm.prod_apply({"model": u"m"}, {"name": u"Body", "kind": u"body"})
        got = None
    except Exception:
        got = sys.exc_info()
    inner = traceback.extract_tb(got[2])[-1] if got else None
    check("W6 an exception is re-raised unchanged (type, message, the original's innermost frame)",
          got is not None and got[0] is Boom and str(got[1]) == "apply failed" and inner[2] == "prod_apply"
          and st["events"][-1]["kind"] == "apply-raised", inner)
    cpm.state["raise"].discard("apply")
    check("W7 uninstall restores the exact originals", o["ot1_uninstall"](cpm) is True
          and all(getattr(cpm, n) is originals[n] for n in o["OT1_HOOKED"]) and o["ot1_state"](cpm) is None)


def section_injection(o, q1):
    calls = []
    cpm = fake_cpm(calls)
    st = o["ot1_install"](cpm, q1)
    record = {"name": u"Body", "kind": u"body", "_items": [item(u"bip_head", 1.33), item(u"bip_tail00", 1.0)]}
    cpm.prod_apply({}, record)
    check("J1 not armed: nothing injected", "injected-failure" not in kinds(st) and st["fired"] == 0)
    del st["events"][:]
    st["armed"] = True
    try:
        cpm.prod_apply({}, record)
        got = None
    except Exception as exc:
        got = exc
    check("J2 armed: CPM's tail write ran and returned, then the pinned failure is raised from the wrapper",
          isinstance(got, RuntimeError) and str(got) == o["OT1_FAIL_TEXT"]
          and ("write", u"bip_tail00") in calls[-3:] and cpm.state["result"][u"bip_tail00"] == 1.0, (got, calls[-3:]))
    check("J2 events: head write, tail write, injected failure, apply-raised (no refresh: the failure precedes it)",
          kinds(st) == ["apply-begin", "scale-write", "scale-write", "injected-failure", "apply-raised"], kinds(st))
    check("J3 fired once and disarmed", st["fired"] == 1 and st["armed"] is False)
    cpm.prod_apply({}, record)
    check("J3 a later Apply is not injected", st["fired"] == 1 and kinds(st)[-1] == "apply-returned")

    st["armed"], st["fired"] = True, 0
    cpm.state["raise"].add(u"bip_tail00")
    try:
        cpm.prod_apply({}, record)
        got = None
    except Exception as exc:
        got = exc
    check("J4 when CPM's own write raises, its exception propagates and nothing is injected",
          isinstance(got, Boom) and st["fired"] == 0 and st["armed"] is True
          and "scale-write-raised" in kinds(st), (got, kinds(st)[-4:]))
    o["ot1_uninstall"](cpm)
    check("J5 uninstall disarms", st["armed"] is False)


def section_static(o):
    tmp = tempfile.mkdtemp(prefix="ot1_obs_")
    try:
        target = os.path.join(tmp, "real_sfm_qualification", "f01_q1_ps2_diagnostic", "observer")
        os.makedirs(target)
        with open(os.path.join(REPO, "real_sfm_qualification", "f01_q1_ps2_diagnostic", "observer",
                               "F01_Q1_Observe.py"), "rb") as f:
            raw = f.read()
        with open(os.path.join(target, "F01_Q1_Observe.py"), "wb") as f:
            f.write(raw + b"\n# changed\n")
        try:
            o["ot1_q1"](tmp)
            refused = False
        except RuntimeError:
            refused = True
        check("L1 a changed Q1 observer is refused", refused)
    finally:
        shutil.rmtree(tmp)
    with open(OBSERVER, "rb") as f:
        tree = ast.parse(f.read())
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            called.add(fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None))
    forbidden = set(["SetValue", "SetKeyValue", "Operate", "StartUndo", "FinishUndo", "AbortUndoableOperation",
                     "Undo", "Redo", "ProcessEvents", "SetHeadTimeInSeconds", "same_time_refresh", "singleShot",
                     "remove", "unlink", "rename", "rmtree", "makedirs"])
    check("L2 the observer makes no scene write, refresh, pumping, Undo, Operate or file removal of its own",
          not called & forbidden, sorted(called & forbidden))
    with open(OBSERVER, "rb") as f:
        src = f.read().decode("ascii")
    import re
    builtin_opens = re.findall(r"(?<![\w.])open\(([^)]*)\)", src)
    check("L3 its only file write is the exclusive-create capture (one os.open with O_EXCL; builtin open read-only)",
          src.count("os.open(") == 1 and "O_EXCL" in src and builtin_opens == ['path, "rb"'],
          builtin_opens)


# ---------------------------------------------------------------------------
# P: the read-only BASE preflight, with the candidate's real scan (extracted verbatim from the app source)
# ---------------------------------------------------------------------------

REAL_NAMES = ["u", "native_attr_name", "name", "typ", "handle", "ptr", "dme_id", "same_dme", "get_attr", "attr_value",
              "prod_flex_strict_read", "prod_flex_strict_list", "prod_instance_strict_members",
              "prod_instance_strict_text", "prod_bs_expression_channels"]
TOUCHED = []


class FAttr(object):
    def __init__(self, value, unreadable=False):
        self.value, self.unreadable = value, unreadable

    def GetValue(self):
        if self.unreadable:
            raise RuntimeError("unreadable value")
        return self.value

    def SetValue(self, value):
        TOUCHED.append(("SetValue", value))
        self.value = value


class FEl(object):
    _next = [5000]

    def __init__(self, kind, label, **attrs):
        FEl._next[0] += 1
        self.kind, self.label, self.h = kind, label, FEl._next[0]
        self.this = self.h * 8
        self.attrs = dict((k, FAttr(v)) for k, v in attrs.items())
        self.broken_type = False

    def GetTypeString(self):
        if self.broken_type:
            raise RuntimeError("unreadable type")
        return self.kind

    def GetName(self):
        return self.label

    def GetHandle(self):
        return self.h

    def GetAttribute(self, attr_name):
        if isinstance(attr_name, bytes):
            attr_name = attr_name.decode("ascii")
        return self.attrs.get(attr_name)

    def HasAttribute(self, attr_name):
        if isinstance(attr_name, bytes):
            attr_name = attr_name.decode("ascii")
        return attr_name in self.attrs

    def Operate(self):
        TOUCHED.append(("Operate", self.label))

    def SetKeyValue(self, index, value):
        TOUCHED.append(("SetKeyValue", self.label))


class FShot(FEl):
    def __init__(self, track):
        FEl.__init__(self, u"DmeFilmClip", u"shot15", animationSets=[])
        self.track = track

    def FindTrackGroup(self, group):
        return self if group == "channelTrackGroup" else None

    def FindTrack(self, track):
        return self.track if track == "animSetEditorChannels" else None


def fgraph(bone):
    transform = FEl(u"DmeTransform", u"bone (%s)" % bone, scale=1.13)
    control = FEl(u"DmElement", bone + u"_scale", value=0.113)
    expression = FEl(u"DmeExpressionOperator", bone + u"_scale_rescale", expr=u"lerp(value, lo, hi)", lo=0.0, hi=10.0,
                     value=0.113, result=1.13)
    inp = FEl(u"DmeChannel", bone + u"_scale", fromElement=control, fromAttribute=u"value", toElement=expression,
              toAttribute=u"value", mode=3)
    out = FEl(u"DmeChannel", u"scaled_%s_scale_channel" % bone, fromElement=expression, fromAttribute=u"result",
              toElement=transform, toAttribute=u"scale", mode=3)
    return {"binding": {"expression": expression, "output": out, "input_channel": inp, "transform": transform,
                        "control": control, "static_output_mode": 3}, "channels": [inp, out]}


def fscene():
    graphs = dict((b, fgraph(b)) for b in (u"bip_head", u"bip_tail00"))
    peer = fgraph(u"bip_head")
    clip = FEl(u"DmeChannelsClip", u"Krystal", channels=graphs[u"bip_head"]["channels"] + graphs[u"bip_tail00"]["channels"])
    peer_clip = FEl(u"DmeChannelsClip", u"krystal20201", channels=list(peer["channels"]))
    film = FEl(u"DmeFilmClip", u"not a channels clip")
    track = FEl(u"DmeTrack", u"animSetEditorChannels", children=[clip, peer_clip, film])
    shot = FShot(track)
    target = FEl(u"DmeAnimationSet", u"Krystal", operators=[graphs[b]["binding"]["expression"] for b in graphs])
    peer_set = FEl(u"DmeAnimationSet", u"krystal20201", operators=[peer["binding"]["expression"]])
    shot.attrs["animationSets"] = FAttr([target, peer_set])
    rows = {}
    refs = {}
    for g, animset in [(graphs[b], target) for b in graphs] + [(peer, peer_set)]:
        g["binding"]["shot"] = shot
        g["binding"]["animset"] = animset
        refs[g["binding"]["expression"].h] = [FRef(animset, "operators"), FRef(g["binding"]["input_channel"], "toElement"),
                                              FRef(g["binding"]["output"], "fromElement")]
    for i, bone in enumerate(sorted(graphs)):
        rows[(i, bone)] = {"bone_name": bone, "classification": u"CHANNEL_DRIVEN_SCALE", "_binding": graphs[bone]["binding"]}
    return {"graphs": graphs, "peer": peer, "clip": clip, "peer_clip": peer_clip, "track": track, "shot": shot,
            "rows": rows, "target_set": target, "peer_set": peer_set, "refs": refs, "raise_after": None,
            "dm": {"sentinel": 0, "first_token": 1, "raise_on_next": None, "repeat_at": None, "none_attr_at": None,
                   "on_next": None}}


class FRef(object):
    """A referring attribute as GetAttributeFromIterator returns it: GetOwner() and GetName()."""
    def __init__(self, owner, attr_name, bad_owner=False, bad_name=False):
        self.owner, self.attr_name, self.bad_owner, self.bad_name = owner, attr_name, bad_owner, bad_name

    def GetOwner(self):
        if self.bad_owner:
            raise RuntimeError("unreadable owner")
        return self.owner

    def GetName(self):
        if self.bad_name:
            raise RuntimeError("unreadable name")
        return self.attr_name


class FClass(object):
    """Stand-ins for vs.CDmElement / Vector / QAngle / Quaternion: their own __dict__ entries are what DC2 snapshots."""


def fake_vs(scene):
    """A fake vs module: g_pDataModel implements Astra's three iterator primitives over scene["refs"], with a
    configurable sentinel and token numbering, and fault injection; the five DC2 classes."""
    cfg = scene["dm"]
    vsmod = types.ModuleType("vs")
    vsmod.DMATTRIBUTE_REFERENCE_ITERATOR_INVALID = cfg["sentinel"]
    for cls_name in ("CDmElement", "Vector", "QAngle", "Quaternion"):
        setattr(vsmod, cls_name, type(cls_name, (FClass,), {}))
    vsmod.CDmElement.__hash__ = lambda self: 1   # an existing entry (as vsUtils would leave), kept by identity
    tokens = {}
    calls = {"first": 0, "get": 0, "next": 0}

    class DM(object):
        def FirstAttributeReferencingElement(self, handle):
            calls["first"] += 1
            rows = scene["refs"].get(handle, [])
            if not rows:
                return cfg["sentinel"]
            token = cfg["first_token"] + handle * 100
            tokens[token] = (handle, 0)
            return token

        def GetAttributeFromIterator(self, token):
            calls["get"] += 1
            handle, i = tokens[token]
            if scene["raise_after"] == (handle, i):
                raise RuntimeError("iterator failed")
            if cfg["none_attr_at"] == (handle, i):
                return None
            return scene["refs"][handle][i]

        def NextAttributeReferencingElement(self, token):
            calls["next"] += 1
            handle, i = tokens[token]
            if cfg["on_next"] is not None:
                cfg["on_next"](vsmod, handle)
            if cfg["raise_on_next"] == (handle, i):
                raise RuntimeError("Next failed")
            if cfg["repeat_at"] == (handle, i):
                return token
            if i + 1 >= len(scene["refs"][handle]):
                return cfg["sentinel"]
            nxt = token + 1
            tokens[nxt] = (handle, i + 1)
            return nxt
    vsmod.g_pDataModel = DM()
    vsmod.calls = calls
    return vsmod


def preflight_cpm(scene):
    sys.path.insert(0, os.path.join(REPO, "cpm", "convergence", "tests"))
    import test_cpm_app_canonical_route as route
    app = route.AppSource(route.APP_PATH)
    ns = {}
    if sys.version_info[0] > 2:
        ns["unicode"], ns["long"] = str, int
    for n in REAL_NAMES:
        route._run_source(app.top_text(n), "app:%s" % n, ns)
    cpm = types.ModuleType("fake_cpm_preflight")
    for n in REAL_NAMES:
        setattr(cpm, n, ns[n])

    def binding(snapshot, row):
        if row.get("_raise"):
            raise RuntimeError("This bone scale is outside the qualified generic topology.")
        return row["_binding"]
    cpm.prod_bs_index_snapshot = lambda identity, instance_context=None: {"bone_index": dict(scene["rows"])}
    cpm.prod_bs_index_binding = binding
    cpm.prod_instance_kw = lambda token: {"instance_context": token} if token is not None else {}
    cpm.prod_instance_token = lambda token: token
    return cpm, app


def run_preflight(o, q1, scene, probe=None, vsmod="fake"):
    del TOUCHED[:]
    cpm, _ = preflight_cpm(scene)
    states = iter(probe or [{"undo": "u", "head_seconds": 0.2083}, {"undo": "u", "head_seconds": 0.2083}])
    scene["vs"] = fake_vs(scene) if vsmod == "fake" else vsmod
    return o["ot1_guarded_preflight"](cpm, q1, {"model": u"m"}, {"kind": u"token"}, lambda: next(states),
                                      scene["vs"])


def section_preflight(o, q1):
    scene = fscene()
    r = run_preflight(o, q1, scene)
    head = r["bones"][u"bip_head"]
    check("P1 valid graphs: the candidate's precondition holds for both scales (one reader, one writer each)",
          r["would_pass"] is True and all(r["bones"][b]["would_pass"] for b in (u"bip_head", u"bip_tail00"))
          and head["candidate_scan"]["readers"] == 1 and head["candidate_scan"]["writers"] == 1, r)
    check("P1 enumeration agrees (2 channels clips read, 6 channels; the film clip skipped; nothing unreadable)",
          head["enumeration"]["clips"] == 2 and head["enumeration"]["channels"] == 6
          and len(head["enumeration"]["readers"]) == 1 and len(head["enumeration"]["writers"]) == 1
          and head["enumeration"]["unreadable"] == [] and head["enumeration"]["readers"][0]["attribute"] == u"result",
          head["enumeration"])
    check("P1 identities, expression and endpoint checks, instance and operator-list membership reported",
          head["expression_ok"] and head["endpoints_ok"] and head["static_output_mode"] == 3
          and head["identities"]["expression"][0] == u"DmeExpressionOperator"
          and r["instance"] == {"kind": u"token"} and head["operator_lists"] == [u"Krystal"], head)
    check("P1 read only: no write, Operate or key change; scene state unchanged before/after",
          TOUCHED == [] and r["side_effects"]["unchanged"] is True, (TOUCHED, r["side_effects"]))

    def variant(mutate):
        s = fscene()
        mutate(s)
        return run_preflight(o, q1, s)

    def shared(s):
        g = s["graphs"][u"bip_head"]["binding"]
        s["peer_clip"].attrs["channels"].value.append(FEl(
            u"DmeChannel", u"foreign_reader", fromElement=g["expression"], fromAttribute=u"result",
            toElement=FEl(u"DmeTransform", u"other"), toAttribute=u"scale"))
    r = variant(shared)
    head, tail = r["bones"][u"bip_head"], r["bones"][u"bip_tail00"]
    check("P2 shared: a second reader in another set's clip -> would_pass False, two readers listed with their clips",
          r["would_pass"] is False and head["would_pass"] is False and head["candidate_scan"]["readers"] == 2
          and sorted(x["clip"] for x in head["enumeration"]["readers"]) == [u"Krystal", u"krystal20201"]
          and tail["would_pass"] is True, head)

    def ambiguous(s):
        g = s["graphs"][u"bip_tail00"]["binding"]
        s["clip"].attrs["channels"].value.append(FEl(
            u"DmeChannel", u"second_writer", fromElement=FEl(u"DmElement", u"x", value=0.5), fromAttribute=u"value",
            toElement=g["expression"], toAttribute=u"value"))
    r = variant(ambiguous)
    tail = r["bones"][u"bip_tail00"]
    check("P3 ambiguous: two writers into the tail expression -> would_pass False, two writers listed",
          r["would_pass"] is False and tail["candidate_scan"]["writers"] == 2
          and len(tail["enumeration"]["writers"]) == 2 and r["bones"][u"bip_head"]["would_pass"] is True, tail)

    def unreadable_endpoint(s):
        bad = FEl(u"DmeChannel", u"broken", toElement=FEl(u"DmeTransform", u"y"), toAttribute=u"scale")
        bad.attrs["fromElement"] = FAttr(None, unreadable=True)
        s["peer_clip"].attrs["channels"].value.append(bad)
    r = variant(unreadable_endpoint)
    head = r["bones"][u"bip_head"]
    check("P4 an unreadable endpoint in an unrelated clip: the candidate's scan refuses; the enumeration names it and "
          "still finds the one reader and writer -> would_pass False",
          r["would_pass"] is False and u"unreadable" in head["candidate_scan"]["error"]
          and head["enumeration"]["unreadable"] == [{"what": "endpoint", "clip": u"krystal20201", "channel": u"broken",
                                                    "position": 2, "attribute": "fromElement"}]
          and len(head["enumeration"]["readers"]) == 1 and len(head["enumeration"]["writers"]) == 1, head)

    def unreadable_clip(s):
        s["track"].attrs["children"].value[2].broken_type = True
        s["peer_clip"].attrs["channels"] = FAttr(None, unreadable=True)
    r = variant(unreadable_clip)
    kinds = sorted(x["what"] for x in r["bones"][u"bip_head"]["enumeration"]["unreadable"])
    check("P5 an unreadable clip type and an unreadable channel list are both listed -> would_pass False",
          r["would_pass"] is False and kinds == ["clip channels", "clip type"], kinds)

    def no_binding(s):
        for row in s["rows"].values():
            if row["bone_name"] == u"bip_tail00":
                row["_raise"] = True
    r = variant(no_binding)
    check("P6 a graph CPM's own binding refuses -> its error recorded, would_pass False",
          r["would_pass"] is False and u"outside the qualified" in r["bones"][u"bip_tail00"]["error"])
    r = variant(lambda s: s["rows"].pop((0, u"bip_head")))
    check("P7 a missing bone -> error recorded, would_pass False",
          r["would_pass"] is False and u"not found" in r["bones"][u"bip_head"]["error"])

    def endpoint_changed(s):
        s["graphs"][u"bip_head"]["binding"]["output"].attrs["fromAttribute"] = FAttr(u"value")
    r = variant(endpoint_changed)
    check("P8 an output reading another attribute -> endpoints_ok False, would_pass False",
          r["would_pass"] is False and r["bones"][u"bip_head"]["endpoints_ok"] is False)

    def listed_twice(s):
        s["peer_set"].attrs["operators"].value.append(s["graphs"][u"bip_head"]["binding"]["expression"])
    r = variant(listed_twice)
    check("P9 an expression listed in two sets' operators arrays is reported (operator-list membership)",
          r["bones"][u"bip_head"]["operator_lists"] == [u"Krystal", u"krystal20201"])
    r = run_preflight(o, q1, fscene(), probe=[{"undo": "a", "head_seconds": 0.2083},
                                               {"undo": "b", "head_seconds": 0.2083}])
    check("P10 a state change across the preflight is recorded as side effects (unchanged False)",
          r["side_effects"]["unchanged"] is False)

    with open(OBSERVER, "rb") as f:
        src = f.read().decode("ascii")
    capture = src[src.index("def ot1_capture"):]
    check("P11 BASE runs the preflight before installing the hooks",
          capture.index("ot1_guarded_preflight(") < capture.index("ot1_install(cpm, q1)"))
    _, app = preflight_cpm(fscene())
    check("P12 the preflight uses the candidate's committed scan text (extracted verbatim here)",
          u"def prod_bs_expression_channels(binding):" in app.top_text("prod_bs_expression_channels"))


def section_direct_refs(o, q1):
    r = run_preflight(o, q1, fscene())
    for bone in (u"bip_head", u"bip_tail00"):
        d = r["bones"][bone]["direct_refs"]
        check("D1 %s: exactly the three live relationships (operators of A, input toElement, output fromElement), "
              "enumeration complete -> pass" % bone,
              d["pass"] is True and d["complete"] is True and d["error"] is None and d["terminated_at_sentinel"] is True
              and d["repeated_token"] is False and len(d["tokens"]) == 3 and d["class_entries"]["unchanged"] is True
              and d["vsutils_module"]["unchanged"] is True and
              sorted(x["role"] for x in d["references"]) == ["animset", "input_channel", "output"] and
              sorted(x["attribute"] for x in d["references"]) == ["fromElement", "operators", "toElement"] and
              all(isinstance(x.get("owner_handle"), int) for x in d["references"]), d)
    check("D1 the valid operator-list membership is one of the three (not an unexplained extra)",
          [x for x in r["bones"][u"bip_head"]["direct_refs"]["references"] if x["role"] == "animset"][0]["owner_name"]
          == u"Krystal" and r["would_pass"] is True)

    def variant(mutate):
        s = fscene()
        mutate(s)
        return run_preflight(o, q1, s)

    def head(s):
        return s["graphs"][u"bip_head"]["binding"]

    def off_track(s):  # a reader the channel-track scan cannot see (in no clip of the track)
        ch = FEl(u"DmeChannel", u"off_track", fromElement=head(s)["expression"], fromAttribute=u"result",
                 toElement=FEl(u"DmeTransform", u"z"), toAttribute=u"scale")
        s["refs"][head(s)["expression"].h].append(FRef(ch, "fromElement"))
    cases = [
        ("an off-track channel reader (channel-track scan still passes)", off_track, "unexpected"),
        ("an unexpected non-channel reference (a connection operator's input)",
         lambda s: s["refs"][head(s)["expression"].h].append(
             FRef(FEl(u"DmeConnectionOperator", u"conn"), "input")), "unexpected"),
        ("a missing reference (no operators listing)",
         lambda s: s["refs"][head(s)["expression"].h].pop(0), "count"),
        ("a duplicated reference (operators returned twice)",
         lambda s: s["refs"][head(s)["expression"].h].append(FRef(s["target_set"], "operators")), "count"),
        ("an unreadable owner", lambda s: setattr(s["refs"][head(s)["expression"].h][1], "bad_owner", True),
         "unreadable"),
        ("an unreadable attribute name", lambda s: setattr(s["refs"][head(s)["expression"].h][2], "bad_name", True),
         "unreadable"),
        ("an enumeration that raises part way (incomplete)", lambda s: s.__setitem__("raise_after", (head(s)["expression"].h, 2)),
         "incomplete"),
        ("the operators listing on the peer's set (wrong instance)",
         lambda s: s["refs"][head(s)["expression"].h].__setitem__(0, FRef(s["peer_set"], "operators")), "unexpected"),
        ("a replaced input channel (same name, another element)",
         lambda s: s["refs"][head(s)["expression"].h].__setitem__(
             1, FRef(FEl(u"DmeChannel", u"bip_head_scale"), "toElement")), "unexpected"),
        ("an empty enumeration (sentinel first)", lambda s: s["refs"].__setitem__(head(s)["expression"].h, []),
         "count"),
        ("a fourth reference after the expected three", lambda s: s["refs"][head(s)["expression"].h].append(
            FRef(FEl(u"DmElement", u"later"), "items")), "count"),
        ("an iterator returning no attribute", lambda s: s["dm"].__setitem__("none_attr_at", (head(s)["expression"].h, 1)),
         "unreadable"),
        ("an exception after three valid rows (NextAttributeReferencingElement)", lambda s: s["dm"].__setitem__(
            "raise_on_next", (head(s)["expression"].h, 2)), "incomplete"),
        ("a repeated iterator token", lambda s: s["dm"].__setitem__("repeat_at", (head(s)["expression"].h, 1)),
         "repeated"),
        ("a class method replaced during traversal (same name, new object)", lambda s: s["dm"].__setitem__(
            "on_next", lambda vsmod, h: h == head(s)["expression"].h and setattr(
                vsmod.CDmElement, "__hash__", lambda self: 1)), "classes"),
        ("an absent class entry created during traversal (Vector.__hash__)", lambda s: s["dm"].__setitem__(
            "on_next", lambda vsmod, h: h == head(s)["expression"].h and setattr(
                vsmod.Vector, "__hash__", lambda self: 2)), "classes"),
        ("vsUtils loaded during traversal", lambda s: s["dm"].__setitem__(
            "on_next", lambda vsmod, h: h == head(s)["expression"].h and sys.modules.setdefault(
                "vsUtils", types.ModuleType("vsUtils"))), "module"),
        ("the right owner under another attribute name",
         lambda s: s["refs"][head(s)["expression"].h].__setitem__(
             2, FRef(head(s)["output"], "toElement")), "unexpected"),
    ]
    for label, mutate, kind in cases:
        sys.modules.pop("vsUtils", None)
        r = variant(mutate)
        sys.modules.pop("vsUtils", None)
        d = r["bones"][u"bip_head"]["direct_refs"]
        why = {"unexpected": bool(d["unexpected"]), "count": d["matched"]["animset"] != 1 or
               len(d["references"]) != 3, "unreadable": bool(d["unreadable"]),
               "incomplete": d["complete"] is False and d["error"] is not None and not d["terminated_at_sentinel"],
               "repeated": d["repeated_token"] is True and d["complete"] is False,
               "classes": d["class_entries"]["unchanged"] is False, "module": d["vsutils_module"]["unchanged"] is False}
        check("D2 %s -> fails (%s); would_pass False; the tail is unaffected" % (label, kind),
              d["pass"] is False and why[kind] and r["bones"][u"bip_head"]["would_pass"] is False
              and r["would_pass"] is False and r["bones"][u"bip_tail00"]["would_pass"] is True, d)
    r = variant(off_track)
    check("D2 the off-track reader is invisible to the channel-track scan, so only DC1 catches it",
          r["bones"][u"bip_head"]["unique"] is True and r["bones"][u"bip_head"]["direct_refs"]["pass"] is False)
    sys.modules.pop("vsUtils", None)
    r = run_preflight(o, q1, fscene(), vsmod=None)
    check("D3 vs unavailable -> no references, would_pass False",
          r["would_pass"] is False and r["bones"][u"bip_head"]["direct_refs"]["error"] == "vs unavailable")

    s = fscene()
    s["dm"].update(sentinel=-1, first_token=0)
    s["refs"] = dict((h, rows) for h, rows in s["refs"].items())
    # token 0 + handle*100 is never falsy for real handles, so force a falsy first token for the head expression
    h = s["graphs"][u"bip_head"]["binding"]["expression"].h
    s["dm"]["first_token"] = -h * 100
    r = run_preflight(o, q1, s)
    d = r["bones"][u"bip_head"]["direct_refs"]
    check("D7 a false-valued valid first token (0, sentinel -1) is traversed, not treated as the end",
          d["tokens"][0] == "0" and d["pass"] is True and d["terminated_at_sentinel"] is True, d["tokens"])

    for preloaded in (False, True):
        sys.modules.pop("vsUtils", None)
        if preloaded:
            sys.modules["vsUtils"] = types.ModuleType("vsUtils")
        s = fscene()
        r = run_preflight(o, q1, s)
        d = r["bones"][u"bip_head"]["direct_refs"]
        check("D8 vsUtils %s: membership recorded unchanged and the observer imports nothing (pass)"
              % ("already loaded" if preloaded else "initially absent"),
              d["vsutils_module"] == {"before": preloaded, "after": preloaded, "unchanged": True} and d["pass"] is True
              and ("vsUtils" in sys.modules) is preloaded, d["vsutils_module"])
        sys.modules.pop("vsUtils", None)
    check("D8 the class entries are recorded with an explicit absent marker",
          d["class_entries"]["before"]["Vector.__hash__"] == "<absent>"
          and isinstance(d["class_entries"]["before"]["CDmElement.__hash__"], dict))
    s = fscene()
    r = run_preflight(o, q1, s)
    check("D9 three primitives used: one First per expression, Next until the sentinel; no write, Operate or key "
          "change; Undo and playhead unchanged",
          s["vs"].calls["first"] == 2 and s["vs"].calls["get"] == 6 and s["vs"].calls["next"] == 6
          and TOUCHED == [] and r["side_effects"]["unchanged"] is True, s["vs"].calls)

    st = {"armed": False, "fired": 0}
    good = run_preflight(o, q1, fscene())
    bad = variant(off_track)
    changed = run_preflight(o, q1, fscene(), probe=[{"undo": "a", "head_seconds": 0.2083},
                                                     {"undo": "b", "head_seconds": 0.2083}])
    refused = [o["ot1_arm"](dict(st), x) for x in (bad, changed, None, {})]
    check("D5 ARM refuses to arm after a failing, state-changing or missing preflight",
          all(x["armed"] is False and "refused" in x for x in refused), refused)
    armed_state = dict(st)
    got = o["ot1_arm"](armed_state, good)
    check("D5 ARM arms only after a passing, unchanged preflight", got == {"armed": True, "fired": 0,
                                                                           "bone": u"bip_tail00"}
          and armed_state["armed"] is True, got)
    try:
        o["ot1_arm"](armed_state, good)
        twice = False
    except RuntimeError:
        twice = True
    check("D5 a second arm is refused", twice)
    with open(OBSERVER, "rb") as f:
        src = f.read().decode("ascii")
    capture = src[src.index("def ot1_capture"):]
    tree = ast.parse(src.encode("ascii"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module)
    check("D6 the observer imports no vsUtils (no import statement, no __import__/importlib)",
          "vsUtils" not in imported and "__import__" not in src and "importlib" not in src, sorted(imported))
    check("D6 BASE and ARM both run the preflight on the vs DataModel; ARM arms through ot1_arm after it",
          'if step in ("BASE", "ARM"):' in capture and "ot1_guarded_preflight(cpm, q1, identity, token, probe, vs)" in capture
          and capture.index("ot1_guarded_preflight(") < capture.index("ot1_arm(st, data[\"preflight\"])")
          and "st[\"armed\"] = True" not in capture)


def main():
    print("Interpreter: %s" % sys.version.split()[0])
    o = load_observer()
    q1 = o["ot1_q1"](REPO)
    check("L0 the pinned Q1 observer loads without running its capture", callable(q1.get("q1_full_map")))
    for section in (lambda: section_wrappers(o, q1), lambda: section_injection(o, q1), lambda: section_static(o),
                    lambda: section_preflight(o, q1), lambda: section_direct_refs(o, q1)):
        try:
            section()
        except Exception:
            check("section.completed", False, traceback.format_exc())
    passed = sum(1 for r in RESULTS if r[1])
    print("RESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
