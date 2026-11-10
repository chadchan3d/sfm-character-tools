# F-01 NQ-03: stock-model header inventory (operator procedure)

**Status:** run once (`NQ03-01`, 2026-11-09; PASS). Results: `cpm/qualification/F01_NQ03_RESULTS.md`. The step order
was corrected after that run (section "Order").

**Purpose:** find a stock character model whose engine-loaded studio header declares **no** procedural bone. That is
the first condition for a generic version 3 Full body qualification under R3 as written
(`cpm/qualification/F01_SFP1_QUATINTERP_FEASIBILITY.md` section 5). The Heavy is the known control: it has two
QUATINTERP helpers (NQ-S6). A clean header is necessary, not sufficient. The chosen model's animation set must still
give every bone a control and have no rig. That is confirmed later, in its own qualification.

**What it reads, and how:** for each of the 24 models in `candidates.json` (the 23 stock characters plus the Heavy as
the control), SFM's own model cache is used exactly as Valve's shipped `modelpipeline` uses it: `FindMDL` →
`IsErrorModel` → `GetStudioHdr` → per bone `pszName`, `parent`, `flags`, `proctype`, `procindex`, `physicsbone`, and the
bones of the local attachments and the bone flex drivers → `Release`. No scene element is created or changed. The
models load into the engine's cache in process memory only.

**Nothing is installed.** The published CPM stays in place and is **not opened**. No pose is saved or applied, and no
session is saved. The reads run inside the read-only window of the pinned S0 observer. That window is anchored on
`heavy1` in a verified copy of the preserved survey session, as in NQ-S6.

| Item | Value |
|---|---|
| Run folder `<Q>` | e.g. `E:\SFM_U0B_Scratch\f01-nq03` (holds `nq03.json`, this machine's paths) |
| Session | a verified **copy** of the preserved survey session (`<Q_SURVEY>\sessions\saved_by_operator\mc_survey.dmx`, `47f6b9a0…`) at `<Q>\session_copy\NQ_SURVEY.dmx`; the original is never opened |
| Observer | `observer\F01_NQ03_Inventory.py` (`745f6dc9…`), wrapping the S0 observer `4a358cc0…` |
| Candidate list | `candidates.json` (`9f77ba71…`) |
| Model files | the 24 candidates resolved through usermod's search paths (first loose file wins), listed in the template; `pre`/`post` pin their bytes, and `resolve` (after `post`) re-derives them |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_nq03\tools\nq03_tool.py <Q>\nq03.json pre / copy / status / post / resolve / analyze` |

## Stop rule

Stop, exit SFM **without saving**, and report if:
- the `NQ03` line is not `OK`, `problems` is above 0, or `readonly` is not `True`;
- SFM offers to recover an autosave;
- SFM hangs or crashes while models load;
- anything else happens that this procedure does not describe.

A model that is not found, an error model, or an unreadable row is a **finding** (recorded, never inferred), not a stop.
If the observer refuses on the animation-set name, repeat with the next label and the name it lists.

Never move the playhead, change editors, select or edit controls, or save.

## Steps

| # | Who | Action | Expected |
|---|---|---|---|
| 0 | Claude | SFM closed. Copy the template to `<Q>\nq03.json`; fill the paths. `pre`, then `copy`. | `PRE PASS`, `COPY PASS` |
| 1 | Owner | Start SFM. **File > Open** `<Q>\session_copy\NQ_SURVEY.dmx`. Open the Script Editor; submit `NQ_DIR = r"<Q>"; NQ_REPO = r"<REPO>"`. | The survey shot with `heavy1`. |
| 2 | Owner | Submit `NQ_LABEL = "NQ03-01"; NQ_ANIMSET = "heavy1"; execfile(NQ_REPO + r"\real_sfm_qualification\f01_nq03\observer\F01_NQ03_Inventory.py")`. Loading 24 models may take a minute or two. | `NQ03 NQ03-01: OK models=24 read=… not_read=… no_procedural_declaration=… readonly=True problems=0` |
| 3 | Owner | Exit SFM. Choose **No** when asked to save. | |
| 4 | Claude | `post`, then `resolve`, then `analyze`. | `POST PASS`, `SESSION CHECK PASS`, `RESOLVE PASS` (each resolved file's SHA-256 equal to its `pre` pin), `evidence\NQ03_ANALYSIS.md` |

Return the SFM console text, including the `NQ03` line.

## Order

The order is **pre, copy, native observation, post, resolve, analyze**.

`resolve` writes `<Q>\evidence\resolution.json`, but `pre` and `status` refuse while `evidence` holds anything: it must
stay empty until postflight. Run 1 listed `resolve` first, so `pre` refused and changed nothing. The just-written
`resolution.json` and the empty `evidence` folder were then removed, and `resolve` ran after `post`.

The order does not affect the files' identity:
- `pre` and `post` pin the bytes of every file in the configuration's `models` list.
- `resolve` refuses unless that list is exactly the search-path resolution.
- `resolve` records each file's SHA-256, which must equal its `pre` pin.

Only the order changed. No kit file, pin or evidence format did.

## What the inventory can and cannot establish

- **Can:** each model's engine declaration per bone, whether the header joins (names, count), and which models declare
  no procedural bone (`candidate`), with the declared bones and their procedure types for the others.
- **Cannot:** how a model evaluates; whether its animation set gives every bone a control or creates a rig; rendered
  behaviour. A `candidate` is a model to qualify next, not a qualified model.

## Next, if a candidate exists

A header with no procedural declaration is a candidate filter, not a generic Full body qualification.

Choose one candidate, preferring a humanoid with a conventional skeleton. After run 1 this is the TF2 Engineer
(`cpm/qualification/F01_NQ03_RESULTS.md` section 9). Then run, under separate authorization:
1. a short read-only check that its animation set gives every bone a direct-FK control with no rig, using the existing
   S0/survey observers on a session with the model added;
2. its version 3 Full body native qualification with a pinned qualification build. The revised UI is inspected during
   normal operation; there is no separate UI test.
