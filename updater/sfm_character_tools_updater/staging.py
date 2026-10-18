# -*- coding: utf-8 -*-
"""Staging cleanup (L-4): removes only updater-private preparation and download folders that are
positively identified as safe to delete.

Scope is fixed by construction: only direct children of `<cfg>\\sfm_character_tools_updater\\staging`.
Transactions (all recovery data, including preserved previous files), the release record, the
installation lock, the Master and the authority directory are outside it and are never touched.

A folder is removed only if:
- its name is one the updater creates there: a preparation id (32 hex) or `download-<32 hex>`;
- it is a plain directory (not a link) holding only plain files with names the updater writes
  into staging (at most one sidecar);
- and it is no longer needed: the preparation that was just installed or discarded, the download
  folder the same command created, or any such folder untouched for STALE_SECONDS.
Anything else is left in place and reported.
"""
import os
import re
import time

from . import w32
from .layout import MASTER_NAME, SIDECAR_RE

PREP_NAME = re.compile(r"^[0-9a-f]{32}$")
DOWNLOAD_NAME = re.compile(r"^download-[0-9a-f]{32}$")
STAGED_FILES = frozenset((MASTER_NAME, "master.txt", "manifest.json", "prepared.json", "release.json", "release.sig"))
STALE_SECONDS = 24 * 3600


def _plain(path, directory):
    a = w32.attrs(path)
    if a == w32.INVALID_FILE_ATTRIBUTES or a & w32.FILE_ATTRIBUTE_REPARSE_POINT:
        return False
    return bool(a & w32.FILE_ATTRIBUTE_DIRECTORY) == directory


def _shape(path):
    """The folder's file names if it has exactly the shape the updater writes, else None."""
    if not _plain(path, True):
        return None
    try:
        names = os.listdir(path)
    except OSError:
        return None
    sidecars = 0
    for n in names:
        if not _plain(os.path.join(path, n), False):
            return None
        if SIDECAR_RE.match(n):
            sidecars += 1
        elif n not in STAGED_FILES:
            return None
    return names if sidecars <= 1 else None


def _newest(path, names):
    try:
        return max([os.stat(path).st_mtime] + [os.stat(os.path.join(path, n)).st_mtime for n in names])
    except OSError:
        return time.time()


def remove(layout, name):
    """Remove one staging folder after re-checking its name and shape. Returns None if removed,
    else the reason it was kept."""
    if not (PREP_NAME.match(name) or DOWNLOAD_NAME.match(name)):
        return "unfamiliar name"
    if not _plain(layout.staging, True):
        return "staging folder is not a plain directory"
    path = os.path.join(layout.staging, name)
    names = _shape(path)
    if names is None:
        return "unexpected folder content"
    try:
        for n in names:
            p = os.path.join(path, n)
            if not _plain(p, False):
                return "content changed during cleanup"
            os.remove(p)
        os.rmdir(path)
    except OSError as e:
        return "%s winerror=%s" % (type(e).__name__, getattr(e, "winerror", None))
    return None


def cleanup(layout, consumed=(), now=None):
    """Remove the consumed folders and stale updater folders in staging. Never raises."""
    out = {"removed": [], "kept": []}
    try:
        if not os.path.isdir(layout.staging):
            return out
        now = time.time() if now is None else now
        for name in sorted(os.listdir(layout.staging)):
            path = os.path.join(layout.staging, name)
            names = _shape(path) if (PREP_NAME.match(name) or DOWNLOAD_NAME.match(name)) else None
            if names is None:
                out["kept"].append({"name": name, "reason": "not an updater staging folder"})
                continue
            if name not in consumed and now - _newest(path, names) < STALE_SECONDS:
                out["kept"].append({"name": name, "reason": "recent"})
                continue
            why = remove(layout, name)
            (out["kept"].append({"name": name, "reason": why}) if why else out["removed"].append(name))
    except Exception as e:  # cleanup never changes an operation's outcome
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
    return out
