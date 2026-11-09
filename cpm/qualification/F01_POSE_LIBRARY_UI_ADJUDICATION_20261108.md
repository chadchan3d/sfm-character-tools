# F-01 Pose Library — UI Adjudication after NQ1 (Astra; Owner-accepted)

**Date:** 2026-11-08. **Author:** Astra (adjudication of the Owner's NQ1 Process A usability observations).
**Status:** accepted by the Owner; implemented offline separately (see the Ledger). This file records Astra's decision as
given; source references are to `cpm/app/SFM_Character_Preset_Manager.py` at `0c084e8`. It does not substitute any
earlier assistant-proposed design.

> The main Poses tab is already usable. **Pose Info needs subtraction; Save Pose needs clearer consequences and less
> inactive clutter.** None of this warrants changing the active qualification build.

## A. Pose Info

Before applying a pose, the artist principally needs to know **what it contains, which model it came from, and any
relevant limitation**.

| Current item | Decision | Reason |
|---|---|---|
| Pose name | **Keep** | Confirms which saved pose is being inspected. |
| Character | **Change** | Identify the saved source model, not the currently selected character. |
| Saved date | **Keep, subordinate** | Helps distinguish versions. Show the latest update date when applicable; seconds are unnecessary. |
| Source shot | **Remove** | `shot15` alone rarely identifies useful provenance. |
| Saved scope | **Keep; rename "Includes"** | Answers the most important question: what will this pose apply? |
| Included control count | **Remove** | "15 controls" does not tell the artist which fingers or movements are included. |
| "Articulation only" | **Replace where consequential** | It is implementation terminology. Explain the practical effect instead. |
| Body parts/bone list | **Remove as a permanent raw list** | The current tiny list is unusable and duplicates the scope summary. |
| Model path | **Condense** | A model filename distinguishes variants; the full path can remain selectable or available on hover. |
| Pose rule and revision | **Remove** | Useful in diagnostics, not an artist's decision. |

There is a concrete labeling problem: the current **Character** value comes from the current selection, while the model
path comes from the saved pose. Those can describe different characters. Use the record's source model for pose
information. (Source: line 36917.)

**Do not add source-project collection or an Advanced Information section.** Neither presently earns its maintenance
cost or screen space. Existing diagnostic records can retain technical provenance.

A much smaller dialog could communicate:

> **SFP1 Grip**
> Includes: Left fingers
> Saved from: krystal2020.mdl
> Saved: 8 November 2026, 19:32
>
> Applies the saved finger bends using the destination hand's orientation.
>
> **Close**

Use "Left fingers" only when it accurately describes the recorded selection. For an individually selected thumb or
mixed selection, name those parts. Retain recognizable rig/control names when no trustworthy friendly label exists — do
not invent anatomical classifications.

For other records, "Includes: Left arm" or "Includes: Full body" is sufficient **unless there are consequential
exclusions**. Then add, for example, "Not included: facial expression controls." Any known incompatibility with the
selected destination should appear plainly; do not add a positive "Compatible" badge based only on preliminary browsing
checks.

## B. Save Pose

**Keep the existing name field, Full body/Selected parts choice, grouped picker, contextual explanation, Save and
Cancel.** The Owner successfully found and saved fingers; this does not need a new selection system.

Bounded changes:

- **Hide the inactive picker in Full body mode.** A disabled tree full of unchecked boxes suggests those parts are
  excluded, even though it is not controlling that save. Show the actual coverage explanation and any required
  exclusion review instead.
- **Retain the picker in Selected parts mode.** Keep group selection and individual controls, including independent
  finger/thumb selection.
- **Hide genuinely empty organizational groups.** However, the inspected code already excludes groups with neither
  selectable nor unavailable entries. Apparently empty rows may contain unsupported rig controls. Do not
  indiscriminately remove them. (Source: line 46324.)
- **Make unavailable-only groups visibly unavailable**, without an actionable-looking checkbox. Keep their reason
  accessible, such as "Driven by the rig; cannot be saved separately." Mixed groups should retain disabled entries where
  they explain an important limitation.
- Shorten repeated group-path prefixes where the remaining label is unambiguous. Preserve the original grouping and
  selection meaning.

The most important wording correction is "Unselected parts unchanged." That can be read as a guarantee that other
anatomy will remain visually motionless. It is too broad. The current summary generates it unconditionally for selected
parts. (Source: line 47810.)

For the finger example: **"Saves the selected finger bends. Applying this pose keeps the destination hand's position and
orientation."** For a general selection: **"Saves the selected parts. Applying may also move parts attached to them."**
Add more explanation only when the particular selection needs it. Do not repeat generic safety prose beneath every
group.

Likewise, distinguish **facial expressions** from **skeletal facial controls**. "Facial controls unchanged" is
inappropriate if the selected route includes some facial bones. Coverage wording must follow the actual route and
exclusions.

## C. Main Poses tab

**Keep its current layout.** Search, sorting, favorites, the compact name list and six action buttons have clear
purposes. Do not add columns, tabs, technical badges or a larger window.

The Motion Editor message is **not evidence of incorrect mode detection**. It is an unconditional label constructed when
the page is created, not a live status report; the Apply gate separately reads `GetTimelineMode()` (label: line 30829;
mode check: line 43576). It is nevertheless misleading presentation. The smallest correction is neutral instructional
wording: **"Apply poses in the Motion Editor."** Keep the existing actionable refusal when Apply is attempted in another
mode. There is no need to introduce continuous mode monitoring.

One useful clarification belongs on **Update Pose**, preferably in its existing confirmation or tooltip: **"Replace this
saved pose with the character's current pose."**

## Priority and disposition

**Meaningful corrections before UI release (required):**
1. Remove the misleading "unselected parts unchanged" promise.
2. Stop presenting the selected character as saved-pose provenance.
3. Replace the warning-like static Motion Editor message.
4. Make saved coverage and consequential exclusions readable.
5. Remove misleading inactive selection controls in Full body mode.

**Optional polish:** shorter group labels, simpler date formatting and reduced dialog framing.

No detailed bone browser, source-project field, Advanced section or main-window expansion is justified. Implement these
presentation changes separately while preserving the accepted selection, compatibility and transaction behavior.
