# -*- coding: ascii -*-
# SFM Character Preset Manager -- Animation Set Editor Quick Launch (QL-1).
#
# Private implementation. Deployed as
# <SFM game>/usermod/scripts/ChadChan3D_CPM/cpm_ase_quick_launch.py,
# outside the Autoinit and Scripts-menu discovery trees. The Autoinit bootstrap
# (usermod/scripts/sfm/autoinit/ChadChan3D/ChadChan3D_CPM_ASE_Button.py) loads
# it once per SFM process into the private module
# chadchan3d_cpm_ase_quick_launch and calls bootstrap_request() each time it
# runs.
#
# One process-lifetime controller adds one "CPM" button to the Animation Set
# Editor's upper bar, only in genuinely free space, and opens CPM on click by
# executing the unchanged installed R15 Scripts-menu launcher in a fresh
# dictionary. It never loads CPM before a click and never moves, resizes,
# hides, reparents or deletes another control.
#
# Controller states:
#   WAITING    no complete, uniquely supported editor toolbar yet (absent,
#              still being built, or temporarily ambiguous); one 1-second
#              discovery timer runs
#   ATTACHED   a validated editor/row; discovery stopped; local events drive
#              one coalesced layout timer
#   SUSPENDED  a positively unsupported toolbar, or an unexpected failure;
#              no automatic retry
#   STOPPING / STOPPED  timers stopped, owned filters and connections removed,
#              owned widgets released
#
# Python 2.7.5 / PySide 1.2 (SFM's embedded interpreter).

import os
import sys
import traceback

try:
    import __builtin__ as _builtins_module
except ImportError:  # Python 3 (offline syntax checks only)
    import builtins as _builtins_module

from PySide import QtCore
from PySide import QtGui

try:
    from PySide import shiboken
except ImportError:
    import shiboken


QUICK_LAUNCH_STAGE = "QL-1"

BUTTON_NAME = "chadchan3d_cpm_ase_button"
CONTROLLER_NAME = "chadchan3d_cpm_ase_quick_launch_controller"
NOTICE_NAME = "chadchan3d_cpm_ase_quick_launch_notice"

BUTTON_TEXT = "CPM"
BUTTON_TOOLTIP = "Open Character Preset Manager"
NOMINAL_WIDTH = 40
NOMINAL_HEIGHT = 32
CLEARANCE = 5

DISCOVERY_INTERVAL_MS = 1000
MAX_BUTTON_RECREATIONS = 3

EDITOR_CLASS = "CQAnimationSetEditor"
EDITOR_NAME = "QAnimationSetEditor"
ROW_CLASS = "CQEditorUpperBarWidget"
NATIVE_BUTTON_CLASS = "CQTabbedToolButton"
NATIVE_ADD_TOOLTIP = "Add"

LAUNCHER_RELATIVE_PARTS = (
    "usermod", "scripts", "sfm", "mainmenu", "ChadChan3D",
    "SFM_Character_Preset_Manager.py",
)

NOTICE_TITLE = "SFM Character Preset Manager"
LAUNCH_FAILED_TEXT = (
    "Character Preset Manager couldn't be opened. Try its Scripts-menu entry. "
    "If that also fails, repair the CPM installation."
)
RECREATION_EXHAUSTED_TEXT = (
    "the CPM button was removed from the Animation Set Editor toolbar "
    "repeatedly, so it won't be added again for now. Open Character Preset "
    "Manager from the Scripts menu, or run ChadChan3D_CPM_ASE_Button again "
    "from Autoinit Manager to retry."
)

WAITING = "WAITING"
ATTACHED = "ATTACHED"
SUSPENDED = "SUSPENDED"
STOPPING = "STOPPING"
STOPPED = "STOPPED"

SUSPEND_UNSUPPORTED = "unsupported"
SUSPEND_FAILED = "failed"

_WATCHED_EVENT_TYPES = frozenset([int(event_type) for event_type in (
    QtCore.QEvent.Resize,
    QtCore.QEvent.Move,
    QtCore.QEvent.Show,
    QtCore.QEvent.Hide,
    QtCore.QEvent.ChildAdded,
    QtCore.QEvent.ChildRemoved,
    QtCore.QEvent.ParentChange,
)])

# The one controller for this SFM process, strongly retained here.
_CONTROLLER = None
# Set when a failed initialization could not be demonstrably cleaned up.
_RESTART_REQUIRED = False


def console(text):
    try:
        sys.stdout.write("[ChadChan3D CPM Quick Launch] %s\n" % (text,))
    except Exception:
        pass


def installed_launcher_path():
    """The installed R15 Scripts-menu launcher, by the sys.executable
    convention the launcher itself uses."""
    game = os.path.dirname(os.path.abspath(sys.executable))
    return os.path.normpath(os.path.abspath(
        os.path.join(game, *LAUNCHER_RELATIVE_PARTS)))


def find_free_slot(row_width, origin, occupied, width, clearance=CLEARANCE):
    """Left x of the first interval at or after origin that holds width
    while keeping clearance from every occupied (left, right) span, or None.

    Spans are half-open pixel intervals in row coordinates. Only real
    occupied space is considered; the row is never split into halves."""
    spans = sorted([(int(left), int(right)) for left, right in occupied
                    if int(right) > int(left)])
    x = max(0, int(origin))
    for left, right in spans:
        if right + clearance <= x:
            continue
        if x + width + clearance <= left:
            break
        x = max(x, right + clearance)
    if x + width <= int(row_width):
        return x
    return None


def _valid(obj):
    if obj is None:
        return False
    try:
        return bool(shiboken.isValid(obj))
    except Exception:
        return False


def _class_name(obj):
    try:
        return str(obj.metaObject().className())
    except Exception:
        return None


def _widget_children(obj):
    try:
        return [child for child in obj.children() if child.isWidgetType()]
    except Exception:
        return []


def _contains(items, obj):
    for item in items:
        if item is obj:
            return True
    return False


def _same_members(first, second):
    """Identity-based set equality (z-order changes are not structure)."""
    if len(first) != len(second):
        return False
    for item in first:
        if not _contains(second, item):
            return False
    return True


def _occupied_spans(row, own, band_top, band_bottom):
    """Horizontal spans of the row's visible direct-child widgets that
    intersect the button band, excluding CPM's own button and windows."""
    spans = []
    for child in _widget_children(row):
        if child is own:
            continue
        if child.isWindow() or not child.isVisibleTo(row):
            continue
        rect = child.geometry()
        if rect.width() <= 0 or rect.height() <= 0:
            continue
        if rect.y() >= band_bottom or rect.y() + rect.height() <= band_top:
            continue
        spans.append((rect.x(), rect.x() + rect.width()))
    return spans


def _read_bytes(path):
    handle = None
    try:
        handle = open(path, "rb")
        return handle.read()
    except Exception:
        return None
    finally:
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass


class QuickLaunchController(QtCore.QObject):

    def __init__(self, app):
        QtCore.QObject.__init__(self, app)
        self.setObjectName(CONTROLLER_NAME)
        self.state = WAITING
        self.suspend_reason = None
        self.counters = {
            "discovery_ticks": 0,
            "layout_runs": 0,
            "filter_events": 0,
            "attachments": 0,
            "buttons_created": 0,
            "launches": 0,
        }
        self._app = app
        self._serial = 0
        self._editor = None
        self._row = None
        self._button = None
        self._watched = []
        self._connections = []
        self._graveyard = []
        self._graveyard_connections = []
        self._layout_pending = False
        self._in_layout = False
        self._deferred_failure = None
        self._launching = False
        self._notice = None
        self._recreations = 0
        self._structure = []
        self._reported = set()
        self._discovery = None
        self._layout = None
        self._quit_connected = False
        try:
            self._discovery = QtCore.QTimer(self)
            self._discovery.setInterval(DISCOVERY_INTERVAL_MS)
            self._discovery.timeout.connect(self._on_discovery_tick)
            self._layout = QtCore.QTimer(self)
            self._layout.setSingleShot(True)
            self._layout.setInterval(0)
            self._layout.timeout.connect(self._on_layout_timer)
            app.aboutToQuit.connect(self.stop)
            self._quit_connected = True
        except Exception:
            self.dispose_partial()
            raise

    def dispose_partial(self):
        """Undo a failed construction. Returns True when nothing owned by
        this controller remains reachable from Qt."""
        clean = True
        for timer in (self._discovery, self._layout):
            if timer is not None:
                try:
                    timer.stop()
                except Exception:
                    clean = False
        if self._quit_connected:
            try:
                self._app.aboutToQuit.disconnect(self.stop)
                self._quit_connected = False
            except Exception:
                clean = False
        try:
            self.setParent(None)
            self.deleteLater()
        except Exception:
            clean = False
        self._discovery = None
        self._layout = None
        return clean

    # -- lifecycle ----------------------------------------------------------

    def start(self):
        self._discover_once()
        if self.state == WAITING:
            self._discovery.start()
        return self.state

    def refresh_request(self):
        """A repeated bootstrap: reuse everything, request one refresh."""
        if self.state in (STOPPING, STOPPED):
            return "stopped"
        if self.state == SUSPENDED:
            if self.suspend_reason != SUSPEND_UNSUPPORTED:
                console("Quick Launch stopped after an error in this session. "
                        "Restart SFM to use the CPM button again.")
                return "restart-required"
            self.state = WAITING
            self.suspend_reason = None
            self._reported.discard("unsupported")
            self._discover_once()
            if self.state == WAITING:
                self._discovery.start()
            return "rediscovered:" + self.state
        if self.state == WAITING:
            self._discover_once()
            return "refreshed:" + self.state
        # An explicit Autoinit refresh rearms button recreation.
        self._rearm_recreation()
        self._schedule_layout()
        return "refreshed:" + self.state

    def stop(self, *args):
        if self.state in (STOPPING, STOPPED):
            return
        self.state = STOPPING
        for timer in (self._discovery, self._layout):
            try:
                if timer is not None:
                    timer.stop()
            except Exception:
                pass
        if self._quit_connected:
            try:
                if _valid(self._app):
                    self._app.aboutToQuit.disconnect(self.stop)
            except Exception:
                pass
            self._quit_connected = False
        self._release_attachment(final=True)
        self._purge_graveyard()
        notice = self._notice
        self._notice = None
        if _valid(notice):
            try:
                notice.close()
                notice.deleteLater()
            except Exception:
                pass
        self.state = STOPPED

    # -- discovery ----------------------------------------------------------

    def _on_discovery_tick(self):
        try:
            self.counters["discovery_ticks"] += 1
            if self.state != WAITING:
                self._discovery.stop()
                return
            self._purge_graveyard()
            self._discover_once()
        except Exception:
            self._fail("discovery")

    def _find_editors(self):
        found = []
        for root in QtGui.QApplication.topLevelWidgets():
            if not _valid(root):
                continue
            candidates = [root] + list(root.findChildren(QtGui.QWidget, EDITOR_NAME))
            for widget in candidates:
                if (_class_name(widget) == EDITOR_CLASS
                        and widget.objectName() == EDITOR_NAME
                        and not _contains(found, widget)):
                    found.append(widget)
        return found

    def _classify_editor(self, editor):
        """('ok', row, add, None) for the complete, uniquely supported toolbar;
        ('waiting', None, None, reason) while it is absent, still being built
        or ambiguous; ('unsupported', None, None, reason) for a structure
        Quick Launch positively cannot use."""
        rows = [child for child in _widget_children(editor)
                if _class_name(child) == ROW_CLASS]
        if not rows:
            return ("waiting", None, None, "upper bar not present yet")
        if len(rows) > 1:
            return ("waiting", None, None, "%d upper bar candidates" % (len(rows),))
        row = rows[0]
        if row.layout() is not None:
            return ("unsupported", None, None, "the upper bar uses a layout manager")
        adds = [child for child in _widget_children(row)
                if _class_name(child) == NATIVE_BUTTON_CLASS
                and child.toolTip() == NATIVE_ADD_TOOLTIP]
        if not adds:
            return ("waiting", None, None, "native Add button not present yet")
        if len(adds) > 1:
            return ("waiting", None, None, "%d native Add button candidates" % (len(adds),))
        return ("ok", row, adds[0], None)

    def _discover_once(self):
        editors = self._find_editors()
        if len(editors) != 1:
            # Absent, or temporarily ambiguous: keep waiting, inject nothing.
            return
        status, row, add, reason = self._classify_editor(editors[0])
        if status == "unsupported":
            self._suspend_unsupported(reason)
        elif status == "ok":
            self._attach(editors[0], row)

    def _suspend_unsupported(self, reason):
        self._discovery.stop()
        self.state = SUSPENDED
        self.suspend_reason = SUSPEND_UNSUPPORTED
        if "unsupported" not in self._reported:
            self._reported.add("unsupported")
            console("this Animation Set Editor toolbar isn't supported (%s), so "
                    "the CPM button wasn't added. Open Character Preset Manager "
                    "from the Scripts menu." % (reason,))

    # -- attachment ---------------------------------------------------------

    def _attach(self, editor, row):
        self._serial += 1
        serial = self._serial
        self._editor = editor
        self._row = row
        # A button that died with an earlier toolbar is released; one still
        # alive elsewhere stays owned, so no second button is created.
        if not _valid(self._button):
            self._button = None
        self._structure = []
        self._rearm_recreation()
        self._reported.discard("foreign-button")
        self._reported.discard("button-elsewhere")
        self.state = ATTACHED
        self._discovery.stop()
        self.counters["attachments"] += 1
        lost = self._make_lost_slot(serial)
        for source in (editor, row):
            source.destroyed.connect(lost)
            self._connections.append((source, lost))
        self._watch(editor)
        self._watch(row)
        self._schedule_layout()

    def _make_lost_slot(self, serial):
        def lost(*args):
            self._on_attachment_lost(serial)
        return lost

    def _on_button_destroyed(self, *args):
        if self.state == ATTACHED:
            self._schedule_layout()

    def _rearm_recreation(self):
        self._recreations = 0
        self._reported.discard("recreation-limit")

    def _on_attachment_lost(self, serial):
        # Runs from a destroyed() emission: never inspect the dying object.
        # The button reference is kept and validated at the next attachment.
        try:
            if serial != self._serial or self.state != ATTACHED:
                return
            self._serial += 1
            self._graveyard.extend(self._watched)
            self._graveyard.extend([source for source, slot in self._connections])
            self._graveyard_connections.extend(self._connections)
            self._watched = []
            self._connections = []
            self._editor = None
            self._row = None
            self._structure = []
            self._layout_pending = False
            self._layout.stop()
            self.state = WAITING
            self._discovery.start()
        except Exception:
            self._fail("attachment loss")

    def _purge_graveyard(self):
        """Remove leftover filters and connections from objects that
        survived a lost attachment, one event-loop turn later."""
        if self._button is not None and not _valid(self._button):
            self._button = None
        pending = self._graveyard_connections
        self._graveyard_connections = []
        for source, slot in pending:
            if _valid(source):
                try:
                    source.destroyed.disconnect(slot)
                except Exception:
                    pass
        objects = self._graveyard
        self._graveyard = []
        for obj in objects:
            if _valid(obj):
                try:
                    obj.removeEventFilter(self)
                except Exception:
                    pass

    def _release_attachment(self, final):
        """Detach from objects that are still valid. CPM's own button is
        deleted only while it is still in the released upper bar; a button
        someone moved elsewhere is never moved or deleted. A non-final
        release keeps owning it so that no second button is created."""
        self._serial += 1
        for source, slot in self._connections:
            if _valid(source):
                try:
                    source.destroyed.disconnect(slot)
                except Exception:
                    pass
        for obj in self._watched:
            if _valid(obj):
                try:
                    obj.removeEventFilter(self)
                except Exception:
                    pass
        button, row = self._button, self._row
        if not _valid(button):
            self._button = None
        elif row is not None and button.parentWidget() is row:
            try:
                button.hide()
                button.deleteLater()
            except Exception:
                pass
            self._button = None
        elif final:
            for signal, slot in ((button.clicked, self._on_click),
                                 (button.destroyed, self._on_button_destroyed)):
                try:
                    signal.disconnect(slot)
                except Exception:
                    pass
            self._button = None
        self._connections = []
        self._watched = []
        self._editor = None
        self._row = None
        self._structure = []
        self._layout_pending = False

    def _watch(self, obj):
        self._watched = [item for item in self._watched if _valid(item)]
        if not _contains(self._watched, obj):
            obj.installEventFilter(self)
            self._watched.append(obj)

    # -- events and layout --------------------------------------------------

    def eventFilter(self, obj, event):
        try:
            self.counters["filter_events"] += 1
            if (self.state == ATTACHED and not self._in_layout
                    and int(event.type()) in _WATCHED_EVENT_TYPES):
                self._schedule_layout()
        except Exception:
            self._deferred_failure = traceback.format_exc()
            try:
                self._layout.start()
            except Exception:
                pass
        return False

    def _schedule_layout(self):
        if self._layout_pending:
            return
        self._layout_pending = True
        self._layout.start()

    def _on_layout_timer(self):
        try:
            self._layout_pending = False
            if self._deferred_failure is not None:
                detail = self._deferred_failure
                self._deferred_failure = None
                self._fail("event filter", detail)
                return
            if self.state == ATTACHED:
                self._run_layout()
        except Exception:
            self._fail("layout")

    def _run_layout(self):
        self.counters["layout_runs"] += 1
        editor, row = self._editor, self._row
        if not (_valid(editor) and _valid(row)):
            self._on_attachment_lost(self._serial)
            return
        status, row_now, add, reason = self._classify_editor(editor)
        if status != "ok" or row_now is not row:
            # The attached toolbar lost its required structure or was
            # replaced: detach safely, then wait, reattach or suspend.
            self._release_attachment(final=False)
            if status == "unsupported":
                self._suspend_unsupported(reason)
            elif status == "ok":
                self._attach(editor, row_now)
            else:
                self.state = WAITING
                self._discovery.start()
            return
        self._in_layout = True
        try:
            structure = []
            for child in _widget_children(row):
                if child is self._button:
                    continue
                structure.append(child)
                if not child.isWindow():
                    self._watch(child)
            # A genuine change to the non-CPM children rearms recreation;
            # CPM's own creation, removal, geometry and visibility do not.
            if not _same_members(structure, self._structure):
                self._structure = structure
                self._rearm_recreation()
            button = self._ensure_button(row, add)
            if button is not None:
                self._place(row, add, button)
        finally:
            self._in_layout = False

    def _ensure_button(self, row, add):
        button = self._button
        if button is not None:
            if _valid(button):
                if button.parentWidget() is row:
                    self._reported.discard("button-elsewhere")
                    return button
                # Moved elsewhere by another script: still ours. It is never
                # moved back, deleted or duplicated.
                if "button-elsewhere" not in self._reported:
                    self._reported.add("button-elsewhere")
                    console("the CPM button was moved out of the toolbar by "
                            "another script; it was left where it is.")
                return None
            self._button = None
            self._recreations += 1
        if self._recreations > MAX_BUTTON_RECREATIONS:
            if "recreation-limit" not in self._reported:
                self._reported.add("recreation-limit")
                console(RECREATION_EXHAUSTED_TEXT)
            return None
        for child in _widget_children(row):
            if child.objectName() == BUTTON_NAME:
                if "foreign-button" not in self._reported:
                    self._reported.add("foreign-button")
                    console("another widget named %s is already in the toolbar; "
                            "it was left untouched and the CPM button was not "
                            "added." % (BUTTON_NAME,))
                return None
        button = QtGui.QToolButton(row)
        button.hide()
        button.setObjectName(BUTTON_NAME)
        button.setText(BUTTON_TEXT)
        button.setToolTip(BUTTON_TOOLTIP)
        button.setAccessibleName(BUTTON_TOOLTIP)
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        try:
            button.setAutoRaise(bool(add.autoRaise()))
        except Exception:
            pass
        button.clicked.connect(self._on_click)
        button.destroyed.connect(self._on_button_destroyed)
        self._button = button
        self.counters["buttons_created"] += 1
        return button

    def _place(self, row, add, button):
        band = add.geometry()
        height = band.height() if band.height() > 0 else NOMINAL_HEIGHT
        width = max(NOMINAL_WIDTH, button.sizeHint().width())
        spans = _occupied_spans(row, button, band.y(), band.y() + height)
        x = find_free_slot(row.width(), band.x(), spans, width)
        if x is None:
            if not button.isHidden():
                button.hide()
            return
        target = QtCore.QRect(x, band.y(), width, height)
        if button.geometry() != target:
            button.setGeometry(target)
        if button.isHidden():
            button.show()

    # -- launch -------------------------------------------------------------

    def _on_click(self, *args):
        if self._launching:
            console("Character Preset Manager is already opening; click ignored.")
            return "busy"
        self._launching = True
        try:
            return self.launch()
        finally:
            self._launching = False

    def launch(self):
        """Execute the unchanged installed R15 launcher in a fresh dictionary.
        The launcher decides load, reuse and refusal and shows its own
        notices."""
        self.counters["launches"] += 1
        path = installed_launcher_path()
        source = _read_bytes(path)
        if source is None:
            console("launch failed: the CPM Scripts-menu launcher could not be "
                    "read at %s" % (path,))
            self._show_notice(LAUNCH_FAILED_TEXT)
            return "launcher-unreadable"
        namespace = None
        try:
            code = compile(source, path, "exec", 0, True)
            source = None
            namespace = {
                "__name__": "__main__",
                "__file__": path,
                "__doc__": None,
                "__package__": None,
                "__builtins__": _builtins_module,
            }
            eval(code, namespace, namespace)
        except Exception:
            console("launch failed: the CPM Scripts-menu launcher raised\n%s"
                    % (traceback.format_exc(),))
            self._show_notice(LAUNCH_FAILED_TEXT)
            return "launcher-failed"
        finally:
            code = None
            namespace = None
            try:
                sys.exc_clear()
            except AttributeError:
                pass
        return "launched"

    def _show_notice(self, text):
        try:
            app = QtGui.QApplication.instance()
            if app is None:
                return "no-qapplication"
            if app.activeModalWidget() is not None:
                console("notice suppressed (a modal dialog is active): %s" % (text,))
                return "suppressed-modal"
            box = self._notice
            if not _valid(box):
                box = QtGui.QMessageBox()
                box.setObjectName(NOTICE_NAME)
                box.setWindowTitle(NOTICE_TITLE)
                box.setIcon(QtGui.QMessageBox.Information)
                box.setStandardButtons(QtGui.QMessageBox.Ok)
                box.setModal(False)
                box.setWindowModality(QtCore.Qt.NonModal)
                box.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
                box.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
                self._notice = box
            box.setText(text)
            box.show()
            box.raise_()
            return "shown"
        except Exception:
            console("notice failed: %s\n%s" % (text, traceback.format_exc()))
            return "failed"

    # -- failure ------------------------------------------------------------

    def _fail(self, where, detail=None):
        """Stop all automatic activity after an unexpected error. One
        diagnostic; no automatic retry."""
        if self.state in (STOPPING, STOPPED):
            return
        if self.state == SUSPENDED and self.suspend_reason == SUSPEND_FAILED:
            return
        if detail is None:
            detail = traceback.format_exc()
        self.state = SUSPENDED
        self.suspend_reason = SUSPEND_FAILED
        for timer in (self._discovery, self._layout):
            try:
                timer.stop()
            except Exception:
                pass
        try:
            self._release_attachment(final=True)
            self._purge_graveyard()
        except Exception:
            pass
        console("stopped after an unexpected error (%s). The CPM button is "
                "unavailable until SFM restarts; the Scripts menu still opens "
                "Character Preset Manager.\n%s" % (where, detail))


def _existing_controller_state():
    controller = _CONTROLLER
    if controller is None:
        return None
    if not isinstance(controller, QuickLaunchController) or not _valid(controller):
        return "malformed"
    return "ok"


def bootstrap_request():
    """Entry point for the Autoinit bootstrap. Starts the one controller, or
    asks the existing one for a refresh. Returns a short status string."""
    global _CONTROLLER, _RESTART_REQUIRED
    if _RESTART_REQUIRED:
        console("a previous start could not be cleaned up. Restart SFM to use "
                "the CPM button.")
        return "restart-required"
    existing = _existing_controller_state()
    if existing == "malformed":
        console("controller slot is malformed; left untouched. Restart SFM to "
                "use the CPM button.")
        return "controller-malformed"
    if existing == "ok":
        return _CONTROLLER.refresh_request()
    app = QtGui.QApplication.instance()
    if app is None:
        console("no QApplication; the CPM button was not added.")
        return "no-qapplication"
    for child in app.children():
        if child.objectName() == CONTROLLER_NAME:
            console("another Quick Launch controller is already running; left "
                    "untouched. Restart SFM to use this one.")
            return "foreign-controller"
    controller = None
    try:
        controller = QuickLaunchController(app)
    except Exception:
        # The constructor already disposed of what it created; verify it.
        leftover = [child for child in app.children()
                    if child.objectName() == CONTROLLER_NAME]
        if leftover:
            _RESTART_REQUIRED = True
        console("could not start (%s). The Scripts menu still opens Character "
                "Preset Manager.\n%s"
                % ("restart SFM to retry" if _RESTART_REQUIRED else "cleaned up",
                   traceback.format_exc()))
        return "init-failed"
    _CONTROLLER = controller
    try:
        return "started:" + controller.start()
    except Exception:
        controller._fail("start")
        return "start-failed"
