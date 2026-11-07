# F-01 full-body S3, run 4: supplemental run B9–B17 (operator procedure)

**Status:** prepared, **not run**. It needs the Owner's execution approval.

**Why:** run 3 (`E:\SFM_U0B_Scratch\f01-full-body-s3-r3`) established the full-body workflow natively (B1–B11), but its
comparator verdict is FAIL for procedural reasons:
- B12 was not observed;
- B13–B17 ran on shot10 instead of shot15, so the legacy Apply moved nothing (shot10's arm is `NQ1 Pose A`'s own
  source);
- B17 was impossible after the timeline was scrubbed.

Its B10 popup also showed the generic "CPM couldn't read everything…" message, which commit `e98b90b` corrects.

Run 4 repeats **only B9–B17**, in a fresh SFM process, with the corrected candidate. Process A and B1–B8 are not
repeated. Run 3's evidence and verdict are not changed.

## Identities

| Item | SHA-256 |
|---|---|
| Candidate CPM (commit `e98b90b`) | `f6098b3a61bbc17b435205741761cf6993fc726d94b575d2c9a4fd600eb4e6e9` |
| Qualification CPM (`build`: one line) | `12b59b295c2062487bd7613a5e9b207420df82fcad0ffac7fe5076bd079a98a0` |
| Difference from run 3's candidate (`9a155bff…`, `c2a2068`) | `prod_pose_require_motion_editor` (the timeline mode checked first in both preflights) and the editor-mode copy: 14 lines added, 1 changed |
| Registries (pose / body), published CPM | `f445d5ef…` / `22dcd159…`, `ccbed9d7…` |
| Run 1 files reused (read only) | `s3_supplement.template.json` (`continuation` section: the destination, `S3 Pose A`, `S3 Pose B` and its `.bak`, `NQ1 Pose A`) |

**Folders:**
- `<Q4>` is the new run folder: `E:\SFM_U0B_Scratch\f01-full-body-s3-r4`.
- `s3_tool <command>` means `python -I <REPO>\real_sfm_qualification\f01_full_body_s3\tools\s3_tool.py <Q4>\s3.json
  <command>`.

**Stop rule, strictly:** STOP at the first `MISMATCH - STOP`, unexpected status, failed observation, or
`LEGACY PRECHECK NOT DISTINCT`. Do not take the next observation, do not repeat a label, do not scrub the timeline or
change editors except where a step says so. Close SFM **without saving**, then run R2 (restore). Restore is always
permitted.

## Preparation (SFM closed)

| # | Action | Expected |
|---|---|---|
| P0 | Copy `s3_supplement.template.json` to `<Q4>\s3.json`; fill in the paths (`source_run` = run 1). | No `<…>` placeholder remains. |
| P1–P3 | `s3_tool build`, `s3_tool pre`, `s3_tool status` | `BUILT` (qualification `12b59b29…`), `PRE PASS` (published installation verified, inventories recorded), `STATUS FRESH` |
| I0–I3 | `s3_tool inspect`, `install`, `seed`, `check` | `INSPECTED` (destination `61df8bcd…`), `INSTALLED`, `SEEDED`, `"installation": "qualification"` |

## Process (one SFM process)

Observe exactly as before, with `S3_DIR = r"<Q4>"`. Each observation must end with `OK`.

| # | Action | Expected / gate |
|---|---|---|
| S0 | Start SFM. Open `<Q4>\sessions\S3_DESTINATION.dmx`. Leave the timeline in the **Clip Editor** (switch to it if needed). Set the playhead to **0.3750 s** (shot13). Open CPM. Click Refresh Model List, select **Krystal**, then the **Poses** tab. Set `S3_DIR` and `S3_REPO`. | `S3 Pose A`, `S3 Pose B` and `NQ1 Pose A` are listed. |
| B9 | Observe. | `S3 STEP B9 (S0-16): OK` (Clip Editor, shot13, 0.375). |
| B10 | Select `S3 Pose A` and click **Apply Pose**. Read the popup, then click OK. Observe. | Popup and status: `Switch to the Motion Editor to apply a pose. Nothing was changed.` |
| B11 | Switch the timeline to the **Motion Editor**. Set the playhead to **0.4167 s** (shot10). Click Refresh Model List, select **Krystal**, then the Poses tab. Observe. | `S3 STEP B11 (S0-18): OK` (Motion Editor, shot10, 0.4167). |
| B12 | Select `S3 Pose A` and click **Apply Pose**. Click OK on the popup. **Observe immediately.** | Popup: `This pose was saved with different body proportions and can't be applied safely. Nothing was changed.` |
| B13 | Set the playhead to **0.2083 s** (shot15). Click Refresh Model List, select **Krystal**, then the Poses tab. Observe. | `S3 STEP B13 (S0-20): OK` (Motion Editor, **shot15**, 0.2083). |
| **Gate** | **Do not Apply.** Leave SFM open and report. The operator (Claude) runs `s3_tool legacy-precheck`. | `LEGACY PRECHECK DISTINCT`: shot15's left arm differs visibly from `NQ1 Pose A`'s source arm (B11). On `NOT DISTINCT`: STOP. |
| B14 | Select `NQ1 Pose A` and click **Apply Pose**. Note the time. Observe. | `Pose applied: NQ1 Pose A.` Only the left arm moves, visibly. |
| B15 | Click **Apply Pose** again. Observe. | `Already matches this pose.` |
| B16 | Click the viewport, then press **Ctrl+Z** once. Observe. | The arm returns. |
| B17 | **Immediately** press **Ctrl+Y** once (no scrubbing, no editor change). Observe. | The arm takes the pose again. |
| B18 | Exit SFM. **Do not save.** | |

## R: evidence, restoration and verdict (SFM closed; always)

| # | Action | Expected |
|---|---|---|
| R0 | `s3_tool library B` | The same 4 files as library A |
| R1 | `s3_tool collect-logs` | `LOGS COLLECTED` |
| R2 | `s3_tool restore` | `RESTORED`: published CPM back, both registries removed, Poses folder into `<Q4>\evidence\library_poses`, every inventory equal to its baseline |
| R3 | `s3_tool check` | `"installation": "published"` |
| R4 | `s3_tool compare` | `<Q4>\evidence\S3_VERDICT.md`, `verdict: PASS` |

## The supplement comparator (`"supplement": true`)

It checks B9–B17 only, all from one SFM process on the qualification build:
- **refusals:** B9→B10 and B11→B12 unchanged (document digest and Undo). The CPM log shows the Motion Editor
  message (`editor-mode-refused`) and the proportions message, with no writes;
- **legacy:** the pre-check distinct before the Apply; the three left-arm channels keyed and the arm moved by at least
  5°, and its bones now equal `NQ1 Pose A`'s source arm within 0.01°; everything else unchanged; one owned Undo
  entry; the repeat a true no-op; Undo restores B13 with Redo available; Redo restores B14; CPM's own P6/P7
  verified;
- **no recovery pause or uncertainty**, restoration complete, and the destination not saved.
