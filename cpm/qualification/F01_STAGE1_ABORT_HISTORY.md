# F-01 Stage 1: the Abort-only Redo history exception (2026-11-19)

**Authority:** the Designer's "F-01 — Run 3 Recovery Findings Disposition", **ACCEPT WITH CONDITIONS** (checkpoint
`46ca4df`). Findings: `F01_STAGE1_FOX_RUN3_FINDINGS.md`.

**Status:**
- Implemented and tested offline; the native check is proposed, not prepared.
- Nothing installed. Run 3's INCOMPLETE verdict (`561f1b09…`) and all run 3 evidence are preserved unchanged.

## 1. Identities

| Item | Value |
|---|---|
| CPM | `2088b4af…` → **`7259e80a5d462eba1aeaa25cf89e9f57cf1081caaeac3002de8db6fbe488ab55`** (1,523,620 B; 91 lines added, 21 removed). Exact diff: `F01_STAGE1_ABORT_HISTORY.diff` (`88cebabf…`, against `46ca4df`) |
| Qualification build (derived, not staged) | **`39f2e35542180952d37f0d75b20d4c5cc89f24db16031b905655dc2310462421`** (line 42630 only, the registry mode; the same derivation reproduces run 3's `b195515f…` from `2088b4af…`) |
| Run 3 replay extract | `cpm/convergence/tests/fixtures/f01_body/fox_run3_abort_extract.json` `1baff1ec…` (read-only extract of run 3's UNDO2 and ABORT captures and its Process B log) |

## 2. The CPM correction

**The new predicate, `prod_pose_abort_undo_check(undo, base)`:**
- **Where it is called:** only after `AbortUndoableOperation`, through a new `abort_record` argument of
  `prod_pose_same_state`, `prod_body_same_state` and `prod_scope_same_state`. These cover the three routes: region
  poses, Full body and Selected parts.
- **Return value:** `(problems, redo_cleared)`.
- **It verifies when either:**
  - the Undo state equals the P1 baseline exactly (the existing behavior); or
  - **all** of the following hold:
    - Redo was pending at P1: `can_redo` true with a non-empty `redo_desc`;
    - Redo is now empty: `can_redo` false and `redo_desc` "";
    - every other member equals P1 exactly: `enabled`, `can_undo` and `undo_desc` (the top entry);
    - both states are complete and readable, with Undo enabled.
- **Anything else is unverified:**
  - a missing or unreadable observation, or a non-boolean flag;
  - an extra member;
  - Redo appearing or being replaced;
  - a changed top entry or Undo availability;
  - Undo becoming disabled;
  - a pending entry recorded without a description.

**Unchanged:**
- **P2:** the same functions without `abort_record` still compare the Undo state exactly. The pre-`StartUndo` check
  and the no-op check are also exact.
- **The rest of the Abort comparison**, all exact: authored state, evaluation, every written binding's snapshot, the
  gate, instance resolution and the observed constraints.
- **P7, transaction ownership, the StartUndo, FinishUndo and abort-failure paths, and the recovery lockout.**
- **The Body Preset bone-scale route and Clothing Fit:** their Abort verification never compared the Undo history,
  and OT1 verified Body Preset natively with Redo cleared.

**Result and log:**
- A verified Abort returns `{"phase": "not-applied", "reason": …}`. It adds `"redo_cleared": true` only when the
  exception applied, so the exact case's result is unchanged.
- The log lines `abort-verified`, `BODY-abort-verified` and `SCOPE-abort-verified` now include `redo_cleared`.

**User-facing messages (the Designer's wording):**
- **Verified, Redo cleared:**
  - the status reads "Your character was restored, but SFM cleared your Redo history.";
  - a dialog titled **Pose not applied** shows the same text;
  - there is no lockout.
  - All three routes are reached through Apply Pose, so the one title applies to each.
- **Verified, exact:** the status reads "The pose couldn't be applied. Nothing was changed." as before, with no
  dialog.
- **Genuinely unverified:**
  - the message is "CPM couldn't confirm that all changes were undone. Check your character before continuing.
    Restart SFM to use pose tools again.";
  - the guard's dialog title for pose operations (`PROD_POSE_SCENE_LABELS`) is **Pose operation stopped**;
  - other operations keep "Recovery could not be verified";
  - the process-wide lockout is unchanged.

## 3. Offline tests

**Results:**

| Suite | Result |
|---|---|
| Stage 1 `test_cpm_app_f01_structural_rig` (section O, Full body route) | **298/298** on 2.7.5 and 3.10.6 (243 before) |
| Selected parts `test_cpm_app_f01_scoped` (section L) | **494/494** on both (487 before) |
| Region poses `test_cpm_app_f01_pose_live` (D8R) | **109/109** on both (104 before) |
| M-05 `test_cpm_app_m05_static_scale` (D11b, the real `ProdWindow.guard`) | 115/116 on both; D11b passes; A9 is the pre-existing failure (114/115 before) |
| Stage E body `test_cpm_app_f01_body`, pose integration | 261/261 and 218/218 on both, unchanged |
| Full regression | identical apart from the added checks (section 5) |

**Teeth.** The same suites were run against run 3's CPM (`2088b4af…`, from Git at `e32b157`):
- the Redo-cleared verification checks fail on every route;
- section O's in-suite teeth load that build and reproduce run 3 offline: exact restoration, then
  `BODY-abort-unverified {"problems": ["Undo history changed or unreadable"]}`, then recovery unverified.

**The model of SFM.** `fake_sfm_body.discard_redo_on_start` models SFM's measured behavior: starting an action
discards pending Redo. It is opt-in, so every earlier test keeps its previous fake behavior.

**What section O covers:**
1. **The predicate.** These verify:
   - exact history, without or with pending Redo;
   - pending Redo cleared, with the flag.

   Eleven unexpected-history cases are unverified:
   - Redo appearing or being replaced;
   - an owned entry left on top;
   - Undo availability changed;
   - Undo disabled after the Abort or at P1;
   - only the flag or only the description cleared;
   - a pending entry without a description;
   - a changed top entry or disabled Undo without Redo.

   Also unverified:
   - every member missing or unreadable, on either side;
   - non-boolean flags, an extra member, or a non-mapping state.
2. **Replay of run 3's evidence** (the extract, pinned; the corrected logic, **not** a native result):
   - the observer saw ABORT equal to UNDO2 in every set, differing only in `can_redo` and `redo_desc`;
   - the native log's only problem was the Undo history;
   - the old exact predicate reproduces it, and the corrected predicate verifies with `redo_cleared`.
   - `enabled` is not in the capture. It was true at P1, because P2 passed. After the Abort it is taken as true, and
     a disabled state stays unverified.
3. **The Full body route, live:**
   - Apply, Undo, then an injected after-writes failure with the Redo discard: the result is verified, with the
     flag. Keys and the Undo stack are exact, Redo is empty, and the calls are StartUndo then Abort.
   - Exact without pending Redo, and pending Redo kept by the fake: the plain result, with no flag.
   - Each of these is unverified:
     - an authored difference with Redo cleared (caught by the authored comparison, not the history);
     - an owned entry left on top;
     - Undo disabled after the Abort;
     - an unreadable Redo;
     - Redo appearing;
     - a failed Abort.
   - **P2:** Redo cleared between P1 and P2 is **stale**, and nothing is written or opened.
4. **Static:**
   - the P2 calls take no `abort_record`, and each route's Abort call does;
   - the exact wording and titles;
   - the guard's title selection.
5. **The Poses window** (qualification build):
   - Redo cleared shows the status and the **Pose not applied** dialog, with no lockout;
   - exact keeps "Nothing was changed." with no dialog;
   - a genuine failure locks out with the new message, and the next Apply is refused.

**Selected parts (L) and region poses (D8R):**
- verified with the flag when Redo is cleared;
- exact without the flag;
- each of these is unverified: an authored difference with Redo cleared, an owned entry left on top, and (Selected
  parts) Undo disabled;
- **P2:** stale (Selected parts).

**M-05 D11b:** the real guard titles an unverified pose recovery **Pose operation stopped** and keeps "Recovery could
not be verified" for Apply Body Preset.

## 4. Native recovery check (proposed here; prepared in section 7)

**Purpose:**
- confirm that the corrected CPM reports verified restoration natively when SFM clears Redo;
- confirm that the exact case still reports "Nothing was changed";
- confirm that no lockout follows a verified Abort.

This is not a repeat of the Fox Save, Apply and visual qualification.

**Fixture (existing Fox material, read-only sources):**
- a fresh copy of run 3's saved disposable session (`s1_session.dmx`, `fcf2441c…`), which holds Fox S and Fox D,
  rigged and posed;
- a byte copy of run 3's saved `S1 Fox` record (`292bc334…`) and its `pose_sources.json` (`a31ea823…`), from
  `evidence/library_after`.

Both are seeded into the library by the tool and removed again by `restore`. The preserved run 3 files themselves are
never opened.

**Infrastructure:**
- the Stage 1 kit's existing commands: build (re-pinned to `7259e80a…` / `39f2e355…`), pre, install, check,
  collect-logs, restore and library;
- the unchanged capture observer;
- one new `seed` command, and a small analyzer and procedure.

**One SFM process, no save, five captures:**

| Step | Action | Expected | Capture |
|---|---|---|---|
| R1 | Open the session copy, Refresh, select Fox D and `S1 Fox`, setup line | Apply enabled | BASE |
| R2 | Apply Pose | `Pose applied: S1 Fox.` | APPLY |
| R3 | Edit > Undo Apply Pose S1 Fox | Redo pending | UNDO |
| R4 | Fault line, Apply Pose | **Pose not applied**: "Your character was restored, but SFM cleared your Redo history." No lockout | ABORT1 |
| R5 | Fault line, Apply Pose (no Redo pending now) | "The pose couldn't be applied. Nothing was changed." | ABORT2 |
| R6 | Apply Pose, then exit without saving | `Pose applied: S1 Fox.` (the pose tools are not paused) | APPLY2 |

**Gates:**
- **Identity:** the qualification build `39f2e355…`.
- **R4, ABORT1 against UNDO:**
  - every set (Fox D, Fox S and the peer) is exact;
  - the Undo state is identical except that the pending Redo is cleared;
  - exactly one `BODY-abort-verified` with `redo_cleared: true`.
- **R5:** ABORT2 equals ABORT1 exactly, including the Undo state, with exactly one `BODY-abort-verified` with
  `redo_cleared: false`.
- **No lockout:** no `abort-unverified`, `RECOVERY_BLOCKED` or `recovery-unverified` anywhere, and APPLY2's Fox D
  equals APPLY's.
- **Isolation:** the source and peer are unchanged throughout, and each fault slot is consumed.
- **Restoration:** the library and the published installation are restored exactly.

**Genuine-failure protection:**
- It is not injected natively: that would need a new fault hook that leaves writes in place or skips the Abort,
  which is not proposed.
- It is covered offline (sections 3.1, 3.3 and 3.5).
- Run 3 itself exercised the native lockout path. Its process-wide pause was logged, and the guard and its pause
  logic are unchanged apart from the title and message.

## 5. Full regression

`run_regressions_v110` (98 result lines) against the Fox run 2/3 baseline: every line is identical except the added checks (pose live 104 to 109, scoped 487 to 494, M-05 114/115 to 115/116, each on 2.7.5 and 3.10.6). The pre-existing historical failures, including M-05 A9, are unchanged.

## 6. Boundaries

- No installation, staging or native execution.
- No Stage 2 work, production promotion, signing, push, merge or release.
- Runs 1 to 3 and their verdicts are unchanged.

## 7. Native check prepared (2026-11-19)

**Authority:** the Designer's "F-01 — Targeted Native Abort Qualification" (ACCEPT offline correction; checkpoint
`25ba936`).

**The kit, `real_sfm_qualification/f01_stage1_recovery/`:**

| File | Identity | Notes |
|---|---|---|
| `observer/F01_S1R_Capture.py` | `100e79a4…` | Runs the Fox capture `F01_S1F_Capture.py` unchanged (`765eefc2…`, verified before use, in a private namespace) with the six steps. Then writes the sidecar `S1F-<step>.undo.json` with `IsUndoEnabled`, `CanUndo`, `CanRedo` and both descriptions, read directly and with raw types. |
| `tools/s1r_tool.py` | | `build`, `pre`, `install`, `check`, `seed`, `library`, `collect-logs`, `restore` and `analyze`, through the Fox, K2, S3 and UA-1 tools, unchanged. `seed` (the one new command) copies run 3's `S1 Fox` record (`292bc334…`) and `pose_sources.json` (`a31ea823…`), verified, into the library. |
| `tools/s1r_analyze.py` | `8128e162…` | Gates EVIDENCE, SETUP, APPLY, REDO_ABORT, EXACT_ABORT, OPERATIONAL and PEER, reusing the Fox analyzer's helpers. |
| `PROCEDURE.md` | `56d03638…` | |
| `s1r.template.json` | | All pins. The `R2_FIXTURE` path is run 3's saved session (`fcf2441c…`), so the unchanged `pre` makes the disposable copy `S1R_SESSION.dmx`. |
| `tests/test_s1r.py` | | **61/61** on 3.10.6 and 18/18 on 2.7.5 (the wrapper and template; the analyzer and tool are Python 3 tools). |

**What the tests cover:**
- **The wrapper:** six steps; the direct sidecar; refusals of a changed capture, an unknown step and a repeated
  capture, writing nothing; non-boolean and unreadable observations kept as such; the real Fox capture found and
  accepting the patched steps.
- **The analyzer,** on a simulated run:
  - the expected run passes;
  - the old build's run-3-like result **fails**;
  - **FAIL** variants: no pending Redo at UNDO; Fox D not restored or evaluated differently; peer or source
    changed; top entry, Undo availability or Undo enabled changed; Redo kept; no `redo_cleared`; fewer writes; the
    fault slot not consumed; ABORT2 Redo-flagged, different or disabled; APPLY2 unverified or not applied; a logged
    lockout; an extra outcome;
  - **INCOMPLETE** variants: a missing, inconsistent, non-boolean, unreadable or foreign sidecar; a missing capture;
    two processes; another session; a moved playhead; a saved session copy; the wrong build; extra or changed
    library files; an incomplete restore; another pose or set names.
- **The template:** the pins are the kit files, the candidate `7259e80a…`, the derived `39f2e355…` and run 3's
  files.
- **Real formats:** the analyzer's event and P6 parsing was also checked against run 3's real log.

**The steps:** one SFM process, no Save, six captures (BASE, APPLY, UNDO, ABORT1, ABORT2, APPLY2), as in section 4.
Undo enabled is observed directly at every step, not assumed.

**Readiness:**
- The run folder `E:\SFM_U0B_Scratch\f01-stage1-recovery` holds `s1r.json` (paths filled, pins from the template).
- `build` has staged the qualification build `39f2e355…` (line 42630 only) with both registries.
- The installation is still the published `ccbed9d7…`, and SFM is closed.
- Run 3's verdict, session and library files were only read; their identities are unchanged.

**Next, with the Owner's authorization:** `pre`, `install`, `check` and `seed`, then the Owner's steps, then
`library Q`, `collect-logs`, `restore`, `check` and `analyze`.

Stopped before installation. No Stage 2 work, promotion, signing, push, merge or release.
