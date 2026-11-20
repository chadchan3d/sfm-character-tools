# F-01 RC4: Astra's revised verification contract, implemented (offline, not native-tested)

**Authority:** Astra's REVISE ruling, accepted in "F-01 RC4 — Implement Astra's Revised Verification Contract"
(Owner/Designer GO at `39722fb`). Evidence: the preserved RC4 native run (`F01_RC4_NATIVE_CROSS_RIG_RESULTS.md`), whose
verdict stays **INCOMPLETE 129/132**.

## 1. Reproduction separated from preservation

**New constants:**
- `PROD_POSE_REPRODUCTION_TOLERANCES = {position: 0.01, angle_degrees: 0.1}`, inclusive;
- `prod_pose_reproduction` checks one required skeletal output: finite, readable evidence first, then both limits.
  - A readable output outside the envelope is a **reproduction** problem.
  - Missing, unreadable or non-finite evidence is an **integrity** problem.
  - Maxima are recorded.

**Where the envelope applies** (skeletal-output reproduction only):

| Route | Reproduction outputs (new envelope) |
|---|---|
| Left arm, v1 (`prod_pose_classify`) | the arm bones' primary local-orientation oracle and anchor-mapped world oracle |
| Full body, v2: Krystal registry and structural rigs (`prod_body_verify_skeleton`) | every expected bone's world transform; simulated leaves stay exempt, as approved |
| Selected parts and generic Full body, v3 (`prod_scope_verify`) | every affected bone's world transform, and each posed bone's local orientation |

**Unchanged** (own limits, as before):
- **Shared constants:** no constant was replaced (`PROD_SCOPE_TOLERANCES` and the profile tolerances keep 0.001 and 0.01°).
- **Destination:** identity, ownership, authority and dependencies.
- **Keys:** authored keys, neighbouring keys, timing and metadata.
- **Character state:** model and placement-handle placement, facing and scale; carried, preserved, passive and unaffected bones' local transforms; scales.
- **Comparisons and rig:** structural compatibility (including Astra's bounded static offsets), P2 stability, the effective rig inputs and the P5 written-value checks, and the pre-write source and composition cross-checks.
- **Recovery:** Abort restoration, Undo and recovery lockout.

## 2. Outcomes

| Outcome | When | Result |
|---|---|---|
| Success | integrity, effective inputs and reproduction verify | `committed-verified`; the `P7-verified` log carries the reproduction maxima |
| Reproduction mismatch | every P7 problem is a reproduction problem (authored change and ownership verified) | phase and log outcome `reproduction-mismatch`, status (warning) "Pose keys applied, but the evaluated pose differs from the saved pose." No lockout, no automatic Undo, ordinary editing and Undo kept; `P7-reproduction-mismatch` logs the problems and maxima |
| Integrity uncertainty | any other problem, or missing or unreadable evidence | `committed-unverified`, as before |
| Recovery uncertainty | Abort restoration can't be established | `ProdRecoveryUnverifiedError` and the lockout, as before |

## 3. Repeat Apply (all three routes)

After context, authority and the planned keys are checked (`prod_pose_nowork`, `prod_pose_nowork_result`):

| Planned keys | Evaluated pose | Result | Undo |
|---|---|---|---|
| all present | reproduction verifies | `no-op` ("Already matches this pose.") | never opened |
| all present | reproduction problems only | no-write `reproduction-mismatch` | never opened |
| all present | integrity problem or unreadable evidence | refusal `already-unverified` ("This pose's keys are already on the character, but CPM couldn't verify it. Nothing was changed.") | never opened |
| any missing | — | the normal guarded transaction (P2–P7) | as before |

The boolean `prod_pose_noop_test`, `prod_body_noop` and `prod_scope_noop` keep their meaning, for existing callers.

## 4. Offline evidence

**`test_cpm_app_f01_cross_rig.py`, 228/228 on Python 2.7.5 and 3.10.6** (37 new V checks):
- **Pure:**
  - the limits, and the preservation limits unchanged;
  - position at, beyond and jointly beyond 0.01;
  - rotation at 0.0999°, 0.1001° and 5°, with the inclusive bound at the exact measured angle;
  - NaN, infinite, zero-quaternion, short, missing and text evidence counted as integrity problems;
  - maxima recorded;
  - the reproduction-only and no-work decisions, and Astra's wording.
- **Live** (structural Tails):
  - **Success and mismatch:**
    - an IK joint left 0.05° off verifies, with the maxima logged (it was unverified under the former 0.01°);
    - 0.5° off is a reproduction mismatch with no lockout, and Undo restores exactly.
  - **Integrity still fails with the skeleton inside the envelope:** a corrupted key, a placement drift (0.005 units), a changed preserved scale and a wrong target context are all `committed-unverified`.
  - **Repeat Apply:**
    - a verified repeat is a no-op with no Undo call;
    - a misbent repeat is a no-write mismatch with no Undo call and no P6;
    - an integrity failure or unreadable evidence refuses without Undo;
    - a missing key takes the guarded transaction.
  - **Abort and recovery:** Abort after adapted writes restores exactly; a failed Abort is still recovery-unverified.
  - **Window:** both window paths report the mismatch with Astra's wording.
- **Teeth:** against `39722fb`'s CPM, 201/209: the new sections fail.

**Contract-change test corrections** (stale expectations of the former contract):
- `test_cpm_app_f01_structural_rig.py`: T and N. A deliberately wrong evaluated skeleton with correct inputs is now `reproduction-mismatch`, still never verified.
- `test_cpm_app_f01_jiggle_leaf.py`: E, the same.
- `test_cpm_app_f01_scoped.py`: F, the same. AM2's P7 boundary moved from 0.001 to the envelope: 0.0101 is a mismatch, while 0.0099 and the former boundary case 0.0011 verify.

**Canonical route:** the new names are registered beside their siblings; the unexplained set is unchanged (the same 11
pre-existing names).

**Full regression:** recorded in the commit. Other suites are unchanged: Krystal (body 261/261), Fox and Tails
(structural 337/337, jiggle 142/142), generic and Selected parts (scoped 495/495), legacy left arm (pose_live 109/109,
integration 218/218).

## 5. Replay of the preserved RC4 evidence (separate label)

`real_sfm_qualification/f01_rc4_cross_rig/tools/rc4x_replay.py` writes
`evidence/replay_revised_contract/RC4X_REPLAY.json` and `.md` beside the unchanged `RC4X_VERDICT`.
- **Verdict:** REPLAY PASS (revised contract), 24/24. This is not a native run; the original verdict stays INCOMPLETE.
- **Reference:** each saved record's own skeletal reference against SFM's evaluated bones in the captures, never the adapter.
- **Self-check:** under the former limits the replay reproduces CPM's own logged P7 decisions (A verified; B unverified on exactly `bip_hip_R` and `bip_knee_R`).

| Direction | Captures | Largest error | Former limits | Revised envelope |
|---|---|---|---|---|
| A (RC4 Chest → original) | APPLY, NAV, REDO, NOOP | 0.00022 units, 0.0033° (`bip_lowerArm_L`) | pass | pass |
| B (RC4 Sit → Tails N) | APPLY, NAV, REDO, NOOP | 0.00095 units, 0.0204° (`bip_knee_R`) | fail (`bip_hip_R`, `bip_knee_R`) | pass |

- **Repeat Applies:** both had every key present (`insert 0, update 0`). Under the revised contract they are successful no-ops that never open Undo.
- **Integrity:** all 129 policy-independent checks of the unchanged analyzer pass (keys, neighbours, placement, history, Abort, peers).

The kit tests (`tests/test_rc4x.py`) gain 5 replay checks. 35/36 pass; the remaining check is the template's pin of
the run's own candidate `f51322d3…`, historical and expected after a CPM change. The kit is not edited.

## 6. Short native check (prepared, not run)

`real_sfm_qualification/f01_rc4_reproduction_check/`:
- **Files:** `PROCEDURE.md`, `rc4r.template.json`, `tools/rc4r_tool.py` (the RC4 kit's tool chain), `tools/rc4r_analyze.py` and `tests/test_rc4r.py` (19/19).
- **Capture:** the RC4 kit's pinned capture, with six of its step names.
- **Sequence:** Direction B only. Save `RC4 Sit` from the original Tails, apply it to a new chest-rigged Tails, apply again, and Undo once.
- **Gates:** EVIDENCE, APPLY (CPM's P7 verified with its own maxima inside the envelope), POSTURE (independent, inside the envelope), NOOP (no insert or update, a no-op result, no Undo opened, unchanged history), UNDO (exact restoration) and PEER.

## 7. Remaining limitations

- The envelope is a fixed tolerance; it is not conditioning-aware. A near-degenerate IK pole far from the origin could still exceed 0.1°.
- The left-arm route's new mismatch path is exercised through the shared helper and its unchanged suites, not by a dedicated live mismatch test.
- All evidence is offline. The native short check is prepared and needs the Owner's authorization.
