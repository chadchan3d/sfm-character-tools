# F-01 RC4: native two-direction Tails cross-rig qualification (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** "F-01 RC4 — Implement Astra's Numerical Compatibility Ruling" (section 4: Astra's bounded two-direction
Tails native test). Records: `cpm/qualification/F01_RC4_CROSS_RIG_ADAPTATION.md`, `F01_RC4_NUMERICAL_BOUNDS.md`.

**What it checks.** One SFM process on one disposable session copy, **never saved**, with the existing, differently
rigged Tails pair:
- **Tails N:** a new Tails, rigged with the installed `rig_biped_simple`: 23 controls, with `rig_chest` driving
  `bip_spine_3`.
- **The original Tails** (`milestailsprower1`): 22 controls, `bip_spine_3` posed directly, as authored in the session
  (sitting).
- **Peer:** the original Fox (`foxmccouldwm1`) is never touched.

Both poses are saved first, then transferred in opposite directions:

| Direction | Pose | From | To |
|---|---|---|---|
| A (chest → direct spine) | `RC4 Chest` | Tails N | the original Tails |
| B (direct spine → chest) | `RC4 Sit` | the original Tails | Tails N |

Each direction includes Apply, navigation, Undo, Redo, a repeated Apply (no-op) and a final Undo. One controlled
Abort is injected after adapted writes. CPM's P7 limits are unchanged; the analyzer measures the skeletal result
independently.

| Item | Value |
|---|---|
| Candidate CPM | the RC4 candidate pinned in `rc4x.template.json` |
| Qualification build | the candidate with only its registry-mode line changed (K2's derivation); needed for the Abort fault line |
| Registries | `f445d5ef…` (poses), `a2254930…` (body; Krystal only, unchanged) |
| Sessions | `RC4X_SESSION.dmx`: a verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s), never saved. `RC4X_SPARE.dmx`: copied by the reused pre, never opened |
| Capture | `observer/F01_RC4X_Capture.py`: the Stage 2 capture (with the Fox capture), unchanged and pinned, plus a read-only offsets sidecar |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_rc4_cross_rig\tools\rc4x_tool.py <Q>\rc4x.json <command>` |
| Protected | `usermod\scripts`, `usermod\cfg`, the preset library, the SFM sessions folder; the published CPM `ccbed9d7…`, both registries absent |

**Never:**
- save the session (no File > Save, no Save As);
- touch the original Fox or Krystal;
- change the shot, or leave the playhead anywhere but 0.2083 s at a capture;
- use Update, Delete, Rename or Favorite;
- apply any other pose or preset;
- Undo or Redo more than listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `rc4x.template.json` to `<Q>\rc4x.json` (a new run folder, `f01-rc4-cross-rig-r1`); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: …` the qualification build, differing from the candidate in the registry-mode line only |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (RC4X): … preset library backed up` |
| P3 | `install`, then `check` | `"installation": "qualification"` |

## Lines to submit in SFM's Script Editor

**Setup line A.** Use it for PREP, SAVED, every `A_` capture and ABORT:
```
S1F_DIR = r"<Q>"; S1F_SOURCE = "<Tails N>"; S1F_TARGET = "milestailsprower1"; S1F_PEER = "foxmccouldwm1"
```

**Setup line B.** Use it for every `B_` capture:
```
S1F_DIR = r"<Q>"; S1F_SOURCE = "milestailsprower1"; S1F_TARGET = "<Tails N>"; S1F_PEER = "foxmccouldwm1"
```

**Capture line.** Only the step name changes, and each step is captured once:
```
S1F_STEP = "PREP"; execfile(r"<REPO>\real_sfm_qualification\f01_rc4_cross_rig\observer\F01_RC4X_Capture.py")
```

Each capture prints three lines. The first two come from the reused captures: "Fox S" and "Fox D" there mean the
setup line's source and target. The last line is `RC4X <step>: controls source … | target … | peer … | offsets
written`. If a line shows errors other than `none`, STOP.

**Fault line** (ABORT only):
```
import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"
```

## Native sequence (Owner; one SFM process)

| # | Action | Expected | Capture |
|---|---|---|---|
| 1 | Start SFM and choose **File > Open** `<Q>\sessions\RC4X_SESSION.dmx`. | Motion Editor, shot15, playhead **0.2083 s**. If not, STOP. | |
| 2 | In the Animation Set Editor, choose **Create Animation Set for New Model** `models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl` once. Note its name: this is **Tails N**. Right-click it and choose **Rig > rig_biped_simple**. | Tails N has a `rig_chest` handle. | |
| 3 | Pose **Tails N** at 0.2083 s with rig handles: **turn `rig_chest`** (never move it), bend `rig_spine_1`, turn `rig_head`, raise one arm and bend the other (`rig_hand_L`, `rig_hand_R`), lift `rig_foot_R`, curl a few fingers. Then move its `rig_root` a few hundred units away from the original Tails and turn it. Do not pose the seven JIGGLE leaves (`ear3_L/R`, `HairSpike_B3/M3/T3`, `Tail6_L/R`) or `ear2_L/R`. **Finish all posing now.** | | |
| 4 | Open **Character Preset Manager**, choose **Refresh Models** and select **Tails N**. Submit setup line A, then capture. | Three lines, errors none. | **PREP** |
| 5 | With Tails N selected, choose **Poses: Save New**. | The status reads "Checking the character before saving." at once, then the dialog opens. | |
| 6 | Keep **Full body**, name it `RC4 Chest`, **Save**. | `Pose saved: RC4 Chest.` | |
| 7 | Select **milestailsprower1** (the original Tails). **Poses: Save New**, **Full body**, name it `RC4 Sit`, **Save**. | `Pose saved: RC4 Sit.` | |
| 8 | Open **Pose Info** for `RC4 Sit`, note the **Rig** row, and close it. Do the same for `RC4 Chest` (select Tails N first). Submit setup line A, then capture. | Rig: `rig_biped` for both (information only). | **SAVED** |
| 9 | **Direction A.** Select **milestailsprower1**, select `RC4 Chest`. Capture. | Apply Pose enabled. | **A_BASE** |
| 10 | **Apply Pose.** | `Pose applied: RC4 Chest. Adapted to this character's rig.` | **A_APPLY** |
| 11 | **Inspect** (no capture): the original Tails takes Tails N's body posture (spine and chest, neck, head, arms, hands, fingers, legs, feet); it stays where it was, facing as it was, with correct proportions; nothing is badly deformed (simulated ear, hair and tail tips may differ a little); Tails N and the Fox did not change. Note what you see. | | |
| 12 | **Navigate.** In the timeline, press **Left arrow** once, then **Right arrow** once. | The playhead reads 0.2083 s; the pose holds. | **A_NAV** |
| 13 | **Undo.** If the **Edit** menu reads **Undo Modify Time Selection**, record it and choose it once (it changes no character). Then the menu must read **Undo Apply Pose RC4 Chest**: choose it once. | The original Tails is as at A_BASE. | **A_UNDO** |
| 14 | **Edit > Redo Apply Pose RC4 Chest** once. | Posed again. | **A_REDO** |
| 15 | **Apply Pose** `RC4 Chest` again. | Nothing changes and the Edit menu is unchanged (a no-op). | **A_NOOP** |
| 16 | **Edit > Undo Apply Pose RC4 Chest** once. | The original Tails is as authored. | **A_FINAL** |
| 17 | **Direction B.** Submit setup line B. Select **Tails N**, select `RC4 Sit`. Capture. | Apply Pose enabled. | **B_BASE** |
| 18 | **Apply Pose.** | `Pose applied: RC4 Sit. Adapted to this character's rig.` | **B_APPLY** |
| 19 | **Inspect** as at step 11: Tails N takes the original Tails' sitting posture where it stands, facing as it was; the original Tails and the Fox did not change. | | |
| 20 | **Navigate** as at step 12. | | **B_NAV** |
| 21 | **Undo** as at step 13, with **Undo Apply Pose RC4 Sit**. | Tails N is as at B_BASE. | **B_UNDO** |
| 22 | **Edit > Redo Apply Pose RC4 Sit** once. | | **B_REDO** |
| 23 | **Apply Pose** `RC4 Sit` again. | A no-op. | **B_NOOP** |
| 24 | **Controlled Abort.** Submit setup line A. Select **milestailsprower1**, select `RC4 Chest`. Submit the **fault line**, then **Apply Pose**. | Either no dialog, with the status `The pose couldn't be applied. Nothing was changed.`; or a dialog **Pose not applied** saying your character was restored but SFM cleared your Redo history (press OK). The original Tails is unchanged. | **ABORT** |
| 25 | Submit setup line B. Select **Tails N**. **Edit > Undo Apply Pose RC4 Sit** once (if the menu names something else, choose nothing, record it and STOP). | Tails N is back to its own pose. | **B_FINAL** |
| 26 | Exit SFM **without saving**. Report each message, what you saw at steps 11 and 19, any Edit menu entry other than the ones listed, and anything unexpected. | | |

## STOP conditions

Exit SFM **without saving** and report. Claude still runs `library Q`, `collect-logs`, `restore`, `check` and
`analyze`. Stop when:
- a capture prints errors other than `none`;
- Full body is refused for either Save, or Apply Pose is disabled at step 9 or 17;
- an Apply is refused (note the exact message), writes to a character other than the selected one, moves it or
  damages it;
- the Edit menu does not name the Apply as listed, or Undo or Redo does not restore;
- a recovery message appears, other than the expected Abort message at step 24;
- SFM crashes, shows a recovery prompt or hangs for more than a minute.

A small difference in a simulated tip, or an adjustment an artist would routinely make, is not a STOP.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q` | the two Tails poses, and `pose_sources.json`, `pose_rigs.json` (and CPM's `character.json`, if written) |
| R2 | `collect-logs` | the CPM log |
| R3 | `restore`, then `check` | library cleanup exact, `RESTORED`; `"installation": "published"` |
| R4 | `analyze` | `RC4X_VERDICT.md` |

**Verdict** (`tools/rc4x_analyze.py`; the gates are described in its docstring):
- **AUTOMATED PASS:** EVIDENCE, PREP, SAVE, ADAPT, A_APPLY, A_POSTURE, A_HISTORY, B_APPLY, B_POSTURE, B_HISTORY, ABORT
  and PEER all pass. Acceptance also needs the Owner's visual assessment (steps 11 and 19).
- **FAIL:** the evidence is complete and a functional gate failed.
- **INCOMPLETE:** evidence, preparation or restoration failed.

**Recorded:**
- the maximum independent skeletal errors per direction, overall, per bone class and for `bip_spine_3`;
- the actual destination offsets against each record (largest angle and distance), and the number of neighbouring
  keys kept;
- any navigation entry, and whether the Abort found a Redo entry.

**Tolerances** (as in the Fox and Stage 2 qualifications):
- **Posture,** independent of CPM: the destination's evaluated non-leaf bones, relative to its own `rig_root`, against
  the source's at SAVED, within 0.05 units and 0.5°.
- **Placement, facing, direct bone offsets and peers:** unchanged within 0.001 units and 0.01°.
- **Authored state:** compared exactly.
- **CPM's P7:** its own unchanged limits (0.001 units, 0.01°), reported from the log.
