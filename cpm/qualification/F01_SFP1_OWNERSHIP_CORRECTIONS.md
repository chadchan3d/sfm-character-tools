# F-01 SFP-1 — Dependency Ownership Corrections (Astra closure review of `953b107`)

**Date:** 2026-11-08. **Authority:** Astra closure review — CORRECTIONS REQUIRED; Owner-authorized bounded offline
correction of the two demonstrated P1 dependency defects. Specification: R3, unchanged. Earlier corrections
(indices, followers, parents, cross-set dependencies, Pass/Play readers) intact. **Status:** offline complete; not
natively qualified; nothing installed, enabled, pushed, merged, packaged or released.

## 1. Defects and root causes

| Defect | Root cause in `953b107` |
|---|---|
| A Pass channel from a posed finger into the preserved tail log's `defaultvalue` was admitted as an external follower | The protected set named bones, model, rig handles, controls, channels and operator elements only. Every other element reached (a log, a layer, the animation set, …) fell through to "external": unknown ownership was treated as external. |
| `posed finger -> prop P -> shared transform -> prop Q -> protected tail` was admitted | The inventory mapped each transform to one DAG (the last enumerated), so the other owner was lost; alias steps also bypassed classification. |

## 2. Corrections

- **Protected ownership graph.** `prod_scope_instance_elements(L)` records the instance's own mutable resources that
  the discovery rows do not name: the animation set, its channels clip, rigs, registrations and owned rig elements,
  every channel's log and layers (keys and defaults), and the control groups. With the bones, model, rig handles,
  controls, channels, operator elements, and the channel log/layer handles, all are protected.
- **Every transform owner.** The inventory records, for each transform, every scene DAG that owns it, each DAG's
  transform, and the scene DAG set. Tracing moves a transform to all its owners and a DAG to its transform through
  the same classification as every other edge. A transform shared between the instance and another DAG is
  protected. A second DAG holding a bone transform is still refused earlier by the live reader (duplicated bone).
- **Positive external-admission invariant** (`prod_scope_dependencies`). An element reached is admitted as external
  only on positive evidence that its effects are bounded and traced: a scene DAG or the transform of scene DAGs
  (reached through the hierarchy, a transform alias, a supported constraint, or a channel), a supported value
  operator (expression, pack-color: traced through its channels), or an element of a supported constraint (traced
  through that constraint). Everything else — a log, layer, control or element of unknown kind or ownership outside
  the instance, a transform no scene DAG owns, a constraint slave that is not a scene DAG — refuses
  (`structure-unsupported`; `evidence-unreadable` when only an unknown effect reaches it). Protected elements refuse
  with `shared-input`, naming the bone or the model where applicable. There is exactly one external-admission site,
  guarded by those positive conditions; moving elements arise only from the authorized inputs and classified edges.
- **Revalidation** is unchanged in form and now covers the new ownership evidence: the authority check runs the
  tracing at Save, P1, P2 and P7, and the traced `{confined, external, edges}` are compared at P2 / verified Abort
  recovery and P7.

CPM `a8351617…` -> `2d791dec96c0b4816693c369fe5f956de5e1ed93a1ecea8b95fd0d5515b9cc6a`; all 31 hunks inside the
scoped-pose block.

## 2a. Regression (Python 2.7.5 and 3.10.6)

Scoped 364/364 both (AX1-3 49, AY 55, AZ 39 correction rows all passing); scoped page (Qt) 12/12; body 246/246;
pose core/library/integration/live 255/87/204/104; pose page 118/118; canonical route 84/85 with only the
historical row (difference `PROD_EMPTY_STATE_GUIDANCE`, `prod_model_candidates`). Production gating, legacy v1/v2
and real ProdWindow dispatch rows pass on both interpreters.

## 3. Counterexamples: before and after

Before = the new tests against `953b107` (Python 3.10.6): 334/362, all 28 failures in the new section: 26 confirm
the defects; 2 were the shared-bone-transform rows, which `953b107` already refused through the live reader with
`structure-unsupported` (the expectation was then aligned to that legitimate earlier refusal). One row (model
transform sharing) was added after the before run. After: all pass on Python 2.7.5 and 3.10.6.

| Case | Before (`953b107`) | After |
|---|---|---|
| **Astra 1:** Pass from posed `finger3` into the `tail_o` log `defaultvalue` | admitted, written, then committed-unverified | refused before writing or Undo (`shared-input`) |
| Pass into a character layer / the character's animation set | admitted | refused (`shared-input`) |
| Pass into another animation's log / another set's control / an element of unknown kind / a transform no scene DAG owns; constraint slaving a non-DAG element | admitted | refused (`structure-unsupported`) |
| **Astra 2:** `finger3 -> P -> shared transform -> Q -> tail`, enumeration orders PQ and QP | admitted (both orders), committed-verified | refused (`shared-input`), both orders |
| Three aliases returning to the leg, orders PQR, RQP, QRP | admitted | refused, every order |
| Following prop sharing the model's transform | — (new) | refused (`shared-input`) |
| Shared transform among external props only (both orders); ordinary unshared prop; bounded expression route into a prop | apply | apply and verify |
| DAG sharing a bone transform (protected or posed) | refused (duplicated bone, live reader) | unchanged |
| Shared alias appearing between P1 and P2 | stale | stale, no write |
| Protected log reader appearing before P7 | committed-unverified | committed-unverified, no automatic Undo |

## 4. Remaining unsupported ownership structures (refused)

1. Pass/Play readers writing into any log, layer or control — the character's or another's — refuse; CPM does not
   establish whether such a write is bounded.
2. Elements outside every scene walked from the document's film clips (orphan transforms, non-DAG constraint slaves)
   have no positive ownership evidence and refuse when reached.
3. Transforms shared between the character and any other DAG refuse when reached; a DAG holding a bone transform
   refuses at the live reader.
4. Element-level conservatism and Play-mode propagation from moving sources, as recorded in
   `F01_SFP1_DEPENDENCY_CORRECTIONS.md` section 3, are unchanged. External followers remain unverified by CPM.

Production experimental gates are unchanged (`PROD_POSE_REGISTRY_MODE` production; `direct_fk_v1` experimental;
`constant_channel_carried_v1` disabled).
