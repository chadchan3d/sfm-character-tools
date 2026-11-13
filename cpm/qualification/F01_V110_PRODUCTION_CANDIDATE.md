# F-01 v1.1.0 production candidate: offline preparation record (2026-11-12)

**Authorization:** "F-01 — Authorize Offline v1.1.0 Production Candidate Preparation" (Owner, 2026-11-12), after the
accepted readiness assessment (CONDITIONAL). Offline only: nothing installed, no SFM run, no signing, merge, tag,
Workshop or updater distribution.

**Status:** candidate prepared and tested offline; native PS-2 prepared, **not run**.

## 1. Candidate identity

| Item | Value |
|---|---|
| Accepted source | `e1b7e21` (CPM `bb70cce26a65b069b5e44cf3e89bfe01ae06acfe5dee99a577632d997ed8211d`) |
| Candidate CPM | `84cd996c914f82bcc41414413958a5a9b536fca088081d862559f48a69144568` (1,441,689 B; production mode) |
| Pose registry (unchanged) | `cpm/pose_profiles/cpm_pose_profiles_v1.json` `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| Body registry (unchanged) | `cpm/pose_profiles/cpm_body_profiles_v1.json` `22dcd1599c0556bcb71df0a9b9d14657684173b3bbf557250710a8104a6baa26` |
| Release spec | `release/v1.1.0-candidate/SOFTWARE_SPEC.json` `3909f6a65b96cfbe5c2610898a2582ce27237772dcd9c38a8d54a0295afcc249` (33 files) |
| Candidate inventory (unsigned) | `036786e1ab619bb6231c59785575585ff493194cd50deb4bf971f26b92b24ffa` (software_version 1.1.0) |
| Candidate package (outside Git) | `E:\SFM_U0B_Scratch\f01-v110-candidate-package\package\SFM.Character.Tools.v1.1.0-candidate-UNSIGNED.zip` `44184585111f861b16d8f58bb7f3f1e3f163c2343c85083b71412f2f80922b69` (1007 entries; deterministic) |

**CPM changes against the accepted source (the only ones):**
- `PROD_SCOPE_RULES = {u"direct_fk_v1": {u"revision": 1, u"status": u"qualified"}}` (was `experimental`);
- the comments above it cite the native evidence (EF-1 run 2 PASS 128/128 on `3da2b653…`, SFP-1 NQ1 PASS 134/134 on
  `2d791dec…`) and the Owner's generic-availability decision.

Nothing else: no pose semantics, placement rule, tolerance, write scope, Undo/Redo, Abort, P7, record version or
registry change. **Kept disabled:** `constant_channel_carried_v1` (`PROD_SCOPE_CARRIED_ENABLED = [False]`,
`PROD_SCOPE_EXTRAPOLATION_QUALIFIED = [False]`), the right-arm mapping (experimental), the Krystal v2 Full body
mapping (experimental, section 2). **Inert in production:** `PROD_POSE_QUAL_FAULT` (acts only when the build mode is
`qualification`; now tested: armed during a production Apply, which commits normally).

**Generic model policy (Owner-approved):** generic v3 availability under the existing fail-closed structural and
transaction safeguards; no allowlist; no fallback. Rig-driven, procedural (control-less), unsupported dependency and
writer configurations keep refusing before any write.

**What production behaviour changes:** a character without a registry profile is now supported on the Poses page
through generic scoped poses (its empty list reads "No saved poses for <character>." instead of "Poses aren't available
for this character yet."); Save New opens the scoped Save dialog; Full body or Selected parts are offered or refused by
the engine (the unrigged Heavy: Full body refused `carried-unsupported`; Krystal, which has no production v2 route:
Full body refused `rig-driven`, Selected parts available).

## 2. Krystal v2 Full body: evidence-gated disposition — RETAIN EXPERIMENTAL

| Condition | Finding |
|---|---|
| A formal accepted native PASS | **Not established.** `F01_FULL_BODY_S3_ASSESSMENT.md` (2026-11-07) records every S3 requirement as established across runs 1–5 but says "Production qualification is not declared by this document"; run 3's comparator verdict is **FAIL** (procedural) and its full-body Apply results (B2–B8) rest on interim checks applied to its valid observations, not a comparator PASS; runs 4 and 5 PASS cover B9–B17 only. The Ledger records "COMPLETE" and "CLOSED (qualified, local development status)"; no Owner acceptance of S3 as a formal native PASS is recorded. |
| The production mapping matches the qualified mapping | **Yes, for the data.** The body registry is `22dcd159…` throughout S3 and now; the mapping's content is unchanged (status `experimental`). |
| No unresolved safety condition | **No defect is open**, but the v2 route is now reached through code S3 never exercised natively: since the S3 build `f6098b3a…` (`e98b90b`), `ProdWindow.save_pose` routes Krystal's Full body through the SFP-1 Save dialog (`prompt_pose_scope` with the v2 body route), and `apply_pose`, `update_pose`, `prod_pose_parse`, `prod_pose_validate` and `prod_pose_deferred_verify` gained version 3 dispatch. The 53 `prod_body_*` functions are unchanged. |

**Disposition:** the mapping stays `experimental`; the body registry and its CPM pin are unchanged. **Exact blockers to
promotion:** (1) the Owner's formal acceptance of the S3 evidence as a native PASS for the v2 Full body mapping, given
run 3's procedural FAIL; (2) native coverage of Save New and Apply of a v2 Full body through the current Save dialog
and dispatch on the production build (one focused smoke after promotion). No S3 testing was done under this
assignment. **Production effect:** Krystal Full body refuses `rig-driven` (Selected parts available; the version 1 left
arm remains qualified); tested offline (`N.production_krystal_full_body_has_no_v2_route_and_refuses_without_fallback`).

## 3. File and dependency manifest

**Package** (`PACKAGE_MANIFEST.json` lists every entry with its SHA-256, size and origin):
- 1003 entries are the published v1.0.0 ZIP's exact bytes (`5323b143…`): the 30 unchanged inventoried software files
  (Normalizer `a484eee1…`, CPM launcher `996ca483…`, adapter `14a1ebc6…`, projection `9b077a1b…`, the authority
  package, the sidecar reader), the updater executable and its runtime, the bundled Animation Groups data (Master,
  sidecar, manifest), the optional CPM button and the READMEs;
- 4 candidate entries: the CPM, the two registries (`usermod/scripts/SFM Character Tools/`, where
  `prod_pose_registry_path()` reads them), and the unsigned v1.1.0 inventory;
- 1 removed: the v1.0.0 inventory signature (re-added by the Owner's signing).

**Installed paths** (profile `sct-authority-profile-2`, layout `sct-layout-2`): CPM
`usermod/scripts/ChadChan3D_CPM/`; library `usermod/scripts/SFM Character Tools/` (registries beside the adapter);
menu `usermod/scripts/sfm/mainmenu/SFM Character Tools/` (launcher, Normalizer, updater launcher, inventory).

**Offline acceptance by the shipped tooling:** the updater's own `inventory.parse`, `check_profile` (profile and
contract hash) and `check_files` (all 33 entries) accept the candidate inventory and the staged files; the signing
tool's precondition (every spec file is its qualified identity in the staged root) passes. The Workshop installer's
`release.py` pins v1.0.0 and refuses the candidate by design (section 7).

**Runtime dependencies unchanged:** SFM's Python 2.7.5 and PySide; the shared authority package and sidecar reader;
the CPM launcher. The registries are read at run time and hash-checked against the CPM's pins; a missing pose registry
disables the Pose Library with "Pose Library files are missing or damaged. Reinstall Character Preset Manager."; a
missing body registry disables only v2 Full body.

## 4. Offline tests

Every CPM suite was run on the candidate and, in place, on the accepted source `e1b7e21` (the candidate's tracked
changes stashed for the baseline run, then restored), under SFM's Python 2.7.5 and 3.10.6. **Every suite's exit code
and failing-check set is identical between the two, except the intended changes below.**

| Suite | Candidate | Note |
|---|---|---|
| `test_cpm_app_f01_scoped` | **475/475** (2.7.5 and 3.10.6) | was 473; new production checks: rule qualified and switches, production authorization admits the rule, unsupported Full body refused in the dialog without writing (Heavy, `carried-unsupported`), the qualification fault hook inert in a production Apply, Krystal Full body without a v2 route refused `rig-driven` with no fallback; availability `available` in production, `not-qualified` for revision 2 |
| `test_cpm_app_f01_pose_page` | **120/120** (2.7.5) | was 119; N5 now checks the generic production list message and, separately, the unsupported-character message when no rule is usable |
| `test_cpm_app_f01_scoped_page` | 14/14 (2.7.5) | unchanged |
| `test_cpm_app_f01_body` | 246/246 (both) | unchanged |
| pose core / library / integration / live | 255/255, 87/87, 204/204, 104/104 (both) | unchanged |
| M-06 instance resolution / static-play flex | 179/179, 334/334 (both) | unchanged |
| clothing fit / operation context / compat projection (publish, suite, compare) | 95/95, 108/108, 196/196; compare 3/3 | unchanged |
| empty states | 15/15 (2.7.5) | unchanged |

**Known pre-existing failures (identical at `e1b7e21`; not caused by the candidate):** canonical route
`derivation.added_top_level_is_bounded` (84/85; compare 2/3); authority adapter and convergence gates Normalizer pin
rows (`oracle.normalizer_range_pinned`, `oracle.normalizer_sha256_pinned`, gates `section.c10.completed`, adapter
`suite.fixture_present`); authority cleanup 42/46; M-05 114/115; r14 17/18 and 14/15; r15 340/345 and 183/188
(`forbidden.unchanged.*` rows); bounded logging 71/72 (the real-log-folder guard: the folder exists after native use).
Suites that need PySide (page suites, empty states) run on 2.7.5 only; `logging_cleanup` and `ui_polish_pass` refuse
without an explicit historical `--reference` build and were not run (as before).

**Kit suites:** EF-1 34/34, S3 37/37, EC-1 14/14, S0 23/23, model survey 10/10, NQ-03 9/9, NQ-S6 7/7, W2 persisted
pose 162/162, **SFP-1 19/19 (was failing)**, **PS-2 12/12 (new; 3/3 state-capture tests on 2.7.5)**; pre-existing:
M-06 W2 and W1 harness (section 8).

## 5. PS-2 native procedure (prepared)

Kit `real_sfm_qualification/f01_ps2_v110/` (`PROCEDURE.md`, `ps2.template.json`, `tools/ps2_tool.py`,
`tools/ps2_compare.py`, `observer/F01_PS2_State.py`, `tests/test_ps2.py`). Four SFM processes, the candidate
installed from the package layout (unsigned inventory, no signature):
1. Engineer: Save New Full body (dialog wording), Help version, Pose Info wording.
2. Restart; Engineer Apply on the destination, Undo/Redo by named entries; Soldier (unqualified, header-clean) Save
   and Apply with Undo; Heavy Full body refusal (`carried-unsupported`).
3. Krystal: Full body refusal (`rig-driven`, no v2 route), Selected parts Save/Apply/Undo/Redo, the version 1 left
   arm, a Body preset (M-05 scale, M-06 static flex) and an Expression, Help version.
4. After `rollback`: v1.0.0 runs and applies a Body preset and an Expression with the run's Poses folders present.

Evidence: read-only state captures (CPM identity, mode, rules, registries, release version, the selected pose and its
Pose Info rows, Undo/Redo names), the CPM logs, the saved records, the Owner's transcribed observations. EF-1 and NQ1
transaction evidence (Abort, no-op, Clip Editor refusal, key preservation) is reused, not repeated.

## 6. Rollback and stop conditions

`rollback` restores v1.0.0 file by file (CPM, inventory and signature from the pre-run backup; registries removed;
housekeeping and `.pyc` restored), verifies every v1.0.0 software file against the published ZIP and the scripts,
cfg and sessions inventories against their baselines, and leaves the preset library (with the run's Poses folders)
untouched. After the native v1.0.0 check, `cleanup` keeps the run's library changes as evidence, puts the library back
exactly as backed up, and requires all four inventories to equal their baselines. Stop conditions: `PROCEDURE.md`
("STOP conditions", "Rollback stop conditions"); a stopped run is restored and reported STOPPED, never PASS.

## 7. Remaining release blockers

1. Native PS-2 execution and verdict (separate Owner authorization).
2. Owner signature of the v1.1.0 inventory (`make_software_inventory.py sign`), producing the final ZIP and its hash.
3. v1.1.0 README and optional README text (the candidate still carries the v1.0.0 copy).
4. Workshop installer v1.1.0: new `release.py` constants (version, archive SHA-256, 1008 entries with the signature,
   33 inventory entries, the two registry paths) and a rebuilt installer, after signing; its own qualification.
5. Updater distribution check with the signed inventory.
6. Merge `feature/f01-pose-library` to `master`, tag, GitHub release and Workshop publication (separate decisions).
7. Not blocking (documented): Krystal v2 Full body stays unavailable in production (section 2); the NQ1 Selected parts
   performance finding (3.3–5.3 s); Heavy Full body (QUATINTERP helpers) and the carried-channel rule.

## 8. Historical test reproducibility

- **SFP-1 NQ1 kit (corrected):** `test_sfp1_nq.py` reads its qualified candidate as the raw Git blob from kit commit
  `7f62c62` (`2d791dec…`); `sfp1_tool build` derives the pinned `b58ae9ba…` from it in one line (42146), exactly as
  pinned; no hash changed, no identity check weakened. 19/19 (3.10.6), 8/8 (2.7.5).
- **M-06 W2 instruments (pre-existing; not repaired):** `test_m06w2.py` reads HEAD's CPM unless `M06W2_W1_APP` names
  another file, and its tools pin the accepted W1 candidate `fd853661…` (= `master`'s and `efe8984`'s CPM). On this
  branch the CPM differs, so 67 failures and 11 errors, identical at `b2167c1` and now. Pointing `M06W2_W1_APP` at
  `git cat-file blob efe8984:cpm/app/SFM_Character_Preset_Manager.py` (`fd853661…`) reproduces the M-06 result:
  127 tests OK, 1 skipped (verified 2026-11-12). No change needed to qualify the candidate.
- **F-01 W1 arm-transfer harness (pre-existing; not repaired):** 76 errors because `accepted/harness/config.json`
  (written by `accepted/tools/prepare_run.py` for a run) is absent from the repository; unrelated to the CPM.
