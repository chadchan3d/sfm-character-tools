# F-01 K2: Krystal version 2 Full body native integration check: results and Owner acceptance

**Date:** 2026-11-14. **Authority:** Blueprint R4 section 5 and section 12 work order K; Owner authorization "F-01 Pose
Library — K2 Native Integration Trial, OWNER AUTHORIZATION: GO"; comparator correction authorized by "F-01 K2 —
Proposed Comparator Correction and Evidence Replay"; closure by "F-01 — Close K2 and Implement Approved UI
Corrections".

**Disposition: K2 ACCEPTED by the Owner.** The original comparator verdict **FAIL (54/55)** is preserved unchanged.
The revised A1 replay of the same evidence is **PASS (56/56)**. The two verdicts are separate, linked records. Krystal
version 2 Full body is **not promoted**: the production build still refuses it (`rig-driven`) and the body registry's
mapping status is unchanged (experimental). Promotion is a separate Owner decision.

## 1. Identities

| Item | Identity |
|---|---|
| Candidate CPM (K1, `3297ac0`) | `3984e1e1d5d2018202fa551700564da6796cc1063c2be7a32112ad023db5ae9c` |
| K1 qualification build (line 42182 only) | `37b0cce608062f2a7e03bab03ee4e590fc3f8c395a2c300538df44e3893b1868` |
| Pose / body registries | `f445d5ef…` / `22dcd159…` |
| Source session `K2_SOURCE.dmx` (R2 fixture copy) | `259ea8a6…` |
| Destination `K2_DESTINATION.dmx` (S3 prepared destination copy) | `61df8bcd…` |
| Published installation before and after | v1.0.0, CPM `ccbed9d7…` |
| Kit | `real_sfm_qualification/f01_k2_krystal/` at `128f9f1`; S3 observer wrapper and UI smoke check unchanged |
| Run folder (raw evidence, not committed) | `E:\SFM_U0B_Scratch\f01-k2-krystal-r1` |

## 2. Executed sequence (no deviation from `PROCEDURE.md`)

- **Preparation (SFM closed).** `build` refused to overwrite the dry run's `staged/`; the staged files were verified
  by hash instead (qualification CPM `37b0cce6…`, differing from the candidate in line 42182 only; registries equal
  their pins). `pre` PASS (backups, four inventories, both session copies). `install`; `check` = qualification.
- **Process A (Owner):** A1 OK; Save New offered Full body with Save enabled; `Pose saved: K2 Pose.`; A2 OK; exit
  without saving. `library A`: one record `K2 Pose--ac9d4962a2ae.json` `7c53209a…` (version 2, `full_body`,
  `body_krystal_v1`, source shot15).
- **Process B (Owner, new SFM process):** B1 OK; Pose Info showed the version 2 record; UI smoke check: Apply Pose
  enabled. `precheck` (read-only): COMPATIBLE (278 written channels, 124 pinned FK positions, plan 278 inserts) and
  DISTINCT (arms 171.3°, legs 97.4°, tail 95.2°, ears 50.3°, spine and hips 35.6°, neck and head 32.0°). Apply, Undo,
  Redo, Hip rotation, Update Pose: B2–B6 OK. Exit without saving.
- **Closeout (SFM closed):** `library B` (record `bf8fc5bc…` and its Update backup `.bak` `7c53209a…`),
  `collect-logs` (two CPM logs), `restore` (`RESTORED`, `inventory_problems: []`), `check` (published `ccbed9d7…`,
  both registries absent), `compare`. Both sessions unchanged (never saved).

## 3. Verdicts

| Record | File (run folder `evidence\`) | SHA-256 | Result |
|---|---|---|---|
| Original | `K2_VERDICT.json` / `.md` | `ddd98ce6…` / `263befbb…` | **FAIL**, 54/55: `apply.written_channels_hold_the_record` (`Ear_r_p`, `bip_tail02_p`) |
| Revised A1 replay | `K2_VERDICT_REVISED_A1.json` / `.md` | `ab423739…` / `40797711…` | **PASS**, 56/56; names the original by SHA-256 |
| Diagnosis | `K2_FINDINGS.md` | `1fbf5f05…` | links both |

**Measured.** Apply wrote the destination's own values to the two FK-position channels, which differ from the saved
values by 1.58e-5 and 2.58e-5 (limit 0.00005). The read-only precheck predicted exactly this, and CPM's log records
`PROD_POSE_BODY-A1 {"differing": ["Ear_r_p", "bip_tail02_p"], "max_distance": 2.5787e-05, "pinned": 124}`.

**Cause of the original FAIL: a comparator defect.** The check, inherited unchanged from `s3_compare`, compared every
written channel with the saved value. The revised A1 contract (`F01_FULL_BODY_S1_CHECKPOINT.md` section 10) keeps
the destination's FK positions. S3 run 3 verified this only with an interim check, so the defect was latent.

**Correction** (`k2_compare.py`; the shared `s3_compare.py`, CPM, tolerances and mapping are unchanged). The pinned
channels are the record descriptor's `fk-written` positions (124). Each one's expected value is B1's observed value at
the mapped tick, not CPM's report. The saved/destination distance must be at most 0.00005 for `body_krystal_v1`,
compared as float32, and exact for every other profile, with finite float32 values. The value after Apply must equal
B1's exactly. Every other written channel is still compared with its saved value. The failing check is replaced by
`apply.written_channels_hold_the_planned_values` and `apply.pinned_fk_positions_within_the_revised_A1_limit`; every
other check is unchanged. `--replay-revised-a1` writes separately named files, refuses without the original verdict,
and never overwrites. The replay ran with the working-tree comparator `9e67e9d6…`; the 31 original evidence and
observation files were byte-identical before and after.

**Kit tests** (`tests/test_k2.py`, Python 3.10.6): 11/11. The native two-channel case passes. These are rejected,
each on its own check: a saved value transferred into a pinned channel, a wrong authored orientation, a wrong handle
position, an extra key, a write to an unrelated channel, a 0.0001 difference, and a record without channel
classification. A difference exactly at the limit is accepted and the next float32 above it rejected; other profiles
are exact; non-finite and non-float32 values are rejected. Replay safety is covered.

## 4. Native results (measured, with the Owner's observations kept separate)

| Area | Machine result | Owner observation |
|---|---|---|
| Save Full body (v2 route through the PS-2 dialog, K1 dispatch) | 278-channel record capturing the source posture; nothing written to the scene; `log.save_verified` | Full body offered, Save enabled, saved |
| Reopen in a new process | the record saved in Process A is the one applied; Apply enabled | Pose Info correct |
| Apply | planned values written, one key each at the mapped tick; posture reproduced relative to the unchanged placement handle; model state, scales, other channels, face, gaze and unrelated animation unchanged; one owned Undo entry; BODY-P6 owned, BODY-P7 verified | "The applied Krystal Full body pose looked correct and useful." |
| Undo / Redo | exact destination; exact applied pose | OK |
| Update | writes nothing to the scene; in place (identity, creation time); holds the posture with the Hip change | OK |
| Performance | Apply 4260 ms (preflight 1743, transaction 1485, deferred verify 1032): responsive (≤ 5000 ms) | about 4 s |
| K1 generic-inventory fallback | 0 log lines in both processes: not engaged | — |
| Recovery or uncertainty | none | none |
| Restoration | published `ccbed9d7…`; registries removed; four inventories equal their baselines | — |

## 5. UI findings (Owner-approved; implemented separately, not in the K2 build)

- Save Pose v2 summary "Facial expressions, gaze and the character's place in the scene are not saved." → "Facial
  expressions and the rootTransform are not saved."
- Pose Info: Name, Type, Model, Model path, Source shot, Source project, Saved, Updated, Not included; "Facial
  expressions, rootTransform"; Source project for new saves, "Not recorded" otherwise.
- Confirmation dialogs (Update Pose had redundant wording) and Trash dialogs: the Owner's standard pattern.

## 6. Remaining findings and release implications

- The S3 comparator (`s3_compare.written_problems`) keeps the latent defect for its own historical runs; it is not
  changed. Any future kit that reuses it for a v2 Apply must use the revised A1 expectation.
- Krystal v2 Full body is natively integrated through the current product path. Promotion (registry status, the
  production refusal) needs a separate Owner decision. The UI corrections need the Owner's visual review, and no
  native acceptance has been run on the UI build.
- PS-2's open findings (Body Preset `committed-unverified`, duplicate-model digest, v1.0.0 topology refusal) are
  unaffected by K2.
