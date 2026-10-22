# Ledger

## Coder gate
Before editing, compare the assignment with the Blueprint and this Ledger.
Verify the current code state and relevant claims.
If the assignment assumes unfinished work is complete, contradicts the
Blueprint, or expands scope, report the conflict before dependent edits.
Otherwise proceed with the assigned milestone.

## Current milestone
**CPM Quick Launch (optional component) — QL-2 PASS in real SFM, owner-accepted within the tested scope
(2026-10-22).** Record: `cpm/quick_launch/README.md`. It is separate from the L-series and the software inventory, and
QL-3 is not started.
- **Sources:**
  - bootstrap `23e3a8813057642400b7e06e0b55e13c89f47b684779d907740905a5e28e4070`;
  - controller `4558d296505416591c79d08ecc9aa2fcaa0710003dbaaad94422e7654229f56f`;
  - tests `8b1195f24f5f1ac84d109d5af5f97f11d3b6386c563188772607dba37174888d`.
- **Appearance:** an original framed 36×32 bold "CPM" icon (`fb3691d8…`), embedded as a standard `QIcon`; fixed
  36 px width. No runtime painting or stylesheet.
- **Offline:** 233/233 under SFM Python 2.7.5 + PySide 1.2; static 32/32 under 3.10.
- **Real SFM:** startup, launch, repeated use, editor close and reopen, resizing, floating and docking, and Extended
  ASE coexistence all passed. The final check showed the icon at `[194, 1, 36, 32]`, 5 px clearance, one owned
  button, polling stopped, and CPM opening normally.
- **Installed (kept):** the bootstrap and controller, at the hashes above. The temporary QL-2 probe has been
  removed. Extended ASE settings and Autoinit configuration are unchanged.
- **Intermittent and unattributed (no correction):**
  - one blank dock pane after re-docking;
  - one floating editor without CPM.

  Neither recurred in later repeated floating and docking.

**v1 Release Baseline Amendment — Normalizer integration, corrected Candidate C Master promotion and Phase F
post-governor simplification: OFFLINE-COMPLETE and REAL-SFM QUALIFIED (bounded; Astra's final adjudication
accepted, 2026-10-22); repository checkpoint committed.** Amendment §6 items 2 and 5 are done; see "Real-SFM
qualification of `6b5d2941…` with corrected Candidate C" below. Items 3 (changed inventory and packaging) and 4
(L-6) remain.
The owner approved two changed first-release identities (record:
`updater_qualification/design/V1_RELEASE_BASELINE_AMENDMENT.md`, `a33d8b3b…`):
- **Decision A:** the Normalizer.
  - **Current:** `6b5d294116765aa1941e0f98394b4b6e35ad0acd2f80c90aba418b13c9b6130d` (496,210 B), the amendment §8
    Phase F simplification. **Offline-verified; real-SFM qualified (bounded) on 2026-10-22.**
  - **Historical:** `25a5e3cd2ccf62dad00df7122d5f1b1d62aea63a2069459993acc3e44feaa343` (496,624 B), the earlier
    real-SFM-qualified build. The "Accepted Normalizer qualifications" below were recorded on it.
- **Decision B, amended by option (b):** the corrected Candidate C.
  - **Master:** `1d855cd34b90a2e6254d97eb4c6ac4b08ccc64d994b8e6a754ddac8466b155ec`.
  - **Sidecar:** `3791677522119a6ca45c1092743041dc07014cfa1fd0891526db995bcf526a16`.
  - **Manifest:** `6c7568063a69de2a22c05f55df066db369f3340e68d0208f9f36a4c017c3c7ae`.
  - **Historical:** original Candidate C (`00df6304…` / `43572fd2…` / `c646f1da…`) is the identity used by every
    real-SFM qualification before 2026-10-22. The corrected identities were real-SFM qualified on 2026-10-22.

G1 and the Normalizer `1f4ec5a2…` remain historical qualification and regression references. This is a narrow
exception to the L card §1 frozen-Normalizer scope; R2, the L card, the Contract Amendment and R15 are unchanged.

**Repository integration (committed in the repository checkpoint):**
- `audit_external_runtime/Rebuild_Control_Groups_Normalizer.py` is now `6b5d2941…` (previously `25a5e3cd…`).
- **Phase F post-governor simplification (Astra's final revised adjudication, owner-approved, 2026-10-21; amendment
  §8):**
  - **Removed:** the process-lifetime Selected/All restriction. Every sequence of successful runs is allowed.
  - **Kept:** the canonical shot-identity re-resolution, the governor (112 / 24 MiB at all three boundaries,
    unchanged), the PRE, native, authority and transaction protections, and the active-run lock.
  - **Restart required only after a measured low-memory STOP or an unverified post-mutation or cleanup outcome.**
    This is recorded on the main window and in the process and survives menu re-execution; a clean UNKNOWN or an
    ordinary refusal records nothing.
  - **Post-mutation abort ruling (Astra, final; owner-approved 2026-10-22):** the condition `(not success and
    mutation_started)` is retained unchanged, with no additional recovery machinery. A generic abort after a native
    Rebuild attempt requires a restart because complete recovery cannot be verified: the transaction has no rollback
    and the abort path doesn't re-verify the session. It does not mean corruption was established. A verified native
    fallback and the resource-stop closures are unaffected. The user-facing wording claims neither corruption nor low
    memory. No new testing; the accepted offline evidence stands.
  - **Fail closed:** lookups and records fail closed. A failed active-run lookup is no longer "no active run".
  - **Wording:** the UNKNOWN wording is the approved initial sentence plus retry guidance with no restart demanded.
  - **Offline:**

    | Suite | Result |
    |---|---|
    | Focused Phase F | 21/21 |
    | Resource stop | 69/69 |
    | UI and log | 20/20 |
    | Floors | 35/35 |
    | Retention | 19/19 |
    | Diagnostics | 74/74 |
    | PRE regression | identical |

    Private evidence: the manifest of the Phase F work folder (see the amendment).
  - **Real SFM:** qualified (bounded) on 2026-10-22; see below.
- `updater/release_tools/character_tools_software_v1.json` pins the new hash and length; its `qualification` note
  records the amendment. All 31 spec sources match their pins. Roles, profile `2bbd93d0…`, the inventory verifier
  and the updater package are unchanged.
- **Consumer contract re-verified by content against `1f4ec5a2…`:** the menu-folder locator is byte-identical; the
  runtime API and build equal the profile's Normalizer contract; the authority imports and interfaces are identical.
- **Master: corrected Candidate C `1d855cd3…` is PROMOTED into `sfm_defaultanimationgroups.txt`** (previously G1
  `ac45e5c1…`, kept in Git history and backed up).
  - **Provenance:** G1 → Candidate B `e2c0f117…` → original Candidate C `00df6304…` → corrected Candidate C.
    - **Candidate B:** the documented data-v1.0.0 replacement: header, 14 additions, 15 corrections, 12 new
      `groupColor`s and the Attachments colour, and side-ordering of 14,956 controls.
    - **Original C:** B plus exactly the four rig-side group renames.
  - **Phase 1 approved (2026-10-21);** the owner acknowledged the full Candidate B scope.
  - **Why a correction was needed:** the first Phase 2 stopped before replacement. In 170 controls, original C had
    one more leading tab than G1 and than structural depth, which violates the CLAUDE.md indentation rule (§5, §18).
    Candidate B's side-ordering step introduced it: Hair 78, Clothing 48, Sexual Bones 25, Face/Ears 8, Wings 4,
    Other 4, Tail 2, Face/Lower Face 1 (private evidence `candidate_c_indentation_finding.tsv` `deca31e1…`).
  - **Correction (owner option (b), 2026-10-21):** exactly one leading tab removed from each of the 170 lines;
    nothing else changed. The same step had also brought 170 of G1's 11,001 pre-existing over-indented lines to
    their depth. That is approved Candidate B content and is left unchanged.
  - **Equivalence and validation (19/19 PASS):**
    - **The edit:** exactly 170 indentation-only lines.
    - **Content:** identical groups, occurrences and fold families.
    - **Indentation:** no deviation beyond G1's preserved ones.
    - **Validator:** `tools/validate_master.py` PASS.
    - **Compiler:** the pinned compiler (`candidate.compile_real`, 9 pins) still reproduces original C's
      `43572fd2…` / `c646f1da…`.
    - **New authority:** sidecar `37916775…` and manifest `6c756806…`, read back from disk, pass reader parity,
      FINAL R3-A2B admission and the manifest binding.
    - **Equivalence:** exhaustive cross-parity both ways. The sidecars are equal in length with byte-identical
      bodies; only the header's source SHA-256 and the header digest differ.
  - **Promotion (CLAUDE.md procedure, 28/28 PASS):**
    - the canonical Master was asserted to be G1;
    - a temporary candidate was validated;
    - the group hierarchy equals G1's except the four renames;
    - all G1 controls are present, plus the 14 additions;
    - colours and indentation match the rules;
    - G1 was backed up, the file atomically replaced, then re-opened and re-validated;
    - compiled from the repository copy: `37916775…` / `6c756806…`.
  - **Real SFM:** the corrected identities were acquired by both the Normalizer and CPM in real SFM on 2026-10-22;
    see below.

**Accepted Normalizer qualifications on `25a5e3cd…` (historical; private evidence, local only; these real-SFM runs
used original Candidate C `00df6304…`):**
- **Four-name rig sides and PRE bridge:** real-SFM PASS (`RESULT.md` `742ac9fd…`).
- **PRE admission:** qualified. Strict membership reads `0e4c982e…`, with the real-SFM legacy `shot228` PASS
  (`QUALIFICATION_RESULT.md` `602d4881…`).
- **Production resource floors (Astra, 2026-10-21):** 112 MiB free VAS (117,440,512 B) and 24 MiB largest
  contiguous region (25,165,824 B), the same at command preparation, target preparation and native entry.
  - **Comparison:** at or below either floor gives STOP; an incomplete census gives UNKNOWN (fail closed).
  - **Evidence:** the Astra evidence package `45742be9…`, and the external memory measurement
    (`MEASUREMENT_RESULT.md` `0ffb7851…`).
- **Safe stop, save, restart and Selected Shot(s) continuation:** qualified in real SFM (`QUALIFICATION_RESULT.md`
  `7dc437a9…`).
- **Final integrated resource-stop qualification, real SFM, 2026-10-21: 9/9 PASS.**
  - **Build:** the qualification-only derivative `5c2520d9…` of `25a5e3cd…`, with an injected native-entry stop at
    `shot2/mia1` and the production floors kept.
  - **Results:**
    - the real readings were above the floors;
    - the stopped target never entered native Rebuild;
    - closure and isolation PASS;
    - the real Qt dialog showed "1 of 4 shots completed / Stopped at: shot2 (unfinished) / 3 shots remaining,
      including shot2" with **Close only**;
    - the report was kept as `Normalizer - Resource Stop - <date-time>.log`, classified `RESOURCE_STOP`;
    - the verified verdict was written after the six teardown checks;
    - the installation was restored exactly.
  - **Evidence:** `QUALIFICATION_RESULT.md` `bb997d50…`, the report `27ef0bed…`, the dialog screenshot `9ca1572c…`,
    and the manifest `6f96b865…`.
- **Report classification:**
  - a verified protective stop with no normalization problem is kept as `Normalizer - Resource Stop - …`, with
    Close only;
  - a refusal, a non-clean target, an UNKNOWN stop or a failed verification keeps
    `Normalizer - Send to Developer - …` with Show Log File and the developer guidance;
  - a clean run replaces `Normalizer - Last Run.log`;
  - Resource Stop and Send to Developer share **one 20-file dated-report limit**.
- **Offline (`25a5e3cd…`, manifest `5de996a7…`):**

  | Suite | Result |
  |---|---|
  | UI and log classification | 20/20 |
  | Resource stop | 69/69 |
  | Production floors | 35/35 |
  | Retention | 19/19 |
  | Diagnostics | 74/74 |
  | PRE regression | identical to the qualified record |

**Real-SFM qualification of `6b5d2941…` with corrected Candidate C (2026-10-22): ACCEPTED (bounded), Astra's final
adjudication.** Amendment §6 items 2 and 5.
- **Method:**
  - the corrected Candidate C authority and the Phase F Normalizer were staged reversibly, with SFM closed;
  - the clean UNKNOWN and the STOP were produced by the approved 2026-10-21 injection applied to Phase F, as two
    qualification-only menu entries (UNKNOWN `8d355165…`, STOP `e609c2d4…`), checked offline first (9/9);
  - production floors were unchanged (112 MiB / 24 MiB);
  - the runbooks are `RUNBOOK.md` `7856c47f…` and `RUNBOOK_CONTINUATION.md` `f56509d1…` (private evidence, local
    only; work-folder manifest `b4ec12e8…`).
- **Attempt 1 (rsq disposable fixture, 15 shots): INCOMPLETE, stopped by a genuine protective STOP.**
  - **Selected (4 shots, 9 targets):** PASS, on corrected Candidate C (report `8786de01…`).
  - **Selected → All admission:** PASS. All was admitted in the same process with no history restriction.
  - **All completion:** NOT DEMONSTRATED. A genuine STOP occurred at `TARGET_PREPARATION`, trigger `LARGEST_FREE`
    (largest block 21.75 MiB; free memory 112.08 MiB), at shot11 after 9 of 15 shots and 17 native operations.
  - **The protective STOP and its verified closure:** PASS. Every closure, isolation and teardown check passed;
    `LOW_MEMORY` was recorded on the main window and in the process; the window had Close only; the report was
    classified RESOURCE_STOP (`b0937566…`).
  - **Not tested in this attempt:** the subsequent restart refusal, the clean UNKNOWN retry and the CPM
    alternation.
  - **Disposition:** `PROCESS1_DISPOSITION.md` `0ca8a505…`. The installation was then restored exactly.
- **Continuation (Astra's bounded two-process plan):**
  - **Process A** (rsq fixture, single-shot selections):
    - **Clean UNKNOWN:** PASS. Injected UNKNOWN at shot3; closure verified; no restart requirement recorded; no
      native work; a Send to Developer report (`bd308c30…`).
    - **UNKNOWN retry:** PASS. The next invocations were admitted with no restart requirement.
    - **Controlled STOP:** PASS. Injected at shot2/mia1; verified; `LOW_MEMORY` on both records; Close only;
      RESOURCE_STOP report (`a73fee4c…`).
    - **Restart refusal:** PASS. The next production invocation was refused with the restart message before any
      preparation, which writes no report.
  - **Process B** (existing smaller 11-shot fixture `testscripts_krysandnika.dmx`, one SFM process):
    - **Selected, then All:** completed normally, **operator-observed.** Their reports were overwritten: every clean
      run replaces the single `Normalizer - Last Run.log`, and the runbook did not copy each clean report before the
      next run. No native-operation count for All is recorded. No dated problem report exists for either run.
    - **CPM Save on `krystal20201`:** authorized against `1d855cd3…`.
    - **Normalizer Selected with the same CPM window and scope open:** PASS (report `a774a7f0…`). Corrected Candidate
      C authority; all targets completed; `protected_handles_released=True`.
    - **CPM Apply in the same window and scope:** authorized against `1d855cd3…`. It was a **valid no-op** (preset
      already matched; undo count unchanged), so **no mutating Apply/Undo is claimed.**
    - **Temporary preset:** deleted.
    - **CPM's scope** was retained across the Normalizer run, with no refusal and no rebuild (`c2f5ab08…`).
  - **Accepted:**
    - Phase F Selected, Selected → All admission, the protective STOP, the UNKNOWN retry and the restart refusal;
    - CPM/Normalizer coexistence on corrected Candidate C;
    - Master protection: handles released, and the Candidate C Master unchanged, verified when restoring;
    - successful All on the 11-shot fixture, as operator-observed.
  - **Disposition:** `CONTINUATION_DISPOSITION.md` `ca62b5b1…`.
- **Restoration (verified exact, after each attempt):**
  - G1 authority, hash and modification times equal to the backup;
  - the production Normalizer `1f4ec5a2…` with its modification time;
  - both qualification entries removed;
  - the CPM preset library returned exactly to its pre-test snapshot (the only differences had been the temporary
    preset's Trash copy and the Krystal library's index and `character.json` files);
  - fixtures and autosave unchanged;
  - Quick Launch, CPM, Extended ASE and Autoinit unchanged (`restoration_verification.json` `529a0dfc…`).

  The live installation is again exact G1 with the production Normalizer `1f4ec5a2…`.
- **No further SFM testing is required for these items.**

**Pending (not yet performed):**
- **The amendment §6 qualification delta:**
  1. Candidate C structural and compiled-authority validation: DONE (offline, 2026-10-21; see above);
  2. focused K-level coexistence with the corrected Candidate C: DONE (real SFM, 2026-10-22; see above);
  3. changed-inventory identity, compatibility and packaging checks;
  4. L-6 on the exact shipping candidate, with the amendment §5 reconciliation.

  Item 5, the bounded live-SFM check of Phase F, is DONE (real SFM, 2026-10-22; see above).
- **Unchanged:** the L-5 items below (production trust, the L-6 test-trust conflict, inventory deployment).
- **L-6:** NOT STARTED / NOT AUTHORIZED.

Previous milestone: **L-5 — Compatibility and packaging: COMPLETE / PASS (bounded), 2026-10-19. Designer-reviewed
and owner-accepted, including the owner-approved compatibility correction.** Committed at the L-5 GitHub checkpoint.
Authorized by the owner under the L card §5. Base: `0010395…`.
- **Private evidence (local only):**
  - L-5: `L5_IMPLEMENTATION_REPORT.md` `83ec2f22…`, manifest `1f4ac03a…` (46 entries);
  - compatibility correction: `L5_CORRECTION_REPORT.md` `7ea88cd7…`, manifest `4495d90f…` (52 entries).
- **Accepted result:** 303/303 PASS (the correction runs `c_final` and `c_final2`; see below). The candidate
  `l5-candidate-20261019T1435Z` (identity `cf792970…`) is a scratch build, not committed and not deployed.
- **Application version:** SFM Control Group Updater **0.1.0** (`VERSION`; About shows it dynamically).
  Animation-group data stays separately versioned (`data-v1.0.0`).
- **Authority profile (`compat/profile.py`):** `sct-authority-profile-1` is now a defined contract, identified by
  its canonical-JSON SHA-256 `2bbd93d0…`. It binds:
  - layout and Master path resolution;
  - sidecar format/semantics 0;
  - the 7 compiler and 2 validator/provider hashes, equal to `candidate.PINS`;
  - runtime API `1.0.0-b2a` and build `package-boundary-corrected-2026-09-22`;
  - the CPM (`sfm-character-semantic-provider-v1`, `cpm-compat-v1`) and Normalizer consumer contracts;
  - static admission limits;
  - the `sct-updater-tx-1` publication protocol;
  - the deployment policy (source authoritative; `.pyc` derived, not inventoried).
- **Signed installed-software inventory (`compat/inventory.py`):**
  - **Location:** `usermod\scripts\sfm\mainmenu\ChadChan3D\sfm_character_tools_inventory.json/.sig`.
  - **Signature:** Ed25519 over the exact bytes, under the same trust as official data.
  - **Content:** the 31 immutable K-qualified software files (CPM app and launcher, Normalizer, CPM adapter and
    projection, authority package, sidecar reader), with role, length and SHA-256; the profile ID and its exact
    contract hash; the runtime identity.
  - **Producer:** `release_tools/make_software_inventory.py` with `release_tools/character_tools_software_v1.json`,
    which records the qualified identities and refuses others. Mutable data is never listed.
- **Enforcement (owner-approved Astra adjudication, 2026-10-18; corrected 2026-10-19):** all three actions — Get
  Published Version, Update Using SFM's TXT and Choose Another TXT File — require a verified, supported Character
  Tools installation before installing data.
  - **Where:** at the common installation admission boundary in `backend.install`, re-verified immediately before
    installation even when preparation was earlier. Published data is also checked before it is prepared.
  - **Preparation:** compiling and validating a TXT stay available without verification. Custom TXT files remain
    supported and need no signature: TXT validation shows the data is valid; the software check shows the installed
    Character Tools can consume it.
  - **Not gated:** recovery of an already-started transaction.
  - **No repair:** modified programs are never overwritten or repaired. An inventory mismatch means unknown
    compatibility, not necessarily defective software.
  - **Refusals (owner-approved text):** missing or unsupported identification gives "This updater couldn't verify
    the installed Character Tools. Install or repair a supported Character Tools release, then try again. Your
    animation-group TXT was not changed." Modified software gives "Some Character Tools program files differ from
    the supported release. Back up your program edits before restoring that release, then try again. Your
    animation-group TXT was not changed." Both happen before any installation step, so the TXT claim holds.
  - **Backend change:** a 10-line admission check (official at preparation and installation; all workflows at
    installation). `recovery`, `journal`, `w32`, `layout`, `legacy_lock`, `process_gate`, `official`, `hooks`,
    `discovery`, `staging` and `user_backup` are byte-identical to `0010395`, and activation is unchanged.
  - **Superseded:** the first L-5 implementation's official-only scope (2026-10-18) and its P6 case, which allowed
    unverified local installation.
- **Package (`updater/packaging/`):** PyInstaller 6.11.1 one-folder build of CPython 3.10.6 x64.
  - **Executables:** `SFM Control Group Updater.exe` (GUI) and `sct-updater-worker.exe` (worker, started inside the
    unchanged Job Object, 2 GiB, kill-on-close).
  - **Pinned sources:** the nine pinned compiler/validator/provider sources are carried byte-exact in
    `_internal\sct_deps` and verified by `candidate.PINS`. There is no import from repository paths and no
    duplicate authority package.
  - **Recipe:** `requirements-build.txt` (hash-locked, offline install), `build.py` (environment and pin checks,
    minimal build `PATH`, fixed hash seed, post-build pin/forbidden-content/workstation-marker checks,
    `bundle_manifest.json`), `sct_updater.spec`, `README.md` (layout, dependency inventory, profile/inventory design,
    intended L-6 deployment).
  - **Build correction:** the first build collected an OpenSSL 3 from Git for Windows on `PATH`. The recipe now uses
    a minimal `PATH`, and the bundle carries only CPython's OpenSSL 1.1.1n.
  - **Reproducibility:** two builds give the same file set and identical code. All bytes are identical except the
    executables' embedded archive and one stdlib `.pyc`, whose code objects unmarshal identically (CPython 3.10
    `marshal` serialization).
- **Candidate (scratch, not deployed):** the scratch build `l5-candidate-20261018T0956Z` (folder
  `dist\SFM Control Group Updater\`).
  - 965 files, about 33 MB, bundle identity `ee51113d…`.
  - GUI executable `a0a6c09d…`, worker executable `4a04c115…`.
- **Read-only diagnostics:** `runtime-check`, a new worker command, reports runtime identity, import origins, pinned
  sources, Ed25519 (RFC 8032 test vector) and the TLS trust store.
- **GUI:** `--sfm-folder PATH` preselects an installation, for the L-6 menu entry. No wording or layout changed.
- **Compatibility correction result (2026-10-19):** effective **303/303 PASS**.
  - `c_final` (13:35–14:34Z): the full existing suite A–K, N, X, M, O, W3, Q (236) as regression, with every scratch
    installation carrying the qualified software and its test-signed inventory.
  - `c_final2` (14:36–14:46Z): P 34, U 25, W 2 and W4 6 on the corrected worker and rebuilt candidate.
  - **P6 rewritten:** both local workflows install on verified software; refuse when software is unverified,
    modified, of an unsupported profile, or changed between preparation and installation (nothing installed, TXT
    unchanged, no backup); presets, logs, bytecode and custom TXT do not invalidate the inventory; recovery of an
    interrupted transaction completes after a program file changed.
  - **Product defect found and fixed:** the worker wrote the user TXT backup before the backend's software check,
    so a refused replacement left an unclaimed backup file. The backup is now made only after verification passes.
  - **Candidate:** the scratch build `l5-candidate-20261019T1435Z` (`dist\SFM Control Group Updater\`), 965 files,
    identity `cf792970…`; GUI `6d12bd72…`, worker `63312291…`. It supersedes the 2026-10-18 candidates.
  - **Consequence (now verified):** the shipping candidate trusts no key, so it installs **no data at all** until the
    production public key is embedded. The packaged workflows compile and prepare, then refuse installation truthfully
    (P9, W2, W4a, U22).
  - Real process status CLEAR; the live installation identical before and after (see the `gameinfo.txt` observation).
- **First L-5 result (2026-10-18, before the correction):** effective **136/136 PASS**.
  - `final`, 2026-10-18 09:57–10:16Z: M 11, O 36, W 2, W3 1, Q 33, W4 6 (89).
  - `final2`: P 22/22 against a fresh clean copy of the final candidate.
  - `final3`: U 25/25.
  - Product source was identical across the three runs; only the harness changed. Real process status was CLEAR
    throughout. The live installation was identical before and after.
- **Group P covered:**
  - the profile and pins, and the qualified software staged byte-exact;
  - the qualified test installation accepted, installed and re-verified;
  - rejection of a changed consumer, a missing file, an invalid signature, an altered inventory, an unsupported
    profile, a contract mismatch, a missing inventory, an untrusted signer, a missing role, path traversal and a
    runtime mismatch;
  - mutable data not checked;
  - the install-time re-check;
  - local workflows unaffected.
  - **Clean directory:** runtime closure (frozen 0.1.0, every path and module from the bundle, even with
    `PYTHONPATH`/`PYTHONHOME`/`PATH` pointing at the development Python; Ed25519; TLS store); packaged compiler
    parity and determinism (G1 = live `bcd97641…`/`d810d648…`); the three workflows through the packaged shipping
    worker (rebuild and import installed; a test-signed package refused as unsigned; the real empty release list
    over TLS); the packaged worker rejects test options; the packaged GUI's window, its worker inside a Job Object,
    idle close with no orphan; bundle contents equal the manifest.
- **Recorded deviations:**
  - a `runtime_check` diagnostic resolved frozen modules' relative `__file__` against the working directory. It is
    fixed: they are reported as `<frozen>`. The candidate was rebuilt.
  - harness defects, all fixed: a run-wide clean copy reused the earlier candidate (now per run label), and the U24
    expectations were updated for the GUI's `sys` import and new entry.
- **Not covered (L-6 or release):** production trust (the shipping trust list is empty), native SFM, the deployed
  menu entry, a real official release, and Windows other than this Windows 10 machine.
- **L-6:** NOT STARTED / NOT AUTHORIZED. The pre-L-6 dependencies are listed under Next.

Previous milestone: **L-4R — GUI usability refinement and final polish: COMPLETE, owner-accepted, 2026-10-18.**
The owner visually reviewed and approved the final GUI, and requested no further interface changes. This entry
completes the L-4 usability refinement below and supersedes its wording where they differ. It is committed at the
L-4R GitHub checkpoint.
- **Private evidence:**
  - refinement: report `ce2e69b1…`, manifest `e2fb0af8…`, 43 entries;
  - final polish: `L4R_FINAL_POLISH_REPORT.md` `32d395e7…`, manifest `4567f193…`, 40 entries.
- **Versioning (owner note):**
  - The **SFM Control Group Updater** targets initial public version **v0.1.0**, to be assigned during L-5 packaging.
    Until L-5 the current development version (`0.4.0-l4`) is kept, and the About window keeps showing the running
    application version dynamically (`VERSION`).
  - **Animation-group data** is versioned separately, beginning with `data-v1.0.0`.
- **Approved product identity and copy (all verbatim; frozen documents unchanged):**
  - The title is **SFM Control Group Updater**, in the window and the title bar. Modules, APIs and history keep
    their names.
  - The three equally prominent buttons are:
    - **Get Published Version**: "Download the flex and bone organization maintained by ChadChan3D."
    - **Update Using SFM's TXT**: "Build Character Tools data from the animation-group TXT already in your SFM
      folder."
    - **Choose Another TXT File**: "Select a different animation-group TXT to use in SFM."
  - "SFM folder:" / Change Folder. The folder picker is titled "Select your SourceFilmmaker folder" and starts at
    the selected installation.
  - "Close SFM before updating its animation-group TXT or Character Tools data." in regular weight under the
    actions. "Choose an action." is removed.
  - The matching status, "Installed animation-group TXT and Character Tools data match.", is subtle text at the
    bottom. It is hidden during operations and refreshed after them. Mismatches, errors and recovery stay prominent
    under the folder line. It describes local files only.
  - **Update Using SFM's TXT:** one stable "Updating Character Tools data…" message and progress bar through both
    steps. NOOP shows "Your data already matches" / "Character Tools data already matches the animation-group TXT
    in SFM. Nothing was changed." Success shows "Character Tools data updated" / "Character Tools data now matches
    the animation-group TXT in SFM."
  - **Get Published Version:** "Nothing published yet" / "ChadChan3D hasn't published a version yet. Nothing was
    changed."; "Published version already installed" / "Published animation-group version [version] is already
    installed. Nothing was changed."; "Published version available" / "A published animation-group TXT and matching
    Character Tools data are available to install." Discovery is unchanged, and there is no "latest" claim.
  - **Replacement confirmation:** "Replace your animation groups?" / "This will replace SFM's animation-group TXT
    with your chosen file and build matching Character Tools data." / "Your current animation-group TXT will be
    saved in the Backups folder." plus the actual folder, with Replace Groups / Cancel.
  - **Replacement success:** "Animation groups updated" / "Your chosen animation-group TXT and matching Character
    Tools data are installed." / "Your previous animation-group TXT was saved in the Backups folder." plus the
    verified file, with Open Backup Folder.
  - **About:** "About SFM Control Group Updater" (title and heading), the approved three paragraphs, then
    "Version:" (running version) and "Author: ChadChan3D", with Close at bottom right. The window is centered over
    the main window, and Copy Diagnostic Information is removed.
  - **Main window:** About at bottom left and Close at bottom right. Close exits when idle and keeps the safe-close
    confirmation during an operation.
  - Only the title, the primary buttons and the active result or confirmation heading are bold.
- **Proposed, not owner-approved verbatim:** the remaining outcome texts, and the published-version replacement
  lead "This will replace SFM's animation-group TXT with published version X and build matching Character Tools
  data."
- **Diagnostics:** the worker results are kept internally (`App.diagnostics`). The shortcut Ctrl+Shift+D copies them
  to the clipboard for support; it is not shown in the interface. It was disclosed at review, and the owner accepted
  the GUI with no further changes.
- **Source:** only `gui/app.py` changed in this polish (`8f6881a0…`), with the tests (`run_l1.py` `312983b5…`,
  `support/gui_driver.py` `05506979…`). `user_backup.py`, `worker.py` and `messages.py` are unchanged from the
  refinement. `backend`, `candidate`, `recovery`, `journal`, `w32`, `layout`, `legacy_lock`, `process_gate`,
  `official`, `hooks`, `discovery`, `staging`, `supervisor` and the release producer are byte-identical to `7b95628`.
- **Result:** group U **25/25 PASS** (`final_polish`, 2026-10-18 05:05–05:13Z), on sources frozen before the run and
  unchanged after it.
  - **New cases:** U21 (the startup line, layout, font weights, title, About text/order/centering/Close, no Copy
    Diagnostic Information, internal diagnostics, Close when idle) and U21b (Close during an update: declined keeps
    it running; confirmed stops it; recovered).
  - U1 now asserts one stable message and progress bar; all approved strings are asserted exactly.
  - No worker or backend behavior changed, so the worker regressions of the refinement (M, O, W, W3, W4) were not
    rerun.
  - The real process status was CLEAR. The live installation was identical before and after the run, with its
    authority equal to the G1 pins.
- **Owner acceptance:** visual review completed and approved (2026-10-18). `updater/SHA256SUMS.txt` is regenerated
  at this checkpoint.
- **L-5:** NOT STARTED / REQUIRES AUTHORIZATION at this checkpoint. It has since been completed (see Current milestone).
  **L-6:** NOT STARTED.

Refinement record (2026-10-18; superseded by the final polish above where the wording differs; its open review
items are resolved by the owner acceptance above):
**L-4 usability refinement (owner-approved, 2026-10-18): IMPLEMENTED; accepted with the final polish.**
Assigned by the owner after the L-4 window review, with an exact-wording addendum. Base: `7b95628…`. Private evidence:
`L4R_IMPLEMENTATION_REPORT.md` and its evidence manifest (see the report's return for hashes).
- **Approved amendment (recorded here; frozen documents unchanged):** the owner approved replacing the card's
  exact primary-button labels. The window is now **SFM Animation Group Manager**, and its three equally prominent
  buttons are:
  - **Get Published Version**: "Download the flex and bone organization maintained by ChadChan3D."
  - **Update From My TXT**: "Update Character Tools using your current animation-group TXT, including any changes
    you've made."
  - **Choose Another Group File**: "Select a different animation-group TXT to use in SFM."

  Their functions are unchanged: an authenticated published data release; a rebuild from the installed TXT, which
  is never rewritten; and a replacement of the installed TXT with a chosen file and its matching data. The L card,
  Amendment and R2 keep their original wording.
- **Window (approved strings verbatim):**
  - "Choose an action." before the buttons; "Save your work and close SFM before installing data." after them. The
    sentence about preparing while SFM is open was removed.
  - "SFM folder:" selector (shows the SourceFilmmaker folder; Steam discovery plus Change Folder).
  - About ("About SFM Character Tools", the approved two paragraphs, "Created by ChadChan3D", the running version)
    replaces Show Details. Copy Diagnostic Information copies the session's worker results to the clipboard; no raw
    JSON is shown.
  - Startup shows "Checking animation-group data…" as a text line with no progress bar, then the local match state.
    The local TXT/data match is shown separately from published-version status.
- **Flows:**
  - **Update From My TXT:** with SFM confirmed closed, one click prepares and installs. With SFM open or its state
    unknown, it prepares privately and shows "Close SFM to finish" with Finish Update. A verified NOOP shows "Your
    data already matches" / "Your animation groups and Character Tools data are already in sync. No changes
    needed."
  - **Choose Another Group File:** a file picker, then one confirmation, "Replace your animation groups?" (approved
    text, the actual Backups folder, Replace Groups / Cancel). It replaces the checkbox and disabled Install button.
    Consent stays bound to the observed TXT (`--confirm-sha`) and to the chosen file's re-check. Success shows
    "Animation groups updated", the approved text, the saved backup's name and location, and Open Backup Folder.
  - **Get Published Version:** distinct outcomes for nothing published, available (Download and Install), installed
    ("Published version X is installed", not "latest"), needs a newer program, check or download failed, and
    rejected.
  - Other outcome wording follows the owner's principles. It is **proposed, not owner-approved verbatim**.
- **User TXT backups (`user_backup.py`, worker `install --backup-txt`, used by the GUI):**
  - Before an install that replaces the installed TXT, with SFM confirmed closed, a verified copy is saved in
    `usermod\cfg\sfm_character_tools_backups\` as `sfm_defaultanimationgroups_backup_<date-time>[_n].txt`.
  - The copy is checked to hash to `--confirm-sha`. The backend refuses any replacement whose installed TXT no
    longer has that identity, so a completed replacement replaced exactly the saved TXT.
  - Files are created new and never overwritten; an identical earlier backup is reused.
  - If the backup cannot be made and verified, the replacement is refused ("Nothing was replaced").
  - A backup is claimed only when the install completed as a replacement.
  - **Unchanged protocol:** the backup runs before, and outside, the protected install. Internal snapshots,
    retired files, journaling and recovery are unchanged, and without the flag the worker behaves exactly as at L-4.
- **Source:**
  - **New:** `user_backup.py`.
  - **Changed:** `gui/app.py` (rewritten), `worker.py` (opt-in `--backup-txt`), `messages.py` (BACKUP_FAILED), and
    the tests (group U rewritten; `support/gui_driver.py`).
  - **Unchanged since `7b95628`:** `backend`, `candidate`, `recovery`, `journal`, `w32`, `layout`, `legacy_lock`,
    `process_gate`, `official`, `hooks`, `discovery`, `staging`, `supervisor` and the release producer.
    `updater/SHA256SUMS.txt` is not yet regenerated (checkpoint step).
- **Result (targeted, not a new campaign):** 80/80 PASS (2026-10-18 03:12–03:25Z): the refined group U 24/24, plus M
  11/11, O 36/36, W 2/2, W3 1/1 and W4 6/6 as regression of the worker's install, import, official and entry
  paths.
  - **Group U covers:**
    - one-click update and the matching-data result;
    - replacement with confirmation, backup and Open Backup Folder; Cancel;
    - consent invalidated by a destination change (refused before any backup or install) and by a source change
      (no backup claimed);
    - an unusable file and a cancelled picker;
    - published-version outcomes and installation (test key);
    - SFM RUNNING and UNKNOWN waits; replacement refused while SFM runs (no backup made);
    - recovery shown, executed and refused while SFM runs;
    - worker killed; the memory ceiling; window closed and GUI process killed (recoverable);
    - backup rules (never overwritten, identical reuse, wrong identity refused, unusable Backups location refused);
    - staging cleanup scope;
    - startup text, About and diagnostics;
    - shipping worker and the production ceiling (highest peak 329 MiB of 2 GiB);
    - the product surface (approved strings asserted exactly).
  - The real process status was CLEAR throughout. The live installation was identical before and after the final
    run, and the sources were unchanged during it.
- **Not yet done:** the owner's hands-on review of the revised window (five scratch screenshots are in the evidence),
  designer review, and the checkpoint commit.
- **L-5:** NOT STARTED / REQUIRES AUTHORIZATION at this checkpoint. It has since been completed (see Current milestone).
  **L-6:** NOT STARTED.
- **Live installation observation (not caused by this work, not verified by it):** after the L-4 checkpoint the
  live `usermod\cfg` gained `sfm_character_tools_updater\` with one transaction completed by the updater at
  2026-10-18 01:52Z (journal VERIFIED → COMPLETE). At 03:02Z the live Master, sidecar and manifest were
  `f85fab80…`, `063a5e0c…` and `126c8307…`. By 03:10Z the authority files were again exact G1 (`ac45e5c1…`,
  `bcd97641…`, `d810d648…`), with no updater transaction recording that restoration. Owner-made copies named
  `… - 17octbackup` and `sfm_shared_authority.zip` are also present. This session made only read-only fingerprints
  of the live installation. Restoring files by hand outside the updater leaves its transaction record describing a
  replaced state; `status` treats the completed transaction as terminal.

Previous milestone: **L-4 — SFM Character Tools Updater GUI and bounded worker: COMPLETE / PASS (bounded), 2026-10-17.**
Authorized by the owner under the L card §5. The designer accepted the report provisionally (private evidence,
`L4_IMPLEMENTATION_REPORT.md` `78d1d47a…`; evidence manifest `e61a7963…`, 51 entries). Base: `59e5254…`.
- **Source (GitHub, `updater/`; digests in `updater/SHA256SUMS.txt`):**
  - **New:** `gui/app.py`, `gui/__init__.py`, `gui/__main__.py`, `supervisor.py` and `staging.py`.
  - **Changed:** `worker.py` (post-install cleanup; `discard-prepared`), `discovery.py` (the download folder is
    removed once prepared), `messages.py` and `__init__.py` (version `0.4.0-l4`).
  - **Tests:** group U in `run_l1.py`, `support/test_worker.py` (test-only `--hold-at`/`--hold-marker`) and the new
    `support/gui_driver.py`.
  - **Unchanged since L-3:** `backend`, `candidate`, `recovery`, `journal`, `w32`, `layout`, `legacy_lock`,
    `process_gate`, `official`, `hooks` and the release producer.
- **GUI** (`python -m sfm_character_tools_updater.gui`, Tkinter):
  - three equal-width primary buttons labelled exactly **Get Official Data**, **Rebuild My Data** and **Use Another
    TXT** (no ellipses, no menu), each with a plain explanation;
  - an installation selector (read-only Steam library detection, plus Choose Folder);
  - the note "Save your work and close SFM before installing data.";
  - progress, preview and result screens, a recovery mode, and a Details area.
- **Workflows:** each action runs only the existing worker commands, so the GUI writes no installed file and there is
  no second publication path.
  - **Get Official Data:** `check-official`, then (when AVAILABLE) `download-official` and `install`.
  - **Rebuild My Data:** `prepare-rebuild`, then `install`.
  - **Use Another TXT:** a file picker, `prepare-import`, a preview (file, destination, backup note), consent before
    Install (bound to the observed destination TXT), then `install`. Cancel runs `discard-prepared`.
- **Truthful outcomes:**
  - Success is shown only for a backend COMPLETE, after the backend's own verification, or a recovery reporting
    WORKING.
  - Refused (SFM open or its state unknown: "Close SFM, then try again", with Try Again), NOOP, UNVERIFIED,
    interrupted and recovery-needed are distinct screens.
  - Unfinished work shows the recovery screen with the primary actions disabled; Recover runs the L-1 `recover`.
- **Bounded worker (`supervisor.py`):**
  - the unchanged worker is created suspended, assigned to a Windows Job Object, then resumed;
  - job-wide memory ceiling **2 GiB**, with kill-on-job-close (no worker outlives the GUI) and
    die-on-unhandled-exception;
  - a result is classified WORKER_MEMORY_LIMIT, WORKER_STOPPED or WORKER_FAILED when the worker gives none, never
    success.
- **Measured peak job memory (G1-scale workload, 54 runs):** status 126 MiB; prepare 303 MiB; download 329 MiB;
  install 141 MiB; recover 125 MiB; check 30 MiB. The ceiling is about 6× the highest peak.
- **Staging cleanup (`staging.py`):**
  - only direct children of `…\staging` that the updater itself creates (preparation and `download-<id>` folders
    with only known plain files);
  - removed after COMPLETE/NOOP (the consumed preparation), on discard, once a download is prepared, or after 24 h
    untouched;
  - unexpected content, unfamiliar names, recent folders and links are kept;
  - transactions and recovery data are outside its scope.
- **Production surface:** the entry point passes no test arguments, and the shipping worker rejects every test
  option. `official.TRUSTED_KEYS` remains empty, so no official package can be installed and unverified data is never
  offered.
- **Result:** effective 267/267 PASS.
  - `final`, 2026-10-17 23:39 to 10-18 00:36Z: groups A–W4 except Q, 211/211 (rerun as regression because the install
    and download paths changed).
  - `final_q`: Q 33/33.
  - `final_u`: U 23/23 on the final GUI source.
  - The real process status was CLEAR throughout. The live installation fingerprint was identical before and after.
    Sources were frozen before each run and unchanged during it.
- **Group U** drives the real window, invoking its buttons as clicks:
  - the three actions end-to-end;
  - consent accepted, declined and invalidated by a destination change; a cancelled file picker;
  - official data: none published, unverified, and installed with a test key;
  - install refused for SFM RUNNING and UNKNOWN, then Try Again;
  - recovery presented, executed, and refused while SFM runs;
  - worker killed during install and during preparation;
  - the memory ceiling (64 MiB in the test);
  - window closed during install, and close declined;
  - GUI process killed during install (its worker ended with it; recovered);
  - cleanup scope;
  - the shipping worker at the production ceiling;
  - the product surface.
- **Recorded corrections (preserved in the evidence):**
  - **Product defect found and fixed:** a Tk variable could be garbage-collected on the worker-wait thread
    (`Tcl_AsyncDelete`). The consent variable now lives as long as the window.
  - **Test design:** a junction in staging makes every command refuse (the L-1 reparse rule), so that case calls the
    cleanup function directly (U19b).
  - **Test-only failure in `final`:** 25 Q cases failed on a user-agent check pinned to `0.3.0-l3`, although every
    outcome matched. The check now reads `VERSION`, and Q was rerun.
  - **GUI layout:** after `final`, the consent box moved above Install (only `gui/app.py` changed), and U was rerun.
- **Not yet done:** a hands-on owner review of the window. Layout was checked only by two screenshots and
  programmatically. (Since then the owner reviewed it and approved the usability refinement above.)
- **Scope of the PASS:** a headless-driven GUI on scratch installations with test keys and a loopback GitHub
  stand-in, plus the shipping worker on a scratch installation. It does not cover packaging (L-5), native SFM, a
  real official release, production trust or release eligibility.
- **No official data release has been published.** Release dependencies are unchanged: the production signing key,
  the signed compatibility profile and installed-software inventory (L-5; `sct-authority-profile-1` remains
  provisional, not certified), `published_at` and the final signed `data-v1.0.0` package.
- **L-5:** NOT STARTED / REQUIRES AUTHORIZATION at this checkpoint. It has since been completed (see Current milestone).
  **L-6:** NOT STARTED.

Previous milestone: **L-3 — Get Official Data online (headless) and official repository identity: COMPLETE / PASS (bounded), 2026-10-17.**
Authorized by the owner under the L card §5, together with the repository identity resolution. The designer accepted
the report provisionally (private evidence, `L3_IMPLEMENTATION_REPORT.md` `834619bb…`; evidence manifest
`1d2a1635…`, 55 entries). Base: `230aa5b…`.
- **Official repository:** the GitHub repository was renamed. The owner confirmed `chadchan3d/sfm-character-tools`
  as the permanent official source of data releases.
  - `official.REPOSITORY` now holds it, for both descriptor validation and release discovery.
  - The check stays exact: a descriptor naming any other repository, including the previous name
    `chadchan3d/sfm-animation-groups-master`, is refused.
  - Redirects from the previous name are not followed.
  - Historical Blueprints, evidence and checkpoint records keep the previous name as written.
- **Source (GitHub, `updater/`; digests in `updater/SHA256SUMS.txt`):**
  - **New:** `sfm_character_tools_updater/discovery.py`.
  - **Changed:** `official.py` (the constant only), `worker.py`, `messages.py`, `hooks.py` and `__init__.py`
    (version `0.3.0-l3`).
  - **Tests:** `run_l1.py` (groups Q and W4) and `support/test_worker.py`; new `support/fake_github.py` and
    `support/net_audit.py`.
  - **Byte-identical to L-2:** `backend`, `candidate`, `recovery`, `journal`, `w32`, `layout`, `legacy_lock`,
    `process_gate` and the release producer.
- **Worker commands:** `check-official` (writes nothing) and
  `download-official --release-tag --descriptor-sha [--allow-older]`.
  - These are the only commands that use the network, each started by an explicit user action.
  - There is no background polling, and importing the worker loads no network module.
- **Discovery** of `https://api.github.com/repos/chadchan3d/sfm-character-tools/releases`:
  - **Listing:** complete (at most 10 pages of 100, each at most 8 MiB). Anything incomplete or malformed gives
    "Couldn't check for updates."
  - **Data releases:** tag `data-vX.Y.Z`, not a draft or prerelease.
  - **Authentication:** each descriptor is checked by the L-2 verifier. Its signed tag must equal the GitHub tag,
    and the assets must be exactly the five signed files with the signed sizes.
  - **Offer:** the highest compatible authenticated sequence, as "Official data [version] is available". There
    is no "latest" claim.
  - **Other outcomes:** a newer release needing a newer updater, a conflict, older only, unverified, incompatible
    and already installed are each reported as such.
  - **Empty list:** "No official data has been published yet."
- **Download:**
  - bound to the checked tag and descriptor digest;
  - compatibility and the sequence rule are checked before any payload request;
  - each file is bounded by its signed length and hash-checked before writing;
  - files are written only to `staging\download-<id>`, then go through the unchanged L-2 `prepare_official` and
    the L-1 install;
  - HTTPS with certificate verification, one redirect allowed and only to GitHub release-asset hosts, no
    credentials sent.
- **Trust boundary (unchanged):**
  - `official.TRUSTED_KEYS` is empty, so the shipping worker refuses every official package.
  - The network test seams (`hooks.network_rewrite`, `hooks.network_timeout`) are set only by
    `tests/support/test_worker.py`.
  - The shipping worker rejects `--net-base` and `--net-timeout`.
- **Result:** final run 244/244 PASS (2026-10-17 21:04–21:56Z):
  - the L-1/L-2 suite as regression, 205/205;
  - Q 33/33, against a loopback GitHub stand-in with test-signed releases;
  - W4 6/6, the shipping worker:
    - no network outside the two commands;
    - one explicit query of the real official list, empty, giving NONE_PUBLISHED;
    - a real download of an absent release, refused;
    - the previous name's real 301, not followed.
- **Run conditions:** the real process status was CLEAR throughout. The live installation fingerprint was
  identical before and after, and the sources were identical to the hashes frozen before the run.
- **Recorded deviations (preserved in the evidence):**
  - **Product defect found in the shakedown and fixed:** refusing an oversized download raised a duplicate
    keyword. It failed closed (ERROR, nothing written); Q25 now gives PACKAGE_DAMAGED.
  - **Test expectations:** three corrected.
  - **First final attempt:** stopped in group F because the harness invocation omitted the outside-target
    argument. Groups A–E had passed 100/100 and no F result was written. The full run was repeated from the
    start.
- **No official data release has been published.** The real release list is empty.
  - `data-v1.0.0` exists only as an unsigned, provisional candidate (private evidence, manifest `4f8d3a10…`).
  - Candidate details: sequence 1; G1 Master `ac45e5c1…`, sidecar `bcd97641…`, manifest `d810d648…`; proposed
    `source_commit` `230aa5bc…`.
- **Outstanding release dependencies (unchanged):**
  - the production signing key (owner-held, outside the repository; its public key embedded by a separate
    authorized change);
  - the signed compatibility profile and installed-software inventory (L-5; `sct-authority-profile-1` remains
    provisional, not certified);
  - `published_at`;
  - the final signed package and its publication.
- **Scope of the PASS:** headless scratch qualification with a loopback stand-in and test keys, plus read-only
  queries of the real, empty list. It does not cover:
  - real asset downloads (no real release exists);
  - proxies or certificate-store packaging;
  - native SFM or the GUI;
  - production trust or release eligibility.
- **L-4:** NOT STARTED / REQUIRES AUTHORIZATION at this checkpoint. It has since been completed (see Current
  milestone). **L-5, L-6:** NOT STARTED.

Previous milestone: **L-2 — Use Another TXT and Get Official Data (headless): COMPLETE / PASS (bounded), 2026-10-17.**
Authorized by the owner under the L card §5. The designer accepted the report (private evidence,
`L2_IMPLEMENTATION_REPORT.md` `1a50f3e7…`; evidence manifest `f8cdac91…`). Base: `4cc180c…`.
- **Source (GitHub, `updater/`; digests in `updater/SHA256SUMS.txt`):**
  - **New:** `sfm_character_tools_updater/official.py` (R2 D1–D5) and the development-side release producer
    `release_tools/make_official_package.py` (not shipped).
  - **Changed:** `backend.py`, `candidate.py`, `worker.py`, `messages.py`, `hooks.py`, `__init__.py`
    (version `0.2.0-l2`) and the tests.
  - **Byte-identical to L-1:** `recovery.py`, `journal.py`, `w32.py`, `layout.py`, `legacy_lock.py`,
    `process_gate.py`. Inside the protected activation body only two message keys changed.
- **Worker commands added:** `prepare-import --source TXT`, `prepare-official --package DIR [--allow-older]`,
  `install … [--accept-replacement]`.
- **One protected backend:** both workflows reach the L-1 `install()` → `_activate()` route.
  - Use Another TXT, and official data whose TXT differs, use the replacement route: retire, then move into the
    vacant path by handle rename with `ReplaceIfExists=FALSE`.
  - Official data with the installed TXT installs the data files only.
  - No second publication path exists.
- **Use Another TXT:**
  - an immutable captured copy, bounded at 64 MiB; the chosen file is never written;
  - explicit consent required when the TXT changes, bound to the observed destination TXT;
  - a chosen file changed or removed before confirmation requires a fresh check;
  - the previous Master and authority are retained by the backend.
- **Get Official Data** (local package of exactly the five D1 files):
  - **Descriptor:** strict and bounded (16 KiB, no duplicate keys, exact keys and types, safe names).
  - **Signature:** Ed25519 over the exact `release.json` bytes, with the key chosen by id among trusted keys
    only.
  - **Compatibility:** contract 1, provisional profile `sct-authority-profile-1`, sidecar format and semantics
    0.
  - **Payload:** exact length and SHA-256. The official sidecar is checked against a canonical compile of the
    official TXT before anything is written, so it is never paired with another TXT.
  - **Remembered releases:** an append-only per-installation record. A reused sequence with different bytes is
    refused; an older release needs `--allow-older` and never lowers the high-water mark.
  - **Consent:** required when replacing a TXT that is not recognized official data.
  - **Install:** the staged package is re-authenticated.
- **Trust boundary:**
  - `official.TRUSTED_KEYS` is **empty**, so the shipping worker refuses every official package (O12, W3).
  - Per-run test keys exist only in the scratch area and are trusted only through the test-only seam
    (`hooks.extra_trusted_keys`, set only by `tests/support/test_worker.py`).
  - The shipping worker rejects every test option and uses the real `tasklist` process query.
  - No private key or credential is in the repository.
- **Dependency:** `cryptography` 50.0.2 (with `cffi` 2.1.1, `pycparser` 3.11, `typing_extensions` 4.16.0).
  - It was installed from recorded PyPI wheels into an isolated qualification virtual environment in the
    scratch area, as the owner approved. Global Python is unchanged.
  - It is imported only for signature verification. Bundling is L-5.
- **Result:** final run 205/205 PASS (2026-10-17 14:23–15:09Z):
  - the full L-1 suite as regression, 157/157 with unchanged expectations;
  - Use Another TXT (M) 11/11;
  - Get Official Data (O) 36/36;
  - shipping-worker trust W3 1/1.
- **Process states:** test operations use an injected CLEAR status unless a case sets its own. X3c and W2 use
  the real query, which was CLEAR throughout. The live installation fingerprint is identical before and after.
- **Recorded deviations and corrections (preserved in the evidence):**
  - **Product defect found and fixed:** `shake1` found that a duplicate descriptor key gave an internal error
    (failed closed, no success claimed) instead of a clean refusal. The regression case O14a now passes.
  - **Test defects corrected:** O4's expectation, and O18b hashing a file while it was locked.
  - **SFM running:** `shake2` stopped before any operation because SFM was running for the owner's other
    projects. The harness then switched to the injected default described above.
  - **Release record:** now created only on the first authenticated record.
- **Outstanding owner-controlled release dependency (not an L-2 defect):** a production Ed25519 signing key.
  - The owner generates it outside the repository (encrypted private key, offline backup, R2 D3).
  - Only the public key is embedded, by a separate authorized change.
  - Until then the shipping updater cannot install official data.
- **Scope of the PASS:** headless scratch qualification on E:/NTFS with a test key. It does not cover native
  SFM, either consumer's UI, real-SFM detection, power loss, cross-user behavior, production trust or release
  eligibility.
- **L-3:** NOT STARTED / REQUIRES AUTHORIZATION at this checkpoint. It has since been completed (see Current
  milestone). **L-4 … L-6:** NOT STARTED.

Previous milestone: **L-1 — Activation backend and Rebuild My Data (headless): COMPLETE / PASS (bounded), 2026-10-17.**
Authorized by the owner under `updater_qualification/design/L_IMPLEMENTATION_AUTHORIZATION_CARD.md` §8. The
designer accepted the report (private evidence, `L1_IMPLEMENTATION_REPORT.md` `f3091fce…`; evidence manifest
`39195857…`). Base: `5d7dea8…`.
- **Source (GitHub, `updater/`; digests in `updater/SHA256SUMS.txt`):**
  - `sfm_character_tools_updater/` (12 modules) — the one protected activation/recovery backend. Its worker
    commands are `status`, `prepare-rebuild`, `install` and `recover`.
  - `tests/` — the test-only L-1 suite: `run_l1.py` plus `support/` (test entry point, racer, holder, legacy
    publisher, Python 2.7 selector check, read-only fingerprint).
- **Port base:** the C1-corrected P1 prototype `p1proto_c1.py` `8871f137…`. The card names the original
  `537739ff…`, but P1 closed only after C1. In a function-level AST comparison:
  - 38 functions are identical, including the plan, the move executor, final verification, the journal, the
    lock, the no-clobber handle rename and checked writes;
  - 19 changed and 10 were not ported, every one explained in the report's equivalence table;
  - the C6–C8 move order, protection and C12 recovery rules are unchanged.
- **Implemented:**
  - `prepare()` writes only to `sfm_character_tools_updater\staging\<id>` and may run while SFM runs.
  - `install()` runs: pre-lock A3 gate → prepared bytes re-verified → transaction → lock → transaction
    records → post-lock gate → protection → journaled no-clobber moves → final verification through held
    handles → release → TXT/SIDECAR correspondence (a failure reports UNVERIFIED) → post-install process
    recheck (restart required if SFM was started).
  - **Path budget:** consumer paths of 260 characters or more refuse.
  - **New transaction schema** `sct-updater-tx-1`. The U0A/P1 schemas are refused without mutation.
  - **Recovery** reports whether the data is WORKING or NEEDS_REBUILD.
  - **`status`** is read-only.
  - **Pinned dependencies:** the unchanged compiler, reader, manifest and FINAL R3-A2B admission, each pinned by
    full SHA-256.
- **Replacement route** (Use Another TXT / Get Official Data in L-2):
  - It is implemented in production as `backend.prepare(layout, "replace", source)` (immutable captured copy in
    staging) plus the `backend._activate` replace kind (M0 retired, then M1 moved into the vacant Master path by
    handle rename with `ReplaceIfExists=FALSE`).
  - It is **not exposed** by the worker.
  - The final run exercised it in 110 cases through the test-only entry point, including 47 interruption
    cases.
  - P1's path-based `MoveFileExW(REPLACE_EXISTING)`, `ReplaceFileW` and `DeleteFileW` helpers are not in the
    product (R2 C6). They remain only in the test racer.
- **Test seams:** `hooks.py` holds inert defaults (no-op barrier, real process query, no write fault). Only
  `updater/tests/support/test_worker.py` assigns them. The product package never assigns them and reads no
  environment variables, and the shipping worker rejects every test option.
- **Result:** final run 157/157 PASS (2026-10-17 12:32–13:12Z), with the real process status CLEAR before and
  after every group:

  | Group | Cases |
  |---|---|
  | A — canonical operations | 7 |
  | B — interruption and recovery | 66 |
  | C — newer-data preservation | 5 |
  | D — occupants, substitution, racers | 10 |
  | E — malformed and inconsistent states | 12 |
  | F — same-account ownership | 5 |
  | G — legacy `publisher.lock` | 9 |
  | H — selector, Py2.7 outside SFM | 2 |
  | I — broker classification, Py2.7 outside SFM | 2 |
  | J — A3 and barriers | 10 |
  | K — path lengths | 3 |
  | N — C1 no-op | 10 |
  | X — L-1 additions | 14 |
  | W — product worker entry | 2 |

  - **Fixtures:** the G1/G2/G3 sidecars and manifests recompiled through the product reproduced P1
    byte-for-byte.
  - **Live installation:** the before/after fingerprint is identical (authority files, listings, `gameinfo`,
    the P0 235-file closure), and no updater directory was created.
- **Expected outcome changes from P1** (by design):
  - **J1–J6:** RUNNING/UNKNOWN now refuse at the pre-lock gate with nothing created. P1's post-lock ABANDONED
    path is covered by X5.
  - **K1 at P1 depth:** now refused by the approved path budget. Long transaction paths are covered by K3.
- **Recorded deviations (preserved in the evidence):**
  - **SFM open during `shake1`.** A real `sfm.exe` was running that the session had not started; no test
    launched SFM. Groups A and N were refused at the pre-lock gate with nothing created, then rerun with SFM
    closed. This is an unplanned observation, not L-6 group 2 qualification.
  - **`shake2`** was stopped on the owner's "Pause".
  - **`/tmp` slip:** two small path notes were written to the user temp folder and deleted immediately.
  - **C1 §5 broker driver:** not rerun (the consumer library is unchanged). I1/I2 were rerun.
- **Scope of the PASS:** scratch qualification of the headless backend on E:/NTFS. It does not cover native SFM,
  either consumer's UI, real-SFM detection, power loss, cross-user behavior or release eligibility.
- **L-2:** NOT STARTED / REQUIRES AUTHORIZATION. **L-3 … L-6:** NOT STARTED.

Previous milestone: **Offline Updater v1 contract checkpoint (documentation only), 2026-10-16: APPROVED.**
After Astra's October 16 proportionality review, the owner approved the offline-v1 direction, and the designer
accepted the reconciled drafts. This checkpoint made no code, test, SFM run, WPR/ETW, installed-file or authority
change. Base: `27aa672…`.
- **Authority (GitHub, `updater_qualification/design/`):**
  - `OFFLINE_UPDATER_V1_CONTRACT_AMENDMENT.md`: the superseding owner decision for v1. It supersedes R2 and the
    2026-10-12 owner decision only where its §3 explicitly says so. It is a repository copy of the approved
    draft `e07c3e10…`, differing only in approval wording and resolved placeholders (its §9).
  - `L_IMPLEMENTATION_AUTHORIZATION_CARD.md`: the L-1 … L-6 plan and the five-group release qualification.
    It is a copy of the approved draft `d540d0ef…` (its §9). Approving it authorizes no increment.
  - R2 (`61cf8ed5…`), the 2026-10-12 owner decision and the ruling stay byte-preserved.
- **Approved:**
  - **Offline v1:**
    - The updater installs only with SFM closed.
    - Candidate preparation may run with SFM open, and writes only to updater-private staging.
    - Installation refuses a RUNNING or UNKNOWN process state.
    - There is no live updating, service, launch interceptor or runtime handshake.
  - **Three equally prominent primary actions:** Get Official Data, Rebuild My Data and Use Another TXT. The
    labels have no ellipses, and all three go through the one protected backend.
  - **Single Windows account:** the qualification boundary is one Windows account. The physical installation
    lock is retained; access-denied or ambiguous ownership refuses; there is no per-user lock.
  - **Superseded testing requirements:** the R2 C10 hard-reset testing requirement and the broad C11
    live-overlap testing requirement are superseded within the offline-v1 qualification contract. They are
    replaced by process-interruption recovery qualification and the offline refusal boundary. They are
    **not passed** and are not recorded as waivers.
  - **Installation mechanism unchanged:** R2 C4–C9 and C12 remain substantively unchanged. That covers
    protected source identity, no-clobber moves, the approved move order, handles held through verification,
    checked writes and flushing, journaling, evidence-based recovery and refusal on unexpected state. D and E
    are unchanged too.
- **Dispositions (earlier verdicts unchanged):**
  - **U0B-P2:** removed from the v1 critical path. **NOT PASSED.** Its design and preparation work
    (2026-10-15/16) is private evidence, not committed: WPR calibration C-1R PASS (bounded), BST DMX oracle
    extraction ELIGIBLE (bounded), observation cards R1/R2, and preparation P-1–P-5 with its C1 correction.
    That work is retained unchanged and supports no v1 claim.
  - **Final P2 recorder/comparator correction A–C:** BLOCKED (report `5274d85e…`). Its issues are unresolved
    and are no longer v1 blockers.
  - **WPR/ETW development:** discontinued, not completed.
  - **Broad U0B-P3 native concurrency:** removed from the v1 critical path. **NOT PASSED.** Not started.
  - **Unqualified, published as v1 limitations (Amendment §5):**
    - L-A: unexpected native SFM overlap;
    - L-B: power/cache loss;
    - L-C: cross-user contention;
    - L-D: non-participating writers;
    - L-E: release freshness;
    - L-F: detection timing.
  - **U0B is closed for v1 at the P1 evidence boundary.** U0A PASS (bounded), P0 technical PASS (bounded) and
    P1 COMPLETE / PASS (bounded) are unchanged.
- **L:**
  - **L-1** (the activation/recovery backend plus Rebuild My Data, without a GUI): **READY FOR AUTHORIZATION /
    NOT STARTED** at this checkpoint. It has since been completed (see Current milestone).
  - **L-2 … L-6:** NOT STARTED; each needs its own authorization.
  - **Release:** requires the card's five qualification groups to pass on the shipping candidate, each group
    covering all three actions.

Previous milestone: **U0B-P1 — Real-artifact scratch qualification (ruling §6): COMPLETE / PASS (bounded), 2026-10-14.**
Owner-approved after the C1 correction and an independent audit (Astra; private, not committed), which
found both reopening defects resolved: bounded technical PASS for the no-op correction, broker
qualification and regression sufficiency. Scope: R2 activation/recovery on real SFM Master and sidecar
artifacts in disposable scratch roots on the installation volume (fixed NTFS), plus the broker entry point
under SFM's Python 2.7.5 outside SFM. **Not** native SFM, consumer-UI, concurrency, durability or release
qualification. P1/C1 is **not** fully procedurally compliant (see Procedural).
- **Original campaign (2026-10-12; prototype `537739ff…`, controller `4affc60b…`):** 130 final PASS =
  125 initial PASS + 5 fresh reruns after a harness selector-oracle correction; the 5 original FAIL
  records are preserved. No demonstrated data-loss finding.
  - Cases by ruling §6 category: canonical import/rebuild/no-op/custom source 7; interrupted
    forward/reverse and killed recovery 66; newer-data preservation 5; occupied
    destinations/substitution/competitors 10; malformed/inconsistent 12; alias/single owner 5; legacy
    `publisher.lock` 9; selection 2 (+70 embedded selector checks); sharing classification 2
    (library/file level only); process status/barriers 10; path length 2.
  - These results stay attributed to `537739ff…`. A3/A4 (no-op) are superseded by C1 N1/N2.
- **Reopened 2026-10-13** on two gaps (verified-no-op bypass of the process gate and transaction
  records; sharing classification below broker entry-point level). **C1 correction, 2026-10-14**
  (corrected prototype `8871f13756d132eae0584190885198c7b6f2c8c62b3bd543a809d64660b4b425`; diff local
  to the no-op branch plus three helper functions):
  - **10 targeted no-op PASS:** CLEAR no-op (rebuild; import of identical bytes); injected RUNNING
    and UNKNOWN (zero exclusive authority opens); pending transaction before and after protection
    (refuse, existing recovery, then NOOP); unknown schema; finished records; unfamiliar entry;
    protection conflict (sharing violation).
  - **2 regression PASS** (import G3; RUNNING full activation) and **1 broker-entry PASS** (14 checks).
  - **2 controls** on the original prototype reproduced both defects; they are not counted as C1
    passes. Shakedown and final runs gave identical verdicts.
- **Gaps CLOSED within P1's tested scope:**
  1. **No-op (R2 C4/C7/C8, A3):** installation lock → transaction inspection → CLEAR process decision →
     exclusive identity-bound Master/sidecar/manifest verification → final inventory verification
     precede a truthful NOOP. Pending or unfamiliar transactions refuse until handled through the
     existing recovery.
  2. **Broker:** real `get_broker()` / `acquire_or_reuse_views()` (Normalizer call shape) under Python
     2.7.5 outside SFM: protected sidecar on a cold broker → `SidecarMissing` with no provider or cache
     admission; reacquisition after release; warm reuse of the same view with no provider open;
     protected Master → `MasterUnreadable` at H0, warm or cold.
- **Audit qualifications (carried):**
  - scratch authority file bytes were not independently rehashed from the audit archive; identities,
    manifests, source and traces were verified;
  - the 49th C1 harness file is the closeout summarizer; the original-prototype reference is inside
    the verified 48-file frozen manifest;
  - protected-Master results show broker behavior at H0, not that all existing detached consumer
    operations stop;
  - ordinary shared previews and a brief legacy `publisher.lock` probe precede the process gate; the
    exclusive Master/sidecar/manifest verification does not;
  - file hashes establish content identity, not independently authenticated test-plan creation times;
  - `intent_schema()` has a non-blocking diagnostic weakness for JSON scalar/list input; it remains
    fail-closed. Pre-production diagnostic hardening, not a P1 blocker;
  - the protected-sidecar `SidecarMissing` diagnostic remains potentially misleading.
- **Real artifacts:** compiling the preserved G1 Master in scratch reproduced the live sidecar
  `bcd97641…` and manifest `d810d648…` byte-for-byte (G1 is regenerable); G2 compiled to `cd370f67…`;
  the semantic test Master **G3** (`5635ecf3…`, sidecar `3a16e945…`) moves exactly one control
  (`Left PupilDown`, `Face/Eyes` → `Face/Expressions`).
- **Claims, limited to the tested cases and interfaces:** interruption at the tested barriers and during
  recovery recovered to the exact old or new set, idempotently; user edits after interruption gave a
  truthful CONFLICT; occupants at tested destinations were never overwritten; the 15 tested competing
  operations during protection were refused; tested malformed states were refused or reconciled; one
  lock owner across the tested aliases. `publisher.lock`: recognized and preserved in place; tested
  results cover **lock acquisition only, not full legacy-publisher exclusion**. RUNNING/UNKNOWN cases
  were **injected process-query responses**, not real running-SFM detection.
- **Findings for P2/L:** F1: the Python 2.7 consumer libraries failed to open the tested **sidecar** path
  at 260 characters (259 worked); no Master threshold was measured; the live maximum is 175. F2: a
  protected sidecar is reported as `SidecarMissing` (library and broker level). F3: an occupant in an
  authority slot yields a truthful CONFLICT, not ROLLED_BACK. F4: holding `publisher.lock` makes a
  legacy lock acquisition fail at open with a generic message. C1: while the Master is protected even a
  valid cached view is refused at H0.
- **Live installation:** never written or locked. Fingerprints (4 authority files vs pins, 235 closure
  files, `gameinfo.txt`, `cfg` listing) showed no detected change at every P1 and C1 check; this is not
  continuous proof of no transient write.
- **Evidence (local only, not committed):** in the operator's approved local Codex evidence directory.
  - P1: report `bb91b373e89a097187140587583adc115924bfca23006f3b97e25cdf63e62c6f`, case matrix
    `0aaa4da8…`, I/O manifest `ac0a27ac…`, scratch inventory `1928aab8…`, footprint log `22daffb6…`,
    harness list `db043719…`.
  - C1: report `36b9acf24cef8dfdf7139f4c5a2f9cec0f4680ae0fcaffb41117ebf61292c756`, case matrix
    `00a7e1e3790a820ff4a1d725b3ad376ac01060a10fbb1ee8710be868d633e87d`, frozen harness list
    `377d84418268f3d7974f83879db33d2258589d312b75529229d39b494e99f431`, test plan `3cae5d16…`,
    prototype diff `20f6ce4e…`, final preflight `cb6cc13d…`.

  The P1 report's "broker-level" (I1/I2) and "Master or sidecar" (F1) wording is superseded by this
  entry; hashed reports are not edited.
- **Procedural (owner dispositions: P1 2026-10-13, C1 2026-10-14; both accepted as non-blocking).**
  - P1: a `git fetch` rewrote `FETCH_HEAD` before closeout; a mistaken empty shell here-document used a
    transient temporary file; agent-harness session files. Unattributed: 58 empty temporary
    directories and a `.ses` modification in the user temp folder. Unresolved: the footprint log
    records its audit at about 22:15 local but lists a 22:47 `.ses` change.
  - C1: the first C1 preflight found SFM running (not agent-started) and stopped before any scratch
    execution. Execution resumed under a separately issued designer authorization to resume after SFM
    closure; the resume preflight found process status CLEAR. Writes outside scope: agent-harness
    session files (including one background task output). Two empty temporary directories appeared in
    the user temp folder during C1 activity; no creator is established. Recurring background temp-file
    activity was also observed and is unattributed.

  P1/C1 is **not** fully procedurally compliant. The dispositions attribute no unexplained activity,
  waive no technical requirement and authorize no future out-of-scope write.
- **U0B-P2, P3 and L (at P1 closeout): NOT STARTED.** See Current milestone for the offline-v1 dispositions.

Previous milestone: **U0B-P0 — Read-only installation, exposure and evidence preflight (ruling §7):
technical acceptance PASS (bounded), 2026-10-12.** Owner disposition (2026-10-12): the
write-footprint deviation is accepted as non-blocking. P0 keeps its bounded technical PASS but is not
described as fully procedurally compliant, and its evidence and temporary files are preserved.
- **Scope held:** run from `a274b7c…`. SFM was not running and was never launched. Non-elevated; no
  tracing, compilation, tests, settings, installed-file or authority change. The live authority was
  hashed three times during the inventory and was unchanged.
- **Acceptance:** the designer found all seven ruling §7 acceptance items satisfied. PASS is not
  native safety, backup recoverability, U0B or release qualification.
- **Evidence (local only, not committed):** the P0 report (`7f3b26e2672af6101ffc7d7d1b8a33fd31daeb906adcd2b120f61044c6fe8a14`)
  and inventory (`6516bdb3c66e29843c45911599294b42c840eecf8e10bb2c375951d9987594d1`), plus a private
  write-footprint note, in the operator's approved local Codex evidence directory. They contain
  workstation paths and installation details, so they stay out of GitHub.
- **Procedural finding (owner-accepted as non-blocking):** P0 permitted writes to one evidence folder
  only. Outside it, during P0:
  1. two working hash-list files in the agent session's temporary scratchpad (disclosed in the
     report);
  2. two tool-output files saved automatically by the agent harness in its session store, one a
     duplicate of item 1 (not disclosed in the report);
  3. a `git fetch` at P0 start rewrote repository metadata (`FETCH_HEAD`); no tracked file, ref,
     index or object changed.

  All still exist, unmodified. They contain hashes, file names and listings, with no credentials. P0
  is therefore **not** described as fully compliant.
- **Verified installation identities** (all match pins and repository bytes):
  - Authority: G1 Master `ac45e5c1…`, `manifest.json` `d810d648…`, the only sidecar `bcd97641…`,
    and an empty `publisher.lock` (`e3b0c442…`).
  - Consumers: CPM `4e35f292…`, launcher `996ca483…`, Normalizer `1f4ec5a2…`, adapter
    `e96e21b5…`, projection `9b077a1b…`, probe v3 `ce4ace98…`, and the shared authority package and
    reader.
  - Bytecode: 25 `.pyc` files carry Python 2.7 magic and timestamps matching their sources.
- **Findings:**
  - **Effective Master:** statically `usermod/cfg/sfm_defaultanimationgroups.txt` (usermod first in
    `gameinfo.txt` SearchPaths; launch options set no `-game`/search path). The Normalizer's
    absolute path is demonstrated in I/J logs. CPM logs a relative path, and the process working
    directory has never been recorded.
  - **Stray copies:** 19 other Master-like files are inert by search-path rules (statically): 12
    outside the live `cfg` (stock `platform`, model packs, a probe backup) and 7 differently named
    TXT files in `cfg`. The P0 report says "eight" for the latter; the inventory shows seven.
  - **Selector:** reads only `*.sfmsidecar` (first matching source hash wins). It ignores
    `publisher.lock` and `manifest.json`, and the winning artifact is not logged.
  - **`publisher.lock`:** created by `tools/sfm_master_sidecar/publisher.py`. Proposed rule:
    recognize in place, never move or delete, and refuse if it is held. Implementation remains to
    qualify.
  - **Ordinary SFM writes:** `cfg` config files and stats at exit; HKCU Qt settings;
    `<document>.autosave` beside the open document (from timestamps, not traced); product logs (the
    Normalizer log is truncated on each run).
  - **G1 sidecar:** `bcd97641…` existed only in the live installation, not in the repository. A
    hash-verified second-volume copy is required before any step that could touch the authority.
    (Since P1: preserved locally and shown to be regenerable from the Master.)
  - **Path budget:** the live sidecar path is 175 characters; with about 172 of transaction overhead
    that is about 347 (over 260). Long paths are enabled on this machine.
  - **Fixture:** the K/item-8 fixture is still at its pin `197e6011…`.
- **Unresolved after P0:**
  - **Native Master access:** path, timing, share mode, and behavior when the Master is locked,
    absent or mid-replacement are UNKNOWN; no file-access trace exists. Observing them needs
    elevation (built-in WPR), a tracer install, or a test-only probe, and each needs approval.
  - **CPM absolute Master target:** inferred only.
  - **Semantic oracle:** there is no Master pair with a deliberate semantic difference (G2 is G1
    plus one LF), no oracle combining group tree and channels/keys, and no real sidecar bytes in the
    repository. (Since P1: the scratch G3 pair exists locally; the native group-tree plus
    channel/key oracle remains for P2.)
  - **Bytecode:** content equivalence is shown by timestamps only.
  - **Antivirus:** Defender real-time protection is on; exclusions are unreadable without elevation;
    interference is untested.
  - **Concurrency (C11/G), durability (C10/G hard reset) and cross-user contention:** unqualified,
    not waived.
  - **Restoration:** plans are proposed only; backup recoverability is unproven.
  - **R3-A1 evidence:** the source document behind "native rereads the Master" is absent from the
    repository.
- **Next proposal (at P0):** P1, real-artifact scratch qualification. It was since authorized and
  executed (see Current milestone).

Previous milestone: **Updater design checkpoint (documentation only), 2026-10-12** (U0B-P0 was
authorized there and has since been executed, above).
The owner approved the updater design adjudication and authorized U0B-P0 as the next milestone. No
code, test, SFM launch or installed-file change was made; baseline `1a2bbd1…`; committed and
verified on GitHub as `a7739736366bb057d51bffe4e74d1a5c74614024`.
- **Authority (GitHub, `updater_qualification/`):**
  - `design/OWNER_DECISION_2026-10-12.md`: the owner record; governs only its explicitly
    approved items and lists original and committed SHA-256s;
  - `design/SFM_Character_Tools_Updater_Blueprint_R2.md`: governs the updater protocol except as
    approved in the owner record; byte-identical to the original (`61cf8ed5…`, CRLF, `-text`);
  - `design/SFM_Updater_Final_Architectural_Ruling_2026-10-12.md`: Astra's final ruling; a
    **sanitized derivative** (original `b985e868…`, copy `d63b886b…`; one workstation path on
    line 213 replaced);
  - `reviews/U0B_Independent_Adversarial_Audit_R2_Reconciled.md`: evidence, not approval; sanitized
    (original `7c552f74…`, copy `c5ab370c…`; one personal name on line 3 → `@OWNER`);
  - `SHA256SUMS.txt`: committed-copy digests.
- **Approved:** keep R2 C6–C8 and C12 unchanged; A3 (UNKNOWN process status refuses; barriers fail
  closed); `publisher.lock` direction: preserve and recognize a verified legacy file in place (no
  migration or deletion).
- **Not approved / on HOLD:** A1 and A2 directions only, with no qualification or hard-reset waiver;
  A4 deferred (cross-user unqualified, no test account); N1-first rejected; R2 C10/G hard-reset and
  C11/G concurrency blockers not waived; live fault injection HOLD.
- **U0B-P0** (ruling §7): read-only preflight, authorized to write only its report and inventory,
  to one new folder in the operator's approved local Codex evidence directory, outside the
  repository. It has since been executed (see Current milestone).
- **U0B-P1, P2, P3:** each needs separate authorization.

**U0A — Disposable Windows activation feasibility (pre-L; Astra Updater Blueprint R2, Stage 0
file half): PASS (bounded), 2026-10-12.** This is experimental evidence, **not** production
qualification. No updater, GUI, packaging or install exists; no product, authority or SFM file was
touched (production fingerprint unchanged).
- **Setup:** baseline `af4c8d6…`; R2 sha `61cf8ed5…` (owner-supplied; committed byte-identical at
  the updater design checkpoint); Windows 10 22H2 19045.6466, NTFS, non-elevated; disposable
  synthetic `usermod\cfg` trees only.
- **Results:** 256 PASS, 1 NOT RUN, 0 FAIL (257 recorded). U0A-1 6/6, U0A-2 83/83, U0A-3 8/9
  (cross-user NOT RUN), U0A-4 5/5, U0A-5 134/134, U0A-6 20/20.
  - *Correction (2026-10-12):* the grand total first recorded as 255 PASS was an arithmetic error.
    The raw verdicts always summed to 256. Documentation-only correction; no rerun; verdict
    unchanged.
- **Confirmed under process termination:**
  - protected own-handle no-clobber rename (`GENERIC_READ|DELETE`, share 0; `FileRenameInfo`,
    `ReplaceIfExists=FALSE` → 183 on an occupied destination; 17 cross-volume, no copy);
  - every racer refused during protection, and every pre-protection mutation detected through the
    held handles;
  - one lock owner across 8 path aliases;
  - an exact final set verified independently;
  - every kill point (including during recovery) recovers to a verified old or new state, or to a
    preserved conflict; recovery is idempotent.
- **Unproven:** power-loss durability, cross-user and standard-user tokens, real disk-full, AV
  interference, and all real-SFM behavior (U0B).
- **R2 remains viable.** Refinements F1–F9 are for L. Notably, F4: the live `publisher.lock` in
  `sfm_shared_authority` would be refused as unfamiliar content (owner direction since approved:
  preserve and recognize it in place; see above); F7: transaction paths add ~172 characters.
- **Evidence:** `updater_qualification/u0a/U0A_WINDOWS_ACTIVATION_FEASIBILITY_REPORT.md`, plus
  `harness/` and `evidence/` (redacted).
- **U0B:** P0 technical PASS (bounded; deviation owner-accepted as non-blocking); P1 COMPLETE /
  PASS (bounded, scratch + broker entry point; reopened 2026-10-13, corrected by C1 2026-10-14);
  P2 and broad P3 removed from the offline-v1 critical path, NOT PASSED (2026-10-16; see Current
  milestone). U0B is closed for v1 at the P1 evidence boundary.

**K — Integrated CPM/Normalizer product workflow qualification: COMPLETE / PASS (2026-10-10).**
K PASS = K1 PASS (K1A2, 53/53) + K2 PASS (K2A1, 39/39), on CPM `4e35f292…` and Normalizer
`1f4ec5a2…`. Exact production CPM/Normalizer and exact G1 authority remain installed. **L: NOT
STARTED.**
- **K2A1:** one fresh SFM process (PID 41240) from `13f57c1e…`:
  - **CPM first:** CPM created the one broker `0x3101aa50`; Save and the Normalizer's `shot9` run
    on G1 followed.
  - **G1→G2 switch:** exact G2 via the frozen tooling with both tools idle. The change alone
    caused no acquisition or rebuild.
  - **Normalizer touched G2 first:** a new G2 cohort, no G1 reuse.
  - **CPM recovery:** exactly one `generation-mismatch` refusal (no mutation, no replay), then one
    rebuild to healthy G2. The deliberate G2 Apply committed a real change and its Undo restored
    the operator's value.
  - **G2 alternation:** the Normalizer's `shot3` run passed on G2; Delete passed; CPM closed; exit.
  - **Restoration:** `S2 RESTORED EXACT G1`; app and fixture unchanged; idle at every probe;
    `mem_ok` never False. The adjudication-script correction is recorded (design §18).
- **Evidence:** design §17 (K1), §18 (K2 and K completion); redacted raw copies in
  `real_sfm_qualification/cpm_k_integrated/raw/` (K1A1, K1A2, K2A1; `MANIFEST.md`).

Earlier K1 record:
- **K1A2:** one fresh SFM process (PID 36888) from the K-0-amended checkpoint `93317866…`.
  Mechanical adjudication **53/53 PASS** over the sealed evidence; disposition PASS. Proven:
  - **Normalizer first:** it created the one canonical broker `0x338d0630` before CPM existed, and
    CPM then joined it.
  - **Coexistence:** divergent shots (CPM playhead `shot10`, Normalizer selection `shot9`) and the
    same shot (`shot3`/`shot3`).
  - **Alternation:** 4 Normalizer Selected runs, all PASS on G1 with `mem_ok` True. CPM Body Save,
    Fit + Undo, Body Apply + Undo, Expression Save, Apply + Undo and Delete ×2, all on G1 with 0
    refusals, 0 stale events and no rescope.
  - **Close orders and lifetimes:** close order X (CPM closed after Normalizer runs) and Y
    (Normalizer run while CPM closed); reopen with the same module and run in a new window; exit
    with CPM open. Idle at every probe; both consumers' views were retained.
  - **Resources:** no STOP; private 3,074 → 3,111 MB.
  - **Closeout:** exact G1 untouched; app and fixture unchanged; expected inventory restored.
- **Runbook clarifications** recorded in K1A2: clip-click selection; slider change before a
  same-value Apply; Delete's Favorites `library.json` cleanup (owner option 1). They are carried
  into K2-D4/K2-E4.
- **Evidence:** design §17; redacted raw copies in `real_sfm_qualification/cpm_k_integrated/raw/`
  (K1A1 and K1A2, `MANIFEST.md`).
- **K1 authorized (K2 is not).**
  - **K1A1 — INCONCLUSIVE:** a qualification-tooling false STOP before either product consumer
    executed; not a CPM or Normalizer failure. The baseline probe in a fresh fixture-loaded process
    showed 528 MB free VAS, which tripped the K rule "free VAS < 600 MB". Item 8 D's Normalizer had
    begun with 421 MB free and finished `mem_ok=True`.
  - **K1A1 closeout:** SFM closed with Don't Save; exact G1 untouched; probe removed; expected
    inventory restored; app and fixture unchanged; sealed (local evidence). It is not reused.
- **K-0 amendment:**
  - the VAS STOP is removed and free VAS (probe, Normalizer samples) is recorded as telemetry only;
  - the Normalizer's own `mem_ok=False` is the primary memory/VAS STOP, and the private-bytes
    safeguards are retained;
  - a regression check was added;
  - reader `e137536d…`, manifest `7bf1683a…`, driver `8b302a96…` (manifest pin only); probe
    unchanged;
  - tests: **2.7.5 160/160**, **3.10 191/191**.
  - Design §5.4 and §16.

**Pre-K CPM UI polish pass — LIVE VERIFIED / PASS (2026-10-09).** The final build
**`4e35f29242351317f2f961c27e19d66fcd3355cff964b081431fc2fff1f5b9d7`** is installed and is **the
exact CPM candidate eligible to enter K**.
- **U3** verified it live as a Help wording delta from U2: owner review of the Getting started Help
  ("good looks"), plus a log showing the exact build loaded, Help opened and the close finalized,
  with no authorizations, mutations or refusals.
- It supersedes `7e4686d7…` (U2 LIVE VERIFIED / PASS) only in those two Help paragraphs. The offline
  UI test passes 100/100 and 65/65, and all existing suites PASS.
- Record: `PRE_K_UI_POLISH_PASS.md` §H; outputs in `pre_k_ui_polish_outputs_r3/`.
- K has since run on this build and is COMPLETE / PASS (see above). L: not started.
- Superseded candidates are retained with their records: `7e4686d7…` (U2 PASS) and `5c6e2789…`
  (U1 SUPERSEDED / NO QUALIFICATION VERDICT).
- Item 8 qualified `bfba4d3a…` functionally. That evidence is unchanged, and the UI pass is
  byte-bounded against it.

The pass makes eight presentation changes:
1. the owner-supplied woman icon, embedded at 64×64;
2. **Character Model:** and "Choose a character model" (Refresh Model List unchanged);
3. Help opens with **Getting started**: the character and the playhead workflow;
4. semantic buttons: blue Apply/Fit, gold Favorite, red Delete. In the refinement these are
   **neutral fills with restrained role-colored borders**, and every role uses the neutral disabled
   state;
5. window 580×800, minimum 540×650 (the four tabs fit);
6. Update confirmation copy, with no question icon;
7. Review buttons in a 2×2 grid;
8. **Clear Classification** wording.

No scope, authority, lifecycle, preset, Fit, generation or Normalizer behavior changed.

Offline results for `7e4686d7…`:
- all existing convergence/R14/R15 suites PASS under 2.7.5 (real Qt) and 3.10;
- `test_cpm_app_ui_polish_pass.py` passes **99/99** (2.7.5) and **64/64** (3.10), including byte
  reconstruction from `bfba4d3a…` and real-Qt pixel checks of fills, borders and disabled states.

(First candidate `5c6e2789…`: 96/96 and 61/61.)

The exact-build historical tests (item 6, item 7 reconstruction, item-8 probe/driver) refuse the new
bytes by design and were not edited. Record: `cpm/qualification/PRE_K_UI_POLISH_PASS.md`; outputs
in `pre_k_ui_polish_outputs_r2/` (first candidate: `pre_k_ui_polish_outputs/`).

**Live checks:**
- **U1** (`5c6e2789…`): SUPERSEDED / NO QUALIFICATION VERDICT.
- **U2** (`7e4686d7…`): **PASS**, on the owner's hands-on review ("Looks good") plus the log. The log
  shows the exact build loaded, the window shown, Help opened, and the close finalized, with no
  authorizations, mutations or refusals. Its only messages were the unchanged "No current shot." and
  "Choose a model first." guards.
- **U3** (`4e35f292…`): **PASS** as a Help wording delta from U2. The owner reviewed the Getting
  started Help; the log shows the exact build loaded, Help opened and the close finalized. Its only
  message was the expected "No current shot." at launch.

No model was selected in U2. Enabled border colors, the Update confirmation and Review rest on the
offline real-Qt checks and on U1 hands-on use. Each deployment was verified with SFM closed: Scripts
difference = the app line only; authority exact G1. Details: `PRE_K_UI_POLISH_PASS.md` §0.3.

Previous milestone: **§22 item 8 — COMPLETE / PASS** (qualifies `bfba4d3a…` only; unchanged). Exact candidate
`bfba4d3a54cf42d5eb744040e95f110d24e0870fcfcbb35d54e2885f9560e2b5` was qualified in one fresh
real-SFM Python 2.7.5 process. The campaign covered:
- focused post-cleanup operation;
- persistence and native Undo;
- ordinary Fit;
- generation refusal and rebuild;
- canonical idle ownership;
- Normalizer coexistence;
- close/reopen behavior.

Historical forced-rollback and queued-Fit evidence is retained with its existing qualifications.
Exact G1 was restored. The temporary item-8 probe, campaign pointer and other qualification-only
deployment were removed. **The exact qualified candidate remains installed.** No new convergence
blocker was found. At that checkpoint CPM was eligible to enter K, and K and L had not started (K
has since completed, PASS, in fresh SFM processes; L is NOT STARTED). This checkpoint does not
decide L's final installation layout.
(Superseded for K entry by the pre-K UI pass: the build eligible to enter K is now the live-verified
`4e35f292…`.)

- **Attempt `I8A1` (2026-10-08, from `d4ad3cf`):**
  - one SFM process, PID 36912;
  - module `0x30b6b490`, class `0x307ed158`, run `20261008-135639-pid36912`;
  - broker `0x310a7810`;
  - windows `0xce494350` → `0x310bea30` → `0x30b87418`;
  - fixture `testscripts.dmx` (`197e6011…`): Krystal on `shot10`, Mia on `shot3`; not saved.
- **Phases A–F PASS.** Mechanical adjudication 34/34, from 30 probe records, the CPM-log excerpt,
  the Normalizer log, and the generation and library records.
  - **A — load and reuse:** `bfba4d3a…` loaded through the private loader; the second click gave
    `PROD_R15_WINDOW_REUSED` with no acquisition.
  - **B — Fit:** authorized on G1; 34 literals; committed-verified with 26 mappings and 7 warnings;
    one release `ok=True`; `changed=1 partial_changed=1 failed=0 unattempted=0`. Only the target
    changed, and Undo restored exactly.
  - **C — persistence and Undo:** Mia scope 46/58/4. Body Save/Update/Apply and Expression
    Save/Apply all equal their readbacks; each Undo restored exactly; library changes stayed within
    the footprint.
  - **D — Normalizer:** Selected `shot3` PASS/PASS, `mem_ok` True 15 / False 0. One broker served
    both projections. Apply and Save continued without reselection, refusal or rebuild.
  - **E — generation transition:** a Save opened under G1 and G2 was activated at 19:46:45 with the
    prompt open. The Save was refused with `generation-mismatch`: no `PROD_SAVE`,
    `durable_commit=None`, libraries E1 = E2 = E3. Only then did one rebuild to healthy G2 happen.
    A deliberate G2 Save was authorized on G2.
  - **F — close/reopen and exit:** Escape and ✕ closes finalized; the reopen kept the same
    module/run under the G2 scope. Idle 0/0/0 at every checkpoint (broker totals: opens/closes
    7/7, views 5).
- **Resources:** private bytes 3,067.8 → 3,103.3 MB (about +35 MB over about 6.5 hours, including
  about 9 MB for the Normalizer). The two closed states after the reopen were equal, with handles,
  GDI and USER flat.
- **Restoration and disposition:** exact G1 restored (Master `ac45e5c1…`, manifest `d810d648…`,
  sidecar `bcd97641…`). The probe and pointer were removed. PASS disposition: the installed app is
  `bfba4d3a…`. The final Scripts inventory differs from the accepted Session 4 inventory only by the
  app line.
- **OWNER-1 historical files:** present and inert; never loaded, never used as authority.
- **Deviation (no effect):** the operator ran the installed Session 1 probe once before A5. Its
  broker counters were unchanged and it caused no acquisition.
- **Evidence:**
  - `real_sfm_qualification/cpm_item8_post_cleanup/ITEM8_EVIDENCE.md` §6;
  - redacted raw files in `raw/I8A1/` (82 files; `raw/MANIFEST.md`).

Previous milestone: **§22 item 7 — COMPLETE: diagnostic/development logging reduction; offline
qualification PASS** (candidate `bfba4d3a…`; design and evidence
`ITEM7_DIAGNOSTIC_LOGGING_REDUCTION_*.md`; manifest `cbb3010b…`; reporting constants removed,
superseding item 6's retention; Q1 parity oracle retained disabled). Its qualification is unchanged.

Previous milestone: **§22 item 6 — COMPLETE: historical authority cleanup; offline qualification
PASS** (candidate `1e866871…`; design and evidence `ITEM6_HISTORICAL_AUTHORITY_CLEANUP_*.md`;
manifest `a9264794…`). Its qualification is unchanged.

Previous milestone: Real-SFM Session 4 (forced rollback-verification qualification, handoff §22
blockers 4–5). **Status: COMPLETE — PASS.**
- S4A (Body Apply): PASS — CONTROL (authentic Abort, rollback verified), GATE (authentic verifier
  True, harness substitutes False → production recovery-unverified), ordinary Apply.
- S4F (Clothing Fit): PASS — CONTROL (`not-committed`), GATE (`abort-unverified`), ordinary Fit and
  Undo.

Evidence: `real_sfm_qualification/cpm_session4/SESSION4_EVIDENCE.md`, raw outputs in `raw/`.
Runbook: `SESSION4_RUNBOOK.md` at `b65c085`; harness `45c44f3d…`.

Sessions 1–4 remain complete (evidence for app `9a78fc96…`). R15 and R14 remain CLOSED.

## Current state
`master`. Before item 6 the product was unchanged since `00d0d83` (last commit touching `cpm/app`,
`cpm/baseline` or the adapter/projection). Items 6 and 7 changed only the mutable app
(`9a78fc96…` → `1e866871…` → `bfba4d3a…`); the launcher, baseline, adapter/projection, shared
package, Normalizer, Master and sidecars are unchanged. Item 8 (real SFM) changed no repository
product file. The pre-K UI polish pass changed only presentation in the app (`bfba4d3a…` → `5c6e2789…`, refined to
`7e4686d7…`, then the Help-wording build `4e35f292…`, which is installed and was K-qualified). U0A
added only experiment/documentation files under `updater_qualification/u0a/` (plus a scoped LF
`.gitattributes` entry for them). The updater design checkpoint added only documents under
`updater_qualification/design/` and `reviews/` plus `SHA256SUMS.txt`, scoped `.gitattributes`
entries, the U0A report's tally correction and this Ledger. U0B-P0 changed no tracked repository
file or installed file; its evidence is local only, and the P0 closeout changed only this Ledger.
U0B-P1 likewise changed no tracked repository file or installed file. Its harness, scratch run and
evidence are local only. Its closeout, the 2026-10-13 reopening reconciliation and the 2026-10-14
final closeout changed only this Ledger. The C1 correction (2026-10-14) likewise changed no tracked or
installed file; its corrected prototype, harness, scratch run and evidence are local only. The U0B-P2
design and preparation work changed no tracked or installed file; its evidence is local only. The Offline
Updater v1 checkpoint (2026-10-16) added only the amendment and L card under `updater_qualification/design/`,
their `SHA256SUMS.txt` entries, scoped `.gitattributes` entries and this Ledger. The L-1 checkpoint
(2026-10-17) added only the new `updater/` tree (product package, test-only suite and `updater/SHA256SUMS.txt`),
a scoped LF `.gitattributes` entry and this Ledger. No existing tool, CPM, Normalizer, Blueprint, amendment or
card file changed, and no installed file changed. The L-1 scratch run and evidence are local only. The L-2
checkpoint (2026-10-17) changed only files under `updater/` (adding `official.py` and
`release_tools/make_official_package.py`, regenerating `updater/SHA256SUMS.txt`) and this Ledger. Its scratch
run, the isolated qualification environment and its evidence are local only. The L-3 checkpoint (2026-10-17)
changed only files under `updater/` (adding `discovery.py` and two test-support files, regenerating
`updater/SHA256SUMS.txt`) and this Ledger. Its scratch run, the unsigned `data-v1.0.0` candidate and the evidence are
local only. No release, tag or key exists. The L-4 checkpoint (2026-10-17) changed only files under `updater/`
(adding `gui/`, `supervisor.py`, `staging.py` and one test-support file, regenerating `updater/SHA256SUMS.txt`) and
this Ledger. Its scratch run, screenshots and evidence are local only. The local git remote now uses the renamed
repository URL. The L-4R checkpoint (2026-10-18) changed only files under `updater/` (rewriting `gui/app.py`, adding
`user_backup.py`, the opt-in `--backup-txt` in `worker.py` and one message, updating the tests, regenerating
`updater/SHA256SUMS.txt`) and this Ledger. Its scratch runs, screenshots and evidence are local only. The L-5
checkpoint (2026-10-19) changed only files under `updater/` (adding `compat/`, `runtime_check.py`, `packaging/` and
the software-inventory producer and spec; changing `__init__`, `backend`, `candidate`, `gui/app`, `messages`,
`supervisor`, `worker` and the tests; regenerating `updater/SHA256SUMS.txt`) and this Ledger. Its build environment,
wheels, builds, candidate, scratch runs and evidence are local only. No key, release, executable or deployment is
committed.

**References for transfer:**
- Authoritative R15 design: `cpm/qualification/R15_IMPLEMENTATION_BLUEPRINT.md`, frozen from
  checkpoint `bd169401fba1c04bf24a148cd8e65748ae757912` (unchanged since `382c79b`). Its §13 line
  "R15 remains OPEN…" predates R15 closure; this Ledger is authoritative for status.
- Updater design authority: `updater_qualification/design/OWNER_DECISION_2026-10-12.md` (with R2 and
  Astra's ruling beside it; see Current milestone). It does not change the frozen R15 Blueprint.
- `cpm/qualification/R15_NAMESPACE_ISOLATION_PROPOSAL.md`: superseded, historical only.
- Convergence requirements and the §22 sequence:
  `docs/qualification/CPM_CONVERGENCE_INTEGRATION_HANDOFF.md`.

The Session 4 campaign folders (`S4A`, `S4F`), the probe JSONL and the CPM log are copied,
redacted, into `real_sfm_qualification/cpm_session4/raw/`. The qualification-only rollback harness
was removed after each campaign; the Scripts deployment equals its pre-harness baseline exactly
(`cefc2b88…`), and no `ACTIVE_CAMPAIGN.txt` remains.

The live authority is exact production G1 (Master `ac45e5c1…`, manifest `d810d648…`, one sidecar
`bcd97641…`), last restored and confirmed at K2A1 closeout (`S2 RESTORED EXACT G1`, 2026-10-10),
and re-verified unchanged, read-only, by U0B-P0 (2026-10-12).

**Deployed and verified** (runbook §0; re-verified at the 2026-10-06 transfer checkpoint and by
item-8 `I8-Preflight`/disposition on 2026-10-08 and the U1–U3 deployments on 2026-10-09; the shared package's qualification-only
`projections.py` is intentionally not deployed):
- launcher `996ca483…` as the Scripts-menu entry;
- private app **`4e35f292…`** (final pre-K UI build, LIVE VERIFIED / PASS in U3, 2026-10-09; the
  builds it replaced, `7e4686d7…`, `5c6e2789…` and the item-8-qualified `bfba4d3a…`, are
  preserved, see below) in
  `usermod/scripts/ChadChan3D_CPM/` (outside `scripts/sfm`, no `__init__.py`);
- probe v3 `ce4ace98…`.

Rollback chain, held in the local U3/U2/U1 attempt folders: `7e4686d7…` → `5c6e2789…` →
`bfba4d3a…`. `bfba4d3a…` can also be restored from git (`2fe9a27`). The previous app `9a78fc96…` remains restorable from git (`9d405c8`). The item-8 probe and campaign
pointer are not deployed. The Scripts deployment equals the accepted Session 4 inventory
(`cefc2b88…`) except the private-app line (U3 inventory `59b8f28b…`). The live authority is exact
production G1. Any later deployment change follows the R15 restart rule.

The step-9 G18AN menu copy has been removed. The pre-R15 app `664a660c…` and probe v2 are archived
outside `usermod/scripts`.

Unchanged (byte-pinned by the R15 suite):
- the baseline `3326024d…`;
- the Normalizer `1f4ec5a2…`;
- the adapter `e96e21b5…` and projection `9b077a1b…`;
- the shared package;
- the Master `ac45e5c1…`;
- R14 private ctypes.

## Verified (real SFM)
Evidence:
- `SESSION1_RUN1_RECONCILIATION.md` (2026-09-28);
- `SESSION1_COMPLETION_EVIDENCE.md` (2026-09-29);
- `R15_SESSION1_ADDENDUM_EVIDENCE.md` (2026-09-30; raw outputs in `cpm_session1/r15_addendum/`).

| Session 1 item | Status |
|---|---|
| Normal CPM operation | PASS |
| Native Apply + Undo (incl. no-op) | PASS |
| Body Save / Update | PASS |
| Expression Save / Update / Apply | PASS |
| Review / Reclassify (Ayane, genuine miss; durable edit and rebuilt classification reported) | PASS |
| Ordinary Clothing Fit + Undo | PASS |
| C10 same-process broker | PASS |
| Simultaneous Normalizer coexistence | PASS, with no CPM scope selected (Session 1) **and with an active CPM scope (R15 addendum)** |
| Resource / latency | PASS (complete) |
| R14 ctypes isolation | CLOSED |
| R15 namespace isolation (Session 1 addendum, P1–P15) | **CLOSED — PASS** |
| Session 2 S2-A_R2: open-window G1→G2 replacement (2026-10-05) | **PASS** |
| Session 2 S2-B_R2: G1→G2 during a Save prompt (2026-10-05) | **PASS** |
| Session 3 S3: queued Fit, G1→G2 between targets (2026-10-06) | **CORE PASS** |
| Session 3 S3_ADD: fresh Fit committing under G2 (2026-10-06) | **PASS** |
| Session 4 S4A: forced Body Apply rollback-verification control + gate (2026-10-06) | **PASS** |
| Session 4 S4F: forced Clothing Fit rollback-verification control + gate (2026-10-06) | **PASS** |
| §22 item 8 `I8A1`: post-cleanup candidate `bfba4d3a…`, Phases A–F (2026-10-08) | **PASS** |

- **Clothing Fit detail:**
  - `Gfit` was authorized.
  - The stage requested 34 literals, more than the 26 source literals, so target-only vocabulary
    was included.
  - The planner produced 26 valid mappings (7 unmatched-target warnings).
  - The stage committed and verified, and its lease was released.
  - Undo visually restored the target.
- **R14:** CPM's resource snapshot ran first, then the Normalizer logged `mem_ok=True` at 13/13
  checkpoints (the first run logged `False` at 15/15).
- **R15 addendum (2026-09-30):**
  - **Design:** one thin menu launcher → one stable private `chadchan3d_cpm_app` module per SFM
    process → explicit compatible-window reuse (`R15_IMPLEMENTATION_BLUEPRINT.md`).
  - **Offline:** R15 suite 345/345 (2.7.5: real PySide/Qt 4.8 plus a model), 188/188 (3.10); all
    regressions PASS.
  - **Isolation:** `__main__` held no CPM names; private function globals.
  - **Stable identity:** one stable module, run ID and class across:
    - the reused second click (no authority acquired);
    - three close/reopen cycles (✕, Escape, Escape; one close request and one finalization each);
    - the notice step.
  - **Normalizer:** Rebuild Selected Shots on `shot3` with CPM's Mia scope active → PASS,
    `mem_ok=True` 15/15; 0 cross-log lines either way.
  - **Continuation:** without reselection, Apply ×2 committed and disposable Save PASS; no stale
    refusal and no scope rebuild.
  - **Notice and legacy slot:**
    - one reusable non-modal notice;
    - frozen G18AN in the slot was refused and preserved, then isolated CPM opened.
  - **Authority and resources:**
    - idle leases/providers 0;
    - across the cycles: private commit −0.5 MB, handles −10, GDI 0, USER −1 (no accumulation).
  - **Recorded deviations (benign):** the baseline ran before P3; one extra observational probe
    before P15; the console transcript was not retained.
  - **Observation:** one no-op Apply began about 0.2 s before the Normalizer's final report write.
    The PASS rests on later actions; alternation stays with K.
  - **Three findings, all resolved by R15, kept distinct:**
    1. the shared Scripts-menu namespace defect;
    2. the repeated-click re-initialization defect;
    3. the pre-existing Escape/reject teardown defect (discovered during R15).
- **Session 2 S2-A_R2 (2026-10-05, pid 25844, broker `0x32def250`, window `0x3210f580`):**
  - **Generation switch:** G1 `ac45e5c1…` → exact G2 `54413b6c…`, using the frozen Checkpoint I
    functions (complete write-once record set).
  - **No-interaction window held:** no CPM activity between G2 activation (17:55:09) and the
    stale Apply (17:56:10).
  - **A8 stale Apply refused before mutation:** `PROD_CPM_OPERATION_AUTHORIZATION_REFUSED …
    reason=u'generation-mismatch'`; no Undo, mutation, native-commit or Apply outcome;
    `native_commit=None`.
  - **Rebuild only after the refusal:** `…REBUILD_SCHEDULED` at 17:57:17, after the dialog was
    dismissed; one automatic Select Model to G2 `54413b6c…`; the same window; no replay.
  - **A10 deliberate Apply:** authorized under G2 and committed (`BodyTest`, `changed_sides=1`).
  - **Idle authority:** P2–P5 leases 0, providers 0, one window / one watcher.
  - **Restoration:** exact G1 (`exact_match: true` in both the finalization record and the
    independent comparison).
  - **First S2-A attempt (folder `S2A`, 2026-10-01):** procedurally invalid (runbook design
    error). Selecting a preset after G2 activation re-evaluated readiness and rebuilt the scope
    under G2 before Apply. That path behaved correctly but does not qualify the stale-action
    boundary. The folder is preserved; its restoration was exact.
  - **Observation:** the refusal dialog shows the guard's generic copy ("Preset could not be
    applied safely. This preset was not applied."), not the stale-scope message, which is logged
    only. See the stale-scope UI presentation item.
- **Session 2 S2-B_R2 (2026-10-05, pid 23944, broker `0x31141250`, window `0x30466580`):**
  - **Save opened under G1:** Save and its prompt opened at 18:36:40, under G1.
  - **Exact G2 while the prompt was open:** activated 18:40:42; no CPM activity until the prompt
    returned (`Q2_SAVE_POST_CONFIRM` 18:41:04).
  - **Stale Save refused:** the stale G1 Save authorization was refused with
    `generation-mismatch` (18:41:09); no `PROD_SAVE`, no durable phase, `durable_commit=None`;
    library inventories 1 = 2 = 3 byte-identical.
  - **Rebuild without replay:** one automatic rebuild to G2 after the refusal; the same window;
    no replay.
  - **Deliberate G2 Save:** passed, with the library diff exactly the three allowed entries.
  - **Idle authority and restoration:** P2–P4 leases and providers 0; exact G1 restoration.
  - **Aborted `S2B` attempt:** confirmed a normal G1 Save before any switch; the authority was
    untouched and the preset was removed. Its residual `character.json` metadata (`updated_at`,
    `last_validated_provider`) is never read for a decision and `semantic_overrides` is empty, so
    it cannot confound the tested boundary (adjudicated in `SESSION2_EVIDENCE.md`).
- **Session 3 S3 (2026-10-06, pid 26156, broker `0x314d92b0`, window `0x30ee7698`):**
  - **Target 1 under G1:** authorized and staged under G1, committed, released ok before target 2.
  - **G2 between targets:** the Fit was deferred at index 1 behind a modal; exact G2 was activated
    and proven live before resume.
  - **Refused, not mutated:** at resume, the target-2 stage proof was refused
    (`generation-mismatch`); no index-1 stage or commit; no continuation under G2.
  - **Truthful stop:** "Clothing Fit stopped" reported 1 committed target and Undo 1 time
    (`verified_changed=[assaultsuitbody1]`, target 2 unattempted). The target was committed with
    plan warnings, so it is accounted as partial rather than in `changed`.
  - **Undo, rebuild and idle state:** one Undo restored target 1 to pre-Fit (snapshot and visual).
    CPM rebuilt to G2 in the same window. P2–P4 were 0/0/0.
  - **Later G2 Fit:** authorized and staged under G2, then an expected structural skip
    (`loinclothbra_chadfix_071` has no compatible Body mappings). The G2 commit is carried by
    S3_ADD.
- **Session 3 S3_ADD (2026-10-06, pid 2324, broker `0x31419270`, window `0xb92d1c60`):** exact G2
  active before SFM started;
  `assaultsuitbody1` authorized, staged, committed and verified under G2 (`committed-verified`,
  26 mappings, 7 warnings), released ok; result PASS `partial_changed=1 failed=0 unattempted=0`;
  P2–P4 0/0/0; one Undo; exact G1 restoration.
- **Session 4 S4A (2026-10-06, pid 2540, broker `0x30fab290`, window `0x309ae698`):**
  - both injected `BodyTest` Applies authorized under G1, writes inside the open Undo
    (`changed_sides=1`, real precommit predicate True);
  - CONTROL: `PROD_APPLY_ABORT_VERIFY restored=True`, "Can't apply preset";
  - GATE: real verifier True, harness substituted False → `restored=False`,
    `ProdRecoveryUnverifiedError`, "Recovery could not be verified";
  - no `native-commit` or committed outcome; Undo state and `mia1` values equal ARM; 0 adapter
    calls during rollback verification; P2–P5 0/0/0; ordinary `BodyTest` Apply committed.
- **Session 4 S4F (2026-10-06, pid 17544, broker `0x311d72b0`, window `0x30bea698`):**
  - both injected Fits authorized under G1, stage `index=0 gfit=ac45e5c1… literals=34`, writes
    inside the open Undo (`changed_sides=3`, real predicate True);
  - CONTROL: `PROD_CLOTHING_FIT_ABORT_VERIFY … restored=True`, `not-committed`, "Nothing changed";
  - GATE: real verifier True, substituted False → `restored=False`, `abort-unverified`, dialog
    `recovery_unverified=[assaultsuitbody1] unattempted=[loinclothbra_chadfix_071] undo_count=0`;
  - stage lease outstanding (1) during rollback verification, 0 adapter calls, exactly one
    successful `release()`; target 2 never staged; nothing committed; P2–P6 0/0/0;
  - ordinary Fit committed-verified and released ok; one Undo restored it visually.
- **§22 item 8 `I8A1` (2026-10-08, pid 36912, broker `0x310a7810`):** see Current milestone and
  `ITEM8_EVIDENCE.md` §6. Sessions 1–4 above qualify `9a78fc96…`; `I8A1` qualifies `bfba4d3a…`.
- **Measurements (Session 1):**
  - process working set +36 MB across the session;
  - CPM scope 107–166 KB;
  - broker retained 666–888 KB;
  - authorization about 0.02 s; warm stage about 0.02 s; one Fit target 0.146 s; scope build
    1.2–1.5 s.

## Unresolved
- **CPM Quick Launch (not product defects):**
  - Two docking incidents were each seen once and are intermittent and unattributed:
    - a blank dock pane after re-docking, after which Console briefly showed the editor's controls;
    - a floating editor without CPM.

    Neither recurred in later repeated floating and docking, and no cause is established.
  - Coexistence was tested with the audited Extended ASE v1.5 and Autoinit v1.2 only.
  - QL-3 packaging is not started.
- **Offline-v1 limitations (published, not qualified; Amendment §5):**
  - L-A: unexpected native SFM overlap during installation;
  - L-B: power/cache-loss persistence. No hard reset was performed; the constructed-state tests qualify
    recovery logic only.
  - L-C: cross-user contention;
  - L-D: non-participating writers (detection only);
  - L-E: release freshness;
  - L-F: process detection cannot exclude a later launch.
- **Other unproven (U0A/P1 residuals):**
  - real disk-full (simulated only);
  - AV/indexer interference;
  - full legacy-publisher exclusion (only lock acquisition was tested).
- **L design inputs carried forward:**
  - F4: the live `publisher.lock` is preserved and recognized in place;
  - F7/P1-F1: the consumer path budget is below 260 characters. The Master threshold was not separately
    measured.
  - P1-F2: busy-versus-missing messaging. The updater's own messages are in L scope; consumer messaging is
    unchanged K/L product work.
  - P1-F3: authority-slot conflict messaging;
  - P1-F4: legacy-lock fail-closed behavior;
  - real running-SFM detection. P1/C1 and L-1 used injected responses (plus the unplanned L-1 `shake1`
    observation); this is qualified in L-6 group 2.
  - `intent_schema()` hardening: implemented in L-1 (a non-object intent is an unknown schema).
  - CPM and Normalizer behavior after an installation, in L-6 group 5.
- **L-1 implementation items (later L stages; not L-1 prerequisites):**
  - staging under `sfm_character_tools_updater\staging\<id>` is never pruned (about 9.5–13 MB per
    preparation). The cleanup policy belongs with L-4 and must not touch transaction recovery data.
  - `prepared.json` is not authenticated. Install re-verifies exact bytes, reader binding, admission and the
    manifest, but not semantic parity (an L-D case).
  - the path budget measures the resolved installation path, not any longer alias a consumer might use;
  - process detection matches the image name `sfm.exe` only;
  - dependencies load from repository paths (`tools/` and the authority package under `tests/sidecar/…`).
    Their shipping location is an L-5 decision.
- **L-2 items (owner dependency or later L stages; not L-2 prerequisites):**
  - **Owner release dependency:** a production Ed25519 signing key, with only its public key embedded by a
    separate authorized change. Until then the shipping updater refuses all official packages.
  - **L-5 compatibility:** the authority profile `sct-authority-profile-1` is provisional, and the signed
    installed-software inventory (R2 E2–E3) is not implemented.
  - **L-5 packaging:** bundling of `cryptography` and its dependencies.
  - **L-4 staging cleanup:** this now includes official-package staging, about 13 MB each.
  - **Remembered releases:** the record is per installation and not protected against deliberate local
    deletion. First-contact and offline freshness limits apply (L-E).
  - **Release provenance:** the producer's `compiler_build` identifier is fixed. Provenance automation belongs
    with release production.
  - **Carried from L-1:** the alias path budget, image-name process detection and repository-path dependencies
    above still apply.
- **L-3 items (later L stages or release; not L-3 prerequisites):**
  - **Freshness:** a check does not record authenticated sequences that are seen but not prepared. The
    high-water mark advances at preparation. First-contact suppression is not detectable (R2 D4).
  - **Downloads:** download folders were kept (resolved in L-4: removed once prepared). The payload is held in
    memory before writing, within the existing bounds.
  - **Untested until later:** real GitHub asset-redirect hosts (untestable until a release exists);
    proxies (untested); the TLS certificate store (an L-5 packaging decision).
- **L-4 items (later L stages or owner review; not L-4 prerequisites):**
  - **Owner review:** done for the L-4 window; it led to the L-4R refinement and final polish (Current
    milestone), which the owner reviewed and accepted on 2026-10-18.
  - **Older releases:** explicit older official installation exists in the worker (`--allow-older`) but not in
    the GUI. OLDER_ONLY is reported, not offered.
  - **Cleanup race:** cleanup removes by path after re-checking shape. A folder swapped for a link between the
    check and the removal is a residual race inside the user's own installation folder.
  - **L-5 packaging:** the one-folder package, the launcher and the shipping worker command; the Python, Tk and
    `cryptography` runtime; and the pinned dependencies, which still load from repository paths.
- **L-5 items (L-6 prerequisites or release; not L-5 defects):**
  - **Production trust:** the production signing key, and embedding its public key, which is a separately
    authorized change. It signs both data releases and the software inventory. Since the compatibility correction,
    the shipping candidate installs **no data of any workflow** until then: every installation needs a verified
    inventory.
  - **L-6 qualification conflict to resolve before L-6:** the card's groups exercise installations on the exact
    shipping candidate (Group 5 with a test-signed package), but that candidate trusts no test key and so can install
    nothing. Either a separately identified test-trust qualification build, or the production key (with a
    production-signed inventory), is needed. This is an owner/designer decision.
  - **Deployment:** the signed inventory must be installed with the Character Tools software (L-6 deployment). The
    live installation has none, so the updater cannot install any data there yet.
  - **Live `gameinfo.txt` changed:** between the L-5 run and the correction (file time 2026-10-18 19:36Z), the live
    `usermod\gameinfo.txt` changed (`044881f3…` to `20f9d202…`) outside this work. Its first search path is still
    `|gameinfo_path|.` (usermod), so the effective Master path is unchanged. The other entries add game mounts. The
    P0 `gameinfo` pin no longer matches.
  - **Unqualified:** the menu entry (`--sfm-folder`) is designed in `updater/packaging/README.md`, not deployed;
    Windows versions other than this Windows 10 machine; code signing of the executables and antivirus reputation.
  - **Reproducibility:** bundles are code-identical but not byte-identical (CPython 3.10 marshal serialization).
- **Removed from the v1 critical path with P2/P3 (not passed):** native Master access, the CPM working
  directory, the native channel/key oracle, bytecode content and restoration recoverability. These were the
  former U0B open items; see Current milestone.
- **K/L residuals from R15 (not in R15 scope, unchanged):**
  - Normalizer namespace isolation (the Normalizer still runs in the shared `__main__`);
  - the shared window slot, log name and identity strings that old CPM builds also claim.
- **Deferred UI findings (product/UI work; none are Session 1 blockers):**
  1. **Legacy preset.** Still open. Apply of an old `body.scale.head` preset is refused. Future
     message: "This preset uses an outdated scale format. Delete this preset and save a new Body
     preset." This is a legacy edge case only; generic bone-scale persistence works.
  2. **Implemented in the pre-K UI polish pass, LIVE VERIFIED / PASS (final build `4e35f292…`,
     U2 + U3):**
     - Update Preset confirmation copy, with no question icon;
     - wider window with all tabs visible;
     - semantic button colors;
     - 2×2 Review grid;
     - Clear Classification wording.
- **Stale-scope UI presentation** and **`SidecarMissing` messaging:** undecided.
  - Real SFM shows that a stale-generation refusal is presented through the guard's generic copy.
    For Apply this is "Preset could not be applied safely…"; for Save it is "Can't save preset —
    Preset could not be saved. Nothing was saved."
  - The stale-scope reason is logged only, and CPM then rebuilds automatically.
- **Product identity strings** (window slot, log name, `PROD_VERSION`) are unchanged from G18AN
  (K/L).
- **Item-8 findings (K/L; user-facing, not failures):**
  1. **Scene source.** CPM resolves its scene from the shot under the playhead
     (`sfmApp.GetShotAtCurrentTime()`). The Normalizer uses the Clip Editor selection. The UI pass
     explains the playhead workflow in Help only; the behavior is unchanged by design.
  2. **Normalizer success.** A successful Normalizer run shows no visible completion confirmation.
     Recommendation: a non-blocking success notice, with modals only for failures or decisions.
- **Remaining pre-K qualification:**
  - Session 2: **COMPLETE — PASS** (S2-A_R2 and S2-B_R2).
  - Session 3: **COMPLETE — PASS** (S3 CORE PASS and S3_ADD).
  - the forced Apply and forced Fit rollback-verification failure gates: **Session 4 COMPLETE —
    PASS** (S4A, S4F);
  - §22 item 6 (historical authority cleanup): **COMPLETE — offline qualification PASS**
    (candidate `1e866871…`; not real-SFM qualified);
  - §22 item 7 (diagnostic/development logging reduction): **COMPLETE — offline qualification
    PASS** (candidate `bfba4d3a…`; not real-SFM qualified);
  - §22 item 8 (focused post-cleanup regression, including post-cleanup real-SFM qualification):
    **COMPLETE / PASS** (`I8A1`, 2026-10-08; candidate `bfba4d3a…` real-SFM qualified and
    installed).

  - Pre-K CPM UI polish pass: **LIVE VERIFIED / PASS** (`7e4686d7…`, U2; supersedes `5c6e2789…`,
    whose U1 attempt was closed as SUPERSEDED / NO QUALIFICATION VERDICT). It is superseded in the
    repository by the Help-wording-only candidate `4e35f292…` (U3 LIVE VERIFIED / PASS; installed).

  - Final pre-K UI build `4e35f292…`: **LIVE VERIFIED / PASS** (U3, Help wording delta from U2).

  **Pre-K complete. `4e35f292…` is the exact CPM candidate eligible to enter K.**
  - **K — COMPLETE / PASS** (K1A2 + K2A1, 2026-10-10).

  L: L-1 to L-4 COMPLETE / PASS (bounded), 2026-10-17; L-4R COMPLETE (owner-accepted), 2026-10-18; L-5 COMPLETE /
  PASS (bounded, Designer-reviewed and owner-accepted), 2026-10-19 (application v0.1.0, one-folder package). L-6 NOT
  STARTED / NOT AUTHORIZED.
- **Session 4 notes (not failures; carried to K; unchanged by items 7–8):**
  - Fit's exception path releases the stage with a bare `release()` (no
    `PROD_CPM_FIT_STAGE_RELEASED` line; result discarded); a raising success-path release could in
    theory be followed by a second `release()`. Live S4F shows exactly one successful release per
    injected stage.
  - The Body bone-scale branch of rollback verification is covered offline only (`BodyTest` changes
    no bone scales); Expression Apply shares `prod_apply` and is covered offline.
- R3, R6, R9, R13, R14, R15: CLOSED. Offline: Suites 1–4 PASS; C7–C10 PASS (C10 also real-SFM);
  R15 suite PASS.

## Next
Stop. This is the L-5 GitHub checkpoint (2026-10-19): L-5 COMPLETE / PASS (bounded), Designer-reviewed and
owner-accepted.
- **Pre-L-6 dependencies, in this order:**
  1. **Normalizer behavior:** investigate and resolve the owner-reported Normalizer behavior problems. The suspected
     relationship to animation-group TXT/sidecar data is unconfirmed. Root cause and corrective scope remain
     undetermined.
  2. **Launcher button:** CPM Quick Launch QL-1 and QL-2 PASS (2026-10-22; see Current milestone). QL-3 (optional
     packaging and installation) is NOT STARTED / NOT AUTHORIZED.
  3. **Release identity:** finalize the integrated software identities, the signed inventory, production trust and
     the release candidate before L-6 qualification. This includes resolving the L-5 items: the shipping candidate
     installs no data without trust, a test-trust qualification build or the production key for L-6, and deployment
     of the inventory and menu entry.
- **Post-v0.1.0 research proposal (not authorized for implementation):** a CPM Pose Library.
- **L-6** (release qualification on the exact shipping candidate): NOT STARTED / NOT AUTHORIZED.
- **Live installation:** see the observation in Current milestone. The authority files are exact G1 again, and the
  updater folder holds one completed owner-run transaction.
- **Outstanding release dependencies:** the production signing key, the signed compatibility profile and
  inventory (L-5), `published_at` and the final signed `data-v1.0.0` package (see Current milestone). No official
  data release has been published.
- **Not authorized by this checkpoint:** the Normalizer investigation, the launcher-button work, production signing,
  L-6 or any later increment; signing, tagging or publishing a release; any native SFM run; WPR/ETW work; or a live
  installation write.

L-1 to L-4 are COMPLETE / PASS (bounded); L-4R is COMPLETE (owner-accepted); L-5 is COMPLETE / PASS (bounded). K is COMPLETE / PASS. U0A is PASS (bounded). U0B is closed for v1 at the P1
evidence boundary. `4e35f292…`, the
production Normalizer `1f4ec5a2…` and exact G1 authority files remain installed (see the live installation observation).

## Checkpoints
Update this Ledger and output its complete, concise contents when:
- The milestone is complete and checked.
- Progress is blocked or requires an owner decision.
- A Blueprint conflict, scope expansion, or unmet prerequisite is found.
- Work is being paused or transferred.

State why the checkpoint occurred. Stop at milestone completion.
For blockers or conflicts, pause affected work until resolved.
The owner relays the updated Ledger to the designer, or the designer
retrieves that same version from the shared repository.

## Maintenance
Replace stale entries; keep checkpoint content about one screen.
Preserve unresolved issues. Label uncertainty and untested claims.
Keep history in Git or an archive. Routine edits do not require a
full Ledger report.
