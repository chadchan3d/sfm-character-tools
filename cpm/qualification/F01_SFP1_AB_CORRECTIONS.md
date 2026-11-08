# F-01 SFP-1 Stages A/B — Implementation Corrections (Astra review of `abe58bb`)

**Date:** 2026-11-08. **Authority:** Owner-approved Astra implementation review of `abe58bb` — ACCEPT WITH
CORRECTIONS; bounded correction of the three demonstrated P1 findings. Specification: R3
(`F01_SCOPED_POSE_BLUEPRINT_R3_20261108.md`), unchanged. **Status:** offline correction complete. CPM
`54e2028d…` -> `d9d8b359009fb05009fde5000a4d10e18258b5fb65e9da1d4e75a811b24423c0`. Not natively qualified; nothing
installed, enabled, pushed, merged, packaged or released.

## 1. Corrections

| Finding | Root cause in `abe58bb` | Correction |
|---|---|---|
| **1. Unsupported channel indices** passed production Apply and verified | `prod_scope_discover` recorded `fromIndex`/`toIndex`, but `prod_scope_classify` never checked them and `prod_scope_bindings` revalidated nothing | `prod_scope_index_supported`: the existing supported endpoint contract (qualified rig-input binding `prod_pose_channel_binding` and the carried admission; R3 3.1 "supported scalar endpoint indices"): a readable native integer equal to 0, any integer type the bindings return (Python 2 `long` included). Absent, unreadable, nonzero, negative, bool, float and text refuse. Applied in `prod_scope_classify` (the bone becomes unresolved, "unsupported channel index"; supported scale-operator channels too), in `prod_scope_check_authority` for every written channel, and in `prod_scope_bindings`, which now revalidates both indices and the one-layer transform log from the live channel at capture, P1, P2 and (new) P7. |
| **2. Blanket follower exemption**: a constraint-driven bone outside the selection moved and still verified | `prod_scope_followers` exempted every slave of a constraint reading an affected bone, and its descendants, from P7's unchanged check | `prod_scope_followers` classifies each follower by bounded relationship. Parent following stays as before (carried descendants in A, expected and verified). The one-way dependence of an explicitly excluded, confined subsystem (R3 4, boundary from `prod_scope_exclusion_boundary`) is retained. Every other follower — a body bone outside the scope, a dependency bone, a rig handle, the model or any other element — has no qualified relationship contract, so the scope refuses (`shared-input`, naming it) before any write. Pole targets now count as reads. Called from `prod_scope_check_authority`, so Save, P1, P2 and P7 all apply it. No constraint solver. |
| **3. Skeletal parent relationships** unprotected: same-transform reparenting escaped P7 | `prod_scope_identity` held bone DAG/transform handles but not parent membership; `prod_scope_verify` compared transforms only | `prod_scope_identity` records each bone's parent DAG identity and the model DAG's parents (compared at P2, during verified Abort recovery, and at P7). `prod_scope_verify` also compares every bone's parent, parent count and parent DAG identities against the baseline, and a changed bone set. `prod_scope_live` refuses (`structure-unsupported`) any bone without exactly one parent that is the model or another bone of the instance (missing, duplicated, foreign or self parent). Identity is compared only within one operation; records hold no runtime handle, so independent operations with different handles are unaffected. |

Unchanged: R3 coverage, ownership and dependency rules; version 1/2 code paths (`prod_pose_channel_binding`
untouched); production gating (`PROD_POSE_REGISTRY_MODE` production, `direct_fk_v1` experimental,
`constant_channel_carried_v1` disabled); the transaction contract; the user copy (existing codes reused).

## 2. Astra's counterexamples: before and after

Before = the new tests run against unmodified `54e2028d…` (Python 3.10.6); after = `d9d8b359…` (both interpreters).

| Counterexample (test) | Before | After |
|---|---|---|
| Modified `toIndex`/`fromIndex` on a written channel, production Apply (`AX1.nonzero_*`) | `verification-pending`, then **`committed-verified`** | refused at P1 `unsupported-selection`; no write, no Undo |
| Constraint follower outside the selection (`AX2.astra_counterexample_…`): `tail` point-constrained to `finger3` with a 100-unit offset | `followers: ['tail']`, **`committed-verified`** while `tail` moved **193.6 units** | refused at P1 `shared-input` naming `tail`; no write, no Undo, `tail` unmoved |
| Unselected jaw re-parented head -> spine with local and world transforms numerically identical (`AX3.astra_counterexample_…`) | **`committed-verified`** | `committed-unverified` (context changed) |

New tests: 49 AX checks plus the section row (section `corrections`): AX1 — nonzero from/to, negative, missing, unreadable, float, bool and
text indices (each refused with no write or Undo), native integer zero accepted, Save refuses before publication, Full
body refuses an index anywhere in the body, classification reason, P2 change -> stale, change before P7 ->
committed-unverified, binding revalidation, and the real `ProdWindow.apply_pose` path; AX2 — point and orientation
followers, Save refusal, follower introduced at P2 / before P7, plus valid following (constraint between unaffected
bones, carried descendants matching an independent matrix evaluation, excluded facial head-follow); AX3 —
same-transform reparenting at P2 / P7 / during the transaction (Abort recovery unverified), changed parent identity,
stale replaced parent element, duplicated and missing parents, unchanged hierarchy verified and its repeat a true
no-op, and an independent operation with different runtime handles. Before the correction 26 of the 49 AX checks failed (and nothing else); the
P2 and Abort reparenting rows already refused through an incidental change in the compiled scope's bone order, now
backed by the explicit parent identity.

## 3. Regression (offline, Python 2.7.5 SFM `-E -s -B` and 3.10.6 `-I`)

| Suite | `abe58bb` | corrected |
|---|---|---|
| `test_cpm_app_f01_scoped.py` | 218/218 both | **268/268 both** (+50 AX rows) |
| `test_cpm_app_f01_scoped_page.py` (real Qt dialog, 2.7.5) | 12/12 | 12/12 |
| `test_cpm_app_f01_body.py` | 246/246 both | 246/246 both |
| `test_cpm_app_f01_pose_core/library/integration/live.py` | 255/87/204/104 both | identical |
| `test_cpm_app_f01_pose_page.py` (2.7.5) | 118/118 | 118/118 |
| `test_cpm_app_canonical_route.py` | 84/85 (historical row) | 84/85, same historical row |

Canonical route: the only difference against the suite's expected sets remains `PROD_EMPTY_STATE_GUIDANCE` and
`prod_model_candidates` (present and unlisted since `ea5e7c4`); the two new helpers are listed in
`F01_SFP1_NEW_TOP` (harness bounds only). Production gating rows (`N.shipped_build_is_production…`,
`N.production_authorization_refuses_the_experimental_rule`, `N.production_save_new…_is_unchanged`) and version 1/2
rows (`A.version_1_records_keep_their_reader`, `N.krystal_full_body_keeps_its_version_2_route`, dispatch rows, the
body and pose suites) pass unchanged.

## 4. Safety notes found during the correction (not changed here)

1. **Followers outside the inventoried operators.** Follower discovery sees the operators of this animation set and
   of the shot (as `abe58bb`). A constraint stored in another animation set (for example a prop's) that reads a posed
   bone is not inventoried; its target is outside this instance, so P7 does not check it. Not exempted, but not
   detected either. Pre-existing; closing it needs a document-wide reader inventory of affected bones.
2. **Non-constraint operators.** Only the known constraint types are classified as followers. Motion of an outside
   bone caused any other way is not refused before writing, but P7 has no exemption for it, so it yields
   committed-unverified. Unknown operator types already refuse (`J.unresolved_operator_in_the_document_refuses`).
3. **Props constrained to a posed bone now refuse** when the constraint is in this animation set or the shot (no
   qualified contract for the prop's result). This is the intended consequence of finding 2.

## 5. Status

Offline correction complete; ready for Astra's correction review. Native qualification (implementation record
sections 8–9) remains separately unauthorized; QUATINTERP and Heavy compatibility are not dependencies.
