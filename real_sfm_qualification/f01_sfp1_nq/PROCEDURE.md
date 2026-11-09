# F-01 SFP-1 Selected parts: bounded native qualification (operator procedure)

**Status:** prepared, **not run**. Running it, and every installation change below, needs the Owner's execution
approval. Its only scene writes are the Owner's own posing in disposable session copies and CPM's own Save, Update and
Apply. No session is saved during the run; preparation step 0 saves the destination (and the optional prop session)
once, before installation, with the published CPM installed and CPM not opened.

**What it shows, as an artist would do it (Krystal, rigged, the R2 fixture):**
1. Pose Krystal's left fingers and thumb, and save only them (Save New → Selected parts).
2. Save a second finger pose and update it in place (Update Pose).
3. Restart SFM, open a different session, and find both poses in the Poses list.
4. Apply the grip to Krystal in another shot whose wrist, arm and fingers are posed differently: the fingers take the
   grip inside the destination's own wrist; the wrist, arm, body, face and gaze stay as they were.
5. Undo and Redo; apply again (nothing written); apply the updated pose (existing keys updated); a verified Abort; the
   Clip Editor refusal.
6. Sequence on qualified routes: the legacy left-arm pose (version 1, natively qualified), then the finger grip on the
   moved arm; Undo/Redo through both.
7. Optionally, an ordinary prop attached to a finger follows the grip (Process C).
8. The Save dialog, its grouped picker, Pose Info and the Apply workflow are inspected by eye and captured.

**Not covered (by design):** a version 3 Full body (Krystal's Full body uses the version 2 route; the Heavy and other
models with procedural bones are not presumed supported; NQ-03 model discovery is separate); the version 2 Full body
route in a sequence (its S3 run 4 closure is still pending); `constant_channel_carried_v1` (disabled); nonunit scale at
a partial boundary (NQ-S1 scale; not present above Krystal's fingers); the 0.00005 offset allowance beyond equality
(shot13's FK positions equal shot15's). Recovery-unverified, the recovery pause and committed-unverified are not
provoked natively (they leave a scene CPM cannot confirm); they are covered offline.

## Identities

| Item | Value |
|---|---|
| Source commit (branch `feature/f01-pose-library`) | `0b839cef4c9cacee90ac0a05be409ed31cd3ae95` |
| Candidate CPM `cpm/app/SFM_Character_Preset_Manager.py` (production source) | `2d791dec96c0b4816693c369fe5f956de5e1ed93a1ecea8b95fd0d5515b9cc6a` |
| Qualification CPM (`build`; exactly one changed line 42146, `PROD_POSE_REGISTRY_MODE = u"qualification"`) | `b58ae9ba0dfee675038bf6b6bf9e5ac27e3e1adb13ed3b0ba93cdc6c11140d05` |
| Pose registry `cpm/pose_profiles/cpm_pose_profiles_v1.json` (left arm qualified) | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| Body registry `cpm/pose_profiles/cpm_body_profiles_v1.json` (pinned by the candidate; Full body is not saved here) | `22dcd1599c0556bcb71df0a9b9d14657684173b3bbf557250710a8104a6baa26` |
| Published CPM (installed before and after) | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df` |
| R2 fixture (read-only; every session copy) | `259ea8a614bc9e43e5bde15afdf38e1a1295dffb50b14cf75692df4221a05a2c` |
| S0 observer (unchanged) | `4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4` |
| Legacy pose `NQ1 Pose A` (version 1, Stage D ME-1b evidence) | `4916a7243193306ab7a93dec9fbc988b079c9af4c3bb0e9828a5b2d89cef3541` |
| Kit (this folder): observer wrapper, UI capture, comparator | recorded by `build` in `<Q>\staged\IDENTITIES.json`; `pre` refuses if any changed since |

**Staged and installed** (by `build` and `install`, nothing else): the qualification CPM into
`usermod\scripts\ChadChan3D_CPM\SFM_Character_Preset_Manager.py`, and both registries into
`usermod\scripts\SFM Character Tools\`. The kit files are executed from the repository by the Script Editor; they are
never installed.

**Isolation of the experimental capability:**
- `direct_fk_v1` is usable only when `PROD_POSE_REGISTRY_MODE == "qualification"`. The shipped build is
  `"production"`. The qualification build differs from the candidate in that line only (`build` refuses otherwise and
  refuses unless the result equals the pinned hash above).
- It is installed only for this run, after `pre` has backed up the published CPM, SFM housekeeping and `.pyc` files and
  recorded four inventories (scripts, `usermod\cfg`, the CPM library, sessions). An installation journal is written
  before any file changes.
- Poses are written only to a new `Characters\krystal2020--7d2aee52ef3a\Poses` folder; `pre` refuses if any Poses
  folder exists. `restore` moves it into `<Q>\evidence\library_poses`, puts the published CPM back, removes both
  registries, restores housekeeping and `.pyc`, and verifies every inventory equals its baseline.
- Sessions are disposable copies in `<Q>\sessions`; the R2 fixture and the source run's files are only read.

**Fixture facts (S0, NQ-1, S3):** shot15 runs 0.1667–0.2917 s, shot13 0.3334–0.3751 s, shot10 0.3751–0.5001 s; each holds
one separate `Krystal` (`krystal2020.mdl`); shot13's FK bone positions equal shot15's exactly. Krystal's 15 left finger
and thumb bones are direct FK (offline section K): `bip_index_0_l … bip_index_2_l`, `bip_middle_0_l … _2_l`,
`bip_ring_0_l … _2_l`, `bip_pinky_0_l … _2_l`, `bip_thumb_0_l … _2_l`. Krystal's native control-group names were never
observed: select the 15 bones by name; record the grouping CPM shows (a UI observation, not a stop).

**Folders and tools:**
- `<Q>`: a new run folder used once, for example `E:\SFM_U0B_Scratch\f01-sfp1-nq1`. `<REPO>`: the F-01 worktree at the
  source commit.
- `python -I <REPO>\real_sfm_qualification\f01_sfp1_nq\tools\sfp1_tool.py <Q>\sfp1.json <command>`, shortened below to
  `sfp1_tool <command>` (system Python 3, SFM closed).
- Keep `<Q>\OPERATOR_NOTES.txt` open and save screenshots to `<Q>\screenshots\` with the names given.

## Stop rule

At any STOP: stop issuing SFM commands, close SFM **without saving**, run R2 (`restore`) and report. Restore is always
permitted and can be re-run. STOP when:
- an observation prints `MISMATCH - STOP`, or a UI capture prints `- STOP`;
- a status differs from the Expected column (except the two explicitly marked findings: C2's refusal, and how the
  picker groups the bones);
- CPM shows "Pose changes are paused…" or "CPM couldn't confirm…";
- a change appears on Krystal outside the selected fingers (wrist, arm, body, face, gaze, jaw) after an Apply;
- SFM stops responding for more than a minute or crashes;
- any step is done out of order.

Never save a session after step 0.

## Preparation (SFM closed)

| # | Action | Expected |
|---|---|---|
| P0 | Copy `sfp1.template.json` to `<Q>\sfp1.json`. Fill in this machine's paths (`Q`, `REPO`, `GAME`, `SESSIONS`, `R2_FIXTURE`, `LEGACY_POSE` = the Stage D ME-1b evidence copy of `NQ1 Pose A--5273df2209ca.json`). Do not change any pin. | No `<…>` placeholder remains. |
| P1 | `sfp1_tool build` | `BUILT: … differs from the candidate in line 42146 only`; `qualification_cpm_sha256` = `b58ae9ba…`. |
| P2 | Confirm no `sfm.exe` is running (`tasklist /FI "IMAGENAME eq sfm.exe"`). Then `sfp1_tool pre`. | `PRE PASS` (a few minutes). `<Q>\sessions\SFP1_SOURCE.dmx` and `SFP1_PREPARATION.dmx` exist. On any refusal nothing changed: STOP and report. |

## Step 0: prepare the destination (published CPM; CPM not opened)

Rotate FK bones only; never move (translate) them. Move only rig handles (`Hand_l`, `Elbow_l`, `Collar_l`) and the
face controls.

| # | Action |
|---|---|
| 0.1 | Start SFM. File > Open `<Q>\sessions\SFP1_PREPARATION.dmx`. Switch to the **Motion Editor**. Playhead **0.3750 s** (frame 9, shot13). |
| 0.2 | shot13's Krystal: open the left hand (rotate every left finger and thumb bone about 15° or more, away from a grip). Turn and raise the left wrist: rotate `Hand_l` about 30° and move it about 5 units; move `Elbow_l` a little. Give her a distinct face: a smile, an open jaw, and turn the eyes with `eyes_rightleft`. |
| 0.3 | Playhead **0.2083 s** (frame 5, shot15). shot15's Krystal: spread the left fingers (rotate each about 15° or more); rotate `Hand_l` about 20° and move it about 4 units (so the legacy left-arm pose will visibly move the arm). |
| 0.4 | File > Save As `<Q>\sessions\SFP1_DESTINATION.dmx`. |
| 0.5 | **Optional prop (Process C).** Still in SFM: playhead **0.3750 s** (shot13). Add a small prop model to shot13 and place it at Krystal's left index finger. Using SFM's **Point** and **Orient** constraint commands (not Parent or Aim), constrain the prop's root transform to Krystal's `bip_index_2_l`. File > Save As `<Q>\sessions\SFP1_PROP.dmx`. Note in OPERATOR_NOTES which model and commands you used. Skip this row to skip Process C. |
| 0.6 | Exit SFM (do not save again). Confirm no `sfm.exe` remains. |
| 0.7 | `sfp1_tool inspect` → `INSPECTED` (destination, and the prop session if prepared, are pinned). |

## Installation (SFM closed)

| # | Action | Expected |
|---|---|---|
| I1 | `sfp1_tool install` | `INSTALLED: qualification CPM b58ae9ba… and both registries`. |
| I2 | `sfp1_tool seed` | `SEEDED: NQ1 Pose A--5273df2209ca.json`. |
| I3 | `sfp1_tool check` | `"installation": "qualification"`. |

## Observing

Once per SFM process, in the Script Editor: `SFP1_DIR = r"<Q>"; SFP1_REPO = r"<REPO>"`.

**Observe** a step:
`SFP1_STEP = "A1"; execfile(SFP1_REPO + r"\real_sfm_qualification\f01_sfp1_nq\observer\F01_SFP1_Observe.py")`,
changing only the step name. Each takes about a minute, prints `SFP1 STEP <step> (S0-NN): OK`, and only reads. Never
repeat a step name.

**UI capture** (with the pose selected in CPM's Poses list):
`SFP1_UI = "UI-A"; execfile(SFP1_REPO + r"\real_sfm_qualification\f01_sfp1_nq\observer\F01_SFP1_UIState.py")`.

For B2, B6, B12 and C2 note in OPERATOR_NOTES the time from clicking **Apply Pose** to the final status, and whether SFM
froze.

## Process A: pose, save and update (source session)

| # | Action | Expected |
|---|---|---|
| A0 | Start SFM. Open `<Q>\sessions\SFP1_SOURCE.dmx`. **Motion Editor**. Playhead **0.2083 s** (shot15). Scripts > SFM Character Tools > Character Preset Manager. Refresh Models, select **Krystal**, **Poses** tab. Set `SFP1_DIR` and `SFP1_REPO`. | `NQ1 Pose A` listed. **Save New** enabled. |
| A1 | Observe. | `SFP1 STEP A1 (S0-01): OK` |
| A2 | Curl Krystal's left fingers and thumb into a clear **grip** (rotate each of the 15 bones about 15° or more; never move them). Do not touch the wrist, arm, face or rig. Observe. | |
| A3 | **Save New**. In the dialog: screenshot `SAVE_DIALOG_1.png` and note: the choices (Full body / Selected parts), how the picker groups Krystal's bones, which arm controls are listed as unavailable and their reasons. Choose **Selected parts**; tick exactly the 15 left finger and thumb bones (a group that holds exactly them may be ticked instead); screenshot `SAVE_DIALOG_2.png`. Name `SFP1 Grip`, Save. Observe. | Status `Pose saved: SFP1 Grip.` Only the 15 bones were selectable as one consistent choice; rig-driven arm controls cannot be selected (shown unavailable with a reason). |
| UI-A | Select `SFP1 Grip`, open **Pose Info**; screenshot `POSE_INFO.png`. Close it. UI capture `UI-A` (no observation). | Pose Info: `Saved scope: Selected parts: …`, `Includes: 15 controls (articulation only)`. `SFP1 UI-A: 'SFP1 Grip' version 3 Selected parts, Apply Pose enabled: OK`. |
| A4 | Pose a **pointing** hand: index straight, the other fingers and thumb curled differently from the grip (at least 15° different in several bones). Observe. | |
| A5 | **Save New** → Selected parts → the same 15 bones → name `SFP1 Point` → Save. Observe. | `Pose saved: SFP1 Point.` |
| A6 | Change at least two fingers by 15° or more (the update content). Observe. | |
| A7 | Select `SFP1 Point`, **Update Pose**, confirm. Observe. | `Pose updated: SFP1 Point.` |
| A8 | Exit SFM **without saving**. Note whether SFM closed cleanly (no crash dialog). Confirm no `sfm.exe` remains. Then `sfp1_tool library A`. | `LIBRARY A: 4 files recorded` (`SFP1 Grip`, `SFP1 Point`, `NQ1 Pose A` and `SFP1 Point`'s `.bak`, the backup Update Pose writes by design). |

## Process B: restart, apply, undo, refusals, sequence (destination session)

The source session is never opened in this process.

| # | Action | Expected |
|---|---|---|
| B0 | Start SFM. Open `<Q>\sessions\SFP1_DESTINATION.dmx`. **Motion Editor**. Playhead **0.3750 s** (shot13). Open CPM, Refresh Models, **Krystal**, **Poses**. Set `SFP1_DIR` and `SFP1_REPO`. | `SFP1 Grip`, `SFP1 Point` and `NQ1 Pose A` listed, loaded from disk. |
| B1 | Observe (baseline). Select `SFP1 Grip`; UI capture `UI-B`. | `SFP1 UI-B: … OK`. |
| B2 | With `SFP1 Grip` selected, **Apply Pose**. Wait until the status leaves `Checking the applied pose...`. Note the time. Look at the left hand. Screenshot `APPLY_GRIP.png`. Observe. | `Pose applied: SFP1 Grip.` Edit > Undo names `Apply Pose SFP1 Grip`. The left fingers take the grip **inside the destination's own turned, raised wrist**. Wrist, arm, body, face, gaze and jaw unchanged. |
| B3 | Click the viewport, **Ctrl+Z** once. Observe. | The open hand returns. |
| B4 | **Ctrl+Y** once. Observe. | The grip again. |
| B5 | **Apply Pose** again (`SFP1 Grip`). Observe. | `Already matches this pose.` No new Undo entry. |
| B6 | Select `SFP1 Point`, **Apply Pose**. Note the time. Observe. | `Pose applied: SFP1 Point.` The **updated** pointing hand (A7's content). |
| B7 | Script Editor: `import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"`. Select `SFP1 Grip`, **Apply Pose**. Observe. | `The pose couldn't be applied. Nothing was changed.` The pointing hand remains; Undo still names `Apply Pose SFP1 Point`. |
| B8 | Switch the timeline to the **Clip Editor** without moving the playhead. Observe. | |
| B9 | **Apply Pose** (`SFP1 Grip`). Observe. | Refused: `Switch to the Motion Editor to apply a pose. Nothing was changed.` |
| B10 | Switch to the **Motion Editor**. Playhead **0.2083 s** (shot15). CPM: Refresh Models, **Krystal**, Poses. Observe. | |
| B11 | Select `NQ1 Pose A`, **Apply Pose**. Observe. | `Pose applied: NQ1 Pose A.` Only the left arm moves (legacy path); the spread fingers keep their own curl. |
| B12 | Select `SFP1 Grip`, **Apply Pose**. Note the time. Observe. | `Pose applied: SFP1 Grip.` The fingers take the grip on the **newly posed arm**; the arm does not move. |
| B13 | **Ctrl+Z** once. Observe. | The fingers return to the spread hand; the arm stays posed. |
| B14 | **Ctrl+Z** once. Observe. | The arm returns. |
| B15 | **Ctrl+Y** once. Observe. | The arm is posed again. |
| B16 | **Ctrl+Y** once. Observe. | The grip again. |
| B17 | Exit SFM **without saving**. Note a clean close. Confirm no `sfm.exe` remains. | |

## Process C (optional): an ordinary attached prop (prop session)

Run only if step 0.5 prepared `SFP1_PROP.dmx`.

| # | Action | Expected |
|---|---|---|
| C0 | Start SFM. Open `<Q>\sessions\SFP1_PROP.dmx`. **Motion Editor**. Playhead **0.3750 s** (shot13). Open CPM, Refresh Models, **Krystal**, Poses; select `SFP1 Grip`. Set `SFP1_DIR`, `SFP1_REPO`. | |
| C1 | Observe. | |
| C2 | **Apply Pose**. Note the time and look at the prop. Screenshot `PROP_APPLY.png`. Observe. | Either `Pose applied: SFP1 Grip.` with the prop following the index finger (CPM does not verify the prop's own pose), or a refusal that changes nothing (a **finding**, not a STOP; note the message). |
| C3 | If C2 applied: **Ctrl+Z** once. If C2 refused: press nothing. Observe. | Applied case: the hand and the prop return. |
| C4 | Exit SFM **without saving**. Confirm no `sfm.exe` remains. | |

## R: evidence, restoration and verdict (SFM closed; always)

| # | Action | Expected |
|---|---|---|
| R0 | `sfp1_tool library B` | `LIBRARY B: 4 files recorded`, identical to library A (the Apply processes changed no record) |
| R1 | `sfp1_tool collect-logs` | `LOGS COLLECTED: N files` (CPM logs since `pre`, verified copies) |
| R2 | `sfp1_tool restore` | `RESTORED`: published CPM `ccbed9d7…` back, both registries removed, the run's Poses folder moved to `<Q>\evidence\library_poses`, housekeeping and `.pyc` restored, every inventory equal to its baseline. |
| R3 | `sfp1_tool check` | `"installation": "published"` |
| R4 | `sfp1_tool compare` | `<Q>\evidence\SFP1_VERDICT.md`, ending `verdict: PASS` (findings listed separately). |

Return `<Q>\observations\`, `<Q>\evidence\`, `<Q>\screenshots\`, `OPERATOR_NOTES.txt` and the SFM console text.

**Rollback at any point:** close SFM without saving, then `sfp1_tool restore` (re-run if interrupted). If `restore`
refuses, the published CPM's verified backup is `<Q>\pre_run\backup\` and the journal `<Q>\pre_run\install_journal.json`;
report before changing anything by hand. A paused CPM ("Pose changes are paused…") needs only an SFM restart after
restore.

## Expected evidence (the comparator's checks, `SFP1_VERDICT.json`)

| Requirement (priority) | Checks |
|---|---|
| Every observation valid, read-only, the qualification CPM loaded | `observed.*`, `valid.*`, `cpm.*` |
| Restart and an independent destination session (2) | `process.restart_between_save_and_apply`, `process.sessions` |
| Save captures exactly the 15 fingers as version 3 Selected parts, changing nothing in the scene (1) | `save.grip_is_version_3_selected_parts_of_the_15_left_fingers`, `save.point_is_…`, `save.grip_captures_the_visible_fingers` (record oracle within 0.01° of A2), `save.*_writes_nothing_to_the_scene` |
| Update Pose in place (1) | `update.point_holds_the_updated_articulation`, `update.updated_articulation_differs_visibly_from_the_first`, `update.in_place` |
| A visibly different destination | `distinct.destination_fingers_differ_from_the_grip` (≥ 5°), `distinct.destination_wrist_differs_from_the_source` |
| Apply reproduces the fingers inside the destination wrist (1, 2) | `apply_grip.fingers_take_the_saved_articulation` (≤ 0.01°), `apply_grip.finger_offsets_are_the_destinations_own`, `apply_grip.keys_at_the_mapped_tick` |
| Preservation of unselected state (3) | `apply_*.only_finger_channels_changed`, `apply_*.wrist_arm_body_and_face_unchanged` (every other bone, world and local), `apply_*.facial_gaze_and_other_controls_unchanged`, `apply_*.model_and_rig_handles_unchanged`, `apply_*.unrelated_animation_unchanged` (every channel outside the instance) |
| Native Undo/Redo, no-op, update keys, Abort, refusal (4) | `apply_*.one_owned_undo_entry`, `undo.restores_the_destination_baseline`, `redo.restores_the_applied_grip`, `repeat.true_noop`, `apply_point.existing_keys_updated_in_place`, `abort.verified_nothing_changed`, `refusal.clip_editor_writes_nothing` |
| CPM's own P7 verification; no uncertainty (4) | `log.three_scoped_applies_owned_and_verified_by_cpm`, `log.repeat_is_noop`, `log.point_updates_only`, `log.abort_verified`, `log.no_recovery_or_uncertainty` |
| Sequence on qualified routes (5) | `seq.destination_fingers_differ_from_the_grip`, `seq.legacy_left_arm_applied`, `seq.legacy_arm_moved_the_wrist_visibly`, `seq.legacy_arm_keeps_the_finger_articulation`, `seq_grip.*`, `seq.undo_fingers_then_arm`, `seq.redo_arm_then_fingers`, `log.legacy_verified_by_cpm` |
| Optional prop (6) | applied: `prop_apply.*` (the character's checks; the prop is not verified) and `prop.undo_restores`; refused: `prop.refusal_writes_nothing`; the outcome is listed under Findings |
| UI (7) | `ui.UI-A_pose_info_and_apply_state`, `ui.UI-B_…`; screenshots and OPERATOR_NOTES are reviewed by eye |
| Restoration | `restore.published_and_inventories_equal`, `sessions.destination_not_saved_during_the_run`, `sessions.prop_session_not_saved_during_the_run` |
| Performance | per scoped Apply from CPM's millisecond log stamps: responsive ≤ 5 s; finding ≤ 30 s (PASS, for the Owner's decision); fail above |

Native dependencies addressed (implementation record section 8): NQ-S2 (exact-time keys on finger channels, Undo/Redo),
NQ-S3 (bit-stable P1/P2: no stale refusal on an idle scene), NQ-S5 (a second instance in another shot and session),
NQ-S8 (control groups read inside the Save dialog), NQ-S9 (the Save dialog inside SFM: appearance, several dialogs per
process, clean exit). Not addressed: NQ-S1 scale, NQ-S4, NQ-S6, NQ-S7 beyond equality.
