# F-01 v1.1.0 release candidate 1: production integration record (2026-11-18)

**Authority:** "F-01 — Begin v1.1.0 Production Integration" (Designer disposition after H1 CLOSED / PASS; commit
`3b1e644` accepted). Offline only: nothing installed, no SFM run, no signing, push, merge, tag or publication.

**Status: locally verified release candidate (unsigned).** No critical failure found. Remaining release gates and
documented limitations: sections 6 and 7.

## 1. Identity

| Item | Value |
|---|---|
| Base | `3b1e644` (CPM `3d31e721…`: H1 helper rule on the OT1-integrated candidate) |
| RC1 CPM | `321835086b2cbed30395de488f6cb258f3f5b49d783be178de8ebe9e16d24c05` (1,479,359 B; production mode) |
| Body registry | `cpm/pose_profiles/cpm_body_profiles_v1.json` `a2254930489772c024a42d057b98a5a01e164be05096dd85df2d461aad73d622` (was `22dcd159…`) |
| Pose registry (unchanged) | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| Release spec | `release/v1.1.0-rc1/SOFTWARE_SPEC.json` `52f9f118482db83d10d5a331a7497048d34137a693fdae04fe77609e876bee30` (33 files) |
| Unsigned inventory | `22e231d2768fcbd3fd48f286c606f59b254a004b3540d5e352cb77787cbeea6c` (software_version 1.1.0, key id `ed25519-5d879134807dff6d`) |
| Unsigned package (outside Git) | `E:\SFM_U0B_Scratch\f01-v110-rc1\package\SFM.Character.Tools.v1.1.0-rc1-UNSIGNED.zip` `5663e088ba089fa694ee99b1a65ffa651f391af710a93f883965ace3d11ff390` (1007 entries; rebuilt independently, byte-identical) |
| Tool / config template | `release/v1.1.0-rc1/rc_tool.py` `42b19fb5…`; `rc.template.json` `55fabeab…` |
| Readiness evidence (outside Git) | `RC_VERIFY.json` `05548c0b…`; `PACKAGE_MANIFEST.json` `86528436…` |

The historical v1.1.0 candidate (`release/v1.1.0-candidate/`, CPM `84cd996c…`, PS-2 run 1) is kept unchanged.

## 2. What is integrated

| Route or correction | Qualification | Production effect in RC1 |
|---|---|---|
| Krystal v2 Full body (stage E body route through the current Save dialog, K1) | K2 native integration check, revised A1 replay PASS 56/56, Owner accepted (`F01_K2_KRYSTAL_V2_NATIVE_RESULTS.md`); S3 runs 1–5 | **Enabled now:** the body registry mapping `krystal-v1 → krystal-v1 full_body` is `qualified` with that evidence; the CPM pins the new registry hash. Krystal Full body saves and applies as version 2 (no more `rig-driven` refusal for Krystal) |
| Generic v3 Full body / Selected parts (`direct_fk_v1` revision 1) | EF-1 PASS 128/128, SFP-1 NQ1 PASS 134/134 | Already `qualified` (since `84cd996c…`); unchanged |
| QUATINTERP helper compatibility (H1) | H1 CLOSED / PASS (`F01_H1_NATIVE_RESULTS.md`) | Already active in production behind the qualified rule (no mode gate, no character condition); unchanged |
| Body Preset ordering correction and production reference guard (OT1) | OT1 replay; OT1S SMOKE PASS (`F01_OT1S_NATIVE_RESULTS.md`) | Already in the base; unchanged |
| Accepted UI corrections (PS-2, K2, UA-1, Pose Info types) | UA-1 / UA-1S Owner acceptance | Already in the base; unchanged |

**The only product change in this step:** the body registry's one mapping (`status` `experimental` → `qualified`,
`evidence` null → the K2 citation, 251 characters within the registry's 256 limit) and the CPM's
`PROD_BODY_REGISTRY_SHA256` pin with a two-line comment. No engine, rule, tolerance, write scope, transaction, Undo,
Abort, P7, record version or UI change.

**Refusals kept:** `constant_channel_carried_v1` disabled; extrapolation unqualified; right-arm mapping experimental;
rig-driven bones on other characters, unknown rig operators, JIGGLE/physics/screen-align and every other procedural
mechanism, attachment or flex-driven helpers, unreadable headers, shared or unbounded dependencies, the Clip and
Graph Editors, recovery lockout and `committed-unverified` all refuse or report as before. An experimental body mapping
still never appears in production (tested with an `experimental` copy of the registry).

## 3. Regression (Python 2.7.5 and 3.10.6)

Every CPM convergence suite was run on RC1 and compared with the H1 baseline run on `3d31e721…`. **Identical exit
codes and failing-check sets, except the intended changes:**

| Suite | RC1 | Change |
|---|---|---|
| `test_cpm_app_f01_body` | **261/261** (both) | was 257; the experimental-only expectations now assert the qualified mapping, production v2 capture and Save, the K1 route in production despite a generic refusal; the former refusals are kept against an `experimental` registry copy (+4 checks) |
| `test_cpm_app_f01_scoped` | **487/487** (both) | was 486; production Krystal Full body takes the v2 route; the `rig-driven` no-fallback refusal kept against the `experimental` copy (+1) |
| `test_cpm_app_f01_helper` | 78/78 (both) | unchanged |
| pose core / library / integration / live | 255 / 87 / 218 / 104 (both) | unchanged |
| M-06 instance resolution / static-play flex; ordering trial | unchanged PASS | unchanged |
| clothing fit / operation context / compat projection | unchanged PASS | unchanged |
| Poses page / scoped page / empty states (2.7.5) | 123 / 17 / 15 | unchanged |

**Pre-existing, unchanged (identical at `3d31e721…`):** canonical route `derivation.added_top_level_is_bounded`
(84/85, compare 2/3); M-05 A9 (114/115); r14 `normalizer_pinned`; r15 `forbidden.unchanged.*`; adapter and gates
Normalizer pin rows; authority cleanup 42/46; bounded-logging real-log-folder guard; `logging_cleanup` and
`ui_polish_pass` need an explicit historical `--reference`; PySide suites run on 2.7.5 only.

**Kits:** EC-1, S0, model survey, NQ-03, NQ-S6, PS-2, W2 persisted pose, H1 capture, OT1S and OT1 observers pass.
EF-1, S3, H1, K2, OT1S, OT1, Q1, SFP-1 and UA-1 kit tests now fail only on the body registry identity they pin
(`22dcd159…`): their builds correctly refuse the changed tree. All nine pass at `3b1e644` (58/58, 43/43, 99/99, OK)
in an LF checkout (`core.autocrlf=false`); a CRLF checkout breaks their exact pins (pre-existing). Their evidence and
verdicts are unchanged.

**Installer and updater (code unchanged from `master`):** Workshop installer `test_disposable` and `test_autoinit` 25/25
OK against the v1.0.0 Archive A (`test_window` not run). Updater `test_production_trust` 16/19 with three historical snapshot rows (pre-existing; `updater/` is identical to
`master`); `test_menu_launcher` 17/17 PASS on SFM's Python 2.7.5, its intended interpreter (the bytes/str error first noted was a Python 3.10 run; corrected in `F01_V110_RC1_SMOKE_PREPARATION.md`).

## 4. Package

`rc_tool.py package` reuses the PS-2 packager unchanged with the RC1 spec: the published v1.0.0 ZIP's exact bytes
(`5323b143…`, 1006 entries) with the CPM replaced, the two registries added at `usermod/scripts/SFM Character
Tools/`, the inventory replaced by the unsigned v1.1.0 inventory, and the v1.0.0 signature left out (1007 entries).
The 1003 other entries are the v1.0.0 bytes (Normalizer, launcher, adapter, projection, authority package, sidecar
reader, updater, Animation Groups data, optional button, READMEs). Deterministic: an independent rebuild gives the same
ZIP hash.

## 5. Readiness verification (`rc_tool.py verify`: RC VERIFY PASS)

| Area | Result |
|---|---|
| Package | manifest, staged files and ZIP intact; against v1.0.0 exactly: changed CPM and inventory, added both registries, removed the signature |
| Updater | the shipped updater's `inventory.parse`, `check_profile` (profile 2, contract hash) and `check_files` (33 files) accept the inventory and the staged files; the inventory equals the spec |
| Versioning | the CPM's own `prod_release_version` returns `1.1.0` for this build from the staged inventory, nothing for another build |
| Installer | the Workshop installer's `core.prepare` accepts the package with v1.1.0 constants derived from it (VERSION 1.1.0, 1008 entries with the signature, 33 inventory entries, PATHS + the two registries) and a placeholder signature (presence only; deleted afterwards) |
| Rollback | the v1.0.0 Archive A is the pinned file; all 1003 kept v1.0.0 files are exact; the v1.0.0 CPM references neither registry, so leftover registries are inert after a v1.0.0 reinstall; PS-2 Process 4 showed v1.0.0 running with Poses folders present |

## 6. Remaining release gates (Owner authorization each; not failures)

1. **Native production smoke of RC1** installed from the package layout. Not yet observed natively: the
   production-mode build with the Krystal v2 mapping qualified (K2, H1 and OT1S ran qualification builds that differ
   in the registry-mode line, and K2 also in the mapping status). One short pass: Krystal Full body Save/Apply/Undo,
   Heavy Full body, an Engineer Full body, a Body Preset and Help version; then rollback. **Recommended before
   signing.**
2. **Signing** of the v1.1.0 inventory with the Owner's key (`make_software_inventory.py sign --spec
   release/v1.1.0-rc1/SOFTWARE_SPEC.json …`), then the final ZIP with the `.sig` (1008 entries) and its hash.
3. **README text for v1.1.0** (owner-approved copy; the package still carries the v1.0.0 README and optional README).
   They are outside the inventory; changing them changes only the ZIP hash.
4. **Workshop installer v1.1.0:** `workshop_installer/release.py` constants (computed in section 5; SHA-256 after
   signing), README wording ("installs the qualified original v1.0.0 archive"), rebuilt `SCT_Setup.exe`, `stage`
   and `stage.verify`.
5. **Updater distribution check** with the signed inventory (it refuses an unsigned one by design). No updater code
   change is needed.
6. Merge `feature/f01-pose-library` to `master`, tag, GitHub release, Workshop publication.

## 7. Documented limitations (not blockers)

- **Full body coverage:** Krystal (v2) and unrigged direct-FK characters (v3), including QUATINTERP-helper characters
  such as the Heavy. Rig-driven characters other than Krystal, JIGGLE (e.g. Ayane), physics and other procedural
  mechanisms refuse Full body safely; Selected parts remains where supported.
- Poses apply in the Motion Editor only.
- Selected parts Apply on Krystal up to about 5.6 s (NQ1/PS-2 performance finding).
- Helper bones follow the hierarchy and may look slightly different (stated in the Save summary).
- The Body Preset scale correction is natively qualified on the Krystal fixture (OT1S); other characters' scale
  expressions run the same code, offline-tested.
- `pose_sources.json` stores local project paths; copying a whole library folder shares them.
- Rollback is a reinstall of v1.0.0 (Setup does not restore older versions); the two registry files stay behind and
  are ignored by v1.0.0; saved poses stay in the library and are ignored by v1.0.0.
- Historical kits pin the pre-integration registry (section 3).
