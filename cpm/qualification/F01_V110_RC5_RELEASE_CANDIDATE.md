# F-01 v1.1.0 release candidate 5: README integration (unsigned, not released)

**Authority:** "SFM Character Tools v1.1.0 — README Integration and Final Release Smoke GO" (Owner/Designer,
2026-11-20). The v1.1.0 README is approved exactly as presented (`README_v110_FINAL.txt`). F-01 functionality is
frozen: no CPM, compatibility rule, tolerance or other approved software changed.

RC4's record (`F01_V110_RC4_RELEASE_CANDIDATE.md`) stays as written; RC5 resolves its blocker 1 (the v1.0.0 README).

## 1. Identities

| Item | Value |
|---|---|
| Product source | last product change `2eacd7e`; RC5 adds only release files and the README |
| Approved README | `release/v1.1.0-rc5/README.txt` `af87797bad22e446e002a776d41cdebb5a1a23e236cef74ade9a5705e836a04f`, 12,510 bytes, 324 lines, ASCII, LF, final newline; byte-identical to the approved `README_v110_FINAL.txt` |
| Production CPM | `b89af5a8e8e86e65352a34803aef84b751c42082aecb58be250149da39e02525` (1,576,306 bytes), unchanged |
| Registries | `f445d5ef7fb183e6bcae3099b3812ffd2363213911605134231c2a1f708d6d00`, `a2254930489772c024a42d057b98a5a01e164be05096dd85df2d461aad73d622`, unchanged |
| Spec | RC4's `release/v1.1.0-rc4/SOFTWARE_SPEC.json` `1543769092ea3878bfb7f6464c2138cfd27f68288acd2868b0cec8c5a5be5b61`, unchanged (the README is outside `usermod/`, so not an inventory file) |
| Inventory (unsigned) | `15db1c1aa9a53f59c82c5068d7b60a741f9a35b8de641080311d2ac33864f948`, identical to RC4's |
| Package | `SFM.Character.Tools.v1.1.0-rc5-UNSIGNED.zip` `baadc4be54e17aead1ddf16474956b9b4cb9ba41fe073f7d4b568bf661fcf6d9`, 1007 entries (1002 exact v1.0.0 bytes, 5 candidate) |
| Tool | `release/v1.1.0-rc5/rc5_tool.py` (RC1's `rc_tool.py` unchanged, plus the README entry) |
| RC4 package | `bef9171a…` and its evidence preserved unchanged |

## 2. Packaging change

The only packaging change is a fifth candidate entry, `README.txt`, pinned by `readme_sha256`. `rc5_tool.py` adds it to
the manifest's replaced entries, to the package check's expected changes (with the README identity) and excludes it from
the rollback check's kept v1.0.0 files. The ZIP-entry rules, timestamps and compression are RC4's.

## 3. Verification (offline)

- **RC VERIFY PASS** on both builds (`E:\SFM_U0B_Scratch\f01-v110-rc5` and `…-rc5-repro`): package (changed exactly
  `README.txt`, the CPM and the inventory; added the two registries; removed the signature; README is the approved
  bytes), updater (inventory parse, profile, 33 files), version (1.1.0 for this build only), installer (Workshop
  `core.prepare` dry run), rollback (1002 v1.0.0 files exact; v1.0.0 CPM reads no registry).
- **Reproducible:** two independent builds give the identical ZIP `baadc4be…`.
- **Independent comparison:** RC5 and RC4 ZIPs have the same 1007 entry names; only `README.txt` differs. The packaged
  README equals the approved file; the packaged CPM and registries equal the repository files and the pins. Both ZIPs
  pass `testzip`.
- **Regression:** no product file changed, so the CPM suites recorded at `2eacd7e` stand. Kit tests: `test_rc4s` 20/20
  (after the pin update), `test_rc4r` 19/19; `test_rc4x` 35/36, `test_rc3s` 34/35 and `test_rc1s` 25/26 fail only
  their historical CPM pins, as recorded for RC4.

## 4. Final smoke kit

`real_sfm_qualification/f01_v110_rc4_smoke/` had not been run. Before any run, its package pin `rc4_zip_sha256` (name
kept) moved to the RC5 ZIP, `RC_ZIP` names the RC5 package, and Save New's feedback item now accepts a busy cursor (the
Owner's decision). `procedure_sha256` is re-pinned (`df1c3794…`); the analyzer and every other pin are unchanged.

## 5. Final production-native smoke

Results are recorded in section 6 once the run is complete.
