# v1 Release Adjudication Addendum

**Status:** owner-approved, 2026-10-22. Records Astra's adjudication of the seven questions raised by
`V1_RELEASE_ASSEMBLY_PLAN.md` (§6, D1–D7). **Narrow and additive:** it governs the plan where they differ and
reconciles only the L card §6 Group 5 rows and the L-6 evidence classification. R15, R2, the Offline Updater v1
Contract Amendment, the L card's other text, the v1 Release Baseline Amendment's other sections and every accepted
qualification are unchanged. It authorizes no step of the plan.

## Rulings

1. **L-6 Group 5:** G1 → corrected Candidate C → G1.
   - Rebuild My Data gives a verified NOOP on both generations.
   - A named control demonstrates the changed semantic classification between G1 and Candidate C.
2. **Qualification evidence:**
   - Accepted development evidence is retained for test-only injections and specially signed fixtures, where the
     responsible implementation is unchanged.
   - Every L-6 case is classified by its actual evidence source.
   - Ordinary production behavior is qualified on the exact shipping executable.
3. **Signing:** one owner-controlled Ed25519 private key, encrypted and backed up. Only the public identity enters
   production code. The owner performs signing.
4. **Timestamp:** `published_at` is the UTC time the immutable package is issued (signed), not necessarily its
   GitHub upload time.
5. **Distribution:**
   - The core software and the updater ship as separate ZIPs.
   - Quick Launch remains the unchanged optional ZIP.
   - The updater Scripts-menu launcher is outside the 31-file signed compatibility inventory, but is listed in the
     software archive manifest.
6. **Restoration:**
   - After L-6, the exact pre-test installation and updater records are restored.
   - Qualification evidence is preserved separately.
   - The final Candidate C installation is a separate owner action.
7. **Normalizer:**
   - The owner confirms redistribution rights for the final `6b5d2941…` implementation.
   - Relevant README wording is corrected before publication, with no unsupported claims about historical
     third-party oracle material.

**Scope note:** the local official-package worker/backend path may be qualified with the unpublished,
production-signed Candidate C package. That does not independently qualify a public GitHub download, which needs
its own evidence once a release exists. No new local-package GUI feature is authorized.

## Reconciliation of L card §6 Group 5 (supersedes those rows of Baseline Amendment §5 only)

| Card / Amendment §5 row | Under this addendum |
|---|---|
| Setup: Rebuild My Data gives a verified NOOP (Amendment: on installed Candidate C) | NOOP on G1 at the start, **and** NOOP on Candidate C after the official install. |
| Get Official Data with a test-signed package of a changed generation (Amendment: relative to Candidate C) | Get Official Data with the **production-signed, unpublished `data-v1.0.0`** (corrected Candidate C, sequence 1) on the G1 installation. G1 → Candidate C is the changed generation. A named control whose classification differs between them is checked in both tools. |
| Use Another TXT with a preserved baseline copy (Amendment: Candidate C, restoring Candidate C) | A preserved external copy of **G1** restores G1; the selected file is unchanged afterwards. |
| After restoring, exact baseline (Amendment: Candidate C identities) | Exactly G1 again (Master `ac45e5c1…`, sidecar `bcd97641…`, manifest `d810d648…`). Afterwards, ruling 6 restores the pre-test installation and updater records. |
| CPM and the Normalizer acquire authority | Unchanged: after each install, with Normalizer `6b5d2941…`. |

Group 1's Candidate C compiler-parity addition (Amendment §5) and the Groups 2–4 fixtures (G1/G2/G3) are unchanged.

## L-6 evidence classification (ruling 2)

Each L-6 case is reported with one source:
- **Shipping executable:** ordinary production behavior on the exact candidate, production trust only. For example:
  - tamper of each package file, the signature or the key id;
  - an unknown (test) signer;
  - replay of the same package;
  - a changed or missing consumer file;
  - source edge cases;
  - real SFM detection;
  - locks and share-read handles;
  - worker kill and GUI close by external process control;
  - Group 5.
- **Retained development evidence:** cases that need test-only injection or specially signed fixtures. The
  implementation responsible must be unchanged since that evidence. For example:
  - a validly signed wrong-repository package, a downgrade, or the same sequence with different bytes;
  - an unsupported-profile inventory;
  - barrier kills and rollback;
  - injected process-gate responses;
  - injected write faults and disk-full.

Production-signed fixtures other than the release artifacts are never made.
