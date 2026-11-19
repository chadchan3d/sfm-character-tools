# F-01 Stage 2: declared JIGGLE leaf compatibility, bounded implementation scope (prepared 2026-11-19)

**Authority:**
- Astra's ruling (`F01_STAGE2_ASTRA_JIGGLE_RULING.md`, the original adjudication).
- Blueprint R4, sections 3, 4, 8, 9 and 10.
- The Owner/Designer's "F-01 Stage 2 — Recover Astra's Existing Ruling".

**Status: scope only.** No code was written. Implementation needs the Owner's separate authorization.

**Base:** Stage 1 is closed (`F01_STAGE1_RECOVERY_CHECK_RESULTS.md` section 6). The candidate is CPM
`7259e80a5d462eba1aeaa25cf89e9f57cf1081caaeac3002de8db6fbe488ab55`, with the structural rig adapter
`structural_rig_v1` revision 1 (experimental).

## 1. Objective

Tails is refused today, and only because of seven control-less leaf JIGGLE bones. The objective is a faithful Full
body pose for Tails, and for any character with the same structure, through the Stage 1 structural rig adapter. The
JIGGLE leaves stay under normal SFM control: CPM never writes them and never requires their simulated transforms to
be identical. Their authored channels, keys and configuration stay protected.

## 2. The observed case: Tails (read-only evidence)

| Fact | Evidence |
|---|---|
| Model: `models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl`, 131 bones. Rig: stock `rig_biped_simple`, the same topology as Fox: 22 rig-driven bones, 102 directly controlled bones and 7 control-less bones. | `F01_BROAD_FULL_BODY_COMPATIBILITY_REVIEW.md` B.1 |
| The control-less bones are exactly the 7 header-declared `JIGGLE` bones: `ear3_L/R`, `HairSpike_B3/M3/T3`, `Tail6_L/R`. | B.1; model header |
| Each is a **leaf** in the header. Its parent is an ordinary, non-procedural bone: `ear2_*`, `HairSpike_*2` or `Tail5_*`. All 7 parents are directly controlled; none is rig-driven. | Model header, re-read on 2026-11-19 (file `6f2a5ea7…`, unchanged) |
| Flags are `0x504` on all 7: `BONE_ALWAYS_PROCEDURAL` plus the hitbox and vertex-LOD0 usage bits. There are no physics or screen-align flags, and the "used by attachment" bit is clear. | Model header |
| The RC1 smoke log already reports them in the v3 path: `helper-refused`, "not a declared QUATINTERP helper". | B.1 |
| Natively established elsewhere: `vs.studio` exposes the procedure constants, including JIGGLE = 5. Jiggle bones on Ayane (also `0x504`) move visibly when rendered while their channels stay constant. | `F01_NQ03_RESULTS.md`; `F01_SFP1_NQ_S6_INVESTIGATION.md` |

Stage 1 refuses Tails at `prod_body_rig_draft` step 7 ("control-less bones … are outside Stage 1").

## 3. What changes

### 3.1 Admission: by mechanism and relationships, never by name or model

In `prod_body_rig_draft`, a control-less bone is admitted as a **simulated leaf output** only when all of the
following hold. In every other case, Stage 1's refusal stands unchanged.

1. **Control-less:** exactly one source-less transform channel per attribute, the bone's only writers, and no
   constraint slaves it. This is the shape `passive` checks today.
2. **Model and header identity:** the studio header is read through the existing read-only
   `prod_scope_helper_evidence` (`GetStudioHdr`; bones, attachments, flex drivers; `vs.studio` constants). It must
   match the scene skeleton exactly by index, name and parent. Unreadable or mismatched evidence admits nothing.
3. **Declared JIGGLE:** `proctype == STUDIO_PROC_JIGGLE`, with `BONE_ALWAYS_PROCEDURAL` set and none of
   `BONE_PHYSICALLY_SIMULATED`, `BONE_PHYSICS_PROCEDURAL` or the screen-align flags (H1's flag rule; the constants come
   from `vs.studio`).
4. **Leaf:** it has no child in the scene and none in the header. Non-leaf jiggle chains keep refusing.
5. **Parent:** a bone of a qualified class in the drafted description: written or preserved FK, or rig-driven
   (`constrained`, which Astra accepts). Tails exercises only the FK parent; the rig-driven parent is covered
   offline.
6. **Isolation:**
   - no local attachment and no bone flex driver uses it (header);
   - no scene dependency reads it: no channel takes its transform as a source, no constraint uses it as a target, and
     no operator reads it;
   - no channel outside the instance writes it (the existing authority check).

   The implementation first confirms which of these reads the existing discovery and authority evidence already
   covers. A narrow read check is added only for one it doesn't cover (R4 section 4: inspect only concrete
   relationships).

The new class has its own name, proposed as `simulated-leaf`. It is **not** `passive`, as Astra rules. No list of
character, model or bone names is added anywhere.

### 3.2 Obligations: the narrow output exemption

| Stage | `passive` today | `simulated-leaf` |
|---|---|---|
| **Capture compatibility** (descriptor, Save/Apply match) | Class, roles and the channels' **values** are compared exactly | Class, roles, log and layer types, parent and index compared exactly. **Channel values are not compared**: the destination keeps its own authored values. The destination must admit exactly the same simulated leaves. |
| **Expected skeleton / P7** | Parent's expected transform composed with the bone's unchanged local transform; world within tolerance; local unchanged | **No transform obligation**, neither world nor local. Scale is still checked (configuration). |
| **No-op** | Skeleton verification includes the bone | Excluded from the skeleton test only; key coverage is unchanged. |
| **P2 / Abort recovery** (`prod_body_same_state`) | Through the descriptor and authored state | Authored state is exact: its channels' logs, keys, times, defaults, metadata and layers, as for every channel. Configuration (scale, parent, identity, authority, header declaration) is exact. No transform comparison. |
| **Writes** | Never written | Never written: outside W and A, with no saved value or oracle and no carried constant. |
| **Header** | Not read | Read again at P2 and P7. A changed declaration refuses before Undo (P2), or gives `committed-unverified` (P7). |

Unchanged:
- A1 FK-position compatibility and the effective-input check (they cover only owners of written channels);
- the exact authored comparison and the observed operator capture;
- the Undo and ownership rules, verified Abort, recovery lockout and the Redo-history exception;
- every tolerance.

### 3.3 Record contract (R4 section 8)

- **Revision 2:** a structural record that contains at least one `simulated-leaf` bone is written as
  `structural_rig_v1` **revision 2**, with the class in the descriptor's bone rows and no new record fields.
  Records without one stay revision 1, byte-identical in form (Fox's records are unaffected).
- **Older readers:** they refuse revision 2 (`prod_body_rig_usable` accepts only revision 1), and the closed
  schema refuses the unknown class. Neither can misapply it.
- **This build:** it accepts both revisions, 1 for records without simulated leaves and 2 for records with them.
  A revision 1 record with a simulated leaf, or a revision 2 record without one, refuses.
- **Validator:** `prod_body_rig_validate` accepts `simulated-leaf` only in revision 2, only as a leaf under a
  qualified parent, and never as written or preserved channels. Saved metadata never authorizes a write: the
  destination's own draft does.
- **Existing records:** registry (Krystal v2), v1 and v3 records and the H1 `engine-helper` role keep their
  interpretation unchanged.

### 3.4 User interface

No new message or dialog.
- Characters that don't qualify keep the existing "Full body poses aren't supported for this character yet" refusal,
  with the cause in the log (`structure-unsupported` naming the bone and the failed criterion).
- The log gains one admission line per draft, naming the admitted simulated leaves (`BODY-RIG-available` detail).
- No Save note, following the Owner's RC1 UI decision for helper notes.

### 3.5 Production status

Like Stage 1, this is experimental: usable in the qualification build only, behind `PROD_BODY_RIG_STATUS`. Production
promotion stays a separate Owner decision.

## 4. Out of scope

- Non-leaf jiggle chains, physics-flagged or physics-procedural bones, screen-align bones, and every other procedure
  type in the structural route.
- The v3 scope route and H1: JIGGLE remains unadmitted there, and the H1 suite stays unchanged. Admitting JIGGLE
  leaves for unrigged characters would be a separate decision.
- A jiggle simulator, rendered-matrix reading, baking, or switching procedural bones off.
- Krystal's registry route and profile, unchanged.
- Bone-parented handles, reverse feet, weighted or multiple-target constraints, and cross-model retargeting
  (excluded since Stage 1).
- Selected parts, which already lists control-less bones as unavailable; unchanged.
- No exploratory model survey.

## 5. Offline qualification plan

**Fixture.** A Tails fixture read only from the R2 fixture session `259ea8a6…`, the Owner's unsaved session that
contains `milestailsprower1` at shot15.
- It uses the existing `f01_dmx_body_fixture.py` reader, as Fox's fixture did.
- It adds a native-shaped header for the scene (bones, flags, proctype, attachments, flex drivers), taken from the
  model file read only.
- Inputs are hash-checked; nothing is modified.

**Suite.** A new `test_cpm_app_f01_jiggle_leaf.py`, on Python 2.7.5 and 3.10.6, covering:

- **Admission:** exactly Tails' 7 bones; the class name `simulated-leaf`; no `passive`.
- **Refusal,** one variant per criterion, each writing nothing:
  - a physics flag;
  - a screen-align flag;
  - `ALWAYS_PROCEDURAL` absent;
  - another procedure type;
  - a non-leaf chain, once in the scene and once in the header;
  - an attachment;
  - a flex driver;
  - a channel reading the bone;
  - a constraint targeting it;
  - a foreign writer;
  - an unsupported parent;
  - a header that is mismatched, renamed or reordered;
  - an unreadable header or constants.
- **Rig-driven parent:** a variant where the leaf sits under a `constrained` bone is admitted.
- **The exemption:** at no-op, P2, P7 and after Abort, a simulated leaf's world and local transforms differ from
  expectation and nothing refuses. The same difference on its FK parent or on a rig-driven bone still fails.
- **Authored protection:**
  - a changed key, default, metadata or layer on a simulated leaf's channel refuses at P2, and is caught by P7 and
    after Abort;
  - a changed scale refuses;
  - a header declaration changed between P1 and P2 refuses before Undo; between commit and P7 it gives
    `committed-unverified`.
- **Records:**
  - Save writes revision 2 with the 7 bones;
  - a destination with different authored jiggle values applies;
  - a destination with one jiggle leaf fewer, or one more, refuses;
  - a revision 1 reader and the RC2 source refuse the record;
  - a forged record (a simulated leaf claimed as written, or revision 1 carrying the class) refuses.
- **Transaction:** a verified Apply writes only the planned channels; Undo and Redo are exact; a true no-op stays a
  no-op; a partial-write fault gives a verified Abort, and a pending Redo gives `redo_cleared`.
- **Teeth:** with the admission disabled, Tails refuses exactly as in Stage 1. Classifying the leaves as `passive`
  fails the simulated-transform variants.

**Regressions:**
- structural rig (147), Stage 1 Abort history and recovery (section O, scoped L, pose D8R);
- H1 helper (78), scoped poses, body stage E, the Krystal registry route and the RC2 production behaviour;
- the full regression, compared with the 2026-11-19 baseline.

## 6. Native qualification (proposal only; not authorized)

Astra's requirement: Tails through the same adapter. The proposed shape is the Fox run 3 kit with Tails instances:
- Save once.
- Restart.
- Apply to a second, visibly differently posed `milestailsprower` instance.
- Undo and Redo.
- Navigate (scrub away and back).
- Abort cases are not repeated: the transaction and recovery evidence is reused.

Checks:
- **Automated:** meaningful posture through P7; the jiggle leaves' channels and keys unchanged at every capture;
  the peer and source unchanged; exact restoration. No identical simulated tip transform is required.
- **Owner, visual:** useful posture and no severe deformation; minor jiggle differences are acceptable.

## 7. Native uncertainties

1. **Where the simulated motion appears.** Ayane's rendered jiggle moved while her channels stayed constant
   (NQ-S6). Whether the DAG transforms that discovery reads also move after scrubbing is not established. The
   exemption is required either way. Its native effect is that a moving tip is never reported.
2. **Stability between reads.** If simulated transforms change between P1 and P2 without any edit, only the
   exempted bones may differ. A difference on any other bone still refuses, which the native run observes.
3. **Rig-driven parent.** Tails doesn't exercise it, so it rests on offline evidence until a native case arises.

## 8. Expected footprint

- **The adapter** (`prod_body_rig_*`, part 4 of stage E):
  - the admission;
  - the header read;
  - revision 2, with `prod_body_rig_usable` accepting revisions 1 and 2, and the validator.
- **Stage E,** one narrowly scoped change each, all inert without a `simulated-leaf` bone:
  - the class in `PROD_BODY_BONE_CLASSES`;
  - its classification;
  - its descriptor rows;
  - its exclusion from `prod_body_expected_skeleton` and `prod_body_verify_skeleton`.
- **Tests:** one new suite and one fixture.
- **No change** to the transaction, Abort, lockout, UI or registry.

Each changed check is listed in the implementation record with its exact diff.

## 9. Restrictions

Stopped before Stage 2 coding, pending the Owner's separate implementation authorization. No production promotion,
signing, push, merge or release. The Stage 1 closure and all historical evidence are preserved unchanged.
