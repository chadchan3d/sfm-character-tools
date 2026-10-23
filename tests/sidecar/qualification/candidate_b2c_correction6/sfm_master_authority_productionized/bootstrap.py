# -*- coding: utf-8 -*-
"""Canonical installed-package bootstrap -- Package-Boundary Correction
(2026-09-21), Section 8.

Purpose: let SFM MAINMENU-level entry code locate (a) the SFM game
installation root and (b) the canonical installed shared-authority
publication directory, WITHOUT depending on:

  - `__file__` on the top-level MAINMENU entry script (established fact:
    "`__file__` is not assumed to exist in MAINMENU execution" --
    `docs/qualification/CPM_ASTRA_AUTHORITY_CONSUMER_DOSSIER.md` Section
    "Runtime environment assumptions"; confirmed independently for the
    real frozen production Normalizer, which never references
    `__file__` or `sys.executable` at all -- it derives paths from the
    loaded `ifm.dll`'s own path instead, a heavier native-module
    dependency this bootstrap module deliberately avoids needing);
  - the current working directory (not a reliable identity in the SFM
    host process -- "Working directory may be the SFM `game` directory
    and is not used as semantic identity", same dossier section);
  - any repository-relative or qualification-candidate-relative path.

Root derivation mechanism: `os.path.dirname(sys.executable)` --
confirmed against the REAL embedded Python 2.7.5 interpreter
(`docs/qualification/SFM_MASTER_SIDECAR_GATE1_H1_PY27_RUNTIME_AUDIT.md`:
`sys.executable == 'E:\\SteamLibrary\\...\\SourceFilmmaker\\game\\sfm.exe'`)
-- i.e. `sys.executable`'s own directory IS the SFM `game` root directly,
available immediately at Python startup, before any native module
(`ifm.dll`) needs to be loaded. This is a DIFFERENT, simpler mechanism
than `resolver.py`'s ifm.dll-based Master-path derivation (which exists
for a different purpose: corroborating the ACTIVE, LOADED ifm.dll
against a resolved Master path) -- this module never touches or assumes
ifm.dll at all.

This module does NOT itself install/copy the package anywhere, and does
NOT itself compile or publish a Master. It only locates: given the game
root, where does the canonical installed publication live, and does
`sys.modules` already show a canonical, non-duplicate copy of this
package loaded. Actual publication into that location is `tools/
sfm_master_sidecar/publisher.py`'s job (Blocker B); actual ownership/
readiness state is `runtime.py`'s job (already built, Astra F6) -- this
module is the missing link between "no `__file__`/CWD available yet"
and "the rest of the already-qualified ownership machinery."

Exact scope (Package-Boundary Targeted Correction, 2026-09-22, Section
6 -- narrowing an earlier, looser reading of what the installed-
isolation regression already proves): `test_package_boundary_installed_
isolation.py` proves this package can be imported and can acquire a
generation, from ONLY its own real files, with no repository/CWD
dependency, ONCE its installed directory has already been placed on
`sys.path`. That test builds `sys.path` directly -- it does not call
`bootstrap_import_path()` itself. This module supplies the deterministic,
`sys.executable`-relative path CALCULATIONS a real MAINMENU entry point
would use to perform that placement (i.e. "where is the package
installed", "where is the published sidecar"); it does not perform, and
no test here exercises, the actual MAINMENU-side `sys.path.insert(...)`
+ `import sfm_master_authority_productionized.runtime` entry seam itself
against a real embedded SFM process. That exact entry seam remains a
real-SFM production Normalizer integration concern, qualified when that
integration happens -- not by this module or its tests.
"""
import os
import sys

# Package-Boundary Correction: the ONE documented, canonical installed
# location for the compiled Master sidecar generation + manifest,
# relative to the SFM game root. Chosen under `usermod/cfg/` to sit
# alongside the canonical Master TXT itself (`resolver.py`'s own
# `_RELATIVE_MASTER_PATH = ("usermod", "cfg", "sfm_defaultanimationgroups.txt")`
# -- the compiled artifact is a derived, co-located sibling of its own
# source, not a separate, hard-to-find install tree).
CANONICAL_INSTALLED_RELATIVE_PATH = ("usermod", "cfg", "sfm_shared_authority")


def game_root():
    """The SFM installation's `game` directory, derived from `sys.
    executable` -- never `__file__`, never the current working
    directory. Real embedded SFM: `sys.executable` IS `.../game/sfm.exe`,
    so its own directory is already the game root with no further
    traversal needed."""
    return os.path.dirname(os.path.abspath(sys.executable))


def installed_authority_root(root=None):
    """The one canonical, documented directory this package expects the
    compiler/publisher to have published a Master sidecar generation +
    manifest into. `root`, if given, overrides `game_root()` -- used
    only by offline tests that cannot assume a real SFM `sys.executable`;
    real production callers never pass it."""
    base = root if root is not None else game_root()
    return os.path.join(base, *CANONICAL_INSTALLED_RELATIVE_PATH)


def bootstrap_import_path():
    """Where THIS package itself (`sfm_master_authority_productionized`)
    is expected to be installed, so MAINMENU entry code can add its
    PARENT directory to `sys.path` before importing it -- derived the
    same `sys.executable`-relative way, never `__file__`. Distinct from
    `installed_authority_root()` (that is the PUBLISHED MASTER SIDECAR's
    location; this is the PACKAGE CODE's own location) -- the two need
    not be the same directory, and are kept as two separate, independently
    documented constants rather than one overloaded path."""
    return os.path.join(game_root(), "usermod", "scripts", "sfm", "mainmenu", "SFM Character Tools")


def ownership_report():
    """A single, explicit snapshot of the canonical-ownership state this
    process currently has for the authority runtime -- for real
    bootstrap code to log/inspect before proceeding, without needing to
    know `runtime.py`'s internals. Never raises; reports whatever is
    observably true right now."""
    canonical_name = "sfm_master_authority_productionized.runtime"
    loaded = sys.modules.get(canonical_name)
    report = {
        "game_root": game_root(),
        "installed_authority_root": installed_authority_root(),
        "bootstrap_import_path": bootstrap_import_path(),
        "runtime_module_loaded": loaded is not None,
        "runtime_is_canonical": None,
    }
    if loaded is not None:
        is_canonical_fn = getattr(loaded, "is_canonical", None)
        if is_canonical_fn is not None:
            report["runtime_is_canonical"] = is_canonical_fn()
    return report
