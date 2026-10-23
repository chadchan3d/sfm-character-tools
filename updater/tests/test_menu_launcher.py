# -*- coding: ascii -*-
"""Offline checks of the updater Scripts-menu launcher under SFM's Python 2.7 (TEST-ONLY).

Runs the exact launcher bytes the way SFM runs a Scripts-menu script (exec in one shared namespace),
with sys.executable pointing into a temporary SFM layout, and checks: path resolution, the argument
list (no shell), detachment flags, immediate return without waiting, no success popup, the
"not installed" and "couldn't start" notices (non-modal, reused, suppressed over a modal dialog),
namespace and sys.path isolation, and that no updater, CPM or authority module is imported. One
case starts a real harmless executable (a renamed copy of Windows hostname.exe).

usage: <SFM game>/sdktools/python/2.7/win32/python.exe -E -B updater/tests/test_menu_launcher.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCHER = os.path.join(os.path.dirname(HERE), "menu", "SFM_Control_Group_Updater.py")
EXE_NAME = "SFM Control Group Updater.exe"
RESULTS = []


def check(name, ok, value=None):
    RESULTS.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, "" if ok or value is None else "  value=%r" % (value,)))


class Recorder(object):
    """Stands in for subprocess.Popen; records calls; optionally raises or passes through."""

    def __init__(self, mode="record"):
        self.calls, self.mode, self.children = [], mode, []

    def __call__(self, args, **kw):
        self.calls.append((args, kw))
        if self.mode == "raise":
            raise OSError(5, "Access is denied")
        if self.mode == "real":
            child = REAL_POPEN(args, **kw)
            self.children.append(child)
            return child
        return Inert()


class Inert(object):
    used = []

    def __getattr__(self, name):
        Inert.used.append(name)
        raise AssertionError("launcher used Popen().%s" % name)


REAL_POPEN = subprocess.Popen


def layout(root, with_exe=True, exe_as_dir=False, real_exe=False):
    sfm = os.path.join(root, "Steam Library", "SourceFilmmaker")
    game = os.path.join(sfm, "game")
    tools = os.path.join(game, "usermod", "tools", "SFM Control Group Updater")
    os.makedirs(os.path.join(game, "usermod", "cfg"))
    exe = os.path.join(tools, EXE_NAME)
    if with_exe or exe_as_dir:
        os.makedirs(tools)
        if exe_as_dir:
            os.makedirs(exe)
        elif real_exe:
            shutil.copyfile(os.path.join(os.environ["SystemRoot"], "System32", "hostname.exe"), exe)
        else:
            open(exe, "wb").close()
    return sfm, game, tools, exe


def run_launcher(game, popen, shared):
    code = compile(open(LAUNCHER, "rb").read(), "SFM_Control_Group_Updater.py", "exec")
    saved = (sys.executable, subprocess.Popen, list(sys.path), set(sys.modules))
    sys.executable = os.path.join(game, "sfm.exe")
    subprocess.Popen = popen
    t0 = time.time()
    try:
        exec(code, shared)
    finally:
        elapsed = time.time() - t0
        sys.executable, subprocess.Popen = saved[0], saved[1]
    return elapsed, saved[2], saved[3]


def shared_namespace():
    # A stand-in for SFM's shared Scripts-menu namespace (a __main__ module's globals, which always
    # include __package__; Python 2.7 adds it on a package import otherwise), already holding other
    # scripts' names.
    return {"__name__": "__main__", "__package__": None, "__builtins__": __builtins__, "other_script_value": 42}


def isolation(shared, before_keys, path_before, modules_before):
    new_mods = set(sys.modules) - modules_before
    bad = [m for m in new_mods if re.match(r"(sfm_character_tools|chadchan3d|cpm|sfm_master|authority)", m.lower())]
    return (set(shared) == before_keys and shared["other_script_value"] == 42 and sys.path == path_before
            and not bad), (sorted(set(shared) ^ before_keys), bad)


def notice_box(app):
    return getattr(app, "_chadchan3d_updater_launch_notice_v1", None)


def main():
    src = open(LAUNCHER, "rb").read()
    try:
        src.decode("ascii")
        ascii_ok = True
    except UnicodeDecodeError:
        ascii_ok = False
    imports = set(re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", src.decode("ascii", "replace"), re.M))
    check("static: ASCII; compiles under Python %s" % sys.version.split()[0],
          ascii_ok and compile(src, "l", "exec") is not None)
    check("static: imports only os, subprocess, sys and PySide (no updater, CPM or authority code)",
          imports <= set(["os", "subprocess", "sys", "PySide"]), sorted(imports))
    check("static: no shell execution, no wait/communicate, no module docstring",
          "shell=" not in src and ".wait(" not in src and ".communicate(" not in src
          and not src.lstrip().startswith(('"""', "'''")))

    from PySide import QtGui
    app = QtGui.QApplication.instance() or QtGui.QApplication([])
    root = tempfile.mkdtemp(prefix="ql_menu_")
    try:
        # Found: one Popen with the exact argument list and detachment; returns at once; no popup.
        sfm, game, tools, exe = layout(os.path.join(root, "found"))
        rec, shared = Recorder(), shared_namespace()
        keys = set(shared)
        elapsed, path0, mods0 = run_launcher(game, rec, shared)
        args, kw = rec.calls[0] if rec.calls else (None, {})
        check("found: exactly one start, argument list [exe, --sfm-folder, SourceFilmmaker folder]",
              len(rec.calls) == 1 and args == [exe, "--sfm-folder", sfm], rec.calls)
        check("found: no shell; cwd = updater folder; close_fds; DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP",
              not kw.get("shell") and kw.get("cwd") == tools and kw.get("close_fds") is True
              and kw.get("creationflags") == 0x00000008 | 0x00000200, kw)
        check("found: returns immediately without waiting or talking to the process",
              elapsed < 1.0 and not Inert.used and "stdin" not in kw and "stdout" not in kw, (elapsed, Inert.used))
        check("found: no success popup", notice_box(app) is None)
        ok, detail = isolation(shared, keys, path0, mods0)
        check("found: shared namespace, sys.path and modules untouched", ok, detail)

        # Missing: actionable non-modal notice naming the expected path and folder; no start.
        sfm, game, tools, exe = layout(os.path.join(root, "missing"), with_exe=False)
        rec, shared = Recorder(), shared_namespace()
        keys = set(shared)
        elapsed, path0, mods0 = run_launcher(game, rec, shared)
        box = notice_box(app)
        text = box.text() if box is not None else ""
        check("missing: nothing started; one notice naming the expected exe and the tools folder",
              not rec.calls and box is not None and exe in text and os.path.dirname(tools) in text
              and "extract" in text, text)
        check("missing: notice is non-modal, parentless, retained, not delete-on-close",
              box is not None and not box.isModal() and box.parent() is None
              and box.objectName() == "chadchan3d_updater_launch_notice_v1"
              and not box.testAttribute(__import__("PySide.QtCore", fromlist=["Qt"]).Qt.WA_DeleteOnClose))
        ok, detail = isolation(shared, keys, path0, mods0)
        check("missing: shared namespace, sys.path and modules untouched", ok, detail)
        run_launcher(game, Recorder(), shared_namespace())
        check("missing again: the same notice is reused (one object)", notice_box(app) is box)
        box.hide()

        sfm, game, tools, exe = layout(os.path.join(root, "isdir"), exe_as_dir=True)
        rec = Recorder()
        run_launcher(game, rec, shared_namespace())
        check("a folder at the exe path counts as not installed", not rec.calls and notice_box(app).isVisible())
        notice_box(app).hide()

        # Start failure: notice, no exception escapes.
        sfm, game, tools, exe = layout(os.path.join(root, "denied"))
        rec, shared = Recorder("raise"), shared_namespace()
        keys = set(shared)
        _, path0, mods0 = run_launcher(game, rec, shared)
        box = notice_box(app)
        check("start failure: no exception; 'couldn't be started' notice names the exe",
              len(rec.calls) == 1 and "couldn't be started" in box.text() and exe in box.text())
        ok, detail = isolation(shared, keys, path0, mods0)
        check("start failure: shared namespace untouched", ok, detail)
        box.hide()

        # Modal dialog active: the notice is suppressed (console only).
        dlg = QtGui.QDialog()
        dlg.setModal(True)
        dlg.show()
        app.processEvents()
        sfm, game, tools, exe = layout(os.path.join(root, "modal"), with_exe=False)
        run_launcher(game, Recorder(), shared_namespace())
        check("missing while a modal dialog is active: notice not shown", app.activeModalWidget() is dlg
              and not notice_box(app).isVisible())
        dlg.hide()

        # Real start of a harmless executable through the real Popen.
        sfm, game, tools, exe = layout(os.path.join(root, "real"), real_exe=True)
        rec = Recorder("real")
        elapsed, _, _ = run_launcher(game, rec, shared_namespace())
        child = rec.children[0] if rec.children else None
        deadline = time.time() + 15
        while child is not None and child.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        check("real start: process created and launcher returned at once (process ends on its own)",
              child is not None and child.pid > 0 and elapsed < 2.0 and child.poll() is not None, elapsed)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
