# F-01 full-body S3, run 3: Process B retest with the revised A1 and the Apply button fix (operator procedure)

**Status:** prepared, **not run**. Running it, and every installation change below, needs the Owner's execution
approval.

**Run history:**
- Run 1 stopped after B1, on the A1 pre-check.
- Run 2 (`E:\SFM_U0B_Scratch\f01-full-body-s3-r2`) passed B1 and the pre-check (COMPATIBLE), then stopped at B2:
  Apply Pose stayed disabled for full-body poses because the Poses page considered only the arm regions.
  Commit `c2a2068` fixes it. Run 2's folder is preserved and never reused.

**Why the revised A1:** run 1 stopped after B1. The approved read-only A1 pre-check (run 1 `evidence\A1_PRECHECK.json`) found four
FK positions differing by 1 ULP to 2.6e-5 units: SFM's rotate tool rewrites positions with float32 noise. Astra's
bounded A1 revision, implemented in commit `381c071`, makes such poses compatible for Krystal and keeps the
destination's own FK positions.

**What run 3 reuses from run 1 (read only, pinned by hash):**
- the destination session `S3_DESTINATION.dmx` (`61df8bcd…`);
- the saved records `S3 Pose A`, the updated `S3 Pose B` and its Update Pose `.bak`, and the legacy `NQ1 Pose A`;
- the Process A observations `S0-01`…`S0-07` with their sidecars.

**Process A is not repeated.** Its Save New, Update Pose and record persistence passed in run 1. Run 1's folder is
never written: run 3 uses its own run folder, and the comparator checks Process A's observations against run 1's
build.

The steps and checks are those of `PROCEDURE.md` Process B, with four changes:
1. the A1 pre-check after B1 is a tool step, and Apply is allowed only on `PRECHECK COMPATIBLE`;
2. a Poses page UI smoke check (B1b) must show Apply Pose enabled for the selected full-body pose before B2;
3. B12's expected refusal is the proportions copy (shot10 differs in its scale state, which is checked before A1);
4. any operation slower than 5 s is reported as a usability finding.

## Identities

| Item | SHA-256 |
|---|---|
| Candidate CPM (commit `c2a2068`: revised A1 `381c071` and the Apply button fix) | `9a155bff002ba9bd1cd9dc59f924ff0fb1f95c167ddb9b3cc8d09282530dc214` |
| Qualification CPM (`build`: one line, `PROD_POSE_REGISTRY_MODE = u"qualification"`) | `814b6ec5125904b8801bef2d439af81d81028bf80c701c5169655b7f30f6b768` |
| Registries (pose / body) | `f445d5ef…` / `22dcd159…` |
| Published CPM (before and after) | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df` |
| Run 1 qualification CPM (Process A's observations) | `45cbaf9515829f7c2ecf18ab71bef11fde5e3f43c9a2c0c19ef61ccbf774e6ef` |
| Run 1 files reused | `s3_continuation.template.json` (`continuation` section) |

**Folders:**
- `<Q1>` is run 1, `E:\SFM_U0B_Scratch\f01-full-body-s3`. It is read only.
- `<Q2>` is run 3, a new folder: `E:\SFM_U0B_Scratch\f01-full-body-s3-r3`.
- `s3_tool <command>` means `python -I <REPO>\real_sfm_qualification\f01_full_body_s3\tools\s3_tool.py <Q2>\s3.json
  <command>`.

**Stop rule:** as in `PROCEDURE.md`. In addition, STOP on `PRECHECK INCOMPATIBLE`. Close SFM **without saving**, run
R2 (restore) and report. Restore is always permitted. Never save a session.

## Preparation (SFM closed)

| # | Action | Expected |
|---|---|---|
| P0 | Copy `s3_continuation.template.json` to `<Q2>\s3.json`. Fill in the paths, with `source_run` = `<Q1>`. | No `<…>` placeholder remains. |
| P1 | `s3_tool build` | `BUILT: … differs from the candidate in line N only`. The qualification CPM is `814b6ec5…`. |
| P2 | `s3_tool pre` | `PRE PASS`. Every run 1 source file verifies by hash. `<Q2>\sessions\` holds only `S3_DESTINATION.dmx` (a verified copy). Backups and the four inventories are recorded. |
| P3 | `s3_tool status` | `STATUS FRESH` |
| I0 | `s3_tool inspect` | `INSPECTED`. The destination equals run 1's pin `61df8bcd…`. |
| I1 | `s3_tool install` | `INSTALLED`: the qualification CPM and both registries; the journal is written first. |
| I2 | `s3_tool seed` | `SEEDED: 4 records and 14 Process A observations`. The library snapshot A is written. |
| I3 | `s3_tool check` | `"installation": "qualification"` |

## Process B (one SFM process; the source session is never opened)

Observe exactly as in `PROCEDURE.md`, with `S3_DIR = r"<Q2>"`. The observation labels and steps are unchanged.

| # | Action | Expected |
|---|---|---|
| B0 | Start SFM. Open `<Q2>\sessions\S3_DESTINATION.dmx`. Switch to the **Motion Editor**. Set the playhead to **0.3750 s**. Open CPM. Click Refresh Models, select **Krystal**, then the **Poses** tab. Set `S3_DIR` and `S3_REPO`. | `S3 Pose A`, `S3 Pose B` and `NQ1 Pose A` are listed. |
| B1 | Observe. | `S3 STEP B1 (S0-08): OK` |
| **B1a** | **Do not Apply.** Leave SFM open. In a command prompt, run `s3_tool precheck`. It reads only the B1 observation, the record and the staged CPM's own code. | `PRECHECK COMPATIBLE`. `<Q2>\evidence\A1_PRECHECK.json` lists the pinned FK positions that differ from the pose, each with the destination value kept and its distance (expected: the four run 1 channels, each ≤ 0.00005). It also reports the plan, with every FK position at the destination's value. On `PRECHECK INCOMPATIBLE`: STOP. |
| **B1b** | **UI smoke check.** In the Poses list, click `S3 Pose A` once to select it. Do not click Apply. In the Script Editor run `execfile(S3_REPO + r"\real_sfm_qualification\f01_full_body_s3\observer\F01_S3_UISmoke.py")`. It reads the button and page state only. | `S3 UI SMOKE: Apply Pose ENABLED for S3 Pose A (full body): OK`, and the **Apply Pose** button is visibly enabled. `<Q2>\observations\UI-SMOKE.json` is written. On `DISABLED - STOP` (or any STOP line): STOP. |
| B2–B11 | As in `PROCEDURE.md`. | As in `PROCEDURE.md`. In B2 the whole body takes posture A, while the destination's FK bone positions are kept (they differ by at most 0.00005 units, which is invisible). |
| B12 | Select `S3 Pose A` and click **Apply Pose** (shot10). Observe. | Refused: `This pose was saved with different body proportions and can't be applied safely. Nothing was changed.` |
| B13–B18 | As in `PROCEDURE.md`. | As in `PROCEDURE.md`. |

For B2, B6 and B14, note the time from **Apply Pose** to the final status in `<Q2>\OPERATOR_NOTES.txt`.

## R: evidence, restoration and verdict (SFM closed; always)

| # | Action | Expected |
|---|---|---|
| R0 | `s3_tool library B` | `LIBRARY B: 4 files recorded` (the same files and hashes as library A) |
| R1 | `s3_tool collect-logs` | `LOGS COLLECTED` |
| R2 | `s3_tool restore` | `RESTORED`:<br>- the published CPM `ccbed9d7…` is back;<br>- both registries are removed;<br>- the run's Poses folder is moved into `<Q2>\evidence\library_poses`;<br>- every inventory equals its pre-run baseline. |
| R3 | `s3_tool check` | `"installation": "published"` |
| R4 | `s3_tool compare` | `<Q2>\evidence\S3_VERDICT.md`, ending `verdict: PASS` |

**Rollback:** close SFM without saving, then `s3_tool restore`; it can be re-run. Run 1's folder is never changed. A
paused CPM needs only an SFM restart after restore.

## Comparator changes for the continuation runs (run 2 onwards)
- **Continuation:** Process A's observations must carry run 1's qualification build (`45cbaf95…`); Process B's must
  carry the continuation run's.
- **`ui.full_body_apply_enabled_before_apply`:** `UI-SMOKE.json` shows Apply Pose enabled, in direct mode, for
  `S3 Pose A` (`full_body`). It must come from the same SFM process as B1, with run 3's qualification build loaded
  and no recovery pause.
- **`precheck.revised_A1_compatible_before_apply`:** `A1_PRECHECK.json` exists, reports compatible, was made with
  run 3's qualification build, and was taken on B1.
- **Update Pose backup:** `library.records_unchanged_by_the_apply_process` now covers every file, including the
  `.bak`. `library.update_backups_are_the_replaced_records` requires the `.bak` to be `S3 Pose B`'s pre-update
  record (posture B, observation A4).
- **Performance:** the classes are unchanged, but every class above `responsive` (above 5 s) is reported as a
  usability finding, even when the verdict is PASS.
