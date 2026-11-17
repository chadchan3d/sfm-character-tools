# F-01 OT1 — Native ordering-trial results

**Date:** 2026-11-16 (native run), 2026-11-17 (closeout). **Authority:** "F-01 OT1 — Native Execution Authorization,
OWNER AUTHORIZATION: GO"; closeout under "F-01 OT1 — Native Results and Narrow Closeout" and "F-01 OT1 — Owner
Confirmation and Closeout". **Kit:** `2f4d877` (`F01_OT1_ORDERING_TRIAL_PREPARATION.md`,
`real_sfm_qualification/f01_ot1_ordering_trial/`). **Trial candidate:** `0cea8acd…`, qualification build
`0fbb4fb1…`; observer `5a13708a…`. **Run folder (raw evidence, not committed):**
`E:\SFM_U0B_Scratch\f01-ot1-ordering-trial-r1`.

A qualification trial: it records evidence for review. It is not a release, promotion or production decision.

## 1. Verdicts (kept separate)

| Item | Result |
|---|---|
| **Original OT1 formal verdict** | **INCOMPLETE** (`evidence\OT1_VERDICT.json` `9ea42020…`, `.md` `b1f4f3f9…`), unchanged. 73/75 checks; gates APPLY FAIL, UNDO PASS, ABORT PASS, EVIDENCE FAIL. Failed: `history.one_owned_entry` (an analyzer assumption, below) and `restore.published_and_inventories_equal` (the external file, below). |
| **Corrected replay verdict** | **INCOMPLETE** (`evidence\OT1_VERDICT_REPLAY.json` `e4cbedf0…`, `.md` `2e0e3580…`). 74/75 checks; **APPLY PASS, UNDO PASS, ABORT PASS**; EVIDENCE FAIL on `restore.published_and_inventories_equal` only. The replay names the original verdict by SHA-256; every original capture, log, verdict and restoration record is byte-identical after it. |
| **Owner-confirmed external inventory exception** | `E:\SourceFilmMaker Sessions\krystal_s2fm_alone_port.dmx` (`5a6a6cde…`, 201,423 bytes, written 2026-11-16 21:23:53 local): created independently of OT1 and unrelated to F-01 (Owner confirmation, "F-01 OT1 — Owner Confirmation and Closeout"). It was written after `pre` (19:38) and before BASE (22:56); every capture shows only `OT1_KRYSTAL.dmx` open. Not modified, removed or relocated; the inventory baseline and `restore.json` (`restored: false`) are unchanged. It is the only inventory difference. |
| **Trial-caused changes** | All restored: preset library exactly as backed up (files and folders; no library difference during the run); published CPM `ccbed9d7…` reinstalled; both registries removed; `usermod\scripts`, `usermod\cfg` and library inventories equal their baselines; `OT1_KRYSTAL.dmx` unsaved (`259ea8a6…`). Q1 (240 files) and PS-2 (1,270 files) evidence byte-identical before and after. |

The formal candidate verdict therefore remains INCOMPLETE. With the history predicate corrected, the only open item
is the Owner-confirmed external file, which the analyzer, by design, does not exempt; whether that exception permits a
formal PASS is a review decision.

## 2. Native functional findings (Owner-accepted observations; measured)

| Step | Head / tail physical | Head expression input → result | Body map | Undo / Redo labels |
|---|---|---|---|---|
| BASE | 1.13 / 0.80 | 0.113 → 1.13 | FAIL (pre-Apply) | `CreateAnimationSetAndModel` / – |
| APPLY | **1.330049 / 1.00** | 0.133005 → 1.330049 | **PASS** | `Apply Body Preset` / – |
| UNDO | **1.13 / 0.80** | 0.113 → 1.13 | baseline | `CreateAnimationSetAndModel` / `Redo Apply Body Preset` |
| REDO | **1.330049 / 1.00** | 0.133005 → 1.330049 | PASS | `Apply Body Preset` / – |
| UNDO2 | **1.13 / 0.80** | 0.113 → 1.13 | baseline | `CreateAnimationSetAndModel` / `Redo Apply Body Preset` |
| ARM | 1.13 / 0.80 | 0.113 → 1.13 | baseline | as UNDO2 |
| ABORT | **1.13 / 0.80** | 0.113 → 1.13 | baseline | `CreateAnimationSetAndModel` / – |

- **Physical Apply:** inside the owned transaction, after the operator, both expression results were the expected
  1.330049 / 1.0 while the physical scales were still 1.13 / 0.80; CPM's own same-time refresh then advanced the
  physical scales to 1.330049 / 1.0; CPM's deferred physical verification logged `committed-verified` and the status
  read "Body Preset applied." This is the ordering Astra hypothesised, and the Q1 lag did not occur.
- **Undo, Redo, final Undo:** every raw field of Krystal A (controls, bone positions, orientations, scales, flex
  weights, visibility) and both scale graphs (source, key, expression input and result, physical scale, output mode
  and empty log) returned exactly (within 1e-6) to BASE after each Undo and to the Apply state after Redo, including
  `bip_head`'s physical scale (one step behind after Undo in Q1).
- **Verified Abort:** with the controlled failure armed, both expressions were operated and verified, the failure
  fired once after the tail's operator call, CPM's abort verification logged `restored=True` (outcome
  `recovery-verified`), Krystal A equalled ARM exactly, no history action was added, the injector fired once and the
  hooks were removed.
- **Peer isolation:** the same-model peer (`krystal20201`) was identical to BASE at all six later captures.
- **Preflights (BASE, ARM):** the channel-track scan found one reader and one writer per expression with nothing
  unreadable; the direct DataModel traversal found exactly the three expected references per expression and ended at
  the sentinel (value `0`), the same live elements at BASE and ARM; class entries and `vsUtils` membership unchanged
  (`vsUtils` never loaded); Undo state and playhead unchanged across each preflight.
- **History observation (preserved, not gated):** the aborted controlled-failure Apply kept the previous Undo entry
  (`CreateAnimationSetAndModel`) but cleared SFM's pending Redo entry (`Redo Apply Body Preset`) that existed at ARM.
  No history action was added. SFM discards pending Redo when a new action starts, even one that is then aborted.

## 3. The history-predicate correction (offline)

The original analyzer required SFM's `GetUndoItemCount` to rise by exactly 1 for the Apply. The measured counts were
BASE 24041, APPLY 24078 (+37), UNDO 24041 (−37), REDO 24078 (+37), UNDO2 24041 (−37), ARM 24041, ABORT 24041 (+0): the
count is of internal change records, not user-facing history actions. The corrected `history.one_owned_entry` requires
the top-level label `Apply Body Preset` with Undo available and no pending Redo after the Apply, on a BASE whose label
is a different action; exactly one ordinary Undo, Redo and final Undo restoring the measured states remain the UNDO
gate's existing label and exact-restoration checks; `history.no_entry_added` also compares Undo availability. The counts
are reported as diagnostic evidence; the Redo-cleared observation is reported as a finding. No other check, threshold,
the candidate or the observer changed.

`tools/ot1_analyze.py` `c3a33489…`, `tools/ot1_tool.py` `82cecbba…` (adds `replay`), `tests/test_ot1.py` `2acd36d0…`:
**99/99 on Python 3.10.6** (8 added: the realistic +37/−37 counts with correct labels pass; an inconsistent count alone
does not decide history; a wrong Apply label, a pending Redo after the Apply, an Apply on a BASE already ending with an
Apply action, an Undo leaving a second Apply entry, and an aborted Apply changing the Undo stack fail; replay refuses
without an original verdict and writes separate files). The observer, candidate and template are unchanged.

## 4. Remaining qualification limitations

1. The formal verdict is INCOMPLETE until review decides how the Owner-confirmed external file is treated.
2. One trial: one character (Krystal), two existing mode-3 scales, one same-model peer, one fixture and time, one
   controlled failure. Not exercised natively: mode-1 scales, created graphs, other rigs, repeated Applies, other
   times or shots, larger scenes.
3. The physical advance at CPM's own refresh is observed, not explained: why the expression result must be current
   before the refresh (operator ordering and dirty state) is not established.
4. Undo exactness was measured at settled captures seconds after each action, not at intermediate event boundaries.
5. The observer read CPM's own snapshot inside the transaction and after the refresh; Q1 showed such reads do not
   advance evaluation, but the candidate has not run unobserved.
6. Direct-reference coverage excludes indirect and Python-side references.
7. The history predicate was corrected after the run; the corrected replay uses the same preserved evidence.

## 5. Production-promotion readiness

**Not ready for promotion.** The candidate is qualification-only; Astra's adjudication puts production repair on hold,
and promotion needs separate adjudication and authorization. This trial supplies favourable evidence for that review
(correct physical Apply, exact native Undo/Redo/final Undo, verified Abort, peer isolation), but the formal verdict is
INCOMPLETE, the evidence is one narrow trial, and production work (scope beyond the trial, user-facing copy, packaging,
release qualification) has not started. Shipping behaviour (`committed-unverified`) remains correct for v1.0.0.
