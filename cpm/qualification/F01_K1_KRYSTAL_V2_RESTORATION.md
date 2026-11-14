# F-01 K1: Krystal v2 Full body restoration — offline checkpoint (2026-11-14)

**Authority:** "F-01 Pose Library — K1: Krystal v2 Full Body Restoration" (APPROVED, bounded offline implementation
and testing), under Blueprint R4 section 5 (`F01_BLUEPRINT_R4_REVISED_OWNER_REVIEW_20261114.md`, adopted `be886d0`).
**Starting checkpoint:** `407ac5a` (CPM `29db211d…`, the PS-2 UI corrections included; working tree matched it).
**Status:** offline qualification candidate ready for designer review. **Not natively qualified; not promoted.**

## Identities

| Item | Value |
|---|---|
| Candidate CPM (production mode, as committed) | `3984e1e1d5d2018202fa551700564da6796cc1063c2be7a32112ad023db5ae9c` (1,453,736 B) |
| K1 qualification build (one line, 42182: `PROD_POSE_REGISTRY_MODE = u"qualification"`) | `37b0cce608062f2a7e03bab03ee4e590fc3f8c395a2c300538df44e3893b1868` (derived offline, not installed) |
| Body registry (mapping unchanged, `experimental`) | `cpm_body_profiles_v1.json` `22dcd1599c0556bcb71df0a9b9d14657684173b3bbf557250710a8104a6baa26` |
| Pose registry (unchanged) | `cpm_pose_profiles_v1.json` `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |

The v2 mapping, its registry, the `prod_body_*` engine and every v2 record format are unchanged. In the production
build the mapping stays experimental, so Krystal's Full body still refuses there (`rig-driven`); the v2 route is usable
only in the qualification build until the native integration check and a separate promotion decision.

## Route traced (current code) and barriers found

| Step | Current code | v2 status |
|---|---|---|
| Save New | `ProdWindow.save_pose` → `prod_pose_authorize` (registry) decides the v2 body route → generic `prod_scope_authorize`, `prod_scope_current_time`, `prod_scope_inventory` → the Save dialog (`prompt_pose_scope`, body route shows the v2 summary and enables Save) → registry capture `prod_body_capture` → `prod_pose_save_new` | **two barriers (below)** |
| Update | `ProdWindow.update_pose`: v2 records keep `prod_body_current_time` + `prod_body_capture`; `prod_pose_update` keeps the regions check for v1/v2 | unchanged since S3 |
| Record loading | `prod_pose_parse` / `prod_pose_validate`: v3 branch added in front; v2 still requires the body registry | unchanged for v2 |
| Poses page | `pose_ui_state`: `prod_scope_parts` returns the same sorted regions for v1/v2; availability through `prod_pose_browse_eligible` | equivalent for v2 |
| Apply | `ProdWindow.apply_pose`: v3 → `prod_scope_*`; v2 → `prod_pose_authorize` + `prod_body_apply`; v1 → `prod_pose_apply` | unchanged for v2 |
| Deferred verification | `prod_pose_deferred_verify`: scoped branch added in front; v2 → `prod_body_verify_applied` | unchanged for v2 |

Since the S3 build (`e98b90b`, CPM `f6098b3a…`): all 53 `prod_body_*` functions and the shared transaction helpers are
unchanged; the only v2-relevant changes are the SFP-1 Save dialog route and the version dispatch added in front of the
v2 branches. Changed module constants since S3 affect presentation only.

**Barrier 1 — generic inventory before the dialog (R4 section 5).** For every character, including one with a usable
v2 route, `save_pose` ran the generic v3 authorization, time pin (a clock check over all generic channels) and
inventory before the dialog. Any generic refusal there (for example a non-written channel off the mapped tick or an
unsupported generic binding) refused Save even though the v2 route would capture. Shown offline: with a generic
inventory refusal, the unchanged CPM refuses (`K1.generic_refusal_does_not_block_the_v2_route` FAILS at `29db211d…`).

**Barrier 2 — the wrong time pin for v2.** On the dialog route the v2 capture compared against the generic v3 time
pin; the S3-qualified sequence pins the body time over the profile's written handle channels when the dialog opens.
Shown offline: a v3 pin that disagrees with the scene makes the v2 capture stale on the unchanged CPM
(`K1.dialog_route_v2_save_uses_the_body_time_pin` FAILS at `29db211d…`).

## Changes (minimum)

`cpm/app/SFM_Character_Preset_Manager.py`:
1. `ProdWindow.save_pose`: when the v2 body route is usable, pin the body time (`prod_body_current_time`) when the
   dialog opens and use it for the v2 capture; build the generic inventory in a guarded step — a generic refusal is
   kept (logged `PROD_POSE_K1-generic-inventory-unavailable`) and the dialog opens with Full body on the v2 route and
   Selected parts unavailable. Without a v2 route the generic refusal stands exactly as before. Choosing Selected parts
   without a generic inventory refuses with the generic refusal's own reason and saves nothing.
2. `prod_scope_selected_parts_unavailable(reason)` (new): the dialog inventory for that case.
3. `ProdWindow.prompt_pose_scope`: when the inventory says Selected parts is unavailable, its radio button is disabled
   with the reason as its tooltip. No other dialog change; the PS-2 UI corrections are kept.

No change to the v2 mapping, records, registries, `prod_body_*`, transactions, Undo/Redo, Abort, P7, tolerances, the
v1 or v3 routes, or production capability status.

## Offline evidence

New body-suite section `K1` (real `ProdWindow.save_pose`, `update_pose`, `apply_pose` on the S0-derived Krystal fake
scene; qualification build mode unless stated):

| Check | Result |
|---|---|
| `K1.production_has_no_v2_route_and_a_generic_refusal_still_refuses` | PASS (production unchanged) |
| `K1.dialog_route_v2_save_uses_the_body_time_pin` | PASS (FAILS on `29db211d…`) |
| `K1.v2_save_writes_nothing_to_the_scene` | PASS |
| `K1.generic_refusal_does_not_block_the_v2_route` | PASS (FAILS on `29db211d…`) |
| `K1.selected_parts_without_a_generic_inventory_refuses_with_its_reason_and_saves_nothing` | PASS |
| `K1.saved_v2_record_reloads` | PASS |
| `K1.apply_dispatches_the_v2_transaction` (real `prod_body_apply`, one owned Undo) | PASS |
| `K1.deferred_verification_verifies_the_v2_pose` (`committed-verified`) | PASS |
| `K1.update_recaptures_the_v2_record_in_place` | PASS |
| `K1.v1_and_v2_dispatch_unchanged` | PASS |

Save dialog page suite (real Qt, 2.7.5): new `D9` (no generic inventory: Full body keeps the v2 route and its summary,
Save enabled, Selected parts disabled with the reason) PASS; D5 (v2 route through the real dialog) and D1–D8 PASS.

**Regression (Python 2.7.5 and 3.10.6):** all 48 CPM suite runs have the same exit codes and failing-check sets as
at `407ac5a`; body 257/257 (was 246; +K1), Save dialog page 17/17 (was 16; +D9), scoped 484/484, Poses page 120/120,
pose core/library/integration/live, M-05/M-06, clothing fit and operation context unchanged; canonical route only its
historical row. Kits unchanged: EF-1 34/34, SFP-1 19/19, S3 37/37, PS-2 14/14. **Counter-check:** the K1 section run
against the unchanged CPM `29db211d…` (via `CPM_TEST_APP_PATH`) fails the two barrier checks.

## Not demonstrated offline (requires the native integration check)

Native behaviour of the real modal dialog with the body pin on the Krystal R2 fixture; v2 Save, reopen, Apply to a
visibly different instance, Update and Undo/Redo through the current product path (R4 section 5 sequence); placement,
useful whole-body result and preservation in SFM. S3's native evidence (runs 1–5: capture, Apply, persistence, update,
no-op, navigation, Undo/Redo, verified Abort) is reused for the unchanged v2 engine, not re-established.

## Remaining integration risks (for the native check)

- The generic inventory path on the real Krystal scene: PS-2 showed it builds there (it reported `rig-driven`), so the
  guarded fallback is expected not to trigger on the R2 fixture; if it does, the log line `K1-generic-inventory-
  unavailable` records why.
- The body time pin is now taken before the generic steps; a clock refusal there refuses Save with the existing clock
  copy (as S3's flow did).
- The qualification build makes every experimental mapping usable (also the right-arm mapping), as in all earlier
  qualification builds; production promotion of the v2 mapping is a separate decision after the native check.
