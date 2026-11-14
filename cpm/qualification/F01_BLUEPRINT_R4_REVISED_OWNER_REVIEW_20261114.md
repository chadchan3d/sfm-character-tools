# F-01 Pose Library — Blueprint R4: Revised Owner-Review Edition

**Revision:** R4, targeted corrections dated November 14, 2026.  
**Disposition:** FINALIZED FOR OWNER APPROVAL.  
**Authority:** Owner Design Directive and Owner Review and Additional Corrections supplied in this conversation.  
**Boundary:** Design and evidence assessment only. This document does not authorize coding, installation, native SFM execution, capability enablement, commits, signing or release.

The November 13 R4 draft is preserved unchanged. This edition supersedes that draft's Heavy, schema, numerical follow-up, UI and work-order provisions where they differ. Historical Blueprint documents and qualification verdicts remain unchanged.

## 1. Product objective and retained foundation

Deliver useful pose saving and reuse across compatible SFM characters. A useful pose with minor imperfections is preferable to refusing the entire operation. Protection against wrong-instance writes, damage to unrelated authored animation and unverified recovery remains mandatory.

There are exactly two ordinary choices: **Full body** and **Selected parts**. There is no Available parts mode, strict-mode selector or procedural-bone picker.

Retain the existing scoped compiler, Save/Apply engine, v1/v2/v3 readers, library safety, selected-instance authority, Motion Editor timing, exact key planning, one owned transaction, verified Abort, recovery pause, same-time refresh and deferred verification. Preserve destination placement and proportions and the accepted Full body anatomical-root translation policy. No new blending, mirroring, automatic floor fitting, general retargeting or transaction engine is proposed.

R4 revises the completeness and acceptance policy of R3, including its accepted amendments; it does not discard R3's ownership and preservation protections. Any later Body Preset correction is a separately bounded diagnosis and change, not an incidental rewrite of M-05/M-06 to implement poses.

## 2. Evidence and classification

The reviewed F-01/PS-2 source baseline is repository checkpoint `8eb00f83feb0844aaa5c45addb2fc8293a0a5df0`, CPM SHA-256 `84cd996c914f82bcc41414413958a5a9b536fca088081d862559f48a69144568`. For the PS-2 investigation, the archived application in the PS-2 staged package was independently hashed to that identity. Findings below refer to this source, not to possible subsequent local edits.

| Evidence | Established conclusion | Limit |
|---|---|---|
| Engineer EF-1 and PS-2 pose rows | Useful generic Full body behavior and the listed preservation/history checks | Not universal rig compatibility |
| Soldier PS-2 | Generic Full body Save/Apply and listed history checks pass | Only the observed case |
| Krystal PS-2 | Selected parts and legacy left-arm operations pass | Current production Full body availability is not established |
| Valid Krystal S3 observations and supplemental runs | Full-body capture, application, persistence, update, no-op, navigation, history and recovery evidence exists | Later SFP-1 dialog/dispatch integration still needs checking |
| Heavy NQ-S6 | 77 controlled bones and two declared QUATINTERP forearm helpers, both skeletal leaves | Leaf status alone does not prove absence of relevant consumers |
| PS-2 Body Preset operations | Two commits followed by failed full-map bone-scale verification | Cause and final numerical scale agreement are unresolved |
| PS-2 duplicate-model Undo | Target control digest restored; target model digest differed; same-model peer digests preserved over Apply/Undo | Digests cannot identify the differing fields or prove full graph restoration |

Keep these classes distinct:

- **Proven product restriction:** Krystal Full body is unavailable in the current product path despite demonstrated useful v2 functionality. This is a restoration priority within F-01 development, not proof that the v2 engine is broken.
- **Unresolved observation:** Body Preset verification and the duplicate-model post-Undo model-state mismatch.
- **Hypothesis:** delayed evaluation, possibly exposed by Happy's later refresh. It is neither confirmed nor dismissed.
- **Permitted artistic limitation:** a declared procedural helper produces a minor visual difference or an artist makes a small adjustment afterward.
- **Safety hazard:** unplanned writes, wrong-instance mutation, shared writable authority, destructive graph changes or unverified recovery. These cannot be waived as artistic imperfections.

S3's run-level procedural FAIL concerned missing or wrong-context test steps. It was not evidence that a procedural-bone comparator failed. Preserve the original verdict, reuse valid observations and close only present integration gaps. The PS-2 aggregate FAIL likewise remains recorded without erasing its successful pose rows.

## 3. Full body and Selected parts contracts

**Full body** captures and reapplies the usable body posture through all supported pose inputs in the chosen route. It includes supported secondary articulation and the accepted anatomical-root movement relative to destination placement. It preserves proportions, excluded expressions and unrelated authored animation.

It does not promise identical reconstruction of every hidden or procedural output. A bounded output may remain under normal SFM control. An unsupported independent articulation may remain at the destination only where its isolation is established and the material omission is communicated. This is not permission to omit major supported anatomy merely to pass a test or call a finger-only result Full body. Reuse an existing rig mapping where available.

**Selected parts** reproduces the saved selected controls. Do not silently drop an explicitly selected unsupported control. Preserve unselected authored inputs; their visible descendants can move with parents or supported dependencies. Finger articulation continues to use destination parent frames without acquiring wrist or arm writes. Preserve R3's existing Selected parts anatomical-root rule. Apply uses the saved scope, not a later UI selection.

Technical route selection occurs before mutation. There is no fallback to another route after a failed Apply. Supported v2 Krystal and generic v3 remain internal routes, not separate artist-facing modes.

## 4. Coverage and safety: bounded changes only

Keep the existing W/A/D/P machinery. It must distinguish reproduced inputs/results, preserved authored inputs, and any specifically admitted SFM-managed visual outputs. These are obligations, not a requirement to build a new general classification framework.

For a permitted engine output:

1. CPM does not author its output, alter its keys, switch off its procedure, detach its rig or bake it.
2. Relevant authored channels, configuration, relationships and shared resources remain protected.
3. Existing dependency checks establish whether its effects can reach authored inputs, placement, another instance or reproduced anatomy in a way that invalidates the planned operation.
4. An existing supported external follower may remain external. A returning dependency, competing writer or unresolved relevant writable effect still refuses.
5. P2 and P7 recheck the boundary at their existing lifecycle points. A postcommit mismatch cannot be retrospectively excused by declaring a new limitation.

Do not require a readable exact rendered matrix or a complete procedure formula where neither is needed to establish these obligations. Conversely, unreadable required ownership/recovery evidence is not a visual limitation.

Do not expand discovery to every hypothetical operator. Inspect an additional relationship only where the observed scene or supported engine contract gives a concrete reason it can invalidate a required protection. Existing conservative handling remains for unsupported relevant mechanisms. Unknown machinery elsewhere is not, by itself, a reason to deny an independent useful pose.

## 5. Krystal restoration — first priority

Restore the existing v2 mapping rather than approximating the rig through generic FK.

The earlier comparison found all 53 top-level `prod_body_*` function bodies identical to S3 checkpoint `e98b90b` after normalizing line endings. This supports reuse; it does not establish that shared dependencies or current dispatch are unchanged. The inspected body-registry identity was `22dcd1599c0556bcb71df0a9b9d14657684173b3bbf557250710a8104a6baa26`, with the mapping experimental.

The bounded integration assignment, after authorization, is:

- Retain the mapping and reuse the valid S3 evidence, including the supplemental scoped and legacy results. Do not rewrite historic verdicts.
- Check `ProdWindow.save_pose`, scope-dialog routing, Update, record loading, Apply and deferred dispatch. Generic inventory construction must not prevent an otherwise supported v2 route from reaching the dialog or operation.
- Inspect changed shared dependencies only where they affect this route. Make the minimum necessary capability-status, pin or packaging changes in the qualification candidate; do not redesign body functions or spoof a v3 record.
- Exercise actual dispatch offline, including existing v2 records and unaffected v1/v3 routes.
- Use one short later Owner-operated integration sequence: Save Full body, reopen the saved record, Apply to a visibly different compatible instance, Update and Undo/Redo. Check placement, useful whole-body result and relevant preservation through the current product path.

Reuse S3's broad full-body and verified Abort evidence unless a changed dependency materially affects those guarantees. No complete S3 rerun or perfect reconstruction of its procedure is required. Restore availability once the actual integration and safety checks pass. Heavy and unrelated UI work are not prerequisites.

## 6. PS-2 investigation — findings from existing evidence

### 6.1 Body Apply and Happy

The following timestamps are UTC as recorded in the pid6592 native log; they correspond to the local November 13 session.

| Operation | Recorded sequence |
|---|---|
| Body, operation 8 | Commit 00:32:01.399; same-time refresh logged .463; pending .468 with five flex-side changes, two existing scale changes and no created scales; deferred `bone-scales` failure .545 |
| Happy, operation 9 | Commit 00:32:07.509; same-time refresh .580; verified .635, with 14 flex-side changes, zero existing scale changes and zero created scales |
| PS2 Dup Body, operation 18 | Commit 00:36:20.878; refresh .934; pending .940 with five flex-side changes, one existing scale change and no created scales; deferred `bone-scales` failure 00:36:21.028 |

The pinned implementation narrows the interpretation:

- `prod_apply()` initializes an empty scale plan and builds it only for Body. Expression follows its flex path. Happy's zero-scale log agrees with that separation. There is no evidence here that CPM's Happy operation directly wrote scale channels.
- Before `FinishUndo`, changed existing scales must pass `prod_bs_authored_matches()`: source, expression input and key must match the requested native value under the existing predicate. Reaching commit is evidence that these checks succeeded, not an independent dump of their exact values.
- `prod_apply_deferred_verify()` first checks context/time, changed mode-3 authored expectations and graph identities via `prod_bs_play_expectations_hold()`, then flex results. The logged reason `bone-scales` is assigned only after those checks pass and `prod_bs_index_verify_saved()` returns false.
- The latter verifies the full saved scale map, including static classification and physical scale. The failed bone and predicate are not logged. It can fail because of evaluation coherence, a physical mismatch with the preset, or another scale's static state. The label does not prove a specific head or tail output failed.
- Happy requested another refresh about six seconds later. However, Body itself already called `same_time_refresh()`, which uses `SetHeadTimeInSeconds` and `ProcessEvents`, before its deferred check. The missing step is not simply “add the refresh already present.” This historical Body helper must not be confused with the separately guarded Pose refresh lifecycle.

Answers to the Owner's five questions:

| Question | Evidence-based answer |
|---|---|
| Did Body write the intended scales? | The reported writes committed and passed the implemented precommit checks; changed mode-3 authored/identity expectations also passed at deferred verification. Raw per-field values were not preserved, so independent exact numerical reconstruction is unavailable. |
| Authored mismatch, evaluation mismatch or both? | The failing stage was full-map scale verification, after the changed-scale authored checks. This weighs against those changed authored inputs being the immediate failure, but does not identify the failed full-map predicate or exclude an issue elsewhere in that map. |
| Did Happy's refresh make the scales visible? | A refresh occurred; the Owner observed later visible changes. Causation and the point at which evaluation became correct were not measured. |
| Did Happy write scale channels? | The production path and log show no planned existing or created scale writes. An evaluation effect is different from authoring a scale. Expression-scale contamination is not a confirmed defect. |
| Did final scales equal the Body preset? | Not established. The later observation stores model/control hashes, not individual scale values. Happy's verified outcome verifies its expression operation, not the previous Body operation. |

**Disposition:** delayed evaluation remains plausible. No scale-tolerance relaxation, added refresh, retry loop or production repair is justified yet. Preserve exact authored-data obligations and the existing conservative committed-unverified outcome.

### 6.2 Duplicate-model Undo

Use `S-K-DUP-SAVED` as the immediate pre-Apply comparison, alongside the earlier BEFORE report. Comparing SAVED, APPLY and UNDO establishes:

- Target `Krystal`, handle 21688: control hash changed on Apply and returned to `221b441e…` on Undo. Its model-state hash changed from `3f54a557…` before Apply to `0369e43b…` after Apply, then `6bb8f0e0…` after Undo; it did not return to baseline.
- Peer `krystal20201`, handle 49430: control hash `36d86186…` and model hash `1375c484…` remained unchanged over those three observations. Earlier changes while preparing/saving the peer should not be mistaken for Apply contamination.
- Document, shot15 and playhead 0.208299994 seconds agree. The final report exposes `Redo Apply Body Preset`, supporting that the Body operation was undone.
- The APPLY observation had a clothing-visibility action on top of history. This is a documented intervening operation, not proof that it explains the remaining model mismatch.

The observer hashes control value attributes separately from bone transforms and global flex weights. It does not include DAG visibility in those dictionaries, nor preserve the raw dictionaries or key/graph contents. Consequently, a visibility toggle alone is not a direct explanation for the model digest difference. An indirect evaluation effect remains possible but unproved.

**Disposition:** sampled control restoration and peer preservation are positive evidence. Full target-state restoration remains unresolved. The available digests cannot distinguish bone scale, other transform or flex-weight differences, and cannot establish full authored graph restoration. Do not label this wrong-instance mutation, data corruption or harmless lag without field-level evidence.

### 6.3 Smallest remaining diagnostic and correction boundary

Existing PS-2 logs, report schemas, state captures and the pinned source establish the above limits. The unchanged disposable session files do not preserve the unsaved final runtime values. No existing per-scale/per-field capture was found in the run that resolves those gaps. Hashes cannot be reversed into that evidence.

Only after later authorization, if no additional preserved raw evidence is supplied, use one bounded disposable reproduction to record the actual failed scale predicates: requested physical values, native source/key/expression inputs, expression results, output mode/log state, physical scales and identities. Sample at the existing precommit/deferred boundary and after an ordinary settled event turn. If still needed to distinguish the Owner's hypothesis, record the same fields immediately around Happy's existing refresh, including unchanged scale authorship. Include the narrow duplicate Apply/Undo comparison with raw target and peer fields and operation history, without intervening visibility edits. This is a specific diagnostic, not a repeat PS-2 campaign.

If authored values remain correct and only evaluated values settle later, the candidate remedy is a minimal ordering change at the existing guarded postcommit verification boundary. Establish that ordering from the observation before selecting it; do not add arbitrary sleeps, polling, manual retiming, extra Undo transactions or a blanket retry. A changed context must still refuse verification. If the authored state or restoration is wrong, correct that exact path instead. No correction may mark a prior failure verified merely because a later expression looks correct.

The restored v1.0.0 “outside the qualified generic topology” Body refusal is a separate historical compatibility result unless a causal regression is demonstrated. It does not establish new F-01 damage.

## 7. Heavy — smallest reusable compatibility exception

Heavy is the next compatibility change, after the Krystal priority and PS-2 diagnosis; it is not their dependency.

Start with the observed case: 77 directly controlled bones and the two declared QUATINTERP leaf forearm helpers. Reuse NQ-S6 and the feasibility assessment. Do not introduce a general procedural-bone framework, universal operator interpreter, binary parser or exact rendered-output reconstruction.

The narrow rule should admit this supported procedural type when existing scene/dependency evidence establishes the relevant safe boundary. It must be based on the declared mechanism and relationships, not merely the model or bone name. It need not claim support for JIGGLE, physics or every other procedural type.

Capture and plan the supported direct-FK body inputs under the existing placement/proportion rules. Leave both helpers' authored channels, keys, defaults and configuration unchanged. Their normal SFM-driven visual output may move. Include them in existing preservation checks; omit only the unavailable exact rendered-result obligation. Do not classify them as constant.

Inspect only concrete outstanding consumers capable of affecting protected animation: for example, an observed attachment/bone-flex driver, a shared writable graph or a scene dependency returning into protected state. Do not require exhaustive proof about every theoretical consumer. A leaf designation alone is insufficient where an actual relevant consumer exists, but unreadable QUATINTERP trigger mathematics alone is not a reason to refuse useful controlled posing.

**Minimal implementation footprint:** a narrow admission/coverage distinction, preservation of the helper authorship and configuration, and the corresponding expected-result/comparator exception. Reuse existing compiler and transaction facilities. Add record fields only if the present contract cannot reliably identify and preserve the promised coverage across Save/Apply. Do not introduce a general material-omission subsystem merely to support these two helpers.

Qualification must establish useful posture, no severe distortion, unchanged helper authored work, target/peer isolation and existing recovery. Minor procedural appearance differences and small later artist adjustments are allowed. Failure of a supported controlled limb, severe deformation or an authored safety violation is not an acceptable helper limitation.

## 8. Record and compatibility requirements

Keep existing envelope IDs, library hashes and v1/v2/v3 semantics. Do not migrate existing records or silently broaden their scope on Update. Preserve all existing Krystal v2 records and mapping semantics.

The record and its recognized engine contract must make captured scope and verification obligations reproducible. Prefer existing portable identities, coverage descriptors and contract-revision mechanism. If a new interpretation would otherwise make an older strict reader silently misapply a record, allocate a narrowly validated contract revision within v3; do not mislabel relaxed coverage as the old strict promise. No revision number is reserved by this draft.

Do not require a new envelope version, generic procedural graph serialization, driver-formula storage or verbose per-output metadata without an actual need. A recognized narrow rule plus the minimum identities/configuration evidence needed to revalidate it is sufficient. Imported declarations never grant execution authority; Apply independently resolves the live route and refuses dangerous changes or unsupported revisions.

Continue reading legacy records unchanged. A desired coverage change is Save New unless an explicitly supported Update preserves the record's original contract. No mass conversion is required.

## 9. Numerical verification

Separate authored correctness, operation stability, structural compatibility and visual reproduction.

- Preserve exact authored keys, times, neighbors, metadata, graph identity and unrelated-state checks, including existing float32 readback semantics. Do not weaken them to explain PS-2.
- Preserve pinned instance, mode, time, history and ownership checks. Numerical tolerance does not authorize concurrent edits.
- Retain current generic destination-offset compatibility: 0.001 SFM units inclusive, Euclidean, for both scopes. Retain current generic observation limits: 0.001 units position, 0.01 degrees skeletal angle and 0.001 degrees effective-input angle. Legacy v2 keeps its qualified limits, including its 0.00005 FK-position compatibility allowance.
- Preserve destination proportions. A comparison of different compatible structures must use the accepted destination-preserving composition. No new accumulated-error budget or geometry-comparator project is a prerequisite here. Change such a comparator only if a concrete case proves it rejects an already authorized structural difference incorrectly.
- For the narrow Heavy exception, verify preserved helper authorship and its supported effect boundary, not an unavailable rendered helper matrix. Continue verifying reproduced inputs and supported skeletal results.

A marginal visual residual is not automatically corruption; stale evaluation is not authored failure. Both require accurate classification. There is no automatic tolerance widening, percentage-of-bones success threshold or post-hoc exemption. PS-2 does not currently justify any tolerance change.

## 10. P1–P7 and recovery guarantees

Save remains read-only. Pin the live instance and authorized time and capture finite effective values without normalization.

P1 selects the supported route and frozen scope, resolves dependencies, plans one deduplicated write set and records independent original and expected states. Any helper output exemption is explicit before writing.

P2 re-resolves authority and revalidates context, protected inputs and relevant relationships. Unreadable required evidence refuses before mutation. Newly encountered limitations cannot be silently admitted.

The owned transaction writes only planned keys at the authorized time. Disabled Undo, uncertain ownership and StartUndo/FinishUndo exceptions retain conservative handling. Abort only a proven owned open transaction; independently verify the original baseline. Unverified recovery leaves operations paused.

After confirmed Pose commit, retain its one same-time refresh outside Undo and guarded deferred verification. P7 checks exact authored expectations, supported effective inputs and skeletal results, preserved relationships, context and ownership. Postcommit failures remain committed-unverified; do not automatically compensate with Undo. Stale callbacks cannot publish success.

True no-op still requires the necessary key coverage and verified expected state. Permitted engine-managed outputs need not be visually frozen for CPM to have no authored work to do.

These are retained Pose guarantees. The existing Body Preset `same_time_refresh()` uses `ProcessEvents`; this document neither changes it nor treats it as proof of equivalent Pose lifecycle semantics. Diagnose that path separately under section 6.

## 11. UI workstream — assigned separately

Claude's bounded UI corrections proceed independently:

- Taller Selected parts picker.
- Useful, detailed Pose Info.
- Removal of misleading controls in blocked Save dialogs.
- Clearer movement-warning wording.
- Simpler Full body descriptions.

Do not redesign these assignments here. Retain Full body and Selected parts, existing window conventions and legacy behavior. Explain consequential coverage limits without promising visually motionless unselected anatomy. Technical details belong in diagnostics unless they serve an artist's actual decision.

Coordinate only genuine shared changes, such as the dialog's correct Krystal route. UI work need not wait for Heavy or become a condition for investigating Body scales; engine work need not wait for optional presentation polish.

## 12. Bounded work order and acceptance

These are proposed implementation/qualification scopes for approval, not permission to start them.

| Priority | Scope and minimum exit |
|---|---|
| **K — Krystal first** | Existing v2 route restored through current dispatch; affected offline tests and short native integration pass. Reuse S3; no mapping rewrite or complete S3 rerun. |
| **Q — PS-2 investigation** | Retain this source/log analysis; obtain only missing field evidence if later authorized; identify and correct the demonstrated cause. Separate evaluated correctness, authored writes and Undo restoration. |
| **H — Heavy** | One narrow supported helper exception; useful controlled Full body result with authored/preservation/history guarantees and no severe distortion. |
| **UI — independent** | Assigned presentation corrections and short Owner UI acceptance, with engine behavior unchanged. |

Priorities are not artificial serial gates. Krystal does not depend on Heavy or a generic Body Preset redesign. A confirmed defect in a dependency actually shared with a route must be addressed before claiming that route safe; an unrelated unresolved observation does not erase its prior evidence.

For Heavy, add focused offline cases around the changed rule: eligible and structurally equivalent non-name-pinned inputs, a concrete dangerous consumer, helper/peer authored changes, relevant unreadability, changed P2/P7 relationships, preserved record/legacy behavior and the existing transaction's failure/no-op paths. Reuse existing broad ownership and recovery suites rather than inventing a new matrix for every theoretical mechanism. Run affected suites on the supported Python versions.

The later native Heavy check should save/reopen a visibly distinct forearm/body pose, Apply to a compatible disposable target with a peer, check planned keys and supported outputs, helper/configuration and unrelated preservation, useful appearance, navigation, no-op and Undo/Redo. Reuse qualified transaction evidence where code is unchanged. Repeat a targeted partial-write Abort case only if the changed plan/verification integration leaves that new boundary untested. Do not repeat Engineer/Soldier campaigns solely because unchanged paths coexist.

Stop a case for wrong-target writes, unexpected authored changes, unverified restoration, severe distortion or an uninterpretable supported result. Record a permitted minor helper difference as a limitation. Do not create additional administrative approval cycles inside an already authorized bounded run.

Release readiness still requires disposition of actual authored-work and recovery concerns. This Blueprint makes no release decision.

## 13. Other PS-2 findings retained

- v1.0.0 topology refusal remains separately recorded; do not suppress it or claim it is a new regression without evidence.
- Null operator fields and unaccepted UI are missing/negative usability evidence, not automatic proof of mutation failure.
- The recorded 5618 ms worst operation is a performance observation; the report's performance check passed with a finding.
- Cleanup removed a pre-existing empty `_Qualification` directory and it was recreated. The restoration inventory should account for required directory state; preserve this tooling deviation rather than rewriting restoration history.
- Stale pre-PS-2 Ledger/candidate status text needs later authorized documentation reconciliation. It is not stronger evidence than completed native reports.

## 14. Evidence references and limits

Local repository: `E:\SFM-F01-Pose-Library`.

Governing retained records include `cpm/qualification/F01_SCOPED_POSE_BLUEPRINT_R3_20261108.md`, `F01_R3_AMENDMENT_02_UNIFIED_OFFSET_LIMIT_20261111.md`, `F01_DESIGN_ISSUE_DI01_APPLY_IN_PLACE.md`, `F01_FULL_BODY_S3_ASSESSMENT.md`, `F01_SFP1_NQ_S6_INVESTIGATION.md` and `F01_SFP1_QUATINTERP_FEASIBILITY.md`.

PS-2 root: `E:\SFM_U0B_Scratch\f01-ps2-v110-r1`.

- `package/stage/usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py`: independently hashed pinned source. Relevant references: `prod_apply` line 29038; `prod_bs_authored_matches` 24063; `prod_bs_play_expectations_hold` 29713; `prod_apply_deferred_verify` 29899; `prod_bs_index_verify_saved` 26908; `prod_bs_classify_static_scale`; `same_time_refresh` 3532. Line numbers refer only to this archived identity.
- `evidence/logs/CPM - 2026-11-14_00-22-22Z - pid6592 - eace79 - 001.log`: operations 8, 9 and 18, including refresh, deferred outcomes and scale-write counts.
- `evidence/logs/CPM - 2026-11-14_00-54-17Z - pid22904 - fda4f1 - 001.log`: restored v1.0.0 refusal.
- `observations/S-K-PRESETS.json`, `S-K-DUP-BEFORE.json`, `S-K-DUP-SAVED.json`, `S-K-DUP-APPLY.json`, `S-K-DUP-UNDO.json`: digest and context evidence, not raw field snapshots.
- `evidence/PS2_VERDICT.md`, `OPERATOR_REPORT.json`, restoration records and retained library copies.
- Observer interpretation checked against `real_sfm_qualification/f01_ps2_v110/observer/F01_PS2_State.py`, especially `_controls_state`, `_model_state` and `shot_animation_sets`. These explain the recorded hash fields; they do not recover their underlying runtime values.

No SFM, comparators or qualification tests were run for this revision. No repository, installation, registry, session or evidence files were changed. The new standalone Blueprint is the deliverable; earlier drafts remain intact.

## 15. Change summary for Owner approval

1. Krystal restoration explicitly reuses demonstrated S3 functionality and requires only the current integration gap to be closed.
2. PS-2 analysis now distinguishes passed authored checks from failed full-map scale verification, confirms Happy's refresh and zero planned scale writes, and identifies exactly what the existing evidence cannot establish.
3. Duplicate Undo is narrowed to restored sampled control state versus differing model state, with unchanged peer evidence. Clothing visibility and evaluation delay remain hypotheses, not blanket explanations.
4. Heavy is reduced to the smallest reusable exception for the observed procedural helper type. No exact rendered matrices, general procedural framework or unnecessary schema expansion is required.
5. Exact authored safeguards and current numerical limits remain. No speculative refresh or tolerance repair is prescribed.
6. Work order is Krystal, PS-2 diagnosis, Heavy; the Owner-assigned UI corrections proceed separately without artificial dependencies.

**Owner approval requested for this revised design. Implementation and native execution remain separately unauthorized by this document.**
