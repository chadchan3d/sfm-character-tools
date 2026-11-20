# F-01 RC4: Astra's numerical compatibility ruling, implemented (offline, not native-tested)

**Authority:** Astra's ACCEPT (bounded static-offset equivalence) and "F-01 RC4 — Implement Astra's Numerical
Compatibility Ruling" (Owner/Designer GO, candidate `3813184` / CPM `da60e0d9…`). This resolves the open finding in
`F01_RC4_CROSS_RIG_ADAPTATION.md` section 4 (that section is kept as written).

## 1. The bounds

These apply to the saved-record versus destination comparison, on the **structural-rig route only**
(`prod_body_compare_descriptor(..., structural=True)` at P1, and the adapter's comparison of common constraints).

| Field | Rule | Bound (inclusive) |
|---|---|---|
| IK `startOffset`, `midOffset` | rotation angle (normalized copies, q/−q equivalent, `abs(norm − 1) ≤ 2⁻¹⁹`) | **0.005°** (`PROD_BODY_RIG_ROTATION_LIMIT_DEG`) |
| Point and orient `oOffset` | the same | **0.005°** |
| Point and orient `vecOffset` | Euclidean distance between finite 3-vectors, presence equal | **0.0001 units** (`PROD_BODY_RIG_VECTOR_LIMIT`) |
| IK `oOffset` | unchanged | 0.0005° |
| IK `vecOffset`, every other field | unchanged | exact |

**Unchanged:**
- **Registry profile route (Krystal):** keeps 0.0005° and exact vectors (default `structural=False`).
- **Structure before offsets:** unique constraint identities and topology are established before any offset is compared. Targets, named slaves, poles, types, weights, solver settings, dependencies, control relationships and proportions are checked as before. The destination's actual offsets and constraint graph are used; source offsets are never substituted, the record is never modified, and nothing accumulates across applications.
- **Chest-control eligibility:** an added or removed chest control still needs a zero `vecOffset` and an identity `oOffset` within 0.0005°, as before.
- **P2, Abort and P7:** P2's exact destination stability, Abort's comparison with the captured baseline, and P7's independent skeletal reference and limits (0.001 units, 0.01°).

**Logging:**
- `BODY-rotation-equivalent` carries the limit actually applied.
- New: `BODY-vector-equivalent` (distances, limit).
- The adapter logs its own comparison the same way (`prod_body_log_equivalent`).

## 2. Measured offsets of the two preserved Tails records (not aligned)

`RC3 Tails` (newly rigged, 23 controls) against `Tails sit alt` (the original, 22 controls). There are 76 common
offset fields, 12 of them different. Everything not listed is identical.

| Constraint | Field | Difference |
|---|---|---|
| IK, left arm (`bip_hand_L`) | startOffset | 0.00130373° |
| IK, left arm | midOffset | 0.00121562° |
| IK, right arm (`bip_hand_R`) | startOffset | 0.00103521° |
| IK, right arm | midOffset | 0.00102021° |
| Orient, `bip_hand_L` | vecOffset | 6.03341×10⁻⁶ units |
| Orient, `bip_hand_R` | vecOffset | 3.82214×10⁻⁶ units |
| Orient, `bip_hand_L` | oOffset | 3.13929×10⁻⁵° |
| Orient, `bip_hand_R` | oOffset | 1.911×10⁻⁵° |
| IK, left leg | startOffset / midOffset | 3.59×10⁻⁶° / 1.33×10⁻⁶° |
| IK, right leg | midOffset | 1.51×10⁻⁷° |

The largest values sit within the new bounds: 26% of the angle bound and 6% of the distance bound. Both directions now
adapt.

## 3. Offline evidence

**`test_cpm_app_f01_cross_rig.py`, 191/191 on Python 2.7.5 and 3.10.6** (it was 123/123). The native records are now
used **without alignment** throughout. Section K:
- the constants, and the measured offsets above;
- both directions adapting from the original records, which are unchanged;
- for each of IK `startOffset` and `midOffset`, orient `oOffset` and point `oOffset`: admitted at 0.9999× the bound, refused at 1.0001×, inclusive exactly at the bound (measured angle), and the profile route keeping 0.0005°;
- an IK `oOffset` keeping 0.0005°;
- `vecOffset`, orient and point: below, at and above 0.0001; components of 0.00006 each that pass individually but jointly exceed it (refused); 0.00005 each (admitted); the profile route and IK `vecOffset` staying exact; invalid values and presence differences refused; sign-equivalent `oOffset` admitted; the norm envelope unchanged;
- still refused: a changed target, pole, type, slave, solver mode, pole vector, duplicate identity, missing constraint, extra dependency, control parent or weight channel; IK bone length and bone scale (as proportions); offsets beyond the bound between the records, with the adapter naming them;
- live P1–P7 with the destination's own offsets moved inside the bounds (an arm IK start and mid offset by 0.004°, a hand `oOffset` by 0.004°, two `vecOffset` values by 5×10⁻⁵): same rig, chest → FK and FK → chest all verify, with CPM logging the 0.005 and 0.0001 limits. The largest independent skeletal error in the fake scene was 0.000455 units and 0.004°, inside P7's unchanged 0.001 units and 0.01°. Undo restores;
- P2: a destination offset change within the bounds after P1 is stale, before any write;
- after the commit, a destination offset change prevents a verified success;
- Abort restores the destination's own captured baseline (its own offsets);
- P7 still detects an incorrect reproduction.

Section N's refusals of chest offsets now include small nonzero offsets inside the new bounds (0.001° and 10⁻⁶
units), which are still unsupported.

**Teeth:** against the pre-ruling CPM (`3813184`), the suite reaches 107/114: section K fails before later sections can
run.

**Regressions:** every existing suite keeps its result, including the Stage 1 numerical-ruling tests, which pin the
profile-route rule through the default comparison. The full regression is recorded in the commit.

## 4. Native preparation

`real_sfm_qualification/f01_rc4_cross_rig/`:
- **Files:** `PROCEDURE.md`, `rc4x.template.json`, the capture `observer/F01_RC4X_Capture.py` (the pinned Stage 2 and Fox captures, unchanged, plus an offsets sidecar), `tools/rc4x_tool.py` (reusing the Stage 2/Fox/K2/S3/UA-1 chain), `tools/rc4x_analyze.py` (reusing the Fox analyzer's helpers) and `tests/test_rc4x.py` (31/31).
- **Run shape:** one SFM process on a disposable copy of the R2 session, never saved, with the differently rigged Tails pair.
  - Two poses are saved first (`RC4 Chest` from a new 23-control Tails, `RC4 Sit` from the original 22-control Tails), then transferred in opposite directions.
  - Each direction: posture, placement and facing, authored and neighbouring keys, peer isolation (Fox), navigation, Undo, Redo, repeated no-op and final Undo.
  - One controlled Abort after adapted writes.
- **Recorded:** the maximum independent skeletal errors and the actual destination offsets. P7 limits are not widened.
- **Status:** not installed and not run; it needs the Owner's authorization.

## 5. Remaining limitations

- The bounds cover the static offsets listed; any other numerical difference still refuses.
- Cross-rig adaptation stays limited to single-bone, zero-offset point and orient conversions. There is no partial adaptation, no IK offset solver and no general retargeting.
- All evidence is offline; native behaviour remains to be qualified.
