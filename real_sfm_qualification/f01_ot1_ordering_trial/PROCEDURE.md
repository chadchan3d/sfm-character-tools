# F-01 OT1: qualification-only ordering trial (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** Astra adjudication (ACCEPT WITH CONDITIONS); the Designer's assignment "F-01 — Implement Astra's
Qualification-Only Ordering Trial"; record `cpm/qualification/F01_OT1_ORDERING_TRIAL_PREPARATION.md`.

**What it decides (the candidate is qualification only; production is unchanged):** whether operating the bound
expression inside the owned Body transaction makes a changed existing mode-3 bone scale (1) apply with a verified
physical scale, (2) undo, redo and undo again natively with exact authored and physical restoration, one history
entry at a time, (3) abort with CPM's own verified recovery when a controlled failure follows the operator call, the
same-model peer untouched throughout. **Apply PASS with Undo FAIL means the candidate FAILS.** No additional workaround
(another preset, a second refresh, retiming, a history listener) without renewed adjudication.

| Item | Value |
|---|---|
| Trial candidate CPM | `0cea8acd…` (see `ot1.template.json`); the only change from `615acf0c…` is the Body existing-scale write (`prod_bs_write_existing_scale` and its two new helpers) |
| Qualification build | `0fbb4fb1…` (one line, the registry mode; the kit's verified install and restore need it) |
| Session | `OT1_KRYSTAL.dmx`: verified copy of the R2 fixture `259ea8a6…` (Q1's and PS-2's), shot15, 0.2083 s; `OT1_SPARE.dmx` is copied by the reused pre and never opened |
| Preset | Krystal's `Body` (`cd31c7f1…`, bip_head 1.33, others 1.0), only read; it changes the two existing mode-3 scales `bip_head` 1.13 → 1.33 and `bip_tail00` 0.8 → 1.0 (Q1) |
| Observer | `observer/F01_OT1_Observe.py` (`403ea566…`), loading the pinned Q1 observer `f2eba1e0…` (see its docstring); BASE and ARM run the read-only graph preflight, including Astra's DC1 direct-reference check through SFM's shipped `vsUtils.iterReferringAttributes` (`vsUtils.py` pinned `d89f23c0…`) |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_ot1_ordering_trial\tools\ot1_tool.py <Q>\ot1.json <command>` |
| Protected inventories (S3 tool) | `usermod\scripts` (SCRIPTS_ROOT), `usermod\cfg` (CFG_ROOT), the preset library (LIBRARY), the SFM sessions folder (SESSIONS); plus the published CPM `ccbed9d7…`, both registries absent, `.pyc` files and housekeeping files |
| Restored afterwards | the published CPM `ccbed9d7…`; both registries removed; the preset library exactly as backed up (files and folders); every protected inventory equal to its baseline |

**Never:** save the session; move the playhead, change the shot or retime anything; apply Happy or any Expression;
apply any preset other than `Body`; touch, select or edit the peer after creating it; edit visibility; Update, Delete,
Rename or Favorite a preset; use Poses; press Undo or Redo more than the steps listed; run any other script.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `ot1.template.json` to `<Q>\ot1.json` (a new run folder); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: … 0fbb4fb1… differs from the candidate in line … only` |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (OT1): preset library backed up` (refuses if `Body` is not the pinned record or SFM's shipped `vsUtils.py` is not the pinned file) |
| P3 | `install`, then `check` | `"installation": "qualification"` |

## Native sequence (Owner, one SFM process)

Setup line, once after opening CPM:
```
OT1_DIR = r"<Q>"; OT1_REPO = r"<REPO>"
```
Capture line (only the step name changes; each step once):
```
OT1_STEP = "BASE"; execfile(OT1_REPO + r"\real_sfm_qualification\f01_ot1_ordering_trial\observer\F01_OT1_Observe.py")
```
Each capture prints `OT1 <step>: <n> events | settled map Body … | undo … redo … | injector … | errors … | written`;
BASE adds `| preflight PASS` or `| preflight FAIL`.

1. Start SFM. **File > Open** `<Q>\sessions\OT1_KRYSTAL.dmx`. **Motion Editor**, **shot15**; the playhead is
   **0.2083 s** as opened (if it is not, STOP: do not move it).
2. **Peer.** Animation Set Editor: **Create Animation Set for New Model**
   `models/fursonas/starfox/krystal/bodies/krystal2020.mdl` (instance B). Change nothing on it.
3. Open **Character Preset Manager**, **Refresh Models**, select **`Krystal`** (A, the original). Submit the setup
   line. Capture **BASE**. It first runs the read-only **graph preflight** (before installing the hooks): for A's
   existing `bip_head` and `bip_tail00` scale graphs, CPM's own snapshot and binding, then the candidate's own
   reader/writer scan and a diagnostic enumeration of the same channels track, recording the instance, the
   expression identities, the reader and writer counts, every unreadable clip, channel or endpoint, and whether the
   candidate's uniqueness precondition holds; and **Astra's DC1 check**: SFM's shipped
   `vsUtils.iterReferringAttributes` on each live expression (`bip_head_scale_rescale`, `bip_tail00_scale_rescale`),
   run to its end, must return exactly three direct references, matched by live element identity: A's animation
   set's `operators`, the admitted input channel's `toElement`, the admitted output channel's `fromElement`, with
   every owner and attribute name recorded. Any extra, missing, unexpected or unreadable reference, an API exception
   or an incomplete enumeration fails. (If `vsUtils` was not already loaded, this imports it; its import patches
   element equality for the rest of the session, which the capture records: design condition OT1-DC2.) It reads the
   Undo state and playhead before and after; it operates,
   writes and moves nothing and opens no Undo action. Then it installs the hooks. Expected: `settled map Body FAIL`,
   undo `CreateAnimationSetAndModel`, errors none, **`preflight PASS`**. **If it prints `preflight FAIL`: STOP before
   step 4** (exit without saving; nothing has been applied).
4. **Apply.** **Body Presets**: select `Body`, **Apply**. Wait for the status message; note it exactly (expected:
   `Body Preset applied.`). Capture **APPLY** (expected: settled map Body PASS, undo `Apply Body Preset`).
5. **Undo.** **Edit** menu: it must read **Undo Apply Body Preset**; choose it once. Capture **UNDO** (expected:
   undo `CreateAnimationSetAndModel`, redo `Redo Apply Body Preset`).
6. **Redo.** **Edit** menu: it must read **Redo Apply Body Preset**; choose it once. Capture **REDO** (expected:
   settled map Body PASS, undo `Apply Body Preset`).
7. **Final Undo.** **Edit** menu: **Undo Apply Body Preset** once. Capture **UNDO2**.
8. Capture **ARM**. It first runs the same read-only preflight, including the DC1 check, on the live expressions;
   only if it passes does it arm the one controlled failure for the next Body Apply. Expected: **`preflight PASS`** and
   `injector {'armed': True, 'fired': 0, 'bone': 'bip_tail00'}`. **If it prints `preflight FAIL` (the injector shows
   `'armed': False` and a refusal): STOP; do not do step 9.**
9. **Controlled failure.** **Body Presets**: select `Body`, **Apply**. Expected: an error message (CPM's
   failed-and-restored copy, e.g. `Preset could not be applied safely. This preset was not applied.`); note it
   exactly and close it. Capture **ABORT** (removes the hooks; expected: `injector {'armed': False, 'fired': 1}`, the
   undo description unchanged from ARM).
10. Exit SFM **without saving**. Report each message, anything visible (A's head and tail after each step; whether B
    ever changed), and anything unexpected.

## STOP conditions

Exit SFM **without saving** and report; Claude still runs `library Q`, `collect-logs`, `restore`, `check`, `analyze`:
- a capture prints `errors` other than `none`, refuses, or says the hooks are not installed;
- BASE prints `preflight FAIL` (a shared, ambiguous or unreadable graph, a refused binding, a direct-reference (DC1)
  mismatch, an API exception or incomplete enumeration, or a state change across the preflight): stop before any
  Apply; the capture names the cause;
- ARM prints `preflight FAIL` (the injector is then not armed): stop before step 9;
- the playhead is not 0.2083 s at step 1, or anything moves it;
- step 4's Apply is refused or fails (an error message instead of an applied or "couldn't confirm" message): do not
  Undo; capture APPLY, then exit;
- the Edit menu does not name `Apply Body Preset` at steps 5–7: do not choose anything; exit;
- step 9 reports that recovery could not be verified, or applies successfully: capture ABORT, then exit;
- B changes visibly at any step; anything is saved, updated, deleted or moved to Trash; SFM crashes, shows an
  autosave recovery prompt, or hangs for more than a minute.

A "couldn't confirm" message at step 4 (committed-unverified) is not a STOP: continue steps 5–10 exactly as written
(the Undo evidence is still required); the analyzer will report the APPLY gate as failed.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q` | no library difference except the known `character.json` rewrite, if any |
| R2 | `collect-logs` | one CPM log |
| R3 | `restore`, then `check` | library cleanup `files_equal_pre` and `folders_equal_pre` true, then `RESTORED`; `"installation": "published"` |
| R4 | `analyze` | `OT1_VERDICT.md` |

**Verdict** (`tools/ot1_analyze.py`): **CANDIDATE PASS** only when the APPLY, UNDO, ABORT and EVIDENCE gates all
pass; **CANDIDATE FAIL** when the evidence is complete and any gate fails (APPLY PASS with UNDO FAIL is a FAIL);
**INCOMPLETE** when evidence or restoration fails (no candidate decision). The gates are listed in the analyzer's
docstring and in the preparation record, section 5. A PASS qualifies the ordering for review only; production
promotion needs separate adjudication and authorization.
