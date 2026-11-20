# F-01 RC4: same-model cross-rig adaptation (implemented offline, not native-tested)

**Authority:** Astra's RC4 ruling (Option B, ACCEPT WITH CONDITIONS) and the Designer's "F-01 RC4 — Astra Ruling and
Implementation Authorization" (2026-11-20). Assessment: `F01_RC4_CROSS_RIG_ASSESSMENT.md`. Kept separate from the Save
New change (`F01_RC4_SAVE_NEW_RESPONSIVENESS.md`) and from Pose Info's Rig row.

## 1. What changed in CPM

| Item | Behaviour |
|---|---|
| Refusal wording (RC3 op 17) | A control or bone present in one rig only is now `rig-differs`, never "different body proportions". Scale differences of the same controls and bones, and IK bone lengths, stay `proportions` |
| `prod_body_rig_adapt` (stage E part 5, pure) | For a structural record whose rig differs from the destination's, it either builds a temporary destination-specific plan or refuses, naming the unsupported relationship |
| P1 (`prod_body_preflight`) | Calls the adapter only when the exact comparison fails with `rig-differs` on the structural route. The plan replaces the saved values for the destination's own written channels. The record's region stays the skeletal reference: P7's expectation and the no-op test use it, never the adapter's region |
| P2 and the Abort check (`prod_body_same_state`) | Besides every existing comparison, the adaptation is derived again from the fresh read and must be identical |
| P3–P7, Undo, Redo, recovery | Unchanged: the same planner and neighbouring-key protections, one owned Undo entry, verified Abort, no compensating Undo, tolerances unchanged |
| Message | "Pose applied: <name>. Adapted to this character's rig." (`applied-adapted`, chosen from the pending record's `adapted` flag) |

## 2. When the adapter adapts

Applicability is decided from structure only; no control or bone name is special. All of the following must hold:
- **Same model and skeleton:** the same model and an identical skeleton (names, indices, parents).
- **Same proportions:** identical IK bone lengths and passive values (exact), model and bone scales, and the same scale for every common control.
- **Common controls mean the same:** each common control has the same class, and the same parent once the extra controls are collapsed.
- **Common constraints match:** every constraint not involving an extra control matches by structural identity. Offsets are compared under the established equivalence (`prod_body_compare_constraints`, unchanged). This covers IK chains, poles, consumers and helpers.
- **Each extra control** (present in one rig only) is a core control under a common control, with no scale. It is the single target of exactly one point and one orient constraint of one bone: zero position offset, identity rotation offset within the established limit, plain solver. Nothing else uses it.
- **Each converted bone** is constrained in one rig and posed directly (FK) in the other. It is explained by exactly one extra control and has no other driver.
- **Channel differences** are only the extra controls' two written channels and constraint weights, and the converted bones' own two channels (FK-written against slave-base).

**How the destination's values are derived:**
- **Same relationship:** the saved value is copied exactly.
- **Control attached under another parent:** the same placement-relative pose, re-expressed under its destination parent.
- **FK → control:** the control takes the saved bone's posture from the record's skeletal reference.
- **Control → FK:** the bone's rotation comes from the reference. Its position stays the destination's own (A1). The adapter checks before writing that the saved position is reachable within the existing A1 allowance (0.001), and otherwise refuses with "This pose moves bip_spine_3 in a way this character's rig can't reproduce. Nothing was changed."

Anything else refuses with "This character's rig is set up differently from the one this pose was saved on (*relationship*), so the pose can't be adapted safely. Nothing was changed."

## 3. Offline qualification: `test_cpm_app_f01_cross_rig.py`, 123/123 on Python 2.7.5 and 3.10.6

**Fixtures:**
- `tails_shot15.json`: the R2 session's original Tails, 22 controls.
- `with_chest()`: the 23-control variant, built by cloning the fixture's own `rig_spine_2` structure. Its roles and relationships match the native `RC3 Tails` record.
- `fixtures/f01_body/rc3_tails/`: read-only copies of the two native RC3 smoke records, hashes pinned.

| Section | Covers |
|---|---|
| M | The op 17 pair now refuses as a rig difference, not proportions; real scale and IK-length differences stay proportions |
| N | The native records, with expectations computed independently using the fake scene's own transform math (the adapter's results are never reused). Both directions; copied values exact; reattached controls, the solved chest and the directly posed spine reproduce the saved postures; determinism; order independence. Refusals (exact copy): rotation or position offset on the extra control, extra control driving two bones, used as a pole, scaled, other solver, missing weight channel, unexpected consumer, control attached elsewhere, different IK pole, different skeleton, another bone controlled differently, unreachable spine translation, bone scale (proportions), other model |
| A | The variant drafts as the native 23-control rig and keeps the scene's posture |
| C | Live P1–P7, chest→FK, FK→chest, production mode and reordered constraints: one owned Undo; P7 verified against the saved reference; posture reproduced (independent fake evaluation); own placement and facing kept; only planned channels change; neighbouring keys untouched; placement, poles, IK lengths, weights, leaves and flexes kept; Undo, Redo, repeated Apply is a no-op, final Undo; a same-rig Apply is not adapted |
| G | Unreachable chest translation and offset chest control refuse before any write; an external driver of the converted bone refuses (shared authority) |
| T | P2: a changed chest relationship and a changed parent control are stale; P2 re-derives the adaptation. Failure injected after adapted writes, both directions: verified Abort restores the exact original state. P7: a changed relationship and a wrong converted bone are unverified. P7's expectation is the saved reference in the destination's placement |
| W | The adapted success copy, and plain refusal copy that says nothing was changed |

**Teeth:** against the committed CPM without the adapter, the suite fails 14 of 37 checks before later sections can run.

## 4. Finding: the Owner's native case still refuses, for a numerical reason

The two native records (the newly rigged `RC3 Tails` and the session's original Tails) differ structurally exactly as
assessed. They also differ, independently of the chest, in limb constraint offsets beyond the established equivalence:

| Field | Largest difference | Established rule |
|---|---|---|
| Arm IK `startOffset` / `midOffset` (both arms) | 0.0013° | ≤ 0.0005° (Astra numerical ruling, Stage 1 run 2) |
| Hand orient constraint `vecOffset` | 6.0×10⁻⁶ units | exact |

The original rig was built separately, possibly by an earlier version of the rig script; that isn't established. Rig
scripts compute these offsets from the bones when they run. Under the unchanged limits:
- the adapter refuses this pair with "…(its arm or leg controls were built with slightly different offsets)…";
- the test `N.native_pair_*_refuses_on_offsets_not_the_chest` records this.

The adaptation tests isolate the structural difference by giving the destination the record's common offsets.

**Consequence:** RC4 as implemented cannot transfer the Owner's demonstrated pose natively. Doing so would need a
ruling on the equivalence limits for separately built rigs (for example, a bounded allowance for IK start and mid
offsets and for constraint position offsets, verified by P7 as now). The Designer and Astra required that limits not
be widened without a ruling, so none were changed.

**Native test preparation:** not prepared. A test of the Owner's case would refuse on this point, and a test between two
freshly rigged instances cannot produce the 22-control rig. Stopped for this decision.

## 5. Limitations

- Single-bone, zero-offset point and orient conversions only, with any number of controls re-attached around them.
- No partial adaptation; IK differences, weighted or multi-target constraints, and other skeletons or models refuse.
- Offsets outside the established equivalence refuse (section 4).
