# F-01 Stage 2: native Tails qualification, preparation (2026-11-19)

**Authority:** the Designer's "F-01 Stage 2 — Native Tails Qualification Preparation" (ACCEPT the offline
implementation for native preparation; checkpoint `208a977`; candidate CPM `001377f9…`). Implementation record:
`F01_STAGE2_JIGGLE_LEAF_IMPLEMENTATION.md`.

**Status: prepared, not run.** Nothing is installed: the published v1.0.0 CPM `ccbed9d7…` is in place, with no
registries. Installation and the native run need the Owner's separate authorization.

## 1. The kit: `real_sfm_qualification/f01_stage2_tails/`

| File | SHA-256 | Role |
|---|---|---|
| `observer/F01_S2T_Capture.py` | `3bd20f07…` | Runs the Fox capture (`F01_S1F_Capture.py`, pinned `765eefc2…`) unchanged, with the seven steps PREP, SAVED, BASE, APPLY, NAV, UNDO and REDO. Then writes the leaf sidecar `S1F-<step>.leaves.json`, through CPM's own read-only `prod_body_live` and `prod_body_rig_header`. |
| `tools/s2t_tool.py` | `1579842c…` | `build`, `pre`, `status`, `install`, `check`, `library`, `collect-logs`, `restore`, `analyze`. It reuses the Fox, K2, S3 and UA-1 tools unchanged, with this kit's session names (`S2T_SESSION.dmx`, `S2T_SPARE.dmx`). |
| `tools/s2t_analyze.py` | `a76b7a80…` | The verdict (section 2), reusing the Fox analyzer's helpers. |
| `PROCEDURE.md` | `480ac08a…` | The operator procedure and the Owner's steps. |
| `s2t.template.json` | `5b7e36eb…` | Paths and pins: candidate `001377f9…`, qualification build `7d3ed720…` (line 42630 only), the R2 fixture `259ea8a6…`, and the Fox kit's shared pins. |
| `tests/test_s2t.py` | `d4417adf…` | **79/79** on Python 3.10.6 and **25/25** on 2.7.5 (the wrapper and template; the analyzer and tool are Python 3 tools). |

**The leaf sidecar** records, for Tails S, Tails D and the peer:
- the header status (READ or UNREADABLE, with its reason);
- every header-declared procedural bone: index, name, parent, flags and procedure type, and whether a local attachment
  or a bone flex driver uses it;
- the scale field of each declared bone;
- the constants.

If runtime attachment or flex-driver evidence refuses Tails, both the sidecar and CPM's `BODY-RIG-leaf-refused` log
line give the exact reason.

**Its design follows the Designer's requirements:**
- **Instances:** two fresh Tails, both rigged with the installed stock `rig_biped_simple`, and the original
  `milestailsprower1` as the untouched peer. The analyzer requires S and D to share the same drafted description under
  different rig names; it never assumes the older rig matches.
- **Order:** all posing is finished before PREP. The session copy is saved once, and SFM is restarted before Apply.
- **Not repeated:** controlled Abort tests and the Fox qualification.

## 2. Automated gates (`S2T_VERDICT`)

| Gate | Requires |
|---|---|
| EVIDENCE | Identities. Every capture: the qualification build, no error, and a complete sidecar from the same process and step. Process A, then a restarted B. One session copy, shot, playhead and the Motion Editor. The copy saved once, the spare never. The library changed only by the one Tails pose. Exact restoration. The log collected, with no unverified, uncertain, failed-Abort or lockout result. |
| PREP | Three Tails sets, with the original as peer. S and D admitted with the same description and different rig names. Each has **exactly the seven header-declared JIGGLE leaves** as simulated leaves, with the same declarations. D posed and placed visibly differently. The session reopens as prepared. |
| SAVE | One structural record of S, **revision 2**, with the drafted written set. It **describes exactly the seven leaves** and saves no value or oracle for them. The admission is logged with the seven leaves. Save is read-only. Selected at SAVED, and **again after the restart**. |
| APPLY | Only drafted written channels changed (rig handles and direct bones), each with one key at the mapped tick. P7 verified. One owned entry. **The leaf channels are not authored by CPM.** |
| POSTURE | The non-leaf posture is observed independently: within 0.05 units and 0.5°. **Placement and facing are unchanged** (0.001 units and 0.01°), and direct-bone offsets are kept. |
| HISTORY | The pose holds after navigating away and back. Undo restores BASE (authored state and non-leaf skeleton) with the Redo entry; Redo restores APPLY. |
| LEAVES | For S, D and the peer: **leaf channels, scale and header declaration unchanged at every capture.** D's leaves are admitted at every Process B capture. Tip transforms are reported as information only, never gated. |
| PEER | Source and peer: authored state exactly, and the non-leaf skeleton unchanged at every capture. |

**Verdicts:**
- **AUTOMATED PASS:** every gate passed. The Owner separately assesses useful posture and the absence of severe
  deformation.
- **REFUSED:** a safe refusal, not a compatibility pass. The reasons are reported from CPM's log.
- **FAIL:** a functional gate failed.
- **INCOMPLETE:** evidence, preparation or restoration failed or is missing.

**The tests cover:**
- the expected run passing while the simulated tips move at every capture;
- a refusal reported with its exact reason;
- one or more failing variants for every gate (49 analyzer variants in all, 46 of them failing);
- a peer whose tips move, but whose body doesn't, still passing.

## 3. Preparation done, and one defect found

- **Run folder:** `E:\SFM_U0B_Scratch\f01-stage2-tails-r1`.
  - It holds `s2t.json`, with paths from Fox run 3's configuration and pins from the template.
  - **`build` passed:** `staged/` holds the qualification CPM `7d3ed720…` (line 42630 only) and both registries.
  - `check` confirms the published CPM `ccbed9d7…` is installed, with no registries.
  - The R2 fixture `259ea8a6…` was only read. Nothing else was run: no `pre`, `install` or seeding.
- **Defect caught by the kit tests:** the first wrapper used a generator expression in the function that runs
  `exec`. Python 2.7 rejects that ("unqualified exec is not allowed … nested function with free variables"), so it
  would have failed inside SFM. It now uses a plain loop, and the 2.7.5 tests pass.
- **Historical kit drift:** the closed recovery kit's own tests (`f01_stage1_recovery/tests/test_s1r.py`) now report
  59/61. Its two template checks compare its pins with the repository's *current* CPM, which Stage 2 changed from
  `7259e80a` to `001377f9`. The kit, its verdict and its evidence are unchanged and are not edited. The Fox kit's
  tests pass 49/49.

## 4. The Owner's steps (summary; `PROCEDURE.md` is authoritative)

**Process A**, one SFM process:
1. Open `S2T_SESSION.dmx`.
2. Create two Tails (`milestailsprower.mdl`) and rig both with `rig_biped_simple`.
3. Pose **Tails S** with rig handles, plus its directly animated ears, hair spikes and tails. Move and turn **Tails D**,
   and pose it differently.
4. Finish all posing, then capture PREP. Expect simulated leaves **7 | 7**.
5. Save New **Full body** `S2 Tails`.
6. Open Pose Info, then capture SAVED.
7. **File > Save**, then exit.

**Process B**, after the restart:
1. Reopen the session.
2. Select Tails D and `S2 Tails`; capture BASE.
3. Apply Pose; capture APPLY.
4. Inspect posture, placement, deformation and the peers.
5. Press Left arrow, then Right arrow; capture NAV.
6. Undo; capture UNDO.
7. Redo; capture REDO.
8. Exit without saving.

**After SFM closes:** `library Q`, `collect-logs`, `restore`, `check` and `analyze`.

## 5. Not done

- No `pre`, installation, seeding or SFM run.
- No Abort or Fox repetition, and no other rig campaign.
- No production promotion, signing, push, merge or release.
- Stage 1 and every historical verdict are unchanged.

## 6. Native GO and procedure correction (2026-11-19)

**Authority:** the Designer's "F-01 Stage 2 — Native Qualification GO": ACCEPT kit `cbe30f6`, with one procedure
correction; native execution authorized after it.

**The correction** (Process A step 4, posing):
- Tails S is posed with the stock rig handles and ordinary editable parent bones (`ear_L`, `HairSpike_M1`, `Tail2_L`
  and `Tail4_R`).
- The seven JIGGLE leaves are listed from the model header, each with its parent: `ear3_L` (`ear2_L`), `ear3_R`
  (`ear2_R`), `HairSpike_B3/M3/T3` (`HairSpike_B2/M2/T2`) and `Tail6_L/R` (`Tail5_L/R`). The Owner must not pose
  them.
- **Accuracy note:** the GO named `ear2_L` among the leaves. The header declares `ear2_L` and `ear2_R` ordinary
  (procedure type 0); they are the parents of `ear3_L` and `ear3_R`. The procedure says so, and, as the GO asks,
  still tells the Owner to leave them alone as an extra precaution.

**What changed with it:**
- The procedure is now `fccf5ecc…`, re-pinned in the template and the run configuration.
- The analyzer (`a76b7a80…`), the capture wrapper and the gates are unchanged.
- Kit tests: 79/79 (3.10.6) and 25/25 (2.7.5).

**Recorded, not altered (as the GO asks):** the two stale-template failures of the closed recovery kit
(`template.candidate_is_the_corrected_cpm` and `template.qualification_build_is_the_one_line_derivation`, 59/61).
They compare that kit's pins with the repository's current CPM. That kit and its evidence stay unchanged.

**Preflight and installation:**
- `staged/` (derived output only) was rebuilt for the new procedure pin. `build` gave `7d3ed720…`, line 42630 only.
- `pre` passed: `S2T_SESSION.dmx` is a verified copy of the R2 fixture `259ea8a6…`, the spare is in place, and the
  preset library is backed up (107 files, 22 folders).
- `install` and `check`: the qualification CPM `7d3ed720…` and both registries are installed.
- The original R2 fixture is unchanged.
