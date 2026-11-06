# F-01 Full-Body Pose Library: design proposal (for Owner and Astra review)

Status: **proposal only; nothing in this document is implemented.** Branch `feature/f01-pose-library` at `8634e2c`.
Labels: **[V]** verified in the code or in recorded native evidence (source named); **[P]** proposed; **[O]** open
question that must be answered before or during implementation.

## 1. Existing implementation and limitations

**What a pose is today [V]** (`cpm/pose_profiles/cpm_pose_profiles_v1.json`, stage D block of the CPM):

- One rig class, `krystal-v1` (model `krystal2020.mdl`), with two arm profiles: `arm_left_v1` (production mapping,
  qualified) and `arm_right_v1` (experimental, hidden in production).
- **Captured per arm:** the hand goal (position and orientation) and the elbow pole position, expressed in the
  collar's frame (`anchor: CollarL`), plus a skeletal oracle (local and collar-mapped world orientation of
  `bip_UpperArm_l`, `bip_lowerArm_l`, `bip_hand_l`) and a compatibility descriptor (arm chain, channel bindings,
  constraints, handle parents, scale state). The 19 finger and carpal bones are **only checked to follow the hand;
  they are not saved** (native Pose B record, `follow_the_arm_bones`).
- **Written on Apply:** exactly three channels, `Hand_l_p`, `Hand_l_o`, `Elbow_l_p`, one key each at the mapped
  tick; `Elbow_l_o` is observed and must stay unchanged. The collar-relative goals are re-expressed in the
  destination's `rig_root` space through the destination's own collar, so the arm follows the destination torso.
- **Pipeline:** P1 preflight (descriptor match, structural checks, unique writers, layer evidence, exact time
  triple, true no-op), the Motion Editor gate (mode 2, every target channel clock at the mapped tick), one
  `StartUndo`/`FinishUndo` transaction with `InsertKeyAtTime` + `SetKeyValue` and post-write checks, one same-time
  head refresh, then the deferred P7 verification against the oracle (0.01 deg). Uncertain write or Undo state sets
  the fail-closed recovery lockout. Save and Update refuse when any region channel clock is not the mapped tick
  (Argon B.2, `e70e515`).
- **Record:** `pose.version 1`, regions keyed by name; `source` is exactly `{rig_class, model_ref, shot_name,
  t_doc_ticks, t_shot_ticks}` (strict schema).

**Limitations:** one arm only; no torso, neck, head, legs, fingers or toes; the source is a shot name only.

**Krystal's rig as natively recorded [V]** (PS-1b5 OBS-03, shot15 `other_channels`; native Pose B descriptor):

| Group | Controls | Drives |
|---|---|---|
| Placement | `rig_root` | `rootTransform` (point + orient constraint) |
| Pelvis, spine | `Hip`; `spine_1`–`spine_4` | `bip_pelvis`; `bip_spine_0`–`bip_spine_3` (point + orient) |
| Neck, head | `Neck`, `Head` | `bip_neck`, `bip_head` (point + orient) |
| Collars | `CollarL`, `CollarR` (parent `spine_4`) | `bip_collar_l/r` (point + orient) |
| Arms (IK) | `Hand_l/r` (target), `Elbow_l/r` (pole), both parented to `rig_root` | IK chain + `bip_hand_l/r` orient |
| Legs (IK) | `Foot_l/r` (target), `Knee_l/r` (pole) | IK chain + `bip_foot_l/r` orient |
| Rig helpers | `rig_footHelper0`–`rig_footHelper3` | **[O] role not yet established** |
| FK bones (no constraint) | 30 finger bones, 8 carpals, 24 toe controls + `bip_toe_l/r`, 6 twist bones, 26 tail, ~15 hair, breasts, butt, jaw, 8 tongue, 6 ear, genital and cosmetic controls | themselves |
| Not transforms | `bip_head_scale`, `bip_tail00_scale` (body scale, M-05), `eye_convergence`, `viewTarget`, `localViewTargetFactor`, 28 constraint `targetWeight` channels | — |

In total the shot15 Krystal has 177 transform controls (71 rig/non-`bip`, 106 `bip`) and 110 flex channels. The
constrained `bip_*` bones also have their own channels, which the constraints override.

## 2. Proposed full-body capture and Apply architecture [P]

**Principle: character-space local posture.** The pose is the posture of the body relative to `rig_root`. Placement
and facing are exactly `rig_root` (and the `rootTransform` it drives), which are never captured or written. Every
in-scope control's local transform is captured at the mapped tick and written back as a key at the destination's
mapped tick. Because the IK targets (`Hand`, `Foot`) and poles (`Elbow`, `Knee`) are parented to `rig_root` [V for
the arm, O for the legs], copying their local values reproduces the limb posture relative to the character, not to
the world.

This is a different, simpler mapping than the arm's collar-relative goals and is valid only between identical rig
classes **with matching proportions** (section 6, R1). It is a new region kind, not a change to the arm algorithm.

**Reuse, with bounded extensions:**

| Existing element | Full-body use |
|---|---|
| Registry, rig class, production/qualified mapping | New profile `body_krystal_v1` with an explicit required-control list; experimental until qualified |
| Instance resolution, pinned context, M-06 | Unchanged |
| Time triple, Motion Editor gate, capture clock check | Unchanged; applied to every in-scope channel |
| Unique-writer, layer-evidence and curve-info checks | Generalized from 3 channels to the profile's list |
| Transaction (one Undo entry, insert at t, post-write checks) | Same code path over N channels (about 94: 17 rig handles, 30 written position/orientation channels, plus 64 FK orientations) |
| One same-time refresh, deferred P7, recovery lockout | Unchanged; P7 oracle widened to every in-scope bone |
| Arm collar-relative plan, shoulder guard | Unchanged, used only by legacy arm poses |

No new polling, no general rig rewriting, no writes outside the listed channels.

**Verification oracle:** for every in-scope bone, its local orientation and its `rig_root`-space position, captured
from the evaluated skeleton; P7 compares the destination after Apply. Placement (`rootTransform` world transform)
must be unchanged; excluded channels must have identical key arrays.

## 3. Exact skeletal scope and exclusions [P]

| Included (written) | Channels |
|---|---|
| Pelvis | `Hip` position + orientation (height and lean are posture) |
| Spine, neck, head | `spine_1`–`spine_4`, `Neck`, `Head` position + orientation |
| Collars | `CollarL/R` position + orientation |
| Arms | `Hand_l/r` position + orientation, `Elbow_l/r` position (`Elbow_*_o` observed, as today) |
| Legs | `Foot_l/r` position + orientation, `Knee_l/r` position (**[O]** the knee orientation's role) |
| Hands | 30 finger bones and 8 carpals: **orientation only** (positions are bone offsets, i.e. proportions) |
| Feet | toe controls and `bip_toe_l/r`: orientation only |

| Excluded (must stay byte-identical) | Reason |
|---|---|
| `rig_root`, `rootTransform` | placement and facing |
| all flex channels | facial expressions and body morphs (Body Presets / Expressions own them) |
| `jaw`, `tongue*`, ears, `viewTarget`, `eye_convergence`, `localViewTargetFactor` | facial / eye control |
| scale channels (`bip_head_scale`, `bip_tail00_scale`, M-05 bone scale) | body proportions |
| constraint `targetWeight` channels | rig configuration (IK/FK switch); required at their qualified values instead |
| the constrained bones' own `bip_*` channels | overridden by constraints; writing them changes nothing visible but could diverge |
| tail, hair, breasts, butt, genitals, anus, cosmetic | secondary motion; **Owner decision D1** (default: excluded) |

**[O]** to settle in stage S0: whether the twist bones (`bip_*_twist2`) and `bip_hip_twist2_*` are animated FK
channels or driven (include as orientation-only, or exclude), and what `rig_footHelper0`–`3` do (foot-roll pivots
would be posture and must be included or required at neutral).

## 4. Mapping and rig compatibility [P]

- Support begins with **Krystal (`krystal-v1`) only**. A full-body pose applies only to the same rig class.
- The profile lists every required control with its expected binding, parent, constraint and log/layer types.
  Capture and Apply resolve the **complete** list first. If any required control is missing, ambiguous,
  differently parented, driven by another writer, has an unexpected constraint weight, an unsupported log or a clock
  off the mapped tick, the operation refuses **before any write or save**: "This character's full-body rig isn't
  supported." It never saves or applies a subset.
- **Proportions:** the record stores the source skeleton's bone offsets and scale state. Apply refuses when the
  destination's differ beyond tolerance (R1), until a retargeting design exists.
- Other characters need their own qualified profile and mapping; no automatic discovery of "all transform
  channels".

## 5. Legacy pose compatibility [P]

| | Legacy partial pose (`version 1`, region `left_arm`) | Complete pose (`version 2`, region `full_body`) |
|---|---|---|
| Identity, metadata, stored values | unchanged on disk; never rewritten by an upgrade | new records only |
| Listed | yes | yes |
| Pose Info "Body parts" | `Left arm` | `Full body` |
| Apply | the existing qualified arm path, unchanged | the full-body path |
| Update | replaces exactly its saved parts (left arm), as today | replaces the full-body posture |
| Save New | — | always creates a complete pose; no partial creation controls |

A legacy pose is never reinterpreted as a complete pose and cannot be converted silently. A v1.1.0 CPM reading a
version 2 record refuses it as unreadable (its strict parser), lists it as unusable and never changes it.

## 6. Safety risks and mitigations

| # | Risk | Mitigation [P] |
|---|---|---|
| R1 | Different proportions (Body Presets, M-05 bone scale) make copied IK targets reach differently: sliding feet, overextended arms | Proportion descriptor in the record; Apply refuses on mismatch; retargeting is out of scope |
| R2 | IK flip or pole ambiguity | Poles copied with targets; P7 bone oracle catches any flip; refuse on failure |
| R3 | Partial write across about 94 channels | One transaction; post-write checks per channel; any failure aborts and verifies the abort; otherwise the recovery lockout, as today |
| R4 | Destination already matches (PS-1b5) | Per-channel no-op test; the qualification destination must differ measurably |
| R5 | Existing keys at t, layered or curve-typed logs | Existing layer-evidence refusals, extended to every channel |
| R6 | Unknown helpers or twist drivers | Stage S0 read-only survey; anything unresolved stays out of scope or required-neutral |
| R7 | Undo size and time | One Undo entry; measure in S0/S3; no polling |
| R8 | A source session name exposes a private path | Store the file name only, never directories (section 7) |

## 7. Pose Info and source identification

- **[V]** `vs.g_pDataModel.GetFileName(sfmApp.GetDocumentRoot().GetFileId())` returned the open session's full path
  in all 12 recorded native runs (Stage D observer), lowercased by SFM, for example
  `e:\sfm_u0b_scratch\f01-stage-d-cc1\sessions\nq1_source.dmx`.
- **[O]** its value for a new, never-saved session, and after Save As.
- **[P]** record an optional `source.session_name` = the base name only (`nq1_source.dmx`), omitted when empty or
  unreadable; Pose Info shows `nq1_source.dmx / shot15`, or the shot alone. It is provenance only (never used for
  Apply). It needs the version 2 schema; version 1 records keep their exact `source`.

## 8. Implementation stages and native acceptance gates [P]

| Stage | Content | Gate |
|---|---|---|
| S0 | Read-only native survey of the Krystal rig: every handle's parent, constraints and weights, each candidate channel's writer, log and layer, twist drivers, foot helpers | One observation; the profile's required list fixed from evidence |
| S1 | Offline core: version 2 schema, `body_krystal_v1` profile, generalized capture, plan, writes, P7, refusals; the fake rig extended to a full biped | Offline suites on both interpreters; the arm path's tests unchanged |
| S2 | UI: Save New creates complete poses, Pose Info `Full body` and source, legacy handling | Offline page and integration suites |
| S3 | Native qualification (below) | All criteria met |
| S4 | Registry: full-body mapping promoted after S3 | Owner and Astra acceptance |

**Native qualification (S3): three short sessions**

1. **N1 capture and reload:** in a Krystal source shot, distinct adjustments on every in-scope region (each at least
   10 deg or 2 units away from rest). Save New (Motion Editor) gives a complete record. In a new SFM process, the
   record reloads unchanged.
2. **N2 apply elsewhere:** a different shot and session whose starting posture differs from the pose by at least
   10 deg in every region (measured before Apply). One Apply:
   - every in-scope bone matches the oracle within 0.01 deg local orientation and 0.001 units `rig_root`-space
     position;
   - `rootTransform` world position and facing unchanged within 1e-6;
   - every excluded channel (flexes, scale, jaw, eyes, secondary bones, constraint weights) has identical keys;
   - one Undo entry; Undo restores the baseline exactly, Redo reapplies, a second Apply is a no-op;
   - moving the playhead away and back shows the same pose.
3. **N3 refusals and regression:**
   - Clip Editor Apply and a clock-mismatched Save refuse;
   - a session with one required control removed or a constraint weight changed refuses before any write;
   - another model refuses;
   - the qualified Pose B left-arm pose applies as before, to a destination whose arm differs.

## 9. Decisions requiring Owner or Astra adjudication

| # | Decision | Recommendation |
|---|---|---|
| D1 | Secondary bones (tail, hair, breasts, butt, genitals, cosmetic) in or out | Out for the first version |
| D2 | Fingers, carpals and toes: orientation only | Yes |
| D3 | Proportion mismatch: refuse (until retargeting) | Refuse |
| D4 | Save New always creates a complete pose; partial creation removed; legacy poses kept and usable | Yes |
| D5 | Store the session file name (base name only) as provenance | Yes, when readable |
| D6 | Astra review of the generalized transaction (N channels) before S3 | Recommended: it changes the qualified write path's scope |
| D7 | Keep `arm_right_v1` experimental / retire it once full body is qualified | Retire from production scope |
