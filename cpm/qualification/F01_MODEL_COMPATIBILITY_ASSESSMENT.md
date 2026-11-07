# F-01 Pose Library — Krystal Closure and Model Compatibility Assessment

**Date:** 2026-11-07. **Status:** assessment only. Nothing has been implemented or run natively, and no installation
was changed.

## 1. Krystal closure

Krystal's complete Pose Library workflow is natively qualified. The record is
`F01_FULL_BODY_S3_ASSESSMENT.md` (`f0df89c2d60387879d692b27a1cb335605d080de`): S3 runs 1–5. Each run's evidence and
verdict are preserved; run 3's own verdict stays FAIL (procedural).

| Item | Identity |
|---|---|
| Model | `models/fursonas/starfox/krystal/bodies/krystal2020.mdl` (rig class `krystal-v1`) |
| Rig | `rig_biped_Krystal45`: 22 handles, 36 constraints (point, orient, IK) |
| Body profile | `body_krystal_v1` in `cpm_body_profiles_v1.json` `22dcd1599c0556bcb71df0a9b9d14657684173b3bbf557250710a8104a6baa26`; the full-body mapping is recorded `experimental` in the shipped file |
| Pose registry (left arm qualified) | `cpm_pose_profiles_v1.json` `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| Qualified candidate | CPM `f6098b3a61bbc17b435205741761cf6993fc726d94b575d2c9a4fd600eb4e6e9` (`e98b90b`); qualification build `12b59b29…` |

**Local development status: Krystal full body QUALIFIED.** Promoting the mapping to `qualified` in the registry
changes the registry's hash, and so the CPM pin. That belongs to release preparation, with a final candidate and a
production smoke test, and has not been done.

## 2. What generalizes today

| Layer | Status | Notes |
|---|---|---|
| Discovery: bones, scene, channels, controls, operators, the document-wide writer index | **Model-independent** | It reads any instance; the S0 survey proved the same reads natively |
| Time mapping, the Motion Editor and clock gates, ownership and authority, the key planner, the P1–P7 transaction (one owned Undo, Abort, recovery pause, deferred verification) | **Model-independent** | Nothing in the transaction knows Krystal |
| Version 2 record, library, Poses page, Save New / Update / Apply | **Model-independent** | The record carries the profile id and rig class |
| FK bones | **Generic rule** | Any bone driven by exactly one transform control channel is classified FK and written |
| Placement-relative oracle and skeleton verification | **Generic, given a placement handle** | Needs a reference frame (Krystal: `rig_root`) |
| Compatibility descriptor (proportions, scale state, IK offsets, passive values) | **Generic, compared same-model** | It compares the destination with the saved instance; it is not Krystal-specific |
| A1 FK-position tolerance | **Per profile** | `body_krystal_v1` 0.00005; any other profile is exact |

## 3. What is Krystal-specific

**Data** (per model in the registry):
- the exact model path (rig class);
- the rig name;
- every rig handle and its parent;
- the exact constraint list;
- the written and preserved handle channels;
- the placement handle;
- the helper handles;
- the passive twist bones;
- the preserved facial FK bones (jaw, tongue);
- the A1 tolerance.

**Engine limits.** These would refuse other rigs even with a profile:
1. **Exactly one rig registration is required.** A model without a rig (FK controls only) refuses with
   `rig-differs`. It also has no placement handle for the oracle frame.
2. **Only point, orient and IK constraints, plus expression-driven scale, are understood.** Valve's standard
   `rig_biped_simple`, and the DAZ v5 and Mixamo rigs built from it, add a reverse foot when the model has the bones.
   The reverse foot uses expression operators and rotation constraints for foot roll, which refuse today as
   `structure-unsupported`.
3. **Every handle and constraint must equal the profile exactly.** The installed rigs differ in names and counts:
   `rig_biped_simple` has `rig_footHelper_L/R`, Krystal's rig `rig_footHelper0–3`, and the DAZ v5 rig 68 constrained
   handles. A profile written by hand for each model would not meet the goal that artists need no configuration.
4. **Facial preservation comes from a named bone list.** Without it, a model's jaw, tongue and eye FK bones would be
   written as pose bones and change the expression.
5. **Unsupported models get a useful but generic message:** "Poses aren't available for this character yet."
   Nothing says *why* (no rig, an unknown rig feature).

**Observations of the installation (read-only):**
- 137 rig scripts are installed; most of the `rig_biped_*` family share the `sfmUtils` building blocks
  (`CreateConstrainedHandle`, `CreatePointOrientConstraint`, `BuildArmLeg`, `CreateReverseFoot`).
- The CPM library already holds Nika Shark, `ayane_dazv5`, `mia` and `krystalv2`.
- Valve's TF2 player models (`tf/models/player/heavy.mdl` and others) are installed.

## 4. Representative test models

| Type | Model | Rig | Why |
|---|---|---|---|
| Conventional SFM humanoid | `tf/models/player/heavy.mdl` | Valve `rig_biped_simple` (Rig menu) | The standard rig on a stock model every SFM user has, with facial flexes and bones |
| Primarily FK controls | the same `heavy.mdl`, **without** a rig | none (bone controls only) | The same model isolates the FK-only path |
| Custom IK rig, substantially different | `ayane_dazv5` (already in the CPM library) | `rig_biped_daz_v5` (68 constrained handles, reverse foot) | A larger rig of the same family, with features Krystal's rig lacks |

## 5. The smallest read-only investigation (proposed; needs authorization)

**Native part:** one SFM process and one new, unsaved scratch session. Nothing is installed, and CPM is not opened.
The observer is the S0 survey, unchanged: read-only and already natively proven.
1. Add `heavy.mdl` to a shot and observe it with no rig (`S0-01`).
2. Apply `rig_biped_simple` from the Rig menu and observe again (`S0-02`).
3. Add `ayane_dazv5` and apply `rig_biped_daz_v5`; observe (`S0-03`).
4. Exit without saving. The session changes are SFM's own model and rig loading in a disposable session.

**Offline part:** one small probe, no CPM change, run on each observation:
- it derives the discovery fixture (the existing `f01_body_fixture` derivation);
- it runs the stage E classifier against a profile drafted automatically from the observation;
- it reports, per model, exactly which rule refuses and why: no rig, an unknown operator, an unmatched handle, an
  unclassified channel;
- it lists the facial FK bones that would be written without a preserved list.

The output is a per-model refusal map. It answers the questions of section 4 (hierarchy, writable controls, IK and
FK, constraint ownership, placement and scale, facial and eye controls, instance compatibility) before any
generalization is implemented.

## 6. Recommended next milestone (after the investigation)

**"Discovered profiles for same-model reuse."** At Save New, CPM records the rig's discovered structure in the
pose, and only for the classes the engine fully understands. At Apply it requires the destination's discovered
structure to be **identical** (same model, same rig). In practice:
- no hand-authored profile per model;
- refusals name the unsupported feature in artist language;
- operator support grows deliberately: reverse foot and rotation constraints first, as rig-internal and preserved;
- the FK-only path gets a defined placement frame;
- facial preservation comes from a policy (section 7).

## 7. Decisions for the Owner and Astra

1. **Where compatibility authority lives:**
   - reviewed registry profiles per model, which are safe but need manual work per model; or
   - the discovered structure recorded in the pose and matched exactly at Apply, which needs no configuration but
     means the classification rules alone decide what is written. That raises the bar on refusing anything unknown.
2. **Facial and eye preservation without a profile.** The candidate sources are:
   - CPM's own Master animation-group taxonomy (`sfm_defaultanimationgroups`, the face groups), which CPM already
     maintains;
   - name rules;
   - or writing facial FK bones as part of the pose.

   This decides whether Apply can change an expression.
3. **The FK-only placement frame**, for models with no rig: the model's root bone or transform. Also, whether the A1
   FK-position rule (exact, or ≤ 0.00005 for Krystal) applies by default to discovered profiles.
4. **Scope of rig features:** treat reverse-foot expressions and rotation constraints as rig-internal and preserved,
   or refuse rigs that have them.
