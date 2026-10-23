# Audit-Only External Runtime Snapshot Manifest

> **Current status (2026-10-22):** `Rebuild_Control_Groups_Normalizer.py` in this directory is now the final v1
> Normalizer, `6b5d294116765aa1941e0f98394b4b6e35ad0acd2f80c90aba418b13c9b6130d` (496,210 B). It is the source of the
> signed software inventory's `normalizer` entry, admitted by the v1 Release Baseline Amendment. The owner confirms
> the right to redistribute this final implementation in the SFM Character Tools v1 release. The text below is the
> historical record of the earlier audit-only snapshot and its identities; it does not describe the current file.

This directory holds a **read-only, audit-only snapshot** of a file that lives outside this
git repository, in the real Source Filmmaker installation. It exists solely so an independent
auditor reviewing this repository's archive can inspect the actual bytes of the one functional
change the Production Normalizer Integration checkpoint made, without needing filesystem access
to the real SFM install.

**This snapshot is not a second production copy and not a new source of authority.** The single
real, live, authoritative copy of this file remains exactly where it has always been:

```
E:\SteamLibrary\steamapps\common\SourceFilmmaker\game\usermod\scripts\sfm\mainmenu\ChadChan3D\Rebuild_Control_Groups_Normalizer.py
```

Nothing in this repository reads from, writes to, or depends on the copy in this directory. The
three integration test harnesses (`test_normalizer_integration_bootstrap.py`,
`test_normalizer_integration_acquisition.py`, `test_normalizer_integration_native_protect.py`)
continue to read the real, live, installed file directly from the absolute path above, exactly as
before -- this snapshot changes nothing about how those harnesses work.

## Snapshotted file

| Field | Value |
|---|---|
| Original installed path | `E:\SteamLibrary\steamapps\common\SourceFilmmaker\game\usermod\scripts\sfm\mainmenu\ChadChan3D\Rebuild_Control_Groups_Normalizer.py` |
| Byte size | 355,415 bytes |
| Line count (newline-terminated lines) | 13,939 |
| SHA-256 | `cdc909a6da9d64c01e8cacf25769e9063a2c25198d4c2e0c2068417a6020e867` |
| Newline style | pure LF (0 CRLF sequences found; matches the real installed file's own pre-existing convention, unchanged by this integration) |
| Encoding | pure ASCII (the file's own `# -*- coding: ascii -*-` declaration; independently confirmed by direct byte-level decode) |
| Reflects final post-correction production file? | **Yes.** This snapshot was taken AFTER the independent-audit-driven protection-lifetime correction (2026-09-22, second correction -- the handle is now acquired immediately before the release-owning try/finally, with the protected stability check as its first operation inside that try) was applied to the real installed file. It is byte-for-byte identical to the file the real SFM installation currently runs. |

## Identity history (for audit continuity)

| Stage | SHA-256 |
|---|---|
| Pre-integration (frozen, before any of this arc's work) | `6656aa9022d458c22c2549da5dfdc14539a572d91200c3f0f459c1453dfd092e` |
| Post-integration, commit `9202933` (before any correction) | `f69a57436d46252fb78d9ae2a2155d7206e07869c74ac5f4d28f6676f5ef2cf0` |
| Post-correction 1 (commit `eff7d96` -- fail-closed protection, first pass) | `88805dbbcebf8c813a97b5346194ff546ecd2a0ef7c6ab47192734b41e1fa2ef` |
| **Post-correction 2 (this snapshot -- protection-lifetime/leak fix)** | **`cdc909a6da9d64c01e8cacf25769e9063a2c25198d4c2e0c2068417a6020e867`** |

## Verification

The exact command used to confirm this snapshot is byte-identical to the live installed file at
the time it was taken:

```python
import hashlib
src = r"E:\SteamLibrary\steamapps\common\SourceFilmmaker\game\usermod\scripts\sfm\mainmenu\ChadChan3D\Rebuild_Control_Groups_Normalizer.py"
dst = r"audit_external_runtime\Rebuild_Control_Groups_Normalizer.py"
assert open(src, "rb").read() == open(dst, "rb").read()
```

An independent auditor can re-run the same comparison against a real SFM install, or simply trust
the SHA-256 above and compare it to the value reported for the live file at the time of any future
correction.
