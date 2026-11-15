# F-01 UA-1S: supplemental native check of the Body Preset and Expression confirmations (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** "F-01 — UA-1 Closure Assessment and Narrow Supplemental Check" (designer, 2026-11-15).

**Why:** in UA-1 run 1 (`F01_UA1_RESULTS.md`) the Update Preset and Delete Preset confirmations never appeared in SFM
(no preset was selected for captures A5/A6). This check closes only that gap: one SFM process, one disposable Body
preset and one disposable Expression, each item's Update and Delete confirmation opened, inspected and cancelled.
**Not repeated:** anything UA-1 run 1 established (Save dialog, Pose Info, Source shot and project, Update Pose, Delete
Pose, older records) or K2 established (Save, Apply, Undo, Redo, Update).

| Item | Value |
|---|---|
| Candidate CPM | `615acf0c23ffcf5c278785bb47de6aaf6a7b9ae26779b9313979ac928240c432` (`fda1fb3`: the UI corrections plus the two pose types) |
| Qualification build | `849d0ed44101965de62165f01fcbb22b3caae9797e867169e71d4247b49cd4a2` (one line: `PROD_POSE_REGISTRY_MODE = u"qualification"`; the presets do not need it, the kit's verified install and restore do) |
| Session | `UA_SOURCE.dmx`: verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s); `pre` also copies `UA_DESTINATION.dmx`, which is not opened |
| Capture script | `observer/F01_UA_Capture.py` `d5d07b90…`, unchanged; its existing steps **A5** (Body preset), **A6** (Expression) and **A7** (clipboard) are used, in this check's own run folder |
| Comparator | `tools/ua_compare.py` in supplement mode (corrected: a missing or wrong-type capture is an explicit failure); writes `UA_SUPPLEMENT_VERDICT` |
| Configuration | `ua_supplement.template.json` (`"mode": "supplement"`) |
| Restored afterwards | the published CPM `ccbed9d7…`; both registries removed; the preset library exactly as backed up (files and folders); every protected inventory equal to its baseline |

**Never:** save the session; open Poses for anything; click Update Preset or Move to Trash in a confirmation; press
Enter or Space in a confirmation (judge the default by its highlight); touch any preset other than `UA Body` and
`UA Expr`; use another character.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `ua_supplement.template.json` to `<Q>\ua_supplement.json` (a new run folder); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: … 849d0ed4… differs from the candidate in line … only` |
| P2 | `pre` | `PRE PASS (K2)` then `PRE PASS (UA-1): preset library backed up` |
| P3 | `install`, then `check` | `"installation": "qualification"` |
| P4 | Create `<Q>\owner_review\` and copy `owner_visual_review_supplement.template.md` into it as `OWNER_VISUAL_REVIEW.md` | |

(`seed` and `replay` refuse in supplement mode.)

## Native sequence (Owner, one SFM process)

Setup line, once after opening CPM:
```
UA_DIR = r"<Q>"; UA_REPO = r"<REPO>"
```
Capture line (only the step name changes):
```
UA_STEP = "A5"; execfile(UA_REPO + r"\real_sfm_qualification\f01_ui_acceptance\observer\F01_UA_Capture.py")
```

1. Start SFM. **File > Open** `<Q>\sessions\UA_SOURCE.dmx`. **Motion Editor**, **shot15**, playhead 0.2083 s. Open
   **Character Preset Manager**, **Refresh Models**, select `Krystal`. Submit the setup line.
2. **Body Preset.** Tab **Body Presets** (not Poses). Click that tab's **Save New**, name `UA Body`, save. Click
   `UA Body` in the **Body Presets** list so it is selected.
3. Capture **A5** (it opens and cancels the Update Preset and Delete Preset dialogs invisibly; the line must report
   2 dialogs and no ERRORS).
4. **V3** Click **Update Preset**. Inspect, screenshot `V3-update-body.png`, click **Cancel**.
5. **V2/V5** Click **Delete Preset**. Inspect, screenshot `V2-delete-body.png`. Select the whole recovery folder path
   with the mouse, press **Ctrl+C**, click **Cancel**. Capture **A7** immediately (the clipboard).
6. **Expression.** Tab **Expressions**. Click that tab's **Save New**, name `UA Expr`, save. Click `UA Expr` in the
   **Expressions** list so it is selected. Capture **A6** (2 dialogs, no ERRORS).
7. **V4** Click **Update Preset**. Inspect, screenshot `V4-update-expression.png`, **Cancel**. **V2** Click **Delete
   Preset**. Inspect, screenshot `V2-delete-expression.png`, **Cancel**.
8. Exit SFM **without saving**. Fill in `<Q>\owner_review\OWNER_VISUAL_REVIEW.md` and put the screenshots beside it.

### Owner visual checklist (recorded separately from the comparator)

| Item | Dialog | Check on screen |
|---|---|---|
| V3 | Update Preset, Body | Title `Character Preset Manager`; `Replace the saved body preset "UA Body" with the character's current body settings?`; **Update Preset** and **Cancel**; Cancel highlighted as the default |
| V4 | Update Preset, Expression | Title; `Replace the saved expression "UA Expr" with the character's current expression?`; **Update Preset** and **Cancel**; Cancel the default |
| V2 | Delete Preset, Body and Expression | Title; `Move the saved body preset "UA Body" to Trash?` / `Move the saved expression "UA Expr" to Trash?`; `You can recover it from:` with the full Trash folder visible; **Move to Trash** and **Cancel**; Cancel the default |
| V5 | Trash folder | selectable with the mouse and copied with Ctrl+C (A7 records what was copied) |

## STOP conditions

Exit SFM **without saving** and report; Claude still runs `collect-logs`, `restore`, `check`:
- a capture prints `ERRORS`, refuses, or reports a number of dialogs other than 2 (A5, A6);
- a preset Save fails, or anything is applied, updated, renamed or moved to Trash;
- SFM crashes, shows an autosave recovery prompt, or hangs for more than a minute.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library S` | the run's library differences (`UA Body`, `UA Expr`, any changed file) |
| R2 | `collect-logs` | one CPM log |
| R3 | `restore`, then `check` | library cleanup `files_equal_pre` and `folders_equal_pre` true, then `RESTORED`; `"installation": "published"` |
| R4 | `compare` | `UA_SUPPLEMENT_VERDICT.md` |

**Supplement PASS** (all checks): the qualification build in every capture; one SFM process on the source session;
`UA Body` and `UA Expr` selected; both Update Preset confirmations and both Trash dialogs exactly as approved (title,
question, buttons, Cancel default, the recovery folder visible and selectable); the copied folder equal to the
library Trash; the log showing only the two preset saves written, every preset dialog cancelled, no pose operation
other than Pose Info, no recovery; only preset files added, nothing removed or moved to Trash; the library and every
inventory restored; the session never saved.

**Acceptance of the supplement needs both, independently:** the automated `UA_SUPPLEMENT_VERDICT` PASS and the
Owner's V2–V5 Accepted. It is reported separately from UA-1 run 1, whose replay verdict stays FAIL.
