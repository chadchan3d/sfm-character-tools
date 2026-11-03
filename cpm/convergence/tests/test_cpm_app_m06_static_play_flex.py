# -*- coding: utf-8 -*-
"""M-06 -- focused offline qualification of imported static flex compatibility in the CPM application source
(cpm/app/SFM_Character_Preset_Manager.py): the STATIC_PLAY_ONE_KEY_ZERO class.

Design authority: Astra's M-06 Production Correction Design, section 6 "Offline matrix".

Technique: as the M-05 suite (whose fake scene, data model and production namespace this reuses), the production
functions are extracted verbatim by name and run against a fake DME graph. Here the FLEX layer is real: controls, mode-3
channels, one-layer DmeFloatLogs and DmeGlobalFlexControllerOperator destinations, reachable from a movie / shot /
track / channels-clip hierarchy for complete writer discovery. Model and control names are synthetic.

Usage: --phase=run (Python 2.7.5 and Python 3.10). Offline only; nothing here demonstrates real-SFM behaviour,
native Undo/Redo or native writer reachability.
"""
from __future__ import print_function

import ast
import json
import math
import os
import sys
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_m05_static_scale as m05  # noqa: E402

PY2 = sys.version_info[0] == 2
try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

RESULTS = []
STATIC = "STATIC_PLAY_ONE_KEY_ZERO"
# Synthetic, unrelated model identity (no Krystal/name/zero special case).
m05.IDENTITY = {"model": u"models/synthetic/zz_rig_unit.mdl", "checksum": 777, "animset_name": u"zz_unit"}


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


def close(a, b):
    return abs(float(a) - float(b)) <= 1.0e-5


# ---------------------------------------------------------------------------
# Native-faithful attribute access (M-06 missing-attribute reader correction)
# ---------------------------------------------------------------------------
# SFM's vs wrapper (sdktools python vs/datamodel.py, CDmElement.GetAttribute) raises
# AttributeError('No such attribute') for a missing attribute instead of returning None, and
# CDmElement.HasAttribute() reports False for it. A present attribute, even one whose value cannot be read,
# reports True. Installed on the shared M-05 fake element for this suite only (the M-05 suite itself is untouched);
# every fake reaches its own attribute records through _lookup_attribute().

_M05_LOOKUP = m05.FakeElement.__dict__["GetAttribute"]


def _contradiction(element, attr_name):
    """A scripted contradictory accessor state for one attribute, held as scene data (a '#contradict:' record) so
    the fake Undo snapshot restores it like any other authored change."""
    if isinstance(attr_name, bytes):
        attr_name = attr_name.decode("ascii")
    marker = _M05_LOOKUP(element, u"#contradict:" + attr_name)
    return None if marker is None else marker.value


def _native_get_attribute(self, attr_name):
    mode = _contradiction(self, attr_name)
    if mode in ("raise_but_has", "has_non_bool", "has_raises"):
        raise AttributeError("No such attribute")
    if mode == "none_but_has":
        return None
    if mode == "present_but_not_has":
        return m05.FakeAttr(self, attr_name, None)
    attr = self._lookup_attribute(attr_name)
    if attr is None:
        raise AttributeError("No such attribute")
    return attr


def _native_has_attribute(self, attr_name):
    mode = _contradiction(self, attr_name)
    if mode in ("raise_but_has", "none_but_has"):
        return True
    if mode == "present_but_not_has":
        return False
    if mode == "has_non_bool":
        return 0
    if mode == "has_raises":
        raise RuntimeError("presence unreadable")
    return self._lookup_attribute(attr_name) is not None


m05.FakeElement._lookup_attribute = _M05_LOOKUP
m05.FakeElement.GetAttribute = _native_get_attribute
m05.FakeElement.HasAttribute = _native_has_attribute


# ---------------------------------------------------------------------------
# Fake FLEX graph
# ---------------------------------------------------------------------------

class Unreadable(object):
    """An attribute that exists but cannot be read (the marker below is only for harness snapshots)."""
    value = "<unreadable>"

    def GetValue(self):
        raise RuntimeError("unreadable attribute")


def make_unreadable(element, attr_name):
    element._attrs[attr_name] = Unreadable()


def _native_failure(*args):
    raise RuntimeError("native accessor failed")


def native_type_fails(element):
    """GetTypeString raises; the historical typ() would substitute the Python class name."""
    element.GetTypeString = _native_failure


def native_identity_fails(element):
    """Neither the handle nor the native pointer can be read."""
    element.GetHandle = _native_failure
    del element.this


class ArrAttr(object):
    def __init__(self, value):
        self.value = value

    def GetValue(self):
        return self.value


class FlexLayer(m05.FakeLayer):
    """One DmeFloatLogLayer; its times/values arrays mirror the keys unless a test overrides them."""

    def __init__(self, element_name, keys, curvetypes=None):
        m05.FakeLayer.__init__(self, element_name, keys)
        # As every surveyed SFM flex layer: empty per-key curve types and an empty compressed block.
        self.put("curvetypes", [] if curvetypes is None else list(curvetypes))
        self.put("compressed", b"")

    # The raw times/values arrays, when a test makes them disagree with the key getters. Held as scene data
    # (an attribute record), so the fake Undo snapshot restores it like any other authored change.
    @property
    def array_override(self):
        attr = self._attrs.get("#arrays")
        return None if attr is None else attr.value

    @array_override.setter
    def array_override(self, value):
        if value is None:
            self.drop("#arrays")
        else:
            self.put("#arrays", value)

    def _lookup_attribute(self, attr_name):
        if isinstance(attr_name, bytes):
            attr_name = attr_name.decode("ascii")
        if attr_name in ("times", "values"):
            if isinstance(self._attrs.get(attr_name), Unreadable):
                return self._attrs[attr_name]
            if self.array_override is not None:
                return ArrAttr(self.array_override[attr_name])
            return ArrAttr([k[0] if attr_name == "times" else k[1] for k in self.keys])
        return _M05_LOOKUP(self, attr_name)

    def ClearAndAddSampleAtTime(self, time, channel):
        m05.Scene.current.cpm_writes.append((self._name, "sample", None))
        source = channel.raw("fromElement").raw(channel.raw("fromAttribute"))
        self.keys = [[0.0, source]]

    def ClearKeys(self):
        m05.Scene.current.cpm_writes.append((self._name, "clear", None))
        self.keys = []


class FlexLog(m05.FakeElement):
    def __init__(self, element_name, layers, use_default=True, default=0.0):
        m05.FakeElement.__init__(self, u"DmeFloatLog", element_name, usedefaultvalue=use_default,
                                 defaultvalue=default, curveinfo=None, bookmarks=[], layers=list(layers))
        self.layers = layers
        self.value_override = None

    def GetNumLayers(self):
        return len(self.layers)

    def GetLayer(self, index):
        return self.layers[index]

    def IsEmpty(self):
        return all(not layer.keys for layer in self.layers)

    def GetValue(self, t):
        if self.value_override is not None:
            return self.value_override
        if self.layers and self.layers[0].keys:
            return self.layers[0].keys[0][1]
        return self.raw("defaultvalue")


class FlexOperator(m05.FakeElement):
    counter = [0]

    def __init__(self, element_name, weight, model=None, gid=None):
        model = model if model is not None else m05.Scene.current.flex_model
        m05.FakeElement.__init__(self, u"DmeGlobalFlexControllerOperator", element_name, flexWeight=weight,
                                 gameModel=model)
        FlexOperator.counter[0] += 1
        self.gid = FlexOperator.counter[0] if gid is None else gid
        model.put("globalFlexControllers", model.raw("globalFlexControllers") + [self])

    def GetGlobalIndex(self):
        return self.gid


class FlexChannel(m05.FakeElement):
    def __init__(self, element_name, log, control, source_attr, destination, mode=3):
        m05.FakeElement.__init__(self, u"DmeChannel", element_name, mode=mode, fromElement=control,
                                 fromAttribute=source_attr, toElement=destination, toAttribute=u"flexWeight",
                                 log=log, fromIndex=0, toIndex=0)
        self.log = log

    def GetLog(self):
        return self.log

    def GetCurrentTime(self):
        return m05.FakeTime(m05.Scene.current.head)

    def Operate(self):
        # Play mode: the log value reaches the destination.
        m05.Scene.current.operate_calls += 1
        if int(self.raw("mode")) == 3:
            self.raw("toElement").put(self.raw("toAttribute"), self.log.GetValue(0.0))


class FlexScene(m05.Scene):
    """M-05 fake scene + flex graph + a movie hierarchy; Undo snapshots also cover list membership and attribute
    presence, so an aborted missing-scale creation is fully undone."""

    def __init__(self):
        m05.Scene.__init__(self)
        self.flex_channels = []
        self.extra_channels = []
        self.discovery_break = None
        self.animset.put("operators", [])
        self.flex_model = m05.FakeElement(u"DmeGameModel", u"zz_unit_model", globalFlexControllers=[])
        self.shot_operators = []
        # Channels held by an extra channels clip whose own native identity the tests can impair.
        self.hidden_channels = []

    def flex_side(self, control, source_attr, channel_attr, effective, stored, mode=3, keys=None, layers=None,
                  curvetypes=None, use_default=True):
        control.put(source_attr, stored)
        dest = FlexOperator(control._name + u"_" + source_attr, effective)
        keys = [[0.0, effective]] if keys is None else keys
        layer_list = layers or [FlexLayer(control._name + u"_layer", keys, curvetypes)]
        log = FlexLog(control._name + u"_log", layer_list, use_default=use_default)
        ch = FlexChannel(control._name + u"_" + source_attr + u"_channel", log, control, source_attr, dest, mode)
        control.put(channel_attr, ch)
        self.flex_channels.append(ch)
        return {"control": control, "dest": dest, "log": log, "layer": layer_list[0], "channel": ch}

    def mono(self, name, effective, stored=None, **kw):
        ctl = m05.FakeElement(u"DmElement", name, defaultValue=0.0)
        self.controls.append(ctl)
        return self.flex_side(ctl, u"value", u"channel", effective, effective if stored is None else stored, **kw)

    def stereo(self, name, left, right):
        ctl = m05.FakeElement(u"DmElement", name, defaultValue=0.0)
        self.controls.append(ctl)
        return (self.flex_side(ctl, u"leftValue", u"leftvaluechannel", left[0], left[1]),
                self.flex_side(ctl, u"rightValue", u"rightvaluechannel", right[0], right[1]))

    def movie(self):
        # The hierarchy is rebuilt per call (so later-added channels are included) and is not scene data:
        # its elements are not registered for Undo snapshots or digests.
        registered = len(self.elements)
        try:
            return self._movie()
        finally:
            del self.elements[registered:]

    def _movie(self):
        clip = m05.FakeElement(u"DmeChannelsClip", u"channels",
                               channels=list(self.flex_channels) + list(self.channels) + list(self.extra_channels))
        track = m05.FakeElement(u"DmeTrack", u"animSetEditorChannels", children=[clip])
        if self.discovery_break == "track-children":
            track.drop("children")
        if self.discovery_break == "children-unreadable":
            make_unreadable(track, "children")
        if self.discovery_break == "children-null":
            track.put("children", None)
        if self.discovery_break == "channels-unreadable":
            make_unreadable(clip, "channels")
        if self.discovery_break == "clip-type-unreadable":
            hidden = m05.FakeElement(u"DmeChannelsClip", u"hidden", channels=list(self.hidden_channels))
            native_type_fails(hidden)
            track.raw("children").append(hidden)
        if self.discovery_break == "clip-identity-unreadable":
            # Two channels clips whose native identity cannot be read: the one holding the competitor is
            # reached second.
            for clip_name, held in ((u"hidden", list(self.hidden_channels)), (u"empty", [])):
                unidentified = m05.FakeElement(u"DmeChannelsClip", clip_name, channels=held)
                native_identity_fails(unidentified)
                track.raw("children").append(unidentified)
        tracks = [track]
        if self.discovery_break == "sibling-null":
            # A second branch whose collection reads as null could hide a competitor while this
            # side's own channel is still found on the readable branch.
            tracks.append(m05.FakeElement(u"DmeTrack", u"hidden", children=None))
        if self.discovery_break == "partial":
            broken = m05.FakeElement(u"DmeTrack", u"unreadable", children=[])
            broken.drop("children")
            tracks.append(broken)
        group = m05.FakeElement(u"DmeTrackGroup", u"channelTrackGroup", tracks=tracks)
        if self.discovery_break == "tracks-unreadable":
            make_unreadable(group, "tracks")
        shot = m05.FakeElement(u"DmeFilmClip", u"shot01", trackGroups=[group], animationSets=[self.animset],
                               operators=list(self.shot_operators))
        if self.discovery_break == "shot-operators-unreadable":
            make_unreadable(shot, "operators")
        shots = m05.FakeElement(u"DmeTrack", u"Film", children=[shot])
        sub = m05.FakeElement(u"DmeTrackGroup", u"subClipTrackGroup", tracks=[shots])
        return m05.FakeElement(u"DmeFilmClip", u"movie", subClipTrackGroup=sub, trackGroups=[])

    def capture(self):
        snap = m05.Scene.capture(self)
        snap["present"] = dict((e._handle, sorted(e._attrs.keys())) for e in self.elements)
        snap["lists"] = {"channels": list(self.channels), "controls": list(self.controls),
                         "operators": list(self.operators), "elements": list(self.elements),
                         "group": list(self.group.raw("controls")), "extra": list(self.extra_channels),
                         "shot_operators": list(self.shot_operators)}
        return snap

    def restore(self, snap):
        for e in self.elements:
            if e._handle in snap["present"]:
                for k in list(e._attrs.keys()):
                    if k not in snap["present"][e._handle]:
                        del e._attrs[k]
                # Like native Undo: an attribute removed, or made unreadable, inside the transaction comes back
                # with its snapshot value (attributes that were already unreadable stay as they were).
                for k in snap["present"][e._handle]:
                    value = snap["attrs"].get((e._handle, k))
                    if value == Unreadable.value:
                        continue
                    if k not in e._attrs or isinstance(e._attrs[k], Unreadable):
                        e._attrs[k] = m05.FakeAttr(e, k, value)
        m05.Scene.restore(self, snap)
        self.channels[:] = snap["lists"]["channels"]
        self.controls[:] = snap["lists"]["controls"]
        self.operators[:] = snap["lists"]["operators"]
        self.elements[:] = snap["lists"]["elements"]
        self.group.put("controls", snap["lists"]["group"])
        self.extra_channels[:] = snap["lists"]["extra"]
        self.shot_operators[:] = snap["lists"]["shot_operators"]


def scene(scale=False, created=False):
    """A synthetic rig: bone 0 implicit-neutral; bone 4 with an optional mode-3 static scale graph (M-05)."""
    m05.Log.lines[:] = []
    m05.Log.samples[:] = []
    m05.Timer.queue[:] = []
    m05.Timer.fail[0] = False
    m05.FakeApp.state[0] = "none"
    m05.Store.files.clear()
    del m05.Store.writes[:]
    s = FlexScene()
    s.fail_flex_write = False
    s.bone(0, u"zz_root")
    if scale:
        t = s.bone(4, u"zz_crest")
        s.head_graph = s.scale_graph(t, u"zz_crest", 0.113, output_mode=3)
    return s


def flex_names(s):
    return sorted(set(c._name for c in s.controls if c.HasAttribute("channel")
                      or c.HasAttribute("leftvaluechannel")))


def record(s, flex, scales=None):
    """A Body record. flex: {name: value or (left, right)}; scales: {(index, name): value}."""
    values = {}
    for name, v in flex.items():
        if isinstance(v, tuple):
            values[u"flex." + name] = {"representation": u"STEREO", "left": v[0], "right": v[1]}
        else:
            values[u"flex." + name] = {"representation": u"MONO", "mono": v}
    rows = []
    for row in m05_bone_rows(s):
        value = (scales or {}).get((row[0], row[1]), row[2])
        rows.append({"bone_index": row[0], "bone_name": row[1], "representation": u"uniform_local_scale_multiplier",
                     "value": value, "capture_state": u"existing-static-control"})
    return {"kind": u"body", "name": u"T", "preset_id": u"preset-m06", "values": values, "bone_scales": rows}


def m05_bone_rows(s):
    rows = []
    for c in s.controls:
        if isinstance(c, m05.FakeTransformControl):
            name = c.transform._name
            index = int(name.split()[1])
            bone = name[name.index("(") + 1:-1]
            scale = c.transform.raw("scale") if "scale" in c.transform._attrs else 1.0
            rows.append((index, bone, scale))
    return sorted(rows)


# ---------------------------------------------------------------------------
# Namespace: the M-05 production namespace with the real FLEX layer
# ---------------------------------------------------------------------------

FLEX_EXTRACT = [
    "global_index", "resolve_side", "flex_binding", "key_count", "side_snapshot", "binding_snapshot",
    "PROD_FLEX_STATIC_PLAY", "PROD_FLEX_BODY_POLICY", "PROD_FLEX_DISCOVERY_NODE_CAP",
    "PROD_FLEX_EVIDENCE_EXACT_FIELDS", "PROD_FLEX_WRITER_FIELDS", "prod_flex_static_play_policy",
    "prod_flex_body_policy_bindings", "prod_flex_element_key", "prod_flex_writer_index", "prod_flex_policy_writers",
    "PROD_FLEX_UNRESOLVED_RECORD_CAP", "PROD_FLEX_SELF_CONTAINED_OPERATORS", "PROD_FLEX_CONSTRAINT_OPERATORS",
    "PROD_FLEX_SLAVE_TARGET_TYPES", "prod_flex_strict_read", "prod_flex_strict_list", "prod_flex_strict_state",
    "prod_flex_controller_peers", "flex_static_play_writers_ok", "native_attr_name",
    "prod_flex_strict_type", "prod_flex_identified_key", "prod_flex_strict_seconds", "prod_flex_strict_number",
    "prod_flex_strict_entries", "flex_key_arrays_match", "flex_bookmarks_ok",
    "prod_flex_capture_refusal",
    "flex_static_play_evidence", "flex_static_play_admitted", "flex_effective_value", "flex_effective_matches",
    "flex_structure_preserved", "flex_authored_change_ok", "p03_flex_expectations", "p03_verify_plan_results",
    "state_kind", "coherent", "same_side_identity", "matches_value", "matches_baseline", "write_side",
    "restore_side", "p02_snapshot_supported", "p02_snapshot_matches_baseline", "p02_saved_value_record",
    "p02_desired", "p03_build_plan", "p03_verify_saved_values", "p03_verify_baselines", "p03_capture_values",
]


def build_namespace(app):
    ns, methods = m05.build_namespace(app)
    missing = [n for n in FLEX_EXTRACT if n not in app.top]
    check("extraction.every_flex_name_present", not missing, missing)
    for name in FLEX_EXTRACT:
        if name not in missing:
            route._run_source(app.top_text(name), "app:%s" % name, ns)

    class _Sfm(m05._SfmApp):
        @staticmethod
        def GetMovie():
            movie = m05.Scene.current.movie()
            if m05.Scene.current.discovery_break == "no-movie":
                return None
            return movie
    ns["sfmApp"] = _Sfm
    ns["make_zero_time"] = lambda: m05.FakeTime(0.0)
    ns["prod_live_bindings_for_cached_scope"] = lambda identity, scope, kind, authority_context=None: {
        "accepted": live_bindings(ns)}
    return ns, methods


def live_bindings(ns):
    out = {}
    for c in m05.Scene.current.controls:
        if c.GetTypeString() != u"DmElement":
            continue
        b = ns["flex_binding"](c)
        if b is not None:
            out[b["literal"]] = b
    return out


def policy(ns, accepted):
    return ns["prod_flex_body_policy_bindings"](accepted)


def side_state(ns, literal, side_name="mono", with_policy=True):
    acc = live_bindings(ns)
    if with_policy:
        acc = policy(ns, acc)
    return ns["binding_snapshot"](acc[literal])["sides"][side_name]


def apply(ns, rec, kind=u"body", context={"token": u"ctx"}):
    rec = dict(rec, kind=kind)
    return ns["prod_apply"](m05.IDENTITY, rec, scope={"authority": {}, "body": {}}, operation_context=context)


def save(ns):
    return ns["prod_save"](m05.IDENTITY, u"body", u"m06 save", scope={"provider_descriptor": {}},
                           operation_context={"token": u"ctx"})


def raises(fn):
    try:
        fn()
    except Exception as exc:
        return exc
    return None


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def section_classification(ns):
    s = scene()
    s.mono(u"qx_empty", 0.0, keys=[])
    s.mono(u"qx_coherent", 0.4)
    s.mono(u"qx_stale", 0.6600985527038574, stored=0.0)
    s.mono(u"qx_stale_nonzero", 0.81, stored=0.37)
    for name, expect in ((u"qx_empty", "EMPTY"), (u"qx_coherent", "ONE_KEY_ZERO"), (u"qx_stale", STATIC),
                         (u"qx_stale_nonzero", STATIC)):
        st = side_state(ns, name)
        check("1 policy classification %s -> %s" % (name, expect), ns["state_kind"](st) == expect,
              ns["state_kind"](st))
    for name, expect in ((u"qx_empty", "EMPTY"), (u"qx_coherent", "ONE_KEY_ZERO"), (u"qx_stale", "UNSUPPORTED"),
                         (u"qx_stale_nonzero", "UNSUPPORTED")):
        st = side_state(ns, name, with_policy=False)
        check("1 no policy (Expression/Fit/legacy) %s -> %s, snapshot unchanged" % (name, expect),
              ns["state_kind"](st) == expect and "policy" not in st and "candidate" not in st, sorted(st))
    st = side_state(ns, u"qx_stale")
    check("2 static-play evidence: one writer, own log/layer, complete discovery, metadata read",
          st["writers_complete"] is True and st["destination_writer_ids"] == [st["channel_id"]]
          and st["log_channel_ids"] == [st["channel_id"]] and st["layer_log_ids"] == [st["log_id"]]
          and st["control_writer_ids"] == [] and st["usedefaultvalue"] is True and st["mode"] == 3
          and st["times_len"] == 1 and st["values_len"] == 1, st)
    check("2 coherent() true for the admitted class; matches_value() unchanged (requires the source)",
          ns["coherent"](st) is True and ns["matches_value"](st, 0.6600985527038574) is False
          and ns["flex_effective_matches"](st, 0.6600985527038574) is True
          and ns["flex_effective_value"](st) == 0.6600985527038574)
    admitted = ns["flex_static_play_admitted"]
    check("2 the full evidence is admitted as-is", admitted(dict(st)) is True)
    for field, value in (("writers_complete", False), ("policy", None), ("policy", u"expression"),
                         ("usedefaultvalue", None), ("defaultvalue", None), ("global_index", None),
                         ("endpoints_ok", False), ("native_layer_count", None), ("native_key_count", None),
                         ("times_len", None), ("curvetypes", u"unreadable"), ("control_writer_ids", [("x",)]),
                         ("log_channel_ids", []), ("layer_log_ids", []), ("source", None)):
        mutated = dict(st)
        mutated[field] = value
        check("2 admission refuses when only %s=%r" % (field, value), admitted(mutated) is False)
    coherent_st = side_state(ns, u"qx_coherent")
    check("1 historical sides gather no writer evidence (no discovery cost, unchanged semantics)",
          "writers_complete" not in coherent_st and coherent_st["candidate"] is False)


def refusal_cases():
    def keyed2(s):
        s.mono(u"zr_target", 0.5, stored=0.0, keys=[[0.0, 0.5], [1.0, 0.5]])

    def layers2(s):
        s.mono(u"zr_target", 0.5, stored=0.0, layers=[FlexLayer(u"l1", [[0.0, 0.5]]), FlexLayer(u"l2", [])])

    def mode1(s):
        s.mono(u"zr_target", 0.5, stored=0.0, mode=1)

    def nonfinite_source(s):
        s.mono(u"zr_target", 0.5, stored=float("nan"))

    def nonfinite_key(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        d["layer"].keys = [[0.0, float("inf")]]

    def key_time(s):
        s.mono(u"zr_target", 0.5, stored=0.0, keys=[[0.25, 0.5]])

    def eval_mismatch(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        d["log"].value_override = 0.7

    def dest_mismatch(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        d["dest"].put("flexWeight", 0.9)

    def unreadable_default_flag(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        d["log"].drop("usedefaultvalue")

    def inconsistent_arrays(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        d["layer"].array_override = {"times": [0.0, 1.0], "values": [0.5]}

    def extra_curvetypes(s):
        s.mono(u"zr_target", 0.5, stored=0.0, curvetypes=[1, 2])

    def wrong_endpoint_attr(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        d["channel"].put("fromAttribute", u"leftValue")

    def wrong_destination(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        d["channel"].put("toAttribute", u"value")

    def duplicate_writer(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        s.extra_channels.append(FlexChannel(u"rogue", FlexLog(u"rl", [FlexLayer(u"rlay", [[0.0, 0.5]])]),
                                            d["control"], u"value", d["dest"]))

    def shared_log(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        other = FlexOperator(u"other", 0.5)
        s.extra_channels.append(FlexChannel(u"twin", d["log"], d["control"], u"value", other))

    def shared_layer(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        other = FlexOperator(u"other", 0.5)
        s.extra_channels.append(FlexChannel(u"twin", FlexLog(u"tl", [d["layer"]]), d["control"], u"value", other))

    def control_writer(s):
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        s.extra_channels.append(FlexChannel(u"ctlw", FlexLog(u"cl", [FlexLayer(u"cly", [[0.0, 0.1]])]),
                                            d["dest"], u"flexWeight", d["control"]))
        s.extra_channels[-1].put("toAttribute", u"value")

    def incomplete_discovery(s):
        s.mono(u"zr_target", 0.5, stored=0.0)
        s.discovery_break = "track-children"

    def partial_discovery(s):
        s.mono(u"zr_target", 0.5, stored=0.0)
        s.discovery_break = "partial"

    def no_movie(s):
        s.mono(u"zr_target", 0.5, stored=0.0)
        s.discovery_break = "no-movie"

    return [("multiple keys", keyed2), ("multiple layers", layers2), ("wrong mode (1)", mode1),
            ("nonfinite source", nonfinite_source), ("nonfinite key", nonfinite_key), ("key not at time 0", key_time),
            ("key != native evaluation", eval_mismatch), ("key != destination", dest_mismatch),
            ("unreadable default flag", unreadable_default_flag), ("inconsistent key arrays", inconsistent_arrays),
            ("extra curve metadata", extra_curvetypes), ("wrong source attribute", wrong_endpoint_attr),
            ("wrong destination attribute", wrong_destination), ("duplicate destination writer", duplicate_writer),
            ("shared writable log", shared_log), ("shared writable layer", shared_layer),
            ("writer to the control", control_writer), ("incomplete discovery (unreadable link)", incomplete_discovery),
            ("incomplete discovery (no movie)", no_movie),
            ("partial discovery (own channel found, another branch unreadable)", partial_discovery)]


def section_refusals(ns):
    for label, make in refusal_cases():
        s = scene()
        s.mono(u"zr_other", 0.2)
        make(s)
        literals = sorted(live_bindings(ns))
        if u"zr_target" not in literals:
            # Structural binding refusal already happens in resolve_side (historical behaviour).
            check("8 refuse %s: not even a supported binding (historical resolve_side)" % label, True)
            continue
        kind = ns["state_kind"](side_state(ns, u"zr_target"))
        before = s.digest()
        exc = raises(lambda: save(ns))
        check("8 refuse %s: class UNSUPPORTED; Save refuses, nothing written" % label,
              kind == "UNSUPPORTED" and exc is not None and "Unsupported static" in _TEXT(exc)
              and not m05.Store.writes and s.digest() == before and not s.cpm_writes, (kind, exc))
        exc = raises(lambda: apply(ns, record(s, {u"zr_other": 0.2, u"zr_target": 0.9})))
        check("8 refuse %s: Apply refuses before any transaction" % label,
              exc is not None and "StartUndo" not in s.events and not s.dm.stack and s.digest() == before, exc)


def section_save(ns):
    s = scene()
    s.mono(u"qy_alpha", 0.6600985527038574, stored=0.0)
    s.mono(u"qy_beta", 0.8100000023841858, stored=0.3700000047683716)
    s.mono(u"qy_gamma", 0.25)
    s.mono(u"qy_zero", 0.0, keys=[])
    s.stereo(u"qy_pair", (0.45, 0.0), (0.3, 0.3))
    before = s.digest()
    m05.Store.files.clear()
    del m05.Store.writes[:]
    path = save(ns)
    saved = m05.Store.files[path]["values"]
    check("2 Save captures the exact key of each static-play side (no display rounding)",
          saved[u"flex.qy_alpha"] == {"representation": u"MONO", "mono": 0.6600985527038574}
          and saved[u"flex.qy_beta"]["mono"] == 0.8100000023841858, saved)
    check("3 nonzero stale source admitted the same way (synthetic names; no zero/name rule)",
          saved[u"flex.qy_beta"]["mono"] != 0.3700000047683716)
    check("1 historical sides saved as before (evaluated)", saved[u"flex.qy_gamma"]["mono"] == 0.25
          and saved[u"flex.qy_zero"]["mono"] == 0.0)
    check("4 stereo: stale left and coherent right each captured", saved[u"flex.qy_pair"] ==
          {"representation": u"STEREO", "left": 0.45, "right": 0.3}, saved[u"flex.qy_pair"])
    check("2 Save made no scene change and no channel operation",
          s.digest() == before and not s.cpm_writes and s.operate_calls == 0 and not s.dm.stack)
    check("12 preset schema unchanged (same record keys and representations)",
          set(m05.Store.files[path]) == set(["schema_version", "record_kind", "preset_id", "character_key", "kind",
                                             "name", "model_ref", "capture_semantic_policy", "capture_provider",
                                             "created_at", "values", "bone_scales", "bone_scale_policy"]))


def section_apply(ns):
    # 5 true no-op on the effective value; disagreement preserved.
    s = scene()
    s.mono(u"qz_stale", 0.66, stored=0.0)
    s.mono(u"qz_plain", 0.25)
    before = s.digest()
    r = apply(ns, record(s, {u"qz_stale": 0.66, u"qz_plain": 0.25}))
    check("5 true no-op: verified, no transaction, no write, disagreement preserved",
          r["phase"] == u"no-op" and "StartUndo" not in s.events and not s.dm.stack and not s.cpm_writes
          and s.digest() == before and s.operate_calls == 0, r["phase"])
    # 5 the admitted state changes after planning: the no-op is not confirmed (nothing written).
    s = scene()
    d = s.mono(u"qz_stale", 0.66, stored=0.0)
    s.mono(u"qz_plain", 0.25)
    real_undo_state = ns["undo_state"]

    def undo_state_with_interference(label):
        if label == "PROD_APPLY_UNDO_BEFORE":
            d["control"]._attrs["value"].value = 0.66   # normalised by someone else after planning
        return real_undo_state(label)
    ns["undo_state"] = undo_state_with_interference
    exc = raises(lambda: apply(ns, record(s, {u"qz_stale": 0.66, u"qz_plain": 0.25})))
    ns["undo_state"] = real_undo_state
    check("5 state changed after planning: no-op not confirmed, refused, no transaction",
          exc is not None and "no-op could be confirmed" in _TEXT(exc) and "StartUndo" not in s.events, exc)
    # 5b matching stale flex beside a required scale creation: not a whole-operation no-op.
    s = scene()
    d = s.mono(u"qz_stale", 0.66, stored=0.0)
    rows = m05_bone_rows(s)
    r = apply(ns, record(s, {u"qz_stale": 0.66}, scales={(rows[0][0], rows[0][1]): 1.4}))
    check("5 matching flex + missing scale creation: one transaction, flex side untouched, verified",
          r["phase"] == u"committed-verified" and len(s.dm.stack) == 1 and s.created
          and d["control"].raw("value") == 0.0 and d["layer"].keys == [[0.0, 0.66]]
          and not [w for w in s.cpm_writes if w[0] in (u"qz_stale", u"qz_stale_layer")], (r["phase"], s.cpm_writes))
    # 6 changed Apply.
    s = scene()
    d = s.mono(u"qz_stale", 0.66, stored=0.12)
    s.mono(u"qz_plain", 0.25)
    base = side_state(ns, u"qz_stale")
    r = apply(ns, record(s, {u"qz_stale": 0.3, u"qz_plain": 0.25}))
    after = side_state(ns, u"qz_stale")
    check("6 changed Apply: key and source updated, effective/destination agree, verified",
          r["phase"] == u"committed-verified" and close(d["control"].raw("value"), 0.3)
          and d["layer"].keys == [[0.0, 0.3]] and close(d["dest"].raw("flexWeight"), 0.3), r["phase"])
    check("6 mode, key time, identities, layer structure and metadata preserved",
          ns["flex_structure_preserved"](after, base) and after["mode"] == 3 and len(s.dm.stack) == 1)
    # 4 stereo per-side write decision.
    s = scene()
    left, right = s.stereo(u"qz_pair", (0.45, 0.0), (0.3, 0.3))
    r = apply(ns, record(s, {u"qz_pair": (0.45, 0.6)}))
    check("4 stereo: matching stale left not written; right changed; verified",
          r["phase"] == u"committed-verified" and left["control"].raw("leftValue") == 0.0
          and left["layer"].keys == [[0.0, 0.45]] and close(right["control"].raw("rightValue"), 0.6), r["phase"])


def section_failures(ns):
    def make():
        s = scene()
        d = s.mono(u"qf_stale", 0.66, stored=0.12)
        s.mono(u"qf_plain", 0.25)
        return s, d

    # 7 key write succeeds, source write raises.
    s, d = make()
    before = s.digest()
    attr = d["control"]._attrs["value"]
    attr.SetValue = lambda v: (_ for _ in ()).throw(RuntimeError("synthetic source failure"))
    exc = raises(lambda: apply(ns, record(s, {u"qf_stale": 0.3, u"qf_plain": 0.25})))
    check("7 source write fails after key write: abort, baseline (incl. disagreement) verified restored",
          isinstance(exc, RuntimeError) and not isinstance(exc, ns["ProdRecoveryUnverifiedError"])
          and "AbortUndo" in s.events and s.digest() == before and d["control"].raw("value") == 0.12
          and d["layer"].keys == [[0.0, 0.66]] and ns["PROD_LOG_CONTEXT"]["recovery"] == u"verified", exc)
    # 7 source write silently ineffective (key took effect): never verified.
    s, d = make()
    before = s.digest()
    d["control"]._attrs["value"].SetValue = lambda v: None
    exc = raises(lambda: apply(ns, record(s, {u"qf_stale": 0.3, u"qf_plain": 0.25})))
    check("7 key took effect but source did not: precommit fails, no false success, recovery verified",
          exc is not None and "precommit" in _TEXT(exc) and s.digest() == before and not s.dm.stack, exc)
    # 7 key write silently ineffective, source written.
    s, d = make()
    before = s.digest()
    d["layer"].SetKeyValue = lambda i, v: None
    exc = raises(lambda: apply(ns, record(s, {u"qf_stale": 0.3, u"qf_plain": 0.25})))
    check("7 source took effect but key did not: precommit fails, no false success, recovery verified",
          exc is not None and "precommit" in _TEXT(exc) and s.digest() == before and not s.dm.stack, exc)
    # 7 key write raises.
    s, d = make()
    before = s.digest()
    d["layer"].SetKeyValue = lambda i, v: (_ for _ in ()).throw(RuntimeError("synthetic key failure"))
    exc = raises(lambda: apply(ns, record(s, {u"qf_stale": 0.3, u"qf_plain": 0.25})))
    check("7 key write fails: abort, recovery verified, baseline restored", exc is not None
          and "AbortUndo" in s.events and s.digest() == before and ns["PROD_LOG_CONTEXT"]["recovery"] == u"verified", exc)
    # 10 failure after missing-scale creation (combined transaction).
    s, d = make()
    rows = m05_bone_rows(s)
    before = s.digest()
    n_channels = len(s.channels)
    s.fail_flex_write = False
    orig = ns["write_side"]

    def failing_write(binding, side, origin, desired):
        raise RuntimeError("synthetic failure after scale creation")
    ns["write_side"] = failing_write
    exc = raises(lambda: apply(ns, record(s, {u"qf_stale": 0.3, u"qf_plain": 0.25},
                                           scales={(rows[0][0], rows[0][1]): 1.4})))
    ns["write_side"] = orig
    check("10 failure after missing-scale creation: combined abort restores scale graph and flex, verified",
          exc is not None and s.created and len(s.channels) == n_channels and s.digest() == before
          and ns["PROD_LOG_CONTEXT"]["recovery"] == u"verified", (exc, ns["PROD_LOG_CONTEXT"]["recovery"]))
    # 9 abort that cannot restore -> recovery unverified (never claimed from visible values).
    s, d = make()
    s.dm.abort_restores = False
    d["control"]._attrs["value"].SetValue = lambda v: (_ for _ in ()).throw(RuntimeError("x"))
    exc = raises(lambda: apply(ns, record(s, {u"qf_stale": 0.3, u"qf_plain": 0.25})))
    check("9 unprovable restoration -> ProdRecoveryUnverifiedError", isinstance(exc, ns["ProdRecoveryUnverifiedError"]),
          exc)


def section_baseline(ns):
    s = scene()
    d = s.mono(u"qb_stale", 0.66, stored=0.12)
    base = side_state(ns, u"qb_stale")
    mb = ns["matches_baseline"]
    check("9 untouched static-play side matches its baseline exactly", mb(side_state(ns, u"qb_stale"), base, STATIC))
    d["control"].put("value", 0.66)
    check("9 source normalised to the key (equivalent-looking) is NOT the restored baseline",
          not mb(side_state(ns, u"qb_stale"), base, STATIC))
    d["control"].put("value", 0.12)
    cases = [("mode changed", lambda: d["channel"].put("mode", 1), lambda: d["channel"].put("mode", 3)),
             ("curve metadata changed", lambda: d["layer"].put("curvetypes", [5]), lambda: d["layer"].drop("curvetypes")),
             ("default flag changed", lambda: d["log"].put("usedefaultvalue", False),
              lambda: d["log"].put("usedefaultvalue", True)),
             ("default value changed", lambda: d["log"].put("defaultvalue", 0.5),
              lambda: d["log"].put("defaultvalue", 0.0))]
    for label, change, undo in cases:
        change()
        ok = mb(side_state(ns, u"qb_stale"), base, STATIC)
        undo()
        check("9 equal visible value but %s: preservation fails" % label, not ok)
    old_log = d["channel"].log
    d["channel"].log = FlexLog(old_log._name, [FlexLayer(d["layer"]._name, [[0.0, 0.66]])])
    d["channel"].put("log", d["channel"].log)
    check("9 replaced log/layer with identical values: preservation fails", not mb(side_state(ns, u"qb_stale"), base,
                                                                                    STATIC))


def section_m05(ns):
    s = scene(scale=True)
    d = s.mono(u"qm_stale", 0.66, stored=0.12)
    s.mono(u"qm_plain", 0.25)
    rows = m05_bone_rows(s)
    crest = [r for r in rows if r[1] == u"zz_crest"][0]
    rec = record(s, {u"qm_stale": 0.3, u"qm_plain": 0.25}, scales={(crest[0], crest[1]): 1.25})
    r = apply(ns, rec)
    pending = r.get("pending") or {}
    check("11 M-06 flex + M-05 scale change: one pending operation carrying detached flex expectations",
          r["phase"] == u"verification-pending" and len(pending.get("flex_expectations") or []) == 2
          and m05.is_pure(pending) and len(s.dm.stack) == 1, r["phase"])
    s.event_turn()
    out = ns["prod_apply_deferred_verify"](pending)
    check("11 deferred check verifies flex expectations and the scale map -> committed-verified",
          out["phase"] == u"committed-verified", out)
    # flex interference during the yield on an unchanged static-play side.
    s = scene(scale=True)
    d = s.mono(u"qm_stale", 0.66, stored=0.12)
    s.mono(u"qm_plain", 0.25)
    rows = m05_bone_rows(s)
    crest = [r for r in rows if r[1] == u"zz_crest"][0]
    r = apply(ns, record(s, {u"qm_stale": 0.66, u"qm_plain": 0.25}, scales={(crest[0], crest[1]): 1.25}))
    s.event_turn()
    d["control"].put("value", 0.66)
    out = ns["prod_apply_deferred_verify"](r["pending"])
    check("11 unchanged static-play side normalised during the yield -> committed-unverified (flex)",
          out["phase"] == u"committed-unverified" and out.get("reason") == u"flex", out)
    # 11 existing M-05 lifecycle protections still hold through the real window path.
    s = scene(scale=True)
    s.mono(u"qm_stale", 0.66, stored=0.12)
    rows = m05_bone_rows(s)
    crest = [r for r in rows if r[1] == u"zz_crest"][0]
    w = WINDOW(record(s, {u"qm_stale": 0.3}, scales={(crest[0], crest[1]): 1.25}))
    w.apply_kind(u"body")
    m05.FakeApp.state[0] = "modal"
    m05.Timer.run_all()
    m05.FakeApp.state[0] = "none"
    check("11 modal at callback entry still ends unverified without scene access (M-05 guard)",
          w.operation is None and any(u"modal-active" in line for line in m05.Log.lines))


def section_isolation(ns, app):
    s = scene()
    s.mono(u"qi_stale", 0.66, stored=0.0)
    exc = raises(lambda: ns["p03_capture_values"](live_bindings(ns)))
    check("12 without the Body policy (Expression / Clothing Fit source / legacy) the stale side is refused",
          exc is not None and "Unsupported static" in _TEXT(exc), exc)
    before = s.digest()
    exc = raises(lambda: apply(ns, record(s, {u"qi_stale": 0.3}), kind=u"expression"))
    check("12 Expression Apply keeps the historical refusal (no transaction)",
          exc is not None and "StartUndo" not in s.events and s.digest() == before, exc)
    tree = ast.parse(app.raw)
    callers = sorted(set(node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                         and "prod_flex_body_policy_bindings" in ast.dump(node)
                         and node.name != "prod_flex_body_policy_bindings"))
    check("12 the Body policy is supplied only by Body capture, Body Apply, abort verification and deferred check",
          callers == ["prod_apply", "prod_apply_deferred_verify", "prod_capture_body_snapshot",
                      "prod_verify_apply_abort_baseline"], callers)
    for fn in ("prod_body_source", "prod_body_source_live_from_baseline", "prod_apply_match"):
        check("12 %s does not use the Body static-play policy" % fn,
              "prod_flex_body_policy_bindings" not in app.top_text(fn) and "static_play_policy" not in app.top_text(fn))
    import hashlib
    for fn, digest in sorted(UNCHANGED_HELPERS.items()):
        check("12 %s is byte-identical to baseline ea5e7c49" % fn,
              hashlib.sha256(app.top_text(fn).encode("utf-8")).hexdigest() == digest)
    check("12 discovery and admission are read-only (no write/operate/refresh/undo calls)",
          not set(["SetValue", "SetKeyValue", "Operate", "StartUndo", "ProcessEvents", "SetHeadTimeInSeconds"])
          & set(n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
                for fn in ("prod_flex_writer_index", "flex_static_play_evidence", "flex_static_play_admitted")
                for n in ast.walk(ast.parse(app.top_text(fn).encode("utf-8"))) if isinstance(n, ast.Call)))


# Text SHA-256 at baseline ea5e7c49 of shared helpers the correction must not change.
UNCHANGED_HELPERS = {
    "matches_value": "fc52df67ab7ef3bdf06c3465db86d84ee2ded13b4ab5a9ed27ca4d5f127bf967",
    "p03_verify_saved_values": "c9733dbe5c2e6a86509ea94f5b58fe574b240340ea26587e05e6e9c7f68d575b",
    "p03_verify_baselines": "654c98394a0f4a00042cc366d381b6955ba014c843c44c1cab2b925791824159",
    "p03_capture_values": "258878b07c155635b6bd81a3417b4fa1fd540d393068f5231e07188c1dc8aa19",
    "p02_snapshot_supported": "1f112115bb1a6411bf20444fb46d3507175a5788b63c17a736457c91f84af2bc",
    "p02_snapshot_matches_baseline": "3b61b12b984305a2aaa393e04552684f592ebc6401f05c5ab306aae4ce6bd3fa",
    "same_side_identity": "7566b2228a32ebe80e5b3236f547e4d7d4c8b289a4a6340d20783b6f85a368a0",
    "resolve_side": "a0ce3e3dd12d8508194e4426d2dcf924494488218a74b9f682c3bbe4d4c6048d",
    "flex_binding": "57effd39f5c96411140f135630064cf4144bfc0c907f844a7dadb0e9f3f8f0c1",
}

def operator(kind, name, **attrs):
    return m05.FakeElement(kind, name, **attrs)


def constraint(kind, target_type=u"DmeDag", target=True, slaves=("slave",)):
    attrs = {}
    for slave_attr in slaves:
        tgt = m05.FakeElement(target_type, u"tgt") if target else None
        attrs[slave_attr] = m05.FakeElement(u"DmeConstraintSlave", u"slave", target=tgt)
    return operator(kind, u"rig", **attrs)


def p1_writer_cases():
    """(label, mutate(scene, side)) -- each must refuse admission."""
    def comp_channel(s, d, **kw):
        return FlexChannel(u"rogue", FlexLog(u"rl", [FlexLayer(u"rlay", [[0.0, 0.5]])]), d["control"], u"value",
                           d["dest"], **kw)

    def unreadable_dest(s, d):
        ch = comp_channel(s, d)
        make_unreadable(ch, "toElement")
        s.extra_channels.append(ch)

    def film_clip_writer(s, d):
        s.shot_operators.append(comp_channel(s, d))

    def unknown_operator(s, d):
        s.animset.put("operators", [operator(u"DmeConnectionOperator", u"conn")])

    def unknown_film_operator(s, d):
        s.shot_operators.append(operator(u"DmeConnectionOperator", u"conn"))

    def constraint_unreadable_target(s, d):
        c = constraint(u"DmeRigPointConstraintOperator")
        make_unreadable(c.raw("slave"), "target")
        s.animset.put("operators", [c])

    def constraint_foreign_target(s, d):
        s.animset.put("operators", [constraint(u"DmeRigOrientConstraintOperator", u"DmeGlobalFlexControllerOperator")])

    def constraint_missing_joint(s, d):
        s.animset.put("operators", [constraint(u"DmeRigIKConstraintOperator", slaves=("slave", "startJoint"))])

    def from_index(s, d):
        d["channel"].put("fromIndex", 1)

    def to_index_unreadable(s, d):
        make_unreadable(d["channel"], "toIndex")

    def to_index_absent(s, d):
        d["channel"].drop("toIndex")

    def peer_controller(s, d):
        FlexOperator(u"peer", 0.5, gid=d["dest"].gid)

    def game_model_unreadable(s, d):
        make_unreadable(d["dest"], "gameModel")

    def mode_unreadable(s, d):
        make_unreadable(d["channel"], "mode")

    # Astra re-review counterexample: a competing channel whose native type read fails.
    def concealed_channel(s, d):
        ch = comp_channel(s, d)
        native_type_fails(ch)
        s.extra_channels.append(ch)

    def concealed_clip(s, d):
        s.hidden_channels.append(comp_channel(s, d))
        s.discovery_break = "clip-type-unreadable"

    def unidentified_clips(s, d):
        s.hidden_channels.append(comp_channel(s, d))
        s.discovery_break = "clip-identity-unreadable"

    return [("collection unreadable: track children", lambda s, d: setattr(s, "discovery_break", "children-unreadable")),
            ("collection present but null: track children", lambda s, d: setattr(s, "discovery_break", "children-null")),
            ("collection present but null on a sibling branch (own channel still found)",
             lambda s, d: setattr(s, "discovery_break", "sibling-null")),
            ("collection unreadable: clip channels", lambda s, d: setattr(s, "discovery_break", "channels-unreadable")),
            ("collection unreadable: track-group tracks", lambda s, d: setattr(s, "discovery_break", "tracks-unreadable")),
            ("collection unreadable: film-clip operators",
             lambda s, d: setattr(s, "discovery_break", "shot-operators-unreadable")),
            ("competing channel with unreadable destination", unreadable_dest),
            ("film-clip-level competing writer", film_clip_writer),
            ("unresolved animation-set operator type", unknown_operator),
            ("unresolved film-clip operator type", unknown_film_operator),
            ("constraint with unreadable slave target", constraint_unreadable_target),
            ("constraint with non-transform slave target", constraint_foreign_target),
            ("IK constraint with unreadable joint slaves", constraint_missing_joint),
            ("scalar fromIndex 1", from_index), ("unreadable toIndex", to_index_unreadable),
            ("absent toIndex", to_index_absent), ("peer flex controller with the same global index", peer_controller),
            ("unreadable destination game model", game_model_unreadable), ("unreadable channel mode", mode_unreadable),
            ("competing channel whose native type is unreadable", concealed_channel),
            ("channels clip whose native type is unreadable, holding a competing channel", concealed_clip),
            ("two channels clips without readable native identity, one holding a competing channel",
             unidentified_clips)]


def p1_metadata_cases():
    def unreadable_curvetypes(s, d):
        make_unreadable(d["layer"], "curvetypes")

    def unreadable_compressed(s, d):
        make_unreadable(d["layer"], "compressed")

    def compressed_data(s, d):
        d["layer"].put("compressed", b"\x01\x02")

    def unreadable_bookmarks(s, d):
        make_unreadable(d["log"], "bookmarks")

    def log_curveinfo(s, d):
        d["log"].put("curveinfo", m05.FakeElement(u"DmeFloatCurveInfo", u"ci"))

    def layer_curveinfo(s, d):
        d["layer"].put("curveinfo", m05.FakeElement(u"DmeFloatCurveInfo", u"ci"))

    def unreadable_log_curveinfo(s, d):
        make_unreadable(d["log"], "curveinfo")

    def unreadable_values(s, d):
        make_unreadable(d["layer"], "values")

    def unconvertible_bookmark(s, d):
        d["log"].put("bookmarks", [object()])

    return [("unreadable curvetypes (not empty)", unreadable_curvetypes),
            ("unreadable compressed block", unreadable_compressed), ("compressed data present", compressed_data),
            ("unreadable bookmarks", unreadable_bookmarks), ("log curve info present", log_curveinfo),
            ("layer curve info present", layer_curveinfo), ("unreadable log curve info", unreadable_log_curveinfo),
            ("unreadable key value array", unreadable_values),
            ("unconvertible bookmark entry", unconvertible_bookmark)]


def section_p1(ns):
    for group, cases in (("P1-1", p1_writer_cases()), ("P1-3", p1_metadata_cases())):
        for label, mutate in cases:
            s = scene()
            s.mono(u"zp_other", 0.2)
            d = s.mono(u"zp_target", 0.5, stored=0.0)
            mutate(s, d)
            kind = ns["state_kind"](side_state(ns, u"zp_target"))
            before = s.digest()
            exc = raises(lambda: save(ns))
            check("%s refuse %s: not admitted; Save refuses, nothing written" % (group, label),
                  kind == "UNSUPPORTED" and exc is not None and not m05.Store.writes and s.digest() == before,
                  (kind, exc))

    # Demonstrably unrelated operators (the surveyed SFM types) do not block admission.
    s = scene()
    s.mono(u"zp_target", 0.5, stored=0.0)
    s.animset.put("operators", [operator(u"DmeExpressionOperator", u"expr"), operator(u"DmePackColorOperator", u"pc"),
                                constraint(u"DmeRigPointConstraintOperator"),
                                constraint(u"DmeRigOrientConstraintOperator", u"DmeRigHandle"),
                                constraint(u"DmeRigIKConstraintOperator", u"DmeGameModel",
                                           slaves=("slave", "startJoint", "midJoint", "endJoint"))])
    s.shot_operators.append(operator(u"DmeExpressionOperator", u"shot_expr"))
    st = side_state(ns, u"zp_target")
    check("P1-1 surveyed unrelated operators (expression, pack colour, point/orient/IK constraints) still admit",
          ns["state_kind"](st) == STATIC and st.get("unresolved_relationships") == 0, (ns["state_kind"](st),))
    check("P1-1 scalar index contract recorded (fromIndex 0, toIndex 0)",
          st.get("from_index") == [u"value", u"0"] and st.get("to_index") == [u"value", u"0"],
          (st.get("from_index"),))

    # P1-3 baseline preservation: curveinfo relationships.
    s = scene()
    d = s.mono(u"zp_target", 0.5, stored=0.0)
    base = side_state(ns, u"zp_target")
    d["log"].put("curveinfo", m05.FakeElement(u"DmeFloatCurveInfo", u"ci"))
    check("P1-3 changed log curve-info relationship does not pass baseline preservation",
          not ns["matches_baseline"](side_state(ns, u"zp_target"), base, STATIC))
    d["log"].put("curveinfo", None)
    d["layer"].put("curveinfo", m05.FakeElement(u"DmeFloatCurveInfo", u"ci"))
    check("P1-3 added layer curve-info relationship does not pass baseline preservation",
          not ns["matches_baseline"](side_state(ns, u"zp_target"), base, STATIC))

    # P1-2 / P1-3 injections through the actual Apply path (changed static-play side; after the write
    # source == key, so the side no longer classifies as STATIC_PLAY_ONE_KEY_ZERO).
    injections = [
        ("P1-2 competing writer added after the authored write",
         lambda s, d: s.extra_channels.append(FlexChannel(u"late", FlexLog(u"ll", [FlexLayer(u"llay", [[0.0, 0.3]])]),
                                                          d["control"], u"value", d["dest"]))),
        ("P1-2 film-clip competing writer added after the authored write",
         lambda s, d: s.shot_operators.append(FlexChannel(u"late", FlexLog(u"ll", [FlexLayer(u"llay", [[0.0, 0.3]])]),
                                                          d["control"], u"value", d["dest"]))),
        ("P1-2 shared log introduced after the authored write",
         lambda s, d: s.extra_channels.append(FlexChannel(u"twin", d["log"], d["control"], u"value",
                                                          FlexOperator(u"o", 0.3)))),
        ("P1-3 curve-info relationship changed after the authored write",
         lambda s, d: d["log"].put("curveinfo", m05.FakeElement(u"DmeFloatCurveInfo", u"ci"))),
        ("P1-3 curve types changed after the authored write", lambda s, d: d["layer"].put("curvetypes", [5])),
        ("P1-3 layer curve-info relationship added after the authored write",
         lambda s, d: d["layer"].put("curveinfo", m05.FakeElement(u"DmeFloatCurveInfo", u"ci"))),
        # Astra re-review counterexamples: the native key getters still report the authored key, but the
        # layer's own arrays (same length) do not.
        ("P1-3 invalid same-length key value array after the authored write",
         lambda s, d: setattr(d["layer"], "array_override", {"times": [0.0], "values": [float("nan")]})),
        ("P1-3 key time array contradicting the key getter after the authored write",
         lambda s, d: setattr(d["layer"], "array_override", {"times": [0.25], "values": [0.3]})),
    ]
    for label, inject in injections:
        # precommit: inside the open transaction, right after the write.
        s = scene()
        d = s.mono(u"zp_target", 0.66, stored=0.12)
        s.mono(u"zp_other", 0.25)
        before = s.digest()
        real_write = ns["write_side"]

        def write_then_inject(binding, side, origin, desired, s=s, d=d, inject=inject, real_write=real_write):
            real_write(binding, side, origin, desired)
            if binding["literal"] == u"zp_target":
                inject(s, d)
        ns["write_side"] = write_then_inject
        result = None
        exc = raises(lambda: apply(ns, record(s, {u"zp_target": 0.3, u"zp_other": 0.25})))
        ns["write_side"] = real_write
        check("%s (precommit): Apply never committed-verified; transaction aborted" % label,
              exc is not None and "precommit" in _TEXT(exc) and not s.dm.stack and s.digest() == before, exc)
        # postcommit: after FinishUndo, at the synchronous verification boundary.
        s = scene()
        d = s.mono(u"zp_target", 0.66, stored=0.12)
        s.mono(u"zp_other", 0.25)
        real_refresh = ns["same_time_refresh"]

        def refresh_then_inject(head_time, lbl, s=s, d=d, inject=inject, real_refresh=real_refresh):
            real_refresh(head_time, lbl)
            inject(s, d)
        ns["same_time_refresh"] = refresh_then_inject
        result = apply(ns, record(s, {u"zp_target": 0.3, u"zp_other": 0.25}))
        ns["same_time_refresh"] = real_refresh
        check("%s (postcommit): committed-unverified, never committed-verified" % label,
              result["phase"] == u"committed-unverified" and len(s.dm.stack) == 1, result["phase"])
        # deferred: the existing M-05 pending operation.
        s = scene(scale=True)
        d = s.mono(u"zp_target", 0.66, stored=0.12)
        rows = m05_bone_rows(s)
        crest = [r for r in rows if r[1] == u"zz_crest"][0]
        result = apply(ns, record(s, {u"zp_target": 0.3}, scales={(crest[0], crest[1]): 1.25}))
        s.event_turn()
        inject(s, d)
        out = ns["prod_apply_deferred_verify"](result["pending"])
        check("%s (deferred): committed-unverified (flex)" % label,
              result["phase"] == u"verification-pending" and out["phase"] == u"committed-unverified"
              and out.get("reason") == u"flex", out)


# ---------------------------------------------------------------------------
# Verified-null IK primary slave (native Step 2 blocker; Astra bounded IK design)
# ---------------------------------------------------------------------------

def ik_operator(primary="null", joints=(u"DmeDag", u"DmeDag", u"DmeDag")):
    """A DmeRigIKConstraintOperator as in the native rig: three joint slaves and, by default, a primary slave
    whose target attribute is present and null. `primary` selects one representation variation."""
    attrs = {}
    for slave_attr, target_type in zip(("startJoint", "midJoint", "endJoint"), joints):
        if target_type == "absent":
            continue
        tgt = m05.FakeElement(target_type, u"bone") if target_type else None
        attrs[slave_attr] = m05.FakeElement(u"DmeConstraintSlave", u"joint", target=tgt)
    op = operator(u"DmeRigIKConstraintOperator", u"ikConstraint_zk", **attrs)
    if primary == "no_slave":
        return op
    if primary == "null_slave":
        op.put("slave", None)
        return op
    slave = m05.FakeElement(u"DmeConstraintSlave", u"primary", target=None)
    op.put("slave", slave)
    if primary == "absent_target":
        slave.drop("target")
    elif primary == "unreadable_target":
        make_unreadable(slave, "target")
    elif primary == "unsupported_target":
        slave.put("target", m05.FakeElement(u"DmeGlobalFlexControllerOperator", u"flexop"))
    elif primary == "resolved":
        slave.put("target", m05.FakeElement(u"DmeDag", u"dag"))
    elif primary == "wrong_type":
        op.put("slave", m05.FakeElement(u"DmElement", u"notslave", target=None))
    elif primary == "unreadable_slave":
        make_unreadable(op, "slave")
    elif primary == "slave_type_unreadable":
        native_type_fails(slave)
    elif primary == "slave_identity_unreadable":
        native_identity_fails(slave)
    return op


def ik_type_unreadable():
    op = ik_operator()
    native_type_fails(op)
    return op


IK_REFUSALS = [
    ("primary slave attribute absent", lambda: [ik_operator("no_slave")]),
    ("primary slave null", lambda: [ik_operator("null_slave")]),
    ("primary slave unreadable", lambda: [ik_operator("unreadable_slave")]),
    ("primary slave not a DmeConstraintSlave", lambda: [ik_operator("wrong_type")]),
    ("primary slave native type unreadable", lambda: [ik_operator("slave_type_unreadable")]),
    ("primary slave identity unreadable", lambda: [ik_operator("slave_identity_unreadable")]),
    ("primary target attribute absent", lambda: [ik_operator("absent_target")]),
    ("primary target unreadable", lambda: [ik_operator("unreadable_target")]),
    ("primary target unsupported (flex controller)", lambda: [ik_operator("unsupported_target")]),
    ("start joint target null", lambda: [ik_operator(joints=(None, u"DmeDag", u"DmeDag"))]),
    ("mid joint target null", lambda: [ik_operator(joints=(u"DmeDag", None, u"DmeDag"))]),
    ("end joint target null", lambda: [ik_operator(joints=(u"DmeDag", u"DmeDag", None))]),
    ("end joint slave absent", lambda: [ik_operator(joints=(u"DmeDag", u"DmeDag", "absent"))]),
    ("joint target unsupported", lambda: [ik_operator(joints=(u"DmeDag", u"DmeGlobalFlexControllerOperator",
                                                               u"DmeDag"))]),
    ("joint null beside a resolved primary", lambda: [ik_operator("resolved", (u"DmeDag", None, u"DmeDag"))]),
    ("point constraint with a null target", lambda: [constraint(u"DmeRigPointConstraintOperator", target=False)]),
    ("orient constraint with a null target", lambda: [constraint(u"DmeRigOrientConstraintOperator", target=False)]),
    ("IK operator native type unreadable", lambda: [ik_type_unreadable()]),
    ("valid IK beside an invalid IK", lambda: [ik_operator(), ik_operator("absent_target")]),
]


def attempt(fn):
    """(result, exception) without letting one failure abort the section."""
    try:
        return fn(), None
    except Exception as exc:
        return None, exc


def ik_scene(factory, scale=False):
    """A fresh scene whose operators are built INSIDE it (registered for the fake Undo snapshot)."""
    s = scene(scale=scale)
    ops = factory()
    s.animset.put("operators", list(s.animset.raw("operators")) + list(ops))
    return s, ops


def section_ik(ns):
    # Admission: verified-null primary with resolved joints (several, like the native rig).
    s, _ = ik_scene(lambda: [ik_operator(), ik_operator(), ik_operator()])
    s.mono(u"zk_other", 0.2)
    s.mono(u"zk_target", 0.5, stored=0.0)
    index = ns["prod_flex_writer_index"]()
    st = side_state(ns, u"zk_target")
    check("IK verified-unbound primary: discovery complete, zero unresolved, counted 3, side admitted",
          index["complete"] is True and index["unresolved_count"] == 0 and index.get("ik_unbound_primary") == 3
          and ns["state_kind"](st) == STATIC and st["writers_complete"] is True,
          (index["unresolved"], index.get("ik_unbound_primary"), ns["state_kind"](st)))
    before = s.digest()
    path, exc = attempt(lambda: save(ns))
    saved = m05.Store.files[path]["values"] if path else {}
    check("IK verified-unbound primary: Body Save captures the effective key; no scene change, no write",
          exc is None and saved.get(u"flex.zk_target") == {"representation": u"MONO", "mono": 0.5}
          and s.digest() == before and not s.cpm_writes and not s.dm.stack, (exc, saved.get(u"flex.zk_target")))
    check("IK verified-unbound primary: discovery log reports completion and the count",
          any("M06_FLEX_WRITER_DISCOVERY_COMPLETE" in line and "ik_unbound_primary=3" in line
              for line in m05.Log.lines))
    # The surveyed resolved-primary IK stays admitted and is not counted as unbound.
    s, _ = ik_scene(lambda: [ik_operator("resolved")])
    s.mono(u"zk_target", 0.5, stored=0.0)
    index = ns["prod_flex_writer_index"]()
    check("IK resolved primary: still complete and admitted; not counted as unbound",
          index["complete"] is True and index.get("ik_unbound_primary") == 0
          and ns["state_kind"](side_state(ns, u"zk_target")) == STATIC)
    # Every unsupported variation refuses before mutation.
    for label, ops in IK_REFUSALS:
        s, _ = ik_scene(ops)
        s.mono(u"zk_other", 0.2)
        s.mono(u"zk_target", 0.5, stored=0.0)
        kind = ns["state_kind"](side_state(ns, u"zk_target"))
        before = s.digest()
        exc = raises(lambda: save(ns))
        check("IK refuse %s: not admitted; Save refuses, nothing written" % label,
              kind == "UNSUPPORTED" and exc is not None and not m05.Store.writes and s.digest() == before
              and not s.cpm_writes, (kind, exc))
        exc = raises(lambda: apply(ns, record(s, {u"zk_other": 0.2, u"zk_target": 0.9})))
        check("IK refuse %s: Apply refuses before any transaction" % label,
              exc is not None and "StartUndo" not in s.events and not s.dm.stack and s.digest() == before, exc)
    # Diagnostic clarity: a discovery-caused refusal says so; an unrelated refusal keeps its message.
    s, _ = ik_scene(lambda: [ik_operator("absent_target")])
    s.mono(u"zk_target", 0.5, stored=0.0)
    exc = raises(lambda: save(ns))
    check("Body Save refusal names incomplete writer discovery (original message kept)",
          exc is not None and "Unsupported static" in _TEXT(exc)
          and "writer discovery was incomplete" in _TEXT(exc) and "unresolved" in _TEXT(exc), exc)
    s = scene()
    s.mono(u"zk_target", 0.5, stored=0.0, keys=[[0.0, 0.5], [1.0, 0.5]])
    exc = raises(lambda: save(ns))
    check("Unrelated Body Save refusal keeps its original message",
          exc is not None and "Unsupported static" in _TEXT(exc) and "writer discovery" not in _TEXT(exc), exc)

    # Mid-operation interference with an admitted verified-unbound IK primary.
    injections = [
        ("IK primary target becomes unreadable after the authored write",
         lambda op: make_unreadable(op.raw("slave"), "target")),
        ("IK primary gains an unsupported target after the authored write",
         lambda op: op.raw("slave").put("target", m05.FakeElement(u"DmeGlobalFlexControllerOperator", u"x"))),
        ("IK primary target attribute removed after the authored write",
         lambda op: op.raw("slave").drop("target")),
        ("IK joint target becomes null after the authored write",
         lambda op: op.raw("midJoint").put("target", None)),
    ]
    for label, inject in injections:
        # precommit
        s, (op,) = ik_scene(lambda: [ik_operator()])
        s.mono(u"zp_target", 0.66, stored=0.12)
        s.mono(u"zp_other", 0.25)
        before = s.digest()
        real_write = ns["write_side"]

        def write_then_inject(binding, side, origin, desired, op=op, real_write=real_write):
            real_write(binding, side, origin, desired)
            if binding["literal"] == u"zp_target":
                inject(op)
        ns["write_side"] = write_then_inject
        exc = raises(lambda: apply(ns, record(s, {u"zp_target": 0.3, u"zp_other": 0.25})))
        ns["write_side"] = real_write
        check("%s (precommit): Apply never committed-verified; transaction aborted" % label,
              exc is not None and "precommit" in _TEXT(exc) and not s.dm.stack and s.digest() == before, exc)
        # postcommit
        s, (op,) = ik_scene(lambda: [ik_operator()])
        s.mono(u"zp_target", 0.66, stored=0.12)
        s.mono(u"zp_other", 0.25)
        real_refresh = ns["same_time_refresh"]

        def refresh_then_inject(head_time, lbl, op=op, real_refresh=real_refresh):
            real_refresh(head_time, lbl)
            inject(op)
        ns["same_time_refresh"] = refresh_then_inject
        result, exc = attempt(lambda: apply(ns, record(s, {u"zp_target": 0.3, u"zp_other": 0.25})))
        ns["same_time_refresh"] = real_refresh
        check("%s (postcommit): committed-unverified, never committed-verified" % label,
              exc is None and result["phase"] == u"committed-unverified" and len(s.dm.stack) == 1,
              exc or result["phase"])
        # deferred
        s, (op,) = ik_scene(lambda: [ik_operator()], scale=True)
        s.mono(u"zp_target", 0.66, stored=0.12)
        rows = m05_bone_rows(s)
        crest = [r for r in rows if r[1] == u"zz_crest"][0]
        result, exc = attempt(lambda: apply(ns, record(s, {u"zp_target": 0.3},
                                                    scales={(crest[0], crest[1]): 1.25})))
        out = None
        if exc is None:
            s.event_turn()
            inject(op)
            out = ns["prod_apply_deferred_verify"](result["pending"])
        check("%s (deferred): committed-unverified (flex)" % label,
              exc is None and result["phase"] == u"verification-pending" and out["phase"] == u"committed-unverified"
              and out.get("reason") == u"flex", exc or out)
    # Control: with no interference the same IK scene commits verified (the injections are what fail).
    s, _ = ik_scene(lambda: [ik_operator()])
    s.mono(u"zp_target", 0.66, stored=0.12)
    s.mono(u"zp_other", 0.25)
    result, exc = attempt(lambda: apply(ns, record(s, {u"zp_target": 0.3, u"zp_other": 0.25})))
    check("IK verified-unbound primary: uninterrupted changed Apply is committed-verified",
          exc is None and result["phase"] == u"committed-verified", exc or result["phase"])


# ---------------------------------------------------------------------------
# Native missing-attribute reader (SFM vs wrapper; native diagnostic staticplay_diag_001)
# ---------------------------------------------------------------------------

class _PAttr(object):
    """A probe attribute object: GetValue returns `value` or raises `exc`."""

    def __init__(self, value=None, exc=None):
        self.value = value
        self.exc = exc

    def GetValue(self):
        if self.exc is not None:
            raise self.exc
        return self.value


class _PElement(object):
    """A probe element with independently scripted accessors. getter / presence: ("return", v) | ("raise", exc) |
    "missing" (no accessor) | "notcallable". Every accessor call records the name it received."""

    def __init__(self, getter, presence):
        self.calls = []
        for method, spec in (("GetAttribute", getter), ("HasAttribute", presence)):
            if spec == "missing":
                continue
            if spec == "notcallable":
                setattr(self, method, 5)
                continue
            setattr(self, method, self._accessor(method, spec))

    def _accessor(self, method, spec):
        def accessor(attr_name):
            self.calls.append((method, attr_name))
            if spec[0] == "raise":
                raise spec[1]
            return spec[1]
        return accessor


class _RaisingAccess(object):
    """Element whose accessor lookup itself fails."""

    @property
    def GetAttribute(self):
        raise RuntimeError("accessor lookup failed")

    def HasAttribute(self, attr_name):
        return False


def reader_matrix():
    V = object()
    AE = AttributeError("No such attribute")
    rows = [
        # (label, getter, presence, expected state, expected value or V)
        ("missing: getter raises AttributeError, HasAttribute False", ("raise", AE), ("return", False), u"absent", None),
        ("legacy missing: getter returns None, HasAttribute False", ("return", None), ("return", False), u"absent",
         None),
        ("present value preserved", ("return", _PAttr(V)), ("return", True), u"present", V),
        ("present-null stays present (value None)", ("return", _PAttr(None)), ("return", True), u"present", None),
        ("contradiction: getter raises AttributeError, HasAttribute True", ("raise", AE), ("return", True),
         u"unreadable", None),
        ("contradiction: getter returns None, HasAttribute True", ("return", None), ("return", True), u"unreadable",
         None),
        ("contradiction: getter succeeds, HasAttribute False", ("return", _PAttr(V)), ("return", False),
         u"unreadable", None),
        ("HasAttribute raises (absence candidate)", ("raise", AE), ("raise", RuntimeError("x")), u"unreadable", None),
        ("HasAttribute raises AttributeError (absence candidate)", ("raise", AE), ("raise", AttributeError("x")),
         u"unreadable", None),
        ("HasAttribute raises (present getter)", ("return", _PAttr(V)), ("raise", RuntimeError("x")), u"unreadable",
         None),
        ("HasAttribute accessor missing", ("raise", AE), "missing", u"unreadable", None),
        ("HasAttribute not callable", ("return", _PAttr(V)), "notcallable", u"unreadable", None),
        ("GetAttribute accessor missing", "missing", ("return", False), u"unreadable", None),
        ("GetAttribute not callable", "notcallable", ("return", False), u"unreadable", None),
        ("getter raises RuntimeError with HasAttribute False", ("raise", RuntimeError("x")), ("return", False),
         u"unreadable", None),
        ("getter raises KeyError with HasAttribute False", ("raise", KeyError("x")), ("return", False), u"unreadable",
         None),
        ("getter raises TypeError with HasAttribute False", ("raise", TypeError("x")), ("return", False),
         u"unreadable", None),
        ("GetValue raises RuntimeError", ("return", _PAttr(exc=RuntimeError("x"))), ("return", True), u"unreadable",
         None),
        ("GetValue raises AttributeError (never absent)", ("return", _PAttr(exc=AttributeError("x"))),
         ("return", True), u"unreadable", None),
        ("malformed attribute object (no GetValue)", ("return", object()), ("return", True), u"unreadable", None),
        ("exception message is not inspected: other AttributeError text, HasAttribute False",
         ("raise", AttributeError("something else")), ("return", False), u"absent", None),
    ]
    for presence in (0, 1, None, "False", u"", [], 0.0):
        rows.append(("non-Boolean presence %r (absence candidate)" % (presence,), ("raise", AE),
                     ("return", presence), u"unreadable", None))
    for presence in (1, "True"):
        rows.append(("non-Boolean presence %r (present getter)" % (presence,), ("return", _PAttr(V)),
                     ("return", presence), u"unreadable", None))
    for falsy in (0, u"", [], 0.0, False):
        rows.append(("present falsy value %r preserved uncoerced" % (falsy,), ("return", _PAttr(falsy)),
                     ("return", True), u"present", falsy))
    return rows, V


def contradict(element, attr_name, mode):
    """A contradictory accessor state for one attribute, as scene data (restored by the fake Undo)."""
    element.put(u"#contradict:" + attr_name, mode)


def contradict_persistent(element, attr_name, mode):
    """The same contradiction as instance-level accessor overrides: NOT scene data, so no Undo restores it."""
    real_get, real_has = element.GetAttribute, element.HasAttribute

    def matches(name):
        if isinstance(name, bytes):
            name = name.decode("ascii")
        return name == attr_name

    def get(name):
        if matches(name):
            if mode in ("raise_but_has", "has_non_bool", "has_raises"):
                raise AttributeError("No such attribute")
            if mode == "none_but_has":
                return None
            if mode == "present_but_not_has":
                return m05.FakeAttr(element, attr_name, None)
        return real_get(name)

    def has(name):
        if matches(name):
            if mode in ("raise_but_has", "none_but_has"):
                return True
            if mode == "present_but_not_has":
                return False
            if mode == "has_non_bool":
                return 0
            if mode == "has_raises":
                raise RuntimeError("presence unreadable")
        return real_has(name)
    element.GetAttribute = get
    element.HasAttribute = has


def legacy_getter(element):
    """The element's getter returns None for a missing attribute (explicit getter-returns-None representation)."""
    element.GetAttribute = lambda name: element._lookup_attribute(name)


def hide(element, attr_name):
    """The attribute verifiably does not exist (native: getter raises, HasAttribute False)."""
    real = element._lookup_attribute

    def lookup(name, real=real):
        if isinstance(name, bytes):
            name = name.decode("ascii")
        return None if name == attr_name else real(name)
    element._lookup_attribute = lookup


def section_reader(ns):
    read = ns["prod_flex_strict_read"]

    # 1. Reader contract matrix.
    rows, V = reader_matrix()
    for label, getter, presence, want_state, want_value in rows:
        el = _PElement(getter, presence)
        state, value = read(el, u"curveinfo")
        ok = state == want_state and (value is want_value if want_value is V or want_value is None
                                      else (value == want_value and type(value) is type(want_value)))
        check("R reader: %s -> %s" % (label, want_state), ok, (state, value))
    check("R reader: element None -> unreadable", read(None, u"curveinfo") == (u"unreadable", None))
    check("R reader: accessor lookup failure -> unreadable", read(_RaisingAccess(), u"curveinfo") == (u"unreadable", None))
    el = _PElement(("raise", AttributeError("No such attribute")), ("return", False))
    read(el, u"curveinfo")
    names = [c[1] for c in el.calls]
    check("R reader: GetAttribute and HasAttribute receive the identical converted native name",
          [c[0] for c in el.calls] == ["GetAttribute", "HasAttribute"] and names[0] == names[1]
          and type(names[0]) is type(names[1]) and names[0] == ns["native_attr_name"](u"curveinfo"), el.calls)
    el = _PElement(("return", _PAttr(1)), ("return", True))
    check("R reader: absent / unreadable states feed strict_list and strict_state unchanged",
          ns["prod_flex_strict_list"](_PElement(("raise", AttributeError("x")), ("return", False)), "bookmarks")
          == (u"absent", None)
          and ns["prod_flex_strict_list"](_PElement(("raise", AttributeError("x")), ("return", True)), "bookmarks")
          == (u"unreadable", None)
          and ns["prod_flex_strict_state"](_PElement(("raise", AttributeError("x")), ("return", False)), "curveinfo")
          == u"absent"
          and ns["prod_flex_strict_state"](_PElement(("return", _PAttr(None)), ("return", True)), "curveinfo")
          == u"null")

    # 2. Native-faithful fakes.
    s = scene()
    d = s.mono(u"zr_target", 0.5, stored=0.0)
    exc = raises(lambda: d["layer"].GetAttribute("curveinfo"))
    check("R fakes: a missing attribute raises AttributeError and reports HasAttribute False (as the vs wrapper)",
          isinstance(exc, AttributeError) and d["layer"].HasAttribute("curveinfo") is False, exc)
    make_unreadable(d["layer"], "compressed")
    check("R fakes: a present-unreadable attribute reports HasAttribute True and its getter returns it",
          d["layer"].HasAttribute("compressed") is True
          and raises(lambda: d["layer"].GetAttribute("compressed").GetValue()) is not None)
    check("R fakes: synthesized key arrays report HasAttribute True",
          d["layer"].HasAttribute("times") is True and d["layer"].HasAttribute("values") is True)

    # 3. Optional metadata: verified absence admits; unreadable or contradictory metadata refuses.
    admits = [
        ("layer curve info verified absent (native wrapper)", lambda s, d: None),
        ("layer curve info absent through a getter returning None", lambda s, d: legacy_getter(d["layer"])),
        ("log curve info verified absent", lambda s, d: d["log"].drop("curveinfo")),
        ("curve types verified absent", lambda s, d: d["layer"].drop("curvetypes")),
        ("compressed block verified absent", lambda s, d: d["layer"].drop("compressed")),
        ("bookmarks verified absent", lambda s, d: d["log"].drop("bookmarks")),
    ]
    for label, mutate in admits:
        s = scene()
        s.mono(u"zr_other", 0.2)
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        mutate(s, d)
        st = side_state(ns, u"zr_target")
        exc = raises(lambda: save(ns))
        check("R admit %s: STATIC_PLAY admitted and Save succeeds" % label,
              ns["state_kind"](st) == STATIC and exc is None and len(m05.Store.writes) == 1,
              (ns["state_kind"](st), st.get("layer_curveinfo"), st.get("log_curveinfo"), exc))
    s = scene()
    d = s.mono(u"zr_target", 0.5, stored=0.0)
    st = side_state(ns, u"zr_target")
    check("R admit: native-absent layer curve info is recorded as absent (never unreadable)",
          st.get("layer_curveinfo") == u"absent" and st.get("log_curveinfo") == u"null", st.get("layer_curveinfo"))

    refusals = [("layer curve info unreadable", lambda s, d: make_unreadable(d["layer"], "curveinfo"))]
    for owner in ("layer", "log"):
        for mode in ("raise_but_has", "none_but_has", "present_but_not_has", "has_non_bool", "has_raises"):
            refusals.append(("%s curve info contradictory (%s)" % (owner, mode),
                             lambda s, d, owner=owner, mode=mode: contradict(d[owner], "curveinfo", mode)))
    refusals += [("curve types contradictory (raise_but_has)",
                  lambda s, d: contradict(d["layer"], "curvetypes", "raise_but_has")),
                 ("compressed contradictory (none_but_has)",
                  lambda s, d: contradict(d["layer"], "compressed", "none_but_has")),
                 ("bookmarks presence non-Boolean", lambda s, d: contradict(d["log"], "bookmarks", "has_non_bool"))]
    # Required evidence: verified absence still refuses.
    refusals += [
        ("channel fromIndex missing", lambda s, d: d["channel"].drop("fromIndex")),
        ("channel toIndex missing", lambda s, d: d["channel"].drop("toIndex")),
        ("channel mode missing", lambda s, d: d["channel"].drop("mode")),
        ("channel fromElement missing", lambda s, d: d["channel"].drop("fromElement")),
        ("channel fromAttribute missing", lambda s, d: d["channel"].drop("fromAttribute")),
        ("log usedefaultvalue missing", lambda s, d: d["log"].drop("usedefaultvalue")),
        ("log defaultvalue missing", lambda s, d: d["log"].drop("defaultvalue")),
        ("layer key times missing", lambda s, d: hide(d["layer"], "times")),
        ("layer key values missing", lambda s, d: hide(d["layer"], "values")),
        ("destination gameModel association missing", lambda s, d: d["dest"].drop("gameModel")),
        ("model globalFlexControllers missing", lambda s, d: s.flex_model.drop("globalFlexControllers")),
        ("channels clip channels missing (required traversal array)",
         lambda s, d: setattr(s, "discovery_break", "track-children")),
    ]
    for label, mutate in refusals:
        s = scene()
        s.mono(u"zr_other", 0.2)
        d = s.mono(u"zr_target", 0.5, stored=0.0)
        mutate(s, d)
        before = s.digest()
        kind = ns["state_kind"](side_state(ns, u"zr_target"))
        exc = raises(lambda: save(ns))
        check("R refuse %s: not admitted; Save refuses, nothing written" % label,
              kind == "UNSUPPORTED" and exc is not None and not m05.Store.writes and s.digest() == before,
              (kind, exc))

    # Constraint relationships: an absent IK primary target stays distinct from a present-null one.
    s, _ = ik_scene(lambda: [ik_operator()])
    s.mono(u"zr_target", 0.5, stored=0.0)
    st = side_state(ns, u"zr_target")
    w = ns["prod_flex_writer_index"]()
    check("R IK: present-null primary target is verified unbound (admitted)",
          ns["state_kind"](st) == STATIC and w["complete"] and w["ik_unbound_primary"] == 1, w.get("unresolved"))
    s, _ = ik_scene(lambda: [ik_operator("absent_target")])
    s.mono(u"zr_target", 0.5, stored=0.0)
    w = ns["prod_flex_writer_index"]()
    check("R IK: absent primary target is not treated as null (discovery incomplete, refused)",
          not w["complete"] and w["ik_unbound_primary"] == 0
          and ns["state_kind"](side_state(ns, u"zr_target")) == "UNSUPPORTED", w.get("unresolved"))
    s, _ = ik_scene(lambda: [ik_operator(joints=(u"DmeDag", u"DmeDag", "absent"))])
    s.mono(u"zr_target", 0.5, stored=0.0)
    w = ns["prod_flex_writer_index"]()
    check("R IK: absent end-joint slave stays unresolved", not w["complete"] and w["ik_unbound_primary"] == 0,
          w.get("unresolved"))

    # 4. Transactions: metadata turning unreadable or contradictory during Apply never verifies.
    injections = [
        ("layer curve info becomes unreadable", lambda d: make_unreadable(d["layer"], "curveinfo")),
        ("layer curve info becomes contradictory", lambda d: contradict(d["layer"], "curveinfo", "raise_but_has")),
        ("layer curve info presence becomes non-Boolean",
         lambda d: contradict(d["layer"], "curveinfo", "has_non_bool")),
        ("log curve info becomes contradictory", lambda d: contradict(d["log"], "curveinfo", "present_but_not_has")),
    ]
    for label, inject in injections:
        for variant in ("changed side", "unchanged static side"):
            target = u"zp_target" if variant == "changed side" else u"zp_static"

            def build(scale=False):
                s = scene(scale=scale)
                sides = {u"zp_target": s.mono(u"zp_target", 0.66, stored=0.12),
                         u"zp_static": s.mono(u"zp_static", 0.4, stored=0.0)}
                s.mono(u"zp_other", 0.25)
                return s, sides
            desired = {u"zp_target": 0.3, u"zp_static": 0.4, u"zp_other": 0.25}
            # precommit
            s, sides = build()
            before = s.digest()
            real_write = ns["write_side"]

            def write_then_inject(binding, side, origin, want, sides=sides, inject=inject, real_write=real_write,
                                  target=target):
                real_write(binding, side, origin, want)
                if binding["literal"] == u"zp_target":
                    inject(sides[target])
            ns["write_side"] = write_then_inject
            exc = raises(lambda: apply(ns, record(s, desired)))
            ns["write_side"] = real_write
            check("R txn %s, %s (precommit): never committed-verified; aborted; exact baseline restored"
                  % (label, variant),
                  exc is not None and "precommit" in _TEXT(exc) and not s.dm.stack and s.digest() == before, exc)
            # synchronous postcommit
            s, sides = build()
            real_refresh = ns["same_time_refresh"]

            def refresh_then_inject(head_time, lbl, sides=sides, inject=inject, real_refresh=real_refresh,
                                    target=target):
                real_refresh(head_time, lbl)
                inject(sides[target])
            ns["same_time_refresh"] = refresh_then_inject
            result, exc = attempt(lambda: apply(ns, record(s, desired)))
            ns["same_time_refresh"] = real_refresh
            check("R txn %s, %s (postcommit): committed-unverified, never committed-verified" % (label, variant),
                  exc is None and result["phase"] == u"committed-unverified" and len(s.dm.stack) == 1,
                  exc or result["phase"])
            # deferred
            s, sides = build(scale=True)
            rows_ = m05_bone_rows(s)
            crest = [r for r in rows_ if r[1] == u"zz_crest"][0]
            result, exc = attempt(lambda: apply(ns, record(s, desired, scales={(crest[0], crest[1]): 1.25})))
            if exc is None:
                s.event_turn()
                inject(sides[target])
                out, exc = attempt(lambda: ns["prod_apply_deferred_verify"](result["pending"]))
            check("R txn %s, %s (deferred): committed-unverified (flex)" % (label, variant),
                  exc is None and result["phase"] == u"verification-pending"
                  and out["phase"] == u"committed-unverified" and out.get("reason") == u"flex",
                  exc or (result["phase"], out))

    # A contradiction that no Undo can restore: the abort's exact baseline comparison fails, so recovery is
    # reported unverified (never success, never a claimed restoration).
    for owner, mode in (("layer", "raise_but_has"), ("layer", "has_non_bool"), ("log", "present_but_not_has")):
        s = scene()
        sides = {u"zp_target": s.mono(u"zp_target", 0.66, stored=0.12)}
        s.mono(u"zp_other", 0.25)
        real_write = ns["write_side"]

        def write_then_persist(binding, side, origin, want, sides=sides, owner=owner, mode=mode,
                               real_write=real_write):
            real_write(binding, side, origin, want)
            if binding["literal"] == u"zp_target":
                contradict_persistent(sides[u"zp_target"][owner], "curveinfo", mode)
        ns["write_side"] = write_then_persist
        exc = raises(lambda: apply(ns, record(s, {u"zp_target": 0.3, u"zp_other": 0.25})))
        ns["write_side"] = real_write
        check("R txn persistent %s curve info contradiction (%s) at precommit: recovery reported unverified"
              % (owner, mode),
              exc is not None and type(exc).__name__ == "ProdRecoveryUnverifiedError" and not s.dm.stack, exc)

    # Uninterrupted control: the same scene with native-absent layer curve info verifies.
    s = scene()
    s.mono(u"zp_target", 0.66, stored=0.12)
    s.mono(u"zp_static", 0.4, stored=0.0)
    s.mono(u"zp_other", 0.25)
    result, exc = attempt(lambda: apply(ns, record(s, {u"zp_target": 0.3, u"zp_static": 0.4, u"zp_other": 0.25})))
    check("R txn control: uninterrupted Apply with native-absent layer curve info is committed-verified",
          exc is None and result["phase"] == u"committed-verified", exc or result["phase"])


WINDOW = None


def main():
    global WINDOW
    print("Interpreter: %s" % sys.version.split()[0])
    app = route.AppSource(route.APP_PATH)
    import hashlib
    print("Candidate app sha256: %s" % hashlib.sha256(app.raw).hexdigest())
    m05.APP = app
    ns, methods = build_namespace(app)
    WINDOW = m05.make_window_class(methods)
    for section in (lambda: section_classification(ns), lambda: section_save(ns), lambda: section_apply(ns),
                    lambda: section_failures(ns), lambda: section_baseline(ns), lambda: section_refusals(ns),
                    lambda: section_m05(ns), lambda: section_isolation(ns, app), lambda: section_p1(ns),
                    lambda: section_ik(ns), lambda: section_reader(ns)):
        try:
            section()
        except Exception:
            check("section.completed", False, traceback.format_exc())
    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    if passed != len(RESULTS):
        sys.exit(1)


if __name__ == "__main__":
    args = dict(a.split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    if args.get("--phase") != "run":
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        sys.exit(2)
    main()
