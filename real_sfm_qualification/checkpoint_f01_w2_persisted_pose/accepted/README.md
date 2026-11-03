# F-01 W2: persisted left-arm pose capture and independent reapplication

**Status: CLOSURE CORRECTIONS A AND B COMPLETE OFFLINE — awaiting Astra's focused review of Corrections A and
B.** This is a research experiment, not a Pose Library.
- **Not run natively.** It has never been run in SFM, and its native gate is closed.
- **Not integrated.** Nothing here is part of CPM, the Normalizer, the preset schema, a GUI or a release.

| Item | Detail |
|---|---|
| Feature | F-01, *Poses as an additional CPM preset category* (`docs/MAINTENANCE_BACKLOG.md`) |
| Governing design | *F01_W2_Astra_Corrected_Design_Contract_2026-10-28* (Astra: ACCEPT WITH BOUNDED CORRECTIONS; SHA-256 `168d10910ac48d32016566e29d24823175b56f8a6459e8e459a1143ee62cbe43`), external and not committed |
| Architecture authority | The frozen R15 Blueprint governs the established CPM architecture; this experiment does not touch it |
| Builds on | The W1 checkpoint `real_sfm_qualification/checkpoint_f01_w1_arm_transfer/` (native PASS 2026-10-28). Its mechanisms are copied and adapted here; the W1 files are unchanged and not imported. |

## What W2 is meant to demonstrate

One Krystal left-arm pose:
1. **Captured read-only** in process A, in one disposable copy of the R2 fixture, at shot15 movie frame 5.
2. **Saved** to a portable, versioned file, `left_arm_pose.f01w2.json`.
3. **Applied after a genuine SFM restart** in process B, in a second, distinct disposable copy, at shot10
   frame 10.
4. **Applied independently**: the application uses only one immutable snapshot of the file's bytes and fresh
   destination observations.
5. **Under W1's transaction model**: one aborted test write, six committed float32 writes to the existing
   bracket keys (ticks 30000 and 70415) of `Hand_l_p`, `Hand_l_o` and `Elbow_l_p`, then owned Undo, Redo and
   final Undo, with the skeletal oracle evaluated independently.

## Contents

| Path | What it is |
|---|---|
| `POSE_FORMAT_v1.md` | The frozen pose-file format: strict JSON schema, conventions, examples |
| `DESIGN_TRACE.md` | Each design-contract clause traced to its code and tests |
| `harness/f01w2_core.py` | Shared core: W1's strict reads, resolution, captures, write targets, writer inventory and oracle (adapted); per-side identity checks; the portable descriptor; the strict pose parser; exclusive publication; two independent plan implementations; read-only process identity; the ledger |
| `harness/f01w2_capture.py` | Process A: read-only capture, the completion gate, exclusive publication |
| `harness/f01w2_apply.py` | Process B: process separation, immutable snapshot, fresh preflight, independent plan, the transactions |
| `tools/prepare_run.py` | `manifest` (launchers and the hash manifest), `prepare` (two disposable copies, the run directory), `gate` (between processes A and B) |
| `tools/finalize_f01w2.py` | The independent finalizer, which loads no harness code |
| `tests/test_f01w2.py`, `tests/fake_sfm_w2.py` | Offline suite (162 tests) and the synthetic fake SFM |
| `tests/fixtures/` | The synthetic scene, the golden pose and adversarial byte fixtures. All synthetic; no private capture. |
| `config.template.json` | Run configuration; local paths are placeholders |
| `INSTRUCTIONS.md` | Proposed operator runbook for a future, separately authorized native run |
| `EVIDENCE_MANIFEST_TEMPLATE.md` | Template for the native evidence manifest |
| `.gitattributes` | LF rule for this folder only |
| `SHA256SUMS.txt` | SHA-256 of every file in this folder except itself |

## Offline qualification

| Check | Python 2.7.5 (SFM) | Python 3.10.6 |
|---|---|---|
| `tests/test_f01w2.py` | 162/162 | 162/162 |
| Golden capture bytes | identical | identical |

**Mutation check:** 68 deliberate defects: the 18 original mutants, 34 for F-01 to F-05 and 16 for
Corrections A and B. The suite detects 67.
- The survivor, M50, removes the finalizer's gate-state summary check. Correction B's lookup validation now
  refuses the same states independently, so the verdict is unchanged. It is reported, not reclassified.
- Run under Python 3.10.6; every round is in the review packages.

**Running the suite:** from `tests/`, run `python test_f01w2.py [RESULTS.json]`. It needs no private input.

## Limitations and unverified native assumptions

1. **The fake is not SFM.**
   - The offline world is synthetic, and its arm "solver" is an analytic stand-in written in the collar
     frame.
   - The tests prove the harness's control flow, evidence and verdicts. They do not prove that native SFM
     behaves the same way.
   - W1's native evidence covers the unchanged mechanisms only.
2. **Process identity is assumed, not yet observed.**
   - `GetProcessTimes`, `OpenProcess(QUERY_LIMITED_INFORMATION)`, `K32EnumProcesses` and
     `QueryFullProcessImageNameW` are assumed to work from SFM's 32-bit Python 2.7.5 and from system Python.
   - Offline tests inject a fake provider, and the finalizer accepts injected evidence only offline.
   - Process A is looked up strictly. `OpenProcess` failing with `ERROR_INVALID_PARAMETER` (87) is assumed to mean
     that no process has the id. Access denied (5), or any other failure, is `UNKNOWN`, and the gate refuses it.
3. **Native publication is assumed.** That Windows `os.rename` refuses an existing target is tested on the
   development machine, not inside SFM.
4. **Determinism across processes is assumed.** A static scene should read back identically within one
   process. The capture completion gate requires exact equality; native jitter would refuse the capture
   (fail closed).
5. **The shoulder guard is tested directly.** In the fake, the collar bone coincides with `CollarL`, so the
   arm-offset comparison catches an origin mismatch first. The guard is tested on its own, and the finalizer
   also recomputes it independently from the recorded evidence.
6. **The source shot is not re-observed in process B.** W1's source-preservation evidence stands and is not
   extended.
7. **Scope.** One pose, one rig, one model, the left arm, existing bracket keys only. No key creation,
   partial poses or generalized retargeting.

## Governance

The canonical Ledger, the backlog and the frozen Blueprint are unchanged, and still list F-01 as an
unapproved proposal. Reconciling them belongs to a future authorized integration.
