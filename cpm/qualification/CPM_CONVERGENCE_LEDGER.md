# Ledger — SFM Character Tools
**Checkpoint:** 2026-10-26 (M-05 closed). Current status replaces the stale L-5/pre-release snapshot; historical detail remains in Git history. **Stop implementation.**

## Authority and revision
- **Authoritative repository:** `chadchan3d/sfm-character-tools`. GitHub `master` immediately before this checkpoint: `e5197e2bc31fc5d9771f5549283fc8cab017458c` (M-05 integration; preceded by `ff220d3…`, to which local `master` was fast-forwarded without reset, rebase or force).
- **Frozen Blueprint:** `cpm/qualification/R15_IMPLEMENTATION_BLUEPRINT.md`, Final R15 Implementation Blueprint dated **2026-09-30**, frozen from `bd169401…` with Clarifications A/B. This is the authoritative R15 architecture, **not** a substitute for the M-05 design. Blueprint unchanged.
- **Approved decision outside that Blueprint:** owner-approved **Astra M-05 Production Correction Design (2026-10-24)**, retained as an external review attachment, not integrated into the R15 Blueprint: narrowly admit coherent static mode-3 bone-scale graphs, preserve channel mode, and verify changed Apply once after commit on the ordinary event loop. No automatic postcommit Undo; fail closed. **Do not substitute mode-3→mode-1 conversion**: native experiments showed delayed physical evaluation in both modes.
- **UNAPPROVED proposals:** changes to flex import/capture/Apply rules; CPM Pose Library (F-01); skins/bodygroups (F-02); unrelated maintenance features. No additional Blueprint revision or release target approved for them.

## Current milestone and done criteria
**M-05 — CLOSED (2026-10-26, designer adjudication).** The designer verified commit `e5197e2bc31fc5d9771f5549283fc8cab017458c`, independently confirmed the three committed source/test SHA-256 values, and accepted the seven native qualification gates and the exact restoration evidence. Native qualification PASS; repository integration complete. The limitations below remain in force.
- **Done criteria met (2026-10-26):** the exact candidate passed the bounded real-SFM Krystal fixture — complete Body Save (head ≈1.13), changed mode-3 Apply with truthful deferred physical verification, stable evaluation, complete native Undo/Redo, true no-op, and disposable save/reopen — followed by exact installation/session restoration. Evidence: `cpm/qualification/M05_NATIVE_QUALIFICATION_EVIDENCE.md`.
- **Product baseline:** v1.0.0 already public on GitHub (published 2026-10-24), with Workshop distribution linked from README; L-6/release historical qualification is complete. The published ZIP SHA-256 is `1e128e1fa536f1b24c032299ecc19fd1cb53ba5645cb7ca58819b1e0792817ba`. **Public v1.0.0 is unchanged** (CPM `ccbed9d7…`, signed inventory, release assets); the M-05 correction is committed but not released. Do not overwrite the signed release or its inventory during maintenance.

## Code and retained work
- **Committed M-05 correction (commit `e5197e2b…`):**
  - `cpm/app/SFM_Character_Preset_Manager.py` SHA-256 `6275f04acd7355abeb1ec032d990aa28140de0bfb2cfb6ce1490aef34592ddde`.
  - `cpm/convergence/tests/test_cpm_app_m05_static_scale.py` SHA-256 `8b3316eb32154c94841a0567173eea4507a124d6304f98bbff72526b10cf80c3`.
  - `cpm/convergence/tests/test_cpm_app_canonical_route.py` SHA-256 `febea0338996aba495136d568e9500b077cf7e6222efbf98420c46467b2417d7`.
  - `cpm/qualification/M05_NATIVE_QUALIFICATION_EVIDENCE.md` (evidence manifest) and this Ledger.
- **Installed product:** the live installation was restored to published CPM `ccbed9d7…` after qualification; installed CPM, updater, signed inventory and Workshop installer state unchanged.
- **Raw evidence (not committed):** the owner's local qualification archive `m05-native-qualification/` (observations 001–009, CPM native log, saved/reopened scene, offline inspection, pre/post integrity and restoration reports), plus the offline re-review package for `6275f04a…`. It holds local scenes, preset-library copies and workstation-path logs.
- Historical audit ZIPs, reports and other untracked local work remain uncommitted and preserved.

## Verification and outstanding risks
- **Offline (Astra independent review):** corrected blockers CLOSED; **115/115 PASS** on Python 2.7.5 and 3.10.6; **24 paired outputs / 2,053 assertion rows**, no changed outcomes; **24 unchanged historical FAIL rows**.
- **Native qualification (2026-10-26), candidate `6275f04a…`, fixture `fa9a0a46…` (shot10 / `Krystal`), observer `ffae20a6…`, target preset `d1c94` (`bip_head` 1.33):**
  - **A** initial static mode-3 state, bone 1.13 — PASS. **B** Body Save: 154 bones, head 1.13, `verified`, no scene change — PASS.
  - **C** changed Apply — PASS: output mode 3 preserved (same log/layer identities, still empty); `verification-pending` → one deferred check `committed-verified` 51 ms after commit → success only then; bone 1.33005; only `bip_head_scale` and five differing flexes changed.
  - **D** away/back stable — PASS. **E** one Ctrl+Z restores the exact baseline digest; Ctrl+Y reproduces the exact post-Apply state with mode 3 kept — PASS. **F** true no-op, no Undo entry, no deferred work — PASS. **G** saved/reopened copy `544946ce…` keeps mode 3/3 and 1.33005, natively and offline — PASS.
  - **Restoration exact:** all four protected inventories equal their pre-run baselines (scripts `57ff4cd5…`, `usermod/cfg` `fed6f8ae…`, preset library `cd0e3fef…`, sessions `4458fc74…`); original sessions `3af2ad54…` and the fixture unchanged.
- **Qualification limitations:** one run on one fixture and one machine. Zero-delay callback ordering is **not universally guaranteed** by Qt; a check that runs before evaluation ends committed-unverified by design. **Native abort-recovery was not separately tested** (offline only). SFM's registry recent-documents list was not restored.
- **Separate flex-import incompatibility (UNRESOLVED):** in shot12, source `krystal20201` saved **PASS** (26 Body controls; 154 bone records; 1 existing scale control). Following animation export/import, recipient `krystal20202new` failed `Breastsize/mono` static-state validation before writing a preset. An earlier native read-only observation of another imported set showed source `0` vs key/evaluated/destination `0.4679802954`; another attempt failed `Muscles/mono`. This supports an import-related representation mismatch, **but cause is not proven**: no successful pre-import Save on that exact recipient, and no complete source/recipient channel comparison. Not part of M-05; do not relax flex invariants without separate design/qualification.
- **Public reception:** owner-reported early SFMLab downloads and Steam subscriptions versus anti-AI comments/ratings are interest/sentiment observations, **not** evidence of software success or failure. No product defect is established by those comments.

## One next bounded action
**Await the designer's selection of the next milestone.** M-05 is closed. No installer assembly, signing, release publication, new native testing or animation-import implementation is authorized until then.
