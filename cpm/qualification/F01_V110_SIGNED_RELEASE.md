# SFM Character Tools v1.1.0: signed release package and final verification

**Authority:** "SFM Character Tools v1.1.0 — Signing and Final Package Verification GO" and "SFM Character Tools v1.1.0
— Signing Complete" (Owner, 2026-11-20). The Owner accepted the documented RC5 evidence gaps
(`F01_V110_RC5_RELEASE_READINESS.md` section 6, `de46c31`). Not merged, pushed or published; Workshop Setup unchanged.

## 1. Signing (Owner)

The Owner signed locally with the existing tool (`updater/release_tools/make_software_inventory.py sign`, unchanged),
spec `release/v1.1.0-rc4/SOFTWARE_SPEC.json`, root the verified RC5 stage. Reported output: inventory
`15db1c1a…`, 33 files, key `ed25519-5d879134807dff6d`, profile `sct-authority-profile-2`, contract `d767c3d5…`. No key
material was read, requested or handled in this work; only the two output files were used.

The signed inventory is byte-identical to the verified unsigned RC5 inventory; the signature is
`28bd1fcaf7583aa7e2fd0b3aaabf568248a0e3f02be850d6724a68d654464ad4` (64 bytes).

## 2. Signed package

| Item | Value |
|---|---|
| ZIP | `SFM.Character.Tools.v1.1.0.zip` **`9ca68df39fe8e0494de8c0db8be41c68faa28b2df182ea2f2f51ccbcde7d16f1`**, 17,847,759 bytes, 1008 entries |
| Built by | `release/v1.1.0-rc5/rc5_signed_tool.py` (`172b4534…`) `package-signed`: the unsigned RC5 entries plus the signature, RC5's deterministic ZIP rules |
| Reproducible | built in `E:\SFM_U0B_Scratch\f01-v110-rc5\signed` and `…\f01-v110-rc5-repro\signed`: identical ZIPs, identical manifests (`3b2b8108…`) and identical verification records (`d5d08a71…`) |
| Artifact list | `release/v1.1.0-rc5/SIGNED_ARTIFACTS.txt` |
| Preserved | unsigned RC5 `baadc4be…`, RC4 `bef9171a…`, published v1.0.0 `5323b143…`, all earlier evidence (hashes re-checked) |

## 3. Verification: SIGNED VERIFY PASS (both builds)

| Check | Result |
|---|---|
| Controls (before signing) | the published v1.0.0 passes the updater's production `verify_installation` (31 files, key `ed25519-5d879134807dff6d`); the v1.1.0 inventory with v1.0.0's signature is refused ("signature does not verify") and nothing is written |
| Integrity | 1008 entries, `testzip` clean, manifest equal to the ZIP's bytes, the ZIP equals the unsigned RC5 ZIP plus exactly the signature entry |
| Changes against v1.0.0 | replaced: `README.txt`, the CPM, the inventory, the signature; added: the two registries; removed: none; 1002 entries the exact v1.0.0 bytes |
| Identities | README `af87797b…` (12,510 bytes; also compared byte for byte with the approved file and the repository copy), CPM `b89af5a8…`, registries `f445d5ef…` and `a2254930…`, inventory `15db1c1a…` |
| Signature | the updater's `official.verify_signature` with the production trust store only (one key, `ed25519-5d879134807dff6d`, the same key as v1.0.0): verified |
| Updater | the updater's `inventory.verify_installation` (production keys) on the extracted `usermod`: SFM Character Tools 1.1.0, profile `sct-authority-profile-2`, 33 files, inventory `15db1c1a…` |
| Version | the CPM's own `prod_release_version` reads 1.1.0 from the signed inventory for this build, nothing for another build |
| Installer | the Workshop installer's `core.prepare` accepts the signed ZIP with v1.1.0 constants derived in memory (paths = v1.0.0's plus the two registries; CPM, registries and signature prepared); `release.py` not changed |
| Rollback | v1.0.0's ZIP is the pinned archive; its CPM `ccbed9d7…` reads no registry |

Run with the updater build environment's Python 3.10.6 and `cryptography` 50.0.2, `-I`.

## 4. Distribution readiness

**ZIP distribution: ready for the Owner's publication decision.** The signed ZIP is complete and verified, with the
documented RC5 evidence limits accepted by the Owner. Publishing (GitHub release, links) and the merge and push of
`feature/f01-pose-library` are the Owner's separate steps.

**Steam Workshop: not ready; Workshop Setup installs only v1.0.0.** `workshop_installer/release.py` binds Archive A
(v1.0.0, `5323b143…`), and Setup refuses any other ZIP. To install v1.1.0 it needs, each separately authorized:
1. `release.py`: `VERSION` 1.1.0, `ARCHIVE` `SFM.Character.Tools.v1.1.0.zip`, `SHA256` `9ca68df3…`, `ARCHIVE_ENTRIES`
   1008, `INVENTORY_ENTRIES` 33, `PATHS` plus the two registries; `OBSOLETE` stays empty (nothing is removed). The
   in-memory dry run above shows `core.prepare` accepts the signed ZIP with exactly these values.
2. Tests: `test_disposable` pins 1006 files and `test_window` pins version 1.0.0 texts; they need the v1.1.0 values, and
   the suite (29 tests) re-run with `SCT_V1_RELEASE_ZIP` set to the signed ZIP. An upgrade from a v1.0.0
   Setup installation (installed record 1.0.0, package 1.1.0) should be covered explicitly.
3. Rebuild `SCT_Setup.exe` (`build.ps1`, Python 3.10 and PyInstaller 6.11.1): `release.py` is bundled, so the helper hash
   changes, and with it the generated management launcher.
4. Re-stage the four-file Workshop payload (`stage.py`: launcher, Setup, the v1.1.0 ZIP, manifest) and `stage.verify`.
5. Native acceptance on Windows: update an existing v1.0.0 Workshop installation to 1.1.0, then Manage Installation
   uninstall (the registries are then known paths and are removed). The Workshop README's Archive A/B notes and
   `QUALIFICATION.md` need updating.
6. The Owner's Workshop item update through the established Scripts-category upload procedure.

Until then, the Workshop item keeps distributing v1.0.0, and the v1.1.0 README's Workshop uninstall note (files left
after a ZIP is installed over a Workshop installation) applies.
