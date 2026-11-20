# F-01 RC4: same-model cross-rig pose reuse and rig names (assessment, no product change)

**Authority:** "F-01 — Owner Design Correction: Cross-Rig Pose Reuse" (2026-11-20). **Evidence:** the RC3 smoke's two
Tails records (`F01_V110_RC3_SMOKE_RESULTS.md`; run folder `evidence/library_after/`): `RC3 Tails` (new Tails,
`rig_biped_simple`) and `Tails sit alt` (the fixture's original Tails). CPM unchanged (`026a65cd…`).

## 1. The demonstrated mismatch

| | `RC3 Tails` | `Tails sit alt` |
|---|---|---|
| Skeleton (131 bones, parents), model and bone scales, IK offsets | same | same |
| Rig controls | 23 | 22: **no `rig_chest`** |
| `bip_spine_3` | point and orient constraint from `rig_chest` (zero offsets) | FK (posed directly) |
| Parent of `rig_neck`, `rig_collar_L`, `rig_collar_R` | `rig_chest` | `rig_spine_2` |
| Everything else (19 controls, 4 IK chains, 30 other constraints) | same | same |

**Copying controls by name would be wrong.** Control values are stored relative to their parent control, and three
same-named controls have different parents. The neck and both shoulders would move by the chest's own rotation.

## 2. Why a safe adaptation is possible

Every Full body record already stores two things:
- the control values (what Apply writes);
- each bone's saved posture relative to the character's placement (`oracle`). Apply's final verification (P7)
  already checks every bone of the destination against this posture.

The bone postures don't depend on the rig. Checked on both records: composing each record's control chain
reproduces its saved bone postures to within 7×10⁻⁵ units, with 0° rotation difference. That covers the chest,
`spine_2`, neck, head and collars.

For this mismatch, every destination value can therefore be computed by exact rigid composition, in both directions:

| Direction | Destination values |
|---|---|
| 23 → 22 (the Owner's case) | 19 identical controls and their descendants copied. `rig_neck` and the collars: chest value ∘ their own value (re-expressed under `rig_spine_2`). `bip_spine_3`: FK rotation from the saved bone posture. Its position stays the destination's own, as for every FK bone (the existing A1 rule) |
| 22 → 23 | `rig_chest`: solved from the saved `bip_spine_3` posture through the destination's own single-target constraint and offsets. `rig_neck` and the collars: re-expressed under the solved chest |

The result is a **complete** Full body transfer, not a partial one. The existing P7 verification checks the result
against the saved bone postures, exactly as for a same-rig Apply.

## 3. Isolated improvement versus a retargeting project

**Isolated and safe (recommended):** same-model rig reconciliation. It runs only after every existing gate:
- same model, and the selected instance pinned;
- identical skeleton and identical proportions (bone scales, model scale, IK offsets).

It adapts only these differences:
- (a) a control present in one rig only, which drives exactly one bone through a single-target point and/or orient
  constraint (weight 1, no pole), while the other rig poses that bone directly or through such a control;
- (b) controls whose parent differs only because of (a).

Every other control, constraint and IK chain must be identical, as today. The design:
- one pure function derives a destination region (values for the destination's own written channels, the saved
  bone postures unchanged, the destination's descriptor);
- P1 to P7 then run **unchanged**: Motion Editor gate, layer evidence, key plan, one native commit and Undo entry,
  same-state checks, skeleton verification and verified recovery;
- any difference outside (a) and (b) still refuses, with the rig message (section 5).

| Larger project (not proposed) | Why |
|---|---|
| Different IK chains (an IK limb against FK, or different poles) | Solving IK handles and pole placement from bones is underdetermined and needs IK evaluation in the verifier |
| Leaving a control-driven region unchanged while its parent moves | Expected bone postures would need native constraint evaluation; today's verifier can't check that safely |
| Multi-target or weighted constraints, different skeletons, other models | General retargeting |

**Omitted parts:**
- Today's verifier can check one kind of omission safely: an FK-only branch the destination keeps unchanged
  (`fk-preserved`, "follows its parent").
- In the Tails case nothing needs omitting.
- Recommendation: the first increment either adapts completely, or refuses and names the differing controls. Partial
  application of control-driven regions belongs to the larger project.

**Reporting:** the success message states the adaptation honestly, for example
`Pose applied: RC3 Tails (adapted to this character's rig: chest control).`

## 4. Pose Info: the rig name

- **What SFM stores:** the rig element's name, which `rig_biped_simple` creates as `rig_biped_<animation set>`
  (`rig_biped_milestailsprower1`, `rig_biped_foxmccouldwm1`, `rig_biped_krystalv21414` in the R2 fixture).
- **What it doesn't store:** the script that built the rig. Both Tails rigs carry the `rig_biped_` name although they
  differ. A script name can't be captured reliably, and the descriptor deliberately stores `@structural`.
- **Capture at Save:** the pinned instance's rig element name, with the suffix `_<animation set name>` removed only
  when it matches exactly. The current CPM already reads that element (`prod_body_live`).
  - Shown as `Rig: rig_biped`.
  - Otherwise `Custom rig`; no rig element: `No rig`; records saved before this change: `Not recorded`.
  - Tooltip: "The rig's name in the scene. Poses apply only where the rig matches or can be adapted safely."
- **Smallest storage:** the local `pose_sources.json` sidecar, as for Source project. There's no record schema change,
  no payload hash change, and older records stay valid. A record-borne field (travelling with exported poses) would
  need a schema revision; it can follow later.

## 5. Refusal wording (kept for the cases that still refuse)

- Order the scale check after the control and constraint comparison, so a missing control refuses as `rig-differs`
  ("This character's rig differs from the one this pose was saved on. Nothing was changed.").
- Name up to three differing controls (artist-visible names, no hashes or arrays).

## 6. Recommendation

Implement as one RC4 change set:
1. same-model rig reconciliation, scoped (a)+(b);
2. the rig name in Pose Info (sidecar);
3. the refusal ordering and wording.

Each comes with offline tests built from these two records, in both directions. Then a short native check: RC3
Tails onto the original Tails, the reverse, Undo and Redo, unchanged peers. Not started: it needs authorization, as
does the Save New feedback correction.
