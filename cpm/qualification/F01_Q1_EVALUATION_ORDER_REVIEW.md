# F-01 Q1 — Analyzer correction, evidence replay and evaluation-order review

**Date:** 2026-11-16. **Authority:** "F-01 Q1 — Offline Analyzer Correction and Evaluation-Order Review"; Astra's
adjudication (ACCEPT WITH CONDITIONS), supplied by the Owner; the Designer's assignment "F-01 — Implement Astra's
Qualification-Only Ordering Trial" (offline preparation only). **Base:** `9f0f7ff` (Q1 results).

This record holds three things: the kit correction and the separately named replay (offline; the original report is
unchanged), Astra's ruling as received, and where its conditions are carried out. The trial itself is prepared in
`F01_OT1_ORDERING_TRIAL_PREPARATION.md`. The corrected refresh-before interpretation is its own record:
`F01_Q1_RESULTS_ERRATUM_1.md`.

## 1. Kit correction and replay (Task A; offline)

`real_sfm_qualification/f01_q1_ps2_diagnostic/`:
- `tools/q1_analyze.py`: `fields.*` requires the identity of every animation set and the game-model fields only where a
  set has a game model (cameras and lights have none); the precommit check accepts CPM's documented pattern, three
  `prod_bs_authored_matches` calls per changed scale (pre-write through `prod_bs_evaluated_matches` on the original
  values, post-write in `prod_bs_write_existing_scale`, precommit), each checked by bone, value and result; a
  propagation table (expression input, expression result, physical scale at every boundary); the depth-truncation
  finding is driven by the evidence; `run(c, replay=True)` writes `Q1_REPORT_REPLAY.*` with exclusive create.
- `tools/q1_tool.py`: the `replay` command.
- `observer/F01_Q1_Observe.py`: events are written through a JSON round trip (`q1_events_payload`) instead of a second
  sanitization, so future boundary maps keep the output-log rows. New pin `f2eba1e0…` in `q1.template.json` and
  `PROCEDURE.md`. Run 1's evidence was captured with the previous observer and is not re-captured.
- Tests: `test_q1.py` 14/14 (Python 3.10.6), `test_q1_observer.py` 21/21 (SFM Python 2.7.5).

**Replay of run 1** (`E:\SFM_U0B_Scratch\f01-q1-ps2-diagnostic-r1\evidence`): `Q1_REPORT_REPLAY.json` `34bdc23c…`,
`.md` `1332865e…`: **EVIDENCE COMPLETE**, every evidence check PASS. The original `Q1_REPORT.json` (`c95da430…`,
EVIDENCE INCOMPLETE) and every evidence file are unchanged.

## 2. Astra's ruling (as received; structured summary)

The full adjudication text was supplied by the Owner in the conversation and is held by the Owner; this summary is
for traceability and does not replace it.

**Evidence verdict.** The committed `F01_Q1_RESULTS.md` refresh-before row is wrong: Body's refresh advanced the
expression results (head 1.13 → 1.33005, tail 0.80 → 1.00) while the physical scales stayed behind; Happy's refresh
advanced the physical scales. Six authored checks passed; of 154 bones only head and tail failed, at static
`evaluated`/`incoherent`. Duplicate Undo: only `bip_head.scale` differed (1.0 vs 1.33005); the input and expression
had returned; the peer matched; history showed "Redo Apply Body Preset". The original analyzer verdict stays
INCOMPLETE; the replay is COMPLETE. The settled captures show mode-3 output, empty log, `useDefaultValue=False`. The
`<depth>` rows and the hooks' extra reads leave the precise timing open.

**Root cause (as far as established).** `prod_bs_write_existing_scale` operates only the input channel;
`prod_bs_index_trace` resolves `expression.result` → bone transform scale. The mechanism (operator ordering, dirty
state, `SetHeadTimeInSeconds` + `ProcessEvents`) is not established.

**Recommended trial.** One call to the bound expression operator's `Operate()` after the input write, inside the owned
transaction, after the binding and input checks; read back `expression.result` against the expected mapped scale
before commit; keep the postcommit physical check. API: `IDmeOperator.Operate()`
(`sdktools/python/2.7/win32/Lib/site-packages/vs/datamodel.py:489`).

**Rejected alternatives.** Later verification; a second refresh (only as a separate controlled comparison if the trial
fails); treating the expression result or the empty log as the final scale; writing the physical scale directly or
keying the output; global re-evaluation. Retaining `committed-unverified` remains correct shipping behaviour.

**Safety conditions.** Reuse the instance token, unique writer, endpoint checks and expression identity; ensure no
conflicting or shared destination of the expression result; preserve the input key structure and the empty output log;
a failure inside the transaction goes to verified Abort; postcommit failures stay unverified with no automatic Undo.
Undo is a separate gate: if Undo needs another preset, retiming or a history listener, stop.

**Suggested wording** (production, if ever needed): "Body Preset changes were committed. CPM couldn't verify the
resulting bone scales." Production repair stays on hold.

**Minimum qualification.** Offline: the actual orchestration with independently advancing input, expression and
physical states; stale physical output refusing verified success; operator exceptions with verified Abort; wrong or
shared identity; peer; no-op; stale and changed-context callbacks; Expression, Body, Pose and legacy regressions.
Native: one Apply, lightweight reads at precommit and after the refresh, the full saved map, untouched peer, one
history action; Undo, Redo, final Undo field by field; one controlled failure after the operator call verifying Abort.

## 3. Where the conditions are carried out

| Condition | Where |
|---|---|
| Erratum, original evidence preserved | `F01_Q1_RESULTS_ERRATUM_1.md`; `F01_Q1_RESULTS.md` gains a one-line pointer only |
| Candidate (qualification only) | `F01_OT1_ORDERING_TRIAL_PREPARATION.md` section 2 |
| Offline qualification | same, section 3 (`test_cpm_app_f01_ordering_trial.py`, regressions) |
| Native trial, Undo gate, controlled Abort | same, sections 4–5 (`real_sfm_qualification/f01_ot1_ordering_trial/`) |
| Production | unchanged; no repair, wording change or promotion |
