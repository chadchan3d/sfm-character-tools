# F-01 Stage 1: numerical compatibility of static constraint rotations (2026-11-19)

**Authority:**
- Astra's numerical compatibility ruling on the run 2 findings: **ACCEPT WITH CONDITIONS**;
- "F-01 Stage 1 — Implement Astra's Numerical Compatibility Ruling" (starting checkpoint `94f21df`).

Findings: `F01_STAGE1_FOX_RUN2_FINDINGS.md`.

**Status:** implemented and tested offline; run 3 prepared, not run. Nothing installed.
- Runs 1 and 2 and their INCOMPLETE verdicts are preserved unchanged: run 1 `f3dda3c2…`, run 2 `0190a57c…`.

## 1. Identities

| Item | Value |
|---|---|
| CPM | `1753bdba…` → **`2088b4aff1a6cfe05242bd1e774ac1fd4a565a92e5c124336b1aa855b62b8df7`** (1,519,905 B; 139 lines added, 4 removed). Exact diff: `F01_STAGE1_NUMERICAL_COMPATIBILITY.diff` (`33d054fe…`, against `94f21df`) |
| Qualification build | **`b195515f31ceb54fd306619f43aa91ad1f1e25977185ec9e79323bf6e1b0f468`** (line 42609 only, the registry mode; the same derivation reproduces run 2's `e3e863ee…` from `1753bdba…`) |
| Kit | capture `765eefc2…`, analyzer `a8623246…`, procedure `ad619f88…` (run 3), pinned in `s1f.template.json` |

## 2. The comparison contract (CPM)

**Where it applies.** The new rules apply only in `prod_body_compare_descriptor`, P1's comparison of the **saved record**
against the **live rig**.
- Nothing else changes: P2 and Abort (`prod_body_same_state`) still compare the live state exactly against P1's
  independently captured live baseline. P7 still verifies reproduction, placement and protected animation
  independently. Authored keys keep their exact checks.

**Rotation equivalence** (`prod_body_compare_constraints`, `prod_body_rotation_compare`, `prod_body_rotation_angle`):
- **Fields:** only the three static constraint fields `solver.startOffset`, `solver.midOffset` and `offsets.oOffset`
  (`PROD_BODY_ROTATION_FIELDS`).
- **Validity, on both sides:**
  - matching presence and the `{present[, value]}` representation, with no extra members;
  - four finite numbers (not booleans);
  - `abs(norm(q) - 1) <= 2^-19` (`PROD_BODY_ROTATION_NORM_LIMIT`).

  Zero, malformed, rescaled and otherwise non-unit values refuse.
- **Comparison:**
  - temporary double-precision normalized copies;
  - signs aligned, so q and -q are one rotation;
  - `angle = degrees(4 atan2(|a - b|, |a + b|))`;
  - admitted when the angle is ≤ **0.0005°** (`PROD_BODY_ROTATION_LIMIT_DEG`, inclusive).
- **No accumulation:**
  - The saved record's values are never modified or replaced.
  - Each comparison is against the original saved value, so repeated reloads that stay within the bound pass, and a
    cumulative departure beyond it refuses.

**Structural matching:**
- **Identity:** constraints are matched by `(type, slaves, targets, pole)`. The JSON encoding is deterministic, keeps
  the named slave slots and keeps the target order.
- **Refusals:** each side must have exactly one row per identity, and the identity sets must be equal.
  - Duplicates refuse before any numerical comparison.
  - Missing, extra or structurally changed constraints refuse (`rig-differs`).
- **Never used for pairing:** list order, value order or the closest values. The descriptor's value-dependent sort no
  longer decides pairing.
- **Records:** unchanged. The descriptor and its order are as written.

**Everything else stays exact:**
- names, types, endpoints, poles, modes, `poleVector` and `vecOffset`;
- bones, handles, channels and roles;
- scale, with the `proportions` reason;
- structural positions and orientations, with their existing reasons;
- the rest of the descriptor.

**Diagnostics:**
- **A refusal** logs every rotation problem with:
  - the constraint identity and field;
  - the raw saved and live values and their norms;
  - the angle, the limit, the norm limit and the problem.
- **Other descriptor refusals** give the total number of differences.
- **An admitted difference** logs `BODY-rotation-equivalent`: the count, the maximum angle and the limit.

## 3. The qualification kit

**Reopen check:**
- It compares the actual save/reopen transition, **SAVED → BASE** (the last Process A capture against the first
  after the restart). `save.read_only` keeps SAVED equal to PREP exactly.
- Every quaternion key must equal SFM's measured float32 load renormalization (`sfm_reload`) of its saved value,
  exactly. This replaces the one-step allowance.
- Key counts, times, frames and every non-quaternion value stay exact.
- It is a fixture-specific loader check, separate from CPM's rule: a sign-flipped key is the same rotation but **not**
  the loader's transformation, and it fails.

**Capture:**
- It now records, for information only, a digest of the compatibility descriptor and the three rotation offsets of
  every constraint.
- The analyzer reports the digests and never uses them as a gate.

**Run 2's real data** (`tests/run2_reload_keys.json` `7d2fea51…`, copied read-only from run 2's SAVED and BASE):
- all **618** quaternion keys equal the function, and 165 of them changed;
- the analyzer accepts that reopen;
- one altered quaternion or vector key is rejected;
- an unrenormalized reopen is rejected.

**Found while doing this (procedural, run 2):**
- After the PREP capture, posing continued in run 2's Process A: Fox S's hands, left foot, spine, neck and pelvis
  handles, and Fox D's left hand.
- So PREP ≠ SAVED, and run 2's SAVE gate (`save.read_only`) would have failed even without the refusal.
- The procedure now says to finish all posing before PREP.

## 4. Offline results

| Suite | Result |
|---|---|
| Stage 1 `test_cpm_app_f01_structural_rig` | **243/243** on 2.7.5 and 3.10.6 (151 before; section N adds 92) |
| Stage E body `test_cpm_app_f01_body` (Krystal registry route) | 261/261 on both, unchanged |
| Kit `tests/test_s1f.py` | **49/49** on 2.7.5 and 3.10.6 (38 before) |
| Full regression (`run_regressions_v110`, 98 result lines) | **identical** to the run 2 corrections baseline; the pre-existing historical failures are unchanged |

**Section N** (Astra's minimum cases):

**1. Replay of run 2:**
- The pinned record (`fixtures/f01_body/fox_run2_s1_fox_record.json`, `da8ca528…`) is reloaded by the measured
  function.
- **Exactly the five offsets change.**
- **Teeth:** the run 2 build (`1753bdba…`, from Git) refuses `rig-differs` with exactly the 16 paths of the native
  log.
- The corrected comparison admits all five, at angles below 1e-4°.
- The saved record is unchanged.

**2. Repeated loads:**
- 2, 3 and 6 reloads are admitted against the record.
- A real float32 two-cycle, over 1 to 6 loads, is admitted against the original value.
- One 0.0003° drift step is admitted. A second step (0.0006° from the record) refuses.

**3. Signs:** sign-equivalent offsets are admitted, including reloaded ones.

**4. The angular bound:**
- The formula matches the reference angle and is stable near 0.
- At 40° and at 179.9999° (where the w ≥ 0 representative changes sign), 0.0004999° is admitted and 0.0005001°
  refused.
- The bound is inclusive: the computed angle passes exactly at the limit and refuses just below it.
- Changes of 0.01°, 3° and 90° refuse.

**5. Validity:** each of the following refuses on either side:
- zero, NaN, infinite, boolean or text components;
- 3 or 5 components, or a scalar;
- the same rotation rescaled to a norm of 1.001;
- a norm beyond the envelope (±2^-18).

Also:
- a norm within the envelope (2^-21) is admitted;
- present against absent, a missing field, a malformed field and an extra member refuse;
- both absent is admitted;
- the refusal diagnostic carries the identity, field, raw values, norms, angle (2°) and limit.

**6. Structure:**
- Reversed and shuffled enumeration is admitted.
- **Value-dependent reordering:** the reorder is reproduced; the run 2 build refuses it (teeth); identity matching
  admits it.
- These refuse:
  - duplicates on either side, before any numerical check;
  - missing or extra constraints;
  - a changed target, pole, type or slave;
  - swapped named slave slots;
  - swapped target order;
  - a changed `poleVector`, `mode` or `vecOffset`;
  - a changed rig name or model.

**7. Live rigs** (fake scenes from the Fox fixture, which holds reload-unstable offsets):
- **Teeth:** the run 2 build refuses a reloaded destination and changes nothing.
- The corrected build applies to a destination reloaded once or three times and verifies at P7, keeping its own
  placement.
- Sign-flipped destination offsets apply and verify.
- **P2:**
  - a one-float32-step change and a sign flip of a live offset after P1 are both **stale**;
  - nothing is written.
- **Abort** restores the exact live baseline, keys and offsets: the destination's own values, not the saved ones.
- **P7:** a compatible rig with a wrong evaluated skeleton is **committed-unverified**.
- **Authored quaternion keys:**
  - preserved keys keep their exact signs;
  - the written key is the saved value in the destination's hemisphere, the existing qualified planner rule
    `prod_pose_hemisphere`, unchanged.

## 5. Full regression

All 59 runs give exactly the same results as the run 2 corrections baseline (Stage E body 261/261, helper, pose, scoped, page, M-05, M-06 and isolation suites unchanged; the pre-existing historical failures unchanged).

## 6. Native readiness (run 3)

**Prepared.** The same procedure (`PROCEDURE.md`, now run 3), re-pinned to `2088b4af…` / `b195515f…`, in a new folder
`E:\SFM_U0B_Scratch\f01-stage1-fox-r3`, where `build` has staged the qualification build (the installation is still the
published `ccbed9d7…`), with two fresh stock-rigged Foxes. The only operator change is to finish all
posing before PREP.

**Next, with the Owner's authorization:** `pre`, `install` and `check`, then Processes A and B, then the
collection, restoration and analysis.

**Stopped before installation and native execution.** No Stage 2, production promotion, signing, push, merge or
release.
