# F-01 Full-Body S3 — Consolidated Native Qualification Assessment

**Date:** 2026-11-07. **Scope:** Krystal (`krystal2020.mdl`), full-body poses (version 2), the legacy left-arm path
(version 1), SFM Motion Editor, one machine.

**Result:** every S3 requirement has been established natively, each by a valid run on the build named below. No
run's own verdict has been revised. Run 3's comparator verdict stays **FAIL** (procedural). Its full-body results
(B1–B11) rest on the comparator's own check functions applied to its valid observations, and its incomplete steps
were repeated in runs 4 and 5.

## Builds

| Runs | Candidate CPM | Qualification build | Difference |
|---|---|---|---|
| 1 | `813a9ff2…` (`459885a`) | `45cbaf95…` | — (Process A only) |
| 2 | `aca2bb06…` (`661cfd7`, revised A1) | `32486723…` | stopped at B2 (Apply button) |
| 3 | `9a155bff…` (`c2a2068`, Apply button fix) | `814b6ec5…` | — |
| 4, 5 | `f6098b3a…` (`e98b90b`) | `12b59b29…` | Against run 3's candidate, Apply checks the timeline editor first and uses the reworded editor-mode copy (+14/−1 lines). In the Motion Editor the transaction path is unchanged. |

The registries are unchanged throughout: pose `f445d5ef…` and body `22dcd159…` (full-body mapping experimental). Each
run restored the published CPM `ccbed9d7…`, and every protected inventory equalled its baseline.

## Results by run

| Requirement | Established by | Evidence |
|---|---|---|
| Save New of a complete pose, Update Pose in place (with the `.bak` of the replaced record), no scene writes | Run 1 Process A | `f01-full-body-s3\observations` A1–A7 and `evidence\library_poses`; the offline check is recorded in `F01_FULL_BODY_S1_CHECKPOINT.md` section 10 |
| Restart and independent reload | Runs 2, 3 (new SFM processes, source session never opened) | the B observations' process ids; the libraries are unchanged A→B |
| Revised A1 (four native FK discrepancies kept at destination values) | Runs 2 and 3 pre-checks | `A1_PRECHECK.json` (COMPATIBLE) |
| Apply Pose enabled for a full-body pose | Run 3 B1b | `f01-full-body-s3-r3\observations\UI-SMOKE.json` |
| Full-body Apply: 278 keys, the posture reproduced (worst 0.00012 units, 0.0003°), placement, face, gaze, jaw, scale and unrelated animation preserved; one owned Undo; P7 verified | Run 3 B2 | `f01-full-body-s3-r3\evidence\INTERIM_CHECK_b2.json` |
| Exact Undo and Redo, true no-op, update of existing keys (posture C), verified Abort, persistence after navigation | Run 3 B3–B8 | `INTERIM_CHECK_b3_b8.json` |
| Clip Editor refusal with "Switch to the Motion Editor to apply a pose. Nothing was changed.", no writes | Run 4 B9–B10 | `f01-full-body-s3-r4\evidence\S3_SCOPED_B9_B12.json` (PASS, 15 checks) |
| Incompatible proportions refusal (shot10), no writes | Run 4 B11–B12 (also run 3, unobserved) | same |
| Legacy left arm: visible transfer onto a different arm (up to 79°), bones equal to the source arm within 0.01°, everything else unchanged, true no-op, Undo with Redo, Redo; P7 verified | Run 5 B11, B13–B17 | `f01-full-body-s3-r5\evidence\S3_VERDICT.md` (**PASS**) |

**Additional native evidence (log only, not observed):** run 4 recorded a third verified full-body Apply onto another
instance (shot15): 278 insertions, owned, P7 verified, about 2.4 s.

## Deviations (preserved, never used as evidence)
- **Run 2:** B1 was first observed in the Clip Editor; the attempt is voided.
- **Run 3:** B12 was not observed; B13–B17 ran on shot10; B17 was impossible after scrubbing.
- **Run 4:** B9 was first observed in the Motion Editor; the attempt is voided. After B13, S3 Pose A was applied by
  mistake, so B13–B17 there are invalid.

Each is recorded in that run's `evidence\DEVIATIONS.json`.

## Performance (CPM log, millisecond stamps)

| Operation | SFM busy | Settled |
|---|---|---|
| Full-body Apply (insert / update) | 2.63 s / 2.64 s | 3.73 s / 3.50 s |
| Full-body no-op | 1.35 s | — |
| Fault and Abort | — | 3.41 s |
| Legacy left-arm Apply | 2.66 s | 3.09 s |

Every operation is under the 5 s threshold. There was no freezing.

## Functional, safety and usability findings
- **Functional:** no open defect. Three defects were found natively and fixed: the bit-exact A1 rule (revised A1),
  the disabled Apply button (`c2a2068`), and the generic Clip Editor message (`e98b90b`).
- **Safety:**
  - no unplanned write;
  - no recovery pause or uncertainty in any run;
  - every Abort verified;
  - restoration complete in every run.
- **Usability:**
  1. About 3 s per full-body Apply.
  2. A pose reproduces the body's offset relative to `rig_root`, for example the hip height. Run 3 B6 looked like a
     translation for that reason. Keeping the destination's hip height could be offered later.
  3. Refusals show a popup that can look like an error, even when the refusal is expected protection.
  4. Partial application of a full-body pose (for example the hands) is a valued future option; it is not built.

## Readiness for CPM v1.1.0 release preparation

The Pose Library is functionally ready for release preparation. These are the remaining release-preparation steps,
not qualification gaps:
1. promote the Krystal full-body mapping to `qualified` in the body registry. This changes its hash and therefore the
   CPM pin, so a final candidate follows;
2. include the body registry in the packaging;
3. run one production-build smoke test of Save and Apply with the final candidate;
4. decide on the usability items above.

Production qualification is not declared by this document.
