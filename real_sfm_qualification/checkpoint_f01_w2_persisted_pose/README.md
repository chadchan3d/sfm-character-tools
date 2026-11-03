# F-01 Pose Library — W2 research checkpoint: persisted left-arm pose, reapplied after a process restart

**Status: W2 COMPLETE — native PASS (Run_002, 2026-10-30); Astra final native ruling: CLOSED/PASS.**

This is a research checkpoint, not a Pose Library. W2 shows that one Krystal left-arm pose can be:
1. captured read-only in one SFM process;
2. saved to a portable versioned file;
3. applied after a genuine SFM restart, in a second process and a second disposable copy, to six existing key values, under native Abort, Undo and Redo.

Nothing here is integrated into CPM, the Normalizer, the preset schema or a release.

- **Feature:** F-01, *Poses as an additional CPM preset category* (`docs/MAINTENANCE_BACKLOG.md`).
- **Builds on:** the W1 checkpoint `real_sfm_qualification/checkpoint_f01_w1_arm_transfer/` (native PASS 2026-10-28). W1's files are unchanged.
- **Governing design:** *F01_W2_Astra_Corrected_Design_Contract_2026-10-28* (SHA-256 `168d10910ac48d32016566e29d24823175b56f8a6459e8e459a1143ee62cbe43`). It is an external review attachment and is not committed.
- **Rulings:**
  - Astra closed the offline candidate CLOSED/PASS, after Corrections A and B.
  - After Run_002, Astra issued the final native qualification ruling, **CLOSED/PASS**.

  Both are external rulings and are not committed.
- **Governance:** the canonical Ledger and the frozen R15 Blueprint are unchanged by this checkpoint.
- **Evidence:** identities, the hash-chained report hashes and the results are in [`W2_NATIVE_QUALIFICATION_EVIDENCE.md`](W2_NATIVE_QUALIFICATION_EVIDENCE.md). The raw native reports and the pose stay in the owner's local run directory.

## Contents

| Path | What it is |
|---|---|
| `accepted/` | The Astra-qualified W2 tree, **byte-exact**: the closed package's candidate, unchanged. This is the tree whose harness files Run_002 executed. |
| `accepted/harness/` | `f01w2_core.py`, `f01w2_capture.py` (process A), `f01w2_apply.py` (process B) |
| `accepted/tools/` | `prepare_run.py` (manifest, prepare, process gate), `finalize_f01w2.py` (the independent finalizer) |
| `accepted/tests/` | The offline suite `test_f01w2.py` (162 tests), the synthetic fake SFM and fixtures (synthetic scene, golden pose, adversarial byte fixtures). There is no private capture. |
| `accepted/README.md`, `DESIGN_TRACE.md`, `POSE_FORMAT_v1.md` | The accepted design, its traceability to the contract, and the portable pose format. Their status lines record the package's pre-execution review state. |
| `accepted/INSTRUCTIONS.md`, `accepted/config.template.json`, `accepted/EVIDENCE_MANIFEST_TEMPLATE.md` | The accepted operator runbook and configuration template, already with placeholders for local paths |
| `accepted/.gitattributes`, `accepted/SHA256SUMS.txt` | The accepted tree's own LF rule (adversarial fixtures binary) and its own hash list |
| `W2_NATIVE_QUALIFICATION_EVIDENCE.md` | The native qualification report |
| `SHA256SUMS.txt` | SHA-256 of every file in this folder |

**Not committed:**
- the executed `config.json`, `CAPTURE_STEP.txt` and `APPLY_STEP.txt` (they contain private local paths);
- the raw native reports (they contain private local paths and scene captures);
- the persisted pose (scene data from the private session);
- the original session, the R2 fixture and both disposable copies;
- Run_001's STOP evidence;
- the review and closure packages;
- the test logs.

Their identities are recorded in the evidence document.

## What W2 proved (Run_002)

| Step | Outcome |
|---|---|
| **Process A** (capture, read-only) | shot15 at 0.20829999446868896 s. The pose was published by a no-replace rename. |
| **Process gate** | The recorded process A was positively shown to have exited (native kernel32), with no SFM running. Both copies and the pose were unchanged. |
| **Process B** (a new process; shot10, frame 10) | Process separation was proved. The pose was read once. There was a fresh compatibility preflight and two independent plans. The abort check restored the authored state exactly. Then: six committed writes; Undo; Redo; final Undo. |
| **Propagation** | IDLE at every stage, with no retime |
| **Finalizer** | **PASS**, `reasons: []` |

## Offline qualification (accepted package)

`accepted/tests/test_f01w2.py`: **162/162** on Python 2.7.5 (SFM) and on 3.10.6. The golden capture bytes are identical on both.

**Mutation check:** 68 deliberate defects, of which **67 were detected**. The survivor is M50, which removes the finalizer's gate-state summary check. Correction B's independent lookup validation refuses the same states, so the verdict is unchanged. It is reported as a survivor, not reclassified.

## Accepted limitations

1. **Left arm only.** The hand position and orientation and the elbow position go into the three existing IK channels `Hand_l_p`, `Hand_l_o` and `Elbow_l_p`, at their two bracket keys. No other body part is covered.
2. **Same rig only.** Compatibility was established for `krystal2020.mdl` in the R2 fixture, by an exact arm-chain and rig-descriptor match (maximum arm bone offset 0.0). Cross-model and cross-rig transfer is not qualified.
3. **Source-shot observation boundary.** Process B does not re-observe the source shot. Source preservation rests on W1's evidence, which W2 does not extend, as the finalizer states.
4. **Existing keys only.** No key, channel, log, layer or operator is created.
5. **One disposable scene, one machine, one native run.** The offline fake is synthetic and is not SFM.
6. **Capture `file_id: 0`.** The capture context records the session file id as 0. The harness accepted it. It is preserved as an observation and not interpreted.
