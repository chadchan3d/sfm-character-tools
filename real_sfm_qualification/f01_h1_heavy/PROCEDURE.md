# F-01 H1: native Heavy procedural-helper check (operator procedure)

**Status:** prepared offline, **not run**. Running it, and every installation change below, needs the Owner's separate
authorization.

**Authority:** Blueprint R4 sections 7 and 12 H; "F-01 H1 — Offline Closure and Native Readiness"; record
`cpm/qualification/F01_H1_HELPER_COMPATIBILITY.md`.

**What it checks (one SFM process, three fresh unrigged Heavies):** a visibly distinct Full body pose saved on Heavy A
(the source), reopened, and applied to Heavy B (the target) while Heavy C (the peer) stays untouched; useful arm and
body posture on B; the procedural forearm helpers follow naturally without severe distortion; B's own helper
animation, C and A unchanged; one Undo, one Redo and a true no-op. Transaction, Abort and recovery evidence is reused
from EF-1 and the offline suites (unchanged code); no Krystal, Engineer, Body Preset or UI campaign is repeated.

| Item | Value |
|---|---|
| H1 candidate CPM | `3d31e721…` (`7310171`) |
| Qualification build | `5a8c832b…` (one line, the registry mode) |
| Session | `H1_SESSION.dmx`: verified copy of the R2 fixture `259ea8a6…` (shot15, 0.2083 s; its Krystal is left alone); the Heavies are added in the session and it is never saved. `H1_SPARE.dmx` is copied by the reused pre and never opened |
| Capture | `observer/F01_H1_Capture.py` (read only; see `h1.template.json`) |
| Tool | `python -I <REPO>\real_sfm_qualification\f01_h1_heavy\tools\h1_tool.py <Q>\h1.json <command>` |
| Protected | `usermod\scripts`, `usermod\cfg`, the preset library, the SFM sessions folder; the published CPM `ccbed9d7…`, both registries absent, `.pyc` and housekeeping files |

**Never:** save the session; move the playhead or change the shot; apply a rig; move any Heavy bone other than
`bip_pelvis` (rotate only; moving other bones changes their attachment offsets and Apply refuses them); touch C after
creating it; use Update, Delete, Rename or Favorite; apply any other pose or preset; Undo or Redo more than listed.

## Preparation (Claude; SFM closed)

| # | Command | Expected |
|---|---|---|
| P0 | Copy `h1.template.json` to `<Q>\h1.json` (a new run folder); fill every `<...>` path. Change no pin. | |
| P1 | `build` | `BUILT: … 5a8c832b… differs from the candidate in line 42546 only` |
| P2 | `pre` | `PRE PASS (K2)`, then `PRE PASS (H1): preset library backed up` |
| P3 | `install`, then `check` | `"installation": "qualification"` |

## Native sequence (Owner, one SFM process)

Setup line, once after step 4 (use the three animation-set names SFM gave the Heavies in step 2):
```
H1_DIR = r"<Q>"; H1_SOURCE = "<A>"; H1_TARGET = "<B>"; H1_PEER = "<C>"
```
Capture line (only the step name changes; each step once):
```
H1_STEP = "BASE"; execfile(r"<REPO>\real_sfm_qualification\f01_h1_heavy\observer\F01_H1_Capture.py")
```
Each capture prints `H1 <step>: header … | helpers … | undo … redo … | errors … | written`.

1. Start SFM. **File > Open** `<Q>\sessions\H1_SESSION.dmx`. **Motion Editor**, shot15, playhead **0.2083 s** as
   opened (if not, STOP).
2. Animation Set Editor: **Create Animation Set for New Model** `models/player/heavy.mdl` **three times**. Note the
   three names (A source, B target, C peer). Apply no rig.
3. So all three can be seen, move each Heavy apart by its **rootTransform** only (placement; not saved in the pose).
   Then pose **A only**, with the rotate tool: bend both elbows strongly (`bip_lowerArm_L/R`), twist both hands
   (`bip_hand_L/R`), raise one upper arm, bend the spine, turn the head, bend one knee; optionally move `bip_pelvis`.
   Leave B and C in their default pose.
4. Open **Character Preset Manager**, **Refresh Models**, select **A**. Submit the setup line. Capture **BASE**
   (expected: `header 'READ'`, `helpers ['hlp_forearm_L', 'hlp_forearm_R']`, errors none). If the header is not READ
   or no helper is listed, capture nothing more, exit without saving and report (this is a safe refusal, not a pass).
5. **Poses: Save New → Full body**, name `Heavy H1`. Note the dialog's summary (expected to end with "Helper bones that
   SFM moves automatically follow the pose and may look slightly different.") and the result message. If Full body is
   refused, note the exact message, capture **SAVED**, exit without saving.
6. Select `Heavy H1` in the Poses list and open **Pose Info** (reopening the saved pose); close it. Capture **SAVED**.
7. In CPM select **B**. **Apply** `Heavy H1`. Note the message exactly. Capture **APPLY**.
8. **Inspect** (no capture): B's arms and body take A's pose; the forearms follow the bent elbows and twisted hands
   without severe twisting, pinching or detachment; C and A did not change. Note what you see (screenshots welcome).
9. **Edit** menu: it must read **Undo Apply Pose Heavy H1**; choose it once. Capture **UNDO**.
10. **Edit** menu: **Redo Apply Pose Heavy H1** once. Capture **REDO**.
11. With B still selected, **Apply** `Heavy H1` again (expected: nothing to change). Note the message. Capture **NOOP**.
12. Exit SFM **without saving**. Report each message, what you saw at step 8 and anything unexpected.

## STOP conditions

Exit SFM **without saving** and report; Claude still runs `library Q`, `collect-logs`, `restore`, `check`, `analyze`:
- a capture prints errors other than `none` or refuses;
- the Heavy is refused (header not READ, no helpers, or Full body refused): report the exact limitation;
- Apply writes to A or C, damages B's existing animation, fails a controlled limb or deforms severely;
- the Edit menu does not name `Apply Pose Heavy H1`, Undo or Redo does not restore, or a recovery message appears;
- anything is saved; SFM crashes, shows a recovery prompt or hangs for more than a minute.

A minor difference in a helper's appearance, or a small adjustment an artist would make, is not a STOP.

## Evidence, restoration and verdict (Claude; SFM closed; always)

| # | Command | Expected |
|---|---|---|
| R1 | `library Q` | the saved Heavy pose (and the Heavy's new character file) only |
| R2 | `collect-logs` | one CPM log |
| R3 | `restore`, then `check` | library cleanup exact, `RESTORED`; `"installation": "published"` |
| R4 | `analyze` | `H1_VERDICT.md` |

**Verdict** (`tools/h1_analyze.py`): **AUTOMATED PASS** when EVIDENCE, HEADER, SAVE, APPLY, UNDO and PEER all pass;
H1 is accepted only with it **and** the Owner's visual acceptance (step 8). **SAFE REFUSAL** when the known Heavy was
refused (header or Save): recorded as the exact limitation, **not** as a compatibility result. **FAIL** when the
evidence is complete and a functional gate fails. **INCOMPLETE** when evidence or restoration fails.
