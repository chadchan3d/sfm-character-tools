SFM Character Tools v1.0.0
==========================
by ChadChan3D


1. WHAT IS THIS?
----------------

SFM models name their bones and flexes in many different ways, so the same
part of a character can be hard to find from one model to the next. SFM
Character Tools brings order to that:

- Control Group Normalizer organizes a model's controls into consistent
  groups.
- Character Preset Manager saves and applies expressions, body settings,
  scale and clothing fits.

Both tools use shared Animation Groups data to recognize model controls. The
included updater installs official data or prepares your own.


2. INSTALLATION
---------------

1. Close Source Filmmaker.
2. Extract this ZIP.
3. Copy the "usermod" folder from this ZIP into your SourceFilmmaker\game
   folder, for example:
       ...\steamapps\common\SourceFilmmaker\game

Your game folder already has a "usermod" folder. Copying merges the two:
your existing files stay where they are, and the tools' files are added. Do
not delete your existing usermod folder. If Windows asks about files with
the same name, those are earlier versions of these tools; replace them.

The SFM Control Group Updater is included and is installed by the same copy.

Before copying, back up anything you have customized. If you have edited
these tools' files, or the folders below contain files you don't recognize,
copy them somewhere outside the SFM folder first. Don't overwrite an
installation you're unsure about.
    game\usermod\scripts\ChadChan3D_CPM\
    game\usermod\scripts\sfm\mainmenu\ChadChan3D\
    game\usermod\tools\SFM Control Group Updater\


3. SET UP ANIMATION GROUPS
--------------------------

The tools need Animation Groups data. Set it up with the updater:

    game\usermod\tools\SFM Control Group Updater\SFM Control Group Updater.exe

Open it from SFM (see section 4) or by double-clicking that file. It offers
three actions:

- Get Published Version (recommended for first-time setup)
  Downloads the official Animation Groups data maintained by ChadChan3D and
  installs it. Needs an internet connection.
- Update Using SFM's TXT
  Builds the tools' data from the animation-group TXT already in your SFM
  folder. Use it after you edit that TXT yourself.
- Choose Another TXT File
  Uses a different animation-group TXT that you select. The file you select
  is not changed.

When an action replaces your current animation-group TXT, the updater asks
first and keeps your previous TXT as a backup.


4. USING THE TOOLS
------------------

In SFM, open the Scripts menu, then ChadChan3D:

    SFM_Character_Preset_Manager        Character Preset Manager
    Rebuild_Control_Groups_Normalizer   Control Group Normalizer
    SFM_Control_Group_Updater           opens the updater

Save your session before running the Normalizer.

The updater opens in its own window; SFM keeps running. You can prepare an
action while SFM is open, but SFM must be closed before the updater installs
data. It tells you when to close SFM.


5. OPTIONAL CPM TOOLBAR BUTTON
------------------------------

The folder "OPTIONAL - CPM Button" adds a CPM button to the Animation Set
Editor toolbar that opens Character Preset Manager.

- It requires Autoinit Manager.
- It has been tested alongside Extended ASE.
- The regular Scripts-menu entry for Character Preset Manager works without
  it.

Copying the main "usermod" folder does NOT install this button. See
"OPTIONAL - CPM Button\README.txt" to install or remove it.


6. HELP IMPROVE MODEL COMPATIBILITY
-----------------------------------

I've collected bone and flex data from over 9,000 SFM models, but many models
remain unrepresented.

If you have a large SFM model library, your scan data can help improve
compatibility.

1. Download SFM Model Scanner:
   https://github.com/chadchan3d/sfm-model-scanner
2. Scan your models with "Scan Subfolders" enabled.
3. Select Export -> Full Scan Data -> SQLITE.
4. Upload the .sqlite file to MEGA or GoFile, then share the download link
   with me on ChadChat:
   https://chadchan3d.com/chat/

The Scanner works offline and does not modify models or upload anything
automatically. Share only data you're comfortable providing.

Your scans help expand the Animation Groups Master to support more bone and
flex names.


7. PROJECT LINKS
----------------

SFM Character Tools
    https://github.com/chadchan3d/sfm-character-tools
SFM Model Scanner
    https://github.com/chadchan3d/sfm-model-scanner
Other SFM tools
    https://github.com/chadchan3d/sfm-package-builder
    https://github.com/chadchan3d/sfm-runtime-monitor
    https://github.com/chadchan3d/sfm-bring-near-props
    https://github.com/chadchan3d/sfm-bring-near-lights
    https://github.com/chadchan3d/remove-remove-workshop-prompt
ChadChat
    https://chadchan3d.com/chat/
