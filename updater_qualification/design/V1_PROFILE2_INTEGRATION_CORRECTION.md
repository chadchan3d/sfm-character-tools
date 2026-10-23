# v1.0.0 Integration Correction: Scripts > SFM Character Tools, Bundled Data, Profile 2

**Status:** implemented and verified offline, 2026-10-23. Owner-approved correction incorporating Astra's
integration adjudication and the owner's ruling on bundled Animation Groups data. The adjudication text itself was
not supplied to this repository; this record states what was implemented.

**Amended the same day by the menu isolation correction (section 10),** which supersedes the layout, locator
identities, profile hash and unsigned inventory stated in sections 2-4.

**Not done here:** production signing, the updater rebuild, final ZIP assembly, live SFM writes, L-6 and
publication.

## 1. Release behavior

- **One ZIP:** both programs, the updater, the official Animation Groups data and the optional CPM Quick Launch.
- **One primary copy:** copying the root `usermod` installs the working software and data. There is no first-run
  download, compilation or separate data step.
- **Menu:** Scripts > **SFM Character Tools**, with the three existing entries (`SFM_Character_Preset_Manager`,
  `Rebuild_Control_Groups_Normalizer`, `SFM_Control_Group_Updater`).
- **Overwrite:** installing overwrites `usermod\cfg\sfm_defaultanimationgroups.txt`. This is owner-approved, and
  the README warns about it. Updater operations keep their protected transactions.

## 2. Layout

```text
usermod/cfg/sfm_defaultanimationgroups.txt                          Master 1d855cd3…
usermod/cfg/sfm_shared_authority/manifest.json                      6c756806…
usermod/cfg/sfm_shared_authority/sfm_master_0_37916775….sfmsidecar  37916775…
usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py      (unchanged location)
usermod/scripts/sfm/mainmenu/SFM Character Tools/                   menu entries, authority software,
                                                                    signed inventory
usermod/tools/SFM Control Group Updater/
OPTIONAL - CPM Button/usermod/...                                   (unchanged locations)
```

## 3. Changed sources (only the menu-directory literal, plus one message)

| File | Change | Identity |
|---|---|---|
| `cpm/app/SFM_Character_Preset_Manager.py` | `PROD_CPM_MAINMENU_RELATIVE_PARTS`; the private-module refusal text names "SFM Character Tools > …" | `d7a8a374…` → `b2c383bd…` |
| `cpm/convergence/cpm_authority_adapter.py` | `MAINMENU_RELATIVE_PARTS` | `e96e21b5…` → `9c3c0351…` |
| `audit_external_runtime/Rebuild_Control_Groups_Normalizer.py` | `_authority_locate_mainmenu_dir()` | `6b5d2941…` → `52e3e777…` |
| `…/sfm_master_authority_productionized/bootstrap.py` | `bootstrap_import_path()` | `acad28b6…` → `06f746cf…` |
| `cpm/quick_launch/cpm_ase_quick_launch.py` (optional, not inventoried) | `LAUNCHER_RELATIVE_PARTS` | `4558d296…` → `7a01bd5e…` |

**Unchanged:**
- the R15 launcher `996ca483…` and the updater launcher `99f27260…` (their header comments still name the earlier
  folder, with no functional effect);
- the Quick Launch bootstrap `23e3a881…` (it hashes whatever controller it loads, and pins none);
- every other inventoried file;
- private module names, loader markers, broker identities, `scripts/ChadChan3D_CPM/`,
  `scripts/sfm/autoinit/ChadChan3D/`, attribution and historical records.

## 4. Profile 2 and the inventory

- **`sct-authority-profile-2`:** contract `e0a9b64e0d947314f4382e417865fdeba72b0607366babcb89f86e6935cb33e4`.
  It is profile 1 (`2bbd93d0…`, unchanged) with `installation_layout` changed:
  - `contract` is `sct-layout-2`;
  - a new field, `software_dir`, is `scripts/sfm/mainmenu/SFM Character Tools`;
  - `software_inventory` is `…/SFM Character Tools/sfm_character_tools_inventory.json`.

  The semantic, compiler, provider, runtime, consumer, admission, publication and deployment contracts are equal.
- **Updater:** it implements profile 2 only. `official.AUTHORITY_PROFILE` and `SUPPORTED_PROFILES` are profile 2.
  The earlier production-signed profile-1 inventory is refused (`SOFTWARE_UNSUPPORTED`); verification is not
  weakened. `runtime_check` and `build.py` read the current profile.
- **Inventory spec** `updater/release_tools/character_tools_software_v1.json`:
  - 31 files across nine roles, profile 2;
  - 30 paths under the new menu folder; the CPM app stays in `scripts/ChadChan3D_CPM/`;
  - only the four changed identities above were updated;
  - the launcher and the optional button stay outside it.
- **Unsigned production inventory** (superseded by section 10: `2e3a8036…`; the exact bytes the owner would have signed: software version 1.0.0, key id
  `ed25519-5d879134807dff6d`): `08c9e78e753c84260ce6124611f76b0cb7a2e6df693d69d4e13fad5fca696f2f` (7,246 B).
  `make_software_inventory.py sign` regenerates these bytes from the staged files.

## 5. Overlay onto an earlier installation (finding, documented remedy)

Windows folder merging replaces same-named files and keeps the rest. Over an installation that already had
Character Tools data, the merge:
- replaces the Master and `manifest.json`;
- adds the new sidecar;
- **keeps the earlier sidecar**.

Measured in scratch:
- **CPM and the Normalizer** still acquire the new generation. Consumers take the first sidecar whose embedded
  source hash matches the Master, and skip others with a diagnostic.
- **The updater status** reports "expected exactly one active sidecar, found 2". Its GUI says "Character Tools data
  doesn't match the animation-group TXT in SFM. Choose Update Using SFM's TXT to fix this."
- **Update Using SFM's TXT** (SFM closed) completes a protected transaction. It retires every earlier sidecar and
  manifest into the transaction's recovery storage (nothing is deleted) and leaves exactly one sidecar. Status is
  then consistent.

A fresh installation needs nothing further. No silent cleanup was added. Only installations that had pre-release
Character Tools data are affected. The README documents the one updater action.

## 6. Earlier installations (`mainmenu\ChadChan3D`)

- **The problem:** the earlier suite files stay active after the merge, giving duplicate menu entries. Within one
  SFM session, whichever package copy loads first wins. The other copy refuses, by its origin and locator checks:
  - a legacy package loaded first makes the new Normalizer and CPM refuse;
  - a new package loaded first makes a legacy CPM adapter refuse.

  It never mixes the two copies.
- **The documented manual retirement:** with SFM closed, delete only these items from `mainmenu\ChadChan3D\`:
  - `SFM_Character_Preset_Manager.py` and `Rebuild_Control_Groups_Normalizer.py`;
  - `SFM_Control_Group_Updater.py`, if present;
  - `cpm_authority_adapter.py` / `.pyc` and `cpm_compat_v1_projection.py` / `.pyc`;
  - `sfm_character_tools_inventory.json` / `.sig`;
  - the folders `sfm_master_authority_productionized\` and `sfm_master_sidecar\`.

  Every other file in that folder is preserved. The updater's history, backups and recovery storage are untouched.

## 7. Official data release (requirements; not signed)

The signed `data-v1.0.0`, sequence 1 (`58752b33…`), names profile 1. It is historical and is never published.

The release for profile 2 keeps the three payload identities above and is built by the owner with the existing
`make_official_package.py build`:
- `--sequence 2`;
- `--data-version 1.0.0`, `--release-tag data-v1.0.0`;
- profile defaulting to `sct-authority-profile-2`;
- `--source-commit` the pushed commit of this correction;
- `--published-at` the issue time;
- the production key `ed25519-5d879134807dff6d`.

Sequence 1 was never published. Its only high-water records exist in scratch acceptance runs.

## 8. Focused verification (offline, scratch)

- **`tests/integration/profile2/run_profile2_checks.py`** (Python 3.10 + test key) with `py27_probe.py` (SFM
  Python 2.7.5): **24/24 PASS**. It covers:
  - the profile and spec consistency;
  - the locators: CPM, the adapter, the Normalizer and the bootstrap agree on a path with spaces; the Quick Launch
    launcher path is correct;
  - CPM and the Normalizer share one broker on the installed generation (fresh and overlay);
  - the profile-1 refusal;
  - the fresh bundled-data status and the verified NOOP;
  - the overlay finding and its remedy;
  - both mixed-location refusals;
  - the documented migration, which leaves unrelated files and exactly one of each entry.
- **Quick Launch run suite (SFM Python 2.7.5 + PySide):** 232/233. **Static:** 31/32. The only failure in both is
  the QL-1 guard "CPM app unchanged from HEAD", which this correction trips intentionally; it is rerun after
  commit.
- **CPM canonical-route suite:** 84/85, with identical Python 3 and 2.7 digests. The new menu folder passes the
  import and origin checks. The one failure, `derivation.added_top_level_is_bounded`, is earlier-milestone drift
  (R15 and empty-state names).

## 9. Validity of accepted evidence

Retained, with the responsible implementation unchanged apart from a path literal:
- K and L-1 to L-5 updater behavior;
- PRE, governor and resource stop;
- sidecar format and semantics, compiler and validator/provider;
- the CPM UI and empty-state behavior;
- QL-2 docking and appearance;
- data identities.

Superseded, and to be reproduced at the next build or signing:
- the updater build `34aa4d0d…` (`official.py` changed: it must be rebuilt);
- the signed inventory `9672e00e…` (profile 1);
- `data-v1.0.0` sequence 1;
- the single ZIP `5aa968b7…`.

The menu-folder locators and the Quick Launch launcher path have new offline evidence (section 8). A real-SFM
check of the new menu folder belongs to L-6.

## 10. Menu isolation correction (2026-10-23, before any signing; supersedes the layout in sections 2-4)

**Why:** the accepted Menu Visibility Check (a read-only analysis of SFM's native Scripts-menu discovery in
`ifm.dll`) established that SFM lists every `.py` file under `scripts\sfm\mainmenu` as a menu item. It searches
every subfolder and has no name filter. Each folder containing a `.py` becomes a submenu, and `.pyc` and other
files are not listed. With the layout in section 2, Scripts > SFM Character Tools would also have shown:
- the CPM adapter and projection;
- a 23-item "sfm master authority productionized" submenu;
- a 3-item "sfm master sidecar" submenu.

**Layout (profile 2 amended; never signed or published):**

```text
usermod/scripts/sfm/mainmenu/SFM Character Tools/   SFM_Character_Preset_Manager.py, Rebuild_Control_Groups_Normalizer.py,
                                                    SFM_Control_Group_Updater.py, sfm_character_tools_inventory.json/.sig
usermod/scripts/SFM Character Tools/                cpm_authority_adapter.py, cpm_compat_v1_projection.py,
                                                    sfm_master_authority_productionized/, sfm_master_sidecar/
usermod/scripts/ChadChan3D_CPM/, autoinit/ChadChan3D/, cfg/, tools/        (unchanged)
```

**Changed sources:** only the library-directory literal in the four established locators, with the comments that
describe it. Private module, package and ownership names are unchanged.

| File | Change | Identity |
|---|---|---|
| `cpm/app/SFM_Character_Preset_Manager.py` | `PROD_CPM_MAINMENU_RELATIVE_PARTS` = `usermod/scripts/SFM Character Tools` | `b2c383bd…` → `230f801d…` (793,310 B) |
| `cpm/convergence/cpm_authority_adapter.py` | `MAINMENU_RELATIVE_PARTS` | `9c3c0351…` → `14a1ebc6…` |
| `audit_external_runtime/Rebuild_Control_Groups_Normalizer.py` | `_authority_locate_mainmenu_dir()` | `52e3e777…` → `a484eee1…` |
| `…/sfm_master_authority_productionized/bootstrap.py` | `bootstrap_import_path()` | `06f746cf…` → `8e99bcd3…` |

**Unchanged:**
- the three menu launchers;
- the Quick Launch controller `7a01bd5e…`, which still opens the CPM menu launcher in the menu folder;
- the Quick Launch bootstrap;
- the origin checks, the single broker, CPM window reuse, Normalizer transactions and resource safeguards.

The functions keep their historical `*_mainmenu_dir` names, and their value is now the library directory.

**Profile 2:**
- `installation_layout` now has `menu_dir` (`scripts/sfm/mainmenu/SFM Character Tools`) and `library_dir`
  (`scripts/SFM Character Tools`), replacing `software_dir`.
- `software_inventory` stays in the menu folder. The contract stays `sct-layout-2`.
- New contract hash: `d767c3d5b69d568ef53a5429ad59bf5f8d4f716cfaed0450789366fdfd48d743`, replacing `e0a9b64e…`.
  Every other contract equals profile 1's (`2bbd93d0…`, unchanged).

**Inventory:**
- Spec `dfe28855…` (11,652 B): 31 files, nine roles. 28 files are in the library folder; the CPM launcher and the
  Normalizer are in the menu folder; the CPM app is in `ChadChan3D_CPM`. The four identities above changed.
- **Unsigned production inventory:** `2e3a8036c58ab8a98044a6c2b159debaab2942d38b072e802a929d860c5b0e8b` (6,882 B),
  in `release/v1.0.0/profile2/`. It replaces `08c9e78e…`, which is no longer current.

**Updater:**
- `official.py` `4c84e608…` and `compat/profile.py` `0dbd8383…` changed in comments and the profile only.
- `updater/SHA256SUMS.txt` is refreshed.
- `run_l1.py` puts its stale-bytecode case beside the adapter in the library folder.

**Focused verification (offline, scratch `profile2-menu-isolation-20261023\run1`):**
- **`tests/integration/profile2`: 27/27 PASS**, first run. New checks:
  - the installed `scripts\sfm\mainmenu` tree holds exactly three `.py` files, all directly in SFM Character
    Tools (SFM's recursive discovery rule);
  - the internal library is outside it;
  - the locators all resolve the library folder on a path with spaces;
  - Quick Launch still targets the menu launcher;
  - **wrong origin:** a library copy left in the menu folder and loaded first makes the Normalizer
    (`BrokerIdentityConflict`) and CPM (`origin-mismatch`) refuse.

  Repeated: the shared broker and generation (fresh and overlay), the profile-1 refusal, the overlay finding and
  remedy, both legacy mixed-location refusals, and the documented migration.
- **`test_production_trust.py`:** 18/18.
- **CPM canonical route:** 84/85, with identical Python 3 and 2.7 digests. The failure is the historical
  `derivation.added_top_level_is_bounded`; this correction adds no top-level names.
- **Quick Launch, before commit:** 232/233 (run) and 31/32 (static). The only failure is the intentional "CPM app
  unchanged from HEAD" guard; both are rerun after commit.

**Unchanged by this correction:**
- the overlay finding (section 5);
- the legacy `ChadChan3D` retirement list (section 6);
- the sequence-2 data requirements (section 7; the package names the profile ID, and the owner builds it from this
  correction's commit);
- the bundled data, the overwrite policy, updater transactions and the optional-button locations.

**Still to do:** the real-SFM check that the menu shows exactly three commands belongs to L-6.
