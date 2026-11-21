# SFM Character Tools v1.1.0: release candidate 4 (unsigned, not for distribution)

RC3 (`release/v1.1.0-rc3/`) with the F-01 RC4 changes, each qualified natively:
- same-model cross-rig adaptation;
- Astra's bounded static-offset equivalence for structural rigs;
- Astra's revised verification contract (reproduction envelope 0.01 units / 0.1°, the reproduction-mismatch outcome,
  and the no-work repeat Apply);
- Save New responsiveness;
- the Pose Info Rig row.

Record: `cpm/qualification/F01_V110_RC4_RELEASE_CANDIDATE.md`. User-facing notes (draft): `RELEASE_NOTES_v1.1.0.md`.

| Entry | Change against v1.0.0 | SHA-256 |
|---|---|---|
| `usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py` | replaced: the integrated F-01 production CPM (RC4) | `b89af5a8e8e86e65352a34803aef84b751c42082aecb58be250149da39e02525` |
| `usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json` | added (unchanged since RC1) | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| `usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json` | added (unchanged since RC1; Krystal v2 Full body qualified) | `a2254930489772c024a42d057b98a5a01e164be05096dd85df2d461aad73d622` |
| `usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json` | replaced: v1.1.0, 33 files, **unsigned** | `15db1c1aa9a53f59c82c5068d7b60a741f9a35b8de641080311d2ac33864f948` |
| `…/sfm_character_tools_inventory.sig` | **left out** until the Owner signs | — |

All other 1003 entries are the exact bytes of the published v1.0.0 ZIP (`5323b143…`). Against RC3, only the CPM and the
inventory differ.

## Build and verify

1. Copy `rc.template.json` to a new run folder as `rc.json` and fill in the three paths.
2. Run `python -I rc4_tool.py <Q>\rc.json package`, then `… verify`.

- **Result:** ZIP `SFM.Character.Tools.v1.1.0-rc4-UNSIGNED.zip`
  `bef9171a6e06aa1e2d3d0d0628d641bf33d3238a91952d7b6b15c659ad52f8fd` (1007 entries).
- **Deterministic:** two independent builds are byte-identical.
- **Verify:** RC VERIFY PASS (package, updater, version, installer, rollback).

## Installation (for the native release smoke, and after signing)

1. Close Source Filmmaker.
2. Extract the ZIP, and merge its `usermod` folder into `…\SourceFilmmaker\game`, replacing existing files.
3. Start SFM. The tools are under Scripts > SFM Character Tools, as in v1.0.0.

Installing replaces `usermod\cfg\sfm_defaultanimationgroups.txt`, as v1.0.0 does: back up a customized file first.

## Rollback to v1.0.0

1. Close SFM.
2. Merge the published `SFM.Character.Tools.v1.0.0.zip` (`5323b143…`) the same way. This restores the v1.0.0 CPM
   (`ccbed9d7…`) and inventory.
3. Delete the two v1.1.0 registry files, `usermod\scripts\SFM Character Tools\cpm_pose_profiles_v1.json` and
   `cpm_body_profiles_v1.json`. v1.0.0 never reads them, so leaving them is harmless (RC VERIFY's rollback check).

Saved poses (the `Poses` folders, `pose_sources.json` and `pose_rigs.json`) are ignored by v1.0.0 and are kept for a
later reinstall.

**Signing (Owner only):** as in `README_RC1.md`, with `--spec release/v1.1.0-rc4/SOFTWARE_SPEC.json`.
