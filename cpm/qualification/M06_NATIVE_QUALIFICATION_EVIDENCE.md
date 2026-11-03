# M-06 native qualification — evidence manifest

**Milestone:** M-06 — Imported static flex compatibility (`STATIC_PLAY_ONE_KEY_ZERO`) and W1 selected-instance
resolution. **Authority:** Astra M-06 Production Correction Design; Astra M-06/M-05 Integration Correction Design
(2026-10-29); the accepted M-06 native qualification runbook; Convergence Ledger. **Run:** 2026-10-31 (G0–G5, D1) and
2026-11-02 (D2–D5, G7), disposable fixtures, one machine (Windows 10, SFM Python 2.7.5). **Result:** G3–G6 PASS
(P1–P9, T01–T12, D1–D5); G7 RESTORED, `integrity.py post` PASS.

The complete raw evidence stays in the owner's local qualification archive `m06-native-qualification-4/` (paths below
are relative to it). It is not committed: it contains local scenes, preset-library copies and logs with workstation
paths. The campaign evidence ledger `evidence/EVIDENCE_LEDGER.md` records every observation, verdict and correction
with its SHA-256.

## Identities

| Item | SHA-256 |
|---|---|
| Qualified CPM `cpm/app/SFM_Character_Preset_Manager.py` (W1; committed) | `fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d` |
| M-06 suite `cpm/convergence/tests/test_cpm_app_m06_static_play_flex.py` (334/334, Python 2.7.5 and 3.10) | `e062824850c404a278fea98943956f98294d4c17c29addcee516ffea3508f93e` |
| W1 suite `cpm/convergence/tests/test_cpm_app_m06_instance_resolution.py` (179/179, Python 2.7.5 and 3.10) | `7f32563c872644269b9aadb8fa0be90a3e0485136c7854114e6955441fdd27b9` |
| Canonical-route harness `cpm/convergence/tests/test_cpm_app_canonical_route.py` (M-06 / W1 allow-lists) | `575139e574f2579be22aa95a537a94cf9c3e644f1498887851be2d282a12d890` |
| M-05 suite `cpm/convergence/tests/test_cpm_app_m05_static_scale.py` (115/115) | `c9702123507540bf4a684c0a734e37293646e942e53ceaa3b1034276e22704b8` |
| `cpm/convergence/tests/test_cpm_app_bounded_logging.py` | `baee9e342cf8205b83cbd954359bc9cdad2e4918f248040927c13fccceac080e` |
| `cpm/convergence/tests/test_cpm_app_empty_states.py` (15/15, Python 2.7.5) | `ca8c3442b0069777d530827fb08c6f7f4a5a56c09df90fe4cde1625ba893fbaa` |
| W2 qualification instruments and tools `real_sfm_qualification/m06_w2_qualification/` (20 files; suite 127/127, 1 skipped, both interpreters) | accepted sums file `2cb3e4f9fb1921e48149a09f47cbfd7e71bd2a3981c559598935e66bffc155a6` |
| W2 core `instruments/m06w2_core.py` | `cde4297c466b7da9…` |
| W2 comparator `tools/compare_obs.py` | `ea80f2a8816ee7a4…` |
| Published CPM (installed before and after; v1.0.0) | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df` |
| Deferred fixture `deferred/m06w2_deferred_disposable.dmx` (byte copy of the protected M-05 original) | `fa9a0a461b12ce2d51e4a05b2ebde6c8c3ad845ca4b4ddc9fdf63fe348b0767a` |

All seven committed CPM source/test files equal the reviewed W1 candidate tree byte for byte.

## Records

| File | SHA-256 |
|---|---|
| Campaign evidence ledger `evidence/EVIDENCE_LEDGER.md` (229 lines) | `95aed481fb367ef11f15f1d6577a0472e8fd034d94606300d1d19689fbbfc8de` |
| Pre-run integrity `pre_run/integrity_pre.json` | `e73b60860ff54b0ce17c2110f0112894e1bf62b59ed248443f169e6d4f4b4509` |
| Post-run integrity `post_run/integrity_post.json` | `8f1dfabbe0100c19910bf5fc191037b07cceeb0ee2098dcffebd66d03ab9f8e9` |
| Restoration report `evidence/restore/restore_log.json` | `68e9e056b80feea338856efb388a626c1c7e712cf9f86b21e2c9102d89068e5b` |
| Restoration journal `evidence/restore/restore_journal.json` | `53312b8564532b439a13945ff86260c0b7b2d0566749693198d9f1700e4e480f` |
| T10 reopened (native pairing) `evidence/T10/T10_reopened_native_pairing.txt` | `af50c9b6c80dffab21943ef0c0c31e10d52e14914b1c32d76977c6bfac16003f` |
| D3 reopened (native pairing) `evidence/D3-D5/D3-D5_reopened_native_pairing.txt` | `ea855785dd255714bbd738a26c85488785eab15b007cde35a0b6f199db4f88eb` |
| T11 peer-preset comparison `evidence/T11/T11_peer_preset_dep4.json` | `216ec637aaa9c401c06911d8a488f61929ed0bbdb9b40bb09c47d3c256fa9a46` |
| D2 prepared verdict `evidence/D2/prep_20261102T181524_verdict.json` | `f50c2cb0d0384996b1af50eed2bc23d0a11d63ee94c67b960f64085dca25482c` |
| Integrity / restoration tools `tools/integrity.py`, `tools/restore.py` | `746f21de…`, `64daba2d…` |

## Checkpoints

| Checkpoint | Result | Evidence |
|---|---|---|
| G3-a — native prerequisites | **PASS** | P1–P5, P7, P9a–c; P6 multi-instance part; both Observers, both Probes, Injector arm/disarm; scene unchanged |
| G3-b — selection | **PASS** | P8: three Select Model operations, each scope-begin/scope-ready naming the selected instance; target and peer `unchanged`. Note: W1 does not log a live signature at selection |
| G3-c — M-05 topology | **PASS** | P6: static flexes one key at 0 equal to stored, 22 zero-key flexes empty; `bip_head` input and output mode 3 |
| G4 | **PASS** | P1–P9 all PASS |
| T01 — Body Save | **PASS** | 154 control-backed bones (150 / 155 `*_twist2` have no transform control, scale value or scale writer), every flex at full precision; one preset file added (Owner-approved coverage rule) |
| T02 — Update | **PASS** | values and bone scales equal T01 exactly; previous file kept as `.bak` |
| T03 — no-op Apply | **PASS** | "already matches this preset"; Undo empty before and after |
| T04 — slim Apply | **PASS** | stored and effective 0.55; one owned Undo entry; committed-verified |
| T05 — imported Muscles Apply | **PASS** | `STATIC_PLAY_ONE_KEY_ZERO` admitted, sole writer; stored and effective 0.80 |
| T06 — empty-log flex Apply | **PASS** | AnalOpen empty → one key 0.35, same log and layer identities (settles U3) |
| T07 — Undo / Redo | **PASS** | one Ctrl+Z restores the exact pre-Apply state; Ctrl+Y the exact post-Apply state |
| T08 — scale graph creation | **PASS** | `bip_head` graph created (scale 1.25); Undo exact |
| T09 — injected abort | **PASS** | authored state and Undo fields restored exactly; all 8 created elements removed |
| T10 — save / reopen | **PASS** | applied key persisted bit-exact; 896 orientation-quaternion components within 2 float32 ULP (Owner-approved rule) |
| T11 — peer isolation | **PASS** | Save from the peer's own instance; peer preset matches the peer, not the target (`bip_head` 1.3300491571426392) |
| T12 — existing mode-3 scale graph | **PASS** | control 0.15, physical 1.50; graph identities, expression, lo/hi and empty output log preserved |
| D1 — deferred fixture | **PASS** | byte copy verified, never opened before D2 |
| D2 — preparation | **PASS** | Muscles stored source 0.6046798229217529, key unchanged; in-session and offline |
| D3 — save / restart / reopen | **PASS** | Muscles still static-play sole writer; `bip_head` mode 3/3, empty output log; 535 orientation components within 2 ULP |
| D4 — deferred Apply | **PASS** | Muscles 0.70, `bip_head` 1.40 on the existing graph; one `verification-pending`, then exactly one deferred `committed-verified` under the same operation id |
| D5 — Undo / Redo | **PASS** | one Undo entry covers the flex and the scale together |
| G7 — restoration | **RESTORED** | see below |

## Comparator adjudications and corrections (W2 only; production CPM unchanged)

- Native string conversion for SWIG `char *` names; array proxies not treated as elements (require `GetId`).
- T01 (Owner): preset coverage requires every bone with a transform control.
- T10: declared reopened path compared case-insensitively (SFM reports lower case).
- T10 (Owner): reopened-state comparisons tolerate transform-control orientation-quaternion components within 2
  float32 ULP (finite values only; every tolerated difference reported). Apply, Undo, Redo and unchanged stay exact.
- D3: orientation components paired in native (time) order before the 2-ULP limit (the identity-free comparison
  sorted lists and paired different keys); regression test added.

## Restoration

With SFM closed: published CPM `ccbed9d7…` reinstalled; M06 Qualification menu removed (no scripts added); preset
library restored to the pinned baseline (run-time library preserved in `evidence/restore/library_after_run`);
housekeeping files and bytecode restored. Post-run protected inventories equal the baselines:

| Location | Files | Inventory SHA-256 |
|---|---|---|
| `usermod/scripts` | 1,107 | `57ff4cd5ecf3ffcf54c9f37acf8d1395caa1f6f78d019df849fbf731709f8b19` |
| `usermod/cfg` | 59 | `fed6f8ae82cc509c95c0ac7bb590562e1e293effd2e0b11515b59c3ce32be3e1` |
| CPM preset library | 107 | `cd0e3fef3e20ce7a2aa0080e98693c5f95501aafe7ef80d8ecd10271090841ad` |
| SFM sessions folder | 986 | `4458fc74b8a2b05dfd43c471d7cae7f14c269e96e4d8c76121da0291ed400431` |

## Findings and limitations

- **F-T01-1 (nonblocking):** Body Save rewrites the shared `character.json` `display_name` to the saving instance's
  animation-set name (Krystal → krystal20202new; recurred in T11). No identity, model or preset-link field changed.
  Separate potential user-facing metadata issue; CPM not changed for it.
- **O-T10-1:** SFM save/reload moves some orientation-quaternion components by 1–2 float32 ULP. Recorded as SFM
  behaviour, not a CPM defect; no independent save/reload without CPM was performed.
- One machine, disposable fixtures. The T06 `AnalOpen` empty-log behaviour is recorded only; any further
  animation-compatibility behaviour is deferred.
- Public v1.0.0 (CPM `ccbed9d7…`, signed inventory, release assets) is unchanged; this correction is not released.
