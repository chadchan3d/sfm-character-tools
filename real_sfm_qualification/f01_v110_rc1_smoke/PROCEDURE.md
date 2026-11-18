# F-01 v1.1.0 RC1 native release smoke (RC1S): operator procedure

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** "F-01 v1.1.0 RC1 — Native Release Smoke Preparation" (RC1 accepted for native production
verification; commit `902df07`). Record: `cpm/qualification/F01_V110_RC1_SMOKE_PREPARATION.md`.

**What it checks, with the exact RC1 production files (nothing derived, no observer in SFM):** Krystal v2 Full body
Save in one SFM process and Apply, Undo and Redo after a restart; generic v3 Full body on an unrigged Heavy with its
procedural forearm helpers (Save, Apply to a second Heavy, Undo, Redo); Body Preset Apply and Undo; Selected parts
Apply; the Save dialog's Full body and Selected parts choices and Pose Info for Full body and Selected parts records.
Production mode was checked offline first (`build`): it keeps no generic-v3 qualification restriction, and the
disabled `constant_channel_carried_v1` route is not used by either build mode.

| Item | Value |
|---|---|
| Installed CPM | `321835086b2cbed30395de488f6cb258f3f5b49d783be178de8ebe9e16d24c05` (RC1, production mode), from the unsigned RC1 package `5663e088…` |
| Registries | `cpm_pose_profiles_v1.json` `f445d5ef…`, `cpm_body_profiles_v1.json` `a2254930…` (Krystal Full body qualified) |
| Sessions | `RC1_SOURCE.dmx`: verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s); `RC1_DESTINATION.dmx`: verified copy of S3's prepared destination `61df8bcd…` (shot13, 0.3750 s). Neither is ever saved |
| Seeded records | K2's version 2 `K2 Pose` `bf8fc5bc…` (Full body) and version 1 `NQ1 Pose A` `4916a724…` (Left arm) |
| Body preset | Krystal's existing `Body` (`cd31c7f1…`), only read: `bip_head` 1.13 → 1.33, `bip_tail00` 0.8 → 1.0 |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_v110_rc1_smoke\tools\rc1s_tool.py <Q>\rc1s.json <command>` |
| Restored afterwards | the published CPM `ccbed9d7…`; both registries removed; the preset library exactly as backed up; every protected inventory equal to its baseline |

**Never:** save a session; move the playhead or change the shot; apply a rig; move a Heavy bone other than
`bip_pelvis` (rotate only); Update, Delete, Rename or Favorite anything; apply any pose or preset not listed; use the
Updater; Undo or Redo more than listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `rc1s.template.json` to `<Q>\rc1s.json` (a new run folder); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: the RC1 production CPM 32183508… and both registries, unmodified from the package; production-mode equivalence PASS` |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (RC1S): preset library backed up` |
| P3 | `install` (its message says "qualification CPM": the reused tool's name for the run's build, here RC1), then `check` | `"installation": "rc1"` |
| P4 | `seed` | `SEEDED: K2 Pose--ac9d4962a2ae.json, NQ1 Pose A--5273df2209ca.json` |
| P5 | Create `<Q>\owner_review\`; copy `owner_smoke_record.template.md` into it as `OWNER_SMOKE_RECORD.md` | |

## Native sequence (Owner)

Record each message exactly and what you see in `OWNER_SMOKE_RECORD.md` (screenshots welcome).

### Process A (`RC1_SOURCE.dmx`)

1. Start SFM. **File > Open** `<Q>\sessions\RC1_SOURCE.dmx`. **Motion Editor**, **shot15**, playhead **0.2083 s** as
   opened (if not, STOP).
2. Open **Character Preset Manager**, **Refresh Models**, select **`Krystal`**, **Poses**. The list shows `K2 Pose`
   and `NQ1 Pose A`. Select `K2 Pose`, open **Pose Info** (Type `Full body`), close it. Select `NQ1 Pose A`, open
   **Pose Info** (Type `Left arm`), close it. **[D1]**
3. **Body Presets**: select `Body`, **Apply** (expected `Body Preset applied.`; head and tail larger). **Edit** menu:
   **Undo Apply Body Preset** once (head and tail back). **[B1]**
4. **Poses: Save New.** The dialog offers **Full body** and **Selected parts**, with Full body selected. Name it
   `RC1 Krystal`, **Save** (expected `Pose saved: RC1 Krystal.`). **[K1]**
5. Animation Set Editor: **Create Animation Set for New Model** `models/player/heavy.mdl` **twice** (Heavy A, Heavy
   B). Apply no rig. Move them apart by their **rootTransform** only. Pose **A only** with the rotate tool: bend both
   elbows strongly, twist both hands, raise one upper arm, bend the spine, turn the head, bend one knee.
6. In CPM: **Refresh Models**, select **Heavy A**, **Poses: Save New → Full body**, name `RC1 Heavy`, **Save**. Note
   the summary (expected to end "Helper bones that SFM moves automatically follow the pose and may look slightly
   different.") and the result `Pose saved: RC1 Heavy.` **[H1]**
7. Select **Heavy B**, **Apply** `RC1 Heavy`. Note the message. **Inspect:** B takes A's arm and body pose; the
   forearms follow the elbows and hands without severe twisting; A and Krystal unchanged. **[H2]**
8. **Edit** menu: **Undo Apply Pose RC1 Heavy** once (B back to default), then **Redo Apply Pose RC1 Heavy** once
   (B posed again). **[H3]**
9. Exit SFM **without saving**.

### Process B (`RC1_DESTINATION.dmx`)

10. Start SFM. **File > Open** `<Q>\sessions\RC1_DESTINATION.dmx`. **Motion Editor**, **shot13**, playhead
    **0.3750 s** as opened (if not, STOP).
11. CPM: **Refresh Models**, **`Krystal`**, **Poses**. Select `RC1 Krystal`, open **Pose Info** (Type `Full body`,
    Source shot `shot15`), close it. **[D2]**
12. **Apply** `RC1 Krystal`. Note the message. **Inspect:** Krystal takes the Process A pose; face and placement
    unchanged; no damaged limbs. **[K2]**
13. **Edit** menu: **Undo Apply Pose RC1 Krystal** once (the destination pose returns), then **Redo Apply Pose RC1
    Krystal** once. **[K3]**
14. Select `NQ1 Pose A`, **Apply** (left arm only; it may take about 5 seconds, or say `Already matches this pose.`).
    If it applied, **Edit > Undo Apply Pose NQ1 Pose A** once. **[S1]**
15. Exit SFM **without saving**. Complete `OWNER_SMOKE_RECORD.md`.

## STOP conditions

Exit SFM **without saving** and report; Claude still runs `library Q`, `collect-logs`, `restore`, `check`, `analyze`:
- Full body is refused for Krystal (for example a `rig-driven` message) or for the Heavy: a **release blocker**;
- an Apply is refused or fails, writes to a character other than the selected one, or damages existing animation;
- the Edit menu does not name the operation at an Undo or Redo step: choose nothing;
- a recovery message, a crash, a hang of more than a minute, or anything saved, updated, renamed or trashed.

A minor helper-bone difference, or a small adjustment an artist would make, is not a STOP.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q` | the seeded records, `RC1 Krystal`, `RC1 Heavy` and their `pose_sources.json` |
| R2 | `collect-logs` | two CPM logs (Process A, Process B) |
| R3 | `restore`, then `check` | library cleanup exact, `RESTORED`; `"installation": "published"` (this is also the v1.0.0 rollback state) |
| R4 | `analyze` | `RC1S_VERDICT.md` |

**Verdict** (`tools/rc1s_analyze.py`, from the CPM's own logs and the saved records): **AUTOMATED SMOKE PASS** when the
EVIDENCE, BODY, KRYSTAL, HEAVY, SELECTED, DISPLAY and CLEAN gates all pass; **SMOKE FAIL** when the evidence is
complete and a functional gate fails; **INCOMPLETE** when evidence or restoration fails. Undo and Redo, and how the
poses look, are the Owner's record. The release smoke is accepted only with the automated PASS **and** the Owner's
record accepted; they are reported side by side.
