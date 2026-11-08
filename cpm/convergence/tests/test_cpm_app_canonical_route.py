# -*- coding: utf-8 -*-
"""CPM convergence Step 2b -- offline qualification of the canonical
authority route wired into the runnable CPM application source
(cpm/app/SFM_Character_Preset_Manager.py).

The application is an SFM MAINMENU script and cannot be imported offline.
As in Steps 1 and 2a, the functions under test are extracted verbatim from
the application source (located by name with ``ast``) and executed in a
namespace whose only stubs are SFM/Qt/DME boundaries and library I/O. The
authority path itself is real: the canonical package's broker, the CPM
adapter, and sidecars published by the real publisher.

Phases: --phase=publish (Python 3; publishes fixtures and runs the suite),
--phase=suite (Python 2.7.5, separate process), --phase=compare.

Offline only. Nothing here demonstrates real-SFM behavior.
"""
import ast
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, os.pardir, os.pardir, os.pardir))
# Test-only override so sensitivity runs can point at perturbed scratch copies.
MODULE_DIR = os.environ.get("CPM_TEST_MODULE_DIR") or os.path.join(_REPO_ROOT, "cpm", "convergence")
TOOLS_DIR = os.path.join(_REPO_ROOT, "tools")
PACKAGE_PARENT = os.path.join(_REPO_ROOT, "tests", "sidecar", "qualification", "candidate_b2c_correction6")
APP_PATH = os.environ.get("CPM_TEST_APP_PATH") or os.path.join(_REPO_ROOT, "cpm", "app", "SFM_Character_Preset_Manager.py")
BASELINE_PATH = os.path.join(_REPO_ROOT, "cpm", "baseline", "SFM_CSP_G18AN_SaveNewCopy.py")
BASELINE_SHA256 = "3326024ddecd544ad1e10659bbf7b98420b5f147fca775433878c19fd9e66b3e"

for _p in (TOOLS_DIR, PACKAGE_PARENT, MODULE_DIR, _THIS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cpm_compat_v1_projection as cpm  # noqa: E402
import cpm_authority_adapter as adapter_mod  # noqa: E402
import test_cpm_authority_adapter as base  # noqa: E402  (fixture Masters, expectations)

PY2 = sys.version_info[0] == 2
try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

FIXTURE_ROOT = os.path.join(tempfile.gettempdir(), "cpm_app_step2b_fixture")
G1_DIR = os.path.join(FIXTURE_ROOT, "g1")
G2_DIR = os.path.join(FIXTURE_ROOT, "g2")
LIVE_DIR = os.path.join(FIXTURE_ROOT, "live")
CORRUPT_DIR = os.path.join(FIXTURE_ROOT, "corrupt")
MASTER_NAME = base.MASTER_NAME
DIGEST_PY3 = os.path.join(FIXTURE_ROOT, "digest_py3.json")
DIGEST_PY27 = os.path.join(FIXTURE_ROOT, "digest_py27.json")

RESULTS = []


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


def _canon(obj):
    return json.loads(json.dumps(obj, sort_keys=True, default=repr))


def _run_source(source, label, globs, locs=None):
    """Module-level exec: Python 2 forbids a bare exec inside functions that
    also define closures."""
    code = compile(source, label, "exec")
    if locs is None:
        exec(code, globs)
    else:
        exec(code, globs, locs)


def raises(name, exc_types, fn):
    try:
        fn()
    except exc_types as exc:
        check(name, True, type(exc).__name__)
        return exc
    except Exception as exc:
        check(name, False, "raised %s: %s" % (type(exc).__name__, exc))
        return None
    check(name, False, "did not raise")
    return None


# ---------------------------------------------------------------------------
# Source extraction by name (ast; Python 2.7 has no end_lineno)
# ---------------------------------------------------------------------------

def _read_source(path):
    with open(path, "rb") as f:
        raw = f.read()
    return raw, raw.decode("utf-8").split(u"\n")


def _ranges(body, total_lines):
    """name -> (start, end) 1-based inclusive line ranges for a node list;
    each node ends where the next begins (trailing blanks trimmed)."""
    out = {}
    for i, node in enumerate(body):
        start = node.lineno
        if getattr(node, "decorator_list", None):
            start = min([d.lineno for d in node.decorator_list] + [start])
        end = (body[i + 1].lineno - 1) if i + 1 < len(body) else total_lines
        names = []
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        for n in names:
            out[n] = (start, end, node)
    return out


class AppSource(object):
    def __init__(self, path):
        self.raw, self.lines = _read_source(path)
        self.tree = ast.parse(self.raw)
        self.top = _ranges(self.tree.body, len(self.lines))

    def text(self, start, end):
        block = self.lines[start - 1:end]
        # Trailing blank and comment-only lines belong to whatever follows.
        while block and (not block[-1].strip() or block[-1].lstrip().startswith(u"#")):
            block.pop()
        return u"\n".join(block) + u"\n"

    def top_text(self, name):
        start, end, _ = self.top[name]
        return self.text(start, end)

    def methods(self, class_name):
        node = self.top[class_name][2]
        return _ranges(node.body, self.top[class_name][1])

    def method_text(self, class_name, method):
        start, end, _ = self.methods(class_name)[method]
        return textwrap.dedent(self.text(start, end))


# ---------------------------------------------------------------------------
# Section 1 -- bounded derivation from the frozen baseline
# ---------------------------------------------------------------------------

# Cumulative bounded edit set against the frozen baseline: Step 2b, then
# Step 3 (Operation Authority Context).
STEP2B_CHANGED_TOP = set([
    "prod_probe_semantic_provider", "prod_current_provider_descriptor",
    "prod_live_bindings_for_cached_scope", "prod_character_record", "prod_ensure_character",
    "prod_scope", "ProdWindow",
])
STEP3_CHANGED_TOP = set([
    "prod_scope_matches_identity", "prod_save", "prod_update_preset", "prod_apply",
    "prod_verify_apply_abort_baseline", "prod_abort_apply_and_verify", "prod_set_override",
    "prod_clear_override",
])
STEP4_CHANGED_TOP = set(["prod_body_source", "prod_body_source_live_from_baseline"])
R14_CHANGED_TOP = set(["prod_resource_snapshot"])  # diagnostic ctypes isolation
R15_CHANGED_TOP = set(["StartProdTool"])  # stable private-module startup (ProdWindow already listed)
# Handoff section 22 item 6 (ITEM6_HISTORICAL_AUTHORITY_CLEANUP_DESIGN.md): the
# historical getter becomes an unconditional refusal and the snapshot helper
# requires a supplied provider (ProdWindow already listed: parity method removed).
ITEM6_CHANGED_TOP = set(["get_semantic_provider", "semantic_snapshot_for_model_row"])
# Handoff section 22 item 7 (ITEM7_DIAGNOSTIC_LOGGING_REDUCTION_DESIGN.md section 7):
# timing/log removals and bounded diagnostic wrappers (StartProdTool already listed).
ITEM7_CHANGED_TOP = set([
    "p01_master_path", "prod_abort_fit_and_verify", "prod_bs_index_capture_map", "prod_bs_index_snapshot",
    "prod_build_bone_scale_plan", "prod_capture_body_snapshot", "prod_capture_bone_scale_map", "prod_discover",
    "prod_move_current_preset_to_trash", "prod_operation_event_turn_sample", "prod_prepare_library_root",
    "prod_q1_compare_body_capture", "prod_resolve", "prod_set_favorite", "prod_validate_bone_scale_map",
    "prod_verify_bone_scale_map", "same_time_refresh", "tool_apply_window_icon", "tool_window_icon",
    "undo_state",
])
# Pre-K UI polish pass (cpm/qualification/PRE_K_UI_POLISH_PASS.md): presentation only --
# the embedded window icon, a semantic action-button helper and its palette, and two
# copy-only ProdWindow methods (the other touched methods are already listed).
UIPASS_CHANGED_TOP = set(["PROD_WINDOW_ICON_NAME", "PROD_WINDOW_ICON_PNG_BASE64"])
UIPASS_NEW_TOP = set(["PROD_ACTION_BUTTON_PALETTES", "tool_apply_semantic_action_button"])
UIPASS_CHANGED_METHODS = set(["operation_default_error_copy", "review_changed"])
# Bounded diagnostic logging (cpm/qualification/CPM_BOUNDED_LOGGING_CORRECTION.md): the
# writer behind log_line, the retired reset, logging-only correlation/outcome helpers,
# two imports, and the retired fixed-file destinations. Every other touched function
# or method is already listed above (ProdWindow, StartProdTool, the abort verifiers).
LOGFIX_CHANGED_TOP = set(["log_line", "reset_log"])
LOGFIX_NEW_TOP = set([
    "PROD_LOG_DIR", "PROD_LOG_FORMAT", "PROD_LOG_HEADER_MARK", "PROD_LOG_FILE_LIMIT", "PROD_LOG_MAX_FILES",
    "PROD_LOG_TOTAL_LIMIT", "PROD_LOG_RECORD_LIMIT", "PROD_LOG_HEADER_LIMIT", "PROD_LOG_LOCK_NAME",
    "PROD_LOG_DROPPED_CAP", "PROD_LOG_NAME_RE", "PROD_LOG_CONSOLE_NOTICE", "PROD_LOG_STATE",
    "PROD_LOG_NON_MUTATING_LABELS", "PROD_LOG_CONTEXT", "ProdLogBusy", "prod_log_utc_stamp",
    "prod_log_bound_record", "prod_log_prefix", "prod_log_header", "prod_log_plain_file",
    "prod_log_owned_segments", "prod_log_open_segment", "prod_log_append", "prod_log_lock", "prod_log_unlock",
    "prod_log_drop", "prod_log_rearm", "prod_log_window_opened", "prod_log_window_closed",
    "prod_log_operation_begin", "prod_log_note_recovery", "prod_log_outcome", "prod_log_refused",
    "prod_log_operation_end",
])
LOGFIX_REMOVED_TOP = set(["OUTPUT_PATH", "PROD_OUTPUT_PATH"])
LOGFIX_ADDED_UNNAMED = [u"import binascii", u"import errno"]
# Logging-only helpers placed into extraction namespaces (log_line stays stubbed there).
LOGFIX_NAMESPACE_HELPERS = [
    "PROD_LOG_NON_MUTATING_LABELS", "PROD_LOG_CONTEXT", "prod_log_window_opened", "prod_log_window_closed",
    "prod_log_operation_begin", "prod_log_note_recovery", "prod_log_outcome", "prod_log_refused",
    "prod_log_operation_end",
]
# M-05 static mode-3 bone-scale correction (Astra production-correction design,
# 2026-10-24): one static definition and its readers, the deferred Apply
# verification helpers, and the ProdWindow continuation methods. prod_apply,
# guard, apply_kind and closeEvent are already listed above.
M05_CHANGED_TOP = set([
    "prod_bs_log_state", "prod_bs_snapshot", "prod_bs_static_one_key_zero", "prod_bs_authored_matches",
    "prod_bs_static_scale_trace", "prod_bs_index_binding", "prod_bs_capture_trace_diagnostic",
    "prod_bs_snapshot_matches_baseline",
])
M05_NEW_TOP = set([
    "PROD_BS_VARY_KEY_LIMIT", "PROD_BS_STATIC_PASS", "PROD_BS_STATIC_PLAY", "prod_bs_mode", "prod_bs_keyed_evidence",
    "prod_bs_static_play_evidence", "prod_bs_classify_static_scale", "prod_bs_static_pass_trace",
    "PROD_APPLY_CHECKING_COPY", "PROD_APPLY_UNVERIFIED_COPY", "prod_apply_deferred_unverified",
    "prod_bs_play_expectation", "prod_bs_play_expectations_hold", "prod_apply_deferred_verify",
    "prod_bs_channel_log_ids",
])
M05_NEW_METHODS = set([
    "operation_continuation_owned", "apply_begin_verification", "apply_verification_turn",
    "apply_finish_verification", "apply_close_pending_verification",
])
# M-06 imported static flex compatibility (Astra M-06 Production Correction Design): the static-play class in
# the flex snapshot/classification/write/restore/baseline helpers, the saved-value and planning helpers, and the
# new policy, discovery, admission and plan-verification names. prod_apply, prod_capture_body_snapshot,
# prod_verify_apply_abort_baseline and prod_apply_deferred_verify are already listed above.
M06_CHANGED_TOP = set([
    "side_snapshot", "binding_snapshot", "state_kind", "coherent", "matches_baseline", "write_side",
    "restore_side", "p02_saved_value_record", "p03_build_plan",
])
M06_NEW_TOP = set([
    "PROD_FLEX_STATIC_PLAY", "PROD_FLEX_BODY_POLICY", "PROD_FLEX_DISCOVERY_NODE_CAP",
    "PROD_FLEX_EVIDENCE_EXACT_FIELDS", "PROD_FLEX_WRITER_FIELDS", "prod_flex_static_play_policy",
    "prod_flex_body_policy_bindings", "prod_flex_element_key", "prod_flex_writer_index", "prod_flex_policy_writers",
    "flex_static_play_evidence", "flex_static_play_admitted", "flex_effective_value", "flex_effective_matches",
    "flex_structure_preserved", "flex_authored_change_ok", "p03_flex_expectations", "p03_verify_plan_results",
    # M-06 P1 evidence-integrity correction
    "PROD_FLEX_UNRESOLVED_RECORD_CAP", "PROD_FLEX_SELF_CONTAINED_OPERATORS", "PROD_FLEX_CONSTRAINT_OPERATORS",
    "PROD_FLEX_SLAVE_TARGET_TYPES", "prod_flex_strict_read", "prod_flex_strict_list", "prod_flex_strict_state",
    "prod_flex_controller_peers", "flex_static_play_writers_ok",
    # M-06 P1 correction 2 (strict native types/identity, key arrays, bookmarks)
    "prod_flex_strict_type", "prod_flex_identified_key", "prod_flex_strict_seconds", "prod_flex_strict_number",
    "prod_flex_strict_entries", "flex_key_arrays_match", "flex_bookmarks_ok",
    # M-06 verified-null IK primary correction (Body capture refusal diagnostic)
    "prod_flex_capture_refusal",
])
# M-06 W1 selected-instance resolution (Astra M-06/M-05 Integration Correction Design, 2026-10-29): the
# bone-scale resolver and its context-carrying callers, the operation context token, and context-free resolution
# that no longer retargets. prod_resolve, prod_scope, prod_probe_semantic_provider,
# prod_live_bindings_for_cached_scope, prod_save, prod_update_preset, prod_apply, the abort verifiers,
# prod_set_override, prod_clear_override, prod_body_source(_live_from_baseline), prod_bs_index_snapshot,
# prod_bs_index_capture_map, prod_capture_body_snapshot, prod_capture_bone_scale_map, prod_q1_compare_body_capture
# and prod_apply_deferred_verify are already listed above. prod_model_candidates is part of the separately
# recorded historical addition residual and is not re-listed here.
M06W1_CHANGED_TOP = set([
    "prod_bs_find_model_row", "prod_bs_current_bone_index", "prod_bs_resolve_binding",
    "prod_bs_resolve_clean_fixture", "prod_context_token", "prod_context_token_matches", "prod_resolve_from_rows",
])
M06W1_NEW_TOP = set([
    "PROD_INSTANCE_TOKEN_KIND", "PROD_INSTANCE_SESSION", "PROD_INSTANCE_RESELECT_COPY",
    "PROD_INSTANCE_CHANNEL_ATTRS", "prod_strict_identity", "prod_instance_document", "prod_instance_rows",
    "prod_bone_layout_sha256", "prod_instance_model", "prod_selection_token", "prod_instance_token",
    "prod_instance_kw", "prod_resolve_instance", "prod_selection_rows", "prod_instance_channels_clip",
    "prod_instance_pair_check",
    # W1 correction (Astra W1 review, CORRECTION REQUIRED): strict text and array readers used only by
    # prod_instance_channels_clip() to prove clip ownership; the permissive r26_* helpers are unchanged.
    "prod_instance_strict_text", "prod_instance_strict_members",
])
M06W1_CHANGED_METHODS = set(["current", "fit_candidate_rows"])
# W1 context helpers placed into extraction namespaces (context-free calls pass no instance keyword).
M06W1_NAMESPACE_HELPERS = ["PROD_INSTANCE_TOKEN_KIND", "prod_instance_token", "prod_instance_kw",
                           "prod_instance_pair_check"]
# F-01 Pose Library M1 stage A (F01 M1 Implementation Addendum R2, 09_FIRST_CODING_ASSIGNMENT.md): one appended,
# self-contained offline block; no existing definition is changed.
F01_STAGEA_NEW_TOP = set([
    "PROD_POSE_CONSTRAINT_TYPES", "PROD_POSE_CONVENTIONS", "PROD_POSE_FORMAT", "PROD_POSE_LABELS",
    "PROD_POSE_MAPPING_STATUSES", "PROD_POSE_MAX_BYTES", "PROD_POSE_MAX_LAYER_KEYS", "PROD_POSE_MAX_MAGNITUDE",
    "PROD_POSE_MESSAGES", "PROD_POSE_PART_NAMES", "PROD_POSE_QUAT_TOLERANCE", "PROD_POSE_REASONS",
    "PROD_POSE_REGIONS", "PROD_POSE_REGISTRY_FORMAT", "PROD_POSE_SNAPSHOT_FIELDS", "PROD_POSE_SOLVER_FIELDS",
    "PROD_POSE_VERSION", "ProdPoseError", "prod_pose_angle_deg", "prod_pose_browse_eligible",
    "prod_pose_canonical_bytes", "prod_pose_check", "prod_pose_check_frames", "prod_pose_check_postconditions",
    "prod_pose_check_typed_value", "prod_pose_compose", "prod_pose_cross_check", "prod_pose_distance",
    "prod_pose_f32", "prod_pose_finite_vector", "prod_pose_hemisphere", "prod_pose_int_types", "prod_pose_invert",
    "prod_pose_is_number", "prod_pose_key_plan", "prod_pose_layer_problems", "prod_pose_mb_angle_deg",
    "prod_pose_mb_apply", "prod_pose_mb_from_quaternion", "prod_pose_mb_mul", "prod_pose_mb_to_quaternion",
    "prod_pose_model_key", "prod_pose_noop_test", "prod_pose_parse", "prod_pose_parts_dialog_state",
    "prod_pose_parts_phrase", "prod_pose_payload_digest", "prod_pose_plan_matrix", "prod_pose_plan_quaternion",
    "prod_pose_plan_region", "prod_pose_qmul", "prod_pose_qrot", "prod_pose_quaternion_input",
    "prod_pose_record_schema", "prod_pose_region_schema", "prod_pose_registry_parse", "prod_pose_registry_schema",
    "prod_pose_registry_select", "prod_pose_reject_constant", "prod_pose_rig_class", "prod_pose_serialize",
    "prod_pose_shoulder_guard", "prod_pose_snapshot_evidence_problems", "prod_pose_strict_json",
    "prod_pose_text_types", "prod_pose_ticks", "prod_pose_time_decide", "prod_pose_ui_state",
    "prod_pose_unique_pairs", "prod_pose_unit", "prod_pose_validate"
])
# F-01 Pose Library M1 stage B (Addendum R2 section 4.3): one appended offline library block after stage A.
F01_STAGEB_NEW_TOP = set([
    "PROD_POSE_FOLDER", "PROD_POSE_FOREIGN_FAVORITES", "PROD_POSE_FOREIGN_FAVORITES_KIND",
    "PROD_POSE_INVALID_ATTRIBUTES", "PROD_POSE_LIBRARY_META", "PROD_POSE_NAME_MAX", "PROD_POSE_REPARSE_POINT",
    "PROD_POSE_UNSAFE_NAME_CHARS", "ProdPoseLibraryError", "prod_pose_assert_contained",
    "prod_pose_assert_unique_name", "prod_pose_attributes", "prod_pose_build_record", "prod_pose_check_name",
    "prod_pose_create_exclusive", "prod_pose_discover", "prod_pose_favorite_key", "prod_pose_inside",
    "prod_pose_is_favorite", "prod_pose_library_paths", "prod_pose_load_foreign_favorites", "prod_pose_load_meta",
    "prod_pose_name_key", "prod_pose_new_preset_id", "prod_pose_read_bytes", "prod_pose_read_file",
    "prod_pose_rename", "prod_pose_replace", "prod_pose_require", "prod_pose_safe_stem", "prod_pose_save_new",
    "prod_pose_set_favorite", "prod_pose_set_foreign_favorite", "prod_pose_stem_matches_id",
    "prod_pose_strict_json_file", "prod_pose_trash", "prod_pose_update", "prod_pose_verify_written"
])
# F-01 Pose Library M1 stage C (Addendum R2.1 sections 9.3 and 10): explicit pose refusals at the existing seams,
# prod_paths "pose", the compact tab padding, and one appended integration block; ProdWindow gains the Pose dispatch.
F01_STAGEC_CHANGED_TOP = set(["prod_apply", "prod_paths", "prod_preset_dir", "tool_apply_tab_style"])
F01_STAGEC_NEW_TOP = set([
    "PROD_POSE_AUTH_SCHEMA", "PROD_POSE_CHECKING_COPY", "PROD_POSE_KIND", "PROD_POSE_REGISTRY_FILENAME",
    "PROD_POSE_REGISTRY_MODE", "PROD_POSE_REGISTRY_SHA256", "PROD_POSE_SCENE_LABELS", "ProdPoseIntegrationError",
    "PROD_POSE_EDITOR_NOTE_COPY",  # F-01 UI consistency pass: the Poses page's one line above the list
    "PROD_POSE_REGISTRY_UNAVAILABLE_COPY",  # F-01 UI completion: the list message for missing/damaged profiles
    "PROD_POSE_RECOVERY_BLOCK",  # F-01 S1 recovery: the process-wide pause (survives CPM window recreation)
    "prod_pose_authorize", "prod_pose_context_gate", "prod_pose_deferred_verify", "prod_pose_load_registry",
    "prod_pose_registry_path", "prod_pose_reread", "prod_pose_selected_library",
])
F01_STAGEC_CHANGED_METHODS = set(["selected_or_none", "operation_default_error_copy"])
F01_STAGEC_NEW_METHODS = set(["apply_pose", "pose_begin_verification", "pose_finish_verification", "pose_guard",
                              "pose_registry_mode", "save_pose"])
# F-01 Pose Library M1 stage D (Addendum R2.1 sections 5.4-8; left arm): one appended live block after stage C;
# ProdWindow gains the Poses page (constructor, tab_changed) and its list methods.
F01_STAGED_NEW_TOP = set([
    "prod_pose_require_motion_editor",  # S3 run 3 B10: Apply checks the timeline editor before evaluation
    "PROD_POSE_BONE_NAME_RE", "PROD_POSE_INSERT_ALLOWED_METADATA", "PROD_POSE_LIVE_EVALUATED_OUTPUTS",
    "PROD_POSE_LIVE_KNOWN_OPERATORS", "PROD_POSE_LIVE_MAX_ARRAY", "PROD_POSE_LIVE_MAX_NODES",
    "PROD_POSE_LIVE_MAX_TOTAL_KEYS", "PROD_POSE_LIVE_REGIONS", "PROD_POSE_LIVE_SLAVE_ATTRS", "PROD_POSE_QUAL_FAULT",
    "PROD_POSE_UNDO_REQUIRED", "ProdPoseUnreadable", "prod_pose_apply", "prod_pose_arm_chain",
    "prod_pose_arm_constraints", "prod_pose_attr", "prod_pose_attribute_names", "prod_pose_binding_identity",
    "prod_pose_bindings", "prod_pose_capture", "prod_pose_capture_authored", "prod_pose_capture_observed",
    "prod_pose_capture_skeleton", "prod_pose_channel_authored", "prod_pose_channel_binding",
    "prod_pose_check_writers", "prod_pose_classify", "prod_pose_compare_descriptor", "prod_pose_components",
    "prod_pose_current_time", "prod_pose_descendants", "prod_pose_descriptor", "prod_pose_differences",
    "prod_pose_effective_inputs", "prod_pose_expected_authored", "prod_pose_field", "prod_pose_film_clips",
    "prod_pose_h", "prod_pose_has", "prod_pose_ident", "prod_pose_key_entries", "prod_pose_key_value",
    "prod_pose_layer_snapshot", "prod_pose_live_arm", "prod_pose_log", "prod_pose_native_name",
    "prod_pose_native_value", "prod_pose_num", "prod_pose_operator_relationships", "prod_pose_opt_attr",
    "prod_pose_oracle", "prod_pose_parent_role", "prod_pose_pending", "prod_pose_plain", "prod_pose_plan_values",
    "prod_pose_portable_value", "prod_pose_preflight", "prod_pose_qualification_fault", "prod_pose_quat",
    "prod_pose_region_payload", "prod_pose_region_profile", "prod_pose_region_state", "prod_pose_require_readable",
    "prod_pose_required", "prod_pose_roundtrip", "prod_pose_same_state", "prod_pose_scale_ok", "prod_pose_seq",
    "prod_pose_slave_target", "prod_pose_structural_checks", "prod_pose_text", "prod_pose_ticks_of",
    "prod_pose_time", "prod_pose_time_read", "prod_pose_transform_state", "prod_pose_type",
    "prod_pose_undo_problems", "prod_pose_undo_state", "prod_pose_unique", "prod_pose_vec3",
    "prod_pose_verify_applied", "prod_pose_walk", "prod_pose_world", "prod_pose_write", "prod_pose_writer_index",
    # Motion Editor apply gate and post-commit same-time refresh (FA-3b)
    "PROD_POSE_APPLY_TIMELINE_MODE", "PROD_POSE_EDITOR_MODE_COPY", "PROD_POSE_EDITOR_CLOCK_COPY", "prod_pose_timeline_mode",
    "prod_pose_apply_gate", "prod_pose_request_refresh",
    # Argon B.2: Save New / Update Pose refuse capture when a region channel's clock is not the mapped tick.
    "PROD_POSE_SAVE_CLOCK_COPY", "PROD_POSE_UPDATE_CLOCK_COPY", "prod_pose_capture_clock_check",
])
F01_STAGED_CHANGED_METHODS = set(["__init__", "tab_changed", "render", "clear_model_selection", "operation_end"])  # NQ-1: Poses refresh
F01_STAGED_NEW_METHODS = set(["refresh_pose_view", "selected_pose", "refresh_pose_buttons", "apply_selected_pose"])
# F-01 full body, stage E (F01_FULL_BODY_CONSOLIDATED_DESIGN.md Rev 2; S1 authorization 2026-11-06): one appended
# block after stage D (complete-pose core, planner and live layer); stage A and C gain small version 2 hooks.
F01_STAGEE_NEW_TOP = set([
    "PROD_BODY_BONE_CLASSES", "PROD_BODY_CHANNEL_ROLES", "PROD_BODY_CONTROL_CHANNELS", "PROD_BODY_DESCRIBED_ROLES",
    "PROD_BODY_FK_POSITION_COPY", "PROD_BODY_FK_POSITION_TOLERANCE", "PROD_BODY_FRAME", "PROD_BODY_HANDLE_CLASSES",
    "PROD_BODY_MAX_CHANNELS", "PROD_BODY_MAX_RECORD_BYTES", "PROD_BODY_MESSAGES", "PROD_BODY_POSE_VERSION",
    "PROD_BODY_PRESERVED_OPERATORS", "PROD_BODY_REGION", "PROD_BODY_REGISTRY_FILENAME", "PROD_BODY_REGISTRY_FORMAT",
    "PROD_BODY_REGISTRY_SHA256", "PROD_BODY_SLAVE_SLOTS", "PROD_BODY_SOURCE_ATTRIBUTES",
    "PROD_BODY_TRANSFORM_TYPES", "PROD_BODY_WRITTEN_ROLES", "prod_body_apply", "prod_body_authority_evidence",
    "prod_body_bindings", "prod_body_bone_order", "prod_body_bone_scale", "prod_body_capture",
    "prod_body_channel_value", "prod_body_check_authority", "prod_body_check_fk_positions", "prod_body_classify",
    "prod_body_compare_descriptor", "prod_body_current_time", "prod_body_descriptor", "prod_body_discover",
    "prod_body_effective_inputs", "prod_body_error", "prod_body_exact", "prod_body_expected_authored",
    "prod_body_expected_skeleton", "prod_body_f32_list", "prod_body_field_value", "prod_body_fk_distance",
    "prod_body_fk_limit", "prod_body_identity", "prod_body_is_record", "prod_body_label_ok", "prod_body_live",
    "prod_body_load_registry", "prod_body_noop", "prod_body_owner_row", "prod_body_payload", "prod_body_pending",
    "prod_body_plan", "prod_body_planned_values", "prod_body_preflight", "prod_body_profile",
    "prod_body_record_schema", "prod_body_region_schema", "prod_body_registry_parse", "prod_body_registry_schema",
    "prod_body_resolve_profile", "prod_body_root_world", "prod_body_same_state", "prod_body_scaled_compose",
    "prod_body_state", "prod_body_typed", "prod_body_usable", "prod_body_validate", "prod_body_verify_applied",
    "prod_body_verify_skeleton", "prod_body_wrap",
])
# F-01 UI consistency pass: the application name (TOOL_NAME; the diagnostic log keeps its product literal), Help's
# preferred height, and the Poses page's state, list-message row and read-only Pose Info.
F01_UI_CHANGED_TOP = set(["TOOL_NAME", "StartCharacterSliderPresetTool",
                          # Final UI polish: one enabled/disabled button text colour everywhere.
                          "tool_apply_visual_theme", "tool_apply_main_action_button"])
F01_UI_NEW_TOP = set(["tool_help_preferred_height", "prod_rename_preset",
                      # Final UI polish: neutral button style, short status names, the installed updater's location.
                      "tool_apply_neutral_button_style", "tool_status_name", "prod_master_updater_paths",
                      # Version footer: the installed release record for this exact CPM build.
                      "prod_release_version"])
F01_UI_NEW_METHODS = set(["pose_ui_state", "set_pose_list_message", "open_pose_info",
                          # The Poses six-button layout: Update Pose, Add/Remove Favorite and Delete Pose handlers.
                          "pose_selection_for_action", "update_selected_pose", "confirm_pose_update", "update_pose",
                          "toggle_pose_favorite", "confirm_pose_trash", "delete_selected_pose",
                          # Rename (list context menu) on Body Presets, Expressions and Poses.
                          "show_rename_menu", "prompt_rename", "rename_kind", "rename_selected_pose",
                          # Final UI polish: Update Animation Groups Master opens the installed updater.
                          "open_master_updater"])
# F-01 SFP-1 scoped poses (F01_SCOPED_POSE_BLUEPRINT_R3_20261108.md; Owner authorization of stages A/B 2026-11-08): one
# appended block after stage E (version 3 records, direct_fk_v1 discovery, the scope compiler and its live layer);
# stages A-C gain small version 3 dispatch hooks; ProdWindow gains the Save dialog.
F01_SFP1_NEW_TOP = set([
    "PROD_SCOPE_AUTH_SCHEMA", "PROD_SCOPE_CARRIED_ENABLED", "PROD_SCOPE_CARRIED_REVISION", "PROD_SCOPE_CARRIED_RULE",
    "PROD_SCOPE_COMPLETENESS", "PROD_SCOPE_CONSTRAINTS", "PROD_SCOPE_CONTROL_CHANNELS",
    "PROD_SCOPE_EXTRAPOLATION_QUALIFIED", "PROD_SCOPE_FK_POSITION_LIMIT", "PROD_SCOPE_KINDS",
    "PROD_SCOPE_LEDGER_ROLES", "PROD_SCOPE_MAX_BONES", "PROD_SCOPE_MAX_GROUPS", "PROD_SCOPE_MAX_RECORD_BYTES",
    "PROD_SCOPE_MESSAGES", "PROD_SCOPE_MODEL_FRAME", "PROD_SCOPE_PART_KEYS", "PROD_SCOPE_POSE_VERSION",
    "PROD_SCOPE_PROVENANCE", "PROD_SCOPE_REVIEW_SCOPE_COPY", "PROD_SCOPE_RULE", "PROD_SCOPE_RULES",
    "PROD_SCOPE_SCALE_OPERATORS", "PROD_SCOPE_SLAVE_SLOTS", "PROD_SCOPE_SOURCE_ATTRIBUTES", "PROD_SCOPE_TOLERANCES",
    "PROD_SCOPE_TRANSFORM_TYPES", "prod_scope_ancestors", "prod_scope_apply", "prod_scope_authorize",
    "prod_scope_availability", "prod_scope_bindings", "prod_scope_bone_order", "prod_scope_capture",
    "prod_scope_carried_admission", "prod_scope_carried_inputs", "prod_scope_channel_value",
    "prod_scope_check_against_source", "prod_scope_check_authority", "prod_scope_check_composition",
    "prod_scope_check_oracle", "prod_scope_children", "prod_scope_classify", "prod_scope_compatible",
    "prod_scope_compile", "prod_scope_compose", "prod_scope_cumulative", "prod_scope_current_time",
    "prod_scope_descendants", "prod_scope_dialog_state", "prod_scope_discover", "prod_scope_effective_inputs",
    "prod_scope_error", "prod_scope_exact", "prod_scope_exclusion_boundary", "prod_scope_expected", "prod_scope_f32",
    "prod_scope_field_value", "prod_scope_followers", "prod_scope_group_view", "prod_scope_groups",
    "prod_scope_highlighted", "prod_scope_identity", "prod_scope_info", "prod_scope_inventory",
    "prod_scope_is_record", "prod_scope_label", "prod_scope_layout_signature", "prod_scope_list_phrase",
    "prod_scope_live", "prod_scope_model_scale", "prod_scope_noop",
    "prod_scope_oracle", "prod_scope_order", "prod_scope_parts", "prod_scope_payload", "prod_scope_pending",
    "prod_scope_plan", "prod_scope_planned_values", "prod_scope_preflight", "prod_scope_procedural_guard",
    "prod_scope_reason_text", "prod_scope_record_request", "prod_scope_record_schema",
    "prod_scope_relative", "prod_scope_request", "prod_scope_row", "prod_scope_rule_usable", "prod_scope_same_state",
    "prod_scope_state", "prod_scope_structure", "prod_scope_summary", "prod_scope_time_names",
    "prod_scope_typed_scale", "prod_scope_validate", "prod_scope_verify", "prod_scope_verify_applied",
    "prod_scope_world", "prod_scope_wrap",
    # SFP-1 A/B corrections (Astra implementation review of abe58bb, Owner-approved): the endpoint-index contract.
    "prod_scope_index_supported", "prod_scope_indices_supported",
    # SFP-1 final dependency corrections (Owner authorization after the 1bf1ab3 re-review).
    "prod_scope_dependency_index", "prod_scope_dependencies"
])
F01_SFP1_NEW_METHODS = set(["prompt_pose_scope"])
EXPECTED_CHANGED_TOP = (STEP2B_CHANGED_TOP | STEP3_CHANGED_TOP | STEP4_CHANGED_TOP | R14_CHANGED_TOP
                        | R15_CHANGED_TOP | ITEM6_CHANGED_TOP | ITEM7_CHANGED_TOP | UIPASS_CHANGED_TOP
                        | LOGFIX_CHANGED_TOP | M05_CHANGED_TOP | M06_CHANGED_TOP | M06W1_CHANGED_TOP
                        | F01_STAGEC_CHANGED_TOP | F01_UI_CHANGED_TOP)
EXPECTED_NEW_TOP = set([
    "PROD_CPM_MAINMENU_RELATIVE_PARTS", "PROD_CPM_ADAPTER_MODULES", "ProdCpmAuthorityBootstrapError",
    "ProdCpmAuthorityNotMigrated", "prod_cpm_mainmenu_dir", "prod_cpm_import_adapter", "prod_cpm_is_main_thread",
    "prod_cpm_open_adapter", "prod_cpm_scope_generation_stale", "prod_cpm_unmigrated_authority",
    "ProdCpmUnmigratedProvider", "prod_cpm_health",
    # Step 3
    "PROD_CPM_OPERATION_CONTEXT_SCHEMA", "PROD_CPM_STALE_SCOPE_MESSAGE", "ProdCpmOperationAuthorityError",
    "prod_cpm_pure_scalar_types", "PROD_CPM_PURE_SCALARS", "prod_cpm_detached",
    "prod_cpm_context_matches_identity", "prod_cpm_reclassify_outcome", "prod_cpm_authorize_operation",
    # Step 4
    "ProdCpmFitStop", "prod_cpm_fit_stage_vocabulary", "prod_cpm_open_fit_stage", "prod_cpm_release_fit_stage",
    # R14
    "_PROD_PRIVATE_WINDLL", "prod_private_windll",
])
# R15 startup/lifecycle additions: bounded here, exercised by the R15 suite
# (not extracted into this suite's namespace).
R15_NEW_TOP = set([
    "PROD_R15_STARTUP_IDLE", "PROD_R15_STARTUP_STARTING", "PROD_R15_STARTUP_FAILED", "PROD_R15_STARTUP",
    "PROD_R15_NOTICE_COPY", "prod_r15_qt_alive", "prod_r15_result", "prod_r15_launcher_refusal",
    "prod_r15_window_decision", "prod_r15_close_partial_window",
])
EXPECTED_CHANGED_METHODS = set(["guard", "render", "semantic_provider_ready",
                                "review_decision", "review_reclassify",  # Step 3
                                "fit_selected", "fit_stage"])  # Step 4
EXPECTED_NEW_METHODS = set(["prod_cpm_request_stale_rebuild_if_needed", "prod_cpm_run_stale_rebuild"])
# R15: Escape/reject teardown repair (pre-existing defect, discovered during R15).
R15_CHANGED_METHODS = set(["closeEvent"])
R15_NEW_METHODS = set(["reject"])
# Item 6: exact removals and the one addition (design sections 5 and 7).
ITEM6_NEW_TOP = set(["ProdHistoricalAuthorityDisabled"])
ITEM6_REMOVED_TOP = set([
    "p01_ascii_fold", "p01_tokenize_master", "p01_parse_occurrences", "SemanticProvider",
    "MasterTxtSemanticProvider", "g18p_sha256_file", "g18p_sidecar_deploy_dir", "g18p_find_sidecar_artifact",
    "g18p_sidecar_dependency_discovery", "g18an_find_file_by_sha", "g18an_verified_sidecar_paths",
    "g18an_import_frozen_sidecar_provider", "g18an_normalize_sidecar_path", "SidecarSemanticProvider",
    "g18an_ascii_case_variant", "g18an_semantic_parity_for_row", "g18an_scope_decision_view",
    "g18an_scope_signature", "g18an_accepted_from_scope", "g18an_flex_plan_signature", "g18an_preset_decisions",
    "g18an_clothing_plan_signature", "g18an_clothing_decisions", "g18an_decision_parity_for_row",
    "acquire_semantic_provider_for_mode", "invalidate_semantic_provider", "p01_provider_answer_signature",
    "p01_synthetic_provider_contract", "semantic_snapshots_for_current_shot",
    "prod_semantic_provider_health_from_descriptor", "prod_provider_health_selftest",
    # constants / class aliases
    "SEMANTIC_PROVIDER_MODE_TXT", "SEMANTIC_PROVIDER_MODE_AUTO", "G18P_MASTER_SHA256",
    "G18P_SIDECAR_ARTIFACT_SHA256", "G18P_SIDECAR_FORMAT_SHA256", "G18P_R1D_VALIDATOR_SHA256",
    "G18P_R1D_PROVIDER_SHA256", "PROD_MASTER_HEALTH_MIN_OCCURRENCES", "PROD_MASTER_HEALTH_MIN_FOLD_FAMILIES",
    "P01SemanticProvider", "P01MasterTxtProvider",
])
ITEM6_REMOVED_METHODS = set(["g18an_run_decision_parity"])
# Item 7: exact top-level removals and changed ProdWindow methods (design section 7).
ITEM7_REMOVED_TOP = set([
    "prod_perf_seconds", "prod_perf_log", "astra_perf_timing", "prod_action_timing", "PROD_PERF_LOGGING",
    "SEMANTIC_PROVIDER_MODE_SIDECAR", "SEMANTIC_PROVIDER_FORCE_MODE", "G18AN_PARITY_SHORTCUT",
])
ITEM7_CHANGED_METHODS = set([
    "apply_kind", "apply_provider_unavailable_to_ui", "clear_model_selection", "delete_kind", "fit_finish",
    "fit_show_partial_failure", "open_details", "open_help", "open_master_page", "open_preset_info",
    "operation_begin", "operation_end", "operation_mark_phase", "poll_foreign_modal", "populate",
    "refresh_animset_display_metadata", "refresh_fit_candidates", "refresh_preset_view", "reload_library_cache",
    "resume_scene_activity_after_foreign_modal", "save_kind", "select_model", "toggle_favorite", "update_kind",
])
# Item 7 removes exactly one unnamed top-level statement: the timing-only import.
ITEM7_REMOVED_UNNAMED = u"import time"


def _unnamed_top_level(source):
    """Source text of every top-level statement that binds no name (docstring,
    imports, guards, bare calls); imports are listed by what they import."""
    out = []
    for node in source.tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets):
            continue
        out.append(source.lines[node.lineno - 1].strip())
    return out


def section_derivation(app):
    raw, _ = _read_source(BASELINE_PATH)
    check("derivation.baseline_sha_pinned", hashlib.sha256(raw).hexdigest() == BASELINE_SHA256)
    baseline = AppSource(BASELINE_PATH)
    changed = set(n for n in app.top if n in baseline.top and app.top_text(n) != baseline.top_text(n))
    added = set(app.top) - set(baseline.top)
    removed = set(baseline.top) - set(app.top)
    check("derivation.changed_top_level_is_bounded", changed == EXPECTED_CHANGED_TOP, sorted(changed))
    check("derivation.added_top_level_is_bounded",
          added == EXPECTED_NEW_TOP | R15_NEW_TOP | ITEM6_NEW_TOP | UIPASS_NEW_TOP | LOGFIX_NEW_TOP | M05_NEW_TOP
          | M06_NEW_TOP | M06W1_NEW_TOP | F01_STAGEA_NEW_TOP | F01_STAGEB_NEW_TOP | F01_STAGEC_NEW_TOP | F01_STAGED_NEW_TOP
          | F01_UI_NEW_TOP | F01_STAGEE_NEW_TOP | F01_SFP1_NEW_TOP,
          sorted(added))
    check("derivation.removed_is_exactly_item6_and_item7", removed == ITEM6_REMOVED_TOP | ITEM7_REMOVED_TOP
          | LOGFIX_REMOVED_TOP, sorted(removed ^ (ITEM6_REMOVED_TOP | ITEM7_REMOVED_TOP | LOGFIX_REMOVED_TOP)))
    bm, am = baseline.methods("ProdWindow"), app.methods("ProdWindow")
    m_changed = set(n for n in am if n in bm and app.method_text("ProdWindow", n) != baseline.method_text("ProdWindow", n))
    # The shortcut binding lives in the constructor-side builder method.
    shortcut_owner = [n for n in bm if "g18an_parity_shortcut = QtGui.QShortcut" in baseline.method_text("ProdWindow", n)]
    check("derivation.shortcut_owner_found", len(shortcut_owner) == 1, shortcut_owner)
    expected_methods = (EXPECTED_CHANGED_METHODS | R15_CHANGED_METHODS | set(shortcut_owner) | ITEM7_CHANGED_METHODS
                        | UIPASS_CHANGED_METHODS | M06W1_CHANGED_METHODS | F01_STAGEC_CHANGED_METHODS
                        | F01_STAGED_CHANGED_METHODS)
    check("derivation.changed_methods_are_bounded", m_changed == expected_methods, sorted(m_changed))
    check("derivation.added_methods_are_bounded",
          set(am) - set(bm) == EXPECTED_NEW_METHODS | R15_NEW_METHODS | M05_NEW_METHODS | F01_STAGEC_NEW_METHODS
          | F01_STAGED_NEW_METHODS | F01_UI_NEW_METHODS | F01_SFP1_NEW_METHODS,
          sorted(set(am) - set(bm)))
    check("derivation.removed_methods_are_exactly_item6", set(bm) - set(am) == ITEM6_REMOVED_METHODS,
          sorted(set(bm) - set(am)))
    # R15: the only unnamed top-level changes are the allow-guard (added right
    # after the docstring) and the removed bottom-of-file StartProdTool() call;
    # item 7 additionally removes exactly one `import time`.
    b_un, a_un = _unnamed_top_level(baseline), _unnamed_top_level(app)
    logfix_imports_once = all(a_un.count(i) == 1 for i in LOGFIX_ADDED_UNNAMED)
    a_un = [line for line in a_un if line not in LOGFIX_ADDED_UNNAMED]
    b_mid = list(b_un[1:-1])
    item7_import_once = b_mid.count(ITEM7_REMOVED_UNNAMED) == 1
    if item7_import_once:
        b_mid.remove(ITEM7_REMOVED_UNNAMED)
    check("derivation.r15_unnamed_top_level_bounded",
          b_un[-1] == u"StartProdTool()" and a_un[:1] == b_un[:1] and a_un[1] == u"if not ("
          and item7_import_once and ITEM7_REMOVED_UNNAMED not in a_un
          and a_un[2:] == b_mid and logfix_imports_once,
          [a_un[1], b_un[-1], len(a_un), len(b_un), item7_import_once, logfix_imports_once])
    check("derivation.item6_historical_machinery_absent", not ITEM6_REMOVED_TOP & set(app.top)
          and "get_semantic_provider" in app.top and "ProdHistoricalAuthorityDisabled" in app.top,
          sorted(ITEM6_REMOVED_TOP & set(app.top)))
    check("derivation.item6_parity_handler_absent", not ITEM6_REMOVED_METHODS & set(am))
    return baseline


# ---------------------------------------------------------------------------
# Section 2 -- static reachability from the production entry points
# ---------------------------------------------------------------------------

FORBIDDEN = set([
    "get_semantic_provider", "acquire_semantic_provider_for_mode", "SidecarSemanticProvider",
    "MasterTxtSemanticProvider", "invalidate_semantic_provider", "g18an_decision_parity_for_row",
    "g18an_semantic_parity_for_row", "g18an_verified_sidecar_paths", "g18an_import_frozen_sidecar_provider",
    "p02_complete_scope", "g11a_source", "prod_semantic_provider_health_from_descriptor",
    "prod_provider_health_selftest", "RunG09AGenericWindowRoute",
])
# Item 6: no exemption. semantic_snapshot_for_model_row no longer reaches the
# historical getter (its provider=None branch refuses), and prod_scope always
# supplies a provider (checked statically and at runtime below).
EXEMPT_EDGES = set()


def _names_in(node):
    names = set()
    attrs = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.Attribute):
            attrs.add(sub.attr)
    return names, attrs


def section_reachability(app):
    top_nodes = dict((n, v[2]) for n, v in app.top.items())
    methods = app.methods("ProdWindow")
    method_attrs_used = set()
    for name, (_, _, node) in methods.items():
        method_attrs_used |= _names_in(node)[1]
    check("reach.parity_handler_unreferenced",
          "g18an_run_decision_parity" not in method_attrs_used
          and "g18an_run_decision_parity" not in _names_in(app.tree)[0], None)
    roots = set(["StartProdTool"])
    root_method_nodes = [node for name, (_, _, node) in methods.items() if name != "g18an_run_decision_parity"]
    frontier = set()
    for node in root_method_nodes:
        frontier |= _names_in(node)[0]
    frontier |= _names_in(top_nodes["StartProdTool"])[0]
    reached = set()
    edges_to_forbidden = set()
    stack = [(None, n) for n in frontier]
    while stack:
        parent, name = stack.pop()
        if name in FORBIDDEN:
            edges_to_forbidden.add((parent, name))
            continue
        if name in reached or name not in top_nodes or name == "ProdWindow":
            continue
        reached.add(name)
        for child in _names_in(top_nodes[name])[0]:
            stack.append((name, child))
    check("reach.no_forbidden_reachable_except_exempt_edge", edges_to_forbidden <= EXEMPT_EDGES,
          sorted("%s->%s" % e for e in edges_to_forbidden - EXEMPT_EDGES))
    check("reach.canonical_route_reachable", set(["prod_cpm_open_adapter", "prod_probe_semantic_provider",
                                                  "prod_scope", "prod_current_provider_descriptor"]) <= reached)
    scope_src = app.top_text("prod_scope")
    check("reach.prod_scope_never_passes_none", u"provider = prod_cpm_open_adapter()" in scope_src
          and u"get_semantic_provider" not in scope_src)
    check("reach.no_parity_shortcut_binding", u"QShortcut(" not in u"".join(
        app.method_text("ProdWindow", n) for n in methods if "parity" in app.method_text("ProdWindow", n)))
    check("reach.render_releases_probe_adapter",
          u"provider = None" in [line.strip() for line in app.method_text("ProdWindow", "render").split(u"\n")])
    guard = methods["guard"][2]
    handlers = [h for t in ast.walk(guard) if isinstance(t, ast.Try if hasattr(ast, "Try") else ast.TryExcept)
                for h in t.handlers]
    hooked = [h for h in handlers if "prod_cpm_request_stale_rebuild_if_needed" in _names_in(h)[1]]
    check("reach.guard_error_path_hooks_stale_rebuild", len(hooked) == 1)
    for name in sorted(EXPECTED_NEW_METHODS):
        names, attrs = _names_in(methods[name][2])
        check("reach.%s_never_replays" % name, "fn" not in names and "guard" not in attrs and "work" not in names)


# ---------------------------------------------------------------------------
# Namespace construction for extracted production code
# ---------------------------------------------------------------------------

EXTRACT_TOP = [
    "u", "typ", "SEMANTIC_PROVIDER_CONTRACT", "SEMANTIC_STATUS_RESOLVED", "SEMANTIC_STATUS_CONFLICT",
    "SEMANTIC_STATUS_ABSENT", "SEMANTIC_STATUS_UNAVAILABLE", "SEMANTIC_MATCH_EXACT", "SEMANTIC_MATCH_FOLDED",
    "SEMANTIC_MATCH_NONE", "SEMANTIC_PROVIDER_KIND_MASTER_TXT", "SEMANTIC_PROVIDER_FOLD_POLICY",
    "SEMANTIC_PROVIDER_KIND_MASTER_SIDECAR", "SEMANTIC_PROVIDER_MASTER_FILENAME",
    "P01_PROVIDER_CONTRACT", "P01_FOLD_POLICY", "P01_STATUS_RESOLVED", "P01_STATUS_CONFLICT",
    "P01_STATUS_ABSENT", "P01_STATUS_UNAVAILABLE", "P01_MATCH_EXACT", "P01_MATCH_FOLDED", "P01_MATCH_NONE",
    "SEMANTIC_BODY_MORPHS_PATH", "PROD_SEMANTIC_POLICY",
    "p01_is_face_path", "semantic_is_body_morph_path", "semantic_snapshot_from_live_vocabulary",
    "semantic_snapshot_signature", "semantic_snapshot_for_model_row", "prod_pure_semantic_row",
    "prod_provider_capture", "prod_json_digest", "prod_binding_descriptor", "prod_live_binding_signatures",
    "prod_override_revision", "prod_scope_pure_assert", "prod_scope_matches_identity",
    "prod_live_bindings_for_cached_scope", "prod_current_provider_descriptor", "prod_character_record",
    "prod_ensure_character", "prod_scope", "p03_unmapped_relevant_controls",
] + [n for n in sorted(EXPECTED_NEW_TOP) if n != "PROD_CPM_PURE_SCALARS"] + [
    "PROD_CPM_PURE_SCALARS", "prod_probe_semantic_provider"]


class _Forbidden(Exception):
    pass


class _Recorder(object):
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append(args)


class _QtStub(object):
    class QObject(object):
        pass

    class QCoreApplication(object):
        @staticmethod
        def instance():
            return None

    class QThread(object):
        @staticmethod
        def currentThread():
            return None

    class QTimer(object):
        scheduled = []

        @classmethod
        def singleShot(cls, delay, callback):
            cls.scheduled.append((delay, callback))


class Env(object):
    """Mutable fixture state the stubs read from."""
    live_root = LIVE_DIR
    bindings = []
    profile = None
    forbidden_calls = []
    writes = []
    import_failure = None
    broker_wrapper = []  # [callable]; a list so Python 2 does not bind it as a method


def _shim_adapter_module():
    """What prod_cpm_import_adapter returns offline: the real adapter module,
    opened against the checked-in canonical package and the fixture's
    published root instead of an SFM installation."""
    class Shim(object):
        CpmAuthorityUnavailable = adapter_mod.CpmAuthorityUnavailable
        CpmGenerationMismatch = adapter_mod.CpmGenerationMismatch
        EXPECTED_API_VERSION = adapter_mod.EXPECTED_API_VERSION
        EXPECTED_BUILD_ID = adapter_mod.EXPECTED_BUILD_ID

        @staticmethod
        def locate_mainmenu_dir():
            return adapter_mod.locate_mainmenu_dir()

        @staticmethod
        def open_canonical_authority(master_path, is_main_thread_fn=None):
            broker, identity = adapter_mod.canonical_bootstrap(PACKAGE_PARENT, lambda: True)
            if Env.broker_wrapper:
                broker = Env.broker_wrapper[0](broker)
            return adapter_mod.CpmAuthorityAdapter(broker, master_path, Env.live_root, runtime_identity=identity)
    return Shim


def build_namespace(app):
    ns = {"os": os, "sys": sys, "hashlib": hashlib, "json": json, "QtCore": _QtStub}
    if not PY2:
        ns["unicode"] = str
        ns["unichr"] = chr
    for name in EXTRACT_TOP:
        _run_source(app.top_text(name), "app:%s" % name, ns)

    def forbidden(name):
        def f(*a, **k):
            Env.forbidden_calls.append(name)
            raise _Forbidden(name)
        return f
    for name in ("get_semantic_provider", "SidecarSemanticProvider", "MasterTxtSemanticProvider",
                 "acquire_semantic_provider_for_mode", "prod_semantic_provider_health_from_descriptor"):
        ns[name] = forbidden(name)
    ns["log_line"] = lambda *a, **k: None
    for name in LOGFIX_NAMESPACE_HELPERS + M06W1_NAMESPACE_HELPERS:
        if name in app.top:  # pinned historical references predate these helpers
            _run_source(app.top_text(name), "app:%s" % name, ns)
    ns["p01_master_path"] = lambda: os.path.join(Env.live_root, MASTER_NAME)

    def import_adapter():
        if Env.import_failure is not None:
            raise Env.import_failure
        return _shim_adapter_module()
    ns["prod_cpm_import_adapter"] = import_adapter
    ns["prod_resolve"] = lambda identity: {"animset": object(), "gm": None, "model": identity["model"],
                                           "checksum": identity["checksum"], "animset_name": identity["animset_name"]}
    ns["p01_all_supported_flex_bindings"] = lambda animset: [dict(b) for b in Env.bindings]
    ns["prod_load_character"] = lambda identity: Env.profile
    ns["prod_norm"] = lambda path: _TEXT(path).lower()
    ns["prod_key"] = lambda path: _TEXT(path).lower()
    ns["PROD_SCHEMA_VERSION"] = 3
    ns["p03_now_stamp"] = lambda: u"2026-09-28T00:00:00"
    ns["prod_paths"] = lambda identity: {"profile": os.path.join(FIXTURE_ROOT, "never_written.json")}
    ns["p02_safe_write_json"] = lambda path, record: Env.writes.append(path)
    ns["p02_read_json"] = lambda path: {}
    ns["P03_KIND_BODY"] = u"body"
    ns["P03_KIND_EXPRESSION"] = u"expression"
    return ns


def _bindings_from_pairs(pairs):
    out = []
    for i, (lit, shape) in enumerate(pairs):
        out.append({"literal": lit, "shape": shape, "global_key": (u"fixture", i)})
    return out


IDENTITY = {"model": u"models/fixture.mdl", "checksum": 7, "animset_name": u"fixture"}


def _broker():
    from sfm_master_authority_productionized import runtime
    return runtime.get_broker()


def _no_outstanding(label):
    b = _broker()
    check("idle.%s.no_outstanding_lease" % label, b.outstanding_lease_count() == 0)
    check("idle.%s.no_open_provider" % label, b.provider_counters()["current_open_provider_count"] == 0)


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------------------
# Section 3 -- runtime behavior of the migrated route
# ---------------------------------------------------------------------------

def section_route(ns, baseline):
    Env.bindings = _bindings_from_pairs(base.LIVE_BINDINGS)
    sha1 = _sha(os.path.join(G1_DIR, MASTER_NAME))

    adapter, health = ns["prod_probe_semantic_provider"](IDENTITY)
    check("health.healthy_small_valid_master", health["status"] == u"healthy", _canon(health))
    check("health.shape", sorted(health.keys()) == ["descriptor", "message", "reason", "status"])
    check("health.reason", health["reason"] == u"canonical-admission-and-view-validated")
    check("health.no_count_fields", not any(k in health["descriptor"] for k in ("occurrence_count", "fold_family_count")))
    check("health.adapter_is_canonical", isinstance(adapter, adapter_mod.CpmAuthorityAdapter))
    scope = ns["prod_scope"](IDENTITY, adapter)
    adapter = None
    check("scope.authority_pinned", scope["authority"] == {
        "provider_generation": 1, "provider_sha256": sha1, "semantic_policy_revision": ns["PROD_SEMANTIC_POLICY"],
        "override_revision": ns["prod_override_revision"](None)}, _canon(scope["authority"]))
    check("scope.schema", scope["schema"] == u"csp-semantic-scope-pure-v1")
    check("scope.provider_descriptor_detached", all(isinstance(v, (_TEXT, int, bool)) for v in scope["provider_descriptor"].values()))
    check("scope.capture_fields", ns["prod_provider_capture"](scope["provider_descriptor"]) == {
        "provider_contract": u"sfm-character-semantic-provider-v1", "source_sha256": sha1,
        "fold_policy": u"ascii-a-z-v1", "provider_generation": 1})
    _no_outstanding("after_scope")

    # Parity on the changed route: the app's scope rows equal the frozen
    # baseline's own snapshot functions applied to parity-proven answers.
    bns = {"hashlib": hashlib}
    if not PY2:
        bns["unicode"] = str
    for name in ("u", "SEMANTIC_STATUS_RESOLVED", "SEMANTIC_STATUS_CONFLICT", "SEMANTIC_STATUS_ABSENT",
                 "SEMANTIC_MATCH_EXACT", "SEMANTIC_MATCH_FOLDED", "SEMANTIC_MATCH_NONE", "SEMANTIC_STATUS_UNAVAILABLE",
                 "P01_STATUS_RESOLVED", "P01_STATUS_CONFLICT", "P01_STATUS_ABSENT", "P01_MATCH_FOLDED",
                 "SEMANTIC_BODY_MORPHS_PATH", "p01_is_face_path", "semantic_is_body_morph_path",
                 "semantic_snapshot_from_live_vocabulary", "semantic_snapshot_signature", "prod_pure_semantic_row"):
        _run_source(baseline.top_text(name), "baseline:%s" % name, bns)
    answers = _shim_adapter_module().open_canonical_authority(ns["p01_master_path"]()).query_many(base._live_literals())
    snap = bns["semantic_snapshot_from_live_vocabulary"](Env.bindings, answers)
    check("parity.scope_rows_equal_baseline_pipeline",
          _canon(scope["semantic"]["rows"]) == _canon([bns["prod_pure_semantic_row"](r) for r in snap["rows"]]))
    check("parity.scope_counts_hand_audit", scope["semantic"]["counts"] == base.EXPECTED_COUNTS, _canon(scope["semantic"]["counts"]))
    check("parity.scope_signature_equals_baseline",
          bns["semantic_snapshot_signature"]({"rows": scope["semantic"]["rows"]}) == bns["semantic_snapshot_signature"](snap))
    check("parity.expression_body_membership", sorted(scope["expression"].keys()) ==
          [u"Blink", u"Brow Up", u"bLiNk", u"jawopen", u"ÑOSE"] and sorted(scope["body"].keys()) == [u"Belly", u"chest"])
    check("parity.absence_distinct_from_conflict", scope["unresolved"] == [u"Brow  Up", u"Ghost", u"ñose"]
          and scope["conflicts"] == [u"WINK", u"Wink"], _canon([scope["unresolved"], scope["conflicts"]]))

    scope_default = ns["prod_scope"](IDENTITY)
    check("scope.default_provider_is_canonical_adapter", _canon(scope_default) == _canon(scope))
    check("route.historical_provider_never_called", Env.forbidden_calls == [], Env.forbidden_calls)
    check("route.matches_identity_current", ns["prod_scope_matches_identity"](scope, IDENTITY) is True)
    live = ns["prod_live_bindings_for_cached_scope"](IDENTITY, scope, u"expression")
    check("route.live_bindings_before_mutation", sorted(live["accepted"].keys()) == sorted(scope["expression"].keys()))
    check("r6.live_bindings_provider_is_fail_closed", type(live["provider"]).__name__ == "ProdCpmUnmigratedProvider")
    raises("r6.late_query_fails_closed", (ns["ProdCpmAuthorityNotMigrated"],), lambda: live["provider"].query_many([u"Belly"]))
    raises("r6.late_descriptor_fails_closed", (ns["ProdCpmAuthorityNotMigrated"],), lambda: ns["prod_provider_capture"](live["provider"]))
    raises("r6.fit_warning_path_fails_closed", (ns["ProdCpmAuthorityNotMigrated"],), lambda: ns["p03_unmapped_relevant_controls"](
        {"provider": live["provider"]}, [{"literal": u"Belly", "shape": u"b", "global_key": u"k"}], {"mappings": []}))
    Env.profile = None
    raises("r6.character_record_fails_closed", (ns["ProdCpmAuthorityNotMigrated"],), lambda: ns["prod_character_record"](IDENTITY))
    raises("r6.ensure_character_new_fails_closed", (ns["ProdCpmAuthorityNotMigrated"],), lambda: ns["prod_ensure_character"](IDENTITY))
    Env.profile = {"schema_version": 3, "semantic_overrides": {}, "semantic_override_revision": 0, "model_ref": {}}
    raises("r6.ensure_character_existing_fails_closed", (ns["ProdCpmAuthorityNotMigrated"],), lambda: ns["prod_ensure_character"](IDENTITY))
    Env.profile = None
    check("r6.no_durable_write_before_refusal", Env.writes == [], Env.writes)
    check("r6.no_historical_fallback", Env.forbidden_calls == [], Env.forbidden_calls)
    _no_outstanding("route")
    return scope


def section_failures(ns):
    Env.bindings = _bindings_from_pairs(base.LIVE_BINDINGS)

    Env.import_failure = ImportError("fixture: cpm_authority_adapter not installed")
    adapter, health = ns["prod_probe_semantic_provider"](IDENTITY)
    check("fail.bootstrap_import_unavailable", adapter is None and health["status"] == u"unavailable"
          and health["reason"] == u"cpm-authority-bootstrap-failed")
    raises("fail.bootstrap_import_descriptor_raises", (ImportError,), ns["prod_current_provider_descriptor"])
    Env.import_failure = None

    from sfm_master_authority_productionized import runtime
    for attr, value, reason in (("RUNTIME_API_VERSION", "9.9.9", u"runtime API"),
                                ("RUNTIME_BUILD_ID", "other-build", u"runtime build")):
        old = getattr(runtime, attr)
        setattr(runtime, attr, value)
        try:
            adapter, health = ns["prod_probe_semantic_provider"](IDENTITY)
        finally:
            setattr(runtime, attr, old)
        check("fail.%s_unavailable" % attr.lower(), adapter is None and health["status"] == u"unavailable"
              and reason in (health["message"] or u""), _canon(health))

    Env.live_root = CORRUPT_DIR
    adapter, health = ns["prod_probe_semantic_provider"](IDENTITY)
    check("fail.invalid_authority_unavailable", adapter is None and health["status"] == u"unavailable"
          and health["reason"].startswith(u"acquisition-failed:"), _canon(health))
    Env.live_root = LIVE_DIR

    def dropping(real):
        def acquire(master_path, specs, **kwargs):
            (kind, (folds, _)), = list(specs.items())
            narrowed = frozenset(folds) - frozenset([u"ghost"])
            return real.acquire_or_reuse_views(master_path, {kind: (narrowed, cpm.build_cpm_compat_v1_projection(narrowed))}, **kwargs)
        return base._ProxyBroker(real, acquire_or_reuse_views=acquire)
    Env.broker_wrapper = [dropping]
    adapter, health = ns["prod_probe_semantic_provider"](IDENTITY)
    Env.broker_wrapper = []
    check("fail.uncovered_unavailable_not_absence", adapter is None and health["status"] == u"unavailable"
          and health["reason"] == u"projection-invalid", _canon(health))
    check("fail.no_historical_fallback", Env.forbidden_calls == [], Env.forbidden_calls)
    _no_outstanding("failures")


class FakeWindow(object):
    def __init__(self):
        self.scope = None
        self.identity = None
        self.provider_health = None
        self.operation = None
        self.fit_active = False
        self.select_calls = []
        self.action_calls = 0

        class Combo(object):
            def currentIndex(self):
                return 3
        self.combo = Combo()


def section_stale_generation(ns, app, scope_g1):
    methods = {}
    for name in ("prod_cpm_request_stale_rebuild_if_needed", "prod_cpm_run_stale_rebuild", "semantic_provider_ready"):
        _run_source(app.method_text("ProdWindow", name), "app:ProdWindow.%s" % name, ns, methods)
    for name, fn in methods.items():
        setattr(FakeWindow, name, fn)
    sha1 = _sha(os.path.join(G1_DIR, MASTER_NAME))
    sha2 = _sha(os.path.join(G2_DIR, MASTER_NAME))

    def select_model(self, index):
        # Stand-in for the existing select_model -> guard -> render path:
        # probe current authority, rebuild the scope, republish.
        self.select_calls.append(index)
        self.scope_at_rebuild = self.scope
        adapter, health = ns["prod_probe_semantic_provider"](self.identity)
        self.provider_health = health
        self.scope = ns["prod_scope"](self.identity, adapter) if health["status"] == u"healthy" else None
    FakeWindow.select_model = select_model

    win = FakeWindow()
    win.identity = dict(IDENTITY)
    win.provider_health = {"status": u"healthy"}
    win.scope = scope_g1
    _QtStub.QTimer.scheduled = []
    check("stale.current_generation_ready", win.semantic_provider_ready() is True and _QtStub.QTimer.scheduled == [])

    def stale_action():
        # The semantic-dependent part of an action: the live-binding check
        # that precedes every Save/Update/Apply mutation.
        win.action_calls += 1
        ns["prod_live_bindings_for_cached_scope"](win.identity, win.scope, u"expression")
        raise AssertionError("mutation would have been reached")

    base._copy_dir_files(G2_DIR, LIVE_DIR)
    try:
        check("stale.generation_detected", ns["prod_cpm_scope_generation_stale"](win.scope) is True)
        exc = raises("stale.action_rejected_before_mutation", (RuntimeError,), stale_action)
        check("stale.rejection_is_stale_scope", exc is not None and "stale" in _TEXT(exc) and not isinstance(exc, AssertionError))
        check("stale.not_ready", win.semantic_provider_ready() is False)
        check("stale.rebuild_scheduled_once", len(_QtStub.QTimer.scheduled) == 1 and _QtStub.QTimer.scheduled[0][0] == 0)
        win.semantic_provider_ready()
        check("stale.no_duplicate_schedule", len(_QtStub.QTimer.scheduled) == 1)
        check("stale.scope_kept_until_rebuild_runs", win.scope is scope_g1)
        win.operation = {"label": u"busy"}
        callback = _QtStub.QTimer.scheduled[0][1]
        check("stale.busy_defers_rebuild", callback() is False and win.select_calls == []
              and _QtStub.QTimer.scheduled[-1][0] == 250 and win.scope is scope_g1)
        win.operation = None
        check("stale.rebuild_runs", callback() is True and win.select_calls == [3])
        check("stale.stale_scope_discarded_before_rebuild", getattr(win, "scope_at_rebuild", "unset") is None)
        check("stale.rebuilt_under_current_generation", win.scope is not None and win.scope["authority"]["provider_sha256"] == sha2)
        check("stale.rebuilt_scope_ready", win.semantic_provider_ready() is True)
        check("stale.no_replay_of_rejected_action", win.action_calls == 1)
        check("stale.new_user_action_required", win.select_calls == [3] and len(_QtStub.QTimer.scheduled) == 2)
        _no_outstanding("stale_rebuild")
    finally:
        base._copy_dir_files(G1_DIR, LIVE_DIR)

    # Non-generation mismatch keeps existing behavior (no rebuild).
    win2 = FakeWindow()
    win2.identity = dict(IDENTITY, checksum=8)
    win2.provider_health = {"status": u"healthy"}
    win2.scope = scope_g1
    _QtStub.QTimer.scheduled = []
    check("stale.identity_mismatch_not_generation", win2.semantic_provider_ready() is False and _QtStub.QTimer.scheduled == [])
    check("stale.generation_current_after_restore", ns["prod_cpm_scope_generation_stale"](scope_g1) is False)
    check("stale.no_historical_fallback", Env.forbidden_calls == [], Env.forbidden_calls)


# ---------------------------------------------------------------------------
# Section 4 -- prod_cpm_import_adapter in a clean child interpreter
# ---------------------------------------------------------------------------

CHILD = r'''
import os, sys, json
src, fake_exe, mode, extra = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
if mode == "collision":
    sys.path.insert(0, extra)
    import cpm_authority_adapter
sys.executable = fake_exe
ns = {"os": os, "sys": sys}
with open(src, "rb") as f:
    exec(compile(f.read(), "app:import", "exec"), ns)
try:
    m = ns["prod_cpm_import_adapter"]()
    out = {"ok": True, "origin": os.path.normcase(os.path.dirname(os.path.abspath(m.__file__)))}
except Exception as exc:
    out = {"ok": False, "error": type(exc).__name__}
out["mainmenu"] = os.path.normcase(ns["prod_cpm_mainmenu_dir"]())
print("CHILD_RESULT " + json.dumps(out))
'''


def section_import(app):
    game = os.path.join(FIXTURE_ROOT, "fake_sfm", "game")
    mainmenu = os.path.join(game, "usermod", "scripts", "SFM Character Tools")
    if not os.path.isdir(mainmenu):
        os.makedirs(mainmenu)
    for name in ("cpm_authority_adapter.py", "cpm_compat_v1_projection.py"):
        shutil.copyfile(os.path.join(MODULE_DIR, name), os.path.join(mainmenu, name))
    src_path = os.path.join(FIXTURE_ROOT, "extracted_import.py")
    with io.open(src_path, "w", encoding="utf-8") as f:
        f.write(u"\n".join(app.top_text(n) for n in (
            "PROD_CPM_MAINMENU_RELATIVE_PARTS", "PROD_CPM_ADAPTER_MODULES", "ProdCpmAuthorityBootstrapError",
            "prod_cpm_mainmenu_dir", "prod_cpm_import_adapter")))
    fake_exe = os.path.join(game, "sfm.exe")

    def run(mode, extra=u""):
        out = subprocess.check_output([sys.executable, "-c", CHILD, src_path, fake_exe, mode, extra or "-"])
        for line in out.decode("utf-8").splitlines():
            if line.startswith("CHILD_RESULT "):
                return json.loads(line[len("CHILD_RESULT "):])
        return {}
    ok = run("clean")
    check("import.formula_from_sys_executable", ok.get("mainmenu") == os.path.normcase(mainmenu))
    check("import.loads_from_canonical_mainmenu", ok.get("ok") is True and ok.get("origin") == os.path.normcase(mainmenu), ok)
    bad = run("collision", MODULE_DIR)
    check("import.same_name_module_elsewhere_refused", bad.get("ok") is False
          and bad.get("error") == "ProdCpmAuthorityBootstrapError", bad)


# ---------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------

def run_suite():
    app = AppSource(APP_PATH)
    baseline = section_derivation(app)
    section_reachability(app)
    ns = build_namespace(app)
    scope = section_route(ns, baseline)
    section_failures(ns)
    section_stale_generation(ns, app, scope)
    section_import(app)
    _no_outstanding("suite_end")


def write_digest(path):
    records = [[name, ok, _canon(value)] for name, ok, value in RESULTS]
    body = json.dumps(records, sort_keys=True, ensure_ascii=True, indent=0, separators=(",", ":"))
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(_TEXT(body))
    print("digest: %s sha256=%s checks=%d" % (os.path.basename(path),
                                              hashlib.sha256(body.encode("utf-8")).hexdigest(), len(records)))


def phase_publish():
    if os.path.isdir(FIXTURE_ROOT):
        shutil.rmtree(FIXTURE_ROOT)
    os.makedirs(FIXTURE_ROOT)
    from sfm_master_sidecar import publisher
    for directory, body in ((G1_DIR, base.MASTER_G1), (G2_DIR, base.MASTER_G2), (CORRUPT_DIR, base.MASTER_CORRUPT)):
        result = publisher.publish(base._write_master(directory, body), directory)
        check("publish.%s" % os.path.basename(directory), os.path.isfile(str(result.generation_path)))
    base._copy_dir_files(G1_DIR, LIVE_DIR)
    artifacts = [n for n in os.listdir(CORRUPT_DIR) if n.endswith(".sfmsidecar")]
    path = os.path.join(CORRUPT_DIR, artifacts[0])
    with open(path, "rb") as f:
        data = bytearray(f.read())
    data[len(data) // 2] ^= 0xFF
    with open(path, "wb") as f:
        f.write(bytes(data))
    if not all(r[1] for r in RESULTS):
        print("RESULT: setup failed")
        sys.exit(1)
    del RESULTS[:]
    run_suite()
    write_digest(DIGEST_PY3)


def phase_suite():
    if not (os.path.isfile(os.path.join(LIVE_DIR, MASTER_NAME)) and os.path.isfile(DIGEST_PY3)):
        print("RESULT: fixtures missing; run --phase=publish first")
        sys.exit(1)
    run_suite()
    write_digest(DIGEST_PY27 if PY2 else DIGEST_PY3 + ".rerun")


def phase_compare():
    with io.open(DIGEST_PY3, encoding="utf-8") as f:
        a = f.read()
    with io.open(DIGEST_PY27, encoding="utf-8") as f:
        b = f.read()
    ra, rb = json.loads(a), json.loads(b)
    check("compare.same_check_count", len(ra) == len(rb), [len(ra), len(rb)])
    check("compare.identical_results_and_values", a == b, [x[0] for x, y in zip(ra, rb) if x != y][:10])
    check("compare.all_pass_both", all(x[1] for x in ra) and all(y[1] for y in rb))
    print("py3 digest sha256=%s" % hashlib.sha256(a.encode("utf-8")).hexdigest())
    print("py27 digest sha256=%s" % hashlib.sha256(b.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    phase = None
    for arg in sys.argv[1:]:
        if arg.startswith("--phase="):
            phase = arg.split("=", 1)[1]
    if phase not in ("publish", "suite", "compare"):
        print("usage: %s --phase=publish|suite|compare" % os.path.basename(sys.argv[0]))
        sys.exit(2)
    print("Interpreter: %s" % sys.version.split()[0])
    print("Phase: %s" % phase)
    {"publish": phase_publish, "suite": phase_suite, "compare": phase_compare}[phase]()
    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    if passed != len(RESULTS):
        sys.exit(1)
