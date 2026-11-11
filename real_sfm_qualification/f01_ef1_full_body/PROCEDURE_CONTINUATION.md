# F-01 EF-1 continuation (run 2): Process B on run 1's fixtures (operator procedure)

**Status:** prepared offline, **not run**. Running it needs the Owner's separate execution approval.

**What it is:** run 1 (`E:\SFM_U0B_Scratch\f01-ef1-full-body`) stopped at B2 and B3, refused before any write under
the former offset limit (`evidence\EF1_STOPPED.json`). After R3 Amendments 01 and 02, this run repeats **Process B
only**. It uses verified copies of run 1's two pinned sessions and run 1's natively saved `EF1 Body` record, byte for
byte. The destination keeps its six SFM-drifted offsets.
- **Process A** (Save New, the native A1–A3 observations, UI-A) is **inherited** from run 1. It is copied into
  `<Q>\inherited`, verified against run 1's pins, and reported as `inherited.*`. It is not re-observed.
- **Process B** is this run's own native evidence, under the Amendment 02 qualification build.
- The verdict states this provenance. The two runs are never presented as one uninterrupted qualification.
- Run 1 is only read. Its whole folder is fingerprinted at `pre` and must be unchanged at `compare`.

| Item | Value |
|---|---|
| Qualification CPM | `bb0433a985620d599fc75574ab749b3b8c603488f812612afdd79a7dfe17c343` (candidate `3da2b653…`, one line, 42118). Run 1's `a378e25a…` and Amendment 01's `fd0844cf…` are refused by `build`. |
| Sessions (run 1, copied, verified) | `ef1_source.dmx` `cc3d2745…`, `ef1_destination.dmx` `de31257b…` |
| Record (run 1, seeded byte for byte) | `EF1 Body--a236dddc4e22.json` `0e0390e0…` |
| Inherited Process A evidence | `observations\S0-01…S0-03` with their sidecars, `UI-A.json`, `library_A.json`, `EF1_STOPPED.json` and run 1's `IDENTITIES.json`, each pinned in `ef1_continuation.template.json` |
| Run folder | a new folder, for example `E:\SFM_U0B_Scratch\f01-ef1-full-body-r2` |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_ef1_full_body\tools\ef1_tool.py <Q>\ef1.json <command>` |

**Sessions folder:**
- **At `inspect`:** it holds exactly the two copies. They are copies, so no starter session or `.bak` (EF1-D1/D2)
  can arise, and any `.bak`, autosave or other file refuses.
- **At `compare`:** the two copies must still equal their pins. An SFM autosave copy is a finding; any other file
  FAILS.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `ef1_continuation.template.json` to `<Q>\ef1.json`; fill `Q`, `REPO`, `GAME`, `SESSIONS`, `RUN1`. Change no pin. | |
| P1 | `build` | `BUILT: … line 42118 only`; `qualification_cpm_sha256` = `bb0433a9…` |
| P2 | `pre` | `MODEL PASS`, then `PRE PASS (continuation)` (run 1 verified, both sessions copied) |
| P3 | `inspect` | `INSPECTED (continuation)` |
| P4 | `install`, then `check` | `INSTALLED`; `"installation": "qualification"` |
| P5 | `seed` | `SEEDED: run 1's record ['EF1 Body--a236dddc4e22.json'] and 10 inherited Process A files` |

## Process B (Owner; destination session)

Stop at any STOP condition below: exit SFM **without saving** and report. Never save. Never open the source session.

1. Start SFM. **File > Open** `E:\SFM_U0B_Scratch\f01-ef1-full-body-r2\sessions\ef1_destination.dmx`. Switch to the **Motion Editor** with the playhead at frame **0**. Open **Scripts > SFM Character Tools > Character Preset Manager**, click **Refresh Models**, select `engineer1`, then the **Poses** tab. Expected: `EF1 Body` listed; the Engineer posed differently, placed and turned differently, smiling. Then submit the setup line:
   ```
   EF1_DIR = r"E:\SFM_U0B_Scratch\f01-ef1-full-body-r2"; EF1_REPO = r"E:\SFM-F01-Pose-Library"; EF1_ANIMSET = "engineer1"
   ```
2. Observe the baseline:
   ```
   EF1_STEP = "B1"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
   ```
   Expected: `EF1 STEP B1 (S0-04): OK`.
3. Select `EF1 Body` in the Poses list, then capture the UI:
   ```
   EF1_UI = "UI-B"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_UIState.py")
   ```
   Expected: `EF1 UI-B: 'EF1 Body' version 3 Full body (72 bones), Apply Pose enabled: OK`.
4. Arm the fault:
   ```
   import sys; sys.modules["chadchan3d_cpm_app"].PROD_POSE_QUAL_FAULT[0] = "after-writes"
   ```
   Then click **Apply Pose**. Expected: `The pose couldn't be applied. Nothing was changed.` The Engineer is unchanged. Observe:
   ```
   EF1_STEP = "B2"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
   ```
5. Click **Apply Pose**. Wait until the status leaves `Checking the applied pose...`, and note the time and whether SFM froze. Expected: `Pose applied: EF1 Body.`; Edit > Undo names `Apply Pose EF1 Body`; the saved body pose in the destination's own spot and facing, still smiling. Observe:
   ```
   EF1_STEP = "B3"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
   ```
6. Click the viewport, press **Ctrl+Z** once. Expected: the destination pose returns. Observe:
   ```
   EF1_STEP = "B4"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
   ```
7. Press **Ctrl+Y** once. Expected: the saved pose again. Observe:
   ```
   EF1_STEP = "B5"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
   ```
8. Click **Apply Pose**. Expected: `Already matches this pose.`, with no new Undo entry. Observe:
   ```
   EF1_STEP = "B6"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
   ```
9. Switch the timeline to the **Clip Editor** without moving the playhead. Observe:
   ```
   EF1_STEP = "B7"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
   ```
10. Click **Apply Pose**. Expected: `Switch to the Motion Editor to apply a pose. Nothing was changed.` Observe:
    ```
    EF1_STEP = "B8"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
    ```
11. Switch back to the **Motion Editor** (playhead unchanged). Observe:
    ```
    EF1_STEP = "B9"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
    ```
12. Press **Ctrl+Z** once. Expected: the destination pose returns. Observe:
    ```
    EF1_STEP = "B10"; execfile(EF1_REPO + r"\real_sfm_qualification\f01_ef1_full_body\observer\F01_EF1_Observe.py")
    ```
13. Exit SFM **without saving**. Report a clean close, the console lines, the B3 time, and any UI issues.

**STOP when:**
- **The B2 Apply shows any other message.** In particular, a refusal ("A bone's attachment point differs too much…"
  or "…different body proportions…") is **not** a verified Abort.
- **The B3 Apply is refused.** That includes a composed-position refusal, `proportions`.
- **A status message differs:** an observation prints `MISMATCH - STOP`, a UI capture prints `- STOP`, or any status
  differs from Expected.
- **CPM reports a recovery problem:** "Pose changes are paused…" or "CPM couldn't confirm…".
- **SFM itself misbehaves:** an autosave recovery prompt, a crash, or a hang longer than a minute.

## R: evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R0 | `library B` | `LIBRARY B: 1 files recorded`, identical to the seeded library A |
| R1 | `collect-logs` | `LOGS COLLECTED: N files` |
| R2 | `restore` | `RESTORED`; the published CPM back; the Engineer folder removed; every inventory equal to its baseline |
| R3 | `check` | `"installation": "published"` |
| R4 | `compare` | `EF1_VERDICT.md` with the provenance line; `provenance.*` and `inherited.*` pass; Process B checks pass, including `abort.reached_the_writes_and_was_verified_by_cpm` |

**Expected outcomes (offline replay of B1 with the record on the Amendment 02 engine):**
- **B3 writes 144 channels:**
  - the six drifted non-root offsets keep the destination's values;
  - the body root takes the saved translation;
  - the placement and the smile are unchanged.
- **Composed result:** within 0.00086 units of the saved pose, inside the unchanged 0.001 limit.
