# F-01 Stage 2: native Tails qualification, results (2026-11-19)

**Authority:** the Designer's "F-01 Stage 2 — Native Qualification GO" (ACCEPT kit `cbe30f6`, with the Process A
posing correction; native execution authorized). Preparation and the correction: `F01_STAGE2_TAILS_NATIVE_PREPARATION.md`
(sections 1 to 6), checkpoint `b48002a`. Procedure: `real_sfm_qualification/f01_stage2_tails/PROCEDURE.md`
(`fccf5ecc…`).

The three results below are reported separately and are not combined.

| Result | Value |
|---|---|
| **Automated verdict** (`S2T_VERDICT`, analyzer `a76b7a80…` unchanged) | **FAIL**: 76 of 77 checks PASS. The only failure is `navigation.pose_holds_after_moving_away_and_back` (HISTORY) |
| **Owner visual acceptance** | **PASS** |
| **Restoration** | **RESTORED**: published v1.0.0 CPM `ccbed9d7…`, no registries, preset library and protected inventories exact |

## 1. Identities

| Item | Value |
|---|---|
| Candidate CPM | `001377f9704ffd4e52503330feea2d4dcf271dd9541a6889d109f6801985de70` |
| Qualification build (installed temporarily) | `7d3ed720f77e9abc0a176a2d8e499c2145d016f866b439e7f7eccf07922d1813` (line 42630 only) |
| Analyzer | `s2t_analyze.py` `a76b7a8041a724167b6482da8d89a48994fcdfbc4072b4dff1539e28980e74f9` (unchanged since `cbe30f6`) |
| `S2T_VERDICT.json` | `3673910496687728df0a313ab7cd75ef29b2e262558fb6c20e3039c4de25c430` |
| `S2T_VERDICT.md` | `f6e58ac40273d632d75b11f70e5f46535aec4bff02dd15292dc3a081bc774858` |
| Session copy after Process A | `59faf7f497e70382900017e72f5569ed2ba67978599d33deaa28e122a3bfe99a` (SFM saved it with a lower-case file name, `s2t_session.dmx`; the analyzer compares names case-insensitively) |
| R2 fixture | `259ea8a6…`, only read, unchanged after the run |
| Saved pose | `Characters/milestailsprower--caebe27de7ca/Poses/S2 Tails--6ff1bab95e82.json` `fd08e4cb…` (moved out by restore; recorded in `evidence/library_Q.json`) |
| CPM logs | Process A `pid34892` `f85af0b6…`; Process B `pid28292` `3bf01490…` |
| Run folder | `E:\SFM_U0B_Scratch\f01-stage2-tails-r1` (`observations/`: 7 captures, 7 leaf sidecars; `evidence/`) |

**Instances:** Tails S `milestailsprower2`, Tails D `milestailsprower3`, peer `milestailsprower1` (the session's
original Tails, untouched).

## 2. Automated result by gate

| Gate | Result |
|---|---|
| EVIDENCE | PASS (39/39) |
| PREP | PASS (7/7) |
| SAVE | PASS (6/6) |
| APPLY | PASS (6/6) |
| POSTURE | PASS (3/3) |
| HISTORY | **FAIL** (4/5) |
| LEAVES | PASS (7/7) |
| PEER | PASS (4/4) |

**Stage 2 evidence (information from the verdict, not a reinterpretation of it):**
- **Leaves:** the seven header-declared JIGGLE leaves (`ear3_L/R`, `HairSpike_B3/M3/T3`, `Tail6_L/R`) were admitted as
  `simulated-leaf` on Tails S and Tails D at every capture. No refusal occurred.
- **Save:** one `structural_rig_v1` **revision 2** record describes the seven leaves with no value or oracle.
- **Apply:** 236 target channels changed, all drafted written channels; the leaves were not authored by CPM; P7 was
  verified.
- **Posture:** Tails D matched Tails S's saved posture independently over 124 non-leaf bones. The maximum deviation
  was 0.00011 units and 0.00047°, against a tolerance of 0.05 units and 0.5°. Placement and facing were unchanged.
- **Leaf channels, scale and declarations:** unchanged at every capture for S, D and the peer. The simulated tips'
  local positions did not change from BASE.
- **Undo and Redo:** UNDO restored BASE exactly (authored state and non-leaf skeleton), with `Redo Apply Pose S2 Tails`
  pending; REDO restored APPLY.

## 3. The failed check and the Owner's procedural observation

**The Owner's observation (preserved as reported):** navigating created an additional SFM Undo entry named
`Modify Time Selection`. The Owner therefore chose Undo **twice**: first to remove that entry, then to undo
`Apply Pose S2 Tails`. The UNDO capture showed `Redo Apply Pose S2 Tails`, and REDO restored the applied pose.

**The check:** `navigation.pose_holds_after_moving_away_and_back` requires all three of:

| Component | NAV against APPLY | Result |
|---|---|---|
| Tails D's authored channel digests | identical | holds |
| Tails D's non-leaf skeleton (124 bones) | identical within tolerance | holds |
| SFM's Undo state | APPLY `undo_desc` `Apply Pose S2 Tails`; NAV `undo_desc` `Modify Time Selection` | **differs** |

So the check failed **only** on the Undo-state component, and that component differs exactly as the Owner described. The
pose itself held through navigation. The playhead read 0.2083 s at NAV, in the Motion Editor, on shot15. These component
values were read from the captures with the analyzer's own helpers; the analyzer and verdict were not changed.

**Consistent evidence in the other captures:**
- UNDO: `undo_desc` `Change Recording State` (the same as BASE), `redo_desc` `Redo Apply Pose S2 Tails`.
- REDO: `undo_desc` `Apply Pose S2 Tails`, `redo_desc` `Modify Time Selection`. The extra entry sat above Apply on
  the Redo stack after the two Undos, which agrees with the Owner's account.
- `undo.history` and `redo.target_equals_apply` passed, because they compare `undo_desc` with BASE and APPLY, and the
  Owner's two Undos placed the history in exactly those states.

**Effect on the unchanged analyzer:**
- **The navigation check:** the extra entry makes this check fail by construction. It expects the top Undo entry
  after navigation still to be CPM's Apply.
- **The UNDO capture:** the second Undo (a deviation from step B6's "once") did not make any check fail. It made the
  UNDO capture comparable at all. With one Undo, SFM would have undone only `Modify Time Selection`, and
  `undo.target_authored_state_equals_base`, `undo.history` and `undo.non_leaf_skeleton_back_to_base` would have failed.

**Comparison with the Fox run (for context only):**
- In Fox run 3 (`f01-stage1-fox-r3`), the same Left/Right arrow navigation left `undo_desc` at `Apply Pose S1 Fox`.
- The evidence does not show why SFM recorded a time-selection change in this run (for example, the timeline's
  keyboard focus or a click in the time bar). CPM records no such entry; the CPM logs show no CPM history action
  between APPLY and NAV.
- The cause is not established and is not claimed.

**Not done:** the verdict is not reinterpreted. No check is waived, and the analyzer, procedure and evidence are
unchanged. No native test is repeated.

## 4. Owner visual acceptance: PASS (as reported)

- Process A: `milestailsprower2` (S) and `milestailsprower3` (D) were created and rigged. PREP and SAVED reported
  `errors none`, 7 | 7 simulated leaves, headers READ READ. `Pose saved: S2 Tails.` The pose and characters looked
  correct. The session copy was saved once, and SFM exited.
- Process B: BASE, APPLY, NAV, UNDO and REDO all reported `errors none`, 7 | 7 leaves, READ READ, and sidecar written.
- The applied pose looked correct, with no severe deformation, unexpected movement or visible damage.
- Undo and Redo worked (with the two-Undo sequence in section 3).

## 5. Restoration

| Step | Result |
|---|---|
| `library Q` | 2 differences, both from the one Tails pose: the pose file and the new character's `pose_sources.json` |
| `collect-logs` | 2 CPM logs (Process A and Process B) |
| `restore` | `RESTORED`: the run's two files and two folders removed; folders and files equal the pre-run backup; `inventory_problems` empty |
| `check` | `"installation": "published"`, `ccbed9d7…`, both registries absent |
| Analyzer evidence checks | `restore.library_exactly_as_before` PASS; `restore.published_and_inventories_equal` PASS |

The R2 fixture `259ea8a6…` is unchanged. The run folder is kept as evidence.

## 6. Stage 2 status

- **Automated verdict:** FAIL (one HISTORY check, the Undo-stack component of navigation). It is recorded as is and
  preserved.
- **Owner visual acceptance:** PASS.
- **Restoration:** RESTORED.
- **Disposition:** for the Owner and Designer. This record proposes no procedure change, analyzer change, repeat run
  or adjudication.
- **Not done:** no production promotion, signing, push, merge or release.
