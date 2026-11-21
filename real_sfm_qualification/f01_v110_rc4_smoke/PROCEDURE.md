# F-01 v1.1.0 RC4 native release smoke (RC4S): operator procedure

**Status:** prepared offline; package pin moved to RC5 before any run. Authorized by "SFM Character Tools v1.1.0 —
README Integration and Final Release Smoke GO" (2026-11-20).

**Authority:** "F-01 Pose Library — v1.1.0 Release Candidate GO" (2026-11-20). Record:
`cpm/qualification/F01_V110_RC4_RELEASE_CANDIDATE.md`.

**What it checks.** One SFM process with the exact RC4 production files (nothing derived; no observer or capture
script in SFM; production registry mode). It covers:
- Fox Full body Save, Apply to a second Fox, Undo and Redo (the structural route);
- the qualified Tails cross-rig transfer: `RC4 Sit` saved from the session's original sitting Tails, applied to a new
  chest-rigged Tails (adapted), applied again (a no-op), and undone once;
- Save New's immediate feedback (the Owner accepts the busy cursor as sufficient) and Pose Info's Rig row, as you
  see them.

The RC4 qualifications are not repeated.

| Item | Value |
|---|---|
| Installed CPM | `b89af5a8e8e86e65352a34803aef84b751c42082aecb58be250149da39e02525` (production mode), from the unsigned RC5 package `baadc4be54e17aead1ddf16474956b9b4cb9ba41fe073f7d4b568bf661fcf6d9` (RC4's production files with the approved v1.1.0 README) |
| Registries | `f445d5ef…`, `a2254930…` (unchanged) |
| Sessions | `RC4_SESSION.dmx`: a verified copy of the R2 fixture `259ea8a6…`, **never saved**. `RC4_SPARE.dmx`: never opened |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_v110_rc4_smoke\tools\rc4s_tool.py <Q>\rc4s.json <command>` |
| Restored afterwards | the published CPM `ccbed9d7…`; both registries removed; the preset library exactly as backed up; every protected inventory equal to its baseline |

**Never:**
- save the session;
- move the playhead or change the shot;
- pose or apply to the original Fox, the original Tails or Krystal (saving the original Tails' pose is allowed);
- use Update, Delete, Rename or Favorite;
- apply any other pose;
- Undo or Redo more than listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `rc4s.template.json` to `<Q>\rc4s.json`; fill every `<...>` path. Change no pin. | |
| P1 | `build`, then `pre`, then `install`, then `check` | `BUILT … production-mode check PASS`; `PRE PASS (RC4S)`; `"installation": "rc4"` |
| P2 | Create `<Q>\owner_review\` and copy `owner_smoke_record.template.md` into it as `OWNER_SMOKE_RECORD.md` | |

## Native sequence (Owner; one SFM process)

1. **Open.** Choose **File > Open** `<Q>\sessions\RC4_SESSION.dmx`. Check: Motion Editor, shot15, playhead **0.2083 s**.
2. **Create three characters.** Choose **Create Animation Set for New Model**:
   - `models/fursonas/foxmccouldwm.mdl` **twice**: **Fox S**, then **Fox D**;
   - `models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl` **once**: **Tails N**.

   Rig all three with **Rig > rig_biped_simple**, then pose:
   - **Fox S:** bend the spine, turn the head, move the hands, lift a foot.
   - **Fox D and Tails N:** move `rig_root` a few hundred units away and turn it; give Fox D a different pose.
3. **Save Fox.** Open **Character Preset Manager**, choose **Refresh Models** and select Fox S. Choose **Poses: Save New**.
   **Note whether Save New gives immediate feedback (a busy cursor is enough).** Keep **Full body**, name it `RC4 Fox`
   and save. Select `RC4 Fox` and open **Pose Info**: **note the Rig row** (expected `rig_biped`). Close it. **[F1]**
4. **Apply Fox.** Select Fox D and `RC4 Fox`, then **Apply Pose**. Expect `Pose applied: RC4 Fox.` Check that Fox D
   takes the posture, stays in place facing the same way, and that nothing else changed. **[F2]**
5. **Undo and Redo Fox.** Choose **Edit > Undo Apply Pose RC4 Fox** once, then **Redo** once. **[F3]**
6. **Save the sitting pose.** Select **milestailsprower1** (the original Tails). Choose **Save New**, **Full body**,
   name it `RC4 Sit`, and save. Open **Pose Info** for it, **note the Rig row**, and close it. **[T1]**
7. **Apply across rigs.** Select **Tails N** and `RC4 Sit`, then **Apply Pose**. Expect
   `Pose applied: RC4 Sit. Adapted to this character's rig.` with no warning. Check that Tails N sits where it
   stands, facing as it was, and that the original Tails, the Foxes and Krystal did not change. **[T2]**
8. **Repeat.** Choose **Apply Pose** `RC4 Sit` again. Expect `Already matches this pose.` and the Edit menu still
   reading **Undo Apply Pose RC4 Sit**. **[T3]**
9. **Undo.** Choose **Edit > Undo Apply Pose RC4 Sit** once: Tails N returns to its own pose. **[T4]**
10. **Exit** SFM **without saving**. Complete `OWNER_SMOKE_RECORD.md`.

**If the Edit menu names something else** (for example a time-selection entry), choose nothing, record it, and
continue.

**STOP** (exit without saving and report) if:
- Save or Apply is refused, or a warning or recovery message appears;
- an Apply writes to the wrong character, moves it or damages it;
- SFM crashes or hangs for more than a minute.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q`, then `collect-logs` | the two poses and CPM's sidecars; one CPM log |
| R2 | `restore`, then `check` | `RESTORED`; `"installation": "published"` |
| R3 | `analyze` | `RC4S_VERDICT.md` (gates EVIDENCE, FOX, TAILS, CROSS, TARGET, DISPLAY, CLEAN) |

The release smoke is accepted only with the automated PASS **and** the Owner's record, reported side by side.
