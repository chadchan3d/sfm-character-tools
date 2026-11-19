# F-01 Stage 1: targeted native Abort recovery check, results

**Authority:** the Owner's "F-01 Stage 1 — Native Recovery Check GO" (checkpoint `fd2f460`). Procedure and kit:
`real_sfm_qualification/f01_stage1_recovery/` (record `F01_STAGE1_ABORT_HISTORY.md` section 7).

**Builds:**
- candidate CPM `7259e80a5d462eba1aeaa25cf89e9f57cf1081caaeac3002de8db6fbe488ab55`;
- qualification build `39f2e35542180952d37f0d75b20d4c5cc89f24db16031b905655dc2310462421`, installed temporarily;
- published CPM `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df`, restored.

Run folder: `<Q>` = the scratch folder `f01-stage1-recovery` (outside the repository).

## 1. Results

| | Result |
|---|---|
| **Formal automated verdict** (`S1R_VERDICT`, analyzer `8128e162…` unchanged) | **INCOMPLETE**: 59 of 60 checks pass. The single failure is the SETUP check `setup.seeded_record_selected`. Every functional gate (APPLY, REDO_ABORT, EXACT_ABORT, OPERATIONAL, PEER) and EVIDENCE pass. |
| **Owner acceptance** (reported separately) | **PASS**. All six captures reported `errors none`, `Undo enabled True` and `sidecar written`. Both controlled Abort cases behaved as expected, normal Apply worked afterwards, and there was no recovery lockout. |
| **Restoration** | **RESTORED**: the published CPM is installed, both registries are removed, the preset library equals its pre-run inventory in files and folders, and the inventory problems are none. |
| **Run 3** | Unchanged and only read. Its verdict stays **INCOMPLETE** (`561f1b09…`). |

The automated verdict is not reinterpreted as a PASS. The analyzer was not changed and was not re-run with different
inputs.

## 2. The failed check

`setup.seeded_record_selected` requires that, at BASE, the CPM window's selected pose is the seeded `S1 Fox`
record (name, `preset_id`, adapter `structural_rig_v1`). At BASE the capture recorded `selected_pose: null`. The
capture returns `null` when the window reports no selected pose record; an exception would have been recorded as a
capture error, and BASE recorded none.

**What the evidence shows:**
- **Times:**
  - Select Model (`foxmccouldwm3`) completed at 19:23:22.5Z.
  - BASE was written at 19:23:44.5Z.
  - The first Apply Pose began at 19:23:51.9Z.
- Selecting a row in the pose list is not a logged operation.
- **From APPLY onward:** every capture records the selected pose as `S1 Fox` with `preset_id`
  `dfdf47f5cf4d62ce527eebb31fa1d3c3`, adapter `structural_rig_v1` revision 1, model
  `models/fursonas/foxmccouldwm.mdl` and the full-body region. This is the seeded record (`292bc334…`).
- **Every Apply was of that record:** the log labels each one `Apply Pose S1 Fox`, and each wrote 212 channels.

**Most likely explanation:** the pose was selected in the 7 s between BASE and the first Apply, which reverses
procedure step 2's order (select `S1 Fox`, then capture BASE). The evidence can't distinguish this from a selection
that was cleared and made again. Either way, the BASE capture does not establish the selection, so the gate is
INCOMPLETE as designed. This is a setup-evidence gap, not a CPM defect.

## 3. Functional evidence (all PASS)

**Undo state.** Read directly by the sidecar. One SFM process (pid 24884) throughout.

| Step | enabled | can_undo | can_redo | undo_desc | redo_desc |
|---|---|---|---|---|---|
| BASE | True | True | False | Change Recording State | "" |
| APPLY | True | True | False | Apply Pose S1 Fox | "" |
| UNDO | True | True | **True** | Change Recording State | **Redo Apply Pose S1 Fox** |
| ABORT1 | True | True | **False** | Change Recording State | **""** |
| ABORT2 | True | True | False | Change Recording State | "" |
| APPLY2 | True | True | False | Apply Pose S1 Fox | "" |

**Abort and Apply results:**
- **ABORT1** (Redo pending):
  - The fault was injected after 212 writes, as many as the committed Apply made.
  - The log shows `PROD_POSE_BODY-abort-verified {"problems": [], "redo_cleared": true}` and the outcome
    `recovery-verified` (`not-applied`).
  - All three sets are exactly as at UNDO, and only the pending Redo was cleared.
  - The operation stayed open for 13 s, until the Owner dismissed the "Pose not applied" dialog.
- **ABORT2** (no Redo):
  - The log shows `{"problems": [], "redo_cleared": false}` and `recovery-verified`.
  - The sets and the complete Undo state are exactly as at ABORT1.
  - The operation returned at once (no dialog).
- **Both Aborts:** the fault slot was consumed both times.
- **APPLY2:** verified, equal to APPLY on Fox D, with one owned entry.
- **OPERATIONAL:**
  - The log has no lockout, unverified, failed-Abort or uncertain result.
  - Events in order: P7-verified, failure, verified Abort, failure, verified Abort, P7-verified.
  - There are exactly two `recovery-verified` outcomes.
- **PEER:** Fox S (`foxmccouldwm2`) and the original Fox (`foxmccouldwm1`) are unchanged at every capture.

**What this establishes natively,** subject to the INCOMPLETE verdict:
- The corrected CPM reports verified restoration when SFM clears a pending Redo entry on Abort.
- It still reports an exact Abort when there was no Redo.
- It does not pause the pose tools after either.

## 4. Evidence identities

| File (under `<Q>`) | SHA-256 |
|---|---|
| `evidence/S1R_VERDICT.json` | `f402da86d32a8e7e4a0f90821ae980711461087fbf2e0fdfab47bde451a8b907` |
| `evidence/S1R_VERDICT.md` | `80a260f12404ed38010ca550914a97160f360d3a4eb60d4b2be193e657d8f069` |
| `sessions/S1R_SESSION.dmx` (never saved; run 3's saved session) | `fcf2441c2c971e857f8f4953435d54a89b31b89d06ed7fe081692cc2401c26bf` |
| `sessions/S1R_SPARE.dmx` (never opened) | `61df8bcd5397c78b064e102047e51b5d9e4e3c43df40394522c57944ba67e992` |
| Run 3 `evidence/S1F_VERDICT.json` (read only) | `561f1b091ca1d6404efe61371509ed6012626bf362ed551523e742d0ffcb9de0` |

Also under `<Q>`:
- `observations/`: twelve files, a capture and an Undo sidecar for each of the six steps;
- `evidence/logs/`: one CPM log, pid 24884;
- `evidence/library_Q.json`: exactly the two seeded files;
- `evidence/restore.json`, `seed.json` and `library_cleanup.json`.

## 5. Not done

- No additional native test.
- No re-run of BASE to close the setup gap.
- No Stage 2 work, promotion, signing, push, merge or release.

Closing the INCOMPLETE verdict, by accepting the gap or by a repeat check, is the Designer's and the Owner's
decision.
