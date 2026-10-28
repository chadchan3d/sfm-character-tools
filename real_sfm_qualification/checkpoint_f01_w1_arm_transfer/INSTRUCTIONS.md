<!-- Derived from the accepted package's RUNBOOK.md (SHA-256 1f43b902aa55a2526e449ca1037e61dcb1ba89897eadfb8550a1f5c57e3bef24) by replacing private absolute paths and the
     original session's file name only: <SESSIONS_DIR> is the folder holding the original session;
     <SOURCE_SESSION> is the original session's file name without extension (identified by SHA-256 in
     W1_NATIVE_QUALIFICATION_EVIDENCE.md); <RUN_DIR> is the run directory that tools/prepare_run.py creates
     (the accepted run used a private local folder named F01_W1_ArmTransfer_Run). Every other word is
     unchanged. The accepted RUNBOOK.md itself is not committed because it contains private paths. -->

# F-01 W1 Operator Runbook

**Do not run this until the harness has passed Astra's independent safety review and the Owner has explicitly authorized native execution.**

This is a write-capable experiment on a disposable copy of the validated R2 fixture. It authors six existing key values in three shot10 channels, then undoes and redoes that change under native Undo.

## Absolute rules

- Never open the original session (`<SESSIONS_DIR>\<SOURCE_SESSION>.dmx`) or the R2 fixture in SFM.
- **Never save.** When closing, always choose not to save.
- Submit `NEXT_STEP.txt` exactly once per step, and only after doing what the previous step printed.
- While a step prints `running`, do not touch SFM until it prints its result. That is normally a few seconds; a capture can take longer.
- Do not use CPM, the Normalizer, sliders, the graph editor, Undo or Redo yourself, playback, or any other scene interaction during the experiment.
- Never delete, edit or rename anything in the run's `reports\` folder. Never reuse a run directory.
- If a step reports `STOP`, `FAIL` or `INCONCLUSIVE`, the experiment is over. Do not improvise recovery: close without saving and finalize (step 6).

## 0. Verify the package (SFM closed)

From the package root, verify every entry of `SHA256SUMS.txt`, for example:

```
python -I -c "import hashlib,sys;[print(('OK  ' if hashlib.sha256(open(p,'rb').read()).hexdigest()==h else 'BAD ')+p) for h,p in (l.split('  ',1) for l in open('SHA256SUMS.txt').read().splitlines())]"
```

Every line must read `OK`.

## 1. Prepare a fresh run (SFM closed)

```
python -I tools\prepare_run.py <package root>
```

This verifies the reviewed harness files and the original and R2 hashes. It then creates `<RUN_DIR>\`, containing:
- a fresh, hash-verified disposable session copy;
- `harness\`;
- an empty `reports\`.

It refuses if that directory already exists.

## 2. Open the disposable session

1. Start SFM.
2. Open `<RUN_DIR>\F01_W1_DISPOSABLE_<SOURCE_SESSION>.dmx`.
3. Leave playback stopped.

## 3. First step: source baseline

1. At 24 fps, set the playhead to **movie frame 5** (0.2083 s, inside shot15) and let it settle.
2. Open **Windows > Script Editor**.
3. Paste the single line from `<RUN_DIR>\harness\NEXT_STEP.txt`, without Markdown fences, and submit it once.

## 4. Every following step

Each step prints its result and a `NEXT:` instruction. Do exactly that instruction, then submit the same `NEXT_STEP.txt` line once.

The playhead positions used are:

| Instruction | Playhead |
|---|---|
| shot15 steps | movie frame **5** |
| shot10 steps | movie frame **10** |
| `RETIME` (only if instructed) | frame **11**, let it settle, then back to frame **10**, let it settle |

With idle propagation, the expected order is:

| # | Step | Where | What the harness does |
|---|---|---|---|
| 1 | `SOURCE_BASELINE` | frame 5 | Read-only capture of shot15 |
| 2 | `TRANSFER` | frame 10 | Preflight; then, after the line returns: the abort check, an evaluated check, the six-value commit and one idle observation |
| 3 | `SOURCE_RETURN` (committed) | frame 5 | Source preserved; destination authored state still committed |
| 4 | `DESTINATION_RETURN` (committed) | frame 10 | Transferred arm reproduced |
| 5 | `UNDO` | stay at 10 | Owned Undo, then one idle observation |
| 6–7 | `SOURCE_RETURN` / `DESTINATION_RETURN` (undone) | 5, then 10 | |
| 8 | `REDO` | stay at 10 | Owned Redo, then one idle observation |
| 9–10 | `SOURCE_RETURN` / `DESTINATION_RETURN` (redone) | 5, then 10 | |
| 11 | `FINAL_UNDO` | stay at 10 | Owned Undo, then one idle observation |
| 12–13 | `SOURCE_RETURN` / `DESTINATION_RETURN` (final) | 5, then 10 | Ends with `COMPLETE_PENDING_CLOSE` |

If an idle observation does not show the expected state, the harness asks for one `RETIME` before continuing. That is expected behaviour, not a fault.

Submitting the line while a step is still running, or after the experiment has ended, does nothing and says so.

## 5. Close without saving

When a step prints `COMPLETE_PENDING_CLOSE`, `STOP`, `FAIL` or `INCONCLUSIVE`:
1. Close the session.
2. When SFM asks whether to save, choose **not to save**.
3. Quit SFM.

If SFM hangs or crashes, do not save; quit or end SFM.

## 6. Finalize (SFM closed)

```
python -I tools\finalize_f01w1.py <RUN_DIR>\harness\config.json
```

This checks the original, the R2 fixture and the disposable copy (which must be unchanged, because nothing was saved), the ledger hash chain and the harness identity. It writes `reports\F01W1-FINAL.json` with `PASS`, `FAIL`, `STOP` or `INCONCLUSIVE`. `PASS` requires an independent audit of every report (complete evidence, ownership, writes, rig inputs, preservation); a terminal status alone never yields `PASS`. Unreadable evidence never yields `PASS`: it ends the run as `INCONCLUSIVE`, or as `STOP` during a restoration check.

Return the whole `reports\` folder for review. It contains private local paths, so share it privately.
