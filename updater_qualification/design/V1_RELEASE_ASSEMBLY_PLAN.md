# SFM Character Tools v1 — Release Assembly Plan (for L-6)

**Status:** plan approved, 2026-10-22, with Astra's adjudication of Questions 1–7 (decisions D1–D7)
owner-approved and recorded in `V1_RELEASE_ADJUDICATION_ADDENDUM.md`; where it differs from a recommendation
below, the addendum governs. Approval of the plan authorizes no step: each step in §5 needs its own authorization.
Starting checkpoint `4c8d165d…`.
**Integration correction (2026-10-23):** `V1_PROFILE2_INTEGRATION_CORRECTION.md` moves the software to Scripts >
SFM Character Tools under `sct-authority-profile-2`, and bundles the Candidate C data in the single ZIP. It
supersedes these identities:
- step 5's build, which must be rebuilt;
- step 6's profile-1 inventory, which must be re-signed (unsigned `2e3a8036…` after the same-day menu isolation
  correction, section 10 of that record; `08c9e78e…` is superseded);
- step 7's sequence-1 package, replaced by sequence 2 for profile 2;
- the single ZIP `5aa968b7…`.

The entries below are historical where so marked.

**Completed:**
- step 2: the production key, owner-held (key id `ed25519-5d879134807dff6d`, public key
  `7f2b9a53fcad0a7818ef5be52ed9fdc8826ac51e3923db30461ddbc96539dba1`);
- steps 3–4: key embedding and the menu launcher (2026-10-22; see the Ledger);
- step 5: the production updater build, v0.1.0, bundle identity `34aa4d0d…` (2026-10-23; see the Ledger);
- step 6, inventory: owner-signed, `sfm_character_tools_inventory.json` `9672e00e…` / `.sig` `dafe6025…`
  (2026-10-23; see the Ledger);
- step 7: owner-signed `data-v1.0.0`, sequence 1, `release.json` `58752b33…` / `release.sig` `5741eb5f…`, issued
  2026-10-23T03:43:34Z; accepted (non-installing) by the production updater candidate (2026-10-23; see the Ledger);
- step 8: the unpublished ZIPs: core `7e95519f…`, updater `96067dcc…`, Quick Launch `e3630efd…` (unchanged), and
  `SHA256SUMS.txt` `9f2760e4…` (2026-10-23; see the Ledger). This is **superseded** by the single-ZIP distribution
  amendment (`V1_SINGLE_ZIP_DISTRIBUTION_AMENDMENT.md`), which keeps these as historical distribution evidence:
  - the one archive is `SFM Character Tools v1.0.0.zip`, finally `5aa968b7…` after the owner's README corrections
    (it superseded `ce3c7957…`);
  - its external contents manifest is `c6010735…`, in `release/v1.0.0/` (2026-10-23).

  §2.1–§2.4 and the step 8 ZIP list are superseded accordingly.

Normalizer redistribution rights are confirmed by the owner.
**Authority:** R15 and updater R2 Blueprints, Offline Updater v1 Contract Amendment, L Implementation Authorization
Card (§5–§7), v1 Release Baseline Amendment (§5–§6), CPM Convergence Ledger. Completed milestones are not reopened.

## 0. Answer

**Can the exact production-trusted shipping updater be qualified with the unpublished, production-signed Candidate C
release package? Yes, for the release decision that matters, with one minimal amendment and one evidence rule:**

- **Yes:** the shipping updater can install that package from a local folder (L-2 local-package path) with no test
  seam. It is the real first-release user path: an installation on G1 (or customized TXT) receives `data-v1.0.0`
  = Candidate C. Group 5 and every case that needs only that one valid signature run on the exact candidate.
- **Amendment needed (§4.1):** the amendment §5 Group 5 table assumes Candidate C is already installed, so "Get
  Official Data with a changed generation" would be a re-install of the same generation. With a production-only
  trust table, the only validly signed package is the release itself. The changed generation becomes
  **G1 → Candidate C** (the release), not a further test-signed change relative to Candidate C.
- **Evidence rule (§4.2):** cases that need **additional validly signed objects** (a wrong-repository package, a
  downgrade, the same sequence with different bytes, an unsupported-profile inventory) or **test seams** (barrier
  holds, injected process responses, injected write faults) cannot run on a seam-free, production-only executable
  without production-signing fixtures. Production-signed fixtures must never exist: each would be a valid
  official object forever. These cases keep their L-1 to L-5 development evidence on the same source.

## 1. Production signing

### Existing mechanisms (unchanged)

| Item | Where | What |
|---|---|---|
| Algorithm | `cryptography` Ed25519 (R2 D2) | raw 64-byte signature over the exact bytes; key id `ed25519-` + first 16 hex of SHA-256(raw public key) |
| Key generation | `updater/release_tools/make_official_package.py keygen --private KEY.pem --public KEY.pub [--passphrase-file F]` | PKCS#8 PEM (encrypted with a passphrase file); refuses paths inside the repository; prints key id and public hex |
| Data package | `make_official_package.py build …` | compiles the TXT with the canonical compiler (official policy), writes the five files into a new folder, signs `release.json`, self-verifies |
| Software inventory | `updater/release_tools/make_software_inventory.py stage` / `sign …` | stages the 31 spec files byte-exactly; signs `sfm_character_tools_inventory.json`; refuses non-qualified bytes; refuses key or output inside the repository |
| Verification | `official.verify_signature`, `official.trusted_keys()`; `compat/inventory.verify_installation` | one trust table for both data and inventory |
| Trust table | `updater/sfm_character_tools_updater/official.py` `TRUSTED_KEYS = {}` | production keys only; test keys only via `hooks.extra_trusted_keys` (test worker), never in the shipping worker |

### Owner key custody (owner action; Claude never handles the private key)

1. On an owner-controlled machine, in a new folder **outside the repository and every SFM folder**, run `keygen`
   with `--passphrase-file` (a strong passphrase, itself stored separately from the key).
2. Keep **one** production private key. Back it up offline (at least two copies, e.g. two encrypted removable
   media), never in Git, cloud sync folders, the scratch roots or the SFM installation.
3. Record and hand over only `KEY.pub` (64 hex) and the printed key id. Their correctness is checked by the
   self-verification of the first `build`/`sign`.
4. Loss of the key means a new key and a new updater build; compromise means the same plus revocation by a new
   updater release. (No revocation list exists in v1; this is an accepted limitation.)

### Public-key embedding (separately authorized code change)

- `updater/sfm_character_tools_updater/official.py`: `TRUSTED_KEYS = {"ed25519-<16hex>": "<64hex>"}` — the only
  product change.
- Follow-ons in the same change: `updater/SHA256SUMS.txt` (`official.py` line); any qualification assertion that
  the shipping trust table is empty (L-3 W4/L-5 wording) becomes "exactly the production key"; the Ledger.
- Then rebuild the one-folder bundle (§2.2). This rebuilt bundle is the **exact shipping candidate**.

### Signing commands (owner runs, or Claude runs with the owner present supplying the key path; outputs outside the repository)

```
BUILD_VENV\Scripts\python.exe -E -s -B updater\release_tools\make_software_inventory.py stage
    --spec updater\release_tools\character_tools_software_v1.json --out REL\core\usermod
BUILD_VENV\Scripts\python.exe -E -s -B updater\release_tools\make_software_inventory.py sign
    --spec updater\release_tools\character_tools_software_v1.json --root REL\core\usermod
    --software-version 1.0.0 --private KEY.pem --passphrase-file PASS --out REL\inventory
BUILD_VENV\Scripts\python.exe -E -s -B updater\release_tools\make_official_package.py build
    --master sfm_defaultanimationgroups.txt --private KEY.pem --passphrase-file PASS --out REL\data-v1.0.0
    --sequence 1 --data-version 1.0.0 --release-tag data-v1.0.0 --source-commit <40-hex pushed commit>
    --published-at <UTC YYYY-MM-DDTHH:MM:SSZ>
```

Artifacts: `sfm_character_tools_inventory.json` + `.sig`; the five-file `data-v1.0.0` folder. Both signed by the
same production key.

## 2. Software distribution

### 2.1 Core software: `SFM Character Tools v1.0.0.zip`

Destination root is the SFM `game` folder; everything lands under `usermod\scripts`. Sources are the spec
(`character_tools_software_v1.json`, `c143b823…`), all 31 verified at `4c8d165d…`.

| Destination (`<game>\usermod\…`) | Count | Repository source |
|---|---|---|
| `scripts\ChadChan3D_CPM\SFM_Character_Preset_Manager.py` (`d7a8a374…`) | 1 | `cpm/app/SFM_Character_Preset_Manager.py` |
| `scripts\sfm\mainmenu\ChadChan3D\SFM_Character_Preset_Manager.py` (`996ca483…`) | 1 | `cpm/app/launcher/…` |
| `scripts\sfm\mainmenu\ChadChan3D\Rebuild_Control_Groups_Normalizer.py` (`6b5d2941…`) | 1 | `audit_external_runtime/…` |
| `scripts\sfm\mainmenu\ChadChan3D\cpm_authority_adapter.py`, `cpm_compat_v1_projection.py` | 2 | `cpm/convergence/…` |
| `scripts\sfm\mainmenu\ChadChan3D\sfm_master_authority_productionized\*.py` | 23 | `tests/sidecar/qualification/candidate_b2c_correction{2,6}/…` (per spec) |
| `scripts\sfm\mainmenu\ChadChan3D\sfm_master_sidecar\{__init__,format,reader}.py` | 3 | `tools/sfm_master_sidecar/…` |
| `scripts\sfm\mainmenu\ChadChan3D\sfm_character_tools_inventory.json` / `.sig` | 2 | produced in §1 (not in the spec) |
| `scripts\sfm\mainmenu\ChadChan3D\SFM_Control_Group_Updater.py` (new menu launcher, §2.3) | 1 | new, outside the inventory (decision D4) |
| `README.txt` (archive root, not installed) | 1 | new |

The Master/sidecar/manifest are **data**, never part of the software ZIP: users get them from `data-v1.0.0`
through the updater (or keep their own TXT and use Rebuild My Data).

### 2.2 Updater: `SFM Control Group Updater v0.1.0.zip`

- Built by the existing L-5 recipe (`updater/packaging/README.md` §1: CPython 3.10.6, locked hash-checked wheels,
  `build.py --out NEW_FOLDER`), after the key embedding. Output: the one-folder `SFM Control Group Updater\`
  (GUI exe, worker exe, `_internal\`) plus `bundle_manifest.json` (bundle identity).
- Proposed default location (decision D3): `<game>\usermod\tools\SFM Control Group Updater\`. Never under
  `usermod\scripts`; never listed in the inventory; it may also live anywhere the user chooses (the GUI detects
  installations, and `--sfm-folder` selects one).

### 2.3 Python 2.7 Scripts-menu launcher (design only; separately authorized code)

`usermod\scripts\sfm\mainmenu\ChadChan3D\SFM_Control_Group_Updater.py` (Scripts → ChadChan3D →
SFM_Control_Group_Updater):
- resolves the SFM `game` folder from `sys.executable`'s folder, computes the fixed default exe path
  (`usermod\tools\SFM Control Group Updater\SFM Control Group Updater.exe`), checks it is a regular file;
- starts it with `subprocess.Popen([exe, "--sfm-folder", <SourceFilmmaker folder>], close_fds=True,
  creationflags=DETACHED_PROCESS)` and returns immediately — no wait, no pipes, no import of updater code;
- if the exe is missing, shows one message box naming the expected folder and the download; nothing else;
- tells the user in one line that installing data requires closing SFM (the updater's process gate enforces it).

It imports only Python 2.7 stdlib plus SFM's Qt for the message box, and loads no updater, CPM or authority module.

### 2.4 Optional Quick Launch

Unchanged: `SFM Character Tools - CPM Quick Launch (optional) v1.0.0.zip`, `e3630efd…`, outside the core inventory and
the updater. Attached to the same software release.

### 2.5 GitHub releases (layout; publication is later and separate)

- Software release, tag `v1.0.0` (must **not** match `^data-v…$`, so discovery ignores it): the core ZIP, the
  updater ZIP, the Quick Launch ZIP, `SHA256SUMS.txt`.
- Data release, tag `data-v1.0.0`, neither draft nor prerelease: exactly the five package files as assets (the
  discovery code requires the asset names to be exactly the signed files).

## 3. Official data: `data-v1.0.0` artifact specification

| Package file | Source / identity |
|---|---|
| `sfm_defaultanimationgroups.txt` | repository Master = corrected Candidate C `1d855cd34b90a2e6254d97eb4c6ac4b08ccc64d994b8e6a754ddac8466b155ec`, 3,973,478 B (last changed in `baca3f40…`) |
| `manifest.json` | compiled by the producer; must equal `6c7568063a69de2a22c05f55df066db369f3340e68d0208f9f36a4c017c3c7ae` |
| `sfm_master_0_3791677522119a6ca45c1092743041dc07014cfa1fd0891526db995bcf526a16.sfmsidecar` | compiled; must equal `3791677522119a6ca45c1092743041dc07014cfa1fd0891526db995bcf526a16` |
| `release.json` | schema 1, `sfm-character-tools-data`, `chadchan3d/sfm-character-tools`, channel `stable`, sequence **1**, data_version `1.0.0`, tag `data-v1.0.0`, `source_commit` (40-hex, pushed, containing this Master), `published_at` (decision D6), minimum updater contract 1, profiles `[sct-authority-profile-1]`, sidecar contract 0/0, compiler build `sfm-master-sidecar-compiler-50dd1804`, signing key id, the three file identities |
| `release.sig` | 64-byte Ed25519 over the exact `release.json` bytes |

Pre-sign check: `tools/validate_master.py` matches its producer pin `62d5273e…` (verified at `4c8d165d…`); the
compiled sidecar/manifest must reproduce the amendment identities or the package is discarded.

**As the Group 5 fixture:** suitable. It is the exact artifact users will receive, needs no test seam or test key,
and installs a generation that differs from G1 by Candidate C's taxonomy corrections (a "changed control" is
picked from the existing G1→Candidate C difference set by the fixture recipe). Conditions:
- it stays **unpublished** until L-6 passes, and the published assets are byte-identical to the qualified ones;
- if L-6 forces a data change, that package is never published and the next is **sequence 2** (the owner's
  installation will have recorded high-water 1);
- `published_at` is signed and cannot be changed after signing (D6).

## 4. L-6 readiness

### 4.1 Minimal amendment (Group 5, supersedes the amendment §5 Group 5 rows only)

Resolved by the addendum (ruling 1 and its Group 5 reconciliation): G1 → Candidate C → G1, NOOP on both
generations, a named changed control; then the pre-test installation and updater records are restored (ruling 6).

1. Start: live installation = exact G1 data + the v1.0.0 core software and production-signed inventory.
2. Rebuild My Data on G1 → verified NOOP.
3. **Get Official Data** from the local, unpublished, production-signed `data-v1.0.0` folder → installs
   Candidate C (customized-TXT consent as designed); exact `1d855cd3…` / `37916775…` / `6c756806…` afterwards.
   This is the "semantically changed generation"; the changed control is a G1→Candidate C difference.
4. Rebuild My Data on the installed Candidate C → verified NOOP (the amendment's shipping-baseline NOOP).
5. SFM checks after each install, as in the card (CPM and Normalizer `6b5d2941…` acquire authority; the changed
   control resolves to its new group).
6. **Use Another TXT** with a preserved external copy of the starting Master: restores the start state exactly
   (byte-identical Master/sidecar/manifest); the selected file unchanged. (Whether the final live state is G1 or
   Candidate C is decision D7.)

Groups 1–4 on the exact candidate, in scratch installations each carrying the production-signed inventory: every
case that needs no extra valid signature and no seam — tamper of each of the five files, the signature and the key
id; an unknown (test) key; replay of the same package; a changed or missing consumer file; malformed/oversized
sources; CRLF; Use Another TXT edge cases; real SFM detection; locks, legacy lock, share-read handle; worker kill
and GUI close by external process control; the C12 messages reachable without seams.

### 4.2 Evidence rule for cases not runnable on a production-only, seam-free executable

Resolved by the addendum (ruling 2 and its evidence classification).

Reused from L-1–L-5 development evidence (same source, bundle verified by `build.py` pins and
`bundle_manifest.json`), named in the L-6 report: wrong-repository valid package; downgrade; same sequence with
different bytes; unsupported-profile inventory; barrier kills and rollback at each journaled point (Group 3);
injected process-gate responses (Group 2 J1–J10); injected write faults and disk-full (Group 4).
The alternative — a separately identified test-trust qualification build — is **not recommended**: it is not the
shipping candidate either, and adds a second build identity to keep apart (decision D2).

### 4.3 Isolation and restoration

- **Scratch:** a new dedicated scratch root (card §7: outside every SFM search, config and script root) under the
  existing write guard for Groups 1–4; copies of
  the production package and inventory only there; deleted or sealed after the report. The private key never
  enters it.
- **Live (Group 5 only, its own execution authorization):** before any change, hash-record and back up outside the
  installation: `usermod\cfg\sfm_defaultanimationgroups.txt`, the sidecar, `manifest.json`, the
  `sfm_shared_authority` folder, `usermod\cfg\sfm_character_tools_updater\` (including `official_releases.log`),
  the 31 current script files and the Quick Launch files. Re-pin `updater/tests/support/fingerprint.py` only
  when the live installation is deliberately moved (amendment §5).
- **Restoration:** Use Another TXT (step 6) restores the data; the updater's own recovery storage and user backups
  are inspected and recorded, not deleted, unless the owner decides; the high-water record (sequence 1) remains
  unless D7 says otherwise; software files remain the v1.0.0 release (they are the shipping software) unless D7
  says to restore the pre-L-6 scripts from the backup.
- **Packages:** the unpublished package and inventory are kept, hash-recorded, outside the repository until
  publication.

### 4.4 Prerequisites before L-6 begins (in order)

1. Owner decisions D1–D7 below.
2. Production key generated and safeguarded by the owner (§1); public key and key id handed over.
3. Authorized code change: embed the public key (+ `SHA256SUMS.txt`, assertions, Ledger); tests green.
4. Authorized code change: the Scripts-menu updater launcher (§2.3), offline-tested under SFM Python 2.7.5.
5. Rebuild the one-folder updater from the committed source → exact shipping candidate (bundle identity
   recorded).
6. Production-sign the inventory (31 files, software version 1.0.0) and build/sign `data-v1.0.0`
   (sequence 1); verify identities (§3).
7. Assemble the core, updater and Quick Launch ZIPs and `SHA256SUMS.txt` (unpublished).
8. L-6 card and amendment §5 reconciliation per §4.1–§4.2 approved; Group 5 restoration plan approved.

## 5. Ordered implementation sequence

| # | Step | Who | Output |
|---|---|---|---|
| 1 | Approve this plan and D1–D7 | Owner (Astra review) | decisions |
| 2 | Generate, back up and safeguard the production key | Owner | `KEY.pub`, key id |
| 3 | Embed the public key; update `SHA256SUMS.txt` and trust assertions; commit | Claude (authorized) | commit |
| 4 | Scripts-menu updater launcher + offline tests; commit | Claude (authorized) | commit |
| 5 | Build the one-folder updater from that commit | Claude | bundle + `bundle_manifest.json` |
| 6 | Stage + production-sign the inventory | Owner signs (ruling 3); Claude stages and verifies | `.json`/`.sig` |
| 7 | Build + production-sign `data-v1.0.0` | Owner signs (ruling 3); Claude verifies identities | five files |
| 8 | Assemble the ZIPs and checksums (unpublished) | Claude | release artifacts |
| 9 | L-6 Groups 1–4 on the exact candidate in scratch | Claude (authorized) | report |
| 10 | L-6 Group 5 on the live installation | Owner-operated, Claude-staged (authorized) | report, restoration |
| 11 | Publish `v1.0.0` and `data-v1.0.0` | Owner (separately authorized) | GitHub releases |

## 6. Owner decisions (resolved: see `V1_RELEASE_ADJUDICATION_ADDENDUM.md`)

- **D1** Key custody: approve the custody procedure (§1) and who runs the signing commands (owner-run, or
  Claude-run with the owner supplying the key path in the session).
- **D2** Evidence rule §4.2 (reuse development evidence; no test-trust build) — recommended — or a test-trust twin.
- **D3** Updater location `usermod\tools\SFM Control Group Updater\` as the fixed launcher target.
- **D4** Menu launcher outside the signed inventory (recommended: it consumes no authority; the 31-file
  reconciliation stays intact) or added to it (spec change, 32 files).
- **D5** Packaging: separate core and updater ZIPs (recommended) or one combined ZIP; software tag `v1.0.0`;
  inventory software version `1.0.0`.
- **D6** `published_at` value: the signing time (recommended) or a planned publication time.
- **D7** Final live state after Group 5: keep the v1.0.0 release with Candidate C (the owner as first user) or
  restore G1 data / pre-L-6 scripts; and whether to keep the sequence-1 high-water record.
- **Confirm:** the top-level `README.md` says the Normalizer source is externally owned with no redistribution
  claim; amendment Decision A ships it in the v1 release. Confirm the redistribution right and align the README
  before publication.
