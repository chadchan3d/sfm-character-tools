# F-01 v1.1.0 RC1: native release smoke results (2026-11-18)

**Authority:** "F-01 RC1 — Native Production Smoke GO" (run); "F-01 RC1 — Owner Results and Final UI Corrections"
(closeout). Kit `real_sfm_qualification/f01_v110_rc1_smoke/` at `b8b4305`; procedure
`F01_V110_RC1_SMOKE_PREPARATION.md`.

## Verdict

| | Result |
|---|---|
| Automated (`rc1s_analyze.py`, unchanged) | **AUTOMATED SMOKE PASS, 18/18** (`RC1S_VERDICT.json` `2ac42b31…`) |
| Owner acceptance | **PASS** (Owner's report: every step completed, including Selected parts Apply; functional behaviour and standard messages normal). The per-item record form `owner_review/OWNER_SMOKE_RECORD.md` was left blank; the acceptance is the Owner's report |
| Restoration | **RESTORED**: published CPM `ccbed9d7…`, both registries removed, every protected inventory equal to its baseline (`restore.json` `043b1593…`); preset library exact, files and folders (`library_cleanup.json` `843e45ab…`) |

**RC1 smoke: PASS.** The exact RC1 production files (CPM `32183508…`, registries `f445d5ef…` and `a2254930…`,
extracted unmodified from the unsigned package `5663e088…`) ran natively in production mode. No production defect
and no unsafe behaviour was found.

## What the evidence shows (both CPM logs written by `32183508…`)

| Area | Evidence |
|---|---|
| Krystal v2 Full body | Process A: Save Pose verified, `RC1 Krystal` version 2 `full_body`, rig class `krystal-v1`; Process B (after a restart): Apply Pose RC1 Krystal committed-verified |
| Generic v3 Heavy, helpers | Save Pose verified on `heavy1`: `RC1 Heavy` version 3, engine `direct_fk_v1` revision 1, `carried_rule: null`; Apply Pose RC1 Heavy committed-verified on `heavy2` |
| Body Preset | Apply Body Preset committed-verified on Krystal (Undo by the Owner) |
| Selected parts | Apply Pose NQ1 Pose A (left arm, version 1) committed-verified on Krystal |
| Pose Info | three openings in Process A (two seeded poses, RC1 Heavy) and two in Process B |
| Clean | no refusal, failure, uncertain or recovery outcome in either process |
| Production mode | equivalence PASS (generic v3 qualified in production; `constant_channel_carried_v1` unusable in both modes) |
| Library | only the seeded records, the two new poses and their `pose_sources.json`; all kept in `evidence/library_after` |

Undo and Redo are SFM menu operations, not logged by CPM; they rest on the Owner's report.

## Recorded outside the verdict

After the procedure's steps, the Owner tried Full body Save on two other characters added to the same unsaved
session: `models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl` (Tails) and `models/fursonas/foxmccouldwm.mdl`
(Fox). Each Save ended `no-op` (`reason: cancelled`) after a refusal in the dialog; nothing was written. These are
outside the smoke's scope and do not affect the verdict (the analyzer requires no refusal *outcome*, and none
occurred). They are diagnosed separately ("F-01 — Broad Full Body Compatibility Review").

## Evidence (outside Git, `E:\SFM_U0B_Scratch\f01-v110-rc1-smoke-r1`, preserved)

`evidence/RC1S_VERDICT.json` `2ac42b31…`, `.md` `5d6a54d4…`; `logs/` (Process A `ac83c6ff…`, Process B
`8c1f80d1…`, `LOGS.json` `e0712c6a…`); `library_Q.json` `a0b78a65…`; `library_cleanup.json`; `library_after/`;
`restore.json`; `staged/IDENTITIES.json` `8db1aa38…`.

## Next

The three Owner-requested UI corrections are a separate presentation revision (`F01_V110_RC2_UI_CORRECTIONS.md`).
No signing, push, merge, tag or publication.
