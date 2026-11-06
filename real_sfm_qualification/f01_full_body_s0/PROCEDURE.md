# F-01 full-body S0: read-only native survey of the Krystal rig (operator procedure)

**Status:** prepared, **not run**. Running it needs the Owner's authorization. One SFM process, six observations,
about 15 minutes. **Nothing is installed:** the published CPM `ccbed9d7…` stays in place and the CPM is not opened.
The observer only reads the scene; the session copy is never saved.

Purpose and questions: `cpm/qualification/F01_FULL_BODY_CONSOLIDATED_DESIGN.md`, section 9 (S0-Q1 … S0-Q13).
Evidence format: `EVIDENCE_SCHEMA.md`.

| Item | Value |
|---|---|
| Run folder | `E:\SFM_U0B_Scratch\f01-full-body-s0-r2` (holds `s0.json`, this machine's paths) |
| Session | `E:\SFM_U0B_Scratch\f01-full-body-s0-r2\sessions\S0_SURVEY.dmx`, a verified copy of the R2 fixture `259ea8a6…` |
| Observer | `E:\SFM-F01-Pose-Library\real_sfm_qualification\f01_full_body_s0\observer\F01_S0_Survey.py`, SHA-256 `4a358cc05449592c7ea3cd6828cb40ca2faed08fc602156c2f15a9398e67c0c4` |
| Tool | `python -I E:\SFM-F01-Pose-Library\real_sfm_qualification\f01_full_body_s0\tools\s0_tool.py E:\SFM_U0B_Scratch\f01-full-body-s0-r2\s0.json <command>` |

**Run history:** the first run, `E:\SFM_U0B_Scratch\f01-full-body-s0`, is **invalid** (operator sequence: the
timeline was switched to the Motion Editor before S0-01). It is preserved unchanged with
`INTERRUPTED_RUN_README.txt` and is never reused or analyzed as a survey. Every later run uses a new folder.

Fixture shots (from NQ-1): shot15 0.1667–0.2917 s, shot13 0.3334–0.3751 s, shot10 0.3751–0.5001 s; each holds one
separate `Krystal` (`krystal2020.mdl`) with a different arm pose.

**Stop rule:** stop issuing SFM commands, exit SFM **without saving**, run step 3.1 and report if:
- the observer prints an error, a `problems` count above 0, or `readonly=False`;
- a `SUMMARY` line's `mode`, `shot` or `head` differs from the step's expected line;
- any step was done out of order (an editor switched early, the playhead moved to the wrong time).

A run with a wrong step is reset in a new run folder; labels are never repeated or suffixed to repair a sequence.
Never edit, key, move or select controls in the viewport, or save, during the survey.

## 1. Preparation (SFM closed)

`… s0_tool.py … pre` → `PRE PASS`. It checks that SFM is closed, the published CPM is installed with no pose registry
beside it, the fixture and the observer match their pins; records the four protected inventories; backs up SFM's
housekeeping and `.pyc` files; creates the session copy. It takes a few minutes (the inventories); wait for
`PRE PASS`. On any refusal it changes nothing: stop and report.

`pre` runs **once per run folder** and never again. Before starting SFM, and whenever unsure whether `pre` already
completed, run `… s0_tool.py … status` (read-only): `STATUS FRESH` means the completed `pre` is still a valid
baseline (SFM closed, published CPM, no registry, unsaved session copy, empty `observations` and `evidence`, no
housekeeping, `.pyc` or inventory change). Anything else is `STATUS NOT FRESH`: do not start the survey; report.

## 2. Survey (one SFM process)

**SFM starts in the Clip Editor. Do not change timeline editors before S0-01.** The first editor change of the run
is in step 2.3.

| # | Action | Editor at observation | Playhead | Shot | Observe |
|---|---|---|---|---|---|
| 2.1 | Start SFM. File > Open `E:\SFM_U0B_Scratch\f01-full-body-s0-r2\sessions\S0_SURVEY.dmx`. Check that the timeline shows the **Clip Editor**; do not click any editor button. Open the Script Editor and run `S0_DIR = r"E:\SFM_U0B_Scratch\f01-full-body-s0-r2"` once. | — | — | — | — |
| 2.2 | Still in the **Clip Editor**, set the playhead to **0.2083 s**. Do not select anything. | **Clip Editor** | **0.2083 s** | shot15 | `S0-01` |
| 2.3 | Switch the timeline to the **Motion Editor**. Do not move the playhead. | **Motion Editor** | **0.2083 s** | shot15 | `S0-02` |
| 2.4 | Stay in the **Motion Editor**. Set the playhead to **0.2500 s**. | **Motion Editor** | **0.2500 s** | shot15 | `S0-03` |
| 2.5 | Stay in the **Motion Editor**. In the Animation Set Editor, click the **Krystal** animation set name once, so its controls are selected; do not touch the viewport or any slider. Then set the playhead back to **0.2083 s**. | **Motion Editor** | **0.2083 s** | shot15 | `S0-04` |
| 2.6 | Stay in the **Motion Editor**. Set the playhead to **0.4167 s**. | **Motion Editor** | **0.4167 s** | shot10 | `S0-05` |
| 2.7 | Stay in the **Motion Editor**. Set the playhead to **0.3750 s**. | **Motion Editor** | **0.3750 s** | shot13 | `S0-06` |
| 2.8 | Exit SFM. When asked to save, choose **No**. Confirm with `tasklist /FI "IMAGENAME eq sfm.exe"` that no `sfm.exe` remains. | — | — | — | — |

To observe, run in the Script Editor (changing only the label):

```
S0_LABEL = "S0-01"; execfile(r"E:\SFM-F01-Pose-Library\real_sfm_qualification\f01_full_body_s0\observer\F01_S0_Survey.py")
```

Before each observation, look at the timeline and the playhead and confirm they match the row. After it, compare the
`SUMMARY` line with the expected line before going on:

`head` is printed as SFM's raw float (for 0.2083 s it prints `0.20829999446868896`); it must round to the value
shown.

| Label | `mode=` | `shot=` | `head=` rounds to |
|---|---|---|---|
| `S0-01` | **Clip Editor** | shot15 | 0.2083 |
| `S0-02` | Motion Editor | shot15 | 0.2083 |
| `S0-03` | Motion Editor | shot15 | 0.2500 |
| `S0-04` | Motion Editor | shot15 | 0.2083 |
| `S0-05` | Motion Editor | shot10 | 0.4167 |
| `S0-06` | Motion Editor | shot13 | 0.3750 |

Every line must also show `bones=156 … readonly=True problems=0`. A label can be used once; the observer refuses to
replace a file. Any mismatch is a stop (see the stop rule).

## 3. Verification and analysis (SFM closed)

| # | Command | Expected |
|---|---|---|
| 3.1 | `… s0_tool.py … post` | `POST PASS`: any housekeeping or `.pyc` file SFM rewrote is put back; the session copy is byte-identical to the fixture (not saved); the published CPM is still installed with no registry; the observer is unchanged; all four inventories equal their baselines. |
| 3.2 | `… s0_tool.py … analyze` | `E:\SFM_U0B_Scratch\f01-full-body-s0-r2\evidence\S0_REPORT.json` and `S0_REPORT.md`; `"valid": true` and `every_observation_unchanged: true`. |

Return the run folder's `observations\`, `evidence\` and the SFM console text. The report is evidence for the S1
coverage contract; it does not authorize implementation.

## What S0 does not cover

- Behaviour that needs a scene change (moving a foot helper or a knee control, solving IK with other inputs): S0
  records the structure that decides it; a behavioural probe would need separate authorization.
- The session file name of a never-saved session or after Save As (decision D5 remains open).
- Any character other than Krystal.
