# F-01 RC4: short native reproduction check, results

**Authority:** "F-01 RC4 — Short Native Reproduction Check GO" (checkpoint `2eacd7e`, CPM `b89af5a8…`). Kit
`real_sfm_qualification/f01_rc4_reproduction_check/` (unchanged). Run folder `E:\SFM_U0B_Scratch\f01-rc4-reproduction-r1`
(evidence preserved, not committed). Qualification build `d7454891…`.

| Result | Value |
|---|---|
| **Automated verdict (unchanged analyzer)** | **AUTOMATED PASS, 55/55**: EVIDENCE, APPLY, POSTURE, NOOP, UNDO and PEER. `RC4R_VERDICT.json` `9b2d0a89…`, `.md` `d634df11…` |
| **Owner visual verdict** | **PASS.** RC4 Sit applied and looked correct; the repeat was a no-op with no new Undo entry (Edit still read *Undo Apply Pose RC4 Sit*); Undo restored the original pose and *Redo Apply Pose RC4 Sit* was available; no warning or recovery message; all six captures `errors none` |
| **Restoration** | **RESTORED.** Published CPM `ccbed9d7…`, both registries absent, library exactly as backed up, no inventory problem; the R2 fixture and both session copies unchanged (never saved) |

## Measurements

| | Value |
|---|---|
| Destination | `milestailsprower2` (`rig_biped_milestailsprower2`, 23 controls, 36 constraints); source `milestailsprower1` (22 controls, 34 constraints) |
| CPM's P7 (revised envelope 0.01 units, 0.1°) | verified; 124 outputs; largest 0.000915 units and **0.0199°**, both at `bip_knee_R` |
| Independent posture (SFM's evaluated bones relative to the destination's `rig_root`, against the source at Save) | 124 bones; largest 0.000915 units and **0.0199°**; worst `bip_knee_R` 0.0199°, `bip_hip_R` 0.0199°, `bip_upperArm_L` 0.0014° |
| Placement, facing, direct-bone offsets | unchanged |
| Keys | only drafted written channels changed; 342 neighbouring keys unchanged; one key at the mapped tick |
| Repeat Apply | P1 `insert 0, update 0, none 238`; CPM no-work result `no-op`; no Undo opened (one P6 in the run); authored state and history equal to B_APPLY |
| Undo | B_BASE restored exactly (authored state and skeleton); Redo entry *Apply Pose RC4 Sit* |
| Peers | the Fox and the original Tails unchanged at every capture |

The right-leg deviation the RC4 run reported (0.0204°, near-collinear IK pole) recurs at 0.0199°. It is inside the
revised envelope and is verified as intended.

## Remaining items

- No release blocker found by this check.
- Not confirmed natively by the Owner: Save New's "Checking the character before saving." feedback and Pose Info's Rig row. The Rig sidecar was recorded natively in the RC4 run.
- RC4 is not packaged, signed or released. The RC4 run kit's own test keeps its one historical pin failure (35/36).
