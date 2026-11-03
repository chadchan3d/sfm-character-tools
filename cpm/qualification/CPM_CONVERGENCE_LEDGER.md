# Ledger — SFM Character Tools
**Checkpoint:** 2026-11-02 (M-06 native qualification PASS; repository integration). Current status replaces the M-05 snapshot; historical detail remains in Git history. **Stop implementation.**

## Authority and revision
- **Authoritative repository:** `chadchan3d/sfm-character-tools`. GitHub `master` immediately before this checkpoint: `ea5e7c49ce80fa5a557afc660932eab7f9587687` (M-05 closed; M-05 integration `e5197e2b…`).
- **Frozen Blueprint:** `cpm/qualification/R15_IMPLEMENTATION_BLUEPRINT.md`, Final R15 Implementation Blueprint dated **2026-09-30**, frozen from `bd169401…` with Clarifications A/B. Authoritative R15 architecture; not a substitute for the M-05/M-06 designs. Blueprint unchanged.
- **Approved decisions outside that Blueprint:** owner-approved **Astra M-05 Production Correction Design (2026-10-24)**; **Astra M-06 Production Correction Design** (admit the imported static flex class `STATIC_PLAY_ONE_KEY_ZERO` with complete writer discovery; fail closed otherwise); **Astra M-06/M-05 Integration Correction Design (2026-10-29)** (W1 selected-instance resolution: operations carry the selected instance and context-free resolution no longer retargets). Retained as external review attachments. **Do not substitute mode-3→mode-1 conversion.**
- **UNAPPROVED proposals:** further flex import/capture/Apply rules (the `AnalOpen` empty-log question is deferred); skins/bodygroups (F-02); unrelated maintenance features. F-01 Pose Library continues on `feature/f01-pose-library`; Stage C not authorized.

## Current milestone and done criteria
**M-06 — native qualification PASS; repository integration complete (2026-11-02).** The exact W1 candidate `fd853661…` passed the bounded M-06 native campaign: G3–G6 PASS (P1–P9, T01–T12, D1–D5) and G7 RESTORED with `integrity post` PASS. Evidence: `cpm/qualification/M06_NATIVE_QUALIFICATION_EVIDENCE.md`. Awaiting designer adjudication.
- **Done criteria met:** Body Save and Update (154 control-backed bones), no-op and changed Apply, imported static-play flex Apply (`Muscles`, empty-log `AnalOpen`), scale-graph creation and existing mode-3 graph Apply, injected abort recovery, native Undo/Redo (one entry for flex and scale), peer isolation, save/reopen persistence and the deferred-verification path after restart — followed by restoration of the published installation.
- **M-05 — CLOSED (2026-10-26, designer adjudication)**; its limitations remain in force.
- **Product baseline:** v1.0.0 public (2026-10-24); published ZIP `1e128e1fa536f1b24c032299ecc19fd1cb53ba5645cb7ca58819b1e0792817ba`. **Public v1.0.0 is unchanged** (CPM `ccbed9d7…`, signed inventory, release assets); M-05 and M-06 are committed but not released. Do not overwrite the signed release or its inventory during maintenance.

## Code and retained work
- **Committed M-06 correction:**
  - `cpm/app/SFM_Character_Preset_Manager.py` SHA-256 `fd853661fe72464d8ff867d73750e539a66d3d6266110051dbce922c75c25c3d`.
  - `cpm/convergence/tests/test_cpm_app_m06_static_play_flex.py` `e0628248…`; `test_cpm_app_m06_instance_resolution.py` `7f32563c…`; updated `test_cpm_app_canonical_route.py` `575139e5…`, `test_cpm_app_m05_static_scale.py` `c9702123…`, `test_cpm_app_bounded_logging.py` `baee9e34…`, `test_cpm_app_empty_states.py` `ca8c3442…`.
  - `real_sfm_qualification/m06_w2_qualification/` — W2 native qualification instruments and tools (20 files, accepted sums `2cb3e4f9…`).
  - `cpm/qualification/M06_NATIVE_QUALIFICATION_EVIDENCE.md` and this Ledger.
- **Installed product:** restored to published CPM `ccbed9d7…`; updater, signed inventory and Workshop installer state unchanged.
- **Raw evidence (not committed):** the owner's local archive `m06-native-qualification-4/` (observations, CPM native logs, disposable scenes, pre/post integrity, restoration report and the run-time preset library). M-05 archive `m05-native-qualification/` retained.
- Historical audit ZIPs, reports and other untracked local work remain uncommitted and preserved.

## Verification and outstanding risks
- **Offline:** M-06 suite 334/334, W1 suite 179/179, M-05 suite 115/115 (Python 2.7.5 and 3.10.6); clothing-fit 95/95 and operation-context 108/108 (publish/suite/compare PASS); empty-states 15/15 (2.7.5); W2 suite 127/127 (1 skipped). Unchanged historical FAIL rows only: canonical-route `derivation.added_top_level_is_bounded` (`PROD_EMPTY_STATE_GUIDANCE`, `prod_model_candidates`, both present and unlisted at `ea5e7c4`); authority-cleanup 4, r14 `normalizer_pinned`, r15 four `forbidden.unchanged.*` (same at `ea5e7c4`); bounded-logging real-log-folder guard (environmental: the folder exists after native use and was unchanged by the run).
- **Native qualification (2026-10-31 / 2026-11-02), candidate `fd853661…`:** all checkpoints PASS — see the evidence manifest. Comparator corrections were W2-only (native strings, array proxies, control-backed preset coverage, path case, the Owner-approved 2-ULP reopen tolerance and its native-order pairing); production CPM unchanged.
- **Restoration:** four protected inventories equal their baselines (scripts `57ff4cd5…`, `usermod/cfg` `fed6f8ae…`, preset library `cd0e3fef…`, sessions `4458fc74…`).
- **Findings:** **F-T01-1 (nonblocking):** Body Save rewrites the shared `character.json` `display_name` to the saving instance's animation-set name; CPM not changed for it. **O-T10-1:** SFM save/reload moves some orientation quaternions by 1–2 float32 ULP (SFM behaviour; no independent save/reload without CPM was performed).
- **Qualification limitations:** one machine, disposable fixtures. Zero-delay callback ordering is not universally guaranteed by Qt; a check that runs before evaluation ends committed-unverified by design. W1 does not log a live signature at selection (G3-b note). SFM's registry recent-documents list was not restored.
- **Public reception:** owner-reported downloads/subscriptions versus anti-AI comments are sentiment observations, not evidence of software success or failure.

## One next bounded action
**Designer adjudication of M-06; reconcile F-01 onto the integrated M-06 baseline.** No installer assembly, signing, release publication, new native testing, further animation-compatibility behaviour or F-01 Stage C implementation is authorized.
