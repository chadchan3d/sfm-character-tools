# F-01 Stage 1: targeted native Abort recovery check

**Authority:** the Designer's "F-01 — Targeted Native Abort Qualification" (ACCEPT offline correction; checkpoint
`25ba936`). Record: `cpm/qualification/F01_STAGE1_ABORT_HISTORY.md`.

**Builds:**
- candidate CPM `7259e80a5d462eba1aeaa25cf89e9f57cf1081caaeac3002de8db6fbe488ab55`;
- qualification build `39f2e35542180952d37f0d75b20d4c5cc89f24db16031b905655dc2310462421`.

## What this checks, and what it does not

One SFM process, with no Save, no restart and no visual qualification. It confirms natively that the corrected CPM:
- reports verified restoration when SFM clears a pending Redo entry ("Pose not applied");
- still reports "Nothing was changed." when there was no Redo;
- does not pause the pose tools after either;
- leaves Fox S and the original Fox untouched.

Undo availability (`IsUndoEnabled`) is read directly by the capture's sidecar. It is not inferred.

It is **not** a repeat of the Fox Save, Apply and visual qualification.

**Run 3 stays as it was:**
- Its folder `f01-stage1-fox-r3` is only read: its saved session and its saved `S1 Fox` record and
  `pose_sources.json` are copied after verification against their pins.
- Its evidence and its INCOMPLETE verdict (`561f1b09…`) are never changed.

## Kit

| File | Role |
|---|---|
| `observer/F01_S1R_Capture.py` | Runs the Fox capture `f01_stage1_fox/observer/F01_S1F_Capture.py` unchanged (pinned `765eefc2…`) with this check's six steps. It then writes the Undo sidecar `S1F-<step>.undo.json`: `IsUndoEnabled`, `CanUndo`, `CanRedo` and both descriptions, read directly. |
| `tools/s1r_tool.py` | `build`, `pre`, `install`, `check`, `seed`, `library`, `collect-logs`, `restore`, `analyze`. It reuses the Fox, K2, S3 and UA-1 tools. |
| `tools/s1r_analyze.py` | The verdict. It reuses the Fox analyzer's helpers. |
| `s1r.template.json` | Paths and pins. Copy it to `<Q>/s1r.json` and fill in the paths only. |

Tool command (SFM closed): `python -I <REPO>\real_sfm_qualification\f01_stage1_recovery\tools\s1r_tool.py <Q>\s1r.json <command>`.

**Preparation, after the Owner's authorization:**
1. `build`: checks the pins and derives the qualification build, which differs from the candidate in one line.
2. `pre`: copies run 3's saved session, verified, as `S1R_SESSION.dmx`, and records backups, inventories and the
   library.
3. `install`, then `check`: installs the qualification build and both registries.
4. `seed`: copies run 3's `S1 Fox` record and `pose_sources.json` into the library, verified.

## The Owner's steps (one SFM process)

**Setup line** (Script Editor, at step 2):
```
S1F_DIR = r"<Q>"; S1F_SOURCE = "foxmccouldwm2"; S1F_TARGET = "foxmccouldwm3"; S1F_PEER = "foxmccouldwm1"
```
**Capture line** (change only the step name; take each step once):
```
S1F_STEP = "BASE"; execfile(r"<REPO>\real_sfm_qualification\f01_stage1_recovery\observer\F01_S1R_Capture.py")
```
Each capture prints an `S1F <step>: …` line, then `S1R <step>: Undo enabled True | … | sidecar written`.

**Fault line:**
```
import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"
```

**Between steps:** do not click in the viewport, the timeline or the animation set editor, and do not move the
playhead. Only the listed menu items, CPM buttons and Script Editor lines are used.

| Step | Action | Expected | Capture |
|---|---|---|---|
| 1 | Start SFM. **File > Open** `<Q>\sessions\S1R_SESSION.dmx`. | Motion Editor, shot15, playhead 0.2083 s. Fox S, Fox D and the original Fox present. | |
| 2 | Open CPM, **Refresh Models**, select **Fox D** (`foxmccouldwm3`), then select `S1 Fox`. Submit the setup line. | Apply Pose enabled. | **BASE** |
| 3 | **Apply Pose**. Wait until the status leaves "Checking the applied pose…". | `Pose applied: S1 Fox.` | **APPLY** |
| 4 | **Edit > Undo Apply Pose S1 Fox**. | Fox D returns to its pose at step 2. The Edit menu offers **Redo Apply Pose S1 Fox**. | **UNDO** |
| 5 | Submit the fault line, then **Apply Pose**. | A dialog titled **Pose not applied**: "Your character was restored, but SFM cleared your Redo history." Press OK. The status shows the same text. Fox D is as at step 4. The Edit menu offers no Redo. | **ABORT1** |
| 6 | Submit the fault line again, then **Apply Pose**. | No dialog. The status reads `The pose couldn't be applied. Nothing was changed.` Fox D is unchanged. | **ABORT2** |
| 7 | **Apply Pose**. Wait for the final status. | `Pose applied: S1 Fox.` The pose tools are not paused. | **APPLY2** |
| 8 | Exit SFM **without saving**. | | |

**Stop** if any of the following happens. Exit without saving and capture nothing more:
- a dialog titled **Pose operation stopped**, or any message that pose tools are paused;
- a capture prints errors, or its `S1R` line does not report `Undo enabled True`;
- Apply Pose is disabled at step 2;
- step 4 offers no Redo;
- Fox S or the original Fox changes;
- SFM crashes or hangs.

Then report what you saw.

**After SFM closes:** `library Q`, `collect-logs`, `restore`, `check`, `analyze`.

## The analyzer's gates (`S1R_VERDICT`)

| Gate | Requires |
|---|---|
| EVIDENCE | The identities. Every capture: the qualification build, no error, and a complete Undo sidecar that agrees with the capture. One SFM process on `S1R_SESSION.dmx`, at one shot and playhead, in the Motion Editor. Both session copies never saved. The library changed only by the two seeded files, unchanged. Library and installation restored. The log collected. |
| SETUP | The three Foxes by name and model. `S1 Fox` (the seeded record) selected. Fox D admitted by the structural discovery. |
| APPLY | Fox D changed. One owned `Apply Pose S1 Fox` entry. UNDO: Fox D exactly as at BASE, the top entry as at BASE, Redo `Redo Apply Pose S1 Fox` pending, Undo enabled (sidecar). |
| REDO_ABORT | The injected failure after as many writes as the committed Apply made. CPM `BODY-abort-verified {"problems": [], "redo_cleared": true}`. All three sets exactly as at UNDO. The Undo state exactly UNDO's, except `can_redo` false and `redo_desc` "". Undo enabled observed directly. The fault slot consumed. |
| EXACT_ABORT | The second injected failure. `BODY-abort-verified {"problems": [], "redo_cleared": false}`. All three sets and the complete Undo state exactly as at ABORT1. The fault slot consumed. |
| OPERATIONAL | No lockout, unverified, failed-Abort or uncertain result in the log. Events in order: P7-verified, failure, verified Abort, failure, verified Abort, P7-verified. Two `recovery-verified` outcomes. APPLY2 equals APPLY on Fox D, with one owned entry. |
| PEER | Fox S and the original Fox unchanged at every capture. |

**Verdict:**
- **AUTOMATED PASS:** every gate passed. The Owner still confirms the two messages at steps 5 and 6.
- **FAIL:** a functional gate failed.
- **INCOMPLETE:** evidence, setup or restoration is missing or failed.

**Genuine unverified recovery** is not injected natively. It is covered offline, in Stage 1 section O, Selected parts
L and pose D8R, and run 3 exercised the native lockout path.
