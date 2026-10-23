# -*- coding: utf-8 -*-
"""CPM R15 -- offline qualification of the stable private-module launcher.

Authoritative design: cpm/qualification/R15_IMPLEMENTATION_BLUEPRINT.md (§11).

Unlike the Step 1-4 suites, nothing here is extracted: every scenario runs the
ACTUAL launcher (cpm/app/launcher/SFM_Character_Preset_Manager.py) against the
ACTUAL canonical application bytes (cpm/app/SFM_Character_Preset_Manager.py),
both deployed into a fake SFM game root, the way SFM's native ScriptController
runs a Scripts-menu file: compiled without future flags and executed with one
shared, process-lifetime host dictionary as globals and locals.

Each scenario runs in its own child interpreter (one child = one "SFM
process"). Stubs are limited to boundaries:
- sfmApp / vs: an empty current shot (no animation sets);
- the filesystem below C:\\Users (the bounded CPM log folder in Public
  Documents and the preset library in the user's Documents) is remapped into
  the fixture, so no real log or preset folder is touched;
- Qt: real PySide 1.2 / Qt 4.8 when importable (the embedded 2.7.5
  interpreter), and otherwise -- and additionally under 2.7.5 -- a behavioural
  Qt 4.8 model that reproduces QWidget::close / QDialog::closeEvent / reject /
  done / deleteLater / modal-stack semantics (not no-op fakes).

Python 2.7.5 is the production gate; 3.10 is compatibility evidence. Mocks do
not qualify real Qt deletion, SFM menu discovery or live coexistence: those
belong to the real-SFM Session 1 addendum.

Usage: --phase=run            (parent; runs every scenario in child processes)
       --child=<scenario> --qt=<real|model> --root=<dir>   (internal)
"""
from __future__ import print_function

import ast
import gc
import hashlib
import io
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

PY2 = sys.version_info[0] == 2
try:
    _TEXT = unicode  # noqa: F821
except NameError:
    _TEXT = str

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, os.pardir, os.pardir, os.pardir))
APP_PATH = os.path.join(_REPO_ROOT, "cpm", "app", "SFM_Character_Preset_Manager.py")
LAUNCHER_PATH = os.path.join(_REPO_ROOT, "cpm", "app", "launcher", "SFM_Character_Preset_Manager.py")
BASELINE_PATH = os.path.join(_REPO_ROOT, "cpm", "baseline", "SFM_CSP_G18AN_SaveNewCopy.py")
NORMALIZER_PATH = os.path.join(_REPO_ROOT, "audit_external_runtime", "Rebuild_Control_Groups_Normalizer.py")
FIXTURE_ROOT = os.path.join(tempfile.gettempdir(), "cpm_app_r15_fixture")

MODULE_KEY = "chadchan3d_cpm_app"
LOADER_MARKER = "cpm-private-loader-v1"
NOTICE_ATTR = "_chadchan3d_cpm_launch_notice_v1"
NOTICE_NAME = "chadchan3d_cpm_launch_notice_v1"
WINDOW_ATTR = "_sfm_character_slider_preset_tool_window"
CPM_LOG = "SFM_CSP_G18AN_SaveNewCopy.log"  # historical; never written by the corrected app
CPM_LOG_DIR = "SFM Character Preset Manager Logs"
G11A_LOG = "SFM_CSP_G11A_ProductionWindowBodyMatch.log"
NORMALIZER_LOG = "sfm_rebuild_control_groups.txt"

# Forbidden components (Blueprint §10): byte identities at 5d94dbf.
PINNED_RAW = {
    "cpm/baseline/SFM_CSP_G18AN_SaveNewCopy.py": "3326024ddecd544ad1e10659bbf7b98420b5f147fca775433878c19fd9e66b3e",
    "audit_external_runtime/Rebuild_Control_Groups_Normalizer.py": "1f4ec5a26605aa90380eb0532fec3915d2cc24a3a20473ed70d57198bd995db7",
    "cpm/convergence/cpm_authority_adapter.py": "e96e21b537b5892fc5c1139b2396bbf5e3ce48a521b45876035d78789f126607",
    "cpm/convergence/cpm_compat_v1_projection.py": "9b077a1baf491262901812620c380a45eeb9cb2bf75ddc28a08ab18612faffc1",
    "sfm_defaultanimationgroups.txt": "ac45e5c1cd45d55b3af95747c97d2f8e93eda4f4fe4fec63e97d62828c904d93",
}
PACKAGE_DIR = "tests/sidecar/qualification/candidate_b2c_correction6/sfm_master_authority_productionized"
# CRLF-normalized digest over the shared package's .py sources.
PACKAGE_DIGEST_PINNED = "97ec7baf8980411f06a61031fc215e978e80ed999196679a37ddc7bb6da73c28"
# R14 private-ctypes isolation: exact top-level text at 5d94dbf.
R14_TEXT_PINNED = "00b8288afa13bc345ede21a6c40efe2eeb898c475d3f99e2c38eb0b69107cc29"

RESULTS = []


def check(name, condition, value=None):
    RESULTS.append((name, bool(condition), value))
    print("[%s] %s" % ("PASS" if condition else "FAIL", name))
    if not condition and value is not None:
        print("      value: %r" % (value,))


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Top-level source extraction (Python 2.7 ast has no end_lineno)
# ---------------------------------------------------------------------------

def top_level_blocks(source_text):
    """name -> source text of each named top-level def/class/assign."""
    lines = source_text.split(u"\n")
    tree = ast.parse(source_text.encode("utf-8") if PY2 else source_text)
    out = {}
    body = tree.body
    for i, node in enumerate(body):
        start = node.lineno
        if getattr(node, "decorator_list", None):
            start = min([d.lineno for d in node.decorator_list] + [start])
        end = (body[i + 1].lineno - 1) if i + 1 < len(body) else len(lines)
        block = lines[start - 1:end]
        while block and (not block[-1].strip() or block[-1].lstrip().startswith(u"#")):
            block.pop()
        names = []
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        for n in names:
            out[n] = u"\n".join(block) + u"\n"
    return out, tree


# ===========================================================================
# Behavioural Qt 4.8 model (used where PySide is not importable, and also
# under 2.7.5 for parity). Semantics follow qwidget.cpp / qdialog.cpp 4.8.
# ===========================================================================

class _Enum(type):
    """Class-level attribute access yields a stable distinct int per name."""
    _registry = {}

    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if not name[:1].isupper():
            return _Stub()  # static Qt API call (e.g. QApplication.font())
        reg = _Enum._registry
        if name not in reg:
            reg[name] = 1 << (len(reg) % 60) if len(reg) < 60 else 1000003 + len(reg)
        return reg[name]


def _enum_class(name, bases=(object,), attrs=None):
    return _Enum(name, bases, dict(attrs or {}))


class _Stub(int):
    """Permissive stand-in for Qt return values and minor widgets whose
    behavior CPM construction does not depend on."""

    def __new__(cls, *args, **kwargs):
        return int.__new__(cls, 0)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Stub()

    def __call__(self, *args, **kwargs):
        return _Stub()

    def __iter__(self):
        return iter(())


class _Signal(object):
    def __init__(self):
        self.slots = []

    def connect(self, fn, *args):
        self.slots.append(fn)
        return True

    def disconnect(self, *args):
        self.slots = []

    def emit(self, *args):
        for fn in list(self.slots):
            fn(*args)


class _ModelApp(object):
    current = None

    def __init__(self):
        _ModelApp.current = self
        self.queue = []
        self.pending_delete = []
        self.timers = []
        self.modal_stack = []
        self.widgets = []

    def activeModalWidget(self):
        return self.modal_stack[-1] if self.modal_stack else None

    def topLevelWidgets(self):
        return [w for w in self.widgets if not w._model_deleted and w._model_parent is None]

    def thread(self):
        return None

    def settle(self, turns=6):
        for _ in range(turns):
            queue, self.queue = self.queue, []
            for fn in queue:
                fn()
            for timer in list(self.timers):
                owner = timer._model_parent
                if timer._active and not timer._model_deleted and not (owner is not None and owner._model_deleted):
                    timer.timeout.emit()
            pending, self.pending_delete = self.pending_delete, []
            for w in pending:
                w._model_delete()


def _qt_model_modules():
    Qt = _enum_class("Qt")
    # Every model class carries the enum metaclass (class-level Qt constants).
    _QtBase = _Enum("_QtBase", (object,), {})

    class QObject(_QtBase):
        def __init__(self, parent=None, *args, **kwargs):
            self._model_parent = parent
            self._model_deleted = False
            self._model_children = []
            self._model_name = u""
            if parent is not None and hasattr(parent, "_model_children"):
                parent._model_children.append(self)

        def setObjectName(self, name):
            self._model_name = name

        def objectName(self):
            return self._model_name

        def parent(self):
            return self._model_parent

        def deleteLater(self):
            _ModelApp.current.pending_delete.append(self)

        def _model_delete(self):
            if self._model_deleted:
                return
            self._model_deleted = True
            for child in list(self._model_children):
                if hasattr(child, "_model_delete"):
                    child._model_delete()
            if self in _ModelApp.current.modal_stack:
                _ModelApp.current.modal_stack.remove(self)

        def receivers(self, signal):
            return 0

        def blockSignals(self, flag):
            return False

        def __getattr__(self, name):
            # Qt API methods are camelCase; Python attributes use underscores.
            if name.startswith("__") or ("_" in name and name not in ("raise_", "exec_")):
                raise AttributeError(name)
            return _Stub()

    class QTimer(QObject):
        def __init__(self, parent=None):
            QObject.__init__(self, parent)
            self.timeout = _Signal()
            self._interval = 0
            self._active = False
            _ModelApp.current.timers.append(self)

        def setInterval(self, ms):
            self._interval = int(ms)

        def interval(self):
            return self._interval

        def setSingleShot(self, flag):
            pass

        def start(self, *args):
            self._active = True

        def stop(self):
            self._active = False

        def isActive(self):
            return self._active and not self._model_deleted

        @staticmethod
        def singleShot(ms, fn):
            _ModelApp.current.queue.append(fn)

    class QEvent(object):
        KeyPress = 6
        DeferredDelete = 52

        def __init__(self, *args):
            self._accepted = True

        def accept(self):
            self._accepted = True

        def ignore(self):
            self._accepted = False

        def isAccepted(self):
            return self._accepted

    class QCloseEvent(QEvent):
        pass

    class QKeyEvent(QEvent):
        def __init__(self, kind, key, modifiers=0, *args):
            QEvent.__init__(self)
            self._key = key

        def key(self):
            return self._key

        def modifiers(self):
            return 0

    class QWidget(QObject):
        def __init__(self, parent=None, *args, **kwargs):
            QObject.__init__(self, parent)
            self._model_visible = False
            self._model_closing = False
            self._model_attrs = {}
            self._model_modality = Qt.NonModal
            self._model_title = u""
            _ModelApp.current.widgets.append(self)

        def setAttribute(self, attr, on=True):
            self._model_attrs[attr] = bool(on)

        def testAttribute(self, attr):
            return self._model_attrs.get(attr, False)

        def setWindowTitle(self, title):
            self._model_title = title

        def windowTitle(self):
            return self._model_title

        def setWindowModality(self, modality):
            self._model_modality = modality

        def windowModality(self):
            return self._model_modality

        def isModal(self):
            return self._model_modality != Qt.NonModal

        def parentWidget(self):
            return self._model_parent

        def isAncestorOf(self, other):
            current = getattr(other, "_model_parent", None)
            while current is not None:
                if current is self:
                    return True
                current = getattr(current, "_model_parent", None)
            return False

        def findChildren(self, *args):
            return []

        def isVisible(self):
            return self._model_visible

        def isHidden(self):
            return not self._model_visible

        def setVisible(self, visible):
            app = _ModelApp.current
            self._model_visible = bool(visible)
            if visible and self._model_modality != Qt.NonModal and self not in app.modal_stack:
                app.modal_stack.append(self)
            if not visible and self in app.modal_stack:
                app.modal_stack.remove(self)

        def show(self):
            self.setVisible(True)

        def hide(self):
            self.setVisible(False)

        def raise_(self):
            pass

        def activateWindow(self):
            pass

        def closeEvent(self, event):
            event.accept()

        def keyPressEvent(self, event):
            event.ignore()

        def close(self):
            return self._model_close_helper(True)

        def _model_close_helper(self, send_event):
            # QWidgetPrivate::close_helper (Qt 4.8)
            if self._model_closing:
                return True
            self._model_closing = True
            if send_event:
                event = QCloseEvent()
                self.closeEvent(event)
                if not self._model_deleted and not event.isAccepted():
                    self._model_closing = False
                    return False
            if not self._model_deleted and not self.isHidden():
                self.hide()
            self._model_closing = False
            if self.testAttribute(Qt.WA_DeleteOnClose):
                self.setAttribute(Qt.WA_DeleteOnClose, False)
                self.deleteLater()
            return True

    class QDialog(QWidget):
        Accepted = 1
        Rejected = 0

        def __init__(self, parent=None, *args, **kwargs):
            QWidget.__init__(self, parent)
            self.finished = _Signal()
            self.accepted = _Signal()
            self.rejected = _Signal()
            self._model_result = None

        def setModal(self, modal):
            self.setWindowModality(Qt.ApplicationModal if modal else Qt.NonModal)

        def closeEvent(self, event):
            # QDialog::closeEvent (Qt 4.8): calls the VIRTUAL reject().
            if self.isVisible():
                self.reject()
                if not self._model_deleted and self.isVisible():
                    event.ignore()
            else:
                event.accept()

        def reject(self):
            self.done(QDialog.Rejected)

        def accept(self):
            self.done(QDialog.Accepted)

        def done(self, result):
            # QDialog::done (Qt 4.8): hide, then close_helper(CloseNoEvent).
            self.hide()
            self._model_result = result
            self._model_close_helper(False)
            self.finished.emit(result)
            (self.accepted if result == QDialog.Accepted else self.rejected).emit()

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape:
                self.reject()
            else:
                event.ignore()

    class QAbstractButton(QWidget):
        def __init__(self, *args, **kwargs):
            QWidget.__init__(self, None)
            self.clicked = _Signal()

        def click(self):
            self.clicked.emit()

    class QMessageBox(QDialog):
        Information = 1
        Warning = 2
        Ok = 1024

        def __init__(self, parent=None, *args):
            QDialog.__init__(self, parent)
            self._model_text = u""
            self._model_ok = QAbstractButton()
            self._model_ok.clicked.connect(lambda: QDialog.done(self, QMessageBox.Ok))
            self.buttonClicked = _Signal()

        def setText(self, text):
            self._model_text = text

        def text(self):
            return self._model_text

        def setIcon(self, icon):
            pass

        def setStandardButtons(self, buttons):
            pass

        def button(self, which):
            return self._model_ok

    class QComboBox(QWidget):
        def __init__(self, *args, **kwargs):
            QWidget.__init__(self, None)
            self._model_items = []
            self._model_index = -1
            self.currentIndexChanged = _Signal()
            self.activated = _Signal()

        def clear(self):
            self._model_items = []
            self._model_index = -1

        def addItem(self, *args):
            self._model_items.append(args)
            if self._model_index < 0:
                self._model_index = 0

        def count(self):
            return len(self._model_items)

        def currentIndex(self):
            return self._model_index

        def setCurrentIndex(self, index):
            self._model_index = int(index)

    class QApplication(QObject):
        def __init__(self, *args):
            QObject.__init__(self, None)

        @staticmethod
        def instance():
            return _ModelApp.current.qapp

        @staticmethod
        def activeWindow():
            return None

        @staticmethod
        def sendEvent(receiver, event):
            if isinstance(event, QKeyEvent):
                receiver.keyPressEvent(event)
            return True

        def activeModalWidget(self):
            return _ModelApp.current.activeModalWidget()

        def topLevelWidgets(self):
            return _ModelApp.current.topLevelWidgets()

        def processEvents(self, *args):
            _ModelApp.current.settle(1)

    class _GuiModule(types.ModuleType):
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            cls = _Enum(name, (QWidget,), {})
            setattr(self, name, cls)
            return cls

    qtcore = types.ModuleType("PySide.QtCore")
    qtcore.Qt = Qt
    qtcore.QObject = QObject
    qtcore.QTimer = QTimer
    qtcore.QEvent = QEvent
    qtcore.QCoreApplication = QApplication
    qtcore.QThread = _enum_class("QThread", (QObject,), {"currentThread": staticmethod(lambda: None)})
    qtcore.qVersion = lambda: "model-4.8"

    def _qt_core_getattr(name):
        raise AttributeError(name)
    qtgui = _GuiModule("PySide.QtGui")
    for cls in (QWidget, QDialog, QMessageBox, QComboBox, QAbstractButton, QKeyEvent, QCloseEvent, QApplication):
        setattr(qtgui, cls.__name__, cls)
    qtgui.QPushButton = _Enum("QPushButton", (qtgui.QAbstractButton,), {})

    shiboken = types.ModuleType("PySide.shiboken")
    shiboken.isValid = lambda obj: not getattr(obj, "_model_deleted", False)

    def _delete(obj):
        obj._model_delete()
    shiboken.delete = _delete

    pyside = types.ModuleType("PySide")
    pyside.__path__ = []
    pyside.QtCore = qtcore
    pyside.QtGui = qtgui
    pyside.shiboken = shiboken
    return pyside, qtcore, qtgui, shiboken


# ===========================================================================
# Child environment: one "SFM process"
# ===========================================================================

CHILD_RESULTS = []


def c(name, condition, value=None):
    CHILD_RESULTS.append([name, bool(condition), _jsonable(value)])


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except Exception:
        return repr(value)


def _host_exec(code, host):
    """SFM's ScriptController: PyRun_FileExFlags(file, main_dict, main_dict)."""
    exec(code, host, host)


class Env(object):
    def __init__(self, qt_mode, root):
        self.qt_mode = qt_mode
        self.root = os.path.normcase(os.path.abspath(root))
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        self.fs = os.path.join(self.root, "fs")
        self.docs = os.path.join(self.fs, "public", "documents")
        os.makedirs(self.docs)
        self._install_fs_shim()
        self.game = os.path.join(self.root, "game")
        self.menu_dir = os.path.join(self.game, "usermod", "scripts", "sfm", "mainmenu", "ChadChan3D")
        self.impl_dir = os.path.join(self.game, "usermod", "scripts", "ChadChan3D_CPM")
        os.makedirs(self.menu_dir)
        os.makedirs(self.impl_dir)
        self.menu_path = os.path.join(self.menu_dir, "SFM_Character_Preset_Manager.py")
        self.impl_path = os.path.normpath(os.path.abspath(os.path.join(self.impl_dir, "SFM_Character_Preset_Manager.py")))
        self.deploy(_read(LAUNCHER_PATH), _read(APP_PATH))
        sys.executable = os.path.join(self.game, "sfm.exe")
        self._install_sfm_fakes()
        self._install_qt()
        self.host = {"__name__": "__main__", "__doc__": None, "__package__": None, "__builtins__": builtins}
        self.consoles = []

    # -- boundaries ---------------------------------------------------------
    def _remap(self, path):
        try:
            if not isinstance(path, (str, _TEXT)):
                return path
            low = os.path.normcase(path)
        except Exception:
            return path
        if low.startswith(self.root):
            return path
        if low.startswith("c:\\users\\"):
            return os.path.join(self.fs, low[len("c:\\users\\"):])
        return path

    def _install_fs_shim(self):
        remap = self._remap
        real_open = builtins.open
        builtins.open = lambda p, *a, **k: real_open(remap(p), *a, **k)
        for name in ("isfile", "isdir", "exists"):
            fn = getattr(os.path, name)
            setattr(os.path, name, (lambda fn: lambda p: fn(remap(p)))(fn))
        real_makedirs, real_rename = os.makedirs, os.rename
        os.makedirs = lambda p, *a, **k: real_makedirs(remap(p), *a, **k)
        os.rename = lambda a, b: real_rename(remap(a), remap(b))
        # The bounded CPM logger also creates, lists, sizes and prunes files.
        for name in ("open", "listdir", "remove", "unlink", "stat", "lstat", "mkdir"):
            fn = getattr(os, name)
            setattr(os, name, (lambda fn: lambda p, *a, **k: fn(remap(p), *a, **k))(fn))
        self.real_open = real_open

    def _install_sfm_fakes(self):
        class Shot(object):
            animationSets = []
        sfm_app = types.ModuleType("sfmApp")
        sfm_app.GetShotAtCurrentTime = lambda: Shot()
        sfm_app.HasDocument = lambda: True  # an open session (empty shot); no modal error dialog
        sys.modules["sfmApp"] = sfm_app
        sys.modules["vs"] = types.ModuleType("vs")

    def _install_qt(self):
        if self.qt_mode == "real":
            from PySide import QtCore, QtGui, shiboken
            self.QtCore, self.QtGui, self.shiboken = QtCore, QtGui, shiboken
            self.app = QtGui.QApplication.instance() or QtGui.QApplication([])
            self.model = None
        else:
            pyside, qtcore, qtgui, shiboken = _qt_model_modules()
            for key in ("PySide", "PySide.QtCore", "PySide.QtGui", "PySide.shiboken"):
                sys.modules.pop(key, None)
            sys.modules["PySide"] = pyside
            sys.modules["PySide.QtCore"] = qtcore
            sys.modules["PySide.QtGui"] = qtgui
            sys.modules["PySide.shiboken"] = shiboken
            self.QtCore, self.QtGui, self.shiboken = qtcore, qtgui, shiboken
            self.model = _ModelApp()
            self.model.qapp = qtgui.QApplication()
            self.app = self.model.qapp

    # -- deployment ---------------------------------------------------------
    def deploy(self, launcher_bytes=None, impl_bytes=None):
        if launcher_bytes is not None:
            with open(self.menu_path, "wb") as f:
                f.write(launcher_bytes)
        if impl_bytes is not None:
            with open(self.impl_path, "wb") as f:
                f.write(impl_bytes)

    # -- host actions -------------------------------------------------------
    def click(self, flags=0):
        """One Scripts-menu click on the deployed launcher."""
        source = _read(self.menu_path)
        if flags:
            code = compile(source, self.menu_path, "exec", flags, True)
        else:
            code = compile(source, self.menu_path, "exec", 0, True)
        buf = io.StringIO() if not PY2 else _Py2Buffer()
        old = sys.stdout
        sys.stdout = buf
        try:
            _host_exec(code, self.host)
        finally:
            sys.stdout = old
        text = buf.getvalue()
        self.consoles.append(text)
        return text

    def settle(self, turns=6):
        if self.model is not None:
            self.model.settle(turns)
            return
        for _ in range(turns):
            self.app.processEvents()
            self.QtCore.QCoreApplication.sendPostedEvents(None, self.QtCore.QEvent.DeferredDelete)
            self.app.processEvents()

    def pump_timers(self, rounds=4):
        """Let retained Qt timers fire (the 100 ms modal watcher)."""
        if self.model is not None:
            self.model.settle(rounds)
            return
        import time
        for _ in range(rounds):
            deadline = time.time() + 0.15
            while time.time() < deadline:
                self.app.processEvents()
                time.sleep(0.01)

    # -- observation --------------------------------------------------------
    def module(self):
        return sys.modules.get(MODULE_KEY)

    def slot(self):
        return getattr(self.app, WINDOW_ATTR, None)

    def set_slot(self, value):
        setattr(self.app, WINDOW_ATTR, value)

    def notice(self):
        return getattr(self.app, NOTICE_ATTR, None)

    def alive(self, obj):
        try:
            return bool(self.shiboken.isValid(obj))
        except Exception:
            return False

    def log_files(self):
        """The bounded CPM log segments, in name order."""
        folder = os.path.join(self.docs, CPM_LOG_DIR.lower())
        if not os.path.isdir(folder):
            return []
        return [os.path.join(folder, n) for n in sorted(os.listdir(folder)) if n.endswith(".log")]

    def log(self, name=None):
        if name is None:
            paths = self.log_files()
        else:
            paths = [os.path.join(self.docs, name.lower())]
        texts = []
        for path in paths:
            if not os.path.isfile(path):
                continue
            with self.real_open(path, "rb") as f:
                texts.append(f.read().decode("utf-8", "replace"))
        return u"".join(texts) if texts else None

    def log_count(self, token):
        return (self.log() or u"").count(token)

    def docs_files(self):
        return sorted(os.listdir(self.docs))

    def windows(self):
        """Alive instances of the private module's ProdWindow."""
        module = self.module()
        if module is None:
            return []
        cls = module.__dict__.get("ProdWindow")
        gc.collect()
        return [o for o in gc.get_objects() if isinstance(o, cls) and self.alive(o)]

    def any_prod_windows(self):
        gc.collect()
        return [o for o in gc.get_objects()
                if type(o).__name__ == "ProdWindow" and self.alive(o)]

    def watchers(self):
        return [w for w in self.windows() if w.modal_watch_timer.isActive()]

    def notices(self):
        gc.collect()
        return [o for o in gc.get_objects() if isinstance(o, self.QtGui.QMessageBox) and self.alive(o)
                and o.objectName() == NOTICE_NAME]

    def escape(self, window):
        event = self.QtGui.QKeyEvent(self.QtCore.QEvent.KeyPress, self.QtCore.Qt.Key_Escape, self.QtCore.Qt.NoModifier)
        self.QtGui.QApplication.sendEvent(window, event)

    def foreign_modal(self):
        dialog = self.QtGui.QDialog()
        dialog.setWindowModality(self.QtCore.Qt.ApplicationModal)
        dialog.show()
        return dialog

    def resources(self):
        """Process working set / private commit / handle / GDI / USER counts
        (Windows, private WinDLL instances), plus live CPM object counts."""
        out = {"cpm_windows": len(self.windows()), "watchers": len(self.watchers()), "notices": len(self.notices())}
        try:
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                            ("PrivateUsage", ctypes.c_size_t)]
            k32, psapi, user32 = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi"), ctypes.WinDLL("user32")
            k32.GetCurrentProcess.restype = ctypes.c_void_p
            k32.GetProcessHandleCount.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
            psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), wintypes.DWORD]
            user32.GetGuiResources.argtypes = [ctypes.c_void_p, wintypes.DWORD]
            proc = k32.GetCurrentProcess()
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            psapi.GetProcessMemoryInfo(proc, ctypes.byref(pmc), pmc.cb)
            handles = wintypes.DWORD(0)
            k32.GetProcessHandleCount(proc, ctypes.byref(handles))
            out.update({"working_set": int(pmc.WorkingSetSize), "private_commit": int(pmc.PrivateUsage),
                        "handles": int(handles.value), "gdi": int(user32.GetGuiResources(proc, 0)),
                        "user": int(user32.GetGuiResources(proc, 1))})
        except Exception as exc:
            out["os_counters_error"] = repr(exc)
        return out


class _Py2Buffer(object):
    def __init__(self):
        self.parts = []

    def write(self, text):
        self.parts.append(text if isinstance(text, _TEXT) else text.decode("utf-8", "replace"))

    def flush(self):
        pass

    def getvalue(self):
        return u"".join(self.parts)


def outcome(text):
    for line in reversed(text.splitlines()):
        if "outcome=" in line:
            return line.split("[ChadChan3D CPM launcher] ", 1)[-1]
    return text.strip()


def host_snapshot(host):
    return dict((k, id(v)) for k, v in host.items())


def func_globals(fn):
    fn = getattr(fn, "__func__", fn)
    return getattr(fn, "__globals__", None)


# ===========================================================================
# Scenarios
# ===========================================================================

def _poison_host(env):
    """Bind the production Normalizer's colliding globals and the frozen
    G18AN build's top-level definitions into the shared host dictionary."""
    norm_text = _read(NORMALIZER_PATH).decode("utf-8").replace(u"\r\n", u"\n")
    blocks, _ = top_level_blocks(norm_text)
    if not PY2:
        env.host["unicode"] = str  # the Normalizer's own Py3 NameError fallback
    for name in ("OUTPUT_PATH", "arr", "handle", "name", "typ", "to_unicode"):
        if name not in blocks:
            continue
        _host_exec(compile(blocks[name], "Normalizer:%s" % name, "exec"), env.host)
    if "OUTPUT_PATH" not in env.host:
        # The current Normalizer no longer binds OUTPUT_PATH at top level; keep
        # the colliding host name the scenarios were designed around.
        env.host["OUTPUT_PATH"] = u"C:\\Users\\Public\\Documents\\host_owned_output.log"
    base_text = _read(BASELINE_PATH).decode("utf-8")
    base_blocks, _ = top_level_blocks(base_text)
    bound = []
    for name in ("prod_scope", "get_semantic_provider", "log_line", "reset_log", "StartProdTool",
                 "prod_cpm_open_adapter", "u", "PROD_OUTPUT_PATH", "PROD_APP_ATTR"):
        if name not in base_blocks:
            continue
        try:
            _host_exec(compile(base_blocks[name], "G18AN:%s" % name, "exec"), env.host)
            bound.append(name)
        except Exception:
            pass
    return bound


def scenario_lifecycle(env):
    """Namespace isolation, stable lifetime, state preservation, log
    destination, three close/reopen cycles (title bar, Escape, deferred
    Escape) and repeated-launch resource trend."""
    impl_bytes = _read(env.impl_path)
    telemetry = []
    host_before = host_snapshot(env.host)
    out = env.click()
    module = env.module()
    c("first_click.created", "outcome=created" in outcome(out), outcome(out))
    c("module.registered_real_module", isinstance(module, types.ModuleType))
    ns = module.__dict__
    c("module.identity_fields", ns.get("__name__") == MODULE_KEY and ns.get("__file__") == env.impl_path
      and ns.get("__chadchan3d_cpm_loader__") == LOADER_MARKER and ns.get("__chadchan3d_cpm_state__") == "ready",
      [ns.get("__name__"), ns.get("__file__"), ns.get("__chadchan3d_cpm_state__")])
    c("module.build_sha_is_exact_installed_bytes", ns.get("__chadchan3d_cpm_build_sha256__") == _sha(impl_bytes)
      == _sha(_read(APP_PATH)))
    c("module.no_path_or_custom_loader", "__path__" not in ns and ns.get("__package__") in (None, "")
      and ns.get("__builtins__") in (builtins, builtins.__dict__))
    c("host.gains_no_bindings", host_snapshot(env.host) == host_before, sorted(set(env.host) - set(host_before)))
    c("host.launcher_function_deleted", "_chadchan3d_cpm_launcher_v1" not in env.host)
    c("host.no_cpm_names", not (set(env.host) & set(["StartProdTool", "ProdWindow", "log_line", "PROD_RUN_ID"])))
    window = env.slot()
    c("window.owned_by_private_class", isinstance(window, ns["ProdWindow"]) and env.alive(window) and window.isVisible())
    c("functions.globals_are_private_dict", all(func_globals(f) is ns for f in (
        ns["StartProdTool"], ns["log_line"], ns["prod_scope"], ns["ProdWindow"].closeEvent,
        window.poll_foreign_modal, window.render)))
    c("log.cpm_log_receives_startup", env.log_count(u"PROD_R15_MODULE name='chadchan3d_cpm_app'") == 1
      and env.log_count(u"PROD_WINDOW_SHOWN=True") == 1)
    c("log.only_cpm_log_written", env.docs_files() == [CPM_LOG_DIR.lower()], env.docs_files())
    identities = (id(module), id(ns["ProdWindow"]), id(ns["StartProdTool"]), ns["PROD_RUN_ID"], id(window))
    counters = (ns.get("_SEMANTIC_PROVIDER_OPEN_COUNT"), ns.get("_SEMANTIC_PROVIDER"))
    telemetry.append(["initial-open", env.resources()])

    # Poison the shared host (Normalizer + frozen G18AN), then click again.
    bound = _poison_host(env)
    c("poison.bound_collision_names", set(["OUTPUT_PATH", "arr", "handle", "name", "typ", "prod_scope",
                                           "get_semantic_provider", "log_line"]) <= set(env.host), bound)
    c("poison.host_typ_is_normalizers", env.host["typ"](None) == "NoneType")
    poisoned = host_snapshot(env.host)
    log_size = len(env.log() or u"")
    out = env.click()
    c("second_click.reused", "outcome=reused" in outcome(out), outcome(out))
    c("second_click.same_identities", (id(env.module()), id(ns["ProdWindow"]), id(ns["StartProdTool"]),
                                       ns["PROD_RUN_ID"], id(env.slot())) == identities)
    c("second_click.no_counter_or_provider_reset", (ns.get("_SEMANTIC_PROVIDER_OPEN_COUNT"), ns.get("_SEMANTIC_PROVIDER"))
      == counters)
    c("second_click.one_window_one_watcher", len(env.windows()) == 1 and len(env.watchers()) == 1)
    c("second_click.log_not_reset_header_not_relogged", len(env.log()) > log_size
      and env.log_count(u"PROD_R15_MODULE name=") == 1 and env.log_count(u"PROD_R15_WINDOW_REUSED") == 1)
    c("second_click.host_poison_untouched", host_snapshot(env.host) == poisoned)
    c("isolation.private_typ_handle_arr_intact", ns["typ"](None) is None and ns["handle"](None) is None
      and ns["arr"](None, "controls") == [])
    c("isolation.private_log_destination", "OUTPUT_PATH" not in ns and "OUTPUT_PATH" in env.host
      and ns["PROD_LOG_DIR"] == u"C:\\Users\\Public\\Documents\\SFM Character Preset Manager Logs"
      and ns["log_line"] is not env.host["log_line"])
    c("isolation.private_prod_scope_is_canonical_route", ns["prod_scope"] is not env.host["prod_scope"]
      and "prod_cpm_open_adapter" in ns["prod_scope"].__code__.co_names)
    c("isolation.callbacks_keep_private_globals", func_globals(window.poll_foreign_modal) is ns
      and func_globals(window.closeEvent) is ns)
    ns["log_line"]("R15_OFFLINE_MARKER after-poison")
    c("isolation.log_line_targets_cpm_log", env.log_count(u"R15_OFFLINE_MARKER") == 1
      and NORMALIZER_LOG not in env.docs_files(), env.docs_files())
    telemetry.append(["second-click", env.resources()])

    # Cycle 1: title-bar close, then reopen.
    requests, finals = env.log_count(u"PROD_CLOSE_REQUEST"), env.log_count(u"PROD_CLOSE_FINALIZED")
    closed = window.close()
    env.settle()
    c("cycle1.close_accepted", closed is True)
    c("cycle1.teardown_once", env.log_count(u"PROD_CLOSE_REQUEST") == requests + 1
      and env.log_count(u"PROD_CLOSE_FINALIZED") == finals + 1)
    c("cycle1.slot_cleared_window_deleted", env.slot() is None and not env.alive(window))
    c("cycle1.no_window_or_watcher_left", env.windows() == [] and env.watchers() == [])
    window = None
    out = env.click()
    window = env.slot()
    c("cycle1.reopen_created_same_module", "outcome=created" in outcome(out) and env.module() is module
      and ns["PROD_RUN_ID"] == identities[3] and isinstance(window, ns["ProdWindow"]))
    c("cycle1.fresh_window_lifecycle", window.closing_requested is False and window.operation is None
      and window.modal_watch_timer.isActive() and len(env.windows()) == 1)
    telemetry.append(["cycle-1", env.resources()])

    # Cycle 2: Escape.
    requests, finals = env.log_count(u"PROD_CLOSE_REQUEST"), env.log_count(u"PROD_CLOSE_FINALIZED")
    env.escape(window)
    env.settle()
    c("cycle2.escape_runs_teardown_once", env.log_count(u"PROD_CLOSE_REQUEST") == requests + 1
      and env.log_count(u"PROD_CLOSE_FINALIZED") == finals + 1)
    c("cycle2.escape_clears_slot_and_deletes", env.slot() is None and not env.alive(window) and env.windows() == [])
    window = None
    out = env.click()
    window = env.slot()
    c("cycle2.reopen_created", "outcome=created" in outcome(out) and env.module() is module and len(env.windows()) == 1)
    telemetry.append(["cycle-2", env.resources()])

    # Cycle 3: Escape while an operation is in flight (deferred close), a
    # launcher click while closing, then the operation's end completes it.
    requests, finals = env.log_count(u"PROD_CLOSE_REQUEST"), env.log_count(u"PROD_CLOSE_FINALIZED")
    window.operation = {"kind": u"Body Save", "operation_id": 7, "phase": u"prompt"}
    window.busy = True
    env.escape(window)
    env.settle()
    c("cycle3.deferred_close_hides_keeps_slot", window.isVisible() is False and env.slot() is window
      and env.alive(window) and window.closing_requested is True)
    c("cycle3.deferred_close_not_finalized", env.log_count(u"PROD_CLOSE_FINALIZED") == finals
      and env.log_count(u"PROD_CLOSE_REQUEST") == requests + 1)
    out = env.click()
    c("cycle3.click_while_closing_refused", "code=refuse-closing" in outcome(out) and env.slot() is window
      and len(env.windows()) == 1 and window.isVisible() is False, outcome(out))
    window.operation_end(u"Body Save")
    env.settle()
    c("cycle3.operation_end_finalizes_once", env.log_count(u"PROD_CLOSE_FINALIZED") == finals + 1
      and env.log_count(u"PROD_CLOSE_REQUEST") == requests + 2)
    c("cycle3.slot_cleared_deleted", env.slot() is None and not env.alive(window) and env.windows() == [])
    window = None
    out = env.click()
    window = env.slot()
    c("cycle3.reopen_created", "outcome=created" in outcome(out) and env.module() is module and len(env.windows()) == 1)
    telemetry.append(["cycle-3", env.resources()])

    # Fit-stage variant of the deferred branch (hide now, finalize on re-close).
    finals = env.log_count(u"PROD_CLOSE_FINALIZED")
    window.fit_stage_running = True
    env.escape(window)
    env.settle()
    c("fitstage.deferred", env.slot() is window and not window.isVisible() and env.log_count(u"PROD_CLOSE_FINALIZED") == finals)
    window.fit_stage_running = False
    window.close()
    env.settle()
    c("fitstage.second_close_finalizes_once", env.log_count(u"PROD_CLOSE_FINALIZED") == finals + 1
      and env.slot() is None and not env.alive(window))
    window = None
    out = env.click()
    c("final.reopen_created", "outcome=created" in outcome(out))
    env.settle()
    telemetry.append(["final-settled", env.resources()])

    c("final.module_never_replaced", env.module() is module and ns["__chadchan3d_cpm_state__"] == "ready"
      and ns["PROD_RUN_ID"] == identities[3] and id(ns["ProdWindow"]) == identities[1])
    c("final.exactly_one_window_one_watcher", len(env.windows()) == 1 and len(env.watchers()) == 1
      and len(env.any_prod_windows()) == 1)
    c("final.no_foreign_log_destinations", env.docs_files() == [CPM_LOG_DIR.lower()], env.docs_files())
    c("final.no_launcher_owned_authority", not any(k.startswith("sfm_master_authority_productionized") for k in sys.modules)
      and "cpm_authority_adapter" not in sys.modules)
    c("telemetry.cpm_objects_bounded", all(t[1]["cpm_windows"] <= 1 and t[1]["watchers"] <= 1 and t[1]["notices"] <= 1
                                           for t in telemetry), telemetry)
    c("telemetry.recorded", True, telemetry)


def scenario_modal(env):
    """Owned modal-yield, foreign modal before the watcher observed it, and
    foreign modal with an empty slot; retained timer callbacks after poison."""
    env.click()
    ns = env.module().__dict__
    window = env.slot()
    _poison_host(env)
    dialog = env.foreign_modal()
    out = env.click()
    c("unobserved_modal.refused_not_shown", "code=refuse-foreign-modal" in outcome(out)
      and window.isVisible() and window.modal_yield_active is False, outcome(out))
    c("unobserved_modal.notice_suppressed", "notice suppressed (a modal dialog is active)" in out
      and (env.notice() is None or not env.notice().isVisible()))
    env.pump_timers()
    c("watcher.yield_entered_via_retained_callback", window.modal_yield_active is True and not window.isVisible()
      and env.log_count(u"G18AN_MODAL_YIELD_ENTER") == 1, env.log_count(u"G18AN_MODAL_YIELD_ENTER"))
    c("watcher.callback_logged_to_cpm_log_after_poison", NORMALIZER_LOG not in env.docs_files(), env.docs_files())
    out = env.click()
    c("modal_yield.refused_not_shown", "code=refuse-modal-yield" in outcome(out) and not window.isVisible(), outcome(out))
    dialog.hide()
    env.pump_timers()
    c("watcher.restores_after_modal", window.modal_yield_active is False and window.isVisible()
      and env.log_count(u"G18AN_MODAL_YIELD_EXIT") == 1)
    out = env.click()
    c("after_modal.reused", "outcome=reused" in outcome(out) and len(env.windows()) == 1)
    window.close()
    env.settle()
    window = None
    dialog2 = env.foreign_modal()
    out = env.click()
    c("empty_slot_foreign_modal.refused_no_window", "code=refuse-foreign-modal" in outcome(out)
      and env.slot() is None and env.windows() == [], outcome(out))
    dialog2.hide()
    out = env.click()
    c("empty_slot_after_modal.created", "outcome=created" in outcome(out) and len(env.windows()) == 1)
    c("modal.no_unexpected_notices", len(env.notices()) <= 1)


def scenario_window_table(env):
    """Every remaining window decision-table row."""
    QtGui = env.QtGui
    env.click()
    ns = env.module().__dict__
    owned = env.slot()
    # Owned, definitively deleted Qt object (slot never cleared).
    env.shiboken.delete(owned)
    out = env.click()
    new = env.slot()
    c("owned_deleted.cleared_by_identity_and_created", "outcome=created" in outcome(out)
      and new is not owned and isinstance(new, ns["ProdWindow"]) and env.log_count(u"PROD_R15_SLOT_CLEARED") == 1
      and u"owned=True" in env.log())
    new.close()
    env.settle()

    Legacy = type("ProdWindow", (QtGui.QDialog,), {})
    for visible in (True, False):
        legacy = Legacy()
        if visible:
            legacy.show()
        env.set_slot(legacy)
        out = env.click()
        c("foreign_live_%s.refused_untouched" % ("visible" if visible else "hidden"),
          "code=refuse-foreign-window" in outcome(out) and env.slot() is legacy and env.alive(legacy)
          and legacy.isVisible() is visible and env.windows() == [], outcome(out))
        legacy.hide()
        env.set_slot(None)
        legacy.deleteLater()
        env.settle()
    notice = env.notice()
    c("foreign_live.notice_shown_nonmodal", notice is not None and notice.isVisible() and not notice.isModal())

    legacy = Legacy()
    env.set_slot(legacy)
    env.shiboken.delete(legacy)
    out = env.click()
    c("foreign_deleted.cleared_and_created", "outcome=created" in outcome(out)
      and isinstance(env.slot(), ns["ProdWindow"]) and u"owned=False" in env.log())
    env.slot().close()
    env.settle()

    marker = object()
    env.set_slot(marker)
    out = env.click()
    c("malformed_occupant.refused_untouched", "code=refuse-malformed" in outcome(out) and env.slot() is marker
      and env.windows() == [], outcome(out))
    env.set_slot(None)

    out = env.click()
    owned = env.slot()
    real_is_valid = env.shiboken.isValid

    def raising(obj):
        raise RuntimeError("liveness unavailable")
    env.shiboken.isValid = raising
    try:
        out = env.click()
    finally:
        env.shiboken.isValid = real_is_valid
    c("uncertain_liveness.refused_not_empty", "code=refuse-uncertain" in outcome(out) and env.slot() is owned
      and env.alive(owned) and len(env.windows()) == 1, outcome(out))
    out = env.click()
    c("uncertain_cleared.reused", "outcome=reused" in outcome(out))
    c("table.decisions_logged_to_cpm_log", env.log_count(u"PROD_R15_LAUNCH_REFUSED") >= 4
      and env.docs_files() == [CPM_LOG_DIR.lower()], env.docs_files())


def scenario_startup_failures(env):
    """Post-READY UI failures: latch, bounded construction, partial-window
    close; pre-construction failure is retryable; STARTING refuses re-entry."""
    env.click()
    module = env.module()
    ns = module.__dict__
    env.slot().close()
    env.settle()

    # Pre-construction failure: not latched, explicit retry works.
    real_prepare = ns["prod_prepare_library_root"]

    def failing_prepare():
        raise RuntimeError("library root unavailable")
    ns["prod_prepare_library_root"] = failing_prepare
    out = env.click()
    c("preconstruct.failed_not_latched", "code=open-failed" in outcome(out)
      and ns["PROD_R15_STARTUP"]["state"] == u"idle" and env.windows() == [], outcome(out))
    ns["prod_prepare_library_root"] = real_prepare
    out = env.click()
    c("preconstruct.retry_created", "outcome=created" in outcome(out) and env.module() is module)
    env.slot().close()
    env.settle()

    # STARTING: a nested launcher click during construction is refused.
    cls = ns["ProdWindow"]
    real_init = cls.__init__
    nested = []

    def reentrant_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        nested.append(env.click())
    cls.__init__ = reentrant_init
    try:
        out = env.click()
    finally:
        cls.__init__ = real_init
    c("starting.nested_click_refused", len(nested) == 1 and "code=refuse-starting" in outcome(nested[0]),
      [outcome(n) for n in nested])
    c("starting.outer_created_one_window", "outcome=created" in outcome(out) and len(env.windows()) == 1
      and ns["PROD_R15_STARTUP"]["state"] == u"idle")
    env.slot().close()
    env.settle()
    c("state.single_window_after_close", env.windows() == [])


def scenario_constructor_failure(env):
    env.click()
    module = env.module()
    ns = module.__dict__
    env.slot().close()
    env.settle()
    cls = ns["ProdWindow"]
    real_init = cls.__init__
    built = []

    def failing_init(self, *args, **kwargs):
        built.append(1)
        real_init(self, *args, **kwargs)
        raise RuntimeError("injected constructor failure")
    cls.__init__ = failing_init
    try:
        outs = [env.click() for _ in range(3)]
    finally:
        cls.__init__ = real_init
    c("ctor.first_attempt_latches", "code=failed-restart-required" in outcome(outs[0])
      and ns["PROD_R15_STARTUP"]["state"] == u"failed-restart-required", outcome(outs[0]))
    c("ctor.later_clicks_refused_no_construction", all("code=refuse-failed-restart-required" in outcome(o) for o in outs[1:])
      and len(built) == 1, [outcome(o) for o in outs])
    c("ctor.ready_module_survives", env.module() is module and ns["__chadchan3d_cpm_state__"] == "ready")
    c("ctor.slot_not_set", env.slot() is None)
    c("ctor.failure_diagnostics_are_text", isinstance(ns["PROD_R15_STARTUP"]["failure"], (str, _TEXT)))
    out = env.click()
    c("ctor.latch_persists_after_restore", "code=refuse-failed-restart-required" in outcome(out) and len(built) == 1)
    c("ctor.notice_single_and_reused", len(env.notices()) == 1 and env.notice().isVisible())


def scenario_show_failure(env):
    env.click()
    module = env.module()
    ns = module.__dict__
    env.slot().close()
    env.settle()
    cls = ns["ProdWindow"]
    had_own_show = "show" in cls.__dict__

    def failing_show(self):
        raise RuntimeError("injected show failure")
    cls.show = failing_show
    try:
        out = env.click()
        partial_count = len(env.windows())
    finally:
        if not had_own_show:
            del cls.show
    env.settle()
    c("show.latched", "code=failed-restart-required" in outcome(out)
      and ns["PROD_R15_STARTUP"]["state"] == u"failed-restart-required", outcome(out))
    c("show.partial_window_closed_and_deleted", partial_count == 1 and env.windows() == [] and env.slot() is None
      and env.log_count(u"partial_window=True closed=True") == 1)
    c("show.partial_close_ran_teardown", env.log_count(u"PROD_CLOSE_FINALIZED") >= 2)
    outs = [env.click() for _ in range(2)]
    c("show.no_accumulation", all("code=refuse-failed-restart-required" in outcome(o) for o in outs)
      and env.windows() == [] and env.module() is module)


class _Finder(object):
    """Import hook (test-only) that fails one late application import."""

    def __init__(self, target, action):
        self.target = target
        self.action = action

    def find_module(self, fullname, path=None):  # Python 2
        return self if fullname == self.target else None

    def load_module(self, fullname):
        self.action()

    def find_spec(self, fullname, path=None, target=None):  # Python 3
        if fullname == self.target:
            self.action()
        return None


def _with_failing_import(target, action, fn):
    saved = sys.modules.pop(target, None)
    finder = _Finder(target, action)
    sys.meta_path.insert(0, finder)
    try:
        return fn()
    finally:
        sys.meta_path.remove(finder)
        if saved is not None:
            sys.modules[target] = saved


def scenario_loading_failures(env):
    """Pre-READY failures remove only the attempt's own entry; explicit retry
    works; interruption is cleaned and propagated; a foreign replacement
    installed during loading is never deleted."""
    host_before = host_snapshot(env.host)

    def import_error():
        raise ImportError("injected late import failure")
    out = _with_failing_import("uuid", import_error, env.click)
    c("late_import.failed_entry_removed", "code=load-failed entry_removed=True" in out
      and MODULE_KEY not in sys.modules, outcome(out))
    c("late_import.nothing_escaped", env.any_prod_windows() == [] and env.slot() is None
      and len(env.notices()) == 1 and host_snapshot(env.host) == host_before)
    c("late_import.diagnostics_are_formatted_text", "injected late import failure" in out)
    out = env.click()
    first = env.module()
    c("late_import.retry_works", "outcome=created" in outcome(out) and first.__chadchan3d_cpm_state__ == "ready")
    first = None
    env.slot().close()
    env.settle()

    # Interruption (fresh module entry required: tested in a clean key).
    del sys.modules[MODULE_KEY]
    env.settle()

    def interrupt():
        raise KeyboardInterrupt()
    interrupted = []

    def run():
        try:
            env.click()
        except KeyboardInterrupt:
            interrupted.append(True)
    _with_failing_import("uuid", interrupt, run)
    c("interrupt.propagated_after_cleanup", interrupted == [True] and MODULE_KEY not in sys.modules)
    c("interrupt.launcher_function_deleted", "_chadchan3d_cpm_launcher_v1" not in env.host
      and host_snapshot(env.host) == host_before)
    out = env.click()
    c("interrupt.retry_works", "outcome=created" in outcome(out))
    env.slot().close()
    env.settle()

    del sys.modules[MODULE_KEY]
    foreign = types.ModuleType(MODULE_KEY)

    def replace_then_fail():
        sys.modules[MODULE_KEY] = foreign
        raise ImportError("injected failure after foreign replacement")
    out = _with_failing_import("uuid", replace_then_fail, env.click)
    c("foreign_replacement.not_deleted", sys.modules.get(MODULE_KEY) is foreign
      and "entry_removed=False" in out, outcome(out))
    out = env.click()
    c("foreign_replacement.then_refused_untouched", "code=module-incompatible" in outcome(out)
      and sys.modules.get(MODULE_KEY) is foreign, outcome(out))


def scenario_identity_refusals(env):
    """Foreign / LOADING / incompatible / wrong-origin / malformed entries are
    refused and left exactly as found."""
    sha = _sha(_read(env.impl_path))

    def entry(**fields):
        module = types.ModuleType(fields.pop("name", MODULE_KEY))
        base = {"__file__": env.impl_path, "__chadchan3d_cpm_loader__": LOADER_MARKER,
                "__chadchan3d_cpm_build_sha256__": sha, "__chadchan3d_cpm_state__": "ready",
                "StartProdTool": lambda: {"outcome": "created"}, "prod_r15_launcher_refusal": lambda *a: None}
        base.update(fields)
        for key, value in base.items():
            if value is not None:
                setattr(module, key, value)
        return module
    cases = [
        ("foreign_object", object(), "code=module-foreign"),
        ("loading", entry(__chadchan3d_cpm_state__="loading"), "code=module-loading"),
        ("wrong_name", entry(name="something_else"), "code=module-foreign"),
        ("old_loader_marker", entry(__chadchan3d_cpm_loader__="cpm-private-loader-v0"), "code=module-incompatible"),
        ("no_loader_marker", entry(__chadchan3d_cpm_loader__=None), "code=module-incompatible"),
        ("wrong_origin", entry(__file__=os.path.join(env.menu_dir, "SFM_Character_Preset_Manager.py")), "code=module-wrong-origin"),
        ("malformed_state", entry(__chadchan3d_cpm_state__="weird"), "code=module-malformed"),
        ("malformed_build", entry(__chadchan3d_cpm_build_sha256__="x"), "code=module-malformed"),
        ("missing_entry_points", entry(StartProdTool=None, prod_r15_launcher_refusal=None), "code=module-malformed"),
        ("none_entry", None, "code=module-foreign"),
    ]
    for label, value, expected in cases:
        sys.modules[MODULE_KEY] = value
        before = dict(value.__dict__) if isinstance(value, types.ModuleType) else None
        out = env.click()
        after_ok = sys.modules.get(MODULE_KEY) is value and (
            before is None or dict(value.__dict__) == before)
        c("refusal.%s" % label, expected in outcome(out) and after_ok and env.any_prod_windows() == [], outcome(out))
    del sys.modules[MODULE_KEY]
    c("refusal.notice_single", len(env.notices()) == 1)
    c("refusal.no_cpm_log_for_foreign_entries", env.log() is None)


def scenario_installed_bytes(env):
    """Changed or unreadable installed bytes never reload; the loaded module
    and its open window keep running; restart is required."""
    env.click()
    module = env.module()
    ns = module.__dict__
    window = env.slot()
    sha = ns["__chadchan3d_cpm_build_sha256__"]
    original = _read(env.impl_path)
    env.deploy(impl_bytes=original + b"\n# changed build\n")
    out = env.click()
    c("changed.refused_restart", "code=installed-build-changed" in outcome(out), outcome(out))
    c("changed.no_reload", env.module() is module and ns["__chadchan3d_cpm_build_sha256__"] == sha
      and ns["__chadchan3d_cpm_state__"] == "ready")
    c("changed.window_keeps_running", env.slot() is window and window.isVisible() and len(env.windows()) == 1)
    c("changed.logged_in_cpm_log", env.log_count(u"code=u'installed-build-changed'") + env.log_count(u"code='installed-build-changed'") == 1)
    window.close()
    env.settle()
    window = None
    out = env.click()
    c("changed.reopen_refused", "code=installed-build-changed" in outcome(out) and env.windows() == [])
    os.remove(env.impl_path)
    out = env.click()
    c("unreadable.refused_module_intact", "code=installed-unreadable" in outcome(out) and env.module() is module)
    env.deploy(impl_bytes=original)
    out = env.click()
    c("restored_bytes.open_again", "outcome=created" in outcome(out) and env.module() is module)
    c("notice.one_widget_reused", len(env.notices()) == 1)


def scenario_absent_unreadable(env):
    os.remove(env.impl_path)
    out = env.click()
    c("absent_unreadable.refused_no_entry", "code=installed-unreadable" in outcome(out) and MODULE_KEY not in sys.modules)
    env.deploy(impl_bytes=_read(APP_PATH))
    out = env.click()
    c("absent_unreadable.retry_after_install", "outcome=created" in outcome(out))


def scenario_notice(env):
    """One retained, parentless, non-modal notice; acknowledge/reuse; no
    Python callbacks; suppressed under modal; foreign slot left untouched."""
    QtGui, QtCore = env.QtGui, env.QtCore
    sys.modules[MODULE_KEY] = object()   # guaranteed launcher refusal
    env.click()
    box = env.notice()
    c("notice.created_on_app_attr", isinstance(box, QtGui.QMessageBox) and box.objectName() == NOTICE_NAME)
    c("notice.parentless_nonmodal", box.parent() is None and not box.isModal()
      and box.windowModality() == QtCore.Qt.NonModal)
    c("notice.delete_and_quit_on_close_disabled", not box.testAttribute(QtCore.Qt.WA_DeleteOnClose)
      and not box.testAttribute(QtCore.Qt.WA_QuitOnClose))
    c("notice.visible_with_text", box.isVisible() and "Restart SFM" in box.text())
    if env.model is None:
        receivers = [box.receivers(QtCore.SIGNAL(sig)) for sig in (
            "finished(int)", "accepted()", "rejected()", "buttonClicked(QAbstractButton*)")]
    else:
        receivers = [len(box.finished.slots), len(box.accepted.slots), len(box.rejected.slots), len(box.buttonClicked.slots)]
    c("notice.no_python_callbacks", receivers == [0, 0, 0, 0], receivers)
    box.button(QtGui.QMessageBox.Ok).click()
    env.settle()
    c("notice.acknowledge_hides_keeps_alive", env.alive(box) and not box.isVisible())
    env.click()
    c("notice.reused_same_object", env.notice() is box and box.isVisible() and len(env.notices()) == 1)
    box.hide()
    dialog = env.foreign_modal()
    out = env.click()
    c("notice.suppressed_under_modal", "notice suppressed (a modal dialog is active)" in out and not box.isVisible())
    dialog.hide()
    env.settle()
    foreign = QtGui.QMessageBox()
    foreign.setObjectName("someone_else")
    setattr(env.app, NOTICE_ATTR, foreign)
    out = env.click()
    c("notice.foreign_slot_untouched", "notice slot foreign or malformed" in out and env.notice() is foreign
      and not foreign.isVisible() and foreign.objectName() == "someone_else")
    setattr(env.app, NOTICE_ATTR, "malformed")
    out = env.click()
    c("notice.malformed_slot_untouched", "notice slot foreign or malformed" in out and env.notice() == "malformed")
    setattr(env.app, NOTICE_ATTR, box)
    del sys.modules[MODULE_KEY]
    out = env.click()
    c("notice.counted_separately_from_windows", "outcome=created" in outcome(out) and len(env.windows()) == 1
      and len(env.notices()) == 1)


def scenario_compile_flags(env):
    """Host future flags are not inherited by the private module; exact bytes
    are compiled with the implementation path as filename."""
    import __future__
    names = ["division", "print_function", "unicode_literals", "absolute_import"] if PY2 else ["annotations"]
    flags = 0
    for n in names:
        flags |= getattr(__future__, n).compiler_flag
    out = env.click(flags=flags)
    ns = env.module().__dict__
    future_mask = 0
    for n in __future__.all_feature_names:
        future_mask |= getattr(__future__, n).compiler_flag
    leaked = sorted(set(k for k, v in ns.items() if isinstance(v, types.FunctionType)
                        and v.__code__.co_flags & flags))
    c("flags.launcher_ran_under_host_flags", "outcome=created" in outcome(out), outcome(out))
    c("flags.private_code_has_no_inherited_future_flags", leaked == [], leaked[:5])
    c("flags.code_filename_is_impl_path", ns["StartProdTool"].__code__.co_filename == env.impl_path)


COOKIE_IMPL = (
    b"# -*- coding: latin-1 -*-\n"
    b"\"\"\"Synthetic R15 implementation (coding-cookie gate).\"\"\"\n"
    b"if not (__name__ == 'chadchan3d_cpm_app' and globals().get('__chadchan3d_cpm_loader__') == 'cpm-private-loader-v1'\n"
    b"        and globals().get('__chadchan3d_cpm_state__') == 'loading'):\n"
    b"    raise RuntimeError('launch through the menu entry')\n"
    b"SAMPLE = u'caf\xe9'\n"
    b"CALLS = []\n"
    b"def StartProdTool():\n"
    b"    CALLS.append(1)\n"
    b"    return {'outcome': 'created', 'code': 'create', 'notice': None}\n"
    b"def prod_r15_launcher_refusal(code, detail=None):\n"
    b"    return None\n"
)


def scenario_coding_cookie(env):
    env.deploy(impl_bytes=COOKIE_IMPL)
    out = env.click()
    ns = env.module().__dict__
    c("cookie.loaded", "outcome=created" in outcome(out), outcome(out))
    c("cookie.latin1_literal_decoded_per_cookie", ns.get("SAMPLE") == u"caf\xe9", repr(ns.get("SAMPLE")))
    c("cookie.build_sha_exact_bytes", ns["__chadchan3d_cpm_build_sha256__"] == _sha(COOKIE_IMPL))
    env.click()
    c("cookie.second_click_no_reexecution", ns["CALLS"] == [1, 1] and env.module().__dict__ is ns)


def scenario_direct_execution(env):
    """The allow-guard refuses every execution outside the loading context,
    before any import or definition."""
    app_bytes = _read(APP_PATH)
    code = compile(app_bytes, "menu:SFM_Character_Preset_Manager.py", "exec", 0, True)
    host_before = set(env.host)
    try:
        _host_exec(code, env.host)
        raised = None
    except RuntimeError as exc:
        raised = _TEXT(exc)
    c("guard.shared_host_refused", raised is not None and "Launch it through" in raised, raised)
    c("guard.shared_host_gains_nothing", set(env.host) == host_before, sorted(set(env.host) - host_before))
    for label, fields in (("no_marker", {"__chadchan3d_cpm_state__": "loading"}),
                          ("wrong_state", {"__chadchan3d_cpm_loader__": LOADER_MARKER, "__chadchan3d_cpm_state__": "ready"}),
                          ("wrong_name", {"__chadchan3d_cpm_loader__": LOADER_MARKER, "__chadchan3d_cpm_state__": "loading"})):
        module = types.ModuleType("other_name" if label == "wrong_name" else MODULE_KEY)
        for k, v in fields.items():
            setattr(module, k, v)
        before = set(module.__dict__)
        try:
            _host_exec(code, module.__dict__)
            ok = False
        except RuntimeError:
            ok = set(module.__dict__) - before <= set(["__builtins__"])
        c("guard.%s_refused_before_definitions" % label, ok)
    c("guard.no_side_effects", env.any_prod_windows() == [] and env.log() is None and MODULE_KEY not in sys.modules)


def scenario_teardown_contrast(env):
    """Model fidelity: with reject() -> close() but the OLD base closeEvent
    finalization, Qt re-enters closing and the close is ignored. The shipped
    finalization does not (proved in the lifecycle scenario)."""
    text = _read(APP_PATH).decode("ascii")
    old = (u"        event.accept()\n        QtGui.QDialog.reject(\n            self\n        )\n")
    contrast = text.replace(old, u"        QtGui.QDialog.closeEvent(\n            self,\n            event,\n        )\n")
    c("contrast.perturbation_applied", contrast != text and contrast.count(u"QtGui.QDialog.closeEvent(") == text.count(
        u"QtGui.QDialog.closeEvent(") + 1)
    env.deploy(impl_bytes=contrast.encode("ascii"))
    env.click()
    window = env.slot()
    closed = window.close()
    env.settle()
    c("contrast.old_finalization_close_ignored", closed is False and env.alive(window) and window.isVisible(),
      [closed, env.alive(window)])
    c("contrast.old_finalization_teardown_ran_but_window_survives", env.log_count(u"PROD_CLOSE_FINALIZED") == 1
      and env.slot() is None)
    window.hide()


SCENARIOS = [
    ("lifecycle", scenario_lifecycle),
    ("modal", scenario_modal),
    ("window_table", scenario_window_table),
    ("startup_failures", scenario_startup_failures),
    ("constructor_failure", scenario_constructor_failure),
    ("show_failure", scenario_show_failure),
    ("loading_failures", scenario_loading_failures),
    ("identity_refusals", scenario_identity_refusals),
    ("installed_bytes", scenario_installed_bytes),
    ("absent_unreadable", scenario_absent_unreadable),
    ("notice", scenario_notice),
    ("compile_flags", scenario_compile_flags),
    ("coding_cookie", scenario_coding_cookie),
    ("direct_execution", scenario_direct_execution),
    ("teardown_contrast", scenario_teardown_contrast),
]


def child_main(scenario, qt_mode, root):
    env = Env(qt_mode, root)
    fn = dict(SCENARIOS)[scenario]
    try:
        fn(env)
    except BaseException as exc:  # report, never hang the parent
        import traceback
        c("scenario_completed", False, traceback.format_exc()[-1500:])
    else:
        c("scenario_completed", True)
    sys.stdout.write("R15_CHILD_RESULT " + json.dumps(CHILD_RESULTS) + "\n")
    sys.stdout.flush()


# ===========================================================================
# Parent: static source gates and scenario orchestration
# ===========================================================================

def static_launcher():
    raw = _read(LAUNCHER_PATH)
    check("launcher.ascii_lf", all(ord(ch) < 128 for ch in raw.decode("latin-1")) and b"\r" not in raw)
    tree = ast.parse(raw)
    kinds = [type(n).__name__ for n in tree.body]
    check("launcher.top_level_is_one_function_and_guarded_call",
          len(tree.body) == 2 and isinstance(tree.body[0], ast.FunctionDef)
          and tree.body[0].name == "_chadchan3d_cpm_launcher_v1" and kinds[1] in ("Try", "TryFinally"), kinds)
    check("launcher.no_module_docstring", ast.get_docstring(tree) is None)
    func = tree.body[0]
    code_text = raw.decode("ascii")
    body_lines = [l for l in code_text.splitlines() if not l.lstrip().startswith("#")]
    body = u"\n".join(body_lines)
    for label, token in (("sys_path", "sys.path"), ("qt_connect", ".connect("), ("timer", "QTimer"),
                         ("nested_event_loop", "exec_("), ("process_events", "processEvents"),
                         ("reload", "reload("), ("execfile", "execfile"), ("dunder_import", "__import__"),
                         ("imp_module", "imp."), ("importlib", "importlib"), ("exec_statement", "exec(")):
        check("launcher.no_%s" % label, token not in body)
    compiles = [n for n in ast.walk(func) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "compile"]
    ok = len(compiles) == 1 and len(compiles[0].args) == 5
    if ok:
        a = compiles[0].args
        ok = (getattr(a[0], "id", None) == "source_bytes" and getattr(a[1], "id", None) == "impl_path"
              and (getattr(a[2], "s", None) or getattr(a[2], "value", None)) == "exec"
              and (getattr(a[3], "n", None) if hasattr(a[3], "n") else getattr(a[3], "value", None)) == 0
              and (getattr(a[4], "id", None) == "True" or getattr(a[4], "value", None) is True))
    check("launcher.single_exact_compile_call", ok)
    reads = [n for n in ast.walk(func) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "read_bytes"]
    check("launcher.reads_installed_bytes_once_per_path", len(reads) == 2)
    top_imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    check("launcher.imports_local_only", not top_imports)
    nested = [n.name for n in func.body if isinstance(n, ast.FunctionDef)]
    check("launcher.helpers_are_local", sorted(nested) == ["classify", "console", "notice", "read_bytes"], nested)


def static_app():
    raw = _read(APP_PATH)
    text = raw.decode("ascii")
    tree = ast.parse(raw)
    first = tree.body[1]
    check("app.allow_guard_first_after_docstring", isinstance(tree.body[0], ast.Expr) and isinstance(first, ast.If)
          and isinstance(first.body[0], ast.Raise) and first.lineno < min(
              n.lineno for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))))
    guard_src = u"\n".join(text.split(u"\n")[first.lineno - 1:first.body[0].lineno + 4])
    check("app.allow_guard_requires_name_marker_state", all(t in guard_src for t in (
        u'__name__ == "chadchan3d_cpm_app"', u'"__chadchan3d_cpm_loader__") == "cpm-private-loader-v1"',
        u'"__chadchan3d_cpm_state__") == "loading"')))
    calls = [n for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)]
    check("app.no_top_level_startup_call", calls == [], [getattr(n.value.func, "id", None) for n in calls])
    blocks, _ = top_level_blocks(text)
    close_src = blocks["ProdWindow"]
    check("app.close_finalizes_via_base_reject_only", u"QtGui.QDialog.reject(\n            self\n        )" in close_src
          and u"QtGui.QDialog.closeEvent(" not in close_src)
    check("app.reject_routes_to_close", u"    def reject(\n        self,\n    ):" in close_src
          and u"        self.close()\n" in close_src)
    check("app.no_sys_path_in_r15_code", all(u"sys.path" not in blocks[n] for n in blocks if n.startswith(u"prod_r15")
                                              or n in (u"StartProdTool", u"PROD_R15_STARTUP")))


def static_forbidden():
    for rel, pinned in sorted(PINNED_RAW.items()):
        check("forbidden.unchanged.%s" % rel, _sha(_read(os.path.join(_REPO_ROOT, rel))) == pinned)
    check("forbidden.unchanged.shared_package", package_digest() == PACKAGE_DIGEST_PINNED, package_digest())
    blocks, _ = top_level_blocks(_read(APP_PATH).decode("ascii"))
    r14 = _sha((blocks["prod_private_windll"] + blocks["prod_resource_snapshot"] + blocks["_PROD_PRIVATE_WINDLL"]).encode("ascii"))
    check("forbidden.unchanged.r14_private_ctypes", r14 == R14_TEXT_PINNED, r14)


def package_digest():
    root = os.path.join(_REPO_ROOT, *PACKAGE_DIR.split("/"))
    h = hashlib.sha256()
    for name in sorted(os.listdir(root)):
        if name.endswith(".py"):
            h.update(name.encode("ascii") + b"\0" + _read(os.path.join(root, name)).replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def run_children(qt_modes):
    if os.path.isdir(FIXTURE_ROOT):
        shutil.rmtree(FIXTURE_ROOT)
    os.makedirs(FIXTURE_ROOT)
    telemetry = {}
    for qt_mode in qt_modes:
        for name, _ in SCENARIOS:
            root = os.path.join(FIXTURE_ROOT, "%s_%s" % (qt_mode, name))
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            proc = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--child=%s" % name,
                                     "--qt=%s" % qt_mode, "--root=%s" % root],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
            output = proc.communicate()[0].decode("utf-8", "replace")
            records = None
            for line in output.splitlines():
                if line.startswith("R15_CHILD_RESULT "):
                    records = json.loads(line[len("R15_CHILD_RESULT "):])
            if records is None:
                check("%s.%s.child_reported" % (qt_mode, name), False, output[-2000:])
                continue
            for cname, ok, value in records:
                if cname == "telemetry.recorded":
                    telemetry[qt_mode] = value
                check("%s.%s.%s" % (qt_mode, name, cname), ok, value)
    return telemetry


def qt_available():
    try:
        out = subprocess.check_output([sys.executable, "-c", "from PySide import QtGui; print('ok')"],
                                      stderr=subprocess.STDOUT)
        return b"ok" in out
    except Exception:
        return False


def main():
    args = dict(a.split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    if "--child" in args:
        child_main(args["--child"], args["--qt"], args["--root"])
        return
    if args.get("--phase") != "run":
        print("usage: %s --phase=run" % os.path.basename(sys.argv[0]))
        sys.exit(2)
    print("Interpreter: %s" % sys.version.split()[0])
    static_launcher()
    static_app()
    static_forbidden()
    modes = (["real"] if qt_available() else []) + ["model"]
    print("Qt modes: %s" % ", ".join(modes))
    telemetry = run_children(modes)
    for mode, rows in sorted(telemetry.items()):
        print("RESOURCE TREND (%s, offline process):" % mode)
        for label, row in rows:
            print("  %-14s %s" % (label, json.dumps(row, sort_keys=True)))
    passed = sum(1 for r in RESULTS if r[1])
    print("\nRESULT: %d/%d %s" % (passed, len(RESULTS), "ALL PASS" if passed == len(RESULTS) else "SOME FAILED"))
    if passed != len(RESULTS):
        sys.exit(1)


if __name__ == "__main__":
    main()
