# F-01 v1.1.0 RC3 native release smoke: results

**Authority:** "F-01 v1.1.0 RC3 — Native Smoke Test GO" (checkpoint `ba81520`). Owner report: "F-01 RC3 — Owner
Acceptance and Save New Delay" (2026-11-20). Kit: `real_sfm_qualification/f01_v110_rc3_smoke/` (unchanged). Run folder:
`E:\SFM_U0B_Scratch\f01-v110-rc3-smoke-r1` (not committed).

| Result | Value |
|---|---|
| **Automated verdict (unchanged analyzer `9e3255a6…`)** | **INCOMPLETE (19/21)**. `RC3S_VERDICT.json` `0f12ba2e…0439`, `RC3S_VERDICT.md` `0b571c8a…cd53` |
| **Owner functional acceptance** | **PASS**: Fox and Tails Full body Save, Apply, Undo and Redo worked; no deformation, targeting or restoration problem reported |
| **Installation and library restoration** | **RESTORED**: published CPM `ccbed9d7…` installed, both registries absent, library cleanup exact (`files_equal_pre`, `folders_equal_pre`), no inventory problem; `check` → `"installation": "published"` |
| **Fixtures** | R2 fixture `259ea8a6…` unchanged; `RC3_SESSION.dmx` `259ea8a6…` and `RC3_SPARE.dmx` `61df8bcd…` unchanged (never saved) |

## 1. What the verdict says

Every functional gate passes:
- FOX: saved once, admitted by the structural adapter (36 constraints, 23 handles, 214 written), revision 1 record, applied and verified to `foxmccouldwm3`;
- TAILS: saved once (7 simulated leaves, described without values), revision 2 record, applied and verified to `milestailsprower3`;
- TARGET: each applied to another instance of the same model;
- DISPLAY: Pose Info opened for both.

The two failures are both caused by actions outside the procedure, taken after the procedure's steps (log ops 12–17):

| Check | Failure | Cause |
|---|---|---|
| EVIDENCE `library_changes_expected` | two extra records | Op 13 saved `Tails sit` (Full body) from the session's **original Fox** `foxmccouldwm1`; op 15 saved `Tails sit alt` from the **original Tails** `milestailsprower1` |
| CLEAN `no_refusal_failure_or_recovery` | op 17 `failed-precommit` | Op 16 applied `Tails sit alt` back onto `milestailsprower1` (committed and verified; the session was not saved). Op 17 applied a pose to `milestailsprower1` and was **refused before any write** (`native_committed: False`) with "This pose was saved with different body proportions and can't be applied safely. Nothing was changed." |

By the procedure's own rule ("INCOMPLETE: evidence … fails"), the verdict is INCOMPLETE. It is not reinterpreted. The
op 17 refusal is a correct refusal with an inaccurate explanation (section 2). It is not a failure of Save, Apply,
Undo or Redo.

## 2. Op 17: the actual refusal cause

The guard is `prod_body_compare_descriptor` (the scale comparison, code `proportions`). Its log detail was
`scale state differs: [u'scale/handles/rig_chest']`.

The two Tails records compared:

| | `RC3 Tails` (new Tails, `rig_biped_simple`) | `Tails sit alt` (the fixture's original Tails) |
|---|---|---|
| Model scale, 131 bone scales | identical | identical |
| Rig handles | 23, including `rig_chest` (parent `rig_spine_2`) | 22, **no `rig_chest`** |
| Constraints | 36 | 34 (no point/orient constraint from `rig_chest` to `bip_spine_3`) |
| `bip_spine_3` | constrained | FK |

The body proportions are identical. The rigs differ. The record's scale map lists every handle, including
`rig_chest` (`{"present": false}`: it has no scale attribute). The scale comparison runs before the handle and
constraint comparisons, so the missing handle is reported as a proportions difference.

The refusal itself is correct, because the structural route never transfers across differing rigs.

## 3. Owner's usability finding: Save New delay

Clicking Save New takes about 5 seconds before the dialog appears, without feedback. Measured on the CPM's own log
(op 3 Fox, op 8 Tails): **3.4 s** of read-only work between `PROD_OPERATION_BEGIN` and the end of the
structural-adapter probe. The rest (the click to BEGIN, and building the dialog) is not logged. Investigation and
the proposed correction are reported separately, and nothing is changed yet.

## 4. Release disposition

RC3's functional evidence for Fox and Tails is accepted by the Owner, and all functional gates pass. Before RC3 can be
recommended for final release preparation, two open items need the Owner's or Designer's decision:
1. the INCOMPLETE automated verdict, caused only by off-procedure actions: accept by adjudication, or repeat a
   procedure-only smoke;
2. whether the Save New feedback and the refusal wording are corrected before release (any CPM change makes a new
   candidate).

RC2 remains the accepted fallback. Nothing was signed, pushed, merged or published.
