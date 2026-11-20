# F-01 Stage 2: declared JIGGLE leaf compatibility, offline implementation (2026-11-19)

**Authority:**
- Astra's ruling, `F01_STAGE2_ASTRA_JIGGLE_RULING.md` (the original ACCEPT WITH CONDITIONS adjudication);
- the scope, `F01_STAGE2_JIGGLE_LEAF_SCOPE.md`;
- the Designer's "F-01 Stage 2 — Implementation Authorization": ACCEPT the scope with the dependency clarification;
  checkpoint `f286a18`.

**Status: implemented and qualified offline; experimental (qualification build only).** Nothing was installed or run
in SFM, and nothing was signed, released or promoted.

## 1. Code identities

| Item | Identity |
|---|---|
| CPM | Stage 1 candidate `7259e80a…` → **`001377f9704ffd4e52503330feea2d4dcf271dd9541a6889d109f6801985de70`** (1,533,738 B; 164 lines added, 14 removed) |
| Exact diff | `F01_STAGE2_JIGGLE_LEAF.diff` (`git diff f286a18 -- cpm/app/…`) |
| New suite | `cpm/convergence/tests/test_cpm_app_f01_jiggle_leaf.py` `e9f57924…` |
| Tails fixture | `cpm/convergence/tests/fixtures/f01_body/tails_shot15.json` `5b9601b9…` |
| Fake scene | `cpm/convergence/tests/fake_sfm_body.py` `9bec46d9…`: one opt-in hook, `simulate_jiggle`; inert unless called |
| Expectation updates | `test_cpm_app_f01_structural_rig.py` `901ad452…` and `test_cpm_app_f01_pose_page.py` `e268021a…`: the "unknown revision" example moves from 2 to 3 (section 4) |

**The Tails fixture** was derived read-only by the existing `f01_dmx_body_fixture.py` from the R2 fixture session
(`259ea8a6…`, unchanged afterwards).
- Source: animation set `milestailsprower1` (GUID `799e8612…`), shot15, t_doc 2083, the same moment as Fox's fixture.
- Contents: 131 bones, 22 handles, 35 operators and 362 channels.

## 2. What changed (stage E part 4, the structural rig adapter)

### Admission (`prod_body_rig_draft` step 7; `prod_body_rig_leaf_admission`, pure)

A control-less bone becomes a **simulated leaf** only when all of these hold:
- **Channels:** exactly one source-less transform channel per attribute.
- **Header:** it matches the scene skeleton exactly by index, name and parent.
- **Declaration:** the header declares it `STUDIO_PROC_JIGGLE`, with `BONE_ALWAYS_PROCEDURAL` set and none of the
  physics or screen-align flags.
- **Leaf:** it has no child, either in the scene or in the header.
- **Parent:** its parent is a bone that is not itself control-less. That covers directly animated, preserved and
  rig-driven parents.
- **Consumers:** none reads it. The concrete consumers checked are a header attachment, a bone flex driver, a rig
  constraint using it as target or pole, and an instance channel reading its DAG or transform.

**Refusals:** every other control-less bone still refuses, with the code `structure-unsupported`, the same artist
message as before, and a log line naming each bone's reason.

**Harmless relationships do not refuse,** following the Designer's dependency clarification:
- the hitbox and vertex usage bits in `0x504`;
- a non-bone element parented below a leaf, such as a prop;
- attachments on other bones.

There is no exhaustive scene-graph search. Followers outside the instance are treated as they are for every other
bone.

The admission works from mechanism and relationships only. No character, model or bone name appears anywhere.

### Header evidence (`prod_body_rig_header`)

- It reuses H1's read-only `prod_scope_helper_evidence` unchanged and adds the `vs.studio` value of
  `STUDIO_PROC_JIGGLE`.
- It never raises: unreadable evidence admits nothing.
- It is read in `prod_body_discover` **on the structural route only.** The registry route (Krystal) never reads it.
- Every phase re-drafts, so a changed declaration refuses at P2 and gives `committed-unverified` at P7.

### The class and its obligations

`simulated-leaf` is a new class, **not** `passive`.

| Where | Change |
|---|---|
| `prod_body_classify` | Assigns the class from the draft's `simulated_leaf_bones`, with the channel role `simulated-leaf`. |
| Descriptor (Save/Apply compatibility) | The leaf's channel rows (role, owner, attribute, log and layer types) are compared exactly. Its **values are not**: each destination keeps its own authored values. |
| Payload | No saved value and no oracle for a leaf. |
| `prod_body_expected_skeleton` / `prod_body_verify_skeleton` (no-op and P7) | **No transform obligation, local or world.** The leaf's scale is still checked. |
| P2 and Abort recovery (`prod_body_same_state`) | **Unchanged.** Its authored channels, keys and layers are already in the exact authored-state comparison, and the descriptor, classification, authority and header (through the re-draft) are compared exactly. These comparisons never included bone transforms, so the exemption needs no change here. The suite confirms simulated motion between P1 and P2, and after an Abort, does not refuse. |

### Records

- **Revision 2:** `structural_rig_v1` **revision 2** exactly when simulated leaves are described. Without them a record
  stays revision 1, so Fox's drafts, descriptors and records are byte-identical to Stage 1's.
- **This build** accepts revisions 1 and 2. The structural record schema adds the class and role.
- **`prod_body_rig_validate`** enforces the following. Any failure gives `invalid-file`.
  - the revision matches the content;
  - each leaf has a parent that is described and is not itself a leaf;
  - each leaf has no child;
  - each leaf owns exactly its two `simulated-leaf` channels, and no other bone carries that role;
  - the oracle covers exactly the non-leaf bones.
- **Older readers:** the Stage 1 build and RC2 both refuse revision 2.
- **Registry (Krystal) record form:** unchanged; it refuses the new class.

Also unchanged:
- the transaction, verified Abort, recovery lockout and the Redo-history exception;
- the UI, messages and tolerances;
- the v3/H1 route, where JIGGLE remains unadmitted;
- Krystal's registry route, and production status (the adapter stays experimental).

## 3. Offline qualification

**`test_cpm_app_f01_jiggle_leaf.py`: 139/139 PASS on Python 2.7.5 and 3.10.6.**

| Section | Covered |
|---|---|
| A. Admission (14) | Tails drafts with exactly the 7 leaves. Classes: 22 constrained, 102 FK, 7 simulated-leaf; no passive. 14 leaf channels, never written (238 written: 34 handle, 204 FK). The descriptor holds channel rows without values. The draft is deterministic. Without a header every leaf is refused as unreadable. The probe logs `simulated_leaves`. |
| B. Refusals (44) | One per criterion, each with its logged reason: each physics and screen-align flag, `ALWAYS_PROCEDURAL` absent, QUATINTERP or undeclared, an attachment, a flex driver, a header name, parent or extra-bone mismatch, the JIGGLE constant or the helper constants unreadable, a missing, `None` or raising header accessor, a jiggle chain (both bones named), a rig constraint following the leaf, a channel reading its DAG or its transform, an exclusion naming a leaf. **Harmless:** a prop parented below a leaf, and attachments on other bones. |
| C. Live, simulated (18) | Save is read-only and writes revision 2 with no leaf value or oracle. Apply goes to a destination posed differently, with **different authored jiggle values** and leaves that move after every evaluation. It commits one owned Undo entry. **P7 verifies while the leaves move.** The body takes the source posture (< 0.001 units, < 0.01°). Leaf keys are unchanged and only planned channels changed. The destination keeps its own jiggle values. Undo and Redo are exact. A repeat Apply is a true no-op while the leaves move. An unsimulated destination verifies. A destination with one leaf not admitted refuses and writes nothing. |
| D. Rig-driven parent (2) | A variant with `Tail6_L` under the rig-driven `bip_hand_L` is admitted, and Save and Apply verify. |
| E. Boundaries (16) | **At P2** (after P1): leaves moving don't refuse. A changed leaf key, leaf scale or header declaration refuses and writes nothing. **At P7:** each of those changes gives `committed-unverified`. The exemption is narrow: a moving **non-leaf** bone (`Tail5_L`) fails P7, and a wrong rig-driven body fails P7 while the leaves move. **Recovery:** a partial-write failure (with a re-evaluation after the Abort) is a verified Abort; a pending Redo cleared by SFM gives `redo_cleared`; a failed Abort is `recovery-unverified`. |
| F. Records (17) | Revision 2 validates. 13 malformed forms are invalid: revision 1 with leaves, 0, 3 or a boolean; a class/role mismatch; a leaf channel claimed preserved; a leaf with a child; a leaf under a leaf; a leaf without a parent; the role on another bone; an oracle for a leaf; a saved leaf value; revision 2 without leaves. The Stage 1 build (`7259e80a`, from Git) and RC2 (`ede599f`) refuse revision 2. |
| G. Unchanged routes (9) | **Fox:** the draft and descriptor are identical to the Stage 1 build's; Save writes revision 1, which the Stage 1 build reads; Apply verifies; revision 2 on a Fox record is invalid. **Krystal:** the registry route reads no header; its record validates and its record form refuses the class. |
| H. Production and teeth (7) | **Production:** the build doesn't offer the adapter, and Apply is `not-qualified` with nothing written. **Teeth:** the Stage 1 build refuses Tails ("outside Stage 1"); the same moving leaves classed as `passive` fail skeleton verification while `simulated-leaf` verifies; with the admission disabled, Tails refuses. |

The remaining 12 checks are the fixture pins (4) and the section completions (8).

**Independent teeth:** the whole suite was also run against the Stage 1 CPM (`7259e80a`) in a scratch copy. It fails from
the first admission check onwards.

## 4. Regressions

The full regression (the v1.1.0 runner plus the structural rig suite: 100 result lines) was run on the candidate and
on a worktree of `f286a18`. The page and r15 suites depend on where they run, so they were also compared with the
in-repository Stage 1 baseline.

**Only two checks differed, and both were expectations about revision 2:**
- `E.c1_availability_refuses_production_other_models_and_unknown_revisions` (structural rig);
- `S3 an unknown adapter revision stays disabled` (pose page).

Both used revision 2 as their example of an *unknown* revision; Stage 2 now defines it. The example moved to revision
3, and the assertion is unchanged. Afterwards: structural rig **298/298** (2.7.5 and 3.10.6), pose page **131/131**.

**Everything else is identical to the baseline**, including the pre-existing historical failures:
- canonical route `derivation.added_top_level_is_bounded`, already failing since Stage 1's names. Stage 2 adds six
  names it doesn't list: `PROD_BODY_RIG_LEAF_REVISION`, `PROD_BODY_RIG_REVISIONS`, `PROD_BODY_SIMULATED_LEAF`,
  `PROD_BODY_RIG_LEAF_PROC`, `prod_body_rig_header` and `prod_body_rig_leaf_admission`;
- M-05 A9, r14/r15, the normalizer pins, bounded logging and the reference-pinned suites.

| Suite | Result |
|---|---|
| Stage E body | 261/261 |
| H1 helper | 78/78 |
| Scoped | 494/494 |
| Pose live | 109/109 |
| Pose integration | 218/218 |
| Pose core | 255/255 |
| Pose library | 87/87 |
| M-06 | 334/334 |
| Ordering trial | 75/75 |
| Instance resolution | 179/179 |

## 5. Native uncertainties

1. **Where the simulated motion appears.** NQ-S6 saw Ayane's rendered jiggle move while her channels stayed constant.
   It is not known whether the DAG transforms CPM reads also move. The exemption makes either case safe, and the
   native run should record which it is, for information only.
2. **Header evidence on Tails.** The accessors and constants are natively established (NQ-S6, NQ-03, H1). Tails'
   attachment and flex-driver tables are read only at runtime: the offline fixture assumes attachments on other bones
   and no flex driver. If either uses a leaf, Tails refuses safely.
3. **Visual faithfulness.** Astra notes that leaf status doesn't guarantee a minor visual effect. Only the Owner's
   visual check can establish useful posture and the absence of severe deformation.
4. **Rig-driven parent.** It is covered offline only; Tails doesn't exercise it.

## 6. Proposed bounded Tails native test (not authorized)

**Shape:** Fox run 3's kit (`real_sfm_qualification/f01_stage1_fox`), with Tails names. It reuses the qualification
build derivation, pre, install, check, collect-logs and restore unchanged, on a verified copy of the R2 session.

**Process A** (one SFM process):
1. Open the session copy.
2. Add two `milestailsprower` instances, Tails S and Tails D, and apply SFM's stock biped rig to each. Pose them
   visibly differently, including ears, hair and tails.
3. Save **Full body** of Tails S as `S2 Tails`.
4. Open Pose Info.
5. Save the session copy.

**Process B** (after a restart), with captures at BASE, APPLY, NAV, UNDO and REDO:
1. **BASE:** select Tails D.
2. **APPLY:** Apply `S2 Tails`.
3. **NAV:** scrub away and back.
4. **UNDO:** Undo.
5. **REDO:** Redo.

The original `milestailsprower1` is the untouched peer. **Abort is not repeated:** the transaction and recovery
evidence of Stage 1 and the Stage 2 offline cases is reused.

**Automated gates:**
- `BODY-RIG-available` lists the seven simulated leaves; the record is revision 2;
- `BODY-P7-verified` with one owned entry;
- only planned channels change; **the leaves' channels and keys are unchanged at every capture**;
- Undo restores and Redo reapplies the authored state exactly;
- Tails S and the peer are unchanged;
- no refusal, Abort or recovery outcome;
- exact restoration.

Simulated tip transforms are recorded for uncertainty 1 only, never gated.

**Owner, visually and separately:** useful body posture, no severe deformation, and acceptable ears, hair and tails.
Minor differences in the tips are acceptable.

**The kit's changes:**
- the Fox capture and analyzer take the Tails names;
- the analyzer adds the leaf checks and leaves the tip transforms out of its equality gates;
- the pins.

## 7. Restrictions honoured

- No installation, native execution, production promotion, signing, push, merge or release.
- No general physics or procedural-bone support, non-leaf chains, cross-model retargeting or character profile.
- Krystal, Fox and the existing generic routes are unchanged.
- All earlier evidence and verdicts are unchanged.
