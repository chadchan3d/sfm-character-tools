# -*- coding: utf-8 -*-
"""F-01 Pose Library M1, stage C: offline qualification of the CPM integration seams in the application source.
Design authority: F-01 M1 Implementation Addendum R2.1 sections 1.3, 8, 9.3 and 10; Owner authorization of stage C
(2026-11-02), including the independent-persistence requirement: a saved pose applies to an independently resolved
destination instance without the source animation set or shot.

Technique: built on the M-06 W1 harness (test_cpm_app_m06_instance_resolution), whose namespace runs the real
production selection, instance resolution, operation context and window lifecycle (operation_begin, guard,
current, the shared continuation turn) over a fake two-instance scene. On top of it the stage A, B and C blocks and
the stage C ProdWindow methods are extracted verbatim. Simulated boundaries only: the native scene (W1's fake),
Qt scheduling (m05.Timer), the library root and MAINMENU folders (temporary), and the stage D scene paths
(prod_pose_capture, prod_pose_apply, prod_pose_verify_applied), which stage C defines as refusals and which this
suite replaces with recording fakes where a lifecycle path needs a result. Nothing here touches SFM or the real
CPM library (hashed before and after).

Usage: --phase=run (Python 2.7.5 and Python 3.10).
"""
from __future__ import print_function

import copy
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import traceback

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import test_cpm_app_canonical_route as route  # noqa: E402
import test_cpm_app_m05_static_scale as m05  # noqa: E402
import test_cpm_app_m06_instance_resolution as w1  # noqa: E402
import test_cpm_app_f01_pose_core as core  # noqa: E402

try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

STAGE_C_START = u"# F-01 Pose Library M1, stage C: CPM integration seams"
STAGE_C_END = u"# === end of F-01 stage C block ==="
STAGE_D_START = u"# F-01 Pose Library M1, stage D: the left-arm live layer"
STAGE_D_END = u"# === end of F-01 stage D block ==="
STAGE_B_START = u"# F-01 Pose Library M1, stage B: offline pose library"
STAGE_B_END = u"# === end of F-01 stage B block ==="
POSE_METHODS = ["pose_registry_mode", "pose_guard", "apply_pose", "save_pose", "pose_begin_verification",
                "pose_finish_verification"]
PAGE_METHODS = ["refresh_pose_view", "selected_pose", "refresh_pose_buttons", "apply_selected_pose"]
SHARED_METHODS = ["operation_default_error_copy", "apply_verification_turn", "apply_finish_verification", "apply_close_pending_verification",
                  "operation_continuation_owned", "apply_begin_verification", "apply_kind", "guard"]
SCENE_WRITE_TOKENS = ("SetKeyValue", "InsertKey", "SetKey(", "StartUndo", "FinishUndo", "AbortUndoableOperation",
                      "SetValue", "RemoveKey", "SetCurrentTime", "SetHeadTime")
REFUSAL = u"Pose records are handled only by the Pose Library."
REAL_LIBRARY = os.path.join(os.path.expanduser("~"), "Documents", "SFM Character Preset Manager")

RESULTS = []


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


def outcome(fn):
    """('ok', result) or (exception type name, code, message)."""
    try:
        return ("ok", fn())
    except Exception as exc:
        return (type(exc).__name__, getattr(exc, "code", None), _TEXT(exc))


def refused(name, result, code=None, text=None):
    ok = result[0] != "ok" and (code is None or result[1] == code) and (text is None or text in result[2])
    check(name, ok, result)


class Fakes(object):
    """Recording stand-ins for the stage D scene paths (stage C defines them as refusals)."""
    captures = []
    applies = []
    verifies = []


# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------

def build(app):
    ns, methods = w1.build_namespace(app)
    for name, ok, value in w1.RESULTS:
        check("w1." + name, ok, value)
    del w1.RESULTS[:]
    for start, end, label in ((core.BLOCK_START, core.BLOCK_END, "stage_a"), (STAGE_B_START, STAGE_B_END, "stage_b"),
                              (STAGE_C_START, STAGE_C_END, "stage_c"), (STAGE_D_START, STAGE_D_END, "stage_d")):
        block, _ = core.extract_block(route.APP_PATH, start, end)
        route._run_source(block, label, ns)
    # Real p02 store helpers and the CPM path helpers used by stage C.
    for name in ("_PROD_PRIVATE_WINDLL", "prod_private_windll", "p02_ensure_dir", "p02_json_text", "p02_unique_temp", "p02_safe_write_json", "prod_paths",
                 "prod_label", "prod_key", "prod_preset_dir", "p03_now_stamp", "prod_apply_deferred_unverified",
                 "prod_outcome"):
        if name not in ns:
            route._run_source(app.top_text(name), "app:%s" % name, ns)
    for name in POSE_METHODS + PAGE_METHODS + SHARED_METHODS:
        route._run_source(app.method_text("ProdWindow", name), "ProdWindow.%s" % name, ns, methods)
    ns["QtCore"].QTimer = m05.Timer
    return ns, methods


def block_text(start, end):
    return core.extract_block(route.APP_PATH, start, end)


def fixture_registry(ns, mainmenu):
    """The shipped registry with the synthetic W1 model listed in krystal-v1 (a test pin, not the product pin)."""
    reg = json.loads(core.read(core.REGISTRY_PATH).decode("utf-8"))
    reg["rig_classes"]["krystal-v1"]["models"].append({"checksum": None, "model_ref": w1.MODEL})
    raw = ns["prod_pose_canonical_bytes"](reg)
    with open(os.path.join(mainmenu, ns["PROD_POSE_REGISTRY_FILENAME"]), "wb") as f:
        f.write(raw)
    return raw


def golden():
    return json.loads(core.read(os.path.join(core.W2_DIR, "tests", "fixtures", "golden_left_arm_pose.f01w2.json"))
                      .decode("utf-8"))


def pose_payload(ns, regions):
    return copy.deepcopy(core.make_record(ns, golden(), regions)["pose"])


def install_fakes(ns, phase=u"verification-pending", capture_regions=None, verify_phase=None, apply_raises=None):
    del Fakes.captures[:]
    del Fakes.applies[:]
    del Fakes.verifies[:]

    def capture(identity, authorization, regions, reg, pinned_time=None):
        Fakes.captures.append((dict(identity), authorization, list(regions)))
        return pose_payload(ns, tuple(capture_regions or regions))

    def apply_(identity, authorization, item, reg, phase_callback=None):
        Fakes.applies.append((dict(identity), authorization, item))
        if apply_raises is not None:
            raise apply_raises
        result = {"phase": phase}
        if phase == u"verification-pending":
            result["pending"] = {u"stage_d": u"fixture"}
        return result

    def verify(pending):
        Fakes.verifies.append(pending)
        if verify_phase is None:
            return ns["prod_apply_deferred_unverified"](u"verify-unavailable")
        return {"phase": verify_phase}

    ns["prod_pose_capture"] = capture
    ns["prod_pose_apply"] = apply_
    ns["prod_pose_verify_applied"] = verify


def restore_stubs(ns, app):
    for name in ("prod_pose_capture", "prod_pose_apply", "prod_pose_verify_applied"):
        route._run_source(app.top_text(name), "app:%s" % name, ns)


def window(ns, Window, scene, inst):
    win = Window()
    win.statuses = []
    w1.select(ns, win, inst)
    return win


def last_status(win):
    return win.statuses[-1] if win.statuses else None


def own_items(ns, win, reg):
    sel = ns["prod_pose_selected_library"](win.identity)
    return ns["prod_pose_discover"](sel[u"char_dir"], sel[u"character_key"], reg)[u"items"]


def ended(win):
    return win.operation is None and not win.busy and getattr(win, "apply_continuation", None) is None


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def section_static(app):
    block, names = block_text(STAGE_C_START, STAGE_C_END)
    check("C0.stage_c_block_names_equal_route_allow_list", set(names) == route.F01_STAGEC_NEW_TOP,
          sorted(set(names) ^ route.F01_STAGEC_NEW_TOP))
    texts = [block] + [app.method_text("ProdWindow", m) for m in POSE_METHODS]
    joined = u"\n".join(texts)
    check("C0.no_scene_write_or_undo_call_in_stage_c", not [t for t in SCENE_WRITE_TOKENS if t in joined],
          [t for t in SCENE_WRITE_TOKENS if t in joined])
    # Independent persistence: stage C never reads the pose's source provenance, and authorization never uses the
    # flex semantic scope or the preset authorization.
    check("C0.stage_c_never_reads_pose_source", not re.search(r"""["']source["']""", joined))
    auth = app.top_text("prod_pose_authorize")
    check("C0.authorize_never_uses_flex_scope_or_preset_authorization",
          not [t for t in ("scope", "prod_cpm_authorize_operation", "membership", "semantic") if t in
               auth.split('"""')[0] + auth.split('"""')[-1]])
    check("C0.authorize_reuses_m06_revalidation", "prod_validate_context_token(" in auth
          and "prod_instance_token(" in auth)
    gate = app.top_text("prod_pose_context_gate")
    check("C0.deferred_gate_reuses_m06_instance_match", "prod_context_token_matches(" in gate)
    turn = app.method_text("ProdWindow", "apply_verification_turn")
    check("C0.shared_turn_dispatches_pose_and_keeps_m05", "prod_pose_deferred_verify(" in turn
          and "prod_apply_deferred_verify(" in turn)
    for m in ("apply_pose", "save_pose"):
        check("C0.%s_runs_through_pose_guard_and_guard" % m, "self.pose_guard(" in app.method_text("ProdWindow", m))
    check("C0.pose_guard_uses_window_guard", "self.guard(" in app.method_text("ProdWindow", "pose_guard"))
    check("C0.registry_pin_is_the_committed_file",
          app.top_text("PROD_POSE_REGISTRY_SHA256").count(core.sha(core.read(core.REGISTRY_PATH))) == 1)


def section_seams(ns, app, methods):
    ident = {"model": w1.MODEL, "checksum": w1.CHECKSUM, "animset_name": u"zz_target"}
    w1.fresh_library()
    refused("C1.prod_preset_dir_refuses_pose", outcome(lambda: ns["prod_preset_dir"](ident, u"pose")), text=REFUSAL)
    paths = ns["prod_paths"](ident)
    check("C1.prod_preset_dir_body_expression_unchanged",
          ns["prod_preset_dir"](ident, u"body") == paths["body"]
          and ns["prod_preset_dir"](ident, u"expression") == paths["expression"])
    check("C1.prod_paths_pose_is_the_store_folder",
          paths["pose"] == ns["prod_pose_library_paths"](paths["char"])[u"poses"]
          and paths["pose"] == os.path.join(paths["char"], u"Poses"))
    # The real preset authorization (the W1 namespace replaces it with a fixture): pose refuses before any
    # authority access; kind=None and Body still reach the authority adapter (unchanged behaviour).
    real = {}
    route._run_source(app.top_text("prod_cpm_authorize_operation"), "app:prod_cpm_authorize_operation", real)
    fn = real["prod_cpm_authorize_operation"]
    reached = []

    class Reached(Exception):
        pass

    def adapter():
        reached.append(1)
        raise Reached()
    fn.__globals__.update({"u": ns["u"], "prod_cpm_import_adapter": adapter, "P03_KIND_BODY": u"body",
                           "PROD_CPM_STALE_SCOPE_MESSAGE": u"stale"})
    scope = {"authority": {"provider_sha256": u"f" * 64}, "semantic": {"rows": []}}
    refused("C1.preset_authorization_refuses_pose_before_authority",
            outcome(lambda: fn(ident, scope, u"pose", u"Apply Preset")), text=REFUSAL)
    check("C1.preset_authorization_pose_never_reached_authority", reached == [])
    r_none = outcome(lambda: fn(ident, scope, None, u"Review flex edit"))
    r_body = outcome(lambda: fn(ident, scope, u"body", u"Apply Preset"))
    check("C1.preset_authorization_kind_none_and_body_unchanged",
          r_none[0] == "Reached" and r_body[0] == "Reached" and reached == [1, 1], (r_none, r_body))
    calls = list(w1.Authority.calls)
    refused("C1.prod_apply_refuses_pose_record",
            outcome(lambda: ns["prod_apply"](ident, {"kind": u"pose"})), text=REFUSAL)
    check("C1.prod_apply_pose_never_authorized", w1.Authority.calls == calls)

    class Dummy(object):
        operation = None
    for name in ("selected_or_none", "refresh_preset_view"):
        route._run_source(app.method_text("ProdWindow", name), "ProdWindow.%s" % name, ns, real)
        refused("C1.%s_refuses_pose" % name, outcome(lambda n=name: real[n](Dummy(), u"pose")), text=REFUSAL)
    d = Dummy()
    refused("C1.apply_kind_refuses_pose", outcome(lambda: methods["apply_kind"](d, u"pose")), text=REFUSAL)
    check("C1.apply_kind_pose_began_no_operation", d.operation is None)
    refused("C1.apply_begin_verification_refuses_pose",
            outcome(lambda: methods["apply_begin_verification"](d, u"pose", {})), text=REFUSAL)
    # Tab strip (Addendum 9.3): padding 14 -> 8 px, min-width removed; everything else unchanged.
    sheets = []

    class Tabs(object):
        def setStyleSheet(self, text):
            sheets.append(text)
    real_tab = {}
    route._run_source(app.top_text("tool_apply_tab_style"), "app:tool_apply_tab_style", real_tab)
    real_tab["tool_apply_tab_style"](Tabs())
    base = route.AppSource(route.BASELINE_PATH)
    route._run_source(base.top_text("tool_apply_tab_style"), "baseline:tool_apply_tab_style", real_tab)
    real_tab["tool_apply_tab_style"](Tabs())
    new, old = sheets
    check("C1.tab_padding_11px_and_no_min_width", "padding: 6px 11px;" in new and "min-width" not in new, new)
    check("C1.tab_style_otherwise_unchanged",
          new == old.replace("padding: 6px 14px;", "padding: 6px 11px;").replace(
              "            min-width: 96px;\n", ""), (old, new))


def section_registry(ns, mainmenu):
    raw = core.read(core.REGISTRY_PATH)
    reg = outcome(lambda: ns["prod_pose_load_registry"](core.REGISTRY_PATH))
    check("C2.shipped_registry_loads_under_the_product_pin", reg[0] == "ok"
          and reg[1][u"_sha256"] == ns["PROD_POSE_REGISTRY_SHA256"], reg[:2])
    bad = os.path.join(mainmenu, "tampered.json")
    with open(bad, "wb") as f:
        f.write(raw.replace(b"krystal-v1", b"krystal-v2", 1))
    refused("C2.tampered_registry_refused", outcome(lambda: ns["prod_pose_load_registry"](bad)), u"registry")
    refused("C2.missing_registry_refused",
            outcome(lambda: ns["prod_pose_load_registry"](os.path.join(mainmenu, "absent.json"))), u"registry")
    check("C2.registry_path_is_mainmenu", ns["prod_pose_registry_path"]() ==
          os.path.join(mainmenu, ns["PROD_POSE_REGISTRY_FILENAME"]))
    if reg[0] == "ok":
        ident = {"model": w1.MODEL, "checksum": w1.CHECKSUM}
        check("C2.synthetic_model_not_listed_in_the_product_registry",
              ns["prod_pose_rig_class"](reg[1], ident["model"], ident["checksum"]) is None)


def section_authorization(ns, Window, reg):
    s = w1.twin_scene()
    w1.fresh_library()
    win = window(ns, Window, s, s.target)
    ctx = w1.begin(win, u"Save Pose")
    ident = dict(win.identity)
    calls = list(w1.Authority.calls)
    a = outcome(lambda: ns["prod_pose_authorize"](ctx, ident, reg, u"production", u"Save Pose"))
    check("C3.authorize_binds_pinned_instance_registry_and_class", a[0] == "ok"
          and a[1][u"context"] is ctx and a[1][u"registry_sha256"] == reg[u"_sha256"]
          and a[1][u"destination"][u"rig_class"] == u"krystal-v1" and a[1][u"record"] is None
          and a[1][u"mode"] == u"production"
          and [(m[u"region"], m[u"status"]) for m in a[1][u"mappings"]] == [(u"left_arm", u"qualified")], a)
    check("C3.authorize_pins_the_selected_target_instance",
          a[0] == "ok" and a[1][u"context"]["instance"]["animset_key"][1] == s.target.animset._handle)
    q = ns["prod_pose_authorize"](ctx, ident, reg, u"qualification", u"Save Pose")
    check("C3.qualification_mode_exposes_experimental_mappings_only_there",
          sorted((m[u"region"], m[u"status"]) for m in q[u"mappings"]) ==
          [(u"left_arm", u"qualified"), (u"right_arm", u"experimental")])
    check("C3.authorize_never_calls_flex_semantic_authority", w1.Authority.calls == calls)
    refused("C3.no_context_refused", outcome(lambda: ns["prod_pose_authorize"](None, ident, reg, u"production",
                                                                              u"Save Pose")), u"no-instance")
    refused("C3.unknown_label_refused", outcome(lambda: ns["prod_pose_authorize"](ctx, ident, reg, u"production",
                                                                                 u"Apply Expression")), u"label")
    refused("C3.apply_without_record_refused",
            outcome(lambda: ns["prod_pose_authorize"](ctx, ident, reg, u"production", u"Apply Pose")),
            u"record-changed")
    other = dict(ident, checksum=ident["checksum"] + 1)
    refused("C3.identity_differs_from_pinned_context_refused",
            outcome(lambda: ns["prod_pose_authorize"](ctx, other, reg, u"production", u"Save Pose")), u"stale")
    raw_real = core.read(core.REGISTRY_PATH)
    real = ns["prod_pose_registry_parse"](raw_real, core.sha(raw_real))
    refused("C3.unlisted_character_refused_not_qualified",
            outcome(lambda: ns["prod_pose_authorize"](ctx, ident, real, u"production", u"Save Pose")),
            u"not-qualified")
    w1.end(win)
    # Peer isolation: the peer's own selection pins the peer, never the target.
    win2 = window(ns, Window, s, s.peer)
    ctx2 = w1.begin(win2, u"Save Pose")
    p = ns["prod_pose_authorize"](ctx2, dict(win2.identity), reg, u"production", u"Save Pose")
    check("C3.peer_selection_pins_the_peer", p[u"context"]["instance"]["animset_key"][1] == s.peer.animset._handle
          and p[u"context"]["animset_id"] != ctx["animset_id"])
    w1.end(win2)
    # Instance deleted, then a new SFM session: the old pinned context no longer authorizes.
    w1.delete_instance(s, s.target)
    refused("C3.deleted_instance_refused_stale",
            outcome(lambda: ns["prod_pose_authorize"](ctx, ident, reg, u"production", u"Save Pose")), u"stale")
    session = ns["PROD_INSTANCE_SESSION"]
    ns["PROD_INSTANCE_SESSION"] = u"later-session"
    try:
        refused("C3.earlier_session_context_refused_stale",
                outcome(lambda: ns["prod_pose_authorize"](ctx2, dict(win2.identity), reg, u"production",
                                                          u"Save Pose")), u"stale")
    finally:
        ns["PROD_INSTANCE_SESSION"] = session


def section_save(ns, app, Window, reg):
    s = w1.twin_scene()
    w1.fresh_library()
    win = window(ns, Window, s, s.target)
    restore_stubs(ns, app)
    win.save_pose(u"Arms Up", [u"left_arm"])
    check("C4.real_capture_refuses_a_character_without_the_arm_rig",
          last_status(win)[1] == u"error" and ended(win), win.statuses[-1:])
    check("C4.refused_save_wrote_nothing", not os.path.isdir(ns["prod_paths"](win.identity)["pose"]))
    install_fakes(ns)
    win.save_pose(u"Arms Up", [u"left_arm"])
    items = own_items(ns, win, reg)
    check("C4.save_through_cpm_lifecycle_writes_one_own_pose", len(items) == 1 and items[0][u"name"] == u"Arms Up"
          and items[0][u"character_key"] == ns["prod_key"](w1.MODEL) and ended(win), (items, win.statuses))
    check("C4.save_status", last_status(win) == (u"Pose saved: Arms Up (Left arm).", u"success"), win.statuses)
    check("C4.capture_received_the_pinned_target_authorization", len(Fakes.captures) == 1
          and Fakes.captures[0][1][u"context"]["instance"]["animset_key"][1] == s.target.animset._handle
          and Fakes.captures[0][2] == [u"left_arm"])
    check("C4.save_used_the_cpm_library_folder",
          os.path.dirname(items[0][u"path"]) == ns["prod_paths"](win.identity)["pose"] if items else False)
    install_fakes(ns, capture_regions=(u"left_arm",))
    win.save_pose(u"Both", [u"left_arm", u"right_arm"])
    check("C4.capture_of_fewer_regions_refused_nothing_saved",
          len(own_items(ns, win, reg)) == 1 and win.statuses[-1][1] == u"error" and ended(win), win.statuses[-1:])
    install_fakes(ns)
    win.save_pose(u"arms up", [u"left_arm"])
    check("C4.duplicate_name_refused_by_store", len(own_items(ns, win, reg)) == 1 and win.statuses[-1][1] == u"error")
    win.identity = None
    win.save_pose(u"No Character", [u"left_arm"])
    check("C4.no_character_refused", last_status(win) == (ns["PROD_POSE_MESSAGES"][u"no-character"], u"error")
          and not Fakes.captures[1:], win.statuses[-1:])
    w1.select(ns, win, s.target)
    win.selection_token = None
    win.save_pose(u"No Instance", [u"left_arm"])
    check("C4.unpinnable_instance_refused_before_capture", win.statuses[-1][1] == u"error"
          and len(Fakes.captures) == 1 and ended(win), win.statuses[-1:])


def saved_item(ns, win, reg, name=u"Arms Up", regions=(u"left_arm",)):
    install_fakes(ns)
    win.save_pose(name, list(regions))
    return [i for i in own_items(ns, win, reg) if i[u"name"] == name][0]


def section_apply(ns, app, Window, reg):
    s = w1.twin_scene()
    w1.fresh_library()
    win = window(ns, Window, s, s.target)
    item = saved_item(ns, win, reg)
    before = core.read(item[u"path"])
    restore_stubs(ns, app)
    # The production build with a registry whose left-arm mapping is still experimental refuses before writing.
    path = os.path.join(ns["prod_cpm_mainmenu_dir"](), ns["PROD_POSE_REGISTRY_FILENAME"])
    shipped, pin = core.read(path), ns["PROD_POSE_REGISTRY_SHA256"]
    draft = json.loads(shipped.decode("utf-8"))
    draft["mappings"][0].update(status=u"experimental", evidence=None)
    raw = ns["prod_pose_canonical_bytes"](draft)
    with open(path, "wb") as f:
        f.write(raw)
    ns["PROD_POSE_REGISTRY_SHA256"] = core.sha(raw)
    try:
        win.apply_pose(item)
    finally:
        with open(path, "wb") as f:
            f.write(shipped)
        ns["PROD_POSE_REGISTRY_SHA256"] = pin
    check("C5.real_apply_refuses_in_the_production_build_experimental_mappings",
          last_status(win)[1] == u"error" and u"isn't supported" in last_status(win)[0] and ended(win),
          win.statuses[-1:])
    # The shipped registry: the qualified left-arm mapping passes authorization and the mapping check (this fake
    # scene has no SFM Undo history, so the real Apply stops at the scene baseline, before writing).
    win.apply_pose(item)
    check("C5.real_apply_admits_the_qualified_left_arm_mapping_in_production",
          last_status(win)[1] == u"error" and u"isn't supported" not in last_status(win)[0] and ended(win)
          and core.read(item[u"path"]) == before, win.statuses[-1:])
    # Committed with a pending check: ownership passes to the shared turn.
    install_fakes(ns)
    del m05.Timer.queue[:]
    win.apply_pose(item)
    pending_owned = win.operation is not None and win.operation_continuation_owned() and \
        win.apply_continuation["kind"] == u"pose"
    check("C5.pending_apply_keeps_operation_until_turn", pending_owned and len(m05.Timer.queue) == 1)
    check("C5.checking_status", last_status(win) == (ns["PROD_POSE_CHECKING_COPY"], u"neutral"), win.statuses[-1:])
    auth = Fakes.applies[0][1] if Fakes.applies else {}
    check("C5.apply_authorization_binds_record_revision_and_target",
          auth.get(u"record", {}).get(u"revision") == item[u"revision"]
          and auth[u"record"][u"preset_id"] == item[u"preset_id"]
          and auth[u"context"]["instance"]["animset_key"][1] == s.target.animset._handle, auth.get(u"record"))
    win.apply_pose(item)
    check("C5.second_action_refused_while_check_pending",
          last_status(win)[1] == u"warning" and len(Fakes.applies) == 1, win.statuses[-1:])
    token = win.apply_continuation["token"]
    m05.Timer.run_all()
    check("C5.turn_ran_pose_verification_not_preset_verification", len(Fakes.verifies) == 1
          and Fakes.verifies[0][u"authorization"] is auth and Fakes.verifies[0][u"stage_d"] == u"fixture")
    check("C5.unverified_result_published_and_operation_ended",
          last_status(win) == (ns["PROD_POSE_MESSAGES"][u"committed-unverified"] % {u"name": u"Arms Up"}, u"error")
          and ended(win), win.statuses[-1:])
    n = len(win.statuses)
    win.apply_verification_turn(token)
    check("C5.stale_duplicate_turn_is_harmless", len(win.statuses) == n and ended(win))
    install_fakes(ns, verify_phase=u"committed-verified")
    win.apply_pose(item)
    m05.Timer.run_all()
    check("C5.verified_result_published", last_status(win) == (u"Pose applied: Arms Up (Left arm).", u"success")
          and ended(win), win.statuses[-1:])
    install_fakes(ns, phase=u"no-op")
    win.apply_pose(item)
    m05.Timer.run_all()
    check("C5.true_no_op_status_without_continuation",
          last_status(win) == (u"Already matches this pose.", u"neutral") and ended(win) and not Fakes.verifies,
          win.statuses[-1:])
    install_fakes(ns, phase=u"not-applied")
    win.apply_pose(item)
    check("C5.not_applied_status", last_status(win) == (ns["PROD_POSE_MESSAGES"][u"not-applied"], u"error")
          and ended(win))
    # Context gate: the destination instance changes before the turn.
    install_fakes(ns, verify_phase=u"committed-verified")
    win.apply_pose(item)
    win.scene_activity_suspended = True
    m05.Timer.run_all()
    win.scene_activity_suspended = False
    check("C5.modal_or_suspended_turn_unverified_without_scene_access", not Fakes.verifies and ended(win)
          and last_status(win)[1] == u"error")
    install_fakes(ns, verify_phase=u"committed-verified")
    m05.Timer.fail[0] = True
    try:
        win.apply_pose(item)
    finally:
        m05.Timer.fail[0] = False
    check("C5.schedule_failure_unverified_and_ended", not Fakes.verifies and ended(win)
          and last_status(win)[1] == u"error", win.statuses[-1:])
    install_fakes(ns, verify_phase=u"committed-verified")
    win.apply_pose(item)
    check("C5.close_before_turn_finalizes_once", win.apply_close_pending_verification() and ended(win))
    m05.Timer.run_all()
    check("C5.queued_turn_after_close_is_stale", not Fakes.verifies and ended(win))
    # Body continuation unchanged by the shared dispatch.
    win.apply_finish_verification({"kind": u"body", "label": u"Apply Body Preset", "pending": {}},
                                  {"phase": u"committed-verified"})
    check("C5.body_continuation_result_unchanged", last_status(win) == ("Body Preset applied.", u"success"))
    check("C5.apply_never_wrote_the_pose_file", core.read(item[u"path"]) == before)
    # The record changed on disk after it was listed.
    with open(item[u"path"], "ab") as f:
        f.write(b" ")
    install_fakes(ns)
    win.apply_pose(item)
    check("C5.changed_record_refused_before_apply", not Fakes.applies and ended(win)
          and last_status(win) == (ns["PROD_POSE_MESSAGES"][u"record-changed"], u"error"), win.statuses[-1:])
    with open(item[u"path"], "wb") as f:
        f.write(before)
    # Deleted destination instance after selection: refused before any apply.
    install_fakes(ns, verify_phase=u"committed-verified")
    win.apply_pose(item)
    w1.delete_instance(s, s.target)
    m05.Timer.run_all()
    check("C5.context_changed_before_turn_is_unverified", not Fakes.verifies and ended(win)
          and last_status(win)[1] == u"error", win.statuses[-1:])
    install_fakes(ns)
    win.apply_pose(item)
    check("C5.deleted_instance_refused_before_apply", not Fakes.applies and ended(win)
          and last_status(win)[1] == u"error", win.statuses[-1:])


def section_recovery(ns, Window, reg):
    s = w1.twin_scene()
    w1.fresh_library()
    win = window(ns, Window, s, s.target)
    item = saved_item(ns, win, reg)
    message = ns["PROD_POSE_MESSAGES"][u"recovery-unverified"] % {u"name": u"Arms Up"}
    install_fakes(ns, apply_raises=ns["ProdRecoveryUnverifiedError"](message))
    win.apply_pose(item)
    check("C6.recovery_unverified_sets_window_block", getattr(win, "pose_recovery_blocked", False) is True
          and ended(win) and last_status(win) == (message, u"error"), win.statuses[-1:])
    install_fakes(ns)
    win.apply_pose(item)
    win.save_pose(u"After", [u"left_arm"])
    blocked = ns["PROD_POSE_MESSAGES"][u"blocked-after-recovery"]
    check("C6.block_refuses_apply_and_save_before_scene_paths", not Fakes.applies and not Fakes.captures
          and win.statuses[-2:] == [(blocked, u"error"), (blocked, u"error")], win.statuses[-2:])
    check("C6.block_leaves_library_metadata_available", len(own_items(ns, win, reg)) == 1)


def section_independent_persistence(ns, Window, reg):
    """Owner clarification 1: save, close SFM, restart, independent destination session, apply without the
    source animation set. Offline proxy: session token change, a new scene with new instances only."""
    s = w1.twin_scene()
    w1.fresh_library()
    win = window(ns, Window, s, s.target)
    item = saved_item(ns, win, reg, regions=(u"left_arm", u"right_arm"))
    source_handle = s.target.animset._handle
    raw = core.read(item[u"path"])
    record = json.loads(raw.decode("utf-8"))
    check("C7.record_is_self_contained_no_scene_identity",
          sorted(record[u"pose"][u"source"]) == [u"model_ref", u"rig_class", u"shot_name", u"t_doc_ticks",
                                                 u"t_shot_ticks"]
          and b"animset_key" not in raw and b"gm_key" not in raw and b"document_key" not in raw)
    old_token = win.selection_token
    session = ns["PROD_INSTANCE_SESSION"]
    ns["PROD_INSTANCE_SESSION"] = u"restarted-session"
    try:
        s2 = w1.twin_scene(peer_name=u"dest_other", target_name=u"dest_character")
        check("C7.source_animation_set_absent_after_restart",
              source_handle not in [i.animset._handle for i in s2.instances if i.animset is not None])
        win2 = window(ns, Window, s2, s2.target)
        listed = own_items(ns, win2, reg)
        check("C7.pose_listed_from_disk_in_new_session", [i[u"preset_id"] for i in listed] == [item[u"preset_id"]])
        install_fakes(ns, verify_phase=u"committed-verified")
        win2.apply_pose(listed[0])
        m05.Timer.run_all()
        auth = Fakes.applies[0][1] if Fakes.applies else {}
        check("C7.apply_authorized_on_the_independent_destination",
              auth.get(u"context", {}).get("instance", {}).get("animset_key", [None, None])[1]
              == s2.target.animset._handle and auth[u"context"]["instance"]["session"] == u"restarted-session",
              auth.get(u"context"))
        check("C7.applied_and_verified_without_source", last_status(win2) == (
            u"Pose applied: Arms Up (Both arms).", u"success") and ended(win2), win2.statuses[-1:])
        refused("C7.earlier_session_selection_refused",
                outcome(lambda: ns["prod_context_token"](dict(win2.identity), old_token)))
        check("C7.record_unchanged_by_restart_apply", core.read(item[u"path"]) == raw)
    finally:
        ns["PROD_INSTANCE_SESSION"] = session


def section_foreign(ns, Window, reg):
    s = w1.twin_scene()
    w1.fresh_library()
    win = window(ns, Window, s, s.target)
    other_dir = os.path.join(w1.Library.root, u"Characters", u"zz_other_character")
    other = {u"character_key": u"zz_other_character", u"char_dir": other_dir, u"library_root": w1.Library.root,
             u"model_ref": w1.MODEL}
    foreign = ns["prod_pose_save_new"](other, u"Wave", pose_payload(ns, (u"left_arm",)), u"20261102-000000-000000",
                                       reg)
    install_fakes(ns)
    win.apply_pose(foreign)
    check("C8.foreign_pose_applies_through_its_own_reread", len(Fakes.applies) == 1
          and Fakes.applies[0][2][u"character_key"] == u"zz_other_character"
          and Fakes.applies[0][1][u"record"][u"revision"] == foreign[u"revision"])
    m05.Timer.run_all()
    with open(foreign[u"path"], "ab") as f:
        f.write(b"\n")
    install_fakes(ns)
    win.apply_pose(foreign)
    check("C8.changed_foreign_record_refused", not Fakes.applies and ended(win)
          and last_status(win)[1] == u"error", win.statuses[-1:])


def tree_digest(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = core.sha(core.read(p))
    return out


def main():
    if "--phase=run" not in sys.argv[1:]:
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        return 2
    print("F-01 stage C integration (Python %s)" % sys.version.split()[0])
    print("Candidate app sha256: %s" % route._sha(route.APP_PATH))
    real_before = tree_digest(REAL_LIBRARY) if os.path.isdir(REAL_LIBRARY) else None
    if not core.w2_verified():
        print("RESULT: W2 oracle files do not verify; stopping")
        return 1
    app = route.AppSource(route.APP_PATH)
    mainmenu = tempfile.mkdtemp(prefix="cpm_f01c_mainmenu_")
    try:
        try:
            ns, methods = build(app)
            Window = w1.make_window(ns, methods)
        except Exception:
            check("namespace.built", False, traceback.format_exc())
            return finish(real_before)
        ns["prod_cpm_mainmenu_dir"] = lambda: mainmenu
        section_static(app)
        for label, fn in (("seams", lambda: section_seams(ns, app, methods)),
                          ("registry", lambda: section_registry(ns, mainmenu))):
            run_section(label, fn)
        raw = fixture_registry(ns, mainmenu)
        ns["PROD_POSE_REGISTRY_SHA256"] = core.sha(raw)  # test pin for the fixture registry
        reg = ns["prod_pose_load_registry"]()
        for label, fn in (("authorization", lambda: section_authorization(ns, Window, reg)),
                          ("save", lambda: section_save(ns, app, Window, reg)),
                          ("apply", lambda: section_apply(ns, app, Window, reg)),
                          ("recovery", lambda: section_recovery(ns, Window, reg)),
                          ("independent_persistence", lambda: section_independent_persistence(ns, Window, reg)),
                          ("foreign", lambda: section_foreign(ns, Window, reg))):
            run_section(label, fn)
    finally:
        shutil.rmtree(mainmenu, True)
    return finish(real_before)


def run_section(label, fn):
    try:
        fn()
        check("section.%s.completed" % label, True)
    except Exception:
        check("section.%s.completed" % label, False, traceback.format_exc())


def finish(real_before):
    if w1.Library.root:
        shutil.rmtree(w1.Library.root, ignore_errors=True)
    real_after = tree_digest(REAL_LIBRARY) if os.path.isdir(REAL_LIBRARY) else None
    check("isolation.real_cpm_library_untouched", real_before == real_after)
    failed = [r for r in RESULTS if not r[1]]
    print("RESULT: %d/%d %s (%s)" % (len(RESULTS) - len(failed), len(RESULTS),
                                     "ALL PASS" if not failed else "SOME FAILED", sys.version.split()[0]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
