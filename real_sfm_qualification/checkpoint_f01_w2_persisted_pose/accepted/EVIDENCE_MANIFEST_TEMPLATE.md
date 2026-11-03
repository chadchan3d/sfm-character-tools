# F-01 W2 native qualification evidence (template)

To be completed only after a separately authorized native run. Use placeholders for every private path or
file name. The raw reports stay private.

## Identities

| Item | SHA-256 |
|---|---|
| Design contract | `168d10910ac48d32016566e29d24823175b56f8a6459e8e459a1143ee62cbe43` |
| `f01w2_core.py` / `f01w2_capture.py` / `f01w2_apply.py` | |
| `config.json` (private) / `HARNESS_SHA256.json` | |
| Original session (unchanged before and after) | |
| R2 fixture = capture copy = application copy (unchanged before and after) | |
| CPM source / installed CPM (published build; no M-06 installation) | |
| Published pose `left_arm_pose.f01w2.json` (bytes) | |

## Process separation

| Process | pid | Creation FILETIME | Provider |
|---|---|---|---|
| A (capture) | | | `windows-kernel32` |
| Gate | | checked FILETIME: | `windows-kernel32` |
| B (application) | | | `windows-kernel32` |

**Required order:** A created < gate checked (A not running, no `sfm.exe`) < B created.

| Strict lookup of process A | State (`ABSENT`, `EXITED` or `PID_REUSED`; never `UNKNOWN`) | Native error, if any |
|---|---|---|
| At the gate | | |
| At APPLY (`process_a_now`) | | |

## Ledger

| # | Report | SHA-256 | Status | Propagation |
|---|---|---|---|---|
| 01 | CAPTURE | | | — |
| 02 | PROCESS_GATE | | | — |
| 03 | APPLY | | | |
| … | | | | |
| — | FINAL | | | |

## Results

| Measure | Result | Tolerance |
|---|---|---|
| Live cross-check, implementation A vs B (position / angle) | | 1e-4 / 0.001° |
| Shoulder guard | | 0.001 |
| Primary oracle, max local orientation error | | 0.01° |
| Secondary oracle, max world position / orientation error | | 0.001 / 0.01° |
| Aborted test writes | | exactly 1, restored |
| Committed writes (per-channel indices, ticks 30000 / 70415) | | exactly 6 |
| Undo / Redo / final Undo ownership and exact states | | all |
| Required Undo/Redo fields readable at capture, preflight, the Abort test, the commit, every callback boundary and every history operation | | all |
| Required history after the Abort test equal to before it; aborted labels absent | | exact |
| `observed_changes` at every observation and before every history operation | | `[]` |
| Unrelated changes at every observation | | 0 |
| Hand-target residual (diagnostic) | | — |

## Not claimed

- The source shot was not re-observed in process B.
- No other limb, rig, model, partial pose or key creation is qualified.
