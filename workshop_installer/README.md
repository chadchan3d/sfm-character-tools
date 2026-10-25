# SFM Character Tools Workshop installer

This is the fixed v1.0.0 offline installer for issue #2. The existing release ZIP is the source of the application files. The installer checks its SHA-256, extracts and verifies the signed software inventory, and installs the Normalizer, CPM, Updater, and optional CPM toolbar button together. It does not modify Autoinit Manager. A subscriber needs Autoinit Manager installed first.

## Build and stage

On Windows with Python 3.10 and PyInstaller 6.11.1, run `workshop_installer/build.ps1`. Build output, the original release ZIP, and the staging output are deliberately excluded from Git. Then run:

```text
python -m workshop_installer.stage --release RELEASE_ZIP --setup dist/SCT_Setup.exe --out NEW_STAGING_DIRECTORY
```

The fresh staging directory contains the Scripts-category upload tree and a SHA-256 manifest. Verify it again using `workshop_installer.stage.verify` before publication. The manifest itself is included in `_workshop_installer/`; it lists the other three files and uses only relative paths. This recipe never executes the updater worker in the ZIP.

Publishing remains a separate owner action. Follow the proved Gate 0 Scripts-category upload procedure: stage only these four files in the publisher's SFM `game/usermod/scripts/sfm/mainmenu/SFM Character Tools/` after checking for collisions, choose **File → Community → Publish to Steam Workshop → Scripts**, and inspect the uploader's exact four-file list before submission. The published item must contain the staged tree beneath `scripts/`, with no additional enclosing folder. Remove only the temporary publisher staging files you recorded. This PR does not perform that staging or publication.

## User flow

Subscribe to the Workshop item and install Autoinit Manager. In SFM, select **Scripts → SFM Character Tools → Install SFM Character Tools**. The launcher checks the two payload hashes and starts the Windows setup window. Review the destination and any existing Animation Groups replacement. Save the project, close SFM normally, then click **Install after SFM closes**. Setup refuses a running or uncheckable SFM process and a busy Updater lock. It snapshots the entire ZIP and setup program before SFM closes, so Workshop unsubscription cannot change the bytes being installed.

Existing changed application files or partial CPM button installations cause a refusal. Existing customized Animation Groups data can be replaced only after explicit consent. The former bytes are verified and backed up before mutation. The installer publishes a durable transaction record before writes, verifies every installed file, and can restore an interrupted installation. The v1.0.0 ZIP is never modified.

After installation, **Scripts → SFM Character Tools → Manage Installation** opens the installed helper for verification, recovery, and conservative removal. It remains available after Workshop unsubscription. If a crash occurred before this launcher was installed, rerun the Workshop setup to recover the PREPARED transaction. Removal leaves changed files and data untouched and reports them. The running helper executable may remain until manually removed after closing setup. The Updater's lock and transaction/backups are not removed. If the user disabled the button in Autoinit Manager, installing the button files does not re-enable it.

The installation process does not provide a silent repair or upgrade path. Use the existing Control Group Updater for subsequent Animation Groups data updates.

## Release acceptance still required

This branch qualifies only disposable-folder behavior. A clean subscriber without uploader or plugin-loader extensions must receive the full payload intact. In real SFM, confirm launcher discovery, setup launch, normal SFM close followed by install, all four tools including the Autoinit button, installed management after unsubscription, and safe coexistence with the Control Group Updater. Keep publication separate from this PR.
