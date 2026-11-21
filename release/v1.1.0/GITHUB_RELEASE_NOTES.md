SFM Character Tools v1.1.0 for Source Filmmaker.

**Download:** `SFM.Character.Tools.v1.1.0.zip`. Full instructions are in the `README.txt` inside the ZIP.

## New: Pose Library
Character Preset Manager has a new **Poses** tab. Save a character's pose and apply it to another copy of the same model.

- **Full body or Selected parts:** save the whole pose, or only the body parts you pick.
- **Apply Pose:** in the Motion Editor, applies the pose at the playhead without changing the character's position or facing. Ctrl+Z undoes it in one step.
- **Compatible rigs:** Full body works with supported characters, including some without rigs and others using compatible rigs such as the standard SFM biped rig (`rig_biped_simple`). CPM checks each character's compatibility; if Full body isn't supported, Selected parts may still be available.
- **Rig versions:** CPM can adapt a pose between versions of the same model's rig when the difference is simple, such as a missing chest control.
- **Safety:** if a pose can't be applied safely, CPM explains why and changes nothing.
- **Pose Info** shows a pose's body parts, source model and rig. Update Pose, Add Favorite and Delete Pose work like the matching preset buttons.

## Known limitations
- Poses don't transfer between different models.
- Facial expressions aren't part of poses. Use Expressions.
- Simulated ear, hair and tail tips may sit slightly differently.
- If CPM reports that the evaluated pose differs from the saved pose, the pose was applied but doesn't match exactly. Check it, and use Ctrl+Z if it looks wrong.

## Also in this release
- **Body Presets and Expressions:** Improved support for static bone scales and flex values, with correct targeting when multiple copies of the same model are present.
- The README now covers updating, returning to v1.0.0, uninstalling, and where your files are saved.
- The Normalizer, the Control Group Updater and the bundled Animation Groups data 1.0.0 are unchanged from v1.0.0.

## Installing or updating
1. Close Source Filmmaker.
2. Extract the ZIP.
3. Copy its top-level `usermod` folder into your `SourceFilmmaker\game` folder (not into `game\usermod`), merging with the existing `usermod`.
4. Start SFM and open **Scripts > SFM Character Tools**.

**Important:** installing replaces `usermod\cfg\sfm_defaultanimationgroups.txt`. If you've customized it, back it up first.

Your Body Presets, Expressions and Review choices are kept in `Documents\SFM Character Preset Manager\`. To return to v1.0.0, install the v1.0.0 ZIP the same way; saved poses are kept and v1.0.0 ignores them.

**Steam Workshop:** Workshop Setup still installs v1.0.0. A Workshop update to v1.1.0 will follow separately.

## Optional CPM toolbar button
The `OPTIONAL - CPM Button` folder adds a Character Preset Manager button to the Animation Set Editor toolbar. It is **not** installed by copying the main `usermod` folder. It requires Autoinit Manager. Follow the README in that folder.

## Verification
- `SHA256SUMS.txt`: the SHA-256 of the ZIP.
- `ZIP_CONTENTS_SHA256.txt`: the SHA-256 of every file inside the ZIP.
- The software inventory inside the ZIP is signed with the same key as v1.0.0.

ZIP SHA-256: `0f64eb1306a57f7065db6dcc8419e7e909525a9057af1ee67dce0c8fcc6b8b57`
