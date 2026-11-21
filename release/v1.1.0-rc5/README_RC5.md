# SFM Character Tools v1.1.0: release candidate 5 (unsigned, not for distribution)

RC4 (`release/v1.1.0-rc4/`) with the Owner-approved v1.1.0 `README.txt` in place of v1.0.0's. Nothing else changes:
the same software spec, CPM, registries and unsigned inventory.

Authority: "SFM Character Tools v1.1.0 — README Integration and Final Release Smoke GO" (2026-11-20). Record:
`cpm/qualification/F01_V110_RC5_RELEASE_CANDIDATE.md`.

| Entry | Change against v1.0.0 | SHA-256 |
|---|---|---|
| `README.txt` | replaced: the approved v1.1.0 README (12,510 bytes, 324 lines, ASCII, LF, final newline) | `af87797bad22e446e002a776d41cdebb5a1a23e236cef74ade9a5705e836a04f` |
| `usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py` | replaced: the integrated F-01 production CPM (RC4) | `b89af5a8e8e86e65352a34803aef84b751c42082aecb58be250149da39e02525` |
| `usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json` | added (unchanged since RC1) | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| `usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json` | added (unchanged since RC1) | `a2254930489772c024a42d057b98a5a01e164be05096dd85df2d461aad73d622` |
| `usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json` | replaced: v1.1.0, 33 files, **unsigned** (identical to RC4's) | `15db1c1aa9a53f59c82c5068d7b60a741f9a35b8de641080311d2ac33864f948` |
| `…/sfm_character_tools_inventory.sig` | **left out** until the Owner signs | — |

All other 1002 entries are the exact bytes of the published v1.0.0 ZIP (`5323b143…`). Against RC4, only `README.txt`
differs.

`README.txt` is at the ZIP root, outside `usermod/`, so it is not an inventory file: the spec
(`release/v1.1.0-rc4/SOFTWARE_SPEC.json`, `15437690…`) and the inventory to be signed are unchanged, and the Workshop
installer never installs it. `README.txt` in this folder is the approved file, byte for byte (`.gitattributes` keeps it
from line-ending conversion).

## Build and verify

1. Copy `rc.template.json` to a new run folder as `rc.json` and fill in the three paths.
2. Run `python -I rc5_tool.py <Q>\rc.json package`, then `… verify`.

- **Result:** ZIP `SFM.Character.Tools.v1.1.0-rc5-UNSIGNED.zip`
  `baadc4be54e17aead1ddf16474956b9b4cb9ba41fe073f7d4b568bf661fcf6d9` (1007 entries).
- **Deterministic:** two independent builds are byte-identical.
- **Verify:** RC VERIFY PASS (package, including the approved README; updater, version, installer, rollback).

`rc5_tool.py` runs RC1's `rc_tool.py` unchanged and adds only the README: a fifth pinned candidate entry, the manifest's
replaced list, the package check's expected changes and README identity, and the rollback check's kept-file count.

Installation, rollback and signing are as in `README_RC4.md`, with this package and `rc5_tool.py`.
