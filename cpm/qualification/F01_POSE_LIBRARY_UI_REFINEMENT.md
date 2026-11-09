# F-01 Pose Library — UI Refinement (offline implementation)

**Date:** 2026-11-09. **Authority:** Owner-accepted Astra UI adjudication after NQ1
(`F01_POSE_LIBRARY_UI_ADJUDICATION_20261108.md`). **Baseline:** `0c084e8` (CPM `2d791dec…`). **Result:** CPM
`d6a40c6ea1639f8a262d02282934e7165fe784129e58b84c2ab48a84d269cae5`. Offline only; native UI acceptance is separately
authorized. Nothing installed, enabled, pushed, merged or released.

## 1. Scope

Presentation only. Unchanged: skeletal mathematics, the scope compiler, the dependency engine, the transaction engine,
the pose schema, compatibility rules, v1/v2 behaviour, and Save / Update / Apply / Undo/Redo behaviour. The one data
addition is presentation-only: the Save dialog inventory now carries each bone's parent (`parents`), used to word the
selection summary; it is not part of the inventory signature, the request or the record.

All five required corrections are implemented; of the optional polish, shorter group labels, simpler dates and reduced
Pose Info framing are implemented (no group boxes).

## 2. Changes

| Area | Change | Code |
|---|---|---|
| Pose Info | Built from the saved record only (`prod_pose_info_view`): **Includes** (a readable group label when the saved selection equals one plain group, e.g. `Left fingers`; otherwise the recorded control names, the full list as a tooltip), **Not included** for consequential exclusions (e.g. `Face controls (chosen when saving)`), **Saved from** the record's model file name (full path as a tooltip, selectable), the latest date (`Updated:` when updated, else `Saved:`; no seconds), and one sentence on what applying does. Removed: Character (current selection), Source shot, control count, the permanent bone list, the Technical details group, Model path and Pose rule. The note for a part that can't be applied to the selected character is kept; no positive "Compatible" badge. | `open_pose_info`, `prod_pose_info_view`, `prod_pose_info_date`, `prod_scope_info` (diagnostic data keeps the rule) |
| Save Pose | The picker is **hidden** in Full body mode (shown for Selected parts, with group and individual selection). Unavailable-only groups show no checkbox, read `<group> (unavailable)`, and keep each entry's reason. Group labels drop a repeated prefix only where the result is unambiguous; the full path is the tooltip. | `prompt_pose_scope`, `prod_scope_group_labels` |
| Coverage wording | The unconditional "Unselected parts unchanged" is gone. Selected parts: "Saves the bends of <group label or the selected parts>." plus, from the actual hierarchy, "Applying keeps the position and orientation of <the parts the selection hangs from> on the destination character.", "Parts attached below them move with them." and "The body root keeps its position." where they apply; without hierarchy data, "Applying may also move parts attached to them." Full body distinguishes facial expressions (flex controls) from skeletal facial bones; the version 2 route says facial expressions, gaze and placement are not saved. | `prod_scope_summary`, `prod_scope_selection_effect`, `prod_scope_friendly_label` |
| Poses tab | Layout, controls and sizes unchanged. The static line reads "Apply poses in the Motion Editor." Update Pose's confirmation and tooltip read "Replace this saved pose with the character's current pose." | `PROD_POSE_EDITOR_NOTE_COPY`, `confirm_pose_update`, page construction |

Friendly labels only reformat a plain one-word group name (`LeftFingers` -> `Left fingers`); control names, counts
and anything else are shown as recorded. A part between two selected parts is never described as kept in place (it
moves with the selection).

## 3. Layout (as rendered by the offline Qt tests)

**Pose Info**, a selected-parts record:

```
SFP1 Grip                                   (bold, plain text)
Includes:     Left fingers
Saved from:   krystal2020.mdl               (tooltip: the full model path)
Saved:        8 November 2026, 19:32
Applies the saved bends of these parts. Applying keeps the position and orientation of bip_hand_l on the
destination character.
                                                           [Close]
```

A version 1 record: `Includes: Left arm`, `Saved from: krystal2020.mdl`, `Updated: 2 November 2026, 10:15` (no
sentence). A version 3 Full body with an exclusion adds `Not included: Face controls (chosen when saving)` and "Applies
the saved body pose. Facial expressions (flex controls) and the character's placement in the scene are not changed."

**Save Pose**: Name; Full body / Selected parts; in Full body, no picker: the coverage line and, when needed, the
Review scope box. In Selected parts, the picker with shortened group labels (`LeftFingers`, `Face`, `Arms > LeftArm`
next to `RigArms > LeftArm`), unavailable-only groups as `LeftArm (unavailable)` without a checkbox, then the coverage
line, Save and Cancel.

**Poses tab**: unchanged, with "Apply poses in the Motion Editor." above the search row.

## 4. Representative records checked (offline)

Version 3 Selected parts (a whole group; a single thumb joint; a mixed selection with an unselected part between two
selected ones; a forearm with parts attached below; a selected body root), version 3 Full body with and without a
confirmed exclusion, version 2 Full body, version 1 left arm (updated), and the real MC-02 picker groups.

## 5. Tests (Python 2.7.5 SFM `-E -s -B`, 3.10.6 `-I`)

| Suite | Before (`0c084e8`) | After |
|---|---|---|
| `test_cpm_app_f01_scoped.py` | 364/364 both | **385/385 both** (+20 `UI.*` checks and the `ui_copy` section row; 4 copy expectations updated) |
| `test_cpm_app_f01_scoped_page.py` (Qt) | 12/12 | **14/14** (hidden picker, group labels, unavailable-only group; copy updated) |
| `test_cpm_app_f01_pose_page.py` (Qt) | 118/118 | **119/119** (Pose Info layout, tab line, Update confirmation and tooltip) |
| `test_cpm_app_f01_body.py` | 246/246 both | identical |
| `test_cpm_app_f01_pose_core/library/integration/live.py` | 255/87/204/104 both | identical |
| `test_cpm_app_canonical_route.py` | 84/85 historical row | 84/85, same row (`PROD_EMPTY_STATE_GUIDANCE`, `prod_model_candidates`); the seven new presentation names are listed in `F01_SFP1_NEW_TOP` |

Every test expectation changed here asserts wording or layout that the adjudication replaced; no behavioural assertion
was relaxed.

## 6. Not done

Astra's "Hide genuinely empty organizational groups" needs no change: the view already omits groups with neither
selectable nor unavailable entries. The Help dialog's own text was not part of the adjudication and is unchanged. No
Advanced section, source-project metadata, bone browser, new tab or larger window.
