# F-01 EC-1: TF2 Engineer control coverage, native results (2026-11-10)

**Verdict: CANDIDATE.** The Owner accepted it on 2026-11-10 ("F-01 — EC-1 Closure and Engineer Full Body Qualification
Preparation"), with deviation EC1-D1 documented.

The TF2 Engineer (`models/player/engineer.mdl`) may enter a separately authorized generic version 3 Full body native
qualification. **Candidate status is not a native Full body qualification.**
- No pose was saved or applied natively.
- The Full body evidence below comes from CPM's engine replaying the observed structure on a fake scene.
- Native Save, Apply, Undo, persistence and rendering are not established.

**Authorization:** "F-01 — EC-1 Engineer Native Investigation Authorization". The Owner operated SFM. Claude handled
preparation, postflight and analysis.
- Kit: `real_sfm_qualification/f01_ec1_engineer/` at `7c29e0c`. The committed files are byte-identical to the tested
  files.
- Nothing was installed: the published CPM `ccbed9d7…` stayed in place and was not opened.
- No rig, control, constraint or animation was added; only one Engineer animation set was created, in a new session.
- The session was not saved.

## 1. Run

| Item | Value |
|---|---|
| Model | `models/player/engineer.mdl` → `tf/models/player/engineer.mdl`, SHA-256 `a505bba46574f265a8df60abc7bb6c0370535c99b3f7988e571d010010a8508c` (the NQ-03 bytes; checked before and after the run) |
| Expected header | `engineer_header.json` `5faabf6b…` (72 rows from NQ-03 run `NQ03-01` `ed7762b8…`) |
| Observer | `F01_EC1_Observe.py` `da71f1b0…`, composing S0 `4a358cc0…`, model survey `f8d52035…` and NQ-S6 `1ac46682…` (pins recorded in the observation) |
| CPM source of the offline replay | `7548d1eb25a7479c9b3c0fffa2186d187ef3763b123412ca5ae6ef2cf6899a45`, qualification mode |
| Console line | `EC1 EC1-01: OK set=engineer1 model=models/player/engineer.mdl rigs=[] bones=72 header_bones=72 checksum=1732717760 proctype_nonzero=0 controls=114 channels=187 operators=0 groups=20 source_less=0 readonly=True problems=0 findings=1` |

## 2. Results

| Requirement | Result |
|---|---|
| The 72-bone header matches NQ-03 | PASS. Checksum 1732717760; all 72 rows equal (name, parent, flags, proctype, procindex, physicsbone); no declared procedural bone; header joins the scene bones by index, name and parent. |
| Every bone has a uniquely attributable, supported direct-FK control | PASS: 72/72 by the census. Each bone has one position and one orientation channel, each referenced by exactly one `DmeTransformControl` in its own slot and sourced from that control's `valuePosition`/`valueOrientation`. Mode 3, one layer of the right log type, one writer document-wide. No bone is control-less or source-less, and no control drives two bones. |
| Channel endpoints and indices meet the v3 contract | PASS. All 187 channels' `fromIndex`/`toIndex` were read natively and are the integer 0 (374 placed on the replay). |
| No unsupported rig or operator dependency | PASS. No rig registration, no constraint and no operator in the animation set, the shot or the document. |
| The independent census and CPM's offline v3 replay agree | PASS. CPM classifies 72/72 direct-FK with root `bip_pelvis`. Full body is `available`, with nothing highlighted or left for review. The compile poses 72/72 with nothing excluded. Save New and reload round-trip as `full_body`. An Apply to a copy with three turned bones (`bip_collar_L_o`, `bip_collar_R_o`, `bip_foot_L_o`) ends `committed-verified`, with the bones restored. |
| No unexpected installation change | PASS. The installation was restored (section 3). |

**Structure (from the observation):**
- **Controls (114):**
  - 72 are bone controls;
  - 1 is model placement (`rootTransform`, not a bone);
  - 41 are flex sliders writing `DmeGlobalFlexControllerOperator.flexWeight`.
- **Control groups:** Face (Expressions, Upper Face, Lower Face), Clothing, Body, Arms, Legs, Toes, Attachments and
  Other.
- **Not present:** the eye-convergence expression operator the Heavy has.

`findings=1` is S0's "expected one rig registration for the animation set, found 0" note. That is expected for an
unrigged model. On its own it is neither a success nor a failure; the complete analysis decides.

## 3. Restoration and the sessions

**`post` (`mc_tool`, unchanged; `post.json` `95e9e7d0…`):**
- **The four protected inventories are equal to their pre-run baselines:**
  - scripts: 1107 files, `39aa9b24…`
  - `usermod/cfg`: 59 files, `f9bb1028…`
  - preset library: 107 files, `a8bc5a1e…`
  - sessions: 990 files, `b2089b81…`
- **Housekeeping put back:** `cfg/config.cfg`, `demoheader.tmp`, `tf2_playerstats.dmx`.
- **Published CPM:** in place with no registry; kit pins unchanged.

**The original result is preserved: `POST FAIL` on one check**, "the disposable session folder is not empty (was the
session saved?): ['ec1_survey.dmx']".

**`MODEL CHECK PASS`** (`model_check.json` `43f32a9e…`).

**EC1-D1 (accepted, procedural deviation):** SFM wrote its empty starter session when File > New created the session
in `<Q>\sessions`.
- **The file:** `ec1_survey.dmx`, 3,984 bytes, SHA-256 `86af982d…`, written at 07:37:21. That was before the
  Engineer was added and before the observation (07:39:55).
- **Its content:** DMX `sfm_session` with no `DmeAnimationSet`, no `DmeGameModel`, no `DmeChannel` and no "engineer".
  The observation's document is this file.
- **The protected sessions inventory is unchanged.** The file was kept in place as evidence.
- **The procedure assumed** that File > New writes nothing. It is corrected (`PROCEDURE.md` "Session files"). Future
  posts classify the folder (`tools/session_files.py`): a starter session is expected, while a session holding a
  character, an autosave or another file is not.
- **A read-only replay** of the classification on this run's folder gives `starter` and nothing unexpected.

**EC1-D2 (accepted):**
- The first observe attempt refused, because the animation set was named `engineer1`, and wrote nothing.
- The retry reused label `EC1-01` with `EC_ANIMSET = "engineer1"` and passed.
- The observer refuses an existing label, so the reuse was valid.

Both deviations are recorded in `evidence/DEVIATIONS.json` (`61821e3e…`).

## 4. Evidence identities (run folder, not committed)

| File | SHA-256 |
|---|---|
| `pre_run/pre.json` | `7d1a6d23b13046b8f34dc8e46794de3c79bddbf003a4c3ee103991ec0ba21941` |
| `observations/EC1-01.json` | `6a04c2ea1a4b6744322fbacefe447866d39d97a48310c5879bb2629ed12a81a1` |
| `evidence/post.json` | `95e9e7d0cfeb3942736708ed48629bd22e7e5a073ef307ccae5e8de9a473c7c2` |
| `evidence/model_check.json` | `43f32a9ef0d2aae2c95c167d9ac6377dff892ac980fe13f31c1475710522c31e` |
| `evidence/EC1_ANALYSIS.json` | `7daedd89e7113662ff1ec6a95af2f8611c48c518c14cbc259dd962cfd35e4912` |
| `evidence/EC1_ANALYSIS.md` | `57bf4045a74fce36a20dc026365511dc930205fa1ce04b4a1d3fe0eeb0dced62` |
| `evidence/DEVIATIONS.json` | `61821e3e29940747bce4bc167ddf54f30ba90efa923027a0888686715d80f508` |
| `sessions/ec1_survey.dmx` (starter) | `86af982dab3adbff1a7e319685f42f6921c0b4aaa25b0decbdd5c79b21fc9ff8` |

## 5. Limits

The result covers one freshly created, unrigged animation set at frame 0, in one session, on one machine. The replay
runs CPM against a fake scene. A rigged, preset or edited Engineer animation set is not covered. Rendering and native
behaviour are not covered.

## 6. Next

The Owner authorized offline preparation of the Engineer's generic version 3 Full body native qualification on
2026-11-10. Running it needs separate authorization.
