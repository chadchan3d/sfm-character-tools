# F-01 Full-Body S0 — Evidence Assessment and Design Reconciliation

**2026-11-06.** Branch `feature/f01-pose-library`. This assesses the completed read-only S0 survey against
`F01_FULL_BODY_CONSOLIDATED_DESIGN.md` (Rev 1, Owner-accepted 2026-11-05). It does not change that design; section 6
lists **proposed** amendments for Owner (and, where marked, Astra) adjudication. Full-body implementation is not
authorized.

Labels: **[N]** native observation (a recorded field); **[A]** derived by the analyzer or by this assessment from
native fields; **[P]** proposal.

## 1. Evidence identities

Run folder `E:\SFM_U0B_Scratch\f01-full-body-s0-r2` (Owner's local archive; not committed). One SFM process
(pid 19088), session copy of the R2 fixture, published CPM installed, CPM not opened (`cpm_loaded: null`).

| File | SHA-256 | Content |
|---|---|---|
| `observations/S0-01.json` | `363444d8dfffc37510708be0cb0ed891dc7c727ed92b1a7ac411b5329dd28a78` | Clip Editor, shot15, 0.2083 s, t_chan 50208 |
| `observations/S0-02.json` | `5b39e969f98952185e1a4b8f6f5537115bce88135d0bfd1d265d034dd69694cb` | Motion Editor, shot15, 0.2083 s, 50208 (primary) |
| `observations/S0-03.json` | `d63017f54d17fd5ed9f7241c892d13825e130150b4cf3a4d4f18262f5a3e586d` | Motion Editor, shot15, 0.2500 s, 50625 |
| `observations/S0-04.json` | `19cbb3647013c4584cd2b2654abde3f23a20a384deb8d6ed8088705a9be5b87c` | Motion Editor, shot15, 0.2083 s after selecting Krystal |
| `observations/S0-05.json` | `13187b1a9282e2dc223f53a0460c92ed3fc10356babb9c97bc5c40e418aca2c1` | Motion Editor, shot10, 0.4167 s, 50208 (another instance) |
| `observations/S0-06.json` | `721bd1b1a22d14ad284b381c6291ec0d90507e68e6cf6b7827e50f1b5b39ec24` | Motion Editor, shot13, 0.3750 s, 50416 (another instance) |
| `evidence/post.json` | `c11a11e09419cc6f3cc9ba8572017ab04353cdac8207fdc483fc8e02f7779b12` | POST PASS: inventories unchanged, session unsaved; `demoheader.tmp`, `tf2_playerstats.dmx` put back |
| `evidence/S0_REPORT.json` / `.md` | `3d8b9f64…` / `164cb534…` | analyzer output at commit `916c7a4` (original; kept unchanged) |
| `sessions/S0_SURVEY.dmx` | `259ea8a6…` | identical to the fixture: never saved |

Read-only proof [N]: every observation's document digest before equals after (`9bc3ee87…`, 10070 channels) and the
digest is identical across all six. Each observation has `problems: []` and `readonly.unchanged: true`.

**Corrected re-analysis [A].** Reading the observations showed three analyzer misreadings (section 3A, 3C).
The analyzer was corrected (commit `088cbe9`, tooling only; observer unchanged) and re-run on the unchanged
observations into `E:\SFM_U0B_Scratch\f01-full-body-s0-r2-assessment\` (`S0_REPORT.json`
`2a4c44c7dce1201d37caead8e8dae0c176e5528cdb76f8333f61931b7ec167c6`, `S0_REPORT.md` `fd5f39c2…`). The original report
stays as produced. Corrected classes: **133 direct FK, 21 constrained, 2 channel-driven without a control**; none
unaccounted.

The first run (`f01-full-body-s0`) is invalid by operator sequence and is not used, except one supplementary clock
fact marked as such in 3B.

## 2. S0-Q1 … S0-Q13

| # | Question | Evidence | Result | Consequence for the design | Another native observation? |
|---|---|---|---|---|---|
| Q1 | Every bone and its parent; one scene element each | [N] S0-02 `bones` (156, each `dag` unique, `parent_bone`), no observer problem; [A] identical bone set and parents in all three instances (`instances.*.structure_equal.bones`) | **RESOLVED** | The descriptor's skeleton is exact: 156 named bones with parents | No |
| Q2 | Every rig handle and its parent | [N] `rig.handles` (22): `rig_root` and `rig_footHelper0–3` under the DmeRig; `spine_1`, `Hand_l/r`, `Elbow_l/r`, `Foot_l/r` under `rig_root`; `spine_2→spine_1`, `spine_3→spine_2`, `spine_4→spine_3`; **`Hip→spine_1`**; `Neck`, `CollarL/R → spine_4`; `Head→Neck`; **`Knee_l/r → Foot_l/r`** | **RESOLVED** | Parent-local values of Hip and Knee are relative to `spine_1` and the foot, not `rig_root`: the plan must use these parents (design C) | No |
| Q3 | Controller-to-bone and -handle relationships | [N] `controls` (290: 178 transform, 112 other) with channel references; `channels[].binding`; [A] corrected report `controls` | **RESOLVED** | 22 handle controls → handle transforms (18) or constraint slaves (foot helpers); 133 FK controls → their bones; 21 constrained-bone controls → their constraint slaves (IK-chain position → bone); `rootTransform` → its slave; `viewTarget` → the view target; 110 flex, scale and eye controls → operators / model | No |
| Q4 | Constrained and directly animated sets; dormant channels | [N] `operators` slaves, `writer_index`; [A] corrected `bones[].class`, `dormant_slave_base_channels`, `structural_offset_channels` | **RESOLVED** | 21 constrained bones; their 42 own channels: 30 write `DmeConstraintSlave` base values (dormant at weight 1), 12 IK-chain `_p` write the bone position (active bone offsets). Plus 8 foot-helper and 2 `rootTransform` slave-base channels. See 3C | No |
| Q5 | IK joints, targets, poles, solver, weights; knee/elbow orientation role | [N] four `DmeRigIKConstraintOperator`: arm `UpperArm→lowerArm→hand`, target `Hand`, pole `Elbow`; leg `hip→knee→foot`, target `Foot`, pole `Knee`; `mode 0`, `poleVector [0,1,0]`, per-op `startOffset`/`midOffset`; orient constraints hand/foot from `Hand`/`Foot`; all 28 weights 1.0 (one key) | **PARTIALLY RESOLVED** | Structure and settings fixed for the descriptor. `Elbow_*_o`, `Knee_*_o` are animated (5–6 keys) but nothing observed consumes them (no child handle, not a target; the IK reads `pvTarget`). Their writing is a policy decision (A2), not an evidence gap | No (P7 verifies the skeleton whatever is decided) |
| Q6 | Foot helpers and foot roll | [N] `rig_footHelper0–3`: parent DmeRig; each point+orient constrained (weight 1) to **`bip_hand_r`, `bip_hand_l`, `bip_foot_l`, `bip_foot_r`** respectively; not a target or pole of any operator; their controls write their slave base | **RESOLVED** | They are passive followers of the hands and feet, not foot-roll pivots; the rig has no foot-roll mechanism. Not written; preserved. (Two "foot" helpers follow hands: names are not evidence) | No |
| Q7 | Twist-bone authority | [N] `bip_UpperArm_l/r_twist2`, `bip_hip_twist2_l/r`: FK controls; `bip_lowerArm_l/r_twist2`: written by `…_twist2_p/_o` channels with **no source element** (`fromElement` null), 20 keys, one distinct value, mode 3; no control, no operator, no constraint; identical in all three instances | **RESOLVED** (authority) | Two classes: 4 twist bones are FK pose inputs; 2 are passive, channel-driven, not user-poseable (A3). The model's `evaluateProceduralBones` attribute exists but its value was not recorded; render-time procedural evaluation does not change the DME transforms the pose reads and writes | No |
| Q8 | Fingers, carpals, toes, tail, hair, ears, other body bones | [A] all direct FK: 30 fingers, 8 carpals, 26 toes (incl. `bip_toe_l/r`), 26 tail, 15 hair, 6 ears, 4 breasts, 2 butt, `Genitals`, `Anus`, `Cosmetic`, `jaw`, 8 tongue, 4 twist; [N] shot10's instance differs from shot15's in 41 FK orientations (ears 17.7–47.9°, left fingers 18.6°, tail 8.6–18.1°) | **RESOLVED** | Every secondary bone is independently poseable FK; all are in coverage | No |
| Q9 | FK translation: fixed offset or animated | [N] all 266 FK channels one layer, **one key (t = 0)**, one distinct value; mapped value equals the bone's local transform; [A] FK local positions identical in all three instances (only constrained `bip_pelvis`, `bip_spine_0` differ); [N] the model exposes no bind/rest-pose attribute (`model.attribute_names`) | **PARTIALLY RESOLVED** | No FK translation is animated in this fixture, but one value per control does not prove a control is never translated, and no rest offsets are readable natively. Translation must be treated as a possible pose input (A1) | No for S1 (the proposed policy does not need a rest table) |
| Q10 | `GetCurrentTime()` per channel class and editor | [N] every channel's `current_ticks`: S0-01 Clip Editor **505/505 = 50299** (mapped 50208); S0-02/03/04/06 Motion Editor **505/505 = mapped tick**, following the playhead (50625 at 0.25 s) and the shot (50416 in shot13); S0-05 **503/503**; selection (S0-04) no change; untouched FK included | **RESOLVED** (this fixture, one process) | The Argon B.2 rule extends to the full body **unchanged**: in the Motion Editor every channel reports the mapped tick; in the Clip Editor none does, so Save there refuses as today. Closes design §13 item 4 as not material | No |
| Q11 | Log/layer types, layers, curve info, keys at t, writers, values | [N] all 505 channels: mode 3, one layer, `curveinfo` null; 180 Vector3, 180 Quaternion, 145 Float layers; no handle or FK channel has a key at the mapped tick (`key_at_mapped` null → Apply inserts); handle keys at 0–2333, 29999–30000, 70415–70417; [A] no instance destination has more than one writer | **RESOLVED** | The existing per-channel layer, curve and unique-writer checks generalize; first Apply inserts on every channel | No |
| Q12 | Compatibility: scale, weights, rig identity; instances | [N] model `models/fursonas/starfox/krystal/bodies/krystal2020.mdl` in all three; rig `rig_biped_Krystal45`, registration `rigElements_Krystal` (`hiddenGroups` Body, Arms, Legs); `bip_head` scale 1.13 everywhere; **`bip_tail00` scale 0.8 in shot15/shot13 but ABSENT in shot10**, whose set also lacks the `bip_tail00_scale` control, its expression operator and two channels; solver settings and weights equal across instances; [A] shot13's posture equals shot15's (0 of 156 bones differ); shot10 differs in 61 bones and faces another direction (same world position) | **RESOLVED** | The scale-state descriptor must include scale attributes and scale controls: a shot15 pose applied to shot10 must refuse. The fixture has no posture-distinct, scale-compatible destination for S3 (section 5) | No for S1; S3 needs a prepared destination |
| Q13 | Unknown operators or unclassified elements | [N] document operator types: Expression 224, PackColor 7, IK 64, Orient 278, Point 214 (all known); instance: 3 expression operators (`eye_convergence_rescale`, `bip_head_scale_rescale`, `bip_tail00_scale_rescale`) and 36 constraints; [A] none unaccounted | **RESOLVED** | No unsupported element on Krystal | No |

## 3. Critical technical findings

### A. The two bones "without observed writers"

`bip_lowerArm_r_twist2` (bone 150, parent `bip_lowerArm_r`) and `bip_lowerArm_l_twist2` (bone 155, parent
`bip_lowerArm_l`) [N]:
- each transform is written by two instance channels, `…_twist2_p` and `…_twist2_o`, mode 3, one layer of 20 keys
  (0, 500, 1000 … ticks) with one distinct value each;
- `fromElement` is null and `fromAttribute` empty: no control drives them, so they do not appear in the Animation
  Set Editor;
- no operator references them; no constraint slaves them; their local transforms are identical in all six
  observations and all three instances (for example, right: orientation `[-0.009386, 0.001716, 0.001205, 0.999954]`,
  position `[0.0152, 4.378, 0.1172]`).

The original analyzer called them "no writer" because it only recognized control and operator sources [A]; they are
**channel-driven without a control**, not unresolved. They can safely belong to the coverage contract **without
being written**: they are passive (not user-poseable), constant, and their parents' posture is reproduced by the
arm IK. Proposed handling (A3): record their values in the descriptor, never write them, and refuse Apply when the
destination's values differ from the record beyond tolerance (an unexpected driver or edit).

### B. Channel-clock coherence

[N] per observation, `current_ticks` of every channel of the instance clip:

| Obs | Editor | Shot, playhead | Mapped | Channels at mapped | Other |
|---|---|---|---|---|---|
| S0-01 | Clip | shot15, 0.2083 | 50208 | 0 / 505 | 505 at 50299 |
| S0-02 | Motion (switched, playhead unchanged) | shot15, 0.2083 | 50208 | 505 / 505 | — |
| S0-03 | Motion (playhead moved) | shot15, 0.2500 | 50625 | 505 / 505 | — |
| S0-04 | Motion (Krystal selected, playhead back) | shot15, 0.2083 | 50208 | 505 / 505 | — |
| S0-05 | Motion | shot10, 0.4167 | 50208 | 503 / 503 | — |
| S0-06 | Motion | shot13, 0.3750 | 50416 | 505 / 505 | — |

Supplementary (invalid run 1, a separate SFM process, Motion Editor first): 505 / 505 at the mapped tick.

Every class (rig handle, direct FK, dormant slave base, IK structural offset, source-less, weight, flex/scale/eye)
behaves identically; untouched FK controls are not stale. Switching to the Motion Editor makes every clock follow
the playhead; moving the playhead or the shot keeps them coherent; selection has no effect. In the Clip Editor every
clock stays at one stale value (50299, the KP-1 value).

**The existing qualified rule is kept unchanged** and extended to every planned and observed channel: Save, Update
and Apply require every channel the operation reads or writes to report exactly the mapped tick (Apply also only in
the Motion Editor). No alternative clock evidence is needed or proposed. Limit: one fixture, one process (plus the
supplementary one); the rule itself refuses wherever this does not hold.

UI actions add Undo entries [N]: switching editors ("Change Recording State"), moving the playhead ("Modify Head
Time"). S1 must not assume an empty or CPM-owned Undo stack before Apply.

### C. Rig and solver authority [N]

| Element | Observed authority |
|---|---|
| Placement | `rig_root` (handle, parent DmeRig, 2 animated channels) → point+orient constraints → the game model (`rootTransform`); `rootTransform` control writes the model's slave base (dormant) |
| Pelvis, spine, neck, head, collars | handles `Hip`, `spine_1–4`, `Neck`, `Head`, `CollarL/R` (animated channels) → point+orient constraints (weight 1) → `bip_pelvis`, `bip_spine_0–3`, `bip_neck`, `bip_head`, `bip_collar_l/r` |
| Arms | `Hand_*` → IK end + orient(`bip_hand_*`); pole `Elbow_*`; joints `UpperArm`, `lowerArm`, `hand` |
| Legs | `Foot_*` → IK end + orient(`bip_foot_*`); pole `Knee_*` (child of `Foot_*`); joints `hip`, `knee`, `foot` |
| Solver | per IK: `mode 0`, `poleVector [0,1,0]`, fixed `startOffset`/`midOffset` quaternions; equal in all instances |
| Weights | 28 `targetWeight` channels, each one key, value 1.0, written from `… weight` elements |
| Dormant channels | the 21 constrained bones' controls write `DmeConstraintSlave` position/orientation (30 channels); the foot helpers' (8) and `rootTransform`'s (2) controls likewise. At weight 1 the bone does not take these values (for example `bip_pelvis` local position `[-1.043, 0.166, 38.959]` vs its slave base `[-0.073, 0.0, 38.938]`) |
| IK-chain bone offsets | `bip_UpperArm/lowerArm/hand/hip/knee/foot_*_p` (12) write the bone position directly; the IK sets only orientation; each is one key and equals the bone's local position: the bone lengths |
| Twist | 4 FK; 2 source-less constant channels (A) |
| Foot helpers | followers of hands and feet (Q6) |

Relationships still open that matter for capture or Apply: **none structural**. Three policy points remain (A1–A3,
section 6). Not observed behaviourally (and not needed, because P7 verifies the evaluated skeleton): how the IK
solver uses the pole handle's orientation, and what the slave base values do at a weight below 1 (weights below 1
refuse).

### D. FK position and orientation

[N] every one of the 133 direct-FK controls has one position key and one orientation key (at t = 0), each a single
value equal to the evaluated local transform. [A] FK local positions are identical across the three instances, while
41 FK orientations differ in shot10: orientation is demonstrably posed per instance; translation is not animated in
this fixture.

This is **not** proof that FK translation is never a pose input: every FK control has a live position channel
(`valuePosition` → bone `position`, mode 3) that an animator can key. No native rest or bind-pose offsets are
available (the model exposes no such attribute), so the design E "required structural offset" cannot be read from
the model. The existing observations are therefore **sufficient to design** the position check but **not sufficient
to justify omitting position**. Proposed policy A1 (section 6) needs no rest table.

## 4. Proposed Krystal coverage inventory (`body_krystal_v1`) [P]

Every element of the instance (156 bones, 22 handles, 290 controls, 505 channels in shot15) is in exactly one row.

| Category | Elements | Channels | Treatment |
|---|---|---|---|
| Placement anchors | `rig_root` handle; `rootTransform` (game model) | `rig_root_p/o`; `rootTransform_p/o` (slave base) | never written; world transform verified unchanged |
| Writable rig handles | `Hip`, `spine_1–4`, `Neck`, `Head`, `CollarL/R`, `Hand_l/r`, `Elbow_l/r` (position), `Foot_l/r`, `Knee_l/r` (position) | **30** | written parent-local at the mapped tick; parents as Q2 |
| Pole orientations | `Elbow_l/r_o`, `Knee_l/r_o` | 4 | **pending A2**; until decided: observed, preserved, clocks checked |
| Constraint-driven bones | 21: `bip_pelvis`, `bip_spine_0–3`, `bip_neck`, `bip_head`, `bip_collar_l/r`, arm and leg IK chains | 30 dormant slave base; 12 IK structural offsets | never written; slave bases byte-identical; offsets equal the record (else refuse); posture verified by P7 |
| Writable direct FK | 124: fingers 30, carpals 8, toes 26, tail 26, hair 15, ears 6, breasts 4, butt 2, `Genitals`, `Anus`, `Cosmetic`, twist 4 | **124** orientation; 124 position **per A1** | orientation always written; position per A1 |
| Preserved facial and gaze | `jaw`, `tongue00–07` (FK structurally, preserved by profile); 110 flex channels (incl. `eyes_updown`, `eyes_rightleft`); `viewTarget_pos/rot`; `eye_convergence_channel`, `scaled_eye_convergence_channel`; `localViewTargetFactor` | 18 + 110 + 5 | never written; keys byte-identical |
| Scale and proportions | `bip_head_scale`, `bip_tail00_scale` controls, their expression operators and `scaled_*` outputs; bone `scale` attributes | 4 | never written; presence and values in the descriptor; mismatch refuses |
| Rig configuration | 36 constraints, 4 IK solver settings, 28 weights, registration | 28 | never written; required exactly (weights 1.0) |
| Structural / passive | `rig_footHelper0–3` (followers); `bip_lowerArm_l/r_twist2` (source-less) | 8 slave base; 4 source-less | never written; foot helpers verified by P7; twist values per A3 |
| Unsupported or unresolved | **none** | — | any future unknown element refuses |

Channel count check against the corrected report's classes (505): rig handle 36 (`rig_root` 2 + writable 30 + pole
orientations 4); direct FK 266 (124 × 2 + jaw/tongue 18); constraint slave base 40 (30 + foot helpers 8 +
`rootTransform` 2); structural offset 12; source-less 4; weights 28; scale 4 (2 controls' channels + 2 operator
outputs); flex 110; gaze 5. Total 505.

**Proposed written set:** 30 handle channels + 124 FK orientation channels = **154 always**; plus up to 124 FK
position channels (A1) and 4 pole orientations (A2): at most **282**. Nothing in "observed" or "preserved" is written
unless A1/A2 promote it explicitly.

**Conditions before any write** (P1, revalidated at P2):
1. Same model path, rig name and registration; 156 bones with the recorded parents; 22 handles with the recorded
   parents; the recorded operator set, types, slaves, targets, poles and solver settings.
2. Every weight exactly 1.0 with one key; every IK-chain offset and every source-less twist value equal to the record
   within 1e-4 / 0.01°.
3. Equal scale state (attributes present or absent, values, scale controls and operators).
4. Every planned channel: in the instance clip, mode 3, one layer of the expected type, `curveinfo` null, the unique
   writer of its destination.
5. Motion Editor; every read or written channel reports exactly the mapped tick.
6. No unknown operator type anywhere in the document; every element classified.

## 5. Implementation readiness

**Determination: READY FOR S1 DESIGN/IMPLEMENTATION AUTHORIZATION**, with three bounded policy decisions (A1–A3) to
be made in that authorization. They need no further native evidence.

S3 note (not an S1 blocker): the fixture offers no posture-distinct, scale-compatible destination: shot13 equals
shot15, and shot10 differs in `bip_tail00` scale state. S3 needs a destination prepared by ordinary SFM editing of a
disposable copy (Owner-performed), and shot10 serves as the scale-state refusal case.

Proposed S1 slices, each offline-only with its own acceptance:

1. **S1-1 Validated coverage and rig compatibility.** The `body_krystal_v1` profile (core and preservation lists
   above), the binding-evidence classifier, coverage verification and the descriptor. A compact structural fixture
   derived from S0-02 (names, parents, bindings and constraint topology; no animation values) drives the tests.
   Accept: the classifier reproduces section 4 exactly; refusals for a missing or re-parented handle, an extra
   bone, an unknown operator, a weight ≠ 1, a changed solver offset, a scale-state change, a changed IK offset or
   twist value, a competing writer, an unreadable field.
2. **S1-2 Version 2 record schema.** Strict v2 parser and writer (`full_body` region, descriptor, oracle for all
   156 bones). Accept: round trip; every malformed or extra field refused; v1 records parse exactly as today; the
   v1.1.0 strict parser refuses v2 without changing it.
3. **S1-3 Combined, deduplicated plan and transaction.** Parent-local plan with planned parents (C); per-channel
   insert/update; whole-plan no-op; one owned Undo; post-write authored-state verification of all 505 channels;
   verified Abort restoration; one refresh; deferred whole-skeleton P7. Accept on a fake full Krystal biped:
   placement-relative posture within 0.01° / 0.001 units; everything outside the plan byte-identical; one Undo
   entry; injected failure at the first, a middle and the last channel aborts and verifies; uncertain Undo sets the
   lockout.
4. **S1-4 Legacy version 1 isolation.** Accept: the existing arm suites (live, core, library, integration, page) pass
   unchanged; v1 Apply and Update use only the arm path; Save New creates only v2 complete poses.
5. **S1-5 Refusals and recovery.** Accept: Clip Editor Save/Apply, a stale clock on any one of the read or written
   channels, a missing preserved channel, a changed preserved key and the recovery lockout each refuse with nothing
   changed.

A registry change (a qualified-or-experimental `body_krystal_v1` mapping) changes the registry pin in the CPM; it
stays experimental until S3 and S4.

## 6. Proposed amendments to the consolidated design (for adjudication)

These refine Rev 1 with native facts; none contradicts the accepted hybrid architecture.

| # | Amendment | Basis | Adjudication |
|---|---|---|---|
| R1 | Dormant channels (D) are defined by binding: a constrained bone's own control writes its `DmeConstraintSlave` base values, not the bone. They are never written, never counted as writers of the bone, and must stay byte-identical | 3C | Owner |
| R2 | New class **constrained-bone structural offset**: a channel writing an attribute no constraint sets (IK-chain positions). Active, never written, compared to the record (proportions) | 3C | Owner |
| R3 | New class **channel-driven without a control** (A3) | 3A | Owner |
| R4 | Clock rule (E): the qualified rule applies unchanged to every channel the operation reads or writes; §13 item 4 closed as not material | 3B | Owner |
| R5 | Foot helpers are passive followers; there is no foot-roll mechanism on Krystal | Q6 | Owner |
| R6 | The scale-state descriptor includes scale controls and operators, not only scale values | Q12 | Owner |
| A1 | **FK translation:** capture both position and orientation of every included FK control; write orientation always; write position when the record's position differs from the destination's by more than 1e-4 (translation is then a pose input), otherwise leave it (offsets agree). Alternative: write position always (simpler, more keys) | 3D | **Owner and Astra recommended**: it decides whether FK translation counts as pose or as body shape |
| A2 | `Elbow_*_o` and `Knee_*_o`: write them as part of the complete rig-control state (posture-neutral by structure), or preserve them as the qualified arm path does for `Elbow_l_o` | Q5 | Owner |
| A3 | Source-less twist channels: never written; values in the descriptor; Apply refuses on a difference | 3A | Owner |

## 7. Risks

1. **A1 is a product-boundary question** (pose versus body shape for translated FK bones).
2. Evidence covers **one fixture and one SFM process**; S1 refusals are written so that any difference refuses.
3. The S3 destination must be prepared (section 5).
4. The written set (154–282 channels) is about 50–90 times the qualified arm's three channels: Undo size and
   time must be measured in S3 (design R7).
5. The model's `evaluateProceduralBones` value was not recorded; it affects rendering, not the DME transforms.
