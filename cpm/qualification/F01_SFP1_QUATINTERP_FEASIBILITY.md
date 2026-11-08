# F-01 SFP-1 — `engine_derived_quatinterp_v1`: Contract Feasibility and the First Generic Full-Body Route

**Date:** 2026-11-08. **Status:** read-only assessment complete. **Verdict: the QUATINTERP contract cannot be established
through supported, read-only interfaces; the assessment stops here (Owner instruction 3).** No CPM code, no R3
amendment, no Heavy admission, nothing launched, installed, enabled, pushed, merged or released. Inputs:
`F01_SFP1_NQ_S6_INVESTIGATION.md` section 7 (NQ-S6 native results), the installed SFM Python bindings, Valve's shipped
model-pipeline scripts and Valve's public Source SDK 2013 reference.

## 1. Sources examined

| Source | Identity | Use |
|---|---|---|
| SFM bindings `sdktools/python/2.7/win32/Lib/site-packages/vs/studio.py` | `6e986690…` | every studio type and accessor exposed to Python |
| SFM bindings `vs/movieobjects.py` | (unchanged since NQ-S6) | `CDmeGameModel` procedural switch, `CDmeMDL.SetUpBones` |
| Valve pipeline `sdktools/python/global/lib/site-packages/modelpipeline/asset.py`, `assembly.py` | `70da1d1a…`, `808a14c1…` | Valve's own read path for compiled-model bone declarations |
| Source SDK 2013 (`ValveSoftware/source-sdk-2013`, `e1f1fd42…`): `src/public/bone_setup.cpp`, `src/public/studio.h`, `src/game/client/c_baseanimating.cpp` | `5bb690ee…`, `cf5ac8bb…`, `94fc2886…` | the reference `DoQuatInterpBone` / `CalcProceduralBone`; read only, not vendored |
| Installed `.vrd` files (procedural-bone sources) | 11 files, all third-party community content under `usermod` | none is for `heavy.mdl` |

## 2. What the reference implementation says the contract is

`CalcProceduralBone` (bone_setup.cpp) runs a bone's procedure only when `BONE_ALWAYS_PROCEDURAL` is set, and
dispatches `STUDIO_PROC_QUATINTERP` to `DoQuatInterpBone` (line 4700). That function:

1. reads `mstudioquatinterpbone_t` through `pProcedure()` — `control` (the driver bone), `numtriggers`, and per trigger
   `mstudioquatinterpinfo_t` {`inv_tolerance`, `trigger` quaternion, `pos`, `quat`};
2. takes the driver's **local** rotation relative to the driver's parent, weights each trigger by angular distance,
   and blends the triggers' `pos`/`quat` into the helper's local transform;
3. writes `parent_world × blended_local` into the helper's own bone-to-world slot **only**; the helper's animated
   (DME/channel) value is not consulted;
4. fallbacks: when no trigger has weight (`scale <= 0.001`, line 4735) it uses trigger 0's pose; when the record is
   absent or the driver is a root bone (line 4709) it concatenates an **uninitialized** local matrix — undefined.

In the client (`c_baseanimating.cpp`), procedural bones skip the animated-pose path entirely.

## 3. Feasibility, element by element

| Contract element | Needed for a qualified category | Supported read-only interface? | Result |
|---|---|---|---|
| **Driver relationship** (`control`) | which bone's local rotation the helper follows; the verifier and scope boundary depend on it | **No.** `mstudioquatinterpbone_t.control` is bound, but no function returns an `mstudioquatinterpbone_t`. `mstudiobone_t.pProcedure()` returns an opaque `void *` (studio.py 924); SWIG does not convert `void *` to a typed pointer; `procindex` (432, 228) is a byte offset from the bone record. Reaching the record needs address arithmetic, `ctypes`, or rebinding a proxy's `this` | **Not establishable** |
| **Procedural configuration** (triggers: `inv_tolerance`, `trigger`, `pos`, `quat`) | expected output for any driver pose | **No**; same record (`pTrigger(i)` only on the unreachable type). The bound field names match the SDK layout (`trigger` included), which corroborates the definition, not reachability | **Not establishable** |
| **Output confinement** | proof the procedure writes nothing a scoped pose owns | **Partial.** Header parent indices (read in NQ-01) show both helpers are leaves: no bone inherits their write. Other consumers are readable but not yet observed: attachments (`mstudioattachment_t.localbone`), bone-flex drivers (`BoneFlexDriver(i).m_nBoneIndex`), hitboxes (`mstudiobbox_t.bone`). Mesh skinning to the helper (its visual purpose) needs vertex-buffer access. The written result itself is unreadable (NQ-S6 finding 4) | **Hierarchy only; output unobservable** |
| **Fallback behaviour** | what is drawn when no trigger matches, the record is missing, or `evaluateProceduralBones` is false | **No.** The reference shows trigger-0 and undefined fallbacks, but SFM's game-model bone setup and its `ShouldEvaluateProceduralBones` gate are not in the SDK (no `EvaluateProcedural` in `c_baseanimating.cpp`); the installed binary's behaviour is undocumented | **Not establishable** |

Supported and readable today: the declaration (`proctype`, `flags`, `procindex` as a number), the parent/leaf
structure, and the model-wide switch. Valve's own pipeline (`asset.py` 775–800, `assembly.py` 20–45) reads exactly that
and **excludes `BONE_ALWAYS_PROCEDURAL` bones from its joint lists** — corroboration that the declaration is the
supported boundary, not a contract for the procedure.

## 4. Verdict and precise limitation

**`engine_derived_quatinterp_v1` cannot be qualified as a contract.** Three of four elements (driver, configuration,
fallback) are reachable only through unsupported pointer access to the record behind `pProcedure()`, a binary reading
of the compiled model, or assumptions that the SDK 2013 reference matches SFM's undocumented game-model evaluation.
The fourth (confinement) is established structurally only; the engine's output is not observable. Per instruction 3
the assessment stops: no workaround, cast, parser or experimental reader was built or tried natively.

What a category could rest on, if Astra and the Owner choose to design one: the engine declaration, leaf status and
the absence of other consumers (readable), and Valve's own pipeline convention. It could not verify the helper's
rendered pose. That is a design decision, not proposed here.

## 5. Route to the first generic v3 Full body

Heavy remains unsupported. The fastest route needs no new capability: **a stock, unrigged model whose studio header
declares no procedural bone**. NQ-S6 corroborates (two models, all bones) that SFM gives a control to every bone
except the declared-procedural ones, so such a model's animation set should be fully direct FK; the qualification
session confirms it.

**Proposed next read-only native observation — focused header inventory (NQ-03), prepared on approval, not built:**

- **Interface:** `vs.studio.g_pMDLCache.FindMDL(path)` → `GetStudioHdr(handle)` → `pBone(i)` (`proctype`, `flags`,
  `parent`, name) plus attachments, bone-flex drivers and hitbox bones → `Release(handle)`; the pattern Valve's
  `modelpipeline/asset.py` ships. No scene element is created; the model loads into the engine's cache in process
  memory only. Wrapped in the pinned S0 read-only window, on the verified session copy, never saved; same pre/post.
- **Candidates (23 installed stock characters plus the Heavy as a known control; files verified on disk):** HL2 `humans/group01/male_07`,
  `humans/group01/female_01`, `alyx`, `barney`, `kleiner`, `gman_high`, `police`, `combine_soldier`; CSS
  `player/ct_gign`, `player/t_leet`; DoD `player/american_assault`, `player/german_assault`; TF2 `player/scout`,
  `soldier`, `pyro`, `demo`, `engineer`, `medic`, `sniper`, `spy` (and `heavy` as the known control); L4D2
  `survivors/survivor_coach`; Portal 2 `player/chell/player`; Black Mesa `humans/scientist`. The Owner may add or
  remove names.
- **Selection rule:** zero bones with `proctype ≠ 0` or a procedural/physics/screen-align flag; prefer the smallest
  humanoid ValveBiped skeleton among those. One Script Editor submission, about five minutes.
- **Then (separately authorized):** the chosen model enters the SFP-1 native acceptance procedure (implementation
  record section 9) as the first generic v3 Full body qualification.

If no candidate qualifies, the inventory itself shows which procedural types dominate stock content, which informs
whether a derived-bone category is worth designing.
