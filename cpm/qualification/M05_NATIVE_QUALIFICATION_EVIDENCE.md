# M-05 native qualification — evidence manifest

**Milestone:** M-05 — Static Mode-3 Bone-Scale Compatibility.
**Authority:** frozen R15 Implementation Blueprint; Astra M-05 Production Correction Design (2026-10-24); Convergence
Ledger. **Run:** 2026-10-26, one disposable fixture, one machine (Windows 10, SFM Python 2.7.5). **Result:** gates A–G
PASS; restoration exact.

The complete raw evidence stays in the owner's local qualification archive `m05-native-qualification/` (paths below are
relative to it). It is not committed: it contains a local scene, preset-library copies and logs with workstation paths.

## Identities

| Item | SHA-256 |
|---|---|
| Qualified CPM `cpm/app/SFM_Character_Preset_Manager.py` (committed) | `6275f04acd7355abeb1ec032d990aa28140de0bfb2cfb6ce1490aef34592ddde` |
| M-05 suite `cpm/convergence/tests/test_cpm_app_m05_static_scale.py` (committed; 115/115, Python 2.7.5 and 3.10) | `8b3316eb32154c94841a0567173eea4507a124d6304f98bbff72526b10cf80c3` |
| Canonical-route harness `cpm/convergence/tests/test_cpm_app_canonical_route.py` (committed) | `febea0338996aba495136d568e9500b077cf7e6222efbf98420c46467b2417d7` |
| Published CPM (installed before and after; v1.0.0) | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df` |
| Fixture `fixture/m05_qual_fixture.dmx` (shot10 / `Krystal`, `krystal2020.mdl`; unchanged before and after) | `fa9a0a461b12ce2d51e4a05b2ebde6c8c3ad845ca4b4ddc9fdf63fe348b0767a` |
| Read-only observer `observer/M05_Qualification_Observer.py` (temporary menu entry) | `ffae20a64dcd8cd8d4053983631ad17cbf419cf6ab11c00883ca5b0ce9804b0b` |
| Apply target: owner Body preset `d1c94` (`bip_head` 1.33; read only) | `cd31c7f1661bd36e87f54cb50b91d7ec4447e83bc6a00573a998496ce8a71f18` |

The CPM log header and `PROD_R15_MODULE` record confirm the loaded build `6275f04a…`.

## Evidence files

| File | SHA-256 |
|---|---|
| `observations/obs_001_20261026T184233.json` (A) | `053060c6ddb002afb44a1f0fd44a974abc92aec66a90adf267edf29174ded727` |
| `observations/obs_002_20261026T184523.json` (B) | `c84e91276ea7e5417cd463dc9d0d2cb69e42d8f440cc5ddcacc2b55d2a555cf5` |
| `observations/obs_003_20261026T184746.json` (C) | `550b2a44a6fb3a3393ee227aa3114fc28007b87396e5b38aa6e397571a188e40` |
| `observations/obs_004_20261026T185319.json` (D, 0.5 s) | `d6868821065f1b5896c2942569b39ab0a86298cfe5efd977c208692ddcdd81d3` |
| `observations/obs_005_20261026T185343.json` (D, 0.375 s) | `c2d56f00a10eac64abf7578b469acd4532aeb9ea4b5871a6027979d125c474ee` |
| `observations/obs_006_20261026T190836.json` (E, Undo) | `cb0745e2f0992455b04c4f58f446f0be39d417edd98090a5b9d43b1a13075be0` |
| `observations/obs_007_20261026T190859.json` (E, Redo) | `2ffafe8e277c9ca9ffdc0efb4b6c33262ee8026ba6400ca9443eb286568cf0f3` |
| `observations/obs_008_20261026T191226.json` (F) | `ab3e00a06f2c86ddce0712558975babaa1aaa5722bd758c9e642f67beb9655e6` |
| `observations/obs_009_20261026T191504.json` (G, reopened) | `f79dd674850ce7399a16bb78aa7d9614d6449eb5a01efb7229d0369e98b26c54` |
| CPM native log `evidence/cpm_logs/CPM - 2026-10-26_22-44-36Z - pid14752 - abeb43 - 001.log` | `903fa6b2f3aaa82aa30221481dca9cd584bc027fe457bbef5a51ccd2f7c2881d` |
| Saved preset `evidence/library_after_run/…/M05 Qual Baseline--preset-83130.json` | `91b4fee07b0352fc7894b0e37458c22493dd4393693ccfe04ce12e555f7b53f2` |
| Saved/reopened scene copy `persistence/m05_qual_saved.dmx` | `544946cefa156d3e97c89d2e208b2156731bbf8279797c2f5031184fc6a0c32e` |
| Offline persistence inspection `persistence/m05_qual_saved_offline_graph.json` | `f605d5b33bb49d41b2a241ff5cc525db555237c20882f58e20f5c4b53ce8241e` |
| Restoration report `evidence/restore_log.json` | `da00d4122a4cc0e74d8eeb8d6fcde4d4d07061dcb44869de90de12aaeabcb965` |
| Pre-run integrity `pre_run/integrity_pre.json` | `9899dd707c45ac2fa61d8059acb1d11050d1e23f0dc15f0fd56a0b70dcd2f4b9` |
| Post-run integrity `post_run/integrity_post.json` | `d43bb5d3bf5f01a87a81c0e1bd85fa9a1eb1ba45e1c093541b8123b15d5d7eaf` |
| Integrity / restoration tools `tools/integrity.py`, `tools/restore.py` | `9f5ba0a3…`, `9c941935…` |

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A — Initial state | **PASS** | obs 001: static mode-3 graph (input mode 3, one float-log layer, one key at t=0; `lerp(value, lo, hi)` lo 0 / hi 10; output mode 3, one empty layer, `usedefaultvalue` 0; single scale writer); `bip_head` 1.13, the only non-neutral bone; digest `6594ca22…`; Undo count 0 |
| B — Body Save | **PASS** | log `PROD_SAVE=PASS controls=26 bone_records=154 existing_scale_controls=1`, outcome `verified`; preset: 154 unique bones, `bip_head` 1.13 `existing-static-control`; obs 002 identical to 001 (no scene change, no Undo entry) |
| C — Changed Apply | **PASS** | log: `native-commit` → `PROD_APPLY_REFRESH` → `verification-pending` (`play_scales=1`, head 0.375) → `ACTION_RETURN_PENDING` → one deferred `PROD_APPLY_DEFERRED_VERIFY outcome='committed-verified'` 51 ms later → outcome `verified`, one result; obs 003: output mode 3 with the same log/layer identities and still empty, lo/hi unchanged, bone 1.33005 = preset; only `bip_head_scale` and the five differing flexes changed |
| D — Evaluation stability | **PASS** | obs 004 (0.5 s) and 005 (0.375 s) identical to obs 003 |
| E — Native Undo/Redo | **PASS** | one Ctrl+Z: obs 006 equals obs 001 exactly (graph, 747 channel records, 289 controls, bone map, digest), Redo available; one Ctrl+Y: obs 007 equals obs 003 exactly, mode 3 preserved |
| F — No-op | **PASS** | "Already matches this preset."; log `outcome='no-op'`, Undo state identical before/after; no transaction or deferred check; obs 008 equals obs 007 |
| G — Persistence | **PASS** | saved copy read offline: shot10 mode 3/3, key 0.1330049, stored bone scale 1.33005, empty output layer, `usedefaultvalue` 0; shots 13–15 unchanged at 1.13; reopened obs 009 (Undo count 0) equals obs 008 |

## Restoration

With SFM closed: published CPM `ccbed9d7…` restored; observer removed (folder held only the observer, no bytecode);
preset library restored from its full backup; `demoheader.tmp` and `tf2_playerstats.dmx` restored (98 other
housekeeping/bytecode files unchanged). Pre-run and post-run protected inventories are identical, file by file:

| Location | Files | Inventory SHA-256 |
|---|---|---|
| `usermod/scripts` | 1,107 | `57ff4cd5ecf3ffcf54c9f37acf8d1395caa1f6f78d019df849fbf731709f8b19` |
| `usermod/cfg` | 59 | `fed6f8ae82cc509c95c0ac7bb590562e1e293effd2e0b11515b59c3ce32be3e1` |
| CPM preset library (23 directories) | 107 | `cd0e3fef3e20ce7a2aa0080e98693c5f95501aafe7ef80d8ecd10271090841ad` |
| SFM sessions folder (originals `3af2ad54…` unchanged) | 986 | `4458fc74b8a2b05dfd43c471d7cae7f14c269e96e4d8c76121da0291ed400431` |

## Limitations

- One run on one fixture and one machine.
- The single zero-delay verification ran after SFM's evaluation in this run; Qt does not guarantee that ordering in
  general. A check that runs first ends committed-unverified by design.
- Native abort-recovery (precommit failure) was not exercised; it is covered offline only.
- The Undo item count after Apply (32) counts elements within the single `Apply Body Preset` transaction.
- SFM's recent-documents list (registry) was not restored.
- The separate animation-import flex incompatibility is unresolved and outside M-05.
- Public v1.0.0 (CPM `ccbed9d7…`, signed inventory, release assets) is unchanged; this correction is not released.
