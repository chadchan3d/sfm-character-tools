# Character Tools v1 Release Baseline Amendment

**Status: owner-approved, 2026-10-21. Additive.** This amendment records two owner decisions that change the
intended first-release identities of two components. It does not edit or replace the Blueprint
(`SFM_Character_Tools_Updater_Blueprint_R2.md`), the L authorization card (`L_IMPLEMENTATION_AUTHORIZATION_CARD.md`),
the Offline Updater v1 Contract Amendment or R15. It is not authorization to redesign the updater or change R15.

## 1. Owner decisions
- **Decision A — APPROVED:** the first Character Tools release includes the qualified Normalizer
  `25a5e3cd2ccf62dad00df7122d5f1b1d62aea63a2069459993acc3e44feaa343`.
- **Decision B — APPROVED:** Master Candidate C
  `00df6304c58662689a67124e2e05a492c8f80bf4aa0028644648e91b0f1f5e8e` is the intended first-release Master. Its
  accepted sidecar and manifest are `43572fd25298e327c7053c9bff9f89086cec924f803280f97ce9a25c9b0272bf` and
  `c646f1da5a4b05c86feb81503cd522acaea8f70bae71272d220c369f45fbe31b`.

- **Decision B amended — option (b), APPROVED 2026-10-21:** correct Candidate C's 170 indentation defects (§4,
  step 3). The owner authorized the mechanically derived identities, subject to the equivalence and validation
  conditions, all of which passed:
  - Master `1d855cd34b90a2e6254d97eb4c6ac4b08ccc64d994b8e6a754ddac8466b155ec`;
  - sidecar `3791677522119a6ca45c1092743041dc07014cfa1fd0891526db995bcf526a16`;
  - manifest `6c7568063a69de2a22c05f55df066db369f3340e68d0208f9f36a4c017c3c7ae`.

  These are the intended first-release data identities. Original Candidate C (`00df6304…` / `43572fd2…` /
  `c646f1da…`) remains the historical identity that the real-SFM qualifications used.

Both decisions are a narrow exception to the L card §1 exclusion of "any change to … the Normalizer" for the v1
release.

## 2. Precedence
This amendment takes precedence only for:
- the shipped Normalizer identity and its Phase F admission policy (§8);
- the intended first-release Master, sidecar and manifest;
- the qualification fixtures and expectations named in §5 that depend on those identities.

Everything else in R2, the L card, the Contract Amendment and R15 is unchanged, including:
- the authority profile `sct-authority-profile-1` (`2bbd93d0…`), its pins and its consumer contracts;
- the installed-software inventory architecture and its 9 roles / 31 files;
- the activation protocol and all updater behavior.

G1 (Master `ac45e5c1…`, sidecar `bcd97641…`, manifest `d810d648…`) and the Normalizer `1f4ec5a2…` remain historical
qualification and regression references.

## 3. Revised shipping identities
| Component | Previous v1 identity | Intended v1 identity | Repository state |
|---|---|---|---|
| Normalizer (`audit_external_runtime/Rebuild_Control_Groups_Normalizer.py`; inventory role `normalizer`) | `1f4ec5a2…`, 380,006 B (K-qualified) | `6b5d2941…`, 496,210 B: the §8 Phase F simplification of `25a5e3cd…` (496,624 B, the real-SFM-qualified build, now historical) | integrated; inventory spec pins hash and length; offline-verified, pending the bounded live-SFM check (§6) |
| Master (`sfm_defaultanimationgroups.txt`) | G1 `ac45e5c1…` | corrected Candidate C `1d855cd3…` (original Candidate C `00df6304…` is historical) | **promoted** into the repository Master (§4, step 3) |
| Sidecar / manifest (published data) | `bcd97641…` / `d810d648…` | `37916775…` / `6c756806…` (original: `43572fd2…` / `c646f1da…`) | data artifacts; produced at data release by the pinned compiler |

**Normalizer consumer-contract invariants re-verified against `1f4ec5a2…` (offline, by content):**
- `_authority_locate_mainmenu_dir` is byte-identical;
- the expected runtime API and build (`1.0.0-b2a` / `package-boundary-corrected-2026-09-22`) equal the profile's
  Normalizer consumer contract;
- the authority-package imports and the adapter, runtime and bootstrap interfaces used are identical.

## 4. Candidate C provenance
Candidate C is derived in two documented steps from the repository Master G1 `ac45e5c1…`:
1. **Candidate B** `e2c0f1178ca77834b05b375ae5d5cf3559995bcd285ca701b97ad2f5c78b3d1e`: the data-v1.0.0 replacement
   candidate (private evidence: build record `96705a11…`, validation `399d9c21…`).
   - **Header:** a provenance header.
   - **Additions:** rig_hip, nine HairSpike controls, and Tail0/Tail6 L/R.
   - **Placement corrections:** 15.
   - **`groupColor`:** added to 12 top-level groups. The existing Attachments colour changes and moves.
   - **Side-ordering normalization:** 1,721 left/right families, 14,956 controls reordered within their groups; 75
     multi-index families held.
   - **Validation:** structural PASS, no exact duplicates, casefold invariant PASS, and every other control keeps its
     G1 destination.
2. **Candidate C**: Candidate B plus exactly four rig-side group renames, `RigArms/LeftArm` → `LeftRigArm`,
   `RigArms/RightArm` → `RightRigArm`, `RigLegs/LeftLeg` → `LeftRigLeg` and `RigLegs/RightLeg` → `RightRigLeg`.
   Verified on 2026-10-21: the B → C diff is exactly these four lines.

3. **Corrected Candidate C** `1d855cd3…`: original Candidate C with exactly one excess leading tab removed from each
   of 170 control lines.
   - **Where they are:** Hair 78, Clothing 48, Sexual Bones 25, Face/Ears 8, Wings 4, Other 4, Tail 2, Face/Lower
     Face 1.
   - **Origin:** Candidate B's side-ordering step had given those lines one tab more than G1 and than their
     structural depth.
   - **Side effect of the same step, left unchanged:** it also brought 170 of G1's 11,001 pre-existing over-indented
     lines to their structural depth. That is approved Candidate B content, so it stays.

`tools/validate_master.py` on original Candidate C (read-only): structural parse PASS, 0 grammar errors, 43 groups,
128,569 controls, 0 exact duplicates, 0 casefold cross-path violations.

**Correction and equivalence (offline, 2026-10-21; 19/19 PASS):**
- **The edit:**
  - same line count; exactly the 170 recorded lines changed;
  - each changed line differs only by one leading tab;
  - 170 bytes shorter.
- **Semantic content identical:** the repository parser gives identical groups (paths, parents, lines, order, depth,
  children, metadata), identical control occurrences (literal, group, line, ranks) and identical ASCII-fold
  families.
- **Indentation:** no control deviates from group indentation + 1 tab except G1's preserved deviations; the 14
  added controls are correct.
- **Validators:** `tools/validate_master.py` PASS; UTF-8, no BOM, LF only.
- **Authority:**
  - **Compiler:** the release's hash-pinned compiler (`candidate.compile_real`, 9 pins) still reproduces original C's
    `43572fd2…` / `c646f1da…`.
  - **New authority:** it produces sidecar `37916775…` and manifest `6c756806…` for the corrected Master. Read back
    from disk, they pass reader semantic parity, FINAL R3-A2B admission and the manifest binding (source SHA-256,
    length, sidecar).
  - **Semantic equivalence:** exhaustive cross-parity both ways passes (original parse against the corrected
    sidecar, and the reverse).
  - **Byte comparison:** the two sidecars are the same length and their bodies are byte-identical. They differ only
    in the header's embedded source SHA-256 and the header digest.

**Promotion (CLAUDE.md procedure, 28/28 PASS):**
- **Before:** the canonical Master was asserted to be G1.
- **Temporary candidate validated:**
  - the group hierarchy equals G1's except exactly the four renames;
  - every G1 control is present, plus exactly the 14 additions;
  - no duplicates; the casefold invariant passes;
  - Candidate B's colours are each the first line of their group; G1's colours are placed as before;
  - there are no new indentation or separator anomalies;
  - the validator passes.
- **Then:** G1 was backed up, the Master atomically replaced, and the re-opened canonical file passed the same
  checks.
- **Compiled from the repository copy:** `37916775…` / `6c756806…`.
- **Tested in SFM?** The corrected byte identities have **not** been run in SFM. All real-SFM evidence belongs to
  original Candidate C.

## 5. L-6 plan reconciliation (L card §6)
A G1 expectation becomes Candidate C only where its purpose is "the shipping baseline". Where the purpose depends on
G1's specific content or known outputs, G1 stays. In this section "Candidate C" means the **corrected** Candidate C
(`1d855cd3…` / `37916775…` / `6c756806…`), the intended shipping baseline.

| L card §6 expectation | Purpose | Under this amendment |
|---|---|---|
| Group 1: real compilation of the live-equivalent G1 Master reproduces the known sidecar and manifest byte-for-byte | compiler parity and determinism against known outputs | **Unchanged (G1 kept).** Add the same check for Candidate C: it must reproduce `37916775…` / `6c756806…`. |
| Group 5 setup: Rebuild My Data on the current G1 gives a verified NOOP | NOOP on the installed shipping baseline | **Candidate C:** Rebuild My Data on the installed Candidate C gives a verified NOOP. |
| Group 5: Get Official Data with a test-signed package of a semantically changed generation (a G3 pair, or an owner-approved equivalent) | install a generation that differs by a known control | **Candidate C basis:** the changed generation and its "changed control resolves to its new group" check are defined relative to Candidate C, through the existing fixture recipe. G3 (defined against G1) is not silently reused as the changed generation. |
| Group 5: Use Another TXT with a preserved copy of the G1 Master, which restores G1 | restore the shipping baseline from an external TXT | **Candidate C:** a preserved copy of Candidate C, which restores Candidate C. |
| Group 5: after restoring, the installation is exactly G1 again | exact baseline restoration | **Candidate C:** exactly Master `1d855cd3…`, sidecar `37916775…`, manifest `6c756806…`. |
| Group 5: CPM and the Normalizer each acquire authority for the installed generation | both shipped tools consume the installed authority | Unchanged, run with the Normalizer `6b5d2941…`. |
| Groups 2–4 fixtures: the P1 G1/G2/G3 sets, G1 regenerated from the preserved Master copy | mechanism tests whose meaning depends on these generations' differences | **Unchanged (G1/G2/G3 kept).** |
| `updater/tests/support/fingerprint.py` live-installation reference (G1) | detect any change to the live installation during a run | Unchanged now; re-pinned only when the live installation is deliberately moved to Candidate C under a separate authorization. |

**Historical tests left unchanged:** these CPM milestone tests pin `1f4ec5a2…` (and G1) as frozen neighbours of
earlier milestones, and will report the Normalizer as changed:
- `test_cpm_app_logging_cleanup.py`;
- `test_cpm_app_r15_namespace_isolation.py`;
- `test_cpm_authority_adapter.py`, which also extracts the Normalizer locator by fixed line range.

Their content invariant is re-verified in §3.

## 6. Qualification delta
Only these are required because of the two changed identities. Accepted K, L-5, PRE and resource-stop evidence is
kept and not rerun.
1. **Candidate C structural and compiled-authority validation: DONE (offline, 2026-10-21).**
   - The corrected Candidate C was promoted into the repository Master by the CLAUDE.md procedure, 28/28 PASS.
   - The pinned compiler reproduces `37916775…` / `6c756806…` from the repository copy, with reader parity,
     admission and binding PASS.
   - Semantic equivalence to original Candidate C is verified (§4).
2. **Focused K-level CPM/Normalizer coexistence with Candidate C:**
   - both tools acquire the Candidate C authority;
   - Normalizer and CPM operations alternate in one SFM process;
   - the Normalizer's Master protection interlock is intact.

   This is bounded to the coexistence claims K made for `1f4ec5a2…`; it is not a repeat of K.
3. **Changed-inventory identity, compatibility and packaging checks:**
   - the L-5 installed-software inventory checks (group P) with the new Normalizer identity: staging byte-exact,
     acceptance, and rejection of the old identity as modified;
   - a rebuilt package carrying the new spec.
4. **L-6** on the eventual exact shipping candidate, with the §5 reconciliation.
5. **Bounded live-SFM check of the Phase F build `6b5d2941…` (§8).** It has not been run in SFM. The check covers:
   - successful Selected and All use in one SFM process;
   - one low-memory STOP refusing the next invocation until SFM restarts;
   - one clean UNKNOWN permitting the next invocation.

   Accepted PRE, governor, warning and continuation evidence (on `25a5e3cd…`) stands and is not rerun.

## 7. Not authorized by this amendment
- Live SFM deployment or real-SFM tests.
- Signing or production keys.
- QL-1 construction or L-6 execution.
- Further Master edits beyond Candidate C.
- Commit or push.

## 8. Phase F post-governor simplification (owner-approved, 2026-10-21)
**Authority:** Astra's final revised adjudication, which supersedes her initial Phase F recommendation. It applies to
the Normalizer only and does not change the updater, R15, the Master or the governor.

**Removed:** the process-lifetime scope-aware admission guard. Earlier Selected or All use no longer restricts
anything, so Selected→Selected, Selected→All, All→Selected and All→All are all allowed after successful runs, and
selecting every shot manually is not special.

**Kept:**
- **Identity checks:** the canonical shot-identity re-resolution after the scope dialog. Each selected shot must
  resolve to exactly one current project shot, and the process refuses if the mapping changed. The scope class is
  still logged.
- **Governor, unchanged:** 112 MiB / 24 MiB at command preparation, target preparation and native entry, with
  `<=` meaning STOP, the strict census and fail-closed UNKNOWN.
- **Other protections:** the PRE/POST, native, authority and transaction protections and the active-run lock.

**Restart policy:**

| Outcome | Subsequent Normalizer use |
|---|---|
| Successful run | allowed |
| Measured low-memory STOP | restart required (`LOW_MEMORY`); a later favorable reading never clears it |
| UNKNOWN with verified closure | a fresh attempt is allowed; nothing is recorded |
| Ordinary clean refusal (PRE refusal, a failure before native Rebuild began) | allowed after correcting the issue |
| A run that did not succeed after at least one native Rebuild attempt (`not success and mutation_started`), or any unverified essential cleanup (Master-index lease, protected-Master handles, run lock, resource-stop closure) | restart required (`UNVERIFIED_CLEANUP`) |

**Post-mutation abort ruling (Astra, final; owner-approved 2026-10-22):**
- **Condition retained unchanged:** in the normal final report, `restart_this_run = (not success and
  mutation_started) or not lease_released or not lock_released or not handles_released`, with `mutation_started =
  telemetry_native_attempts > 0`. No additional recovery machinery is added.
- **Why a restart is required:** the per-target transaction is non-undoable and has no rollback. After a generic
  abort, the abort path records only a failure message and does not re-verify the session, so the Normalizer cannot
  separate a benign abort (for example, the playhead not entering the next shot) from a failed identity or
  isolation check. A restart is required because complete recovery cannot be verified, not because corruption was
  established.
- **Verified native fallback is unaffected:** a target that ends in a fallback terminal state after native Rebuild
  passes the full per-target verification and does not make the run fail, so it never triggers this restart.
- **Resource stops are unaffected:** STOP and UNKNOWN closures keep their own verified-closure decision. A verified
  UNKNOWN closure, including after partial progress, permits a fresh attempt.
- **User wording:** the end-of-run and later-invocation messages say only that the run couldn't be confirmed to have
  finished cleanly. They claim neither corruption nor low memory.
- **Evidence:** the accepted offline evidence below, unchanged. No new testing was performed for this ruling.

**How the requirement is recorded:**
- **Two records:** a marker parented to the SFM main window and a process attribute. It survives menu-script
  re-execution and document changes; only process exit removes it.
- **Checked twice:** at the entry point (before and after the scope dialog) and again at the arming point
  immediately before scope traversal.
- **Fail closed:** a record that cannot be read or is malformed refuses the run. A record that cannot be made fails
  the resource-stop closure check, so no verified recovery is claimed.
- **Active-run lock correction:** a failed active-run lookup is no longer treated as "no active run". It refuses
  the run at entry, and never verifies a released lock.

**Wording:**
- **Low-memory STOP:** the approved warning is unchanged (save, restart, Selected Shot(s) including the unfinished
  shot). It stays a Resource Stop report with Close only.
- **Initial UNKNOWN:** "Normalizer couldn't verify that enough memory is available to continue safely." The
  guidance is "You can try again. If this keeps happening, save your project and restart SFM."
- **Partial UNKNOWN:** "Save your project, then use Selected Shot(s) to process the remaining shots, including the
  unfinished shot." No restart is demanded. It is a Send to Developer report with Show Log File.
- **Later invocation after low memory:** "An earlier Normalizer run stopped because SFM was running low on
  available memory." followed by save, restart and try again.
- **Later invocation after unverified cleanup:** "An earlier Normalizer run couldn't confirm that it finished
  cleanly." followed by save, restart and try again. It does not claim low memory.
- **End of an unverified run:** "The Normalizer couldn't confirm that this run finished cleanly." followed by save,
  restart and try again.
- **Wording status:** only the initial-UNKNOWN sentence was supplied verbatim. The other new strings follow the
  approved distinctions and are open to owner wording review.

**Offline verification (2026-10-21):**
- **Accepted suites:**

  | Suite | Result |
  |---|---|
  | Resource stop | 69/69; L11 restated for the new policy; the restart record replaces the Phase F marker check |
  | UI and log classification | 20/20 |
  | Production floors | 35/35 |
  | Retention | 19/19 |
  | Diagnostics | 74/74 |
  | PRE regression | identical to the qualified record |
- **Focused Phase F suite: 21/21.** It covers:
  - all four transitions, and full-project-then-subset use;
  - a low-memory STOP persisting across menu re-execution, and not cleared by a favorable reading;
  - a clean and a partial UNKNOWN permitting fresh admission;
  - unverified closure, failure after mutation and lease failure each requiring a restart, while PRE refusals and
    failures before work do not;
  - identity refusal and admission at the entry point;
  - active-run lookup failure, a malformed record, a record failure and an unverifiable lock release failing
    closed;
  - the arming recheck;
  - the warning text and report classification.
- **Contract:** the consumer-contract invariants against `1f4ec5a2…` are re-verified; the floors are unchanged.
