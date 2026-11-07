# F-01 Full-Body S3 — Native Qualification Plan

**Status: PREPARED, NOT EXECUTED.** Drafted 2026-11-06 alongside the final S1 Undo corrections. The executable kit is
now `real_sfm_qualification/f01_full_body_s3/`: the operator procedure `PROCEDURE.md`, the tool, observer wrapper and
comparator. Section 7 records how the kit refines this plan. Nothing has been installed, launched or run. Executing
any step requires the Owner's execution approval. The plan supersedes the outline in
`F01_FULL_BODY_S1_CHECKPOINT.md` section 6.

## 1. Candidate and scope

| Item | Identity |
|---|---|
| Branch commit | `9799c9e7d54e52c6fbcb8a96f2cdce716dadce63` (code), plus this docs commit |
| CPM (production source) | `e1dc727f661e20f896a340fa403392a8d6241dc5d131203cc941ed91c829b7be` |
| Body profile registry | `cpm/pose_profiles/cpm_body_profiles_v1.json` `22dcd159…` (full-body mapping experimental) |
| Left-arm registry | `f445d5ef…` (qualified Krystal left arm), unchanged |

**Scope:** Krystal (`krystal2020.mdl`), region `full_body`, SFM timeline Motion Editor (mode 2), one machine. Out of
scope: other rigs, the Clip and Graph Editors (refusal only), production promotion, packaging, release.

**Build:** the qualification CPM is the candidate with exactly one changed line,
`PROD_POSE_REGISTRY_MODE = u"qualification"` (as in NQ-1). Its SHA-256 is recorded before installation. The body
registry is installed byte-exact beside it. Afterwards the published CPM is restored and every protected inventory is
compared with its baseline (NQ-1 procedure).

## 2. Fixture preparation (Owner, ordinary SFM editing, before the run)

Both sessions are disposable copies of the S0 R2 fixture, each saved once by the Owner.

1. **Source `S3_SOURCE.dmx` (shot15):** two whole-body postures, A and B, at two frames, keyed by ordinary editing.
   - A and B differ from each other in every posed region: spine, hips, each arm, each leg, tail, neck and head,
     fingers and ears.
   - Rotations only on FK bones; no FK bone translation (A1).
   - The jaw is open in A and closed in B.
2. **Destination `S3_DESTINATION.dmx` (shot13):** a third posture, distinct from both A and B in every posed region.
   - `rig_root` is moved and turned, so the placement differs from the source.
   - At the Apply time (0.3750 s) no written channel has a key, so the first Apply exercises insertion.
   - Flexes, gaze and eye controls, bone scale, poles and twist keys carry non-default values, so their preservation
     is observable.

**Distinctness is checked before Apply.** On the pre-apply observations, the offline comparator must show that every
posed region differs from the record's oracle (and A from B) by at least 5°, or 0.5 units for translations. If any
region falls below that, STOP: the run would not show that Apply moved it.

## 3. Processes and steps

The S0 read-only observer records an observation (OBS) before and after each step: keys of every channel, the evaluated
skeleton (local and world), placement, flexes, scale, Undo state, and a digest of all channels outside the written set.
The CPM log is kept for every process.

### Process A: save (source session)

| Step | Action | Expected |
|---|---|---|
| A1 | Open `S3_SOURCE.dmx`, Motion Editor, frame of posture A. OBS. | Baseline. |
| A2 | Poses → Save New → `S3 Pose A`. OBS. | One version 2 record, region `full_body`. Scene unchanged: observer digest equal and no Undo entry. |
| A3 | Frame of posture B, then Save New → `S3 Pose B`. OBS. | As A2. |
| A4 | Exit SFM **without saving**. | Record SHA-256s noted from disk. |

### Process B: apply (new SFM process, destination session; source session never opened)

**Independent saved-pose reload:** both poses are discovered from disk in a new process. Before B2, the offline
comparator re-parses each record in a separate Python process (stage E validator) and checks:
- each record's SHA-256 equals the A4 value;
- each record's oracle equals the A-process observation of the source skeleton.

| Step | Action | Expected |
|---|---|---|
| B1 | Open `S3_DESTINATION.dmx`, Motion Editor, 0.3750 s. OBS (baseline). | Distinctness check passes. |
| B2 | Apply `S3 Pose A`. OBS after the automatic refresh. | **Insert**: one Undo entry `Apply Pose S3 Pose A`; P6 refresh; P7 `committed-verified`. Every posed bone within 0.01° and 0.001 units of the oracle in the destination placement. Exactly one key added per written channel at t; neighbouring keys unchanged. |
| B3 | Ctrl+Z, OBS; Ctrl+Y, OBS. Do not move the playhead between B2 and B3. | Undo: every key and the evaluated skeleton exactly as in B1. Redo: exactly as in B2. |
| B4 | Apply `S3 Pose B`. OBS. | **Existing-key update**: key times and counts unchanged, values changed; P7 `committed-verified`; skeleton within tolerance of B's oracle. |
| B5 | Apply `S3 Pose B` again. OBS. | **True no-op**: status "no-op", no Undo entry, no write; Undo still names `Apply Pose S3 Pose B`. |
| B6 | Script Editor: `import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"`. Then Apply `S3 Pose A`. OBS. | **Verified Abort**: "The pose couldn't be applied. Nothing was changed." Keys, skeleton and Undo history exactly as in B5; no lockout. If CPM reports that it couldn't confirm the scene, observe once, then STOP. |
| B7 | Navigate away and back to 0.3750 s. OBS. | Pose B is unchanged. |
| B8 | Ctrl+Z, OBS. | Pose A's exact keys and skeleton (B2 state). |
| B9 | Exit **without saving**. | |

**Preservation checks (B2, B4, B6, B7 against B1 or the previous state):**
- **Placement:** `rig_root` position and orientation, the model transform, and Krystal's world placement.
- **Facial:** every flex control value, jaw and `tongue00`–`07` local transforms, eyes and gaze.
- **Scale:** bone scales, including `bip_head` 1.13 and its effect on jaw and tongue, and the rig scale.
- **Preserved handles (A2):** `rig_root_p`/`_o`, `Elbow_l/r_o`, `Knee_l/r_o`.
- **Passive twist (A3):** `bip_lowerArm_l/r_twist2`.
- **Unrelated channels:** the digest of every channel outside the 278-channel written set is identical. This covers
  other animation sets, the camera and lights.

### Process C: refusals and legacy regression (new process)

| Step | Action | Expected |
|---|---|---|
| C1 | Destination copy, Clip Editor, Apply `S3 Pose A`. | Refused before writing; no Undo entry. |
| C2 | shot10 Krystal (FK positions differ), Apply `S3 Pose A`. | "This pose uses different bone positions and can't be applied safely."; nothing written. |
| C3 | **Legacy left arm:** shot15, Motion Editor, apply the qualified v1 Pose B (`87e61f60…`), then repeat, then Ctrl+Z and Ctrl+Y. | As stage D ME-1/ME-1b: verified automatically; true no-op; exact Undo and Redo; everything outside the left arm unchanged. |
| C4 | Exit without saving; restore the published CPM and the registry state. | Every protected inventory equals its baseline. |

## 4. Transaction runtime measurement

There is no code change for this: every CPM log record carries a millisecond UTC stamp and the operation number.
For B2, B4, B6 and C3 the comparator reports:
- operation start → `BODY-P1` (P1: discovery, classification, authority, planning);
- `BODY-P1` → `BODY-P6` (P2 revalidation, `StartUndo`, about 278 writes, P5 checks, `FinishUndo`);
- `BODY-P6` → `BODY-P7-verified` (deferred verification);
- the whole operation.

The observer also records the wall time of Ctrl+Z and Ctrl+Y in B3 and the Undo item count where SFM reports it.

Runtime is evidence, not a pass criterion. A duration over 10 s, or SFM visibly freezing, is a finding for the
Owner's decision.

## 5. Pass criteria and stop rules

**Pass:** every Expected cell holds, preservation is exact, and the comparator verdict is
`FULL BODY QUALIFICATION PASS`. The legacy regression matches stage D, and the restoration inventories equal baseline.

**Stop rules:**
- any unplanned write, crash, recovery lockout, unexpected Undo entry (including `Modify Head Time` above an Apply
  before an Undo step), or failed distinctness check: STOP;
- preserve all evidence;
- do not retry within the run;
- report to the Owner.

## 6. Work needed before execution (each needs authorization)

1. **Procedure** (`real_sfm_qualification/f01_full_body_s3/PROCEDURE.md`): this plan as numbered operator steps, in
   the NQ-1 style.
2. **Observer:** the S0 observer reused unchanged (read-only); a wrapper adds the channel digest and the timing excerpt.
3. **Offline comparator** on the S0 analyzer:
   - oracle tolerance;
   - distinctness;
   - preservation;
   - Undo and Redo exactness;
   - timing.

   It must be tested offline against the S0 fixtures.
4. The qualification CPM build and its installation/restoration manifest.
5. Owner preparation of the two fixture sessions (section 2).

Raw native evidence stays in the Owner's local archive; the repository receives the summary record and the hashes.

## 7. Kit and refinements (2026-11-06, Owner authorization "Finish Recovery Safety and Prepare Native Qualification")

The kit in `real_sfm_qualification/f01_full_body_s3/` implements this plan, refined towards the artist workflow:

- **Candidate:** CPM `813a9ff2…` (after the recovery-pause correction `af45dfa`); qualification build `45cbaf95…`.
- **Posing:** the Owner poses Krystal in SFM during Process A, rather than preparing the postures beforehand. Posture
  A is saved as `S3 Pose A`, B as `S3 Pose B`, and a third posture C updates `S3 Pose B` in place (Update Pose).
  Applying the updated B over A therefore exercises the existing-key update.
- **Destination:** shot13 of the R2 fixture, posed by the Owner once (step 0), compatible under A1 (rotations only on
  FK bones). `rig_root` is moved and turned; the face, jaw and gaze are set distinctly.
- **Processes:** two SFM processes. The refusals (Clip Editor, shot10 FK positions) and the legacy left-arm
  regression run in Process B after the full-body steps.
- **Legacy pose:** `NQ1 Pose A` (`4916a724…`), seeded by hash, because the R2 shot15 arm already matches Pose B
  (PS-1b5).
- **Observer:** the S0 observer `4a358cc0…`, unchanged, through a read-only wrapper. The wrapper adds a digest of
  every channel outside the instance and an immediate editor, shot and playhead check.
- **Comparator:**
  - independent of CPM's code;
  - uses the registry tolerances;
  - checks: distinctness (≥ 5° per anatomical group), full-body reproduction relative to `rig_root`, preservation,
    Undo/Redo, the no-op, the update in place, the Abort, the refusals, CPM's own P6/P7 log verdicts and
    restoration;
  - measures timing from the CPM log's millisecond stamps. Responsive is ≤ 5 s; a finding is up to 30 s; a fail is
    above that.
- **Offline tests** (`tests/test_s3.py`):
  - the wrapper against the S0 fake (read-only, sidecar, repeated step refused, mismatch reported), on Python 2.7.5
    and 3.10.6;
  - the build derivation;
  - a complete synthetic run (PASS) and 13 counterexamples (each FAIL), on 3.10.6.
## 8. Run 1 result and the Process B retest (2026-11-07)

**Run 1:** Process A passed. Process B stopped after B1, on the A1 pre-check: four FK positions differed by float32
noise from SFM's rotate tool. Nothing was applied, and the installation was restored. The record is in
`F01_FULL_BODY_S1_CHECKPOINT.md` section 10.

**Run 2** (`PROCEDURE_B_RETEST.md`) uses the revised-A1 candidate `aca2bb06…` (qualification `32486723…`) and starts
at Process B in a new run folder. Run 1's destination, records (including the Update Pose `.bak`) and Process A
observations are reused read-only, pinned by hash in `s3_continuation.template.json`.

Kit changes:
- **Continuation mode:** `pre`, `inspect` and `seed` reuse run 1's pinned files.
- **`s3_tool precheck`:** after B1, the staged qualification CPM's own revised A1 check runs on the B1 observation
  and `S3 Pose A`, through `s3_precheck.py` (read-only). Apply is allowed only on `COMPATIBLE`.
- **Comparator:**
  - Process A is checked against run 1's build;
  - a compatible pre-check is required;
  - the library check now covers the `.bak`, which must be the replaced record.
- **B12:** the expected refusal is the proportions copy.
- **Performance:** anything above 5 s is reported as a usability finding.
- **Tests:** 29 kit tests on 3.10.6, including the continuation lifecycle on a temporary installation (the source run
  is unchanged and restore returns every inventory); the wrapper tests pass on 2.7.5.
## 9. Run 2 result and run 3 (2026-11-07)

**Run 2** passed B1 and the revised A1 pre-check natively, then stopped at B2: the Poses page never enabled Apply
Pose for a full-body pose. Fixed in `c2a2068`; recorded in `F01_FULL_BODY_S1_CHECKPOINT.md` section 11.

**Run 3** reuses the same run 1 files and steps (`PROCEDURE_B_RETEST.md`), with:
- the candidate `9a155bff…` and qualification build `814b6ec5…`;
- a new UI smoke check (B1b, read-only): Apply Pose must be enabled for the selected `S3 Pose A` before the first
  Apply. The comparator requires it.

Kit tests: 33 on 3.10.6 (including the UI smoke check against a fake window, the comparator's smoke requirement and
the continuation lifecycle); the wrapper and smoke tests pass on 2.7.5.
