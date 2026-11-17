# -*- coding: utf-8 -*-
"""F-01 OT1 -- focused offline qualification of the ordering correction with its integrated production
reference guard (Astra's final ACCEPT WITH CONDITIONS; F01_OT1_PRODUCTION_GUARD.md), through the actual prod_apply
dispatch and transaction path, without the OT1 observer. The fake DataModel derives each element's direct references
from the scene's own attribute links (test_cpm_app_m05_static_scale.FakeDataModel).

The candidate: for an admitted, changed, existing mode-3 Body scale, after the existing input write, CPM operates the
exclusively bound expression operator inside the owned transaction and verifies its result before commit; the
existing postcommit physical-scale verification is unchanged.

Technique: the M-05 suite's harness (production functions extracted verbatim from cpm/app; fakes only at the SFM, Qt,
DME, authority and library boundaries), with an explicit evaluator whose input, expression-result and physical-scale
states advance independently:
  - input: CPM's own writes (key, source) and its input-channel Operate() copy the native value to expression.value;
  - expression result: only expression.Operate() or an evaluator step changes it;
  - physical scale: only an evaluator step copies an up-to-date result into a mode-3 bone's scale.
Models: "q1" (each same-time refresh advances each graph by ONE link, the stale expression first; the settled interval
advances nothing: Q1's measured behaviour), "stale" (the physical scale never advances), "wrong" (the physical scale
advances to a wrong value), "frozen" (nothing evaluates). The baseline is the same namespace with the trial's one call disabled
(prod_bs_operate_bound_expression -> no-op), i.e. exactly the source before the candidate.

Usage: --phase=run (Python 2.7.5 and Python 3.10). Offline only; nothing here demonstrates real-SFM evaluation order,
native Undo/Redo, or Qt timer ordering.
"""
from __future__ import print_function

import ast
import hashlib
import os
import sys
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_m05_static_scale as m  # noqa: E402

_TEXT = m._TEXT
RESULTS = []


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


m.check = check  # the harness's own extraction check reports here
close = m.route_close
IDENTITY = m.IDENTITY


# ---------------------------------------------------------------------------
# Scene: Krystal-like (pelvis implicit neutral, spine mode 1, head and tail existing mode 3), optional peer clip
# ---------------------------------------------------------------------------

_original_expression_operate = m.FakeExpression.Operate


def _traced_operate(self):
    scene = m.Scene.current
    graph = scene.graph_by_expression.get(self._handle)
    scene.events.append(("ExprOperate", self._name, scene.dm.open is not None))
    scene.operate_log.append({
        "expression": self._name, "handle": self._handle, "in_transaction": scene.dm.open is not None,
        "writes_before": len(scene.cpm_writes),
        "state": graph_state(graph) if graph is not None else None})
    hook = scene.operate_hook
    if hook is not None:
        return hook(self, _original_expression_operate)
    return _original_expression_operate(self)


m.FakeExpression.Operate = _traced_operate


def graph_state(graph):
    return {"key": graph["input"].log.layers[0].keys[0][1] if graph["input"].log.layers[0].keys else None,
            "source": graph["control"].raw("value"), "value": graph["expression"].raw("value"),
            "result": graph["expression"].raw("result"), "physical": graph["transform"].raw("scale"),
            "output_mode": int(graph["output"].raw("mode")), "output_empty": graph["output"].log.IsEmpty()}


def lerp(expression):
    lo, hi = expression.raw("lo"), expression.raw("hi")
    return lo + expression.raw("value") * (hi - lo)


def scale_outputs(scene):
    return [c for c in scene.channels + scene.peer_channels if c.raw("toAttribute") == u"scale"]


def make_model(scene, model):
    def refresh():
        scene.refreshes += 1
        if model == "frozen":  # nothing evaluates (isolates what verification itself reads)
            return
        for output in scale_outputs(scene):
            expression, transform = output.raw("fromElement"), output.raw("toElement")
            mode = int(output.raw("mode"))
            if mode == 1:  # mode 1 unchanged from the M-05 harness: synchronous at the refresh
                expression.put("result", lerp(expression))
                transform.put("scale", expression.raw("result"))
                continue
            if mode != 3 or not output.log.IsEmpty() or output.log.raw("usedefaultvalue"):
                continue
            if not close(expression.raw("result"), lerp(expression)):
                expression.put("result", lerp(expression))  # one link: the stale expression first
            elif model == "q1":
                transform.put("scale", expression.raw("result"))  # then the physical scale
            elif model == "wrong":
                transform.put("scale", expression.raw("result") + 0.05)
            # "stale": the physical scale never advances

    def event_turn():
        scene.event_turns += 1  # the settled interval advances nothing (Q1)
    scene.refresh = refresh
    scene.event_turn = event_turn


def trial_scene(model="q1", head_mode=3, peer=False, tail=True):
    scene = m.Scene()
    scene.operate_hook = None
    scene.operate_log = []
    scene.peer_channels = []
    scene.refreshes = 0
    scene.event_turns = 0
    scene.precommit = None
    scene.bone(0, u"bip_pelvis")
    spine = scene.bone(3, u"bip_spine")
    scene.spine_graph = scene.scale_graph(spine, u"bip_spine", 0.1, output_mode=1)
    head = scene.bone(55, u"bip_head")
    scene.head_graph = scene.scale_graph(head, u"bip_head", 0.113, output_mode=head_mode)
    scene.tail_graph = None
    if tail:
        tail_t = scene.bone(60, u"bip_tail00")
        scene.tail_graph = scene.scale_graph(tail_t, u"bip_tail00", 0.08, output_mode=3)
    scene.graph_by_expression = dict((g["expression"]._handle, g) for g in
                                     (scene.spine_graph, scene.head_graph, scene.tail_graph) if g is not None)
    scene.peer_graph = None
    if peer:
        scene.peer_graph = peer_graph(scene)
    make_model(scene, model)

    real_finish = scene.dm.FinishUndo

    def finish():
        scene.precommit = dict((name, graph_state(g)) for name, g in
                               (("head", scene.head_graph), ("tail", scene.tail_graph)) if g is not None)
        real_finish()
    scene.dm.FinishUndo = finish
    return scene


def peer_graph(scene):
    """A same-model peer instance: its own transform, control, expression and channels in its own channels clip."""
    transform = m.FakeElement(u"DmeTransform", u"bone 55 (bip_head)", scale=1.13)
    control = m.FakeElement(u"DmElement", u"bip_head_scale", value=0.113, defaultValue=0.1)
    expression = m.FakeExpression(u"bip_head_scale_rescale", expr=u"lerp(value, lo, hi)", lo=0.0, hi=10.0,
                                  value=0.113, result=1.13)
    in_log = m.FakeLog(u"bip_head_scale_log", [m.FakeLayer(u"bip_head_scale_layer0", [(0.0, 0.113)])])
    input_channel = m.FakeChannel(u"bip_head_scale", in_log, mode=3, fromElement=control, fromAttribute=u"value",
                                  toElement=expression, toAttribute=u"value")
    out_log = m.FakeLog(u"scaled_bip_head_scale_log", [m.FakeLayer(u"scaled_bip_head_scale_layer0", [])])
    output = m.FakeChannel(u"scaled_bip_head_scale_channel", out_log, mode=3, fromElement=expression,
                           fromAttribute=u"result", toElement=transform, toAttribute=u"scale")
    clip = m.FakeElement(u"DmeChannelsClip", u"krystal20201", channels=[input_channel, output])
    scene.extra_clips.append(clip)
    scene.peer_channels.extend([input_channel, output])
    graph = {"control": control, "expression": expression, "input": input_channel, "output": output,
             "transform": transform, "clip": clip}
    scene.graph_by_expression[expression._handle] = graph
    return graph


def trial_record(head=1.33, tail=1.0, spine=1.0, pelvis=1.0, smile=0.25, with_tail=True):
    def row(index, bone, value, state):
        return {"bone_index": index, "bone_name": bone, "representation": u"uniform_local_scale_multiplier",
                "value": value, "capture_state": state}
    scales = [row(0, u"bip_pelvis", pelvis, u"implicit-neutral"),
              row(3, u"bip_spine", spine, u"existing-static-control"),
              row(55, u"bip_head", head, u"existing-static-control")]
    if with_tail:
        scales.append(row(60, u"bip_tail00", tail, u"existing-static-control"))
    return {"kind": u"body", "name": u"Body", "preset_id": u"preset-1", "values": {u"flex.Smile": smile},
            "bone_scales": scales}


def reset(**kw):
    return m.reset(scene_factory=trial_scene, **kw)


def run_apply(ns, record):
    return m.run_apply(ns, record)


def apply_and_settle(ns, record):
    """Apply (CPM's own refresh runs inside), one ordinary event turn, then CPM's deferred verification."""
    result = run_apply(ns, record)
    outcome = None
    if result.get("pending") is not None:
        m.Scene.current.event_turn()
        outcome = ns["prod_apply_deferred_verify"](result["pending"])
    return result, outcome


def attempt(fn, *args):
    try:
        return fn(*args), None
    except Exception as exc:
        return None, exc


def operated(scene):
    return [e["expression"] for e in scene.operate_log]


def abort_log():
    return [line for line in m.Log.lines if line.startswith(u"PROD_APPLY_ABORT_VERIFY")]


class Baseline(object):
    """The source before the candidate: the trial's single call disabled."""
    def __init__(self, ns):
        self.ns = ns

    def __enter__(self):
        self.real = self.ns["prod_bs_operate_bound_expression"]
        self.ns["prod_bs_operate_bound_expression"] = lambda item, native: None

    def __exit__(self, *exc):
        self.ns["prod_bs_operate_bound_expression"] = self.real
        return False


def on_open(scene, mutate):
    """Mutate the scene right after the owned transaction opens (so Abort can restore attribute values)."""
    real = scene.dm.StartUndo

    def start(label, redo):
        real(label, redo)
        mutate(scene)
    scene.dm.StartUndo = start


# ---------------------------------------------------------------------------
# Section P -- propagation (Q1 model) and the baseline reproduction
# ---------------------------------------------------------------------------

def section_propagation(ns):
    with Baseline(ns):
        scene = reset()
        result, outcome = apply_and_settle(ns, trial_record())
    check("P0 baseline under the Q1 model reproduces Q1: Body's refresh advances only the expression results "
          "(head 1.33, tail 1.0), the physical scales stay 1.13 / 0.8, CPM reports committed-unverified bone-scales",
          result["phase"] == u"verification-pending" and outcome["phase"] == u"committed-unverified"
          and outcome.get("reason") == u"bone-scales"
          and close(graph_state(scene.head_graph)["result"], 1.33) and close(graph_state(scene.tail_graph)["result"], 1.0)
          and close(graph_state(scene.head_graph)["physical"], 1.13)
          and close(graph_state(scene.tail_graph)["physical"], 0.8) and not scene.operate_log,
          (result["phase"], outcome, graph_state(scene.head_graph)))

    scene = reset()
    result = run_apply(ns, trial_record())
    head_op = [e for e in scene.operate_log if e["expression"] == u"bip_head_scale_rescale"]
    tail_op = [e for e in scene.operate_log if e["expression"] == u"bip_tail00_scale_rescale"]
    check("P1 each changed mode-3 expression is operated exactly once, inside the owned transaction",
          len(head_op) == 1 and len(tail_op) == 1 and len(scene.operate_log) == 2
          and all(e["in_transaction"] for e in scene.operate_log), scene.operate_log)
    check("P2 the operator runs after that scale's input write (key, source and expression input already the "
          "requested native value; result and physical still the originals)",
          close(head_op[0]["state"]["key"], 0.133) and close(head_op[0]["state"]["source"], 0.133)
          and close(head_op[0]["state"]["value"], 0.133) and close(head_op[0]["state"]["result"], 1.13)
          and close(head_op[0]["state"]["physical"], 1.13)
          and close(tail_op[0]["state"]["value"], 0.1) and close(tail_op[0]["state"]["result"], 0.8),
          (head_op, tail_op))
    pre = scene.precommit
    check("P3 at commit the expression results are the expected mapped scales and the physical scales are "
          "unchanged (CPM writes no physical scale)",
          close(pre["head"]["result"], 1.33) and close(pre["tail"]["result"], 1.0)
          and close(pre["head"]["physical"], 1.13) and close(pre["tail"]["physical"], 0.8), pre)
    check("P4 no CPM write to a bone scale, an output channel or a channel mode; output mode 3 and empty logs kept",
          not [w for w in scene.cpm_writes if w[1] in ("scale", "mode") or u"scaled_" in _TEXT(w[0])]
          and pre["head"]["output_mode"] == 3 and pre["head"]["output_empty"] and pre["tail"]["output_mode"] == 3
          and pre["tail"]["output_empty"], scene.cpm_writes)
    check("P5 one native Undo entry with the existing labels; result pending",
          [(e[0], e[1]) for e in scene.dm.stack] in ([(b"Apply Body Preset", b"Redo Apply Body Preset")],
                                                     [("Apply Body Preset", "Redo Apply Body Preset")])
          and result["phase"] == u"verification-pending", scene.dm.stack)
    check("P6 CPM's own refresh then advances the physical scales (head 1.33, tail 1.0)",
          scene.refreshes == 1 and close(graph_state(scene.head_graph)["physical"], 1.33)
          and close(graph_state(scene.tail_graph)["physical"], 1.0), graph_state(scene.head_graph))
    writes = list(scene.cpm_writes)
    scene.event_turn()
    outcome = ns["prod_apply_deferred_verify"](result["pending"])
    check("P7 deferred verification of the physical map -> committed-verified, read-only",
          outcome["phase"] == u"committed-verified" and outcome["verified"] is True and scene.cpm_writes == writes
          and len(scene.operate_log) == 2 and scene.dm.undo_calls == 0, outcome)


# ---------------------------------------------------------------------------
# Section S -- the expression result never substitutes for physical verification
# ---------------------------------------------------------------------------

def section_stale(ns, Window):
    for model, label in (("stale", "never advances"), ("wrong", "advances to a wrong value")):
        scene = reset(model=model)
        result, outcome = apply_and_settle(ns, trial_record())
        check("S1 physical scale %s: correct expression results at commit, committed-unverified bone-scales, "
              "no Undo or compensation" % label,
              close(scene.precommit["head"]["result"], 1.33) and close(graph_state(scene.head_graph)["result"], 1.33)
              and outcome["phase"] == u"committed-unverified" and outcome.get("reason") == u"bone-scales"
              and scene.dm.undo_calls == 0 and len(scene.dm.stack) == 1, (outcome, graph_state(scene.head_graph)))

    scene = reset(model="stale")
    w = Window(trial_record())
    w.apply_kind(u"body")
    m.Timer.run_all()
    check("S2 window: a stale physical scale never publishes success (unverified copy, ended once)",
          w.statuses[-1] == (ns["PROD_APPLY_UNVERIFIED_COPY"], u"error")
          and not [s for s in w.statuses if s[1] == u"success"] and w.operation is None
          and len(m.results()) == 1, w.statuses)

    src = m.APP.top_text("prod_bs_operate_bound_expression")
    called = m._names_called(src)
    check("S3 the trial function writes nothing but the operator: no SetValue/SetKeyValue, no refresh, events, "
          "timer, Undo, channel Operate or physical read as success",
          not called & set(["SetValue", "SetKeyValue", "same_time_refresh", "ProcessEvents", "SetHeadTimeInSeconds",
                            "singleShot", "StartUndo", "FinishUndo", "AbortUndoableOperation", "Undo", "Redo",
                            "prod_apply_deferred_verify", "prod_bs_index_verify_saved", "prod_bs_evaluated_matches"])
          and u"physical_scale" not in src and src.count(u"operate()") == 1, sorted(called))
    verify_src = m.APP.top_text("prod_apply_deferred_verify") + m.APP.top_text("prod_bs_index_verify_saved")
    check("S4 success is still decided by the deferred physical verification (unchanged; it reads no expression "
          "Operate and calls no trial function)",
          u"prod_bs_operate_bound_expression" not in verify_src and u"Operate" not in verify_src)


# ---------------------------------------------------------------------------
# Section E -- operator exceptions and verified Abort
# ---------------------------------------------------------------------------

def raise_before(expression, operate):
    raise RuntimeError("synthetic operator failure")


def raise_after_partial(expression, operate):
    expression.put("result", 7.0)
    raise RuntimeError("synthetic operator failure after a partial result")


def silent_noop(expression, operate):
    return None


def wrong_value(expression, operate):
    operate(expression)
    expression.put("result", expression.raw("result") + 0.01)


def touches_input(expression, operate):
    operate(expression)
    m.Scene.current.head_graph["control"].put("value", 0.2)


def section_abort(ns):
    cases = [
        ("operator raises before any change", raise_before, u"synthetic operator failure"),
        ("operator raises after a partial result", raise_after_partial, u"partial result"),
        ("operator silently does nothing", silent_noop, u"did not produce the expected result"),
        ("operator produces a wrong result", wrong_value, u"did not produce the expected result"),
        ("operator disturbs the authored input", touches_input, u"after its expression was operated"),
    ]
    for label, hook, text in cases:
        scene = reset()
        before = scene.digest()
        scene.operate_hook = hook
        _, error = attempt(run_apply, ns, trial_record())
        check("E1 %s -> verified Abort: exact baseline (inputs, expression results, physical), no Undo entry" % label,
              isinstance(error, RuntimeError) and not isinstance(error, ns["ProdRecoveryUnverifiedError"])
              and "AbortUndo" in scene.events and "FinishUndo" not in scene.events and not scene.dm.stack
              and scene.digest() == before and abort_log() and u"restored=True" in abort_log()[-1]
              and text in abort_log()[-1] and ns["PROD_LOG_CONTEXT"]["recovery"] == u"verified",
              (error, abort_log()))

    scene = reset()
    scene.operate_hook = raise_after_partial
    scene.dm.abort_restores = False
    _, error = attempt(run_apply, ns, trial_record())
    check("E2 an operator failure whose Abort cannot be proved -> recovery uncertainty, never success",
          isinstance(error, ns["ProdRecoveryUnverifiedError"]) and ns["PROD_LOG_CONTEXT"]["recovery"] == u"unverified",
          error)

    scene = reset()
    before = scene.digest()
    scene.fail_flex_write = True
    _, error = attempt(run_apply, ns, trial_record(smile=0.5))
    check("E3 a failure after both operators ran (the flex write) -> verified Abort restores the operated "
          "expression results to 1.13 / 0.8 with the physical scales",
          isinstance(error, RuntimeError) and len(scene.operate_log) == 2 and scene.digest() == before
          and close(graph_state(scene.head_graph)["result"], 1.13) and close(graph_state(scene.tail_graph)["result"], 0.8)
          and u"restored=True" in abort_log()[-1], (error, abort_log()))

    for field, value in (("result", 1.33), ("scale", 1.33)):
        scene = reset(model="frozen")
        scene.fail_flex_write = True
        if field == "result":
            scene.dm.after_abort = lambda s: s.head_graph["expression"].put("result", 1.33)
        else:
            scene.dm.after_abort = lambda s: s.head_graph["transform"].put("scale", 1.33)
        _, error = attempt(run_apply, ns, trial_record(smile=0.5))
        check("E4 an operated %s left at 1.33 after Abort (nothing re-evaluates) is not verified recovery"
              % ("expression result" if field == "result" else "physical scale"),
              isinstance(error, ns["ProdRecoveryUnverifiedError"]) and u"restored=False" in abort_log()[-1], error)


# ---------------------------------------------------------------------------
# Section I -- wrong, replaced, shared or ambiguous expression bindings
# ---------------------------------------------------------------------------

def extra_reader(scene):
    helper = m.FakeElement(u"DmeTransform", u"helper", scale=scene.head_graph["expression"].raw("result"))
    channel = m.FakeChannel(u"helper_scale", m.FakeLog(u"helper_log", [m.FakeLayer(u"helper_layer", [])]), mode=3,
                            fromElement=scene.head_graph["expression"], fromAttribute=u"result", toElement=helper,
                            toAttribute=u"scale")
    scene.channels.append(channel)


def peer_clip_with(scene, **endpoints):
    channel = m.FakeChannel(u"foreign", m.FakeLog(u"foreign_log", [m.FakeLayer(u"foreign_layer", [])]), mode=3,
                            **endpoints)
    clip = m.FakeElement(u"DmeChannelsClip", u"other", channels=[channel])
    scene.extra_clips.append(clip)
    return channel


def peer_reader(scene):
    peer_clip_with(scene, fromElement=scene.head_graph["expression"], fromAttribute=u"result",
                   toElement=m.FakeElement(u"DmeTransform", u"other"), toAttribute=u"scale")


def peer_writer(scene):
    peer_clip_with(scene, fromElement=m.FakeElement(u"DmElement", u"other", value=0.5), fromAttribute=u"value",
                   toElement=scene.head_graph["expression"], toAttribute=u"value")


class UnreadableChannel(m.FakeChannel):
    def GetAttribute(self, attr_name):
        if attr_name in ("fromElement", b"fromElement"):
            raise RuntimeError("unreadable endpoint")
        return m.FakeChannel.GetAttribute(self, attr_name)


def peer_unreadable(scene):
    channel = UnreadableChannel(u"unreadable", m.FakeLog(u"u_log", [m.FakeLayer(u"u_layer", [])]), mode=3,
                                fromElement=None, toElement=m.FakeElement(u"DmeTransform", u"x"), toAttribute=u"scale")
    scene.extra_clips.append(m.FakeElement(u"DmeChannelsClip", u"other", channels=[channel]))


def repoint_output(scene):
    other = m.FakeExpression(u"other_rescale", expr=u"lerp(value, lo, hi)", lo=0.0, hi=10.0, value=0.113, result=1.13)
    scene.head_graph["output"].put("fromElement", other)


def change_expr_text(scene):
    scene.head_graph["expression"].put("expr", u"lerp(value, lo, hi) * 1")


def change_limits(scene):
    scene.head_graph["expression"].put("hi", 9.0)


def retarget_output(scene):
    scene.head_graph["output"].put("toElement", m.FakeElement(u"DmeTransform", u"elsewhere", scale=1.13))


def section_identity(ns):
    # Pre-existing sharing the plan cannot see (another clip) or does not reject (a non-bone reader).
    def off_track(scene):  # a channel reading the expression that is in no channels clip at all
        m.FakeChannel(u"off_track", m.FakeLog(u"o_log", [m.FakeLayer(u"o_layer", [])]), mode=3,
                      fromElement=scene.head_graph["expression"], fromAttribute=u"result",
                      toElement=m.FakeElement(u"DmeTransform", u"o", scale=1.13), toAttribute=u"scale")

    def non_channel(scene):  # a non-channel element holding the expression
        m.FakeElement(u"DmeConnectionOperator", u"conn", input=scene.head_graph["expression"])

    def second_list(scene):  # the expression listed in the peer's operators array too
        m.FakeElement(u"DmeAnimationSet", u"krystal20201", operators=[scene.head_graph["expression"]])

    for label, setup in (("a second reader of expression.result in the same clip", extra_reader),
                         ("a reader in another animation set's channels clip", peer_reader),
                         ("a writer into expression.value in another channels clip", peer_writer),
                         ("an off-track reader in no channels clip", off_track),
                         ("a non-channel reference (connection operator)", non_channel),
                         ("the expression in a second operators array", second_list)):
        scene = reset()
        setup(scene)
        before = scene.digest()
        _, error = attempt(run_apply, ns, trial_record())
        check("I1 %s -> refused BEFORE Undo opens: no StartUndo, no write, nothing operated" % label,
              isinstance(error, RuntimeError) and u"shared or ambiguous" in _TEXT(error)
              and "StartUndo" not in scene.events and not scene.cpm_writes and not scene.operate_log
              and not scene.dm.stack and scene.digest() == before, (error, scene.events))

    for fault, text in (("raise", u"unreadable"), ("repeat", u"repeated"), ("unreadable", u"unreadable")):
        scene = reset()
        scene.ref_fault = fault
        before = scene.digest()
        _, error = attempt(run_apply, ns, trial_record())
        check("I2 reference enumeration %s (incomplete / repeated / unreadable) -> refused before Undo" % fault,
              isinstance(error, RuntimeError) and text in _TEXT(error) and "StartUndo" not in scene.events
              and not scene.cpm_writes and scene.digest() == before, (error, scene.events))

    scene = reset()
    peer_unreadable(scene)
    result, outcome = apply_and_settle(ns, trial_record())
    check("I2 an unrelated unreadable channel elsewhere in the shot does NOT block a valid Apply (verified)",
          outcome is not None and outcome["phase"] == u"committed-verified" and len(scene.operate_log) == 2,
          (result.get("phase"), outcome))

    scene = reset()
    calls = []
    real_first = scene.dm.FirstAttributeReferencingElement
    scene.dm.FirstAttributeReferencingElement = lambda h: (calls.append(("StartUndo" in scene.events)), real_first(h))[1]
    result, outcome = apply_and_settle(ns, trial_record())
    check("I2 each changed mode-3 expression is checked before StartUndo and again inside the transaction just "
          "before Operate()", calls == [False, False, True, True] and outcome["phase"] == u"committed-verified", calls)

    # Changed after the preflight: an extra reference appears once the transaction is open -> late refusal, Abort.
    for label, mutate in (("an extra reader added after the preflight", off_track),
                          ("a non-channel reference added after the preflight", non_channel)):
        scene = reset()
        before = dict((k, graph_state(g)) for k, g in (("head", scene.head_graph), ("tail", scene.tail_graph)))
        on_open(scene, mutate)
        _, error = attempt(run_apply, ns, trial_record())
        after = dict((k, graph_state(g)) for k, g in (("head", scene.head_graph), ("tail", scene.tail_graph)))
        check("I2 %s -> refused before Operate(), verified Abort, values restored" % label,
              isinstance(error, RuntimeError) and not isinstance(error, ns["ProdRecoveryUnverifiedError"])
              and not scene.operate_log and not scene.dm.stack and u"shared or ambiguous" in abort_log()[-1]
              and u"restored=True" in abort_log()[-1] and after == before, (error, abort_log()[-1:]))
    scene = reset()
    on_open(scene, lambda s: setattr(s, "context_ok", False))
    _, error = attempt(run_apply, ns, trial_record())
    check("I2 the operation context changes after the preflight -> refused before Operate(), verified Abort",
          isinstance(error, RuntimeError) and not scene.operate_log and not scene.dm.stack
          and u"changed" in abort_log()[-1] and u"restored=True" in abort_log()[-1], (error, abort_log()[-1:]))

    # Changed after the transaction opened (identity no longer the planned binding).
    for label, mutate, text in (("output re-pointed to another expression", repoint_output, u"binding changed"),
                                ("output re-targeted away from the bone", retarget_output, u"binding changed"),
                                ("expression text replaced", change_expr_text, u"was replaced"),
                                ("expression limits changed", change_limits, u"limits changed")):
        scene = reset()
        before = dict((k, graph_state(g)) for k, g in (("head", scene.head_graph), ("tail", scene.tail_graph)))
        on_open(scene, mutate)
        _, error = attempt(run_apply, ns, trial_record())
        after = dict((k, graph_state(g)) for k, g in (("head", scene.head_graph), ("tail", scene.tail_graph)))
        check("I3 %s -> refused before Operate(), verified Abort (graph values and wiring restored)" % label,
              isinstance(error, RuntimeError) and not scene.operate_log and not scene.dm.stack
              and text in abort_log()[-1] and u"restored=True" in abort_log()[-1] and after == before
              and scene.head_graph["output"].raw("fromElement") is scene.head_graph["expression"]
              and scene.head_graph["output"].raw("toElement") is scene.head_graph["transform"],
              (error, abort_log()[-1:]))

    for label, mutate in (("input log and layer replaced (equal values)", m.replace_input_log),
                          ("output log and layer replaced (equal contents)", m.replace_output_log)):
        scene = reset()
        on_open(scene, mutate)
        _, error = attempt(run_apply, ns, trial_record())
        check("I4 %s -> refused before Operate() (by the existing authored check or the trial's identity check); "
              "nothing committed; the fake Abort cannot undo an object replacement, so recovery is reported "
              "unverified, never success" % label,
              isinstance(error, RuntimeError) and not scene.operate_log and not scene.dm.stack
              and (u"was replaced" in abort_log()[-1] or u"authored-state verification" in abort_log()[-1]),
              (error, abort_log()[-1:]))

    # Cast fallback.
    def cast_to(result):
        m._Vs.CastElementAsDmeExpressionOperator = staticmethod(result)

    class Proxy(object):
        def __init__(self, element, operate=True):
            self.element = element
            self.this = element.this
            if operate:
                self.Operate = lambda: m.FakeExpression.Operate(element)

        def GetHandle(self):
            return self.element.GetHandle()

    for label, caster, ok in (("the same element", lambda e: Proxy(e), True),
                              ("a different element", lambda e: Proxy(m.Scene.current.tail_graph["expression"]), False),
                              ("nothing", lambda e: None, False),
                              ("an exception", lambda e: (_ for _ in ()).throw(RuntimeError("cast")), False),
                              ("the same element without Operate", lambda e: Proxy(e, operate=False), False)):
        scene = reset()
        scene.head_graph["expression"].Operate = None
        cast_to(caster)
        result, error = attempt(run_apply, ns, trial_record(tail=0.8))
        if ok:
            check("I5 non-callable Operate, cast to %s -> operated through the cast, committed" % label,
                  error is None and result["phase"] == u"verification-pending"
                  and operated(scene) == [u"bip_head_scale_rescale"], (error, operated(scene)))
        else:
            check("I5 non-callable Operate, cast to %s -> refused, verified Abort" % label,
                  isinstance(error, RuntimeError) and not scene.operate_log and not scene.dm.stack
                  and u"cannot be operated" in abort_log()[-1] and u"restored=True" in abort_log()[-1],
                  (error, abort_log()[-1:]))
    del m._Vs.CastElementAsDmeExpressionOperator

    scene = reset()
    scene.extra_clips.append(m.FakeElement(u"DmeFilmClip", u"not channels", channels=[]))
    peer_clip_with(scene, fromElement=m.FakeElement(u"DmElement", u"x", value=0.0), fromAttribute=u"value",
                   toElement=m.FakeElement(u"DmeExpressionOperator", u"unrelated"), toAttribute=u"value")
    result, outcome = apply_and_settle(ns, trial_record())
    check("I6 unrelated clips and channels are not mistaken for sharing -> verified Apply",
          outcome is not None and outcome["phase"] == u"committed-verified", (result["phase"], outcome))


# ---------------------------------------------------------------------------
# Section N -- peer isolation, unchanged scales, mode 1, created graphs, no-op, Expression presets
# ---------------------------------------------------------------------------

def peer_state(scene):
    return graph_state(scene.peer_graph)


def section_isolation(ns):
    scene = reset(peer=True)
    peer_before = peer_state(scene)
    result, outcome = apply_and_settle(ns, trial_record())
    handles = sorted(e["handle"] for e in scene.operate_log)
    check("N1 same-model peer (same names, own clip): exactly the target's head and tail expressions are operated, "
          "never the peer's",
          handles == sorted([scene.head_graph["expression"]._handle, scene.tail_graph["expression"]._handle])
          and scene.peer_graph["expression"]._handle not in handles, (handles, operated(scene)))
    check("N1 every peer field unchanged through Apply, CPM's refresh and the deferred verification",
          outcome["phase"] == u"committed-verified" and peer_state(scene) == peer_before
          and close(graph_state(scene.head_graph)["physical"], 1.33), (outcome, peer_state(scene)))

    scene = reset()
    tail_before = graph_state(scene.tail_graph)
    result, outcome = apply_and_settle(ns, trial_record(tail=0.8))
    check("N2 an unchanged mode-3 scale (tail) is not written or operated; only the changed head is",
          operated(scene) == [u"bip_head_scale_rescale"] and graph_state(scene.tail_graph) == tail_before
          and outcome["phase"] == u"committed-verified", (operated(scene), outcome))

    for label, kw, record in (("changed mode-1 scale", {"head_mode": 1}, trial_record(head=1.25, tail=0.8)),
                              ("created implicit-neutral graph", {}, trial_record(head=1.13, tail=0.8, pelvis=1.4)),
                              ("FLEX-only change", {}, trial_record(head=1.13, tail=0.8, smile=0.5))):
        with Baseline(ns):
            base_scene = reset(**kw)
            base_result, base_outcome = apply_and_settle(ns, record)
            base_digest, base_writes = base_scene.digest(), list(base_scene.cpm_writes)
        scene = reset(**kw)
        result, outcome = apply_and_settle(ns, record)
        same_shape = (result["phase"] == base_result["phase"] and (outcome or {}).get("phase")
                      == (base_outcome or {}).get("phase"))
        check("N3 %s: no expression operated; outcome and writes identical to the source before the candidate"
              % label, not scene.operate_log and same_shape and scene.cpm_writes == base_writes
              and len(scene.dm.stack) == len(base_scene.dm.stack),
              (operated(scene), result["phase"], base_result["phase"]))
        # Element handles differ between scenes; compare values through the graph states instead.
        check("N3 %s: resulting graph values identical to the baseline" % label,
              graph_state(scene.head_graph) == graph_state(base_scene.head_graph)
              and graph_state(scene.spine_graph) == graph_state(base_scene.spine_graph)
              and scene.created == base_scene.created and scene.flex == base_scene.flex)

    scene = reset()
    before = scene.digest()
    result = run_apply(ns, trial_record(head=1.13, tail=0.8))
    check("N4 matching Apply is a verified no-op: no transaction, no Operate, nothing changed",
          result["phase"] == u"no-op" and not scene.operate_log and "StartUndo" not in scene.events
          and scene.digest() == before, result["phase"])

    expression_record = {"kind": u"expression", "name": u"Happy", "preset_id": u"p-2", "values": {u"flex.Smile": 0.5}}
    with Baseline(ns):
        base_scene = reset()
        base_result = run_apply(ns, expression_record)
    scene = reset()
    result = run_apply(ns, expression_record)
    check("N5 Expression Preset Apply: no scale plan, no expression operated, outcome identical to the baseline",
          not scene.operate_log and result["phase"] == base_result["phase"]
          and scene.cpm_writes == base_scene.cpm_writes
          and [(e[0], e[1]) for e in scene.dm.stack] == [(e[0], e[1]) for e in base_scene.dm.stack],
          (result["phase"], scene.dm.stack))

    trial_names = ("prod_bs_operate_bound_expression", "prod_bs_expression_references",
                   "prod_bs_expression_reference_guard", "prod_bs_revalidate_operation")
    callers = sorted(n for n in m.APP.top if any(t in m.APP.top_text(n) for t in trial_names)
                     and n not in trial_names)
    check("N6 the correction and guard are reachable only from the Body existing-scale write and prod_apply's "
          "pre-Undo guard (no Expression, Pose, created-graph, shared-callback or record-format path)",
          callers == ["prod_apply", "prod_bs_write_existing_scale"], callers)
    apply_src = m.APP.top_text("prod_apply")
    guard_at = apply_src.index("prod_bs_expression_reference_guard(")
    check("N6 in prod_apply the guard runs after the no-op return and before StartUndo, only for static mode-3 items",
          apply_src.index("return prod_outcome(") < guard_at < apply_src.index("StartUndo(")
          and u"\"static_output_mode\"" in apply_src[guard_at - 400:guard_at])
    check("N6 no vsUtils import and no global element equality/hash change in the application",
          not any(x in m.APP.raw.decode("utf-8") for x in (u"import vsUtils", u"from vsUtils", u"vsUtils.",
                                                           u"CDmElement.__eq__", u"CDmElement.__hash__")))
    methods = [n for n in m.APP.methods("ProdWindow") if any(t in m.APP.method_text("ProdWindow", n)
                                                              for t in trial_names)]
    check("N6 no window method or callback references the trial", not methods, methods)


# ---------------------------------------------------------------------------
# Section C -- callbacks: stale, duplicate and changed context (Q1 model)
# ---------------------------------------------------------------------------

def section_callbacks(ns, Window):
    checking = ns["PROD_APPLY_CHECKING_COPY"]
    unverified_copy = ns["PROD_APPLY_UNVERIFIED_COPY"]
    scene = reset()
    w = Window(trial_record())
    w.apply_kind(u"body")
    check("C1 pending Apply keeps the operation and shows only the checking status",
          w.operation is not None and w.statuses[-1] == (checking, u"neutral") and len(m.Timer.queue) == 1)
    m.Timer.run_all()
    check("C1 the one callback verifies the physical map: 'Body Preset applied.', ended once",
          w.statuses[-1] == (u"Body Preset applied.", u"success") and w.operation is None and len(m.results()) == 1
          and m.has(m.outcomes()[-1], u"outcome", u"verified"), (w.statuses[-1:], m.outcomes()))
    w.apply_verification_turn((1, 1))
    check("C2 a duplicate callback after completion is harmless",
          len(m.results()) == 1 and w.operation is None and u"PROD_APPLY_VERIFY_STALE" in m.log_text())
    scene.head = 0.375
    w.record = trial_record(head=1.5)
    w.apply_kind(u"body")
    newer = w.operation
    w.apply_verification_turn((1, 1))
    check("C2 a stale callback never ends a newer pending operation",
          w.operation is newer and newer is not None and len(m.results()) == 1)
    m.Timer.run_all()
    check("C2 the newer operation still finishes once, verified",
          w.operation is None and len(m.results()) == 2 and w.statuses[-1] == (u"Body Preset applied.", u"success"))

    for label, mutate, reason in (
            ("context changed", lambda s: setattr(s, "context_ok", False), u"context-changed"),
            ("evaluation time moved", lambda s: setattr(s, "head", 0.5), u"time-changed"),
            ("authored value changed", lambda s: s.head_graph["control"].put("value", 0.3), u"authored"),
            ("expression limits changed", lambda s: s.head_graph["expression"].put("hi", 9.0), u"authored")):
        scene = reset()
        result = run_apply(ns, trial_record())
        mutate(scene)
        writes = list(scene.cpm_writes)
        outcome = ns["prod_apply_deferred_verify"](result["pending"])
        check("C3 %s before the callback -> committed-unverified (%s); no rewrite, no Undo, no further Operate"
              % (label, reason),
              outcome["phase"] == u"committed-unverified" and outcome.get("reason") == reason
              and scene.cpm_writes == writes and scene.dm.undo_calls == 0 and len(scene.operate_log) == 2, outcome)

    scene = reset()
    w = Window(trial_record())
    w.apply_kind(u"body")
    m.FakeApp.state[0] = "modal"
    m.Timer.run_all()
    m.FakeApp.state[0] = "none"
    check("C4 modal at the callback -> unverified 'modal-active' without scene verification",
          w.operation is None and u"modal-active" in m.outcomes()[-1] and w.statuses[-1] == (unverified_copy, u"error"),
          m.outcomes()[-1:])
    scene = reset()
    w = Window(trial_record())
    w.apply_kind(u"body")
    event = w.close()
    check("C5 close while pending -> closed-before-verification, ended once",
          w.operation is None and u"closed-before-verification" in m.outcomes()[-1] and len(m.results()) == 1
          and event.state == "ignored", m.outcomes()[-1:])
    m.Timer.run_all()


# ---------------------------------------------------------------------------

def main():
    print("Interpreter: %s" % sys.version.split()[0])
    m.APP = route.AppSource(route.APP_PATH)
    print("Candidate app sha256: %s" % hashlib.sha256(m.APP.raw).hexdigest())
    ns, methods = m.build_namespace(m.APP)
    Window = m.make_window_class(methods)
    for section in (lambda: section_propagation(ns), lambda: section_stale(ns, Window), lambda: section_abort(ns),
                    lambda: section_identity(ns), lambda: section_isolation(ns),
                    lambda: section_callbacks(ns, Window)):
        try:
            section()
        except Exception:
            check("section.completed", False, traceback.format_exc())
    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        sys.exit(2)
    sys.exit(main())
