# Workshop Setup v1.1.0: native upgrade and uninstall acceptance (WU)

**Status:** prepared offline, **not run**. Running it needs the Owner's separate authorization.

**What it establishes**, on the Owner's real v1.0.0 Workshop Setup installation:
1. the v1.1.0 Setup recognizes the existing installation;
2. updating installs v1.1.0 correctly;
3. existing presets and settings remain;
4. Character Preset Manager opens from the existing toolbar button;
5. the new Poses tab appears and works;
6. Manage Installation recognizes the updated installation and uninstalls safely.

The staged v1.1.0 Setup runs from the staging folder (`launch`), so the Steam-managed Workshop files stay v1.0.0 and
untouched. Afterwards `restore` returns the three usermod trees and the preset library to their exact pre-test state:
the v1.0.0 Workshop installation, ready for the later real Workshop update.

| Item | Value |
|---|---|
| Release ZIP | `SFM.Character.Tools.v1.1.0.zip` `0f64eb1306a57f7065db6dcc8419e7e909525a9057af1ee67dce0c8fcc6b8b57` (GitHub v1.1.0) |
| Staged Setup | `SCT_Setup.exe` `6fb5ac65b9358e28a50bdbe3401890f1d9f46d20805a89d293fd2e377cb7b28e`; Manage Installation launcher `47ed666a…` |
| Starting state required | installation record package `5323b143…` (v1.0.0), CPM `ccbed9d7…`, no registries |
| Session | `WU_SESSION.dmx`: a verified copy of the R2 fixture `259ea8a6…`, **never saved** |
| Tool | `python -I <REPO>\real_sfm_qualification\workshop_v110_upgrade\tools\wu_tool.py <Q>\wu.json <command>` |
| Backed up and restored | `usermod\scripts`, `usermod\cfg`, `usermod\tools`, `Documents\SFM Character Preset Manager` |

**Never:** save the session; use the Workshop menu's "Install or Update (Windows Setup)" entry (that is still the
v1.0.0 payload); unsubscribe or change anything in Steam; delete files by hand except the one Setup file Setup itself
names in step 9.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `wu.template.json` to `<Q>\wu.json`; fill the paths. Change no pin. | |
| P1 | `pre` | `PRE PASS: v1.0.0 Workshop installation found; backed up and verified …` |

## Hands-on test (Owner)

1. **Recognition.** Claude runs `launch`. Setup opens. **[W1]** Note what it shows: Installed version **1.0.0**,
   Package version **1.1.0**, and an update (not a fresh install). SFM must be closed; if it isn't, close it.
2. **Update.** Choose **Update / Reinstall** and confirm. Wait for the completion page **[W2]**, then close Setup.
3. Claude runs `check-update` (automated: every v1.1.0 file installed, Pose Library registries present, nothing else
   changed, presets untouched, Steam's Workshop files untouched).
4. **Presets.** Start SFM, open `<Q>\sessions\WU_SESSION.dmx`, Motion Editor, shot15. Open Character Preset Manager
   **from the toolbar button** in the Animation Set Editor **[W4]**. Select a character you have presets for: its Body
   Presets and Expressions are listed as before **[W3]**.
5. **Poses.** Open the **Poses** tab **[W5]**. Select the original Fox, **Save New**, Full body, name it `WU Pose`. Then
   select it and open **Pose Info** (note the Rig row). Optional: create a second Fox, Apply `WU Pose` to it, then
   Ctrl+Z.
6. **Close SFM without saving.**
7. **Manage Installation.** Start SFM, choose **Scripts > SFM Character Tools > Manage Installation** **[W6]**. Note
   that it shows the installed version **1.1.0**. Close SFM while Setup stays open.
8. **Uninstall.** Choose **Uninstall** and confirm. Note the completion page and anything it says remains.
9. If the page names a remaining Setup file, choose **Show Setup File**, close Setup, and delete that one file.
10. Tell Claude you're done, with any notes.

**STOP** and report if Setup refuses unexpectedly, a step changes something it shouldn't, or SFM crashes.

## Evidence and restoration (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| R1 | `check-uninstall` | `CHECK-UNINSTALL PASS` (programs, registries and launcher removed; TXT and backups kept; no pre-existing preset file changed; Steam's files untouched) |
| R2 | `restore` | `RESTORED`: the v1.0.0 Workshop installation and the preset library exactly as at `pre`; anything added since is kept in `<Q>\evidence\after_restore_removed\` |

The result is accepted only with the automated checks **and** the Owner's W1–W6 observations, reported side by side.
