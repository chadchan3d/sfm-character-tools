# F-01 Stage 1: Fox native run 3, results and Abort recovery diagnosis (2026-11-19)

**Authority:** "F-01 Stage 1 — Fox Run 3 Native GO" (checkpoint `e32b157`) and "F-01 Stage 1 — Fox Run 3 Native
Results".

**Status:**
- This record covers diagnosis only. **No code, kit or procedure was changed.**
- The analyzer verdict is preserved unchanged.
- The preset library and the published v1.0.0 installation were restored and verified.

## 1. Formal verdict

**Automated verdict: INCOMPLETE.** This comes from the unchanged analyzer `a8623246…`.

| Item | Identity |
|---|---|
| `S1F_VERDICT.json` | `561f1b091ca1d6404efe61371509ed6012626bf362ed551523e742d0ffcb9de0` |
| `S1F_VERDICT.md` | `522637aa8b699d58072464a404badce1b58359df9bd99a95c41301017817196f` |
| Candidate / qualification build | `2088b4af…` / `b195515f…` |
| Disposable session (saved by Process A) | `fcf2441c…` |
| CPM log, Process A (pid 33356) | `01ab23bc…` |
| CPM log, Process B (pid 18760) | `275b68fd…` |
| Captures | PREP `3169132d…`, SAVED `798fceb3…`, BASE `6bedecb2…`, APPLY `aef038e5…`, NAV `57130861…`, UNDO `a35c71ff…`, REDO `84fc8daa…`, NOOP `6085d861…`, UNDO2 `b65f9046…`, ABORT `cc1571a6…` |

**Gates:**
- **Passed:** PREP, SAVE, APPLY, POSTURE, HISTORY, PEER and TAILS.
- **Failed:** ABORT and EVIDENCE.

**The three failed checks have one cause:**
1. `abort.verified_by_cpm`: CPM logged `BODY-abort-unverified`, not `BODY-abort-verified`.
2. `abort.authored_state_and_history_restored`:
   - authored differences: **none** (`[]`);
   - Undo state: `can_redo` false, `redo_desc` "".
3. `log.no_unverified_uncertain_or_failed_abort_result`: the log contains the `abort-unverified` line.

**Everything else passed:**
- **Numerical contract:**
  - the reopen equalled SFM's load renormalization exactly, with 69, 66 and 31 keys renormalized in the three sets;
  - P1 admitted the 5 reloaded offsets as `BODY-rotation-equivalent`, with a maximum angle of 3.87e-6° against the 0.0005° limit.
- **Apply:** 212 inserts, verified by P7.
- **History:** Undo and Redo restored exactly; the repeated Apply wrote nothing and added no entry; the final Undo
  restored BASE.
- **Isolation:** the source, the peer and Tails were unchanged.
- **Restoration:**
  - the library equals the pre-run library: the 2 added files were moved to `evidence/library_after`;
  - the published `ccbed9d7…` is reinstalled;
  - the inventories are equal.

**Owner visual acceptance (reported separately):**
- Process A and Process B, up to and including the final Undo, behaved as expected.
- The Owner accepts the visual result.
- This is separate from the automated verdict and does not change it.

## 2. The failed recovery predicate

**The predicate:**
- In `prod_body_same_state`, which `prod_body_apply` calls after `AbortUndoableOperation`, the failing line is:
  ```python
  undo = prod_pose_undo_state(dm())
  if prod_pose_undo_problems(undo) or undo != pre[u"undo"]:
      problems.append(u"Undo history changed or unreadable")
  ```
- The log reports exactly one problem: `BODY-abort-unverified {"problems": ["Undo history changed or unreadable"]}`.
- Every other comparison in the predicate found nothing:
  - instance resolution;
  - evaluated state;
  - every written binding's times, values, metadata, defaults, bookmarks, curve types, compression and curve info;
  - the apply gate.

**The Undo state:**

| | enabled | can_undo | undo_desc | can_redo | redo_desc |
|---|---|---|---|---|---|
| P1 baseline (= UNDO2) | true | true | `Change Recording State` | **true** | **`Redo Apply Pose S1 Fox`** |
| After the Abort (= ABORT) | true | true | `Change Recording State` | **false** | **""** |

**Why:**
- The procedure places the controlled Abort immediately after the final Undo (step B9), so a pending Redo entry
  exists at P1.
- `StartUndo` and the writes in the owned transaction start a new action, and SFM discards pending Redo when a new
  action starts. `AbortUndoableOperation` removes the owned action but cannot bring the discarded Redo back.
- This SFM behavior is already on record. OT1 measured it natively (`F01_OT1_NATIVE_RESULTS.md`): "SFM discards
  pending Redo when a new action starts, even one that is then aborted."
- OT1's Abort predicate did not compare Redo, so OT1 verified.
- Every earlier body, scoped and pose kit ran its Abort with an empty Redo stack:
  - EF1 ran it at B2, straight after the restart;
  - S3 (B6) and SFP1 (B6) ran it after a successful Apply;
  - Stage D ran it after an Apply (B8) and states "the Redo stack is empty there, as W2 qualified".
- So the exact Undo comparison was never exercised with a pending Redo.
- Stage 1's procedure, which I wrote, broke that precondition, and the run exposed the gap.

## 3. Actual mismatch versus verification defect

**There was no restoration mismatch in the animation.** An independent full comparison of the observer's ABORT
capture against UNDO2 found exactly three differences:
- `session.undo.can_redo`;
- `session.undo.redo_desc`;
- the step name.

Everything else is identical, for all three animation sets (Fox D, Fox S and the peer):
- every channel and log;
- every key time and value;
- every bone and the evaluated pose;
- the names, selection and qualification-fault slot (consumed).

**Stale evaluation and observer limits are ruled out:**
- CPM's own post-Abort predicate also found no channel, evaluation or gate difference.
- The navigation, Undo and Redo captures read the same evaluated state as CPM.

**The one real change is to the history.** The pending Redo entry `Apply Pose S1 Fox` was discarded. The Undo stack
below the top entry cannot be read by CPM or the observer (only the top Undo and Redo descriptions and availability
are exposed). The top entry and its availability are exactly as before.

**So this is a verification defect, failing closed:**
- The predicate demands a history state that SFM cannot produce once any new action has started.
- The lockout correctly withheld "Nothing was changed": strictly, the Redo history did change.
- In ordinary use, any Apply that fails after its writes, made after an Undo, would lock CPM out like this even
  though the character is exactly restored.

**The same exact comparison is in all three Apply routes:**
- `prod_pose_same_state` (line 44227);
- `prod_body_same_state` (line 45919);
- `prod_scope_same_state` (line 48802).

**`prod_body_same_state` is also P2's final revalidation** (line 45941), where the exact comparison must stay.

## 4. Smallest justified correction (proposed, not implemented)

**C1, CPM: the post-Abort Undo predicate only.**
- **Scope:** the three `*_same_state` functions gain an Abort-only mode. P2 and the no-op check stay exactly as
  they are.
- **Requirement:** after `AbortUndoableOperation`, the Undo state must satisfy one of:
  - it is exactly the P1 state; or
  - P1 had a pending Redo (`can_redo` true), and the state now equals the P1 state with only `can_redo` false and
    `redo_desc` "". Here `enabled`, `can_undo` and `undo_desc` must match exactly, and the result must still be
    readable with Undo enabled.
- **Still refused:**
  - any other Undo difference: an added or remaining owned entry, a changed top entry, or Undo disabled or
    unreadable;
  - any authored, evaluated or gate difference.
- **New log line:** `BODY-abort-verified` gains a `redo_cleared` flag.

**C2, CPM wording (Designer/Owner choice).**
- **When the Redo history was cleared:** "Nothing was changed" is not literally true of the history. Proposed:
  "The pose couldn't be applied. Your character wasn't changed. (SFM's Redo history was cleared.)"
- **When there was no pending Redo:** the existing message stays.

**C3, CPM wording for genuinely unverified recovery.** Adopt the Owner's proposal:
- title **Pose operation stopped**;
- text: "CPM couldn't confirm that all changes were undone. Check your character before continuing. Restart SFM to
  use pose tools again."

The lockout itself is unchanged: it is not suppressed or relaxed. The current title "Recovery could not be verified"
is at lines 32972 and 39548, and the message is `PROD_POSE_MESSAGES["recovery-unverified"]`.

**C4, kit:**
- `abort.authored_state_and_history_restored` accepts the same single measured transition: UNDO2 with a pending
  Redo becomes ABORT with Redo cleared and everything else exact.
- `abort.verified_by_cpm` still requires `BODY-abort-verified`.
- The procedure's expected Abort message follows C2.
- The run 3 evidence becomes a replay fixture, and the tests cover:
  - the exact, Redo-cleared and other-history-difference cases;
  - an owned entry left behind;
  - Undo being disabled.

**Not proposed:**
- moving the Abort to a point with an empty Redo stack only: that would pass the kit but leave the product defect;
- refusing Apply when Redo is pending: that would block a normal workflow;
- any change to P2, P7, the numerical contract or the authored-data checks.

**Offline tests:**
- exact Undo restoration verifies;
- Redo cleared from a pending Redo verifies, with the flag;
- each of these stays unverified:
  - Redo cleared when P1 had none;
  - a changed `undo_desc` or `can_undo`;
  - a left-over owned entry;
  - Undo disabled;
  - an unreadable Undo state;
- P2 still refuses a cleared Redo as stale;
- the same cases run for the pose, body and scope routes.

## 5. Boundaries kept

- Runs 1 and 2 and their verdicts are unchanged.
- No further native test was run.
- There was no Stage 2 work, production promotion, signing, push, merge or release.
- This record awaits Designer/Owner review before any implementation.
