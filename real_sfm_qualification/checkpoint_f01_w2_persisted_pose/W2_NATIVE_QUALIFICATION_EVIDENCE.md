# F-01 W2 native qualification — evidence manifest

**Experiment:** F-01 W2: persisted left-arm pose capture and independent reapplication after a process restart. Research; not a Pose Library.

**Authority:**
- Astra's corrected W2 design contract (2026-10-28);
- Astra's CLOSED/PASS ruling on the offline candidate (Corrections A and B);
- the Owner's staged authorizations for preparation, Process A, the process gate and Process B;
- Astra's final native qualification ruling: **CLOSED/PASS**.

**Run:** Run_002, 2026-10-30, on one machine (Windows 10, SFM Python 2.7.5; tools on Python 3.10.6).

**Result:** `F01W2 FINAL: PASS`, `reasons: []`.

**Run_001** stopped at its capture step. The playhead was at 0.1667 s, shot15's start tick, and the harness requires a playhead strictly inside the shot. Nothing was written and both copies were unsaved. Its STOP report is listed below; Run_001 is not part of the result.

The raw native reports, the executed configuration and step files, and the pose stay in the owner's local run directory. They are not committed: they contain private local paths and scene data.

## Identities

| Item | SHA-256 |
|---|---|
| Controlling specification: *F01_W2_Astra_Corrected_Design_Contract_2026-10-28* (external attachment) | `168d10910ac48d32016566e29d24823175b56f8a6459e8e459a1143ee62cbe43` |
| Closed W2 package `F01_W2_CLOSURE_CORRECTIONS_A_B_ASTRA_REVIEW.zip` (external; not committed) | `5e90350f91952c618dbcb1602c8d1aaae076fab288cec303bf9822ddb4b08423` |
| `accepted/harness/f01w2_core.py` (committed, byte-exact) | `4042fb1cdc0900aa956e5a8ffd32c9e5c7be609500c05fd8026ee3315854a89d` |
| `accepted/harness/f01w2_capture.py` (committed, byte-exact) | `7e419b5c08a6e0193b2d871f6b2aac1e4f4ba128dc0e3ff6e769b0be031c9617` |
| `accepted/harness/f01w2_apply.py` (committed, byte-exact) | `13601836596979b8e96411bd366827b24c54e00f92ef1ebed6d24f0af218d39b` |
| `accepted/tools/prepare_run.py` (committed, byte-exact) | `24fd0639000012f17f1282c00f039050aac485db9a0241749e61bdb0979e6497` |
| `accepted/tools/finalize_f01w2.py` (committed, byte-exact) | `3802694bd15434e303f0a8631cbf984d419a9cb0517bfa8f469a5832181b6781` |
| `accepted/tests/test_f01w2.py` (committed, byte-exact) | `eb82ce0d54cd665341ba15fa44481bce51ef874a0e2cc4ea3d09d8dc260b5900` |
| `accepted/tests/fake_sfm_w2.py` (committed, byte-exact) | `dbce2e288d08fc6ddb13264147471514d61b8f11c1dae7143ec50982c54391b7` |
| `accepted/config.template.json` (committed, byte-exact) | `ee3d994621cba12472141cb038741a5370d6b453f4d872effac12d03121d0b52` |
| `accepted/INSTRUCTIONS.md` (committed, byte-exact) | `82533d92df5a666ee3038eccfc69f7b1a9a724fc1008409b798550862ccd1ab7` |
| `accepted/POSE_FORMAT_v1.md` (committed, byte-exact) | `d9511b8bc4e1819a5631be7d3441c1b6128c142ac842e9863f55b0c423faed0a` |
| Executed `harness/config.json` (private paths; not committed; see `accepted/config.template.json`) | `ba05b60ee8e8d9439149be2e8e06d40ec177ec928f8b56e3a1646b5f66fbde69` |
| Executed `harness/CAPTURE_STEP.txt` (private path; not committed) | `c9f57d4c15b6525674dafee220f26fab87fee8c1f7ee9a7638e3197a18c4fbb4` |
| Executed `harness/APPLY_STEP.txt` (private path; not committed) | `ee63f13739ad34d2e9d974b315350ba0c01554b533dd3d5146e609d2a14e7008` |
| Executed `HARNESS_SHA256.json` (enforced by `prepare_run.py`; not committed) | `484a56b861b1539ad00a6ed44371838a3106f54806b0e7d2974382ee86ddd19a` |
| Persisted pose `poses/left_arm_pose.f01w2.json` (8,240 bytes; scene data from the private session; not committed) | `ff5a5f42059873e4d0e701145968f025001487a7f12b0f4333be3cb49d3aca28` |
| Run_002 capture disposable copy (unchanged; nothing saved; not committed) | `259ea8a614bc9e43e5bde15afdf38e1a1295dffb50b14cf75692df4221a05a2c` |
| Run_002 application disposable copy (unchanged; nothing saved; not committed) | `259ea8a614bc9e43e5bde15afdf38e1a1295dffb50b14cf75692df4221a05a2c` |
| Original session `<SOURCE_SESSION>.dmx` (never opened; unchanged) | `3af2ad5425c5aa623df47ecfb2737015b8f80260b1ffebe5c2a868ed039b687b` |
| F-01 repository `cpm_source` hashed as a protected file at every step (unchanged) | `6275f04acd7355abeb1ec032d990aa28140de0bfb2cfb6ce1490aef34592ddde` |
| Run_001 STOP report (capture refused at the shot15 boundary 0.1667 s; not committed) | `4cb4f6baaa41925f456f1ffe070390f0c347e26b3a2cfcd222cbe2daeecf70c8` |
| Run_002 closure evidence package `F01_W2_RUN002_NATIVE_CLOSURE_ASTRA_REVIEW.zip` (external; not committed) | `8676cded9e2cb7990e2235a02412e0c2758ce8de3de6f49fd6204052d3e5b696` |
| R2 fixture (read-only source of both disposable copies; unchanged) | `259ea8a614bc9e43e5bde15afdf38e1a1295dffb50b14cf75692df4221a05a2c` |
| Installed product CPM before and after the run (published v1.0.0) | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df` |

## Evidence files (`reports/`): hash-chained ledger

Each step report records its predecessor's SHA-256 (`previous_report_sha256`). The finalizer verified the chain independently.

The table's figures:
- Each figure is measured against the state the step expects, across `bip_UpperArm_l`, `bip_lowerArm_l` and `bip_hand_l`.
- **TRANSFERRED** rows show the primary oracle (local orientation, in degrees) and the secondary oracle (world position, in units) against the pose's goal. The limits are 0.01° and 0.001.
- **BASELINE** rows show the angle and world-position distance from the destination's original baseline.

| Report | Step | Status | PID | Observed state | Max primary (deg) | Max secondary position | Chained | SHA-256 |
|---|---|---|---|---|---|---|---|---|
| `F01W2-01-CAPTURE.json` | CAPTURE | CAPTURE_COMPLETE_PENDING_CLOSE | 26556 | — | — | — | yes | `d75e67ab219911133edea3f9a05302c3a2a6967d29202663821fb954db8f4bfb` |
| `F01W2-02-PROCESS_GATE.json` | PROCESS_GATE | CONTINUE | 23212 | — | — | — | yes | `1e8b4c09385c26c4215ce39117152afeb5e48ee7139304411dc5e66596b90594` |
| `F01W2-03-APPLY.json` | APPLY | CONTINUE | 27252 | TRANSFERRED | 0.000923745 | 9.17e-05 | yes | `9c4b2045f938b7536098945803b0774b48a6f87fc7aecab542d77ac1dbc1e7b2` |
| `F01W2-04-UNDO.json` | UNDO | CONTINUE | 27252 | BASELINE | 2.41484e-06 | 0 | yes | `7b36d207a4491750cacc7d0b68d2998b702a262e271166c43cda9f1093c64ecc` |
| `F01W2-05-REDO.json` | REDO | CONTINUE | 27252 | TRANSFERRED | 0.00107021 | 0.000131 | yes | `768e7c3c36f84d1e424fe1b8a2a9572abbd01173a39bd9b6e746758b42ba3c3f` |
| `F01W2-06-FINAL_UNDO.json` | FINAL_UNDO | COMPLETE_PENDING_CLOSE | 27252 | BASELINE | 2.41484e-06 | 0 | yes | `36f09a73fd1eb95e396070906f28866b445f399e0389ffaf10a1ced85049c7c5` |
| `F01W2-FINAL.json` | FINAL | PASS | — | — | — | — | — | `f1bfdd07d431fa2103f746df4328ba444ce98dc56c775b1d8a15c78dc850edd7` |

**Process identity.**
- Process A is pid 26556, which created the capture.
- The gate ran in a separate system-Python process.
- Process B is pid 27252, which ran APPLY through FINAL_UNDO.

The APPLY report's process-separation evidence: `{"a_created_before_gate": true, "a_not_running_now": true, "b_created_after_gate": true, "b_is_not_a": true, "gate_saw_a_exited": true, "gate_saw_no_sfm": true, "same_provider": true}`.

## Results

| Item | Value |
|---|---|
| Collar-mapping agreement (upper-arm origin; limit 0.001) | 6.47e-05 |
| Independent plan cross-check (quaternion path against matrix path) | `{"agree": true, "elbow_position": 0.0, "hand_orientation_degrees": 1.7075472925031877e-06, "hand_orientation_degrees_matrix_path": 1.7075472925031877e-06, "hand_orientation_same_hemisphere": true, "hand_position": 0.0}` |
| Hand-target residual: saved in the pose / observed after the commit | 0.0513914 / 0.0513676 |
| Write accounting (finalizer) | `{"aborted_test_writes": 1, "committed_writes": 6, "native_history_operations": ["Undo", "Redo", "Undo"]}` |
| Propagation (finalizer) | `{"committed": "IDLE", "final": "IDLE", "redone": "IDLE", "undone": "IDLE"}` (no retime required) |
| Protected files (finalizer) | original session, R2 fixture, both disposable copies, `cpm_source`, harness and configuration: all unchanged |
| Harness manifest enforced by `prepare_run.py` | `HARNESS_SHA256.json` `484a56b861b1539ad00a6ed44371838a3106f54806b0e7d2974382ee86ddd19a` |

## Observations carried to review

1. **Capture `file_id: 0`.** This is recorded in the capture context. The harness accepted the capture, and nothing in W2's acceptance depends on the file id. It is preserved, not interpreted.
2. **Source shot not re-observed in Process B.** The finalizer says so itself: *"W1 source-preservation evidence is unchanged and not extended."*
3. **No retime required.** Every Process B stage reached its expected idle state on the first observation.

## Offline qualification of the accepted package

`accepted/tests/test_f01w2.py`: **162/162** on Python 2.7.5 and 3.10.6. Mutation: **67/68 detected**. The survivor, M50, is reported, not reclassified; see `README.md`.
