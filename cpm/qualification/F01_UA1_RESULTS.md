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
