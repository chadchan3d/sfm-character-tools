# F-01 Stage 1: Fox native run 2 findings (2026-11-19)

**Authority:**
- "F-01 Stage 1 — Fox Run 2 Authorization" (Owner GO; checkpoint `72e12c6`; candidate `1753bdba…`; qualification
  build `e3e863ee…`);
- the Owner's report "F-01 Fox Run 2 — Native Apply Refusal" (preserve as INCOMPLETE, collect, restore,
  investigate, propose; do not relax validation blindly or change the rig engine).

**Status:** diagnosis only. No code changed.

## 1. Outcome

**Formal verdict: INCOMPLETE.**
- Analyzer: `evidence/S1F_VERDICT.json` `0190a57c…`, `S1F_VERDICT.md` `99830b7d…`.
- EVIDENCE FAILs on the missing NAV, UNDO, REDO, NOOP, UNDO2 and ABORT captures. Every other gate is NOT EVALUATED.

**Owner visual acceptance: not reached.** Nothing was applied.

**Run:** `E:\SFM_U0B_Scratch\f01-stage1-fox-r2`.
- Fox S is `foxmccouldwm2`, Fox D is `foxmccouldwm3`, and the peer is `foxmccouldwm1`.
- Captures PREP, SAVED, BASE and APPLY were taken.
- The refusal happened at the first Apply (step B3). Nothing after it was performed.

**Shown natively in Process A:**
- **Fresh rigs:** both fresh Foxes were admitted with the same drafted description (23 handles, 36 constraints, 214
  written channels; the same description digest at every capture).
- **C2:** `S1 Fox` was saved as a version 2 structural record. `JAW_p` and `JAW_o` were included with no exclusions.
- **Tails:** refused with its cause in the log.
- **C1:** after the restart, Apply Pose was enabled.

**Refusal** (process B log `a7167485…`, `PROD_POSE_BODY-refused`):
- code `rig-differs`, raised by `prod_body_compare_descriptor` in preflight P1;
- outcome `failed-precommit`, with no native or durable commit.

**Restoration:**
- `RESTORED`;
- published `ccbed9d7…`;
- both registries absent;
- the library is exactly as before (the only differences were the pose and `pose_sources.json`);
- the four inventories are equal.

**Preservation:**
- run 1 is unchanged (`S1F_VERDICT.json` `f3dda3c2…`);
- the session record `S1_SESSION.dmx` `a2fbaed2…` and `S1_SPARE.dmx` `61df8bcd…` are unchanged.

## 2. The exact mismatch

The log lists 16 paths, which is its truncation limit. **The full set is five quaternions (20 components):**

| Descriptor constraint | Field |
|---|---|
| 4: IK to `rig_hand_R`, pole `rig_elbow_R` | `solver.startOffset` |
| 5: IK to `rig_foot_L`, pole `rig_knee_L` | `solver.midOffset` |
| 6: IK to `rig_foot_R`, pole `rig_knee_R` | `solver.midOffset` and `solver.startOffset` |
| 35: orient `rig_foot_L` → `L_Foot` | `offsets.oOffset` (beyond the log's 16; derived below) |

**Nothing structural differs.** Names, types, slaves, targets, poles, `poleVector`, `mode`, `vecOffset`, bones,
handles, channels, scale and structural values all pass. The structural values are compared first, and they passed.

**The two rigs are identical as built.**
- The saved session (`S1_SESSION.dmx`, written at A9) stores Fox S's and Fox D's IK offsets bit-for-bit
  identical (0 float32 steps apart in every component).
- These stored values are bit-identical to the record's descriptor.
- So the rigs did not differ at Save. The destination's values changed **when SFM loaded the session in
  Process B**.

## 3. Cause: SFM renormalizes every quaternion when it loads a session

**The model.** On load, SFM replaces each stored quaternion `q` with its float32 renormalization:

```
s = q·q (float32, summed in order),  q' = q × float32(1 / float32(√s))
```

**It is measured, not assumed.**
- **Reloaded keys:** run 2's Process A keys (SAVED) against Process B (BASE), every quaternion key of all three
  Foxes:
  - **618 of 618** reloaded keys equal this function of the saved key, bit for bit;
  - 165 of them changed;
  - the largest change was **2 float32 steps**.
  - Plain `q / √s` explains 518; renormalizing in double explains 347.
- **The descriptor:** applying the function to the record's descriptor changes **exactly** the five quaternions
  above, and nothing else. Its first 16 components are precisely the 16 logged paths, in the logged order.
- **Why only some change:** the rig script writes offsets that are unit length only to within about 1e-7.
  - Those within float32 rounding of 1 survive unchanged (constraint 3, 4 `midOffset`, 5 `startOffset`).
  - The others move by one step (≤ 1.2e-7).
- **The rotation change** is at most about 1e-5°.
- **Run 1's reload rounding** has the same cause.

**It is not idempotent.**
- 73 of the 618 already-reloaded keys change again under a second application.
- Simulation over 100,000 near-unit quaternions and 20 reloads:
  - 13% settle into a 2-cycle;
  - the furthest any reload moves from the original is 9.5 float32 steps (1.1e-6), or 7.6e-6°.

**Who is exposed.**
- A rig built (or rebuilt) in the current session carries raw offsets until its first reload.
- So **any** Full body saved before a restart is refused after it, **even on the same character**:
  - the source itself would have been refused too;
  - so would the common workflow of rigging, saving a pose and continuing tomorrow.
- **Krystal's qualified rig is not exposed today.**
  - Her three native S0 fixtures (taken after many reloads) have 44 of 44 constraint quaternions already at a fixed
    point.
  - The Fox fixture (read straight from the R2 file) has 8 of 42 that would change.

**Classification.**
- **This is not a safety or reproduction problem.**
  - The rig, its structure and its solver inputs are the same up to SFM's own load rounding.
  - The IK result differs by ~1e-5°, far below the posture tolerance (0.5°) and the placement limit (0.001 units).
- **The comparison is overly strict about a value SFM itself does not keep stable.** It treats
  float32-representation noise in constraint quaternions as a different rig.
- **Related latent defect:** `prod_body_descriptor` sorts constraints by their full JSON, values included. A one-step
  change could therefore reorder rows and turn a harmless difference into a misleading positional mismatch.
  - It did not happen here, because the sort key differs earlier, in the slaves.

**Kit consequence.**
- The C6 reopen allowance ("at most one float32 step", from run 1) is **wrong**: run 2 measured 2 steps.
- Had Apply succeeded, the PREP gate would have reported INCOMPLETE for SFM's own rounding.

## 4. Smallest justified correction (proposed; not implemented)

**R2-1: compare constraint quaternions as SFM keeps them.**
- In `prod_body_compare_descriptor` only, the constraint fields `solver.startOffset`, `solver.midOffset` and
  `offsets.oOffset` are equal when every component differs by at most **2^-19** (16 float32 steps at unit scale,
  about 1.9e-6; under 5e-4° of rotation).
  - The sign is not flipped: q and -q stay different.
  - Both values must be finite unit quaternions under the existing checks.
- **Everything else stays exact:**
  - names, types, slaves, targets, poles, `poleVector`, `mode`;
  - `vecOffset` (vectors are not renormalized, and none changed);
  - bones, handles, channels, roles, scale;
  - structural positions and orientations, which keep their own `proportions` and `rig-differs` reasons.
- **Bound:**
  - The bound is about 8 times the measured one-reload change (2 steps).
  - It is about 1.7 times the simulated worst over 20 reloads.
  - It is many orders below any rig difference that matters. Fox's older 22-handle rig differs in structure, and its
    offsets differ by more than 1e-2.
- **No record format change.** Existing records compare as before, apart from this field-level rule.

**R2-2: align constraints by identity, not by value.**
- Before comparing, both sides' constraint rows are matched by `(type, slaves, targets, pole)`, which is unique per
  constraint.
- A different set of identities stays `rig-differs`. Rows are not compared by position in a value-dependent order.
- Records stay as written.

**R2-3: diagnostics.**
- The refusal log gives the total number of differing paths and the saved and live values of the first few, not
  just 16 bare paths.
- The user message is unchanged.

**R2-4: kit.**
- The reopen check requires each Process B quaternion key to equal SFM's float32 renormalization of its Process A
  key, exactly. This replaces "≤ 1 step". It is stricter and fits all 618 keys.
- The capture also records a digest of the compatibility descriptor, so a descriptor-level drift is visible in the
  evidence.

**Tests (offline, before any native run):**
- A fake reload applies the measured function to the destination's constraint quaternions:
  - **teeth:** the current CPM refuses `rig-differs`, reproducing run 2;
  - the corrected CPM applies;
  - it still applies after a second and third reload.
- Still refused:
  - an offset changed by 1e-4;
  - a sign-flipped quaternion;
  - a changed `vecOffset`, pole or target;
  - Fox's older rig.
- Reordering-by-value cannot produce a mismatch.
- Krystal's registry route is unchanged (stage E suites).
- The kit test is updated for the exact reload model.

**Not proposed:**
- a general float tolerance;
- any change to structural, placement, Undo, Abort or recovery checks;
- a change to the rig engine or to SFM's sessions;
- re-saving or normalizing records.

**Alternative, if the Designer prefers no tolerance at all:**
- Accept equality when either value reaches the other within a few applications of the renormalization function.
- It is exact but harder to state, and its 2-cycles need two-sided iteration. Not recommended.

**Run 3 (after approval and offline qualification):** the same procedure, re-pinned to the new candidate, in a new
folder `f01-stage1-fox-r3`. Runs 1 and 2 stay preserved.

No installation, Stage 2, promotion, signing, push, merge or release.
