# F-01 M1 Stages A/B — integration record on the M-06 baseline

**Feature:** F-01 Pose Library M1, offline Stages A (pose core) and B (pose library), with the Astra P1 corrections
(P1-1 exact-time insertion, P1-2 strict evidence, P1-3 physical containment; Astra ruling PASS WITH BOUNDED
CORRECTIONS, findings closed by the P1 correction package). **Date:** 2026-11-02. **Scope:** offline only. Stages A/B
are not wired into `ProdWindow` and read no live scene. **Stage C (live integration) is not started.**

## Source pin

| Item | Identity |
|---|---|
| Base commit (master, M-06 integration) | `efe8984369eb0530a84ac5b9ce71fdffe9a7ece1` |
| Base CPM `cpm/app/SFM_Character_Preset_Manager.py` (M-06 W1, native-qualified) | `fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d` |
| Appended F-01 Stage A/B block (corrected; byte-identical to the P1 package's appended block) | `5a3d94f562b37f59…` |
| F-01 CPM = base CPM bytes followed by the F-01 block | `648c881cc0648b2f797aab2b5f8639920745d9906c5275ecb4d580aab7b0de2d` |

The F-01 block is append-only: the P1 package's corrected application `9a0fb4cb…` is the M-05 CPM `6275f04a…`
byte for byte followed by this block. It was rebased onto `fd853661…` without change; its 109 top-level names do not
collide with the base's 674.

**Retired pin:** the M-06 native campaign pinned the earlier F-01 worktree CPM `a0333366…` (M-05 base plus the
uncorrected block). The campaign is complete (G7 RESTORED), so that pin no longer applies.

## Selected-instance dependency closure (Addendum R2.1 §1.3)

The base commit contains the complete reviewed closure: `prod_selection_token` (UI token at selection),
`prod_resolve_instance` and the strict identity reads, `prod_instance_channels_clip`, `prod_context_token` and the
operation `context`, `prod_validate_context_token`, `prod_instance_pair_check`, and the window's selection plumbing. Its
outstanding M-06 native obligations passed in the M-06 campaign (`cpm/qualification/M06_NATIVE_QUALIFICATION_EVIDENCE.md`):
instance identity (P8, G3-b), reload invalidation (P3, G3-a) and peer isolation (T11). F-01 does not copy or fork it.

## P1 correction package identities (verified)

`F01_M1_AB_P1_CORRECTION/MANIFEST.sha256` verifies completely.

| File | Package (M-05 base) | Committed here |
|---|---|---|
| `cpm/app/SFM_Character_Preset_Manager.py` | `9a0fb4cb41582799…` | `648c881c…` (rebased, above) |
| `cpm/convergence/tests/test_cpm_app_f01_pose_core.py` | `e21272cfe25c83ca…` | same |
| `cpm/convergence/tests/test_cpm_app_f01_pose_library.py` | `028139bd856802ab…` | same |
| `cpm/convergence/tests/test_cpm_app_canonical_route.py` | `f74dec6b20a474e4…` | `aa310f57c0972fc3…` |
| `cpm/pose_profiles/cpm_pose_profiles_v1.json` (Stage A registry) | — | `87efaad9045e2a56…` |

The route harness is the M-06 harness plus exactly the package's two F-01 changes (the `F01_STAGEA_NEW_TOP` /
`F01_STAGEB_NEW_TOP` declarations and their union term), verified mechanically against the package.

## Verification on the rebased tree (Python 3.10.6 and SFM 2.7.5)

| Suite | Result |
|---|---|
| F-01 Stage A `test_cpm_app_f01_pose_core.py` | 252/252 both |
| F-01 Stage B `test_cpm_app_f01_pose_library.py` | 87/87 both |
| M-06 static play / W1 instance resolution / M-05 | 334/334, 179/179, 115/115 both |
| Clothing fit / operation context (publish, suite, compare) | 95/95, 108/108, 3/3 |
| Empty states | 15/15 (2.7.5) |
| F-01 W2 checkpoint `accepted/tests/test_f01w2.py` | 162/162 both |
| Astra P1 counterexamples (`repro_astra_p1.py`) | results identical to the package's `repro_corrected.json`: all 7 refused or detected by their intended check; no file written outside the library |

Unchanged historical rows, as on master: canonical-route `derivation.added_top_level_is_bounded` (only the two historical
undeclared names `PROD_EMPTY_STATE_GUIDANCE`, `prod_model_candidates`), authority-cleanup 4, r14 `normalizer_pinned`,
r15 `forbidden.unchanged.*`, the bounded-logging real-log-folder guard. The W1 checkpoint suite needs the private executed
`config.json` (not committed); its committed files are unchanged and verify against `SHA256SUMS.txt`.

## Next

Stage C (integration checkpoint preparation) needs its separate authorization.
