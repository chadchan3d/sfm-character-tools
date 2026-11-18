# SFM Character Tools v1.1.0: release candidate 2 (unsigned, not for distribution)

RC1 (`release/v1.1.0-rc1/`, native smoke PASS) with the Owner's three final UI corrections. Record:
`cpm/qualification/F01_V110_RC2_UI_CORRECTIONS.md`.

| Entry | Change against v1.0.0 | SHA-256 |
|---|---|---|
| `usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py` | replaced: the F-01 CPM with the RC1 UI corrections | `7aa0fc4e159756f288a26819d9f8400f6f665bd797e5aff1c03ffac3a87eba47` |
| `usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json` | added | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| `usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json` | added (Krystal v2 Full body qualified) | `a2254930489772c024a42d057b98a5a01e164be05096dd85df2d461aad73d622` |
| `usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json` | replaced: v1.1.0, 33 files, **unsigned** | `b547c6dd2c8c7046141480951c40f89579daf6b741aaf4fb3ad5cb2b964f2cf8` |
| `…/sfm_character_tools_inventory.sig` | **left out** until the Owner signs | — |

**Build and verify:**
1. Copy `rc.template.json` to a new run folder as `rc.json` and fill in the three paths.
2. Run `python -I rc2_tool.py <Q>\rc.json package`, then `… verify`.

The result is ZIP `SFM.Character.Tools.v1.1.0-rc2-UNSIGNED.zip`
`46be7dbf375127050f433c73d442143497bec12bd7d28dc50f57765cccc76577` (1007 entries; deterministic).

**Signing (Owner only):** as in `README_RC1.md`, with `--spec release/v1.1.0-rc2/SOFTWARE_SPEC.json`.
