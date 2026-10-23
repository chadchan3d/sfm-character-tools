# CPM diagnostic logging correction: bounded, descriptive logs

**Status: IMPLEMENTED AND OFFLINE-VERIFIED (2026-10-23).** Real-SFM smoke testing belongs to L-6.

| | |
|---|---|
| Authority | Astra's adjudication of 2026-10-23, *Approved with bounded amendments* (summarized in section 1) |
| Starting checkpoint | `bee7790957474ccba59ead112e3c192d00074bbb` |
| Changed product file | `cpm/app/SFM_Character_Preset_Manager.py` only |
| CPM application before | `230f801dfe5c243c327ed397e76b1d467e9514874732d1ffecafa381d56c69fa`, 793,310 B (the signed software inventory) |
| CPM application after | `ccbed9d794984643fc6f7d7d9c65ef90e5812eb27f85dc4a86855a17c2d3d8df`, **816,665 B** |
| Not changed | profile-2 contract, production updater `cbf11e80…`, signed data sequence 2 (`release.json` `8621a735…`), Normalizer, CPM launcher, optional toolbar button, README |

## 1. The defect and the approved contract

CPM appended every record to `C:\Users\Public\Documents\SFM_CSP_G18AN_SaveNewCopy.log` with no size limit and no
rotation, under a development filename. Startup cleared it only when it did not exist, and the launcher-refusal path
assigned the same destination.

Astra's approved contract:

| Item | Decision |
|---|---|
| Folder | `C:\Users\Public\Documents\SFM Character Preset Manager Logs\` |
| Filename | `CPM - <UTC date_time>Z - pid<PID> - <6-hex session> - <NNN>.log` |
| Encoding | UTF-8 text; existing event names preserved |
| File limit | 2 MiB = 2,097,152 bytes, including header and line endings |
| Retention | five owned files in total across all CPM processes, including the current segment |
| Total | 10 MiB = 10,485,760 bytes |
| Record limit | 64 KiB = 65,536 encoded bytes, including prefix and truncation notice |
| Historical log | untouched; no longer written |

Further rulings: rotate *before* a write would cross the limit; prune the oldest owned segments *before* creating
another; header in every segment; never truncate on reopen; explicit ownership (filename grammar **and** header);
never prune unrelated files, the historical log or anything outside the folder, and never follow links/reparse
points; oversized messages keep their beginning and end, are sliced before encoding and stay valid UTF-8; a small
nonblocking interprocess lock around retention and writing; on failure, no extra file, no bypass of the limits, no
fallback to the old log, a bounded dropped-record count, at most one console notice per failure episode, and
suspension until the next explicit launch/reopen. No service, queue, timer or shutdown machinery. Logging must never
authorize or refuse a product operation. `PROD_OPERATION_END` is bookkeeping, not proof of success.

## 2. Implementation

All in the canonical application. Callers keep calling `log_line()`.

- **Writer** (top of the module, replacing the old `reset_log`/`log_line`):
  - each record is open-write-flush-close, as before;
  - under the lock: the record is prepared (bounded), then appended, rotating first when needed;
  - rotation lists the folder, keeps only *owned* segments (grammar + regular non-reparse file, checked with
    `GetFileAttributesW` through the R14 private `kernel32` handle + identifying header), prunes oldest-first until at
    most four remain and the total leaves room, then creates the next segment with `O_CREAT|O_EXCL` and writes its
    header. Unknown file attributes stop retention, so the logger stops writing instead of guessing;
  - each process appends only to its own segment. If another process pruned it, or it was modified externally (size
    differs from what this process wrote), the next write rotates;
  - lock: one byte of the fixed, empty `CPM - writer.lock`, taken with `msvcrt.locking(LK_NBLCK)`; never waited for.
- **Record format:** `<UTC ISO time>Z #<sequence> s=<session> w=<window> op=<operation> | <existing text>`, CRLF.
  Sequence numbers follow write order within a process.
- **Header:** `SFM Character Preset Manager diagnostic log cpm-log-v1 | build_sha256=… version=… | session=… pid=…
  run_id=… | segment=… created=…Z | python=… | limits file_bytes=2097152 files=5 total_bytes=10485760
  record_bytes=65536`. The build SHA-256 is the loader-supplied `__chadchan3d_cpm_build_sha256__`.
- **Failures:**
  - lock contention drops and counts the record (no suspension, no console notice);
  - any filesystem failure (folder, lock file, listing, pruning, creation, write) drops and counts the record,
    suspends writing and prints once: "CPM couldn't write its diagnostic log. You can keep using the tool. If you need
    troubleshooting help, check that the log folder is writable.";
  - `StartProdTool()` and `prod_r15_launcher_refusal()` call `prod_log_rearm()` (one retry per explicit launch or
    reopen);
  - the next successful write is preceded by `PROD_LOG_DROPPED count=N last_reason=…`.
- **Retired:** the fixed-file destinations `OUTPUT_PATH` and `PROD_OUTPUT_PATH`, and the startup `reset_log()` call.
  `reset_log()` remains for dormant callers and touches nothing.

### Diagnostic additions (only where evidence was missing)

| Boundary | Added |
|---|---|
| Launch/reuse/reopen | `PROD_R15_LAUNCH_RESULT outcome code window run_id`; window-instance id (`w=`) on every record |
| Close | `PROD_CLOSE_DEFERRED reason='fit-stage-running' or 'operation-active'`; `w=` on the finalized close |
| Operations | operation id (`op=`) on every record inside an operation; `PROD_OPERATION_OUTCOME` at the existing decision points; `PROD_OPERATION_RESULT` after `PROD_OPERATION_END` |
| Refusals before an operation | `PROD_OPERATION_REFUSED kind reason` (another action active, model context unverified, operation not started, Clothing Fit without targets) |
| Exceptions | the outcome record adds error type, last phase and the existing native/durable commit and recovery facts beside the existing `PROD_ACTION_ERROR` and traceback |

Authority, selection and refresh were already covered (`PROD_PROVIDER_HEALTH`, `PROD_CPM_OPERATION_AUTHORIZED` /
`_REFUSED` with the generation SHA-256, `PROD_MODELS`, `PROD_SELECTION`, `PROD_SELECTION_PROVIDER_GATED`) and are
unchanged. No scene scan, DME read, broker call, resource sample or dump was added.

### Outcome vocabulary and decision points

| Outcome | Recorded where |
|---|---|
| `verified` | Save/Update after the existing re-read + `prod_validate_preset`; Favorite, Trash, Review/Reclassify after their existing durable verification; Apply when `prod_apply` returns `committed-verified`; Clothing Fit when targets changed and passed post-stage verification; guard failure after a durable change whose readback was verified |
| `no-op` | cancelled Save/Update/Delete prompts; Apply `no-op`; Clothing Fit with every target already matching or skipped |
| `completed` | the non-mutating guarded actions (Refresh Models, Select Model, Clear Model, Model Info, Preset Info, Help) |
| `refused` | `ProdCpmOperationAuthorityError`; the existing "name already exists" and "preset does not match" branches; plus `PROD_OPERATION_REFUSED` before an operation |
| `failed-precommit` | any other failure with no native or durable commit recorded |
| `committed-unverified` | native commit recorded; durable write without verified readback; Clothing Fit closed after a commit before post-stage verification |
| `recovery-verified` / `recovery-unverified` | the existing Apply/Fit abort-and-verify verdicts (`prod_log_note_recovery`) and `ProdRecoveryUnverifiedError` |
| `partial` | Clothing Fit stopped after some targets were committed and verified |
| `not-recorded` | `PROD_OPERATION_RESULT` when no decision point recorded an outcome. Never success by default |

The classification mirrors the branches `guard()` already uses to choose the user-facing message; it changes no
message, state or control flow.

## 3. Verification

### Focused suite: `cpm/convergence/tests/test_cpm_app_bounded_logging.py`

**72/72 under Python 2.7.5 (real PySide/Qt 4.8) and 72/72 under Python 3.10 (behavioral Qt model).**

The logger units execute the app's actual logger block (extracted verbatim) against a temporary folder. The
integration cases launch the actual application through the R15 harness: the real launcher, module and `ProdWindow`,
with `C:\Users` remapped into the fixture. Two process-level cases (lock holder, concurrent writers) run as child
interpreters.

| Astra case | Evidence |
|---|---|
| 1 Creation | grammar filename with pid and session; header with build, version, session, pid, run id, segment, UTC creation, Python, limits; UTC/sequence/session/window/operation prefix; UTF-8 round-trip (é, 日本, emoji); CRLF; empty lock file |
| 2 Limits | a 65,536-byte record is kept whole and one byte more is truncated within 65,536; the file is filled to exactly 2,097,152 B, then the next record rotates (full file unchanged, new segment with header); across 7 segments, never more than 5 files, 2,097,152 B per file and 10,225,075 B in total; segments 003–007 retained; a 300,018-character mixed-script record keeps its beginning and end with a notice, as valid UTF-8; a 10,000,000-character message is bounded within 5 s |
| 3 Preservation | historical log (outside and inside the folder), unrelated `.log`, near-miss name, grammar-named foreign file without header, grammar-named directory, other extension and a directory junction: all byte-identical or present after 7+ rotations; retention applied to owned segments only. A file symbolic link could not be created without the Windows symlink privilege, so that sub-case did not run |
| 4 Failures | unwritable folder: `False`, never raises, one notice for 50 records, suspended, no retry until rearm, then `PROD_LOG_DROPPED count=51`; failed deletion: no sixth file, suspended, one notice; read-only current segment: contained; lock held by another process: 5 records dropped in under 1 s, no notice, no suspension, then reported as `lock-busy`; real app with a blocked folder: window created and usable, one console notice, nothing else written |
| 5 Concurrency | folder pre-filled with five full owned segments; two processes × 401 records under contention. An observer (4,329 polls) saw at most 5 files, 2,082,110 B per file and 10,410,550 B in total; rotations pruned the shared segments; each file holds one process's records in sequence order; written + reported drops + pending drops = attempts for each writer |
| 6 Identity | launch → `created window=1`; reuse → same window, same segment, no truncation; close finalizes with `w=1`; reopen → `created window=2`, same session and run id, sequence continuous |
| 7 Outcomes | through the real `guard()`: verified, no-op, completed, not-recorded, failed-precommit, refused (authority; preset mismatch), committed-unverified (native; durable), recovery-verified, recovery-unverified, verified-after-UI-failure, each with BEGIN/OUTCOME/END/RESULT on the same `w=`/`op=`; unchanged dialog and status copy; real refusals (another action active; Clothing Fit without targets); real Refresh Models failure and success; deferred close then finalized |

The suite's final guard confirms from a clean interpreter that the real log folder was never created and the real
historical log is byte-identical (`caddb7db…`, 895,505 B).

### Existing regressions: candidate versus the starting checkpoint, identical conditions

HEAD (`230f801d…`) was exported to a scratch tree outside `C:\Users` and run with the same harnesses.

| Suite | Candidate | HEAD | Note |
|---|---|---|---|
| R15 (2.7.5 real + model, 3.10 model): 15 scenarios | **471/471** | 471/471 | after the harness repairs below; static: the same 4 historical byte pins fail in both |
| Empty states (2.7.5) | 15/15 | 15/15 | |
| Operation context (publish/suite/compare) | 108/108, 108/108, 3/3 | identical | |
| Clothing Fit | 95/95, 95/95, 3/3 | identical | |
| Canonical route | 84/85 | 84/85 | same historical `derivation.added_top_level_is_bounded` |
| Convergence gates | 147/148 | 147/148 | same historical Normalizer pins |
| R14 ctypes isolation (2.7.5) | 17/18 | 17/18 | same historical `r14.normalizer_pinned` |
| Quick Launch ASE (2.7.5) | 232/233 | 231/233 (no `.git` in the export) | the candidate's one failure is the pre-commit "CPM app unchanged from HEAD" guard |
| Quick Launch distribution | refused | refused | pre-existing and unrelated: `cpm_ase_quick_launch.py` changed in `bb956de` after its QL-2 identity record |
| Profile-2 integration | stops at the spec | — | expected: the inventory spec pins the CPM app at `230f801d…` and refuses to stage the new bytes. The layout and locator boundaries are unchanged by this correction (accepted 27/27 at `8f135eb9…`); the signed sequence-2 package was read and is byte-identical |

### Test-harness changes (no product effect)

- **R15 harness:**
  - follows the bounded folder: `log()` reads every segment and `log_files()` lists them; it also remaps `os.open`,
    `listdir`, `remove`, `unlink`, `stat`, `lstat` and `mkdir` below `C:\Users`;
  - checks the private log destination instead of the retired `OUTPUT_PATH`;
  - two pre-existing gaps repaired, both applied identically to the HEAD comparison:
    - the fake `sfmApp` now has `HasDocument`. Without it, every real-Qt launch raised an error dialog that waited for
      a click;
    - host poisoning tolerates the current Normalizer no longer binding `OUTPUT_PATH`. This restores the full
      lifecycle/modal scenarios (reuse, three close/reopen cycles, deferred Escape), which had stopped after the first
      click.
- **Canonical-route harness:**
  - a bounded `LOGFIX_*` allow-list entry: two changed functions, the new logging names, the two retired names and the
    two new imports;
  - extraction namespaces receive the real logging-only helpers, with `log_line` still stubbed.

## 4. Limitations and disclosed choices

- **Contention drops:** under a deliberate tight-loop race between two writers, the nonblocking lock drops a large
  share of records (60–80% in the race above). Every drop is counted and reported, and the limits held throughout.
  Interactive CPM is unlikely to produce such races.
- **Refusals raised as ordinary exceptions:** preconditions raised as plain `RuntimeError` (for example "Select a
  preset first.") are classified `failed-precommit`, meaning stopped with nothing committed. `refused` is reserved for
  the explicit refusal decision points listed above.
- **Folder itself:** the reparse check applies to files considered for pruning. A log folder that is itself a junction
  is used as given; only files with this logger's grammar and header are ever pruned.
- **Python 2.7 lone surrogates:** under Python 2.7, a lone surrogate in a message encodes as CESU-style bytes; all
  other text stays valid UTF-8. Truncation always cuts at UTF-8 boundaries.
- **Limits:** they are logical file-byte limits. A file modified by another program is not appended to, and the logger
  rotates instead.

## 5. Release consequences (not done here)

The CPM application identity changes from `230f801d…` (793,310 B) to `ccbed9d7…` (816,665 B). Required next, under
separate authorization:
1. update the inventory spec and regenerate the unsigned 31-file software inventory;
2. owner signing and verification;
3. the README logging section;
4. final packaging and L-6, including the real-SFM smoke check: launch, an ordinary operation, a safe refusal,
   close/reopen and log inspection.

No profile-2 change, updater rebuild or data re-signing is required.
