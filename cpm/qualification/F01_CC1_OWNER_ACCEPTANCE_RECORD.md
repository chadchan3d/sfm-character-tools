# F-01 CC-1 Owner acceptance record

**Disposition (Owner, 2026-11-04):** **CC-1 — FUNCTIONAL PASS / ACCEPTED WITH DOCUMENTED PROCEDURAL DEVIATIONS.**
The substantive non-flat Save/Apply consistency evidence is accepted and fulfils Stage D production requirement 1. The
three procedural deviations below are recorded and are not product defects. The original comparator FAIL and all
native evidence are preserved unchanged. No further CC-1 testing or Astra adjudication is required.

**Run:** CC-1 native Save/Apply capture consistency, 2026-11-04, one SFM process (pid 22540), qualification build
`152ce6aa…` of the accepted Stage D candidate `18849e5f…` (commit `d8e6600`, unchanged). Disposable copy of R2
(`259ea8a6…`). `<Q>` below is the CC-1 run folder in the owner's local archive.

**Comparator verdict (preserved, unmodified):** `FAIL`. Comparator `cc1_compare.py` `bd523b08…`, thresholds unchanged;
`<Q>/evidence/CC1_VERDICT.json` `4c987527…`. All checks ran; the three problems are listed in section 1.


## 1. Procedural deviations

| # | Deviation | Comparator effect |
|---|---|---|
| D1 | OBS-01 (source baseline) was captured in the **Clip Editor** (mode 3, clock 50299), not the Motion Editor (mode 2, clock 50208). OBS-02 to OBS-08 are all mode 2. | Problems 1 and 2: `not Motion Editor (2) throughout`; `src_base: mapped tick 50208 / clock [50299]`. |
| D2 | A first **Apply Pose B in the Clip Editor** (22:40:08Z) was refused by the gate before writing. The operator then switched to the Motion Editor, and the second Apply (22:40:19Z) verified. The procedure said no repeated Apply attempts. | None (not visible to the comparator); found in the CPM log. |
| D3 | The **Save status** observed at OBS-04 was `Ready to apply "CC1 Pose C".`, not `Pose saved: CC1 Pose C (Left arm).` | Problem 3: `Save status 'Ready to apply "CC1 Pose C".'` |

## 2. Functional measurements (`CC1_VERDICT.json` findings; every check other than the three above passed)

| Check | Measured | Requirement |
|---|---|---|
| Non-flat: source arm at the Save frame (shot10, 0.4583 s, clock 50624) vs Pose B | 2.8101°, 5.1449°, 2.8184° (upper arm, lower arm, hand) | at least one bone ≥ 1.0° |
| Non-flat: same vs the held pose | 78.547°, 26.0162°, 15.3816° | at least one bone ≥ 1.0° |
| Non-flat rig (vs Pose B / vs held) | Hand position 0.5106 / 24.2903; hand orientation 1.8136° / 86.2788°; elbow position 0.261 / 12.4162 | every written channel differs from both |
| Source rig = log value at the Save frame | all three channels | required |
| Pose C record oracle vs observed source skeleton | 0.0°, 0.0°, 0.0° | ≤ 0.01° |
| Record source | shot10, `t_doc_ticks` 4583 | the Save frame |
| Save and Undo | OBS-03 and OBS-04 Undo identical (top `Modify Head Time`) | unchanged |
| Destination Apply C (shot15, 0.2083 s, clock 50208) | One key inserted per written channel at 50208; elbow orientation unchanged; `P6-refresh` then `P7-verified`; status `Pose applied: CC1 Pose C (Left arm).`; top Undo `Apply Pose CC1 Pose C` | automatic, exact |
| Destination arm vs Pose C record and vs observed source arm | 0.0003°, 0.0005°, 0.0005° (both) | ≤ 0.01° |
| Destination rig = keys at 50208 | all three channels | 1e-4 position, 1e-3 orientation |
| Navigation (0.2500 s, then back to 0.2083 s) | keys unchanged; arm 0.0003°, 0.0005°, 0.0005° | preserved |
| Unrelated integrity | unrelated authored channels, bones (local and world, arm descendants excluded), model placement and facing unchanged at source and destination; source and destination are distinct instances | unchanged |

## 3. The refused Clip Editor Apply (D2) made no changes

- CPM log: `PROD_POSE_CHANNEL_CLOCK t_chan=50208 reported=… 50299`, then
  `ProdPoseError: Switch the timeline to the Motion Editor to apply a pose. Nothing was changed.`, raised by
  `prod_pose_apply_gate` inside the P1 preflight, then `PROD_OPERATION_OUTCOME … outcome=u'failed-precommit'` with
  `native_committed: False`, `last_phase: BEGIN`, `durable_persisted: False`. No `PROD_POSE_P1` plan, P3 or P6 line was
  logged for that operation.
- OBS-01 (22:39:40Z) predates both Apply attempts, so OBS-01 to OBS-02 covers the refusal and Apply B together. The
  only authored difference is Apply B's: exactly one inserted key per written channel (Hand_l position 4 to 5 keys,
  Hand_l orientation 4 to 5, Elbow_l position 5 to 6), elbow orientation unchanged (6 keys), unrelated channel digests
  identical.
- Undo: OBS-01 `can_undo: False` (empty); OBS-02 top `Apply Pose NQ1 Pose B`, `can_redo: False`.
- Incidentally, this is native evidence that the Stage D gate refuses before writing in the Clip Editor.

## 4. Save completed successfully (D3)

- CPM log, Save Pose operation 5: `PROD_POSE_CHANNEL_CLOCK t_chan=50624` (all three channels 50624), then `durable-commit`
  and `durable-verified` for `preset_id 0444f56b36772bf3ce82d0c098d61344`, then outcome `verified` (22:40:54Z).
- The record exists: `CC1 Pose C--0444f56b3677.json` (`ea644017…`), name `CC1 Pose C`, source shot10 / 4583, and it
  matches the observed source skeleton exactly (section 2). Apply C from it reproduced the pose.
- Product code sets `Pose saved: %(name)s (%(parts)s).` at the end of the Save transaction. The post-Save list refresh
  blocks signals, so it cannot change the status. The observed text `Ready to apply "CC1 Pose C".` is the Poses-tab
  handler's message. The log shows UI activity (Master-path reads, 22:41:01Z to 22:41:22Z) between the Save and OBS-04
  (22:41:28Z), consistent with a tab switch before observing. The operator's exact action is not recorded.

## 5. Why the Clip Editor baseline does not invalidate the flat-hold comparison (D1)

- **Authored data is the same in either editor.** The baseline keys and unrelated-channel digests are document data;
  the Apply B insertion check used them and passed.
- **The held pose is the same at both clocks.** In OBS-01 each written channel and the elbow orientation are bracketed
  by keys at 30000 and 70415 whose values are identical, so the channel is flat across [30000, 70415]. Both 50208
  (Motion Editor) and 50299 (Clip Editor) lie inside it, and the observer recorded the rig equal to the log value at both
  ticks (`at_converted` and `at_clock` true). The baseline arm used in the held-pose comparison is therefore what the
  Motion Editor would have shown at 50208. Supplementary check: `<Q>/evidence/CC1_OBS01_ASSESSMENT.json` (`1868cefd…`).
- **The write was gated in the Motion Editor.** Apply B's P1 and P2 pinned mode 2 and clock 50208 before
  `StartUndo`, P7 verified at `t_chan` 50208, and OBS-02 records mode 2 and clock 50208.
- **The held-pose margin is large.** The Save-frame arm is 15.4° to 78.5° from the held pose, against a 1.0°
  requirement.
- **What is not evidenced:** an observation showing the switch to the Motion Editor came before CPM was used.

## Evidence index (owner's local archive, not committed)

`<Q>/observations/OBS-01..08.json`; `<Q>/evidence/CC1_VERDICT.json`, `restore.json` (`a0154401…`, `RESTORED`; published
CPM `ccbed9d7…`; four protected inventories equal their baselines), `CC1_OBS01_ASSESSMENT.json` and its script,
`logs/CPM - 2026-11-04_22-39-18Z - pid22540 - da6e8e - 001.log` (`f5acc6ac…`),
`library_poses/krystal2020--7d2aee52ef3a/` (Pose C `ea644017…`, Pose B `87e61f60…` unchanged).

Following this acceptance, Krystal's left-arm mapping is promoted to `qualified` in the production registry (F-01
production registry integration); every other mapping stays experimental.
