# F-01 Broad Full Body Compatibility Review: adjudication package for Astra (2026-11-18)

**Assignment:** "F-01 — Broad Full Body Compatibility Review" (Owner). Diagnosis and design adjudication only. No CPM,
model, session or animation was changed, and no SFM run was made. Current release: v1.1.0 RC2 (unsigned, not
published).

**Authority:** Blueprint R4 (`F01_BLUEPRINT_R4_REVISED_OWNER_REVIEW_20261114.md`), sections 3, 4 and 7, with the
Owner's direction: broad usability, faithful results and actual safety, not theoretical perfection.

**Evidence base (read-only):**
- the RC1 smoke's CPM log (`E:\SFM_U0B_Scratch\f01-v110-rc1-smoke-r1\evidence\logs`, Process A `ac83c6ff…`);
- the unsaved session the Owner used, which is the R2 fixture `259ea8a6…`, never modified;
- both models' `.mdl` files, whose header checksums equal the ones in the log;
- the RC2 source;
- the earlier native model survey (`F01_MODEL_COMPATIBILITY_SURVEY.md`, MC-01–03).

Offline scripts and outputs are in `E:\SFM_U0B_Scratch\f01-broad-compat-review`. Every input is hash-checked before
and after reading.

---

## A. The user-facing problem

An artist poses a common community character and chooses **Save New → Full body**. CPM refuses with:

> Full body can't be saved: parts of this character's body are driven by its rig. Choose Selected parts …

The artist then sees a working-looking Selected parts picker. However, on a rigged character it offers only the
directly controlled extremities: fingers, toes, tails, ears, hair and face. The spine, arms, legs, hands, feet, neck
and head are listed as unavailable ("rig control (not supported in poses yet)" / "driven by the rig"). The pose that
matters, the body posture, cannot be saved at all.

The common SFM workflow is to apply the stock biped rig before animating. Every rigged character is refused unless
it has a hand-written registry profile, and today only Krystal has one. In practice, Full body works only on
**unrigged** characters (the Heavy, the Engineer) and on **Krystal**. That makes the Pose Library a
special-character feature rather than a general one.

## B. Tails and Fox: findings

The Owner tried both in the RC1 production build after the smoke steps. Both animation sets already exist in the
Owner's project at shot15: `milestailsprower1` (GUID `12869e79…`) and `foxmccouldwm1` (`000162e7…`). They are not
new instances. Each Save ended as a cancelled no-op after the refusal, and nothing was written.

### B.1 Observed facts

| | Tails (`models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl`) | Fox (`models/fursonas/foxmccouldwm.mdl`) |
|---|---|---|
| Logged refusal | `rig-driven`: 16 bones listed (the log caps the list at 16), from `prod_scope_compile`, full_body branch | `rig-driven`, same path |
| Second blocker logged | `helper-refused`: 7 control-less bones, "not a declared QUATINTERP helper" | none |
| Rig on the instance | `rig_biped_milestailsprower1`, built by SFM's stock `platform/scripts/sfm/animset/rig_biped_simple.py` | `rig_biped_foxmccouldwm1`, same script |
| Rig structure (fixture) | 19 handles; 34 constraints: 13 point, 17 orient, 4 IK (two-bone arms and legs with elbow/knee poles); `rig_root` drives the model's rootTransform; `rig_footHelper_L/R` follow the feet | **identical topology**, ValveBiped bone names |
| Bones | 131: **22 rig-driven**, **102 directly controlled**, 7 control-less | 112: **22 rig-driven**, **90 directly controlled**, 0 other |
| Control-less bones (model header) | `ear3_L/R`, `HairSpike_B3/M3/T3`, `Tail6_L/R`: all **`JIGGLE`**, leaf bones (flags `0x504`, no physics flags) | none (no procedural bones at all) |
| Other operators | 1 expression (eye convergence), already understood | same |

**For comparison, Krystal in the same session:**
- **Rig:** `rig_biped_Krystal45`, a *customized* biped rig with different handle names (`Hip`, `spine_1–4`, `Hand_l`),
  36 constraints, 21 rig-driven bones, 133 direct bones and 2 control-less twist bones.
- **Generic v3 refuses her too:** in the same log (operations 6 and 7) it gives the same `rig-driven` refusal. Her
  Save succeeds only because the v2 route matches her hand-written profile `body_krystal_v1`.

### B.2 Per-model diagnosis

| Question | Tails | Fox |
|---|---|---|
| Exact refusal and code path | Generic v3: `prod_scope_classify` marks every constraint slave `constrained`; `prod_scope_compile(full_body)` raises `rig-driven`. No v2 profile matches (`prod_pose_registry_select` holds only `krystal-v1`) | same |
| Applied rig, and how the body is driven | stock `rig_biped_simple`: the artist poses 19 rig handles; point and orient constraints copy the handles onto the spine, neck, head, collars and toes; IK solves the arms and legs from the hand and foot handles and the elbow and knee poles | same |
| What CPM can already read and reproduce | 102 direct bones (v3 FK). Every operator and binding of the rig is in the vocabulary that v2's `prod_body_classify` already classifies, verifies and applies for Krystal (point, orient, IK with one target of weight 1, handle hierarchy, helper followers, placement handle, IK offsets, passive bones). This is shown for the same rig script on the Heavy (MC-02: classified from a drafted profile) | 90 direct bones and the same rig vocabulary |
| What causes rejection | (1) no profile for this rig; (2) 7 JIGGLE leaves, which v3 refuses as `carried-unsupported`, behind the rig refusal | (1) only |
| Do the rejected elements matter for faithful reproduction? | (1) **Yes, decisively:** the 22 rig-driven bones *are* the posture. Writing the bones under the rig would be overridden (a misleading result), so the refusal is right *for v3*. The rig handles are the meaningful inputs. (2) **No:** jiggle leaves are secondary, simulated tips with no children, no attachments and no flex drivers | (1) as for Tails |
| Real hazard, or conservative restriction? | (1) v3's refusal prevents a misleading partial result (**necessary for v3**). The absence of any route other than a per-character profile is a **conservative eligibility restriction**. (2) Refusing jiggle leaves protects nothing concrete: writing them is not needed, and leaving them is what SFM does anyway | (1) as for Tails |
| Does Selected parts suggest reusable support? | Only for the 102 direct bones. Rig handles are not offered. No | same |

**Hypotheses, not yet observed:**
- **H-1:** a profile drafted from the scene's own graph would classify Tails and Fox exactly as it classified the
  rigged Heavy. Basis: same rig script and same vocabulary. Not run on these instances.
- **H-2:** Tails' jiggle leaves would pass v2's existing `passive` class (one source-less channel per attribute).
  Basis: CPM's own log classified them as carried candidates, which requires exactly that representation.
- **H-3:** the stock rig's handle-space Apply composes correctly under P7, as it does for Krystal's rig. Not observed
  on `rig_biped_simple`.

## C. The current architecture, briefly

| Route | Admission | Capture and Apply | Verification |
|---|---|---|---|
| **v3 generic** (`direct_fk_v1` rev 1, qualified) | Every bone is direct FK: one control's own channels, sole writer, no constraint. Face-group bones are offered for review. Control-less bones refuse unless H1 admits them | bone local channels; root translation per R3/A1; placement and proportions preserved | P7: exact authored keys and skeletal results within tolerances |
| **H1 exception** (inside v3) | a control-less leaf declared `QUATINTERP` + `BONE_ALWAYS_PROCEDURAL` in the header, with a direct-FK parent and no attachment or flex-driver use | not written; outside the written set; preserved | excluded from the rendered-result comparison only |
| **v2 Krystal** (registry profile `body_krystal_v1`, qualified) | the live rig must equal the profile *exactly*: rig name, handles and parents, constraint list, written and preserved handle channels, placement handle, helper handles, passive and preserved bones. Everything else is classified from evidence (`prod_body_classify`) | rig handle channels + direct FK bones in one record, with a structural descriptor | descriptor equality at Apply; P7 skeleton composition through the rig |
| **Shared safeguards (all routes)** | selected-instance authority; sole-writer and shared-log checks; no fallback after a failed Apply | one owned transaction (P1–P7); verified Abort; recovery lockout; deferred verification; `committed-unverified` never shown as success | |

## D. Compatibility barriers, classified

| # | Barrier | Where | Class |
|---|---|---|---|
| 1 | v3 refuses constrained bones | `prod_scope_classify` / `compile` | **Necessary for faithful reproduction**: writing rig-overridden bones would mislead. Keep |
| 2 | A rigged character needs a hand-written registry profile | `prod_pose_registry_select`; `prod_body_classify` profile equality | **Potentially excessive admission restriction.** The profile repeats facts the classifier already derives and checks from evidence. The survey drafted Krystal's profile from structure, equal in every field except `preserved_fk_bones` |
| 3 | Rig name compared literally (`rig_biped_<animset>`) | profile and descriptor | **Potentially excessive.** It ties a pose to the animation set name at rig time, so a second instance refuses |
| 4 | Jiggle leaves refuse Full body | v3: `carried-unsupported`; H1 admits only QUATINTERP | **Potentially excessive** for leaf jiggle bones with no consumers (Tails). **Necessary** to keep refusing non-leaf jiggle chains, physics-flagged bones, or bones used by attachments or flex drivers |
| 5 | Constraint vocabulary: point, orient, IK; one target; weight 1; handles parented to the rig or a handle | `prod_body_classify` | **Necessary safety and faithfulness.** Multi-target or weighted constraints, cross-character or prop targets, and aim, parent or twist operators change meaning. Keep refusing |
| 6 | Bone-parented rig handles (DAZ-style finger and toe handles) | profile parent forms | **Unresolved, pending evidence** (survey MC-03; P7 composition for handles under bones untested) |
| 7 | Reverse-foot rigs (heel attachments, foot-roll constraints) | not observed | **Unresolved, pending evidence** |
| 8 | Facial FK bones on rigged models | v3 review by Face group; v2 `preserved_fk_bones` from the profile | **Necessary protection** (expressions are not poses); the mechanism must not depend on a hand-written list |
| 9 | Sole writer, shared logs, one channel per attribute, mode-3 single layer | both routes | **Necessary safety** (authored-data and recovery integrity). Keep |
| 10 | `unknown_operator_types` document-wide refusal | `prod_body_classify` | **Inert:** the list is never filled. No change needed; noted so it is not mistaken for a barrier |
| 11 | Descriptor requires the same `model_ref` | `prod_body_descriptor` | **Necessary today** (cross-model retargeting is out of scope in R4) |

## E. Smallest practical expansion options

All of these reuse the existing v2 classifier, descriptor, planner, transaction and P7 code. None is
character-specific, and none interprets procedures.

**Option 1 (recommended): a discovered rig description in place of a registry profile.**
At Save, CPM drafts the v2 profile from the live instance by fixed structural rules:
- handles and parents;
- the constraint list;
- helpers = constrained handles that are not targets;
- placement = the handle constraining the model's rootTransform;
- written handle channels = the control channels of core handles; preserved = placement and pole orientations;
- passive = source-less control-less bones;
- face = the existing v3 Face-group review.

The draft feeds the unchanged `prod_body_classify`, and the descriptor is stored in the record (the existing v2
format). At Apply, the destination's drafted description must equal the saved one exactly, with the rig name
normalized to its structure. Anything outside the vocabulary (barrier 5) still refuses. **Covers Tails and Fox
(barrier 2, with 3), the rigged Heavy, and Krystal** without her hand-written profile; existing Krystal records stay
readable.

**Option 2: leaf jiggle bones as SFM-managed outputs (barrier 4).**
- Admit a control-less **leaf** bone declared `JIGGLE` in the header, under H1's existing conditions: header matches
  the scene, direct-FK or rig-driven parent, no children, no attachment or flex-driver use, no physics or
  screen-align flags.
- Never write it, keep its channels in the preservation checks, and exclude only its rendered result.
- This is the H1 mechanism with one more declared proctype, not a jiggle interpreter.
- **Covers Tails' 7 bones;** probably also Ayane's 8 passive jiggle bones (survey) if they are leaves.

**Option 3: rig-name normalization (barrier 3).** Compare structure, not the `rig_biped_<animset>` string. It is
part of Option 1, and could ship alone for Krystal.

**Not proposed now:**
- bone-parented handles (6) and reverse foot (7): each needs one native observation first;
- multi-target, weighted, aim or parent constraints;
- cross-model retargeting.

## F. Questions for Astra's ruling

1. **Admission:** may the registry-profile requirement (barrier 2) be replaced by a description drafted from the
   instance and matched exactly at Apply (Option 1)? The vocabulary (barrier 5), sole-writer and recovery
   safeguards (9) and face protection (8) stay. Which, if any, of the registry's remaining roles (explicit
   refusals, tolerances) should stay?
2. **Rig-driven characters:** is capturing and reapplying the **rig handles** (the artist's meaningful controls),
   with rig-driven bones verified through P7 and never written, the endorsed contract for rigged Full body?
3. **Secondary procedural outputs:** may control-less **leaf** `JIGGLE` bones remain under SFM control inside Full
   body, under H1's conditions (Option 2)? Must non-leaf jiggle chains and physics-flagged bones keep refusing?
4. **Evidence for a safe Save/Apply contract:** is the following sufficient?
   - offline suites for the drafting rules and refusals;
   - one native Owner-operated check on a `rig_biped_simple` character (Fox: Save, restart, Apply to a visibly
     different compatible instance, Undo/Redo, a peer left unchanged);
   - one on Tails for the jiggle leaves;
   - a Krystal re-check under the drafted description.

   Reuse unchanged transaction, Abort and recovery evidence.
5. **Reproduction failure versus harmless difference:**
   - **Failure:** a rig-driven or direct bone outside P7 tolerance; a handle, placement or proportion change; any
     write to a preserved, peer or face input.
   - **Harmless:** a jiggle or QUATINTERP output that differs, with its channels unchanged. Should Astra define
     tolerances per class?
6. **Smallest implementation and qualification strategy:**
   - Option 1 + Option 3 as one bounded milestone, with Option 2 as a separate small rule;
   - then, each only after its own native observation, bone-parented handles and reverse foot.

   Is that the right order and boundary?

**Requested from Astra:**
- an explicit recommended design;
- the safeguards that must be retained;
- the limitations permitted;
- the implementation boundaries, including what stays out (barriers 6 and 7, retargeting, new frameworks).

---

**No additional native observation is needed for this adjudication.** The diagnosis rests on the logged refusals,
the fixture's own rig graph and the model headers. H-1 to H-3 would be settled by the qualification proposed in
F4, after the ruling and Owner approval.

**Stopped here for review.** No implementation, production change, signing, push, merge, tag or release.
