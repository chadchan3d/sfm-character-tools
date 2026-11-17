# F-01 OT1S: minimal native integration smoke check (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** "F-01 — OT1 Integrated Candidate: Final Qualification" (Designer ACCEPT WITH CONDITIONS); record
`cpm/qualification/F01_OT1_PRODUCTION_GUARD.md`.

**What it checks (the integrated candidate is not yet promoted; production is unchanged):** on the known Krystal
fixture, (1) the integrated production reference guard accepts the known three-reference graph, before the Body
transaction and again before `Operate()`; (2) Body Apply produces the expected physical scales; (3) native Undo
restores the baseline; (4) native Redo restores the applied state; (5) a final Undo restores the baseline again;
(6) the same-model peer stays unchanged; (7) installation and library restoration succeed. No controlled failure and
no shared-reference scene: those are already qualified (OT1 native trial; offline suites).

| Item | Value |
|---|---|
| Integrated candidate CPM | `48ff01a3…` (`d719bb0`; production reference guard) |
| Qualification build | `10328efe…` (one line, the registry mode) |
| Session | `OT1S_KRYSTAL.dmx`: verified copy of the R2 fixture `259ea8a6…`, shot15, 0.2083 s; `OT1S_SPARE.dmx` is copied by the reused pre and never opened |
| Preset | Krystal's `Body` (`cd31c7f1…`), only read: `bip_head` 1.13 → 1.33, `bip_tail00` 0.8 → 1.0 |
| Observer | `observer/F01_OT1S_Observe.py` (see `ot1s.template.json`): the pinned OT1 observer's recording hooks plus a pass-through hook on the production guard; its injector is never armed |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_ot1_integration_smoke\tools\smoke_tool.py <Q>\ot1s.json <command>` |
| Protected inventories | `usermod\scripts`, `usermod\cfg`, the preset library, the SFM sessions folder; the published CPM `ccbed9d7…`, both registries absent, `.pyc` and housekeeping files |

**Never:** save the session; move the playhead, change the shot or retime; apply Happy, any Expression or any preset
other than `Body`; touch the peer after creating it; edit visibility; use Poses; Update, Delete, Rename or Favorite a
preset; choose Undo or Redo more often than listed; run any other script.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `ot1s.template.json` to `<Q>\ot1s.json` (a new run folder); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: … 10328efe… differs from the candidate in line 42546 only` |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (OT1S): preset library backed up` |
| P3 | `install`, then `check` | `"installation": "qualification"` |

## Native sequence (Owner, one SFM process)

Setup line, once after opening CPM:
```
OT1S_DIR = r"<Q>"; OT1S_REPO = r"<REPO>"
```
Capture line (only the step name changes; each step once):
```
OT1S_STEP = "BASE"; execfile(OT1S_REPO + r"\real_sfm_qualification\f01_ot1_integration_smoke\observer\F01_OT1S_Observe.py")
```
Each capture prints `OT1S <step>: <n> events | settled map Body … | undo … redo … | guard … | errors … | written`.

1. Start SFM. **File > Open** `<Q>\sessions\OT1S_KRYSTAL.dmx`. **Motion Editor**, **shot15**; the playhead is
   **0.2083 s** as opened (if not, STOP: do not move it).
2. **Peer.** Animation Set Editor: **Create Animation Set for New Model**
   `models/fursonas/starfox/krystal/bodies/krystal2020.mdl` (instance B). Change nothing on it.
3. Open **Character Preset Manager**, **Refresh Models**, select **`Krystal`** (A, the original). Submit the setup
   line. Capture **BASE** (installs the hooks; expected: `settled map Body FAIL`, undo `CreateAnimationSetAndModel`,
   errors none).
4. **Apply.** **Body Presets**: select `Body`, **Apply**. Note the status message exactly (expected:
   `Body Preset applied.`). Capture **APPLY** (expected: `settled map Body PASS`, undo `Apply Body Preset`,
   `guard 4 accepted, 0 refused`).
5. **Undo.** **Edit** menu: it must read **Undo Apply Body Preset**; choose it once. Capture **UNDO** (expected: undo
   `CreateAnimationSetAndModel`, redo `Redo Apply Body Preset`).
6. **Redo.** **Edit** menu: it must read **Redo Apply Body Preset**; choose it once. Capture **REDO** (expected:
   `settled map Body PASS`, undo `Apply Body Preset`).
7. **Final Undo.** **Edit** menu: **Undo Apply Body Preset** once. Capture **UNDO2** (removes the hooks).
8. Exit SFM **without saving**. Report each message and anything visible (A's head and tail after each step; whether
   B ever changed).

## STOP conditions

Exit SFM **without saving** and report; Claude still runs `library Q`, `collect-logs`, `restore`, `check`, `analyze`:
- a capture prints `errors` other than `none`, refuses, or says the hooks are not installed;
- the playhead is not 0.2083 s at step 1, or anything moves it;
- step 4 is refused (for example "scale expression is shared or ambiguous") or fails: do not Undo; capture APPLY,
  then exit. A "couldn't confirm" message is not a STOP: continue steps 5–8 exactly;
- the Edit menu does not name `Apply Body Preset` at steps 5–7: choose nothing; exit;
- B changes visibly; anything is saved, updated, deleted or trashed; SFM crashes, shows a recovery prompt or hangs
  for more than a minute.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q` | no library difference except the known `character.json` rewrite, if any |
| R2 | `collect-logs` | one CPM log |
| R3 | `restore`, then `check` | library cleanup exact, `RESTORED`; `"installation": "published"` |
| R4 | `analyze` | `OT1S_VERDICT.md` |

**Verdict** (`tools/smoke_analyze.py`): **SMOKE PASS** only when the GUARD, APPLY, UNDO, PEER and EVIDENCE gates all
pass; **SMOKE FAIL** when the evidence is complete and a functional gate fails; **INCOMPLETE** when evidence or
restoration fails. Unrelated files appearing in a protected folder during the run (as in OT1) are recorded and left
untouched; they make restoration, and so the verdict, INCOMPLETE until reviewed.
