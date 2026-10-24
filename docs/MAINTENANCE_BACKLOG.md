# SFM Character Tools — Future Update Backlog

**Created:** 2026-10-24
**Baseline:** Public v1.0.0 release complete; L-6 accepted. This is a planning list only.
**Status:** No item below is authorized for implementation, no target release is assigned, and no existing qualification is reopened.

## Deferred usability issues from v1.0.0

### M-01 — Updater: misleading refusal when Animation Groups TXT is held open
- **Observed:** During qualification, when another application holds the installed TXT open, the updater refuses safely but may say: "Automatic recovery is unavailable; required files are missing."
- **Expected improvement:** Report that access to the file is blocked or unavailable, with an actionable explanation where reliably distinguishable. Do not imply files are missing without evidence.
- **Safety/evidence:** No data change or false success was observed. Deferred as W-1, non-blocking.
- **Status:** Deferred usability defect; investigate wording and detection before changing behavior.

### M-02 — Normalizer: technical no-shots message with no project/scene open
- **Observed:** Rebuild Control Groups with no project/shots available may show: "Could not resolve rebuild scope: No shots returned by sfmApp.GetShots()."
- **Expected improvement:** A short, user-facing explanation, e.g. "No shots are available. Open a project with at least one shot before running Rebuild Control Groups."
- **Safety/evidence:** Refusal is expected when there is no shot to rebuild. No destructive behavior was reported.
- **Status:** Deferred minor UX issue; do not turn the expected refusal into an unsupported operation.

## Requested presentation improvement

### M-03 — Remove redundant “SFM” from two Scripts-menu tool names
- **Owner request:** Within **Scripts > SFM Character Tools**, the SFM prefix is redundant on two of the entries.
- **Proposed menu labels:**
  - `SFM Character Preset Manager` → **Character Preset Manager**
  - `SFM Control Group Updater` → **Control Group Updater**
- **Unchanged menu context:** **Scripts > SFM Character Tools**; leave **Rebuild Control Groups Normalizer** as-is unless separately requested.
- **References to reconcile:** Menu display, launcher references, help text, main/optional READMEs, documentation and any other user-facing labels. Review optional CPM button's launcher target.
- **Compatibility caution:** SFM discovers menu scripts by files under `scripts/sfm/mainmenu`; internal filenames/paths, authority locators, signed software inventory and updater compatibility checks may depend on current names. Investigate before deciding whether to rename script files or merely presentation strings. Do not casually rename internal identities.
- **Status:** Owner-requested, implementation/design not yet approved.

### M-04 — Normalizer dialog cleanup
- **Observed:** The Rebuild Control Groups dialog shows its title twice (in the window title bar and again as an internal heading), and the title bar's “?” button does nothing.
- **Expected improvement:** Remove the duplicate internal heading and the inactive “?” button.
- **Repro:** Open **Scripts > SFM Character Tools > Rebuild Control Groups Normalizer**.
- **Scope:** Presentation only; no change to Normalizer behavior.
- **Status:** Confirmed (owner-observed). Future UI/presentation improvement; not a v1.0.0 reopening item, and not yet approved for implementation.

## Future CPM features — investigation first

### F-01 — Poses as an additional CPM preset category
- **Owner request:** Add **Poses** alongside existing Body and Expression preset capabilities.
- **Desired user outcome:** Save a character pose, apply it again, and manage pose presets through CPM.
- **Questions for design:** What transforms and controls constitute a pose? How do rigs/IK, control availability, shot/time selection, model compatibility, partial poses, and native Undo behave? How does this stay distinct from body shapes and expressions?
- **Status:** Feature request; no storage schema, GUI, scope or implementation authorized.

### F-02 — Save and/or switch Skins and Bodygroups in CPM
- **Owner request:** Investigate saving and restoring model skin/bodygroup selections, as well as easy access to changing them without preset creation.
- **Desired user outcome:** Conveniently view and change a model's skins/bodygroups, and possibly include these states in saved presets.
- **Questions for design:** Identify SFM's native skin/bodygroup APIs and actual model limitations; distinguish discrete skin/bodygroup state from body morph/scale settings; decide standalone controls vs preset membership; handle compatibility, absent choices, verification and Undo.
- **Status:** Feature investigation; do not assume both are supported or promise preset integration before feasibility work.

## Project guardrails
- Keep the published v1.0.0 software and signed data release history intact; do not edit artifacts as part of maintaining this list.
- This document records observations and owner requests, not a Blueprint revision, coding assignment, or release commitment.
- When selecting a future task, define its exact user-visible success result. Prefer bounded direct evidence; do not expand verification loops without a decision they can change.
