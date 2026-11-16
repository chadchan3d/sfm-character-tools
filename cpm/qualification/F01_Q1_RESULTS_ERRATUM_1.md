# F-01 Q1 results — Erratum 1: the expression results at Body's refresh-before boundary

**Date:** 2026-11-16. **Corrects:** `F01_Q1_RESULTS.md` (committed in `9f0f7ff`), section 2, the table row
"refresh before" and the "Failing predicate" paragraph that generalizes from it. **Authority:** Astra's adjudication of
the Q1 evaluation-order review (ACCEPT WITH CONDITIONS), which identified the error; the Designer's assignment
"F-01 — Implement Astra's Qualification-Only Ordering Trial" ("record the corrected refresh-before interpretation as a
separate erratum").

The historical record is not rewritten: `F01_Q1_RESULTS.md` keeps its text and gains only a one-line pointer to this
erratum. The raw evidence, the original analyzer report and the replay are unchanged.

## 1. What the results stated, and what the evidence shows

`F01_Q1_RESULTS.md` section 2 reported, for Body's own operation:

| Boundary | Expression `result` (as stated) | Physical bone scale |
|---|---|---|
| refresh before | 1.33004916 / 1.0 | 1.13 / 0.8 (old) |

The preserved evidence shows a different expression result at that boundary. From the replay of the run's own
captures (`evidence\Q1_REPORT_REPLAY.md`, propagation table; `bip_head` / `bip_tail00`):

| Boundary | Expression input (`value`) | Expression `result` | Physical bone scale |
|---|---|---|---|
| pre-write | 0.113 / 0.08 | 1.13 / 0.8 | 1.13 / 0.8 |
| post-write | 0.13300492 / 0.1 | 1.13 / 0.8 | 1.13 / 0.8 |
| precommit | 0.13300492 / 0.1 | 1.13 / 0.8 | 1.13 / 0.8 |
| **refresh before (Body)** | 0.13300492 / 0.1 | **1.13 / 0.8 (old)** | 1.13 / 0.8 |
| **refresh after (Body)** | 0.13300492 / 0.1 | **1.33004916 / 1.0** | **1.13 / 0.8 (old)** |
| deferred | 0.13300492 / 0.1 | 1.33004916 / 1.0 | 1.13 / 0.8 |
| settled | 0.13300492 / 0.1 | 1.33004916 / 1.0 | 1.13 / 0.8 |
| refresh before (Happy) | 0.13300492 / 0.1 | 1.33004916 / 1.0 | 1.13 / 0.8 |
| **refresh after (Happy)** | 0.13300492 / 0.1 | 1.33004916 / 1.0 | **1.33004916 / 1.0** |

(Values rounded here; the replay table carries the unrounded floats.)

**Corrected reading.** Body's own same-time refresh advanced the expression results (head 1.13 → 1.33005, tail
0.80 → 1.00) while the physical scales stayed behind; Happy's refresh then advanced the physical scales. Each
same-time refresh advanced the chain by one link: input → expression result on Body's refresh, expression result →
physical scale on Happy's. The original row's "1.33004916 / 1.0" at "refresh before" was taken from the later
boundaries.

**The failing predicate, restated by boundary.** At every Body boundary from refresh-before through settled, CPM's
static trace failed with `(None, 'evaluated', 'incoherent')` for both bones:
- at **refresh before** (and at precommit), the incoherence is between the written input (0.133 / 0.1) and the
  expression result (still 1.13 / 0.8); the result and the physical scale agree;
- from **refresh after** through **settled** (and at Happy's refresh-before), it is between the expression result
  (1.33 / 1.0) and the physical scale (still 1.13 / 0.8).

The original paragraph described only the second form for all boundaries.

## 2. What does not change

- Every other measured statement of `F01_Q1_RESULTS.md`: the six authored checks (all True), the deferred map
  reproducing CPM's own result and log (`committed-unverified`, `bone-scales`), Happy making no scale write, only head
  and tail failing among the saved bones, and the duplicate-model Undo fields (only `bip_head`'s physical scale differs
  after Undo, 1.33 before vs 1.0 after, with the authored input and expression result returned; peer unchanged).
- The verdicts: the original analyzer report stays **EVIDENCE INCOMPLETE** (`Q1_REPORT.json` `c95da430…`); the replay
  with the corrected analyzer is **EVIDENCE COMPLETE** (`Q1_REPORT_REPLAY.json` `34bdc23c…`, `.md` `1332865e…`).
- The open questions: the precise operator ordering, dirty-state handling and the role of
  `SetHeadTimeInSeconds` + `ProcessEvents` are not established; the boundary maps' output-log rows were cut at the
  observer's depth bound (the settled maps carry them).

## 3. Evidence

| Item | Identity |
|---|---|
| Run folder (not committed) | `E:\SFM_U0B_Scratch\f01-q1-ps2-diagnostic-r1` |
| Original analyzer report (unchanged) | `evidence\Q1_REPORT.json` `c95da4303c1cb2f86d5b40c803f61981799fbf0545c6d06d4a6765308c94a285` |
| Replay (corrected analyzer) | `evidence\Q1_REPORT_REPLAY.json` `34bdc23c1a746b6c8d3ce2042fdddc4df009e30906ca7c879a526a4ae455b1c8`; `evidence\Q1_REPORT_REPLAY.md` `1332865efaa441d3519d9a8d8fef6069bec7fc40982ca4bc50f53f93834b0680` |
| Static-trace evidence at refresh-before | replay JSON `analysis.body.refresh_before.failing[*].static` = `[null, "evaluated", "incoherent"]` for both bones |
