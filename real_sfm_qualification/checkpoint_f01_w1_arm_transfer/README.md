# F-01 Pose Library — W1 research checkpoint: rig-preserving left-arm transfer

**Status: W1 COMPLETE — native PASS (2026-10-28).** This is a research checkpoint, not a Pose Library.
It demonstrates one rig-preserving left-arm transfer between two shots of one disposable session, under
native Abort, Undo and Redo. Nothing here is integrated into CPM, the Normalizer, the preset schema or a
release.

- **Feature:** F-01, *Poses as an additional CPM preset category* (`docs/MAINTENANCE_BACKLOG.md`).
- **Governance:** the canonical Ledger (`cpm/qualification/CPM_CONVERGENCE_LEDGER.md`) and the frozen R15
  Blueprint are unchanged by this checkpoint. W1 was run under Astra's *F-01 Final Adjudication*
  (2026-10-27, SHA-256 `41bd5bf7c3867765df467bd1867c7fd547cf56ca487d49383ed8c80b6b554a5f`), retained as an
  external review attachment and not committed. Astra's final safety ruling on the harness: **PASS, all
  findings closed.**
- **Evidence:** numerical results, identities and evidence hashes are in
  [`W1_NATIVE_QUALIFICATION_EVIDENCE.md`](W1_NATIVE_QUALIFICATION_EVIDENCE.md). The raw native reports stay
  in the owner's local run directory and are not committed.

## Contents

| Path | What it is |
|---|---|
| `accepted/harness/f01w1_harness.py` | The accepted SFM harness, byte-exact (`a91933c2…`) |
| `accepted/tools/prepare_run.py`, `accepted/tools/finalize_f01w1.py` | Run preparation and the post-close finalizer, byte-exact |
| `accepted/tests/test_f01w1_harness.py`, `accepted/tests/fake_sfm.py` | The offline suite (82 tests) and its fake SFM, byte-exact |
| `accepted/ACCEPTED_PACKAGE_README.md` | The accepted package's own README, byte-exact: the implemented design, every correction round and the offline coverage. Its status line records the package's pre-execution review state. |
| `config.template.json` | The accepted `config.json` with its five private path values replaced by placeholders, including the original session's file name (`<SOURCE_SESSION>`); every other value (frames, ticks, tolerances, cross-check values) is unchanged |
| `INSTRUCTIONS.md` | The accepted operator runbook with private paths and the original session's file name replaced by placeholders; otherwise word-for-word |
| `W1_NATIVE_QUALIFICATION_EVIDENCE.md` | The native qualification report: identities, evidence hashes, numerical results |
| `SHA256SUMS.txt` | SHA-256 of every file in this folder |

Not committed: the accepted `config.json` and `NEXT_STEP.txt` (both contain private local paths), the R3
native captures used as offline test inputs (they hold scene data from the original session), the
original session, the R2 fixture and the disposable copy, the raw native reports, the review diffs and the
test logs. Their identities are recorded in the evidence document.

## Experiment design (as accepted)

**Scope.** One disposable copy of the validated R2 fixture (`krystal2020.mdl`, animation set `Krystal`).
Source pose: shot15, movie frame 5. Destination: shot10, movie frame 10. Only the left arm.

**Mutation boundary.** Exactly six existing key values are written: the two bracket keys (native ticks
30000 and 70415) of the three existing IK rig channels `Hand_l_p`, `Hand_l_o` and `Elbow_l_p`. No key is
added or removed, no channel, log, layer or operator is created, and `SetKeyValue` is the only scene
writer. Writer uniqueness is checked document-wide before any write.

**Coordinate mapping** (collar-relative). With `Cs`/`Cd` the source/destination `CollarL` world transforms,
`Rs`/`Rd` the source/destination `rig_root` world transforms and `Ls` the source rig-handle local transform:

```
Gworld = Cd × inverse(Cs) × Rs × Ls
Ldest  = inverse(Rd) × Gworld
```

The hand receives position and orientation; the elbow receives position only. Values are converted to
float32 before writing. Before any write, the upper-arm origin mapping must agree within 0.001 units, and
the computed goals must match Astra's independent cross-check within 1e-4 units and 0.001°. The quaternion
hemisphere follows the key value being replaced, with identical components at both keys.

**Oracle.**
- **Primary:** the destination's local orientations of `bip_UpperArm_l`, `bip_lowerArm_l` and `bip_hand_l`
  must equal the source's within 0.01°.
- **Secondary:** the source world transforms mapped through `Cd × inverse(Cs)` must match within
  0.001 units and 0.01°.
- **Disagreement** between the two is `ORACLE_DISAGREEMENT` and is never waived.
- **Preservation:** every other bone, the model, `rig_root`, `CollarL`, constraint weights and scale
  states must be unchanged; the hand-target residual is recorded at every observation.

**Transactions.** Writes run only in deferred one-shot callbacks after the Script Editor line returns. The
sequence is: an abort check (one key written, then `AbortUndoableOperation`; exact authored restoration
required), the six-value commit under a nonce-bearing Undo description, then owned Undo, Redo and a final
Undo. Each Undo/Redo has an ownership precondition and exact authored verification. Any failure inside a
transaction aborts and verifies restoration; uncertain ownership or unverified recovery is `STOP`. There is
never a blind Undo, history clearing or compensating write. The Owner moves the playhead; the harness never
does.

**Acceptance.** `finalize_f01w1.py` derives `PASS` only from an independent audit of the complete,
hash-chained ledger of step reports, with unchanged protected files.

Full detail, including every review correction, is in `accepted/ACCEPTED_PACKAGE_README.md`.

## Result summary

`F01W1 FINAL: PASS`, no failure reasons; all 13 steps; propagation `IDLE` at every stage (no retime).

| Measure | Result | Tolerance |
|---|---|---|
| Primary oracle, max local orientation error | 0.00107° | 0.01° |
| Secondary oracle, max world orientation error | 0.00088° | 0.01° |
| Secondary oracle, max world position error | 0.000131 units | 0.001 |
| Goals vs Astra cross-check | 1.4e-5 units, 3.1e-5° | 1e-4, 0.001° |
| Writes | 6, exact float32, three existing channels | exactly 6 |
| Unrelated changes | 0 at every observation | 0 |

Abort, Undo, Redo and the final Undo each restored or reproduced the exact expected authored state; the
source was preserved at all four stages; the original session, the R2 fixture and the disposable copy were
unchanged afterwards. See the evidence document for the per-stage table.

## Limitations and unsupported cases

- **One pair, one chain:** one compatible source/destination pair in one session, one model and rig, the
  left arm only, on one machine. No other limb, rig, model, character pair or cross-session transfer is
  qualified.
- **Not a pose capture:** W1 transfers between two shots of the same open document. There is no saved pose
  file, no reload and no independent reapplication.
- **Fixed write set:** only the existing bracket keys are changed. Single-frame pose insertion, key
  creation, clock equivalence and partial poses are not qualified.
- **Idle propagation only:** the retime-dependent path never occurred natively, so it is qualified offline
  only.
- **Evaluated rollback:** an unchanged evaluated state after the abort is recorded but does not by itself
  prove evaluated rollback; the owned Undo/Redo results supply that evidence.
- **Hand-target residual:** the transferred pose reproduces the source rig's own reach residual (0.0514
  units). Whether that is acceptable is a Pose Library design question, not a transfer defect.
- **Configuration is machine-specific:** a run elsewhere needs a filled-in config and therefore new
  `HARNESS_SHA256.json` values; that is a new candidate, not this accepted one.
- **No product integration:** no CPM code, GUI, preset schema, Undo integration or release is involved.

## Next design milestone (recommended, not implemented)

Astra has recommended **W2: persisted capture, independent reload and reapplication of one compatible
left-arm pose.** Its recommended scope:
- a versioned pose-file format;
- read-only capture of effective rig inputs and independent skeletal reference data;
- collar-relative saved control transforms;
- fresh destination compatibility resolution;
- the existing three-channel / six-key mutation boundary;
- native Apply, Undo, Redo and final Undo verification;
- no production CPM integration and no preset-schema change.

W2 is a recommendation only. No W2 design is approved and no W2 code exists in this checkpoint.

## Reproducing the offline suite

The suite needs inputs that are not public. To run it, assemble a copy of `accepted/`:
1. copy `config.template.json` to `harness/config.json` (the tests replace every path value);
2. place the R3 captures `R3-shot15-A.json` and `R3-shot10-A.json` in `test_inputs/` (the suite verifies
   their SHA-256 values, listed in the evidence document);
3. from `tests/`, run `python test_f01w1_harness.py <summary.json>` under SFM Python 2.7.5 or Python 3.

Result for this checkpoint's exact files: 82/82 under both interpreters.
