# -*- coding: utf-8 -*-
"""F-01: classify the files SFM leaves in a run's disposable sessions folder (Python 3; read-only).

SFM writes an initial session file when File > New creates a session in a chosen folder, before any model is added
(EC-1 deviation EC1-D1: `ec1_survey.dmx`, 3,984 bytes, no animation set). It may also write `<name>.autosave` beside an
open session. A postflight must tell these apart from a session that was saved with a character in it. Classes:

  starter       a DMX session (`<!-- dmx encoding ... format sfm_session`) holding no animation set, game model or
                channel element type: what File > New writes
  character     a DMX session holding an animation set or a game model (a saved session with a character in it)
  autosave      a `.autosave` file (SFM's periodic copy of an open session); its content is classified alongside
  other         anything else (unexpected)

Element type names are stored as text in both DMX encodings (binary string table, keyvalues2), so a byte search for
the type name is exact for presence. Nothing is written, moved or removed.
"""
from __future__ import print_function

import hashlib
import os
import time

DMX_SESSION = b"format sfm_session"
CHARACTER_TYPES = (b"DmeAnimationSet", b"DmeGameModel")
CHANNEL_TYPES = (b"DmeChannel",)
HEAD_BYTES = 256


def classify_bytes(name, data):
    head = data[:HEAD_BYTES]
    is_session = head.startswith(b"<!-- dmx encoding") and DMX_SESSION in head
    counts = dict((t.decode("ascii"), data.count(t)) for t in CHARACTER_TYPES + CHANNEL_TYPES)
    if name.lower().endswith(".autosave"):
        cls = "autosave"
    elif not is_session:
        cls = "other"
    elif any(data.count(t) for t in CHARACTER_TYPES):
        cls = "character"
    elif any(data.count(t) for t in CHANNEL_TYPES):
        cls = "other"
    else:
        cls = "starter"
    return {"name": name, "class": cls, "session": is_session, "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "element_types": counts,
            "content": ("character" if any(counts[t.decode("ascii")] for t in CHARACTER_TYPES) else "no character")
            if is_session else None}


def classify_folder(folder):
    rows = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            rows.append({"name": name, "class": "other", "detail": "not a file"})
            continue
        with open(path, "rb") as f:
            row = classify_bytes(name, f.read())
        row["mtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path)))
        rows.append(row)
    return rows


def by_name(rows, name):
    """The row for `name`, compared without case (SFM lowercases the session names it writes)."""
    hits = [r for r in rows if r["name"].lower() == name.lower()]
    return hits[0] if len(hits) == 1 else None
