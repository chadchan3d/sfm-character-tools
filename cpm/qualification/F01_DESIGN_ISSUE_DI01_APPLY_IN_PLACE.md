# F01-DI-01: Apply in Place, anatomical pose translation versus character placement (2026-11-12)

**Status: UNRESOLVED design issue.** Recorded by the Owner's decision "F-01 — EF-1 Closure Decisions" (2026-11-12).
No behaviour is changed: pelvis translation stays in Full body, `rootTransform` stays untouched, and no new placement
rule is implemented. This is not an EF-1 failure; EF-1 run 2 is PASS (`F01_EF1_RESULTS.md`).

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

## 6. Constraints until decided

- No pose-engine, R3 or placement change. Pelvis translation stays in Full body; `rootTransform` is not altered.
- Operator instructions note that a large body-root movement after Apply is expected under R3 and is not by itself a
  STOP (`real_sfm_qualification/f01_ef1_full_body/PROCEDURE.md` B3, `PROCEDURE_CONTINUATION.md` step 5).
- Evidence: run 2 folder `E:\SFM_U0B_Scratch\f01-ef1-full-body-r2`, observations `S0-04.json` (B1) `d22439a8…` and
  `S0-06.json` (B3) `8ef36b7d…`; record `0e0390e0…`; inherited run-1 `S0-01.json`/`S0-02.json` (source rest and
  posed).
