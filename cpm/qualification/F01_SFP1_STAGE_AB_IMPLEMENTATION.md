# F-01 SFP-1 — Scoped Poses, Stages A/B: Offline Implementation Record

**Date:** 2026-11-08. **Status:** offline implementation of SFP-1 stages A and B complete; ready for implementation
review. **Not natively qualified.** Nothing was installed, launched, pushed, merged, signed, packaged or released, and
no experimental capability is enabled in the production build.

## 1. Authority and identities

| Item | Identity |
|---|---|
| Blueprint | `cpm/qualification/F01_SCOPED_POSE_BLUEPRINT_R3_20261108.md`, Revision 3, SHA-256 `e4cfa882…` (byte-exact, commit `5d7efaa`) |
| Reference checkpoint | `6d6e9e6ce15cfc33d2544d74edb97482fc207d79` (`feature/f01-pose-library`) |
| CPM before | `f6098b3a…` |
| CPM candidate | `54e2028d…` |
| Implementation commit | `abe58bb` |
| Test fixtures | `fixtures/f01_scoped/mc01_heavy_norig.json` `eb240d2e…` (from MC-01 `f94185a8…`), `mc02_heavy_rig.json` `816c7336…` (from MC-02 `569a7222…`) |

R3 governs new scoped-pose functionality. Version 1 (left arm) and version 2 (registry full body) records keep their
qualified paths unchanged.

## 2. What was implemented

### Stage A — offline core (one appended block, `F-01 Pose Library scoped poses, SFP-1`)

- **Version 3 record** (R3 6) in the existing envelope (`schema_version 3`, `record_kind preset`, `kind pose`,
  payload digest): `pose.version 3` with the closed sections `engine`, `source`, `scope`, `structure`, `values`,
  `oracle`. The reader rejects unknown fields, duplicate ids or memberships, contradictory ledgers, cycles, nonfinite
  or non-float32 values, missing evidence, unsupported or forged rule revisions, and internally inconsistent skeletal
  evidence (the saved locals must recompose to the saved boundary-relative transforms). Runtime handles and instance
  names are never stored. Large records use the existing 4 MiB bounded reader without the body registry; version 1
  keeps its 128 KiB limit.
- **`direct_fk_v1` discovery** (R3 3) without a profile: a bone is direct FK when one transform control's own position
  and orientation channels (Play mode, one layer, supported log types) are the only writers of its transform and no
  constraint slaves it. Other roles: constrained (rig-driven), carried candidate (one source-less channel per
  attribute), unresolved. A supported expression operator writing a bone's scale is a dependency, not a co-writer.
  The anatomical root is the single top-level bone directly under the model; anything else is ambiguous.
- **One scope compiler** (R3 4) for Full body and Selected parts producing W (written channels with their value
  source), A (posed, carried, preserved), D (ancestor chains, component boundaries, model placement, scales), P (the
  rest) and the coverage ledger. Selection is deduplicated, never widened (no parent is added to W) and never reduced
  (an unsupported requested bone refuses, naming it). Full body includes every bone by default (hair, tails, secondary
  anatomy, supported facial bones) and refuses, naming the parts, when anything would be omitted.
- **Exclusions and scope review** (R3 2.3, 4): control groups are organization only. A top-level group labelled Face
  only *highlights* candidates; exclusion needs the artist's explicit confirmation (`user_confirmed`) and still passes
  a technical boundary check (no cross-boundary write, no feedback into the body, no shared log, no excluded opaque
  bone with posed descendants). Excluded direct-FK bones stay in the composition as preserved branches.
- **Authority** (R3 3, 4): per attribute, document-wide: each written channel is the sole writer of its destination
  and owns its log and layer; its control's value is not driven; no outside channel writes an affected or dependency
  bone; no constraint drives an affected bone; no operator feeds the pose back into its dependencies. Unrelated
  writers elsewhere do not refuse. Unknown operator types anywhere in the document refuse (existing strict reader).
- **Frames and scale** (R3 5): one parent-first hierarchy over A; `P = P_parent + rotate(Q_parent, S_parent·p)`,
  `Q = Q_parent·q`, `S = S_parent·s`; external boundaries seeded from their observed destination frames and verified
  cumulative ancestor scale; posed bones from the saved, independently observed local orientation with the pinned
  destination offset; unselected bridges and carried descendants from their destination local state. Model/wrapper
  scale other than absent or 1 refuses.
- **Independent verification**: the source's observed transforms must compose (capture); the destination's observed
  transforms must compose (P1); the expected result must agree with the saved boundary-relative source observations
  wherever no bridge intervenes (P1); P7 reads the native skeleton again (selected locals, parent-first worlds,
  carried locals, unaffected branches, scales, placement, exact written positions, authored keys).
- **Compatibility** (R3 6): the same validated model (key and checksum), skeleton layout signature, resolved scope
  (posed, carried, preserved, ledger, root, boundaries), bone and boundary scales, and structural offsets within the
  provisional `0.00005` limit (the body root's translation is pose data in Full body and a pinned dependency in
  Selected parts). Different wrist or arm posture and different placement are allowed.
- **`constant_channel_carried_v1`** (R3 3.1): the complete read-only admission check (verified-null source, indices,
  one layer, strictly ordered identical float32 keys, curve/compression data, defaults, evaluation at t, local state,
  exclusive authority, extrapolation) and a procedural-state guard that reports **unsupported**. Disabled
  (`PROD_SCOPE_CARRIED_ENABLED = [False]`, `PROD_SCOPE_EXTRAPOLATION_QUALIFIED = [False]`). Carried elements never
  receive writes.
- **Planning and transaction** (R3 8): stage A's key planner (insert, update, exact key, hemisphere and sign-straddle
  safeguards), pinned offsets inserted with the destination's own value, one complete expected authored state, and the
  stage E P1–P7 contract unchanged: Motion Editor gate, P2 exact revalidation (including every affected and dependency
  bone's evaluated transform), one owned Undo, verified Abort, uncertain StartUndo/FinishUndo handling, one same-time
  refresh, deferred verification, committed-unverified without compensating Undo.
- **Generic authorization** (R3 6.1): `prod_scope_authorize` keeps the pinned selected-instance context, library
  identity, mode and lifecycle gates and uses the engine's own rule table; no Krystal registry entry or rig class is
  involved, and an imported record can neither enable a rule nor a capability.

### Stage B — lifecycle and UI

- **Save New** (Poses tab, unchanged layout and buttons): in a build where scoped poses are usable, the button opens
  the **Save Pose** dialog — name, **Full body** (default) / **Selected parts**, the compact grouped skeletal-control
  picker (groups resolved to bone controls by identity; unavailable controls shown with their reason; placement,
  gaze and flex never listed), the coverage line from the ledger, and **Review scope** when highlighted controls exist
  (required when an unsupported component is only a highlighted candidate). Full body of a character with a usable
  registry profile (Krystal) keeps its version 2 route; everything else saves version 3. The dialog's inventory is
  pinned and revalidated after it closes (a change in groups, bindings or classification is stale). Without scoped
  support (the production build) Save New is exactly the earlier flow.
- **Update Pose** recaptures a version 3 record with its frozen scope; the store refuses a changed scope or format.
- **Apply Pose** dispatches on the validated payload version (1 → stage D, 2 → stage E, 3 → scoped), with version 3
  authorized by `prod_scope_authorize`; the deferred turn dispatches scoped P7 the same way.
- **Library and page**: persistence, independent reload, Favorites, Rename, Delete/Trash and foreign-library
  protections reuse the existing store; the page state and Pose Info read parts through `prod_scope_parts` (no legacy
  `regions` assumption for v3); Pose Info lists the saved scope, exclusions with provenance, a compatibility note and
  the pose rule.
- Live SFM selection seeding is **not** implemented (optional; nothing reads the current selection).

### Shared-code changes outside the new block

`PROD_POSE_PART_NAMES` (adds Selected parts), `prod_pose_validate` and `prod_pose_parse` (version 3 dispatch and size
rule), `prod_pose_parts_phrase`, `prod_pose_ui_state` (the `selected_parts` part), `prod_pose_update` (scope and
format preservation for v3), `prod_pose_deferred_verify` (scoped dispatch); ProdWindow `apply_pose`, `save_pose`,
`update_pose`, `refresh_pose_view`, `pose_ui_state`, `open_pose_info`, and the new `prompt_pose_scope`. Legacy paths
reference no scoped name unless a version 3 record or the Save dialog is involved.

## 3. Production configuration (unchanged behaviour)

`PROD_POSE_REGISTRY_MODE = "production"`; `PROD_SCOPE_RULES = {direct_fk_v1: revision 1, experimental}`. In
production `prod_scope_rule_usable` is false, so Save New, Update and Apply of scoped poses are unavailable and the
Poses page behaves as before for every character. The qualification build (`"qualification"` mode) admits
`direct_fk_v1`; `constant_channel_carried_v1` stays disabled in both.

## 4. Offline results (`54e2028d…`)

Python 2.7.5 (SFM's interpreter, `-E -s`) and Python 3.10.6 (`-I`); full run compared row by row with the same
run at the reference checkpoint `6d6e9e6`.

| Suite | Before (`f6098b3a`) | Candidate |
|---|---|---|
| **`test_cpm_app_f01_scoped.py`** (new: R3 section 11 matrix) | — | **218/218** both |
| **`test_cpm_app_f01_scoped_page.py`** (new: the real Qt Save dialog, 2.7.5 only) | — | **12/12** |
| `test_cpm_app_f01_body.py` | 246/246 | 246/246 both (harness adaptation, section 6) |
| `test_cpm_app_f01_pose_core.py` / `_library.py` / `_integration.py` / `_live.py` | 255 / 87 / 204 / 104 | unchanged, both |
| `test_cpm_app_f01_pose_page.py` (2.7.5) | 118/118 | 118/118 |
| M-05 115, M-06 179 and 334, clothing-fit 95, operation-context 108, empty-states 15 (2.7.5) | PASS | unchanged |
| Historical FAIL rows (authority-cleanup 4, bounded-logging real-log-folder guard, canonical-route `added_top_level_is_bounded`, r14 `normalizer_pinned`, r15 five `forbidden.unchanged.*`, convergence-gates 7, authority-adapter fixture) | FAIL | identical |
| Environment-only exits (PySide absent in 3.10; suites needing a pinned `--reference`; sidecar mismatch) | — | identical |

The new suite covers, on four structures (Krystal shot15/shot13, Heavy MC-01 without a rig, Heavy MC-02 with
`rig_biped_simple`, analytic skeletons): records (round-trip, digest, unknown/forged rule, unknown version, unknown
field, missing evidence, duplicates, contradictions, cycles, NaN, non-float32, bounds, no runtime identity, v1
reader); coverage (survey censuses reproduced without a profile, hair/tail included, unsupported tail never omitted,
Face group never authorizes omission); exclusion boundaries (review required, the same solver requested refuses,
confirmed exclusion with one-way head follow verifies, posed descendant of an opaque exclusion, shared log,
cross-boundary writer from an imported record); frames (fingers under a differently placed and rotated wrist,
upper arm + hand with an unselected forearm, carried descendants, unrelated branches) against an independent matrix
evaluator; three wrong-planner counterexamples refused before any write, and a self-consistent wrong expectation never
verified; scale (cumulative ancestor scale, own vs parent scale, mismatch, wrapper scale, drift at P2 and P7, a scale
expression as a dependency); carried constants (every R3 3.1 refusal, a synthetic positive, no helper writes,
incompatible helper state); full body (root translation vs preserved placement, ambiguous root, offset within/beyond
the limit, one-ULP drift, update in place, scope change refused); authority (competing writer, shared log, external
constraint, unknown operator, writers introduced at P2 and P7, unrelated writers allowed); key planning (insert,
update, exact keys, missing-key non-no-op, sign straddle) and sequential composition (full body then fingers, Undo/Redo
through both baselines); transactions (disabled Undo, StartUndo before/after, late write with verified Abort, failed
Abort, FinishUndo uncertainty with an older identical label, stale callback, after-commit uncertainty, replaced
instance, stale record); the real window lifecycle, dispatch and the dialog copy (section 5).

## 5. Evidence that the real CPM routes reach version 3

`test_cpm_app_f01_scoped.py` section N runs the real `ProdWindow.save_pose`, `apply_pose`, `update_pose` and
`pose_guard` (extracted verbatim) against a fake window seam: on the unrigged Heavy (no registry entry) Save New
through the dialog creates a version 3 record, Apply runs the scoped transaction (one StartUndo/FinishUndo), the
deferred turn verifies it, Update recaptures it in place with the same scope; one envelope with payload versions 1, 2
and 3 dispatches to `prod_pose_apply`, `prod_body_apply` and `prod_scope_apply`; the production build refuses the
experimental rule and leaves the earlier Save New unchanged; a failed recovery locks out the next scoped operation
process-wide. `test_cpm_app_f01_scoped_page.py` drives the real Qt Save dialog under SFM's PySide.

## 6. Evidence that version 1 and 2 behaviour is intact

All earlier F-01 suites pass unchanged in their assertions (core 255, library 87, integration 204, live 104, Poses page
118, full body 246) on both interpreters; M-05, M-06, clothing-fit, operation-context and empty-states are unchanged.
Two harness adaptations, no assertion changed: `test_cpm_app_f01_body.py` now also loads the scoped block and its fake
window answers the qualification build's new Save dialog with Full body (the v2 route it already tested);
`test_cpm_app_canonical_route.py` lists the SFP-1 additions in its derivation bounds (its one historical FAIL,
`PROD_EMPTY_STATE_GUIDANCE` and `prod_model_candidates` unlisted, is unchanged).

## 7. Limitations

- Scoped poses are unqualified natively and disabled in production.
- Full body v3 needs a fully supported body. Every surveyed model has two control-less bones (Krystal's
  `bip_lowerArm_l/r_twist2`, the Heavy's `hlp_forearm_L/R`), so **no surveyed model can save a v3 Full body** until
  `constant_channel_carried_v1` is qualified; Krystal's Full body keeps its version 2 route. Selected parts work on all
  three structures.
- Rigged bodies (constraints, IK) are refused for Full body v3 (`rig-driven`); bone-parented rig handles, IK target
  application, reverse foot, jiggle and scalar controls are not writable capabilities (R3 9).
- Facial semantics are not inferred: the Face group only highlights; skeletal faces are included unless the artist
  excludes them.
- No current-selection seeding; no Apply-time subset; no mirroring, blending or retargeting.
- The coverage summary names a group only when the selection equals that group's eligible controls.

## 8. Native qualification dependencies (none claimed)

| Id | Dependency | Offline handling |
|---|---|---|
| NQ-S1 | SFM's absolute transforms follow `P = P_parent + R(S_parent·p)` with nonunit and nested ancestor scale at a partial boundary | composition checked against observed transforms at capture and P1; refuses on disagreement |
| NQ-S2 | Exact-time key insertion and update on newly scoped channels (finger, thumb, root position) and their Undo/Redo | stage D/E write primitives reused unchanged |
| NQ-S3 | Bit-stable re-evaluation between P1 and P2 (every affected and dependency bone compared exactly) | P2 refuses on any difference |
| NQ-S4 | Root placement: the Heavy's `rootTransform` places the model; the body root's translation is model-relative | Full body v3 positive not reachable on surveyed models (NQ-S6) |
| NQ-S5 | Fresh-instance identity: a second instance of the same model has the same layout signature and resolved scope | compatibility refuses otherwise |
| NQ-S6 | Procedural-state guard and constant-log extrapolation (`evaluateProceduralBones` reads `true` on MC-01/02/03; its meaning is unestablished) | `constant_channel_carried_v1` disabled; the guard reports unsupported |
| NQ-S7 | The provisional `0.00005` structural-offset allowance for `direct_fk_v1` | refuses beyond it |
| NQ-S8 | Control-group reader (`rootControlGroup`, `children`, `controls`) inside the operation | observed read-only in MC-01..03; organization only |
| NQ-S9 | The Save dialog inside SFM: appearance (fonts, sizing, tri-state groups) and lifetime (deferred deletion by SFM's event loop; offline, six dialogs left undeleted until interpreter exit crashed PySide at shutdown) | Qt 4.8 offline only; the test processes deletions after each dialog |

## 9. Proposed short SFM acceptance procedure (separate authorization required)

Qualification build (`PROD_POSE_REGISTRY_MODE = "qualification"`) in a disposable test installation with the
existing pre/post inventory and restoration safeguards; disposable sessions only.

1. **Fingers, unrigged model.** Two TF2 Heavy instances placed differently. Pose heavy1's left fingers; Save New →
   Selected parts → LeftFingers. Restart SFM; on heavy2 turn the wrist and raise the arm; Apply. Verify the grip,
   unchanged wrist/arm keys, P7 verified, a repeat no-op, Undo/Redo. (NQ-S1, S2, S3, S5, S8, S9)
2. **Fingers, rigged model.** Krystal shot15 → Save left fingers; Apply in shot13 with a differently posed arm rig.
   Then Apply Krystal's version 2 Full body followed by the finger pose: sequential composition, Undo/Redo through
   both baselines, one Undo entry each. (NQ-S1, S2)
3. **Bridge and scale.** On the Heavy select `bip_index_0_L` and `bip_index_2_L` (index 1 unselected); on Krystal
   select `jaw` (under the `bip_head` scale expression). Verify native local/absolute results and unchanged bridge
   inputs. (NQ-S1)
4. **Refusals.** Full body on the Heavy refuses naming the control-less helpers; Full body v3 on the rigged Heavy
   refuses as rig-driven; nothing is written.
5. **Recovery.** One injected owned-write failure (`PROD_POSE_QUAL_FAULT = "after-writes"`): verified Abort, nothing
   changed.
6. Restore the installation; preserve sessions and evidence. Stop on wrong-instance mutation, uncertain authority,
   unexpected scope expansion, unverifiable recovery or source/oracle disagreement.

A native Full body v3 positive and the carried-constant class need NQ-S6 first (a read-only guard observation on the
Heavy), or a fully direct-FK model; this is a bounded follow-up, not a survey.

## 10. Readiness

Ready for implementation review of the offline stages A/B. Native qualification, production enablement and release
remain separately unauthorized.
