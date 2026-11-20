# SFM Character Tools v1.1.0: release candidate 3 (unsigned, not for distribution)

RC2 (`release/v1.1.0-rc2/`) with the structural rig adapter enabled for normal installations: Fox structural rigs
(F-01 Stage 1) and Tails' declared JIGGLE leaves (F-01 Stage 2). Record: `cpm/qualification/F01_V110_RC3_INTEGRATION.md`.

| Entry | Change against v1.0.0 | SHA-256 |
|---|---|---|
| `usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py` | replaced: RC2's CPM with Stage 1 and Stage 2, the structural adapter `qualified` | `026a65cd4447233093a3429b60a7adf481d9a92060613bae15ef59bf1076c9ba` |
| `usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json` | added (unchanged from RC2) | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| `usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json` | added (unchanged from RC2; Krystal v2 Full body qualified) | `a2254930489772c024a42d057b98a5a01e164be05096dd85df2d461aad73d622` |
| `usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json` | replaced: v1.1.0, 33 files, **unsigned** | `bda55d9e8657b576192b3a0b1e4c0f41ca9207d4531c39f707fccd4b8c7ff01d` |
| `…/sfm_character_tools_inventory.sig` | **left out** until the Owner signs | — |

**Build and verify:**
1. Copy `rc.template.json` to a new run folder as `rc.json` and fill in the three paths.
2. Run `python -I rc3_tool.py <Q>\rc.json package`, then `… verify`.

The result is ZIP `SFM.Character.Tools.v1.1.0-rc3-UNSIGNED.zip`
`5ca540720d9313dcbbe26073a4512631ace8a6f21e6ad9964acc336917254c6a` (1007 entries; deterministic).

**Signing (Owner only):** as in `README_RC1.md`, with `--spec release/v1.1.0-rc3/SOFTWARE_SPEC.json`.
