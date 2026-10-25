# Workshop installer candidate qualification

This report covers only the isolated issue #2 implementation branch. It is not permission to publish a Workshop item.

| Check | Result | Boundary |
| --- | --- | --- |
| Original v1.0.0 ZIP SHA-256, all 1,006 archive entries, 1,004 mapped files, authority triple and 31-file signed inventory | PASS | Exact approved release bytes; no application code changed |
| Both optional CPM button hashes and paired placement | PASS | Offline source and disposable destination |
| Fresh install, installed-file verification and conservative removal | PASS | Disposable `game/usermod` tree |
| Existing custom Master and alternate sidecar require consent, restore former bytes on removal | PASS | Disposable files |
| Partial button and running-SFM simulation refuse before destination mutation | PASS | Process result injected for test; not a native SFM run |
| Held Updater installation lock refuses the installer | PASS | Real Win32 no-sharing lock in a disposable tree |
| Interrupted write leaves PREPARED; recovery restores prior files | PASS | Injected interruption in disposable tree |
| Changed authority/button files survive removal | PASS | Disposable files |
| Python 2 menu and management launcher grammar | PASS | Static Python 2 grammar check; not embedded SFM execution |
| Self-contained Windows helper build and staged three-payload-file SHA-256 manifest | PASS | Built on Windows; staged output verified locally |
| Actual Workshop subscriber without publisher plugins, installed-menu launch, Autoinit button and installed management after unsubscribe | NOT TESTED | Owner's later real-SFM release acceptance |
| Steam policy acceptance and public publication | NOT TESTED | No Steam submission in this branch |

Disposable tests: `python -m unittest workshop_installer.tests.test_disposable -v` with `SCT_V1_RELEASE_ZIP` set to the unchanged release archive. Seven tests passed. After the last installer write-order change, the fresh-install/removal and interrupted-recovery cases were rerun and passed. Tests did not touch an SFM installation.

The source branch contains no release ZIP, executable, generated build output, raw local logs or screenshots. The staged payload is a separate local candidate for owner inspection, not a published release.
