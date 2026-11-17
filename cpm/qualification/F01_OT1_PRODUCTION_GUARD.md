# F-01 OT1 — Production reference guard integration (offline)

**Date:** 2026-11-17. **Authority:** Astra's final ACCEPT WITH CONDITIONS ruling, accepted by the Designer in
"F-01 — OT1 Production Guard Integration" (offline implementation and testing only). **Base:** `85649f6` (qualified
OT1 candidate `0cea8acd…`). Related: `F01_OT1_ORDERING_TRIAL_PREPARATION.md`, `F01_OT1_NATIVE_RESULTS.md`.

**Status: implemented and qualified offline; not installed, not natively run, not promoted.** The working ordering
correction (operate the bound expression inside the owned Body transaction and verify its result before commit; keep
the postcommit physical verification) is unchanged.

## 1. Identities

| Item | Value |
|---|---|
| Qualified OT1 candidate (base) | `0cea8acdcf934cc69590356ba7c237c963728e118fa67e298e641fd56077fa3c` |
| **Integrated candidate CPM** | **`48ff01a3b328f94de0f267d910a10e745b0cdc2b22f550ef3783c03394abcefa`** |
| Exact diff | `cpm/qualification/F01_OT1_PRODUCTION_GUARD.diff` (`git diff 85649f6 -- cpm/app/…`, `a1d097d6…`): 171 lines added, 71 removed |
| Its one-line qualification derivation (if ever needed) | `10328efe…` (`PROD_POSE_REGISTRY_MODE`, line 42546) |
| Tests | `test_cpm_app_f01_ordering_trial.py` `a1cc7e48…`; harness `test_cpm_app_m05_static_scale.py` `d4513314…`; `test_cpm_app_m06_static_play_flex.py` `8af61952…`; route allow-list `test_cpm_app_canonical_route.py` |

## 2. What changed, and where relative to `StartUndo`

| Order in `prod_apply` (Body) | Safeguard |
|---|---|
| unchanged | authorization, live bindings, selected-instance pair checks (bindings and snapshot), plan (`prod_bs_index_build_plan`: the admitted binding, one output from `expression.result` to the bone's scale, one input, `lerp(value,lo,hi)`, coherent), the no-op return |
| **new, after the no-op return and before `StartUndo`** | for every changed, existing, admitted mode-3 scale: `prod_bs_expression_reference_guard` — the expression's direct DataModel references, enumerated read only through `vs.g_pDataModel.FirstAttributeReferencingElement` / `GetAttributeFromIterator` / `NextAttributeReferencingElement` until the token equals `vs.DMATTRIBUTE_REFERENCE_ITERATOR_INVALID` (explicit comparison; repeated token, unreadable attribute, owner, name or handle, API exception or more than 4096 tokens refuse), must be exactly three, each matched once by live element identity (`same_dme`): the selected animation set's `operators`, the planned input channel's `toElement`, the planned output channel's `fromElement`. Missing, additional, ambiguous or unreadable → `RuntimeError` before Undo opens or any character data is written. |
| `StartUndo` | unchanged |
| unchanged | created graphs; per changed existing scale: one-key check, key and source write, input-channel `Operate()`, authored check |
| **inside `prod_bs_operate_bound_expression`, immediately before `Operate()`** (mode-3 only) | existing expression type/text and endpoint checks; **new** `prod_bs_revalidate_operation`: the operation context is still current (`prod_validate_context_token`) and, with a pinned instance, the freshly resolved selected animation set (`prod_resolve_instance`) is the binding's own (`prod_strict_identity`); **the reference guard again**; existing identity, input-log/layer, limit checks; then `Operate()` and the result/authored check |
| unchanged | flex writes, precommit checks, `FinishUndo`, same-time refresh, deferred physical verification (`committed-verified` only on physical evidence; otherwise `committed-unverified`), verified Abort on any exception inside the transaction |

**Removed:** `prod_bs_expression_channels`, the shot-wide channel-track scan. It refused a valid Apply whenever any
unrelated channel anywhere in the shot's channels track was unreadable; the direct-reference requirement replaces it
(it sees every channel or non-channel element referring to the expression, whether in a clip or not). Checks on the
actual expression, its planned channels and their endpoints are unchanged. `vsUtils` is not imported and global
element equality and hashing are untouched.

The guard and correction are reachable only from `prod_apply`'s Body existing-scale path and
`prod_bs_write_existing_scale` (trial suite N6). Not changed: no-op behaviour, mode-1 scales, created graphs,
Expression Presets, Pose Apply, record formats, Undo/Redo semantics, context-change refusals, `committed-unverified`.

## 3. Offline qualification (production dispatch, no observer)

The trial suite drives `prod_apply`, the window guard and the deferred callback with production functions extracted
verbatim; the fake DataModel derives each element's direct references from the fake scene's own attribute links (an
attribute holding the element, or a list containing it), with injectable iterator faults.

**`test_cpm_app_f01_ordering_trial.py`: 75/75 on SFM Python 2.7.5 and 3.10.6.** Added or revised for the guard:
- valid three-reference graphs apply and verify (P, N, C sections, unchanged);
- refused **before Undo opens** (no `StartUndo`, no write, nothing operated, scene unchanged): a second reader in the
  same clip, a reader or writer in another set's clip, an **off-track reader in no clip**, a **non-channel reference**
  (connection operator), the expression in a second `operators` array; an **incomplete enumeration** (iterator
  exception), a **repeated token**, an **unreadable reference**;
- an **unrelated unreadable channel** elsewhere in the shot **does not block** a valid Apply (verified);
- each changed mode-3 expression is checked before `StartUndo` and again inside the transaction just before
  `Operate()`;
- **binding changed after the preflight** (an extra reader or a non-channel reference added once the transaction
  opens; output re-pointed or re-targeted; expression text or limits changed; logs replaced) and an **operation
  context changed after the preflight** → refused before `Operate()` with **verified Abort**;
- late operator failures (raise, partial result, no-op, wrong value, disturbed input; a later flex failure) →
  verified Abort; unprovable Abort → recovery uncertainty;
- a **stale or wrong physical scale never reports verified success**;
- mode-1, created-graph, FLEX-only, no-op and Expression-preset Applies operate nothing and match the baseline.
With the guard disabled the identity section passes 15 of 27 (every before-Undo and late-reference case fails).

**Harness alignment (test code only):** the M-05 fakes gain the three iterator primitives on `FakeDataModel`, the
sentinel on the fake `vs`, `GetOwner`/`GetName` on fake attributes, and the animation set's live `operators` list
(M-05 stays 114/115, the same pre-existing A9 failure). The M-06 flex harness's synthetic scene listed no operators on
its animation set; it now lists its scale expression there, as SFM does (the OT1 native preflight found exactly that
reference). Canonical route: `F01_OT1_NEW_TOP` updated (the scan removed; the guard names added); 84/85, compare 2/3,
the same 11 pre-existing unlisted names; changed tops equal the expected set.

**Regressions (same runner as before, both interpreters), unchanged against the qualified candidate:** Body 257/257;
Pose core 255, library 87, live 104, integration 218; Scoped 486; M-06 instance resolution 179/179; M-06 static-play
flex 334/334; operation context 108/108, compare 3/3; clothing fit 95/95; compat v1 projection 196/196; Poses page
123, scoped page 17, empty states 15 (2.7.5); M-05 114/115; canonical route 84/85; convergence gates 147/148; R14
17/18 and 14/15; R15 340/345 and 183/188; authority cleanup 42/46; bounded logging 71/72 (environment guard);
authority adapter and the logging-cleanup/UI-polish suites as before (setup / `--reference` required). No new failure.

## 4. Behaviour changed beyond the intended Body scale path

None intended or observed. The only user-visible differences are on that path: a Body Apply whose admitted mode-3
scale expression has other direct references is now refused before Undo with "Bone … scale expression is shared or
ambiguous." (previously refused inside the transaction with verified Abort, or not at all for references outside the
channels track); an unrelated unreadable channel no longer refuses it.

## 5. Outstanding risks and incompatibilities

1. **Not natively qualified.** OT1's native evidence is for `0cea8acd…`; the guard changes when and how the
   expression's references are checked. The integrated candidate needs its own native confirmation before promotion.
2. **Real-rig reference sets.** Krystal's expressions had exactly three references natively. Other rigs or scenes may
   list the expression elsewhere (a second operators list, presets, rig or script elements); those Body Applies would
   now be refused before Undo. That is the approved conservative behaviour, but its frequency is unknown.
3. **The OT1 native kit is candidate-specific:** its observer's channel-scan preflight calls
   `prod_bs_expression_channels`, which no longer exists; it remains the record for `0cea8acd…` and would need
   adaptation to observe this candidate.
4. Iterator token type and sentinel value are known only from the native run (sentinel `0`); the guard compares
   explicitly and records nothing, so an unexpected API change would refuse rather than pass.
5. The physical-advance mechanism at the refresh remains observed, not explained; Undo exactness was measured on one
   fixture.

## 6. Recommendation

The bounded integration is ready for Designer and Owner review as a production-integration candidate. Approval for
production should be conditional on a native confirmation of this integrated candidate (Apply, Undo, Redo, final
Undo, verified Abort, peer isolation, and the before-Undo refusal), separately authorized, and on Astra's review of
risk 2. No installation, signing, push, merge or release has been done.

## 7. Designer acceptance, compatibility policy and native smoke preparation (2026-11-17)

**Designer disposition ("F-01 — OT1 Integrated Candidate: Final Qualification"):** ACCEPT WITH CONDITIONS. The
production reference guard and its offline results are accepted; Astra's final technical condition is implemented; no
further Astra consultation is required solely to investigate other rigs.

**Compatibility policy (recorded):** Body Apply conservatively **refuses** a changed, existing, mode-3 scale whose
expression has any direct DataModel reference beyond the three planned ones (the selected set's `operators`, the
planned input's `toElement`, the planned output's `fromElement`), or whose references cannot be read completely. The
refusal happens before Undo opens, with "Bone … scale expression is shared or ambiguous." (or "… references are
unreadable."). This is Astra's approved safety restriction; support for such rigs is not broadened in this milestone.

**Correction to section 3 ("Regressions … no new failure"):** that run covered the CPM convergence suites only. The
qualification-kit tests were not rerun at `d719bb0`; two OT1 kit tests read the working-tree CPM and failed against
the integrated candidate (`test_ot1.py` 97/99: the template's candidate pin and derived build are, correctly, those of
`0cea8acd…`; `test_ot1_observer.py` 20/22: its preflight cases extract the removed channel scan). Test-only fix, as
the K2 and EF-1 kit tests already do: both now read the qualified OT1 candidate as the raw Git blob from the OT1 kit
commit `2f4d877` (refusing unless it hashes to `0cea8acd…`): `test_ot1.py` `f4ce0f5c…` 99/99,
`test_ot1_observer.py` `687e2b5d…` 68/68 on 2.7.5 and 3.10.6. Every F-01 kit test now passes (EC-1, EF-1, S0, S3, K2,
model survey, NQ-03, NQ-S6, PS-2, Q1 14/14 and 21/21, SFP-1 NQ, UA-1 15/15 and 12/12, W2, OT1, OT1S). No product code
changed.

**Native smoke check prepared (not run):** `real_sfm_qualification/f01_ot1_integration_smoke/` — `PROCEDURE.md`,
`ot1s.template.json` `0f8b667c…` (integrated candidate `48ff01a3…`, qualification build `10328efe…`),
`observer/F01_OT1S_Observe.py` `04fb02e9…` (the pinned OT1 observer's recording hooks, plus a pass-through hook on
`prod_bs_expression_reference_guard`; the injector is never armed), `tools/smoke_tool.py` `3698aa0b…` (reuses the OT1,
UA-1, K2 and S3 tooling), `tools/smoke_analyze.py` `5148cc39…` (reuses the OT1 analyzer's comparisons; gates GUARD,
APPLY, UNDO, PEER, EVIDENCE), `tests/test_smoke.py` `fc9d61f2…` 43/43 (3.10.6), `tests/test_smoke_observer.py`
`0102f840…` 11/11 (2.7.5 and 3.10.6). One SFM session on the R2 fixture copy: BASE (peer created), Apply `Body`,
Undo, Redo, final Undo; no controlled failure and no shared-reference scene. The guard gate requires four accepted
guard calls, two before the transaction's first scale write and one immediately before each bone's write.
