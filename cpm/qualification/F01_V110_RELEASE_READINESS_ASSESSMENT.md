# F-01 v1.1.0: release-integration readiness assessment (2026-11-19)

**Authority:** the Owner/Designer's "F-01 Stage 2 — Final Qualification Disposition", next milestone. This is an
assessment from the committed records only. Nothing was built, installed, run natively or changed, and no
compatibility campaign was begun. No promotion, signing, push, merge or release.

## 1. Summary

There are two different builds, and the assessment differs for each.

| Build | CPM | What it is | Readiness |
|---|---|---|---|
| **RC2** (the release baseline) | `7aa0fc4e…`, unsigned package `46be7dbf…` | Krystal v2 Full body, generic direct-FK (v3) with the H1 helper rule, the OT1 Body Preset correction and guard, Selected parts, Body Presets, the accepted UI | **No known product defect blocks it.** Only the Owner's release gates remain (section 4) |
| **HEAD candidate** (RC2 + Stage 1 + Stage 2) | `001377f9…` | RC2 plus the structural rig adapter (Fox) and JIGGLE leaves (Tails), both still `PROD_BODY_RIG_STATUS = "experimental"` | **Not release-integrated.** In production mode it behaves as RC2. Making Fox and Tails available needs a product change, a new RC and a production-mode native smoke (section 3) |

There has been no product-code change since `208a977`.

## 2. Feature status

| Feature | Native evidence | Formal automated verdict | Disposition | In RC2? |
|---|---|---|---|---|
| **Krystal Full body (v2)** | K2 (qualification build); RC1 native smoke (production files) | K2 original FAIL 54/55, revised A1 replay **PASS** 56/56; RC1 smoke **PASS** 18/18 | Accepted; promoted to `qualified` in RC1 (`a2254930…`) | **Yes** |
| **Generic direct-FK (v3)** | EF-1 (Engineer); PS-2 pose rows (Engineer, Soldier); RC1 smoke (Heavy v3) | EF-1 **PASS**; PS-2 run 1 FAIL 34/42 overall, all pose rows passing; RC1 smoke **PASS** | Accepted | **Yes** |
| **Helper bones (H1, QUATINTERP)** | H1 Heavy check; RC1 smoke (Heavy) | Original INCOMPLETE; corrected-analyzer replay **PASS** 62/62 | CLOSED / PASS | **Yes** |
| **Fox: structural rig (Stage 1)** | Fox runs 1 to 3; Abort recovery check (qualification builds, CPM `7259e80a…`) | Run 3 **INCOMPLETE** (`561f1b09…`); check **INCOMPLETE** 59/60 (`f402da86…`) | **CLOSED by Owner/Designer adjudication**; experimental | **No** |
| **Tails: JIGGLE leaves (Stage 2)** | Tails run (qualification build of `001377f9…`) | **FAIL** 76/77 (`36739104…`; NAV Undo-state only) | **CLOSED by Owner/Designer adjudication, with documented NAV history exception**; experimental | **No** |
| **Selected parts** | SFP-1 NQ1; PS-2 (Krystal Selected parts Save, Apply, Undo, Redo); RC1 smoke | NQ1 **PASS** 134/134; RC1 smoke **PASS** | Accepted, with a performance finding | **Yes** |
| **Body Presets** | M-05, M-06 native qualifications; OT1S; RC1 smoke Body Preset Apply | M-05/M-06 PASS; OT1S **SMOKE PASS**; RC1 smoke **PASS** | Accepted. The PS-2 Body Preset findings are resolved through Q1 → OT1 → OT1S | **Yes** |

**Neither Fox nor Tails has a formal automated PASS.** Both are accepted by adjudication, and their non-PASS verdicts
are preserved.

## 3. What adding Fox and Tails to v1.1.0 would need

These are not defects. They are the steps that remain, and each needs separate authorization.

1. **A product change:** set `PROD_BODY_RIG_STATUS` to `qualified`. The structural route's authorization currently
   records `evidence: None`; whether an evidence reference is needed is a design decision.
2. **A new release candidate (RC3):** the full regression on Python 2.7.5 and 3.10.6, the package, and RC VERIFY.
3. **A short production-mode native smoke.** All Fox and Tails native evidence came from qualification builds
   (registry mode `qualification`). The structural route has never run natively in production mode.
4. **Fox on the final code.** Fox's native evidence is on `7259e80a…`. Stage 2 changed the adapter afterwards. Offline,
   Fox's drafts are byte-identical (revision 1), but Fox has not run natively on `001377f9…`. One Fox Save/Apply in
   the same smoke would cover this.
5. **Documentation:**
   - rollback: RC2 and v1.0.0 refuse structural (version 2 / revision 2) records safely, and the records stay in the
     library;
   - limitations: weighted or multi-target constraints, other rig operators, bone-parented handles and retargeting
     are excluded;
   - the NAV history observation (section 5).

If v1.1.0 ships as RC2, Fox and Tails keep refusing Full body safely (as in the RC1 smoke), and Selected parts stays
available where supported.

## 4. Remaining release gates for RC2

These come from `F01_V110_RC1_INTEGRATION.md` section 6 and `F01_V110_RC2_UI_CORRECTIONS.md` section 4. They are
gates, not failures, and each needs the Owner's authorization.

1. **Optional:** a native look at RC2's three presentation-only corrections. RC1's native smoke covered everything
   else.
2. **The v1.1.0 README:** the package still carries the v1.0.0 README.
3. **Signing** the v1.1.0 inventory with the Owner's key. Only the Owner signs.
4. **Distribution checks:** the updater check on the signed package, plus the Workshop installer constants,
   `SCT_Setup.exe`, `stage` and `stage.verify`.
5. **Publication:** merge `feature/f01-pose-library` into `master`, then tag, GitHub release and Workshop publication.
   The branch has many local commits that are not on GitHub.

## 5. Known issues: product findings versus historical test failures

### 5.1 Product findings (none is a recorded blocker)

| Finding | Status |
|---|---|
| Selected parts Apply on Krystal takes up to about 5.6 s (NQ1/PS-2) | Performance finding; a documented limitation |
| **F-T01-1:** Body Save rewrites the shared `character.json` `display_name` | Nonblocking. Known since M-06; CPM not changed |
| **O-T10-1:** SFM save/reload moves some quaternions by 1–2 float32 ULP | SFM behaviour; analyzers renormalize on reload |
| `pose_sources.json` stores local project paths | Documented limitation (privacy when a library folder is shared) |
| Tails NAV: SFM recorded `Modify Time Selection` during navigation, so two Undos reached Apply | Cause undetermined; CPM logged no operation. Not in RC2's scope. Accepted as a documented exception |
| PS-2 Body Preset deferred verification and the duplicate-model Undo difference | **Resolved** (one cause, the evaluated scale lag): Q1 diagnosis, the OT1 ordering correction and guard, and OT1S SMOKE PASS. The PS-2 FAIL verdict is preserved |
| v1.0.0 Body preset topology refusal | A v1.0.0 limitation (no M-05). v1.1.0 carries M-05. The link to the user report is not established |

### 5.2 Historical test failures (not product defects)

These are unchanged since their recorded baselines, are not caused by Stage 1 or Stage 2 behaviour, and do not test
shipped behaviour.

| Failure | Why it fails |
|---|---|
| Canonical route `derivation.added_top_level_is_bounded` | An allow-list of new top-level names. It has failed since earlier unlisted names, and Stage 1 and Stage 2 add more. This is bookkeeping, not behaviour. It should be brought up to date before a release that includes Fox and Tails |
| M-05 A9 (114/115), authority cleanup (42/46), r14 `normalizer_pinned`, r15 `forbidden.unchanged.*`, normalizer pins | Pins to historical artefacts; the same at `ea5e7c4` |
| Bounded-logging real-log-folder guard | Environmental: the log folder exists after native use |
| W1 harness | Missing generated configuration |
| Nine historical qualification kits | They pin the pre-integration registry; they pass at `3b1e644` |
| Recovery kit `test_s1r.py` 59/61 | Template checks compare against the repository's current CPM, which Stage 2 changed; recorded, not altered |
| Non-PASS qualification verdicts: PS-2 34/42, Q1, OT1, K2 original, H1 original, Fox runs 1 to 3, the recovery check, Tails 76/77 | Preserved history. Each was followed by a correction, replay or adjudication recorded in the ledger |

## 6. Assessment

- **RC2:** release-integration ready as far as the records show. There is no open product defect and the native
  production smoke passed. Remaining: README, signing, distribution checks and publication.
- **Fox and Tails:** qualified by adjudication, not by automated verdict, and still experimental. They are not ready to
  ship in v1.1.0 without the steps in section 3. One option is to ship RC2 as v1.1.0 and integrate Fox and Tails in a
  later release; the other is an RC3 with those steps first. The choice belongs to the Owner and Designer.
