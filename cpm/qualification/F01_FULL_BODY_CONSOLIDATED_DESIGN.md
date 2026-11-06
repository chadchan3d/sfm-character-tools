# F-01 Full-Body Architecture — Consolidated Design

**Revision 1, 2026-11-05.** Branch `feature/f01-pose-library`, based on `8634e2c`.
**Status:** the Owner accepted this architecture on 2026-11-05 ("F-01 — Consolidate Architecture and Prepare S0
Native Survey"). **Full-body implementation is not authorized.** The next step is the read-only S0 survey
(section 9), which needs the Owner's execution authorization.

This document **supersedes** `cpm/qualification/F01_FULL_BODY_DESIGN_PROPOSAL.md` (SHA-256 `b6e37e7d…`). That
proposal is kept unchanged as the historical record. Nothing here modifies the frozen R15 Blueprint
(`cpm/qualification/R15_IMPLEMENTATION_BLUEPRINT.md`), the Stage D design or any recorded decision. The qualified
left-arm Pose Library (Stage D, CC-1, registry `f445d5ef…`) is unchanged.

## 1. Sources and their limits

| # | Source | Where |
|---|---|---|
| 1 | R15 Blueprint, Convergence Ledger, F-01 design history | GitHub `chadchan3d/sfm-character-tools` (`master` `efe8984`, F-01 branch `02e0085`); local Ledger and Stage C/D records on this branch |
| 2 | The original full-body proposal | `cpm/qualification/F01_FULL_BODY_DESIGN_PROPOSAL.md` (unchanged) |
| 3 | Astra's full-body architectural adjudication | external review record, **not in this repository or on GitHub** |
| 4 | Argon's independent adversarial audit | external review record, **not in this repository or on GitHub** |
| 5 | Stage D and CC-1 native qualification evidence | `F01_STAGE_D_NATIVE_QUALIFICATION_EVIDENCE.md`, `F01_CC1_OWNER_ACCEPTANCE_RECORD.md`; PS-1b5 observations (Owner's local archive) |

The review texts (3, 4) are not reproduced and were not available while this was written. This document records
their content **only as the Owner's authorization states it**. It names Astra or Argon only where that authorization
attributes a point; elsewhere it says "the accepted architecture". The F-01 M1 Addendum R2/R2.1 and
`09_FIRST_CODING_ASSIGNMENT.md` are not on GitHub either; this document does not reconstruct them.

## 2. What a full-body pose is

A pose is the **complete skeletal posture** of one character, relative to its placement frame. It is captured from
the pinned instance at the mapped tick, in the Motion Editor. On Apply it is reproduced on a compatible destination
at that destination's mapped tick, in one Undo transaction. The pose is never partial. Save and Apply refuse,
changing nothing, whenever a complete pose cannot be captured or written.

## 3. A — Hybrid discovery and validated profiles

1. **Validated rig-core definition.** The profile (first `body_krystal_v1`) explicitly lists the rig core:
   - the placement handle;
   - the pelvis, spine, neck, head and collar handles;
   - the arm and leg IK targets and poles;
   - the constraint topology: operator types, slaves, targets and pole targets, with the qualified target weights;
   - the rig registration.

   Every element must be present, unique and bound as listed, or the operation refuses. The final core list is fixed
   from the S0 evidence.
2. **Discovery.** Save and Apply enumerate the pinned instance's actual structure, using the existing M-06
   instance resolution and channels-clip membership:
   - every model bone and its parent;
   - every rig handle and its parent;
   - every control, and every channel of the instance's clip;
   - every operator of the animation set and the shot;
   - a document-wide index of every channel destination and every constraint slave.
3. **Structural classification.** Each discovered bone and transform control is put in exactly one class. The class
   comes from **binding evidence**: which channel writes which transform, from which source element, and which
   operator slaves which DAG.

   | Class | Evidence | Treatment |
   |---|---|---|
   | core handle | listed in the profile and bound as listed | written (pose input) |
   | direct FK | written only by control channels of the instance; no constraint, no operator output | written: orientation, plus position when position is a pose input (E) |
   | constrained | slaved by a rig constraint | not written; its posture is verified; its own channels are **dormant** (D) |
   | operator-driven | written by an operator output, for example an expression | not written; verified |
   | no writer | no channel and no constraint | structurally fixed; verified unchanged relative to its parent |
   | preserved by profile | in the profile's explicit preservation set (section 4) and structurally confirmed | not written; keys must stay identical |
   | unsupported | unknown operator type, competing writers, unreadable, ambiguous or unclassified | **refuse** the whole operation |

   Writable channels are **never inferred from names**. Names appear only in the profile's explicit core and
   preservation lists, and every name-listed element is still checked structurally.
4. **Coverage verification.** Before any save or write, every discovered bone and transform control must be
   accounted for. Nothing may silently disappear from a supposedly complete pose:
   - an unsupported element refuses the operation;
   - a discovered element missing from the record refuses Apply.
5. **Compatibility descriptor.** Saved with the pose, it identifies the exact captured structure:
   - rig class, model and rig registration name;
   - every bone with its parent;
   - every rig handle with its parent;
   - the constraint topology and weights;
   - each element's class;
   - the structural offsets of orientation-only bones;
   - the scale state;
   - the written channel set.

   Secondary bone names are recorded per pose, as discovered. They are **not** hardcoded as a universal requirement
   of the profile.
6. **Scope.** The first qualified implementation is Krystal-specific (`krystal-v1` → `krystal-v1`). Any other rig
   class needs its own validated profile and qualification.

## 4. B — Complete skeletal body posture

New Save creates a complete skeletal body pose by default. It includes every independently poseable body element
that is technically supported:
- torso, neck and head;
- arms, legs, hands, fingers, carpals, feet and toes;
- tails, wings, ears, hair and other skeletal appendages;
- additional independently poseable bones, including secondary anatomy (on Krystal: breasts, butt, genitals, anus,
  cosmetic).

It always preserves:

| Preserved | Mechanism |
|---|---|
| Global placement and facing | the placement handle (`rig_root`) and `rootTransform` are never written; P7 checks their world transforms |
| Body proportions and scale | bone `scale` attributes and scale channels (M-05) and Body Preset flexes are never written; a scale-state difference between record and destination refuses (F) |
| Facial flexes | no flex channel is written |
| Jaw and tongue expression controls | in the preservation set: `jaw`, `tongue00`–`tongue07` |
| Eye gaze | `viewTarget`, `eye_convergence`, `localViewTargetFactor` and their channels preserved |
| Rig configuration | constraint weights, IK solver settings, rig registration; required at their qualified values, never written |
| Unrelated animation | every channel not in the write plan keeps byte-identical keys (instance-wide baseline, D) |

On Krystal the authorization decides two things that differ from the original proposal: the ears are included as
skeletal appendages (the proposal had excluded them as facial controls), and the tail, hair and secondary anatomy are
included (the proposal had excluded them, D1). Each is still included **only if** S0 classifies it as independently
poseable. An element that turns out to be unsupported makes full-body Save refuse; it is never dropped.

Known evidence: in M-06's native qualification, `bip_lowerArm_r_twist2` and `bip_lowerArm_l_twist2` (bones 150 and
155) had no transform control. Their class is an S0 question (S0-Q7).

## 5. C — Coordinate representation

The design keeps three quantities apart:

1. **Placement-frame-relative skeletal posture (P):** each bone's orientation and position relative to the
   character's placement frame (`rig_root` / `rootTransform`). This is what the pose means, and what P7 verifies on
   the whole skeleton.
2. **Each written controller's actual parent-local value (L):** the channel value, expressed in that controller's
   actual parent space (another handle, a bone or `rig_root`). This is what is keyed.
3. **The planned destination parent transforms (D):** the parents' transforms as they *will be* after the
   transaction. Parents written in the same transaction use their planned values; unwritten parents use the
   destination's actual values.

The plan computes each controller's L from P and D. A parent-local value is copied from the record only when the plan
shows it reproduces P:
- the descriptors match;
- the parent chain matches;
- the structural offsets agree (E).

**Copying parent-local transforms is never assumed to reproduce the intended posture.** P7 verifies P, not only the
written keys.

The **qualified legacy left-arm mapping is preserved unchanged:**
- collar-relative hand goal and elbow pole;
- re-expressed through the destination's collar;
- the shoulder guard.

Version 1 left-arm records always use it.

## 6. D — Combined application transaction

One full-body Apply, using the existing Stage D pipeline generalized from 3 channels to the plan:

1. **One instance-wide baseline:** the existing authored capture of every channel of the instance's clip, every
   control and every operator relationship, plus the observed constraint attributes and the evaluated skeleton.
2. **One deduplicated write plan:**
   - each channel at most once, with one value at the mapped tick;
   - an insert or update decided per channel;
   - two plan entries for one channel, or a planned channel the baseline does not hold, refuse.
3. **Complete compatibility and timing preflight:**
   - descriptor and coverage (A);
   - unique writers;
   - layer and curve evidence for every planned channel;
   - the time triple;
   - the Motion Editor gate;
   - the clock policy (E);
   - the true no-op decision across the whole plan.

   All of it is revalidated immediately before `StartUndo`.
4. **One synchronous owned Undo transaction:** `StartUndo`, then `InsertKeyAtTime` + `SetKeyValue` (insert) or
   `SetKeyValue` (update) only, then `FinishUndo`.
5. **Complete post-write authored-state verification** inside the transaction:
   - every planned channel equals the plan;
   - every other channel, control and operator relationship equals the baseline.
6. **Verified whole-operation restoration after Abort:** `AbortUndoableOperation` only while the transaction is
   provably held, then the whole-instance comparison against the baseline.
7. **One postcommit refresh:** one same-time head request, outside the transaction.
8. **One guarded deferred whole-skeleton verification (P7):**
   - every bone's P against the record's oracle;
   - placement unchanged;
   - preserved channels identical.

   A failed verification stays committed-unverified.

The fail-closed recovery lockout is kept unchanged: an uncertain write or Undo state sets it.

**Dormant channels.** A constrained bone (for example `bip_pelvis`, the IK chain bones and the collar bones) still
has its own position and orientation channels. These are classified as dormant. They are:
- never written as ordinary FK inputs;
- never counted as competing active writers of a bone whose driver is a verified constraint at its qualified weights;
- required to keep byte-identical keys.

If the constraint is not the verified active driver (weight not as qualified, disabled, missing), the bone's
authority is ambiguous and the operation refuses.

## 7. E — FK translation and clock safeguards

- **Orientation-only FK mapping:** allowed only when the bone's local translation equals the required structural
  offset on both record and destination, within tolerance. This is verified from the descriptor and the destination
  discovery.
- **Translation as a pose input:** if a bone's translation is an actual pose input (S0-Q9: an animated position
  channel, or a value differing from the structural offset), its position channel is supported and written. It is
  never silently discarded. If it cannot be supported, the operation refuses.
- **Playhead safeguards kept:**
  - Apply only in the Motion Editor;
  - the time triple;
  - the clock revalidation before `StartUndo`;
  - the Argon B.2 Save/Update refusal when a region channel's clock differs from the mapped tick.
- **Not assumed:** that every untouched FK channel reports the current playhead time in the Motion Editor. Stage D
  qualified this only for the four arm channels. S0-Q10 measures it for every channel class. The full-body clock
  policy (which channels must report the mapped tick, and what evidence replaces it otherwise) is decided from that
  evidence before S1 (section 10, item 4).

## 8. F — Compatibility and record versions

| | Legacy pose (`pose.version 1`, region `left_arm`) | Full-body pose (`pose.version 2`, region `full_body`) |
|---|---|---|
| Reading | readable and usable, unchanged on disk, never upgraded or reinterpreted | new strict schema with the compatibility descriptor |
| Apply | the qualified arm path, unchanged | the full-body transaction (D) |
| Update | keeps its existing left-arm behaviour | replaces the complete pose |
| Save New | — | always creates a complete pose; no partial-pose creation controls |

The following refuse safely, before any write:
- an incompatible rig class or structure;
- different proportions (structural offsets or scale state);
- a different solver configuration or constraint weights.

A v1.1.0 CPM's strict parser refuses version 2 records as unreadable and never changes them.

**Deferred:** cross-character retargeting and partial-pose creation.

## 9. Remaining empirical S0 questions

The S0 survey (`real_sfm_qualification/f01_full_body_s0/`) answers these from one read-only native session of the
Krystal R2 fixture. Each answer comes from the named observation and report fields (`EVIDENCE_SCHEMA.md`).

| # | Question | Evidence |
|---|---|---|
| S0-Q1 | Every model bone and its parent; each with exactly one scene element | `bones`, `scene` |
| S0-Q2 | Every rig handle and its parent (`Hip`, spine, `Neck`, `Head`, `CollarR`, legs, `rig_footHelper0`–`3`) | `rig.handles`; report `rig_handles` |
| S0-Q3 | Controller-to-bone and controller-to-handle relationships | `controls`, `channels.binding`; report `controls` |
| S0-Q4 | The constrained and the directly animated bone sets; the dormant channels | `operators`, `writer_index`; report `bones[].class`, `dormant_channels` |
| S0-Q5 | Leg and arm IK: joints, target, pole, solver settings, weights; the knee and elbow orientation controls' role | `operators[].slaves/targets/pvTarget/solver`; `Knee_*_o`, `Elbow_*_o` channels |
| S0-Q6 | Foot helpers and foot roll: their parents, children, writers and constraint roles | report `rig_handles`, `operators` |
| S0-Q7 | Twist-bone authority (FK channel, operator output, constraint or none; bones 150 and 155) | report `bones` |
| S0-Q8 | Fingers, carpals, toes, tail, hair, ears and other body bones: independently animated, constrained, fixed or driven | report `bones`, `bone_classes`, `unaccounted_bones` |
| S0-Q9 | For each FK bone: is translation a fixed structural offset or animated; does it agree across the three instances | report `bones[].translation`, `instances[].local_position_differences` |
| S0-Q10 | `GetCurrentTime()` per channel class in the Motion Editor (untouched, after moving the playhead, after selecting the set) and in the Clip Editor | report `clocks_by_observation`, `off_clock_channels` |
| S0-Q11 | Log and layer types, layer counts, curve info, keys at the mapped tick, unique or competing writers, effective values at the playhead | `channels[].layers`, `value_at_mapped`, `writer_index.destinations` |
| S0-Q12 | Compatibility: scale state, constraint weights, rig identity; structure equality and posture differences between the three Krystal instances | report `scale`, `operators`, `instances` |
| S0-Q13 | Any unknown operator type or unclassified element | report `operator_types_in_document`, `unaccounted_bones` |

S0 is structural and read-only. Foot-roll and knee *behaviour* under changed inputs needs a scene change. If the
structure leaves it open, a behavioural probe needs separate authorization.

## 10. Resolved Owner decisions (2026-11-05)

1. The independent architectural review is **closed**. The hybrid architecture (Astra), with Argon's adversarial
   corrections, is accepted. No further review is commissioned unless evidence reveals a material architectural
   contradiction.
2. **Hybrid discovery + validated profiles** (A): an explicit validated rig core, discovery, structural
   classification, complete coverage verification and a saved compatibility descriptor. No universal hardcoded
   secondary-bone list. No writability inferred from names.
3. **Complete skeletal posture by default** (B). Secondary and appendage bones are included when independently
   poseable. This supersedes the proposal's D1 ("out for the first version"). Unknown or unsupported controls refuse;
   they never silently disappear.
4. **Preserved:**
   - placement and facing;
   - proportions and scale;
   - facial flexes;
   - jaw and tongue;
   - eye gaze;
   - rig configuration;
   - unrelated animation.
5. **Coordinates** (C): placement-relative posture, actual parent-local values and planned destination parents are
   kept apart. The legacy left-arm mapping is preserved. Parent-local copying is not assumed to reproduce posture.
   This supersedes the proposal's single "character-space local posture" principle.
6. **One combined transaction** (D) with an instance-wide baseline, a deduplicated plan, complete preflight, one owned
   Undo, post-write verification, verified Abort restoration, one refresh, one deferred whole-skeleton verification
   and the existing recovery lockout. Dormant channels on constraint-driven bones are handled explicitly.
7. **FK translation and clocks** (E): orientation-only mapping only with verified structural offsets; translation
   that is a pose input is supported, not discarded. The qualified playhead safeguards are kept. Untouched-FK clock
   behaviour is an S0 question, not an assumption.
8. **Versions** (F):
   - version 2 full-body records;
   - version 1 left-arm poses stay readable and usable;
   - legacy Update keeps its left-arm behaviour;
   - New Save always creates complete poses (the proposal's D4, confirmed);
   - incompatible rigs, proportions or solver configurations refuse;
   - retargeting and partial-pose creation are deferred (D3: refuse, confirmed).
9. The proposal's **D2** (fingers, carpals, toes orientation-only) is replaced by E. It holds only where S0 and the
   descriptor verify the offsets.
10. **Krystal-specific** first qualified implementation; broader compatibility is established separately.
11. **S0 first:** one bounded read-only native survey before the coverage contract is finalized and implementation
    is authorized.
12. **Not decided by this authorization** (remain open; they do not block S0):
    - D5, storing the source session's base file name;
    - D7, the fate of the experimental `arm_right_v1` mapping.

## 11. Qualification plan (S3)

There are three short native sessions on a disposable copy of the fixture. The source and destination are posed
distinctly: before Apply, every included region differs by at least 10° (or 2 units for translated bones),
measured in the destination.

1. **Q-A: complete save and persistence.** In the Motion Editor, Save New on a source posed away from rest in every
   region:
   - the record holds every classified element and its descriptor;
   - every element is accounted for, and no element is unsupported.

   SFM is then closed completely. In a new process, the record lists, reloads byte-identical and Pose Info shows
   `Full body`.
2. **Q-B: apply elsewhere.** A different shot, with the destination character at a different world position and
   facing. One Apply (Motion Editor):
   - every bone's placement-relative posture matches the oracle within 0.01° and 0.001 units, including the
     secondary bones;
   - the placement and `rootTransform` world transforms are unchanged within 1e-6;
   - the following have byte-identical keys: flexes, jaw and tongue, eye controls, scale attributes and scale
     channels, constraint weights, dormant channels, and every unrelated channel;
   - there is one Undo entry; Undo restores the baseline exactly and Redo reapplies;
   - a second Apply is a no-op ("Already matches this pose.");
   - moving the playhead away and back shows the same pose.
3. **Q-C: refusals and regression.**
   - Apply in the Clip Editor refuses, and so does a clock-mismatched Save; both change nothing.
   - A structurally incompatible destination refuses before any write. This is a disposable copy with one changed
     constraint weight, or another model.
   - The qualified Pose B left-arm pose applies as before, to a destination whose arm differs.
   - Legacy Update replaces only the left arm.

Offline suites (both interpreters) precede S3. The existing arm suites stay unchanged and passing.

## 12. Stages

| Stage | Content | Gate |
|---|---|---|
| S0 | Read-only native survey (prepared) | Owner execution; report reviewed; core list and clock policy fixed from evidence |
| S1 | Offline core: v2 schema, discovery, classification, coverage, descriptor, plan, transaction, P7, refusals; fake full biped | Offline suites; arm tests unchanged |
| S2 | UI: complete Save New, Pose Info `Full body`, legacy handling | Offline page and integration suites |
| S3 | Native qualification (section 11) | All criteria met |
| S4 | Registry: full-body mapping qualified | Owner acceptance |

Each stage needs its own authorization.

## 13. Open items and possible contradictions

1. The Astra and Argon texts are not in the repository. Attribution beyond the authorization's wording is not
   possible from this repository.
2. **Ears** were excluded by the proposal as facial and are included by the authorization as appendages. This is
   resolved by the authorization, subject to S0 classification.
3. **Coverage versus support:** "every discovered skeletal control accounted for" together with "unsupported controls
   must not silently disappear" means full-body Save on Krystal refuses until every element has a supported class.
   S0 shows whether that is achievable without new mechanisms.
4. **Clock policy at full-body scale:** this may be material. If S0 shows that untouched FK channels do not report
   the mapped tick in the Motion Editor, the Argon B.2 rule would refuse every full-body Save. The rule cannot simply
   be relaxed. A replacement evidence of evaluation time would need an Owner decision before S1.
5. **Proportions:** Body Presets own flexes and bone scale (M-05/M-06), not bone position or orientation channels. A
   full-body pose therefore never overwrites them. A scale-state difference changes child world offsets, so it
   refuses (F) until retargeting exists.
