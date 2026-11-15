# F-01 Q1: PS-2 Body Preset and Undo diagnostic — offline preparation

**Date:** 2026-11-15. **Authority:** Blueprint R4 section 6 (6.3); "F-01 — Q1: PS-2 Body Preset and Undo Diagnostic
Preparation" (offline preparation approved). **Status:** kit prepared and tested offline; not installed, not run.
The native trial needs the Owner's separate authorization.

## 1. Preserved facts (from PS-2 run 1 and R4 section 6; not reinterpreted)

- Body operations 8 (`Body`) and 18 (`PS2 Dup Body`) committed, then ended `committed-unverified`, reason
  `bone-scales`, at the deferred full-map check (`prod_bs_index_verify_saved`).
- Their changed existing scales passed CPM's precommit authored check (`prod_bs_authored_matches`) before
  `FinishUndo`; reaching commit is that evidence, not a dump of the values.
- Happy (operation 9) had no planned scale writes (zero existing or created scale changes logged).
- Body already called its existing `same_time_refresh` (`SetHeadTimeInSeconds` + `ProcessEvents`) before the
  deferred check.
- In the duplicate check the peer `krystal20201` kept its control and model digests through Apply and Undo; the
  target `Krystal`'s control digest returned to its pre-Apply value after Undo, its model-state digest did not.
- The PS-2 observer stored digests (bone transforms and flex weights rounded to 6 decimals, controls), not values;
  no raw per-field evidence exists. The PS-2 evidence folder is unchanged by this preparation.

## 2. What the existing code says the failure can be

`prod_bs_index_verify_saved(record, snapshot)` (unchanged since PS-2: all 107 relevant definitions are byte-identical
between PS-2's `84cd996c…` and the candidate `615acf0c…`) returns False at the first saved bone that fails one of four
predicates: an `IMPLICIT_NEUTRAL` bone whose saved value is not 1; a classification other than
`CHANNEL_DRIVEN_SCALE`; `prod_bs_static_scale_trace` false (the static rule includes `physical_matches_lerp`, the
evaluated physical scale equalling the expression's result, so stale evaluation can surface here); or the physical
scale not within `EPSILON` (1e-5) of the saved value. It logs none of these. The diagnostic records all four for every
saved bone.

## 3. The kit

`real_sfm_qualification/f01_q1_ps2_diagnostic/` (LF-pinned in `.gitattributes`):

| File | Role |
|---|---|
| `PROCEDURE.md` | the operator procedure, PASS/STOP criteria and restoration |
| `q1.template.json` | identities and pins |
| `observer/F01_Q1_Observe.py` (`81ab0bbc…`) | in-process recording hooks and raw captures (Python 2.7, in SFM) |
| `tools/q1_tool.py` | build, pre, install, seed, check, library, collect-logs, restore, analyze (reuses the UA-1/K2/S3 tooling) |
| `tools/q1_analyze.py` | evidence completeness and the descriptive analysis |
| `tests/test_q1.py`, `tests/test_q1_observer.py` | offline tests |

**Identities:** candidate `615acf0c…` (`fda1fb3`); qualification build `849d0ed4…` (line 42220 only); registries
`f445d5ef…` / `22dcd159…`; session = R2 fixture `259ea8a6…` (PS-2's session source); `Body` `cd31c7f1…` and `Happy`
`bc4e8585…` (verified unchanged in the library since PS-2's backup; read only); `PS2 Dup Body` `29629f1b…` (PS-2's own
record, from its evidence, seeded and removed at restore); published CPM `ccbed9d7…`.

**Instrumentation (read-only with respect to the scene, the library and CPM's decisions):** four CPM functions are
wrapped in the SFM process for the session (installed by the BASE capture, removed by DUP-UNDO). Each wrapper calls the
original with the same arguments and returns its result, or re-raises its exception with the original traceback,
unchanged:
- `prod_apply`: the operation and its outcome;
- `prod_bs_authored_matches`: CPM's precommit snapshot, desired value and result per changed scale;
- `same_time_refresh`: the complete saved-scale map of the operation's character (Body's record) immediately before
  and after the existing refresh, through CPM's own `prod_bs_index_snapshot`, `prod_bs_index_trace` and
  `prod_bs_classify_static_scale`;
- `prod_bs_index_verify_saved`: after CPM's own check returns, the complete map on the same snapshot, and whether it
  reproduces CPM's result.
Captures record the raw, unrounded fields of every animation set in the shot (controls, bone position, orientation and
scale, flex weights, model visibility, skin, body group, child visibility), the session and Undo history, the selected
instance, and the settled complete map against `Body` and `PS2 Dup Body`.

**Sequence (one SFM process):** BASE → Apply `Body` → BODY → (only if BODY's settled map fails) Apply `Happy` → HAPPY →
create instance B (same model, unchanged) → DUP-BEFORE → Apply `PS2 Dup Body` to A → DUP-APPLY → one Undo → DUP-UNDO.
No visibility edits.

## 4. Offline tests

| Suite | Result |
|---|---|
| `test_q1_observer.py` (Python 2.7.5, the candidate's real functions through the R15 harness, pinned to `fda1fb3`) | **19/19**: the observer's map equals CPM's own `prod_bs_index_verify_saved` in every failure kind and the all-pass case (real classification and `close_enough`), including where CPM raises; wrappers return results and re-raise exceptions unchanged with the original traceback, record events in order, are idempotent and uninstall to the exact originals |
| `test_q1.py` (Python 3.10.6) | **10/10**: build derivation `849d0ed4…` and refusals; pre refuses a changed preset; seed copies only the pinned record and refuses twice; complete synthetic evidence → EVIDENCE COMPLETE with the delayed-evaluation, persistent (Happy) and not-reproduced readings; field-level duplicate differences (target vs unchanged peer); eleven incomplete-evidence cases each failing their own check (missing capture, wrong identity, missing fields, hooks left installed, inconsistent deferred map, unreadable boundary map, missing required Happy, visibility edit, wrong history, unexpected library change, failed restoration, saved session) |

## 5. Observational limitations

1. The boundary maps make the same read-only DataModel reads CPM's verification makes, in the same Python call and
   with no event processing; that an attribute read cannot itself advance operator evaluation is assumed, not proven.
   The refresh-before map adds such reads inside CPM's operation (after commit, before the refresh). The analysis
   checks that the deferred map reproduces CPM's own result and log outcome; a disagreement makes the evidence
   incomplete instead of being interpreted.
2. "Settled" is the state when the Owner submits the capture after the operation's message, i.e. after at least one
   ordinary event turn, not exactly one.
3. The raw captures hold control values, bone transforms, flex weights and visibility, and the scale graphs' authored
   inputs through the traces; they do not dump every flex channel's keys or every operator graph. A remaining
   difference in a flex weight is located to the field, not traced to its graph.
4. The duplicate step applies PS-2's own `PS2 Dup Body` record to A with an unchanged B; PS-2 had edited and saved B
   first. Whether B's edit mattered is outside this reproduction.
5. One reproduction on one machine; the Happy step runs only if the settled Body map fails.

## 6. PASS/STOP and restoration

PASS of the diagnostic = `EVIDENCE COMPLETE` from `q1_analyze` (procedure section "Evidence, restoration and
analysis"); otherwise STOP/incomplete with the failed checks named. The analysis then names the failing bones,
predicates and values at each boundary and the field-level Undo differences; the cause decision and any correction
remain for review (R4 section 6.3). Restoration is mandatory after completion or STOP: the library is put back exactly
(files and folders), the published CPM reinstalled, both registries removed, all four inventories equal their
baselines, the session unchanged.

## 7. Owner actions in SFM (summary; exact text in PROCEDURE.md)

Open the disposable session at shot15 0.2083 s; open CPM, select Krystal; submit the setup line; capture BASE; apply
`Body`, capture BODY; only if told by BODY's line, apply `Happy`, capture HAPPY; create a second Krystal animation set
for the same model and change nothing; refresh, select the original Krystal, capture DUP-BEFORE; apply `PS2 Dup Body`,
capture DUP-APPLY; Ctrl+Z once, capture DUP-UNDO; exit without saving; report the messages and what was visible.
