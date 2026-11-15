# F-01 UA-1: native UI acceptance of the UI corrections after K2 (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** "F-01 — Native UI Acceptance Proposal" (2026-11-14), on the committed UI corrections
(`F01_K2_UI_CORRECTIONS.md`, commit `d3d23d1`).

**What it establishes:** that the approved interface appears natively: the Save Pose Full body summary; Pose Info's
field order, Model path, Source shot, Source project and Saved Values; the Update Pose confirmation and, after one
disposable Update in another session, the updated source; the Body Preset and Expression confirmations; the Trash
dialogs with a visible, selectable and copyable recovery folder; and older records showing "Not recorded" and
staying usable. The automated captures check the exact dialog content without showing it; the Owner's visual
inspection (V1–V5) of the same dialogs opened through the CPM buttons establishes their on-screen readability,
arrangement, default button and copyable recovery folder. **Reused, not repeated:** K2's accepted Save, Apply, Undo, Redo and Update engine evidence. Nothing
is applied in UA-1.

| Item | Value |
|---|---|
| Candidate CPM | `8eccf1723fef395fcf0678ea25c0dbdf145ba77d1558ca318887aa6cfe057194` (`d3d23d1`) |
| UA-1 qualification build | `ea670f51d13b295c59f51047fc029da512d523528482889f0c0d9835700afa6f` (one line, 42220: `PROD_POSE_REGISTRY_MODE = u"qualification"`, needed for Krystal's version 2 Full body) |
| Registries | `cpm_pose_profiles_v1.json` `f445d5ef…`, `cpm_body_profiles_v1.json` `22dcd159…` |
| Sessions | `UA_SOURCE.dmx`: verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s); `UA_DESTINATION.dmx`: verified copy of S3's prepared destination `61df8bcd…` (shot13, 0.3750 s) |
| Seeded older records | K2's updated version 2 `K2 Pose` `bf8fc5bc…` (no source project recorded); version 1 `NQ1 Pose A` `4916a724…` |
| Capture script | `observer/F01_UA_Capture.py` `d5d07b90…` (read-only; drives each handler to its dialog and answers Cancel) |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_ui_acceptance\tools\ua_tool.py <Q>\ua.json <command>` |
| Restored afterwards | the published CPM `ccbed9d7…`; both registries removed; the preset library exactly as backed up (files and folders); every protected inventory equal to its baseline |

**Never:** save a session; click Apply Pose, Move to Trash, Rename, Add Favorite or the Updater; confirm Update
Preset; touch any preset other than `UA Body` and `UA Expr`; use another character. The only writes in SFM are Save
New (`UA Pose`, `UA Body`, `UA Expr`) and one Update Pose of `UA Pose`, all in the disposable library state that
restore removes.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `ua.template.json` to `<Q>\ua.json`; fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: … ea670f51… differs from the candidate in line 42220 only` |
| P2 | `pre` | `PRE PASS (K2)` (published installation, backups, four inventories, both session copies) then `PRE PASS (UA-1): preset library backed up` |
| P3 | `install`, then `check` | `INSTALLED`; `"installation": "qualification"` |
| P4 | `seed` | `SEEDED: K2 Pose--ac9d4962a2ae.json, NQ1 Pose A--5273df2209ca.json` |
| P5 | Create `<Q>\owner_review\` and copy `owner_visual_review.template.md` into it as `OWNER_VISUAL_REVIEW.md` | the Owner's record of V1–V5 and the screenshots |

## Native sequence (Owner)

Once per SFM process, after opening CPM, submit:
```
UA_DIR = r"<Q>"; UA_REPO = r"<REPO>"
```
Capture a step (each step once; it prints `UA STEP <step>: <n> dialog(s) captured`; the dialogs it captures are not
shown on screen and end as Cancel):
```
UA_STEP = "A1"; execfile(UA_REPO + r"\real_sfm_qualification\f01_ui_acceptance\observer\F01_UA_Capture.py")
```

### Process A (UA_SOURCE.dmx)

1. Start SFM. **File > Open** `<Q>\sessions\UA_SOURCE.dmx`. **Motion Editor**, **shot15**, playhead 0.2083 s
   (frame 5). Open **Character Preset Manager**, **Refresh Models**, select `Krystal`, **Poses**. Submit the setup
   line.
2. **Older version 2 record.** Select `K2 Pose`, open **Pose Info**. Expected order: Name, Type (`Full body`), Model,
   Model path, Source shot (`shot13`), Source project (`Not recorded`), Saved, Updated, Includes if shown, Not included
   (`Facial expressions, rootTransform`); the Saved Values tree lists the saved controls. Close it. Capture **A1**.
3. **Older version 1 record.** Select `NQ1 Pose A`, open **Pose Info** (Type `Left arm`, Source project
   `Not recorded`). Close it. Capture **A2**.
4. **Save Pose.** Capture **A3** first (it opens and cancels the Save dialog invisibly). Then click **Save New**.
   Expected: **Full body** selected, the summary `Facial expressions and the rootTransform are not saved.`, Save
   enabled. Name it `UA Pose`, **Save**. Expected: `Pose saved: UA Pose.`
5. **New pose.** Select `UA Pose`, open **Pose Info**. Expected: Source shot `shot15`, Source project the full path
   of `UA_SOURCE.dmx` (SFM reports it in lower case), no Updated row. Close it.

Steps 6–9 are the **Owner visual inspection** (V1–V4 below): you open the real dialogs through the CPM buttons, inspect
them on screen, take a screenshot of each, and close them with the mouse on **Cancel**. Never press Enter or Space in
these dialogs (judge the default button by its highlight), and never click Update Pose, Update Preset or Move to
Trash here.

6. **V1: Update Pose confirmation.** Click **Update Pose**. Inspect (checklist V1), screenshot `V1-update-pose.png`,
   click **Cancel**.
7. **V2: Delete Pose (Trash) dialog.** Click **Delete Pose**. Inspect (checklist V2), screenshot
   `V2-delete-pose.png`. Select the whole folder path with the mouse and press **Ctrl+C** (checklist V5). Click
   **Cancel**. Capture **A7** (the clipboard), then capture **A4**.
8. **V3: Body Presets.** Tab **Body Presets**, **Save New**, name `UA Body`, save. Select `UA Body`. Click **Update
   Preset**, inspect (checklist V3), screenshot `V3-update-body.png`, **Cancel**. Click **Delete Preset**, inspect
   (checklist V2 for this preset), screenshot `V3-delete-body.png`, **Cancel**. Capture **A5** (with `UA Body` still
   selected).
9. **V4: Expressions.** Tab **Expressions**, **Save New**, name `UA Expr`, save. Select `UA Expr`. **Update Preset**,
   inspect (checklist V4), screenshot `V4-update-expression.png`, **Cancel**; **Delete Preset**, inspect (checklist
   V2 for this expression), screenshot `V4-delete-expression.png`, **Cancel**. Capture **A6**.
10. Exit SFM **without saving**.

Claude: `library A`.

### Process B (UA_DESTINATION.dmx)

11. Start SFM. **File > Open** `<Q>\sessions\UA_DESTINATION.dmx`. **Motion Editor**, **shot13**, playhead 0.3750 s
    (frame 9). Open CPM, Refresh Models, `Krystal`, **Poses**. Submit the setup line.
12. Select `UA Pose`, click **Update Pose**, check the confirmation as in step 6, click **Update Pose**. Expected:
    `Pose updated: UA Pose.`
13. Open **Pose Info**. Expected: Source shot `shot13`, Source project the full path of `UA_DESTINATION.dmx`, an
    Updated row. Close it. Capture **B1** (with `UA Pose` selected).
14. Exit SFM **without saving**. Fill in `<Q>\owner_review\OWNER_VISUAL_REVIEW.md` (a copy of
    `owner_visual_review.template.md`) and put the screenshots beside it; report anything else you saw (Save dialog,
    Pose Info layout, messages).

## Owner visual inspection checklist (V1–V5)

Recorded by the Owner in `<Q>\owner_review\` (observations and screenshots), separately from the comparator. Each
item is **Accepted**, **Not accepted** (with what is wrong) or **Not seen**.

| Item | Dialog | Check on screen |
|---|---|---|
| V1 | Update Pose (step 6) | Title `Character Preset Manager`; one readable question `Replace the saved pose "UA Pose" with the character's current pose?`; no second explanation; buttons **Update Pose** and **Cancel**, in a sensible order; **Cancel** highlighted as the default |
| V2 | Delete Pose, Delete Preset (Body and Expression) (steps 7–9) | Title `Character Preset Manager`; `Move the saved pose / body preset / expression "<name>" to Trash?` with the right name, readable; `You can recover it from:` with the full Trash folder visible (not cut off); **Move to Trash** and **Cancel**, **Cancel** highlighted as the default |
| V3 | Update Preset, Body (step 8) | Title; `Replace the saved body preset "UA Body" with the character's current body settings?`; **Update Preset** and **Cancel**; Cancel the default |
| V4 | Update Preset, Expression (step 9) | Title; `Replace the saved expression "UA Expr" with the character's current expression?`; **Update Preset** and **Cancel**; Cancel the default |
| V5 | Trash folder (step 7) | The path can be selected with the mouse and copied with Ctrl+C (the A7 capture records what was copied) |

Not part of V1–V5 (already verified elsewhere, not repeated): the functional Save, Update, Apply, Undo and Redo
behaviour (K2), and the Save dialog, Pose Info, Source shot and Source project (the two-process steps above and the
automated captures).

## STOP conditions

Exit SFM **without saving** and report; Claude still runs `library B`, `collect-logs`, `restore`, `check`:
- a capture prints `ERRORS` or refuses;
- the Save dialog shows a refusal, Selected parts only, or another summary; Save fails;
- Update Pose is refused or reports anything other than `Pose updated: UA Pose.`;
- anything is moved to Trash, applied, renamed or saved other than the four writes above;
- SFM crashes, shows an autosave recovery prompt, or hangs for more than a minute.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library B` | the run's library differences (Poses, `pose_sources.json`, `UA Body`, `UA Expr`, any changed file) |
| R2 | `collect-logs` | two CPM logs (Process A, Process B) |
| R3 | `restore`, then `check` | library cleanup with `files_equal_pre` and `folders_equal_pre` true, then `RESTORED`; `"installation": "published"` |
| R4 | `compare` | `UA_VERDICT.md` |

**PASS** (all `ua_compare` checks): the UA-1 qualification build in every capture; a restart between Save and
Update; the sessions as named; older records with their own Source shot, `Not recorded`, the approved order and
tree, Apply enabled; the real Save dialog with Full body and the approved summary; the new pose's Source shot
`shot15` and Source project equal to the session; the Update Pose, Update Preset and Trash dialogs exactly as
approved (title, question, buttons, Cancel default, recovery folder visible and selectable); the copied folder equal
to the library Trash; after the Update, Source shot `shot13` and Source project equal to the updating session; the
logs showing only the four writes, every captured dialog cancelled, the source recorded twice, no Apply and no
recovery, uncertainty or unrecorded source; the sidecar holding only `UA Pose` with the updating session; the older
records unchanged; the pose record carrying no project path; nothing moved to Trash; the library and every inventory
restored; the sessions never saved.

**UA-1 acceptance needs both, independently:** the automated `UA_VERDICT` **PASS** (unchanged; the Owner's review
never substitutes for a failed check), **and** the Owner's visual inspection V1–V5 all **Accepted**
(`owner_review\OWNER_VISUAL_REVIEW.md` with its screenshots). The two are reported side by side; neither is
rewritten from the other. A visual item Not accepted is a UI finding for a later, separately authorized correction;
it does not change the automated verdict. A STOPPED run is restored and reported STOPPED.
