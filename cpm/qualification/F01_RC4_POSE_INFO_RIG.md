# F-01 RC4: Pose Info "Rig" row (implemented offline, not native-tested)

**Authority:** Astra's RC4 ruling section 4 and "F-01 RC4 — Astra Ruling and Implementation Authorization" section 4.
Kept separate from the adaptation logic (`F01_RC4_CROSS_RIG_ADAPTATION.md`).

**What is recorded.** At Save New and Update Pose, CPM reads the scene rig element registered to the saved instance.
It stores `{label, scene}` in a local per-character sidecar, `pose_rigs.json`, keyed by the pose identity, exactly
like Source project. The portable pose record is unchanged, and nothing about it is part of a shared pose file.

**What Pose Info shows.** A "Rig:" row after "Model path:":

| Recorded | Shown |
|---|---|
| A scene name ending exactly in `_<animation set>` (the rig scripts' naming) | That suffix removed, for example `rig_biped` |
| Any other usable scene name | The name as it is |
| An unusable name (control characters, over 256 characters) | `Custom rig` |
| No rig registration | `No rig` |
| Several registrations, an unreadable scene, an older pose, or a damaged sidecar | `Not recorded` |

The tooltip gives the scene name. It says this is not the script that built the rig, and that a matching name doesn't
mean a pose will apply.

**What it never does.** It never identifies the rig script and never decides compatibility. Apply never reads it.
Recording never fails a Save or Update, and a damaged sidecar is never overwritten.

**Evidence.** `test_cpm_app_f01_structural_rig.py` section I: 23 checks, suite 337/337 on Python 2.7.5 and 3.10.6. The
names are registered in the stage B and C sets of `test_cpm_app_canonical_route.py`. Full regression: only the new
checks differ, plus the known environmental r15 working-copy item.
