# F-01 Pose Library — UI Presentation Corrections (Astra review of `284cfa2`)

**Date:** 2026-11-09. **Authority:** Astra's UI implementation review of `284cfa2` — CORRECTIONS REQUIRED; Owner-accepted,
bounded offline corrections. Builds on `F01_POSE_LIBRARY_UI_ADJUDICATION_20261108.md` and
`F01_POSE_LIBRARY_UI_REFINEMENT.md`. Offline only; the next gate is Owner-operated native UI acceptance.

## 1. Corrections against the review

| Review point | Correction |
|---|---|
| 1. Remove unnecessary Pose Info explanations | No generated paragraph for an ordinary Selected parts pose. Removed "Applies the saved bends…", "Applies the saved body pose.", "using the character's rig", "(chosen when saving)" and "(from supported metadata)". A sentence appears only for a consequential effect: unselected attached parts that move with the selection, or a selected body root that keeps its position. Recorded exclusions stay (`Not included: Face controls`); a full body states only what it never includes (`Not included: Facial expressions, scene placement`; version 2 adds `gaze`). The destination-incompatibility note is unchanged. Dates read `November 8, 2026`. |
| 2. Simplify Save Pose explanations | No "Saves the bends of…" and no parent-bone statements; an ordinary valid selection shows no text. Kept, when they apply: unsupported controls (existing refusal), required review and exclusions, what a full body does not save including scene placement ("Facial expressions and the character's place in the scene are not saved."), "Unselected parts attached to these parts move with them." and "The body root keeps its position." No bone identifiers in prose; no promise that unselected parts stay motionless. |
| 3. Recorded group labels | `prod_scope_friendly_label`: a label of plain words is kept as recorded (`Left Fingers`, `Left fingers`); a single camel-case word is spaced (`LeftFingers` -> `Left fingers`); count labels, control names or irregular spacing return none, and the recorded controls are named. A group label is still used only when the saved selection exactly covered that group (`prod_scope_label`); individual and mixed selections show their recorded control names. |
| 4. Preserve accepted behaviour | Unchanged: the pose engine and transactions, Save/Update/Apply, schema and compatibility, v1/v2, the Poses tab layout, the hidden Full body picker, Selected parts grouping and unavailable-control handling, source-model identification. No new fields, dialogs, tabs or sections. |

## 2. Rendered text (offline)

**Pose Info, SFP1-style finger grip** (a group-covered selection):

```
SFP1 Grip
Includes:     Left fingers
Saved from:   krystal2020.mdl
Saved:        November 8, 2026
                                   [Close]
```

| Record | Pose Info rows and sentence |
|---|---|
| Version 3 Full body with a confirmed exclusion | `Includes: Full body` / `Not included: Face controls, facial expressions, scene placement` / `Saved from` / `Saved`; no sentence |
| Version 3 Full body | `Includes: Full body` / `Not included: Facial expressions, scene placement` / …; no sentence |
| Version 3 single forearm | `Includes: forearm` / … ; "Unselected parts attached to these parts move with them." |
| Version 3 mixed selection | `Includes: thumb1, finger1, finger3` / … ; "Unselected parts attached to these parts move with them." |
| Version 3 single thumb tip | `Includes: thumb1` / …; no sentence |
| Version 2 Full body | `Includes: Full body` / `Not included: Facial expressions, gaze, scene placement` / …; no sentence |
| Version 1 left arm (updated) | `Includes: Left arm` / `Saved from: krystal2020.mdl` / `Updated: November 2, 2026`; no sentence |

**Save Pose guidance line:**

| Choice | Text |
|---|---|
| Selected parts: a whole finger group, or a fingertip | (none) |
| Selected parts: a forearm, a thumb base, or two fingers with one between | Unselected parts attached to these parts move with them. |
| Selected parts: the body root | Unselected parts attached to these parts move with them. The body root keeps its position. |
| Full body (version 3) | Facial expressions and the character's place in the scene are not saved. |
| Full body with highlighted facial bones included / left out | Includes the listed facial bones. Facial expressions are not saved. / The listed controls are left as they are on the character. |
| Full body (version 2 route) | Facial expressions, gaze and the character's place in the scene are not saved. |
| Nothing selected / unsupported control / refused Full body | the existing messages, unchanged |

## 3. Tests

The `ui_copy` section of `test_cpm_app_f01_scoped.py` is rewritten around the review: the ordinary grip has exactly
Includes, Saved from and the date and no explanation (UI.1); consequential exclusions remain (UI.2); attached-part
movement remains where it happens (UI.3); a full body shows only what it does not include (UI.4); spaced and
camel-case group names (UI.5); individual and mixed selections name their recorded controls (UI.6); legacy version 1
and 2 records remain readable (UI.7); plus no banned phrase in any rendered record, Save guidance cases, unambiguous
group labels and the Poses tab line. The Qt Save dialog and Poses page tests are updated to the corrected copy and date
format.

| Suite (Python 2.7.5 and 3.10.6) | `284cfa2` | corrected |
|---|---|---|
| `test_cpm_app_f01_scoped.py` | 385/385 both | **389/389 both** |
| `test_cpm_app_f01_scoped_page.py` (Qt) | 14/14 | 14/14 (copy updated) |
| `test_cpm_app_f01_pose_page.py` (Qt) | 119/119 | 119/119 (date format updated) |
| body, pose core/library/integration/live | 246; 255/87/204/104 both | identical |
| `test_cpm_app_canonical_route.py` | 84/85 historical row | 84/85, same row (`PROD_EMPTY_STATE_GUIDANCE`, `prod_model_candidates`); `PROD_POSE_FULL_BODY_NOT_INCLUDED` replaces `PROD_POSE_FULL_BODY_EFFECT` in the bounds |

CPM `d6a40c6e…` -> `7548d1eb25a7479c9b3c0fffa2186d187ef3763b123412ca5ae6ef2cf6899a45`; every changed hunk is in the presentation helpers or the Save dialog's version 2 line.
