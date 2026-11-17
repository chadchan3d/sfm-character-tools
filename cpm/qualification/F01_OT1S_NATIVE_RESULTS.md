# F-01 OT1S — Native integration smoke check of the integrated production-guard candidate: results

**Date:** 2026-11-17. **Authority:** Owner authorization "F-01 OT1S — Native Integration Smoke Authorization, OWNER
AUTHORIZATION: GO"; Owner completion report "F-01 OT1S — Owner Native Completion"; closure by "F-01 OT1S — Final
Qualification Closure" (**DESIGNER DISPOSITION: ACCEPT / PASS**). Related: `F01_OT1_PRODUCTION_GUARD.md`,
`F01_OT1_NATIVE_RESULTS.md`; kit `real_sfm_qualification/f01_ot1_integration_smoke/`.

**Disposition: SMOKE PASS (formal analyzer verdict), accepted by the Designer.** The integrated candidate is natively
qualified on the known Krystal fixture. It is **not promoted**: the published v1.0.0 remains installed and unchanged.
The OT1, Q1 and PS-2 verdicts and their recorded limitations are preserved unchanged.

## 1. Identities

| Item | Identity |
|---|---|
| Repository checkpoint (kit commit) | `d95ab93` |
| Integrated candidate CPM (`d719bb0`) | `48ff01a3b328f94de0f267d910a10e745b0cdc2b22f550ef3783c03394abcefa` |
| Qualification build (line 42546 only, `PROD_POSE_REGISTRY_MODE`) | `10328efee31731b09bef7a699bc3ab0a87294e670189d94be673774c81fc99b0` |
| Smoke observer `F01_OT1S_Observe.py` | `04fb02e91bd60663aaa6f8ccdd27733e02ad827c87664f63ff70edf8b6019e70` |
| Pinned OT1 observer (loaded by the smoke observer) | `5a13708a…` |
| `smoke_tool.py` / `smoke_analyze.py` (unchanged) | `3698aa0b…` / `5148cc394e0ccdbc4a8d5a0d20000ca59d3fe667259b272e4869ff08a5441ec4` |
| Config template / run config | `0f8b667c…` / `ot1s.json` `f0e660fd…` |
| Session `OT1S_KRYSTAL.dmx` (R2 fixture copy; after the run) | `259ea8a6…` (unchanged, never saved) |
| `OT1S_SPARE.dmx` (copied by the reused `pre`, never opened) | `61df8bcd…` (unchanged) |
| Published installation before and after | v1.0.0, CPM `ccbed9d7…`; both registries absent |
| Run folder (raw evidence, not committed) | `E:\SFM_U0B_Scratch\f01-ot1s-integration-smoke-r1` |

**Verdict files (original run, unchanged):** `evidence/OT1S_VERDICT.json`
`937ba03aaa78d59b85531dcdbfce85df43263bc0753ada1ed807e8222c898c54`, `evidence/OT1S_VERDICT.md`
`405709f71782b898b783a978ec3c889faf3341c2324aa4b3459c3eb5fa3348bb`.

**Evidence files:** captures `OT1S-BASE.json` `975d5447…`, `OT1S-APPLY.json` `dab5a8dc…`, `OT1S-UNDO.json`
`c46718e5…`, `OT1S-REDO.json` `54106d1e…`, `OT1S-UNDO2.json` `33d84771…`; CPM log
`CPM - 2026-11-17_23-14-33Z - pid18456 - 6f1a10 - 001.log` `c44b9e06…` (91 lines); `library_Q.json` `d7818b61…`;
`library_cleanup.json` `632a2d92…`; `restore.json` `243fa777…`.

## 2. Executed sequence (no deviation from `PROCEDURE.md`)

- **Preparation (SFM closed):** `build` (`10328efe…`, differs from the candidate in line 42546 only); `pre` PASS
  (backups, four protected inventories, preset library 107 files and 22 folders, session copies); `install`; `check`
  = `"installation": "qualification"`, both registries present. A manifest of the OT1, Q1 and PS-2 evidence folders
  was recorded before the run.
- **Native (Owner, one SFM process):** opened `OT1S_KRYSTAL.dmx` (shot15, 0.2083 s); created the same-model peer
  (krystal2020.mdl, instance B); CPM, Refresh Models, selected `Krystal` (A); BASE; Apply `Body`; APPLY; Edit > Undo
  Apply Body Preset; UNDO; Edit > Redo Apply Body Preset; REDO; Edit > Undo Apply Body Preset; UNDO2; exit without
  saving. The Owner reported no unexpected behaviour and no change on the peer.
- **Closeout (SFM closed):** `library Q`, `collect-logs`, `restore`, `check`, `analyze`, then the evidence-manifest
  comparison. Nothing in the candidate, kit, analyzer or evidence was changed.

## 3. Measured states

| Capture | Owner line | `bip_head` input / result / physical | `bip_tail00` input / result / physical | Undo | Redo | Item count |
|---|---|---|---|---|---|---|
| BASE | Body FAIL, errors none | 0.113 / 1.13 / 1.13 | 0.08 / 0.80 / 0.80 | Change Recording State | — | 24041 |
| APPLY | Body PASS, 10 events, guard 4 accepted 0 refused, errors none | 0.1330049 / 1.3300492 / 1.3300492 | 0.10 / 1.00 / 1.00 | Apply Body Preset | — | 24078 |
| UNDO | Body FAIL, errors none | 0.113 / 1.13 / 1.13 | 0.08 / 0.80 / 0.80 | Change Recording State | Redo Apply Body Preset | 24041 |
| REDO | Body PASS, errors none | 0.1330049 / 1.3300492 / 1.3300492 | 0.10 / 1.00 / 1.00 | Apply Body Preset | — | 24078 |
| UNDO2 | Body FAIL, errors none | 0.113 / 1.13 / 1.13 | 0.08 / 0.80 / 0.80 | Change Recording State | Redo Apply Body Preset | 24041 |

("Body FAIL" at BASE/UNDO/UNDO2 is the settled-map comparison against the `Body` preset, expected to fail when the
preset is not applied.) Full-precision values are in `OT1S_VERDICT.md`. `bip_head` 1.3300492 is the same native
rounding of the requested 1.33 recorded by OT1.

## 4. Results by gate (`smoke_analyze.py`, unchanged)

**SMOKE PASS — GUARD, APPLY, UNDO, PEER and EVIDENCE all PASS (50 checks, 0 failures).**

- **Production reference guard (GUARD):** four calls, four accepted, zero refused — both changed mode-3 scale
  expressions before the Body transaction's first scale write, and each again immediately before its own bone's write
  inside the transaction (before `Operate()`). The known Krystal three-reference graph is accepted natively.
- **Physical Apply (APPLY):** the operation returned; exactly the two changed mode-3 scales were written; the deferred
  physical verification passed and matches the CPM log (`PROD_APPLY_DEFERRED_VERIFY outcome='committed-verified'`,
  `PROD_OPERATION_OUTCOME … outcome='verified'`); the full settled scale map passes; the target's physical scales are
  the requested ones and only the head and tail scales changed; Apply created one owned history entry.
- **Undo, Redo and final Undo (UNDO):** Undo and the final Undo restore every target field and both scale graphs to
  BASE exactly; Redo restores them to APPLY exactly; the history labels are consistent at each step.
- **Peer (PEER):** the same-model peer is unchanged at every capture.
- **Evidence (EVIDENCE):** all five captures present with the qualification build and complete fields; one SFM
  process on the disposable session; shot and time never moved; session never saved; hooks installed at BASE and
  removed at UNDO2; failure injector never armed; target and same-model peer identified, same selected instance
  throughout; only the one Body Apply; no visibility edit; BASE precondition (head and tail differ from the preset);
  no recovery or uncertainty in the log; library and restoration checks (below).

## 5. Baseline Undo label

`PROCEDURE.md` predicted `CreateAnimationSetAndModel` as the Undo label at BASE, UNDO and UNDO2; SFM showed
`Change Recording State`. This does not invalidate the qualification:
- The analyzer requires no specific baseline label. It requires a non-empty BASE label other than `Apply Body Preset`,
  and that Undo and the final Undo return exactly to the BASE label with `Redo Apply Body Preset` pending — which they
  did — together with exact field and graph restoration.
- SFM's internal change count is 24041 at BASE, UNDO and UNDO2, identical to OT1's BASE (whose label was
  `CreateAnimationSetAndModel`). The `Change Recording State` entry therefore added no recorded data change; it
  relabelled the top history entry after the peer was created.
- Which interface action produced that entry is not established by the evidence. The prediction in `PROCEDURE.md` was
  inaccurate in the label only; the procedure and the evidence are left unchanged.

## 6. Restoration and preserved evidence

- **Preset library:** `library Q`: 0 differences from the pre-run library; restoration cleanup exact
  (`folders_equal_pre` and `files_equal_pre` true; nothing kept in evidence, no run folders removed or recreated).
- **Installation:** `restore` → `RESTORED` (no inventory problems, no poses moved); `check` →
  `"installation": "published"`, CPM `ccbed9d7…`, both registries absent. The published v1.0.0 is installed and
  unchanged.
- **Protected inventories:** equal to their pre-run baselines (`usermod\scripts`, `usermod\cfg`, preset library, SFM
  sessions folder).
- **Sessions:** both copies match their pins (never saved).
- **OT1, Q1 and PS-2 evidence:** `f01-ot1-ordering-trial-r1` (239 files), `f01-q1-ps2-diagnostic-r1` (240) and
  `f01-ps2-v110-r1` (1,270) are byte-identical to the pre-run manifest (none changed, missing or added). Their
  original verdicts (`OT1_VERDICT` `9ea42020…` INCOMPLETE, `OT1_VERDICT_REPLAY` `e4cbedf0…` INCOMPLETE, `Q1_REPORT`
  `c95da430…`, `Q1_REPORT_REPLAY` `34bdc23c…`, `PS2_VERDICT` `9919e98c…` FAIL 34/42) stand unchanged.
- **External file:** `E:\SourceFilmMaker Sessions\krystal_s2fm_alone_port.dmx` (the Owner-confirmed exception in
  `F01_OT1_NATIVE_RESULTS.md`) is untouched (`5a6a6cde…`, 201,423 bytes, 2026-11-16 21:23:53).

## 7. Scope and limitations

- One machine, one fixture (Krystal R2, shot15), one Apply/Undo/Redo/final Undo cycle. No controlled failure and no
  shared-reference scene in this run: verified Abort is evidenced by OT1 (candidate `0cea8acd…`) and the before-Undo
  refusal by the offline suites only (`F01_OT1_PRODUCTION_GUARD.md` section 3).
- The compatibility policy (refuse additional or unreadable direct references before Undo) is unchanged; its frequency
  on other rigs is unknown.
- The physical-advance mechanism at the refresh remains observed, not explained.
- No production promotion, installation change, signing, push, merge or release.
