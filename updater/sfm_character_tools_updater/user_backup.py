# -*- coding: utf-8 -*-
"""User-facing TXT backups (L-4 usability refinement).

Before a replacement of the installed animation-group TXT, a verified copy of that TXT is saved in
`<cfg>\\sfm_character_tools_backups\\`, a folder for the user to open and reuse. It is separate from,
and in addition to, the protected transaction storage (snapshots and retired files), which is
unchanged.

The copy must have the SHA-256 the replacement is bound to (`--confirm-sha`). The backend refuses
any replacement whose installed TXT no longer has that identity, so a completed replacement always
replaced exactly the TXT saved here. Files are created new (CREATE_NEW) and never overwritten; an
existing updater backup with identical content is reused instead of adding another copy.
"""
import hashlib
import os
import re
import time

from . import official, w32
from .messages import Stop

BACKUP_DIR = "sfm_character_tools_backups"
BASE = "sfm_defaultanimationgroups_backup_"
NAME_RE = re.compile(r"^sfm_defaultanimationgroups_backup_\d{8}-\d{6}(_\d{1,3})?\.txt$")
ERROR_FILE_EXISTS = (80, 183)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def backup_dir(layout):
    return os.path.join(layout.cfg, BACKUP_DIR)


def _fail(reason, **details):
    return Stop("REFUSED", "BACKUP_FAILED", reason=reason, **details)


def _read(path, limit):
    with open(path, "rb") as f:
        return f.read(limit + 1)


def save_previous_txt(layout, expected_sha, now=None):
    """Returns {"folder", "name", "sha256", "reused"} for a verified backup of the installed TXT,
    or raises Stop (BACKUP_FAILED, or DESTINATION_CHANGED if the TXT is no longer the one confirmed)."""
    try:
        data = _read(layout.master, official.MAX_SOURCE_BYTES)
    except OSError as e:
        raise _fail("installed TXT could not be read", error=type(e).__name__)
    if len(data) > official.MAX_SOURCE_BYTES:
        raise _fail("installed TXT larger than allowed")
    if sha(data) != expected_sha:
        raise Stop("REFUSED", "DESTINATION_CHANGED", reason="installed TXT is not the one confirmed")
    folder = backup_dir(layout)
    a = w32.attrs(folder)
    if a == w32.INVALID_FILE_ATTRIBUTES:
        try:
            os.mkdir(folder)
        except OSError as e:
            raise _fail("backup folder could not be created", error=type(e).__name__)
        a = w32.attrs(folder)
    if a == w32.INVALID_FILE_ATTRIBUTES or not a & w32.FILE_ATTRIBUTE_DIRECTORY or a & w32.FILE_ATTRIBUTE_REPARSE_POINT:
        raise _fail("backup folder is not a plain folder")
    try:
        names = sorted(os.listdir(folder))
    except OSError as e:
        raise _fail("backup folder could not be listed", error=type(e).__name__)
    for n in names:
        p = os.path.join(folder, n)
        pa = w32.attrs(p)
        if NAME_RE.match(n) and pa != w32.INVALID_FILE_ATTRIBUTES and not pa & (
                w32.FILE_ATTRIBUTE_DIRECTORY | w32.FILE_ATTRIBUTE_REPARSE_POINT):
            try:
                if os.path.getsize(p) == len(data) and sha(_read(p, len(data))) == expected_sha:
                    return {"folder": folder, "name": n, "sha256": expected_sha, "reused": True}
            except OSError:
                pass
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    for i in range(1, 1000):
        name = "%s%s%s.txt" % (BASE, stamp, "" if i == 1 else "_%d" % i)
        ok, err = w32.write_new_file(os.path.join(folder, name), data)
        if ok:
            break
        if err not in ERROR_FILE_EXISTS:
            raise _fail("backup could not be written", error=w32.ename(err))
    else:
        raise _fail("no free backup name")
    try:
        verified = sha(_read(os.path.join(folder, name), len(data))) == expected_sha
    except OSError:
        verified = False
    if not verified:
        raise _fail("backup could not be verified", name=name)
    return {"folder": folder, "name": name, "sha256": expected_sha, "reused": False}
