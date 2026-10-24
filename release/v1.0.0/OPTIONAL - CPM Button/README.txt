CPM TOOLBAR BUTTON (OPTIONAL)
SFM Character Tools v1.0.0
================================

WHAT IT DOES
------------
Adds a CPM button to Source Filmmaker's Animation Set Editor toolbar. Clicking it opens Character Preset Manager.

The button is optional. You can also open Character Preset Manager from:

Scripts > SFM Character Tools > SFM Character Preset Manager


REQUIREMENTS
------------
- SFM Character Tools v1.0.0
- Autoinit Manager

Get Autoinit Manager from Steam Workshop:
https://steamcommunity.com/sharedfiles/filedetails/?id=3400621327

The button has also been tested alongside Extended Animation Set Editor Buttons (Extended ASE).


INSTALL OR UPDATE
-----------------
1. Close SFM.
2. Open the "OPTIONAL - CPM Button" folder included in the download.
3. Copy its "usermod" folder into your SFM game folder:

   ...\steamapps\common\SourceFilmmaker\game

4. Allow Windows to merge folders and replace existing files.
5. Start SFM.

The CPM button should appear in the Animation Set Editor toolbar.

Use these same steps to update an existing button.


TURN THE BUTTON ON OR OFF
-------------------------
Open Scripts > Autoinit Manager.

Find ChadChan3D_CPM_ASE_Button and check or uncheck it.

Restart SFM to apply the change.


REMOVE THE BUTTON
-----------------
Close SFM and delete these two files:

usermod\scripts\sfm\autoinit\ChadChan3D\ChadChan3D_CPM_ASE_Button.py

usermod\scripts\ChadChan3D_CPM\cpm_ase_quick_launch.py

Do not delete the ChadChan3D_CPM folder itself. It also contains Character Preset Manager.


TROUBLESHOOTING
---------------
Button missing?
Check that Autoinit Manager is installed and the CPM button is enabled. Restart SFM.

Button not visible in the toolbar?
Widen the Animation Set Editor. Some buttons are hidden when the window is narrow.

Button doesn't open Character Preset Manager?
Try opening Character Preset Manager from the Scripts menu. If that also fails, reinstall SFM Character Tools.


PROJECT
-------
SFM Character Tools:
https://github.com/chadchan3d/sfm-character-tools

Help and feedback:
https://chadchan3d.com/chat/
