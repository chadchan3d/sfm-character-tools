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

There are 20 checks in the unittest suite: 16 disposable installation tests and four interface/launcher tests.

Run with `SCT_V1_RELEASE_ZIP` set to the unchanged archive:

```text
python -m unittest discover -s workshop_installer/tests -v
```

The final helper is 6,720,732 bytes, SHA-256:

```text
b9e408ec35962eb84a05b73753c8d41187921899c276d70868903803618c252e
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
