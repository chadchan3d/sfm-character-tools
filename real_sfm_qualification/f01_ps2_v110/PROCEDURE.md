# F-01 PS-2: v1.1.0 production candidate smoke, rollback to v1.0.0 (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
execution approval ("F-01 — Authorize Offline v1.1.0 Production Candidate Preparation" authorizes preparation only).

**What it is:** one bounded native smoke of the **production** CPM candidate, installed in the actual package layout,
followed by a rollback to the exact v1.0.0 installation and a native check that v1.0.0 still works with the run's Poses
folders present. It reuses the native transaction evidence of EF-1 (Engineer Full body: Abort, Undo/Redo, no-op, Clip
Editor refusal, key preservation) and SFP-1 NQ1 (Krystal Selected parts) and does **not** repeat those campaigns.

| Item | Value |
|---|---|
| Candidate CPM | `84cd996c914f82bcc41414413958a5a9b536fca088081d862559f48a69144568` (production mode; `direct_fk_v1` revision 1 qualified; carried-channel rule disabled; the qualification fault hook inert) |
| Pose Library registries | `cpm_pose_profiles_v1.json` `f445d5ef…` (left arm qualified, right arm experimental), `cpm_body_profiles_v1.json` `22dcd159…` (Krystal v2 Full body **experimental**: not promoted, see `cpm/qualification/F01_V110_PRODUCTION_CANDIDATE.md`) |
| Release spec | `release/v1.1.0-candidate/SOFTWARE_SPEC.json` (33 files: the 31 of v1.0.0, the new CPM identity, two registries) |
| Package | built by `ps2_tool package` from the published v1.0.0 ZIP `5323b143…`: v1.0.0's exact bytes, the candidate CPM, both registries, the **unsigned** v1.1.0 candidate inventory; the v1.0.0 signature is left out |
| Restored afterwards | v1.0.0: CPM `ccbed9d7…`, inventory `ad058c15…` and signature `344b9fb8…`; no registries |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_ps2_v110\tools\ps2_tool.py <Q>\ps2.json <command>` |
| State capture | `observer\F01_PS2_State.py` (read-only; writes `<Q>\observations\<step>.json` once per step) |

**Never:** save any session, open the Updater or **Update Animation Groups Master**, use Delete or Rename, or touch
any preset other than the ones named. The Updater would refuse the unsigned candidate inventory by design.

**Amendment 1 (2026-11-13, Owner):** adds the Selected parts UI acceptance (step 17a–e, 19) and the duplicate-model
Body preset check (21a–d) inside Process 3; the four-process structure is unchanged. Distribution order (Owner):
manual ZIP (SFMLab, website, GitHub) first, then an update of the existing Workshop installer; Workshop readiness is
not a prerequisite of this qualification. Krystal v2 Full body stays experimental.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `ps2.template.json` to `<Q>\ps2.json`; fill every `<...>` path. Change no pin. | |
| P1 | `package` | `PACKAGED: 1007 entries (1003 from v1.0.0, 4 candidate); ZIP … ; inventory <candidate_inventory_sha256> (UNSIGNED)` |
| P2 | `pre` | `PRE PASS` (v1.0.0 verified file by file against the published ZIP; the whole preset library backed up; no Poses folder exists) |
| P3 | `install`, then `check` | `INSTALLED`; `"installation": "candidate"`, both registries present, `"signature_present": false` |
| P4 | `seed` | `SEEDED: NQ1 Pose B--f8fe642ca9ff.json (version 1, left arm)` |

## Native smoke (Owner)

Setup line, submitted once in each SFM process after CPM is open:
```
PS2_DIR = r"<Q>"; PS2_REPO = r"<REPO>"
```
Capture command (replace the step):
```
PS2_STEP = "S-PROD"; execfile(PS2_REPO + r"\real_sfm_qualification\f01_ps2_v110\observer\F01_PS2_State.py")
```
Each capture prints `PS2 <step>: CPM … | written`. Note every status message exactly as shown.

### Process 1: Engineer Save New (candidate)

1. Start SFM. **File > Open** `<Q>\sessions\PS2_ENGINEER_SOURCE.dmx`. **Motion Editor**, playhead frame **0**. Open
   **Scripts > SFM Character Tools > Character Preset Manager**, **Refresh Models**, select `engineer1`, **Poses**.
   Submit the setup line, then capture **S-PROD**. Expected: `… mode 'production' version u'1.1.0' …`.
2. **Help**: note the footer's version text. Expected: `Version: 1.1.0`. Close Help.
3. **Save New**. Expected: the dialog opens with **Full body** selected and the summary
   `Includes hip movement. Facial expressions and the character's rootTransform are not saved.` Name it
   `PS2 Engineer Body`, **Save**. Expected: `Pose saved: PS2 Engineer Body.`
4. Select `PS2 Engineer Body`, open **Pose Info** and close it, then capture **S-E-INFO**. Expected: `v3 'full_body'
   (72 parts)`.
5. Exit SFM **without saving**.

### Process 2: Engineer Apply, Soldier, Heavy (candidate)

6. Start SFM. **File > Open** `<Q>\sessions\PS2_ENGINEER_DESTINATION.dmx`. Motion Editor, frame 0. Open CPM, Refresh
   Models, `engineer1`, **Poses**. Submit the setup line.
7. Select `PS2 Engineer Body`, **Apply Pose**. Expected: `Pose applied: PS2 Engineer Body.` The Engineer may move a
   long way: his hips take the saved movement, his rootTransform stays (F01-DI-01; not a STOP). Capture
   **S-E-APPLY** (undo `Apply Pose PS2 Engineer Body`).
8. Click the viewport, **Ctrl+Z** until **Edit > Redo** names `Apply Pose PS2 Engineer Body` (SFM's own
   `Change Recording State` entries are undone first if any; never undo past the Apply). Capture **S-E-UNDO**.
9. **Ctrl+Y** once. Capture **S-E-REDO** (undo `Apply Pose PS2 Engineer Body`).
10. **Soldier** (previously unqualified, header-clean): in the Animation Set Editor, **Create Animation Set for New
    Model** `models/player/soldier.mdl`. In CPM, **Refresh Models**, select the Soldier, **Poses**. In the Motion
    Editor at frame 0, rotate three Soldier bones visibly (for example the spine, the left upper arm, the head).
11. **Save New**. If the summary is the Full body summary of step 3 and Save is enabled: name it `PS2 Soldier Body`,
    **Save** (expected `Pose saved: PS2 Soldier Body.`), select it, capture **S-SOLDIER-SAVED**. If the dialog shows
    a refusal instead: note the message verbatim, **Cancel**, capture **S-SOLDIER-SAVED** anyway, and skip to
    step 14 (a refusal that writes nothing is a FINDING, not a STOP).
12. Rotate the Soldier's left upper arm again visibly. **Apply Pose** `PS2 Soldier Body`. Expected: `Pose applied: PS2
    Soldier Body.`, the arm back where it was saved. Capture **S-SOLDIER-APPLY**.
13. **Ctrl+Z** until **Edit > Redo** names `Apply Pose PS2 Soldier Body`. Capture **S-SOLDIER-UNDO**.
14. **Heavy** (declared procedural helpers): **Create Animation Set for New Model** `models/player/heavy.mdl`. In CPM,
    **Refresh Models**, select the Heavy, **Poses**, **Save New**. Expected: **Full body** shows
    `Some bones of this character have no controls, and CPM can't confirm they stay fixed. Choose Selected parts to
    save a smaller pose.` and Save is disabled. Note the message, **Cancel**. Capture **S-HEAVY**.
15. Exit SFM **without saving**.

### Process 3: Krystal (candidate)

16. Start SFM. **File > Open** `<Q>\sessions\PS2_KRYSTAL.dmx`. Motion Editor; go to **shot15** at the frame used by
    PS-1 (t_doc 2083). Open CPM, Refresh Models, `Krystal`, **Poses** (`NQ1 Pose B` listed). Submit the setup line.
17. **Save New**. Expected: **Full body** shows `Full body can't be saved: parts of this character's body are driven
    by its rig. Choose Selected parts to save a smaller pose.` (the version 2 route stays unavailable in production).
    Note it. Screenshot **SP-1** (the dialog with that Full body message).

    **Selected parts UI acceptance (the Owner's judgement, recorded; not inferred from automated tests).** In the same
    dialog, before saving:
    - a. Choose **Selected parts**. Note how the grouped bone picker presents the groups (labels, nesting, unavailable
      groups) and the **visible list size** (how many rows show without scrolling; whether the dialog size is
      workable). Screenshot **SP-2**.
    - b. **Scroll** the picker to the bottom and back. Note whether scrolling is smooth and nothing is cut off.
      Screenshot **SP-3** (scrolled).
    - c. **Select and deselect**: tick a whole group, untick it, tick two single bones, untick one; note whether group
      tri-state, single ticks and the **scope summary** line follow correctly. Note the summary texts exactly.
    - d. End with the left fingers group ticked. Screenshot **SP-4** (picker with the selection and its summary).
    - e. Name it `PS2 Krystal grip`, **Save**. Expected: `Pose saved: PS2 Krystal grip.` Select it, open **Pose
      Info**; note the rows exactly; screenshot **SP-5**; close it. Capture **S-K-GRIP**.
18. Rotate one left index finger bone visibly. **Apply Pose** `PS2 Krystal grip`. Expected: `Pose applied: PS2
    Krystal grip.` Screenshot **SP-6** (after the Apply). Capture **S-K-GRIP-APPLY**.
19. **Ctrl+Z** until **Edit > Redo** names `Apply Pose PS2 Krystal grip`. Capture **S-K-UNDO**. **Ctrl+Y** once.
    Capture **S-K-REDO**. Then give your **Selected parts UI verdict**: `ACCEPTED`, `ACCEPTED WITH NOTES` or `NOT
    ACCEPTED`, with one observation each for: the Save dialog, the picker groups, the list size, scrolling, select
    and deselect, the scope summary, Pose Info, and the Apply workflow. A `NOT ACCEPTED` UI is not a STOP: continue.
20. Select `NQ1 Pose B` (version 1, left arm), **Apply Pose**. Expected: `Pose applied: NQ1 Pose B (Left arm).`
    Capture **S-K-LEGACY**.
21. **Body Presets**: select `Body`, **Apply**. Expected: applied, no error. **Expressions**: select `Happy`,
    **Apply**. Expected: applied. Open **Help**, note the version text, close it. Capture **S-K-PRESETS**.

    **Duplicate-model Body preset check** (two instances of the same model; prompted by a user report, not a confirmed
    diagnosis). Stay in shot15, Motion Editor:
    - 21a. In the Animation Set Editor, **Create Animation Set for New Model**
      `models/fursonas/starfox/krystal/bodies/krystal2020.mdl` (the same model as `Krystal`). Note the new animation
      set's name (instance **B**; the original `Krystal` is instance **A**). In CPM, **Refresh Models**: note how the
      two instances are listed. Select **A** (`Krystal`). Capture **S-K-DUP-BEFORE** (expected: `… | N animation
      sets | written`, never `UNREADABLE`).
    - 21b. Select **B** in CPM. In the Animation Set Editor change one of **B**'s body sliders visibly (a body shape
      slider, not the face). **Body Presets > Save New**, name it `PS2 Dup Body`. Expected: `Body Preset saved.` and
      only B changed on screen. Capture **S-K-DUP-SAVED**.
    - 21c. Select **A** (`Krystal`) in CPM, **Body Presets**, select `PS2 Dup Body`, **Apply**. Expected: A takes B's
      body shape; **B does not change**. Either it applies, or CPM refuses with a message and nothing changes on
      either instance (note the message exactly). Capture **S-K-DUP-APPLY**. Screenshot **DUP-1** (both instances).
    - 21d. If it applied: click the viewport, **Ctrl+Z** until A's body returns (note each Edit > Undo name). B must
      not change. Capture **S-K-DUP-UNDO**. If it was refused: capture **S-K-DUP-UNDO** without pressing anything.
22. Exit SFM **without saving**. (Logs are collected once, after Process 4.)

### Rollback and the v1.0.0 check

23. Claude: `library K`, then `rollback`. Expected: `ROLLED BACK to v1.0.0; the run's Poses folders are kept`,
    `library_untouched: true`, `inventory_problems: []`.
24. Owner, **Process 4 (v1.0.0)**: start SFM, **File > Open** `<Q>\sessions\PS2_V100_KRYSTAL.dmx`. Open CPM (v1.0.0
    has no Poses tab). Refresh Models, `Krystal`. **Body Presets**: apply `Body`; **Expressions**: apply `Happy`.
    Expected: both apply without error, nothing about the Poses folders. Submit the setup line and capture
    **S-V100**. Exit SFM **without saving**.
25. Claude: `library V100`, `collect-logs`, `cleanup` (expected `RESTORED`), `check` (`"installation": "v1.0.0"`),
    then transcribe the Owner's report into `<Q>\evidence\OPERATOR_REPORT.json` (keys of `operator_expect`, the
    texts exactly as reported, `clean_closes`, and `selected_parts_ui`: `{verdict, observations: {save_dialog,
    picker_groups, list_size, scrolling, select_deselect, scope_summary, pose_info, apply_workflow}, notes}`), copy
    the Owner's screenshots into `<Q>\screenshots\` (`SP-1.png` … `SP-6.png`, `DUP-1.png`), then `compare`.

**Screenshots:** save them anywhere outside the SFM and library folders (for example the Desktop) with the names
above; Claude copies them into the run folder. They are evidence only.

**Verdicts:** the functional verdict (PASS, PASS WITH FINDINGS, FAIL) and the **Selected parts UI acceptance** are
reported separately. The UI acceptance is exactly the Owner's verdict; an incomplete report (a missing verdict,
observation or fewer than five SP screenshots) is NOT ACCEPTED. The duplicate-model check passes when the save is
attributed to B, the Apply to A, A changes, B's state digest is unchanged and Undo restores A; a refusal that changes
neither instance is a FINDING; any change to B, or any change after a refusal, FAILS.

## STOP conditions

Exit SFM **without saving**, report, and let Claude run `rollback` then `cleanup` (always):
- a capture prints anything other than `production` and `1.1.0` in Processes 1–3, or a capture refuses;
- any Pose Apply is refused or ends with "Pose changes are paused…" / "CPM couldn't confirm…";
- a Save, Apply or Undo changes a different character, or anything outside the posed body (Undo must restore it);
- in the duplicate-model check: instance B changes when the preset is applied to A, the preset applies to B instead
  of A, or Undo does not restore A (stop after capturing **S-K-DUP-APPLY** / **S-K-DUP-UNDO**; the logs are kept);
- the Heavy's or Krystal's Full body can be saved (a refusal is expected), or Krystal's Full body saves a version 2
  pose;
- SFM misbehaves: a crash, an autosave recovery prompt, or a hang longer than a minute;
- any status message differs from Expected in a way that changes meaning.

The Soldier's Full body refusal (step 11) is a **finding**, not a STOP, provided nothing was written.

## Evidence, rollback and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library K` (after Process 3) | the run's records under `Characters\…\Poses` |
| R2 | `rollback` | v1.0.0 restored file by file; library untouched; housekeeping and `.pyc` restored |
| R3 | `library V100` (after Process 4) | the same Poses rows as `library K` |
| R4 | `collect-logs` | 4 CPM processes: three candidate (`84cd996c…`), one v1.0.0 (`ccbed9d7…`) |
| R5 | `cleanup` | `RESTORED`: library equal to the pre-run backup, every inventory equal to its baseline |
| R6 | `compare` | `PS2_VERDICT.md`: PASS, or PASS WITH FINDINGS (Soldier refusal only) |

**If the run stops early:** `rollback` and `cleanup` still run (they need no completed steps), followed by
`collect-logs` and `compare` for the record. A stopped run is reported as STOPPED; it is never a PASS.

**Rollback stop conditions (after `rollback` or `cleanup`):** any `inventory_problems`, `library_untouched: false`,
an installed v1.0.0 software file that differs from the published ZIP, or Poses rows that changed between
`library K` and `library V100`. Then nothing further is installed; the backups in `<Q>\pre_run\backup` are the
recovery source, and the Owner decides.
