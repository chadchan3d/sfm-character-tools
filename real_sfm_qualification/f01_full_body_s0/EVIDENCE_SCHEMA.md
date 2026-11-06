# F-01 full-body S0: expected evidence schema

One observation = one file `observations/S0-NN.json`, format `F01-S0-survey-v1`, written once by
`observer/F01_S0_Survey.py` (exclusive create). `tools/s0_analyze.py` (`validate`) enforces this schema. Handles are
SFM element handles (integers), valid only within one SFM process. An element *identity* is
`{handle, type, name}`. A *field* is `{status: READ, value}`, `{status: ABSENT}` or
`{status: UNREADABLE, error}`: an absent attribute is never confused with an unreadable one.

## Observation

| Key | Content | Answers |
|---|---|---|
| `format`, `label`, `pid`, `python`, `document` | identity; `document` is `GetFileName(GetFileId())` | provenance |
| `session_before`, `session_after` | `head_seconds`, `head_ticks`, `timeline_mode {value, name}`, `undo {can_undo, can_redo, undo_desc, redo_desc}`, `current_shot` | read-only proof; Q10 |
| `readonly` | `digest_before`, `digest_after` (`sha256`, `channels`, `unreadable`) over every authored key of every channel in the document; `unchanged` = both digests and both session states equal | read-only proof |
| `problems` | every condition the observer could not resolve; empty for a usable observation | completeness |
| `shot`, `shots` | the current shot (identity, start, end); every shot with its animation sets | instance identity |
| `animation_set`, `animation_set_name` | the surveyed set (identity, element id, attribute names) | instance identity |
| `channels_clip` | the set's own channels clip, proven by channel membership, and every candidate | M-06 rule |
| `time` | `t_doc`, `t_shot`, `t_chan` (ticks) from the native clip-stack conversion | Q10, Q11 |
| `model` | identity, `modelName`, attribute names, transform state | Q12 |
| `scene` | every element under the shot's `scene`: type, name, parent handles and, for DAGs, `transform`, `local_position`, `local_orientation`, `scale` (field), `world_position`, `world_orientation` | Q1, Q2 |
| `bones` | per model bone (name from `bone N (name)`): `index`, `transform`, `dag`, `parent_dags`, `parent_bone`, transform state | Q1 |
| `rig` | `registrations` (rig, registration element, its attributes, every owned element); `handles`: per `DmeRigHandle` its identity, `parents`, `in_scene`, transform state | Q2, Q6 |
| `controls` | every control of the set: identity and every attribute as a field (values and channel references) | Q3 |
| `channels` | every channel of the set's clip: identity; `binding` (`fromElement`, `fromAttribute`, `fromIndex`, `toElement`, `toAttribute`, `toIndex`, `mode`); `current_ticks` (`GetCurrentTime`); `log` identity, `log_fields`, `log_attributes`; `layers` (type, `key_count`, `first_ticks`, `last_ticks`, `key_at_mapped`, `keys_sha256`, `distinct_values`, `range`, full `keys` when at most 64); `value_at_clock`, `value_at_mapped`; `destination_value` (the driven attribute's current value) | Q4, Q9, Q10, Q11 |
| `operators` | every operator of the set and the shot: identity, `owners`, `slaves` (slot → slave element, its `target`, its attributes), `targets` (target, `targetWeight`, `oOffset`, `vecOffset`, attributes), `pvTarget`, `solver` (`startOffset`, `midOffset`, `poleVector`, `mode`), all other attributes | Q4, Q5, Q6, Q7, Q12, Q13 |
| `writer_index` | document-wide: `destinations` (`"<element handle>:<attribute>"` → every channel writing it, with its source element), `slave_targets` (DAG handle → every operator slaving it), `operator_types` | Q4, Q11, Q13 |
| `cpm_loaded` | `null` unless the CPM module is loaded (the procedure keeps it closed) | isolation |

## Report (`evidence/S0_REPORT.json`, `S0_REPORT.md`)

Format `F01-S0-report-v1`: per observation its validity and read-only result; `readonly`
(`every_observation_unchanged`, `one_document_digest_per_process`); for the primary observation (the first Motion
Editor observation unless named) `analysis`:

- `bones`: per bone `class` from binding evidence only: `constrained` (slaved by a rig constraint; the attributes the
  constraints set; `dormant_slave_base_channels`, the channels writing its `DmeConstraintSlave` base values; and
  `structural_offset_channels`, channels writing an attribute no constraint sets, such as an IK chain bone's
  position), `channel-driven without a control` (written only by channels with no source element), `direct FK` (written only by control channels; per channel its layers, keys,
  distinct values, clock and whether the mapped value equals the bone's local transform; `translation`: *constant
  (structural-offset candidate)* or *animated translation*), `operator-driven` (a channel from an operator, such as
  an expression), `driven by an unknown operator`, `competing writers`, `no writer`, `unclassified`;
- `rig_handles` (parents, writers, constraints on it, roles as target or pole), `operators` (slaves, targets,
  weights and weight channels, pole, solver), `controls` (what each control's channels drive);
- `clocks_by_channel_class` and `off_clock_channels`; `scale`; `unaccounted_bones`; `coverage` counts;

plus `clocks_by_observation`, `instances` (other Krystal instances: structure equality and posture differences) and
`same_instance_other_times`.

A report is **valid** only if every observation passes the schema with no observer problem. The analysis is
evidence for the coverage contract; it does not decide it.
