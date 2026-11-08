# F-01 Pose Library — Native Model Compatibility Survey: Results and Assessment

**Date:** 2026-11-07. **Status:** investigation complete. Nothing was implemented. CPM is unchanged (candidate
`f6098b3a…`), nothing was installed, and the published CPM `ccbed9d7…` stayed in place and was not opened. The
proposal is in `F01_MODEL_COMPATIBILITY_ASSESSMENT.md`. The kit is `real_sfm_qualification/f01_model_survey/`
(commit `b04729b`).

## 1. Native evidence

The run folder is `f01-model-survey` (the Owner's local scratch archive, not committed). All three observations come
from one SFM process (pid 35164) and one new session.

| Obs. | Animation set | Model | Rig | Bones | Rig handles | Controls | Channels | Operators | Flex | SHA-256 |
|---|---|---|---|---|---|---|---|---|---|---|
| MC-01 | `heavy1` | `models/player/heavy.mdl` | none | 79 | 0 | 126 | 211 | 1 | 46 | `f94185a8…` |
| MC-02 | `heavy1` | same | `rig_biped_heavy1` (`rig_biped_simple`) | 79 | 23 | 181 | 289 | 37 | 46 | `569a7222…` |
| MC-03 | `ayane_dazv51` | `models/lordaardvark/sfm/deadoralive/fantasy/ayane_dazv5.mdl` | `rig_biped_ayane_dazv51` (`rig_biped_daz_v5`) | 165 | 73 | 436 | 727 | 137 | 112 | `6b1f09bd…` |

**Read-only proof.** Every observation has `readonly.unchanged = true` (the document digest of every key, and the
session state, are equal before and after) and `problems = 0`. MC-01 holds one expected finding: "expected one rig
registration for the animation set, found 0".

**Preparation changes,** made by SFM itself in the disposable session and kept separate from the observations:
- the new session;
- two models added;
- two rigs applied.

**SFM warnings.** Applying `rig_biped_simple` to the Heavy printed "model is missing heel attachment point"
for `pvt_heel_R` and `pvt_heel_L`. The script (`CreateReverseFoot`, identical in `usermod` and `platform`,
`9a59eac4…`) then skips the reverse foot. Whether SFM printed the same warning for Ayane was not reported.
`rig_biped_daz_v5` (`ab7cec06…`) has the same check.

**Postflight.**
- `post` put back SFM's rewritten housekeeping files (`demoheader.tmp`, `tf2_playerstats.dmx`).
- All four protected inventories equal their baselines.
- The CPM, the kit, the models and the rig scripts are unchanged.
- Its single reported problem is deviation MC-D3.

**Deviations** (`evidence\DEVIATIONS.json`, all preserved):
- **MC-D1:** the procedure wrongly assumed that File > New would offer a folder. SFM created the session in its
  default sessions folder.
- **MC-D2:** the Owner saved the disposable session at the end.
- **MC-D3:** with Owner approval, `mc_survey.dmx` (`47f6b9a0…`) and `mc_survey.autosave` (`7b6de455…`) were moved to
  `sessions\saved_by_operator\`. Each copy was verified byte-identical before the original was removed, and the
  protected sessions folder then equalled its baseline (`evidence\relocation.json`).

None of these affects the observations, which were taken before the save.

**Evidence identities:**

| File | SHA-256 |
|---|---|
| `MC_PROBE.json` | `ca93762e…` |
| `MC_HYPOTHETICAL_MC03_PARENTING.json` | `44ea8f2d…` |
| `post.json` | `3930a172…` |
| `relocation.json` | `52b850ec…` |
| `DEVIATIONS.json` | `cb494330…` |

**Offline analysis:**
- **The probe** (`evidence\MC_PROBE.json`, `MC_PROBE.md`) ran CPM's own stage E classifier against a profile drafted
  from structure alone.
- **One hypothetical** (`evidence\MC_HYPOTHETICAL_MC03_PARENTING.json`) is clearly labelled.
- **Krystal's S0 run 2 observations** served as the control case.

## 2. Per-model coverage and refusals

**Control case, Krystal (S0 run 2).** The profile drafted from structure equals the hand-authored `body_krystal_v1`
in every field except `preserved_fk_bones` (jaw and tongue). That covers:
- handles and parents;
- the 36 constraints;
- the four helpers;
- the placement handle;
- the 30 written and 6 preserved handle channels;
- both passive twist bones.

The classifier accepts both, and CPM's descriptor builds from the draft.

| | MC-01 Heavy, no rig | MC-02 Heavy, `rig_biped_simple` | MC-03 Ayane, `rig_biped_daz_v5` |
|---|---|---|---|
| Classifier, drafted profile | **REFUSED** `rig-differs`: "rig registration [] (0)" | **CLASSIFIED**: 144 written channels (108 FK, 36 handle); 23 constrained, 54 FK and 2 passive bones | **Not expressible**: 20 rig handles (`rig_finger*`, `rig_toe*`) are parented to hand and toe **bones**; the profile can name only the rig or a rig handle |
| Next refusal behind the first | none (the same rule) | — | **Hypothetical,** bone parents accepted: **CLASSIFIED**, 304 written channels (168 FK, 136 handle); 73 constrained, 84 FK and 8 passive bones. Nothing else refuses |
| Operator types | 1 expression (eye convergence) | point 14, orient 18, IK 4, expression 1 | point 64, orient 68, IK 4, expression 1 |
| Unknown operators in the document | none | none | none |
| Bone classes (census) | 77 FK (one control channel each), 2 passive (`hlp_forearm_L/R`) | 23 constrained, 54 FK, 2 passive | 73 constrained, 84 FK, 8 passive (jiggle) |
| Placement reference | the model's own `rootTransform` control writes the model transform; root bone `bip_pelvis` | `rig_root` (derived) | `rig_root` (derived) |
| Gaze | the `viewTarget` transform control, classified preserved | same | same |
| Face | 46 flex controllers, preserved by the existing rule; no facial bone is written | same | 112 flexes preserved; **43 facial FK bones would be written** |
| Scale | model scale and bone scales recorded; no scale channels on bones | same | same |

**What CPM already classifies correctly,** on all three:
- FK bones driven by one control channel;
- point, orient and IK constraints with their slave and weight channels;
- IK offsets, passive (source-less) bones, rig handles and helpers;
- flex controls and the eye target, as preserved non-bone destinations.

**The demonstrated refusals in CPM today:**
- there is no rig (MC-01);
- rig handles are parented to bones (MC-03);
- the Krystal-specific requirement: the model, rig name, handle set, constraint list and facial list must equal a
  hand-written profile. Neither the Heavy nor Ayane has one, so production refuses both before classification even
  starts.

## 3. Common limitations and findings

1. **Rig names are per instance.** Both scripts call `BeginRig("rig_biped_" + animSet.GetName())`, giving
   `rig_biped_heavy1` and `rig_biped_ayane_dazv51`. A descriptor that compares rig names literally ties a pose to the
   animation set's name at rig time. A second instance of the same model would then refuse. This is shown from the
   script source and the observations; a native second-instance test was not run.
2. **Facial preservation can't come from structure, and names alone are not enough.**
   - On Ayane, the 43 facial FK bones (jaw, tongue, eyeballs, eyelids, brows, cheeks, lips) look structurally
     identical to body FK bones.
   - Every one of them is in Ayane's `Face` control groups (Upper, Mid and Lower Face, Eyes, Tongue). No body bone is.
   - On Krystal, name matching also flags 15 hair bones (`bip_head_hair*`).
   - The Heavy's face is flexes only, so nothing is at risk there.

   Control-group membership is therefore the best evidence observed. Its origin (SFM's default animation groups, or
   the model's own definitions) was not established.
3. **Gaze:** the `viewTarget` transform is preserved on all models. Ayane's eyeball **bones** are FK bones, so a
   pose would turn her eyes unless they are preserved.
4. **Props and attachments are FK bones.** The Heavy's 19 `prop_*`, `weapon_*` and `prp_*` bones, 3 attachment
   bones and 2 clothing bones would be written as part of a pose. That may or may not be wanted; it is a policy
   question, not a refusal.
5. **Reverse foot: untested.**
   - Neither model has the heel attachments, so neither rig built foot-roll rotation constraints or connection
     operators.
   - Every operator in all three observations is one CPM already understands.
   - Whether reverse-foot rigs refuse remains an untested assumption. Demonstrating it needs a model with
     `pvt_heel_L/R` attachments.
6. **Bone-parented rig handles.** The DAZ rig parents finger and toe handles to bones. Accepting them needs a
   profile parent form for "bone" and an oracle that composes those handles through the posed skeleton. The latter
   is untested: nothing in this survey exercised P7's skeleton verification for handles under bones.
7. **FK-only support is structurally simple.**
   - All 77 animated bones of the unrigged Heavy have exactly one control channel.
   - The model has its own placement control (`rootTransform`).
   - The missing piece is a defined placement frame for the oracle, not classification.

## 4. Smallest generalization milestone

**"Discovered rig description, same model, same instance structure."**
1. **At Save New:** CPM drafts the profile from structure, by exactly the rules the probe used, and stores it in
   the version 2 record as the pose's descriptor. The rules are:
   - parents and constraints;
   - helpers = constrained handles;
   - placement = the single unconstrained handle under the rig, or `rootTransform` without a rig;
   - written and preserved handle channels;
   - passive bones.
2. **At Apply:** the destination's drafted description must equal the saved one, compared by roles and structure.
   The rig name is normalized by its animation-set suffix. Any difference refuses.
3. **Facial preservation by control group:** an FK bone whose control is in a Face group (or another policy-named
   group) is preserved. When groups are absent, or a facial group cannot be resolved, the pose refuses rather than
   writes the face.
4. **Refusal copy names the reason:** no rig, an unsupported rig feature, a different rig, the face cannot be
   protected.
5. **Out of the first milestone:** bone-parented handles (DAZ), reverse foot and FK-only placement each follow as a
   separate, natively qualified extension.

With items 1–4, the survey data say the rigged Heavy would be supported. Krystal's own profile would become
redundant.

## 5. Choices for Astra's adjudication

1. **Compatibility authority:** a discovered description in the pose, matched exactly, in place of registry
   profiles. The registry would keep only explicit refusals and tolerances.
2. **Facial policy:** preserve FK bones in Face control groups. Decide what counts as a facial group and what
   happens without groups (refuse, or write).
3. **Rig-name identity:** whether `rig_biped_<animset>` is normalized, or rig identity is purely structural.
4. **Props and attachments:** write `prop_*` and weapon bones with the pose, or preserve them by group (`Other`,
   `Attachments`, `Clothing`).
5. **FK-only placement frame:** the model `rootTransform`, and whether A1's tolerance applies by default.
6. **Bone-parented handles:** the scope and oracle design for DAZ-style rigs.
7. **Reverse foot:** treat foot-roll rotation constraints and connection operators as rig-internal (preserved), or
   refuse. This needs one more native observation of a model with heel attachments.

## 6. Recommendation

1. Implement the milestone in section 4 for rigged models of the `rig_biped_simple` family, with group-based
   facial preservation. Qualify it natively on the Heavy and re-qualify Krystal under the discovered description.
2. Then, in order: FK-only models, DAZ bone-parented handles, and reverse foot. Each of these needs Astra's
   decision first.
