# F-01 M1 Stage C — CPM integration audit and seams

**Authority:** F-01 M1 Implementation Addendum R2.1 §§1.3, 8, 9.3 and 10; Owner authorization of Stage C
(2026-11-02), including the binding requirement that a saved pose stays usable after SFM restarts, without the
source animation set or shot. **Scope:** offline integration only. There are no scene writes, no Poses page, no
native execution and no installation change. Stage D needs separate Owner authorization.

**Base:** `feature/f01-pose-library` at `02e00853` (F-01 CPM `648c881c…` = M-06 W1 `fd853661…` followed by the
Stage A/B block). The selected-instance closure is the one pinned there (§1.3); Stage C reuses it and does not
copy it.

## 1. What Stage C adds

| Area | Change |
|---|---|
| Pose dispatch | `ProdWindow.apply_pose(item)` and `ProdWindow.save_pose(name, regions)`, both through `pose_guard` → the existing `ProdWindow.guard`. That gives one operation at a time, the M-06 pinned operation context, and the shared error, outcome and resource handling. Not wired to any widget yet. |
| Authorization | `prod_pose_authorize` binds the operation's pinned M-06 context (revalidated with `prod_validate_context_token`), the hash-pinned registry and its mode, the destination's listed rig class, and the record's identity and revision. It never uses the flex semantic scope or `prod_cpm_authorize_operation`. |
| Registry | `prod_pose_load_registry`: `cpm_pose_profiles_v1.json` from the MAINMENU directory, pinned to `87efaad9…`. Production mode unless `ProdWindow.pose_mode` is set explicitly (qualification). |
| Library context | `prod_pose_selected_library`: CPM's own character key, character folder and library root. Without the root, the P1 containment check refuses every write. `prod_pose_reread`: a fresh check of an own or a foreign record before Apply. |
| Continuation | `pose_begin_verification` hands a committed Apply Pose to the **shared** `apply_verification_turn`; a pose continuation record (`kind="pose"`) is dispatched to `prod_pose_deferred_verify` and `pose_finish_verification`. Stale tokens, close-before-turn, modal or suspended state and scheduling failure behave as in M-05. |
| Deferred gate | `prod_pose_context_gate`: the pinned destination instance must still resolve identically (`prod_context_token_matches`); otherwise the result is committed-unverified, `context-changed`. |
| Recovery block | A recovery-unverified Pose result sets `pose_recovery_blocked`; Apply and Save are refused until CPM reopens (§8.5). |
| Error copy | `operation_default_error_copy` keeps Pose refusal copy (titles "Pose Not Applied" / "Pose Not Saved"). `pose_guard` replaces unexpected internal errors with the UX spec's "nothing was changed" copy and logs them in full. |
| Tab strip | `tool_apply_tab_style`: `padding: 6px 8px`, `min-width` removed (§9.3). Native fit check U-1 remains. |
| Stage D seams | `prod_pose_capture`, `prod_pose_apply` and `prod_pose_verify_applied` are explicit refusals or unverified results. Stage C writes nothing to the scene. |

## 2. Audit of existing paths (§10.1)

Each function was traced in the real source. "Pose calls" means the Stage C Pose path uses it.

| Function | Pose calls | Branches on `kind` | Unexpected kind `"pose"` before Stage C | Stage C |
|---|---|---|---|---|
| `ProdWindow.guard` / `operation_begin` / `operation_revalidate` / `operation_end` | yes | no (label only) | — | reused unchanged; pins the M-06 context for Pose labels |
| `ProdWindow.current` | yes | no | — | reused (revalidates the pinned instance) |
| `prod_context_token`, `prod_validate_context_token`, `prod_context_token_matches`, `prod_resolve_instance`, `prod_instance_token` | yes | no | — | reused unchanged |
| `prod_instance_channels_clip`, `prod_instance_pair_check` | Stage D (C9b, C4) | no | — | unchanged |
| `prod_cpm_authorize_operation` | **no** | `kind is not None`; Body vs everything else | would authorize **Expression** membership | explicit refusal of `"pose"` before any authority access; `kind=None` (Review flex edit) and Body/Expression unchanged |
| `prod_live_bindings_for_cached_scope` | no | Body / Expression only | `NameError` (accidental refusal) | unchanged; unreachable for poses |
| `prod_paths` | yes | no | — | gains `"pose"` (§4.1) |
| `prod_preset_dir` (→ `prod_unique_path`, `prod_discover`, `prod_save`) | **no** | Body vs everything else | **Expression folder** | explicit refusal |
| `prod_validate_preset` (→ `prod_reread_selected_record`, `prod_update_preset`, `prod_move_current_preset_to_trash`) | no | positive Body/Expression whitelist | refused ("Preset kind is unsupported.") | unchanged (already safe) |
| `prod_apply` (Undo label site) | **no** | Body vs everything else | Expression Apply and label | explicit refusal at entry |
| `prod_favorite_key` | no (Stage B has `prod_pose_favorite_key`) | no | `pose:<id>`, the same key | unchanged |
| `ProdWindow.selected_or_none`, `refresh_preset_view` | no | Body vs everything else | **Expression list** | explicit refusal |
| `ProdWindow.apply_kind` | no | Body vs Expression copy | Expression Apply | explicit refusal (`apply_pose` is the dispatch) |
| `ProdWindow.apply_begin_verification` | no | label | "Apply Expression" continuation | explicit refusal (`pose_begin_verification`) |
| `ProdWindow.apply_verification_turn` | yes | — | Body verification | dispatches `kind="pose"` to `prod_pose_deferred_verify`; Body/Expression unchanged |
| `ProdWindow.apply_finish_verification` | yes | Body vs Expression copy | "Expression applied." | dispatches `kind="pose"` to `pose_finish_verification` |
| `ProdWindow.apply_close_pending_verification`, `operation_continuation_owned` | yes | no | — | reused unchanged |
| `ProdWindow.operation_default_error_copy` | yes | label | generic "Try again." | Pose branch keeps Pose copy |
| `ProdWindow.tab_changed` | Stage D (Poses page) | page identity | — | unchanged |

No indiscriminate unknown-kind rejection was added (§10.3). Every new refusal names `"pose"` only.

## 3. Source-independent persistence

- A pose record holds only its own data: the envelope, the regions, and `pose.source` as display-only provenance
  (rig class, model, shot name, times). It holds no DME identity, animation-set key, document key or handle.
- Apply resolves the **destination** only, through the window's current M-06 selection. No Stage C function reads
  `pose.source` (static check), and authorization never consults the source.
- The Stage C suite saves a pose, starts a new session (new session token, new scene, new instances; the source
  animation set is absent), lists the pose from disk and applies it. Authorization pins the independent
  destination, the result is verified, the earlier session's selection is refused, and the record bytes are
  unchanged.
- Stage D's native checkpoint must still demonstrate this in SFM: save, close SFM, restart, open an independent
  destination session, apply, then check exact-time keys, the pose, Undo and Redo.

## 4. Verification (Python 3.10.6 and SFM 2.7.5)

See the Stage C report for the run results. New suite: `cpm/convergence/tests/test_cpm_app_f01_pose_integration.py`
(`--phase=run`). Mutation spot-checks: removing the M-06 revalidation from `prod_pose_authorize`, or the Pose
dispatch from the shared turn, each fails three behavioural checks.

## 5. Open for Stage D

Stage D implements, at least, C4/C9b/C7b/C8/C10 behind the three refusing seams: P1–P6 Apply with exact-time update
and insertion, Abort verification, the P7 verification items and the time-triple gate. It also adds a minimal Poses
page and capture for Save New. It must keep `pose.source` out of every live path.
