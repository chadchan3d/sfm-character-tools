# -*- coding: utf-8 -*-
# M-06 W2 native qualification: READ-ONLY Observer v2. TEMPORARY qualification instrument; not product code.
#
# Installed (temporarily, by an authorized native session) as:
#   <SFM game>\usermod\scripts\sfm\mainmenu\M06 Qualification\M06_Qualification_Observer.py
# with m06w2_core.py and its configuration in INSTRUMENT_DIR below. Run from Scripts > M06 Qualification only while
# CPM is idle (closed, or showing its final status). It never moves the playhead.
#
# Configuration selection (one mechanism, verified): tools/stage_instruments.py writes one Observer per staged
# configuration, substituting CONFIG_NAME: M06_Qualification_Observer.py reads m06w2_config.json (the multi-instance
# fixture) and M06_Deferred_Observer.py reads m06w2_deferred_config.json (the deferred fixture). The staged
# configuration records its own config_name; an Observer whose configuration names a different file refuses (the
# observation is written insufficient). Every observation records the configuration name and hash it used.
#
# Read-only by construction (see m06w2_core.py). The core is exec'd into a private dictionary; nothing is placed in
# __main__, sys.modules or any CPM module, and everything lives inside one function that is deleted after it runs.
# Output: one exclusively created JSON observation per run in the configured observation directory. An observation
# whose required evidence is unreadable is written with complete = false and the reasons; it is never "ok".

INSTRUMENT_DIR = u"<INSTRUMENT_DIR>"     # replaced by tools/stage_instruments.py when the run is prepared
CONFIG_NAME = u"<CONFIG_NAME>"           # replaced by tools/stage_instruments.py (one staged Observer per config)


def _m06w2_observer():
    import io
    import json
    import os
    import time

    import sfmApp
    import vs

    core = {"__name__": "m06w2_core_private"}
    core_path = os.path.join(INSTRUMENT_DIR, u"m06w2_core.py")
    with open(core_path, "rb") as f:
        eval(compile(f.read(), core_path, "exec"), core)
    with io.open(os.path.join(INSTRUMENT_DIR, CONFIG_NAME), encoding="utf-8") as f:
        config = json.load(f)
    out_dir = config["observation_dir"]
    watch = None
    watch_path = config.get("watch_path")
    if watch_path and os.path.isfile(watch_path):
        with io.open(watch_path, encoding="utf-8") as f:
            watch = json.load(f).get("created") or []
    stamp = time.strftime("%Y%m%dT%H%M%S")
    try:
        if config.get("config_name") != CONFIG_NAME:
            raise RuntimeError(u"configuration %s names itself %r: not the staged configuration for this Observer" %
                               (CONFIG_NAME, config.get("config_name")))
        record = core["observe"](sfmApp, vs, config, label=u"observer", watch=watch, config_name=CONFIG_NAME)
        record["ok"] = record["complete"]
    except Exception as exc:
        import traceback
        record = {"format": core["FORMAT"], "core": core["CORE_VERSION"], "ok": False, "complete": False,
                  "config_name": CONFIG_NAME,
                  "insufficient": [u"observation aborted: %r" % (exc,)], "traceback": traceback.format_exc()}
    record["taken_local"] = stamp
    record["watch_file"] = watch_path if watch is not None else None
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    seq = len([n for n in os.listdir(out_dir) if n.startswith(u"obs_") and n.endswith(u".json")]) + 1
    path = os.path.join(out_dir, u"obs_%03d_%s.json" % (seq, stamp))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(core["dumps"](record).encode("ascii"))
    reasons = record.get("insufficient") or []
    text = (u"Observation %03d saved: %s.\n%s" %
            (seq, u"COMPLETE" if record["complete"] else u"INSUFFICIENT (%d reason(s))" % len(reasons),
             u"\n".join(reasons[:8])))
    try:
        from PySide import QtGui
        QtGui.QMessageBox.information(None, u"M06 Qualification Observer", text)
    except Exception:
        print(text)


try:
    _m06w2_observer()
finally:
    del _m06w2_observer
