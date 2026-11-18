# F-01 Stage 1: native Fox run 1 findings (2026-11-18)

**Authority:** "F-01 Stage 1 — Fox Native Findings and Next Steps". **Status: native qualification BLOCKED, not
PASS.** Diagnosis and proposals only: no CPM, kit or analyzer change, no new native run.

**Run:** `E:\SFM_U0B_Scratch\f01-stage1-fox-r1`, qualification build `5ac0e9d6…` of candidate `35c400c1…`.

**Evidence preserved:**
- the captures PREP, SAVED and BASE;
- two CPM logs (Process A pid 3872, Process B pid 32496);
- the saved record `S1 Fox` (`library_after`);
- the saved session copy `s1_session.dmx` `ba2f7331…`.

**Restored:** library files and folders exactly as before, `RESTORED`, published CPM `ccbed9d7…`, registries absent.

**Automated verdict (unchanged analyzer): INCOMPLETE.** Seven captures are missing: APPLY through ABORT were never
reached.
- The analyzer stops at the first missing capture, so its other gates were **not evaluated**, although the table
  prints them as PASS. That is an analyzer reporting defect; see C6.
- **Owner visual acceptance:** none. Apply never ran.

## 1. What the native run did show

| Observation | Result |
|---|---|
| Structural discovery on Fox A (`foxmccouldwm1`) | Admitted: placement `rig_root`, 22 handles, 34 constraints, 214 written channels, 22 rig-driven and 90 direct bones. **Exactly the offline fixture's description** |
| Save New, Full body | `S1 Fox` saved through the adapter: version 2, `adapter structural_rig_v1`, 214 values. `BODY-RIG-available` logged. Save read-only: all three sets unchanged, PREP to SAVED |
| Reopened after restart | The same record was selected in Process B (BASE) |
| Tails | Refused by structural discovery: control-less bones `HairSpike_B3/M3/T3`, `Tail6_L/R`, `ear3_L/R` ("outside Stage 1"). The v3 refusal was `rig-driven`; nothing saved |
| Placement semantics | On both Foxes `rig_root` **is** the model transform (0.0 units, <5e-6°), and the pelvis sits at the same rest offset above it (0.79, 0, 37.91). Fox B was placed 941 units and 101° away from Fox A |
| Session save and reload | Fox B, its rig and its pose survived the restart. SFM rewrote **71 orientation keys by one float32 step** (at most 4.2e-6°) on all three sets, with no key-time change |

## 2. Finding A: Save succeeds, Apply is disabled

**Cause (exact).**
- The Poses page decides Apply availability, and the Pose Info note, for every non-v3 record through
  `prod_pose_browse_eligible(selection, record, pose_rig_class)`.
  - Code: `ProdWindow` state builder and Pose Info.
  - This requires a **registry** rig class for the selected model, plus a registry mapping from the record's
    `source.rig_class` to it.
- Fox has no registry rig class (`prod_pose_rig_class` → `None`), so every structural record shows
  `not-qualified`:
  - Apply is disabled;
  - Pose Info says "Can't be applied to foxmccouldwm2 / foxmccouldwm1: Full body".
- Stage 1 changed the window's Apply **dispatch** and authorization, but not this **availability** path.
- **Offline reproduction:** the run's own record parses, `prod_pose_rig_class` gives `None`, the eligible regions are
  `[]`, and `apply_pose` is disabled.
- **Why the offline suite missed it.** Its window tests call `apply_pose` directly. The Poses page's button state was
  never exercised for a structural record.

**Record validation and structural matching are not the cause.** The record validates, and the destination was
never read: no Apply operation appears in the Process B log.

## 3. Finding B: the prepared Fox B is not a compatible destination

Even with Apply enabled, this run could not have passed. P1 would have refused Fox B with `rig-differs`. That would
have been the correct, safe result.

- **The two rigs differ.**
  - Fox B, freshly rigged by the **installed** `rig_biped_simple.py`, has **`rig_chest`**: 23 handles and 36
    constraints. `rig_chest` point- and orient-drives `ValveBiped.Bip01_Spine4`, and the neck and collars are
    parented under it.
  - Fox A's rig in the R2 session has **no** `rig_chest`: Spine4 is a directly animated bone there, and the neck and
    collars hang under `rig_spine_2`.
  - Script lines 184, 215, 266 to 282 and 329 always build `rig_chest` (Spine3, falling back to Spine4).
  - So Fox A's rig was built by a different (earlier or modified) script.
- **Correction to the Astra package.** `F01_BROAD_FULL_BODY_COMPATIBILITY_REVIEW.md` says Tails' and Fox's rigs were
  "built by SFM's stock `platform/scripts/sfm/animset/rig_biped_simple.py`". That came from the handle names. Fox A's
  rig does not match what that script builds today. The diagnosis (refusal cause and vocabulary) is unaffected.
- **Under Stage 1's contract** (same model, compatible rig structure, exact comparison), a pose cannot move between
  these two rig versions. Supporting that would be a broadening, a mapping between rig variants, and is not proposed
  here.

## 4. Owner findings

1. **Face review is friction.** The structural route reused the v3 review: it lists JAW and five tongue bones with
   "Leave these controls unchanged", and leaving it unchecked included JAW in the pose (as designed for v3).
2. **Refusal wording.** Tails showed the v3 technical sentence ("parts of this character's body are driven by its
   rig …").
3. **Placement.** The destination's location and facing must be kept. By design `rig_root` is the placement handle:
   - it is never written, and P7 requires it unchanged;
   - every other handle is written in its parent's space, so posture beneath placement reproduces in the
     destination's own place;
   - this matches the review's Option 1 rule that Astra accepted ("placement = the handle constraining the model's
     rootTransform … preserved").

   Natively, `rig_root` is confirmed to be the model transform on both Foxes. That Apply keeps Fox B in place is
   shown offline only, until an Apply runs.

## 5. Smallest safe corrections (proposed, not implemented)

| # | Correction | Scope | Safety |
|---|---|---|---|
| C1 | **Apply availability for structural records.** `prod_body_rig_availability(record, identity, mode)` returns "available" when the record is structural, `prod_body_rig_usable(mode, rule, revision)`, and the model matches the selected character; otherwise `not-qualified` or `different-model`. Used in the two availability places, as `prod_scope_availability` is for v3 | Window state and Pose Info note only | Unchanged: it only enables the button. P1 still drafts the destination and compares exactly, then P2 to P7. A different rig, as in Finding B, refuses with "This character's rig differs from the one this pose was saved on. Nothing was changed." |
| C2 | **Face controls left unchanged by default** on the structural route. The Face-group bones that are directly animated (Fox: JAW, tongue) are recorded as an exclusion with provenance `supported_metadata`, an existing value. There is no review box or checkbox, and the summary reads "Facial expressions, face controls and the rootTransform are not saved." | Structural route only | Only ever reduces writes. The record and validation already carry exclusions; Pose Info lists "Face controls". **Decision:** should v3 Full body (for example Heavy, Engineer) follow the same rule for consistency? That changes RC2 production behaviour |
| C3 | **Refusal wording.** The Save dialog's Full body refusals (`rig-driven`, `carried-unsupported`, `unsupported-body`, and an unavailable structural route) show "Full body poses aren't supported for this character yet. You can still save Selected parts." Codes and details stay in the log | Dialog copy | No behaviour change. **This is a visible production change against RC2** (all characters), needing the Owner's release decision |
| C4 | **Offline test gap.** Exercise the Poses page's real button state and the Pose Info note for structural records (source and destination), and the dialog flow without a checkbox | Tests | — |
| C5 | **Native preparation.** Create **both** the source and the destination Fox fresh in Process A, each rigged with the installed `rig_biped_simple`, and pose the source distinctly. The R2 session's `foxmccouldwm1` becomes an untouched peer. This tests what artists do today (rig, pose, save, apply). Optional, as a recorded safe refusal: Apply `S1 Fox` from an old-rig Fox to a new-rig Fox gives `rig-differs` and writes nothing | Procedure | — |
| C6 | **Kit corrections.** (a) Compare the reopened session with a tolerance: same key times, orientation values within 1e-6 per component (SFM's own reload step). (b) Report gates that were not evaluated as NOT EVALUATED, never PASS. (c) Analyzer and procedure follow C5. Analyzer and procedure pins change accordingly | Kit only | — |

None of these relaxes authored-animation protection, instance isolation, structural verification or recovery.

## 6. Decisions requested

1. Approve C1, C4, C5 and C6 (the Save/Apply contradiction, its tests, and a corrected native run).
2. C2: the structural route only, or v3 Full body as well?
3. C3: accept the Owner's refusal wording for all characters (a production-visible change).
4. Finding B: confirm that poses do not move between different rig versions in Stage 1 (a safe refusal), with
   cross-variant mapping left for a later, separate decision.

No Stage 2 work, new native test, production promotion, push, merge, signing or release.
