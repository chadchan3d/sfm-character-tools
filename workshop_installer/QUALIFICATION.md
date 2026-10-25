# Workshop installer candidate qualification

This report covers only the isolated issue #2 implementation branch. It is not permission to publish a Workshop item.

| Check | Result | Boundary |
| --- | --- | --- |
| Original v1.0.0 ZIP SHA-256, all 1,006 archive entries, 1,004 mapped files, authority triple, 31 inventory hashes/sizes and signature-file presence | PASS | Exact approved release bytes; no independent cryptographic signature verification |
| Both optional CPM button hashes and paired placement | PASS | Offline source and disposable destination |
| Fresh install, installed-file verification and conservative removal | PASS | Disposable `game/usermod` tree |
| Existing custom Master and alternate sidecar require consent, restore former bytes on removal | PASS | Disposable files |
| Partial button and running-SFM simulation refuse before destination mutation | PASS | Process result injected for test; not a native SFM run |
| Held Updater installation lock refuses the installer | PASS | Real Win32 no-sharing lock in a disposable tree |
| Interrupted write leaves PREPARED; recovery restores prior files | PASS | Injected interruption in disposable tree |
| Changed authority/button files survive removal | PASS | Disposable files |
| Installer-state reparse paths and post-consent authority changes refuse before destination mutation | PASS | Focused disposable regressions |
| Interrupted removal resumes while preserving the recorded customized authority/button groups; further changes refuse | PASS | Focused disposable regression |
| Python 2 menu and management launcher grammar | PASS | Static Python 2 grammar check; not embedded SFM execution |
| Self-contained Windows helper build and staged three-payload-file SHA-256 manifest | PASS | Built on Windows; staged output verified locally |
| Actual Workshop subscriber without publisher plugins, installed-menu launch, Autoinit button and installed management after unsubscribe | NOT TESTED | Owner's later real-SFM release acceptance |
| Steam policy acceptance and public publication | NOT TESTED | No Steam submission in this branch |

Disposable tests: `python -m unittest workshop_installer.tests.test_disposable -v` with `SCT_V1_RELEASE_ZIP` set to the unchanged release archive. Ten tests passed, including three focused regressions added after PR review. Tests did not touch an SFM installation.

The source branch contains no release ZIP, executable, generated build output, raw local logs or screenshots. The staged payload is a separate local candidate for owner inspection, not a published release.
