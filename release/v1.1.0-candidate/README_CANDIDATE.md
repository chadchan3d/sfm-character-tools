# SFM Character Tools v1.1.0: production CANDIDATE (unsigned, not for distribution)

Prepared offline under "F-01 — Authorize Offline v1.1.0 Production Candidate Preparation" (2026-11-12). Not
installed, not natively qualified, not signed, not released. Record: `cpm/qualification/F01_V110_PRODUCTION_CANDIDATE.md`.

## What it is

The published v1.0.0 package (`SFM.Character.Tools.v1.0.0.zip`, `5323b143…`, 1006 entries) with exactly these changes:

| Entry | Change | SHA-256 |
|---|---|---|
| `usermod/scripts/ChadChan3D_CPM/SFM_Character_Preset_Manager.py` | replaced: the F-01 production candidate CPM | `84cd996c914f82bcc41414413958a5a9b536fca088081d862559f48a69144568` |
| `usermod/scripts/SFM Character Tools/cpm_pose_profiles_v1.json` | added (Pose Library registry; left arm qualified) | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00` |
| `usermod/scripts/SFM Character Tools/cpm_body_profiles_v1.json` | added (body registry; Krystal v2 Full body experimental) | `22dcd1599c0556bcb71df0a9b9d14657684173b3bbf557250710a8104a6baa26` |
| `usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.json` | replaced: v1.1.0, 33 files, **unsigned** | `036786e1ab619bb6231c59785575585ff493194cd50deb4bf971f26b92b24ffa` |
| `usermod/scripts/sfm/mainmenu/SFM Character Tools/sfm_character_tools_inventory.sig` | **left out** until the Owner signs | — |

Every other entry (1003) is the v1.0.0 release's exact bytes: the Normalizer, the CPM launcher, adapter and projection,
the authority package, the sidecar reader, the updater, the bundled Animation Groups data, the optional button and the
READMEs. They come from the published ZIP, not from a repository checkout, because several repository sources differ
from the shipped bytes in line endings only.

- **Spec:** `SOFTWARE_SPEC.json` (`3909f6a6…`), the format of `updater/release_tools/character_tools_software_v1.json`.
- **Package build:** `real_sfm_qualification/f01_ps2_v110/tools/ps2_tool.py package` (deterministic ZIP: fixed
  timestamps, sorted entries, deflate 9). Candidate ZIP `SFM.Character.Tools.v1.1.0-candidate-UNSIGNED.zip`
  `44184585111f861b16d8f58bb7f3f1e3f163c2343c85083b71412f2f80922b69` (1007 entries; outside the repository).

## Signing (Owner only; after PS-2)

`updater/release_tools/make_software_inventory.py sign --spec release/v1.1.0-candidate/SOFTWARE_SPEC.json --root
<stage>\usermod --software-version 1.1.0 --private <key outside the repository> --out <new folder>`. With the v1.0.0
key (`ed25519-5d879134807dff6d`) it writes the same inventory bytes (`036786e1…`) and its signature. Offline, the
updater's own `parse`, `check_profile` and `check_files` already accept the unsigned inventory and the staged files.

## Not yet done (release blockers)

1. Native PS-2 (`real_sfm_qualification/f01_ps2_v110/PROCEDURE.md`) and its verdict.
2. The Owner's signature; then the final ZIP (with the `.sig`), whose hash replaces the candidate's.
3. README text for v1.1.0 (the package still carries the v1.0.0 README and optional README; owner-approved copy).
4. Workshop installer: `workshop_installer/release.py` pins v1.0.0 (version, archive SHA-256, 1006 entries, 31
   inventory entries, the exact path set); v1.1.0 needs the new values (1008 entries with the `.sig`, 33 inventory
   entries, the two registry paths) and a rebuilt installer, after signing.
5. Updater distribution check with the signed v1.1.0 inventory (the updater refuses an unsigned one by design).
6. Merge to `master`, tag, GitHub release, Workshop publication: separate authorizations.
