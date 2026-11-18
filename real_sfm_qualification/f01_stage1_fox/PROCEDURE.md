# F-01 Stage 1: native Fox structural-rig qualification (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** "F-01 Stage 1 — Offline Acceptance and Native Qualification Preparation" (Designer: ACCEPT offline
implementation for native qualification, commit `fc534c3`); record `cpm/qualification/F01_STAGE1_STRUCTURAL_RIG_SUPPORT.md`.

**What it checks.** Two SFM processes on one disposable session copy:
- **Process A:** Fox B is prepared (a second, stock-rigged, differently posed and placed Fox), Fox A's Full body is
  saved, and the session copy is saved.
- **Process B, after a restart:** the saved pose is applied to Fox B, then navigation, Undo, Redo, a repeat no-op,
  a final Undo, and one controlled Abort after the mixed rig and FK writes.
- **Peers:** Fox A and Tails stay unchanged throughout. Tails' expected refusal is recorded.
- **Not in this run:** Krystal (offline regression only) and Stage 2.

| Item | Value |
|---|---|
| Stage 1 candidate CPM | `35c400c1…` (`fc534c3`) |
| Qualification build | `5ac0e9d6…` (one line, the registry mode, line 42597) |
| Registries | `f445d5ef…` (poses), `a2254930…` (body; Krystal only, unchanged) |
| Sessions | `S1_SESSION.dmx`: a verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s), the **disposable** session, prepared and saved once in Process A. `S1_SPARE.dmx` is copied by the reused pre and never opened. The R2 fixture itself is only read |
| Capture | `observer/F01_S1F_Capture.py` (read only) |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_stage1_fox\tools\s1f_tool.py <Q>\s1f.json <command>` |
| Protected | `usermod\scripts`, `usermod\cfg`, the preset library, the SFM sessions folder; the published CPM `ccbed9d7…`, both registries absent, `.pyc` and housekeeping files |

**Never:**
- touch Fox A or Tails, apart from selecting them;
- save any session except `S1_SESSION.dmx` once at step A9, and never "Save As";
- save in Process B;
- change the shot, or leave the playhead anywhere but 0.2083 s at a capture;
- use Update, Delete, Rename or Favorite;
- apply any other pose or preset;
- Undo or Redo more than listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `s1f.template.json` to `<Q>\s1f.json` (a new run folder); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: … 5ac0e9d6… differs from the candidate in line 42597 only` |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (S1F): preset library backed up` |
| P3 | `install`, then `check` | `"installation": "qualification"` |

## Process A: preparation and Save (Owner)

**Setup line.** Submit it once, at step A5. Use the names SFM shows: Fox A is `foxmccouldwm1`, Fox B is the new set,
Tails is `milestailsprower1`.
```
S1F_DIR = r"<Q>"; S1F_SOURCE = "foxmccouldwm1"; S1F_TARGET = "<Fox B>"; S1F_PEER = "milestailsprower1"
```

**Capture line.** Only the step name changes, and each step is captured once:
```
S1F_STEP = "PREP"; execfile(r"<REPO>\real_sfm_qualification\f01_stage1_fox\observer\F01_S1F_Capture.py")
```
Each capture prints `S1F <step>: Fox A rig_root | Fox B rig_root | peer structure-unsupported | undo … | errors none | written`.

1. **Open the session.** Start SFM and choose **File > Open** `<Q>\sessions\S1_SESSION.dmx`. Check: Motion Editor,
   shot15, playhead **0.2083 s** as opened. If not, STOP.
2. **Create Fox B.** In the Animation Set Editor, choose **Create Animation Set for New Model**
   `models/fursonas/foxmccouldwm.mdl`, once. Note its name.
3. **Rig Fox B.** Right-click Fox B and choose **Rig > rig_biped_simple** (SFM's stock biped rig, as on Fox A).
4. **Pose and place Fox B visibly differently**, at 0.2083 s in the Motion Editor, using **rig handles only**:
   - move `rig_root` well away from Fox A (a few hundred units) and turn it;
   - rotate `rig_spine_1`, `rig_neck` and `rig_head`;
   - move `rig_hand_L` and `rig_hand_R` (bending the elbows);
   - move `rig_foot_R` and lift `rig_toe_R`;
   - optionally, curl one hand's fingers.

   Do not touch Fox A or Tails.
5. **Capture PREP.** Open **Character Preset Manager**, choose **Refresh Models**, select **Fox A**. Submit the setup
   line, then capture **PREP**. Expected: `Fox A rig_root | Fox B rig_root | peer structure-unsupported`, errors
   none. If Fox A or Fox B is not `rig_root`, capture nothing more, exit **without saving** and report.
6. **Save the pose.** With Fox A selected, choose **Poses: Save New → Full body**, name `S1 Fox`.
   - Expected dialog: Full body is available, and Review scope lists `JAW` and the tongue bones.
   - Leave "Leave these controls unchanged" **unchecked**. Note the summary, choose **Save**, and note the result
     message (`Pose saved: S1 Fox.`).
   - If Full body is refused, note the exact message, capture **SAVED**, exit without saving and report.
7. **Capture SAVED.** Select `S1 Fox` in the Poses list and open **Pose Info**: Type Full body, Not included facial
   expressions and rootTransform. Close it, keep `S1 Fox` selected, and capture **SAVED**.
8. **Tails (expected safe refusal).** Select **Tails**, choose **Save New**, and note what the dialog shows for Full
   body (expected: the rig refusal, Save disabled). Choose **Cancel**. Select Fox A again.
9. **Save the session copy.** **File > Save** (this saves `<Q>\sessions\S1_SESSION.dmx`; never Save As). Then exit
   SFM.

## Process B: Apply after the restart (Owner)

1. **Reopen.** Start SFM and **File > Open** `<Q>\sessions\S1_SESSION.dmx`. Check: Motion Editor, shot15, playhead
   **0.2083 s**, Fox B present, rigged and posed as you left it. If Fox B is missing or not as left, STOP; this is a
   preparation failure.
2. **Capture BASE.** Open **Character Preset Manager**, choose **Refresh Models** and select **Fox B**. In the Poses
   list, select `S1 Fox` (the reopened pose). Submit the setup line again (same names) and capture **BASE**.
3. **Apply.** Choose **Apply** `S1 Fox`. Note the message (`Pose applied: S1 Fox.`) and capture **APPLY**.
4. **Inspect** (no capture). Check that:
   - Fox B takes Fox A's body posture: spine, neck, head, arms, hands, legs, feet, toes, fingers and tails;
   - Fox B stays in its own place and keeps its proportions;
   - nothing is severely distorted;
   - Fox A and Tails did not change.

   Note what you see; screenshots are welcome.
5. **Navigate.** In the timeline, press **Left arrow** once, then **Right arrow** once. The playhead reads
   **0.2083 s** again, and Fox B still shows the pose. Capture **NAV**.
6. **Undo.** The **Edit** menu must read **Undo Apply Pose S1 Fox**. Choose it once, then capture **UNDO**.
7. **Redo.** Choose **Edit > Redo Apply Pose S1 Fox** once, then capture **REDO**.
8. **Repeat Apply.** With Fox B still selected, **Apply** `S1 Fox` again. Expected: `Already matches this pose.`.
   Capture **NOOP**.
9. **Final Undo.** Choose **Edit > Undo Apply Pose S1 Fox** once more. Capture **UNDO2**.
10. **Controlled Abort.** In the Script Editor, run:
    ```
    import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"
    ```
    Then, with Fox B and `S1 Fox` selected, choose **Apply**. Expected: `The pose couldn't be applied. Nothing was
    changed.`, Fox B looks as at step 9, and the Edit menu is as at step 9. Capture **ABORT**.
11. **Exit** SFM **without saving**. Report each message, what you saw at step 4 and anything unexpected.

## STOP conditions

Exit SFM **without saving** (except step A9) and report. Claude still runs `library Q`, `collect-logs`, `restore`,
`check` and `analyze`. Stop when:
- a capture prints errors other than `none`, or refuses;
- Fox A's Full body is refused: report the exact message (this is a safe refusal, not a pass);
- Apply writes to Fox A or Tails, damages Fox B's existing animation, leaves a body part clearly unposed, moves
  Fox B's placement or distorts it severely;
- the Edit menu does not name `Apply Pose S1 Fox`, Undo or Redo does not restore, the Abort leaves anything changed,
  or a recovery message appears;
- SFM crashes, shows a recovery prompt or hangs for more than a minute.

A small difference in a secondary part, or an adjustment an artist would routinely make, is not a STOP.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q` | the saved Fox pose (and the new character files) only |
| R2 | `collect-logs` | the CPM logs of both processes |
| R3 | `restore`, then `check` | library cleanup exact, `RESTORED`; `"installation": "published"` |
| R4 | `analyze` | `S1F_VERDICT.md` |

`S1_SESSION.dmx` stays in the run folder as the record of the fixture preparation; its hash is in the verdict. The R2
fixture and the Owner's sessions folder are unchanged.

**Verdict** (`tools/s1f_analyze.py`):
- **AUTOMATED PASS:** EVIDENCE, PREP, SAVE, APPLY, POSTURE, HISTORY, ABORT, PEER and TAILS all pass. Stage 1 is
  accepted natively only with it **and** the Owner's visual acceptance (step B4).
- **REFUSED:** Fox A's Full body was refused. This is safe, but Stage 1 is not qualified.
- **FAIL:** the evidence is complete and a functional gate failed.
- **INCOMPLETE:** evidence, the fixture preparation or restoration failed.

The posture gate is independent of CPM's planner. It compares SFM's evaluated bone transforms of Fox B, relative to
its own `rig_root`, with Fox A's at Save:
- usable-reproduction tolerance: 0.05 units and 0.5°, with the maxima reported;
- placement, offsets and peers unchanged within 0.001 units and 0.01°.
