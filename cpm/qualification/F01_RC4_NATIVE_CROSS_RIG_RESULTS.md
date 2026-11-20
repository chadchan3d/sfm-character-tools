# F-01 RC4 native two-direction Tails cross-rig qualification: results and investigation

**Authority:** "F-01 RC4 — Native Cross-Rig Qualification GO" (checkpoint `5fee7a6`, CPM `f51322d3…`) and "F-01 RC4 —
Native Results and Verification Failure". Kit: `real_sfm_qualification/f01_rc4_cross_rig/` (unchanged). Run folder:
`E:\SFM_U0B_Scratch\f01-rc4-cross-rig-r1` (all evidence preserved, not committed). Qualification build `df6c4326…`.

| Result | Value |
|---|---|
| **Automated verdict (unchanged analyzer)** | **INCOMPLETE**, 129/132 checks. `RC4X_VERDICT.json` `3269609a…`, `.md` `92e898d2…` |
| **Owner visual observations** | Direction A looked successful. Direction B looked visually correct, but CPM showed the committed-unverified warning, at Apply and again at the repeated Apply. Abort: "The pose couldn't be applied. Nothing was changed." Save New feedback and Pose Info's Rig row were not reported by the Owner |
| **Restoration** | **RESTORED.** Published CPM `ccbed9d7…`, both registries absent, library cleanup exact (`files_equal_pre`, `folders_equal_pre`), no inventory problem. The R2 fixture and both session copies are unchanged (never saved) |

## 1. Gates

Passed: PREP, SAVE, ADAPT, A_POSTURE, B_APPLY, B_POSTURE, B_HISTORY, ABORT and PEER.

Failed:
- **EVIDENCE** `log.no_unverified_uncertain_failed_abort_or_lockout_result`: Direction B's two `P7-unverified` / `committed-unverified` outcomes;
- **A_APPLY** `apply.p7_verified_in_the_cpm_log`: fewer than two P7-verified results, because B's were unverified;
- **A_HISTORY** `noop.reported_by_cpm_twice`: B's repeated Apply wasn't a reported no-op (section 3).

Those two checks count both directions but are filed under the A gates. That is an analyzer labelling flaw; the
analyzer was not changed. All three failures have the single cause in section 2.

## 2. Direction B's P7 failure: the exact cause

CPM's log (op 15): `PROD_POSE_BODY-P7-unverified {"problems": ["bone bip_hip_R", "bone bip_knee_R"]}`.

**Measured independently** from SFM's evaluated bones (destination at B_APPLY against the saved source, each relative to
its own `rig_root`):

| Bone | Angle | Position |
|---|---|---|
| `bip_knee_R` | **0.02036°** | 0.000953 units |
| `bip_hip_R` | **0.02033°** | 0.000013 units |
| next largest (arms, left leg) | ≤ 0.0018° | ≤ 0.00014 units |

- P7's unchanged limit is 0.01° and 0.001 units, so it detected a real evaluated deviation; the verifier was not wrong.
- The deviation is about twice the angle limit; the knee shift is just inside the position limit.
- The analyzer's usability bound (0.05 units, 0.5°) passes.

**Mechanism: a near-degenerate IK pole amplifying float32 placement rounding.**
- The right leg is a two-bone IK chain (`bip_hip_R` → `bip_knee_R` → `bip_foot_R`), targeting `rig_foot_R`, with pole `rig_knee_R` (parent `rig_foot_R`).
- In the original Tails' sitting pose, the pole lies only **0.433 units** from the hip–foot axis (chain 6.66 units). The left leg's pole is 2.80 units off, and Tails N's poles in its own pose are 7–9 units off.
- These controls are not adapted: they are copied exactly. The placement-relative pole nevertheless differs by **5.6×10⁻⁵ units** between source and destination. That is float32 world-space resolution at the placements involved (≈ 504 and ≈ 685 units from the origin; float32 steps there are about 6×10⁻⁵).
- With the pole nearly on the axis, that rounding tilts the IK plane by **0.0256°**, and the hip and knee follow by 0.020°. The foot, the IK target, matches (0.00005 units). The left leg, under the same rounding, tilts 0.0012°.
- The right-leg rig offsets of the two rigs differ by at most 1.5×10⁻⁷° (measured), so the offset bounds play no part.

**Practical significance:** a 0.02° swing of the right thigh and shin about the hip–foot line, and a 0.001-unit knee
shift. That's invisible at normal viewing, consistent with the Owner's report. It is a genuine evaluated difference,
not a verification defect. It arises from the saved pose's geometry and placement-dependent float32 evaluation, not
from the adaptation: no adapted channel is involved, and the chest conversion in both directions reproduced
`bip_spine_3` within 0.00006 units and 0.00002°. It is likely that applying this sitting pose to a same-rig Tails
placed elsewhere would behave the same; that is inferred, not observed.

## 3. B_NOOP: a new operation, not a retained warning

CPM's log (op 16): P1 `{"actions": {"none": 238}, "noop": false}`, then P6 `{"owned": true, "written": 0}`, then
`P7-unverified` with the same two bones, and outcome `committed-unverified`.

- **Why it wasn't a no-op:** CPM's no-op rule requires every key already present **and** the skeleton already verifying. The keys were present but the skeleton didn't verify.
- **What happened instead:** CPM opened its Undo transaction, wrote nothing and verified again, so the warning was raised anew.
- **No extra entry was left:** the authored state and Undo state at B_NOOP equal B_REDO's (`noop.writes_nothing_and_adds_no_entry` passed). B_FINAL's single Undo restored Tails N exactly to its own pose. So no empty entry remained.
- **Safe but confusing:** nothing was written, and the Undo history was unaffected.

## 4. Authored state, placement, history and Abort

| | Direction A (RC4 Chest → original, 22 controls) | Direction B (RC4 Sit → Tails N, 23 controls) |
|---|---|---|
| Adaptation | `bip_spine_3` → FK; neck and collars re-attached | `rig_chest` solved; neck and collars re-attached |
| Actual destination offsets vs record | 0.00130° max, 6.03×10⁻⁶ units max (76 compared) | the same |
| Channels changed | only drafted written channels, rig handles and FK bones; leaves never authored | the same |
| Neighbouring keys | 336 kept unchanged, one key at the mapped tick | 342 kept unchanged |
| Independent posture, largest | 0.00022 units, **0.0033°** (P7 verified) | 0.00095 units, **0.0204°** (P7 unverified) |
| Converted `bip_spine_3` | 0.000057 units, 0.0000175° | 0.000039 units, 0.0000187° |
| Placement, facing, FK offsets | unchanged | unchanged |
| Navigation | pose held; no time-selection entry | pose held; no time-selection entry |
| Undo, Redo, final Undo | exact | exact |
| Repeated Apply | reported no-op | not a no-op (section 3); nothing written |

- **Abort:** a single injected failure after 238 adapted writes; `BODY-abort-verified {"problems": [], "redo_cleared": false}`. The original Tails was exactly as at A_FINAL, Tails N and the Undo state exactly as at B_NOOP, and the fault slot was consumed.
- **Peers:** the Fox was unchanged at every capture; each direction's source was unchanged during its Apply.
- **Direction A, verified independently:** every A gate check passed except the two cross-direction counts above. Direction A qualifies on its own evidence.

## 5. UI evidence (native)

- **Pose Info Rig:** both saves recorded the scene rig in the local sidecar (`RIG-recorded`): `RC4 Chest` → `rig_biped` (`rig_biped_milestailsprower2`), and `RC4 Sit` → `rig_biped` (`rig_biped_milestailsprower1`).
- **Not reported by the Owner:** what Pose Info showed, and whether Save New's feedback was visible.

## 6. Options (for review; no change made)

1. **Keep P7 as it is**, and document the limitation: a pose whose IK pole is nearly collinear with its chain may not verify after transfer to a differently placed character. This is likely route-independent.
2. **Conditioning-aware verification** of IK start and mid joints: the angular allowance scales with the chain's pole conditioning and float32 placement resolution, with a fixed cap. This changes the verification contract and needs Astra's adjudication.
3. **Repeat Apply (independent of 1 and 2):** when every planned key is already present but the skeleton doesn't verify, refuse before opening a transaction, saying the pose is already applied but couldn't be verified. This replaces the empty transaction and the repeated warning. It's small and stays on the safe side, but it changes the no-op semantics, so review is needed.

Smallest justified correction:
- for the verification result: none, under the current contract (option 1);
- for the repeat-Apply behaviour: option 3.
