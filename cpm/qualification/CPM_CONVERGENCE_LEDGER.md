# Ledger — SFM Character Tools
**Checkpoint:** 2026-10-26. Current status replaces the stale L-5/pre-release snapshot; historical detail remains in Git history. **Stop implementation.**

## Authority and revision
- **Authoritative repository:** `chadchan3d/sfm-character-tools`; owner-reported local project folder: `E:\SFM Animation Group Master\` (**local contents not accessible/UNVERIFIED here**). GitHub `master` immediately before this checkpoint: `eb73dad211da7552e23eb12bb4a75a1173274edf`.
- **Frozen Blueprint:** `cpm/qualification/R15_IMPLEMENTATION_BLUEPRINT.md`, Final R15 Implementation Blueprint dated **2026-09-30**, frozen from `bd169401…` with Clarifications A/B. This is the authoritative R15 architecture, **not** a substitute for the M-05 design. Blueprint unchanged.
- **Approved decision outside that Blueprint:** owner-approved **Astra M-05 Production Correction Design (2026-10-24)**, retained as an external review attachment, not integrated into the R15 Blueprint: narrowly admit coherent static mode-3 bone-scale graphs, preserve channel mode, and verify changed Apply once after commit on the ordinary event loop. No automatic postcommit Undo; fail closed. **Do not substitute mode-3→mode-1 conversion**: native experiments showed delayed physical evaluation in both modes.
- **UNAPPROVED proposals:** changes to flex import/capture/Apply rules; CPM Pose Library (F-01); skins/bodygroups (F-02); unrelated maintenance features. No additional Blueprint revision or release target approved for them.

## Current milestone and done criteria
**M-05 — OFFLINE CORRECTION ACCEPTED; NATIVE QUALIFICATION PENDING.** Done means the exact corrected CPM candidate passes the bounded real-SFM Krystal fixture: complete Body Save (head scale ≈1.13), changed mode-3 Apply with truthful deferred physical verification, stable evaluation, complete native Undo/Redo, no-op, and disposable save/reopen; then exact installation/session restoration. **Not yet done.**
- **Product baseline:** v1.0.0 already public on GitHub (published 2026-10-24), with Workshop distribution linked from README; L-6/release historical qualification is complete. The published ZIP SHA-256 is `1e128e1fa536f1b24c032299ecc19fd1cb53ba5645cb7ca58819b1e0792817ba`. Do not overwrite the signed release or its inventory during maintenance.

## Code and retained work
- **GitHub baseline:** pre-checkpoint `master` `eb73dad…`; the remote CPM source is *not* the uncommitted M-05 correction. Local `master` was reported at `0d12e070…` on 2026-10-24; its **current** HEAD/dirty status is **UNVERIFIED**.
- **Uncommitted local M-05 candidate (Claude/Astra reported, not mounted here):**
  - `cpm/app/SFM_Character_Preset_Manager.py` SHA-256 `6275f04acd7355abeb1ec032d990aa28140de0bfb2cfb6ce1490aef34592ddde`.
  - `cpm/convergence/tests/test_cpm_app_m05_static_scale.py` (new/untracked at last report) SHA-256 `8b3316eb32154c94841a0567173eea4507a124d6304f98bbff72526b10cf80c3`.
  - `cpm/convergence/tests/test_cpm_app_canonical_route.py` SHA-256 `febea0338996aba495136d568e9500b077cf7e6222efbf98420c46467b2417d7`.
  - Preserve these files and all uncommitted work. **No M-05 commit, installation, signing, or native qualification confirmed.**

## Verification and outstanding risks
- **Astra independent offline review:** corrected blockers CLOSED; **115/115 PASS** on Python 2.7.5 and 3.10.6; **24 paired outputs / 2,053 assertion rows**, no changed outcomes; **24 unchanged historical FAIL rows** (not 23). The manifest had 66 checked entries. These results apply **only to the exact local M-05 candidate above**, not published v1.0.0 or a real-SFM run.
- **Native M-05 unresolved:** one-shot zero-delay callback may precede SFM physical evaluation; real DME `usedefaultvalue`, log/layer identity reads, native Undo/Redo with mode 3 preserved, actual no-op and persistence remain unqualified. Stop on a failure; no retry/polling/delay hacks.
- **Separate flex-import incompatibility (UNRESOLVED):** in shot12, source `krystal20201` saved **PASS** (26 Body controls; 154 bone records; 1 existing scale control). Following animation export/import, recipient `krystal20202new` failed `Breastsize/mono` static-state validation before writing a preset. An earlier native read-only observation of another imported set showed source `0` vs key/evaluated/destination `0.4679802954`; another attempt failed `Muscles/mono`. This supports an import-related representation mismatch, **but cause is not proven**: no successful pre-import Save on that exact recipient, and no complete source/recipient channel comparison. Do not fold into M-05 or relax flex invariants without separate design/qualification.
- **Public reception:** owner-reported early SFMLab downloads and Steam subscriptions versus anti-AI comments/ratings are interest/sentiment observations, **not** evidence of software success or failure. No product defect is established by those comments.

## One next bounded action
**Run the already approved single native M-05 qualification** against a disposable Krystal fixture using exact candidate `6275f04a…`, with read-only pre/post integrity evidence, one Save→changed Apply→deferred check→Undo/Redo→no-op→save/reopen sequence, terminal PASS/FAIL per gate, and full cleanup/restoration. Do not modify implementation, original sessions, Normalizer, updater, signed artifacts, or the Blueprint. Stop and request adjudication if native evaluation fails.
