# F-01 OT1 — Astra's qualification-only ordering trial: offline preparation

**Date:** 2026-11-16. **Authority:** Astra adjudication of the Q1 evaluation-order review, ACCEPT WITH CONDITIONS;
the Designer's assignment "F-01 — Implement Astra's Qualification-Only Ordering Trial" (offline preparation only).
**Governing design:** Blueprint R4 section 6. **Base checkpoint:** `9f0f7ff` (CPM `615acf0c…`).

**Status: prepared offline, not run.** No SFM launch, installation, deployment, push, merge, signing or release.
Production is unchanged: the candidate exists only to be qualified; promotion needs separate adjudication and
authorization. Related records: `F01_Q1_EVALUATION_ORDER_REVIEW.md` (Astra's ruling as received, the Q1 analyzer
correction and replay), `F01_Q1_RESULTS_ERRATUM_1.md` (the corrected refresh-before interpretation).

## 1. Identities

| Item | Value |
|---|---|
| Base CPM (`9f0f7ff`) | `615acf0c23ffcf5c278785bb47de6aaf6a7b9ae26779b9313979ac928240c432` |
| **Trial candidate CPM** | **`0cea8acdcf934cc69590356ba7c237c963728e118fa67e298e641fd56077fa3c`** |
| Exact diff, base → candidate | `cpm/qualification/F01_OT1_CANDIDATE.diff` (`git diff 9f0f7ff -- cpm/app/SFM_Character_Preset_Manager.py`, 244 lines, `a59f3b26794c279d0f7b3192a388330fb16994e88c914d8bae28adc83751d01a`): 226 lines added, 0 removed |
| Qualification build (one line, `PROD_POSE_REGISTRY_MODE = u"qualification"`, line 42446) | `0fbb4fb1aae964a4514e3df2a7c6820605d3af95857a819ac9595c00f3e9c780` |
| Registries (unchanged) | pose `f445d5ef…`, body `22dcd159…` |
| Published installation (restored after the trial) | v1.0.0, CPM `ccbed9d7…` |
| Trial suite | `cpm/convergence/tests/test_cpm_app_f01_ordering_trial.py` `4424ab09…` |
| Native kit (current: DC1 instrumentation, section 4.3; earlier `ac84df8` observer `66a4f485…`, `59414aa` observer `93e9fbf3…`) | `real_sfm_qualification/f01_ot1_ordering_trial/`: `PROCEDURE.md`, `ot1.template.json` `40b4b11a…`, `observer/F01_OT1_Observe.py` **`403ea56642249559c4e74d2a9d0e5c6adea6773a7aa6910d8cd96464e24143e2`** (loads the pinned Q1 observer `f2eba1e0…`), `tools/ot1_tool.py` `6f052af2…`, `tools/ot1_analyze.py` `f0bbb45b…`, `tests/test_ot1.py` `e823b955…`, `tests/test_ot1_observer.py` `b1556c5b…` |
| SFM's shipped DC1 helper (pinned, verified by `pre`) | `<SFM game>\sdktools\python\global\Scripts\vsUtils.py` `d89f23c0599fa271abc52a3edffcfcfebd46bc381671cfad07076d7522f9767a` |

## 2. The candidate correction

Only `prod_bs_write_existing_scale` changes, and only for a binding admitted as the static mode-3 class
(`binding["static_output_mode"] == 3`, set solely by `prod_bs_index_binding`). Two helpers are added.

For an admitted, changed, existing mode-3 bone scale, inside the existing owned `Apply Body Preset` transaction:

| Assignment step | Where |
|---|---|
| 1. Existing binding, instance and writer-identity checks | unchanged, before the transaction: `prod_cpm_authorize_operation`, `prod_instance_pair_check` (bindings and snapshot), `prod_bs_index_build_plan` (`prod_bs_index_binding`: one output channel to `transform.scale` from `expression.result`, one input channel, `lerp(value,lo,hi)`, coherent before Apply, the static class) |
| 2. Write the input through the existing Body path | unchanged: one-key check, `SetKeyValue(0)`, `source.SetValue`, `input_channel.Operate()`, `prod_bs_authored_matches` |
| 3. Operate the bound expression in the owned transaction | new `prod_bs_operate_bound_expression`: proves the binding first (below), then one `Operate()` on the bound `DmeExpressionOperator` (directly, or through `vs.CastElementAsDmeExpressionOperator` only when the cast is the same element) |
| 4. Verify the expression result before commit | the same function: CPM's `prod_bs_snapshot` after `Operate()` must still satisfy `prod_bs_authored_matches` (static one key at 0, source, expression input and key equal to the native value, output mode 3 with its readable, empty, non-default output log) and `expression.result` must equal `prod_bs_expected_physical` (`lo + native·(hi − lo)`) within `EPSILON` |
| 5. Retain the postcommit physical verification | unchanged: `same_time_refresh`, then the deferred `prod_apply_deferred_verify` → `prod_bs_play_expectations_hold` + `prod_bs_index_verify_saved` (physical scale) |

**Binding proof before `Operate()` (shared, replaced or ambiguous → refusal):** expression type
`DmeExpressionOperator` and text `lerp(value,lo,hi)`; the output channel still reads `expression.result` into the
planned transform's `scale`, and the input channel still writes `expression.value`; across **every** channels clip of
the shot's `animSetEditorChannels` track (so another animation set or a same-model peer is seen), exactly one channel
reads the expression (the planned output) and exactly one writes it (the planned input), read strictly
(`prod_instance_strict_members`, `prod_flex_strict_read`: an unreadable track, clip, channel list or endpoint
refuses); the control, input channel, input log and layer (re-read from the channel), expression, output channel,
output log and layer, and transform identities equal the plan's baseline; `lo`/`hi` equal the baseline and the
binding.

**Failure handling:** every refusal or operator exception is raised inside the transaction, so the existing
`prod_abort_apply_and_verify` runs (`AbortUndoableOperation`, one refresh, `prod_verify_apply_abort_baseline`, which
compares `expr_result` and `physical_scale` with the baseline): verified Abort, or `ProdRecoveryUnverifiedError` when
restoration cannot be proved. Postcommit failures stay `committed-unverified` with no automatic Undo.

**Unchanged:** Expression Presets (no scale plan), newly created scale graphs (`prod_bs_create_graph`), mode-1 scales,
flex writes, Pose Apply, every window method and callback, the deferred verification, the abort verification, record
formats and user-facing text. Only `prod_bs_write_existing_scale` calls the two helpers (trial suite N6; canonical
route: changed tops exactly the expected set plus `F01_OT1_CHANGED_TOP`). The expression result alone never decides
success (trial suite S1–S4).

## 3. Offline qualification

### 3.1 The trial suite (`test_cpm_app_f01_ordering_trial.py`): **63/63 on Python 2.7.5 (SFM) and 3.10.6**

The M-05 harness (production functions extracted verbatim; fakes only at the SFM/Qt/DME/authority/library boundaries)
with an explicit evaluator in which **input, expression result and physical scale advance independently**: input by
CPM's own writes and input-channel `Operate()`; the expression result only by `expression.Operate()` or an evaluator
step; the physical scale only by an evaluator step copying an up-to-date result into a mode-3 bone. Models: **q1**
(each same-time refresh advances each graph one link, the stale expression first; the settled interval advances
nothing — Q1's measurement), **stale** (physical never advances), **wrong** (physical advances to a wrong value),
**frozen** (nothing evaluates). The baseline is the same namespace with the trial's one call disabled.

| Section | What it shows |
|---|---|
| P0 | the baseline under the q1 model reproduces Q1 exactly: after Body's refresh the expression results are 1.33/1.0, the physical scales 1.13/0.8, `committed-unverified` (`bone-scales`) |
| P1–P7 | the candidate: each changed mode-3 expression operated exactly once, inside the transaction, after its input write; at commit the results are 1.33/1.0 and the physical scales still 1.13/0.8 (CPM writes no bone scale, output channel or mode; output mode 3 and empty logs kept); one Undo entry; CPM's own refresh then advances the physical scales; the deferred physical verification → `committed-verified`, read-only |
| S1–S4 | stale or wrong physical output → `committed-unverified` (`bone-scales`), never success, no Undo; the window publishes the unverified copy; the trial function writes nothing but the operator and reads no physical value as success; the deferred verification is unchanged |
| E1–E4 | operator raises (before or after a partial result), does nothing, produces a wrong result, or disturbs the authored input → verified Abort to the exact baseline, no Undo entry; unprovable Abort → recovery uncertainty; a later failure (flex write) after both operators ran → verified Abort restores the operated results; an operated result or physical scale left after Abort → not verified |
| I1–I6 | a second reader in the same clip, a reader or writer in another channels clip, an unreadable endpoint anywhere in the track, an output re-pointed or re-targeted, expression text or limits changed, input or output log replaced → refused **before** `Operate()`, nothing committed; the cast fallback operates only the same element; unrelated clips and channels are not mistaken for sharing |
| N1–N6 | a same-model peer (same names, own clip) is never operated or changed; an unchanged mode-3 scale is not written or operated; mode-1, created-graph and FLEX-only Applies and Expression Presets operate nothing and match the baseline's outcome and writes; no-op operates nothing; the trial is reachable only from the Body existing-scale write |
| C1–C5 | under the q1 model through the window: the one callback verifies and ends once; duplicate and stale callbacks are harmless and never end a newer operation; context, time, authored or limit changes before the callback → `committed-unverified` with no rewrite, Undo or further `Operate()`; modal at the callback and close while pending end unverified |

**Discrimination:** with the candidate's call disabled the same suite passes 22 of 57 checks (it aborts in P1), so it
does not pass on the baseline.

### 3.2 Harness and route changes (test code only)

- `test_cpm_app_m05_static_scale.py`: the fakes gain what the candidate reads — `HasAttribute`, a
  `DmeExpressionOperator` with `Operate()`, and the shot's channels track (`FindTrackGroup` → `FindTrack` → one
  `DmeChannelsClip` holding the scene's channels, kept out of the Undo capture); the six new or strict-read names are
  extracted. Result unchanged: **114/115 on both interpreters, the same pre-existing failure** (A9 `in (1, 3)`, present
  at `9f0f7ff`).
- `test_cpm_app_canonical_route.py`: a dedicated, commented `F01_OT1_CHANGED_TOP = {prod_bs_write_existing_scale}` and
  `F01_OT1_NEW_TOP = {prod_bs_expression_channels, prod_bs_operate_bound_expression}`. Result unchanged: **84/85,
  compare 2/3**, the same pre-existing `derivation.added_top_level_is_bounded` failure with exactly the same 11
  unlisted names; `derivation.changed_top_level_is_bounded` passes.

### 3.3 Regressions (HEAD `9f0f7ff` vs candidate, same runner, both interpreters)

One runner (each suite under its own protocol, sequentially) on a full `git archive` of `9f0f7ff` and on the
candidate working tree.

| Suite | HEAD `9f0f7ff` | Candidate |
|---|---|---|
| Body (`f01_body`), both | 257/257 | 257/257 |
| Pose core / library / live / integration, both | 255 / 87 / 104 / 218, all pass | identical |
| Scoped, both | 486/486 | 486/486 |
| M-06 instance resolution / static-play flex, both | 179/179, 334/334 | identical |
| Operation context (publish/suite/compare) | 108/108, 3/3 | identical |
| Clothing fit; compat v1 projection | 95/95, 3/3; 196/196, 3/3 | identical |
| M-05, both | 114/115 (pre-existing A9) | 114/115, same failure |
| Canonical route | 84/85, compare 2/3 (pre-existing, same 11 names) | identical |
| Convergence gates | 147/148, compare 2/3 (normalizer pins) | identical |
| R14 ctypes isolation | 17/18 (2.7.5), 14/15 (3.10.6) (normalizer pin) | identical |
| Authority cleanup, both | 42/46 | 42/46, same four checks |
| Authority adapter | setup fails (fixture) | identical |
| Logging cleanup, UI polish pass | refuse without an explicit `--reference` app | identical |
| R15 namespace isolation | archive run aborted early (`lifecycle.child_reported`), with the same five `forbidden.unchanged.*` failures | 340/345 (2.7.5), 183/188 (3.10.6): only those five (pinned files outside `cpm/app` differ in this worktree) |
| Poses page / scoped page / empty states (2.7.5; PySide is absent from 3.10) | not loadable from the archive | 123/123, 17/17, 15/15, equal to the recorded results (`F01_K2_UI_CORRECTIONS.md` section 3) |
| Bounded logging, both | not loadable from the archive | 71/72: `guard.real_log_folder_absent_and_historical_log_unchanged`, an environment guard (this machine's CPM log folder exists after the native runs); independent of the application source |
| Ordering trial (new), both | — | 63/63 |

No suite changed result because of the candidate.

### 3.4 Native-kit tests

Revised with the BASE preflight (section 4.1): `tests/test_ot1.py` **67/67** (the five added cases: no preflight, a
state change across it, a shared expression, an unreadable endpoint, another instance → INCOMPLETE);
`tests/test_ot1_observer.py` **35/35 on SFM Python 2.7.5 and 3.10.6** (15 added, P1–P12, below). As first committed:

- `tests/test_ot1.py` (Python 3.10.6): **62/62** — template pins equal the files (candidate, registries, both observers,
  the S0 observer; published, fixture, destination, Body, legacy-pose pins equal the Q1/UA-1 kits'; no personal path);
  the one-line derivation from the real candidate gives the pinned qualification build; the analyzer on synthetic runs:
  the complete trial → CANDIDATE PASS; Q1's lagging physical scale after Undo → **CANDIDATE FAIL with "Apply PASS with
  Undo FAIL: the candidate FAILS"**; 25 single-check mutations across APPLY, UNDO and ABORT → CANDIDATE FAIL at the
  right gate; 15 evidence defects (missing capture, wrong build, time moved, another shot, second process, session
  saved, library or installation not restored, hooks left, extra Apply, visibility edit, another instance, no peer,
  recovery uncertainty, wrong starting state) → INCOMPLETE; exclusive-create reports.
- `tests/test_ot1_observer.py`: **20/20 on SFM Python 2.7.5 and 3.10.6** — the five wrappers pass arguments and results
  through and re-raise unchanged; the scale-write read brackets CPM's write; the refresh read follows CPM's refresh;
  the controlled failure fires once, only when armed, only after CPM's armed write returned (never when it raised);
  uninstall restores and disarms; a changed Q1 observer is refused; the observer makes no scene write, refresh, Undo or
  `Operate()` and writes only its exclusive-create capture.

## 4. Native trial (prepared, not run): `real_sfm_qualification/f01_ot1_ordering_trial/PROCEDURE.md`

One SFM process; `OT1_KRYSTAL.dmx` (verified copy of the R2 fixture `259ea8a6…`), shot15 at 0.2083 s, never moved;
original `Krystal` (A) plus a same-model peer created first (B); Krystal's pinned `Body` preset only. No Happy, no
other preset, no retiming.

| Step | Proves |
|---|---|
| BASE (B created, A selected; hooks installed) | starting state: head 1.13, tail 0.8; history `CreateAnimationSetAndModel` |
| Apply `Body` → APPLY | correct physical Apply: two changed mode-3 writes; at precommit (inside the transaction, after the operator; CPM's own snapshot) results 1.33/1.0 with authored input and empty output intact; CPM's deferred physical verification `committed-verified`; settled map PASS; raw physical scales 1.33/1.0; one history entry; only head and tail scales changed on A's bones; B untouched |
| Edit > Undo → UNDO | exact authored and physical restoration to BASE (raw fields and both scale graphs), history back one entry with Redo `Apply Body Preset`, B untouched |
| Edit > Redo → REDO | exactly the APPLY state, settled map PASS, history forward one entry |
| Edit > Undo → UNDO2 | exactly BASE again |
| ARM, Apply `Body` → ABORT | controlled failure after the tail's operator call (both expressions operated and verified first): CPM's own abort verification `restored=True`, no recovery uncertainty, A equals ARM exactly, no history entry, B untouched, injector fired once |

### 4.1 BASE graph preflight (Designer authorization "F-01 OT1 — BASE Preflight Improvement"; observer only)

At BASE, before the hooks are installed, the observer inspects A's existing `bip_head` and `bip_tail00` graphs read
only: CPM's own `prod_bs_index_snapshot` and `prod_bs_index_binding` for the selected instance, then
- the **candidate's own scan**, `prod_bs_expression_channels` (the exact function the candidate calls before
  `Operate()`): reader and writer counts and identities, or the error it raises (it stops at the first unreadable item);
- a **diagnostic enumeration** of the same structure with the same strict primitives that continues past failures,
  listing every reader and writer (clip, channel, attribute) and every unreadable track, clip type, clip channel list
  or endpoint;
- the candidate's other pre-`Operate()` graph checks that need no plan baseline: expression type and text, the four
  endpoints, static output mode 3;
- which animation sets list the expression in their `operators` arrays (reported; not part of the candidate);
- **would_pass**: the candidate's graph-uniqueness precondition holds for both scales (exactly the planned reader and
  writer, nothing unreadable, endpoints and expression as required);
- the instance and the expression, output, input-channel, transform and control identities.

The Undo state (description, Redo description, count) and the playhead are read before and after the preflight and
recorded. It calls no `Operate()`, writes nothing, refreshes nothing, moves nothing and opens no Undo action (offline
test P1 and the static check L2; natively, `side_effects.unchanged`). The analyzer requires a passing, unchanged
preflight (`preflight.read_only_no_state_change`, `preflight.candidate_uniqueness_precondition`, EVIDENCE), and the
procedure stops before the first Apply when BASE prints `preflight FAIL`. The candidate is unchanged (`0cea8acd…`).

Offline (`test_ot1_observer.py` P1–P12, with the candidate's committed scan and strict-read helpers extracted verbatim
from the app source): valid graphs pass; a second reader in another set's clip (shared) and a second writer
(ambiguous) fail with both listed; an unreadable endpoint in an unrelated clip makes the candidate's scan refuse while
the enumeration names it and still finds the one reader and writer; an unreadable clip type and channel list are both
listed; a refused binding, a missing bone and a changed endpoint fail; operators-array membership is reported only; a
state change across the preflight is recorded; nothing is written or operated; the preflight precedes the hooks.

### 4.2 What the scan covers, and what it cannot establish

**Covered (both in the candidate and in the preflight):** every `DmeChannel` listed in the `channels` array of every
`DmeChannelsClip` child of the shot's `channelTrackGroup` / `animSetEditorChannels` track, by its `fromElement`
(readers) and `toElement` (writers), compared by element identity with the bound expression. This is where SFM keeps
the channels of every animation set in the shot, including a same-model peer's.

**Not covered:**
- channels outside that track: other tracks or track groups, other shots or nested film clips, and channels listed in
  no clip;
- **non-channel references** to the expression: operators that hold element or attribute references (for example
  connection or constraint operators, rig or script-created elements), other element-valued attributes or element
  arrays anywhere in the document. The preflight's `operators`-array report shows membership in animation sets'
  operator lists only, not data flow. No read-only, verified way to enumerate every element referring to another
  element was used; the SFM Python API's reverse-reference facilities were not established in this work.

**Consequence: the scan proves channel exclusivity within the shot's animation-set channels track, not universal graph
exclusivity.** Neither the candidate nor this record claims more.

**Does the trial's safety depend on the uncovered reference types?** Operating the expression changes only that
expression's own `result`. Q1 measured that, without the candidate, Body's own same-time refresh already advances that
`result` to the same value; the candidate makes it current before commit instead of after. A consumer outside the scan
would therefore receive the same value it already receives today, a little earlier and inside CPM's owned Undo entry,
and nothing evaluates inside the transaction except CPM's explicit calls. A hidden writer into `expression.value`
would already conflict with today's Body path; the candidate's post-`Operate()` authored check and the unchanged
postcommit physical verification would report it, not certify it. On that reasoning no new destination is created.
But Astra's condition reads "ensure no conflicting or shared destination of the expression result", and that can be
ensured only for channel references. **This is recorded as an unresolved Astra design condition (OT1-DC1):** Astra
should either accept channel-track exclusivity plus the reasoning above as sufficient for the qualification-only
trial, or name an additional reference inspection to be prepared before the native run. **Disposition:** Astra named
the direct-reference inspection; it is implemented in section 4.3.

### 4.3 Astra's DC1 ruling and the direct-reference instrumentation

**Ruling (Astra, second ACCEPT WITH CONDITIONS; accepted by the Designer in "F-01 OT1 — Implement Astra DC1
Instrumentation Condition"; recorded here as the assignment states it):** OT1-DC1 is resolved by instrumentation, not
by a candidate change. At the existing BASE observation (after the peer exists) and again at ARM (before arming), the
observer enumerates the direct DataModel references to A's live `bip_head_scale_rescale` and
`bip_tail00_scale_rescale` with SFM's shipped read-only `vsUtils.iterReferringAttributes`, and requires exactly three
relationships each, matched by live element identity: A's animation set `operators`, the admitted input channel
`toElement`, the admitted output channel `fromElement`. Any extra, missing, unexpected or unreadable reference, an API
exception, an incomplete enumeration or a mismatch with the candidate's binding and endpoint checks stops the trial
before Apply (BASE) or before arming (ARM). The channel-track uniqueness check stays. The candidate (`0cea8acd…`) is
unchanged.

**Implementation (observer only):** `ot1_vsutils` imports `vsUtils` (recording whether it was already loaded, its
source file's SHA-256 and the `vs.CDmElement.__eq__`/`__hash__` presence before and after); `ot1_direct_refs` iterates
`iterReferringAttributes(expression)` to its end — the helper is a generator that stops only when
`IDataModel.NextAttributeReferencingElement` returns `DMATTRIBUTE_REFERENCE_ITERATOR_INVALID`, so a normal end means a
complete enumeration and any exception is recorded as incomplete — and records each attribute's owner (identity, type,
name, handle) and name, assigning a role only when the owner is the binding's live element (`same_dme`) under the
expected attribute name. The preflight's `would_pass` now also requires the DC1 result for both expressions. ARM runs
the same preflight first and arms through `ot1_arm` only after a passing, unchanged preflight. The analyzer
independently re-checks the recorded evidence (it does not trust the observer's pass flags): three references per
expression, each role exactly once with the expected attribute, owners equal to the preflight's binding identities,
the `operators` owner being the selected instance's set, nothing unreadable, extra or incomplete, the same live
elements at BASE and ARM, a passing unchanged ARM preflight, and the pinned `vsUtils.py`. `pre` refuses unless the
installed `vsUtils.py` is the pinned file.

**Offline verification:** `test_ot1_observer.py` **55/55 on SFM Python 2.7.5 and 3.10.6** (D1–D6 added): the three
references pass, with the operators-array membership as one of them; an off-track reader (invisible to the channel-
track scan, which still passes), an unexpected connection-operator reference, a missing or duplicated reference, an
unreadable owner or attribute name, an enumeration raising part way, the operators listing on the peer's set, a
replaced input channel with the same name, the right owner under another attribute name, and an unavailable vsUtils
all fail; ARM refuses to arm after a failing, state-changing or missing preflight and arms once after a passing one;
nothing is written or operated. `test_ot1.py` **84/84 on 3.10.6** (17 added: each DC1 defect at BASE or ARM, partial
evidence with no reference list or no identities, no or state-changing ARM preflight, BASE/ARM identity disagreement,
an unpinned or failed vsUtils → INCOMPLETE; the valid evidence passes and the vsUtils import is reported as a
finding). The DC1 mutations leave the observer's own pass flags True, so they show the analyzer cannot be carried to a
false PASS by partial or contradictory evidence. On SFM Python 2.7.5 the same file is 84/84 when the reused Q1 helper
`set_field_problems` sees `str` names (it tests `isinstance(name, str)`, which 2.7's JSON `unicode` fails; the kit tools
are Python 3 by design and run so).

**Coverage after DC1:** every direct DataModel attribute reference to each expression (element and element-array
attributes of any owner, anywhere in the loaded data model) is enumerated and must be exactly the three expected
ones. Not covered: indirect relationships (an element that references the operators list or a channel, scripts holding
Python references, anything outside the DataModel), and the period between ARM and the controlled-failure Apply
(and between BASE and the first Apply), which are one user action apart with no other step in between.

**New design condition OT1-DC2 (for Astra):** `vsUtils` is not imported by SFM's startup (`sfm_init.py` imports
nothing; `sfmUtils` does not import it; only on-demand scripts do). Importing it runs module-level code that sets
`vs.CDmElement.__hash__ = GetHandle` and `__eq__` (handle-hash equality), adds helper methods, and sets `__hash__` on
`vs.Vector`, `vs.QAngle` and `vs.Quaternion`, for the rest of the SFM process. Without it, `CDmElement` defines no
`__eq__`/`__hash__` (Python object identity). The observer would therefore change element equality semantics in the
same process before the Apply, Undo, Redo and Abort steps it qualifies. It writes nothing to the DataModel, and CPM
compares elements through `same_dme` (handle and pointer) and handle tuples; a heuristic search found no direct
`==`, `in` or index use on element wrappers in CPM, but that is not a proof. The capture records whether `vsUtils` was
preloaded and the class attributes before and after; the analyzer reports it as a finding. Per the assignment no
unreviewed substitute (for example calling the same `IDataModel` iterator primitives without importing `vsUtils`, or
undoing its patches) was used. Astra should accept the import as implemented, or choose one of those alternatives.

**Protected inventories** (the S3 tool, unchanged): `usermod\scripts`, `usermod\cfg`, the preset library, the SFM
sessions folder; plus the published CPM, both registries absent, `.pyc` and housekeeping files; restoration verified
by `restore`/`check` and the analyzer.

## 5. Gates, failure and STOP conditions

**Verdict** (`ot1_analyze.py`): **CANDIDATE PASS** only when APPLY, UNDO (Undo, Redo, final Undo) and ABORT pass on
complete evidence; **CANDIDATE FAIL** when the evidence is complete and any of them fails — **Apply PASS with Undo FAIL
is a FAIL**, and the report says so; **INCOMPLETE** when evidence or restoration fails (no candidate decision). Exact
restoration means every raw field of A (controls, bone positions, orientations, scales, flex weights, visibility) and
both scale graphs (source, key, expression input and result, physical scale, output mode and log) within 1e-6.

**STOP (exit without saving; restoration and analysis still run):** any capture error, refusal or missing hooks; the
playhead not 0.2083 s or moved; the first Apply refused or failed (no Undo is attempted); the Edit menu not naming
`Apply Body Preset`; the controlled-failure Apply reporting unverified recovery or succeeding; any visible change to
B; anything saved, updated, deleted or trashed; a crash, recovery prompt or hang. A "couldn't confirm" Apply is not a
STOP: the Undo steps still run, and the APPLY gate fails.

**After a FAIL:** no additional workaround (another preset, a second refresh, retiming, a history listener) without
renewed adjudication; a second refresh is admissible only as Astra's separate controlled comparison.

## 6. Remaining uncertainties

1. **SFM's evaluation order is still not established.** The offline q1 model reproduces Q1 and predicts a PASS, but it
   is a model. Whether CPM's own refresh after commit advances the physical scales once the expression is current,
   and what `SetHeadTimeInSeconds` + `ProcessEvents` do with operator dirty state, only the native trial can show.
2. **Undo and Redo of an operated expression.** `Operate()` inside `StartUndo` should record the `result` change in the
   Apply's Undo entry; the physical scale is written by the output channel outside CPM's writes and is not recorded.
   Whether native Undo, Redo and the final Undo leave the physical scale exact (Q1 showed it one step behind after
   Undo) is the trial's separate gate and the most likely failure.
3. **`Operate()` on the wrapper.** The expression read from `output.fromElement` is expected to be a
   `CDmeExpressionOperator` (it derives from `IDmeOperator`); the same-element cast fallback is implemented and tested
   offline only.
4. **Strict shot-wide scan.** Any unreadable channel endpoint in any channels clip of the shot refuses the Body Apply
   (fail closed, verified Abort). The fixture's other clips (camera, lights, props) are not yet proven readable; the
   BASE preflight (section 4.1) now reports this before any Apply and stops the trial if it fails. The scan's coverage
   limit is design condition OT1-DC1 (section 4.2).
5. **Observer reads.** Inside the transaction the observer reads only `prod_bs_snapshot`, which the candidate itself
   calls after `Operate()`. After CPM's refresh it reads the same snapshot of the two written scales before CPM's
   deferred verification. In Q1, heavier full-map reads at these boundaries did not advance a stale physical scale,
   so reads are not expected to pull evaluation, but this is not proven for every case.
6. **Abort and history.** Whether `AbortUndoableOperation` after the operator keeps or clears the Redo entry left by
   UNDO2 is recorded, not gated. The abort verification itself compares expression result and physical scale.
7. **Scope of the trial.** One character, two scales, one peer, one fixture; not mode-1, created graphs, other rigs,
   repeated Applies, or an expression shared in other ways than tested offline.
8. **The offline fake Abort** cannot undo a Python-level object replacement (trial suite I4); such cases are refused
   before `Operate()` and nothing is committed, but their recovery is reported unverified in the fake.

## 7. Readiness recommendation

**OT1-DC1 is implemented as Astra ruled (section 4.3). Ready for the Owner's authorization of the native trial once
Astra has disposed of design condition OT1-DC2** (the `vsUtils` import's process-wide equality patch, section 4.3),
with these conditions: run exactly `PROCEDURE.md` in one
SFM session from a new run folder; the candidate and qualification build as pinned (`0cea8acd…` / `0fbb4fb1…`);
restoration and the analyzer always run; the verdict is reported as the analyzer gives it. A CANDIDATE PASS qualifies
the ordering for review only: production repair stays on hold, the shipping behaviour (`committed-unverified`) is
unchanged, and any promotion needs separate adjudication. A CANDIDATE FAIL — including Apply PASS with Undo FAIL —
ends this candidate; any further change needs renewed adjudication.
