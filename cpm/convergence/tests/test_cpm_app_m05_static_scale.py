# -*- coding: utf-8 -*-
"""M-05 -- focused offline qualification of the static mode-3 bone-scale
correction in the CPM application source (cpm/app/SFM_Character_Preset_Manager.py).

Design authority: Astra's M-05 production-correction design (2026-10-24), section 7
"Focused offline checks".

Technique (as in the Step 2b/3 suites): the production functions and ProdWindow
methods under test are extracted verbatim by name from the application source and
executed in a namespace whose stubs cover only SFM/Qt/DME boundaries, authority and
library I/O. The scene is a small fake DME graph with a simple evaluation model:
expression results refresh at same_time_refresh, and a mode-3 output reaches the bone
only on a later ordinary event-loop turn (the delayed propagation both closed native
arms observed at CPM's verification boundary). Immediate mode-1 propagation at that
refresh is a stub assumption that keeps the previously supported synchronous path
exercisable; it is NOT a finding of the native experiments (Arm 2, with mode 1, also
showed delayed propagation).

Usage: --phase=run (Python 2.7.5 and Python 3.10). Offline only; nothing here
demonstrates real-SFM behaviour, native Undo/Redo, or Qt zero-timer ordering.
"""
from __future__ import print_function

import ast
import json
import re
import os
import sys
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402

PY2 = sys.version_info[0] == 2
try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

RESULTS = []


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


# ---------------------------------------------------------------------------
# Fake DME scene
# ---------------------------------------------------------------------------

class FakeTime(object):
    def __init__(self, s):
        self.s = float(s)

    def GetSeconds(self):
        return self.s


class FakeAttr(object):
    def __init__(self, owner, attr_name, value):
        self.owner = owner
        self.name = attr_name
        self.value = value

    def GetValue(self):
        return self.value

    def SetValue(self, value):
        Scene.current.cpm_writes.append((self.owner._name, self.name, value))
        self.value = value


class FakeElement(object):
    _next = [1000]

    def __init__(self, type_string, element_name, **attrs):
        FakeElement._next[0] += 1
        self._type = type_string
        self._name = element_name
        self._handle = FakeElement._next[0]
        self.this = self._handle * 16
        self._attrs = {}
        for key in sorted(attrs):
            self._attrs[key] = FakeAttr(self, key, attrs[key])
        if Scene.current is not None:
            Scene.current.elements.append(self)

    def GetTypeString(self):
        return self._type

    def GetName(self):
        return self._name

    def GetHandle(self):
        return self._handle

    def GetAttribute(self, attr_name):
        if isinstance(attr_name, bytes):
            attr_name = attr_name.decode("ascii")
        return self._attrs.get(attr_name)

    # Evaluation / test-side direct state (never recorded as a CPM write).
    def raw(self, attr_name):
        return self._attrs[attr_name].value

    def put(self, attr_name, value):
        if attr_name in self._attrs:
            self._attrs[attr_name].value = value
        else:
            self._attrs[attr_name] = FakeAttr(self, attr_name, value)

    def drop(self, attr_name):
        self._attrs.pop(attr_name, None)


class FakeLayer(FakeElement):
    def __init__(self, element_name, keys):
        FakeElement.__init__(self, u"DmeFloatLogLayer", element_name)
        self.keys = [list(k) for k in keys]

    def GetKeyCount(self):
        return len(self.keys)

    def GetKeyTime(self, index):
        return FakeTime(self.keys[index][0])

    def GetKeyValue(self, index):
        return self.keys[index][1]

    def SetKeyValue(self, index, value):
        Scene.current.cpm_writes.append((self._name, "key%d" % index, value))
        self.keys[index][1] = float(value)


class FakeLog(FakeElement):
    def __init__(self, element_name, layers, use_default=False, log_type=u"DmeFloatLog"):
        FakeElement.__init__(self, log_type, element_name, usedefaultvalue=use_default, defaultvalue=0.0)
        self.layers = layers

    def GetNumLayers(self):
        return len(self.layers)

    def GetLayer(self, index):
        return self.layers[index]

    def IsEmpty(self):
        return all(not layer.keys for layer in self.layers)

    def GetValue(self, t):
        if self.layers and self.layers[0].keys:
            return self.layers[0].keys[0][1]
        return 0.0


class FakeChannel(FakeElement):
    def __init__(self, element_name, log, **attrs):
        FakeElement.__init__(self, u"DmeChannel", element_name, **attrs)
        self.log = log

    def GetLog(self):
        return self.log

    def GetCurrentTime(self):
        return FakeTime(Scene.current.head)

    def Operate(self):
        # Play mode copies the log value at the current time to the destination.
        Scene.current.operate_calls += 1
        if int(self.raw("mode")) == 3 and self.log.layers and self.log.layers[0].keys:
            self.raw("toElement").put(self.raw("toAttribute"), self.log.layers[0].keys[0][1])
        elif int(self.raw("mode")) == 1:
            self.raw("toElement").put(self.raw("toAttribute"),
                                      self.raw("fromElement").raw(self.raw("fromAttribute")))


class FakeTransformControl(FakeElement):
    def __init__(self, element_name, transform):
        FakeElement.__init__(self, u"DmeTransformControl", element_name)
        self.transform = transform

    def GetTransform(self):
        return self.transform


class FakeAnimset(FakeElement):
    def FindControl(self, literal):
        return None


class FakeDataModel(object):
    def __init__(self, scene):
        self.scene = scene
        self.stack = []
        self.open = None
        self.undo_calls = 0
        self.redo_calls = 0
        self.abort_restores = True
        self.after_abort = None

    def IsUndoEnabled(self):
        return True

    def GetUndoItemCount(self):
        return len(self.stack)

    def GetUndoDesc(self):
        return self.stack[-1][0] if self.stack else u""

    def StartUndo(self, label, redo):
        self.open = (label, redo, self.scene.capture())
        self.scene.events.append("StartUndo")

    def FinishUndo(self):
        label, redo, before = self.open
        self.stack.append((label, redo, before))
        self.open = None
        self.scene.events.append("FinishUndo")

    def AbortUndoableOperation(self):
        label, redo, before = self.open
        if self.abort_restores:
            self.scene.restore(before)
        if self.after_abort is not None:
            self.after_abort(self.scene)
        self.open = None
        self.scene.events.append("AbortUndo")

    def Undo(self):
        self.undo_calls += 1

    def Redo(self):
        self.redo_calls += 1


class Scene(object):
    current = None

    def __init__(self):
        Scene.current = self
        self.elements = []
        self.cpm_writes = []
        self.events = []
        self.operate_calls = 0
        self.head = 0.375
        self.context_ok = True
        self.channels = []
        self.controls = []
        self.operators = []
        self.flex = {u"Smile": 0.25}
        self.flex_baseline = None
        self.created = []
        self.animset = FakeAnimset(u"DmeAnimationSet", u"Krystal")
        self.group = FakeElement(u"DmeControlGroup", u"Body", controls=[])
        self.dm = FakeDataModel(self)

    # --- construction -----------------------------------------------------
    def bone(self, index, bone_name, scale=None):
        attrs = {} if scale is None else {"scale": scale}
        transform = FakeElement(u"DmeTransform", u"bone %d (%s)" % (index, bone_name), **attrs)
        control = FakeTransformControl(bone_name, transform)
        self.controls.append(control)
        self.group.put("controls", self.group.raw("controls") + [control])
        return transform

    def scale_graph(self, transform, bone_name, native, output_mode=3, out_keys=(), use_default=False,
                    in_keys=None, in_layers=1, out_layers=1, out_log_type=u"DmeFloatLog", physical=None,
                    expr_text=u"lerp(value, lo, hi)", lo=0.0, hi=10.0):
        literal = bone_name + u"_scale"
        control = FakeElement(u"DmElement", literal, value=native, defaultValue=0.1)
        self.controls.append(control)
        expression = FakeElement(u"DmeExpressionOperator", literal + u"_rescale", expr=expr_text, lo=lo, hi=hi,
                                 value=native, result=lo + native * (hi - lo))
        self.operators.append(expression)
        keys = [(0.0, native)] if in_keys is None else in_keys
        in_log = FakeLog(literal + u"_log", [FakeLayer(literal + u"_layer%d" % i, keys if i == 0 else [])
                                             for i in range(in_layers)])
        input_channel = FakeChannel(literal, in_log, mode=3, fromElement=control, fromAttribute=u"value",
                                    toElement=expression, toAttribute=u"value")
        out_log = FakeLog(u"scaled_" + literal + u"_log",
                          [FakeLayer(u"scaled_" + literal + u"_layer%d" % i, list(out_keys) if i == 0 else [])
                           for i in range(out_layers)], use_default=use_default, log_type=out_log_type)
        output = FakeChannel(u"scaled_" + literal + u"_channel", out_log, mode=output_mode, fromElement=expression,
                             fromAttribute=u"result", toElement=transform, toAttribute=u"scale")
        self.channels.extend([input_channel, output])
        transform.put("scale", lo + native * (hi - lo) if physical is None else physical)
        return {"control": control, "expression": expression, "input": input_channel, "output": output,
                "transform": transform}

    # --- SFM evaluation model --------------------------------------------
    def refresh(self):
        """same_time_refresh: operators evaluate; a mode-1 output reaches the bone."""
        for expression in self.operators:
            lo, hi = expression.raw("lo"), expression.raw("hi")
            expression.put("result", lo + expression.raw("value") * (hi - lo))
        for channel in self.channels:
            if channel.raw("toAttribute") == u"scale" and int(channel.raw("mode")) == 1:
                channel.raw("toElement").put("scale", channel.raw("fromElement").raw("result"))

    def event_turn(self):
        """An ordinary event-loop turn: a mode-3 (empty, non-default) output reaches the bone."""
        for channel in self.channels:
            if (channel.raw("toAttribute") == u"scale" and int(channel.raw("mode")) == 3
                    and channel.log.IsEmpty() and not channel.log.raw("usedefaultvalue")):
                channel.raw("toElement").put("scale", channel.raw("fromElement").raw("result"))

    # --- undo snapshot ----------------------------------------------------
    def capture(self):
        state = {}
        for element in self.elements:
            for key, attr in element._attrs.items():
                state[(element._handle, key)] = attr.value
            if isinstance(element, FakeLayer):
                state[(element._handle, "#keys")] = [list(k) for k in element.keys]
        return {"attrs": state, "flex": dict(self.flex)}

    def restore(self, snap):
        for element in self.elements:
            for key in list(element._attrs.keys()):
                if (element._handle, key) in snap["attrs"]:
                    element._attrs[key].value = snap["attrs"][(element._handle, key)]
            if isinstance(element, FakeLayer) and (element._handle, "#keys") in snap["attrs"]:
                element.keys = [list(k) for k in snap["attrs"][(element._handle, "#keys")]]
        self.flex = dict(snap["flex"])

    def digest(self):
        snap = self.capture()
        return json.dumps(sorted((repr(k), repr(v)) for k, v in snap["attrs"].items()) + [repr(sorted(snap["flex"].items()))])


def krystal_scene(head_mode=3, spine=True, **head_kw):
    scene = Scene()
    scene.bone(0, u"bip_pelvis")
    head = scene.bone(55, u"bip_head")
    scene.head_graph = scene.scale_graph(head, u"bip_head", 0.113, output_mode=head_mode, **head_kw)
    if spine:
        spine_t = scene.bone(3, u"bip_spine")
        scene.spine_graph = scene.scale_graph(spine_t, u"bip_spine", 0.1, output_mode=1)
    return scene


IDENTITY = {"model": u"models/krystal/krystal2020.mdl", "checksum": 1234, "animset_name": u"Krystal"}


def body_record(head=1.25, pelvis=1.0, spine=1.0, smile=0.25, with_spine=True):
    scales = [
        {"bone_index": 0, "bone_name": u"bip_pelvis", "representation": u"uniform_local_scale_multiplier",
         "value": pelvis, "capture_state": u"implicit-neutral"},
        {"bone_index": 55, "bone_name": u"bip_head", "representation": u"uniform_local_scale_multiplier",
         "value": head, "capture_state": u"existing-static-control"},
    ]
    if with_spine:
        scales.insert(1, {"bone_index": 3, "bone_name": u"bip_spine",
                          "representation": u"uniform_local_scale_multiplier", "value": spine,
                          "capture_state": u"existing-static-control"})
    return {"kind": u"body", "name": u"T", "preset_id": u"preset-1", "values": {u"flex.Smile": smile},
            "bone_scales": scales}


# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------

TOP_EXTRACT = [
    # shared DME helpers
    "u", "b", "native_attr_name", "name", "typ", "dme_id", "same_dme", "get_attr", "attr_value", "arr",
    "as_float", "close_enough", "seconds", "handle", "ptr", "key_count", "layer_count", "get_layer",
    "EPSILON", "dm", "undo_state", "P03_KIND_BODY", "P04_SCALE_LOGICAL_ID",
    # bone-scale definition, traces, capture and parity
    "PROD_BS_BONE_RE", "PROD_BS_VARY_KEY_LIMIT", "prod_bs_group_paths", "prod_bs_scale_channels",
    "prod_bs_bone_rows", "prod_bs_log_state", "prod_bs_control_membership", "prod_bs_trace_scaled_bone",
    "prod_bs_channel_log_ids", "prod_bs_snapshot", "prod_bs_static_one_key_zero", "prod_bs_expected_physical", "prod_bs_authored_matches",
    "prod_bs_evaluated_matches", "prod_bs_names", "PROD_BS_STATIC_PASS", "PROD_BS_STATIC_PLAY", "prod_bs_mode",
    "prod_bs_keyed_evidence", "prod_bs_static_play_evidence", "prod_bs_classify_static_scale",
    "prod_bs_static_scale_trace", "prod_bs_static_pass_trace", "prod_bs_full_bone_scale_map",
    "prod_bs_bone_record_index", "prod_bs_write_existing_scale", "prod_bs_index_snapshot",
    "prod_bs_index_log_state", "prod_bs_index_trace", "prod_bs_index_binding", "prod_bs_index_clean_fixture",
    "prod_bs_index_validate_saved_map", "prod_bs_index_build_plan", "prod_bs_index_verify_saved",
    "prod_bs_index_capture_static_trace", "prod_bone_scale_keys_from_records",
    "prod_validate_bone_scale_map_against_keys", "prod_bs_capture_trace_diagnostic", "prod_bs_index_capture_map",
    "prod_q1_compare_body_capture", "prod_capture_body_snapshot", "prod_capture_bone_scale_map",
    # save / apply / recovery
    "prod_save", "prod_flex_record", "prod_validate_scale_plan_finite", "ProdRecoveryUnverifiedError",
    "prod_optional_float_matches", "prod_bs_snapshot_matches_baseline", "prod_verify_apply_abort_baseline",
    "prod_abort_apply_and_verify", "prod_apply", "PROD_APPLY_CHECKING_COPY", "PROD_APPLY_UNVERIFIED_COPY",
    "prod_apply_deferred_unverified", "prod_bs_play_expectation", "prod_bs_play_expectations_hold",
    "prod_apply_deferred_verify", "prod_outcome", "prod_validate_context_token",
    # logging-only correlation
    "PROD_LOG_NON_MUTATING_LABELS", "PROD_LOG_CONTEXT", "prod_log_operation_begin", "prod_log_note_recovery",
    "prod_log_outcome", "prod_log_refused", "prod_log_operation_end", "prod_log_window_closed",
    "PROD_APP_ATTR",
]

WINDOW_METHODS = [
    "operation_begin", "operation_mark_phase", "operation_revalidate", "operation_commit_state",
    "operation_end", "operation_durable_error_copy", "operation_default_error_copy", "guard", "apply_kind",
    "operation_continuation_owned", "apply_begin_verification", "apply_verification_turn",
    "apply_finish_verification", "apply_close_pending_verification", "closeEvent",
]


class Log(object):
    lines = []
    samples = []


class Timer(object):
    queue = []
    fail = [False]

    @classmethod
    def singleShot(cls, delay, callback):
        if cls.fail[0]:
            raise RuntimeError("synthetic timer failure")
        cls.queue.append((delay, callback))

    @classmethod
    def run_all(cls):
        ran = 0
        while cls.queue:
            delay, callback = cls.queue.pop(0)
            callback()
            ran += 1
        return ran


class _QtCore(object):
    QTimer = Timer


class FakeApp(object):
    """Qt application boundary: state = 'none' | 'modal' | 'unreadable' | 'absent'."""
    state = ["none"]
    modal_queries = [0]

    def activeModalWidget(self):
        FakeApp.modal_queries[0] += 1
        if FakeApp.state[0] == "unreadable":
            raise RuntimeError("modal state unreadable")
        return object() if FakeApp.state[0] == "modal" else None


class _QtGui(object):
    class QApplication(object):
        @staticmethod
        def instance():
            return None if FakeApp.state[0] == "absent" else FakeApp()

    class QDialog(object):
        rejected = []

        @staticmethod
        def reject(window):
            _QtGui.QDialog.rejected.append(window)


class _Vs(object):
    @staticmethod
    def CastElementAsDmeTransformControl(element):
        return element

    @property
    def g_pDataModel(self):
        return Scene.current.dm


class _SfmApp(object):
    @staticmethod
    def GetHeadTimeInSeconds():
        return Scene.current.head

    @staticmethod
    def SetHeadTimeInSeconds(t):
        Scene.current.head = float(t)

    @staticmethod
    def ProcessEvents():
        Scene.current.events.append("ProcessEvents")


class _OperationAuthorityError(RuntimeError):
    pass


def build_namespace(app):
    ns = {"os": os, "sys": sys, "json": json, "math": __import__("math"), "re": __import__("re"),
          "traceback": traceback, "QtCore": _QtCore, "QtGui": _QtGui, "vs": _Vs(), "sfmApp": _SfmApp}
    if not PY2:
        ns["unicode"] = str
        ns["long"] = int
    missing = [name for name in TOP_EXTRACT if name not in app.top]
    check("extraction.every_production_name_present", not missing, missing)
    for name in TOP_EXTRACT:
        if name in missing:
            continue
        route._run_source(app.top_text(name), "app:%s" % name, ns)

    ns["log_line"] = lambda text: Log.lines.append(_TEXT(text))
    ns["prod_resource_snapshot"] = lambda label, *a, **k: Log.samples.append(_TEXT(label))
    # Scene topology boundaries (the indexed/historical traversals above are real).
    ns["prod_bs_find_model_row"] = lambda identity: {"model": IDENTITY["model"], "checksum": IDENTITY["checksum"],
                                                     "animset": Scene.current.animset, "shot": u"shot10"}
    ns["get_channels_clip"] = lambda animset, shot: u"clip"
    ns["r26_clip_channels"] = lambda clip: list(Scene.current.channels)
    ns["prod_bs_animset_controls"] = lambda animset: list(Scene.current.controls)
    ns["r26_animset_controls"] = lambda animset: list(Scene.current.controls)
    ns["r26_animset_operators"] = lambda animset: list(Scene.current.operators)
    ns["group_inventory"] = lambda animset: [{"group": Scene.current.group, "path": u"Body"}]
    ns["same_time_refresh"] = lambda head_time, label: (Scene.current.events.append("refresh"),
                                                        Scene.current.refresh())
    ns["prod_context_token_matches"] = lambda token: Scene.current.context_ok

    def create_graph(fixture, physical):
        Scene.current.created.append((fixture["names"]["literal"], physical))
        graph = Scene.current.scale_graph(fixture["transform"], fixture["bone_row"]["bone_name"],
                                          physical / 10.0, output_mode=1)
        return graph
    ns["prod_bs_create_graph"] = create_graph

    # Authority and FLEX boundaries (not part of M-05).
    ns["prod_cpm_authorize_operation"] = lambda identity, scope, kind, label: {"operation": _TEXT(label),
                                                                               "master_sha256": u"0" * 64}
    ns["prod_live_bindings_for_cached_scope"] = lambda identity, scope, kind, authority_context=None: {
        "accepted": {u"Smile": {"literal": u"Smile"}}}

    def build_plan(accepted, preset):
        Scene.current.flex_baseline = dict(Scene.current.flex)
        desired = preset["values"][u"flex.Smile"]
        needs = not route_close(Scene.current.flex[u"Smile"], desired)
        return {"plan": [{"needs_write": needs, "binding": u"Smile", "side": u"value", "origin": None,
                          "desired": desired}],
                "changed_sides": 1 if needs else 0, "baselines": [u"Smile"]}
    ns["p03_build_plan"] = build_plan

    def write_side(binding, side, origin, desired):
        if Scene.current.fail_flex_write:
            raise RuntimeError("synthetic flex write failure")
        Scene.current.cpm_writes.append((u"flex", binding, desired))
        Scene.current.flex[binding] = desired
    ns["write_side"] = write_side
    ns["p03_verify_saved_values"] = lambda accepted, flex: route_close(Scene.current.flex[u"Smile"],
                                                                       flex["values"][u"flex.Smile"])
    ns["p03_verify_baselines"] = lambda accepted, baselines: route_close(Scene.current.flex[u"Smile"],
                                                                         Scene.current.flex_baseline[u"Smile"])
    # Save boundaries.
    ns["prod_discover"] = lambda identity, kind: []
    ns["prod_assert_unique_preset_name_items"] = lambda items, kind, name: None
    ns["p03_capture_values"] = lambda accepted: ({u"flex.Smile": Scene.current.flex[u"Smile"]}, None)
    ns["uuid"] = type("uuid_stub", (object,), {"uuid4": staticmethod(lambda: type("H", (object,), {"hex": "0" * 32})())})
    ns["prod_key"] = lambda path: _TEXT(path).lower()
    ns["prod_norm"] = lambda path: _TEXT(path).lower()
    ns["PROD_SEMANTIC_POLICY"] = u"master-category-operation-scope-v1"
    ns["prod_provider_capture"] = lambda descriptor: {"provider": u"fixture"}
    ns["p03_now_stamp"] = lambda: u"2026-10-24T00:00:00"
    ns["prod_validate_preset"] = lambda identity, record, kind: None
    ns["prod_ensure_character"] = lambda identity, authority_context=None: None
    ns["prod_unique_path"] = lambda identity, kind, name, pid: u"library/body_preset.json"
    ns["prod_scope"] = lambda identity: {"provider_descriptor": {}}

    def write_json(path, record):
        Store.files[path] = json.loads(json.dumps(record))
        Store.writes.append(path)
    ns["p02_safe_write_json"] = write_json
    ns["p02_read_json"] = lambda path: json.loads(json.dumps(Store.files[path]))
    ns["PROD_Q1_INDEXED_CAPTURE_PARITY"] = False
    # Window boundaries.
    ns["prod_context_token"] = lambda identity: {"token": u"ctx"}
    ns["prod_operation_event_turn_sample"] = lambda oid, label: None
    ns["tool_warning_message"] = lambda window, title, message: window.dialogs.append((title, message))
    ns["ProdCpmOperationAuthorityError"] = _OperationAuthorityError
    ns["prod_reread_selected_record"] = lambda identity, item, kind: json.loads(json.dumps(item["record"]))

    methods = {}
    for name in WINDOW_METHODS:
        route._run_source(app.method_text("ProdWindow", name), "ProdWindow.%s" % name, ns, methods)
    return ns, methods


def route_close(a, b):
    return abs(float(a) - float(b)) <= 1.0e-5


class Store(object):
    files = {}
    writes = []


def make_window_class(methods):
    class FakeEvent(object):
        def __init__(self):
            self.state = None

        def ignore(self):
            self.state = "ignored"

        def accept(self):
            self.state = "accepted"

    class FakeTimerHandle(object):
        def stop(self):
            pass

    class FakeWindow(object):
        def __init__(self, record):
            self.operation = None
            self.operation_generation = 0
            self.busy = False
            self.identity = dict(IDENTITY)
            self.scope = {"authority": {}, "body": {}}
            self.closing_requested = False
            self.scene_activity_suspended = False
            self.fit_active = False
            self.fit_stage_running = False
            self.fit_generation = 0
            self.fit_committed_order = []
            self.modal_deferred_fit_stage = None
            self.modal_watch_timer = FakeTimerHandle()
            self.status_generation = 0
            self.statuses = []
            self.dialogs = []
            self.hidden = 0
            self.closes = 0
            self.log_window_id = 1
            self.record = record

        def current(self):
            return dict(IDENTITY)

        def selected(self, kind):
            return {"source": u"v3", "record": self.record}

        def set_status(self, text, level=u"neutral"):
            self.statuses.append((_TEXT(text), level))

        def hide(self):
            self.hidden += 1

        def close(self):
            self.closes += 1
            event = FakeEvent()
            self.closeEvent(event)
            return event

        def prod_cpm_request_stale_rebuild_if_needed(self):
            return False

    for name, fn in methods.items():
        setattr(FakeWindow, name, fn)
    FakeWindow.FakeEvent = FakeEvent
    return FakeWindow


def reset(scene_factory=krystal_scene, **kw):
    Log.lines[:] = []
    Log.samples[:] = []
    FakeApp.state[0] = "none"
    FakeApp.modal_queries[0] = 0
    Timer.queue[:] = []
    Timer.fail[0] = False
    Store.files.clear()
    Store.writes[:] = []
    scene = scene_factory(**kw)
    scene.fail_flex_write = False
    return scene


def is_pure(value, depth=0):
    if depth > 30:
        return False
    if value is None or isinstance(value, (bool, int, float, _TEXT, str)):
        return True
    if PY2 and isinstance(value, long):  # noqa: F821
        return True
    if isinstance(value, (list, tuple)):
        return all(is_pure(v, depth + 1) for v in value)
    if isinstance(value, dict):
        return all(is_pure(k, depth + 1) and is_pure(v, depth + 1) for k, v in value.items())
    return False


def log_text():
    return u"\n".join(Log.lines)


# ---------------------------------------------------------------------------
# Section A -- one static definition (pure classification)
# ---------------------------------------------------------------------------

def head_trace(ns, scene):
    snapshot = ns["prod_bs_index_snapshot"](IDENTITY)
    row = snapshot["bone_index"][(55, u"bip_head")]
    return ns["prod_bs_index_trace"](snapshot, row)


def section_classification(ns):
    classify = ns["prod_bs_classify_static_scale"]

    scene = reset()
    trace = head_trace(ns, scene)
    check("A1 qualified static mode-3 graph classifies as the output-play static class",
          classify(trace) == (ns["PROD_BS_STATIC_PLAY"], None, None), classify(trace))
    check("A1 historical generic topology still reports False for mode 3 (field unchanged)",
          trace["generic_lerp_topology"] is False)
    check("A1 output log evidence recorded (readable, empty, no default playback)",
          trace["output"]["log"]["use_default_value"] is False and trace["output"]["log"]["key_count"] == 0
          and trace["output"]["log"]["layer_count"] == 1 and trace["output"]["log"]["is_empty"] is True,
          trace["output"]["log"])

    snapshot = ns["prod_bs_index_snapshot"](IDENTITY)
    spine = ns["prod_bs_index_trace"](snapshot, snapshot["bone_index"][(3, u"bip_spine")])
    check("A2 qualified mode-1 graph keeps the historical output-pass class",
          classify(spine) == (ns["PROD_BS_STATIC_PASS"], None, None), classify(spine))

    cases = [
        ("keyed output (one key)", dict(out_keys=[(0.0, 1.0)]), (u"structure", u"unsupported")),
        ("keyed output (varying keys)", dict(out_keys=[(0.0, 1.0), (1.0, 2.0)]), (u"structure", u"time-varying")),
        ("keyed output (equal keys)", dict(out_keys=[(0.0, 1.0), (1.0, 1.0)]), (u"structure", u"unsupported")),
        ("additional output layer", dict(out_layers=2), (u"structure", u"unsupported")),
        ("output plays its default value", dict(use_default=True), (u"structure", u"unsupported")),
        ("non-float output log", dict(out_log_type=u"DmeIntLog"), (u"structure", u"unsupported")),
        ("additional input layer", dict(in_layers=2), (u"structure", u"unsupported")),
        ("time-varying input", dict(in_keys=[(0.0, 0.113), (1.0, 0.2)]), (u"structure", u"time-varying")),
        ("multi-key static input", dict(in_keys=[(0.0, 0.113), (1.0, 0.113)]), (u"structure", u"unsupported")),
        ("input key not at time zero", dict(in_keys=[(0.5, 0.113)]), (u"structure", u"unsupported")),
        ("unsupported expression", dict(expr_text=u"value*hi"), (u"structure", u"unsupported")),
        ("degenerate limits", dict(lo=1.0, hi=1.0), (u"structure", u"unsupported")),
        ("physical scale incoherent", dict(physical=1.5), (u"evaluated", u"incoherent")),
    ]
    for label, kw, expected in cases:
        scene = reset(**kw)
        got = classify(head_trace(ns, scene))
        check("A3 refuse: %s -> %s/%s" % ((label,) + expected), got == (None,) + expected, got)

    # Missing evidence never counts as an empty log.
    scene = reset()
    scene.head_graph["output"].log.drop("usedefaultvalue")
    got = classify(head_trace(ns, scene))
    check("A4 unreadable default-value flag -> structure/unreadable", got == (None, u"structure", u"unreadable"), got)
    scene = reset()
    scene.head_graph["output"].log.IsEmpty = lambda: (_ for _ in ()).throw(RuntimeError("unreadable"))
    got = classify(head_trace(ns, scene))
    check("A4 unreadable output emptiness -> structure/unreadable", got == (None, u"structure", u"unreadable"), got)
    scene = reset()
    scene.head_graph["output"].log.GetLayer = lambda index: None
    got = classify(head_trace(ns, scene))
    check("A4 unreadable output layer -> structure/unreadable", got == (None, u"structure", u"unreadable"), got)
    # An unreadable output mode is refused earlier: the unchanged trace's
    # historical topology flag converts the mode and raises (fail-closed).
    scene = reset()
    scene.head_graph["output"].put("mode", None)
    error = None
    try:
        head_trace(ns, scene)
    except Exception as exc:
        error = exc
    check("A4 unreadable output mode is refused by the unchanged trace (fail-closed)", error is not None, error)
    error = None
    try:
        run_save(ns)
    except Exception as exc:
        error = exc
    check("A4 unreadable output mode: Save refuses without publishing", error is not None and not Store.writes, error)
    check("A4 classifier itself maps an unreadable output mode to structure/unreadable",
          classify({"output": {"mode": None}, "generic_lerp_topology": False}) == (None, u"structure", u"unreadable"))

    # Conflicting writers.
    scene = reset()
    extra = FakeChannel(u"rogue", FakeLog(u"rogue_log", [FakeLayer(u"rogue_layer", [(0.0, 0.2)])]), mode=3,
                        fromElement=scene.head_graph["control"], fromAttribute=u"value",
                        toElement=scene.head_graph["expression"], toAttribute=u"value")
    scene.channels.append(extra)
    got = classify(head_trace(ns, scene))
    check("A5 two writers to the expression input -> structure/conflicting",
          got == (None, u"structure", u"conflicting"), got)
    scene = reset()
    scene.controls.append(scene.head_graph["control"])
    got = classify(head_trace(ns, scene))
    check("A5 control listed twice in the animation set -> structure/conflicting",
          got == (None, u"structure", u"conflicting"), got)
    scene = reset()
    second = FakeChannel(u"rogue_out", FakeLog(u"rogue_out_log", [FakeLayer(u"rogue_out_layer", [])]), mode=3,
                         fromElement=scene.head_graph["expression"], fromAttribute=u"result",
                         toElement=scene.head_graph["transform"], toAttribute=u"scale")
    scene.channels.append(second)
    try:
        head_trace(ns, scene)
        check("A5 a competing bone-scale writer is refused by the trace", False, "no error")
    except RuntimeError as exc:
        check("A5 a competing bone-scale writer is refused by the trace", u"found 2" in _TEXT(exc), _TEXT(exc))

    # Authored incoherence.
    scene = reset()
    scene.head_graph["control"].put("value", 0.2)
    got = classify(head_trace(ns, scene))
    check("A6 key/control disagreement -> authored/incoherent", got == (None, u"authored", u"incoherent"), got)
    scene = reset()
    scene.head_graph["expression"].put("value", 0.2)
    got = classify(head_trace(ns, scene))
    check("A6 stale expression input -> authored/incoherent", got == (None, u"authored", u"incoherent"), got)
    scene = reset()
    scene.head_graph["expression"].put("result", 1.5)
    got = classify(head_trace(ns, scene))
    check("A6 expression result disagrees with bone -> evaluated/incoherent",
          got == (None, u"evaluated", u"incoherent"), got)

    # Output modes other than 1/3.
    for mode in (0, 2):
        scene = reset(head_mode=mode)
        got = classify(head_trace(ns, scene))
        check("A7 output mode %d -> structure/unsupported" % mode, got == (None, u"structure", u"unsupported"), got)

    # Diagnostic distinguishes the evidence and carries no native reference.
    scene = reset(out_keys=[(0.0, 1.0), (1.0, 2.0)])
    diagnostic = ns["prod_bs_capture_trace_diagnostic"](head_trace(ns, scene))
    check("A8 capture diagnostic reports class/stage/evidence and output-log facts",
          diagnostic["static_class"] is None and diagnostic["static_stage"] == u"structure"
          and diagnostic["static_evidence"] == u"time-varying" and diagnostic["output_key_count"] == 2
          and diagnostic["output_values_vary"] is True and is_pure(diagnostic), diagnostic)

    # Not scattered: the single definition is the only place that admits output mode 3.
    src = APP.raw.decode("utf-8")
    check("A9 no scattered 'mode in (1, 3)' substitutions", u"in (1, 3)" not in src and u"in (3, 1)" not in src)


# ---------------------------------------------------------------------------
# Section B -- Save capture, parity and refusals
# ---------------------------------------------------------------------------

def run_save(ns):
    return ns["prod_save"](IDENTITY, u"body", u"Krystal static", scope={"provider_descriptor": {}},
                           operation_context={"token": u"ctx"})


def section_capture(ns):
    scene = reset()
    before = scene.digest()
    undo_before = len(scene.dm.stack)
    capture = ns["prod_capture_body_snapshot"](IDENTITY, {u"Smile": {}}, operation_context={"token": u"ctx"})
    scales = capture["bone_scales"]
    keys = [(r["bone_index"], r["bone_name"]) for r in scales]
    check("B1 static mode-3 capture includes every native bone",
          keys == [(0, u"bip_pelvis"), (3, u"bip_spine"), (55, u"bip_head")] and
          capture["expected_bone_keys"] == [(0, u"bip_pelvis"), (3, u"bip_spine"), (55, u"bip_head")], keys)
    head = [r for r in scales if r["bone_name"] == u"bip_head"][0]
    check("B1 bip_head captured as its physical multiplier (~1.13), existing schema",
          route_close(head["value"], 1.13) and head["representation"] == u"uniform_local_scale_multiplier"
          and head["capture_state"] == u"existing-static-control" and set(head) == set(
              ["bone_index", "bone_name", "representation", "value", "capture_state"]), head)
    check("B1 capture result is pure data", is_pure(capture))
    check("B1 capture made no scene change (modes, keys, controls, expressions, transforms)",
          scene.digest() == before and not scene.cpm_writes and len(scene.dm.stack) == undo_before
          and scene.operate_calls == 0, scene.cpm_writes)

    path = run_save(ns)
    saved = Store.files.get(path) or {}
    check("B2 Save writes one preset with the complete map and existing policy",
          Store.writes == [path] and saved.get("bone_scale_policy") == u"complete-native-bone-map-physical-uniform-v1"
          and saved.get("bone_scales") == scales, saved.get("bone_scales"))
    check("B2 Save made no scene change", scene.digest() == before and not scene.cpm_writes)

    # Indexed and historical capture agree (Q1 parity oracle) for mode 3 and mode 1.
    for label, factory_kw in (("mode-3 head", {}), ("mode-1 head", {"head_mode": 1})):
        scene = reset(**factory_kw)
        indexed = ns["prod_bs_index_capture_map"](IDENTITY)
        try:
            ok = ns["prod_q1_compare_body_capture"](IDENTITY, indexed)
        except Exception as exc:
            ok = exc
        check("B3 indexed and historical capture agree (%s)" % label,
              ok is True and u"Q1_CAPTURE_PARITY=PASS" in log_text(), ok)
    scene = reset(out_keys=[(0.0, 1.0)])
    hist = None
    try:
        ns["prod_capture_bone_scale_map"](IDENTITY)
    except RuntimeError as exc:
        hist = _TEXT(exc)
    check("B3 historical capture refuses the same keyed output", hist is not None and u"bip_head" in hist, hist)

    refusals = [
        ("keyed output", dict(out_keys=[(0.0, 1.0)])),
        ("additional layer", dict(out_layers=2)),
        ("default-value playback", dict(use_default=True)),
        ("incoherent physical scale", dict(physical=1.5)),
        ("time-varying input", dict(in_keys=[(0.0, 0.113), (1.0, 0.2)])),
    ]
    for label, kw in refusals:
        scene = reset(**kw)
        before = scene.digest()
        error = None
        try:
            run_save(ns)
        except RuntimeError as exc:
            error = _TEXT(exc)
        check("B4 Save refuses (%s) without publishing a partial preset" % label,
              error is not None and u"outside the qualified static contract" in error and not Store.writes
              and scene.digest() == before and u"Q3_SCALE_CAPTURE_REJECT bone=" in log_text(), error)

    scene = reset()
    scene.head_graph["output"].log.drop("usedefaultvalue")
    error = None
    try:
        run_save(ns)
    except RuntimeError as exc:
        error = _TEXT(exc)
    check("B4 Save refuses missing output-log evidence", error is not None and not Store.writes
          and u"'static_evidence': u'unreadable'" in log_text().replace(u"'static_evidence': 'unreadable'",
                                                                       u"'static_evidence': u'unreadable'"), error)

    scene = reset()
    extra = FakeChannel(u"rogue_out", FakeLog(u"rogue_out_log", [FakeLayer(u"rogue_out_layer", [])]), mode=3,
                        fromElement=scene.head_graph["expression"], fromAttribute=u"result",
                        toElement=scene.head_graph["transform"], toAttribute=u"scale")
    scene.channels.append(extra)
    error = None
    try:
        run_save(ns)
    except RuntimeError as exc:
        error = _TEXT(exc)
    check("B4 Save refuses a competing bone-scale writer", error is not None and not Store.writes, error)


# ---------------------------------------------------------------------------
# Section C -- Apply: transaction, deferred verification, no-op, recovery
# ---------------------------------------------------------------------------

def replace_input_log(scene):
    channel = scene.head_graph["input"]
    old = channel.log
    channel.log = FakeLog(old._name, [FakeLayer(old.layers[0]._name, [list(k) for k in old.layers[0].keys])],
                          use_default=old.raw("usedefaultvalue"))


def replace_output_log(scene):
    channel = scene.head_graph["output"]
    old = channel.log
    channel.log = FakeLog(old._name, [FakeLayer(old.layers[0]._name, [])], use_default=old.raw("usedefaultvalue"))


def change_limits(scene):
    expression = scene.head_graph["expression"]
    expression.put("lo", 0.25)
    expression.put("hi", 8.25)
    expression.put("result", 0.25 + expression.raw("value") * 8.0)
    scene.head_graph["transform"].put("scale", expression.raw("result"))


def change_limits_baseline(scene):
    # Same physical 1.13 at the restored input 0.113, different mapping.
    expression = scene.head_graph["expression"]
    value = expression.raw("value")
    lo = 1.13 - value * 8.0
    expression.put("lo", lo)
    expression.put("hi", lo + 8.0)
    expression.put("result", lo + value * 8.0)


def run_apply(ns, record, context={"token": u"ctx"}):
    return ns["prod_apply"](IDENTITY, record, scope={"authority": {}, "body": {}},
                            operation_context=context)


def section_apply(ns):
    # C1 changed mode-3 scale: one native transaction, output mode preserved, pending.
    scene = reset()
    result = run_apply(ns, body_record(head=1.25, smile=0.5))
    head = scene.head_graph
    check("C1 changed mode-3 Apply returns an explicit pending (not terminal) outcome",
          result["phase"] == u"verification-pending" and result["native_committed"] is True
          and result["verified"] is False, result["phase"])
    check("C1 one native Undo entry with the existing labels",
          [(e[0], e[1]) for e in scene.dm.stack] == [(b"Apply Body Preset", b"Redo Apply Body Preset")]
          or [(e[0], e[1]) for e in scene.dm.stack] == [("Apply Body Preset", "Redo Apply Body Preset")],
          [(e[0], e[1]) for e in scene.dm.stack])
    check("C1 output channel mode stays 3 and its log stays empty",
          int(head["output"].raw("mode")) == 3 and head["output"].log.IsEmpty())
    check("C1 authored state committed (key, control, expression input = 0.125)",
          route_close(head["input"].log.layers[0].keys[0][1], 0.125) and route_close(head["control"].raw("value"), 0.125)
          and route_close(head["expression"].raw("value"), 0.125))
    check("C1 bone not yet evaluated at CPM's boundary (models the Arm 1/2 observation)",
          route_close(head["transform"].raw("scale"), 1.13))
    check("C1 no write to any channel mode", not [w for w in scene.cpm_writes if w[1] == "mode"], scene.cpm_writes)
    pending = result["pending"]
    check("C1 pending continuation retains only pure data (no DME wrapper)", is_pure(pending))
    check("C1 pending pins the evaluation time and frozen preset",
          route_close(pending["head_time"], 0.375) and pending["record"] == body_record(head=1.25, smile=0.5)
          and len(pending["play_expectations"]) == 1)
    check("C1 no success and no terminal outcome logged by prod_apply",
          u"outcome='committed'" not in log_text() and u"outcome='verification-pending'" in log_text())

    # C2 deferred verification after an ordinary event-loop turn.
    writes_before = list(scene.cpm_writes)
    events_before = list(scene.events)
    scene.event_turn()
    outcome = ns["prod_apply_deferred_verify"](pending)
    check("C2 deferred verification observes the requested physical map -> committed-verified",
          outcome["phase"] == u"committed-verified" and outcome["verified"] is True, outcome)
    check("C2 verification is read-only (no write, refresh, playhead move, Undo or Operate)",
          scene.cpm_writes == writes_before and scene.events == events_before and scene.dm.undo_calls == 0
          and len(scene.dm.stack) == 1 and route_close(scene.head, 0.375))

    # C3 continuation runs before evaluation: unverified, no retry, no compensation.
    scene = reset()
    result = run_apply(ns, body_record(head=1.25, smile=0.5))
    outcome = ns["prod_apply_deferred_verify"](result["pending"])
    check("C3 unevaluated result at the one callback -> committed-unverified (bone-scales)",
          outcome["phase"] == u"committed-unverified" and outcome.get("reason") == u"bone-scales"
          and outcome["native_committed"] is True, outcome)
    check("C3 no automatic Undo or compensating write after commitment",
          scene.dm.undo_calls == 0 and len(scene.dm.stack) == 1 and route_close(scene.head_graph["control"].raw("value"), 0.125))

    # C4 interference during the yield.
    interference = [
        ("context changed", lambda s: setattr(s, "context_ok", False), u"context-changed"),
        ("evaluation time moved", lambda s: setattr(s, "head", 0.5), u"time-changed"),
        ("authored value changed", lambda s: s.head_graph["control"].put("value", 0.3), u"authored"),
        ("output mode changed", lambda s: s.head_graph["output"].put("mode", 1), u"authored"),
        ("output keyed by the user", lambda s: s.head_graph["output"].log.layers[0].keys.append([0.0, 1.0]),
         u"authored"),
        ("FLEX changed", lambda s: s.flex.__setitem__(u"Smile", 0.9), u"flex"),
        # Astra's reproduced counterexamples (equivalent values, different objects / mapping).
        ("input log and layer replaced with identical values", replace_input_log, u"authored"),
        ("output log and layer replaced with identical empty contents", replace_output_log, u"authored"),
        ("expression limits changed (lo 0.25, hi 8.25) preserving 1.25", change_limits, u"authored"),
    ]
    for label, mutate, reason in interference:
        scene = reset()
        result = run_apply(ns, body_record(head=1.25, smile=0.5))
        scene.event_turn()
        mutate(scene)
        writes_before = list(scene.cpm_writes)
        outcome = ns["prod_apply_deferred_verify"](result["pending"])
        check("C4 %s during the yield -> committed-unverified (%s), nothing rewritten" % (label, reason),
              outcome["phase"] == u"committed-unverified" and outcome.get("reason") == reason
              and scene.cpm_writes == writes_before and scene.dm.undo_calls == 0, outcome)

    # C5 true no-op: physical bone and slider already match.
    scene = reset()
    before = scene.digest()
    result = run_apply(ns, body_record(head=1.13, smile=0.25))
    check("C5 matching Apply is a verified no-op: no Undo entry, no mode change, no deferred work",
          result["phase"] == u"no-op" and "pending" not in result and not scene.dm.stack
          and "StartUndo" not in scene.events and scene.digest() == before, result["phase"])
    # Slider match alone is insufficient: the physical bone must match.
    scene = reset(physical=1.5)
    error = None
    try:
        run_apply(ns, body_record(head=1.13, smile=0.25))
    except RuntimeError as exc:
        error = _TEXT(exc)
    check("C5 incoherent physical bone with matching slider is refused before any transaction",
          error is not None and not scene.dm.stack and "StartUndo" not in scene.events, error)

    # C6 precommit failure: exact baseline restoration of an original mode-3 graph.
    scene = reset()
    before = scene.digest()
    scene.fail_flex_write = True
    error = None
    try:
        run_apply(ns, body_record(head=1.25, smile=0.5))
    except Exception as exc:
        error = exc
    check("C6 precommit failure aborts and verifies the exact mode-3 baseline",
          isinstance(error, RuntimeError) and not isinstance(error, ns["ProdRecoveryUnverifiedError"])
          and "AbortUndo" in scene.events and scene.digest() == before
          and u"PROD_APPLY_ABORT_VERIFY restored=True" in log_text()
          and ns["PROD_LOG_CONTEXT"]["recovery"] == u"verified", (error, ns["PROD_LOG_CONTEXT"]["recovery"]))
    scene = reset()
    scene.fail_flex_write = True
    scene.dm.abort_restores = False
    error = None
    try:
        run_apply(ns, body_record(head=1.25, smile=0.5))
    except Exception as exc:
        error = exc
    check("C6 unprovable restoration is reported as recovery uncertainty",
          isinstance(error, ns["ProdRecoveryUnverifiedError"]) and ns["PROD_LOG_CONTEXT"]["recovery"] == u"unverified",
          error)
    for label, hook in (("output log/layer replaced after abort restoration", replace_output_log),
                        ("expression limits changed after abort restoration", change_limits_baseline)):
        scene = reset()
        scene.fail_flex_write = True
        scene.dm.after_abort = hook
        error = None
        try:
            run_apply(ns, body_record(head=1.25, smile=0.5))
        except Exception as exc:
            error = exc
        check("C6 %s is not verified recovery" % label,
              isinstance(error, ns["ProdRecoveryUnverifiedError"])
              and ns["PROD_LOG_CONTEXT"]["recovery"] == u"unverified"
              and u"PROD_APPLY_ABORT_VERIFY restored=False" in log_text(), error)
    # Recovery recognizes an original mode-3 graph only with its empty output layer restored.
    baseline = {"output_mode": 3, "output_key_count": 0, "output_is_empty": True, "output_layer_count": 1,
                "output_log_type": u"DmeFloatLog", "output_use_default_value": False}
    observed = dict(baseline, output_key_count=1, output_is_empty=False)
    check("C6 a keyed output after abort is not accepted as the restored mode-3 baseline",
          ns["prod_bs_snapshot_matches_baseline"](baseline, baseline) is True
          and ns["prod_bs_snapshot_matches_baseline"](observed, baseline) is False)
    check("C6 mode-1 baseline comparison is unchanged (output-log fields not compared)",
          ns["prod_bs_snapshot_matches_baseline"](dict(observed, output_mode=1), dict(baseline, output_mode=1)) is True)

    # C7 existing mode-1 behaviour: synchronous, mode 1 kept, verified at the boundary.
    scene = reset(head_mode=1)
    result = run_apply(ns, body_record(head=1.25, smile=0.5))
    check("C7 mode-1 changed scale remains synchronous committed-verified",
          result["phase"] == u"committed-verified" and "pending" not in result
          and int(scene.head_graph["output"].raw("mode")) == 1
          and route_close(scene.head_graph["transform"].raw("scale"), 1.25), result["phase"])

    # C8 absent-control creation (implicit-neutral bone) remains synchronous.
    scene = reset()
    result = run_apply(ns, body_record(head=1.13, pelvis=1.4, smile=0.25))
    check("C8 missing-control creation unchanged: created once, synchronous verified",
          scene.created == [(u"bip_pelvis_scale", 1.4)] and result["phase"] == u"committed-verified"
          and "pending" not in result, (scene.created, result["phase"]))

    # C9 FLEX-only Apply on a scene whose head is static mode 3: synchronous, verified.
    scene = reset()
    result = run_apply(ns, body_record(head=1.13, smile=0.5))
    check("C9 FLEX-only Apply with an unchanged mode-3 head verifies synchronously",
          result["phase"] == u"committed-verified" and "pending" not in result
          and int(scene.head_graph["output"].raw("mode")) == 3, result["phase"])

    # C10 mixed: changed mode-3 + created scale -> deferred, complete map verified.
    scene = reset()
    result = run_apply(ns, body_record(head=1.25, pelvis=1.4, smile=0.5))
    scene.event_turn()
    outcome = ns["prod_apply_deferred_verify"](result["pending"])
    check("C10 mixed changed mode-3 + created scale is deferred and verifies the complete map",
          result["phase"] == u"verification-pending" and outcome["phase"] == u"committed-verified",
          (result["phase"], outcome))

    # C11 unsupported target refuses before mutation.
    scene = reset(out_keys=[(0.0, 1.0)])
    error = None
    try:
        run_apply(ns, body_record(head=1.25, smile=0.5))
    except RuntimeError as exc:
        error = _TEXT(exc)
    check("C11 keyed mode-3 output refuses Apply before any transaction",
          error is not None and not scene.dm.stack and "StartUndo" not in scene.events, error)

    # C12 a saved multiplier is portable to a mode-1 target.
    scene = reset(head_mode=1)
    result = run_apply(ns, body_record(head=1.13, smile=0.25))
    check("C12 a 1.13 multiplier saved from mode 3 is a no-op on a matching mode-1 target",
          result["phase"] == u"no-op")


# ---------------------------------------------------------------------------
# Section D -- operation lifecycle (guard, ownership, callbacks, close)
# ---------------------------------------------------------------------------

def has(line, key, value):
    return re.search(u"%s=u?'%s'" % (key, value), line) is not None


def outcomes():
    return [line for line in Log.lines if line.startswith(u"PROD_OPERATION_OUTCOME")]


def results():
    return [line for line in Log.lines if line.startswith(u"PROD_OPERATION_RESULT")]


def section_lifecycle(ns, Window):
    checking = ns["PROD_APPLY_CHECKING_COPY"]
    unverified_copy = ns["PROD_APPLY_UNVERIFIED_COPY"]

    # D1 pending result keeps ownership; no success; serialization held.
    scene = reset()
    w = Window(body_record(head=1.25, smile=0.5))
    w.apply_kind(u"body")
    check("D1 pending Apply keeps the operation active after guard returns",
          w.operation is not None and w.busy is True and w.operation.get("phase") == u"verification-pending"
          and len(Timer.queue) == 1 and Timer.queue[0][0] == 0, (w.operation, Timer.queue))
    check("D1 pending shows only the checking status; no success published",
          w.statuses[-1] == (checking, u"neutral") and not [s for s in w.statuses if s[1] == u"success"], w.statuses)
    check("D1 no terminal outcome or operation end recorded while pending",
          not outcomes() and not results() and u"PROD_OPERATION_END" not in log_text(), outcomes())

    # D2 competing CPM actions are refused while pending.
    calls = []
    w.guard("Save Current Body", lambda: calls.append(1))
    check("D2 competing action refused while verification is pending",
          not calls and w.statuses[-1][0] == u"Finish the current action before starting another."
          and w.operation is not None and len(Timer.queue) == 1)
    w.apply_kind(u"body")
    check("D2 a second Apply is refused and does not start another transaction",
          len(scene.dm.stack) == 1 and len(Timer.queue) == 1)

    # D3 the one callback after an event-loop turn verifies and ends exactly once.
    scene.event_turn()
    Timer.run_all()
    check("D3 verified: 'Body Preset applied.' and outcome 'verified'",
          w.statuses[-1] == (u"Body Preset applied.", u"success")
          and len(outcomes()) == 1 and has(outcomes()[0], u"outcome", u"verified"), (w.statuses[-1], outcomes()))
    check("D3 operation ended exactly once; serialization released",
          w.operation is None and w.busy is False and len(results()) == 1
          and has(results()[0], u"outcome", u"verified"), results())

    # D4 duplicate / stale callbacks are harmless.
    stale_token = (1, 1)
    w.apply_verification_turn(stale_token)
    check("D4 duplicate callback after completion is harmless", len(results()) == 1 and w.operation is None
          and u"PROD_APPLY_VERIFY_STALE" in log_text())
    scene.head = 0.375
    w.record = body_record(head=1.5, smile=0.5)
    w.apply_kind(u"body")
    newer = w.operation
    w.apply_verification_turn(stale_token)
    check("D4 a stale callback never ends a newer pending operation",
          w.operation is newer and newer is not None and len(results()) == 1 and len(Timer.queue) == 1)
    scene.event_turn()
    Timer.run_all()
    Timer.run_all()
    check("D4 the newer operation still finishes once", w.operation is None and len(results()) == 2)

    # D5 callback runs before evaluation -> unverified copy, no success, ended once.
    scene = reset()
    w = Window(body_record(head=1.25, smile=0.5))
    w.apply_kind(u"body")
    Timer.run_all()
    check("D5 unevaluated at the callback: committed-unverified copy, never success",
          w.statuses[-1] == (unverified_copy, u"error") and not [s for s in w.statuses if s[1] == u"success"]
          and has(outcomes()[-1], u"outcome", u"committed-unverified") and w.operation is None and len(results()) == 1,
          (w.statuses, outcomes()))
    check("D5 no automatic Undo after an unverified committed change", scene.dm.undo_calls == 0
          and len(scene.dm.stack) == 1)

    # D6 scheduling failure is terminal and does not leave CPM busy.
    scene = reset()
    w = Window(body_record(head=1.25, smile=0.5))
    Timer.fail[0] = True
    w.apply_kind(u"body")
    Timer.fail[0] = False
    check("D6 scheduling failure -> terminal unverified, operation ended, not busy",
          w.operation is None and w.busy is False and w.statuses[-1] == (unverified_copy, u"error")
          and len(results()) == 1 and u"committed-unverified" in results()[0] and not Timer.queue,
          (w.statuses, results()))

    # D7 close while pending: finalized without DME access; window not resurrected.
    scene = reset()
    w = Window(body_record(head=1.25, smile=0.5))
    w.apply_kind(u"body")
    calls = []
    real_verify = ns["prod_apply_deferred_verify"]
    ns["prod_apply_deferred_verify"] = lambda pending: calls.append(1) or real_verify(pending)
    event = w.close()
    check("D7 close while pending ends the operation as unverified (closed-before-verification)",
          w.operation is None and w.busy is False and u"closed-before-verification" in outcomes()[-1]
          and len(results()) == 1 and event.state == "ignored" and w.hidden == 1, (outcomes(), event.state))
    statuses_after_close = list(w.statuses)
    Timer.run_all()
    check("D7 deferred close then finalizes; the queued check performs no scene access",
          not calls and w.closes == 2 and len(results()) == 1 and _QtGui.QDialog.rejected
          and w.statuses == statuses_after_close, (calls, w.closes))
    ns["prod_apply_deferred_verify"] = real_verify

    # D8 foreign modal suspends scene access at the callback.
    scene = reset()
    w = Window(body_record(head=1.25, smile=0.5))
    w.apply_kind(u"body")
    w.scene_activity_suspended = True
    calls = []
    ns["prod_apply_deferred_verify"] = lambda pending: calls.append(1) or real_verify(pending)
    scene.event_turn()
    Timer.run_all()
    ns["prod_apply_deferred_verify"] = real_verify
    check("D8 suspended scene access -> unverified without DME access, ended once",
          not calls and w.operation is None and u"scene-access-unavailable" in outcomes()[-1]
          and len(results()) == 1, outcomes())

    # D8b fresh modal check: the watcher's cached flag is still False.
    for state, reason in (("modal", u"modal-active"), ("absent", u"qt-application-unavailable"),
                          ("unreadable", u"modal-state-unreadable")):
        scene = reset()
        w = Window(body_record(head=1.25, smile=0.5))
        w.apply_kind(u"body")
        scene.event_turn()
        calls = []
        snapshots = []
        real_snapshot = ns["prod_bs_index_snapshot"]
        ns["prod_apply_deferred_verify"] = lambda pending: calls.append(1) or real_verify(pending)
        ns["prod_bs_index_snapshot"] = lambda identity: snapshots.append(1) or real_snapshot(identity)
        FakeApp.state[0] = state
        queries_before = FakeApp.modal_queries[0]
        writes_before = list(scene.cpm_writes)
        Timer.run_all()
        FakeApp.state[0] = "none"
        ns["prod_apply_deferred_verify"] = real_verify
        ns["prod_bs_index_snapshot"] = real_snapshot
        check("D8b %s at callback entry (cached suspension False) -> unverified '%s', zero scene verification"
              % (state, reason),
              w.scene_activity_suspended is False and not calls and not snapshots and w.operation is None
              and w.busy is False and reason in outcomes()[-1] and len(results()) == 1
              and w.statuses[-1] == (unverified_copy, u"error") and scene.cpm_writes == writes_before
              and not [s for s in w.statuses if s[1] == u"success"]
              and (state == "absent" or FakeApp.modal_queries[0] > queries_before),
              (outcomes(), w.statuses, calls, snapshots))

    # D8c telemetry: the synchronous guard return is not terminal completion.
    scene = reset()
    w = Window(body_record(head=1.25, smile=0.5))
    w.apply_kind(u"body")
    samples_at_return = list(Log.samples)
    scene.event_turn()
    Timer.run_all()
    check("D8c guard return while pending samples ACTION_RETURN_PENDING, terminal result samples ACTION_END",
          u"ACTION_RETURN_PENDING:Apply Body Preset" in samples_at_return
          and u"ACTION_END:Apply Body Preset" not in samples_at_return
          and Log.samples.count(u"ACTION_END:Apply Body Preset") == 1, Log.samples)
    scene = reset(head_mode=1)
    w = Window(body_record(head=1.25, smile=0.5))
    w.apply_kind(u"body")
    check("D8c synchronous Apply still samples ACTION_END once at guard return",
          Log.samples.count(u"ACTION_END:Apply Body Preset") == 1
          and u"ACTION_RETURN_PENDING:Apply Body Preset" not in Log.samples, Log.samples)

    # D9 an exception during verification is terminal (never leaves CPM busy).
    scene = reset()
    w = Window(body_record(head=1.25, smile=0.5))
    w.apply_kind(u"body")
    ns["prod_apply_deferred_verify"] = lambda pending: (_ for _ in ()).throw(RuntimeError("synthetic"))
    Timer.run_all()
    ns["prod_apply_deferred_verify"] = real_verify
    check("D9 verification error -> unverified 'error', operation ended once",
          w.operation is None and u"'reason': u'error'" in outcomes()[-1].replace(u"'reason': 'error'", u"'reason': u'error'")
          and len(results()) == 1 and w.statuses[-1] == (unverified_copy, u"error"), outcomes())

    # D10 synchronous outcomes unchanged and ended at once.
    for label, record, phase_copy in (
            ("mode-1 changed", None, (u"Body Preset applied.", u"success")),
            ("no-op", body_record(head=1.13, smile=0.25), (u"Already matches this preset.", u"neutral"))):
        scene = reset(head_mode=1) if record is None else reset()
        w = Window(record or body_record(head=1.25, smile=0.5))
        w.apply_kind(u"body")
        check("D10 synchronous %s Apply publishes at once and ends the operation" % label,
              w.statuses[-1] == phase_copy and w.operation is None and len(results()) == 1
              and u"PROD_APPLY_VERIFY_SCHEDULED" not in log_text() and checking not in [s[0] for s in w.statuses],
              (w.statuses, results()))

    # D11 guard exception path still ends exactly once.
    scene = reset()
    w = Window(body_record(head=1.25, smile=0.5))
    w.guard("Apply Body Preset", lambda: (_ for _ in ()).throw(RuntimeError("synthetic precommit")))
    check("D11 guard failure ends the operation exactly once", w.operation is None and len(results()) == 1
          and len(w.dialogs) == 1)

    # D12 deferred end-to-end: success requires the observed values, not callback delivery.
    scene = reset()
    w = Window(body_record(head=1.25, smile=0.5))
    w.apply_kind(u"body")
    scene.event_turn()
    Timer.run_all()
    check("D12 end-to-end: mode 3 kept, bone 1.25, verified once",
          int(scene.head_graph["output"].raw("mode")) == 3 and route_close(scene.head_graph["transform"].raw("scale"), 1.25)
          and w.statuses[-1] == (u"Body Preset applied.", u"success") and len(results()) == 1)


# ---------------------------------------------------------------------------
# Section E -- static boundaries of the new code
# ---------------------------------------------------------------------------

def _names_called(source):
    tree = ast.parse(source)
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute):
                called.add(fn.attr)
            elif isinstance(fn, ast.Name):
                called.add(fn.id)
    return called


def section_static(app):
    verify = _names_called(app.top_text("prod_apply_deferred_verify"))
    holds = _names_called(app.top_text("prod_bs_play_expectations_hold"))
    forbidden = set(["SetValue", "SetKeyValue", "Operate", "StartUndo", "FinishUndo", "Undo", "Redo",
                     "AbortUndoableOperation", "SetHeadTimeInSeconds", "ProcessEvents", "same_time_refresh",
                     "singleShot", "sleep", "prod_cpm_authorize_operation", "prod_bs_write_existing_scale",
                     "prod_bs_create_graph", "write_side"])
    check("E1 deferred verification is read-only (no write, refresh, pumping, timer, Undo or reauthorization)",
          not (verify | holds) & forbidden, sorted((verify | holds) & forbidden))
    turn = app.method_text("ProdWindow", "apply_verification_turn")
    begin = app.method_text("ProdWindow", "apply_begin_verification")
    import re
    check("E2 exactly one zero-delay timer in the continuation; no retry, delay or pumping",
          begin.count(u"singleShot(") == 1 and re.search(u"singleShot\\(\\s*0\\s*,", begin) is not None
          and u"singleShot" not in turn and u"ProcessEvents" not in turn + begin and u"sleep" not in turn + begin,
          begin)
    apply_src = app.top_text("prod_apply")
    check("E3 prod_apply writes no channel mode", u"\"mode\"" not in apply_src.split(u"play_expectations = [")[1]
          .split(u"total = (")[0] and u"SetValue" not in apply_src)


APP = None


def main():
    global APP
    print("Interpreter: %s" % sys.version.split()[0])
    APP = route.AppSource(route.APP_PATH)
    import hashlib
    print("Candidate app sha256: %s" % hashlib.sha256(APP.raw).hexdigest())
    ns, methods = build_namespace(APP)
    Window = make_window_class(methods)
    for section in (lambda: section_classification(ns), lambda: section_capture(ns), lambda: section_apply(ns),
                    lambda: section_lifecycle(ns, Window), lambda: section_static(APP)):
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
