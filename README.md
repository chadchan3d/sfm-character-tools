# SFM Character Tools

SFM character models use different bone and flex names and layouts. SFM Character Tools helps animators use a consistent control layout and reuse character settings across shots.

**Get v1.0.0:** [Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3826760383) · [GitHub download](https://github.com/chadchan3d/sfm-character-tools/releases/tag/v1.0.0)

## What's included

- **Control Group Normalizer** rebuilds model control groups into a consistent layout, making bones and flexes easier to find without changing the shot structure.
- **Character Preset Manager (CPM)** saves and applies body settings and facial expressions across shots. It also fits clothing to characters.
- **SFM Control Group Updater** updates Animation Groups data and builds its matching sidecar after you edit or replace the TXT. It updates recognition data, not the applications.

The included Animation Groups file catalogues bone and flex names from more than 9,000 SFM models, providing broad model support without model-by-model setup. Its matching sidecar is included, so the tools can run immediately after installation.

## Installation

**Steam Workshop:** [Subscribe to SFM Character Tools](https://steamcommunity.com/sharedfiles/filedetails/?id=3826760383), open SFM, then choose **Scripts → SFM Character Tools → Install or Update (Windows Setup)**. Close SFM while keeping Setup open, install the tools, then close Setup and restart SFM. Setup backs up your existing Animation Groups TXT before replacing it; custom edits are not merged.

**GitHub manual installation:** Download the software ZIP from the [v1.0.0 release](https://github.com/chadchan3d/sfm-character-tools/releases/tag/v1.0.0). Close SFM, extract the ZIP, and copy its `usermod` folder into `SourceFilmmaker/game`, merging with the existing folder. **Back up a customized `usermod/cfg/sfm_defaultanimationgroups.txt` first:** manual installation replaces it.

Open **Scripts → SFM Character Tools** to use the tools. See the [release README](release/v1.0.0/README.txt) for complete installation and usage instructions.

## Optional CPM toolbar button

The button opens Character Preset Manager directly from the Animation Set Editor toolbar. [Autoinit Manager](https://steamcommunity.com/sharedfiles/filedetails/?id=3400621327) is required only for this button; the three main applications work without it.

Workshop Setup installs both button files automatically. For a GitHub manual install, close SFM and copy `OPTIONAL - CPM Button/usermod` into `SourceFilmmaker/game`, merging folders and replacing files when prompted.

To enable or disable the button, open **Scripts → kiwifruit → Autoinit Manager**, tick or untick **ChadChan3D_CPM_ASE_Button**, then restart SFM. The button has been tested alongside Extended Animation Set Editor Buttons, a separate Workshop addon.

## Model compatibility and contributions

Many models are still unrepresented. Share scan data from your model library to improve bone and flex recognition for everyone. Your scans help the Normalizer organize more models correctly and Character Preset Manager support more characters.

Use [SFM Model Scanner](https://github.com/chadchan3d/sfm-model-scanner) and share your scan data through [ChadChat](https://chadchan3d.com/chat/), where you can also get help. See the [release README](release/v1.0.0/README.txt) for the scan and export procedure.

## Known limitations

- **Normalizer rebuilding cannot be undone with SFM Undo.** Save your project before rebuilding. CPM uses the shot under the playhead; Normalizer's Selected Shot(s) uses the Clip Editor selection.
- Large Normalizer workloads can exhaust SFM's limited memory. A resource stop reduces the risk but cannot prevent every crash. If it stops, save, restart SFM, and finish the remaining shots with Selected Shot(s).
- Some existing bone-scale configurations can prevent Body Preset saving. See [known issues](docs/MAINTENANCE_BACKLOG.md).

## Development and documentation

- **Animation Groups and shared authority:** [canonical Master](sfm_defaultanimationgroups.txt), [sidecar source](tools/sfm_master_sidecar/) and [Master content records](audit/master-content/README.md).
- **Applications:** [Normalizer](audit_external_runtime/Rebuild_Control_Groups_Normalizer.py), [CPM](cpm/app/SFM_Character_Preset_Manager.py), [CPM convergence history](cpm/qualification/CPM_CONVERGENCE_LEDGER.md), and [Control Group Updater](updater/packaging/README.md).
- **Workshop distribution:** [installer source and documentation](workshop_installer/README.md).
- **Verification and maintenance:** [tests](tests/), [sidecar qualification records](docs/qualification/README.md), [maintenance backlog](docs/MAINTENANCE_BACKLOG.md), and [Master editing guidance](CLAUDE.md). Detailed historical evidence remains in the linked project records.

## License

Original material in this repository, wholly authored within this project, is released under [CC0 1.0](LICENSE): public domain dedication, no rights reserved. This does not extend to externally owned material referenced but not included here, such as historical Normalizer/T130 oracle sources or other third-party inputs a harness may optionally consume. CC0 applies only to material this repository contains and that ChadChan3D has the right to dedicate.
