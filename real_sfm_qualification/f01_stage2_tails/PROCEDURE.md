# F-01 Stage 2: native Tails JIGGLE leaf qualification (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** the Designer's "F-01 Stage 2 — Native Tails Qualification Preparation" (ACCEPT the offline
implementation for native preparation; checkpoint `208a977`); Astra's ruling
(`cpm/qualification/F01_STAGE2_ASTRA_JIGGLE_RULING.md`); record `F01_STAGE2_JIGGLE_LEAF_IMPLEMENTATION.md`.

**What it checks.** Two SFM processes on one disposable session copy.
- **Process A:** two **fresh** Tails instances are created, and both are rigged with the installed stock biped rig:
  - **Tails S**, the source, posed distinctly;
  - **Tails D**, the destination, posed and placed differently.

  Tails S's Full body is saved, and the session copy is saved.
- **Process B, after a restart:** Apply to Tails D, navigation, Undo and Redo.
- **Peer:** the session's original Tails (`milestailsprower1`, an older rig) is the untouched peer. An older saved rig
  is never assumed to match a new one.

Abort is not repeated: Stage 1's transaction and Abort evidence is reused, because those paths are unchanged.

The ears, hair and tail tips (`ear3_L/R`, `HairSpike_B3/M3/T3`, `Tail6_L/R`) are SFM's simulated JIGGLE outputs. CPM
never writes them, and their simulated positions are never required to match.

| Item | Value |
|---|---|
| Candidate CPM | `001377f9…` (Stage 2) |
| Qualification build | `7d3ed720…` (one line, the registry mode, line 42630) |
| Registries | `f445d5ef…` (poses), `a2254930…` (body; Krystal only, unchanged) |
| Sessions | `S2T_SESSION.dmx`: a verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s), the **disposable** session, prepared and saved once in Process A. `S2T_SPARE.dmx` is copied by the reused pre and never opened. The R2 fixture itself is only read |
| Capture | `observer/F01_S2T_Capture.py`: the Fox capture, unchanged and pinned, plus a read-only leaf sidecar |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_stage2_tails\tools\s2t_tool.py <Q>\s2t.json <command>` |
| Protected | `usermod\scripts`, `usermod\cfg`, the preset library, the SFM sessions folder; the published CPM `ccbed9d7…`, both registries absent, `.pyc` and housekeeping files |

**Never:**
- touch the original Tails (`milestailsprower1`) or any other character;
- save any session except `S2T_SESSION.dmx`, once, at A8, and never use "Save As";
- save in Process B;
- change the shot, or leave the playhead anywhere but 0.2083 s at a capture;
- use Update, Delete, Rename or Favorite;
- apply any other pose or preset;
- Undo or Redo more than listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `s2t.template.json` to `<Q>\s2t.json` (a new run folder, `f01-stage2-tails-r1`); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: … 7d3ed720… differs from the candidate in line 42630 only` |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (S2T): … preset library backed up` |
| P3 | `install`, then `check` | `"installation": "qualification"` |

## Process A: preparation and Save (Owner)

**Setup line.** Submit it at step A5 with the two names SFM gave the new Tails instances, and again at B2:
```
S1F_DIR = r"<Q>"; S1F_SOURCE = "<Tails S>"; S1F_TARGET = "<Tails D>"; S1F_PEER = "milestailsprower1"
```

**Capture line.** Only the step name changes, and each step is captured once:
```
S1F_STEP = "PREP"; execfile(r"<REPO>\real_sfm_qualification\f01_stage2_tails\observer\F01_S2T_Capture.py")
```

Each capture prints two lines:
- `S1F <step>: Fox S rig_root | Fox D rig_root | peer … | undo … | errors none | written`. This is the reused Fox
  capture: "Fox S" and "Fox D" mean Tails S and Tails D.
- `S2T <step>: simulated leaves Tails S 7 | Tails D 7 | header READ READ | sidecar written`.

1. **Open the session.** Start SFM and choose **File > Open** `<Q>\sessions\S2T_SESSION.dmx`. Check: Motion Editor,
   shot15, playhead **0.2083 s** as opened. If not, STOP.
2. **Create two Tails.** In the Animation Set Editor, choose **Create Animation Set for New Model**
   `models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl`, **twice**. Note the two names: the first is
   **Tails S**, the second is **Tails D**.
3. **Rig both.** Right-click each new Tails and choose **Rig > rig_biped_simple**.
4. **Pose them at 0.2083 s** in the Motion Editor:
   - **Tails S**, using rig handles:
     - bend the spine (`rig_spine_1`) and turn the head (`rig_head`);
     - raise one arm and bend the other (move `rig_hand_L` and `rig_hand_R`);
     - lift one foot (`rig_foot_R`) and its toe (`rig_toe_R`);
     - curl a few fingers.

     Then turn the directly animated ears, hair spikes and tails with their own controls (for example `ear_L`,
     `ear2_L`, `HairSpike_M1`, `Tail2_L`, `Tail4_R`). The tips have no controls; leave them alone.
   - **Tails D:** move its `rig_root` a few hundred units away from Tails S and turn it. Then pose it differently with a
     couple of rig handles (for example both hands down, head turned the other way).

   **Finish all posing before step 5.** From the PREP capture until you exit at A8, change no control, handle or key
   of any character.
5. **Capture PREP.**
   - Open **Character Preset Manager**, choose **Refresh Models** and select **Tails S**.
   - Submit the setup line, then capture **PREP**.
   - Expected: `S2T PREP: simulated leaves Tails S 7 | Tails D 7 | header READ READ`, errors none.
   - If either count is not 7, or the first line does not show `rig_root` for both: capture nothing more, exit
     **without saving** and report the two lines. CPM's log keeps the exact reason.
6. **Save the pose.** With Tails S selected, choose **Poses: Save New**, keep **Full body**, and name it `S2 Tails`.
   - Choose **Save**. Expected: `Pose saved: S2 Tails.`
   - If Full body is refused, note the exact message, capture **SAVED**, exit **without saving** and report. A safe
     refusal is not a pass.
7. **Capture SAVED.**
   - Select `S2 Tails` in the Poses list and open **Pose Info**. Expected: Type Full body, and no "Can't be applied"
     note.
   - Close Pose Info, keep `S2 Tails` selected, and capture **SAVED**.
8. **Save the session copy.** Choose **File > Save** (this saves `<Q>\sessions\S2T_SESSION.dmx`; never use Save As).
   Then exit SFM.

## Process B: Apply after the restart (Owner)

1. **Reopen.** Start SFM and choose **File > Open** `<Q>\sessions\S2T_SESSION.dmx`.
   - Check: Motion Editor, shot15, playhead **0.2083 s**, and both new Tails present, rigged and posed as you left
     them.
   - If not, STOP; this is a preparation failure.
2. **Capture BASE.**
   - Open **Character Preset Manager**, choose **Refresh Models**, select **Tails D**, and select `S2 Tails` in the
     Poses list.
   - Expected: **Apply Pose is enabled.** If not, capture BASE anyway, exit **without saving** and report.
   - Submit the setup line again (same names) and capture **BASE**.
3. **Apply.** Choose **Apply Pose** `S2 Tails`. Note the message (`Pose applied: S2 Tails.`) and capture **APPLY**.
4. **Inspect** (no capture). Check that:
   - Tails D takes Tails S's body posture: spine, neck, head, arms, hands, fingers, legs, feet, toes, ears, hair and
     tails;
   - Tails D stays where it was, facing as it was, with correct proportions;
   - nothing is severely deformed. The simulated ear, hair and tail **tips** may sit a little differently; that is
     acceptable;
   - Tails S and the original Tails did not change.

   Note what you see; screenshots are welcome.
5. **Navigate.** In the timeline, press **Left arrow** once, then **Right arrow** once. The playhead reads
   **0.2083 s** again, and Tails D still shows the pose. Capture **NAV**.
6. **Undo.** The **Edit** menu must read **Undo Apply Pose S2 Tails**. Choose it once, then capture **UNDO**.
7. **Redo.** Choose **Edit > Redo Apply Pose S2 Tails** once, then capture **REDO**.
8. **Exit** SFM **without saving**. Report each message, what you saw at step 4 and anything unexpected.

## STOP conditions

Exit SFM **without saving** (except at step A8) and report. Claude still runs `library Q`, `collect-logs`, `restore`,
`check` and `analyze`. Stop when:
- a capture prints errors other than `none`, or refuses;
- the leaf count is not 7, or Tails S's Full body is refused (a safe refusal, not a pass), or Apply Pose is disabled at
  B2;
- Apply changes Tails S or the original Tails, damages Tails D's existing animation, leaves a body part clearly
  unposed, moves Tails D's placement or deforms it severely;
- the Edit menu does not name `Apply Pose S2 Tails`, or Undo or Redo does not restore;
- a recovery message appears;
- SFM crashes, shows a recovery prompt or hangs for more than a minute.

A small difference in a simulated tip, or an adjustment an artist would routinely make, is not a STOP.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q` | the saved Tails pose (and the new character files) only |
| R2 | `collect-logs` | the CPM logs of both processes |
| R3 | `restore`, then `check` | library cleanup exact, `RESTORED`; `"installation": "published"` |
| R4 | `analyze` | `S2T_VERDICT.md` |

**Verdict** (`tools/s2t_analyze.py`):
- **AUTOMATED PASS:** EVIDENCE, PREP, SAVE, APPLY, POSTURE, HISTORY, LEAVES and PEER all pass. Acceptance also needs the
  Owner's visual assessment (step B4).
- **REFUSED:** Tails S's Full body was refused. This is safe, but not a compatibility pass; the exact reasons are
  reported from CPM's log (for example an attachment or bone flex driver using a leaf).
- **FAIL:** the evidence is complete and a functional gate failed.
- **INCOMPLETE:** evidence, the fixture preparation or restoration failed.

A gate with no evaluated check is shown as **NOT EVALUATED**, never PASS.

**Tolerances** (as in the Fox qualification):
- **Posture,** independent of CPM's planner: SFM's evaluated non-leaf bones of Tails D, relative to its own `rig_root`,
  against Tails S's at Save, within 0.05 units and 0.5°.
- **Placement, facing, offsets and peers** unchanged within 0.001 units and 0.01°.
- **Authored state** (every channel, the leaves' included), scales and header declarations are compared exactly. The
  reopened session is compared under the measured load renormalization of quaternion keys.
- **Simulated tip transforms** are recorded for information only, never gated.
