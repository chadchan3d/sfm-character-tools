# SFM Animation Groups Master

A curated, structurally-validated `sfm_defaultanimationgroups.txt` for Source
Filmmaker, plus a compiled binary "sidecar" format that lets SFM's in-game
Normalizer tooling look up controls in that Master without re-parsing the
full TXT file on every query.

## What's here

- **`sfm_defaultanimationgroups.txt`** — the canonical Master: SFM's
  animation-group hierarchy (rig groups, controls, flexes, helper bones,
  metadata) reorganized and taxonomy-corrected from the stock/community
  baseline, while preserving every exact control literal.
- **`reference/`** — comparison data used while building the Master.
  (The third-party "Silkworm" reference file used during that work is kept
  locally only and is intentionally not part of this repository — see
  `.gitignore`.)
- **`tools/sfm_master_sidecar/`** — the compiled sidecar format: a compiler,
  binary reader/writer, manifest/publisher, and CLI, built to reproduce the
  Normalizer's exact lookup/fold/conflict semantics from a compact binary
  artifact instead of the raw TXT.
- **`tools/validate_master.py`** — a read-only structural validator for the
  Master (brace/indentation structure, exact-duplicate controls, and a
  native-Rebuild ASCII-casefold cross-path invariant).
- **`tools/verify_phase2_production_order.py`**, **`tools/extract_phase2_human_review.py`**
  — supporting tools from the taxonomy production pass.
- **`tests/`** — the pytest suite for the sidecar format, plus a
  `tests/sidecar/qualification/` harness suite that qualifies the sidecar
  against the real, unmodified Normalizer/T130 consumer source as a
  read-only oracle (desktop Python 3, cross-checked against real embedded
  Python 2.7 where noted).
- **`docs/qualification/`** — the gate-by-gate design and qualification
  audit trail for the sidecar work (`SFM_MASTER_SIDECAR_*.md`,
  `SFM_SIDECAR_*.md`): architecture decisions, resource/performance
  baselines, and the evidence behind each qualification verdict.
- **`audit/master-content/`** — the taxonomy classification ledgers and
  human-review records behind the Master's current organization
  (`phase2/`, `flex-bone/`, `imports/`, `helpers/`, `sexual-bones/`,
  `whole-master/`), kept separate from the software qualification material
  above since it documents Master *content* decisions, not sidecar
  behavior. See `audit/master-content/README.md` and
  `docs/qualification/README.md` for what's in each.
- **`cpm/baseline/`** — a frozen, SHA-256-pinned migration baseline
  (`SFM_CSP_G18AN_SaveNewCopy.py`) imported verbatim from the now-closed
  `sfm-character-preset-manager` source archive, serving as the parity
  oracle for CPM shared-authority convergence; see `cpm/baseline/MANIFEST.md`.
- **`cpm/quick_launch/`** — CPM Quick Launch, an **optional** CPM button for SFM's
  Animation Set Editor toolbar. It requires Autoinit Manager to be installed already
  (never bundled or changed) and ships as a separate ZIP, outside the core Character
  Tools software inventory and the Control Group Updater. Character Preset Manager
  stays available from the Scripts menu without it. See
  `cpm/quick_launch/README.md` and `cpm/quick_launch/distribution/README.txt`.

## Editing the Master

The Master is maintained through deterministic, re-validated Python edits
rather than free-form text generation — see `CLAUDE.md` for the exact
editing contract (canonical-file discipline, structural parsing rules,
duplicate/casefold invariants, and the validate-before-promote workflow).

## Running the tests

```
python -m pytest tests/
python tools/validate_master.py sfm_defaultanimationgroups.txt
```

Most qualification harnesses under `tests/sidecar/qualification/` are fully
self-contained and need nothing beyond this repository (`desktop_session_owner_qualification.py`,
`desktop_view_expansion_qualification.py`, `desktop_round3_foundation_qualification.py`,
`desktop_parity_and_timing.py`, `desktop_minimum_c3_qualification.py`).

One, `desktop_r1_consumer_projection_qualification.py`, additionally
compares the sidecar against the *real* SFM Normalizer/T130 source as a
read-only oracle, to prove the compiled sidecar reproduces that consumer's
exact behavior rather than a reimplementation of it. That real source is:

- `SFM_NORMALIZER_ORACLE_PATH` — the live, currently-deployed
  `Rebuild_Control_Groups_Normalizer.py` from your own SFM install
  (`usermod/scripts/sfm/mainmenu/...`);
- `SFM_T130_ORACLE_PATH` — a T130 live-trigger requalification snapshot of
  that same Normalizer.

Neither oracle file is distributed with this repository — they are
historical copies kept outside this project, and this repo makes no claim
about them. This is separate from the final v1 Normalizer
(`audit_external_runtime/Rebuild_Control_Groups_Normalizer.py`,
`6b5d2941…`), which is included here and redistributed in the SFM Character
Tools release with the owner's confirmed redistribution rights. Set both environment variables to the
exact local paths of your own copies to run this harness end-to-end. If
either is unset or doesn't resolve to a real file, the harness prints a
single `SKIPPED: ...` line naming both variables and exits successfully
(code 0) without running any oracle-dependent check — it never reports a
false PASS, and it never crashes for lack of these files.

## Limitations

- The sidecar qualification work establishes desktop-Python-3 and
  real-embedded-Python-2.7 parity against the real Normalizer/T130
  consumer contract; it does not itself constitute a live-SFM Qt-main-thread
  production integration (see the `docs/qualification/SFM_MASTER_SIDECAR_*`
  gate audits for exactly what has and has not been qualified).
- `desktop_r1_consumer_projection_qualification.py` loads both real oracle
  files once at startup and uses them throughout, including its
  hand-audited/manual-profile checks — it is an all-or-nothing harness, not
  split into an oracle-free subset. Without both external files it reports
  the SKIPPED result above rather than running any part of the suite.

## License

Original material in this repository — wholly authored within this
project — is released under CC0 1.0 (see `LICENSE`): public domain
dedication, no rights reserved. This does **not** extend to any
externally-owned material referenced but not included here (the real SFM
Normalizer/T130 source above, or any other third-party input a harness
may optionally consume) — CC0 applies only to what this repository
actually contains and that ChadChan3D has the right to dedicate.
