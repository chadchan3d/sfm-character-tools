# SFM Character Tools v1.1.0: GitHub publication receipt

**Authority:** "SFM Character Tools v1.1.0 — GitHub Publication GO" (Owner/Designer, 2026-11-20). Workshop Setup and the
Workshop item were not changed. The Owner's installed v1.0.0 (CPM `ccbed9d7…`, no registries) was left in place for
the planned Workshop upgrade test.

## Published

| Item | Value |
|---|---|
| Release | **SFM Character Tools v1.1.0**, https://github.com/chadchan3d/sfm-character-tools/releases/tag/v1.1.0 |
| Published | 2026-11-21T04:51:53Z; not a draft, not a prerelease; GitHub "Latest" |
| Tag | `v1.1.0` (lightweight) → `1aaf8efa761096769a3975021b2775e2450cc842` |
| Branches | `master` fast-forwarded `efe8984` → `1aaf8ef`; `feature/f01-pose-library` `407ac5a` → `1aaf8ef`. No force push, rebase or history rewrite |
| Notes | `release/v1.1.0/GITHUB_RELEASE_NOTES.md`; the published body equals the file |

| Asset | Size | SHA-256 (GitHub digest = local original = anonymous download) |
|---|---|---|
| `SFM.Character.Tools.v1.1.0.zip` | 17,846,671 | `0f64eb1306a57f7065db6dcc8419e7e909525a9057af1ee67dce0c8fcc6b8b57` |
| `SHA256SUMS.txt` | 97 | `e2019ba700337ec89f797068109b53984f2fccfbbded7b5ac75d7b3277c03155` |
| `ZIP_CONTENTS_SHA256.txt` | 146,979 | `8985f4c93293031c28ba54e864cc9c3b84b4f996bd857e503d7030f2085d63b9` |

## Checks

- **Before pushing:** remote unchanged since the plan (`master` `efe8984`, feature `407ac5a`); both fast-forward to
  `1aaf8ef`; no `v1.1.0` tag or release existed. ZIP, signature (production key `ed25519-5d879134807dff6d`, inventory
  `15db1c1a…`, version 1.1.0), both checksum files (equal to the committed copies; every `ZIP_CONTENTS` line matches its
  entry) and the notes (equal to the commit) verified. Outgoing changes (397 files) scanned: no user-profile or temporary
  paths (only `C:\Users\Public` log folders), no other email address, no key material, no archives, executables or
  logs; one binary, a test fixture; one author identity, as in the published history.
- **After pushing:** `ls-remote` shows `master`, the feature branch and `v1.1.0` at `1aaf8ef`; the tag object is that
  commit; `v1.0.0` still at `076a85a`.
- **Public release:** the page and all three assets return HTTP 200 without authentication; the downloaded files are
  byte-identical to the local originals and `sha256sum -c SHA256SUMS.txt` passes; GitHub's asset digests match.
- **Homepage:** `README.md` on `master` links "Get v1.1.0" and the manual-install link to the v1.1.0 release, both
  release-README links to `release/v1.1.0/README.txt`, and marks Workshop Setup as currently installing v1.0.0.
- **Rollback and data:** the v1.0.0 release and its ZIP (`1e128e1f…`) remain downloadable; `data-v1.0.0` unchanged
  (not draft, not prerelease), so Get Published Version is unaffected (it uses `data-v*` releases only).
- **Local:** the `master` worktree was fast-forwarded to `1aaf8ef` (no collisions; the canonical
  `sfm_defaultanimationgroups.txt` unchanged by the release).

No publication irregularities.
