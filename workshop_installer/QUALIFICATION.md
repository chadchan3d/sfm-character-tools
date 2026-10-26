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
