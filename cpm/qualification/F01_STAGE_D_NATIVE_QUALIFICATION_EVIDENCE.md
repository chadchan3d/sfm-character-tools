# F-01 Pose Library Stage D: native qualification evidence

**Status:** Stage D **CLOSED / PASS** for its bounded functionality — Astra ACCEPT of candidate
`18849e5f7c9ccd9ab763d10a84a0629d363d8b58e1a6b7185a76bf1bca5b8004` (2026-11-04). **Production promotion on HOLD.**

**Supported scope:** Krystal (`krystal2020.mdl`), left arm, SFM timeline **Motion Editor (mode 2)**. Apply refuses
before writing in the Clip Editor and the Graph Editor. Production pose mappings remain experimental (the production
registry holds no qualified mapping).

## Accepted behaviour

- **Apply gate (P1):** `sfmApp.GetTimelineMode() == 2` and every target channel clock (`GetCurrentTime`) equal to the
  mapped (clip-stack) tick; otherwise a refusal before writing.
- **Revalidation:** the mode and clocks are revalidated at P2, **immediately before `StartUndo`**, together with the
  existing instance, time, key and history checks; a change refuses. At P7 a change gives committed-unverified.
- **Write:** one owned transaction; an insert is `InsertKeyAtTime(t)` then `SetKeyValue` (never `GetDefaultCurveType`,
  which crashed SFM natively on logs without curve info); an update is `SetKeyValue`.
- **Automatic display:** after a confirmed, owned commit and outside the transaction, one same-time
  `sfmApp.SetHeadTimeInSeconds` request at the original document time; the guarded deferred verification (P7) runs on
  the next normal turn. A failed P7 stays committed-unverified: no automatic Undo, no compensating keys.

## Native runs (one machine; disposable copies of the qualified destination `2b623376…`; Pose A `4916a724…`, Pose B `87e61f60…`)

| Run | Mode | Result |
|---|---|---|
| FA-3b | Motion Editor | Pose A at the mapped tick 50208: exact placement (arm within 0.001° of the saved oracle) after evaluation, after Undo/Redo of the insert and after navigating away and back. |
| ME-1 | Motion Editor | Candidate `18849e5f…`: Apply A verified automatically (`P6-refresh` → `P7-verified`); a true no-op with unchanged history; Apply B updated the 50208 keys and verified automatically. |
| ME-1b | Motion Editor | Undo B restored Pose A's exact keys and skeleton; Redo B restored Pose B's exact keys and skeleton; Pose B correct after navigating away and back. Comparator: MOTION EDITOR QUALIFICATION PASS. |

In every Motion Editor run: one SFM process, the shot15 Krystal instance, mode 2 throughout, clock = mapped tick 50208
at the original frame, unrelated channels, bones (local and world), placement and facing unchanged; the published CPM
`ccbed9d7…` restored afterwards with every protected inventory equal to its baseline.

## Findings that bound the scope

- FA-1 (Clip Editor, clock 50299): the 50208 key displayed 1.3–2.8° from the pose; FA-2 showed 50299 is exact in that
  context. TM-1: mode 3 (Clip) ↔ clock 50299, modes 2 and 4 (Motion, Graph) ↔ 50208 in this fixture.
- Gate 1: a same-time `SetHeadTimeInSeconds` request does not converge the editor contexts' clocks.
- In the Motion Editor every playhead move adds a `Modify Head Time` Undo entry above an Apply.
- SFM does not re-evaluate after a scripted key write until a head-time request or navigation.

## Remaining production requirements

1. **Capture consistency:** one native Save/Apply case on a non-flat interval in another supported shot (Save
   captures the visible pose; the record matches the observed skeleton; Apply reproduces it automatically in the
   Motion Editor and after navigation).
2. **Registry authorization:** promote only Krystal's qualified left-arm mapping to the production registry; every
   other mapping stays experimental; unsupported editor modes stay refused.

## Repository record

- `cpm/app/SFM_Character_Preset_Manager.py` `18849e5f…`; tests `test_cpm_app_f01_pose_live.py` `dd3ccb40…`,
  `test_cpm_app_f01_pose_page.py` `ab998711…`, `test_cpm_app_f01_pose_integration.py` `c6cce982…`,
  `test_cpm_app_f01_pose_core.py` `14eff07b…`, `test_cpm_app_canonical_route.py` `fe6feaaa…`.
- `real_sfm_qualification/f01_stage_d_nq1/` — native procedure, observers and offline comparators (13 files).
- Offline: F-01 live 67/67, core 253/253, library 87/87, integration 112/112, Poses page 24/24, M-06 334/334 and
  179/179, M-05 115/115 (Python 2.7.5 and 3.10.6); clothing-fit, operation-context and empty-states PASS; W2 162 OK.
  Unchanged historical FAIL rows only (canonical-route `derivation.added_top_level_is_bounded`, authority-cleanup 4,
  bounded-logging real-log-folder guard).
- Raw native evidence (observations, CPM logs, verdicts, restoration reports) is the owner's local archive and is not
  committed.
