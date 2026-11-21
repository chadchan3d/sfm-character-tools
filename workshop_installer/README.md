# SFM Character Tools Workshop Setup

Setup installs the official SFM Character Tools v1.1.0 archive, the signed ZIP published as [GitHub release v1.1.0](https://github.com/chadchan3d/sfm-character-tools/releases/tag/v1.1.0), including Control Group Normalizer, Character Preset Manager, Control Group Updater and both CPM toolbar-button files. Autoinit Manager is optional: it enables the toolbar button, but is not needed to install or use the three main tools. Setup does not modify Autoinit Manager or its settings.

The Workshop payload is the same archive as the GitHub v1.1.0 download: `SFM.Character.Tools.v1.1.0.zip`, SHA-256 `0f64eb1306a57f7065db6dcc8419e7e909525a9057af1ee67dce0c8fcc6b8b57`, 1,008 entries. Against v1.0.0 it adds the two Pose Library registry files (`scripts/SFM Character Tools/cpm_pose_profiles_v1.json` and `cpm_body_profiles_v1.json`) and replaces Character Preset Manager and the signed software inventory; Setup never installs the two README files. Earlier Workshop payloads installed the v1.0.0 archive (Archive A, `5323b143…`), which differed from the GitHub v1.0.0 download (Archive B, `1e128e1f…`) only in the optional-button README; see `QUALIFICATION.md`.

Both toolbar files are installed unconditionally. The bootstrap is inside Autoinit Manager's startup tree, and its private implementation is outside SFM's Scripts-menu and startup discovery trees. Without Autoinit Manager, neither runs automatically. Install Autoinit Manager later, enable the CPM button there and restart SFM; reinstalling Character Tools is unnecessary. Install, update, recovery and uninstall do not require Autoinit or parse its mount configuration.

## User flow

Subscribe, then choose **Scripts → SFM Character Tools → Install or Update (Windows Setup)**. Review the destination and replacement notice. Save your project and close SFM normally before choosing **Install** or **Update / Reinstall**. Setup checks again and refuses a running or uncheckable SFM process.

Leave Setup open while closing SFM. Steam may continue to show SFM as Running until Setup closes. After installation, close Setup before starting SFM again.

Setup shows **Preparing Setup** before extracting and verifying the package. Its window stays available while one worker performs file operations. Installation, removal and recovery cannot overlap; Close is unavailable during an active operation. **Back to Setup** returns to a fresh review, without automatically repeating an operation. A running SFM process produces close-SFM instructions; an unreadable process check remains a separate refusal.

Setup displays the established installed/package versions and installation folder before consent. Matching versions are described as a reinstall. If the Windows process check fails, **Could not check Source Filmmaker** explains the refusal and Details shows the available diagnostic reason. Temporary cleanup leaves the current page visible until Setup closes; a cleanup failure is reported separately from the installation or removal result.

Setup replaces known Character Tools program files and installs the package's matching Animation Groups TXT, sidecar and manifest. Custom TXT edits are not merged. Before replacing an existing TXT, Setup creates and verifies a timestamped backup under `usermod/cfg/sfm_character_tools_installer/backups/`. Only TXT backups are retained permanently. Setup does not inspect the CPM library in Documents.

An update may replace data previously installed by Control Group Updater; **Package version** means this Workshop package, not necessarily newer Animation Groups data. **Installed version** is shown only when an installation record establishes it. Known obsolete program files are removed using the previous installation record and the publisher's explicit obsolete-path list. Unrecognized files are not removed.

**Scripts → SFM Character Tools → Manage Installation** remains available after Workshop unsubscription. It can uninstall without the ZIP or Autoinit Manager. With the matching Workshop package still present, it also supports reinstalling that release. Installing button files does not re-enable a button disabled in Autoinit Manager; enable it there and restart SFM if necessary.

The two menu entries remain separate: the Workshop entry supplies installation/update files, while the installed entry preserves management access after unsubscription. An unavailable package is an ordinary management state; a package that fails verification is reported separately. Neither condition suppresses uninstall when its safety checks pass.

## Interruption and removal

An interrupted installation is completed from the exact verified package used to begin it. Keep SFM closed and run Setup again. If that package is absent, obtain it again. Setup does not restore an older program version, retain previous application binaries, or claim that a multi-file update is atomic. If a destination file changed after the interruption, Setup identifies it and stops automatic recovery. Preserve the change and seek recovery assistance; Setup will not overwrite it on retry. The original TXT backup is never overwritten on retry.

Uninstall removes known programs, dependencies, both button files, installed menu entries, the manifest and recognized sidecars. It keeps the TXT, TXT backups, unrelated files, and existing updater records and independent backups. Modified program files are included in the explicit removal consent. Shared directories are never recursively deleted.

A recognized empty `publisher.lock` is held exclusively while authority files are removed, then deleted through the same verified Windows handle. Busy, unreadable, linked or nonempty locks stop removal before file changes. The sidecar directory is removed only when empty; unrelated contents are reported and retained. The updater's separate installation lock and records are not deleted.

Management is removed last. If Setup is running from its installed executable, Windows may prevent deletion of that executable. **Show Setup File** opens Explorer with the exact remaining file selected. Close Setup before deleting that file; retained folders and unrelated files do not need to be deleted. No service or self-deletion helper is installed. Unsubscribe to remove the Steam-managed Setup entry; uninstall does not modify Workshop-managed files.

File selection uses the Windows Shell API, without command-line quoting. A selection failure reports the exact remaining location and diagnostic error. Routine retained-directory lists are omitted from successful removal pages; unexpected retained authority files remain available in Details.

**Optional CPM toolbar button:** Requires Autoinit Manager. Enable **ChadChan3D_CPM_ASE_Button** under **Scripts → kiwifruit → Autoinit Manager**, then restart SFM.

## Package and filesystem protection

The publisher-maintained `release.py` binds the version (1.1.0), archive filename, SHA-256 and full mapped file list to the official v1.1.0 archive; any other ZIP, including the v1.0.0 archives, is refused. Setup checks its hash, archive paths, authority consistency, the 33 inventory entries' hashes/sizes and signature-file presence. It does **not** independently verify the inventory's cryptographic signature.

Setup snapshots verified source contents outside Workshop before installation, rejects destination/state reparse points, uses the existing Updater installation lock, and refuses unresolved updater operations. Completion requires checking all intended installed files and removals. These checks do not protect against an administrator deliberately racing filesystem changes or a user manually starting SFM after an interrupted operation.

The pre-release rollback-style installer record is not silently migrated. If one exists, Setup refuses rather than discarding recovery evidence. That experimental installer was not a public release.

## Build and stage

Build on Windows with Python 3.10 and PyInstaller 6.11.1:

```text
powershell -File workshop_installer/build.ps1 -Output BUILD_DIRECTORY
python -m workshop_installer.stage --release RELEASE_ZIP --setup BUILD_DIRECTORY/SCT_Setup.exe --out NEW_STAGING_DIRECTORY
```

The single-window interface uses Windows controls through Python's ctypes; no separate GUI runtime is required. Subscribers need no Python runtime. Build output and the ZIP are excluded from Git. `stage.verify` checks the four-file staging tree: menu launcher, setup executable, original ZIP and relative-path manifest. The bundled updater executables are not executed by staging or disposable tests.

Publication is separate: follow the already-qualified Scripts-category procedure, inspect the four-file upload list and avoid an extra enclosing directory. This implementation does not stage files into SFM or submit anything to Steam.

## Acceptance boundary

**v1.1.0 update:** prepared and verified offline (`QUALIFICATION.md`, section "v1.1.0 update"); the native upgrade and uninstall acceptance and the Workshop upload are pending. The Workshop item still distributes the v1.0.0 payload until then.

**v1.0.0:** qualification is complete within its recorded boundary. The Owner reports all six final GUI checks PASS and successful Steam Workshop upload, removal of the local publishing copy, subscription/download, installation without preexisting Character Tools, and launch of all three applications. These are Owner observations, separate from the final 21/21 automated checks and artifact verification. Earlier accepted installation, bounded tool use, toolbar activation, payload-independent uninstall, retained TXT/backups, reinstallation and locking evidence remains applicable. The Owner accepts the Workshop distribution decision and the documentation-only archive distinction. No further subscriber or application qualification is required. The remaining publication actions are the Owner's public visibility change and release announcement; this is not a claim of separate Valve policy approval.
