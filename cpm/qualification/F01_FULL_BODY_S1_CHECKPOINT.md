# F-01 Full-Body S1 — Offline Implementation Checkpoint

**2026-11-06.** Branch `feature/f01-pose-library`. Authorization: "F-01 Full-Body Pose Library — S1 Implementation"
(Owner, 2026-11-06). Design: `F01_FULL_BODY_CONSOLIDATED_DESIGN.md` Revision 2. **Offline only:** nothing here is
natively qualified, and full-body support is **not** production-qualified.

## 1. Identities

| Item | Value |
|---|---|
| CPM `cpm/app/SFM_Character_Preset_Manager.py` | `947d4a11e8754b59a8728e6e846c38d182d72bcb33268d5fb7092e9bcae61178` (production registry mode) |
| Body profile registry `cpm/pose_profiles/cpm_body_profiles_v1.json` | `22dcd1599c0556bcb71df0a9b9d14657684173b3bbf557250710a8104a6baa26` (mapping `krystal-v1` full body: experimental) |
| Left-arm registry `cpm_pose_profiles_v1.json` | `f445d5ef…`, unchanged |
| S0 fixtures (`cpm/convergence/tests/fixtures/f01_body/`) | `s0_shot15` `1fe45db6…`, `s0_shot13` `7851d75b…`, `s0_shot10` `dc9c7b1d…` |

| Commit | Slice |
|---|---|
| `da70d4787e434a0d5a1076a3b0de4c93d5d1eef2` | S1-A/B: design Rev 2, body registry, classification and coverage, descriptor, capture payload, version 2 records, stage A/C hooks |
| `6f845d0180885b57b8e88242c2e40c44490e0927` | S1-C: A1 compatibility, the combined planner, expected authored state and expected skeleton |
| `02b4406e9390d79274e919f36ad46239c1137c6c` | S1-D: live discovery, capture, P1–P7 transaction, deferred verification |
| `20363f3db4a4426dad99c41a5b6831633a88f3ef` | S1-E: Save New, Update Pose, Apply Pose and Pose Info on complete poses |

## 2. What was built

A new stage E block (about 1,400 lines) after stage D; stages A–D unchanged except small, version-gated hooks:
- version 2 dispatch in record validation and parsing (the version 1 size limit and behaviour are unchanged);
- `Full body` part name;
- body mappings in the registry selection;
- the body registry attached at load (missing or damaged: full body unavailable, left arm unaffected);
- the deferred-turn dispatch.

| Part | Content |
|---|---|
| Rig core and coverage | Every bone, rig handle and channel of the pinned instance gets exactly one role from binding evidence (S0 classes: placement, core handle, helper; constrained bone with dormant slave-base channels and IK bone-offset channels; FK written; FK preserved; passive source-less; weights; scale operator outputs; preserved inputs). Anything unresolved refuses. On Krystal: 124 FK + 9 preserved + 21 constrained + 2 passive bones; 278 written channels |
| Compatibility | Exact descriptor: bones and parents, handles and parents, all 36 constraints with solver settings and offsets, channel roles, IK bone offsets (proportions), passive twist values (A3), scale state (bone, handle and model scale, scale operators and controls) |
| A1 | Saved and destination effective FK positions must be equal finite float32 values; otherwise the whole Apply refuses before any write, with "This pose uses different bone positions and can't be applied safely." FK positions are planned like every written channel: missing keys inserted, correct keys left |
| Record | Version 2, region `full_body`: the 278 parent-local values, the placement-relative oracle of every bone, the descriptor; about 250 KB; strict schema |
| Transaction | P1 complete preflight; P2 whole-state revalidation before `StartUndo`; one owned Undo entry with `InsertKeyAtTime` + `SetKeyValue`; post-write checks of every planned layer and the whole instance's authored and observed state; verified Abort restoration; one refresh; deferred whole-skeleton P7; the existing recovery lockout |
| Combined state | One baseline, one plan, one expected authored state, one expected skeleton: posed bones at the saved placement-relative posture; preserved and passive bones following their parents with their own local transforms and hierarchical bone scale |
| UI | Save New creates complete poses only; disabled where no usable full-body mapping exists (the production build). Update Pose recaptures a complete pose in place; Apply Pose dispatches by record version; Pose Info lists Full body |

## 3. Offline results (Python 3.10.6 and 2.7.5)

| Suite | Result |
|---|---|
| `test_cpm_app_f01_body.py` (new) | 158/158 both |
| Pose core | 255/255 both |
| Pose library | 87/87 both |
| Pose integration | 202/202 both |
| Pose live (left arm) | 79/79 both |
| Poses page | 97/97 (2.7.5) |
| M-06 instance resolution / static flex | 179/179, 334/334 |
| M-05 static scale | 115/115 |
| Empty states | 15/15 (2.7.5) |
| Bounded logging | 71/72 (the recorded environmental row) |
| Canonical route | historical row only |

The body suite runs three ways:
- **Pure layers:** against fixtures derived from the native S0 observations. The real Krystal structure of shot15, shot13 and shot10 is classified, compared and planned. The expected-skeleton model reproduces SFM's own evaluated S0 transforms, including bone scale.
- **Live layer:** against `fake_sfm_body.py`, a scene built from those fixtures with a deterministic stand-in evaluator.
- **Window:** through the real `ProdWindow` methods.

It covers every acceptance item of the authorization:
- complete coverage, and refusal of unknown operators and controls;
- independent version 2 save and reload;
- legacy version 1 isolation;
- position and orientation capture;
- A1 refusal before any write;
- insertions where evaluated positions already match;
- correct keys left unchanged;
- refusal of missing, duplicate and layered key structures;
- P1/P2 revalidation;
- late-channel Abort recovery;
- one combined Undo entry with Undo/Redo;
- authorized descendant motion versus unrelated changes;
- the verified repeat no-op;
- preservation of placement, face, gaze, scale, poles, twist and unrelated channels.

## 4. Known limitations and open defects

1. **The fake evaluator is not SFM.** Its IK, constraint offsets and evaluation order are a rigid-covariant
   stand-in. Offline tests prove internal consistency, not that SFM's solver reproduces the saved posture within
   0.01°. Only native qualification can.
2. **Production build.** The full-body mapping is experimental. In the production build Save New is disabled, so no
   new pose can be created (left-arm creation was removed by D4); saved poses still apply. The UI state carries a
   tooltip, but the Poses page does not display tooltips, so the reason is not shown.
3. **A1 strictness on native data.** Instances whose FK positions differ by float noise refuse (shot10: 1–2 ULP in
   19 channels). This is the ruling's intent; it may refuse instances users consider identical.
4. **Undo size and time.** One Undo entry holds about 278 key insertions; native cost unmeasured.
5. **Packaging.** The body registry must be installed beside the CPM (MAINMENU) byte-exact; the release tooling does
   not yet include it.
6. **Evidence breadth.** One rig (Krystal), one fixture, one machine; clocks qualified in one SFM process.
7. **A zero-key written channel** refuses as unreadable evidence in the fake (no value at t); natively SFM may
   return a default value, in which case the planner refuses it instead. It refuses either way.
8. **Stage C hook.** The body registry loader is looked up dynamically (`globals().get`) so suites without stage E
   keep loading the left-arm registry.

No open defect is known in the implemented behaviour; the items above are boundaries.

## 5. Readiness

**Ready for independent technical review** of the stage E block, the registry and the tests before native
full-body qualification. Review should cover:
- the classification rules;
- A1;
- the combined expected state;
- the P5/P7 checks;
- the fake evaluator's assumptions.

## 6. Proposed minimal native qualification (S3)

The run uses the qualification build (registry mode `qualification`, one line, as NQ-1), with the body registry
installed beside it and restored after. It needs one disposable destination session and three short SFM processes.
The S0 observer records before and after each step; it is read-only and unchanged.

0. **Destination preparation (Owner, ordinary SFM editing, SFM saved once):**
   - in a copy of the R2 fixture, pose shot13's Krystal distinctly: spine, hips, arms and legs by their handles,
     tail, ears and fingers by rotation only (no FK bone translation), and open the jaw;
   - move and turn `rig_root`;
   - save as `S3_DESTINATION.dmx`.
1. **Process A, save:** in shot15 at 0.2083 s, in the Motion Editor, Save New (`S3 Full Body`). Expected: a version 2
   record, and the scene unchanged (observer digest). Exit without saving.
2. **Process B, apply:** open the destination at 0.3750 s, in the Motion Editor, and Apply.
   - **Expected:** one Undo entry `Apply Pose S3 Full Body`, P7 `committed-verified`, and every posed bone within
     0.01° and 0.001 units of the record's placement-relative oracle (offline comparison of the observation).
   - **Preserved:** `rig_root`, model placement, jaw/tongue, flexes, gaze, scale, poles and twist keys unchanged.
   - Then Ctrl+Z restores every key, Ctrl+Y reapplies, and a second Apply is a no-op.
3. **Process C, refusals and regression:**
   - Apply in the Clip Editor refuses;
   - Apply to shot10 refuses (proportions);
   - the qualified Pose B left-arm pose applies to shot15 as before.

Pass criteria are the offline acceptance items above, measured natively. The run needs a short procedure and a
comparator built on the S0 analyzer; both need authorization.

## 7. Astra S1 review corrections (2026-11-06)

Astra's disposition of the reviewed checkpoint `03a1e334` was **ACCEPT WITH CORRECTIONS**. The corrections are offline
only and add no architecture or feature.

| Commit | Correction |
|---|---|
| `8323469b6da3637b066ab9e99fff31f02d884b4f` | P1 ownership, P7 authority, P2 A1 and evaluated-state recheck, bindings once per comparison, descriptor pairing by handle |
| `82997bda027c219b7ae93ed6255b4690376ca14e` | The shared Undo validator refuses disabled Undo; full-body `StartUndo` outcomes |

CPM after the corrections: `90cf0987322144bab8445dca01ca516c9c7994654fcf0d0120b4ef68af2ad0ce`. The registries are
unchanged.

| Finding | Correction |
|---|---|
| **P1, ownership** | Discovery records the document-wide authority over the instance from the writer index: every channel writing an instance element, every channel sharing a written channel's log, every log sharing its layer, and every operator slaving an instance DAG. Before any write, Apply refuses an outside writer, a shared log or layer, a driven control, or a constraint outside the animation set. It also reconciles each DAG's slaves exactly with the approved classification. These are the stage D rules applied instance-wide; the version 1 code is untouched |
| **P7, deferred authority** | Fresh discovery reclassifies the instance, and its authority must equal the authority admitted at P1. A newly conflicting writer, shared log or layer, or constraint gives `committed-unverified`, never verified; nothing is undone or aborted |
| **P2, A1** | Immediately before Undo, and again when verifying an Abort, Apply rechecks two things: the A1 predicate against the saved FK positions (exact float32), and that every written channel's owner is evaluated at the same channel value as at P1. After an Abort the reference is the restored original state, never the applied one. P1 also refuses a transform that is inconsistent with its channel |
| **Undo startup** | `prod_pose_undo_problems` (shared) reports disabled Undo. A failure before the native `StartUndo` call is a plain refusal. A failure of `StartUndo` itself is uncertain: recovery-unverified and the `pose_guard` lockout, with no write, no Abort, and never `not-applied`. `FinishUndo` handling is unchanged |
| **Performance** | Bindings are resolved once per comparison phase: P1, P2, Abort verification and P7 each resolve them freshly, exactly once. Previously they were resolved once per planned channel |
| **Ordering** | The descriptor pairs constraints with operators by handle |

Focused counterexamples (suite section `X.*`, 31 checks):
- shared log and shared layer;
- external constraints;
- a conflict appearing after commit;
- a one-ULP evaluated FK change between P1 and P2;
- transform/channel inconsistencies;
- disabled Undo;
- a refusal before `StartUndo` compared with `StartUndo` failing before and after opening;
- `FinishUndo` failing before and after commit;
- the injected qualification fault through the real `pose_guard`, its lockout and refusal of later operations;
- a late Abort restoring keys, transforms and Undo;
- a single binding resolution per comparison;
- constraint-order permutation.

Against the reviewed CPM `03a1e33`, 21 of these checks fail (X.1–X.7 and X.11): those are the defects. The others
confirm behaviour that was already correct.

Results after the corrections, on Python 3.10.6 and 2.7.5:
- full-body suite 189/189;
- pose core 255/255, library 87/87, integration 202/202, live 79/79;
- Poses page 97/97 (2.7.5);
- M-06 179/179 and 334/334, M-05 115/115;
- empty states 15/15 (2.7.5);
- canonical route: historical row only.

Remaining concerns:
1. **Version 1 `StartUndo`.** The qualified left-arm path still treats an exception from `StartUndo` as "not opened"
   and verifies the state. It was deliberately left unchanged (only the shared validator changed), and needs the
   Owner's or Astra's decision.
2. **Cost.** P1, P2 and P7 each traverse the whole document for the writer index; S0's document has about 10,000
   channels. Native cost is unmeasured.
3. **Evaluation during the transaction.** If SFM evaluates during the transaction, verifying an Abort compares the
   transforms with the restored state. A transform that still holds applied values then fails closed (recovery
   unverified) rather than passing.
4. **Native verification still needed.** The limitations in section 4 stand: solver, Undo size, single-rig evidence.
