# Workshop Setup v1.1.0 native upgrade acceptance, run 1: results

**Authority:** "SFM Character Tools v1.1.0 — Native Workshop Upgrade Test GO" and "Workshop v1.1.0 — Owner Acceptance
and Restoration" (Owner, Option A, 2026-11-21). Kit at `82f3b32`; run folder `E:\SFM_U0B_Scratch\workshop-v110-native-r1`
(evidence preserved, not committed). Staged Setup `6fb5ac65…`, release ZIP `0f64eb13…`.

## 1. Verdicts, reported separately

| | Result |
|---|---|
| **Owner** | **W1–W6 completed successfully, no problems observed** (Owner confirmation). Individual on-screen texts were not separately recorded and are not reconstructed here |
| **Automated update check** | **CHECK-UPDATE FAIL**, kept unchanged (`evidence\CHECK_UPDATE.json`). It ran after the uninstall had already happened, so it measured the uninstalled state: no installation record, managed files absent. The installed v1.1.0 state was **never captured by an automated snapshot**. Not an observed installer defect |
| **Automated uninstall check** | **CHECK-UNINSTALL PASS**, every gate (`evidence\CHECK_UNINSTALL.json`) |
| **Restoration** | **RESTORED** exactly (`evidence\RESTORE.json`) |

## 2. Independently verified operations (files and logs, all after `pre` at 00:18 local)

| Step | Evidence |
|---|---|
| Preflight | `pre` PASS: Setup record v1.0.0 (`5323b143…`), CPM `ccbed9d7…`, no registries; three usermod trees, the preset library and Autoinit's settings backed up and verified; Steam payload and Autoinit code recorded |
| W1–W2 update by the v1.1.0 Setup | Setup's verified TXT backup created at 05:20:29Z, byte-identical to the pre-test TXT; the installed Setup helper afterwards is the v1.1.0 build `6fb5ac65…` (v1.0.0's was `9375f0ff…`) |
| W3–W5 CPM v1.1.0 in SFM | CPM log `…05-22-21Z - pid32528 - 99dd93…` (`528d7738…`, preserved) written by the v1.1.0 production CPM `b89af5a8…`: Refresh Models, Help, Select Model ×2, **Save Pose `WU Pose` from `foxmccouldwm1` verified** (structural rig route; the generic no-rig route declined the rigged Fox first, as designed), **Pose Info completed**. No failure, recovery or lockout outcome |
| Pose record | `WU Pose--f57ee396dfa0.json`, `pose_sources.json` and `pose_rigs.json` (Rig `rig_biped`, scene `rig_biped_foxmccouldwm1`) written in the Fox's library folder; preserved in `evidence\after_restore_removed\library\` |
| W6 uninstall | the Setup record and every v1.1.0 program, both registries and the management launcher removed; TXT and all Setup and updater TXT backups kept; the only remaining program file the running Setup executable (expected, README) |

**Not independently verifiable from the evidence:** that Setup displayed installed 1.0.0 / package 1.1.0 (W1); that CPM was opened from the toolbar button rather than the Scripts menu (W4; CPM logs no launch source); that existing Body Presets and Expressions were displayed (W3; no preset operation was logged, and no preset file changed); that Manage Installation displayed 1.1.0 (W6). These rest on the Owner's confirmation.

## 3. Protection and restoration

- **Throughout** (CHECK-UNINSTALL): nothing outside the managed set, installer state, bytecode and SFM housekeeping
  changed; no pre-existing preset file changed or deleted (additions: the three WU Pose files only); Steam's Workshop
  payload (the four v1.0.0 files) unchanged; Autoinit Manager's code unchanged; Autoinit's settings unchanged.
- **Restore:** 1,031 files restored from the backup (the v1.0.0 programs and Setup state); four moved to evidence (the
  run's TXT backup and the three WU Pose files). After restore, every inventory equals `pre`: `usermod\scripts`,
  `usermod\cfg`, `usermod\tools`, the preset library, the Workshop payload and Autoinit's settings; directory trees equal;
  Autoinit code unchanged. Independently: Setup record package `5323b143…`, CPM `ccbed9d7…`, Setup helper `9375f0ff…`,
  no registries.
- **Sessions:** `WU_SESSION.dmx` still the R2 fixture `259ea8a6…` (never saved); the protected
  `krystal_s2fm_alone_port.dmx` still `5a6a6cde…`.

## 4. Release assessment

**Sufficient for Workshop publication without repeating the test, in my assessment, with one documented gap.**

- Everything the upgrade must do is covered: the offline suite (50/50 against the published ZIP) runs the same
  `core.install` path from a real v1.0.0 Setup installation to v1.1.0 and checks every installed file, the registries,
  the TXT backup and data preservation; the native run shows the same Setup build performing that update on the real
  installation (backup, installed v1.1.0 helper), CPM v1.1.0 running from it with a verified pose save and Pose Info,
  and the updated Manage Installation uninstalling correctly (automated PASS).
- **Gap:** no automated snapshot of the installed v1.1.0 state on the real installation. Its content is the part the
  offline tests verify most directly (every file hash after `core.install`), and the native evidence (the v1.1.0 helper installed,
  the v1.1.0 CPM running from the installation) is consistent with it. Whether the two registry files were installed
  cannot be shown from the native evidence alone (they were absent again after the uninstall); the offline upgrade test
  verifies their installation. The Owner's W1/W3/W4/W6
  observations are confirmations without recorded detail.
- The Workshop item itself was not touched; the post-publication check that Steam delivers the staged hashes remains
  part of publication.
