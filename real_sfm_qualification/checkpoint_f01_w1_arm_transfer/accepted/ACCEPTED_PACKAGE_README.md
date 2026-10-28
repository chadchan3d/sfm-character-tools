# F-01 W1 Arm-Transfer Harness: Candidate for Independent Safety Review

**Status: FINAL-CORRECTED CANDIDATE, unexecuted and uncommitted.** It corrects the three P1 findings of Astra's safety review, the two remaining findings of Astra's closure review, and the one remaining P1-1 path of Astra's focused closure review; see *P1 corrections*, *Final focused corrections* and *Remaining abort-recovery correction* below. It requires Astra's independent safety review and explicit Owner authorization before any native SFM execution. No SFM was run, nothing was written to any session, and no production, CPM, M-05 or M-06 file was changed.

- **Controlling specification:** Astra, *F-01 Final Adjudication*, 2026-10-27 (`F01_Astra_Final_Adjudication_2026-10-27.md`, SHA-256 `41bd5bf7c3867765df467bd1867c7fd547cf56ca487d49383ed8c80b6b554a5f`).

## Contents

| Path | Purpose |
|---|---|
| `harness/f01w1_harness.py` | The SFM harness (Python 2.7/3); one Owner-submitted step per invocation |
| `harness/config.json` | Paths, protected-file hashes, frames, bracket ticks, tolerances, Astra cross-check values |
| `harness/NEXT_STEP.txt` | The single Script Editor line, pointing at the run directory's copy |
| `tools/prepare_run.py` | Creates a fresh run directory and disposable copy (SFM closed) |
| `tools/finalize_f01w1.py` | Post-close verification and overall verdict |
| `tests/fake_sfm.py`, `tests/test_f01w1_harness.py` | Offline tests: fake `sfmApp`/`vs`/`PySide` built from the R3 captures |
| `test_inputs/R3-shot15-A.json`, `R3-shot10-A.json` | R3 captures, verified against their published hashes |
| `test_results/` | Test output and JSON summaries for both interpreters |
| `RUNBOOK.md` | Exact Owner procedure |
| `HARNESS_SHA256.json` | Hashes that `prepare_run.py` enforces |
| `SHA256SUMS.txt`, `MANIFEST_SHA256.json` | Every file in the package |

## How the specification is implemented

**Scope and prerequisites (section 1).**
- **Fresh identities:** every step resolves the document, shot, animation set, model, rig registration, rig handles, controls, channels, logs, layers, bones and constraints anew.
- **Context checks:** the document must be the configured disposable path. The shot, head time, media time and shot range must equal the fixture's values, and the process must be the one that captured the baselines.
- **Preflight checks:**
  - **Arm hierarchy:** parents, bone indices and local bone positions match across the arm chain.
  - **Scale:** absent or 1 on the arm bones, the four handles and the model.
  - **Constraints:** the IK solver fields, constraint target offsets and pole target match. Joints, slaves and targets are matched by object identity.
  - **Weights:** all evaluated weights are 1.0.
  - **Parent space:** `Hand_l` and `Elbow_l` are parented to `rig_root`, and `rig_root` × local equals world.
  - **Writers:** writer uniqueness is checked document-wide: destination, log, layer, constraint slave targets and control writers.
  - **Operator types:** an unknown type anywhere stops.
  - **Write channels:** mode 3, indices 0/0, the expected log and layer types, a single layer, and no curve info.
  - **Hold interval:** both clocks are strictly inside the bracket, and the handle locals equal the native log values at both clocks.
  - **Undo:** native Undo is enabled.
- **Protected files:** the original, the R2 fixture, the disposable copy, the harness, the config and the CPM source are hashed before and after every step. A change is a `STOP`.

**Exact write set (section 2).**
- **Six values:** the bracket key values only, in `Hand_l_p`, `Hand_l_o` and `Elbow_l_p`.
- **Key lookup:** each channel resolves its own indices by native integer key time (`GetTenthsOfMS`: 30000 and 70415), requiring unique matches and no intervening key.
- **Writers:** only `SetKeyValue` writes to the scene.
- **Quaternion:** one quaternion, the same components and sign at both keys.
- **Hold check:** native log evaluation at both clocks is verified before `FinishUndo`.

**Coordinates (section 3).**
- **Formula:** `Gworld = Cd × inverse(Cs) × Rs × Ls`, then `Ldest = inverse(Rd) × Gworld`. Hand position and orientation are written; the elbow gets position only.
- **Float32:** values are converted to float32 before writing.
- **Pre-write checks:** the upper-arm origin mapping must be within 0.001. The goals must also match Astra's cross-check values within 1e-4 units and 0.001°, comparing orientations by rotation.

**Oracle (section 4).**
- **Primary:** the source local orientations of `bip_UpperArm_l`, `bip_lowerArm_l` and `bip_hand_l`, within 0.01°.
- **Secondary:** the source world transforms mapped through `Cd × inverse(Cs)`, within 0.001 units and 0.01°.
- **Disagreement:** if the two disagree, the state is `ORACLE_DISAGREEMENT`, which is never waived.
- **Preserved state:**
  - every other bone's local transform and scale state;
  - the arm bones' local positions and scale;
  - the model's local and world transforms;
  - `rig_root` and `CollarL` world transforms;
  - `Elbow_l` orientation;
  - constraint weights, and the scale state of the model and the four handles (P1-3).
- **Descendants:** descendant world transforms are not required to stay fixed.
- **Residual:** the hand-target residual is recorded at every observation.

**Transactions (section 5).**
- **Timing:** writes run only in `QTimer` one-shot callbacks after the Script Editor line has returned. Every callback re-checks the UI thread, the absence of modal dialogs, CPM idleness, the context and the write-target identities.
- **Undo descriptions:** distinct, nonce-bearing descriptions, using the two-argument `StartUndo`.
- **Sequence:**
  1. **Abort check:** one key is written, read back and aborted. The full authored state must be restored exactly. Evaluated state is checked after one idle opportunity.
  2. **Commit:** six writes with exact float32 readback, followed by full authored and source verification and the log check at both clocks. Then `FinishUndo`.
  3. **Ownership check:** the top Undo entry must be ours.
  4. **Undo, Redo, final Undo:** each is preceded by an ownership precondition and followed by exact authored verification.
- **Failures:** any failure inside the transaction aborts and verifies restoration. Uncertain ownership or unverified recovery stops; there is never a blind Undo, history clearing or compensating write.

**Evaluation (section 6).**
- **Observation:** one observation after one ordinary event-loop opportunity, classified as `IDLE` or as needing the one prescribed retime (frame 10 → 11 → 10, performed by the Owner).
- **After the retime:** a correct state is `RETIMING_DEPENDENT`; anything else is a `FAIL`.
- **Round trips:** after every stage, the playhead goes to shot15 and back. The source must be preserved, and the destination must show the state for that stage.

**Acceptance (section 7).**
- **Finalize:** `finalize_f01w1.py` derives `PASS` only from a complete, unbroken ledger with every step successful, no unclassified attribute changes and unchanged protected files.
- **Recording:** the propagation class is recorded per stage. A retiming-dependent result is reported as such, not as an immediately evaluated Apply.

## Implementation decisions for review

1. **Owner-driven steps.** The harness never moves the playhead and never forces evaluation. The prescribed retime and the shot15 round trips are Owner playhead moves; the harness verifies the resulting context.
2. **`CollarL` parent.** In both captures `CollarL` is parented to `spine_4`, not `rig_root`. The anchor uses its evaluated world transform, so the parent-space requirement applies to the written inputs only (`Hand_l`, `Elbow_l`).
3. **Quaternion sign.** The computed rotation equals Astra's cross-check value. Astra's printed components have the opposite sign (same rotation). The harness chooses the hemisphere of the key value it replaces and writes those identical components at both keys. The choice is recorded in the plan.
4. **Abort evaluated check.** If the evaluated state is not the baseline after the abort and one idle opportunity, the harness stops before committing. An unchanged evaluated state is recorded only; it does not prove evaluated rollback.
5. **Ownership evidence.** Ownership requires all of the following:
   - the nonce-bearing description on top of the stack;
   - the exact expected authored state;
   - an unbroken ledger from the same process and document.

   `GetUndoItemCount`, `ItemsAddedToCurrentUndo` and `UndoEnabledForElement` are recorded only.
6. **Two preservation classes.**
   - **Authored (exact; any change is a `STOP`):** in both shots, every channel's binding and complete logs, read through the native key getters. Also every animation-set control's stored values and channel references, the rig registration, rig-handle parents, and the constraint slave, target, offset, pole and solver relationships.
   - **Other constraint and operator attributes:** these exclude channel destinations and expression results. A change is reported and prevents `PASS` (giving `INCONCLUSIVE`), because some may be evaluated caches.

   Key values are serialized by layer type (Float, Vector3, Quaternion, Color: the types the fixture's shots use). Any other layer type, and any unreadable required field, refuses rather than being compared (see P1-1).
7. **`FAIL` is terminal.** A failed transfer is not undone or retried. The session is discarded without saving.
8. **Report size.** The source and destination baselines are stored once (steps 1 and 2); the committed state is derived from them.

## P1 corrections (Astra safety review)

- **P1-1, preservation evidence completeness.**
  - **Key serialization:** key values are serialized losslessly per layer type, covering only the four types present in the fixture (offline DMX survey: shot15 has 593 Vector3, 593 Quaternion, 463 Float and 2 Color logs; shot10 has 271, 271 and 205). Any other layer type raises; the old type marker is gone.
  - **Readability:** every authored, evaluated and constraint/operator capture must be fully readable; verifiably absent optional fields are allowed. Unreadable evidence at preflight is INCONCLUSIVE before any write. Later unreadability is INCONCLUSIVE (no PASS). During abort, Undo or Redo restoration checks, it is STOP: *recovery unverified*.
- **P1-2, rig input acceptance.**
  - **Required inputs:** an observation is accepted only if the `Hand_l` position and orientation and `Elbow_l` position equal the expected inputs: the float32 goals for committed and redone states, the baseline for aborted, undone and final states. Their native log evaluations at both the current and the nominal clock must agree too, and `Elbow_l_o` must stay at its baseline at both clocks. Tolerances are the declared effective and log-evaluation ones.
  - **Unchanged:** the skeletal oracle is still required. The hand-target residual stays diagnostic only.
- **P1-3, weights and scale.** Constraint weights (targets and values) and the scale state of the model and of `rig_root`, `CollarL`, `Hand_l` and `Elbow_l` are judged in every destination observation and in every source-return check. Source returns also judge bone scale and model placement.
- **Finalizer.** PASS now needs an independent audit of the whole ledger, and a terminal status alone is not enough. The audit checks:
  - **Grammar:** exact step order and stages, plus a single process.
  - **Evidence:** `evidence_complete`, stable integrity and no unclassified attribute changes in every report.
  - **Transaction:** the abort check proves restoration and its evaluated baseline is accepted; six exact float32 writes at 30000/70415 ticks; the commit's Undo-description ownership; and the Undo/Redo ownership preconditions.
  - **Observations:** every accepted observation passes the oracle, rig-input and preservation checks; propagation is classified consistently; source returns are clean.

  Anything incomplete or contradictory yields INCONCLUSIVE.
- **Unchanged:** the three channels and six writes, `CollarL` anchoring and coordinates, oracle and tolerances, the Undo/Abort/Redo sequence, Owner-controlled playhead, terminal FAIL and the protected files.

## Final focused corrections (Astra closure review)

- **P1-1, recovery-specific classification.** Every read required to verify a restoration now goes through `recovery_read()`, so unreadable evidence there is **STOP: recovery unverified**:
  - **After the abort:** the source authored state, and the evaluated state read by the abort's evaluated check.
  - **After Undo or Redo:** the source authored state, and the evaluated observation.
  - **Later steps:** the retime, source-return and destination-return steps of the undone, redone and final stages.

  Unreadable evidence during ordinary preflight, before any write, and in the committed stage stays INCONCLUSIVE. Nothing else changes.
- **Finalizer, contradictory raw evidence.** `writes_consistent()` checks each write's raw evidence independently of its summary flags:
  - **(A) readback:** `readback` = `requested_float32` = the plan's float32 goal, for the abort-check write too.
  - **(B) abort restoration:** the abort check needs `authored_restored` true **and** a present, empty `differences` list.
  - **(C) bracket coverage:** each of the three channels has exactly its two planned bracket indices, in order, at the native ticks 30000 and 70415, consistent with the plan's bracket times and write-channel record. A global tick set is not accepted as per-channel coverage.
- **Tests added (11):**
  - **Recovery (8 checks):** unreadable source after the abort, Undo and Redo; unreadable evaluated evidence after the abort and after Undo; unreadable evidence at the final destination return and at an undone source return. One more check confirms preflight unreadability stays INCONCLUSIVE.
  - **Finalizer (3 cases, 9 mutations):** readback contradictions (a commit write, a self-consistent but unplanned value, the abort-check write); abort restoration with nonempty or missing `differences`; per-channel coverage (both writes at 30000, swapped indices, a wrong index, wrong plan bracket times).
- **Adjusted test:** the reviewed test that hid evidence after Undo expected INCONCLUSIVE. Under this ruling that is STOP, and it is covered by the recovery tests. The test now checks the committed-stage case, which stays INCONCLUSIVE.
- **Detection:** against the baseline package's harness and finalizer, all 10 new negative tests fail (`test_results/final_tests_against_p1_baseline_py3.10.6.txt`). The preflight test passes on both, as intended.

## Remaining abort-recovery correction (Astra focused closure review)

- **Defect:** in `step_transfer.commit()`, a failure after the six writes (for example an unreadable source-authored capture) aborted and verified only the destination-authored restoration, then re-raised the original `Unresolved`, which was classified INCONCLUSIVE although source preservation after the abort was never verified.
- **Correction:** the commit-failure abort path now verifies **both** recovery conditions through the recovery-specific reads:
  - the destination authored state equals its baseline (`recovery_capture`);
  - the source authored state equals its baseline (`recovery_read`, label `source authored state after commit abort`).

  Either read unreadable is **STOP: recovery unverified**; either state differing from its baseline is STOP. Only when both are verified is the original failure re-raised with its own classification. The original failure (`repr`) is kept in the `commit-aborted`/`commit-abort-failed` event (`commit_failure`) and in every STOP message. Preflight unreadability before any write stays INCONCLUSIVE.
- **Tests added (2):**
  - six authorized writes, then the source-authored capture becomes unreadable and stays unreadable after the abort; the destination is restored; the result is STOP (recovery unverified), with the original `Unresolved` preserved;
  - a commit failure (float32 readback mismatch) whose abort restores the destination but leaves the source different from its baseline: STOP.
- **Detection:** against the reviewed harness (`89470853…`), both new tests fail; the first ends INCONCLUSIVE, exactly the reported path (`test_results/abort_recovery_tests_against_reviewed_py3.10.6.txt`).
- **Unchanged:** the three-channel/six-key mutation boundary, coordinates, oracle, tolerances, input/weight/scale checks, finalizer, transaction sequence, Owner retiming and terminal FAIL handling. The test fake gains one switch (`unreadable_after_writes`).

## Offline qualification

82 tests (80 from the final-corrections package plus the 2 above), all passing under SFM Python 2.7.5 and Python 3.10.6 (`test_results/`). They cover:
- **Math:** reproduction of Astra's goals directly from the R3 captures:
  - hand position within 1.4e-5, from 6-decimal rounding and float32 spacing;
  - same rotation;
  - anchor error 0.0000647;
  - source residual 0.051391.

  Agreement with an independent matrix implementation, the sign rule, and the oracle states.
- **Procedure:** the full idle-propagation `PASS`, with exactly `StartUndo`, `Abort`, `StartUndo`, `FinishUndo`, `Undo`, `Redo`, `Undo`, and stored source values untouched. A retiming-dependent `PASS`.
- **FAIL paths:** no propagation after the retime; oracle disagreement; an unrelated bone change; a source evaluated change.
- **STOP paths:**
  - abort not restoring; synchronous evaluation not rolled back;
  - a write without effect; a write exception (abort and restore); float32 readback mismatch (commit aborted and restored);
  - uncertain commit ownership; a foreign Undo or Redo entry; Undo not restoring;
  - a competing writer; a shared log; a missing bracket key; an intervening key;
  - a modal dialog at callback entry; authored mutation in either shot; wrong playhead;
  - protected-file change; Undo disabled; harness change mid-ledger.
- **INCONCLUSIVE:** unreadable required evidence.
- **Refusals:** concurrent submission; a tampered or empty ledger; steps after the end.
- **P1 negatives:**
  - **Evidence:** unsupported layer types and identical unreadable records are refused.
  - **Rig inputs:** wrong inputs fail at every stage (committed, aborted, undone, redone, final), and stale log evaluations at either clock are rejected.
  - **Weights and scale:** changed weights, model scale and collar/root scale fail at the destination and at the source return.
  - **Finalizer:** 15 kinds of contradictory or incomplete ledger are not PASS, and status alone is not evidence.
  - **Detection:** against the reviewed harness and finalizer, 22 of these tests fail (`test_results/p1_tests_against_reviewed_candidate_py3.10.6.txt`).
- **Finalize and preparation:** a saved disposable copy gives `STOP`; an incomplete ledger gives `INCONCLUSIVE`; the final report is exclusive; an attribute change prevents `PASS`. Preparation refuses reuse, a modified harness and a changed fixture.
- **Static safety:** the only native mutators are `SetKeyValue`, `StartUndo`, `FinishUndo`, `AbortUndoableOperation`, `Undo` and `Redo`, each confined to its function. There are no forbidden calls and only standard, `sfmApp`, `vs` and `PySide` imports.

## Native assumptions not demonstrated offline

The fake rig is a lookup, so these are exactly what the experiment, or its first step, will establish:
- **Undo behaviour:** whether `SetKeyValue` records Undo, whether `AbortUndoableOperation` restores, and whether `Undo`/`Redo` restore the authored values exactly.
- **Undo descriptions:** whether `GetUndoDesc` and `GetRedoDesc` return the supplied descriptions verbatim. If not, the run stops safely after the commit.
- **Evaluation timing:** whether one `QTimer(0)` turn is an evaluation opportunity in SFM.
- **Native types:** that `GetTenthsOfMS` exists on key times, that `vs.Vector`/`vs.Quaternion` (or `vs.mathlib`) construct native values, and that element arrays behave as in R3.
- **Capture cost:** 2,398 channels holding 2,964 keys across the two shots (offline DMX survey), captured twice per step. The capture is bounded at 400,000 keys; exceeding it is `INCONCLUSIVE`.
- **Attribute stability:** whether unclassified constraint attributes stay stable under evaluation. If not, the result is `INCONCLUSIVE`, not `PASS`.

This candidate does not qualify single-frame pose insertion, clock equivalence, generic rig support or a Pose Library. Configuration and reports contain private local paths, so share them privately.
