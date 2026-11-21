# F-01 v1.1.0 RC5: evidence-based release-readiness assessment

**Authority:** "F-01 RC5 — Correct Owner Verdict and Assess Release Readiness" (Owner, 2026-11-20). The Owner declined a
further native test solely to repeat previously qualified functionality. This assessment uses committed records and
preserved evidence only. It changes no product code, README, package or verdict, and it does not decide release: that
is the Owner's.

## 1. The candidate

| Item | Value |
|---|---|
| Package | `SFM.Character.Tools.v1.1.0-rc5-UNSIGNED.zip` `baadc4be54e17aead1ddf16474956b9b4cb9ba41fe073f7d4b568bf661fcf6d9`, 1007 entries |
| Integrity | two independent builds identical; RC VERIFY PASS (package, updater, version, installer dry run, rollback); `testzip` clean |
| Content | 1002 entries byte-identical to the published v1.0.0 ZIP; CPM `b89af5a8…`; registries `f445d5ef…`, `a2254930…`; unsigned inventory `15db1c1a…`; approved README `af87797b…` |
| Against RC4 | only `README.txt` differs |
| Regression | no product file changed since `2eacd7e`: CPM suites as recorded there (structural Fox and Tails 337/337, jiggle 142/142, Krystal body 261/261, scoped 495/495, pose_live 109/109, integration 218/218, cross-rig 228/228); kit tests unchanged apart from the three historical CPM-pin failures |

## 2. Native evidence available for this code

The production CPM `b89af5a8…` and the qualification build `d7454891…` used by the RC4 short check differ in exactly one
line, `PROD_POSE_REGISTRY_MODE` (verified by diff of the staged file). The mode is read in one place,
`pose_registry_mode()`, and only decides which registry mappings and rules are admitted (qualified only in production).
The production-mode check passes on the packaged CPM: every route the release claims is admitted in production.

| Run | Build | What it established natively |
|---|---|---|
| Stage 1 Fox run 3 + recovery check (2026-11-19; closed by Owner/Designer adjudication) | qualification builds of the Stage 1 code | Fox structural route revision 1: Save, Apply, posture, navigation, Undo/Redo, no-op, Abort recovery |
| RC3 smoke (2026-11-20) | **production** RC3 CPM `026a65cd…` | Fox Save (structural revision 1, 36 constraints, 23 handles) and Apply to another Fox, verified; Tails Save/Apply verified; Pose Info opened for both; Owner functional PASS for Fox and Tails Save, Apply, Undo and Redo. Automated INCOMPLETE 19/21 only from actions outside the procedure |
| RC4 cross-rig run (2026-11-20) | qualification of `f51322d3…` (before the revised contract) | both cross-rig directions adapted and posture-correct; Undo, Redo, repeated no-op on Direction A; `pose_rigs.json` recorded natively; Direction B's 0.0204° led to the revised contract |
| RC4 short reproduction check (2026-11-20) | `d7454891…` = **this CPM**, qualification mode | AUTOMATED PASS 55/55 and Owner PASS: cross-rig Apply verified (0.0199°); posture, placement and facing; only planned keys; **repeat Apply a no-op with no new Undo entry**; **Undo restored the base exactly; Redo available**; Fox and original Tails unchanged |
| RC5 production smoke (2026-11-20) | **this CPM, production mode, installed from the RC5 package** | Tails Save from the original Tails (structural revision 2, production admission); cross-rig Apply adapted and verified (0.0204° within 0.1°), one owned Undo entry; Pose Info opened once without error; `pose_rigs.json` entry `rig_biped`; restoration exact. Automated SMOKE FAIL 15/23 (absent steps only); Owner visual PASS withdrawn |

## 3. The omitted RC5 checks: covered or not

| Omitted RC5 check | Earlier evidence | On this exact production package? | Coverage |
|---|---|---|---|
| Fox Save, Full body (structural rev 1) | Stage 1 run 3; RC3 production smoke (`026a65cd…`); structural suite 337/337 on `b89af5a8…` | No. RC5 exercised the same structural Save path natively in production for Tails (revision 2) | **Covered by earlier native evidence on an earlier build plus offline regression on this build.** The RC3→RC4 changes on the same-rig path are: bounded offset equivalence (inert when offsets are equal, accepting only differences ≤ 0.005° / 0.0001), the wider P7 envelope (more permissive) and the no-work check before writing |
| Fox Apply to another Fox, posture, placement, target isolation | RC3 production smoke (verified; Owner PASS); Stage 1 run 3 (posture, PEER) | No | **Covered, same as above.** Fox-specific Apply on the RC4 code has not run natively |
| Fox Undo / Redo | RC3 Owner PASS; Stage 1 run 3 HISTORY; RC4 short check Undo exact and Redo available (Tails, this CPM) | No | **Covered.** Undo ownership code (P3/P6) is unchanged by RC4 and was exercised on this CPM |
| Fox Pose Info | RC3 (opened for both) | No (opened once, for Tails) | Covered for opening; see the Rig row below |
| Repeat Apply no-op without a new Undo entry | RC4 short check on this CPM (automated and Owner PASS); RC4 run Direction A | No (not performed in RC5) | **Covered on this exact code in qualification mode.** The no-work path does not read the registry mode |
| Final Undo of the cross-rig Apply | RC4 short check on this CPM: base restored exactly | No (not observed in RC5; the Undo entry was created and owned) | **Covered on this exact code** |
| Pose Info **Rig row, as displayed** | none: the sidecar was written natively (RC4 run, RC5); the row's rendering is covered offline only (`F01_RC4_POSE_INFO_RIG.md`) | Opened natively in RC5 without error; the text shown was not reported | **Specifically unverified natively.** Display only |
| Save New immediate feedback | Owner accepted the busy cursor (RC4 decision) | Save ran natively in RC5 | Accepted by the Owner's decision |

Also not exercised natively by any smoke (by kit design, the smoke installs only the CPM and registries):
- **Whole-ZIP merge installation.** Every other packaged file is the published v1.0.0's exact bytes, already in use; the
  README has no runtime role.
- **Version display "1.1.0"** with the packaged inventory: verified offline (RC VERIFY `version`); in the smokes the CPM
  fell back to its build label because v1.0.0's inventory stayed installed.
- **The signed inventory.** The signature does not exist yet; RC VERIFY's updater check covers parse, profile and files,
  not signature verification.

## 4. Risk assessment

**Substantive risk: low.** The reasons:
1. Every functional path the release claims has passed natively at least once, and the two most recently changed paths
   (cross-rig adaptation with the revised envelope; repeat Apply and Undo) passed natively on this exact code. RC5 adds
   the production-mode admission for the structural route on this code.
2. The only code difference between the natively qualified build and the release CPM is the mode line, and the
   production-mode check proves the release's routes are admitted in production.
3. Fox's same-rig route on the RC4 code is the largest gap. It shares the structural adapter and P1–P7 with the Tails
   route that RC5 ran in production; the RC4 changes on that path either do nothing when offsets match or loosen a limit
   by Astra's ruling; and the structural suite (337/337) covers Fox on this build. A Fox-specific regression would show as
   a refusal or a reproduction-mismatch message, both of which change nothing or leave a normal Undo.
4. All safeguards stay in force: checks before any write, one owned Undo per Apply, verified Abort and recovery lockout.

**Gaps that can reasonably be accepted as documented limits of the release evidence:**
- Fox Save/Apply/Undo/Redo not run natively on the RC4/RC5 code (covered by RC3 production and Stage 1 native evidence
  plus offline regression on this build).
- Repeat Apply and final Undo not run in production mode (covered on the identical code in qualification mode).
- The whole-ZIP merge installation and the 1.1.0 version display not exercised natively (identical bytes; offline
  verification).

**Gap with no native evidence at all:** the Pose Info Rig row as displayed. Its failure modes are cosmetic (a wrong or
missing label); the data behind it was recorded natively, and Pose Info opened natively without error. Reasonable to
accept as a documented limitation, or to check informally when the Owner next opens Pose Info on an installed v1.1.0.

## 5. Readiness

From the evidence, RC5 is **ready for the Owner's publication decision**, provided the Owner accepts the limits in
section 4. The RC5 smoke's automated verdict remains **SMOKE FAIL (15/23)**; this assessment does not change it, and
release would rest on the cross-evidence above, not on that run.

Remaining before publication (Owner only):
1. Decide whether to accept section 4's documented limits.
2. Sign the inventory `15db1c1a…`. Signing adds `sfm_character_tools_inventory.sig` and so changes the ZIP hash; the
   signed package then needs `rc5_tool.py verify` (or an equivalent check, including the updater's signature
   verification) before distribution.
3. Merge, push and publish. Workshop Setup still installs v1.0.0 (Archive A); distributing v1.1.0 through Workshop
   needs its own installer release work.

## 6. Owner decision (2026-11-20)

"SFM Character Tools v1.1.0 — Signing and Final Package Verification GO": **the Owner/Designer explicitly accepts the
documented RC5 evidence gaps** (section 4) as low-risk limits of the release evidence. The Fox qualification, the
repeat-Apply (no-op) test and the Undo test are not repeated to complete the smoke checklist.

Preserved unchanged: the RC5 automated **SMOKE FAIL (15/23)** (and the out-of-order INCOMPLETE 9/23); the **withdrawal**
of the Owner's RC5 visual PASS; the RC5 production-mode Tails evidence; the earlier accepted Fox (Stage 1, RC3) and
RC4 native qualifications; this risk assessment. No incomplete test is relabelled as passed. The acceptance is a release
decision on the evidence as it stands, not a verdict change.
