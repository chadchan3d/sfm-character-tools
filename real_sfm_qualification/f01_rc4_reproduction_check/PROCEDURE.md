# F-01 RC4: short native check of the revised verification contract (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** "F-01 RC4 — Implement Astra's Revised Verification Contract" (section 5: the short native acceptance
Astra specified). Record: `cpm/qualification/F01_RC4_REVISED_VERIFICATION.md`.

**What it checks.** Direction B of the RC4 run only, in one SFM process on a disposable session copy that is never
saved:
- `RC4 Sit` is saved from the session's original sitting Tails (`milestailsprower1`, 22 controls);
- it is applied to a new chest-rigged Tails (**Tails N**, 23 controls), which must verify under the revised
  reproduction envelope (0.01 units, 0.1°);
- applied again, it must be a successful no-op with no new Undo history;
- one Undo must restore Tails N exactly.

The Fox (`foxmccouldwm1`) is the untouched peer. The full two-direction RC4 qualification is not repeated; its evidence
is preserved and replayed separately (`f01_rc4_cross_rig/tools/rc4x_replay.py`).

| Item | Value |
|---|---|
| Candidate CPM | pinned in `rc4r.template.json` |
| Qualification build | the candidate with only its registry-mode line changed (K2's derivation) |
| Sessions | `RC4R_SESSION.dmx`: a verified copy of the R2 fixture `259ea8a6…`, never saved. `RC4R_SPARE.dmx`: never opened |
| Capture | the RC4 cross-rig kit's `observer/F01_RC4X_Capture.py`, unchanged and pinned |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_rc4_reproduction_check\tools\rc4r_tool.py <Q>\rc4r.json <command>` |

**Never:**
- save the session;
- touch the original Tails (except saving its pose), the Fox or Krystal;
- change the shot or move the playhead from 0.2083 s at a capture;
- apply any other pose;
- Undo or Redo more than listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `rc4r.template.json` to `<Q>\rc4r.json` (a new run folder); fill every `<...>` path. Change no pin. | |
| P1 | `build`, then `pre`, then `install`, then `check` | `BUILT`, `PRE PASS (RC4R)`, `"installation": "qualification"` |

## Lines to submit in SFM's Script Editor

**Setup** (the same for every capture):
```
S1F_DIR = r"<Q>"; S1F_SOURCE = "milestailsprower1"; S1F_TARGET = "<Tails N>"; S1F_PEER = "foxmccouldwm1"
```
**Capture** (only the step name changes):
```
S1F_STEP = "PREP"; execfile(r"<REPO>\real_sfm_qualification\f01_rc4_cross_rig\observer\F01_RC4X_Capture.py")
```

## Native sequence (Owner; one SFM process)

| # | Action | Expected | Capture |
|---|---|---|---|
| 1 | **File > Open** `<Q>\sessions\RC4R_SESSION.dmx`. | Motion Editor, shot15, playhead 0.2083 s | |
| 2 | **Create Animation Set for New Model** `models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl` once; note its name (**Tails N**). **Rig > rig_biped_simple** on it. Move its `rig_root` a few hundred units away and turn it. | Tails N has `rig_chest` | |
| 3 | Open **Character Preset Manager**, **Refresh Models**, select Tails N. Submit the setup line, then capture. | errors none | **PREP** |
| 4 | Select **milestailsprower1**. **Poses: Save New**, **Full body**, name `RC4 Sit`, **Save**. Capture. | `Pose saved: RC4 Sit.` | **SAVED** |
| 5 | Select **Tails N**, select `RC4 Sit`. Capture. | Apply Pose enabled | **B_BASE** |
| 6 | **Apply Pose.** Capture. | `Pose applied: RC4 Sit. Adapted to this character's rig.` (no warning) | **B_APPLY** |
| 7 | **Inspect** (no capture): Tails N takes the sitting posture where it stands, facing as it was; nothing is badly deformed; the original Tails and the Fox did not change. | | |
| 8 | **Apply Pose** `RC4 Sit` again. Capture. | `Already matches this pose.`; no warning; the Edit menu is unchanged | **B_NOOP** |
| 9 | **Edit > Undo Apply Pose RC4 Sit** once. Capture. | Tails N is back to its own pose | **B_UNDO** |
| 10 | Exit SFM **without saving**. Report every message exactly, what you saw at step 7 and anything unexpected. | | |

**STOP** (exit without saving and report) if:
- a capture prints errors;
- Save or Apply is refused;
- a warning or recovery message appears;
- the Edit menu names anything other than the Apply at step 9;
- SFM crashes or hangs.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q`, `collect-logs` | RC4 Sit and its sidecars; the CPM log |
| R2 | `restore`, then `check` | `RESTORED`; `"installation": "published"` |
| R3 | `analyze` | `RC4R_VERDICT.md` (gates EVIDENCE, APPLY, POSTURE, NOOP, UNDO and PEER) |

**Recorded:** CPM's own reproduction maxima, the independent posture maxima (overall and the worst bones) and the
number of neighbouring keys kept.
