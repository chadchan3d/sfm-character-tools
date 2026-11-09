# F-01 SFP-1 — NQ1 Native Qualification Results (Selected parts on Krystal)

**Date:** 2026-11-08. **Verdict: PASS (134/134 comparator checks) with a performance finding.** Accepted by the Owner.
Owner-operated in SFM; preparation, installation, evidence collection, restoration and comparison run with the kit's
tools. Nothing enabled for production, merged, pushed or released.

## 1. Identities and scope

| Item | Value |
|---|---|
| Implementation commit | `0b839cef4c9cacee90ac0a05be409ed31cd3ae95` (CPM `2d791dec96c0b4816693c369fe5f956de5e1ed93a1ecea8b95fd0d5515b9cc6a`) |
| Kit commit | `7f62c62722f388e45fa66c00bd00e4b958bde918` (`real_sfm_qualification/f01_sfp1_nq/`) |
| Qualification build (installed for the run only; one line, `PROD_POSE_REGISTRY_MODE = u"qualification"`) | `b58ae9ba0dfee675038bf6b6bf9e5ac27e3e1adb13ed3b0ba93cdc6c11140d05` |
| Published CPM (before and after) | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df` |
| Model | Krystal (`krystal2020.mdl`, rigged) |
| Fixture | R2 disposable fixture `259ea8a614bc9e43e5bde15afdf38e1a1295dffb50b14cf75692df4221a05a2c` (source shot15 0.2083 s; destination shot13 0.3750 s and shot15 0.2083 s in a separately prepared session) |
| Legacy pose | `NQ1 Pose A` (version 1 left arm) `4916a7243193306ab7a93dec9fbc988b079c9af4c3bb0e9828a5b2d89cef3541` |
| Scope run | Processes A and B of the kit's procedure; the optional prop Process C was not run |

## 2. What NQ1 qualifies

The tested Selected parts workflow on Krystal, natively:
- **Save New and Update Pose** of the 15 left finger and thumb bones as version 3 Selected parts (`direct_fk_v1`
  revision 1; scope label `LeftFingers`); each record equals the posed fingers (0.0° error); Save and Update wrote
  nothing to the scene; Update replaced the record in place.
- **Independent reload**: Apply ran in a separate SFM process that opened only the destination session.
- **Apply** into a destination wrist and arm posed differently: fingers within 0.01° of the record with the
  destination's own offsets; only finger channels changed; every other bone, control, the model, rig handles and all
  animation outside the instance unchanged.
- **Undo/Redo** (one owned entry per Apply), **true no-op** repeat, **updated keys** in place, **verified Abort**
  (injected after-writes fault), **Clip Editor refusal** (nothing written).
- **Composition with the existing v1 left-arm pose**: the legacy arm Apply changed only its arm channels and moved
  the wrist visibly while the fingers kept their curl; the grip then applied on the moved arm without moving it; Undo
  and Redo through both.
- CPM's own log: three scoped Applies owned and P7-verified, the no-op, update-only keys, the verified Abort, the
  legacy Apply verified, and no recovery or uncertainty.

**Not qualified by NQ1:** generic version 3 Full body; version 2 Full body composition; external prop constraints;
other character rigs; NQ-S1, NQ-S4, NQ-S6 or additional NQ-S7 scenarios.

## 3. Performance finding

| Apply | Blocking (start to final status) | Total (including CPM's deferred verification) |
|---|---|---|
| B2 (grip) | 3.7 s (3661 ms) | 5.3 s (5315 ms) |
| B6 (updated point) | 3.3 s (3285 ms) | 4.8 s (4782 ms) |
| B12 (grip after the legacy arm) | 3.3 s (3313 ms) | 4.8 s (4781 ms) |

The kit's criteria are responsive ≤ 5 s and limit 30 s. B2's total exceeded 5 s by 0.3 s, so the comparator classes
performance as a **finding** (PASS, for the Owner's decision); this is a passing qualification with a performance
finding, not a performance-free result. The Owner observed about 3 seconds or less and no freezing.

## 4. Restoration and integrity

`restore` put the published CPM back, removed both registries, moved the run's Poses folder into evidence, restored
SFM housekeeping and `.pyc` files, and verified that **all four protected inventories (scripts, `usermod\cfg`, the CPM
library, sessions) equal their pre-run baselines** (`inventory_problems: []`); the installation journal ends
`restored`; `check` reports `published`. No session was saved during the run (the destination still hashes to its
pinned value).

## 5. Deviations

- **Destination filename case.** SFM saved the prepared destination as `sfp1_destination.dmx`; `inspect` refused (the
  tool matches names exactly). Only the name's case was corrected to `SFP1_DESTINATION.dmx`; the bytes were verified
  unchanged before and after (`95345cecf45c493d954f398a90d8837fb0b6436950a1c612055a6e9334673c14`), then pinned.
- **Procedure wording.** The library steps expected 3 files; 4 were recorded, the fourth being the `.bak` backup that
  Update Pose writes by design. Library A and B are identical. The procedure text is corrected in the same commit as
  this record.

## 6. UI findings

The Owner's Process A usability observations were supplied separately and adjudicated by Astra (accepted; a separate
record, not in this repository). They are not implemented here. In Process B the Owner observed no further UI issues.
The Owner's screenshots and operator notes are not in the run folder and are not archived with this evidence.

## 7. Evidence (run folder `E:\SFM_U0B_Scratch\f01-sfp1-nq1`, outside Git)

| File | SHA-256 (prefix) |
|---|---|
| `evidence\SFP1_VERDICT.json` | `d0cb4f8cd653a6f1` |
| `evidence\SFP1_VERDICT.md` | `e6dae3191658e719` |
| `compare_console.txt` (comparator output) | `74732b484658872b` |
| `evidence\restore.json` | `c1a35e92896bb4c9` |
| `evidence\logs\` CPM logs, pid15164 (Process A) and pid17260 (Process B); `LOGS.json` | `59fd2e0adfaf1da6`, `1701c0aa15880cd6`; `95cec5b473ed8c27` |
| `evidence\library_poses\krystal2020--7d2aee52ef3a\`: `SFP1 Grip--ffad379ba3b6.json`, `SFP1 Point--ed611a3a785f.json`, its `.bak`, `NQ1 Pose A--5273df2209ca.json` | `a5bce5f0c3d6686b`, `aae725c23d7abb4a`, `52ed200dc0b89d6f`, `4916a7243193306a` |
| `evidence\library_A.json`, `library_B.json`, `destination.json`, `seed.json` | `85e0bf211178859e`, `be4dfedd365e9f93`, `4d303c1186611fb5`, `ae72d0b20475df89` |
| `staged\IDENTITIES.json`; `pre_run\install_journal.json` | `6db93d6301d97f83`; `5edeb52111ecd06b` |
| `observations\` (A1–A7, B1–B16 with sidecars; UI-A, UI-B) | 48 files |

NQ1 is native evidence for the tested workflow; it is not authorization to ship the feature.
