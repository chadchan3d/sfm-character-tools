# F-01 full-body S3, run 5: legacy left-arm segment (operator procedure)

**Status:** prepared, **not run**.

**Why:** run 4 (`E:\SFM_U0B_Scratch\f01-full-body-s3-r4`) established B9–B12 natively with the corrected candidate:
- the Clip Editor message "Switch to the Motion Editor to apply a pose. Nothing was changed.";
- the proportions refusal;
- no writes.

After a valid B13, `S3 Pose A` was applied to shot15 by mistake, so B13–B17 were invalid. That is recorded in its
`evidence\DEVIATIONS.json`. Run 5 repeats only the legacy segment in a fresh SFM process, with the same candidate
`f6098b3a…` (qualification `12b59b29…`). It takes B11 again, because B11 is the legacy pose's source arm (shot10),
which the pre-check compares against.

`<Q5>` = `E:\SFM_U0B_Scratch\f01-full-body-s3-r5`. The configuration is `s3_legacy.template.json`
(`"supplement_steps": ["B11", "B13", "B14", "B15", "B16", "B17"]`). Preparation and restoration are exactly as in
`PROCEDURE_SUPPLEMENT.md`.

**Stop rule, strictly:** stop at the first `MISMATCH - STOP`, unexpected message or wrong click. Do not take the next
step or try to undo a mistake. Close SFM without saving, then restore.

## Commands (paste into the Script Editor, then click Submit)

- **Setup, once:** `S3_DIR = r"E:\SFM_U0B_Scratch\f01-full-body-s3-r5"; S3_REPO = r"E:\SFM-F01-Pose-Library"`
- **Editor check:** `import sfmApp; print(sfmApp.GetNameForTimelineMode(sfmApp.GetTimelineMode()))`
- **Observe step X:**
  `S3_STEP = "X"; execfile(S3_REPO + r"\real_sfm_qualification\f01_full_body_s3\observer\F01_S3_Observe.py")`

## Steps

| # | Action | Expected |
|---|---|---|
| S0 | Start SFM. Open `<Q5>\sessions\S3_DESTINATION.dmx`. Switch the timeline to the **Motion Editor**. Submit the editor check. | It prints `Motion Editor`. |
| S0b | Set the playhead to **0.4167 s** (shot10). Open CPM. Click **Refresh Model List**, select **Krystal**, then the **Poses** tab. Submit the setup line. | `S3 Pose A`, `S3 Pose B` and `NQ1 Pose A` are listed. |
| B11 | Observe `B11`. | `S3 STEP B11 (S0-18): OK` |
| B13 | Set the playhead to **0.2083 s** (shot15). Click **Refresh Model List**, select **Krystal**, then **Poses**. Observe `B13`. | `S3 STEP B13 (S0-20): OK`, and the summary shows `shot=shot15`. |
| Gate | **Stop. Click nothing in CPM.** Report. The operator (Claude) runs `s3_tool legacy-precheck`. | `LEGACY PRECHECK DISTINCT` |
| B14 | In the Poses list, click **NQ1 Pose A** (check that it is highlighted, not S3 Pose A or B). Click **Apply Pose**. Observe `B14`. | `Pose applied: NQ1 Pose A.` Only the left arm moves, visibly. |
| B15 | Click **Apply Pose** again. Observe `B15`. | `Already matches this pose.` |
| B16 | Click once in the viewport, press **Ctrl+Z** once. Observe `B16`. | The arm returns. |
| B17 | Straight away, without touching the timeline: click once in the viewport, press **Ctrl+Y** once. Observe `B17`. | The arm takes the pose again. |
| B18 | Exit SFM. Choose **No** when asked to save. | |

## Verdict

`s3_tool compare` evaluates the listed steps (supplement mode), checking:
- the pre-check showed a visible difference before the Apply;
- the three left-arm channels were keyed and the arm moved by at least 5°, its bones now equal to the legacy pose's
  source arm within 0.01°;
- everything else is unchanged and there is one owned Undo entry;
- the repeat is a true no-op;
- Undo restores B13 with Redo available, and Redo restores B14;
- CPM's own P6 and P7 verified;
- restoration is complete and the session was not saved.
