# F-01 R3 Amendment 01: generic v3 Full body non-root offset compatibility limit (2026-11-11)

**Status:** Owner-accepted Astra adjudication, **MODIFY R3**. It amends `F01_SCOPED_POSE_BLUEPRINT_R3_20261108.md`
section 5, "Non-root FK positions". Every other R3 text is unchanged.

**Authority text.** The decision as accepted by the Owner ("F-01 — Implement Astra's R3 Position-Tolerance
Amendment", 2026-11-11) is quoted below. Astra's original adjudication document was not supplied to this record; the
Owner's acceptance is the authority quoted here.
> Scope: Generic v3 `direct_fk_v1` Full body non-root position compatibility only. The Owner accepts Astra's
> proposed limit of **0.001 SFM units, inclusive**, using Euclidean distance between saved and destination local
> offset vectors.

## 1. The amendment

| Item | Before (R3 section 5) | After (Amendment 01) |
|---|---|---|
| Generic v3 `direct_fk_v1` **Full body**: each non-root bone's saved versus destination local offset | provisional 0.00005 units | **0.001 units, inclusive**, Euclidean distance of the two local offset vectors |
| Generic v3 **Selected parts**: the same comparison | 0.00005 units | **unchanged**, 0.00005 units |
| **Parent-first composed position** (the expected result against the source's observed model-frame transforms; `PROD_SCOPE_TOLERANCES["position"]`) | 0.001 units | **unchanged**, 0.001 units; separate from the local-offset limit |

**Unchanged:**
- **Destination offsets remain authoritative.** The source's offsets are never imported. An accepted difference
  only permits the Apply; the destination keeps its own offsets.
- **Body root:** its translation remains pose data, and is not subject to this limit.
- **Other policies:** legacy v1/v2 poses (`PROD_BODY_FK_POSITION_TOLERANCE` `body_krystal_v1` 0.00005), model
  identity and checksum, skeletal topology and layout signature, scope, scale and boundary scale, ownership and
  authority, and every angular tolerance.

**What the larger limit does not do:**
- **Composed check:** an offset difference accepted locally but amplified along a chain beyond the 0.001 composed
  limit still refuses (`proportions`; R3 section 5: "do not silently relax the skeletal check").
- **Exactness and coherence obligations still apply:**
  - finite float32 values;
  - agreement between the destination's evaluated channel value and its local transform;
  - P1 pinning, and P2 refusal on a one-float32-step change;
  - existing exact position keys left untouched;
  - missing keys inserted with the pinned destination value;
  - contradictory existing keys refused;
  - P7 verification.

The rule keeps `direct_fk_v1` revision 1. Records saved under it are unchanged and remain valid.

## 2. Numerical evidence (native EF-1, 2026-11-11)

**Run:** `real_sfm_qualification/f01_ef1_full_body/`, STOPPED.
- **B2 and B3** were both refused `fk-position` at P1, before any write, against record `EF1 Body`
  (`0e0390e0…`).
- **Destination B1** (`S0-04`, `2d0c6815…`): its six non-root bones rotated with SFM's rotate tool at preparation
  hold SFM-written local offsets.
- **Source:** drift at most 7.3e-6.
- **All other non-root bones:** within 1.1e-6.

| Bone | Saved offset | Destination offset | Euclidean difference |
|---|---|---|---|
| `bip_head` | (-0.000001, -3.416229, 0.000000) | (-0.000418, -3.416667, 0.000057) | 6.0765e-4 |
| `bip_upperArm_R` | (0.000016, 6.772213, 0.000009) | (-0.000560, 6.772330, -0.000105) | 5.9812e-4 |
| `bip_lowerArm_L` | (11.405773, -0.000004, -0.000004) | (11.405384, -0.000186, 0.000183) | 4.6867e-4 |
| `bip_knee_L` | (15.993519, 0.000000, 0.000007) | (15.993164, -0.000189, -0.000144) | 4.2959e-4 |
| `bip_hip_R` | (-4.588550, 3.357311, -1.242807) | (-4.588762, 3.357121, -1.242864) | 2.9021e-4 |
| `bip_spine_2` | (0.000000, -5.956688, 0.000000) | (-0.000197, -5.956844, 0.000119) | 2.7804e-4 |

The largest difference (6.08e-4) is 12 times the former limit and 61% of the new one. The offline replay of B1 is
in section 3.

## 3. Implementation

`cpm/app/SFM_Character_Preset_Manager.py` (`7548d1eb…` → `f4de5b611bbbb1ee82758fcba7632a00d5e3f41fa27aded356e4ea209a433bde`).
These are the only changes:
- **`PROD_SCOPE_FK_POSITION_LIMIT`** becomes a per-scope table: `{"full_body": 0.001, "selected_parts": 0.00005}`.
- **`prod_scope_compatible`** uses the limit of the pose's scope. It refuses a scope with no limit
  (`structure-unsupported`). It compares, as before, the float32 of the Euclidean distance with the float32 of the
  limit. Its log detail names the scope.
- **The v3 refusal copy for `fk-position`** becomes "A bone's attachment point differs too much from the saved pose.
  Nothing was changed."

**What does not change:**
- **Paths and rules:** the key planner, P1/P2, P7, the composed check and every other tolerance.
- **The legacy v2 route:** its 0.00005 limit and its own copy, `PROD_BODY_FK_POSITION_COPY`.
- **Revision:** `direct_fk_v1` stays at revision 1.

**Details:** the Poses page has no Details facility, and none was added. The offending bones and their distances
remain in CPM's log (`SCOPE-refused` detail).

**Qualification derivation** (one line, 42118: `PROD_POSE_REGISTRY_MODE = u"qualification"`): `fd0844cf3da65148d27ff0833ba186af20854e1f868972f41796163027d1689e`.

## 4. EF-1 replay, before and after

CPM's own engine ran in qualification mode on the native B1 destination (`ef1_destination_b1.json`, derived from
`S0-04` exactly as the scoped fixtures are; all 187 endpoint indices were read natively as 0) with the saved record
(`ef1_body_record.json`, `0e0390e0…`).

| | Before (`7548d1eb…`) | After (`f4de5b61…`) |
|---|---|---|
| Outcome | `fk-position` at P1, the same six bones and distances as the native log to every printed digit; no write | `committed-verified` |
| Channels written | 0 | 144 (72 orientations, the root translation, 71 non-root positions) |
| Non-root position keys | | exactly the destination's own values; keys at other times unchanged; no existing exact key updated |
| Composed 72-bone result versus the saved oracle, model frame | | ≤ 0.000860 units and 0.000019° (worst `bip_head`/`prp_helmet`, where the `bip_spine_2` and `bip_head` drifts add) |

## 5. Regression

`test_cpm_app_f01_scoped.py` adds section AM (29 checks). Requirements, by number:
1. **The six EF-1 offsets:** they match the native measurement and now apply. The drifted offsets are kept, never
   imported.
2. **Composed result:** within 0.001.
3. **Position keys:** they hold the exact destination values.
4. **The inclusive boundary:**
   - **Local rule in isolation:** the largest float32 offset within 0.001 is admitted, and the next float32 step is
     refused with the new message, writing nothing.
   - **End to end at the exact boundary:** the outcome is either a verified Apply or a composed refusal that writes
     nothing.
5. **Euclidean length:** a component vector (0.0006 on each axis, length 0.00104) refuses.
6. **Composed chain:** two locally admitted offsets aligned along a chain refuse at the composed check, writing
   nothing. So does a single admitted offset under the ancestor scale 1.2.
7. **Material changes:** 0.05 units, and a different bone length (1 unit), refuse.
8. **P2:** a destination 0.0009 away applies, but a one-float32-step change between P1 and P2 refuses as `stale`,
   writing nothing.
9. **Selected parts unchanged:** 0.00004 applies; 0.00006 and 0.0009 refuse. The legacy v2 limit and copy are pinned
   unchanged.

In section I, the Full body offset rows move to the new rule: 0.00004 and 0.00006 apply, 0.002 refuses.

Model identity, parent membership, writer and ownership refusals are covered by the existing sections, which are
unchanged and pass.

**Suite results.** Baseline is `7548d1eb…`; after is `f4de5b61…`, whose hash was checked at the start and end of the
run.

| Suite | Baseline (3.10.6 / 2.7.5) | After (3.10.6 / 2.7.5) |
|---|---|---|
| f01_scoped | 389/389 / 389/389 | **424/424 / 424/424** |
| f01_scoped_page (2.7.5 only) | 14/14 | 14/14 |
| f01_body (legacy v2, Krystal) | 246/246 / 246/246 | 246/246 / 246/246 |
| f01_pose_core | 255/255 / 255/255 | 255/255 / 255/255 |
| f01_pose_live (legacy v1 left arm) | 104/104 / 104/104 | 104/104 / 104/104 |
| f01_pose_integration | 204/204 / 204/204 | 204/204 / 204/204 |
| f01_pose_library | 87/87 / 87/87 | 87/87 / 87/87 |
| f01_pose_page (2.7.5 only) | 119/119 | 119/119 |
| m06_static_play_flex | 334/334 / 334/334 | 334/334 / 334/334 |
| m06_instance_resolution | 179/179 / 179/179 | 179/179 / 179/179 |
| m05_static_scale | 114/115 / 114/115 | 114/115 / 114/115 (pre-existing `A9 no scattered 'mode in (1, 3)'`, from the SFP-1 dependency code; unchanged) |
| empty_states (2.7.5 only) | 15/15 | 15/15 |
| canonical_route (suite) | 84/85 / 84/85 | 84/85 / 84/85 (historical `derivation.added_top_level_is_bounded`; no name added) |

## 6. Limitations

- **Two limits can bind at the boundary:**
  - **The composed check:** the unchanged composed 0.001 check can bind before the new local limit. Under an ancestor
    scale s > 1, a local difference d composes to roughly s·d. At the exact boundary, the source/destination
    composition noise (a few 1e-6, direction-dependent) can decide either way. Both cases refuse safely, but such a
    destination is refused as `proportions`, not `fk-position`.
  - **The float32 sliver:** the local comparison uses float32, as before. A distance within float32 rounding of
    0.001 (up to 1.00000005e-3) is admitted locally, and it can then only be refused by the composed check.
- **Not native evidence:** offline replay only. A native repeat of EF-1 needs separate authorization.
- **Message copy for `proportions`:** unchanged, "different body proportions". Astra's wording was approved for
  `fk-position` only.
