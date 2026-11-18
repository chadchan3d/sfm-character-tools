# F-01 H1 — Native Heavy procedural-helper check: results

**Date:** 2026-11-17. **Authority:** Owner authorization "F-01 H1 — Native Execution Authorization — OWNER GO"; Owner
completion report "F-01 H1 — Owner Native Results" (**Owner visual acceptance: PASS**); Designer "F-01 H1 — Analyzer
Correction Authorized" (Option 2). Related: `F01_H1_HELPER_COMPATIBILITY.md`; kit `real_sfm_qualification/f01_h1_heavy/`.

**Disposition: H1 CLOSED / PASS.** The original analyzer verdict **INCOMPLETE** stands unchanged as the run's first
verdict (one evidence check, caused by an analyzer allow-list omission, section 4). The Designer-authorized corrected
analyzer, replayed on the same unchanged native evidence, gives **AUTOMATED PASS** (62/62 checks). With the Owner's
visual acceptance, H1 is natively qualified on the known Heavy. It is **not promoted**: the published v1.0.0 remains
installed and unchanged. The OT1, OT1S, Q1 and PS-2 verdicts and their recorded limitations are preserved unchanged.

## 1. Identities

| Item | Identity |
|---|---|
| Kit checkpoint (native run) | `0552eb8` |
| H1 candidate CPM (`7310171`) | `3d31e72141a50fca3a9b10f5ae0970af3b7f2253a66f4f6f8a03e38c28e29d1e` |
| Qualification build (line 42546 only, `PROD_POSE_REGISTRY_MODE`) | `5a8c832bf7dd385188014178fcc43c80074b0d18a192320406e5322b181d0a05` |
| Capture `observer/F01_H1_Capture.py` (unchanged) | `faad5d4cb7d7084dfca635fe8df1821972edb656a87410249a4f40133ff50a5e` |
| `PROCEDURE.md` (unchanged) | `257d3b6d0f71a2a58ab668bc0d2621f1965cd00e6c7ee89ffb2c69fc415de186` |
| Original analyzer `tools/h1_analyze.py` (run verdict) | `d7af5d94fc268ff56792257d3fa8cb1dc51af07f164e802bb5f7f1d13b31578a` |
| Corrected analyzer (replay verdict; re-pinned in `h1.template.json`) | `effcf928455b2482604159e728d2237be4bf0827db6c9a2787a6607eb8c2d306` |
| Run config `h1.json` | `9594831a…` |
| Session `H1_SESSION.dmx` (R2 fixture copy; after the run) | `259ea8a6…` (unchanged, never saved) |
| `H1_SPARE.dmx` (copied by the reused `pre`, never opened) | `61df8bcd…` (unchanged) |
| Published installation before and after | v1.0.0, CPM `ccbed9d7…`; both registries absent |
| Run folder (raw evidence, not committed) | `E:\SFM_U0B_Scratch\f01-h1-heavy-r1` |

**Verdict files:** original `evidence/H1_VERDICT.json`
`2b721b4a2fb0851f93def7ef06408e7adda9d088f719ace7f32ac0585468ebd6`, `evidence/H1_VERDICT.md`
`e3fbbe401761cee484b88b8d98882dd31c7f0b6ad73ac46fdc64f8d0f2da6ff2` (unchanged); replay
`evidence/H1_REPLAY_VERDICT.json` `e360eda430a389fda77eb1e09e379c4108e91b0a571497cfef59b4af954a6b0b` (records
`replay_of_verdict_sha256` = the original's), `evidence/H1_REPLAY_VERDICT.md`
`d8aab58f77c35394365e74071624311fc6054974ccdf46151c1183ba57c16145`.

**Evidence files (unchanged by the replay; all 22 rehashed before and after):** captures `H1-BASE.json`
`50ae748f…`, `H1-SAVED.json` `47e5a841…`, `H1-APPLY.json` `90e4ed5a…`, `H1-UNDO.json` `53a7eff9…`, `H1-REDO.json`
`3a7136b2…`, `H1-NOOP.json` `9fbcded9…`; CPM log `CPM - 2026-11-18_02-53-35Z - pid7888 - 15f2c4 - 001.log`
`a7d43b1d…` (132 lines); `library_Q.json` `b9d7af84…`; `library_cleanup.json` `ab0fe280…`; `restore.json`
`c4265fff…`; kept library files: pose `Heavy H1--4cfe409f901e.json` `14c6bc97…`, `pose_sources.json` `ea1721fa…`.

## 2. Executed sequence (no deviation from `PROCEDURE.md`)

- **Preparation (SFM closed):** `build` (`5a8c832b…`, line 42546 only); `pre` PASS (backups, four protected
  inventories, preset library 107 files and 22 folders, session copies); `install`; `check` `"installation":
  "qualification"`.
- **Native (Owner, one SFM process):** three fresh, unrigged Heavies; A posed with the rotate tool; captures BASE,
  SAVED, APPLY, UNDO, REDO, NOOP, each reporting `header READ`, helpers `hlp_forearm_L`, `hlp_forearm_R`, errors none.
  Full body Save New `Heavy H1`; reopened in Pose Info; Apply to B; one Undo, one Redo; the second Apply reported
  "Already matches this pose."; SFM exited without saving.
- **Closeout (SFM closed):** `library Q` (2 differences: the pose and its `pose_sources.json`); `collect-logs` (1 log);
  `restore` (library cleanup exact: files and folders equal pre; `RESTORED`, no inventory problems); `check`
  `"installation": "published"`, CPM `ccbed9d7…`, both registries absent; `analyze` (original verdict).

## 3. Results

| Gate | Original (`d7af5d94…`) | Replay (`effcf928…`) |
|---|---|---|
| EVIDENCE | **FAIL** (1 check: `library.changed_only_by_the_one_saved_heavy_pose`) | PASS |
| HEADER | PASS | PASS |
| SAVE | PASS | PASS |
| APPLY | PASS (154 target channels changed; bone transforms only; helper channels never written; P7 verified; one owned entry) | PASS |
| UNDO | PASS (Undo = BASE, Redo = APPLY, true no-op) | PASS |
| PEER | PASS (A and C unchanged at every capture) | PASS |
| **Verdict** | **INCOMPLETE** | **AUTOMATED PASS** (62/62) |

**Owner visual acceptance (step 8): PASS.** B reproduced the saved pose; the procedural forearms looked acceptable;
A and C remained unchanged; Undo and Redo worked.

## 4. The analyzer correction

**Cause.** CPM's Save New also writes the per-character informational sidecar `pose_sources.json` (the project a pose
was saved from; never read by Apply or any compatibility check; documented in the CPM beside `PROD_POSE_SOURCES`). The
UA-1 comparator already accounts for it; the H1 analyzer's library allow-list admitted only pose records and
`character.json`, so the expected sidecar was reported as unexpected. Not a CPM, scene or restoration defect.

**Correction (analyzer only; CPM, capture, procedure, observations and original evidence unchanged).**
`pose_sources_ok` admits `Characters/<dir>/pose_sources.json` only when it is `added`, in the one saved pose's own
character folder, the file kept in `library_after` hashes to the recorded difference, and it is exactly
`{entries, record_kind: "cpm-pose-sources", schema_version: 1}` with exactly one entry keyed by that pose's
`preset_id`, whose only field `project` is this run's `sessions\H1_SESSION.dmx` (case-insensitive). Any other library
change stays unexpected. A `--replay` mode writes `H1_REPLAY_VERDICT.json/.md` beside the original (exclusive create)
and records the original verdict's hash; the original verdict is never rewritten.

**Tests.** `tests/test_h1.py` 58/58 (was 48/48; 10 added: the native shape passes; another project, a second entry,
another pose's key, an extra field, another character folder, `changed` status, a hash mismatch, and another new file
beside it each give INCOMPLETE; a replay leaves the original verdict unchanged). Teeth: with the original analyzer the
native-shape test fails. `tests/test_h1_capture.py` unchanged (capture unchanged).

## 5. Protection

Sessions never saved (hashes above); the external session `krystal_s2fm_alone_port.dmx` untouched (last modified
2026-11-16, before the run); four protected inventories and the published installation restored exactly; preset
library equal to pre-run in files and folders, the run's two files kept in evidence. No additional SFM run, product
change, installation, promotion, push, merge, signing or release.
