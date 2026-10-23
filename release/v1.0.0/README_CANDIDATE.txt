SFM Character Tools v1.0.0
==========================
by ChadChan3D


1. WHAT IT DOES FOR YOUR WORKFLOW
---------------------------------

Every SFM model names its bones and flexes its own way, so finding the
control you want often means scrolling through long, unsorted lists - and
learning a new layout for every character. SFM Character Tools fixes that:

- The Control Group Normalizer rebuilds a model's control groups using one
  consistent set of grouping conventions. The same kinds of controls land in
  the same, predictable groups on every model, so animation controls are
  easier to find and quicker to reach.
- Character Preset Manager saves and reapplies expressions, body settings,
  scale and clothing fits, so you can reuse a look across shots and
  characters instead of rebuilding it slider by slider.
- The SFM Control Group Updater keeps the shared Animation Groups data that
  both tools use up to date, or builds it from your own animation-group
  file.

Both tools read the same Animation Groups data to recognize model controls.
This download already includes it, so everything works right after you
install.


2. INSTALLATION
---------------

1. Close Source Filmmaker.
2. Extract this ZIP.
3. Copy the "usermod" folder from this ZIP into your SourceFilmmaker\game
   folder, for example:
       ...\steamapps\common\SourceFilmmaker\game
   Merge the folders; do not delete your existing "usermod" folder.
4. Start SFM. The tools are in the Scripts menu under SFM Character Tools.

That one copy installs Character Preset Manager, the Normalizer, the updater
and the official Animation Groups data. No separate download or setup step
is needed.

IMPORTANT - this install REPLACES your animation-group file:
    usermod\cfg\sfm_defaultanimationgroups.txt
If you have customized that file, copy it somewhere outside the SFM folder
before you install. The same goes for any other file Windows asks to
replace: back up customized versions, and if you don't recognize a file,
cancel and inspect it first.

Optional: CPM toolbar button (CPM Quick Launch)
  The folder "OPTIONAL - CPM Button" adds a CPM button to the Animation Set
  Editor toolbar that opens Character Preset Manager. It is not installed by
  the step above. It requires Autoinit Manager:
      https://steamcommunity.com/sharedfiles/filedetails/?id=3400621327
  It has been tested alongside Extended ASE. See section 7.

Updating from an earlier SFM Character Tools test version
  Earlier versions lived under Scripts > ChadChan3D. After copying the new
  "usermod" folder, close SFM and delete ONLY these items from
      usermod\scripts\sfm\mainmenu\ChadChan3D\
  (leave everything else in that folder, including your other scripts):
      SFM_Character_Preset_Manager.py
      Rebuild_Control_Groups_Normalizer.py
      SFM_Control_Group_Updater.py         (if present)
      cpm_authority_adapter.py   and   cpm_authority_adapter.pyc
      cpm_compat_v1_projection.py   and   cpm_compat_v1_projection.pyc
      sfm_character_tools_inventory.json
      sfm_character_tools_inventory.sig
      sfm_master_authority_productionized   (folder)
      sfm_master_sidecar                    (folder)
  Until you do, the tools may refuse to start in an SFM session where the
  old copy was opened first; restart SFM after the cleanup.
  If the updater then says "Character Tools data doesn't match the
  animation-group TXT in SFM", choose Update Using SFM's TXT once (with SFM
  closed). It tidies up the data left from the earlier version; nothing is
  deleted - the old files are kept in the updater's recovery storage.


3. CHARACTER PRESET MANAGER
---------------------------

Scripts > SFM Character Tools > SFM_Character_Preset_Manager

Select a character in the Animation Set Editor with the playhead inside a
shot, then use the tabs:

- Body Presets - save the character's current body sliders (including
  scale) with Save New, and reapply them to the same or another character
  with Apply Preset.
- Expressions - the same for facial expressions.
- Clothing Fit - fit selected clothing to the character's body with
  Fit Selected to Model.
- Review - items that need your review before a preset uses them.

Update Preset overwrites the selected preset with the character's current
settings, Add Favorite marks it, Preset Info shows its details, and Delete
Preset removes it.


4. CONTROL GROUP NORMALIZER
---------------------------

Scripts > SFM Character Tools > Rebuild_Control_Groups_Normalizer

Save your session first. The Normalizer asks which shots to process:

- Rebuild Selected Shot(s) - only the shots selected in the Clip Editor.
- Rebuild All Shots - every shot in the session.

It reorganizes the characters' control groups using the Animation Groups
conventions; your animation is kept.

Protective memory stop: SFM has limited memory. If it runs low while the
Normalizer works, the Normalizer stops on its own before SFM can crash
("Normalizer - Stopped to Protect SFM"). Do what the message says: save your
project, restart SFM, then use Rebuild Selected Shot(s) for the remaining
shots. If it reports that it couldn't verify enough memory, save and follow
its instructions the same way.


5. SFM CONTROL GROUP UPDATER
----------------------------

Scripts > SFM Character Tools > SFM_Control_Group_Updater
(or double-click usermod\tools\SFM Control Group Updater\
SFM Control Group Updater.exe)

The updater opens in its own window. You can choose an action while SFM is
open, but SFM must be closed before the updater installs anything - it tells
you when. Whenever it replaces your animation-group file it asks first and
keeps your previous file as a backup.

- Get Published Version - download and install newer official Animation
  Groups data when ChadChan3D publishes it (needs an internet connection).
- Update Using SFM's TXT - rebuild the tools' data from the
  sfm_defaultanimationgroups.txt in your SFM folder. Use it after you edit
  that file yourself.
- Choose Another TXT File - use a different animation-group file you select
  (the file you select is not changed).


6. CUSTOM ANIMATION GROUPS
--------------------------

You can maintain your own sfm_defaultanimationgroups.txt. After editing it,
run Update Using SFM's TXT so both tools pick up your changes.

Please keep the official group names and structure, and add your own
controls inside the existing groups where possible. Both tools rely on those
grouping conventions; renaming or reorganizing the official groups makes
controls harder to find and can stop presets and normalization from
recognizing them.

Remember that installing a new SFM Character Tools download replaces this
file (section 2), and Get Published Version replaces it with official data
(after asking). Keep a copy of your customized version.


7. OPTIONAL CPM TOOLBAR BUTTON
------------------------------

Requires Autoinit Manager (see section 2). The regular Scripts-menu entry
for Character Preset Manager always works without it.

Install (SFM closed):
  From "OPTIONAL - CPM Button\usermod", copy these two files to the same
  places in your SFM game folder:
      usermod\scripts\sfm\autoinit\ChadChan3D\ChadChan3D_CPM_ASE_Button.py
      usermod\scripts\ChadChan3D_CPM\cpm_ase_quick_launch.py
  If either file is already there, replace both together only if they came
  from an earlier SFM Character Tools download. If only one exists, or you
  don't know where it came from, stop and keep a backup of it instead.
  Don't remove anything else from the ChadChan3D_CPM folder - it holds
  Character Preset Manager.

Turn off / on:
  Scripts > Autoinit Manager: untick or tick ChadChan3D_CPM_ASE_Button, then
  restart SFM.

Remove (SFM closed):
  Delete only those two files. You may delete the autoinit\ChadChan3D folder
  if it is then empty. Never delete the ChadChan3D_CPM folder.

If the button doesn't appear, check that Autoinit Manager is installed and
the button is ticked in it, then restart SFM. If the editor is too narrow,
widen it or use the Scripts menu.


8. HELP IMPROVE MODEL COMPATIBILITY
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


9. CREDITS
----------

Silkworm's Default Animation Groups file was an early foundation for
cataloguing SFM bone and flex names; the Animation Groups Master builds on
that work.


10. PROJECT LINKS
-----------------

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
Steam Workshop - ChadChan3D's SFM tools
    https://steamcommunity.com/profiles/76561199571308867/myworkshopfiles/?appid=1840
ChadChat
    https://chadchan3d.com/chat/
