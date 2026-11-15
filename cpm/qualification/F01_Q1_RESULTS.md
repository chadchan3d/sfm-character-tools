# F-01 Q1: PS-2 Body Preset and Undo diagnostic — results

**Date:** 2026-11-15. **Authority:** "F-01 Q1 — Native Diagnostic Execution Authorization, OWNER AUTHORIZATION: GO";
closeout under "F-01 Q1 — Owner Native Completion". **Kit:** `8ede527` (`F01_Q1_DIAGNOSTIC_PREPARATION.md`).
**Candidate:** `615acf0c…`, qualification build `849d0ed4…`. **Run folder (raw evidence, not committed):**
`E:\SFM_U0B_Scratch\f01-q1-ps2-diagnostic-r1`.

This is a diagnostic: it records field evidence. It makes no product verdict and implements no correction.

## 1. Verdicts (kept separate)

| Item | Result |
|---|---|
| **Analyzer verdict (formal)** | **EVIDENCE INCOMPLETE** (`evidence\Q1_REPORT.json` `c95da430…`), unchanged. |
| Cause of INCOMPLETE | Two analyzer assumptions, not missing evidence: (1) `fields.*` (all six captures) requires a game model in every animation set of the shot; this shot also holds a camera and two lights (`Main_Cam`, `SUN`, `SunHair`) with none, and every capture error list is empty. (2) `body.precommit_checks_observed` expected one `prod_bs_authored_matches` call per changed scale (2); CPM calls it six times for two changed scales — twice pre-write through `prod_bs_evaluated_matches` on the original values, twice post-write in `prod_bs_write_existing_scale`, twice at precommit — all six True. Every other evidence check passed (process, hooks installed and removed, refresh, deferred and settled maps, the deferred map reproducing CPM's result and log, Happy, two instances, the same instance throughout, the Apply and its Undo as the only history, no visibility edit, library, log, restoration, session). |
| Observer limitation | The event maps (refresh and deferred boundaries) were sanitized a second time inside the capture, so their output-channel log and input rows were cut at the depth bound (`<depth>`); the expression value and result, the physical scale, the classification and the predicate are present at every boundary. The settled maps carry the complete trace, including the logs. |
| **Restoration** | **Verified.** Library cleanup `files_equal_pre` and `folders_equal_pre` true (only the seeded `PS2 Dup Body` was added; no `character.json` rewrite this time); published CPM `ccbed9d7…`; both registries removed; all four inventories equal their baselines; `Q1_KRYSTAL.dmx` unchanged (`259ea8a6…`); the observer hooks were removed in SFM (DUP-UNDO `hooks_removed: true`) and no longer exist after SFM exited; PS-2's evidence tree byte-identical (1,270 files) before and after; the 11 collected evidence files byte-identical before and after restoration and analysis. |
| Deviation Q1-D1 | The first `pre` stopped in a precondition check (nothing written): the reused S3 pre needs `LEGACY_POSE` / `legacy_pose_sha256`, omitted from the Q1 template. Added to the run configuration with the value pinned in the S3/K2/UA-1 kits; checked only, never used. No existing pin changed. |

## 2. Body Preset scale verification — measured

The Owner applied `Body` (status: committed, CPM log `committed-unverified`, reason `bone-scales`, as in PS-2
operation 8). BODY's settled map failed, so `Happy` was applied (HAPPY captured).

`bip_head` (saved 1.33004916) and `bip_tail00` (saved 1.0) are the two changed scales; every other saved bone passed
at every boundary.

| Boundary | Authored input (expression `value`, input log key) | Expression `result` | Physical bone scale | Predicate (CPM's own functions) |
|---|---|---|---|---|
| precommit (6 calls) | original 0.113 / 0.08 before writing; 0.13300492 / 0.1 after writing and at precommit | — | — | `prod_bs_authored_matches` True ×6 |
| refresh before | 0.13300492 / 0.1 | 1.33004916 / 1.0 | **1.13 / 0.8 (old)** | static fails: `(None, 'evaluated', 'incoherent')` |
| refresh after (Body's own `same_time_refresh`) | same | same | **1.13 / 0.8** | same |
| deferred (CPM's snapshot; matches CPM's False and the log) | same | same | **1.13 / 0.8** | same |
| settled (Owner capture, seconds later) | same | same | **1.13 / 0.8** | same |
| Happy, refresh before | same | same | **1.13 / 0.8** | same |
| Happy, refresh after | same | same | **1.33004916 / 1.0** | passes |
| Happy settled | same | same | 1.33004916 / 1.0 | passes |

**Failing predicate:** the static classification's `evaluated` stage with evidence `incoherent` — the output channel
(mode 3, play, empty log) and the bone's physical scale did not equal the expression's result. Not the authored
inputs (source value, expression input and the one key all equal the requested native value), not the expression
result, not classification or implicit neutrality.

**Measured effect of Happy:** Happy made no scale write (its operation recorded no scale event; the authored inputs are
identical before and after). The physical scales changed during Happy's existing refresh: evaluated, not authored.

## 3. Duplicate-model Apply and Undo — measured (raw fields)

Target `Krystal` (handle 21688), peer `krystal20201` (handle 49430). `PS2 Dup Body` applied to A (log
`committed-unverified`, `bone-scales`); one Undo; Redo then named `Apply Body Preset`.

| Comparison | Target | Peer |
|---|---|---|
| BEFORE → APPLY | 6 control values and 5 flex weights changed (the preset's values); bone scales unchanged (physical `bip_head` still 1.33) | identical |
| APPLY → UNDO | the 6 controls and 5 flexes back; `bip_head` physical scale 1.33 → **1.0** | identical |
| **BEFORE → UNDO** | **controls identical, flex weights identical, every bone position and orientation identical; one field differs: `bip_head` physical scale 1.33 (before) vs 1.0 (after Undo)** | identical |

The authored `bip_head` scale input after Undo is back to 0.13300492 (expression result 1.33004916), the value before
the Apply. Its physical scale shows 1.0, the value the undone Apply had requested. At DUP-APPLY the authored input was
0.1 (result 1.0) while the physical scale still showed 1.33. Across Apply and Undo the physical scale shows the
previous authored value.

**Undo restoration:** every measured authored field and every control, flex weight and bone transform of the target
returned to its pre-Apply value except the evaluated `bip_head` physical scale. The peer never changed.

## 4. What the evidence shows, and what it does not

- Measured: the Body Preset's authored scale writes are correct at precommit, deferred and settled boundaries; the
  failing predicate is evaluation coherence (physical scale ≠ expression result); Body's own refresh and an ordinary
  settled interval did not update the physical scale; the next operation's refresh (Happy's) did; after the duplicate
  Undo the only remaining target difference is the same evaluated scale, one step behind the authored value. This
  reproduces both PS-2 findings with field-level evidence.
- Not established: why the evaluated scale advances on a later operation's refresh but not on the applying
  operation's own refresh or during the settled interval; whether other ordinary events (e.g. scrubbing) would update
  it; the output channel's log rows at the refresh and deferred boundaries (cut by the observer depth bound; present in
  the settled maps). No correction is inferred here (R4 section 6.3: establish the ordering before selecting a remedy).

## 5. Proposed follow-up (not started; each needs authorization)

1. Kit correction, offline: the analyzer's `fields` check to require game-model fields only for animation sets that
   have a game model, and its precommit check to accept CPM's documented call pattern (pre-write, post-write and
   precommit calls, all True, covering every changed scale); the observer's event sanitization depth so boundary maps
   keep the output-log rows. Then a separately named replay of this run's preserved evidence (the original
   `Q1_REPORT` stays).
2. Designer review of the measured evaluation-ordering behaviour before any remedy is selected.
