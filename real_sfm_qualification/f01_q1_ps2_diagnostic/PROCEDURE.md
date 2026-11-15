# F-01 Q1: PS-2 Body Preset scale-verification and duplicate-model Undo diagnostic (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** Blueprint R4 section 6.3; "F-01 — Q1: PS-2 Body Preset and Undo Diagnostic Preparation" (offline
preparation approved).

**What it establishes (field evidence only; no repair):**
1. *Body Preset Apply commits but fails deferred `bone-scales` verification* (PS-2 operations 8 and 18): which saved
   bone fails `prod_bs_index_verify_saved`, by which exact predicate (implicit neutral, classification, static trace,
   physical value), with the requested and physical values, the authored sources, keys and expression inputs, the
   expression result, output mode and log state, at CPM's precommit check, immediately before and after its existing
   same-time refresh, at its deferred verification (on the very snapshot CPM used), and after an ordinary settled
   event turn; if the settled map still fails, the same around Happy's existing refresh.
2. *After duplicate-model Body Preset Undo, the target's control digest returns but its model digest does not*: the
   raw (unrounded) target and peer fields before Apply, after Apply and after one Undo (controls, bone positions,
   orientations and scales, flex weights, model visibility, skin, body group, child visibility), the Undo history and
   the selected instance, with no intervening visibility edit.

**Not repeated:** the PS-2 campaign. Nothing is changed in CPM: no tolerance, refresh, sleep, polling, retry or Undo
is added; committed-unverified handling is unchanged.

| Item | Value |
|---|---|
| Candidate CPM | `615acf0c…` (`fda1fb3`). Its Body path is byte-identical to PS-2's `84cd996c…`: all 107 relevant definitions (`prod_apply`, `prod_apply_deferred_verify`, `same_time_refresh`, `close_enough`, `EPSILON`, every `prod_bs_*` and `p03_*`, the instance resolution) compared equal |
| Qualification build | `849d0ed44101965de62165f01fcbb22b3caae9797e867169e71d4247b49cd4a2` (one line; the kit's verified install and restore need it; the Body path does not depend on it) |
| Session | `Q1_KRYSTAL.dmx`: verified copy of the R2 fixture `259ea8a6…` (PS-2's `PS2_KRYSTAL.dmx`), shot15, 0.2083 s |
| Presets | Krystal's `Body` (`cd31c7f1…`, bip_head 1.33, others 1.0) and `Happy` (`bc4e8585…`), verified unchanged since PS-2 and only read; PS-2's own `PS2 Dup Body` (`29629f1b…`, every bone 1.0) seeded from PS-2's evidence |
| Observer | `observer/F01_Q1_Observe.py` `81ab0bbc…` (hooks and captures; see its docstring) |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_q1_ps2_diagnostic\tools\q1_tool.py <Q>\q1.json <command>` |
| Restored afterwards | the published CPM `ccbed9d7…`; both registries removed; the preset library exactly as backed up (files and folders); every protected inventory equal to its baseline |

**Expected scale changes (from PS-2's log and the pinned records):** the session's existing scale graphs are
`bip_head` 1.13 and `bip_tail00` 0.8; `Body` changes both (to 1.33 and 1.0: two existing scale changes, PS-2
operation 8); `PS2 Dup Body` then changes `bip_head` to 1.0 (one change, PS-2 operation 18).

**Never:** save the session; edit visibility (clothing, bodygroups, Hide/Show) or anything else between the
duplicate captures; Update, Delete, Rename or Favorite a preset; use Poses; apply anything not listed; press Undo more
than the one step listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `q1.template.json` to `<Q>\q1.json` (a new run folder); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: … 849d0ed4… differs from the candidate in line 42220 only` |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (Q1): preset library backed up` (refuses if `Body`, `Happy` or `PS2 Dup Body` is not the pinned record) |
| P3 | `install`, then `check` | `"installation": "qualification"` |
| P4 | `seed` | `SEEDED: PS2 Dup Body--preset-49480.json (Body and Happy verified unchanged)` |

## Native sequence (Owner, one SFM process)

Setup line, once after opening CPM:
```
Q1_DIR = r"<Q>"; Q1_REPO = r"<REPO>"
```
Capture line (only the step name changes; each step once):
```
Q1_STEP = "BASE"; execfile(Q1_REPO + r"\real_sfm_qualification\f01_q1_ps2_diagnostic\observer\F01_Q1_Observe.py")
```
Each capture prints `Q1 <step>: <n> events | settled map Body …, PS2 Dup Body … | undo … | errors … | written`.

1. Start SFM. **File > Open** `<Q>\sessions\Q1_KRYSTAL.dmx`. **Motion Editor**, **shot15**, playhead **0.2083 s**.
   Open **Character Preset Manager**, **Refresh Models**, select `Krystal`. Submit the setup line.
2. Capture **BASE** (installs the hooks; expected `errors none`).
3. **Body Presets**: select `Body`, **Apply**. Wait for the status message; note it exactly (expected: applied, or
   "CPM couldn't confirm …", as in PS-2). Capture **BODY**.
4. **Only if BODY printed `settled map Body FAIL`:** **Expressions**: select `Happy`, **Apply**; note the message;
   capture **HAPPY**. Otherwise skip this step.
5. **Duplicate model.** Animation Set Editor: **Create Animation Set for New Model**
   `models/fursonas/starfox/krystal/bodies/krystal2020.mdl` (the same model; it becomes instance B). Change nothing on
   it. In CPM, **Refresh Models** and select **A** (`Krystal`). Capture **DUP-BEFORE**.
6. With **A** selected: **Body Presets**, select `PS2 Dup Body`, **Apply**. Wait for the message; note it. Do not
   touch visibility or anything else. Capture **DUP-APPLY** (its line should show `undo 'Apply Body Preset'`; if it
   shows anything else, note it and continue).
7. Click the viewport, press **Ctrl+Z once**. Check **Edit**: Redo should name `Apply Body Preset`. Capture
   **DUP-UNDO** (removes the hooks).
8. Exit SFM **without saving**. Report each message, anything visible (e.g. whether A's head changed after Apply and
   after Undo, whether B changed), and anything unexpected.

## STOP conditions

Exit SFM **without saving** and report; Claude still runs `library Q`, `collect-logs`, `restore`, `check`:
- a capture prints `errors` other than `none`, refuses, or says the hooks are not installed;
- an Apply is refused with a structural message, B changes when A is applied, or the Undo does not name `Apply Body
  Preset`;
- anything is saved, updated, deleted or moved to Trash other than the listed Applies;
- SFM crashes, shows an autosave recovery prompt, or hangs for more than a minute.

## Evidence, restoration and analysis (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q` | the run's library differences (the seeded `PS2 Dup Body`; Krystal's `character.json` rewrite, F-T01-1) |
| R2 | `collect-logs` | one CPM log |
| R3 | `restore`, then `check` | library cleanup `files_equal_pre` and `folders_equal_pre` true, then `RESTORED`; `"installation": "published"` |
| R4 | `analyze` | `Q1_REPORT.md` |

**Diagnostic PASS = `EVIDENCE COMPLETE`** (every evidence check of `q1_analyze`): the qualification build in every
capture; BASE, BODY, DUP-BEFORE, DUP-APPLY, DUP-UNDO (and HAPPY when BODY's settled map failed); readable raw fields
in each; one SFM process on the disposable session; hooks installed at BASE and removed at DUP-UNDO; the Body
operation, its precommit checks (as many as the log's changed existing scales), complete maps at both refresh
boundaries, and the deferred map reproducing CPM's own result and log outcome; a settled map; for the duplicate, two
instances of the model, the same selected instance throughout, the Apply and its deferred map observed, the history
being exactly that Apply and its Undo, and no visibility change on any instance; only the seeded preset and the known
character rewrite in the library; no recovery or uncertainty in the log; restoration exact; the session never saved.
**STOP / incomplete:** any of these missing or inconsistent; the report then says which, and the analysis is not used
for a cause decision.

The report's analysis is descriptive: the failing bones and predicates at each boundary with values, a reading
(not reproduced; deferred failure with a passing settled map; still failing when settled; and Happy's effect if
captured), and the field-level duplicate differences. It is not a product verdict; the cause decision and any
correction are for review and separate authorization (R4 section 6.3).
