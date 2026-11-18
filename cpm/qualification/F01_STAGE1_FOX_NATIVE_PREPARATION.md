# F-01 Stage 1: native Fox qualification, prepared (2026-11-18)

**Authority:** "F-01 Stage 1 — Offline Acceptance and Native Qualification Preparation" (Designer: ACCEPT offline
implementation for native qualification, commit `fc534c3`).

**Status: prepared, not run.**
- Kit `real_sfm_qualification/f01_stage1_fox/`, staged by `build` in `E:\SFM_U0B_Scratch\f01-stage1-fox-r1`.
- Nothing installed (`check`: published `ccbed9d7…`, registries absent). `pre`, `install` and the native run need
  the Owner's authorization.
- No engine change: the candidate is the accepted Stage 1 CPM `35c400c1…`.

## 1. Identities

| Item | Value |
|---|---|
| Candidate | `35c400c139901796f1588884171b0667f580755daa37ec961719ed141dc382fc` (`fc534c3`) |
| Qualification build | `5ac0e9d621cb15838b520f0c527a3f9b12d70cac9f60d872fd92d4a30ce71ac8`: the registry-mode line only (42597), derived and verified by the reused K2 `build` |
| Registries | `f445d5ef…` and `a2254930…` (unchanged) |
| Kit files | `PROCEDURE.md` `59fdafd9…`, capture `F01_S1F_Capture.py` `aec8b344…`, analyzer `s1f_analyze.py` `82aad2d8…` (all pinned in `s1f.template.json` and checked by `build`), tool `s1f_tool.py` `85fb6014…` |
| Inputs (pins verified, read only) | R2 fixture `259ea8a6…`, S3 destination `61df8bcd…` (the never-opened spare), legacy pose `4916a724…` |

## 2. What is reused and what is new

**Reused unchanged.** The H1 kit's tool chain, with this kit's identity substituted. Through UA-1, K2 and S3, that
covers:
- SFM-closed refusals;
- backups of the published CPM, `.pyc` and housekeeping files;
- four protected inventories and the installation journal;
- the one-line qualification build;
- the whole-library backup and exact files-and-folders cleanup;
- log collection;
- restoration.

CPM's own read functions do the observation, and the established `PROD_POSE_QUAL_FAULT[0] = "after-writes"` line
(EF-1, S3) arms the Abort.

**New, and kept small:**
- a read-only capture, based on H1's;
- the analyzer;
- the procedure;
- the kit test.

## 3. The designer's corrections

- **Fox B survives the restart.** The session is the disposable copy `S1_SESSION.dmx`.
  - In Process A, the Owner creates Fox B (a new `foxmccouldwm` set), applies SFM's stock `rig_biped_simple`, and
    poses and places Fox B visibly differently with rig handles only. The Owner then saves Fox A's pose and saves
    that copy once (File > Save, never Save As).
  - Process B reopens the saved copy in a new SFM process.
  - Nothing relies on an unsaved model surviving a restart.
- **The preparation is recorded.**
  - The PREP capture records all three sets before the Save.
  - The analyzer's PREP gate requires the same model, a structural admission of both Foxes with an identical
    drafted description under different rig names, and Fox B visibly differently posed (above 10°) and placed.
  - It also requires the reopened session to hold every channel of the three sets exactly as prepared, compared by
    a handle-free content digest across the processes.
  - The saved copy's hash is reported in the verdict.
- **The original session is preserved.** The R2 fixture is only read, the spare copy must stay byte-identical, and
  the Owner's sessions folder stays under the protected inventory.

## 4. Required observations → gates

| Designer requirement | Gate (analyzer) |
|---|---|
| Fox Full body Save through structural discovery | SAVE: one version 2 record with adapter `structural_rig_v1`, its written set equal to the drafted one, `BODY-RIG-available` logged, Save read-only |
| Saved pose reopened after a restart | SAVE: selected in Pose Info at SAVED, and selected again at BASE in the new process |
| Body posture and secondary articulation on a differently posed and placed compatible Fox | APPLY: only the drafted written channels change, both rig handle and direct bone channels, other keys untouched, P7 verified, one owned entry. POSTURE: every bone of Fox B, relative to its own `rig_root`, against Fox A's saved posture, from SFM's evaluated transforms (not the planner): 0.05 units and 0.5°, maxima reported per class (rig-driven and direct) |
| Placement and proportions | POSTURE: Fox B's `rig_root` and model transform unchanged, and its direct bones' local offsets unchanged (0.001 / 0.01°); IK lengths and other preserved channels are covered by APPLY |
| Source Fox unchanged; peer isolation | PEER: Fox A and Tails, every capture of both processes |
| Navigation, Undo, Redo, final Undo, repeat no-op | HISTORY: one frame away and back (same playhead, same pose); UNDO = BASE; REDO = APPLY; no-op with no entry (and the CPM log's `noop`); UNDO2 = BASE; Edit menu entries |
| Mixed rig/FK partial-write Abort | ABORT: the injected failure after as many writes as the committed Apply made (rig and FK channels, shown at APPLY); `BODY-abort-verified`; Fox B and the Undo history exactly as at UNDO2; the fault slot consumed |
| Tails, expected safe refusal | TAILS: refused by the structural discovery (control-less bones) and no saved pose |

**Verdict.**
- **AUTOMATED PASS** means every gate passed. Stage 1 native acceptance also needs the Owner's visual acceptance.
- **REFUSED** means Fox's Save was refused: safe, but not qualified.
- **FAIL** means a functional gate failed.
- **INCOMPLETE** means evidence, preparation or restoration failed.

The Abort point is the one the CPM provides: after all planned writes and before commit. The mid-plan failure is
covered offline (Stage 1 suite, `T.partial_write_failure_*`).

## 5. Offline checks

- **Kit test `tests/test_s1f.py`: 31/31 PASS** on Python 2.7.5 (SFM's interpreter, which also runs the capture) and
  3.10.6.
  - The capture runs against the real Stage 1 CPM on the fake Fox scene. It records the structural admission (22
    handles, 34 constraints, 214 written, 22 rig-driven and 90 direct bones), a description digest that ignores the
    rig name, a Tails-like refusal with its code, and handle-free content digests. It is read-only, refuses bad
    names, and writes exactly one file.
  - A complete simulated two-process run, using CPM's real Save, Apply, P7, Undo, Redo, no-op and injected-fault
    Abort, gives **AUTOMATED PASS**. Its independently measured posture covers 112 bones, below 0.01°.
  - Each break gives the expected verdict:
    - **FAIL:** posture off by a few degrees, a moved placement, a preserved channel written, a neighbouring key
      changed, Fox A changed, an incomplete Undo, an Abort leaving a change, an Abort without the injected
      failure, a record without the adapter, or Tails admitted;
    - **INCOMPLETE:** an unverified P7 in the log, a playhead not returned, no restart, the session not reopened
      as prepared, Fox B not visibly different, the session not saved, a restore failure, or another build;
    - **REFUSED:** a refused Save.
- **`build`** ran in the run folder: BUILT, one line, and the pins verified. **`check`:** published.
- **Stage 1 offline results** are as accepted (147/147; the regression is identical to RC2). Krystal needs offline
  regression only (body suite 261/261 unchanged).

## 6. Shortest run (Owner)

The full steps are in `PROCEDURE.md`.
1. **Preparation (Claude, SFM closed):** `pre`, `install`, `check`.
2. **Process A:** open `S1_SESSION.dmx`; create, rig, pose and place Fox B; capture PREP; Save New Full body
   `S1 Fox`; Pose Info; capture SAVED; Tails Save New (note the refusal, Cancel); File > Save; exit.
3. **Process B:** reopen; select Fox B and `S1 Fox`; capture BASE; Apply, capture APPLY; visual inspection; one frame
   left and right, capture NAV; Undo, Redo, repeat Apply and final Undo, each with its capture; arm the fault, Apply,
   capture ABORT; exit without saving.
4. **After the run (Claude):** `library Q`, `collect-logs`, `restore`, `check`, `analyze`.

There are 10 captures and two SFM sessions.

**Stopped before installation and native execution for the Owner's authorization.** No promotion, push, merge,
signing or publication.
