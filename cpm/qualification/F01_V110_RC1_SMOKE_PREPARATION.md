# F-01 v1.1.0 RC1: native release smoke preparation (2026-11-18)

**Authority:** "F-01 v1.1.0 RC1 — Native Release Smoke Preparation" (Designer: RC1 accepted for native production
verification; commit `902df07`, CPM `32183508…`, unsigned package `5663e088…`). Offline only: nothing installed, no
SFM run, no signing, push, merge, tag or publication.

**Status: native-ready.** The kit is built and verified offline; the run waits for the Owner's authorization to
install. No product file changed.

## 1. The kit (`real_sfm_qualification/f01_v110_rc1_smoke/`)

| File | Role |
|---|---|
| `PROCEDURE.md` | the operator procedure: two SFM processes, 15 steps |
| `rc1s.template.json` | paths and pins (RC1 ZIP, CPM, both registries, fixtures, seeded records, Body preset, kit files) |
| `tools/rc1s_tool.py` | build, pre, status, install, seed, check, library, collect-logs, restore, analyze |
| `tools/rc1s_modes.py` | the offline production-mode equivalence check (section 2) |
| `tools/rc1s_analyze.py` | the automated verdict from the CPM's own logs, the saved records and the restoration |
| `owner_smoke_record.template.md` | the Owner's record (D1, B1, K1, H1–H3, D2, K2, K3, S1) |
| `tests/test_rc1s.py` | 26/26 offline (mode check on the real RC1 CPM and registries; analyzer gates on synthetic evidence; pins) |

**Exact production files.** Unlike every earlier F-01 kit, nothing is derived: `build` extracts the CPM and both
registries from the pinned unsigned RC1 package, requires each to equal its pin and the repository file, and stages
them unmodified (`32183508…`, `f445d5ef…`, `a2254930…`). No observer or capture script runs in SFM.

**Reused unchanged:** K2's pre (verified copies of the R2 fixture and of S3's prepared destination), the S3 tool's
install, collect-logs and restore (four protected inventories, published-CPM, `.pyc` and housekeeping backups, the
installation journal), UA-1's library backup, seed (K2 Pose, NQ1 Pose A) and exact library cleanup. Existing
disposable fixtures only; no new campaign.

**What the Owner does (shortest form):**
- Process A, on `RC1_SOURCE.dmx` (shot15):
  - Pose Info on both seeded poses;
  - Body Preset Apply, then Undo;
  - Save New → Full body `RC1 Krystal`;
  - two new Heavies: pose A, Save New → Full body `RC1 Heavy`, Apply to B, Undo, Redo;
  - exit without saving.
- Process B, on `RC1_DESTINATION.dmx` (shot13):
  - Pose Info on `RC1 Krystal`;
  - Apply `RC1 Krystal`, Undo, Redo;
  - Apply `NQ1 Pose A` (Selected parts), Undo if it applied;
  - exit without saving.

**Offline preparation done:** run folder `E:\SFM_U0B_Scratch\f01-v110-rc1-smoke-r1` (outside Git): `rc1s.json`
filled; `build` **BUILT** (production-mode equivalence PASS; `staged/IDENTITIES.json` `8db1aa38…`); `check`:
`published` (CPM `ccbed9d7…`, no registries). Every fixture pin was verified on disk (R2 fixture, S3 destination,
K2 Pose `bf8fc5bc…`, NQ1 Pose A `4916a724…`, Body preset `cd31c7f1…`, RC1 ZIP `5663e088…`); the library holds no
Poses folder. `pre` is left for immediately before the run, so its inventories are a fresh baseline.

## 2. Production mode: no former restriction, no unsupported route

The build mode changes exactly three things in the CPM:
- which registry mappings are selected (`prod_pose_registry_select`);
- whether an engine rule is usable (`prod_scope_rule_usable`);
- the qualification-only fault injector.

`rc1s_modes.py` runs the RC1 CPM's own functions (ast-extracted) on the RC1 registries:

| Check | Result |
|---|---|
| RC1 registry mode | `production` |
| Generic v3 (`direct_fk_v1` revision 1) | `qualified`; usable in production exactly as in the qualification build. The former generic-v3 restriction (experimental, qualification only) is gone |
| `constant_channel_carried_v1` | disabled (`PROD_SCOPE_CARRIED_ENABLED = [False]`); unusable in **both** modes, so no tested model can need it in production more than it did in the H1, EF-1 or SFP-1 qualification runs. A v3 record names `carried_rule: null`; the analyzer requires it for `RC1 Heavy` |
| Krystal Full body | production selects the same `full_body krystal-v1` mapping as qualification, as `qualified` |
| Left arm (Selected parts, version 1) | selected in production (`qualified`) |
| Left out of production | only the `experimental` right-arm mapping (not used by the smoke) |

Teeth (tests): a qualification derivation, an experimental Full body registry, an experimental generic rule or an
enabled carried rule each fail the check.

## 3. Verdict rules

`rc1s_analyze.py` gives **AUTOMATED SMOKE PASS** only when every gate passes:
- **EVIDENCE:** the RC1 build, two CPM logs written by `32183508…`, restoration and the expected library changes;
- **BODY:** Apply Body Preset committed-verified on Krystal;
- **KRYSTAL:** a version 2 `full_body` record saved in Process A and applied committed-verified in Process B;
- **HEAVY:** a version 3 `direct_fk_v1` record with no carried rule, applied committed-verified to a different Heavy;
- **SELECTED:** NQ1 Pose A applied, or a no-op;
- **DISPLAY:** three Pose Info openings;
- **CLEAN:** no refusal, failure or recovery outcome.

It gives **SMOKE FAIL** when the evidence is complete but a functional gate fails, and **INCOMPLETE** otherwise.
Undo, Redo and the look of each pose are recorded in the Owner's record. Acceptance needs both, reported side by
side. Minor helper-bone differences are not failures; useful poses and intact authored data are.

## 4. Updater-test failures: release-safety classification

| Test | Result | Classification |
|---|---|---|
| `updater/tests/test_menu_launcher.py` | **17/17 PASS** on SFM's Python 2.7.5 (its intended interpreter: it imports PySide 1 and compares the launcher as `str`) | Not a failure. The earlier "bytes/str error" was the test run under Python 3.10; the RC1 record's note is corrected |
| `test_production_trust` row "no other updater code changed" | FAIL (historical) | Compares against the pre-v1.0.0 profile-2 base snapshot. RC1 ships the v1.0.0 updater bytes unchanged (`rc_tool verify`: every one of the 1003 kept v1.0.0 files is exact). **Not release-relevant** |
| `test_production_trust` row "inventory spec is 769a8577, 31 sources" | FAIL (expected) | Pins the v1.0.0 spec; v1.1.0 has its own 33-file spec `52f9f118…`, already accepted by the shipped updater's `inventory.parse`, `check_profile` and `check_files` (RC VERIFY). **Not release-relevant** |
| `test_production_trust` row "SHA256SUMS.txt matches every listed file" | FAIL (stale manifest) | `process_gate.py` gained an opt-in `no_window` argument for the Workshop installer (`01f37ca`, after v1.0.0; default behaviour unchanged). The shipped updater is the frozen v1.0.0 executable, and `SHA256SUMS.txt` is a repository manifest that is not in the package. **Not release-relevant.** An optional docs-only refresh is left for a separate authorization; no updater code is changed |
| `test_production_trust` other 16 rows | PASS | These include the **safety rows**: production trust is exactly the approved key; unknown or impersonating signers, modified or truncated signatures are refused; the test seam is unset in shipping code |

**Release safety still rests on the gates below:** the signed inventory through the real updater, and the Workshop
installer staging the signed package. Neither can run before signing.

## 5. After a successful smoke (prepared sequence; each step needs the Owner's authorization)

1. **README v1.1.0:**
   - text for the package README and the optional README: what is new (Poses, Full body for Krystal and unrigged
     characters, Selected parts) and the limitations in `F01_V110_RC1_INTEGRATION.md` section 7;
   - this changes only the ZIP hash, because the READMEs are outside the inventory;
   - rebuild with `rc_tool.py package` in a new run folder and `verify`.
2. **Signing (Owner only; the private key never enters the repository or this session):**
   - `make_software_inventory.py sign --spec release/v1.1.0-rc1/SOFTWARE_SPEC.json --root <stage>\usermod
     --software-version 1.1.0 --private <key> --out <new folder>`;
   - add the `.sig` (1008 entries) and record the final ZIP SHA-256.
3. **Updater path (signed package):** the shipped updater's official verification of the signed inventory and
   signature under the production key, its file check against the extracted package, and CPM Help showing 1.1.0. These
   run on a disposable installation. The updater must refuse a modified signature.
4. **Workshop installer:**
   - set `release.py` (VERSION 1.1.0, 1008 entries, 33 inventory entries, PATHS plus the two registries, the final
     SHA-256);
   - update the README wording;
   - rebuild `SCT_Setup.exe`, then run `stage` and `stage.verify` against the signed ZIP;
   - run `test_disposable` and `test_autoinit` against it.
5. **Rollback:** reinstall v1.0.0 Archive A (`5323b143…`), as verified offline; the registries left behind are inert.
6. **Publication:** merge `feature/f01-pose-library` to `master`, tag `v1.1.0`, GitHub release, Workshop upload.
