# F-01 model compatibility survey (operator procedure)

**Purpose:** the read-only structure of three model configurations, analysed offline with CPM's current classifier.
Assessment: `cpm/qualification/F01_MODEL_COMPATIBILITY_ASSESSMENT.md`.

| Item | Value |
|---|---|
| Run folder `<Q>` | `E:\SFM_U0B_Scratch\f01-model-survey` (holds `mc.json`, this machine's paths) |
| Observer | `observer\F01_MC_Observe.py`. It wraps the natively proven S0 observer `4a358cc0…`, verifies its hash before use and never changes it. |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_model_survey\tools\mc_tool.py <Q>\mc.json pre / status / post / probe` |

**Nothing is installed.** The published CPM stays in place and is **not opened**. The session is new and disposable,
and it is **never saved**.

## Preparation changes versus observations

The survey has two kinds of steps:
- **Preparation (P):** SFM's own actions in the disposable session: creating the session, adding a model, applying a
  rig. These change only that unsaved session.
- **Observation (MC-NN):** strictly read-only. Each observation proves it with a digest of every key in the document
  and the session state, taken before and after.

## Stop rule

Stop, exit SFM **without saving**, and report if:
- an observation line is not `OK`;
- `problems` is above 0, or `readonly` is not `True`;
- anything happens that this table does not describe.

Two cases are not stops:
- **The animation set name differs.** The observer then refuses and writes nothing, listing the names it found.
  Repeat the same label with the name it listed.
- **Findings.** These are structural facts, for example "no rig" on MC-01. They are expected; report them.

Never move the playhead, change editors, select or edit controls, or save during the survey.

## Commands (paste into the Script Editor, then click Submit)

- **Setup, once:**
  `MC_DIR = r"E:\SFM_U0B_Scratch\f01-model-survey"; MC_REPO = r"E:\SFM-F01-Pose-Library"`
- **Observe:** set the label and the animation set name; only these two change between observations:
  `MC_LABEL = "MC-01"; MC_ANIMSET = "heavy"; execfile(MC_REPO + r"\real_sfm_qualification\f01_model_survey\observer\F01_MC_Observe.py")`

## Steps

| # | Kind | Action | Expected |
|---|---|---|---|
| 0 | — | SFM closed. The operator (Claude) runs `pre`. | `PRE PASS` |
| 1 | P | Start SFM. **File > New.** Name the session `MC_SURVEY`. If SFM asks for a folder, choose `<Q>\sessions`. Open the Script Editor and submit the setup line. | An empty session with one shot. |
| 2 | P | In the Animation Set Editor, click **+** > **Create Animation Set for New Model**. Choose `models/player/heavy.mdl` (TF2). Click nothing else. | An animation set named `heavy` (note its exact name). |
| 3 | MC-01 | Observe with `MC_LABEL = "MC-01"; MC_ANIMSET = "heavy"`. | `MC MC-01: OK … rigs=[] … problems=0 findings=1` |
| 4 | P | Right-click the `heavy` animation set > **Rig** > **rig_biped_simple**. | The rig handles appear. |
| 5 | MC-02 | Observe with `MC_LABEL = "MC-02"; MC_ANIMSET = "heavy"`. | `MC MC-02: OK … rigs=['…'] … problems=0` |
| 6 | P | **+** > **Create Animation Set for New Model**. Choose `models/lordaardvark/sfm/deadoralive/fantasy/ayane_dazv5.mdl`. Then right-click its animation set > **Rig** > **rig_biped_daz_v5**. | An animation set named `ayane_dazv5`, rigged. |
| 7 | MC-03 | Observe with `MC_LABEL = "MC-03"; MC_ANIMSET = "ayane_dazv5"`. | `MC MC-03: OK … problems=0` |
| 8 | — | Exit SFM. Choose **No** when asked to save. | |
| 9 | — | The operator runs `post`, then `probe`. | `POST PASS`; `Q\evidence\MC_PROBE.json` and `MC_PROBE.md` |

Return the SFM console text, including each `MC` line.
