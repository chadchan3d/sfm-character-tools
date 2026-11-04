# F-01 Stage D native checkpoint NQ-1: left-arm Pose Library, save → restart → apply

**Status:** prepared, **not run**. Running it, and every installation change below, needs the Owner's execution
approval. It is one bounded checkpoint. Its only scene writes are those of CPM's own Apply Pose, in disposable session
copies that are never saved.

**What it proves (Owner authorization, Stage D §§1 and 3):**
1. A left-arm pose is saved in one SFM process.
2. That process is closed completely.
3. A new SFM process opens a destination session that contains **neither source animation set**.
4. The pose is loaded from disk and applied at the destination playhead.
5. Native `InsertKey` creates exactly one key at the exact channel time without touching neighbouring keys, and a
   second pose **updates** that key.
6. Ctrl+Z, Ctrl+Y, a true no-op and an injected **Abort** behave as the contract requires.
7. The authored keys, rig inputs, skeletal result and character placement are checked by CPM's own verification
   *and* by an independent observer.

## Identities (pins)

| Item | SHA-256 |
|---|---|
| Stage D candidate CPM `cpm/app/SFM_Character_Preset_Manager.py` (production build) | see `IDENTITIES.json` (`candidate_cpm_sha256`) |
| Qualification CPM (derived by `nq1_tool.py build`; differs in exactly one line: `PROD_POSE_REGISTRY_MODE = u"qualification"`) | see `IDENTITIES.json` (`qualification_cpm_sha256`) |
| Pose profiles `cpm_pose_profiles_v1.json` (installed only for the run) | `87efaad9045e2a562fabb18f6050d426c382654e86c6a2213a812bfdb01363cd` |
| Published CPM (installed before and after) | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df` |
| R2 fixture (read-only; the source of every session copy) | `259ea8a614bc9e43e5bde15afdf38e1a1295dffb50b14cf75692df4221a05a2c` |

**Fixture facts (offline read of the R2 fixture):**

| Role | Shot (document range) | Animation set | Element id | Playhead | Channel time |
|---|---|---|---|---|---|
| Pose A source | shot10 (0.3751–0.5001 s) | Krystal | `1a2aab02abca8e46a0381eaf7530d23f` | 0.4167 s (frame 10 at 24 fps) | 5.0208 s |
| Pose B source | shot13 (0.3334–0.3751 s) | Krystal | `21cffbd736fd5e458fc9fcc6db029402` | 0.3750 s (frame 9) | 5.0416 s |
| Destination | shot15 (0.1667–0.2917 s) | Krystal | `992a01c0e7553546b09480382eade7b5` | 0.2083 s (frame 5) | **5.0208 s (50208 ticks)** |

- All three are `krystal2020.mdl`. They are separate, rigged animation sets.
- The destination's written channels (`Hand_l_p`, `Hand_l_o`, `Elbow_l_p`) each hold keys at 2.9999, 3.0000, 7.0415
  and 7.0416 s, with no key at 5.0208 s. **The first Apply therefore inserts**, and the second updates that key.
- shot13 and shot10 hold different arm poses, so Pose A and Pose B differ in every written channel.
- shot13 and shot10 are the last two shots. Deleting them (step 0) leaves no gap in front of shot15.

`<Q>` is the run folder, `E:\SFM_U0B_Scratch\f01-stage-d-nq1`. `<REPO>` is the F-01 worktree. Tools run with the system
Python 3: `python -I <REPO>\real_sfm_qualification\f01_stage_d_nq1\tools\nq1_tool.py <Q>\nq1.json <command>`.
`nq1.json` is `nq1.template.json` with this machine's paths. It already exists in `<Q>`.

**Stop rule:** at any STOP, stop issuing SFM commands. Close SFM **without saving**, then run step R (restore) and report.
Restore is always permitted.

## Preparation (SFM closed)

| # | Action | Expected |
|---|---|---|
| P1 | `nq1_tool.py … build` | `BUILT: … differs from the candidate in line N only`. Done offline; `IDENTITIES.json` written. |
| P2 | Confirm SFM is not running (`tasklist /FI "IMAGENAME eq sfm.exe"`), then `nq1_tool.py … pre` | `PRE PASS`. Backups, inventories and `<Q>\sessions\NQ1_SOURCE.dmx` and `NQ1_PREPARATION.dmx` created. STOP if it refuses. |

## Step 0: prepare the destination session (SFM, published CPM, CPM not opened)

| # | Action | Expected |
|---|---|---|
| 0.1 | Start SFM. File > Open `<Q>\sessions\NQ1_PREPARATION.dmx`. | Opens normally. |
| 0.2 | In the timeline (clip editor), select **shot13** and **shot10**, the last two shots (0.3334 s to the end), and press Delete. | Only shot3 … shot14 remain. shot15 is unchanged at 0.1667–0.2917 s. |
| 0.3 | File > Save As `<Q>\sessions\NQ1_DESTINATION.dmx`. Then exit SFM. | SFM closed completely (`tasklist` shows no `sfm.exe`). |
| 0.4 | `nq1_tool.py … inspect` | `"pass": true`: neither source element id is present, and the destination arm keys are byte-identical to the R2 fixture. **STOP** otherwise. |

## Installation (SFM closed)

| # | Action | Expected |
|---|---|---|
| I1 | `nq1_tool.py … install` | `INSTALLED`. The journal is written first. `usermod\scripts\ChadChan3D_CPM\SFM_Character_Preset_Manager.py` = qualification CPM; `usermod\scripts\SFM Character Tools\cpm_pose_profiles_v1.json` = the profiles. |
| I2 | `nq1_tool.py … check` | `"installation": "qualification"`. |

## Process A: save the two poses

The observer runs from SFM's Script Editor. Each run writes the next `<Q>\observations\OBS-NN.json` and prints one
`WROTE` line. Type this once per process:
`NQ1_DIR = r"E:\SFM_U0B_Scratch\f01-stage-d-nq1"`. Then, for each observation:
`execfile(r"<REPO>\real_sfm_qualification\f01_stage_d_nq1\observer\F01_NQ1_Observe.py")`.

| # | Action | Expected / STOP |
|---|---|---|
| A1 | Start SFM. Open `<Q>\sessions\NQ1_SOURCE.dmx`. Set the playhead to **0.4167 s** (frame 10, shot10). | |
| A2 | Scripts > SFM Character Tools > Character Preset Manager. Refresh Models, select **Krystal**, then click the **Poses** tab. | Tabs: Body Presets, Expressions, Clothing Fit, Poses, and Review if shown. **All fit without scroll buttons (U-1).** Save New is enabled. "No poses saved for Krystal yet…" |
| A3 | Save New, name `NQ1 Pose A`, then Save. | Status `Pose saved: NQ1 Pose A (Left arm).` The list shows the pose. STOP on any refusal. |
| A4 | Observe (OBS-01). | `WROTE OBS-01.json  shot=shot10 head=0.4167…` |
| A5 | Set the playhead to **0.3750 s** (frame 9, shot13). In CPM: Refresh Models, select **Krystal**, then the Poses tab (switch away and back if Save New is disabled). Save New, `NQ1 Pose B`, then Save. | `Pose saved: NQ1 Pose B (Left arm).` |
| A6 | Observe (OBS-02). | `shot=shot13 head=0.375…` |
| A7 | Exit SFM. **Do not save.** Confirm with `tasklist` that no `sfm.exe` remains. | Process A has ended. |

## Process B: a new SFM process with the destination session

| # | Action | Expected / STOP |
|---|---|---|
| B1 | Start SFM. Open `<Q>\sessions\NQ1_DESTINATION.dmx`. Set the playhead to **0.2083 s** (frame 5, shot15). Open CPM, Refresh Models, select **Krystal**, then the Poses tab. | Both poses are listed, loaded from disk. |
| B2 | Observe (OBS-03): the baseline. | `shot=shot15 head=0.2083…` |
| B3 | Select `NQ1 Pose A`, then **Apply Pose**. Wait until the status leaves `Checking the applied pose...`. | `Pose applied: NQ1 Pose A (Left arm).` Edit > Undo names `Apply Pose NQ1 Pose A`. If the status is `Pose keys were written, but CPM couldn't verify…`, observe once, then STOP. |
| B4 | Observe (OBS-04). | |
| B5 | Click the SFM viewport, then press **Ctrl+Z** once. Observe (OBS-05). | The arm returns to its baseline. |
| B6 | Press **Ctrl+Y** once. Observe (OBS-06). | The arm takes Pose A again. |
| B7 | In CPM, with `NQ1 Pose A` still selected, press **Apply Pose** again. Observe (OBS-07). | `Already matches this pose.` No new Undo entry. |
| B8 | Select `NQ1 Pose B`, then **Apply Pose**. Wait for the final status. Observe (OBS-08). | `Pose applied: NQ1 Pose B (Left arm).` This is an **update** of the key inserted in B3. |
| B9 | In the Script Editor run `import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"`. Then select `NQ1 Pose A` and press **Apply Pose**. Observe (OBS-09). | `The pose couldn't be applied. Nothing was changed.` (The injected failure follows the writes; CPM aborts and verifies.) The arm still shows Pose B, and Undo still names `Apply Pose NQ1 Pose B`. If the message says CPM couldn't confirm the scene, observe once, then STOP. |
| B10 | Ctrl+Z once. Observe (OBS-10). | The arm returns to Pose A. |
| B11 | Ctrl+Z once more. Observe (OBS-11). | The arm returns to the baseline. |
| B12 | Exit SFM. **Do not save.** Confirm that no `sfm.exe` remains. | |

The fault line in B9 works only in the qualification build (`PROD_POSE_QUAL_FAULT` is ignored unless the build's
registry mode is `qualification`) and fires once.

## T: time probe (investigation of the process A STOP; read-only, published CPM, CPM not opened)

Process A refused Save Pose: `channel Elbow_l_p: converted 50208 != reported 50299`. W2's accepted native evidence
shows `GetCurrentTime` = 50299 at both shot10 / 0.4167 s and shot15 / 0.2083 s, but both are 416 ticks after their
shot's start, so it cannot tell whether that value follows the playhead. This probe decides it.

| # | Action | Expected |
|---|---|---|
| T1 | Start SFM. Open `<Q>\sessions\NQ1_SOURCE.dmx`. In the Script Editor: `NQ1_DIR = r"<Q>"`. | |
| T2 | For each playhead time in order, **0.4167 s, 0.4583 s, 0.3750 s, 0.2083 s, 0.4167 s**, set the playhead and run `execfile(r"<REPO>\real_sfm_qualification\f01_stage_d_nq1\observer\F01_NQ1_TimeProbe.py")`. | One `WROTE PROBE-NN.json` line per time (PROBE-01 … PROBE-05), `problems=[]`. |
| T3 | Exit SFM. **Do not save.** | |

| If `reported` … | Then |
|---|---|
| stays the same while `converted` changes with the playhead | `GetCurrentTime` does not follow the playhead; it is not a witness to the evaluation time (correction A). |
| equals `converted` + the same offset at every time | SFM evaluates at a different time than CPM converts to; the conversion is wrong. STOP: no insert may be made at the converted time. |
| anything else | Report; no correction is chosen. |

## R: restore (always; SFM closed)

| # | Action | Expected |
|---|---|---|
| R1 | `nq1_tool.py … restore` | `RESTORED`. Published CPM `ccbed9d7…` back in place. Profile file removed. The run's `Poses` folder moved into `<Q>\evidence\library_poses`. Housekeeping and `.pyc` restored. Every inventory (`usermod\scripts`, `usermod\cfg`, preset library, sessions) equals its pre-run baseline. Re-run it if it was interrupted. |
| R2 | `nq1_tool.py … check` | `"installation": "published"`. |
| R3 | Copy the CPM log files written during the run from `C:\Users\Public\Documents\SFM Character Preset Manager Logs` into `<Q>\evidence\logs`. | They hold the `PROD_POSE_P1` / `P6` / `P7-verified` / `abort-verified` lines. |
| R4 | `python -I …\tools\nq1_compare.py <Q>\nq1.json` | `"verdict": "PASS"` in `<Q>\evidence\NQ1_VERDICT.json`. |

## Expected evidence

| Requirement | Evidence |
|---|---|
| **Persistence across a restart** | OBS-01/02 and OBS-03…11 have different process ids. The destination observations list no source element id (`1a2aab02…`, `21cffbd7…`). `destination_inspection.json` passes. Both pose files are unchanged from process A through B. The CPM log shows the destination instance pinned in `PROD_POSE_P1`. |
| **Key creation (insert)** | OBS-04 against OBS-03: each written channel has exactly one more key, at 50208 ticks, with every other key identical. `Elbow_l_o` is untouched. The CPM log `PROD_POSE_P1` plans `insert` at index 2. |
| **Update** | OBS-08 against OBS-04: the same key times and counts; only the 50208-tick key values change. The CPM log plans `update`. |
| **Rig inputs, skeletal result, placement** | In OBS-04 and OBS-08 the rig inputs equal the written key values. The left upper arm, lower arm and hand local orientations match the pose's oracle within 0.01°. Every other bone's **local** (parent-relative) transform, the model, rig_root
and CollarL are unchanged; world-space movement of the fingers and twist bones with the arm is not compared (in this
fixture both left twist bones and all fingers are driven only by their own channels). Every other channel's authored
keys, in every shot, have the same digest as in OBS-03 throughout process B. CPM's own P7 result is `committed-verified` (`PROD_POSE_P7-verified`). |
| **Undo / Redo** | OBS-05 equals OBS-03 exactly (keys). OBS-06 equals OBS-04. OBS-10 equals OBS-04. OBS-11 equals OBS-03. The Undo descriptions are `Apply Pose NQ1 Pose A` / `Apply Pose NQ1 Pose B`. |
| **True no-op** | OBS-07: keys and the Undo/Redo state equal OBS-06; status `Already matches this pose.` |
| **Recovery (Abort)** | OBS-09 equals OBS-08 exactly, including the Undo/Redo state (the Redo stack is empty there, as W2 qualified). Status `The pose couldn't be applied. Nothing was changed.` The CPM log has `PROD_POSE_abort-verified`. |
| **Restoration** | `restore.json`: `"restored": true`; `check` reports the published installation. |

Recovery-unverified (a failed Abort) and committed-unverified are covered offline only. They are not provoked natively:
provoking them would leave the scene in a state CPM itself cannot confirm.

## What is not covered

- Right arm, both arms, Choose Parts, other-character poses, Rename, Delete and Favorites (not in Stage D).
- Production-build availability: the production registry has no qualified mapping until this checkpoint's evidence
  qualifies one. In the production build the Poses page shows "this arm isn't supported" and Apply stays disabled.
