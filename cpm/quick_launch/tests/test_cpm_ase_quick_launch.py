# -*- coding: utf-8 -*-
"""CPM Quick Launch QL-1 -- focused offline verification.

Authoritative design: the Owner-approved CPM Quick Launch Construction
Blueprint (Astra), sections 2, 3 and 7. See cpm/quick_launch/README.md.

Every Qt scenario runs the ACTUAL bootstrap and implementation, deployed into
a fake SFM game root, in its own child interpreter (one child = one SFM
process). Autoinit is modelled as one shared host dictionary used as globals
and locals. Clicks run the ACTUAL, unchanged R15 Scripts-menu launcher against
a small stub CPM implementation that records StartProdTool calls.

Qt is real PySide 1.2 / Qt 4.8 under SFM's embedded Python 2.7.5. Widgets are
kept off screen. The SFM editor hierarchy is modelled with subclasses carrying
the observed native class names (audit section 10.3). Mocks do not qualify
real SFM toolbar behaviour, Extended ASE coexistence or Autoinit itself:
those are QL-2.

Usage (from the repository root):
  <SFM python 2.7.5> -E -B cpm/quick_launch/tests/test_cpm_ase_quick_launch.py --phase=run
  py -3 cpm/quick_launch/tests/test_cpm_ase_quick_launch.py --phase=static
"""
from __future__ import print_function

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types

try:
    import __builtin__ as builtins  # noqa: F401  (Python 2)
except ImportError:  # pragma: no cover
    import builtins

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_QL_DIR = os.path.dirname(_THIS_DIR)
_REPO_ROOT = os.path.abspath(os.path.join(_QL_DIR, os.pardir, os.pardir))
BOOTSTRAP_PATH = os.path.join(_QL_DIR, "autoinit", "ChadChan3D_CPM_ASE_Button.py")
IMPL_PATH = os.path.join(_QL_DIR, "cpm_ase_quick_launch.py")
LAUNCHER_PATH = os.path.join(_REPO_ROOT, "cpm", "app", "launcher", "SFM_Character_Preset_Manager.py")
APP_PATH = os.path.join(_REPO_ROOT, "cpm", "app", "SFM_Character_Preset_Manager.py")
FIXTURE_ROOT = os.path.join(tempfile.gettempdir(), "cpm_ase_quick_launch_ql1_fixture")

MODULE_KEY = "chadchan3d_cpm_ase_quick_launch"
LOADER_MARKER = "cpm-ase-quick-launch-loader-v1"
CPM_MODULE_KEY = "chadchan3d_cpm_app"
BUTTON_NAME = "chadchan3d_cpm_ase_button"
CONTROLLER_NAME = "chadchan3d_cpm_ase_quick_launch_controller"
NOTICE_NAME = "chadchan3d_cpm_ase_quick_launch_notice"
R15_NOTICE_ATTR = "_chadchan3d_cpm_launch_notice_v1"
LAUNCH_FAILED_TEXT = (
    "Character Preset Manager couldn't be opened. Try its Scripts-menu entry. "
    "If that also fails, repair the CPM installation."
)

RESULTS = []


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("%s %s%s" % ("PASS" if condition else "FAIL", name,
                       "" if condition or value is None else "  value=%r" % (value,)))


def _read(path):
    with open(path, "rb") as handle:
        return handle.read()


# ---------------------------------------------------------------------------
# Static checks (Python 2.7.5 and 3.10)
# ---------------------------------------------------------------------------

def static_checks():
    boot, impl = _read(BOOTSTRAP_PATH), _read(IMPL_PATH)
    for label, data, path in (("bootstrap", boot, BOOTSTRAP_PATH), ("impl", impl, IMPL_PATH)):
        try:
            data.decode("ascii")
            ascii_ok = True
        except UnicodeDecodeError:
            ascii_ok = False
        check("static.%s.ascii" % label, ascii_ok)
        check("static.%s.lf_only" % label, b"\r" not in data)
        check("static.%s.coding_cookie" % label, data.startswith(b"# -*- coding: ascii -*-\n"))
        try:
            compile(data, path, "exec", 0, True)
            compiled = True
        except SyntaxError as exc:
            compiled = repr(exc)
        check("static.%s.compiles_py%d.%d" % ((label,) + tuple(sys.version_info[:2])), compiled is True, compiled)
        for literal in (b"sfmApp.ShowTabWindow(", b"sfmApp.RegisterTabWindow("):
            check("static.%s.no_autoinit_rewrite_literal.%s" % (label, literal[7:-1].decode()), literal not in data)
        check("static.%s.no_toolbutton_prefix" % label, b"toolbutton_" not in data)
        code_lines = [line for line in data.splitlines() if not line.lstrip().startswith(b"#")]
        check("static.%s.no_sys_path_change" % label, not any(b"sys.path" in line for line in code_lines))
        check("static.%s.no_model_browser" % label, b"Model Browser" not in data and b"model_browser" not in data)

    tree = ast.parse(boot)
    kinds = [type(node).__name__ for node in tree.body]
    check("static.bootstrap.top_level_is_def_plus_try", kinds in (["FunctionDef", "TryFinally"], ["FunctionDef", "Try"]), kinds)
    check("static.bootstrap.no_docstring", ast.get_docstring(tree) is None)
    check("static.bootstrap.function_name",
          tree.body and getattr(tree.body[0], "name", None) == "_chadchan3d_cpm_ase_quick_launch_bootstrap_v1")
    check("static.bootstrap.no_qt_or_callbacks", b"PySide" not in boot and b".connect(" not in boot)

    for literal, label in ((b"processEvents", "no_process_events"), (b"exec_(", "no_nested_event_loop"),
                           (b"StartProdTool", "no_direct_cpm_entry"), (b"import chadchan3d_cpm_app", "no_cpm_import"),
                           (b"SFM_Character_Preset_Manager import", "no_cpm_from_import"),
                           (b"app.installEventFilter", "no_application_event_filter"),
                           (b"singleShot(", "no_anonymous_single_shots"),
                           (b"setParent(", "no_reparenting_calls")):
        if literal == b"setParent(":
            # Only the controller's own disposal may detach itself.
            check("static.impl.%s" % label, impl.count(literal) == 1 and b"self.setParent(None)" in impl, impl.count(literal))
        else:
            check("static.impl.%s" % label, literal not in impl)

    # The R15 launcher and the CPM application are unchanged from HEAD.
    for label, path in (("r15_launcher", LAUNCHER_PATH), ("cpm_app", APP_PATH)):
        rel = os.path.relpath(path, _REPO_ROOT).replace(os.sep, "/")
        try:
            head = subprocess.check_output(["git", "-C", _REPO_ROOT, "rev-parse", "HEAD:" + rel]).strip()
            work = subprocess.check_output(["git", "-C", _REPO_ROOT, "hash-object", rel]).strip()
            check("static.%s_unchanged_from_head" % label, head == work, (head, work))
        except Exception as exc:
            check("static.%s_unchanged_from_head" % label, False, repr(exc))


# ---------------------------------------------------------------------------
# Child-process scenario environment
# ---------------------------------------------------------------------------

STUB_CPM_APP = b"""# stub CPM implementation for QL-1 offline tests
import sys as _sys


def _record():
    rec = getattr(_sys, "_ql_cpm_record", None)
    if rec is None:
        rec = _sys._ql_cpm_record = []
    return rec


def StartProdTool():
    _record().append(["start", id(_sys.modules.get("chadchan3d_cpm_app"))])
    return {"outcome": "opened", "code": "stub"}


def prod_r15_launcher_refusal(code, path):
    _record().append(["refusal", code])
"""


class Env(object):
    def __init__(self, root):
        from PySide import QtCore, QtGui, shiboken
        self.QtCore, self.QtGui, self.shiboken = QtCore, QtGui, shiboken
        self.root = root
        self.game = os.path.join(root, "game")
        self.autoinit_dir = os.path.join(self.game, "usermod", "scripts", "sfm", "autoinit", "ChadChan3D")
        self.private_dir = os.path.join(self.game, "usermod", "scripts", "ChadChan3D_CPM")
        self.menu_dir = os.path.join(self.game, "usermod", "scripts", "sfm", "mainmenu", "ChadChan3D")
        for path in (self.autoinit_dir, self.private_dir, self.menu_dir):
            os.makedirs(path)
        self.boot_path = os.path.join(self.autoinit_dir, "ChadChan3D_CPM_ASE_Button.py")
        self.impl_path = os.path.normpath(os.path.join(self.private_dir, "cpm_ase_quick_launch.py"))
        self.launcher_path = os.path.normpath(os.path.join(self.menu_dir, "SFM_Character_Preset_Manager.py"))
        self.cpm_path = os.path.join(self.private_dir, "SFM_Character_Preset_Manager.py")
        self.write(self.boot_path, _read(BOOTSTRAP_PATH))
        self.write(self.impl_path, _read(IMPL_PATH))
        self.write(self.launcher_path, _read(LAUNCHER_PATH))
        self.write(self.cpm_path, STUB_CPM_APP)
        sys.executable = os.path.join(self.game, "sfm.exe")
        sys._ql_cpm_record = []
        self.console = _Capture(sys.stdout)
        sys.stdout = self.console
        self.errors = _Capture(sys.stderr)
        sys.stderr = self.errors
        self.app = QtGui.QApplication.instance() or QtGui.QApplication([])
        self.offscreen = _Offscreen(QtCore, QtGui)
        self.app.installEventFilter(self.offscreen)
        self.host = {"__name__": "__main__", "__doc__": None, "__package__": None,
                     "__builtins__": builtins, "unrelated_autoinit_name": 1}
        self.main = None
        self.stack = None

    def write(self, path, data):
        with open(path, "wb") as handle:
            handle.write(data)

    # -- host actions -------------------------------------------------------
    def autoinit(self, flags=0):
        """One Autoinit execution of the deployed bootstrap in shared globals."""
        source = _read(self.boot_path)
        code = compile(source, self.boot_path, "exec", flags, True)
        eval(code, self.host, self.host)

    def scripts_menu(self):
        host = {"__name__": "__main__", "__doc__": None, "__package__": None, "__builtins__": builtins}
        code = compile(_read(self.launcher_path), self.launcher_path, "exec", 0, True)
        eval(code, host, host)

    # -- Qt helpers ---------------------------------------------------------
    def pump(self, ms):
        loop = self.QtCore.QEventLoop()
        self.QtCore.QTimer.singleShot(ms, loop.quit)
        loop.exec_()

    def flush(self):
        self.QtCore.QCoreApplication.sendPostedEvents(None, self.QtCore.QEvent.DeferredDelete)
        self.pump(20)

    def module(self):
        return sys.modules.get(MODULE_KEY)

    def ctl(self):
        module = self.module()
        return None if module is None else module.__dict__.get("_CONTROLLER")

    def named(self, name):
        found = []
        for top in self.QtGui.QApplication.topLevelWidgets():
            if self.shiboken.isValid(top):
                for widget in [top] + list(top.findChildren(self.QtGui.QWidget, name)):
                    if widget.objectName() == name and not any(widget is f for f in found):
                        found.append(widget)
        return found

    def make_main(self):
        QtGui, QtCore = self.QtGui, self.QtCore
        self.main = CQSFMMainWindow()
        self.main.setAttribute(QtCore.Qt.WA_DontShowOnScreen, True)
        self.main.resize(1200, 1000)
        self.stack = QtGui.QStackedWidget(self.main)
        self.stack.setGeometry(0, 0, 479, 935)
        self.main.show()

    def make_editor(self, width=479, row=True, add=True, layout=False):
        editor = CQAnimationSetEditor()
        editor.setObjectName("QAnimationSetEditor")
        parts = {"editor": editor}
        if row:
            bar = CQEditorUpperBarWidget(editor)
            bar.setGeometry(0, 2, width, 39)
            if layout:
                self.QtGui.QHBoxLayout(bar)
            parts["row"] = bar
            if add:
                plus = CQTabbedToolButton(bar)
                plus.setToolTip("Add")
                plus.setGeometry(2, 1, 40, 32)
                parts["add"] = plus
            tools = CQTabbedToolButton(bar)
            tools.setToolTip("Tools")
            tools.setGeometry(width - 42, 1, 40, 32)
            parts["tools"] = tools
        self.stack.addWidget(editor)
        self.stack.setCurrentWidget(editor)
        editor.show()
        return parts

    def close_editor(self, editor):
        editor.deleteLater()
        self.flush()


class _Capture(object):
    def __init__(self, stream):
        self.stream = stream
        self.text = []

    def write(self, data):
        self.text.append(data)
        try:
            self.stream.write(data)
        except Exception:
            pass

    def flush(self):
        pass

    def joined(self):
        return "".join(self.text)

    def count(self, needle):
        return self.joined().count(needle)


def _Offscreen(QtCore, QtGui):
    class Offscreen(QtCore.QObject):
        """Test-only: keep every top-level window (notices, dialogs) off the
        real screen. Production code never installs an application filter."""
        def eventFilter(self, obj, event):
            if event.type() == QtCore.QEvent.Polish and obj.isWidgetType() and obj.isWindow():
                obj.setAttribute(QtCore.Qt.WA_DontShowOnScreen, True)
            return False
    return Offscreen()


def _qt_classes():
    from PySide import QtGui
    global CQSFMMainWindow, CQAnimationSetEditor, CQEditorUpperBarWidget, CQTabbedToolButton

    class CQSFMMainWindow(QtGui.QWidget):
        pass

    class CQAnimationSetEditor(QtGui.QWidget):
        pass

    class CQEditorUpperBarWidget(QtGui.QWidget):
        pass

    class CQTabbedToolButton(QtGui.QToolButton):
        pass


def rect(widget):
    g = widget.geometry()
    return [g.x(), g.y(), g.width(), g.height()]


def clear_of_siblings(row, button, clearance=5):
    """Every visible sibling in the button's band keeps >= clearance px."""
    b = button.geometry()
    worst = None
    for child in row.children():
        if not child.isWidgetType() or child is button or child.isWindow() or not child.isVisibleTo(row):
            continue
        g = child.geometry()
        if g.y() >= b.y() + b.height() or g.y() + g.height() <= b.y():
            continue
        gap = max(g.x() - (b.x() + b.width()), b.x() - (g.x() + g.width()))
        worst = gap if worst is None else min(worst, gap)
    return worst is None or worst >= clearance, worst


def snapshot(row, exclude):
    return [(c.objectName(), c.toolTip() if hasattr(c, "toolTip") else "", rect(c), c.isHidden(),
             c.parentWidget() is row)
            for c in row.children() if c.isWidgetType() and c is not exclude]


def timers(ctl, QtCore):
    return [c for c in ctl.children() if isinstance(c, QtCore.QTimer)]


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_namespace(env, c):
    QtCore, QtGui = env.QtCore, env.QtGui
    env.make_main()
    parts = env.make_editor()
    before = sorted(env.host.keys())
    env.autoinit()
    module, ctl = env.module(), env.ctl()
    c("module.registered", module is not None)
    ns = module.__dict__ if module is not None else {}
    c("module.markers", ns.get("__chadchan3d_cpm_ase_loader__") == LOADER_MARKER
      and ns.get("__chadchan3d_cpm_ase_state__") == "ready"
      and ns.get("__file__") == env.impl_path
      and ns.get("__chadchan3d_cpm_ase_build_sha256__") == hashlib.sha256(_read(env.impl_path)).hexdigest())
    c("host.no_residual_names", sorted(env.host.keys()) == before, sorted(set(env.host) - set(before)))
    c("controller.parent_is_qapplication", ctl is not None and ctl.parent() is env.app)
    c("controller.attached_immediately", ctl is not None and ctl.state == "ATTACHED", ctl and ctl.state)
    env.pump(50)
    buttons = env.named(BUTTON_NAME)
    c("button.created_once", len(buttons) == 1, len(buttons))
    c("startup.cpm_not_loaded", CPM_MODULE_KEY not in sys.modules)

    # Inherited future flags must not change behaviour.
    import __future__
    flags = 0
    for feature in ("division", "print_function", "unicode_literals", "absolute_import"):
        flags |= getattr(__future__, feature).compiler_flag
    env.autoinit(flags)
    c("future_flags.host_unchanged", sorted(env.host.keys()) == before)
    c("future_flags.same_module_controller", env.module() is module and env.ctl() is ctl)

    # Repeated execution: one module, controller, button, set of timers and connections.
    button = buttons[0] if buttons else None
    quit_receivers = env.app.receivers(QtCore.SIGNAL("aboutToQuit()"))
    editor_receivers = parts["editor"].receivers(QtCore.SIGNAL("destroyed(QObject*)"))
    for _ in range(5):
        env.autoinit()
        env.pump(20)
    c("rerun.same_module", env.module() is module)
    c("rerun.same_controller", env.ctl() is ctl)
    now = env.named(BUTTON_NAME)
    c("rerun.one_button_same_object", len(now) == 1 and now[0] is button, len(now))
    c("rerun.ownership_retained", ctl._button is button and env.console.count("already in the toolbar") == 0)
    c("rerun.two_timers", len(timers(ctl, QtCore)) == 2, len(timers(ctl, QtCore)))
    c("rerun.discovery_stopped_while_attached", not ctl._discovery.isActive())
    c("rerun.quit_receivers_stable", env.app.receivers(QtCore.SIGNAL("aboutToQuit()")) == quit_receivers)
    c("rerun.editor_receivers_stable",
      parts["editor"].receivers(QtCore.SIGNAL("destroyed(QObject*)")) == editor_receivers)
    c("rerun.click_receivers_one", button is not None and button.receivers(QtCore.SIGNAL("clicked(bool)")) == 1,
      button and button.receivers(QtCore.SIGNAL("clicked(bool)")))
    c("rerun.host_unchanged", sorted(env.host.keys()) == before)

    # Callbacks keep private-module globals when shared globals change.
    for name in ("os", "sys", "QtCore", "QtGui", "find_free_slot", "console", "_CONTROLLER", "traceback"):
        env.host[name] = None
    fn = ctl.launch
    globs = getattr(fn, "__func__", getattr(fn, "im_func", None))
    globs = getattr(globs, "__globals__", getattr(globs, "func_globals", None))
    c("callbacks.private_globals", globs is module.__dict__)
    runs = ctl.counters["layout_runs"]
    parts["row"].resize(300, 39)
    env.pump(50)
    c("callbacks.layout_after_host_poisoning", ctl.counters["layout_runs"] > runs
      and not button.isHidden() and rect(button)[0] == 47, rect(button))
    parts["row"].resize(479, 39)
    env.pump(50)
    c("callbacks.relayout_visible", not button.isHidden() and rect(button)[0] == 47, rect(button))
    button.click()
    env.pump(20)
    c("callbacks.click_launches", [r[0] for r in sys._ql_cpm_record] == ["start"], sys._ql_cpm_record)


def scenario_bootstrap_refusals(env, c):
    QtCore = env.QtCore
    env.make_main()
    env.make_editor()
    # Unreadable implementation: refused, nothing registered.
    original = _read(env.impl_path)
    os.remove(env.impl_path)
    env.autoinit()
    c("missing_impl.refused", env.console.count("code=installed-unreadable") == 1 and env.module() is None)
    # Load failure: entry removed; a repaired file then loads.
    env.write(env.impl_path, original + b"\nraise RuntimeError('broken install')\n")
    env.autoinit()
    c("load_failure.entry_removed", env.module() is None and env.console.count("entry_removed=True") == 1)
    c("load_failure.no_controller", not [o for o in env.app.children() if o.objectName() == CONTROLLER_NAME])
    env.write(env.impl_path, original)
    env.autoinit()
    module, ctl = env.module(), env.ctl()
    c("repaired.loads", module is not None and ctl is not None and ctl.state == "ATTACHED")
    env.pump(30)
    # Changed installed bytes: refused, the running controller is untouched.
    env.write(env.impl_path, original + b"\n# changed\n")
    env.autoinit()
    c("changed_impl.refused", env.console.count("code=installed-build-changed") == 1)
    c("changed_impl.controller_untouched", env.module() is module and env.ctl() is ctl and ctl.state == "ATTACHED")
    env.write(env.impl_path, original)
    # LOADING state and malformed controller slot: refused, untouched.
    module.__chadchan3d_cpm_ase_state__ = "loading"
    env.autoinit()
    c("loading_state.refused", env.console.count("code=module-loading") == 1
      and module.__chadchan3d_cpm_ase_state__ == "loading")
    module.__chadchan3d_cpm_ase_state__ = "ready"
    module._CONTROLLER = "not a controller"
    env.autoinit()
    c("malformed_slot.refused", env.console.count("outcome=controller-malformed") == 1
      and module._CONTROLLER == "not a controller")
    module._CONTROLLER = ctl
    env.autoinit()
    c("restored_slot.refresh", env.console.count("outcome=refreshed:ATTACHED") == 1)
    c("buttons.one", len(env.named(BUTTON_NAME)) == 1)


def scenario_foreign_module(env, c):
    env.make_main()
    env.make_editor()
    foreign = types.ModuleType(MODULE_KEY)
    sys.modules[MODULE_KEY] = foreign
    env.autoinit()
    c("foreign_module.refused", env.console.count("code=module-incompatible") == 1)
    c("foreign_module.untouched", sys.modules.get(MODULE_KEY) is foreign and not hasattr(foreign, "_CONTROLLER"))
    c("foreign_module.no_button", not env.named(BUTTON_NAME))


def scenario_geometry(env, c):
    QtCore, QtGui = env.QtCore, env.QtGui
    env.make_main()
    parts = env.make_editor()
    row, add, tools = parts["row"], parts["add"], parts["tools"]
    env.autoinit()
    env.pump(50)
    ctl = env.ctl()
    button = env.named(BUTTON_NAME)[0]
    c("native.position", rect(button) == [47, 1, 40, 32], rect(button))
    c("native.visible", button.isVisible())
    c("native.text_tooltip", button.text() == "CPM" and button.toolTip() == "Open Character Preset Manager"
      and button.accessibleName() == "Open Character Preset Manager")
    c("native.plain_tool_button", type(button) is QtGui.QToolButton and button.parentWidget() is row)
    c("native.not_clipped", button.width() >= max(40, button.sizeHint().width()))
    c("native.add_tools_unchanged", rect(add) == [2, 1, 40, 32] and rect(tools) == [437, 1, 40, 32]
      and not add.isHidden() and not tools.isHidden())

    def extended(lefts, right_group=True, width=479):
        made = []
        for i, x in enumerate(lefts):
            b = QtGui.QToolButton(row)
            b.setObjectName("toolbutton_ext%d" % i)
            b.setGeometry(x, 1, 32 if i else 40, 32)
            b.show()
            made.append(b)
        if right_group:
            for name, offset in (("toolbutton_paste", 79), ("toolbutton_gear", 42)):
                b = QtGui.QToolButton(row)
                b.setObjectName(name)
                b.setGeometry(width - offset, 1, 37, 32)
                b.show()
                made.append(b)
        return made

    # Extended-like configuration, owner settings: left cluster ends at 189.
    tools.hide()
    ext = extended([1, 43, 79, 115, 157], True)
    env.pump(50)
    ok, gap = clear_of_siblings(row, button)
    c("owner_settings.after_cluster", rect(button)[0] == 194 and button.isVisible(), rect(button))
    c("owner_settings.clearance", ok, gap)
    # All buttons shown: cluster ends at 271.
    more = []
    for i, x in enumerate([187, 223]):
        b = QtGui.QToolButton(row)
        b.setObjectName("toolbutton_more%d" % i)
        b.setGeometry(x, 1, 32, 32)
        b.show()
        more.append(b)
    # A 32-px button from 223 ends at 255; add one more ending at 271.
    b = QtGui.QToolButton(row)
    b.setObjectName("toolbutton_more_last")
    b.setGeometry(239, 1, 32, 32)
    b.show()
    more.append(b)
    env.pump(50)
    ok, gap = clear_of_siblings(row, button)
    c("all_shown.after_cluster", rect(button)[0] == 276 and button.isVisible(), rect(button))
    c("all_shown.clearance", ok, gap)
    foreign_before = snapshot(row, button)

    # Narrow: the right group follows the edge (as Extended does) -> hidden.
    row.resize(316, 39)
    ext[-2].move(316 - 79, 1)
    ext[-1].move(316 - 42, 1)
    tools.move(316 - 42, 1)
    expected_after_narrow = snapshot(row, button)
    env.pump(50)
    c("narrow.hidden", button.isHidden(), rect(button))
    c("narrow.foreign_untouched", snapshot(row, button) == expected_after_narrow)
    # Widen: returns.
    row.resize(479, 39)
    ext[-2].move(400, 1)
    ext[-1].move(437, 1)
    tools.move(437, 1)
    env.pump(50)
    c("widen.restored", not button.isHidden() and rect(button)[0] == 276, rect(button))
    c("widen.foreign_untouched", snapshot(row, button) == foreign_before)

    # Hidden controls do not reserve space.
    for b in more:
        b.hide()
    env.pump(50)
    c("hidden_siblings.free_space", rect(button)[0] == 194, rect(button))
    for b in more:
        b.show()
    env.pump(50)
    c("shown_siblings.reoccupied", rect(button)[0] == 276, rect(button))

    # Native Add hidden (Extended "+" off): still placed, Add untouched.
    add.hide()
    env.pump(50)
    c("add_hidden.placed", not button.isHidden() and clear_of_siblings(row, button)[0])
    c("add_hidden.add_untouched", add.isHidden() and rect(add) == [2, 1, 40, 32])
    add.show()
    env.pump(50)

    # Out-of-band widget and child popup window are not occupied space.
    low = QtGui.QWidget(row)
    low.setGeometry(0, 34, 479, 5)
    low.show()
    popup = QtGui.QWidget(row, QtCore.Qt.Popup)
    popup.setGeometry(270, 1, 120, 32)
    popup.show()
    env.pump(50)
    c("out_of_band_and_popup.ignored", rect(button)[0] == 276 and not button.isHidden(), rect(button))
    popup.deleteLater()
    low.deleteLater()
    env.flush()

    # A full-width foreign control in the band: hide; removed: return.
    wall = QtGui.QLabel("x", row)
    wall.setGeometry(0, 0, 479, 39)
    wall.show()
    env.pump(50)
    c("wall.hidden", button.isHidden())
    c("wall.untouched", rect(wall) == [0, 0, 479, 39] and not wall.isHidden())
    wall.deleteLater()
    env.flush()
    c("wall_removed.restored", not button.isHidden() and rect(button)[0] == 276, rect(button))

    # Ancestor visibility is not explicit visibility.
    pos = rect(button)
    parts["editor"].hide()
    env.pump(50)
    c("editor_hidden.button_not_hidden", not button.isHidden() and rect(button) == pos)
    parts["editor"].show()
    env.pump(50)
    c("editor_shown.same_place", not button.isHidden() and rect(button) == pos)

    # No runaway relayout once settled.
    runs = ctl.counters["layout_runs"]
    env.pump(600)
    c("settled.no_runaway_layout", ctl.counters["layout_runs"] == runs, ctl.counters["layout_runs"] - runs)
    c("settled.one_button", len(env.named(BUTTON_NAME)) == 1)


def scenario_lifecycle(env, c):
    QtCore = env.QtCore
    env.make_main()
    env.autoinit()
    ctl = env.ctl()
    c("start_absent.waiting", ctl.state == "WAITING" and ctl._discovery.isActive())
    c("start_absent.no_button", not env.named(BUTTON_NAME))
    c("start_absent.quiet", env.console.count("[ChadChan3D CPM Quick Launch] ") == 0)
    quit_receivers = env.app.receivers(QtCore.SIGNAL("aboutToQuit()"))
    ticks = ctl.counters["discovery_ticks"]
    env.pump(3500)
    c("waiting.ticks_about_1hz", 2 <= ctl.counters["discovery_ticks"] - ticks <= 4,
      ctl.counters["discovery_ticks"] - ticks)
    c("waiting.no_output_per_tick", env.console.count("[ChadChan3D CPM Quick Launch] ") == 0)

    cycles = []
    for cycle in range(10):
        ticks = ctl.counters["discovery_ticks"]
        parts = env.make_editor()
        env.pump(2100)
        attached = ctl.state == "ATTACHED" and len(env.named(BUTTON_NAME)) == 1
        restore_ticks = ctl.counters["discovery_ticks"] - ticks
        button = env.named(BUTTON_NAME)
        placed = bool(button) and rect(button[0]) == [47, 1, 40, 32] and button[0].isVisible()
        watched = len(ctl._watched)
        env.close_editor(parts["editor"])
        waiting_now = ctl.state == "WAITING" and ctl._discovery.isActive() and ctl._editor is None \
            and ctl._row is None
        env.pump(1100)
        # The dead button reference is released on the next discovery tick.
        waiting_now = waiting_now and ctl._button is None
        cycles.append({
            "attached": attached, "placed": placed, "restore_ticks": restore_ticks, "watched": watched,
            "waiting_after_close": waiting_now, "buttons_after_close": len(env.named(BUTTON_NAME)),
            "graveyard": len(ctl._graveyard) + len(ctl._graveyard_connections),
            "timers": len(timers(ctl, QtCore)),
            "quit_receivers": env.app.receivers(QtCore.SIGNAL("aboutToQuit()")),
        })
    c("cycles.attached_each_time", all(x["attached"] and x["placed"] for x in cycles), cycles)
    c("cycles.restored_within_two_ticks", all(x["restore_ticks"] <= 2 for x in cycles),
      [x["restore_ticks"] for x in cycles])
    c("cycles.waiting_after_close", all(x["waiting_after_close"] for x in cycles))
    c("cycles.no_button_after_close", all(x["buttons_after_close"] == 0 for x in cycles))
    c("cycles.graveyard_purged", all(x["graveyard"] == 0 for x in cycles), [x["graveyard"] for x in cycles])
    c("cycles.bounded_resources", len(set((x["watched"], x["timers"], x["quit_receivers"]) for x in cycles)) == 1
      and cycles[0]["timers"] == 2 and cycles[0]["quit_receivers"] == quit_receivers,
      [(x["watched"], x["timers"], x["quit_receivers"]) for x in cycles])
    c("cycles.attachments_counted", ctl.counters["attachments"] == 10, ctl.counters["attachments"])

    # Row lost while the editor survives: back to WAITING (quietly, still
    # polling), then automatic reattachment when a complete toolbar appears.
    parts = env.make_editor()
    env.pump(2100)
    c("row_loss.attached_first", ctl.state == "ATTACHED")
    parts["row"].deleteLater()
    env.flush()
    c("row_loss.waiting", ctl.state == "WAITING" and ctl._discovery.isActive())
    env.pump(2200)
    c("row_loss.still_waiting_quietly", ctl.state == "WAITING" and ctl._discovery.isActive()
      and env.console.count("isn't supported") == 0, ctl.state)
    events = ctl.counters["filter_events"]
    parts["editor"].resize(400, 900)
    parts["editor"].resize(479, 935)
    c("row_loss.editor_filter_removed", ctl.counters["filter_events"] == events,
      ctl.counters["filter_events"] - events)
    bar = CQEditorUpperBarWidget(parts["editor"])
    bar.setGeometry(0, 2, 479, 39)
    plus = CQTabbedToolButton(bar)
    plus.setToolTip("Add")
    plus.setGeometry(2, 1, 40, 32)
    bar.show()
    plus.show()
    ticks = ctl.counters["discovery_ticks"]
    env.pump(2100)
    c("row_loss.reattached_without_rerun", ctl.state == "ATTACHED" and ctl._row is bar
      and len(env.named(BUTTON_NAME)) == 1 and ctl.counters["discovery_ticks"] - ticks <= 2
      and not ctl._discovery.isActive())
    env.close_editor(parts["editor"])
    env.pump(1100)

    # Ambiguous: two editors -> WAITING, nothing injected; once one remains,
    # it is attached automatically.
    first = env.make_editor()
    second = env.make_editor()
    env.pump(1200)
    c("two_editors.waiting_no_injection", ctl.state == "WAITING" and ctl._discovery.isActive()
      and not env.named(BUTTON_NAME), ctl.state)
    env.close_editor(second["editor"])
    env.pump(1200)
    c("two_editors.one_left_attached", ctl.state == "ATTACHED" and ctl._editor is first["editor"]
      and len(env.named(BUTTON_NAME)) == 1)
    env.close_editor(first["editor"])
    env.pump(1100)
    # Positively unsupported: a row with a layout manager -> SUSPENDED, once.
    with_layout = env.make_editor(layout=True)
    env.pump(1200)
    c("row_with_layout.suspended", ctl.state == "SUSPENDED" and ctl.suspend_reason == "unsupported"
      and not env.named(BUTTON_NAME))
    c("row_with_layout.one_actionable_diagnostic", env.console.count("isn't supported") == 1
      and env.console.count("from the Scripts menu") >= 1)
    ticks = ctl.counters["discovery_ticks"]
    env.pump(2200)
    c("row_with_layout.no_retry_storm", ctl.counters["discovery_ticks"] == ticks and not ctl._discovery.isActive())
    env.close_editor(with_layout["editor"])
    env.autoinit()
    c("row_with_layout.rerun_waits", ctl.state == "WAITING")

    # Shutdown while waiting.
    env.autoinit()
    c("shutdown_waiting.precondition", ctl.state == "WAITING")
    env.app.aboutToQuit.emit()
    c("shutdown_waiting.stopped", ctl.state == "STOPPED" and not ctl._discovery.isActive()
      and not ctl._layout.isActive())
    c("shutdown_waiting.quit_disconnected",
      env.app.receivers(QtCore.SIGNAL("aboutToQuit()")) == quit_receivers - 1)
    ctl.stop()
    c("shutdown.idempotent", ctl.state == "STOPPED")
    env.autoinit()
    c("after_stop.no_restart", env.console.count("outcome=stopped") == 1 and ctl.state == "STOPPED")


def scenario_shutdown_attached(env, c):
    QtCore = env.QtCore
    env.make_main()
    parts = env.make_editor()
    env.autoinit()
    env.pump(50)
    ctl = env.ctl()
    os.remove(env.launcher_path)
    env.named(BUTTON_NAME)[0].click()
    notice = ctl._notice
    c("precondition.attached_with_notice", ctl.state == "ATTACHED" and notice is not None and notice.isVisible())
    env.app.aboutToQuit.emit()
    env.flush()
    c("stopped", ctl.state == "STOPPED")
    c("timers_stopped", not ctl._discovery.isActive() and not ctl._layout.isActive())
    c("own_button_released", not env.named(BUTTON_NAME))
    c("notice_closed", not env.shiboken.isValid(notice) or not notice.isVisible())
    events = ctl.counters["filter_events"]
    parts["row"].resize(300, 39)
    parts["editor"].resize(400, 900)
    c("filters_removed", ctl.counters["filter_events"] == events)
    c("foreign_untouched", rect(parts["add"]) == [2, 1, 40, 32] and env.shiboken.isValid(parts["tools"]))
    c("cpm_not_closed_or_loaded", CPM_MODULE_KEY not in sys.modules)


def scenario_ownership(env, c):
    QtCore, QtGui = env.QtCore, env.QtGui
    env.make_main()
    parts = env.make_editor()
    row = parts["row"]
    foreign = QtGui.QToolButton(row)
    foreign.setObjectName(BUTTON_NAME)
    foreign.setText("other")
    foreign.setGeometry(100, 1, 40, 32)
    foreign.show()
    elsewhere = QtGui.QPushButton(env.main)
    elsewhere.setObjectName(BUTTON_NAME)
    elsewhere.setGeometry(600, 600, 50, 20)
    elsewhere.show()
    env.autoinit()
    env.pump(50)
    ctl = env.ctl()
    c("foreign_in_row.untouched", env.shiboken.isValid(foreign) and rect(foreign) == [100, 1, 40, 32]
      and foreign.isVisible() and foreign.text() == "other")
    c("foreign_in_row.not_duplicated", ctl._button is None and len(env.named(BUTTON_NAME)) == 2)
    c("foreign_in_row.one_diagnostic", env.console.count("already in the toolbar") == 1)
    foreign.deleteLater()
    env.flush()
    env.pump(50)
    own = ctl._button
    c("foreign_removed.own_created", own is not None and own.isVisible() and rect(own)[0] == 47, own and rect(own))
    c("elsewhere.untouched", env.shiboken.isValid(elsewhere) and rect(elsewhere) == [600, 600, 50, 20])

    # External deletion of the owned button: recreated, bounded.
    created = ctl.counters["buttons_created"]
    for _ in range(3):
        ctl._button.deleteLater()
        env.flush()
        env.pump(50)
    c("deleted_owned.recreated", ctl._button is not None and env.shiboken.isValid(ctl._button)
      and ctl._button.isVisible() and ctl.counters["buttons_created"] == created + 3)
    ctl._button.deleteLater()
    env.flush()
    env.pump(50)
    runs = ctl.counters["layout_runs"]
    env.pump(500)
    c("deleted_owned.limit_stops_recreation", ctl._button is None
      and ctl.counters["buttons_created"] == created + 3)
    c("deleted_owned.limit_one_diagnostic", env.console.count("removed from the Animation Set Editor toolbar repeatedly") == 1
      and env.console.count("from the Scripts menu, or run ChadChan3D_CPM_ASE_Button again") == 1)
    c("deleted_owned.no_storm", ctl.counters["layout_runs"] == runs)
    c("deleted_owned.still_attached", ctl.state == "ATTACHED")


def scenario_init_failure(env, c):
    QtCore = env.QtCore
    env.make_main()
    env.make_editor()
    quit_receivers = env.app.receivers(QtCore.SIGNAL("aboutToQuit()"))
    # Fault-injected deployment: a malformed discovery interval makes the
    # controller constructor fail after its first timer exists.
    impl = _read(env.impl_path)
    env.write(env.impl_path, impl.replace(b"DISCOVERY_INTERVAL_MS = 1000", b"DISCOVERY_INTERVAL_MS = 'malformed'"))
    env.autoinit()
    env.flush()
    module = env.module()
    c("partial_init.reported", env.console.count("outcome=init-failed") == 1)
    c("partial_init.cleaned_up", not [o for o in env.app.children() if o.objectName() == CONTROLLER_NAME])
    c("partial_init.quit_receivers_restored", env.app.receivers(QtCore.SIGNAL("aboutToQuit()")) == quit_receivers)
    c("partial_init.no_restart_flag", module._RESTART_REQUIRED is False and module._CONTROLLER is None)
    module.DISCOVERY_INTERVAL_MS = 1000
    env.autoinit()
    env.pump(50)
    c("partial_init.manual_rerun_starts", module._CONTROLLER is not None
      and module._CONTROLLER.state == "ATTACHED" and len(env.named(BUTTON_NAME)) == 1)
    # Cleanup that cannot be demonstrated -> restart required, no further start.
    old = module._CONTROLLER
    old.stop()
    old.setParent(None)
    old.deleteLater()
    env.flush()
    module._CONTROLLER = None
    original_dispose = module.QuickLaunchController.dispose_partial
    module.QuickLaunchController.dispose_partial = lambda self: False
    module.DISCOVERY_INTERVAL_MS = "malformed"
    env.autoinit()
    module.QuickLaunchController.dispose_partial = original_dispose
    module.DISCOVERY_INTERVAL_MS = 1000
    c("undemonstrated_cleanup.restart_flag", module._RESTART_REQUIRED is True)
    env.autoinit()
    c("undemonstrated_cleanup.refuses", env.console.count("outcome=restart-required") == 1
      and module._CONTROLLER is None)


def scenario_failure_cleanup(env, c):
    QtCore = env.QtCore
    env.make_main()
    parts = env.make_editor()
    env.autoinit()
    env.pump(50)
    module, ctl = env.module(), env.ctl()
    c("precondition.attached", ctl.state == "ATTACHED" and len(env.named(BUTTON_NAME)) == 1)

    def boom(*args, **kwargs):
        raise RuntimeError("injected layout fault")
    module.find_free_slot = boom
    parts["row"].resize(470, 39)
    env.pump(50)
    env.flush()
    c("layout_fault.suspended_failed", ctl.state == "SUSPENDED" and ctl.suspend_reason == "failed")
    c("layout_fault.one_diagnostic", env.console.count("stopped after an unexpected error") == 1)
    c("layout_fault.timers_stopped", not ctl._discovery.isActive() and not ctl._layout.isActive())
    c("layout_fault.own_button_released", not env.named(BUTTON_NAME))
    events, runs, ticks = ctl.counters["filter_events"], ctl.counters["layout_runs"], ctl.counters["discovery_ticks"]
    parts["row"].resize(479, 39)
    parts["editor"].resize(400, 900)
    env.pump(2200)
    c("layout_fault.filters_removed", ctl.counters["filter_events"] == events)
    c("layout_fault.no_retry", ctl.counters["layout_runs"] == runs and ctl.counters["discovery_ticks"] == ticks)
    env.autoinit()
    c("layout_fault.rerun_requires_restart", env.console.count("outcome=restart-required") == 1
      and ctl.state == "SUSPENDED" and not env.named(BUTTON_NAME))
    c("layout_fault.foreign_untouched", rect(parts["add"]) == [2, 1, 40, 32] and rect(parts["tools"]) == [437, 1, 40, 32])


def scenario_filter_failure(env, c):
    env.make_main()
    parts = env.make_editor()
    env.autoinit()
    env.pump(50)
    module, ctl = env.module(), env.ctl()

    class Boom(object):
        def __contains__(self, item):
            raise RuntimeError("injected filter fault")
    module._WATCHED_EVENT_TYPES = Boom()
    parts["row"].resize(470, 39)
    c("filter_fault.event_still_delivered", parts["row"].width() == 470)
    env.pump(50)
    env.flush()
    c("filter_fault.suspended_failed", ctl.state == "SUSPENDED" and ctl.suspend_reason == "failed")
    c("filter_fault.one_diagnostic", env.console.count("stopped after an unexpected error (event filter)") == 1)
    c("filter_fault.own_button_released", not env.named(BUTTON_NAME))


def scenario_launch(env, c):
    QtCore, QtGui = env.QtCore, env.QtGui
    env.make_main()
    env.make_editor()
    env.autoinit()
    env.pump(1200)
    ctl = env.ctl()
    button = env.named(BUTTON_NAME)[0]
    c("before_click.cpm_not_loaded", CPM_MODULE_KEY not in sys.modules)
    button.click()
    record = sys._ql_cpm_record
    c("click.r15_loads_and_starts", [r[0] for r in record] == ["start"] and CPM_MODULE_KEY in sys.modules
      and sys.modules[CPM_MODULE_KEY].__dict__.get("__chadchan3d_cpm_state__") == "ready", record)
    cpm_module = sys.modules.get(CPM_MODULE_KEY)
    button.click()
    env.scripts_menu()
    button.click()
    c("repeat.reuses_one_module", [r[0] for r in record] == ["start"] * 4
      and sys.modules.get(CPM_MODULE_KEY) is cpm_module and len(set(r[1] for r in record)) == 1, record)
    c("repeat.no_quick_launch_notice", ctl._notice is None)

    # R15 remains the decision-maker: a changed CPM build is refused by R15.
    stub = _read(env.cpm_path)
    env.write(env.cpm_path, stub + b"\n# changed\n")
    button.click()
    c("r15_refusal.routed", record[-1] == ["refusal", "installed-build-changed"] and len(record) == 5, record)
    r15_notice = getattr(env.app, R15_NOTICE_ATTR, None)
    c("r15_refusal.r15_notice_only", r15_notice is not None and r15_notice.isVisible() and ctl._notice is None)
    if r15_notice is not None:
        r15_notice.close()
    env.write(env.cpm_path, stub)

    # Missing launcher: one controller-owned, reused, non-modal notice.
    launcher = _read(env.launcher_path)
    os.remove(env.launcher_path)
    button.click()
    notice = ctl._notice
    c("missing_launcher.notice", notice is not None and notice.isVisible() and notice.text() == LAUNCH_FAILED_TEXT
      and notice.objectName() == NOTICE_NAME and not notice.isModal()
      and notice.windowModality() == QtCore.Qt.NonModal, notice and notice.text())
    c("missing_launcher.console", env.console.count("launcher could not be read") == 1)
    notice.close()
    button.click()
    c("missing_launcher.notice_reused", ctl._notice is notice and notice.isVisible()
      and len([w for w in QtGui.QApplication.topLevelWidgets() if w.objectName() == NOTICE_NAME]) == 1)
    notice.close()
    c("missing_launcher.no_retry", len(record) == 5 and ctl.counters["launches"] == 6, ctl.counters["launches"])

    # Active foreign modal: no notice over it, none queued afterwards.
    modal = QtGui.QDialog()
    modal.setModal(True)
    modal.show()
    modal_active = QtGui.QApplication.activeModalWidget() is modal
    button.click()
    c("modal.suppressed", modal_active and not notice.isVisible()
      and env.console.count("notice suppressed (a modal dialog is active)") == 1, modal_active)
    modal.close()
    env.pump(100)
    c("modal.no_surprise_popup", not notice.isVisible())

    # Fresh execution dictionary per click.
    env.write(env.launcher_path, b"import sys as _s\n"
              b"_s._ql_ns.append([globals(), sorted(globals().keys()), globals() is locals(),"
              b" globals().get('__file__'), globals().get('__name__')])\n")
    sys._ql_ns = []
    button.click()
    button.click()
    # The probe itself retains each dictionary so identity can be compared;
    # ids alone are unreliable once Quick Launch has discarded a dictionary.
    first, second = sys._ql_ns
    module_dict = env.module().__dict__
    c("fresh_dict.distinct", first[0] is not second[0] and first[0] is not module_dict
      and first[0] is not env.host and second[0] is not module_dict)
    first[0] = second[0] = None
    c("fresh_dict.globals_is_locals", first[2] and second[2])
    c("fresh_dict.metadata", first[3] == env.launcher_path and first[4] == "__main__"
      and first[1] == sorted(["__builtins__", "__doc__", "__file__", "__name__", "__package__", "_s"]), first)

    # Reentrant click during a launch is ignored, not queued.
    env.write(env.launcher_path, b"import sys as _s\n"
              b"_s._ql_exec = getattr(_s, '_ql_exec', 0) + 1\n"
              b"_s._ql_button.click()\n")
    sys._ql_button = button
    button.click()
    env.pump(50)
    c("reentry.ignored", sys._ql_exec == 1 and env.console.count("already opening; click ignored") == 1,
      getattr(sys, "_ql_exec", None))

    # A launcher that raises: one notice, no retry.
    env.write(env.launcher_path, b"import sys as _s\n_s._ql_raise = getattr(_s, '_ql_raise', 0) + 1\n"
              b"raise RuntimeError('launcher fault')\n")
    button.click()
    env.pump(50)
    c("launcher_raises.notice_no_retry", sys._ql_raise == 1 and notice.isVisible()
      and env.console.count("launcher raised") == 1)
    notice.close()
    env.write(env.launcher_path, b"def broken(:\n")
    button.click()
    c("launcher_syntax_error.notice", notice.isVisible() and env.console.count("launcher raised") == 2)
    notice.close()
    env.write(env.launcher_path, launcher)
    button.click()
    c("restored_launcher.works", [r[0] for r in record][-1] == "start")
    c("controller_still_attached", ctl.state == "ATTACHED")


def scenario_recreation_policy(env, c):
    QtCore, QtGui = env.QtCore, env.QtGui
    env.make_main()
    parts = env.make_editor()
    row = parts["row"]
    env.autoinit()
    env.pump(50)
    ctl = env.ctl()
    base = ctl.counters["buttons_created"]
    exhausted = "removed from the Animation Set Editor toolbar repeatedly"

    def created():
        return ctl.counters["buttons_created"] - base

    def kill():
        ctl._button.deleteLater()
        env.flush()
        env.pump(50)

    # CPM's own creation, removal, geometry and visibility never rearm.
    kill()
    kill()
    row.resize(80, 39)
    env.pump(50)
    hidden_when_narrow = ctl._button.isHidden()
    row.resize(479, 39)
    parts["tools"].move(430, 1)
    parts["tools"].move(437, 1)
    env.pump(50)
    c("own_events.no_rearm", hidden_when_narrow and not ctl._button.isHidden() and ctl._recreations == 2
      and created() == 2, (hidden_when_narrow, ctl._recreations, created()))
    kill()
    kill()
    c("unchanged.bounded_at_three", ctl._button is None and created() == 3 and not env.named(BUTTON_NAME),
      created())
    c("unchanged.one_actionable_message", env.console.count(exhausted) == 1
      and env.console.count("from the Scripts menu, or run ChadChan3D_CPM_ASE_Button again") == 1)
    row.resize(470, 39)
    row.resize(479, 39)
    parts["tools"].hide()
    parts["tools"].show()
    parts["tools"].raise_()
    env.pump(100)
    runs = ctl.counters["layout_runs"]
    env.pump(500)
    c("unchanged.geometry_visibility_zorder_no_rearm", ctl._button is None and created() == 3)
    c("unchanged.no_storm", ctl.counters["layout_runs"] == runs and not ctl._discovery.isActive())
    c("unchanged.no_lockout_state", ctl.state == "ATTACHED" and ctl.suspend_reason is None)

    # A genuine change to the non-CPM toolbar children rearms the full budget.
    ext = QtGui.QToolButton(row)
    ext.setObjectName("toolbutton_ext")
    ext.setGeometry(150, 1, 32, 32)
    ext.show()
    env.pump(50)
    c("structure_change.recovered", ctl._button is not None and ctl._button.isVisible() and created() == 4
      and clear_of_siblings(row, ctl._button)[0], created())
    kill()
    kill()
    kill()
    c("structure_change.full_budget", ctl._button is not None and created() == 7, created())
    kill()
    c("structure_change.bounded_again", ctl._button is None and created() == 7
      and env.console.count(exhausted) == 2)

    # An explicit Autoinit refresh rearms.
    env.autoinit()
    env.pump(50)
    c("refresh.recovered", ctl._button is not None and ctl._button.isVisible() and created() == 8
      and len(env.named(BUTTON_NAME)) == 1, created())

    # A still-valid owned button moved elsewhere stays owned: no duplicate,
    # never moved back or deleted.
    own = ctl._button
    own.setParent(env.main)
    own.setGeometry(700, 700, 40, 32)
    own.show()
    env.pump(50)
    c("reparented.no_duplicate", ctl._button is own and created() == 8 and len(env.named(BUTTON_NAME)) == 1)
    c("reparented.not_moved_or_deleted", env.shiboken.isValid(own) and own.parentWidget() is env.main
      and rect(own) == [700, 700, 40, 32] and own.isVisible())
    c("reparented.one_message", env.console.count("moved out of the toolbar") == 1)
    env.autoinit()
    env.pump(50)
    c("reparented.refresh_no_duplicate", created() == 8 and len(env.named(BUTTON_NAME)) == 1
      and own.parentWidget() is env.main)
    env.close_editor(parts["editor"])
    parts = env.make_editor()
    env.pump(2100)
    c("reparented.new_toolbar_no_duplicate", ctl.state == "ATTACHED" and ctl._button is own and created() == 8
      and len(env.named(BUTTON_NAME)) == 1 and rect(own) == [700, 700, 40, 32])
    own.setParent(parts["row"])
    own.show()
    env.pump(50)
    c("reparented.returned_is_placed", own.parentWidget() is parts["row"] and rect(own)[0] == 47
      and own.isVisible() and created() == 8, rect(own))
    own.click()
    c("reparented.click_still_launches", [r[0] for r in sys._ql_cpm_record] == ["start"])
    own.setParent(env.main)
    env.pump(50)
    own.deleteLater()
    env.flush()
    env.pump(50)
    c("reparented_then_destroyed.recreated", ctl._button is not None and ctl._button.parentWidget() is parts["row"]
      and created() == 9 and len(env.named(BUTTON_NAME)) == 1, created())
    # Shutdown leaves a button that lives elsewhere in place, disconnected.
    moved = ctl._button
    moved.setParent(env.main)
    env.pump(50)
    env.app.aboutToQuit.emit()
    env.flush()
    moved.click()
    c("shutdown.elsewhere_button_untouched_and_disconnected", env.shiboken.isValid(moved)
      and moved.parentWidget() is env.main and [r[0] for r in sys._ql_cpm_record] == ["start"]
      and ctl.state == "STOPPED")


def scenario_delayed_construction(env, c):
    QtCore, QtGui = env.QtCore, env.QtGui
    env.make_main()
    env.autoinit()
    ctl = env.ctl()
    parts = env.make_editor(row=False)
    editor = parts["editor"]
    env.pump(1200)
    c("editor_without_toolbar.waiting", ctl.state == "WAITING" and ctl._discovery.isActive()
      and not env.named(BUTTON_NAME))
    bar = CQEditorUpperBarWidget(editor)
    bar.setGeometry(0, 2, 479, 39)
    tools = CQTabbedToolButton(bar)
    tools.setToolTip("Tools")
    tools.setGeometry(437, 1, 40, 32)
    bar.show()
    env.pump(1200)
    c("toolbar_without_add.waiting", ctl.state == "WAITING" and ctl._discovery.isActive()
      and not env.named(BUTTON_NAME))

    def add_button(row, x=2):
        plus = CQTabbedToolButton(row)
        plus.setToolTip("Add")
        plus.setGeometry(x, 1, 40, 32)
        plus.show()
        return plus

    plus = add_button(bar)
    ticks = ctl.counters["discovery_ticks"]
    env.pump(1200)
    c("add_appears.attached", ctl.state == "ATTACHED" and ctl._row is bar and len(env.named(BUTTON_NAME)) == 1
      and rect(ctl._button) == [47, 1, 40, 32] and ctl.counters["discovery_ticks"] - ticks <= 2)
    ticks = ctl.counters["discovery_ticks"]
    env.pump(2200)
    c("attached.polling_stopped", not ctl._discovery.isActive() and ctl.counters["discovery_ticks"] == ticks)
    c("delayed.quiet", env.console.count("[ChadChan3D CPM Quick Launch] ") == 0)

    # Required structure lost without destruction: detach to WAITING.
    plus.deleteLater()
    env.flush()
    env.flush()
    c("add_lost.waiting", ctl.state == "WAITING" and ctl._discovery.isActive() and ctl._row is None)
    c("add_lost.own_button_removed", not env.named(BUTTON_NAME) and ctl._button is None)
    events = ctl.counters["filter_events"]
    bar.resize(470, 39)
    bar.resize(479, 39)
    c("add_lost.filters_removed", ctl.counters["filter_events"] == events)
    plus = add_button(bar)
    env.pump(1200)
    c("add_returns.reattached", ctl.state == "ATTACHED" and len(env.named(BUTTON_NAME)) == 1)

    # Temporarily ambiguous candidates: wait, inject nothing, then recover.
    dup = add_button(bar, 300)
    env.pump(50)
    env.flush()
    c("two_add_candidates.waiting_no_injection", ctl.state == "WAITING" and not env.named(BUTTON_NAME))
    dup.deleteLater()
    env.flush()
    env.pump(1200)
    c("two_add_candidates.recovered", ctl.state == "ATTACHED" and len(env.named(BUTTON_NAME)) == 1)
    bar2 = CQEditorUpperBarWidget(editor)
    bar2.setGeometry(0, 50, 479, 39)
    bar2.show()
    env.pump(50)
    env.flush()
    c("two_toolbar_candidates.waiting_no_injection", ctl.state == "WAITING" and not env.named(BUTTON_NAME))
    bar2.deleteLater()
    env.flush()
    env.pump(1200)
    c("two_toolbar_candidates.recovered", ctl.state == "ATTACHED" and ctl._row is bar
      and len(env.named(BUTTON_NAME)) == 1)

    # Toolbar replacement: the old toolbar is destroyed, a new complete one appears.
    new_bar = CQEditorUpperBarWidget(editor)
    new_bar.setGeometry(0, 2, 479, 39)
    add_button(new_bar)
    bar.deleteLater()
    new_bar.show()
    env.flush()
    env.pump(1200)
    button = ctl._button
    c("replaced.attached_to_new", ctl.state == "ATTACHED" and ctl._row is new_bar
      and button is not None and button.parentWidget() is new_bar and len(env.named(BUTTON_NAME)) == 1)
    c("replaced.no_stale_references", not ctl._graveyard and not ctl._graveyard_connections
      and all(env.shiboken.isValid(o) for o in ctl._watched)
      and all(env.shiboken.isValid(o) and o.parentWidget() is new_bar for o in ctl._structure)
      and all(env.shiboken.isValid(src) for src, slot in ctl._connections))
    # Replacement while the old toolbar survives elsewhere.
    newest = CQEditorUpperBarWidget(editor)
    newest.setGeometry(0, 2, 479, 39)
    add_button(newest)
    newest.show()
    new_bar.setParent(env.main)
    env.flush()
    env.pump(1200)
    c("replaced_old_alive.attached_to_newest", ctl.state == "ATTACHED" and ctl._row is newest
      and len(env.named(BUTTON_NAME)) == 1 and ctl._button.parentWidget() is newest)
    events = ctl.counters["filter_events"]
    new_bar.resize(300, 39)
    c("replaced_old_alive.old_unwatched", ctl.counters["filter_events"] == events
      and not new_bar.findChildren(QtGui.QWidget, BUTTON_NAME))

    # Foreign widget renamed away from the reserved name: recovery follows
    # the next toolbar event (no extra polling).
    env.close_editor(editor)
    parts = env.make_editor()
    foreign = QtGui.QToolButton(parts["row"])
    foreign.setObjectName(BUTTON_NAME)
    foreign.setGeometry(100, 1, 40, 32)
    foreign.show()
    env.pump(1200)
    c("foreign.blocks_without_touching", ctl.state == "ATTACHED" and ctl._button is None
      and rect(foreign) == [100, 1, 40, 32])
    foreign.setObjectName("someone_else")
    env.pump(200)
    c("foreign_renamed.no_immediate_poll", ctl._button is None)
    parts["tools"].move(430, 1)
    env.pump(50)
    c("foreign_renamed.recovers_on_next_toolbar_event", ctl._button is not None and ctl._button.isVisible()
      and clear_of_siblings(parts["row"], ctl._button)[0] and rect(foreign) == [100, 1, 40, 32])
    module = env.module()
    c("no_lockout", module._RESTART_REQUIRED is False and ctl.suspend_reason is None)


SCENARIOS = [
    ("namespace", scenario_namespace),
    ("bootstrap_refusals", scenario_bootstrap_refusals),
    ("foreign_module", scenario_foreign_module),
    ("geometry", scenario_geometry),
    ("lifecycle", scenario_lifecycle),
    ("shutdown_attached", scenario_shutdown_attached),
    ("ownership", scenario_ownership),
    ("init_failure", scenario_init_failure),
    ("failure_cleanup", scenario_failure_cleanup),
    ("filter_failure", scenario_filter_failure),
    ("launch", scenario_launch),
    ("recreation_policy", scenario_recreation_policy),
    ("delayed_construction", scenario_delayed_construction),
]


def child_main(name, root):
    _qt_classes()
    records = []

    def c(cname, condition, value=None):
        records.append([cname, bool(condition), _jsonable(value)])

    env = Env(root)
    try:
        dict(SCENARIOS)[name](env, c)
    except Exception:
        import traceback
        records.append(["scenario_completed", False, traceback.format_exc()])
    errors = env.errors.joined()
    records.append(["no_unhandled_qt_callback_errors", "Traceback" not in errors
                    and "already deleted" not in errors, errors[-1500:]])
    sys.stdout = env.console.stream
    print("QL1_CHILD_RESULT " + json.dumps(records))
    sys.stdout.flush()
    os._exit(0)


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except Exception:
        return repr(value)


def run_children():
    if os.path.isdir(FIXTURE_ROOT):
        shutil.rmtree(FIXTURE_ROOT)
    os.makedirs(FIXTURE_ROOT)
    for name, _ in SCENARIOS:
        root = os.path.join(FIXTURE_ROOT, name)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.Popen([sys.executable, "-E", "-B", os.path.abspath(__file__),
                                 "--child=%s" % name, "--root=%s" % root],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        output = proc.communicate()[0].decode("utf-8", "replace")
        records = None
        for line in output.splitlines():
            if line.startswith("QL1_CHILD_RESULT "):
                records = json.loads(line[len("QL1_CHILD_RESULT "):])
        if records is None:
            check("%s.child_reported" % name, False, output[-2000:])
            continue
        for cname, ok, value in records:
            check("%s.%s" % (name, cname), ok, value)


def qt_available():
    try:
        out = subprocess.check_output([sys.executable, "-E", "-B", "-c", "from PySide import QtGui; print('ok')"],
                                      stderr=subprocess.STDOUT)
        return b"ok" in out
    except Exception:
        return False


def main():
    args = dict(a.split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    if "--child" in args:
        child_main(args["--child"], args["--root"])
        return
    phase = args.get("--phase")
    if phase not in ("run", "static"):
        print("usage: %s --phase=run|static" % os.path.basename(sys.argv[0]))
        sys.exit(2)
    print("Interpreter: %s" % sys.version.split()[0])
    static_checks()
    if phase == "run":
        if sys.version_info[:3] != (2, 7, 5) or not qt_available():
            check("run.requires_sfm_python_2_7_5_with_pyside", False, sys.version)
        else:
            run_children()
    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    if passed != len(RESULTS):
        sys.exit(1)


if __name__ == "__main__":
    main()
