# F-01 Scoped Pose Library — Architectural Blueprint and First Milestone

Revision 3 — 2026-11-08

Status: DESIGN READY FOR OWNER AUTHORIZATION OF BOUNDED SFP-1 STAGES A/B. This document is not itself authorization to implement, install, execute SFM, promote a mapping, or release. The independent audit is closed; another general design cycle is not required.

## R3 change summary

R3 preserves R2's Full body/Selected parts product design, facial-scope policy, records, legacy routes and transaction guarantees. It makes four bounded amendments:

1. Define a read-only `constant_channel_carried_v1` candidate class for control-less bones. A null channel source is not evidence that a bone is fixed. Constant keys, complete authority, supported procedural-state evidence and coherent native transforms are required before admission; unknown behavior cannot be deferred to P7.
2. Specify parent-first partial-pose composition through unselected bridges, cumulative uniform scale at boundaries, and an independently observed skeletal oracle. Reuse the existing scale-aware primitives without reusing a whole-body oracle where partial-scope semantics differ.
3. Make generic v3 authorization, per-attribute authority and grouped selection explicit integration obligations. Preserve legacy v1/v2 dispatch and distinguish the library envelope version from the pose payload version.
4. Add targeted offline counterexamples and bounded native gates. Stages A/B can proceed after Owner authorization with unqualified capabilities disabled. No new general survey or repeat W1/W2 campaign is required.

R2 remains preserved. Appendix A records the independently checked source and observation evidence; Appendix B is the implementation checklist. Argon's conclusions and citations are not adopted as authority.

## 1. Authority and purpose

This Blueprint records the Owner-approved direction: full-body and partial poses share a scoped representation; finger/thumb articulation is a core feature; sequential application is sufficient; live SFM state is the primary technical authority; supported skeletal facial controls may be included; flex expressions remain separate.

It supersedes the earlier general-compatibility G1–G4 proposal and the full-body-only policy for NEW general-purpose pose records. It does not reinterpret version 1 left-arm or version 2 Krystal records, replace historical qualification records, or alter M-05/M-06.

Reference baseline inspected: `feature/f01-pose-library`, local commit `6d6e9e6ce15cfc33d2544d74edb97482fc207d79`. Relevant project records include `F01_MODEL_COMPATIBILITY_SURVEY.md`, `F01_FULL_BODY_S3_ASSESSMENT.md`, and `F01_FULL_BODY_CONSOLIDATED_DESIGN.md`. Their qualification claims retain their original scope. The new direct-FK/scoped behavior is not natively qualified.

Purpose: save the complete declared body posture or an explicitly selected part, reload it independently, and reproduce it on a compatible instance without changing placement, proportions or unauthorized animation. Facial-expression systems may be explicitly outside the body scope; their mere existence is not a refusal condition.

## 2. Full body, facial exclusions and truthful coverage

### 2.1 Product scope

**Full body** captures the character's declared body positioning and articulation: trunk, limbs, hands, fingers, feet, toes, hair, ears, tails, wings and other relevant skeletal anatomy present on the model. It does not mean every mechanism in the animation set. Flex expressions, gaze inputs, model placement and scale remain outside the write scope. Skeletal expression systems may also be explicitly excluded.

Full body may include supported skeletal facial controls when they have not been excluded. It must disclose that inclusion; an Expression preset is not guaranteed to overwrite those skeletal controls. The existing Expression path handles its supported flex values.

There is no separate **Whole skeleton** operation for v1.1.0. It adds another completeness promise without serving the primary workflow. A full-body record that also captures supported facial bones is simply a full-body record with that additional declared coverage.

### 2.2 Coverage ledger

Before capture, account for every relevant skeletal element as one of:

- **Body articulation:** reproduced directly or through an understood relationship, including independently poseable secondary anatomy.
- **Included skeletal expression:** optional additional captured articulation, subject to exactly the same technical admission rules.
- **Excluded expression:** explicitly left outside capture, with a recorded semantic basis and a verified technical boundary.
- **Placement/proportion or supported fixed/derived state:** protected or verified according to its existing role; not an omitted pose input.
- **Unresolved:** blocks Full body until its role and relevant relationships are resolved. It need not block an independent Selected parts operation.

These categories are evidence, not a name-based anatomical ontology. A classification ledger may account for bones without adding writes to their dormant or derived channels.

Do not build Full body by taking only the channels the engine happens to support. A tail that is unsupported remains a missing body capability, not an expression exclusion or passive bone. Dropping a body part changes the record to **Selected parts**; never keep the Full body label merely because the user named it that way.

### 2.3 Practical scope construction

Use the following deterministic policy:

1. Enumerate the live skeletal inventory, applicable controls and known structural roles. Default pose-relevant skeletal controls to inclusion, including hair, ears and custom bones. This avoids silently losing anatomy when semantic information is absent.
2. Accept an expression exclusion automatically only from an explicit semantic source with a supported, reviewed interpretation. A native type that establishes a flex destination is such technical evidence; a group merely named Face is not sufficient evidence about arbitrary skeletal bones. The survey has not established a universal authoritative semantic source for facial bones.
3. Use SFM control groups and labels to organize a proposed scope or highlight an ambiguity. Resolve membership by native identity, not name-only joins. Do not use substrings such as head, jaw or face to authorize exclusions, and do not exclude an entire head subtree.
4. When an unsupported or ambiguous component might be an expression system, show a concise **Review scope** summary within the Save dialog. The artist can explicitly identify the displayed controls as expression controls to leave unchanged, retain them in the requested pose, or choose Selected parts. This is a declaration of intended artistic scope, not technical permission to ignore dependencies.
5. Resolve technical isolation separately. Owner confirmation cannot override competing writers, shared logs, unreadable boundaries or unknown side effects.
6. Freeze the resolved coverage and exclusions in the record. Update and Apply reuse that scope; they do not repeat a naming heuristic or silently redefine it. Within the current window, a confirmed draft may be reused for another Save only while its model/structure/membership identity remains unchanged. No separately authored per-character profile or persistent profile-management interface is required.

For a fully supportable model, the inclusion default permits ordinary one-step Full body capture, possibly including skeletal facial controls. Scope review is an exception for ambiguity/exclusion, not a required setup ritual for every model.

Reliable automatic body-versus-face semantics are not generally derivable from geometry or control topology. The practical compromise is automatic inclusion plus explicit, visible exceptions. This provides useful body capture without claiming that CPM can prove anatomical meaning from arbitrary Workshop labels. Human-confirmed exclusions are recorded as such, not presented as machine-verified anatomy. If the artist does not resolve an ambiguous exclusion, Full body remains unavailable; supported Selected parts remain available.

### 2.4 Admission outcomes

| Situation | Required outcome |
|---|---|
| Conventional supported body, explicitly excluded facial system with a proven independent boundary | Allow **Full body**. Do not require a supported facial pose solver. |
| Supported skeletal face included in the resolved scope | Capture it and disclose the inclusion. |
| Unsupported facial inputs explicitly requested for capture | Refuse that request or let the artist explicitly revise the scope before capture. Never silently drop them. |
| Facial-looking component has unresolved semantic scope | Ask for scope review; do not guess, silently exclude it, or downgrade the operation without notice. |
| Facial operator can write requested/protected body state or shares mutable authority | Refuse the affected operation. |
| Operator's side effects cannot be bounded sufficiently to establish safety | Refuse where that uncertainty affects authority; absence of a visible connection is not proof of independence. |
| Unsupported body/secondary articulation would be omitted | Refuse **Full body**; permit an explicitly selected supportable part. |

For Selected parts, completeness means the entire declared selection and its required effects are supported. No selected unsupported element may be silently removed. A partial finger operation may remain safe even when a broader torso operation cannot be isolated from the same facial system.

## 3. Technical foundation

Use live bones, transform controls, channels, logs, bindings, hierarchy and operator relationships. Rig scripts may inform engineering and qualification; do not parse or execute them during ordinary Save/Apply to reconstruct authority.

The installed engine defines supported behavior. Automatically generated descriptors instantiate those rules; they cannot authorize unknown behavior. Control groups organize selection, labels and scope-review proposals; their labels alone establish neither semantic exclusions nor writer ownership or compatibility.

The first new rule set is `direct_fk_v1`:

- A selected transform attribute is driven by a uniquely identified supported transform-control channel.
- Its destination, source, indices, mode, log, layer, key/metadata representation and evaluation satisfy the existing strict readers and key-planner contract.
- No competing channel, constraint or operator drives the selected attribute or its control source.
- Written channels have exclusive logs and layers, including against other instances.
- Do not admit a new key representation merely because the model is unrigged.
- Rig presence elsewhere is not itself a refusal. Direct-FK fingers can qualify on a rigged model.
- Bone-parented rig handles, IK target application, reverse foot, dynamic jiggle and arbitrary scalar controls are not new writable capabilities in this milestone.

An existing qualified version 1/2 path continues to handle its approved rig operations. Do not replace it with generic discovery in this milestone.

### 3.1 Control-less skeletal elements: explicit read-only admission

R2's refusal of unresolved authority was safe, but its reference to fixed/derived elements was not a sufficiently implementable generic classification. Distinguish:

- **Supported fixed local transform:** positively established absence of animation/procedural writers under a qualified ownership contract, with readable finite local state and understood parenting.
- **Constant-channel carried transform:** a real channel-driven transform satisfying `constant_channel_carried_v1` below. It is not writer-free, dormant, or a newly writable pose control.
- **Known derived output:** handled only by an existing qualified relationship contract. Do not relabel an IK or procedural output fixed.
- **Unresolved runtime behavior:** not admitted to a requested/affected skeletal outcome. An independent selected scope can still operate when its boundary is proven.

`constant_channel_carried_v1` is a reusable representation rule, not a list of Heavy or Krystal bone names. Admission requires all of the following:

1. Fresh unique bone/transform/parent identities. No ordinary transform control owns the endpoints. Each local position/orientation endpoint has exactly one supported channel writer, verified-null `fromElement`, supported scalar endpoint indices, and native mode 3. Absent/unreadable source or endpoint evidence is not verified null.
2. Correct Vector3/Quaternion log and layer types; one layer; fully readable raw key times/values and metadata consistent with native getters. Admit one or more strictly ordered keys whose stored float32 values are all identical (same quaternion sign), with supported constant interpolation/extrapolation. Nonfinite, duplicate-time, layered, compressed, unsupported curve/tangent or contradictory evidence refuses. Read defaults and their enable state; an enabled default must not contradict the constant. Do not impose new restrictions on unrelated qualified legacy representations.
3. Full representation evidence establishes a constant at the authorized time, including outside the key range when applicable. A single evaluation matching the last key does not establish extrapolation semantics. Existing supported log semantics may be reused; unsupported semantics remain a native qualification dependency.
4. At capture and destination P1, mapped time and current time agree under the Motion Editor rule; evaluated log, destination local transform and independently observed skeletal state agree within the established observation rules. Constant-key summaries alone are insufficient. Capture the exact destination authored baseline for preservation.
5. Document-wide channel/operator/alias/resource discovery establishes exclusive authority for these attributes and no unknown relevant effects. A model's non-channel procedural evaluation must also be accounted for. Absence from the DME writer list does not prove absence of engine procedural bone evaluation.
6. Procedural-state evidence is positive and readable under a supported engine contract: either procedural evaluation is verifiably disabled for the relevant model, or authoritative per-bone evidence excludes a procedural override for these bones. Do not infer either from a name, null source, identical keys or one stable snapshot. Do not change a model flag to obtain admission. If the required evidence is unavailable, report this class as unsupported for that scope.
7. Record the rule revision and required portable structural evidence. Runtime identities are freshly resolved; they are not persisted as authority. P2 rechecks the same authority, procedural-state, values and parenting assumptions before Undo. Shared mutable logs/layers with W refuse. P7 repeats authority and preservation checks but cannot rescue inadequate P1/P2 admission.

The MC-01 model attribute inventory includes `evaluateProceduralBones`, but the observation does not record its value or establish its exact native semantics. It is a concrete candidate for a minimal read-only guard during implementation/qualification, not an already proven API contract. Do not invent a new model-file parser or assume an undocumented flag from its spelling. A supported guard must distinguish missing/unreadable from disabled. Until the guard's contract is established, this new passive class remains experimental and unavailable for ordinary scene operations; other admitted direct-FK scopes can proceed.

**Capture and Apply semantics:** carried elements receive no key insertion or updates, including when they lack a key at the playhead. Store their classification, structure and observed local/oracle evidence. For Full body, their constant local state must be compatible with the saved body evidence; meaningful orientation or offset differences refuse rather than being silently preserved under a completeness claim. Use the existing A1 numerical offset policy only where that role is actually structural; use existing quaternion observation tolerances without changing them. For Selected parts, unselected carried articulation comes from the destination baseline, not the source pose. Any structural dependency necessary for interpreting selected articulation still requires compatibility. Direct selection of an unwriteable helper does not create a writable pose target; explain its supported carried role or refuse an unsupported request.

A moving source-less log or unknown jiggle result is not a new capture capability. If it belongs to requested body anatomy, Full body refuses. If safely isolated outside a partial scope, its presence alone does not block that scope. Semantic facial exclusions still require section 2's separate scope and boundary evidence.

## 4. One scope compiler, four explicit sets

Compile every operation into:

1. **W — written inputs:** exact channel attributes authorized for key insertion/update.
2. **A — affected anatomy:** selected bones and supported descendants/outputs whose evaluated transforms may change.
3. **D — read-only dependencies:** parent frames, bindings, structural offsets, scales, clocks, boundary conditions and operator relationships needed to interpret W and A.
4. **P — protected state:** all other authored state; evaluated preservation obligations where the operation could affect it.

Selection is an expression of intent, not W. Resolve it through current native identities and the supported rules. Deduplicate before planning. Refuse ambiguity.

### Dependency and exclusion rules

- Do not auto-add a parent bone to W. Selecting fingers must not write the wrist, elbow or arm.
- Required supporting writes may be included only if the UI describes their affected scope and the artist has selected that scope. There are no coupled supporting writes for the first direct-FK rule set.
- Unselected supported descendants may follow a changed parent while retaining their own local articulation and authored data. Record them as carried descendants, not silently selected articulation.
- Inspect document-wide writer/log/layer sharing and external operator relationships. Do not narrow the inventory to the selected controls.
- Separate **unknown pose semantics** from **unknown side effects**. CPM need not reproduce an excluded facial solver if an existing supported interface can enumerate its complete relevant outputs, aliases, mutable resources and dependencies well enough to establish the boundary. An operator with an unknown write set cannot be declared harmless.
- For an excluded facial subsystem, prove that its outputs do not drive W, body outcomes in A, their structural/placement dependencies, or their control sources; that there is no feedback/cross-boundary write; and that it shares no mutable channel/log/layer resource with the planned operation. Changing body inputs must not trigger hidden graph or authored-data mutations.
- One-way dependence on a posed head/parent frame is permitted when that relationship and output confinement are established. The face may follow the head or continue its own confined procedural evaluation. It must not feed back into the captured body or change protected authored inputs.
- Do not require excluded facial world transforms to remain fixed while the head moves. Also do not claim preservation of the exact visible facial expression for an excluded procedural subsystem whose evaluation is not qualified. The guarantee is unchanged excluded inputs/keys/graph and safe output confinement, not freezing its solver.
- If a selected input is shared between body and excluded facial control, do not assume that leaving the facial channel unwritten preserves independence. Resolve the complete relationship or refuse.
- For a preserved supported branch, retain the existing exact-authored and local-articulation verification. The special treatment of an explicitly excluded solver must not become a blanket waiver for unselected body anatomy.
- Name, owner animation set, group membership, an empty partial endpoint list, or the user's scope confirmation is never a substitute for technical isolation evidence.
- Discovery and supported-pose classification must be separable: discovery may inventory a known bounded interface even if CPM has no pose adapter for that solver. If the current reader cannot establish a required boundary, refuse that scope and identify the missing interface; do not skip the node or invent a generic safe adapter.

Index authority by endpoint element identity, attribute and index, with operator read/write effects and aliases represented explicitly. Position, orientation and scale are different attributes. A supported scale expression does not become an orientation co-writer merely because it references the same bone. It remains a scale dependency: its supported effect set, input stability and output must be verified, and a write to scale or feedback from W is not ignored. Unknown effect sets refuse when potentially relevant; a simple reference scan finding no connection is not an isolation proof.

At P1/P2/P7, revalidate relevant boundary identities, output confinement and shared-resource evidence. Compare required protected authored state to the destination's own baseline. An unobservable potentially modified attribute is not evidence of preservation.

This is a targeted scope correction, not authorization to build a general rig interpreter. A concrete isolation limitation may require a small supported reader later, but no new general research campaign is a prerequisite for the already supported direct-FK paths.

## 5. Frames, articulation and structural positions

### Partial direct-FK articulation

Capture selected bones' local orientations. Resolve each selected component against its actual skeletal parent boundary. Apply using the destination's current parent frames, not the source's world position. A destination wrist may have a different orientation and arm position.

For each selected component, store independently observed skeletal evidence relative to its source boundary, plus local orientations. At Apply, construct the expected result using destination boundary frames, saved observed articulation and the admitted destination structural offsets. A boundary inside another selected ancestor's affected subtree uses its expected post-Apply frame, not its frozen pre-Apply world frame. Do not derive the only skeletal oracle from the values just written. The exact composition and independent checks follow below.

Carried descendants preserve their destination local articulation and follow their expected posed parents. They do not inherit the source's unselected articulation.

Finger articulation excludes wrist/hand placement unless the artist explicitly selects a supported wrist articulation scope. Selecting an IK hand target is not a finger pose and refuses under `direct_fk_v1`.

### Parent-first composition, bridges and cumulative scale

Build one acyclic hierarchy for A and the ancestor/dependency paths needed to interpret it; resolve once per comparison phase, then walk parent before child. Fresh lifecycle phases still re-resolve authority. Do not compute each selected component independently against a stale boundary.

For supported positive uniform scales, let `P`, `Q` and `S` denote world position, normalized world orientation and cumulative scale, and `p`, `q`, `s` denote a bone's local position, local orientation and own scale:

```text
P_b = P_parent + rotate(Q_parent, S_parent * p_b)
Q_b = Q_parent * q_b
S_b = S_parent * s_b
```

The parent's cumulative scale acts on the child's offset. The child's own scale affects descendants, not its own offset. Seed an external boundary from its observed destination frame and the verified cumulative scale of its complete relevant ancestor chain. Do not reset scale to 1 at a partial selection boundary. Do not apply scale twice when converting an already scaled affine frame. Model/wrapper scale must be explicitly supported and included, or refused; the legacy helper's root seed of 1 is not evidence that all model scales are 1. Existing supported bone-scale accumulation is reusable. Nonuniform, negative, singular, sheared or unreadable scale remains unsupported. Relevant source/destination scale compatibility is required; this is not scale retargeting.

For selected bones, use the saved independently observed local articulation for the skeletal expectation and the admitted destination position inputs (except the authorized full-body root translation). For unselected bridges and carried descendants, use their pinned destination local position/orientation/scale. Never copy source articulation into an unselected bridge.

Example: selecting upper arm and hand but not forearm yields expected upper arm from the destination shoulder boundary and saved upper-arm articulation; expected forearm from that expected upper arm and destination forearm local state; expected hand from that expected forearm and saved hand articulation. The forearm receives no writes. The hand must not use the old forearm world frame or the source forearm articulation. Likewise a finger-only pose uses the destination wrist, while a selected wrist plus fingers uses the expected posed wrist.

**Independent verification:** capture source skeletal observations through native bone/local/absolute-transform readers, independently of channel plan construction. Before mutation, verify the admitted composition against independently observed destination baseline transforms and validate the recorded source observations against their source hierarchy/scale evidence. A disagreement is not an excuse to broaden tolerance. Build expected target transforms from saved observed skeletal articulation plus destination protected inputs, not by evaluating the just-authored keys and declaring that result correct. At P7, read actual native skeletal transforms again and compare both selected local articulation and parent-first expected world results; separately check exact authored keys, log/input results, carried locals, placement, scales and all protected authored data. Shared mathematical primitives are acceptable; the actual observation and expected evidence must not both come from the planner's outputs.

Source component-relative world observations are consistency evidence, not permission to impose the source's unselected bridge pose on the destination. Analytical offline tests with independently calculated rotations, offsets and scales must detect wrong multiplication order, missing ancestor scale and double scale. Existing positional/angular tolerances remain unchanged. If accepted numeric offset differences amplify beyond those tolerances, refuse that case; do not silently relax the skeletal check.

### Full-body direct-FK scope

Use the verified model placement transform as the reference frame. Preserve its channels, values and scale. Do not infer placement from an arbitrary bone named root or pelvis.

For the bounded first rule, support a single uniquely identified anatomical root directly under the model frame, with no conflicting authority. Its model-relative translation is pose data, allowing crouching/body offset without moving the model placement transform. Refuse ambiguous multiple-root or extra-wrapper arrangements until explicitly supported. Merely being first in the bone array is not sufficient.

Root translation is included only in full-body mode in this milestone. Selecting the anatomical root in Selected parts captures its articulation but does not authorize body translation; disclose the distinction. Its position remains a read-only destination dependency, with no position key written and no source/destination structural-offset equality requirement for that pose translation. Pin it exactly during P1/P2. Do not misclassify a different destination body offset as a proportion change.

### Non-root FK positions

Capture finite source float32 offsets for compatibility. At Apply, preserve the destination offsets rather than importing them. Plan required position keys using the pinned destination values, including missing-key insertion. Existing exact keys remain untouched. Meaningful offset differences refuse.

The first generic rule uses an explicitly versioned, provisional maximum Euclidean offset discrepancy of `0.00005` SFM units, matching the demonstrated bounded policy rather than introducing a larger allowance. This is an engineering limit proposed for native qualification of `direct_fk_v1`, not a claim that every model's rounding fits it. It is not applied to arbitrary rigs or increased automatically. Source and destination values must be finite native float32 values; destination log/transform coherence and P1/P2 stability remain exact as in revised A1.

Scale/proportion compatibility remains a separate requirement. Admit only the scale representations the existing transform/oracle code actually supports; do not approximate an unsupported nonuniform or sheared transform. Do not treat this tolerance as retargeting or as permission to transfer arbitrary facial, stretch or accessory translations. Unsupported translation posing must refuse rather than produce an incomplete claim.

## 6. Record contract

Retain the existing library envelope: `schema_version: 3`, `record_kind: preset`, `kind: pose`, character/model reference, stable preset ID, name, timestamps and payload SHA-256.

Use **`pose.version: 3`** for the new scoped payload. This is distinct from the existing envelope schema version. Keep `pose.format: cpm-pose` and existing coordinate/quaternion/time conventions. Do not overload version 2 `full_body` regions.

The closed version 3 schema contains the following sections:

| Section | Required content |
|---|---|
| `engine` | Supported rule ID `direct_fk_v1` and contract revision. The engine, not the file, supplies limits and admission rules. |
| `source` | Existing validated model identity, normalized model reference, skeleton layout signature and observed checksum evidence where available; capture time and diagnostic shot name. No runtime handles. |
| `scope` | `full_body` or `selected_parts`; explicit requested, posed and carried bone IDs; completeness claim `declared_body` or `declared_scope`; a coverage ledger mapping relevant bone IDs to the roles in section 2. Each excluded skeletal-expression set has stable IDs, reason and provenance (`supported_metadata` with policy revision, or `user_confirmed`). A human-readable label is descriptive only. |
| `structure` | Unique bone IDs tied to model bone index/name/parent; portable binding roles, supported representations and dependency edges; placement/boundary references; relevant scale and structural compatibility evidence. Describe excluded-subsystem boundary obligations, not an executable opaque solver or a requirement that unrelated facial internals match the source. |
| `values` | Selected finite float32 local orientations; source structural offsets; anatomical-root pose translation only when authorized by full-body scope. No copied arbitrary attributes or script expressions. |
| `oracle` | Independently captured source skeletal local orientations and component-boundary/model-relative transforms for the declared affected evidence; not merely a duplicate of channel key values. |

No shipped v3 records exist under R1: use the corrected v3 contract directly, without inventing a migration from R1 draft records. Version 1/2 behavior is unchanged.

The schema must reject unknown fields, duplicate IDs, duplicate destinations, contradictory scope memberships, cycles, nonfinite values, missing required evidence, forged rule revisions and excessive counts/record sizes. Use the current bounded pose-record reader and size limits unless measured legitimate records require a separately reviewed adjustment.

Do not persist complete runtime baselines or unrelated private scene contents in pose files. Runtime W/A/D/P evidence is reconstructed and pinned per operation. The coverage ledger must account for the model inventory used to make the declared-body claim, including excluded and structural elements; omitted body entries cannot become exclusions by default. Exclusion provenance is a record of intended scope, not trusted execution authority. Apply independently verifies the live technical boundary; imported files cannot grant themselves unknown operator support. Pose Info exposes all declared exclusions.

Persist enough portable topology to resolve the selected scope uniquely; no instance names or native pointers as mutation authority.

Match the existing validated model identity plus skeleton/layout and operation-specific structure. A matching path alone is insufficient. Do not invent missing native checksums or require a new asset-hashing service. If the existing evidence cannot establish the supported same-model contract, refuse with a useful reason.

Unrelated facial internals need not be structurally identical between source and destination when they are explicitly excluded and the destination independently satisfies the required boundary. Preserve their destination state; do not copy the source face or validate its opaque solver against a source oracle. Different wrist poses are allowed. Different relevant bone lengths, scale state, parent relationships or bindings are not automatically allowed. Unrelated rig-display names and unrelated current pose values are not compatibility keys. Do not attempt cross-model or rig-to-FK retargeting.

Preserve v1/v2 parser, dispatch, update, oracle and facial semantics. No automatic migration or silent conversion. New generic/scoped records use v3. Existing qualified Krystal Save New remains available through its v2 path and original declared coverage; adding v3 must not disable it or silently change its facial behavior. Update preserves a record's format and declared scope. Changing scope is Save New. Rename/Delete/Favorite and foreign-library protections reuse existing library behavior.

### 6.1 Generic authorization and legacy dispatch

Dispatch on validated pose payload version/engine rule, not on the envelope's `schema_version` or the selected UI label alone. The envelope remains `schema_version: 3` for old and new pose payloads.

Keep v1/v2 registry/profile selection and operation behavior intact. Generic v3 requires its own supported-rule/capability authorization using the same pinned selected-instance context, library identity/revision, mode/time/history gates, ownership and lifecycle guard. It must not require that a generic model resolve to a Krystal registry entry; it must not bypass common safety checks to avoid that entry. Never spoof a Krystal rig class. Imported records cannot authorize new engine rules or enable an experimental capability.

Audit existing Save New, Update, Apply, Pose Info, compatibility display and enabled-state decisions for assumptions about legacy `regions` or registry membership. Route existing Krystal Full body deterministically as section 7 states; route new Selected parts through v3 only when admitted. Unsupported v3 shows a useful refusal without disabling qualified legacy operations. Keep data adapters separate while sharing transaction primitives. Offline tests must exercise actual production dispatch, not replace the authorization function with success.

## 7. Selection and UI contract

Keep the existing CPM Poses tab, compact library, actions and status area. No extra tab, technical profile editor, mandatory facial wizard or literal complete-skeleton operation. Keep Owner-approved typography, tab sizing and no-ellipsis button labels.

Save New offers:

- **Full body** — default.
- **Selected parts**.

Full body starts with the inclusion-based coverage resolver in section 2. Display a short coverage summary before saving, for example `Body and secondary anatomy; facial controls unchanged` where that exclusion has been established, or `Includes supported facial bones; flex expressions unchanged`. The summary is based on the actual ledger, not merely on the chosen label.

When necessary, **Review scope** opens the same compact grouped control list used to inspect selected parts. Show the unresolved component, proposed exclusion and affected names. Offer explicit exclusion as expression controls, continued inclusion, Selected parts, or cancel. Confirmation resolves scope only; it never suppresses technical refusal. Do not ask artists to write a profile or understand operator classes. Remember a valid draft only under the unchanged identity conditions in section 2.

Where the existing qualified Krystal route is used, Full body may retain that v2 behavior and show `Qualified Krystal body; facial controls unchanged`. Do not create a separate ordinary-user operation called Krystal body solely to distinguish a file version. Select the supported route deterministically and disclose its coverage. Do not silently migrate v2 records or claim generic v3 qualification from that fallback. Selected parts uses the new route where supported.

Use the compact grouped skeletal-control picker as the reliable first selection interface. Resolve the surveyed control-group memberships to actual bone controls; keep placement, gaze, flex and other non-skeletal items out of its eligible list. Show meaningful unavailable controls with a reason rather than silently adding them. Groups are convenience containers, never authority or proof of facial semantics.

Seeding from current SFM selection is optional and must stay unavailable until that reader is qualified. It is not a milestone blocker. When seeding is enabled, unsupported explicit selections must be disclosed as below. Store explicit resolved members, pin selection/instance/time when the scope is confirmed, and revalidate after the dialog. Do not silently absorb later selection changes.

For direct-FK skeletal controls, select the bone articulation and its required structural-position key behavior, even if SFM exposes separate orientation and position channels. Flexes, gaze, placement controls, unsupported handles and controls from another instance are not silently discarded from an explicit selection: explain the unsupported selection and let the artist correct it before Save.

Example copy:

- `Left fingers: articulation only. Wrist and arm unchanged.`
- `Full body: body articulation captured; the listed facial controls are left unchanged.`
- `Review these controls before saving: CPM cannot determine whether they belong to the body pose.`
- `This tail cannot be captured yet. Choose Selected parts to save a smaller pose.`
- `This control also drives the arm. Choose a supported scope or select finger controls.`

Apply uses the record's declared scope regardless of current SFM selection. There is no Apply-time subset selector in this milestone. Pose Info lists captured scope, exclusions, scope provenance and compatibility reasons. Update retains the saved scope and exclusion policy; changed semantic scope is Save New. A renamed group alone does not redefine an existing record. Changed binding/coverage evidence can require review or refusal.

Save/Apply refusals name the relevant feature or scope boundary, not simply “unsupported model.” Do not claim nothing changed after an uncertain transaction or failed postcommit verification.

## 8. Existing transaction engine and P1–P7 contract

Reuse the qualified strict readers, key planner, ownership checks, operation context, Undo lifecycle, same-time refresh, deferred verification and process-wide recovery pause. Introduce the scoped compiler and expected-state data ahead of those mechanisms. Do not build an independent Undo engine or change M-05/M-06 dispatch.

- **Capture:** read-only, settled Motion Editor context with consistent mapped channel times. Save actual evaluated posture, not stale stored control inputs. Pin context across prompts. No scene normalization.
- **P1:** resolve fresh selected instance; resolve the declared body/selected scope and explicit exclusions; compile W/A/D/P; validate records, time, authority, compatibility and evidence. Pin the destination baseline and boundary transforms. Produce one deduplicated key plan and complete expected authored state.
- **P2:** freshly re-resolve authority, scope and context. Require unchanged pinned dependency values, exact structural-position coherence, source record revision, model instance, history and clocks. Destination wrist changes between source capture and destination P1 are allowed; changes during this operation are not.
- **Owned writes:** insert/update only W at the authorized tick in one native Undo operation. Preserve neighboring keys and protected metadata. Verify exact planned float32 values and transaction-time expectations.
- **Failure before/during Undo:** retain the corrected uncertain StartUndo/FinishUndo handling, no blind Abort/Undo, and recovery pause. Abort only a proven owned transaction and verify the independent original baseline, including inserted-key removal.
- **After confirmed commit:** request the established single same-time refresh outside Undo and use the existing deferred lifecycle. No polling or nested event processing.
- **P7:** independently verify authored state, refreshed inputs, the captured-body/selected skeletal oracle in destination frames, carried descendants, protected state, fresh authority, exclusion boundaries and ownership/context. Excluded facial inputs/keys/graph must match their destination baseline; opaque excluded facial evaluation is outside the pose oracle and may only behave within the established confined boundary. Do not weaken body-pose verification or promote an unexplained body change to an exclusion. Failure remains unverified; no automatic compensating Undo.

True no-op requires all required exact keys and evaluated results to match. A visible match with missing keys is an insertion, not a no-op. Reuse quaternion hemisphere/sign safeguards. Do not widen verification tolerances to admit an unfamiliar model.

Sequential application is the entire layering model: later operations replace overlapping authorized input values; nonoverlapping authored inputs remain unchanged. Each operation has its own Undo entry. There is no persistent blend stack or additive quaternion mode. Key insertion may affect interpolation on selected channels between existing keys; do not promise identical surrounding motion there.

## 9. First milestone: SFP-1 — Direct FK and independent finger articulation

### Included

1. Strict v3 scoped records and independent persistence/reload.
2. Automatic supported direct-FK discovery without per-model hand-written profiles.
3. Full-body direct-FK Save/Update/Apply on a compatible model, including alongside an explicitly excluded independent facial system when its technical boundary is established.
4. Selected independent direct-FK fingers/thumbs, including on a rigged character where those controls qualify.
5. Partial application with different destination wrist orientation and arm posture.
6. Scope-aware compatibility, unsupported-feature isolation when provable, and meaningful refusals.
7. Existing UI/library integration and all qualified transaction safeguards.
8. v1/v2 backward compatibility.

### Excluded

New IK applications, generic bone-parented rig-handle support, reverse foot, arbitrary scalar/procedural inputs, flex capture, a universal anatomical inference system, hand-authored per-character profiles, cross-model retargeting, mirroring, blending, persistent layers, automatic record migration, Apply-time subset selection and production promotion.

Independent FK toe/hair/tail selections can use the same mechanism when they meet its rules; no separate feature implementation or unsupported-feature workaround is needed. Do not market their compatibility without the corresponding evidence.

## 10. Bounded implementation stages for Claude after authorization

### A. Offline scope and record core

Implement the closed v3 schema and coverage/exclusion ledger, inclusion-default scope construction and explicit scope-review outcomes, direct-FK discovery/admission, W/A/D/P compiler, dependency/frame logic, compatibility checks and pure expected-state planning. Use existing survey fixtures and independently constructed counterexamples. Keep experimental capability disabled in the production configuration. No new native campaign is required before this stage.

Exit evidence: fixtures demonstrate meaningful full-body and finger scopes, including safe isolation and genuine cross-boundary refusals; scope/authority counterexamples refuse; portable records round-trip; legacy readers remain unchanged. A generated profile matching its own generated expectation is not sufficient evidence.

### B. Existing lifecycle and UI integration

Connect the scoped plan to the existing Save/Update/Apply, file handling, one-transaction and deferred-verification mechanisms. Add the compact Full body/Selected parts selector, conditional scope review and diagnostics. Exercise actual production dispatch and pose_guard wherever practicable; fake native APIs, not the internal scope/authority decisions under test.

Exit evidence: complete offline acceptance matrix, fault injection through real orchestration, unchanged v1/v2 regressions, candidate/source identities and a focused review package. If an existing function is too region-specific, make the smallest additive/refactoring change needed and retain separate legacy expected-state adapters. Do not silently route old records through new semantics.

This R3 completes the requested focused reconciliation after the independent audit. Stages A and B are ready to form one bounded coding assignment when the Owner authorizes implementation; no additional general design audit is required. Do not add an administrative approval between every internal stage. Implement unsupported native evidence as explicit refusal and a targeted qualification dependency, never invented success. A missing passive procedural guard blocks that case, not independent direct-FK implementation.

### C. Native qualification, separately authorized

After offline review, prepare one short Owner-operated procedure using disposable sessions and existing restoration safeguards. No automated SFM operation is implied. No production enablement until results are accepted.

## 11. Required offline acceptance tests

| Area | Required positive/negative evidence |
|---|---|
| Records | v3 round-trip and fresh reload; corrupt digest; unknown rule/version; missing/duplicate/cyclic scope data; nonfinite values; bounded size; no runtime identity persistence; v1/v2 unchanged. |
| Coverage | Full body accounts for body and secondary anatomy plus explicit expression/structural exclusions; a conventional supported body with an excluded unfamiliar but isolated face passes; the same solver requested for capture refuses; an unsupported tail cannot be silently omitted. Ambiguous labels require scope review, not auto-exclusion. |
| Exclusion boundaries | Shared logs/layers, hidden or unresolved output sets, feedback into body, or mutations of authored state refuse. Proven one-way head-follow behavior is allowed without requiring identical facial world transforms. A new cross-boundary writer at P2/P7 refuses or prevents verified success. |
| Scope semantics | A group merely named Face or a bone containing head cannot authorize omission; hair/ears remain included by default. User confirmation does not bypass technical checks. Stable declared scope survives group renaming; relevant model/binding changes invalidate it. Imported exclusions never authorize unsupported execution. |
| Selection | One instance only; deleted/replaced instance; ambiguous bindings; group membership changing during a dialog; duplicate selections deduplicated; unsupported selections refused; Apply ignores unrelated current SFM selection. |
| Frames | Fingers reproduce in differently rotated/positioned wrists; arm and wrist inputs remain unchanged; upper-arm + hand selection with unselected forearm uses the expected forearm frame and its destination local state; multiple selected components and carried descendants traverse parent-first; unrelated branches remain unchanged. Independently calculated rotations catch a self-consistent wrong planner. |
| Scale | Nonunit and nested uniform bone scales above and inside a partial boundary; own-scale versus parent-scale distinction; omitted/double ancestor scale detected; unsupported model/wrapper scale refuses; supported scale-only operator does not falsely conflict with orientation; scale drift at P2 refuses and at P7 prevents verified success. |
| Carried constants | Captured MC-01 repeated-key shape as candidate evidence, with explicit missing procedural/metadata evidence refusing; fully supported synthetic positive; null versus unreadable source; active nonconstant keys; contradictory defaults/evaluation; unreadable curve/compression data; shared resources; unknown procedural authority; new writer at P2/P7; no helper writes or missing-key insertion; Full body refuses incompatible helper state; isolated partial operation remains possible. |
| Proportions/placement | Root pose translation differs from preserved model placement; ambiguous placement refuses; structural-offset boundary and beyond-boundary cases; one-ULP P1/P2 drift refuses; scale mismatch refuses; no source offset transfer. |
| Authority | Competing writer, shared log/layer, external constraint, unresolved operator; conflicts introduced at P2 and P7. Proven unrelated differences do not cause blanket refusal. |
| Key planning | Insert/update/exact-key preservation; missing-key non-no-op; quaternion sign/neighbor safeguards; protected metadata and neighboring key integrity; composition of overlapping and disjoint pose scopes. |
| Transactions | Disabled Undo; pre-call refusal; StartUndo/FinishUndo exceptions including older identical history labels; partial/late write failure; verified Abort; failed recovery process-wide lockout; stale callbacks; after-commit uncertainty without automatic Undo. |
| UI/library | Full body beside an isolated excluded face remains available; ambiguous scope receives concise review; an unsupported requested body feature offers Selected parts rather than silent fallback; grouped picker works with native selection seeding unavailable; existing Krystal v2 Save New retains its behavior and honest coverage; Update cannot silently change scope; foreign-library and file-failure protections remain. |
| Dispatch | A non-Krystal v3 supported scope reaches the real common authorization/lifecycle path; unknown rule or disabled capability refuses; envelope v3 does not misroute v1/v2 payloads; legacy regions are not required by v3; deleted/replaced instance and stale record fail before writes. |

Run affected suites on Python 2.7.5 and 3.10.6. Test the new scoped behavior on more than one model structure without adding a per-model engine exception. Retain existing qualified regression evidence; broaden testing only for changed shared code or a concrete failure.

## 12. Bounded native acceptance

Use an existing surveyed direct-FK model for full-body operation and a structurally suitable finger setup. Confirm suitability offline first; do not assume a rigged model's fingers are direct FK merely from their appearance.

1. Save/Update a full-body direct-FK pose, restart and reload it, then Apply to another compatible instance with different model placement. Verify source-blind persistence, skeletal result, preserved placement/proportions/flexes and authored scope.
2. Save finger/thumb articulation; restart/reload; Apply to a compatible instance with a substantially different wrist orientation and arm posture. Verify the intended grip, unchanged wrist/arm inputs, exact key effects and independent parent-relative skeletal result.
3. Apply a full-body pose then the finger pose; verify sequential composition, repeat no-op and Undo/Redo returning through the two exact baselines. Cover insert and update at the selected time.
4. Verify one controlled owned-write failure and recovery, plus offline-covered refusal cases that require native wrapper evidence. Do not repeat every historical fault campaign.
5. Confirm Full body can coexist with an explicitly excluded unfamiliar facial system where its boundary is supported, with unchanged excluded authored inputs and no effects on protected body state. Conversely, an unresolved dangerous dependency or requested unsupported body feature must refuse. Use existing observations for offline preparation; native testing of an actual new boundary reader is required before enabling that case. Do not launch another general model survey.
6. Restore the test installation and preserve original sessions/evidence. Stop on wrong-instance mutation, uncertain authority, unexpected scope expansion, unverifiable recovery or source/oracle disagreement. No improvised repairs or tolerance widening.

Add the following checks to that same bounded qualification, reusing existing fixtures where suitable:

- For a candidate with control-less helpers, establish the procedural-state guard and supported constant-log/extrapolation semantics before enabling its Save/Apply path. Then verify carried local state through an actual parent pose change, navigation and Undo/Redo. Stable observations are corroboration, not a substitute for authoritative procedural/ownership evidence. If the guard cannot establish the boundary, refuse this case and report the precise missing dependency; do not conduct a general procedural-bone survey.
- Include a nonunit ancestor-scale partial case and a selected-ancestor/selected-descendant case separated by an unselected bone. Verify native local/absolute results and protected bridge inputs. These are new scoped combinations, not a repeat of the complete Krystal campaign.

Native-only obligations include parent-frame/scale evaluation, constant-channel/procedural guard semantics, exact-time insertion in the new scope, root placement interpretation, fresh-instance identity, and the new rule's numeric allowance. Current-selection API qualification is required only if that optional seeding feature is enabled. These are focused capability gates, not reasons for another general rig survey. No native success is claimed by this Blueprint.

## 13. Release boundary and remaining decisions

SFP-1 provides a usable direct-FK and finger-pose foundation. It does not by itself authorize v1.1.0 publication or claim universal rig compatibility. The next expansion is automatic full-pose support for the understood standard-rig relationships, using the same scoped planner and engine.

The revised scope decision remains Full body with explicit coverage, not literal skeletal completeness. Reliable automatic anatomical inference is not assumed; ambiguous exclusions use a brief scope review. The specification is ready for Owner authorization of bounded stages A/B, followed by focused implementation review and separately authorized native qualification. No further product-design decision or general audit is required before offline coding. Native execution, installation changes and release remain separately unauthorized.

R1 and R2 remain preserved. No production repository files were edited in preparing this standalone R3 Blueprint. Implementation should incorporate the approved document into project records only when the Owner authorizes that work.


## Appendix A. Independent assessment and evidence limits

Inspected local checkpoint: `6d6e9e6ce15cfc33d2544d74edb97482fc207d79`. Source references below are to `cpm/app/SFM_Character_Preset_Manager.py` at that checkpoint. This review used R2, actual source and preserved native MC-01 observations; it does not adopt the closed Argon reports as authority.

| Question | Verified evidence | Adjudication |
|---|---|---|
| Are source-less helper channels fixed? | Native MC-01 has 79 bones and 211 channels. Both Heavy forearm helpers have position/orientation channels in mode 3, one layer, 20 identical keys at ticks 0–9500, observed current tick 50000, and matching mapped/current evaluation and destination values. Their log `curveinfo` is null. The layer record does not contain complete curve/compression metadata. | They are real constant-looking channel outputs in this observation, not absent writers. Repeated keys and a null source alone do not establish safe passive authority or procedural absence. |
| Is the current passive rule generic? | `prod_body_classify`, lines 43925–43932, uses profile `passive_channel_bones`, then checks one source-less writer and transform log/layer types. | Useful legacy behavior within its existing profile contract; not a sufficient generic inference rule. Keep legacy intact and add section 3.1 for new v3 admission. |
| Does the survey prove procedural behavior absent? | MC-01 lists `evaluateProceduralBones` among model attributes, but does not record its value in model state. | No. Do not assume the helpers jiggle either. A read-only supported guard is a precise remaining dependency for that class. |
| Is scale-aware machinery available? | `prod_body_bone_scale` at 44311, `prod_body_scaled_compose` at 44325, and `prod_body_expected_skeleton` at 44333. The existing loop accumulates bone scale and composes passive/preserved descendants using expected parents. | Reuse primitives and conventions. Add explicit v3 boundary seeding and unselected-bridge semantics. The legacy posed-bone branch maps its whole-body saved oracle, which is not by itself a partial-pose algorithm. |
| Is generic authorization already available? | `prod_pose_authorize`, 41843–41878, selects a registry and rig class and records legacy region keys. | An additive v3 authorization/data adapter is required. Removing registry checks globally would weaken legacy behavior; bypassing common context gates would weaken all behavior. |

The two concerns expose specification gaps, not evidence that the existing qualified Krystal engine has failed. R3 resolves the offline design gaps. Runtime behavior of new generic rules remains unqualified. No SFM execution, production edits or new native observations occurred during this review.

## Appendix B. Bounded implementation checklist for Claude

After Owner authorization of stages A/B:

1. Implement the strict v3 scope/coverage record and compiler; preserve envelope semantics and v1/v2 routes. No per-character profile requirement for ordinary admitted direct FK.
2. Add reusable fixed/constant-carried admission with explicit missing-evidence refusal. Keep source-less channels in authority and preservation inventories; never silently classify procedural uncertainty as fixed.
3. Build one parent-first expected hierarchy with selected articulation, destination bridges/carried locals and cumulative supported scales. Add independent observed source/local/world evidence and analytical counterexamples.
4. Keep document-wide resource discovery and per-attribute operator effects. Preserve P1/P2 admission, exact authored checks, conservative Undo/Abort, one refresh and P7 committed-unverified semantics. Do not add writes to passive helpers, scale, excluded expression or unselected bridges.
5. Connect generic v3 to actual CPM authorization, Save/Update/Apply, lifecycle guard and UI enabled states. Use the grouped picker; optional native-selection seeding may wait. Preserve Owner-approved wording, no ellipses and compact five-tab layout.
6. Run the section 11 focused tests on both supported Python versions, including production orchestration and targeted fault injection. Preserve prior regression decisions; document any concrete changed shared-code dependency.
7. Deliver one implementation review package with source identity, bounded diff, test results and a precise native-gate list. Keep experimental production capability disabled. Do not install or execute SFM under A/B authority.

**Readiness recommendation: READY TO AUTHORIZE SFP-1 STAGES A/B.** The next step is bounded implementation after Owner authorization, not another general architecture review. Passive/procedural and scoped-scale native questions must be resolved before enabling the corresponding scene capability; they do not require postponing the offline compiler, records, picker or integration work.
