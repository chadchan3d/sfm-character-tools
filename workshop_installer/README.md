# SFM Character Tools Workshop Setup

Setup installs the unchanged v1.0.0 release ZIP, including Control Group Normalizer, Character Preset Manager, Control Group Updater and both CPM toolbar-button files. It requires Autoinit Manager for installation; it does not modify that dependency or its settings.

## User flow

Subscribe, install Autoinit Manager, then choose **Scripts → SFM Character Tools → Install or Update (Windows Setup)**. Review the destination and replacement notice. Save your project and close SFM normally before choosing **Install** or **Update / Reinstall**. Setup checks again and refuses a running or uncheckable SFM process.

Setup replaces known Character Tools program files and installs the package's matching Animation Groups TXT, sidecar and manifest. Custom TXT edits are not merged. Before replacing an existing TXT, Setup creates and verifies a timestamped backup under `usermod/cfg/sfm_character_tools_installer/backups/`. Only TXT backups are retained permanently. Setup does not inspect the CPM library in Documents.

An update may replace data previously installed by Control Group Updater; “included version” means this Workshop package, not necessarily newer Animation Groups data. Known obsolete program files are removed using the previous installation record and the publisher's explicit obsolete-path list. Unrecognized files are not removed.

**Scripts → SFM Character Tools → Manage Installation** remains available after Workshop unsubscription. It can uninstall without the ZIP or Autoinit Manager. With the matching Workshop package still present, it also supports reinstalling that release. Installing button files does not re-enable a button disabled in Autoinit Manager; enable it there and restart SFM if necessary.

## Interruption and removal

An interrupted installation is completed from the exact verified package used to begin it. Keep SFM closed and run Setup again. If that package is absent, obtain it again. Restore Autoinit Manager if it is missing. Setup does not restore an older program version, retain previous application binaries, or claim that a multi-file update is atomic. If a destination file changed after the interruption, Setup identifies it and stops automatic recovery. Preserve the change and seek recovery assistance; Setup will not overwrite it on retry. The original TXT backup is never overwritten on retry.

Uninstall removes known programs, dependencies, both button files, installed menu entries, the manifest and recognized sidecars. It keeps the TXT, TXT backups, unrelated files, and existing updater records and independent backups. Modified program files are included in the explicit removal consent. Shared directories are never recursively deleted.

A recognized empty `publisher.lock` is held exclusively while authority files are removed, then deleted through the same verified Windows handle. Busy, unreadable, linked or nonempty locks stop removal before file changes. The sidecar directory is removed only when empty; unrelated contents are reported and retained. The updater's separate installation lock and records are not deleted.

Management is removed last. If Setup is running from its installed executable, Windows may prevent deletion of that executable. The result identifies it for manual deletion after Setup closes. No service or self-deletion helper is installed. Unsubscribe to remove the Steam-managed Setup entry; uninstall does not modify Workshop-managed files.

## Package and filesystem protection

The publisher-maintained `release.py` binds the version, archive filename, SHA-256 and full mapped file list. The original ZIP is unchanged. Setup checks its hash, archive paths, authority consistency, the 31 inventory entries' hashes/sizes and signature-file presence. It does **not** independently verify the inventory's cryptographic signature.

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

Disposable tests cover the installer, not a live SFM installation. Remaining practical acceptance is installed-menu launch, installation after normal SFM exit, opening the three tools, CPM button activation, updater coordination and removal. Clean-subscriber download/launch and Valve policy disposition remain separate public-Workshop release conditions. Gate 0 and Gate 1 are not repeated by this revision.
