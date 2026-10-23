OPTIONAL - CPM Button (CPM Quick Launch 1.0.0)
==============================================

Adds a CPM button to SFM's Animation Set Editor toolbar. The button opens
Character Preset Manager. It is optional: Character Preset Manager always
stays available from Scripts > ChadChan3D > SFM_Character_Preset_Manager.

Copying the main "usermod" folder of SFM Character Tools does not install
this button. Install it only with the steps below.


BEFORE YOU START
----------------
You need both of these already installed:

1. SFM Character Tools (Character Preset Manager), from the main "usermod"
   folder of this ZIP. The button opens it through its Scripts-menu entry.
2. Autoinit Manager (Steam Workshop item 3400621327). To check, look for
   Scripts > Autoinit Manager in SFM. If it is not there, do not install
   this button; use the Scripts menu instead. This ZIP does not include or
   change Autoinit Manager.

The button has been tested alongside Extended ASE.

Always close SFM before adding, replacing or removing files.

"SFM game folder" below means:
  ...\steamapps\common\SourceFilmmaker\game

The button consists of exactly two files:

  A  game\usermod\scripts\sfm\autoinit\ChadChan3D\ChadChan3D_CPM_ASE_Button.py
  B  game\usermod\scripts\ChadChan3D_CPM\cpm_ase_quick_launch.py

Version 1.0.0 file fingerprints (SHA-256):

  A  23e3a8813057642400b7e06e0b55e13c89f47b684779d907740905a5e28e4070
  B  4558d296505416591c79d08ecc9aa2fcaa0710003dbaaad94422e7654229f56f

To see a file's fingerprint, open a Command Prompt and run:
  certutil -hashfile "<full path to the file>" SHA256


STEP 1: CHECK WHAT IS ALREADY THERE (never skip this)
-----------------------------------------------------
With SFM closed, look for files A and B at the paths above.

- Neither file exists                  -> follow FRESH INSTALL.
- Both exist and both fingerprints
  match a version listed in this file  -> follow UPDATE.
- Only one exists, or a fingerprint
  matches no listed version            -> STOP. Do not copy anything.
                                          The file was changed or comes
                                          from somewhere else. See
                                          TROUBLESHOOTING.

Never copy these files over existing files without this check.


FRESH INSTALL
-------------
1. Close SFM.
2. Copy file A from this folder's
     usermod\scripts\sfm\autoinit\ChadChan3D\
   to
     game\usermod\scripts\sfm\autoinit\ChadChan3D\
   (create the ChadChan3D folder if it does not exist).
3. Copy file B from this folder's
     usermod\scripts\ChadChan3D_CPM\
   to
     game\usermod\scripts\ChadChan3D_CPM\
   This folder already exists: it holds Character Preset Manager. Add the
   file; do not replace or remove anything else in it.
4. Optional: confirm both fingerprints match the values above.
5. Start SFM and open the Animation Set Editor. The CPM button appears in
   its toolbar. Click it to open Character Preset Manager.


UPDATE (replacing a recognized earlier version)
-----------------------------------------------
Only when STEP 1 found both files and both match a listed version.

1. Close SFM.
2. Replace BOTH files A and B with the ones from this folder. Never update
   only one of them.
3. Start SFM.

If you had turned the button off in Autoinit Manager, it stays off after
an update.


TURN THE BUTTON OFF OR ON
-------------------------
Scripts > Autoinit Manager: untick (off) or tick (on)
ChadChan3D_CPM_ASE_Button, then restart SFM. The change takes effect after
the restart.

Character Preset Manager keeps working from the Scripts menu either way.


REMOVE
------
1. Close SFM.
2. Delete file A and file B (only these two files).
3. If game\usermod\scripts\sfm\autoinit\ChadChan3D\ is now empty, you may
   delete that empty folder.
4. Do NOT delete the ChadChan3D_CPM folder: it contains Character Preset
   Manager itself.

Autoinit Manager may still remember the button's on/off setting. That is
harmless; leave it.


TROUBLESHOOTING
---------------
- No CPM button: check that Autoinit Manager is installed and that
  ChadChan3D_CPM_ASE_Button is ticked in it, then restart SFM.
- The button disappears when the editor is narrow: widen the Animation Set
  Editor, or use the Scripts menu.
- "Character Preset Manager couldn't be opened": Character Preset Manager
  itself is missing or damaged. Try its Scripts-menu entry; if that also
  fails, reinstall SFM Character Tools from the main "usermod" folder.
- STEP 1 found an unrecognized file: keep a backup copy of it somewhere
  outside the SFM folder, and do not overwrite it. Ask for help with the
  file's fingerprint, or remove it yourself only if you know where it came
  from.
- After replacing files while SFM was running, the button may refuse to
  load the new version until SFM is restarted. Restart SFM.

This button never changes your animation data, Autoinit Manager's settings
or other add-ons' settings.
