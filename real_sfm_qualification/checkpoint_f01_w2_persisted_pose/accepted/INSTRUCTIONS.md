# F-01 W2 operator runbook (proposed)

**Do not run this until Astra has adjudicated native readiness AND the Owner has separately authorized
native execution.**

This is a write-capable experiment on two disposable copies of the validated R2 fixture:
- **Process A** captures a pose, read-only.
- **Process B**, a new SFM process, applies that pose to six existing key values, then undoes and redoes the
  change under native Undo.

## Absolute rules

- **Never open** the original session (`<SESSIONS_DIR>\<SOURCE_SESSION>.dmx`) or the R2 fixture in SFM.
- **Process A** opens only the CAPTURE copy; **process B** opens only the APPLICATION copy.
- **Never save.** When closing, always choose not to save.
- **One submission per step.** Submit the launcher line exactly once per step, and only after doing what the
  previous step printed.
- **Don't touch SFM while a step is running.** If a step prints `running`, wait until it prints its result.
- **No other interaction during the run:** no CPM, Normalizer, sliders, graph editor, manual Undo or Redo,
  playback or other scene interaction.
- **Never alter evidence.** Never delete, edit or rename anything in `reports\` or `poses\`. Never reuse a run
  directory.
- **Any `STOP`, `FAIL` or `INCONCLUSIVE` ends the experiment.** Do not improvise recovery: close without
  saving and finalize (step 7). In particular, never use Undo or Redo to "fix" a stopped run. After a `STOP`
  the harness refuses every further submission, and it makes no compensating Undo, Redo or write itself.
- **M-06 must not be installed.** Make sure no temporary M-06 installation is present: the installed CPM must
  be the published build.

## 0. Configure and verify (SFM closed)

1. Copy this folder to a package root.
2. Fill `harness\config.json` from `config.template.json`, replacing every `<...>` placeholder.
3. Run `python -I tools\prepare_run.py manifest <package root>`. This writes `CAPTURE_STEP.txt`,
   `APPLY_STEP.txt` and `HARNESS_SHA256.json`.
4. Have the resulting hashes reviewed before continuing.

## 1. Prepare a fresh run (SFM closed)

```
python -I tools\prepare_run.py prepare <package root>
```

This step:
- verifies the reviewed harness files and the original and R2 hashes;
- creates `<RUN_DIR>\` containing the two hash-verified disposable copies, `harness\`, and empty `reports\`
  and `poses\` folders.

It refuses if the run directory already exists.

## 2. Process A: capture

1. Start SFM and open `<RUN_DIR>\F01_W2_CAPTURE_DISPOSABLE.dmx`. Leave playback stopped.
2. At 24 fps, set the playhead to **movie frame 5** (0.2083 s, shot15) and let it settle.
3. Open **Windows > Script Editor** and paste the single line from `<RUN_DIR>\harness\CAPTURE_STEP.txt`.
   Submit it once.
4. Expected result: `CAPTURE_COMPLETE_PENDING_CLOSE`.

## 3. Close process A

Close the session **without saving** and quit SFM. Make sure `sfm.exe` is no longer running.

## 4. Process gate (SFM closed)

```
python -I tools\prepare_run.py gate <RUN_DIR>\harness\config.json
```

The gate refuses unless all of the following hold:
- process A (pid and creation time) is positively shown to be gone. Windows must report one of: no process
  with that id, that process exited, or the id now belonging to a different process (a different creation
  time). If process A cannot be queried (for example, access denied), the gate refuses: that is not proof that
  it exited. Run the gate from the same Windows account that ran SFM;
- no `sfm.exe` is running;
- both disposable copies are unchanged;
- the pose still has its recorded hash.

It records the gate time and process A's state.

## 5. Process B: application

1. Start SFM again. This must be a new process.
2. Open `<RUN_DIR>\F01_W2_APPLY_DISPOSABLE.dmx` and set the playhead to **movie frame 10** (0.4167 s,
   shot10). Let it settle.
3. Open the Script Editor and submit the line from `<RUN_DIR>\harness\APPLY_STEP.txt` once.

The steps then run in this order:

| # | Step | Playhead | What the harness does |
|---|---|---|---|
| 1 | `APPLY` | frame 10 | Process-separation check; one read of the pose file; fresh compatibility preflight; two independent plan calculations. Then, after the line returns: the abort check, an evaluated check, the six-value commit and one idle observation. |
| 2 | `UNDO` | stay at 10 | Owned Undo, then one idle observation |
| 3 | `REDO` | stay at 10 | Owned Redo, then one idle observation |
| 4 | `FINAL_UNDO` | stay at 10 | Owned Undo, then one idle observation; ends with `COMPLETE_PENDING_CLOSE` |

After each step, do what its `NEXT:` line says, then submit the same `APPLY_STEP.txt` line once.

If an idle observation is not yet the expected state, the harness asks for one `RETIME`:
1. Move to frame **11** and let it settle.
2. Move back to frame **10** and let it settle.
3. Submit once.

That is expected behaviour, not a fault. The harness never offers a retime when the idle observation already
shows an unrelated change: that is a `FAIL`. It also never offers one when an operator or constraint
attribute changed: that is a `STOP`.

Before every native history operation (the abort check, the commit, Undo, Redo and the final Undo), the
harness rechecks that no unrelated operator, constraint or skeletal state has changed. This includes any time
the scene sat idle between your submissions. Any change, or any of that evidence becoming unreadable, ends the
run with `STOP` before that operation.

## 6. Close process B

Close **without saving** and quit SFM.

## 7. Finalize (SFM closed)

```
python -I tools\finalize_f01w2.py <RUN_DIR>\harness\config.json
```

The finalizer writes `reports\F01W2-FINAL.json` with a verdict of `PASS`, `FAIL`, `STOP` or `INCONCLUSIVE`.
A `PASS` requires all of the following, audited independently:
- the complete hash-chained ledger;
- the exact pose bytes;
- process separation with native kernel32 evidence;
- one aborted test write and six committed writes;
- owned history operations and accepted observations;
- unchanged protected files.

Return the whole `reports\` folder and the pose file for review. They contain private local paths, so share
them privately.
