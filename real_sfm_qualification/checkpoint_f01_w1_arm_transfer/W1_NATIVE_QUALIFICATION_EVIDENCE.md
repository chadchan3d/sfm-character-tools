# F-01 W1 native qualification — evidence manifest

**Experiment:** F-01 W1, rig-preserving left-arm transfer (research; not a Pose Library).
**Authority:** Astra *F-01 Final Adjudication* (2026-10-27); Astra final harness safety ruling PASS, all findings
closed; owner authorization for one disposable native run. **Run:** 2026-10-28, 04:59–05:08 UTC, one disposable
session, one machine (Windows 10, SFM Python 2.7.5), one SFM process. **Result:** `F01W1 FINAL: PASS`.

The raw native reports stay in the owner's local run directory `F01_W1_ArmTransfer_Run/` (paths below are relative
to it). They are not committed: they contain private local paths and full scene captures.

## Identities

| Item | SHA-256 |
|---|---|
| Controlling specification: Astra *F-01 Final Adjudication* 2026-10-27 (external attachment) | `41bd5bf7c3867765df467bd1867c7fd547cf56ca487d49383ed8c80b6b554a5f` |
| Accepted package `F01_W1_Harness_Abort_Recovery_Correction_Safety_Review.zip` (not committed) | `272a9f55647953a49a359fac1a015095e656ae6b20770fb08e19666d798cf5f7` |
| Harness `accepted/harness/f01w1_harness.py` (committed, byte-exact) | `a91933c2c9a2eec791ff70691fa1810b7f24a3497900441e29791585fcb82106` |
| Accepted `harness/config.json` (private paths; not committed; see `config.template.json`) | `7f855c3fcda97aad75d194c277808643f57c586a09153e6422536e7fe20894ff` |
| Accepted `harness/NEXT_STEP.txt` (private path; not committed) | `ad5d91da6e88b7b19721c2a582b385222873e68f0ecd07c8c63efe7f084a80e6` |
| Accepted `HARNESS_SHA256.json` (enforced by `prepare_run.py`; not committed) | `c30b16cd36095c1564b07d7253d8f4e54d4d2e5a95d01b6adc578cae9d8c70bc` |
| Accepted `RUNBOOK.md` (private paths; sanitized as `INSTRUCTIONS.md`) | `1f43b902aa55a2526e449ca1037e61dcb1ba89897eadfb8550a1f5c57e3bef24` |
| `accepted/tools/prepare_run.py` (committed, byte-exact) | `0664630413f9b54c4880ce53254cd849b055df01a8f0b9b26262ca4051dac090` |
| `accepted/tools/finalize_f01w1.py` (committed, byte-exact) | `0bcfa1838862329548043a9b345936c1aa3c3629c229bda63b54e7d78949f39f` |
| `accepted/tests/test_f01w1_harness.py` (committed, byte-exact) | `0c3d40fd7d195b2fd91dfd1032de71eca3c49cff8e14a8448cf21ed0f5478480` |
| `accepted/tests/fake_sfm.py` (committed, byte-exact) | `fb9ba3c36b65023f0bee07149295b5587b53843feace0473574668a58bc2d22d` |
| Offline input R3 capture `R3-shot15-A.json` (scene data; not committed) | `838c21d231f497edd640524f1ae728ab4ff08013ee660f7c7014b06daa64dde0` |
| Offline input R3 capture `R3-shot10-A.json` (scene data; not committed) | `b14bcd930f3e4eb2d1d1f4f5637ba833dc7a0fb678835ec0dc2bc911cc3105de` |
| Original session `<SOURCE_SESSION>.dmx` (never opened; unchanged before and after) | `3af2ad5425c5aa623df47ecfb2737015b8f80260b1ffebe5c2a868ed039b687b` |
| R2 fixture (read-only source of the disposable copy; unchanged) | `259ea8a614bc9e43e5bde15afdf38e1a1295dffb50b14cf75692df4221a05a2c` |
| Disposable session `F01_W1_DISPOSABLE_<SOURCE_SESSION>.dmx` (unchanged after the run: nothing saved) | `259ea8a614bc9e43e5bde15afdf38e1a1295dffb50b14cf75692df4221a05a2c` |

The harness also hashed the CPM application source in the owner's working tree as a protected file before and after
every step; it was unchanged throughout. W1 neither imports nor writes CPM. The installed product CPM was the
published v1.0.0 build `ccbed9d7…` before and after the run.

## Evidence files (`reports/`)

Each report records the SHA-256 of its predecessor (`previous_report_sha256`); the finalizer verified the chain.

| Report | Step / stage | Status | SHA-256 |
|---|---|---|---|
| `F01W1-01-SOURCE_BASELINE.json` | read-only shot15 capture | CONTINUE | `ad8f70401adc72098d29b4e7eb4219939b3d4c1613cd2f4463cb1b125b6f927b` |
| `F01W1-02-TRANSFER.json` | preflight, abort check, commit, observation / committed | CONTINUE (IDLE) | `77757c05a8786eef1779fa1715180c0e40ba58838fb4f986b0a42bd3325b68a6` |
| `F01W1-03-SOURCE_RETURN.json` | committed | CONTINUE | `5896237ae4dca889f37a0a8861b56ef8c17d67a0f7ab1de7497e7d9a4b067b0c` |
| `F01W1-04-DESTINATION_RETURN.json` | committed | CONTINUE | `b3bd8f8223272adf49ab0624dbfe67cea058720cd3ed275ff379b604f833ba85` |
| `F01W1-05-UNDO.json` | undone | CONTINUE (IDLE) | `8c3dd8f98f736a9db08f2c6d6697fa37fa6b591e5d61517c2a94423cac628709` |
| `F01W1-06-SOURCE_RETURN.json` | undone | CONTINUE | `2d7383af34bef6c4837a77b3e16b89d04a6966f505e612e0349768a547751e35` |
| `F01W1-07-DESTINATION_RETURN.json` | undone | CONTINUE | `3fe34060be466c8a46af0bdc64c2b8108968e636d5081834e845583cb2500e8a` |
| `F01W1-08-REDO.json` | redone | CONTINUE (IDLE) | `ab1ecdf66a3e0d5325b5b86b537749eb1e2a9223bc189998b1e459512e57b3ab` |
| `F01W1-09-SOURCE_RETURN.json` | redone | CONTINUE | `c7013892d76986777a0f39e3bb089ad7808383d867fa3c1b86b7193debc281a1` |
| `F01W1-10-DESTINATION_RETURN.json` | redone | CONTINUE | `6e10dc038ac670e5a239e3a380f7ec165eba7c633334c3001bd35395a4753d65` |
| `F01W1-11-FINAL_UNDO.json` | final | CONTINUE (IDLE) | `c2388d67d6721a3f40bd2afbe45a4d08ea59bbf1512776b5cd73ef09753c04bd` |
| `F01W1-12-SOURCE_RETURN.json` | final | CONTINUE | `87881deb92a028417b519752252cc0f5f3b2117502a5a38c9e93ce5fb50980db` |
| `F01W1-13-DESTINATION_RETURN.json` | final | COMPLETE_PENDING_CLOSE | `fd791eefc7b1ea39fb3d858dfbf32f7950ae326f6b48f83a5b7da461107c9770` |
| `F01W1-FINAL.json` | finalizer verdict | **PASS**, `reasons: []` | `9cc9c4491950a9e9f0fedd6c008421b82eb29ad5df77dbb62f8300caf8cb7403` |

Every step report has `evidence_complete: true` and identical before/after protected-file records.

## Preflight (step 2)

- **Document scope:** 10,070 channels and 787 operators, all of supported types (224 expression, 7 pack-colour,
  64 IK, 278 orient-constraint, 214 point-constraint); writer uniqueness checked document-wide.
- **Arm chain:** `bip_collar_l`, `bip_UpperArm_l`, `bip_UpperArm_l_twist2`, `bip_lowerArm_l`,
  `bip_lowerArm_l_twist2`, `bip_hand_l`; bone offset mismatch 0.0.
- **Constraints:** IK, hand-orient and collar point/orient constraint offsets and solver fields read and matched.
- **Native Undo:** enabled; Undo stack empty before the abort check.

## Pose transfer

| Quantity | Value |
|---|---|
| Collar (upper-arm origin) mapping error | 6.47e-5 units (limit 0.001) |
| Goals vs Astra cross-check: hand position / elbow position / hand orientation | 1.37e-5 / 7.02e-6 units / 3.13e-5° (limits 1e-4, 0.001°) |
| Written `Hand_l_p` (float32) | `[-3.0101867, 10.6349316, 39.0317993]` |
| Written `Hand_l_o` (float32 quaternion) | `[-0.3717369, 0.5041141, -0.6012118, 0.4962107]` (hemisphere of the replaced key; not negated) |
| Written `Elbow_l_p` (float32) | `[-16.9013958, 6.9997425, 54.8686829]` |
| Writes | `Hand_l_p` keys 1/2, `Hand_l_o` keys 1/2, `Elbow_l_p` keys 2/3 at ticks 30000/70415; each exact float32 readback, key count and key time unchanged |
| Change from baseline at the destination | upper arm 79.09°, forearm 20.87°, hand 17.13°; hand world position 24.83 units |

## Oracle and observations

| Report | Expected | State | Max primary (°) | Max secondary (°) | Max secondary (units) | Residual | Unrelated |
|---|---|---|---|---|---|---|---|
| 02 TRANSFER | TRANSFERRED | TRANSFERRED | 0.00092 | 0.00088 | 0.000092 | 0.05137 | 0 |
| 04 DESTINATION_RETURN | TRANSFERRED | TRANSFERRED | 0.00107 | 0.00073 | 0.000131 | 0.05138 | 0 |
| 05 UNDO | BASELINE | BASELINE | baseline 2.4e-6 | | baseline 0.0 | 0.000055 | 0 |
| 07 DESTINATION_RETURN | BASELINE | BASELINE | baseline 2.4e-6 | | baseline 0.0 | 0.000055 | 0 |
| 08 REDO | TRANSFERRED | TRANSFERRED | 0.00107 | 0.00073 | 0.000131 | 0.05138 | 0 |
| 10 DESTINATION_RETURN | TRANSFERRED | TRANSFERRED | 0.00107 | 0.00073 | 0.000131 | 0.05138 | 0 |
| 11 FINAL_UNDO | BASELINE | BASELINE | baseline 2.4e-6 | | baseline 0.0 | 0.000055 | 0 |
| 13 DESTINATION_RETURN | BASELINE | BASELINE | baseline 2.4e-6 | | baseline 0.0 | 0.000055 | 0 |

Every observation has `correct: true` and accepted rig inputs (goals for transferred states, baseline otherwise).
For BASELINE rows the figures are the distance from the original baseline. The hand-target residual of the
transferred state equals the source pose's own residual (0.05139), not an error introduced by the transfer.

**Source preservation:** the four `SOURCE_RETURN` reports (committed, undone, redone, final) each record no source
evaluated changes and no observed changes.

## Recovery

| Check | Result |
|---|---|
| Abort check | one `Hand_l_p` key written (exact), then `AbortUndoableOperation`: authored state restored exactly (`differences: []`); Undo stack empty before and after; evaluated state at baseline after one idle opportunity |
| Commit | Undo entry `F01W1 arm transfer 946d467f6ad8`, 6 items, on top of the stack (ownership verified) |
| Undo | entry removed (6 → 0 items), Redo offered for the same description; exact baseline authored state; BASELINE observation |
| Redo | entry restored (0 → 6 items); exact committed authored state; TRANSFERRED observation identical to the committed one |
| Final Undo | entry removed again; exact baseline authored state; BASELINE observation |
| Propagation | IDLE at committed, undone, redone and final; no retime requested |
| Protected files after close | original session, R2 fixture and disposable copy all unchanged |

## Offline qualification of the committed files

`accepted/tests/test_f01w1_harness.py` with `config.template.json` as the config and the two R3 captures as inputs:
**82/82 pass** under SFM Python 2.7.5 and under Python 3.10.6 (no failures, no errors).

## Package note

The accepted ZIP also contains a stray 169-byte file `TestRecoveryClassification`: a test-run summary written when
the suite was invoked with a test-class name as its single argument, which the suite treats as the summary path. It
is listed in the package manifest, is not code, and is not committed here.
