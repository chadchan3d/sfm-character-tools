# F01-DI-01: Apply in Place, anatomical pose translation versus character placement (2026-11-12)

**Status: RESOLVED — RETAIN R3** (2026-11-12; "F-01 — Final F01-DI-01 Decision and Closure"). Astra's final ruling,
"RETAIN WITH MINOR REFINEMENTS", accepted by the Owner after independent and adversarial reviews by Astra and Fable.
The resolution is section 7. Sections 1–6 are the original record (opened by "F-01 — EF-1 Closure Decisions",
2026-11-12), kept as written. This was never an EF-1 failure; EF-1 run 2 remains CLOSED/PASS (`F01_EF1_RESULTS.md`).

## 1. What happened

In EF-1 run 2 (B3), applying the Full body pose `EF1 Body` to the destination Engineer moved the visible character
78.60 units, substantially downward and partly out of the camera framing. CPM did exactly what R3 specifies.

## 2. Current R3 behaviour

- **Placement is preserved.** R3 uses the verified model placement transform (`rootTransform`) as the reference
  frame and preserves its channels, values and scale (Blueprint R3 lines 26 and 192).
- **The anatomical root's translation is pose data.** In Full body, the single anatomical root directly under the
  model frame (`bip_pelvis` on the Engineer) takes its saved **model-relative** translation: "allowing crouching/body
  offset without moving the model placement transform" (line 194). Selected parts never transfers it (line 196).
- **Consequence:** the saved translation is reproduced in the destination's model frame, wherever and however that
  frame is placed. The visible displacement is the destination placement's rotation applied to
  (saved pelvis − destination pelvis).

## 3. The EF-1 measurements (native, run 2)

| Quantity | Value |
|---|---|
| `rootTransform`, B1 through B10 | unchanged: position (48.504, 27.993, −38.444), orientation (−0.45733, 0, 0.8893, 0) |
| Saved `bip_pelvis` local translation (record `0e0390e0…`) | (72.418, 0.000, 51.434) |
| Destination `bip_pelvis` local translation (B1) | (0.000, −20.177, 28.486) |
| After the Apply (B3) | (72.418, 0.000, 51.434); differs from the saved value by 0.0 |
| Model-frame displacement | (72.418, 20.177, 22.948), **78.60 units** |
| World displacement | (−60.79, −20.18, **−45.56**), 78.60 units; equals placement × local to 2e-6 |
| Lowest bone (world z) | B1 −55.11 (`bip_toe_L`) → B3 −107.98 (`bip_toe_R`) |
| Highest bone (world z) | B1 +5.42 → B3 −37.88 (`prp_helmet`) |

**Where the saved translation came from:** run 1's Process A posing. The source pelvis moved from its pre-posing baseline (A1:
(0, 0, 41.344)) to the saved value: 73.12 units, 72.42 along model +X and 10.09 up. The destination's own pelvis was
23.93 units from that baseline.

**Why it reads as "down":** the source model was upright (model +X → world (−1, 0, 0), up → up), so the saved offset
was mostly horizontal there. The destination's placement is turned and tilted: model +X → world (−0.58, 0, −0.81), and
model up is 54° from world up. The same model-frame offset therefore points largely downward in the destination.

## 4. The tension

- **Artist expectation (the Owner's principle):** "A saved pose should normally apply to the character where the
  artist has placed it."
- **Legitimate pelvis movement must remain available:** crouching, jumping, leaning and weight shifts are expressed
  through the pelvis translation, and dropping it would flatten those poses.
- R3 treats placement as `rootTransform` only. In SFM practice artists also place characters by moving the pelvis, so
  a pose's pelvis offset can mix anatomical posture with the placement the artist gave the source character.

## 5. Design question for Astra

> Under R3, Full body Apply preserves the model placement (`rootTransform`) and writes the anatomical root's saved
> model-relative translation. On the Engineer (EF-1 run 2) that moved the visible character 78.60 units (world
> −45.56 in z) because the source pose carried a 73.1-unit pelvis offset created during posing, and the destination's
> placement is rotated and tilted relative to the source's.
>
> How should a Full body pose separate **anatomical pose translation** (crouch, jump, lean, weight shift) from
> **character placement** (where the artist put the character), so that a pose normally applies where the
> destination character already stands, without losing legitimate pelvis movement?
>
> In particular:
> 1. What reference should the pelvis translation be relative to: the model frame (current), the model's rest pelvis,
>    the destination's current pelvis, or a ground/contact reference? And in which frame are horizontal and vertical
>    components interpreted when the destination placement is tilted?
> 2. Should horizontal and vertical components be treated differently (for example, keep the destination's
>    horizontal pelvis position and transfer height/lean), and how does that hold for a jump or a lying pose?
> 3. Should "apply in place" be the default with the current behaviour as an explicit option, or the reverse? What
>    does the Save dialog record so that Apply can tell the two apart without guessing?
> 4. How do existing version 3 records (which store only the model-relative root translation) behave under any new
>    rule, given that R3 records must not be reinterpreted silently?
> 5. Which native evidence would qualify the answer (for example, EF-1's fixtures with the destination placement
>    tilted, plus an upright destination and a crouch pose)?

## 6. Constraints until decided (as recorded while open)

- No pose-engine, R3 or placement change. Pelvis translation stays in Full body; `rootTransform` is not altered.
- Operator instructions note that a large body-root movement after Apply is expected under R3 and is not by itself a
  STOP (`real_sfm_qualification/f01_ef1_full_body/PROCEDURE.md` B3, `PROCEDURE_CONTINUATION.md` step 5).
- Evidence: run 2 folder `E:\SFM_U0B_Scratch\f01-ef1-full-body-r2`, observations `S0-04.json` (B1) `d22439a8…` and
  `S0-06.json` (B3) `8ef36b7d…`; record `0e0390e0…`; inherited run-1 `S0-01.json`/`S0-02.json` (source rest and
  posed).

## 7. Resolution: RETAIN R3 (2026-11-12)

**Ruling (Astra, final; accepted by the Owner): RETAIN WITH MINOR REFINEMENTS.** Generic v3 Full body Apply continues
to:
- preserve the destination's `rootTransform`;
- apply the saved pelvis translation and rotation;
- apply the other authorized skeletal pose controls;
- preserve the destination's non-root structural offsets;
- preserve unrelated animation and the existing transaction safeguards.

**Artist-facing principle:** a Full body pose reproduces the saved skeletal arrangement, including pelvis movement,
relative to the destination character's existing scene root. Pelvis translation is a legitimate part of crouching,
sitting, jumping, leaning, lunging and weight-shift poses. This supersedes the provisional principle in section 4
("A saved pose should normally apply to the character where the artist has placed it"), which is kept above as the
original concern.

**Superseded alternatives (rejected):**
- *Preserve the destination pelvis position by default.* Astra's initial recommendation, withdrawn on
  reconsideration: it sacrifices legitimate pelvis movement.
- *Transfer saved pelvis height, keep the destination's horizontal pelvis position* (Fable). Rejected: horizontal
  pelvis movement is also legitimate posing information, particularly for leaning, lunging and weight shifts.
- Neither improves normal Full body posing enough to justify changing the qualified engine.

**Interpretation of EF-1:** the 78.60-unit displacement came from transferring an unusually large saved pelvis
translation (run 1's 73.1-unit Process A offset) into a tilted destination model frame. It was correct under R3. It
shows a known limitation (CPM cannot infer whether an artist used pelvis translation for posing or for incidental
placement); it does not establish a defect in the default Full body workflow. **EF-1 remains CLOSED/PASS; no
qualification correction or retest.** EF-1's observations, verdict and native evidence are not rewritten.

**Later option, not current scope:** optional pose matching (for example, a choice to keep the destination's pelvis
position) may be considered later if actual artist workflows establish a recurring need. It is not part of the
current F-01 implementation.

**Minor refinement, wording only (Owner-accepted):** the version 3 Full body interface text said what is not saved as
"the character's place in the scene" / "scene placement", which can be read as a promise that the visible body stays
where it is. Corrected so that it names hip movement as included and the `rootTransform` as what stays:

| Where | Before | After |
|---|---|---|
| Save Pose dialog, Full body summary (`prod_scope_summary`) | "Facial expressions and the character's place in the scene are not saved." | "Includes hip movement. Facial expressions and the character's rootTransform are not saved." |
| Pose Info, Includes (v3 Full body) | "Full body" | "Full body, including hip movement" |
| Pose Info, Not included (v3 Full body, `PROD_POSE_FULL_BODY_NOT_INCLUDED[3]`) | "Facial expressions, scene placement" | "Facial expressions, rootTransform" |

Unchanged on purpose: the Apply messages ("Pose applied: …", "Already matches this pose.") make no placement claim;
Selected parts' "The body root keeps its position." is accurate (Selected parts never transfers root translation);
the legacy version 2 (registry) Full body wording belongs to a different, separately qualified route. No placement
selector, warning, threshold, extra pane or recurring explanation was added.

**CPM identity:** the wording successor is `bb70cce26a65b069b5e44cf3e89bfe01ae06acfe5dee99a577632d997ed8211d`, which
differs from the natively qualified `3da2b6537d67bc4c55ae7952f24f86ec61ea4f51b2c6721078a3a159a466a35d` in those three
string lines plus one comment, nothing else. **It is not the binary tested in EF-1;** EF-1 PASS stays tied to
`3da2b653…` (qualification build `bb0433a9…`). The EF-1 kit's build test now reads that exact source from its pinned
commit `19e8f68` and still requires both original hashes. Pose semantics, record versions, tolerances, write scope,
Undo/Redo, Abort, P7 and the comparator are unchanged.
