# F-01 SFP-1 — NQ-S6: Procedural State of Control-less Bones (Focused Investigation)

**Date:** 2026-11-08. **Status:** CLOSED. Offline investigation complete; the bounded read-only native observation
**ran on 2026-11-08 with a clean postflight** (section 7). Outcome: the Heavy's helpers are **declared procedural**.
No production code changed, nothing enabled, installed, pushed, merged or released. `constant_channel_carried_v1`
stays disabled and its refusal stands. Sections 1–6 are the pre-observation record, unchanged.

## 1. Question

Can CPM admit the TF2 Heavy's control-less forearm helpers (`hlp_forearm_L/R`) under R3 3.1, which requires positive,
readable procedural-state evidence: procedural evaluation verifiably disabled for the model, or authoritative
per-bone evidence that excludes a procedural override, plus a supported constant/extrapolation contract?

## 2. Verified findings (offline, from shipped sources and existing evidence)

1. **`evaluateProceduralBones` is model-wide.** SFM's bindings (`vs/movieobjects.py`, `CDmeGameModel`) expose only
   `SetEvaluateProceduralBones(bool)` and `ShouldEvaluateProceduralBones() -> bool`; no per-bone variant exists. All
   three survey observations record the attribute as `true` (MC-01, MC-02, MC-03, `mc.game_model_attributes`). A
   model-wide `true` says procedural evaluation is enabled for whatever the model declares procedural; it does not
   say which bones those are. (R3 Appendix A's "does not record its value" refers to S0's model state; the survey's
   attribute dump does record it.)
2. **SFM ships a per-bone, engine-side declaration.** `CDmeGameModel.GetStudioHdr()` returns the engine-loaded
   `studiohdr_t`; `studiohdr_t.pBone(i)` returns `mstudiobone_t` with `proctype` (0, or one of `STUDIO_PROC_AXISINTERP`,
   `QUATINTERP`, `AIMATBONE`, `AIMATATTACH`, `JIGGLE`, `TWIST_MASTER`, `TWIST_SLAVE`, `POINT/ORIENT/AIM_CONSTRAINT`),
   `procindex` and `flags` (`BONE_ALWAYS_PROCEDURAL`, `BONE_PHYSICS_PROCEDURAL`, `BONE_PHYSICALLY_SIMULATED`,
   screen-align flags). This is the compiled model's own data as loaded by the engine, read through a shipped
   interface — not a model-file parser.
3. **That read path works inside SFM.** CPM itself calls `game_model.GetStudioHdr()` natively for its model identity
   checksum (published CPM and the current source). The Owner's other local SFM scripts read `hdr.numbones`,
   `hdr.pBone(i).pszName()`, `proctype` and the flag bits the same way. Neither has yet been applied to the Heavy's or
   Ayane's bones, so **the values for these models are not observed**.
4. **The rendered procedural result is not readable.** No supported Python reader returns the engine-evaluated bone
   matrices of an in-scene game model (`CDmeMDL.SetUpBones` belongs to preview MDL shapes and needs raw matrix
   buffers). CPM reads DME transforms (`GetAbsPosition`/`GetAbsOrientation`); for a procedural bone those hold the
   channel value, not what the engine draws. A community script shipped in this installation describes disabling
   Procedural Bones to stop jiggle and *baking* them into channels, consistent with procedural results living outside
   the DME channels — corroboration only.
5. **A procedural helper's driver is not readable through a supported interface.** The typed records exist
   (`mstudioquatinterpbone_t.control`, `mstudioaxisinterpbone_t`, `mstudiojigglebone_t`, `mstudiotwistbone_t`), but
   `mstudiobone_t.pProcedure()` returns an untyped `void*` with no shipped cast. `proctype` and `procindex` are
   readable; which bone drives a helper is not.
6. **No log extrapolation contract exists.** The DME log API has no extrapolation mode (the hold/infinite calls belong
   to time selections). MC-01's helper logs hold 20 identical keys at ticks 0–9500, evaluated at tick 50000; their
   value there equals the keys (one evaluation). M-06's natively qualified one-key static flex class shows a one-key
   float log evaluating to its key away from it; nothing qualified shows constant evaluation beyond the last key for
   vector or quaternion logs with several keys.
7. **Defaults:** MC-01 records `usedefaultvalue = false` with `defaultvalue` = identity, which differs from the
   helpers' constant. Whether `CDmeLog.HasDefaultValue()` (what CPM's snapshot reads) follows `usedefaultvalue` is not
   established; if it reports `true`, the current admission check would refuse on a disabled default. The
   observation records both.

## 3. Unresolved assumptions

- The Heavy's helpers are *probably* declared procedural (TF2 `hlp_` bones are conventionally quaternion-interpolation
  helpers). **Not verified**; it is exactly what NQ-01 reads.
- That `proctype == 0` with no procedural flags means the engine never overrides a bone while
  `evaluateProceduralBones` is `true` (engine semantics, not an SFM-documented contract).
- Constant extrapolation for vector/quaternion logs beyond the last key.
- `HasDefaultValue()` versus `usedefaultvalue`.

## 4. The bounded native observation (prepared)

`real_sfm_qualification/f01_nq_s6/`: observer `F01_NQS6_Observe.py` (`1ac46682…`, wraps the pinned S0 observer inside
its read-only digest window), `tools/nq_tool.py` (the model survey's `mc_tool` reused unchanged for pre/status/post,
plus a verified session copy and the preserved original's hash check), `tools/nq_analyze.py`, offline tests 7/7
(Python 2.7.5 and 3.10.6), `PROCEDURE.md`. Two observations on a verified copy of the preserved survey session:
NQ-01 `heavy1`, NQ-02 `ayane_dazv51` (jiggle bones as the contrast). About ten minutes of SFM time; no flag change,
no key, no Apply, never saved. Preconditions checked read-only today: published CPM installed with no registry beside
it, kit pins, both models present, the preserved session at its pinned bytes.

## 5. Functional consequence

| NQ-01 outcome for `hlp_forearm_L/R` | Consequence |
|---|---|
| **Declared procedural** (`proctype` ≠ 0 or a procedural flag) — expected | They are engine-derived outputs. R3 3.1 forbids relabeling a procedural output as fixed, so `constant_channel_carried_v1` must refuse them permanently, and **no v3 Full body of the unrigged Heavy is possible under R3 as written.** Admitting them would need a new, explicitly reviewed role ("engine-procedural derived bone": never written, its declaration read from the studio header, its rendered result outside the DME oracle). Two facts limit that role today: the rendered result is not observable (finding 4) and the driver is not readable (finding 5), so it would rest on the engine declaration plus Owner visual confirmation. That is an **architectural decision** (an R3 amendment), not an implementation gap. |
| **No declaration** (`proctype` 0, no procedural flag) | Per-bone evidence then excludes a procedural override. The guard becomes implementable from the studio header (a small change: read the declaration per candidate bone; unreadable refuses). Still open before enabling: extrapolation (NQ samples are corroboration; a qualified contract or a destination with a key at the pose time is needed), the `HasDefaultValue` question, and R3 12's carried-state qualification (parent pose change, navigation, Undo/Redo). That is **implementation plus native qualification.** |
| **Unreadable** | The refusal stands; the dependency is the reader itself. |

Not proposed, in any case: omitting the helpers, or reclassifying them as facial exclusions.

**A different representative model.** v3 Full body needs a model whose every bone is direct FK (one control per
bone) or a qualified carried class, with no rig constraints. None of the surveyed models qualifies: Krystal is rigged
(21 constrained bones) and has two source-less twist bones; MC-01/MC-02 have the two helpers; Ayane is rigged and has
eight jiggle bones. A model whose studio header declares **no** procedural bones and whose animation set gives every
bone a control would qualify under the existing rules with no new capability. The observer reads exactly that
declaration, so one extra observation on a candidate model (added to the session copy) would settle a candidate in
the same run, if the Owner names one.

## 6. Answers

1. **Findings / assumptions:** sections 2 and 3.
2. **Is `constant_channel_carried_v1` admission feasible with available interfaces?** Only if the Heavy's header
   declares the helpers non-procedural; the per-bone declaration is readable through a supported interface, the
   rendered result and the driver are not. If they are declared procedural (expected), admission is infeasible by
   contract.
3. **Kind of remaining work:** one native read (NQ-01). Then either an architectural decision (procedural helpers:
   an R3 amendment for derived procedural bones) or implementation plus native qualification (non-procedural
   helpers). For a different, fully direct-FK model without procedural declarations: native qualification only.
4. **Smallest next action:** run the prepared NQ-S6 observation (steps 0–5 of `PROCEDURE.md`), optionally with one
   Owner-chosen candidate model that has no rig.
5. **Implementation review readiness:** unchanged. SFP-1 stages A/B (`abe58bb`, CPM `54e2028d…`) remain ready for
   review; this investigation changes no production code.

## 7. Native observation results (2026-11-08)

**Run.** Owner-operated, per `real_sfm_qualification/f01_nq_s6/PROCEDURE.md`, on a verified copy of the preserved
survey session. Preflight `PRE PASS`; `COPY PASS` (copy `47f6b9a0…`, 547,388 bytes). Both observations `OK`,
`readonly=True`, `problems=0`, `findings=0`; the copy was never saved. Postflight `POST PASS` (the four protected
inventories — scripts, `usermod/cfg`, the CPM library, sessions — equal their baselines; SFM's two housekeeping files
`demoheader.tmp` and `tf2_playerstats.dmx` were put back under the existing procedure; no session written) and
`SESSION CHECK PASS` (the preserved original `mc_survey.dmx` still `47f6b9a047b02462…`). No stop condition occurred.

| Evidence (run folder, not committed) | SHA-256 |
|---|---|
| `observations/NQ-01.json` (`heavy1`) | `9f5851269d8f0f7daba59d43080a6bdca248a9f3d2f26fdc020ade256cc44d18` |
| `observations/NQ-02.json` (`ayane_dazv51`) | `7da8dc4649ccde76cd3fd2fd61d1de0da3910ace5c8ce0f60c5fea60f4d93f6f` |
| `evidence/NQ_S6_ANALYSIS.json` | `c1656974a5a35db654c0b85aaae1aab3a895abaf9c641bf071c1c0b511f4c0cb` |
| `evidence/NQ_S6_ANALYSIS.md` | `0f45704c01abd3d80ecf8afcfa3838b37481959b156a3d04ef3c2205e7dc8fe8` |
| `evidence/post.json` | `82a68ff344129d8483e228710749a78238deff256df26ecd3482fa55620b8eac` |
| `evidence/session_check.json` | `f24fb85e03d8bb9d6ec5f817d63366a4698351c8e538b80235dcd9ce67437ecc` |

**Declared by the engine-loaded model** (`GetStudioHdr().pBone(i)`; header and scene bones join by index and name
with no problems on both models; `ShouldEvaluateProceduralBones()` and the attribute both `True`):

| Model | Header = scene bones | Declared procedural (all) | `proctype` | `flags` |
|---|---|---|---|---|
| Heavy `models/player/heavy.mdl` | 79 = 79 | `hlp_forearm_L` (77, parent 11 `bip_lowerArm_L`, `procindex` 432), `hlp_forearm_R` (78, parent 12 `bip_lowerArm_R`, `procindex` 228) | 2 `STUDIO_PROC_QUATINTERP` | 7172 = 0x1C04: `BONE_ALWAYS_PROCEDURAL` (0x04) plus bits inside `BONE_USED_MASK` |
| Ayane `ayane_dazv5.mdl` | 165 = 165 | the eight `ValveBiped.Bip01_{L,R}_{Breast,Butt}{0,1}_jiggle` | 5 `STUDIO_PROC_JIGGLE` | 1284 = 0x504: `BONE_ALWAYS_PROCEDURAL` plus used bits |

On both models the control-less (source-less channel) bones are **exactly** the declared-procedural bones (Heavy 2/2,
Ayane 8/8); every one classifies `declared-procedural`. Both Heavy helpers are leaves (no child bones).

**Observed in the DME channels** (corroboration, not a contract): each of the 20 helper/jiggle channels holds 20
identical keys over ticks 0–9500 and evaluated to that constant at every sample (−1,000,000; 0; 9500; 9501; 50091;
500910; 100,000,000). `usedefaultvalue = False` and `CDmeLog.HasDefaultValue() = False` on every one, which closes the
section 3 `HasDefaultValue` question for these logs. Ayane's jiggle bones visibly move when rendered, yet their channels
are equally constant: constant channels do not show a fixed rendered bone. The rendered result remains unreadable.

**Consequence (section 5, first row).** The helpers are engine-derived outputs. Under R3 3.1
`constant_channel_carried_v1` must refuse them permanently; **no v3 Full body of the unrigged Heavy is possible under R3
as written.** A nonprocedural declaration was not found, so nothing here bears on admitting a nonprocedural bone. No
workaround is implemented or proposed; Heavy admission would need a separately approved category and R3 amendment.

**Next (Owner direction, 2026-11-08):** the Owner accepted Astra's bounded assessment as the architectural direction
and authorized a read-only feasibility assessment of a separate `engine_derived_quatinterp_v1` category (no Heavy
admission, code change or R3 amendment): `cpm/qualification/F01_SFP1_QUATINTERP_FEASIBILITY.md`.
