# F-01 v1.1.0 RC3 native release smoke (RC3S): operator procedure

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** "F-01 v1.1.0 — RC3 Authorization" (prepare RC3 with Fox and Tails enabled; one short normal-install
smoke test). Record: `cpm/qualification/F01_V110_RC3_INTEGRATION.md`.

**What it checks.** One SFM process, using the exact RC3 production files (nothing derived, and no observer or capture
script in SFM):
- Fox Full body Save, Apply to a second Fox, Undo and Redo;
- Tails Full body Save, Apply to a second Tails, Undo and Redo;
- the correct destination, useful visible posture, no obvious deformation and unchanged peers.

The full Fox and Tails qualifications, Abort experiments and skeletal captures are not repeated.

**Production mode** is checked offline first (`build`):
- the installed CPM is the package's own production build;
- the structural adapter is usable in production exactly as in the qualification build;
- RC1's production checks still hold.

| Item | Value |
|---|---|
| Installed CPM | `026a65cd4447233093a3429b60a7adf481d9a92060613bae15ef59bf1076c9ba` (RC3, production mode), from the unsigned RC3 package `5ca540720d9313dcbbe26073a4512631ace8a6f21e6ad9964acc336917254c6a` |
| Registries | `cpm_pose_profiles_v1.json` `f445d5ef…`, `cpm_body_profiles_v1.json` `a2254930…` (unchanged from RC2) |
| Sessions | `RC3_SESSION.dmx`: a verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s), **never saved**. `RC3_SPARE.dmx` is copied by the reused pre and never opened. The R2 fixture itself is only read |
| Peers | the session's original Fox (`foxmccouldwm1`), original Tails (`milestailsprower1`) and Krystal, none touched |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_v110_rc3_smoke\tools\rc3s_tool.py <Q>\rc3s.json <command>` |
| Restored afterwards | the published CPM `ccbed9d7…`; both registries removed; the preset library exactly as backed up; every protected inventory equal to its baseline |

**Never:**
- save the session;
- move the playhead or change the shot;
- touch the original Fox, the original Tails or Krystal;
- pose the seven Tails JIGGLE leaves (`ear3_L/R`, `HairSpike_B3/M3/T3`, `Tail6_L/R`), and leave `ear2_L/R` alone;
- use Update, Delete, Rename or Favorite;
- apply any other pose or preset;
- use the Updater;
- Undo or Redo more than listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `rc3s.template.json` to `<Q>\rc3s.json` (a new run folder); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: the RC3 production CPM … and both registries, unmodified from the package; production-mode check PASS (structural adapter usable in production)` |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (RC3S): … preset library backed up` |
| P3 | `install` (its message says "qualification CPM": the reused tool's name for the run's build, here RC3), then `check` | `"installation": "rc3"` |
| P4 | Create `<Q>\owner_review\`; copy `owner_smoke_record.template.md` into it as `OWNER_SMOKE_RECORD.md` | |

## Native sequence (Owner; one SFM process)

Record each message exactly and what you see in `OWNER_SMOKE_RECORD.md`. Screenshots are welcome.

1. **Open the session.** Start SFM and choose **File > Open** `<Q>\sessions\RC3_SESSION.dmx`. Check: Motion Editor,
   shot15, playhead **0.2083 s** as opened. If not, STOP.
2. **Create four characters.** In the Animation Set Editor, choose **Create Animation Set for New Model**:
   - `models/fursonas/foxmccouldwm.mdl` **twice**: the first is **Fox S**, the second **Fox D**;
   - `models/jcthornton/sonic_the_hedgehog/milestailsprower.mdl` **twice**: the first is **Tails S**, the second
     **Tails D**.

   Note the four names.
3. **Rig all four.** Right-click each new character and choose **Rig > rig_biped_simple**.
4. **Pose them** at 0.2083 s, with rig handles:
   - **Fox S** and **Tails S**: bend the spine, turn the head, move both hands, lift one foot and curl a few
     fingers. On Tails S, also turn `ear_L`, `HairSpike_M1`, `Tail2_L` and `Tail4_R`.
   - **Fox D** and **Tails D**: move `rig_root` a few hundred units away and turn it, then pose it differently with
     a couple of rig handles.
   - Finish all posing now.
5. **Save Fox.** Open **Character Preset Manager**, choose **Refresh Models** and select **Fox S**. Choose
   **Poses: Save New**, keep **Full body**, name it `RC3 Fox` and choose **Save**. Expected: `Pose saved: RC3 Fox.`
   Select `RC3 Fox`, open **Pose Info** (Type `Full body`) and close it. **[F1]**
6. **Apply Fox.** Select **Fox D**, select `RC3 Fox` and choose **Apply Pose**. Expected: `Pose applied: RC3 Fox.`
   **Inspect:**
   - Fox D takes Fox S's body posture;
   - Fox D stays where it was, facing as it was;
   - nothing is badly deformed;
   - Fox S, the original Fox, the Tails and Krystal did not change.

   **[F2]**
7. **Undo and Redo Fox.** The **Edit** menu must read **Undo Apply Pose RC3 Fox**. Choose it once: Fox D returns to its
   own pose. Then choose **Edit > Redo Apply Pose RC3 Fox** once: Fox D is posed again. **[F3]**
8. **Save Tails.** Select **Tails S**, choose **Poses: Save New**, keep **Full body**, name it `RC3 Tails` and choose
   **Save**. Expected: `Pose saved: RC3 Tails.` Select `RC3 Tails`, open **Pose Info** (Type `Full body`) and close
   it. **[T1]**
9. **Apply Tails.** Select **Tails D**, select `RC3 Tails` and choose **Apply Pose**. Expected:
   `Pose applied: RC3 Tails.` **Inspect** as at step 6:
   - the ear, hair and tail **tips** are simulated and may sit a little differently; that is acceptable;
   - Tails S, the original Tails, the Foxes and Krystal did not change.

   **[T2]**
10. **Undo and Redo Tails.** The **Edit** menu must read **Undo Apply Pose RC3 Tails**. Choose it once, then
    **Edit > Redo Apply Pose RC3 Tails** once. **[T3]**
11. **Exit** SFM **without saving**. Complete `OWNER_SMOKE_RECORD.md`.

**If the Edit menu names something else** at step 7 or 10 (for example a time-selection entry), choose nothing.
Record exactly what it names, then continue with the next step. Do not Undo extra entries.

## STOP conditions

Exit SFM **without saving** and report. Claude still runs `library Q`, `collect-logs`, `restore`, `check` and
`analyze`. Stop when:
- Full body is refused for Fox S or Tails S (for example a `rig-driven` message). This is a **release blocker** for
  RC3, and RC2 remains the fallback;
- an Apply is refused or fails, writes to a character other than the selected one, moves the destination, or damages
  existing animation;
- a recovery message appears;
- SFM crashes, shows a recovery prompt or hangs for more than a minute;
- anything is saved, updated, renamed or trashed.

A small difference in a simulated tip or a helper bone, or an adjustment an artist would routinely make, is not a
STOP.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q` | `RC3 Fox`, `RC3 Tails` and their `pose_sources.json` (and CPM's `character.json`, if written) |
| R2 | `collect-logs` | one CPM log |
| R3 | `restore`, then `check` | library cleanup exact, `RESTORED`; `"installation": "published"` (also the v1.0.0 rollback state) |
| R4 | `analyze` | `RC3S_VERDICT.md` |

**Verdict** (`tools/rc3s_analyze.py`, from the CPM's own log and the saved records):
- **AUTOMATED SMOKE PASS:** the EVIDENCE, FOX, TAILS, TARGET, DISPLAY and CLEAN gates all pass;
- **SMOKE FAIL:** the evidence is complete and a functional gate fails;
- **INCOMPLETE:** evidence or restoration fails.

Undo and Redo, posture, deformation and the peers are the Owner's record. The release smoke is accepted only with the
automated PASS **and** the Owner's record accepted, reported side by side.
