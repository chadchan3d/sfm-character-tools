# Workshop Setup revision: bounded verification

This report covers the owner-approved lightweight installer revision on PR #3. It does not certify a live installation or authorize public Workshop publication.

## Current results

| Check | Result | Evidence boundary |
| --- | --- | --- |
| Original release archive SHA-256, all 1,006 ZIP entries and 1,004 mapped files | PASS | Unchanged v1.0.0 archive |
| Matching Master/sidecar/manifest and 31 inventory hashes/sizes, signature-file presence | PASS | No independent cryptographic signature verification |
| Full release install, per-file hash verification and removal | PASS | Disposable Windows destination; bundled updater executables not executed |
| Existing TXT backup, retained TXT on uninstall and backup failure before program changes | PASS | Exact byte comparison in disposable directories |
| Reinstall of modified programs and partial button repair | PASS | Known files replaced after a captured consent snapshot |
| Synthetic next-release addition and obsolete-file/bytecode removal | PASS | Small test-only extension; not a claim of another released version |
| Interrupted installation completion, exact-package binding and original-backup retention | PASS | Injected interruption; no previous program backups or rollback |
| Changed-file recovery guidance | PASS | Focused regression verifies relative path and no futile Retry action |
| Autoinit required on installation recovery | PASS | Focused regression verifies no resumed writes until restored; uninstall remains independent |
| Autoinit in configured SFM mounts | PASS | Seven focused tests cover mounted archive/default roots, unmounted/commented roots, incomplete dependencies, reparse paths and unsupported/ambiguous configuration |
| Intervening TXT edit, running/unreadable process status, busy updater lock | PASS | Edit/status checks; real Windows updater lock |
| Uninstall without payload or Autoinit, additional sidecar removal, unrelated-file preservation | PASS | Disposable filesystem; no real unsubscription |
| Interrupted uninstall and failed lock cleanup retain management for retry | PASS | Injected failures with direct management-file assertions |
| Running installed helper retention is reported | PASS | Running-path decision injected; actual executable-removal behavior remains a native acceptance item |
| Legacy publisher lock: valid empty, busy, nonempty, hard-linked and absent | PASS | Real Windows files/handles; deletion targets the exclusively held verified object |
| State-path reparse rejection | PASS | Focused mocked file-attribute regression |
| Native window labels, owned details control, busy-action exclusion and missing-payload uninstall | PASS | Hidden Windows controls; no live SFM |
| Generated Workshop/management scripts' Python 2 grammar | PASS | Static grammar and compile checks; embedded Python 2.7 execution remains native acceptance |
| Windowed argument handling with absent console streams | PASS | Regression plus frozen helper startup |
| Self-contained helper build and staged payload hashes | PASS | Windows, Python 3.10.6, PyInstaller 6.11.1 |
| Public repository sanitation | PASS | Complete proposed branch/history, PR text, staging manifest and decoded helper reviewed |

There are 29 checks in the unittest suite: 17 disposable installation tests, seven mounted-dependency tests and five interface/launcher tests. The mounted-dependency correction passed ten focused tests: the seven new tests, dependency enforcement on recovery, ordinary interrupted-installation retry and no-Autoinit uninstall. The preceding two P2 corrections passed their five focused checks. Unrelated qualifications were not repeated.

Run with `SCT_V1_RELEASE_ZIP` set to the unchanged archive:

```text
python -m unittest discover -s workshop_installer/tests -v
```

The corrected helper SHA-256:

```text
fc72fba888eeb662c17afa991e0eced3f10db0f1052099b9a66e65b17fbd8234
```

Build output and original release ZIP are not committed. Generated manifests contain relative paths only. Earlier PR qualification requiring restoration of previous software and preservation of modified program files is superseded by the owner's explicit replacement/removal policy.

## Corrections caught during preparation

The generated management launcher received a static Python 2 grammar regression check after an unintended template edit was caught. That edit was corrected before the final build. Frozen `--help` startup exposed argparse's assumption that stderr exists in a windowed executable; console-free argument handling was corrected and retested. The final UI uses native Windows controls with no additional GUI runtime.

## Remaining real-SFM acceptance

Use an explicitly authorized installation, with the current TXT backed up independently before the acceptance run:

1. Launch the installed Workshop menu entry; confirm the destination and replacement notice, close SFM normally, and install. Check the matching authority files and TXT backup.
2. Restart SFM; open CPM, run a bounded Selected Shots normalization, open the updater without an unnecessary data activation, and confirm CPM button availability/activation through Autoinit Manager.
3. Confirm Setup and Updater exclude each other using the existing installation lock. This is an integration check, not a repeat of the earlier filesystem campaign.
4. Confirm installed management works without the Workshop payload; close SFM and uninstall. Check the retained TXT/backup, removed tools/button/sidecars, and accurate reporting of any running Setup executable or unrelated remaining directory contents.

Do not repeat Gate 0/Gate 1. Clean-subscriber distribution and unresolved Valve policy questions remain separate release conditions. No live SFM, Workshop publication, merge or application changes occurred in this revision.

## Owner-approved usability revision — 26 October 2026

The installation engine and original v1.0.0 ZIP remain unchanged apart from typed process refusal reporting and an opt-in hidden tasklist query. The default Updater process query behavior is unchanged; the released Updater was not rebuilt. Both menu filenames remain unchanged.

### Implemented

- One non-daemon worker owns lengthy preparation, preview, installation, recovery, removal and temporary cleanup. The native UI thread alone owns Windows controls. Busy state blocks overlapping work and Close; stale page action IDs cannot trigger new-page actions.
- The initial preparation window is shown/painted before package extraction and installation scanning. An inherited hidden startup hint cannot leave Setup permanently invisible.
- Running SFM, unreadable process status, unavailable Workshop package, invalid package, incomplete operation and unreadable operation record have distinct presentation.
- Back to Setup refreshes consent rather than automatically retrying. Finish Installation/Finish Uninstall use the existing recorded-operation recovery paths.
- Compact measured text layout, explicit destination before consent, no uninstall ellipsis, useful Details only, and CRLF formatting for the native multiline EDIT control.
- Accurate completion copy, Open Backup Folder, and Show Setup File selecting the exact retained executable. No self-deletion mechanism.

### Verification performed

The final complete Windows suite passed **39/39 tests** on Python 3.10.6. It includes the existing full mapped-release install/remove, TXT backup, interrupted recovery, changed-file refusal, reparse, updater-lock, mounted-Autoinit and payload-independent uninstall cases. The 15 interface/process-query checks cover serialization, thread ownership, deferred completion, busy closure, stale clicks, reviewed-snapshot binding, distinct errors, missing/invalid packages, CRLF, long paths and exact Explorer selection arguments.

One initial failure was an obsolete assertion expecting the word "closed" in a process refusal. The test now asserts the typed RUNNING/UNKNOWN evidence. Its focused rerun and the final full run passed. This did not relax the process gate.

The Windows one-file helper built with PyInstaller 6.11.1. Its SHA-256 is:

```text
7eeb472d87287e11b0bb83251e1564069fa0c37204b3ab165c5587307446b6f9
```

The four-file payload was restaged and verified. The original release ZIP remains:

```text
5323b1431a200c0bea3641e7dcb2f9fac45920d889f749ac9bf07972f5a89458
```

### Startup measurement and its limits

One local warm launch of the final helper recorded:

| Stage | Elapsed |
|---|---:|
| Equivalent launcher executable/ZIP hash checks, measured separately | 0.018 s |
| Process launch to helper entry | 0.200 s |
| Process launch to native window show/paint marker | 0.269 s |
| Helper entry to native window show/paint marker | 0.068 s |
| Show/paint marker to preparation completion | 7.305 s |

These are internal timing markers, not a human-observed SFM menu launch or a cold-start guarantee. They demonstrate that expensive preparation occurs after the native show/paint boundary. They do not establish that the owner's previously observed 5–10-second visible launch delay is fully resolved in SFM.

Qualification markers are opt-in through SCT_SETUP_TIMING_FILE, contain stage/time values only, and do not change installation decisions. Raw local evidence is not committed.

### Explicitly pending Owner observations

Graphical inspection could not access the shell-launched disposable Setup window. The subsequent graphical launch request timed out awaiting app approval. No successful graphical responsiveness observation is claimed, and no alternative UI automation was used to bypass that limitation.

- **Owner condition 2:** the built interface repaint/move/minimize check during deliberately delayed work remains unverified. In-process native-control tests prove worker isolation and blocked Close/duplicate actions, but do not substitute for this visible observation.
- **Owner condition 3:** Show Setup File's exact Explorer command is covered; actual Explorer highlighting and manual deletion after the installed Setup exits remain unverified for this revision.
- Hidden tasklist execution, captured output, timeout and unchanged status decisions pass source-level tests. Absence of visible console flashes remains an Owner observation.
- Final SFM presentation/launch checks are Owner-operated. No SFM startup or application qualification was performed by this revision.

The earlier owner-operated bounded practical acceptance remains accepted. It is not repeated. The revised UI still requires the bounded observations above before its additional Owner conditions can be marked complete. This is not authorization to merge or publish.

### Sanitation

PUBLIC REPOSITORY SANITATION: PASS, subject to final published-commit verification. Proposed source/history and PR metadata were checked; the staged manifest contains relative paths only. All 5,464 decoded executable code objects were checked for identifying build paths. Build outputs, private fixture files, raw logs and screenshots are excluded. Authorized public project identifiers and commit email remain.

## Owner amendment — Autoinit Manager is optional

This amendment supersedes the earlier mandatory-Autoinit installation and recovery policy. Earlier results remain historical evidence for their identified candidates; they are not qualification of this amendment.

`preview()`, `install()` and `recover()` no longer require Autoinit Manager or read its mount configuration. Uninstall remains independent. The existing mount-inspection helper is retained but is not called by any installation path; its historical tests do not establish an admission requirement.

Both unchanged toolbar files are installed with the three main tools. Source inspection of the pinned ZIP establishes that the bootstrap is only under `scripts/sfm/autoinit/ChadChan3D/`, while the private implementation is outside both Scripts-menu and startup discovery trees. Setup installs no `sfm_init_local.py` or startup hook. The bootstrap imports standard-library modules; the implementation imports Qt/SFM dependencies but neither depends on Autoinit Manager modules or its shared globals. In the absence of a loader executing that bootstrap, the files are inactive. Later installation/enabling through Autoinit requires no Character Tools reinstall. No native SFM startup is claimed for this source-inspection conclusion.

### Focused results

**7/7 PASS** on Windows/Python 3.10.6:

1. Full 1,006-file installation and uninstall without Autoinit or gameinfo.txt; all installed hashes verified.
2. Fresh installation and reinstall/repair without Autoinit, even with uninterpretable mount configuration; both toolbar hashes correct and original custom TXT backup preserved.
3. Interrupted installation recovery after Autoinit/configuration removal; exact original backup retained, toolbar pair complete, subsequent uninstall succeeds.
4. Existing Autoinit-present toolbar pair repair and uninstall regression.
5. Wrong recovery package and intervening TXT edits still refuse.
6. Real Windows Updater installation lock still excludes installation.
7. Failed required TXT backup still prevents program changes.

The 15 interface/process-query tests also passed after the wording amendment. There are now 40 available suite methods; the full suite was not rerun merely to repeat unrelated tests. The earlier 39/39 result belongs to the preceding usability candidate.

The amended helper was rebuilt and restaged. Current SHA-256:

```text
e9cd4054c48073deb843cfaff4c907164d4be71be0d3290cb24a377ac58abf73
```

All four staged files were verified; the original ZIP and both button-file identities remain unchanged. The new helper's 5,464 decoded code objects also pass the identifying-build-path scan. PUBLIC REPOSITORY SANITATION: PASS following source/history and artifact review.

The preceding startup measurements remain evidence for that candidate, not new timing measurements of this rebuilt executable. The outstanding visible desktop checks and final Owner-operated SFM presentation checks remain pending. No live SFM installation, application source, original release ZIP, signing, PR merge or Workshop publication was changed.

## Owner-approved final copy and presentation correction — 26 October 2026

This follow-up applies the Owner's approved copy. Install/reinstall wording uses the established package and installed versions, the destination remains visible, and absent metadata no longer creates an empty control or spacing. Metadata uses a modestly smaller native font. No custom painting, shading or decorative indicators were added.

UNKNOWN process status now displays **Could not check Source Filmmaker**, explains that the Windows process check failed, and exposes the available specific diagnostic reason in Details. RUNNING remains separate, and interrupted-operation evidence is retained. Optional-toolbar instructions identify **Scripts → kiwifruit → Autoinit Manager** and **ChadChan3D_CPM_ASE_Button**. Autoinit remains optional.

Temporary cleanup leaves the existing page visible and disables actions/Close until the worker finishes. A cleanup error identifies temporary-file cleanup separately and permits exit without repeatedly attempting the failed cleanup. Routine retained-directory lists are omitted from successful removal; unexpected authority-file information remains available.

**Show Setup File** now uses `SHParseDisplayName` and the single-item `SHOpenFolderAndSelectItems` call on the existing worker. HRESULTs are checked, COM initialization/uninitialization is balanced, and the returned item identifier is released. Failures identify the remaining file and actual diagnostic error rather than silently opening another directory.

### Focused verification

- **21/21 interface/process-query tests PASS**, Windows/Python 3.10.6. This is the focused interface suite, not a repeat of the installation or application campaigns.
- Coverage includes version-dependent copy, exact UNKNOWN explanation and available diagnostics, interrupted-operation preservation, quiet cleanup success/failure, worker exclusion, native-control spacing, routine-directory suppression, unexpected retained-file reporting, and Shell selection success/failure/resource cleanup. The Shell call tests use controlled responses; they do not establish actual Explorer selection.
- The production helper builds successfully with PyInstaller 6.11.1. Embedded app/window/core code matches the reviewed source. All four staged payload hashes and wrapper-archive members were checked. The original release ZIP and toolbar pair are unchanged.
- The first disposable GUI preparation refused because the restricted process query returned UNKNOWN; the production gate was preserved. With normal Windows process-query access, a full disposable installation and the actual built helper launch succeeded. The graphical helper did not expose the Setup window, so no button interaction or Explorer selection was observed. The missing visual result is **PENDING**, not PASS.
- Earlier Owner observations of prompt preparation, successful installation and absence of console flashes remain accepted. No new extended visual-responsiveness claim is made.

Current Setup SHA-256:

```text
b799f9f987d2396ae0a432f38142aa278a9abe85c0c1b92d6c431f7d780dfe80
```

Launcher SHA-256: `ae97cdcb171d324dfa6a006a72aa9fb7835f4a2a1462a7b5e537e58ecd022cb2`.

Staging-manifest SHA-256: `02bf22718272c88b13c5cb1284d74a9a38b4c6397a9af1bedc29771da0486e5c`.

### Remaining Owner acceptance

Using this corrected build, verify the final pages and quiet Close behavior. After removal leaves its running helper, **Show Setup File must visibly open its containing folder and select that exact executable at a path containing spaces**. Close Setup and confirm the file can be manually deleted. Actual Explorer observation is required; mocked calls, HRESULT success, or source inspection cannot substitute. This follow-up does not close that acceptance condition.

The previously pending extended move/minimize/repaint check remains pending unless directly observed by the Owner. Final SFM checks remain Owner-operated. No live installation, SFM startup, Gate 0/1 repetition, application changes, merge or Workshop publication occurred.

PUBLIC REPOSITORY SANITATION: PASS for the proposed correction and staged artifact. Source/diff and metadata were inspected; all 5,469 decoded executable code objects passed the identifying-build-path scan. Private raw evidence and disposable fixtures are excluded from the repository. Final published blob identities are checked before handoff.

## Final Windows distribution-test build — 26 October 2026

This entry supersedes the pending Owner GUI conditions above. The Owner explicitly reports all six GUI acceptance checks **PASS**, including actual Explorer selection, deletion after closing Setup, final presentation and closing behavior. These are Owner observations of the accepted candidate, not automated results or observations repeated on the final text-only rebuild.

Build source: `eed44a919620f1926f28817892ac0dd00b137dbc`, tree `fdad2cdd0afa3b29795ae18a0da054966d2ac50d`. The checkout was clean and matched the published PR branch before building. Commits `11166336` and `eed44a91` remove only the unnecessary Steam Stop warning from Setup and README. The retained notice is: **Steam may still show SFM as Running while Setup is open.** No installation, backup, locking, recovery, removal or application behavior changed.

Final build: Windows Python **3.10.6**, existing locked PyInstaller **6.11.1** environment; one-file, windowed `SCT_Setup.exe`. No dependency installation or upgrade occurred.

| Verification | Result |
| --- | --- |
| Focused interface/process-query suite | PASS, 21/21 on final source |
| Windows executable build and bounded `--help` startup | PASS, exit 0 |
| Bundled app/window/core/release code versus final source | PASS |
| Removed warning absent from bundled Python code and current app/README | PASS |
| Four-file staging, manifest hashes/sizes and exact ZIP member structure | PASS |
| Original v1.0.0 release ZIP identity | PASS, unchanged |
| Public correction history, documentation, manifest and executable code sanitation | PASS; 5,469 decoded code objects inspected |
| Owner's six GUI observations on accepted presentation candidate | PASS, Owner-reported |
| Repetition of Owner GUI/application campaign on text-only rebuild | NOT TESTED; deliberately not repeated |
| Clean-subscriber delivery/launch of this final package | NOT TESTED; next Owner-operated test |
| Public Workshop policy disposition | PENDING; separate release decision |

### Final artifact identities

Paths below are relative to the staging root, under `scripts/sfm/mainmenu/SFM Character Tools/`.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `Install or Update (Windows Setup).py` | 1,867 | `e8bcfb38183675dfa132848ed2c65ebb0ba44cf1a9b409268273bffab4018793` |
| `_workshop_installer/SCT_Setup.exe` | 6,749,429 | `9375f0ff7d6009ffa32a13785ca88e001eae9b17d85983af6090a5eb60f55a12` |
| `_workshop_installer/SFM.Character.Tools.v1.0.0.zip` | 17,667,566 | `5323b1431a200c0bea3641e7dcb2f9fac45920d889f749ac9bf07972f5a89458` |
| `_workshop_installer/installer_manifest.json` | 732 | `2840f4e206f2bcc6f0105d173c3e44f5141dc04858cbb058d14a925314f0b3a0` |

Distribution-test archive: `SFM_Character_Tools_Workshop_Installer_Final_20261026.zip`, **23,553,562 bytes**, SHA-256 `ebac2b9dea2d0da6fefcb4eb85617d87459593d0ae9d5923e3630580c53b07a8`. It contains exactly the four staged files, without an enclosing directory. The wrapper is for distribution-test preparation, not a change to the original software release ZIP.

**READY FOR DISTRIBUTION TEST. PUBLIC REPOSITORY SANITATION: PASS.** No live SFM changes, merge or Workshop publication occurred. Final clean-subscriber Steam Workshop delivery/launch and distribution-policy decisions remain with the Owner.

## Final qualification closeout and archive decision — 26 October 2026

**RELEASE READY — Owner acceptance complete.** This closeout supersedes the historical pending distribution-test and Owner decision statuses above. Earlier entries describe the evidence available at their respective checkpoints and remain preserved.

### Owner-reported Workshop acceptance

The Owner reports **PASS** for the final Workshop distribution and clean-install test:

1. Staged the final Workshop package in `usermod` and uploaded it to Steam.
2. Removed the local publishing copy.
3. Subscribed and downloaded the package through SFM.
4. Confirmed that no Character Tools were installed before testing.
5. Installed through the Workshop-delivered installer.
6. Launched all three applications and confirmed basic operation.

These are Owner observations establishing delivery, clean installation, Scripts-menu integration and basic operation. No independent screenshots, trace logs or measurements are asserted. The six previously accepted Owner GUI checks, independent code review, final Windows build, 21/21 focused automated tests, staging integrity and sanitation evidence remain accepted. No campaign was repeated. The Owner accepts the Workshop distribution decision; no additional subscriber test or application qualification is required. This records the Owner's decision, not separate Valve policy approval.

### Approved archive distinction and provenance

| Identity | Purpose | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Archive A | Qualified Steam Workshop installer payload; original published software ZIP | 17,667,566 | `5323b1431a200c0bea3641e7dcb2f9fac45920d889f749ac9bf07972f5a89458` |
| Archive B | Authoritative current GitHub `v1.0.0` download | 17,666,478 | `1e128e1fa536f1b24c032299ecc19fd1cb53ba5645cb7ca58819b1e0792817ba` |

Archive A's original GitHub publication is recorded by commit `2ff801b8cc99ece429c51509876c6d1bcf6d4b14`. Commit `14826373a90f105077a988e80b48734dafaaea0c` records the subsequent Owner-approved simplification of `OPTIONAL - CPM Button/README.txt` and replacement of the GitHub ZIP/checksum assets with Archive B. The Workshop installer pinned Archive A from its first implementation and retains it by explicit Owner decision. It is not byte-identical to the current GitHub download; earlier references to the unchanged or original ZIP mean Archive A, not Archive B.

The independent read-only comparison verified both archive hashes, ZIP integrity and SHA-256 hashes for every entry. Both archives contain 1,006 entries, with identical paths/order, no missing/additional entries and no duplicate paths. Only the optional-button README differs:

| README identity | Bytes | Compressed bytes | SHA-256 |
| --- | ---: | ---: | --- |
| Archive A | 4,956 | 2,028 | `49957781ee009ba5b1742ad4bf47048816c9074b67fc999836341dd512882eba` |
| Archive B | 2,090 | 940 | `06af2636d6ad8b53a9031dd00a1b3fa57aae637ebd9f428e30ddc1e9265252b9` |

The 1,088-byte archive-size difference equals the README's compressed-size difference. The other 1,005 entries match in uncompressed bytes and stored compressed payloads, including programs, executables, Animation Groups TXT, sidecar, manifest, signed inventory and both toolbar scripts. Setup's `_map_member()` excludes this README from installation. There is no installed application/data difference and no reason to rebuild or repeat application qualification.

The Owner explicitly approves retaining A for Workshop and B for the current GitHub release. Neither archive, existing release asset, tag, executable or tested Workshop payload is changed by this closeout. The final Setup and four-file staging ZIP retain the identities recorded above; build source remains `eed44a919620f1926f28817892ac0dd00b137dbc`.

**PUBLIC REPOSITORY SANITATION: PASS.** This closeout changes documentation only, uses public identifiers and relative paths, and contains no private evidence or build artifacts. PR #3 merge into its existing `master` target is Owner-authorized after integrity checks. Making the tested Workshop item public and publishing the announcement remain Owner actions.
