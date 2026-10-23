SFM CHARACTER TOOLS v1.0.0
==========================
by ChadChan3D


1. WHAT THE TOOLS DO
--------------------
SFM models use different names and arrangements for bones and flex controls. Animators must search through long lists and learn a different layout for each character.

Character Preset Manager saves body settings (including bone scaling) and facial expressions for reuse across shots. It also fits clothing to characters.

Control Group Normalizer rebuilds control groups using a consistent structure across models. Bones and flexes appear in the same groups, so animators learn one layout instead of many.

Character Preset Manager and the Normalizer read a sidecar file built from SFM's Animation Groups file. The ZIP includes the Animation Groups file and its sidecar, so the tools work right after installation. SFM Control Group Updater keeps the two in sync.

The ZIP also includes an optional Character Preset Manager toolbar button, which you can install separately (section 7).


2. INSTALLATION
---------------
IMPORTANT: Installing or upgrading replaces your existing Animation Groups file:

   usermod\cfg\sfm_defaultanimationgroups.txt

If you've customized this file, save a backup copy before installing or upgrading.

1. Close Source Filmmaker.
2. Extract the ZIP.
3. Copy the included "usermod" folder into your SourceFilmmaker\game folder, typically:

   ...\steamapps\common\SourceFilmmaker\game

   This merges with the existing "usermod" folder; do not create a second one inside it.

4. If Windows asks, allow it to merge folders and replace existing files.
5. Start SFM. Open Scripts > SFM Character Tools to find the three tools.


3. CHARACTER PRESET MANAGER
---------------------------
Open Scripts > SFM Character Tools > SFM Character Preset Manager.

1. Move the playhead into a shot containing your character.
2. Click Refresh Model List.
3. Select the character.

- Body Presets: Save body settings, including bone scaling, with Save New. Restore them with Apply Preset.
- Expressions: Save facial expressions with Save New. Restore them with Apply Preset.
- Clothing Fit: Use Fit Selected to Model to fit selected clothing to your character.
- Review: Classify unrecognized flexes as Body or Expression, or exclude them from presets. Your choices are saved for that model.

You can also update existing presets, mark favorites, and delete presets.


4. CONTROL GROUP NORMALIZER
---------------------------
Open Scripts > SFM Character Tools > Rebuild Control Groups Normalizer.

The Normalizer rebuilds character control groups into a standard layout without changing your shot structure.

The Normalizer does not support SFM Undo. Save your project before rebuilding shots.

- Rebuild Selected Shot(s): Process the shots selected in the Clip Editor.
- Rebuild All Shots: Process every shot in the project.

Rebuild All Shots can use substantial memory, especially in large projects. Start a fresh SFM session before processing a large project.

If available memory reaches the Normalizer's safety limit, processing stops and a warning appears to help prevent an SFM crash.

If processing stops, save your project, restart SFM, and use Rebuild Selected Shot(s) to finish the remaining shots.


5. SFM CONTROL GROUP UPDATER
----------------------------
SFM reads the Animation Groups file (usermod\cfg\sfm_defaultanimationgroups.txt). Character Preset Manager and the Normalizer use a compiled sidecar built from that file. The two files must match for the tools to recognize bones and flexes.

The updater installs Animation Groups updates and rebuilds the matching sidecar when you edit or replace your TXT file.

To open the updater, select Scripts > SFM Character Tools > SFM Control Group Updater in SFM. It opens in a separate window.

You can also launch it directly without opening SFM:

   usermod\tools\SFM Control Group Updater\SFM Control Group Updater.exe

Close SFM before choosing an action. The updater stays open after SFM closes.

The updater offers three actions:

- Get Published Version: Install the latest Animation Groups file published for SFM Character Tools and its matching sidecar. Requires internet access.
- Update Using SFM's TXT: Rebuild the sidecar after editing your installed Animation Groups file.
- Choose Another TXT File: Replace your installed Animation Groups file with a copy of the TXT you select and build its matching sidecar. The selected source file is not modified.

Before replacing the installed Animation Groups file, the updater asks for confirmation and saves a backup here:

   usermod\cfg\sfm_character_tools_backups\


6. ADVANCED: CUSTOM ANIMATION GROUPS
------------------------------------
You can add support for more models by editing your Animation Groups file.

Keep the existing group names and hierarchy. Add new bone and flex names within the appropriate groups.

To apply your changes:

1. Edit usermod\cfg\sfm_defaultanimationgroups.txt.
2. Open SFM Control Group Updater, then close SFM.
3. Select Update Using SFM's TXT to rebuild the matching sidecar.

Get Published Version replaces your customized Animation Groups file. A backup is saved here:

   usermod\cfg\sfm_character_tools_backups\


7. OPTIONAL CPM TOOLBAR BUTTON
------------------------------
The included "OPTIONAL - CPM Button" folder adds a Character Preset Manager button to the Animation Set Editor toolbar.

The button requires Autoinit Manager. Install it before installing the button:
https://steamcommunity.com/sharedfiles/filedetails/?id=3400621327

The button has been tested for compatibility with the Steam Workshop script Extended Animation Set Editor Buttons (Extended ASE).

INSTALL:

1. Close SFM.
2. Open the "OPTIONAL - CPM Button" folder.
3. Copy its "usermod" folder into your SourceFilmmaker\game folder.

This installs two files:

   usermod\scripts\sfm\autoinit\ChadChan3D\ChadChan3D_CPM_ASE_Button.py
   usermod\scripts\ChadChan3D_CPM\cpm_ase_quick_launch.py

If upgrading an earlier version of the button, replace both files together.

After installing, start SFM and open the Animation Set Editor. The CPM button should appear in its toolbar.

If the button doesn't appear, check that Autoinit Manager is installed, the button is enabled, and the Animation Set Editor is wide enough to display it.

ENABLE OR DISABLE:

Open Scripts > Autoinit Manager, tick or untick ChadChan3D_CPM_ASE_Button, then restart SFM.

REMOVE:

Close SFM and delete the two files listed above. Do not delete the ChadChan3D_CPM folder, which also contains Character Preset Manager.


8. HELP IMPROVE MODEL COMPATIBILITY
-----------------------------------
Better bone and flex recognition lets the Normalizer organize more models correctly and helps Character Preset Manager work with more characters.

The included Animation Groups file draws on scans of over 9,000 SFM models, but many models remain unrepresented. You can help expand its coverage by contributing scan data from your model library.

1. Download SFM Model Scanner:
   https://github.com/chadchan3d/sfm-model-scanner

2. Scan your library with "Scan Subfolders" enabled.

3. Select Export > Full Scan Data > SQLITE.

4. Upload the exported .sqlite file to MEGA or GoFile.

5. Share the download link on ChadChat:
   https://chadchan3d.com/chat/

The Scanner works offline, does not modify your models, and does not upload anything automatically.


9. CREDITS
----------
The included Animation Groups file builds on Silkworm's original Default Animation Groups file, which helped establish the bone and flex name catalogue.

Silkworm's Default Animation Groups on SFMLab:
https://sfmlab.com/project/9c38bba3-f861-4a05-9565-6f9fd3f4deb1/


10. LOGS AND DIAGNOSTICS
------------------------
Normalizer:
C:\Users\Public\Documents\SFM Normalizer Logs\
Keeps the log from the last error-free run plus up to 20 dated reports.

Character Preset Manager:
C:\Users\Public\Documents\SFM Character Preset Manager Logs\
Keeps up to five 2 MiB log files.

SFM Control Group Updater:
Press Ctrl+Shift+D in the updater window to copy session diagnostics. The updater doesn't save a log file.

Need help or found a bug? Visit ChadChat: https://chadchan3d.com/chat/


11. PROJECT LINKS
-----------------
SFM Character Tools
https://github.com/chadchan3d/sfm-character-tools

SFM Model Scanner
https://github.com/chadchan3d/sfm-model-scanner

SFM Package Builder
https://github.com/chadchan3d/sfm-package-builder

SFM Runtime Monitor
https://github.com/chadchan3d/sfm-runtime-monitor

SFM Bring Near Props
https://github.com/chadchan3d/sfm-bring-near-props

SFM Bring Near Lights
https://github.com/chadchan3d/sfm-bring-near-lights

Remove Remove Workshop Prompt
https://github.com/chadchan3d/remove-remove-workshop-prompt

ChadChan3D's Steam Workshop
https://steamcommunity.com/profiles/76561199571308867/myworkshopfiles/?appid=1840

ChadChat
https://chadchan3d.com/chat/
