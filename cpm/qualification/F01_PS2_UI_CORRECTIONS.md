# F-01 PS-2 UI corrections (2026-11-14)

**Authority:** "F-01 — Implement PS-2 UI Corrections" (Owner-approved UI corrections from the PS-2 native test).
**Baseline:** `8eb00f8` (production candidate `755be73`, CPM `84cd996c…`, the build PS-2 run 1 tested).
**UI candidate CPM:** `29db211d02413775dc351f28746eb41b719d5b169e6fa8f0bdf9637b9912344f` (1,451,230 B).
**Not natively tested.** PS-2 run 1 (`E:\SFM_U0B_Scratch\f01-ps2-v110-r1`) tested `84cd996c…`; its evidence, pins
and package stay as they are, and the PS-2 kit stays pinned to `84cd996c…`.

## Changes (interface only)

| # | Owner finding | Change |
|---|---|---|
| 1 | Selected parts picker showed about three rows on the Engineer | The picker's minimum height is eleven rows (`PROD_POSE_PICKER_ROWS`) whatever the number of groups, limited to half the available screen height and never below four rows (`prod_pose_picker_height`). Scrolling, nesting, checkboxes and tri-state groups unchanged. |
| 2 | Pose Info too sparse | Rebuilt on the Expression Preset Info pattern: a **Pose** box (Name, Type, Model, Model path, Saved, Updated, Includes, Not included, Hip position for a version 3 Full body) and a **Saved Values** tree (`Bone / Control`, `Value`) listing every saved bone or control with its saved values. "Saved from" is now "Model" plus "Model path". |
| 3 | Rig-driven Full body showed a review checklist that could not enable Save | A Full body refusal shows only its reason (which already says "Choose Selected parts to save a smaller pose."); the review checklist appears only when the review can resolve it (`review-required`). |
| 4 | "Unselected parts attached to these parts move with them." awkward | "Moving a selected bone can also move its children." Trigger unchanged and verified: only when the selection has unselected descendants (a forearm without the hand; finger1 and finger3 without finger2); never for an ordinary complete selection such as a whole finger group or a fingertip. |
| 5 | "Includes hip movement" felt obvious | Full body summary: "Facial expressions and the rootTransform are not saved." It names the rootTransform rather than "scene placement", so it never implies the visible body can't move; the hip explanation moved to Pose Info ("Hip position: Saved. Applying it moves the hips; the rootTransform stays where it is."). |

**Unchanged:** pose capture, Apply, compatibility rules (including Krystal's rig-driven refusal and the Heavy's
procedural refusal), Undo/Redo, Abort, P7, transactions, record schema and versions, the version 2 route and its
wording, the main window.

## Pose Info content

From the saved record only; nothing is re-evaluated against the scene.

- **Version 3 Full body** (example, PS-2's `PS2 Engineer Body`): Type Full body; Model `engineer.mdl`; Model path
  `models/player/engineer.mdl`; Saved; Includes `72 bones`; Not included `Facial expressions, rootTransform`; Hip
  position. Saved Values: `Saved bones (72)` as a tree following the saved skeleton (pelvis → hips, spine → neck →
  head, collars → arms → hands → fingers); the body root shows `Position x, y, z; Rotation X …°, Y …°, Z …°`, every
  other bone its local rotation.
- **Version 3 Selected parts** (example, `PS2 Krystal grip`): Type Selected parts; Model; Model path; Saved; Includes
  `Left fingers (15 bones)` (the group label when the selection exactly covered one group, otherwise `N bones`);
  the child-movement note when it applies. Saved Values: every saved bone by its exact name, nested under its
  nearest saved ancestor, with its local rotation. Recorded exclusions are listed by name (`Left unchanged: Face
  (n)`).
- **Version 2** (registry Full body): every saved control with its position and rotation.
- **Version 1** (left arm): the saved arm goals (Elbow position; Hand position and rotation), relative to the anchor.
- **Rotations** read as X/Y/Z degrees (roll about X, pitch about Y, yaw about Z, composed Z-Y-X); the exact saved
  quaternion is the value's tooltip. Positions are in SFM units.

## Unavailable metadata and open UI limitations

- **Source project / session:** pose records store the shot name and times, not the session file or project, so
  Pose Info shows no source-project field. Adding it needs a record schema change (a separate Owner decision).
- **Euler readability:** bones near gimbal alignment (for example finger roots) can show large X/Z values for a
  natural pose; the tooltip has the exact quaternion. Showing angles in each control's own SFM display convention
  would need a native check of that convention.
- **Picker size on very small screens:** limited to half the available height (at least four rows); the dialog then
  scrolls the picker.
- The PS-2 kit's comparator check `engineer.pose_info_wording` expects the tested build's Pose Info rows; a native
  check of this UI candidate needs that expectation updated.

## Offline verification

All 48 CPM suite runs (24 suites, Python 2.7.5 and 3.10.6) have the same exit codes and failing-check sets as the
previous candidate `755be73`; only the changed suites grew:

| Suite | Result | New or changed checks |
|---|---|---|
| `test_cpm_app_f01_scoped` | 484/484 (both) | Pose Info fields and values (v3 Full body and Selected parts, nesting, exclusions, v1/v2), Euler rendering, child-movement wording and trigger, Full body summary, refusal without checklist, resolvable review kept, picker sizing |
| `test_cpm_app_f01_scoped_page` | 16/16 (2.7.5, real Qt dialog) | D7 refusal with highlighted face bones shows no checklist; D8 picker minimum eleven rows with three groups (measured: rows 20 px, minimum 226 px, shown 336 px) |
| `test_cpm_app_f01_pose_page` | 120/120 (2.7.5) | U8 and V4 Pose Info: Pose box (Name, Type, Model, Model path, dates) and Saved Values tree |
| Other CPM suites | unchanged | historical rows only (canonical route `derivation.added_top_level_is_bounded`, etc.) |
| Clothing fit, operation context (three-phase) | 95/95, 108/108; compare 3/3 | unchanged |
| Kits: EF-1, SFP-1, S3, PS-2 | 34/34, 19/19, 37/37, 14/14 | unchanged (historical builds read from their pinned commits) |
