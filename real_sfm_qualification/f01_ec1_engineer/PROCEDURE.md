# F-01 EC-1: TF2 Engineer control-coverage investigation (operator procedure)

**Status:** run once (`EC1-01`, 2026-11-10). The verdict is **CANDIDATE**, with deviation EC1-D1 accepted. Results:
`cpm/qualification/F01_EC1_RESULTS.md`. Do not repeat this run. The session-file expectations below were corrected
after the run (section "Session files").

**Purpose:** decide, from the Engineer's actual SFM animation set, whether `models/player/engineer.mdl` may become a
candidate for a version 3 Full body Save/Apply native qualification. NQ-03 showed that its header declares no
procedural bone (`cpm/qualification/F01_NQ03_RESULTS.md`). That is a filter, not coverage. This investigation does
**not** infer direct-FK coverage from the header. It observes every binding and answers:

1. Does the animation set expose a direct control for every bone?
2. Are all control types, channel bindings and endpoint indices supported by the version 3 contract (`direct_fk_v1`)?
3. Is any bone uncontrolled, duplicated, indirectly driven or otherwise unsuitable?
4. Is a rig present, or are there unsupported operator dependencies?
5. Does the complete structure satisfy the requirements to become a Full body Save/Apply qualification candidate?

**Nothing is installed.** The published CPM stays in place and is **not opened**. The session is new and disposable,
and it is **never saved**. No pose is saved or applied. No rig is applied. No control, key or model setting is
changed. The only SFM action besides reading is the preparation step that creates the Engineer's animation set in
that unsaved session.

| Item | Value |
|---|---|
| Run folder `<Q>` | e.g. `E:\SFM_U0B_Scratch\f01-ec1-engineer` (holds `ec1.json`, this machine's paths) |
| Model | `models/player/engineer.mdl`, resolved through usermod's search paths to `tf/models/player/engineer.mdl`, SHA-256 `a505bba4…`. These are the bytes NQ-03 read; `pre` refuses on any other file. |
| Expected header | `engineer_header.json` (`5faabf6b…`): the Engineer's 72 header rows from NQ-03 run `NQ03-01` (`ed7762b8…`), checksum `1732717760` |
| Observer | `observer\F01_EC1_Observe.py` (`da71f1b0…`). It composes three natively proven observers, each pinned and verified before use: S0 `4a358cc0…`, the model survey's `F01_MC_Observe.py` `f8d52035…` and NQ-S6's `F01_NQS6_Observe.py` `1ac46682…`. |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_ec1_engineer\tools\ec1_tool.py <Q>\ec1.json pre / status / post / analyze` |

## What is observed and how it is judged

**One read-only observation, `EC1-01`,** is taken inside S0's read-only window. That window is a digest of every key
in the document and of the session state, taken before and after. The observation records:
- **From S0:** every bone and scene element; every control; every channel (binding, `fromIndex`/`toIndex`, mode, log
  and layer types, keys); the operators; and the document-wide writer index.
- **From the model survey's extension:** the control-group tree and the flex controllers.
- **From NQ-S6's extension:** the in-scene model's engine-loaded studio header and the source-less channels.

**The offline analysis (`analyze`) judges the observation by two independent routes, which must agree:**
1. **A census, with no CPM code:** for each bone it checks four things:
   - exactly one position channel and one orientation channel, each referenced by exactly one `DmeTransformControl`
     through its own slot;
   - each channel's source is that control's `valuePosition`/`valueOrientation`, in mode 3, with one layer of the
     right log type;
   - observed endpoint indices are the integer 0;
   - exactly one writer document-wide.

   It also reports:
   - controls that drive several bones;
   - control-less and source-less bones;
   - rig registrations, constraints, and operator types outside the supported set.
2. **CPM's own version 3 engine:** the repository source, in qualification mode, runs on a replay of the observation.
   - **Conversion:** exactly as the scoped fixtures are made (`f01_scoped_fixture.py`), with the observed endpoint
     indices placed on every channel.
   - **Calls:** `prod_scope_inventory`, the Full body compile, Save New with reload, and an Apply to a copy with three
     turned bones.

   The replay is not native evidence.

**Verdict:**
- **CANDIDATE:** every criterion passes. These cover a clean read-only window, the model's identity (model reference,
  header checksum, every header row equal to the NQ-03 pin, no declared procedural bone), the header joining the
  scene's bones, and Questions 1 to 5.
- **NOT-CANDIDATE:** a criterion fails on readable evidence.
- **NO-CONCLUSION:** the observation is not clean, or needed evidence is unreadable.

CANDIDATE means only that the Engineer may enter a version 3 Full body Save/Apply native qualification, which needs
its own authorization and a pinned qualification build. It is **not** a qualification.

## Stop rule

Stop, exit SFM **without saving**, and report if:
- the `EC1` line is not `OK`, `readonly` is not `True`, `problems` is above 0, or `findings` is not exactly 1;
- the observer refuses because the model is not `models/player/engineer.mdl`;
- SFM offers to recover an autosave, applies or offers a rig, or opens any dialog this procedure does not describe;
- SFM hangs or crashes while the model loads;
- anything else happens that this procedure does not describe.

The expected finding is "no rig registration". If the observer refuses on the animation-set name, nothing is written:
repeat with the next label (`EC1-02`) and the name it lists. That is not a stop.

Never move the playhead, change editors, select or edit controls, apply a rig, open a right-click menu on the
animation set, or save.

## Commands (paste into the Script Editor, then click Submit)

- **Setup, once:** `EC_DIR = r"<Q>"; EC_REPO = r"<REPO>"`
- **Observe:** `EC_LABEL = "EC1-01"; EC_ANIMSET = "engineer"; execfile(EC_REPO + r"\real_sfm_qualification\f01_ec1_engineer\observer\F01_EC1_Observe.py")`

## Steps

| # | Who | Action | Expected |
|---|---|---|---|
| 0 | Claude | SFM closed. Copy `ec1.template.json` to `<Q>\ec1.json` and fill the paths. Run `pre`. | `MODEL PASS`, then `PRE PASS` |
| 1 | Owner | Start SFM. **File > New.** Name the session `EC1_SURVEY`. If SFM asks for a folder, choose `<Q>\sessions`. Open the Script Editor and submit the setup line. | An empty session with one shot. SFM writes its empty starter session `<Q>\sessions\ec1_survey.dmx` now (expected; see "Session files"). |
| 2 | Owner | In the Animation Set Editor, click **+** > **Create Animation Set for New Model**. Choose `models/player/engineer.mdl` (TF2). Click nothing else. | One animation set, normally named `engineer` (note its exact name). |
| 3 | Owner | Submit the observe line. | `EC1 EC1-01: OK set=engineer model=models/player/engineer.mdl rigs=[] bones=72 header_bones=72 checksum=1732717760 proctype_nonzero=0 … readonly=True problems=0 findings=1` |
| 4 | Owner | Exit SFM. Choose **No** when asked to save. | |
| 5 | Claude | `post`, then `analyze`. | `SESSION FILES PASS` (only SFM's starter session), `MODEL CHECK PASS`, `POSTFLIGHT PASS`; then `evidence\EC1_ANALYSIS.md` with a verdict |

Return the SFM console text, including the `EC1` line.

## Session files

File > New writes SFM's empty **starter session** into the chosen folder at once, before any model is added. Run 1
showed this: `ec1_survey.dmx`, 3,984 bytes, written at 07:37:21, with no animation set, game model or channel. The
observation followed at 07:39:55. This is SFM behaviour and not a save; the Owner exited without saving.

`post` therefore runs three checks:
1. **`mc_tool`'s post, unchanged:** it records `post.json` as it reports. Its emptiness check prints
   `POST FAIL … the disposable session folder is not empty` whenever the starter session is there. That result is
   kept as a raw fact.
2. **The session-folder classification** (`tools/session_files.py`, written to `evidence/session_files.json`):
   - **Expected:** at most one file, a DMX session holding no `DmeAnimationSet`, `DmeGameModel` or `DmeChannel`.
   - **Unexpected:** a session holding a character, which means the session was saved; an `.autosave` file; or any
     other file.
3. **The model check:** the model still resolves to the pinned bytes.

**`POSTFLIGHT PASS`** requires all of these:
- every `mc_tool` post check passes, except that its emptiness check may fail;
- if the emptiness check fails, the classification passes;
- the model check passes.

The protected inventories, the sessions folder among them, are compared by `mc_tool` exactly as before.

Run 1 predates the classification. Its `post.json` keeps `POST FAIL` on the emptiness check. A read-only replay of the
classification on its folder gives `starter` for `ec1_survey.dmx` and nothing unexpected (EC1-D1).

## Evidence

| File | Content |
|---|---|
| `pre_run\pre.json` | kit pins, the model's hash, the four protected inventories, housekeeping and `.pyc` backups |
| `observations\EC1-01.json` | the observation (the composed observers' pins inside) |
| `evidence\post.json` | restoration: housekeeping put back, inventories equal to their baselines, session folder empty |
| `evidence\model_check.json` | the model still resolves to the pinned bytes |
| `evidence\EC1_ANALYSIS.json`, `.md` | criteria, census, CPM inventory and replay, verdict; CPM source hash and the expected header's hash |

## What it can and cannot establish

- **Can:**
  - every binding of a freshly created, unrigged Engineer animation set at the playhead;
  - whether each bone has exactly one direct-FK control within `direct_fk_v1`, according to both the census and CPM's
    classifier;
  - whether any rig, constraint or unsupported operator is present;
  - whether CPM would offer, compile, save and apply a Full body pose for that structure on a faithful fake scene.
- **Cannot:**
  - native Save or Apply behaviour, Undo, timing or rendering;
  - an animation set that was later rigged, preset or edited;
  - other sessions;
  - whether the engine evaluates any bone procedurally at render time. The header declares none, and no supported
    reader shows the rendered result.

## Offline preparation evidence (2026-11-10)

- **Tests:** `tests\test_ec1.py` passes 13/13 on Python 3.10.6, and its 4 observer tests on SFM's Python 2.7.5. After
  the session-file correction the count is 14/14; the added test covers the classifier and the post rule.
  - **Observer:** read-only composition, with refusals on label, existing file, animation set, model and each
    pinned observer.
  - **Analysis, NOT-CANDIDATE through both routes:** the committed real Heavy structure (MC-01).
  - **Analysis, every criterion passes:** the same skeleton with controls on its two helpers.
  - **Analysis, single-criterion failures:** an index, a rig, a constraint, an unsupported operator and a shared
    control each fail their own criterion.
  - **Analysis, NO-CONCLUSION:** unreadable evidence.
  - **Tool:** the template's pins, and the model identity across the search order.
- **Native Heavy data:** the analysis was also run on the native MC-01 observation (the unrigged Heavy, with the
  Heavy's NQ-S6 header reads added for the run).
  - Verdict: **NOT-CANDIDATE**.
  - Census: 77 direct-FK bones; `hlp_forearm_L/R` are control-less and source-less.
  - CPM: Full body is refused as `carried-unsupported`.
  - Agreement: the census and CPM agree.

  This reproduces the known Heavy result.

## Next

- **If CANDIDATE:** propose the Engineer's version 3 Full body native qualification under separate authorization.
- **If NOT-CANDIDATE:** report the failed criteria. HL2 Barney is considered only after reviewing the Engineer's
  results.
