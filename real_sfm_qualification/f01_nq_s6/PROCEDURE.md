# F-01 SFP-1 NQ-S6: procedural-state observation (operator procedure)

**Purpose:** read, through SFM's own shipped interfaces, whether the TF2 Heavy's control-less forearm helpers
(`hlp_forearm_L/R`) are declared procedural by the engine-loaded model, and record the evaluation evidence that
`constant_channel_carried_v1` (R3 3.1) needs. Ayane's jiggle bones are the contrast case. Assessment:
`cpm/qualification/F01_SFP1_NQ_S6_INVESTIGATION.md`.

| Item | Value |
|---|---|
| Run folder `<Q>` | `E:\SFM_U0B_Scratch\f01-nq-s6` (holds `nq.json`, this machine's paths) |
| Session | a verified **copy** of the preserved survey session (`f01-model-survey\sessions\saved_by_operator\mc_survey.dmx`, `47f6b9a0…`) at `<Q>\session_copy\NQ_SURVEY.dmx`. The original is never opened. |
| Observer | `observer\F01_NQS6_Observe.py` (`1ac46682…`). It wraps the natively proven S0 observer `4a358cc0…` inside S0's read-only window, as the model survey observer did. |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_nq_s6\tools\nq_tool.py <Q>\nq.json pre / copy / status / post / analyze` |

**Nothing is installed.** The published CPM stays in place and is **not opened**. No pose is saved or applied, no
model flag (including Procedural Bones) is changed, no key is authored, and the session copy is **never saved**.

## Stop rule

Stop, exit SFM **without saving**, and report if an `NQ` line is not `OK`, `problems` is above 0, `readonly` is not
`True`, SFM offers to recover an autosave, or anything happens that this table does not describe. Findings (for
example the rig registrations) are not stops. If the observer refuses on the animation-set name, repeat the same label
with the name it lists.

Never move the playhead, change editors, select or edit controls, open a right-click menu on a model, or save.

## Commands (paste into the Script Editor, then click Submit)

- **Setup, once:** `NQ_DIR = r"E:\SFM_U0B_Scratch\f01-nq-s6"; NQ_REPO = r"E:\SFM-F01-Pose-Library"`
- **Observe:** `NQ_LABEL = "NQ-01"; NQ_ANIMSET = "heavy1"; execfile(NQ_REPO + r"\real_sfm_qualification\f01_nq_s6\observer\F01_NQS6_Observe.py")`

## Steps

| # | Who | Action | Expected |
|---|---|---|---|
| 0 | Claude | SFM closed: `pre`, then `copy`. | `PRE PASS`, `COPY PASS` |
| 1 | Owner | Start SFM. **File > Open** `<Q>\session_copy\NQ_SURVEY.dmx`. Open the Script Editor; submit the setup line. | The survey shot with `heavy1` and `ayane_dazv51`. |
| 2 | Owner | Observe `NQ_LABEL = "NQ-01"; NQ_ANIMSET = "heavy1"`. | `NQ NQ-01: OK … header_bones=79 … readonly=True problems=0` |
| 3 | Owner | Observe `NQ_LABEL = "NQ-02"; NQ_ANIMSET = "ayane_dazv51"`. | `NQ NQ-02: OK … readonly=True problems=0` |
| 4 | Owner | Exit SFM. Choose **No** when asked to save. | |
| 5 | Claude | `post`, then `analyze`. | `POST PASS`, `SESSION CHECK PASS`, `evidence\NQ_S6_ANALYSIS.md` |

Return the SFM console text, including both `NQ` lines.

## What the observation can and cannot establish

- **Can:** each bone's engine declaration (`proctype`, `procindex`, procedural/physics/screen-align flags), the
  model-wide `ShouldEvaluateProceduralBones()` value, whether header indices and names join the scene's bones, the
  helpers' log defaults (`HasDefaultValue` versus `usedefaultvalue`), and evaluation samples inside and outside the
  key range.
- **Cannot:** the engine's rendered (procedural) result for a bone — no supported Python reader exposes it for an
  in-scene game model — or a log extrapolation *contract* (the DME log API has no extrapolation mode; samples are
  corroboration only).
