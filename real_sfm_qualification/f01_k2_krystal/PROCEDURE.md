# F-01 K2: Krystal version 2 Full body native integration check (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
execution authorization.

**Authority:** Blueprint R4 section 5 (the short integration sequence) and section 12 (work order K), on the K1
offline candidate (`3297ac0`, `F01_K1_KRYSTAL_V2_RESTORATION.md`).

**What it establishes:** that Krystal's existing version 2 Full body works through the current product path (the
SFP-1 Save dialog with the PS-2 interface, K1's dispatch): Save Full body, reopen the saved record in a new SFM
process, Apply it to a visibly different compatible instance, Undo and Redo, Update the record; with placement, a
useful whole-body posture, preservation and recovery checked. **Reused, not repeated:** S3 runs 1–5 for the unchanged
v2 engine (verified Abort, true no-op, update of existing keys, Clip Editor and proportions refusals, navigation, the
v1 left arm).

| Item | Value |
|---|---|
| Candidate CPM | `3984e1e1d5d2018202fa551700564da6796cc1063c2be7a32112ad023db5ae9c` (K1, `3297ac0`) |
| K1 qualification build | `37b0cce608062f2a7e03bab03ee4e590fc3f8c395a2c300538df44e3893b1868` (one line, 42182: `PROD_POSE_REGISTRY_MODE = u"qualification"`) |
| Registries | `cpm_pose_profiles_v1.json` `f445d5ef…`, `cpm_body_profiles_v1.json` `22dcd159…` (Krystal v2 mapping unchanged) |
| Source session | `K2_SOURCE.dmx`: verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s) |
| Destination session | `K2_DESTINATION.dmx`: verified copy of S3's prepared destination `61df8bcd…` (S3 run 1; shot13, 0.3750 s; posed differently and natively compatible in S3 runs 3–5) |
| Observer | the S3 wrapper `F01_S3_Observe.py` and UI smoke check `F01_S3_UISmoke.py`, unchanged (S0 observer `4a358cc0…`) |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_k2_krystal\tools\k2_tool.py <Q>\k2.json <command>` |
| Restored afterwards | the published CPM `ccbed9d7…`; both registries removed; every protected inventory equal to its baseline |

**Never:** save a session; use Selected parts, the right arm, the legacy left arm, Body Presets, Expressions, Delete,
Rename, Favorite or the Updater; apply any pose other than `K2 Pose`. The qualification build exposes experimental
mappings (including the right arm); they are not exercised.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `k2.template.json` to `<Q>\k2.json`; fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: the K1 qualification CPM 37b0cce6… differs from the candidate in line 42182 only` |
| P2 | `pre` | `PRE PASS (K2)` (published installation verified; backups; four inventories; `K2_SOURCE.dmx` and `K2_DESTINATION.dmx` verified copies) |
| P3 | `install`, then `check` | `INSTALLED`; `"installation": "qualification"` |

## Native sequence (Owner)

Once per SFM process, after opening CPM, submit:
```
S3_DIR = r"<Q>"; S3_REPO = r"<REPO>"
```
Observe a step:
```
S3_STEP = "A1"; execfile(S3_REPO + r"\real_sfm_qualification\f01_full_body_s3\observer\F01_S3_Observe.py")
```
(The S3 observer's step table is used: A steps expect shot15 at 0.2083 s, B steps shot13 at 0.3750 s.)

### Process A: Save Full body (K2_SOURCE.dmx)

1. Start SFM. **File > Open** `<Q>\sessions\K2_SOURCE.dmx`. **Motion Editor**, go to **shot15**, playhead
   0.2083 s (frame 5 at 24 fps). Open **Character Preset Manager**, **Refresh Models**, select `Krystal`, **Poses**.
   Submit the setup line. Observe **A1**.
2. **Save New**. Expected: the Save dialog with **Full body** selected and the summary `Facial expressions, gaze and
   the character's place in the scene are not saved.` (the version 2 route; no rig-driven refusal), Save enabled.
   Name it `K2 Pose`, **Save**. Expected: `Pose saved: K2 Pose.` Observe **A2**.
3. Exit SFM **without saving**.

Claude: `library A`.

### Process B: reopen, Apply, Undo, Redo, Update (K2_DESTINATION.dmx)

4. Start SFM. **File > Open** `<Q>\sessions\K2_DESTINATION.dmx`. **Motion Editor**, **shot13**, playhead 0.3750 s
   (frame 9). Open CPM, Refresh Models, `Krystal`, **Poses**. Submit the setup line. Observe **B1**.
5. Select `K2 Pose`, open **Pose Info** (expected: Type `Full body`, Model `krystal2020.mdl`, a Saved Values tree of
   saved controls), close it. Run the UI smoke check:
   ```
   execfile(S3_REPO + r"\real_sfm_qualification\f01_full_body_s3\observer\F01_S3_UISmoke.py")
   ```
   Expected: Apply Pose enabled for a version 2 Full body pose.
6. **Claude runs `precheck`** (SFM stays open; read only). Continue only on `COMPATIBLE and DISTINCT`.
7. **Apply Pose** `K2 Pose`. Expected: `Pose applied: K2 Pose.`; Krystal takes the saved body posture where the
   destination placed her (rig placement unchanged), face unchanged. Note the time. Observe **B2**.
8. Click the viewport, **Ctrl+Z** until Edit > Redo names `Apply Pose K2 Pose` (undo SFM's own recording-state
   entries first if any; never past the Apply). Expected: the destination posture returns. Observe **B3**.
9. **Ctrl+Y** once. Expected: the applied posture. Observe **B4**.
10. Select the **Hip** control and rotate it visibly (about 15°, Rotate tool). Observe **B5**.
11. Select `K2 Pose`, **Update Pose**, confirm. Expected: `Pose updated: K2 Pose.` Observe **B6**.
12. Exit SFM **without saving**. Report the messages, the Apply time, and anything unexpected.

## STOP conditions

Exit SFM **without saving** and report; Claude still runs `library B`, `collect-logs`, `restore`, `check`:
- an observation prints a mismatch (shot, playhead or timeline editor), or a capture refuses;
- step 2 shows a refusal, Selected parts only, or any summary other than the version 2 one; or Save fails;
- step 5: Apply Pose is not enabled for `K2 Pose`;
- step 6: `precheck` is not `COMPATIBLE and DISTINCT` (do not Apply);
- step 7: Apply is refused or ends with "Pose changes are paused…" or "CPM couldn't confirm…"; the character moves
  away from its placement, another character or the face changes;
- step 8 or 9: Undo does not return the destination posture, or Redo does not restore the applied one;
- step 11: Update is refused or changes the scene;
- SFM crashes, shows an autosave recovery prompt, or hangs for more than a minute.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library B` | the run's Poses folder: `K2 Pose--….json` and its Update backup `.json.bak` |
| R2 | `collect-logs` | two CPM logs (Process A, Process B) |
| R3 | `restore`, then `check` | `RESTORED`; `"installation": "published"`; every inventory equal to its baseline |
| R4 | `compare` | `K2_VERDICT.md` |

**PASS** (all `k2_compare` checks): K1 qualification build in every observation; restart between Save and Apply;
version 2 Full body record of the 278-channel mapping capturing the source posture, Save writing nothing; the record
saved in Process A is the one applied; Apply enabled after reopening; precheck compatible and distinct; Apply writes the
record's values with one key each at the mapped tick, reproduces the whole-body posture relative to the unchanged
placement handle with model state, scales and preserved bones unchanged, leaves the instance's other channels, its
facial/gaze controls and all unrelated animation unchanged, with one owned Undo entry; Undo restores the destination,
Redo the applied pose; Update writes nothing to the scene, keeps the record's identity and holds the updated posture;
CPM's log shows the Save verified, Pose Info, one Apply owned and P7-verified, the Update verified, and no recovery or
uncertainty; restoration complete; sessions never saved; performance within the limit. A `K1-generic-inventory-
unavailable` log line is reported as a finding, not a failure.

**Not a PASS by itself:** an Owner observation without the matching machine check. A STOPPED run is restored and
reported STOPPED.
