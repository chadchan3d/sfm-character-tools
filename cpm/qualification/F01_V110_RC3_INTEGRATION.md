# F-01 v1.1.0 RC3: Fox and Tails enabled for normal installations (2026-11-19)

**Authority:** the Owner/Designer's "F-01 v1.1.0 — RC3 Authorization": prepare RC3 with Fox and Tails enabled; RC2
accepted as the release baseline but not published; RC2 remains the fallback.

**Status: RC3 locally verified (unsigned).** The native smoke test is prepared but not run. Nothing is installed: the
published v1.0.0 CPM `ccbed9d7…` is in place, with no registries. No signing, promotion, merge, push, Workshop
publication or release.

## 1. The product change (CPM `001377f9…` → `026a65cd4447233093a3429b60a7adf481d9a92060613bae15ef59bf1076c9ba`)

Diff: `F01_V110_RC3_INTEGRATION.diff` (7 lines added, 4 removed; one constant, one expression, one comment).

| Change | Why |
|---|---|
| `PROD_BODY_RIG_STATUS` `experimental` → `qualified` | `prod_body_rig_usable` admits the structural adapter in production only when it is `qualified`. Revisions 1 (Fox) and 2 (Tails' JIGGLE leaves) become usable in production exactly as in the qualification build |
| The structural authorization's mapping carries an `evidence` reference while `qualified` (`None` while experimental) | CPM's registry rule pairs `qualified` with non-empty evidence. The reference names the two native qualifications closed by adjudication (`F01_STAGE1_RECOVERY_CHECK_RESULTS.md`, `F01_STAGE2_TAILS_NATIVE_RESULTS.md`) |
| The constant's comment | Describes the new status |

**Nothing else changed:**
- no registry change;
- no record format, admission rule, classifier, planner, transaction, P2–P7 or recovery change.

The CPM's history since RC2 (`7aa0fc4e…`, commit `ede599f`) is only the five Stage 1/2 commits (`fc534c3`,
`72e12c6`, `de57360`, `25ba936`, `208a977`) and this change. No product file outside the CPM changed.

## 2. Regression (Python 2.7.5 and 3.10.6)

Every CPM convergence suite, including the structural rig and JIGGLE leaf suites, was run sequentially on two trees:
- the baseline, HEAD `30a32bf`, in an LF worktree outside the system temp folder;
- RC3, this repository's working tree.

**Every exit code and failing-check set is identical, except the intended production-behaviour checks below.**

| Suite | Baseline | RC3 |
|---|---|---|
| `test_cpm_app_f01_structural_rig` (both) | 298/298 | **307/307** |
| `test_cpm_app_f01_jiggle_leaf` (both) | 139/139 | **142/142** |
| `test_cpm_app_f01_pose_page` (2.7.5) | 131/131 | **133/133** |
| body 261, helper 78, pose core 255, integration 218, library 87, live 109, scoped 494, M-06 334 and 179, ordering trial 75, scoped page 19, empty states 15, operation context 108, clothing fit 95, compat projection 196 | PASS | identical |

**Test expectations corrected (they asserted RC2's production refusal, which RC3 intentionally changes):**
- **Structural rig, R section:**
  - new: production authorizes a structural Save and Apply, with status `qualified` and evidence;
  - new: the production probe admits as in qualification, without writing;
  - new: a production Apply verifies `committed-verified`.
  - RC2's three refusal checks are kept, run with the status temporarily `experimental`, plus one check that the
    experimental authorization carries no evidence.
- **Structural rig, E section:**
  - new: the production Save dialog offers Full body through the structural route and saves;
  - new: availability is `available` in production, and other models and unknown revisions stay refused in both
    modes;
  - new: the production window Apply verifies.
  - RC2's refusals (dialog, availability, Apply) are kept against the experimental status.
- **JIGGLE leaf, H section:**
  - new: production offers Tails' Full body with exactly the seven simulated leaves, the same probe as qualification;
  - new: production authorizes the Apply as qualified with evidence, and the authorization writes nothing.
  - RC2's three refusal checks are kept against the experimental status.
- **Poses page, S4:**
  - new: in production the structural pose enables Apply Pose with no note;
  - new: another model and an unknown revision stay disabled.
  - RC2's disabled-with-note check is kept against the experimental status.

Each experimental block restores the status it found.

**Teeth:**
- Against a copy of RC3's CPM with the status set back to `experimental`, the new checks fail:
  - structural rig 292/300: R's three authorization and probe checks (the R section then stops at the production
    Apply);
  - structural rig E: the production dialog, availability and Apply checks. The other-models check also fails there,
    because experimental production answers `not-qualified` before the model test;
  - JIGGLE leaf H: both new checks (140/142);
  - Poses page S4: the new check (132/133), run in the baseline worktree.
- The kept RC2 checks pass in both builds.

**Canonical route allow-list:**
- The test now lists the 47 top-level names Stage 1 and 2 added since RC2's CPM (`F01_STRUCTURAL_NEW_TOP`; none
  removed).
- `derivation.added_top_level_is_bounded` still fails, now only on the eleven names already unlisted at RC2
  (`PROD_EMPTY_STATE_GUIDANCE`, `PROD_POSE_PICKER_ROWS`, `PROD_POSE_PICKER_SCREEN_SHARE`, `prod_model_candidates`,
  five `prod_pose_info_*`, `prod_pose_picker_height`, `prod_scope_selected_parts_unavailable`).
- Not changed further: the eleven were never audited into the list, and listing them is not needed to assess RC3.

**Pre-existing, unchanged:**
- M-05 A9 (115/116);
- r14 `normalizer_pinned`;
- r15 `forbidden.unchanged.*`;
- the authority-adapter and convergence-gates Normalizer pins;
- authority cleanup 42/46;
- bounded logging's real-log-folder guard;
- `logging_cleanup` and `ui_polish_pass` need an explicit `--reference`;
- the PySide suites run on 2.7.5 only.

**Environmental:**
- **CRLF copy:** r15's `forbidden.unchanged.cpm/convergence/cpm_compat_v1_projection.py` fails in this repository's
  checkout only. Its working copy of that file has CRLF line endings, which Git does not report as a change. The LF
  worktree passes, and the Stage 2 runs showed the same.
- **Temp worktree:** a first baseline worktree inside the system temp folder broke the page, empty-state,
  bounded-logging and r15 child fixtures, which remap temp paths. It was discarded, and the baseline above was rerun
  outside temp.

## 3. Qualification kits

Every kit test was run on both trees (Python 3.10.6, and 2.7.5 where the test supports it).

**Identical to the baseline except:**
- **Stage 2 Tails kit** (`test_s2t.py`): 76/79 (3.10.6) and 22/25 (2.7.5). `candidate.is_the_stage2_cpm` and two
  template checks pin the Stage 2 CPM `001377f9…`, which RC3 replaces. This is the pattern already recorded for the
  recovery kit (59/61) and the RC1S kit (`P.installed_build_is_the_rc1_cpm`). The kit, its verdict and its evidence
  are not edited.
- **New RC3 smoke kit:** 35/35.

The Fox kit stays 49/49.

## 4. Package (`release/v1.1.0-rc3/`)

| Item | Value |
|---|---|
| Spec | `SOFTWARE_SPEC.json` `6c3d9503…`: RC2's spec with the RC3 CPM identity (1,534,088 B) and RC3 text; 33 files |
| Tool | `rc3_tool.py` `46f11cef…`: RC1's `rc_tool.py` unchanged, with the RC3 spec and package name; `rc.template.json` `f6f921c9…` |
| Unsigned inventory | `bda55d9e8657b576192b3a0b1e4c0f41ca9207d4531c39f707fccd4b8c7ff01d` |
| Unsigned package (outside Git) | `E:\SFM_U0B_Scratch\f01-v110-rc3\package\SFM.Character.Tools.v1.1.0-rc3-UNSIGNED.zip` `5ca540720d9313dcbbe26073a4512631ace8a6f21e6ad9964acc336917254c6a` (1007 entries) |
| Reproducibility | An independent rebuild in `f01-v110-rc3-repro` is byte-identical |
| Readiness | `rc3_tool.py verify`: **RC VERIFY PASS** (`RC_VERIFY.json` `2dc60b12…`): package, updater (parse, profile, files; v1.1.0), version, installer (`prepare` with placeholder signature) and rollback to v1.0.0 |
| Against RC2's package | the same 1007 names; only the CPM and the inventory differ (both registries byte-identical) |

## 5. Registry behaviour and the qualified routes (offline)

The smoke kit's `build` staged the RC3 production files from the package, and its production-mode check
(`rc3s_modes`, on the CPM's own code) passed. `IDENTITIES.json` is `c0c91794…`.

| Check | Result |
|---|---|
| RC1's checks | production mode; generic v3 usable as in qualification; carried rule disabled; Krystal v2 Full body and left arm qualified; only the experimental right arm left out. All PASS |
| `structural_status` | `PROD_BODY_RIG_STATUS` is `qualified`: PASS |
| `structural_production` | revisions 1 and 2 usable in production and qualification alike, so no qualification-only switch is needed: PASS |
| `structural_bounded` | revisions 0 and 3, another rule and an unknown mode stay unusable: PASS |

The existing qualified routes are unchanged in the regression above: Krystal v2, generic v3 with H1 helpers, Selected
parts, Body Presets, M-05 and M-06.

## 6. Native smoke test (prepared, not run): `real_sfm_qualification/f01_v110_rc3_smoke/`

| File | SHA-256 |
|---|---|
| `PROCEDURE.md` | `2c3cdf1a…` |
| `tools/rc3s_tool.py` | `1de59ea2…` |
| `tools/rc3s_modes.py` | `6927bf04…` |
| `tools/rc3s_analyze.py` | `9e3255a6…` |
| `rc3s.template.json` | `b2e4fd6d…` |
| `owner_smoke_record.template.md` | `943f0ddf…` |
| `tests/test_rc3s.py` | `5b28c653…` |

**The installation:**
- the exact RC3 production CPM and registries, from the package;
- no observer or capture script in SFM;
- reused, unchanged: K2's pre, the S3 install/collect-logs/restore and UA-1's library backup and cleanup.

**One SFM process** on a verified copy of the R2 fixture (`RC3_SESSION.dmx`, never saved):
1. Create two Foxes and two Tails, and rig all four with `rig_biped_simple`.
2. Pose Fox S and Tails S. Move and pose Fox D and Tails D differently.
3. Fox: Save New Full body `RC3 Fox`, Pose Info, Apply to Fox D, inspect, Undo, Redo.
4. Tails: the same with `RC3 Tails`.
5. Exit without saving.

Not repeated: the qualification campaigns, Abort tests, restart and skeletal captures.

**Automated gates** (`RC3S_VERDICT`, from CPM's own log and the saved records):

| Gate | Requires |
|---|---|
| EVIDENCE | The RC3 build and its production-mode check; one CPM log, written by the RC3 CPM; exact restoration; only the two poses (and CPM's own character files) in the library |
| FOX | Save verified and logged as a structural admission; record version 2, adapter revision 1, Fox model; Apply `committed-verified` |
| TAILS | The same, with the seven JIGGLE leaves admitted and described without values; adapter revision 2 |
| TARGET | Each Apply on another instance of the same model, never the source or the session's original Fox or Tails |
| DISPLAY | Pose Info for both records |
| CLEAN | No refusal, failure, recovery or unverified outcome |

**The Owner's record** covers posture, placement, deformation, the peers, and the Undo and Redo labels. If the Edit
menu names another entry, the Owner records it and chooses nothing.

**Kit tests** (35/35):
- production-mode checks on the real RC3 CPM, failing for the RC2 experimental gate, a qualification build, a missing
  revision 2 and an unbounded gate;
- 23 analyzer variants;
- the pins.

**Run folder prepared offline:** `E:\SFM_U0B_Scratch\f01-v110-rc3-smoke-r1`, with `rc3s.json` and `staged/`. `check`
reports `"installation": "published"`. Not done: `pre`, `install` or any SFM run.

**Release gate:**
- If the automated verdict is AUTOMATED SMOKE PASS and the Owner's record is accepted, RC3 is recommended for final
  release preparation.
- If the normal-install test shows a substantive problem, it is reported before any further testing or architecture
  change, and RC2 remains the fallback.

## 7. Not done

- No native installation, `pre`, seeding or SFM run.
- No signing, production promotion, merge, push, Workshop publication or release.
- Historical kits, verdicts and evidence are unchanged.
