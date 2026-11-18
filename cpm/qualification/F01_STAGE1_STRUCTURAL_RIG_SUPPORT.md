# F-01 Stage 1: generic structural rig support, offline (2026-11-18)

**Authority:** "F-01 — Stage 1: Generic Structural Rig Support" (proposed Owner authorization: Stage 1 implementation
and offline testing only). Astra's disposition of `F01_BROAD_FULL_BODY_COMPATIBILITY_REVIEW.md`: ACCEPT WITH
CONDITIONS. F-01 Blueprint R4.

**Status: implemented and qualified offline; experimental (qualification build only).**
- Not installed, not run in SFM, not signed or released.
- RC2 stays the release baseline: the production build behaves exactly as RC2, and rigged characters without a
  registry profile still refuse Full body.
- Stage 2 (leaf JIGGLE bones) is not started.

## 1. Implementation and code identities

| Item | Identity |
|---|---|
| CPM | RC2 `7aa0fc4e…` → **`35c400c139901796f1588884171b0667f580755daa37ec961719ed141dc382fc`** (1,509,844 B; 506 lines added, 38 removed; exact diff `F01_STAGE1_STRUCTURAL_RIG.diff` `f731ef5a…`) |
| Fox fixture | `cpm/convergence/tests/fixtures/f01_body/fox_shot15.json` `053787dc…` |
| Fixture reader | `cpm/convergence/tests/f01_dmx_body_fixture.py` (new, read-only DMX reader) |
| Fake scene | `cpm/convergence/tests/fake_sfm_body.py` (two additive features; unchanged for the S0 Krystal fixtures) |
| Suite | `cpm/convergence/tests/test_cpm_app_f01_structural_rig.py` (new) |

**The adapter** is part 4 of the stage E block, `prod_body_rig_*`. It adds no new engine:
- **Drafting.** `prod_body_rig_draft` builds a rig description from the selected live instance, in the registry
  profile's own form. No name decides a role, and no character, model or rig is listed anywhere.
- **Reuse.** The draft then goes through the existing machinery unchanged:
  - the registry's structural rules (`prod_body_registry_parse`, run on a one-profile document);
  - the stage E classifier, descriptor, A1 FK-position check and planner;
  - the P1–P7 transaction, verified Abort, recovery lockout and P7 skeleton verification.
- **Hooks in the existing stage E code.** Each is inert for a registry profile:
  - `prod_body_resolve_profile` drafts for a structural authorization;
  - `prod_body_state` and P7 re-draft from every fresh read and refuse any change;
  - the descriptor's rig name comes from structure;
  - a drafted description carries its own FK-position limit;
  - the capture writes the adapter's record form;
  - record validation accepts either form, and each form refuses the other.
- **Window.**
  - Save New tries the adapter only when there is no registry route and the generic v3 Full body is refused.
  - Apply and Update dispatch structural records to the adapter's authorization.
  - Selected parts and the registry and v3 routes are unchanged.
- **Gating.** `PROD_BODY_RIG_STATUS = "experimental"`, so the adapter is usable in the qualification build only.
  Production never runs the probe, so it adds no log line and changes no behaviour.

## 2. The supported structural rig class

A character is admitted only when **every role is established on its own**:

| Role | Rule |
|---|---|
| Rig | Exactly one rig registration for the instance, with handles |
| Handle hierarchy | Each handle has one parent: the instance's rig or another of its handles |
| Placement | The one rig handle that both point- and orient-constrains the **model transform**. It must be a child of the rig, not driven itself, and its channels are preserved (never written) |
| Constraints | Point, orient and **two-bone IK** only: one target, weight exactly 1, every slave and target inside the instance. IK chains must run start → mid → end as parent and child bones; the target and pole are rig handles. At most one point, one orient and one IK slot per element, and an IK start or mid joint is never also orient-driven. Duplicates refuse |
| Helper handles | A handle a constraint drives must follow exactly one bone, by one point and one orient constraint, and must never be a constraint input. Dependent handles, such as the toes under the foot helpers, stay its children and are written as ordinary core handles |
| Core handles | Exactly one position and one orientation control channel each, both written. A missing or shared channel refuses |
| Pole orientation | Preserved only for a **leaf** handle that is nothing but an IK pole (not a target, no child handles). Otherwise it is written. The solver reads the pole's position; preserving the pole orientation is what Krystal's natively qualified profile does. Every Apply is still verified by P7 |
| Rig-driven bones | Never written. Their posture is reproduced through the handles and verified by P7. Their own offset channels (IK bone lengths) are compared exactly as proportions |
| Direct bones | Exactly one control channel per attribute, written. Each destination keeps its own FK positions (A1, with the v3 Full body limit of 0.001) |
| Face | The existing v3 review, reused: the Face-group bones, limited to directly animated ones, can be left unchanged only by the artist's confirmation (`user_confirmed`). They are then preserved FK bones that follow their parent. For Fox the review offers `JAW` and the five tongue bones. Flex, eye and other non-bone controls stay preserved as before, so they never block a body pose |

**Fox** (stock `rig_biped_simple`) drafts as follows:
- 22 handles, `rig_root` as placement, and the two `rig_footHelper` handles as helpers;
- 34 constraints;
- 34 written and 6 preserved handle channels (`rig_root`, and the elbow and knee pole orientations);
- 90 FK bones and 22 rig-driven bones;
- 214 written channels in total.

**Portability.**
- Not compared: the animation set's name, the rig's name (`rig_biped_<animset>` becomes `@structural` in the
  descriptor) and every enumeration order.
- Compared exactly: the model, the bones, the handles and their parents, the constraint roles, the solver settings,
  the offsets, the scales, the IK bone lengths and the channel roles.
- The rig's own element names, which the rig script generates from the skeleton (handles, constraint operators and
  their channels), are part of the compared structure. A renamed constraint is therefore a different rig.
- Destination elements are resolved by identity inside the pinned instance. Duplicated handles, controls or
  channels, or two rig registrations, refuse.

**Excluded in Stage 1 (each refuses before any write):**
- control-less bones, both jiggle tips (Stage 2) and procedural helpers;
- weighted or multiple-target constraints;
- any other operator type, such as aim, parent, twist or connection operators, and with them reverse-foot rigs;
- handles parented to bones;
- cross-model retargeting: a record of another model refuses with `different-model`.

Krystal keeps her registry profile and route unchanged. The adapter is only tried when there is no registry route.

## 3. Record contract

- **Format.** A structural record is a **version 2** record with an explicit adapter marker,
  `pose.adapter = {rule: "structural_rig_v1", revision: 1}`, in place of `pose.registry`.
- **Region fields.**
  - The region names `profile_id: "structural_rig_v1"`.
  - The descriptor's rig name is `@structural`.
  - The region adds `exclusions`: the artist-confirmed face exclusions, which must equal the descriptor's preserved
    FK bones exactly.
  - Passive bones never appear.
- **Older readers.** RC2 refuses these records as unreadable. This is tested against RC2's own source.
- **Existing records.** Registry records, version 1 and version 3 keep their interpretation.
- **Authority.** Saved metadata never authorizes a write: the destination's own draft does, and the saved
  descriptor must equal it exactly. A forged record that claims an extra written channel refuses.
- **No registry needed.** A structural record does not need the body registry to be read.
- **Pose Info.** It shows a structural record as Full body, with the face exclusion listed under Not included.

## 4. Offline results

**Suite `test_cpm_app_f01_structural_rig.py`: 147/147 PASS on Python 2.7.5 and 3.10.6.**

| Area | Covered |
|---|---|
| Drafting | Fox's roles as above. The unchanged classifier accepts the draft, rig-driven bones are never written, and the descriptor names no instance |
| Wrong roles (23 refusals) | Placement point and orient disagreeing, missing, under a handle or constrained by a bone; two model point constraints; a helper following a handle; a helper used as an input; a bone-parented handle; weighted and multiple-target constraints; an aim operator; a non-two-bone IK; an IK pole on a bone; a target or slave outside the character; a missing or shared control channel; a control-less bone; no rig; conflicting drivers; a repeated constraint; unconfirmed, rig-driven, missing or repeated exclusions |
| Role decisions | A pole with a child handle, or a pole that is also an orient target, has its orientation written |
| Portability | A renamed set and rig with reversed operators, channels, controls, bones and handles drafts the same roles and descriptor, and applies and verifies live. A renamed constraint operator is a different rig |
| Live Save and Apply | Save is read-only and records 214 values. Apply to a distinctly posed and placed copy uses one owned Undo, writes only planned channels and preserves the placement, poles, IK lengths, slaves, weights and flexes. P7 verifies, and the posture matches the source in the destination's own placement to 6e-14 units and 2.4e-6°. Undo, Redo and a repeated no-op Apply all behave as expected |
| Refusals before any write | Changed constraint orientation or position offset (`rig-differs`); a changed IK solver setting; a different IK bone length or handle scale (`proportions`); a missing major control; an FK position beyond 0.001 (`fk-position`; within it, the destination keeps its own value); a duplicated handle (`ambiguous`); two registrations; a shared log; an external constraint on an FK or rig-driven bone (`shared-authority`); another model; the Clip Editor; production Save and Apply (`not-qualified`); an inert production probe |
| P2 and P7 | A rig key or constraint offset changed after P1 is stale, and nothing is written. One partial-write failure after both rig and FK writes ends in a verified Abort (keys exact, no Undo entry). A failed Abort locks recovery. P7 independently catches a wrong evaluated skeleton whose inputs are all correct, and also a structural change, a new external constraint, or a foreign Undo entry after the commit |
| Face | An exclusion is recorded and its bone isn't saved. At Apply the bone keeps its keys and local pose, and P7 verifies. Pose Info lists "Face controls" |
| Records | The record validates with and without the body registry. Thirteen malformed variants and a digest mismatch are invalid. The forged extra write refuses. The RC2 legacy reader (`7aa0fc4e…`, from `ede599f`) refuses the structural record but still reads a Krystal registry record |
| Window | Production keeps the RC2 refusal for Fox, with no probe and no file. The qualification build's dialog offers Full body through the adapter and saves a version 2 structural record. "Leave these controls unchanged" records the face exclusion. Selected parts on Fox stays version 3. The window's Apply dispatch, deferred verification and Update in place all work, and production Apply of a structural record refuses. A control-less bone (as on Tails) keeps the generic refusal |

**Fixture.** `fox_shot15.json` is read from the RC1 smoke's source session (the R2 fixture `259ea8a6…`, never
modified; hash-checked before and after). It is not a native observation:
- handles are element indices;
- world transforms compose the stored locals;
- values come from hold evaluation.

The reader was checked against the native S0 fixture: Krystal derived from the same session file classifies under
her qualified registry profile with **exactly** the native fixture's role counts (124 FK, 21 constrained, 2 passive,
9 preserved FK; 30 handle-written and 248 FK-written channels).

**Fake scene.** Two additive features:
- control groups when a fixture has them;
- handles under a helper follow it before the bones they drive are evaluated again.

Neither applies to the S0 Krystal fixtures, whose body suite is unchanged.

**Regressions:** section 4.1: unchanged against RC2.

### 4.1 Regression against the RC2 baseline

Full regression (`run_regressions_v110`, every CPM convergence suite under its own protocol, Python 2.7.5 and
3.10.6) on the final CPM. Every one of the 59 runs gives **the same result as the RC2 baseline** (`F01_V110_RC2_UI_CORRECTIONS.md`
section 2). The pre-existing rows are unchanged: canonical route 84/85, M-05 A9, r14 and r15 pins, authority adapter,
convergence gates, authority cleanup, bounded logging, and the reference-gated suites. Stage E body 261/261, helper 78/78,
scoped 487/487, pose core 255/255, pose integration 218/218, pose live 104/104, pose library 87/87, pose page 123/123,
scoped page 18/18.

One regression was found and fixed during the run. The first run had pose integration at 172/203 and pose live at
91/104: their harnesses load the window methods without the stage E block, and Apply and Update called
`prod_body_rig_is_record` for version 1 records. Both calls are now guarded by `version == 2`, and both suites are
back to 218/218 and 104/104.

## 5. Remaining native uncertainties

1. **Native discovery equals the fixture (H-1).** The fixture comes from the saved session, not a live read:
   - handle parents and registration elements;
   - channel bindings and the document-wide writer counts;
   - control groups.
2. **SFM's rig evaluation (H-3).** Handle writes on `rig_biped_simple` must compose as P7 expects natively:
   - the two-bone IK with elbow and knee poles;
   - the foot helpers following the feet, with the toe handles beneath them.

   The fake scene is a stand-in, not SFM's solver.
3. **Pole orientations.** That preserving the leaf pole orientations leaves the posture unchanged was established on
   Krystal's custom rig, not yet on the stock rig.
4. **Second-instance portability.** A second Fox rigged in the Owner's scene (another animation set name, so another
   rig name) must give the same native structure, and the operator and channel names the rig script generates must
   be identical.
5. **Ordinary native noise.** SFM's rotate tool moving FK positions on Fox within the 0.001 limit, as seen for
   Krystal and the Engineer.
6. **Unchanged native facts.** Undo, Redo, time and editor behaviour use the primitives already qualified on Krystal
   and Heavy; no new uncertainty is expected.

## 6. Shortest Fox native qualification (proposal; needs Owner authorization)

**Setup.**
- One Owner-operated session on a copy of the RC1 source session.
- The Stage 1 candidate installed as a qualification build, derived by the existing one-line mode switch.
- Reuse the RC1S kit pattern: backups, install, analysis and exact restoration.
- No new harness.

**Process A.**
1. At shot15, select Fox and choose Save New → Full body. The dialog offers Full body, with the face review listing
   JAW and the tongue.
2. Save once with the default (face included).
3. Open Pose Info.
4. Add a second `foxmccouldwm` instance, apply SFM's stock biped rig, and pose it visibly differently.
5. Save the session copy.

**Process B (restart).**
1. Apply the pose to the second Fox and check it visually.
2. Undo, then Redo.
3. Confirm the original Fox, the peer, is unchanged.

**Controls.**
- Tails still refuses Full body with the generic message, and nothing is written (Stage 2 is not implemented).
- Optional: Krystal's registry Full body Save and Apply, unchanged.

**Analyzer gates** (from the CPM log and records):
- `BODY-RIG-available`, `BODY-P1`, `BODY-P7-verified` and the native-commit labels;
- no refusal, Abort or recovery outcome;
- a v2 structural record;
- an unchanged peer;
- exact restoration.

This settles H-1 and H-3 for `rig_biped_simple`. Production availability then needs Astra's review of the evidence
and the Owner's promotion (`PROD_BODY_RIG_STATUS`).

## 7. Restrictions honoured

Nothing was done beyond offline work and local commits:
- no installed production change and no SFM run;
- no Stage 2 work, signing, push, merge, tag or publication;
- no model, animation, session or registry change;
- no Fox-specific code, character whitelist, universal rig interpreter or new qualification framework.

Stopped for Owner review.
