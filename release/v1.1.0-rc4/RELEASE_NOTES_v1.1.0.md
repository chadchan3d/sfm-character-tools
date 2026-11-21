# SFM Character Tools v1.1.0: release notes (DRAFT for Owner review)

## New: Pose Library in Character Preset Manager

Save a character's pose and apply it to another instance of the same character.

- **Full body:** saves and applies the whole skeletal pose of characters rigged with the stock biped rig
  (`rig_biped_simple`), and of Krystal's qualified rig.
- **Selected parts:** saves and applies only the body parts you choose.
- **Different rig versions:** a pose saved on one rig version of a model can be applied to another version of the same
  model's rig when CPM can adapt it safely (for example, rigs with and without a chest control). The status then reads
  "Pose applied: <name>. Adapted to this character's rig."
- **Undo:** each Apply is one SFM Undo entry, "Apply Pose <name>".
- **Safety:** CPM checks the character before changing anything. If a pose can't be applied safely, it explains why
  and changes nothing.
- **Pose Info:** shows what a pose contains, where it was saved from, and the rig it was saved on.
- **Repeat Apply:** applying a pose the character already has changes nothing ("Already matches this pose.").

## Improvements

- Save New shows "Checking the character before saving." straight away while it checks the character.
- If an applied pose's evaluated result differs noticeably from the saved pose, CPM says so: "Pose keys applied, but
  the evaluated pose differs from the saved pose." Undo works as usual.

## Known limitations

- Poses apply only to the same model. Different models aren't retargeted.
- Rig adaptation covers simple control differences only, such as a chest control present on one rig version and not
  the other. Other rig differences are refused, with an explanation.
- Facial expressions (flexes) are not part of poses. Use Expressions for those.
- Simulated ear, hair and tail tips follow SFM's own simulation and may sit slightly differently.
- Apply works in the Motion Editor.
- Small differences of up to 0.1° or 0.01 units between a saved pose and the applied result are treated as a
  match.

## Upgrade and rollback

- **Upgrade:** install as for v1.0.0, by merging the ZIP's `usermod` folder into your SFM `game` folder. Your presets,
  expressions and Body Presets are kept.
- **Roll back:** install v1.0.0 the same way. Saved poses are kept and are ignored by v1.0.0.
