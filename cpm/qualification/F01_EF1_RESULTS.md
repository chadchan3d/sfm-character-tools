# F-01 EF-1: TF2 Engineer generic version 3 Full body, native qualification results (2026-11-12)

**Verdict: PASS.** Accepted by the Owner on 2026-11-12 ("F-01 — EF-1 Closure Decisions": "ACCEPT EF-1 PASS").

**Provenance (two runs, never presented as one uninterrupted qualification):**
- **Process A** (native Save New of the Full body record, A1–A3, UI-A, library A) is **inherited from run 1**, run
  under qualification build `a378e25a…`. Run 1 is STOPPED and preserved unchanged.
- **Process B** (restart, verified Abort, Apply, Undo/Redo, no-op, Clip Editor refusal, final Undo, UI-B) is
  **native in run 2**, under qualification build `bb0433a985620d599fc75574ab749b3b8c603488f812612afdd79a7dfe17c343`
  (candidate `3da2b653…`, R3 Amendments 01 and 02; one changed line, 42118).

**Scope of the claim:** the generic version 3 `direct_fk_v1` Full body route on the TF2 Engineer
(`models/player/engineer.mdl`, `a505bba4…`, 72 bones), with the destination's six SFM-drifted offsets admitted under
the 0.001 limit. Production enablement, push, merge and release are separate decisions; `direct_fk_v1` stays
qualification-only.

## 1. Runs

| | Run 1 | Run 2 (continuation) |
|---|---|---|
| Folder | `E:\SFM_U0B_Scratch\f01-ef1-full-body` | `E:\SFM_U0B_Scratch\f01-ef1-full-body-r2` |
| Kit | `PROCEDURE.md` (`dc39f35`; `6665c2e`, `ba2c647`, `e36b304`) | `PROCEDURE_CONTINUATION.md` (`19e8f68`) |
| Build | `a378e25a…` | `bb0433a9…` |
| Outcome | STOPPED at B2/B3 (`fk-position` refusal at P1 before any write; `EF1_STOPPED.json` `78d37168…`) | PASS, 128/128 |
| Deviations | EF1-D1, EF1-D2 (accepted) | EF1-D3 (accepted, section 4) |

Run 1 is unchanged: its folder fingerprint `5796239846aaface…` was verified at `pre` and again at `compare`
(`provenance.run1_folder_untouched_since_pre`).

## 2. Run 2 execution

**Preparation (Claude, SFM closed):** `build` → `BUILT` `bb0433a9…` (line 42118 only); `pre` → `MODEL PASS`,
`PRE PASS (continuation)` (13 run-1 pins verified; both sessions copied and verified: `cc3d2745…`, `de31257b…`);
`inspect` → `INSPECTED (continuation)`; `install`/`check` → `"installation": "qualification"`, journal `complete`;
`seed` → record `EF1 Body--a236dddc4e22.json` `0e0390e0…` byte for byte, 10 inherited files.

**Process B (Owner, SFM pid 3928, 2026-11-12):** B1–B10 and UI-B, all observers `OK`. Exit without saving.

**Close-out (Claude, SFM closed):** `library B` (1 file, `0e0390e0…`, identical to library A); `collect-logs` (1 CPM
log); `restore` → `RESTORED`, published CPM `ccbed9d7…`, Engineer character folder removed, `inventory_problems: []`;
`check` → `"installation": "published"`, both registries absent; `compare` → PASS.

**Protected inventories (equal to baselines after restore):** scripts 1107 `39aa9b24…`; `usermod/cfg` 59
`f9bb1028…`; preset library 107 `a8bc5a1e…`; sessions 990 `b2089b81…`.

## 3. Native results (run 2, Process B)

| Requirement | Evidence |
|---|---|
| Verified Abort reached the writes | Log: P1 (144 inserts, noop false) → `P3-P6-failure` "qualification fault injected at after-writes", written 144 → `abort-verified` (no problems) → outcome `recovery-verified`. B2 document digest equals B1's. |
| Apply writes the body, one owned Undo entry, verified | Log: P1 144 inserts → P6 owned, Undo "Apply Pose EF1 Body", written 144 → `P7-verified` → `verified`. |
| Every bone takes the saved orientation; the body root takes the saved translation; composed result in the model frame | PASS within 0.001 units / 0.01°. |
| Non-root offsets are the destination's own (the six drifted ones kept) | PASS; non-root position keys inserted only where missing. |
| Only skeletal channels changed; placement, face and other animation unchanged | PASS; `rootTransform` identical B1–B10; `outside` hash identical at every step. |
| Neighbouring keys, layers and metadata preserved; keys at the mapped tick | PASS. |
| Undo (B4) and Redo (B5) | PASS: B4 document equals B1, B5 equals B3. |
| Repeat Apply is a true no-op (B6) | PASS: P1 noop, 144 unchanged, no Undo entry. |
| Clip Editor refusal writes nothing (B8) | PASS: `editor-mode` refusal before any write. |
| Final Undo returns to the baseline (B10) | PASS: document digest `b4cdb23a…` equals B1; see EF1-D3. |
| Restart between Save and Apply; record unchanged by Apply | PASS (run-1 Process A pid vs run-2 pid 3928; library B equals library A). |
| UI-B | `'EF1 Body' version 3 Full body (72 bones), Apply Pose enabled: OK`. |
| Performance | responsive: B3 whole 915 ms (preflight 327, transaction 381, deferred verify 207). |

## 4. Deviation EF1-D3 (accepted; harmless SFM-specific variation)

- **Instruction as run:** `PROCEDURE_CONTINUATION.md` step 12, "Press Ctrl+Z once."
- **Actual operator sequence:** Ctrl+Z (SFM "Change Recording State"), Ctrl+Z (SFM "Change Recording State"), Ctrl+Z
  ("Apply Pose EF1 Body"), then observe B10.
- **Cause:** normal SFM behaviour (confirmed by the Owner). The editor switches at B7 and B9 each pushed a "Change
  Recording State" entry above the Apply. Not a CPM defect.
- **Evidence:**
  - The Apply is one Undo operation: at B4 one Ctrl+Z restored the baseline digest `b4cdb23a…` with Redo naming the
    Apply.
  - The recording-state entries changed no data: document digest `9e4ed379…` constant from B5 to B9; at B6→B7 the top
    Undo changed from the Apply to "Change Recording State".
  - Three presses mean exactly two such entries: after B10, Redo names "Redo Apply Pose EF1 Body" and Undo names the
    session's baseline "Change Recording State".
  - B10 equals B1 exactly (187 channels, all 72 bones' world and local transforms, placement, face, outside animation).
- **Disposition:** not a product failure, not a reason to repeat; the PASS verdict is unchanged. The comparator's
  verdict files are not rewritten; the variation is recorded in run 2's `evidence\EF1_CLOSURE.json` (`c783c2cf…`) and
  here.
- **Correction:** future instructions undo through recording-state entries to and including the named Apply, and
  stop there (`PROCEDURE.md` B10, `PROCEDURE_CONTINUATION.md` step 12).

## 5. Separate usability/design issue: F01-DI-01 (unresolved)

Applying `EF1 Body` moved the visible Engineer 78.60 units (world z −45.56), largely out of frame, although
`rootTransform` was unchanged. R3 was followed exactly: Full body writes the anatomical root's saved model-relative
translation (72.418, 0, 51.434), which came from run 1's 73.1-unit Process A pelvis offset, into a destination
placement that is rotated and tilted relative to the source's. This is **not** part of the EF-1 verdict. Recorded with
the design question for Astra in `F01_DESIGN_ISSUE_DI01_APPLY_IN_PLACE.md`. The procedures' B3 expectation text now
says this movement is expected under R3 and is not by itself a STOP.

## 6. Evidence (run 2 folder; not committed)

| File | SHA-256 |
|---|---|
| `evidence\EF1_VERDICT.md` | `aecaa5ec2b8c5f1ff8dc35c96d0e15b965553653b35923d997b3655b86692a76` |
| `evidence\EF1_VERDICT.json` | `3b9b2ad9d7f0f82758860461ca30ca79d1522f3565975879b70ddae86851cdfc` |
| `evidence\EF1_CLOSURE.json` | `c783c2cf1ceac56c006acc644b7c08b7b08b0a084b666db9035a8de75934e2b6` |
| `evidence\restore.json` | `05b5d48f…` |
| `evidence\library_B.json` | `4847bbc4…` |
| CPM log `CPM - 2026-11-12_12-07-51Z - pid3928 - 84bdc8 - 001.log` | `3a141de9…` |
| `pre_run\pre.json` | `a0e17043…` |
| `ef1.json` | `a99c315a…` |
| Observations B1–B10 (`S0-04` … `S0-13`) | `d22439a8…`, `5858dd8c…`, `8ef36b7d…`, `0cc73e02…`, `6dcf86ba…`, `ba1e7a0a…`, `60b967ad…`, `e0e05e49…`, `7a5232cd…`, `44036713…` |
| `observations\UI-B.json` | `1223c41a…` |

Identities in the verdict: comparator `f362bab1…`, observer wrapper `e8c122f1…`, S0 observer `4a358cc0…`, UI capture
`8ba4aefa…`, expected header `5faabf6b…`.
