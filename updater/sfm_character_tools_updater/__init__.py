# -*- coding: utf-8 -*-
"""SFM Control Group Updater (SFM Character Tools External Updater) -- installed-publication backend.

Offline Updater v1 (updater_qualification/design/OFFLINE_UPDATER_V1_CONTRACT_AMENDMENT.md):
installation runs only while SFM is closed. This package is the one protected
activation/recovery backend of R2 C4-C12; every installed write goes through it.

L-1: Rebuild My Data, headless. L-2: Use Another TXT and Get Official Data from a local signed
package, headless, through the same backend and replacement route. L-3: Get Official Data online
(explicit-action release check and bounded download, then the L-2 path), headless. L-4: the Tkinter GUI
(gui/), the bounded worker under a Job Object (supervisor.py) and staging cleanup (staging.py). L-5: the
authority profile and signed installed-software inventory (compat/) and the one-folder package
(updater/packaging/).

VERSION is the application version (first public version 0.1.0). Animation-group data releases are
versioned separately (data-v1.0.0, ...).
"""

VERSION = "0.1.0"
TX_SCHEMA = "sct-updater-tx-1"
PREP_SCHEMA = "sct-updater-prep-2"
