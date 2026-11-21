SFM CHARACTER TOOLS v1.1.0
==========================
by ChadChan3D


1. WHAT THE TOOLS DO
--------------------
Character Preset Manager saves body settings (including bone scaling) and
facial expressions for reuse across shots. It also fits clothing to
characters. New in v1.1.0, its Pose Library saves character poses and
applies them to other copies of the same model.

Control Group Normalizer rebuilds bones and flexes into consistent groups
across supported models, so animators learn one layout instead of many.

SFM Control Group Updater installs Animation Groups updates and rebuilds
the matching sidecar after you edit the file (section 8). The ZIP includes the current
file, so the tools work right after installation.

The ZIP also includes an optional Character Preset Manager toolbar button
(section 10).


2. INSTALLATION AND UPDATING
----------------------------
IMPORTANT: Installing or upgrading replaces your existing Animation Groups file:

   usermod\cfg\sfm_defaultanimationgroups.txt

If you've customized this file, save a backup copy before installing or upgrading.

1. Close Source Filmmaker.
2. Extract the ZIP.
3. Copy the top-level "usermod" folder into your SourceFilmmaker\game folder (not into game\usermod), typically:

   ...\steamapps\common\SourceFilmmaker\game

4. If Windows asks, allow it to merge folders and replace existing files.
5. Start SFM. Open Scripts > SFM Character Tools to find the three tools.

UPDATING FROM v1.0.0:

Follow the same steps. Your Body Presets, Expressions and Review choices are kept in your Documents folder (section 4).

RETURNING TO v1.0.0:

Install the v1.0.0 ZIP the same way. Saved poses are kept; v1.0.0 ignores them. v1.0.0 doesn't use these v1.1.0 files, so you can delete them:

   usermod\scripts\SFM Character Tools\cpm_pose_profiles_v1.json
   usermod\scripts\SFM Character Tools\cpm_body_profiles_v1.json


3. UNINSTALLING
---------------
Steam Workshop installation: If you installed using Workshop Setup, open Scripts > SFM Character Tools > Manage Installation to uninstall the managed tools. Unsubscribing from the Workshop item alone doesn't remove installed files.

If you later installed a newer ZIP over the Workshop installation, some newer files may remain after using Manage Installation. Follow the manual removal instructions below to remove them.

Manual ZIP installation: Close SFM and remove the files listed below.

Uninstalling removes the tools. It doesn't delete your presets, poses, logs or Animation Groups backups.

1. Close SFM.
2. In your SourceFilmmaker\game folder, delete these folders:

   usermod\scripts\SFM Character Tools\
   usermod\scripts\sfm\mainmenu\SFM Character Tools\
   usermod\tools\SFM Control Group Updater\

3. Delete these files, together with any file of the same name ending in .pyc:

   usermod\scripts\ChadChan3D_CPM\SFM_Character_Preset_Manager.py
   usermod\scripts\ChadChan3D_CPM\cpm_ase_quick_launch.py
   usermod\scripts\sfm\autoinit\ChadChan3D\ChadChan3D_CPM_ASE_Button.py

   The last two are the optional toolbar button (section 10), if you installed it. Delete the ChadChan3D_CPM folder only if it is now empty.

4. Delete the sidecar files in usermod\cfg\sfm_shared_authority\: manifest.json and the file whose name starts with sfm_master_0_ and ends in .sfmsidecar. Delete the folder only if it is now empty.

Your Animation Groups file, usermod\cfg\sfm_defaultanimationgroups.txt, is left in place. SFM uses it for its own animation groups. If you saved a copy of an earlier version before installing, you can restore that copy.

KEPT AFTER UNINSTALLING:

- Presets, poses and Review choices: Documents\SFM Character Preset Manager\
- Animation Groups backups: usermod\cfg\sfm_character_tools_backups\
- Logs: the folders listed in section 4

Reinstalling uses these again. Delete them yourself only if you no longer want them.


4. WHERE YOUR FILES ARE SAVED
-----------------------------
CHARACTER PRESET MANAGER:

Body Presets, Expressions, Poses and Review choices are saved in:

   Documents\SFM Character Preset Manager\

Each model has its own folder. To open the selected model's folder, use
Model Info > Open Preset Folder in CPM.

Updating, downgrading or uninstalling doesn't touch this folder. Copy it
to back up your presets and poses.

ANIMATION GROUPS:

   Installed file: usermod\cfg\sfm_defaultanimationgroups.txt
   Updater backups: usermod\cfg\sfm_character_tools_backups\

LOGS:

Include these when reporting a problem.

   Character Preset Manager: C:\Users\Public\Documents\SFM Character Preset Manager Logs\
   Control Group Normalizer: C:\Users\Public\Documents\SFM Normalizer Logs\


5. CHARACTER PRESET MANAGER
---------------------------
Open Scripts > SFM Character Tools > SFM Character Preset Manager.

1. Move the playhead into a shot containing your character.
2. Click Refresh Model List.
3. Select the character from the list.

CPM has these tabs:

- Body Presets: Save body settings, including bone scaling, with Save New. Restore them with Apply Preset.
- Expressions: Save facial expressions with Save New. Restore them with Apply Preset.
- Clothing Fit: Use Fit Selected to Model to fit selected clothing to your character.
- Poses: Save and apply character poses (section 6).
- Review: Appears when CPM finds unrecognized flexes. Classify them as Body or Expression, or exclude them from presets.

Update Preset, Add Favorite and Delete Preset manage existing presets.


6. POSE LIBRARY
---------------
The Poses tab saves a character's pose and applies it to another instance of the same character.

- Save New: Saves the pose at the playhead, either Full body or only the Selected parts you pick.
- Apply Pose: In the Motion Editor, select a pose and click Apply Pose. The pose is applied at the playhead without changing the character's position or facing. Ctrl+Z undoes it in one step.
- Pose Info: Shows a pose's body parts, source model and rig.
- Update Pose, Add Favorite, Delete Pose: Work like the matching preset buttons. Right-click a pose to rename it.

Full body works with supported characters, including some without rigs
and others using compatible rigs such as the standard SFM biped rig
(rig_biped_simple). CPM checks each character's compatibility. If Full
body isn't supported, Selected parts may still be available.

CPM can adapt a pose between versions of the same model's rig when the
difference is simple, such as a missing chest control. If a pose can't be
applied safely, CPM explains why and changes nothing.

KNOWN LIMITATIONS:

- Poses don't transfer between different models.
- Facial expressions aren't part of poses. Use Expressions.
- Simulated ear, hair and tail tips may sit slightly differently.
- If CPM reports that the evaluated pose differs from the saved pose, the
  pose was applied but doesn't match exactly. Check it, and use Ctrl+Z if
  it looks wrong.


7. CONTROL GROUP NORMALIZER
---------------------------
Open Scripts > SFM Character Tools > Rebuild Control Groups Normalizer.

The Normalizer rebuilds character control groups into a standard layout
without changing your shot structure.

IMPORTANT: The Normalizer doesn't support Undo. Save your project first.

- Rebuild Selected Shot(s): Rebuilds the shots selected in the Clip Editor.
- Rebuild All Shots: Rebuilds every shot in the project.

Large projects can use substantial memory. Start a fresh SFM session
before processing a large project. If available memory reaches the
safety limit, the Normalizer stops and displays a warning to help
prevent a crash. Save, restart SFM, and use Rebuild Selected Shot(s) on
the remaining shots. Rebuilding a shot twice is safe.


8. SFM CONTROL GROUP UPDATER
----------------------------
SFM reads the Animation Groups file. Character Preset Manager and the
Normalizer read a sidecar compiled from it. The two must match for the
tools to recognize bones and flexes.

Open the updater from Scripts > SFM Character Tools > SFM Control Group
Updater, or run it directly without SFM:

   usermod\tools\SFM Control Group Updater\SFM Control Group Updater.exe

It opens in its own window. Close SFM before choosing an action.

- Get Published Version: Installs the latest published Animation Groups
  file and its sidecar, replacing your current file. Requires internet.
- Update Using SFM's TXT: Rebuilds the sidecar after you edit your
  Animation Groups file (section 9).
- Choose Another TXT File: Installs a copy of the TXT you select, for
  example a backup, and builds its sidecar.

Before replacing your Animation Groups file, the updater asks to confirm
and saves a backup in:

   usermod\cfg\sfm_character_tools_backups\

To report a problem, press Ctrl+Shift+D in the updater window to copy
diagnostics. The updater doesn't save a log file.


9. ADVANCED: CUSTOM ANIMATION GROUPS
------------------------------------
You can add support for more models by editing your Animation Groups file.
Add new bone and flex names to the appropriate groups, but don't rename or
move groups: the tools rely on the existing names and hierarchy.

To apply your changes:

1. Edit usermod\cfg\sfm_defaultanimationgroups.txt.
2. Close SFM and open SFM Control Group Updater.
3. Choose Update Using SFM's TXT to rebuild the sidecar.

Installing or updating SFM Character Tools, or choosing Get Published
Version, replaces your customized file. Get Published Version saves a
backup first (section 4); before installing or updating, save your own
copy (section 2). To keep your additions, copy them from the backup into
the replacement file, then repeat steps 2 and 3.

To help the published file cover more models, share your scan data (section 11).


10. OPTIONAL CPM TOOLBAR BUTTON
-------------------------------
The "OPTIONAL - CPM Button" folder adds a Character Preset Manager button
to the Animation Set Editor toolbar.

Requires Autoinit Manager (install it first):
https://steamcommunity.com/sharedfiles/filedetails/?id=3400621327

Tested with Extended Animation Set Editor Buttons (Extended ASE).

INSTALL:

1. Close SFM.
2. Copy the "usermod" folder from "OPTIONAL - CPM Button" into your
   SourceFilmmaker\game folder (not into game\usermod). If Windows asks,
   allow it to replace existing files.

This installs:

   usermod\scripts\sfm\autoinit\ChadChan3D\ChadChan3D_CPM_ASE_Button.py
   usermod\scripts\ChadChan3D_CPM\cpm_ase_quick_launch.py

ENABLE OR DISABLE:

Open Scripts > Autoinit Manager, tick or untick ChadChan3D_CPM_ASE_Button,
then restart SFM.

If the button doesn't appear in the Animation Set Editor, check that
Autoinit Manager is installed, the button is enabled, and the editor is
wide enough to show it.

REMOVE:

Close SFM and delete the two files above and their .pyc copies. Keep the
ChadChan3D_CPM folder; Character Preset Manager uses it.


11. HELP IMPROVE MODEL COMPATIBILITY
------------------------------------
The included Animation Groups file draws on scans of over 9,000 SFM models,
but many remain unrepresented. Scan data from your library helps the tools
recognize more models.

SFM Model Scanner works offline, doesn't modify your models, and doesn't
upload anything. The export contains each model's bone, flex and
attachment data and its path inside the folder you scanned, not the full
path to your library.

1. Download SFM Model Scanner:
   https://github.com/chadchan3d/sfm-model-scanner
2. Scan your library with "Include subfolders" ticked.
3. Choose Export > Full Scan Data > SQLite.
4. Upload the .sqlite file to MEGA or GoFile.
5. Share the link on ChadChat: https://chadchan3d.com/chat/


12. CREDITS
-----------
The included Animation Groups file builds on Silkworm's original Default
Animation Groups file, which helped establish much of its bone and flex
catalogue:
https://sfmlab.com/project/9c38bba3-f861-4a05-9565-6f9fd3f4deb1/


13. HELP AND LINKS
------------------
Questions, bug reports and scan data: ChadChat
https://chadchan3d.com/chat/

SFM Character Tools:
https://github.com/chadchan3d/sfm-character-tools

OTHER TOOLS BY CHADCHAN3D:

SFM Model Scanner
https://github.com/chadchan3d/sfm-model-scanner

SFM Package Builder
https://github.com/chadchan3d/sfm-package-builder

SFM Bring Near Props
https://github.com/chadchan3d/sfm-bring-near-props

SFM Bring Near Lights
https://github.com/chadchan3d/sfm-bring-near-lights

Remove Remove Workshop Prompt
https://github.com/chadchan3d/remove-remove-workshop-prompt

Steam Workshop
https://steamcommunity.com/profiles/76561199571308867/myworkshopfiles/?appid=1840
