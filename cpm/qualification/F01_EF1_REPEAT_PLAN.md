# F-01 EF-1 repeat (run 2) after R3 Amendment 01: plan (2026-11-11)

**Status:** plan only. Nothing is built, installed or run. Execution needs the Owner's separate authorization. The
kit changes below also need it, as a reviewed kit commit.

## 1. What carries over from run 1, and what stays separate

**Run 1 stays where it is** (`E:\SFM_U0B_Scratch\f01-ef1-full-body`, classified STOPPED in `evidence\EF1_STOPPED.json`).
- Its folder is only read, never written. Run 2 gets a new run folder, for example
  `E:\SFM_U0B_Scratch\f01-ef1-full-body-r2`.
- **It is restored:** the published CPM is installed, both registries are removed, all four inventories equal their
  baselines, and the Engineer character folder is gone from the library.

**The same fixtures:**

| Fixture | Run-1 pin |
|---|---|
| Source session `ef1_source.dmx` | `cc3d2745e67cfb0cea247fcd5c6828e4bbce3ca1525a4bce19d10808793a76fc` |
| Destination session `ef1_destination.dmx` | `de31257bd014373118c20e9eeac6c783db35a4197ddeb94e6e8ed50aeb22cc89` |
| Saved record `EF1 Body--a236dddc4e22.json` (run-1 `evidence\library_poses`) | `0e0390e0f982e0f84cf56893a9c679bad4652042209accff67014a5542e7f2be` |

Run 2 copies all three, verified by hash; the originals are only read. Step 0 (session preparation) is **not**
repeated, so the destination keeps its six SFM-drifted offsets. That is exactly the case the amendment admits, and
it is what makes the repeat meaningful.

## 2. Recommended scope: Process B only, on the run-1 pose

Run 1 already established Process A natively:
- the Save New of a version 3 Full body record (A1–A3, UI-A, and library A);
- the record's oracle matching the A2 observation within 2.4e-6°;
- Save writing nothing to the scene.

Reposing the source would create a different pose and repeat manual work that is not under test. Run 2 therefore
seeds the pinned run-1 record, as the S3 continuation did, and runs Process B unchanged.

Process B covers:
- restart and an independent destination, against a record saved in an earlier SFM process (A pid 20520);
- B1, and B2: the verified Abort, which run 1 never reached;
- B3, the Apply; B4–B5, Undo and Redo; B6, the no-op; B7–B8, the Clip Editor refusal; B9; B10, the final Undo;
- UI-B;
- R0–R4: restoration and compare.

**Alternative, if the Owner prefers:** a full Process A on a verified copy of the source session. This needs new
posing and a new record, and the 72-bone check still compares against whatever is saved.

## 3. Kit changes needed (a reviewed commit before execution)

- **`ef1.template.json` pins:**
  - candidate `f4de5b61…`, qualification `fd0844cf…` (one line, 42118);
  - the three fixture pins above;
  - registries, published CPM, S0 observer and expected header unchanged.
- **`ef1_tool`, a continuation mode modelled on `s3_tool`'s:**
  - **`pre`:** copies the two pinned sessions into the new `sessions` folder, verified. There are no starter files,
    and the comparator's EF1-D1/D2 handling is not needed.
  - **`inspect`:** pins those copies.
  - **`seed`:** after `install`, copies the pinned record into the new `Characters\engineer--6111c38a013f\Poses`
    folder, and the run-1 Process A observations (`S0-01…03`, their sidecars, UI-A, library A) into the new
    `observations` folder, all verified.
  - **`restore`:** unchanged.
- **`ef1_compare`:**
  - Accepts the seeded Process A evidence, with `process.restart_between_save_and_apply` against run 1's A pid.
  - Checks unchanged, including `apply.non_root_offsets_are_the_destinations_own` and
    `apply.body_matches_the_pose_in_the_model_frame` at 0.001. The offline replay of B1 gives 0.00086 there, which
    is within 0.001.
  - New check: the destination's six drifted offsets are still present at B1 and unchanged after the Apply, so the
    amended rule is exercised and nothing is imported.
- **Tests:** a synthetic continuation run, PASS and counterexamples, on Python 2.7.5 and 3.10.6.

## 4. Expected native outcomes (from the offline replay)

- **B2:** "The pose couldn't be applied. Nothing was changed." This is the verified Abort.
- **B3:** "Pose applied: EF1 Body."
  - It writes 144 skeletal channels: the six drifted non-root offsets keep the destination's values, and the body
    root takes the saved translation.
  - The placement (`rootTransform`) and the smile stay unchanged.
  - Composed result against the saved pose: within 0.001 units.
- **The rest:** as in the procedure.

If the native composed error at B3 exceeds 0.001 (offline 0.00086), CPM refuses with `proportions`, or P7 does not
verify. That is a STOP under the existing rules: tolerances are never widened.

## 5. Stop conditions and restrictions

These are unchanged from `real_sfm_qualification/f01_ef1_full_body/PROCEDURE.md`. In addition, run 2 stops if any
pinned fixture, record or run-1 file does not verify. There is no push, merge, production enablement or release.
