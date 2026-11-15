# F-01 UA-1: native UI acceptance of the UI corrections after K2 — results

**Dates:** run 2026-11-15 (preparation 2026-11-14). **Authority:** "F-01 UA-1 — Native UI Acceptance Trial, OWNER
AUTHORIZATION: GO"; closeout under "F-01 UA-1 — Owner Acceptance and Closeout".
**Kit:** `real_sfm_qualification/f01_ui_acceptance/` (`ab214a8`, `9e1c06a`, `8ef734e`). **Candidate:** CPM
`8eccf172…` (`d3d23d1`); qualification build `ea670f51…` (line 42220 only). **Run folder (raw evidence, not
committed):** `E:\SFM_U0B_Scratch\f01-ui-acceptance-r1`.

## Disposition

| Result | Status |
|---|---|
| **Owner visual acceptance** | **Accepted.** The Owner reports: all intended UI elements were personally inspected and approved; the native UI looked correct and worked as intended; differences in the order of inspection are accepted as operator deviations. (`owner_review\OWNER_VISUAL_REVIEW.md` was left blank and no screenshots were placed in the run folder; the acceptance is the Owner's statement, recorded here as given.) |
| **Formal automated verdict** | **None.** The unchanged comparator raised `KeyError: 'labels'` in `trash_problems` (the A5 Trash capture is an error message box, not a Trash dialog) before writing `UA_VERDICT`. This is a comparator robustness defect; the comparator was not changed during execution. |
| Diagnostic (not a verdict) | `evidence\UA_DIAGNOSTIC_NOT_A_VERDICT.json/.md`: the same checks with one in-memory guard (a non-dialog Trash capture is a failure, not an exception): **48/67 pass, 19 fail** — all 19 procedural (below). |
| **Restoration** | **Verified.** Library cleanup: `files_equal_pre` and `folders_equal_pre` true (the run's Poses folder removed; the pre-existing empty `_Qualification` folder kept); S3 restore `RESTORED`: published CPM `ccbed9d7…`, both registries removed, all four inventories equal their baselines. Sessions never saved (`259ea8a6…`, `61df8bcd…`). The 16 original evidence files are byte-identical before and after restoration and diagnosis. |

## Measured native results (from the preserved captures and CPM logs)

- **Older records (A1/A2, taken in swapped order).** `NQ1 Pose A` (v1): Type `Left arm`, Source shot `shot10`,
  Source project `Not recorded`, approved order, Saved Values tree, Apply enabled. `K2 Pose` (v2): Source shot
  `shot13`, `Not recorded`, Updated row, Not included `Facial expressions, rootTransform`, Apply enabled.
- **Save dialog (A3, real dialog cancelled).** Full body checked, Save enabled, the approved summary visible; the
  review line and "Leave these controls unchanged" present but hidden (as designed for the v2 route).
- **New pose (A4, taken with `UA Expr` selected).** Pose Info in the approved order, Source shot `shot15`, Source
  project the source session path (lower case), Not included approved. Update Pose confirmation and Delete Pose
  Trash dialog exactly as approved for the selected name: title, one question, Update Pose/Cancel or Move to
  Trash/Cancel, Cancel default, Trash folder visible and selectable (mouse and keyboard flags).
- **Update in a new SFM process (B1).** One Update Pose verified; Pose Info Source shot `shot13`, Source project the
  destination session, Updated row; the confirmation exact.
- **Sidecar.** `UA Pose` → the destination session (replaced on Update, as decided); the other two saved poses →
  the source session. Pose records carry no project path. Every save and the update logged
  `PROD_POSE_SOURCE-recorded`; no `SOURCE-unrecorded`, no Apply, no recovery or uncertainty.

## The 19 diagnostic failures: all procedural

| Failure | Cause (from the evidence) | Product behaviour shown |
|---|---|---|
| `older.A1_selected`, `older.A2_selected`, `older.v2_not_included_wording`, `older.v2_updated_record_shows_updated` | A1 and A2 captured with the two records swapped | both records correct in the other step |
| `new.selected`, `update.A4_confirmation`, `trash.pose_dialog`, `update.same_pose` | A4 taken with `UA Expr` selected | dialogs exact for the selected pose |
| `preset.*` (4), `trash.body_dialog`, `trash.expression_dialog` | `UA Body` and `UA Expr` were saved as poses on the Poses tab; no preset was selected for A5/A6, so the handlers stopped at "Select a preset first" (`failed-precommit`, nothing written) | none: see unresolved item 1 |
| `trash.recovery_folder_copies` | the clipboard held the capture command, not the copied path | the Trash folder label is natively selectable (A4) |
| `log.only_the_owners_saves_and_one_update_were_written`, `log.every_captured_dialog_ended_cancelled`, `log.source_recorded_on_save_and_update`, `library.source_sidecar_holds_only_the_new_pose_with_the_updating_session` | three Save Pose writes instead of one pose and two presets; the A5/A6 `failed-precommit` ends | each save recorded its source correctly |

**Product defects demonstrated:** none. The "Can't update preset / Preset could not be updated" messages appeared
only because the capture called the handlers with no preset selected; in the window those buttons are disabled
without a selection.

## Unresolved, and the minimum further verification

1. **Update Preset and Delete Preset confirmations were not shown natively.** The CPM log records no Update Preset or
   Delete Preset dialog (only the four `failed-precommit` capture calls). Their wording is verified offline on the
   real window (UA-1 capture test U3) and they use the same helpers (`tool_confirm_action`, `tool_confirm_trash`)
   whose native output was captured exactly for Update Pose and Delete Pose. Coder's assessment: low residual risk.
   If the Owner wants native evidence, the minimum is one short SFM session on a disposable copy: Save New one Body
   preset and one Expression, open each Update and Delete dialog, Cancel — with the comparator fix below. Not
   started; needs authorization.
2. **Comparator robustness.** `trash_problems` must treat a non-dialog capture as a failure (the one-line guard used
   by the diagnostic). Offline kit correction; needs authorization; the run's evidence can then be replayed into a
   separately named verdict without touching `UA_VERDICT`.
3. **Owner visual record.** The template was not filled in; the Owner's acceptance is recorded from the closeout
   message. Screenshots, if kept, can be added to `owner_review\` by the Owner.

## Designer disposition and kit correction (2026-11-15)

**Designer disposition:** the available UA-1 functional evidence and the Owner's visual approval are accepted with the
procedural limitations documented above; no formal automated PASS is claimed for run 1. The Owner also accepted
`fda1fb3` (two pose types).

**Comparator correction (offline, kit only):** `ua_compare.one_dialog` makes a missing capture, an error, zero or
several dialogs, a dialog of the other kind (an error message box where a Trash dialog was expected — the run 1
crash), or a capture without readable labels or buttons an explicit failed check; an unreadable or malformed capture
file fails `captured.<step>`. No acceptance predicate was relaxed. Tests: `test_ua.py` 15/15 on Python 3.10.6 (new:
the run 1 message-box case, a malformed capture file, every reader against eight kinds of missing or wrong captures,
replay safety, the supplement); `test_ua_capture.py` 12/12 on Python 2.7.5 (unchanged).

**Replay of run 1 (formal record of run 1 under the corrected comparator):** `ua_tool replay` wrote
`evidence\UA_VERDICT_REPLAY.json/.md` (`709065a4…`): **FAIL, 48/67**, exactly the 19 procedural failures of the
diagnostic. It names the eight capture files it read by SHA-256; all 28 earlier evidence files are byte-identical
before and after; no `UA_VERDICT` exists or was created for run 1.

## Supplement UA-1S (prepared offline, not run)

`real_sfm_qualification/f01_ui_acceptance/PROCEDURE_SUPPLEMENT.md`, `ua_supplement.template.json`
(`"mode": "supplement"`), `owner_visual_review_supplement.template.md`. One SFM process on a fresh copy of the R2
source session, candidate `615acf0c…` (`fda1fb3`), qualification build `849d0ed4…`: Save New one Body preset and one
Expression on their own tabs, capture A5/A6 (the unchanged capture script) and A7 (the copied folder), and the Owner
opens, inspects (V2–V5), screenshots and cancels each Update Preset and Delete Preset confirmation. Supplement
comparator checks: the exact native wording, title, buttons and Cancel default of all four confirmations; the
recovery folder visible, selectable and copied; only the two preset saves written; every preset dialog cancelled; no
pose operation; nothing removed or moved to Trash; restoration exact. Needs the Owner's separate authorization.

## Combined evidence against the original UI acceptance requirements

| Requirement (UA-1 proposal) | Native machine evidence | Owner visual | Remaining limitation |
|---|---|---|---|
| 1. Save Pose Full body summary | A3 (passes) | accepted | none |
| 2. Pose Info order, Model path, Source shot and project, Saved Values | A1/A2 (swapped), A4 (`UA Expr`), B1 — content correct | accepted | the formal checks failed on step identity only |
| 3. Update Pose confirmation and updated source | A4 (`UA Expr`), B1 — exact | accepted | none material |
| 4. Body Preset and Expression confirmations | **none** (not shown in run 1) | accepted per the Owner's statement; no record | **open until UA-1S** (offline real-window evidence only) |
| 5. Trash dialogs: name, button, visible, selectable path | A4 Delete Pose — exact, selectable | accepted | copying not machine-recorded (A7 held the command); preset Trash dialogs open until UA-1S |
| 6. Older records and missing metadata | A1/A2 — `Not recorded`, Apply enabled, records unchanged | accepted | none |

Run 1's formal result stays **FAIL (replay 48/67, all procedural)**. If UA-1S passes with V2–V5 accepted, every UI
requirement above has native machine evidence plus Owner acceptance, and the remaining limitation is that
requirements 1–3 and 6 were checked in steps whose identity checks failed procedurally in run 1 (their content was
correct).

## UA-1S supplemental native check — results (2026-11-15)

**Authority:** "F-01 — UA-1S Native Execution Authorization, OWNER AUTHORIZATION: GO"; closeout under "F-01 UA-1S —
Owner Acceptance and Final Closeout". **Kit:** `8b8c971`; candidate `615acf0c…` (`fda1fb3`), qualification build
`849d0ed4…` (line 42220 only); capture script `d5d07b90…` unchanged. **Run folder (raw evidence, not committed):**
`E:\SFM_U0B_Scratch\f01-ui-acceptance-s1`.

| Result | Status |
|---|---|
| **Automated verdict** | **PASS, 25/25** (`evidence\UA_SUPPLEMENT_VERDICT.json` `3f185cf0…`), the unchanged supplement comparator. Finding (not a failure): Body Save rewrote Krystal's `character.json` and its `.bak` (the known F-T01-1 behaviour); both were restored from the backup. |
| **Owner visual acceptance** | **Accepted**, V2 (Trash dialogs), V3 (Body Preset Update), V4 (Expression Update), V5 (recovery path): approved titles, wording and buttons, recovery paths visible and selectable, no unexpected behaviour. **Source:** the Owner's closeout message in the conversation. `owner_review\OWNER_VISUAL_REVIEW.md` is still the blank template (byte-identical, `ec70a847…`), and no screenshots are in the run folder; the Owner reports having taken them, but they are not in the local evidence. |
| **Restoration** | **Verified.** Library cleanup `files_equal_pre` and `folders_equal_pre` true (nothing removed, nothing recreated); published CPM `ccbed9d7…`; both registries removed; all four inventories equal their baselines; `UA_SOURCE.dmx` unchanged (`259ea8a6…`). The 8 evidence files collected before restoration are byte-identical afterwards. |

**Measured (from the captures and the CPM log):** one SFM process on the source session; `UA Body` and `UA Expr`
saved on their own tabs and selected; A5 and A6 each captured the Update Preset confirmation (title `Character Preset
Manager`, the approved question, **Update Preset** / **Cancel**, Cancel the default) and the Trash dialog (the approved
question, `You can recover it from:`, the library Trash folder visible and selectable, **Move to Trash** / **Cancel**,
Cancel the default); A7's clipboard equals the Trash folder (the A7 command was prepared before copying, as
directed). Log: only `Save Current Body` and `Save Current Expression` written (verified); every preset dialog
cancelled; no pose operation other than Pose Info; no recovery. Library: only the two preset files added (and the
F-T01-1 rewrite); nothing removed; nothing moved to Trash.

**Product defects:** none. **Procedural deviations:** none in UA-1S. **Documentation limitation:** the Owner's
visual record and screenshots are not in the run folder (acceptance recorded from the conversation).

## Combined assessment after UA-1S

UA-1 run 1 keeps its formal **FAIL, 48/67** (replay `709065a4…`, unchanged). UA-1S is recorded separately: **PASS
25/25**, Owner accepted. Against the original UI acceptance requirements:

| Requirement | Evidence | Status |
|---|---|---|
| 1. Save Pose Full body summary | run 1 A3 (check passed); Owner accepted | met |
| 2. Pose Info order, Model path, Source shot and project, Saved Values | run 1 A1/A2/A4/B1, content correct (identity checks failed procedurally); Owner accepted | met, with the run 1 procedural limitation |
| 3. Update Pose confirmation and updated source | run 1 A4 (exact, `UA Expr`) and B1 (exact, updated shot and project); Owner accepted | met, with the run 1 procedural limitation |
| 4. Body Preset and Expression confirmations | **UA-1S A5/A6 exact; Owner accepted** | **met** |
| 5. Trash dialogs: name, button, visible, selectable and copyable path | run 1 A4 (Delete Pose, exact, selectable); **UA-1S A5/A6 (preset Trash dialogs, exact) and A7 (path copied)**; Owner accepted | **met** |
| 6. Older records and missing metadata | run 1 A1/A2: `Not recorded`, Apply enabled, records unchanged; Owner accepted | met, with the run 1 procedural limitation |

**Remaining qualification limitations:** run 1's formal FAIL stands (all 19 failures procedural: inspection order and
selections); requirements 2, 3 and 6 rest on run 1 captures whose content was correct but whose step-identity checks
failed; the Owner's visual records for both runs are statements in the conversation, not filled forms or local
screenshots. No further native run is recommended solely to correct run 1's inspection order. The UI tested natively
is `615acf0c…` for the presets (UA-1S) and `8eccf172…` for everything else (run 1); the only difference between them
is the Pose Info pose-type label (`fda1fb3`), tested offline.
