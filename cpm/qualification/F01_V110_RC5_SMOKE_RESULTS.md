# F-01 v1.1.0 RC5 final production-native smoke: results

**Authority:** "SFM Character Tools v1.1.0 — README Integration and Final Release Smoke GO" (2026-11-20); results
reported in "F-01 RC5 — Final Production Smoke Results". Kit `real_sfm_qualification/f01_v110_rc4_smoke/` at `0fb04b3`
(package pin moved to RC5 before the run); run folder `E:\SFM_U0B_Scratch\f01-v110-rc5-smoke-r1`.

## 1. Verdicts, reported separately

| | Result |
|---|---|
| **Automated (unchanged analyzer `079c86a9…`)** | **SMOKE FAIL (15/23)** in procedure order (restore, then analyze); see section 3 |
| **Owner visual** | **PASS**, as given: "All steps worked as expected, including Fox and Tails pose operations, Pose Info, Undo/Redo and repeat Apply. No problems were reported." The item-by-item record was not filled in |
| **Restoration** | **RESTORED**: published CPM `ccbed9d7…`, both registries removed, preset library files and folders equal to the pre-run backup, no protected-inventory problems |

The automated FAIL is **missing evidence, not a product failure**: no step was refused, failed or entered recovery, and
every operation that ran passed. But the CPM log does not contain the Fox steps, the repeat Apply or a second Pose
Info, which the Owner reports as done. That discrepancy is unresolved (section 4).

## 2. What ran (the one CPM log of the run)

Log `CPM - 2026-11-21_03-31-22Z - pid19148 - 3f0606 - 001.log` (`63c989af…`), written by the production CPM
`b89af5a8…` installed byte-for-byte from the RC5 package `baadc4be…` (production registry mode). It is the only CPM log
created after installation. CPM was open 22:31:22–22:33:31 local time.

| op | Operation | Character | Outcome |
|---|---|---|---|
| 1–3 | Refresh Models ×2, Select Model | | completed |
| 4 | Save Pose | milestailsprower2 | no-op (cancelled) |
| 6 | Save Pose `RC4 Sit` (Full body, structural adapter revision 2) | milestailsprower1 (original Tails) | verified |
| 8 | Apply Pose `RC4 Sit` | milestailsprower2 (new, chest-rigged Tails) | verified: `RIG-adapted` (`bip_spine_3` → constrained; `rig_chest` destination-only); bounded offsets within Astra's limits (max 0.0013°, 6.0e-6 units); P7 reproduction 0.000953 units / 0.0204° (`bip_knee_R`) within 0.01 / 0.1°; one Undo entry `Apply Pose RC4 Sit` |
| — | SFM "Select .MDL file" dialog opened and closed | | (no CPM operation) |
| 9 | Pose Info | milestailsprower2 | completed |

Library during the run: `RC4 Sit--a07269e2ca6c.json` (`a76b7f7b…`), `pose_sources.json` and `pose_rigs.json` (entry
label `rig_biped`, scene `rig_biped_milestailsprower1`) in the Tails folder. No Fox file.

## 3. Automated verdict

Two runs of the unchanged analyzer, both kept:

- **First run, out of order** (before `restore`): `E:\SFM_U0B_Scratch\f01-v110-rc5-smoke-r1\evidence\RC4S_VERDICT.json`
  `f00f3687…` — **INCOMPLETE (9/23)**. My error: the procedure analyzes after restoring (R2 then R3), so the
  restoration checks failed and the record checks could not read the restored-library evidence yet.
- **Procedure order** (after `restore`, on an exact copy of the evidence without the first verdict):
  `E:\SFM_U0B_Scratch\f01-v110-rc5-smoke-r1-postrestore-analysis\evidence\RC4S_VERDICT.json` `159f1e92…` — **SMOKE
  FAIL (15/23)**.

| Gate | Pass | Fail |
|---|---|---|
| EVIDENCE | build staged; production-mode check; one CPM log; log written by `b89af5a8…`; installation restored; library restored; library changes expected | |
| FOX | record leaves (vacuous) | saved once; admitted by the structural adapter; structural Full body record; applied and verified |
| TARGET | | Fox applied to another instance of the same model |
| TAILS | saved once from the original Tails; admitted by the structural adapter; structural Full body revision 2 | |
| CROSS | applied to another Tails and verified; adapted to the chest rig; reproduction within the revised envelope | repeat Apply is a no-op without Undo |
| DISPLAY | | Pose Info opened for both (1); scene rig recorded for both (Fox missing; Tails `rig_biped`) |
| CLEAN | no refusal, failure or recovery | |

Every failed check is an absent step: Fox Save, Fox Apply and its target, the repeat Apply, and Fox's Pose Info.

## 4. Discrepancy and what would close it

The Owner reports Fox operations, Undo/Redo and repeat Apply as done. The run's only CPM log records none of them, the
library gained no Fox pose, and no other CPM log exists after installation. Undo and Redo are SFM actions and are not
logged by CPM, so the Fox Undo/Redo and the final Undo cannot be checked from the log either way.

Not repeated or reinterpreted here. Closing it needs an Owner decision, for example a short re-run of the missing steps
(Fox Save, Pose Info, Apply, Undo/Redo; the `RC4 Sit` repeat Apply) with the same package and kit in a new run folder,
or an explicit adjudication accepting the evidence as it stands. Each needs separate authorization.

## 5. Restoration (verified)

- `restore` (22:36:35): installation **published** (CPM `ccbed9d7…`), registries absent, `inventory_problems: []`
  across the four protected inventories (scripts, cfg, preset library, sessions).
- Library cleanup: run differences (the three Tails files) moved to `evidence\library_after`; files and folders equal
  to the pre-run backup; the run-created Tails folders removed.
- Sessions: `RC4_SESSION.dmx` still hashes to the R2 fixture `259ea8a6…` (never saved); `RC4_SPARE.dmx` still
  `61df8bcd…` (never opened). The protected `krystal_s2fm_alone_port.dmx` hashes to its pre-run inventory value
  `5a6a6cde…` (read only).
