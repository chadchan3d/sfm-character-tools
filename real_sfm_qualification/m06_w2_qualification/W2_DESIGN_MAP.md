# M-06 W2: design-to-implementation map

**Authority:**

- Astra's *M-06/M-05 Integration Correction Design*, 2026-10-29, section "W2: Qualification instrumentation and deferred-path coverage".
- The Owner's W2 assignment, which restates the adjudicated audit items, including the scale-writer correction.

**Starting points:**

- the attempt-3 instruments (Observer v1, Abort Injector v2, `compare_obs.py`) from `03_native_attempts/attempt3_d2bd6fd6`;
- the M-05 offline DMX reader.

**Test names** below are in `tests/test_m06w2.py`.

## Brief §1: preserve W1

| Requirement | Implementation | Evidence |
|---|---|---|
| Accepted W1 application byte-identical | No production file is touched. W2 is a separate, uncommitted folder. | `TestW1Preserved`; `git status`; the regression comparison in the review package |

## Brief §2: strict native Observer

| Requirement | Implementation | Tests |
|---|---|---|
| Context: document, shot, playhead, selected animation set, game model, model path, checksum; same-model peer; agreement at beginning and end | `core.context_record` (begin and end), `core.animset_record`, `core.checksum_of`. A peer must be distinct **and** same-model. | `test_context_must_agree_at_beginning_and_end`, `test_peer_must_be_a_distinct_instance_and_controls_unique`, `test_peer_must_be_same_model` |
| Complete target bone-scale state: every bone's index, name and transform identity; scale presence and physical value; writers, channels and relationships; graph identities, topology and memberships | `core.bones_record`, `core.graph_record`, `core.Scene`, `core.group_membership`; animation-set `controls`/`operators`; `channels_clips` | `test_complete_observation_of_target_peer_bones_graph_and_flex` |
| **Scale-writer correction:** exact bone endpoint **and** `toAttribute == "scale"`; unreadable endpoints stay unresolved | `scale_writers = scene.writers(bone, "scale")`; `Scene.unresolved` makes the observation insufficient | `test_scale_writer_requires_exact_bone_and_scale_attribute`, `test_unreadable_endpoint_or_attribute_is_unresolved_not_excluded`; mutants W03, W04 |
| Body flex: every authorized side; stored source, keys, key arrays, log evaluation, destination; endpoints, modes, layers, metadata; static-play disagreement | `core.control_record`, `core.side_record`, `core.log_record`, `core.representation` | `test_complete_observation_…` (static-play, one-key, stereo); mutant W08 |
| Non-Body preservation: Expression and other target controls, authored values, keys, modes, relationships; transform-control authored state | `nonbody` (config: Expression literals that exist in the fixture, mono and stereo); `transform_controls`. Evaluated outputs that an authorized scale operation may affect are not demanded unchanged: the Apply invariant releases only the declared bone's scale and graph. | `test_complete_observation_…` |
| Same-model peer: independent authored baseline | The peer's full animation-set record, compared under every invariant | `test_negative_4_unexpected_same_model_peer_change` |
| Undo/Redo: availability, descriptions, item information; interpreted against the operation baseline | `core.undo_record`. Flags must be exact `bool`; the count is diagnostic. Each comparator invariant names its own Undo rule. | `test_undo_evidence_strict`; `test_undo_redo_invariants`; mutant W07 |
| Integrity: protected files, disposable fixture, candidate and instrument hashes | `core.integrity_record`; the staged config records the instrument paths; the CPM pin | `test_protected_file_change_makes_observation_insufficient`; `TestStaging` |
| Absent, null, present and unreadable distinguished; required unreadable makes the observation insufficient; never an empty or neutral substitute | `core.read`, `core.read_list`, `core.value`, `core.ident`, `Observation.require*` | `test_four_states_are_distinguished`, `test_presence_claimed_for_a_missing_attribute_is_unreadable`, `test_unreadable_values_never_become_empty_or_neutral`, `test_pointer_like_or_unreadable_identity_is_insufficient`; mutants W01, W02, W05, W06 |
| Read-only | No mutating call exists in the core | `test_core_is_read_only_by_construction` |

## Brief §3: fail-closed comparison

| Requirement | Implementation | Tests |
|---|---|---|
| Declared invariants: unchanged, Apply delta, aborted restoration, Undo baseline, Redo applied state, reopened persistence | `compare_obs.py` `unchanged`, `apply`, `aborted`, `undo`, `redo`, `reopened`; plus `preset` and `prepared` | `test_unchanged_positive`, `test_apply_*`, `test_undo_redo_invariants`, `test_reopened_*`, `test_preset_*`, `test_prepared_fixture_invariant` |
| PASS, OBSERVED MISMATCH, INSUFFICIENT EVIDENCE; only PASS succeeds | Exit 0, 1 and 2 | `test_exit_status_only_pass_succeeds` |
| Negative 1: missing required fields | `require_keys`; `differences()` treats a one-sided key as a difference | `test_negative_1_missing_required_fields`; mutant W11 |
| Negative 2: identical unreadable markers | `scan_states` over both whole records | `test_negative_2_identical_unreadable_markers`; mutant W10 |
| Negative 3: contradictory or wrong-instance identities | `identities()`; the context check | `test_negative_3_contradictory_or_wrong_instance_identity`; mutants W12, W13 |
| Negative 4: unexpected same-model peer change | The peer record is compared under every invariant | `test_negative_4_unexpected_same_model_peer_change` |
| Negative 5: changed Undo state where preservation is required | `inv_unchanged` (also used by `aborted`) | `test_negative_5_…`; mutant W14 |
| Negative 6: incomplete graph removal | `inv_aborted`: detachment (controls, operators, control groups, channels clips) **and** resolvability; then `unchanged` | `test_negative_6_incomplete_graph_removal`, `test_equal_counts_and_names_are_not_restoration`; mutants W15, W16 |
| Negative 7: unreadable scale or flex relationships | Unresolved channels and unreadable states make the evidence insufficient | `test_negative_7_…` |
| Negative 8: false preservation from missing keys | The declared scope (`declared`): records must be exactly the declared literals and peers; no defaults | `test_negative_8_…`; mutants W20, W21 |
| Reload: portable structure and values with freshly resolved identities; no runtime handles | `reopened` strips `handle` and `id` and compares by structure | `test_reopened_compares_portable_state_with_fresh_identities` |
| Presets: complete bone coverage and full-precision effective values | `inv_preset` (exact equality with the observed effective values; the stored source is refused) | `test_preset_bone_coverage_and_full_precision`; mutant W19 |

## Brief §4: Abort Injector and graph-recovery evidence

| Requirement | Implementation | Tests |
|---|---|---|
| Pin the exact candidate; fail closed on a mismatch | `CANDIDATE_SHA256 = fd853661…`; any other installed CPM refuses to arm | `test_pinned_candidate_refuses_any_other_cpm`, `test_injector_source_pins_the_accepted_candidate`; mutant W24 |
| Before the exception, record the created scale control, operators, channels and endpoints, scale-attribute creation and physical value, animation-set, channel-container and control-group membership, and the peer state | `core.created_elements`, from a complete armed baseline and a complete in-transaction observation; the fired record and the watch list | `test_fired_record_holds_every_created_element_and_attachment`, `test_peer_change_inside_the_transaction_is_recorded`, `test_incomplete_baseline_refuses_to_arm`; mutants W09, W25 |
| After the abort, prove removal of every element and attachment, restoration of authored state, no peer change, and preserved Undo; counts and names are insufficient | `compare_obs.py aborted` with the fired record; the Observer's `watch` | `test_post_abort_complete_cleanup_passes_and_incomplete_cleanup_fails`, `test_aborted_without_created_evidence_is_insufficient` |

## Brief §5: separate deferred-verification fixture

| Requirement | Implementation | Evidence |
|---|---|---|
| A new disposable copy of the accepted M-05 fixture; the protected original untouched; the existing mode-3 graph retained | `NATIVE_PROCEDURES.md` §3; the preparation script refuses any document but the hash-verified copy | `test_preparation_refuses_the_wrong_document_and_unsuitable_flex`; mutant W28 |
| Identify a compatible Body flex: mode 3, one layer, one key at zero, coherent evaluation | Offline: `tools/scan_deferred_fixture.py` (shape; actual fixture: Muscles). Natively: coherence re-checked before any change. | `evidence/deferred_fixture_scan.json`; `test_scan_*` (real fixture included); mutants W26, W27 |
| Change only the stored source, to a distinct finite supported value | The preparation script: one `SetValue` on `value`, inside one Undo entry, after confirmation | `test_preparation_changes_only_the_stored_source`; `prepared` invariant; mutant W22 |
| After reopen: the disagreement survives, admission holds, the graph is intact, no unintended change | `reopened` with `static_play`; `admitted_static_play` (representation, mode, sole writer, no control writer) | `test_reopened_*`, `test_admission_requires_the_sole_writer_evidence`; mutant W23 |
| Stop instead of broadening | Scanner `stop`; preparation `stop` records | `test_scan_stops_rather_than_broadening` |
| Deferred sequence: commit → pending → deferred verification → verified; identity continuity; graph identity; flex; scale; combined Undo/Redo | `NATIVE_PROCEDURES.md` §4; `apply` with `graph: existing`; `undo`/`redo` | `test_apply_existing_graph_replaced_is_mismatch`; mutant W18 |
| No claim from mode-1 creation or an offline callback | Stated in the procedure | — |

## Brief §6: native prerequisite probes

| Probe | Implementation | Tests (fakes only: acceptance logic, not native results) |
|---|---|---|
| 1, 2 identity APIs; 4 clip topology; 6 presence agreement; Undo `False`/empty forms | `native/M06_Native_Probe.py`; `tools/compare_probes.py` | `test_probe_records_identity_topology_presence_and_undo_forms`, `test_presence_disagreement_and_pointer_ids_fail_acceptance`; mutant W30 |
| 3 same-session reload invalidation | Two probe runs and `reload_result` | `test_reload_acceptance`, `test_acceptance_fails_when_the_token_would_survive_reload`; mutant W29 |
| 5 real `render()` with duplicate instances | A UI procedure (`NATIVE_PROCEDURES.md` §5) | — (native only) |

## Brief §7: offline qualification

- Both interpreters, with every script compiled under each (`TestScriptsCompile`).
- Mutation testing: `tests/mutate_w2.py`.
- Staging: `tools/stage_instruments.py`.

## Astra-required corrections (W2 correction round)

**Authority:** the Owner's *M-06 W2: Astra-Required Qualification Instrument Corrections* (owner-authorized bounded correction, W2 only). Counterexample IDs refer to `tests/counterexamples.py`, which reproduces each one against the previous W2 tree and the corrected tree. Mutants W31–W62 are in `tests/mutate_w2.py`.

| Finding | Correction | Tests | Counterexamples | Mutants |
|---|---|---|---|---|
| **1. Observer completeness** | Core: log `channel_log_attribute` (must equal `GetLog()`), `bookmarks`, `curveinfo`, `is_empty`; layer `times`, `values`, `curvetypes`, `compressed`, `curveinfo`; the CPM must be configured with and installed as `fd853661`; `config_name`. Comparator `sufficiency()`: validates every side, graph input and output log (`check_log`, `check_view`, `check_side`, `check_graph`), re-derives the representation, requires clip membership, the scale endpoint and the CPM identity; never trusts `complete`. Verified absence of optional attributes still passes. | `TestFinding1ObserverCompleteness` (5 tests) | F1a–F1d | W31–W37 |
| **2. Apply preserves undeclared state** | `inv_apply()`: per declared side, only the authored value fields are masked (`mask_side`, `mask_log_values`: key values, the raw value array, compressed data, the evaluation, the destination, and the stored source only when declared). Every undeclared side, including the opposite stereo side, is compared in full; log identities, defaults, metadata, key times and layers stay compared. The effective value (from the representation), the evaluation and destination, and the stored source are checked separately. Existing graphs: `mask_graph` releases only the declared values; `graph_value_problems` checks the control source, input log, expression input and result, output log and physical scale against `control_value` and `scale` (both required); identities, expression, `lo`/`hi`, endpoints and modes stay compared; `graph_attachment` checks memberships. No literal or graph is removed from the comparison. | `TestFinding2ApplyPreservesUndeclaredState` (9 tests); `test_apply_*` | F2a–F2f | W38–W43 |
| **3. Abort and graph-removal proof** | Core `created_elements()` also inventories the created channels' logs and layers. `inv_aborted()`: requires the complete fired record (`FIRED`), a v3 firing on `fd853661`; both embedded observations pass `sufficiency` and identity checks against A and B; the baseline equals A; `recompute_created()` re-derives controls, operators, channels, logs, layers, control-group memberships and scale attributes, which must reconcile exactly (ids, roles, handles) with the recorded lists; every created element must be detached and `gone`, with resolvability evidence for each; a recorded or observed peer change is a mismatch; then `unchanged` (state and Undo). | `TestFinding3AbortAndGraphRemoval` (8 tests); `test_negative_6_*`; `TestInjector` | F3a–F3e | W44–W49, W15, W16 |
| **4. Reload prerequisite checker** | Probe v2 records `selected_token`, W1's own components (document key, the shot's `GetFileId()`, shot key, the configured target animation set's key, its game model's key, model, checksum), each four-state, and `controls_examined`. `compare_probes.reload_result()`: both tokens complete and readable (else FAIL); the same instance, configuration, model and checksum; invalidation only from a token component; peers ignored. `presence_checks()`: coverage complete and nonempty. | `test_probe_records_the_selected_instance_token`, `test_unreadable_file_id_is_not_invalidation`, `test_peer_only_change_is_not_invalidation`, `test_presence_coverage_must_be_complete_and_nonempty`, `test_reload_acceptance` | F4a–F4c | W50–W53, W29, W30 |
| **5. Deferred configuration and output mode** | One mechanism: `stage_instruments.py` stages one Observer per configuration (`CONFIG_NAME` substituted: `M06_Qualification_Observer.py` → `m06w2_config.json`, `M06_Deferred_Observer.py` → `m06w2_deferred_config.json`) and records `config_name` in each configuration; the Observer and the preparation verify it; the comparator requires equal configurations and, for `prepared`, the deferred one. The preparation requires the qualified mode-3 graph (`qualified_graph_problems`: input and output mode 3), runs `prepared` in-session, and instructs Save As only on PASS (else DO NOT SAVE). `reopened` with `static_play` re-checks the graph modes. The scanner requires output mode 3. | `TestConfigSelection` (3 tests); `test_preparation_refuses_an_output_mode_1_graph`, `test_preparation_refuses_a_configuration_that_is_not_the_deferred_one`, `test_save_as_is_offered_only_after_the_prepared_comparison_passes`; `test_scan_stops_rather_than_broadening` (output mode 1) | F5a–F5d | W54–W59, W27 |
| **6. `inv_preset` on a valid EMPTY log** | `effective_value()`: EMPTY (no key and `IsEmpty()` True) → the stored source, required finite and coherent (CPM's 1e-5) with the evaluation and destination; ONE_KEY_ZERO / STATIC_PLAY_ONE_KEY_ZERO → the key, finite and coherent; anything else refuses. Admission is unchanged: EMPTY is never static-play admitted. | `TestFinding6PresetEmptyLog` (4 tests); `test_preset_bone_coverage_and_full_precision` | F6 | W60–W62 |

**Offline limits.** The fakes cannot show native behaviour. In particular they cannot show whether `IsEmpty()`, `bookmarks`, `curveinfo`, `curvetypes` and `compressed` exist and read as modelled on native logs and layers; whether `AbortUndoableOperation` makes logs and layers unresolvable; or what `GetFileId()` does across a same-session reopen. These remain native obligations (README). If a native read differs, the Observer reports it insufficient and the run stops; nothing is defaulted.

## Astra's final W2 review (three findings)

**Authority:** the Owner's *M-06 W2: Final Bounded Instrument Corrections* (Astra: W2 CORRECTION REQUIRED). Production references are to W1 `fd853661`. Counterexample IDs G1–G3 are in `tests/counterexamples.py`; mutants W63–W80 are in `tests/mutate_w2.py`.

| Finding | Correction | Tests | Counterexamples | Mutants |
|---|---|---|---|---|
| **R1. Compressed-data false PASS** | `mask_log_values()` no longer masks `compressed`; it is protected in every invariant. `compressed_state()` distinguishes verified absence, valid empty data, non-empty data, unreadable and malformed; `check_log()` refuses malformed records. STATIC_PLAY recognition (comparator `representation_of`, core `representation`) requires CPM's metadata rule: empty or absent compressed block, no curve info or curve types. No prohibition for EMPTY or ONE_KEY_ZERO, which production allows. | `TestR1CompressedData` (6) | G1a, G1b; positive G1c | W63–W67 |
| **R2A. M-05 empty output log** | `graph_value_problems()` no longer requires output-log values. It checks the source control, the single input key at time zero and its evaluation, the expression input, `lerp(value, lo, hi)` with finite distinct bounds, and that the result, the physical bone and the declared scale equal `lerp(control_value)`. `output_representation_problems()`: mode 1, or mode 3 with an empty log and `usedefaultvalue` False. `mask_graph()` no longer masks the output log, so its identity, mode, keys, defaults and metadata stay compared. `qualified_graph_problems()` includes the output representation. The fake now models the accepted M-05 topology. | `TestR2AScaleEmptyOutputLog` (9) | G2a; negatives G2a-n1, G2a-n2 | W68–W72 |
| **R2B. EMPTY → one-key Apply** | For a declared side whose origin is EMPTY, only the key structure (keys, times, values, key count, empty flag) is released, and `empty_transition_problems()` requires one layer with exactly one key at time zero equal to the declared effective value, `IsEmpty()` False and ONE_KEY_ZERO (key = new source). Log and layer identities, defaults, compressed data and metadata stay compared. Undeclared sides are fully compared. Keyed origins keep key times, counts, raw time arrays and the empty flag protected, and an origin CPM does not write refuses. Production parity: ONE_KEY_ZERO and STATIC_PLAY recognition (comparator and core) require `IsEmpty()` False, as CPM's `state_kind()` and `flex_static_play_admitted()` do. | `TestR2BEmptyToOneKeyApply` (11) | G2b; negatives G2b-n1, -n2, -n3 | W73–W76 |
| **R3. Abort configuration handoff** | The injector verifies its staged configuration names itself `m06w2_config.json` (or refuses to arm), and passes that identity to its baseline and in-transaction observations. `inv_aborted()` requires A, the baseline, the in-transaction observation and B all to record `m06w2_config.json`. The configuration hashes agree pairwise through `identities()`. | `TestR3AbortConfigurationHandoff` (5), using the real staged Observer → Injector → comparator chain | G3; negative G3-n1 | W77–W80 |

**Refusal attribution.** For every counterexample, `tests/counterexamples.py` records the comparator's reasons and whether the safeguard it targets fired. A new check must never stand in for an older one. During this round, the new configuration-identity check concealed the wrong-instance check in F3d and in `test_contradictory_identities`, whose substitute baseline omitted the configuration. Both now observe that baseline with the ordinary configuration and assert the specific reason. The abort tests now assert their responsible conditions.

**Mutation.** Round 1 (Python 3.10.6) detected 76/80. The survivors W42, W68, W71 and W75 each exposed a test that did not isolate its check: a refusal from arithmetic on a missing value; only empty output logs exercised; a flag only ever changed rather than unsupported in both A and B; and keyed-origin structure enforced only through representation recognition. The tests were added or tightened, with no assertion weakened. Round 2 detected 80/80 on Python 2.7.5 and on 3.10.6.

## Configuration digest validation (R4)

**Authority:** the Owner's *M-06 W2: Final Configuration Digest Validation* (Astra: W2 CORRECTION REQUIRED; R1–R3 accepted).

| Finding | Correction | Tests | Counterexamples | Mutants |
|---|---|---|---|---|
| **R4. Matching invalid configuration digests passed** | `sufficiency()` requires every observation's `config_sha256` to satisfy `sha256_text()`: a string of exactly 64 hexadecimal characters. Anything else is INSUFFICIENT EVIDENCE, reported as `<observation>/config_sha256: … is not a SHA-256 digest`. This covers A, B and, for `aborted`, the injector's baseline and in-transaction observations, which pass through the same check. `config_name` validation and the cross-report equality in `identities()` are unchanged. | `TestR4ConfigDigest` (7), on the real staged Observer → Injector → comparator evidence | H1–H3 (null, empty, "fabricated" in all four); H4 (one contradictory valid-format digest); positive H5 (the actual staged handoff) | W81, W82 |
