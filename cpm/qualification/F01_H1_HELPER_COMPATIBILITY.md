# F-01 H1 — Generic procedural-helper compatibility (offline)

**Date:** 2026-11-17. **Authority:** Blueprint R4 sections 7, 8, 9 and 12 H; "F-01 H1 — Generic Procedural-Helper
Compatibility" (bounded implementation and offline testing). **Base:** `aec7e2b` (CPM `48ff01a3…`).
**Status: implemented and tested offline; Designer-accepted for native qualification preparation ("F-01 H1 —
Offline Closure and Native Readiness"); committed locally; not installed, not natively run, not promoted.**

## 1. Identities

| Item | Value |
|---|---|
| Candidate CPM | `3d31e72141a50fca3a9b10f5ae0970af3b7f2253a66f4f6f8a03e38c28e29d1e` |
| Exact diff | `F01_H1_HELPER_COMPATIBILITY.diff` (`git diff aec7e2b -- cpm/app/…`): 173 lines added, 25 removed |
| New suite | `cpm/convergence/tests/test_cpm_app_f01_helper.py` `2d021604…` |
| Allow-list | `test_cpm_app_canonical_route.py` `3fbdf2bb…` (`F01_H1_NEW_TOP`) |
| Kit test correction | `real_sfm_qualification/f01_ot1_integration_smoke/tests/test_smoke.py` `8f5c5ef9…` |

## 2. The rule (mechanism and relationships; no names, no model identity)

A control-less bone (`prod_scope_classify` class `carried-candidate`: one source-less mode-3 channel per attribute, the
bone's only writers, no constraint) is admitted as an **engine helper** in a **Full body** only when:

1. the live game model's studio header (`CDmeGameModel.GetStudioHdr()`, the accessors read natively by NQ-S6 and
   NQ-03) matches the scene skeleton exactly by index, name and parent;
2. it declares `STUDIO_PROC_QUATINTERP` with `BONE_ALWAYS_PROCEDURAL` and none of `BONE_PHYSICALLY_SIMULATED`,
   `BONE_PHYSICS_PROCEDURAL`, `BONE_SCREEN_ALIGN_SPHERE/CYLINDER` (constant values read from `vs.studio`);
3. it is a leaf in the scene and in the header, under a direct-FK parent that is posed;
4. no local attachment and no bone flex driver uses it.

Unreadable or inconsistent evidence admits nothing (the earlier `carried-unsupported` refusal stands). JIGGLE,
physics and every other procedure are not admitted. Selected parts is unchanged.

## 3. What an admitted helper gets

- **Never written:** outside W and A; no saved value, offset or oracle; never classified constant (no carried rule).
- **Protected:** its channels, logs, keys, defaults and configuration are in the existing exact authored-state
  comparison (P2, P5, P7); its scale, parent membership, identity and writer authority are checked as for every bone;
  a competing writer, a constraint driving it, or a channel/constraint carrying it into protected state refuses.
- **Follows:** the dependency tracer admits it only through the hierarchy or its own transform (returned with the
  confined followers); P7 does not require its rendered transform (the unavailable procedural output).
- **Record:** the coverage ledger marks it `engine-helper` (no new field or record version; older strict readers
  refuse the unknown role instead of misapplying it). The validator accepts the role for Full body only, as a leaf
  under a posed bone. Apply requires the destination to admit exactly the same helpers (ledger equality).
- **Rechecked:** the header is read again at P2 (through the compiled scope) and at P7; a changed declaration gives a
  refusal before Undo, or `committed-unverified`.
- **Save note:** "Helper bones that SFM moves automatically follow the pose and may look slightly different."

## 4. Offline results

**`test_cpm_app_f01_helper.py`: 78/78 on Python 2.7.5 and 3.10.6** (native MC-01 Heavy fixture with a native-shaped
header): admission of exactly `hlp_forearm_L/R`; refusal per criterion and fail-closed evidence; a renamed rig on
another model admitted, and JIGGLE-declared helpers not; read-only Save and the record's ledger; Apply verified with
only planned channels written, the destination's own helper authoring untouched, Undo/Redo exact, true no-op, verified
Abort, production mode; concrete consumers refused (channel into a control, constraints from or onto the helper,
competing writer) and an external prop below the helper admitted; P2 and P7 changes; older-reader and tampered-record
refusals; a pre-H1 strict v3 record (the native EF-1 Engineer Full body record) still validates; with the v3 rule
not qualified, production refuses the Heavy inventory and the saved helper pose (`not-qualified`, nothing written)
while the qualification build still applies it. With the rule disabled the suite fails 20 checks and cannot proceed past Save; without the tracer allowance
Save and Apply are refused.

**Regressions (both interpreters), unchanged against the recorded baseline:** scoped 486/486; body 257/257; pose core
255, library 87, live 104, integration 218; ordering trial 75/75; M-06 334/334 and 179/179; operation context
108/108; clothing fit 95/95; compat projection 196/196; Poses page 123, scoped page 17, empty states 15 (2.7.5);
pre-existing: M-05 114/115 (A9), canonical route 84/85 with the same 11 unlisted names (compare 2/3), convergence
gates 147/148, R14 17/18 and 14/15, R15 340/345 and 183/188, authority cleanup 42/46, bounded logging 71/72; setup- or
reference-gated suites as before. F-01 kit tests all pass after one test-only correction: the OT1S kit test read the
working-tree CPM (41/43); it now reads the integrated candidate `48ff01a3…` as the raw Git blob from `d719bb0`
(43/43), as the OT1, K2 and EF-1 kit tests do.

## 5. Final offline confirmations (Designer closure)

| Requirement | Evidence |
|---|---|
| Reusable, no name or model conditions | the CPM diff contains no bone, character or model name; a renamed rig on another model path is admitted (B) |
| No independent promotion, no gate bypass | every helper path runs after `prod_scope_row` / `prod_scope_authorize` (`prod_scope_rule_usable`); section H; Krystal's v2 mapping and `rig-driven` refusal untouched (scoped 486/486, body 257/257) |
| Strict v3 records compatible; older readers refuse safely | G (EF-1 record validates; the role is refused by the pre-H1 enum as `invalid-file`) |
| Minor engine-driven helper movement permitted | helpers are followers with no rendered-transform obligation (D) |
| Dangerous dependencies, wrong-target writes, unverified recovery still refuse | E, F, D (verified Abort), unchanged transaction suites |

## 6. Native readiness and open points

- **First native use:** attachments and bone flex drivers were read natively from the MDL-cache header (NQ-03), not
  yet from the game model's header (same `studiohdr_t` type). Unreadable would refuse safely (Heavy stays refused).
- **Visual result unproven:** offline fakes cannot show SFM's QUATINTERP output; the native check must judge useful
  posture and the absence of severe forearm distortion.
- **Availability:** the rule runs under the qualified `direct_fk_v1`, so in this candidate it applies in production
  mode too. It is not promoted; promotion should follow the native check.
- **Proposed native check (Owner-operated, separately authorized; reuse the EF-1/PS-2 tooling, no new framework):**
  Heavy (MC-01 session copy): Save a visibly distinct Full body (forearms twisted, body posture changed), reopen,
  Apply to a disposable compatible Heavy with a same-model peer; check planned keys only, helper channels unchanged,
  useful appearance without severe distortion, peer unchanged, no-op, Undo/Redo. Transaction and recovery evidence is
  reused (unchanged code); no Engineer, Krystal or Body Preset rerun.
