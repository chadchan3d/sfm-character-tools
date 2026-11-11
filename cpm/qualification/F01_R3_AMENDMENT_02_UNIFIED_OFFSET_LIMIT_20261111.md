# F-01 R3 Amendment 02: unified generic v3 non-root offset limit (2026-11-11)

**Status:** an Owner-accepted Astra numerical tolerance adjudication. It amends R3 section 5, "Non-root FK
positions", following Amendment 01 (`F01_R3_AMENDMENT_01_FULL_BODY_OFFSET_LIMIT_20261111.md`, preserved unchanged).

**Authority text.** The ruling as accepted by the Owner ("F-01 — R3 Amendment 02: Unify Generic v3 Offset
Tolerances", 2026-11-11) is quoted below. Astra's ruling document itself was not supplied to this record.
> Raise generic v3 `direct_fk_v1` **Selected parts** non-root local offset compatibility tolerance from `0.00005` to
> **`0.001` SFM units, inclusive**, measured as Euclidean distance between saved and destination offset vectors.
> Generic v3 Full body already uses `0.001`. Retain it. Retain the existing `0.001` source-composition and P7
> position-verification limits. Do not raise either to `0.002`. Do not alter legacy v1/v2 behavior.

## 1. The rule after Amendment 02

| Limit | Value |
|---|---|
| Generic v3 `direct_fk_v1` non-root local offset compatibility, **Full body** (Amendment 01) | 0.001 units, inclusive, Euclidean |
| Generic v3 `direct_fk_v1` non-root local offset compatibility, **Selected parts** (this amendment; was 0.00005) | 0.001 units, inclusive, Euclidean |
| Parent-first composed position against the source's observed component-relative transforms (`PROD_SCOPE_TOLERANCES["position"]`) | 0.001 units, **unchanged** |
| P7 position verification of the evaluated result against the expected (the same tolerance) | 0.001 units, **unchanged** (not 0.002) |
| Angles | 0.01° and 0.001° effective, **unchanged** |
| Legacy v1 left arm and v2 registry Full body (`PROD_BODY_FK_POSITION_TOLERANCE` `body_krystal_v1`) | 0.00005, **unchanged** |

**Why:** the revision prevents unnecessary refusals caused by small numerical differences that normal SFM
operations introduce. Native EF-1 showed SFM's own rotate tool moving destination offsets by up to 6.08e-4.
Amendment 01 admitted that for Full body. A Selected parts pose containing the same bones was still refused at
0.00005; the offline evidence is in section 3.

**Unchanged:**
- **How poses are applied:**
  - destination non-root offsets are authoritative and never imported;
  - existing correct keys are preserved exactly, and missing keys are inserted with the pinned destination value;
  - contradictory existing keys refuse;
  - P1/P2 revalidate the destination state exactly, so even a one-float32-step change refuses;
  - parent-first composition uses the destination's parent frames and supported carried intermediate bones;
  - unselected and protected authored state is preserved;
  - Undo/Redo, the verified Abort and P7 behave as before.
- **Structure and scope:** the model, skeleton, hierarchy, scale and writer checks, scope selection, pose coverage
  and the transaction rules.
- **Revision:** `direct_fk_v1` stays at revision 1.
- **History:** the historical SFP-1 NQ1 result is not rewritten. It remains qualified for the specific workflow it
  tested (candidate `2d791dec…`, Selected parts, Krystal).

## 2. Implementation

`cpm/app/SFM_Character_Preset_Manager.py`: `f4de5b61…` (Amendment 01) → `3da2b6537d67bc4c55ae7952f24f86ec61ea4f51b2c6721078a3a159a466a35d`.
- **Changed:** one value, `PROD_SCOPE_FK_POSITION_LIMIT["selected_parts"]`, from 0.00005 to 0.001, and its comment.
- **Unchanged:** no other line.

**Qualification derivation** (one line, 42118): `bb0433a985620d599fc75574ab749b3b8c603488f812612afdd79a7dfe17c343`.

## 3. Coverage (Astra's minimum; `test_cpm_app_f01_scoped.py` section AM2, 49 checks, plus AM and existing sections)

| # | Requirement | Where |
|---|---|---|
| 1 | Inclusive 0.001 boundary and the next float32 above, both scopes | AM (Full body), AM2 (Selected parts, unscaled body): local rule at and above; end to end, a verified Apply or a composed refusal without writes |
| 2 | Euclidean distance: components within, length beyond | AM, AM2 (0.0006 per axis; length 0.00104) |
| 3 | EF-1 native-derived offsets; a Selected parts subset with an affected bone | AM: the B1 Full body replay. AM2: Selected parts saved on native A2 (`ef1_source_a2.json` from `S0-02`), applied to native B1 for `bip_head` (6.08e-4) and the right arm (5.98e-4). Each was refused under the former 0.00005 without writes, and applies under Amendment 02 with exact destination position keys and only the selected inputs changed |
| 4 | Material attachment changes; incompatible models; parent changes; unsupported writers | AM, AM2 (0.05, 1 unit); existing `different-model`, AX3 (parent identity and membership), J/C (competing, shared and cross-boundary writers) |
| 5 | Accumulated parent-first discrepancies, ancestor-scale amplification | AM (Full body chain; scale 1.2); AM2 (finger chain; finger2 0.00095 under cumulative 1.08): refuse `proportions` without writes; existing G (scale) |
| 6 | Fingers under a substantially rotated destination wrist | AM2 (offsets 0.00004, 0.00006 and 0.0009 under the placed destination's hand turned 75°); existing F |
| 7 | Mixed selection with unselected carried intermediate bones | AM2 (upper arm and hand, forearm bridge; hand 0.0009): the bridge and carried fingers receive no write; existing F, AX2 |
| 8 | Exact destination offsets, existing keys, neighbouring keys, layers, metadata | AM, AM2 (position keys at the tick equal the destination values; other keys unchanged); existing K (neighbours, sign flip); the EF-1 comparator's key-level checks |
| 9 | One float32 step between P1 and P2 | AM (Full body), AM2 (Selected parts): `stale`, without writes; existing I, G, AX1–AX3 |
| 10 | Wrong composition, protected-key changes, P7 position errors above 0.001 | existing F (self-consistent wrong planner never verified), J/AY/AZ (P7 committed-unverified); AM2: an expected position 0.0011 off is never verified, and 0.0009 off verifies (P7 limit unchanged at 0.001) |
| 11 | Krystal NQ1, Full body regressions, legacy routes | the scoped suite (section K, Krystal fingers; section I, Full body) and the other suites below, unchanged |

**Results** (CPM `3da2b653…` and test file `dd3466f9…`, both hashes checked at the start and end of the run):
- **Scoped suite:** 472/472 on Python 3.10.6 and on 2.7.5, up from 424 after Amendment 01.
- **Unchanged from the baseline on both interpreters:**

  | Suite | Result |
  |---|---|
  | f01_body | 246/246 |
  | f01_pose_core | 255/255 |
  | f01_pose_live | 104/104 |
  | f01_pose_integration | 204/204 |
  | f01_pose_library | 87/87 |
  | m06_static_play_flex | 334/334 |
  | m06_instance_resolution | 179/179 |

- **Python 2.7.5 only, unchanged:** f01_scoped_page 14/14, f01_pose_page 119/119, empty_states 15/15.
- **Historical rows, unchanged:** m05_static_scale 114/115 (pre-existing `A9`); canonical_route 84/85 (historical
  `derivation.added_top_level_is_bounded`).
- **EF-1 kit:** 23/23 on Python 3.10.6 and 9/9 on 2.7.5, with the new pins.

## 4. Limitations (as Amendment 01)

- **At the exact boundary, the composed or P7 0.001 check can bind first.** This happens under ancestor scale above
  1, or through source/destination composition noise. Such a destination refuses as `proportions`, safely.
- **The float32 sliver:** the local comparison uses float32 rounding up to 1.00000005e-3.
- **Offline only:** no native evidence of this amendment.
