# F-01 NQ-03: stock-model header inventory, native results (2026-11-09)

**Status:** run once (`NQ03-01`). POST PASS and SESSION CHECK PASS. The Heavy control reproduces NQ-S6 exactly.
14 of 24 models declare no procedural bone. **No model is qualified by this result.**

**Owner verdict (2026-11-10, "F-01 — NQ-03 Closure and Engineer Investigation"):** PASS.
- 24/24 models read.
- 14 without declared procedural bones.
- The Heavy control matches NQ-S6.
- The protected inventories are restored.

Zero declared procedural bones is a **candidate filter, not a generic Full body qualification**. The procedure's step
order is corrected (section 7.1).

**Authorization:** "F-01 — NQ-03 Authorization". The Owner operated SFM. Claude handled preparation, postflight and
analysis. Nothing was installed: the published CPM `ccbed9d7…` stayed in place and was not opened. No pose was
saved or applied, no session was saved, and no model, rig or animation set was changed.

## 1. Run

| Item | Value |
|---|---|
| Kit | `real_sfm_qualification/f01_nq03/` at `24ee3a3` (committed blobs equal to the tested files) |
| Observer | `F01_NQ03_Inventory.py` `745f6dc9…`, wrapping S0 `4a358cc0…`; candidates `9f77ba71…` |
| Session | verified copy of the preserved survey session `47f6b9a0…`, anchored on `heavy1` |
| Console line | `models=24 read=24 not_read=0 no_procedural_declaration=14 readonly=True problems=0` (Owner report) |
| SFM | closed without saving; no unexpected event reported |

## 2. Evidence identities (run folder, not committed)

| File | SHA-256 |
|---|---|
| `observations/NQ03-01.json` | `ed7762b8296d21f2db08b82358273875c81dafc1f514ade70233c8efbb9e6954` |
| `evidence/resolution.json` | `4545b8c918d5bdcecdc07629b169d5b32cc5022dd4b117684537dcfbbf637fd3` |
| `evidence/NQ03_ANALYSIS.json` | `33416889c7b61685cb2126705db2c53482ebae22a2bef362bc2a6e419f0a40ac` |
| `evidence/NQ03_ANALYSIS.md` | `ef501facbc58dd1a93e6e233138dfeb87c0d3a1233fd3719a6d4775f0acb95f4` |
| `evidence/post.json` | `d840c4bc81cfbf3f9e7d46bc24e5363b42fb84d19cc20fa3c1384f0867654977` |
| `evidence/session_check.json` | `f24fb85e03d8bb9d6ec5f817d63366a4698351c8e538b80235dcd9ce67437ecc` |

## 3. Restoration

- **POST PASS:** the installation, the library and the sessions are unchanged. The four inventories after the run:
  - scripts: 1107 files, `39aa9b24…`
  - `usermod/cfg`: 59 files, `f9bb1028…`
  - library: 107 files, `a8bc5a1e…`
  - sessions: 990 files, `b2089b81…`
- **Housekeeping put back:** `cfg/config.cfg`, `demoheader.tmp`, `tf2_playerstats.dmx`.
- **SESSION CHECK PASS:** the preserved survey session is still `47f6b9a0…`.
- **Model files:** for all 24, the post-run `resolve` gave the same SHA-256 as the `pre` pins, with no mismatches.

## 4. Heavy control

`tf/models/player/heavy.mdl` (`69e0188d…`) has header name `player/heavy.mdl`, 79 bones, and is not an error model.

| Index | Bone | Parent | Flags | Procedure | procindex | physicsbone |
|---|---|---|---|---|---|---|
| 77 | `hlp_forearm_L` | 11 `bip_lowerArm_L` | 7172 | QUATINTERP (2) | 432 | 10 |
| 78 | `hlp_forearm_R` | 12 `bip_lowerArm_R` | 7172 | QUATINTERP (2) | 228 | 12 |

These are the only declared bones. All 79 rows were compared with NQ-S6 `NQ-01` (`nq.studio.bones`) on name, parent,
flags, proctype, procindex and physicsbone, and there are **0 differences**. The control is reproduced, so the
classifications below are accepted as the engine's declarations.

The constants were read from the engine and are complete:
- **Procedure types:** QUATINTERP 2, JIGGLE 5, and the rest of the list.
- **Flags:** `BONE_PHYSICALLY_SIMULATED` 1, `BONE_PHYSICS_PROCEDURAL` 2, `BONE_ALWAYS_PROCEDURAL` 4, the screen-align
  flags 8 and 16.
- **`MDLHANDLE_INVALID`:** 65535.

## 5. Classification (all 24 read; none unreadable or not loaded)

| Model (resolved file) | Bones | Class | Declared procedural |
|---|---|---|---|
| `hl2/models/humans/group01/male_07.mdl` | 68 | declared-procedural | 12 QUATINTERP (ValveBiped elbow, ulna, shoulder, trapezius, wrist, bicep, …) |
| `hl2/models/humans/group01/female_01.mdl` | 72 | declared-procedural | 16 QUATINTERP |
| `hl2/models/alyx.mdl` | 85 | declared-procedural | 26 QUATINTERP (legs and arms) |
| `hl2/models/barney.mdl` | 57 | **candidate** | – |
| `hl2/models/kleiner.mdl` | 69 | declared-procedural | 13 QUATINTERP |
| `hl2/models/gman_high.mdl` | 70 | declared-procedural | 14 QUATINTERP |
| `hl2/models/police.mdl` | 57 | **candidate** | – |
| `hl2/models/combine_soldier.mdl` | 44 | **candidate** | – |
| `CSS/models/player/ct_gign.mdl` | 50 | **candidate** | – |
| `CSS/models/player/t_leet.mdl` | 50 | **candidate** | – |
| `dod/models/player/american_assault.mdl` | 56 | **candidate** | – |
| `dod/models/player/german_assault.mdl` | 56 | **candidate** | – |
| `tf/models/player/scout.mdl` | 78 | declared-procedural | `hlp_forearm_L/R` QUATINTERP |
| `tf/models/player/soldier.mdl` | 86 | **candidate** | – |
| `tf/models/player/pyro.mdl` | 75 | **candidate** | – |
| `tf/models/player/demo.mdl` | 84 | declared-procedural | `hlp_forearm_L/R` QUATINTERP |
| `tf/models/player/engineer.mdl` | 72 | **candidate** | – |
| `tf/models/player/medic.mdl` | 92 | **candidate** | – |
| `tf/models/player/sniper.mdl` | 74 | **candidate** | – |
| `tf/models/player/spy.mdl` | 84 | **candidate** | – |
| `tf/models/player/heavy.mdl` (control) | 79 | declared-procedural | `hlp_forearm_L/R` QUATINTERP |
| `left4dead2_movies/models/survivors/survivor_coach.mdl` | 73 | declared-procedural | 10 QUATINTERP |
| `Portal2/models/player/chell/player.mdl` | 77 | **candidate** | – |
| `blackmesa/models/humans/scientist.mdl` | 61 | declared-procedural | `ValveBiped.Bip01_Tie`, `Tie2` JIGGLE |

Each model's file SHA-256 is in `evidence/resolution.json`. Its header name and checksum are in the observation.

## 6. Shortlist (header clean, nothing more)

"Candidate" means only that the engine-loaded header declares no procedure type and no procedural, physics or
screen-align flag on any bone. It does **not** mean qualification.

| Group | Models | Skeleton | Notes |
|---|---|---|---|
| TF2 | Soldier, Pyro, Engineer, Medic, Sniper, Spy | 53 `bip_` bones, the same family as the Heavy | 19–39 extra prop, weapon and helper bones each |
| HL2 / CS:S / DoD:S | Barney, Police, Combine Soldier, GIGN, Leet, American and German assault | `ValveBiped.Bip01_*` | only 2–5 extra attachment or weapon bones |
| Portal 2 | Chell | non-ValveBiped (`root`, `spine1`, twist joints, …) | unconventional naming |

## 7. Anomalies and observations (none blocking)

1. **Procedure ordering (deviation; corrected 2026-11-10).** Step 0 of `PROCEDURE.md` listed `resolve`, `pre`, `copy`.
   - **What happens:** `resolve` creates `<Q>/evidence`, and `pre` refuses while `evidence` exists. On this run `pre`
     refused and changed nothing.
   - **What was done:** the just-generated `resolution.json` and the empty `evidence` folder were removed. Then `pre`
     and `copy` ran, and `resolve` ran after `post`.
   - **Why the identity guarantee held:** the first `resolve` had confirmed that the configuration's model list equals
     the search-path resolution, `pre`/`post` pin those files' bytes, and the post-run `resolve` matched the `pre` pins.
   - **Correction (made under the closure authorization):** the order is now pre, copy, native observation, post,
     resolve, analyze. Step 0 is `pre`, `copy`; step 4 is `post`, `resolve`, `analyze`. `PROCEDURE.md` gains a section
     "Order", and `nq03_tool.py`'s docstring and usage line match.
   - **Checked against the pins and evidence:**
     - The kit pins are unchanged: wrapper `745f6dc9…`, S0 `4a358cc0…`, candidates `9f77ba71…`, published CPM
       `ccbed9d7…`. No code or evidence format changed.
     - The offline tests are unchanged and pass: 9/9 on Python 3.10.6 and 4/4 on 2.7.5.
     - The six evidence files in section 2 still have the recorded hashes.
2. **Release return values.** `Release` returned:
   - 1 for the nine TF2 classes;
   - 2 for the Heavy (whose animation set is in the session);
   - 0 for all others.

   This is read as the cache's remaining reference count, which suggests something else in the process already
   holds the TF2 player models. It is recorded, not explained. It does not affect the header reads and implies no
   write.
3. **`flex_drivers` = 0 for every model.** This counts bone flex drivers only, not facial flex controllers.
4. **Not-procedural helpers exist.** The Spy has `hlp_suitArm*` and `hlp_thigh*` bones that declare nothing. Whether
   such bones have controls is exactly what the next check must establish.

## 8. Further evidence needed per candidate

The header is necessary, not sufficient. Before any candidate can be used for a version 3 Full body:
1. **Control coverage, read-only:** a session with the model added, its animation set giving every bone a direct-FK
   control (none control-less, as the Heavy helpers were in NQ-S6), using the existing S0 and survey observers.
2. **No rig:** the animation set creates no rig and no operators that drive bones.
3. **Behaviour:** its own version 3 Full body native qualification with a pinned qualification build.

## 9. Recommendation (not launched)

For the next control-coverage investigation, the recommendation is **`tf/models/player/engineer.mdl`**:
- It has a conventional humanoid skeleton from the Heavy's family (53 `bip_` bones), so differences from the Heavy are
  attributable to the helpers and not to a skeleton change.
- It has the fewest extra bones among the clean TF2 classes (19).
- Unlike the Spy, it has no non-procedural `hlp_` helpers.

**Alternative:** `hl2/models/barney.mdl`, a ValveBiped humanoid with only 4 extra bones. It would also test a
second skeleton family.

That investigation needs separate authorization.
