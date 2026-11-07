# F-01 Full-Body S3 — Native Qualification Plan (DRAFT)

**Status: DRAFT, NOT AUTHORIZED, NOT EXECUTED.** Prepared 2026-11-06 at the Owner's request alongside the final S1 Undo
corrections. Nothing in this plan has been installed, launched or run. Executing any step requires separate Owner
authorization. The plan supersedes the outline in `F01_FULL_BODY_S1_CHECKPOINT.md` section 6.

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
