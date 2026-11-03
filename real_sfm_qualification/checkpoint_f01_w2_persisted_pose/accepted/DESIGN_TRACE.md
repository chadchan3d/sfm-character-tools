# F-01 W2 design trace

This file traces each clause of *F01_W2_Astra_Corrected_Design_Contract_2026-10-28* to the code that
implements it and the offline tests that exercise it.

**Path abbreviations**
- `core` is `harness/f01w2_core.py`; `capture` and `apply` are the other two harness files.
- `prepare` is `tools/prepare_run.py`; `final` is `tools/finalize_f01w2.py`.
- Tests are named by class and method in `tests/test_f01w2.py`.

## §1 Scope

| Clause | Implementation | Tests |
|---|---|---|
| Model `krystal2020.mdl`, animation set `Krystal`, shot15/f5 to shot10/f10 | `config.template.json`; `core.resolve`, `core.context` | `TestPreflight.test_model_mismatch`; `TestCaptureIntegrity.test_wrong_document_place_and_frame` |
| Only `Hand_l_p`, `Hand_l_o`, `Elbow_l_p`; existing keys at 30000 and 70415, indices resolved per channel | `core.WRITE_CHANNELS`, `core.write_targets`, `core.find_bracket` | `TestProcedure.test_per_channel_bracket_indices_and_write_accounting` (`Hand_l_o` writes go to indices 1 and 2) |
| No key insertion, creation, GUI, CPM or schema change | Writes only through `core.write_key` → `SetKeyValue` | key times unchanged (test above); `write_key` records `count_unchanged` and `time_unchanged` |
| W1 not rerun or modified | The W1 files are untouched; their mechanisms are copied into `core` | `git status` (the W1 folder is unchanged) |

## §2 Designer decisions

| Clause | Implementation | Tests |
|---|---|---|
| Two distinct, byte-identical copies of R2, neither saved | `prepare.prepare`, `core.check_config`, `core.integrity`, `prepare.gate`, `final.main` | `TestPrepare.test_manifest_and_prepare`, `test_config_must_name_four_distinct_files_and_fixed_pose_path`; `TestProcessSeparation.test_gate_refuses_saved_capture_copy`; `TestFinalizer.test_saved_disposable_copy_is_stop` |
| Fixed path `<RUN_DIR>/poses/left_arm_pose.f01w2.json`; refuse an existing file; same-directory temp file, flush+fsync, no-replace rename, read back and hash | `core.publish_pose`, `core.no_replace_rename`, `core.write_exclusive` | `TestPublication.test_platform_rename_refuses_existing_target`, `test_preexisting_pose_refuses_and_is_not_overwritten` |
| Interrupted publication is not qualified; the temp file has a non-pose name | temp file `INCOMPLETE-<nonce>.f01w2-capture.tmp`; the success record is written only after publication | `TestPublication.test_interrupted_before_rename_leaves_no_pose`, `test_interrupted_after_rename_without_record_refuses` |
| Process B needs a complete capture record AND a matching hash (a harness condition, not a format dependency) | `apply.capture_evidence`, `apply.load_snapshot`; the format has no sidecar field | `TestPublication.test_pose_changed_after_gate_refuses_application`, `test_capture_record_hash_binding_cannot_be_forged_without_breaking_the_chain` |
| Synthetic offline fixtures; no private captures | `tests/fixtures/synthetic_scene.json`, `tests/fake_sfm_w2.py` | the whole suite (no R3 input) |

## §3 Pose format

| Clause | Implementation | Tests |
|---|---|---|
| 64 KiB, identifier, version 1, closed schema | `core.POSE_SCHEMA`, `core.parse_pose`, `POSE_FORMAT_v1.md` | `TestPoseFormat.*` |
| Reject unknown, duplicate or missing fields, wrong versions or types, component counts, non-finite numbers, magnitudes, invalid UTF-8 | `core.validate_node`, `core.unique_pairs`, `core.reject_constant` | `TestPoseFormat.test_unknown_missing_and_type_errors`, `test_committed_adversarial_fixtures`, `test_size_and_input_type` |
| No code execution | parser uses `json` only | `TestPoseFormat.test_parser_never_executes_content` |
| Units, `[x,y,z,w]`, W1 composition, collar frame | `core.CONVENTIONS` (constants, validated) | `TestPoseFormat.test_unknown_missing_and_type_errors` (wrong `units` or `quaternion_order` rejected) |
| Full precision; float32 only at the write | `core.build_payload` (doubles), `core.plan_quaternion` (`f32` at the end) | `TestProcedure.test_capture_bytes_are_deterministic_golden` |
| `abs(norm(q)-1) <= 1e-4`, never normalized silently | `core.validate_node` (`quat`) | `TestPoseFormat.test_quaternion_norm_tolerance` |
| Hand transform and elbow position relative to `CollarL`; no elbow orientation | `core.build_payload` | `POSE_SCHEMA` (an extra field is rejected) |
| Independent oracle data read from evaluated bones | `core.build_payload` reads `capture_skeleton` bone DAGs | `TestProcedure.test_goals_match_independent_expectation` |
| Diagnostics never authoritative | `diagnostics` is used only to report `saved_hand_target_residual` | — |
| No handles, pids, Undo identities, paths or W1 data | `core.descriptor` (names and roles only), `core.portable_value` (refuses element references) | `TestProcedure.test_pose_file_has_no_runtime_identities` |

## §4 Compatibility and fresh binding

| Clause | Implementation | Tests |
|---|---|---|
| Model, bone names, indices, parents, local offsets (1e-4) | `core.descriptor`, `core.compare_descriptor` | `TestPreflight.test_bone_index_differs`, `test_arm_bone_offset_differs`, `test_arm_bone_offset_within_bound_is_accepted` |
| `Hand_l`/`Elbow_l` parented to `rig_root`; `CollarL` parent recorded, not assumed | `core.structural_checks`, `core.parent_role` | `TestPreflight.test_hand_handle_parentage` |
| Scales absent or 1; weights 1 (1e-6) | `core.structural_checks`, `core.compare_descriptor` | `TestPreflight.test_unsupported_scale`, `test_constraint_weight`, `test_constraint_extra_target` |
| Control roles, mode 3, log/layer types, one layer, curve info, indices | `core.channel_binding` (all four channels, including observed `Elbow_l_o`) | `TestPreflight.test_channel_mode`, `test_observed_channel_binding_change`, `test_layer_curve_info` |
| IK joints, pole target, hand-orient and collar relationships, solver fields, offsets, exact types | `core.structural_checks` (by identity), `core.descriptor` | `TestPreflight.test_pole_target_identity`, `test_name_alone_is_not_identity`, `test_ik_joint_identity`, `test_solver_field_differs`, `test_solver_field_absent`, `test_target_offset_differs` |
| Document-wide writer uniqueness, graph sharing, operator whitelist | `core.writer_index`, `core.check_writers` | `TestPreflight.test_competing_writer_in_another_shot`, `test_constraint_driving_rig_handle`, `test_channel_writing_control`, `test_shared_log`, `test_unknown_operator_type` |
| One unique key at each bracket, consecutive, no key between | `core.find_bracket` | `TestPreflight.test_bracket_key_missing`, `test_bracket_key_duplicated`, `test_intervening_key` |
| Unreadable relationships refuse | strict reads (`Unresolved`) | `TestPreflight.test_unreadable_required_relationship` |
| Log values at both clocks agree with effective inputs | `core.hold_state` (A and B) | `TestCaptureIntegrity.test_effective_log_disagreement` |

## §5 Capture-integrity gate (process A)

| Clause | Implementation | Tests |
|---|---|---|
| Process A's document, shot15, frame 5, clocks | `core.context` (`capture_session`) | `TestCaptureIntegrity.test_wrong_document_place_and_frame` |
| Bindings and effective/log agreement | `capture.snapshot`, `core.hold_state`, `core.check_writers` | `TestCaptureIntegrity.test_effective_log_disagreement` |
| Oracle from evaluated bones | `core.capture_skeleton` → `build_payload` | golden test |
| Authored state and Undo history before and after; no change attributable to capture | `capture.capture`: second snapshot, `completion_gate` | `TestCaptureIntegrity.test_authored_change_during_capture`, `test_undo_history_change_during_capture`, `test_evaluated_change_during_capture`; `TestProcedure.test_capture_is_read_only` |
| Revalidate process, document, shot, frame, time and bindings at completion | `completion_gate` (context, process, binding_identity) | same |
| Protected files unchanged before publication | `core.integrity` compared before publishing | `TestCaptureIntegrity.test_protected_file_change_during_capture` |
| Exact temp bytes validated; publish only after every gate; success record bound to the hash | `core.publish_pose`, capture report `publication` | `TestPublication.*` |
| No writes, history commands, saves, forced evaluation or playhead change | `capture` has no mutating call | `TestProcedure.test_capture_is_read_only` (`dm.calls == []`, keys unchanged) |

## §6 Mapping and independent cross-check

| Clause | Implementation | Tests |
|---|---|---|
| `Hc`, `Ec`, collar-relative skeleton | `core.build_payload` | `TestProcedure.test_goals_match_independent_expectation` |
| `Hd_local = inverse(Rd) x Cd x Hc`; `Ed` likewise | `core.plan_quaternion` | same |
| Second implementation using matrices, not wrapping the first | `core.plan_matrix` and `core.mb_*` | `TestIndependentPlans.test_matrix_path_calls_no_quaternion_helper` (AST check); mutation M05 detected |
| Compare float32 goals within 1e-4 / 0.001°, sign-invariantly; one hemisphere | `core.cross_check` | `TestIndependentPlans.test_cross_check_is_sign_invariant_but_requires_one_hemisphere`, `test_disagreement_refuses_before_mutation` |
| Hemisphere chosen against the current destination key | `core.plan_quaternion` (`reference` = the bracket key value) | `TestIndependentPlans.test_hemisphere_follows_the_replaced_key` |
| Shoulder guard (0.001) | `core.shoulder_guard` | `TestPreflight.test_shoulder_guard` |
| Live check, not fixed constants | no stored cross-check constants in the W2 config | — |

## §7 Source independence (process B)

| Clause | Implementation | Tests |
|---|---|---|
| A genuine restart; process identity and start evidence; A exited before B began (with creation-time evidence) | `core.WindowsProcesses`, `core.process_evidence`; `prepare.gate` (A not running by pid and creation time, no `sfm.exe`, gate time); `apply.process_separation`; `final.process_audit` | `TestProcessSeparation.*`; `TestProcedure.test_pid_reuse_is_not_mistaken_for_the_same_process`; `TestFinalizer.test_process_tampering` |
| Load once, as an immutable snapshot | `apply.load_snapshot` (one read), payload kept in the report | `TestPublication.test_snapshot_read_exactly_once` |
| Values only from the file and the live destination; no source queries or helpers; no `resolve_other` | `apply` never resolves `'source'`; `core` has no `resolve_other`; `apply.capture_evidence` reads only status, hash and process | `TestSourceIndependence.test_application_never_reads_captured_payload_from_the_ledger`, `test_application_succeeds_with_source_values_destroyed`; full run with 65 poisoned source elements and zero hits (`TestProcedure.test_full_procedure_pass`) |
| Detector for indirect access | the fake poisons source-pose reads | `TestSourceIndependence.test_poison_detector_catches_indirect_source_access`; mutation M12 detected |
| The writer inventory may read metadata only | `core.writer_index` | `TestSourceIndependence.test_writer_inventory_reads_only_metadata` |

## §8 Mutation, oracle, recovery

| Clause | Implementation | Tests |
|---|---|---|
| Deferred one-shot callbacks; context and binding re-verified before each | `core.schedule`, `apply.step_apply.entry`, `apply.common_destination` | `TestTransactions.test_context_change_before_commit`; `TestProcessSeparation.test_later_steps_must_stay_in_process_b` |
| One aborted test write, counted separately | `apply.abort_check` | `TestTransactions.test_abort_check_write_raises`, `test_abort_raises_is_recovery_unverified`, `test_abort_does_not_restore`, `test_unreadable_after_abort_is_stop`, `test_writes_ignored_is_detected` |
| Six committed writes, exact readbacks, clocks, authored = baseline + six | `apply.commit` | `TestTransactions.test_commit_failure_midway_aborts_and_verifies`, `test_commit_readback_mismatch`, `test_commit_failure_with_unreadable_recovery` |
| Owned Undo, Redo, final Undo; ownership before and after; exact states | `apply.step_history` | `TestTransactions.test_foreign_top_entry_before_undo`, `test_mangled_description_after_commit`, `test_redo_ownership`, `test_undo_without_exact_restoration`, `test_unreadable_after_undo_is_stop`, `test_undo_disabled` |
| Primary 0.01°, secondary 0.001 / 0.01°; disagreement never waived; preservation classes | `core.classify` (W1), `core.oracle_from_pose` | `TestTransactions.test_oracle_disagreement_never_waived`, `test_unrelated_bone_change_fails` |
| One bounded retime, labelled `RETIMING_DEPENDENT` | `apply.step_retime`, `apply.finish_observation` | `TestProcedure.test_retime_dependent_procedure` |
| No claim about the source shot in process B | `final.main` (`not_claimed`); README | — |

## §9 Finalizer

| Clause | Implementation | Tests |
|---|---|---|
| Independent of the harness; full chained audit; pose bytes; process separation; write accounting (1 + 6) and history; brackets and float32; observations; protected files | `final` (own parser and own arithmetic: Euler–Rodrigues) | `TestFinalizer.*` |
| A status alone is not evidence; tampering detected | `final.audit` | `TestFinalizer.test_status_alone_is_not_evidence`, `test_write_accounting_tampering`, `test_plan_tampering_detected_independently`, `test_grammar_and_status`, `test_finalizer_chain_tamper`, `test_pose_file_changed_after_run` |
| Native PASS only with kernel32 process evidence | `final.process_audit` (`offline` must be passed explicitly by tests) | `TestFinalizer.test_native_provider_required_without_offline_flag` |

## §9a Correction round: Astra adjudication of 2026-10-29 (F-01 to F-05)

Astra's modified remedies govern wherever they differ from Argon's audit. Each Argon counterexample was
reproduced against the reviewed candidate first and is rejected by this one (`qualification/` in the review
package). The tolerances, the write set (three channels, six keys and one aborted test write), the coordinate
mapping, the persistence format and the Owner-controlled retime are all unchanged.

| Remedy | Implementation | Tests |
|---|---|---|
| **F-01:** exactly three arm-bone records; each error a finite, nonnegative number (booleans and malformed values rejected) | `final.observation_complete`, `final.error_value` | `TestF01SkeletalEvidence.test_missing_and_malformed_bone_records` |
| **F-01:** TRANSFERRED within the primary and secondary tolerances with `inputs_at_goal`; BASELINE within the baseline tolerances with `inputs_at_baseline`; applied to every accepted observation, including the abort baseline and retimed observations | `final.accepted(observation, expect, tol)` | `test_out_of_tolerance_with_summary_flags_unchanged`, `test_rig_inputs_must_match_the_expectation` |
| **F-01:** an unsuccessful idle observation must hold complete evidence and satisfy preservation before a retime is allowed | `final.audit` (NOT_AT_IDLE branch); `apply.finish_observation` (a skeletal preservation failure at idle is FAIL and is not sent to retime) | `test_unsuccessful_idle_observation_must_be_complete_before_retime`, `test_idle_preservation_failure_is_not_sent_to_retime` |
| **F-02:** capture context (document, shot, playhead, shot-media clock, pid); every process B context consistent with the APPLY context and the destination baseline; `PROCESS_GATE` has no scene context | `final.context_problems`, `final.identity_of` | `TestF02EvidenceFinalization.test_wrong_context_on_every_scene_step`, `test_retime_context_is_audited`, `test_gate_needs_no_scene_context` |
| **F-02:** process identity by pid and creation time; provider consistency, including the gate's provider; in a native run the report pid equals the queried pid | `final.process_audit` | `test_native_process_identity_and_provider` (a native re-expression of the ledger passes, then each forgery is refused) |
| **F-02:** complete protected-file evidence on every report, identical across the run and equal to the configured hashes | `final.integrity_problems`, `final.audit` | `test_complete_protected_file_evidence_on_every_report` |
| **F-02:** the actual compatibility descriptor and preflight results, recomputed, with the live descriptor tied to the recorded destination baseline | `final.compatibility_problems` | `test_compatibility_descriptor_and_preflight` |
| **F-02:** shoulder-origin guard recomputed; both planning implementations compared against the independent goals; orientation compared sign-invariantly, with the hemisphere required only of the two authored keys | `final.plan_independently_ok` | `test_shoulder_guard_recomputed`, `test_both_planning_implementations_against_independent_goals` (a sign-flipped second result is accepted) |
| **F-02:** `observed_changes` explicitly empty on every observing step | `final.audit` | `test_observed_changes_must_be_explicitly_empty` |
| **F-03:** shared validator for the required history fields (booleans, readable strings, no sentinels); `GetUndoItemCount` stays diagnostic | `core.history_problems`, `core.require_history`, `core.history_changes` | `TestF03UndoEvidence.test_non_boolean_history_flag_is_unreadable`, `test_unreadable_item_count_alone_does_not_block_capture` |
| **F-03:** capture: required history readable and unchanged; unreadable means INCONCLUSIVE with nothing published | `capture.capture` (`undo_at_start`, `undo_at_completion`) | `test_identically_unreadable_capture_history_is_inconclusive` |
| **F-03:** unreadable before any write is INCONCLUSIVE; unreadable after a mutation is STOP (recovery/ownership unverified) | `core.require_history(…, mutated)` | `test_unreadable_history_before_any_write_is_inconclusive`, `test_unreadable_history_after_abort_stops_before_commit`, `test_unreadable_history_before_and_after_undo_is_stop` |
| **F-03:** Abort test and failed-commit Abort: authored state and required history restored, aborted labels absent; a changed history stops with its evidence (never cleared or repaired) | `apply.abort_check`, `apply.commit` (failure path) | `test_history_changed_by_abort_stops_without_repair`, `test_failed_commit_abort_must_restore_history` |
| **F-03:** callback boundaries recheck readable history as the experiment left it; commit owns the Undo entry; Undo/Redo own the entry before and the opposite entry after | `apply.history_boundary`, `apply.same_history`, `apply.owned_undo`, `apply.owned_redo`, `apply.expected_history` | `test_history_changed_between_abort_and_commit`, `test_false_redo_availability_after_undo`, `test_false_undo_availability_after_redo` |
| **F-03:** finalizer audits readable before/after history for capture completion, preflight, the Abort test, the commit, Undo, Redo and the final Undo | `final.history_readable`, `final.same_history`, `final.owned_undo`, `final.owned_redo` | `test_finalizer_requires_readable_restored_owned_history` |
| **F-04:** a preservation gate before accepting an observation, before offering a retime and before continuing; a recheck immediately before every native history operation (abort check, commit, Undo, Redo, final Undo), including after an Owner-controlled delay | `apply.preservation_gate`, `apply.finish_observation`, `apply.step_retime`, `apply.step_history.perform` (operator/constraint attributes and skeletal preservation) | `TestF04Preservation.*` (before the abort check, at APPLY idle, at an unsuccessful idle, before Undo/Redo/final Undo, at the history observation, at retime, skeletal change before Undo) |
| **F-04:** on a change or on unreadable preservation evidence: record, STOP, emit no next action, refuse later submissions, and make no compensating Undo, Redo or write | `apply.observed_now` (unreadable after a mutation is STOP), `core.due_step` | each `TestF04Preservation` case asserts the exact native call list and that a later submission reserves nothing; `test_unreadable_preservation_evidence_after_mutation_is_stop` |
| **F-05:** strict lookup of the recorded process: ABSENT (ERROR_INVALID_PARAMETER), EXITED, PID_REUSED, RUNNING or UNKNOWN; access denied or any other failure is UNKNOWN, never an exit | `core.WindowsProcesses.lookup`, `core.recorded_process_state`, `core.EXITED_STATES`; `prepare.gate`; `apply.process_separation` (`process_a_now`); `final.process_audit` | `TestF05ProcessQueries.test_targeted_lookup_distinguishes_absent_denied_exited_reused`, `test_gate_refuses_when_process_a_cannot_be_queried`, `test_gate_records_verified_exit_absence_and_reuse`, `test_apply_refuses_when_process_a_becomes_unqueryable` |
| **F-05:** best-effort enumeration kept separate (inaccessible processes skipped, exited processes filtered out); handles always closed; native error codes kept in diagnostics | `core.WindowsProcesses.images`, `core.WindowsProcesses._open` | `test_images_is_best_effort_and_filters_exited` (scripted kernel32: opened handles equal closed handles) |

## §9b Closure round: Astra Corrections A and B

| Correction | Implementation | Tests |
|---|---|---|
| **A:** after a native mutation, unreadable required authored, preservation or recovery evidence is STOP (unverified) at synchronous entry, in deferred callbacks and at retime; before any write it remains INCONCLUSIVE; STOP schedules nothing more, emits no next action and makes no compensating call | `core.POST_MUTATION_STEPS` (RETIME, UNDO, REDO, FINAL_UNDO: every step after APPLY's commit) in `core.run_entry`; `core.guarded(…, mutated=True)` for the APPLY `commit` callback (after the aborted test write), `observe_idle` and the history `perform` callback. The abort check itself, before its write, stays INCONCLUSIVE. | `TestCorrectionAPostMutationStop.*`: at UNDO/REDO/FINAL_UNDO entry; between entry and the deferred callback; after the history operation; at retime of every stage; after the aborted test write before commit; after commit before the idle observation; restoration unreadable after an aborted mutation; pre-write INCONCLUSIVE preserved |
| **B:** the finalizer validates the raw process-A lookup behind the gate and APPLY classifications. ABSENT needs an explicitly recorded null lookup; EXITED the same pid and creation time with `running` False (and no STILL_ACTIVE exit code); PID_REUSED the same pid with another valid creation time. A recorded error, UNKNOWN, or missing, malformed or contradictory fields are refused. | `final.lookup_problems`, `final.process_audit` | `TestCorrectionBLookupEvidence.*`: full `main()` with `offline=False` on native-form ledgers with regenerated hash chains (the gate claims an exit but its lookup was denied; APPLY likewise; gate lookup records omitted; consistent ledger passes); per-state acceptance and refusal matrix. `native_ledger` keeps the raw lookup pids consistent with process A. |

## §10 Allowlist

Every file lives under `real_sfm_qualification/f01_w2_persisted_pose/`. The gate is a subcommand of the
allowlisted `tools/prepare_run.py`; there is no separate tool. The root `.gitattributes`, the W1 checkpoint,
CPM, the Normalizer, the Ledger, the Blueprint, the backlog and the M-06 worktree are untouched.
