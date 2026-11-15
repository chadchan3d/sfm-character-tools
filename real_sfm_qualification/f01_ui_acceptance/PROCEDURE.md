# F-01 UA-1: native UI acceptance of the UI corrections after K2 (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** "F-01 — Native UI Acceptance Proposal" (2026-11-14), on the committed UI corrections
(`F01_K2_UI_CORRECTIONS.md`, commit `d3d23d1`).

**What it establishes:** that the approved interface appears natively: the Save Pose Full body summary; Pose Info's
field order, Model path, Source shot, Source project and Saved Values; the Update Pose confirmation and, after one
disposable Update in another session, the updated source; the Body Preset and Expression confirmations; the Trash
dialogs with a visible, selectable and copyable recovery folder; and older records showing "Not recorded" and
staying usable. **Reused, not repeated:** K2's accepted Save, Apply, Undo, Redo and Update engine evidence. Nothing
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
6. **Update Pose confirmation.** Click **Update Pose**. Expected: window title `Character Preset Manager`, the one
   question `Replace the saved pose "UA Pose" with the character's current pose?`, buttons **Update Pose** and
   **Cancel**, Cancel the default. Click **Cancel**.
7. **Delete Pose (Trash) dialog.** Click **Delete Pose**. Expected: title `Character Preset Manager`, `Move the saved
   pose "UA Pose" to Trash?`, `You can recover it from:` and the library's Trash folder, buttons **Move to Trash** and
   **Cancel** (default). Select the whole folder path with the mouse and press **Ctrl+C**. Click **Cancel**. Capture
   **A7** (the clipboard), then capture **A4**.
8. **Body Presets.** Tab **Body Presets**, **Save New**, name `UA Body`, save. Select `UA Body`. Click **Update
   Preset**: expected title `Character Preset Manager`, `Replace the saved body preset "UA Body" with the character's
   current body settings?`, **Update Preset** and **Cancel** (default); click **Cancel**. Click **Delete Preset**:
   `Move the saved body preset "UA Body" to Trash?`, the recovery folder, **Move to Trash** and **Cancel**; click
   **Cancel**. Capture **A5** (with `UA Body` still selected).
9. **Expressions.** Tab **Expressions**, **Save New**, name `UA Expr`, save. Select `UA Expr`. **Update Preset**
   (`Replace the saved expression "UA Expr" with the character's current expression?`) → **Cancel**; **Delete
   Preset** (`Move the saved expression "UA Expr" to Trash?`) → **Cancel**. Capture **A6**.
10. Exit SFM **without saving**.

Claude: `library A`.

### Process B (UA_DESTINATION.dmx)

11. Start SFM. **File > Open** `<Q>\sessions\UA_DESTINATION.dmx`. **Motion Editor**, **shot13**, playhead 0.3750 s
    (frame 9). Open CPM, Refresh Models, `Krystal`, **Poses**. Submit the setup line.
12. Select `UA Pose`, click **Update Pose**, check the confirmation as in step 6, click **Update Pose**. Expected:
    `Pose updated: UA Pose.`
13. Open **Pose Info**. Expected: Source shot `shot13`, Source project the full path of `UA_DESTINATION.dmx`, an
    Updated row. Close it. Capture **B1** (with `UA Pose` selected).
14. Exit SFM **without saving**. Report what you saw at each step (wording, order, layout, anything unexpected), the
    messages, and screenshots if taken.

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

**Not a PASS by itself:** an Owner observation without the matching machine check. The Owner's visual review
(layout, readability, anything unexpected) is reported beside the verdict. A STOPPED run is restored and reported
STOPPED.
