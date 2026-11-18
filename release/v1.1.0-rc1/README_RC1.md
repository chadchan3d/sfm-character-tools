# SFM Character Tools v1.1.0: release candidate 1 (unsigned, not for distribution)

Prepared offline under "F-01 — Begin v1.1.0 Production Integration" (2026-11-18). Not installed, not natively
smoke-tested, not signed, not released. Record: `cpm/qualification/F01_V110_RC1_INTEGRATION.md`.

The published v1.0.0 package (`SFM.Character.Tools.v1.0.0.zip`, `5323b143…`, 1006 entries) with exactly these changes:

| Entry | Change | SHA-256 |
|---|---|---|
| `usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py` | replaced: the integrated F-01 CPM | `321835086b2cbed30395de488f6cb258f3f5b49d783be178de8ebe9e16d24c05` |
| `usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json` | added (left arm qualified) | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| `usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json` | added (Krystal v2 Full body qualified) | `a2254930489772c024a42d057b98a5a01e164be05096dd85df2d461aad73d622` |
| `usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json` | replaced: v1.1.0, 33 files, **unsigned** | `22e231d2768fcbd3fd48f286c606f59b254a004b3540d5e352cb77787cbeea6c` |
| `usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.sig` | **left out** until the Owner signs | — |

- **Spec:** `SOFTWARE_SPEC.json` (`52f9f118…`).
- **Build and verify:** copy `rc.template.json` to a new run folder as `rc.json`, fill the three paths, then
  `python -I rc_tool.py <Q>\rc.json package` and `… verify`. ZIP `SFM.Character.Tools.v1.1.0-rc1-UNSIGNED.zip`
  `5663e088ba089fa694ee99b1a65ffa651f391af710a93f883965ace3d11ff390` (1007 entries; deterministic).
- **Signing (Owner only):** `updater/release_tools/make_software_inventory.py sign --spec
  release/v1.1.0-rc1/SOFTWARE_SPEC.json --root <stage>\usermod --software-version 1.1.0 --private <key outside the
  repository> --out <new folder>`.

Remaining gates: the record's section 6.
