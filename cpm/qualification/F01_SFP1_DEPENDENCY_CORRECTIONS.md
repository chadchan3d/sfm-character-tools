# F-01 SFP-1 — Final Dependency Corrections (A, B, C)

**Date:** 2026-11-08. **Authority:** Owner authorization after the `1bf1ab3` re-review: one offline correction round for
(A) cross-animation-set constraint dependencies, (B) channel-reader dependencies, (C) confined external prop
followers. Specification: R3, unchanged. The three `1bf1ab3` corrections are intact. **Status:** offline complete;
not natively qualified; nothing installed, enabled, pushed, merged, packaged or released.

## 1. What changed

One mechanism replaces the animation-set-local follower check: **document-wide precommit dependency tracing**.

- `prod_scope_dependency_index()` (called by `prod_scope_discover`, so every phase has it): the writer index's
  traversal (every film clip, its operators and its animation sets' operators, every channels clip), recording
  for each supported constraint its inputs (operator, target and slave elements), the DAGs it reads (targets, pole)
  and drives (slave targets); for each channel with a source, its source, destination and mode; every scene's DAG
  hierarchy and each transform's DAG. Unreadable reads, writes, modes, sources or destinations are recorded as
  unknown, never guessed. The legacy writer index (`prod_pose_writer_index`) is unchanged and still refuses unknown
  operator types document-wide.
- `prod_scope_dependencies(D, S)`: traces moving elements from the authorized inputs (affected bones, the written
  channels' source controls) through the known relationships only — DAG hierarchy, supported constraints, and
  channels (Pass; Play conservatively; Off has no effect; Record refuses because it would author data from a posed
  input; unknown/unreadable refuses when it can matter). Expression and pack-color operators are reached through
  their channels; no operator is interpreted and no constraint is solved. Chains are followed transitively,
  including ones that leave the character and re-enter it.
- Classification: affected bones through the hierarchy and excluded, confined bones (R3 4 one-way head-follow) move
  legitimately; any other bone, the model, a rig handle, a control, a channel or an operator element of the
  instance is protected and the scope refuses **before any write or Undo** (`shared-input`, naming it;
  `evidence-unreadable` when only an unknown effect reaches it; `structure-unsupported` for a Record reader).
  Elements outside the character are **external followers**: admitted, left under their own SFM relationships, not
  verified by CPM, and traced onward.
- Revalidation: the authority check (Save, P1, P2, P7) runs the tracing; the traced relationships
  `{confined, external, edges}` are part of the P1 state and compared exactly at P2 / Abort recovery (stale /
  recovery unverified) and at P7 (committed-unverified). No automatic compensating Undo.
- `prod_scope_followers` now returns the traced confined followers (the P7 exemption remains the R3 excluded
  subsystem only).

CPM `d9d8b359…` -> `a835161752639fefec36cdfdcce9e041e46f1f0f5f961416b7064ab68277b8cb`; R3 coverage, ownership, skeletal verification, v1/v2 code and production
gating are unchanged.

## 2. Counterexamples: before and after

Before = the new tests against `d9d8b359…` (Python 3.10.6): 288/324, the 36 failures all in the new section.
After: 324/324 on Python 2.7.5 and 3.10.6.

| Case | Before | After |
|---|---|---|
| Constraint in another animation set moving the unselected `tail` from posed `finger3` | admitted, written, committed-unverified (tail moved 193.6) | refused before writing (`shared-input`, names the bone) |
| Prop following a posed finger, constraint in the character's set / the shot | refused | applies and verifies (prop not verified by CPM) |
| Prop following, constraint in the prop's own set | applies | applies, now traced (not trusted: a return path refuses) |
| Prop dependency returning into the character (bone via another set or the character's set, a control via a channel, the model parented under the prop) | admitted | refused before writing |
| Multi-step chain: external only / re-entering the character | applies / admitted | applies / refused |
| Pass reader of a posed bone or a written source control driving a character bone; through an expression operator | admitted | refused before writing |
| Record-mode reader of a posed bone | admitted | refused (`structure-unsupported`) |
| Unrelated Pass channel; Pass of an unposed bone into a prop; posed bone into a prop; Off-mode reader | applies | applies |
| Harmless follower / return path appearing between P1 and P2 | applies / stale | stale / stale, no write |
| Return path or (modelled) Pass reader appearing before P7 | committed-unverified (from the moved bone) | committed-unverified, no automatic Undo |
| Harmless follower relationship appearing before P7 | committed-verified | committed-unverified (relationships changed since P1) |
| Constraint with unreadable reads driving a character bone; channel with unreadable mode or source reaching protected state | admitted | refused (`evidence-unreadable`) |
| Unreadable-read constraint driving only a prop | applies | applies |
| Unknown operator in another animation set | refused | refused |
| Previous counterexamples (index, follower, reparenting; AX1–AX3 rows) | closed | closed |

Pass tests model CM_PASS explicitly (`model_pass`: the source attribute is copied to the destination and the skeleton
re-solved after evaluation); none relies on the fake's default evaluation, which ignores non-Play channels.

## 3. Remaining unsupported dependency structures (refused or not verified, by design)

1. **External followers are not verified.** CPM applies the character pose and leaves admitted external followers
   under their SFM relationships; it does not claim their rendered pose.
2. **Element-level granularity.** A reader of any attribute of a moving element is treated as reading the motion;
   an expression or pack-color operator with any moving input is treated as moving all its outputs. Conservative:
   may refuse a harmless reader that reaches the character.
3. **Play-mode channels sourced from a moving element propagate** (conservatively); none exists in the observed native
   scenes (Krystal shot 13/15, MC-01, MC-02: no channel reads a bone or another channel's control).
4. **Unknown read sets** are treated as reading the pose; an unknown write set refuses when the operator may be
   relevant; unknown operator types refuse document-wide (unchanged).
5. **Rig handles and other instance elements parented under posed bones** refuse (bone-parented rig handles are not a
   supported capability in R3).
6. **Native relationship semantics** (Pass evaluation, constraint evaluation order) are modelled from SFM's channel
   modes and the supported constraint contracts; they are not natively qualified by this offline round.

## 4. Regression and gating

| Suite | `1bf1ab3` | this round |
|---|---|---|
| `test_cpm_app_f01_scoped.py` | 268/268 both | **324/324 both** (+55 AY checks, +1 section row) |
| `test_cpm_app_f01_scoped_page.py` (Qt, 2.7.5) | 12/12 | 12/12 |
| `test_cpm_app_f01_body.py` | 246/246 both | 246/246 both |
| `test_cpm_app_f01_pose_core/library/integration/live.py` | 255/87/204/104 both | identical |
| `test_cpm_app_f01_pose_page.py` (2.7.5) | 118/118 | 118/118 |
| `test_cpm_app_canonical_route.py` | 84/85 historical row | 84/85, same row; difference still only `PROD_EMPTY_STATE_GUIDANCE`, `prod_model_candidates` |

All CPM changes lie inside the scoped-pose block (11 of 11 hunks). Production experimental gates are unchanged
(`PROD_POSE_REGISTRY_MODE` production; `direct_fk_v1` experimental; `constant_channel_carried_v1` disabled).
