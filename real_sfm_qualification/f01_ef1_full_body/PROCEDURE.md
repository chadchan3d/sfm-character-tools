# F-01 EF-1: TF2 Engineer generic version 3 Full body, bounded native qualification (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
execution approval.

**Scene writes:**
- the Owner's preparation (step 0: one Engineer added and posed, with the published CPM installed and CPM not opened);
- the Owner's posing of the source in Process A;
- CPM's own Save New and Apply Pose.

**Session saves:** step 0 saves the two sessions once. No session is saved after step 0.

**What it shows, as an artist would do it (TF2 Engineer `models/player/engineer.mdl`, unrigged, EC-1 CANDIDATE):**
1. Pose the Engineer's whole body, including the body root (`bip_pelvis`), and save it as a version 3 **Full body**
   pose (Save New → Full body). No profile or registry entry is used: the scope is CPM's automatic `direct_fk_v1`
   discovery.
2. Restart SFM and open a separately prepared destination session whose Engineer has the following:
   - a different body pose and body-root position;
   - a different scene placement (`rootTransform`);
   - a facial expression.

   The saved pose appears in the Poses list.
3. A verified Abort first: the fault hook makes the first Apply roll back, and nothing changes.
4. Apply. Expected results:
   - every bone takes the saved orientation;
   - the body root takes the saved translation relative to the model;
   - every other bone keeps the destination's own offset;
   - the whole body matches the pose in the model's frame;
   - the scene placement, the facial expression and everything outside the Engineer stay unchanged.
5. Undo, Redo, a second Apply that writes nothing, a Clip Editor refusal, and a final Undo back to the baseline.
6. The Save dialog, Pose Info and the Apply workflow are inspected by eye in normal use and captured. This is not a
   separate UI qualification.

**Rules used, unchanged:**
- R3 (`cpm/qualification/F01_SCOPED_POSE_BLUEPRINT_R3_20261108.md`) and the existing P1–P7 transaction;
- the established tolerances (0.01°, 0.001 units);
- no new pose semantics.

The offline replay (EC-1 and this kit's checks) is **not** native acceptance.

**Not covered (by design):**
- Update Pose: natively qualified for Selected parts in SFP-1 NQ1, and not repeated here.
- A rigged Engineer, or another model. The Heavy and others with declared procedural bones are not presumed
  supported.
- Selected parts on the Engineer.
- `constant_channel_carried_v1` (disabled).
- Nonunit scale (NQ-S1): the Engineer has no scale.
- A second instance in the same session.
- Rendering.
- Recovery-unverified, the recovery pause and committed-unverified: they leave a scene CPM cannot confirm, so they are
  not provoked natively. They are covered offline.

## Identities

| Item | Value |
|---|---|
| Source branch | `feature/f01-pose-library`. The EC-1 closure is at `28efe0a`. The CPM is unchanged since the accepted UI implementation `ccc6d7c`. |
| Candidate CPM `cpm/app/SFM_Character_Preset_Manager.py` (production source, accepted UI) | `7548d1eb25a7479c9b3c0fffa2186d187ef3763b123412ca5ae6ef2cf6899a45` |
| Qualification CPM (`build`; exactly one changed line, 42118: `PROD_POSE_REGISTRY_MODE = u"qualification"`) | `a378e25ae932d273d53a13e2c7c0ab2aa1ae7f71f31ea944667fd8d93aed971e` |
| Pose registry (pinned by the candidate; not used by Full body v3) | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| Body registry (pinned by the candidate; not used by Full body v3) | `22dcd1599c0556bcb71df0a9b9d14657684173b3bbf557250710a8104a6baa26` |
| Published CPM (installed before and after) | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df` |
| Model | `models/player/engineer.mdl` → `tf/models/player/engineer.mdl` `a505bba4…` (NQ-03 and EC-1). `pre` refuses on any other file. |
| Expected header (the comparator's 72 bones) | `f01_ec1_engineer/engineer_header.json` `5faabf6b…` |
| S0 observer (unchanged; verified by the wrapper at every step) | `4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4` |
| Kit files: wrapper, UI capture, comparator, session classifier | recorded by `build` in `<Q>\staged\IDENTITIES.json`. `pre` refuses if any of them changed since. |
| CPM library folder for the Engineer | `Characters\engineer--6111c38a013f` (CPM's label for the model path). It must not exist before the run. |

**Staged and installed** (by `build` and `install`, nothing else):
- the qualification CPM into `usermod\scripts\ChadChan3D_CPM\SFM_Character_Preset_Manager.py`;
- both registries into `usermod\scripts\SFM Character Tools\`.

The kit files run from the repository through the Script Editor; they are never installed.

**Isolation of the experimental capability:**
- **The mode line:** `direct_fk_v1` is usable only when `PROD_POSE_REGISTRY_MODE == "qualification"`, and the shipped
  build is `"production"`. The qualification build differs from the candidate in that line only. `build` refuses
  otherwise, and refuses unless the result equals the pin above.
- **Installed only for this run:**
  - **Before installation:** `pre` backs up the published CPM, SFM housekeeping and `.pyc` files, and records four
    inventories: scripts, `usermod\cfg`, the CPM library and sessions.
  - **During installation:** an installation journal is written before any file changes.
- **Where poses go:** only into the new `Characters\engineer--6111c38a013f` folder.
- **What `restore` does:**
  - moves every file CPM wrote there outside `Poses` (for example `character.json`) into
    `<Q>\evidence\library_character`;
  - moves `Poses` into `<Q>\evidence\library_poses`;
  - removes the emptied folder;
  - puts the published CPM back, removes both registries, and restores housekeeping and `.pyc`;
  - verifies every inventory equals its baseline.

**Sessions and SFM's own files in `<Q>\sessions`:**
- **The two pinned sessions:** step 0 creates exactly two sessions there, both holding the Engineer.
  `inspect` classifies the folder (`f01_ec1_engineer/tools/session_files.py`) and pins both.
- **The starter session (expected):** File > New writes SFM's empty starter session (`ef1_source.dmx`) at once, before
  the model is added (EC-1 deviation EC1-D1). File > Save then overwrites it with the Engineer. `inspect` refuses if a
  session still holds no character, which would mean Save was skipped.
- **Name case:** SFM writes the names in lowercase; every check ignores case.
- **SFM's autosave copies:** a `.autosave` file beside an open session is expected. It is recorded as a finding,
  never pinned, and never counted as a save.
- **Saves:** a pinned session whose bytes change means it was saved, and that FAILS. Any other file also FAILS.

**Folders and tools:**
- `<Q>`: a new run folder, used once; for example `E:\SFM_U0B_Scratch\f01-ef1-full-body`.
- `<REPO>`: the F-01 worktree at the source commit.
- `python -I <REPO>\real_sfm_qualification\f01_ef1_full_body\tools\ef1_tool.py <Q>\ef1.json <command>`, shortened
  below to `ef1_tool <command>` (system Python 3, SFM closed).
- Keep `<Q>\OPERATOR_NOTES.txt` open, and save screenshots to `<Q>\screenshots\` with the names given.

## Stop rule

At any STOP: stop issuing SFM commands, close SFM **without saving**, run R2 (`restore`) and report. Restore is always
permitted and can be re-run.

STOP when:
- an observation prints `MISMATCH - STOP`, or a UI capture prints `- STOP`;
- a status differs from the Expected column;
- CPM shows "Pose changes are paused…" or "CPM couldn't confirm…";
- after an Apply, a change appears outside the Engineer's skeleton: its placement, its face, the camera, or anything
  else;
- SFM offers to recover an autosave, stops responding for more than a minute, or crashes;
- any `ef1_tool` command refuses, or a step is done out of order.

Never save a session after step 0. Never open the source session in Process B.

## Preparation (SFM closed)

| # | Action | Expected |
|---|---|---|
| P0 | Copy `ef1.template.json` to `<Q>\ef1.json`. Fill in this machine's paths (`Q`, `REPO`, `GAME`, `SESSIONS`). Do not change any pin. | No `<…>` placeholder remains. |
| P1 | `ef1_tool build` | `BUILT: … differs from the candidate in line 42118 only`; `qualification_cpm_sha256` = `a378e25a…`. |
| P2 | Confirm no `sfm.exe` is running (`tasklist /FI "IMAGENAME eq sfm.exe"`). Then run `ef1_tool pre`. | `MODEL PASS`, then `PRE PASS` (a few minutes). `<Q>\sessions` exists and is empty. On any refusal nothing changed: STOP and report. |

## Step 0: prepare the two sessions (published CPM; CPM not opened)

When posing, rotate bones only, except where a row says move. Use the Animation Set Editor's groups (Body, Arms,
Legs, Face) to select each control. "About" means any clearly visible amount.

| # | Action |
|---|---|
| 0.1 | Start SFM. **File > New**, name `EF1_SOURCE`; if SFM asks for a folder, choose `<Q>\sessions`. SFM writes its starter session `ef1_source.dmx` now (expected). |
| 0.2 | Animation Set Editor: **+** > **Create Animation Set for New Model**, choose `models/player/engineer.mdl` (TF2). Click nothing else. Note the animation set's exact name (normally `engineer1`) in OPERATOR_NOTES. |
| 0.3 | **File > Save.** (`ef1_source.dmx` now holds the unposed Engineer.) |
| 0.4 | Switch to the **Motion Editor**. Playhead at frame **0** (0.0000 s). Make the destination differ. **Body:** rotate `bip_spine_2` about 20° backward, `bip_head` about 25° to the left, `bip_upperArm_R` about 30° down, `bip_lowerArm_L` about 20°, `bip_hip_R` about 20° backward, `bip_knee_L` about 15°. **Body root:** *move* `bip_pelvis` about 5 units sideways and 2 down. **Placement:** select `rootTransform` (Body group); *move* it about 40 units sideways and rotate it about 45° about the vertical axis. **Face:** Face > Expressions > `happySmall` to about 0.7. |
| 0.5 | **File > Save As** `EF1_DESTINATION` in `<Q>\sessions`. |
| 0.6 | Exit SFM (do not save again). Confirm no `sfm.exe` remains. |
| 0.7 | `ef1_tool inspect` → `INSPECTED: ef1_source.dmx and ef1_destination.dmx are pinned` (any autosave copies are listed). |

## Installation (SFM closed)

| # | Action | Expected |
|---|---|---|
| I1 | `ef1_tool install` | `INSTALLED: qualification CPM a378e25a… and both registries`. |
| I2 | `ef1_tool check` | `"installation": "qualification"`. |

## Observing

**Once per SFM process,** in the Script Editor, with the name noted at 0.2:
`EF1_DIR = r"<Q>"; EF1_REPO = r"<REPO>"; EF1_ANIMSET = "engineer1"`

**Observe a step** by changing only the step name:
`EF1_STEP = "A1"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")`.
- Each observation takes about a minute.
- It prints `EF1 STEP <step> (S0-NN): OK` and only reads.
- Never repeat a step name.

**UI capture**, with the pose selected in CPM's Poses list:
`EF1_UI = "UI-A"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_UIState.py")`.

**Timing:** for B3, note in OPERATOR_NOTES the time from clicking **Apply Pose** to the final status, and whether SFM
froze.

## Process A: pose and save (source session)

| # | Action | Expected |
|---|---|---|
| A0 | Start SFM. Open `<Q>\sessions\ef1_source.dmx`. **Motion Editor**. Playhead frame **0**. Scripts > SFM Character Tools > Character Preset Manager. Refresh Models, select the Engineer (`engineer1`), **Poses** tab. Submit the setup line. | The Poses list is empty. **Save New** enabled. |
| A1 | Observe. | `EF1 STEP A1 (S0-01): OK` |
| A2 | Pose the whole body. **Body root:** *move* `bip_pelvis` about 5 units up and 5 forward, and rotate it about 15° about the vertical axis. **Rotate:** `bip_spine_1` about 20° forward; `bip_head` about 30° to the right; `bip_upperArm_L` about 60° up; `bip_lowerArm_L` about 45°; `bip_upperArm_R` about 40° forward; `bip_hand_R` about 30°; `bip_hip_L` about 35° forward; `bip_knee_L` about 50°; `bip_index_1_R` and `bip_middle_1_R` about 40° each. Do not touch `rootTransform`, any face slider or any other control. Observe. | |
| A3 | **Save New**. In the dialog: screenshot `SAVE_DIALOG_1.png`. Note in OPERATOR_NOTES: the choices (Full body / Selected parts), whether Full body is offered, its summary text, and any message. Choose **Full body**; screenshot `SAVE_DIALOG_2.png`. Name `EF1 Body`, Save. Observe. | Status `Pose saved: EF1 Body.` |
| UI-A | Select `EF1 Body`, open **Pose Info**; screenshot `POSE_INFO.png`, and note anything unclear or wrong. Close it. UI capture `UI-A` (no observation). | `EF1 UI-A: 'EF1 Body' version 3 Full body (72 bones), Apply Pose enabled: OK`. |
| A4 | Exit SFM **without saving**. Note whether SFM closed cleanly (no crash dialog). Confirm no `sfm.exe` remains. Then `ef1_tool library A`. | `LIBRARY A: 1 files recorded` (`EF1 Body`). |

## Process B: restart, abort, apply, undo, refusal (destination session)

The source session is never opened in this process.

| # | Action | Expected |
|---|---|---|
| B0 | Start SFM. Open `<Q>\sessions\ef1_destination.dmx`. **Motion Editor**. Playhead frame **0**. Open CPM, Refresh Models, the Engineer, **Poses**. Submit the setup line. | `EF1 Body` listed, loaded from disk. The Engineer stands in the destination pose, placed and turned differently, smiling. |
| B1 | Observe (baseline). Select `EF1 Body`; UI capture `UI-B`. | `EF1 UI-B: … OK`. |
| B2 | Script Editor: `import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"`. With `EF1 Body` selected, **Apply Pose**. Observe. | `The pose couldn't be applied. Nothing was changed.` The Engineer is unchanged. Edit > Undo names the same entry as at B1. |
| B3 | **Apply Pose** (`EF1 Body`). Wait until the status leaves `Checking the applied pose...`. Note the time. Screenshot `APPLY_BODY.png`. Observe. | `Pose applied: EF1 Body.` Edit > Undo names `Apply Pose EF1 Body`. The Engineer takes the saved body pose **where the destination placed him**: same spot and facing as before the Apply; pelvis raised and forward as saved; still smiling. |
| B4 | Click the viewport, **Ctrl+Z** once. Observe. | The destination pose returns. |
| B5 | **Ctrl+Y** once. Observe. | The saved pose again. |
| B6 | **Apply Pose** again (`EF1 Body`). Observe. | `Already matches this pose.` No new Undo entry. |
| B7 | Switch the timeline to the **Clip Editor** without moving the playhead. Observe. | |
| B8 | **Apply Pose** (`EF1 Body`). Observe. | Refused: `Switch to the Motion Editor to apply a pose. Nothing was changed.` |
| B9 | Switch to the **Motion Editor** (playhead unchanged). Observe. | Nothing changed. |
| B10 | **Ctrl+Z** once. Observe. | The destination pose returns (the baseline). |
| B11 | Exit SFM **without saving**. Note a clean close. Confirm no `sfm.exe` remains. | |

## R: evidence, restoration and verdict (SFM closed; always)

| # | Action | Expected |
|---|---|---|
| R0 | `ef1_tool library B` | `LIBRARY B: 1 files recorded`, identical to library A (Process B changed no record). |
| R1 | `ef1_tool collect-logs` | `LOGS COLLECTED: N files` (CPM logs since `pre`, verified copies). |
| R2 | `ef1_tool restore` | `CHARACTER FOLDER: …` and `CHARACTER FOLDER REMOVED`, then `RESTORED`. That means: published CPM `ccbed9d7…` back; both registries removed; the run's Poses folder in `<Q>\evidence\library_poses`; housekeeping and `.pyc` restored; every inventory equal to its baseline. |
| R3 | `ef1_tool check` | `"installation": "published"` |
| R4 | `ef1_tool compare` | `<Q>\evidence\EF1_VERDICT.md`, ending `verdict: PASS` (findings listed separately). |

Return `<Q>\observations\`, `<Q>\evidence\`, `<Q>\screenshots\`, `OPERATOR_NOTES.txt` and the SFM console text.

**Rollback at any point:** close SFM without saving, then run `ef1_tool restore` (re-run it if interrupted). If
`restore` refuses, report before changing anything by hand. The verified backup of the published CPM is in
`<Q>\pre_run\backup\`, and the journal is `<Q>\pre_run\install_journal.json`. A paused CPM ("Pose changes are
paused…") needs only an SFM restart after restore.

## Expected evidence (the comparator's checks, `EF1_VERDICT.json`)

| Requirement | Checks |
|---|---|
| Every observation valid, read-only, with the qualification CPM loaded, the 72 Engineer bones, and only S0's no-rig note as a finding | `observed.*`, `valid.*`, `findings.*`, `cpm.*`, `structure.*` |
| Persistence after a restart, in an independently loaded destination | `process.restart_between_save_and_apply`, `process.sessions`, `library.*` |
| Save New: a version 3 Full body record of all 72 bones that captures the visible pose and writes nothing to the scene | `save.is_version_3_full_body_of_all_72_bones` (declared body, `direct_fk_v1` revision 1, root `bip_pelvis`, root translation included, nothing carried or excluded); `save.oracle_frame_is_the_model`; `save.captures_the_visible_pose` (oracle within 0.01° and 0.001 units of A2, locally and in the model frame); `save.root_translation_is_the_root_channel_value`; `save.pose_differs_visibly_from_the_source_baseline`; `save.source_posing_touched_only_bones`; `save.writes_nothing_to_the_scene` |
| A visibly different destination | `distinct.destination_body_differs_from_the_pose` (≥ 5°), `distinct.destination_body_root_differs_from_the_pose` (≥ 1 unit), `distinct.destination_model_placement_differs`, `distinct.destination_has_a_facial_expression` |
| Accurate restoration of the skeletal controls and the body root | `apply.every_bone_takes_the_saved_orientation` (≤ 0.01°), `apply.body_root_takes_the_saved_translation` (≤ 0.001), `apply.body_matches_the_pose_in_the_model_frame`, `apply.non_root_offsets_are_the_destinations_own` |
| Preservation of placement, face and unrelated animation | `apply.only_skeletal_channels_changed` (the 144 bone channels, keyed at the mapped tick; verified on CPM's replay), `apply.model_placement_unchanged`, `apply.facial_and_placement_controls_unchanged`, `apply.unrelated_animation_unchanged`, `apply.keys_at_the_mapped_tick`, `apply.neighbouring_keys_layers_and_metadata_preserved` (keys at other times, the log, its layers and metadata unchanged), `apply.non_root_position_keys_inserted_only_where_missing` (R3 section 5: an existing exact key untouched; a missing one inserted with the destination's own value) |
| Native Undo/Redo, no-op, verified Abort, refusal | `apply.one_owned_undo_entry`, `abort.verified_nothing_changed`, `undo.restores_the_destination_baseline`, `redo.restores_the_applied_pose`, `repeat.true_noop`, `refusal.clip_editor_writes_nothing`, `editor.switching_back_changes_nothing`, `undo.final_undo_returns_to_the_baseline` |
| CPM's own P7 verification; no uncertainty | `log.one_scoped_apply_owned_and_verified_by_cpm`, `log.abort_verified_before_the_apply`, `log.repeat_is_noop`, `log.apply_writes_the_body`, `log.no_recovery_or_uncertainty` |
| UI in normal use | `ui.UI-A_pose_info_and_apply_state`, `ui.UI-B_…`; the screenshots and OPERATOR_NOTES are reviewed by eye, and actual problems are recorded as findings |
| Restoration and the sessions | `restore.published_and_inventories_equal`, `restore.engineer_character_folder_removed`, `sessions.source_not_saved_during_the_run`, `sessions.destination_not_saved_during_the_run`, `sessions.no_unexpected_files` (autosave copies are findings) |
| Performance | the Apply's timing from CPM's millisecond log stamps: responsive ≤ 5 s; finding ≤ 30 s (PASS, for the Owner's decision); fail above |

## Offline preparation evidence (2026-11-10)

- **Tests:** `tests\test_ef1.py` passes 20/20 on Python 3.10.6, and its 9 wrapper and UI tests on SFM's Python 2.7.5.
  - **Observer wrapper:** read-only; it refuses a repeated or unknown step, a wrong model, a missing animation set or
    a modified S0, and reclassifies only the exact no-rig note. Its step table equals the comparator's.
  - **UI capture:** records a version 3 Full body pose and reports STOP otherwise.
  - **Tool:**
    - **build:** derives the pinned build in line 42118 only, and refuses a wrong pin.
    - **inspect:** pins two character sessions and records autosaves. It refuses a starter session, identical
      sessions or an unexpected file.
    - **restore:** moves a new Engineer folder into evidence and removes it.
    - **pre:** refuses when the Engineer folder exists.
  - **Comparator:** a complete synthetic 72-bone run passes; an autosave is a finding. Each of 22 counterexamples
    fails on its own check, plus a wrong build, a problem and a second finding.
- **Real CPM record format:** CPM's own engine (`7548d1eb…`, qualification mode) ran on a replay of the native EC-1
  Engineer observation.
  - **Save:** the Full body record has exactly the fields the comparator expects: 72 posed bones, `declared_body`,
    root `bip_pelvis`, root translation included, frame `component-boundary`.
  - **Model-frame transform:** the comparator's transform matches the record's oracle to within 2.0e-6 units and
    4.8e-6°.
  - **Apply, to a destination with moved placement:** `committed-verified`; the placement is unchanged, and the body
    matches the oracle in the model frame to within 2.0e-6 units and 4.5e-6°.
  - **Write set:** CPM writes all 144 skeletal channels and none outside the skeleton. That set is the comparator's
    rule; it was corrected after this check from an initial rule that admitted only the root's position channel.
