# F-01 full-body S3: first native qualification (operator procedure)

**Status:** prepared, **not run**. Running it, and every installation change below, needs the Owner's execution
approval. Its only scene writes are the Owner's own posing in disposable session copies and CPM's own Save, Update
and Apply. No session is saved during the run (preparation step 0 saves the destination once, before installation).

**What it shows, as an artist would do it:**
1. Pose Krystal's whole body in SFM.
2. Save it with CPM (Save New).
3. Restart SFM and find the saved pose in the Poses list.
4. Apply it to Krystal in another shot that stands in a visibly different posture.
5. The whole body takes the pose, including tail, ears, fingers, toes and hair.
6. The destination keeps its placement, facial expression, gaze, jaw, proportions and all unrelated animation.
7. Undo and Redo the Apply.
8. Apply the same pose again: nothing is written ("Already matches this pose.").
9. Update an existing saved pose (Update Pose) and apply the updated version over the first (existing keys updated).

It also checks:
- a verified Abort;
- the Clip Editor and body-proportion refusals;
- the legacy left-arm Apply;
- how long a full-body Apply takes, and whether SFM stays responsive.

The comparator turns each of these into a machine check (section 6).

## Identities

| Item | Value |
|---|---|
| Candidate CPM (production source, branch `feature/f01-pose-library`) | `813a9ff29436732f060ddb383af312e0292c303bc8aadef90e7297ad3782bc79` |
| Qualification CPM (`build`; exactly one changed line, `PROD_POSE_REGISTRY_MODE = u"qualification"`) | `45cbaf9515829f7c2ecf18ab71bef11fde5e3f43c9a2c0c19ef61ccbf774e6ef` |
| Pose registry `cpm_pose_profiles_v1.json` (left arm qualified) | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| Body registry `cpm_body_profiles_v1.json` (full body experimental) | `22dcd1599c0556bcb71df0a9b9d14657684173b3bbf557250710a8104a6baa26` |
| Published CPM (installed before and after) | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df` |
| R2 fixture (read-only; every session copy) | `259ea8a614bc9e43e5bde15afdf38e1a1295dffb50b14cf75692df4221a05a2c` |
| S0 observer (unchanged) | `4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4` |
| Legacy pose `NQ1 Pose A` (version 1, Stage D ME-1b) | `4916a7243193306ab7a93dec9fbc988b079c9af4c3bb0e9828a5b2d89cef3541` |

`build` records the wrapper and comparator hashes in `<Q>\staged\IDENTITIES.json`, and `pre` refuses if either has
changed since.

**Fixture facts (from the S0 survey and NQ-1):**
- shot15 runs 0.1667–0.2917 s, shot13 0.3334–0.3751 s and shot10 0.3751–0.5001 s.
- Each holds one separate `Krystal` (`krystal2020.mdl`).
- shot13's FK bone positions equal shot15's exactly, so they are compatible (A1).
- shot10's differ by 1–2 float32 ULP in 19 channels, so CPM refuses it (A1).

**Folders:**
- `<Q>` is the run folder, for example `E:\SFM_U0B_Scratch\f01-full-body-s3`. A run folder is used once.
- `<REPO>` is the F-01 worktree.
- Tools run with the system Python 3:
  `python -I <REPO>\real_sfm_qualification\f01_full_body_s3\tools\s3_tool.py <Q>\s3.json <command>`, shortened
  below to `s3_tool <command>`.

**Stop rule:** at any STOP, stop issuing SFM commands, close SFM **without saving**, run step R1 (restore) and
report. Restore is always permitted and can be re-run. STOP when:
- an observation prints `MISMATCH - STOP`;
- a status differs from the Expected column;
- CPM shows "Pose changes are paused…" or "CPM couldn't confirm…";
- SFM stops responding for more than a minute;
- any step is done out of order.

Never save a session after step 0.

## Preparation (SFM closed)

| # | Action | Expected |
|---|---|---|
| P0 | Copy `s3.template.json` to `<Q>\s3.json`. Fill in this machine's paths. Set `candidate_cpm_sha256` to the candidate value above. Set `LEGACY_POSE` to the Stage D ME-1b evidence copy of `NQ1 Pose A--5273df2209ca.json`. | No `<…>` placeholder remains. |
| P1 | `s3_tool build` | `BUILT: … differs from the candidate in line N only`. The qualification CPM hash equals the table above. |
| P2 | Confirm no `sfm.exe` is running (`tasklist /FI "IMAGENAME eq sfm.exe"`). Then `s3_tool pre`. | `PRE PASS` (a few minutes). `<Q>\sessions\S3_SOURCE.dmx` and `S3_PREPARATION.dmx` exist. On any refusal nothing changed: STOP and report. |

## Step 0: prepare the destination (SFM with the published CPM; CPM not opened)

The destination must look clearly different from the pose, **without** becoming incompatible with it. Rotate FK bones
(tail, ears, fingers, toes, hair); never move them. A1 refuses any FK bone translation. Move only rig handles
(Hip, spine, Neck, Head, Hand, Foot, Collar, Elbow, Knee) and `rig_root`.

| # | Action |
|---|---|
| 0.1 | Start SFM. File > Open `<Q>\sessions\S3_PREPARATION.dmx`. Switch the timeline to the **Motion Editor**. Set the playhead to **0.3750 s** (frame 9, shot13). |
| 0.2 | Pose shot13's Krystal so that **every** group below is clearly different from shot15's R2 posture (about 15° or more):<br>- **spine and hips:** Hip, spine_1–4;<br>- **neck and head:** Neck, Head;<br>- **both arms:** Hand_l/r, Collar_l/r;<br>- **both legs:** Foot_l/r;<br>- **tail:** rotate several tail bones;<br>- **ears:** rotate Ear_l/r;<br>- **fingers:** curl the fingers of both hands. |
| 0.3 | Move and turn `rig_root` (for example 30 units sideways and 45° about the vertical axis). |
| 0.4 | Give her a distinct face and gaze: set a few facial sliders (for example a smile and a brow), open the jaw, and turn the eyes with `eyes_rightleft` / `eyes_updown`. |
| 0.5 | File > Save As `<Q>\sessions\S3_DESTINATION.dmx`. Exit SFM. Confirm no `sfm.exe` remains. |
| 0.6 | `s3_tool inspect` → `INSPECTED`. The destination is pinned. |

## Installation (SFM closed)

| # | Action | Expected |
|---|---|---|
| I1 | `s3_tool install` | `INSTALLED`. The journal is written first. `usermod\scripts\ChadChan3D_CPM\SFM_Character_Preset_Manager.py` is the qualification CPM. Both registries are in `usermod\scripts\SFM Character Tools\`. |
| I2 | `s3_tool seed` | `SEEDED: NQ1 Pose A--5273df2209ca.json` (the legacy left-arm pose, in the run's Poses folder). |
| I3 | `s3_tool check` | `"installation": "qualification"`. |

## Observing

Once per SFM process, in the Script Editor:
`S3_DIR = r"<Q>"; S3_REPO = r"<REPO>"`.

For each step marked **Observe**:
`S3_STEP = "A1"; execfile(S3_REPO + r"\real_sfm_qualification\f01_full_body_s3\observer\F01_S3_Observe.py")`,
changing only the step name.

Each observation:
- takes about a minute;
- prints a `SUMMARY` line, then `S3 STEP <step> (S0-NN): OK`;
- reads only.

`MISMATCH - STOP` means the editor, shot or playhead is not the step's. Never repeat a step name.

Keep `<Q>\OPERATOR_NOTES.txt` open. For B2, B6 and B14, note the time from clicking **Apply Pose** to the final
status, and whether SFM froze or showed "Not Responding".

## Process A: pose, save and update (source session)

| # | Action | Expected |
|---|---|---|
| A0 | Start SFM. Open `<Q>\sessions\S3_SOURCE.dmx`. Switch to the **Motion Editor**. Set the playhead to **0.2083 s** (frame 5, shot15). Open Scripts > SFM Character Tools > Character Preset Manager. Click Refresh Models, select **Krystal**, then the **Poses** tab. Set `S3_DIR` and `S3_REPO`. | `NQ1 Pose A` is listed. **Save New** is enabled. |
| A1 | Observe. | `S3 STEP A1 (S0-01): OK` |
| A2 | Pose **posture A**: change every group of step 0.2 on shot15's Krystal (rotate FK bones, never move them). Do not touch the face or `rig_root`. Observe. | |
| A3 | **Save New**, name `S3 Pose A`, Save. Observe. | `Pose saved: S3 Pose A.` |
| A4 | Pose **posture B**: change at least the arms, legs and tail visibly from A. Observe. | |
| A5 | **Save New**, name `S3 Pose B`, Save. Observe. | `Pose saved: S3 Pose B.` |
| A6 | Pose **posture C**: change at least the head, arms and tail again (the update content). Observe. | |
| A7 | Select `S3 Pose B`, click **Update Pose**, then confirm. Observe. | `Pose updated: S3 Pose B.` |
| A8 | Exit SFM **without saving**. Confirm no `sfm.exe` remains. Then `s3_tool library A`. | `LIBRARY A: 3 files recorded`. |

## Process B: restart, apply, undo, update, refusals, legacy (destination session)

The source session is never opened in this process.

| # | Action | Expected |
|---|---|---|
| B0 | Start SFM. Open `<Q>\sessions\S3_DESTINATION.dmx`. Switch to the **Motion Editor**. Set the playhead to **0.3750 s** (frame 9, shot13). Open CPM. Click Refresh Models, select **Krystal**, then the **Poses** tab. Set `S3_DIR` and `S3_REPO`. | `S3 Pose A`, `S3 Pose B` and `NQ1 Pose A` are listed, loaded from disk. |
| B1 | Observe (baseline). | |
| B2 | Select `S3 Pose A` and click **Apply Pose**. Wait until the status leaves `Checking the applied pose...`. Note the time. Look at her. Observe. | `Pose applied: S3 Pose A.` Edit > Undo names `Apply Pose S3 Pose A`. The whole body takes posture A: spine, head, arms, legs, tail, ears, fingers, toes and hair. Her place in the scene, facial expression, gaze, open jaw and proportions are unchanged. |
| B3 | Click the viewport, then press **Ctrl+Z** once. Observe. | She returns to the step-0 posture. |
| B4 | Press **Ctrl+Y** once. Observe. | Posture A again. |
| B5 | With `S3 Pose A` selected, click **Apply Pose** again. Observe. | `Already matches this pose.` No new Undo entry. |
| B6 | Select `S3 Pose B` and click **Apply Pose**. Wait for the final status. Note the time. Observe. | `Pose applied: S3 Pose B.` She takes **posture C**, the updated content. |
| B7 | In the Script Editor run `import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"`. Then select `S3 Pose A` and click **Apply Pose**. Observe. | `The pose couldn't be applied. Nothing was changed.` She still shows posture C, and Undo still names `Apply Pose S3 Pose B`. |
| B8 | Set the playhead to 0.2083 s, then back to **0.3750 s**. Observe. | Posture C persists. |
| B9 | Switch the timeline to the **Clip Editor** without moving the playhead. Observe. | |
| B10 | Select `S3 Pose A` and click **Apply Pose**. Observe. | Refused: `Switch the timeline to the Motion Editor to apply a pose. Nothing was changed.` |
| B11 | Switch to the **Motion Editor**. Set the playhead to **0.4167 s** (frame 10, shot10). In CPM click Refresh Models, select **Krystal**, then the Poses tab. Observe. | |
| B12 | Select `S3 Pose A` and click **Apply Pose**. Observe. | Refused: `This pose uses different bone positions and can't be applied safely.` A different refusal that also changes nothing is a finding, not a STOP. |
| B13 | Set the playhead to **0.2083 s** (frame 5, shot15). In CPM click Refresh Models, select **Krystal**, then the Poses tab. Observe. | |
| B14 | Select `NQ1 Pose A` and click **Apply Pose**. Note the time. Observe. | `Pose applied: NQ1 Pose A.` Only the left arm moves (legacy left-arm path). |
| B15 | Click **Apply Pose** again. Observe. | `Already matches this pose.` |
| B16 | Click the viewport, then press **Ctrl+Z** once. Observe. | The left arm returns. |
| B17 | Press **Ctrl+Y** once. Observe. | The left arm takes the pose again. |
| B18 | Exit SFM **without saving**. Confirm no `sfm.exe` remains. | |

## R: evidence, restoration and verdict (SFM closed; always)

| # | Action | Expected |
|---|---|---|
| R0 | `s3_tool library B` | `LIBRARY B: 3 files recorded` |
| R1 | `s3_tool collect-logs` | `LOGS COLLECTED: N files` (the CPM logs since `pre`, as verified copies) |
| R2 | `s3_tool restore` | `RESTORED`:<br>- the published CPM `ccbed9d7…` is back;<br>- both registries are removed;<br>- the run's Poses folder is moved into `<Q>\evidence\library_poses`;<br>- housekeeping and `.pyc` files are restored;<br>- every inventory equals its pre-run baseline. |
| R3 | `s3_tool check` | `"installation": "published"` |
| R4 | `s3_tool compare` | `<Q>\evidence\S3_VERDICT.md`, ending `verdict: PASS`. |

Return `<Q>\observations\`, `<Q>\evidence\`, `OPERATOR_NOTES.txt` and the SFM console text.

**Rollback at any point:** close SFM without saving, then run `s3_tool restore`; re-run it if it is interrupted.
- If `restore` refuses, the published CPM's verified backup is `<Q>\pre_run\backup\`, and the installation journal
  is `<Q>\pre_run\install_journal.json`. Report before changing anything by hand.
- A paused CPM ("Pose changes are paused…") needs only an SFM restart after restore. The pause is never cleared
  within the SFM process that set it.

## 6. Expected evidence (the comparator's checks)

| Requirement | Checks (`S3_VERDICT.json`) |
|---|---|
| Every observation valid, read-only, the qualification CPM loaded | `observed.*`, `valid.*`, `cpm.*` |
| **Save** captures the visible pose and changes nothing in the scene | `save.version_2_full_body`, `save.written_set` (278 channels), `save.A_captures_the_visible_posture` (every bone within 0.001 units and 0.01° of the record, relative to `rig_root`), `save.*_writes_nothing_to_the_scene` |
| **Update Pose** replaces the saved posture in place | `update.B_holds_the_updated_posture`, `update.B_no_longer_holds_the_saved_posture`, `update.in_place`, `update.writes_nothing_to_the_scene` |
| **Restart and retrieve** | `process.restart_between_save_and_apply` (different SFM processes), `process.sessions`, `library.records_unchanged_by_the_apply_process` |
| A **visibly different** destination (an Apply that moves nothing proves nothing: PS-1b5) | `distinct.destination_differs_from_A_in_every_group` (≥ 5° in spine and hips, neck and head, arms, legs, tail, ears, fingers), `distinct.B_differs_from_A_visibly` |
| **Apply reproduces the full body** | `apply_A.written_channels_hold_the_record`, `apply_A.full_body_posture_reproduced`. Every posed bone must be at the record's posture in the destination's own placement. Jaw, tongue and the passive twist bones keep their own local pose. Bone scales, the model and `rig_root` must be unchanged. |
| **Preservation** | `apply_*.other_instance_channels_unchanged` (every non-written channel: flexes, eyes, jaw, tongue, `rig_root`, pole orientations, scale and weights), `apply_*.facial_gaze_and_other_controls_unchanged`, `apply_*.unrelated_animation_unchanged` (every channel outside the instance, every shot) |
| **One owned Undo; Undo / Redo** | `apply_*.one_owned_undo_entry`, `undo.restores_the_baseline`, `redo.restores_the_applied_pose` |
| **Re-apply without writes** | `repeat.true_noop` (the whole-document digest and the Undo state unchanged), `log.repeat_is_noop` |
| **Existing keys updated** | `apply_B.existing_keys_updated_in_place` (same key times and counts), `apply_B.updated_posture_reproduced`, `log.apply_B_updates_only` |
| **Verified Abort** | `abort.verified_nothing_changed`, `log.abort_verified` |
| **Refusals write nothing** | `refusal.clip_editor_writes_nothing`, `refusal.fk_positions_write_nothing`, `log.refusals_wrote_nothing` |
| **CPM's own deferred verification**; no uncertainty | `log.apply_A_verified_by_cpm` (owned P6, P7 verified), `log.no_recovery_or_uncertainty` |
| **Legacy left arm** | `legacy.*`, `log.legacy_*` |
| **Performance** | Per full-body Apply, from the CPM log's millisecond stamps: preflight, transaction (P1→P6), blocking (start→P6), deferred verification (P6→P7) and whole. `responsive` if the worst is ≤ 5 s; `finding` up to 30 s (PASS, for the Owner's decision); `fail` above 30 s |
| **Restoration** | `restore.published_and_inventories_equal`, `sessions.destination_not_saved_during_the_run` |

The verdict is PASS only if every check passes and performance is `responsive` or `finding`.

**Not provoked natively:** recovery-unverified, the recovery pause and committed-unverified. Provoking them would
leave a scene that CPM itself cannot confirm. They are covered offline (full-body Y.*, legacy U.*, integration C6).
