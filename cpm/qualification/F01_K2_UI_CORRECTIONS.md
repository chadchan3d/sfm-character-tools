# F-01: Owner-approved UI corrections after K2 (offline implementation)

**Date:** 2026-11-14. **Authority:** "F-01 — Close K2 and Implement Approved UI Corrections", Phase 2; committed under "F-01 — Authorize
Phase 2 UI Commit" after the precommit audit (section 5).
**Status:** implemented and tested offline on top of `0f18573`; committed locally; not installed, not natively
accepted. Next: designer review, then the separately authorized native UI acceptance check.

**Owner decisions (2026-11-14):** (1) Update Pose replaces the stored Source project with the current session,
matching the updated Source shot; "Not recorded" when unavailable. (2) Includes and the Hip position explanation
stay alongside the approved order. (3) The expression Update wording is accepted. (4) Lower-case paths, missing
metadata and small orphaned entries are accepted; older records stay compatible; whole-library sharing is
documented (section 2); `pose_sources.json` is excluded from portable pose exports. (5) Trash dialogs keep the full
recovery folder, selectable and copyable, with Move to Trash and Cancel (default).

**CPM:** `3984e1e1…` (K1, the K2-tested candidate) → `8eccf1723fef395fcf0678ea25c0dbdf145ba77d1558ca318887aa6cfe057194`
(1,459,023 B, ASCII, LF). The K2-tested source, its qualification build `37b0cce6…` and all K2 evidence are unchanged.

## 1. Changes

| Area | Before | After |
|---|---|---|
| Save Pose, version 2 Full body summary | "Facial expressions, gaze and the character's place in the scene are not saved." | "Facial expressions and the rootTransform are not saved." (the generic Full body text, unchanged) |
| Pose Info rows | Name, Type, Model, Model path, Saved, Updated, Includes, Not included, (hips) | Name, Type, Model, Model path, **Source shot**, **Source project**, Saved, Updated, Includes, Not included, (hips) |
| Pose Info "Not included", version 2 | "Facial expressions, gaze, scene placement" | "Facial expressions, rootTransform" |
| Source shot | not shown | the record's own `pose.source.shot_name` (versions 1, 2 and 3); "Not recorded" if absent |
| Source project | not available | the original session's `.dmx` path from a local sidecar; "Not recorded" otherwise |
| Update Pose confirmation | title "Update Pose"; 'Update "X" using the current pose?' plus a second sentence | title "Character Preset Manager"; 'Replace the saved pose "X" with the character's current pose?'; Update Pose / Cancel (default) |
| Update Preset confirmation | "Update preset?"; 'Copy the current body flexes and bone scaling into "X"?' plus "The preset's current values will be overwritten." | 'Replace the saved body preset "X" with the character's current body settings?' / 'Replace the saved expression "X" with the character's current expression?'; Update Preset / Cancel (default) |
| Delete Pose / Delete Preset (Trash) | "Move pose to Trash?" / "Move preset to Trash?"; 'Move "X" to Trash?' | title "Character Preset Manager"; 'Move the saved pose / body preset / expression "X" to Trash?'; "You can recover it from:" and the Trash folder (selectable by mouse and keyboard, copyable); Move to Trash / Cancel (default) |

Two shared helpers, `tool_confirm_action` and `tool_confirm_trash`, carry the pattern for all four reachable
confirmations in the main window (Update Pose, Delete Pose, Update Preset, Delete Preset for Body Presets and
Expressions). The unreachable legacy `CharacterPresetWindow` is not changed (production launches `ProdWindow` only).
Functional windows (Save Pose, Pose Info, Rename) and failure titles (Pose Not Saved, …) are unchanged. Confirmation
and cancellation behaviour is unchanged: the same accept/cancel outcome, Cancel default, the same post-modal
revalidation.

**Kept rows not in the Owner's list:** Includes (bone count and group) and the version 3 Full body Hip position note
(F01-DI-01, RETAIN R3) stay, after Updated, so no existing information is removed. The Owner may decide otherwise.

## 2. Source project: storage and compatibility

- **No record format change.** Pose records (versions 1–3, closed schemas, payload digest) are unchanged; no field
  is added; existing and new records stay readable by every build that reads them today, including the published
  v1.0.0.
- **Sidecar:** `<library>/Characters/<character>/pose_sources.json` (beside `library.json` and
  `pose_favorites.json`, outside the Poses folder, so pose discovery never sees it). Strict format
  `{"schema_version": 1, "record_kind": "cpm-pose-sources", "entries": {"<preset_id>": {"project": "<path>"}}}`;
  only absolute `.dmx` paths without control characters (≤ 1024 characters) are accepted. Written with CPM's
  existing safe JSON write (temporary file and `.bak`), contained to the character folder, read back.
- **Capture:** `vs.g_pDataModel.GetFileName(sfmApp.GetDocumentRoot().GetFileId())`, the call the S0 observer read
  natively in K2 (`e:\sfm_u0b_scratch\…\k2_destination.dmx`; SFM reports the path in lower case). No document, an
  unsaved session or an unusual name → not recorded.
- **Lifecycle:** Save New records it after the pose is durable. Update Pose records the session its new values come
  from (or removes the entry when unknown), so Source shot and Source project always describe the same capture.
  Rename changes nothing (keyed by identity). Delete moves only the pose file to Trash and keeps the entry, so a pose
  restored from Trash shows its project again. Entries of permanently removed poses stay as small orphans (not
  cleaned).
- **Never blocks:** a missing, unreadable or damaged sidecar shows "Not recorded"; recording failures are logged
  without the path (`PROD_POSE_SOURCE-unrecorded`) and never fail Save or Update; a damaged sidecar is never
  overwritten. Apply, compatibility and every scene path never read it (static check: only Pose Info and the store).
- **Privacy:** the path stays in the artist's local library folder. A shared pose `.json` carries no path. Sharing
  a whole character folder (or the whole library) by copying it would include `pose_sources.json`, and with it the
  full paths of the artist's SFM sessions, which can contain the Windows user name; artists sharing whole library
  folders should delete that file first.
- **Exports:** the production window has no pose or library export (the only export, a single Body or Expression
  preset file, belongs to the legacy window that production does not launch), so nothing exports the sidecar
  today. Any future portable pose export must copy pose records only and exclude `pose_sources.json` (Owner
  decision 4).
- **Limitation:** poses saved before this change, and poses saved by other builds, show "Not recorded". A pose
  file copied to another computer shows "Not recorded" there.

## 3. Verification (offline; Python 2.7.5 = SFM, 3.10.6)

| Suite | Before (`0f18573`) | After |
|---|---|---|
| Poses page (2.7.5) | 120/120 | **123/123** (field order, Source project "Not recorded", Update Pose / Update Preset / Trash pattern, copyable recovery path, preset wording) |
| Scoped page (2.7.5) | 17/17 | 17/17 (v2 summary text) |
| Scoped (both) | 484/484 | **485/485** (Pose Info order and Source rows) |
| Pose integration (both) | 204/204 | **218/218** (SP1–SP7: Save records the project outside the record; unavailable → not recorded; Rename keeps; Update records or forgets; Delete keeps, restore shows it; damaged sidecar never blocks or is overwritten; strict format; only Pose Info and the store read it; the session read on a fake sfmApp) |
| Body (both) | 257/257 | 257/257 |
| Pose library / core / live (both) | 87 / 255 / 104 | unchanged, all pass |
| M-06 instance resolution (both) | 179/179 | 179/179 |
| Operation context | 108/108, compare 3/3 | unchanged |
| Empty states (2.7.5) | 15/15 | 15/15 |
| M-05 (both) | 114/115 | 114/115 (same pre-existing failure) |
| Canonical route | 84/85, compare 2/3 | 84/85, compare 2/3: the same pre-existing failing check `derivation.added_top_level_is_bounded`, with exactly the same 11 unlisted names (section 5) |
| Kits: PS-2 14, EF-1 34, K2 11 | OK | OK (the K2 kit test now reads the K1 candidate from commit `128f9f1`, as the EF-1 kit test does) |

Test expectations changed only where the Owner changed the text or order (Poses page U8/U9/V4, scoped UI.1/UI.7,
scoped page D5/D9), plus the canonical-route allow-list entries justified in section 5.

## 5. Precommit audit: canonical route `derivation.added_top_level_is_bounded`

The check compares every top-level name added since the frozen baseline with the union of the per-milestone
allow-lists. Its printed detail is the complete added set (`sorted(added)`), not the unlisted names, which is why
the detail grew from 566 to 580 names. The audit computed the unlisted names directly:

| | Added since baseline | Unlisted (the failure) |
|---|---|---|
| Before Phase 2 (`0f18573`) | 566 | 11, all from earlier F-01 UI work: `PROD_EMPTY_STATE_GUIDANCE`, `PROD_POSE_PICKER_ROWS`, `PROD_POSE_PICKER_SCREEN_SHARE`, `prod_model_candidates`, `prod_pose_info_number`, `prod_pose_info_position`, `prod_pose_info_quat_tip`, `prod_pose_info_rotation`, `prod_pose_info_values`, `prod_pose_picker_height`, `prod_scope_selected_parts_unavailable` |
| Phase 2, before allow-list entries | 580 (14 added, none removed) | 23 = the same 11 + 12 Phase 2 names |
| Phase 2, committed | 580 | **the same 11** (no new unexplained name) |

**The 14 names** are exactly the authorized changes: the dialog helpers `PROD_CONFIRM_TITLE`, `tool_confirm_action`,
`tool_confirm_trash`; the sidecar store `PROD_POSE_NOT_RECORDED`, `PROD_POSE_SOURCES`, `PROD_POSE_SOURCES_KIND`,
`PROD_POSE_SOURCE_PROJECT_MAX`, `prod_pose_sources_path`, `prod_pose_valid_project`, `prod_pose_load_sources`,
`prod_pose_source_project`, `prod_pose_set_source`; the seam functions `prod_pose_session_project`,
`prod_pose_record_source`. A source scan of each: no menu or launcher entry point; no subprocess, ctypes, network,
`exec`/`eval`, file removal or rename; no scene write. The only scene access is the read-only
`HasDocument` / `GetDocumentRoot` / `GetFileName` in `prod_pose_session_project`. The only write is
`prod_pose_set_source`'s contained `p02_safe_write_json` of the sidecar. The existing changed-text tops are
`PROD_POSE_FULL_BODY_NOT_INCLUDED` and `prod_pose_info_view` (the approved wording and order) and `ProdWindow`
(the dialogs and call sites; `derivation.changed_methods_are_bounded` passes).

**Allow-list entries, with justification:** the two seam functions join `F01_STAGEC_NEW_TOP`, which the pose
integration check `C0.stage_c_block_names_equal_route_allow_list` requires to equal the Stage C block's names; the
other 12 form a dedicated, commented `F01_K2UI_NEW_TOP`. Nothing was suppressed; the pre-existing failure and its 11
names stand unchanged.

## 4. Not done / boundary

No native run, installation, promotion, signing, push or merge. The K2-qualified Save/Apply engine, mapping,
ownership, Undo/Redo, P7 and recovery code are unchanged (the diff touches only the dialogs, the Save/Update/Pose
Info call sites, the sidecar store and the Pose Info view). The Owner's visual review needs an installed build,
which is a separate authorization.

## 6. Addendum (2026-11-15): two pose types (Owner decision after UA-1)

**Change:** Pose Info's Type is always **Full body** or **Selected parts**. A version 1 arm pose (left arm, the right
arm, or both) shows Type `Selected parts` and its saved part(s) under Includes (`NQ1 Pose A`: Type `Selected parts`,
Includes `Left arm`). Version 2 and version 3 records show what they showed before. CPM `8eccf172…` →
`615acf0c23ffcf5c278785bb47de6aaf6a7b9ae26779b9313979ac928240c432` (`prod_pose_info_view` only; 9 lines).

**Where pose types appear (inventory):** only the Pose Info Type row. Pose list rows show names only; Help names no
pose type; the Saved and Applied statuses name the pose only. Messages that name a **part** (the Update refusal
"… Left arm can't be read …", the Pose Info note "Can't be applied to …: Right arm", the Saved Values group "Left arm
goals, relative to CollarL", the Apply Parts dialog rows) name the part, not a type, and are unchanged. The Poses page
state summary (`prod_pose_ui_state`, "Saved: Left arm") is not displayed (the page shows only the Motion Editor note)
and is unchanged.

**Unchanged:** records (no migration or rewrite), the version 1 fixed scope, every Save, Update, Apply, compatibility,
recovery and registry path, and the version 2 and version 3 behaviour.

**Tests (Python 2.7.5 and 3.10.6):** scoped 486/486 (UI.7 now expects Selected parts + Includes Left arm; new UI.7b:
every v1, v2 and v3 record shows exactly the two types, a two-arm v1 record includes "Left arm, Right arm"); Poses
page 123/123 (U8 and V4 expect Selected parts and Includes; the two-part record likewise); body 257/257, pose
integration 218/218, pose library/core/live 87/255/104, M-06 179/179, operation context 108/108, scoped page 17/17,
empty states 15/15; kits PS-2 14, EF-1 34, K2 11, UA-1 7 and 12 (2.7.5). Pre-existing, unchanged: M-05 114/115 (A9),
canonical route 84/85 (`derivation.added_top_level_is_bounded`, no new top-level name). No native qualification:
the change is display-only and no functional dependency was found.
