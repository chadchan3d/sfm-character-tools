# F-01 Stage 1: run 1 corrections and the run 2 native procedure (2026-11-19)

**Authority:**
- "F-01 Stage 1 — Native Findings Disposition" (Designer: C1, C3, C4, C5 and C6 approved; C2 revised);
- the C2 clarification on facial controls.

Findings: `F01_STAGE1_FOX_NATIVE_FINDINGS.md`.

**Status: implemented and tested offline; run 2 prepared, not run.**
- Nothing is installed.
- Run 1 (`f01-stage1-fox-r1`) and its INCOMPLETE verdict (`S1F_VERDICT.json` `f3dda3c2…`) are preserved unchanged.

## 1. Code identities

| Item | Value |
|---|---|
| CPM | Stage 1 `35c400c1…` → **`1753bdbaeb1544aa98679c89b9c4cc65b51861c40fb0975d9d5f315ca8f43baa`** (1,512,330 B). Exact diff: `F01_STAGE1_RUN2_CORRECTIONS.diff` (against `422c1e7`) |
| Qualification build | `e3e863ee43e25f66f0161151f9e37f4830842b3f80a41da0475caf82b2677b0c` (line 42609 only) |
| Kit | capture `fbd7681c…`, analyzer `53aa8313…`, procedure `e125a6ec…` (pinned in `s1f.template.json`) |

## 2. The corrections

**C1: Apply availability.**
- `prod_body_rig_availability(record, identity, mode)` returns `available` only when all three hold: the record is a
  structural rig record, its adapter rule and revision are usable in this build, and its model is the selected
  model. Otherwise it returns `not-qualified` or `different-model`.
- The Poses page state and the Pose Info note use it for structural records, as `prod_scope_availability` is used for
  v3. Both calls are guarded by `version == 2`.
- An enabled button authorizes nothing. Apply still resolves the destination itself, drafts its description,
  compares it exactly (a different rig refuses with `rig-differs`), and then runs P2 to P7, Abort and recovery,
  all unchanged.

**C2: facial controls (as clarified).**
- A Full body whose face-group bones are all supported (directly animated: a jaw, a tongue) saves them with the
  body. There is **no review box**, and the summary is the plain "Facial expressions and the rootTransform are not
  saved."
  - This applies to the generic route.
  - It also applies to the structural route, where every bone of a drafted description is classified confidently
    and the inventory's review list is now empty.
- A choice appears only for face-group controls CPM **cannot** capture (a `review-required` body), and only those
  are left unchanged. The wording is positive:
  - box: "Face controls";
  - note: "The body pose is saved. These face controls can't be included, so they stay as they are.";
  - choice: "Save the body and leave these face controls as they are";
  - summary before the choice: "Some face controls can't be saved with this pose. Choose to save the body and leave
    them as they are.";
  - summary after it: "The body pose is saved and the listed face controls stay as they are. Facial expressions and
    the rootTransform are not saved."
- The exclusion record format and reason are unchanged (`user_confirmed`).
- Facial expressions (flex controls) stay excluded.
- There is no character-specific rule.
- Krystal's qualified registry profile keeps her jaw and tongue preserved, as qualified. It was not replaced.

**C3: refusal wording.**
- `PROD_SCOPE_FULL_BODY_UNSUPPORTED` = "Full body poses aren't supported for this character yet. You can still save
  Selected parts." It is now the user copy of the three "unsupported Full body capability" codes: `rig-driven`,
  `unsupported-body` and `carried-unsupported`.
- Codes and exact causes (bones) stay in the diagnostic log (`SCOPE-refused`).
- Context, stale, invalid-record, Motion Editor, compatibility and failed-operation messages are unchanged.

**C4: tests on the real UI paths.**
- Poses-page suite section S (real PySide window, 8 checks):
  - A structural Full body record of the same model enables Apply Pose in the qualification build and shows
    "Available: Full body".
  - Pose Info has no "Can't be applied" note.
  - The click reaches the structural authorization and the version 2 transaction.
  - Another model, an unknown adapter revision, a recovery pause and the production build keep Apply disabled, and
    Pose Info says so.
  - **Teeth:** against the run 1 CPM, S1 and S2 fail (127/131), reproducing the native defect.
- The Stage 1 suite adds availability unit checks, C2 and C3 checks, and confirms that the generic v3 review data are
  unchanged.
- The scoped-page dialog suite covers: no box for a supported jaw; the positive choice for a review-required body;
  and Save waiting for that choice.

**C5: native fixture.**
- Two fresh Foxes, both rigged with the installed stock `rig_biped_simple`: Fox S (the source, posed, jaw included)
  and Fox D (the destination, posed and placed differently).
- The session's original Fox (`foxmccouldwm1`, the older 22-handle rig) is the untouched peer.
- The strict structural rule is kept. Cross-version rig compatibility (22-handle and 23-handle rigs) is recorded as a
  **future limitation**.

**C6: kit.**
- The reopen comparison allows **only** SFM's measured reload rounding. Channels, bindings, logs and key times must
  be identical, every value exact, except that quaternion key components may differ by at most one float32 step
  (2^-23, run 1's measured maximum).
- Missing captures make gates **NOT EVALUATED**, never PASS.
- Tails' refusal is judged from the CPM log.
- The capture records keys and a handle-free frame digest for all three sets.
- Authored-data, Undo, Abort, peer and restoration checks within Process B stay exact.
- Run 1's evidence analyzed in memory by the corrected analyzer gives INCOMPLETE: EVIDENCE FAIL and every other gate
  NOT EVALUATED. Nothing was written to run 1.

## 3. Offline results

| Suite | Result |
|---|---|
| Stage 1 `test_cpm_app_f01_structural_rig` | **151/151** on 2.7.5 and 3.10.6 |
| Poses page `test_cpm_app_f01_pose_page` (real window, 2.7.5) | **131/131** (8 new: C1/C4) |
| Save dialog `test_cpm_app_f01_scoped_page` (real dialog, 2.7.5) | **19/19** (C2 dialog checks updated, 1 new) |
| Generic v3 `test_cpm_app_f01_scoped` | 487/487 on both (C2/C3 expectations updated: the jaw saved without review; positive review wording; the Owner's refusal wording, with the cause asserted in the log) |
| Kit `tests/test_s1f.py` | **38/38** on 2.7.5 and 3.10.6: the simulated run 2 gives AUTOMATED PASS; one-step reload rounding on the peer or the destination is accepted; two steps or a changed key time give INCOMPLETE (PREP); missing captures give NOT EVALUATED; Tails not refused gives FAIL; and the earlier breaks behave as before |
| Full regression (`run_regressions_v110`, 59 runs) | identical to the Stage 1 baseline apart from the added checks (Poses page 123 → 131, Save dialog 18 → 19). Stage E body 261/261, helper 78/78 and the other suites unchanged; the pre-existing historical failures are unchanged |

## 4. Run 2

**Procedure:** `real_sfm_qualification/f01_stage1_fox/PROCEDURE.md`, in a new run folder
`E:\SFM_U0B_Scratch\f01-stage1-fox-r2`, where `build` has staged the qualification build. There are two SFM sessions
and 10 captures.

**Next:** with the Owner's authorization, run `pre`, `install` and `check`, then Process A and Process B.

**Stopped before installation and native execution for the Owner's authorization.** No production promotion,
signing, push, merge or release.
