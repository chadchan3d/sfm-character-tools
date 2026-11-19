# F-01 Stage 1: native Fox structural-rig qualification, run 3 (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:**
- "F-01 Stage 1 — Native Findings Disposition" (Designer: C1, C3–C6 approved, C2 revised) and the C2 clarification
  on facial controls;
- Astra's numerical compatibility ruling (ACCEPT WITH CONDITIONS) and "F-01 Stage 1 — Implement Astra's Numerical
  Compatibility Ruling";
- records `cpm/qualification/F01_STAGE1_FOX_NATIVE_FINDINGS.md`, `F01_STAGE1_RUN2_CORRECTIONS.md`,
  `F01_STAGE1_FOX_RUN2_FINDINGS.md` and `F01_STAGE1_NUMERICAL_COMPATIBILITY.md`.

Run 3 is the corrected Fox continuation of run 2, with the same steps, in a new folder `f01-stage1-fox-r3`. Runs 1 and 2
(`f01-stage1-fox-r1`, `f01-stage1-fox-r2`, both INCOMPLETE) stay preserved as they are.

**What it checks.** Two SFM processes on one disposable session copy.
- **Process A:** two **fresh** Foxes are created and both rigged with the **installed** stock biped rig:
  - **Fox S**, the source, posed distinctly (jaw included);
  - **Fox D**, the destination, posed and placed differently.

  Fox S's Full body is saved, and the session copy is saved.
- **Process B, after a restart:** Apply to Fox D, navigation, Undo, Redo, a repeat no-op, a final Undo, and one
  controlled Abort after the mixed rig and FK writes.
- **Peers and controls:**
  - the session's original Fox (`foxmccouldwm1`, an older rig) is the untouched peer;
  - Tails' Save New refusal is checked.

  Krystal needs offline regression only, and Stage 2 is not in this run.

| Item | Value |
|---|---|
| Candidate CPM | `2088b4af…` (Stage 1 with the run 1 corrections and Astra's numerical compatibility ruling) |
| Qualification build | `b195515f…` (one line, the registry mode, line 42609) |
| Registries | `f445d5ef…` (poses), `a2254930…` (body; Krystal only, unchanged) |
| Sessions | `S1_SESSION.dmx`: a verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s), the **disposable** session, prepared and saved once in Process A. `S1_SPARE.dmx` is copied by the reused pre and never opened. The R2 fixture itself is only read |
| Capture | `observer/F01_S1F_Capture.py` (read only) |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_stage1_fox\tools\s1f_tool.py <Q>\s1f.json <command>` |
| Protected | `usermod\scripts`, `usermod\cfg`, the preset library, the SFM sessions folder; the published CPM `ccbed9d7…`, both registries absent, `.pyc` and housekeeping files |

**Never:**
- touch the original Fox (`foxmccouldwm1`) or Tails, apart from selecting Tails at A8;
- save any session except `S1_SESSION.dmx` once at A9, and never "Save As";
- save in Process B;
- change the shot, or leave the playhead anywhere but 0.2083 s at a capture;
- use Update, Delete, Rename or Favorite;
- apply any other pose or preset;
- Undo or Redo more than listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `s1f.template.json` to `<Q>\s1f.json` (a new run folder, `f01-stage1-fox-r3`); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: … b195515f… differs from the candidate in line 42609 only` |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (S1F): preset library backed up` |
| P3 | `install`, then `check` | `"installation": "qualification"`. There is no seed step; ignore the reused tool's "Next: seed" |

## Process A: preparation and Save (Owner)

**Setup line.** Submit it once, at step A5, with the two names SFM gave the new Foxes:
```
S1F_DIR = r"<Q>"; S1F_SOURCE = "<Fox S>"; S1F_TARGET = "<Fox D>"; S1F_PEER = "foxmccouldwm1"
```

**Capture line.** Only the step name changes, and each step is captured once:
```
S1F_STEP = "PREP"; execfile(r"<REPO>\real_sfm_qualification\f01_stage1_fox\observer\F01_S1F_Capture.py")
```
Each capture prints `S1F <step>: Fox S rig_root | Fox D rig_root | peer rig_root | undo … | errors none | written`.

1. **Open the session.** Start SFM and choose **File > Open** `<Q>\sessions\S1_SESSION.dmx`. Check: Motion Editor,
   shot15, playhead **0.2083 s** as opened. If not, STOP.
2. **Create two Foxes.** In the Animation Set Editor, choose **Create Animation Set for New Model**
   `models/fursonas/foxmccouldwm.mdl`, **twice**. Note the two names: the first is **Fox S**, the second **Fox D**.
3. **Rig both.** Right-click each new Fox and choose **Rig > rig_biped_simple**.
4. **Pose them at 0.2083 s** in the Motion Editor:
   - **Fox S**, using rig handles:
     - bend the spine (`rig_spine_1`) and turn the head (`rig_head`);
     - raise one arm and bend the other (move `rig_hand_L` and `rig_hand_R`);
     - lift one foot (`rig_foot_R`) and its toe (`rig_toe_R`);
     - curl a few fingers of one hand, and open the jaw (`JAW`).
   - **Fox D:** move its `rig_root` a few hundred units away from Fox S and turn it, then pose it differently with a
     couple of rig handles (for example both hands down, head turned the other way).

   Do not touch the original Fox or Tails.

   **Finish all posing before step 5.** From the PREP capture until you exit at A9, change no control, handle or key
   of any character. The analyzer requires the saved session to match the PREP capture exactly (in run 2, posing
   continued after PREP).
5. **Capture PREP.** Open **Character Preset Manager**, choose **Refresh Models**, select **Fox S**. Submit the setup
   line, then capture **PREP**. Expected: `Fox S rig_root | Fox D rig_root | peer rig_root`, errors none. If Fox S or
   Fox D is not `rig_root`, capture nothing more, exit **without saving** and report.
6. **Save the pose.** With Fox S selected, choose **Poses: Save New**, keep **Full body**, and name it `S1 Fox`.
   - Expected: no face review box, and the summary "Facial expressions and the rootTransform are not saved."
   - Choose **Save**. Expected: `Pose saved: S1 Fox.`
   - If Full body is refused, note the exact message, capture **SAVED**, exit without saving and report.
7. **Capture SAVED.** Select `S1 Fox` in the Poses list and open **Pose Info**: Type Full body, no "Can't be applied"
   note. Close it, keep `S1 Fox` selected, and capture **SAVED**.
8. **Tails (expected safe refusal).** Select **Tails** and choose **Save New**. The Full body summary is expected to
   read exactly "Full body poses aren't supported for this character yet. You can still save Selected parts.", with
   Save disabled. Choose **Cancel**, then select Fox S again.
9. **Save the session copy.** **File > Save** (this saves `<Q>\sessions\S1_SESSION.dmx`; never Save As). Then exit
   SFM.

## Process B: Apply after the restart (Owner)

1. **Reopen.** Start SFM and **File > Open** `<Q>\sessions\S1_SESSION.dmx`. Check: Motion Editor, shot15, playhead
   **0.2083 s**, and both new Foxes present, rigged and posed as you left them. If not, STOP; this is a preparation
   failure.
2. **Capture BASE.** Open **Character Preset Manager**, choose **Refresh Models**, select **Fox D**, and select
   `S1 Fox` in the Poses list.
   - Expected: **Apply Pose is enabled**. If not, capture BASE anyway, exit without saving and report.
   - Submit the setup line again (same names) and capture **BASE**.
3. **Apply.** Choose **Apply Pose** `S1 Fox`. Note the message (`Pose applied: S1 Fox.`) and capture **APPLY**.
4. **Inspect** (no capture). Check that:
   - Fox D takes Fox S's body posture: spine, neck, head, arms, hands, fingers, legs, feet, toes, tails and the open
     jaw;
   - Fox D stays where it was, facing as it was, with correct proportions;
   - nothing is severely distorted;
   - Fox S and the original Fox did not change.

   Note what you see; screenshots are welcome.
5. **Navigate.** In the timeline, press **Left arrow** once, then **Right arrow** once. The playhead reads
   **0.2083 s** again, and Fox D still shows the pose. Capture **NAV**.
6. **Undo.** The **Edit** menu must read **Undo Apply Pose S1 Fox**. Choose it once, then capture **UNDO**.
7. **Redo.** Choose **Edit > Redo Apply Pose S1 Fox** once, then capture **REDO**.
8. **Repeat Apply.** With Fox D still selected, **Apply Pose** `S1 Fox` again. Expected: `Already matches this pose.`
   Capture **NOOP**.
9. **Final Undo.** Choose **Edit > Undo Apply Pose S1 Fox** once more. Capture **UNDO2**.
10. **Controlled Abort.** In the Script Editor, run:
    ```
    import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"
    ```
    Then, with Fox D and `S1 Fox` selected, choose **Apply Pose**. Expected: `The pose couldn't be applied. Nothing
    was changed.`, Fox D looks as at step 9, and the Edit menu is as at step 9. Capture **ABORT**.
11. **Exit** SFM **without saving**. Report each message, what you saw at step 4 and anything unexpected.

## STOP conditions

Exit SFM **without saving** (except step A9) and report. Claude still runs `library Q`, `collect-logs`, `restore`,
`check` and `analyze`. Stop when:
- a capture prints errors other than `none`, or refuses;
- Fox S's Full body is refused (a safe refusal, not a pass), or Apply Pose is disabled at B2;
- Apply writes to Fox S or the original Fox, damages Fox D's existing animation, leaves a body part clearly unposed,
  moves Fox D's placement or distorts it severely;
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

`S1_SESSION.dmx` stays in the run folder as the record of the fixture preparation; its hash is in the verdict.

**Verdict** (`tools/s1f_analyze.py`):
- **AUTOMATED PASS:** EVIDENCE, PREP, SAVE, APPLY, POSTURE, HISTORY, ABORT, PEER and TAILS all pass. Stage 1 is
  accepted natively only with it **and** the Owner's visual acceptance (step B4).
- **REFUSED:** Fox S's Full body was refused. This is safe, but Stage 1 is not qualified.
- **FAIL:** the evidence is complete and a functional gate failed.
- **INCOMPLETE:** evidence, the fixture preparation or restoration failed.

A gate with no evaluated check is shown as **NOT EVALUATED**, never PASS.

**Tolerances:**
- **Posture,** independent of CPM's planner: SFM's evaluated bones of Fox D, relative to its own `rig_root`, against
  Fox S's at Save, within 0.05 units and 0.5°, with the maxima reported.
- **Placement, offsets and peers** unchanged within 0.001 units and 0.01°.
- **The reopened session** is compared exactly, except that every quaternion key must equal SFM's own load
  renormalization of its Process A value exactly (the float32 function measured in run 2 on all 618 keys). Every
  authored-data, Undo, Abort and restoration check within Process B stays exact.
