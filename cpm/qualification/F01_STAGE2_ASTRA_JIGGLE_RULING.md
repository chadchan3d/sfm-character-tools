# F-01 Stage 2: Astra's ruling on leaf JIGGLE bones (recorded 2026-11-19)

## 1. Provenance

- **Source:** Astra's adjudication of `F01_BROAD_FULL_BODY_COMPATIBILITY_REVIEW.md` (2026-11-18), disposition
  **ACCEPT WITH CONDITIONS**. Stage 1 (generic structural rig support) was authorized under the same disposition
  (`F01_STAGE1_STRUCTURAL_RIG_SUPPORT.md`, Authority).
- **How it reached the repository:** the ruling was preserved in the Owner/Designer conversation. Its Stage 2
  provisions were reproduced by the Owner/Designer in "F-01 Stage 2 — Recover Astra's Existing Ruling" on 2026-11-19.
  Until then, the repository recorded only the disposition and the questions put to Astra.
- **Status:** this is the original adjudication, not a new design proposal and not a new adjudication. No further
  Astra adjudication was requested.

The quotations below are verbatim as reproduced. Only Astra's Stage 2 provisions are recorded here. The Stage 1
provisions are reflected in the Stage 1 authorization and record.

## 2. Astra's ruling (verbatim)

### Jiggle leaves

> "Accept Option 2 with a specific correction. A declared, control-less JIGGLE leaf may remain under normal SFM
> control when model/header identity agrees, authored channels are preserved, and relevant attachment, flex-driver
> and scene dependencies establish its isolation. A qualified rig-driven parent is acceptable.
>
> Do not simply classify it as today’s v2 passive bone. That class checks unchanged local transforms and inherited
> expected world transforms. Simulation can legitimately violate both. Introduce the narrow output exemption
> throughout capture compatibility, no-op, P2, P7 and recovery comparisons, while retaining authored-state and
> configuration checks.
>
> Leaf status does not guarantee a visually minor effect. Tails’ acceptance must still establish useful posture and
> absence of severe deformation. Non-leaf jiggle chains and unsupported physics relationships can remain excluded
> from this first implementation."

### Native qualification

> "Tails: Exercise the same adapter with its jiggle exception, verify meaningful posture, unchanged helper authorship
> and acceptable visible results. Include navigation and history restoration without demanding identical simulated
> tip transforms."

## 3. Design implications stated with the recovered ruling (Owner/Designer)

- Tails' seven leaf JIGGLE bones are the initial case, not a character-specific whitelist.
- Reuse the qualified Stage 1 structural rig adapter.
- Allow supported simulated leaf outputs to follow SFM naturally.
- Preserve authored helper channels, keys, configuration and relevant dependency safeguards.
- Do not require identical simulated bone positions or rotations.
- Do not silently omit meaningful body articulation.
- Do not implement a general physics or procedural-bone system.
- Do not replace Krystal's existing qualified route.

**Owner's priority:** "A useful, faithful Full body pose is preferable to refusing an otherwise compatible character
because minor secondary bones cannot be reproduced exactly."

## 4. Astra's ruling compared with Claude's proposal

Claude's proposal is `F01_BROAD_FULL_BODY_COMPATIBILITY_REVIEW.md` section E, Option 2, with question F.3 and the
hypothesis H-2. It is analysis submitted for adjudication and carries no authority of its own. Where the two differ,
**the ruling governs**.

| Point | Claude's proposal (2026-11-18) | Astra's ruling |
|---|---|---|
| Admission | A control-less **leaf** declared `JIGGLE`, "under H1's existing conditions": the header matches the scene, a direct-FK or rig-driven parent, no children, no attachment or flex-driver use, and no physics or screen-align flags. | **Accepted, with a correction.** Model and header identity must agree, authored channels must be preserved, and relevant attachment, flex-driver **and scene** dependencies must establish isolation. A qualified rig-driven parent is acceptable. |
| Class | H-2: "Tails' jiggle leaves would pass v2's existing `passive` class (one source-less channel per attribute)." | **Rejected.** "Do not simply classify it as today’s v2 passive bone." The `passive` class checks unchanged local transforms and inherited expected world transforms, and simulation can legitimately violate both. |
| What is exempted | "Never write it, keep its channels in the preservation checks, and exclude only its rendered result." | A **narrow output exemption throughout capture compatibility, no-op, P2, P7 and recovery comparisons**, while authored-state **and configuration** checks are retained. |
| Visual effect | Not addressed; the proposal treated jiggle differences as harmless (question F.5). | "Leaf status does not guarantee a visually minor effect." Tails' acceptance must establish useful posture and the absence of severe deformation. |
| Exclusions | Asked whether non-leaf chains and physics-flagged bones must keep refusing (F.3). | Non-leaf jiggle chains and unsupported physics relationships **can remain excluded** from this first implementation. |
| Native evidence | One native check on Tails for the jiggle leaves (F.4). | Tails, through **the same adapter**: meaningful posture, unchanged helper authorship, acceptable visible results, and navigation and history restoration **without identical simulated tip transforms**. |

## 5. Use

The bounded Stage 2 implementation scope is prepared from this ruling in `F01_STAGE2_JIGGLE_LEAF_SCOPE.md`.
Implementation needs the Owner's separate authorization.
