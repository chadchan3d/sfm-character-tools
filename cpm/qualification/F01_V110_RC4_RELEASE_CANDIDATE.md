# F-01 v1.1.0 release candidate 4: preparation record (unsigned, not installed, not released)

**Authority:** "F-01 Pose Library — v1.1.0 Release Candidate GO" (Owner/Designer, after the RC4 short native check
AUTOMATED PASS 55/55 and Owner PASS; documentation checkpoint `00220ce`). F-01 functionality is frozen: no feature,
numerical limit or qualification decision was changed in this preparation.

## 1. Source and candidate identities

| Item | Value |
|---|---|
| Source commit | `00220ce` (the last product change is `2eacd7e`; only documentation since) on branch `feature/f01-pose-library` |
| Production CPM | `cpm/app/SFM_Character_Preset_Manager.py` `b89af5a8e8e86e65352a34803aef84b751c42082aecb58be250149da39e02525` (1,576,306 bytes) |
| Registries | `cpm_pose_profiles_v1.json` `f445d5ef…`, `cpm_body_profiles_v1.json` `a2254930…` (unchanged since RC1) |
| Spec | `release/v1.1.0-rc4/SOFTWARE_SPEC.json` `1543769092ea3878bfb7f6464c2138cfd27f68288acd2868b0cec8c5a5be5b61` (RC3's spec with only the CPM identity and the description changed) |
| Inventory (unsigned) | `15db1c1aa9a53f59c82c5068d7b60a741f9a35b8de641080311d2ac33864f948` (v1.1.0, 33 files) |
| Package | `SFM.Character.Tools.v1.1.0-rc4-UNSIGNED.zip` `bef9171a6e06aa1e2d3d0d0628d641bf33d3238a91952d7b6b15c659ad52f8fd`, 1007 entries (1003 exact v1.0.0 bytes, 4 candidate) |
| Tool | `release/v1.1.0-rc4/rc4_tool.py` (RC1's `rc_tool.py` unchanged, with the RC4 spec and package name) |
| Rollback | the published v1.0.0 ZIP `5323b143…` (CPM `ccbed9d7…`), unchanged and available |

## 2. Production changes against published v1.0.0

The package differs from v1.0.0 in exactly four entries: the CPM replaced, the two Pose Library registries added, and
the inventory replaced. The signature is left out until the Owner signs.

Against RC3 (`5ca54072…`), only the CPM and the inventory differ.

The CPM integrates every accepted F-01 change:
- **Pose Library routes:** the v1 left arm (legacy); Krystal v2 Full body; generic v3 direct_fk with Selected parts and the QUATINTERP helper rule; the structural rig adapter for Fox (revision 1) and Tails' JIGGLE leaves (revision 2);
- **RC4 changes:**
  - same-model cross-rig adaptation;
  - Astra's bounded static-offset equivalence (structural route);
  - Astra's revised verification contract: reproduction envelope 0.01 units and 0.1°, the reproduction-mismatch outcome, and the no-work repeat Apply;
- **UI:** Save New responsiveness; the Pose Info Rig row (local `pose_rigs.json`); the accepted UI corrections;
- **Earlier changes kept:** the OT1 Body Preset ordering correction, M-05 and M-06.

## 3. Production configuration

| Check | Result |
|---|---|
| Version identity | CPM reports `software_version` from the packaged inventory only when its one cpm_app entry is this exact build; the inventory says 1.1.0 (RC VERIFY `version` PASS) |
| Registry mode | `PROD_POSE_REGISTRY_MODE = u"production"`, exactly once (the RC4S production-mode check PASS on the package's own CPM: production, generic v3, carried rule disabled, Krystal v2 and left arm qualified, only experimental mappings left out, structural adapter qualified, usable and bounded) |
| Fault injection | `prod_pose_qualification_fault` acts only when the mode is `qualification`; inert in production |
| Registries | hash-pinned in the CPM; any other file refuses |
| Scratch, test or user paths | none in the CPM (searched for scratch folders, user profiles, fixtures and the test tree) |
| Production safeguards | unchanged: P1–P7, the key planner, Undo ownership, verified Abort and recovery lockout |
| Rollback | the v1.0.0 package unchanged; RC VERIFY `rollback` PASS (v1.0.0's CPM reads no registry) |

## 4. Verification

- **Package:** `package` and `verify` give RC VERIFY PASS (package, updater, version, installer, rollback). Two independent builds give the identical ZIP `bef9171a…`.
- **Packaging fidelity:** the packaged CPM and registries equal the qualified files, byte for byte. The RC4S `build` extracted them from the ZIP and matched them to the pins and the repository.
- **Regression** (this CPM, recorded at `2eacd7e`): every CPM convergence suite unchanged against the RC4 baseline, except the intended RC4 checks:
  - cross-rig 228/228 and scoped 495/495, on Python 2.7.5 and 3.10.6;
  - the known environmental r15 working-copy item.
- **Qualification kits:** every kit test result is identical to the RC3 run, except:
  - the new RC4 kits: `test_rc4r` 19/19, `test_rc4s` 20/20, and `test_rc4x` 35/36 (its historical pin of the run's CPM);
  - `test_rc3s`, now 34/35 (its historical pin of the RC3 CPM).

  Historical kits are not edited.
- **Native evidence:**
  - RC4 short native check AUTOMATED PASS 55/55 and Owner PASS (qualification build of this CPM);
  - the RC4 run's replay under the revised contract, REPLAY PASS 24/24;
  - the RC4 run's original verdict, INCOMPLETE 129/132, unchanged.

## 5. Release blockers and open items

1. **The package README is still v1.0.0's.** The ZIP's `README.txt` is the v1.0.0 file: titled v1.0.0, with no Pose
   Library section. The package rule takes every non-candidate file from the v1.0.0 ZIP byte for byte.
   - A v1.1.0 README needs Owner-approved user-facing text and a spec change, so the README becomes a candidate file.
   - Draft release notes are in `release/v1.1.0-rc4/RELEASE_NOTES_v1.1.0.md`, outside the package.
   - **Decision needed:** this is the one remaining content blocker.
2. **Not yet run natively:** the production package itself. Every native run of this CPM used the qualification build,
   and Save New's feedback and Pose Info's Rig row haven't been confirmed natively by the Owner. Prepared:
   `real_sfm_qualification/f01_v110_rc4_smoke/` (tests 20/20; offline `build` against the package PASS).
3. **Owner-only steps:** signing the inventory, merging, pushing and Workshop publication.

## 6. Final native smoke

**Recommended.** It is short, in one SFM process with the production files exactly as users will install them:
- Fox Full body Save, Apply, Undo and Redo;
- the qualified Tails cross-rig transfer, with the repeat no-op and one Undo;
- Save New's feedback and Pose Info's Rig row, as seen by the Owner.

The RC4 qualification campaigns are not repeated. Procedure: `real_sfm_qualification/f01_v110_rc4_smoke/PROCEDURE.md`.
